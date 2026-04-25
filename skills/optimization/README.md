# Optimization — Model Selection & Cost Analysis

**Skills for optimizing model selection, evaluating cost-quality tradeoffs, and A/B testing.**

## Skills in This Directory

| Skill | Used By | Purpose |
|-------|---------|---------|
| **model-engineer.md** | Orchestrator | Core Model Engineer workflow |
| **model-engineer-automation.md** | Orchestrator | Automated model recommendation generation |
| **model-analysis.md** | Model Engineer | Analyze model performance across tasks |
| **model-recommendation.md** | Model Engineer | Generate ranked model recommendations |
| **cost-quality-tradeoff.md** | Model Engineer | Evaluate upgrade/downgrade decisions |
| **model-comparison.md** | Model Engineer | Compare models across historical data |
| **ab-testing-framework.md** | Orchestrator | A/B test design and methodology |
| **ab-test-automation.md** | Orchestrator | Automated A/B test execution |

## Roles

**Model Engineer** (Sonnet/Opus): Analysis, recommendations, tradeoff evaluation  
**Orchestrator** (Haiku): Routing decisions, automation, A/B test execution

## When to Use

- **Daily cost analysis** — Orchestrator runs tokenadvisor-scheduler, which feeds Model Engineer
- **Evaluating model changes** — Model Engineer uses cost-quality-tradeoff.md
- **A/B testing models** — Orchestrator uses ab-testing-framework.md and ab-test-automation.md
- **Checking model quality trends** — Model Engineer uses model-analysis.md and model-comparison.md

## Optimization Loop

```
Task execution
  ↓
Metrics recorded + QE feedback
  ↓
Model Engineer analysis (model-analysis, model-recommendation)
  ↓
Recommendations to Orchestrator
  ↓
Next similar task uses recommended model
  ↓
Cost decreases, quality maintained/improved
```

## Cost Optimization Strategy

- Cost-first: Haiku 4.5 → Sonnet 4.5 → 4.6 → Opus 4.6 → 4.7
- Quality gate: min_quality = best_quality - 5 points
- Progression: Test all effort/thinking combos per model

## See Also

- `../monitoring/` — Metrics that feed optimization
- `../shared/` — Quality assessment feedback
- config/MODEL_ASSIGNMENTS_LOCKED.md — Locked progression and strategy
