"""
Tests for Monitoring & Observability — metrics, prometheus, tracing,
health checks, SLO tracking, alerting, and structured logging.

30+ tests covering all monitoring components.
"""

import json
import logging
import time
import pytest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from src.orchestration.monitoring.metrics import (
    Counter, Gauge, Histogram, MetricsRegistry, create_orchestrator_metrics,
)
from src.orchestration.monitoring.prometheus_exporter import PrometheusExporter
from src.orchestration.monitoring.structured_logger import StructuredLogger, get_logger
from src.orchestration.monitoring.tracing import Tracer, Span
from src.orchestration.monitoring.health_check import (
    HealthCheck, HealthStatus, HealthReport,
)
from src.orchestration.monitoring.slo_tracker import (
    SLOTracker, SLO, SLOStatus, create_default_slos,
)
from src.orchestration.monitoring.alerting import (
    AlertManager, AlertRule, AlertSeverity, AlertState, create_default_alert_rules,
)


# ===========================================================================
# Counter Tests
# ===========================================================================

class TestCounter:
    def test_initial_value_is_zero(self):
        c = Counter("test_counter")
        assert c.value == 0.0

    def test_inc_default_increments_by_one(self):
        c = Counter("test_counter")
        c.inc()
        assert c.value == 1.0

    def test_inc_by_amount(self):
        c = Counter("test_counter")
        c.inc(5.0)
        assert c.value == 5.0

    def test_inc_accumulates(self):
        c = Counter("test_counter")
        c.inc(3)
        c.inc(7)
        assert c.value == 10.0

    def test_inc_negative_raises(self):
        c = Counter("test_counter")
        with pytest.raises(ValueError):
            c.inc(-1)

    def test_labels_stored(self):
        c = Counter("test_counter", labels={"role": "engineer"})
        assert c.labels == {"role": "engineer"}


# ===========================================================================
# Gauge Tests
# ===========================================================================

class TestGauge:
    def test_initial_value_is_zero(self):
        g = Gauge("test_gauge")
        assert g.value == 0.0

    def test_set_value(self):
        g = Gauge("test_gauge")
        g.set(42.0)
        assert g.value == 42.0

    def test_inc_and_dec(self):
        g = Gauge("test_gauge")
        g.inc(10)
        g.dec(3)
        assert g.value == 7.0

    def test_can_go_negative(self):
        g = Gauge("test_gauge")
        g.dec(5)
        assert g.value == -5.0


# ===========================================================================
# Histogram Tests
# ===========================================================================

class TestHistogram:
    def test_initial_count_is_zero(self):
        h = Histogram("test_histogram")
        assert h.count == 0

    def test_observe_increments_count(self):
        h = Histogram("test_histogram")
        h.observe(1.5)
        assert h.count == 1

    def test_observe_accumulates_sum(self):
        h = Histogram("test_histogram")
        h.observe(2.0)
        h.observe(3.0)
        assert h.sum == 5.0

    def test_bucket_counts_correct(self):
        h = Histogram("test_histogram", buckets=[1.0, 5.0, 10.0])
        h.observe(0.5)  # <= 1.0, <= 5.0, <= 10.0
        h.observe(3.0)  # <= 5.0, <= 10.0
        h.observe(7.0)  # <= 10.0
        assert h.bucket_counts[1.0] == 1
        assert h.bucket_counts[5.0] == 2
        assert h.bucket_counts[10.0] == 3

    def test_inf_bucket_counts_all(self):
        h = Histogram("test_histogram", buckets=[1.0])
        h.observe(0.5)
        h.observe(100.0)
        assert h.bucket_counts[float("inf")] == 2


# ===========================================================================
# MetricsRegistry Tests
# ===========================================================================

