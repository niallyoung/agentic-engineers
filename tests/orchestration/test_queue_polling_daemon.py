"""
Tests for Queue Polling Daemon — Phase 1

Covers:
1. Daemon startup and shutdown (SIGTERM, SIGINT)
2. Queue state transitions (incoming → processing → done, → failed)
3. Task routing to agents
4. HANDBACK monitoring and timeout
5. Error handling and recovery
6. Backwards compatibility (poll_and_process, run_poll_cycle)
7. ExtendedQueueManager (failed/ directory)
"""

import os
import sys
import signal
import time
import threading
import tempfile
import yaml
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

from src.orchestration.agents.automation import AutomationController, AutomationMetrics, ShutdownSignal
from src.orchestration.agents.orchestrator import OrchestratorAgent, QueueManager, TaskRouter
from src.orchestration.queue_manager import ExtendedQueueManager


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def temp_queue(tmp_path):
    """Create a temporary queue directory with session-id structure."""
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()
    # Create session-id partitioned structure
    session_dir = queue_dir / "default"
    (session_dir / "incoming").mkdir(parents=True)
    (session_dir / "processing").mkdir(parents=True)
    (session_dir / "done").mkdir(parents=True)
    return queue_dir


@pytest.fixture
def sample_delegate():
    """Sample DELEGATE YAML dict."""
    return {
        "task_id": "2026-05-17-test-task",
        "role": "engineer",
        "model": "claude-sonnet-4-6",
        "effort": "medium",
        "scope": "Test task for queue polling daemon",
        "plan": ["Step 1: Do the thing", "Step 2: Verify it worked"],
        "success_criteria": ["All tests pass", "Coverage >= 90%"],
    }


@pytest.fixture
def sample_handback():
    """Sample HANDBACK dict."""
    return {
        "handoff_type": "HANDBACK",
        "task_id": "2026-05-17-test-task",
        "status": "complete",
        "quality_score": 92,
        "deliverables": ["src/foo.py"],
        "tokens_in": 1000,
        "tokens_out": 500,
    }


def write_delegate(queue_dir: Path, filename: str, delegate: dict, session_id: str = None):
    """Helper: write a DELEGATE YAML to incoming/.
    
    If session_id is None, writes to queue_dir/incoming/ directly (for QueueManagers
    that have already been initialized and have their session_queue_dir set).
    If session_id is provided, writes to queue_dir/{session_id}/incoming/.
    """
    if session_id is not None:
        incoming = queue_dir / session_id / "incoming"
    else:
        incoming = queue_dir / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    path = incoming / filename
    with open(path, "w") as f:
        yaml.dump(delegate, f)
    return path


def write_delegate_to_qm(qm: QueueManager, filename: str, delegate: dict) -> Path:
    """Helper: write a DELEGATE YAML directly to qm.incoming_dir."""
    qm.incoming_dir.mkdir(parents=True, exist_ok=True)
    path = qm.incoming_dir / filename
    with open(path, "w") as f:
        yaml.dump(delegate, f)
    return path


# ─── 1. Daemon Startup and Shutdown ──────────────────────────────────────────


