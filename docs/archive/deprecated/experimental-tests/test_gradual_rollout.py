"""
Tests for Gradual Rollout System.

Covers:
- Traffic sampling (deterministic, consistent, boundary conditions)
- Stage progression (advance, rollback, override, disable)
- Health check evaluation (pass, fail, insufficient samples)
- Automatic rollback (error rate, quality score thresholds)
- Manual controls (pause, resume, advance, rollback, override)
- Audit trail (persistence, completeness)
- Environment variable configuration
- Integration scenarios (dry-run, shadow mode style)
- Thread safety
- Edge cases

35+ tests.
"""

import json
import os
import threading
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.orchestration.agents.gradual_rollout import (
    RolloutStage,
    RolloutAction,
    RolloutDecisionReason,
    RolloutConfig,
    RolloutManager,
    RolloutHealthSnapshot,
    RolloutDecision,
    StageMetrics,
    TrafficSampler,
    HealthCheckEvaluator,
    create_rollout_manager,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_audit_dir(tmp_path):
    return str(tmp_path / "rollout-audit")


@pytest.fixture
def config(tmp_audit_dir):
    return RolloutConfig(
        error_threshold=0.05,
        quality_min=0.80,
        min_samples=5,   # Low for tests
        auto_advance=True,
        audit_dir=tmp_audit_dir,
    )


@pytest.fixture
def manager(config):
    return RolloutManager(
        config=config,
        initial_stage=RolloutStage.STAGE_10,
        enabled=True,
    )


@pytest.fixture
def disabled_manager(config):
    return RolloutManager(
        config=config,
        initial_stage=RolloutStage.DISABLED,
        enabled=True,
    )


# ===========================================================================
# TrafficSampler Tests
# ===========================================================================

class TestTrafficSampler:

    def test_zero_percent_never_samples(self):
        for i in range(100):
            assert TrafficSampler.sample(f"task-{i}", 0) is False

    def test_hundred_percent_always_samples(self):
        for i in range(100):
            assert TrafficSampler.sample(f"task-{i}", 100) is True

    def test_deterministic_same_task_same_result(self):
        task_id = "task-abc-123"
        result1 = TrafficSampler.sample(task_id, 50)
        result2 = TrafficSampler.sample(task_id, 50)
        assert result1 == result2

    def test_deterministic_across_percentages(self):
        """A task sampled at 50% must also be sampled at 75% and 100%."""
        # Find a task that is sampled at 10%
        for i in range(200):
            task_id = f"task-{i}"
            if TrafficSampler.sample(task_id, 10):
                # Must also be sampled at higher percentages
                assert TrafficSampler.sample(task_id, 25)
                assert TrafficSampler.sample(task_id, 50)
                assert TrafficSampler.sample(task_id, 75)
                assert TrafficSampler.sample(task_id, 100)
                break

    def test_approximate_distribution_10_percent(self):
        """~10% of 1000 tasks should be sampled at 10%."""
        sampled = sum(1 for i in range(1000) if TrafficSampler.sample(f"t-{i}", 10))
        assert 50 <= sampled <= 150, f"Expected ~100, got {sampled}"

    def test_approximate_distribution_50_percent(self):
        """~50% of 1000 tasks should be sampled at 50%."""
        sampled = sum(1 for i in range(1000) if TrafficSampler.sample(f"t-{i}", 50))
        assert 400 <= sampled <= 600, f"Expected ~500, got {sampled}"

    def test_approximate_distribution_75_percent(self):
        """~75% of 1000 tasks should be sampled at 75%."""
        sampled = sum(1 for i in range(1000) if TrafficSampler.sample(f"t-{i}", 75))
        assert 650 <= sampled <= 850, f"Expected ~750, got {sampled}"

    def test_bucket_range(self):
        """Bucket must always be in [0, 99]."""
        for i in range(500):
            b = TrafficSampler.bucket(f"task-{i}")
            assert 0 <= b <= 99

    def test_different_task_ids_may_differ(self):
        """Different task IDs should not always produce the same result."""
        results = {TrafficSampler.sample(f"task-{i}", 50) for i in range(20)}
        assert len(results) == 2, "Expected both True and False across 20 tasks"

    def test_empty_task_id(self):
        """Empty task_id should not raise."""
        result = TrafficSampler.sample("", 50)
        assert isinstance(result, bool)


# ===========================================================================
# RolloutStage Tests
# ===========================================================================

class TestRolloutStage:

    def test_progression_order(self):
        stages = RolloutStage.progression()
        values = [s.value for s in stages]
        assert values == [10, 25, 50, 75, 100]

    def test_next_stage_from_disabled(self):
        assert RolloutStage.DISABLED.next_stage() == RolloutStage.STAGE_10

    def test_next_stage_progression(self):
        assert RolloutStage.STAGE_10.next_stage() == RolloutStage.STAGE_25
        assert RolloutStage.STAGE_25.next_stage() == RolloutStage.STAGE_50
        assert RolloutStage.STAGE_50.next_stage() == RolloutStage.STAGE_75
        assert RolloutStage.STAGE_75.next_stage() == RolloutStage.STAGE_100

    def test_next_stage_at_100_is_none(self):
        assert RolloutStage.STAGE_100.next_stage() is None

    def test_prev_stage_from_10_is_disabled(self):
        assert RolloutStage.STAGE_10.prev_stage() == RolloutStage.DISABLED

    def test_prev_stage_progression(self):
        assert RolloutStage.STAGE_25.prev_stage() == RolloutStage.STAGE_10
        assert RolloutStage.STAGE_50.prev_stage() == RolloutStage.STAGE_25
        assert RolloutStage.STAGE_75.prev_stage() == RolloutStage.STAGE_50
        assert RolloutStage.STAGE_100.prev_stage() == RolloutStage.STAGE_75

    def test_prev_stage_from_disabled_is_none(self):
        assert RolloutStage.DISABLED.prev_stage() is None


# ===========================================================================
# HealthCheckEvaluator Tests
# ===========================================================================

class TestHealthCheckEvaluator:

    @pytest.fixture
    def evaluator(self, config):
        return HealthCheckEvaluator(config)

    def _make_metrics(self, stage=10, total=10, errors=0, quality_sum=9.0, latencies=None):
        m = StageMetrics(stage=stage)
        m.total_tasks = total
        m.error_tasks = errors
        m.quality_score_sum = quality_sum
        m.latency_samples = latencies or [100.0] * total
        return m

    def test_healthy_when_thresholds_met(self, evaluator):
        metrics = self._make_metrics(total=10, errors=0, quality_sum=9.0)
        snapshot = evaluator.evaluate(RolloutStage.STAGE_10, metrics)
        assert snapshot.is_healthy is True
        assert snapshot.failure_reasons == []

    def test_unhealthy_insufficient_samples(self, evaluator):
        metrics = self._make_metrics(total=2, errors=0, quality_sum=2.0)
        snapshot = evaluator.evaluate(RolloutStage.STAGE_10, metrics)
        assert snapshot.is_healthy is False
        assert any("Insufficient" in r for r in snapshot.failure_reasons)

    def test_unhealthy_error_rate_exceeded(self, evaluator):
        # 3/10 = 30% error rate, threshold is 5%
        metrics = self._make_metrics(total=10, errors=3, quality_sum=7.0)
        snapshot = evaluator.evaluate(RolloutStage.STAGE_10, metrics)
        assert snapshot.is_healthy is False
        assert any("Error rate" in r for r in snapshot.failure_reasons)

    def test_unhealthy_quality_score_low(self, evaluator):
        # quality = 6.0/10 = 0.60, min is 0.80
        metrics = self._make_metrics(total=10, errors=0, quality_sum=6.0)
        snapshot = evaluator.evaluate(RolloutStage.STAGE_10, metrics)
        assert snapshot.is_healthy is False
        assert any("Quality score" in r for r in snapshot.failure_reasons)

    def test_error_rate_calculation(self, evaluator):
        metrics = self._make_metrics(total=10, errors=1, quality_sum=9.0)
        snapshot = evaluator.evaluate(RolloutStage.STAGE_10, metrics)
        assert abs(snapshot.error_rate - 0.10) < 0.001

    def test_quality_score_calculation(self, evaluator):
        metrics = self._make_metrics(total=10, errors=0, quality_sum=9.5)
        snapshot = evaluator.evaluate(RolloutStage.STAGE_10, metrics)
        assert abs(snapshot.quality_score - 0.95) < 0.001

    def test_p95_latency_calculated(self, evaluator):
        latencies = list(range(1, 101))  # 1..100 ms
        metrics = self._make_metrics(total=100, errors=0, quality_sum=90.0, latencies=latencies)
        snapshot = evaluator.evaluate(RolloutStage.STAGE_10, metrics)
        assert snapshot.p95_latency_ms >= 95  # p95 of 1..100

    def test_empty_metrics_not_healthy(self, evaluator):
        metrics = StageMetrics(stage=10)
        snapshot = evaluator.evaluate(RolloutStage.STAGE_10, metrics)
        assert snapshot.is_healthy is False


# ===========================================================================
# RolloutManager Core Tests
# ===========================================================================

class TestRolloutManagerCore:

    def test_initial_stage(self, manager):
        assert manager.stage == RolloutStage.STAGE_10

    def test_disabled_manager_never_routes_new_path(self, disabled_manager):
        for i in range(100):
            assert disabled_manager.should_use_new_path(f"task-{i}") is False

    def test_stage_100_always_routes_new_path(self, config):
        m = RolloutManager(config=config, initial_stage=RolloutStage.STAGE_100)
        for i in range(20):
            assert m.should_use_new_path(f"task-{i}") is True

    def test_routing_is_deterministic(self, manager):
        task_id = "stable-task-xyz"
        r1 = manager.should_use_new_path(task_id)
        r2 = manager.should_use_new_path(task_id)
        assert r1 == r2

    def test_disabled_enabled_flag(self, config):
        m = RolloutManager(config=config, initial_stage=RolloutStage.STAGE_100, enabled=False)
        for i in range(20):
            assert m.should_use_new_path(f"task-{i}") is False

    def test_status_returns_dict(self, manager):
        s = manager.status()
        assert "stage" in s
        assert "enabled" in s
        assert "paused" in s
        assert "health" in s
        assert "metrics" in s


# ===========================================================================
# Manual Control Tests
# ===========================================================================

class TestManualControls:

    def test_pause_stops_auto_advance(self, manager):
        manager.pause(operator="test-op")
        assert manager.is_paused is True
        result = manager.evaluate_and_advance()
        assert result is None

    def test_resume_allows_advance(self, manager):
        manager.pause()
        manager.resume()
        assert manager.is_paused is False

    def test_manual_advance(self, manager):
        assert manager.stage == RolloutStage.STAGE_10
        new_stage = manager.advance(operator="test-op")
        assert new_stage == RolloutStage.STAGE_25
        assert manager.stage == RolloutStage.STAGE_25

    def test_manual_advance_at_100_returns_none(self, config):
        m = RolloutManager(config=config, initial_stage=RolloutStage.STAGE_100)
        result = m.advance()
        assert result is None
        assert m.stage == RolloutStage.STAGE_100

    def test_manual_rollback(self, manager):
        manager.advance()  # 10 → 25
        result = manager.rollback(operator="test-op")
        assert result == RolloutStage.STAGE_10
        assert manager.stage == RolloutStage.STAGE_10

    def test_manual_rollback_from_10_goes_to_disabled(self, manager):
        result = manager.rollback()
        assert result == RolloutStage.DISABLED
        assert manager.stage == RolloutStage.DISABLED

    def test_override_stage(self, manager):
        manager.override_stage(RolloutStage.STAGE_75, operator="test-op")
        assert manager.stage == RolloutStage.STAGE_75

    def test_disable(self, manager):
        manager.disable(operator="test-op")
        assert manager.stage == RolloutStage.DISABLED
        for i in range(20):
            assert manager.should_use_new_path(f"task-{i}") is False


# ===========================================================================
# Automatic Rollback Tests
# ===========================================================================

class TestAutomaticRollback:

    def _fill_metrics(self, manager, *, error_rate=0.0, quality=0.95, n=10):
        """Fill stage metrics with synthetic outcomes."""
        stage = manager.stage
        # Find task IDs that are sampled at this stage
        sampled = []
        for i in range(1000):
            tid = f"task-{i}"
            if TrafficSampler.sample(tid, stage.value):
                sampled.append(tid)
            if len(sampled) >= n:
                break

        for idx, tid in enumerate(sampled):
            is_error = idx < int(n * error_rate)
            manager.record_outcome(
                tid,
                error=is_error,
                quality_score=quality if not is_error else 0.0,
                latency_ms=100.0,
            )

    def test_no_rollback_when_healthy(self, manager):
        self._fill_metrics(manager, error_rate=0.0, quality=0.95)
        # Should not rollback
        assert manager.stage == RolloutStage.STAGE_10

    def test_auto_rollback_on_high_error_rate(self, config):
        # Use lower min_samples to trigger rollback quickly
        config.min_samples = 5
        m = RolloutManager(config=config, initial_stage=RolloutStage.STAGE_25)
        self._fill_metrics(m, error_rate=0.60, quality=0.40, n=10)
        # Trigger evaluation
        m._check_auto_rollback()
        assert m.stage == RolloutStage.STAGE_10

    def test_auto_rollback_on_low_quality(self, config):
        config.min_samples = 5
        m = RolloutManager(config=config, initial_stage=RolloutStage.STAGE_25)
        self._fill_metrics(m, error_rate=0.0, quality=0.50, n=10)
        m._check_auto_rollback()
        assert m.stage == RolloutStage.STAGE_10

    def test_no_rollback_below_min_samples(self, config):
        config.min_samples = 50
        m = RolloutManager(config=config, initial_stage=RolloutStage.STAGE_25)
        # Only 3 samples — below min_samples, should NOT rollback even with errors
        self._fill_metrics(m, error_rate=1.0, quality=0.0, n=3)
        m._check_auto_rollback()
        assert m.stage == RolloutStage.STAGE_25  # No rollback

    def test_rollback_from_10_goes_to_disabled(self, config):
        config.min_samples = 5
        m = RolloutManager(config=config, initial_stage=RolloutStage.STAGE_10)
        self._fill_metrics(m, error_rate=0.80, quality=0.10, n=10)
        m._check_auto_rollback()
        assert m.stage == RolloutStage.DISABLED


# ===========================================================================
# Auto-Advance Tests
# ===========================================================================

class TestAutoAdvance:

    def _fill_healthy_metrics(self, manager, n=10):
        stage = manager.stage
        sampled = []
        for i in range(1000):
            tid = f"task-{i}"
            if TrafficSampler.sample(tid, stage.value):
                sampled.append(tid)
            if len(sampled) >= n:
                break
        for tid in sampled:
            manager.record_outcome(tid, error=False, quality_score=0.95, latency_ms=100.0)

    def test_advance_on_healthy_metrics(self, manager):
        self._fill_healthy_metrics(manager, n=10)
        new_stage = manager.evaluate_and_advance()
        assert new_stage == RolloutStage.STAGE_25
        assert manager.stage == RolloutStage.STAGE_25

    def test_no_advance_when_paused(self, manager):
        self._fill_healthy_metrics(manager, n=10)
        manager.pause()
        result = manager.evaluate_and_advance()
        assert result is None
        assert manager.stage == RolloutStage.STAGE_10

    def test_no_advance_when_auto_advance_disabled(self, config):
        config.auto_advance = False
        m = RolloutManager(config=config, initial_stage=RolloutStage.STAGE_10)
        result = m.evaluate_and_advance()
        assert result is None

    def test_no_advance_at_stage_100(self, config):
        m = RolloutManager(config=config, initial_stage=RolloutStage.STAGE_100)
        result = m.evaluate_and_advance()
        assert result is None


# ===========================================================================
# Audit Trail Tests
# ===========================================================================

class TestAuditTrail:

    def test_initialization_recorded(self, manager):
        trail = manager.get_audit_trail()
        assert len(trail) >= 1
        assert trail[0].reason == RolloutDecisionReason.INITIALIZATION.value

    def test_advance_recorded(self, manager):
        manager.advance(operator="alice")
        trail = manager.get_audit_trail()
        advance_entries = [d for d in trail if d.action == RolloutAction.ADVANCE.value]
        assert len(advance_entries) >= 1
        assert advance_entries[-1].operator == "alice"

    def test_rollback_recorded(self, manager):
        manager.rollback(operator="bob")
        trail = manager.get_audit_trail()
        rollback_entries = [d for d in trail if d.action == RolloutAction.ROLLBACK.value]
        assert len(rollback_entries) >= 1

    def test_pause_resume_recorded(self, manager):
        manager.pause()
        manager.resume()
        trail = manager.get_audit_trail()
        actions = [d.action for d in trail]
        assert RolloutAction.PAUSE.value in actions
        assert RolloutAction.RESUME.value in actions

    def test_audit_persisted_to_disk(self, manager, tmp_audit_dir):
        manager.advance()
        log_file = Path(tmp_audit_dir) / "audit.jsonl"
        assert log_file.exists()
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) >= 2  # init + advance
        for line in lines:
            record = json.loads(line)
            assert "timestamp" in record
            assert "action" in record
            assert "from_stage" in record
            assert "to_stage" in record

    def test_audit_trail_is_copy(self, manager):
        trail = manager.get_audit_trail()
        trail.clear()
        assert len(manager.get_audit_trail()) > 0


