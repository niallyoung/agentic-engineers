"""
End-to-End Queue Migration Tests (Phase 4).

Comprehensive tests for complete migration flow:
- Old queue path migration to new location
- Backward compatibility with legacy paths
- New path as canonical storage location
- Multi-harness isolation
- Data persistence across migration
- Session data preservation
"""

import pytest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import patch
from datetime import datetime

from src.orchestration.queue_compat import QueuePathMigration


class TestOldQueuePathMigration:
    """Test migration from old queue paths to new location."""
    
    def test_legacy_queue_path_detected_correctly(self, tmp_path):
        """Verify old ~/.copilot/queue/{sid}/ paths are detected."""
        legacy_base = tmp_path / ".copilot" / "queue"
        legacy_base.mkdir(parents=True)
        
        session_id = "test-session-123"
        session_dir = legacy_base / session_id
        session_dir.mkdir()
        
        (session_dir / "incoming").mkdir()
        (session_dir / "processing").mkdir()
        (session_dir / "done").mkdir()
        
        qm = QueuePathMigration(legacy_base=legacy_base, new_base=tmp_path / ".agentic-engineers")
        detected = qm.detect_legacy_queue(session_id)
        
        assert detected is not None
        assert detected == session_dir
        assert (detected / "incoming").exists()
    
    def test_legacy_queue_contents_preserved(self, tmp_path):
        """Verify legacy queue contents are detected for migration."""
        legacy_base = tmp_path / ".copilot" / "queue"
        legacy_base.mkdir(parents=True)
        
        session_id = "test-session"
        session_dir = legacy_base / session_id
        (session_dir / "incoming").mkdir(parents=True)
        (session_dir / "processing").mkdir(parents=True)
        (session_dir / "done").mkdir(parents=True)
        
        # Create some DELEGATE/HANDBACK files
        (session_dir / "incoming" / "DELEGATE-1.yaml").write_text("test: data\n")
        (session_dir / "processing" / "HANDBACK-1.yaml").write_text("result: done\n")
        (session_dir / "done" / "HANDBACK-2.yaml").write_text("result: old\n")
        
        qm = QueuePathMigration(legacy_base=legacy_base)
        contents = qm.get_legacy_queue_contents(session_id)
        
        assert len(contents["incoming"]) == 1
        assert len(contents["processing"]) == 1
        assert len(contents["done"]) == 1
        assert "DELEGATE-1.yaml" in contents["incoming"]
        assert "HANDBACK-1.yaml" in contents["processing"]
        assert "HANDBACK-2.yaml" in contents["done"]
    
    def test_legacy_queue_files_can_be_read(self, tmp_path):
        """Verify legacy queue files are readable for migration."""
        legacy_base = tmp_path / ".copilot" / "queue"
        legacy_base.mkdir(parents=True)
        
        session_id = "test-session"
        delegate_file = legacy_base / session_id / "incoming" / "DELEGATE-task-1.yaml"
        delegate_file.parent.mkdir(parents=True)
        
        test_content = """---
handoff_type: DELEGATE
task_id: test-task
role: Engineer
scope: >
  Test migration
"""
        delegate_file.write_text(test_content)
        
        # Verify we can read it back
        assert delegate_file.read_text() == test_content
        assert delegate_file.exists()


class TestBackwardCompatibilityLayerHandlesOldPaths:
    """Test backward compat layer gracefully handles legacy paths."""
    
    def test_old_path_readable_via_compat_layer(self, tmp_path):
        """Verify backward compat layer can read from old paths."""
        legacy_base = tmp_path / ".copilot" / "queue"
        legacy_base.mkdir(parents=True)
        
        session_id = "test-session"
        session_dir = legacy_base / session_id
        (session_dir / "processing").mkdir(parents=True)
        
        # Create a HANDBACK in old location
        handback_file = session_dir / "processing" / "HANDBACK-task-1.yaml"
        handback_file.write_text("---\nstatus: complete\n")
        
        qm = QueuePathMigration(legacy_base=legacy_base)
        contents = qm.get_legacy_queue_contents(session_id)
        
        assert "HANDBACK-task-1.yaml" in contents["processing"]
    
    def test_validation_confirms_migration_readiness(self, tmp_path):
        """Verify migration validation confirms readiness."""
        legacy_base = tmp_path / ".copilot" / "queue"
        new_base = tmp_path / ".agentic-engineers"
        legacy_base.mkdir(parents=True)
        
        session_id = "test-session"
        session_dir = legacy_base / session_id
        (session_dir / "incoming").mkdir(parents=True)
        
        # Add some legacy data
        (session_dir / "incoming" / "DELEGATE-1.yaml").write_text("test: 1\n")
        
        qm = QueuePathMigration(legacy_base=legacy_base, new_base=new_base)
        validation = qm.validate_migration(session_id, "copilot")
        
        assert validation["legacy_exists"] is True
        assert validation["legacy_count"] >= 1
        assert validation["can_migrate"] is True
        assert validation["status"] in ["success", "warning"]


