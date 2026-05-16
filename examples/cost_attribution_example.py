#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cost Attribution Integration Example

Demonstrates:
  1. Creating a CostAttributor
  2. Attributing costs to agents
  3. Aggregating by dimensions
  4. Recording to MetricsRegistry
  5. Retrieving aggregated costs
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestration.models.cost_attributor import CostAttributor
from src.orchestration.models.cost_attribution_metrics import CostAttributionMetrics
from src.orchestration.monitoring.metrics import MetricsRegistry, create_cost_metrics


def example_basic_attribution():
    """Example 1: Basic cost attribution."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Cost Attribution")
    print("="*70)
    
    attributor = CostAttributor()
    
    # Single agent task
    result = attributor.attribute_cost(
        task_id="task-001",
        agents=["engineer"],
        tokens_per_agent={"engineer": 5000},
        total_cost=0.15,
        roles_per_agent={"engineer": "engineer"},
        models_per_agent={"engineer": "haiku-4-5"},
        task_type="implementation",
    )
    
    print(result.summary())


def example_multi_agent_attribution():
    """Example 2: Multi-agent cost attribution."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Multi-Agent Cost Attribution")
    print("="*70)
    
    attributor = CostAttributor()
    
    # Multi-agent collaborative task
    result = attributor.attribute_cost(
        task_id="task-002",
        agents=["engineer", "senior_engineer", "quality_engineer"],
        tokens_per_agent={
            "engineer": 8000,
            "senior_engineer": 12000,
            "quality_engineer": 5000,
        },
        total_cost=0.60,
        roles_per_agent={
            "engineer": "engineer",
            "senior_engineer": "senior_engineer",
            "quality_engineer": "quality_engineer",
        },
        models_per_agent={
            "engineer": "haiku-4-5",
            "senior_engineer": "sonnet-4-6",
            "quality_engineer": "haiku-4-5",
        },
        task_type="implementation",
    )
    
    print(result.summary())


def example_aggregation():
    """Example 3: Cost aggregation by dimensions."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Cost Aggregation by Dimensions")
    print("="*70)
    
    attributor = CostAttributor()
    results = []
    
    # Simulate multiple tasks
    tasks = [
        ("task-001", ["engineer"], {"engineer": 5000}, 0.15, "implementation"),
        ("task-002", ["senior_engineer"], {"senior_engineer": 8000}, 0.40, "review"),
        ("task-003", ["engineer", "quality_engineer"],
         {"engineer": 6000, "quality_engineer": 4000}, 0.25, "implementation"),
        ("task-004", ["engineer"], {"engineer": 3000}, 0.10, "documentation"),
    ]
    
    for task_id, agents, tokens, cost, task_type in tasks:
        result = attributor.attribute_cost(
            task_id=task_id,
            agents=agents,
            tokens_per_agent=tokens,
            total_cost=cost,
            roles_per_agent={a: a for a in agents},
            models_per_agent={a: "haiku-4-5" for a in agents},
            task_type=task_type,
        )
        results.append(result)
    
    # Aggregate by role
    print("\nCosts by Role:")
    by_role = attributor.aggregate_by_role(results)
    for role, cost in sorted(by_role.items()):
        print(f"  {role:20s}: ${cost:.4f}")
    
    # Aggregate by task type
    print("\nCosts by Task Type:")
    by_type = attributor.aggregate_by_task_type(results)
    for task_type, cost in sorted(by_type.items()):
        print(f"  {task_type:20s}: ${cost:.4f}")
    
    # Aggregate by model
    print("\nCosts by Model:")
    by_model = attributor.aggregate_by_model(results)
    for model, cost in sorted(by_model.items()):
        print(f"  {model:20s}: ${cost:.4f}")
    
    # Total
    total = sum(by_role.values())
    print(f"\nTotal Cost: ${total:.4f}")


def example_metrics_integration():
    """Example 4: Integration with MetricsRegistry."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Metrics Integration")
    print("="*70)
    
    # Setup
    registry = MetricsRegistry()
    cost_metrics = create_cost_metrics(registry)
    attribution_metrics = CostAttributionMetrics(registry, cost_metrics)
    attributor = CostAttributor()
    
    # Process tasks
    tasks = [
        ("task-001", ["engineer"], {"engineer": 5000}, 0.15, "implementation"),
        ("task-002", ["senior_engineer"], {"senior_engineer": 8000}, 0.40, "review"),
        ("task-003", ["engineer", "quality_engineer"],
         {"engineer": 6000, "quality_engineer": 4000}, 0.25, "implementation"),
    ]
    
    print("\nRecording attributions to metrics...")
    for task_id, agents, tokens, cost, task_type in tasks:
        result = attributor.attribute_cost(
            task_id=task_id,
            agents=agents,
            tokens_per_agent=tokens,
            total_cost=cost,
            roles_per_agent={a: a for a in agents},
            models_per_agent={a: "haiku-4-5" for a in agents},
            task_type=task_type,
            timestamp=f"2025-01-15T{10:02d}:00:00Z",
        )
        attribution_metrics.record_attribution(result)
    
    # Retrieve from metrics
    print("\nCosts by Role (from metrics):")
    by_role = attribution_metrics.get_cost_by_role()
    for role, cost in sorted(by_role.items()):
        print(f"  {role:20s}: ${cost:.4f}")
    
    print("\nCosts by Task Type (from metrics):")
    by_type = attribution_metrics.get_cost_by_task_type()
    for task_type, cost in sorted(by_type.items()):
        print(f"  {task_type:20s}: ${cost:.4f}")
    
    print("\nCosts by Model (from metrics):")
    by_model = attribution_metrics.get_cost_by_model()
    for model, cost in sorted(by_model.items()):
        print(f"  {model:20s}: ${cost:.4f}")


