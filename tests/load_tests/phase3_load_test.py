"""
Phase 3 Load Tests
==================
Stress tests for Phase 3 components under concurrent agent load.

Scenarios:
  - 50 concurrent agents recording tokens simultaneously
  - 100 concurrent agents (peak load)
  - Sustained throughput over 500 sequential tasks
  - Mixed read/write concurrency (stats + record simultaneously)
  - Budget checker under concurrent session load

Run with:
    python3 -m pytest tests/load_tests/phase3_load_test.py -v

Or standalone:
    python3 tests/load_tests/phase3_load_test.py
"""

import sys
import os
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.orchestration.monitoring.metrics import MetricsRegistry
from src.orchestration.monitoring.token_tracker import TokenTracker
from src.orchestration.monitoring.budget_checker import BudgetChecker
from src.orchestration.monitoring.cli_formatter import CLIFormatter
from src.orchestration.monitoring.orchestrator_cli import OrchestratorCLI
from src.orchestration.models.complexity_scorer import ComplexityScorer, TaskAttributes
from src.orchestration.models.model_selector import ModelSelector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

AGENTS = ["engineer", "senior-engineer", "lead-engineer", "security-engineer", "quality-engineer"]


def _make_tracker() -> TokenTracker:
    return TokenTracker(MetricsRegistry())


def _make_attrs() -> TaskAttributes:
    return TaskAttributes(has_plan=True, effort="medium", task_type="implementation")


def _make_delegate(task_id: str) -> dict:
    return {
        "handoff_type": "DELEGATE",
        "task_id": task_id,
        "role": "engineer",
        "model": "claude-sonnet-4.6",
        "effort": "medium",
        "scope": "Load test task",
    }


def _make_handback(task_id: str, cost_usd: float = 0.05) -> dict:
    return {
        "handoff_type": "HANDBACK",
        "task_id": task_id,
        "status": "success",
        "tokens": {"input": 1000, "output": 500, "cached": 0, "cost_usd": cost_usd},
        "agent": "engineer",
        "model": "claude-sonnet-4.6",
    }


# ---------------------------------------------------------------------------
# Load test scenarios
# ---------------------------------------------------------------------------

def load_test_concurrent_token_recording(num_agents: int, tasks_per_agent: int = 10) -> dict:
    """
    Simulate `num_agents` agents each recording `tasks_per_agent` token events
    concurrently into a shared TokenTracker.
    """
    tracker = _make_tracker()
    errors = []
    task_counter = [0]
    lock = threading.Lock()

    def agent_work(agent_idx: int):
        agent = AGENTS[agent_idx % len(AGENTS)]
        for t in range(tasks_per_agent):
            with lock:
                task_id = f"load-{task_counter[0]:05d}"
                task_counter[0] += 1
            try:
                tracker.record_task_tokens(
                    task_id, agent,
                    input_tokens=1000 + agent_idx * 10,
                    output_tokens=500 + t * 5,
                    cached_tokens=100,
                    cost_usd=0.05 + agent_idx * 0.001,
                )
            except Exception as e:
                errors.append(str(e))

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=num_agents) as pool:
        futures = [pool.submit(agent_work, i) for i in range(num_agents)]
        for f in as_completed(futures):
            f.result()
    elapsed = time.perf_counter() - start

    stats = tracker.get_stats()
    total_tasks = num_agents * tasks_per_agent

    return {
        "scenario": f"concurrent_token_recording_{num_agents}_agents",
        "num_agents": num_agents,
        "total_tasks": total_tasks,
        "elapsed_s": elapsed,
        "tasks_per_sec": total_tasks / elapsed,
        "recorded_tasks": stats.task_count,
        "errors": errors,
        "data_loss": total_tasks - stats.task_count,
    }