# ===========================================================================
# Environment Variable Configuration Tests
# ===========================================================================

class TestEnvConfig:

    def test_from_env_defaults(self, tmp_audit_dir):
        with patch.dict(os.environ, {"ROLLOUT_AUDIT_DIR": tmp_audit_dir}, clear=False):
            config = RolloutConfig.from_env()
        assert config.error_threshold == 0.05
        assert config.quality_min == 0.80
        assert config.min_samples == 20
        assert config.auto_advance is True

    def test_from_env_custom_values(self, tmp_audit_dir):
        env = {
            "ROLLOUT_ERROR_THRESHOLD": "0.10",
            "ROLLOUT_QUALITY_MIN": "0.70",
            "ROLLOUT_MIN_SAMPLES": "50",
            "ROLLOUT_AUTO_ADVANCE": "false",
            "ROLLOUT_AUDIT_DIR": tmp_audit_dir,
        }
        with patch.dict(os.environ, env, clear=False):
            config = RolloutConfig.from_env()
        assert config.error_threshold == 0.10
        assert config.quality_min == 0.70
        assert config.min_samples == 50
        assert config.auto_advance is False

    def test_manager_from_env_stage(self, tmp_audit_dir):
        env = {
            "ROLLOUT_STAGE": "25",
            "ROLLOUT_ENABLED": "true",
            "ROLLOUT_PAUSED": "false",
            "ROLLOUT_AUDIT_DIR": tmp_audit_dir,
        }
        with patch.dict(os.environ, env, clear=False):
            m = RolloutManager.from_env()
        assert m.stage == RolloutStage.STAGE_25

    def test_manager_from_env_paused(self, tmp_audit_dir):
        env = {
            "ROLLOUT_STAGE": "10",
            "ROLLOUT_PAUSED": "true",
            "ROLLOUT_AUDIT_DIR": tmp_audit_dir,
        }
        with patch.dict(os.environ, env, clear=False):
            m = RolloutManager.from_env()
        assert m.is_paused is True

    def test_manager_from_env_disabled(self, tmp_audit_dir):
        env = {
            "ROLLOUT_ENABLED": "false",
            "ROLLOUT_STAGE": "100",
            "ROLLOUT_AUDIT_DIR": tmp_audit_dir,
        }
        with patch.dict(os.environ, env, clear=False):
            m = RolloutManager.from_env()
        assert m.is_enabled is False
        assert m.should_use_new_path("any-task") is False


