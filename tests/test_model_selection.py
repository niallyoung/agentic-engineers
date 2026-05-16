# -*- coding: utf-8 -*-
"""
Comprehensive test suite for the Model Selection Optimization Framework.

Tests cover:
  - ComplexityScorer (scoring algorithm, edge cases, calibration)
  - ModelSelector (routing decisions, overrides, cost estimation)
  - CostQualityAnalyzer (efficiency analysis, provisioning detection, outliers)
  - ABTestingFramework (experiment lifecycle, Welch's t-test, early stopping)
  - RecommendationsEngine (daily report, recommendation types, A/B proposals)

Run with:
    pytest tests/test_model_selection.py -v
"""

import math
import tempfile
from pathlib import Path

import pytest

from src.orchestration.models.complexity_scorer import (
    ComplexityLevel,
    ComplexityScorer,
    TaskAttributes,
)
from src.orchestration.models.model_selector import (
    MODEL_COST_MULTIPLIERS,
    ModelSelector,
    ModelTier,
    RoutingDecision,
)
from src.orchestration.models.cost_quality_analyzer import (
    COST_TARGET_PER_QUALITY_POINT,
    CostQualityAnalyzer,
    EfficiencyReport,
)
from src.orchestration.models.ab_testing import (
    ABTestingFramework,
    Experiment,
    ExperimentResult,
    ExperimentStatus,
    _cohens_d,
    _welch_t_test,
)
from src.orchestration.models.recommendations import (
    Recommendation,
    RecommendationsEngine,
    RecommendationType,
)


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def scorer():
    return ComplexityScorer()


@pytest.fixture
def selector():
    return ModelSelector()


@pytest.fixture
def analyzer():
    return CostQualityAnalyzer()


@pytest.fixture
def ab_framework(tmp_path):
    return ABTestingFramework(experiments_dir=str(tmp_path / "experiments"))


@pytest.fixture
def engine():
    return RecommendationsEngine()


def _make_metric(
    role="Engineer",
    model="haiku-4-5",
    quality=88.0,
    cost=0.001,
    tokens_in=500,
    tokens_out=300,
    complexity_score=25.0,
    escalated=False,
    **kwargs,
) -> dict:
    return {
        "role": role,
        "model": model,
        "quality_score": quality,
        "cost": cost,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "complexity_score": complexity_score,
        "escalated": escalated,
        **kwargs,
    }


# ===========================================================================
# ComplexityScorer tests
# ===========================================================================