class TestDaemonStartupShutdown:
    """Test AutomationController daemon lifecycle."""

    def test_daemon_initializes_with_defaults(self, temp_queue):
        """Controller initializes with sane defaults."""
        with patch("src.orchestration.agents.automation.OrchestratorAgent") as mock_orch:
            mock_orch.return_value = Mock(last_task_time=time.time())
            ctrl = AutomationController(
                queue_dir=str(temp_queue),
                max_cycles=1,
                daemon_mode=False,
                idle_timeout=1,
            )
        assert ctrl.poll_interval > 0
        assert ctrl.idle_timeout >= 0

    def test_daemon_mode_flag(self, temp_queue):
        """daemon_mode=True disables idle timeout exit."""
        with patch("src.orchestration.agents.automation.OrchestratorAgent") as mock_orch:
            mock_orch.return_value = Mock(last_task_time=time.time())
            ctrl = AutomationController(
                queue_dir=str(temp_queue),
                daemon_mode=True,
                max_cycles=1,
            )
        assert ctrl.daemon_mode is True

    def test_sigterm_sets_shutdown_flag(self, temp_queue):
        """SIGTERM handler sets shutdown_requested=True."""
        with patch("src.orchestration.agents.automation.OrchestratorAgent") as mock_orch:
            mock_orch.return_value = Mock(last_task_time=time.time())
            ctrl = AutomationController(
                queue_dir=str(temp_queue),
                max_cycles=1,
                daemon_mode=False,
                idle_timeout=1,
            )
        ctrl._setup_signal_handlers()
        # Simulate SIGTERM
        ctrl._setup_signal_handlers()
        os.kill(os.getpid(), signal.SIGTERM)
        time.sleep(0.1)
        assert ctrl.shutdown_requested is True
        assert ctrl.shutdown_signal == ShutdownSignal.SIGTERM

    def test_sigint_sets_shutdown_flag(self, temp_queue):
        """SIGINT handler sets shutdown_requested=True."""
        with patch("src.orchestration.agents.automation.OrchestratorAgent") as mock_orch:
            mock_orch.return_value = Mock(last_task_time=time.time())
            ctrl = AutomationController(
                queue_dir=str(temp_queue),
                max_cycles=1,
                daemon_mode=False,
                idle_timeout=1,
            )
        ctrl._setup_signal_handlers()
        os.kill(os.getpid(), signal.SIGINT)
        time.sleep(0.1)
        assert ctrl.shutdown_requested is True
        assert ctrl.shutdown_signal == ShutdownSignal.SIGINT

    def test_max_cycles_exits_cleanly(self, temp_queue):
        """max_cycles=N causes clean exit after N cycles."""
        with patch("src.orchestration.agents.automation.OrchestratorAgent") as mock_orch:
            mock_instance = Mock()
            mock_instance.last_task_time = time.time()
            mock_instance.run_poll_cycle.return_value = {
                "tasks_processed": 0,
                "tasks_success": 0,
                "tasks_escalated": 0,
                "tasks_failed": 0,
            }
            mock_orch.return_value = mock_instance
            ctrl = AutomationController(
                queue_dir=str(temp_queue),
                max_cycles=3,
                poll_interval=0.01,
                daemon_mode=True,
            )
            result = ctrl.run()

        assert result["status"] == "COMPLETE"
        assert result["exit_reason"] == "max_cycles"
        assert ctrl.metrics.cycles_completed == 3

    def test_graceful_shutdown_after_current_cycle(self, temp_queue):
        """SIGTERM causes exit after current cycle completes."""
        call_count = 0

        def slow_poll_cycle():
            nonlocal call_count
            call_count += 1
            time.sleep(0.05)
            return {"tasks_processed": 0, "tasks_success": 0, "tasks_escalated": 0, "tasks_failed": 0}

        with patch("src.orchestration.agents.automation.OrchestratorAgent") as mock_orch:
            mock_instance = Mock()
            mock_instance.last_task_time = time.time()
            mock_instance.run_poll_cycle.side_effect = slow_poll_cycle
            mock_orch.return_value = mock_instance

            ctrl = AutomationController(
                queue_dir=str(temp_queue),
                poll_interval=0.01,
                daemon_mode=True,
            )
            ctrl._setup_signal_handlers()

            def send_sigterm():
                time.sleep(0.08)
                os.kill(os.getpid(), signal.SIGTERM)

            t = threading.Thread(target=send_sigterm)
            t.start()
            result = ctrl.run()
            t.join()

        assert result["status"] == "COMPLETE"
        assert result["exit_reason"] == "sigterm"


# ─── 2. Queue State Transitions ──────────────────────────────────────────────


