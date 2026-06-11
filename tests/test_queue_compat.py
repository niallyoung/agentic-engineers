"""
Tests for Queue Path Migration Backward Compatibility Layer.

Tests the QueuePathMigration class which handles:
1. Detection of legacy queue paths
2. Validation of migration integrity
3. Diagnostics for migration planning
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from src.orchestration.queue_compat import QueuePathMigration


class TestQueuePathMigrationDetection:
    """Test detection of legacy queue paths."""
    
    def test_detect_legacy_queue_when_exists(self, tmp_path):
        """Detect legacy queue when it exists."""
        legacy_base = tmp_path / "legacy"
        legacy_base.mkdir()
        session_dir = legacy_base / "test-session-123"
        session_dir.mkdir()
        
        qm = QueuePathMigration(legacy_base=legacy_base)
        result = qm.detect_legacy_queue("test-session-123")
        
        assert result is not None
        assert result == session_dir
    
    def test_detect_legacy_queue_when_not_exists(self, tmp_path):
        """Return None when legacy queue doesn't exist."""
        legacy_base = tmp_path / "legacy"
        legacy_base.mkdir()
        
        qm = QueuePathMigration(legacy_base=legacy_base)
        result = qm.detect_legacy_queue("nonexistent-session")
        
        assert result is None
    
    def test_list_legacy_sessions(self, tmp_path):
        """List all sessions in legacy queue base."""
        legacy_base = tmp_path / "legacy"
        legacy_base.mkdir()
        
        # Create some sessions
        for i in range(3):
            (legacy_base / f"session-{i}").mkdir()
        
        # Create some non-session items (should be ignored if they start with .)
        (legacy_base / ".hidden").mkdir()
        
        qm = QueuePathMigration(legacy_base=legacy_base)
        sessions = qm.list_legacy_sessions()
        
        assert len(sessions) == 3
        assert "session-0" in sessions
        assert "session-1" in sessions
        assert "session-2" in sessions
    
    def test_list_legacy_sessions_when_base_not_exists(self, tmp_path):
        """Return empty list when legacy base doesn't exist."""
        legacy_base = tmp_path / "nonexistent" / "path"
        
        qm = QueuePathMigration(legacy_base=legacy_base)
        sessions = qm.list_legacy_sessions()
        
        assert sessions == []


class TestQueuePathMigrationContents:
    """Test reading queue contents from both paths."""
    
    def test_get_legacy_queue_contents(self, tmp_path):
        """Read contents of legacy queue."""
        legacy_base = tmp_path / "legacy"
        session_dir = legacy_base / "test-session" / "incoming"
        session_dir.mkdir(parents=True)
        
        # Create some task files
        (session_dir / "task1.yaml").touch()
        (session_dir / "task2.yaml").touch()
        
        qm = QueuePathMigration(legacy_base=legacy_base.parent / "legacy")
        contents = qm.get_legacy_queue_contents("test-session")
        
        assert contents["incoming"] == ["task1.yaml", "task2.yaml"]
        assert contents["processing"] == []
        assert contents["done"] == []
    
    def test_get_legacy_queue_contents_multiple_states(self, tmp_path):
        """Read contents from all queue states."""
        legacy_base = tmp_path / "legacy"
        session_dir = legacy_base / "test-session"
        
        for state in ["incoming", "processing", "done"]:
            state_dir = session_dir / state
            state_dir.mkdir(parents=True)
            for i in range(2):
                (state_dir / f"task-{state}-{i}.yaml").touch()
        
        qm = QueuePathMigration(legacy_base=legacy_base)
        contents = qm.get_legacy_queue_contents("test-session")
        
        assert len(contents["incoming"]) == 2
        assert len(contents["processing"]) == 2
        assert len(contents["done"]) == 2
    
    def test_get_new_queue_contents(self, tmp_path):
        """Read contents of new queue path."""
        new_base = tmp_path / "new"
        queue_dir = new_base / "claude" / "test-session" / "queue" / "incoming"
        queue_dir.mkdir(parents=True)
        
        (queue_dir / "new-task1.yaml").touch()
        (queue_dir / "new-task2.yaml").touch()
        
        qm = QueuePathMigration(new_base=new_base)
        contents = qm.get_new_queue_contents("test-session", "claude")
        
        assert contents["incoming"] == ["new-task1.yaml", "new-task2.yaml"]
        assert contents["failed"] == []
    
    def test_get_queue_contents_nonexistent_session(self, tmp_path):
        """Return empty dict when session doesn't exist."""
        legacy_base = tmp_path / "legacy"
        legacy_base.mkdir()
        
        qm = QueuePathMigration(legacy_base=legacy_base)
        contents = qm.get_legacy_queue_contents("nonexistent")
        
        assert contents == {"incoming": [], "processing": [], "done": []}


