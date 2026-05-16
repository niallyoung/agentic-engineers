# Cost Attribution Logic — Implementation Guide

## Overview

The Cost Attribution system allocates task costs to agents based on token contribution. This enables tracking costs by role, model, task type, and time period for financial visibility and optimization.

## Architecture

### Components

1. **CostAttributor** (`cost_attributor.py`)
   - Core cost allocation logic
   - Weighted by token contribution
   - Handles edge cases (zero tokens, single agent, etc.)
   - Thread-safe for concurrent operations

2. **CostAttributionMetrics** (`cost_attribution_metrics.py`)
   - Integration bridge with MetricsRegistry
   - Records attribution results to metrics
   - Provides retrieval API for aggregated costs

3. **MetricsRegistry** (existing)
   - Central metrics collection
   - Cost metrics with labels (role, model, task_type, date)
   - Counters, gauges, and histograms

## Cost Attribution Algorithm

### Basic Principle: Token-Weighted Distribution

Cost is allocated to agents proportionally to their token contribution:

```
cost_per_agent = total_cost × (tokens_per_agent / total_tokens)
```

### Example

Task with 2 agents:
- Engineer: 10,000 tokens, Haiku model
- Senior Engineer: 20,000 tokens, Sonnet model
- Total cost: $0.45

Attribution:
- Engineer: $0.45 × (10,000 / 30,000) = $0.15 (33%)
- Senior Engineer: $0.45 × (20,000 / 30,000) = $0.30 (67%)

### Edge Cases

1. **Zero Tokens**: Cost splits equally among agents
2. **Zero Cost**: All agents get $0.00
3. **Single Agent**: Agent receives 100% of cost
4. **Missing Agent in Tokens Dict**: Treated as 0 tokens

## Attribution Dimensions

Costs are tracked by four dimensions:

### 1. Role (Agent Type)
- `engineer` — Implementation tasks
- `senior_engineer` — Complex tasks, reviews
- `quality_engineer` — Quality assurance
- `security_engineer` — Security reviews
- `orchestrator` — Routing and coordination

### 2. Model
- `haiku-4-5` — Fast, cheap (0.33× cost)
- `sonnet-4-6` — Balanced (1.0× cost)
- `opus-4-7` — Powerful (3.0× cost)
- `gpt-5-4` — GPT-5 parity (1.0× cost)
- `gpt-5-5` — GPT-5 premium (7.5× cost)

### 3. Task Type
- `implementation` — Code implementation
- `review` — Code/design review
- `routing` — Task routing decision
- `analysis` — Data analysis
- `documentation` — Documentation writing

### 4. Time Period
- **Hourly**: Tracked via timestamp
- **Daily**: Aggregated by date (YYYY-MM-DD)
- **Weekly**: Derived from daily data
- **Monthly**: Derived from daily data

## API Reference

### CostAttributor

#### `attribute_cost()`

Allocate task cost to agents based on token contribution.

```python
from src.orchestration.models.cost_attributor import CostAttributor

attributor = CostAttributor()

result = attributor.attribute_cost(
    task_id="task-001",
    agents=["engineer", "senior_engineer"],
    tokens_per_agent={"engineer": 10000, "senior_engineer": 20000},
    total_cost=0.45,
    roles_per_agent={"engineer": "engineer", "senior_engineer": "senior_engineer"},
    models_per_agent={"engineer": "haiku-4-5", "senior_engineer": "sonnet-4-6"},
    task_type="implementation",
    timestamp="2025-01-15T10:30:00Z",
)

print(result.summary())
# Output:
# Cost Attribution: task-001
#   Total cost: $0.4500
#   Total tokens: 30,000
#   Timestamp: 2025-01-15T10:30:00Z
#
# Agent shares:
#   engineer [engineer/haiku-4-5]: $0.1500 (33.3%) (10,000 tokens)
#   senior_engineer [senior_engineer/sonnet-4-6]: $0.3000 (66.7%) (20,000 tokens)
```

#### `aggregate_by_role()`

Aggregate costs across multiple tasks by role.

```python
results = [result1, result2, result3]  # CostAttributionResult objects
by_role = attributor.aggregate_by_role(results)

# Output: {"engineer": 0.45, "senior_engineer": 0.75, ...}
```

#### `aggregate_by_model()`

Aggregate costs by model.

```python
by_model = attributor.aggregate_by_model(results)
# Output: {"haiku-4-5": 0.30, "sonnet-4-6": 0.90, ...}
```

#### `aggregate_by_task_type()`

Aggregate costs by task type.

```python
by_type = attributor.aggregate_by_task_type(results)
# Output: {"implementation": 0.60, "review": 0.45, ...}
```

#### `aggregate_by_date()`

Aggregate costs by date.

```python
by_date = attributor.aggregate_by_date(results)
# Output: {"2025-01-15": 0.80, "2025-01-16": 0.45, ...}
```

#### `get_history()`

Retrieve all attribution results.

```python
history = attributor.get_history()
# Returns: List[CostAttributionResult]
```

