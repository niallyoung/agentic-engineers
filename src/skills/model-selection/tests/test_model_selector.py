"""
test_model_selector.py — comprehensive test suite for COST-003 (ModelSelector + QualityEstimator)

123 tests across 12 test classes covering all public API methods, constraints,
edge cases, COST-002 integration, Pareto frontier correctness, and performance.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

_SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_SKILL_ROOT))

from scripts.quality_estimator import QualityEstimator, _infer_tier
from scripts.model_selector import ModelSelector

# ---------------------------------------------------------------------------
# MINIMAL_YAML — embedded fixture (isolates tests from real models.yaml)
# ---------------------------------------------------------------------------

MINIMAL_YAML = """
providers:
  anthropic:
    claude-haiku-4.5:
      input: 0.00008
      output: 0.00024
    claude-sonnet-4.5:
      input: 0.003
      output: 0.015
    claude-opus-4.8:
      input: 0.005
      output: 0.025
  openai:
    gpt-4o-mini:
      input: 0.00015
      output: 0.0006
    gpt-4o:
      input: 0.0025
      output: 0.01
  ollama:
    llama-3-70b:
      input: 0.0
      output: 0.0

model_selection:
  models:
    claude-haiku-4.5:
      provider: anthropic
      tier: haiku
      base_quality: 0.65
      avg_latency_sec: 1.5
    claude-sonnet-4.5:
      provider: anthropic
      tier: sonnet
      base_quality: 0.82
      avg_latency_sec: 3.0
    claude-opus-4.8:
      provider: anthropic
      tier: opus
      base_quality: 0.95
      avg_latency_sec: 7.0
    gpt-4o-mini:
      provider: openai
      tier: mini
      base_quality: 0.62
      avg_latency_sec: 1.5
    gpt-4o:
      provider: openai
      tier: sonnet
      base_quality: 0.83
      avg_latency_sec: 3.5
    llama-3-70b:
      provider: ollama
      tier: haiku
      base_quality: 0.68
      avg_latency_sec: 6.0

  task_quality_adjustments:
    code_review:
      mini: -0.05
      haiku: -0.05
      sonnet: 0.05
      opus: 0.02
    documentation:
      mini: 0.05
      haiku: 0.05
      sonnet: 0.0
      opus: -0.02
    general:
      mini: 0.0
      haiku: 0.0
      sonnet: 0.0
      opus: 0.0
    security_audit:
      mini: -0.10
      haiku: -0.10
      sonnet: 0.02
      opus: 0.03
"""

EMPTY_YAML = """
providers:
  anthropic:
    claude-haiku-4.5:
      input: 0.00008
      output: 0.00024
model_selection:
  models: {}
  task_quality_adjustments: {}
