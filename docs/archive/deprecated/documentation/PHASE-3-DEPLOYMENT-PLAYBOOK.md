# Phase 3 Production Deployment Playbook

**Version**: 1.0  
**Date**: 2026-05-17  
**Status**: Ready for Production  
**Owner**: Senior Engineering Team

---

## Overview

This playbook governs the production deployment of Phase 3 orchestration
improvements: dry-run mode, shadow mode, and gradual rollout. Follow each
stage in order. Do **not** skip stages or compress timelines without explicit
approval from a Lead or Principal Engineer.

---

## Pre-Deployment Checklist

Before starting any deployment stage, verify all items below:

### Code & Tests
- [ ] All 1,942+ tests passing (`python3 -m pytest tests/ --tb=short -q`)
- [ ] Zero regressions against pre-Phase-3 baseline
- [ ] Code reviewed and approved by Lead Engineer
- [ ] Feature flag system validated (`tests/test_feature_flags.py` — 24 tests)
- [ ] Monitoring system validated (`tests/test_deployment_monitoring.py` — 24 tests)

### Infrastructure
- [ ] `config/deployment.yaml` reviewed and committed
- [ ] Monitoring dashboards configured and accessible
- [ ] Alert rules configured (error rate, latency P99, quality score)
- [ ] Rollback procedures tested in staging
- [ ] Audit log directories exist (`artifacts/rollout/`, `artifacts/shadow-mode/`)

