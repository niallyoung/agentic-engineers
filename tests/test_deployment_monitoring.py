"""
Deployment Monitoring & Alerting — Tests.

Validates DeploymentMonitor:
  - Records metrics correctly
  - Generates accurate snapshots
  - Fires alerts at correct thresholds
  - Triggers auto-rollback callback on critical alerts
  - Handles concurrent recording safely
"""

from __future__ import annotations

import threading
import time
from typing import List
from unittest.mock import MagicMock

import pytest

from src.orchestration.deployment.monitoring import (
    Alert,
    AlertSeverity,
    DeploymentMonitor,
    MetricSnapshot,
)


# ─────────────────────────────────────────────────────────────────────────── #
# Helpers
# ─────────────────────────────────────────────────────────────────────────── #

def _make_monitor(**kwargs) -> DeploymentMonitor:
    defaults = dict(
        error_rate_threshold=0.05,
        latency_p99_threshold_ms=500.0,
        quality_min=0.80,
        window_seconds=60.0,
    )
    defaults.update(kwargs)
    return DeploymentMonitor(**defaults)


def _fill_monitor(monitor: DeploymentMonitor, n: int = 20, error_rate: float = 0.0,
                  latency_ms: float = 100.0, quality: float = 0.95) -> None:
    for i in range(n):
        is_error = (i / n) < error_rate
        monitor.record_request(
            latency_ms=latency_ms,
            is_error=is_error,
            tokens=500,
            cost_usd=0.002,
            quality_score=0.0 if is_error else quality,
        )


# ─────────────────────────────────────────────────────────────────────────── #
# 1. Basic recording
# ─────────────────────────────────────────────────────────────────────────── #

class TestMonitorRecording:
    def test_record_single_request(self):
        mon = _make_monitor()
        mon.record_request(latency_ms=100.0)
        snap = mon.snapshot()
        assert snap.total_requests == 1

    def test_record_multiple_requests(self):
        mon = _make_monitor()
        for _ in range(10):
            mon.record_request(latency_ms=100.0)
        snap = mon.snapshot()
        assert snap.total_requests == 10

    def test_error_count_tracked(self):
        mon = _make_monitor()
        mon.record_request(latency_ms=100.0, is_error=True)
        mon.record_request(latency_ms=100.0, is_error=False)
        snap = mon.snapshot()
        assert snap.error_count == 1

    def test_token_cost_accumulated(self):
        mon = _make_monitor()
        mon.record_request(latency_ms=100.0, tokens=1000, cost_usd=0.01)
        mon.record_request(latency_ms=100.0, tokens=500, cost_usd=0.005)
        snap = mon.snapshot()
        assert snap.total_tokens == 1500
        assert abs(snap.total_cost_usd - 0.015) < 1e-9


# ─────────────────────────────────────────────────────────────────────────── #
# 2. Snapshot accuracy
# ─────────────────────────────────────────────────────────────────────────── #

class TestMonitorSnapshot:
    def test_empty_snapshot(self):
        mon = _make_monitor()
        snap = mon.snapshot()
        assert snap.total_requests == 0
        assert snap.error_rate == 0.0
        assert snap.avg_latency_ms == 0.0

    def test_error_rate_calculation(self):
        mon = _make_monitor()
        for _ in range(10):
            mon.record_request(latency_ms=100.0, is_error=False)
        for _ in range(2):
            mon.record_request(latency_ms=100.0, is_error=True)
        snap = mon.snapshot()
        # 2 errors / 12 total = ~16.7% (in rolling window)
        assert snap.error_rate > 0.0

    def test_avg_latency_calculation(self):
        mon = _make_monitor()
        mon.record_request(latency_ms=100.0)
        mon.record_request(latency_ms=200.0)
        snap = mon.snapshot()
        assert abs(snap.avg_latency_ms - 150.0) < 1.0

    def test_quality_score_calculation(self):
        mon = _make_monitor()
        mon.record_request(latency_ms=100.0, quality_score=1.0)
        mon.record_request(latency_ms=100.0, quality_score=0.8)
        snap = mon.snapshot()
        assert abs(snap.quality_score - 0.9) < 0.01

    def test_snapshot_has_timestamp(self):
        mon = _make_monitor()
        snap = mon.snapshot()
        assert snap.timestamp is not None
        assert "T" in snap.timestamp  # ISO 8601

    def test_snapshot_stage_passed_through(self):
        mon = _make_monitor()
        snap = mon.snapshot(stage=25)
        assert snap.stage == 25

    def test_snapshot_to_dict(self):
        import json
        mon = _make_monitor()
        mon.record_request(latency_ms=100.0)
        snap = mon.snapshot()
        json.dumps(snap.to_dict())


# ─────────────────────────────────────────────────────────────────────────── #
# 3. Alerting — error rate
# ─────────────────────────────────────────────────────────────────────────── #

