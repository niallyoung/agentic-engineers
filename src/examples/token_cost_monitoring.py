#!/usr/bin/env python3
"""
Token Cost Monitoring Examples

Demonstrates how to:
1. View token usage metrics
2. Interpret cost metrics
3. Evaluate cost anomaly alerts
4. Generate optimization recommendations
5. Create cost reports
"""

import json
from datetime import datetime
from collections import defaultdict
from src.orchestration.monitoring.metrics import MetricsRegistry, create_orchestrator_metrics
from src.orchestration.monitoring.alerting import AlertManager, create_default_alert_rules


def example_1_view_token_metrics():
    """Example 1: View current token usage metrics."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: View Token Usage Metrics")
    print("=" * 70)
    
    # Create metrics registry
    registry = MetricsRegistry()
    metrics = create_orchestrator_metrics(registry)
    
    # Simulate some token usage
    metrics['tokens_total'].inc(5000)
    metrics['cost_usd_total'].inc(0.15)
    metrics['tokens_input_total'].inc(3000)
    metrics['tokens_output_total'].inc(2000)
    metrics['tokens_cached_total'].inc(500)
    
    # Display metrics
    print(f"\nToken Usage Summary:")
    print(f"  Total tokens: {metrics['tokens_total'].value:,.0f}")
    print(f"  Input tokens: {metrics['tokens_input_total'].value:,.0f}")
    print(f"  Output tokens: {metrics['tokens_output_total'].value:,.0f}")
    print(f"  Cached tokens: {metrics['tokens_cached_total'].value:,.0f}")
    print(f"  Total cost: ${metrics['cost_usd_total'].value:.2f}")
    
    # Calculate cache effectiveness
    total_tokens = metrics['tokens_total'].value
    cached_tokens = metrics['tokens_cached_total'].value
    cache_savings = (cached_tokens / total_tokens * 100) if total_tokens > 0 else 0
    
    print(f"\nCache Performance:")
    print(f"  Cached tokens: {cached_tokens:,.0f}")
    print(f"  Cache effectiveness: {cache_savings:.1f}%")


def example_2_interpret_cost_breakdown():
    """Example 2: Interpret cost breakdown by model."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Cost Breakdown by Model")
    print("=" * 70)
    
    # Simulate task costs by model
    tasks = [
        {"model": "claude-haiku-4-5", "cost": 0.005, "tokens": 500},
        {"model": "claude-haiku-4-5", "cost": 0.006, "tokens": 600},
        {"model": "claude-sonnet-4", "cost": 0.025, "tokens": 500},
        {"model": "claude-sonnet-4", "cost": 0.030, "tokens": 600},
        {"model": "claude-opus", "cost": 0.150, "tokens": 500},
    ]
    
    # Calculate breakdown
    cost_by_model = defaultdict(lambda: {"count": 0, "cost": 0, "tokens": 0})
    for task in tasks:
        cost_by_model[task["model"]]["count"] += 1
        cost_by_model[task["model"]]["cost"] += task["cost"]
        cost_by_model[task["model"]]["tokens"] += task["tokens"]
    
    total_cost = sum(d["cost"] for d in cost_by_model.values())
    
    print(f"\nCost Breakdown by Model:")
    print(f"{'Model':<25} {'Tasks':<8} {'Cost':<12} {'% of Total':<12}")
    print("-" * 60)
    
    for model in sorted(cost_by_model.keys()):
        data = cost_by_model[model]
        pct = (data["cost"] / total_cost * 100) if total_cost > 0 else 0
        print(f"{model:<25} {data['count']:<8} ${data['cost']:<11.4f} {pct:<11.1f}%")
    
    print("-" * 60)
    print(f"{'TOTAL':<25} {len(tasks):<8} ${total_cost:<11.4f} {100.0:<11.1f}%")


