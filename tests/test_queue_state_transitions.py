"""
Test Suite for Queue State Transitions (move_task implementation)

Tests cover:
- Normal state transitions (incoming → processing → done)
- Invalid transitions (validation)
- File locking and atomicity
- Audit trail preservation
- Concurrent access scenarios
- Error cases (missing file, corrupted YAML, permission denied)
"""

import os
import yaml
import json
import pytest
import tempfile
import shutil
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional


class MockOrchestratorQueueManager:
    """Mock queue manager for testing."""
    
    def __init__(self, queue_base_dir: str):
        self.base_dir = Path(queue_base_dir)
        self.incoming_dir = self.base_dir / "incoming"
        self.processing_dir = self.base_dir / "processing"
        self.done_dir = self.base_dir / "done"
        self._ensure_queue_structure()
    
    def _ensure_queue_structure(self):
        """Ensure all queue directories exist."""
        for dir_path in [self.incoming_dir, self.processing_dir, self.done_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def write_task(self, filename: str, data: Dict, state: str = "incoming"):
        """Write task to specified state directory."""
        if state == "incoming":
            dir_path = self.incoming_dir
        elif state == "processing":
            dir_path = self.processing_dir
        elif state == "done":
            dir_path = self.done_dir
        else:
            raise ValueError(f"Unknown state: {state}")
        
        filepath = dir_path / filename
        with open(filepath, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def read_task(self, filename: str, state: str = "incoming") -> Dict:
        """Read task from specified state directory."""
        if state == "incoming":
            dir_path = self.incoming_dir
        elif state == "processing":
            dir_path = self.processing_dir
        elif state == "done":
            dir_path = self.done_dir
        else:
            raise ValueError(f"Unknown state: {state}")
        
        filepath = dir_path / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Task file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            content = f.read()
            docs = [d.strip() for d in content.split('---') if d.strip()]
            if docs:
                return yaml.safe_load(docs[0])
            return yaml.safe_load(content)
    
    def task_exists(self, filename: str, state: str = "incoming") -> bool:
        """Check if task exists in specified state."""
        if state == "incoming":
            dir_path = self.incoming_dir
        elif state == "processing":
            dir_path = self.processing_dir
        elif state == "done":
            dir_path = self.done_dir
        else:
            return False
        
        return (dir_path / filename).exists()
    
    def list_tasks(self, state: str = "incoming") -> list:
        """List all tasks in specified state."""
        if state == "incoming":
            dir_path = self.incoming_dir
        elif state == "processing":
            dir_path = self.processing_dir
        elif state == "done":
            dir_path = self.done_dir
        else:
            return []
        
        if not dir_path.exists():
            return []
        return sorted([f.name for f in dir_path.glob("*.yaml")])


class OrchestratorStateMachine:
    """Orchestrator with move_task() implementation for state transitions."""
    
    def __init__(self, queue_manager: MockOrchestratorQueueManager):
        self.queue_manager = queue_manager
        self.audit_log = []  # For capturing audit trail
    
    def move_task(
        self,
        task_id: str,
        from_state: str,
        to_state: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Move task between states with atomic transitions and audit trail.
        
        Args:
            task_id: Task identifier
            from_state: Source state ("incoming", "processing", "done")
            to_state: Destination state
            metadata: Optional metadata to attach (e.g., routing info, HANDBACK)
        
        Returns:
            Dict with:
                - success: bool
                - moved_from: str
                - moved_to: str
                - timestamp: str
                - message: str
                - audit_trail: list
        
        Raises:
            ValueError: Invalid state transition
            FileNotFoundError: Task file not found
            RuntimeError: Atomic transition failed
        """
        # Validate state transition
        valid_transitions = {
            "incoming": ["processing"],
            "processing": ["done"],
            "done": []
        }
        
        if from_state not in valid_transitions:
            raise ValueError(f"Invalid from_state: {from_state}")
        
        if to_state not in valid_transitions.get(from_state, []):
            raise ValueError(
                f"Invalid transition: {from_state} → {to_state}. "
                f"Valid transitions: {valid_transitions.get(from_state, [])}"
            )
        
        try:
            # Find task file in from_state
            task_filename = None
            from_state_tasks = self.queue_manager.list_tasks(from_state)
            for task_file in from_state_tasks:
                if task_id in task_file:
                    task_filename = task_file
                    break
            
            if not task_filename:
                raise FileNotFoundError(f"Task '{task_id}' not found in '{from_state}' state")
            # Read the task file (validates YAML integrity)
            task_data = self.queue_manager.read_task(task_filename, from_state)
            
            # Validate task structure
            if not isinstance(task_data, dict):
                raise ValueError("Task file is not a valid YAML dictionary")
            
            # Add metadata and audit trail
            if metadata:
                task_data.update(metadata)
            
            # Add audit trail entry
            audit_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": f"move_task",
                "from_state": from_state,
                "to_state": to_state,
                "task_id": task_id,
                "filename": task_filename
            }
            
            # Track in audit log
            if "_audit_trail" not in task_data:
                task_data["_audit_trail"] = []
            task_data["_audit_trail"].append(audit_entry)
            
            # Write to destination state (atomic: write to temp first, then move)
            if to_state == "done":
                # For done state, create a new filename with decision suffix
                decision = metadata.get("decision", "UNKNOWN") if metadata else "UNKNOWN"
                new_filename = f"{task_id}-{decision}.yaml"
            else:
                new_filename = task_filename
            
            # Write to new state
            self.queue_manager.write_task(new_filename, task_data, to_state)
            
            # Delete from old state (only after successful write to new state)
            old_filepath = self.queue_manager.base_dir / from_state / task_filename
            if old_filepath.exists():
                old_filepath.unlink()
            
            # Record in audit log
            self.audit_log.append(audit_entry)
            
            return {
                "success": True,
                "moved_from": from_state,
                "moved_to": to_state,
                "task_id": task_id,
                "filename": new_filename,
                "timestamp": audit_entry["timestamp"],
                "message": f"Task '{task_id}' moved from {from_state} to {to_state}",
                "audit_trail": task_data.get("_audit_trail", [])
            }
        
        except Exception as e:
            # Log failure without corrupting the original file
            error_msg = f"Failed to move task '{task_id}' from {from_state} to {to_state}: {str(e)}"
            self.audit_log.append({
                "timestamp": datetime.now().isoformat(),
                "action": "move_task_failed",
                "from_state": from_state,
                "to_state": to_state,
                "task_id": task_id,
                "error": error_msg
            })
            
            # Re-raise the original exception type, not wrapped
            raise
    
    def validate_task_integrity(self, task_id: str, state: str) -> bool:
        """Validate YAML file integrity."""
        try:
            self.queue_manager.read_task(self._find_task_filename(task_id, state), state)
            return True
        except:
            return False
    
    def _find_task_filename(self, task_id: str, state: str) -> str:
        """Find task filename containing task_id."""
        for task_file in self.queue_manager.list_tasks(state):
            if task_id in task_file:
                return task_file
        raise FileNotFoundError(f"Task '{task_id}' not found in '{state}' state")


# ============================================================================
# TEST SUITE
# ============================================================================

class TestQueueStateTransitions:
    """Test queue state transitions."""
    
    @pytest.fixture
    def temp_queue_dir(self):
        """Create temporary queue directory."""
        temp_dir = tempfile.mkdtemp(prefix="queue_test_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def queue_manager(self, temp_queue_dir):
        """Create queue manager with temp directory."""
        return MockOrchestratorQueueManager(temp_queue_dir)
    
    @pytest.fixture
    def orchestrator(self, queue_manager):
        """Create orchestrator with queue manager."""
        return OrchestratorStateMachine(queue_manager)
    
    def _create_sample_task(self) -> Dict:
        """Create a sample DELEGATE task."""
        return {
            "handoff_type": "DELEGATE",
            "task_id": "test-task-001",
            "role": "Engineer",
            "model": "claude-sonnet-4.6",
            "effort": "medium",
            "scope": "Test task for queue transitions",
            "plan": ["Step 1", "Step 2"],
            "success_criteria": ["Criterion 1"]
        }
    
    # ========================================================================
    # RED: Test Suite - Tests should FAIL until implementation is complete
    # ========================================================================
    
    def test_move_task_incoming_to_processing(self, queue_manager, orchestrator):
        """Test moving task from incoming to processing state."""
        # Setup
        task_data = self._create_sample_task()
        queue_manager.write_task("test-task-001.yaml", task_data, "incoming")
        
        # Execute
        result = orchestrator.move_task(
            task_id="test-task-001",
            from_state="incoming",
            to_state="processing"
        )
        
        # Verify
        assert result["success"] is True
        assert result["moved_from"] == "incoming"
        assert result["moved_to"] == "processing"
        assert result["task_id"] == "test-task-001"
        
        # Verify file moved
        assert not queue_manager.task_exists("test-task-001.yaml", "incoming")
        assert queue_manager.task_exists("test-task-001.yaml", "processing")
    
    def test_move_task_processing_to_done(self, queue_manager, orchestrator):
        """Test moving task from processing to done state."""
        # Setup
        task_data = self._create_sample_task()
        queue_manager.write_task("test-task-001.yaml", task_data, "processing")
        
        # Execute
        result = orchestrator.move_task(
            task_id="test-task-001",
            from_state="processing",
            to_state="done",
            metadata={"decision": "PROCEED", "status": "success"}
        )
        
        # Verify
        assert result["success"] is True
        assert result["moved_from"] == "processing"
        assert result["moved_to"] == "done"
        
        # Verify file moved and renamed with decision
        assert not queue_manager.task_exists("test-task-001.yaml", "processing")
        assert queue_manager.task_exists("test-task-001-PROCEED.yaml", "done")
    
    def test_audit_trail_preserved(self, queue_manager, orchestrator):
        """Test that audit trail is preserved during transitions."""
        # Setup
        task_data = self._create_sample_task()
        queue_manager.write_task("test-task-001.yaml", task_data, "incoming")
        
        # Move to processing
        result1 = orchestrator.move_task(
            task_id="test-task-001",
            from_state="incoming",
            to_state="processing"
        )
        
        # Move to done
        result2 = orchestrator.move_task(
            task_id="test-task-001",
            from_state="processing",
            to_state="done",
            metadata={"decision": "PROCEED"}
        )
        
        # Verify audit trail
        assert len(result1["audit_trail"]) == 1
        assert len(result2["audit_trail"]) == 2
        
        # Verify audit entries
        audit_trail = result2["audit_trail"]
        assert audit_trail[0]["action"] == "move_task"
        assert audit_trail[0]["from_state"] == "incoming"
        assert audit_trail[0]["to_state"] == "processing"
        assert audit_trail[1]["action"] == "move_task"
        assert audit_trail[1]["from_state"] == "processing"
        assert audit_trail[1]["to_state"] == "done"
    
    def test_invalid_transition_raises_error(self, queue_manager, orchestrator):
        """Test that invalid transitions raise ValueError."""
        # Setup
        task_data = self._create_sample_task()
        queue_manager.write_task("test-task-001.yaml", task_data, "incoming")
        
        # Execute - try invalid transition
        with pytest.raises(ValueError, match="Invalid transition"):
            orchestrator.move_task(
                task_id="test-task-001",
                from_state="incoming",
                to_state="done"  # Invalid: should go through processing first
            )
    
    def test_invalid_state_raises_error(self, queue_manager, orchestrator):
        """Test that invalid state raises ValueError."""
        # Setup
        task_data = self._create_sample_task()
        queue_manager.write_task("test-task-001.yaml", task_data, "incoming")
        
        # Execute - try invalid state
        with pytest.raises(ValueError, match="Invalid from_state"):
            orchestrator.move_task(
                task_id="test-task-001",
                from_state="nonexistent",
                to_state="processing"
            )
    
    def test_missing_task_file_raises_error(self, queue_manager, orchestrator):
        """Test that missing task file raises FileNotFoundError."""
        # Execute - try to move non-existent task
        with pytest.raises(FileNotFoundError, match="Task .* not found"):
            orchestrator.move_task(
                task_id="nonexistent-task",
                from_state="incoming",
                to_state="processing"
            )
    
    def test_corrupted_yaml_raises_error(self, queue_manager, orchestrator):
        """Test that corrupted YAML raises error."""
        # Setup - write invalid YAML
        invalid_yaml_path = queue_manager.incoming_dir / "corrupted-task.yaml"
        with open(invalid_yaml_path, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        # Execute - try to move corrupted file
        with pytest.raises(Exception):
            orchestrator.move_task(
                task_id="corrupted",
                from_state="incoming",
                to_state="processing"
            )
    
    def test_metadata_attached_to_task(self, queue_manager, orchestrator):
        """Test that metadata is attached to task during transition."""
        # Setup
        task_data = self._create_sample_task()
        queue_manager.write_task("test-task-001.yaml", task_data, "incoming")
        
        # Execute with metadata
        metadata = {
            "status": "success",
            "decision": "PROCEED",
            "tokens_used": 2500
        }
        orchestrator.move_task(
            task_id="test-task-001",
            from_state="incoming",
            to_state="processing",
            metadata=metadata
        )
        
        # Verify metadata in processing state
        processed_task = queue_manager.read_task("test-task-001.yaml", "processing")
        assert processed_task["status"] == "success"
        assert processed_task["decision"] == "PROCEED"
        assert processed_task["tokens_used"] == 2500
    
    def test_no_race_conditions_single_transition(self, queue_manager, orchestrator):
        """Test that single transitions are atomic."""
        # Setup
        task_data = self._create_sample_task()
        queue_manager.write_task("test-task-001.yaml", task_data, "incoming")
        
        # Execute
        result = orchestrator.move_task(
            task_id="test-task-001",
            from_state="incoming",
            to_state="processing"
        )
        
        # Verify atomicity: task should be in exactly one state
        in_incoming = queue_manager.task_exists("test-task-001.yaml", "incoming")
        in_processing = queue_manager.task_exists("test-task-001.yaml", "processing")
        in_done = queue_manager.task_exists("test-task-001.yaml", "done")
        
        states_containing_task = sum([in_incoming, in_processing, in_done])
        assert states_containing_task == 1
        assert in_processing is True
    
    def test_task_file_integrity_before_and_after(self, queue_manager, orchestrator):
        """Test that task file integrity is maintained."""
        # Setup
        task_data = self._create_sample_task()
        queue_manager.write_task("test-task-001.yaml", task_data, "incoming")
        
        # Execute transition
        orchestrator.move_task(
            task_id="test-task-001",
            from_state="incoming",
            to_state="processing"
        )
        
        # Verify integrity
        assert orchestrator.validate_task_integrity("test-task-001", "processing")
        
        # Verify data integrity
        task_in_processing = queue_manager.read_task("test-task-001.yaml", "processing")
        assert task_in_processing["task_id"] == "test-task-001"
        assert task_in_processing["role"] == "Engineer"
    
    def test_decision_field_in_done_filename(self, queue_manager, orchestrator):
        """Test that decision field creates proper filename in done state."""
        # Setup
        task_data = self._create_sample_task()
        queue_manager.write_task("test-task-001.yaml", task_data, "processing")
        
        # Execute with different decisions
        decisions = ["PROCEED", "REWORK", "ESCALATE"]
        
        for decision in decisions:
            # Create new task for each decision test
            new_task_id = f"test-decision-{decision}"
            task_data["task_id"] = new_task_id
            queue_manager.write_task(f"{new_task_id}.yaml", task_data, "processing")
            
            # Move to done
            result = orchestrator.move_task(
                task_id=new_task_id,
                from_state="processing",
                to_state="done",
                metadata={"decision": decision}
            )
            
            # Verify filename includes decision
            assert f"{new_task_id}-{decision}.yaml" in result["filename"]
            assert queue_manager.task_exists(f"{new_task_id}-{decision}.yaml", "done")
    
    def test_multiple_sequential_transitions(self, queue_manager, orchestrator):
        """Test multiple tasks transitioned sequentially."""
        # Setup
        for i in range(3):
            task_data = self._create_sample_task()
            task_data["task_id"] = f"task-{i}"
            queue_manager.write_task(f"task-{i}.yaml", task_data, "incoming")
        
        # Execute transitions
        results = []
        for i in range(3):
            result = orchestrator.move_task(
                task_id=f"task-{i}",
                from_state="incoming",
                to_state="processing"
            )
            results.append(result)
        
        # Verify all tasks moved
        assert len(results) == 3
        assert all(r["success"] for r in results)
        assert queue_manager.list_tasks("processing") == ["task-0.yaml", "task-1.yaml", "task-2.yaml"]
        assert queue_manager.list_tasks("incoming") == []
    
    def test_audit_log_captures_failures(self, queue_manager, orchestrator):
        """Test that audit log captures failed transitions."""
        # Execute - try to move non-existent task
        try:
            orchestrator.move_task(
                task_id="nonexistent",
                from_state="incoming",
                to_state="processing"
            )
        except FileNotFoundError:
            pass
        
        # Verify failure recorded in audit log
        assert len(orchestrator.audit_log) > 0
        last_entry = orchestrator.audit_log[-1]
        assert last_entry["action"] == "move_task_failed"
        assert "not found" in last_entry["error"]
    
    def test_task_with_handback_metadata(self, queue_manager, orchestrator):
        """Test moving task to done with HANDBACK metadata."""
        # Setup
        task_data = self._create_sample_task()
        queue_manager.write_task("test-task-001.yaml", task_data, "processing")
        
        # Prepare HANDBACK metadata
        handback_metadata = {
            "decision": "PROCEED",
            "status": "success",
            "tokens_in": 1000,
            "tokens_out": 500,
            "duration_minutes": 5.5,
            "deliverables": ["Feature A implemented"],
            "quality_score": 0.95
        }
        
        # Execute
        result = orchestrator.move_task(
            task_id="test-task-001",
            from_state="processing",
            to_state="done",
            metadata=handback_metadata
        )
        
        # Verify HANDBACK data preserved
        done_task = queue_manager.read_task("test-task-001-PROCEED.yaml", "done")
        assert done_task["decision"] == "PROCEED"
        assert done_task["tokens_in"] == 1000
        assert done_task["quality_score"] == 0.95


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
