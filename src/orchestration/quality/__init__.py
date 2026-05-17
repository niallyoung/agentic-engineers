"""
Quality Thresholds & Feedback Cycles — Phase I

Modules:
  - trend_monitor: Track quality metrics over time, detect trends
  - feedback_cycles: Automate quality feedback loops
  - threshold_enforcement: Enforce quality thresholds before task completion
  - quality_dashboard: Display quality metrics and trends
"""

from .trend_monitor import TrendMonitor, QualityDataPoint, TrendDirection
from .feedback_cycles import FeedbackCycleManager, CycleStage, FeedbackCycle
from .threshold_enforcement import ThresholdEnforcer, ThresholdViolation, EnforcementResult
from .quality_dashboard import QualityDashboard

__all__ = [
    "TrendMonitor",
    "QualityDataPoint",
    "TrendDirection",
    "FeedbackCycleManager",
    "CycleStage",
    "FeedbackCycle",
    "ThresholdEnforcer",
    "ThresholdViolation",
    "EnforcementResult",
    "QualityDashboard",
]
