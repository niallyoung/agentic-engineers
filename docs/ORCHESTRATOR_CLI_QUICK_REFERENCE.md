# OrchestratorCLI — Quick Reference Guide

## Installation & Initialization

```python
from src.orchestration.monitoring.orchestrator_cli import OrchestratorCLI
from src.orchestration.monitoring.token_tracker import TokenTracker
from src.orchestration.monitoring.metrics import MetricsRegistry

# Initialize
registry = MetricsRegistry()
tracker = TokenTracker(registry)
cli = OrchestratorCLI(token_tracker=tracker)
```

## Core API

### Record Task Completion
```python
cli.on_task_complete(delegate, handback)
```

**Parameters**:
- `delegate`: Dict with `task_id`, `role`, `model`, `effort`
- `handback`: Dict with `task_id`, `status`, `tokens_in`, `tokens_out`, `cost_usd`

**Behavior**:
- Records metrics in TokenTracker
- Prints formatted task line
- Checks budget status
- Invokes callback if budget threshold exceeded

### Print Session Summary
```python
cli.print_session_summary()
```

**Output**:
- Task count
- Total tokens (input, output, cached)
- Total cost with budget percentage
- Per-agent breakdown sorted by cost
- Final budget status alert

### Check Task Blocking
```python
if cli.should_block_new_tasks():
    queue.pause()
```

**Returns**: `True` only when budget is BLOCKED (100%+)

### Get Session Statistics
```python
stats = cli.get_session_stats()
print(f"Tasks: {stats.task_count}")
print(f"Cost: ${stats.total_cost_usd:.2f}")
print(f"Tokens: {stats.effective_tokens:,}")
```

### Get Budget Status
```python
result = cli.get_budget_status()
print(f"Status: {result.status.value}")
print(f"Used: {result.pct_used:.1f}%")
print(f"Remaining: ${result.remaining_usd:.2f}")
```

### Reset Session
```python
cli.reset_session()
```

**Effect**: Clears all recorded metrics

---

## Configuration Options

### Custom Budget Config
```python
cli = OrchestratorCLI(
    token_tracker=tracker,
    budget_config_path=Path("config/token_budget.yaml"),
)
```

**YAML Format**:
```yaml
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
```

### No-Color Mode (for CI/CD)
```python
cli = OrchestratorCLI(
    token_tracker=tracker,
    no_color=True,
)
```

### Budget Callback
```python
def on_budget_exceeded(result):
    if result.status == BudgetStatus.WARNING:
        print(f"⚠️  {result.message}")
    elif result.status == BudgetStatus.CRITICAL:
        print(f"🚨 {result.message}")
    elif result.status == BudgetStatus.BLOCKED:
        print(f"🛑 {result.message}")

cli = OrchestratorCLI(
    token_tracker=tracker,
    on_budget_exceeded=on_budget_exceeded,
)
```

---

## Budget Thresholds

| Status | Percentage | Action |
|--------|-----------|--------|
| OK | < 70% | Continue normally |
| WARNING | 70-89% | Alert but continue |
| CRITICAL | 90-99% | Alert and consider pausing |
| BLOCKED | ≥ 100% | Block all new tasks |

---

## Orchestrator Integration Pattern

```python
# Session initialization
cli = OrchestratorCLI(
    token_tracker=tracker,
    budget_config_path=Path("config/token_budget.yaml"),
    on_budget_exceeded=handle_budget_alert,
)

# Task loop
while queue.has_tasks():
    delegate = queue.pop()
    
    try:
        handback = invoke_agent(delegate)
    except Exception as e:
        handback = create_synthetic_handback(delegate, error=str(e))
    
    # Record metrics and check budget
    cli.on_task_complete(delegate, handback)
    
    # Block if exhausted
    if cli.should_block_new_tasks():
        queue.pause()
        break

# Session finalization
cli.print_session_summary()
cli.reset_session()
```

---

## Example: Budget Callback Handler

```python
def handle_budget_alert(result):
    """Custom budget alert handler."""
    
    if result.status == BudgetStatus.WARNING:
        # Log warning but continue
        logger.warning(f"Budget at {result.pct_used:.1f}%: {result.message}")
    
    elif result.status == BudgetStatus.CRITICAL:
        # Log critical and notify
        logger.critical(f"Budget critical: {result.message}")
        send_slack_alert(f"Budget at {result.pct_used:.1f}%")
    
    elif result.status == BudgetStatus.BLOCKED:
        # Log blocked and escalate
        logger.critical(f"Budget exhausted: {result.message}")
        send_slack_alert("Budget exhausted - pausing tasks")
        send_email_alert("budget-alerts@company.com", result.message)

cli = OrchestratorCLI(
    token_tracker=tracker,
    on_budget_exceeded=handle_budget_alert,
)
```

