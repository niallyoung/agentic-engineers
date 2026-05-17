"""
Feedback Cycle Manager — Automate quality feedback loops.

Defines the five-stage feedback cycle:
  1. task_execution   — task runs
  2. quality_assessment — QE scores the output
  3. feedback_collection — feedback gathered from QE HANDBACK
  4. trend_analysis   — TrendMonitor analyses the new data point
  5. routing_improvement — Model Engineer recommendation applied

Usage::

    manager = FeedbackCycleManager()
    cycle = manager.start_cycle(task_id="2026-05-17-fix-auth", task_type="code")
    manager.advance(cycle.cycle_id, CycleStage.QUALITY_ASSESSMENT, score=92.0)
    manager.advance(cycle.cycle_id, CycleStage.FEEDBACK_COLLECTION, feedback={"model": "haiku"})
    manager.advance(cycle.cycle_id, CycleStage.TREND_ANALYSIS)
    manager.advance(cycle.cycle_id, CycleStage.ROUTING_IMPROVEMENT, recommendation="keep_haiku")
    assert manager.get_cycle(cycle.cycle_id).is_complete
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class CycleStage(str, Enum):
    TASK_EXECUTION = "task_execution"
    QUALITY_ASSESSMENT = "quality_assessment"
    FEEDBACK_COLLECTION = "feedback_collection"
    TREND_ANALYSIS = "trend_analysis"
    ROUTING_IMPROVEMENT = "routing_improvement"
    COMPLETE = "complete"


_STAGE_ORDER = [
    CycleStage.TASK_EXECUTION,
    CycleStage.QUALITY_ASSESSMENT,
    CycleStage.FEEDBACK_COLLECTION,
    CycleStage.TREND_ANALYSIS,
    CycleStage.ROUTING_IMPROVEMENT,
    CycleStage.COMPLETE,
]


@dataclass
class StageRecord:
    stage: CycleStage
    entered_at: float
    completed_at: Optional[float] = None
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.completed_at is None:
            return None
        return self.completed_at - self.entered_at


@dataclass
class FeedbackCycle:
    """Tracks a single end-to-end feedback cycle for one task."""
    cycle_id: str
    task_id: str
    task_type: str
    created_at: float
    current_stage: CycleStage
    stage_history: List[StageRecord] = field(default_factory=list)
    quality_score: Optional[float] = None
    feedback: Dict[str, Any] = field(default_factory=dict)
    routing_recommendation: Optional[str] = None

    @property
    def is_complete(self) -> bool:
        return self.current_stage == CycleStage.COMPLETE

    @property
    def total_duration_seconds(self) -> Optional[float]:
        if not self.is_complete:
            return None
        return self.stage_history[-1].completed_at - self.created_at  # type: ignore[operator]

    def summary(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "current_stage": self.current_stage.value,
            "is_complete": self.is_complete,
            "quality_score": self.quality_score,
            "routing_recommendation": self.routing_recommendation,
            "stages_completed": len(self.stage_history),
            "total_duration_seconds": self.total_duration_seconds,
        }


class FeedbackCycleManager:
    """
    Manages feedback cycles for all tasks.

    Each task that completes triggers a feedback cycle that progresses
    through five stages, ultimately improving routing decisions.
    """

    def __init__(self) -> None:
        self._cycles: Dict[str, FeedbackCycle] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start_cycle(self, task_id: str, task_type: str) -> FeedbackCycle:
        """Start a new feedback cycle for a task."""
        cycle_id = str(uuid.uuid4())
        now = time.time()
        initial_stage = CycleStage.TASK_EXECUTION
        cycle = FeedbackCycle(
            cycle_id=cycle_id,
            task_id=task_id,
            task_type=task_type,
            created_at=now,
            current_stage=initial_stage,
            stage_history=[StageRecord(stage=initial_stage, entered_at=now)],
        )
        self._cycles[cycle_id] = cycle
        return cycle

    def advance(
        self,
        cycle_id: str,
        next_stage: CycleStage,
        **stage_data: Any,
    ) -> FeedbackCycle:
        """
        Advance a cycle to the next stage.

        Keyword arguments are stored as stage data and also applied to
        well-known cycle fields (score, feedback, recommendation).
        """
        cycle = self._get_or_raise(cycle_id)
        if cycle.is_complete:
            raise ValueError(f"Cycle {cycle_id} is already complete")

        # Validate ordering
        current_idx = _STAGE_ORDER.index(cycle.current_stage)
        next_idx = _STAGE_ORDER.index(next_stage)
        if next_idx != current_idx + 1:
            raise ValueError(
                f"Cannot advance from {cycle.current_stage} to {next_stage}; "
                f"expected {_STAGE_ORDER[current_idx + 1]}"
            )

        now = time.time()
        # Close current stage
        cycle.stage_history[-1].completed_at = now
        cycle.stage_history[-1].data = stage_data

        # Apply well-known fields
        if "score" in stage_data:
            cycle.quality_score = float(stage_data["score"])
        if "feedback" in stage_data:
            cycle.feedback.update(stage_data["feedback"])
        if "recommendation" in stage_data:
            cycle.routing_recommendation = stage_data["recommendation"]

        # Open next stage
        cycle.current_stage = next_stage
        cycle.stage_history.append(StageRecord(stage=next_stage, entered_at=now))

        if next_stage == CycleStage.COMPLETE:
            cycle.stage_history[-1].completed_at = now

        return cycle

    def complete_cycle(self, cycle_id: str) -> FeedbackCycle:
        """Shortcut to mark a cycle complete from ROUTING_IMPROVEMENT."""
        return self.advance(cycle_id, CycleStage.COMPLETE)

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_cycle(self, cycle_id: str) -> FeedbackCycle:
        return self._get_or_raise(cycle_id)

    def cycles_for_task(self, task_id: str) -> List[FeedbackCycle]:
        return [c for c in self._cycles.values() if c.task_id == task_id]

    def all_cycles(self) -> List[FeedbackCycle]:
        return list(self._cycles.values())

    def complete_cycles(self) -> List[FeedbackCycle]:
        return [c for c in self._cycles.values() if c.is_complete]

    def in_progress_cycles(self) -> List[FeedbackCycle]:
        return [c for c in self._cycles.values() if not c.is_complete]

    def cycle_metrics(self) -> Dict[str, Any]:
        """Aggregate metrics across all cycles."""
        all_c = self.all_cycles()
        complete = self.complete_cycles()
        scores = [c.quality_score for c in complete if c.quality_score is not None]
        durations = [c.total_duration_seconds for c in complete if c.total_duration_seconds]
        return {
            "total_cycles": len(all_c),
            "complete_cycles": len(complete),
            "in_progress_cycles": len(self.in_progress_cycles()),
            "avg_quality_score": sum(scores) / len(scores) if scores else None,
            "avg_duration_seconds": sum(durations) / len(durations) if durations else None,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_or_raise(self, cycle_id: str) -> FeedbackCycle:
        if cycle_id not in self._cycles:
            raise KeyError(f"No cycle with id {cycle_id!r}")
        return self._cycles[cycle_id]
