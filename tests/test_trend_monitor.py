"""
Tests for TrendMonitor — Quality trend tracking and analysis.

Coverage:
  - QualityDataPoint validation
  - Recording data points
  - Moving average computation (7-day, 30-day)
  - Trend direction classification
  - TrendReport fields
  - Degrading / improving helpers
  - Edge cases (no data, single point, boundary deltas)
"""

from __future__ import annotations

import time
import pytest

from src.orchestration.quality.trend_monitor import (
    TrendMonitor,
    TrendDirection,
    QualityDataPoint,
)


# ---------------------------------------------------------------------------
# QualityDataPoint
# ---------------------------------------------------------------------------

class TestQualityDataPoint:
    def test_valid_datapoint(self):
        dp = QualityDataPoint(task_type="code", score=92.0)
        assert dp.task_type == "code"
        assert dp.score == 92.0
        assert dp.timestamp > 0

    def test_score_zero_valid(self):
        dp = QualityDataPoint(task_type="test", score=0.0)
        assert dp.score == 0.0

    def test_score_hundred_valid(self):
        dp = QualityDataPoint(task_type="test", score=100.0)
        assert dp.score == 100.0

    def test_score_below_zero_raises(self):
        with pytest.raises(ValueError, match="score must be 0-100"):
            QualityDataPoint(task_type="code", score=-1.0)

    def test_score_above_hundred_raises(self):
        with pytest.raises(ValueError, match="score must be 0-100"):
            QualityDataPoint(task_type="code", score=101.0)

    def test_optional_fields(self):
        dp = QualityDataPoint(
            task_type="security",
            score=95.0,
            task_id="task-001",
            role="security_engineer",
            metadata={"model": "opus"},
        )
        assert dp.task_id == "task-001"
        assert dp.role == "security_engineer"
        assert dp.metadata["model"] == "opus"


# ---------------------------------------------------------------------------
# TrendMonitor — recording
# ---------------------------------------------------------------------------

class TestTrendMonitorRecording:
    def test_record_returns_datapoint(self):
        monitor = TrendMonitor()
        dp = monitor.record("code", 90.0)
        assert isinstance(dp, QualityDataPoint)

    def test_record_stores_data(self):
        monitor = TrendMonitor()
        monitor.record("code", 90.0)
        monitor.record("code", 85.0)
        assert len(monitor.data_for("code")) == 2

    def test_record_datapoint_directly(self):
        monitor = TrendMonitor()
        dp = QualityDataPoint(task_type="test", score=88.0)
        monitor.record_datapoint(dp)
        assert len(monitor.data_for("test")) == 1

    def test_task_types_returns_all(self):
        monitor = TrendMonitor()
        monitor.record("code", 90.0)
        monitor.record("test", 88.0)
        monitor.record("docs", 82.0)
        assert set(monitor.task_types()) == {"code", "test", "docs"}

    def test_data_for_unknown_type_returns_empty(self):
        monitor = TrendMonitor()
        assert monitor.data_for("unknown") == []


# ---------------------------------------------------------------------------
# TrendMonitor — moving averages
# ---------------------------------------------------------------------------

class TestMovingAverage:
    def test_seven_day_average(self):
        monitor = TrendMonitor()
        monitor.record("code", 90.0)
        monitor.record("code", 80.0)
        avg = monitor.moving_average("code", 7)
        assert avg == pytest.approx(85.0)

    def test_thirty_day_average(self):
        monitor = TrendMonitor()
        for score in [80, 85, 90, 95]:
            monitor.record("code", float(score))
        avg = monitor.moving_average("code", 30)
        assert avg == pytest.approx(87.5)

    def test_moving_average_no_data_returns_none(self):
        monitor = TrendMonitor()
        assert monitor.moving_average("code", 7) is None

    def test_moving_average_excludes_old_data(self):
        monitor = TrendMonitor()
        # Add an old data point (40 days ago)
        old_dp = QualityDataPoint(
            task_type="code",
            score=50.0,
            timestamp=time.time() - 40 * 86400,
        )
        monitor.record_datapoint(old_dp)
        monitor.record("code", 90.0)
        # 7-day average should only include the recent point
        avg = monitor.moving_average("code", 7)
        assert avg == pytest.approx(90.0)


# ---------------------------------------------------------------------------
# TrendMonitor — trend reports
# ---------------------------------------------------------------------------

class TestTrendReport:
    def test_insufficient_data_with_no_points(self):
        monitor = TrendMonitor()
        report = monitor.trend_report("code")
        assert report.direction == TrendDirection.INSUFFICIENT_DATA
        assert report.sample_count == 0

    def test_insufficient_data_with_two_points(self):
        monitor = TrendMonitor()
        monitor.record("code", 90.0)
        monitor.record("code", 88.0)
        report = monitor.trend_report("code")
        assert report.direction == TrendDirection.INSUFFICIENT_DATA

    def test_stable_trend(self):
        monitor = TrendMonitor()
        for score in [88, 89, 90, 88, 89]:
            monitor.record("code", float(score))
        report = monitor.trend_report("code")
        assert report.direction == TrendDirection.STABLE

    def test_improving_trend(self):
        monitor = TrendMonitor()
        # Add old baseline data (31 days ago)
        for score in [80, 81, 82]:
            dp = QualityDataPoint(
                task_type="code",
                score=float(score),
                timestamp=time.time() - 31 * 86400,
            )
            monitor.record_datapoint(dp)
        # Add recent high scores
        for score in [90, 92, 93]:
            monitor.record("code", float(score))
        report = monitor.trend_report("code")
        assert report.direction == TrendDirection.IMPROVING
        assert report.delta > 2.0

    def test_degrading_trend(self):
        monitor = TrendMonitor()
        # Add old baseline data (31 days ago)
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
        report = monitor.trend_report("code")
        assert report.direction == TrendDirection.DEGRADING
        assert report.delta < -2.0

    def test_degrading_trend_has_alert(self):
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
        report = monitor.trend_report("code")
        assert report.alert is not None
        assert "degrading" in report.alert.lower()

    def test_stable_trend_no_alert(self):
        monitor = TrendMonitor()
        for score in [88, 89, 90, 88, 89]:
            monitor.record("code", float(score))
        report = monitor.trend_report("code")
        assert report.alert is None

    def test_report_min_max_std(self):
        monitor = TrendMonitor()
        for score in [80, 90, 100]:
            monitor.record("code", float(score))
        report = monitor.trend_report("code")
        assert report.min_score == 80.0
        assert report.max_score == 100.0
        assert report.std_dev > 0

    def test_all_trend_reports(self):
        monitor = TrendMonitor()
        monitor.record("code", 90.0)
        monitor.record("test", 88.0)
        reports = monitor.all_trend_reports()
        assert "code" in reports
        assert "test" in reports

    def test_degrading_task_types(self):
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
        assert "code" in monitor.degrading_task_types()

    def test_improving_task_types(self):
        monitor = TrendMonitor()
        for score in [80, 81, 82]:
            dp = QualityDataPoint(
                task_type="test",
                score=float(score),
                timestamp=time.time() - 31 * 86400,
            )
            monitor.record_datapoint(dp)
        for score in [90, 92, 93]:
            monitor.record("test", float(score))
        assert "test" in monitor.improving_task_types()
