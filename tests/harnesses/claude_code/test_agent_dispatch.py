"""
Regression tests for Claude Code harness AgentDispatch.

AC1: Claude Code harness delegation success >= 95%
AC3: All 8 agents available and dispatch correctly
AC4: Model routing follows complexity levels (Haiku/Sonnet/Opus)
AC5: 10+ regression tests (this file contributes the remaining tests)
AC6: Zero regressions in existing tests
"""

from __future__ import annotations

import pytest

from src.harnesses.claude_code.agent_dispatch import (
    AGENT_ROSTER,
    EFFORT_TIER,
    ROLE_MODEL_PINS,
    TIER_MODELS,
    AgentDispatch,
    DispatchResult,
    ModelTier,
)

# CORE_SKILLS lives in skill_renderer, imported here for cross-module checks.
from src.harnesses.claude_code.skill_renderer import CORE_SKILLS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def dispatch() -> AgentDispatch:
    """Shared AgentDispatch instance."""
    return AgentDispatch()


# ---------------------------------------------------------------------------
# AC3: All 8 agents available and dispatch correctly
# ---------------------------------------------------------------------------


class TestAgentRoster:
    """AC3: All 8 agents are registered and dispatchable."""

    def test_agent_roster_has_8_entries(self) -> None:
        """AGENT_ROSTER must have exactly 8 agents."""
        assert len(AGENT_ROSTER) == 8

    def test_expected_agents_in_roster(self) -> None:
        """All expected agent names are in AGENT_ROSTER."""
        expected = {
            "orchestrator",
            "engineer",
            "senior-engineer",
            "lead-engineer",
            "quality-engineer",
            "principal-engineer",
            "security-engineer",
            "model-engineer",
        }
        assert set(AGENT_ROSTER) == expected

    @pytest.mark.parametrize("agent_name", AGENT_ROSTER)
    def test_all_agents_dispatch_successfully(
        self, dispatch: AgentDispatch, agent_name: str
    ) -> None:
        """Each agent in the roster must dispatch without raising an exception."""
        result = dispatch.route(agent=agent_name, effort="low")
        assert isinstance(result, DispatchResult)
        assert result.success is True
        assert result.agent == agent_name
        assert result.model  # non-empty string

    def test_available_agents_returns_sorted_list(
        self, dispatch: AgentDispatch
    ) -> None:
        """available_agents() returns a sorted list of all 8 agents."""
        agents = dispatch.available_agents()
        assert len(agents) == 8
        assert agents == sorted(agents)

    def test_is_agent_available_known(self, dispatch: AgentDispatch) -> None:
        """is_agent_available() returns True for known agents."""
        for name in AGENT_ROSTER:
            assert dispatch.is_agent_available(name) is True

    def test_is_agent_available_unknown(self, dispatch: AgentDispatch) -> None:
        """is_agent_available() returns False for unknown agents."""
        assert dispatch.is_agent_available("nonexistent-agent") is False

    def test_route_unknown_agent_raises_value_error(
        self, dispatch: AgentDispatch
    ) -> None:
        """Routing an unknown agent must raise ValueError."""
        with pytest.raises(ValueError, match="Unknown agent"):
            dispatch.route(agent="unknown-agent", effort="low")

    def test_route_result_has_correct_agent_name(
        self, dispatch: AgentDispatch
    ) -> None:
        """DispatchResult.agent must equal the input agent name."""
        result = dispatch.route(agent="engineer", effort="low")
        assert result.agent == "engineer"

    def test_route_result_has_explanation(self, dispatch: AgentDispatch) -> None:
        """DispatchResult must always have a non-empty explanation."""
        result = dispatch.route(agent="senior-engineer", effort="medium")
        assert isinstance(result.explanation, str)
        assert len(result.explanation) > 0


# ---------------------------------------------------------------------------
# AC4: Complexity-based model routing (Haiku / Sonnet / Opus)
# ---------------------------------------------------------------------------