class TestMetricsRegistry:
    def test_counter_idempotent(self):
        reg = MetricsRegistry()
        c1 = reg.counter("my_counter")
        c2 = reg.counter("my_counter")
        assert c1 is c2

    def test_gauge_idempotent(self):
        reg = MetricsRegistry()
        g1 = reg.gauge("my_gauge")
        g2 = reg.gauge("my_gauge")
        assert g1 is g2

    def test_histogram_idempotent(self):
        reg = MetricsRegistry()
        h1 = reg.histogram("my_histogram")
        h2 = reg.histogram("my_histogram")
        assert h1 is h2

    def test_get_all_returns_all_metrics(self):
        reg = MetricsRegistry()
        reg.counter("c1")
        reg.gauge("g1")
        all_metrics = reg.get_all()
        assert len(all_metrics) == 2

    def test_label_differentiation(self):
        reg = MetricsRegistry()
        c1 = reg.counter("tasks", labels={"role": "engineer"})
        c2 = reg.counter("tasks", labels={"role": "senior"})
        c1.inc(5)
        assert c2.value == 0.0

    def test_create_orchestrator_metrics(self):
        reg = MetricsRegistry()
        metrics = create_orchestrator_metrics(reg)
        assert "tasks_total" in metrics
        assert "queue_depth" in metrics
        assert "task_duration_seconds" in metrics
        assert "quality_score" in metrics


# ===========================================================================
# PrometheusExporter Tests
# ===========================================================================

class TestPrometheusExporter:
    def test_export_counter(self):
        reg = MetricsRegistry()
        c = reg.counter("test_counter", description="A test counter")
        c.inc(42)
        exporter = PrometheusExporter(reg)
        output = exporter.export()
        assert "# HELP test_counter A test counter" in output
        assert "# TYPE test_counter counter" in output
        assert "test_counter 42.0" in output

    def test_export_gauge(self):
        reg = MetricsRegistry()
        g = reg.gauge("test_gauge")
        g.set(7.5)
        exporter = PrometheusExporter(reg)
        output = exporter.export()
        assert "# TYPE test_gauge gauge" in output
        assert "test_gauge 7.5" in output

    def test_export_histogram(self):
        reg = MetricsRegistry()
        h = reg.histogram("test_hist", buckets=[1.0, 5.0])
        h.observe(0.5)
        h.observe(3.0)
        exporter = PrometheusExporter(reg)
        output = exporter.export()
        assert "# TYPE test_hist histogram" in output
        assert 'test_hist_bucket{le="1.0"}' in output
        assert "test_hist_sum" in output
        assert "test_hist_count" in output

    def test_export_with_labels(self):
        reg = MetricsRegistry()
        reg.counter("labeled_counter", labels={"env": "prod"})
        exporter = PrometheusExporter(reg)
        output = exporter.export()
        assert 'env="prod"' in output

    def test_export_to_file(self, tmp_path):
        reg = MetricsRegistry()
        reg.counter("file_counter").inc(1)
        exporter = PrometheusExporter(reg)
        filepath = str(tmp_path / "metrics.txt")
        exporter.export_to_file(filepath)
        assert Path(filepath).exists()
        content = Path(filepath).read_text()
        assert "file_counter" in content


# ===========================================================================
# StructuredLogger Tests
# ===========================================================================

class TestStructuredLogger:
    def test_log_outputs_json(self, capsys):
        logger = StructuredLogger("test_logger_json")
        logger.info("test message")
        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["message"] == "test message"
        assert data["level"] == "INFO"

    def test_log_includes_extra_fields(self, capsys):
        logger = StructuredLogger("test_logger_extra")
        logger.info("task routed", task_id="task-001", role="engineer")
        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["task_id"] == "task-001"
        assert data["role"] == "engineer"

    def test_bind_adds_context(self, capsys):
        logger = StructuredLogger("test_logger_bind")
        bound = logger.bind(service="orchestrator")
        bound.info("bound message")
        captured = capsys.readouterr()
        data = json.loads(captured.out.strip())
        assert data["service"] == "orchestrator"

    def test_get_logger_returns_same_instance(self):
        l1 = get_logger("shared_logger")
        l2 = get_logger("shared_logger")
        assert l1 is l2


# ===========================================================================
# Tracing Tests
# ===========================================================================