### Team Readiness
- [ ] On-call engineer identified and briefed
- [ ] Rollback runbook distributed to team
- [ ] Escalation path documented (Senior → Lead → Principal Engineer)
- [ ] Communication channel open (Slack/Teams #deployments)

---

## Stage 1: Dry-Run Mode (Day 1)

**Goal**: Validate the full orchestration pipeline without any production side effects.

### Activation

```bash
# Enable dry-run via environment variable (no code change required)
export DEPLOY_MODE=dry_run
export DEPLOY_DRY_RUN=true

# Or update config/deployment.yaml:
# deployment:
#   mode: dry_run
#   dry_run:
#     enabled: true
#     collect_metrics: true
```

### Validation Steps

1. **Run dry-run E2E tests**:
   ```bash
   python3 -m pytest tests/test_phase3_dry_run_e2e.py -v
   # Expected: 25 tests PASSED
   ```

2. **Execute sample orchestrator tasks** with dry-run enabled:
   ```bash
   python3 scripts/dry_run_examples.py
   ```

3. **Verify no side effects**:
   - No files written to `artifacts/queue/`
   - No git commits created
   - No API calls made
   - Audit trail written to `/tmp/dry-run-audit.json`

4. **Review audit trail**:
   ```bash
   cat /tmp/dry-run-audit.json | python3 -m json.tool | head -50
   ```

5. **Verify metrics collection**:
   - Operation counts recorded correctly
   - All operation types captured (FILE_WRITE, GIT_COMMIT, API_CALL, QUEUE_MOVE, etc.)

### Success Criteria
- [ ] All 25 dry-run E2E tests pass
- [ ] Zero actual files written
- [ ] Zero git commits created
- [ ] Audit trail complete and JSON-valid
- [ ] Metrics collected for all operation types

### Rollback
```bash
unset DEPLOY_MODE
unset DEPLOY_DRY_RUN
```

---

## Stage 2: Shadow Mode (Days 2–3)

**Goal**: Run new code path in parallel with production at 10% traffic, comparing results without impact.

### Activation

```bash
export DEPLOY_MODE=shadow
export DEPLOY_SHADOW=true
export SHADOW_MODE_ENABLED=true
export SHADOW_MODE_TRAFFIC_PCT=10
```

### Validation Steps

1. **Run shadow mode E2E tests**:
   ```bash
   python3 -m pytest tests/test_phase3_shadow_mode_e2e.py -v
   # Expected: 20 tests PASSED
   ```

2. **Deploy shadow mode** (10% traffic):
   - Confirm `ShadowModeContext` is instantiated with `traffic_percentage=10`
   - Verify production path always executes
   - Verify shadow path executes for ~10% of tasks

3. **Monitor for 24 hours**:
   - Check shadow vs. production result comparison logs
   - Review `artifacts/shadow-mode/` for comparison reports
   - Monitor error rates (shadow errors must NOT affect production)

4. **Day 3: Review metrics**:
   - Shadow correctness rate (target: ≥95% match with production)
   - Shadow latency overhead (target: ≤20% additional latency)
   - Zero production errors caused by shadow execution

5. **Run concurrent agent test**:
   ```bash
   python3 examples/shadow_mode_integration.py
   ```

### Key Metrics to Monitor
| Metric | Warning | Critical |
|--------|---------|----------|
| Shadow error rate | >5% | >15% |
| Production impact | Any | Any |
| Result mismatch rate | >10% | >25% |
| Shadow latency overhead | >50% | >100% |

### Success Criteria
- [ ] All 20 shadow mode E2E tests pass
- [ ] Production path unaffected by shadow execution
- [ ] Shadow correctness ≥95%
- [ ] Zero production errors from shadow mode
- [ ] 50+ concurrent tasks handled without errors

### Rollback
```bash
unset DEPLOY_MODE
unset DEPLOY_SHADOW
unset SHADOW_MODE_ENABLED
```

---

## Stage 3: Gradual Rollout (Days 4–8)

**Goal**: Incrementally route production traffic to the new code path across 5 stages.

### Activation

```bash
export DEPLOY_MODE=gradual_rollout
export DEPLOY_ROLLOUT=true
export ROLLOUT_ENABLED=true
```

### Stage 3a: 10% Traffic (Day 4)

```bash
export ROLLOUT_STAGE=10
# Or use RolloutManager:
# mgr = RolloutManager(initial_stage=RolloutStage.STAGE_10)
```

**Monitoring** (minimum 4 hours before advancing):
- Error rate < 5%
- P99 latency < 2000ms
- Quality score > 0.80
- No critical alerts

**Advance**:
```python
mgr.advance()  # → STAGE_25
```

### Stage 3b: 25% Traffic (Day 5)

```bash
export ROLLOUT_STAGE=25
```

**Monitoring** (minimum 8 hours before advancing):
- Same thresholds as Stage 3a
- Compare metrics against Stage 3a baseline

### Stage 3c: 50% Traffic (Day 6, morning)

```bash
export ROLLOUT_STAGE=50
```

**Monitoring** (minimum 4 hours before advancing):
- Error rate < 5%
- P99 latency < 2000ms
- Quality score > 0.80

### Stage 3d: 75% Traffic (Day 6, afternoon)

```bash
export ROLLOUT_STAGE=75
```

**Monitoring** (minimum 4 hours before advancing):
- Same thresholds
- Verify no cost anomalies

### Stage 3e: 100% Traffic (Day 7)

```bash
export ROLLOUT_STAGE=100
```

**Final validation**:
- Run full test suite: `python3 -m pytest tests/ --tb=short -q`
- Monitor for 24 hours post-100% rollout
- Confirm all metrics stable

### Rollout Validation Tests

```bash
python3 -m pytest tests/test_phase3_gradual_rollout_e2e.py -v
# Expected: 31 tests PASSED
```

### Rollback at Any Stage

```python
# Immediate rollback (one stage):
mgr.rollback()

# Full rollback to disabled:
while mgr.stage != RolloutStage.DISABLED:
    mgr.rollback()

# Or via environment:
export ROLLOUT_STAGE=0  # DISABLED
```

### Stage Health Thresholds

| Metric | Advance Threshold | Auto-Rollback Threshold |
|--------|------------------|------------------------|
| Error rate | < 5% | > 10% |
| P99 latency | < 2000ms | > 5000ms |
| Quality score | > 0.80 | < 0.72 |
| Min samples | ≥ 20 | — |

---

## Monitoring & Alerting

### DeploymentMonitor Configuration

```python
from src.orchestration.deployment.monitoring import DeploymentMonitor

monitor = DeploymentMonitor(
    error_rate_threshold=0.05,       # 5% error rate
    latency_p99_threshold_ms=2000.0, # 2 second P99
    quality_min=0.80,                # 80% quality score
    window_seconds=300.0,            # 5-minute rolling window
    auto_rollback_callback=lambda: mgr.rollback(),
)
```

### Alert Severity Levels

| Severity | Condition | Action |
|----------|-----------|--------|
| INFO | Metrics within bounds | Log only |
| WARNING | Metric exceeds threshold | Page on-call |
| CRITICAL | Metric exceeds 2× threshold | Auto-rollback + page |

### Checking Alerts

```python
alerts = monitor.check_alerts(stage=current_stage)
for alert in alerts:
    print(f"[{alert.severity}] {alert.message}")
```

---

## Feature Flag Management

### Quick Reference

| Flag | Environment Variable | Values |
|------|---------------------|--------|
| Deployment mode | `DEPLOY_MODE` | `dry_run`, `shadow`, `gradual_rollout`, `production` |
| Dry-run enabled | `DEPLOY_DRY_RUN` | `true`/`false` |
| Shadow enabled | `DEPLOY_SHADOW` | `true`/`false` |
| Shadow traffic % | `DEPLOY_SHADOW_PCT` | `1`–`100` |
| Rollout enabled | `DEPLOY_ROLLOUT` | `true`/`false` |
| Rollout stage | `DEPLOY_ROLLOUT_STAGE` | `10`, `25`, `50`, `75`, `100` |

### List Current Flags

```bash
python3 -m src.orchestration.deployment.feature_flags list
```

### Validate Config

```python
from src.orchestration.deployment.config_loader import load_deployment_config
cfg = load_deployment_config()
assert cfg.is_valid(), "Deployment config is invalid!"
```

---

## Rollback Procedures

### Immediate Rollback (< 5 minutes)

1. Set environment variable:
   ```bash
   export DEPLOY_MODE=production
   export ROLLOUT_STAGE=0
   ```

2. Verify rollback:
   ```python
   from src.orchestration.deployment.feature_flags import get_feature_flags
   flags = get_feature_flags()
   assert flags.is_production
   ```

3. Notify team in #deployments channel.

### Full Rollback (code revert)

```bash
git log --oneline -10  # identify pre-Phase-3 commit
git revert HEAD~N      # revert N commits
python3 -m pytest tests/ --tb=short -q  # verify tests pass
```

### Auto-Rollback

The `DeploymentMonitor` will automatically call the rollback callback when
a CRITICAL alert fires. Ensure the callback is wired to `mgr.rollback()`:

```python
monitor = DeploymentMonitor(
    auto_rollback_callback=lambda: mgr.rollback(),
)
```

---

## Post-Deployment (Days 8–14)

- [ ] Monitor error rates, latency, quality for 7 days
- [ ] Review audit trails from gradual rollout (`artifacts/rollout/`)
- [ ] Collect user/operator feedback
- [ ] Document lessons learned
- [ ] Archive shadow mode comparison reports
- [ ] Update this playbook with any corrections

---

## Phase C Recommendations

Based on Phase B implementation, the following improvements are recommended for Phase C:

1. **Automated stage advancement**: Implement `evaluate_and_advance()` loop that
   auto-advances based on health checks after minimum dwell time.

2. **Metrics dashboard**: Wire `DeploymentMonitor.snapshot()` to a Prometheus
   exporter for real-time Grafana dashboards.

3. **Canary analysis**: Integrate statistical significance testing (Welch's t-test)
   before advancing stages — see `skills/ab-testing/`.

4. **Deployment pipeline integration**: Add pre-merge gate that runs
   `test_phase3_dry_run_e2e.py` + `test_phase3_shadow_mode_e2e.py` in CI.

5. **Feature flag persistence**: Store flag state in DynamoDB/Redis for
   multi-instance deployments (current implementation is in-process only).

6. **Alerting integrations**: Connect `DeploymentMonitor` alerts to PagerDuty,
   Slack, and CloudWatch for production-grade observability.

---

## Contacts

| Role | Responsibility |
|------|---------------|
| Senior Engineer | Implementation, day-to-day deployment |
| Lead Engineer | Approval to advance stages, escalation |
| Principal Engineer | Architecture decisions, emergency rollback authority |
| On-call Engineer | 24/7 monitoring, alert response |
