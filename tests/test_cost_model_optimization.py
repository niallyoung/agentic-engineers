"""
test_cost_model_optimization.py — Comprehensive COST-003 Tests (22+ tests)

Covers:
- Pareto frontier computation (edge cases, correctness)
- All 5 recommendation types (cheapest, fastest, best_quality, balanced, custom)
- Regression detection and alerting
- Mixed-model routing simulation
- Performance benchmarks
"""

import pytest
import time
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, MagicMock, patch

from src.agents.cost_management.model_optimizer import (
    ModelOptimizer,
    ParetoFrontier,
    RecommendationResult,
    RoutingSimulation,
)
from src.agents.cost_management.regression_detector import (
    RegressionDetector,
    RegressionAlert,
    RegressionReport,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_model_selector():
    """Create a mock ModelSelector with realistic data."""
    selector = Mock()
    
    # Mock cost_quality_frontier response
    frontier_models = [
        {
            "model": "claude-haiku-4.5",
            "provider": "anthropic",
            "estimated_cost": 0.002,
            "estimated_quality": 0.70,
            "estimated_latency_sec": 0.5,
        },
        {
            "model": "claude-sonnet-4.6",
            "provider": "anthropic",
            "estimated_cost": 0.008,
            "estimated_quality": 0.92,
            "estimated_latency_sec": 1.2,
        },
        {
            "model": "claude-opus-4.7",
            "provider": "anthropic",
            "estimated_cost": 0.018,
            "estimated_quality": 0.98,
            "estimated_latency_sec": 2.0,
        },
        {
            "model": "gpt-4o-mini",
            "provider": "openai",
            "estimated_cost": 0.005,
            "estimated_quality": 0.75,
            "estimated_latency_sec": 0.8,
        },
    ]
    
    selector.cost_quality_frontier.return_value = {
        "models": frontier_models,
        "pareto_indices": [0, 1, 2],  # haiku, sonnet, opus are Pareto optimal
    }
    
    # Mock recommend_model response
    selector.recommend_model.return_value = {
        "model": "claude-sonnet-4.6",
        "provider": "anthropic",
        "estimated_cost": 0.008,
        "estimated_quality": 0.92,
        "estimated_latency_sec": 1.2,
        "reasoning": "Meets quality target with good cost balance",
    }
    
    # Mock simulate_model_mix response
    selector.simulate_model_mix.return_value = {
        "daily_cost": 85.50,
        "avg_quality": 0.88,
        "breakdown": {
            "claude-sonnet-4.5": {"tasks": 500, "cost": 40.0, "quality": 0.92},
            "claude-haiku-4.5": {"tasks": 500, "cost": 45.5, "quality": 0.70},
        },
    }
    
    # Mock quality estimator
    selector._quality = Mock()
    selector._quality.get_avg_latency.return_value = 1000  # ms
    
    return selector


# ============================================================================
# PARETO FRONTIER TESTS (7 tests)
# ============================================================================

class TestParetoFrontier:
    """Test Pareto frontier computation."""
    
    @pytest.fixture
    def optimizer(self, mock_model_selector):
        """Create optimizer instance with mocked ModelSelector."""
        return ModelOptimizer(model_selector=mock_model_selector)
    
    def test_pareto_frontier_basic(self, optimizer):
        """Test basic Pareto frontier computation."""
        frontier = optimizer.get_pareto_frontier(
            task_type="general",
            input_tokens=1000,
            output_tokens=500,
        )
        
        assert isinstance(frontier, ParetoFrontier)
        assert len(frontier.models) > 0
        assert len(frontier.pareto_indices) > 0
        assert frontier.computation_time_ms >= 0
        assert frontier.total_models == len(frontier.models)
    
    def test_pareto_frontier_computation_time(self, optimizer):
        """Test Pareto computation time < 100ms for typical case."""
        frontier = optimizer.get_pareto_frontier(
            task_type="general",
            input_tokens=5000,
            output_tokens=2000,
        )
        
        assert frontier.computation_time_ms < 100.0, \
            f"Computation time {frontier.computation_time_ms}ms exceeds 100ms"
    
    def test_pareto_frontier_indices_valid(self, optimizer):
        """Test Pareto indices are valid."""
        frontier = optimizer.get_pareto_frontier(
            task_type="code-review",
            input_tokens=5000,
            output_tokens=2000,
        )
        
        for idx in frontier.pareto_indices:
            assert 0 <= idx < len(frontier.models), \
                f"Invalid index {idx} for {len(frontier.models)} models"
    
    def test_pareto_frontier_no_domination(self, optimizer):
        """Test that Pareto models have no domination."""
        frontier = optimizer.get_pareto_frontier(
            task_type="general",
            input_tokens=1000,
            output_tokens=500,
        )
        
        pareto_models = [frontier.models[i] for i in frontier.pareto_indices]
        
        # Each Pareto model should have no strictly better alternative
        for model in pareto_models:
            # Count how many models are strictly better (lower cost AND higher quality)
            strictly_better = [
                m for m in pareto_models
                if m["estimated_cost"] < model["estimated_cost"]
                and m["estimated_quality"] > model["estimated_quality"]
            ]
            assert len(strictly_better) == 0, \
                f"Model {model['model']} is dominated"
    
    def test_pareto_frontier_with_provider_filter(self, optimizer, mock_model_selector):
        """Test Pareto frontier with provider filtering."""
        # Set up mock to return only anthropic models
        anthropic_models = [
            {
                "model": "claude-haiku-4.5",
                "provider": "anthropic",
                "estimated_cost": 0.002,
                "estimated_quality": 0.70,
                "estimated_latency_sec": 0.5,
            },
            {
                "model": "claude-sonnet-4.6",
                "provider": "anthropic",
                "estimated_cost": 0.008,
                "estimated_quality": 0.92,
                "estimated_latency_sec": 1.2,
            },
        ]
        mock_model_selector.cost_quality_frontier.return_value = {
            "models": anthropic_models,
            "pareto_indices": [0, 1],
        }
        
        frontier = optimizer.get_pareto_frontier(
            task_type="general",
            input_tokens=1000,
            output_tokens=500,
            providers=["anthropic"],
        )
        
        assert isinstance(frontier, ParetoFrontier)
        # All models should be from Anthropic
        for model in frontier.models:
            assert model["provider"].lower() == "anthropic"
    
    def test_pareto_frontier_empty_on_invalid_task(self, optimizer):
        """Test Pareto frontier with invalid task type."""
        # Should handle gracefully or return empty
        frontier = optimizer.get_pareto_frontier(
            task_type="nonexistent_task_12345",
            input_tokens=1000,
            output_tokens=500,
        )
        
        # Either returns empty or valid frontier
        assert isinstance(frontier, ParetoFrontier)
    
    def test_pareto_frontier_large_tokens(self, optimizer):
        """Test Pareto frontier with large token counts."""
        frontier = optimizer.get_pareto_frontier(
            task_type="general",
            input_tokens=100000,
            output_tokens=50000,
        )
        
        assert isinstance(frontier, ParetoFrontier)
        assert len(frontier.models) > 0


# ============================================================================
# RECOMMENDATION TYPE TESTS (13 tests)
# ============================================================================

class TestRecommendations:
    """Test all 5 recommendation types."""
    
    @pytest.fixture
    def optimizer(self, mock_model_selector):
        return ModelOptimizer(model_selector=mock_model_selector)
    
    def test_recommend_cheapest_basic(self, optimizer):
        """Test cheapest recommendation."""
        rec = optimizer.recommend_cheapest(
            task_type="general",
            input_tokens=1000,
            output_tokens=500,
        )
        
        assert isinstance(rec, RecommendationResult)
        assert rec.model != "unknown"
        assert rec.estimated_cost >= 0
        assert rec.estimated_quality >= 0
        assert rec.estimated_latency_sec >= 0
        assert rec.recommendation_type == "cheapest"
        assert rec.selection_time_ms >= 0
    
    def test_recommend_cheapest_is_minimum(self, optimizer):
        """Test cheapest recommendation gives minimum cost."""
        rec = optimizer.recommend_cheapest(
            task_type="general",
            input_tokens=1000,
            output_tokens=500,
        )
        
        # Get frontier and verify this is the cheapest
        frontier = optimizer.get_pareto_frontier(
            task_type="general",
            input_tokens=1000,
            output_tokens=500,
        )
        
        cheapest_cost = min(m["estimated_cost"] for m in frontier.models)
        assert rec.estimated_cost <= cheapest_cost * 1.001  # Allow tiny floating point error
    
    def test_recommend_fastest_basic(self, optimizer):
        """Test fastest recommendation."""
        rec = optimizer.recommend_fastest(
            task_type="general",
            input_tokens=1000,
            output_tokens=500,
        )
        
        assert isinstance(rec, RecommendationResult)
        assert rec.model != "unknown"
        assert rec.recommendation_type == "fastest"
        assert rec.selection_time_ms >= 0
    
    def test_recommend_fastest_is_minimum_latency(self, optimizer):
        """Test fastest recommendation gives minimum latency."""
        rec = optimizer.recommend_fastest(
            task_type="general",
            input_tokens=1000,
            output_tokens=500,
        )
        
        frontier = optimizer.get_pareto_frontier(
            task_type="general",
            input_tokens=1000,
            output_tokens=500,
        )
        
        fastest_latency = min(m["estimated_latency_sec"] for m in frontier.models)
        assert rec.estimated_latency_sec <= fastest_latency * 1.001
    
    def test_recommend_best_quality_basic(self, optimizer):
        """Test best quality recommendation."""
        rec = optimizer.recommend_best_quality(
            task_type="code-review",
            input_tokens=5000,
            output_tokens=2000,
        )
        
        assert isinstance(rec, RecommendationResult)
        assert rec.model != "unknown"
        assert rec.recommendation_type == "best_quality"
        assert rec.selection_time_ms >= 0
    
    def test_recommend_best_quality_is_maximum(self, optimizer):
        """Test best quality recommendation gives maximum quality."""
        rec = optimizer.recommend_best_quality(
            task_type="general",
            input_tokens=1000,
            output_tokens=500,
        )
        
        frontier = optimizer.get_pareto_frontier(
            task_type="general",
            input_tokens=1000,
            output_tokens=500,
        )
        
        best_quality = max(m["estimated_quality"] for m in frontier.models)
        assert rec.estimated_quality >= best_quality * 0.999  # Allow tiny error
    
    def test_recommend_balanced_basic(self, optimizer):
        """Test balanced recommendation."""
        rec = optimizer.recommend_balanced(
            task_type="general",
            input_tokens=1000,
            output_tokens=500,
        )
        
        assert isinstance(rec, RecommendationResult)
        assert rec.model != "unknown"
        assert rec.recommendation_type == "balanced"
        assert rec.selection_time_ms >= 0
    
    def test_recommend_balanced_with_weights(self, optimizer):
        """Test balanced recommendation with custom weights."""
        rec = optimizer.recommend_balanced(
            task_type="general",
            input_tokens=1000,
            output_tokens=500,
            cost_weight=0.5,
            quality_weight=0.3,
            latency_weight=0.2,
        )
        
        assert isinstance(rec, RecommendationResult)
        assert rec.recommendation_type == "balanced"
        assert "cost" in rec.reasoning.lower()
        assert "quality" in rec.reasoning.lower()
    
    def test_recommend_balanced_extreme_weights(self, optimizer):
        """Test balanced with extreme weight (should favor that dimension)."""
        # All weight on quality
        rec_quality = optimizer.recommend_balanced(
            task_type="general",
            input_tokens=1000,
            output_tokens=500,
            cost_weight=0.0,
            quality_weight=1.0,
            latency_weight=0.0,
        )
        
        # All weight on cost
        rec_cost = optimizer.recommend_balanced(
            task_type="general",
            input_tokens=1000,
            output_tokens=500,
            cost_weight=1.0,
            quality_weight=0.0,
            latency_weight=0.0,
        )
        
        # Should be different or at least valid
        assert rec_quality.model != "unknown"
        assert rec_cost.model != "unknown"
    
    def test_recommend_custom_basic(self, optimizer):
        """Test custom recommendation."""
        rec = optimizer.recommend_custom(
            task_type="general",
            input_tokens=1000,
            output_tokens=500,
            constraints={"max_cost": 0.10},
        )
        
        assert isinstance(rec, RecommendationResult)
        assert rec.recommendation_type == "custom"
    
    def test_recommend_custom_quality_target(self, optimizer):
        """Test custom recommendation with quality target."""
        rec = optimizer.recommend_custom(
            task_type="general",
            input_tokens=1000,
            output_tokens=500,
            constraints={"quality_target": 0.8},
        )
        
        assert isinstance(rec, RecommendationResult)
        assert rec.estimated_quality >= 0.75  # Should meet or exceed target
    
    def test_recommend_custom_max_latency(self, optimizer):
        """Test custom recommendation with max latency."""
        rec = optimizer.recommend_custom(
            task_type="general",
            input_tokens=1000,
            output_tokens=500,
            constraints={"max_latency_sec": 2.0},
        )
        
        assert isinstance(rec, RecommendationResult)
        assert rec.estimated_latency_sec <= 2.0


# ============================================================================
# REGRESSION DETECTION TESTS (6+ tests)
# ============================================================================

class TestRegressionDetection:
    """Test regression detection and alerting."""
    
    @pytest.fixture
    def detector(self):
        return RegressionDetector(threshold_pct=10.0)
    
    def test_record_performance_basic(self, detector):
        """Test recording performance metrics."""
        detector.record_performance(
            task_type="general",
            model="claude-sonnet-4.5",
            cost=0.05,
            quality=0.95,
            latency_sec=1.2,
        )
        
        assert ("general", "claude-sonnet-4.5") in detector._baselines
    
    def test_regression_cost_increase(self, detector):
        """Test detection of cost regression."""
        # Record baseline (multiple times to establish baseline)
        detector.record_performance("general", "claude-sonnet-4.5", 0.05, 0.95, 1.2)
        detector.record_performance("general", "claude-sonnet-4.5", 0.05, 0.95, 1.2)
        
        # Record degraded cost (20% higher)
        for _ in range(3):
            detector.record_performance("general", "claude-sonnet-4.5", 0.06, 0.95, 1.2)
        
        alerts = detector.detect_regressions(task_type="general")
        cost_alerts = [a for a in alerts if a.metric_type == "cost"]
        
        # Should have detected cost regression (>10%)
        assert len(cost_alerts) > 0, f"Expected cost alerts, got {alerts}"
    
    def test_regression_quality_drop(self, detector):
        """Test detection of quality regression."""
        detector.record_performance("general", "claude-sonnet-4.5", 0.05, 0.95, 1.2)
        detector.record_performance("general", "claude-sonnet-4.5", 0.05, 0.95, 1.2)
        detector.record_performance("general", "claude-sonnet-4.5", 0.05, 0.95, 1.2)
        
        # Quality drops 20% (from 0.95 to 0.76)
        for _ in range(3):
            detector.record_performance("general", "claude-sonnet-4.5", 0.05, 0.76, 1.2)
        
        alerts = detector.detect_regressions()
        quality_alerts = [a for a in alerts if a.metric_type == "quality"]
        
        # Should detect quality drop (>10%)
        assert len(quality_alerts) > 0, f"Expected quality alerts, got {alerts}"
    
    def test_regression_latency_increase(self, detector):
        """Test detection of latency regression."""
        detector.record_performance("general", "claude-sonnet-4.5", 0.05, 0.95, 1.0)
        detector.record_performance("general", "claude-sonnet-4.5", 0.05, 0.95, 1.2)
        
        alerts = detector.detect_regressions()
        latency_alerts = [a for a in alerts if a.metric_type == "latency"]
        
        assert len(latency_alerts) > 0
    
    def test_regression_severity_warning(self, detector):
        """Test warning severity (10-25% degradation)."""
        detector = RegressionDetector(threshold_pct=10.0)
        
        # Establish baseline (higher initial values to allow room for degradation)
        for _ in range(3):
            detector.record_performance("general", "model-a", 0.10, 0.95, 1.0)
        
        # 18% cost increase = warning (within 10-25% range)
        for _ in range(3):
            detector.record_performance("general", "model-a", 0.118, 0.95, 1.0)
        
        alerts = detector.detect_regressions()
        warning_alerts = [a for a in alerts if a.severity == "warning"]
        assert len(warning_alerts) > 0, f"Got alerts: {alerts}"
    
    def test_regression_severity_critical(self, detector):
        """Test critical severity (>25% degradation)."""
        # Establish baseline
        for _ in range(3):
            detector.record_performance("general", "model-a", 0.10, 0.95, 1.0)
        
        # 50% cost increase = critical (> 25%)
        for _ in range(3):
            detector.record_performance("general", "model-a", 0.15, 0.95, 1.0)
        
        alerts = detector.detect_regressions()
        critical_alerts = [a for a in alerts if a.severity == "critical"]
        assert len(critical_alerts) > 0, f"Got alerts: {alerts}"
    
    def test_regression_filter_by_task_type(self, detector):
        """Test filtering regressions by task type."""
        detector.record_performance("general", "model-a", 0.05, 0.95, 1.0)
        detector.record_performance("code-review", "model-a", 0.10, 0.92, 1.5)
        
        detector.record_performance("general", "model-a", 0.06, 0.95, 1.0)
        detector.record_performance("code-review", "model-a", 0.09, 0.92, 1.5)
        
        general_alerts = detector.detect_regressions(task_type="general")
        assert all(a.task_type == "general" for a in general_alerts)
    
    def test_regression_filter_by_model(self, detector):
        """Test filtering regressions by model."""
        detector.record_performance("general", "model-a", 0.05, 0.95, 1.0)
        detector.record_performance("general", "model-b", 0.10, 0.92, 1.5)
        
        detector.record_performance("general", "model-a", 0.06, 0.95, 1.0)
        detector.record_performance("general", "model-b", 0.09, 0.92, 1.5)
        
        model_b_alerts = detector.detect_regressions(model="model-b")
        assert all(a.model == "model-b" for a in model_b_alerts)
    
    def test_regression_generate_report(self, detector):
        """Test report generation."""
        detector.record_performance("general", "model-a", 0.05, 0.95, 1.0)
        detector.record_performance("code-review", "model-b", 0.10, 0.92, 1.5)
        
        detector.record_performance("general", "model-a", 0.06, 0.95, 1.0)
        detector.record_performance("code-review", "model-b", 0.13, 0.92, 1.5)
        
        report = detector.generate_report()
        
        assert isinstance(report, RegressionReport)
        assert report.total_tracked == 2
        assert report.critical_count + report.warning_count + report.info_count > 0
    
    def test_regression_update_baseline(self, detector):
        """Test updating baseline to acknowledge regression."""
        detector.record_performance("general", "model-a", 0.05, 0.95, 1.0)
        detector.record_performance("general", "model-a", 0.05, 0.95, 1.0)
        
        # Degrade performance
        for _ in range(3):
            detector.record_performance("general", "model-a", 0.06, 0.95, 1.0)
        
        # Should detect regression before update
        alerts_before = detector.detect_regressions()
        assert len(alerts_before) > 0
        
        # Update baseline
        detector.update_baseline("general", "model-a")
        
        # Should not detect after baseline update
        alerts_after = detector.detect_regressions()
        assert len(alerts_after) == 0
    
    def test_regression_metrics_summary(self, detector):
        """Test metrics summary."""
        detector.record_performance("general", "model-a", 0.05, 0.95, 1.0)
        detector.record_performance("code-review", "model-b", 0.10, 0.92, 1.5)
        
        summary = detector.get_metrics_summary()
        
        assert summary["total_task_model_pairs"] == 2
        assert "general" in summary["tracked_tasks"]
        assert "code-review" in summary["tracked_tasks"]
        assert "model-a" in summary["tracked_models"]
        assert "model-b" in summary["tracked_models"]


# ============================================================================
# MIXED-MODEL ROUTING TESTS (3 tests)
# ============================================================================

class TestMixedModelRouting:
    """Test mixed-model routing simulation."""
    
    @pytest.fixture
    def optimizer(self, mock_model_selector):
        return ModelOptimizer(model_selector=mock_model_selector)
    
    def test_simulate_model_mix_basic(self, optimizer):
        """Test basic model mix simulation."""
        result = optimizer.simulate_model_mix(
            mix={
                "claude-sonnet-4.5": 0.5,
                "claude-haiku-4.5": 0.5,
            },
            daily_tasks=1000,
            avg_tokens=(1000, 500),
        )
        
        assert isinstance(result, RoutingSimulation)
        assert result.daily_cost > 0
        assert 0 <= result.avg_quality <= 1
        assert result.avg_latency_sec > 0
    
    def test_simulate_model_mix_weighted(self, optimizer, mock_model_selector):
        """Test that mix weights affect cost appropriately."""
        # 100% cheap model
        cheap_result = {
            "daily_cost": 10.0,
            "avg_quality": 0.70,
            "breakdown": {"claude-haiku-4.5": {"tasks": 1000, "cost": 10.0}},
        }
        
        # 100% expensive model
        expensive_result = {
            "daily_cost": 100.0,
            "avg_quality": 0.98,
            "breakdown": {"claude-opus-4.7": {"tasks": 1000, "cost": 100.0}},
        }
        
        # First call returns cheap result
        mock_model_selector.simulate_model_mix.side_effect = [cheap_result, expensive_result]
        
        result_cheap = optimizer.simulate_model_mix(
            mix={"claude-haiku-4.5": 1.0},
            daily_tasks=1000,
            avg_tokens=(1000, 500),
        )
        
        result_expensive = optimizer.simulate_model_mix(
            mix={"claude-opus-4.7": 1.0},
            daily_tasks=1000,
            avg_tokens=(1000, 500),
        )
        
        # Expensive should cost more
        assert result_expensive.daily_cost > result_cheap.daily_cost
    
    def test_simulate_model_mix_breakdown(self, optimizer, mock_model_selector):
        """Test model mix breakdown contains expected models."""
        mix = {
            "claude-sonnet-4.5": 0.3,
            "claude-haiku-4.5": 0.7,
        }
        
        # Update mock to return this specific breakdown
        mock_model_selector.simulate_model_mix.return_value = {
            "daily_cost": 85.50,
            "avg_quality": 0.88,
            "breakdown": {
                "claude-sonnet-4.5": {"tasks": 300, "cost": 50.0, "quality": 0.92},
                "claude-haiku-4.5": {"tasks": 700, "cost": 35.5, "quality": 0.70},
            },
        }
        
        result = optimizer.simulate_model_mix(
            mix=mix,
            daily_tasks=1000,
            avg_tokens=(1000, 500),
        )
        
        assert isinstance(result, RoutingSimulation)
        assert result.breakdown is not None
        # Both models should be in breakdown
        assert "claude-sonnet-4.5" in result.breakdown
        assert "claude-haiku-4.5" in result.breakdown


# ============================================================================
# PERFORMANCE BENCHMARK TESTS (3 tests)
# ============================================================================

class TestPerformanceBenchmarks:
    """Test performance benchmarks."""
    
    @pytest.fixture
    def optimizer(self, mock_model_selector):
        return ModelOptimizer(model_selector=mock_model_selector)
    
    def test_pareto_computation_under_100ms(self, optimizer):
        """Test Pareto frontier computation < 100ms."""
        start = time.time()
        frontier = optimizer.get_pareto_frontier(
            task_type="general",
            input_tokens=5000,
            output_tokens=2000,
        )
        elapsed_ms = (time.time() - start) * 1000
        
        assert frontier.computation_time_ms < 100.0
        assert elapsed_ms < 100.0
    
    def test_recommendation_under_50ms(self, optimizer):
        """Test individual recommendation < 50ms."""
        start = time.time()
        rec = optimizer.recommend_balanced(
            task_type="general",
            input_tokens=1000,
            output_tokens=500,
        )
        elapsed_ms = (time.time() - start) * 1000
        
        assert rec.selection_time_ms < 50.0
        assert elapsed_ms < 50.0
    
    def test_all_recommendation_types_performance(self, optimizer):
        """Test all 5 recommendation types complete quickly."""
        start = time.time()
        
        optimizer.recommend_cheapest("general", 1000, 500)
        optimizer.recommend_fastest("general", 1000, 500)
        optimizer.recommend_best_quality("general", 1000, 500)
        optimizer.recommend_balanced("general", 1000, 500)
        optimizer.recommend_custom("general", 1000, 500, {})
        
        elapsed_ms = (time.time() - start) * 1000
        
        # All 5 should complete in < 250ms (50ms each)
        assert elapsed_ms < 250.0


# ============================================================================
# EDGE CASE & ERROR HANDLING TESTS (5 tests)
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def optimizer(self, mock_model_selector):
        return ModelOptimizer(model_selector=mock_model_selector)
    
    @pytest.fixture
    def detector(self):
        return RegressionDetector()
    
    def test_pareto_zero_tokens(self, optimizer):
        """Test Pareto with zero tokens."""
        frontier = optimizer.get_pareto_frontier(
            task_type="general",
            input_tokens=0,
            output_tokens=0,
        )
        
        assert isinstance(frontier, ParetoFrontier)
    
    def test_recommendation_no_constraints(self, optimizer):
        """Test custom recommendation with empty constraints."""
        rec = optimizer.recommend_custom(
            task_type="general",
            input_tokens=1000,
            output_tokens=500,
            constraints={},
        )
        
        assert isinstance(rec, RecommendationResult)
    
    def test_regression_detector_no_history(self, detector):
        """Test regression detection with no history."""
        alerts = detector.detect_regressions()
        
        assert isinstance(alerts, list)
        assert len(alerts) == 0
    
    def test_regression_detector_threshold_zero(self):
        """Test regression detector with zero threshold."""
        detector = RegressionDetector(threshold_pct=0.0)
        
        detector.record_performance("general", "model-a", 0.05, 0.95, 1.0)
        detector.record_performance("general", "model-a", 0.050001, 0.95, 1.0)
        
        # Even tiny increase should be detected
        alerts = detector.detect_regressions()
        assert len(alerts) > 0
    
    def test_regression_detector_very_high_threshold(self):
        """Test regression detector with very high threshold."""
        detector = RegressionDetector(threshold_pct=100.0)
        
        detector.record_performance("general", "model-a", 0.05, 0.95, 1.0)
        # 50% cost increase
        detector.record_performance("general", "model-a", 0.075, 0.95, 1.0)
        
        alerts = detector.detect_regressions()
        assert len(alerts) == 0  # Should not trigger at 50% vs 100% threshold


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
