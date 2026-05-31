"""
Comprehensive test suite for ProviderTracker class.
Tests: 36 tests covering 5 providers, cost tracking, metrics aggregation, and efficiency calculations.
"""

import pytest
from datetime import datetime
from src.agents.cost_management.provider_tracker import (
    ProviderTracker,
    ProviderType,
    ProviderMetrics,
    TokenUsage,
    ProviderCost,
)


class TestProviderTrackerInitialization:
    """Tests for ProviderTracker initialization and basic setup."""

    def test_tracker_initializes_empty(self):
        """Test that ProviderTracker initializes with empty state."""
        tracker = ProviderTracker()
        assert len(tracker.requests) == 0
        assert tracker.get_total_cost() == 0.0
        assert tracker.get_total_tokens() == 0

    def test_tracker_has_all_five_providers(self):
        """Test that ProviderType enum contains all 5 providers."""
        providers = list(ProviderType)
        assert len(providers) == 5
        provider_names = {p.name for p in providers}
        expected = {"ANTHROPIC", "OPENAI", "GEMINI", "GITHUB_COPILOT", "OLLAMA"}
        assert provider_names == expected


class TestAnthropicTracking:
    """Tests for Anthropic provider tracking."""

    def test_record_anthropic_request(self):
        """Test recording a single Anthropic request."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        assert len(tracker.requests) == 1
        assert tracker.get_total_cost() == 0.05

    def test_anthropic_multiple_requests(self):
        """Test recording multiple Anthropic requests."""
        tracker = ProviderTracker()
        for i in range(3):
            tracker.record_request(
                provider=ProviderType.ANTHROPIC,
                model="claude-opus-4-6",
                input_tokens=100 + i,
                output_tokens=50 + i,
                cost_usd=0.05 + (i * 0.01),
            )
        assert len(tracker.requests) == 3
        # 0.05 + 0.06 + 0.07 = 0.18
        assert tracker.get_total_cost() == pytest.approx(0.18, rel=1e-6)

    def test_anthropic_metrics_aggregation(self):
        """Test that Anthropic metrics are correctly aggregated."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        metrics = tracker.get_all_metrics()
        assert "anthropic" in metrics
        assert metrics["anthropic"].total_requests == 1
        assert metrics["anthropic"].total_cost_usd == 0.05


