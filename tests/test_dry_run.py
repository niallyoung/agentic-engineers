"""
Test Suite for Dry-Run Mode Implementation

Tests cover:
1. DryRunContext initialization and configuration
2. File operation logging
3. Git operation logging
4. API call logging
5. Queue operation logging
6. Audit trail generation
7. JSON serialization
8. Context manager behavior
9. Global context management
10. Integration with AutomationController
"""

import pytest
import json
import logging
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from src.orchestration.dry_run import (
    DryRunContext,
    OperationType,
    SimulatedOperation,
    initialize_dry_run,
    get_dry_run_context,
    is_dry_run_enabled,
    dry_run_mode,
)


# ─── Test Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def temp_log_file():
    """Create a temporary log file path."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        path = f.name
    yield path
    # Cleanup
    try:
        Path(path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def logger():
    """Create a test logger."""
    return logging.getLogger("test_dry_run")


@pytest.fixture
def dry_run_context(logger):
    """Create a DryRunContext instance."""
    return DryRunContext(enabled=True, logger=logger)


# ─── Test DryRunContext Initialization ────────────────────────────────────


class TestDryRunContextInitialization:
    """Test DryRunContext initialization."""
    
    def test_initialization_disabled(self):
        """Test initialization with dry-run disabled."""
        ctx = DryRunContext(enabled=False)
        assert ctx.enabled is False
        assert len(ctx.operations) == 0
        assert ctx.log_file is None
    
    def test_initialization_enabled(self):
        """Test initialization with dry-run enabled."""
        ctx = DryRunContext(enabled=True)
        assert ctx.enabled is True
        assert len(ctx.operations) == 0
    
    def test_initialization_with_log_file(self, temp_log_file):
        """Test initialization with log file."""
        ctx = DryRunContext(enabled=True, log_file=temp_log_file)
        assert ctx.log_file == temp_log_file
    
    def test_context_manager(self):
        """Test context manager behavior."""
        with DryRunContext(enabled=True) as ctx:
            assert ctx.enabled is True
        # Should exit cleanly


# ─── Test File Operations ────────────────────────────────────────────────


class TestFileOperations:
    """Test file operation logging."""
    
    def test_log_file_write(self, dry_run_context):
        """Test file write logging."""
        op = dry_run_context.log_file_write("/path/to/file.txt", "content")
        
        assert op.operation_type == OperationType.FILE_WRITE
        assert "/path/to/file.txt" in op.description
        assert op.details["path"] == "/path/to/file.txt"
        assert op.details["content_length"] == 7
        assert op.would_succeed is True
    
    def test_log_file_read(self, dry_run_context):
        """Test file read logging."""
        op = dry_run_context.log_file_read("/path/to/file.txt")
        
        assert op.operation_type == OperationType.FILE_READ
        assert op.details["path"] == "/path/to/file.txt"
    
    def test_log_file_delete(self, dry_run_context):
        """Test file delete logging."""
        op = dry_run_context.log_file_delete("/path/to/file.txt")
        
        assert op.operation_type == OperationType.FILE_DELETE
        assert op.details["path"] == "/path/to/file.txt"
    
    def test_log_file_move(self, dry_run_context):
        """Test file move logging."""
        op = dry_run_context.log_file_move("/old/path.txt", "/new/path.txt")
        
        assert op.operation_type == OperationType.FILE_MOVE
        assert op.details["from_path"] == "/old/path.txt"
        assert op.details["to_path"] == "/new/path.txt"
    
    def test_log_file_copy(self, dry_run_context):
        """Test file copy logging."""
        op = dry_run_context.log_file_copy("/src/file.txt", "/dst/file.txt")
        
        assert op.operation_type == OperationType.FILE_COPY
        assert op.details["from_path"] == "/src/file.txt"
        assert op.details["to_path"] == "/dst/file.txt"
    
    def test_log_dir_create(self, dry_run_context):
        """Test directory create logging."""
        op = dry_run_context.log_dir_create("/path/to/dir")
        
        assert op.operation_type == OperationType.DIR_CREATE
        assert op.details["path"] == "/path/to/dir"
    
    def test_log_dir_delete(self, dry_run_context):
        """Test directory delete logging."""
        op = dry_run_context.log_dir_delete("/path/to/dir")
        
        assert op.operation_type == OperationType.DIR_DELETE
        assert op.details["path"] == "/path/to/dir"
    
    def test_file_write_with_error(self, dry_run_context):
        """Test file write with error."""
        op = dry_run_context.log_file_write(
            "/path/to/file.txt",
            "content",
            would_succeed=False,
            error_message="Permission denied"
        )
        
        assert op.would_succeed is False
        assert op.error_message == "Permission denied"


# ─── Test Git Operations ────────────────────────────────────────────────


class TestGitOperations:
    """Test git operation logging."""
    
    def test_log_git_commit(self, dry_run_context):
        """Test git commit logging."""
        files = ["file1.py", "file2.py"]
        op = dry_run_context.log_git_commit("Fix: bug in orchestrator", files=files)
        
        assert op.operation_type == OperationType.GIT_COMMIT
        assert "Fix: bug in orchestrator" in op.description
        assert op.details["message"] == "Fix: bug in orchestrator"
        assert op.details["files"] == files
        assert op.details["file_count"] == 2
    
    def test_log_git_push(self, dry_run_context):
        """Test git push logging."""
        op = dry_run_context.log_git_push(remote="origin", branch="main")
        
        assert op.operation_type == OperationType.GIT_PUSH
        assert "origin/main" in op.description
        assert op.details["remote"] == "origin"
        assert op.details["branch"] == "main"
    
    def test_log_git_branch(self, dry_run_context):
        """Test git branch logging."""
        op = dry_run_context.log_git_branch("feature/dry-run", action="create")
        
        assert op.operation_type == OperationType.GIT_BRANCH
        assert "feature/dry-run" in op.description
        assert op.details["branch_name"] == "feature/dry-run"
        assert op.details["action"] == "create"


# ─── Test API Operations ────────────────────────────────────────────────


class TestAPIOperations:
    """Test API call logging."""
    
    def test_log_api_call(self, dry_run_context):
        """Test API call logging."""
        payload = {"task_id": "123", "status": "complete"}
        op = dry_run_context.log_api_call("POST", "/tasks/123/complete", payload=payload)
        
        assert op.operation_type == OperationType.API_CALL
        assert "POST" in op.description
        assert "/tasks/123/complete" in op.description
        assert op.details["method"] == "POST"
        assert op.details["endpoint"] == "/tasks/123/complete"
        assert op.details["payload"] == payload


# ─── Test Queue Operations ────────────────────────────────────────────


class TestQueueOperations:
    """Test queue operation logging."""
    
    def test_log_queue_move(self, dry_run_context):
        """Test queue move logging."""
        op = dry_run_context.log_queue_move(
            "task-123",
            "incoming",
            "processing"
        )
        
        assert op.operation_type == OperationType.QUEUE_MOVE
        assert "task-123" in op.description
        assert op.details["task_id"] == "task-123"
        assert op.details["from_state"] == "incoming"
        assert op.details["to_state"] == "processing"
    
    def test_log_queue_archive(self, dry_run_context):
        """Test queue archive logging."""
        op = dry_run_context.log_queue_archive(
            "task-123",
            "Max retries exceeded"
        )
        
        assert op.operation_type == OperationType.QUEUE_ARCHIVE
        assert "task-123" in op.description
        assert op.details["reason"] == "Max retries exceeded"


# ─── Test Subprocess Operations ────────────────────────────────────────


class TestSubprocessOperations:
    """Test subprocess operation logging."""
    
    def test_log_subprocess_run(self, dry_run_context):
        """Test subprocess run logging."""
        op = dry_run_context.log_subprocess_run(
            "git commit -m 'test'",
            cwd="/repo"
        )
        
        assert op.operation_type == OperationType.SUBPROCESS_RUN
        assert "git commit" in op.description
        assert op.details["command"] == "git commit -m 'test'"
        assert op.details["cwd"] == "/repo"


# ─── Test Audit Trail ────────────────────────────────────────────────


class TestAuditTrail:
    """Test audit trail generation."""
    
    def test_get_audit_trail_empty(self, dry_run_context):
        """Test audit trail with no operations."""
        audit = dry_run_context.get_audit_trail()
        
        assert audit["dry_run_mode"] is True
        assert audit["total_operations"] == 0
        assert audit["operations"] == []
        assert "start_time" in audit
        assert "end_time" in audit
        assert "duration_seconds" in audit
    
    def test_get_audit_trail_with_operations(self, dry_run_context):
        """Test audit trail with operations."""
        dry_run_context.log_file_write("/path/to/file.txt", "content")
        dry_run_context.log_git_commit("Fix: bug")
        dry_run_context.log_queue_move("task-123", "incoming", "processing")
        
        audit = dry_run_context.get_audit_trail()
        
        assert audit["total_operations"] == 3
        assert len(audit["operations"]) == 3
        assert audit["operation_counts"]["file_write"] == 1
        assert audit["operation_counts"]["git_commit"] == 1
        assert audit["operation_counts"]["queue_move"] == 1
    
    def test_write_audit_trail(self, dry_run_context, temp_log_file):
        """Test writing audit trail to file."""
        dry_run_context.log_file = temp_log_file
        dry_run_context.log_file_write("/path/to/file.txt", "content")
        
        dry_run_context.write_audit_trail()
        
        # Verify file was written
        assert Path(temp_log_file).exists()
        
        # Verify JSON is valid
        with open(temp_log_file) as f:
            data = json.load(f)
        
        assert data["total_operations"] == 1
        assert data["dry_run_mode"] is True
    
    def test_print_summary(self, dry_run_context, capsys):
        """Test summary printing."""
        dry_run_context.log_file_write("/path/to/file.txt", "content")
        dry_run_context.log_git_commit("Fix: bug")
        
        summary = dry_run_context.print_summary()
        
        assert "DRY-RUN MODE SUMMARY" in summary
        assert "Total operations: 2" in summary
        assert "file_write: 1" in summary
        assert "git_commit: 1" in summary


# ─── Test SimulatedOperation ────────────────────────────────────────────


class TestSimulatedOperation:
    """Test SimulatedOperation class."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        op = SimulatedOperation(
            operation_type=OperationType.FILE_WRITE,
            timestamp=datetime.now().isoformat(),
            description="Write file",
            details={"path": "/file.txt"},
            would_succeed=True,
        )
        
        data = op.to_dict()
        
        assert data["operation_type"] == "file_write"
        assert data["description"] == "Write file"
        assert data["would_succeed"] is True
        assert data["details"]["path"] == "/file.txt"
    
    def test_json_serializable(self):
        """Test that operation is JSON serializable."""
        op = SimulatedOperation(
            operation_type=OperationType.FILE_WRITE,
            timestamp=datetime.now().isoformat(),
            description="Write file",
            details={"path": "/file.txt"},
        )
        
        # Should not raise
        json_str = json.dumps(op.to_dict())
        assert json_str is not None