class TestTracer:
    def test_start_and_end_span(self):
        tracer = Tracer("test_service")
        span = tracer.start_span("test_op")
        tracer.end_span(span)
        completed = tracer.get_completed_spans()
        assert len(completed) == 1
        assert completed[0].name == "test_op"

    def test_span_has_trace_id(self):
        tracer = Tracer("test_service")
        span = tracer.start_span("op")
        assert span.trace_id is not None
        tracer.end_span(span)

    def test_span_duration_calculated(self):
        tracer = Tracer("test_service")
        span = tracer.start_span("op")
        time.sleep(0.01)
        tracer.end_span(span)
        assert span.duration_ms is not None
        assert span.duration_ms >= 10

    def test_trace_context_manager(self):
        tracer = Tracer("test_service")
        with tracer.trace("ctx_op") as span:
            span.set_attribute("key", "value")
        assert span.status == "ok"
        assert span.end_time is not None

    def test_trace_context_manager_error(self):
        tracer = Tracer("test_service")
        with pytest.raises(ValueError):
            with tracer.trace("failing_op") as span:
                raise ValueError("test error")
        assert span.status == "error"

    def test_nested_spans_share_trace_id(self):
        tracer = Tracer("test_service")
        with tracer.trace("parent") as parent:
            child = tracer.start_span("child")
            assert child.trace_id == parent.trace_id
            tracer.end_span(child)

    def test_span_set_attribute(self):
        tracer = Tracer("test_service")
        span = tracer.start_span("op")
        span.set_attribute("role", "engineer")
        assert span.attributes["role"] == "engineer"
        tracer.end_span(span)

    def test_span_add_event(self):
        tracer = Tracer("test_service")
        span = tracer.start_span("op")
        span.add_event("checkpoint", step=1)
        assert len(span.events) == 1
        assert span.events[0]["name"] == "checkpoint"
        tracer.end_span(span)


# ===========================================================================
# HealthCheck Tests
# ===========================================================================

class TestHealthCheck:
    def test_healthy_when_no_checks(self):
        hc = HealthCheck()
        report = hc.check()
        assert report.status == HealthStatus.HEALTHY

    def test_healthy_check_passes(self):
        hc = HealthCheck()
        hc.add_check("always_ok", lambda: True)
        report = hc.check()
        assert report.status == HealthStatus.HEALTHY
        assert report.healthy is True

    def test_failing_critical_check_marks_unhealthy(self):
        hc = HealthCheck()
        hc.add_check("failing", lambda: False, critical=True)
        report = hc.check()
        assert report.status == HealthStatus.UNHEALTHY
        assert report.healthy is False

    def test_failing_non_critical_marks_degraded(self):
        hc = HealthCheck()
        hc.add_check("degraded_check", lambda: False, critical=False)
        report = hc.check()
        assert report.status == HealthStatus.DEGRADED

    def test_exception_in_check_marks_unhealthy(self):
        hc = HealthCheck()
        hc.add_check("exploding", lambda: 1 / 0, critical=True)
        report = hc.check()
        assert report.status == HealthStatus.UNHEALTHY

    def test_report_to_dict(self):
        hc = HealthCheck()
        hc.add_check("ok_check", lambda: True)
        report = hc.check()
        d = report.to_dict()
        assert "status" in d
        assert "checks" in d
        assert d["healthy"] is True

    def test_liveness_always_true(self):
        hc = HealthCheck()
        assert hc.liveness() is True

    def test_readiness_false_when_unhealthy(self):
        hc = HealthCheck()
        hc.add_check("critical_fail", lambda: False, critical=True)
        assert hc.readiness() is False

    def test_decorator_registration(self):
        hc = HealthCheck()

        @hc.register("decorated_check")
        def my_check():
            return True

        report = hc.check()
        names = [c.name for c in report.checks]
        assert "decorated_check" in names


# ===========================================================================
# SLO Tracker Tests
# ===========================================================================

