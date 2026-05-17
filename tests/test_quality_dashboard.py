"""
Tests for QualityDashboard — Unified quality metrics display.

Coverage:
  - Snapshot generation
  - Terminal rendering
  - Prometheus rendering
  - JSON rendering
  - Overall health classification (healthy / degraded / critical)
  - Alert propagation from TrendMonitor
  - Empty state rendering
  - Integration with all three subsystems
"""

from __future__ import annotations

import time
import pytest

from src.orchestration.quality.trend_monitor import TrendMonitor, QualityDataPoint
from src.orchestration.quality.threshold_enforcement import ThresholdEnforcer
from src.orchestration.quality.feedback_cycles import FeedbackCycleManager, CycleStage
from src.orchestration.quality.quality_dashboard import QualityDashboard


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dashboard_with_data() -> QualityDashboard:
    monitor = TrendMonitor()
    enforcer = ThresholdEnforcer()
    manager = FeedbackCycleManager()

    # Add trend data
    for score in [88, 89, 90, 88, 89]:
        monitor.record("code", float(score))

    # Add compliance data
    enforcer.evaluate("code", 92.0, task_id="t1")
    enforcer.evaluate("test", 88.0, task_id="t2")

    # Add a complete cycle
    cycle = manager.start_cycle("t1", "code")
    cid = cycle.cycle_id
    manager.advance(cid, CycleStage.QUALITY_ASSESSMENT, score=92.0)
    manager.advance(cid, CycleStage.FEEDBACK_COLLECTION)
    manager.advance(cid, CycleStage.TREND_ANALYSIS)
    manager.advance(cid, CycleStage.ROUTING_IMPROVEMENT)
    manager.advance(cid, CycleStage.COMPLETE)

    return QualityDashboard(monitor=monitor, enforcer=enforcer, cycle_manager=manager)


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

class TestDashboardSnapshot:
    def test_snapshot_returns_snapshot(self):
        dashboard = QualityDashboard()
        snap = dashboard.snapshot()
        assert snap is not None

    def test_snapshot_has_timestamp(self):
        dashboard = QualityDashboard()
        snap = dashboard.snapshot()
        assert snap.timestamp <= time.time()

    def test_snapshot_empty_is_healthy(self):
        dashboard = QualityDashboard()
        snap = dashboard.snapshot()
        assert snap.overall_health == "healthy"

    def test_snapshot_with_data(self):
        dashboard = _make_dashboard_with_data()
        snap = dashboard.snapshot()
        assert "code" in snap.trend_reports
        assert snap.compliance_report["total"] == 2

    def test_snapshot_degrading_is_critical(self):
        monitor = TrendMonitor()
        # Add old high baseline
        for score in [92, 93, 94]:
            dp = QualityDataPoint(
                task_type="code",
                score=float(score),
                timestamp=time.time() - 31 * 86400,
            )
            monitor.record_datapoint(dp)
        # Add recent low scores
        for score in [80, 82, 81]:
            monitor.record("code", float(score))
        dashboard = QualityDashboard(monitor=monitor)
        snap = dashboard.snapshot()
        assert snap.overall_health == "critical"

    def test_snapshot_alerts_from_degrading(self):
        monitor = TrendMonitor()
        for score in [92, 93, 94]:
            dp = QualityDataPoint(
                task_type="code",
                score=float(score),
                timestamp=time.time() - 31 * 86400,
            )
            monitor.record_datapoint(dp)
        for score in [80, 82, 81]:
            monitor.record("code", float(score))
        dashboard = QualityDashboard(monitor=monitor)
        snap = dashboard.snapshot()
        assert len(snap.alerts) > 0


# ---------------------------------------------------------------------------
# Terminal rendering
# ---------------------------------------------------------------------------

class TestTerminalRendering:
    def test_render_terminal_returns_string(self):
        dashboard = QualityDashboard()
        output = dashboard.render_terminal()
        assert isinstance(output, str)

    def test_render_terminal_contains_header(self):
        dashboard = QualityDashboard()
        output = dashboard.render_terminal()
        assert "QUALITY DASHBOARD" in output

    def test_render_terminal_contains_trends_section(self):
        dashboard = _make_dashboard_with_data()
        output = dashboard.render_terminal()
        assert "Quality Trends" in output

    def test_render_terminal_contains_compliance_section(self):
        dashboard = _make_dashboard_with_data()
        output = dashboard.render_terminal()
        assert "Threshold Compliance" in output

    def test_render_terminal_contains_cycles_section(self):
        dashboard = _make_dashboard_with_data()
        output = dashboard.render_terminal()
        assert "Feedback Cycles" in output

    def test_render_terminal_shows_health(self):
        dashboard = QualityDashboard()
        output = dashboard.render_terminal()
        assert "HEALTHY" in output.upper() or "DEGRADED" in output.upper() or "CRITICAL" in output.upper()


# ---------------------------------------------------------------------------
# Prometheus rendering
# ---------------------------------------------------------------------------

class TestPrometheusRendering:
    def test_render_prometheus_returns_string(self):
        dashboard = _make_dashboard_with_data()
        output = dashboard.render_prometheus()
        assert isinstance(output, str)

    def test_render_prometheus_contains_trend_metrics(self):
        dashboard = _make_dashboard_with_data()
        output = dashboard.render_prometheus()
        assert "quality_trend_current_avg" in output

    def test_render_prometheus_contains_compliance_metrics(self):
        dashboard = _make_dashboard_with_data()
        output = dashboard.render_prometheus()
        assert "quality_compliance_total" in output

    def test_render_prometheus_contains_cycle_metrics(self):
        dashboard = _make_dashboard_with_data()
        output = dashboard.render_prometheus()
        assert "quality_cycles_total" in output

    def test_render_prometheus_contains_health(self):
        dashboard = _make_dashboard_with_data()
        output = dashboard.render_prometheus()
        assert "quality_overall_health" in output


# ---------------------------------------------------------------------------
# JSON rendering
# ---------------------------------------------------------------------------

class TestJsonRendering:
    def test_render_json_returns_dict(self):
        dashboard = _make_dashboard_with_data()
        data = dashboard.render_json()
        assert isinstance(data, dict)

    def test_render_json_has_required_keys(self):
        dashboard = _make_dashboard_with_data()
        data = dashboard.render_json()
        for key in ["timestamp", "overall_health", "trend_reports", "compliance_report", "cycle_metrics", "alerts"]:
            assert key in data

    def test_render_json_overall_health_valid(self):
        dashboard = _make_dashboard_with_data()
        data = dashboard.render_json()
        assert data["overall_health"] in ("healthy", "degraded", "critical")
