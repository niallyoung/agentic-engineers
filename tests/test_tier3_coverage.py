"""
COVERAGE-TIER3: Tests for optional/edge-case modules.

Targets:
- src/orchestration/memory/session_memory.py (67% → 85%+)
- src/orchestration/protocol/feedback_outcome.py (72% → 90%+)
- src/orchestration/protocol/optimization.py (67% → 85%+)
- src/orchestration/protocol/quality_evaluation.py (64% → 85%+)
"""

import os
import json
import tempfile
import shutil
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# ─── Imports ───────────────────────────────────────────────────────────────────

from src.orchestration.protocol.feedback_outcome import FeedbackOutcome
from src.orchestration.protocol.optimization import (
    Optimization,
    CostOpportunity,
    QualityOpportunity,
)
from src.orchestration.protocol.quality_evaluation import QualityEvaluation
from src.orchestration.memory.session_memory import (
    SessionMemoryManager,
    GlobalMemoryManager,
)


# ═══════════════════════════════════════════════════════════════════════════════
# FeedbackOutcome Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestFeedbackOutcomeToDict:
    """Tests for FeedbackOutcome.to_dict() (line 70 uncovered)."""

    def test_to_dict_basic(self):
        """to_dict returns all required keys."""
        fo = FeedbackOutcome(
            task_id="t-001",
            outcome="success",
            quality_baseline=90,
            quality_achieved=95,
            cost_budget=0.10,
            cost_actual=0.07,
        )
        d = fo.to_dict()
        assert d["task_id"] == "t-001"
        assert d["outcome"] == "success"
        assert d["quality_baseline"] == 90
        assert d["quality_achieved"] == 95
        assert d["cost_budget"] == 0.10
        assert d["cost_actual"] == 0.07

    def test_to_dict_optional_fields(self):
        """to_dict includes optional recommendation fields."""
        fo = FeedbackOutcome(
            task_id="t-002",
            outcome="partial",
            quality_baseline=85,
            quality_achieved=80,
            cost_budget=0.20,
            cost_actual=0.18,
            routing_recommendation="senior-engineer",
            model_recommendation="claude-sonnet-4.6",
            effort_recommendation="high",
            recommendations=["Increase effort", "Use better model"],
            agent_role="engineer",
            agent_success_rate=0.87,
            model_used="claude-haiku-4.5",
            effort_level="medium",
        )
        d = fo.to_dict()
        assert d["routing_recommendation"] == "senior-engineer"
        assert d["model_recommendation"] == "claude-sonnet-4.6"
        assert d["effort_recommendation"] == "high"
        assert len(d["recommendations"]) == 2
        assert d["agent_role"] == "engineer"
        assert d["agent_success_rate"] == 0.87

    def test_to_dict_trend_fields(self):
        """to_dict includes trend data."""
        fo = FeedbackOutcome(
            task_id="t-003",
            outcome="success",
            quality_baseline=90,
            quality_achieved=92,
            cost_budget=0.10,
            cost_actual=0.09,
            trend_7day={"quality": 91.5, "cost": 0.088},
            trend_30day={"quality": 89.0, "cost": 0.092},
        )
        d = fo.to_dict()
        assert d["trend_7day"] == {"quality": 91.5, "cost": 0.088}
        assert d["trend_30day"] == {"quality": 89.0, "cost": 0.092}
        assert "version" in d
        assert "recorded_at" in d

    def test_to_dict_null_recommendations(self):
        """to_dict handles None recommendation fields."""
        fo = FeedbackOutcome(
            task_id="t-004",
            outcome="failed",
            quality_baseline=90,
            quality_achieved=50,
            cost_budget=0.10,
            cost_actual=0.15,
        )
        d = fo.to_dict()
        assert d["routing_recommendation"] is None
        assert d["model_recommendation"] is None
        assert d["effort_recommendation"] is None