# ===========================================================================
# Factory Tests
# ===========================================================================

class TestFactory:

    def test_create_rollout_manager(self, tmp_audit_dir):
        m = create_rollout_manager(stage=25, audit_dir=tmp_audit_dir)
        assert m.stage == RolloutStage.STAGE_25

    def test_create_rollout_manager_invalid_stage(self, tmp_audit_dir):
        with pytest.raises(ValueError, match="Invalid stage value"):
            create_rollout_manager(stage=99, audit_dir=tmp_audit_dir)

    def test_create_rollout_manager_disabled(self, tmp_audit_dir):
        m = create_rollout_manager(stage=0, audit_dir=tmp_audit_dir)
        assert m.stage == RolloutStage.DISABLED


# ===========================================================================
# Thread Safety Tests
# ===========================================================================

class TestThreadSafety:

    def test_concurrent_record_outcome(self, manager):
        """Multiple threads recording outcomes should not corrupt state."""
        errors = []

        def record(i):
            try:
                # Find a task sampled at stage 10
                tid = f"thread-task-{i}"
                manager.record_outcome(
                    tid, error=(i % 10 == 0), quality_score=0.9, latency_ms=50.0
                )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"

    def test_concurrent_stage_transitions(self, config):
        """Concurrent advance/rollback should not corrupt stage state."""
        m = RolloutManager(config=config, initial_stage=RolloutStage.STAGE_50)
        errors = []

        def do_transition(i):
            try:
                if i % 2 == 0:
                    m.advance()
                else:
                    m.rollback()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=do_transition, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        # Stage must be a valid RolloutStage
        assert m.stage in list(RolloutStage)


