"""
Tests for FeedbackCycleManager — Quality feedback loop automation.

Coverage:
  - Cycle creation and lifecycle
  - Stage advancement (happy path)
  - Stage ordering enforcement
  - Well-known field extraction (score, feedback, recommendation)
  - Complete cycle detection
  - Duration tracking
  - Cycle querying helpers
  - Aggregate metrics
  - Error cases (unknown cycle, double-complete, wrong stage order)
"""

from __future__ import annotations

import pytest

from src.orchestration.quality.feedback_cycles import (
    FeedbackCycleManager,
    FeedbackCycle,
    CycleStage,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _full_cycle(manager: FeedbackCycleManager, task_id: str = "task-001", task_type: str = "code") -> FeedbackCycle:
    """Drive a cycle through all stages and return it."""
    cycle = manager.start_cycle(task_id=task_id, task_type=task_type)
    cid = cycle.cycle_id
    manager.advance(cid, CycleStage.QUALITY_ASSESSMENT, score=92.0)
    manager.advance(cid, CycleStage.FEEDBACK_COLLECTION, feedback={"model": "haiku"})
    manager.advance(cid, CycleStage.TREND_ANALYSIS)
    manager.advance(cid, CycleStage.ROUTING_IMPROVEMENT, recommendation="keep_haiku")
    manager.advance(cid, CycleStage.COMPLETE)
    return manager.get_cycle(cid)


# ---------------------------------------------------------------------------
# Cycle creation
# ---------------------------------------------------------------------------

class TestCycleCreation:
    def test_start_cycle_returns_cycle(self):
        manager = FeedbackCycleManager()
        cycle = manager.start_cycle(task_id="t1", task_type="code")
        assert isinstance(cycle, FeedbackCycle)

    def test_start_cycle_initial_stage(self):
        manager = FeedbackCycleManager()
        cycle = manager.start_cycle(task_id="t1", task_type="code")
        assert cycle.current_stage == CycleStage.TASK_EXECUTION

    def test_start_cycle_not_complete(self):
        manager = FeedbackCycleManager()
        cycle = manager.start_cycle(task_id="t1", task_type="code")
        assert not cycle.is_complete

    def test_start_cycle_unique_ids(self):
        manager = FeedbackCycleManager()
        c1 = manager.start_cycle("t1", "code")
        c2 = manager.start_cycle("t2", "code")
        assert c1.cycle_id != c2.cycle_id

    def test_start_cycle_stores_task_info(self):
        manager = FeedbackCycleManager()
        cycle = manager.start_cycle(task_id="my-task", task_type="security")
        assert cycle.task_id == "my-task"
        assert cycle.task_type == "security"


# ---------------------------------------------------------------------------
# Stage advancement
# ---------------------------------------------------------------------------

class TestStageAdvancement:
    def test_advance_to_quality_assessment(self):
        manager = FeedbackCycleManager()
        cycle = manager.start_cycle("t1", "code")
        manager.advance(cycle.cycle_id, CycleStage.QUALITY_ASSESSMENT, score=88.0)
        updated = manager.get_cycle(cycle.cycle_id)
        assert updated.current_stage == CycleStage.QUALITY_ASSESSMENT

    def test_advance_sets_quality_score(self):
        manager = FeedbackCycleManager()
        cycle = manager.start_cycle("t1", "code")
        manager.advance(cycle.cycle_id, CycleStage.QUALITY_ASSESSMENT, score=88.0)
        assert manager.get_cycle(cycle.cycle_id).quality_score == pytest.approx(88.0)

    def test_advance_sets_feedback(self):
        manager = FeedbackCycleManager()
        cycle = manager.start_cycle("t1", "code")
        manager.advance(cycle.cycle_id, CycleStage.QUALITY_ASSESSMENT, score=88.0)
        manager.advance(cycle.cycle_id, CycleStage.FEEDBACK_COLLECTION, feedback={"model": "sonnet"})
        updated = manager.get_cycle(cycle.cycle_id)
        assert updated.feedback["model"] == "sonnet"

    def test_advance_sets_recommendation(self):
        manager = FeedbackCycleManager()
        cycle = manager.start_cycle("t1", "code")
        manager.advance(cycle.cycle_id, CycleStage.QUALITY_ASSESSMENT, score=88.0)
        manager.advance(cycle.cycle_id, CycleStage.FEEDBACK_COLLECTION)
        manager.advance(cycle.cycle_id, CycleStage.TREND_ANALYSIS)
        manager.advance(cycle.cycle_id, CycleStage.ROUTING_IMPROVEMENT, recommendation="upgrade_to_sonnet")
        updated = manager.get_cycle(cycle.cycle_id)
        assert updated.routing_recommendation == "upgrade_to_sonnet"

    def test_full_cycle_is_complete(self):
        manager = FeedbackCycleManager()
        cycle = _full_cycle(manager)
        assert cycle.is_complete

    def test_full_cycle_has_duration(self):
        manager = FeedbackCycleManager()
        cycle = _full_cycle(manager)
        assert cycle.total_duration_seconds is not None
        assert cycle.total_duration_seconds >= 0

    def test_stage_history_length(self):
        manager = FeedbackCycleManager()
        cycle = _full_cycle(manager)
        # 6 stages: TASK_EXECUTION → QA → FEEDBACK → TREND → ROUTING → COMPLETE
        assert len(cycle.stage_history) == 6


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestCycleErrors:
    def test_advance_unknown_cycle_raises(self):
        manager = FeedbackCycleManager()
        with pytest.raises(KeyError):
            manager.advance("nonexistent", CycleStage.QUALITY_ASSESSMENT)

    def test_advance_complete_cycle_raises(self):
        manager = FeedbackCycleManager()
        cycle = _full_cycle(manager)
        with pytest.raises(ValueError, match="already complete"):
            manager.advance(cycle.cycle_id, CycleStage.QUALITY_ASSESSMENT)

    def test_advance_wrong_stage_order_raises(self):
        manager = FeedbackCycleManager()
        cycle = manager.start_cycle("t1", "code")
        with pytest.raises(ValueError, match="Cannot advance"):
            manager.advance(cycle.cycle_id, CycleStage.TREND_ANALYSIS)

    def test_get_unknown_cycle_raises(self):
        manager = FeedbackCycleManager()
        with pytest.raises(KeyError):
            manager.get_cycle("bad-id")


# ---------------------------------------------------------------------------
# Querying
# ---------------------------------------------------------------------------

class TestCycleQuerying:
    def test_cycles_for_task(self):
        manager = FeedbackCycleManager()
        manager.start_cycle("task-A", "code")
        manager.start_cycle("task-B", "test")
        cycles = manager.cycles_for_task("task-A")
        assert len(cycles) == 1
        assert cycles[0].task_id == "task-A"

    def test_all_cycles(self):
        manager = FeedbackCycleManager()
        manager.start_cycle("t1", "code")
        manager.start_cycle("t2", "test")
        assert len(manager.all_cycles()) == 2

    def test_complete_cycles(self):
        manager = FeedbackCycleManager()
        _full_cycle(manager, "t1")
        manager.start_cycle("t2", "test")  # in progress
        assert len(manager.complete_cycles()) == 1

    def test_in_progress_cycles(self):
        manager = FeedbackCycleManager()
        _full_cycle(manager, "t1")
        manager.start_cycle("t2", "test")
        assert len(manager.in_progress_cycles()) == 1

    def test_cycle_summary(self):
        manager = FeedbackCycleManager()
        cycle = _full_cycle(manager)
        summary = cycle.summary()
        assert summary["is_complete"] is True
        assert summary["quality_score"] == pytest.approx(92.0)
        assert summary["routing_recommendation"] == "keep_haiku"


# ---------------------------------------------------------------------------
# Aggregate metrics
# ---------------------------------------------------------------------------

class TestCycleMetrics:
    def test_metrics_empty(self):
        manager = FeedbackCycleManager()
        metrics = manager.cycle_metrics()
        assert metrics["total_cycles"] == 0
        assert metrics["avg_quality_score"] is None

    def test_metrics_with_complete_cycles(self):
        manager = FeedbackCycleManager()
        _full_cycle(manager, "t1")
        _full_cycle(manager, "t2")
        metrics = manager.cycle_metrics()
        assert metrics["total_cycles"] == 2
        assert metrics["complete_cycles"] == 2
        assert metrics["avg_quality_score"] == pytest.approx(92.0)

    def test_metrics_mixed(self):
        manager = FeedbackCycleManager()
        _full_cycle(manager, "t1")
        manager.start_cycle("t2", "test")  # in progress
        metrics = manager.cycle_metrics()
        assert metrics["total_cycles"] == 2
        assert metrics["in_progress_cycles"] == 1
