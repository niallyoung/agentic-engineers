# Token Cost Monitoring Quick Reference

## Alert Rules at a Glance

### 🚨 TokenCostDailyHigh
```
Triggers: Daily cost > $100
Duration: 5 minutes
Action: Review task volume, optimize prompts, route to cheaper models
Potential savings: 30% reduction
```

### 🚨 TokenCostPerTaskHigh
```
Triggers: Cost per task > $5.00
Duration: 10 minutes
Action: Use cheaper models, reduce input size, constrain output
Potential savings: 50% reduction per task
```

### 🚨 TokenCacheHitRateLow
```
Triggers: Cache hit rate < 50%
Duration: 15 minutes
Action: Increase cache TTL, reuse prompts, normalize formatting
Potential savings: 30-50% cost reduction
```

### 🚨 TokenUsageAnomaly
```
Triggers: Token usage > 2.5σ from 7-day mean
Duration: 5 minutes
Action: Investigate load spike, check for runaway loops, review changes
Potential savings: TBD (investigate first)
```

---

## Quick Metrics Reference

| Metric | Type | Threshold | Unit |
|--------|------|-----------|------|
| `daily_token_cost` | Gauge | > $100 | USD |
| `cost_per_task` | Histogram | > $5.00 | USD |
| `cache_hit_rate` | Gauge | < 0.5 | 0.0-1.0 |
| `token_usage_sigma` | Gauge | > 2.5 | σ |

---

## Common Issues & Quick Fixes

### High Daily Cost
```python
# Check cost by model
cost_by_model = defaultdict(float)
for task in tasks:
    cost_by_model[task.model] += task.cost

# Route more to Haiku (cheaper)
if task_complexity < 0.5:
    model = "claude-haiku-4-5"  # $0.80/$4.00 per M
else:
    model = "claude-sonnet-4"   # $3.00/$15.00 per M
```

### High Cost Per Task
```python
# Optimize prompt
prompt = """
Task: [task]
Constraints:
- Response must be < 100 tokens
- Use bullet points only
- No explanations
"""
```

### Low Cache Hit Rate
```python
# Reuse system prompts
SYSTEM_PROMPT = "You are an expert..."  # Cache this
cache_config = {
    "ttl_seconds": 3600,  # 1 hour
    "max_size": 1000,
}
```

### Usage Anomaly
```python
# Check recent usage
import statistics

historical = [1000, 1100, 950, 1050, 1000, 1150, 1000]  # Last 7 days
current = 2500

mean = statistics.mean(historical)
stdev = statistics.stdev(historical)
sigma = (current - mean) / stdev  # If > 2.5, alert fires
```

---

## Code Examples

### View Metrics
```python
from src.orchestration.monitoring.metrics import MetricsRegistry, create_orchestrator_metrics

registry = MetricsRegistry()
metrics = create_orchestrator_metrics(registry)

print(f"Total cost: ${metrics['cost_usd_total'].value:.2f}")
print(f"Total tokens: {metrics['tokens_total'].value:,.0f}")
```

### Evaluate Alerts
```python
from src.orchestration.monitoring.alerting import AlertManager, create_default_alert_rules

manager = AlertManager()
for rule in create_default_alert_rules():
    manager.add_rule(rule)

alerts = manager.evaluate({
    "daily_token_cost": 150.0,
    "cost_per_task": 6.5,
    "cache_hit_rate": 0.40,
    "token_usage_sigma": 2.8,
})

for alert in alerts:
    print(f"🚨 {alert.name}: {alert.message}")
```

### Record Metrics
```python
# During task execution
metrics['tokens_total'].inc(1250)
metrics['cost_usd_total'].inc(0.0125)
metrics['tokens_input_total'].inc(1000)
metrics['tokens_output_total'].inc(250)

# Cache hit
metrics['tokens_cached_total'].inc(500)
```

---

## Optimization Checklist

- [ ] Review model selection (route simple tasks to Haiku)
- [ ] Optimize prompts (remove unnecessary context)
- [ ] Increase cache TTL (from 1h to 24h if possible)
- [ ] Reuse system prompts (don't recreate each time)
- [ ] Constrain output length (add token limits)
- [ ] Batch similar tasks (reduce per-task overhead)
- [ ] Monitor trends (set up dashboards)
- [ ] Review runbooks (when alerts fire)

---

## Model Pricing Reference

| Model | Input | Output | Notes |
|-------|-------|--------|-------|
| Haiku | $0.80/M | $4.00/M | Fast, cheap |
| Sonnet | $3.00/M | $15.00/M | Balanced |
| Opus | $15.00/M | $75.00/M | Best quality |

---

## Documentation Links

- **Full Guide**: `docs/TOKEN-COST-MONITORING.md`
- **Examples**: `examples/token_cost_monitoring.py`
- **Implementation**: `IMPLEMENTATION_SUMMARY_TOKEN_COST_ALERTS.md`
- **Alert Rules**: `src/orchestration/monitoring/alerting_rules.yaml`
- **Metrics**: `src/orchestration/monitoring/metrics.py`
- **Tests**: `tests/test_monitoring.py::TestTokenCostAnomalyAlerts`

---

## Support

For issues or questions:
1. Check troubleshooting section in `TOKEN-COST-MONITORING.md`
2. Review examples in `examples/token_cost_monitoring.py`
3. Check runbooks in `docs/runbooks/`
4. Review test cases in `tests/test_monitoring.py`
