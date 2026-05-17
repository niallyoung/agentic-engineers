"""
OrchestratorCLI Usage Examples

Demonstrates how to integrate OrchestratorCLI into the Orchestrator
for token tracking, budget enforcement, and formatted output.
"""

from pathlib import Path
from src.orchestration.monitoring.orchestrator_cli import OrchestratorCLI
from src.orchestration.monitoring.token_tracker import TokenTracker
from src.orchestration.monitoring.metrics import MetricsRegistry
from src.orchestration.monitoring.budget_checker import BudgetStatus, BudgetResult


# ===========================================================================
# Example 1: Basic Usage with Default Budget
# ===========================================================================

def example_basic_usage():
    """
    Basic usage: Initialize OrchestratorCLI and track tasks.
    Uses default budget ($5.00 per session).
    """
    print("=" * 70)
    print("Example 1: Basic Usage with Default Budget")
    print("=" * 70)
    
    # Initialize components
    registry = MetricsRegistry()
    tracker = TokenTracker(registry)
    cli = OrchestratorCLI(token_tracker=tracker)
    
    # Simulate task completion
    delegate = {
        "task_id": "task-001",
        "role": "engineer",
        "model": "claude-haiku-4-5",
        "effort": "high",
    }
    
    handback = {
        "task_id": "task-001",
        "status": "complete",
        "tokens_in": 1000,
        "tokens_out": 500,
        "cached_tokens": 100,
        "cost_usd": 0.05,
    }
    
    # Record task completion
    print("\nRecording task completion...")
    cli.on_task_complete(delegate, handback)
    
    # Check budget status
    budget_result = cli.get_budget_status()
    print(f"\nBudget Status: {budget_result}")
    
    # Print session summary
    print("\nSession Summary:")
    cli.print_session_summary()


# ===========================================================================
# Example 2: Custom Budget Configuration
# ===========================================================================

def example_custom_budget():
    """
    Custom budget configuration: Load budget limits from YAML file.
    """
    print("\n" + "=" * 70)
    print("Example 2: Custom Budget Configuration")
    print("=" * 70)
    
    # Create a custom budget config
    config_path = Path("/tmp/token_budget.yaml")
    config_path.write_text("""
budget:
  session_usd: 10.0
  daily_usd: 50.0
  warn_pct: 60
  critical_pct: 80
  block_pct: 100
display:
  mode: compact
  show_per_task: true
  show_session_summary: true
""")
    
    # Initialize with custom config
    registry = MetricsRegistry()
    tracker = TokenTracker(registry)
    cli = OrchestratorCLI(
        token_tracker=tracker,
        budget_config_path=config_path,
    )
    
    # Record a task that uses 65% of custom budget
    delegate = {"task_id": "task-001", "role": "engineer"}
    handback = {
        "task_id": "task-001",
        "status": "complete",
        "tokens_in": 5000,
        "tokens_out": 2500,
        "cost_usd": 6.5,  # 65% of $10.00 budget → WARNING
    }
    
    print("\nRecording task with custom budget ($10.00)...")
    cli.on_task_complete(delegate, handback)
    
    budget_result = cli.get_budget_status()
    print(f"\nBudget Status: {budget_result}")
    print(f"Status: {budget_result.status.value}")


# ===========================================================================
# Example 3: Budget Callback Handling
# ===========================================================================