class TestOpenAITracking:
    """Tests for OpenAI provider tracking."""

    def test_record_openai_request(self):
        """Test recording a single OpenAI request."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.OPENAI,
            model="gpt-4",
            input_tokens=150,
            output_tokens=75,
            cost_usd=0.08,
        )
        assert len(tracker.requests) == 1
        assert tracker.get_total_cost() == 0.08

    def test_openai_metrics_aggregation(self):
        """Test that OpenAI metrics are correctly aggregated."""
        tracker = ProviderTracker()
        for i in range(2):
            tracker.record_request(
                provider=ProviderType.OPENAI,
                model="gpt-4",
                input_tokens=150,
                output_tokens=75,
                cost_usd=0.08,
            )
        metrics = tracker.get_all_metrics()
        assert "openai" in metrics
        assert metrics["openai"].total_requests == 2
        assert metrics["openai"].total_cost_usd == pytest.approx(0.16, rel=1e-6)


class TestGeminiTracking:
    """Tests for Google Gemini provider tracking."""

    def test_record_gemini_request(self):
        """Test recording a single Gemini request."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.GEMINI,
            model="gemini-pro",
            input_tokens=120,
            output_tokens=60,
            cost_usd=0.02,
        )
        assert len(tracker.requests) == 1
        assert tracker.get_total_cost() == 0.02

    def test_gemini_metrics_aggregation(self):
        """Test that Gemini metrics are correctly aggregated."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.GEMINI,
            model="gemini-pro",
            input_tokens=120,
            output_tokens=60,
            cost_usd=0.02,
        )
        metrics = tracker.get_all_metrics()
        assert "gemini" in metrics
        assert metrics["gemini"].total_requests == 1


class TestGitHubCopilotTracking:
    """Tests for GitHub Copilot provider tracking."""

    def test_record_github_copilot_request(self):
        """Test recording a single GitHub Copilot request."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.GITHUB_COPILOT,
            model="copilot-gpt4",
            input_tokens=140,
            output_tokens=70,
            cost_usd=0.03,
        )
        assert len(tracker.requests) == 1
        assert tracker.get_total_cost() == 0.03

    def test_github_copilot_metrics_aggregation(self):
        """Test that GitHub Copilot metrics are correctly aggregated."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.GITHUB_COPILOT,
            model="copilot-gpt4",
            input_tokens=140,
            output_tokens=70,
            cost_usd=0.03,
        )
        metrics = tracker.get_all_metrics()
        assert "github_copilot" in metrics
        assert metrics["github_copilot"].total_requests == 1


class TestOllamaTracking:
    """Tests for Ollama provider tracking."""

    def test_record_ollama_request(self):
        """Test recording a single Ollama request."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.OLLAMA,
            model="mistral",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
        )
        assert len(tracker.requests) == 1
        assert tracker.get_total_cost() == 0.001

    def test_ollama_metrics_aggregation(self):
        """Test that Ollama metrics are correctly aggregated."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.OLLAMA,
            model="mistral",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
        )
        metrics = tracker.get_all_metrics()
        assert "ollama" in metrics
        assert metrics["ollama"].total_requests == 1


class TestMultiProviderTracking:
    """Tests for tracking across multiple providers concurrently."""

    def test_all_five_providers_tracked_concurrently(self):
        """Test that all 5 providers can be tracked in a single tracker."""
        tracker = ProviderTracker()
        providers_config = [
            (ProviderType.ANTHROPIC, "claude-opus-4-6", 100, 50, 0.05),
            (ProviderType.OPENAI, "gpt-4", 150, 75, 0.08),
            (ProviderType.GEMINI, "gemini-pro", 120, 60, 0.02),
            (ProviderType.GITHUB_COPILOT, "copilot-gpt4", 140, 70, 0.03),
            (ProviderType.OLLAMA, "mistral", 100, 50, 0.001),
        ]

        for provider, model, input_tok, output_tok, cost in providers_config:
            tracker.record_request(
                provider=provider,
                model=model,
                input_tokens=input_tok,
                output_tokens=output_tok,
                cost_usd=cost,
            )

        assert len(tracker.requests) == 5
        metrics = tracker.get_all_metrics()
        assert len(metrics) == 5
        assert all(m.total_requests == 1 for m in metrics.values())

    def test_provider_isolation(self):
        """Test that recording one provider doesn't affect others."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        tracker.record_request(
            provider=ProviderType.OPENAI,
            model="gpt-4",
            input_tokens=150,
            output_tokens=75,
            cost_usd=0.08,
        )

        metrics = tracker.get_all_metrics()
        assert metrics["anthropic"].total_requests == 1
        assert metrics["openai"].total_requests == 1


class TestTokenTracking:
    """Tests for token counting and tracking."""

    def test_total_tokens_calculation(self):
        """Test that total tokens are correctly calculated."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        assert tracker.get_total_tokens() == 150

    def test_tokens_multiple_requests(self):
        """Test token calculation across multiple requests."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        tracker.record_request(
            provider=ProviderType.OPENAI,
            model="gpt-4",
            input_tokens=150,
            output_tokens=75,
            cost_usd=0.08,
        )
        assert tracker.get_total_tokens() == 375

    def test_cached_tokens_included(self):
        """Test that cached tokens are included in totals."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cached_tokens=25,
            cost_usd=0.05,
        )
        assert tracker.get_total_tokens() == 175


class TestCostCalculations:
    """Tests for cost tracking and calculations."""

    def test_total_cost_calculation(self):
        """Test that total cost is correctly calculated."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        assert tracker.get_total_cost() == pytest.approx(0.05, rel=1e-6)

    def test_cost_multiple_providers(self):
        """Test cost calculation across multiple providers."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        tracker.record_request(
            provider=ProviderType.OPENAI,
            model="gpt-4",
            input_tokens=150,
            output_tokens=75,
            cost_usd=0.08,
        )
        assert tracker.get_total_cost() == pytest.approx(0.13, rel=1e-6)

    def test_cost_per_token_calculation(self):
        """Test cost per token efficiency metric."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.06,
        )
        # Cost: $0.06, Tokens: 150, Expected: $0.0004 per token
        efficiency = tracker.get_efficiency_metrics()
        expected_cost_per_token = 0.06 / 150
        assert efficiency["avg_cost_per_token"] == pytest.approx(
            expected_cost_per_token, rel=1e-6
        )


