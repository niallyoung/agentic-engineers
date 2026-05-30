"""
Budget management and enforcement for Copilot harness.

Provides real-time budget monitoring, alert thresholds, hard spend limits,
cost forecasting, and savings recommendations.

Author: Engineer
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import statistics

from src.copilot.cost_tracker import CostTracker, TaskCost, TokenUsage


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    BLOCKED = "blocked"


@dataclass
class BudgetAlert:
    """Represents a budget alert."""
    
    level: AlertLevel
    threshold_percent: int
    current_cost: float
    budget_limit: float
    message: str
    timestamp: datetime = field(default_factory=datetime.now)


class BudgetManager:
    """
    Manages budgets, tracks spending against limits, and enforces hard blocks.
    
    Features:
    - Real-time budget monitoring with configurable thresholds
    - Alert levels at 50%, 75%, 90%, and 100% of budget
    - Hard block enforcement at budget limit
    - Cost forecasting based on historical spending patterns
    - Savings analysis and recommendations
    """
    
    # Default alert thresholds (percent of budget)
    DEFAULT_THRESHOLDS = {
        50: AlertLevel.INFO,
        75: AlertLevel.WARNING,
        90: AlertLevel.CRITICAL,
        100: AlertLevel.BLOCKED,
    }
    
    # Forecast window (hours to look back for trend analysis)
    FORECAST_WINDOW_HOURS = 24
    FORECAST_SAMPLES = 20
    
    def __init__(
        self,
        session_budget_usd: float,
        max_cost_per_task_usd: Optional[float] = None,
        alert_thresholds: Optional[Dict[int, AlertLevel]] = None,
    ):
        """
        Initialize budget manager.
        
        Args:
            session_budget_usd: Total budget for the session in USD
            max_cost_per_task_usd: Maximum cost allowed per individual task
            alert_thresholds: Custom alert threshold mapping (percent -> AlertLevel)
        """
        if session_budget_usd <= 0:
            raise ValueError("Session budget must be positive")
        
        self.session_budget_usd = session_budget_usd
        self.max_cost_per_task_usd = max_cost_per_task_usd
        self.alert_thresholds = alert_thresholds or self.DEFAULT_THRESHOLDS
        
        self.alerts: List[BudgetAlert] = []
        self.blocked_tasks: List[str] = []
        self.cost_history: deque = deque(maxlen=self.FORECAST_SAMPLES)
        self.last_alert_threshold = 0
    
    def check_budget_available(
        self,
        cost_tracker: CostTracker,
        estimated_cost_usd: float,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a task can proceed within budget.
        
        Args:
            cost_tracker: Session cost tracker
            estimated_cost_usd: Estimated cost of the upcoming task
            
        Returns:
            Tuple of (can_proceed, reason_if_blocked)
        """
        current_cost = cost_tracker.get_session_total_cost()
        projected_cost = current_cost + estimated_cost_usd
        
        # Check session budget limit
        if projected_cost > self.session_budget_usd:
            reason = (
                f"Session budget exceeded: "
                f"${current_cost:.2f} + ${estimated_cost_usd:.2f} "
                f"would exceed ${self.session_budget_usd:.2f} budget"
            )
            return False, reason
        
        # Check per-task limit if set
        if self.max_cost_per_task_usd and estimated_cost_usd > self.max_cost_per_task_usd:
            reason = (
                f"Task cost exceeds per-task limit: "
                f"${estimated_cost_usd:.2f} > ${self.max_cost_per_task_usd:.2f}"
            )
            return False, reason
        
        return True, None
    
    def record_task_and_check_alerts(
        self,
        cost_tracker: CostTracker,
        task_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_tokens: int = 0,
        duration_ms: int = 0,
        metadata: Optional[Dict] = None,
    ) -> Optional[BudgetAlert]:
        """
        Record a task cost and check for budget alerts.
        
        Args:
            cost_tracker: Session cost tracker
            task_id: Task identifier
            model: Model used
            input_tokens: Input token count
            output_tokens: Output token count
            cached_tokens: Cached token count
            duration_ms: Task duration
            metadata: Optional metadata
            
        Returns:
            BudgetAlert if a threshold was crossed, None otherwise
        """
        # Record the task
        task_cost = cost_tracker.record_task(
            task_id=task_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            duration_ms=duration_ms,
            metadata=metadata,
        )
        
        # Add to history for forecasting
        self.cost_history.append(task_cost.cost_usd)
        
        # Check for alerts
        alert = self._check_thresholds(cost_tracker)
        
        if alert:
            self.alerts.append(alert)
        
        return alert
    
    def _check_thresholds(self, cost_tracker: CostTracker) -> Optional[BudgetAlert]:
        """Check if spending has crossed any alert thresholds."""
        current_cost = cost_tracker.get_session_total_cost()
        percent_used = (current_cost / self.session_budget_usd) * 100
        
        # Find the highest threshold that has been crossed
        for threshold in sorted(self.alert_thresholds.keys(), reverse=True):
            if percent_used >= threshold and threshold > self.last_alert_threshold:
                self.last_alert_threshold = threshold
                level = self.alert_thresholds[threshold]
                
                message = (
                    f"Budget alert at {threshold}%: "
                    f"${current_cost:.2f} of ${self.session_budget_usd:.2f} spent"
                )
                
                alert = BudgetAlert(
                    level=level,
                    threshold_percent=threshold,
                    current_cost=current_cost,
                    budget_limit=self.session_budget_usd,
                    message=message,
                )
                
                return alert
        
        return None
    
    def block_task(self, task_id: str, reason: str) -> None:
        """Record a blocked task."""
        self.blocked_tasks.append(task_id)
    
    def get_alerts(
        self,
        level: Optional[AlertLevel] = None,
        limit: Optional[int] = None,
    ) -> List[BudgetAlert]:
        """
        Get alerts, optionally filtered by level.
        
        Args:
            level: Optional alert level to filter by
            limit: Optional limit on number of alerts returned
            
        Returns:
            List of alerts
        """
        alerts = self.alerts
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        if limit:
            alerts = alerts[-limit:]
        
        return alerts
    
    def get_budget_status(self, cost_tracker: CostTracker) -> Dict:
        """
        Get comprehensive budget status.
        
        Args:
            cost_tracker: Session cost tracker
            
        Returns:
            Dictionary with budget status information
        """
        current_cost = cost_tracker.get_session_total_cost()
        remaining = self.session_budget_usd - current_cost
        percent_used = (current_cost / self.session_budget_usd) * 100
        
        return {
            "session_budget_usd": self.session_budget_usd,
            "current_cost_usd": current_cost,
            "remaining_budget_usd": remaining,
            "percent_used": percent_used,
            "total_tasks": len(cost_tracker.tasks),
            "average_cost_per_task": cost_tracker.get_average_cost_per_task(),
            "blocked_tasks": len(self.blocked_tasks),
            "alert_count": len(self.alerts),
            "status": self._get_status_string(percent_used),
        }
    
    def _get_status_string(self, percent_used: float) -> str:
        """Get human-readable status string."""
        if percent_used >= 100:
            return "BLOCKED"
        elif percent_used >= 90:
            return "CRITICAL"
        elif percent_used >= 75:
            return "WARNING"
        elif percent_used >= 50:
            return "CAUTION"
        else:
            return "OK"
    
    def forecast_remaining_budget(self, cost_tracker: CostTracker) -> Dict:
        """
        Forecast budget consumption based on historical trends.
        
        Args:
            cost_tracker: Session cost tracker
            
        Returns:
            Dictionary with forecast information
        """
        if not self.cost_history or len(self.cost_history) < 2:
            return {
                "forecast_available": False,
                "reason": "Insufficient history for forecast",
                "estimated_tasks_remaining": None,
                "estimated_time_to_exhaustion": None,
            }
        
        # Calculate average cost and variance
        avg_cost = statistics.mean(self.cost_history)
        variance = statistics.variance(self.cost_history) if len(self.cost_history) > 1 else 0
        stdev = statistics.stdev(self.cost_history) if len(self.cost_history) > 1 else 0
        
        current_cost = cost_tracker.get_session_total_cost()
        remaining = self.session_budget_usd - current_cost
        
        # Conservative estimate (use mean + 1 stdev)
        conservative_cost = avg_cost + stdev if stdev > 0 else avg_cost
        
        if conservative_cost > 0:
            tasks_remaining = int(remaining / conservative_cost)
        else:
            tasks_remaining = None
        
        # Estimate time based on task count and average execution time
        task_times = [t.duration_ms for t in cost_tracker.tasks if t.duration_ms > 0]
        if task_times:
            avg_time_ms = statistics.mean(task_times)
            time_to_exhaustion_ms = (tasks_remaining * avg_time_ms) if tasks_remaining else None
        else:
            time_to_exhaustion_ms = None
        
        return {
            "forecast_available": True,
            "average_cost_per_task": avg_cost,
            "conservative_cost_per_task": conservative_cost,
            "cost_stdev": stdev,
            "remaining_budget_usd": remaining,
            "estimated_tasks_remaining": tasks_remaining,
            "estimated_time_to_exhaustion_ms": time_to_exhaustion_ms,
        }
    
    def get_savings_recommendations(self, cost_tracker: CostTracker) -> List[Dict]:
        """
        Analyze spending patterns and recommend cost optimizations.
        
        Args:
            cost_tracker: Session cost tracker
            
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        # Analyze cost by model
        cost_by_model = cost_tracker.get_cost_by_model()
        total_cost = cost_tracker.get_session_total_cost()
        
        if total_cost == 0:
            return recommendations
        
        # Check for expensive model overuse
        for model, data in cost_by_model.items():
            model_pct = (data["cost"] / total_cost) * 100
            
            if model_pct > 40 and model.startswith("claude-opus"):
                recommendations.append({
                    "type": "model_downgrade",
                    "severity": "high",
                    "model": model,
                    "current_cost": data["cost"],
                    "percent_of_total": model_pct,
                    "suggestion": f"Consider routing more tasks to cheaper models. {model} comprises {model_pct:.1f}% of costs.",
                    "potential_savings": data["cost"] * 0.7,  # Assuming 70% cost savings
                })
        
        # Check cache effectiveness
        total_tokens = cost_tracker.get_session_total_tokens()
        cache_ratio = total_tokens.cached_tokens / total_tokens.total_tokens if total_tokens.total_tokens > 0 else 0
        
        if cache_ratio < 0.05:
            recommendations.append({
                "type": "cache_optimization",
                "severity": "medium",
                "current_cache_ratio": cache_ratio,
                "suggestion": "Enable prompt caching for frequently-used context. Current cache ratio is very low.",
            })
        
        # Check for outlier expensive tasks
        avg_cost = cost_tracker.get_average_cost_per_task()
        most_expensive = cost_tracker.get_most_expensive_tasks(3)
        
        for task in most_expensive:
            if task.cost_usd > avg_cost * 3:
                recommendations.append({
                    "type": "task_optimization",
                    "severity": "medium",
                    "task_id": task.task_id,
                    "cost": task.cost_usd,
                    "average_cost": avg_cost,
                    "suggestion": f"Task {task.task_id} cost ${task.cost_usd:.3f} ({task.cost_usd/avg_cost:.1f}x average). Consider breaking into smaller tasks.",
                })
        
        return recommendations
    
    def get_report(self, cost_tracker: CostTracker) -> str:
        """Generate a formatted budget report."""
        status = self.get_budget_status(cost_tracker)
        forecast = self.forecast_remaining_budget(cost_tracker)
        recommendations = self.get_savings_recommendations(cost_tracker)
        
        report = []
        report.append("=" * 70)
        report.append("BUDGET REPORT")
        report.append("=" * 70)
        report.append("")
        
        # Budget Status
        report.append("BUDGET STATUS")
        report.append("-" * 70)
        report.append(f"Total Budget:        ${status['session_budget_usd']:>8.2f}")
        report.append(f"Current Spending:    ${status['current_cost_usd']:>8.2f}")
        report.append(f"Remaining Budget:    ${status['remaining_budget_usd']:>8.2f}")
        report.append(f"Percent Used:        {status['percent_used']:>8.1f}%")
        report.append(f"Status:              {status['status']:>8}")
        report.append("")
        
        # Task Statistics
        report.append("TASK STATISTICS")
        report.append("-" * 70)
        report.append(f"Total Tasks:         {status['total_tasks']:>8}")
        report.append(f"Avg Cost per Task:   ${status['average_cost_per_task']:>8.3f}")
        report.append(f"Blocked Tasks:       {status['blocked_tasks']:>8}")
        report.append(f"Alerts Triggered:    {status['alert_count']:>8}")
        report.append("")
        
        # Forecast
        if forecast["forecast_available"]:
            report.append("FORECAST")
            report.append("-" * 70)
            report.append(f"Avg Cost (historical): ${forecast['average_cost_per_task']:>8.3f}")
            report.append(f"Conservative Estimate: ${forecast['conservative_cost_per_task']:>8.3f}")
            report.append(f"Tasks Remaining Est.:  {forecast['estimated_tasks_remaining']:>8}")
            if forecast['estimated_time_to_exhaustion_ms']:
                hours = forecast['estimated_time_to_exhaustion_ms'] / (1000 * 60 * 60)
                report.append(f"Time to Exhaustion:    {hours:>8.1f} hours")
            report.append("")
        
        # Recommendations
        if recommendations:
            report.append("RECOMMENDATIONS")
            report.append("-" * 70)
            for rec in recommendations:
                report.append(f"[{rec['severity'].upper()}] {rec['suggestion']}")
            report.append("")
        
        report.append("=" * 70)
        
        return "\n".join(report)
