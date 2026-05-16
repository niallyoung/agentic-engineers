"""
Tests for TokenTracker — token metrics collection and cost attribution.

Comprehensive test suite covering:
- Token recording and aggregation
- Cost attribution by agent
- Per-agent statistics
- Thread safety
- Integration with MetricsRegistry
"""

import pytest
import threading
import time
from src.orchestration.monitoring.metrics import MetricsRegistry
from src.orchestration.monitoring.token_tracker import (
    TokenTracker, TokenMetrics, TokenStats,
)


# ===========================================================================
# TokenMetrics Tests
# ===========================================================================

class TestTokenMetrics:
    """Test TokenMetrics dataclass."""
    
    def test_create_token_metrics(self):
        """Test creating a TokenMetrics instance."""
        metrics = TokenMetrics(
            task_id="task-001",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=100,
            cost_usd=0.045,
        )
        assert metrics.task_id == "task-001"
        assert metrics.agent == "engineer"
        assert metrics.input_tokens == 1000
        assert metrics.output_tokens == 500
        assert metrics.cached_tokens == 100
        assert metrics.cost_usd == 0.045
    
    def test_total_tokens_property(self):
        """Test total_tokens includes all token types."""
        metrics = TokenMetrics(
            task_id="task-001",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=100,
            cost_usd=0.045,
        )
        assert metrics.total_tokens == 1600
    
    def test_effective_tokens_property(self):
        """Test effective_tokens excludes cached tokens."""
        metrics = TokenMetrics(
            task_id="task-001",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=100,
            cost_usd=0.045,
        )
        assert metrics.effective_tokens == 1500


# ===========================================================================
# TokenStats Tests
# ===========================================================================

class TestTokenStats:
    """Test TokenStats aggregation."""
    
    def test_total_tokens_property(self):
        """Test total_tokens aggregation."""
        stats = TokenStats(
            total_input_tokens=1000,
            total_output_tokens=500,
            total_cached_tokens=100,
        )
        assert stats.total_tokens == 1600
    
    def test_effective_tokens_property(self):
        """Test effective_tokens excludes cached."""
        stats = TokenStats(
            total_input_tokens=1000,
            total_output_tokens=500,
            total_cached_tokens=100,
        )
        assert stats.effective_tokens == 1500
    
    def test_avg_cost_per_task(self):
        """Test average cost calculation."""
        stats = TokenStats(
            total_cost_usd=1.0,
            task_count=10,
        )
        assert stats.avg_cost_per_task == 0.1
    
    def test_avg_cost_per_task_zero_tasks(self):
        """Test average cost with zero tasks."""
        stats = TokenStats(task_count=0)
        assert stats.avg_cost_per_task == 0.0
    
    def test_avg_tokens_per_task(self):
        """Test average tokens calculation."""
        stats = TokenStats(
            total_input_tokens=1000,
            total_output_tokens=500,
            task_count=10,
        )
        assert stats.avg_tokens_per_task == 150.0


# ===========================================================================
# TokenTracker Tests
# ===========================================================================

