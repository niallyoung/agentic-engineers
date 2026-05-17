"""
BudgetChecker Usage Examples

Demonstrates practical usage patterns for the BudgetChecker class.
"""

import sys
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestration.monitoring import BudgetChecker, BudgetStatus
from src.orchestration.monitoring.token_tracker import TokenStats


def example_basic_usage():
    """Basic usage: Check budget status."""
    print("=" * 60)
    print("Example 1: Basic Budget Check")
    print("=" * 60)
    
    # Create a budget checker with default config
    checker = BudgetChecker()
    
    # Create token stats (simulating task execution)
    stats = TokenStats(total_cost_usd=2.50)
    
    # Check budget
    result = checker.check(stats)
    
    print(f"Status: {result.status.value}")
    print(f"Cost: ${result.pct_used:.1f}% of ${result.budget_usd:.2f}")
    print(f"Remaining: ${result.remaining_usd:.2f}")
    print(f"Message: {result.message}")
    print()


def example_blocking_decision():
    """Decision making: Should we block new tasks?"""
    print("=" * 60)
    print("Example 2: Blocking Decision")
    print("=" * 60)
    
    checker = BudgetChecker()
    
    # Simulate spending approaching budget limit
    costs = [1.0, 2.0, 3.5, 4.5, 5.0, 5.5]
    
    for cost in costs:
        stats = TokenStats(total_cost_usd=cost)
        result = checker.check(stats)
        
        if checker.should_block(stats):
            print(f"✗ BLOCKED: ${cost:.2f} - {result.message}")
        elif result.status == BudgetStatus.CRITICAL:
            print(f"⚠ CRITICAL: ${cost:.2f} - {result.message}")
        elif result.status == BudgetStatus.WARNING:
            print(f"⚠ WARNING: ${cost:.2f} - {result.message}")
        else:
            print(f"✓ OK: ${cost:.2f} - {result.message}")
    print()


def example_custom_config():
    """Custom configuration: Load from YAML file."""
    print("=" * 60)
    print("Example 3: Custom Configuration")
    print("=" * 60)
    
    # Load config from file (if it exists)
    config_path = Path("config/token_budget.yaml")
    checker = BudgetChecker(config_path=config_path)
    
    print(f"Budget Config:")
    print(f"  Session Limit: ${checker.budget_config['session_usd']:.2f}")
    print(f"  Daily Limit: ${checker.budget_config['daily_usd']:.2f}")
    print(f"  Warning Threshold: {checker.budget_config['warn_pct']}%")
    print(f"  Critical Threshold: {checker.budget_config['critical_pct']}%")
    print(f"  Block Threshold: {checker.budget_config['block_pct']}%")
    print()
    
    print(f"Display Config:")
    print(f"  Mode: {checker.display_config['mode']}")
    print(f"  Show Per-Task: {checker.display_config['show_per_task']}")
    print(f"  Show Session Summary: {checker.display_config['show_session_summary']}")
    print()


def example_multi_agent_tracking():
    """Multi-agent: Track budget across multiple agents."""
    print("=" * 60)
    print("Example 4: Multi-Agent Budget Tracking")
    print("=" * 60)
    
    checker = BudgetChecker()
    
    # Simulate multiple agents contributing to cost
    stats = TokenStats(
        total_cost_usd=3.75,
        task_count=4,
        agent_tokens={
            "engineer": 2500,
            "orchestrator": 1500,
            "quality-engineer": 1000,
        },
        agent_costs={
            "engineer": 2.00,
            "orchestrator": 1.25,
            "quality-engineer": 0.50,
        },
        agent_counts={
            "engineer": 2,
            "orchestrator": 1,
            "quality-engineer": 1,
        },
    )
    
    result = checker.check(stats)
    
    print(f"Overall Status: {result.status.value}")
    print(f"Total Cost: ${stats.total_cost_usd:.2f} ({result.pct_used:.1f}%)")
    print(f"Tasks: {stats.task_count}")
    print()
    print("Per-Agent Breakdown:")
    for agent in sorted(stats.agent_costs.keys()):
        cost = stats.agent_costs[agent]
        count = stats.agent_counts[agent]
        avg_cost = cost / count if count > 0 else 0
        print(f"  {agent:20s}: ${cost:6.2f} ({count} tasks, avg ${avg_cost:.2f}/task)")
    print()


def example_session_lifecycle():
    """Session lifecycle: Track budget through a full session."""
    print("=" * 60)
    print("Example 5: Session Lifecycle")
    print("=" * 60)
    
    checker = BudgetChecker()
    
    # Simulate task execution throughout a session
    tasks = [
        ("task-1", 0.50),
        ("task-2", 0.75),
        ("task-3", 1.25),
        ("task-4", 1.50),
        ("task-5", 0.75),
    ]
    
    cumulative_cost = 0.0
    
    print("Task Execution:")
    for task_id, cost in tasks:
        cumulative_cost += cost
        stats = TokenStats(total_cost_usd=cumulative_cost)
        result = checker.check(stats)
        
        status_symbol = {
            BudgetStatus.OK: "✓",
            BudgetStatus.WARNING: "⚠",
            BudgetStatus.CRITICAL: "⚠⚠",
            BudgetStatus.BLOCKED: "✗",
        }[result.status]
        
        print(f"  {status_symbol} {task_id:10s}: ${cost:5.2f} → Total: ${cumulative_cost:5.2f} "
              f"({result.pct_used:5.1f}%) - {result.status.value}")
    
    print()
    print(f"Session Summary:")
    print(f"  Total Cost: ${cumulative_cost:.2f}")
    print(f"  Budget Used: {result.pct_used:.1f}%")
    print(f"  Remaining: ${result.remaining_usd:.2f}")
    print(f"  Final Status: {result.status.value}")
    print()


def example_threshold_monitoring():
    """Monitoring: Track status changes as budget increases."""
    print("=" * 60)
    print("Example 6: Threshold Monitoring")
    print("=" * 60)
    
    checker = BudgetChecker()
    
    print("Budget Thresholds:")
    print(f"  OK:       0% - {checker.budget_config['warn_pct']-1}%")
    print(f"  WARNING:  {checker.budget_config['warn_pct']}% - {checker.budget_config['critical_pct']-1}%")
    print(f"  CRITICAL: {checker.budget_config['critical_pct']}% - {checker.budget_config['block_pct']-1}%")
    print(f"  BLOCKED:  {checker.budget_config['block_pct']}%+")
    print()
    
    # Test each threshold
    test_percentages = [0, 50, 70, 80, 90, 95, 100, 110]
    budget = checker.budget_config['session_usd']
    
    print("Threshold Testing:")
    for pct in test_percentages:
        cost = (pct / 100.0) * budget
        stats = TokenStats(total_cost_usd=cost)
        result = checker.check(stats)
        
        print(f"  {pct:3d}% (${cost:5.2f}): {result.status.value:8s} - {result.message}")
    print()


if __name__ == "__main__":
    example_basic_usage()
    example_blocking_decision()
    example_custom_config()
    example_multi_agent_tracking()
    example_session_lifecycle()
    example_threshold_monitoring()
    
    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)
