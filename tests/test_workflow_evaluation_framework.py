"""
Unit Tests for Workflow Evaluation Framework

Tests cover:
- Workflow pattern definitions
- Metrics collection
- Anomaly detection
- Matrix reporting
- CLI functionality

Target: ≥14 tests with ≥90% coverage
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
import time

from src.skills._meta.evaluation_framework.workflow_patterns import (
    WorkflowPattern,
    WorkflowDefinition,
    WORKFLOW_PATTERNS,
    WORKFLOW_SIMPLE,
    WORKFLOW_ESCALATION,
    WORKFLOW_PARALLEL,
    WORKFLOW_CHAINED,
    WORKFLOW_ERROR_RECOVERY,
    HARNESSES,
    MODELS,
    get_workflow_definition,
    get_all_workflow_definitions,
)
from src.skills._meta.evaluation_framework.workflow_matrix_tester import (
    WorkflowMetrics,
    WorkflowMetricsCollector,
    AnomalyType,
    AnomalyResult,
)
from src.skills._meta.evaluation_framework.anomaly_report import (
    AnomalyReportGenerator,
    AnomalyGroup,
)


# ============================================================================
# WORKFLOW PATTERN TESTS
# ============================================================================

class TestWorkflowPatterns:
    """Test workflow pattern definitions."""
    
    def test_workflow_simple_definition(self):
        """Test SIMPLE workflow pattern is properly defined."""
        assert WORKFLOW_SIMPLE.pattern == WorkflowPattern.SIMPLE
        assert "simple" in WORKFLOW_SIMPLE.name.lower()
        assert len(WORKFLOW_SIMPLE.objectives) > 0
        assert len(WORKFLOW_SIMPLE.success_criteria) > 0
        assert WORKFLOW_SIMPLE.expected_success_rate == 95.0
    
    def test_workflow_escalation_definition(self):
        """Test ESCALATION workflow pattern is properly defined."""
        assert WORKFLOW_ESCALATION.pattern == WorkflowPattern.ESCALATION
        assert "escalation" in WORKFLOW_ESCALATION.name.lower()
        assert len(WORKFLOW_ESCALATION.success_criteria) > 0
        assert WORKFLOW_ESCALATION.expected_success_rate == 90.0
    
    def test_workflow_parallel_definition(self):
        """Test PARALLEL workflow pattern is properly defined."""
        assert WORKFLOW_PARALLEL.pattern == WorkflowPattern.PARALLEL
        assert len(WORKFLOW_PARALLEL.failure_scenarios) > 0
    
    def test_workflow_chained_definition(self):
        """Test CHAINED workflow pattern is properly defined."""
        assert WORKFLOW_CHAINED.pattern == WorkflowPattern.CHAINED
        assert WORKFLOW_CHAINED.expected_success_rate == 92.0
    
    def test_workflow_error_recovery_definition(self):
        """Test ERROR_RECOVERY workflow pattern is properly defined."""
        assert WORKFLOW_ERROR_RECOVERY.pattern == WorkflowPattern.ERROR_RECOVERY
        assert WORKFLOW_ERROR_RECOVERY.expected_success_rate == 85.0
    
    def test_get_workflow_definition_by_enum(self):
        """Test retrieving workflow definition by enum."""
        workflow = get_workflow_definition(WorkflowPattern.SIMPLE)
        assert workflow is not None
        assert workflow.pattern == WorkflowPattern.SIMPLE
    
    def test_get_workflow_definition_by_string(self):
        """Test retrieving workflow definition by string."""
        workflow = get_workflow_definition("simple")
        assert workflow is not None
        assert workflow.pattern == WorkflowPattern.SIMPLE
    
    def test_get_all_workflow_definitions(self):
        """Test retrieving all workflow definitions."""
        workflows = get_all_workflow_definitions()
        assert len(workflows) == 5
        assert "simple" in workflows
        assert "escalation" in workflows
        assert "parallel" in workflows
        assert "chained" in workflows
        assert "error_recovery" in workflows
    
    def test_workflow_metrics_keys_initialized(self):
        """Test that workflow definitions have metric keys."""
        for workflow_def in WORKFLOW_PATTERNS.values():
            assert len(workflow_def.metric_keys) > 0
            assert "total_latency_ms" in workflow_def.metric_keys


# ============================================================================
# METRICS COLLECTION TESTS
# ============================================================================

class TestMetricsCollection:
    """Test metrics collection and aggregation."""
    
    def test_workflow_metrics_creation(self):
        """Test creating a workflow metrics instance."""
        metric = WorkflowMetrics(
            workflow="simple",
            harness="opencode",
            model="haiku",
            status="PASS",
            total_latency_ms=2345,
            per_task_cost_usd=0.0456,
            success_rate=95.5,
        )
        assert metric.workflow == "simple"
        assert metric.harness == "opencode"
        assert metric.model == "haiku"
        assert metric.total_latency_ms == 2345
        assert metric.per_task_cost_usd == 0.0456
        assert metric.status == "PASS"
    
    def test_workflow_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metric = WorkflowMetrics(
            workflow="simple",
            harness="opencode",
            model="haiku",
            status="PASS",
            total_latency_ms=2345,
            per_task_cost_usd=0.0456,
            success_rate=95.5,
        )
        data = metric.to_dict()
        assert data["workflow"] == "simple"
        assert data["total_latency_ms"] == 2345
        assert data["per_task_cost_usd"] == 0.0456
    
    def test_metrics_collector_creation(self):
        """Test creating a metrics collector."""
        collector = WorkflowMetricsCollector()
        assert len(collector.metrics) == 0
        assert len(collector.anomalies) == 0
    
    def test_metrics_collector_add_metric(self):
        """Test adding metrics to collector."""
        collector = WorkflowMetricsCollector()
        metric = WorkflowMetrics(
            workflow="simple",
            harness="opencode",
            model="haiku",
            status="PASS",
            total_latency_ms=2345,
            per_task_cost_usd=0.0456,
            success_rate=95.5,
        )
        collector.add_metric(metric)
        assert len(collector.metrics) == 1
        assert collector.metrics[0] == metric
    
    def test_metrics_collector_calculate_baselines(self):
        """Test calculating baseline metrics."""
        collector = WorkflowMetricsCollector()
        
        # Add multiple metrics for simple workflow
        for i in range(5):
            metric = WorkflowMetrics(
                workflow="simple",
                harness="opencode",
                model="haiku",
                status="PASS",
                total_latency_ms=2000 + (i * 100),
                per_task_cost_usd=0.04 + (i * 0.001),
                success_rate=95.0 + (i * 0.5),
            )
            collector.add_metric(metric)
        
        collector.calculate_baselines()
        
        assert "simple" in collector.baselines
        baseline = collector.baselines["simple"]
        assert "median_latency_ms" in baseline
        assert "median_cost_usd" in baseline
        assert baseline["median_latency_ms"] > 0
        assert baseline["median_cost_usd"] > 0


# ============================================================================
# ANOMALY DETECTION TESTS
# ============================================================================

class TestAnomalyDetection:
    """Test anomaly detection logic."""
    
    def test_anomaly_result_creation(self):
        """Test creating an anomaly result."""
        anomaly = AnomalyResult(
            workflow="simple",
            harness="opencode",
            model="haiku",
            anomaly_type=AnomalyType.HIGH_LATENCY,
            reasons=["Latency spike detected"],
        )
        assert anomaly.has_anomaly()
        assert anomaly.anomaly_type == AnomalyType.HIGH_LATENCY
    
    def test_no_anomaly_result(self):
        """Test anomaly result with no anomaly."""
        anomaly = AnomalyResult(
            workflow="simple",
            harness="opencode",
            model="haiku",
            anomaly_type=AnomalyType.NONE,
        )
        assert not anomaly.has_anomaly()
    
    def test_detect_high_latency_anomaly(self):
        """Test detecting high latency anomaly."""
        collector = WorkflowMetricsCollector()
        
        # Add baseline metrics (normal latency)
        for i in range(3):
            metric = WorkflowMetrics(
                workflow="simple",
                harness="opencode",
                model="haiku",
                status="PASS",
                total_latency_ms=2000,
                per_task_cost_usd=0.04,
                success_rate=95.0,
            )
            collector.add_metric(metric)
        
        # Add anomalous metric (very high latency)
        anomaly_metric = WorkflowMetrics(
            workflow="simple",
            harness="opencode",
            model="sonnet",
            status="PASS",
            total_latency_ms=10000,  # 5x higher
            per_task_cost_usd=0.04,
            success_rate=95.0,
        )
        collector.add_metric(anomaly_metric)
        
        collector.calculate_baselines()
        collector.detect_anomalies()
        
        # Should detect anomaly
        assert len(collector.anomalies) > 0
        found = any(
            a.harness == "opencode" and a.anomaly_type == AnomalyType.HIGH_LATENCY
            for a in collector.anomalies
        )
        assert found
    
    def test_detect_low_success_rate_anomaly(self):
        """Test detecting low success rate anomaly."""
        collector = WorkflowMetricsCollector()
        
        # Add baseline metrics (normal success)
        for i in range(3):
            metric = WorkflowMetrics(
                workflow="simple",
                harness="opencode",
                model="haiku",
                status="PASS",
                total_latency_ms=2000,
                per_task_cost_usd=0.04,
                success_rate=95.0,
            )
            collector.add_metric(metric)
        
        # Add anomalous metric (low success rate)
        anomaly_metric = WorkflowMetrics(
            workflow="simple",
            harness="copilot",
            model="haiku",
            status="PASS",
            total_latency_ms=2000,
            per_task_cost_usd=0.04,
            success_rate=85.0,  # Below 95% threshold
        )
        collector.add_metric(anomaly_metric)
        
        collector.calculate_baselines()
        collector.detect_anomalies()
        
        # Should detect anomaly
        found = any(
            a.anomaly_type == AnomalyType.LOW_SUCCESS
            for a in collector.anomalies
        )
        assert found


# ============================================================================
# METRICS SUMMARY & EXPORT TESTS
# ============================================================================

class TestMetricsExport:
    """Test metrics export and reporting."""
    
    def test_metrics_collector_get_summary(self):
        """Test getting metrics summary."""
        collector = WorkflowMetricsCollector()
        
        # Add metrics
        for i in range(10):
            metric = WorkflowMetrics(
                workflow="simple",
                harness="opencode",
                model="haiku",
                status="PASS" if i < 9 else "FAIL",
                total_latency_ms=2000 + i * 100,
                per_task_cost_usd=0.04 + i * 0.001,
                success_rate=95.0,
            )
            collector.add_metric(metric)
        
        summary = collector.get_summary()
        
        assert summary["total_tests"] == 10
        assert summary["passed"] == 9
        assert summary["failed"] == 1
        assert summary["pass_rate"] == 90.0
    
    def test_export_json(self):
        """Test exporting metrics to JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = WorkflowMetricsCollector()
            
            metric = WorkflowMetrics(
                workflow="simple",
                harness="opencode",
                model="haiku",
                status="PASS",
                total_latency_ms=2345,
                per_task_cost_usd=0.0456,
                success_rate=95.5,
            )
            collector.add_metric(metric)
            collector.calculate_baselines()
            
            json_path = Path(tmpdir) / "metrics.json"
            collector.export_json(json_path)
            
            assert json_path.exists()
            with open(json_path) as f:
                data = json.load(f)
            
            assert "summary" in data
            assert "metrics" in data
            assert len(data["metrics"]) == 1
    
    def test_export_csv(self):
        """Test exporting metrics to CSV."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = WorkflowMetricsCollector()
            
            metric = WorkflowMetrics(
                workflow="simple",
                harness="opencode",
                model="haiku",
                status="PASS",
                total_latency_ms=2345,
                per_task_cost_usd=0.0456,
                success_rate=95.5,
            )
            collector.add_metric(metric)
            
            csv_path = Path(tmpdir) / "metrics.csv"
            collector.export_csv(csv_path)
            
            assert csv_path.exists()
            with open(csv_path) as f:
                lines = f.readlines()
            
            assert len(lines) >= 2  # Header + at least 1 row
    
    def test_export_markdown_matrix(self):
        """Test exporting markdown matrix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            collector = WorkflowMetricsCollector()
            
            # Add metrics for each workflow
            for workflow in ["simple", "escalation"]:
                for harness in HARNESSES:
                    for model in MODELS:
                        metric = WorkflowMetrics(
                            workflow=workflow,
                            harness=harness,
                            model=model,
                            status="PASS",
                            total_latency_ms=2345,
                            per_task_cost_usd=0.0456,
                            success_rate=95.5,
                        )
                        collector.add_metric(metric)
            
            md_path = Path(tmpdir) / "matrix.md"
            collector.export_markdown_matrix(md_path)
            
            assert md_path.exists()
            with open(md_path) as f:
                content = f.read()
            
            assert "simple" in content.lower()
            assert "escalation" in content.lower()
            assert "✅" in content or "✔" in content


