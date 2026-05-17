# -*- coding: utf-8 -*-
"""
Tests for CostOptimizer.

Coverage: opportunity detection (downgrade, upgrade, parallelization, caching,
effort reduction), report generation, effectiveness tracking.
"""

import pytest
from src.orchestration.cost.cost_optimizer import (
    CostOptimizer,
    OptimizationOpportunity,
    OptimizationReport,
    OpportunityType,
    RiskLevel,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def optimizer():
    return CostOptimizer()


def make_metric(
    role="engineer",
    model="opus-4-7",
    complexity_score=20.0,
    quality_score=95.0,
    cost=0.50,
    tokens_in=1000,
    tokens_out=500,
    task_type="implementation",
    escalated=False,
    effort="medium",
    duration_ms=3000,
):
    return {
        "role": role,
        "model": model,
        "complexity_score": complexity_score,
        "quality_score": quality_score,
        "cost": cost,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "task_type": task_type,
        "escalated": escalated,
        "effort": effort,
        "duration_ms": duration_ms,
    }


# ---------------------------------------------------------------------------
# Empty / edge case tests
# ---------------------------------------------------------------------------

class TestCostOptimizerEmpty:
    def test_empty_metrics_returns_empty_report(self, optimizer):
        report = optimizer.analyze()
        assert report.total_tasks_analyzed == 0
        assert report.opportunities == []
        assert report.estimated_total_savings_pct == 0.0

    def test_empty_metrics_quality_maintained(self, optimizer):
        report = optimizer.analyze()
        assert report.quality_maintained is True


# ---------------------------------------------------------------------------
# Model downgrade opportunity tests
# ---------------------------------------------------------------------------

class TestModelDowngradeOpportunities:
    def test_opus_for_low_complexity_detected(self, optimizer):
        metrics = [make_metric(model="opus-4-7", complexity_score=15.0) for _ in range(5)]
        optimizer.load(metrics)
        report = optimizer.analyze()
        downgrade_opps = report.by_type(OpportunityType.MODEL_DOWNGRADE)
        assert len(downgrade_opps) >= 1
        assert any("Opus" in o.description or "opus" in o.description.lower() for o in downgrade_opps)

    def test_opus_downgrade_has_positive_savings(self, optimizer):
        metrics = [make_metric(model="opus-4-7", complexity_score=10.0) for _ in range(3)]
        optimizer.load(metrics)
        report = optimizer.analyze()
        downgrade_opps = report.by_type(OpportunityType.MODEL_DOWNGRADE)
        for opp in downgrade_opps:
            assert opp.estimated_savings_pct > 0

    def test_sonnet_for_trivial_detected(self, optimizer):
        metrics = [make_metric(model="sonnet-4-6", complexity_score=5.0) for _ in range(4)]
        optimizer.load(metrics)
        report = optimizer.analyze()
        downgrade_opps = report.by_type(OpportunityType.MODEL_DOWNGRADE)
        assert len(downgrade_opps) >= 1

    def test_appropriate_model_no_downgrade(self, optimizer):
        # Sonnet for medium complexity — no downgrade needed
        metrics = [make_metric(model="sonnet-4-6", complexity_score=50.0) for _ in range(5)]
        optimizer.load(metrics)
        report = optimizer.analyze()
        downgrade_opps = report.by_type(OpportunityType.MODEL_DOWNGRADE)
        assert len(downgrade_opps) == 0

    def test_downgrade_confidence_scales_with_count(self, optimizer):
        metrics_few = [make_metric(model="opus-4-7", complexity_score=10.0) for _ in range(2)]
        metrics_many = [make_metric(model="opus-4-7", complexity_score=10.0) for _ in range(20)]
        optimizer.load(metrics_few)
        report_few = optimizer.analyze()
        optimizer.load(metrics_many)
        report_many = optimizer.analyze()
        opps_few = report_few.by_type(OpportunityType.MODEL_DOWNGRADE)
        opps_many = report_many.by_type(OpportunityType.MODEL_DOWNGRADE)
        if opps_few and opps_many:
            assert opps_many[0].confidence >= opps_few[0].confidence


# ---------------------------------------------------------------------------
# Model upgrade opportunity tests
# ---------------------------------------------------------------------------

class TestModelUpgradeOpportunities:
    def test_high_escalation_triggers_upgrade(self, optimizer):
        metrics = [
            make_metric(model="haiku-4-5", escalated=(i % 5 == 0))
            for i in range(10)
        ]
        # 2/10 = 20% escalation rate > 15% threshold
        optimizer.load(metrics)
        report = optimizer.analyze()
        upgrade_opps = report.by_type(OpportunityType.MODEL_UPGRADE)
        assert len(upgrade_opps) >= 1

    def test_low_escalation_no_upgrade(self, optimizer):
        metrics = [make_metric(model="sonnet-4-6", escalated=False) for _ in range(10)]
        optimizer.load(metrics)
        report = optimizer.analyze()
        upgrade_opps = report.by_type(OpportunityType.MODEL_UPGRADE)
        assert len(upgrade_opps) == 0


# ---------------------------------------------------------------------------
# Parallelization opportunity tests
# ---------------------------------------------------------------------------

class TestParallelizationOpportunities:
    def test_repeated_slow_tasks_flagged(self, optimizer):
        metrics = [
            make_metric(task_type="slow_review", duration_ms=10000)
            for _ in range(5)
        ]
        optimizer.load(metrics)
        report = optimizer.analyze()
        parallel_opps = report.by_type(OpportunityType.PARALLELIZATION)
        assert len(parallel_opps) >= 1

    def test_fast_tasks_not_flagged(self, optimizer):
        metrics = [
            make_metric(task_type="quick_check", duration_ms=1000)
            for _ in range(5)
        ]
        optimizer.load(metrics)
        report = optimizer.analyze()
        parallel_opps = report.by_type(OpportunityType.PARALLELIZATION)
        assert len(parallel_opps) == 0

    def test_parallelization_low_risk(self, optimizer):
        metrics = [make_metric(task_type="review", duration_ms=8000) for _ in range(4)]
        optimizer.load(metrics)
        report = optimizer.analyze()
        parallel_opps = report.by_type(OpportunityType.PARALLELIZATION)
        for opp in parallel_opps:
            assert opp.risk == RiskLevel.LOW


# ---------------------------------------------------------------------------
# Caching opportunity tests
# ---------------------------------------------------------------------------

class TestCachingOpportunities:
    def test_repeated_task_type_flagged(self, optimizer):
        # 9/10 tasks same type = 90% repetition rate
        metrics = [make_metric(task_type="routing") for _ in range(9)]
        metrics.append(make_metric(task_type="other"))
        optimizer.load(metrics)
        report = optimizer.analyze()
        cache_opps = report.by_type(OpportunityType.CACHING)
        assert len(cache_opps) >= 1

    def test_diverse_tasks_no_caching(self, optimizer):
        metrics = [make_metric(task_type=f"type_{i}") for i in range(10)]
        optimizer.load(metrics)
        report = optimizer.analyze()
        cache_opps = report.by_type(OpportunityType.CACHING)
        assert len(cache_opps) == 0


# ---------------------------------------------------------------------------
# Effort reduction tests
# ---------------------------------------------------------------------------

class TestEffortReductionOpportunities:
    def test_high_effort_low_complexity_flagged(self, optimizer):
        metrics = [
            make_metric(effort="high", complexity_score=10.0) for _ in range(5)
        ]
        optimizer.load(metrics)
        report = optimizer.analyze()
        effort_opps = report.by_type(OpportunityType.EFFORT_REDUCTION)
        assert len(effort_opps) >= 1

    def test_appropriate_effort_not_flagged(self, optimizer):
        metrics = [make_metric(effort="medium", complexity_score=50.0) for _ in range(5)]
        optimizer.load(metrics)
        report = optimizer.analyze()
        effort_opps = report.by_type(OpportunityType.EFFORT_REDUCTION)
        assert len(effort_opps) == 0


# ---------------------------------------------------------------------------
# Report and effectiveness tests
# ---------------------------------------------------------------------------

class TestOptimizationReport:
    def test_report_has_date(self, optimizer):
        optimizer.load([make_metric()])
        report = optimizer.analyze(date="2026-05-17")
        assert report.date == "2026-05-17"

    def test_report_total_cost(self, optimizer):
        metrics = [make_metric(cost=0.10) for _ in range(5)]
        optimizer.load(metrics)
        report = optimizer.analyze()
        assert report.total_cost_analyzed == pytest.approx(0.50)

    def test_report_summary_renders(self, optimizer):
        optimizer.load([make_metric()])
        report = optimizer.analyze()
        text = report.summary()
        assert "Cost Optimization Report" in text

    def test_high_priority_filter(self, optimizer):
        metrics = [make_metric(model="opus-4-7", complexity_score=5.0) for _ in range(10)]
        optimizer.load(metrics)
        report = optimizer.analyze()
        hp = report.high_priority()
        assert all(o.priority <= 2 for o in hp)

    def test_opportunity_impact_score(self):
        opp = OptimizationOpportunity(
            type=OpportunityType.MODEL_DOWNGRADE,
            role="engineer",
            description="test",
            estimated_savings_pct=20.0,
            estimated_quality_impact=-2.0,
            confidence=0.80,
            risk=RiskLevel.LOW,
            priority=1,
            affected_tasks=5,
        )
        assert opp.impact_score() == pytest.approx(20.0 * 0.80 * 1.0)

    def test_effectiveness_tracking(self, optimizer):
        optimizer.record_outcome(OpportunityType.MODEL_DOWNGRADE, "engineer", "pass", 15.0)
        optimizer.record_outcome(OpportunityType.MODEL_DOWNGRADE, "engineer", "fail", 0.0)
        summary = optimizer.get_effectiveness_summary()
        assert summary["total"] == 2
        assert summary["pass_rate"] == pytest.approx(0.5)
        assert summary["avg_savings_pct"] == pytest.approx(7.5)

    def test_effectiveness_empty(self, optimizer):
        summary = optimizer.get_effectiveness_summary()
        assert summary["total"] == 0
