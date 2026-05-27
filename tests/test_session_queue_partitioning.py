"""
Test Suite for Session-ID Based Queue Partitioning

⚠️ DEPENDENT ON LEGACY QUEUE BEHAVIOR (NOW REMOVED)
These tests cover session-ID based queue partitioning and legacy queue migration,
which have been removed as of 2026-05-26. The new canonical queue path structure
no longer supports these features.

Tests cover:
- Session-ID detection from environment variable
- Session-ID detection from filesystem
- Queue path partitioning by session-id
- Legacy queue migration (DEPRECATED)
- Multiple concurrent sessions isolation
- Backward compatibility (REMOVED)

TESTS SKIPPED: These require legacy queue structure that no longer exists.
See tests/test_queue_path_centralization.py for new canonical path tests.
"""

import os
import yaml
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

# Skip all tests in this module - test legacy functionality that was removed
pytestmark = pytest.mark.skip(
    reason="Legacy queue partitioning tests (functionality removed). "
           "See tests/test_queue_path_centralization.py for canonical path tests."
)
import sys

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import QueueManager from src.orchestration.agents.orchestrator
try:
    from src.orchestration.agents.orchestrator import QueueManager
except ImportError as e:
    # If that fails, try direct file import by modifying the path
    sys.path.insert(0, str(Path(__file__).parent))
    # This will fail with relative imports, so we'll skip those tests
    print(f"Warning: Could not import QueueManager: {e}")