def example_3_evaluate_cost_anomaly_alerts():
    """Example 3: Evaluate cost anomaly alerts."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Cost Anomaly Alert Evaluation")
    print("=" * 70)
    
    # Create alert manager
    manager = AlertManager()
    for rule in create_default_alert_rules():
        manager.add_rule(rule)
    
    # Scenario 1: Normal metrics
    print("\nScenario 1: Normal Metrics")
    print("-" * 40)
    normal_metrics = {
        "daily_token_cost": 75.0,
        "cost_per_task": 3.50,
        "cache_hit_rate": 0.75,
        "token_usage_sigma": 1.2,
    }
    
    alerts = manager.evaluate(normal_metrics)
    cost_alerts = [a for a in alerts if "Token" in a.name]
    
    if cost_alerts:
        for alert in cost_alerts:
            print(f"  🚨 {alert.name}: {alert.message}")
    else:
        print("  ✓ No cost anomaly alerts")
    
    # Scenario 2: High cost metrics
    print("\nScenario 2: High Cost Metrics")
    print("-" * 40)
    manager.clear_history()
    
    high_cost_metrics = {
        "daily_token_cost": 150.0,
        "cost_per_task": 6.5,
        "cache_hit_rate": 0.40,
        "token_usage_sigma": 2.8,
    }
    
    alerts = manager.evaluate(high_cost_metrics)
    cost_alerts = [a for a in alerts if "Token" in a.name]
    
    if cost_alerts:
        for alert in cost_alerts:
            print(f"  🚨 {alert.name}")
            print(f"     Severity: {alert.severity.value}")
            print(f"     Message: {alert.message}")
    else:
        print("  ✓ No cost anomaly alerts")


def example_4_cost_optimization_recommendations():
    """Example 4: Generate cost optimization recommendations."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Cost Optimization Recommendations")
    print("=" * 70)
    
    def generate_recommendations(metrics_dict):
        """Generate optimization recommendations."""
        recommendations = []
        
        daily_cost = metrics_dict.get("daily_token_cost", 0)
        if daily_cost > 100:
            recommendations.append({
                "priority": "HIGH",
                "issue": "Daily cost exceeds $100",
                "recommendation": "Review model selection and prompt optimization",
                "potential_savings": f"${daily_cost * 0.3:.2f} (30% reduction)",
            })
        
        cost_per_task = metrics_dict.get("cost_per_task", 0)
        if cost_per_task > 5.0:
            recommendations.append({
                "priority": "HIGH",
                "issue": "Cost per task exceeds $5",
                "recommendation": "Route to cheaper models or optimize prompts",
                "potential_savings": f"${cost_per_task * 0.5:.2f} per task (50% reduction)",
            })
        
        cache_hit_rate = metrics_dict.get("cache_hit_rate", 1.0)
        if cache_hit_rate < 0.5:
            recommendations.append({
                "priority": "MEDIUM",
                "issue": "Cache hit rate below 50%",
                "recommendation": "Increase cache TTL and reuse prompts",
                "potential_savings": f"${daily_cost * (0.5 - cache_hit_rate):.2f} (cache improvement)",
            })
        
        sigma = metrics_dict.get("token_usage_sigma", 0)
        if sigma > 2.5:
            recommendations.append({
                "priority": "MEDIUM",
                "issue": "Unusual token usage pattern",
                "recommendation": "Investigate task volume spike or code changes",
                "potential_savings": "TBD (investigate first)",
            })
        
        return recommendations
    
    # Analyze high-cost scenario
    metrics = {
        "daily_token_cost": 150.0,
        "cost_per_task": 6.5,
        "cache_hit_rate": 0.40,
        "token_usage_sigma": 2.8,
    }
    
    recommendations = generate_recommendations(metrics)
    
    print(f"\nCurrent Metrics:")
    print(f"  Daily cost: ${metrics['daily_token_cost']:.2f}")
    print(f"  Cost per task: ${metrics['cost_per_task']:.2f}")
    print(f"  Cache hit rate: {metrics['cache_hit_rate']:.1%}")
    print(f"  Token usage deviation: {metrics['token_usage_sigma']:.1f}σ")
    
    print(f"\nRecommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n  {i}. [{rec['priority']}] {rec['issue']}")
        print(f"     → {rec['recommendation']}")
        print(f"     💰 Potential savings: {rec['potential_savings']}")


