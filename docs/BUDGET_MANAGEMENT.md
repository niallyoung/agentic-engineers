# Copilot Token Tracking & Budget Management

## Overview

This module provides comprehensive token usage tracking, cost calculation, and budget management for Copilot tasks across different AI model pricing tiers.

### Key Features

- **Per-task cost tracking** with full token usage breakdown
- **Session-level cost aggregation** and reporting
- **Multi-tier pricing support** for Haiku, Sonnet, and Opus models
- **Real-time budget monitoring** with configurable alert thresholds
- **Hard spend limits** that prevent task execution when exceeded
- **Cost forecasting** based on historical spending patterns
- **Savings analysis** and optimization recommendations
- **Session persistence** with JSON export/import
- **CLI interface** for budget management commands

---

## Architecture

### Components

1. **CostTracker** (`src/copilot/cost_tracker.py`)
   - Records token usage per task
   - Calculates costs using pricing tables
   - Aggregates session-level statistics
   - Exports/imports session data

2. **BudgetManager** (`src/copilot/budget_manager.py`)
   - Monitors spending against budget limits
   - Generates alerts at threshold levels (50%, 75%, 90%, 100%)
   - Enforces hard blocks when budget exceeded
   - Forecasts remaining budget and tasks
   - Generates savings recommendations

3. **BudgetCLI** (`src/copilot/cli_budget.py`)
   - Command-line interface for budget operations
   - Status reporting
   - Cost breakdown analysis
   - Historical tracking and forecasting
   - Recommendation generation

### Pricing Model

The module uses a three-tier pricing model matching the Copilot agent roles:

| Model | Cost (per M tokens) | Tier | Role |
|-------|-------------------|------|------|
| claude-haiku-4.5 | Input: $1.00, Output: $5.00 | Cheap | Engineer, Orchestrator |
| claude-sonnet-5 | Input: $3.00, Output: $15.00 | Medium | Senior, Lead, QE, Model Engineer |
| claude-opus-5 | Input: $5.00, Output: $25.00 | Premium | Principal Engineer |
| claude-fable-5 | Input: $10.00, Output: $50.00 | Premium | Security Engineer |
| claude-opus-4.8 | Input: $5.00, Output: $25.00 | Premium | Fallback tier |

Rates are Anthropic list price per million tokens. The previous table priced
Opus at $15/$75 and Haiku at $0.80/$4.00 — those were Claude 3-era figures and
overstated Opus spend 3x. Sonnet 5 keeps Sonnet 4.6's rate but emits ~30% more
tokens for the same text, so budgets drain ~30% faster at an unchanged price.

Cached tokens receive a 10% discount on input token cost.

---

## Usage

### Basic Token Tracking

```python
from src.copilot.cost_tracker import CostTracker

# Create a tracker
tracker = CostTracker(session_id="my-session")

# Record a task
task_cost = tracker.record_task(
    task_id="TASK-001",
    model="claude-haiku-4.5",
    input_tokens=1000,
    output_tokens=500,
    cached_tokens=100,
    duration_ms=2000,
    metadata={"user_id": "user123"}
)

# Get session statistics
print(f"Total cost: ${tracker.get_session_total_cost():.3f}")
print(f"Total tokens: {tracker.get_session_total_tokens().total_tokens}")
print(f"Average cost per task: ${tracker.get_average_cost_per_task():.4f}")

# Export to JSON
json_data = tracker.export_to_json()
```

### Budget Management

```python
from src.copilot.budget_manager import BudgetManager

# Create budget manager
budget_mgr = BudgetManager(
    session_budget_usd=100.0,
    max_cost_per_task_usd=50.0
)

# Check if a task can proceed
can_proceed, reason = budget_mgr.check_budget_available(
    tracker,
    estimated_cost_usd=5.0
)

if not can_proceed:
    print(f"Task blocked: {reason}")

# Record a task and check alerts
alert = budget_mgr.record_task_and_check_alerts(
    tracker,
    task_id="TASK-002",
    model="claude-sonnet-4.6",
    input_tokens=5000,
    output_tokens=2500,
    duration_ms=3000
)

if alert:
    print(f"⚠️ {alert.message}")

# Get budget status
status = budget_mgr.get_budget_status(tracker)
print(f"Status: {status['status']}")
print(f"Spent: ${status['current_cost_usd']:.2f} of ${status['session_budget_usd']:.2f}")
print(f"Remaining: ${status['remaining_budget_usd']:.2f}")

# Get forecast
forecast = budget_mgr.forecast_remaining_budget(tracker)
if forecast["forecast_available"]:
    print(f"Estimated tasks remaining: {forecast['estimated_tasks_remaining']}")

# Get recommendations
recommendations = budget_mgr.get_savings_recommendations(tracker)
for rec in recommendations:
    print(f"[{rec['severity']}] {rec['suggestion']}")

# Generate full report
report = budget_mgr.get_report(tracker)
print(report)
```