def load_test_mixed_read_write(num_writers: int = 20, num_readers: int = 10, duration_s: float = 2.0) -> dict:
    """
    Simultaneous writers (record_task_tokens) and readers (get_stats / get_agent_stats)
    for `duration_s` seconds. Verifies no deadlocks or data corruption.
    """
    tracker = _make_tracker()
    errors = []
    write_count = [0]
    read_count = [0]
    stop_event = threading.Event()

    def writer(agent_idx: int):
        agent = AGENTS[agent_idx % len(AGENTS)]
        i = 0
        while not stop_event.is_set():
            try:
                tracker.record_task_tokens(
                    f"rw-{agent_idx}-{i}", agent, 500, 250, cost_usd=0.02
                )
                write_count[0] += 1
                i += 1
            except Exception as e:
                errors.append(f"writer: {e}")

    def reader():
        while not stop_event.is_set():
            try:
                tracker.get_stats()
                read_count[0] += 1
            except Exception as e:
                errors.append(f"reader: {e}")

    threads = []
    for i in range(num_writers):
        t = threading.Thread(target=writer, args=(i,), daemon=True)
        t.start()
        threads.append(t)
    for _ in range(num_readers):
        t = threading.Thread(target=reader, daemon=True)
        t.start()
        threads.append(t)

    time.sleep(duration_s)
    stop_event.set()
    for t in threads:
        t.join(timeout=2.0)

    return {
        "scenario": "mixed_read_write",
        "num_writers": num_writers,
        "num_readers": num_readers,
        "duration_s": duration_s,
        "total_writes": write_count[0],
        "total_reads": read_count[0],
        "write_throughput": write_count[0] / duration_s,
        "read_throughput": read_count[0] / duration_s,
        "errors": errors,
    }


def load_test_sustained_sequential(num_tasks: int = 500) -> dict:
    """
    Sequential throughput: record `num_tasks` tokens one after another.
    Measures sustained throughput without concurrency overhead.
    """
    tracker = _make_tracker()
    start = time.perf_counter()
    for i in range(num_tasks):
        agent = AGENTS[i % len(AGENTS)]
        tracker.record_task_tokens(f"seq-{i:05d}", agent, 1000, 500, cost_usd=0.05)
    elapsed = time.perf_counter() - start

    stats = tracker.get_stats()
    return {
        "scenario": "sustained_sequential",
        "num_tasks": num_tasks,
        "elapsed_s": elapsed,
        "tasks_per_sec": num_tasks / elapsed,
        "recorded_tasks": stats.task_count,
        "data_loss": num_tasks - stats.task_count,
    }


def load_test_budget_checker_concurrent(num_threads: int = 50, checks_per_thread: int = 20) -> dict:
    """
    Concurrent budget checks from many threads (simulates orchestrator checking
    budget status for many simultaneous tasks).
    """
    tracker = _make_tracker()
    checker = BudgetChecker()
    # Pre-populate some spend
    for i in range(20):
        tracker.record_task_tokens(f"pre-{i}", "engineer", 1000, 500, cost_usd=0.05)

    errors = []
    results = []
    lock = threading.Lock()

    def check_worker():
        for _ in range(checks_per_thread):
            try:
                stats = tracker.get_stats()
                result = checker.check(stats)
                with lock:
                    results.append(result.status.value)
            except Exception as e:
                with lock:
                    errors.append(str(e))

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=num_threads) as pool:
        futures = [pool.submit(check_worker) for _ in range(num_threads)]
        for f in as_completed(futures):
            f.result()
    elapsed = time.perf_counter() - start

    total_checks = num_threads * checks_per_thread
    return {
        "scenario": "budget_checker_concurrent",
        "num_threads": num_threads,
        "total_checks": total_checks,
        "elapsed_s": elapsed,
        "checks_per_sec": total_checks / elapsed,
        "errors": errors,
        "completed_checks": len(results),
    }


def load_test_model_selector_concurrent(num_threads: int = 50, selects_per_thread: int = 50) -> dict:
    """
    Concurrent model selection — ComplexityScorer + ModelSelector under load.
    """
    selector = ModelSelector()
    attrs = _make_attrs()
    errors = []
    results = []
    lock = threading.Lock()

    def select_worker():
        for _ in range(selects_per_thread):
            try:
                decision = selector.select(attrs)
                with lock:
                    results.append(decision.model)
            except Exception as e:
                with lock:
                    errors.append(str(e))

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=num_threads) as pool:
        futures = [pool.submit(select_worker) for _ in range(num_threads)]
        for f in as_completed(futures):
            f.result()
    elapsed = time.perf_counter() - start

    total = num_threads * selects_per_thread
    return {
        "scenario": "model_selector_concurrent",
        "num_threads": num_threads,
        "total_selects": total,
        "elapsed_s": elapsed,
        "selects_per_sec": total / elapsed,
        "errors": errors,
        "completed": len(results),
    }


# ---------------------------------------------------------------------------
# pytest test functions
# ---------------------------------------------------------------------------

