# Operations — Metrics, Analytics & Optimization

**This directory contains metrics schemas, analysis frameworks, and optimization guidance.**

## Files

| File | Purpose |
|------|---------|
| **COMPLETED_PLANS.md** | Completed initiatives & security audits, archived plans, lessons learned |
| **METRICS.md** | Per-task JSON schema and session JSONL format. Defines what gets recorded to `~/.claude/metrics/` |
| **TOKENADVISOR.md** | Daily metrics analysis framework. Cost trends, anomalies, optimization opportunities. |

## How Metrics Flow

```
Task execution
  ↓
HANDBACK reports: tokens, quality, duration
  ↓
Metrics recorded to: ~/.claude/metrics/YYYY-MM-DD/task_id.json
  ↓
TokenAdvisor (daily)
  ↓
Analyze: cost trends, anomalies, opportunities
  ↓
Model Engineer recommendations
  ↓
Orchestrator applies to next similar task
```

## Schema Overview

### Per-Task Metrics (task_id.json)
```json
{
  "task_id": "2026-04-24-fix-token-timeout",
  "role": "Engineer",
  "model": "haiku-4-5",
  "effort": "high",
  "tokens_in": 18500,
  "tokens_out": 2100,
  "quality_score": 92,
  "cost_usd": 0.018,
  "duration_minutes": 42,
  "rework_required": false,
  "qe_feedback": {...}
}
```

### Session Metrics (session.jsonl)
```
{per-task metrics, one line per task}
```

## When You Need This

- **Recording metrics?** Use METRICS.md schema
- **Analyzing cost trends?** Check TOKENADVISOR.md
- **Understanding Model Engineer recommendations?** See how metrics feed analysis
- **Cost optimization?** TOKENADVISOR.md identifies opportunities
- **Building dashboards?** METRICS.md defines the data structure

## Key Metrics Tracked

| Metric | Purpose |
|--------|---------|
| tokens_in, tokens_out | Measure API usage (cost drivers) |
| quality_score | Verify output quality (1-100) |
| cost_usd | Calculate task cost and trends |
| duration_minutes | Track agent speed |
| rework_required | Flag tasks needing fixes (quality issues) |
| qe_feedback | Quality Engineer assessment (model suitability) |

## Workflow

**During session:**
1. Create TODO.md using `orchestration/todo-management.md` skill
2. Update hourly with completed tasks, blockers, ETA
3. Record metrics using METRICS.md format

**After session:**
1. Archive old TODO.md: `mv TODO.md .TODO.archive.$(date +%Y-%m-%d).md`
2. Add session summary to COMPLETED_PLANS.md if major initiative
3. Log metrics to METRICS.md
4. Review token burn with TOKENADVISOR.md for next session optimization

## See Also

- `../MANIFEST.md` — Complete file listing of entire system (discovery tool)
- `../config/MODEL_ASSIGNMENTS_LOCKED.md` — Model costs ($/task)
- `../skills/orchestration/todo-management.md` — Create/manage TODO.md for planning
- `../skills/optimization/` — How metrics drive model recommendations
- `../guides/DEPLOYMENT_STATUS.md` — Phase tracking and capacity
