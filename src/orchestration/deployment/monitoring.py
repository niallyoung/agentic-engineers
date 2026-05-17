"""
Deployment Monitoring & Alerting System.

Tracks error rates, latency, throughput, and cost metrics across all
deployment stages. Triggers alerts on anomalies and supports automatic
rollback on critical errors.

Features:
- Real-time metric collection (error rate, latency, throughput, cost)
- Per-stage metric snapshots
- Configurable alert thresholds
- Automatic rollback signalling on critical errors
- Thread-safe metric accumulation
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """A monitoring alert."""
    severity: AlertSeverity
    message: str
    metric_name: str
    metric_value: float
    threshold: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    stage: Optional[int] = None  # rollout stage pct, if applicable

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity.value,
            "message": self.message,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "timestamp": self.timestamp,
            "stage": self.stage,
        }


@dataclass
class MetricSnapshot:
    """Point-in-time snapshot of deployment metrics."""
    timestamp: str
    stage: Optional[int]
    total_requests: int
    error_count: int
    error_rate: float          # 0.0–1.0
    avg_latency_ms: float
    p99_latency_ms: float
    throughput_rps: float      # requests per second
    total_tokens: int
    total_cost_usd: float
    quality_score: float       # 0.0–1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "stage": self.stage,
            "total_requests": self.total_requests,
            "error_count": self.error_count,
            "error_rate": self.error_rate,
            "avg_latency_ms": self.avg_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "throughput_rps": self.throughput_rps,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "quality_score": self.quality_score,
        }


@dataclass
class _RequestRecord:
    """Internal record of a single request."""
    latency_ms: float
    is_error: bool
    tokens: int
    cost_usd: float
    quality_score: float
    timestamp: float  # monotonic time


class DeploymentMonitor:
    """
    Thread-safe deployment monitoring and alerting system.

    Usage::

        monitor = DeploymentMonitor(
            error_rate_threshold=0.05,
            latency_p99_threshold_ms=2000,
            auto_rollback_callback=lambda: rollout.rollback(),
        )

        # Record each request
        monitor.record_request(
            latency_ms=120.5,
            is_error=False,
            tokens=500,
            cost_usd=0.002,
            quality_score=0.95,
        )

        # Get current snapshot
        snap = monitor.snapshot(stage=10)

        # Check for alerts
        alerts = monitor.check_alerts(stage=10)
    """

    def __init__(
        self,
        error_rate_threshold: float = 0.05,
        latency_p99_threshold_ms: float = 2000.0,
        quality_min: float = 0.80,
        window_seconds: float = 300.0,  # 5-minute rolling window
        auto_rollback_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        self.error_rate_threshold = error_rate_threshold
        self.latency_p99_threshold_ms = latency_p99_threshold_ms
        self.quality_min = quality_min
        self.window_seconds = window_seconds
        self.auto_rollback_callback = auto_rollback_callback

        self._lock = threading.Lock()
        self._records: Deque[_RequestRecord] = deque()
        self._alerts: List[Alert] = []
        self._rollback_triggered = False

        # Cumulative counters (never reset)
        self._total_requests = 0
        self._total_errors = 0
        self._total_tokens = 0
        self._total_cost_usd = 0.0

    # ------------------------------------------------------------------ #
    # Recording
    # ------------------------------------------------------------------ #

    def record_request(
        self,
        latency_ms: float,
        is_error: bool = False,
        tokens: int = 0,
        cost_usd: float = 0.0,
        quality_score: float = 1.0,
    ) -> None:
        """Record a single request's metrics."""
        now = time.monotonic()
        record = _RequestRecord(
            latency_ms=latency_ms,
            is_error=is_error,
            tokens=tokens,
            cost_usd=cost_usd,
            quality_score=quality_score,
            timestamp=now,
        )
        with self._lock:
            self._records.append(record)
            self._total_requests += 1
            if is_error:
                self._total_errors += 1
            self._total_tokens += tokens
            self._total_cost_usd += cost_usd
            self._evict_old_records(now)

    def _evict_old_records(self, now: float) -> None:
        """Remove records outside the rolling window (must hold lock)."""
        cutoff = now - self.window_seconds
        while self._records and self._records[0].timestamp < cutoff:
            self._records.popleft()

    # ------------------------------------------------------------------ #
    # Snapshot
    # ------------------------------------------------------------------ #

    def snapshot(self, stage: Optional[int] = None) -> MetricSnapshot:
        """Return a point-in-time metric snapshot."""
        now = time.monotonic()
        with self._lock:
            self._evict_old_records(now)
            records = list(self._records)
            total_req = self._total_requests
            total_err = self._total_errors
            total_tok = self._total_tokens
            total_cost = self._total_cost_usd

        n = len(records)
        if n == 0:
            return MetricSnapshot(
                timestamp=datetime.now(timezone.utc).isoformat(),
                stage=stage,
                total_requests=total_req,
                error_count=total_err,
                error_rate=0.0,
                avg_latency_ms=0.0,
                p99_latency_ms=0.0,
                throughput_rps=0.0,
                total_tokens=total_tok,
                total_cost_usd=total_cost,
                quality_score=1.0,
            )

        latencies = sorted(r.latency_ms for r in records)
        errors = sum(1 for r in records if r.is_error)
        qualities = [r.quality_score for r in records]

        window_duration = max(records[-1].timestamp - records[0].timestamp, 1e-6)
        throughput = n / window_duration

        p99_idx = max(0, int(0.99 * n) - 1)

        return MetricSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            stage=stage,
            total_requests=total_req,
            error_count=total_err,
            error_rate=errors / n,
            avg_latency_ms=sum(latencies) / n,
            p99_latency_ms=latencies[p99_idx],
            throughput_rps=throughput,
            total_tokens=total_tok,
            total_cost_usd=total_cost,
            quality_score=sum(qualities) / n,
        )

    # ------------------------------------------------------------------ #
    # Alerting
    # ------------------------------------------------------------------ #

    def check_alerts(self, stage: Optional[int] = None) -> List[Alert]:
        """
        Evaluate current metrics against thresholds.

        Returns any new alerts generated. Also triggers auto-rollback
        callback if a CRITICAL alert fires and callback is configured.
        """
        snap = self.snapshot(stage=stage)
        new_alerts: List[Alert] = []

        # Error rate
        if snap.error_rate > self.error_rate_threshold:
            severity = (
                AlertSeverity.CRITICAL
                if snap.error_rate > self.error_rate_threshold * 2
                else AlertSeverity.WARNING
            )
            new_alerts.append(Alert(
                severity=severity,
                message=(
                    f"Error rate {snap.error_rate:.1%} exceeds threshold "
                    f"{self.error_rate_threshold:.1%}"
                ),
                metric_name="error_rate",
                metric_value=snap.error_rate,
                threshold=self.error_rate_threshold,
                stage=stage,
            ))

        # P99 latency
        if snap.p99_latency_ms > self.latency_p99_threshold_ms and snap.total_requests > 0:
            new_alerts.append(Alert(
                severity=AlertSeverity.WARNING,
                message=(
                    f"P99 latency {snap.p99_latency_ms:.0f}ms exceeds threshold "
                    f"{self.latency_p99_threshold_ms:.0f}ms"
                ),
                metric_name="p99_latency_ms",
                metric_value=snap.p99_latency_ms,
                threshold=self.latency_p99_threshold_ms,
                stage=stage,
            ))

        # Quality score
        if snap.quality_score < self.quality_min and snap.total_requests > 0:
            severity = (
                AlertSeverity.CRITICAL
                if snap.quality_score < self.quality_min * 0.9
                else AlertSeverity.WARNING
            )
            new_alerts.append(Alert(
                severity=severity,
                message=(
                    f"Quality score {snap.quality_score:.2f} below minimum "
                    f"{self.quality_min:.2f}"
                ),
                metric_name="quality_score",
                metric_value=snap.quality_score,
                threshold=self.quality_min,
                stage=stage,
            ))

        with self._lock:
            self._alerts.extend(new_alerts)

        # Auto-rollback on critical alerts
        critical = [a for a in new_alerts if a.severity == AlertSeverity.CRITICAL]
        if critical and self.auto_rollback_callback and not self._rollback_triggered:
            logger.critical(
                "CRITICAL alert(s) detected — triggering auto-rollback: %s",
                [a.message for a in critical],
            )
            self._rollback_triggered = True
            try:
                self.auto_rollback_callback()
            except Exception as exc:  # noqa: BLE001
                logger.error("Auto-rollback callback failed: %s", exc)

        return new_alerts

    # ------------------------------------------------------------------ #
    # Accessors
    # ------------------------------------------------------------------ #

    @property
    def all_alerts(self) -> List[Alert]:
        with self._lock:
            return list(self._alerts)

    @property
    def critical_alerts(self) -> List[Alert]:
        return [a for a in self.all_alerts if a.severity == AlertSeverity.CRITICAL]

    @property
    def rollback_triggered(self) -> bool:
        return self._rollback_triggered

    def reset(self) -> None:
        """Reset all metrics and alerts (useful for stage transitions)."""
        with self._lock:
            self._records.clear()
            self._alerts.clear()
            self._rollback_triggered = False
            self._total_requests = 0
            self._total_errors = 0
            self._total_tokens = 0
            self._total_cost_usd = 0.0