class TestFeedbackOutcomeFromDict:
    """Tests for FeedbackOutcome.from_dict() (line 96 uncovered)."""

    def test_from_dict_basic(self):
        """from_dict reconstructs a FeedbackOutcome from a dict."""
        data = {
            "task_id": "t-010",
            "outcome": "success",
            "quality_baseline": 90,
            "quality_achieved": 93,
            "cost_budget": 0.10,
            "cost_actual": 0.08,
        }
        fo = FeedbackOutcome.from_dict(data)
        assert fo.task_id == "t-010"
        assert fo.outcome == "success"
        assert fo.quality_baseline == 90
        assert fo.quality_achieved == 93

    def test_from_dict_defaults(self):
        """from_dict uses sensible defaults for missing optional fields."""
        data = {"task_id": "t-011", "outcome": "partial"}
        fo = FeedbackOutcome.from_dict(data)
        assert fo.quality_baseline == 90  # default
        assert fo.quality_achieved == 0   # default
        assert fo.cost_budget == 0.0
        assert fo.cost_actual == 0.0
        assert fo.recommendations == []
        assert fo.trend_7day == {}
        assert fo.trend_30day == {}

    def test_from_dict_with_all_optional_fields(self):
        """from_dict handles all optional fields."""
        data = {
            "task_id": "t-012",
            "outcome": "success",
            "quality_baseline": 85,
            "quality_achieved": 88,
            "quality_assessment": "exceeds",
            "cost_budget": 0.15,
            "cost_actual": 0.12,
            "cost_assessment": "under",
            "trend_7day": {"quality": 87.0},
            "trend_30day": {"quality": 86.5},
            "agent_role": "senior-engineer",
            "agent_success_rate": 0.95,
            "model_used": "claude-sonnet-4.6",
            "effort_level": "high",
            "recommendations": ["rec1"],
            "routing_recommendation": "lead-engineer",
            "model_recommendation": "claude-sonnet-4.6",
            "effort_recommendation": "medium",
            "recorded_at": "2026-01-01T00:00:00",
            "version": "2.0",
        }
        fo = FeedbackOutcome.from_dict(data)
        assert fo.quality_assessment == "exceeds"
        assert fo.cost_assessment == "under"
        assert fo.agent_role == "senior-engineer"
        assert fo.model_used == "claude-sonnet-4.6"
        assert fo.version == "2.0"
        assert fo.recorded_at == "2026-01-01T00:00:00"

    def test_round_trip_serialization(self):
        """to_dict → from_dict preserves all data."""
        fo = FeedbackOutcome(
            task_id="t-013",
            outcome="success",
            quality_baseline=90,
            quality_achieved=92,
            cost_budget=0.10,
            cost_actual=0.09,
            agent_role="engineer",
            recommendations=["do better"],
        )
        fo.compute_assessments()
        d = fo.to_dict()
        fo2 = FeedbackOutcome.from_dict(d)
        assert fo2.task_id == fo.task_id
        assert fo2.outcome == fo.outcome
        assert fo2.quality_assessment == fo.quality_assessment
        assert fo2.cost_assessment == fo.cost_assessment


class TestFeedbackOutcomeValidate:
    """Tests for FeedbackOutcome.validate() (lines 121-134 uncovered)."""

    def test_validate_valid(self):
        """validate() returns empty list for valid instance."""
        fo = FeedbackOutcome(
            task_id="t-020",
            outcome="success",
            quality_baseline=90,
            quality_achieved=92,
            cost_budget=0.10,
            cost_actual=0.09,
            agent_success_rate=0.95,
        )
        errors = fo.validate()
        assert errors == []

    def test_validate_empty_task_id(self):
        """validate() catches empty task_id."""
        fo = FeedbackOutcome(
            task_id="",
            outcome="success",
            quality_baseline=90,
            quality_achieved=92,
            cost_budget=0.10,
            cost_actual=0.09,
        )
        errors = fo.validate()
        assert any("task_id" in e for e in errors)

    def test_validate_invalid_outcome(self):
        """validate() catches invalid outcome values."""
        fo = FeedbackOutcome(
            task_id="t-021",
            outcome="unknown",
            quality_baseline=90,
            quality_achieved=92,
            cost_budget=0.10,
            cost_actual=0.09,
        )
        errors = fo.validate()
        assert any("outcome" in e.lower() or "Invalid" in e for e in errors)

    def test_validate_quality_baseline_out_of_range(self):
        """validate() catches quality_baseline > 100."""
        fo = FeedbackOutcome(
            task_id="t-022",
            outcome="success",
            quality_baseline=150,
            quality_achieved=92,
            cost_budget=0.10,
            cost_actual=0.09,
        )
        errors = fo.validate()
        assert any("quality_baseline" in e for e in errors)

    def test_validate_quality_achieved_negative(self):
        """validate() catches quality_achieved < 0."""
        fo = FeedbackOutcome(
            task_id="t-023",
            outcome="success",
            quality_baseline=90,
            quality_achieved=-5,
            cost_budget=0.10,
            cost_actual=0.09,
        )
        errors = fo.validate()
        assert any("quality_achieved" in e for e in errors)

    def test_validate_agent_success_rate_out_of_range(self):
        """validate() catches agent_success_rate > 1."""
        fo = FeedbackOutcome(
            task_id="t-024",
            outcome="success",
            quality_baseline=90,
            quality_achieved=90,
            cost_budget=0.10,
            cost_actual=0.09,
            agent_success_rate=1.5,
        )
        errors = fo.validate()
        assert any("agent_success_rate" in e for e in errors)

    def test_validate_multiple_errors(self):
        """validate() accumulates multiple errors."""
        fo = FeedbackOutcome(
            task_id="",
            outcome="invalid",
            quality_baseline=200,
            quality_achieved=-10,
            cost_budget=0.10,
            cost_actual=0.09,
        )
        errors = fo.validate()
        assert len(errors) >= 3