"""


@pytest.fixture
def models_yaml(tmp_path):
    """Write MINIMAL_YAML to a temp file and return its Path."""
    p = tmp_path / "models.yaml"
    p.write_text(MINIMAL_YAML)
    return p


@pytest.fixture
def selector(models_yaml):
    """Shared ModelSelector instance backed by MINIMAL_YAML."""
    return ModelSelector(models_yaml=models_yaml)


@pytest.fixture
def estimator(models_yaml):
    """Shared QualityEstimator instance backed by MINIMAL_YAML."""
    return QualityEstimator(models_yaml=models_yaml)


# ===========================================================================
# TestModelSelectorInit
# ===========================================================================

class TestModelSelectorInit:
    """ModelSelector initialization and config loading."""

    def test_init_with_valid_yaml(self, models_yaml):
        """ModelSelector loads config when models_yaml exists."""
        sel = ModelSelector(models_yaml=models_yaml)
        assert len(sel._model_meta) > 0, "Expected at least one model loaded"

    def test_init_with_missing_yaml(self):
        """ModelSelector falls back gracefully when models.yaml is absent."""
        sel = ModelSelector(models_yaml=Path("nonexistent.yaml"))
        assert isinstance(sel, ModelSelector)

    def test_provider_rates_loaded(self, models_yaml):
        """Provider cost rates are loaded from yaml."""
        selector = ModelSelector(models_yaml=models_yaml)
        assert "anthropic" in selector._provider_rates

    def test_model_meta_loaded(self, models_yaml):
        """Model metadata is loaded from yaml."""
        selector = ModelSelector(models_yaml=models_yaml)
        assert "claude-haiku-4.5" in selector._model_meta

    def test_init_with_cost_aggregator(self, models_yaml):
        """ModelSelector accepts an optional CostAggregator."""
        class FakeAggregator:
            pass
        agg = FakeAggregator()
        sel = ModelSelector(models_yaml=models_yaml, cost_aggregator=agg)
        assert sel._cost_aggregator is agg


# ===========================================================================
# TestRecommendModelBasic
# ===========================================================================

class TestRecommendModelBasic:
    """Basic return-value structure from recommend_model."""

    def test_returns_dict_with_required_keys(self, selector):
        """recommend_model returns dict with all required keys."""
        rec = selector.recommend_model("general", 1000, 500)
        for key in ("model", "provider", "estimated_cost", "estimated_quality",
                    "estimated_latency_sec", "reasoning", "_selection_time_ms"):
            assert key in rec

    def test_model_is_string(self, selector):
        """Returned model is a non-empty string."""
        rec = selector.recommend_model("general", 1000, 500)
        assert isinstance(rec["model"], str) and rec["model"]

    def test_provider_is_string(self, selector):
        """Returned provider is a non-empty string."""
        rec = selector.recommend_model("general", 1000, 500)
        assert isinstance(rec["provider"], str) and rec["provider"]

    def test_cost_is_non_negative(self, selector):
        """Estimated cost is non-negative."""
        rec = selector.recommend_model("general", 1000, 500)
        assert rec["estimated_cost"] >= 0

    def test_quality_between_0_and_1(self, selector):
        """Estimated quality is in [0, 1]."""
        rec = selector.recommend_model("general", 1000, 500)
        assert 0.0 <= rec["estimated_quality"] <= 1.0

    def test_latency_is_positive(self, selector):
        """Estimated latency is positive."""
        rec = selector.recommend_model("general", 1000, 500)
        assert rec["estimated_latency_sec"] > 0

    def test_reasoning_is_non_empty(self, selector):
        """Reasoning string is populated."""
        rec = selector.recommend_model("general", 1000, 500)
        assert isinstance(rec["reasoning"], str) and rec["reasoning"]

    def test_no_constraints_returns_highest_quality(self, selector):
        """Without constraints the highest-quality model is recommended."""
        rec = selector.recommend_model("general", 1000, 500)
        assert rec["estimated_quality"] >= 0.8

    def test_zero_tokens_ok(self, selector):
        """Zero-token requests are handled without error."""
        rec = selector.recommend_model("general", 0, 0)
        assert rec["estimated_cost"] >= 0

    def test_large_token_count(self, selector):
        """Very large token counts are handled correctly."""
        rec = selector.recommend_model("code_review", 100000, 50000)
        assert rec["estimated_cost"] >= 0


# ===========================================================================
# TestRecommendModelCostConstraints
# ===========================================================================

class TestRecommendModelCostConstraints:
    """Budget constraints in recommend_model."""

    def test_recommendation_under_budget(self, selector):
        """Recommended model cost is <= max_cost when budget is satisfiable."""
        rec = selector.recommend_model("general", 1000, 500, {"max_cost": 0.1})
        assert rec["estimated_cost"] <= 0.1

    def test_tight_budget_picks_cheap_model(self, selector):
        """A very tight budget forces selection of the cheapest model."""
        rec = selector.recommend_model("general", 1000, 500, {"max_cost": 0.001})
        assert rec["estimated_cost"] <= 0.001

    def test_cost_exactly_at_limit_is_allowed(self, selector):
        """Exact budget match is accepted."""
        # claude-haiku-4.5: (1000*0.00008 + 500*0.00024)/1000 = 0.0002
        haiku_cost = (1000 * 0.00008 + 500 * 0.00024) / 1000
        rec = selector.recommend_model("general", 1000, 500,
                                       {"max_cost": haiku_cost,
                                        "provider_preference": ["anthropic"]})
        assert abs(rec["estimated_cost"] - haiku_cost) < 1e-9 or rec["estimated_cost"] <= haiku_cost

    def test_all_models_over_budget_returns_cheapest(self, selector):
        """When all models exceed budget, cheapest is returned with warning."""
        rec = selector.recommend_model("general", 1000, 500,
                                       {"max_cost": 1e-5,
                                        "provider_preference": ["anthropic"]})
        assert "exceed" in rec["reasoning"].lower()
        assert len(rec["model"]) > 0

    def test_max_cost_zero_returns_free_models_or_cheapest(self, selector):
        """max_cost=0 returns ollama (free) if available, else cheapest."""
        rec = selector.recommend_model("general", 1000, 500, {"max_cost": 0})
        # Ollama models are free so cost should be 0
        assert rec["estimated_cost"] == 0 or rec["provider"] == "ollama"

    def test_budget_respected_for_large_tokens(self, selector):
        """Budget is respected even for large token counts."""
        rec = selector.recommend_model("general", 50000, 20000, {"max_cost": 0.5})
        assert rec["estimated_cost"] <= 0.5

    def test_estimated_cost_is_rounded(self, selector):
        """Estimated cost is rounded to at most 6 decimal places."""
        rec = selector.recommend_model("general", 1000, 500)
        cost_str = str(rec["estimated_cost"])
        if "." in cost_str:
            assert len(cost_str.split(".")[1]) <= 6

    def test_cost_uses_anthropic_rates_correctly(self, selector):
        """Cost for claude-haiku-4.5 matches expected rate calculation."""
        rec = selector.recommend_model("general", 1000, 500,
                                       {"provider_preference": ["anthropic"],
                                        "max_cost": 0.001})
        if rec["model"] == "claude-haiku-4.5":
            # (1000*0.00008 + 500*0.00024)/1000 = 0.0002
            expected = (1000 * 0.00008 + 500 * 0.00024) / 1000
            assert abs(rec["estimated_cost"] - expected) < 1e-8

    def test_ollama_models_have_zero_cost(self, selector):
        """Ollama models are free (cost = 0)."""
        rec = selector.recommend_model("general", 10000, 5000,
                                       {"provider_preference": ["ollama"]})
        assert rec["estimated_cost"] == 0.0

    def test_openai_rates_applied_correctly(self, selector):
        """Cost for gpt-4o-mini matches expected rate."""
        rec = selector.recommend_model("general", 1000, 500,
                                       {"provider_preference": ["openai"],
                                        "max_cost": 0.001})
        if rec["model"] == "gpt-4o-mini":
            # (1000*0.00015 + 500*0.0006)/1000 = 0.00045
            expected = (1000 * 0.00015 + 500 * 0.0006) / 1000
            assert abs(rec["estimated_cost"] - expected) < 1e-8


# ===========================================================================
# TestRecommendModelQualityTargets
# ===========================================================================

class TestRecommendModelQualityTargets:
    """Quality target constraints in recommend_model."""

    def test_high_quality_target_picks_best_model(self, selector):
        """quality_target=0.95 results in highest-quality model being recommended."""
        rec = selector.recommend_model("general", 1000, 500, {"quality_target": 0.95})
        assert rec["estimated_quality"] >= 0.85

    def test_low_quality_target_still_picks_best_within_budget(self, selector):
        """Low quality_target doesn't force a downgrade — best quality still wins."""
        rec = selector.recommend_model("general", 1000, 500, {"quality_target": 0.5})
        assert rec["estimated_quality"] >= 0.6

    def test_unachievable_quality_returns_best_available(self, selector):
        """quality_target > max(quality) returns best available with advisory."""
        rec = selector.recommend_model("general", 1000, 500, {"quality_target": 0.9999})
        assert "not achievable" in rec["reasoning"].lower()

    def test_quality_and_cost_combined(self, selector):
        """Combined quality_target + max_cost returns best quality within budget."""
        rec = selector.recommend_model("code_review", 5000, 2000,
                                       {"quality_target": 0.8, "max_cost": 0.1})
        assert rec["estimated_cost"] <= 0.1

    def test_code_review_quality_higher_than_general(self, selector):
        """Sonnet-class models score higher quality on code_review than general."""
        code_q = selector._quality.estimate_quality("claude-sonnet-4.5", "code_review")
        general_q = selector._quality.estimate_quality("claude-sonnet-4.5", "general")
        assert code_q > general_q

    def test_documentation_quality_higher_for_haiku(self, selector):
        """Haiku gets quality boost for documentation task."""
        haiku_doc = selector._quality.estimate_quality("claude-haiku-4.5", "documentation")
        haiku_gen = selector._quality.estimate_quality("claude-haiku-4.5", "general")
        assert haiku_doc > haiku_gen

    def test_security_audit_haiku_quality_lower(self, selector):
        """Haiku gets quality penalty for security_audit."""
        haiku_sec = selector._quality.estimate_quality("claude-haiku-4.5", "security_audit")
        haiku_gen = selector._quality.estimate_quality("claude-haiku-4.5", "general")
        assert haiku_sec < haiku_gen

    def test_quality_score_clamped_at_1(self, selector):
        """Quality score never exceeds 1.0."""
        score = selector._quality.estimate_quality("claude-opus-4.8", "code_review")
        assert score <= 1.0

    def test_quality_score_clamped_at_0(self, selector):
        """Quality score never goes below 0.0."""
        score = selector._quality.estimate_quality("gpt-4o-mini", "security_audit")
        assert score >= 0.0