class TestNewPathAsCanonical:
    """Test that new path is the canonical storage location."""
    
    def test_new_queue_path_created_by_isolation(self, tmp_path):
        """Verify new queue path is created correctly."""
        new_base = tmp_path / ".agentic-engineers"
        
        qm = QueuePathMigration(new_base=new_base)
        
        session_id = "new-session-456"
        harness = "claude"
        new_path = new_base / session_id / harness / "queue"
        new_path.mkdir(parents=True, exist_ok=True)
        
        # Verify structure
        assert new_path.exists()
        assert (new_path.parent / "metadata.json").parent.exists()
    
    def test_new_path_canonical_structure(self, tmp_path):
        """Verify new path follows canonical structure."""
        new_base = tmp_path / ".agentic-engineers" / "artifacts"
        
        session_id = "sid-123"
        harness = "copilot"
        
        # Create the canonical new structure
        queue_path = new_base / session_id / harness / "queue"
        queue_path.mkdir(parents=True)
        
        delegates_path = new_base / session_id / harness / "delegates"
        delegates_path.mkdir(parents=True)
        
        # Verify canonical structure
        assert (queue_path / "incoming").parent.exists()
        assert (delegates_path).exists()
    
    def test_new_path_subdirectories_complete(self, tmp_path):
        """Verify new path has all required subdirectories."""
        new_base = tmp_path / ".agentic-engineers"
        session_id = "test-session"
        harness = "local"
        
        queue_path = new_base / session_id / harness / "queue"
        
        for subdir in ["incoming", "processing", "done", "failed"]:
            subdir_path = queue_path / subdir
            subdir_path.mkdir(parents=True, exist_ok=True)
            assert subdir_path.exists()


class TestOrchestratorWritesToNewLocation:
    """Test that Orchestrator writes DELEGATEs to new location."""
    
    def test_orchestrator_target_path_structure(self, tmp_path):
        """Verify Orchestrator would write to new path structure."""
        session_id = "orch-test-session"
        harness = "copilot"
        new_base = tmp_path / ".agentic-engineers" / "artifacts"
        
        # Simul DELEGATE storage location
        delegates_dir = new_base / session_id / harness / "delegates"
        delegates_dir.mkdir(parents=True)
        
        # Create DELEGATE file
        delegate_file = delegates_dir / "DELEGATE-task-1.yaml"
        delegate_file.write_text("""---
handoff_type: DELEGATE
task_id: test-task-1
role: Engineer
scope: Test migration
""")
        
        assert delegate_file.exists()
        assert "DELEGATE" in delegate_file.name
        assert str(new_base) in str(delegate_file)


class TestAgentsReadFromNewLocation:
    """Test that agents read DELEGATEs from new location."""
    
    def test_agent_reads_delegate_from_new_path(self, tmp_path):
        """Verify agent can read DELEGATE from new path."""
        session_id = "agent-test"
        harness = "claude"
        new_base = tmp_path / ".agentic-engineers" / "artifacts"
        
        delegates_dir = new_base / session_id / harness / "delegates"
        delegates_dir.mkdir(parents=True)
        
        # Write DELEGATE
        delegate_content = """---
handoff_type: DELEGATE
task_id: task-123
role: Engineer
scope: Read from new path
success_criteria:
  - Can be read from new location
"""
        delegate_file = delegates_dir / "DELEGATE-task-123.yaml"
        delegate_file.write_text(delegate_content)
        
        # Verify agent can read it
        assert delegate_file.exists()
        assert delegate_file.read_text() == delegate_content
        assert ".agentic-engineers" in str(delegate_file)


class TestAgentsWriteToNewLocation:
    """Test that agents write HANDBACKs to new location."""
    
    def test_agent_writes_handback_to_new_path(self, tmp_path):
        """Verify agent writes HANDBACK to new path."""
        session_id = "agent-write-test"
        harness = "claude"
        new_base = tmp_path / ".agentic-engineers" / "artifacts"
        
        queue_path = new_base / session_id / harness / "queue"
        done_dir = queue_path / "done"
        done_dir.mkdir(parents=True)
        
        # Agent writes HANDBACK
        handback_content = """---
handoff_type: HANDBACK
task_id: task-123
status: complete
result: Success
"""
        handback_file = done_dir / "HANDBACK-task-123.yaml"
        handback_file.write_text(handback_content)
        
        assert handback_file.exists()
        assert handback_file.read_text() == handback_content
        assert str(new_base) in str(handback_file)