class TestFeedbackOutcomeComputeAssessments:
    """Tests for compute_assessments() cost 'on' case (line 150 uncovered)."""

    def test_cost_assessment_on_target(self):
        """compute_assessments() sets cost_assessment='on' when within 10% over."""
        fo = FeedbackOutcome(
            task_id="t-030",
            outcome="success",
            quality_baseline=90,
            quality_achieved=92,
            cost_budget=0.10,
            cost_actual=0.105,  # 5% over budget, within 10% tolerance
        )
        fo.compute_assessments()
        assert fo.cost_assessment == "on"

    def test_cost_assessment_over_budget(self):
        """compute_assessments() sets cost_assessment='over' when >110% of budget."""
        fo = FeedbackOutcome(
            task_id="t-031",
            outcome="success",
            quality_baseline=90,
            quality_achieved=92,
            cost_budget=0.10,
            cost_actual=0.12,  # 20% over budget
        )
        fo.compute_assessments()
        assert fo.cost_assessment == "over"

    def test_quality_assessment_meets(self):
        """compute_assessments() sets quality_assessment='meets' at 90-99% of baseline."""
        fo = FeedbackOutcome(
            task_id="t-032",
            outcome="success",
            quality_baseline=100,
            quality_achieved=94,  # 94% of 100 → meets (≥90%)
            cost_budget=0.10,
            cost_actual=0.10,
        )
        fo.compute_assessments()
        assert fo.quality_assessment == "meets"

    def test_quality_assessment_below(self):
        """compute_assessments() sets quality_assessment='below' when <90% of baseline."""
        fo = FeedbackOutcome(
            task_id="t-033",
            outcome="failed",
            quality_baseline=100,
            quality_achieved=80,  # 80% of 100 → below
            cost_budget=0.10,
            cost_actual=0.10,
        )
        fo.compute_assessments()
        assert fo.quality_assessment == "below"


# ═══════════════════════════════════════════════════════════════════════════════
# Optimization Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestOptimizationToDict:
    """Tests for Optimization.to_dict() with opportunities (line 78 uncovered)."""

    def test_to_dict_empty(self):
        """to_dict works with no opportunities."""
        opt = Optimization(task_id="opt-001")
        d = opt.to_dict()
        assert d["task_id"] == "opt-001"
        assert d["cost_opportunities"] == []
        assert d["quality_opportunities"] == []

    def test_to_dict_with_cost_opportunities(self):
        """to_dict serializes CostOpportunity objects."""
        opt = Optimization(task_id="opt-002")
        opt.cost_opportunities.append(CostOpportunity(
            opportunity_type="model_downgrade",
            description="Use Haiku instead of Sonnet for simple tasks",
            estimated_savings=0.05,
            estimated_savings_percent=40.0,
            confidence=0.9,
            implementation_effort="low",
        ))
        d = opt.to_dict()
        assert len(d["cost_opportunities"]) == 1
        co = d["cost_opportunities"][0]
        assert co["opportunity_type"] == "model_downgrade"
        assert co["estimated_savings"] == 0.05
        assert co["confidence"] == 0.9

    def test_to_dict_with_quality_opportunities(self):
        """to_dict serializes QualityOpportunity objects."""
        opt = Optimization(task_id="opt-003")
        opt.quality_opportunities.append(QualityOpportunity(
            opportunity_type="model_upgrade",
            description="Upgrade to Opus for complex reasoning",
            estimated_improvement=8,
            estimated_cost_increase=0.03,
            confidence=0.85,
            implementation_effort="medium",
        ))
        d = opt.to_dict()
        assert len(d["quality_opportunities"]) == 1
        qo = d["quality_opportunities"][0]
        assert qo["opportunity_type"] == "model_upgrade"
        assert qo["estimated_improvement"] == 8
        assert qo["estimated_cost_increase"] == 0.03

    def test_to_dict_with_both_opportunity_types(self):
        """to_dict handles both cost and quality opportunities."""
        opt = Optimization(
            task_id="opt-004",
            historical_success_rate=0.92,
            historical_avg_quality=87.0,
            historical_avg_cost=0.08,
            recommendations=["Downgrade model", "Add more tests"],
            primary_recommendation="Downgrade model",
            confidence_score=0.88,
            estimated_total_savings=0.05,
            estimated_quality_improvement=5,
        )
        opt.cost_opportunities.append(CostOpportunity(
            opportunity_type="effort_reduction",
            description="Reduce effort for simple tasks",
            estimated_savings=0.02,
            estimated_savings_percent=20.0,
            confidence=0.75,
            implementation_effort="low",
        ))
        opt.quality_opportunities.append(QualityOpportunity(
            opportunity_type="more_testing",
            description="Add integration tests",
            estimated_improvement=5,
            estimated_cost_increase=0.01,
            confidence=0.8,
            implementation_effort="medium",
        ))
        d = opt.to_dict()
        assert len(d["cost_opportunities"]) == 1
        assert len(d["quality_opportunities"]) == 1
        assert d["primary_recommendation"] == "Downgrade model"
        assert d["confidence_score"] == 0.88
        assert d["estimated_total_savings"] == 0.05

    def test_to_dict_includes_metadata(self):
        """to_dict includes analyzed_at and version."""
        opt = Optimization(task_id="opt-005")
        d = opt.to_dict()
        assert "analyzed_at" in d
        assert "version" in d
        assert d["version"] == "1.0"


