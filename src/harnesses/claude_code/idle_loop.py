"""
Idle-loop detection and orchestrator-scheduler invocation for the Claude Code harness.

Phase G-1: wires the Claude Code harness to automatically poll the session queue
during idle periods. When the user has been idle past a threshold, no task is being
processed, and the message queue is empty, the harness invokes the
``orchestrator-scheduler --poll-once`` skill to drain ``queue/incoming/``.

Design constraints (per Phase G — "AGENTS with SKILLS"):
  - No external daemons, cron jobs, or system services.
  - Idle detection lives inside the harness; queue processing is a SKILL.
  - Skill invocation is bounded (soft timeout) so the harness never hangs.
  - Scheduler failures are non-fatal: the harness logs and continues.

Configuration is sourced from ``settings.json`` under the ``idle_loop`` key::

    "idle_loop": {
      "enabled": true,
      "interval_seconds": 180,
      "action": "invoke_skill",
      "skill": "orchestrator-scheduler",
      "args": ["--poll-once"]
    }

Typical wiring inside the harness main loop::

    from src.harnesses.claude_code.idle_loop import ClaudeIdleLoop

    idle_loop = ClaudeIdleLoop.from_settings("dist/claude/settings.json")

    # On any user activity (keystroke, message, command):
    idle_loop.on_user_activity()

    # When a task starts / finishes:
    idle_loop.set_task_in_progress(True)
    ...
    idle_loop.set_task_in_progress(False)

    # Periodically (e.g. every 30-60s) from the harness scheduler tick:
    result = idle_loop.check_idle(message_queue_empty=mq.empty())
    if result is not None:
        # result is the scheduler's JSON dict (or an error envelope)
        ...
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
from typing import Any, Callable, Dict, List, Optional

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

logger = logging.getLogger("claude_code.idle_loop")

# Defaults
DEFAULT_INTERVAL_SECONDS = 180          # idle threshold (3 minutes)
DEFAULT_SKILL = "orchestrator-scheduler"
DEFAULT_ARGS: List[str] = ["--poll-once"]
DEFAULT_SKILL_TIMEOUT_SECONDS = 35      # hard cap on the blocking invocation

# Module path to the scheduler script, used for the subprocess invocation path.
_SCHEDULER_MODULE_PATH = (
    "src/skills/orchestrator-scheduler/scripts/orchestrator_scheduler.py"
)


@dataclass
class IdleLoopConfig:
    """Parsed ``idle_loop`` configuration from settings.json."""

    enabled: bool = True
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    action: str = "invoke_skill"
    skill: str = DEFAULT_SKILL
    args: List[str] = field(default_factory=lambda: list(DEFAULT_ARGS))
    skill_timeout_seconds: int = DEFAULT_SKILL_TIMEOUT_SECONDS
    # Phase G-2: adaptive backoff + file watch (canonical settings keys, see
    # src/harnesses/shared/backoff_poller.py — backoff_intervals/watch_enabled).
    backoff_intervals: Optional[List[int]] = None
    watch_enabled: bool = True
    watch_poll_seconds: float = 0.5
    # Retained for backward-compatible callers/tests that inspect the raw dict.
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "IdleLoopConfig":
        """Build config from a settings dict's ``idle_loop`` section.

        Unknown keys are ignored (forward compatible). Missing keys fall back
        to defaults. A ``None``/empty section yields a default (enabled) config.
        """
        data = data or {}
        intervals = data.get("backoff_intervals")
        if intervals is not None:
            try:
                intervals = [int(x) for x in intervals] or None
            except (TypeError, ValueError):
                intervals = None
        try:
            watch_poll = float(data.get("watch_poll_seconds", 0.5))
        except (TypeError, ValueError):
            watch_poll = 0.5
        return cls(
            enabled=bool(data.get("enabled", True)),
            interval_seconds=int(data.get("interval_seconds", DEFAULT_INTERVAL_SECONDS)),
            action=str(data.get("action", "invoke_skill")),
            skill=str(data.get("skill", DEFAULT_SKILL)),
            args=list(data.get("args", DEFAULT_ARGS)),
            skill_timeout_seconds=int(
                data.get("skill_timeout_seconds", DEFAULT_SKILL_TIMEOUT_SECONDS)
            ),
            backoff_intervals=intervals,
            watch_enabled=bool(data.get("watch_enabled", True)),
            watch_poll_seconds=watch_poll if watch_poll > 0 else 0.5,
            raw=dict(data),
        )

    def to_backoff_config(self) -> Any:
        """Adapt to the shared :class:`BackoffConfig` (continuous poller)."""
        if BackoffConfig is None:  # pragma: no cover - shared module unavailable
            return None
        # Prefer the canonical from_settings_dict so unknown keys are tolerated.
        return BackoffConfig.from_settings_dict(self.raw or {
            "enabled": self.enabled,
            "backoff_intervals": self.backoff_intervals,
            "watch_enabled": self.watch_enabled,
            "watch_poll_seconds": self.watch_poll_seconds,
        })


class ClaudeIdleLoop:
    """Idle detection + orchestrator-scheduler invocation for Claude Code.

    The harness is responsible for calling :meth:`on_user_activity`,
    :meth:`set_task_in_progress`, and :meth:`check_idle` at the appropriate
    points in its event loop. This class owns no threads or timers — it is a
    pure state machine driven by the harness, keeping it deterministic and
    testable.
    """

    def __init__(
        self,
        config: Optional[IdleLoopConfig] = None,
        repo_root: Optional[Path] = None,
        invoker: Optional[Callable[[List[str], int], Dict[str, Any]]] = None,
        clock: Callable[[], float] = time.monotonic,
        incoming_dir: Optional[Path] = None,
    ) -> None:
        """Initialize the idle loop.

        Args:
            config: Parsed idle-loop configuration. Defaults applied if None.
            repo_root: Repository root (used to locate the scheduler script for
                the default subprocess invoker). Defaults to cwd.
            invoker: Override the skill-invocation strategy. Receives
                ``(args, timeout_seconds)`` and returns the scheduler's JSON
                result dict. Injected in tests; defaults to a subprocess call.
            clock: Monotonic time source (injectable for tests).
            incoming_dir: ``queue/incoming/`` path for the file watch. When None,
                the watch is disabled (loop falls back to fixed-interval polling).
        """
        self.config = config or IdleLoopConfig()
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self._clock = clock
        self._invoker = invoker or self._subprocess_invoker
        self.incoming_dir = Path(incoming_dir) if incoming_dir else None

        now = self._clock()
        self._last_activity_time: float = now
        self._task_in_progress: bool = False
        # Avoid an immediate poll on the first tick after construction.
        self._last_poll_time: float = now

        # Phase G-2: adaptive backoff + file watch via the shared BackoffPoller.
        # The poller owns the ladder and the early-wake-on-new-DELEGATE watch; it
        # calls back into _poll_for_backoff() each cycle. Optional: when the
        # shared module is unavailable the loop keeps its fixed-interval G-1
        # behaviour.
        self._poller: Optional["BackoffPoller"] = None
        if BackoffPoller is not None and BackoffConfig is not None:
            try:
                self._poller = BackoffPoller(
                    config=self.config.to_backoff_config(),
                    incoming_dir=self.incoming_dir,
                    poll=self._poll_for_backoff,
                    clock=clock,
                )
            except Exception as e:  # pragma: no cover - never block the harness
                logger.warning("BackoffPoller disabled (init failed): %s", e)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_settings(
        cls,
        settings_path: str | Path,
        repo_root: Optional[Path] = None,
        **kwargs: Any,
    ) -> "ClaudeIdleLoop":
        """Construct from a settings.json file path.

        A missing file or absent ``idle_loop`` section yields default config.
        """
        config = IdleLoopConfig.from_dict(cls._load_idle_config(settings_path))
        return cls(config=config, repo_root=repo_root, **kwargs)

    @staticmethod
    def _load_idle_config(settings_path: str | Path) -> Optional[Dict[str, Any]]:
        path = Path(settings_path)
        try:
            data = json.loads(path.read_text())
        except FileNotFoundError:
            logger.warning("settings.json not found at %s; using idle-loop defaults", path)
            return None
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Could not parse settings.json at %s: %s; using defaults", path, e)
            return None
        return data.get("idle_loop")

    # ------------------------------------------------------------------
    # Activity / task signals (called by the harness)
    # ------------------------------------------------------------------

    def on_user_activity(self) -> None:
        """Record user activity (keystroke, message, command). Resets idle timer."""
        self._last_activity_time = self._clock()

    def set_task_in_progress(self, in_progress: bool) -> None:
        """Mark whether a task is currently being processed by the harness."""
        self._task_in_progress = bool(in_progress)
        if in_progress:
            # Active work also counts as activity.
            self._last_activity_time = self._clock()

    def idle_duration(self) -> float:
        """Seconds since the last recorded user activity."""
        return self._clock() - self._last_activity_time

    # ------------------------------------------------------------------
    # Idle decision
    # ------------------------------------------------------------------

    def current_interval(self) -> int:
        """Effective idle threshold for this cycle (backoff-aware).

        The configured ``interval_seconds`` governs the *initial* idle threshold
        (preserving the Phase G-1 contract). Once the queue has been observed
        empty at least once, the shared BackoffPoller's ladder takes over and the
        wait grows 5s -> 30s -> 180s -> 600s until work reappears.
        """
        if self._poller is not None and self._poller.level > 0:
            return self._poller.current_interval
        return self.config.interval_seconds

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
        except Exception:  # pragma: no cover - watch failures are non-fatal
            return False
        return False

    def is_idle(self, message_queue_empty: bool = True) -> bool:
        """Return True if all idle conditions are met.

        Conditions (all must hold):
          1. idle-loop enabled
          2. no task in progress
          3. message queue empty
          4. user idle for >= current (backoff-aware) interval

        Wake-early: if the file watch detects a new DELEGATE, the backoff level
        is reset and the idle threshold collapses so we poll immediately.
        """
        if not self.config.enabled:
            return False
        if self._task_in_progress:
            return False
        if not message_queue_empty:
            return False

        if self._queue_has_new_work():
            logger.info("New DELEGATE detected in queue; waking early")
            return True

        return self.idle_duration() >= self.current_interval()

    def check_idle(
        self,
        message_queue_empty: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Check idle conditions; invoke the scheduler skill if idle.

        Intended to be called periodically (e.g. every 30-60s) by the harness.

        Returns:
            None if not idle (no action taken). Otherwise the scheduler's JSON
            result dict. On timeout or error an envelope dict with an
            ``errors`` list is returned (never raises into the harness).
        """
        if not self.is_idle(message_queue_empty=message_queue_empty):
            return None

        idle_secs = int(self.idle_duration())
        logger.info("Claude idle for %ds, polling queue", idle_secs)

        # Record the attempt time up-front so a long/failed invocation does not
        # immediately re-fire on the next tick.
        self._last_poll_time = self._clock()

        start = time.monotonic()
        try:
            result = self._invoker(
                list(self.config.args),
                self.config.skill_timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            logger.warning(
                "Queue poll timed out after %ds; will retry next idle cycle",
                self.config.skill_timeout_seconds,
            )
            envelope = self._error_envelope("timeout", "scheduler invocation timed out")
            self._update_backoff(envelope)
            self._last_activity_time = self._clock()
            return envelope
        except Exception as e:  # non-fatal: never crash the harness
            logger.error("Queue poll error: %s", e)
            envelope = self._error_envelope("invoke", str(e))
            self._update_backoff(envelope)
            self._last_activity_time = self._clock()
            return envelope

        elapsed = time.monotonic() - start
        self._log_poll_result(result, elapsed)
        self._update_backoff(result)

        # Reset the idle timer so we don't poll again until the user is idle
        # for another full (backoff-aware) interval (polling is itself "activity").
        self._last_activity_time = self._clock()
        return result

    def _update_backoff(self, result: Dict[str, Any]) -> None:
        """Advance/reset the shared poller's backoff from a poll result.

        ``check_idle`` runs the scheduler itself (single-shot, harness-driven),
        so we update the poller's level directly rather than calling its
        ``run_cycle`` (which would re-poll). Reset on work processed; advance on
        an empty/failed/error cycle. Non-fatal.
        """
        if self._poller is None:
            return
        try:
            result = result or {}
            processed = int(result.get("processed", 0) or 0)
            if processed > 0:
                self._poller.reset_backoff()
            else:
                self._poller._advance_backoff()
            logger.debug(
                "Backoff level %d -> next interval %ds",
                self._poller.level,
                self._poller.current_interval,
            )
        except Exception as e:  # pragma: no cover - never block the harness
            logger.debug("Backoff update failed: %s", e)

    def _poll_for_backoff(self) -> Dict[str, Any]:
        """Adapter the shared BackoffPoller calls when driven in continuous mode.

        Runs one scheduler invocation via the configured invoker and returns a
        ``{"processed": N, ...}`` dict. Used only when a caller drives the loop
        through :meth:`run_backoff_cycle`; ``check_idle`` does not use this path.
        """
        try:
            result = self._invoker(
                list(self.config.args),
                self.config.skill_timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return self._error_envelope("timeout", "scheduler invocation timed out")
        except Exception as e:
            return self._error_envelope("invoke", str(e))
        return result or {}

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

    # ------------------------------------------------------------------
    # Skill invocation
    # ------------------------------------------------------------------

    def _scheduler_script(self) -> Path:
        return self.repo_root / _SCHEDULER_MODULE_PATH

    def _subprocess_invoker(
        self,
        args: List[str],
        timeout_seconds: int,
    ) -> Dict[str, Any]:
        """Invoke ``orchestrator-scheduler`` as a subprocess and parse its JSON.

        The scheduler emits a single JSON line on stdout (for ``--poll-once``).
        We capture it and parse. Raises ``subprocess.TimeoutExpired`` on timeout
        (handled by the caller). A non-zero exit code is not fatal: the scheduler
        encodes errors inside the JSON ``errors`` array.
        """
        script = self._scheduler_script()
        cmd = [sys.executable, str(script), *args]
        logger.debug("Invoking scheduler: %s (timeout=%ds)", " ".join(cmd), timeout_seconds)

        env = dict(os.environ)
        env.setdefault("AGENTIC_HARNESS", "claude")

        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=env,
            cwd=str(self.repo_root),
        )

        stdout = (completed.stdout or "").strip()
        if not stdout:
            stderr = (completed.stderr or "").strip()
            return self._error_envelope(
                "invoke",
                f"scheduler produced no JSON output (rc={completed.returncode}): {stderr[:200]}",
            )

        # The scheduler prints one JSON object; tolerate trailing log lines by
        # taking the last non-empty line.
        last_line = stdout.splitlines()[-1]
        try:
            return json.loads(last_line)
        except json.JSONDecodeError as e:
            return self._error_envelope("parse", f"could not parse scheduler JSON: {e}")

    # ------------------------------------------------------------------
    # Logging / helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _error_envelope(stage: str, message: str) -> Dict[str, Any]:
        return {
            "processed": 0,
            "failed": 1,
            "duration_ms": 0,
            "queue_empty": None,
            "lock_skipped": False,
            "errors": [{"stage": stage, "message": message}],
        }

    @staticmethod
    def _log_poll_result(result: Dict[str, Any], elapsed_seconds: float) -> None:
        errors = result.get("errors") or []
        if errors:
            logger.error(
                "Queue poll error: %s",
                "; ".join(f"{e.get('stage')}: {e.get('message')}" for e in errors),
            )
            return

        if result.get("lock_skipped"):
            logger.info(
                "Queue poll skipped (another harness holds the lock), duration %.1fs",
                elapsed_seconds,
            )
            return

        processed = result.get("processed", 0)
        logger.info(
            "Queued %d DELEGATEs, duration %.1fs", processed, elapsed_seconds
        )