class TestComplexityScorer:

    def test_trivial_routing_task(self, scorer):
        attrs = TaskAttributes(effort="low", task_type="routing", estimated_tokens=500)
        score, level = scorer.score(attrs)
        assert level == ComplexityLevel.TRIVIAL
        assert score < 20

    def test_low_complexity(self, scorer):
        attrs = TaskAttributes(effort="low", task_type="documentation")
        score, level = scorer.score(attrs)
        assert level in (ComplexityLevel.TRIVIAL, ComplexityLevel.LOW)

    def test_medium_complexity(self, scorer):
        attrs = TaskAttributes(effort="medium", task_type="implementation", estimated_tokens=10_000)
        score, level = scorer.score(attrs)
        assert level in (ComplexityLevel.MEDIUM, ComplexityLevel.HIGH)

    def test_high_complexity_refactor(self, scorer):
        attrs = TaskAttributes(
            effort="high",
            task_type="refactor",
            has_plan=False,
            scope_clarity=0.5,
            num_files_affected=8,
        )
        score, level = scorer.score(attrs)
        assert level in (ComplexityLevel.HIGH, ComplexityLevel.CRITICAL)
        assert score >= 60

    def test_critical_architecture(self, scorer):
        attrs = TaskAttributes(
            effort="max",
            task_type="architecture",
            has_plan=False,
            scope_clarity=0.2,
            is_cross_service=True,
            security_sensitive=True,
            estimated_tokens=80_000,
        )
        score, level = scorer.score(attrs)
        assert level == ComplexityLevel.CRITICAL
        assert score >= 80

    def test_security_sensitive_raises_score(self, scorer):
        base = TaskAttributes(effort="medium", task_type="implementation")
        secure = TaskAttributes(effort="medium", task_type="implementation", security_sensitive=True)
        s_base, _ = scorer.score(base)
        s_secure, _ = scorer.score(secure)
        assert s_secure > s_base

    def test_no_plan_raises_score(self, scorer):
        with_plan = TaskAttributes(effort="medium", has_plan=True)
        without_plan = TaskAttributes(effort="medium", has_plan=False)
        s_with, _ = scorer.score(with_plan)
        s_without, _ = scorer.score(without_plan)
        assert s_without > s_with

    def test_scope_clarity_effect(self, scorer):
        clear = TaskAttributes(effort="medium", scope_clarity=1.0)
        ambiguous = TaskAttributes(effort="medium", scope_clarity=0.0)
        s_clear, _ = scorer.score(clear)
        s_ambiguous, _ = scorer.score(ambiguous)
        assert s_ambiguous > s_clear

    def test_token_thresholds(self, scorer):
        small = TaskAttributes(effort="medium", estimated_tokens=1_000)
        large = TaskAttributes(effort="medium", estimated_tokens=60_000)
        s_small, _ = scorer.score(small)
        s_large, _ = scorer.score(large)
        assert s_large > s_small

    def test_prior_escalations_raise_score(self, scorer):
        no_esc = TaskAttributes(effort="medium", prior_escalation_count=0)
        with_esc = TaskAttributes(effort="medium", prior_escalation_count=3)
        s_no, _ = scorer.score(no_esc)
        s_with, _ = scorer.score(with_esc)
        assert s_with > s_no

    def test_tag_simple_lowers_score(self, scorer):
        base = TaskAttributes(effort="medium")
        tagged = TaskAttributes(effort="medium", tags=["simple"])
        s_base, _ = scorer.score(base)
        s_tagged, _ = scorer.score(tagged)
        assert s_tagged < s_base

    def test_score_clamped_0_100(self, scorer):
        # Extreme attributes should not exceed 100
        extreme = TaskAttributes(
            effort="max",
            task_type="architecture",
            has_plan=False,
            scope_clarity=0.0,
            is_cross_service=True,
            security_sensitive=True,
            estimated_tokens=200_000,
            prior_escalation_count=10,
            num_files_affected=20,
            required_quality_score=99.0,
        )
        score, _ = scorer.score(extreme)
        assert 0.0 <= score <= 100.0

    def test_score_from_dict(self, scorer):
        data = {"effort": "high", "task_type": "refactor", "has_plan": False}
        score, level = scorer.score_from_dict(data)
        assert isinstance(score, float)
        assert isinstance(level, ComplexityLevel)

    def test_describe_output(self, scorer):
        attrs = TaskAttributes(effort="high", security_sensitive=True, has_plan=False)
        score, level = scorer.score(attrs)
        desc = scorer.describe(attrs, score, level)
        assert "security" in desc.lower()
        assert str(score) in desc

    def test_cross_service_raises_score(self, scorer):
        local = TaskAttributes(effort="medium", is_cross_service=False)
        cross = TaskAttributes(effort="medium", is_cross_service=True)
        s_local, _ = scorer.score(local)
        s_cross, _ = scorer.score(cross)
        assert s_cross > s_local


# ===========================================================================
# ModelSelector tests
# ===========================================================================

