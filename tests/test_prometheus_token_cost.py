"""
Tests for PrometheusExporter with token and cost metrics.

Tests cover:
1. Token metrics export (input, output, cached by role/model)
2. Cost metrics export (by role, model, task type, date)
3. Prometheus format validation
4. Label handling
5. Integration with MetricsRegistry
"""

import pytest
from pathlib import Path
from src.orchestration.monitoring.metrics import (
    MetricsRegistry, Counter, Gauge, Histogram,
    create_orchestrator_metrics, create_token_metrics, create_cost_metrics
)
from src.orchestration.monitoring.prometheus_exporter import PrometheusExporter


class TestTokenMetricsExport:
    """Test token metrics export in Prometheus format."""
    
    def test_export_tokens_by_role(self):
        """Test exporting token metrics with role labels."""
        registry = MetricsRegistry()
        
        # Create token metrics
        tokens_input = registry.counter(
            "orchestrator_tokens_input_by_role",
            "Input tokens by role",
            labels={"role": "engineer"}
        )
        tokens_input.inc(1000)
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        assert "orchestrator_tokens_input_by_role" in output
        assert 'role="engineer"' in output
        assert "1000" in output
    
    def test_export_tokens_by_model(self):
        """Test exporting token metrics with model labels."""
        registry = MetricsRegistry()
        
        tokens_output = registry.counter(
            "orchestrator_tokens_output_by_model",
            "Output tokens by model",
            labels={"model": "claude-haiku-4.5"}
        )
        tokens_output.inc(500)
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        assert "orchestrator_tokens_output_by_model" in output
        assert 'model="claude-haiku-4.5"' in output
        assert "500" in output
    
    def test_export_tokens_cached(self):
        """Test exporting cached token metrics."""
        registry = MetricsRegistry()
        
        tokens_cached = registry.counter(
            "orchestrator_tokens_cached_by_role",
            "Cached tokens by role",
            labels={"role": "orchestrator"}
        )
        tokens_cached.inc(250)
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        assert "orchestrator_tokens_cached_by_role" in output
        assert 'role="orchestrator"' in output
    
    def test_export_tokens_per_task_histogram(self):
        """Test exporting tokens per task distribution."""
        registry = MetricsRegistry()
        
        histogram = registry.histogram(
            "orchestrator_tokens_per_task",
            "Tokens per task distribution",
            buckets=[100, 500, 1000, 5000, 10000]
        )
        histogram.observe(250)
        histogram.observe(750)
        histogram.observe(2500)
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        assert "# TYPE orchestrator_tokens_per_task histogram" in output
        assert "orchestrator_tokens_per_task_bucket" in output
        assert "orchestrator_tokens_per_task_sum" in output
        assert "orchestrator_tokens_per_task_count 3" in output


class TestCostMetricsExport:
    """Test cost metrics export in Prometheus format."""
    
    def test_export_cost_by_role(self):
        """Test exporting cost metrics with role labels."""
        registry = MetricsRegistry()
        
        cost_by_role = registry.counter(
            "orchestrator_cost_usd_by_role",
            "Cost by role",
            labels={"role": "engineer"}
        )
        cost_by_role.inc(0.50)
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        assert "orchestrator_cost_usd_by_role" in output
        assert 'role="engineer"' in output
        assert "0.5" in output
    
    def test_export_cost_by_model(self):
        """Test exporting cost metrics with model labels."""
        registry = MetricsRegistry()
        
        cost_by_model = registry.counter(
            "orchestrator_cost_usd_by_model",
            "Cost by model",
            labels={"model": "claude-opus-4.7"}
        )
        cost_by_model.inc(1.25)
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        assert "orchestrator_cost_usd_by_model" in output
        assert 'model="claude-opus-4.7"' in output
    
    def test_export_cost_by_task_type(self):
        """Test exporting cost metrics with task type labels."""
        registry = MetricsRegistry()
        
        cost_by_task = registry.counter(
            "orchestrator_cost_usd_by_task_type",
            "Cost by task type",
            labels={"task_type": "code_review"}
        )
        cost_by_task.inc(0.75)
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        assert "orchestrator_cost_usd_by_task_type" in output
        assert 'task_type="code_review"' in output
    
    def test_export_cost_daily_gauge(self):
        """Test exporting daily cost gauge."""
        registry = MetricsRegistry()
        
        cost_daily = registry.gauge(
            "orchestrator_cost_usd_daily",
            "Daily cost",
            labels={"date": "2026-05-17"}
        )
        cost_daily.set(12.50)
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        assert "# TYPE orchestrator_cost_usd_daily gauge" in output
        assert 'date="2026-05-17"' in output
        assert "12.5" in output
    
    def test_export_cost_per_task_histogram(self):
        """Test exporting cost per task distribution."""
        registry = MetricsRegistry()
        
        histogram = registry.histogram(
            "orchestrator_cost_per_task",
            "Cost per task distribution",
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0]
        )
        histogram.observe(0.02)
        histogram.observe(0.08)
        histogram.observe(0.25)
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        assert "# TYPE orchestrator_cost_per_task histogram" in output
        assert "orchestrator_cost_per_task_bucket" in output
        assert "orchestrator_cost_per_task_sum" in output
        assert "orchestrator_cost_per_task_count 3" in output
    
    def test_export_cost_per_quality_point(self):
        """Test exporting cost per quality point metric."""
        registry = MetricsRegistry()
        
        histogram = registry.histogram(
            "orchestrator_cost_per_quality_point",
            "Cost per quality point",
            buckets=[0.0001, 0.001, 0.01, 0.1]
        )
        histogram.observe(0.0005)
        histogram.observe(0.0015)
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        assert "# TYPE orchestrator_cost_per_quality_point histogram" in output
        assert "orchestrator_cost_per_quality_point_count 2" in output


