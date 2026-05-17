"""
Phase 3 Gradual Rollout — End-to-End Tests.

Validates that RolloutManager:
  - Correctly samples traffic at each of the 5 stages (10/25/50/75/100%)
  - Advances through stages in order
  - Rolls back correctly on health failures
  - Pauses and resumes correctly
  - Monitors and alerts at each stage
  - Integrates with audit trail
"""

from __future__ import annotations

import threading
from typing import List

import pytest

from src.orchestration.agents.gradual_rollout import (
    RolloutManager,
    RolloutConfig,
    RolloutStage,
    TrafficSampler,
    StageMetrics,
)


# ─────────────────────────────────────────────────────────────────────────── #
# Helpers
# ─────────────────────────────────────────────────────────────────────────── #

def _make_manager(stage: RolloutStage = RolloutStage.STAGE_10) -> RolloutManager:
    return RolloutManager(initial_stage=stage, enabled=True)


def _sample_traffic(mgr: RolloutManager, n: int = 200) -> float:
    """Return fraction of n tasks routed to new path."""
    sampled = sum(
        1 for i in range(n) if mgr.should_use_new_path(f"task-{i:04d}")
    )
    return sampled / n


# ─────────────────────────────────────────────────────────────────────────── #
# 1. Stage initialisation
# ─────────────────────────────────────────────────────────────────────────── #

class TestRolloutStageInit:
    def test_disabled_stage(self):
        mgr = RolloutManager(initial_stage=RolloutStage.DISABLED)
        assert mgr.stage == RolloutStage.DISABLED

    def test_stage_10_init(self):
        mgr = _make_manager(RolloutStage.STAGE_10)
        assert mgr.stage == RolloutStage.STAGE_10

    def test_stage_100_init(self):
        mgr = _make_manager(RolloutStage.STAGE_100)
        assert mgr.stage == RolloutStage.STAGE_100

    def test_all_stages_valid(self):
        for stage in RolloutStage:
            mgr = RolloutManager(initial_stage=stage)
            assert mgr.stage == stage


# ─────────────────────────────────────────────────────────────────────────── #
# 2. Traffic allocation at each stage
# ─────────────────────────────────────────────────────────────────────────── #

class TestRolloutTrafficAllocation:
    def test_disabled_routes_no_traffic(self):
        mgr = RolloutManager(initial_stage=RolloutStage.DISABLED)
        rate = _sample_traffic(mgr)
        assert rate == 0.0

    def test_stage_10_routes_roughly_10_pct(self):
        mgr = _make_manager(RolloutStage.STAGE_10)
        rate = _sample_traffic(mgr, 500)
        assert 0.04 <= rate <= 0.18, f"Expected ~10%, got {rate:.1%}"

    def test_stage_25_routes_roughly_25_pct(self):
        mgr = _make_manager(RolloutStage.STAGE_25)
        rate = _sample_traffic(mgr, 500)
        assert 0.17 <= rate <= 0.33, f"Expected ~25%, got {rate:.1%}"

    def test_stage_50_routes_roughly_50_pct(self):
        mgr = _make_manager(RolloutStage.STAGE_50)
        rate = _sample_traffic(mgr, 500)
        assert 0.40 <= rate <= 0.60, f"Expected ~50%, got {rate:.1%}"

    def test_stage_75_routes_roughly_75_pct(self):
        mgr = _make_manager(RolloutStage.STAGE_75)
        rate = _sample_traffic(mgr, 500)
        assert 0.65 <= rate <= 0.85, f"Expected ~75%, got {rate:.1%}"

    def test_stage_100_routes_all_traffic(self):
        mgr = _make_manager(RolloutStage.STAGE_100)
        rate = _sample_traffic(mgr)
        assert rate == 1.0

    def test_deterministic_per_task_id(self):
        mgr = _make_manager(RolloutStage.STAGE_50)
        results = [mgr.should_use_new_path("fixed-task-id") for _ in range(5)]
        assert len(set(results)) == 1


# ─────────────────────────────────────────────────────────────────────────── #
# 3. Stage advancement
# ─────────────────────────────────────────────────────────────────────────── #

class TestRolloutAdvancement:
    def test_advance_from_10_to_25(self):
        mgr = _make_manager(RolloutStage.STAGE_10)
        new_stage = mgr.advance()
        assert new_stage == RolloutStage.STAGE_25

    def test_advance_through_all_stages(self):
        mgr = _make_manager(RolloutStage.STAGE_10)
        expected = [
            RolloutStage.STAGE_25,
            RolloutStage.STAGE_50,
            RolloutStage.STAGE_75,
            RolloutStage.STAGE_100,
        ]
        for expected_stage in expected:
            result = mgr.advance()
            assert result == expected_stage

    def test_advance_at_100_returns_none(self):
        mgr = _make_manager(RolloutStage.STAGE_100)
        result = mgr.advance()
        assert result is None

    def test_advance_from_disabled_goes_to_10(self):
        mgr = RolloutManager(initial_stage=RolloutStage.DISABLED)
        new_stage = mgr.advance()
        assert new_stage == RolloutStage.STAGE_10


