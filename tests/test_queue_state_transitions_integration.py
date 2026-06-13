"""
Integration Test for Queue State Transitions with Real Orchestrator

⚠️ DEPENDENT ON QUEUE-ISOLATION
These tests require queue-isolation to be properly initialized. As of 2026-05-26,
the queue infrastructure requires queue-isolation skill for canonical path support.

Tests the actual move_task() implementation in orchestration/agents/orchestrator.py
with the real QueueManager and OrchestratorAgent classes.

TESTS SKIPPED: These require queue-isolation initialization.
See tests/test_queue_path_centralization.py for isolated queue path tests.
"""

import os
import yaml
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import pytest
from src.orchestration.agents.orchestrator import QueueManager

# Skip all tests in this module - require queue-isolation setup
pytestmark = pytest.mark.skip(
    reason="Queue-isolation dependent tests (requires proper setup). "
           "See tests/test_queue_path_centralization.py for canonical path tests."
)


def test_move_task_integration_incoming_to_processing():
    """Integration test: move task from incoming to processing."""
    # Setup
    temp_dir = tempfile.mkdtemp(prefix="queue_integration_")
    try:
        queue_manager = QueueManager(queue_dir=temp_dir)
        
        # Create a sample task
        task_data = {
            "handoff_type": "DELEGATE",
            "task_id": "integration-test-001",
            "role": "Engineer",
            "model": "claude-sonnet-4.6",
            "effort": "medium",
            "scope": "Integration test task",
            "plan": ["Step 1", "Step 2"],
            "success_criteria": ["Criterion 1"]
        }
        
        # Write task to incoming
        incoming_path = queue_manager.incoming_dir / "integration-test-001.yaml"
        with open(incoming_path, 'w') as f:
            yaml.dump(task_data, f, default_flow_style=False, sort_keys=False)
        
        # Move task from incoming to processing
        result = queue_manager.move_task(
            task_id="integration-test-001",
            from_state="incoming",
            to_state="processing"
        )
        
        # Verify results
        assert result["success"] is True
        assert result["moved_from"] == "incoming"
        assert result["moved_to"] == "processing"
        assert result["task_id"] == "integration-test-001"
        
        # Verify file moved
        assert not incoming_path.exists()
        processing_path = queue_manager.processing_dir / "integration-test-001.yaml"
        assert processing_path.exists()
        
        # Verify audit trail in the moved file
        with open(processing_path, 'r') as f:
            moved_task = yaml.safe_load(f)
        
        assert "_audit_trail" in moved_task
        assert len(moved_task["_audit_trail"]) == 1
        assert moved_task["_audit_trail"][0]["action"] == "move_task"
        assert moved_task["_audit_trail"][0]["from_state"] == "incoming"
        assert moved_task["_audit_trail"][0]["to_state"] == "processing"
        
        print("✓ Integration test passed: incoming → processing")
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_move_task_integration_processing_to_done():
    """Integration test: move task from processing to done."""
    # Setup
    temp_dir = tempfile.mkdtemp(prefix="queue_integration_")
    try:
        queue_manager = QueueManager(queue_dir=temp_dir)
        
        # Create a sample task in processing
        task_data = {
            "handoff_type": "DELEGATE",
            "task_id": "integration-test-002",
            "role": "Engineer",
            "model": "claude-sonnet-4.6",
            "effort": "medium",
            "scope": "Integration test task",
            "plan": ["Step 1"],
            "success_criteria": ["Criterion 1"]
        }
        
        # Write task to processing
        processing_path = queue_manager.processing_dir / "integration-test-002.yaml"
        with open(processing_path, 'w') as f:
            yaml.dump(task_data, f, default_flow_style=False, sort_keys=False)
        
        # Move task from processing to done with HANDBACK metadata
        handback_metadata = {
            "decision": "PROCEED",
            "status": "success",
            "tokens_in": 1000,
            "tokens_out": 500,
            "duration_minutes": 5.5,
            "quality_score": 0.95
        }
        
        result = queue_manager.move_task(
            task_id="integration-test-002",
            from_state="processing",
            to_state="done",
            metadata=handback_metadata
        )
        
        # Verify results
        assert result["success"] is True
        assert result["moved_from"] == "processing"
        assert result["moved_to"] == "done"
        
        # Verify file moved and renamed with decision
        assert not processing_path.exists()
        done_path = queue_manager.done_dir / "integration-test-002-PROCEED.yaml"
        assert done_path.exists()
        
        # Verify metadata in done file
        with open(done_path, 'r') as f:
            done_task = yaml.safe_load(f)
        
        assert done_task["decision"] == "PROCEED"
        assert done_task["status"] == "complete"
        assert done_task["tokens_in"] == 1000
        assert done_task["quality_score"] == 0.95
        
        # Verify audit trail extended
        assert "_audit_trail" in done_task
        assert len(done_task["_audit_trail"]) >= 1
        assert done_task["_audit_trail"][-1]["action"] == "move_task"
        assert done_task["_audit_trail"][-1]["from_state"] == "processing"
        assert done_task["_audit_trail"][-1]["to_state"] == "done"
        
        print("✓ Integration test passed: processing → done")
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_move_task_integration_full_workflow():
    """Integration test: full workflow incoming → processing → done."""
    # Setup
    temp_dir = tempfile.mkdtemp(prefix="queue_integration_")
    try:
        queue_manager = QueueManager(queue_dir=temp_dir)
        
        # Create a sample task
        task_data = {
            "handoff_type": "DELEGATE",
            "task_id": "integration-test-full",
            "role": "Engineer",
            "model": "claude-sonnet-4.6",
            "effort": "medium",
            "scope": "Full workflow test",
            "plan": ["Step 1", "Step 2"],
            "success_criteria": ["Done"]
        }
        
        # Write task to incoming
        incoming_path = queue_manager.incoming_dir / "integration-test-full.yaml"
        with open(incoming_path, 'w') as f:
            yaml.dump(task_data, f, default_flow_style=False, sort_keys=False)
        
        # Step 1: Move incoming → processing
        result1 = queue_manager.move_task(
            task_id="integration-test-full",
            from_state="incoming",
            to_state="processing"
        )
        assert result1["success"]
        
        # Step 2: Move processing → done
        result2 = queue_manager.move_task(
            task_id="integration-test-full",
            from_state="processing",
            to_state="done",
            metadata={"decision": "PROCEED"}
        )
        assert result2["success"]
        
        # Verify full audit trail
        done_path = queue_manager.done_dir / "integration-test-full-PROCEED.yaml"
        with open(done_path, 'r') as f:
            final_task = yaml.safe_load(f)
        
        audit_trail = final_task.get("_audit_trail", [])
        assert len(audit_trail) == 2
        
        # Verify transitions
        assert audit_trail[0]["from_state"] == "incoming"
        assert audit_trail[0]["to_state"] == "processing"
        assert audit_trail[1]["from_state"] == "processing"
        assert audit_trail[1]["to_state"] == "done"
        
        # Verify task is only in done state
        assert not (queue_manager.incoming_dir / "integration-test-full.yaml").exists()
        assert not (queue_manager.processing_dir / "integration-test-full.yaml").exists()
        assert done_path.exists()
        
        print("✓ Integration test passed: full workflow incoming → processing → done")
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_move_task_error_handling():
    """Integration test: error handling for invalid operations."""
    # Setup
    temp_dir = tempfile.mkdtemp(prefix="queue_integration_")
    try:
        queue_manager = QueueManager(queue_dir=temp_dir)
        
        # Test 1: Moving non-existent task
        try:
            queue_manager.move_task(
                task_id="nonexistent",
                from_state="incoming",
                to_state="processing"
            )
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError as e:
            assert "not found" in str(e)
        
        # Test 2: Invalid transition
        # First create a task in incoming
        task_data = {"task_id": "test-001", "role": "Engineer"}
        with open(queue_manager.incoming_dir / "test-001.yaml", 'w') as f:
            yaml.dump(task_data, f)
        
        # Try to move directly to done (invalid)
        try:
            queue_manager.move_task(
                task_id="test-001",
                from_state="incoming",
                to_state="done"
            )
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Invalid transition" in str(e)
        
        print("✓ Integration test passed: error handling")
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_move_task_delegate_prefixed_filename():
    """
    Regression test for the DELEGATE-prefix filename bug.
    
    Scenario: filename is 'DELEGATE-opencode-config-validation.yaml'
              task_id in YAML is '2026-05-17-opencode-config-validation'
    
    The old code did `if task_id in task_file` which evaluates:
        '2026-05-17-opencode-config-validation' in 'DELEGATE-opencode-config-validation.yaml'
        → False  (date prefix not in filename)
    
    The fix: pass filename= explicitly to move_task so it uses the file directly.
    """
    temp_dir = tempfile.mkdtemp(prefix="queue_delegate_prefix_")
    try:
        queue_manager = QueueManager(queue_dir=temp_dir)
        
        # Simulate the real-world scenario: DELEGATE-prefixed filename, date-prefixed task_id
        task_data = {
            "handoff_type": "DELEGATE",
            "task_id": "2026-05-17-opencode-config-validation",
            "role": "Engineer",
            "model": "claude-sonnet-4.6",
            "effort": "medium",
            "scope": "Validate opencode configuration",
            "plan": ["Step 1", "Step 2"],
            "success_criteria": ["Config validated"]
        }
        
        incoming_filename = "DELEGATE-opencode-config-validation.yaml"
        task_id = "2026-05-17-opencode-config-validation"
        
        # Write task to incoming with DELEGATE-prefixed filename
        incoming_path = queue_manager.incoming_dir / incoming_filename
        with open(incoming_path, 'w') as f:
            yaml.dump(task_data, f, default_flow_style=False, sort_keys=False)
        
        # Verify old substring search would FAIL (this is the bug)
        assert task_id not in incoming_filename, (
            f"Sanity check: '{task_id}' should NOT be a substring of '{incoming_filename}' "
            f"(this confirms the bug scenario)"
        )
        
        # Fix: pass filename= explicitly — should succeed
        result = queue_manager.move_task(
            task_id=task_id,
            from_state="incoming",
            to_state="processing",
            filename=incoming_filename
        )
        
        assert result["success"] is True
        assert result["moved_from"] == "incoming"
        assert result["moved_to"] == "processing"
        assert result["task_id"] == task_id
        
        # Verify file moved
        assert not incoming_path.exists()
        processing_path = queue_manager.processing_dir / incoming_filename
        assert processing_path.exists()
        
        # Verify audit trail
        with open(processing_path, 'r') as f:
            moved_task = yaml.safe_load(f)
        assert "_audit_trail" in moved_task
        assert moved_task["_audit_trail"][0]["from_state"] == "incoming"
        assert moved_task["_audit_trail"][0]["to_state"] == "processing"
        
        # Now move processing → done using filename from move_result
        processing_filename = result["filename"]
        result2 = queue_manager.move_task(
            task_id=task_id,
            from_state="processing",
            to_state="done",
            filename=processing_filename,
            metadata={"decision": "PROCEED", "status": "success"}
        )
        assert result2["success"] is True
        
        done_path = queue_manager.done_dir / f"{task_id}-PROCEED.yaml"
        assert done_path.exists()
        
        print("✓ Regression test passed: DELEGATE-prefixed filename with date-prefixed task_id")
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_move_task_error_message_shows_available_files():
    """
    Test that FileNotFoundError now includes helpful diagnostic info:
    available files list and a hint about filename vs task_id mismatch.
    """
    temp_dir = tempfile.mkdtemp(prefix="queue_error_msg_")
    try:
        queue_manager = QueueManager(queue_dir=temp_dir)
        
        # Create a file with DELEGATE prefix
        task_data = {"handoff_type": "DELEGATE", "task_id": "2026-05-17-foo", "role": "Engineer"}
        with open(queue_manager.incoming_dir / "DELEGATE-foo.yaml", 'w') as f:
            yaml.dump(task_data, f)
        
        # Try to find by task_id (old-style, will fail because date prefix mismatch)
        try:
            queue_manager.move_task(
                task_id="2026-05-17-foo",
                from_state="incoming",
                to_state="processing"
                # No filename= — old-style substring search
            )
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError as e:
            error_msg = str(e)
            # New error message should include available files and a hint
            assert "DELEGATE-foo.yaml" in error_msg, f"Error should list available files, got: {error_msg}"
            assert "Hint" in error_msg, f"Error should include a hint, got: {error_msg}"
        
        # Now try with explicit filename — should succeed
        result = queue_manager.move_task(
            task_id="2026-05-17-foo",
            from_state="incoming",
            to_state="processing",
            filename="DELEGATE-foo.yaml"
        )
        assert result["success"] is True
        
        print("✓ Error message test passed: helpful diagnostics in FileNotFoundError")
    
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    test_move_task_integration_incoming_to_processing()
    test_move_task_integration_processing_to_done()
    test_move_task_integration_full_workflow()
    test_move_task_error_handling()
    test_move_task_delegate_prefixed_filename()
    test_move_task_error_message_shows_available_files()
    print("\n✅ All integration tests passed!")