class TestPrometheusFormatValidation:
    """Test Prometheus format compliance."""
    
    def test_metric_help_text_present(self):
        """Test that HELP lines are present for all metrics."""
        registry = MetricsRegistry()
        registry.counter("test_counter", description="Test counter")
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        assert "# HELP test_counter Test counter" in output
    
    def test_metric_type_present(self):
        """Test that TYPE lines are present for all metrics."""
        registry = MetricsRegistry()
        registry.counter("test_counter", description="Test")
        registry.gauge("test_gauge", description="Test")
        registry.histogram("test_histogram", description="Test")
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        assert "# TYPE test_counter counter" in output
        assert "# TYPE test_gauge gauge" in output
        assert "# TYPE test_histogram histogram" in output
    
    def test_labels_properly_formatted(self):
        """Test that labels are properly formatted in Prometheus syntax."""
        registry = MetricsRegistry()
        registry.counter(
            "test_metric",
            labels={"role": "engineer", "model": "haiku"}
        )
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        # Labels should be in format: {key1="value1",key2="value2"}
        assert 'role="engineer"' in output
        assert 'model="haiku"' in output
        assert "{" in output and "}" in output
    
    def test_no_trailing_whitespace(self):
        """Test that output has no trailing whitespace."""
        registry = MetricsRegistry()
        registry.counter("test_counter").inc(1)
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        lines = output.split("\n")
        for line in lines[:-1]:  # Skip last empty line
            assert not line.endswith(" "), f"Line has trailing whitespace: {line}"
    
    def test_ends_with_newline(self):
        """Test that output ends with newline."""
        registry = MetricsRegistry()
        registry.counter("test_counter").inc(1)
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        assert output.endswith("\n")


class TestIntegrationWithMetricsRegistry:
    """Test integration with MetricsRegistry."""
    
    def test_export_all_orchestrator_metrics(self):
        """Test exporting all standard orchestrator metrics."""
        registry = MetricsRegistry()
        metrics = create_orchestrator_metrics(registry)
        
        # Populate some metrics
        metrics["tasks_total"].inc(5)
        metrics["tokens_total"].inc(1000)
        metrics["cost_usd_total"].inc(0.50)
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        assert "orchestrator_tasks_total" in output
        assert "orchestrator_tokens_total" in output
        assert "orchestrator_cost_usd_total" in output
    
    def test_export_token_metrics_with_labels(self):
        """Test exporting token metrics with proper labels."""
        registry = MetricsRegistry()
        
        # Create metrics with different roles
        for role in ["engineer", "senior_engineer", "orchestrator"]:
            tokens = registry.counter(
                "orchestrator_tokens_input_by_role",
                "Input tokens by role",
                labels={"role": role}
            )
            tokens.inc(100 * len(role))
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        assert 'role="engineer"' in output
        assert 'role="senior_engineer"' in output
        assert 'role="orchestrator"' in output
    
    def test_export_cost_metrics_with_multiple_labels(self):
        """Test exporting cost metrics with multiple label dimensions."""
        registry = MetricsRegistry()
        
        # Cost by role
        registry.counter(
            "orchestrator_cost_usd_by_role",
            labels={"role": "engineer"}
        ).inc(0.50)
        
        # Cost by model
        registry.counter(
            "orchestrator_cost_usd_by_model",
            labels={"model": "haiku"}
        ).inc(0.30)
        
        # Cost by task type
        registry.counter(
            "orchestrator_cost_usd_by_task_type",
            labels={"task_type": "code_review"}
        ).inc(0.75)
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        assert 'role="engineer"' in output
        assert 'model="haiku"' in output
        assert 'task_type="code_review"' in output


class TestExportToFile:
    """Test export to file functionality."""
    
    def test_export_token_cost_metrics_to_file(self, tmp_path):
        """Test exporting token and cost metrics to file."""
        registry = MetricsRegistry()
        
        # Add some metrics
        registry.counter("orchestrator_tokens_input_by_role", 
                        labels={"role": "engineer"}).inc(1000)
        registry.counter("orchestrator_cost_usd_by_role",
                        labels={"role": "engineer"}).inc(0.50)
        
        exporter = PrometheusExporter(registry)
        filepath = str(tmp_path / "metrics.txt")
        exporter.export_to_file(filepath)
        
        assert Path(filepath).exists()
        content = Path(filepath).read_text()
        
        assert "orchestrator_tokens_input_by_role" in content
        assert "orchestrator_cost_usd_by_role" in content
        assert 'role="engineer"' in content


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_registry(self):
        """Test exporting empty registry."""
        registry = MetricsRegistry()
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        # Should still have trailing newline (or be empty with newline)
        assert output.endswith("\n") or output == ""
    
    def test_metric_with_zero_value(self):
        """Test exporting metric with zero value."""
        registry = MetricsRegistry()
        registry.counter("test_counter")  # Default value is 0
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        assert "test_counter 0" in output
    
    def test_metric_with_special_characters_in_labels(self):
        """Test handling labels with special characters."""
        registry = MetricsRegistry()
        registry.counter(
            "test_metric",
            labels={"task_type": "code-review"}
        ).inc(1)
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        assert 'task_type="code-review"' in output
    
    def test_histogram_with_inf_bucket(self):
        """Test histogram with infinity bucket."""
        registry = MetricsRegistry()
        h = registry.histogram("test_histogram", buckets=[1.0, 5.0, 10.0])
        h.observe(15.0)
        
        exporter = PrometheusExporter(registry)
        output = exporter.export()
        
        assert 'le="+Inf"' in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