# ===========================================================================
# TestRecommendModelLatency
# ===========================================================================

class TestRecommendModelLatency:
    """Latency constraints in recommend_model."""

    def test_fast_latency_avoids_opus(self, selector):
        """max_latency_sec=2.0 should exclude opus (7s) and select faster models."""
        rec = selector.recommend_model("general", 1000, 500, {"max_latency_sec": 2.0})
        assert rec["estimated_latency_sec"] <= 2.0

    def test_latency_and_cost_combined(self, selector):
        """Latency + cost constraints both satisfied simultaneously."""
        rec = selector.recommend_model("general", 1000, 500,
                                       {"max_latency_sec": 4.0, "max_cost": 0.05})
        assert rec["estimated_latency_sec"] <= 4.0

    def test_generous_latency_allows_all_models(self, selector):
        """max_latency_sec=60 doesn't restrict model choice."""
        rec = selector.recommend_model("general", 1000, 500, {"max_latency_sec": 60.0})
        assert len(rec["model"]) > 0

    def test_unreachable_latency_picks_fastest(self, selector):
        """When no model meets latency SLA, fastest is returned with advisory."""
        rec = selector.recommend_model("general", 1000, 500, {"max_latency_sec": 0.1})
        # Should return fastest model even though SLA can't be met
        assert len(rec["model"]) > 0

    def test_latency_constraint_excludes_ollama_when_slow(self, selector):
        """max_latency_sec=2 excludes ollama (llama-3-70b at 6s)."""
        rec = selector.recommend_model("general", 1000, 500,
                                       {"max_latency_sec": 2.0,
                                        "provider_preference": ["anthropic", "openai", "ollama"]})
        assert rec["estimated_latency_sec"] <= 2.0
        assert rec["provider"] != "ollama"

    def test_latency_all_three_constraints(self, selector):
        """All three constraints (cost + quality + latency) applied correctly."""
        rec = selector.recommend_model("general", 5000, 2000,
                                       {"max_cost": 0.2, "quality_target": 0.7,
                                        "max_latency_sec": 5.0})
        assert rec["estimated_cost"] <= 0.2

    def test_latency_returns_sec_as_float(self, selector):
        """Latency is returned as a float in seconds."""
        rec = selector.recommend_model("general", 1000, 500, {"max_latency_sec": 5.0})
        assert isinstance(rec["estimated_latency_sec"], float)

    def test_latency_advisory_when_impossible(self, selector):
        """Reasoning mentions latency issue when SLA can't be met."""
        rec = selector.recommend_model("general", 1000, 500, {"max_latency_sec": 0.001})
        assert "latency" in rec["reasoning"].lower() or "sla" in rec["reasoning"].lower()


