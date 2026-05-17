# -*- coding: utf-8 -*-
"""
Tests for CostAwareRouter.

Coverage: routing decisions, budget enforcement, security overrides,
fallback behavior, spend tracking, efficiency metrics.
"""

import pytest
from src.orchestration.cost.cost_aware_router import (
    CostAwareRouter,
    CostBudget,
    RoutingCandidate,
    RoutingResult,
    MODEL_COST_MULTIPLIERS,
    MODEL_QUALITY_BASELINES,
    BASE_COST_PER_TOKEN,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def router():
    return CostAwareRouter(quality_threshold=90.0)


@pytest.fixture
def candidates():
    return [
        {"agent": "engineer", "role": "engineer", "model": "haiku-4-5"},
        {"agent": "senior_engineer", "role": "senior_engineer", "model": "sonnet-4-6"},
        {"agent": "lead_engineer", "role": "lead_engineer", "model": "opus-4-7"},
    ]


# ---------------------------------------------------------------------------
# CostBudget tests
# ---------------------------------------------------------------------------

class TestCostBudget:
    def test_unlimited_budget_has_capacity(self):
        budget = CostBudget()
        assert budget.has_capacity(1_000_000.0)

    def test_budget_blocks_when_exceeded(self):
        budget = CostBudget(daily_limit=1.0, spent_today=0.95)
        assert not budget.has_capacity(0.10)

    def test_budget_allows_when_within_limit(self):
        budget = CostBudget(daily_limit=1.0, spent_today=0.50)
        assert budget.has_capacity(0.40)

    def test_record_spend_accumulates(self):
        budget = CostBudget(daily_limit=5.0)
        budget.record_spend(1.0)
        budget.record_spend(2.0)
        assert budget.spent_today == pytest.approx(3.0)

    def test_remaining_daily(self):
        budget = CostBudget(daily_limit=10.0, spent_today=3.0)
        assert budget.remaining_daily() == pytest.approx(7.0)

    def test_utilization_pct(self):
        budget = CostBudget(daily_limit=10.0, spent_today=5.0)
        assert budget.utilization_pct() == pytest.approx(50.0)

    def test_unlimited_budget_utilization_is_zero(self):
        budget = CostBudget()
        assert budget.utilization_pct() == 0.0

    def test_weekly_limit_enforced(self):
        budget = CostBudget(weekly_limit=5.0, spent_this_week=4.9)
        assert not budget.has_capacity(0.2)


# ---------------------------------------------------------------------------
# CostAwareRouter routing tests
# ---------------------------------------------------------------------------

class TestCostAwareRouterRouting:
    def test_selects_cheapest_viable_candidate(self, router, candidates):
        result = router.route("task-001", candidates, estimated_tokens=1000)
        assert result.selected is not None
        # Haiku is cheapest and quality 82 < 90 threshold, so should pick Sonnet
        assert result.selected.model == "sonnet-4-6"

    def test_returns_routing_result(self, router, candidates):
        result = router.route("task-001", candidates, estimated_tokens=1000)
        assert isinstance(result, RoutingResult)
        assert result.task_id == "task-001"

    def test_all_candidates_scored(self, router, candidates):
        result = router.route("task-001", candidates, estimated_tokens=1000)
        assert len(result.all_candidates) == 3

    def test_quality_threshold_filters_haiku(self, router, candidates):
        # Default threshold 90.0; Haiku baseline is 82.0 — should be excluded
        result = router.route("task-001", candidates, estimated_tokens=1000)
        selected_models = {c.model for c in result.all_candidates if c.model == "haiku-4-5"}
        haiku = next(c for c in result.all_candidates if c.model == "haiku-4-5")
        assert haiku.quality_score < 90.0

    def test_low_threshold_selects_haiku(self, candidates):
        router = CostAwareRouter(quality_threshold=80.0)
        result = router.route("task-001", candidates, estimated_tokens=1000)
        assert result.selected.model == "haiku-4-5"

    def test_security_sensitive_forces_opus(self, router, candidates):
        result = router.route(
            "task-sec", candidates, estimated_tokens=1000, security_sensitive=True
        )
        assert result.selected.model == "opus-4-7"

    def test_required_quality_override(self, router, candidates):
        # Require 95+ quality — only Opus qualifies
        result = router.route(
            "task-hq", candidates, estimated_tokens=1000, required_quality=95.0
        )
        assert result.selected.model == "opus-4-7"

    def test_fallback_when_no_viable_candidate(self, router):
        # All candidates below threshold
        low_quality_candidates = [
            {"agent": "eng", "role": "engineer", "model": "haiku-4-5"},
        ]
        result = router.route(
            "task-fb", low_quality_candidates, estimated_tokens=1000, required_quality=99.0
        )
        assert result.fallback_used is True
        assert result.selected is not None  # Best available

    def test_empty_candidates_returns_no_selection(self, router):
        result = router.route("task-empty", [], estimated_tokens=1000)
        assert result.selected is None

    def test_cost_calculation_correct(self, router):
        candidates = [{"agent": "eng", "role": "engineer", "model": "sonnet-4-6"}]
        result = router.route("task-cost", candidates, estimated_tokens=2000)
        expected = 2000 * BASE_COST_PER_TOKEN * MODEL_COST_MULTIPLIERS["sonnet-4-6"]
        assert result.selected.estimated_cost == pytest.approx(expected)

    def test_routing_history_recorded(self, router, candidates):
        router.route("task-001", candidates)
        router.route("task-002", candidates)
        history = router.get_routing_history()
        assert len(history) == 2

    def test_spend_by_agent_tracked(self, router, candidates):
        router.route("task-001", candidates, estimated_tokens=1000)
        spend = router.get_spend_by_agent()
        assert len(spend) > 0

    def test_spend_by_model_tracked(self, router, candidates):
        router.route("task-001", candidates, estimated_tokens=1000)
        spend = router.get_spend_by_model()
        assert "sonnet-4-6" in spend

    def test_clear_history(self, router, candidates):
        router.route("task-001", candidates)
        router.clear_history()
        assert router.get_routing_history() == []
        assert router.get_spend_by_agent() == {}


# ---------------------------------------------------------------------------
# Budget enforcement tests
# ---------------------------------------------------------------------------

class TestBudgetEnforcement:
    def test_agent_budget_blocks_routing(self):
        router = CostAwareRouter(quality_threshold=80.0)
        router.set_budget("engineer", daily_limit=0.0001)  # Tiny budget
        candidates = [
            {"agent": "engineer", "role": "engineer", "model": "haiku-4-5"},
            {"agent": "senior_engineer", "role": "senior_engineer", "model": "sonnet-4-6"},
        ]
        result = router.route("task-001", candidates, estimated_tokens=10000)
        # Engineer should be blocked by budget; senior_engineer selected
        assert result.selected.agent == "senior_engineer"

    def test_global_budget_blocks_all(self):
        router = CostAwareRouter(quality_threshold=80.0)
        router.set_global_budget(daily_limit=0.0001)
        candidates = [
            {"agent": "eng", "role": "engineer", "model": "haiku-4-5"},
        ]
        result = router.route("task-001", candidates, estimated_tokens=10000)
        # Fallback used since global budget exceeded
        assert result.fallback_used is True

    def test_budget_get_returns_unlimited_by_default(self):
        router = CostAwareRouter()
        budget = router.get_budget("nonexistent_agent")
        assert budget.daily_limit == float("inf")


# ---------------------------------------------------------------------------
# Efficiency metrics tests
# ---------------------------------------------------------------------------

class TestEfficiencyMetrics:
    def test_efficiency_metrics_empty(self):
        router = CostAwareRouter()
        metrics = router.get_efficiency_metrics()
        assert metrics["total_tasks"] == 0

    def test_efficiency_metrics_after_routing(self):
        router = CostAwareRouter(quality_threshold=80.0)
        candidates = [{"agent": "eng", "role": "engineer", "model": "haiku-4-5"}]
        router.route("t1", candidates, estimated_tokens=1000)
        router.route("t2", candidates, estimated_tokens=2000)
        metrics = router.get_efficiency_metrics()
        assert metrics["total_tasks"] == 2
        assert metrics["total_cost"] > 0
        assert metrics["avg_quality"] > 0
        assert metrics["fallback_rate"] == 0.0