class TestModelSelector:

    def test_trivial_routes_to_haiku(self, selector):
        attrs = TaskAttributes(effort="low", task_type="routing", estimated_tokens=500)
        decision = selector.select(attrs)
        assert decision.model == ModelTier.HAIKU

    def test_medium_routes_to_sonnet(self, selector):
        attrs = TaskAttributes(effort="medium", task_type="implementation", estimated_tokens=15_000)
        decision = selector.select(attrs)
        assert decision.model == ModelTier.SONNET

    def test_critical_routes_to_opus(self, selector):
        attrs = TaskAttributes(
            effort="max",
            task_type="architecture",
            has_plan=False,
            scope_clarity=0.2,
            estimated_tokens=80_000,
        )
        decision = selector.select(attrs)
        assert decision.model == ModelTier.OPUS

    def test_security_override_forces_opus(self, selector):
        # Even a low-effort task should get Opus if security_sensitive
        attrs = TaskAttributes(effort="low", task_type="routing", security_sensitive=True)
        decision = selector.select(attrs)
        assert decision.model == ModelTier.OPUS
        assert decision.override_applied
        assert "security" in decision.override_reason.lower()

    def test_cross_service_override_forces_sonnet_minimum(self, selector):
        attrs = TaskAttributes(effort="low", task_type="trivial", is_cross_service=True)
        decision = selector.select(attrs)
        assert decision.model in (ModelTier.SONNET, ModelTier.OPUS)
        assert decision.override_applied

    def test_high_quality_requirement_upgrades_tier(self, selector):
        attrs = TaskAttributes(effort="low", task_type="trivial", required_quality_score=96.0)
        decision = selector.select(attrs)
        # Should upgrade from Haiku
        assert decision.model != ModelTier.HAIKU

    def test_decision_has_cost_multiplier(self, selector):
        attrs = TaskAttributes(effort="medium")
        decision = selector.select(attrs)
        assert decision.cost_multiplier > 0
        assert decision.cost_multiplier == MODEL_COST_MULTIPLIERS[decision.model]

    def test_decision_has_quality_baseline(self, selector):
        attrs = TaskAttributes(effort="medium")
        decision = selector.select(attrs)
        assert 0 < decision.quality_baseline <= 100

    def test_select_from_dict(self, selector):
        data = {"effort": "high", "task_type": "refactor", "has_plan": False}
        decision = selector.select_from_dict(data)
        assert isinstance(decision, RoutingDecision)

    def test_estimate_cost_haiku_cheaper(self, selector):
        # Use clearly different token counts to ensure different models are selected
        haiku_attrs = TaskAttributes(effort="low", task_type="routing", estimated_tokens=500)
        sonnet_attrs = TaskAttributes(effort="medium", task_type="implementation", estimated_tokens=20_000)
        cost_haiku = selector.estimate_cost(haiku_attrs)
        cost_sonnet = selector.estimate_cost(sonnet_attrs)
        assert cost_haiku < cost_sonnet

    def test_estimate_cost_no_tokens_returns_zero(self, selector):
        attrs = TaskAttributes(effort="medium")
        assert selector.estimate_cost(attrs) == 0.0

    def test_decision_str_representation(self, selector):
        attrs = TaskAttributes(effort="medium")
        decision = selector.select(attrs)
        s = str(decision)
        assert "Model:" in s
        assert "Cost multiplier" in s


# ===========================================================================
# CostQualityAnalyzer tests
# ===========================================================================