### CLI Usage

```bash
# Show budget status
python -m src.copilot.cli_budget status

# Show detailed budget status
python -m src.copilot.cli_budget status --verbose

# Generate budget report
python -m src.copilot.cli_budget report
python -m src.copilot.cli_budget report --output report.txt

# Show cost breakdown by model
python -m src.copilot.cli_budget breakdown
python -m src.copilot.cli_budget breakdown --format json

# Forecast budget exhaustion
python -m src.copilot.cli_budget forecast --budget 100.0

# Get cost optimization recommendations
python -m src.copilot.cli_budget recommendations
python -m src.copilot.cli_budget recommendations --min-severity high

# Show recent task costs
python -m src.copilot.cli_budget history
python -m src.copilot.cli_budget history --limit 20
python -m src.copilot.cli_budget history --model claude-sonnet-4.6
```

---

## Alert Thresholds

Budget alerts are triggered at configurable spending levels:

| Threshold | Level | Action |
|-----------|-------|--------|
| 50% | INFO | Informational notification |
| 75% | WARNING | Warning notification |
| 90% | CRITICAL | Critical warning |
| 100% | BLOCKED | Task execution blocked |

Default thresholds can be customized when creating a BudgetManager:

```python
budget_mgr = BudgetManager(
    session_budget_usd=100.0,
    alert_thresholds={
        50: AlertLevel.INFO,
        75: AlertLevel.WARNING,
        90: AlertLevel.CRITICAL,
        100: AlertLevel.BLOCKED,
    }
)
```

---

## Cost Forecasting

The budget manager uses historical spending data to forecast:

1. **Average cost per task** - Mean of historical task costs
2. **Cost variance** - Standard deviation of task costs
3. **Conservative estimate** - Mean + 1 standard deviation
4. **Remaining tasks** - Budget remaining ÷ conservative estimate
5. **Time to exhaustion** - Estimated tasks × average execution time

```python
forecast = budget_mgr.forecast_remaining_budget(tracker)
if forecast["forecast_available"]:
    print(f"Average cost: ${forecast['average_cost_per_task']:.3f}")
    print(f"Conservative: ${forecast['conservative_cost_per_task']:.3f}")
    print(f"Tasks remaining: {forecast['estimated_tasks_remaining']}")
    print(f"Hours remaining: {forecast['estimated_time_to_exhaustion_ms']/3600000:.1f}")
```

---

## Savings Recommendations

The system analyzes spending patterns and recommends optimizations:

### Model Downgrade
If expensive models (Opus) comprise >40% of costs:
```
[HIGH] Consider routing more tasks to cheaper models. 
claude-opus-4.8 comprises 65.2% of costs.
Potential savings: $42.50
```

### Cache Optimization
If cached tokens <5% of total:
```
[MEDIUM] Enable prompt caching for frequently-used context. 
Current cache ratio is very low.
```

### Task Optimization
If individual tasks exceed 3x average cost:
```
[MEDIUM] Task TASK-001 cost $0.150 (5.0x average). 
Consider breaking into smaller tasks.
```

---

## Session Persistence

Save and load sessions for analysis and archival:

```python
# Save to JSON
tracker.save_to_file("session_2024_05_30.json")

# Load from JSON
tracker = CostTracker()
tracker.load_from_file("session_2024_05_30.json")
```

JSON format includes:
- Session metadata (ID, start time, duration)
- Total cost and token counts
- Efficiency metrics
- Per-task records with full details
- Cost breakdown by model

