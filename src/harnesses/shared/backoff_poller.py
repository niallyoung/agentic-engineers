"""
Continuous idle-loop polling with adaptive backoff + file watch (Phase G-2).

Phase G-1 wired each harness to invoke ``orchestrator-scheduler --poll-once``
once per idle window. Phase G-2 adds the *continuous* polling engine that sits
underneath that single-shot call: a harness-agnostic state machine that polls
the session queue on an interval that **backs off** when the queue stays empty
and **resets** the moment work appears — either because a poll processed
DELEGATEs, or because a lightweight filesystem watch on ``queue/incoming/``
detected a newly-arrived DELEGATE file.

Design goals (per Phase G — "AGENTS with SKILLS"):
  - No external daemons, cron jobs, or system services — this is a pure,
    harness-driven state machine. The harness owns the cadence; this class owns
    the *decision* of how long to wait and *when* to poll.
  - Deterministic and unit-testable: time and sleep are injectable; the file
    watch is a cheap directory scan with no OS-specific inotify dependency.
  - Non-fatal: a poll callable that raises never crashes the loop. The error is
    recorded and the loop continues (treated as an empty/failed cycle).

Backoff ladder
--------------
Polling waits a configurable interval keyed by a *backoff level*. The default
ladder matches the Phase G-2 specification::

    level 0 -> 5s     (active: queue recently had work)
    level 1 -> 30s
    level 2 -> 180s
    level 3 -> 600s   (deep idle; capped here)

Each *empty* poll advances the level by one (capped at the last rung). Any of
the following resets the level to 0:
  - a poll that processed >= 1 DELEGATE,
  - a file watch that detected a new file in ``queue/incoming/``.

Typical wiring inside a harness loop::

    from src.harnesses.shared.backoff_poller import BackoffPoller, BackoffConfig

    poller = BackoffPoller(
        config=BackoffConfig.from_settings_dict(settings.get("idle_loop")),
        incoming_dir=queue_root / "incoming",
        poll=lambda: scheduler.poll_once(),   # returns {"processed": N, ...}
    )

    while harness_idle:
        outcome = poller.run_cycle()          # one poll + backoff update
        poller.sleep_until_next()             # honours interval OR wakes on file
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("harness.backoff_poller")

# Default backoff ladder (seconds), indexed by level.
DEFAULT_BACKOFF_INTERVALS: List[int] = [5, 30, 180, 600]


@dataclass
class BackoffConfig:
    """Configuration for the continuous backoff poller.

    Attributes:
        enabled: Master switch. When False, the poller is a no-op.
        backoff_intervals: Ordered list of wait-seconds per backoff level. Must
            be non-empty; the last value is the cap (``max_backoff_seconds``).
        watch_enabled: Whether to scan ``queue/incoming/`` between sleeps to
            wake early when a DELEGATE arrives.
        watch_poll_seconds: How often the file watch re-scans while sleeping.
    """

    enabled: bool = True
    backoff_intervals: List[int] = field(
        default_factory=lambda: list(DEFAULT_BACKOFF_INTERVALS)
    )
    watch_enabled: bool = True
    watch_poll_seconds: float = 0.5

    def __post_init__(self) -> None:
        if not self.backoff_intervals:
            self.backoff_intervals = list(DEFAULT_BACKOFF_INTERVALS)
        # Coerce to ints and drop non-positive rungs defensively.
        cleaned = [int(x) for x in self.backoff_intervals if int(x) > 0]
        self.backoff_intervals = cleaned or list(DEFAULT_BACKOFF_INTERVALS)

    @property
    def max_level(self) -> int:
        """Highest valid backoff level index."""
        return len(self.backoff_intervals) - 1

    @property
    def max_backoff_seconds(self) -> int:
        """The capped (deepest) backoff interval."""
        return self.backoff_intervals[-1]

    def interval_for(self, level: int) -> int:
        """Return the wait-seconds for ``level`` (clamped into range)."""
        idx = max(0, min(level, self.max_level))
        return self.backoff_intervals[idx]

    @classmethod
    def from_settings_dict(cls, data: Optional[Dict[str, Any]]) -> "BackoffConfig":
        """Build config from an ``idle_loop`` settings section.

        Unknown keys are ignored (forward-compatible). Missing keys fall back to
        defaults. Invalid types are coerced/ignored gracefully rather than
        raising, so a malformed config never takes the harness down.
        """
        data = data or {}

        def _bool(key: str, default: bool) -> bool:
            v = data.get(key, default)
            return bool(v)

        def _intervals() -> List[int]:
            raw = data.get("backoff_intervals")
            if raw is None:
                # Allow a single ``max_backoff_seconds`` to extend the default
                # ladder's cap without redefining the whole ladder.
                return list(DEFAULT_BACKOFF_INTERVALS)
            if not isinstance(raw, (list, tuple)):
                logger.warning(
                    "idle_loop.backoff_intervals must be a list; using defaults"
                )
                return list(DEFAULT_BACKOFF_INTERVALS)
            out: List[int] = []
            for item in raw:
                try:
                    iv = int(item)
                except (TypeError, ValueError):
                    logger.warning("Ignoring non-int backoff interval %r", item)
                    continue
                if iv > 0:
                    out.append(iv)
            return out or list(DEFAULT_BACKOFF_INTERVALS)

        def _watch_poll() -> float:
            v = data.get("watch_poll_seconds", 0.5)
            try:
                f = float(v)
            except (TypeError, ValueError):
                return 0.5
            return f if f > 0 else 0.5

        return cls(
            enabled=_bool("enabled", True),
            backoff_intervals=_intervals(),
            watch_enabled=_bool("watch_enabled", True),
            watch_poll_seconds=_watch_poll(),
        )


@dataclass
class CycleOutcome:
    """Result of a single :meth:`BackoffPoller.run_cycle` call."""

    polled: bool                       # did we actually invoke ``poll``?
    processed: int = 0                 # DELEGATEs processed this cycle
    backoff_level: int = 0             # level *after* this cycle
    backoff_seconds: int = 0           # the interval we will sleep next
    reset: bool = False                # was the level reset to 0 this cycle?
    error: Optional[str] = None        # captured (non-fatal) poll error
    skip_reason: Optional[str] = None  # set when polled is False


class BackoffPoller:
    """Harness-agnostic continuous poller with adaptive backoff + file watch.

    The poller owns no threads. It is driven by the harness, which alternates
    :meth:`run_cycle` (do one poll + update backoff) with
    :meth:`sleep_until_next` (wait the current interval, waking early if a file
    appears). Both time and sleep are injectable for deterministic tests.
    """

    def __init__(
        self,
        config: Optional[BackoffConfig] = None,
        incoming_dir: Optional[Path] = None,
        poll: Optional[Callable[[], Dict[str, Any]]] = None,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        """Initialise the poller.

        Args:
            config: Backoff configuration (defaults applied if None).
            incoming_dir: Path to ``queue/incoming/`` for the file watch. If
                None, the file watch is disabled regardless of config.
            poll: Callable performing one queue poll. Returns a dict with at
                least ``processed`` (int). Injected in tests / wired to the
                scheduler in production. May raise — errors are captured.
            clock: Monotonic time source (injectable).
            sleeper: Sleep function (injectable; tests pass a no-op recorder).
        """
        self.config = config or BackoffConfig()
        self.incoming_dir = Path(incoming_dir) if incoming_dir else None
        self._poll = poll
        self._clock = clock
        self._sleep = sleeper

        self._level: int = 0
        # Snapshot of incoming/ filenames, used to detect *new* arrivals.
        self._seen: set[str] = self._scan_incoming()

    # ------------------------------------------------------------------
    # Backoff state
    # ------------------------------------------------------------------

    @property
    def level(self) -> int:
        """Current backoff level."""
        return self._level

    @property
    def current_interval(self) -> int:
        """Wait-seconds for the current backoff level."""
        return self.config.interval_for(self._level)

    def reset_backoff(self) -> None:
        """Reset the backoff level to 0 (active state)."""
        self._level = 0

    def _advance_backoff(self) -> None:
        """Advance the backoff level by one, capped at ``max_level``."""
        if self._level < self.config.max_level:
            self._level += 1

    # ------------------------------------------------------------------
    # File watch
    # ------------------------------------------------------------------

    def _scan_incoming(self) -> set[str]:
        """Return the set of current filenames in ``incoming/`` (cheap scan).

        Tolerant of a missing directory or a file deleted mid-scan: returns an
        empty set rather than raising, so a transient FS race never crashes the
        loop.
        """
        if self.incoming_dir is None:
            return set()
        try:
            return {
                e.name
                for e in os.scandir(self.incoming_dir)
                if e.is_file() and not e.name.startswith(".")
            }
        except (FileNotFoundError, NotADirectoryError):
            return set()
        except OSError as e:  # pragma: no cover - defensive
            logger.debug("incoming scan failed: %s", e)
            return set()

    def has_new_file(self) -> bool:
        """True if a new DELEGATE file appeared since the last snapshot.

        Updates the internal snapshot as a side effect, so repeated calls only
        report each file once. Designed to be < 1ms for typical queue sizes.
        """
        if not self.config.watch_enabled or self.incoming_dir is None:
            return False
        current = self._scan_incoming()
        new = current - self._seen
        self._seen = current
        return bool(new)

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    def run_cycle(self) -> CycleOutcome:
        """Perform one poll and update the backoff level.

        - Disabled config -> no-op outcome.
        - poll raises -> captured as a non-fatal error; treated as an empty
          cycle (backoff advances).
        - poll processed >= 1 -> backoff resets to 0.
        - poll processed 0 -> backoff advances one level (capped).

        Returns:
            :class:`CycleOutcome` describing what happened and the next wait.
        """
        if not self.config.enabled:
            return CycleOutcome(
                polled=False,
                backoff_level=self._level,
                backoff_seconds=self.current_interval,
                skip_reason="disabled",
            )

        if self._poll is None:
            raise RuntimeError("BackoffPoller has no poll callable configured")

        # Refresh the watch snapshot so files we are about to process are not
        # later re-reported as "new" by has_new_file().
        self._seen = self._scan_incoming()

        error: Optional[str] = None
        processed = 0
        try:
            result = self._poll() or {}
            processed = int(result.get("processed", 0) or 0)
        except Exception as e:  # non-fatal: never crash the loop
            error = str(e)
            logger.error("poll cycle error (non-fatal): %s", e)

        reset = False
        if processed > 0:
            self.reset_backoff()
            reset = True
            logger.info("Processed %d DELEGATE(s); backoff reset to 0", processed)
        else:
            self._advance_backoff()
            logger.debug(
                "Empty/failed cycle; backoff advanced to level %d (%ds)",
                self._level,
                self.current_interval,
            )

        return CycleOutcome(
            polled=True,
            processed=processed,
            backoff_level=self._level,
            backoff_seconds=self.current_interval,
            reset=reset,
            error=error,
        )

    def sleep_until_next(self) -> float:
        """Sleep the current interval, waking early if a new file arrives.

        While the file watch is enabled, this sleeps in ``watch_poll_seconds``
        slices and returns early (resetting backoff) the instant a new DELEGATE
        appears in ``incoming/``. With the watch disabled it performs a single
        sleep of the full interval.

        Returns:
            The wall-clock seconds actually slept (per the injected clock).
        """
        interval = float(self.current_interval)
        start = self._clock()

        if not self.config.watch_enabled or self.incoming_dir is None:
            self._sleep(interval)
            return self._clock() - start

        slice_s = max(0.001, float(self.config.watch_poll_seconds))
        while (self._clock() - start) < interval:
            if self.has_new_file():
                self.reset_backoff()
                logger.info("New DELEGATE detected during sleep; waking early")
                break
            remaining = interval - (self._clock() - start)
            self._sleep(min(slice_s, remaining))

        return self._clock() - start


__all__ = [
    "BackoffPoller",
    "BackoffConfig",
    "CycleOutcome",
    "DEFAULT_BACKOFF_INTERVALS",
]
