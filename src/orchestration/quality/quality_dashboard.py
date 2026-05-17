"""
Quality Dashboard — Display quality metrics, trends, and threshold compliance.

Supports terminal (text) output and Prometheus/Grafana-compatible output.

Usage::

    dashboard = QualityDashboard(monitor=monitor, enforcer=enforcer, cycle_manager=manager)
    print(dashboard.render_terminal())
    print(dashboard.render_prometheus())
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .trend_monitor import TrendMonitor, TrendDirection
from .threshold_enforcement import ThresholdEnforcer
from .feedback_cycles import FeedbackCycleManager


@dataclass
class DashboardSnapshot:
    """Point-in-time snapshot of all quality metrics."""
    timestamp: float
    trend_reports: Dict[str, Any]
    compliance_report: Dict[str, Any]
    cycle_metrics: Dict[str, Any]
    alerts: List[str]
    overall_health: str   # "healthy" | "degraded" | "critical"


class QualityDashboard:
    """
    Aggregates quality data from TrendMonitor, ThresholdEnforcer, and
    FeedbackCycleManager into a unified dashboard view.
    """

    def __init__(
        self,
        monitor: Optional[TrendMonitor] = None,
        enforcer: Optional[ThresholdEnforcer] = None,
        cycle_manager: Optional[FeedbackCycleManager] = None,
    ) -> None:
        self.monitor = monitor or TrendMonitor()
        self.enforcer = enforcer or ThresholdEnforcer()
        self.cycle_manager = cycle_manager or FeedbackCycleManager()

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> DashboardSnapshot:
        """Capture current state of all quality systems."""
        trend_reports = {
            tt: {
                "direction": r.direction.value,
                "current_avg": r.current_avg,
                "baseline_avg": r.baseline_avg,
                "delta": r.delta,
                "sample_count": r.sample_count,
                "alert": r.alert,
            }
            for tt, r in self.monitor.all_trend_reports().items()
        }

        compliance = self.enforcer.compliance_report()
        cycle_metrics = self.cycle_manager.cycle_metrics()

        alerts: List[str] = []
        for tt, r in self.monitor.all_trend_reports().items():
            if r.alert:
                alerts.append(r.alert)

        # Determine overall health
        degrading = self.monitor.degrading_task_types()
        compliance_rate = compliance.get("compliance_rate")
        if degrading or (compliance_rate is not None and compliance_rate < 70):
            overall_health = "critical"
        elif compliance_rate is not None and compliance_rate < 90:
            overall_health = "degraded"
        else:
            overall_health = "healthy"

        return DashboardSnapshot(
            timestamp=time.time(),
            trend_reports=trend_reports,
            compliance_report=compliance,
            cycle_metrics=cycle_metrics,
            alerts=alerts,
            overall_health=overall_health,
        )

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render_terminal(self) -> str:
        """Render a human-readable terminal dashboard."""
        snap = self.snapshot()
        lines = [
            "=" * 60,
            "  QUALITY DASHBOARD",
            f"  {_fmt_time(snap.timestamp)}",
            f"  Overall Health: {snap.overall_health.upper()}",
            "=" * 60,
        ]

        # Trends
        lines.append("\n── Quality Trends ──────────────────────────────────────")
        if snap.trend_reports:
            for tt, r in snap.trend_reports.items():
                arrow = {"improving": "↑", "degrading": "↓", "stable": "→", "insufficient_data": "?"}.get(
                    r["direction"], "?"
                )
                lines.append(
                    f"  {tt:20s} {arrow} {r['direction']:20s} "
                    f"avg={r['current_avg']:.1f}  Δ={r['delta']:+.1f}  n={r['sample_count']}"
                )
        else:
            lines.append("  (no trend data)")

        # Compliance
        lines.append("\n── Threshold Compliance ────────────────────────────────")
        comp = snap.compliance_report
        if comp["total"] > 0:
            lines.append(f"  Tasks evaluated : {comp['total']}")
            lines.append(f"  Passed          : {comp['passed']}")
            lines.append(f"  Failed          : {comp['failed']}")
            lines.append(f"  Escalations     : {comp.get('escalations', 0)}")
            lines.append(f"  Compliance rate : {comp['compliance_rate']:.1f}%")
            lines.append(f"  Avg score       : {comp.get('avg_score', 0):.1f}")
        else:
            lines.append("  (no evaluations recorded)")

        # Feedback cycles
        lines.append("\n── Feedback Cycles ─────────────────────────────────────")
        cm = snap.cycle_metrics
        lines.append(f"  Total cycles    : {cm['total_cycles']}")
        lines.append(f"  Complete        : {cm['complete_cycles']}")
        lines.append(f"  In progress     : {cm['in_progress_cycles']}")
        if cm["avg_quality_score"] is not None:
            lines.append(f"  Avg quality     : {cm['avg_quality_score']:.1f}")

        # Alerts
        if snap.alerts:
            lines.append("\n── Alerts ──────────────────────────────────────────────")
            for alert in snap.alerts:
                lines.append(f"  ⚠  {alert}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def render_prometheus(self) -> str:
        """Render Prometheus-compatible metrics text."""
        snap = self.snapshot()
        lines: List[str] = []

        # Trend metrics
        for tt, r in snap.trend_reports.items():
            safe_tt = tt.replace("-", "_")
            lines.append(f'quality_trend_current_avg{{task_type="{tt}"}} {r["current_avg"]:.4f}')
            lines.append(f'quality_trend_delta{{task_type="{tt}"}} {r["delta"]:.4f}')
            lines.append(f'quality_trend_samples{{task_type="{tt}"}} {r["sample_count"]}')

        # Compliance metrics
        comp = snap.compliance_report
        if comp["total"] > 0:
            lines.append(f'quality_compliance_total {comp["total"]}')
            lines.append(f'quality_compliance_passed {comp["passed"]}')
            lines.append(f'quality_compliance_failed {comp["failed"]}')
            lines.append(f'quality_compliance_rate {comp["compliance_rate"]:.4f}')

        # Cycle metrics
        cm = snap.cycle_metrics
        lines.append(f'quality_cycles_total {cm["total_cycles"]}')
        lines.append(f'quality_cycles_complete {cm["complete_cycles"]}')
        lines.append(f'quality_cycles_in_progress {cm["in_progress_cycles"]}')
        if cm["avg_quality_score"] is not None:
            lines.append(f'quality_cycles_avg_score {cm["avg_quality_score"]:.4f}')

        # Health
        health_val = {"healthy": 1, "degraded": 0.5, "critical": 0}.get(snap.overall_health, 0)
        lines.append(f"quality_overall_health {health_val}")

        return "\n".join(lines)

    def render_json(self) -> Dict[str, Any]:
        """Return dashboard data as a dict (JSON-serialisable)."""
        snap = self.snapshot()
        return {
            "timestamp": snap.timestamp,
            "overall_health": snap.overall_health,
            "trend_reports": snap.trend_reports,
            "compliance_report": snap.compliance_report,
            "cycle_metrics": snap.cycle_metrics,
            "alerts": snap.alerts,
        }


def _fmt_time(ts: float) -> str:
    import datetime
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
