# Runbook: SLO Breach

**Alert**: `SLOBreach`
**Severity**: Page (immediate response required)
**Threshold**: Any SLO enters BREACHED state

---

## SLOs Defined

| SLO | Target | Window |
|-----|--------|--------|
| `task_success_rate` | >= 95% | 60 min |
| `quality_score_avg` | >= 85% | 60 min |
| `error_rate` | <= 1% | 60 min |
| `routing_success_rate` | >= 99% | 30 min |
| `validation_pass_rate` | >= 95% | 60 min |

## Immediate Actions (< 2 minutes)

1. **Identify which SLO is breached** — check monitoring dashboard
2. **Assess blast radius** — how many tasks affected?
3. **Determine if breach is ongoing or historical**

## Per-SLO Response

### `task_success_rate` breached:
→ See [high-error-rate.md](high-error-rate.md)

### `quality_score_avg` breached:
→ See [low-quality-score.md](low-quality-score.md)

### `error_rate` breached:
→ See [high-error-rate.md](high-error-rate.md)

### `routing_success_rate` breached:
- Check `src/orchestration/routing_agent.py` logs
- Verify agent manifest is valid
- Check model API availability

### `validation_pass_rate` breached:
- Check recent DELEGATE schema changes
- Verify `delegate-schema.yaml` and `handback-schema.yaml` are current
- Review recent protocol changes

## Post-Breach Actions

1. Document incident in `docs/incidents/YYYY-MM-DD-slo-breach.md`
2. Root cause analysis within 24 hours
3. Update alerting thresholds if needed
4. Review SLO targets if consistently at risk

## Escalation

- 0-15 min: On-call engineer
- 15-30 min: Lead Engineer
- 30+ min: Principal Engineer
