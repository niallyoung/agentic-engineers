"""
Integration tests for protocol schemas with Orchestrator.

Tests the full workflow:
DELEGATE → HANDBACK → Quality Evaluation → Feedback/Outcome → Optimization
"""

import pytest
from datetime import datetime
from src.orchestration.protocol.expanded_delegate import ExpandedDelegate
from src.orchestration.protocol.expanded_handback import ExpandedHandback
from src.orchestration.protocol.orchestrator_integration import (
    ExpandedDelegateHandler,
    ExpandedHandbackHandler,
    QualityEvaluationEngine,
    FeedbackLoopEngine,
    OptimizationEngine,
    ProtocolEventPublisher,
)
from src.orchestration.protocol.event_model import EventType


class TestExpandedDelegateHandler:
    """Test DELEGATE creation and management."""
    
    def test_create_delegate_minimal(self):
        """Test creating a minimal DELEGATE."""
        delegate = ExpandedDelegateHandler.create_delegate(
            task_id="2026-05-20-test-task",
            role="engineer",
            model="claude-sonnet-4.6",
            effort="medium",
            scope="Implement feature X with comprehensive testing and documentation",
            plan=["Step 1: Design", "Step 2: Implement", "Step 3: Test"],
        )
        
        assert delegate.task_id == "2026-05-20-test-task"
        assert delegate.role == "engineer"
        assert delegate.quality_baseline == 90
        assert len(delegate.plan) == 3
    
    def test_create_delegate_full(self):
        """Test creating a DELEGATE with all fields."""
        delegate = ExpandedDelegateHandler.create_delegate(
            task_id="2026-05-20-full-task",
            role="senior-engineer",
            model="claude-opus-4.7",
            effort="high",
            scope="Design and implement complex distributed system with fault tolerance",
            plan=[
                "Design architecture",
                "Implement core components",
                "Add fault tolerance",
                "Comprehensive testing",
                "Documentation",
            ],
            quality_baseline=95,
            acceptance_criteria=[
                "All tests pass",
                "Code coverage ≥90%",
                "Documentation complete",
            ],
            quality_thresholds={"test_coverage": 90, "regressions": 0},
            tags=["architecture", "distributed-systems"],
            priority="critical",
            dependencies=["2026-05-19-design-task"],
            estimated_tokens=50000,
            estimated_time_minutes=480,
            constraints=["Must use Python 3.7+", "No external dependencies"],
            feedback_required=True,
            feedback_topics=["architecture", "performance"],
            optimization_targets=["cost", "quality"],
            cost_target=5.0,
        )
        
        assert delegate.task_id == "2026-05-20-full-task"
        assert delegate.role == "senior-engineer"
        assert delegate.quality_baseline == 95
        assert len(delegate.acceptance_criteria) == 3
        assert delegate.priority == "critical"
        assert delegate.estimated_tokens == 50000
    
    def test_delegate_serialization(self):
        """Test DELEGATE serialization to/from dict."""
        original = ExpandedDelegateHandler.create_delegate(
            task_id="2026-05-20-serialize-test",
            role="engineer",
            model="claude-sonnet-4.6",
            effort="medium",
            scope="Test serialization with comprehensive testing and documentation",
            plan=["Step 1", "Step 2"],
            quality_baseline=90,
        )
        
        # Serialize
        data = ExpandedDelegateHandler.to_dict(original)
        assert data["task_id"] == "2026-05-20-serialize-test"
        assert data["quality_baseline"] == 90
        
        # Deserialize
        restored = ExpandedDelegateHandler.from_dict(data)
        assert restored.task_id == original.task_id
        assert restored.quality_baseline == original.quality_baseline
        assert restored.role == original.role


