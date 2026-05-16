"""
Alerting — Alert rule evaluation and firing.

Defines alerting rules (similar to Prometheus AlertManager) that
evaluate conditions against metrics and fire alerts when thresholds
are breached.

Usage:
    manager = AlertManager()

    manager.add_rule(AlertRule(
        name="HighErrorRate",
        description="Error rate exceeds 5%",
        severity=AlertSeverity.CRITICAL,
        condition=lambda metrics: metrics.get("error_rate", 0) > 0.05,
        for_minutes=5,
    ))

    alerts = manager.evaluate(current_metrics)
    for alert in alerts:
        print(alert.name, alert.severity, alert.message)
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    PAGE = "page"  # Requires immediate human response


class AlertState(Enum):
    """Alert lifecycle states."""
    INACTIVE = "inactive"
    PENDING = "pending"    # Condition met but not yet for required duration
    FIRING = "firing"
    RESOLVED = "resolved"


@dataclass
class AlertRule:
    """
    An alerting rule definition.

    Attributes:
        name: Unique rule identifier
        description: Human-readable description
        severity: Alert severity level
        condition: Callable(metrics_dict) -> bool — True means alert should fire
        for_minutes: How long condition must be true before firing (default: 0)
        annotations: Additional metadata (runbook_url, summary, etc.)
    """
    name: str
    description: str
    severity: AlertSeverity
    condition: Callable[[Dict[str, Any]], bool]
    for_minutes: float = 0.0
    annotations: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """A fired alert instance."""
    name: str
    severity: AlertSeverity
    state: AlertState
    message: str
    fired_at: float
    resolved_at: Optional[float] = None
    annotations: Dict[str, str] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)

    @property
    def duration_minutes(self) -> float:
        end = self.resolved_at or time.time()
        return (end - self.fired_at) / 60.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "severity": self.severity.value,
            "state": self.state.value,
            "message": self.message,
            "fired_at": self.fired_at,
            "resolved_at": self.resolved_at,
            "duration_minutes": round(self.duration_minutes, 2),
            "annotations": self.annotations,
            "labels": self.labels,
        }


class AlertManager:
    """
    Evaluate alert rules against current metrics.

    Tracks pending/firing state per rule and handles
    the for_minutes duration requirement.
    """

    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._pending_since: Dict[str, float] = {}  # rule_name -> timestamp when condition first met
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []

    def add_rule(self, rule: AlertRule) -> None:
        """Register an alert rule."""
        self._rules[rule.name] = rule

    def evaluate(self, metrics: Dict[str, Any]) -> List[Alert]:
        """
        Evaluate all rules against current metrics.

        Args:
            metrics: Current metrics snapshot (dict of name -> value)

        Returns:
            List of currently firing alerts.
        """
        now = time.time()
        fired = []

        for name, rule in self._rules.items():
            try:
                condition_met = rule.condition(metrics)
            except Exception:
                condition_met = False

            if condition_met:
                if name not in self._pending_since:
                    self._pending_since[name] = now

                pending_duration = (now - self._pending_since[name]) / 60.0

                if pending_duration >= rule.for_minutes:
                    if name not in self._active_alerts:
                        alert = Alert(
                            name=name,
                            severity=rule.severity,
                            state=AlertState.FIRING,
                            message=rule.description,
                            fired_at=now,
                            annotations=rule.annotations,
                        )
                        self._active_alerts[name] = alert
                        self._alert_history.append(alert)
                    fired.append(self._active_alerts[name])
                else:
                    # Still pending
                    if name in self._active_alerts:
                        fired.append(self._active_alerts[name])
            else:
                # Condition no longer met — resolve if was firing
                if name in self._active_alerts:
                    alert = self._active_alerts.pop(name)
                    alert.state = AlertState.RESOLVED
                    alert.resolved_at = now
                self._pending_since.pop(name, None)

        return fired

    def get_active_alerts(self) -> List[Alert]:
        """Return all currently active (firing) alerts."""
        return list(self._active_alerts.values())

    def get_alert_history(self) -> List[Alert]:
        """Return full alert history."""
        return list(self._alert_history)

    def clear_history(self) -> None:
        """Clear alert history (for testing)."""
        self._alert_history.clear()
        self._active_alerts.clear()
        self._pending_since.clear()


def create_default_alert_rules() -> List[AlertRule]:
     """
     Create the standard Orchestrator alert rules.

     Returns:
         List of AlertRule definitions.
     """
     return [
         AlertRule(
             name="HighErrorRate",
             description="Error rate exceeds 5% — investigate immediately",
             severity=AlertSeverity.CRITICAL,
             condition=lambda m: m.get("error_rate", 0) > 0.05,
             for_minutes=5,
             annotations={
                 "runbook_url": "docs/runbooks/high-error-rate.md",
                 "summary": "Orchestrator error rate is critically high",
             },
         ),
         AlertRule(
             name="LowQualityScore",
             description="Average quality score below 70",
             severity=AlertSeverity.WARNING,
             condition=lambda m: m.get("avg_quality_score", 100) < 70,
             for_minutes=10,
             annotations={
                 "runbook_url": "docs/runbooks/low-quality-score.md",
                 "summary": "Task quality scores are degraded",
             },
         ),
         AlertRule(
             name="QueueDepthHigh",
             description="Queue depth exceeds 100 tasks",
             severity=AlertSeverity.WARNING,
             condition=lambda m: m.get("queue_depth", 0) > 100,
             for_minutes=5,
             annotations={
                 "runbook_url": "docs/runbooks/queue-depth-high.md",
                 "summary": "Task queue is backing up",
             },
         ),
         AlertRule(
             name="QueueDepthCritical",
             description="Queue depth exceeds 500 tasks — system overloaded",
             severity=AlertSeverity.CRITICAL,
             condition=lambda m: m.get("queue_depth", 0) > 500,
             for_minutes=2,
             annotations={
                 "runbook_url": "docs/runbooks/queue-depth-high.md",
                 "summary": "Queue critically overloaded",
             },
         ),
         AlertRule(
             name="HighRetryRate",
             description="Task retry rate exceeds 20%",
             severity=AlertSeverity.WARNING,
             condition=lambda m: m.get("retry_rate", 0) > 0.20,
             for_minutes=15,
             annotations={
                 "runbook_url": "docs/runbooks/high-retry-rate.md",
                 "summary": "Many tasks requiring retries",
             },
         ),
         AlertRule(
             name="SLOBreach",
             description="One or more SLOs are breached",
             severity=AlertSeverity.PAGE,
             condition=lambda m: m.get("slo_breached", False),
             for_minutes=0,
             annotations={
                 "runbook_url": "docs/runbooks/slo-breach.md",
                 "summary": "SLO breach detected — immediate action required",
             },
         ),
         # ===== Token Cost Anomaly Alerts =====
         AlertRule(
             name="TokenCostDailyHigh",
             description="Daily token cost exceeds $100",
             severity=AlertSeverity.WARNING,
             condition=lambda m: m.get("daily_token_cost", 0) > 100,
             for_minutes=5,
             annotations={
                 "runbook_url": "docs/runbooks/token-cost-high.md",
                 "summary": "Daily token cost is high",
                 "impact": "Cost control",
             },
         ),
         AlertRule(
             name="TokenCostPerTaskHigh",
             description="Cost per task exceeds $5",
             severity=AlertSeverity.WARNING,
             condition=lambda m: m.get("cost_per_task", 0) > 5.0,
             for_minutes=10,
             annotations={
                 "runbook_url": "docs/runbooks/token-cost-high.md",
                 "summary": "Average cost per task is high",
                 "impact": "Cost optimization",
             },
         ),
         AlertRule(
             name="TokenCacheHitRateLow",
             description="Cache hit rate below 50%",
             severity=AlertSeverity.WARNING,
             condition=lambda m: m.get("cache_hit_rate", 1.0) < 0.5,
             for_minutes=15,
             annotations={
                 "runbook_url": "docs/runbooks/cache-hit-rate-low.md",
                 "summary": "Token cache effectiveness is degraded",
                 "impact": "Cost and performance",
             },
         ),
         AlertRule(
             name="TokenUsageAnomaly",
             description="Token usage anomaly detected (> 2.5σ from mean)",
             severity=AlertSeverity.WARNING,
             condition=lambda m: m.get("token_usage_sigma", 0) > 2.5,
             for_minutes=5,
             annotations={
                 "runbook_url": "docs/runbooks/token-usage-anomaly.md",
                 "summary": "Unusual token usage pattern detected",
                 "impact": "Cost and performance",
             },
         ),
     ]
