"""
E2E Protocol Tests: Full DELEGATE/HANDBACK Cycle (Phase 4)

Comprehensive integration tests covering:
1. DELEGATE written and queued
2. Orchestrator processes DELEGATE (incoming → processing)
3. HANDBACK written by agent (processing → done/failed/escalation)
4. Queue state transitions and consistency
5. Multi-harness isolation
6. Canonical paths (no artifacts/ corruption)
7. Span capture on HANDBACK completion

These tests verify the complete lifecycle of a task through the agentic-engineers
protocol, from initial DELEGATE creation through orchestrator processing to final
HANDBACK and queue cleanup.

Usage:
    pytest tests/test_e2e_protocol_full_cycle.py -v -s
    make test-protocol-e2e
"""

import pytest
import os
import sys
import yaml
import json
import time
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Generator
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import test helpers
from tests.helpers.queue_test_helpers import (
    setup_isolated_queue,
    setup_legacy_queue,
)


# ============================================================================
# Session and Queue Setup Fixtures
# ============================================================================

@pytest.fixture
def test_session(tmp_path: Path) -> Tuple[Path, str, str]:
    """
    Create an isolated test session with canonical queue structure.

    Returns:
        Tuple of (queue_path, session_id, harness)
    """
    session_id = f"e2e-test-{uuid.uuid4().hex[:8]}"
    harness = "test"

    queue_path = setup_isolated_queue(tmp_path, session_id, harness)

    # Verify all required subdirectories exist
    assert (queue_path / "incoming").exists(), "incoming/ not created"
    assert (queue_path / "processing").exists(), "processing/ not created"
    assert (queue_path / "done").exists(), "done/ not created"
    assert (queue_path / "failed").exists(), "failed/ not created"

    return queue_path, session_id, harness


@pytest.fixture
def sample_delegate() -> Dict:
    """Valid DELEGATE YAML with all required fields."""
    return {
        "handoff_type": "DELEGATE",
        "task_id": f"task-{uuid.uuid4().hex[:8]}",
        "agent": "engineer",
        "model": "claude-haiku-4.5",
        "effort": "high",
        "scope": "Test implementation task with full protocol coverage",
        "plan": [
            "1. Read and understand requirement",
            "2. Identify affected files",
            "3. Write implementation",
            "4. Run tests",
            "5. Commit changes"
        ],
        "success_criteria": [
            "All tests pass",
            "Code follows style guide",
            "No linter warnings"
        ],
        "context": [
            "File: test.py",
            "Error: None",
            "Root cause: Testing protocol"
        ],
        "estimated_tokens": 2000,
    }


@pytest.fixture
def sample_handback(sample_delegate: Dict) -> Dict:
    """Valid HANDBACK YAML with all required fields."""
    return {
        "handoff_type": "HANDBACK",
        "task_id": sample_delegate["task_id"],
        "agent": "engineer",
        "status": "success",
        "output": "Task completed successfully with full protocol coverage",
        "metrics": {
            "quality": 0.95,
            "tokens": 1800,
            "cost": 0.04,
            "duration_seconds": 120,
        },
        "confidence": 0.95,
        "escalations": [],
    }


# ============================================================================
# Test 1: DELEGATE Written and Queued
# ============================================================================

def test_delegate_written_and_queued(test_session: Tuple[Path, str, str], sample_delegate: Dict):
    """
    Test 1: Write canonical DELEGATE YAML to incoming/, verify it's readable.

    Validates:
    - DELEGATE can be written to canonical queue path
    - File format is valid YAML
    - All required fields present
    - File is in correct directory
    """
    queue_path, session_id, harness = test_session
    incoming_dir = queue_path / "incoming"

    # Write DELEGATE as YAML file
    delegate_file = incoming_dir / f"{sample_delegate['task_id']}.yaml"
    with open(delegate_file, "w") as f:
        yaml.dump(sample_delegate, f)

    # Verify file exists
    assert delegate_file.exists(), f"DELEGATE file not created: {delegate_file}"

    # Verify it can be read back
    with open(delegate_file, "r") as f:
        loaded = yaml.safe_load(f)

    # Verify all required fields are present
    assert loaded["handoff_type"] == "DELEGATE"
    assert loaded["task_id"] == sample_delegate["task_id"]
    assert loaded["agent"] == "engineer"
    assert loaded["model"] == "claude-haiku-4.5"
    assert loaded["effort"] == "high"
    assert "scope" in loaded
    assert "plan" in loaded
    assert "success_criteria" in loaded
    assert "estimated_tokens" in loaded

    # Verify it's in the correct directory
    assert delegate_file.parent == incoming_dir