class TestMonitorAlertErrorRate:
    def test_no_alert_below_threshold(self):
        mon = _make_monitor(error_rate_threshold=0.10)
        _fill_monitor(mon, n=20, error_rate=0.0)
        alerts = mon.check_alerts()
        error_alerts = [a for a in alerts if a.metric_name == "error_rate"]
        assert error_alerts == []

    def test_warning_alert_at_threshold(self):
        mon = _make_monitor(error_rate_threshold=0.05)
        # Record 10% errors (above threshold but below 2x)
        _fill_monitor(mon, n=20, error_rate=0.10)
        alerts = mon.check_alerts()
        error_alerts = [a for a in alerts if a.metric_name == "error_rate"]
        assert len(error_alerts) >= 1

    def test_critical_alert_at_2x_threshold(self):
        mon = _make_monitor(error_rate_threshold=0.05)
        # Record 20% errors (above 2x threshold)
        _fill_monitor(mon, n=20, error_rate=0.20)
        alerts = mon.check_alerts()
        critical = [a for a in alerts if a.severity == AlertSeverity.CRITICAL and a.metric_name == "error_rate"]
        assert len(critical) >= 1


# ─────────────────────────────────────────────────────────────────────────── #
# 4. Alerting — latency and quality
# ─────────────────────────────────────────────────────────────────────────── #

class TestMonitorAlertLatencyQuality:
    def test_latency_alert_above_threshold(self):
        mon = _make_monitor(latency_p99_threshold_ms=200.0)
        _fill_monitor(mon, n=20, latency_ms=500.0)
        alerts = mon.check_alerts()
        lat_alerts = [a for a in alerts if a.metric_name == "p99_latency_ms"]
        assert len(lat_alerts) >= 1

    def test_no_latency_alert_below_threshold(self):
        mon = _make_monitor(latency_p99_threshold_ms=1000.0)
        _fill_monitor(mon, n=20, latency_ms=100.0)
        alerts = mon.check_alerts()
        lat_alerts = [a for a in alerts if a.metric_name == "p99_latency_ms"]
        assert lat_alerts == []

    def test_quality_alert_below_minimum(self):
        mon = _make_monitor(quality_min=0.90)
        _fill_monitor(mon, n=20, quality=0.70)
        alerts = mon.check_alerts()
        q_alerts = [a for a in alerts if a.metric_name == "quality_score"]
        assert len(q_alerts) >= 1


# ─────────────────────────────────────────────────────────────────────────── #
# 5. Auto-rollback
# ─────────────────────────────────────────────────────────────────────────── #

class TestMonitorAutoRollback:
    def test_auto_rollback_triggered_on_critical(self):
        callback = MagicMock()
        mon = _make_monitor(
            error_rate_threshold=0.05,
            auto_rollback_callback=callback,
        )
        # Record 30% errors → critical alert
        _fill_monitor(mon, n=20, error_rate=0.30)
        mon.check_alerts()
        callback.assert_called_once()

    def test_auto_rollback_not_triggered_on_warning(self):
        callback = MagicMock()
        mon = _make_monitor(
            error_rate_threshold=0.05,
            auto_rollback_callback=callback,
        )
        # Record 7% errors → warning only (below 2x threshold)
        _fill_monitor(mon, n=100, error_rate=0.07)
        mon.check_alerts()
        callback.assert_not_called()

    def test_rollback_triggered_flag_set(self):
        callback = MagicMock()
        mon = _make_monitor(
            error_rate_threshold=0.05,
            auto_rollback_callback=callback,
        )
        _fill_monitor(mon, n=20, error_rate=0.30)
        mon.check_alerts()
        assert mon.rollback_triggered is True

    def test_rollback_triggered_only_once(self):
        callback = MagicMock()
        mon = _make_monitor(
            error_rate_threshold=0.05,
            auto_rollback_callback=callback,
        )
        _fill_monitor(mon, n=20, error_rate=0.30)
        mon.check_alerts()
        mon.check_alerts()  # second call
        callback.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────── #
# 6. Reset and alert history
# ─────────────────────────────────────────────────────────────────────────── #

class TestMonitorReset:
    def test_reset_clears_metrics(self):
        mon = _make_monitor()
        _fill_monitor(mon, n=10)
        mon.reset()
        snap = mon.snapshot()
        assert snap.total_requests == 0

    def test_reset_clears_alerts(self):
        mon = _make_monitor(error_rate_threshold=0.05)
        _fill_monitor(mon, n=20, error_rate=0.30)
        mon.check_alerts()
        mon.reset()
        assert mon.all_alerts == []

    def test_all_alerts_accumulate(self):
        mon = _make_monitor(error_rate_threshold=0.05)
        _fill_monitor(mon, n=20, error_rate=0.30)
        mon.check_alerts()
        _fill_monitor(mon, n=20, error_rate=0.30)
        mon.check_alerts()
        assert len(mon.all_alerts) >= 2


# ─────────────────────────────────────────────────────────────────────────── #
# 7. Concurrency
# ─────────────────────────────────────────────────────────────────────────── #

class TestMonitorConcurrency:
    def test_concurrent_recording_is_safe(self):
        mon = _make_monitor()
        errors: List[str] = []
        lock = threading.Lock()

        def record(i: int):
            try:
                mon.record_request(latency_ms=float(i), is_error=(i % 10 == 0))
            except Exception as exc:
                with lock:
                    errors.append(str(exc))

        threads = [threading.Thread(target=record, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert errors == []
        snap = mon.snapshot()
        assert snap.total_requests == 50
