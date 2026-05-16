"""
SLO Tracker — Service Level Objective definition and tracking.

Defines SLOs for the Orchestrator and tracks compliance over time.

SLOs tracked:
    - Task success rate (>= 95%)
    - P95 task latency (<= 300s)
    - Quality score (>= 85 avg)
    - Queue processing time (<= 60s)
    - Error rate (<= 1%)

Usage:
    tracker = SLOTracker()
    tracker.define_slo(SLO(
        name="task_success_rate",
        description="95% of tasks complete successfully",
        target=0.95,
        window_minutes=60,
        metric_fn=lambda: completed / total,
    ))
    tracker.record_event("task_success_rate", success=True)
    status = tracker.evaluate("task_success_rate")
"""

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple


class SLOStatus(Enum):
    """SLO compliance status."""
    MET = "met"
    AT_RISK = "at_risk"     # Within 5% of target
    BREACHED = "breached"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class SLOEvent:
    """A single event contributing to an SLO measurement."""
    timestamp: float
    value: float  # 1.0 = success/good, 0.0 = failure/bad, or numeric value
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class SLO:
    """
    Service Level Objective definition.

    Attributes:
        name: Unique SLO identifier
        description: Human-readable description
        target: Target value (e.g. 0.95 for 95% success rate)
        window_minutes: Rolling window for evaluation
        comparison: "gte" (>=) or "lte" (<=)
        at_risk_threshold: How close to target before "at_risk" (default 5%)
    """
    name: str
    description: str
    target: float
    window_minutes: int = 60
    comparison: str = "gte"  # "gte" or "lte"
    at_risk_threshold: float = 0.05  # 5% margin


@dataclass
class SLOEvaluation:
    """Result of evaluating an SLO."""
    slo_name: str
    status: SLOStatus
    current_value: Optional[float]
    target: float
    event_count: int
    window_minutes: int
    timestamp: float = field(default_factory=time.time)
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slo_name": self.slo_name,
            "status": self.status.value,
            "current_value": self.current_value,
            "target": self.target,
            "event_count": self.event_count,
            "window_minutes": self.window_minutes,
            "timestamp": self.timestamp,
            "message": self.message,
        }


class SLOTracker:
    """
    Track SLO compliance using rolling windows of events.
    """

    MIN_EVENTS_FOR_EVALUATION = 5

    def __init__(self):
        self._slos: Dict[str, SLO] = {}
        self._events: Dict[str, Deque[SLOEvent]] = {}

    def define_slo(self, slo: SLO) -> None:
        """Register an SLO definition."""
        self._slos[slo.name] = slo
        if slo.name not in self._events:
            self._events[slo.name] = deque()

    def record_event(self, slo_name: str, value: float, **labels) -> None:
        """
        Record an event for an SLO.

        Args:
            slo_name: Name of the SLO
            value: Metric value (1.0=good, 0.0=bad, or numeric)
            **labels: Optional label key-value pairs
        """
        if slo_name not in self._slos:
            raise KeyError(f"SLO '{slo_name}' not defined")

        event = SLOEvent(
            timestamp=time.time(),
            value=value,
            labels=labels,
        )
        self._events[slo_name].append(event)

    def _get_window_events(self, slo_name: str) -> List[SLOEvent]:
        """Get events within the SLO's rolling window."""
        slo = self._slos[slo_name]
        cutoff = time.time() - (slo.window_minutes * 60)
        events = self._events[slo_name]

        # Prune old events
        while events and events[0].timestamp < cutoff:
            events.popleft()

        return list(events)

    def evaluate(self, slo_name: str) -> SLOEvaluation:
        """
        Evaluate current SLO compliance.

        Returns:
            SLOEvaluation with status and current value.
        """
        if slo_name not in self._slos:
            raise KeyError(f"SLO '{slo_name}' not defined")

        slo = self._slos[slo_name]
        events = self._get_window_events(slo_name)

        if len(events) < self.MIN_EVENTS_FOR_EVALUATION:
            return SLOEvaluation(
                slo_name=slo_name,
                status=SLOStatus.INSUFFICIENT_DATA,
                current_value=None,
                target=slo.target,
                event_count=len(events),
                window_minutes=slo.window_minutes,
                message=f"Need {self.MIN_EVENTS_FOR_EVALUATION} events, have {len(events)}",
            )

        current = sum(e.value for e in events) / len(events)

        # Determine compliance
        if slo.comparison == "gte":
            met = current >= slo.target
            at_risk = current >= (slo.target - slo.at_risk_threshold) and not met
        else:  # lte
            met = current <= slo.target
            at_risk = current <= (slo.target + slo.at_risk_threshold) and not met

        if met:
            status = SLOStatus.MET
            message = f"SLO met: {current:.3f} {'≥' if slo.comparison == 'gte' else '≤'} {slo.target}"
        elif at_risk:
            status = SLOStatus.AT_RISK
            message = f"SLO at risk: {current:.3f} (target: {slo.target})"
        else:
            status = SLOStatus.BREACHED
            message = f"SLO BREACHED: {current:.3f} (target: {slo.target})"

        return SLOEvaluation(
            slo_name=slo_name,
            status=status,
            current_value=current,
            target=slo.target,
            event_count=len(events),
            window_minutes=slo.window_minutes,
            message=message,
        )

    def evaluate_all(self) -> Dict[str, SLOEvaluation]:
        """Evaluate all registered SLOs."""
        return {name: self.evaluate(name) for name in self._slos}

    def get_slo_names(self) -> List[str]:
        """Return list of registered SLO names."""
        return list(self._slos.keys())


def create_default_slos() -> List[SLO]:
    """
    Create the standard set of Orchestrator SLOs.

    Returns:
        List of SLO definitions.
    """
    return [
        SLO(
            name="task_success_rate",
            description="95% of tasks complete successfully within 1 hour",
            target=0.95,
            window_minutes=60,
            comparison="gte",
        ),
        SLO(
            name="quality_score_avg",
            description="Average task quality score >= 85",
            target=0.85,
            window_minutes=60,
            comparison="gte",
        ),
        SLO(
            name="error_rate",
            description="Error rate <= 1% over 1 hour",
            target=0.01,
            window_minutes=60,
            comparison="lte",
        ),
        SLO(
            name="routing_success_rate",
            description="99% of routing decisions succeed",
            target=0.99,
            window_minutes=30,
            comparison="gte",
        ),
        SLO(
            name="validation_pass_rate",
            description="95% of DELEGATE/HANDBACK validations pass",
            target=0.95,
            window_minutes=60,
            comparison="gte",
        ),
    ]