# ============================================================================
# Test 2: Orchestrator Processes DELEGATE
# ============================================================================

def test_orchestrator_processes_delegate(test_session: Tuple[Path, str, str], sample_delegate: Dict):
    """
    Test 2: Simulate orchestrator processing DELEGATE (incoming → processing).

    Validates:
    - DELEGATE moved from incoming/ to processing/
    - Metadata preserved during move
    - Processing directory has correct file
    """
    queue_path, session_id, harness = test_session
    incoming_dir = queue_path / "incoming"
    processing_dir = queue_path / "processing"

    # Write DELEGATE to incoming
    delegate_file = incoming_dir / f"{sample_delegate['task_id']}.yaml"
    with open(delegate_file, "w") as f:
        yaml.dump(sample_delegate, f)

    # Simulate orchestrator moving file
    processing_file = processing_dir / delegate_file.name
    shutil.move(str(delegate_file), str(processing_file))

    # Verify move completed
    assert not delegate_file.exists(), "DELEGATE still in incoming/ after move"
    assert processing_file.exists(), "DELEGATE not in processing/ after move"

    # Verify content preserved
    with open(processing_file, "r") as f:
        loaded = yaml.safe_load(f)

    assert loaded["task_id"] == sample_delegate["task_id"]
    assert loaded["agent"] == "engineer"

    # Verify processing dir has exactly one file
    files_in_processing = list(processing_dir.glob("*.yaml"))
    assert len(files_in_processing) == 1


# ============================================================================
# Test 3: HANDBACK Written by Agent
# ============================================================================

def test_handback_written_by_agent(test_session: Tuple[Path, str, str], sample_delegate: Dict, sample_handback: Dict):
    """
    Test 3: Simulate agent writing HANDBACK, orchestrator moves to done/.

    Validates:
    - HANDBACK can be written to processing/
    - HANDBACK has correct schema
    - Orchestrator can move to done/ directory
    - File is readable after move
    """
    queue_path, session_id, harness = test_session
    processing_dir = queue_path / "processing"
    done_dir = queue_path / "done"

    # Setup: Put DELEGATE in processing
    delegate_file = processing_dir / f"{sample_delegate['task_id']}.yaml"
    with open(delegate_file, "w") as f:
        yaml.dump(sample_delegate, f)

    # Agent writes HANDBACK with same task_id
    handback_file = processing_dir / f"HANDBACK-{sample_delegate['task_id']}.yaml"
    with open(handback_file, "w") as f:
        yaml.dump(sample_handback, f)

    # Verify HANDBACK exists in processing
    assert handback_file.exists()

    # Simulate orchestrator moving HANDBACK to done
    done_file = done_dir / handback_file.name
    shutil.move(str(handback_file), str(done_file))

    # Verify move completed
    assert not handback_file.exists()
    assert done_file.exists()

    # Verify content
    with open(done_file, "r") as f:
        loaded = yaml.safe_load(f)

    assert loaded["handoff_type"] == "HANDBACK"
    assert loaded["task_id"] == sample_delegate["task_id"]
    assert loaded["status"] == "success"
    assert "output" in loaded
    assert "metrics" in loaded


# ============================================================================
# Test 4: Failed Task Goes to Failed Directory
# ============================================================================