class TestQueueStateTransitions:
    """Test atomic queue state transitions."""

    def test_incoming_to_processing(self, temp_queue, sample_delegate):
        """Task moves from incoming to processing atomically."""
        qm = QueueManager(queue_dir=str(temp_queue))
        write_delegate_to_qm(qm, "DELEGATE-2026-05-17-test-task.yaml", sample_delegate)
        result = qm.move_task(
            task_id="2026-05-17-test-task",
            from_state="incoming",
            to_state="processing",
        )
        assert result["success"] is True
        assert result["moved_from"] == "incoming"
        assert result["moved_to"] == "processing"
        assert not (qm.incoming_dir / "DELEGATE-2026-05-17-test-task.yaml").exists()
        assert (qm.processing_dir / "DELEGATE-2026-05-17-test-task.yaml").exists()

    def test_processing_to_done(self, temp_queue, sample_delegate, sample_handback):
        """Task moves from processing to done with HANDBACK metadata."""
        qm = QueueManager(queue_dir=str(temp_queue))
        write_delegate_to_qm(qm, "DELEGATE-2026-05-17-test-task.yaml", sample_delegate)
        qm.move_task("2026-05-17-test-task", "incoming", "processing")
        result = qm.move_task(
            task_id="2026-05-17-test-task",
            from_state="processing",
            to_state="done",
            metadata=sample_handback,
        )
        assert result["success"] is True
        assert result["moved_to"] == "done"
        assert not (qm.processing_dir / "DELEGATE-2026-05-17-test-task.yaml").exists()

    def test_invalid_transition_raises(self, temp_queue, sample_delegate):
        """Invalid state transition raises ValueError."""
        qm = QueueManager(queue_dir=str(temp_queue))
        write_delegate_to_qm(qm, "DELEGATE-2026-05-17-test-task.yaml", sample_delegate)
        with pytest.raises(ValueError, match="Invalid transition"):
            qm.move_task("2026-05-17-test-task", "incoming", "done")

    def test_missing_task_raises(self, temp_queue):
        """Missing task raises FileNotFoundError."""
        qm = QueueManager(queue_dir=str(temp_queue))
        with pytest.raises(FileNotFoundError):
            qm.move_task("nonexistent-task", "incoming", "processing")

    def test_audit_trail_appended(self, temp_queue, sample_delegate):
        """Audit trail is appended on each transition."""
        qm = QueueManager(queue_dir=str(temp_queue))
        write_delegate_to_qm(qm, "DELEGATE-2026-05-17-test-task.yaml", sample_delegate)
        result = qm.move_task("2026-05-17-test-task", "incoming", "processing")
        assert len(result["audit_trail"]) >= 1
        assert result["audit_trail"][0]["action"] == "move_task"

    def test_move_to_failed(self, temp_queue, sample_delegate):
        """ExtendedQueueManager moves task to failed/ directory."""
        qm = ExtendedQueueManager(queue_dir=str(temp_queue))
        write_delegate_to_qm(qm, "DELEGATE-2026-05-17-test-task.yaml", sample_delegate)
        # First move to processing
        qm.move_task("2026-05-17-test-task", "incoming", "processing")
        # Then move to failed
        result = qm.move_to_failed(
            task_id="2026-05-17-test-task",
            reason="agent timeout",
            from_state="processing",
        )
        assert result["success"] is True
        assert result["moved_to"] == "failed"
        assert (qm.failed_dir / "2026-05-17-test-task-FAILED.yaml").exists()
        assert not (qm.processing_dir / "DELEGATE-2026-05-17-test-task.yaml").exists()

    def test_recover_failed_task(self, temp_queue, sample_delegate):
        """Failed task can be recovered back to incoming/."""
        qm = ExtendedQueueManager(queue_dir=str(temp_queue))
        write_delegate_to_qm(qm, "DELEGATE-2026-05-17-test-task.yaml", sample_delegate)
        qm.move_task("2026-05-17-test-task", "incoming", "processing")
        qm.move_to_failed("2026-05-17-test-task", reason="test failure")
        result = qm.recover_failed_task("2026-05-17-test-task")
        assert result["success"] is True
        assert result["moved_to"] == "incoming"
        assert not (qm.failed_dir / "2026-05-17-test-task-FAILED.yaml").exists()

    def test_failed_metadata_attached(self, temp_queue, sample_delegate):
        """Failure reason is stored in task metadata."""
        qm = ExtendedQueueManager(queue_dir=str(temp_queue))
        write_delegate_to_qm(qm, "DELEGATE-2026-05-17-test-task.yaml", sample_delegate)
        qm.move_task("2026-05-17-test-task", "incoming", "processing")
        qm.move_to_failed("2026-05-17-test-task", reason="timeout after 4h")
        failed_path = qm.failed_dir / "2026-05-17-test-task-FAILED.yaml"
        with open(failed_path) as f:
            data = yaml.safe_load(f)
        assert data["_failure_reason"] == "timeout after 4h"
        assert "_failed_at" in data

    def test_list_failed_tasks(self, temp_queue, sample_delegate):
        """list_failed_tasks() returns failed task filenames."""
        qm = ExtendedQueueManager(queue_dir=str(temp_queue))
        write_delegate_to_qm(qm, "DELEGATE-2026-05-17-test-task.yaml", sample_delegate)
        qm.move_task("2026-05-17-test-task", "incoming", "processing")
        qm.move_to_failed("2026-05-17-test-task", reason="test")
        failed = qm.list_failed_tasks()
        assert len(failed) == 1
        assert "FAILED" in failed[0]