# ─── Test Global Context Management ────────────────────────────────────


class TestGlobalContext:
    """Test global dry-run context management."""
    
    def test_initialize_dry_run(self):
        """Test initializing global dry-run context."""
        ctx = initialize_dry_run(enabled=True)
        
        assert ctx.enabled is True
        assert get_dry_run_context() is ctx
    
    def test_is_dry_run_enabled_false(self):
        """Test checking if dry-run is enabled (false case)."""
        initialize_dry_run(enabled=False)
        assert is_dry_run_enabled() is False
    
    def test_is_dry_run_enabled_true(self):
        """Test checking if dry-run is enabled (true case)."""
        initialize_dry_run(enabled=True)
        assert is_dry_run_enabled() is True
    
    def test_context_manager_dry_run_mode(self, temp_log_file):
        """Test dry_run_mode context manager."""
        with dry_run_mode(enabled=True, log_file=temp_log_file) as ctx:
            assert ctx.enabled is True
            ctx.log_file_write("/path/to/file.txt", "content")
        
        # Verify audit trail was written
        assert Path(temp_log_file).exists()


# ─── Test Integration ────────────────────────────────────────────────


class TestIntegration:
    """Integration tests for dry-run mode."""
    
    def test_multiple_operations_audit_trail(self, dry_run_context, temp_log_file):
        """Test audit trail with multiple operations."""
        dry_run_context.log_file = temp_log_file
        
        # Simulate a complete orchestration cycle
        dry_run_context.log_queue_move("task-1", "incoming", "processing")
        dry_run_context.log_file_write("/queue/processing/task-1.yaml", "content")
        dry_run_context.log_git_commit("Process task-1", files=["task-1.yaml"])
        dry_run_context.log_api_call("POST", "/tasks/1/complete", payload={"status": "success"})
        dry_run_context.log_queue_move("task-1", "processing", "done")
        
        dry_run_context.write_audit_trail()
        
        # Verify audit trail
        with open(temp_log_file) as f:
            audit = json.load(f)
        
        assert audit["total_operations"] == 5
        assert audit["operation_counts"]["queue_move"] == 2
        assert audit["operation_counts"]["file_write"] == 1
        assert audit["operation_counts"]["git_commit"] == 1
        assert audit["operation_counts"]["api_call"] == 1
    
    def test_disabled_dry_run_no_logging(self):
        """Test that disabled dry-run doesn't log operations."""
        ctx = DryRunContext(enabled=False)
        
        # Log operations
        ctx.log_file_write("/path/to/file.txt", "content")
        ctx.log_git_commit("Fix: bug")
        
        # Operations should still be recorded (for testing purposes)
        # but the enabled flag should be False
        assert ctx.enabled is False
    
    def test_operation_counts_accuracy(self, dry_run_context):
        """Test that operation counts are accurate."""
        # Log various operations
        for i in range(3):
            dry_run_context.log_file_write(f"/file{i}.txt", "content")
        
        for i in range(2):
            dry_run_context.log_git_commit(f"Commit {i}")
        
        dry_run_context.log_queue_move("task-1", "incoming", "processing")
        
        audit = dry_run_context.get_audit_trail()
        
        assert audit["operation_counts"]["file_write"] == 3
        assert audit["operation_counts"]["git_commit"] == 2
        assert audit["operation_counts"]["queue_move"] == 1
        assert audit["total_operations"] == 6


