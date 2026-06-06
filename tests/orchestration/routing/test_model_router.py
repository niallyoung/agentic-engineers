"""Tests for src/orchestration/routing/model_router.py."""

from __future__ import annotations

import pytest

from src.orchestration.routing import (
    ModelRouter,
    RoutingDecision,
    RoutingRule,
    load_default_router,
)
from src.orchestration.routing.model_router import _always, load_budgets


# ---------------------------------------------------------------------------
# Default router behavior
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def router() -> ModelRouter:
    return load_default_router()


class TestDefaultRouting:
    def test_security_task_routes_to_security_engineer(self, router):
        d = router.route({"task_type": "security"})
        assert d.role == "security_engineer"
        assert d.model == "claude-opus"
        assert d.effort == "max"
        assert d.budget == 5000

    def test_security_scope_field_routes_to_security_engineer(self, router):
        d = router.route({"task_type": "bug_fix", "security_scope": "auth"})
        assert d.role == "security_engineer"
        assert d.rule_name == "security_first"

    def test_architecture_routes_to_principal(self, router):
        d = router.route({"task_type": "architecture"})
        assert d.role == "principal_engineer"
        assert d.model == "claude-opus"

    def test_approval_gate_principal_routes_to_principal(self, router):
        d = router.route({"task_type": "bug_fix", "approval_gate": "principal_engineer"})
        assert d.role == "principal_engineer"

    def test_code_review_routes_to_lead(self, router):
        d = router.route({"task_type": "code_review"})
        assert d.role == "lead_engineer"
        assert d.model == "claude-sonnet"
        assert d.budget == 2500

    def test_quality_gate_routes_to_qe(self, router):
        d = router.route({"task_type": "quality_gate"})
        assert d.role == "quality_engineer"
        assert d.budget == 1000

    def test_cost_analysis_routes_to_model_engineer(self, router):
        d = router.route({"task_type": "cost_analysis"})
        assert d.role == "model_engineer"

    def test_complex_complexity_routes_to_senior(self, router):
        d = router.route({"task_type": "implementation", "estimated_complexity": "high"})
        assert d.role == "senior_engineer"

    def test_orchestration_routes_to_haiku_orchestrator(self, router):
        d = router.route({"task_type": "orchestration"})
        assert d.role == "general_orchestrator"
        assert d.model == "claude-haiku"
        assert d.budget == 500

    def test_default_fallback_to_engineer_haiku(self, router):
        d = router.route({"task_type": "bug_fix", "scope": "Tiny pagination fix"})
        assert d.role == "engineer"
        assert d.model == "claude-haiku"
        assert d.effort == "high"
        assert d.budget == 1500
        assert d.rule_name == "fallback_engineer"

    def test_empty_task_uses_fallback(self, router):
        d = router.route({})
        assert d.role == "engineer"

    def test_unknown_task_type_uses_fallback(self, router):
        d = router.route({"task_type": "asdf-not-a-known-type"})
        assert d.role == "engineer"


class TestPriorityOrder:
    def test_security_beats_architecture(self, router):
        d = router.route({"task_type": "architecture", "security_scope": "auth"})
        assert d.role == "security_engineer"

    def test_security_beats_code_review(self, router):
        d = router.route({"task_type": "code_review", "security_scope": "crypto"})
        assert d.role == "security_engineer"

    def test_review_beats_complexity(self, router):
        d = router.route({"task_type": "code_review", "estimated_complexity": "high"})
        assert d.role == "lead_engineer"


# ---------------------------------------------------------------------------
# Constructor + API contracts
# ---------------------------------------------------------------------------

class TestModelRouterContracts:
    def test_requires_at_least_one_rule(self):
        with pytest.raises(ValueError, match="at least one rule"):
            ModelRouter(rules=[], budgets={})

    def test_requires_fallback_rule(self):
        rule = RoutingRule(
            name="only", role="engineer", model="claude-haiku", effort="high",
            priority_rank=1, rationale="x",
            match=lambda t: t.get("x") == 1,
        )
        with pytest.raises(ValueError, match="fallback"):
            ModelRouter(rules=[rule], budgets={})

    def test_route_rejects_non_dict(self, router):
        with pytest.raises(TypeError):
            router.route("not a dict")  # type: ignore[arg-type]

    def test_routing_decision_as_dict_roundtrips(self, router):
        d = router.route({})
        out = d.as_dict()
        assert out["role"] == d.role
        assert out["budget"] == d.budget
        assert set(out.keys()) == {"role", "model", "effort", "budget", "rule_name", "rationale"}

    def test_matcher_exception_treated_as_no_match(self):
        bad = RoutingRule(
            name="bad", role="engineer", model="claude-haiku", effort="high",
            priority_rank=1, rationale="x",
            match=lambda t: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        fallback = RoutingRule(
            name="fallback", role="engineer", model="claude-haiku", effort="high",
            priority_rank=999, rationale="x", match=_always,
        )
        r = ModelRouter(rules=[bad, fallback], budgets={"engineer": 1500})
        d = r.route({})
        assert d.rule_name == "fallback"

    def test_unknown_role_gets_default_budget(self):
        rule = RoutingRule(
            name="weird", role="weird_role", model="claude-haiku", effort="high",
            priority_rank=1, rationale="x", match=_always,
        )
        r = ModelRouter(rules=[rule], budgets={})
        d = r.route({})
        assert d.budget == 1500  # default fallback


# ---------------------------------------------------------------------------
# Budgets loader
# ---------------------------------------------------------------------------

class TestBudgetsLoader:
    def test_loads_known_roles(self):
        b = load_budgets()
        for role in ("engineer", "senior_engineer", "lead_engineer", "principal_engineer",
                     "security_engineer", "quality_engineer", "general_orchestrator",
                     "model_engineer"):
            assert role in b, f"missing role: {role}"
            assert b[role] > 0

    def test_engineer_budget_matches_spec(self):
        b = load_budgets()
        assert b["engineer"] == 1500
        assert b["general_orchestrator"] == 500
        assert b["security_engineer"] == 5000
