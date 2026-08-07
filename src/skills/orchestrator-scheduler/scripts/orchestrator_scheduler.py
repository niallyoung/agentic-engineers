#!/usr/bin/env python3
"""
Orchestrator Scheduler: Harness-native queue polling.

Invokes OrchestratorSkill.poll_queue() on a schedule, or once per harness
idle-loop invocation via the --poll-once flag.

Uses environment variables (read at runtime) for session/harness detection.

No external daemons, no cron jobs—purely a SKILL that can be re-invoked as needed.

Phase G-1 enhancements:
  - --poll-once flag: single polling cycle with a bounded timeout, returns JSON
  - --session-id override: explicit session for testing/automation
  - File-based queue locking (atomic O_CREAT|O_EXCL) with stale-lock cleanup
  - Structured JSON output for harness consumption
"""

import errno
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(name)s — %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Defaults (seconds)
DEFAULT_POLL_TIMEOUT_SECONDS = 30
DEFAULT_STALE_LOCK_SECONDS = 300
DEFAULT_LOCK_ACQUIRE_TIMEOUT_SECONDS = 5
LOCK_RETRY_BASE_DELAY = 0.1
LOCK_RETRY_MAX_ATTEMPTS = 3


class LockTimeoutError(Exception):
    """Raised when the queue lock cannot be acquired (held by another harness)."""


class QueueLock:
    """
    File-based queue lock for multi-harness coordination.

    Acquisition is atomic via os.O_CREAT | os.O_EXCL. The lock file records
    the PID, ISO-8601 timestamp, and harness name for debugging races.

    Stale locks (mtime older than ``stale_age_seconds``) are presumed to be
    left behind by a crashed harness and are cleaned up before acquisition.
    """

    def __init__(
        self,
        lock_path: Path,
        harness: str = "unknown",
        stale_age_seconds: int = DEFAULT_STALE_LOCK_SECONDS,
        acquire_timeout_seconds: int = DEFAULT_LOCK_ACQUIRE_TIMEOUT_SECONDS,
    ):
        self.lock_path = Path(lock_path)
        self.harness = harness
        self.stale_age_seconds = stale_age_seconds
        self.acquire_timeout_seconds = acquire_timeout_seconds
        self._held = False

    def _cleanup_stale(self) -> None:
        """Remove the lock file if it is older than the stale threshold."""
        try:
            age = time.time() - self.lock_path.stat().st_mtime
        except FileNotFoundError:
            return
        except OSError as e:
            logger.warning(f"Could not stat lock file {self.lock_path}: {e}")
            return

        if age > self.stale_age_seconds:
            logger.warning(
                f"Stale lock detected (age={age:.1f}s > {self.stale_age_seconds}s); "
                f"removing: {self.lock_path}"
            )
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass
            except OSError as e:
                logger.error(f"Failed to remove stale lock {self.lock_path}: {e}")

    def acquire(self) -> bool:
        """
        Attempt to acquire the lock, cleaning up stale locks first.

        Retries on contention up to ``acquire_timeout_seconds``. On transient
        OS errors, retries up to LOCK_RETRY_MAX_ATTEMPTS with exponential backoff.

        Returns:
            True if acquired.

        Raises:
            LockTimeoutError: if the lock is held by another (live) harness.
        """
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._cleanup_stale()

        start = time.time()
        os_error_attempts = 0

        while True:
            try:
                fd = os.open(
                    str(self.lock_path),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o644,
                )
                with os.fdopen(fd, "w") as f:
                    f.write(f"{os.getpid()}\n")
                    f.write(f"{datetime.now(timezone.utc).isoformat()}\n")
                    f.write(f"{self.harness}\n")
                self._held = True
                logger.info(
                    f"Lock acquired: {self.lock_path} "
                    f"(pid={os.getpid()}, harness={self.harness})"
                )
                return True

            except FileExistsError:
                # Held by another harness — re-check for staleness, then wait.
                self._cleanup_stale()
                elapsed = time.time() - start
                if elapsed > self.acquire_timeout_seconds:
                    logger.info(
                        f"Lock held by another harness; skipping cycle: {self.lock_path}"
                    )
                    raise LockTimeoutError(
                        f"Could not acquire lock within {self.acquire_timeout_seconds}s"
                    )
                time.sleep(LOCK_RETRY_BASE_DELAY)

            except OSError as e:
                # Transient FS error: retry with exponential backoff.
                os_error_attempts += 1
                if os_error_attempts >= LOCK_RETRY_MAX_ATTEMPTS:
                    logger.error(
                        f"Lock acquisition failed after {os_error_attempts} attempts: {e}"
                    )
                    raise
                backoff = LOCK_RETRY_BASE_DELAY * (2 ** os_error_attempts)
                logger.warning(
                    f"Lock acquisition OS error (errno={e.errno}); "
                    f"retry {os_error_attempts}/{LOCK_RETRY_MAX_ATTEMPTS} in {backoff:.2f}s"
                )
                time.sleep(backoff)

    def release(self) -> None:
        """Release the lock file (idempotent)."""
        try:
            self.lock_path.unlink()
            logger.info(f"Lock released: {self.lock_path}")
        except FileNotFoundError:
            logger.debug(f"Lock already released: {self.lock_path}")
        except OSError as e:
            logger.error(f"Failed to release lock {self.lock_path}: {e}")
        finally:
            self._held = False

    def __enter__(self) -> "QueueLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()