class TestQueuePathMigrationValidation:
    """Test migration validation logic."""
    
    def test_validate_migration_legacy_exists_new_missing(self, tmp_path):
        """Validate when legacy exists but new doesn't."""
        legacy_base = tmp_path / "legacy"
        new_base = tmp_path / "new"
        
        # Create legacy queue with tasks
        session_dir = legacy_base / "test-session" / "incoming"
        session_dir.mkdir(parents=True)
        (session_dir / "task.yaml").touch()
        
        qm = QueuePathMigration(legacy_base=legacy_base, new_base=new_base)
        result = qm.validate_migration("test-session", "copilot")
        
        assert result["status"] in ["success", "warning"]
        assert result["legacy_exists"] is True
        assert result["new_path_exists"] is False
        assert result["legacy_count"] == 1
        assert result["can_migrate"] is True
    
    def test_validate_migration_both_exist(self, tmp_path):
        """Validate when both legacy and new queues exist."""
        legacy_base = tmp_path / "legacy"
        new_base = tmp_path / "new"
        
        # Create legacy queue
        legacy_dir = legacy_base / "test-session" / "incoming"
        legacy_dir.mkdir(parents=True)
        (legacy_dir / "legacy-task.yaml").touch()
        
        # Create new queue
        new_dir = new_base / "copilot" / "test-session" / "queue" / "incoming"
        new_dir.mkdir(parents=True)
        (new_dir / "new-task.yaml").touch()
        
        qm = QueuePathMigration(legacy_base=legacy_base, new_base=new_base)
        result = qm.validate_migration("test-session", "copilot")
        
        assert result["status"] in ["success", "warning"]
        assert result["legacy_exists"] is True
        assert result["new_path_exists"] is True
        assert result["legacy_count"] == 1
        assert result["new_count"] == 1
        # Should warn about potential duplicates
        assert any("duplicates" in w.lower() for w in result["warnings"])
    
    def test_validate_migration_neither_exist(self, tmp_path):
        """Validate when neither queue exists."""
        legacy_base = tmp_path / "legacy"
        new_base = tmp_path / "new"
        
        legacy_base.mkdir()
        new_base.mkdir()
        
        qm = QueuePathMigration(legacy_base=legacy_base, new_base=new_base)
        result = qm.validate_migration("nonexistent-session", "copilot")
        
        assert result["status"] == "warning"
        assert result["legacy_exists"] is False
        assert result["new_path_exists"] is False
        assert result["can_migrate"] is False
    
    def test_validate_migration_contains_timestamp(self, tmp_path):
        """Validation result includes timestamp."""
        legacy_base = tmp_path / "legacy"
        legacy_base.mkdir()
        
        qm = QueuePathMigration(legacy_base=legacy_base)
        result = qm.validate_migration("test-session")
        
        assert "timestamp" in result
        assert result["timestamp"]  # Non-empty string