#### `get_task_attribution(task_id)`

Retrieve attribution for a specific task.

```python
result = attributor.get_task_attribution("task-001")
# Returns: CostAttributionResult or None
```

### CostAttributionMetrics

#### `record_attribution()`

Record attribution result to MetricsRegistry.

```python
from src.orchestration.monitoring.metrics import MetricsRegistry, create_cost_metrics
from src.orchestration.models.cost_attribution_metrics import CostAttributionMetrics

registry = MetricsRegistry()
cost_metrics = create_cost_metrics(registry)

attribution_metrics = CostAttributionMetrics(registry, cost_metrics)

# After attribution
result = attributor.attribute_cost(...)
attribution_metrics.record_attribution(result)
```

#### `get_cost_by_role()`

Retrieve aggregated costs by role from metrics.

```python
by_role = attribution_metrics.get_cost_by_role()
# Output: {"engineer": 0.45, "senior_engineer": 0.75, ...}
```

#### `get_cost_by_model()`

Retrieve aggregated costs by model.

```python
by_model = attribution_metrics.get_cost_by_model()
```

#### `get_cost_by_task_type()`

Retrieve aggregated costs by task type.

```python
by_type = attribution_metrics.get_cost_by_task_type()
```

#### `get_cost_by_date()`

Retrieve daily aggregated costs.

```python
by_date = attribution_metrics.get_cost_by_date()
```

## Usage Examples

### Example 1: Simple Single-Agent Task

```python
attributor = CostAttributor()

result = attributor.attribute_cost(
    task_id="task-simple",
    agents=["engineer"],
    tokens_per_agent={"engineer": 5000},
    total_cost=0.15,
    roles_per_agent={"engineer": "engineer"},
    models_per_agent={"engineer": "haiku-4-5"},
    task_type="implementation",
)

print(f"Engineer cost: ${result.agent_shares['engineer'].cost:.2f}")
# Output: Engineer cost: $0.15
```

### Example 2: Multi-Agent Collaborative Task

```python
result = attributor.attribute_cost(
    task_id="task-collab",
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

for agent, share in result.agent_shares.items():
    print(f"{agent}: ${share.cost:.4f} ({share.weight*100:.1f}%)")

# Output:
# engineer: $0.1920 (32.0%)
# senior_engineer: $0.2880 (48.0%)
# quality_engineer: $0.1200 (20.0%)
```

### Example 3: Daily Cost Aggregation

```python
attributor = CostAttributor()
results = []

# Simulate 5 tasks throughout the day
for i in range(5):
    result = attributor.attribute_cost(
        task_id=f"task-{i:03d}",
        agents=["engineer"],
        tokens_per_agent={"engineer": 5000 + i*1000},
        total_cost=0.10 + i*0.05,
        roles_per_agent={"engineer": "engineer"},
        models_per_agent={"engineer": "haiku-4-5"},
        timestamp=f"2025-01-15T{10+i:02d}:00:00Z",
    )
    results.append(result)

# Aggregate by date
by_date = attributor.aggregate_by_date(results)
print(f"Daily cost (2025-01-15): ${by_date['2025-01-15']:.2f}")
# Output: Daily cost (2025-01-15): $1.50

# Aggregate by role
by_role = attributor.aggregate_by_role(results)
print(f"Engineer cost: ${by_role['engineer']:.2f}")
# Output: Engineer cost: $1.50
```

### Example 4: Cost Analysis with Metrics Integration

```python
from src.orchestration.monitoring.metrics import MetricsRegistry, create_cost_metrics
from src.orchestration.models.cost_attribution_metrics import CostAttributionMetrics

# Setup
registry = MetricsRegistry()
cost_metrics = create_cost_metrics(registry)
attribution_metrics = CostAttributionMetrics(registry, cost_metrics)
attributor = CostAttributor()

# Process multiple tasks
tasks = [
    ("task-001", ["engineer"], {"engineer": 5000}, 0.15, "implementation"),
    ("task-002", ["senior_engineer"], {"senior_engineer": 8000}, 0.40, "review"),
    ("task-003", ["engineer", "quality_engineer"], 
     {"engineer": 6000, "quality_engineer": 4000}, 0.25, "implementation"),
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
    attribution_metrics.record_attribution(result)

# Retrieve aggregated costs
print("Costs by role:")
for role, cost in attribution_metrics.get_cost_by_role().items():
    print(f"  {role}: ${cost:.2f}")

print("\nCosts by task type:")
for task_type, cost in attribution_metrics.get_cost_by_task_type().items():
    print(f"  {task_type}: ${cost:.2f}")

# Output:
# Costs by role:
#   engineer: $0.30
#   senior_engineer: $0.40
#   quality_engineer: $0.10
#
# Costs by task type:
#   implementation: $0.40
#   review: $0.40
```

## Data Structures

### CostAttributionResult