# ─── 3. Task Routing ─────────────────────────────────────────────────────────


class TestTaskRouting:
    """Test TaskRouter routes DELEGATEs to correct agents."""

    def test_explicit_role_engineer(self):
        """Explicit role=engineer routes to EngineerAgent."""
        router = TaskRouter()
        delegate = {"role": "engineer", "plan": ["step 1"]}
        agent_name, agent = router.route_task(delegate)
        assert agent_name == "engineer"

    def test_explicit_role_senior_engineer(self):
        """Explicit role=senior_engineer routes to SeniorEngineerAgent."""
        router = TaskRouter()
        delegate = {"role": "senior_engineer"}
        agent_name, agent = router.route_task(delegate)
        assert agent_name == "senior_engineer"

    def test_explicit_role_principal_engineer(self):
        """Explicit role=principal_engineer routes to PrincipalEngineerAgent."""
        router = TaskRouter()
        delegate = {"role": "principal_engineer"}
        agent_name, agent = router.route_task(delegate)
        assert agent_name == "principal_engineer"

    def test_explicit_role_security_engineer(self):
        """Explicit role=security_engineer routes to SecurityEngineerAgent."""
        router = TaskRouter()
        delegate = {"role": "security_engineer"}
        agent_name, agent = router.route_task(delegate)
        assert agent_name == "security_engineer"

    def test_security_scoped_routes_to_security(self):
        """is_security_scoped=True routes to SecurityEngineerAgent."""
        router = TaskRouter()
        delegate = {"is_security_scoped": True}
        agent_name, _ = router.route_task(delegate)
        assert agent_name == "security_engineer"

    def test_high_complexity_no_plan_routes_to_senior(self):
        """High complexity without plan routes to SeniorEngineerAgent."""
        router = TaskRouter()
        delegate = {"complexity": "high", "plan": None}
        agent_name, _ = router.route_task(delegate)
        assert agent_name == "senior_engineer"

    def test_default_routes_to_engineer(self):
        """Default (no special fields) routes to EngineerAgent."""
        router = TaskRouter()
        delegate = {"scope": "simple task", "plan": ["step 1"]}
        agent_name, _ = router.route_task(delegate)
        assert agent_name == "engineer"

    def test_all_known_roles_are_routable(self):
        """All known roles can be routed without error."""
        router = TaskRouter()
        known_roles = [
            "orchestrator", "engineer", "senior_engineer", "lead_engineer",
            "principal_engineer", "quality_engineer", "model_engineer", "security_engineer"
        ]
        for role in known_roles:
            agent_name, agent = router.route_task({"role": role})
            assert agent_name == role
            # agent is None — TaskRouter routes by name only (no stub instantiation)


# ─── 4. HANDBACK Monitoring and Timeout ──────────────────────────────────────