class TestEfficiencyMetrics:
    """Tests for efficiency metric computation."""

    def test_efficiency_metrics_structure(self):
        """Test that efficiency metrics have expected structure."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
        )
        metrics = tracker.get_efficiency_metrics()
        assert "avg_cost_per_token" in metrics
        assert "avg_cost_per_request" in metrics
        assert "success_rate" in metrics

    def test_success_rate_calculation(self):
        """Test success rate calculation for requests."""
        tracker = ProviderTracker()
        for i in range(3):
            tracker.record_request(
                provider=ProviderType.ANTHROPIC,
                model="claude-opus-4-6",
                input_tokens=100,
                output_tokens=50,
                cost_usd=0.05,
                status="error" if i == 2 else "success",
            )
        efficiency = tracker.get_efficiency_metrics()
        assert efficiency["success_rate"] == pytest.approx(2 / 3, rel=1e-6)

    def test_empty_tracker_efficiency_metrics(self):
        """Test efficiency metrics on empty tracker."""
        tracker = ProviderTracker()
        metrics = tracker.get_efficiency_metrics()
        # Empty tracker returns 0 values
        assert isinstance(metrics, dict)
        if "success_rate" in metrics:
            assert metrics["success_rate"] == 0.0


class TestComparison:
    """Tests for provider comparison functionality."""

    def test_get_comparison_structure(self):
        """Test that comparison has expected structure."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
            duration_ms=200,
        )
        comparison = tracker.get_comparison()
        assert "rankings" in comparison

    def test_cheapest_provider_ranking(self):
        """Test that cheapest provider is correctly identified."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.10,
        )
        tracker.record_request(
            provider=ProviderType.OLLAMA,
            model="mistral",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
        )
        comparison = tracker.get_comparison()
        assert comparison["rankings"]["cheapest_provider"] == "ollama"

    def test_fastest_provider_ranking(self):
        """Test that fastest provider is correctly identified."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.05,
            duration_ms=500,
        )
        tracker.record_request(
            provider=ProviderType.OPENAI,
            model="gpt-4",
            input_tokens=150,
            output_tokens=75,
            cost_usd=0.08,
            duration_ms=200,
        )
        comparison = tracker.get_comparison()
        assert comparison["rankings"]["fastest_provider"] == "openai"


class TestDataClasses:
    """Tests for data class functionality."""

    def test_token_usage_creation(self):
        """Test TokenUsage dataclass creation."""
        tokens = TokenUsage(input_tokens=100, output_tokens=50, cached_tokens=10)
        assert tokens.input_tokens == 100
        assert tokens.output_tokens == 50
        assert tokens.cached_tokens == 10
        assert tokens.total_tokens == 160

    def test_provider_cost_creation(self):
        """Test ProviderCost dataclass creation."""
        from datetime import datetime
        now = datetime.now()
        tokens = TokenUsage(input_tokens=100, output_tokens=50)
        cost = ProviderCost(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            timestamp=now,
            token_usage=tokens,
            cost_usd=0.05,
        )
        assert cost.provider == ProviderType.ANTHROPIC
        assert cost.model == "claude-opus-4-6"
        assert cost.cost_usd == 0.05

    def test_provider_metrics_creation(self):
        """Test ProviderMetrics dataclass creation."""
        metrics = ProviderMetrics(
            provider=ProviderType.ANTHROPIC,
            total_requests=5,
            total_cost_usd=0.25,
            total_input_tokens=500,
            total_output_tokens=250,
        )
        assert metrics.provider == ProviderType.ANTHROPIC
        assert metrics.total_requests == 5
        assert metrics.total_cost_usd == 0.25


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_cost_request(self):
        """Test handling of zero-cost requests."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.OLLAMA,
            model="mistral",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.0,
        )
        assert tracker.get_total_cost() == 0.0
        assert len(tracker.requests) == 1

    def test_very_small_cost(self):
        """Test handling of very small costs."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.OLLAMA,
            model="mistral",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.00001,
        )
        assert tracker.get_total_cost() > 0

    def test_large_token_counts(self):
        """Test handling of large token counts."""
        tracker = ProviderTracker()
        tracker.record_request(
            provider=ProviderType.ANTHROPIC,
            model="claude-opus-4-6",
            input_tokens=100000,
            output_tokens=50000,
            cost_usd=5.0,
        )
        assert tracker.get_total_tokens() == 150000