class TestOptimizationFromDict:
    """Tests for Optimization.from_dict() with cost/quality opps (lines 118-140)."""

    def test_from_dict_basic(self):
        """from_dict creates Optimization from minimal dict."""
        data = {"task_id": "opt-010"}
        opt = Optimization.from_dict(data)
        assert opt.task_id == "opt-010"
        assert opt.cost_opportunities == []
        assert opt.quality_opportunities == []

    def test_from_dict_with_cost_opportunities(self):
        """from_dict reconstructs CostOpportunity objects."""
        data = {
            "task_id": "opt-011",
            "cost_opportunities": [
                {
                    "opportunity_type": "model_downgrade",
                    "description": "Use cheaper model",
                    "estimated_savings": 0.03,
                    "estimated_savings_percent": 30.0,
                    "confidence": 0.8,
                    "implementation_effort": "low",
                }
            ],
        }
        opt = Optimization.from_dict(data)
        assert len(opt.cost_opportunities) == 1
        co = opt.cost_opportunities[0]
        assert co.opportunity_type == "model_downgrade"
        assert co.estimated_savings == 0.03
        assert isinstance(co, CostOpportunity)

    def test_from_dict_with_quality_opportunities(self):
        """from_dict reconstructs QualityOpportunity objects."""
        data = {
            "task_id": "opt-012",
            "quality_opportunities": [
                {
                    "opportunity_type": "additional_review",
                    "description": "Add a review step",
                    "estimated_improvement": 7,
                    "estimated_cost_increase": 0.02,
                    "confidence": 0.75,
                    "implementation_effort": "high",
                }
            ],
        }
        opt = Optimization.from_dict(data)
        assert len(opt.quality_opportunities) == 1
        qo = opt.quality_opportunities[0]
        assert qo.opportunity_type == "additional_review"
        assert qo.estimated_improvement == 7
        assert isinstance(qo, QualityOpportunity)

    def test_from_dict_full_round_trip(self):
        """to_dict → from_dict preserves all data."""
        opt = Optimization(
            task_id="opt-013",
            historical_success_rate=0.9,
            historical_avg_quality=88.0,
            historical_avg_cost=0.07,
            recommendations=["rec1", "rec2"],
            primary_recommendation="rec1",
            confidence_score=0.85,
            estimated_total_savings=0.04,
            estimated_quality_improvement=6,
        )
        opt.cost_opportunities.append(CostOpportunity(
            opportunity_type="parallelization",
            description="Run tasks in parallel",
            estimated_savings=0.04,
            estimated_savings_percent=35.0,
            confidence=0.85,
            implementation_effort="medium",
        ))
        opt.quality_opportunities.append(QualityOpportunity(
            opportunity_type="model_upgrade",
            description="Use a better model",
            estimated_improvement=6,
            estimated_cost_increase=0.02,
            confidence=0.9,
            implementation_effort="low",
        ))

        d = opt.to_dict()
        opt2 = Optimization.from_dict(d)
        assert opt2.task_id == opt.task_id
        assert len(opt2.cost_opportunities) == 1
        assert len(opt2.quality_opportunities) == 1
        assert opt2.cost_opportunities[0].opportunity_type == "parallelization"
        assert opt2.quality_opportunities[0].opportunity_type == "model_upgrade"

    def test_from_dict_defaults(self):
        """from_dict uses sensible defaults for missing optional fields."""
        data = {"task_id": "opt-014"}
        opt = Optimization.from_dict(data)
        assert opt.historical_success_rate == 0.0
        assert opt.historical_avg_quality == 0.0
        assert opt.historical_avg_cost == 0.0
        assert opt.recommendations == []
        assert opt.primary_recommendation is None
        assert opt.confidence_score == 0.0


class TestOptimizationValidate:
    """Tests for Optimization.validate() (lines 159-170 uncovered)."""

    def test_validate_valid(self):
        """validate() returns empty errors for valid instance."""
        opt = Optimization(
            task_id="opt-020",
            historical_success_rate=0.9,
            historical_avg_quality=88.0,
            confidence_score=0.85,
        )
        assert opt.validate() == []

    def test_validate_empty_task_id(self):
        """validate() catches empty task_id."""
        opt = Optimization(task_id="")
        errors = opt.validate()
        assert any("task_id" in e for e in errors)

    def test_validate_historical_success_rate_out_of_range(self):
        """validate() catches historical_success_rate > 1."""
        opt = Optimization(
            task_id="opt-021",
            historical_success_rate=1.5,
        )
        errors = opt.validate()
        assert any("historical_success_rate" in e for e in errors)

    def test_validate_historical_avg_quality_out_of_range(self):
        """validate() catches historical_avg_quality > 100."""
        opt = Optimization(
            task_id="opt-022",
            historical_avg_quality=150.0,
        )
        errors = opt.validate()
        assert any("historical_avg_quality" in e for e in errors)

    def test_validate_confidence_score_out_of_range(self):
        """validate() catches confidence_score > 1."""
        opt = Optimization(
            task_id="opt-023",
            confidence_score=2.0,
        )
        errors = opt.validate()
        assert any("confidence_score" in e for e in errors)

    def test_validate_multiple_errors(self):
        """validate() accumulates multiple errors."""
        opt = Optimization(
            task_id="",
            historical_success_rate=2.0,
            historical_avg_quality=200.0,
            confidence_score=-0.1,
        )
        errors = opt.validate()
        assert len(errors) >= 3

    def test_validate_boundary_values(self):
        """validate() accepts boundary values (0 and 1 / 0 and 100)."""
        opt = Optimization(
            task_id="opt-024",
            historical_success_rate=0.0,
            historical_avg_quality=0.0,
            confidence_score=1.0,
        )
        assert opt.validate() == []

        opt2 = Optimization(
            task_id="opt-025",
            historical_success_rate=1.0,
            historical_avg_quality=100.0,
            confidence_score=0.0,
        )
        assert opt2.validate() == []


