#!/usr/bin/env python3
"""
Tests for the Copilot CLI idle-loop integration (Phase G-1).

Covers:
  - Idle detection (busy / threshold / activity reset)
  - Scheduler JSON parsing (incl. log-prefixed stdout)
  - Lock-skip handling (multi-harness coordination)
  - Timeout + spawn-failure graceful degradation
  - settings.json idle_loop config
  - End-to-end: real scheduler subprocess against an empty temp queue
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from src.harnesses.copilot_cli.idle_loop import (
    CopilotIdleLoop,
    IdlePollResult,
    main,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SETTINGS_JSON = REPO_ROOT / "dist" / "copilot" / "settings.json"
IDLE_LOOP_MODULE = REPO_ROOT / "src" / "harnesses" / "copilot_cli" / "idle_loop.py"


def _completed(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(
        args=["x"], returncode=returncode, stdout=stdout, stderr=stderr
    )


# --------------------------------------------------------------------------
# Idle detection
# --------------------------------------------------------------------------

def test_busy_is_never_idle():
    loop = CopilotIdleLoop(idle_threshold_seconds=0)
    loop.mark_busy()
    assert loop.is_idle() is False


def test_idle_after_threshold():
    loop = CopilotIdleLoop(idle_threshold_seconds=0)
    loop.mark_done()
    assert loop.is_idle() is True


def test_not_idle_before_threshold():
    loop = CopilotIdleLoop(idle_threshold_seconds=10_000)
    loop.notify_activity()
    assert loop.is_idle() is False


def test_check_idle_skips_when_not_idle():
    loop = CopilotIdleLoop(idle_threshold_seconds=10_000)
    loop.notify_activity()
    result = loop.check_idle()
    assert result.polled is False
    assert result.skip_reason == "not_idle"


def test_scheduler_timeout_clamped_below_block():
    loop = CopilotIdleLoop(block_seconds=10, scheduler_timeout_seconds=30)
    assert loop.scheduler_timeout_seconds == 9


# --------------------------------------------------------------------------
# JSON parsing / scheduler invocation (mocked subprocess)
# --------------------------------------------------------------------------

def test_parses_clean_json():
    loop = CopilotIdleLoop(idle_threshold_seconds=0)
    payload = {
        "processed": 3, "failed": 0, "duration_ms": 1500,
        "queue_empty": False, "lock_skipped": False, "errors": [],
    }
    with mock.patch("subprocess.run", return_value=_completed(json.dumps(payload))):
        result = loop.check_idle(force=True)
    assert result.polled is True
    assert result.processed == 3
    assert result.failed == 0
    assert result.lock_skipped is False
    assert result.errors == []


def test_parses_json_with_leading_log_lines():
    loop = CopilotIdleLoop(idle_threshold_seconds=0)
    payload = {"processed": 1, "failed": 0, "lock_skipped": False, "errors": []}
    stdout = (
        "[2026-06-26] orchestrator — INFO: Starting queue poll...\n"
        "[2026-06-26] orchestrator — INFO: done\n"
        + json.dumps(payload)
        + "\n"
    )
    with mock.patch("subprocess.run", return_value=_completed(stdout)):
        result = loop.check_idle(force=True)
    assert result.processed == 1
    assert result.errors == []


def test_lock_skip_is_not_an_error():
    loop = CopilotIdleLoop(idle_threshold_seconds=0)
    payload = {
        "processed": 0, "failed": 0, "lock_skipped": True,
        "queue_empty": True, "errors": [],
    }
    with mock.patch("subprocess.run", return_value=_completed(json.dumps(payload))):
        result = loop.check_idle(force=True)
    assert result.lock_skipped is True
    assert result.processed == 0
    assert result.errors == []


def test_timeout_degrades_gracefully():
    loop = CopilotIdleLoop(idle_threshold_seconds=0, block_seconds=5)
    with mock.patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="x", timeout=5),
    ):
        result = loop.check_idle(force=True)
    assert result.polled is True
    assert result.errors and result.errors[0]["stage"] == "timeout"
    # Harness must not crash — exception is swallowed.


def test_spawn_failure_degrades_gracefully():
    loop = CopilotIdleLoop(idle_threshold_seconds=0)
    with mock.patch("subprocess.run", side_effect=OSError("no python")):
        result = loop.check_idle(force=True)
    assert result.polled is True
    assert result.errors and result.errors[0]["stage"] == "spawn"


def test_no_json_output_is_parse_error():
    loop = CopilotIdleLoop(idle_threshold_seconds=0)
    with mock.patch(
        "subprocess.run",
        return_value=_completed(stdout="garbage\n", stderr="boom", returncode=2),
    ):
        result = loop.check_idle(force=True)
    assert result.polled is True
    assert result.errors and result.errors[0]["stage"] == "parse"


def test_command_includes_poll_once_and_harness_env():
    loop = CopilotIdleLoop(idle_threshold_seconds=0, session_id="sess-1")
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs.get("env", {})
        return _completed(json.dumps({"processed": 0, "errors": []}))

    with mock.patch("subprocess.run", side_effect=fake_run):
        loop.check_idle(force=True)

    assert "--poll-once" in captured["cmd"]
    assert "--session-id" in captured["cmd"]
    assert "sess-1" in captured["cmd"]
    assert any(str(c).endswith("orchestrator_scheduler.py") for c in captured["cmd"])
    assert captured["env"].get("AGENTIC_HARNESS") == "copilot"


def test_idle_timer_resets_after_poll():
    loop = CopilotIdleLoop(idle_threshold_seconds=0)
    with mock.patch(
        "subprocess.run",
        return_value=_completed(json.dumps({"processed": 0, "errors": []})),
    ):
        loop.check_idle(force=True)
    # Immediately after polling, idle timer was reset, so a 5s threshold check
    # should now report not-idle.
    loop.idle_threshold_seconds = 5
    assert loop.is_idle() is False


# --------------------------------------------------------------------------
# settings.json config
# --------------------------------------------------------------------------

def test_settings_json_has_idle_loop_config():
    assert SETTINGS_JSON.exists(), f"missing {SETTINGS_JSON}"
    cfg = json.loads(SETTINGS_JSON.read_text())
    il = cfg["idle_loop"]
    assert il["enabled"] is True
    assert il["interval_seconds"] == 180
    assert il["action"] == "invoke_skill"
    assert il["skill"] == "orchestrator-scheduler"
    assert il["args"] == ["--poll-once"]


# --------------------------------------------------------------------------
# from_settings / enabled flag
# --------------------------------------------------------------------------

def test_from_settings_reads_real_dist_config():
    loop = CopilotIdleLoop.from_settings(SETTINGS_JSON)
    assert loop.enabled is True
    assert loop.idle_threshold_seconds == 180


def test_from_settings_missing_file_uses_defaults(tmp_path):
    loop = CopilotIdleLoop.from_settings(tmp_path / "nope.json")
    assert loop.enabled is True
    assert loop.idle_threshold_seconds == 180


def test_from_settings_disabled_blocks_polling(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"idle_loop": {"enabled": False, "interval_seconds": 0}}))
    loop = CopilotIdleLoop.from_settings(p)
    loop.mark_done()
    assert loop.enabled is False
    assert loop.is_idle() is False
    # check_idle without force does nothing
    result = loop.check_idle()
    assert result.polled is False


# --------------------------------------------------------------------------
# IdlePollResult
# --------------------------------------------------------------------------

def test_result_to_dict_roundtrip():
    r = IdlePollResult(polled=True, processed=2, failed=1, lock_skipped=False)
    d = r.to_dict()
    assert d["polled"] is True
    assert d["processed"] == 2
    assert d["failed"] == 1


# --------------------------------------------------------------------------
# End-to-end: real scheduler subprocess against an empty temp queue
# --------------------------------------------------------------------------

def test_e2e_real_scheduler_empty_queue(tmp_path):
    """
    Drive the real scheduler subprocess via the idle-loop. Point HOME at a temp
    dir so the queue is empty; expect a clean JSON result with processed=0 and
    no errors. Exercises: idle-loop -> subprocess -> scheduler -> lock -> empty
    queue -> JSON parse.
    """
    env = dict(os.environ)
    env["HOME"] = str(tmp_path)
    env["COPILOT_SESSION_ID"] = "e2e-idle-session"
    env["AGENTIC_HARNESS"] = "copilot"
    # Pre-create the empty queue structure the orchestrator expects.
    qroot = tmp_path / ".agentic-engineers" / "copilot" / "e2e-idle-session" / "queue"
    for state in ("incoming", "processing", "done", "failed"):
        (qroot / state).mkdir(parents=True, exist_ok=True)

    proc = subprocess.run(
        [sys.executable, str(IDLE_LOOP_MODULE), "--force",
         "--session-id", "e2e-idle-session", "--block-seconds", "20"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert proc.stdout.strip(), f"no stdout; stderr={proc.stderr[-500:]}"
    result = json.loads(proc.stdout.strip().splitlines()[-1])
    assert result["polled"] is True
    assert result["processed"] == 0
    assert not result["errors"], f"unexpected errors: {result['errors']}"
    assert proc.returncode == 0


def test_main_force_emits_json(tmp_path):
    """main(--force) emits a JSON result (scheduler mocked via subprocess)."""
    payload = {"processed": 0, "failed": 0, "lock_skipped": False, "errors": []}
    with mock.patch("subprocess.run", return_value=_completed(json.dumps(payload))):
        with mock.patch("sys.stdout") as out:
            rc = main(["--force", "--session-id", "s"])
    assert rc == 0