class TestHandbackMonitoring:
    """Test HANDBACK correlation and timeout handling."""

    def test_wait_for_children_no_children(self, temp_queue):
        """wait_for_children returns all_complete immediately if no children."""
        qm = QueueManager(queue_dir=str(temp_queue))
        orch = OrchestratorAgent.__new__(OrchestratorAgent)
        orch.queue_manager = qm
        result = orch.wait_for_children("nonexistent-parent", timeout_minutes=1)
        assert result["status"] == "all_complete"
        assert result["children_results"] == {}

    def test_wait_for_children_timeout(self, temp_queue, sample_delegate):
        """wait_for_children times out if children don't complete."""
        # Create QueueManager first to get the actual session_id-partitioned paths
        qm = QueueManager(queue_dir=str(temp_queue))
        # Write a child task to processing (never completes)
        child = dict(sample_delegate)
        child["task_id"] = "2026-05-17-child-task"
        child["parent_task_id"] = "2026-05-17-parent-task"
        qm.processing_dir.mkdir(parents=True, exist_ok=True)
        with open(qm.processing_dir / "child.yaml", "w") as f:
            yaml.dump(child, f)
        orch = OrchestratorAgent.__new__(OrchestratorAgent)
        orch.queue_manager = qm

        # Use a very short timeout (fractional minutes)
        result = orch.wait_for_children("2026-05-17-parent-task", timeout_minutes=0.001)
        assert result["status"] == "timed_out"
        assert "2026-05-17-child-task" in result["children_failed"]

    def test_route_handback_proceed_high_score(self, temp_queue):
        """HANDBACK with quality_score >= 90 → PROCEED."""
        qm = QueueManager(queue_dir=str(temp_queue))
        orch = OrchestratorAgent.__new__(OrchestratorAgent)
        orch.queue_manager = qm
        orch.task_state = {}
        handback = {"task_id": "t1", "status": "complete", "quality_score": 95}
        action, ctx = orch.route_handback(handback, {})
        assert action == "PROCEED"

    def test_route_handback_escalate_low_score(self, temp_queue):
        """HANDBACK with quality_score < 60 → ESCALATE."""
        qm = QueueManager(queue_dir=str(temp_queue))
        orch = OrchestratorAgent.__new__(OrchestratorAgent)
        orch.queue_manager = qm
        orch.task_state = {}
        handback = {"task_id": "t1", "status": "complete", "quality_score": 45}
        action, ctx = orch.route_handback(handback, {})
        assert action == "ESCALATE"

    def test_route_handback_rework_medium_score(self, temp_queue):
        """HANDBACK with quality_score 60-69 → REWORK."""
        qm = QueueManager(queue_dir=str(temp_queue))
        orch = OrchestratorAgent.__new__(OrchestratorAgent)
        orch.queue_manager = qm
        orch.task_state = {}
        handback = {"task_id": "t1", "status": "complete", "quality_score": 65}
        action, ctx = orch.route_handback(handback, {})
        assert action == "REWORK"

    def test_route_handback_critical_failed_status(self, temp_queue):
        """HANDBACK with status=failed → ESCALATE regardless of score."""
        qm = QueueManager(queue_dir=str(temp_queue))
        orch = OrchestratorAgent.__new__(OrchestratorAgent)
        orch.queue_manager = qm
        orch.task_state = {}
        handback = {"task_id": "t1", "status": "failed", "quality_score": 95, "failure_reason": "crash"}
        action, ctx = orch.route_handback(handback, {})
        assert action == "ESCALATE"


# ─── 5. Error Handling and Recovery ──────────────────────────────────────────


