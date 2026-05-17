"""
Phase 3 Dry-Run Mode — End-to-End Tests.

Validates that DryRunContext:
  - Intercepts all side-effect operations (file writes, git, API, queue)
  - Produces zero actual side effects
  - Collects accurate metrics and audit trail
  - Works with all agent types and orchestrator tasks
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.orchestration.dry_run import DryRunContext, OperationType


# ─────────────────────────────────────────────────────────────────────────── #
# Helpers
# ─────────────────────────────────────────────────────────────────────────── #

def _make_dry_run(enabled: bool = True, log_file: str | None = None) -> DryRunContext:
    return DryRunContext(enabled=enabled, log_file=log_file)


# ─────────────────────────────────────────────────────────────────────────── #
# 1. Basic activation
# ─────────────────────────────────────────────────────────────────────────── #

class TestDryRunActivation:
    def test_enabled_flag_true(self):
        ctx = _make_dry_run(enabled=True)
        assert ctx.enabled is True

    def test_enabled_flag_false(self):
        ctx = _make_dry_run(enabled=False)
        assert ctx.enabled is False

    def test_context_manager_returns_self(self):
        ctx = _make_dry_run()
        with ctx as c:
            assert c is ctx

    def test_no_operations_on_init(self):
        ctx = _make_dry_run()
        assert ctx.operations == []


# ─────────────────────────────────────────────────────────────────────────── #
# 2. File operations — no side effects
# ─────────────────────────────────────────────────────────────────────────── #

class TestDryRunFileOperations:
    def test_log_file_write_no_actual_write(self, tmp_path):
        target = tmp_path / "output.txt"
        ctx = _make_dry_run()
        ctx.log_file_write(str(target), "hello world")
        assert not target.exists(), "DryRun must NOT create files"

    def test_log_file_write_recorded(self):
        ctx = _make_dry_run()
        ctx.log_file_write("/fake/path.txt", "content")
        assert len(ctx.operations) == 1
        assert ctx.operations[0].operation_type == OperationType.FILE_WRITE

    def test_log_file_delete_no_actual_delete(self, tmp_path):
        real_file = tmp_path / "keep.txt"
        real_file.write_text("keep me")
        ctx = _make_dry_run()
        ctx.log_file_delete(str(real_file))
        assert real_file.exists(), "DryRun must NOT delete files"

    def test_log_file_move_no_actual_move(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("data")
        dst = tmp_path / "dst.txt"
        ctx = _make_dry_run()
        ctx.log_file_move(str(src), str(dst))
        assert src.exists()
        assert not dst.exists()

    def test_multiple_file_ops_all_recorded(self):
        ctx = _make_dry_run()
        ctx.log_file_write("/a.txt", "a")
        ctx.log_file_read("/b.txt")
        ctx.log_file_delete("/c.txt")
        assert len(ctx.operations) == 3


# ─────────────────────────────────────────────────────────────────────────── #
# 3. Git operations — no side effects
# ─────────────────────────────────────────────────────────────────────────── #

class TestDryRunGitOperations:
    def test_log_git_commit_recorded(self):
        ctx = _make_dry_run()
        ctx.log_git_commit("feat: add feature")
        ops = [o for o in ctx.operations if o.operation_type == OperationType.GIT_COMMIT]
        assert len(ops) == 1

    def test_log_git_push_recorded(self):
        ctx = _make_dry_run()
        ctx.log_git_push("origin", "main")
        ops = [o for o in ctx.operations if o.operation_type == OperationType.GIT_PUSH]
        assert len(ops) == 1

    def test_log_git_branch_recorded(self):
        ctx = _make_dry_run()
        ctx.log_git_branch("feature/new-branch")
        ops = [o for o in ctx.operations if o.operation_type == OperationType.GIT_BRANCH]
        assert len(ops) == 1


# ─────────────────────────────────────────────────────────────────────────── #
# 4. API and Queue operations
# ─────────────────────────────────────────────────────────────────────────── #

class TestDryRunApiQueueOperations:
    def test_log_api_call_recorded(self):
        ctx = _make_dry_run()
        ctx.log_api_call("POST", "https://api.example.com/tasks", {"task": "test"})
        ops = [o for o in ctx.operations if o.operation_type == OperationType.API_CALL]
        assert len(ops) == 1

    def test_log_queue_move_recorded(self):
        ctx = _make_dry_run()
        ctx.log_queue_move("task-123", "incoming", "processing")
        ops = [o for o in ctx.operations if o.operation_type == OperationType.QUEUE_MOVE]
        assert len(ops) == 1

    def test_log_queue_archive_recorded(self):
        ctx = _make_dry_run()
        ctx.log_queue_archive("task-456", "done")
        ops = [o for o in ctx.operations if o.operation_type == OperationType.QUEUE_ARCHIVE]
        assert len(ops) == 1


# ─────────────────────────────────────────────────────────────────────────── #
# 5. Metrics collection
# ─────────────────────────────────────────────────────────────────────────── #

class TestDryRunMetrics:
    def test_operation_counts_tracked(self):
        ctx = _make_dry_run()
        ctx.log_file_write("/a.txt", "x")
        ctx.log_file_write("/b.txt", "y")
        ctx.log_git_commit("msg")
        assert ctx.operation_counts[OperationType.FILE_WRITE] == 2
        assert ctx.operation_counts[OperationType.GIT_COMMIT] == 1

    def test_get_audit_trail_returns_all_ops(self):
        ctx = _make_dry_run()
        ctx.log_file_write("/x.txt", "data")
        ctx.log_api_call("GET", "https://api.example.com", {})
        trail = ctx.get_audit_trail()
        assert "operations" in trail
        assert len(trail["operations"]) == 2

    def test_audit_trail_serialisable(self):
        ctx = _make_dry_run()
        ctx.log_file_write("/x.txt", "data")
        trail = ctx.get_audit_trail()
        # Must be JSON-serialisable
        json.dumps(trail)

    def test_audit_trail_written_to_file(self, tmp_path):
        log_file = str(tmp_path / "audit.json")
        with _make_dry_run(log_file=log_file) as ctx:
            ctx.log_file_write("/x.txt", "data")
        assert Path(log_file).exists()
        data = json.loads(Path(log_file).read_text())
        assert "operations" in data


# ─────────────────────────────────────────────────────────────────────────── #
# 6. Disabled dry-run (pass-through)
# ─────────────────────────────────────────────────────────────────────────── #

class TestDryRunDisabled:
    def test_disabled_still_records(self):
        """Even when disabled, operations are still recorded for audit."""
        ctx = _make_dry_run(enabled=False)
        ctx.log_file_write("/x.txt", "data")
        # Operations are recorded regardless of enabled state
        assert len(ctx.operations) == 1

    def test_disabled_no_log_output(self, caplog):
        import logging
        ctx = _make_dry_run(enabled=False)
        with caplog.at_level(logging.INFO):
            ctx.log_file_write("/x.txt", "data")
        # No "DRY-RUN MODE" banner in logs when disabled
        assert "DRY-RUN MODE ENABLED" not in caplog.text


# ─────────────────────────────────────────────────────────────────────────── #
# 7. Error simulation
# ─────────────────────────────────────────────────────────────────────────── #

class TestDryRunErrorSimulation:
    def test_log_failure_recorded(self):
        ctx = _make_dry_run()
        ctx.log_file_write("/x.txt", "data", would_succeed=False, error_message="Permission denied")
        op = ctx.operations[0]
        assert op.would_succeed is False
        assert "Permission denied" in op.error_message

    def test_audit_trail_includes_failures(self):
        ctx = _make_dry_run()
        ctx.log_file_write("/x.txt", "data", would_succeed=False, error_message="Disk full")
        trail = ctx.get_audit_trail()
        failed = [o for o in trail["operations"] if not o["would_succeed"]]
        assert len(failed) == 1


# ─────────────────────────────────────────────────────────────────────────── #
# 8. Multi-agent simulation
# ─────────────────────────────────────────────────────────────────────────── #

class TestDryRunMultiAgent:
    def test_orchestrator_task_simulation(self):
        """Simulate a full orchestrator task through dry-run."""
        ctx = _make_dry_run()
        # Orchestrator reads queue
        ctx.log_file_read("artifacts/queue/incoming/task-001.yaml")
        # Moves to processing
        ctx.log_queue_move("task-001", "incoming", "processing")
        # Engineer writes output
        ctx.log_file_write("artifacts/queue/processing/task-001.yaml", "result: done")
        # Git commit
        ctx.log_git_commit("chore: process task-001")
        # Archive
        ctx.log_queue_archive("task-001", "done")

        assert len(ctx.operations) == 5
        trail = ctx.get_audit_trail()
        assert trail["total_operations"] == 5

    def test_all_agent_types_simulation(self):
        """Simulate operations from each agent type."""
        ctx = _make_dry_run()
        agent_ops = {
            "orchestrator": lambda: ctx.log_queue_move("t", "in", "proc"),
            "engineer": lambda: ctx.log_file_write("/src/feature.py", "code"),
            "senior_engineer": lambda: ctx.log_file_write("/src/complex.py", "complex"),
            "quality_engineer": lambda: ctx.log_api_call("POST", "https://qe/review", {}),
            "security_engineer": lambda: ctx.log_api_call("POST", "https://sec/scan", {}),
        }
        for agent, op in agent_ops.items():
            op()

        assert len(ctx.operations) == len(agent_ops)