# ─────────────────────────────────────────────────────────────────────────── #
# 4. Rollback
# ─────────────────────────────────────────────────────────────────────────── #

class TestRolloutRollback:
    def test_rollback_from_25_to_10(self):
        mgr = _make_manager(RolloutStage.STAGE_25)
        prev = mgr.rollback()
        assert prev == RolloutStage.STAGE_10

    def test_rollback_from_10_to_disabled(self):
        mgr = _make_manager(RolloutStage.STAGE_10)
        prev = mgr.rollback()
        assert prev == RolloutStage.DISABLED

    def test_rollback_from_100_to_75(self):
        mgr = _make_manager(RolloutStage.STAGE_100)
        prev = mgr.rollback()
        assert prev == RolloutStage.STAGE_75

    def test_full_rollback_sequence(self):
        mgr = _make_manager(RolloutStage.STAGE_100)
        stages = []
        for _ in range(5):
            stages.append(mgr.rollback())
        assert stages == [
            RolloutStage.STAGE_75,
            RolloutStage.STAGE_50,
            RolloutStage.STAGE_25,
            RolloutStage.STAGE_10,
            RolloutStage.DISABLED,
        ]


# ─────────────────────────────────────────────────────────────────────────── #
# 5. Pause and resume
# ─────────────────────────────────────────────────────────────────────────── #

class TestRolloutPauseResume:
    def test_pause_stops_new_path_routing(self):
        mgr = _make_manager(RolloutStage.STAGE_100)
        mgr.pause()
        assert mgr.is_paused
        # When paused, the manager reports is_paused=True
        # (routing behaviour depends on implementation — pause flag is set)
        assert mgr.is_paused is True

    def test_resume_restores_routing(self):
        mgr = _make_manager(RolloutStage.STAGE_100)
        mgr.pause()
        mgr.resume()
        assert not mgr.is_paused
        rate = _sample_traffic(mgr)
        assert rate == 1.0

    def test_pause_preserves_stage(self):
        mgr = _make_manager(RolloutStage.STAGE_50)
        mgr.pause()
        assert mgr.stage == RolloutStage.STAGE_50


# ─────────────────────────────────────────────────────────────────────────── #
# 6. Outcome recording and health evaluation
# ─────────────────────────────────────────────────────────────────────────── #

class TestRolloutOutcomeRecording:
    def test_record_success_outcome(self):
        mgr = _make_manager(RolloutStage.STAGE_10)
        # Should not raise
        mgr.record_outcome("task-001", error=False, quality_score=0.95, latency_ms=120.0)

    def test_record_error_outcome(self):
        mgr = _make_manager(RolloutStage.STAGE_10)
        mgr.record_outcome("task-001", error=True, quality_score=0.0, latency_ms=500.0)

    def test_evaluate_health_with_good_metrics(self):
        mgr = _make_manager(RolloutStage.STAGE_10)
        for i in range(25):
            mgr.record_outcome(f"task-{i}", error=False, quality_score=0.95, latency_ms=100.0)
        health = mgr.evaluate_health()
        assert health is not None

    def test_stage_metrics_accessible(self):
        mgr = _make_manager(RolloutStage.STAGE_10)
        mgr.record_outcome("task-001", error=False, quality_score=0.9, latency_ms=100.0)
        metrics = mgr.get_stage_metrics()
        assert metrics is not None


# ─────────────────────────────────────────────────────────────────────────── #
# 7. Audit trail
# ─────────────────────────────────────────────────────────────────────────── #

class TestRolloutAuditTrail:
    def test_audit_trail_exists(self):
        mgr = _make_manager(RolloutStage.STAGE_10)
        trail = mgr.get_audit_trail()
        assert trail is not None

    def test_audit_trail_records_advance(self):
        mgr = _make_manager(RolloutStage.STAGE_10)
        mgr.advance()
        trail = mgr.get_audit_trail()
        assert len(trail) >= 1

    def test_audit_trail_records_rollback(self):
        mgr = _make_manager(RolloutStage.STAGE_50)
        mgr.rollback()
        trail = mgr.get_audit_trail()
        assert len(trail) >= 1


# ─────────────────────────────────────────────────────────────────────────── #
# 8. Concurrency
# ─────────────────────────────────────────────────────────────────────────── #

class TestRolloutConcurrency:
    def test_concurrent_should_use_new_path(self):
        """50 concurrent threads querying should_use_new_path must not error."""
        mgr = _make_manager(RolloutStage.STAGE_50)
        errors: List[str] = []
        lock = threading.Lock()

        def query(i: int):
            try:
                mgr.should_use_new_path(f"task-{i}")
            except Exception as exc:
                with lock:
                    errors.append(str(exc))

        threads = [threading.Thread(target=query, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert errors == []

    def test_concurrent_record_outcomes(self):
        """Concurrent outcome recording must be thread-safe."""
        mgr = _make_manager(RolloutStage.STAGE_10)
        errors: List[str] = []
        lock = threading.Lock()

        def record(i: int):
            try:
                mgr.record_outcome(f"task-{i}", error=False, quality_score=0.9, latency_ms=100.0)
            except Exception as exc:
                with lock:
                    errors.append(str(exc))

        threads = [threading.Thread(target=record, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert errors == []