class TestCostQualityAnalyzer:

    def test_empty_metrics_returns_empty_report(self, analyzer):
        analyzer.load([])
        report = analyzer.analyze()
        assert report.total_tasks == 0
        assert report.total_cost == 0.0

    def test_basic_analysis(self, analyzer):
        metrics = [_make_metric() for _ in range(5)]
        analyzer.load(metrics)
        report = analyzer.analyze()
        assert report.total_tasks == 5
        assert "Engineer" in report.role_stats

    def test_cost_per_quality_computed(self, analyzer):
        metrics = [_make_metric(quality=90.0, cost=0.002) for _ in range(3)]
        analyzer.load(metrics)
        report = analyzer.analyze()
        stats = report.role_stats["Engineer"]
        assert stats.cost_per_quality_point > 0

    def test_over_provisioned_detection(self, analyzer):
        # Opus model for trivial task (complexity < 40)
        metrics = [
            _make_metric(model="opus-4-7", complexity_score=15.0)
            for _ in range(3)
        ]
        analyzer.load(metrics)
        report = analyzer.analyze()
        assert len(report.over_provisioned_tasks) > 0

    def test_under_provisioned_detection(self, analyzer):
        # Haiku for high-complexity task
        metrics = [
            _make_metric(model="haiku-4-5", complexity_score=70.0)
            for _ in range(3)
        ]
        analyzer.load(metrics)
        report = analyzer.analyze()
        assert len(report.under_provisioned_tasks) > 0

    def test_sonnet_medium_complexity_not_over_provisioned(self, analyzer):
        metrics = [
            _make_metric(model="sonnet-4-6", complexity_score=45.0)
            for _ in range(3)
        ]
        analyzer.load(metrics)
        report = analyzer.analyze()
        assert len(report.over_provisioned_tasks) == 0

    def test_outlier_detection(self, analyzer):
        # Need >=3 samples; use extreme spread so outlier is >3σ
        metrics = [_make_metric(tokens_in=100, tokens_out=100) for _ in range(9)]
        metrics.append(_make_metric(tokens_in=100_000, tokens_out=100_000))
        analyzer.load(metrics)
        report = analyzer.analyze()
        assert len(report.outliers) >= 1

    def test_efficiency_label_good(self, analyzer):
        # Low cost/quality → "good"
        metrics = [_make_metric(quality=95.0, cost=0.0001) for _ in range(3)]
        analyzer.load(metrics)
        report = analyzer.analyze()
        stats = report.role_stats["Engineer"]
        assert stats.efficiency == "good"

    def test_efficiency_label_poor(self, analyzer):
        # Very high cost/quality → "poor"
        metrics = [_make_metric(quality=50.0, cost=0.5) for _ in range(3)]
        analyzer.load(metrics)
        report = analyzer.analyze()
        stats = report.role_stats["Engineer"]
        assert stats.efficiency == "poor"

    def test_escalation_rate_computed(self, analyzer):
        metrics = [_make_metric(escalated=(i % 2 == 0)) for i in range(10)]
        analyzer.load(metrics)
        report = analyzer.analyze()
        stats = report.role_stats["Engineer"]
        assert 0.4 <= stats.escalation_rate <= 0.6

    def test_compare_models_haiku_cheaper(self):
        result = CostQualityAnalyzer.compare_models(
            tokens=5_000,
            quality_a=82.0,
            quality_b=93.0,
            model_a=ModelTier.HAIKU,
            model_b=ModelTier.SONNET,
        )
        assert result["model_a"]["cost"] < result["model_b"]["cost"]

    def test_compare_models_winner(self):
        result = CostQualityAnalyzer.compare_models(
            tokens=5_000,
            quality_a=82.0,
            quality_b=93.0,
            model_a=ModelTier.HAIKU,
            model_b=ModelTier.SONNET,
        )
        assert result["winner"] in ("haiku-4-5", "sonnet-4-6")

    def test_report_summary_string(self, analyzer):
        metrics = [_make_metric() for _ in range(5)]
        analyzer.load(metrics)
        report = analyzer.analyze()
        summary = report.summary()
        assert "Engineer" in summary
        assert "Total tasks" in summary


# ===========================================================================
# ABTestingFramework tests
# ===========================================================================