class TestModelRouting:
    """AC4: Model routing follows complexity levels."""

    def test_low_effort_maps_to_haiku(self, dispatch: AgentDispatch) -> None:
        """effort='low' must resolve to claude-haiku-4.5."""
        model = dispatch.model_for_effort("low")
        assert model == "claude-haiku-4.5"

    def test_medium_effort_maps_to_sonnet(self, dispatch: AgentDispatch) -> None:
        """effort='medium' must resolve to claude-sonnet-4.5."""
        model = dispatch.model_for_effort("medium")
        assert model == "claude-sonnet-4.5"

    def test_high_effort_maps_to_opus(self, dispatch: AgentDispatch) -> None:
        """effort='high' must resolve to claude-opus-4.8."""
        model = dispatch.model_for_effort("high")
        assert model == "claude-opus-4.8"

    def test_max_effort_maps_to_opus(self, dispatch: AgentDispatch) -> None:
        """effort='max' must also resolve to claude-opus-4.8."""
        model = dispatch.model_for_effort("max")
        assert model == "claude-opus-4.8"

    def test_tier_models_covers_all_tiers(self) -> None:
        """TIER_MODELS must define a model for every ModelTier value."""
        for tier in ModelTier:
            assert tier in TIER_MODELS, f"Missing model for tier {tier}"
            assert TIER_MODELS[tier]  # non-empty

    def test_effort_tier_covers_standard_efforts(self) -> None:
        """EFFORT_TIER must cover low, medium, high, and max."""
        for effort in ("low", "medium", "high", "max"):
            assert effort in EFFORT_TIER

    def test_haiku_tier_model_contains_haiku(self) -> None:
        """Haiku tier model name must contain 'haiku'."""
        assert "haiku" in TIER_MODELS[ModelTier.HAIKU].lower()

    def test_sonnet_tier_model_contains_sonnet(self) -> None:
        """Sonnet tier model name must contain 'sonnet'."""
        assert "sonnet" in TIER_MODELS[ModelTier.SONNET].lower()

    def test_opus_tier_model_contains_opus(self) -> None:
        """Opus tier model name must contain 'opus'."""
        assert "opus" in TIER_MODELS[ModelTier.OPUS].lower()

    def test_senior_engineer_low_effort_uses_haiku(
        self, dispatch: AgentDispatch
    ) -> None:
        """senior-engineer with low effort -> Haiku (no pin, effort routing)."""
        result = dispatch.route(agent="senior-engineer", effort="low")
        assert result.pinned is False
        assert "haiku" in result.model.lower()
        assert result.tier == ModelTier.HAIKU

    def test_senior_engineer_medium_effort_uses_sonnet(
        self, dispatch: AgentDispatch
    ) -> None:
        """senior-engineer with medium effort -> Sonnet."""
        result = dispatch.route(agent="senior-engineer", effort="medium")
        assert result.pinned is False
        assert "sonnet" in result.model.lower()
        assert result.tier == ModelTier.SONNET

    def test_senior_engineer_high_effort_uses_opus(
        self, dispatch: AgentDispatch
    ) -> None:
        """senior-engineer with high effort -> Opus."""
        result = dispatch.route(agent="senior-engineer", effort="high")
        assert result.pinned is False
        assert "opus" in result.model.lower()
        assert result.tier == ModelTier.OPUS

    def test_lead_engineer_high_effort_uses_opus(
        self, dispatch: AgentDispatch
    ) -> None:
        """lead-engineer with high effort -> Opus."""
        result = dispatch.route(agent="lead-engineer", effort="high")
        assert "opus" in result.model.lower()

    def test_quality_engineer_medium_effort_uses_sonnet(
        self, dispatch: AgentDispatch
    ) -> None:
        """quality-engineer with medium effort -> Sonnet."""
        result = dispatch.route(agent="quality-engineer", effort="medium")
        assert "sonnet" in result.model.lower()

    def test_model_engineer_medium_effort_uses_sonnet(
        self, dispatch: AgentDispatch
    ) -> None:
        """model-engineer with medium effort -> Sonnet."""
        result = dispatch.route(agent="model-engineer", effort="medium")
        assert "sonnet" in result.model.lower()