class TestSLOTracker:
    def test_define_and_evaluate_slo(self):
        tracker = SLOTracker()
        tracker.define_slo(SLO(
            name="success_rate",
            description="95% success",
            target=0.95,
            window_minutes=60,
        ))
        # Record 10 successes
        for _ in range(10):
            tracker.record_event("success_rate", 1.0)
        result = tracker.evaluate("success_rate")
        assert result.status == SLOStatus.MET

    def test_slo_breached(self):
        tracker = SLOTracker()
        tracker.define_slo(SLO(
            name="success_rate",
            description="95% success",
            target=0.95,
            window_minutes=60,
        ))
        # Record 5 successes and 5 failures = 50% rate
        for _ in range(5):
            tracker.record_event("success_rate", 1.0)
        for _ in range(5):
            tracker.record_event("success_rate", 0.0)
        result = tracker.evaluate("success_rate")
        assert result.status == SLOStatus.BREACHED

    def test_insufficient_data(self):
        tracker = SLOTracker()
        tracker.define_slo(SLO(
            name="success_rate",
            description="95% success",
            target=0.95,
            window_minutes=60,
        ))
        tracker.record_event("success_rate", 1.0)  # only 1 event
        result = tracker.evaluate("success_rate")
        assert result.status == SLOStatus.INSUFFICIENT_DATA

    def test_lte_slo_met(self):
        tracker = SLOTracker()
        tracker.define_slo(SLO(
            name="error_rate",
            description="Error rate <= 1%",
            target=0.01,
            window_minutes=60,
            comparison="lte",
        ))
        # Record 10 events with 0% error rate
        for _ in range(10):
            tracker.record_event("error_rate", 0.0)
        result = tracker.evaluate("error_rate")
        assert result.status == SLOStatus.MET

    def test_evaluate_all(self):
        tracker = SLOTracker()
        for slo in create_default_slos():
            tracker.define_slo(slo)
        results = tracker.evaluate_all()
        assert len(results) == len(create_default_slos())

    def test_unknown_slo_raises(self):
        tracker = SLOTracker()
        with pytest.raises(KeyError):
            tracker.evaluate("nonexistent_slo")


# ===========================================================================
# AlertManager Tests
# ===========================================================================

class TestAlertManager:
    def test_no_alerts_when_condition_false(self):
        manager = AlertManager()
        manager.add_rule(AlertRule(
            name="TestAlert",
            description="Test",
            severity=AlertSeverity.WARNING,
            condition=lambda m: False,
        ))
        alerts = manager.evaluate({})
        assert len(alerts) == 0

    def test_alert_fires_when_condition_true(self):
        manager = AlertManager()
        manager.add_rule(AlertRule(
            name="HighError",
            description="High error rate",
            severity=AlertSeverity.CRITICAL,
            condition=lambda m: m.get("error_rate", 0) > 0.05,
            for_minutes=0,
        ))
        alerts = manager.evaluate({"error_rate": 0.10})
        assert len(alerts) == 1
        assert alerts[0].name == "HighError"
        assert alerts[0].severity == AlertSeverity.CRITICAL

    def test_alert_resolves_when_condition_clears(self):
        manager = AlertManager()
        manager.add_rule(AlertRule(
            name="QueueHigh",
            description="Queue high",
            severity=AlertSeverity.WARNING,
            condition=lambda m: m.get("queue_depth", 0) > 100,
            for_minutes=0,
        ))
        manager.evaluate({"queue_depth": 200})
        assert len(manager.get_active_alerts()) == 1
        manager.evaluate({"queue_depth": 10})
        assert len(manager.get_active_alerts()) == 0

    def test_for_minutes_delays_firing(self):
        manager = AlertManager()
        manager.add_rule(AlertRule(
            name="SlowAlert",
            description="Slow to fire",
            severity=AlertSeverity.WARNING,
            condition=lambda m: True,
            for_minutes=60,  # 60 minutes required
        ))
        alerts = manager.evaluate({})
        assert len(alerts) == 0  # Not fired yet

    def test_alert_history_tracked(self):
        manager = AlertManager()
        manager.add_rule(AlertRule(
            name="TestAlert",
            description="Test",
            severity=AlertSeverity.INFO,
            condition=lambda m: True,
            for_minutes=0,
        ))
        manager.evaluate({})
        history = manager.get_alert_history()
        assert len(history) == 1

    def test_create_default_alert_rules(self):
        rules = create_default_alert_rules()
        assert len(rules) >= 5
        names = [r.name for r in rules]
        assert "HighErrorRate" in names
        assert "QueueDepthHigh" in names
        assert "SLOBreach" in names

    def test_exception_in_condition_does_not_fire(self):
         manager = AlertManager()
         manager.add_rule(AlertRule(
             name="BrokenAlert",
             description="Broken condition",
             severity=AlertSeverity.WARNING,
             condition=lambda m: 1 / 0,  # will raise
             for_minutes=0,
         ))
         alerts = manager.evaluate({})
         assert len(alerts) == 0