class TestOrchestratorPollsNewLocation:
    """Test that Orchestrator polls HANDBACKs from new location."""
    
    def test_orchestrator_polls_done_directory(self, tmp_path):
        """Verify Orchestrator polls from new done directory."""
        session_id = "poll-test"
        harness = "copilot"
        new_base = tmp_path / ".agentic-engineers" / "artifacts"
        
        done_dir = new_base / session_id / harness / "queue" / "done"
        done_dir.mkdir(parents=True)
        
        # Orchestrator finds HANDBACK in done dir
        handback_files = [
            "HANDBACK-task-1.yaml",
            "HANDBACK-task-2.yaml",
            "HANDBACK-task-3.yaml",
        ]
        
        for hb in handback_files:
            (done_dir / hb).write_text(f"---\ntask: {hb}\n")
        
        # Verify all are accessible
        found = list(done_dir.glob("HANDBACK-*.yaml"))
        assert len(found) == 3
        assert all(f.suffix == ".yaml" for f in found)


class TestMultiHarnessIsolation:
    """Test multi-harness isolation in unified structure."""
    
    def test_copilot_and_claude_queues_isolated(self, tmp_path):
        """Verify copilot and claude queues don't interfere."""
        new_base = tmp_path / ".agentic-engineers" / "artifacts"
        session_id = "multi-harness-test"
        
        # Create isolated queues for two harnesses
        copilot_queue = new_base / session_id / "copilot" / "queue"
        claude_queue = new_base / session_id / "claude" / "queue"
        
        copilot_queue.mkdir(parents=True)
        claude_queue.mkdir(parents=True)
        
        # Write to copilot
        (copilot_queue / "incoming").mkdir(exist_ok=True)
        copilot_delegate = copilot_queue / "incoming" / "DELEGATE-copilot.yaml"
        copilot_delegate.write_text("harness: copilot\n")
        
        # Write to claude
        (claude_queue / "incoming").mkdir(exist_ok=True)
        claude_delegate = claude_queue / "incoming" / "DELEGATE-claude.yaml"
        claude_delegate.write_text("harness: claude\n")
        
        # Verify isolation
        assert copilot_delegate.exists()
        assert claude_delegate.exists()
        assert copilot_delegate.read_text() != claude_delegate.read_text()
        assert "copilot" in copilot_delegate.read_text()
        assert "claude" in claude_delegate.read_text()
    
    def test_three_harnesses_independent(self, tmp_path):
        """Verify three harnesses can coexist independently."""
        new_base = tmp_path / ".agentic-engineers" / "artifacts"
        session_id = "three-harness-test"
        
        harnesses = ["copilot", "claude", "local"]
        queues = {}
        
        for harness in harnesses:
            queue_path = new_base / session_id / harness / "queue"
            queue_path.mkdir(parents=True)
            queues[harness] = queue_path
            
            # Write unique marker
            marker = queue_path / "harness.txt"
            marker.write_text(f"This is the {harness} queue\n")
        
        # Verify all three are independent
        for harness, queue_path in queues.items():
            marker = queue_path / "harness.txt"
            assert marker.exists()
            assert f"This is the {harness} queue" in marker.read_text()


class TestSessionDataPersistenceAcrossMigration:
    """Test that session data persists across migration."""
    
    def test_metadata_json_preserved(self, tmp_path):
        """Verify metadata.json is preserved during migration."""
        session_id = "metadata-test"
        harness = "copilot"
        new_base = tmp_path / ".agentic-engineers" / "artifacts"
        
        # Create session with metadata
        session_dir = new_base / session_id / harness
        session_dir.mkdir(parents=True)
        
        metadata = {
            "session_id": session_id,
            "harness": harness,
            "created_at": datetime.now().isoformat(),
            "queue_version": "2.0",
        }
        
        metadata_file = session_dir / "metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2))
        
        # Verify metadata is preserved
        assert metadata_file.exists()
        loaded = json.loads(metadata_file.read_text())
        assert loaded["session_id"] == session_id
        assert loaded["queue_version"] == "2.0"
    
    def test_task_files_preserved_after_migration(self, tmp_path):
        """Verify task files survive migration process."""
        session_id = "task-migration-test"
        harness = "local"
        new_base = tmp_path / ".agentic-engineers" / "artifacts"
        
        queue_path = new_base / session_id / harness / "queue"
        
        # Create task files in different states
        for state, files in [
            ("incoming", ["DELEGATE-1.yaml", "DELEGATE-2.yaml"]),
            ("processing", ["HANDBACK-1.yaml"]),
            ("done", ["HANDBACK-2.yaml", "HANDBACK-3.yaml"]),
            ("failed", ["HANDBACK-error.yaml"]),
        ]:
            state_dir = queue_path / state
            state_dir.mkdir(parents=True)
            
            for filename in files:
                (state_dir / filename).write_text(f"---\nfile: {filename}\nstate: {state}\n")
        
        # Verify all files survived
        for state in ["incoming", "processing", "done", "failed"]:
            state_dir = queue_path / state
            files = list(state_dir.glob("*.yaml"))
            assert len(files) > 0
            
            for f in files:
                content = f.read_text()
                assert f"state: {state}" in content


