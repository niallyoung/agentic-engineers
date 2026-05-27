"""
Phase 3 Performance Benchmarks
================================
Measures throughput and latency of core Phase 3 components:
  - TokenTracker.record_task_tokens()
  - CLIFormatter.format_task_line()
  - BudgetChecker.check()
  - ComplexityScorer.score()
  - ModelSelector.select()
  - OrchestratorCLI.on_task_complete()

Run with:
    python3 tests/benchmarks/phase3_performance.py

Or via pytest (slower due to fixture overhead):
    python3 -m pytest tests/benchmarks/phase3_performance.py -v
"""

import time
import statistics
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.orchestration.monitoring.metrics import MetricsRegistry
from src.orchestration.monitoring.token_tracker import TokenTracker, TokenMetrics
from src.orchestration.monitoring.cli_formatter import CLIFormatter
from src.orchestration.monitoring.budget_checker import BudgetChecker
from src.orchestration.monitoring.orchestrator_cli import OrchestratorCLI
from src.orchestration.models.complexity_scorer import ComplexityScorer, TaskAttributes
from src.orchestration.models.model_selector import ModelSelector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_metrics(task_id: str = "bench-task-001", agent: str = "engineer") -> TokenMetrics:
    return TokenMetrics(
        task_id=task_id,
        agent=agent,
        input_tokens=1000,
        output_tokens=500,
        cached_tokens=200,
        cost_usd=0.05,
    )


def _make_delegate(task_id: str = "bench-task-001") -> dict:
    return {
        "handoff_type": "DELEGATE",
        "task_id": task_id,
        "role": "engineer",
        "model": "claude-sonnet-4.6",
        "effort": "medium",
        "scope": "Benchmark task",
    }


def _make_handback(task_id: str = "bench-task-001", cost_usd: float = 0.05) -> dict:
    return {
        "handoff_type": "HANDBACK",
        "task_id": task_id,
        "status": "complete",
        "tokens": {
            "input": 1000,
            "output": 500,
            "cached": 200,
            "cost_usd": cost_usd,
        },
        "agent": "engineer",
        "model": "claude-sonnet-4.6",
    }


def _make_task_attributes() -> TaskAttributes:
    return TaskAttributes(
        has_plan=True,
        effort="medium",
        task_type="implementation",
        scope_clarity=0.8,
    )


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