# ===========================================================================
# Token Cost Anomaly Alert Tests
# ===========================================================================

class TestTokenCostAnomalyAlerts:
    """Tests for cost anomaly detection alerts."""

    def test_daily_cost_high_alert_fires(self):
        """Alert fires when daily cost exceeds $100."""
        manager = AlertManager()
        manager.add_rule(AlertRule(
            name="TokenCostDailyHigh",
            description="Daily token cost exceeds $100",
            severity=AlertSeverity.WARNING,
            condition=lambda m: m.get("daily_token_cost", 0) > 100,
            for_minutes=0,  # No duration requirement for testing
        ))
        alerts = manager.evaluate({"daily_token_cost": 150.50})
        assert len(alerts) == 1
        assert alerts[0].name == "TokenCostDailyHigh"
        assert alerts[0].severity == AlertSeverity.WARNING

    def test_daily_cost_high_alert_does_not_fire_below_threshold(self):
        """Alert does not fire when daily cost is below $100."""
        manager = AlertManager()
        manager.add_rule(AlertRule(
            name="TokenCostDailyHigh",
            description="Daily token cost exceeds $100",
            severity=AlertSeverity.WARNING,
            condition=lambda m: m.get("daily_token_cost", 0) > 100,
            for_minutes=0,
        ))
        alerts = manager.evaluate({"daily_token_cost": 75.25})
        assert len(alerts) == 0

    def test_cost_per_task_high_alert_fires(self):
        """Alert fires when cost per task exceeds $5."""
        manager = AlertManager()
        manager.add_rule(AlertRule(
            name="TokenCostPerTaskHigh",
            description="Cost per task exceeds $5",
            severity=AlertSeverity.WARNING,
            condition=lambda m: m.get("cost_per_task", 0) > 5.0,
            for_minutes=0,  # No duration requirement for testing
        ))
        alerts = manager.evaluate({"cost_per_task": 7.50})
        assert len(alerts) == 1
        assert alerts[0].name == "TokenCostPerTaskHigh"

    def test_cost_per_task_high_alert_does_not_fire_below_threshold(self):
        """Alert does not fire when cost per task is below $5."""
        manager = AlertManager()
        manager.add_rule(AlertRule(
            name="TokenCostPerTaskHigh",
            description="Cost per task exceeds $5",
            severity=AlertSeverity.WARNING,
            condition=lambda m: m.get("cost_per_task", 0) > 5.0,
            for_minutes=0,
        ))
        alerts = manager.evaluate({"cost_per_task": 3.25})
        assert len(alerts) == 0

    def test_cache_hit_rate_low_alert_fires(self):
        """Alert fires when cache hit rate drops below 50%."""
        manager = AlertManager()
        manager.add_rule(AlertRule(
            name="TokenCacheHitRateLow",
            description="Cache hit rate below 50%",
            severity=AlertSeverity.WARNING,
            condition=lambda m: m.get("cache_hit_rate", 1.0) < 0.5,
            for_minutes=0,  # No duration requirement for testing
        ))
        alerts = manager.evaluate({"cache_hit_rate": 0.35})
        assert len(alerts) == 1
        assert alerts[0].name == "TokenCacheHitRateLow"

    def test_cache_hit_rate_low_alert_does_not_fire_above_threshold(self):
        """Alert does not fire when cache hit rate is above 50%."""
        manager = AlertManager()
        manager.add_rule(AlertRule(
            name="TokenCacheHitRateLow",
            description="Cache hit rate below 50%",
            severity=AlertSeverity.WARNING,
            condition=lambda m: m.get("cache_hit_rate", 1.0) < 0.5,
            for_minutes=0,
        ))
        alerts = manager.evaluate({"cache_hit_rate": 0.75})
        assert len(alerts) == 0

    def test_token_usage_anomaly_alert_fires(self):
        """Alert fires when token usage is > 2.5σ from mean."""
        manager = AlertManager()
        manager.add_rule(AlertRule(
            name="TokenUsageAnomaly",
            description="Token usage anomaly detected (> 2.5σ from mean)",
            severity=AlertSeverity.WARNING,
            condition=lambda m: m.get("token_usage_sigma", 0) > 2.5,
            for_minutes=0,  # No duration requirement for testing
        ))
        alerts = manager.evaluate({"token_usage_sigma": 3.2})
        assert len(alerts) == 1
        assert alerts[0].name == "TokenUsageAnomaly"

    def test_token_usage_anomaly_alert_does_not_fire_below_threshold(self):
        """Alert does not fire when token usage is within 2.5σ."""
        manager = AlertManager()
        manager.add_rule(AlertRule(
            name="TokenUsageAnomaly",
            description="Token usage anomaly detected (> 2.5σ from mean)",
            severity=AlertSeverity.WARNING,
            condition=lambda m: m.get("token_usage_sigma", 0) > 2.5,
            for_minutes=0,
        ))
        alerts = manager.evaluate({"token_usage_sigma": 1.8})
        assert len(alerts) == 0

    def test_multiple_cost_alerts_can_fire_simultaneously(self):
        """Multiple cost anomaly alerts can fire at the same time."""
        manager = AlertManager()
        manager.add_rule(AlertRule(
            name="TokenCostDailyHigh",
            description="Daily token cost exceeds $100",
            severity=AlertSeverity.WARNING,
            condition=lambda m: m.get("daily_token_cost", 0) > 100,
            for_minutes=0,
        ))
        manager.add_rule(AlertRule(
            name="TokenCostPerTaskHigh",
            description="Cost per task exceeds $5",
            severity=AlertSeverity.WARNING,
            condition=lambda m: m.get("cost_per_task", 0) > 5.0,
            for_minutes=0,
        ))
        manager.add_rule(AlertRule(
            name="TokenCacheHitRateLow",
            description="Cache hit rate below 50%",
            severity=AlertSeverity.WARNING,
            condition=lambda m: m.get("cache_hit_rate", 1.0) < 0.5,
            for_minutes=0,
        ))
        
        metrics = {
            "daily_token_cost": 150.0,
            "cost_per_task": 6.5,
            "cache_hit_rate": 0.40,
        }
        alerts = manager.evaluate(metrics)
        assert len(alerts) == 3
        alert_names = {a.name for a in alerts}
        assert alert_names == {
            "TokenCostDailyHigh",
            "TokenCostPerTaskHigh",
            "TokenCacheHitRateLow",
        }

    def test_cost_anomaly_alert_annotations(self):
        """Cost anomaly alerts include proper annotations."""
        manager = AlertManager()
        manager.add_rule(AlertRule(
            name="TokenCostDailyHigh",
            description="Daily token cost exceeds $100",
            severity=AlertSeverity.WARNING,
            condition=lambda m: m.get("daily_token_cost", 0) > 100,
            for_minutes=0,
            annotations={
                "runbook_url": "docs/runbooks/token-cost-high.md",
                "summary": "Daily token cost is high",
                "impact": "Cost control",
            },
        ))
        alerts = manager.evaluate({"daily_token_cost": 150.0})
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.annotations["runbook_url"] == "docs/runbooks/token-cost-high.md"
        assert alert.annotations["impact"] == "Cost control"

    def test_create_default_alert_rules_includes_cost_anomalies(self):
        """Default alert rules include all cost anomaly alerts."""
        rules = create_default_alert_rules()
        rule_names = {r.name for r in rules}
        
        cost_anomaly_alerts = {
            "TokenCostDailyHigh",
            "TokenCostPerTaskHigh",
            "TokenCacheHitRateLow",
            "TokenUsageAnomaly",
        }
        assert cost_anomaly_alerts.issubset(rule_names)
