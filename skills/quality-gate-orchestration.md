---
name: quality-gate-orchestration
description: Master orchestrator for comprehensive quality verification + self-healing feedback loop
type: skill
applies_to: [agentic-engineers framework, ERS services]
phase: "Phase 5 Implementation"
---

# quality-gate-orchestration Skill — Master Quality Gate Orchestrator

Master orchestrator that coordinates all 12 Quality Engineer skills in a comprehensive pre-deployment verification workflow with self-healing feedback loop.

**Responsibility**: Detect quality issues → Diagnose → Route to Healer (if safe) or Escalate → Re-validate → Gate decision (PROCEED/WARN/BLOCK/ESCALATE)

## Quick Start

```bash
# Full pre-deployment verification
/quality-gate-orchestration /home/user/git/ers/{service-name} --deployment-target prod

# Faster check (skip expensive E2E)
/quality-gate-orchestration /home/user/git/ers/{service-name} --skip-e2e

# With state migration validation
/quality-gate-orchestration /home/user/git/ers/{service-name} --deployment-target prod --validate-migrations

# JSON output for CI/CD
/quality-gate-orchestration /home/user/git/ers/{service-name} --json --output-dir ./quality-reports/
```

## Architecture

### The Self-Healing Workflow

```
Input: service_path, deployment_target (dev/staging/prod)
  ↓
PHASE 1: Parallel Quality Checks
  ├─ Testing Layer (parallel):
  │   ├─ test-unit-orchestration
  │   ├─ test-integration-orchestration
  │   ├─ test-e2e-orchestration (optional, expensive)
  │   └─ test-business-logic
  │
  ├─ Security Layer (parallel):
  │   ├─ security-semantic-scan
  │   ├─ security-dependency-scan
  │   └─ security-secret-detection
  │
  ├─ Compliance Layer (parallel):
  │   ├─ requirement-verification
  │   ├─ spec-compliance-verification
  │   └─ (optional) state-migration-verification
  │
  └─ Result: Aggregate pass/fail, identify CRITICAL vs MAJOR vs MINOR issues
  ↓
PHASE 2: Gate Decision (Immediate Check)
  - All checks green? → PROCEED (skip self-healing)
  - Issues found? → PHASE 3 (self-healing loop)
  ↓
PHASE 3: SELF-HEALING LOOP
  For each issue detected:
    1. Call issue-diagnostic-engine
       ↓
    2. Route based on confidence + risk:
       ├─ HIGH confidence + LOW risk → Call healer-engineer (auto-fix)
       │   ├─ Healer creates PR + optional auto-merge
       │   ├─ If Healer succeeds: mark as HEALED
       │   └─ If Healer PR fails CI: escalate to Lead
       │
       └─ LOW confidence OR HIGH risk → Queue for escalation
           ├─ Security findings → escalate to Security Engineer
           ├─ Logic bugs → escalate to Lead Engineer
           └─ Infrastructure → escalate to Principal Engineer
    3. After healing: Re-run affected quality gates (limited scope)
    4. If still fails → Escalate to human (2nd attempt)
  ↓
PHASE 4: Final Gate Decision
  Classify deployment readiness:
  - PROCEED: All checks green, self-healing successful
  - WARN: Major issues with mitigation path documented
  - BLOCK: Critical issues (security, unmet requirements)
  - ESCALATE: Unknowns requiring human judgment
```

## Input Schema

```json
{
  "service_path": "/home/user/git/ers/{service-name}",
  "deployment_target": "prod",  // dev | staging | prod
  "skip_e2e": false,            // skip expensive E2E tests
  "skip_business_logic": false, // skip parametric testing
  "validate_migrations": false, // check state migrations (if applicable)
  "fail_on_warn": false,        // treat WARN as gate failure
  "auto_heal_max_attempts": 2   // max self-healing iterations
}
```

## Output Schema