class TestExpandedHandbackHandler:
    """Test HANDBACK creation and management."""
    
    def test_create_handback_minimal(self):
        """Test creating a minimal HANDBACK."""
        handback = ExpandedHandbackHandler.create_handback(
            task_id="2026-05-20-test-task",
            status="success",
        )
        
        assert handback.task_id == "2026-05-20-test-task"
        assert handback.status == "success"
        assert handback.quality_score == 0
    
    def test_create_handback_full(self):
        """Test creating a HANDBACK with all metrics."""
        handback = ExpandedHandbackHandler.create_handback(
            task_id="2026-05-20-full-task",
            status="success",
            deliverables=["src/feature.py", "tests/test_feature.py", "docs/FEATURE.md"],
            tests={"unit_tests": True, "integration_tests": True, "e2e_tests": True},
            tokens_in=25000,
            tokens_out=15000,
            time_elapsed_minutes=120,
            cost_actual=0.85,
            model_used="claude-sonnet-4.6",
            quality_score=92,
            test_coverage=0.92,
            regressions_detected=0,
            acceptance_criteria_met=["All tests pass", "Code coverage ≥90%"],
            model_assessment="Sonnet performed well for this task",
            blockers=[],
            recommendations=["Consider adding performance tests"],
            success_rate=1.0,
            quality_trend="improved",
            cost_trend="under_budget",
            effort_actual="medium",
            notes="Task completed successfully with high quality",
        )
        
        assert handback.task_id == "2026-05-20-full-task"
        assert handback.status == "success"
        assert handback.quality_score == 92
        assert handback.test_coverage == 0.92
        assert len(handback.deliverables) == 3
    
    def test_handback_serialization(self):
        """Test HANDBACK serialization to/from dict."""
        original = ExpandedHandbackHandler.create_handback(
            task_id="2026-05-20-serialize-test",
            status="success",
            quality_score=90,
            test_coverage=0.85,
        )
        
        # Serialize
        data = ExpandedHandbackHandler.to_dict(original)
        assert data["task_id"] == "2026-05-20-serialize-test"
        assert data["quality_score"] == 90
        
        # Deserialize
        restored = ExpandedHandbackHandler.from_dict(data)
        assert restored.task_id == original.task_id
        assert restored.quality_score == original.quality_score


class TestQualityEvaluationEngine:
    """Test quality evaluation workflow."""
    
    def test_evaluate_exceeds_baseline(self):
        """Test evaluation when quality exceeds baseline."""
        delegate = ExpandedDelegateHandler.create_delegate(
            task_id="2026-05-20-quality-test",
            role="engineer",
            model="claude-sonnet-4.6",
            effort="medium",
            scope="Implement feature with comprehensive testing and documentation",
            plan=["Design", "Implement", "Test"],
            quality_baseline=90,
            acceptance_criteria=["All tests pass", "Code coverage ≥90%"],
        )
        
        handback = ExpandedHandbackHandler.create_handback(
            task_id="2026-05-20-quality-test",
            status="success",
            quality_score=95,
            test_coverage=0.95,
            regressions_detected=0,
            acceptance_criteria_met=["All tests pass", "Code coverage ≥90%"],
        )
        
        evaluation = QualityEvaluationEngine.evaluate(delegate, handback)
        
        assert evaluation.quality_achieved == 95
        assert evaluation.quality_baseline == 90
        assert evaluation.quality_score == 95
        assert evaluation.acceptance_criteria_assessment["All tests pass"] == "met"
        assert not evaluation.escalation_required
    
    def test_evaluate_meets_baseline(self):
        """Test evaluation when quality meets baseline."""
        delegate = ExpandedDelegateHandler.create_delegate(
            task_id="2026-05-20-meets-test",
            role="engineer",
            model="claude-sonnet-4.6",
            effort="medium",
            scope="Implement feature with comprehensive testing and documentation",
            plan=["Design", "Implement", "Test"],
            quality_baseline=90,
            acceptance_criteria=["All tests pass"],
        )
        
        handback = ExpandedHandbackHandler.create_handback(
            task_id="2026-05-20-meets-test",
            status="success",
            quality_score=88,
            test_coverage=0.88,
            regressions_detected=0,
            acceptance_criteria_met=["All tests pass"],
        )
        
        evaluation = QualityEvaluationEngine.evaluate(delegate, handback)
        
        assert evaluation.quality_achieved == 88
        assert evaluation.acceptance_criteria_assessment["All tests pass"] == "met"
        assert not evaluation.escalation_required
    
    def test_evaluate_below_baseline(self):
        """Test evaluation when quality is below baseline."""
        delegate = ExpandedDelegateHandler.create_delegate(
            task_id="2026-05-20-below-test",
            role="engineer",
            model="claude-sonnet-4.6",
            effort="medium",
            scope="Implement feature with comprehensive testing and documentation",
            plan=["Design", "Implement", "Test"],
            quality_baseline=90,
            acceptance_criteria=["All tests pass", "Code coverage ≥90%"],
        )
        
        handback = ExpandedHandbackHandler.create_handback(
            task_id="2026-05-20-below-test",
            status="success",
            quality_score=75,
            test_coverage=0.75,
            regressions_detected=2,
            acceptance_criteria_met=["All tests pass"],
        )
        
        evaluation = QualityEvaluationEngine.evaluate(delegate, handback)
        
        assert evaluation.quality_achieved == 75
        assert evaluation.acceptance_criteria_assessment["Code coverage ≥90%"] == "not_met"
        assert evaluation.escalation_required
        # Escalation reason is set to the first issue found (regressions in this case)
        assert evaluation.escalation_reason in ["Regressions detected: 2", "Quality below baseline: 75 < 90"]


