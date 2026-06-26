"""OpenCode Harness Idle-Loop Integration (Phase G-1).

Wires the OpenCode harness to automatically poll its session queue during idle
periods by invoking the ``orchestrator-scheduler`` SKILL (``--poll-once``).

Design reference: ``src/orchestration/PHASE_G_HARNESS_COOPERATION.md``.

Behaviour
---------
1. Idle detection — the harness records user/command activity via
   :meth:`OpenCodeIdleLoop.on_activity`. When no activity has occurred for
   ``idle_threshold_seconds`` (default 180s, i.e. 3 minutes), the loop is
   considered idle.
2. Skill invocation — on idle, the loop invokes
   ``orchestrator-scheduler --poll-once`` as a subprocess (the canonical SKILL
   entry point), blocking up to ``skill_timeout_seconds`` (default 35s).
3. Queue processing — the scheduler acquires the session queue lock, processes
   available DELEGATEs, and emits a JSON result on stdout. The lock provides
   multi-harness coordination: if another harness (e.g. Claude Code) holds the
   lock, this cycle is skipped cleanly (``lock_skipped: true``).
4. Continuation — the loop resets its activity clock so the next idle window is
   measured afresh; the harness keeps calling :meth:`check_and_poll`.

SPEC compliance
---------------
- No external daemon: polling runs inside the harness via the SKILL.
- No startup hook: idle detection is harness-internal.
- All work through the SKILL: we shell out to ``orchestrator_scheduler.py``
  rather than importing orchestration internals, keeping the harness decoupled.
- Graceful failure: timeouts and scheduler errors never raise to the harness;
  they are logged and the loop continues.
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
from typing import Any, Dict, Optional

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

logger = logging.getLogger(__name__)

# Defaults (seconds). Idle threshold sits in the 3-5 minute window from the
# Phase G design; the skill timeout gives the 30s poll budget headroom.
DEFAULT_IDLE_THRESHOLD_SECONDS = 180
DEFAULT_SKILL_TIMEOUT_SECONDS = 35
DEFAULT_POLL_BUDGET_SECONDS = 30


_SCHEDULER_REL = Path(
    "skills/orchestrator-scheduler/scripts/orchestrator_scheduler.py"
)


def _scheduler_script_path() -> Path:
    """Resolve the absolute path to the orchestrator-scheduler script.

    The scheduler lives at
    ``src/skills/orchestrator-scheduler/scripts/orchestrator_scheduler.py``.
    This module may be installed under either ``src/harnesses/opencode/`` or
    ``src/opencode/``, so we walk up the ancestor chain looking for the ``src``
    root that contains the scheduler rather than assuming a fixed depth.
    """
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        candidate = ancestor / _SCHEDULER_REL
        if candidate.exists():
            return candidate
    # Fall back to the conventional src/ layout (parents[2]) even if missing,
    # so the error surfaced later names the expected path.
    return here.parents[2] / _SCHEDULER_REL


@dataclass
class IdlePollResult:
    """Outcome of a single idle-poll attempt."""

    polled: bool                       # Did we actually invoke the scheduler?
    processed: int = 0
    failed: int = 0
    queue_empty: Optional[bool] = None
    lock_skipped: bool = False
    timed_out: bool = False
    duration_seconds: float = 0.0
    error: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


class OpenCodeIdleLoop:
    """Idle detection + orchestrator-scheduler invocation for OpenCode.

    The harness owns the cadence: it should call :meth:`on_activity` whenever the
    user types or a command is processed, and :meth:`check_and_poll` periodically
    (e.g. every 30-60s) from its event loop. ``check_and_poll`` is a no-op until
    the idle threshold is reached.
    """

    def __init__(
        self,
        *,
        idle_threshold_seconds: int = DEFAULT_IDLE_THRESHOLD_SECONDS,
        skill_timeout_seconds: int = DEFAULT_SKILL_TIMEOUT_SECONDS,
        poll_budget_seconds: int = DEFAULT_POLL_BUDGET_SECONDS,
        session_id: Optional[str] = None,
        scheduler_script: Optional[Path] = None,
        python_executable: Optional[str] = None,
        clock: Any = time.monotonic,
        backoff_config: Optional["BackoffConfig"] = None,
        incoming_dir: Optional[Path] = None,
    ) -> None:
        """
        Args:
            idle_threshold_seconds: Seconds of inactivity before polling (3-5 min).
            skill_timeout_seconds: Hard wall-clock timeout for the subprocess.
            poll_budget_seconds: Soft poll budget passed to the scheduler
                (``--timeout``). Should be < ``skill_timeout_seconds``.
            session_id: Explicit session override (passed as ``--session-id``).
                When ``None``, the scheduler detects it from the environment.
            scheduler_script: Override path to the scheduler script (testing).
            python_executable: Python interpreter to run the scheduler with.
            clock: Monotonic clock function (injectable for tests).
        """
        if skill_timeout_seconds <= poll_budget_seconds:
            logger.warning(
                "skill_timeout_seconds (%s) <= poll_budget_seconds (%s); "
                "the subprocess may be killed before the scheduler returns.",
                skill_timeout_seconds,
                poll_budget_seconds,
            )
        self.idle_threshold_seconds = idle_threshold_seconds
        self.skill_timeout_seconds = skill_timeout_seconds
        self.poll_budget_seconds = poll_budget_seconds
        self.session_id = session_id
        self.scheduler_script = Path(scheduler_script) if scheduler_script else _scheduler_script_path()
        self.python_executable = python_executable or sys.executable
        self._clock = clock
        self._last_activity = clock()

        # Phase G-2: adaptive backoff + file watch via the shared BackoffPoller.
        # The poller calls back into poll_now() each cycle and owns the backoff
        # ladder + early-wake-on-new-DELEGATE behaviour. It is optional: when the
        # shared module is unavailable, the loop degrades to the fixed-interval
        # G-1 behaviour.
        self.backoff_config = backoff_config
        self.incoming_dir = Path(incoming_dir) if incoming_dir else None
        self._poller: Optional["BackoffPoller"] = None
        if BackoffPoller is not None and BackoffConfig is not None:
            try:
                cfg = backoff_config or BackoffConfig()
                self._poller = BackoffPoller(
                    config=cfg,
                    incoming_dir=self.incoming_dir,
                    poll=self._poll_for_backoff,
                    clock=clock,
                )
            except Exception as e:  # pragma: no cover
                logger.warning("BackoffPoller disabled (init failed): %s", e)

    # ------------------------------------------------------------------
    # Activity tracking
    # ------------------------------------------------------------------

    def on_activity(self) -> None:
        """Record user/command activity, resetting the idle timer."""
        self._last_activity = self._clock()

    def idle_seconds(self) -> float:
        """Return seconds since the last recorded activity."""
        return self._clock() - self._last_activity

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
        """True if inactive past the current (backoff-aware) threshold.

        Wake-early: a newly-arrived DELEGATE (queue watch) resets backoff and
        forces an immediate idle verdict so the scheduler runs without delay.
        """
        if self._queue_has_new_work():
            logger.info("New DELEGATE detected in queue; waking early")
            return True
        return self.idle_seconds() >= self.current_interval()

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    def check_and_poll(self) -> IdlePollResult:
        """Poll the queue if idle; otherwise return a no-op result.

        Safe to call frequently from the harness event loop. Never raises:
        timeouts and scheduler errors are captured in the returned result.
        """
        if not self.is_idle():
            return IdlePollResult(polled=False)

        result = self.poll_now()
        self._apply_backoff(result)

        # Reset the activity clock so the next idle window is measured afresh,
        # creating the natural ~3-5 minute polling rhythm.
        self.on_activity()
        return result

    def _apply_backoff(self, result: IdlePollResult) -> None:
        """Advance/reset the shared poller's backoff from a single-shot poll.

        ``check_and_poll`` runs the scheduler itself, so we update the poller's
        level directly (reset on work, advance on empty/error). Non-fatal.
        """
        if self._poller is None:
            return
        try:
            if result.processed > 0:
                self._poller.reset_backoff()
            else:
                self._poller._advance_backoff()
        except Exception as e:  # pragma: no cover
            logger.debug("Backoff update failed: %s", e)

    def poll_now(self) -> IdlePollResult:
        """Invoke ``orchestrator-scheduler --poll-once`` immediately.

        Bypasses the idle check (used by :meth:`check_and_poll` and available for
        manual/forced polling). Always returns; never raises.
        """
        logger.info("OpenCode idle, polling queue")

        cmd = [
            self.python_executable,
            str(self.scheduler_script),
            "--poll-once",
            "--timeout",
            str(self.poll_budget_seconds),
        ]
        if self.session_id:
            cmd += ["--session-id", self.session_id]

        env = dict(os.environ)
        # Ensure the scheduler attributes this poll to the OpenCode harness even
        # if AGENTIC_HARNESS is unset upstream.
        env.setdefault("AGENTIC_HARNESS", "opencode")

        start = self._clock()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.skill_timeout_seconds,
                env=env,
            )
        except subprocess.TimeoutExpired:
            duration = self._clock() - start
            logger.warning(
                "Scheduler poll-once timed out after %.1fs; "
                "will retry on next idle cycle",
                duration,
            )
            return IdlePollResult(
                polled=True,
                timed_out=True,
                duration_seconds=duration,
                error="timeout",
            )
        except Exception as e:  # pragma: no cover - defensive
            duration = self._clock() - start
            logger.error("Scheduler poll-once failed to launch: %s", e)
            return IdlePollResult(
                polled=True,
                duration_seconds=duration,
                error=str(e),
            )

        duration = self._clock() - start
        return self._parse_result(proc, duration)

    # ------------------------------------------------------------------
    # Continuous backoff driving (Phase G-2)
    # ------------------------------------------------------------------

    def _poll_for_backoff(self) -> Dict[str, Any]:
        """Adapter the shared BackoffPoller calls each cycle.

        Runs one scheduler poll and returns a ``{"processed": N, ...}`` dict so
        the poller can decide whether to reset or advance the backoff level.
        """
        result = self.poll_now()
        return {
            "processed": result.processed,
            "failed": result.failed,
            "queue_empty": result.queue_empty,
            "lock_skipped": result.lock_skipped,
        }

    def run_backoff_cycle(self):
        """Run one adaptive-backoff poll cycle (poll + backoff update).

        Returns the poller's :class:`CycleOutcome`, or ``None`` when the shared
        BackoffPoller is unavailable (caller should fall back to
        :meth:`check_and_poll`). Never raises.
        """
        if self._poller is None:
            return None
        try:
            return self._poller.run_cycle()
        except Exception as e:  # pragma: no cover - never crash the harness
            logger.error("Backoff cycle error (non-fatal): %s", e)
            return None

    def sleep_until_next(self) -> float:
        """Sleep the current backoff interval, waking early on a new DELEGATE.

        Delegates to the shared poller. Returns 0.0 when unavailable.
        """
        if self._poller is None:
            return 0.0
        return self._poller.sleep_until_next()

    def _parse_result(
        self,
        proc: "subprocess.CompletedProcess[str]",
        duration: float,
    ) -> IdlePollResult:
        """Parse the scheduler's JSON stdout into an :class:`IdlePollResult`."""
        raw: Dict[str, Any] = {}
        stdout = (proc.stdout or "").strip()
        if stdout:
            # The scheduler prints a single JSON object on its final line.
            last_line = stdout.splitlines()[-1]
            try:
                raw = json.loads(last_line)
            except json.JSONDecodeError:
                logger.error(
                    "Could not parse scheduler output as JSON: %r", last_line
                )

        if not raw:
            stderr = (proc.stderr or "").strip()
            logger.error(
                "Scheduler poll-once returned no result "
                "(exit=%s, stderr=%s)",
                proc.returncode,
                stderr[-500:] if stderr else "<empty>",
            )
            return IdlePollResult(
                polled=True,
                duration_seconds=duration,
                error=f"no-result (exit={proc.returncode})",
            )

        processed = int(raw.get("processed", 0) or 0)
        failed = int(raw.get("failed", 0) or 0)
        lock_skipped = bool(raw.get("lock_skipped", False))
        queue_empty = raw.get("queue_empty")
        errors = raw.get("errors") or []

        if lock_skipped:
            logger.info(
                "Queue lock held by another harness; skipped polling "
                "(multi-harness coordination)"
            )
        elif queue_empty and processed == 0:
            logger.info("Queue empty; nothing to process (%.1fs)", duration)
        else:
            logger.info(
                "Processed %d DELEGATEs in %.1fs (%d failed)",
                processed,
                duration,
                failed,
            )

        if errors:
            for err in errors:
                logger.error(
                    "Scheduler error [%s]: %s",
                    err.get("stage", "?"),
                    err.get("message", err),
                )

        return IdlePollResult(
            polled=True,
            processed=processed,
            failed=failed,
            queue_empty=queue_empty,
            lock_skipped=lock_skipped,
            duration_seconds=duration,
            error=(errors[0].get("message") if errors else None),
            raw=raw,
        )


__all__ = ["OpenCodeIdleLoop", "IdlePollResult"]