# ═══════════════════════════════════════════════════════════════════════════════
# QualityEvaluation Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestQualityEvaluationToDict:
    """Tests for QualityEvaluation.to_dict() (line 59 uncovered)."""

    def test_to_dict_basic(self):
        """to_dict returns all required keys."""
        qe = QualityEvaluation(
            task_id="qe-001",
            delegate_task_id="del-001",
            handback_task_id="hb-001",
            quality_baseline=90,
            quality_achieved=92,
        )
        d = qe.to_dict()
        assert d["task_id"] == "qe-001"
        assert d["delegate_task_id"] == "del-001"
        assert d["handback_task_id"] == "hb-001"
        assert d["quality_baseline"] == 90
        assert d["quality_achieved"] == 92

    def test_to_dict_with_evaluation_results(self):
        """to_dict serializes evaluation_results and acceptance_criteria."""
        qe = QualityEvaluation(
            task_id="qe-002",
            delegate_task_id="del-002",
            handback_task_id="hb-002",
            quality_baseline=90,
            quality_achieved=88,
            quality_score=85,
            evaluation_results={"test_coverage": True, "docs_updated": False},
            acceptance_criteria_assessment={"criterion_1": True, "criterion_2": True},
            issues_found=["Missing edge case test"],
            recommendations=["Add edge case tests"],
            escalation_required=False,
            escalation_reason=None,
        )
        d = qe.to_dict()
        assert d["evaluation_results"] == {"test_coverage": True, "docs_updated": False}
        assert d["acceptance_criteria_assessment"] == {"criterion_1": True, "criterion_2": True}
        assert d["issues_found"] == ["Missing edge case test"]
        assert d["recommendations"] == ["Add edge case tests"]
        assert d["escalation_required"] is False

    def test_to_dict_with_escalation(self):
        """to_dict handles escalation fields."""
        qe = QualityEvaluation(
            task_id="qe-003",
            delegate_task_id="del-003",
            handback_task_id="hb-003",
            quality_baseline=90,
            quality_achieved=60,
            escalation_required=True,
            escalation_reason="Quality far below baseline",
        )
        d = qe.to_dict()
        assert d["escalation_required"] is True
        assert d["escalation_reason"] == "Quality far below baseline"

    def test_to_dict_includes_metadata(self):
        """to_dict includes evaluated_at, evaluator, version."""
        qe = QualityEvaluation(
            task_id="qe-004",
            delegate_task_id="del-004",
            handback_task_id="hb-004",
            quality_baseline=90,
            quality_achieved=90,
            evaluator="senior-quality-engineer",
        )
        d = qe.to_dict()
        assert "evaluated_at" in d
        assert d["evaluator"] == "senior-quality-engineer"
        assert "version" in d


class TestQualityEvaluationFromDict:
    """Tests for QualityEvaluation.from_dict() (line 80 uncovered)."""

    def test_from_dict_basic(self):
        """from_dict reconstructs QualityEvaluation from minimal dict."""
        data = {
            "task_id": "qe-010",
            "delegate_task_id": "del-010",
            "handback_task_id": "hb-010",
            "quality_baseline": 90,
            "quality_achieved": 92,
        }
        qe = QualityEvaluation.from_dict(data)
        assert qe.task_id == "qe-010"
        assert qe.quality_baseline == 90
        assert qe.quality_achieved == 92

    def test_from_dict_defaults(self):
        """from_dict uses sensible defaults for optional fields."""
        data = {
            "task_id": "qe-011",
            "delegate_task_id": "del-011",
            "handback_task_id": "hb-011",
            "quality_baseline": 90,
            "quality_achieved": 90,
        }
        qe = QualityEvaluation.from_dict(data)
        assert qe.quality_score == 0
        assert qe.evaluation_results == {}
        assert qe.acceptance_criteria_assessment == {}
        assert qe.issues_found == []
        assert qe.recommendations == []
        assert qe.escalation_required is False
        assert qe.escalation_reason is None
        assert qe.evaluator == "quality-engineer"

    def test_from_dict_full_data(self):
        """from_dict handles all fields."""
        data = {
            "task_id": "qe-012",
            "delegate_task_id": "del-012",
            "handback_task_id": "hb-012",
            "quality_baseline": 85,
            "quality_achieved": 88,
            "quality_score": 82,
            "evaluation_results": {"check1": True, "check2": False},
            "acceptance_criteria_assessment": {"ac1": True},
            "issues_found": ["issue1"],
            "recommendations": ["rec1", "rec2"],
            "escalation_required": True,
            "escalation_reason": "Critical issue found",
            "evaluated_at": "2026-01-01T00:00:00",
            "evaluator": "lead-engineer",
            "version": "2.0",
        }
        qe = QualityEvaluation.from_dict(data)
        assert qe.quality_score == 82
        assert qe.evaluation_results == {"check1": True, "check2": False}
        assert qe.issues_found == ["issue1"]
        assert qe.escalation_required is True
        assert qe.evaluator == "lead-engineer"
        assert qe.version == "2.0"

    def test_round_trip(self):
        """to_dict → from_dict is lossless."""
        qe = QualityEvaluation(
            task_id="qe-013",
            delegate_task_id="del-013",
            handback_task_id="hb-013",
            quality_baseline=90,
            quality_achieved=88,
            quality_score=85,
            evaluation_results={"t1": True, "t2": False},
            issues_found=["minor issue"],
            escalation_required=False,
        )
        d = qe.to_dict()
        qe2 = QualityEvaluation.from_dict(d)
        assert qe2.task_id == qe.task_id
        assert qe2.quality_score == qe.quality_score
        assert qe2.evaluation_results == qe.evaluation_results


