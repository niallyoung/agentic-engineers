# Token & Cost Metrics Implementation Guide

**Purpose**: Document the metrics that must be collected and exported by the PrometheusExporter to support the updated Grafana dashboard.

**Status**: Design specification (implementation in DELEGATE 3 follow-up)

---

## Overview

The updated Grafana dashboard requires the following metrics to be collected and exported:

1. **Token Metrics** (4 types)
2. **Cost Metrics** (2 types)

All metrics should be exposed via the PrometheusExporter in Prometheus text format.

---

## Token Metrics

### 1. `orchestrator_tokens_input_total` (Counter)

**Type**: Counter  
**Description**: Total input tokens consumed across all tasks  
**Unit**: tokens  
**Labels**: `model`, `role`

**Usage**:
```promql
rate(orchestrator_tokens_input_total[1m])  # Input tokens per second
sum(orchestrator_tokens_input_total)       # Total input tokens
sum(orchestrator_tokens_input_total) by (model)  # By model
```

**Implementation**:
```python
input_tokens_counter = registry.counter(
    "orchestrator_tokens_input_total",
    description="Total input tokens consumed",
    labels={"model": model_name, "role": role_name}
)
input_tokens_counter.inc(tokens_consumed)
```

**Collection Points**:
- After each task completion in Orchestrator
- Extract from HANDBACK block: `tokens.used` (input portion)
- Label with task's `model` and `role`

---

### 2. `orchestrator_tokens_output_total` (Counter)

**Type**: Counter  
**Description**: Total output tokens generated across all tasks  
**Unit**: tokens  
**Labels**: `model`, `role`

**Usage**:
```promql
rate(orchestrator_tokens_output_total[1m])  # Output tokens per second
sum(orchestrator_tokens_output_total)       # Total output tokens
sum(orchestrator_tokens_output_total) by (model)  # By model
```

**Implementation**:
```python
output_tokens_counter = registry.counter(
    "orchestrator_tokens_output_total",
    description="Total output tokens generated",
    labels={"model": model_name, "role": role_name}
)
output_tokens_counter.inc(tokens_generated)
```

**Collection Points**:
- After each task completion in Orchestrator
- Extract from HANDBACK block: `tokens.used` (output portion)
- Label with task's `model` and `role`

---

### 3. `orchestrator_tokens_cached_total` (Counter)

**Type**: Counter  
**Description**: Total cached tokens reused (prompt caching)  
**Unit**: tokens  
**Labels**: `model`, `role`

**Usage**:
```promql
rate(orchestrator_tokens_cached_total[1m])  # Cached tokens per second
(sum(orchestrator_tokens_cached_total) / sum(orchestrator_tokens_total)) * 100  # Cache hit %
```

**Implementation**:
```python
cached_tokens_counter = registry.counter(
    "orchestrator_tokens_cached_total",
    description="Total cached tokens reused (prompt caching)",
    labels={"model": model_name, "role": role_name}
)
cached_tokens_counter.inc(cached_tokens_count)
```

**Collection Points**:
- After each task completion in Orchestrator
- Extract from API response: cache_creation_input_tokens, cache_read_input_tokens
- Label with task's `model` and `role`

**Note**: Requires API support for prompt caching metrics (Claude API v1.3+)

---

### 4. `orchestrator_tokens_per_task_bucket` (Histogram)

**Type**: Histogram  
**Description**: Distribution of tokens consumed per task  
**Unit**: tokens  
**Labels**: `model`, `role`  
**Buckets**: [100, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000, +Inf]

**Usage**:
```promql
histogram_quantile(0.50, rate(orchestrator_tokens_per_task_bucket[5m]))  # P50
histogram_quantile(0.95, rate(orchestrator_tokens_per_task_bucket[5m]))  # P95
histogram_quantile(0.99, rate(orchestrator_tokens_per_task_bucket[5m]))  # P99
```

**Implementation**:
```python
tokens_per_task_histogram = registry.histogram(
    "orchestrator_tokens_per_task",
    description="Distribution of tokens consumed per task",
    labels={"model": model_name, "role": role_name},
    buckets=[100, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000]
)
tokens_per_task_histogram.observe(total_tokens_for_task)
```

**Collection Points**:
- After each task completion in Orchestrator
- Extract from HANDBACK block: `tokens.used` (total)
- Label with task's `model` and `role`

---

## Cost Metrics

### 5. `orchestrator_cost_total` (Counter)

**Type**: Counter  
**Description**: Total cost in USD of token consumption  
**Unit**: USD  
**Labels**: `model`, `role`

**Usage**:
```promql
sum(orchestrator_cost_total)              # Total cost
sum(orchestrator_cost_total) by (model)   # Cost by model
sum(orchestrator_cost_total) by (role)    # Cost by role
sum(increase(orchestrator_cost_total[1d])) # Daily cost
```

**Implementation**:
```python
cost_counter = registry.counter(
    "orchestrator_cost_total",
    description="Total cost in USD of token consumption",
    labels={"model": model_name, "role": role_name}
)
cost_counter.inc(task_cost_usd)
```

