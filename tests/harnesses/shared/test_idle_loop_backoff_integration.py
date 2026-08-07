"""Phase G-2 — Idle-loop ↔ BackoffPoller integration tests (all 3 harnesses).

The shared ``BackoffPoller`` is unit-tested in ``test_backoff_poller.py``. This
module verifies the *wiring* inside each harness idle loop:

  * backoff progression: empty polls advance the ladder, work resets it;
  * ``current_interval`` honours the G-1 initial threshold then follows the
    ladder once the queue is seen empty;
  * file-watch wake-early: a new DELEGATE in ``incoming/`` short-circuits the
    idle threshold and resets backoff;
  * error recovery: scheduler timeouts/exceptions are non-fatal and advance
    (never reset) the backoff level.

All three harnesses (Claude, OpenCode, Copilot) are driven through their own
public interfaces with injected clocks / invokers so the tests are deterministic.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src.harnesses.shared.backoff_poller import BackoffConfig
from src.harnesses.claude_code.idle_loop import ClaudeIdleLoop, IdleLoopConfig
from src.harnesses.opencode.idle_loop import OpenCodeIdleLoop
from src.harnesses.copilot_cli.idle_loop import CopilotIdleLoop


# ---------------------------------------------------------------------------
# Deterministic clock
# ---------------------------------------------------------------------------


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def _g2_config(intervals=(5, 30, 180, 600)) -> BackoffConfig:
    return BackoffConfig(
        enabled=True,
        backoff_intervals=list(intervals),
        watch_enabled=True,
        watch_poll_seconds=0.01,
    )


# ===========================================================================
# Claude Code
# ===========================================================================


class TestClaudeBackoff:
    def _loop(self, clock, results, *, intervals=(5, 30, 180, 600), interval_seconds=180,
              incoming_dir=None):
        """Build a Claude loop whose invoker returns successive ``results``."""
        seq = iter(results)

        def invoker(args, timeout):
            try:
                return next(seq)
            except StopIteration:
                return {"processed": 0, "queue_empty": True, "errors": []}

        cfg = IdleLoopConfig(
            enabled=True,
            interval_seconds=interval_seconds,
            backoff_intervals=list(intervals),
            raw={"enabled": True, "backoff_intervals": list(intervals),
                 "watch_enabled": incoming_dir is not None, "watch_poll_seconds": 0.01},
        )
        return ClaudeIdleLoop(config=cfg, invoker=invoker, clock=clock,
                              incoming_dir=incoming_dir)

    def test_initial_threshold_is_interval_seconds(self):
        clock = FakeClock()
        loop = self._loop(clock, [], interval_seconds=180)
        # Before any poll, level 0 -> uses configured interval, not ladder rung.
        assert loop.current_interval() == 180
        assert loop.backoff_level() == 0

    def test_empty_poll_advances_backoff(self):
        clock = FakeClock()
        loop = self._loop(clock, [
            {"processed": 0, "queue_empty": True, "errors": []},
            {"processed": 0, "queue_empty": True, "errors": []},
        ])
        clock.advance(180)
        loop.check_idle()                       # empty -> level 1 (30s)
        assert loop.backoff_level() == 1
        assert loop.current_interval() == 30
        clock.advance(30)
        loop.check_idle()                       # empty -> level 2 (180s)
        assert loop.backoff_level() == 2
        assert loop.current_interval() == 180

    def test_processed_resets_backoff(self):
        clock = FakeClock()
        loop = self._loop(clock, [
            {"processed": 0, "queue_empty": True, "errors": []},
            {"processed": 2, "queue_empty": False, "errors": []},
        ])
        clock.advance(180)
        loop.check_idle()                       # empty -> level 1
        assert loop.backoff_level() == 1
        clock.advance(30)
        loop.check_idle()                       # processed 2 -> reset
        assert loop.backoff_level() == 0
        assert loop.current_interval() == 180   # back to initial threshold

    def test_error_is_non_fatal_and_advances(self):
        clock = FakeClock()

        def invoker(args, timeout):
            raise RuntimeError("boom")

        cfg = IdleLoopConfig(enabled=True, interval_seconds=180,
                             backoff_intervals=[5, 30, 180, 600],
                             raw={"backoff_intervals": [5, 30, 180, 600]})
        loop = ClaudeIdleLoop(config=cfg, invoker=invoker, clock=clock)
        clock.advance(180)
        result = loop.check_idle()              # must not raise
        assert result["errors"]                 # error envelope returned
        assert loop.backoff_level() == 1        # advanced, not reset

    def test_file_watch_wakes_early(self, tmp_path):
        clock = FakeClock()
        incoming = tmp_path / "incoming"
        incoming.mkdir()
        loop = self._loop(clock, [
            {"processed": 0, "queue_empty": True, "errors": []},
        ], incoming_dir=incoming)
        # Drive into deep backoff first so the threshold is large.
        clock.advance(180)
        loop.check_idle()                       # empty -> level 1
        assert loop.backoff_level() == 1
        # Not enough time elapsed for level-1 (30s) threshold...
        assert loop.is_idle() is False
        # ...but a new DELEGATE arriving wakes us early and resets backoff.
        (incoming / "task-new.yaml").write_text("handoff_type: DELEGATE\n")
        assert loop.is_idle() is True
        assert loop.backoff_level() == 0


# ===========================================================================
# OpenCode
# ===========================================================================


class TestOpenCodeBackoff:
    def _loop(self, clock, results, *, incoming_dir=None, threshold=180):
        seq = iter(results)

        def fake_run(cmd, **kwargs):
            try:
                payload = next(seq)
            except StopIteration:
                payload = {"processed": 0, "queue_empty": True}
            import json as _json
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout=_json.dumps(payload), stderr="")

        loop = OpenCodeIdleLoop(
            idle_threshold_seconds=threshold,
            clock=clock,
            backoff_config=_g2_config(),
            incoming_dir=incoming_dir,
        )
        loop._fake_run = fake_run  # type: ignore[attr-defined]
        return loop

    def test_initial_threshold_then_ladder(self, monkeypatch):
        clock = FakeClock()
        loop = self._loop(clock, [
            {"processed": 0, "queue_empty": True},
            {"processed": 0, "queue_empty": True},
        ])
        monkeypatch.setattr(subprocess, "run", loop._fake_run)
        assert loop.current_interval() == 180      # level 0 -> initial threshold
        clock.advance(180)
        loop.check_and_poll()                       # empty -> level 1
        assert loop.backoff_level() == 1
        assert loop.current_interval() == 30

    def test_processed_resets(self, monkeypatch):
        clock = FakeClock()
        loop = self._loop(clock, [
            {"processed": 0, "queue_empty": True},
            {"processed": 1, "queue_empty": False},
        ])
        monkeypatch.setattr(subprocess, "run", loop._fake_run)
        clock.advance(180)
        loop.check_and_poll()                       # empty -> level 1
        assert loop.backoff_level() == 1
        clock.advance(30)
        loop.check_and_poll()                       # processed -> reset
        assert loop.backoff_level() == 0

    def test_timeout_is_non_fatal_and_advances(self, monkeypatch):
        clock = FakeClock()
        loop = self._loop(clock, [])

        def boom(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=1)

        monkeypatch.setattr(subprocess, "run", boom)
        clock.advance(180)
        result = loop.check_and_poll()              # must not raise
        assert result.timed_out is True
        assert loop.backoff_level() == 1            # advanced

    def test_file_watch_wakes_early(self, tmp_path, monkeypatch):
        clock = FakeClock()
        incoming = tmp_path / "incoming"
        incoming.mkdir()
        loop = self._loop(clock, [
            {"processed": 0, "queue_empty": True},
        ], incoming_dir=incoming)
        monkeypatch.setattr(subprocess, "run", loop._fake_run)
        clock.advance(180)
        loop.check_and_poll()                       # empty -> level 1
        assert loop.backoff_level() == 1
        assert loop.is_idle() is False              # 30s not elapsed
        (incoming / "task-new.yaml").write_text("handoff_type: DELEGATE\n")
        assert loop.is_idle() is True
        assert loop.backoff_level() == 0


# ===========================================================================
# Copilot CLI
# ===========================================================================


class TestCopilotBackoff:
    def _loop(self, results, *, incoming_dir=None, threshold=180):
        seq = iter(results)

        def fake_run(cmd, **kwargs):
            try:
                payload = next(seq)
            except StopIteration:
                payload = {"processed": 0, "queue_empty": True}
            import json as _json
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout=_json.dumps(payload), stderr="")

        loop = CopilotIdleLoop(
            idle_threshold_seconds=threshold,
            backoff_config=_g2_config(),
            incoming_dir=incoming_dir,
        )
        loop._fake_run = fake_run  # type: ignore[attr-defined]
        return loop

    def test_initial_threshold_then_ladder(self, monkeypatch):
        loop = self._loop([
            {"processed": 0, "queue_empty": True},
            {"processed": 0, "queue_empty": True},
        ])
        monkeypatch.setattr(subprocess, "run", loop._fake_run)
        assert loop.current_interval() == 180
        loop.check_idle(force=True)                 # empty -> level 1
        assert loop.backoff_level() == 1
        assert loop.current_interval() == 30

    def test_processed_resets(self, monkeypatch):
        loop = self._loop([
            {"processed": 0, "queue_empty": True},
            {"processed": 3, "queue_empty": False},
        ])
        monkeypatch.setattr(subprocess, "run", loop._fake_run)
        loop.check_idle(force=True)                 # empty -> level 1
        assert loop.backoff_level() == 1
        loop.check_idle(force=True)                 # processed -> reset
        assert loop.backoff_level() == 0

    def test_timeout_is_non_fatal_and_advances(self, monkeypatch):
        loop = self._loop([])

        def boom(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=1)

        monkeypatch.setattr(subprocess, "run", boom)
        result = loop.check_idle(force=True)        # must not raise
        assert result.errors                        # captured as error
        assert loop.backoff_level() == 1            # advanced

    def test_file_watch_wakes_early(self, tmp_path, monkeypatch):
        incoming = tmp_path / "incoming"
        incoming.mkdir()
        loop = self._loop([
            {"processed": 0, "queue_empty": True},
        ], incoming_dir=incoming)
        monkeypatch.setattr(subprocess, "run", loop._fake_run)
        loop.check_idle(force=True)                 # empty -> level 1
        assert loop.backoff_level() == 1
        # mark_done resets the activity timer; not enough idle for level-1 (30s).
        loop.mark_done()
        assert loop.is_idle() is False
        (incoming / "task-new.yaml").write_text("handoff_type: DELEGATE\n")
        assert loop.is_idle() is True
        assert loop.backoff_level() == 0


# ===========================================================================
# Cross-harness consistency
# ===========================================================================


def test_all_three_expose_backoff_api():
    """Every harness loop exposes the same Phase G-2 backoff surface."""
    claude = ClaudeIdleLoop(config=IdleLoopConfig())
    opencode = OpenCodeIdleLoop(backoff_config=_g2_config())
    copilot = CopilotIdleLoop(backoff_config=_g2_config())
    for loop in (claude, opencode, copilot):
        assert hasattr(loop, "current_interval")
        assert hasattr(loop, "backoff_level")
        assert hasattr(loop, "run_backoff_cycle")
        assert hasattr(loop, "sleep_until_next")
        assert loop.backoff_level() == 0
