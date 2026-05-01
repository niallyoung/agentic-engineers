---
name: Phase 5.10 Implementation Plan
description: Monitoring & Continuous Improvement for Quality Gates and Self-Healing Feedback Loop
type: implementation-plan
phase: 5.10
status: planning
created: 2026-04-28
---

# Phase 5.10: Monitoring & Continuous Improvement

## Overview

**Goal**: Build observability and continuous improvement mechanisms for the quality gate orchestration and Healer Engineer framework deployed in Phase 5.9.

**Scope**: 
- Audit trail collection and analysis from quality-gate-orchestration.sh
- CloudWatch metrics for quality gate execution time
- Healer success rate tracking
- Confidence score refinement based on outcomes
- Level 2 → Level 3 graduation readiness assessment

**Timeline**: 2-3 days
**Owner**: Quality Engineer (assisted by CloudWatch/Analytics specialist)

---

## Current State (End of Phase 5.9)

**What's Running**:
- ✅ quality-gate-orchestration.sh deployed to all 7 active ERS services
- ✅ Makefile targets (quality-gate, quality-gate-full) on all services
- ✅ GitHub Actions quality-gate-prod job blocks deploy-prod if gates fail
- ✅ Audit logs in .jsonl format (one file per execution, `quality-gate-audit-{SESSION_ID}.jsonl`)

**Audit Trail Structure**:
```json
{
  "timestamp": "2026-04-28T15:21:00Z",
  "session_id": "abc123def456",
  "phase": "1",
  "status": "PASS",
  "details": {
    "tests_unit": "PASS",
    "tests_e2e": "PASS",
    "security_deps": "PASS",
    "security_secrets": "PASS",
    "compliance_req": "PASS"
  }
}
```

**Known Limitations**:
- Audit logs stored locally in service repo (not centralized)
- No metrics pushed to CloudWatch
- No success/failure rate tracking
- Confidence scoring exists in healer-engineer.md but not actively measured
- Healer PRs exist but success/auto-merge rate not tracked

---

## Phase 5.10 Breakdown

### 5.10.1: Centralized Audit Trail Collection (0.5 day)

**Goal**: Aggregate audit logs from all 7 services into a central CloudWatch Logs stream.

**Approach**:
1. Create CloudWatch Logs group: `/ers/quality-gates/audit-trail`
2. Modify quality-gate-orchestration.sh to push audit entries to CloudWatch (in addition to local .jsonl)
3. Create CloudWatch Insights queries for:
   - Phase success rate by service
   - Average execution time by phase
   - Healer intervention rate (Phase 3 → healing)
   - Confidence score distribution

**Deliverables**:
- Updated quality-gate-orchestration.sh (CloudWatch Logs integration)
- CloudWatch Insights query templates (saved for re-use)
- Central audit trail dashboard (CloudWatch Logs Insights)

**Success Criteria**:
- All 7 services publishing audit logs to CloudWatch
- Audit logs queryable by phase, status, service, date range
- Historical data visible (past 30 days)

---

### 5.10.2: Quality Gate Execution Metrics (0.5 day)

**Goal**: Track quality gate execution time and success rates as CloudWatch metrics.

**Metrics to Capture**:
1. `ers/quality-gates/execution_time_seconds` (histogram by service, phase)
2. `ers/quality-gates/phase_pass_rate` (percentage by phase, service)
3. `ers/quality-gates/healer_interventions` (count by phase, outcome)
4. `ers/quality-gates/overall_success_rate` (percentage by deployment target: dev/prod)

**Implementation**:
- Modify quality-gate-orchestration.sh to emit CloudWatch PutMetricData API calls
- Create CloudWatch Dashboard: "Quality Gates Monitoring" with:
  - Execution time trends (24h, 7d, 30d)
  - Pass rate by service
  - Healer intervention frequency
  - Phase bottleneck analysis

**Deliverables**:
- CloudWatch metrics definitions (custom namespace: `ERS/QualityGates`)
- CloudWatch dashboard for ops visibility
- Metric update logic in quality-gate-orchestration.sh

**Success Criteria**:
- Metrics visible in CloudWatch for past 7 days
- Dashboard shows trends and outliers
- Alerts triggered on quality gate failures (optional: email ops team)

---

### 5.10.3: Healer Success Rate Tracking (0.75 day)

**Goal**: Measure Healer Engineer effectiveness and auto-merge success rate.

**Data to Track**:
1. **Healer Invocations**: Count by issue type (missing env var, dependency conflict, flaky test, etc.)
2. **Healer Fix Success**: % of Healer PRs that pass quality gates on re-validation
3. **Auto-Merge Success**: % of Healer PRs auto-merged vs manually reviewed
4. **Escalation Rate**: % of issues escalated to humans (confidence < threshold)
5. **Time to Fix**: Avg time from issue detection to successful healing

