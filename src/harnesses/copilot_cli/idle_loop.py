#!/usr/bin/env python3
"""
Copilot CLI Idle-Loop Integration (Phase G-1).

Wires the Copilot CLI harness to the agentic-engineers queue: when the CLI is
idle (no command being processed), it invokes the ``orchestrator-scheduler``
SKILL with ``--poll-once`` to drain any queued DELEGATEs.

Design constraints (SPEC.md compliant):
  - No external daemon/cron/launchd — polling runs inside the harness idle-loop.
  - The scheduler is a SKILL, invoked via ``--poll-once`` (one bounded cycle).
  - Multi-harness safe — the scheduler holds a file lock per session queue, so
    several harnesses sharing one session never process the same DELEGATE twice.
  - Graceful — scheduler failures/timeouts never crash the harness; the next
    idle cycle simply retries.

Contract with the scheduler (``orchestrator-scheduler --poll-once``):
  Emits a single JSON object on stdout, e.g.::

      {"processed": 2, "failed": 0, "duration_ms": 1840,
       "queue_empty": false, "session_id": "...", "harness": "copilot",
       "lock_skipped": false, "errors": []}

Typical wiring (Copilot CLI host calls this between commands)::

    idle = CopilotIdleLoop()
    idle.notify_activity()          # on every user command
    ...
    result = idle.check_idle()      # when the prompt goes idle
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    # Phase G-2 shared continuous-backoff poller (adaptive backoff + file watch).
    from src.harnesses.shared.backoff_poller import BackoffConfig, BackoffPoller
except Exception:  # pragma: no cover - fallback when imported off the src root
    try:
        from harnesses.shared.backoff_poller import (  # type: ignore
            BackoffConfig,
            BackoffPoller,
        )
    except Exception:  # pragma: no cover
        BackoffConfig = None  # type: ignore
        BackoffPoller = None  # type: ignore

logger = logging.getLogger("copilot.idle_loop")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(
        logging.Formatter("[%(asctime)s] %(name)s — %(levelname)s: %(message)s")
    )
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)


# ---- Defaults -------------------------------------------------------------

# Idle threshold before polling (seconds). Phase G recommends 180s.
DEFAULT_IDLE_THRESHOLD_SECONDS = 180

# Hard wall-clock budget for the blocking scheduler invocation (seconds).
# The scheduler's own soft timeout is set just under this so it returns first.
DEFAULT_BLOCK_SECONDS = 35

# Soft per-cycle timeout passed to the scheduler (must be < block budget so the
# scheduler returns cleanly before we kill the subprocess).
DEFAULT_SCHEDULER_TIMEOUT_SECONDS = 30


def _resolve_src_root() -> Path:
    """Return the repository ``src/`` root (…/src/harnesses/copilot_cli/ -> …/src)."""
    return Path(__file__).resolve().parent.parent.parent


@dataclass
class IdlePollResult:
    """Outcome of one idle-loop poll attempt."""

    polled: bool                      # did we actually invoke the scheduler?
    processed: int = 0
    failed: int = 0
    queue_empty: Optional[bool] = None
    lock_skipped: bool = False
    duration_ms: int = 0
    errors: List[Dict[str, str]] = field(default_factory=list)
    skip_reason: Optional[str] = None  # set when polled is False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "polled": self.polled,
            "processed": self.processed,
            "failed": self.failed,
            "queue_empty": self.queue_empty,
            "lock_skipped": self.lock_skipped,
            "duration_ms": self.duration_ms,
            "errors": self.errors,
            "skip_reason": self.skip_reason,
        }


class CopilotIdleLoop:
    """
    Idle detector + scheduler invoker for the Copilot CLI harness.

    The host marks activity via :meth:`notify_activity` (on each user command)
    and calls :meth:`check_idle` when the CLI is otherwise quiet. When the idle
    duration exceeds the threshold, :meth:`check_idle` invokes the scheduler
    once and returns a structured :class:`IdlePollResult`.
    """

    def __init__(
        self,
        idle_threshold_seconds: int = DEFAULT_IDLE_THRESHOLD_SECONDS,
        block_seconds: int = DEFAULT_BLOCK_SECONDS,
        scheduler_timeout_seconds: int = DEFAULT_SCHEDULER_TIMEOUT_SECONDS,
        session_id: Optional[str] = None,
        python_executable: Optional[str] = None,
        backoff_config: Optional["BackoffConfig"] = None,
        incoming_dir: Optional["Path"] = None,
    ) -> None:
        self.idle_threshold_seconds = idle_threshold_seconds
        self.block_seconds = block_seconds
        # Keep the scheduler's soft timeout strictly below the hard block budget.
        self.scheduler_timeout_seconds = min(
            scheduler_timeout_seconds, max(1, block_seconds - 1)
        )
        self.session_id = session_id
        self.python_executable = python_executable or sys.executable or "python3"
        self._last_activity = time.monotonic()
        self._busy = False  # True while a command is being processed
        self.enabled = True

        # Phase G-2: adaptive backoff + file watch via the shared BackoffPoller.
        self.backoff_config = backoff_config
        self.incoming_dir = Path(incoming_dir) if incoming_dir else None
        self._poller = None
        if BackoffPoller is not None and BackoffConfig is not None:
            try:
                cfg = backoff_config or BackoffConfig()
                self._poller = BackoffPoller(
                    config=cfg,
                    incoming_dir=self.incoming_dir,
                    poll=self._poll_for_backoff,
                )
            except Exception as e:  # pragma: no cover
                logger.warning("BackoffPoller disabled (init failed): %s", e)

    # ---- Construction helpers --------------------------------------------

    @classmethod
    def from_settings(
        cls,
        settings_path: "str | Path",
        **kwargs: Any,
    ) -> "CopilotIdleLoop":
        """
        Construct from a ``settings.json`` file with an ``idle_loop`` section::

            "idle_loop": {
              "enabled": true,
              "interval_seconds": 180,
              "action": "invoke_skill",
              "skill": "orchestrator-scheduler",
              "args": ["--poll-once"]
            }

        A missing file or absent section yields defaults. Explicit ``kwargs``
        override values parsed from settings.
        """
        cfg = cls._load_idle_config(settings_path) or {}
        interval = int(cfg.get("interval_seconds", DEFAULT_IDLE_THRESHOLD_SECONDS))
        # Build the shared backoff config from the canonical G-2 settings keys
        # (backoff_intervals / watch_enabled / watch_poll_seconds). Tolerant of
        # missing/malformed values. Caller kwargs still win.
        if BackoffConfig is not None and "backoff_config" not in kwargs:
            kwargs["backoff_config"] = BackoffConfig.from_settings_dict(cfg)
        loop = cls(idle_threshold_seconds=interval, **kwargs)
        # Honour an explicit disable flag.
        loop.enabled = bool(cfg.get("enabled", True))
        return loop

    @staticmethod
    def _load_idle_config(settings_path: "str | Path") -> Optional[Dict[str, Any]]:
        path = Path(settings_path)
        try:
            data = json.loads(path.read_text())
        except FileNotFoundError:
            logger.warning(
                "settings.json not found at %s; using idle-loop defaults", path
            )
            return None
        except (json.JSONDecodeError, OSError) as e:
            logger.error(
                "Could not parse settings.json at %s: %s; using defaults", path, e
            )
            return None
        return data.get("idle_loop")

    # ---- Activity tracking ------------------------------------------------

    def notify_activity(self) -> None:
        """Mark user/command activity (resets the idle timer)."""
        self._last_activity = time.monotonic()

    def mark_busy(self) -> None:
        """Mark the CLI as actively processing a command (suppresses polling)."""
        self._busy = True
        self._last_activity = time.monotonic()

    def mark_done(self) -> None:
        """Mark command processing complete; idle timer starts now."""
        self._busy = False
        self._last_activity = time.monotonic()

    def idle_seconds(self) -> float:
        """Seconds since the last recorded activity."""
        return time.monotonic() - self._last_activity

    def current_interval(self) -> int:
        """Effective idle threshold this cycle (backoff-aware).

        The configured idle threshold governs the *initial* wait (Phase G-1
        contract). Once the queue has been seen empty, the shared BackoffPoller's
        ladder takes over (5s -> 30s -> 180s -> 600s) until work reappears.
        """
        if self._poller is not None and self._poller.level > 0:
            return self._poller.current_interval
        return self.idle_threshold_seconds

    def backoff_level(self) -> int:
        """Current backoff level (0 = fastest). 0 when backoff unavailable."""
        return self._poller.level if self._poller is not None else 0

    def _queue_has_new_work(self) -> bool:
        """True if the file watch saw a new DELEGATE (resets backoff as a side effect)."""
        if self._poller is None:
            return False
        try:
            if self._poller.has_new_file():
                self._poller.reset_backoff()
                return True
        except Exception:  # pragma: no cover
            return False
        return False

    def is_idle(self) -> bool:
        """True if enabled, not busy, and past the (backoff-aware) threshold.

        Wake-early: a newly-arrived DELEGATE resets backoff and forces an
        immediate idle verdict so the scheduler runs without delay.
        """
        if not self.enabled:
            return False
        if self._busy:
            return False
        if self._queue_has_new_work():
            logger.info("New DELEGATE detected in queue; waking early")
            return True
        return self.idle_seconds() >= self.current_interval()

    # ---- Polling ----------------------------------------------------------

    def check_idle(self, force: bool = False) -> IdlePollResult:
        """
        If idle (or ``force``), invoke the scheduler once and return the result.

        Never raises: scheduler failures/timeouts are captured in the result so
        the harness keeps running. The next idle cycle retries automatically.
        """
        if not force and not self.is_idle():
            return IdlePollResult(polled=False, skip_reason="not_idle")

        logger.info("Copilot idle, polling queue")
        result = self._invoke_scheduler()
        self._update_backoff(result)

        if result.polled and result.lock_skipped:
            logger.info(
                "Queue lock held by another harness — skipping this cycle"
            )
        elif result.polled:
            elapsed_s = result.duration_ms / 1000.0
            logger.info(
                "Processed %d DELEGATEs in %.2fs (failed=%d, queue_empty=%s)",
                result.processed,
                elapsed_s,
                result.failed,
                result.queue_empty,
            )
            for err in result.errors:
                logger.error(
                    "Scheduler error [%s]: %s",
                    err.get("stage", "?"),
                    err.get("message", ""),
                )

        # Reset the idle timer so we don't immediately re-poll.
        self._last_activity = time.monotonic()
        return result

    def _build_command(self) -> List[str]:
        scheduler_script = str(
            _resolve_src_root()
            / "skills"
            / "orchestrator-scheduler"
            / "scripts"
            / "orchestrator_scheduler.py"
        )
        cmd = [
            self.python_executable,
            scheduler_script,
            "--poll-once",
            "--timeout",
            str(self.scheduler_timeout_seconds),
        ]
        if self.session_id:
            cmd += ["--session-id", self.session_id]
        return cmd

    def _build_env(self) -> Dict[str, str]:
        env = dict(os.environ)
        # Ensure the scheduler attributes the queue to the Copilot harness.
        env.setdefault("AGENTIC_HARNESS", "copilot")
        return env

    def _invoke_scheduler(self) -> IdlePollResult:
        """
        Run ``orchestrator-scheduler --poll-once`` as a subprocess, blocking up
        to ``block_seconds``. Parse the JSON result; degrade gracefully on any
        failure.
        """
        cmd = self._build_command()
        env = self._build_env()
        src_root = _resolve_src_root()
        start = time.monotonic()

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(src_root),
                env=env,
                capture_output=True,
                text=True,
                timeout=self.block_seconds,
            )
        except subprocess.TimeoutExpired:
            logger.warning(
                "Scheduler exceeded %ds block budget; deferring to next idle cycle",
                self.block_seconds,
            )
            return IdlePollResult(
                polled=True,
                duration_ms=int((time.monotonic() - start) * 1000),
                errors=[{"stage": "timeout", "message": "block budget exceeded"}],
            )
        except (OSError, ValueError) as e:
            logger.error("Failed to launch scheduler: %s", e)
            return IdlePollResult(
                polled=True,
                duration_ms=int((time.monotonic() - start) * 1000),
                errors=[{"stage": "spawn", "message": str(e)}],
            )

        return self._parse_result(proc, start)

    def _update_backoff(self, result: "IdlePollResult") -> None:
        """Advance/reset the shared poller's backoff from a single-shot poll.

        ``check_idle`` runs the scheduler itself, so we update the poller's level
        directly (reset on work processed, advance on empty/error). Non-fatal.
        """
        if self._poller is None or not result.polled:
            return
        try:
            if result.processed > 0:
                self._poller.reset_backoff()
            else:
                self._poller._advance_backoff()
            logger.debug(
                "Backoff level %d -> next interval %ds",
                self._poller.level,
                self._poller.current_interval,
            )
        except Exception as e:  # pragma: no cover
            logger.debug("Backoff update failed: %s", e)

    def _poll_for_backoff(self) -> Dict[str, Any]:
        """Adapter the shared BackoffPoller calls in continuous mode.

        Runs one scheduler poll and returns a ``{"processed": N, ...}`` dict so
        the poller can reset/advance its backoff level.
        """
        result = self._invoke_scheduler()
        return {
            "processed": result.processed,
            "failed": result.failed,
            "queue_empty": result.queue_empty,
            "lock_skipped": result.lock_skipped,
        }

    def run_backoff_cycle(self):
        """Run one adaptive-backoff poll cycle (poll + backoff update).

        Returns the shared poller's ``CycleOutcome`` or ``None`` when the shared
        BackoffPoller is unavailable. Never raises.
        """
        if self._poller is None:
            return None
        try:
            return self._poller.run_cycle()
        except Exception as e:  # pragma: no cover
            logger.error("Backoff cycle error (non-fatal): %s", e)
            return None

    def sleep_until_next(self) -> float:
        """Sleep the current backoff interval, waking early on a new DELEGATE."""
        if self._poller is None:
            return 0.0
        return self._poller.sleep_until_next()

    def _parse_result(
        self, proc: "subprocess.CompletedProcess[str]", start: float
    ) -> IdlePollResult:
        duration_ms = int((time.monotonic() - start) * 1000)
        payload = self._extract_json(proc.stdout)

        if payload is None:
            stderr_tail = (proc.stderr or "").strip().splitlines()[-3:]
            logger.error(
                "Scheduler produced no parseable JSON (exit=%s): %s",
                proc.returncode,
                " | ".join(stderr_tail) if stderr_tail else "<no stderr>",
            )
            return IdlePollResult(
                polled=True,
                duration_ms=duration_ms,
                errors=[
                    {
                        "stage": "parse",
                        "message": f"no JSON on stdout (exit={proc.returncode})",
                    }
                ],
            )

        return IdlePollResult(
            polled=True,
            processed=int(payload.get("processed", 0) or 0),
            failed=int(payload.get("failed", 0) or 0),
            queue_empty=payload.get("queue_empty"),
            lock_skipped=bool(payload.get("lock_skipped", False)),
            duration_ms=int(payload.get("duration_ms", duration_ms) or duration_ms),
            errors=list(payload.get("errors", []) or []),
        )

    @staticmethod
    def _extract_json(stdout: str) -> Optional[Dict[str, Any]]:
        """
        Extract the scheduler's JSON object from stdout.

        Logging may precede the JSON, so we scan from the last line backward for
        the first line that parses as a JSON object.
        """
        if not stdout:
            return None
        for line in reversed(stdout.strip().splitlines()):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                continue
        return None


def main(argv: Optional[List[str]] = None) -> int:
    """
    CLI entry point — run a single idle poll immediately (``--force``) for
    manual E2E testing of the Copilot idle-loop wiring.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Copilot CLI idle-loop: poll the queue once via orchestrator-scheduler"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Poll immediately, ignoring the idle threshold",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Explicit session ID override (otherwise detected from env)",
    )
    parser.add_argument(
        "--idle-threshold",
        type=int,
        default=DEFAULT_IDLE_THRESHOLD_SECONDS,
        help=f"Idle threshold in seconds (default: {DEFAULT_IDLE_THRESHOLD_SECONDS})",
    )
    parser.add_argument(
        "--block-seconds",
        type=int,
        default=DEFAULT_BLOCK_SECONDS,
        help=f"Hard block budget for the scheduler call (default: {DEFAULT_BLOCK_SECONDS})",
    )
    parser.add_argument("--verbose", action="store_true", help="DEBUG logging")
    args = parser.parse_args(argv)

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    loop = CopilotIdleLoop(
        idle_threshold_seconds=args.idle_threshold,
        block_seconds=args.block_seconds,
        session_id=args.session_id,
    )
    result = loop.check_idle(force=args.force)
    print(json.dumps(result.to_dict()))
    # Non-zero exit only on genuine errors (not lock skips / empty queue).
    return 0 if not result.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