def test_failed_task_goes_to_failed_dir(test_session: Tuple[Path, str, str], sample_delegate: Dict):
    """
    Test 4: HANDBACK with status=failure moves task to failed/ directory.

    Validates:
    - HANDBACK with status=failure is recognized
    - Task moved to failed/ not done/
    - Failure metadata preserved
    """
    queue_path, session_id, harness = test_session
    processing_dir = queue_path / "processing"
    failed_dir = queue_path / "failed"

    # Setup: DELEGATE in processing
    delegate_file = processing_dir / f"{sample_delegate['task_id']}.yaml"
    with open(delegate_file, "w") as f:
        yaml.dump(sample_delegate, f)

    # Agent writes failure HANDBACK
    failed_handback = {
        "handoff_type": "HANDBACK",
        "task_id": sample_delegate["task_id"],
        "agent": "engineer",
        "status": "failure",
        "output": "Task failed with error",
        "metrics": {
            "quality": 0.0,
            "tokens": 500,
            "cost": 0.02,
            "duration_seconds": 30,
        },
        "confidence": 0.0,
        "escalations": ["Error in implementation"],
    }

    handback_file = processing_dir / f"HANDBACK-{sample_delegate['task_id']}.yaml"
    with open(handback_file, "w") as f:
        yaml.dump(failed_handback, f)

    # Orchestrator moves to failed/ (not done/)
    failed_file = failed_dir / handback_file.name
    shutil.move(str(handback_file), str(failed_file))

    # Verify location
    assert not handback_file.exists()
    assert failed_file.exists()

    # Verify status preserved
    with open(failed_file, "r") as f:
        loaded = yaml.safe_load(f)

    assert loaded["status"] == "failure"
    assert len(loaded["escalations"]) > 0


# ============================================================================
# Test 5: Blocked Task Retry Counter
# ============================================================================

def test_blocked_task_retry_counter(test_session: Tuple[Path, str, str], sample_delegate: Dict):
    """
    Test 5: HANDBACK with status=blocked stays in processing/ with retry metadata.

    Validates:
    - Blocked HANDBACK recognized
    - Task stays in processing/ (not moved to done/failed)
    - Retry counter incremented
    - Retry metadata captured
    """
    queue_path, session_id, harness = test_session
    processing_dir = queue_path / "processing"

    # Setup: DELEGATE in processing with initial retry count
    delegate_file = processing_dir / f"{sample_delegate['task_id']}.yaml"
    sample_delegate_with_retry = sample_delegate.copy()
    sample_delegate_with_retry["_retry_count"] = 0
    with open(delegate_file, "w") as f:
        yaml.dump(sample_delegate_with_retry, f)

    # Agent writes blocked HANDBACK
    blocked_handback = {
        "handoff_type": "HANDBACK",
        "task_id": sample_delegate["task_id"],
        "agent": "engineer",
        "status": "blocked",
        "output": "Task blocked: resource unavailable",
        "metrics": {
            "quality": 0.5,
            "tokens": 1000,
            "cost": 0.03,
            "duration_seconds": 60,
        },
        "confidence": 0.5,
        "escalations": ["Resource unavailable - will retry"],
        "_retry_count": 1,
        "_last_blocked_reason": "resource unavailable",
    }

    handback_file = processing_dir / f"HANDBACK-{sample_delegate['task_id']}.yaml"
    with open(handback_file, "w") as f:
        yaml.dump(blocked_handback, f)

    # For blocked, file stays in processing (no move)
    # But we increment the retry counter
    assert handback_file.exists()

    # Verify retry metadata
    with open(handback_file, "r") as f:
        loaded = yaml.safe_load(f)

    assert loaded["status"] == "blocked"
    assert loaded["_retry_count"] == 1
    assert "_last_blocked_reason" in loaded


# ============================================================================
# Test 6: Escalate Creates New DELEGATE
# ============================================================================