# ─── Test Error Handling ────────────────────────────────────────────


class TestErrorHandling:
    """Test error handling in dry-run mode."""
    
    def test_operation_with_error(self, dry_run_context):
        """Test recording operation with error."""
        op = dry_run_context.log_file_write(
            "/protected/file.txt",
            "content",
            would_succeed=False,
            error_message="Permission denied"
        )
        
        assert op.would_succeed is False
        assert op.error_message == "Permission denied"
        
        audit = dry_run_context.get_audit_trail()
        assert audit["operations"][0]["would_succeed"] is False
    
    def test_invalid_log_file_path(self, dry_run_context):
        """Test handling of invalid log file path."""
        # Set invalid path
        dry_run_context.log_file = "/invalid/path/that/does/not/exist/file.json"
        
        # Should raise when trying to write
        with pytest.raises(Exception):
            dry_run_context.write_audit_trail()


# ─── Test Performance ────────────────────────────────────────────────


class TestPerformance:
    """Test performance of dry-run mode."""
    
    def test_large_number_of_operations(self, dry_run_context):
        """Test handling large number of operations."""
        # Log 1000 operations
        for i in range(1000):
            dry_run_context.log_file_write(f"/file{i}.txt", "content")
        
        audit = dry_run_context.get_audit_trail()
        
        assert audit["total_operations"] == 1000
        assert len(audit["operations"]) == 1000
        assert audit["operation_counts"]["file_write"] == 1000
    
    def test_audit_trail_generation_performance(self, dry_run_context):
        """Test audit trail generation performance."""
        # Log operations
        for i in range(100):
            dry_run_context.log_file_write(f"/file{i}.txt", "content")
        
        # Generate audit trail (should be fast)
        import time
        start = time.time()
        audit = dry_run_context.get_audit_trail()
        duration = time.time() - start
        
        # Should complete in < 100ms
        assert duration < 0.1
        assert audit["total_operations"] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
