"""
Tests for expanded protocol schemas.
"""

import pytest
from datetime import datetime
from src.orchestration.protocol.expanded_delegate import ExpandedDelegate
from src.orchestration.protocol.expanded_handback import ExpandedHandback
from src.orchestration.protocol.quality_evaluation import QualityEvaluation
from src.orchestration.protocol.feedback_outcome import FeedbackOutcome
from src.orchestration.protocol.optimization import Optimization, CostOpportunity, QualityOpportunity
from src.orchestration.protocol.event_model import Event, EventType
from src.orchestration.protocol.artifact_linking import ArtifactLink, ArtifactLinkage
from src.orchestration.protocol.validation import validate_delegate, validate_handback


class TestExpandedDelegate:
    """Tests for ExpandedDelegate schema."""
    
    def test_create_delegate(self):
        """Test creating a DELEGATE."""
        delegate = ExpandedDelegate(
            task_id="2026-05-17-test-task",
            role="engineer",
            model="claude-haiku-4-5",
            effort="high",
            scope="This is a test task that should have at least fifteen words in the scope description for validation purposes.",
            plan=["Step 1", "Step 2", "Step 3"],
            quality_baseline=90,
        )
        
        assert delegate.task_id == "2026-05-17-test-task"
        assert delegate.role == "engineer"
        assert delegate.quality_baseline == 90
    
    def test_delegate_validation(self):
        """Test DELEGATE validation."""
        delegate = ExpandedDelegate(
            task_id="test",  # Too short
            role="invalid-role",
            model="claude-haiku-4-5",
            effort="high",
            scope="Short scope",  # Too short
            plan=[],  # Empty plan
        )
        
        errors = delegate.validate()
        assert len(errors) > 0
        assert any("task_id" in e for e in errors)
        assert any("role" in e for e in errors)
        assert any("scope" in e for e in errors)
        assert any("plan" in e for e in errors)
    
    def test_delegate_to_dict(self):
        """Test DELEGATE serialization."""
        delegate = ExpandedDelegate(
            task_id="2026-05-17-test-task",
            role="engineer",
            model="claude-haiku-4-5",
            effort="high",
            scope="This is a test task that should have at least fifteen words in the scope description for validation purposes.",
            plan=["Step 1", "Step 2"],
        )
        
        data = delegate.to_dict()
        assert data["task_id"] == "2026-05-17-test-task"
        assert data["role"] == "engineer"
        assert len(data) >= 20  # Should have 20+ fields
    
    def test_delegate_from_dict(self):
        """Test DELEGATE deserialization."""
        data = {
            "task_id": "2026-05-17-test-task",
            "role": "engineer",
            "model": "claude-haiku-4-5",
            "effort": "high",
            "scope": "This is a test task that should have at least fifteen words in the scope description for validation purposes.",
            "plan": ["Step 1", "Step 2"],
            "quality_baseline": 85,
        }
        
        delegate = ExpandedDelegate.from_dict(data)
        assert delegate.task_id == "2026-05-17-test-task"
        assert delegate.quality_baseline == 85


class TestExpandedHandback:
    """Tests for ExpandedHandback schema."""
    
    def test_create_handback(self):
        """Test creating a HANDBACK."""
        handback = ExpandedHandback(
            task_id="2026-05-17-test-task",
            status="complete",
            deliverables=["file1.py", "file2.py"],
            tests={"test_1": True, "test_2": True},
            quality_score=92,
        )
        
        assert handback.task_id == "2026-05-17-test-task"
        assert handback.status == "complete"
        assert handback.quality_score == 92
    
    def test_handback_validation(self):
        """Test HANDBACK validation."""
        handback = ExpandedHandback(
            task_id="",  # Empty
            status="invalid",  # Invalid status
            deliverables=[],
            tests={},
            quality_score=150,  # Out of range
        )
        
        errors = handback.validate()
        assert len(errors) > 0
        assert any("task_id" in e for e in errors)
        assert any("status" in e for e in errors)
        assert any("quality_score" in e for e in errors)
    
    def test_handback_to_dict(self):
        """Test HANDBACK serialization."""
        handback = ExpandedHandback(
            task_id="2026-05-17-test-task",
            status="complete",
            deliverables=["file1.py"],
            tests={"test_1": True},
            quality_score=90,
        )
        
        data = handback.to_dict()
        assert data["task_id"] == "2026-05-17-test-task"
        assert data["status"] == "complete"
        assert len(data) >= 25  # Should have 25+ fields


class TestQualityEvaluation:
    """Tests for QualityEvaluation schema."""
    
    def test_create_quality_evaluation(self):
        """Test creating a Quality Evaluation."""
        qe = QualityEvaluation(
            task_id="2026-05-17-qe-001",
            delegate_task_id="2026-05-17-test-task",
            handback_task_id="2026-05-17-test-task",
            quality_baseline=90,
            quality_achieved=92,
        )
        
        assert qe.task_id == "2026-05-17-qe-001"
        assert qe.quality_baseline == 90
    
    def test_quality_evaluation_compute_score(self):
        """Test quality score computation."""
        qe = QualityEvaluation(
            task_id="2026-05-17-qe-001",
            delegate_task_id="2026-05-17-test-task",
            handback_task_id="2026-05-17-test-task",
            quality_baseline=90,
            quality_achieved=92,
            evaluation_results={"test_1": True, "test_2": True, "test_3": False},
            acceptance_criteria_assessment={"criterion_1": True, "criterion_2": True},
        )
        
        score = qe.compute_quality_score()
        assert 0 <= score <= 100
        assert score > 0  # Should be positive since most tests passed