def test_50_concurrent_agents_no_data_loss():
    """50 concurrent agents recording tokens — zero data loss required."""
    r = load_test_concurrent_token_recording(num_agents=50, tasks_per_agent=10)
    assert r["errors"] == [], f"Errors during load: {r['errors']}"
    assert r["data_loss"] == 0, f"Data loss: {r['data_loss']} tasks not recorded"
    assert r["tasks_per_sec"] > 100, f"Throughput too low: {r['tasks_per_sec']:.0f} tasks/s"


def test_100_concurrent_agents_no_data_loss():
    """100 concurrent agents recording tokens — zero data loss required."""
    r = load_test_concurrent_token_recording(num_agents=100, tasks_per_agent=5)
    assert r["errors"] == [], f"Errors during load: {r['errors']}"
    assert r["data_loss"] == 0, f"Data loss: {r['data_loss']} tasks not recorded"
    assert r["tasks_per_sec"] > 100, f"Throughput too low: {r['tasks_per_sec']:.0f} tasks/s"


def test_mixed_read_write_no_errors():
    """Concurrent readers and writers produce no errors or deadlocks."""
    r = load_test_mixed_read_write(num_writers=20, num_readers=10, duration_s=1.0)
    assert r["errors"] == [], f"Errors during mixed load: {r['errors']}"
    assert r["total_writes"] > 0, "No writes completed"
    assert r["total_reads"] > 0, "No reads completed"
    assert r["write_throughput"] > 50, f"Write throughput too low: {r['write_throughput']:.0f}/s"


def test_sustained_sequential_500_tasks():
    """500 sequential tasks complete with zero data loss."""
    r = load_test_sustained_sequential(num_tasks=500)
    assert r["data_loss"] == 0, f"Data loss: {r['data_loss']} tasks"
    assert r["tasks_per_sec"] > 500, f"Sequential throughput too low: {r['tasks_per_sec']:.0f} tasks/s"


def test_budget_checker_50_concurrent_threads():
    """50 threads checking budget concurrently — no errors."""
    r = load_test_budget_checker_concurrent(num_threads=50, checks_per_thread=20)
    assert r["errors"] == [], f"Errors: {r['errors']}"
    assert r["completed_checks"] == r["total_checks"], (
        f"Missing checks: {r['total_checks'] - r['completed_checks']}"
    )
    assert r["checks_per_sec"] > 500, f"Budget check throughput too low: {r['checks_per_sec']:.0f}/s"


def test_model_selector_50_concurrent_threads():
    """50 threads selecting models concurrently — no errors, consistent results."""
    r = load_test_model_selector_concurrent(num_threads=50, selects_per_thread=50)
    assert r["errors"] == [], f"Errors: {r['errors']}"
    assert r["completed"] == r["total_selects"], (
        f"Missing selects: {r['total_selects'] - r['completed']}"
    )
    assert r["selects_per_sec"] > 1000, f"Model selection throughput too low: {r['selects_per_sec']:.0f}/s"


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

def print_result(r: dict) -> None:
    scenario = r.get("scenario", "unknown")
    errors = r.get("errors", [])
    status = "✓" if not errors else f"✗ ({len(errors)} errors)"
    print(f"\n  [{status}] {scenario}")
    for k, v in r.items():
        if k in ("scenario", "errors"):
            continue
        if isinstance(v, float):
            print(f"      {k}: {v:.2f}")
        else:
            print(f"      {k}: {v}")
    if errors:
        for e in errors[:5]:
            print(f"      ERROR: {e}")


if __name__ == "__main__":
    print("\n=== Phase 3 Load Tests ===")

    scenarios = [
        lambda: load_test_concurrent_token_recording(50, 10),
        lambda: load_test_concurrent_token_recording(100, 5),
        lambda: load_test_mixed_read_write(20, 10, 2.0),
        lambda: load_test_sustained_sequential(500),
        lambda: load_test_budget_checker_concurrent(50, 20),
        lambda: load_test_model_selector_concurrent(50, 50),
    ]

    all_passed = True
    for fn in scenarios:
        r = fn()
        print_result(r)
        if r.get("errors"):
            all_passed = False
        if r.get("data_loss", 0) > 0:
            all_passed = False

    print()
    if all_passed:
        print("All load tests passed. ✓")
    else:
        print("Some load tests FAILED. ✗")
        sys.exit(1)