class TestFeedbackLoopEngine:
    """Test feedback loop workflow."""
    
    def test_create_feedback_success(self):
        """Test creating feedback for successful task."""
        delegate = ExpandedDelegateHandler.create_delegate(
            task_id="2026-05-20-feedback-test",
            role="engineer",
            model="claude-sonnet-4.6",
            effort="medium",
            scope="Implement feature with comprehensive testing and documentation",
            plan=["Design", "Implement", "Test"],
            quality_baseline=90,
            cost_target=1.0,
        )
        
        handback = ExpandedHandbackHandler.create_handback(
            task_id="2026-05-20-feedback-test",
            status="success",
            quality_score=92,
            cost_actual=0.85,
        )
        
        evaluation = QualityEvaluationEngine.evaluate(delegate, handback)
        feedback = FeedbackLoopEngine.create_feedback(handback, delegate, evaluation)
        
        assert feedback.outcome == "success"
        assert feedback.quality_assessment == "exceeds"
        assert feedback.cost_assessment == "under"
        assert feedback.routing_recommendation == "engineer"
    
    def test_create_feedback_partial(self):
        """Test creating feedback for partial success."""
        delegate = ExpandedDelegateHandler.create_delegate(
            task_id="2026-05-20-partial-test",
            role="engineer",
            model="claude-sonnet-4.6",
            effort="medium",
            scope="Implement feature with comprehensive testing and documentation",
            plan=["Design", "Implement", "Test"],
            quality_baseline=90,
            cost_target=1.0,
        )
        
        handback = ExpandedHandbackHandler.create_handback(
            task_id="2026-05-20-partial-test",
            status="success",
            quality_score=75,
            cost_actual=1.2,
        )
        
        evaluation = QualityEvaluationEngine.evaluate(delegate, handback)
        feedback = FeedbackLoopEngine.create_feedback(handback, delegate, evaluation)
        
        assert feedback.outcome == "partial"
        assert feedback.quality_assessment == "below"
        assert feedback.cost_assessment == "over"
    
    def test_create_feedback_with_trends(self):
        """Test creating feedback with historical trend data."""
        delegate = ExpandedDelegateHandler.create_delegate(
            task_id="2026-05-20-trend-test",
            role="engineer",
            model="claude-sonnet-4.6",
            effort="medium",
            scope="Implement feature with comprehensive testing and documentation",
            plan=["Design", "Implement", "Test"],
            quality_baseline=90,
            cost_target=1.0,
        )
        
        handback = ExpandedHandbackHandler.create_handback(
            task_id="2026-05-20-trend-test",
            status="success",
            quality_score=92,
            cost_actual=0.85,
        )
        
        evaluation = QualityEvaluationEngine.evaluate(delegate, handback)
        
        # Create historical outcomes
        historical = [
            {
                "task_id": "2026-05-19-task-1",
                "quality_score": 88,
                "cost_actual": 0.90,
                "outcome": "success",
                "timestamp": datetime.now().isoformat(),
            },
            {
                "task_id": "2026-05-19-task-2",
                "quality_score": 91,
                "cost_actual": 0.95,
                "outcome": "success",
                "timestamp": datetime.now().isoformat(),
            },
        ]
        
        feedback = FeedbackLoopEngine.create_feedback(
            handback, delegate, evaluation, historical_outcomes=historical
        )
        
        assert feedback.trend_7day is not None
        assert feedback.trend_7day["avg_quality"] > 0


