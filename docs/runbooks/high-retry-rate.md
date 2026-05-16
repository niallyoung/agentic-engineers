# Runbook: High Retry Rate

**Alert**: `OrchestratorHighRetryRate`
**Severity**: Warning
**Threshold**: Retry rate > 20% for 15 minutes

---

## Symptoms

- `orchestrator_tasks_retried_total` rate is elevated
- Tasks completing but requiring multiple attempts
- Higher token consumption than expected

## Immediate Actions

1. **Check retry patterns**
   ```bash
   grep "retry_count" artifacts/metrics/$(date +%Y-%m-%d)-*.yaml | grep -v ": 0"
   ```

2. **Identify which tasks are retrying**
   ```bash
   grep -l "retry_count: [1-9]" artifacts/metrics/$(date +%Y-%m-%d)-*.yaml
   ```

## Diagnosis

### If retries are on specific task types:
- Review task complexity vs. model capability
- Check if task requirements are ambiguous
- Consider adding more context to DELEGATE blocks

### If retries are widespread:
- Model API may be degraded (partial responses)
- Quality thresholds may be too strict
- Check if Quality Engineer scoring changed

## Resolution

1. **Ambiguous tasks**: Improve DELEGATE `scope` and `context` fields
2. **Model degradation**: Switch to backup model in manifest
3. **Threshold too strict**: Review Quality Engineer rubric with Lead Engineer

## Token Impact

Each retry doubles token cost. At 20% retry rate:
- 1.2x token multiplier
- At 50% retry rate: 1.5x multiplier

Monitor `orchestrator_tokens_total` alongside retry rate.