class TestFeedbackOutcome:
    """Tests for FeedbackOutcome schema."""
    
    def test_create_feedback_outcome(self):
        """Test creating Feedback/Outcome."""
        fo = FeedbackOutcome(
            task_id="2026-05-17-feedback-001",
            outcome="success",
            quality_baseline=90,
            quality_achieved=92,
            cost_budget=0.10,
            cost_actual=0.08,
        )
        
        assert fo.task_id == "2026-05-17-feedback-001"
        assert fo.outcome == "success"
    
    def test_feedback_outcome_compute_assessments(self):
        """Test assessment computation."""
        fo = FeedbackOutcome(
            task_id="2026-05-17-feedback-001",
            outcome="success",
            quality_baseline=90,
            quality_achieved=92,
            cost_budget=0.10,
            cost_actual=0.08,
        )
        
        fo.compute_assessments()
        assert fo.quality_assessment == "exceeds"
        assert fo.cost_assessment == "under"


class TestOptimization:
    """Tests for Optimization schema."""
    
    def test_create_optimization(self):
        """Test creating Optimization."""
        opt = Optimization(
            task_id="2026-05-17-opt-001",
            historical_success_rate=0.95,
            historical_avg_quality=88.0,
            historical_avg_cost=0.09,
        )
        
        assert opt.task_id == "2026-05-17-opt-001"
        assert opt.historical_success_rate == 0.95
    
    def test_optimization_with_opportunities(self):
        """Test Optimization with cost/quality opportunities."""
        opt = Optimization(
            task_id="2026-05-17-opt-001",
            historical_success_rate=0.95,
            historical_avg_quality=88.0,
            historical_avg_cost=0.09,
        )
        
        # Add cost opportunity
        cost_opp = CostOpportunity(
            opportunity_type="model_downgrade",
            description="Use Haiku instead of Sonnet",
            estimated_savings=0.03,
            estimated_savings_percent=33.3,
            confidence=0.85,
            implementation_effort="low",
        )
        opt.cost_opportunities.append(cost_opp)
        
        assert len(opt.cost_opportunities) == 1
        assert opt.cost_opportunities[0].opportunity_type == "model_downgrade"


class TestEvent:
    """Tests for Event model."""
    
    def test_create_event(self):
        """Test creating an Event."""
        event = Event(
            event_id="evt-001",
            event_type=EventType.DELEGATE_CREATED,
            task_id="2026-05-17-test-task",
            actor="orchestrator",
            actor_role="orchestrator",
        )
        
        assert event.event_id == "evt-001"
        assert event.event_type == EventType.DELEGATE_CREATED
    
    def test_event_validation(self):
        """Test Event validation."""
        event = Event(
            event_id="",  # Empty
            event_type=EventType.DELEGATE_CREATED,
            task_id="",  # Empty
            actor="",
            actor_role="",
        )
        
        errors = event.validate()
        assert len(errors) > 0


class TestArtifactLinking:
    """Tests for artifact linking."""
    
    def test_create_artifact_link(self):
        """Test creating an artifact link."""
        link = ArtifactLink(
            link_id="link-001",
            source_artifact_id="2026-05-17-test-task",
            source_artifact_type="delegate",
            target_artifact_id="2026-05-17-test-task",
            target_artifact_type="handback",
            link_type="executes",
        )
        
        assert link.link_id == "link-001"
        assert link.link_type == "executes"
    
    def test_artifact_linkage_manager(self):
        """Test ArtifactLinkage manager."""
        linkage = ArtifactLinkage()
        
        link = linkage.create_link(
            source_id="2026-05-17-test-task",
            source_type="delegate",
            target_id="2026-05-17-test-task",
            target_type="handback",
            link_type="executes",
            description="Task execution link",
        )
        
        assert len(linkage.links) == 1
        
        # Get links from source
        from_links = linkage.get_links_from("2026-05-17-test-task")
        assert len(from_links) == 1


class TestValidation:
    """Tests for validation functions."""
    
    def test_validate_delegate_valid(self):
        """Test validating a valid DELEGATE."""
        data = {
            "task_id": "2026-05-17-test-task",
            "role": "engineer",
            "model": "claude-haiku-4-5",
            "effort": "high",
            "scope": "This is a test task that should have at least fifteen words in the scope description for validation purposes.",
            "plan": ["Step 1", "Step 2"],
        }
        
        errors = validate_delegate(data)
        assert len(errors) == 0
    
    def test_validate_delegate_invalid(self):
        """Test validating an invalid DELEGATE."""
        data = {
            "task_id": "test",  # Too short
            "role": "invalid",
            "effort": "high",
            "scope": "Short",  # Too short
            # Missing plan
        }
        
        errors = validate_delegate(data)
        assert len(errors) > 0
    
    def test_validate_handback_valid(self):
        """Test validating a valid HANDBACK."""
        data = {
            "task_id": "2026-05-17-test-task",
            "status": "complete",
            "deliverables": ["file1.py"],
            "tests": {"test_1": True},
        }
        
        errors = validate_handback(data)
        assert len(errors) == 0
    
    def test_validate_handback_invalid(self):
        """Test validating an invalid HANDBACK."""
        data = {
            "task_id": "",
            "status": "invalid",
            "quality_score": 150,
        }
        
        errors = validate_handback(data)
        assert len(errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