class TestSessionIDDetection:
    """Test session-id detection logic."""
    
    def test_detect_session_id_from_env_copilot(self):
        """Test detection of session-id from COPILOT_SESSION_ID environment variable."""
        test_session_id = "54744939-4acb-430c-b2c4-3b8322289d0b"
        
        with patch.dict(os.environ, {"COPILOT_SESSION_ID": test_session_id}):
            detected_id = QueueManager.detect_session_id()
            assert detected_id == test_session_id
    
    def test_detect_session_id_from_env_claude(self):
        """Test detection of session-id from CLAUDE_SESSION_ID environment variable."""
        test_session_id = "606ff436-b44b-47c5-90b8-f4bcc3fdb413"
        
        with patch.dict(os.environ, {"CLAUDE_SESSION_ID": test_session_id}, clear=False):
            # Remove COPILOT_SESSION_ID if present
            env = os.environ.copy()
            if "COPILOT_SESSION_ID" in env:
                del env["COPILOT_SESSION_ID"]
            
            with patch.dict(os.environ, env, clear=True):
                with patch.dict(os.environ, {"CLAUDE_SESSION_ID": test_session_id}):
                    detected_id = QueueManager.detect_session_id()
                    assert detected_id == test_session_id
    
    def test_detect_session_id_from_filesystem_copilot(self):
        """Test detection of session-id from ~/.copilot/session-state/ filesystem scan."""
        test_session_id = "54744939-4acb-430c-b2c4-3b8322289d0b"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock session-state structure
            session_state_dir = Path(tmpdir) / ".copilot" / "session-state"
            session_dir = session_state_dir / test_session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            
            # Mock home() to return tmpdir
            with patch("src.orchestration.agents.orchestrator.Path.home", return_value=Path(tmpdir)):
                detected_id = QueueManager.detect_session_id()
                assert detected_id == test_session_id
    
    def test_detect_session_id_returns_most_recent_session(self):
        """Test that detection returns most recently modified session directory."""
        session_id_1 = "54744939-4acb-430c-b2c4-3b8322289d0b"
        session_id_2 = "606ff436-b44b-47c5-90b8-f4bcc3fdb413"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            session_state_dir = Path(tmpdir) / ".copilot" / "session-state"
            
            # Create two session directories
            dir_1 = session_state_dir / session_id_1
            dir_2 = session_state_dir / session_id_2
            dir_1.mkdir(parents=True, exist_ok=True)
            dir_2.mkdir(parents=True, exist_ok=True)
            
            # Make dir_2 more recently modified
            import time
            time.sleep(0.1)
            dir_2.touch()
            
            with patch("src.orchestration.agents.orchestrator.Path.home", return_value=Path(tmpdir)):
                detected_id = QueueManager.detect_session_id()
                assert detected_id == session_id_2
    
    def test_detect_session_id_raises_error_when_not_found(self):
        """Test that detection raises RuntimeError when session-id cannot be found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Clear environment variables
            env = {}
            
            with patch.dict(os.environ, env, clear=True):
                with patch("src.orchestration.agents.orchestrator.Path.home", return_value=Path(tmpdir)):
                    with pytest.raises(RuntimeError, match="Could not detect session-id"):
                        QueueManager.detect_session_id()


class TestQueuePathPartitioning:
    """Test that queue paths are properly partitioned by session-id."""
    
    def test_queue_paths_include_session_id(self):
        """Test that queue directories include session-id in path."""
        test_session_id = "54744939-4acb-430c-b2c4-3b8322289d0b"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "queue"
            queue_dir.mkdir()
            
            with patch.dict(os.environ, {"COPILOT_SESSION_ID": test_session_id}):
                qm = QueueManager(queue_dir=str(queue_dir))
                
                # Check that paths include session-id
                assert test_session_id in str(qm.session_queue_dir)
                assert test_session_id in str(qm.incoming_dir)
                assert test_session_id in str(qm.processing_dir)
                assert test_session_id in str(qm.done_dir)
    
    def test_get_queue_dir_methods(self):
        """Test the get_*_queue_dir() accessor methods."""
        test_session_id = "54744939-4acb-430c-b2c4-3b8322289d0b"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "queue"
            queue_dir.mkdir()
            
            with patch.dict(os.environ, {"COPILOT_SESSION_ID": test_session_id}):
                qm = QueueManager(queue_dir=str(queue_dir))
                
                # Test getter methods
                incoming = qm.get_incoming_queue_dir()
                processing = qm.get_processing_queue_dir()
                done = qm.get_done_queue_dir()
                
                assert incoming.exists()
                assert processing.exists()
                assert done.exists()
                
                assert test_session_id in str(incoming)
                assert test_session_id in str(processing)
                assert test_session_id in str(done)
    
    def test_multiple_sessions_use_separate_queues(self):
        """Test that different sessions use separate queue partitions."""
        session_id_1 = "54744939-4acb-430c-b2c4-3b8322289d0b"
        session_id_2 = "606ff436-b44b-47c5-90b8-f4bcc3fdb413"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "queue"
            queue_dir.mkdir()
            
            # Create queue manager for session 1
            with patch.dict(os.environ, {"COPILOT_SESSION_ID": session_id_1}):
                qm1 = QueueManager(queue_dir=str(queue_dir))
                incoming1 = qm1.get_incoming_queue_dir()
            
            # Create queue manager for session 2
            with patch.dict(os.environ, {"COPILOT_SESSION_ID": session_id_2}):
                qm2 = QueueManager(queue_dir=str(queue_dir))
                incoming2 = qm2.get_incoming_queue_dir()
            
            # Verify they use different directories
            assert str(incoming1) != str(incoming2)
            assert session_id_1 in str(incoming1)
            assert session_id_2 in str(incoming2)


class TestLegacyQueueMigration:
    """Test legacy queue migration from old structure to session-id partitioned."""
    
    def test_migrate_legacy_queue_copies_files(self):
        """Test that migration copies files from old to new location."""
        test_session_id = "54744939-4acb-430c-b2c4-3b8322289d0b"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "queue"
            queue_dir.mkdir()
            
            # Create legacy queue structure with test files
            old_incoming = queue_dir / "incoming"
            old_incoming.mkdir()
            task_file = old_incoming / "task-001.yaml"
            task_data = {"task_id": "task-001", "title": "Test task"}
            with open(task_file, 'w') as f:
                yaml.dump(task_data, f)
            
            with patch.dict(os.environ, {"COPILOT_SESSION_ID": test_session_id}):
                qm = QueueManager(queue_dir=str(queue_dir))
                
                # Check that file was copied to new location
                new_file_path = qm.incoming_dir / "task-001.yaml"
                assert new_file_path.exists()
                
                # Verify content is preserved
                with open(new_file_path) as f:
                    content = yaml.safe_load(f)
                    assert content["task_id"] == "task-001"
    
    def test_migrate_legacy_queue_renames_old_dirs(self):
        """Test that migration renames old directories to backup."""
        test_session_id = "54744939-4acb-430c-b2c4-3b8322289d0b"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "queue"
            queue_dir.mkdir()
            
            # Create legacy queue structure
            old_incoming = queue_dir / "incoming"
            old_incoming.mkdir()
            old_incoming_file = old_incoming / "task-001.yaml"
            with open(old_incoming_file, 'w') as f:
                yaml.dump({"task_id": "task-001"}, f)
            
            with patch.dict(os.environ, {"COPILOT_SESSION_ID": test_session_id}):
                qm = QueueManager(queue_dir=str(queue_dir))
                
                # Check that old directory no longer exists
                assert not (queue_dir / "incoming").exists()
                
                # Check that backup directory was created
                backup_dirs = list(queue_dir.glob("incoming-legacy-*"))
                assert len(backup_dirs) == 1
    
    def test_migrate_creates_migration_log(self):
        """Test that migration creates a .migration-log file."""
        test_session_id = "54744939-4acb-430c-b2c4-3b8322289d0b"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "queue"
            queue_dir.mkdir()
            
            # Create legacy queue structure
            old_incoming = queue_dir / "incoming"
            old_incoming.mkdir()
            old_incoming_file = old_incoming / "task-001.yaml"
            with open(old_incoming_file, 'w') as f:
                yaml.dump({"task_id": "task-001"}, f)
            
            with patch.dict(os.environ, {"COPILOT_SESSION_ID": test_session_id}):
                qm = QueueManager(queue_dir=str(queue_dir))
                
                # Check migration log exists
                migration_log_path = queue_dir / ".migration-log"
                assert migration_log_path.exists()
                
                # Verify log content
                with open(migration_log_path) as f:
                    log = yaml.safe_load(f)
                    assert isinstance(log, list)
                    assert log[-1]["action"] == "migration_completed"
                    assert log[-1]["status"] == "success"
    
    def test_no_migration_if_already_partitioned(self):
        """Test that migration skips if queue is already partitioned."""
        test_session_id = "54744939-4acb-430c-b2c4-3b8322289d0b"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "queue"
            queue_dir.mkdir()
            
            # Create already-partitioned structure
            session_dir = queue_dir / test_session_id
            session_dir.mkdir()
            (session_dir / "incoming").mkdir()
            (session_dir / "processing").mkdir()
            (session_dir / "done").mkdir()
            
            with patch.dict(os.environ, {"COPILOT_SESSION_ID": test_session_id}):
                qm = QueueManager(queue_dir=str(queue_dir))
                
                # No migration log should be created (already partitioned)
                migration_log_path = queue_dir / ".migration-log"
                assert not migration_log_path.exists()
    
    def test_no_migration_if_no_old_structure(self):
        """Test that migration skips if old queue structure doesn't exist."""
        test_session_id = "54744939-4acb-430c-b2c4-3b8322289d0b"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "queue"
            queue_dir.mkdir()
            
            # No old queue structure created
            
            with patch.dict(os.environ, {"COPILOT_SESSION_ID": test_session_id}):
                qm = QueueManager(queue_dir=str(queue_dir))
                
                # No migration log should be created
                migration_log_path = queue_dir / ".migration-log"
                assert not migration_log_path.exists()


