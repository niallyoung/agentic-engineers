"""
regression_detector.py — Performance Regression Detection & Alerting (COST-003)

Tracks model performance metrics over time and detects regressions:
- Cost increases, quality drops, latency degradation
- Configurable thresholds (default 10%)
- Alert severity levels: info, warning, critical (>25%)
- Historical baseline tracking and management

Design principles:
- In-memory tracking with configurable retention (default 30 days)
- Strict regression definition: >threshold degradation from baseline
- Alert severity: warning (10-25%), critical (>25%)
- Baseline updates for acknowledged regressions

Usage:
    from src.agents.cost_management.regression_detector import RegressionDetector

    detector = RegressionDetector(threshold_pct=10)

    # Record metric
    detector.record_performance("code-review", "claude-sonnet-4.5", 0.05, 0.95, 1.2)

    # Detect regressions
    regressions = detector.detect_regressions(task_type="code-review")

    # Generate report
    report = detector.generate_report()

    # Acknowledge and update baseline
    detector.update_baseline("code-review", "claude-sonnet-4.5")
"""
from __future__ import absolute_import, annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class RegressionAlert:
    """Single regression alert."""
    model: str
    task_type: str
    metric_type: str  # "cost", "quality", or "latency"
    baseline_value: float
    current_value: float
    degradation_pct: float
    severity: str  # "info", "warning", "critical"
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RegressionReport:
    """Report of all detected regressions."""
    alerts: List[RegressionAlert] = field(default_factory=list)
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    total_tracked: int = 0
    report_time: datetime = field(default_factory=datetime.now)


class RegressionDetector:
    """
    Performance regression detector tracking cost, quality, and latency metrics.
    
    Detects degradation relative to baseline, with configurable threshold
    and severity levels.
    """
    
    def __init__(
        self,
        threshold_pct: float = 10.0,
        history_window_days: int = 30,
    ) -> None:
        """
        Initialize RegressionDetector.

        Args:
            threshold_pct: Degradation threshold for regression (default 10%)
            history_window_days: Days of history to retain (default 30)
        """
        self.threshold_pct = threshold_pct
        self.history_window_days = history_window_days

        # Storage: {(task_type, model): {"cost": [...], "quality": [...], ...}}
        self._history: Dict[Tuple[str, str], Dict[str, List[Tuple[float, datetime]]]] = {}

        # Baseline: {(task_type, model): {"cost": float, ...}}
        self._baselines: Dict[Tuple[str, str], Dict[str, float]] = {}
    
    def record_performance(
        self,
        task_type: str,
        model: str,
        cost: float,
        quality: float,
        latency_sec: float,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Record performance metrics for a model on a task type.
        
        Args:
            task_type: Task category (e.g., "code-review", "general")
            model: Model name (e.g., "claude-sonnet-4.5")
            cost: Cost in dollars
            quality: Quality score 0-1
            latency_sec: Latency in seconds
            timestamp: Optional timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        key = (task_type, model)
        
        # Initialize history if needed
        if key not in self._history:
            self._history[key] = {
                "cost": [],
                "quality": [],
                "latency": [],
            }
        
        # Record metrics
        self._history[key]["cost"].append((cost, timestamp))
        self._history[key]["quality"].append((quality, timestamp))
        self._history[key]["latency"].append((latency_sec, timestamp))
        
        # Initialize baseline if needed (use first recorded value)
        if key not in self._baselines:
            self._baselines[key] = {
                "cost": cost,
                "quality": quality,
                "latency": latency_sec,
            }
    
    def _cleanup_old_entries(self) -> None:
        """Remove entries older than history_window_days."""
        cutoff = datetime.now() - timedelta(days=self.history_window_days)
        
        for key in self._history:
            for metric in ["cost", "quality", "latency"]:
                self._history[key][metric] = [
                    (value, ts) for value, ts in self._history[key][metric]
                    if ts >= cutoff
                ]
    
    def detect_regressions(
        self,
        task_type: Optional[str] = None,
        model: Optional[str] = None,
        metric_type: Optional[str] = None,
    ) -> List[RegressionAlert]:
        """
        Detect regressions for matching (task_type, model, metric_type).

        Args:
            task_type: Optional task type filter
            model: Optional model filter
            metric_type: Optional metric type filter ("cost", "quality", "latency")

        Returns:
            List of RegressionAlert objects
        """
        self._cleanup_old_entries()

        alerts: List[RegressionAlert] = []

        for (task, mdl), metrics in self._history.items():
            # Filter by task_type/model if specified
            if task_type and task != task_type:
                continue
            if model and mdl != model:
                continue

            baseline = self._baselines.get((task, mdl), {})
            if not baseline:
                continue

            # Check each metric type
            for metric in ["cost", "quality", "latency"]:
                if metric_type and metric != metric_type:
                    continue

                if not metrics[metric]:
                    continue

                # Get recent value (average of last 5 or all if fewer)
                recent_values = [v for v, _ in metrics[metric][-5:]]
                if not recent_values:
                    continue

                current = sum(recent_values) / len(recent_values)
                baseline_val = baseline.get(metric, 0.0)

                if baseline_val == 0:
                    continue

                # Detect regression
                if metric == "quality":
                    # For quality, lower is worse
                    degradation = ((baseline_val - current) / baseline_val) * 100.0
                else:
                    # For cost/latency, higher is worse
                    degradation = ((current - baseline_val) / baseline_val) * 100.0

                if degradation > self.threshold_pct:
                    # Determine severity
                    if degradation > 25.0:
                        severity = "critical"
                    else:
                        severity = "warning"

                    alerts.append(
                        RegressionAlert(
                            model=mdl,
                            task_type=task,
                            metric_type=metric,
                            baseline_value=baseline_val,
                            current_value=current,
                            degradation_pct=degradation,
                            severity=severity,
                        )
                    )

        return alerts
    
    def generate_report(self) -> RegressionReport:
        """
        Generate comprehensive regression report.
        
        Returns:
            RegressionReport with all alerts and summary statistics
        """
        alerts = self.detect_regressions()
        
        critical = sum(1 for a in alerts if a.severity == "critical")
        warning = sum(1 for a in alerts if a.severity == "warning")
        info = sum(1 for a in alerts if a.severity == "info")
        
        return RegressionReport(
            alerts=alerts,
            critical_count=critical,
            warning_count=warning,
            info_count=info,
            total_tracked=len(self._baselines),
        )
    
    def update_baseline(
        self,
        task_type: str,
        model: str,
    ) -> None:
        """
        Update baseline to current performance (acknowledge regression).

        Args:
            task_type: Task type
            model: Model name
        """
        key = (task_type, model)

        if key not in self._history:
            logger.warning("No history for %s", key)
            return

        metrics = self._history[key]

        # Use average of recent values
        new_baseline = {}
        for metric in ["cost", "quality", "latency"]:
            recent = [v for v, _ in metrics[metric][-5:]]
            if recent:
                new_baseline[metric] = sum(recent) / len(recent)

        if new_baseline:
            self._baselines[key] = new_baseline
            logger.info("Updated baseline for %s: %s", key, new_baseline)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for all tracked metrics.

        Returns:
            Dict with summary stats
        """
        summary: Dict[str, Any] = {
            "total_task_model_pairs": len(self._baselines),
            "tracked_tasks": set(),
            "tracked_models": set(),
        }

        for task_type, model_name in self._baselines:
            summary["tracked_tasks"].add(task_type)
            summary["tracked_models"].add(model_name)

        summary["tracked_tasks"] = sorted(list(summary["tracked_tasks"]))
        summary["tracked_models"] = sorted(list(summary["tracked_models"]))

        return summary
