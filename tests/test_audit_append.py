"""Tests for scripts/audit_append.py — the clause-7 audit JSONL append helper.

Covers: every clause-7 event type accepted, missing-field rejection, unknown-event
rejection, append-only accumulation across calls, date-named file resolution, env-var
session/harness resolution, dry-run (no write), stdin-JSON mode, --extra merge,
numeric field type validation, and that ts is always computed by the script itself
(never trusted from caller input).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.audit_append import (  # noqa: E402
    ALLOWED_EVENTS,
    compute_ts,
    detect_harness,
    get_session_id,
    main,
    resolve_audit_path,
    validate_event,
)

BASE_ARGS = [
    "--task-id", "t1",
    "--parent-task-id", "root-task",
    "--depth", "1",
    "--agent-role", "senior-engineer",
    "--agent-model", "claude-sonnet-5",
    "--status", "success",
]


# ---------------------------------------------------------------------------
# Each clause-7 event type is accepted
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("event", sorted(ALLOWED_EVENTS))
def test_each_event_type_accepted_dry_run(event, capsys):
    rc = main(["--event", event, "--dry-run"] + BASE_ARGS)
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == event
    assert out["task_id"] == "t1"


def test_seven_events_in_enum():
    # Locks the clause-7 enum size so an accidental addition/removal is caught.
    assert ALLOWED_EVENTS == {
        "delegate_issued",
        "subagent_spawned",
        "handback_received",
        "gate_result",
        "escalation",
        "refusal",
        "limit_exceeded",
    }


# ---------------------------------------------------------------------------
# Rejection: unknown event / missing fields — the one permitted failure mode
# ---------------------------------------------------------------------------

def test_unknown_event_rejected_via_argparse():
    with pytest.raises(SystemExit) as exc_info:
        main(["--event", "not_a_real_event", "--dry-run"] + BASE_ARGS)
    assert exc_info.value.code == 2


def test_missing_required_field_rejected(capsys):
    # Omit --status entirely.
    args = ["--event", "delegate_issued", "--dry-run",
            "--task-id", "t1", "--parent-task-id", "root-task",
            "--depth", "1", "--agent-role", "senior-engineer",
            "--agent-model", "claude-sonnet-5"]
    rc = main(args)
    assert rc == 2
    err = capsys.readouterr().err
    assert "status" in err
    assert "required field missing" in err


def test_validate_event_rejects_unknown_event_directly():
    errors = validate_event({"event": "bogus", "task_id": "t1", "parent_task_id": None,
                              "depth": 0, "agent_role": "orchestrator",
                              "agent_model": "claude-sonnet-5", "status": "success"})
    assert any("event" in e for e in errors)


def test_validate_event_rejects_negative_depth():
    errors = validate_event({"event": "delegate_issued", "task_id": "t1", "parent_task_id": None,
                              "depth": -1, "agent_role": "orchestrator",
                              "agent_model": "claude-sonnet-5", "status": "success"})
    assert any("depth" in e for e in errors)


def test_validate_event_rejects_non_numeric_tokens():
    errors = validate_event({"event": "handback_received", "task_id": "t1", "parent_task_id": "p1",
                              "depth": 1, "agent_role": "engineer",
                              "agent_model": "claude-haiku-4.5", "status": "success",
                              "tokens": "a lot"})
    assert any("tokens" in e for e in errors)


def test_validate_event_accepts_null_parent_task_id_for_root():
    errors = validate_event({"event": "delegate_issued", "task_id": "root-1", "parent_task_id": None,
                              "depth": 0, "agent_role": "orchestrator",
                              "agent_model": "claude-sonnet-5", "status": "success"})
    assert errors == []


# ---------------------------------------------------------------------------
# Append-only accumulation, date-named file, mkdir -p
# ---------------------------------------------------------------------------

def test_append_only_accumulation(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTIC_SESSION_ID", "sess-1")
    monkeypatch.setenv("AGENTIC_HARNESS", "claude")

    rc1 = main(["--event", "delegate_issued", "--base-dir", str(tmp_path)] + BASE_ARGS)
    rc2 = main(["--event", "handback_received", "--base-dir", str(tmp_path)] + BASE_ARGS)
    assert rc1 == 0
    assert rc2 == 0

    files = list((tmp_path / "claude" / "sess-1" / "audit").glob("events-*.jsonl"))
    assert len(files) == 1
    lines = files[0].read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["event"] == "delegate_issued"
    assert second["event"] == "handback_received"


def test_date_named_file(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTIC_SESSION_ID", "sess-2")
    monkeypatch.setenv("AGENTIC_HARNESS", "opencode")
    rc = main(["--event", "gate_result", "--base-dir", str(tmp_path)] + BASE_ARGS)
    assert rc == 0
    files = list((tmp_path / "opencode" / "sess-2" / "audit").glob("*.jsonl"))
    assert len(files) == 1
    assert re.match(r"^events-\d{4}-\d{2}-\d{2}\.jsonl$", files[0].name)


def test_mkdir_p_creates_nested_dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTIC_SESSION_ID", "sess-3")
    monkeypatch.setenv("AGENTIC_HARNESS", "codex")
    assert not (tmp_path / "codex").exists()
    rc = main(["--event", "escalation", "--base-dir", str(tmp_path)] + BASE_ARGS)
    assert rc == 0
    assert (tmp_path / "codex" / "sess-3" / "audit").is_dir()


# ---------------------------------------------------------------------------
# Env resolution (session id + harness priority)
# ---------------------------------------------------------------------------

def test_get_session_id_priority():
    env = {"AGENTIC_SESSION_ID": "a", "CLAUDE_SESSION_ID": "b", "COPILOT_SESSION_ID": "c"}
    assert get_session_id(env) == "a"
    assert get_session_id({"CLAUDE_SESSION_ID": "b", "COPILOT_SESSION_ID": "c"}) == "b"
    assert get_session_id({"COPILOT_SESSION_ID": "c"}) == "c"


def test_get_session_id_falls_back_to_uuid():
    sid = get_session_id({})
    assert re.match(r"^[0-9a-f-]{36}$", sid)


def test_detect_harness_priority():
    assert detect_harness({"AGENTIC_HARNESS": "custom", "CLAUDE_SESSION_ID": "x"}) == "custom"
    assert detect_harness({"CLAUDE_SESSION_ID": "x"}) == "claude"
    assert detect_harness({"COPILOT_SESSION_ID": "x"}) == "copilot"
    assert detect_harness({"OPENAI_API_KEY": "x"}) == "gpt"
    assert detect_harness({}) == "local"


def test_resolve_audit_path_shape(tmp_path):
    p = resolve_audit_path(harness="claude", session_id="sess-9", date_str="2026-08-14", base_dir=tmp_path)
    assert p == tmp_path / "claude" / "sess-9" / "audit" / "events-2026-08-14.jsonl"


def test_resolve_audit_path_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError):
        resolve_audit_path(harness="../etc", session_id="sess-9", date_str="2026-08-14", base_dir=tmp_path)


# ---------------------------------------------------------------------------
# dry-run: no write
# ---------------------------------------------------------------------------

def test_dry_run_does_not_write(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AGENTIC_SESSION_ID", "sess-dry")
    monkeypatch.setenv("AGENTIC_HARNESS", "claude")
    rc = main(["--event", "refusal", "--dry-run", "--base-dir", str(tmp_path)] + BASE_ARGS)
    assert rc == 0
    out = capsys.readouterr().out
    assert json.loads(out)["event"] == "refusal"
    assert not (tmp_path / "claude").exists()


# ---------------------------------------------------------------------------
# stdin-JSON mode
# ---------------------------------------------------------------------------

def test_stdin_json_mode(tmp_path, monkeypatch, capsys):
    payload = json.dumps({
        "event": "limit_exceeded", "task_id": "t2", "parent_task_id": "p2",
        "depth": 3, "agent_role": "senior-engineer", "agent_model": "claude-sonnet-5",
        "status": "blocked",
    })
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO(payload))
    rc = main(["--dry-run"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "limit_exceeded"
    assert out["task_id"] == "t2"


def test_stdin_invalid_json_rejected(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO("{not json"))
    rc = main([])
    assert rc == 2
    assert "invalid JSON" in capsys.readouterr().err


def test_stdin_empty_rejected(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO(""))
    rc = main([])
    assert rc == 2


# ---------------------------------------------------------------------------
# --extra merge
# ---------------------------------------------------------------------------

def test_extra_fields_merged(capsys):
    rc = main(["--event", "gate_result", "--dry-run", "--extra", '{"error": "lint failed"}'] + BASE_ARGS)
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["error"] == "lint failed"


def test_extra_invalid_json_rejected(capsys):
    rc = main(["--event", "gate_result", "--dry-run", "--extra", "{not json"] + BASE_ARGS)
    assert rc == 2
    assert "invalid JSON in --extra" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# ts is computed by the script, never trusted from the caller
# ---------------------------------------------------------------------------

def test_ts_is_iso8601_utc_and_computed(capsys):
    rc = main(["--event", "handback_received", "--dry-run", "--tokens", "100", "--cost", "0.5"] + BASE_ARGS)
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$", out["ts"])


def test_stdin_supplied_ts_is_overridden(capsys):
    payload = json.dumps({
        "event": "delegate_issued", "task_id": "t3", "parent_task_id": None,
        "depth": 0, "agent_role": "orchestrator", "agent_model": "claude-sonnet-5",
        "status": "success", "ts": "1999-01-01T00:00:00.000Z",
    })
    import io
    import sys as _sys
    _stdin_backup = _sys.stdin
    _sys.stdin = io.StringIO(payload)
    try:
        rc = main(["--dry-run"])
    finally:
        _sys.stdin = _stdin_backup
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ts"] != "1999-01-01T00:00:00.000Z"


def test_compute_ts_format():
    from datetime import datetime, timezone
    ts = compute_ts(datetime(2026, 8, 14, 12, 30, 45, 123000, tzinfo=timezone.utc))
    assert ts == "2026-08-14T12:30:45.123Z"


# ---------------------------------------------------------------------------
# Real (non-dry-run) filesystem write failure is a warning, not a crash
# ---------------------------------------------------------------------------

def test_real_write_failure_returns_1_not_raise(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AGENTIC_SESSION_ID", "sess-bad")
    monkeypatch.setenv("AGENTIC_HARNESS", "bad/harness")  # illegal path separator
    rc = main(["--event", "refusal", "--base-dir", str(tmp_path)] + BASE_ARGS)
    assert rc == 1
    assert "warning" in capsys.readouterr().err
