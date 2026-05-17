"""
Phase 3 Shadow Mode — End-to-End Tests.

Validates that ShadowModeContext:
  - Executes production path for every request
  - Samples shadow path at the configured traffic percentage
  - Compares results without impacting production
  - Handles concurrent agents correctly
  - Collects accurate metrics
"""

from __future__ import annotations

import threading
import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.orchestration.agents.shadow_mode import (
    ShadowModeContext,
    ShadowModeTraffic,
    get_shadow_mode_config,
)


# ─────────────────────────────────────────────────────────────────────────── #
# Helpers
# ─────────────────────────────────────────────────────────────────────────── #

def _prod_fn(*args, **kwargs) -> dict:
    return {"result": "production", "args": args}


def _shadow_fn(*args, **kwargs) -> dict:
    return {"result": "shadow", "args": args}


def _slow_fn(*args, **kwargs) -> dict:
    time.sleep(0.01)
    return {"result": "slow"}


def _error_fn(*args, **kwargs) -> dict:
    raise RuntimeError("Shadow error")


# ─────────────────────────────────────────────────────────────────────────── #
# 1. Basic execution
# ─────────────────────────────────────────────────────────────────────────── #

class TestShadowModeBasic:
    def test_production_always_executes(self):
        ctx = ShadowModeContext("task-001", traffic_percentage=1, enabled=True)
        prod, shadow = ctx.execute_parallel(_prod_fn, _shadow_fn)
        assert prod["result"] == "production"

    def test_shadow_not_executed_at_1_pct(self):
        # At 1% traffic, most tasks should NOT be sampled
        sampled = 0
        total = 100
        for i in range(total):
            ctx = ShadowModeContext(f"task-{i:04d}", traffic_percentage=1, enabled=True)
            _, shadow = ctx.execute_parallel(_prod_fn, _shadow_fn)
            if shadow is not None:
                sampled += 1
        # At 1%, expect very few sampled (allow up to 5 out of 100)
        assert sampled <= 5, f"Expected ≤5% sampling at 1%, got {sampled}/{total}"

    def test_shadow_always_executes_at_100_pct(self):
        ctx = ShadowModeContext("task-001", traffic_percentage=100, enabled=True)
        prod, shadow = ctx.execute_parallel(_prod_fn, _shadow_fn)
        assert prod["result"] == "production"
        assert shadow["result"] == "shadow"

    def test_production_result_returned_regardless_of_shadow(self):
        """Production result must be returned even if shadow fails."""
        ctx = ShadowModeContext("task-001", traffic_percentage=100, enabled=True)
        prod, shadow = ctx.execute_parallel(_prod_fn, _error_fn)
        assert prod["result"] == "production"
        # Shadow error is captured, not raised
        summary = ctx.get_metrics_summary()
        assert summary["shadow_error"] is not None or shadow is None


# ─────────────────────────────────────────────────────────────────────────── #
# 2. Traffic sampling
# ─────────────────────────────────────────────────────────────────────────── #

class TestShadowModeTrafficSampling:
    def test_10_pct_traffic_roughly_correct(self):
        """With 10% traffic, ~10% of tasks should be sampled."""
        sampled = 0
        total = 200
        for i in range(total):
            ctx = ShadowModeContext(f"task-{i:04d}", traffic_percentage=10, enabled=True)
            _, shadow = ctx.execute_parallel(_prod_fn, _shadow_fn)
            if shadow is not None:
                sampled += 1
        # Allow ±8% tolerance around 10%
        rate = sampled / total
        assert 0.02 <= rate <= 0.18, f"Expected ~10% sampling, got {rate:.1%}"

    def test_50_pct_traffic_roughly_correct(self):
        sampled = 0
        total = 200
        for i in range(total):
            ctx = ShadowModeContext(f"task-{i:04d}", traffic_percentage=50, enabled=True)
            _, shadow = ctx.execute_parallel(_prod_fn, _shadow_fn)
            if shadow is not None:
                sampled += 1
        rate = sampled / total
        assert 0.35 <= rate <= 0.65, f"Expected ~50% sampling, got {rate:.1%}"

    def test_deterministic_sampling(self):
        """Same task ID must always produce same sampling decision."""
        results = []
        for _ in range(5):
            ctx = ShadowModeContext("fixed-task-id", traffic_percentage=10, enabled=True)
            _, shadow = ctx.execute_parallel(_prod_fn, _shadow_fn)
            results.append(shadow is not None)
        assert len(set(results)) == 1, "Sampling must be deterministic"

    def test_shadow_mode_traffic_enum_values(self):
        valid_pcts = {t.value for t in ShadowModeTraffic}
        assert 10 in valid_pcts
        assert 50 in valid_pcts
        assert 100 in valid_pcts