def example_budget_callback():
    """
    Budget callback: Handle budget threshold events with custom logic.
    """
    print("\n" + "=" * 70)
    print("Example 3: Budget Callback Handling")
    print("=" * 70)
    
    def on_budget_exceeded(result: BudgetResult):
        """Custom callback for budget threshold events."""
        if result.status == BudgetStatus.WARNING:
            print(f"⚠️  WARNING: Budget at {result.pct_used:.1f}%")
            print(f"   Remaining: ${result.remaining_usd:.2f}")
        elif result.status == BudgetStatus.CRITICAL:
            print(f"🚨 CRITICAL: Budget at {result.pct_used:.1f}%")
            print(f"   Remaining: ${result.remaining_usd:.2f}")
            print("   Consider pausing new tasks")
        elif result.status == BudgetStatus.BLOCKED:
            print(f"🛑 BLOCKED: Budget exhausted")
            print("   No new tasks will be accepted")
    
    # Initialize with callback
    registry = MetricsRegistry()
    tracker = TokenTracker(registry)
    cli = OrchestratorCLI(
        token_tracker=tracker,
        on_budget_exceeded=on_budget_exceeded,
    )
    
    # Record tasks that trigger different thresholds
    print("\nRecording tasks with budget escalation...")
    
    # Task 1: OK (20% of budget)
    cli.on_task_complete(
        {"task_id": "task-001", "role": "engineer"},
        {"task_id": "task-001", "status": "complete", "cost_usd": 1.0},
    )
    
    # Task 2: WARNING (75% of budget)
    cli.on_task_complete(
        {"task_id": "task-002", "role": "engineer"},
        {"task_id": "task-002", "status": "complete", "cost_usd": 2.75},
    )
    
    # Task 3: CRITICAL (95% of budget)
    cli.on_task_complete(
        {"task_id": "task-003", "role": "engineer"},
        {"task_id": "task-003", "status": "complete", "cost_usd": 0.95},
    )


# ===========================================================================
# Example 4: Session Lifecycle Management
# ===========================================================================

def example_session_lifecycle():
    """
    Session lifecycle: Initialize, track tasks, print summary, reset.
    """
    print("\n" + "=" * 70)
    print("Example 4: Session Lifecycle Management")
    print("=" * 70)
    
    registry = MetricsRegistry()
    tracker = TokenTracker(registry)
    cli = OrchestratorCLI(token_tracker=tracker)
    
    # Session 1: Multiple tasks
    print("\n--- Session 1 ---")
    for i in range(3):
        delegate = {"task_id": f"task-{i:03d}", "role": "engineer"}
        handback = {
            "task_id": f"task-{i:03d}",
            "status": "complete",
            "tokens_in": 1000,
            "tokens_out": 500,
            "cost_usd": 0.05,
        }
        cli.on_task_complete(delegate, handback)
    
    print("\nSession 1 Summary:")
    cli.print_session_summary()
    
    # Reset for new session
    print("\n--- Resetting for Session 2 ---")
    cli.reset_session()
    
    # Session 2: New tasks
    print("\n--- Session 2 ---")
    for i in range(2):
        delegate = {"task_id": f"task-{100+i:03d}", "role": "orchestrator"}
        handback = {
            "task_id": f"task-{100+i:03d}",
            "status": "complete",
            "tokens_in": 500,
            "tokens_out": 250,
            "cost_usd": 0.025,
        }
        cli.on_task_complete(delegate, handback)
    
    print("\nSession 2 Summary:")
    cli.print_session_summary()


# ===========================================================================
# Example 5: No-Color Mode (for CI/CD)
# ===========================================================================

def example_no_color_mode():
    """
    No-color mode: Disable ANSI colors for CI/CD environments.
    """
    print("\n" + "=" * 70)
    print("Example 5: No-Color Mode (for CI/CD)")
    print("=" * 70)
    
    registry = MetricsRegistry()
    tracker = TokenTracker(registry)
    
    # Initialize with no_color=True
    cli = OrchestratorCLI(token_tracker=tracker, no_color=True)
    
    print("\nRecording tasks with no-color mode...")
    
    delegate = {"task_id": "task-001", "role": "engineer"}
    handback = {
        "task_id": "task-001",
        "status": "complete",
        "tokens_in": 1000,
        "tokens_out": 500,
        "cost_usd": 0.05,
    }
    
    cli.on_task_complete(delegate, handback)
    
    print("\nSession Summary (no ANSI colors):")
    cli.print_session_summary()


# ===========================================================================
# Example 6: Task Blocking Decision
# ===========================================================================