class TestErrorHandling:
    """Test error handling and recovery paths."""

    def test_polling_cycle_error_does_not_crash_daemon(self, temp_queue):
        """A polling cycle error is caught and daemon continues."""
        call_count = 0

        def failing_cycle():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Simulated cycle failure")
            return {"tasks_processed": 0, "tasks_success": 0, "tasks_escalated": 0, "tasks_failed": 0}

        with patch("src.orchestration.agents.automation.OrchestratorAgent") as mock_orch:
            mock_instance = Mock()
            mock_instance.last_task_time = time.time()
            mock_instance.run_poll_cycle.side_effect = failing_cycle
            mock_orch.return_value = mock_instance

            ctrl = AutomationController(
                queue_dir=str(temp_queue),
                max_cycles=2,
                poll_interval=0.01,
                daemon_mode=True,
            )
            result = ctrl.run()

        assert result["status"] == "COMPLETE"
        assert ctrl.metrics.error_count >= 1

    def test_corrupted_yaml_archived(self, temp_queue):
        """Corrupted YAML in incoming/ is archived, not left in queue."""
        incoming = temp_queue / "default" / "incoming"
        incoming.mkdir(parents=True, exist_ok=True)
        corrupt_file = incoming / "DELEGATE-corrupt.yaml"
        corrupt_file.write_text(": invalid: yaml: {{{{")

        qm = QueueManager(queue_dir=str(temp_queue))
        orch = OrchestratorAgent.__new__(OrchestratorAgent)
        orch.queue_manager = qm
        orch.task_state = {}
        orch.tasks_processed = 0
        orch.tasks_success = 0
        orch.tasks_escalated = 0

        # _process_task should catch the error and archive
        with patch.object(orch, "queue_manager") as mock_qm:
            mock_qm.list_incoming_tasks.return_value = ["DELEGATE-corrupt.yaml"]
            mock_qm.read_task.side_effect = Exception("YAML parse error")
            mock_qm.archive_task.return_value = "/tmp/archive/DELEGATE-corrupt.yaml"
            orch._process_task = OrchestratorAgent._process_task.__get__(orch)

            # Patch quality_validator and task_router to avoid full init
            orch.quality_validator = Mock()
            orch.task_router = Mock()
            orch.orchestrator_cli = Mock()
            orch.orchestrator_cli.should_block_new_tasks.return_value = False

            orch._process_task("DELEGATE-corrupt.yaml")

        mock_qm.archive_task.assert_called_once_with("DELEGATE-corrupt.yaml")

    def test_move_to_failed_nonexistent_task(self, temp_queue):
        """move_to_failed raises FileNotFoundError for missing task."""
        qm = ExtendedQueueManager(queue_dir=str(temp_queue))
        with pytest.raises(FileNotFoundError):
            qm.move_to_failed("nonexistent-task", reason="test")

    def test_recover_failed_nonexistent_task(self, temp_queue):
        """recover_failed_task raises FileNotFoundError for missing task."""
        qm = ExtendedQueueManager(queue_dir=str(temp_queue))
        with pytest.raises(FileNotFoundError):
            qm.recover_failed_task("nonexistent-task")

    def test_invalid_from_state_for_failed(self, temp_queue, sample_delegate):
        """move_to_failed raises ValueError for invalid from_state."""
        qm = ExtendedQueueManager(queue_dir=str(temp_queue))
        write_delegate_to_qm(qm, "DELEGATE-2026-05-17-test-task.yaml", sample_delegate)
        with pytest.raises(ValueError, match="Invalid from_state"):
            qm.move_to_failed("2026-05-17-test-task", reason="test", from_state="done")


# ─── 6. Backwards Compatibility ──────────────────────────────────────────────