class TestQueueOperationsWithSessionID:
    """Test that queue operations work correctly with session-id partitioning."""
    
    def test_list_incoming_tasks_uses_session_partition(self):
        """Test that list_incoming_tasks() reads from session partition."""
        test_session_id = "54744939-4acb-430c-b2c4-3b8322289d0b"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "queue"
            queue_dir.mkdir()
            
            with patch.dict(os.environ, {"COPILOT_SESSION_ID": test_session_id}):
                qm = QueueManager(queue_dir=str(queue_dir))
                
                # Add a task to the session's incoming queue
                task_file = qm.incoming_dir / "task-001.yaml"
                with open(task_file, 'w') as f:
                    yaml.dump({"task_id": "task-001"}, f)
                
                # Verify list includes it
                tasks = qm.list_incoming_tasks()
                assert "task-001.yaml" in tasks
    
    def test_session_isolation_no_cross_contamination(self):
        """Test that different sessions' tasks don't interfere."""
        session_id_1 = "54744939-4acb-430c-b2c4-3b8322289d0b"
        session_id_2 = "606ff436-b44b-47c5-90b8-f4bcc3fdb413"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "queue"
            queue_dir.mkdir()
            
            # Create task in session 1
            with patch.dict(os.environ, {"COPILOT_SESSION_ID": session_id_1}):
                qm1 = QueueManager(queue_dir=str(queue_dir))
                task_file_1 = qm1.incoming_dir / "task-session1.yaml"
                with open(task_file_1, 'w') as f:
                    yaml.dump({"task_id": "task-session1"}, f)
            
            # Create task in session 2
            with patch.dict(os.environ, {"COPILOT_SESSION_ID": session_id_2}):
                qm2 = QueueManager(queue_dir=str(queue_dir))
                task_file_2 = qm2.incoming_dir / "task-session2.yaml"
                with open(task_file_2, 'w') as f:
                    yaml.dump({"task_id": "task-session2"}, f)
            
            # Verify session 1 only sees its own task
            with patch.dict(os.environ, {"COPILOT_SESSION_ID": session_id_1}):
                qm1 = QueueManager(queue_dir=str(queue_dir))
                tasks_1 = qm1.list_incoming_tasks()
                assert "task-session1.yaml" in tasks_1
                assert "task-session2.yaml" not in tasks_1
            
            # Verify session 2 only sees its own task
            with patch.dict(os.environ, {"COPILOT_SESSION_ID": session_id_2}):
                qm2 = QueueManager(queue_dir=str(queue_dir))
                tasks_2 = qm2.list_incoming_tasks()
                assert "task-session2.yaml" in tasks_2
                assert "task-session1.yaml" not in tasks_2


class TestBackwardCompatibility:
    """Test backward compatibility with old queue structure."""
    
    def test_fallback_to_default_session_if_detection_fails(self):
        """Test that QueueManager handles session-id detection failure gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_dir = Path(tmpdir) / "queue"
            queue_dir.mkdir()
            
            # Force session-id detection to fail
            with patch.dict(os.environ, {}, clear=True):
                with patch("pathlib.Path.home", return_value=Path(tmpdir)):
                    qm = QueueManager(queue_dir=str(queue_dir))
                    
                    # Should fall back to "default" session-id
                    assert "default" in str(qm.session_queue_dir) or "default" == qm.session_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
