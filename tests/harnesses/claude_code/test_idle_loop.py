"""
Tests for the Claude Code harness idle-loop (Phase G-1).

Covers:
  - Config parsing from settings.json (idle_loop section, defaults, missing file)
  - Idle detection state machine (activity, task-in-progress, queue-empty, threshold)
  - Skill invocation on idle (via injected invoker)
  - Non-fatal error/timeout handling (no exceptions escape into the harness)
  - End-to-end: real subprocess invocation of orchestrator-scheduler --poll-once
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from src.harnesses.claude_code.idle_loop import (
    ClaudeIdleLoop,
    IdleLoopConfig,
    DEFAULT_INTERVAL_SECONDS,
)


# ---------------------------------------------------------------------------
# Fake clock for deterministic idle-duration testing
# ---------------------------------------------------------------------------


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------


class TestIdleLoopConfig:
    def test_from_dict_full(self):
        cfg = IdleLoopConfig.from_dict({
            "enabled": True,
            "interval_seconds": 180,
            "action": "invoke_skill",
            "skill": "orchestrator-scheduler",
            "args": ["--poll-once"],
        })
        assert cfg.enabled is True
        assert cfg.interval_seconds == 180
        assert cfg.skill == "orchestrator-scheduler"
        assert cfg.args == ["--poll-once"]

    def test_from_dict_defaults_on_empty(self):
        cfg = IdleLoopConfig.from_dict({})
        assert cfg.enabled is True
        assert cfg.interval_seconds == DEFAULT_INTERVAL_SECONDS
        assert cfg.args == ["--poll-once"]

    def test_from_dict_none(self):
        cfg = IdleLoopConfig.from_dict(None)
        assert cfg.enabled is True

    def test_from_dict_ignores_unknown_keys(self):
        cfg = IdleLoopConfig.from_dict({"enabled": True, "future_key": "x"})
        assert cfg.enabled is True

    def test_from_settings_reads_file(self, tmp_path):
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({
            "model": "haiku",
            "idle_loop": {"enabled": True, "interval_seconds": 60},
        }))
        loop = ClaudeIdleLoop.from_settings(settings)
        assert loop.config.interval_seconds == 60

    def test_from_settings_missing_file_defaults(self, tmp_path):
        loop = ClaudeIdleLoop.from_settings(tmp_path / "nope.json")
        assert loop.config.enabled is True
        assert loop.config.interval_seconds == DEFAULT_INTERVAL_SECONDS

    def test_from_settings_malformed_json_defaults(self, tmp_path):
        settings = tmp_path / "settings.json"
        settings.write_text("{ not json")
        loop = ClaudeIdleLoop.from_settings(settings)
        assert loop.config.enabled is True

    def test_dist_settings_has_idle_loop_block(self):
        """The shipped dist/claude/settings.json must carry the idle_loop config."""
        repo_root = Path(__file__).resolve().parents[3]
        data = json.loads((repo_root / "dist" / "claude" / "settings.json").read_text())
        assert "idle_loop" in data
        il = data["idle_loop"]
        assert il["enabled"] is True
        assert il["skill"] == "orchestrator-scheduler"
        assert il["args"] == ["--poll-once"]


# ---------------------------------------------------------------------------
# Idle detection state machine
# ---------------------------------------------------------------------------


class TestIdleDetection:
    def _loop(self, clock, calls):
        def invoker(args, timeout):
            calls.append((args, timeout))
            return {"processed": 0, "failed": 0, "queue_empty": True,
                    "lock_skipped": False, "errors": []}

        cfg = IdleLoopConfig(enabled=True, interval_seconds=180)
        return ClaudeIdleLoop(config=cfg, invoker=invoker, clock=clock)

    def test_not_idle_before_threshold(self):
        clock = FakeClock()
        calls = []
        loop = self._loop(clock, calls)
        clock.advance(179)
        assert loop.is_idle(message_queue_empty=True) is False
        assert loop.check_idle(message_queue_empty=True) is None
        assert calls == []

    def test_idle_after_threshold_invokes(self):
        clock = FakeClock()
        calls = []
        loop = self._loop(clock, calls)
        clock.advance(180)
        assert loop.is_idle(message_queue_empty=True) is True
        result = loop.check_idle(message_queue_empty=True)
        assert result is not None
        assert len(calls) == 1
        assert calls[0][0] == ["--poll-once"]

    def test_activity_resets_timer(self):
        clock = FakeClock()
        calls = []
        loop = self._loop(clock, calls)
        clock.advance(200)
        loop.on_user_activity()  # reset
        assert loop.is_idle() is False
        clock.advance(179)
        assert loop.is_idle() is False
        clock.advance(1)
        assert loop.is_idle() is True

    def test_task_in_progress_blocks_idle(self):
        clock = FakeClock()
        calls = []
        loop = self._loop(clock, calls)
        loop.set_task_in_progress(True)
        clock.advance(300)
        assert loop.is_idle() is False
        assert loop.check_idle() is None
        assert calls == []

    def test_nonempty_message_queue_blocks_idle(self):
        clock = FakeClock()
        calls = []
        loop = self._loop(clock, calls)
        clock.advance(300)
        assert loop.is_idle(message_queue_empty=False) is False
        assert loop.check_idle(message_queue_empty=False) is None
        assert calls == []

    def test_disabled_never_idle(self):
        clock = FakeClock()
        calls = []
        cfg = IdleLoopConfig(enabled=False, interval_seconds=180)
        loop = ClaudeIdleLoop(
            config=cfg,
            invoker=lambda a, t: calls.append((a, t)),
            clock=clock,
        )
        clock.advance(10_000)
        assert loop.is_idle() is False
        assert loop.check_idle() is None
        assert calls == []

    def test_poll_resets_idle_timer(self):
        """After a successful poll, the loop should not immediately re-poll."""
        clock = FakeClock()
        calls = []
        loop = self._loop(clock, calls)
        clock.advance(180)
        loop.check_idle()
        assert len(calls) == 1
        # Immediately after, not idle again until another full interval.
        assert loop.is_idle() is False
        clock.advance(180)
        loop.check_idle()
        assert len(calls) == 2


# ---------------------------------------------------------------------------
# Error / timeout handling — must never raise into the harness
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def _ready_loop(self, invoker, clock):
        cfg = IdleLoopConfig(enabled=True, interval_seconds=180)
        loop = ClaudeIdleLoop(config=cfg, invoker=invoker, clock=clock)
        clock.advance(180)
        return loop

    def test_timeout_returns_error_envelope(self):
        clock = FakeClock()

        def invoker(args, timeout):
            raise subprocess.TimeoutExpired(cmd="scheduler", timeout=timeout)

        loop = self._ready_loop(invoker, clock)
        result = loop.check_idle()
        assert result["failed"] == 1
        assert result["errors"][0]["stage"] == "timeout"

    def test_generic_exception_returns_error_envelope(self):
        clock = FakeClock()

        def invoker(args, timeout):
            raise RuntimeError("boom")

        loop = self._ready_loop(invoker, clock)
        result = loop.check_idle()
        assert result["failed"] == 1
        assert result["errors"][0]["stage"] == "invoke"

    def test_scheduler_error_array_logged_not_raised(self):
        clock = FakeClock()

        def invoker(args, timeout):
            return {"processed": 0, "failed": 1, "lock_skipped": False,
                    "errors": [{"stage": "process", "message": "x"}]}

        loop = self._ready_loop(invoker, clock)
        result = loop.check_idle()  # should not raise
        assert result["errors"]


# ---------------------------------------------------------------------------
# Subprocess invoker: JSON parsing
# ---------------------------------------------------------------------------


class TestSubprocessInvoker:
    def test_parses_trailing_json_line(self, monkeypatch, tmp_path):
        loop = ClaudeIdleLoop(repo_root=tmp_path)

        class _Completed:
            returncode = 0
            stdout = '[log] some line\n{"processed": 2, "failed": 0, "errors": []}'
            stderr = ""

        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Completed())
        result = loop._subprocess_invoker(["--poll-once"], 35)
        assert result["processed"] == 2

    def test_empty_stdout_yields_error_envelope(self, monkeypatch, tmp_path):
        loop = ClaudeIdleLoop(repo_root=tmp_path)

        class _Completed:
            returncode = 1
            stdout = ""
            stderr = "exploded"

        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Completed())
        result = loop._subprocess_invoker(["--poll-once"], 35)
        assert result["errors"][0]["stage"] == "invoke"

    def test_unparseable_json_yields_error_envelope(self, monkeypatch, tmp_path):
        loop = ClaudeIdleLoop(repo_root=tmp_path)

        class _Completed:
            returncode = 0
            stdout = "not json at all"
            stderr = ""

        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Completed())
        result = loop._subprocess_invoker(["--poll-once"], 35)
        assert result["errors"][0]["stage"] == "parse"


# ---------------------------------------------------------------------------
# End-to-end: real subprocess -> orchestrator-scheduler --poll-once
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_e2e_empty_queue_via_subprocess(self, tmp_path, monkeypatch):
        """
        Drive the real scheduler subprocess against an empty session queue and
        verify the harness receives a clean JSON result (no crash, no error).
        """
        repo_root = Path(__file__).resolve().parents[3]

        # Point the queue root at a temp HOME so we don't touch real queues.
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("CLAUDE_SESSION_ID", "idle-e2e-session")
        monkeypatch.setenv("AGENTIC_HARNESS", "claude")

        cfg = IdleLoopConfig(enabled=True, interval_seconds=0)
        loop = ClaudeIdleLoop(config=cfg, repo_root=repo_root)

        result = loop.check_idle(message_queue_empty=True)
        assert result is not None, "idle loop should have invoked the scheduler"
        # Empty queue -> processed 0, no errors, queue_empty True.
        assert result.get("errors") == [], result
        assert result.get("processed") == 0
        assert result.get("queue_empty") is True
        assert result.get("session_id") == "idle-e2e-session"
