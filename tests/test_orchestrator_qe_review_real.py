"""
Test that the post-completion Quality Engineer review is REAL, not fabricated.

Background: OrchestratorAgent._process_task() used to hardcode a Quality
Engineer "review" — a constant dict with quality_score=90 and
decision="PROCEED" — every time a task was flagged for secondary review,
regardless of what actually triggered the review. This meant escalations
were always rubber-stamped approved.

The fix wires the escalation-review branch to the real
QualityEngineerProtocolIntegration (src/orchestration/agents/
quality_engineer_protocol_integration.py), grounded in the independently
computed Layer 3 quality_validator score rather than a constant or the
sub-agent's self-report.

Test Plan:
1. QE review is invoked (real evaluate_quality() runs) only for tasks that
   actually trigger escalation — not for every task.
2. The QE verdict reflects the real evaluation, not a hardcoded stamp: a low
   quality_score is discovered by the code (not returned unconditionally),
   and the score in quality_engineer_review matches what was fed in.
3. A failing QE evaluation (low quality) results in decision=ESCALATE and
   blocks the task from being counted as a success.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.orchestration.agents.orchestrator import OrchestratorAgent, QueueManager, TaskRouter
from src.orchestration.agents.quality_engineer_protocol_integration import (
    QualityEngineerProtocolIntegration,
)


class TestRealQualityEngineerReview:
    """Verify the post-completion QE gate uses real evaluation, not a stamp."""

    @pytest.fixture
    def mock_queue_manager(self):
        mock_qm = Mock(spec=QueueManager)
        mock_qm.move_task = Mock(return_value={
            "filename": "test-task.yaml",
            "audit_trail": [],
        })
        mock_qm.list_incoming_tasks = Mock(return_value=[])
        mock_qm.read_task = Mock(return_value={})
        mock_qm.incoming_dir = Path("/tmp/queue/incoming")
        mock_qm.processing_dir = Path("/tmp/queue/processing")
        mock_qm.done_dir = Path("/tmp/queue/done")
        mock_qm.failed_dir = Path("/tmp/queue/failed")
        return mock_qm

    @pytest.fixture
    def orchestrator(self, mock_queue_manager):
        """Real OrchestratorAgent with only I/O boundaries mocked.

        Crucially, `quality_engineer_integration` is left as the REAL
        instance created by OrchestratorAgent.__init__ — that's the thing
        under test.
        """
        with patch.object(QueueManager, "__init__", return_value=None):
            orch = OrchestratorAgent(queue_dir=None, agent_context=None)
            orch.queue_manager._agent = mock_queue_manager
            orch.task_router = Mock(spec=TaskRouter)
            orch.token_tracker = Mock()
            orch.orchestrator_cli = Mock()
            orch.has_children = Mock(return_value=False)
            return orch

    @staticmethod
    def _delegate(task_id="qe-real-task"):
        return {
            "task_id": task_id,
            "role": "engineer",
            "model": "claude-sonnet-4.6",
            "effort": "medium",
            "scope": "Implement a feature for the QE review test",
            "plan": ["Step 1"],
            "success_criteria": ["Works"],
        }

    @staticmethod
    def _handback(task_id="qe-real-task", status="success"):
        return {
            "task_id": task_id,
            "status": status,
            "notes": "Did the work.",
        }

    def _wire_pre_routing_validation(self, orch, quality_score=90):
        """Layer 1+2 pre-routing validation must let the task through."""
        orch.quality_validator.validate_delegate = Mock(
            return_value=Mock(
                routing_decision=Mock(value="high"),
                quality_score=quality_score,
                findings=[],
            )
        )
        orch.quality_validator.summary = Mock(return_value="OK")

    def _run(self, orch, mock_queue_manager, delegate, handback, handback_quality_score):
        """Drive _process_task() through the real escalation-review branch."""
        mock_agent = Mock()
        mock_agent.execute = Mock(return_value=handback)
        orch.task_router.route_task = Mock(return_value=("engineer", mock_agent))

        self._wire_pre_routing_validation(orch)

        # Layer 3 (post-completion) validation is the real, independently
        # computed score fed into the QE evaluation — mocked here only
        # because we want deterministic control over the score being tested,
        # not because quality_engineer_integration itself is mocked.
        orch.quality_validator.validate_handback = Mock(
            return_value=Mock(
                quality_score=handback_quality_score,
                critical_findings=[],
                as_dict=lambda: {},
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_queue_manager.incoming_dir = Path(tmpdir)
            with patch.object(orch.queue_manager._agent, "read_task", return_value=delegate):
                with patch.object(
                    orch.queue_manager._agent,
                    "move_task",
                    return_value={"filename": "test-task.yaml", "audit_trail": []},
                ):
                    orch._process_task(f"{delegate['task_id']}.yaml")

        return handback

    # ── AC: QE review is invoked for appropriate tasks ──────────────────────

    def test_qe_review_invoked_when_escalation_triggered(self, orchestrator, mock_queue_manager):
        """A low post-completion quality score must trigger a REAL QE evaluation."""
        delegate = self._delegate("qe-low-score")
        handback = self._handback("qe-low-score")

        assert orchestrator.quality_engineer_integration.evaluations == []

        self._run(orchestrator, mock_queue_manager, delegate, handback, handback_quality_score=55)

        # The real QualityEngineerProtocolIntegration.evaluate_quality() ran
        # and recorded an evaluation — this is not possible with a hardcoded
        # stamp, which never touches the integration object at all.
        assert len(orchestrator.quality_engineer_integration.evaluations) == 1
        assert orchestrator.quality_engineer_integration.evaluations[0].task_id == "qe-low-score"

    def test_qe_review_not_invoked_when_no_escalation(self, orchestrator, mock_queue_manager):
        """A healthy task must not trigger the QE review branch at all."""
        delegate = self._delegate("qe-healthy-task")
        handback = self._handback("qe-healthy-task")

        self._run(orchestrator, mock_queue_manager, delegate, handback, handback_quality_score=95)

        assert orchestrator.quality_engineer_integration.evaluations == []
        assert "quality_engineer_review" not in handback

    # ── AC: QE verdict is used, not stamped ─────────────────────────────────

    def test_qe_verdict_reflects_real_score_not_hardcoded_90(self, orchestrator, mock_queue_manager):
        """The old code always wrote quality_score=90 into the QE review.

        Feed a Layer 3 score of 55 through the escalation-review branch and
        confirm quality_engineer_review carries THAT score, not a constant.
        """
        delegate = self._delegate("qe-score-passthrough")
        handback = self._handback("qe-score-passthrough")

        self._run(orchestrator, mock_queue_manager, delegate, handback, handback_quality_score=55)

        qe_review = handback["quality_engineer_review"]
        assert qe_review["quality_score"] == 55
        assert qe_review["quality_score"] != 90, (
            "quality_score must come from the real evaluation, not the old "
            "hardcoded stamp value"
        )
        assert qe_review["evaluator"] == "quality_engineer_protocol_integration"

    # ── AC: Failed QE review blocks approval ────────────────────────────────

    def test_failed_qe_review_blocks_approval(self, orchestrator, mock_queue_manager):
        """A low-quality HANDBACK must be ESCALATEd, not rubber-stamped PROCEED."""
        delegate = self._delegate("qe-blocks-approval")
        handback = self._handback("qe-blocks-approval")

        tasks_success_before = orchestrator.tasks_success
        tasks_escalated_before = orchestrator.tasks_escalated

        self._run(orchestrator, mock_queue_manager, delegate, handback, handback_quality_score=40)

        qe_review = handback["quality_engineer_review"]
        assert qe_review["decision"] == "ESCALATE"
        assert qe_review["escalation_required"] is True

        # The escalation must actually count against success metrics — this
        # is what "blocks approval" means in the queue's audit trail.
        assert orchestrator.tasks_success == tasks_success_before
        assert orchestrator.tasks_escalated == tasks_escalated_before + 1

    def test_qe_evaluation_exception_fails_closed_to_escalate(self, orchestrator, mock_queue_manager):
        """If real evaluation blows up, that must never be treated as approval."""
        delegate = self._delegate("qe-eval-error")
        handback = self._handback("qe-eval-error")

        # Force the real evaluate_quality() to raise, simulating a broken
        # protocol schema or unexpected input.
        orchestrator.quality_engineer_integration.evaluate_quality = Mock(
            side_effect=RuntimeError("boom")
        )

        self._run(orchestrator, mock_queue_manager, delegate, handback, handback_quality_score=40)

        qe_review = handback["quality_engineer_review"]
        assert qe_review["decision"] == "ESCALATE"
        assert "error" in qe_review
