"""Tests for OpenCode harness idle-loop integration (Phase G-1).

Covers:
1. Idle detection (activity tracking, threshold, is_idle).
2. check_and_poll gating (no-op when active, polls when idle).
3. Subprocess invocation + JSON parsing (mocked subprocess.run).
4. Graceful handling of timeouts, scheduler errors, lock-skip, empty queue.
5. Real-subprocess E2E with a fake scheduler script emitting JSON.
6. Config validation of the `idle_loop` block.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path
from unittest import mock

import pytest

from src.harnesses.opencode.idle_loop import (
    OpenCodeIdleLoop,
    IdlePollResult,
    DEFAULT_IDLE_THRESHOLD_SECONDS,
)
from src.harnesses.opencode.config_validator import validate_text, Severity


# ---------------------------------------------------------------------------
# Controllable fake clock
# ---------------------------------------------------------------------------


class FakeClock:
    """Monotonic clock whose value advances only when told to."""

    def __init__(self, start: float = 1000.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def _completed(stdout: str, returncode: int = 0, stderr: str = ""):
    return subprocess.CompletedProcess(
        args=["python", "scheduler"], returncode=returncode,
        stdout=stdout, stderr=stderr,
    )


# ---------------------------------------------------------------------------
# 1. Idle detection
# ---------------------------------------------------------------------------


def test_default_threshold_is_in_design_window():
    assert 180 <= DEFAULT_IDLE_THRESHOLD_SECONDS <= 300


def test_not_idle_immediately_after_activity():
    clk = FakeClock()
    loop = OpenCodeIdleLoop(idle_threshold_seconds=180, clock=clk)
    assert loop.is_idle() is False
    assert loop.idle_seconds() == 0


def test_becomes_idle_after_threshold():
    clk = FakeClock()
    loop = OpenCodeIdleLoop(idle_threshold_seconds=180, clock=clk)
    clk.advance(179)
    assert loop.is_idle() is False
    clk.advance(1)  # exactly at threshold
    assert loop.is_idle() is True


def test_on_activity_resets_idle_timer():
    clk = FakeClock()
    loop = OpenCodeIdleLoop(idle_threshold_seconds=180, clock=clk)
    clk.advance(200)
    assert loop.is_idle() is True
    loop.on_activity()
    assert loop.is_idle() is False
    assert loop.idle_seconds() == 0


# ---------------------------------------------------------------------------
# 2. check_and_poll gating
# ---------------------------------------------------------------------------


def test_check_and_poll_noop_when_active():
    clk = FakeClock()
    loop = OpenCodeIdleLoop(idle_threshold_seconds=180, clock=clk)
    with mock.patch.object(loop, "poll_now") as poll:
        result = loop.check_and_poll()
    poll.assert_not_called()
    assert result.polled is False


def test_check_and_poll_invokes_when_idle_and_resets_clock():
    clk = FakeClock()
    loop = OpenCodeIdleLoop(idle_threshold_seconds=180, clock=clk)
    clk.advance(180)
    with mock.patch.object(
        loop, "poll_now",
        return_value=IdlePollResult(polled=True, processed=2),
    ) as poll:
        result = loop.check_and_poll()
    poll.assert_called_once()
    assert result.processed == 2
    # Clock reset → no longer idle right after polling.
    assert loop.is_idle() is False


# ---------------------------------------------------------------------------
# 3. Subprocess invocation + JSON parsing
# ---------------------------------------------------------------------------


def test_poll_now_builds_expected_command():
    loop = OpenCodeIdleLoop(session_id="sess-123", poll_budget_seconds=30)
    payload = json.dumps({"processed": 0, "failed": 0, "queue_empty": True,
                          "lock_skipped": False, "errors": []})
    with mock.patch("subprocess.run", return_value=_completed(payload)) as run:
        loop.poll_now()
    # Index form (call_args[0]=positional, call_args[1]=kwargs) works on 3.7+.
    cmd = run.call_args[0][0]
    assert "--poll-once" in cmd
    assert "--session-id" in cmd and "sess-123" in cmd
    assert "--timeout" in cmd and "30" in cmd
    # Harness attribution defaults to opencode.
    env = run.call_args[1]["env"]
    assert env["AGENTIC_HARNESS"] == "opencode"


def test_poll_now_parses_processed_result():
    loop = OpenCodeIdleLoop()
    payload = json.dumps({"processed": 3, "failed": 1, "queue_empty": False,
                          "lock_skipped": False, "errors": []})
    with mock.patch("subprocess.run", return_value=_completed(payload)):
        result = loop.poll_now()
    assert result.polled is True
    assert result.processed == 3
    assert result.failed == 1
    assert result.lock_skipped is False
    assert result.error is None


def test_poll_now_handles_lock_skip():
    loop = OpenCodeIdleLoop()
    payload = json.dumps({"processed": 0, "failed": 0, "queue_empty": False,
                          "lock_skipped": True, "errors": []})
    with mock.patch("subprocess.run", return_value=_completed(payload)):
        result = loop.poll_now()
    assert result.lock_skipped is True
    assert result.processed == 0


def test_poll_now_ignores_leading_log_lines_before_json():
    loop = OpenCodeIdleLoop()
    payload = json.dumps({"processed": 1, "failed": 0, "queue_empty": False,
                          "lock_skipped": False, "errors": []})
    noisy = "INFO some log line\nWARN another\n" + payload
    with mock.patch("subprocess.run", return_value=_completed(noisy)):
        result = loop.poll_now()
    assert result.processed == 1


# ---------------------------------------------------------------------------
# 4. Graceful failure handling
# ---------------------------------------------------------------------------


def test_poll_now_handles_timeout_gracefully():
    loop = OpenCodeIdleLoop(skill_timeout_seconds=5, poll_budget_seconds=2)
    with mock.patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="scheduler", timeout=5),
    ):
        result = loop.poll_now()
    assert result.polled is True
    assert result.timed_out is True
    assert result.error == "timeout"
    assert result.processed == 0


def test_poll_now_handles_scheduler_errors_field():
    loop = OpenCodeIdleLoop()
    payload = json.dumps({
        "processed": 0, "failed": 1, "queue_empty": False, "lock_skipped": False,
        "errors": [{"stage": "process", "message": "boom"}],
    })
    with mock.patch("subprocess.run", return_value=_completed(payload, returncode=1)):
        result = loop.poll_now()
    assert result.failed == 1
    assert result.error == "boom"


def test_poll_now_handles_empty_output():
    loop = OpenCodeIdleLoop()
    with mock.patch("subprocess.run", return_value=_completed("", returncode=1,
                                                              stderr="traceback")):
        result = loop.poll_now()
    assert result.polled is True
    assert result.processed == 0
    assert result.error is not None and "no-result" in result.error


def test_poll_now_handles_launch_failure():
    loop = OpenCodeIdleLoop()
    with mock.patch("subprocess.run", side_effect=OSError("exec format error")):
        result = loop.poll_now()
    assert result.polled is True
    assert "exec format error" in (result.error or "")


# ---------------------------------------------------------------------------
# 5. Real-subprocess E2E with a fake scheduler script
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_scheduler(tmp_path: Path) -> Path:
    """A standalone script that mimics orchestrator_scheduler --poll-once JSON."""
    script = tmp_path / "fake_scheduler.py"
    script.write_text(textwrap.dedent(
        """
        import json, sys
        # Emit a realistic poll-once JSON payload on the final stdout line.
        print("INFO some startup log to stderr-ish noise")
        print(json.dumps({
            "processed": 2,
            "failed": 0,
            "queue_empty": False,
            "session_id": "e2e-session",
            "harness": "opencode",
            "lock_skipped": False,
            "errors": [],
        }))
        sys.exit(0)
        """
    ))
    return script


def test_e2e_real_subprocess_processes_delegates(fake_scheduler: Path):
    loop = OpenCodeIdleLoop(
        session_id="e2e-session",
        scheduler_script=fake_scheduler,
        python_executable=sys.executable,
        skill_timeout_seconds=10,
        poll_budget_seconds=5,
    )
    result = loop.poll_now()
    assert result.polled is True
    assert result.processed == 2
    assert result.failed == 0
    assert result.lock_skipped is False
    assert result.error is None
    assert result.duration_seconds >= 0


def test_e2e_idle_trigger_to_poll(fake_scheduler: Path):
    clk = FakeClock()
    loop = OpenCodeIdleLoop(
        idle_threshold_seconds=180,
        session_id="e2e-session",
        scheduler_script=fake_scheduler,
        skill_timeout_seconds=10,
        poll_budget_seconds=5,
        clock=clk,
    )
    # Active → no poll.
    assert loop.check_and_poll().polled is False
    # Go idle → real subprocess runs.
    clk.advance(180)
    result = loop.check_and_poll()
    assert result.polled is True
    assert result.processed == 2


# ---------------------------------------------------------------------------
# 6. Config validation of the idle_loop block
# ---------------------------------------------------------------------------


VALID_CONFIG = """// agentic-engineers OpenCode configuration (test fixture)
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["AGENTS.md"],
  "default_agent": "orchestrator",
  "model": "anthropic/claude-haiku-4-5",
  "idle_loop": {
    "enabled": true,
    "interval_seconds": 180,
    "action": "invoke_skill",
    "skill": "orchestrator-scheduler",
    "args": ["--poll-once"]
  },
  "permission": { "read": "allow" }
}
"""


def test_idle_loop_config_is_valid_and_not_unknown_key():
    result = validate_text(VALID_CONFIG)
    # No errors, and idle_loop must NOT be flagged as an unknown top-level key.
    assert result.ok, [e.message for e in result.errors]
    assert all(
        "idle_loop" not in e.message.lower() or "unknown" not in e.message.lower()
        for e in result.warnings
    )


def test_idle_loop_rejects_bad_interval():
    bad = VALID_CONFIG.replace('"interval_seconds": 180', '"interval_seconds": -5')
    result = validate_text(bad)
    assert not result.ok
    assert any("interval_seconds" in (e.path or "") for e in result.errors)


def test_idle_loop_warns_on_too_low_interval():
    low = VALID_CONFIG.replace('"interval_seconds": 180', '"interval_seconds": 5')
    result = validate_text(low)
    assert any("interval_seconds" in (e.path or "") for e in result.warnings)


def test_idle_loop_rejects_non_object():
    bad = VALID_CONFIG.replace(
        '"idle_loop": {\n    "enabled": true,\n    "interval_seconds": 180,\n'
        '    "action": "invoke_skill",\n    "skill": "orchestrator-scheduler",\n'
        '    "args": ["--poll-once"]\n  }',
        '"idle_loop": "yes"',
    )
    result = validate_text(bad)
    assert not result.ok
    assert any("idle_loop" in (e.path or "") for e in result.errors)