class TestQualityEvaluationValidate:
    """Tests for QualityEvaluation.validate() (lines 100-115 uncovered)."""

    def test_validate_valid(self):
        """validate() returns empty list for valid instance."""
        qe = QualityEvaluation(
            task_id="qe-020",
            delegate_task_id="del-020",
            handback_task_id="hb-020",
            quality_baseline=90,
            quality_achieved=92,
            quality_score=88,
        )
        assert qe.validate() == []

    def test_validate_empty_task_id(self):
        """validate() catches empty task_id."""
        qe = QualityEvaluation(
            task_id="",
            delegate_task_id="del-021",
            handback_task_id="hb-021",
            quality_baseline=90,
            quality_achieved=90,
        )
        errors = qe.validate()
        assert any("task_id" in e for e in errors)

    def test_validate_empty_delegate_task_id(self):
        """validate() catches empty delegate_task_id."""
        qe = QualityEvaluation(
            task_id="qe-022",
            delegate_task_id="",
            handback_task_id="hb-022",
            quality_baseline=90,
            quality_achieved=90,
        )
        errors = qe.validate()
        assert any("delegate_task_id" in e for e in errors)

    def test_validate_empty_handback_task_id(self):
        """validate() catches empty handback_task_id."""
        qe = QualityEvaluation(
            task_id="qe-023",
            delegate_task_id="del-023",
            handback_task_id="",
            quality_baseline=90,
            quality_achieved=90,
        )
        errors = qe.validate()
        assert any("handback_task_id" in e for e in errors)

    def test_validate_quality_baseline_out_of_range(self):
        """validate() catches quality_baseline > 100."""
        qe = QualityEvaluation(
            task_id="qe-024",
            delegate_task_id="del-024",
            handback_task_id="hb-024",
            quality_baseline=110,
            quality_achieved=90,
        )
        errors = qe.validate()
        assert any("quality_baseline" in e for e in errors)

    def test_validate_quality_achieved_negative(self):
        """validate() catches quality_achieved < 0."""
        qe = QualityEvaluation(
            task_id="qe-025",
            delegate_task_id="del-025",
            handback_task_id="hb-025",
            quality_baseline=90,
            quality_achieved=-1,
        )
        errors = qe.validate()
        assert any("quality_achieved" in e for e in errors)

    def test_validate_quality_score_out_of_range(self):
        """validate() catches quality_score > 100."""
        qe = QualityEvaluation(
            task_id="qe-026",
            delegate_task_id="del-026",
            handback_task_id="hb-026",
            quality_baseline=90,
            quality_achieved=90,
            quality_score=150,
        )
        errors = qe.validate()
        assert any("quality_score" in e for e in errors)

    def test_validate_multiple_errors(self):
        """validate() accumulates all errors."""
        qe = QualityEvaluation(
            task_id="",
            delegate_task_id="",
            handback_task_id="",
            quality_baseline=200,
            quality_achieved=-5,
            quality_score=200,
        )
        errors = qe.validate()
        assert len(errors) >= 4