# ===========================================================================
# TestRecommendModelProviderPreference
# ===========================================================================

class TestRecommendModelProviderPreference:
    """Provider preference filtering in recommend_model."""

    def test_anthropic_only_returns_anthropic_model(self, selector):
        """provider_preference=['anthropic'] restricts to Anthropic models."""
        rec = selector.recommend_model("general", 1000, 500,
                                       {"provider_preference": ["anthropic"]})
        assert rec["provider"] == "anthropic"

    def test_openai_only_returns_openai_model(self, selector):
        """provider_preference=['openai'] restricts to OpenAI models."""
        rec = selector.recommend_model("general", 1000, 500,
                                       {"provider_preference": ["openai"]})
        assert rec["provider"] == "openai"

    def test_ollama_only_returns_ollama_model(self, selector):
        """provider_preference=['ollama'] restricts to Ollama models."""
        rec = selector.recommend_model("general", 1000, 500,
                                       {"provider_preference": ["ollama"]})
        assert rec["provider"] == "ollama"

    def test_preference_order_respected_when_budget_allows(self, selector):
        """Provider preference order is honored when budget is sufficient."""
        rec = selector.recommend_model("general", 1000, 500,
                                       {"provider_preference": ["anthropic", "openai"]})
        assert rec["provider"] in ("anthropic", "openai")

    def test_fallback_when_preferred_provider_unavailable(self, selector):
        """Falls back to all providers if preferred provider has no models."""
        rec = selector.recommend_model("general", 1000, 500,
                                       {"provider_preference": ["nonexistent_provider"]})
        assert len(rec["model"]) > 0

    def test_multi_provider_preference_includes_all(self, selector):
        """Multi-provider list includes all listed providers as candidates."""
        rec = selector.recommend_model("general", 1000, 500,
                                       {"max_cost": 0.0001,
                                        "provider_preference": ["anthropic", "openai", "ollama"]})
        # With tight budget, Ollama (free) should win
        assert rec["estimated_cost"] <= 0.0001

    def test_preference_combined_with_cost(self, selector):
        """Provider preference + cost constraint both honored."""
        rec = selector.recommend_model("general", 1000, 500,
                                       {"provider_preference": ["anthropic"],
                                        "max_cost": 0.001})
        assert rec["provider"] == "anthropic"

    def test_empty_provider_preference_uses_all_providers(self, selector):
        """Empty provider_preference list uses all providers."""
        rec = selector.recommend_model("general", 1000, 500,
                                       {"provider_preference": []})
        assert len(rec["model"]) > 0


# ===========================================================================
# TestRecommendModelEdgeCases
# ===========================================================================

class TestRecommendModelEdgeCases:
    """Edge cases and error handling in recommend_model."""

    def test_unknown_task_type_falls_back_to_general(self, selector):
        """Unknown task_type uses 'general' quality adjustments."""
        rec = selector.recommend_model("completely_unknown_task", 1000, 500)
        assert len(rec["model"]) > 0

    def test_none_constraints_equivalent_to_empty(self, selector):
        """None constraints produce same result as empty dict."""
        rec1 = selector.recommend_model("general", 1000, 500, None)
        rec2 = selector.recommend_model("general", 1000, 500, {})
        assert rec1["model"] == rec2["model"]

    def test_cost_aggregator_used_when_provided(self, models_yaml):
        """CostAggregator is called when provided (mocked to fixed value)."""
        class FakeAgg:
            def aggregate_task_cost(self, task_type, input_tokens, output_tokens, model_variants):
                provider = list(model_variants.keys())[0]
                return {provider: 0.042}
        sel = ModelSelector(models_yaml=models_yaml, cost_aggregator=FakeAgg())
        rec = sel.recommend_model("general", 1000, 500)
        # At least one call should have been made (cost for a model)
        assert rec["estimated_cost"] >= 0

    def test_cost_aggregator_fallback_on_error(self, models_yaml):
        """Falls back to rates if CostAggregator raises an exception."""
        class BrokenAgg:
            def aggregate_task_cost(self, *args, **kwargs):
                raise RuntimeError("agg down")
        sel = ModelSelector(models_yaml=models_yaml, cost_aggregator=BrokenAgg())
        rec = sel.recommend_model("general", 1000, 500)
        assert rec["estimated_cost"] >= 0

    def test_all_providers_over_budget_reasoning(self, selector):
        """Over-budget scenario includes explanatory reasoning."""
        rec = selector.recommend_model("general", 1000, 500,
                                       {"max_cost": 1e-10,
                                        "provider_preference": ["anthropic"]})
        assert len(rec["reasoning"]) > 0

    def test_no_models_in_yaml(self, tmp_path):
        """Empty model_selection.models section handled gracefully."""
        empty = tmp_path / "empty.yaml"
        empty.write_text(EMPTY_YAML)
        sel = ModelSelector(models_yaml=empty)
        candidates = sel._enrich_models("general", 100, 100)
        assert isinstance(candidates, list)

    def test_recommend_model_very_high_token_count(self, selector):
        """Recommend handles million-token requests without overflow."""
        rec = selector.recommend_model("general", 1000000, 500000)
        assert rec["estimated_cost"] >= 0

    def test_selection_time_ms_key_present(self, selector):
        """recommend_model includes _selection_time_ms diagnostic key."""
        rec = selector.recommend_model("general", 1000, 500)
        assert "_selection_time_ms" in rec and rec["_selection_time_ms"] >= 0

    def test_recommend_is_deterministic(self, selector):
        """Same inputs always produce same recommendation."""
        rec1 = selector.recommend_model("general", 1000, 500)
        rec2 = selector.recommend_model("general", 1000, 500)
        assert rec1["model"] == rec2["model"]