```python
@dataclass
class CostAttributionResult:
    task_id: str                              # Unique task identifier
    total_cost: float                         # Total task cost in USD
    total_tokens: int                         # Total tokens consumed
    timestamp: str                            # ISO8601 timestamp
    agent_shares: Dict[str, AgentCostShare]   # Cost allocation per agent
```

### AgentCostShare

```python
@dataclass
class AgentCostShare:
    agent: str                    # Agent name
    role: str                     # Agent role (engineer, senior_engineer, etc.)
    model: str                    # Model used (haiku-4-5, sonnet-4-6, etc.)
    tokens: int                   # Tokens consumed by this agent
    cost: float                   # Allocated cost in USD
    weight: float                 # Token contribution as fraction (0.0-1.0)
    task_type: Optional[str]      # Task type (implementation, review, etc.)
    timestamp: Optional[str]      # ISO8601 timestamp
```

### DimensionalCosts

```python
@dataclass
class DimensionalCosts:
    by_role: Dict[str, float]          # Costs aggregated by role
    by_model: Dict[str, float]         # Costs aggregated by model
    by_task_type: Dict[str, float]     # Costs aggregated by task type
    by_date: Dict[str, float]          # Costs aggregated by date
```

## Metrics Registry Integration

### Cost Metrics Created

The `create_cost_metrics()` function creates the following metrics:

1. **Counters** (monotonically increasing):
   - `orchestrator_cost_usd_by_role` — Total cost by role
   - `orchestrator_cost_usd_by_model` — Total cost by model
   - `orchestrator_cost_usd_by_task_type` — Total cost by task type

2. **Gauges** (can increase/decrease):
   - `orchestrator_cost_usd_daily` — Daily cost aggregation

3. **Histograms** (distribution tracking):
   - `orchestrator_cost_per_task` — Cost distribution per task
   - `orchestrator_cost_per_quality_point` — Cost efficiency metric

### Metric Labels

Metrics support labels for dimensional analysis:

```python
# Example: Cost by role
counter = registry.counter(
    "orchestrator_cost_usd_by_role",
    labels={"role": "engineer"}
)
counter.inc(0.15)

# Example: Cost by date
gauge = registry.gauge(
    "orchestrator_cost_usd_daily",
    labels={"date": "2025-01-15"}
)
gauge.set(1.50)
```

## Thread Safety

Both `CostAttributor` and `CostAttributionMetrics` are thread-safe:

- `CostAttributor` uses `threading.Lock()` for history tracking
- `MetricsRegistry` uses `threading.Lock()` for metric updates
- Safe for concurrent task attribution in multi-threaded environments

## Testing

### Test Coverage

- **27 tests** for `CostAttributor`
  - Basic attribution (single/multiple agents)
  - Edge cases (zero tokens, zero cost, empty agents)
  - Metadata preservation (role, model, task type, timestamp)
  - Aggregation by all dimensions
  - History tracking and retrieval
  - Utility methods

- **8 tests** for `CostAttributionMetrics`
  - Recording attribution results
  - Retrieving costs by dimension
  - Multi-task aggregation

### Running Tests

```bash
# Run all cost attribution tests
python3 -m pytest tests/test_cost_attributor.py -v
python3 -m pytest tests/test_cost_attribution_metrics.py -v

# Run with coverage
python3 -m pytest tests/test_cost_attributor.py --cov=src.orchestration.models.cost_attributor
```

## Performance Characteristics

- **Attribution time**: O(n) where n = number of agents
- **Aggregation time**: O(m) where m = number of results
- **Memory**: O(m) for history storage
- **Thread safety**: Lock-based (minimal contention expected)

## Future Enhancements

1. **Historical Analysis**
   - Time-series cost trends
   - Cost forecasting
   - Anomaly detection

2. **Cost Optimization**
   - Model downgrade recommendations
   - Token efficiency improvements
   - Cost-quality tradeoff analysis

3. **Reporting**
   - Daily/weekly/monthly reports
   - Cost breakdown by department
   - Budget tracking and alerts

4. **Integration**
   - Prometheus export
   - Grafana dashboards
   - Cost allocation to billing systems

## Troubleshooting

### Issue: Costs don't sum correctly

**Cause**: Missing agents in `tokens_per_agent` dict
**Solution**: Ensure all agents in `agents` list have entries in `tokens_per_agent`

### Issue: Timestamp format incorrect

**Cause**: Custom timestamp not in ISO8601 format
**Solution**: Use format `YYYY-MM-DDTHH:MM:SSZ` (e.g., `2025-01-15T10:30:00Z`)

### Issue: Metrics not updating

**Cause**: `record_attribution()` not called after attribution
**Solution**: Always call `attribution_metrics.record_attribution(result)` after `attributor.attribute_cost()`

## References

- **Token Visibility System**: See `docs/TOKEN-VISIBILITY.md`
- **Metrics Registry**: See `src/orchestration/monitoring/metrics.py`
- **Cost Quality Analyzer**: See `src/orchestration/models/cost_quality_analyzer.py`
- **Model Selector**: See `src/orchestration/models/model_selector.py`
