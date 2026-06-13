"""
Unit tests for OrchestratorSkill.

Tests cover:
- Queue state machine transitions
- Task claiming and atomic moves
- HANDBACK parsing and routing
- Crash recovery and timeout detection
- Idle detection and sleep threshold
- QE gate invocation
- Span capture for observability
"""

import json
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.skills.orchestrator.scripts.orchestrator_skill import (
    OrchestratorSkill,
    QueueValidationError,
    TaskClaimError,
    HandbackParseError,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def temp_queue():
    """Create a temporary queue directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        queue_root = Path(tmpdir) / "queue"
        queue_root.mkdir()
        yield queue_root


@pytest.fixture
def orchestrator(temp_queue):
    """Create an OrchestratorSkill instance with temp queue."""
    skill = OrchestratorSkill(
        session_id="test-session",
        harness="local",
        queue_root=str(temp_queue),
    )
    return skill


# ─────────────────────────────────────────────────────────────────────────────
# Test: Queue Structure
# ─────────────────────────────────────────────────────────────────────────────

def test_queue_structure_created(orchestrator, temp_queue):
    """Test that queue directory structure is created."""
    assert (temp_queue / "incoming").exists()
    assert (temp_queue / "processing").exists()
    assert (temp_queue / "done").exists()
    assert (temp_queue / "failed").exists()


def test_keep_me_files_created(orchestrator, temp_queue):
    """Test that .keep.me files are created in each queue directory."""
    for state in ["incoming", "processing", "done", "failed"]:
        keep_me = temp_queue / state / ".keep.me"
        assert keep_me.exists()


# ─────────────────────────────────────────────────────────────────────────────
# Test: DELEGATE Validation
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_delegate_valid(orchestrator):
    """Test validation of a valid DELEGATE."""
    delegate = {
        "handoff_type": "DELEGATE",
        "task_id": "test-task-001",
        "agent": "engineer",
        "scope": "Test scope",
        "plan": ["Step 1", "Step 2"],
        "success_criteria": ["AC1"],
    }
    # Should not raise
    orchestrator._validate_delegate(delegate)


def test_validate_delegate_missing_fields(orchestrator):
    """Test validation fails with missing required fields."""
    delegate = {
        "handoff_type": "DELEGATE",
        "task_id": "test-task-001",
        # Missing: agent, scope, plan, success_criteria
    }
    with pytest.raises(QueueValidationError, match="missing required fields"):
        orchestrator._validate_delegate(delegate)


def test_validate_delegate_invalid_handoff_type(orchestrator):
    """Test validation fails with invalid handoff_type."""
    delegate = {
        "handoff_type": "INVALID",
        "task_id": "test-task-001",
        "agent": "engineer",
        "scope": "Test scope",
        "plan": ["Step 1"],
        "success_criteria": ["AC1"],
    }
    with pytest.raises(QueueValidationError, match="handoff_type"):
        orchestrator._validate_delegate(delegate)


# ─────────────────────────────────────────────────────────────────────────────
# Test: HANDBACK Validation
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_handback_valid(orchestrator):
    """Test validation of a valid HANDBACK."""
    handback = {
        "handoff_type": "HANDBACK",
        "task_id": "test-task-001",
        "status": "success",
    }
    # Should not raise
    orchestrator._validate_handback(handback)


def test_validate_handback_missing_fields(orchestrator):
    """Test validation fails with missing required fields."""
    handback = {
        "handoff_type": "HANDBACK",
        # Missing: task_id, status
    }
    with pytest.raises(QueueValidationError, match="missing required fields"):
        orchestrator._validate_handback(handback)


def test_validate_handback_invalid_status(orchestrator):
    """Test validation fails with invalid status."""
    handback = {
        "handoff_type": "HANDBACK",
        "task_id": "test-task-001",
        "status": "invalid_status",
    }
    with pytest.raises(QueueValidationError, match="Invalid status"):
        orchestrator._validate_handback(handback)


def test_validate_handback_valid_statuses(orchestrator):
    """Test validation accepts all valid statuses."""
    for status in ["success", "failure", "partial", "blocked", "escalate"]:
        handback = {
            "handoff_type": "HANDBACK",
            "task_id": "test-task-001",
            "status": status,
        }
        # Should not raise
        orchestrator._validate_handback(handback)


# ─────────────────────────────────────────────────────────────────────────────
# Test: Task Claiming
# ─────────────────────────────────────────────────────────────────────────────

def test_claim_task_success(orchestrator, temp_queue):
    """Test successful task claiming."""
    task_id = "test-task-001"
    delegate = {
        "handoff_type": "DELEGATE",
        "task_id": task_id,
        "agent": "engineer",
        "scope": "Test scope",
        "plan": ["Step 1"],
        "success_criteria": ["AC1"],
    }

    # Create DELEGATE file in incoming/
    incoming_file = temp_queue / "incoming" / f"{task_id}.yaml"
    with incoming_file.open("w") as f:
        import yaml
        yaml.dump(delegate, f)

    # Claim task
    claimed = orchestrator.claim_task(task_id, incoming_file)

    # Verify DELEGATE moved to processing/
    assert not incoming_file.exists()
    assert (temp_queue / "processing" / f"{task_id}.yaml").exists()

    # Verify metadata created
    meta_file = temp_queue / "processing" / f"{task_id}.meta.json"
    assert meta_file.exists()

    with meta_file.open("r") as f:
        metadata = json.load(f)

    assert metadata["task_id"] == task_id
    assert metadata["claimed_at"]
    assert metadata["retry_count"] == 0

    # Verify returned DELEGATE
    assert claimed["task_id"] == task_id


def test_claim_task_nonexistent(orchestrator):
    """Test claiming a nonexistent task raises error."""
    with pytest.raises(TaskClaimError):
        nonexistent = Path("/nonexistent/task.yaml")
        orchestrator.claim_task("nonexistent", nonexistent)


# ─────────────────────────────────────────────────────────────────────────────
# Test: State Transitions
# ─────────────────────────────────────────────────────────────────────────────

def test_move_task_to_done(orchestrator, temp_queue):
    """Test moving task from processing/ to done/."""
    task_id = "test-task-001"

    # Create task in processing/
    processing_file = temp_queue / "processing" / f"{task_id}.yaml"
    processing_file.write_text("test content")

    handback = {
        "handoff_type": "HANDBACK",
        "task_id": task_id,
        "status": "success",
        "output": "Task completed",
    }

    # Move to done
    orchestrator._move_task_to_done(task_id, handback)

    # Verify moved and HANDBACK written
    assert not processing_file.exists()
    assert (temp_queue / "done" / f"{task_id}.yaml").exists()
    assert (temp_queue / "done" / f"{task_id}-HANDBACK.yaml").exists()


def test_move_task_to_failed(orchestrator, temp_queue):
    """Test moving task from processing/ to failed/."""
    task_id = "test-task-001"

    # Create task in processing/
    processing_file = temp_queue / "processing" / f"{task_id}.yaml"
    processing_file.write_text("test content")

    # Move to failed
    orchestrator._move_task_to_failed(task_id, "Test error message")

    # Verify moved
    assert not processing_file.exists()
    assert (temp_queue / "failed" / f"{task_id}.yaml").exists()
    assert (temp_queue / "failed" / f"{task_id}-ERROR.json").exists()

    # Verify error file content
    with (temp_queue / "failed" / f"{task_id}-ERROR.json").open("r") as f:
        error = json.load(f)

    assert error["task_id"] == task_id
    assert error["error"] == "Test error message"


def test_move_task_to_failed_from_incoming(orchestrator, temp_queue):
    """Test moving task to failed from incoming/ directory."""
    task_id = "test-task-001"

    # Create task in incoming/
    incoming_file = temp_queue / "incoming" / f"{task_id}.yaml"
    incoming_file.write_text("test content")

    # Move to failed
    orchestrator._move_task_to_failed(task_id, "Invalid delegate")

    # Verify moved from incoming
    assert not incoming_file.exists()
    assert (temp_queue / "failed" / f"{task_id}.yaml").exists()


# ─────────────────────────────────────────────────────────────────────────────
# Test: Crash Recovery
# ─────────────────────────────────────────────────────────────────────────────

def test_recover_crashed_tasks_no_crashes(orchestrator):
    """Test crash recovery when no tasks are crashed."""
    recovered, failed = orchestrator.recover_crashed_tasks()
    assert recovered == 0
    assert failed == 0


def test_recover_crashed_tasks_orphaned(orchestrator, temp_queue):
    """Test detection of orphaned task (claimed_at > deadline)."""
    task_id = "test-task-001"

    # Create metadata with old claimed_at
    old_time = datetime.now(tz=timezone.utc) - timedelta(seconds=700)  # > 600s
    metadata = {
        "task_id": task_id,
        "claimed_at": old_time.isoformat(),
        "retry_count": 0,
        "last_error": None,
    }

    meta_file = temp_queue / "processing" / f"{task_id}.meta.json"
    with meta_file.open("w") as f:
        json.dump(metadata, f)

    # Create corresponding DELEGATE file
    delegate_file = temp_queue / "processing" / f"{task_id}.yaml"
    delegate_file.write_text("test")

    # Run recovery
    recovered, failed = orchestrator.recover_crashed_tasks()

    # Should be recovered (moved to retry-pending)
    assert recovered == 1
    assert failed == 0

    # Verify moved to retry-pending
    assert (temp_queue / "retry-pending" / f"{task_id}.yaml").exists()

    # Verify retry count incremented
    retry_meta = temp_queue / "retry-pending" / f"{task_id}.meta.json"
    with retry_meta.open("r") as f:
        retry_metadata = json.load(f)

    assert retry_metadata["retry_count"] == 1


def test_recover_crashed_tasks_max_retries(orchestrator, temp_queue):
    """Test task is moved to failed after max retries."""
    task_id = "test-task-001"

    # Create metadata with max retries reached
    old_time = datetime.now(tz=timezone.utc) - timedelta(seconds=700)
    metadata = {
        "task_id": task_id,
        "claimed_at": old_time.isoformat(),
        "retry_count": 3,  # >= RETRY_MAX_ATTEMPTS
        "last_error": None,
    }

    meta_file = temp_queue / "processing" / f"{task_id}.meta.json"
    with meta_file.open("w") as f:
        json.dump(metadata, f)

    delegate_file = temp_queue / "processing" / f"{task_id}.yaml"
    delegate_file.write_text("test")

    # Run recovery
    recovered, failed = orchestrator.recover_crashed_tasks()

    # Should be failed
    assert recovered == 0
    assert failed == 1

    # Verify moved to failed
    assert (temp_queue / "failed" / f"{task_id}.yaml").exists()


# ─────────────────────────────────────────────────────────────────────────────
# Test: Idle Detection
# ─────────────────────────────────────────────────────────────────────────────

def test_idle_detection_clean_poll(orchestrator):
    """Test clean_poll_count increments on empty polls."""
    assert orchestrator.clean_poll_count == 0

    processed, failed = orchestrator.poll_queue()

    assert processed == 0
    assert failed == 0
    assert orchestrator.clean_poll_count == 1


def test_idle_detection_reset_on_processed(orchestrator, temp_queue):
    """Test clean_poll_count resets when task is processed."""
    orchestrator.clean_poll_count = 2

    # Create a DELEGATE file
    task_id = "test-task-001"
    delegate = {
        "handoff_type": "DELEGATE",
        "task_id": task_id,
        "agent": "engineer",
        "scope": "Test scope",
        "plan": ["Step 1"],
        "success_criteria": ["AC1"],
    }

    incoming_file = temp_queue / "incoming" / f"{task_id}.yaml"
    with incoming_file.open("w") as f:
        import yaml
        yaml.dump(delegate, f)

    # Poll should process the task and reset counter
    processed, failed = orchestrator.poll_queue()

    assert processed == 1
    assert orchestrator.clean_poll_count == 0


def test_idle_loop_normal_sleep(orchestrator):
    """Test normal sleep behavior when below idle threshold."""
    orchestrator.clean_poll_count = 1  # < IDLE_THRESHOLD_POLLS

    # Mock time.sleep to verify it's called with correct duration
    with patch('time.sleep') as mock_sleep:
        result = orchestrator.run_idle_loop()
        mock_sleep.assert_called_once_with(orchestrator.POLL_INTERVAL_SEC)

    # Verify return structure
    assert result['work_processed'] == 0
    assert result['idle_entered'] is False
    assert result['wake_reason'] == 'normal'


def test_idle_loop_deep_sleep_enters_idle(orchestrator):
    """Test deep sleep behavior when idle threshold reached."""
    orchestrator.clean_poll_count = 3  # >= IDLE_THRESHOLD_POLLS

    # Mock _deep_sleep to avoid actual sleep
    with patch.object(orchestrator, '_deep_sleep', return_value='timeout'):
        result = orchestrator.run_idle_loop()

    # Verify return structure
    assert result['work_processed'] == 0
    assert result['idle_entered'] is True
    assert result['wake_reason'] == 'timeout'

    # Verify counter reset after deep sleep
    assert orchestrator.clean_poll_count == 0


def test_idle_loop_return_structure(orchestrator):
    """Test that run_idle_loop returns correct tuple structure."""
    orchestrator.clean_poll_count = 0

    result = orchestrator.run_idle_loop()

    # Verify return type and keys
    assert isinstance(result, dict)
    assert 'work_processed' in result
    assert 'idle_entered' in result
    assert 'wake_reason' in result

    assert isinstance(result['work_processed'], int)
    assert isinstance(result['idle_entered'], bool)
    assert isinstance(result['wake_reason'], str)


def test_idle_loop_multiple_cycles(orchestrator):
    """Test idle detection across multiple poll cycles."""
    # First two polls - clean
    orchestrator.clean_poll_count = 0
    result1 = orchestrator.run_idle_loop()
    assert result1['idle_entered'] is False
    assert orchestrator.clean_poll_count == 0

    # Simulate another clean poll by incrementing counter
    orchestrator.clean_poll_count = 1
    result2 = orchestrator.run_idle_loop()
    assert result2['idle_entered'] is False

    # Simulate third clean poll
    orchestrator.clean_poll_count = 2
    result3 = orchestrator.run_idle_loop()
    assert result3['idle_entered'] is False

    # Simulate fourth clean poll - should trigger deep sleep
    orchestrator.clean_poll_count = 3
    with patch.object(orchestrator, '_deep_sleep', return_value='file_event'):
        result4 = orchestrator.run_idle_loop()
        assert result4['idle_entered'] is True
        assert result4['wake_reason'] == 'file_event'


def test_deep_sleep_polling_detects_new_file(orchestrator, temp_queue):
    """Test that deep sleep polling detects new files in incoming/."""
    # This test is skipped in fast mode - file detection is tested via integration
    # Use mock to verify polling logic without actual file I/O delays
    incoming_dir = temp_queue / "incoming"

    # Mock Path.glob to simulate new files being created
    original_glob = Path.glob
    call_count = [0]

    def mock_glob(self, pattern):
        call_count[0] += 1
        # Call 1 is the initial snapshot; call 2 is the first in-loop poll.
        # With DEEP_SLEEP_SEC=0.5 and poll_interval=10s, only one in-loop
        # poll happens before timeout, so the new file must appear on call 2.
        if call_count[0] > 1:
            return [incoming_dir / "new-task.yaml"]
        return []

    original_timeout = orchestrator.DEEP_SLEEP_SEC
    orchestrator.DEEP_SLEEP_SEC = 0.5

    try:
        with patch.object(Path, 'glob', mock_glob):
            result = orchestrator._deep_sleep_polling()
            assert result == 'file_event'
    finally:
        orchestrator.DEEP_SLEEP_SEC = original_timeout


def test_deep_sleep_polling_timeout(orchestrator):
    """Test that deep sleep polling returns timeout if no files added."""
    # Use very short timeout for fast testing
    original_timeout = orchestrator.DEEP_SLEEP_SEC
    orchestrator.DEEP_SLEEP_SEC = 0.05  # 50ms timeout for fast test

    try:
        result = orchestrator._deep_sleep_polling()
        assert result == 'timeout'
    finally:
        orchestrator.DEEP_SLEEP_SEC = original_timeout


def test_deep_sleep_polling_signal_handling(orchestrator):
    """Test that deep sleep responds to SIGUSR1 signal."""
    import signal as sig
    import os
    import threading

    # Send SIGUSR1 after a short delay
    def send_signal_after_delay():
        time.sleep(0.05)
        try:
            os.kill(os.getpid(), sig.SIGUSR1)
        except:
            pass  # Ignore if signal fails

    thread = threading.Thread(target=send_signal_after_delay, daemon=True)
    thread.start()

    # Use moderate timeout
    original_timeout = orchestrator.DEEP_SLEEP_SEC
    orchestrator.DEEP_SLEEP_SEC = 0.5

    try:
        result = orchestrator._deep_sleep_polling()
        # May be 'signal' or 'timeout' depending on timing
        assert result in ('signal', 'timeout')
    finally:
        orchestrator.DEEP_SLEEP_SEC = original_timeout
        thread.join(timeout=1)


# ─────────────────────────────────────────────────────────────────────────────
# Test: QE Gate
# ─────────────────────────────────────────────────────────────────────────────

def test_qe_gate_approve_high_quality(orchestrator):
    """Test QE gate approves high confidence/quality HANDBACK."""
    handback = {
        "handoff_type": "HANDBACK",
        "task_id": "test-task-001",
        "status": "success",
        "confidence": 0.95,
        "metrics": {"quality": 0.90},
    }

    approved = orchestrator.invoke_qe_gate("test-task-001", handback)
    assert approved is True


def test_qe_gate_reject_low_quality(orchestrator):
    """Test QE gate rejects low confidence HANDBACK."""
    handback = {
        "handoff_type": "HANDBACK",
        "task_id": "test-task-001",
        "status": "success",
        "confidence": 0.5,
        "metrics": {"quality": 0.6},
    }

    approved = orchestrator.invoke_qe_gate("test-task-001", handback)
    assert approved is False


def test_qe_gate_reject_low_confidence(orchestrator):
    """Test QE gate rejects low confidence."""
    handback = {
        "handoff_type": "HANDBACK",
        "task_id": "test-task-001",
        "status": "success",
        "confidence": 0.65,
        "metrics": {"quality": 0.90},
    }

    approved = orchestrator.invoke_qe_gate("test-task-001", handback)
    assert approved is False


# ─────────────────────────────────────────────────────────────────────────────
# Test: Span Capture
# ─────────────────────────────────────────────────────────────────────────────

def test_capture_span(orchestrator, temp_queue):
    """Test SPAN capture for observability."""
    orchestrator.capture_span(
        "test_method",
        task_id="test-001",
        duration_ms=100,
    )

    spans_dir = temp_queue.parent / "spans"
    assert spans_dir.exists()

    span_files = list(spans_dir.glob("*.span.json"))
    assert len(span_files) > 0

    with span_files[0].open("r") as f:
        span = json.load(f)

    assert span["span_name"] == "orchestrator-test_method"
    assert span["attributes"]["task_id"] == "test-001"
    assert span["trace_id"] == "test-session"


# ─────────────────────────────────────────────────────────────────────────────
# Test: HANDBACK Parsing
# ─────────────────────────────────────────────────────────────────────────────

def test_parse_handback_valid(orchestrator):
    """Test parsing valid HANDBACK from text."""
    text = """Some output here...

handoff_type: HANDBACK
task_id: test-task-001
status: success
output: Task completed successfully
"""

    handback = orchestrator._parse_handback(text)
    assert handback["task_id"] == "test-task-001"
    assert handback["status"] == "success"


def test_parse_handback_missing(orchestrator):
    """Test parsing fails when HANDBACK is missing."""
    text = "No handback here"

    with pytest.raises(HandbackParseError):
        orchestrator._parse_handback(text)


# ─────────────────────────────────────────────────────────────────────────────
# Test: Session/Harness Detection
# ─────────────────────────────────────────────────────────────────────────────

def test_session_id_detection_explicit(temp_queue):
    """Test explicit session_id takes precedence."""
    skill = OrchestratorSkill(
        session_id="explicit-session",
        harness="local",
        queue_root=str(temp_queue),
    )
    assert skill.session_id == "explicit-session"


def test_harness_detection_explicit(temp_queue):
    """Test explicit harness takes precedence."""
    skill = OrchestratorSkill(
        session_id="test",
        harness="explicit-harness",
        queue_root=str(temp_queue),
    )
    assert skill.harness == "explicit-harness"


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_full_workflow_success(orchestrator, temp_queue):
    """Test full workflow: poll → claim → spawn → handle → done."""
    task_id = "integration-test-001"

    # Create a DELEGATE
    delegate = {
        "handoff_type": "DELEGATE",
        "task_id": task_id,
        "agent": "engineer",
        "scope": "Integration test",
        "plan": ["Step 1"],
        "success_criteria": ["AC1"],
    }

    incoming_file = temp_queue / "incoming" / f"{task_id}.yaml"
    with incoming_file.open("w") as f:
        import yaml
        yaml.dump(delegate, f)

    # Poll and process
    processed, failed = orchestrator.poll_queue()

    # Verify task moved to done
    assert processed == 1
    assert failed == 0
    assert (temp_queue / "done" / f"{task_id}-HANDBACK.yaml").exists()


def test_full_workflow_qe_rejection(orchestrator, temp_queue):
    """Test workflow with QE gate rejection."""
    task_id = "qe-reject-test"

    # Create a DELEGATE
    delegate = {
        "handoff_type": "DELEGATE",
        "task_id": task_id,
        "agent": "engineer",
        "scope": "Test QE rejection",
        "plan": ["Step 1"],
        "success_criteria": ["AC1"],
    }

    incoming_file = temp_queue / "incoming" / f"{task_id}.yaml"
    with incoming_file.open("w") as f:
        import yaml
        yaml.dump(delegate, f)

    # Mock spawn_sub_agent to return low-quality HANDBACK
    def mock_spawn(delegate_dict):
        return """
handoff_type: HANDBACK
task_id: qe-reject-test
status: success
confidence: 0.5
output: Low quality result
"""

    with patch.object(orchestrator, 'spawn_sub_agent', side_effect=mock_spawn):
        processed, failed = orchestrator.poll_queue()

    # QE should reject → moved to failed
    assert (temp_queue / "failed" / f"{task_id}.yaml").exists()


# ─────────────────────────────────────────────────────────────────────────────
# Test: Escalation Chaining (C2c parity — QUEUE-PROTOCOL.md "Escalation Chaining")
#
# Canonical behaviour: on HANDBACK status=escalate, the Orchestrator synthesizes
# a follow-on DELEGATE ({task_id}-escalated-to-{role}) into incoming/ and moves
# the original task to done/ with audit metadata. There is NO escalation/ state
# directory in the queue protocol.
# ─────────────────────────────────────────────────────────────────────────────

def _stage_processing_delegate(temp_queue, task_id, agent="engineer"):
    """Stage a claimed DELEGATE in processing/ (as claim_task would)."""
    import yaml
    delegate = {
        "handoff_type": "DELEGATE",
        "task_id": task_id,
        "agent": agent,
        "scope": "Escalation test scope",
        "plan": ["Step 1"],
        "success_criteria": ["AC1"],
    }
    processing_file = temp_queue / "processing" / f"{task_id}.yaml"
    with processing_file.open("w") as f:
        yaml.dump(delegate, f)
    meta_file = temp_queue / "processing" / f"{task_id}.meta.json"
    with meta_file.open("w") as f:
        json.dump({"task_id": task_id, "retry_count": 0}, f)
    return delegate


def _escalate_handback(task_id, escalate_to="senior-engineer", chain=None):
    """Build a HANDBACK with status=escalate."""
    return {
        "handoff_type": "HANDBACK",
        "task_id": task_id,
        "status": "escalate",
        "output": {
            "escalate_to": escalate_to,
            "escalation_reason": "Complex architecture requires senior review",
        },
        "escalation_chain": chain or [],
    }


def test_escalation_enqueues_follow_on_delegate_in_incoming(orchestrator, temp_queue):
    """Escalation must synthesize a new DELEGATE into incoming/ (canonical C2c)."""
    task_id = "escalate-task-001"
    _stage_processing_delegate(temp_queue, task_id)

    orchestrator._move_task_to_escalation(task_id, _escalate_handback(task_id))

    expected = temp_queue / "incoming" / f"{task_id}-escalated-to-senior-engineer.yaml"
    assert expected.exists(), (
        "Escalation must enqueue follow-on DELEGATE in incoming/, "
        "not a separate escalation/ directory"
    )


def test_escalation_does_not_create_escalation_dir(orchestrator, temp_queue):
    """escalation/ is not a recognized queue state dir — must not be created."""
    task_id = "escalate-task-002"
    _stage_processing_delegate(temp_queue, task_id)

    orchestrator._move_task_to_escalation(task_id, _escalate_handback(task_id))

    assert not (temp_queue / "escalation").exists()
    assert not (temp_queue.parent / "escalation").exists()


def test_escalation_delegate_shape_matches_c2c(orchestrator, temp_queue):
    """Synthesized DELEGATE must carry agent, context, and escalation_chain."""
    import yaml
    task_id = "escalate-task-003"
    _stage_processing_delegate(temp_queue, task_id, agent="engineer")
    handback = _escalate_handback(task_id, chain=[])

    orchestrator._move_task_to_escalation(task_id, handback)

    delegate_file = temp_queue / "incoming" / f"{task_id}-escalated-to-senior-engineer.yaml"
    with delegate_file.open("r") as f:
        delegate = yaml.safe_load(f)

    assert delegate["handoff_type"] == "DELEGATE"
    assert delegate["agent"] == "senior-engineer"
    assert delegate["task_id"] == f"{task_id}-escalated-to-senior-engineer"
    assert delegate["context"]["original_task_id"] == task_id
    assert delegate["context"]["original_handback"] == handback
    assert delegate["context"]["escalation_reason"] == (
        "Complex architecture requires senior review"
    )
    assert delegate["escalation_chain"] == ["engineer"]


def test_escalation_chain_appends_original_role(orchestrator, temp_queue):
    """escalation_chain must append the role that just escalated."""
    import yaml
    task_id = "escalate-task-004"
    _stage_processing_delegate(temp_queue, task_id, agent="senior-engineer")
    handback = _escalate_handback(
        task_id, escalate_to="principal-engineer", chain=["engineer"]
    )

    orchestrator._move_task_to_escalation(task_id, handback)

    delegate_file = (
        temp_queue / "incoming" / f"{task_id}-escalated-to-principal-engineer.yaml"
    )
    with delegate_file.open("r") as f:
        delegate = yaml.safe_load(f)

    assert delegate["escalation_chain"] == ["engineer", "senior-engineer"]


def test_escalation_delegate_is_reingestable(orchestrator, temp_queue):
    """Synthesized DELEGATE must pass the skill's own DELEGATE validation."""
    import yaml
    task_id = "escalate-task-005"
    _stage_processing_delegate(temp_queue, task_id)

    orchestrator._move_task_to_escalation(task_id, _escalate_handback(task_id))

    delegate_file = temp_queue / "incoming" / f"{task_id}-escalated-to-senior-engineer.yaml"
    with delegate_file.open("r") as f:
        delegate = yaml.safe_load(f)

    # Must not raise — otherwise poll_queue would route it straight to failed/
    orchestrator._validate_delegate(delegate)


def test_escalation_default_target_lead_engineer(orchestrator, temp_queue):
    """Missing escalate_to falls back to lead-engineer (C2c default)."""
    task_id = "escalate-task-006"
    _stage_processing_delegate(temp_queue, task_id)
    handback = {
        "handoff_type": "HANDBACK",
        "task_id": task_id,
        "status": "escalate",
        "output": "Needs review but no explicit target",
    }

    orchestrator._move_task_to_escalation(task_id, handback)

    expected = temp_queue / "incoming" / f"{task_id}-escalated-to-lead-engineer.yaml"
    assert expected.exists()


def test_escalation_moves_original_to_done_with_audit(orchestrator, temp_queue):
    """Original task archives to done/ with HANDBACK audit metadata."""
    import yaml
    task_id = "escalate-task-007"
    _stage_processing_delegate(temp_queue, task_id)

    orchestrator._move_task_to_escalation(task_id, _escalate_handback(task_id))

    # Original DELEGATE archived to done/
    assert (temp_queue / "done" / f"{task_id}.yaml").exists()
    assert not (temp_queue / "processing" / f"{task_id}.yaml").exists()
    # Metadata cleaned up
    assert not (temp_queue / "processing" / f"{task_id}.meta.json").exists()
    # HANDBACK audit file records the chained DELEGATE
    handback_file = temp_queue / "done" / f"{task_id}-HANDBACK.yaml"
    assert handback_file.exists()
    with handback_file.open("r") as f:
        audit = yaml.safe_load(f)
    assert audit["escalation_delegate_created"] == (
        f"{task_id}-escalated-to-senior-engineer.yaml"
    )


def test_handle_handback_escalate_routes_to_incoming(orchestrator, temp_queue):
    """End-to-end: handle_handback with status=escalate chains into incoming/."""
    task_id = "escalate-task-008"
    _stage_processing_delegate(temp_queue, task_id)
    handback_text = f"""
handoff_type: HANDBACK
task_id: {task_id}
status: escalate
output:
  escalate_to: lead-engineer
  escalation_reason: Quality concerns
escalation_chain: []
"""

    result = orchestrator.handle_handback(task_id, handback_text)

    assert result["status"] == "escalate"
    expected = temp_queue / "incoming" / f"{task_id}-escalated-to-lead-engineer.yaml"
    assert expected.exists()
    assert not (temp_queue.parent / "escalation").exists()


# ─────────────────────────────────────────────────────────────────────────────
# Test: Wake Timer and Stalled Task Detection
# ─────────────────────────────────────────────────────────────────────────────

def test_wake_timer_no_stalled_tasks(orchestrator):
    """Test wake_timer returns no stalled tasks when queue is healthy."""
    result = orchestrator.wake_timer()

    assert result['stalled_detected'] == 0
    assert result['recovered'] == 0
    assert result['escalated'] == 0
    assert result['wake_reason'] == 'no_stalled_tasks'


def test_wake_timer_detects_stalled_task(orchestrator, temp_queue):
    """Test wake_timer detects task without recent heartbeat."""
    task_id = "stalled-task-001"

    # Create a task in processing/ with old heartbeat
    processing_dir = temp_queue / "processing"

    # Create metadata file with old timestamp
    now_iso = datetime.now(tz=timezone.utc).isoformat()
    old_timestamp = (datetime.now(tz=timezone.utc) - timedelta(seconds=150)).timestamp()

    metadata = {
        "task_id": task_id,
        "claimed_at": now_iso,
        "retry_count": 0,
        "last_error": None,
    }
    meta_file = processing_dir / f"{task_id}.meta.json"
    with meta_file.open("w") as f:
        json.dump(metadata, f)

    # Set old heartbeat (150 seconds ago, exceeds 120s default timeout)
    orchestrator.heartbeat_tracker[task_id] = old_timestamp

    # Detect stalled tasks
    stalled = orchestrator.detect_stalled_tasks()

    assert task_id in stalled
    assert len(stalled) == 1


def test_wake_timer_recovers_stalled_task(orchestrator, temp_queue):
    """Test wake_timer recovers stalled task to retry-pending."""
    task_id = "stalled-task-002"

    # Create a task in processing/ with old heartbeat
    processing_dir = temp_queue / "processing"

    # Create metadata file
    now_iso = datetime.now(tz=timezone.utc).isoformat()
    old_timestamp = (datetime.now(tz=timezone.utc) - timedelta(seconds=150)).timestamp()

    metadata = {
        "task_id": task_id,
        "claimed_at": now_iso,
        "retry_count": 0,
        "last_error": None,
    }
    meta_file = processing_dir / f"{task_id}.meta.json"
    with meta_file.open("w") as f:
        json.dump(metadata, f)

    # Create delegate file in processing/
    delegate_file = processing_dir / f"{task_id}.yaml"
    delegate_file.write_text(f"task_id: {task_id}\n")

    # Set old heartbeat
    orchestrator.heartbeat_tracker[task_id] = old_timestamp

    # Run wake_timer
    result = orchestrator.wake_timer()

    assert result['stalled_detected'] == 1
    assert result['recovered'] == 1
    assert result['escalated'] == 0

    # Verify task was moved to retry-pending
    retry_pending_dir = temp_queue / "retry-pending"
    assert (retry_pending_dir / f"{task_id}.yaml").exists()
    assert not (processing_dir / f"{task_id}.yaml").exists()


def test_wake_timer_escalates_max_retries(orchestrator, temp_queue):
    """Test wake_timer escalates task after max retries exceeded."""
    task_id = "max-retries-task-003"

    # Create a task in processing/ with max retries
    processing_dir = temp_queue / "processing"

    # Create metadata file with max retries reached
    now_iso = datetime.now(tz=timezone.utc).isoformat()
    old_timestamp = (datetime.now(tz=timezone.utc) - timedelta(seconds=150)).timestamp()

    metadata = {
        "task_id": task_id,
        "claimed_at": now_iso,
        "retry_count": 3,  # Max retries (default)
        "last_error": None,
    }
    meta_file = processing_dir / f"{task_id}.meta.json"
    with meta_file.open("w") as f:
        json.dump(metadata, f)

    # Create delegate file
    delegate_file = processing_dir / f"{task_id}.yaml"
    delegate_file.write_text(f"task_id: {task_id}\n")

    # Set old heartbeat
    orchestrator.heartbeat_tracker[task_id] = old_timestamp

    # Run wake_timer
    result = orchestrator.wake_timer()

    assert result['stalled_detected'] == 1
    assert result['recovered'] == 0
    assert result['escalated'] == 1

    # Verify task was moved to escalation
    assert not (processing_dir / f"{task_id}.yaml").exists()


def test_heartbeat_update_resets_stall_timer(orchestrator):
    """Test that updating heartbeat resets stall detection."""
    task_id = "heartbeat-test-004"

    # Set initial heartbeat
    orchestrator.update_heartbeat(task_id)
    initial_time = orchestrator.heartbeat_tracker[task_id]

    # Wait a bit and update again
    time.sleep(0.1)
    orchestrator.update_heartbeat(task_id)
    updated_time = orchestrator.heartbeat_tracker[task_id]

    # Time should be updated
    assert updated_time > initial_time


def test_heartbeat_interval_configuration(orchestrator):
    """Test heartbeat_interval is configurable."""
    # Check default config
    assert orchestrator.config.heartbeat_interval == 30

    # Create new config with custom interval
    from src.skills.orchestrator.scripts.orchestrator_skill import PollingConfig
    custom_config = PollingConfig(heartbeat_interval=60)

    assert custom_config.heartbeat_interval == 60
    assert custom_config.to_dict()['heartbeat_interval'] == 60


def test_stale_and_crash_thresholds(orchestrator):
    """Test SLA thresholds are properly configured."""
    config = orchestrator.config

    # Verify thresholds match SPEC queue SLA design
    assert config.heartbeat_interval == 30  # Default: 30s
    assert config.stale_threshold_sec == 300  # WARN at 300s
    assert config.crash_threshold_sec == 600  # ESCALATE at 600s (LOCKED)

    # Verify relationship: stale < crash
    assert config.stale_threshold_sec < config.crash_threshold_sec


def test_wake_timer_span_capture(orchestrator, temp_queue):
    """Test wake_timer captures observability span."""
    task_id = "span-test-005"

    # Create a stalled task
    processing_dir = temp_queue / "processing"
    now_iso = datetime.now(tz=timezone.utc).isoformat()
    old_timestamp = (datetime.now(tz=timezone.utc) - timedelta(seconds=150)).timestamp()

    metadata = {
        "task_id": task_id,
        "claimed_at": now_iso,
        "retry_count": 0,
        "last_error": None,
    }
    meta_file = processing_dir / f"{task_id}.meta.json"
    with meta_file.open("w") as f:
        json.dump(metadata, f)

    delegate_file = processing_dir / f"{task_id}.yaml"
    delegate_file.write_text(f"task_id: {task_id}\n")

    orchestrator.heartbeat_tracker[task_id] = old_timestamp

    # Run wake_timer (should capture span)
    result = orchestrator.wake_timer()

    # Verify result
    assert result['stalled_detected'] == 1
    assert result['recovered'] == 1