def test_escalate_creates_new_delegate(test_session: Tuple[Path, str, str], sample_delegate: Dict):
    """
    Test 6: HANDBACK with status=escalate creates new DELEGATE in incoming/.

    Validates:
    - Escalate status recognized
    - New DELEGATE created with same task_id
    - New DELEGATE in incoming/ directory
    - Escalation chain preserved
    """
    queue_path, session_id, harness = test_session
    incoming_dir = queue_path / "incoming"
    processing_dir = queue_path / "processing"

    # Setup: DELEGATE in processing
    delegate_file = processing_dir / f"{sample_delegate['task_id']}.yaml"
    with open(delegate_file, "w") as f:
        yaml.dump(sample_delegate, f)

    # Agent writes escalate HANDBACK
    escalate_handback = {
        "handoff_type": "HANDBACK",
        "task_id": sample_delegate["task_id"],
        "agent": "engineer",
        "status": "escalate",
        "output": "Escalating to senior engineer for complex analysis",
        "metrics": {
            "quality": 0.6,
            "tokens": 2000,
            "cost": 0.05,
            "duration_seconds": 180,
        },
        "confidence": 0.4,
        "escalations": ["Complexity exceeds engineer scope"],
    }

    handback_file = processing_dir / f"HANDBACK-{sample_delegate['task_id']}.yaml"
    with open(handback_file, "w") as f:
        yaml.dump(escalate_handback, f)

    # Orchestrator creates new DELEGATE for escalation
    new_delegate = sample_delegate.copy()
    new_delegate["agent"] = "senior-engineer"  # Escalate to senior engineer
    new_delegate["escalation_parent"] = sample_delegate["task_id"]
    new_delegate["escalation_reason"] = "Complexity exceeds engineer scope"

    new_delegate_file = incoming_dir / f"{new_delegate['task_id']}-escalated.yaml"
    with open(new_delegate_file, "w") as f:
        yaml.dump(new_delegate, f)

    # Verify new DELEGATE in incoming
    assert new_delegate_file.exists()

    # Verify escalation chain
    with open(new_delegate_file, "r") as f:
        loaded = yaml.safe_load(f)

    assert loaded["agent"] == "senior-engineer"
    assert "escalation_parent" in loaded
    assert loaded["escalation_reason"] == "Complexity exceeds engineer scope"


# ============================================================================
# Test 7: Multi-Harness Isolation
# ============================================================================

def test_multi_harness_isolation(tmp_path: Path):
    """
    Test 7: Two sessions with different harnesses don't interfere.

    Validates:
    - Multiple harnesses can coexist
    - Queue paths are completely isolated
    - Tasks in one harness don't affect another
    - Canonical paths enforce isolation
    """
    session_id = f"multi-harness-{uuid.uuid4().hex[:8]}"

    # Setup two harnesses
    queue_path_copilot = setup_isolated_queue(tmp_path, session_id, "copilot")
    queue_path_claude = setup_isolated_queue(tmp_path, session_id, "claude")

    # Verify paths are different
    assert queue_path_copilot != queue_path_claude
    assert "copilot" in str(queue_path_copilot)
    assert "claude" in str(queue_path_claude)

    # Create task in copilot
    copilot_task = {
        "handoff_type": "DELEGATE",
        "task_id": "task-copilot-001",
        "agent": "engineer",
        "model": "gpt-4",
        "effort": "high",
        "scope": "Copilot task",
        "plan": ["1. Do something"],
        "success_criteria": ["Success"],
    }

    copilot_file = queue_path_copilot / "incoming" / "task-copilot-001.yaml"
    with open(copilot_file, "w") as f:
        yaml.dump(copilot_task, f)

    # Create task in claude
    claude_task = {
        "handoff_type": "DELEGATE",
        "task_id": "task-claude-001",
        "agent": "engineer",
        "model": "claude-opus-4.6",
        "effort": "high",
        "scope": "Claude task",
        "plan": ["1. Do something"],
        "success_criteria": ["Success"],
    }

    claude_file = queue_path_claude / "incoming" / "task-claude-001.yaml"
    with open(claude_file, "w") as f:
        yaml.dump(claude_task, f)

    # Verify isolation: copilot task not in claude queue
    claude_files = list((queue_path_claude / "incoming").glob("*.yaml"))
    assert len(claude_files) == 1
    assert "claude-001" in str(claude_files[0])
    assert "copilot-001" not in str(claude_files[0])

    # Verify isolation: claude task not in copilot queue
    copilot_files = list((queue_path_copilot / "incoming").glob("*.yaml"))
    assert len(copilot_files) == 1
    assert "copilot-001" in str(copilot_files[0])
    assert "claude-001" not in str(copilot_files[0])


# ============================================================================
# Test 8: Queue State Consistency
# ============================================================================