class OrchestratorScheduler:
    """
    Scheduler that polls the queue for DELEGATEs and invokes Orchestrator.

    Session and harness are detected from environment variables at runtime,
    ensuring fresh detection on each invocation (no cached state). A session
    override may be supplied for testing/automation.
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        harness: Optional[str] = None,
        stale_lock_seconds: int = DEFAULT_STALE_LOCK_SECONDS,
        lock_acquire_timeout_seconds: int = DEFAULT_LOCK_ACQUIRE_TIMEOUT_SECONDS,
    ):
        """
        Initialize scheduler with runtime environment detection.

        Args:
            session_id: Explicit session ID override (otherwise detect from env).
            harness: Explicit harness override (otherwise detect from env).
            stale_lock_seconds: Lock age beyond which a lock is treated as stale.
            lock_acquire_timeout_seconds: Time to wait for a contended lock.
        """
        self.session_id = session_id or self._detect_session_id()
        self.harness = harness or self._detect_harness()
        self.stale_lock_seconds = stale_lock_seconds
        self.lock_acquire_timeout_seconds = lock_acquire_timeout_seconds
        self.orchestrator = None

        logger.info(
            f"OrchestratorScheduler initialized: "
            f"session={self.session_id}, harness={self.harness}"
        )

    def _detect_session_id(self) -> str:
        """
        Detect session ID from environment variables (runtime).

        Priority:
        1. CLAUDE_SESSION_ID (Claude harness)
        2. OPENCODE_SESSION_ID (OpenCode harness)
        3. COPILOT_SESSION_ID (Copilot harness)
        4. AGENTIC_SESSION_ID (generic override)
        5. CLAUDE_CODE_SESSION_ID (Claude Code CLI)

        Raises:
            RuntimeError: If no session ID found
        """
        session_id = (
            os.environ.get('CLAUDE_SESSION_ID') or
            os.environ.get('OPENCODE_SESSION_ID') or
            os.environ.get('COPILOT_SESSION_ID') or
            os.environ.get('AGENTIC_SESSION_ID') or
            os.environ.get('CLAUDE_CODE_SESSION_ID')
        )

        if not session_id:
            msg = (
                "No session ID found in environment. Set one of:\n"
                "  - CLAUDE_SESSION_ID (for Claude harness)\n"
                "  - OPENCODE_SESSION_ID (for OpenCode harness)\n"
                "  - COPILOT_SESSION_ID (for Copilot harness)\n"
                "  - AGENTIC_SESSION_ID (generic override)\n"
                "  - CLAUDE_CODE_SESSION_ID (Claude Code CLI)\n"
                "Or pass --session-id explicitly."
            )
            logger.error(msg)
            raise RuntimeError(msg)

        logger.debug(f"Detected session ID: {session_id}")
        return session_id

    def _detect_harness(self) -> str:
        """
        Detect harness from environment variables (runtime).

        Priority:
        1. AGENTIC_HARNESS (explicit override)
        2. Infer from which session ID env var is set
        3. Default to "claude"
        """
        if os.environ.get('AGENTIC_HARNESS'):
            harness = os.environ.get('AGENTIC_HARNESS')
            logger.debug(f"Detected harness from AGENTIC_HARNESS: {harness}")
            return harness

        if os.environ.get('OPENCODE_SESSION_ID'):
            logger.debug("Detected harness from OPENCODE_SESSION_ID: opencode")
            return 'opencode'

        if os.environ.get('COPILOT_SESSION_ID'):
            logger.debug("Detected harness from COPILOT_SESSION_ID: copilot")
            return 'copilot'

        if os.environ.get('CLAUDE_SESSION_ID') or os.environ.get('CLAUDE_CODE_SESSION_ID'):
            logger.debug("Detected harness: claude (default)")
            return 'claude'

        logger.debug("Using default harness: claude")
        return 'claude'

    def _load_orchestrator(self) -> None:
        """
        Lazy-load OrchestratorSkill to avoid circular imports.
        """
        if self.orchestrator is not None:
            return

        try:
            # Add src/ to path if not already there.
            # __file__ = src/skills/orchestrator-scheduler/scripts/<this>; 4x parent = src/.
            src_root = Path(__file__).resolve().parent.parent.parent.parent
            if str(src_root) not in sys.path:
                sys.path.insert(0, str(src_root))

            from skills.orchestrator.scripts.orchestrator_skill import OrchestratorSkill

            # Initialize with detected session/harness
            self.orchestrator = OrchestratorSkill(
                session_id=self.session_id,
                harness=self.harness
            )
            logger.info(f"OrchestratorSkill loaded: {self.orchestrator.queue_root}")

        except Exception as e:
            logger.error(f"Failed to load OrchestratorSkill: {e}", exc_info=True)
            raise

    def _queue_root(self) -> Path:
        """Return the session queue root path (orchestrator must be loaded)."""
        self._load_orchestrator()
        return Path(self.orchestrator.queue_root)

    def _lock_path(self) -> Path:
        """Return the lock-file path for this session's queue."""
        return self._queue_root() / ".lock"

    def run(self) -> Tuple[int, int]:
        """
        Poll queue and process DELEGATEs (single cycle, no lock semantics).

        Retained for backward compatibility. Prefer poll_queue_once() for
        harness idle-loop invocation.

        Returns:
            Tuple[int, int]: (processed_count, failed_count)
        """
        try:
            self._load_orchestrator()

            logger.info("Starting queue poll...")
            result = self.orchestrator.poll_queue()

            if isinstance(result, tuple):
                processed, failed = result
            else:
                processed = result
                failed = 0

            logger.info(f"Queue poll complete: processed={processed}, failed={failed}")
            return (processed, failed)

        except Exception as e:
            logger.error(f"Error during queue polling: {e}", exc_info=True)
            raise

    def poll_queue_once(
        self,
        timeout_seconds: int = DEFAULT_POLL_TIMEOUT_SECONDS,
    ) -> Dict[str, Any]:
        """
        Process all DELEGATEs in queue/incoming/ exactly once, then return.

        Acquires a file-based queue lock (cleaning up stale locks) so that
        concurrent harnesses serialize their polling. If the lock is held by
        another live harness, this cycle is skipped (not an error).

        Args:
            timeout_seconds: Soft budget for the cycle. If exceeded mid-cycle,
                remaining DELEGATEs are left for the next invocation and a
                ``timeout`` error is recorded.

        Returns:
            Structured result dict:
            {
              "processed": int,
              "failed": int,
              "duration_ms": int,
              "queue_empty": bool,
              "session_id": str,
              "harness": str,
              "lock_skipped": bool,
              "errors": [ {"stage": str, "message": str}, ... ],
            }
        """
        start = time.monotonic()
        errors: List[Dict[str, str]] = []
        processed = 0
        failed = 0
        queue_empty = True
        lock_skipped = False

        def _result() -> Dict[str, Any]:
            return {
                "processed": processed,
                "failed": failed,
                "duration_ms": int((time.monotonic() - start) * 1000),
                "queue_empty": queue_empty,
                "session_id": self.session_id,
                "harness": self.harness,
                "lock_skipped": lock_skipped,
                "errors": errors,
            }

        # Load orchestrator + resolve paths.
        try:
            self._load_orchestrator()
            lock_path = self._lock_path()
            incoming_dir = self._queue_root() / "incoming"
        except Exception as e:
            logger.error(f"Failed to initialize queue for poll-once: {e}", exc_info=True)
            errors.append({"stage": "init", "message": str(e)})
            failed += 1
            return _result()

        lock = QueueLock(
            lock_path,
            harness=self.harness,
            stale_age_seconds=self.stale_lock_seconds,
            acquire_timeout_seconds=self.lock_acquire_timeout_seconds,
        )

        # Acquire lock (skip cycle on contention, fail gracefully on OS error).
        try:
            lock.acquire()
        except LockTimeoutError:
            lock_skipped = True
            logger.info("Poll-once skipped: queue lock held by another harness.")
            return _result()
        except OSError as e:
            errors.append({"stage": "lock", "message": f"errno={e.errno}: {e}"})
            failed += 1
            logger.error(f"Poll-once lock error: {e}")
            return _result()

        try:
            # Quick emptiness probe for accurate queue_empty + early exit.
            try:
                pending = list(incoming_dir.glob("*.yaml"))
            except Exception as e:
                pending = []
                errors.append({"stage": "scan", "message": str(e)})
            queue_empty = len(pending) == 0

            if queue_empty:
                logger.info("Poll-once: queue empty, nothing to process.")
                return _result()

            # Soft timeout guard before a potentially long poll cycle.
            elapsed = time.monotonic() - start
            if elapsed >= timeout_seconds:
                errors.append({
                    "stage": "timeout",
                    "message": f"Timeout ({timeout_seconds}s) reached before processing",
                })
                logger.warning("Poll-once timed out before processing began.")
                return _result()

            logger.info(
                f"Poll-once: processing {len(pending)} delegate(s) "
                f"(budget={timeout_seconds}s)."
            )
            poll_result = self.orchestrator.poll_queue()
            if isinstance(poll_result, tuple):
                processed, failed_from_poll = poll_result
            else:
                processed, failed_from_poll = poll_result, 0
            failed += failed_from_poll

            # Re-check emptiness after the cycle.
            try:
                queue_empty = len(list(incoming_dir.glob("*.yaml"))) == 0
            except Exception:
                pass

            duration = time.monotonic() - start
            if duration > timeout_seconds:
                errors.append({
                    "stage": "timeout",
                    "message": (
                        f"Cycle exceeded {timeout_seconds}s budget "
                        f"(took {duration:.1f}s); remaining items deferred"
                    ),
                })
                logger.warning(
                    f"Poll-once exceeded timeout budget ({duration:.1f}s > {timeout_seconds}s)."
                )

        except Exception as e:
            logger.error(f"Poll-once processing error: {e}", exc_info=True)
            errors.append({"stage": "process", "message": str(e)})
            failed += 1
        finally:
            lock.release()

        result = _result()
        logger.info(
            f"Poll-once complete: processed={result['processed']}, "
            f"failed={result['failed']}, duration_ms={result['duration_ms']}, "
            f"errors={len(result['errors'])}"
        )
        return result

    def run_with_retry(self, max_retries: int = 3) -> Tuple[int, int]:
        """
        Run queue polling with retry logic.

        Args:
            max_retries: Number of times to retry on failure

        Returns:
            Tuple[int, int]: (processed_count, failed_count)
        """
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Attempt {attempt}/{max_retries}")
                return self.run()

            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt} failed: {e}")

                if attempt < max_retries:
                    logger.info(f"Retrying in 5 seconds...")
                    time.sleep(5)

        # All retries exhausted
        logger.error(f"All {max_retries} attempts failed. Last error: {last_error}")
        raise last_error


