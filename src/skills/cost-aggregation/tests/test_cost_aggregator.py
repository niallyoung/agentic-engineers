"""
Tests for cost-aggregation skill (COST-002).

Coverage:
  - CostAggregator initialisation (providers.yaml paths, missing yaml, etc.)
  - Per-provider cost calculations (accuracy ±2% vs published rates)
  - aggregate_task_cost() — all providers, partial sets, winner, savings
  - cost_trend_for_provider() — date ranges, empty data, accumulation
  - record_usage() — persistence, accumulation, unknown provider
  - provider_health_check() — env-var based status, caching, invalidation
  - Provider adapters (each provider independently)
  - BaseProvider — rate loading, fallback, known_models
  - OllamaProvider — always zero-cost
  - Edge cases: zero tokens, unknown models, very large counts, bad dates
  - Performance: aggregate_task_cost < 100ms
"""

from __future__ import annotations

import json
import os
import time
import pytest
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict
import sys

# Bootstrap import path so tests can import from scripts/
_SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_SKILL_ROOT))

from scripts.cost_aggregator import (
    CostAggregator,
    SUPPORTED_PROVIDERS,
    DATE_FMT,
    ZERO_COST_THRESHOLD,
    _date_range,
    _utcnow,
    _utcdate,
)
from scripts.providers.base_provider import BaseProvider
from scripts.providers.anthropic_provider import AnthropicProvider
from scripts.providers.openai_provider import OpenAIProvider
from scripts.providers.google_provider import GoogleProvider
from scripts.providers.copilot_provider import CopilotProvider
from scripts.providers.ollama_provider import OllamaProvider


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture()
def providers_yaml(tmp_path: Path) -> Path:
    """Minimal providers.yaml for deterministic tests."""
    content = """
providers:
  anthropic:
    auth_env: ANTHROPIC_API_KEY
    models:
      claude-sonnet-4.6:
        input_per_1m: 3.00
        output_per_1m: 15.00
      claude-haiku-4.5:
        input_per_1m: 0.25
        output_per_1m: 1.25
      claude-opus-4.7:
        input_per_1m: 15.00
        output_per_1m: 75.00
    fallback:
      input_per_1m: 3.00
      output_per_1m: 15.00
  openai:
    auth_env: OPENAI_API_KEY
    models:
      gpt-5.4:
        input_per_1m: 6.00
        output_per_1m: 16.00
      gpt-4o:
        input_per_1m: 2.50
        output_per_1m: 10.00
      gpt-4o-mini:
        input_per_1m: 0.15
        output_per_1m: 0.60
    fallback:
      input_per_1m: 2.50
      output_per_1m: 10.00
  google:
    auth_env: GOOGLE_API_KEY
    models:
      gemini-2.0:
        input_per_1m: 6.00
        output_per_1m: 5.00
      gemini-2.0-flash:
        input_per_1m: 0.075
        output_per_1m: 0.30
    fallback:
      input_per_1m: 1.25
      output_per_1m: 5.00
  copilot:
    auth_env: GITHUB_TOKEN
    models:
      claude-sonnet-4.6:
        input_per_1m: 1.00
        output_per_1m: 1.50
      gpt-4o-mini:
        input_per_1m: 0.10
        output_per_1m: 0.20
    fallback:
      input_per_1m: 1.00
      output_per_1m: 1.50
  ollama:
    auth_env: null
    zero_cost: true
    models:
      mistral:latest:
        input_per_1m: 0.0
        output_per_1m: 0.0
    fallback:
      input_per_1m: 0.0
      output_per_1m: 0.0
"""
    p = tmp_path / "providers.yaml"
    p.write_text(content)
    return p


@pytest.fixture()
def data_dir(tmp_path: Path) -> Path:
    """Isolated data directory for usage records."""
    d = tmp_path / "cost-aggregation"
    d.mkdir()
    return d


@pytest.fixture()
def agg(providers_yaml: Path, data_dir: Path) -> CostAggregator:
    """CostAggregator backed by tmp paths."""
    return CostAggregator(providers_yaml=providers_yaml, data_dir=data_dir)


@pytest.fixture()
def all_model_variants() -> Dict[str, str]:
    """Standard model variant mapping for aggregate tests."""
    return {
        "anthropic": "claude-sonnet-4.6",
        "openai": "gpt-5.4",
        "google": "gemini-2.0",
        "copilot": "claude-sonnet-4.6",
        "ollama": "mistral:latest",
    }


# ===========================================================================
# Helpers
# ===========================================================================

def cost_for(input_tokens: int, output_tokens: int, in_per_1m: float, out_per_1m: float) -> float:
    """Reference cost calculation (mirrors BaseProvider.calculate_cost)."""
    return (input_tokens * in_per_1m + output_tokens * out_per_1m) / 1_000_000.0


# ===========================================================================
# Module-level helpers
# ===========================================================================