def example_5_daily_cost_report():
    """Example 5: Generate daily cost report."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Daily Cost Report")
    print("=" * 70)
    
    # Create metrics
    registry = MetricsRegistry()
    metrics = create_orchestrator_metrics(registry)
    
    # Simulate daily activity
    metrics['tokens_total'].inc(12500)
    metrics['tokens_input_total'].inc(8000)
    metrics['tokens_output_total'].inc(4000)
    metrics['tokens_cached_total'].inc(500)
    metrics['cost_usd_total'].inc(0.38)
    metrics['tasks_total'].inc(75)
    metrics['tasks_completed'].inc(72)
    metrics['tasks_failed'].inc(3)
    
    # Record some cost per task observations
    for _ in range(72):
        metrics['cost_per_task'].observe(0.0053)  # ~$0.38 / 72 tasks
    
    # Generate report
    total_tokens = metrics['tokens_total'].value
    total_cost = metrics['cost_usd_total'].value
    cached_tokens = metrics['tokens_cached_total'].value
    total_tasks = metrics['tasks_total'].value
    completed = metrics['tasks_completed'].value
    failed = metrics['tasks_failed'].value
    
    cost_per_task = total_cost / completed if completed > 0 else 0
    success_rate = completed / total_tasks if total_tasks > 0 else 0
    cache_effectiveness = (cached_tokens / total_tokens * 100) if total_tokens > 0 else 0
    
    print(f"\nDaily Cost Report - {datetime.now().strftime('%Y-%m-%d')}")
    print("-" * 70)
    
    print(f"\nToken Usage:")
    print(f"  Total tokens: {total_tokens:,.0f}")
    print(f"  Input tokens: {metrics['tokens_input_total'].value:,.0f}")
    print(f"  Output tokens: {metrics['tokens_output_total'].value:,.0f}")
    print(f"  Cached tokens: {cached_tokens:,.0f}")
    print(f"  Total cost: ${total_cost:.2f}")
    print(f"  Cost per token: ${total_cost / total_tokens * 1_000_000:.2f}/M tokens")
    
    print(f"\nTask Performance:")
    print(f"  Total tasks: {total_tasks}")
    print(f"  Completed: {completed}")
    print(f"  Failed: {failed}")
    print(f"  Success rate: {success_rate:.1%}")
    print(f"  Cost per task: ${cost_per_task:.4f}")
    
    print(f"\nCache Performance:")
    print(f"  Cached tokens: {cached_tokens:,.0f}")
    print(f"  Cache effectiveness: {cache_effectiveness:.1f}%")
    print(f"  Cache savings: ${total_cost * (cache_effectiveness / 100) * 0.5:.2f} (estimated)")
    
    print(f"\nCost Status:")
    if total_cost > 100:
        print(f"  ⚠️  Daily cost exceeds $100 threshold")
    else:
        print(f"  ✓ Daily cost within budget")
    
    if cost_per_task > 5.0:
        print(f"  ⚠️  Cost per task exceeds $5 threshold")
    else:
        print(f"  ✓ Cost per task within budget")
    
    if cache_effectiveness < 50:
        print(f"  ⚠️  Cache effectiveness below 50% threshold")
    else:
        print(f"  ✓ Cache effectiveness healthy")


def example_6_alert_history():
    """Example 6: Review alert history."""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Alert History")
    print("=" * 70)
    
    manager = AlertManager()
    for rule in create_default_alert_rules():
        manager.add_rule(rule)
    
    # Simulate multiple evaluations
    print("\nSimulating alert lifecycle...")
    
    # First evaluation: metrics normal
    manager.evaluate({
        "daily_token_cost": 75.0,
        "cost_per_task": 3.50,
        "cache_hit_rate": 0.75,
    })
    print("  ✓ Evaluation 1: Normal metrics")
    
    # Second evaluation: cost spike
    manager.evaluate({
        "daily_token_cost": 120.0,
        "cost_per_task": 5.50,
        "cache_hit_rate": 0.40,
    })
    print("  ⚠️  Evaluation 2: Cost spike detected")
    
    # Third evaluation: back to normal
    manager.evaluate({
        "daily_token_cost": 80.0,
        "cost_per_task": 3.75,
        "cache_hit_rate": 0.70,
    })
    print("  ✓ Evaluation 3: Metrics normalized")
    
    # Display history
    history = manager.get_alert_history()
    
    print(f"\nAlert History ({len(history)} total):")
    print("-" * 70)
    
    for alert in history:
        duration = alert.duration_minutes
        print(f"\n  • {alert.name}")
        print(f"    State: {alert.state.value}")
        print(f"    Severity: {alert.severity.value}")
        print(f"    Duration: {duration:.1f} minutes")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("TOKEN COST MONITORING EXAMPLES")
    print("=" * 70)
    
    example_1_view_token_metrics()
    example_2_interpret_cost_breakdown()
    example_3_evaluate_cost_anomaly_alerts()
    example_4_cost_optimization_recommendations()
    example_5_daily_cost_report()
    example_6_alert_history()
    
    print("\n" + "=" * 70)
    print("Examples Complete")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
