---
name: Level 3 Graduation Checklist
description: Readiness criteria and validation for graduating Healer Engineer from Level 2 (intelligent routing) to Level 3 (autonomous healing with auto-merge)
type: checklist
status: template
created: 2026-04-28
---

# Level 3 Graduation Checklist

## Overview

This checklist validates readiness to move Healer Engineer from **Level 2** (intelligent routing to humans) to **Level 3** (autonomous fixing and auto-merge for low-risk issues).

All 5 success criteria must be **PASS** before Level 3 rollout is approved.

---

## Success Criteria

### Criterion 1: Healer Success Rate ≥ 70%

**Definition**: Of all issues Healer attempts to fix, ≥70% pass quality gates on re-validation.

**Measurement**:
```bash
# Run metrics analyzer
./healer-metrics-analyzer.py --days 30 --output healer-report.json

# Check in output:
healer_report.json.healer_success.success_rate >= 70
```

**Validation**:
- [ ] Healer success rate measured for past 30 days
- [ ] Success rate ≥ 70%
- [ ] At least 20 Healer invocations in measurement period
- [ ] No downward trend in recent data (last 7 days)

**Why This Matters**: If Healer auto-fixes fail more often than not, it blocks deployment. 70% is the minimum safe threshold.

---

### Criterion 2: Auto-Merge Success Rate ≥ 50%

**Definition**: Of successful Healer fixes (that pass quality gates), ≥50% can be auto-merged without human review.

**Measurement**:
```bash
# Query GitHub API for healer-created PRs
gh pr list --author "healer-engineer[bot]" --state merged --label "healer-fix" --json number,mergedAt | wc -l

# Calculate: merged_count / total_healer_fixes
```

**Validation**:
- [ ] GitHub API access configured
- [ ] Query for past 30 days of Healer PRs
- [ ] Auto-merge rate ≥ 50%
- [ ] No security bypasses in auto-merged PRs (audit sample of 10)
- [ ] Average time from PR creation to merge < 5 minutes

**Why This Matters**: If most Healer PRs still need manual review, Level 3 gains little benefit. 50% auto-merge is the breakeven point.

---

### Criterion 3: Escalation Rate ≤ 30%

**Definition**: Of all detected issues, ≤30% escalated to humans (confidence < threshold). The rest either pass initially or are fixed by Healer.

**Measurement**:
```bash
./healer-metrics-analyzer.py --days 30 --output healer-report.json

# Check in output:
healer_report.json.escalation.escalation_rate <= 30
```

**Validation**:
- [ ] Escalation rate measured for past 30 days
- [ ] Escalation rate ≤ 30%
- [ ] At least 50 total quality gate checks in period
- [ ] Escalation reasons documented (e.g., "logic regression 15%, infra issue 8%, other 7%")

**Why This Matters**: High escalation means humans are still reviewing most issues. Level 3 requires automation to handle majority of problems.

---

### Criterion 4: Confidence Score Calibration Error < 5%

**Definition**: Diagnostic engine predictions match actual outcomes within 5% margin. If diagnostic engine predicts HIGH confidence, actual success rate is 95% ± 5%.

**Measurement**:
```bash
# Run analyzer with confidence breakdown
./healer-metrics-analyzer.py --days 30 --output healer-report.json

# For each confidence level, calculate:
# actual_success_rate = successful_fixes / total_attempts
# predicted_success_rate = HIGH (95%) | MEDIUM (60%) | LOW (30%)
# calibration_error = |actual - predicted|
```

**Validation**:
- [ ] Confidence breakdown available (HIGH/MEDIUM/LOW attempts and outcomes)
- [ ] HIGH confidence: actual success rate 90-100% (predicted 95% ± 5%)
- [ ] MEDIUM confidence: actual success rate 55-65% (predicted 60% ± 5%)
- [ ] LOW confidence: actual success rate 25-35% (predicted 30% ± 5%)
- [ ] Confidence threshold recommendations reviewed and approved

**Why This Matters**: Miscalibrated confidence scores lead to wrong routing decisions. Under-calibrated (overconfident) → too many failures. Over-calibrated (under-confident) → too many escalations.

---

### Criterion 5: Zero Critical Incidents from Healer Fixes

**Definition**: No production incidents (SEV-1/SEV-2) caused by Healer auto-fixes in past 30 days.

**Validation**:
- [ ] Incident database queried for past 30 days
- [ ] Filter: "root_cause CONTAINS 'healer' OR pr_author == 'healer-engineer[bot]'"
- [ ] Result: zero critical incidents
- [ ] Any SEV-3 incidents reviewed for root cause (process improvement)

**Why This Matters**: Even with 70% success rate, a single critical incident from an auto-fix undermines trust in autonomy.

---

## Pre-Rollout Validation

### Security Review
- [ ] Healer auto-fix scope limited to low-risk categories:
  - [ ] Missing env vars (config, not code logic)
  - [ ] Dependency version updates (bounded, with tests)
  - [ ] Flaky test stabilization (test logic, not business logic)
  - [ ] Lockfile regeneration (dep management, not code)
  - [ ] Import path fixes (syntax, not logic)
- [ ] No Healer access to:
  - [ ] Authentication/authorization code
  - [ ] Database schema migrations
  - [ ] API contract changes
  - [ ] Cryptography/security-critical code