class TestOptimizationEngine:
    """Test optimization analysis workflow."""
    
    def test_analyze_cost_optimization(self):
        """Test identifying cost optimization opportunities."""
        delegate = ExpandedDelegateHandler.create_delegate(
            task_id="2026-05-20-cost-opt-test",
            role="engineer",
            model="claude-opus-4.7",
            effort="high",
            scope="Implement complex feature with comprehensive testing and documentation",
            plan=["Design", "Implement", "Test"],
            quality_baseline=90,
            cost_target=5.0,
        )
        
        handback = ExpandedHandbackHandler.create_handback(
            task_id="2026-05-20-cost-opt-test",
            status="success",
            quality_score=92,
            cost_actual=3.5,
        )
        
        evaluation = QualityEvaluationEngine.evaluate(delegate, handback)
        feedback = FeedbackLoopEngine.create_feedback(handback, delegate, evaluation)
        optimization = OptimizationEngine.analyze(delegate, handback, feedback)
        
        assert optimization.cost_opportunities is not None
        assert len(optimization.cost_opportunities) > 0
        assert optimization.primary_recommendation is not None
    
    def test_analyze_quality_optimization(self):
        """Test identifying quality optimization opportunities."""
        delegate = ExpandedDelegateHandler.create_delegate(
            task_id="2026-05-20-quality-opt-test",
            role="engineer",
            model="claude-haiku-4.5",
            effort="low",
            scope="Implement simple feature with basic testing and documentation",
            plan=["Implement", "Test"],
            quality_baseline=85,
            cost_target=0.5,
        )
        
        handback = ExpandedHandbackHandler.create_handback(
            task_id="2026-05-20-quality-opt-test",
            status="success",
            quality_score=78,
            test_coverage=0.75,
            cost_actual=0.3,
        )
        
        evaluation = QualityEvaluationEngine.evaluate(delegate, handback)
        feedback = FeedbackLoopEngine.create_feedback(handback, delegate, evaluation)
        optimization = OptimizationEngine.analyze(delegate, handback, feedback)
        
        assert optimization.quality_opportunities is not None
        assert len(optimization.quality_opportunities) > 0


