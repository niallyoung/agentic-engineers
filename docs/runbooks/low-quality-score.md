# Runbook: Low Quality Score

**Alert**: `OrchestratorLowQualityScore`
**Severity**: Warning
**Threshold**: Average quality score < 70 for 10 minutes

---

## Symptoms

- `orchestrator_quality_score` histogram showing low values
- Quality Engineer HANDBACKs with low scores
- Increased retry rates

## Immediate Actions

1. **Check recent quality scores**
   ```bash
   ls artifacts/metrics/ | tail -20
   grep "quality_score_validator" artifacts/metrics/*.yaml | sort -t: -k3 -n | head -20
   ```

2. **Identify which roles/models are underperforming**
   ```bash
   grep -h "role\|model\|quality_score_validator" artifacts/metrics/$(date +%Y-%m-%d)-*.yaml
   ```

## Diagnosis

### If specific role is low:
- Review recent DELEGATEs for that role
- Check if task complexity exceeds model capability
- Consider escalating to higher-capability model

### If all roles are low:
- Check if task requirements changed (new schema, new expectations)
- Review Quality Engineer scoring criteria
- Check if model API degraded

### If new model was recently deployed:
- Compare quality scores before/after model change
- Consider rolling back to previous model
- File A/B test via `ab-testing` skill

## Resolution

1. **Model mismatch**: Update `src/orchestration/agents-manifest.yaml` to use higher-capability model
2. **Task too complex**: Break task into smaller sub-tasks
3. **Scoring criteria changed**: Update Quality Engineer evaluation rubric

## SLO Impact

Quality score < 85 average → SLO `quality_score_avg` at risk
Quality score < 70 average → SLO `quality_score_avg` breached