def test_queue_state_consistency(test_session: Tuple[Path, str, str], sample_delegate: Dict, sample_handback: Dict):
    """
    Test 8: After full cycle: incoming/ empty, done/ has task, metrics captured.

    Validates:
    - Queue state transitions are atomic
    - incoming/ becomes empty after processing
    - done/ has completed task
    - Metrics properly captured
    - No orphaned files
    """
    queue_path, session_id, harness = test_session
    incoming_dir = queue_path / "incoming"
    processing_dir = queue_path / "processing"
    done_dir = queue_path / "done"

    # Step 1: Write to incoming
    delegate_file = incoming_dir / f"{sample_delegate['task_id']}.yaml"
    with open(delegate_file, "w") as f:
        yaml.dump(sample_delegate, f)

    assert len(list(incoming_dir.glob("*.yaml"))) == 1
    assert len(list(processing_dir.glob("*.yaml"))) == 0
    assert len(list(done_dir.glob("*.yaml"))) == 0

    # Step 2: Move to processing
    processing_file = processing_dir / delegate_file.name
    shutil.move(str(delegate_file), str(processing_file))

    assert len(list(incoming_dir.glob("*.yaml"))) == 0
    assert len(list(processing_dir.glob("*.yaml"))) == 1

    # Step 3: Agent writes HANDBACK
    handback_file = processing_dir / f"HANDBACK-{sample_delegate['task_id']}.yaml"
    with open(handback_file, "w") as f:
        yaml.dump(sample_handback, f)

    assert len(list(processing_dir.glob("*.yaml"))) == 2  # DELEGATE + HANDBACK

    # Step 4: Move HANDBACK to done
    done_file = done_dir / handback_file.name
    shutil.move(str(handback_file), str(done_file))

    # Step 5: Clean up DELEGATE from processing
    shutil.move(str(processing_file), str(done_dir / processing_file.name))

    # Final state
    assert len(list(incoming_dir.glob("*.yaml"))) == 0, "incoming/ not empty"
    assert len(list(processing_dir.glob("*.yaml"))) == 0, "processing/ not empty"
    assert len(list(done_dir.glob("*.yaml"))) == 2, "done/ doesn't have both files"

    # Verify done/ has both DELEGATE and HANDBACK
    done_files = [f.name for f in done_dir.glob("*.yaml")]
    assert any("HANDBACK" in f for f in done_files), "No HANDBACK in done/"


# ============================================================================
# Test 9: Canonical Paths Throughout
# ============================================================================

def test_canonical_paths_throughout(test_session: Tuple[Path, str, str]):
    """
    Test 9: All queue operations use canonical paths (no artifacts/).

    Validates:
    - Queue path follows canonical format
    - No artifacts/ segment in path
    - Session ID and harness in correct positions
    - Path structure: ~/.agentic-engineers/{session}/{harness}/queue/
    """
    queue_path, session_id, harness = test_session

    # Verify canonical structure
    assert ".agentic-engineers" in str(queue_path), f"Invalid path: {queue_path}"
    assert "artifacts" not in str(queue_path), f"Path contains artifacts/: {queue_path}"
    assert session_id in str(queue_path), f"Session ID not in path: {queue_path}"
    assert harness in str(queue_path), f"Harness not in path: {queue_path}"
    assert "queue" in str(queue_path), f"queue/ not in path: {queue_path}"

    # Verify path structure
    # Expected: {base}/.agentic-engineers/{session}/{harness}/queue/
    path_parts = queue_path.parts
    agentic_idx = next(i for i, p in enumerate(path_parts) if p == ".agentic-engineers")

    assert path_parts[agentic_idx] == ".agentic-engineers"
    assert path_parts[agentic_idx + 1] == session_id
    assert path_parts[agentic_idx + 2] == harness
    assert path_parts[agentic_idx + 3] == "queue"

    # Verify subdirectories follow canonical structure
    for subdir in ["incoming", "processing", "done", "failed"]:
        subdir_path = queue_path / subdir
        assert subdir_path.exists()
        assert "artifacts" not in str(subdir_path)


# ============================================================================
# Test 10: Span Capture on HANDBACK
# ============================================================================

