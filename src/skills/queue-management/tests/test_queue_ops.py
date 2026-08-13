"""Tests for queue-management's queue_ops.py — enqueue atomicity, path
isolation, ancestry-based cycle detection, and schema validation.

Run via: pytest src/skills/queue-management/tests/ (make test-skills).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import queue_ops  # noqa: E402
from queue_ops import (  # noqa: E402
    QueueOperations,
    detect_harness,
    exceeds_max_depth,
    get_queue_path,
    get_session_id,
    has_cycle,
)


VALID_DELEGATE = {
    "handoff_type": "DELEGATE",
    "task_id": "test-task-001",
    "agent": "engineer",
    "scope": "Implement a well-scoped change to the widget renderer module as described in the linked ticket, touching only render.py",
    "plan": ["Step one: read the file", "Step two: make the change"],
    "context": "The widget renderer at src/widgets/render.py needs a fix for the off-by-one error in the padding calculation logic used on every frame",
    "success_criteria": ["Tests pass"],
}

VALID_HANDBACK = {
    "handoff_type": "HANDBACK",
    "task_id": "test-task-001",
    "agent": "engineer",
    "status": "success",
    "output": "Fixed the padding calculation.",
    "metrics": {"quality": 0.9, "tokens": 500, "cost": 0.01, "duration_seconds": 12.5},
}


@pytest.fixture
def ops(tmp_path):
    return QueueOperations(session_id="test-session", queue_path=str(tmp_path))


# ---------------------------------------------------------------------------
# enqueue() — schema validation
# ---------------------------------------------------------------------------

class TestEnqueueSchema:
    def test_valid_delegate_enqueues(self, ops):
        result = ops.enqueue(VALID_DELEGATE)
        assert result["status"] == "enqueued"
        assert result["handoff_type"] == "DELEGATE"
        assert Path(result["queue_path"]).exists()

    def test_valid_handback_enqueues(self, ops):
        result = ops.enqueue(VALID_HANDBACK)
        assert result["status"] == "enqueued"
        assert result["handoff_type"] == "HANDBACK"

    def test_rejects_legacy_type_field(self, ops):
        bad = {**VALID_DELEGATE, "type": "DELEGATE"}
        with pytest.raises(ValueError, match="legacy"):
            ops.enqueue(bad)

    def test_rejects_legacy_role_field(self, ops):
        bad = {**VALID_DELEGATE, "role": "Engineer"}
        with pytest.raises(ValueError, match="legacy"):
            ops.enqueue(bad)

    def test_rejects_legacy_quality_score(self, ops):
        bad = {**VALID_HANDBACK, "quality_score": 90}
        with pytest.raises(ValueError, match="legacy"):
            ops.enqueue(bad)

    def test_rejects_missing_handoff_type(self, ops):
        bad = {k: v for k, v in VALID_DELEGATE.items() if k != "handoff_type"}
        with pytest.raises(ValueError, match="handoff_type"):
            ops.enqueue(bad)

    def test_rejects_invalid_agent(self, ops):
        bad = {**VALID_DELEGATE, "agent": "junior-engineer"}
        with pytest.raises(ValueError, match="agent"):
            ops.enqueue(bad)

    def test_rejects_short_scope(self, ops):
        bad = {**VALID_DELEGATE, "scope": "too short"}
        with pytest.raises(ValueError, match="scope"):
            ops.enqueue(bad)

    def test_rejects_single_step_plan(self, ops):
        bad = {**VALID_DELEGATE, "plan": ["only one step here"]}
        with pytest.raises(ValueError, match="plan"):
            ops.enqueue(bad)

    def test_rejects_handback_missing_metrics(self, ops):
        bad = {k: v for k, v in VALID_HANDBACK.items() if k != "metrics"}
        with pytest.raises(ValueError, match="metrics"):
            ops.enqueue(bad)

    def test_rejects_handback_incomplete_metrics(self, ops):
        bad = {**VALID_HANDBACK, "metrics": {"quality": 0.9}}
        with pytest.raises(ValueError, match="tokens"):
            ops.enqueue(bad)

    def test_rejects_invalid_status(self, ops):
        bad = {**VALID_HANDBACK, "status": "complete"}  # legacy alias, not canonical
        with pytest.raises(ValueError, match="status"):
            ops.enqueue(bad)


# ---------------------------------------------------------------------------
# enqueue() — atomicity
# ---------------------------------------------------------------------------

class TestAtomicity:
    def test_written_file_is_valid_yaml(self, ops):
        result = ops.enqueue(VALID_DELEGATE)
        with open(result["queue_path"]) as fh:
            data = yaml.safe_load(fh)
        assert data["task_id"] == "test-task-001"
        assert "enqueued_at" in data

    def test_no_temp_files_left_behind(self, ops, tmp_path):
        ops.enqueue(VALID_DELEGATE)
        leftovers = list(tmp_path.rglob(".tmp-*"))
        assert leftovers == []

    def test_delegate_lands_in_incoming(self, ops):
        result = ops.enqueue(VALID_DELEGATE)
        assert "/incoming/" in result["queue_path"]

    def test_handback_lands_in_processing(self, ops):
        result = ops.enqueue(VALID_HANDBACK)
        assert "/processing/" in result["queue_path"]

    def test_move_task_between_states(self, ops):
        ops.enqueue(VALID_HANDBACK)
        result = ops.move_task("test-task-001", "processing", "done")
        assert result["status"] == "moved"
        assert (ops.session_queue_path / "done" / "test-task-001.yaml").exists()
        assert not (ops.session_queue_path / "processing" / "test-task-001.yaml").exists()

    def test_move_task_missing_raises(self, ops):
        with pytest.raises(FileNotFoundError):
            ops.move_task("does-not-exist", "incoming", "processing")


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------

class TestAuditTrail:
    def test_enqueue_appends_audit_line(self, ops):
        ops.enqueue(VALID_DELEGATE)
        audit_path = ops.session_queue_path.parent / "audit.log"
        assert audit_path.exists()
        lines = audit_path.read_text().strip().splitlines()
        assert len(lines) == 1
        assert "DELEGATE" in lines[0]
        assert "test-task-001" in lines[0]

    def test_audit_log_is_append_only_across_calls(self, ops):
        ops.enqueue(VALID_DELEGATE)
        ops.enqueue(VALID_HANDBACK)
        audit_path = ops.session_queue_path.parent / "audit.log"
        lines = audit_path.read_text().strip().splitlines()
        assert len(lines) == 2


# ---------------------------------------------------------------------------
# Path isolation
# ---------------------------------------------------------------------------

class TestPathIsolation:
    def test_get_queue_path_layout(self, tmp_path):
        p = get_queue_path("sess-1", "claude", base_dir=tmp_path)
        assert p == tmp_path / "claude" / "sess-1" / "queue"

    @pytest.mark.parametrize("bad_session", ["", ".", "..", "a/b", "a\\b", "a\x00b"])
    def test_rejects_traversal_in_session_id(self, tmp_path, bad_session):
        with pytest.raises(ValueError):
            get_queue_path(bad_session, "claude", base_dir=tmp_path)

    @pytest.mark.parametrize("bad_harness", ["../etc", "a/b"])
    def test_rejects_traversal_in_harness(self, tmp_path, bad_harness):
        with pytest.raises(ValueError):
            get_queue_path("sess-1", bad_harness, base_dir=tmp_path)

    def test_detect_harness_explicit_override(self, monkeypatch):
        monkeypatch.setenv("AGENTIC_HARNESS", "opencode")
        assert detect_harness() == "opencode"

    def test_detect_harness_falls_back_to_local(self, monkeypatch):
        for var in ("AGENTIC_HARNESS", "CLAUDE_SESSION_ID", "COPILOT_SESSION_ID", "OPENAI_API_KEY"):
            monkeypatch.delenv(var, raising=False)
        assert detect_harness() == "local"

    def test_get_session_id_generates_uuid_when_unset(self, monkeypatch):
        for var in ("AGENTIC_SESSION_ID", "CLAUDE_SESSION_ID", "COPILOT_SESSION_ID"):
            monkeypatch.delenv(var, raising=False)
        sid = get_session_id()
        assert len(sid) > 0

    def test_queue_ops_isolated_by_session(self, tmp_path):
        ops_a = QueueOperations(session_id="session-a", queue_path=str(tmp_path))
        ops_b = QueueOperations(session_id="session-b", queue_path=str(tmp_path))
        ops_a.enqueue(VALID_DELEGATE)
        assert not (ops_b.session_queue_path / "incoming" / "test-task-001.yaml").exists()

    def test_enriched_error_mentions_canonical_path_on_invalid_session(self, tmp_path):
        """AC1: rejected queue-path operation cites the canonical template."""
        with pytest.raises(ValueError) as exc_info:
            get_queue_path("bad/session", "claude", base_dir=tmp_path)
        error_msg = str(exc_info.value)
        assert "~/.agentic-engineers/{harness}/{session-id}/queue/" in error_msg

    def test_enriched_error_lists_legacy_paths_on_invalid_harness(self, tmp_path):
        """AC1: rejected queue-path operation lists all unsupported legacy paths."""
        with pytest.raises(ValueError) as exc_info:
            get_queue_path("sess-1", "bad/harness", base_dir=tmp_path)
        error_msg = str(exc_info.value)
        # Verify all legacy paths are listed
        assert "~/.copilot/queue/" in error_msg
        assert "~/.claude/queue/" in error_msg
        assert "artifacts/queue/" in error_msg

    def test_enriched_error_on_empty_session_id(self, tmp_path):
        """AC1: enriched message on path validation failure."""
        with pytest.raises(ValueError) as exc_info:
            get_queue_path("", "claude", base_dir=tmp_path)
        error_msg = str(exc_info.value)
        # Should contain both canonical template and legacy paths
        assert "~/.agentic-engineers/{harness}/{session-id}/queue/" in error_msg
        assert "~/.copilot/queue/" in error_msg


# ---------------------------------------------------------------------------
# Ancestry-based cycle / depth detection
# ---------------------------------------------------------------------------

class TestCycleDetection:
    def test_no_cycle_when_no_ancestry(self):
        assert has_cycle("engineer", None) is False
        assert has_cycle("engineer", []) is False

    def test_cycle_when_target_in_ancestry(self):
        assert has_cycle("senior-engineer", ["orchestrator", "senior-engineer", "lead-engineer"]) is True

    def test_no_cycle_when_target_not_in_ancestry(self):
        assert has_cycle("engineer", ["orchestrator", "senior-engineer"]) is False

    def test_exceeds_max_depth(self):
        assert exceeds_max_depth(["orchestrator", "senior-engineer", "lead-engineer"], max_depth=3) is True

    def test_within_max_depth(self):
        assert exceeds_max_depth(["orchestrator", "senior-engineer"], max_depth=3) is False

    def test_enqueue_rejects_cyclic_delegate(self, ops):
        cyclic = {
            **VALID_DELEGATE,
            "task_id": "cyclic-task",
            "ancestry": ["orchestrator", "engineer"],
        }
        with pytest.raises(RuntimeError, match="Cycle"):
            ops.enqueue(cyclic)

    def test_enqueue_rejects_depth_exceeded(self, ops):
        deep = {
            **VALID_DELEGATE,
            "task_id": "deep-task",
            "agent": "quality-engineer",
            "ancestry": ["orchestrator", "senior-engineer", "lead-engineer"],
        }
        with pytest.raises(RuntimeError, match="depth"):
            ops.enqueue(deep)

    def test_enqueue_allows_valid_ancestry(self, ops):
        ok = {
            **VALID_DELEGATE,
            "task_id": "shallow-task",
            "ancestry": ["orchestrator"],
        }
        result = ops.enqueue(ok)
        assert result["status"] == "enqueued"


def test_init_rejects_empty_session_id(tmp_path):
    with pytest.raises(ValueError):
        QueueOperations(session_id="", queue_path=str(tmp_path))