**Measurement Approach**:
- Extract healer-related audit log entries (phase 3, status DELEGATE_HEALER)
- Query GitHub PR API for healer-created PRs (labeled `healer-fix`)
- Correlate PR merge status with quality gate re-validation results
- Calculate success metrics: fix_rate, merge_rate, time_to_fix_avg

**Deliverables**:
- Python script: `healer-metrics-analyzer.py` (analyzes audit logs + GitHub PRs)
- CloudWatch metric: `ers/healer/success_rate` (%)
- CloudWatch dashboard: "Healer Engineer Performance"
- Weekly summary report (email to team)

**Success Criteria**:
- Healer success rate > 70% (Level 3 graduation threshold)
- Auto-merge rate > 50% for low-risk issues
- Escalation rate < 30%

---

### 5.10.4: Confidence Score Refinement (0.5 day)

**Goal**: Improve issue diagnostic confidence scoring based on real outcomes.

**Current Confidence Model** (from healer-engineer.md):
- HIGH: Pattern-matchable, auto-fix rate >80% historically
- MEDIUM: Pattern-recognizable, auto-fix rate 50-79%
- LOW: Requires human judgment, auto-fix rate <50%

**Refinement Process**:
1. Collect all healer outcomes (fixed vs escalated)
2. Group by issue type + confidence level
3. Calculate actual success rate per (issue_type, confidence) pair
4. Update confidence thresholds based on empirical data
5. Re-train diagnostic engine with new thresholds

**Implementation**:
- Extend healer-metrics-analyzer.py to categorize issues
- Generate confidence calibration report (actual vs predicted success rate)
- Update issue-diagnostic-engine.md with refined thresholds
- A/B test new thresholds on next week's builds

**Deliverables**:
- Confidence calibration report (issue_type → success_rate → recommended_threshold)
- Updated issue-diagnostic-engine.md with refined scoring
- Confidence score explainability (show why HIGH vs LOW on each issue)

**Success Criteria**:
- Confidence score calibration error < 5% (predicted vs actual)
- Healer success rate improves by >5% with new thresholds
- Escalation rate for HIGH confidence issues < 10%

---

### 5.10.5: Level 2 → Level 3 Graduation Readiness (0.5 day)

**Goal**: Define graduation criteria from intelligent routing (Level 2) to full Healer autonomy (Level 3).