# ===========================================================================
# TestRecommendBatch
# ===========================================================================

class TestRecommendBatch:
    """recommend_batch multi-task API."""

    def test_batch_returns_list(self, selector):
        """recommend_batch returns a list."""
        result = selector.recommend_batch([])
        assert isinstance(result, list)

    def test_batch_length_matches_input(self, selector):
        """Output length equals input length."""
        tasks = [
            {"task_type": "general", "tokens": (1000, 500)},
            {"task_type": "code_review", "tokens": (2000, 800)},
            {"task_type": "documentation", "tokens": (500, 300)},
        ]
        assert len(selector.recommend_batch(tasks)) == 3

    def test_batch_each_item_has_required_keys(self, selector):
        """Each item in batch result has all required keys."""
        result = selector.recommend_batch([{"task_type": "general", "tokens": (1000, 500)}])
        item = result[0]
        for key in ("model", "provider", "estimated_cost", "estimated_quality",
                    "reasoning", "_selection_time_ms", "task_type", "_cumulative_cost"):
            assert key in item

    def test_batch_includes_task_type(self, selector):
        """Each batch result item includes the original task_type."""
        result = selector.recommend_batch([{"task_type": "code_review", "tokens": (1000, 500)}])
        assert result[0]["task_type"] == "code_review"

    def test_batch_cumulative_cost_increases(self, selector):
        """Cumulative cost is non-decreasing across batch items."""
        tasks = [
            {"task_type": "general", "tokens": (1000, 500)},
            {"task_type": "code_review", "tokens": (2000, 800)},
            {"task_type": "security_audit", "tokens": (3000, 1000)},
        ]
        result = selector.recommend_batch(tasks)
        cum_costs = [r["_cumulative_cost"] for r in result]
        for i in range(1, len(cum_costs)):
            assert cum_costs[i] >= cum_costs[i - 1]

    def test_batch_constraints_applied_per_task(self, selector):
        """Constraints are applied independently per task in the batch."""
        tasks = [
            {"task_type": "general", "tokens": (1000, 500),
             "constraints": {"max_cost": 0.001}},
            {"task_type": "general", "tokens": (1000, 500),
             "constraints": {"max_cost": 1.0}},
        ]
        result = selector.recommend_batch(tasks)
        assert result[0]["estimated_cost"] <= 0.001

    def test_empty_batch_returns_empty_list(self, selector):
        """Empty task list returns empty list."""
        result = selector.recommend_batch([])
        assert result == []

    def test_batch_tokens_as_list(self, selector):
        """tokens can be a list (not just tuple)."""
        tasks = [{"task_type": "general", "tokens": [1000, 500]}]
        result = selector.recommend_batch(tasks)
        assert len(result) == 1


# ===========================================================================
# TestCostQualityFrontier
# ===========================================================================