class TestQualityEvaluationComputeScore:
    """Tests for compute_quality_score() edge cases (lines 120, 137, 141-142)."""

    def test_compute_score_empty_evaluation_results(self):
        """compute_quality_score() returns 0 when evaluation_results is empty (line 120)."""
        qe = QualityEvaluation(
            task_id="qe-030",
            delegate_task_id="del-030",
            handback_task_id="hb-030",
            quality_baseline=90,
            quality_achieved=90,
        )
        score = qe.compute_quality_score()
        assert score == 0

    def test_compute_score_no_acceptance_criteria(self):
        """compute_quality_score() uses only eval results when no acceptance_criteria (line 137)."""
        qe = QualityEvaluation(
            task_id="qe-031",
            delegate_task_id="del-031",
            handback_task_id="hb-031",
            quality_baseline=90,
            quality_achieved=90,
            evaluation_results={"check1": True, "check2": True, "check3": False},
            # No acceptance_criteria_assessment
        )
        score = qe.compute_quality_score()
        # 2/3 = 66% → score should be ~66
        assert score == qe.quality_score
        assert 60 <= score <= 70

    def test_compute_score_with_issues_deduction(self):
        """compute_quality_score() deducts for issues_found (lines 141-142)."""
        qe = QualityEvaluation(
            task_id="qe-032",
            delegate_task_id="del-032",
            handback_task_id="hb-032",
            quality_baseline=90,
            quality_achieved=90,
            evaluation_results={"check1": True, "check2": True},
            issues_found=["issue1", "issue2"],  # 2 issues → 10 point deduction
        )
        score_without_issues = 100  # 2/2 = 100%
        score = qe.compute_quality_score()
        # Should be 100 - 10 = 90
        assert score == 90

    def test_compute_score_max_deduction_cap(self):
        """compute_quality_score() caps issue deduction at 30 points."""
        qe = QualityEvaluation(
            task_id="qe-033",
            delegate_task_id="del-033",
            handback_task_id="hb-033",
            quality_baseline=90,
            quality_achieved=90,
            evaluation_results={f"check{i}": True for i in range(10)},
            issues_found=[f"issue{i}" for i in range(10)],  # 10 issues → max 30 deduction
        )
        score = qe.compute_quality_score()
        # 10/10 = 100, deduction = min(10*5, 30) = 30, final = 70
        assert score == 70

    def test_compute_score_with_acceptance_criteria_and_issues(self):
        """compute_quality_score() combines eval + criteria + issues."""
        qe = QualityEvaluation(
            task_id="qe-034",
            delegate_task_id="del-034",
            handback_task_id="hb-034",
            quality_baseline=90,
            quality_achieved=90,
            evaluation_results={"e1": True, "e2": True},  # 100%
            acceptance_criteria_assessment={"a1": True, "a2": True},  # 100%
            issues_found=["one issue"],  # -5
        )
        score = qe.compute_quality_score()
        # base = 100, criteria = 100, weighted = 70+30 = 100, deduction = 5 → 95
        assert score == 95

    def test_compute_score_no_deduction_without_issues(self):
        """compute_quality_score() doesn't deduct when no issues_found."""
        qe = QualityEvaluation(
            task_id="qe-035",
            delegate_task_id="del-035",
            handback_task_id="hb-035",
            quality_baseline=90,
            quality_achieved=90,
            evaluation_results={"e1": True, "e2": True},
        )
        score = qe.compute_quality_score()
        assert score == 100  # no deduction


# ═══════════════════════════════════════════════════════════════════════════════
# SessionMemory Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestGlobalMemoryManagerDefaultBaseDir:
    """Tests for GlobalMemoryManager with default base_dir (line 96 uncovered)."""

    def test_default_base_dir_is_home_dir(self):
        """GlobalMemoryManager() without args uses ~/.agentic-engineers."""
        gm = GlobalMemoryManager()
        expected = Path(os.path.expanduser("~/.agentic-engineers"))
        assert gm.base_dir == expected

    def test_custom_base_dir(self, tmp_path):
        """GlobalMemoryManager() with explicit base_dir uses that path."""
        gm = GlobalMemoryManager(base_dir=str(tmp_path))
        assert gm.base_dir == tmp_path

    def test_build_global_index_with_empty_dir(self, tmp_path):
        """build_global_index works even with empty base directory."""
        gm = GlobalMemoryManager(base_dir=str(tmp_path))
        index_path = gm.build_global_index()
        assert index_path.exists()
        content = json.loads(index_path.read_text())
        assert isinstance(content, dict)

    def test_build_global_index_writes_file(self, tmp_path):
        """build_global_index writes MEMORY_INDEX.json at base_dir root."""
        gm = GlobalMemoryManager(base_dir=str(tmp_path))
        index_path = gm.build_global_index()
        assert index_path.name == "MEMORY_INDEX.json"
        assert index_path.parent == tmp_path