```json
{
  "service": "{service-name}",
  "deployment_target": "prod",
  "timestamp": "2026-04-28T08:15:00Z",
  "overall_decision": "PROCEED",  // PROCEED | WARN | BLOCK | ESCALATE
  
  "phase_1_results": {
    "testing": {
      "unit": { "passed": 142, "failed": 0 },
      "integration": { "passed": 28, "failed": 0 },
      "e2e": { "passed": 8, "failed": 0, "skipped": 0 },
      "business_logic": { "edge_cases_tested": 32, "passed": 31, "failed": 1 }
    },
    "security": {
      "semantic_findings": 2,           // HIGH: 0, MEDIUM: 2, LOW: 0
      "dependency_vulns": { "critical": 0, "major": 1, "minor": 3 },
      "secrets_detected": 0
    },
    "compliance": {
      "requirements_total": 15,
      "requirements_covered": 15,
      "coverage_percent": 100,
      "specs_compliant_percent": 87.5
    }
  },
  
  "self_healing": {
    "issues_detected": 4,
    "issues_healed": 2,           // e.g., dependency version bumps
    "issues_escalated": 2,        // security findings, logic bugs
    "healer_prs_created": 2,
    "healer_prs_urls": ["#125", "#126"],
    "healer_success_rate": 50,    // 2 of 4 issues auto-fixed
    "escalations": [
      {
        "issue_id": "security-finding-1",
        "type": "security_finding",
        "severity": "HIGH",
        "description": "JWT scope not validated in Lambda handler",
        "route_to": "security",
        "escalation_time": "2026-04-28T08:16:00Z"
      }
    ]
  },
  
  "gate_details": {
    "all_tests_green": true,
    "no_critical_security_issues": false,  // 1 escalated to Security
    "all_requirements_covered": true,
    "specs_compliant": true,
    "deployment_target_strictness": "prod"
  },
  
  "deployment_ready": true,
  "gate_status": "PROCEED",
  "warnings": [],
  "blockers": [],
  
  "audit_trail": [
    { "timestamp": "2026-04-28T08:15:00Z", "event": "PHASE_1_START", "details": "Running 12 quality skills" },
    { "timestamp": "2026-04-28T08:15:30Z", "event": "TESTING_COMPLETE", "details": "178 tests passed" },
    { "timestamp": "2026-04-28T08:16:00Z", "event": "SECURITY_ISSUE_DETECTED", "details": "JWT scope bypass found" },
    { "timestamp": "2026-04-28T08:16:15Z", "event": "HEALER_ROUTED", "details": "Missing env var → auto-fix" },
    { "timestamp": "2026-04-28T08:16:45Z", "event": "HEALER_SUCCESS", "details": "PR #125 created + merged" },
    { "timestamp": "2026-04-28T08:17:00Z", "event": "ESCALATION", "details": "Security finding → Security Engineer" },
    { "timestamp": "2026-04-28T08:17:30Z", "event": "PHASE_4_DECISION", "details": "PROCEED (with escalation review)" }
  ],
  
  "report_location": "/home/user/git/ers/quality-reports/{service-name}/2026-04-28-08-15/report.json"
}
```

## Options

```
--deployment-target    dev | staging | prod (default: dev)
--skip-e2e            Skip expensive Playwright tests (default: false)
--skip-business-logic Skip parametric testing (default: false)
--validate-migrations Check state migrations if applicable (default: false)
--fail-on-warn        Treat WARN as gate failure (default: false)
--json                JSON output (default: console + markdown)
--output-dir          Report directory (default: ./quality-reports/)
--max-heal-attempts   Self-healing loop max iterations (default: 2)
--no-auto-merge       Never auto-merge Healer PRs, just create (default: false)
```

## Deployment-Target Strictness

Different deployment targets have different quality thresholds:

**dev**:
- ✅ Tests can have flakiness (re-run once)
- ✅ Requirements can be partial (in-flight)
- ⚠️  Security findings can be reviewed offline
- ✅ Specs can deviate with documentation

**staging**:
- ✅ All tests must pass (flakiness not acceptable)
- ✅ All requirements must be covered (or exempted)
- ⚠️  Security findings must be reviewed within 24h
- ✅ Specs must be 90%+ compliant

**prod**:
- ✅ ALL tests MUST pass (no exceptions)
- ✅ ALL requirements MUST be covered (100%)
- ❌ NO critical security findings (all escalated)
- ✅ Specs MUST be 95%+ compliant
- ✅ State migrations (if applicable) MUST be validated

## Integration Points

### Called by:
- GitHub Actions (main.yaml pre-deployment step)
- Orchestrator agent (manual verification)
- Pre-push hooks (informational)

### Calls (in parallel where safe):
1. test-unit-orchestration
2. test-integration-orchestration
3. test-e2e-orchestration
4. test-business-logic
5. security-semantic-scan
6. security-dependency-scan
7. security-secret-detection
8. requirement-verification
9. spec-compliance-verification
10. (optional) state-migration-verification
11. issue-diagnostic-engine (per issue)
12. healer-engineer (per auto-fixable issue)

### Output consumed by:
- GitHub Actions: JSON for CI/CD gating
- Slack: summary + links to Healer PRs
- CloudWatch: metrics + alarms
- S3: report archive for audit trail

## Self-Healing Thresholds