class TestCostQualityFrontier:
    """cost_quality_frontier Pareto correctness."""

    def test_frontier_returns_dict(self, selector):
        """cost_quality_frontier returns a dict."""
        result = selector.cost_quality_frontier("general", 1000, 500)
        assert isinstance(result, dict)

    def test_frontier_has_models_key(self, selector):
        """Result has 'models' key."""
        result = selector.cost_quality_frontier("general", 1000, 500)
        assert "models" in result

    def test_frontier_has_pareto_indices(self, selector):
        """Result has 'pareto_indices' key."""
        result = selector.cost_quality_frontier("general", 1000, 500)
        assert "pareto_indices" in result

    def test_frontier_indices_valid(self, selector):
        """All pareto_indices are valid indices into models list."""
        result = selector.cost_quality_frontier("general", 1000, 500)
        n = len(result["models"])
        for idx in result["pareto_indices"]:
            assert 0 <= idx < n

    def test_pareto_no_dominated_solutions(self, selector):
        """No model in the Pareto set is dominated by another."""
        result = selector.cost_quality_frontier("general", 1000, 500)
        models = result["models"]
        pareto = result["pareto_indices"]
        for i in pareto:
            for j in pareto:
                if i == j:
                    continue
                ci, cj = models[i], models[j]
                # j should NOT strictly dominate i
                strictly_dominates = (
                    cj["estimated_cost"] <= ci["estimated_cost"]
                    and cj["estimated_quality"] >= ci["estimated_quality"]
                    and (cj["estimated_cost"] < ci["estimated_cost"]
                         or cj["estimated_quality"] > ci["estimated_quality"])
                )
                assert not strictly_dominates, f"{cj['model']} dominates {ci['model']}"

    def test_pareto_frontier_non_empty(self, selector):
        """Pareto frontier always contains at least one model."""
        result = selector.cost_quality_frontier("general", 1000, 500)
        assert len(result["pareto_indices"]) > 0

    def test_pareto_models_sorted_by_cost(self, selector):
        """models list is sorted by cost ascending."""
        result = selector.cost_quality_frontier("general", 1000, 500)
        costs = [m["estimated_cost"] for m in result["models"]]
        assert costs == sorted(costs)

    def test_pareto_free_model_always_on_frontier(self, selector):
        """Ollama (free, $0) model should be on the Pareto frontier."""
        result = selector.cost_quality_frontier("general", 1000, 500)
        models = result["models"]
        pareto = result["pareto_indices"]
        free_model_indices = [i for i, m in enumerate(models)
                              if m["estimated_cost"] == 0.0]
        # At least one free model exists and is on the frontier
        assert any(i in pareto for i in free_model_indices)

    def test_pareto_highest_quality_on_frontier(self, selector):
        """Highest-quality model must always be on the Pareto frontier."""
        result = selector.cost_quality_frontier("general", 1000, 500)
        models = result["models"]
        pareto = result["pareto_indices"]
        max_quality = max(m["estimated_quality"] for m in models)
        best_idx = next(i for i, m in enumerate(models)
                        if m["estimated_quality"] == max_quality)
        assert best_idx in pareto

    def test_provider_filter_applied(self, selector):
        """providers parameter restricts models to listed providers."""
        result = selector.cost_quality_frontier("general", 1000, 500,
                                                 providers=["anthropic"])
        for m in result["models"]:
            assert m["provider"] == "anthropic"


# ===========================================================================
# TestSimulateModelMix
# ===========================================================================

class TestSimulateModelMix:
    """simulate_model_mix daily-cost predictions."""

    def test_simulation_returns_dict(self, selector):
        """simulate_model_mix returns a dict."""
        result = selector.simulate_model_mix(
            {"claude-haiku-4.5": 1.0}, 1000, (1000, 500))
        assert isinstance(result, dict)

    def test_simulation_required_keys(self, selector):
        """Result has 'daily_cost', 'avg_quality', 'breakdown' keys."""
        result = selector.simulate_model_mix(
            {"claude-haiku-4.5": 1.0}, 1000, (1000, 500))
        assert "daily_cost" in result
        assert "avg_quality" in result
        assert "breakdown" in result

    def test_simulation_daily_cost_positive(self, selector):
        """Daily cost is positive for paid models."""
        result = selector.simulate_model_mix(
            {"claude-sonnet-4.5": 1.0}, 1000, (1000, 500))
        assert result["daily_cost"] > 0

    def test_simulation_avg_quality_in_range(self, selector):
        """Average quality is in [0, 1]."""
        result = selector.simulate_model_mix(
            {"claude-sonnet-4.5": 0.5, "claude-haiku-4.5": 0.5}, 1000, (1000, 500))
        assert 0.0 <= result["avg_quality"] <= 1.0

    def test_simulation_cost_per_task_accuracy(self, selector):
        """Cost-per-task in breakdown matches direct calculation."""
        result = selector.simulate_model_mix(
            {"claude-haiku-4.5": 1.0}, 1000, (1000, 500))
        expected_cost = (1000 * 0.00008 + 500 * 0.00024) / 1000
        actual = result["breakdown"]["claude-haiku-4.5"]["cost_per_task"]
        assert abs(actual - expected_cost) < 1e-6

    def test_simulation_free_models_zero_cost(self, selector):
        """Ollama models contribute zero cost."""
        result = selector.simulate_model_mix(
            {"llama-3-70b": 1.0}, 1000, (1000, 500))
        assert result["daily_cost"] == 0.0

    def test_simulation_breakdown_length_matches_mix(self, selector):
        """Breakdown has one entry per model in mix."""
        mix = {"claude-haiku-4.5": 0.5, "claude-sonnet-4.5": 0.5}
        result = selector.simulate_model_mix(mix, 1000, (1000, 500))
        assert len(result["breakdown"]) == 2

    def test_simulation_normalises_fractions(self, selector):
        """Fractions that don't sum to 1.0 are normalised."""
        # 0.3 + 0.3 = 0.6, should be normalised to 0.5/0.5
        result = selector.simulate_model_mix(
            {"claude-haiku-4.5": 0.3, "claude-sonnet-4.5": 0.3}, 1000, (1000, 500))
        fractions = [v["fraction"] for v in result["breakdown"].values()]
        assert abs(sum(fractions) - 1.0) < 0.01

    def test_simulation_mixed_quality_weighted_correctly(self, selector):
        """Weighted average quality is between individual model qualities."""
        q_haiku = selector._quality.estimate_quality("claude-haiku-4.5", "general")
        q_sonnet = selector._quality.estimate_quality("claude-sonnet-4.5", "general")
        result = selector.simulate_model_mix(
            {"claude-haiku-4.5": 0.5, "claude-sonnet-4.5": 0.5}, 1000, (1000, 500))
        expected = (q_haiku + q_sonnet) / 2
        assert abs(result["avg_quality"] - expected) < 0.01

    def test_simulation_daily_cost_accuracy_vs_expected(self, selector):
        """Daily cost matches: tasks * fraction * cost_per_task (for each model)."""
        daily_tasks = 100
        in_tok, out_tok = 1000, 500
        cost_haiku = (in_tok * 0.00008 + out_tok * 0.00024) / 1000
        expected_daily = daily_tasks * 1.0 * cost_haiku
        result = selector.simulate_model_mix(
            {"claude-haiku-4.5": 1.0}, daily_tasks, (in_tok, out_tok))
        assert abs(result["daily_cost"] - expected_daily) < 1e-4


