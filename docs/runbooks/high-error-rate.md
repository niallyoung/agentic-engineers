# Runbook: High Error Rate

**Alert**: `OrchestratorHighErrorRate`
**Severity**: Critical
**Threshold**: Error rate > 5% for 5 minutes

---

## Symptoms

- `orchestrator_errors_total` rate is elevated
- Tasks failing without completing
- Quality Engineer reporting validation failures

## Immediate Actions (< 5 minutes)

1. **Check queue state**
   ```bash
   ls artifacts/queue/processing/
   ls artifacts/queue/incoming/
   ```

2. **Check recent error logs**
   ```bash
   tail -100 logs/orchestrator.log | grep '"level":"ERROR"'
   ```

3. **Identify error pattern** — look for:
   - `validation_error`: DELEGATE/HANDBACK schema issues
   - `routing_error`: Agent unavailable or misconfigured
   - `timeout_error`: Agent taking too long

## Diagnosis

### If validation errors dominate:
- Check recent DELEGATE files in `artifacts/delegates/`
- Verify schema against `src/orchestration/delegate-schema.yaml`
- Look for missing required fields (`task_id`, `role`, `model`)

### If routing errors dominate:
- Check `src/orchestration/agents-manifest.yaml` for agent config
- Verify agent model names are valid
- Check if model API is accessible

### If timeouts dominate:
- Check if tasks are stuck in `artifacts/queue/processing/`
- Look for tasks older than 2 hours
- Consider increasing timeout thresholds

## Resolution

1. Fix root cause (schema, config, or infrastructure)
2. Requeue failed tasks if appropriate:
   ```bash
   mv artifacts/queue/processing/failed-task.yaml artifacts/queue/incoming/
   ```
3. Monitor error rate drops below 1%
4. Update post-mortem in `docs/incidents/`

## Escalation

If not resolved in 30 minutes → escalate to Principal Engineer
