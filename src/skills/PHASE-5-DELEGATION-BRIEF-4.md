---
name: Phase 5.5 — Lead Engineer Track (Self-Healing Skills)
description: Build 2 self-healing skills for issue diagnosis and automated fixing
type: delegation-brief
version: 1.0
date: 2026-04-27
---

# Phase 5.5: Lead Engineer Track — Self-Healing Feedback Loop Skills

**Delegation**: Lead Engineer (Opus)  
**Timeline**: 1.5 days  
**Blocking**: Track 1 (testing), Track 2 (security), Track 3 (compliance) must be done first  
**Deliverables**: 2 skill .md files + git commits

---

## Skills to Build

### 11. issue-diagnostic-engine.md
**Purpose**: Analyze quality gate failures, diagnose root cause, assign confidence + risk scores

**Input Spec**:
```
failure_log: dict  # structured failure from quality gate (test, security, config)
service_path: str
failure_type: str  # "test_failure", "security_finding", "config_missing", "dependency_issue"

# Example failure_log from test-unit-orchestration:
# {
#   "test_name": "TestUserCreation",
#   "error": "expected database connection to exist",
#   "stack_trace": "models_test.go:42: database not initialized"
# }
```

**Output Spec**:
```json
{
  "failure": "test failed: expected database connection to exist",
  "root_cause": "configuration",
  "root_cause_category": "config_missing",
  "root_cause_details": "Environment variable DATABASE_URL not set in Lambda test environment",
  "confidence": "HIGH",
  "risk_level": "LOW",
  "suggested_fix": "Add DATABASE_URL to cdk/stacks/command_stack.go Lambda environment variables, or set in test setup",
  "healer_eligible": true,
  "can_auto_fix": true,
  "fix_files": ["cdk/stacks/command_stack.go"],
  "issue_type": "missing_env_var",
  "escalation_needed": false,
  "escalation_reason": null,
  "estimated_effort": "5 minutes"
}
```

**Implementation Notes**:
- Input sources: failures from test-unit-orchestration, security scans, deployment errors
- Root cause categories:
  - `dependency`: missing dependency, version conflict, outdated package
  - `configuration`: missing env var, wrong path, incorrect permission
  - `test_flakiness`: timing issue, data race, concurrency problem
  - `logic_regression`: code bug (requires code review)
  - `infrastructure`: service unavailable, network issue
  - `security`: missing validation, injection vulnerability (requires security review)
- Confidence scoring:
  - HIGH: Pattern-matchable error (missing var, known flakiness)
  - LOW: Ambiguous error (logical bug, infrastructure issue)
- Risk scoring:
  - LOW: Safe to auto-fix (env var, dependency version, flaky retry)
  - HIGH: Requires human review (security, logic, architecture)
- Healer eligibility: `confidence == HIGH AND risk_level == LOW`

**Analysis Process**:
1. Parse failure log (test output, security finding, error message)
2. Pattern match against known issues (missing env vars, flaky patterns, etc.)
3. If pattern found → HIGH confidence
4. If ambiguous → LOW confidence
5. Determine risk: safe fixes (env, deps) = LOW risk; changes affecting logic = HIGH risk
6. Suggest remediation (code file, exact change)
7. Route: high conf + low risk → Healer; low conf OR high risk → escalation

**Success Criteria**:
✓ Diagnose missing env var correctly → HIGH confidence, suggest fix  
✓ Diagnose logic bug correctly → LOW confidence, escalate  
✓ Diagnose flaky test → HIGH confidence, suggest retry logic  
✓ Score confidence and risk appropriately  
✓ Suggest concrete code changes (file + line)

**Related Specs**:
- QUALITY-ENGINEER-DESIGN.md § Decision 4 (Self-Healing Feedback Loop)
- PHASE-5-SKILL-SPECIFICATIONS.md § Skill 11

---

### 12. healer-engineer.md
**Purpose**: Auto-fix low-risk, pattern-matchable issues; create PR + optional auto-merge

**Input Spec**:
```
diagnostic: dict  # from issue-diagnostic-engine
service_path: str
create_pr: bool = True
auto_merge_if_ci_passes: bool = True
```

**Output Spec**:
```json
{
  "issue_fixed": true,
  "fix_type": "missing_env_var",
  "issue_type": "config_missing",
  "root_cause": "DATABASE_URL not set in Lambda environment",
  "file_modified": "cdk/stacks/command_stack.go",
  "change_made": "Added DATABASE_URL='postgresql://localhost/test' to Lambda environment variables",
  "fix_applied": "✓ File updated",
  "pr_created": true,
  "pr_number": 123,
  "pr_url": "https://github.com/{your-org}/{service-name}/pull/123",
  "pr_title": "fix(config): add missing DATABASE_URL env var to Lambda",
  "pr_status": "CI_RUNNING",
  "auto_merge_eligible": true,
  "auto_merge_triggered": false,
  "notes": "Fix applied successfully; CI running. Will auto-merge if all checks pass.",
  "audit_trail": {
    "fixer": "healer-engineer",
    "timestamp": "2026-04-27T14:32:00Z",
    "diagnostic_input": "from issue-diagnostic-engine",
    "confidence": "HIGH",
    "risk_level": "LOW"
  }
}
```

