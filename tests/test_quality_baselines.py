"""
Tests for Quality Baselines — Validate baseline constants and integration.

Coverage:
  - Default threshold values match QUALITY-BASELINES.md
  - All task types have defined thresholds
  - Threshold values are within valid range (0-100)
  - Integration: enforcer + monitor + dashboard work together
  - Baseline rationale (security > code/test > docs/perf)
"""

from __future__ import annotations

import pytest

from src.orchestration.quality.threshold_enforcement import (
    ThresholdEnforcer,
    DEFAULT_THRESHOLDS,
)
from src.orchestration.quality.trend_monitor import TrendMonitor
from src.orchestration.quality.feedback_cycles import FeedbackCycleManager, CycleStage
from src.orchestration.quality.quality_dashboard import QualityDashboard


class TestDefaultThresholdValues:
    """Validate that defaults match QUALITY-BASELINES.md."""

    def test_code_baseline(self):
        assert DEFAULT_THRESHOLDS["code"] == 90.0

    def test_test_baseline(self):
        assert DEFAULT_THRESHOLDS["test"] == 90.0

    def test_documentation_baseline(self):
        assert DEFAULT_THRESHOLDS["documentation"] == 85.0

    def test_performance_baseline(self):
        assert DEFAULT_THRESHOLDS["performance"] == 85.0

    def test_security_baseline(self):
        assert DEFAULT_THRESHOLDS["security"] == 95.0

    def test_default_baseline(self):
        assert DEFAULT_THRESHOLDS["default"] == 85.0

    def test_all_thresholds_in_range(self):
        for task_type, threshold in DEFAULT_THRESHOLDS.items():
            assert 0.0 <= threshold <= 100.0, f"{task_type} threshold {threshold} out of range"

    def test_security_highest_threshold(self):
        non_default = {k: v for k, v in DEFAULT_THRESHOLDS.items() if k != "default"}
        assert DEFAULT_THRESHOLDS["security"] == max(non_default.values())

    def test_code_and_test_equal(self):
        assert DEFAULT_THRESHOLDS["code"] == DEFAULT_THRESHOLDS["test"]

    def test_docs_and_perf_equal(self):
        assert DEFAULT_THRESHOLDS["documentation"] == DEFAULT_THRESHOLDS["performance"]


class TestBaselineIntegration:
    """Integration tests: all three subsystems working together."""

    def test_full_pipeline_pass(self):
        monitor = TrendMonitor()
        enforcer = ThresholdEnforcer()
        manager = FeedbackCycleManager()
        dashboard = QualityDashboard(monitor=monitor, enforcer=enforcer, cycle_manager=manager)

        # Record quality data
        for score in [91, 92, 93, 90, 94]:
            monitor.record("code", float(score))

        # Evaluate threshold
        result = enforcer.evaluate("code", 92.0, task_id="integration-t1")
        assert result.passed

        # Run feedback cycle
        cycle = manager.start_cycle("integration-t1", "code")
        cid = cycle.cycle_id
        manager.advance(cid, CycleStage.QUALITY_ASSESSMENT, score=92.0)
        manager.advance(cid, CycleStage.FEEDBACK_COLLECTION, feedback={"model": "haiku"})
        manager.advance(cid, CycleStage.TREND_ANALYSIS)
        manager.advance(cid, CycleStage.ROUTING_IMPROVEMENT, recommendation="keep_haiku")
        manager.advance(cid, CycleStage.COMPLETE)

        # Dashboard should be healthy
        snap = dashboard.snapshot()
        assert snap.overall_health == "healthy"
        assert snap.compliance_report["compliance_rate"] == pytest.approx(100.0)

    def test_full_pipeline_fail_triggers_alert(self):
        monitor = TrendMonitor()
        enforcer = ThresholdEnforcer()
        manager = FeedbackCycleManager()
        dashboard = QualityDashboard(monitor=monitor, enforcer=enforcer, cycle_manager=manager)

        # Record degrading quality
        from src.orchestration.quality.trend_monitor import QualityDataPoint
        import time
        for score in [92, 93, 94]:
            dp = QualityDataPoint(
                task_type="code",
                score=float(score),
                timestamp=time.time() - 31 * 86400,
            )
            monitor.record_datapoint(dp)
        for score in [78, 79, 80]:
            monitor.record("code", float(score))

        # Evaluate failing threshold
        enforcer.evaluate("code", 78.0, task_id="fail-t1")

        snap = dashboard.snapshot()
        assert snap.overall_health in ("degraded", "critical")
        assert len(snap.alerts) > 0