class TestTokenTracker:
    """Test TokenTracker implementation."""
    
    def test_initialize_tracker(self):
        """Test TokenTracker initialization."""
        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        assert tracker.registry is registry
        assert tracker.tokens_input_total is not None
        assert tracker.tokens_output_total is not None
        assert tracker.tokens_cached_total is not None
        assert tracker.cost_usd_total is not None
    
    def test_record_single_task(self):
        """Test recording a single task."""
        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        
        tracker.record_task_tokens(
            task_id="task-001",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=100,
            cost_usd=0.045,
        )
        
        assert tracker.tokens_input_total.value == 1000
        assert tracker.tokens_output_total.value == 500
        assert tracker.tokens_cached_total.value == 100
        assert tracker.cost_usd_total.value == 0.045
    
    def test_record_multiple_tasks(self):
        """Test recording multiple tasks."""
        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        
        tracker.record_task_tokens(
            task_id="task-001",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=100,
            cost_usd=0.045,
        )
        tracker.record_task_tokens(
            task_id="task-002",
            agent="senior",
            input_tokens=2000,
            output_tokens=1000,
            cached_tokens=200,
            cost_usd=0.090,
        )
        
        assert tracker.tokens_input_total.value == 3000
        assert tracker.tokens_output_total.value == 1500
        assert tracker.tokens_cached_total.value == 300
        assert tracker.cost_usd_total.value == 0.135
    
    def test_record_task_negative_tokens_raises(self):
        """Test that negative token counts raise ValueError."""
        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        
        with pytest.raises(ValueError):
            tracker.record_task_tokens(
                task_id="task-001",
                agent="engineer",
                input_tokens=-1000,
                output_tokens=500,
            )
    
    def test_record_task_negative_cost_raises(self):
        """Test that negative cost raises ValueError."""
        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        
        with pytest.raises(ValueError):
            tracker.record_task_tokens(
                task_id="task-001",
                agent="engineer",
                input_tokens=1000,
                output_tokens=500,
                cost_usd=-0.045,
            )
    
    def test_get_stats_empty(self):
        """Test get_stats with no recorded metrics."""
        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        
        stats = tracker.get_stats()
        assert stats.total_input_tokens == 0
        assert stats.total_output_tokens == 0
        assert stats.total_cached_tokens == 0
        assert stats.total_cost_usd == 0.0
        assert stats.task_count == 0
    
    def test_get_stats_aggregation(self):
        """Test get_stats aggregates correctly."""
        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        
        tracker.record_task_tokens(
            task_id="task-001",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=100,
            cost_usd=0.045,
        )
        tracker.record_task_tokens(
            task_id="task-002",
            agent="engineer",
            input_tokens=2000,
            output_tokens=1000,
            cached_tokens=200,
            cost_usd=0.090,
        )
        
        stats = tracker.get_stats()
        assert stats.total_input_tokens == 3000
        assert stats.total_output_tokens == 1500
        assert stats.total_cached_tokens == 300
        assert stats.total_cost_usd == 0.135
        assert stats.task_count == 2
        assert stats.effective_tokens == 4500
    
    def test_get_agent_stats(self):
        """Test per-agent statistics."""
        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        
        tracker.record_task_tokens(
            task_id="task-001",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=100,
            cost_usd=0.045,
        )
        
        agent_stats = tracker.get_agent_stats("engineer")
        assert agent_stats is not None
        assert agent_stats["agent"] == "engineer"
        assert agent_stats["input_tokens"] == 1000
        assert agent_stats["output_tokens"] == 500
        assert agent_stats["cached_tokens"] == 100
        assert agent_stats["total_tokens"] == 1600
        assert agent_stats["effective_tokens"] == 1500
        assert agent_stats["cost_usd"] == 0.045
        assert agent_stats["task_count"] == 1
    
    def test_get_agent_stats_nonexistent(self):
        """Test get_agent_stats for nonexistent agent."""
        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        
        agent_stats = tracker.get_agent_stats("nonexistent")
        assert agent_stats is None
    
    def test_get_agent_stats_multiple_tasks(self):
        """Test agent stats with multiple tasks."""
        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        
        tracker.record_task_tokens(
            task_id="task-001",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.045,
        )
        tracker.record_task_tokens(
            task_id="task-002",
            agent="engineer",
            input_tokens=2000,
            output_tokens=1000,
            cost_usd=0.090,
        )
        
        agent_stats = tracker.get_agent_stats("engineer")
        assert agent_stats["task_count"] == 2
        assert agent_stats["input_tokens"] == 3000
        assert agent_stats["output_tokens"] == 1500
        assert agent_stats["cost_usd"] == 0.135
        assert agent_stats["avg_tokens_per_task"] == 2250.0
        assert agent_stats["avg_cost_per_task"] == 0.0675
    
    def test_cost_attribution_single_agent(self):
        """Test cost attribution with single agent."""
        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        
        tracker.record_task_tokens(
            task_id="task-001",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.045,
        )
        
        attribution = tracker.get_cost_attribution()
        assert "engineer" in attribution
        assert attribution["engineer"]["tokens"] == 1500
        assert attribution["engineer"]["cost"] == 0.045
        assert attribution["engineer"]["token_percentage"] == 100.0
        assert attribution["engineer"]["cost_percentage"] == 100.0
    
    def test_cost_attribution_multiple_agents(self):
        """Test cost attribution with multiple agents."""
        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        
        tracker.record_task_tokens(
            task_id="task-001",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.045,
        )
        tracker.record_task_tokens(
            task_id="task-002",
            agent="senior",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.045,
        )
        
        attribution = tracker.get_cost_attribution()
        assert len(attribution) == 2
        assert attribution["engineer"]["token_percentage"] == 50.0
        assert attribution["senior"]["token_percentage"] == 50.0
        assert attribution["engineer"]["cost_percentage"] == 50.0
        assert attribution["senior"]["cost_percentage"] == 50.0
    
    def test_cost_attribution_weighted(self):
        """Test cost attribution with different token counts."""
        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        
        # Engineer: 1000 tokens, cost 0.045
        tracker.record_task_tokens(
            task_id="task-001",
            agent="engineer",
            input_tokens=500,
            output_tokens=500,
            cost_usd=0.045,
        )
        # Senior: 2000 tokens, cost 0.090
        tracker.record_task_tokens(
            task_id="task-002",
            agent="senior",
            input_tokens=1000,
            output_tokens=1000,
            cost_usd=0.090,
        )
        
        attribution = tracker.get_cost_attribution()
        # Engineer: 1000 / 3000 = 33.33%
        assert abs(attribution["engineer"]["token_percentage"] - 33.33) < 0.1
        # Senior: 2000 / 3000 = 66.67%
        assert abs(attribution["senior"]["token_percentage"] - 66.67) < 0.1
    
    def test_get_all_metrics(self):
        """Test retrieving all recorded metrics."""
        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        
        tracker.record_task_tokens(
            task_id="task-001",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.045,
        )
        tracker.record_task_tokens(
            task_id="task-002",
            agent="senior",
            input_tokens=2000,
            output_tokens=1000,
            cost_usd=0.090,
        )
        
        all_metrics = tracker.get_all_metrics()
        assert len(all_metrics) == 2
        assert all_metrics[0].task_id == "task-001"
        assert all_metrics[1].task_id == "task-002"
    
    def test_histogram_observations(self):
        """Test that histograms record observations."""
        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        
        tracker.record_task_tokens(
            task_id="task-001",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.045,
        )
        tracker.record_task_tokens(
            task_id="task-002",
            agent="engineer",
            input_tokens=2000,
            output_tokens=1000,
            cost_usd=0.090,
        )
        
        assert tracker.tokens_per_task.count == 2
        assert tracker.cost_per_task.count == 2
    
    def test_clear_metrics(self):
        """Test clearing all metrics."""
        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        
        tracker.record_task_tokens(
            task_id="task-001",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.045,
        )
        
        tracker.clear()
        
        assert tracker.tokens_input_total.value == 0.0
        assert tracker.tokens_output_total.value == 0.0
        assert tracker.tokens_cached_total.value == 0.0
        assert tracker.cost_usd_total.value == 0.0
        assert len(tracker.get_all_metrics()) == 0
    
    def test_thread_safety(self):
        """Test thread-safe concurrent recording."""
        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        
        def record_tasks(agent_name, count):
            for i in range(count):
                tracker.record_task_tokens(
                    task_id=f"{agent_name}-task-{i}",
                    agent=agent_name,
                    input_tokens=1000,
                    output_tokens=500,
                    cost_usd=0.045,
                )
        
        threads = [
            threading.Thread(target=record_tasks, args=("engineer", 10)),
            threading.Thread(target=record_tasks, args=("senior", 10)),
            threading.Thread(target=record_tasks, args=("lead", 10)),
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        stats = tracker.get_stats()
        assert stats.task_count == 30
        assert stats.total_input_tokens == 30000
        assert stats.total_output_tokens == 15000
        assert abs(stats.total_cost_usd - 1.35) < 0.001  # floating-point tolerance


# ===========================================================================
# Integration Tests
# ===========================================================================

class TestTokenTrackerIntegration:
    """Integration tests with MetricsRegistry."""
    
    def test_metrics_registered_with_registry(self):
        """Test that metrics are registered with the registry."""
        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        
        all_metrics = registry.get_all()
        metric_names = [m.name for m in all_metrics.values() if hasattr(m, 'name')]
        
        assert "orchestrator_tokens_input_total" in metric_names
        assert "orchestrator_tokens_output_total" in metric_names
        assert "orchestrator_tokens_cached_total" in metric_names
        assert "orchestrator_cost_usd_total" in metric_names
    
    def test_prometheus_export_includes_token_metrics(self):
        """Test that Prometheus export includes token metrics."""
        from src.orchestration.monitoring.prometheus_exporter import PrometheusExporter
        
        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        
        tracker.record_task_tokens(
            task_id="task-001",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.045,
        )
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        assert "orchestrator_tokens_input_total" in output
        assert "orchestrator_tokens_output_total" in output
        assert "orchestrator_cost_usd_total" in output
        assert "1000.0" in output  # input tokens
        assert "500.0" in output   # output tokens
    
    def test_per_agent_metrics_in_registry(self):
        """Test that per-agent metrics are registered."""
        registry = MetricsRegistry()
        tracker = TokenTracker(registry)
        
        tracker.record_task_tokens(
            task_id="task-001",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.045,
        )
        
        all_metrics = registry.get_all()
        agent_metric_keys = [k for k in all_metrics.keys() if "by_agent" in k]
        
        assert len(agent_metric_keys) > 0