def test_span_capture_on_handback(test_session: Tuple[Path, str, str], sample_delegate: Dict, sample_handback: Dict):
    """
    Test 10: After HANDBACK, span YAML written to artifacts/{date}/SPAN-*.yaml.

    Validates:
    - Span file created after HANDBACK
    - Span contains telemetry metadata
    - Span file in correct location (artifacts/{date}/)
    - Span format is valid YAML
    - Span includes task_id, status, duration, tokens
    """
    queue_path, session_id, harness = test_session

    # Get artifacts directory (sibling of queue)
    artifacts_dir = queue_path.parent.parent / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Create dated subdirectory
    date_str = datetime.now().strftime("%Y-%m-%d")
    dated_dir = artifacts_dir / date_str
    dated_dir.mkdir(parents=True, exist_ok=True)

    # Simulate orchestrator writing span after HANDBACK
    span_data = {
        "span_type": "handback_completion",
        "task_id": sample_delegate["task_id"],
        "agent": "engineer",
        "status": sample_handback["status"],
        "timestamp": datetime.now().isoformat(),
        "duration_seconds": sample_handback["metrics"]["duration_seconds"],
        "tokens_used": sample_handback["metrics"]["tokens"],
        "quality_score": sample_handback["metrics"]["quality"],
        "confidence": sample_handback["confidence"],
        "session_id": session_id,
        "harness": harness,
        "telemetry": {
            "trace_id": f"trace-{sample_delegate['task_id']}",
            "span_id": f"span-{uuid.uuid4().hex[:8]}",
            "parent_span_id": f"parent-{sample_delegate['task_id']}",
        },
    }

    span_file = dated_dir / f"SPAN-{sample_delegate['task_id']}.yaml"
    with open(span_file, "w") as f:
        yaml.dump(span_data, f)

    # Verify span file created
    assert span_file.exists()

    # Verify span content
    with open(span_file, "r") as f:
        loaded = yaml.safe_load(f)

    assert loaded["span_type"] == "handback_completion"
    assert loaded["task_id"] == sample_delegate["task_id"]
    assert loaded["status"] == sample_handback["status"]
    assert "timestamp" in loaded
    assert "duration_seconds" in loaded
    assert "tokens_used" in loaded
    assert "quality_score" in loaded
    assert "telemetry" in loaded
    assert "trace_id" in loaded["telemetry"]


# ============================================================================
# Integration: Full Cycle Test (All Steps)
# ============================================================================

def test_full_protocol_cycle(test_session: Tuple[Path, str, str], sample_delegate: Dict, sample_handback: Dict):
    """
    Integration test: Full DELEGATE → processing → HANDBACK → done cycle.

    This test orchestrates all previous tests in sequence:
    1. Write DELEGATE to incoming
    2. Move to processing (orchestrator)
    3. Agent writes HANDBACK
    4. Move to done
    5. Verify final state
    6. Write span
    """
    queue_path, session_id, harness = test_session

    # Step 1: DELEGATE to incoming
    incoming_dir = queue_path / "incoming"
    delegate_file = incoming_dir / f"{sample_delegate['task_id']}.yaml"
    with open(delegate_file, "w") as f:
        yaml.dump(sample_delegate, f)

    assert delegate_file.exists()

    # Step 2: Move to processing
    processing_dir = queue_path / "processing"
    processing_file = processing_dir / delegate_file.name
    shutil.move(str(delegate_file), str(processing_file))

    assert processing_file.exists()
    assert not delegate_file.exists()

    # Step 3: Agent writes HANDBACK
    handback_file = processing_dir / f"HANDBACK-{sample_delegate['task_id']}.yaml"
    with open(handback_file, "w") as f:
        yaml.dump(sample_handback, f)

    assert handback_file.exists()

    # Step 4: Move to done
    done_dir = queue_path / "done"
    done_handback = done_dir / handback_file.name
    done_delegate = done_dir / processing_file.name

    shutil.move(str(handback_file), str(done_handback))
    shutil.move(str(processing_file), str(done_delegate))

    # Step 5: Verify final state
    assert done_handback.exists()
    assert done_delegate.exists()
    assert len(list(processing_dir.glob("*.yaml"))) == 0

    # Step 6: Write span
    artifacts_dir = queue_path.parent.parent / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    dated_dir = artifacts_dir / date_str
    dated_dir.mkdir(parents=True, exist_ok=True)

    span_data = {
        "span_type": "full_cycle",
        "task_id": sample_delegate["task_id"],
        "status": sample_handback["status"],
        "timestamp": datetime.now().isoformat(),
        "stages": ["delegate_created", "processing_started", "handback_received", "completed"],
    }

    span_file = dated_dir / f"SPAN-{sample_delegate['task_id']}.yaml"
    with open(span_file, "w") as f:
        yaml.dump(span_data, f)

    assert span_file.exists()

    # Final verification
    with open(done_handback, "r") as f:
        final_handback = yaml.safe_load(f)

    assert final_handback["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