class TestHelpers:
    """Tests for module-level helper functions."""

    def test_utcnow_returns_utc_datetime(self):
        dt = _utcnow()
        assert dt.tzinfo == timezone.utc

    def test_utcdate_parses_correctly(self):
        dt = _utcdate("2026-05-01")
        assert dt.year == 2026
        assert dt.month == 5
        assert dt.day == 1

    def test_date_range_single_day(self):
        result = _date_range("2026-05-01", "2026-05-01")
        assert result == ["2026-05-01"]

    def test_date_range_multiple_days(self):
        result = _date_range("2026-05-01", "2026-05-03")
        assert result == ["2026-05-01", "2026-05-02", "2026-05-03"]

    def test_date_range_end_before_start_returns_empty(self):
        result = _date_range("2026-05-05", "2026-05-01")
        assert result == []

    def test_date_range_month_boundary(self):
        result = _date_range("2026-01-30", "2026-02-02")
        assert len(result) == 4
        assert result[0] == "2026-01-30"
        assert result[-1] == "2026-02-02"


# ===========================================================================
# CostAggregator — Initialisation
# ===========================================================================

class TestCostAggregatorInit:
    """Tests for CostAggregator initialisation."""

    def test_default_init_does_not_crash(self):
        """Default init should not raise even if providers.yaml missing."""
        agg = CostAggregator()
        assert agg is not None

    def test_init_with_custom_providers_yaml(self, providers_yaml, data_dir):
        agg = CostAggregator(providers_yaml=providers_yaml, data_dir=data_dir)
        assert len(agg.list_providers()) == 5

    def test_list_providers_returns_all_five(self, agg):
        providers = agg.list_providers()
        assert set(providers) == {"anthropic", "openai", "google", "copilot", "ollama"}

    def test_init_missing_yaml_uses_builtin_rates(self, tmp_path, data_dir):
        missing = tmp_path / "nonexistent.yaml"
        agg = CostAggregator(providers_yaml=missing, data_dir=data_dir)
        # Should still work with built-in rates
        cost = agg.get_adapter("anthropic").calculate_cost(1000, 500, "claude-sonnet-4.6")
        assert cost > 0

    def test_init_malformed_yaml_uses_builtin_rates(self, tmp_path, data_dir):
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("this: is: not: valid: yaml: [[[")
        agg = CostAggregator(providers_yaml=bad_yaml, data_dir=data_dir)
        # Should not raise — falls back to built-in rates
        assert agg is not None

    def test_custom_cache_ttl(self, providers_yaml, data_dir):
        agg = CostAggregator(
            providers_yaml=providers_yaml,
            data_dir=data_dir,
            cache_ttl_seconds=60,
        )
        assert agg._cache_ttl == 60

    def test_get_adapter_known_provider(self, agg):
        adapter = agg.get_adapter("anthropic")
        assert isinstance(adapter, AnthropicProvider)

    def test_get_adapter_unknown_provider_raises(self, agg):
        with pytest.raises(KeyError, match="meta"):
            agg.get_adapter("meta")


# ===========================================================================
# BaseProvider
# ===========================================================================

class TestBaseProvider:
    """Tests for the BaseProvider abstract base class via a concrete subclass."""

    def _make_concrete(self, config=None):
        """Instantiate a concrete provider with given config."""
        cfg = config or {}

        class _ConcreteProvider(BaseProvider):
            PROVIDER_NAME = "test"

            def health_check(self):
                return {"status": "healthy"}

        return _ConcreteProvider(cfg)

    def test_calculate_cost_known_model(self):
        p = self._make_concrete({
            "models": {"m1": {"input_per_1m": 2.0, "output_per_1m": 8.0}},
            "fallback": {"input_per_1m": 1.0, "output_per_1m": 4.0},
        })
        cost = p.calculate_cost(1_000_000, 1_000_000, "m1")
        assert cost == pytest.approx(10.0)  # 2 + 8

    def test_calculate_cost_uses_fallback_for_unknown_model(self):
        p = self._make_concrete({
            "models": {},
            "fallback": {"input_per_1m": 1.0, "output_per_1m": 4.0},
        })
        cost = p.calculate_cost(1_000_000, 1_000_000, "unknown-model")
        assert cost == pytest.approx(5.0)  # 1 + 4

    def test_calculate_cost_zero_tokens(self):
        p = self._make_concrete({
            "models": {"m1": {"input_per_1m": 10.0, "output_per_1m": 20.0}},
        })
        assert p.calculate_cost(0, 0, "m1") == pytest.approx(0.0)

    def test_calculate_cost_only_input(self):
        p = self._make_concrete({
            "models": {"m1": {"input_per_1m": 2.0, "output_per_1m": 8.0}},
        })
        cost = p.calculate_cost(500_000, 0, "m1")
        assert cost == pytest.approx(1.0)

    def test_calculate_cost_only_output(self):
        p = self._make_concrete({
            "models": {"m1": {"input_per_1m": 2.0, "output_per_1m": 8.0}},
        })
        cost = p.calculate_cost(0, 500_000, "m1")
        assert cost == pytest.approx(4.0)

    def test_calculate_cost_large_tokens(self):
        p = self._make_concrete({
            "models": {"m1": {"input_per_1m": 3.0, "output_per_1m": 15.0}},
        })
        cost = p.calculate_cost(10_000_000, 5_000_000, "m1")
        assert cost == pytest.approx(30.0 + 75.0)

    def test_known_models_returns_list(self):
        p = self._make_concrete({
            "models": {
                "m1": {"input_per_1m": 1.0, "output_per_1m": 2.0},
                "m2": {"input_per_1m": 3.0, "output_per_1m": 6.0},
            },
        })
        assert set(p.known_models()) == {"m1", "m2"}

    def test_is_zero_cost_false_by_default(self):
        p = self._make_concrete()
        assert p.is_zero_cost() is False

    def test_is_zero_cost_true_when_configured(self):
        p = self._make_concrete({"zero_cost": True})
        assert p.is_zero_cost() is True

    def test_get_rates_returns_fallback_for_unknown(self):
        p = self._make_concrete({
            "fallback": {"input_per_1m": 9.0, "output_per_1m": 18.0},
        })
        rates = p.get_rates("nonexistent")
        assert rates["input_per_1m"] == pytest.approx(9.0)
        assert rates["output_per_1m"] == pytest.approx(18.0)


