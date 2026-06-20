---
name: model-selection
description: >
  Model Selection Optimization (COST-003) — recommends optimal AI models for tasks
  given budget constraints, quality targets, and latency requirements. Computes
  the Pareto cost-quality frontier and supports mixed-model routing simulation.
version: "1.0.0"
dependencies:
  - skill: cost-budgeting
    optional: false
  - skill: cost-aggregation
    optional: true
entry_points:
  - scripts/model_selector.py
tests:
  - tests/test_model_selector.py
coverage_minimum: 85
---

# COST-003: Model Selection Optimization

Recommends the optimal AI model for a task given cost, quality, and latency constraints.

## API

### `ModelSelector`

```python
from scripts.model_selector import ModelSelector

selector = ModelSelector()
```

#### `recommend_model(task_type, input_tokens, output_tokens, constraints=None)`

Recommend the single best model for a task.

**Parameters:**
- `task_type` (str): Task category (`code_review`, `documentation`, `security_audit`, `general`, etc.)
- `input_tokens` (int): Expected input token count
- `output_tokens` (int): Expected output token count
- `constraints` (dict, optional):
  - `max_cost` (float): Maximum cost per task in USD
  - `quality_target` (float): Minimum quality score [0.0, 1.0]
  - `max_latency_sec` (float): Maximum acceptable latency in seconds
  - `provider_preference` (list[str]): Ordered list of preferred providers

**Returns:** dict with keys `model`, `provider`, `estimated_cost`, `estimated_quality`, `estimated_latency_sec`, `reasoning`, `_selection_time_ms`

#### `recommend_batch(tasks)`

Recommend models for multiple tasks, tracking cumulative cost.

#### `cost_quality_frontier(task_type, input_tokens, output_tokens, providers=None)`

Compute the Pareto-optimal cost/quality frontier.

#### `simulate_model_mix(mix, daily_tasks, avg_tokens, task_type="general")`

Predict daily cost and quality for a hypothetical routing mix.

## Integration

- **COST-001** (CostBudgeter): uses same rate structure from `src/config/models.yaml`
- **COST-002** (CostAggregator): optional, pass as `cost_aggregator=` parameter for richer cost estimates

## Quality Tiers

| Tier | Score Range | Example Models |
|------|-------------|----------------|
| mini | 0.52–0.67 | gpt-4o-mini |
| haiku | 0.55–0.70 | claude-haiku-4.5, gemini-flash |
| sonnet | 0.82–0.90 | claude-sonnet-4.5/4.6, gpt-4o |
| opus | 0.95–0.98 | claude-opus-4.8 |

## Self-Improvement

This skill participates in the framework's continuous improvement cycle
(see [skill-improvement-feedback](../skill-improvement-feedback/SKILL.md)).

When you use **model-selection** during a task, include a skill_feedback entry
in your HANDBACK to help improve it over time:

```yaml
skill_feedback:
  - skill_name: model-selection
    effectiveness_score: 0.85        # required: 0.0–1.0
    clarity_score: 0.90              # optional
    coverage_gaps:
      - "Specific scenario the skill did not address"
    improvement_suggestions:
      - "Concrete change that would have helped"
    usage_context: "One sentence on how you used this skill"
```

Positive feedback is as valuable as critical feedback. Three or more
feedback items for this skill automatically trigger an improvement task.