---

## Example: Per-Agent Statistics

```python
stats = cli.get_session_stats()

print(f"Total tasks: {stats.task_count}")
print(f"Total cost: ${stats.total_cost_usd:.2f}")

for agent in sorted(stats.agent_tokens.keys()):
    tokens = stats.agent_tokens[agent]
    cost = stats.agent_costs[agent]
    count = stats.agent_counts[agent]
    pct = (tokens / stats.effective_tokens * 100) if stats.effective_tokens > 0 else 0
    
    print(f"{agent:20} {tokens:6,} tokens ({pct:5.1f}%) ${cost:.2f} ({count} tasks)")
```

---

## Common Patterns

### Pattern 1: Basic Session Tracking
```python
cli = OrchestratorCLI(token_tracker=tracker)

for delegate in tasks:
    handback = invoke_agent(delegate)
    cli.on_task_complete(delegate, handback)

cli.print_session_summary()
```

### Pattern 2: Budget-Aware Task Processing
```python
cli = OrchestratorCLI(token_tracker=tracker)

for delegate in tasks:
    if cli.should_block_new_tasks():
        break
    
    handback = invoke_agent(delegate)
    cli.on_task_complete(delegate, handback)

cli.print_session_summary()
```

### Pattern 3: Multi-Session Workflow
```python
cli = OrchestratorCLI(token_tracker=tracker)

for session_num in range(num_sessions):
    print(f"\n--- Session {session_num} ---")
    
    for delegate in get_session_tasks(session_num):
        handback = invoke_agent(delegate)
        cli.on_task_complete(delegate, handback)
    
    cli.print_session_summary()
    cli.reset_session()
```

### Pattern 4: Custom Budget Enforcement
```python
def enforce_budget(cli, queue):
    """Custom budget enforcement logic."""
    
    while queue.has_tasks():
        budget = cli.get_budget_status()
        
        if budget.status == BudgetStatus.BLOCKED:
            print("Budget exhausted - stopping")
            break
        elif budget.status == BudgetStatus.CRITICAL:
            print(f"Budget critical ({budget.pct_used:.1f}%) - processing only high-priority tasks")
            delegate = queue.pop_high_priority()
        else:
            delegate = queue.pop()
        
        handback = invoke_agent(delegate)
        cli.on_task_complete(delegate, handback)

enforce_budget(cli, queue)
cli.print_session_summary()
```

---

## Troubleshooting

### Issue: Budget alerts not firing
**Solution**: Ensure `on_budget_exceeded` callback is provided or check console output for default alerts

### Issue: No-color mode not working
**Solution**: Set `no_color=True` in OrchestratorCLI constructor or set `NO_COLOR` environment variable

### Issue: Missing task_id error
**Solution**: Ensure HANDBACK dict contains `task_id` field

### Issue: Budget status shows BLOCKED but tasks still processing
**Solution**: Check that `should_block_new_tasks()` is being called before accepting new tasks

---

## Performance Notes

- **on_task_complete()**: O(1) - Constant time
- **print_session_summary()**: O(n) - Linear in number of agents
- **should_block_new_tasks()**: O(1) - Single budget check
- **get_session_stats()**: O(n) - Linear in number of tasks
- **reset_session()**: O(n) - Clears all metrics

Memory overhead is minimal (delegates to TokenTracker).

---

## Related Files

- **Implementation**: `src/orchestration/monitoring/orchestrator_cli.py`
- **Tests**: `tests/test_orchestrator_cli.py` (30 tests)
- **Examples**: `examples/orchestrator_cli_examples.py` (8 examples)
- **Documentation**: `ORCHESTRATOR_CLI_IMPLEMENTATION.md`

---

## API Reference

### OrchestratorCLI Methods

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `__init__` | `(tracker, budget_config_path, no_color, on_budget_exceeded)` | - | Initialize CLI |
| `on_task_complete` | `(delegate, handback)` | None | Record task completion |
| `print_session_summary` | `()` | None | Print session summary |
| `should_block_new_tasks` | `()` | bool | Check if tasks should be blocked |
| `reset_session` | `()` | None | Clear all metrics |
| `get_session_stats` | `()` | TokenStats | Get aggregated statistics |
| `get_budget_status` | `()` | BudgetResult | Get current budget status |

---

## Support & Issues

For questions or issues:
1. Check the examples in `examples/orchestrator_cli_examples.py`
2. Review the test cases in `tests/test_orchestrator_cli.py`
3. Read the full documentation in `ORCHESTRATOR_CLI_IMPLEMENTATION.md`