def example_task_blocking():
    """
    Task blocking: Check if new tasks should be blocked due to budget.
    """
    print("\n" + "=" * 70)
    print("Example 6: Task Blocking Decision")
    print("=" * 70)
    
    registry = MetricsRegistry()
    tracker = TokenTracker(registry)
    cli = OrchestratorCLI(token_tracker=tracker)
    
    print("\nSimulating budget exhaustion...")
    
    # Record tasks until budget is exhausted
    for i in range(100):
        delegate = {"task_id": f"task-{i:03d}", "role": "engineer"}
        handback = {
            "task_id": f"task-{i:03d}",
            "status": "complete",
            "tokens_in": 1000,
            "tokens_out": 500,
            "cost_usd": 0.06,  # Each task uses 6% of budget
        }
        
        cli.on_task_complete(delegate, handback)
        
        # Check if new tasks should be blocked
        if cli.should_block_new_tasks():
            print(f"\n✓ Task blocking activated after {i+1} tasks")
            print(f"  Budget status: {cli.get_budget_status()}")
            break
    
    print("\nFinal session summary:")
    cli.print_session_summary()


# ===========================================================================
# Example 7: Integration with Orchestrator
# ===========================================================================

def example_orchestrator_integration():
    """
    Orchestrator integration: How OrchestratorCLI fits into the workflow.
    """
    print("\n" + "=" * 70)
    print("Example 7: Orchestrator Integration Pattern")
    print("=" * 70)
    
    print("""
    Typical Orchestrator workflow with OrchestratorCLI:
    
    1. Initialize at session start:
       registry = MetricsRegistry()
       tracker = TokenTracker(registry)
       cli = OrchestratorCLI(
           token_tracker=tracker,
           budget_config_path=Path("config/token_budget.yaml"),
           on_budget_exceeded=handle_budget_alert,
       )
    
    2. For each task in queue:
       delegate = queue.pop()
       handback = invoke_agent(delegate)
       
       # Record metrics and check budget
       cli.on_task_complete(delegate, handback)
       
       # Check if new tasks should be blocked
       if cli.should_block_new_tasks():
           queue.pause()
    
    3. At session end:
       cli.print_session_summary()
       cli.reset_session()
    
    Benefits:
    - Unified entry point for token tracking
    - Automatic budget enforcement
    - Formatted console output
    - Task blocking decisions
    - Session lifecycle management
    """)


# ===========================================================================
# Example 8: Agent Statistics and Attribution
# ===========================================================================

def example_agent_statistics():
    """
    Agent statistics: Get per-agent token usage and cost attribution.
    """
    print("\n" + "=" * 70)
    print("Example 8: Agent Statistics and Attribution")
    print("=" * 70)
    
    registry = MetricsRegistry()
    tracker = TokenTracker(registry)
    cli = OrchestratorCLI(token_tracker=tracker)
    
    # Record tasks from different agents
    print("\nRecording tasks from different agents...")
    
    agents = ["engineer", "orchestrator", "quality-engineer"]
    for agent in agents:
        for i in range(3):
            delegate = {"task_id": f"{agent}-task-{i}", "role": agent}
            handback = {
                "task_id": f"{agent}-task-{i}",
                "status": "complete",
                "tokens_in": 1000,
                "tokens_out": 500,
                "cost_usd": 0.05,
            }
            cli.on_task_complete(delegate, handback)
    
    # Get statistics
    stats = cli.get_session_stats()
    
    print(f"\nTotal tasks: {stats.task_count}")
    print(f"Total cost: ${stats.total_cost_usd:.2f}")
    print(f"Total tokens: {stats.effective_tokens:,}")
    
    print("\nPer-agent breakdown:")
    for agent in sorted(stats.agent_tokens.keys()):
        tokens = stats.agent_tokens[agent]
        cost = stats.agent_costs[agent]
        count = stats.agent_counts[agent]
        pct = (tokens / stats.effective_tokens * 100) if stats.effective_tokens > 0 else 0
        print(f"  {agent:20} {tokens:6,} tokens ({pct:5.1f}%) ${cost:.2f} ({count} tasks)")


if __name__ == "__main__":
    # Run all examples
    example_basic_usage()
    example_custom_budget()
    example_budget_callback()
    example_session_lifecycle()
    example_no_color_mode()
    example_task_blocking()
    example_orchestrator_integration()
    example_agent_statistics()
    
    print("\n" + "=" * 70)
    print("All examples completed successfully!")
    print("=" * 70)