class TestABTestingFramework:

    def test_create_experiment(self, ab_framework):
        exp_id = ab_framework.create_experiment(
            name="test-exp",
            hypothesis="Haiku is cheaper with same quality",
            control={"model": "sonnet-4-6"},
            variant={"model": "haiku-4-5"},
        )
        assert exp_id is not None
        exp = ab_framework.load_experiment(exp_id)
        assert exp is not None
        assert exp.status == ExperimentStatus.DRAFT.value

    def test_start_experiment(self, ab_framework):
        exp_id = ab_framework.create_experiment(
            name="start-test", hypothesis="h",
            control={"model": "sonnet-4-6"}, variant={"model": "haiku-4-5"},
        )
        assert ab_framework.start_experiment(exp_id)
        exp = ab_framework.load_experiment(exp_id)
        assert exp.status == ExperimentStatus.RUNNING.value
        assert exp.start_date is not None

    def test_cannot_start_running_experiment(self, ab_framework):
        exp_id = ab_framework.create_experiment(
            name="double-start", hypothesis="h",
            control={}, variant={},
        )
        ab_framework.start_experiment(exp_id)
        assert not ab_framework.start_experiment(exp_id)

    def test_analyze_insufficient_data(self, ab_framework):
        exp_id = ab_framework.create_experiment(
            name="small-exp", hypothesis="h",
            control={}, variant={},
        )
        result = ab_framework.analyze_experiment(
            exp_id,
            control_metrics=[_make_metric() for _ in range(5)],
            variant_metrics=[_make_metric() for _ in range(5)],
        )
        assert result.status == "insufficient_data"

    def test_analyze_sufficient_data_significant(self, ab_framework):
        exp_id = ab_framework.create_experiment(
            name="sig-exp", hypothesis="h",
            control={"model": "sonnet-4-6"}, variant={"model": "haiku-4-5"},
        )
        # Control: quality 70, Variant: quality 90 → should be significant
        ctrl = [_make_metric(quality=70.0, cost=0.003) for _ in range(50)]
        var = [_make_metric(quality=90.0, cost=0.001) for _ in range(50)]
        result = ab_framework.analyze_experiment(exp_id, ctrl, var)
        assert result.status == "ok"
        assert result.significant
        assert result.variant_better

    def test_analyze_no_significant_difference(self, ab_framework):
        exp_id = ab_framework.create_experiment(
            name="no-diff-exp", hypothesis="h",
            control={}, variant={},
        )
        # Same quality for both groups
        ctrl = [_make_metric(quality=88.0) for _ in range(50)]
        var = [_make_metric(quality=88.0) for _ in range(50)]
        result = ab_framework.analyze_experiment(exp_id, ctrl, var)
        assert not result.significant

    def test_early_stop_signal(self, ab_framework):
        exp_id = ab_framework.create_experiment(
            name="early-stop", hypothesis="h",
            control={"model": "sonnet-4-6"}, variant={"model": "haiku-4-5"},
        )
        # Very strong signal
        ctrl = [_make_metric(quality=60.0, cost=0.005) for _ in range(100)]
        var = [_make_metric(quality=95.0, cost=0.001) for _ in range(100)]
        result = ab_framework.analyze_experiment(exp_id, ctrl, var)
        assert result.early_stop_signal

    def test_regression_signal(self, ab_framework):
        exp_id = ab_framework.create_experiment(
            name="regression", hypothesis="h",
            control={}, variant={},
        )
        # Variant much worse
        ctrl = [_make_metric(quality=95.0) for _ in range(100)]
        var = [_make_metric(quality=60.0) for _ in range(100)]
        result = ab_framework.analyze_experiment(exp_id, ctrl, var)
        assert result.regression_signal

    def test_stop_experiment(self, ab_framework):
        exp_id = ab_framework.create_experiment(
            name="stop-exp", hypothesis="h",
            control={"model": "sonnet-4-6"}, variant={"model": "haiku-4-5"},
        )
        ab_framework.start_experiment(exp_id)
        ctrl = [_make_metric(quality=70.0, cost=0.003) for _ in range(50)]
        var = [_make_metric(quality=90.0, cost=0.001) for _ in range(50)]
        # Inject metrics by monkey-patching _load_group_metrics
        ab_framework._load_group_metrics = lambda eid, g: ctrl if g == "control" else var
        assert ab_framework.stop_experiment(exp_id)
        exp = ab_framework.load_experiment(exp_id)
        assert exp.status == ExperimentStatus.COMPLETED.value

    def test_list_experiments(self, ab_framework):
        for i in range(3):
            ab_framework.create_experiment(
                name=f"exp-{i}", hypothesis="h", control={}, variant={}
            )
        exps = ab_framework.list_experiments()
        assert len(exps) == 3

    def test_list_experiments_filtered_by_status(self, ab_framework):
        exp_id = ab_framework.create_experiment(
            name="running-exp", hypothesis="h", control={}, variant={}
        )
        ab_framework.start_experiment(exp_id)
        ab_framework.create_experiment(
            name="draft-exp", hypothesis="h", control={}, variant={}
        )
        running = ab_framework.list_experiments(status="running")
        assert len(running) == 1

    def test_generate_report_insufficient_data(self, ab_framework):
        exp_id = ab_framework.create_experiment(
            name="report-exp", hypothesis="h", control={}, variant={}
        )
        result = ExperimentResult(
            control_count=5, variant_count=5,
            control_avg_quality=0, variant_avg_quality=0,
            control_avg_cost=0, variant_avg_cost=0,
            quality_improvement_pct=0, cost_reduction_pct=0,
            p_value=1.0, significant=False, cohens_d=0, power=0,
            variant_better=False, early_stop_signal=False,
            regression_signal=False, status="insufficient_data",
        )
        report = ab_framework.generate_report(exp_id, result)
        assert "Insufficient" in report

    def test_cohens_d_zero_for_identical(self):
        a = [85.0] * 20
        b = [85.0] * 20
        assert _cohens_d(a, b) == 0.0

    def test_cohens_d_large_for_different(self):
        import random
        random.seed(42)
        a = [60.0 + random.gauss(0, 1) for _ in range(50)]
        b = [90.0 + random.gauss(0, 1) for _ in range(50)]
        d = _cohens_d(a, b)
        assert abs(d) > 1.0  # large effect

    def test_welch_t_test_identical_groups(self):
        a = [85.0 + i * 0.1 for i in range(30)]
        b = [85.0 + i * 0.1 for i in range(30)]
        t, p = _welch_t_test(a, b)
        assert p > 0.05  # not significant

    def test_welch_t_test_very_different_groups(self):
        a = [60.0] * 50
        b = [90.0] * 50
        t, p = _welch_t_test(a, b)
        assert p < 0.001  # highly significant