class TestGlobalMemoryManagerCleanup:
    """Tests for GlobalMemoryManager.cleanup_old_sessions() (lines 127-157)."""

    def test_cleanup_returns_dict(self, tmp_path):
        """cleanup_old_sessions() always returns a dict with required keys."""
        gm = GlobalMemoryManager(base_dir=str(tmp_path))
        result = gm.cleanup_old_sessions(days=30)
        assert "archived_count" in result
        assert "archived_sessions" in result

    def test_cleanup_nonexistent_base_dir(self):
        """cleanup_old_sessions() handles missing base directory gracefully."""
        gm = GlobalMemoryManager(base_dir="/nonexistent/path/xyz123")
        result = gm.cleanup_old_sessions(days=30)
        assert result["archived_count"] == 0
        assert result["archived_sessions"] == []

    def test_cleanup_skips_files(self, tmp_path):
        """cleanup_old_sessions() skips non-directory entries in base_dir."""
        (tmp_path / "not_a_session.txt").write_text("hello")
        gm = GlobalMemoryManager(base_dir=str(tmp_path))
        result = gm.cleanup_old_sessions(days=30)
        assert result["archived_count"] == 0

    def test_cleanup_skips_dirs_without_memory(self, tmp_path):
        """cleanup_old_sessions() skips session dirs without a memory/ subdirectory."""
        (tmp_path / "session-001").mkdir()  # No memory/ subdir
        gm = GlobalMemoryManager(base_dir=str(tmp_path))
        result = gm.cleanup_old_sessions(days=0)  # 0 days means archive everything old
        assert result["archived_count"] == 0

    def test_cleanup_archives_old_sessions(self, tmp_path):
        """cleanup_old_sessions() archives sessions older than threshold."""
        # Create a session with a memory directory
        session_dir = tmp_path / "session-002"
        memory_dir = session_dir / "memory"
        memory_dir.mkdir(parents=True)
        (memory_dir / "data.json").write_text('{"test": true}')

        # Set modification time to 100 days ago
        old_time = (datetime.now() - timedelta(days=100)).timestamp()
        os.utime(str(memory_dir), (old_time, old_time))

        gm = GlobalMemoryManager(base_dir=str(tmp_path))
        result = gm.cleanup_old_sessions(days=30)
        assert result["archived_count"] == 1
        assert "session-002" in result["archived_sessions"]

        # Verify memory was moved to archive
        archive_path = tmp_path / "archive" / "session-002" / "memory"
        assert archive_path.exists()

    def test_cleanup_keeps_recent_sessions(self, tmp_path):
        """cleanup_old_sessions() does not archive recent sessions."""
        session_dir = tmp_path / "session-003"
        memory_dir = session_dir / "memory"
        memory_dir.mkdir(parents=True)
        (memory_dir / "data.json").write_text('{"test": true}')
        # mtime is now (recent), not modified

        gm = GlobalMemoryManager(base_dir=str(tmp_path))
        result = gm.cleanup_old_sessions(days=30)
        assert result["archived_count"] == 0
        assert memory_dir.exists()  # Should still be there

    def test_cleanup_handles_shutil_error_gracefully(self, tmp_path):
        """cleanup_old_sessions() continues when a move fails."""
        session_dir = tmp_path / "session-004"
        memory_dir = session_dir / "memory"
        memory_dir.mkdir(parents=True)

        old_time = (datetime.now() - timedelta(days=100)).timestamp()
        os.utime(str(memory_dir), (old_time, old_time))

        gm = GlobalMemoryManager(base_dir=str(tmp_path))

        # Mock shutil.move to raise an exception
        import src.orchestration.memory.session_memory as sm_module
        original_shutil = sm_module.__dict__.get('shutil')

        with patch("shutil.move", side_effect=OSError("Permission denied")):
            result = gm.cleanup_old_sessions(days=30)
        # Should not raise, just not archive it
        assert isinstance(result, dict)
        assert result["archived_count"] == 0

    def test_cleanup_custom_days_threshold(self, tmp_path):
        """cleanup_old_sessions() respects the days parameter."""
        session_dir = tmp_path / "session-005"
        memory_dir = session_dir / "memory"
        memory_dir.mkdir(parents=True)

        # Set mtime to 10 days ago
        ten_days_ago = (datetime.now() - timedelta(days=10)).timestamp()
        os.utime(str(memory_dir), (ten_days_ago, ten_days_ago))

        gm = GlobalMemoryManager(base_dir=str(tmp_path))

        # With 30-day threshold: should NOT archive (10 days < 30)
        result_30 = gm.cleanup_old_sessions(days=30)
        assert result_30["archived_count"] == 0

    def test_cleanup_multiple_old_sessions(self, tmp_path):
        """cleanup_old_sessions() archives multiple old sessions."""
        old_time = (datetime.now() - timedelta(days=60)).timestamp()

        for i in range(3):
            memory_dir = tmp_path / f"session-{i:03d}" / "memory"
            memory_dir.mkdir(parents=True)
            os.utime(str(memory_dir), (old_time, old_time))

        gm = GlobalMemoryManager(base_dir=str(tmp_path))
        result = gm.cleanup_old_sessions(days=30)
        assert result["archived_count"] == 3
        assert len(result["archived_sessions"]) == 3


class TestSessionMemoryManagerWriteSummary:
    """Additional tests for SessionMemoryManager.write_session_summary()."""

    def test_write_summary_with_all_data(self, tmp_path):
        """write_session_summary() writes a complete summary file."""
        mgr = SessionMemoryManager("test-sess-001", base_dir=str(tmp_path))
        summary_data = {
            "delegates": {"count": 5},
            "handbacks": {"count": 4},
            "memory": {"file_count": 12, "total_size_bytes": 4096},
        }
        path = mgr.write_session_summary(summary_data)
        assert path.exists()
        content = path.read_text()
        assert "test-sess-001" in content
        assert "Delegates" in content
        assert "5" in content
        assert "Handbacks" in content
        assert "4" in content
        assert "Memory Statistics" in content

    def test_write_summary_empty_data(self, tmp_path):
        """write_session_summary() handles empty dict."""
        mgr = SessionMemoryManager("test-sess-002", base_dir=str(tmp_path))
        path = mgr.write_session_summary({})
        assert path.exists()
        content = path.read_text()
        assert "Session Memory Summary" in content
