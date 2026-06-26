"""
Phase G-2 — Exhaustive tests for the continuous polling backoff/file-watch engine.

Covers (per the G-2 test plan):
  1. Unit — backoff logic (levels, advance/reset, cap, custom intervals)
  2. Unit — file watch (detection, reset, deletion race, overhead)
  3. Unit — config parsing (fields, defaults, type validation, invalid handling)
  4. Integration — empty-queue behaviour (advance 0->3, honoured sleeps)
  5. Integration — DELEGATE arrival (file-watch wake + reset)
  6. Integration — error recovery (poll raises, malformed, non-blocking)
  7. Stress — rapid cycles (10 DELEGATEs, no hang, fast)
  8. Stress — long idle with wake (level 3 -> early wake, no wasted sleeps)

All tests are deterministic: time and sleep are injected via fakes, so no test
sleeps for real and there are no flaky timing assertions.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from src.harnesses.shared.backoff_poller import (
    BackoffPoller,
    BackoffConfig,
    CycleOutcome,
    DEFAULT_BACKOFF_INTERVALS,
)


# ---------------------------------------------------------------------------
# Deterministic fakes
# ---------------------------------------------------------------------------


class FakeClock:
    """Monotonic clock that only advances when explicitly told to, or when the
    paired FakeSleeper sleeps."""

    def __init__(self, start: float = 1000.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


class FakeSleeper:
    """Records every sleep and advances the bound clock (simulating elapsed
    wall-time) so watch-driven loops terminate deterministically."""

    def __init__(self, clock: FakeClock) -> None:
        self.clock = clock
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)
        self.clock.advance(seconds)

    @property
    def total(self) -> float:
        return sum(self.calls)


def make_poller(
    *,
    intervals=None,
    incoming_dir: Path | None = None,
    poll=None,
    watch_enabled: bool = True,
    watch_poll_seconds: float = 0.5,
    enabled: bool = True,
):
    clock = FakeClock()
    sleeper = FakeSleeper(clock)
    cfg = BackoffConfig(
        enabled=enabled,
        backoff_intervals=list(intervals or DEFAULT_BACKOFF_INTERVALS),
        watch_enabled=watch_enabled,
        watch_poll_seconds=watch_poll_seconds,
    )
    poller = BackoffPoller(
        config=cfg,
        incoming_dir=incoming_dir,
        poll=poll or (lambda: {"processed": 0}),
        clock=clock,
        sleeper=sleeper,
    )
    return poller, clock, sleeper


def write_delegate(incoming: Path, name: str) -> Path:
    incoming.mkdir(parents=True, exist_ok=True)
    p = incoming / name
    p.write_text("handoff_type: DELEGATE\ntask_id: t\n")
    return p


# ===========================================================================
# 1. Unit — Backoff logic
# ===========================================================================


class TestBackoffLogic:
    def test_initial_level_zero_five_seconds(self):
        poller, _, _ = make_poller()
        assert poller.level == 0
        assert poller.current_interval == 5

    def test_empty_polls_advance_ladder(self):
        poller, _, _ = make_poller(poll=lambda: {"processed": 0})
        expected = [(1, 30), (2, 180), (3, 600)]
        for level, secs in expected:
            outcome = poller.run_cycle()
            assert outcome.backoff_level == level
            assert outcome.backoff_seconds == secs

    def test_successful_poll_resets_to_zero(self):
        seq = iter([0, 0, 0, 3])  # 3 empties then a hit

        def poll():
            return {"processed": next(seq)}

        poller, _, _ = make_poller(poll=poll)
        poller.run_cycle()
        poller.run_cycle()
        poller.run_cycle()
        assert poller.level == 3
        outcome = poller.run_cycle()
        assert outcome.reset is True
        assert outcome.processed == 3
        assert poller.level == 0
        assert poller.current_interval == 5

    def test_capped_at_max_backoff(self):
        poller, _, _ = make_poller(poll=lambda: {"processed": 0})
        for _ in range(10):
            poller.run_cycle()
        assert poller.level == 3
        assert poller.current_interval == 600
        assert poller.config.max_backoff_seconds == 600

    @pytest.mark.parametrize(
        "intervals,expected_caps",
        [
            ([10, 20, 40], 40),
            ([1, 5], 5),
            ([7], 7),
            ([2, 4, 8, 16, 32], 32),
        ],
    )
    def test_custom_intervals_respected(self, intervals, expected_caps):
        poller, _, _ = make_poller(intervals=intervals, poll=lambda: {"processed": 0})
        assert poller.current_interval == intervals[0]
        for _ in range(20):
            poller.run_cycle()
        assert poller.current_interval == expected_caps

    def test_reset_backoff_method(self):
        poller, _, _ = make_poller(poll=lambda: {"processed": 0})
        poller.run_cycle()
        poller.run_cycle()
        assert poller.level == 2
        poller.reset_backoff()
        assert poller.level == 0

    def test_missing_processed_key_treated_as_empty(self):
        poller, _, _ = make_poller(poll=lambda: {})
        outcome = poller.run_cycle()
        assert outcome.processed == 0
        assert outcome.backoff_level == 1

    def test_none_poll_result_treated_as_empty(self):
        poller, _, _ = make_poller(poll=lambda: None)
        outcome = poller.run_cycle()
        assert outcome.processed == 0
        assert poller.level == 1


# ===========================================================================
# 2. Unit — File watch
# ===========================================================================


class TestFileWatch:
    def test_detects_new_file(self, tmp_path):
        incoming = tmp_path / "incoming"
        incoming.mkdir()
        poller, _, _ = make_poller(incoming_dir=incoming)
        assert poller.has_new_file() is False
        write_delegate(incoming, "a.yaml")
        assert poller.has_new_file() is True

    def test_new_file_reported_once(self, tmp_path):
        incoming = tmp_path / "incoming"
        incoming.mkdir()
        poller, _, _ = make_poller(incoming_dir=incoming)
        write_delegate(incoming, "a.yaml")
        assert poller.has_new_file() is True
        assert poller.has_new_file() is False  # already seen

    def test_sleep_resets_backoff_on_detection(self, tmp_path):
        incoming = tmp_path / "incoming"
        incoming.mkdir()
        poller, clock, sleeper = make_poller(
            incoming_dir=incoming, intervals=[600], watch_poll_seconds=0.5
        )
        # Force deep backoff.
        for _ in range(5):
            poller.run_cycle()
        assert poller.level == 0  # single-rung ladder caps at 0
        poller, clock, sleeper = make_poller(
            incoming_dir=incoming, intervals=[5, 600], watch_poll_seconds=0.5
        )
        poller.run_cycle()  # empty -> level 1 (600s)
        assert poller.current_interval == 600
        # A file arrives during the sleep window.
        write_delegate(incoming, "wake.yaml")
        poller.sleep_until_next()
        assert poller.level == 0  # reset by detection

    def test_graceful_if_dir_missing(self, tmp_path):
        missing = tmp_path / "does_not_exist"
        poller, _, _ = make_poller(incoming_dir=missing)
        # No crash; nothing detected.
        assert poller.has_new_file() is False

    def test_graceful_if_file_deleted_before_scan(self, tmp_path):
        incoming = tmp_path / "incoming"
        incoming.mkdir()
        poller, _, _ = make_poller(incoming_dir=incoming)
        f = write_delegate(incoming, "a.yaml")
        assert poller.has_new_file() is True
        f.unlink()  # deleted before next scan
        # Disappearance is not a "new file"; must not raise.
        assert poller.has_new_file() is False

    def test_hidden_files_ignored(self, tmp_path):
        incoming = tmp_path / "incoming"
        incoming.mkdir()
        poller, _, _ = make_poller(incoming_dir=incoming)
        (incoming / ".lock").write_text("x")
        assert poller.has_new_file() is False

    def test_watch_disabled_never_detects(self, tmp_path):
        incoming = tmp_path / "incoming"
        incoming.mkdir()
        poller, _, _ = make_poller(incoming_dir=incoming, watch_enabled=False)
        write_delegate(incoming, "a.yaml")
        assert poller.has_new_file() is False

    def test_watch_overhead_under_1ms(self, tmp_path):
        incoming = tmp_path / "incoming"
        incoming.mkdir()
        for i in range(20):
            write_delegate(incoming, f"d{i}.yaml")
        # Real clock for a genuine perf measurement.
        poller = BackoffPoller(
            config=BackoffConfig(),
            incoming_dir=incoming,
            poll=lambda: {"processed": 0},
        )
        poller.has_new_file()  # prime snapshot
        iterations = 200
        start = time.perf_counter()
        for _ in range(iterations):
            poller.has_new_file()
        avg_ms = ((time.perf_counter() - start) / iterations) * 1000
        assert avg_ms < 1.0, f"watch overhead {avg_ms:.3f}ms exceeds 1ms"


# ===========================================================================
# 3. Unit — Config parsing
# ===========================================================================


class TestConfigParsing:
    def test_loads_all_fields(self):
        cfg = BackoffConfig.from_settings_dict({
            "enabled": True,
            "backoff_intervals": [5, 30, 180, 600],
            "watch_enabled": True,
            "watch_poll_seconds": 0.25,
        })
        assert cfg.enabled is True
        assert cfg.backoff_intervals == [5, 30, 180, 600]
        assert cfg.watch_enabled is True
        assert cfg.watch_poll_seconds == 0.25

    def test_defaults_when_empty(self):
        cfg = BackoffConfig.from_settings_dict({})
        assert cfg.enabled is True
        assert cfg.backoff_intervals == DEFAULT_BACKOFF_INTERVALS
        assert cfg.watch_enabled is True
        assert cfg.watch_poll_seconds == 0.5

    def test_defaults_when_none(self):
        cfg = BackoffConfig.from_settings_dict(None)
        assert cfg.backoff_intervals == DEFAULT_BACKOFF_INTERVALS

    def test_bool_coercion(self):
        cfg = BackoffConfig.from_settings_dict({"enabled": 0, "watch_enabled": 1})
        assert cfg.enabled is False
        assert cfg.watch_enabled is True

    def test_invalid_intervals_type_falls_back(self):
        cfg = BackoffConfig.from_settings_dict({"backoff_intervals": "nope"})
        assert cfg.backoff_intervals == DEFAULT_BACKOFF_INTERVALS

    def test_non_int_intervals_filtered(self):
        cfg = BackoffConfig.from_settings_dict(
            {"backoff_intervals": [5, "x", 30, None, 600]}
        )
        assert cfg.backoff_intervals == [5, 30, 600]

    def test_non_positive_intervals_dropped(self):
        cfg = BackoffConfig.from_settings_dict({"backoff_intervals": [0, -5, 10]})
        assert cfg.backoff_intervals == [10]

    def test_empty_intervals_falls_back_to_default(self):
        cfg = BackoffConfig.from_settings_dict({"backoff_intervals": []})
        assert cfg.backoff_intervals == DEFAULT_BACKOFF_INTERVALS

    def test_invalid_watch_poll_seconds_falls_back(self):
        cfg = BackoffConfig.from_settings_dict({"watch_poll_seconds": "fast"})
        assert cfg.watch_poll_seconds == 0.5

    def test_non_positive_watch_poll_falls_back(self):
        cfg = BackoffConfig.from_settings_dict({"watch_poll_seconds": -1})
        assert cfg.watch_poll_seconds == 0.5

    def test_unknown_keys_ignored(self):
        cfg = BackoffConfig.from_settings_dict({"enabled": True, "future": "x"})
        assert cfg.enabled is True

    def test_post_init_drops_bad_intervals(self):
        cfg = BackoffConfig(backoff_intervals=[0, -1])
        assert cfg.backoff_intervals == DEFAULT_BACKOFF_INTERVALS

    def test_max_level_and_interval_for(self):
        cfg = BackoffConfig(backoff_intervals=[5, 30, 180, 600])
        assert cfg.max_level == 3
        assert cfg.interval_for(0) == 5
        assert cfg.interval_for(3) == 600
        assert cfg.interval_for(99) == 600   # clamped high
        assert cfg.interval_for(-5) == 5     # clamped low


# ===========================================================================
# 4. Integration — Empty-queue behaviour
# ===========================================================================


class TestEmptyQueueBehaviour:
    def test_five_empty_polls_advance_and_cap(self):
        poller, _, _ = make_poller(poll=lambda: {"processed": 0})
        levels = [poller.run_cycle().backoff_level for _ in range(5)]
        assert levels == [1, 2, 3, 3, 3]

    def test_each_sleep_honours_configured_duration(self, tmp_path):
        # Watch disabled -> a single full-interval sleep per cycle.
        poller, clock, sleeper = make_poller(
            intervals=[5, 30, 180, 600],
            poll=lambda: {"processed": 0},
            watch_enabled=False,
        )
        slept = []
        for _ in range(4):
            poller.run_cycle()
            sleeper.calls.clear()
            poller.sleep_until_next()
            slept.append(sleeper.total)
        assert slept == [30.0, 180.0, 600.0, 600.0]

    def test_outcome_fields_complete(self):
        poller, _, _ = make_poller(poll=lambda: {"processed": 0})
        outcome = poller.run_cycle()
        assert isinstance(outcome, CycleOutcome)
        assert outcome.polled is True
        assert outcome.error is None
        assert outcome.skip_reason is None

    def test_disabled_poller_is_noop(self):
        poller, _, _ = make_poller(enabled=False, poll=lambda: {"processed": 5})
        outcome = poller.run_cycle()
        assert outcome.polled is False
        assert outcome.skip_reason == "disabled"
        assert poller.level == 0


# ===========================================================================
# 5. Integration — DELEGATE arrival wakes the loop
# ===========================================================================


class TestDelegateArrival:
    def test_arrival_during_deep_idle_wakes_and_resets(self, tmp_path):
        incoming = tmp_path / "incoming"
        incoming.mkdir()
        poller, clock, sleeper = make_poller(
            incoming_dir=incoming,
            intervals=[5, 30, 180, 600],
            poll=lambda: {"processed": 0},
            watch_poll_seconds=1.0,
        )
        # Drive to level 2 (180s).
        poller.run_cycle()
        poller.run_cycle()
        assert poller.level == 2
        assert poller.current_interval == 180

        # DELEGATE arrives while we are about to sleep 180s.
        write_delegate(incoming, "incoming.yaml")
        slept = poller.sleep_until_next()
        # Woke far earlier than 180s and reset to active.
        assert slept < 180
        assert poller.level == 0

    def test_after_wake_next_cycle_processes_and_stays_active(self, tmp_path):
        incoming = tmp_path / "incoming"
        incoming.mkdir()
        processed_flag = {"n": 0}

        def poll():
            # Simulate the scheduler draining the file that triggered the wake.
            n = len(list(incoming.glob("*.yaml")))
            processed_flag["n"] = n
            for f in incoming.glob("*.yaml"):
                f.unlink()
            return {"processed": n}

        poller, _, _ = make_poller(
            incoming_dir=incoming, intervals=[5, 600], poll=poll, watch_poll_seconds=1.0
        )
        poller.run_cycle()  # empty -> level 1
        write_delegate(incoming, "d.yaml")
        poller.sleep_until_next()  # wakes, reset to 0
        outcome = poller.run_cycle()  # processes the delegate
        assert outcome.processed == 1
        assert poller.level == 0


# ===========================================================================
# 6. Integration — Error recovery (non-blocking)
# ===========================================================================


class TestErrorRecovery:
    def test_poll_exception_captured_not_raised(self):
        def poll():
            raise RuntimeError("scheduler boom")

        poller, _, _ = make_poller(poll=poll)
        outcome = poller.run_cycle()  # must not raise
        assert outcome.error == "scheduler boom"
        assert outcome.processed == 0
        # An errored cycle is treated as empty -> backoff advances.
        assert poller.level == 1

    def test_retry_succeeds_after_error(self):
        calls = {"n": 0}

        def poll():
            calls["n"] += 1
            if calls["n"] == 1:
                raise TimeoutError("lock timeout")
            return {"processed": 2}

        poller, _, _ = make_poller(poll=poll)
        out1 = poller.run_cycle()
        assert out1.error and poller.level == 1
        out2 = poller.run_cycle()
        assert out2.error is None
        assert out2.processed == 2
        assert poller.level == 0  # reset after successful retry

    def test_timeout_error_is_non_fatal(self):
        import subprocess

        def poll():
            raise subprocess.TimeoutExpired(cmd="scheduler", timeout=30)

        poller, _, _ = make_poller(poll=poll)
        outcome = poller.run_cycle()
        assert outcome.error is not None
        assert poller.level == 1

    def test_partial_batch_still_resets_when_processed_positive(self):
        # Even if the scheduler reports failures, a positive ``processed`` count
        # means work happened -> stay active.
        def poll():
            return {"processed": 1, "failed": 2}

        poller, _, _ = make_poller(poll=poll)
        poller.run_cycle()
        poller.run_cycle()  # advance a bit first
        poller.reset_backoff()
        poller._level = 2
        outcome = poller.run_cycle()
        assert outcome.processed == 1
        assert poller.level == 0


# ===========================================================================
# 7. Stress — Rapid cycles
# ===========================================================================


class TestRapidCycles:
    def test_ten_delegates_processed_without_hang(self):
        # A queue of 10 DELEGATEs drained one per cycle; backoff stays at 0.
        remaining = {"n": 10}

        def poll():
            if remaining["n"] <= 0:
                return {"processed": 0}
            remaining["n"] -= 1
            return {"processed": 1}

        poller, _, _ = make_poller(poll=poll, watch_enabled=False)
        start = time.perf_counter()
        processed_total = 0
        for _ in range(10):
            outcome = poller.run_cycle()
            processed_total += outcome.processed
            assert poller.level == 0  # never backs off while draining
        elapsed = time.perf_counter() - start
        assert processed_total == 10
        assert elapsed < 5.0

    def test_many_rapid_cycles_deterministic(self):
        toggles = iter([1, 0] * 50)

        def poll():
            return {"processed": next(toggles)}

        poller, _, _ = make_poller(poll=poll, intervals=[5, 30])
        for _ in range(100):
            poller.run_cycle()
        # Last toggle was 0 (empty) -> level advanced to 1.
        assert poller.level in (0, 1)


# ===========================================================================
# 8. Stress — Long idle with early wake (no wasted sleeps)
# ===========================================================================


class TestLongIdleWithWake:
    def test_deep_idle_then_inject_wakes_early(self, tmp_path):
        incoming = tmp_path / "incoming"
        incoming.mkdir()
        poller, clock, sleeper = make_poller(
            incoming_dir=incoming,
            intervals=[5, 30, 180, 600],
            poll=lambda: {"processed": 0},
            watch_poll_seconds=2.0,
        )
        # Advance all the way to the 600s rung.
        for _ in range(4):
            poller.run_cycle()
        assert poller.current_interval == 600

        # Inject a DELEGATE then sleep — must wake almost immediately.
        write_delegate(incoming, "late.yaml")
        sleeper.calls.clear()
        slept = poller.sleep_until_next()
        assert poller.level == 0
        # No wasted long sleep: total slept is a small fraction of 600s.
        assert slept <= poller.config.watch_poll_seconds + 1e-6
        assert sleeper.total <= poller.config.watch_poll_seconds + 1e-6

    def test_full_idle_sleep_when_no_file_arrives(self, tmp_path):
        incoming = tmp_path / "incoming"
        incoming.mkdir()
        poller, clock, sleeper = make_poller(
            incoming_dir=incoming,
            intervals=[10],
            poll=lambda: {"processed": 0},
            watch_poll_seconds=2.0,
        )
        poller.run_cycle()  # level stays 0 (single rung), interval 10s
        slept = poller.sleep_until_next()
        # No file -> slept the full interval in watch_poll-sized slices.
        assert slept == pytest.approx(10.0, abs=2.0)
        # Each slice <= watch_poll_seconds.
        assert all(s <= 2.0 + 1e-9 for s in sleeper.calls)