def benchmark(name: str, fn, iterations: int = 1000) -> dict:
    """Run fn() `iterations` times and return timing stats (µs)."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        elapsed = (time.perf_counter() - start) * 1_000_000  # µs
        times.append(elapsed)

    result = {
        "name": name,
        "iterations": iterations,
        "mean_us": statistics.mean(times),
        "median_us": statistics.median(times),
        "p95_us": sorted(times)[int(0.95 * len(times))],
        "p99_us": sorted(times)[int(0.99 * len(times))],
        "min_us": min(times),
        "max_us": max(times),
    }
    return result


def print_result(r: dict) -> None:
    print(
        f"  {r['name']:<45} "
        f"mean={r['mean_us']:>8.1f}µs  "
        f"p95={r['p95_us']:>8.1f}µs  "
        f"p99={r['p99_us']:>8.1f}µs  "
        f"max={r['max_us']:>8.1f}µs"
    )


# ---------------------------------------------------------------------------
# Individual benchmarks
# ---------------------------------------------------------------------------

def bench_token_tracker_record(iterations: int = 1000) -> dict:
    tracker = TokenTracker(MetricsRegistry())
    i = 0

    def fn():
        nonlocal i
        tracker.record_task_tokens(f"task-{i}", "engineer", 1000, 500, cached_tokens=200, cost_usd=0.05)
        i += 1

    return benchmark("TokenTracker.record_task_tokens()", fn, iterations)


def bench_token_tracker_get_stats(iterations: int = 1000) -> dict:
    tracker = TokenTracker(MetricsRegistry())
    for j in range(100):
        tracker.record_task_tokens(f"task-{j}", "engineer", 1000, 500, cost_usd=0.05)

    return benchmark("TokenTracker.get_session_stats()", tracker.get_stats, iterations)


def bench_cli_formatter_format_task_line(iterations: int = 1000) -> dict:
    formatter = CLIFormatter(no_color=True)
    metrics = _make_metrics()

    def fn():
        formatter.format_task_line(metrics, session_cost=1.23)

    return benchmark("CLIFormatter.format_task_line()", fn, iterations)


def bench_budget_checker_check(iterations: int = 1000) -> dict:
    checker = BudgetChecker()
    tracker = TokenTracker(MetricsRegistry())
    for j in range(50):
        tracker.record_task_tokens(f"task-{j}", "engineer", 1000, 500, cost_usd=0.02)
    stats = tracker.get_stats()

    def fn():
        checker.check(stats)

    return benchmark("BudgetChecker.check()", fn, iterations)


def bench_complexity_scorer(iterations: int = 1000) -> dict:
    scorer = ComplexityScorer()
    attrs = _make_task_attributes()

    def fn():
        scorer.score(attrs)

    return benchmark("ComplexityScorer.score()", fn, iterations)


def bench_model_selector(iterations: int = 1000) -> dict:
    selector = ModelSelector()
    attrs = _make_task_attributes()

    def fn():
        selector.select(attrs)

    return benchmark("ModelSelector.select()", fn, iterations)


def bench_orchestrator_cli_on_task_complete(iterations: int = 200) -> dict:
    """Lower iterations — involves print I/O."""
    tracker = TokenTracker(MetricsRegistry())
    cli = OrchestratorCLI(token_tracker=tracker, no_color=True)
    i = 0

    def fn():
        nonlocal i
        delegate = _make_delegate(f"bench-{i}")
        handback = _make_handback(f"bench-{i}", cost_usd=0.05)
        cli.on_task_complete(delegate, handback)
        i += 1

    return benchmark("OrchestratorCLI.on_task_complete()", fn, iterations)


# ---------------------------------------------------------------------------
# Thresholds (µs) — tests fail if exceeded
# ---------------------------------------------------------------------------

THRESHOLDS_P99_US = {
    "TokenTracker.record_task_tokens()": 500,
    "TokenTracker.get_session_stats()": 500,
    "CLIFormatter.format_task_line()": 200,
    "BudgetChecker.check()": 200,
    "ComplexityScorer.score()": 500,
    "ModelSelector.select()": 500,
    "OrchestratorCLI.on_task_complete()": 5_000,  # includes print I/O
}


# ---------------------------------------------------------------------------
# pytest-compatible test functions
# ---------------------------------------------------------------------------

def test_token_tracker_record_performance():
    r = bench_token_tracker_record()
    threshold = THRESHOLDS_P99_US[r["name"]]
    assert r["p99_us"] < threshold, (
        f"{r['name']} p99={r['p99_us']:.1f}µs exceeds threshold {threshold}µs"
    )


def test_token_tracker_get_stats_performance():
    r = bench_token_tracker_get_stats()
    threshold = THRESHOLDS_P99_US[r["name"]]
    assert r["p99_us"] < threshold, (
        f"{r['name']} p99={r['p99_us']:.1f}µs exceeds threshold {threshold}µs"
    )


def test_cli_formatter_performance():
    r = bench_cli_formatter_format_task_line()
    threshold = THRESHOLDS_P99_US[r["name"]]
    assert r["p99_us"] < threshold, (
        f"{r['name']} p99={r['p99_us']:.1f}µs exceeds threshold {threshold}µs"
    )


def test_budget_checker_performance():
    r = bench_budget_checker_check()
    threshold = THRESHOLDS_P99_US[r["name"]]
    assert r["p99_us"] < threshold, (
        f"{r['name']} p99={r['p99_us']:.1f}µs exceeds threshold {threshold}µs"
    )


def test_complexity_scorer_performance():
    r = bench_complexity_scorer()
    threshold = THRESHOLDS_P99_US[r["name"]]
    assert r["p99_us"] < threshold, (
        f"{r['name']} p99={r['p99_us']:.1f}µs exceeds threshold {threshold}µs"
    )


def test_model_selector_performance():
    r = bench_model_selector()
    threshold = THRESHOLDS_P99_US[r["name"]]
    assert r["p99_us"] < threshold, (
        f"{r['name']} p99={r['p99_us']:.1f}µs exceeds threshold {threshold}µs"
    )


def test_orchestrator_cli_performance():
    r = bench_orchestrator_cli_on_task_complete()
    threshold = THRESHOLDS_P99_US[r["name"]]
    assert r["p99_us"] < threshold, (
        f"{r['name']} p99={r['p99_us']:.1f}µs exceeds threshold {threshold}µs"
    )


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n=== Phase 3 Performance Benchmarks ===\n")

    benchmarks = [
        bench_token_tracker_record,
        bench_token_tracker_get_stats,
        bench_cli_formatter_format_task_line,
        bench_budget_checker_check,
        bench_complexity_scorer,
        bench_model_selector,
        bench_orchestrator_cli_on_task_complete,
    ]

    results = []
    failures = []

    for fn in benchmarks:
        r = fn()
        results.append(r)
        print_result(r)
        threshold = THRESHOLDS_P99_US.get(r["name"])
        if threshold and r["p99_us"] > threshold:
            failures.append(f"  FAIL: {r['name']} p99={r['p99_us']:.1f}µs > threshold {threshold}µs")

    print()
    if failures:
        print("THRESHOLD VIOLATIONS:")
        for f in failures:
            print(f)
        sys.exit(1)
    else:
        print("All benchmarks within thresholds. ✓")