def example_daily_aggregation():
    """Example 5: Daily cost aggregation."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Daily Cost Aggregation")
    print("="*70)
    
    attributor = CostAttributor()
    results = []
    
    # Simulate tasks throughout the day
    print("\nSimulating tasks throughout 2025-01-15...")
    for hour in range(9, 18):  # 9 AM to 5 PM
        result = attributor.attribute_cost(
            task_id=f"task-{hour:02d}00",
            agents=["engineer"],
            tokens_per_agent={"engineer": 5000 + hour*100},
            total_cost=0.10 + hour*0.02,
            roles_per_agent={"engineer": "engineer"},
            models_per_agent={"engineer": "haiku-4-5"},
            timestamp=f"2025-01-15T{hour:02d}:00:00Z",
        )
        results.append(result)
    
    # Aggregate by date
    by_date = attributor.aggregate_by_date(results)
    print("\nDaily Cost Summary:")
    for date, cost in sorted(by_date.items()):
        print(f"  {date}: ${cost:.4f}")
    
    # Statistics
    total_cost = sum(by_date.values())
    avg_cost = total_cost / len(results)
    print(f"\nTotal daily cost: ${total_cost:.4f}")
    print(f"Average cost per task: ${avg_cost:.4f}")
    print(f"Number of tasks: {len(results)}")


def example_edge_cases():
    """Example 6: Edge cases."""
    print("\n" + "="*70)
    print("EXAMPLE 6: Edge Cases")
    print("="*70)
    
    attributor = CostAttributor()
    
    # Case 1: Zero tokens (equal split)
    print("\nCase 1: Zero tokens (equal split)")
    result = attributor.attribute_cost(
        task_id="task-zero-tokens",
        agents=["agent_a", "agent_b"],
        tokens_per_agent={"agent_a": 0, "agent_b": 0},
        total_cost=0.20,
    )
    for agent, share in result.agent_shares.items():
        print(f"  {agent}: ${share.cost:.4f} ({share.weight*100:.1f}%)")
    
    # Case 2: Zero cost
    print("\nCase 2: Zero cost")
    result = attributor.attribute_cost(
        task_id="task-zero-cost",
        agents=["agent_a", "agent_b"],
        tokens_per_agent={"agent_a": 1000, "agent_b": 2000},
        total_cost=0.0,
    )
    for agent, share in result.agent_shares.items():
        print(f"  {agent}: ${share.cost:.4f}")
    
    # Case 3: Single agent
    print("\nCase 3: Single agent")
    result = attributor.attribute_cost(
        task_id="task-single",
        agents=["agent_a"],
        tokens_per_agent={"agent_a": 5000},
        total_cost=0.30,
    )
    for agent, share in result.agent_shares.items():
        print(f"  {agent}: ${share.cost:.4f} ({share.weight*100:.1f}%)")
    
    # Case 4: Missing agent in tokens dict
    print("\nCase 4: Missing agent in tokens dict")
    result = attributor.attribute_cost(
        task_id="task-missing",
        agents=["agent_a", "agent_b"],
        tokens_per_agent={"agent_a": 1000},  # agent_b missing
        total_cost=0.30,
    )
    for agent, share in result.agent_shares.items():
        print(f"  {agent}: ${share.cost:.4f} ({share.weight*100:.1f}%)")


def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("COST ATTRIBUTION INTEGRATION EXAMPLES")
    print("="*70)
    
    example_basic_attribution()
    example_multi_agent_attribution()
    example_aggregation()
    example_metrics_integration()
    example_daily_aggregation()
    example_edge_cases()
    
    print("\n" + "="*70)
    print("Examples completed successfully!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