---

## Integration with Copilot Harness

### Pre-Task Budget Check

```python
budget_mgr = BudgetManager(
    session_budget_usd=FLAGS.budget,
    max_cost_per_task_usd=FLAGS.max_cost_per_task
)

def execute_task(task_id, model, prompt):
    # Estimate cost
    estimated_tokens = len(prompt.split()) * 1.3  # rough estimate
    estimated_cost = pricing.estimate_cost(model, estimated_tokens)
    
    # Check budget
    can_proceed, reason = budget_mgr.check_budget_available(
        tracker,
        estimated_cost
    )
    
    if not can_proceed:
        logger.error(reason)
        return None
    
    # Execute task
    response = invoke_model(model, prompt)
    
    # Record actual cost
    alert = budget_mgr.record_task_and_check_alerts(
        tracker,
        task_id=task_id,
        model=model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        cached_tokens=response.usage.cached_tokens,
        duration_ms=response.latency_ms
    )
    
    if alert:
        logger.warning(f"Budget alert: {alert.message}")
    
    return response
```

---

## Data Structures

### TokenUsage
```python
@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.cached_tokens
```

### TaskCost
```python
@dataclass
class TaskCost:
    task_id: str
    model: str
    timestamp: datetime
    token_usage: TokenUsage
    cost_usd: float
    duration_ms: int = 0
    metadata: Dict = field(default_factory=dict)
```

### BudgetAlert
```python
@dataclass
class BudgetAlert:
    level: AlertLevel  # INFO | WARNING | CRITICAL | BLOCKED
    threshold_percent: int
    current_cost: float
    budget_limit: float
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
```

---

## Testing

Comprehensive test suite with 50+ unit tests covering:

- Token usage tracking accuracy
- Cost calculation for all pricing tiers
- Budget enforcement and hard blocks
- Alert generation at all thresholds
- Forecasting accuracy
- Savings recommendations
- Session persistence
- CLI command execution
- Edge cases (zero tokens, very large amounts, etc.)

Run tests:
```bash
python3 -m pytest tests/copilot/test_cost_tracker.py -v
```

With coverage:
```bash
python3 -m pytest tests/copilot/test_cost_tracker.py -v \
    --cov=src/copilot \
    --cov-report=term-missing
```

---

## Performance

- Cost calculation: <1ms per task
- Budget check: <0.1ms
- JSON export: <10ms for 1000 tasks
- Forecast calculation: <50ms with 100 historical tasks

All operations are thread-safe with no external dependencies beyond Python stdlib.

---

## Configuration

### Custom Pricing

```python
from src.copilot.cost_tracker import PricingTable, PricingTier

custom_pricing = {
    "my-model": PricingTier(
        model="my-model",
        input_cost_per_mtok=2.0,
        output_cost_per_mtok=10.0,
        cached_cost_per_mtok=0.2,
    )
}

pricing_table = PricingTable(custom_pricing=custom_pricing)
tracker = CostTracker(pricing_table=pricing_table)
```

### Custom Alert Thresholds

```python
from src.copilot.budget_manager import AlertLevel

budget_mgr = BudgetManager(
    session_budget_usd=100.0,
    alert_thresholds={
        25: AlertLevel.INFO,
        60: AlertLevel.WARNING,
        85: AlertLevel.CRITICAL,
        100: AlertLevel.BLOCKED,
    }
)
```

---

## Troubleshooting

### "Session budget must be positive"
Ensure budget_usd > 0. Use a small value like 0.01 for testing.

### "Task cost exceeds per-task limit"
Set max_cost_per_task_usd to match expected model costs, or increase the limit.

### "No forecast available"
Forecast requires at least 2 historical tasks. Execute a few tasks first.

### Missing coverage in CLI
The CLI module has lower coverage because many command branches are tested through integration testing rather than unit tests.

---

## API Reference

See inline docstrings for complete API documentation:

```bash
python3 -c "from src.copilot.cost_tracker import CostTracker; help(CostTracker)"
python3 -c "from src.copilot.budget_manager import BudgetManager; help(BudgetManager)"
python3 -c "from src.copilot.cli_budget import BudgetCLI; help(BudgetCLI)"
```
