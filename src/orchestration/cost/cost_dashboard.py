# -*- coding: utf-8 -*-
"""
CostDashboard — Display and report cost metrics across agents, models, and time.

Provides:
  - Current spend summary by agent/role/model
  - Cost trends over time
  - Cost efficiency metrics
  - Cost optimization opportunities
  - Alert generation for overspend and inefficiency
  - Daily/weekly/monthly report generation

Usage::

    dashboard = CostDashboard()
    dashboard.ingest(metrics)
    summary = dashboard.get_spend_summary()
    print(summary.render())
    
    alerts = dashboard.check_alerts(daily_budget=10.0)
    report = dashboard.generate_report(period="daily")
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SpendSummary:
    """Aggregated spend summary across all dimensions."""
    period: str
    start_date: str
    end_date: str
    total_cost: float
    total_tasks: int
    by_agent: Dict[str, float]
    by_model: Dict[str, float]
    by_role: Dict[str, float]
    by_task_type: Dict[str, float]
    by_date: Dict[str, float]
    avg_cost_per_task: float
    avg_quality: float
    efficiency_score: float  # quality / cost_per_task (normalized)

    def render(self) -> str:
        """Return human-readable dashboard text."""
        lines = [
            f"╔══ Cost Dashboard ({self.period}: {self.start_date} → {self.end_date}) ══╗",
            f"  Total cost:    ${self.total_cost:.4f}",
            f"  Total tasks:   {self.total_tasks}",
            f"  Avg/task:      ${self.avg_cost_per_task:.4f}",
            f"  Avg quality:   {self.avg_quality:.1f}%",
            f"  Efficiency:    {self.efficiency_score:.2f}",
            "",
            "  By Agent:",
        ]
        for agent, cost in sorted(self.by_agent.items(), key=lambda x: -x[1]):
            pct = (cost / self.total_cost * 100) if self.total_cost > 0 else 0
            lines.append(f"    {agent:<30} ${cost:.4f}  ({pct:.1f}%)")
        lines.append("")
        lines.append("  By Model:")
        for model, cost in sorted(self.by_model.items(), key=lambda x: -x[1]):
            pct = (cost / self.total_cost * 100) if self.total_cost > 0 else 0
            lines.append(f"    {model:<30} ${cost:.4f}  ({pct:.1f}%)")
        lines.append("")
        lines.append("  By Role:")
        for role, cost in sorted(self.by_role.items(), key=lambda x: -x[1]):
            pct = (cost / self.total_cost * 100) if self.total_cost > 0 else 0
            lines.append(f"    {role:<30} ${cost:.4f}  ({pct:.1f}%)")
        lines.append("╚" + "═" * 55 + "╝")
        return "\n".join(lines)


@dataclass
class CostAlert:
    """A cost alert triggered by threshold violation."""
    alert_type: str   # "overspend" | "efficiency" | "opportunity" | "trend"
    severity: str     # "info" | "warning" | "critical"
    message: str
    agent: Optional[str]
    threshold: float
    actual_value: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def __str__(self) -> str:
        agent_str = f" [{self.agent}]" if self.agent else ""
        return (
            f"[{self.severity.upper()}]{agent_str} {self.alert_type}: "
            f"{self.message} "
            f"(threshold={self.threshold:.4f}, actual={self.actual_value:.4f})"
        )


@dataclass
class CostReport:
    """A generated cost report for a time period."""
    period: str
    generated_at: str
    summary: SpendSummary
    alerts: List[CostAlert]
    trends: Dict[str, Any]
    top_cost_drivers: List[Tuple[str, float]]
    recommendations_summary: str

    def render(self) -> str:
        lines = [
            f"=== Cost Report ({self.period}) — Generated {self.generated_at} ===",
            "",
            self.summary.render(),
            "",
        ]
        if self.alerts:
            lines.append(f"Alerts ({len(self.alerts)}):")
            for alert in self.alerts:
                lines.append(f"  {alert}")
            lines.append("")
        if self.top_cost_drivers:
            lines.append("Top Cost Drivers:")
            for driver, cost in self.top_cost_drivers[:5]:
                lines.append(f"  {driver}: ${cost:.4f}")
            lines.append("")
        if self.trends:
            lines.append("Trends:")
            for k, v in self.trends.items():
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CostDashboard
# ---------------------------------------------------------------------------

class CostDashboard:
    """
    Aggregate and display cost metrics across all dimensions.

    Ingests task metric records and provides real-time and historical views.
    """

    def __init__(self, quality_threshold: float = 90.0):
        self._metrics: List[dict] = []
        self._quality_threshold = quality_threshold
        self._alert_history: List[CostAlert] = []

    # ------------------------------------------------------------------
    # Data ingestion
    # ------------------------------------------------------------------

    def ingest(self, metrics: List[dict]) -> None:
        """Load (or append) task metric records."""
        self._metrics.extend(metrics)

    def reset(self) -> None:
        """Clear all ingested metrics (for testing)."""
        self._metrics.clear()
        self._alert_history.clear()

    # ------------------------------------------------------------------
    # Spend summary
    # ------------------------------------------------------------------

    def get_spend_summary(
        self,
        period: str = "all",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> SpendSummary:
        """
        Return aggregated spend summary.

        Args:
            period: "daily" | "weekly" | "monthly" | "all"
            start_date: ISO date string (YYYY-MM-DD), inclusive
            end_date: ISO date string (YYYY-MM-DD), inclusive
        """
        records = self._filter_by_period(period, start_date, end_date)

        if not records:
            today = date.today().isoformat()
            return SpendSummary(
                period=period,
                start_date=start_date or today,
                end_date=end_date or today,
                total_cost=0.0,
                total_tasks=0,
                by_agent={},
                by_model={},
                by_role={},
                by_task_type={},
                by_date={},
                avg_cost_per_task=0.0,
                avg_quality=0.0,
                efficiency_score=0.0,
            )

        by_agent: Dict[str, float] = defaultdict(float)
        by_model: Dict[str, float] = defaultdict(float)
        by_role: Dict[str, float] = defaultdict(float)
        by_task_type: Dict[str, float] = defaultdict(float)
        by_date: Dict[str, float] = defaultdict(float)
        qualities: List[float] = []

        for m in records:
            cost = m.get("cost", 0.0)
            agent = m.get("agent", m.get("role", "unknown"))
            model = m.get("model", "unknown")
            role = m.get("role", "unknown")
            task_type = m.get("task_type", "unknown")
            ts = m.get("timestamp", "")
            day = ts[:10] if ts else date.today().isoformat()
            quality = m.get("quality_score")

            by_agent[agent] += cost
            by_model[model] += cost
            by_role[role] += cost
            by_task_type[task_type] += cost
            by_date[day] += cost
            if quality is not None:
                qualities.append(quality)

        total_cost = sum(m.get("cost", 0.0) for m in records)
        total_tasks = len(records)
        avg_cost = total_cost / total_tasks if total_tasks > 0 else 0.0
        avg_quality = statistics.mean(qualities) if qualities else 0.0
        efficiency = avg_quality / avg_cost if avg_cost > 0 else 0.0

        # Determine date range
        dates = sorted(by_date.keys())
        s_date = start_date or (dates[0] if dates else date.today().isoformat())
        e_date = end_date or (dates[-1] if dates else date.today().isoformat())

        return SpendSummary(
            period=period,
            start_date=s_date,
            end_date=e_date,
            total_cost=total_cost,
            total_tasks=total_tasks,
            by_agent=dict(by_agent),
            by_model=dict(by_model),
            by_role=dict(by_role),
            by_task_type=dict(by_task_type),
            by_date=dict(by_date),
            avg_cost_per_task=avg_cost,
            avg_quality=avg_quality,
            efficiency_score=efficiency,
        )

    # ------------------------------------------------------------------
    # Trend analysis
    # ------------------------------------------------------------------

    def get_cost_trends(self, days: int = 7) -> Dict[str, Any]:
        """Analyze cost trends over the last N days."""
        by_date: Dict[str, float] = defaultdict(float)
        for m in self._metrics:
            ts = m.get("timestamp", "")
            day = ts[:10] if ts else date.today().isoformat()
            by_date[day] += m.get("cost", 0.0)

        sorted_days = sorted(by_date.items())[-days:]
        if len(sorted_days) < 2:
            return {"direction": "stable", "change_pct": 0.0, "daily_costs": dict(sorted_days)}

        costs = [c for _, c in sorted_days]
        first_half = statistics.mean(costs[: len(costs) // 2]) if costs else 0
        second_half = statistics.mean(costs[len(costs) // 2 :]) if costs else 0

        if first_half > 0:
            change_pct = (second_half - first_half) / first_half * 100
        else:
            change_pct = 0.0

        direction = "increasing" if change_pct > 5 else "decreasing" if change_pct < -5 else "stable"

        return {
            "direction": direction,
            "change_pct": change_pct,
            "daily_costs": dict(sorted_days),
            "avg_daily": statistics.mean(costs) if costs else 0.0,
        }

    # ------------------------------------------------------------------
    # Alert generation
    # ------------------------------------------------------------------

    def check_alerts(
        self,
        daily_budget: Optional[float] = None,
        efficiency_floor: Optional[float] = None,
        overspend_pct: float = 80.0,  # Alert at 80% of budget
    ) -> List[CostAlert]:
        """Check for alert conditions and return triggered alerts."""
        alerts: List[CostAlert] = []
        today_str = date.today().isoformat()
        today_records = [
            m for m in self._metrics
            if m.get("timestamp", "")[:10] == today_str
        ]
        today_cost = sum(m.get("cost", 0.0) for m in today_records)

        # Overspend alert
        if daily_budget and today_cost >= daily_budget * (overspend_pct / 100):
            severity = "critical" if today_cost >= daily_budget else "warning"
            alerts.append(CostAlert(
                alert_type="overspend",
                severity=severity,
                message=f"Daily spend ${today_cost:.4f} is {today_cost/daily_budget*100:.0f}% of budget",
                agent=None,
                threshold=daily_budget * (overspend_pct / 100),
                actual_value=today_cost,
            ))

        # Per-agent overspend
        by_agent: Dict[str, float] = defaultdict(float)
        for m in today_records:
            agent = m.get("agent", m.get("role", "unknown"))
            by_agent[agent] += m.get("cost", 0.0)

        # Efficiency alert
        qualities = [m.get("quality_score", 0.0) for m in self._metrics if m.get("quality_score")]
        if qualities and efficiency_floor:
            avg_quality = statistics.mean(qualities)
            if avg_quality < efficiency_floor:
                alerts.append(CostAlert(
                    alert_type="efficiency",
                    severity="warning",
                    message=f"Average quality {avg_quality:.1f}% below floor {efficiency_floor:.1f}%",
                    agent=None,
                    threshold=efficiency_floor,
                    actual_value=avg_quality,
                ))

        self._alert_history.extend(alerts)
        return alerts

    def get_alert_history(self) -> List[CostAlert]:
        return list(self._alert_history)

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    def generate_report(self, period: str = "daily") -> CostReport:
        """Generate a structured cost report for the given period."""
        summary = self.get_spend_summary(period=period)
        alerts = self.check_alerts()
        trends = self.get_cost_trends()

        # Top cost drivers
        all_drivers = list(summary.by_agent.items()) + list(summary.by_model.items())
        top_drivers = sorted(all_drivers, key=lambda x: -x[1])[:5]

        # Simple recommendations summary
        if summary.total_cost == 0:
            rec_summary = "No cost data available."
        elif trends.get("direction") == "increasing":
            rec_summary = "Cost is trending up. Review model assignments and consider downgrading low-complexity tasks."
        else:
            rec_summary = "Cost is stable or decreasing. Continue monitoring."

        return CostReport(
            period=period,
            generated_at=datetime.utcnow().isoformat() + "Z",
            summary=summary,
            alerts=alerts,
            trends=trends,
            top_cost_drivers=top_drivers,
            recommendations_summary=rec_summary,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _filter_by_period(
        self,
        period: str,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> List[dict]:
        """Filter metrics by time period."""
        if start_date and end_date:
            return [
                m for m in self._metrics
                if start_date <= m.get("timestamp", "")[:10] <= end_date
            ]

        today = date.today()
        if period == "daily":
            cutoff = today.isoformat()
        elif period == "weekly":
            cutoff = (today - timedelta(days=7)).isoformat()
        elif period == "monthly":
            cutoff = (today - timedelta(days=30)).isoformat()
        else:
            return list(self._metrics)

        return [
            m for m in self._metrics
            if m.get("timestamp", "")[:10] >= cutoff
        ]

    def top_cost_agents(self, n: int = 5) -> List[Tuple[str, float]]:
        """Return the top N agents by total cost."""
        by_agent: Dict[str, float] = defaultdict(float)
        for m in self._metrics:
            agent = m.get("agent", m.get("role", "unknown"))
            by_agent[agent] += m.get("cost", 0.0)
        return sorted(by_agent.items(), key=lambda x: -x[1])[:n]