# ===========================================================================
# Integration Scenario Tests
# ===========================================================================

class TestIntegrationScenarios:

    def test_full_rollout_progression(self, config):
        """Simulate a full rollout from DISABLED to STAGE_100."""
        config.min_samples = 5
        m = RolloutManager(config=config, initial_stage=RolloutStage.DISABLED)

        # Manually advance through all stages
        for expected in RolloutStage.progression():
            m.advance(operator="ci-pipeline")
            assert m.stage == expected

        assert m.stage == RolloutStage.STAGE_100

    def test_rollout_with_mid_stage_failure_and_recovery(self, config):
        """Simulate failure at stage 50, rollback, fix, re-advance."""
        config.min_samples = 5
        m = RolloutManager(config=config, initial_stage=RolloutStage.STAGE_50)

        # Simulate bad metrics
        stage = m.stage
        sampled = [f"task-{i}" for i in range(1000) if TrafficSampler.sample(f"task-{i}", stage.value)][:10]
        for tid in sampled:
            m.record_outcome(tid, error=True, quality_score=0.0, latency_ms=5000.0)

        m._check_auto_rollback()
        assert m.stage == RolloutStage.STAGE_25  # Rolled back

        # Fix and re-advance
        m.advance(operator="engineer")
        assert m.stage == RolloutStage.STAGE_50

    def test_pause_resume_cycle(self, config):
        """Pause, verify no advance, resume, verify advance works."""
        config.min_samples = 5
        m = RolloutManager(config=config, initial_stage=RolloutStage.STAGE_10)

        # Fill healthy metrics
        sampled = [f"task-{i}" for i in range(1000) if TrafficSampler.sample(f"task-{i}", 10)][:10]
        for tid in sampled:
            m.record_outcome(tid, error=False, quality_score=0.95, latency_ms=100.0)

        m.pause()
        result = m.evaluate_and_advance()
        assert result is None  # Paused

        m.resume()
        result = m.evaluate_and_advance()
        assert result == RolloutStage.STAGE_25

    def test_status_snapshot_completeness(self, manager):
        """Status dict should contain all expected keys."""
        s = manager.status()
        required_keys = ["stage", "stage_value", "enabled", "paused", "health", "metrics", "config"]
        for key in required_keys:
            assert key in s, f"Missing key: {key}"