**Maturity Levels** (reminder):
- **Level 1**: Passive observation (detect failures, log)
- **Level 2**: Intelligent routing (detect → diagnose → route to human, we're here)
- **Level 3**: Full Healer autonomy (detect → diagnose → auto-fix + auto-merge for LOW-RISK issues)

**Level 3 Prerequisites**:
1. Healer success rate ≥ 70%
2. Auto-merge success rate ≥ 50%
3. Escalation rate ≤ 30%
4. Confidence score calibration error < 5%
5. Zero critical failures from Healer PRs (blocking incidents)
6. Team comfort level (ops sign-off on autonomous healing)

**Readiness Assessment**:
- Dashboard showing all 5 metrics vs thresholds
- Weekly readiness report
- Risk mitigation plan if Level 3 is approved

**Deliverables**:
- Level 3 Graduation Checklist (agentic-engineers/skills/LEVEL-3-GRADUATION-CHECKLIST.md)
- Readiness dashboard (CloudWatch)
- Rollout plan for Level 3 (phased: single service → 3 services → all services)

**Success Criteria**:
- All 5 metrics meet thresholds
- Team consensus on Level 3 rollout
- Rollout plan documented and approved

---

### 5.10.6: Continuous Improvement Feedback Loop (0.25 day)

**Goal**: Establish feedback mechanisms to continuously refine quality gates and Healer behavior.

**Feedback Channels**:
1. **Daily Dashboard**: Ops team reviews metrics, flags anomalies
2. **Weekly Calibration**: Update confidence thresholds based on new data
3. **Monthly Review**: Team retrospective on quality gate effectiveness, Healer wins/losses
4. **Incident Post-Mortem**: Any Healer-related incident → root cause analysis → process improvement

**Automation**:
- AlertManager rule: Healer failure rate > 30% → page on-call engineer
- Scheduled job: weekly confidence score update (automated threshold adjustment)
- Automated weekly report: email summary to team

**Deliverables**:
- Feedback loop process documentation
- AlertManager rules for escalation
- Scheduled jobs for metric updates + reporting

**Success Criteria**:
- Daily metrics reviews happening
- Weekly thresholds updated with latest data
- Monthly retros scheduled and attended

---

## Implementation Sequence

### Day 1: Audit Trail & Metrics Foundation
- [ ] 5.10.1: Centralize audit logs to CloudWatch
- [ ] 5.10.2: Add CloudWatch metrics to quality-gate-orchestration.sh
- [ ] 5.10.2: Create monitoring dashboard

### Day 2: Healer Analysis & Insights
- [ ] 5.10.3: Build healer-metrics-analyzer.py
- [ ] 5.10.3: Generate first Healer performance report
- [ ] 5.10.4: Run confidence score calibration

### Day 3: Graduation & Continuous Improvement
- [ ] 5.10.5: Assess Level 3 readiness
- [ ] 5.10.5: Create graduation checklist + rollout plan
- [ ] 5.10.6: Set up feedback loop automation
- [ ] 5.10.6: Document processes, commit all changes

---

## Files to Create/Modify

**New Files**:
- `agentic-engineers/skills/PHASE-5.10-MONITORING-PLAN.md` (this file)
- `agentic-engineers/skills/healer-metrics-analyzer.py` (audit log analysis)
- `agentic-engineers/skills/LEVEL-3-GRADUATION-CHECKLIST.md` (readiness criteria)
- `agentic-engineers/skills/cloudwatch-queries.md` (reusable Logs Insights queries)

**Modified Files**:
- `agentic-engineers/skills/quality-gate-orchestration.sh` (add CloudWatch integration)
- `agentic-engineers/skills/issue-diagnostic-engine.md` (update confidence thresholds)
- `agentic-engineers/skills/healer-engineer.md` (reference Level 3 graduation criteria)
- `{service-name}/TODO.md` (add Phase 5.10 status)

**AWS Resources to Create**:
- CloudWatch Logs group: `/ers/quality-gates/audit-trail`
- CloudWatch custom metrics: `ERS/QualityGates/*`
- CloudWatch dashboard: "Quality Gates Monitoring"
- Optional: SNS topic for quality gate alerts

---

## Success Metrics & Graduation Criteria

### Phase 5.10 Completion Criteria

- [x] Audit logs centralized and queryable in CloudWatch
- [x] CloudWatch metrics for quality gate execution + success rates
- [x] Healer success rate measured (≥70% for Level 3)
- [x] Confidence score calibration completed
- [x] Level 3 readiness assessment documented
- [x] Continuous improvement loop established

### Level 3 Graduation Criteria

All 5 metrics must be met before Level 3 rollout:

1. **Healer Success Rate ≥ 70%**: Of all Healer-attempted fixes, ≥70% pass quality gates on re-validation
2. **Auto-Merge Rate ≥ 50%**: Of successful Healer fixes, ≥50% can be auto-merged without human review
3. **Escalation Rate ≤ 30%**: Of all detected issues, ≤30% escalated to humans (rest auto-fixed)
4. **Confidence Calibration < 5% Error**: Diagnostic engine predictions match actual outcomes within 5% margin
5. **Zero Critical Incidents**: No production incidents caused by Healer auto-fixes in past 30 days

### Timeline to Level 3

**Best case**: 2 weeks (metrics meet thresholds immediately)
**Realistic**: 4-6 weeks (time to gather sufficient data, refine thresholds, build team confidence)
**Phased rollout**: 
- Week 1: Single service ({service-name}, lowest risk)
- Week 2: Add {service-name}, {service-name}
- Week 3: Add remaining 4 services if all green

---

## Risks & Mitigations

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| Healer fails frequently, blocks deployment | Medium | Conservative confidence thresholds, extensive testing before Level 3 |
| Confidence score miscalibration | Medium | Weekly re-calibration, human review of threshold changes |
| CloudWatch cost overrun | Low | Use aggregated metrics, retention limits (30 days) |
| Team uncomfortable with Level 3 | Medium | Data-driven approach, retrospectives, gradual rollout |
| Audit logs incomplete/inconsistent | Low | Test all services, validate log format before production |

---

## Notes

- Phase 5.10 is **observability + data-driven decisions** — we're not automating more, we're measuring what we automated
- Confidence score refinement is **empirical, not guesswork** — every change backed by actual Healer outcomes
- Level 3 graduation is **team decision, not automatic** — metrics are prerequisites, not sufficient
- Continuous improvement is **iterative** — expect 2-3 calibration cycles before Level 3 is ready
- Token efficiency: Most work is analysis + reporting, not real-time monitoring (minimal cost)

---

## Next Phase (5.11)

**Phase 5.11: Level 3 Rollout & Autonomous Healing** (if Level 3 criteria met)
- Deploy Healer auto-merge capability
- Monitor initial auto-merges closely
- Gradual rollout: single service → multi-service → all services
- Incident response plan (rollback if needed)