class TestProtocolEventPublisher:
    """Test event publishing for task lifecycle."""
    
    def test_publish_delegate_created_event(self):
        """Test publishing delegate.created event."""
        publisher = ProtocolEventPublisher()
        
        event = publisher.publish_event(
            event_type=EventType.DELEGATE_CREATED,
            task_id="2026-05-20-event-test",
            actor="orchestrator",
            actor_role="orchestrator",
            data={"role": "engineer", "model": "claude-sonnet-4.6"},
            tags=["protocol", "delegate"],
        )
        
        assert event.event_type == EventType.DELEGATE_CREATED
        assert event.task_id == "2026-05-20-event-test"
        assert event.actor == "orchestrator"
    
    def test_publish_execution_events(self):
        """Test publishing execution lifecycle events."""
        publisher = ProtocolEventPublisher()
        task_id = "2026-05-20-execution-test"
        
        # Publish execution.started
        start_event = publisher.publish_event(
            event_type=EventType.EXECUTION_STARTED,
            task_id=task_id,
            actor="engineer",
            actor_role="engineer",
            data={"model": "claude-sonnet-4.6"},
        )
        
        # Publish execution.completed
        complete_event = publisher.publish_event(
            event_type=EventType.EXECUTION_COMPLETED,
            task_id=task_id,
            actor="engineer",
            actor_role="engineer",
            data={"quality_score": 92},
        )
        
        # Get all events for task
        events = publisher.get_events(task_id)
        assert len(events) == 2
        assert events[0].event_type == EventType.EXECUTION_STARTED
        assert events[1].event_type == EventType.EXECUTION_COMPLETED
    
    def test_publish_quality_evaluation_event(self):
        """Test publishing quality.evaluated event."""
        publisher = ProtocolEventPublisher()
        
        event = publisher.publish_event(
            event_type=EventType.QUALITY_EVALUATED,
            task_id="2026-05-20-quality-event-test",
            actor="quality_engineer",
            actor_role="quality_engineer",
            data={"quality_score": 92, "assessment": "exceeds"},
            priority="high",
        )
        
        assert event.event_type == EventType.QUALITY_EVALUATED
        assert event.priority == "high"


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow."""
    
    def test_full_workflow_success(self):
        """Test complete workflow from DELEGATE to Optimization."""
        # Step 1: Create DELEGATE
        delegate = ExpandedDelegateHandler.create_delegate(
            task_id="2026-05-20-e2e-test",
            role="engineer",
            model="claude-sonnet-4.6",
            effort="medium",
            scope="Implement feature with comprehensive testing and documentation",
            plan=["Design", "Implement", "Test"],
            quality_baseline=90,
            cost_target=1.0,
            acceptance_criteria=["All tests pass", "Code coverage ≥90%"],
        )
        
        # Step 2: Create HANDBACK
        handback = ExpandedHandbackHandler.create_handback(
            task_id="2026-05-20-e2e-test",
            status="success",
            quality_score=92,
            test_coverage=0.92,
            cost_actual=0.85,
            acceptance_criteria_met=["All tests pass", "Code coverage ≥90%"],
        )
        
        # Step 3: Quality Evaluation
        evaluation = QualityEvaluationEngine.evaluate(delegate, handback)
        assert evaluation.quality_score == 92
        assert not evaluation.escalation_required
        
        # Step 4: Feedback Loop
        feedback = FeedbackLoopEngine.create_feedback(handback, delegate, evaluation)
        assert feedback.outcome == "success"
        assert feedback.quality_assessment == "exceeds"
        
        # Step 5: Optimization
        optimization = OptimizationEngine.analyze(delegate, handback, feedback)
        assert optimization.primary_recommendation is not None
        
        # Step 6: Event Publishing
        publisher = ProtocolEventPublisher()
        publisher.publish_event(
            event_type=EventType.DELEGATE_CREATED,
            task_id="2026-05-20-e2e-test",
            actor="orchestrator",
            actor_role="orchestrator",
        )
        publisher.publish_event(
            event_type=EventType.EXECUTION_COMPLETED,
            task_id="2026-05-20-e2e-test",
            actor="engineer",
            actor_role="engineer",
        )
        publisher.publish_event(
            event_type=EventType.QUALITY_EVALUATED,
            task_id="2026-05-20-e2e-test",
            actor="quality_engineer",
            actor_role="quality_engineer",
        )
        
        events = publisher.get_events("2026-05-20-e2e-test")
        assert len(events) == 3