**Implementation Notes**:
- Eligibility: only execute if HIGH confidence + LOW risk (from diagnostic)
- Auto-fix types allowed (only these):
  - `missing_env_var`: add to CDK stack environment vars + .env file
  - `dependency_version`: update go.mod/package.json + regenerate lockfile (go mod tidy, npm install)
  - `flaky_test`: add retry logic or stabilize test data setup
  - `lockfile_stale`: regenerate package-lock.json or go.sum
  - `import_path_wrong`: fix import statement (single file)
- Auto-fix types NOT allowed:
  - Logic bugs (requires code review)
  - Security issues (requires security review)
  - Architecture changes (requires design discussion)
- Create PR: conventional commit message (e.g., "fix(config): add missing DATABASE_URL")
- Auto-merge decision:
  - All quality gates pass (tests, security, lint)
  - No human escalations triggered
  - Single, isolated change (<5 files affected)
  - Audit trail complete
- Tracking: log what was fixed, when, outcome (feedback to Orchestrator)

**PR Creation Process**:
1. Clone or pull latest main
2. Create branch: `git checkout -b fix/missing-database-url`
3. Apply fix (edit file, update env, etc.)
4. Commit: `git commit -m "fix(config): add missing DATABASE_URL env var"`
5. Push: `git push -u origin fix/missing-database-url`
6. Create PR via GitHub API: `gh pr create ...`
7. Wait for CI (tests, lint, security scans)
8. If all pass + auto_merge_if_ci_passes → merge PR

**Success Criteria**:
✓ Auto-fix missing env var  
✓ Create PR with proper commit message  
✓ Optionally auto-merge if CI passes  
✓ Escalate if fix PR fails CI  
✓ Maintain audit trail (who/what/when)

**Related Specs**:
- QUALITY-ENGINEER-DESIGN.md § Decision 4 (Self-Healing Feedback Loop)
- QUALITY-ENGINEER-DESIGN.md § Decision 5 (Escalation Thresholds)
- PHASE-5-SKILL-SPECIFICATIONS.md § Skill 12

---

## Integration Points

**Inputs from Previous Tracks**:
- Test failures from Track 1 → diagnostic engine
- Security findings from Track 2 → diagnostic engine
- Requirement verification issues from Track 3 → diagnostic engine

**Outputs for Next Track**:
- Healer results feed into quality-gate-orchestration (master orchestrator)
- Escalations feed into human review queue (Lead/Principal/Security)
- Audit trail feeds into quality reporting

**Workflow**:
```
Test/Security/Config Failure
  ↓
issue-diagnostic-engine (classify + score)
  ↓
  ├─ HIGH confidence + LOW risk → healer-engineer (auto-fix)
  │   ├─ Fix succeeds → PR created + potentially auto-merged
  │   └─ Fix fails → escalate to Lead Engineer
  │
  └─ LOW confidence OR HIGH risk → escalate to Lead/Principal/Security
```

**Success Criteria for Track**:
- Both skills implemented + tested locally
- Each skill callable as independent module or CLI
- Output JSON matches spec exactly
- Diagnostic engine classifies issues correctly
- Healer successfully auto-fixes low-risk issues
- Escalation path working (high-risk issues → human)

---

## Implementation Steps

1. **Create skill files** (hours 0-2):
   - issue-diagnostic-engine.md
   - healer-engineer.md

2. **Implement in parallel** (hours 2-20):
   - Diagnostic: pattern matching + confidence/risk scoring
   - Healer: file editing + PR creation + optional auto-merge
   - Test with simulated failures from Track 1 (missing env vars, flaky tests)

3. **Validate** (hours 20-24):
   - Run diagnostic on real test failures from {service-name}
   - Run healer on missing env var → verify PR created
   - Run healer on flaky test → verify retry logic added
   - Verify auto-merge decision logic

4. **Git commit**:
   - One commit per skill file: `feat(skills): add issue-diagnostic-engine skill`

---

## Risk Management

**Healer Guardrails**:
- Only auto-fix if diagnostic confidence = HIGH + risk = LOW
- Never auto-fix logic bugs (requires code review)
- Never auto-fix security issues (requires security review)
- All auto-fixed PRs must pass CI before merge
- Audit trail tracks all auto-fixes (for compliance + feedback)

**Escalation Paths**:
- Diagnostic confidence = LOW → Lead Engineer review
- Risk level = HIGH → Security Engineer (security) or Principal (architecture)
- Auto-fix PR fails CI → escalate to Lead Engineer

---

## Success Definition

Track is complete when:
- [ ] Both .md skill files created in `/skills/`
- [ ] Each file includes: purpose, input spec, output spec, implementation notes
- [ ] Diagnostic engine classifies missing env var correctly (HIGH conf, LOW risk)
- [ ] Diagnostic engine classifies logic bug correctly (LOW conf, escalate)
- [ ] Healer successfully auto-fixes missing env var
- [ ] Healer creates PR with proper commit message
- [ ] Healer respects guardrails (no security/logic fixes)
- [ ] All output JSON matches spec
- [ ] Both committed to git with clear messages
- [ ] Ready to integrate with Track 5 (master orchestrator)

---

**Version**: 1.0  
**Status**: Ready for delegation  
**Owner**: Lead Engineer (Opus)  
**Blocking On**: Track 1 (testing), Track 2 (security), Track 3 (compliance)  
**Start Date**: 2026-04-29 (after foundational tracks)  
**Target Date**: 2026-04-30