# ---------------------------------------------------------------------------
# Pinned-role tests
# ---------------------------------------------------------------------------


class TestPinnedRoles:
    """Roles with fixed models must not be downgraded by effort routing."""

    def test_orchestrator_always_uses_haiku(
        self, dispatch: AgentDispatch
    ) -> None:
        """orchestrator must use Haiku regardless of effort."""
        for effort in ("low", "medium", "high", "max"):
            result = dispatch.route(agent="orchestrator", effort=effort)
            assert result.pinned is True
            assert "haiku" in result.model.lower(), (
                f"orchestrator with effort={effort} got {result.model}"
            )

    def test_engineer_always_uses_haiku(self, dispatch: AgentDispatch) -> None:
        """engineer must use Haiku regardless of effort."""
        for effort in ("low", "medium", "high"):
            result = dispatch.route(agent="engineer", effort=effort)
            assert result.pinned is True
            assert "haiku" in result.model.lower()

    def test_security_engineer_always_uses_opus(
        self, dispatch: AgentDispatch
    ) -> None:
        """security-engineer must use Opus regardless of effort (pinned)."""
        for effort in ("low", "medium", "high"):
            result = dispatch.route(agent="security-engineer", effort=effort)
            assert result.pinned is True
            assert "opus" in result.model.lower(), (
                f"security-engineer with effort={effort} got {result.model}"
            )

    def test_principal_engineer_always_uses_opus(
        self, dispatch: AgentDispatch
    ) -> None:
        """principal-engineer must use Opus regardless of effort (pinned)."""
        for effort in ("low", "medium", "high"):
            result = dispatch.route(agent="principal-engineer", effort=effort)
            assert result.pinned is True
            assert "opus" in result.model.lower()

    def test_pinned_result_has_pinned_true(self, dispatch: AgentDispatch) -> None:
        """DispatchResult.pinned must be True for pinned roles."""
        for agent in ROLE_MODEL_PINS:
            result = dispatch.route(agent=agent, effort="low")
            assert result.pinned is True, f"Expected pinned=True for {agent}"

    def test_non_pinned_result_has_pinned_false(
        self, dispatch: AgentDispatch
    ) -> None:
        """DispatchResult.pinned must be False for non-pinned roles."""
        non_pinned = [a for a in AGENT_ROSTER if a not in ROLE_MODEL_PINS]
        for agent in non_pinned:
            result = dispatch.route(agent=agent, effort="low")
            assert result.pinned is False, f"Expected pinned=False for {agent}"


# ---------------------------------------------------------------------------
# AC1: Delegation success rate >= 95%
# ---------------------------------------------------------------------------