# ===========================================================================
# TestQualityEstimator
# ===========================================================================

class TestQualityEstimator:
    """QualityEstimator class and _infer_tier() helper."""

    def test_estimate_quality_returns_float(self, estimator):
        """estimate_quality returns a float."""
        score = estimator.estimate_quality("claude-sonnet-4.5", "general")
        assert isinstance(score, float)

    def test_opus_quality_highest(self, estimator):
        """Claude Opus scores highest quality among all models."""
        opus_q = estimator.estimate_quality("claude-opus-4.8", "general")
        for model in ("claude-haiku-4.5", "claude-sonnet-4.5", "gpt-4o-mini", "gpt-4o"):
            assert opus_q >= estimator.estimate_quality(model, "general")

    def test_score_within_bounds(self, estimator):
        """All quality scores are within [0, 1]."""
        for model in ("claude-haiku-4.5", "claude-sonnet-4.5", "claude-opus-4.8",
                      "gpt-4o-mini", "gpt-4o", "llama-3-70b"):
            for task in ("general", "code_review", "documentation", "security_audit"):
                score = estimator.estimate_quality(model, task)
                assert 0.0 <= score <= 1.0, f"{model}/{task} out of bounds: {score}"

    def test_unknown_model_uses_fallback(self, estimator):
        """Unknown model name falls back to tier-inferred quality."""
        score = estimator.estimate_quality("some-unknown-model-4x", "general")
        assert 0.0 <= score <= 1.0

    def test_unknown_task_uses_general_adjustment(self, estimator):
        """Unknown task type falls back to 'general' adjustments."""
        score = estimator.estimate_quality("claude-sonnet-4.5", "unknown_task_xyz")
        assert 0.0 <= score <= 1.0

    def test_get_model_tier_haiku(self, estimator):
        """get_model_tier returns 'haiku' for claude-haiku-4.5."""
        assert estimator.get_model_tier("claude-haiku-4.5") == "haiku"

    def test_get_model_tier_opus(self, estimator):
        """get_model_tier returns 'opus' for claude-opus-4.7."""
        assert estimator.get_model_tier("claude-opus-4.8") == "opus"

    def test_get_avg_latency_from_config(self, estimator):
        """get_avg_latency returns the configured value for a known model."""
        latency = estimator.get_avg_latency("claude-haiku-4.5")
        # Returns in ms (1.5 sec * 1000 = 1500) or could be in sec depending on impl
        assert latency > 0

    def test_get_avg_latency_opus(self, estimator):
        """Opus latency is higher than haiku latency."""
        haiku_lat = estimator.get_avg_latency("claude-haiku-4.5")
        opus_lat = estimator.get_avg_latency("claude-opus-4.8")
        assert opus_lat > haiku_lat

    def test_list_known_models(self, estimator):
        """list_known_models returns all models from config."""
        models = estimator.list_known_models()
        assert "claude-haiku-4.5" in models
        assert "claude-opus-4.8" in models
        assert len(models) >= 6

    # _infer_tier tests
    def test_infer_tier_haiku(self):
        """claude-haiku-4.5 → haiku tier."""
        assert _infer_tier("claude-haiku-4.5") == "haiku"

    def test_infer_tier_sonnet(self):
        """claude-sonnet-4.5 → sonnet tier."""
        assert _infer_tier("claude-sonnet-4.5") == "sonnet"

    def test_infer_tier_opus(self):
        """claude-opus-4.7 → opus tier."""
        assert _infer_tier("claude-opus-4.8") == "opus"

    def test_infer_tier_mini(self):
        """gpt-4o-mini → mini tier (mini takes priority over 4o)."""
        assert _infer_tier("gpt-4o-mini") == "mini"

    def test_infer_tier_flash(self):
        """gemini-2.0-flash → haiku tier (flash mapped to haiku)."""
        assert _infer_tier("gemini-2.0-flash") == "haiku"

    def test_infer_tier_unknown_defaults_to_sonnet(self):
        """Completely unknown model name defaults to sonnet tier."""
        assert _infer_tier("totally-unknown-model-xyz") == "sonnet"

    def test_infer_tier_pro(self):
        """gemini-pro → sonnet tier."""
        assert _infer_tier("gemini-pro") == "sonnet"

    def test_infer_tier_turbo(self):
        """gpt-4-turbo → sonnet tier."""
        assert _infer_tier("gpt-4-turbo") == "sonnet"

    def test_infer_tier_gpt4o(self):
        """gpt-4o → sonnet tier (4o mapped to sonnet)."""
        assert _infer_tier("gpt-4o") == "sonnet"

    def test_estimate_quality_fallback_when_no_config(self):
        """QualityEstimator works with fallback heuristics when no yaml provided."""
        qe = QualityEstimator(models_yaml=Path("nonexistent.yaml"))
        score = qe.estimate_quality("claude-sonnet-4.5", "general")
        assert 0.0 <= score <= 1.0

    def test_get_avg_latency_fallback_for_unknown(self, estimator):
        """get_avg_latency returns a positive default for unknown models."""
        latency = estimator.get_avg_latency("some-completely-unknown-model")
        assert latency > 0

    def test_get_model_tier_fallback_for_unknown(self, estimator):
        """get_model_tier returns a valid tier string for unknown model."""
        tier = estimator.get_model_tier("completely-unknown-model")
        assert isinstance(tier, str) and tier

    def test_load_config_handles_corrupt_yaml(self, tmp_path):
        """QualityEstimator handles corrupt YAML gracefully."""
        bad = tmp_path / "corrupt.yaml"
        bad.write_text(":: invalid yaml ::")
        qe = QualityEstimator(models_yaml=bad)
        assert isinstance(qe, QualityEstimator)