# ===========================================================================
# AnthropicProvider
# ===========================================================================

class TestAnthropicProvider:
    """Tests for Anthropic cost calculations."""

    @pytest.fixture()
    def provider(self, providers_yaml):
        import yaml as _yaml
        data = _yaml.safe_load(providers_yaml.read_text())
        return AnthropicProvider(data["providers"]["anthropic"])

    def test_claude_sonnet_46_cost(self, provider):
        """5000 in + 2000 out @ $3/$15 per 1M = $0.045"""
        cost = provider.calculate_cost(5000, 2000, "claude-sonnet-4.6")
        assert cost == pytest.approx(0.045, rel=0.02)

    def test_claude_haiku_45_cost(self, provider):
        """$0.25/$1.25 per 1M"""
        cost = provider.calculate_cost(1_000_000, 1_000_000, "claude-haiku-4.5")
        assert cost == pytest.approx(0.25 + 1.25)

    def test_claude_opus_47_cost(self, provider):
        """$15/$75 per 1M"""
        cost = provider.calculate_cost(1_000_000, 1_000_000, "claude-opus-4.8")
        assert cost == pytest.approx(15.0 + 75.0)

    def test_unknown_model_uses_sonnet_fallback(self, providers_yaml):
        """Fallback for unknown model should be sonnet rates ($3/$15)"""
        import yaml as _yaml
        data = _yaml.safe_load(providers_yaml.read_text())
        provider = AnthropicProvider(data["providers"]["anthropic"])
        cost_fallback = provider.calculate_cost(1_000_000, 1_000_000, "claude-unknown-99")
        assert cost_fallback == pytest.approx(3.0 + 15.0)

    def test_zero_tokens_returns_zero(self, provider):
        assert provider.calculate_cost(0, 0, "claude-sonnet-4.6") == pytest.approx(0.0)

    def test_health_check_without_env_var(self, provider, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        health = provider.health_check()
        assert health["status"] == "unknown"
        assert "ANTHROPIC_API_KEY" in health.get("reason", "")

    def test_health_check_with_env_var(self, provider, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        health = provider.health_check()
        assert health["status"] == "healthy"
        assert "last_checked" in health

    def test_health_check_has_timestamp(self, provider, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        health = provider.health_check()
        ts = health["last_checked"]
        # Should be parseable as ISO-8601
        datetime.fromisoformat(ts.replace("Z", "+00:00"))

    def test_builtin_model_haiku_exists(self):
        """Built-in rates should always include haiku even with empty config."""
        provider = AnthropicProvider({})
        assert "claude-haiku-4.5" in provider.known_models()

    def test_builtin_model_sonnet_exists(self):
        provider = AnthropicProvider({})
        assert "claude-sonnet-4.6" in provider.known_models()

    def test_accuracy_within_2_percent(self, provider):
        """Cost accuracy ±2% quality gate."""
        expected = cost_for(5000, 2000, 3.0, 15.0)
        actual = provider.calculate_cost(5000, 2000, "claude-sonnet-4.6")
        assert actual == pytest.approx(expected, rel=0.02)


# ===========================================================================
# OpenAIProvider
# ===========================================================================

class TestOpenAIProvider:
    """Tests for OpenAI cost calculations."""

    @pytest.fixture()
    def provider(self, providers_yaml):
        import yaml as _yaml
        data = _yaml.safe_load(providers_yaml.read_text())
        return OpenAIProvider(data["providers"]["openai"])

    def test_gpt_54_cost(self, provider):
        """5000 in + 2000 out @ $6/$16 per 1M = $0.062"""
        cost = provider.calculate_cost(5000, 2000, "gpt-5.4")
        assert cost == pytest.approx(0.062, rel=0.02)

    def test_gpt_4o_cost(self, provider):
        """$2.50/$10 per 1M"""
        cost = provider.calculate_cost(1_000_000, 1_000_000, "gpt-4o")
        assert cost == pytest.approx(2.50 + 10.0)

    def test_gpt_4o_mini_cost(self, provider):
        """$0.15/$0.60 per 1M"""
        cost = provider.calculate_cost(1_000_000, 1_000_000, "gpt-4o-mini")
        assert cost == pytest.approx(0.15 + 0.60)

    def test_unknown_model_uses_fallback(self, providers_yaml):
        import yaml as _yaml
        data = _yaml.safe_load(providers_yaml.read_text())
        provider = OpenAIProvider(data["providers"]["openai"])
        # Fallback is gpt-4o rates: $2.50/$10
        cost = provider.calculate_cost(1_000_000, 1_000_000, "gpt-99-super")
        assert cost == pytest.approx(2.50 + 10.0)

    def test_zero_tokens_returns_zero(self, provider):
        assert provider.calculate_cost(0, 0, "gpt-4o") == pytest.approx(0.0)

    def test_health_check_without_env_var(self, provider, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        health = provider.health_check()
        assert health["status"] == "unknown"

    def test_health_check_with_env_var(self, provider, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        health = provider.health_check()
        assert health["status"] == "healthy"

    def test_builtin_gpt4_exists(self):
        provider = OpenAIProvider({})
        assert "gpt-4" in provider.known_models()

    def test_accuracy_within_2_percent(self, provider):
        expected = cost_for(5000, 2000, 6.0, 16.0)
        actual = provider.calculate_cost(5000, 2000, "gpt-5.4")
        assert actual == pytest.approx(expected, rel=0.02)


# ===========================================================================
# GoogleProvider
# ===========================================================================

class TestGoogleProvider:
    """Tests for Google Gemini cost calculations."""

    @pytest.fixture()
    def provider(self, providers_yaml):
        import yaml as _yaml
        data = _yaml.safe_load(providers_yaml.read_text())
        return GoogleProvider(data["providers"]["google"])

    def test_gemini_20_cost(self, provider):
        """5000 in + 2000 out @ $6/$5 per 1M = $0.040"""
        cost = provider.calculate_cost(5000, 2000, "gemini-2.0")
        assert cost == pytest.approx(0.040, rel=0.02)

    def test_gemini_flash_cost(self, provider):
        """$0.075/$0.30 per 1M"""
        cost = provider.calculate_cost(1_000_000, 1_000_000, "gemini-2.0-flash")
        assert cost == pytest.approx(0.075 + 0.30)

    def test_unknown_model_uses_fallback(self, providers_yaml):
        import yaml as _yaml
        data = _yaml.safe_load(providers_yaml.read_text())
        provider = GoogleProvider(data["providers"]["google"])
        # Fallback is $1.25/$5.00
        cost = provider.calculate_cost(1_000_000, 1_000_000, "gemini-99")
        assert cost == pytest.approx(1.25 + 5.00)

    def test_zero_tokens_returns_zero(self, provider):
        assert provider.calculate_cost(0, 0, "gemini-2.0") == pytest.approx(0.0)

    def test_health_check_without_env_var(self, provider, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        health = provider.health_check()
        assert health["status"] == "unknown"

    def test_health_check_with_env_var(self, provider, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "AIzaTest")
        health = provider.health_check()
        assert health["status"] == "healthy"

    def test_builtin_gemini_flash_exists(self):
        provider = GoogleProvider({})
        assert "gemini-2.0-flash" in provider.known_models()

    def test_accuracy_within_2_percent(self, provider):
        expected = cost_for(5000, 2000, 6.0, 5.0)
        actual = provider.calculate_cost(5000, 2000, "gemini-2.0")
        assert actual == pytest.approx(expected, rel=0.02)


# ===========================================================================
# CopilotProvider
# ===========================================================================

class TestCopilotProvider:
    """Tests for GitHub Copilot cost calculations."""

    @pytest.fixture()
    def provider(self, providers_yaml):
        import yaml as _yaml
        data = _yaml.safe_load(providers_yaml.read_text())
        return CopilotProvider(data["providers"]["copilot"])

    def test_copilot_sonnet_cost(self, provider):
        """5000 in + 2000 out @ $1/$1.5 per 1M = $0.008"""
        cost = provider.calculate_cost(5000, 2000, "claude-sonnet-4.6")
        assert cost == pytest.approx(0.008, rel=0.02)

    def test_copilot_gpt4o_mini_cost(self, provider):
        """$0.10/$0.20 per 1M"""
        cost = provider.calculate_cost(1_000_000, 1_000_000, "gpt-4o-mini")
        assert cost == pytest.approx(0.10 + 0.20)

    def test_copilot_cheaper_than_direct_api(self, providers_yaml):
        """Copilot should be cheaper than direct Anthropic for same model."""
        import yaml as _yaml
        data = _yaml.safe_load(providers_yaml.read_text())
        copilot = CopilotProvider(data["providers"]["copilot"])
        anthropic = AnthropicProvider(data["providers"]["anthropic"])
        copilot_cost = copilot.calculate_cost(5000, 2000, "claude-sonnet-4.6")
        anthropic_cost = anthropic.calculate_cost(5000, 2000, "claude-sonnet-4.6")
        assert copilot_cost < anthropic_cost

    def test_zero_tokens_returns_zero(self, provider):
        assert provider.calculate_cost(0, 0, "claude-sonnet-4.6") == pytest.approx(0.0)

    def test_health_check_without_env_var(self, provider, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        health = provider.health_check()
        assert health["status"] == "unknown"
        assert "no API access" in health.get("reason", "")

    def test_health_check_with_env_var(self, provider, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "ghs_token123")
        health = provider.health_check()
        assert health["status"] == "healthy"

    def test_builtin_sonnet_exists(self):
        provider = CopilotProvider({})
        assert "claude-sonnet-4.6" in provider.known_models()

    def test_accuracy_within_2_percent(self, provider):
        expected = cost_for(5000, 2000, 1.0, 1.5)
        actual = provider.calculate_cost(5000, 2000, "claude-sonnet-4.6")
        assert actual == pytest.approx(expected, rel=0.02)


# ===========================================================================
# OllamaProvider
# ===========================================================================

class TestOllamaProvider:
    """Tests for Ollama (zero-cost local) provider."""

    @pytest.fixture()
    def provider(self, providers_yaml):
        import yaml as _yaml
        data = _yaml.safe_load(providers_yaml.read_text())
        return OllamaProvider(data["providers"]["ollama"])

    def test_mistral_always_zero(self, provider):
        assert provider.calculate_cost(5000, 2000, "mistral:latest") == 0.0

    def test_unknown_model_always_zero(self, provider):
        """Any model on Ollama is zero-cost."""
        assert provider.calculate_cost(999_999, 999_999, "llama99:latest") == 0.0

    def test_zero_tokens_always_zero(self, provider):
        assert provider.calculate_cost(0, 0, "mistral:latest") == 0.0

    def test_large_token_count_still_zero(self, provider):
        assert provider.calculate_cost(100_000_000, 50_000_000, "mistral:latest") == 0.0

    def test_is_zero_cost_true(self, provider):
        assert provider.is_zero_cost() is True

    def test_health_check_returns_healthy(self, provider):
        health = provider.health_check()
        assert health["status"] == "healthy"

    def test_health_check_has_note(self, provider):
        health = provider.health_check()
        assert "note" in health

    def test_health_check_no_env_var_needed(self, provider, monkeypatch):
        """Ollama doesn't require any env var."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        health = provider.health_check()
        assert health["status"] == "healthy"

    def test_builtin_rates_all_zero(self):
        """Even with empty config, Ollama fallback must be zero."""
        provider = OllamaProvider({})
        cost = provider.calculate_cost(1_000_000, 1_000_000, "any-model")
        assert cost == 0.0


# ===========================================================================
# CostAggregator.aggregate_task_cost
# ===========================================================================

class TestAggregateTaskCost:
    """Tests for CostAggregator.aggregate_task_cost()."""

    def test_all_five_providers_canonical_example(self, agg, all_model_variants):
        """Canonical example from the COST-002 spec."""
        result = agg.aggregate_task_cost(
            task_type="code_review",
            input_tokens=5000,
            output_tokens=2000,
            model_variants=all_model_variants,
        )
        assert result["anthropic"] == pytest.approx(0.045, rel=0.02)
        assert result["openai"] == pytest.approx(0.062, rel=0.02)
        assert result["google"] == pytest.approx(0.040, rel=0.02)
        assert result["copilot"] == pytest.approx(0.008, rel=0.02)
        assert result["ollama"] == pytest.approx(0.000, abs=1e-9)

    def test_winner_is_ollama(self, agg, all_model_variants):
        result = agg.aggregate_task_cost(
            task_type="code_review",
            input_tokens=5000,
            output_tokens=2000,
            model_variants=all_model_variants,
        )
        assert result["winner"] == "ollama"

    def test_savings_vs_cheapest_cloud_is_google(self, agg, all_model_variants):
        """Cheapest cloud provider is Google at $0.040; ollama saves $0.040."""
        result = agg.aggregate_task_cost(
            task_type="code_review",
            input_tokens=5000,
            output_tokens=2000,
            model_variants=all_model_variants,
        )
        assert result["savings_vs_cheapest_cloud"] == pytest.approx(0.040, rel=0.02)

    def test_partial_providers_subset(self, agg):
        """Works with a subset of providers."""
        result = agg.aggregate_task_cost(
            task_type="test",
            input_tokens=1000,
            output_tokens=500,
            model_variants={"anthropic": "claude-sonnet-4.6", "openai": "gpt-4o"},
        )
        assert "anthropic" in result
        assert "openai" in result
        assert "ollama" not in result
        assert result["winner"] in {"anthropic", "openai"}

    def test_winner_is_cheapest_provider(self, agg):
        """Winner is always the provider with minimum cost."""
        result = agg.aggregate_task_cost(
            task_type="test",
            input_tokens=1000,
            output_tokens=500,
            model_variants={"anthropic": "claude-opus-4.8", "openai": "gpt-4o-mini"},
        )
        # gpt-4o-mini should be cheaper than opus
        assert result["winner"] == "openai"

    def test_single_provider_is_winner(self, agg):
        """Single provider is always the winner."""
        result = agg.aggregate_task_cost(
            task_type="test",
            input_tokens=1000,
            output_tokens=500,
            model_variants={"anthropic": "claude-sonnet-4.6"},
        )
        assert result["winner"] == "anthropic"

    def test_only_ollama_winner_and_savings_zero(self, agg):
        """When only Ollama (no cloud API providers), winner=ollama, savings=0.0."""
        result = agg.aggregate_task_cost(
            task_type="test",
            input_tokens=1000,
            output_tokens=500,
            model_variants={"ollama": "mistral:latest"},
        )
        assert result["winner"] == "ollama"
        assert result["savings_vs_cheapest_cloud"] == 0.0

    def test_copilot_excluded_from_cheapest_cloud_baseline(self, agg):
        """Copilot is a managed service, not a direct cloud API — excluded from baseline."""
        result = agg.aggregate_task_cost(
            task_type="test",
            input_tokens=5000,
            output_tokens=2000,
            model_variants={
                "copilot": "claude-sonnet-4.6",  # $0.008
                "ollama": "mistral:latest",        # $0.000
            },
        )
        # No direct cloud providers → savings = 0
        assert result["savings_vs_cheapest_cloud"] == 0.0

    def test_unknown_provider_skipped(self, agg):
        """Unknown provider name is skipped, not fatal."""
        result = agg.aggregate_task_cost(
            task_type="test",
            input_tokens=1000,
            output_tokens=500,
            model_variants={
                "anthropic": "claude-sonnet-4.6",
                "meta": "llama-3-70b",  # not supported
            },
        )
        assert "anthropic" in result
        assert "meta" not in result

    def test_zero_tokens_all_zero_costs(self, agg, all_model_variants):
        result = agg.aggregate_task_cost(
            task_type="test",
            input_tokens=0,
            output_tokens=0,
            model_variants=all_model_variants,
        )
        for provider in ["anthropic", "openai", "google", "copilot", "ollama"]:
            assert result[provider] == pytest.approx(0.0)

    def test_very_large_token_counts(self, agg):
        """Large token counts don't overflow or raise."""
        result = agg.aggregate_task_cost(
            task_type="test",
            input_tokens=10_000_000,
            output_tokens=5_000_000,
            model_variants={"anthropic": "claude-sonnet-4.6"},
        )
        expected = cost_for(10_000_000, 5_000_000, 3.0, 15.0)
        assert result["anthropic"] == pytest.approx(expected, rel=0.02)

    def test_empty_model_variants_returns_minimal(self, agg):
        """Empty model_variants returns just winner=None and savings=0."""
        result = agg.aggregate_task_cost(
            task_type="test",
            input_tokens=1000,
            output_tokens=500,
            model_variants={},
        )
        assert result["winner"] is None
        assert result["savings_vs_cheapest_cloud"] == 0.0

    def test_result_contains_winner_key(self, agg, all_model_variants):
        result = agg.aggregate_task_cost(
            task_type="test",
            input_tokens=1000,
            output_tokens=500,
            model_variants=all_model_variants,
        )
        assert "winner" in result

    def test_result_contains_savings_key(self, agg, all_model_variants):
        result = agg.aggregate_task_cost(
            task_type="test",
            input_tokens=1000,
            output_tokens=500,
            model_variants=all_model_variants,
        )
        assert "savings_vs_cheapest_cloud" in result

    def test_savings_non_negative(self, agg, all_model_variants):
        result = agg.aggregate_task_cost(
            task_type="test",
            input_tokens=5000,
            output_tokens=2000,
            model_variants=all_model_variants,
        )
        assert result["savings_vs_cheapest_cloud"] >= 0.0

    def test_cost_values_are_non_negative(self, agg, all_model_variants):
        result = agg.aggregate_task_cost(
            task_type="test",
            input_tokens=5000,
            output_tokens=2000,
            model_variants=all_model_variants,
        )
        for provider in ["anthropic", "openai", "google", "copilot", "ollama"]:
            assert result[provider] >= 0.0

    def test_task_type_does_not_affect_cost(self, agg, all_model_variants):
        """task_type is metadata only and must not affect cost."""
        r1 = agg.aggregate_task_cost(
            task_type="code_review",
            input_tokens=5000,
            output_tokens=2000,
            model_variants=all_model_variants,
        )
        r2 = agg.aggregate_task_cost(
            task_type="planning",
            input_tokens=5000,
            output_tokens=2000,
            model_variants=all_model_variants,
        )
        assert r1["anthropic"] == pytest.approx(r2["anthropic"])
        assert r1["winner"] == r2["winner"]


# ===========================================================================
# CostAggregator.aggregate_task_cost — Performance
# ===========================================================================

class TestAggregatePerformance:
    """Performance tests for aggregate_task_cost (< 100ms requirement)."""

    def test_aggregation_under_100ms(self, agg, all_model_variants):
        """Quality gate: aggregation must complete in <100ms."""
        start = time.monotonic()
        agg.aggregate_task_cost(
            task_type="perf_test",
            input_tokens=5000,
            output_tokens=2000,
            model_variants=all_model_variants,
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 100.0, f"aggregate_task_cost took {elapsed_ms:.1f}ms (>100ms)"

    def test_aggregation_repeated_calls_fast(self, agg, all_model_variants):
        """100 consecutive calls should stay well under 10 seconds total."""
        start = time.monotonic()
        for _ in range(100):
            agg.aggregate_task_cost(
                task_type="batch",
                input_tokens=5000,
                output_tokens=2000,
                model_variants=all_model_variants,
            )
        elapsed = time.monotonic() - start
        assert elapsed < 10.0, f"100 calls took {elapsed:.2f}s"


# ===========================================================================
# CostAggregator.record_usage + cost_trend_for_provider
# ===========================================================================

class TestCostTrend:
    """Tests for record_usage() and cost_trend_for_provider()."""

    def test_trend_empty_range_returns_zero(self, agg):
        trend = agg.cost_trend_for_provider("anthropic", "2026-05-01", "2026-05-03")
        assert trend["total"] == pytest.approx(0.0)
        assert trend["avg_per_day"] == pytest.approx(0.0)
        assert len(trend["daily_spend"]) == 3

    def test_trend_includes_correct_dates(self, agg):
        trend = agg.cost_trend_for_provider("anthropic", "2026-05-01", "2026-05-03")
        dates = [d["date"] for d in trend["daily_spend"]]
        assert dates == ["2026-05-01", "2026-05-02", "2026-05-03"]

    def test_trend_single_day(self, agg):
        trend = agg.cost_trend_for_provider("anthropic", "2026-05-15", "2026-05-15")
        assert len(trend["daily_spend"]) == 1

    def test_trend_after_record_usage(self, agg):
        agg.record_usage("anthropic", "claude-sonnet-4.6", 5000, 2000, date="2026-05-10")
        trend = agg.cost_trend_for_provider("anthropic", "2026-05-10", "2026-05-10")
        assert trend["total"] == pytest.approx(0.045, rel=0.02)

    def test_trend_accumulates_multiple_records(self, agg):
        agg.record_usage("anthropic", "claude-sonnet-4.6", 5000, 2000, date="2026-05-10")
        agg.record_usage("anthropic", "claude-sonnet-4.6", 5000, 2000, date="2026-05-10")
        trend = agg.cost_trend_for_provider("anthropic", "2026-05-10", "2026-05-10")
        assert trend["total"] == pytest.approx(0.090, rel=0.02)

    def test_trend_across_multiple_days(self, agg):
        agg.record_usage("anthropic", "claude-sonnet-4.6", 5000, 2000, date="2026-05-10")
        agg.record_usage("anthropic", "claude-sonnet-4.6", 5000, 2000, date="2026-05-11")
        trend = agg.cost_trend_for_provider("anthropic", "2026-05-10", "2026-05-11")
        assert trend["total"] == pytest.approx(0.090, rel=0.02)
        assert trend["avg_per_day"] == pytest.approx(0.045, rel=0.02)

    def test_trend_missing_days_are_zero(self, agg):
        agg.record_usage("anthropic", "claude-sonnet-4.6", 5000, 2000, date="2026-05-11")
        trend = agg.cost_trend_for_provider("anthropic", "2026-05-10", "2026-05-12")
        day_spends = {d["date"]: d["spend"] for d in trend["daily_spend"]}
        assert day_spends["2026-05-10"] == pytest.approx(0.0)
        assert day_spends["2026-05-11"] == pytest.approx(0.045, rel=0.02)
        assert day_spends["2026-05-12"] == pytest.approx(0.0)

    def test_trend_unknown_provider_raises(self, agg):
        with pytest.raises(ValueError, match="Unknown provider"):
            agg.cost_trend_for_provider("meta", "2026-05-01", "2026-05-03")

    def test_trend_start_after_end_raises(self, agg):
        with pytest.raises(ValueError, match="start_date"):
            agg.cost_trend_for_provider("anthropic", "2026-05-10", "2026-05-01")

    def test_trend_returns_provider_field(self, agg):
        trend = agg.cost_trend_for_provider("openai", "2026-05-01", "2026-05-01")
        assert trend["provider"] == "openai"

    def test_record_usage_unknown_provider_raises(self, agg):
        with pytest.raises(ValueError, match="Unknown provider"):
            agg.record_usage("meta", "llama", 1000, 500)

    def test_record_usage_default_date_is_today(self, agg):
        today = _utcnow().strftime(DATE_FMT)
        agg.record_usage("anthropic", "claude-sonnet-4.6", 1000, 500)
        trend = agg.cost_trend_for_provider("anthropic", today, today)
        assert trend["total"] > 0.0

    def test_record_usage_creates_data_dir(self, providers_yaml, tmp_path):
        new_data_dir = tmp_path / "new-dir"
        assert not new_data_dir.exists()
        agg = CostAggregator(providers_yaml=providers_yaml, data_dir=new_data_dir)
        agg.record_usage("anthropic", "claude-sonnet-4.6", 1000, 500, date="2026-05-01")
        assert new_data_dir.exists()

    def test_trend_all_providers_supported(self, agg):
        for provider in SUPPORTED_PROVIDERS:
            trend = agg.cost_trend_for_provider(provider, "2026-05-01", "2026-05-01")
            assert "total" in trend

    def test_record_ollama_usage_records_zero(self, agg):
        agg.record_usage("ollama", "mistral:latest", 10000, 5000, date="2026-05-10")
        trend = agg.cost_trend_for_provider("ollama", "2026-05-10", "2026-05-10")
        assert trend["total"] == pytest.approx(0.0)


# ===========================================================================
# CostAggregator.provider_health_check
# ===========================================================================

class TestProviderHealthCheck:
    """Tests for provider_health_check() and its caching."""

    def test_health_check_returns_all_providers(self, agg):
        health = agg.provider_health_check()
        assert set(health.keys()) == {"anthropic", "openai", "google", "copilot", "ollama"}

    def test_ollama_always_healthy(self, agg):
        health = agg.provider_health_check()
        assert health["ollama"]["status"] == "healthy"

    def test_health_check_status_values_are_valid(self, agg):
        health = agg.provider_health_check()
        valid_statuses = {"healthy", "degraded", "unknown"}
        for provider, info in health.items():
            assert info["status"] in valid_statuses, (
                f"Provider '{provider}' has invalid status '{info['status']}'"
            )

    def test_health_check_has_last_checked_field(self, agg):
        health = agg.provider_health_check()
        for provider, info in health.items():
            assert "last_checked" in info, f"'{provider}' missing last_checked"

    def test_health_check_cached_second_call(self, agg, monkeypatch):
        """Second call within TTL should return cached result."""
        call_count = {"n": 0}
        original_health = agg._adapters["anthropic"].health_check

        def counting_health():
            call_count["n"] += 1
            return original_health()

        monkeypatch.setattr(agg._adapters["anthropic"], "health_check", counting_health)
        agg.provider_health_check()
        agg.provider_health_check()
        assert call_count["n"] == 1  # Only called once (second call cached)

    def test_health_cache_invalidation(self, agg, monkeypatch):
        """After invalidate_health_cache(), next call re-queries all providers."""
        call_count = {"n": 0}
        original_health = agg._adapters["anthropic"].health_check

        def counting_health():
            call_count["n"] += 1
            return original_health()

        monkeypatch.setattr(agg._adapters["anthropic"], "health_check", counting_health)
        agg.provider_health_check()
        agg.invalidate_health_cache()
        agg.provider_health_check()
        assert call_count["n"] == 2

    def test_health_check_with_all_env_vars(self, agg, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        monkeypatch.setenv("GOOGLE_API_KEY", "AIza-test")
        monkeypatch.setenv("GITHUB_TOKEN", "ghs-test")
        agg.invalidate_health_cache()
        health = agg.provider_health_check()
        assert health["anthropic"]["status"] == "healthy"
        assert health["openai"]["status"] == "healthy"
        assert health["google"]["status"] == "healthy"
        assert health["copilot"]["status"] == "healthy"
        assert health["ollama"]["status"] == "healthy"

    def test_health_check_without_any_env_vars(self, agg, monkeypatch):
        for env in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "GITHUB_TOKEN"]:
            monkeypatch.delenv(env, raising=False)
        agg.invalidate_health_cache()
        health = agg.provider_health_check()
        # Cloud providers should be unknown without keys
        assert health["anthropic"]["status"] == "unknown"
        assert health["openai"]["status"] == "unknown"
        assert health["google"]["status"] == "unknown"
        assert health["copilot"]["status"] == "unknown"
        # Ollama should always be healthy (local)
        assert health["ollama"]["status"] == "healthy"

    def test_health_check_unknown_has_reason(self, agg, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        agg.invalidate_health_cache()
        health = agg.provider_health_check()
        assert "reason" in health["anthropic"]

    def test_zero_ttl_never_caches(self, providers_yaml, data_dir, monkeypatch):
        """TTL=0 means every call re-queries."""
        agg = CostAggregator(
            providers_yaml=providers_yaml,
            data_dir=data_dir,
            cache_ttl_seconds=0,
        )
        call_count = {"n": 0}
        original_health = agg._adapters["anthropic"].health_check

        def counting_health():
            call_count["n"] += 1
            return original_health()

        monkeypatch.setattr(agg._adapters["anthropic"], "health_check", counting_health)
        agg.provider_health_check()
        agg.provider_health_check()
        assert call_count["n"] == 2
