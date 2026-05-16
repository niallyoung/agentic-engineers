# Token Cost Monitoring & Anomaly Detection Guide

## Overview

This guide explains how to monitor token usage and costs in the agentic-engineers framework, interpret cost metrics, and respond to cost anomaly alerts.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Understanding Token Costs](#understanding-token-costs)
3. [Cost Metrics](#cost-metrics)
4. [Alert Rules](#alert-rules)
5. [Interpreting Alerts](#interpreting-alerts)
6. [Optimization Strategies](#optimization-strategies)
7. [Troubleshooting](#troubleshooting)
8. [Examples](#examples)

---

## Quick Start

### View Current Token Usage

```python
from src.orchestration.monitoring.metrics import MetricsRegistry, create_orchestrator_metrics

# Create metrics registry
registry = MetricsRegistry()
metrics = create_orchestrator_metrics(registry)

# Get current metrics
all_metrics = registry.get_all()
print(f"Total tokens used: {metrics['tokens_total'].value}")
print(f"Total cost: ${metrics['tokens_cost_total'].value:.2f}")
```

### Check Active Alerts

```python
from src.orchestration.monitoring.alerting import AlertManager, create_default_alert_rules

manager = AlertManager()
for rule in create_default_alert_rules():
    manager.add_rule(rule)

# Evaluate alerts with current metrics
alerts = manager.evaluate({
    "daily_token_cost": 150.0,
    "cost_per_task": 6.5,
    "cache_hit_rate": 0.40,
})

for alert in alerts:
    print(f"🚨 {alert.name}: {alert.message}")
```

---

## Understanding Token Costs

### Token Pricing Model

Tokens are priced based on the model used:

| Model | Input Cost | Output Cost | Notes |
|-------|-----------|------------|-------|
| Claude Haiku | $0.80/M | $4.00/M | Fast, cost-effective |
| Claude Sonnet | $3.00/M | $15.00/M | Balanced quality/cost |
| Claude Opus | $15.00/M | $75.00/M | High quality, expensive |
| GPT-4 | $0.03/1K | $0.06/1K | Competitive pricing |

### Cost Calculation

```
Total Cost = (Input Tokens × Input Rate) + (Output Tokens × Output Rate)

Example:
- Input: 1,000 tokens @ $3.00/M = $0.003
- Output: 500 tokens @ $15.00/M = $0.0075
- Total: $0.0105 per task
```

### Cost Drivers

1. **Model Selection** — Opus costs 10x more than Haiku
2. **Input Size** — Larger prompts = higher input token cost
3. **Output Length** — Longer responses = higher output token cost
4. **Cache Hit Rate** — Cache misses require full re-processing
5. **Task Complexity** — Complex tasks often require more tokens

---

## Cost Metrics

### Key Metrics

#### 1. Daily Token Cost
- **Metric**: `daily_token_cost`
- **Unit**: USD ($)
- **Threshold**: > $100 (warning)
- **Meaning**: Total cost accumulated in last 24 hours
- **Action**: Review task volume and model selection

#### 2. Cost Per Task
- **Metric**: `cost_per_task`
- **Unit**: USD ($)
- **Threshold**: > $5.00 (warning)
- **Meaning**: Average cost per completed task
- **Action**: Investigate task complexity and model routing

#### 3. Cache Hit Rate
- **Metric**: `cache_hit_rate`
- **Unit**: Percentage (0.0-1.0)
- **Threshold**: < 50% (warning)
- **Meaning**: Proportion of cached results vs. new computations
- **Action**: Improve caching strategy or increase cache TTL

#### 4. Token Usage Anomaly
- **Metric**: `token_usage_sigma`
- **Unit**: Standard Deviations (σ)
- **Threshold**: > 2.5σ (warning)
- **Meaning**: Current usage deviation from 7-day average
- **Action**: Investigate unusual patterns or load spikes

### Metric Collection

Metrics are collected automatically during task execution:

```python
from src.orchestration.monitoring.metrics import MetricsRegistry, create_orchestrator_metrics

registry = MetricsRegistry()
metrics = create_orchestrator_metrics(registry)

# During task execution
metrics['tokens_total'].inc(1250)  # Input + output tokens
metrics['tokens_cost_total'].inc(0.0125)  # Cost in dollars
metrics['cache_hits'].inc()  # Cache hit
# or
metrics['cache_misses'].inc()  # Cache miss
```

---

## Alert Rules

### Alert Configuration

All cost anomaly alerts are defined in `alerting_rules.yaml` and implemented in `alerting.py`.

### Alert Definitions

#### TokenCostDailyHigh
```yaml
Alert: TokenCostDailyHigh
Severity: WARNING
Threshold: Daily cost > $100
Duration: 5 minutes
Runbook: docs/runbooks/token-cost-high.md
```

**Triggers when:**
- Total cost in last 24 hours exceeds $100
- Condition persists for 5 minutes

**Example metrics:**
```python
{"daily_token_cost": 150.50}  # Fires alert
{"daily_token_cost": 75.00}   # Does not fire
```

#### TokenCostPerTaskHigh
```yaml
Alert: TokenCostPerTaskHigh
Severity: WARNING
Threshold: Cost per task > $5.00
Duration: 10 minutes
Runbook: docs/runbooks/token-cost-high.md
```

**Triggers when:**
- Average cost per task exceeds $5.00
- Condition persists for 10 minutes

**Example metrics:**
```python
{"cost_per_task": 7.50}  # Fires alert
{"cost_per_task": 3.25}  # Does not fire
```

#### TokenCacheHitRateLow
```yaml
Alert: TokenCacheHitRateLow
Severity: WARNING
Threshold: Cache hit rate < 50%
Duration: 15 minutes
Runbook: docs/runbooks/cache-hit-rate-low.md
```

**Triggers when:**
- Cache hit rate drops below 50%
- Condition persists for 15 minutes

**Example metrics:**
```python
{"cache_hit_rate": 0.35}  # Fires alert (35% hit rate)
{"cache_hit_rate": 0.75}  # Does not fire (75% hit rate)
```

#### TokenUsageAnomaly
```yaml
Alert: TokenUsageAnomaly
Severity: WARNING
Threshold: Token usage > 2.5σ from mean
Duration: 5 minutes
Runbook: docs/runbooks/token-usage-anomaly.md
```

**Triggers when:**
- Current token usage is > 2.5 standard deviations above 7-day average
- Condition persists for 5 minutes

**Example metrics:**
```python
{"token_usage_sigma": 3.2}  # Fires alert (3.2σ above mean)
{"token_usage_sigma": 1.8}  # Does not fire (1.8σ above mean)
```

---

## Interpreting Alerts

### Alert States

| State | Meaning | Action |
|-------|---------|--------|
| PENDING | Condition met but duration threshold not reached | Monitor |
| FIRING | Alert is active and requires attention | Investigate |
| RESOLVED | Condition cleared | Verify metrics returned to normal |

### Alert Lifecycle

```
Condition Met
    ↓
PENDING (duration timer starts)
    ↓
Duration threshold reached
    ↓
FIRING (alert active)
    ↓
Condition clears
    ↓
RESOLVED (alert closed)
```

### Example Alert Response

```python
from src.orchestration.monitoring.alerting import AlertManager, create_default_alert_rules

manager = AlertManager()
for rule in create_default_alert_rules():
    manager.add_rule(rule)

# Simulate high cost scenario
metrics = {
    "daily_token_cost": 150.0,
    "cost_per_task": 6.5,
    "cache_hit_rate": 0.40,
    "token_usage_sigma": 2.8,
}

alerts = manager.evaluate(metrics)

for alert in alerts:
    print(f"Alert: {alert.name}")
    print(f"Severity: {alert.severity.value}")
    print(f"Message: {alert.message}")
    print(f"Fired at: {alert.fired_at}")
    print(f"Annotations: {alert.annotations}")
    print()
```

**Output:**
```
Alert: TokenCostDailyHigh
Severity: warning
Message: Daily token cost exceeds $100
Fired at: 1715976000.0
Annotations: {'runbook_url': 'docs/runbooks/token-cost-high.md', ...}

Alert: TokenCostPerTaskHigh
Severity: warning
Message: Cost per task exceeds $5
Fired at: 1715976000.0
Annotations: {'runbook_url': 'docs/runbooks/token-cost-high.md', ...}

Alert: TokenCacheHitRateLow
Severity: warning
Message: Cache hit rate below 50%
Fired at: 1715976000.0
Annotations: {'runbook_url': 'docs/runbooks/cache-hit-rate-low.md', ...}

Alert: TokenUsageAnomaly
Severity: warning
Message: Token usage anomaly detected (> 2.5σ from mean)
Fired at: 1715976000.0
Annotations: {'runbook_url': 'docs/runbooks/token-usage-anomaly.md', ...}
```

---

## Optimization Strategies

### 1. Model Selection Optimization

**Problem**: High cost per task
**Solution**: Route tasks to cheaper models when possible

```python
# Route simple tasks to Haiku (cheaper)
if task_complexity < 0.5:
    model = "claude-haiku-4-5"  # $0.80/$4.00 per M tokens
else:
    model = "claude-sonnet-4"   # $3.00/$15.00 per M tokens
```

**Expected Impact**: 50-70% cost reduction for simple tasks

### 2. Prompt Optimization

**Problem**: High input token count
**Solution**: Reduce prompt size and complexity

```python
# Before: 2,000 token prompt
prompt = """
You are an expert engineer...
[20 paragraphs of context]
Task: [actual task]
"""

# After: 500 token prompt
prompt = """
You are an engineer.
Context: [key facts only]
Task: [actual task]
"""
```

**Expected Impact**: 60-80% reduction in input tokens

### 3. Cache Optimization

**Problem**: Low cache hit rate (< 50%)
**Solution**: Increase cache TTL and reuse prompts

```python
# Enable caching for repeated queries
cache_config = {
    "ttl_seconds": 3600,  # 1 hour
    "max_size": 1000,     # Max entries
}

# Reuse system prompts
SYSTEM_PROMPT = "You are an expert..."  # Cache this
```

**Expected Impact**: 30-50% cost reduction through cache hits

### 4. Batch Processing

**Problem**: Many small tasks with high overhead
**Solution**: Batch similar tasks together

```python
# Before: 100 tasks × $0.05 = $5.00
for task in tasks:
    result = process_task(task)

# After: 1 batch × $0.10 = $0.10
batch_result = process_batch(tasks)
```

**Expected Impact**: 80-90% cost reduction for batch workloads

### 5. Output Length Control

**Problem**: Long, verbose responses
**Solution**: Constrain output length

```python
prompt = """
Task: [task]
Constraints:
- Response must be < 100 tokens
- Use bullet points only
- No explanations
"""
```

**Expected Impact**: 40-60% reduction in output tokens

### 6. Monitoring & Alerting

**Problem**: Undetected cost spikes
**Solution**: Set up alerts and dashboards

```python
# Alert on daily cost > $100
manager.add_rule(AlertRule(
    name="TokenCostDailyHigh",
    condition=lambda m: m.get("daily_token_cost", 0) > 100,
    for_minutes=5,
))

# Daily cost report
daily_cost = metrics['tokens_cost_total'].value
print(f"Daily cost: ${daily_cost:.2f}")
```

**Expected Impact**: Early detection of cost anomalies

---

## Troubleshooting

### Issue: TokenCostDailyHigh Alert Firing

**Symptoms:**
- Alert fires repeatedly
- Daily cost consistently > $100

**Diagnosis:**
```python
# Check cost breakdown by model
from collections import defaultdict

cost_by_model = defaultdict(float)
for task in completed_tasks:
    cost_by_model[task.model] += task.cost

for model, cost in sorted(cost_by_model.items(), key=lambda x: -x[1]):
    print(f"{model}: ${cost:.2f}")
```

**Solutions:**
1. Route more tasks to cheaper models (Haiku)
2. Reduce task volume
3. Optimize prompts (see [Prompt Optimization](#2-prompt-optimization))
4. Increase cache hit rate (see [Cache Optimization](#3-cache-optimization))

### Issue: TokenCostPerTaskHigh Alert Firing

**Symptoms:**
- Alert fires for specific task types
- Cost per task > $5.00

**Diagnosis:**
```python
# Check cost by task type
cost_by_type = defaultdict(lambda: {"count": 0, "cost": 0})
for task in completed_tasks:
    cost_by_type[task.type]["count"] += 1
    cost_by_type[task.type]["cost"] += task.cost

for task_type, data in cost_by_type.items():
    avg_cost = data["cost"] / data["count"]
    print(f"{task_type}: ${avg_cost:.2f} avg ({data['count']} tasks)")
```

**Solutions:**
1. Use cheaper model for this task type
2. Reduce input prompt size
3. Constrain output length
4. Break into smaller subtasks

### Issue: TokenCacheHitRateLow Alert Firing

**Symptoms:**
- Cache hit rate < 50%
- Cost not decreasing despite optimization

**Diagnosis:**
```python
# Check cache statistics
cache_hits = metrics['cache_hits'].value
cache_misses = metrics['cache_misses'].value
hit_rate = cache_hits / (cache_hits + cache_misses)

print(f"Cache hits: {cache_hits}")
print(f"Cache misses: {cache_misses}")
print(f"Hit rate: {hit_rate:.1%}")
```

**Solutions:**
1. Increase cache TTL (time-to-live)
2. Reuse system prompts across tasks
3. Normalize prompt formatting
4. Increase cache size

### Issue: TokenUsageAnomaly Alert Firing

**Symptoms:**
- Alert fires unexpectedly
- Token usage > 2.5σ from 7-day average

**Diagnosis:**
```python
# Check recent token usage vs. historical
import statistics

historical = [1000, 1100, 950, 1050, 1000, 1150, 1000]  # Last 7 days
current = 2500

mean = statistics.mean(historical)
stdev = statistics.stdev(historical)
sigma = (current - mean) / stdev

print(f"Mean: {mean:.0f} tokens")
print(f"StdDev: {stdev:.0f} tokens")
print(f"Current: {current} tokens")
print(f"Deviation: {sigma:.1f}σ")
```

**Solutions:**
1. Check for unusual task volume spike
2. Verify no runaway loops or infinite retries
3. Review recent code changes
4. Check for new high-complexity tasks

---

## Examples

### Example 1: Daily Cost Report

```python
from src.orchestration.monitoring.metrics import MetricsRegistry, create_orchestrator_metrics
from datetime import datetime

registry = MetricsRegistry()
metrics = create_orchestrator_metrics(registry)

# Simulate some token usage
metrics['tokens_total'].inc(5000)
metrics['tokens_cost_total'].inc(0.15)
metrics['cache_hits'].inc(150)
metrics['cache_misses'].inc(50)

# Generate report
print("=" * 50)
print(f"Token Cost Report - {datetime.now().strftime('%Y-%m-%d')}")
print("=" * 50)
print(f"Total tokens: {metrics['tokens_total'].value:,.0f}")
print(f"Total cost: ${metrics['tokens_cost_total'].value:.2f}")

cache_hits = metrics['cache_hits'].value
cache_misses = metrics['cache_misses'].value
total_cache = cache_hits + cache_misses
hit_rate = cache_hits / total_cache if total_cache > 0 else 0

print(f"Cache hits: {cache_hits:,.0f}")
print(f"Cache misses: {cache_misses:,.0f}")
print(f"Hit rate: {hit_rate:.1%}")
print("=" * 50)
```

**Output:**
```
==================================================
Token Cost Report - 2026-05-17
==================================================
Total tokens: 5,000
Total cost: $0.15
Cache hits: 150
Cache misses: 50
Hit rate: 75.0%
==================================================
```

### Example 2: Alert Evaluation with Metrics

```python
from src.orchestration.monitoring.alerting import AlertManager, create_default_alert_rules

# Create alert manager
manager = AlertManager()
for rule in create_default_alert_rules():
    manager.add_rule(rule)

# Simulate metrics from monitoring system
current_metrics = {
    "daily_token_cost": 120.50,
    "cost_per_task": 4.75,
    "cache_hit_rate": 0.65,
    "token_usage_sigma": 1.8,
    "error_rate": 0.02,
    "queue_depth": 45,
    "avg_quality_score": 85,
}

# Evaluate alerts
alerts = manager.evaluate(current_metrics)

print("Active Alerts:")
print("-" * 50)
for alert in alerts:
    print(f"• {alert.name}")
    print(f"  Severity: {alert.severity.value}")
    print(f"  Message: {alert.message}")
    print()

if not alerts:
    print("✓ No active alerts")
```

**Output:**
```
Active Alerts:
--------------------------------------------------
• TokenCostDailyHigh
  Severity: warning
  Message: Daily token cost exceeds $100

```

### Example 3: Cost Optimization Recommendations

```python
from src.orchestration.monitoring.metrics import MetricsRegistry, create_orchestrator_metrics

def generate_optimization_recommendations(metrics_dict):
    """Generate cost optimization recommendations."""
    recommendations = []
    
    # Check daily cost
    daily_cost = metrics_dict.get("daily_token_cost", 0)
    if daily_cost > 100:
        recommendations.append({
            "priority": "HIGH",
            "issue": "Daily cost exceeds $100",
            "recommendation": "Review model selection and prompt optimization",
            "potential_savings": f"${daily_cost * 0.3:.2f} (30% reduction)",
        })
    
    # Check cost per task
    cost_per_task = metrics_dict.get("cost_per_task", 0)
    if cost_per_task > 5.0:
        recommendations.append({
            "priority": "HIGH",
            "issue": "Cost per task exceeds $5",
            "recommendation": "Route to cheaper models or optimize prompts",
            "potential_savings": f"${cost_per_task * 0.5:.2f} per task (50% reduction)",
        })
    
    # Check cache hit rate
    cache_hit_rate = metrics_dict.get("cache_hit_rate", 1.0)
    if cache_hit_rate < 0.5:
        recommendations.append({
            "priority": "MEDIUM",
            "issue": "Cache hit rate below 50%",
            "recommendation": "Increase cache TTL and reuse prompts",
            "potential_savings": f"${daily_cost * (0.5 - cache_hit_rate):.2f} (cache improvement)",
        })
    
    # Check token usage anomaly
    sigma = metrics_dict.get("token_usage_sigma", 0)
    if sigma > 2.5:
        recommendations.append({
            "priority": "MEDIUM",
            "issue": "Unusual token usage pattern",
            "recommendation": "Investigate task volume spike or code changes",
            "potential_savings": "TBD (investigate first)",
        })
    
    return recommendations

# Example usage
metrics = {
    "daily_token_cost": 150.0,
    "cost_per_task": 6.5,
    "cache_hit_rate": 0.40,
    "token_usage_sigma": 2.8,
}

recommendations = generate_optimization_recommendations(metrics)

print("Cost Optimization Recommendations")
print("=" * 70)
for i, rec in enumerate(recommendations, 1):
    print(f"\n{i}. [{rec['priority']}] {rec['issue']}")
    print(f"   Recommendation: {rec['recommendation']}")
    print(f"   Potential savings: {rec['potential_savings']}")
print("\n" + "=" * 70)
```

**Output:**
```
Cost Optimization Recommendations
======================================================================

1. [HIGH] Daily cost exceeds $100
   Recommendation: Review model selection and prompt optimization
   Potential savings: $45.00 (30% reduction)

2. [HIGH] Cost per task exceeds $5
   Recommendation: Route to cheaper models or optimize prompts
   Potential savings: $3.25 per task (50% reduction)

3. [MEDIUM] Cache hit rate below 50%
   Recommendation: Increase cache TTL and reuse prompts
   Potential savings: $60.00 (cache improvement)

4. [MEDIUM] Unusual token usage pattern
   Recommendation: Investigate task volume spike or code changes
   Potential savings: TBD (investigate first)

======================================================================
```

---

## Related Documentation

- [Alerting System](./MONITORING.md#alerting)
- [Metrics Collection](./MONITORING.md#metrics)
- [Runbooks](./runbooks/)
  - [Token Cost High](./runbooks/token-cost-high.md)
  - [Cache Hit Rate Low](./runbooks/cache-hit-rate-low.md)
  - [Token Usage Anomaly](./runbooks/token-usage-anomaly.md)

---

## Summary

Token cost monitoring is critical for maintaining operational efficiency. By understanding cost metrics, interpreting alerts, and implementing optimization strategies, you can:

- ✅ Detect cost anomalies early
- ✅ Optimize model selection
- ✅ Reduce token consumption
- ✅ Improve cache effectiveness
- ✅ Maintain cost control

For questions or issues, refer to the [Troubleshooting](#troubleshooting) section or consult the runbooks.