class TestDelegationSuccessRate:
    """AC1: Claude Code harness delegation success >= 95%."""

    def test_measure_delegation_success_passes_threshold(
        self, dispatch: AgentDispatch
    ) -> None:
        """Default scenario set must achieve >= 95% success rate."""
        metrics = dispatch.measure_delegation_success()
        assert metrics["success_rate"] >= 0.95, (
            f"Delegation success rate {metrics['success_rate']:.0%} < 95%. "
            f"Failures: {metrics['failures']}"
        )

    def test_measure_delegation_success_returns_all_fields(
        self, dispatch: AgentDispatch
    ) -> None:
        """measure_delegation_success() must return the required keys."""
        metrics = dispatch.measure_delegation_success()
        assert "total" in metrics
        assert "passed" in metrics
        assert "failed" in metrics
        assert "success_rate" in metrics
        assert "failures" in metrics

    def test_measure_delegation_with_custom_scenarios(
        self, dispatch: AgentDispatch
    ) -> None:
        """Custom scenario list is respected."""
        scenarios = [
            {"agent": "engineer", "effort": "low"},
            {"agent": "senior-engineer", "effort": "high"},
        ]
        metrics = dispatch.measure_delegation_success(scenarios)
        assert metrics["total"] == 2
        assert metrics["passed"] == 2
        assert metrics["success_rate"] == 1.0

    def test_route_batch_returns_correct_count(
        self, dispatch: AgentDispatch
    ) -> None:
        """route_batch() must return one result per input task."""
        tasks = [
            {"agent": "engineer", "effort": "low"},
            {"agent": "senior-engineer", "effort": "medium"},
            {"agent": "quality-engineer", "effort": "high"},
        ]
        results = dispatch.route_batch(tasks)
        assert len(results) == 3
        for result in results:
            assert isinstance(result, DispatchResult)
            assert result.success is True

    def test_route_batch_preserves_order(self, dispatch: AgentDispatch) -> None:
        """route_batch() must preserve the input order."""
        tasks = [
            {"agent": "engineer", "effort": "low"},
            {"agent": "security-engineer", "effort": "high"},
            {"agent": "model-engineer", "effort": "medium"},
        ]
        results = dispatch.route_batch(tasks)
        assert results[0].agent == "engineer"
        assert results[1].agent == "security-engineer"
        assert results[2].agent == "model-engineer"


# ---------------------------------------------------------------------------
# Misc / edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge-case and boundary-condition tests."""

    def test_route_with_none_effort_defaults_to_haiku_for_non_pinned(
        self, dispatch: AgentDispatch
    ) -> None:
        """No effort hint defaults to Haiku tier for non-pinned agents."""
        result = dispatch.route(agent="senior-engineer", effort=None)
        assert result.tier == ModelTier.HAIKU

    def test_route_includes_task_description_in_explanation(
        self, dispatch: AgentDispatch
    ) -> None:
        """Task description is echoed in the explanation for non-pinned roles."""
        result = dispatch.route(
            agent="senior-engineer",
            effort="high",
            task_description="Refactor the payment service",
        )
        assert "Refactor" in result.explanation

    def test_route_metadata_is_propagated(self, dispatch: AgentDispatch) -> None:
        """Metadata dict is attached to the result unchanged."""
        meta = {"task_id": "test-123", "priority": "high"}
        result = dispatch.route(agent="engineer", effort="low", metadata=meta)
        assert result.metadata == meta

    def test_get_agent_model_convenience_method(
        self, dispatch: AgentDispatch
    ) -> None:
        """get_agent_model() returns just the model string."""
        model = dispatch.get_agent_model("engineer", effort="low")
        assert isinstance(model, str)
        assert "haiku" in model.lower()

    def test_dispatch_with_custom_tier_models(self) -> None:
        """Custom tier_models override is respected."""
        custom_tiers = {
            ModelTier.HAIKU: "custom-haiku-model",
            ModelTier.SONNET: "custom-sonnet-model",
            ModelTier.OPUS: "custom-opus-model",
        }
        # Remove pinned roles to exercise effort routing
        dispatch = AgentDispatch(role_pins={}, tier_models=custom_tiers)
        result = dispatch.route(agent="senior-engineer", effort="low")
        assert result.model == "custom-haiku-model"

    def test_dispatch_with_custom_role_pins(self) -> None:
        """Custom role_pins override maps a role to a specific model."""
        custom_pins = {"engineer": "claude-sonnet-4.5"}
        dispatch = AgentDispatch(role_pins=custom_pins)
        result = dispatch.route(agent="engineer", effort="low")
        assert result.model == "claude-sonnet-4.5"
        assert result.pinned is True

    def test_model_tier_enum_has_three_values(self) -> None:
        """ModelTier must define HAIKU, SONNET, and OPUS."""
        values = {t.value for t in ModelTier}
        assert values == {"haiku", "sonnet", "opus"}