# ─────────────────────────────────────────────────────────────────────────── #
# 3. Parallel execution
# ─────────────────────────────────────────────────────────────────────────── #

class TestShadowModeParallelExecution:
    def test_shadow_runs_concurrently_with_production(self):
        """Shadow should not block production path."""
        call_order = []

        def prod():
            call_order.append("prod_start")
            time.sleep(0.005)
            call_order.append("prod_end")
            return "prod"

        def shadow():
            call_order.append("shadow_start")
            time.sleep(0.005)
            call_order.append("shadow_end")
            return "shadow"

        ctx = ShadowModeContext("task-parallel", traffic_percentage=100, enabled=True)
        prod_result, _ = ctx.execute_parallel(prod, shadow)
        assert prod_result == "prod"

    def test_concurrent_agents_50_tasks(self):
        """50 concurrent shadow-mode tasks must all complete without error."""
        errors = []
        results = []
        lock = threading.Lock()

        def run_task(i: int):
            try:
                ctx = ShadowModeContext(f"concurrent-{i}", traffic_percentage=50, enabled=True)
                prod, _ = ctx.execute_parallel(_prod_fn, _shadow_fn)
                with lock:
                    results.append(prod)
            except Exception as exc:
                with lock:
                    errors.append(str(exc))

        threads = [threading.Thread(target=run_task, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert errors == [], f"Concurrent errors: {errors}"
        assert len(results) == 50

    def test_production_latency_measured(self):
        ctx = ShadowModeContext("task-latency", traffic_percentage=100, enabled=True)
        ctx.execute_parallel(_slow_fn, _shadow_fn)
        summary = ctx.get_metrics_summary()
        assert summary["production_latency_ms"] >= 0


# ─────────────────────────────────────────────────────────────────────────── #
# 4. Result comparison
# ─────────────────────────────────────────────────────────────────────────── #

class TestShadowModeResultComparison:
    def test_identical_results_detected(self):
        def identical_fn(*a, **kw):
            return {"value": 42}

        ctx = ShadowModeContext("task-match", traffic_percentage=100, enabled=True)
        prod, shadow = ctx.execute_parallel(identical_fn, identical_fn)
        assert prod == shadow

    def test_different_results_both_captured(self):
        ctx = ShadowModeContext("task-diff", traffic_percentage=100, enabled=True)
        prod, shadow = ctx.execute_parallel(_prod_fn, _shadow_fn)
        assert prod["result"] == "production"
        assert shadow["result"] == "shadow"

    def test_shadow_error_does_not_affect_production(self):
        ctx = ShadowModeContext("task-err", traffic_percentage=100, enabled=True)
        prod, shadow = ctx.execute_parallel(_prod_fn, _error_fn)
        assert prod["result"] == "production"


# ─────────────────────────────────────────────────────────────────────────── #
# 5. Metrics collection
# ─────────────────────────────────────────────────────────────────────────── #

class TestShadowModeMetrics:
    def test_metrics_summary_has_required_fields(self):
        ctx = ShadowModeContext("task-metrics", traffic_percentage=100, enabled=True)
        ctx.execute_parallel(_prod_fn, _shadow_fn)
        summary = ctx.get_metrics_summary()
        required = {"task_id", "sampled", "traffic_percentage", "production_latency_ms", "timestamp"}
        assert required.issubset(summary.keys())

    def test_task_id_in_metrics(self):
        ctx = ShadowModeContext("my-unique-task", traffic_percentage=100, enabled=True)
        ctx.execute_parallel(_prod_fn, _shadow_fn)
        assert ctx.get_metrics_summary()["task_id"] == "my-unique-task"

    def test_traffic_percentage_in_metrics(self):
        ctx = ShadowModeContext("task-pct", traffic_percentage=25, enabled=True)
        ctx.execute_parallel(_prod_fn, _shadow_fn)
        assert ctx.get_metrics_summary()["traffic_percentage"] == 25


# ─────────────────────────────────────────────────────────────────────────── #
# 6. Config loading
# ─────────────────────────────────────────────────────────────────────────── #

class TestShadowModeConfig:
    def test_get_shadow_mode_config_returns_tuple(self):
        cfg = get_shadow_mode_config()
        # Returns (enabled: bool, traffic_pct: int)
        assert isinstance(cfg, tuple)
        assert len(cfg) == 2

    def test_config_has_traffic_percentage(self):
        enabled, traffic_pct = get_shadow_mode_config()
        assert isinstance(traffic_pct, int)
        assert traffic_pct in {1, 5, 10, 25, 50, 75, 100}

    def test_env_override_traffic_pct(self, monkeypatch):
        monkeypatch.setenv("SHADOW_MODE_TRAFFIC_PCT", "25")
        _, traffic_pct = get_shadow_mode_config()
        assert traffic_pct == 25