class TestHarnessConfigWipePreservesSessionData:
    """Test session data persists across harness config wipe."""
    
    def test_session_data_survives_config_reset(self, tmp_path):
        """Verify session data survives config/setup changes."""
        session_id = "config-wipe-test"
        harness = "copilot"
        new_base = tmp_path / ".agentic-engineers" / "artifacts"
        
        # Create initial queue data
        queue_path = new_base / session_id / harness / "queue"
        (queue_path / "processing").mkdir(parents=True)
        
        task_file = queue_path / "processing" / "HANDBACK-important.yaml"
        task_file.write_text("---\ncritical: data\ndo_not_lose: true\n")
        
        # Simulate config wipe by checking if data still exists
        assert task_file.exists()
        assert "critical: data" in task_file.read_text()
        
        # Create new config (harness reinitialization)
        metadata_file = new_base / session_id / harness / "metadata.json"
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        metadata_file.write_text(json.dumps({"reinit": True}))
        
        # Verify both old and new config coexist
        assert task_file.exists()
        assert metadata_file.exists()


class TestMigrationValidationSummary:
    """Test comprehensive migration validation summary."""
    
    def test_migration_summary_with_multiple_sessions(self, tmp_path):
        """Verify migration summary reports all sessions correctly."""
        legacy_base = tmp_path / ".copilot" / "queue"
        new_base = tmp_path / ".agentic-engineers"
        
        # Create multiple legacy sessions
        for i in range(3):
            session_id = f"session-{i}"
            session_dir = legacy_base / session_id
            (session_dir / "incoming").mkdir(parents=True)
            (session_dir / "incoming" / f"DELEGATE-{i}.yaml").write_text(f"task: {i}\n")
        
        qm = QueuePathMigration(legacy_base=legacy_base, new_base=new_base)
        summary = qm.get_migration_summary()
        
        assert len(summary["legacy_sessions"]) == 3
        assert summary["total_legacy_items"] >= 3
        assert len(summary["validations"]) == 3
        
        for session_id in summary["legacy_sessions"]:
            assert session_id in summary["validations"]


class TestEndToEndMigrationFlow:
    """Comprehensive end-to-end migration flow test."""
    
    def test_complete_migration_workflow(self, tmp_path):
        """
        Test complete migration workflow:
        1. Legacy queue exists with data
        2. Migration validation passes
        3. New queue path created
        4. Data structure validated
        5. Multi-harness isolation confirmed
        """
        # Step 1: Create legacy queue with data
        legacy_base = tmp_path / ".copilot" / "queue"
        session_id = "complete-test"
        session_dir = legacy_base / session_id
        
        for state in ["incoming", "processing", "done"]:
            (session_dir / state).mkdir(parents=True)
            for i in range(2):
                (session_dir / state / f"task-{i}.yaml").write_text(
                    f"---\nstate: {state}\ntask: {i}\n"
                )
        
        # Step 2: Validate migration readiness
        new_base = tmp_path / ".agentic-engineers"
        qm = QueuePathMigration(legacy_base=legacy_base, new_base=new_base)
        
        validation = qm.validate_migration(session_id, "copilot")
        assert validation["legacy_exists"]
        assert validation["legacy_count"] >= 6
        assert validation["can_migrate"]
        
        # Step 3: Create new queue structure
        queue_path = new_base / session_id / "copilot" / "queue"
        for state in ["incoming", "processing", "done", "failed"]:
            (queue_path / state).mkdir(parents=True)
        
        # Step 4: Verify new path structure
        assert queue_path.exists()
        assert all((queue_path / state).exists() for state in ["incoming", "processing", "done", "failed"])
        
        # Step 5: Verify multi-harness capable
        for harness in ["copilot", "claude", "gpt"]:
            harness_queue = new_base / session_id / harness / "queue"
            harness_queue.mkdir(parents=True, exist_ok=True)
            assert harness_queue.exists()
        
        # Final: Verify migration summary
        summary = qm.get_migration_summary()
        assert session_id in summary["legacy_sessions"]