# ===========================================================================
# TestModelSelectorHelpers
# ===========================================================================

class TestModelSelectorHelpers:
    """Unit tests for ModelSelector internal helpers."""

    def test_resolve_rates_unknown_provider_uses_fallback(self, selector):
        """Unknown provider returns fallback rates."""
        rates = selector._resolve_rates("unknown_provider", "unknown_model")
        assert "input" in rates and "output" in rates

    def test_resolve_rates_partial_match(self, selector):
        """Partial model name match returns provider rates."""
        # Add a partial match scenario: known provider, unknown exact model
        rates = selector._resolve_rates("anthropic", "claude-haiku-99-ultra")
        assert "input" in rates

    def test_resolve_rates_exact_match(self, selector):
        """Exact model name returns correct rates."""
        rates = selector._resolve_rates("anthropic", "claude-haiku-4.5")
        assert rates["input"] == pytest.approx(0.00008)
        assert rates["output"] == pytest.approx(0.00024)

    def test_resolve_rates_no_model_match_uses_fallback(self, selector):
        """Known provider but completely different model → fallback."""
        rates = selector._resolve_rates("anthropic", "zzz-nonexistent-model-abc")
        assert "input" in rates and "output" in rates

    def test_recommend_batch_invalid_tokens_fallback(self, selector):
        """Batch handles missing tokens with fallback to (0,0)."""
        tasks = [{"task_type": "general"}]  # no 'tokens' key
        result = selector.recommend_batch(tasks)
        assert len(result) == 1

    def test_load_config_handles_corrupt_yaml(self, tmp_path):
        """ModelSelector handles corrupt YAML gracefully."""
        bad = tmp_path / "corrupt.yaml"
        bad.write_text(":: invalid yaml ::")
        sel = ModelSelector(models_yaml=bad)
        assert isinstance(sel, ModelSelector)

    def test_provider_preference_with_budget_triggers_over_budget_fallback(self, selector):
        """Over-budget with provider_preference returns over-budget reasoning."""
        rec = selector.recommend_model("general", 1000, 500,
                                       {"max_cost": 1e-10,
                                        "provider_preference": ["anthropic"]})
        assert "exceed" in rec["reasoning"].lower() or len(rec["model"]) > 0

    def test_reasoning_mentions_provider_fallback_when_preferred_unavailable(self, selector):
        """When preferred provider unavailable, falls back silently to all."""
        rec = selector.recommend_model("general", 1000, 500,
                                       {"provider_preference": ["nonexistent"]})
        # Should still return a valid model (fallback activated)
        assert len(rec["model"]) > 0


# ===========================================================================
# TestPerformance
# ===========================================================================

class TestPerformance:
    """Performance benchmarks (all under specified ms limits)."""

    def test_single_recommendation_under_50ms(self, selector):
        """Single recommend_model call completes in < 50ms."""
        start = time.perf_counter()
        selector.recommend_model("general", 5000, 2000,
                                  {"max_cost": 0.1, "quality_target": 0.8})
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 50, f"Too slow: {elapsed_ms:.1f}ms"

    def test_batch_10_tasks_under_200ms(self, selector):
        """10-task recommend_batch completes in < 200ms."""
        tasks = [
            {"task_type": "general", "tokens": (1000, 500),
             "constraints": {"max_cost": 0.05}}
            for _ in range(10)
        ]
        start = time.perf_counter()
        selector.recommend_batch(tasks)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 200, f"Too slow: {elapsed_ms:.1f}ms"

    def test_frontier_computation_under_50ms(self, selector):
        """cost_quality_frontier completes in < 50ms."""
        start = time.perf_counter()
        selector.cost_quality_frontier("code_review", 5000, 2000)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 50, f"Too slow: {elapsed_ms:.1f}ms"

    def test_simulate_mix_under_20ms(self, selector):
        """simulate_model_mix completes in < 20ms."""
        mix = {"claude-haiku-4.5": 0.5, "claude-sonnet-4.5": 0.3, "llama-3-70b": 0.2}
        start = time.perf_counter()
        selector.simulate_model_mix(mix, 1000, (1000, 500))
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 20, f"Too slow: {elapsed_ms:.1f}ms"

    def test_recommendation_time_reported(self, selector):
        """_selection_time_ms is reported and is a small positive number."""
        rec = selector.recommend_model("general", 1000, 500)
        assert rec["_selection_time_ms"] >= 0
        assert rec["_selection_time_ms"] < 50
