"""
TokenTracker Usage Examples and Integration Guide

This module demonstrates how to use the TokenTracker class to monitor
token consumption and cost attribution across agents.
"""

from src.orchestration.monitoring.metrics import MetricsRegistry
from src.orchestration.monitoring.token_tracker import TokenTracker
from src.orchestration.monitoring.prometheus_exporter import PrometheusExporter


# ===========================================================================
# Example 1: Basic Token Recording
# ===========================================================================

def example_basic_recording():
    """Record token metrics for a single task."""
    registry = MetricsRegistry()
    tracker = TokenTracker(registry)
    
    # Record a task executed by the engineer agent
    tracker.record_task_tokens(
        task_id="task-2026-06-02-001",
        agent="engineer",
        input_tokens=1000,
        output_tokens=500,
        cached_tokens=100,
        cost_usd=0.045,
    )
    
    # Get aggregated statistics
    stats = tracker.get_stats()
    print(f"Total tokens: {stats.total_tokens}")
    print(f"Total cost: ${stats.total_cost_usd:.4f}")
    print(f"Tasks processed: {stats.task_count}")


# ===========================================================================
# Example 2: Multi-Agent Task Tracking
# ===========================================================================

def example_multi_agent_tracking():
    """Track tokens across multiple agents."""
    registry = MetricsRegistry()
    tracker = TokenTracker(registry)
    
    # Engineer task
    tracker.record_task_tokens(
        task_id="task-001",
        agent="engineer",
        input_tokens=1000,
        output_tokens=500,
        cost_usd=0.045,
    )
    
    # Senior engineer task
    tracker.record_task_tokens(
        task_id="task-002",
        agent="senior_engineer",
        input_tokens=2000,
        output_tokens=1000,
        cost_usd=0.090,
    )
    
    # Lead engineer task
    tracker.record_task_tokens(
        task_id="task-003",
        agent="lead_engineer",
        input_tokens=3000,
        output_tokens=1500,
        cost_usd=0.135,
    )
    
    # Get per-agent statistics
    for agent in ["engineer", "senior_engineer", "lead_engineer"]:
        stats = tracker.get_agent_stats(agent)
        if stats:
            print(f"\n{agent}:")
            print(f"  Tokens: {stats['effective_tokens']}")
            print(f"  Cost: ${stats['cost_usd']:.4f}")
            print(f"  Tasks: {stats['task_count']}")
            print(f"  Avg tokens/task: {stats['avg_tokens_per_task']:.0f}")


# ===========================================================================
# Example 3: Cost Attribution Analysis
# ===========================================================================

def example_cost_attribution():
    """Analyze cost attribution by agent."""
    registry = MetricsRegistry()
    tracker = TokenTracker(registry)
    
    # Record tasks from different agents
    tracker.record_task_tokens(
        task_id="task-001",
        agent="engineer",
        input_tokens=1000,
        output_tokens=500,
        cost_usd=0.045,
    )
    tracker.record_task_tokens(
        task_id="task-002",
        agent="senior_engineer",
        input_tokens=2000,
        output_tokens=1000,
        cost_usd=0.090,
    )
    
    # Get cost attribution
    attribution = tracker.get_cost_attribution()
    
    print("\nCost Attribution Analysis:")
    print("-" * 60)
    for agent, data in attribution.items():
        print(f"\n{agent}:")
        print(f"  Tokens: {data['tokens']:,}")
        print(f"  Cost: ${data['cost']:.4f}")
        print(f"  Token Share: {data['token_percentage']:.1f}%")
        print(f"  Cost Share: {data['cost_percentage']:.1f}%")


# ===========================================================================
# Example 4: Prometheus Export
# ===========================================================================

def example_prometheus_export():
    """Export metrics in Prometheus format."""
    registry = MetricsRegistry()
    tracker = TokenTracker(registry)
    
    # Record some tasks
    tracker.record_task_tokens(
        task_id="task-001",
        agent="engineer",
        input_tokens=1000,
        output_tokens=500,
        cost_usd=0.045,
    )
    tracker.record_task_tokens(
        task_id="task-002",
        agent="senior_engineer",
        input_tokens=2000,
        output_tokens=1000,
        cost_usd=0.090,
    )
    
    # Export to Prometheus format
    exporter = PrometheusExporter(registry)
    prometheus_text = exporter.export()
    
    print("Prometheus Metrics:")
    print("-" * 60)
    print(prometheus_text)
    
    # Save to file for scraping
    exporter.export_to_file("/tmp/metrics.txt")


# ===========================================================================
# Example 5: Real-time Monitoring
# ===========================================================================

def example_real_time_monitoring():
    """Monitor token consumption in real-time."""
    registry = MetricsRegistry()
    tracker = TokenTracker(registry)
    
    # Simulate task execution
    tasks = [
        ("task-001", "engineer", 1000, 500, 0.045),
        ("task-002", "engineer", 1200, 600, 0.054),
        ("task-003", "senior_engineer", 2000, 1000, 0.090),
        ("task-004", "lead_engineer", 3000, 1500, 0.135),
    ]
    
    for task_id, agent, input_tokens, output_tokens, cost in tasks:
        tracker.record_task_tokens(
            task_id=task_id,
            agent=agent,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )
        
        # Print real-time stats
        stats = tracker.get_stats()
        print(f"\n[{task_id}] Task completed")
        print(f"  Running total: {stats.total_tokens:,} tokens, ${stats.total_cost_usd:.4f}")
        print(f"  Average cost/task: ${stats.avg_cost_per_task:.4f}")


# ===========================================================================
# Example 6: Integration with Orchestrator
# ===========================================================================

