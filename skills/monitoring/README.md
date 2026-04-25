# Monitoring — Pipeline & Metrics Monitoring

**Skills for monitoring CI/CD pipelines, collecting metrics, and analyzing performance.**

## Skills in This Directory

| Skill | Used By | Purpose |
|-------|---------|---------|
| **cicd-watch.md** | Orchestrator, Quality Engineer | Monitor GitHub Actions pipeline status |
| **metrics-collection.md** | Orchestrator | Record task metrics to ~/.claude/metrics/ |
| **token-advisor.md** | Orchestrator | Manual daily metrics analysis framework |
| **tokenadvisor-scheduler.md** | Orchestrator | Automated metrics analysis (scheduled daily) |
| **quality-feedback-analysis.md** | Model Engineer | Extract patterns from quality feedback |

## When to Use

- **Watching builds after push** — Both Orchestrator and QE use cicd-watch.md
- **Recording task results** — Orchestrator uses metrics-collection.md
- **Analyzing cost trends** — Orchestrator uses token-advisor.md or tokenadvisor-scheduler.md
- **Improving model selection** — Model Engineer uses quality-feedback-analysis.md

## Metrics Flow

```
Task execution
  ↓
Engineer reports metrics (HANDBACK)
  ↓
Orchestrator records metrics (metrics-collection.md)
  ↓
Daily analysis (tokenadvisor-scheduler.md)
  ↓
Model Engineer feedback analysis (quality-feedback-analysis.md)
  ↓
Recommendations for next task
```

## See Also

- `../orchestration/` — How metrics feed into task routing
- `../optimization/` — Model recommendations based on metrics
- `../roles/` — Role responsibilities for monitoring
