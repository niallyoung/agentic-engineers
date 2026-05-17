"""
Tests for Quality Engineer Protocol Integration.

Tests the integration of expanded protocol schemas with the Quality Engineer.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict
from src.orchestration.agents.quality_engineer_protocol_integration import QualityEngineerProtocolIntegration


class TestQualityEngineerProtocolIntegration:
    """Test Quality Engineer protocol integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.qe = QualityEngineerProtocolIntegration()
    
    def _create_delegate_dict(self, task_id: str, role: str = "engineer", quality_baseline: int = 90) -> Dict:
        """Helper to create delegate dict."""
        return {
            "task_id": task_id,
            "role": role,
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "scope": "Implement feature with comprehensive testing and documentation",
            "quality_baseline": quality_baseline,
            "acceptance_criteria": ["All tests pass", "Code coverage ≥90%"],
            "quality_thresholds": {},
            "quality_required_by": datetime.now().isoformat(),
            "tags": [],
            "priority": "medium",
            "dependencies": [],
            "related_tasks": [],
            "plan": ["Design", "Implement", "Test"],
            "estimated_tokens": 0,
            "estimated_time_minutes": 0,
            "constraints": [],
            "feedback_required": True,
            "feedback_topics": [],
            "optimization_targets": [],
            "cost_target": 1.5,
            "parent_task_id": None,
            "related_artifacts": [],
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
        }
    
    def _create_handback_dict(self, task_id: str, quality_score: int = 92) -> Dict:
        """Helper to create handback dict."""
        return {
            "task_id": task_id,
            "status": "complete",
            "quality_score": quality_score,
            "test_coverage": quality_score / 100,
            "cost_actual": 1.2,
            "tokens_in": 22000,
            "tokens_out": 8000,
            "time_elapsed_minutes": 180,
            "model_used": "claude-sonnet-4-6",
            "acceptance_criteria_met": ["All tests pass", "Code coverage ≥90%"] if quality_score >= 90 else ["All tests pass"],
            "deliverables": ["src/feature.py"],
            "tests": {"unit": True},
            "regressions_detected": 0 if quality_score >= 80 else 2,
            "success_rate": quality_score / 100,
            "quality_trend": "improved",
            "cost_trend": "under",
            "effort_actual": "medium",
            "notes": "Task completed",
            "created_at": datetime.now().isoformat(),
            "version": "1.0",
        }
    
    def test_evaluate_quality_high(self):
        """Test quality evaluation for high-quality task."""
        delegate = self._create_delegate_dict("2026-05-20-high-quality", quality_baseline=90)
        handback = self._create_handback_dict("2026-05-20-high-quality", quality_score=92)
        
        evaluation = self.qe.evaluate_quality(delegate, handback)
        
        assert evaluation.quality_score == 92
        assert evaluation.quality_baseline == 90
        assert not evaluation.escalation_required
        assert len(self.qe.evaluations) == 1
    
    def test_evaluate_quality_low(self):
        """Test quality evaluation for low-quality task."""
        delegate = self._create_delegate_dict("2026-05-20-low-quality", quality_baseline=90)
        handback = self._create_handback_dict("2026-05-20-low-quality", quality_score=55)
        
        evaluation = self.qe.evaluate_quality(delegate, handback)
        
        assert evaluation.quality_score == 55
        assert evaluation.escalation_required
        assert len(self.qe.evaluations) == 1
    
    def test_check_escalation_required(self):
        """Test escalation check for low-quality task."""
        delegate = self._create_delegate_dict("2026-05-20-escalate", quality_baseline=90)
        handback = self._create_handback_dict("2026-05-20-escalate", quality_score=55)
        
        evaluation = self.qe.evaluate_quality(delegate, handback)
        should_escalate, context = self.qe.check_escalation(evaluation, delegate)
        
        assert should_escalate
        assert context is not None
        assert context["escalation_level"] == "principal_engineer"
        assert context["quality_score"] == 55
        assert len(self.qe.escalations) == 1
    
    def test_check_escalation_not_required(self):
        """Test escalation check for high-quality task."""
        delegate = self._create_delegate_dict("2026-05-20-no-escalate", quality_baseline=90)
        handback = self._create_handback_dict("2026-05-20-no-escalate", quality_score=92)
        
        evaluation = self.qe.evaluate_quality(delegate, handback)
        should_escalate, context = self.qe.check_escalation(evaluation, delegate)
        
        assert not should_escalate
        assert context is None
        assert len(self.qe.escalations) == 0
    
    def test_quality_metrics_7_day(self):
        """Test quality metrics for 7-day period."""
        # Create multiple evaluations
        for i in range(5):
            delegate = self._create_delegate_dict(f"2026-05-20-metric-{i}", role="engineer", quality_baseline=90)
            handback = self._create_handback_dict(f"2026-05-20-metric-{i}", quality_score=85 + i)
            self.qe.evaluate_quality(delegate, handback)
        
        # Get metrics
        metrics = self.qe.get_quality_metrics("engineer", days=7)
        
        assert metrics["count"] == 5
        assert metrics["avg_quality"] == 87.0  # (85+86+87+88+89)/5
        assert metrics["min_quality"] == 85
        assert metrics["max_quality"] == 89
        assert metrics["success_rate"] == 0.0  # 0 out of 5 >= baseline 90
    
    def test_quality_metrics_trend_improving(self):
        """Test quality trend detection (improving)."""
        # Create evaluations with improving trend
        scores = [80, 82, 84, 86, 88, 90, 92]
        for i, score in enumerate(scores):
            delegate = self._create_delegate_dict(f"2026-05-20-trend-{i}", role="engineer", quality_baseline=90)
            handback = self._create_handback_dict(f"2026-05-20-trend-{i}", quality_score=score)
            self.qe.evaluate_quality(delegate, handback)
        
        metrics = self.qe.get_quality_metrics("engineer", days=30)
        assert metrics["trend"] == "improving"
    
    def test_quality_metrics_trend_declining(self):
        """Test quality trend detection (declining)."""
        # Create evaluations with declining trend
        scores = [92, 90, 88, 86, 84, 82, 80]
        for i, score in enumerate(scores):
            delegate = self._create_delegate_dict(f"2026-05-20-decline-{i}", role="engineer", quality_baseline=90)
            handback = self._create_handback_dict(f"2026-05-20-decline-{i}", quality_score=score)
            self.qe.evaluate_quality(delegate, handback)
        
        metrics = self.qe.get_quality_metrics("engineer", days=30)
        assert metrics["trend"] == "declining"
    
    def test_quality_dashboard(self):
        """Test quality dashboard generation."""
        # Create evaluations for multiple roles
        for role in ["engineer", "senior-engineer"]:
            for i in range(3):
                delegate = self._create_delegate_dict(f"2026-05-20-dashboard-{role}-{i}", role=role, quality_baseline=90)
                handback = self._create_handback_dict(f"2026-05-20-dashboard-{role}-{i}", quality_score=85 + i)
                self.qe.evaluate_quality(delegate, handback)
        
        dashboard = self.qe.get_quality_dashboard()
        
        assert dashboard["total_evaluations"] == 6
        assert "engineer" in dashboard["roles"]
        assert "senior-engineer" in dashboard["roles"]
        assert "overall" in dashboard
        assert dashboard["overall"]["avg_quality"] > 0
    
    def test_get_escalations_all(self):
        """Test getting all escalations."""
        # Create escalations
        for i in range(3):
            delegate = self._create_delegate_dict(f"2026-05-20-esc-{i}", role="engineer", quality_baseline=90)
            handback = self._create_handback_dict(f"2026-05-20-esc-{i}", quality_score=50 + i)
            evaluation = self.qe.evaluate_quality(delegate, handback)
            self.qe.check_escalation(evaluation, delegate)
        
        escalations = self.qe.get_escalations()
        assert len(escalations) == 3
    
    def test_get_escalations_by_role(self):
        """Test getting escalations filtered by role."""
        # Create escalations for different roles
        for role in ["engineer", "senior-engineer"]:
            for i in range(2):
                delegate = self._create_delegate_dict(f"2026-05-20-esc-{role}-{i}", role=role, quality_baseline=90)
                handback = self._create_handback_dict(f"2026-05-20-esc-{role}-{i}", quality_score=50)
                evaluation = self.qe.evaluate_quality(delegate, handback)
                self.qe.check_escalation(evaluation, delegate)
        
        engineer_escalations = self.qe.get_escalations(role="engineer")
        assert len(engineer_escalations) == 2
        
        senior_escalations = self.qe.get_escalations(role="senior-engineer")
        assert len(senior_escalations) == 2
    
    def test_improvement_recommendations_low_quality(self):
        """Test improvement recommendations for low-quality role."""
        # Create low-quality evaluations
        for i in range(5):
            delegate = self._create_delegate_dict(f"2026-05-20-low-{i}", role="engineer", quality_baseline=90)
            handback = self._create_handback_dict(f"2026-05-20-low-{i}", quality_score=75)
            self.qe.evaluate_quality(delegate, handback)
        
        recommendations = self.qe.generate_improvement_recommendations("engineer")
        
        assert len(recommendations) > 0
        assert any("quality" in r.lower() for r in recommendations)
    
    def test_improvement_recommendations_high_quality(self):
        """Test improvement recommendations for high-quality role."""
        # Create high-quality evaluations
        for i in range(5):
            delegate = self._create_delegate_dict(f"2026-05-20-high-{i}", role="engineer", quality_baseline=90)
            handback = self._create_handback_dict(f"2026-05-20-high-{i}", quality_score=95)
            self.qe.evaluate_quality(delegate, handback)
        
        recommendations = self.qe.generate_improvement_recommendations("engineer")
        
        # Should have no or minimal recommendations
        assert len(recommendations) == 0
    
    def test_escalation_summary(self):
        """Test escalation summary generation."""
        # Create escalations with different levels
        for i in range(3):
            delegate = self._create_delegate_dict(f"2026-05-20-sum-{i}", role="engineer", quality_baseline=90)
            handback = self._create_handback_dict(f"2026-05-20-sum-{i}", quality_score=50 + i)
            evaluation = self.qe.evaluate_quality(delegate, handback)
            self.qe.check_escalation(evaluation, delegate)
        
        summary = self.qe.generate_escalation_summary()
        
        assert summary["total_escalations"] == 3
        assert "by_level" in summary
        assert "by_reason" in summary
        assert "by_role" in summary