**Collection Points**:
- After each task completion in Orchestrator
- Calculate from tokens: `cost = (input_tokens * input_price + output_tokens * output_price) / 1000000`
- Use current Claude pricing (as of May 2026)
- Label with task's `model` and `role`

**Pricing Reference** (as of May 2026):
```python
PRICING = {
    "haiku-4.5": {
        "input": 0.80,      # per 1M input tokens
        "output": 4.00,     # per 1M output tokens
    },
    "sonnet-4": {
        "input": 3.00,      # per 1M input tokens
        "output": 15.00,    # per 1M output tokens
    },
    "opus-4": {
        "input": 15.00,     # per 1M input tokens
        "output": 75.00,    # per 1M output tokens
    }
}
```

---

### 6. `orchestrator_cost_per_task_bucket` (Histogram)

**Type**: Histogram  
**Description**: Distribution of task costs in USD  
**Unit**: USD  
**Labels**: `model`, `role`  
**Buckets**: [0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0, +Inf]

**Usage**:
```promql
histogram_quantile(0.50, rate(orchestrator_cost_per_task_bucket[5m]))  # P50 cost
histogram_quantile(0.95, rate(orchestrator_cost_per_task_bucket[5m]))  # P95 cost
histogram_quantile(0.99, rate(orchestrator_cost_per_task_bucket[5m]))  # P99 cost
```

**Implementation**:
```python
cost_per_task_histogram = registry.histogram(
    "orchestrator_cost_per_task",
    description="Distribution of task costs in USD",
    labels={"model": model_name, "role": role_name},
    buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 50.0]
)
cost_per_task_histogram.observe(task_cost_usd)
```

**Collection Points**:
- After each task completion in Orchestrator
- Calculate from tokens using pricing table above
- Label with task's `model` and `role`

---

## Collection Implementation

### Location: `src/orchestration/agents/orchestrator.py`

Add metric collection after HANDBACK processing:

```python
def _record_metrics(self, handback: Dict, task_metadata: Dict) -> None:
    """Record metrics from completed task."""
    
    # Extract data from HANDBACK
    tokens_used = handback.get("tokens", {}).get("used", 0)
    tokens_input = handback.get("tokens", {}).get("input", 0)
    tokens_output = handback.get("tokens", {}).get("output", 0)
    tokens_cached = handback.get("tokens", {}).get("cached", 0)
    
    model = task_metadata.get("model", "unknown")
    role = task_metadata.get("role", "unknown")
    
    # Record token metrics
    self.metrics.counter(
        "orchestrator_tokens_input_total",
        labels={"model": model, "role": role}
    ).inc(tokens_input)
    
    self.metrics.counter(
        "orchestrator_tokens_output_total",
        labels={"model": model, "role": role}
    ).inc(tokens_output)
    
    self.metrics.counter(
        "orchestrator_tokens_cached_total",
        labels={"model": model, "role": role}
    ).inc(tokens_cached)
    
    self.metrics.histogram(
        "orchestrator_tokens_per_task",
        labels={"model": model, "role": role}
    ).observe(tokens_used)
    
    # Calculate and record cost
    cost_usd = self._calculate_cost(model, tokens_input, tokens_output)
    
    self.metrics.counter(
        "orchestrator_cost_total",
        labels={"model": model, "role": role}
    ).inc(cost_usd)
    
    self.metrics.histogram(
        "orchestrator_cost_per_task",
        labels={"model": model, "role": role}
    ).observe(cost_usd)

def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD for token consumption."""
    
    pricing = {
        "haiku-4.5": {"input": 0.80, "output": 4.00},
        "sonnet-4": {"input": 3.00, "output": 15.00},
        "opus-4": {"input": 15.00, "output": 75.00},
    }
    
    rates = pricing.get(model, {"input": 0, "output": 0})
    input_cost = (input_tokens * rates["input"]) / 1_000_000
    output_cost = (output_tokens * rates["output"]) / 1_000_000
    
    return input_cost + output_cost
```

---

## Prometheus Exporter Updates

### Location: `src/orchestration/monitoring/prometheus_exporter.py`

The exporter already supports Counter and Histogram types. No changes needed — it will automatically export all registered metrics.

### Export Format Example

```
# HELP orchestrator_tokens_input_total Total input tokens consumed
# TYPE orchestrator_tokens_input_total counter
orchestrator_tokens_input_total{model="haiku-4.5",role="engineer"} 125000
orchestrator_tokens_input_total{model="sonnet-4",role="senior_engineer"} 45000

# HELP orchestrator_cost_total Total cost in USD of token consumption
# TYPE orchestrator_cost_total counter
orchestrator_cost_total{model="haiku-4.5",role="engineer"} 0.15
orchestrator_cost_total{model="sonnet-4",role="senior_engineer"} 0.85

# HELP orchestrator_tokens_per_task Distribution of tokens consumed per task
# TYPE orchestrator_tokens_per_task histogram
orchestrator_tokens_per_task_bucket{model="haiku-4.5",role="engineer",le="100"} 5
orchestrator_tokens_per_task_bucket{model="haiku-4.5",role="engineer",le="500"} 12
...
orchestrator_tokens_per_task_sum{model="haiku-4.5",role="engineer"} 125000
orchestrator_tokens_per_task_count{model="haiku-4.5",role="engineer"} 42
```

