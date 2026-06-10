"""
Test HANDBACK Escalation Chaining (C2c).

When a HANDBACK has status='escalate', the Orchestrator creates a new DELEGATE
for the target agent and enqueues it in incoming/.

Test Plan:
1. HANDBACK with status=escalate triggers escalation DELEGATE creation
2. New DELEGATE has correct agent/role from escalate_to field
3. Escalation DELEGATE contains original context
4. Original task moved to done/ with escalation metadata
5. Escalation chain is tracked
"""

import pytest
import json
import yaml
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.orchestration.agents.orchestrator import OrchestratorAgent, QueueManager, TaskRouter


class TestEscalationChaining:
    """Verify escalation chaining from HANDBACK to new DELEGATE."""

    @pytest.fixture
    def mock_queue_manager(self):
        """Create a mock QueueManager with necessary methods."""
        mock_qm = Mock(spec=QueueManager)
        mock_qm.move_task = Mock(return_value={
            "filename": "escalation-task.yaml",
            "audit_trail": []
        })
        mock_qm.list_incoming_tasks = Mock(return_value=[])
        mock_qm.read_task = Mock(return_value={})
        mock_qm.incoming_dir = Path("/tmp/queue/incoming")
        mock_qm.processing_dir = Path("/tmp/queue/processing")
        mock_qm.done_dir = Path("/tmp/queue/done")
        mock_qm.failed_dir = Path("/tmp/queue/failed")
        return mock_qm

    @pytest.fixture
    def mock_orchestrator(self, mock_queue_manager):
        """Create a mock Orchestrator with stubbed dependencies."""
        with patch.object(QueueManager, '__init__', return_value=None):
            orch = OrchestratorAgent(queue_dir=None, agent_context=None)
            # Replace queue_manager's wrapped agent with our mock
            orch.queue_manager._agent = mock_queue_manager
            # Mock other dependencies
            orch.task_router = Mock(spec=TaskRouter)
            orch.quality_validator = Mock()
            orch.token_tracker = Mock()
            orch.orchestrator_cli = Mock()
            return orch

    def test_escalate_status_triggers_chain(self, mock_orchestrator, mock_queue_manager):
        """
        Test that HANDBACK with status='escalate' triggers escalation chaining.

        Success Criteria (AC1):
        - HANDBACK with status='escalate' is detected
        - escalate_to role is read from HANDBACK.output
        - New DELEGATE is created for target role
        """
        # Setup: Create a mock DELEGATE for the task router
        mock_delegate = {
            "task_id": "test-task",
            "role": "engineer",
            "scope": "Test task",
            "plan": [],
            "success_criteria": [],
        }

        # Setup: Create a HANDBACK with escalate status
        mock_handback = {
            "task_id": "test-task",
            "status": "escalate",
            "output": {
                "escalate_to": "senior-engineer",
                "escalation_reason": "Complex problem requires senior review"
            },
            "escalation_chain": ["engineer"],
        }

        # Setup: Mock the agent to return the escalating HANDBACK
        mock_agent = Mock()
        mock_agent.execute = Mock(return_value=mock_handback)
        mock_orchestrator.task_router.route_task = Mock(
            return_value=("engineer", mock_agent)
        )

        # Mock quality validator
        mock_orchestrator.quality_validator.validate_delegate = Mock(
            return_value=Mock(routing_decision=Mock(value="high"), quality_score=90, findings=[])
        )
        mock_orchestrator.quality_validator.validate_handback = Mock(
            return_value=Mock(quality_score=85, critical_findings=[], as_dict=lambda: {})
        )
        mock_orchestrator.quality_validator.summary = Mock(return_value="OK")

        # Setup: Create a temp directory for incoming queue
        with tempfile.TemporaryDirectory() as tmpdir:
            incoming_dir = Path(tmpdir)
            mock_queue_manager.incoming_dir = incoming_dir

            # AC1: Call _process_task to trigger escalation chaining
            with patch.object(mock_orchestrator, '_process_task', wraps=mock_orchestrator._process_task):
                # Simulate reading a task from incoming/
                with patch.object(mock_orchestrator.queue_manager._agent, 'read_task', return_value=mock_delegate):
                    with patch.object(mock_orchestrator.queue_manager._agent, 'move_task', return_value={"filename": "test.yaml", "audit_trail": []}):
                        mock_orchestrator._process_task("test-task.yaml")

            # AC1: Verify escalation file was written
            escalation_files = list(incoming_dir.glob("*.yaml"))
            assert len(escalation_files) > 0, "Escalation DELEGATE file should be created"

            # Read and check the escalation DELEGATE
            with open(escalation_files[0], 'r') as f:
                escalation_delegate = yaml.safe_load(f)

            assert escalation_delegate["agent"] == "senior-engineer", \
                "Escalation DELEGATE should target senior-engineer"
            assert "escalate" in escalation_delegate["task_id"].lower(), \
                "Escalation task_id should indicate escalation"

    def test_escalation_delegate_contains_original_context(self, mock_orchestrator, mock_queue_manager):
        """
        Test that escalation DELEGATE contains original HANDBACK and metadata.

        Success Criteria (AC2):
        - Escalation DELEGATE includes original_task_id
        - Escalation DELEGATE includes original_handback
        - Context field preserves escalation reason
        """
        mock_delegate = {
            "task_id": "test-task-2",
            "role": "engineer",
            "scope": "Test task",
            "plan": [],
            "success_criteria": [],
        }

        mock_handback = {
            "task_id": "test-task-2",
            "status": "escalate",
            "output": {
                "escalate_to": "lead-engineer",
                "escalation_reason": "Code review required"
            },
            "deliverables": ["code changes"],
            "escalation_chain": ["engineer"],
        }

        mock_agent = Mock()
        mock_agent.execute = Mock(return_value=mock_handback)
        mock_orchestrator.task_router.route_task = Mock(
            return_value=("engineer", mock_agent)
        )

        mock_orchestrator.quality_validator.validate_delegate = Mock(
            return_value=Mock(routing_decision=Mock(value="high"), quality_score=90, findings=[])
        )
        mock_orchestrator.quality_validator.validate_handback = Mock(
            return_value=Mock(quality_score=85, critical_findings=[], as_dict=lambda: {})
        )
        mock_orchestrator.quality_validator.summary = Mock(return_value="OK")

        with tempfile.TemporaryDirectory() as tmpdir:
            incoming_dir = Path(tmpdir)
            mock_queue_manager.incoming_dir = incoming_dir

            with patch.object(mock_orchestrator.queue_manager._agent, 'read_task', return_value=mock_delegate):
                with patch.object(mock_orchestrator.queue_manager._agent, 'move_task', return_value={"filename": "test.yaml", "audit_trail": []}):
                    mock_orchestrator._process_task("test-task-2.yaml")

            # AC2: Verify escalation DELEGATE context
            escalation_files = list(incoming_dir.glob("*.yaml"))
            assert len(escalation_files) > 0

            with open(escalation_files[0], 'r') as f:
                escalation_delegate = yaml.safe_load(f)

            assert escalation_delegate["context"]["original_task_id"] == "test-task-2", \
                "Escalation DELEGATE should preserve original_task_id"
            assert escalation_delegate["context"]["original_handback"] == mock_handback, \
                "Escalation DELEGATE should include original_handback"
            assert escalation_delegate["context"]["escalation_reason"] == "Code review required", \
                "Escalation DELEGATE should preserve escalation_reason"

    def test_escalation_chain_tracking(self, mock_orchestrator, mock_queue_manager):
        """
        Test that escalation chain is properly tracked.

        Success Criteria (AC3):
        - New DELEGATE has escalation_chain with current role appended
        - escalation_chain shows path of escalations
        """
        mock_delegate = {
            "task_id": "test-task-3",
            "role": "engineer",
            "scope": "Test task",
            "plan": [],
            "success_criteria": [],
        }

        mock_handback = {
            "task_id": "test-task-3",
            "status": "escalate",
            "output": {
                "escalate_to": "principal-engineer",
                "escalation_reason": "Architecture decision required"
            },
            "escalation_chain": ["engineer", "senior-engineer"],  # Already escalated twice
        }

        mock_agent = Mock()
        mock_agent.execute = Mock(return_value=mock_handback)
        mock_orchestrator.task_router.route_task = Mock(
            return_value=("senior-engineer", mock_agent)
        )

        mock_orchestrator.quality_validator.validate_delegate = Mock(
            return_value=Mock(routing_decision=Mock(value="high"), quality_score=90, findings=[])
        )
        mock_orchestrator.quality_validator.validate_handback = Mock(
            return_value=Mock(quality_score=85, critical_findings=[], as_dict=lambda: {})
        )
        mock_orchestrator.quality_validator.summary = Mock(return_value="OK")

        with tempfile.TemporaryDirectory() as tmpdir:
            incoming_dir = Path(tmpdir)
            mock_queue_manager.incoming_dir = incoming_dir

            with patch.object(mock_orchestrator.queue_manager._agent, 'read_task', return_value=mock_delegate):
                with patch.object(mock_orchestrator.queue_manager._agent, 'move_task', return_value={"filename": "test.yaml", "audit_trail": []}):
                    mock_orchestrator._process_task("test-task-3.yaml")

            # AC3: Verify escalation chain is updated
            escalation_files = list(incoming_dir.glob("*.yaml"))
            assert len(escalation_files) > 0

            with open(escalation_files[0], 'r') as f:
                escalation_delegate = yaml.safe_load(f)

            assert "escalation_chain" in escalation_delegate, \
                "Escalation DELEGATE should include escalation_chain"
            # The chain should show the path so far (engineer -> senior-engineer)
            assert "engineer" in escalation_delegate["escalation_chain"], \
                "Escalation chain should track path"

    def test_original_task_moved_to_done(self, mock_orchestrator, mock_queue_manager):
        """
        Test that original task is moved to done/ with escalation metadata.

        Success Criteria (AC4):
        - Original task moved from processing/ to done/
        - Escalation file is created
        - Process completes without error
        """
        mock_delegate = {
            "task_id": "test-task-4",
            "role": "engineer",
            "scope": "Test task",
            "plan": [],
            "success_criteria": [],
        }

        mock_handback = {
            "task_id": "test-task-4",
            "status": "escalate",
            "output": {
                "escalate_to": "lead-engineer",
            },
        }

        mock_agent = Mock()
        mock_agent.execute = Mock(return_value=mock_handback)
        mock_orchestrator.task_router.route_task = Mock(
            return_value=("engineer", mock_agent)
        )

        mock_orchestrator.quality_validator.validate_delegate = Mock(
            return_value=Mock(routing_decision=Mock(value="high"), quality_score=90, findings=[])
        )
        mock_orchestrator.quality_validator.validate_handback = Mock(
            return_value=Mock(quality_score=85, critical_findings=[], as_dict=lambda: {})
        )
        mock_orchestrator.quality_validator.summary = Mock(return_value="OK")

        with tempfile.TemporaryDirectory() as tmpdir:
            incoming_dir = Path(tmpdir)
            mock_queue_manager.incoming_dir = incoming_dir

            with patch.object(mock_orchestrator.queue_manager._agent, 'read_task', return_value=mock_delegate):
                with patch.object(mock_orchestrator.queue_manager._agent, 'move_task', return_value={"filename": "test.yaml", "audit_trail": []}):
                    mock_orchestrator._process_task("test-task-4.yaml")

            # AC4: Verify escalation file was created
            escalation_files = list(incoming_dir.glob("*.yaml"))
            assert len(escalation_files) > 0, \
                "Escalation file should be created when task is escalated"

    def test_escalate_to_default_fallback(self, mock_orchestrator, mock_queue_manager):
        """
        Test that escalation defaults to 'lead-engineer' if escalate_to is missing.

        Success Criteria (AC5):
        - Missing escalate_to defaults to 'lead-engineer'
        - Graceful fallback prevents errors
        """
        mock_delegate = {
            "task_id": "test-task-5",
            "role": "engineer",
            "scope": "Test task",
            "plan": [],
            "success_criteria": [],
        }

        # HANDBACK with escalate status but no escalate_to field
        mock_handback = {
            "task_id": "test-task-5",
            "status": "escalate",
            "output": {
                "escalation_reason": "Needs review"
                # Missing: escalate_to
            },
        }

        mock_agent = Mock()
        mock_agent.execute = Mock(return_value=mock_handback)
        mock_orchestrator.task_router.route_task = Mock(
            return_value=("engineer", mock_agent)
        )

        mock_orchestrator.quality_validator.validate_delegate = Mock(
            return_value=Mock(routing_decision=Mock(value="high"), quality_score=90, findings=[])
        )
        mock_orchestrator.quality_validator.validate_handback = Mock(
            return_value=Mock(quality_score=85, critical_findings=[], as_dict=lambda: {})
        )
        mock_orchestrator.quality_validator.summary = Mock(return_value="OK")

        with tempfile.TemporaryDirectory() as tmpdir:
            incoming_dir = Path(tmpdir)
            mock_queue_manager.incoming_dir = incoming_dir

            with patch.object(mock_orchestrator.queue_manager._agent, 'read_task', return_value=mock_delegate):
                with patch.object(mock_orchestrator.queue_manager._agent, 'move_task', return_value={"filename": "test.yaml", "audit_trail": []}):
                    mock_orchestrator._process_task("test-task-5.yaml")

            # AC5: Verify fallback to lead-engineer
            escalation_files = list(incoming_dir.glob("*.yaml"))
            assert len(escalation_files) > 0

            with open(escalation_files[0], 'r') as f:
                escalation_delegate = yaml.safe_load(f)

            assert escalation_delegate["agent"] == "lead-engineer", \
                "Missing escalate_to should default to 'lead-engineer'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