def example_orchestrator_integration():
    """
    Example of how to integrate TokenTracker with the Orchestrator.
    
    This shows the pattern for recording tokens when a task completes.
    """
    from src.orchestration.monitoring.metrics import create_orchestrator_metrics
    
    # Initialize monitoring system
    registry = MetricsRegistry()
    metrics = create_orchestrator_metrics(registry)
    tracker = TokenTracker(registry)
    
    # Simulate task execution and completion
    # In real orchestrator code, this would be called after task completion
    
    def on_task_completed(task_id: str, agent: str, handback: dict):
        """Called when a task completes and returns a HANDBACK."""
        
        # Extract token metrics from HANDBACK
        tokens = handback.get("tokens", {})
        input_tokens = tokens.get("input", 0)
        output_tokens = tokens.get("output", 0)
        cached_tokens = tokens.get("cached", 0)
        cost_usd = tokens.get("cost_usd", 0.0)
        
        # Record in tracker
        tracker.record_task_tokens(
            task_id=task_id,
            agent=agent,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            cost_usd=cost_usd,
        )
        
        # Update orchestrator metrics
        metrics["tokens_total"].inc(input_tokens + output_tokens)
        metrics["tasks_completed"].inc()
    
    # Simulate task completion
    handback = {
        "tokens": {
            "input": 1000,
            "output": 500,
            "cached": 100,
            "cost_usd": 0.045,
        }
    }
    on_task_completed("task-001", "engineer", handback)
    
    # Get stats
    stats = tracker.get_stats()
    print(f"\nOrchestrator Integration Example:")
    print(f"  Total tokens: {stats.total_tokens:,}")
    print(f"  Total cost: ${stats.total_cost_usd:.4f}")
    print(f"  Tasks completed: {stats.task_count}")


# ===========================================================================
# Example 7: Budget Tracking
# ===========================================================================

def example_budget_tracking():
    """Track token consumption against a budget."""
    registry = MetricsRegistry()
    tracker = TokenTracker(registry)
    
    # Set a budget limit
    BUDGET_LIMIT = 100000  # 100k tokens
    
    # Simulate task execution
    tasks = [
        ("task-001", "engineer", 10000, 5000),
        ("task-002", "engineer", 12000, 6000),
        ("task-003", "senior_engineer", 20000, 10000),
        ("task-004", "lead_engineer", 30000, 15000),
    ]
    
    for task_id, agent, input_tokens, output_tokens in tasks:
        tracker.record_task_tokens(
            task_id=task_id,
            agent=agent,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=0.0,  # Cost calculation omitted for simplicity
        )
        
        stats = tracker.get_stats()
        used = stats.effective_tokens
        remaining = BUDGET_LIMIT - used
        pct_used = (used / BUDGET_LIMIT) * 100
        
        print(f"\n{task_id}: {used:,}/{BUDGET_LIMIT:,} tokens ({pct_used:.1f}%)")
        if remaining < 0:
            print(f"  ⚠️  BUDGET EXCEEDED by {abs(remaining):,} tokens")
        elif remaining < BUDGET_LIMIT * 0.1:
            print(f"  ⚠️  WARNING: Only {remaining:,} tokens remaining (10%)")
        else:
            print(f"  ✓ {remaining:,} tokens remaining")


# ===========================================================================
# Example 8: Agent Performance Comparison
# ===========================================================================

def example_agent_performance():
    """Compare performance metrics across agents."""
    registry = MetricsRegistry()
    tracker = TokenTracker(registry)
    
    # Record tasks from different agents
    agents_data = {
        "engineer": [
            (1000, 500, 0.045),
            (1200, 600, 0.054),
            (1100, 550, 0.0495),
        ],
        "senior_engineer": [
            (2000, 1000, 0.090),
            (2200, 1100, 0.099),
        ],
        "lead_engineer": [
            (3000, 1500, 0.135),
        ],
    }
    
    task_id = 0
    for agent, tasks in agents_data.items():
        for input_tokens, output_tokens, cost in tasks:
            task_id += 1
            tracker.record_task_tokens(
                task_id=f"task-{task_id:03d}",
                agent=agent,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
            )
    
    # Compare agents
    print("\nAgent Performance Comparison:")
    print("-" * 70)
    print(f"{'Agent':<20} {'Tokens':<12} {'Cost':<12} {'Avg/Task':<12} {'Tasks':<8}")
    print("-" * 70)
    
    for agent in agents_data.keys():
        stats = tracker.get_agent_stats(agent)
        if stats:
            print(
                f"{agent:<20} {stats['effective_tokens']:<12,} "
                f"${stats['cost_usd']:<11.4f} "
                f"${stats['avg_cost_per_task']:<11.4f} "
                f"{stats['task_count']:<8}"
            )


if __name__ == "__main__":
    print("=" * 70)
    print("TokenTracker Usage Examples")
    print("=" * 70)
    
    print("\n\n1. Basic Token Recording")
    print("=" * 70)
    example_basic_recording()
    
    print("\n\n2. Multi-Agent Tracking")
    print("=" * 70)
    example_multi_agent_tracking()
    
    print("\n\n3. Cost Attribution Analysis")
    print("=" * 70)
    example_cost_attribution()
    
    print("\n\n4. Prometheus Export")
    print("=" * 70)
    example_prometheus_export()
    
    print("\n\n5. Real-time Monitoring")
    print("=" * 70)
    example_real_time_monitoring()
    
    print("\n\n6. Orchestrator Integration")
    print("=" * 70)
    example_orchestrator_integration()
    
    print("\n\n7. Budget Tracking")
    print("=" * 70)
    example_budget_tracking()
    
    print("\n\n8. Agent Performance Comparison")
    print("=" * 70)
    example_agent_performance()