class TestBackwardsCompatibility:
    """Ensure existing API is not broken."""

    def test_queue_manager_move_to_processing_still_works(self, temp_queue, sample_delegate):
        """Legacy move_to_processing() method still works."""
        qm = QueueManager(queue_dir=str(temp_queue))
        write_delegate_to_qm(qm, "DELEGATE-test.yaml", sample_delegate)
        result = qm.move_to_processing("DELEGATE-test.yaml")
        assert result is not None
        assert (qm.processing_dir / "DELEGATE-test.yaml").exists()

    def test_queue_manager_move_to_done_still_works(self, temp_queue, sample_delegate, sample_handback):
        """Legacy move_to_done() method still works."""
        qm = QueueManager(queue_dir=str(temp_queue))
        write_delegate_to_qm(qm, "DELEGATE-test.yaml", sample_delegate)
        qm.move_to_processing("DELEGATE-test.yaml")
        result = qm.move_to_done("DELEGATE-test.yaml", sample_handback)
        assert result is not None

    def test_queue_manager_list_incoming_tasks(self, temp_queue, sample_delegate):
        """list_incoming_tasks() returns correct filenames."""
        qm = QueueManager(queue_dir=str(temp_queue))
        write_delegate_to_qm(qm, "DELEGATE-test.yaml", sample_delegate)
        tasks = qm.list_incoming_tasks()
        assert "DELEGATE-test.yaml" in tasks

    def test_queue_manager_read_task(self, temp_queue, sample_delegate):
        """read_task() parses DELEGATE YAML correctly."""
        qm = QueueManager(queue_dir=str(temp_queue))
        write_delegate_to_qm(qm, "DELEGATE-test.yaml", sample_delegate)
        data = qm.read_task("DELEGATE-test.yaml")
        assert data["task_id"] == "2026-05-17-test-task"
        assert data["role"] == "engineer"

    def test_run_poll_cycle_returns_metrics(self, temp_queue):
        """run_poll_cycle() returns dict with expected keys."""
        qm = QueueManager(queue_dir=str(temp_queue))
        with patch.object(qm, "list_incoming_tasks", return_value=[]):
            orch = OrchestratorAgent.__new__(OrchestratorAgent)
            orch.queue_manager = qm
            orch.task_state = {}
            orch.tasks_processed = 0
            orch.tasks_success = 0
            orch.tasks_escalated = 0
            orch.last_task_time = time.time()
            orch.token_tracker = Mock()
            orch.token_tracker.get_stats.return_value = Mock(
                total_input_tokens=0,
                total_output_tokens=0,
                total_cached_tokens=0,
                total_cost_usd=0.0,
            )
            result = orch.run_poll_cycle()

        assert "tasks_processed" in result
        assert "tasks_success" in result
        assert "tasks_escalated" in result
        assert "tokens" in result

    def test_automation_metrics_record_cycle(self):
        """AutomationMetrics.record_cycle() accumulates correctly."""
        metrics = AutomationMetrics()
        cycle_result = {"tasks_processed": 2, "tasks_success": 2, "tasks_escalated": 0, "tasks_failed": 0}
        metrics.record_cycle(1.5, cycle_result)
        assert metrics.cycles_completed == 1
        assert metrics.tasks_processed == 2
        assert metrics.tasks_success == 2

    def test_extended_queue_manager_inherits_base(self, temp_queue):
        """ExtendedQueueManager inherits all QueueManager methods."""
        qm = ExtendedQueueManager(queue_dir=str(temp_queue))
        assert hasattr(qm, "move_task")
        assert hasattr(qm, "list_incoming_tasks")
        assert hasattr(qm, "read_task")
        assert hasattr(qm, "move_to_processing")
        assert hasattr(qm, "move_to_done")
        # New methods
        assert hasattr(qm, "move_to_failed")
        assert hasattr(qm, "list_failed_tasks")
        assert hasattr(qm, "recover_failed_task")


# ─── 7. Metrics Collection ────────────────────────────────────────────────────


class TestMetricsCollection:
    """Test metrics are collected and reported correctly."""

    def test_metrics_finalize(self):
        """AutomationMetrics.finalize() sets end_time and duration."""
        metrics = AutomationMetrics()
        time.sleep(0.01)
        metrics.finalize()
        assert metrics.end_time is not None
        assert metrics.total_duration_seconds > 0

    def test_metrics_to_dict(self):
        """AutomationMetrics.to_dict() returns serializable dict."""
        metrics = AutomationMetrics()
        metrics.record_cycle(1.0, {"tasks_processed": 1, "tasks_success": 1, "tasks_escalated": 0, "tasks_failed": 0})
        metrics.finalize()
        d = metrics.to_dict()
        assert d["cycles_completed"] == 1
        assert d["tasks_processed"] == 1
        assert "start_time" in d

    def test_collect_metrics_from_handback(self, temp_queue):
        """collect_metrics() extracts canonical metrics from HANDBACK."""
        qm = QueueManager(queue_dir=str(temp_queue))
        orch = OrchestratorAgent.__new__(OrchestratorAgent)
        orch.queue_manager = qm
        orch.task_state = {}
        handback = {
            "task_id": "t1",
            "status": "complete",
            "quality_score": 92,
            "tokens_in": 1000,
            "tokens_out": 500,
            "effort_actual": 0.5,
        }
        delegate = {"role": "engineer", "model": "claude-sonnet-4-6", "effort": "medium"}
        metrics = orch.collect_metrics(handback, delegate)
        assert metrics["task_id"] == "t1"
        assert metrics["quality_score_validator"] == 92
        assert metrics["tokens_in"] == 1000
        assert metrics["tokens_out"] == 500
        assert metrics["total_tokens"] == 1500
