---
name: cost-budgeting
description: >
  Cost Budget Enforcement (COST-001) — enforces per-session, per-hour, and per-day
  AI spend limits across all agents and models. Blocks task execution when budgets
  are exceeded and emits structured alerts for operator action. Integrates with
  model-selection (COST-003) to pre-screen model choices against budget headroom.
license: Proprietary
compatibility: agentic-engineers framework v5.10+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: cost
  role: orchestrator
  model: claude-haiku-4-5
  effort: low
  runtime: python3
  spec: COST-001
entry_points:
  - scripts/cost_budgeter.py
tests:
  - tests/test_cost_budgeter.py
coverage_minimum: 85
---

# COST-001: Cost Budget Enforcement

Enforces per-session, per-hour, and per-day spend limits on AI usage across all agents.

## API

### `CostBudgeter`

```python
from src.skills.cost_budgeting.scripts.cost_budgeter import CostBudgeter

budgeter = CostBudgeter(session_limit=1.0, hourly_limit=5.0, daily_limit=20.0)
result = budgeter.check_budget(estimated_cost=0.05)
# result.allowed: bool
# result.remaining: float
# result.alert: str | None
```

## Usage

Use this skill to gate task execution against configured spend limits. Invoked
automatically by the Orchestrator before delegating to expensive models.

### Budget tiers

| Tier | Default | Configurable |
|---|---|---|
| Session | $1.00 | Yes |
| Hourly | $5.00 | Yes |
| Daily | $20.00 | Yes |

## Dependencies

- No runtime dependencies on other skills.
- `model-selection` (COST-003) depends on this skill to check headroom before recommending models.

## Spec compliance

Implements COST-001 from `src/specs/SPEC.md`.