### Process Review
- [ ] Auto-merge guard rails in place:
  - [ ] All quality gates must pass (tests, security, compliance)
  - [ ] Single, isolated change (no multi-file refactoring)
  - [ ] No human escalations triggered
  - [ ] Commit is small and focused
- [ ] Audit trail captures:
  - [ ] What was fixed
  - [ ] Why Healer decided to fix it
  - [ ] Confidence level
  - [ ] Quality gate re-validation results
  - [ ] Auto-merge decision
- [ ] Rollback plan documented:
  - [ ] If Healer auto-merge failure rate > 5%, disable auto-merge
  - [ ] If escalation rate < 10% after Level 3, celebrate success
  - [ ] If critical incident, immediate rollback to Level 2

### Team Sign-Off
- [ ] Data reviewed by Quality Engineer
- [ ] Risk assessment approved by Tech Lead
- [ ] Ops team aware and prepared for monitoring
- [ ] Incident response plan reviewed

---

## Rollout Plan (if approved)

### Phase 1: Single Service Pilot (Week 1)
- [ ] Enable Level 3 on **{example-service}** (lowest risk, critical path)
- [ ] Monitor 24/7: auto-merge rate, incident response, escalation patterns
- [ ] Daily metrics review (ops team)

### Phase 2: Expand to 3 Services (Week 2)
- [ ] If Phase 1 metrics healthy: enable on {service-name}, {example-service}, {example-service}
- [ ] Expand monitoring to dashboard
- [ ] Weekly review with team

### Phase 3: Full Rollout (Week 3+)
- [ ] If all 5 services green: enable on {example-service}, {service-name}, {service-name}
- [ ] Establish ongoing monitoring + feedback loop
- [ ] Monthly readiness reviews

### Fallback to Level 2
- [ ] If auto-merge failure rate > 5%, disable auto-merge (stay at Level 2 routing)
- [ ] If escalation rate > 30%, disable Healer entirely
- [ ] If critical incident: immediate rollback, root cause analysis, process improvement

---

## Measurement Dashboard

**CloudWatch Dashboard**: `ers/healer/level-3-readiness`

Displays:
- Real-time healer success rate (target: ≥ 70%)
- Auto-merge rate (target: ≥ 50%)
- Escalation rate (target: ≤ 30%)
- Confidence calibration error (target: < 5%)
- Critical incident count (target: 0)
- Time-series trends (24h, 7d, 30d)

**Automated Report**: Weekly summary emailed to team with:
- Metric status vs thresholds
- Failure pattern analysis
- Recommended confidence adjustments
- Rollout readiness verdict

---

## Sign-Off Template

```
LEVEL 3 GRADUATION APPROVAL FORM

Date: [DATE]
Reviewed By: [NAME, ROLE]

Criterion 1 (Success Rate ≥ 70%):     [ ] PASS  [ ] FAIL
Criterion 2 (Auto-Merge ≥ 50%):       [ ] PASS  [ ] FAIL
Criterion 3 (Escalation Rate ≤ 30%):  [ ] PASS  [ ] FAIL
Criterion 4 (Calibration Error < 5%): [ ] PASS  [ ] FAIL
Criterion 5 (Zero Critical Incidents): [ ] PASS  [ ] FAIL

Security Review:        [ ] APPROVED  [ ] CONCERNS
Process Review:         [ ] APPROVED  [ ] CONCERNS
Team Sign-Off:          [ ] APPROVED  [ ] CONCERNS

Rollout Decision:
  [ ] APPROVED for Level 3 rollout (all criteria pass)
  [ ] CONDITIONAL: approve with guardrails (specify below)
  [ ] DEFERRED: retry after [N] days (specify concerns below)

Comments:
[...]

Signature: _________________________
```

---

## Failure Recovery

If Level 3 is activated and encounters issues:

### Scenario A: Auto-Merge Failures > 5%
1. Immediately disable auto-merge (Healer still routes, but PRs require review)
2. Analyze failure pattern (which issue types failing?)
3. Re-calibrate confidence thresholds
4. Test new thresholds on [N] builds
5. Retry Level 3 with updated scoring

### Scenario B: Critical Incident from Healer Fix
1. Revert the problematic Healer PR
2. Disable Level 3 entirely; return to Level 2
3. Root cause analysis: did Healer act outside scope? Was confidence miscalibrated?
4. Update guardrails, expand scope of "low-risk" issues
5. Add regression test to prevent recurrence
6. Retry Level 3 after fixes validated

### Scenario C: Escalation Rate Increases (> 40%)
1. Confidence scores drifted (possibly due to new issue types)
2. Re-run confidence calibration immediately
3. Update thresholds for any new patterns
4. Assess if a previously auto-fix-able issue type now needs human judgment

---

## Success Stories (Template)

Once Level 3 succeeds, document wins:

**Example**: "Healer auto-fixed 847 missing env var issues in April without a single incident. Saved ~12 hours of manual review per week."

These successes inform future expansion of Healer scope (e.g., moving from config-only fixes to simple logic fixes).

---

## Next Steps After Level 3

Once Level 3 is stable (2+ weeks of metrics > 95% success):

1. **Scope Expansion**: Enable Healer to fix simple logic bugs (with tests)
2. **PR Automation**: Integrate with GitHub auto-approvers for quick review
3. **Feedback Loop**: Monthly calibration + pattern improvement
4. **Documentation**: Update HEALER-WORKFLOW.md with learned patterns
5. **Team Training**: Ops/engineers understand Healer behavior, trust it