# ============================================================================
# HARNESS AND MODEL TESTS
# ============================================================================

class TestHarnessesAndModels:
    """Test harness and model definitions."""
    
    def test_harnesses_defined(self):
        """Test that all harnesses are defined."""
        assert len(HARNESSES) == 4
        assert "opencode" in HARNESSES
        assert "copilot" in HARNESSES
        assert "claude-code" in HARNESSES
        assert "pi-dev" in HARNESSES
    
    def test_models_defined(self):
        """Test that all models are defined."""
        assert len(MODELS) == 3
        assert "haiku" in MODELS
        assert "sonnet" in MODELS
        assert "opus" in MODELS
    
    def test_full_matrix_coverage(self):
        """Test that full matrix would cover all combinations."""
        expected_combinations = len(WORKFLOW_PATTERNS) * len(HARNESSES) * len(MODELS)
        assert expected_combinations == 60


# ============================================================================
# ANOMALY REPORT TESTS
# ============================================================================

class TestAnomalyReporting:
    """Test anomaly report generation."""
    
    def test_anomaly_report_generator_creation(self):
        """Test creating an anomaly report generator."""
        metrics = []
        anomalies = []
        generator = AnomalyReportGenerator(metrics, anomalies)
        assert generator is not None
    
    def test_group_anomalies(self):
        """Test grouping anomalies by type."""
        metrics = []
        anomalies = [
            AnomalyResult(
                workflow="simple",
                harness="opencode",
                model="haiku",
                anomaly_type=AnomalyType.HIGH_LATENCY,
                reasons=["Latency spike"],
            ),
            AnomalyResult(
                workflow="escalation",
                harness="copilot",
                model="sonnet",
                anomaly_type=AnomalyType.HIGH_LATENCY,
                reasons=["Latency spike"],
            ),
        ]
        generator = AnomalyReportGenerator(metrics, anomalies)
        groups = generator.group_anomalies()
        
        assert AnomalyType.HIGH_LATENCY in groups
        assert groups[AnomalyType.HIGH_LATENCY].count == 2
    
    def test_detect_regressions_success_rate(self):
        """Test detecting success rate regressions."""
        # Create metrics with one harness having low success rate
        metrics = []
        for i in range(10):
            metric = WorkflowMetrics(
                workflow="simple",
                harness="opencode" if i < 3 else "copilot",
                model="haiku",
                status="FAIL" if (i < 3) else "PASS",  # opencode has 30% success
                total_latency_ms=2000,
                per_task_cost_usd=0.04,
                success_rate=70.0 if i < 3 else 95.0,
            )
            metrics.append(metric)
        
        generator = AnomalyReportGenerator(metrics, [])
        regressions = generator.detect_regressions()
        
        # Should detect regression on opencode harness
        regression_types = [r.get("type") for r in regressions]
        assert "HARNESS_FAILURE_RATE" in regression_types
    
    def test_generate_markdown_report(self):
        """Test generating markdown report."""
        metrics = []
        anomalies = [
            AnomalyResult(
                workflow="simple",
                harness="opencode",
                model="haiku",
                anomaly_type=AnomalyType.LOW_SUCCESS,
                reasons=["Success rate 85% < 95% threshold"],
            ),
        ]
        generator = AnomalyReportGenerator(metrics, anomalies)
        report = generator.generate_markdown_report()
        
        assert "Anomaly Analysis Report" in report
        assert "LOW_SUCCESS" in report
        assert "CRITICAL" in report
    
    def test_generate_summary_table(self):
        """Test generating anomaly summary table."""
        metrics = []
        anomalies = [
            AnomalyResult(
                workflow="simple",
                harness="opencode",
                model="haiku",
                anomaly_type=AnomalyType.HIGH_LATENCY,
                reasons=["Latency 10000ms > 2x median 2000ms"],
            ),
        ]
        generator = AnomalyReportGenerator(metrics, anomalies)
        table = generator.generate_summary_table()
        
        assert "simple" in table
        assert "opencode" in table
        assert "high_latency" in table


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple components."""
    
    def test_full_workflow_evaluation_pipeline(self):
        """Test complete workflow evaluation pipeline."""
        # Create collector
        collector = WorkflowMetricsCollector()
        
        # Add metrics for full matrix (5 workflows × 4 harnesses × 3 models = 60)
        from src.skills._meta.evaluation_framework.workflow_patterns import (
            WorkflowPattern,
        )
        
        count = 0
        for workflow_enum in WorkflowPattern:
            workflow = workflow_enum.value
            for harness in HARNESSES:
                for model in MODELS:
                    metric = WorkflowMetrics(
                        workflow=workflow,
                        harness=harness,
                        model=model,
                        status="PASS",
                        total_latency_ms=2000 + (count % 5) * 500,
                        per_task_cost_usd=0.04 + (count % 5) * 0.01,
                        success_rate=95.0,
                    )
                    collector.add_metric(metric)
                    count += 1
        
        # Calculate baselines
        collector.calculate_baselines()
        assert len(collector.baselines) == 5
        
        # Detect anomalies
        collector.detect_anomalies()
        
        # Get summary
        summary = collector.get_summary()
        assert summary["total_tests"] == 60
        assert summary["passed"] == 60
        assert summary["pass_rate"] == 100.0
    
    def test_end_to_end_with_anomalies(self):
        """Test end-to-end pipeline with anomalies."""
        collector = WorkflowMetricsCollector()
        
        # Add normal metrics
        for i in range(3):
            metric = WorkflowMetrics(
                workflow="simple",
                harness="opencode",
                model="haiku",
                status="PASS",
                total_latency_ms=2000,
                per_task_cost_usd=0.04,
                success_rate=95.0,
            )
            collector.add_metric(metric)
        
        # Add anomalous metric
        anomaly_metric = WorkflowMetrics(
            workflow="simple",
            harness="copilot",
            model="haiku",
            status="PASS",
            total_latency_ms=10000,
            per_task_cost_usd=0.04,
            success_rate=85.0,  # Low success rate
        )
        collector.add_metric(anomaly_metric)
        
        collector.calculate_baselines()
        collector.detect_anomalies()
        
        # Should have detected anomaly
        assert len(collector.anomalies) > 0
        
        # Generate report
        generator = AnomalyReportGenerator(collector.metrics, collector.anomalies)
        report = generator.generate_markdown_report()
        
        assert "Anomaly Analysis Report" in report
        assert len(report) > 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
