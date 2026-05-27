---
name: cost-aggregation
description: Consolidates provider-specific AI costs into unified metrics across Anthropic, OpenAI, Google Gemini, GitHub Copilot, and Ollama. Enables apples-to-apples cost comparison and savings analysis.
skill: cost-aggregation
version: 1.0.0
task_id: COST-002
depends_on: [COST-001]
author: senior-engineer
status: active
---

# Cost Aggregation Skill (COST-002)

Consolidates provider-specific AI costs into unified metrics across 5 providers:
Anthropic, OpenAI, Google Gemini, GitHub Copilot, and Ollama (local/zero-cost).

## Purpose

Enable apples-to-apples cost comparison across AI providers for any given task,
supporting model selection optimization (COST-003) and budget enforcement (COST-001).

## API

```python
from src.skills.cost_aggregation.scripts.cost_aggregator import CostAggregator

agg = CostAggregator()

# Compare cost across providers for a task
result = agg.aggregate_task_cost(
    task_type="code_review",
    input_tokens=5000,
    output_tokens=2000,
    model_variants={
        "anthropic": "claude-sonnet-4.6",
        "openai": "gpt-5.4",
        "google": "gemini-2.0",
        "copilot": "claude-sonnet-4.6",
        "ollama": "mistral:latest"
    }
)
# Returns per-provider cost, winner, and savings vs cheapest cloud

# Daily cost trend for a provider
trend = agg.cost_trend_for_provider("anthropic", "2026-05-01", "2026-05-28")
# Returns daily_spend list, total, avg_per_day

# Provider health check
health = agg.provider_health_check()
# Returns status per provider (healthy/degraded/unknown)

# Record actual usage for trend tracking
agg.record_usage("anthropic", "claude-sonnet-4.6", 5000, 2000)
```

## Providers

| Provider   | Auth          | Cost Model    | Zero-Cost |
|------------|---------------|---------------|-----------|
| anthropic  | ANTHROPIC_API_KEY | per-token  | No        |
| openai     | OPENAI_API_KEY    | per-token  | No        |
| google     | GOOGLE_API_KEY    | per-token  | No        |
| copilot    | GITHUB_TOKEN      | per-use    | No        |
| ollama     | (none)            | local      | **Yes**   |

## Configuration

Provider pricing is configured in `src/config/providers.yaml`.
Update that file when providers change their published rates.

## Performance

- `aggregate_task_cost()`: <10ms (pure computation, no network calls)
- `provider_health_check()`: <1ms when cached (5-minute TTL)
- Cost accuracy: ±2% vs published rates

## Files

```
src/skills/cost-aggregation/
├── SKILL.md                          # This file
├── scripts/
│   ├── __init__.py
│   ├── cost_aggregator.py            # Main CostAggregator class
│   └── providers/
│       ├── __init__.py
│       ├── base_provider.py          # Abstract base class
│       ├── anthropic_provider.py     # Anthropic claude-* models
│       ├── openai_provider.py        # OpenAI GPT-* models
│       ├── google_provider.py        # Google Gemini models
│       ├── copilot_provider.py       # GitHub Copilot (per-use)
│       └── ollama_provider.py        # Ollama local (zero-cost)
└── tests/
    ├── __init__.py
    └── test_cost_aggregator.py       # 80+ test cases
```

## Dependencies

- `COST-001` (cost_budgeter): Uses same rate structure pattern
- `pyyaml`: providers.yaml loading
- `pytest`: Test suite
