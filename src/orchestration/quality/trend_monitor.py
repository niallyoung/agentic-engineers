"""
Trend Monitor — Track quality metrics over time and detect trends.

Tracks quality scores per task type, computes moving averages (7-day, 30-day),
detects trend direction (improving / degrading / stable), and emits alerts
when trends change significantly.

Usage::

    monitor = TrendMonitor()
    monitor.record(task_type="code", score=92.0)
    monitor.record(task_type="code", score=88.0)
    report = monitor.trend_report("code")
    print(report.direction)  # TrendDirection.DEGRADING
"""

from __future__ import annotations

import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class TrendDirection(str, Enum):
    IMPROVING = "improving"
    DEGRADING = "degrading"
    STABLE = "stable"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class QualityDataPoint:
    """A single quality measurement."""
    task_type: str
    score: float          # 0-100
    timestamp: float = field(default_factory=time.time)
    task_id: Optional[str] = None
    role: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 100.0:
            raise ValueError(f"score must be 0-100, got {self.score}")


@dataclass
class TrendReport:
    """Summary of quality trend for a task type."""
    task_type: str
    direction: TrendDirection
    current_avg: float          # most recent 7-day average
    baseline_avg: float         # 30-day average (or all-time if <30 days)
    delta: float                # current_avg - baseline_avg
    sample_count: int
    seven_day_avg: Optional[float]
    thirty_day_avg: Optional[float]
    min_score: float
    max_score: float
    std_dev: float
    alert: Optional[str] = None


# Thresholds for trend classification
_IMPROVING_DELTA = 2.0   # +2 points = improving
_DEGRADING_DELTA = -2.0  # -2 points = degrading
_MIN_SAMPLES_FOR_TREND = 3


class TrendMonitor:
    """
    Tracks quality scores over time and detects trends.

    Thread-safety: not thread-safe; wrap with a lock if used concurrently.
    """

    def __init__(self) -> None:
        # task_type -> list of data points (chronological)
        self._data: Dict[str, List[QualityDataPoint]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(self, task_type: str, score: float, **kwargs) -> QualityDataPoint:
        """Record a quality score for a task type."""
        dp = QualityDataPoint(task_type=task_type, score=score, **kwargs)
        self._data[task_type].append(dp)
        return dp

    def record_datapoint(self, dp: QualityDataPoint) -> None:
        """Record a pre-built QualityDataPoint."""
        self._data[dp.task_type].append(dp)

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def data_for(self, task_type: str) -> List[QualityDataPoint]:
        """Return all data points for a task type (chronological)."""
        return list(self._data.get(task_type, []))

    def task_types(self) -> List[str]:
        """Return all known task types."""
        return list(self._data.keys())

    def _points_in_window(
        self, task_type: str, days: int
    ) -> List[QualityDataPoint]:
        cutoff = time.time() - days * 86400
        return [dp for dp in self._data.get(task_type, []) if dp.timestamp >= cutoff]

    def moving_average(self, task_type: str, days: int) -> Optional[float]:
        """Return moving average over the last *days* days, or None if no data."""
        points = self._points_in_window(task_type, days)
        if not points:
            return None
        return statistics.mean(p.score for p in points)

    # ------------------------------------------------------------------
    # Trend analysis
    # ------------------------------------------------------------------

    def trend_report(self, task_type: str) -> TrendReport:
        """Generate a trend report for a task type."""
        all_points = self._data.get(task_type, [])
        if not all_points:
            return TrendReport(
                task_type=task_type,
                direction=TrendDirection.INSUFFICIENT_DATA,
                current_avg=0.0,
                baseline_avg=0.0,
                delta=0.0,
                sample_count=0,
                seven_day_avg=None,
                thirty_day_avg=None,
                min_score=0.0,
                max_score=0.0,
                std_dev=0.0,
            )

        scores = [dp.score for dp in all_points]
        seven_day_avg = self.moving_average(task_type, 7)
        thirty_day_avg = self.moving_average(task_type, 30)

        # current = 7-day avg (or most recent half of all data)
        if seven_day_avg is not None:
            current_avg = seven_day_avg
        else:
            # Use most recent half of data points as "current"
            half = max(1, len(all_points) // 2)
            current_avg = statistics.mean(p.score for p in all_points[-half:])

        # baseline = all-time average (includes historical data outside windows)
        # This allows detecting improvement/degradation vs historical baseline
        baseline_avg = statistics.mean(scores)

        delta = current_avg - baseline_avg

        if len(all_points) < _MIN_SAMPLES_FOR_TREND:
            direction = TrendDirection.INSUFFICIENT_DATA
        elif delta >= _IMPROVING_DELTA:
            direction = TrendDirection.IMPROVING
        elif delta <= _DEGRADING_DELTA:
            direction = TrendDirection.DEGRADING
        else:
            direction = TrendDirection.STABLE

        std_dev = statistics.stdev(scores) if len(scores) > 1 else 0.0

        alert = None
        if direction == TrendDirection.DEGRADING:
            alert = (
                f"Quality degrading for '{task_type}': "
                f"7-day avg {current_avg:.1f} vs 30-day avg {baseline_avg:.1f} "
                f"(delta {delta:+.1f})"
            )

        return TrendReport(
            task_type=task_type,
            direction=direction,
            current_avg=current_avg,
            baseline_avg=baseline_avg,
            delta=delta,
            sample_count=len(all_points),
            seven_day_avg=seven_day_avg,
            thirty_day_avg=thirty_day_avg,
            min_score=min(scores),
            max_score=max(scores),
            std_dev=std_dev,
            alert=alert,
        )

    def all_trend_reports(self) -> Dict[str, TrendReport]:
        """Return trend reports for all known task types."""
        return {tt: self.trend_report(tt) for tt in self._data}

    def degrading_task_types(self) -> List[str]:
        """Return task types with degrading quality trends."""
        return [
            tt
            for tt, report in self.all_trend_reports().items()
            if report.direction == TrendDirection.DEGRADING
        ]

    def improving_task_types(self) -> List[str]:
        """Return task types with improving quality trends."""
        return [
            tt
            for tt, report in self.all_trend_reports().items()
            if report.direction == TrendDirection.IMPROVING
        ]
