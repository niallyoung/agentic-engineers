"""Tests for queue migration metrics (Phase 4)."""

import pytest
from pathlib import Path
from src.orchestration.metrics.queue_migration_metrics import (
    QueueHealthMetrics,
    MigrationProgressMetrics,
    MultiHarnessMetrics,
    QueueAlertsAndThresholds,
)


class TestQueueHealthMetrics:
    """Test queue health metrics collection."""
    
    def test_record_task_completion(self, tmp_path):
        """Record task completion and latency."""
        metrics = QueueHealthMetrics(metrics_dir=tmp_path)
        metrics.record_task_completion("task-1", 5.0, success=True)
        
        assert metrics.tasks_processed == 1
        assert metrics.tasks_failed == 0
        assert len(metrics.latencies) == 1
    
    def test_average_latency_calculation(self, tmp_path):
        """Calculate average latency correctly."""
        metrics = QueueHealthMetrics(metrics_dir=tmp_path)
        
        metrics.record_task_completion("task-1", 5.0, success=True)
        metrics.record_task_completion("task-2", 15.0, success=True)
        
        assert metrics.get_average_latency() == 10.0
    
    def test_error_rate_calculation(self, tmp_path):
        """Calculate error rate correctly."""
        metrics = QueueHealthMetrics(metrics_dir=tmp_path)
        
        for i in range(9):
            metrics.record_task_completion(f"task-{i}", 5.0, success=True)
        
        metrics.record_task_completion("task-failed", 10.0, success=False)
        
        assert metrics.get_error_rate() == 10.0  # 1 failure out of 10 tasks


class TestMigrationProgressMetrics:
    """Test migration progress tracking."""
    
    def test_record_task_migrated(self):
        """Record task migration."""
        metrics = MigrationProgressMetrics()
        
        metrics.record_task_migrated("session-1")
        metrics.record_task_migrated("session-1")
        metrics.record_task_migrated("session-2")
        
        assert metrics.tasks_migrated["session-1"] == 2
        assert metrics.tasks_migrated["session-2"] == 1
    
    def test_migration_progress_summary(self):
        """Get migration progress summary."""
        metrics = MigrationProgressMetrics()
        
        metrics.record_task_migrated("session-1")
        metrics.record_task_migrated("session-2")
        
        progress = metrics.get_migration_progress()
        
        assert progress['total_tasks_migrated'] == 2
        assert progress['sessions_in_progress'] == 2
        assert progress['migration_errors'] == 0


class TestMultiHarnessMetrics:
    """Test per-harness metrics."""
    
    def test_record_task_per_harness(self):
        """Record tasks per harness."""
        metrics = MultiHarnessMetrics()
        
        metrics.record_task("copilot", "task-1", 5.0, success=True)
        metrics.record_task("claude", "task-2", 10.0, success=True)
        metrics.record_task("copilot", "task-3", 8.0, success=False)
        
        summary = metrics.get_harness_summary()
        
        assert summary["copilot"]["total_tasks"] == 2
        assert summary["copilot"]["tasks_failed"] == 1
        assert summary["claude"]["total_tasks"] == 1
    
    def test_harness_summary_has_expected_fields(self):
        """Verify harness summary has all expected fields."""
        metrics = MultiHarnessMetrics()
        
        metrics.record_task("copilot", "task-1", 5.0)
        
        summary = metrics.get_harness_summary()
        
        assert "copilot" in summary
        assert "total_tasks" in summary["copilot"]
        assert "error_rate" in summary["copilot"]
        assert "avg_latency" in summary["copilot"]


class TestQueueAlertsAndThresholds:
    """Test queue alerts and thresholds."""
    
    def test_alert_on_high_latency(self, tmp_path):
        """Alert when latency exceeds threshold."""
        metrics = QueueHealthMetrics(metrics_dir=tmp_path)
        alerts = QueueAlertsAndThresholds()
        
        # Record tasks with high latency
        for i in range(5):
            metrics.record_task_completion(f"task-{i}", 100.0, success=True)
        
        triggered = alerts.check_health(metrics)
        
        assert len(triggered) > 0
        assert any(a['metric'] == 'average_latency' for a in triggered)
    
    def test_alert_on_high_error_rate(self, tmp_path):
        """Alert when error rate exceeds threshold."""
        metrics = QueueHealthMetrics(metrics_dir=tmp_path)
        alerts = QueueAlertsAndThresholds()
        
        # Record mostly failures
        for i in range(10):
            metrics.record_task_completion(f"task-{i}", 5.0, success=(i == 0))
        
        triggered = alerts.check_health(metrics)
        
        assert len(triggered) > 0
        assert any(a['metric'] == 'error_rate' for a in triggered)
    
    def test_no_alerts_on_healthy_metrics(self, tmp_path):
        """No alerts when metrics are healthy."""
        metrics = QueueHealthMetrics(metrics_dir=tmp_path)
        alerts = QueueAlertsAndThresholds()
        
        # Record healthy metrics
        for i in range(5):
            metrics.record_task_completion(f"task-{i}", 5.0, success=True)
        
        triggered = alerts.check_health(metrics)
        
        assert len(triggered) == 0