def main():
    """CLI entry point for orchestrator-scheduler."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Harness-native queue polling scheduler for agentic-engineers"
    )
    parser.add_argument(
        '--poll-once',
        action='store_true',
        help="Single polling cycle with lock + 30s budget; emits JSON result"
    )
    parser.add_argument(
        '--session-id',
        type=str,
        default=None,
        help="Explicit session ID override (for testing/automation)"
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_POLL_TIMEOUT_SECONDS,
        help=f"Poll-once soft timeout in seconds (default: {DEFAULT_POLL_TIMEOUT_SECONDS})"
    )
    parser.add_argument(
        '--retry',
        type=int,
        default=1,
        help="Number of retry attempts on failure (default: 1; ignored with --poll-once)"
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        scheduler = OrchestratorScheduler(session_id=args.session_id)

        if args.poll_once:
            result = scheduler.poll_queue_once(timeout_seconds=args.timeout)
            print(json.dumps(result))
            sys.exit(0 if not result["errors"] else 1)

        if args.retry > 1:
            processed, failed = scheduler.run_with_retry(max_retries=args.retry)
        else:
            processed, failed = scheduler.run()

        # Exit with status code
        sys.exit(0 if failed == 0 else 1)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        # Emit a structured error if poll-once was requested.
        if getattr(args, "poll_once", False):
            print(json.dumps({
                "processed": 0,
                "failed": 1,
                "duration_ms": 0,
                "queue_empty": None,
                "lock_skipped": False,
                "errors": [{"stage": "fatal", "message": str(e)}],
            }))
        sys.exit(1)


if __name__ == '__main__':
    main()