class TestQueuePathMigrationSummary:
    """Test batch migration summary."""
    
    def test_get_migration_summary_no_sessions(self, tmp_path):
        """Get summary when no legacy sessions exist."""
        legacy_base = tmp_path / "legacy"
        legacy_base.mkdir()
        
        qm = QueuePathMigration(legacy_base=legacy_base)
        summary = qm.get_migration_summary()
        
        assert summary["legacy_sessions"] == []
        assert summary["total_legacy_items"] == 0
        assert summary["validations"] == {}
    
    def test_get_migration_summary_with_sessions(self, tmp_path):
        """Get summary with multiple sessions."""
        legacy_base = tmp_path / "legacy"
        
        # Create multiple sessions with tasks
        for session_num in range(2):
            session_dir = legacy_base / f"session-{session_num}" / "incoming"
            session_dir.mkdir(parents=True)
            for i in range(2):
                (session_dir / f"task-{i}.yaml").touch()
        
        qm = QueuePathMigration(legacy_base=legacy_base)
        summary = qm.get_migration_summary()
        
        assert len(summary["legacy_sessions"]) == 2
        assert summary["total_legacy_items"] == 4  # 2 sessions * 2 tasks each
        assert "validations" in summary
        assert len(summary["validations"]) == 2
    
    def test_get_migration_summary_contains_timestamp(self, tmp_path):
        """Summary includes timestamp."""
        legacy_base = tmp_path / "legacy"
        legacy_base.mkdir()
        
        qm = QueuePathMigration(legacy_base=legacy_base)
        summary = qm.get_migration_summary()
        
        assert "timestamp" in summary
        assert summary["timestamp"]


class TestQueuePathMigrationInitialization:
    """Test initialization with custom paths."""
    
    def test_initialization_with_custom_paths(self, tmp_path):
        """Initialize with custom legacy and new base paths."""
        custom_legacy = tmp_path / "custom_legacy"
        custom_new = tmp_path / "custom_new"
        
        custom_legacy.mkdir()
        custom_new.mkdir()
        
        qm = QueuePathMigration(legacy_base=custom_legacy, new_base=custom_new)
        
        assert qm.legacy_base == custom_legacy
        assert qm.new_base == custom_new
    
    def test_initialization_with_default_paths(self):
        """Initialize with default paths."""
        qm = QueuePathMigration()

        assert qm.legacy_base == Path.home() / ".copilot" / "queue"
        assert qm.new_base == Path.home() / ".agentic-engineers"
    
    def test_initialization_with_partial_override(self, tmp_path):
        """Initialize with only legacy base override."""
        custom_legacy = tmp_path / "custom_legacy"
        custom_legacy.mkdir()

        qm = QueuePathMigration(legacy_base=custom_legacy)

        assert qm.legacy_base == custom_legacy
        assert qm.new_base == Path.home() / ".agentic-engineers"


class TestQueuePathMigrationEdgeCases:
    """Test edge cases and error handling."""
    
    def test_detection_with_multiple_harnesses(self, tmp_path):
        """Handle multiple harnesses in new queue structure."""
        new_base = tmp_path / "new"
        
        # Create queues for multiple harnesses
        for harness in ["claude", "copilot", "gpt"]:
            queue_dir = new_base / harness / "test-session" / "queue"
            (queue_dir / "incoming").mkdir(parents=True)
            (queue_dir / "incoming" / "task.yaml").touch()
        
        qm = QueuePathMigration(new_base=new_base)
        
        for harness in ["claude", "copilot", "gpt"]:
            contents = qm.get_new_queue_contents("test-session", harness)
            assert len(contents["incoming"]) == 1
    
    def test_contents_with_non_yaml_files(self, tmp_path):
        """Ignore non-YAML files when reading queue contents."""
        legacy_base = tmp_path / "legacy"
        session_dir = legacy_base / "test-session" / "incoming"
        session_dir.mkdir(parents=True)
        
        # Create mix of YAML and non-YAML files
        (session_dir / "task.yaml").touch()
        (session_dir / "readme.txt").touch()
        (session_dir / "data.json").touch()
        
        qm = QueuePathMigration(legacy_base=legacy_base)
        contents = qm.get_legacy_queue_contents("test-session")
        
        # Should only include .yaml files
        assert contents["incoming"] == ["task.yaml"]
    
    def test_sorted_file_listings(self, tmp_path):
        """File listings are sorted alphabetically."""
        legacy_base = tmp_path / "legacy"
        session_dir = legacy_base / "test-session" / "incoming"
        session_dir.mkdir(parents=True)
        
        # Create files in non-alphabetical order
        for name in ["zebra.yaml", "apple.yaml", "middle.yaml"]:
            (session_dir / name).touch()
        
        qm = QueuePathMigration(legacy_base=legacy_base)
        contents = qm.get_legacy_queue_contents("test-session")
        
        assert contents["incoming"] == ["apple.yaml", "middle.yaml", "zebra.yaml"]
