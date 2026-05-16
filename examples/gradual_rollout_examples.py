"""
Gradual Rollout — Example Script.

Demonstrates:
1. Basic rollout setup and traffic routing
2. Health check evaluation and auto-advance
3. Manual controls (pause, resume, rollback, override)
4. Automatic rollback on threshold breach
5. Audit trail inspection
6. Environment variable configuration
7. Integration pattern with dry-run / shadow mode

Run:
    python examples/gradual_rollout_examples.py
"""

import os
import sys
import time
import random
import tempfile
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestration.agents.gradual_rollout import (
    RolloutStage,
    RolloutManager,
    RolloutConfig,
    TrafficSampler,
    create_rollout_manager,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def separator(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def simulate_task(task_id: str, *, error_rate: float = 0.02, base_quality: float = 0.92) -> dict:
    """Simulate a task outcome."""
    error = random.random() < error_rate
    quality = 0.0 if error else base_quality + random.uniform(-0.05, 0.05)
    latency = random.uniform(80, 200) if not error else random.uniform(500, 2000)
    return {"error": error, "quality_score": max(0.0, min(1.0, quality)), "latency_ms": latency}


# ---------------------------------------------------------------------------
# Example 1: Basic routing
# ---------------------------------------------------------------------------

def example_basic_routing(audit_dir: str) -> None:
    separator("Example 1: Basic Traffic Routing")

    manager = create_rollout_manager(stage=10, audit_dir=audit_dir)
    print(f"Stage: {manager.stage.name} ({manager.stage.value}% traffic)")

    sampled_count = 0
    total = 50
    for i in range(total):
        task_id = f"task-{i:04d}"
        if manager.should_use_new_path(task_id):
            sampled_count += 1

    print(f"Tasks routed to new path: {sampled_count}/{total} ({sampled_count/total*100:.1f}%)")
    print(f"Expected: ~10%  Actual: {sampled_count/total*100:.1f}%")

    # Determinism check
    task_id = "stable-task-xyz"
    results = [manager.should_use_new_path(task_id) for _ in range(5)]
    print(f"\nDeterminism check for '{task_id}': {results}")
    print(f"All same? {len(set(results)) == 1}")


# ---------------------------------------------------------------------------
# Example 2: Health checks and auto-advance
# ---------------------------------------------------------------------------

def example_health_and_advance(audit_dir: str) -> None:
    separator("Example 2: Health Checks and Auto-Advance")

    config = RolloutConfig(
        error_threshold=0.05,
        quality_min=0.80,
        min_samples=10,
        auto_advance=True,
        audit_dir=audit_dir,
    )
    manager = RolloutManager(config=config, initial_stage=RolloutStage.STAGE_10)
    print(f"Starting at: {manager.stage.name}")

    # Simulate 20 healthy tasks
    sampled = []
    for i in range(1000):
        tid = f"task-{i}"
        if manager.should_use_new_path(tid):
            sampled.append(tid)
        if len(sampled) >= 20:
            break

    print(f"\nSimulating {len(sampled)} tasks with healthy metrics...")
    for tid in sampled:
        outcome = simulate_task(tid, error_rate=0.02, base_quality=0.92)
        manager.record_outcome(tid, **outcome)

    health = manager.evaluate_health()
    print(f"\nHealth snapshot:")
    print(f"  Samples:       {health.total_samples}")
    print(f"  Error rate:    {health.error_rate:.1%}")
    print(f"  Quality score: {health.quality_score:.2f}")
    print(f"  Healthy:       {health.is_healthy}")

    new_stage = manager.evaluate_and_advance()
    if new_stage:
        print(f"\nAuto-advanced to: {new_stage.name}")
    else:
        print(f"\nNo advance (still at {manager.stage.name})")


# ---------------------------------------------------------------------------
# Example 3: Manual controls
# ---------------------------------------------------------------------------

def example_manual_controls(audit_dir: str) -> None:
    separator("Example 3: Manual Controls")

    manager = create_rollout_manager(stage=25, audit_dir=audit_dir)
    print(f"Starting at: {manager.stage.name}")

    # Pause
    manager.pause(operator="ops-team")
    print(f"\nPaused: {manager.is_paused}")

    # Resume
    manager.resume(operator="ops-team")
    print(f"Resumed: {not manager.is_paused}")

    # Manual advance
    new_stage = manager.advance(operator="ci-pipeline")
    print(f"\nManual advance → {new_stage.name}")

    # Override to specific stage
    manager.override_stage(RolloutStage.STAGE_75, operator="lead-engineer")
    print(f"Override → {manager.stage.name}")

    # Rollback
    prev = manager.rollback(operator="incident-response")
    print(f"Rollback → {prev.name}")

    # Disable
    manager.disable(operator="incident-response")
    print(f"Disabled → {manager.stage.name}")
    print(f"New path routing: {manager.should_use_new_path('any-task')}")


# ---------------------------------------------------------------------------
# Example 4: Automatic rollback on threshold breach
# ---------------------------------------------------------------------------

def example_auto_rollback(audit_dir: str) -> None:
    separator("Example 4: Automatic Rollback on Threshold Breach")

    config = RolloutConfig(
        error_threshold=0.05,
        quality_min=0.80,
        min_samples=10,
        audit_dir=audit_dir,
    )
    manager = RolloutManager(config=config, initial_stage=RolloutStage.STAGE_50)
    print(f"Starting at: {manager.stage.name}")

    # Simulate bad metrics (60% error rate)
    sampled = []
    for i in range(1000):
        tid = f"task-{i}"
        if manager.should_use_new_path(tid):
            sampled.append(tid)
        if len(sampled) >= 15:
            break

    print(f"\nSimulating {len(sampled)} tasks with BAD metrics (60% error rate)...")
    for tid in sampled:
        outcome = simulate_task(tid, error_rate=0.60, base_quality=0.40)
        manager.record_outcome(tid, **outcome)

    health_before = manager.evaluate_health()
    print(f"\nHealth before rollback check:")
    print(f"  Error rate: {health_before.error_rate:.1%} (threshold: 5%)")
    print(f"  Quality:    {health_before.quality_score:.2f} (min: 0.80)")
    print(f"  Healthy:    {health_before.is_healthy}")
    if health_before.failure_reasons:
        for r in health_before.failure_reasons:
            print(f"  ⚠️  {r}")

    manager._check_auto_rollback()
    print(f"\nAfter auto-rollback check: {manager.stage.name}")


# ---------------------------------------------------------------------------
# Example 5: Audit trail inspection
# ---------------------------------------------------------------------------

def example_audit_trail(audit_dir: str) -> None:
    separator("Example 5: Audit Trail")

    manager = create_rollout_manager(stage=10, audit_dir=audit_dir)
    manager.advance(operator="ci-pipeline")
    manager.pause(operator="ops-team")
    manager.resume(operator="ops-team")
    manager.rollback(operator="incident-response")

    trail = manager.get_audit_trail()
    print(f"Audit trail ({len(trail)} entries):\n")
    for entry in trail:
        print(f"  [{entry.timestamp[:19]}] {entry.action:10s} | {entry.reason:30s} | "
              f"{entry.from_stage:3d}→{entry.to_stage:3d} | op={entry.operator}")

    # Show persisted audit log
    log_file = Path(audit_dir) / "audit.jsonl"
    if log_file.exists():
        lines = log_file.read_text().strip().split("\n")
        print(f"\nPersisted {len(lines)} records to: {log_file}")


# ---------------------------------------------------------------------------
# Example 6: Full rollout simulation
# ---------------------------------------------------------------------------

def example_full_rollout_simulation(audit_dir: str) -> None:
    separator("Example 6: Full Rollout Simulation (DISABLED → STAGE_100)")

    config = RolloutConfig(
        error_threshold=0.05,
        quality_min=0.80,
        min_samples=10,
        auto_advance=True,
        audit_dir=audit_dir,
    )
    manager = RolloutManager(config=config, initial_stage=RolloutStage.DISABLED)
    print(f"Starting at: {manager.stage.name}\n")

    for stage in RolloutStage.progression():
        manager.advance(operator="ci-pipeline")
        print(f"Advanced to: {manager.stage.name}")

        # Simulate tasks at this stage
        sampled = []
        for i in range(2000):
            tid = f"stage-{stage.value}-task-{i}"
            if manager.should_use_new_path(tid):
                sampled.append(tid)
            if len(sampled) >= 15:
                break

        for tid in sampled:
            outcome = simulate_task(tid, error_rate=0.01, base_quality=0.93)
            manager.record_outcome(tid, **outcome)

        health = manager.evaluate_health()
        print(f"  Samples: {health.total_samples}, Error: {health.error_rate:.1%}, "
              f"Quality: {health.quality_score:.2f}, Healthy: {health.is_healthy}")

    print(f"\nFinal stage: {manager.stage.name}")
    status = manager.status()
    print(f"Status: enabled={status['enabled']}, paused={status['paused']}")


# ---------------------------------------------------------------------------
# Example 7: Integration with dry-run / shadow mode pattern
# ---------------------------------------------------------------------------

def example_integration_pattern(audit_dir: str) -> None:
    separator("Example 7: Integration Pattern")

    print("""
Pattern for integrating with dry-run and shadow mode:

    from src.orchestration.agents.gradual_rollout import RolloutManager
    from src.orchestration.dry_run import DryRunContext
    from src.orchestration.agents.shadow_mode import ShadowModeContext

    rollout = RolloutManager.from_env()

    def process_task(task_id: str, task: dict) -> dict:
        # 1. Check rollout stage
        use_new = rollout.should_use_new_path(task_id)

        # 2. Optionally wrap in dry-run for safety
        dry_run_enabled = os.environ.get("DRY_RUN", "false") == "true"

        try:
            if use_new:
                result = new_orchestrator_logic(task)
            else:
                result = old_orchestrator_logic(task)

            rollout.record_outcome(
                task_id,
                error=False,
                quality_score=result.get("quality_score", 1.0),
                latency_ms=result.get("latency_ms", 0.0),
            )
        except Exception as e:
            rollout.record_outcome(task_id, error=True, quality_score=0.0, latency_ms=0.0)
            raise

        # 3. Periodically evaluate and auto-advance
        rollout.evaluate_and_advance()

        return result

Environment variables for production deployment:
    ROLLOUT_ENABLED=true
    ROLLOUT_STAGE=10          # Start at 10%
    ROLLOUT_AUTO_ADVANCE=true
    ROLLOUT_ERROR_THRESHOLD=0.05
    ROLLOUT_QUALITY_MIN=0.80
    ROLLOUT_MIN_SAMPLES=100   # Higher in production
    ROLLOUT_AUDIT_DIR=/var/log/rollout
""")

    # Show env-based config
    with os.popen("env | grep ROLLOUT_ 2>/dev/null") as f:
        env_vars = f.read().strip()
    if env_vars:
        print("Current ROLLOUT_* environment variables:")
        print(env_vars)
    else:
        print("No ROLLOUT_* environment variables set (using defaults).")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as audit_dir:
        example_basic_routing(audit_dir)
        example_health_and_advance(audit_dir)
        example_manual_controls(audit_dir)
        example_auto_rollback(audit_dir)
        example_audit_trail(audit_dir)
        example_full_rollout_simulation(audit_dir)
        example_integration_pattern(audit_dir)

    print("\n✅ All examples completed successfully.")