**Healer eligible (auto-fix, no escalation)**:
- Missing environment variable (HIGH confidence, LOW risk)
- Dependency patch version bump (HIGH confidence, LOW risk)
- Flaky test (stabilize with retry, HIGH confidence, LOW risk)
- Lockfile regeneration (HIGH confidence, LOW risk)
- Import path fixes (HIGH confidence, LOW risk)

**Escalate immediately (no auto-fix)**:
- Security findings (always escalate to Security Engineer)
- Logic regressions (escalate to Lead Engineer)
- Infrastructure issues (escalate to Principal)
- Database migrations (escalate to Lead + validation)
- Major dependency version bumps (escalate to Lead)

## Exit Codes

```
0   PROCEED (all checks green, ready to deploy)
1   WARN (issues found, but mitigation documented, requires approval)
2   BLOCK (critical issues, must fix before deployment)
3   ESCALATE (requires human judgment, routed to appropriate role)
4   ERROR (orchestrator itself failed, investigate)
```

## Example: Full Pre-Deployment Run

```bash
$ /quality-gate-orchestration /home/user/git/ers/{service-name} --deployment-target prod --json

[2026-04-28 08:15:00] Starting Phase 1: Quality checks...
[2026-04-28 08:15:03] ✅ test-unit-orchestration: 142 passed
[2026-04-28 08:15:15] ✅ test-integration-orchestration: 28 passed
[2026-04-28 08:15:45] ✅ test-e2e-orchestration: 8 passed
[2026-04-28 08:16:00] ⚠️  test-business-logic: 31 passed, 1 edge case failed
[2026-04-28 08:16:15] ⚠️  security-semantic-scan: 2 findings (MEDIUM severity)
[2026-04-28 08:16:30] ✅ security-dependency-scan: no critical vulnerabilities
[2026-04-28 08:16:45] ✅ security-secret-detection: no secrets detected
[2026-04-28 08:17:00] ✅ requirement-verification: 15/15 requirements covered
[2026-04-28 08:17:15] ✅ spec-compliance-verification: 87.5% compliant

Phase 1 complete: 4 issues detected
  → 1 edge case (test failure)
  → 2 security findings (MEDIUM)
  → 1 failed state migration test

Starting Phase 3: Self-Healing...
[2026-04-28 08:17:30] Diagnosing edge case failure...
  → Root cause: parameterized test missing boundary condition
  → Confidence: LOW, Risk: MEDIUM
  → Action: Escalate to Lead Engineer
[2026-04-28 08:17:45] Diagnosing security findings...
  → Root cause 1: Missing input validation (MEDIUM severity)
  → Root cause 2: Weak crypto usage (MEDIUM severity)
  → Confidence: HIGH, Risk: HIGH
  → Action: Escalate to Security Engineer

Phase 3 complete: 0 auto-fixed, 3 escalated

Final Decision: BLOCK (critical issues require review)
Exit code: 2

Report saved: /home/user/git/ers/quality-reports/{service-name}/2026-04-28-08-15/report.json
```

## Related Skills

- `test-unit-orchestration.md` — Unit test discovery + execution
- `test-integration-orchestration.md` — Integration test orchestration
- `test-e2e-orchestration.md` — E2E test filtering + execution
- `test-business-logic.md` — Business logic verification
- `security-semantic-scan.md` — Semantic security scanning
- `security-dependency-scan.md` — Dependency vulnerability scanning
- `security-secret-detection.md` — Hardcoded secret detection
- `requirement-mapping.md` — Requirement traceability
- `requirement-verification.md` — Requirement coverage validation
- `spec-compliance-verification.md` — Spec compliance checking
- `issue-diagnostic-engine.md` — Root cause analysis
- `healer-engineer.md` — Automated issue fixing

## Architecture Notes

**Parallel Execution**: Testing, security, and compliance checks run in parallel (3 independent layers). No shared state, safe to parallelize.

**Self-Healing Loop**: Critical for fast feedback. Healer auto-fixes low-risk issues (env vars, dependency patches) within minutes, vs hours for human review.

**Deployment-Target Awareness**: Prod gates are stricter (100% requirement coverage) vs dev (partial OK). Configured per-target.

**Audit Trail**: Every action logged (issue detected, diagnosed, healed/escalated, outcome). Used for continuous improvement.

**Token Efficiency**: Entire check costs ~$0.36 per service. E2E skippable if needed. Healer saves tokens vs manual fixes.

---

**Status**: Implementation ready  
**Integration**: Primary pre-deployment gate for all 8 ERS services
**Next**: Deploy to GitHub Actions (main.yaml)