# ===========================================================================
# RecommendationsEngine tests
# ===========================================================================

class TestRecommendationsEngine:

    def test_empty_metrics_no_recommendations(self, engine):
        engine.load_metrics([])
        report = engine.generate_daily_report()
        assert report["recommendations"] == []

    def test_over_provisioned_generates_downgrade(self, engine):
        # Opus for trivial tasks → downgrade recommendation
        metrics = [
            _make_metric(model="opus-4-7", complexity_score=10.0, quality=95.0, cost=0.01)
            for _ in range(10)
        ]
        engine.load_metrics(metrics)
        report = engine.generate_daily_report()
        types = [r.type for r in report["recommendations"]]
        assert RecommendationType.DOWNGRADE in types

    def test_high_escalation_generates_upgrade(self, engine):
        metrics = [
            _make_metric(
                model="haiku-4-5",
                quality=75.0,
                cost=0.001,
                escalated=(i % 5 == 0),  # 20% escalation rate
            )
            for i in range(20)
        ]
        engine.load_metrics(metrics)
        report = engine.generate_daily_report()
        types = [r.type for r in report["recommendations"]]
        assert RecommendationType.UPGRADE in types

    def test_recommendations_have_confidence(self, engine):
        metrics = [
            _make_metric(model="opus-4-7", complexity_score=10.0, quality=95.0, cost=0.01)
            for _ in range(10)
        ]
        engine.load_metrics(metrics)
        report = engine.generate_daily_report()
        for rec in report["recommendations"]:
            assert 0.0 <= rec.confidence <= 1.0

    def test_ab_test_proposals_generated(self, engine):
        metrics = [
            _make_metric(model="opus-4-7", complexity_score=10.0, quality=95.0, cost=0.01)
            for _ in range(10)
        ]
        engine.load_metrics(metrics)
        report = engine.generate_daily_report()
        assert len(report["ab_test_proposals"]) > 0

    def test_recommendations_sorted_by_priority(self, engine):
        metrics = (
            [_make_metric(model="opus-4-7", complexity_score=10.0, cost=0.01) for _ in range(10)]
            + [_make_metric(model="haiku-4-5", quality=70.0, escalated=True) for _ in range(10)]
        )
        engine.load_metrics(metrics)
        report = engine.generate_daily_report()
        recs = report["recommendations"]
        priorities = [r.priority for r in recs]
        assert priorities == sorted(priorities)

    def test_summary_string_generated(self, engine):
        metrics = [_make_metric() for _ in range(5)]
        engine.load_metrics(metrics)
        report = engine.generate_daily_report()
        assert isinstance(report["summary"], str)
        assert len(report["summary"]) > 0

    def test_recommend_for_role(self, engine):
        metrics = [
            _make_metric(role="Senior Engineer", model="opus-4-7", complexity_score=10.0, cost=0.01)
            for _ in range(10)
        ]
        recs = engine.recommend_for_role("Senior Engineer", "opus-4-7", metrics)
        assert isinstance(recs, list)

    def test_cheaper_model_haiku_from_sonnet(self):
        result = RecommendationsEngine._cheaper_model("sonnet-4-6")
        assert result == ModelTier.HAIKU.value

    def test_cheaper_model_sonnet_from_opus(self):
        result = RecommendationsEngine._cheaper_model("opus-4-7")
        assert result == ModelTier.SONNET.value

    def test_better_model_sonnet_from_haiku(self):
        result = RecommendationsEngine._better_model("haiku-4-5")
        assert result == ModelTier.SONNET.value

    def test_better_model_opus_from_sonnet(self):
        result = RecommendationsEngine._better_model("sonnet-4-6")
        assert result == ModelTier.OPUS.value