---

## Testing & Validation

### Unit Tests

Create `tests/test_token_cost_metrics.py`:

```python
def test_token_metrics_collection():
    """Test token metrics are collected correctly."""
    registry = MetricsRegistry()
    
    # Simulate task completion
    registry.counter("orchestrator_tokens_input_total", 
                   labels={"model": "haiku-4.5", "role": "engineer"}).inc(1000)
    registry.counter("orchestrator_tokens_output_total",
                   labels={"model": "haiku-4.5", "role": "engineer"}).inc(500)
    
    # Verify
    assert registry.get_all()["orchestrator_tokens_input_total{model=haiku-4.5,role=engineer}"].value == 1000

def test_cost_calculation():
    """Test cost calculation is accurate."""
    orchestrator = Orchestrator()
    
    # Test Haiku pricing
    cost = orchestrator._calculate_cost("haiku-4.5", 1_000_000, 1_000_000)
    assert cost == pytest.approx(4.80, rel=0.01)  # 0.80 + 4.00
    
    # Test Sonnet pricing
    cost = orchestrator._calculate_cost("sonnet-4", 1_000_000, 1_000_000)
    assert cost == pytest.approx(18.00, rel=0.01)  # 3.00 + 15.00

def test_histogram_percentiles():
    """Test histogram percentile calculations."""
    registry = MetricsRegistry()
    histogram = registry.histogram("orchestrator_tokens_per_task")
    
    # Add observations
    for tokens in [100, 200, 500, 1000, 2000, 5000]:
        histogram.observe(tokens)
    
    # Verify percentiles
    assert histogram.percentile(50) is not None
    assert histogram.percentile(95) is not None
```

### Integration Tests

1. Run orchestrator with sample tasks
2. Export metrics to Prometheus format
3. Validate all metrics are present
4. Verify metric values are correct
5. Check labels are properly formatted

### Prometheus Query Validation

Test all dashboard queries in Prometheus UI:

```promql
# Token throughput
rate(orchestrator_tokens_input_total[1m])
rate(orchestrator_tokens_output_total[1m])
rate(orchestrator_tokens_cached_total[1m])

# Token distribution
histogram_quantile(0.50, rate(orchestrator_tokens_per_task_bucket[5m]))
histogram_quantile(0.95, rate(orchestrator_tokens_per_task_bucket[5m]))

# Cost metrics
sum(orchestrator_cost_total)
sum(orchestrator_cost_total) by (model)
sum(orchestrator_cost_total) by (role)

# Cost distribution
histogram_quantile(0.50, rate(orchestrator_cost_per_task_bucket[5m]))
histogram_quantile(0.95, rate(orchestrator_cost_per_task_bucket[5m]))
```

---

## Deployment Checklist

- [ ] Implement `_record_metrics()` in Orchestrator
- [ ] Implement `_calculate_cost()` in Orchestrator
- [ ] Update pricing table with current rates
- [ ] Create unit tests for metric collection
- [ ] Create integration tests for cost calculation
- [ ] Test Prometheus export format
- [ ] Validate all dashboard queries
- [ ] Deploy to staging environment
- [ ] Verify metrics appear in Prometheus
- [ ] Verify dashboard panels populate with data
- [ ] Deploy to production
- [ ] Monitor metrics collection for 24 hours
- [ ] Create runbook for metric troubleshooting

---

## Troubleshooting

### Metrics Not Appearing

1. Check Orchestrator is running and processing tasks
2. Verify metrics registry is initialized
3. Check PrometheusExporter is exporting to `/metrics` endpoint
4. Verify Prometheus is scraping the endpoint
5. Check Prometheus targets page for scrape status

### Incorrect Cost Values

1. Verify pricing table is up-to-date
2. Check token counts in HANDBACK blocks
3. Validate cost calculation formula
4. Compare with manual calculation

### Missing Labels

1. Verify task_metadata contains `model` and `role`
2. Check label values are strings (not None)
3. Validate label names match dashboard queries

---

## References

- Prometheus Metrics Types: https://prometheus.io/docs/concepts/metric_types/
- Grafana Dashboard JSON: https://grafana.com/docs/grafana/latest/dashboards/json-model/
- Claude API Pricing: https://www.anthropic.com/pricing
- Prompt Caching: https://docs.anthropic.com/en/docs/build-a-chatbot-with-an-api

---

**Implementation Status**: Ready for DELEGATE 3 follow-up  
**Estimated Effort**: 4-6 hours  
**Complexity**: Medium (straightforward metric collection, requires API integration for cache metrics)
