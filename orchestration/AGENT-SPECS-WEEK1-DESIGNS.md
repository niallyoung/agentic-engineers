---
name: Week 1 Agent Specification Designs
description: Complete design specifications for 7 agents to fix AGENTS.md compliance across agentic-engineers workflows
type: design
phase: architecture-remediation-week1
created: 2026-04-28
status: DESIGN_COMPLETE
---

# Week 1 Agent Specification Designs

**Designed By**: Principal Engineer (Opus)  
**Design Date**: 2026-04-28  
**Target Implementation**: Week 2 (2026-05-05 to 2026-05-12)  
**Integration Goal**: Phase 5.10 Quality Orchestration Foundation

---

## Overview

This document defines 7 agent specifications to replace non-compliant shell scripts with proper AGENTS.md routing and DELEGATE/HANDBACK protocol. Each agent includes:

- **Role Assignment**: From AGENTS.md + duty
- **Model + Effort**: Optimal cost/capability match
- **Input/Output Contracts**: DELEGATE → HANDBACK data flow
- **Integration Points**: Where and how to invoke
- **Example DELEGATE Block**: For Week 2 engineers to use as template
- **Example HANDBACK Block**: What success looks like
- **Implementation Success Criteria**: What validates completion
- **Open Questions**: Clarifications needed from Orchestrator

---

## Agent 1: Quality Gate Orchestrator

**Purpose**: Master entry point for all quality checks; coordinates 4 parallel sub-agents (Security, Testing, Metrics, Healing); aggregates results and makes PROCEED/ESCALATE decision.

**Current Issue**: `make quality-gate` target runs shell scripts directly; no DELEGATE/HANDBACK audit trail; no budget awareness.

### Role & Model Assignment

| Field | Value | Rationale |
|-------|-------|-----------|
| **Role** | Orchestrator (specialized) | Master coordinator; routes to sub-agents |
| **Model** | claude-sonnet-4-6 | High coordination complexity; understands full quality landscape |
| **Effort** | high | Parallel delegation, aggregation logic, decision tree |

### Input Requirements (DELEGATE Block)

```yaml
input:
  source: make quality-gate (or API trigger)
  provides:
    - repo_path: "/home/user/git/ers/{service}"
    - service_name: "{service-name}" (etc)
    - commit_sha: "abc123def456" (optional)
    - force_full_checks: false (skip fast-path if true)
    - budget_context: 
        session_pct: 45.0
        trend: "stable"
        recommended_model: "sonnet"
```

### Output Requirements (HANDBACK Block)

```yaml
output:
  final_decision: "PROCEED" | "ESCALATE"
  checks_passed:
    security: { status: "PASS" | "WARN" | "FAIL", severity: "low" | "medium" | "high" }
    testing: { status: "PASS" | "FAIL", coverage: 85.3 }
    metrics: { status: "PASS" | "WARN", health_score: 92 }
    healing: { status: "PASS" | "ESCALATED", auto_fixed: 3, escalated: 1 }
  escalation_path: null | { agent: "Security Engineer", reason: "..." }
  audit_trail:
    - timestamp: "2026-04-28T10:15:00Z"
      agent: "Testing Agent"
      result: "5 unit tests passed, 2 e2e tests failed"
  total_duration_seconds: 145
  cloudwatch_logged: true | false
  recommendation: "Ready to merge; 2 escalations require human review"
```

### Integration Points

**Invoked From**:
- `make quality-gate` target (thin wrapper calls DELEGATE)
- GitHub Actions pre-merge workflow (calls DELEGATE via CLI)
- Manual developer trigger (local verification)

**Invokes**:
- Security Check Agent (DELEGATE)
- Testing Agent (DELEGATE)
- Metrics Agent (DELEGATE)
- Healer Agent (DELEGATE)

**Parallel Execution**: All 4 sub-agents delegated simultaneously; Quality Orchestrator waits for all HANDBACK blocks before aggregating.

### Example DELEGATE Block

```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-05-quality-orchestrator-{service-name}
timestamp: 2026-05-05T09:00:00Z
role: Quality Gate Orchestrator
model: claude-sonnet-4-6
effort: high
scope: >
  Execute full quality gate for {service-name} service. Delegate to Security, Testing, 
  Metrics, and Healing agents in parallel. Aggregate results. Return PROCEED or 
  ESCALATE decision with audit trail suitable for CI/CD pipeline consumption.
context:
  - Service: {service-name} (Go/Lambda)
  - Commit: abc123def456
  - Budget: 45.0% session available, trend stable
  - Previous metrics: 92/100 health score
  - Phase 5.10 depends on this orchestrator being bulletproof
plan:
  1. Read budget context from Orchestrator
  2. DELEGATE to Security Agent (credential scanning, compliance checks)
  3. DELEGATE to Testing Agent (unit + e2e + coverage analysis)
  4. DELEGATE to Metrics Agent (health score, trend analysis)
  5. DELEGATE to Healer Agent (identify + auto-fix low-risk issues)
  6. Wait for all 4 HANDBACK blocks
  7. Aggregate results into final decision
  8. Log to CloudWatch (optional, depends on ENABLE_CLOUDWATCH)
  9. Return HANDBACK with audit_trail + escalation_path
success_criteria:
  - All 4 sub-agents complete successfully
  - Final decision is either PROCEED or ESCALATE (no ambiguous states)
  - Audit trail includes timestamp + agent + result for each sub-check
  - Total execution < 300 seconds (5 min timeout)
  - CloudWatch logging succeeds if ENABLE_CLOUDWATCH=true
---
```

### Example HANDBACK Block

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-05-quality-orchestrator-{service-name}
timestamp: 2026-05-05T09:04:30Z
status: complete
final_decision: PROCEED
checks_passed:
  security:
    status: PASS
    credential_scans: 0
    compliance_violations: 0
  testing:
    status: PASS
    unit_tests: "145 passed"
    e2e_tests: "23 passed"
    coverage: 87.3
  metrics:
    status: PASS
    health_score: 93
    trend: "improving"
    latency_p95: 245
  healing:
    status: PASS
    issues_found: 2
    auto_fixed: 2
    escalated: 0
audit_trail:
  - timestamp: 2026-05-05T09:00:15Z
    agent: Security Agent
    result: "PASS - no credentials, 0 violations"
  - timestamp: 2026-05-05T09:01:30Z
    agent: Testing Agent
    result: "PASS - 145 unit, 23 e2e, 87.3% coverage"
  - timestamp: 2026-05-05T09:02:45Z
    agent: Metrics Agent
    result: "PASS - health 93, trending up"
  - timestamp: 2026-05-05T09:03:20Z
    agent: Healer Agent
    result: "PASS - fixed 2 linting issues automatically"
total_duration_seconds: 270
cloudwatch_logged: true
escalation_path: null
recommendation: "Healthy service; ready to merge. Auto-fixes applied (2 lint issues)."
---
```

### Implementation Success Criteria (Week 2 Engineer)

- [ ] Agent accepts DELEGATE with repo_path, service_name, commit_sha, budget_context
- [ ] Agent delegates to all 4 sub-agents simultaneously (parallel execution)
- [ ] Agent waits for all 4 HANDBACK blocks (timeout after 5 min)
- [ ] Agent aggregates results into single HANDBACK block
- [ ] HANDBACK includes audit_trail with all sub-agent results
- [ ] Final decision is PROCEED or ESCALATE (no ambiguous states)
- [ ] CloudWatch logging works if ENABLE_CLOUDWATCH=true
- [ ] Can be invoked from `make quality-gate` wrapper
- [ ] Can be invoked from GitHub Actions
- [ ] HANDBACK correctly reflects success/failure of each check

### Open Questions for Design Review

1. **Fast Path**: Should Quality Orchestrator support fast-path (e.g., skip metrics if nothing changed)? If yes, what triggers fast-path?
2. **Timeout Strategy**: If a sub-agent times out (e.g., Testing Agent hangs), should Orchestrator escalate immediately or wait?
3. **Rollback on Failure**: If Healer Agent fixes something but Testing Agent then fails, should we escalate or auto-rollback fixes?
4. **CloudWatch Integration**: Should CloudWatch logging be required or optional? Current plan is optional with ENABLE_CLOUDWATCH flag.

---

## Agent 2: Token Advisor

**Purpose**: Monitors session token budget; recommends optimal model tier (Haiku/Sonnet/Opus) for upcoming tasks; provides budget awareness to Orchestrator.

**Current Issue**: Token usage tracked by shell scripts (`capture_token_usage.sh`); budget decisions made implicitly outside agent network; no structured HANDBACK on recommendations.

### Role & Model Assignment

| Field | Value | Rationale |
|-------|-------|-----------|
| **Role** | Model Engineer (new authority) | Optimal for budget + model selection decisions |
| **Model** | claude-sonnet-4-6 | Understands token patterns; makes confident recommendations |
| **Effort** | medium | Periodic analysis, not real-time; lightweight calculations |

### Input Requirements (DELEGATE Block)

```yaml
input:
  source: Orchestrator (pre-delegation check)
  provides:
    - analysis_type: "current_status" | "trend" | "recommendation"
    - task_complexity: "low" | "medium" | "high" | "max" (optional, for recommendations)
    - horizon: 60 (look-ahead minutes, default)
```

### Output Requirements (HANDBACK Block)

```yaml
output:
  session_pct: 45.0
  tokens_used: 87300
  tokens_available: 200000
  trend: "stable" | "increasing" | "critical"
  velocity: 1200 (tokens/minute over last 30 min)
  ttl_minutes: 420 (until reset)
  recommended_model: "haiku" | "sonnet" | "opus"
  recommendation_confidence: 0.95
  warning: null | "approaching session limit"
  actions:
    - "Switch to Haiku for routine tasks"
    - "Use Sonnet for medium-complexity work"
    - "Reserve Opus for critical design work only"
```

### Integration Points

**Invoked From**:
- Orchestrator (before each major DELEGATE)
- Quality Gate Orchestrator (for budget context in sub-agent delegation)
- Manual developer query (via CLI `make show-budget` or similar)

**Timing**: Invoked at start of session + before delegating high-effort tasks

### Example DELEGATE Block

```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-05-token-advisor-status-check
timestamp: 2026-05-05T09:00:00Z
role: Token Advisor (Model Engineer)
model: claude-sonnet-4-6
effort: medium
scope: >
  Analyze current session token usage. Provide current session percentage, 
  usage trend over last 30 minutes, velocity estimate, and recommendation 
  for optimal model tier for upcoming high-complexity design work (Principal 
  Engineer task expected).
context:
  - Previous status: 42% at 2026-05-05T08:00:00Z
  - Task ahead: Principal Engineer design (estimated 4000 tokens)
  - Phase 5.10 critical path depends on efficient token usage
plan:
  1. Query session token metrics (from Orchestrator context or SSM)
  2. Calculate velocity (tokens/min over last 30 min)
  3. Project TTL (time to reset)
  4. Analyze trend (stable/increasing/critical)
  5. Recommend model tier for Principal work
  6. Flag warnings if approaching limits
  7. Return HANDBACK with all metrics + recommendations
success_criteria:
  - session_pct, tokens_used, tokens_available all populated
  - trend accurately reflects recent usage pattern
  - recommended_model is defensible (not just Haiku to save money)
  - confidence score is calibrated (0.7+ = trusted, 0.5-0.7 = caution)
  - warnings trigger only if real constraint (not pessimistic)
---
```

### Example HANDBACK Block

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-05-token-advisor-status-check
timestamp: 2026-05-05T09:01:15Z
status: complete
session_pct: 45.2
tokens_used: 90400
tokens_available: 200000
trend: stable
velocity: 1150
ttl_minutes: 410
recommended_model: sonnet
recommendation_confidence: 0.92
warning: null
actions:
  - "Principal Engineer design task (4000 tokens estimated) is within safe budget"
  - "After Principal task, switch to Haiku/Sonnet for Week 2 implementation"
  - "Monitor velocity; if exceeds 1500 tokens/min, escalate to human"
analysis_details:
  last_30min_tokens: 34500
  avg_per_minute: 1150
  session_reset_at: "2026-05-05T23:59:59Z"
  historical_trend: "stable (±100 tokens/min variance)"
---
```

### Implementation Success Criteria (Week 2 Engineer)

- [ ] Agent reads token metrics from Orchestrator context (or SSM if available)
- [ ] Agent calculates session_pct, velocity, trend
- [ ] Agent recommends model tier based on budget + upcoming work complexity
- [ ] Confidence score is calibrated (0.7+ = trusted, 0.5-0.7 = caution, <0.5 = escalate)
- [ ] Warnings only trigger on real constraints
- [ ] HANDBACK includes actions list (not just numbers)
- [ ] Can be invoked before each major DELEGATE by Orchestrator
- [ ] Works in sessions with varied token usage patterns

### Open Questions for Design Review

1. **Data Source**: Where does Token Advisor read token metrics? Orchestrator context? SSM? CloudWatch? (Currently implicit in shell scripts)
2. **Caching**: Should Token Advisor cache results (e.g., don't recompute every 30s)? Recommendation: cache for 2 min.
3. **Escalation**: At what point does "warning" become "escalate to human"? (e.g., <50k tokens left = escalate?)
4. **Model Recommendations**: Should recommendations factor in task urgency (e.g., if Phase 5.10 critical, use Opus even if expensive)?

---

## Agent 3: Config Audit

**Purpose**: Scans service configurations (Makefile, CDK, env files, CLAUDE.md) against ERS standards; identifies deviations and non-compliance; rates severity.

**Current Issue**: Config validation is scattered across `{service-name}.md` + skill docs; no agent executes periodic audits; no structured report.

### Role & Model Assignment

| Field | Value | Rationale |
|-------|-------|-----------|
| **Role** | Quality Engineer | Compliance verification; post-implementation quality gate |
| **Model** | claude-sonnet-4-6 | Understands full ERS config standard; can read multiple file formats |
| **Effort** | medium | Static analysis; no code execution |

### Input Requirements (DELEGATE Block)

```yaml
input:
  source: Quality Gate Orchestrator (periodic) or manual trigger
  provides:
    - service_path: "/home/user/git/ers/{service-name}"
    - audit_scope: "full" | "makefile" | "cdk" | "env" | "claude-md"
    - strict_mode: false (report warnings; true = fail on any deviation)
```

### Output Requirements (HANDBACK Block)

```yaml
output:
  service: "{service-name}"
  audit_timestamp: "2026-05-05T09:15:00Z"
  scope: "full"
  status: "PASS" | "WARN" | "FAIL"
  deviations:
    - file: "Makefile"
      line: 5
      rule: "must include env/.env.$(ENV_NAME)"
      current: "# no env file inclusion"
      severity: "high"
      remediation: "Add: -include env/.env.$(ENV_NAME)"
    - file: "cdk/main.go"
      line: 45
      rule: "must read DNS_ROOT_DOMAIN from env"
      current: "rootDomain := \"hardcoded.com\""
      severity: "medium"
      remediation: "Use os.Getenv(\"DNS_ROOT_DOMAIN\")"
  deviation_count: 2
  high_severity: 1
  medium_severity: 1
  low_severity: 0
  compliance_score: 92
  last_audit: "2026-04-28T16:00:00Z"
  trend: "improving" | "stable" | "declining"
  recommendation: "Fix high-severity issues before merge; medium-severity can be scheduled"
```

### Integration Points

**Invoked From**:
- Quality Gate Orchestrator (periodic audit during quality checks)
- Manual trigger: `make audit-config`
- Cleanup Agent (pre-cleanup, verify no untracked config deviations)

### Example DELEGATE Block

```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-05-config-audit-{service-name}
timestamp: 2026-05-05T09:15:00Z
role: Config Audit Agent (Quality Engineer)
model: claude-sonnet-4-6
effort: medium
scope: >
  Audit {service-name} service configuration against ERS Configuration & Dependency 
  Management Standard. Check Makefile, CDK, env files, CLAUDE.md for compliance. 
  Report deviations with severity and remediation guidance. Provide compliance score.
context:
  - Standard location: ~/.agents/agentic-engineers/skills/{service-name}.md
  - Service path: /home/user/git/ers/{service-name}
  - Previous audit: 2026-04-28 (full compliance)
  - Last deviation trend: stable
plan:
  1. Load ERS configuration standard from skills/{service-name}.md
  2. Read target service files (Makefile, cdk/main.go, env/*, CLAUDE.md)
  3. Check each rule from standard against actual files
  4. Rate severity (high/medium/low) for each deviation
  5. Calculate compliance score (100 - deviations)
  6. Compare to previous audit (identify trend)
  7. Return HANDBACK with all deviations + recommendations
success_criteria:
  - All deviations identified with line numbers
  - Severity ratings are consistent (high = blocking, medium = should fix, low = nice to have)
  - Remediation guidance is specific and actionable
  - Compliance score accurately reflects deviation count
  - Trend (improving/stable/declining) matches historical pattern
  - Can run multiple times in succession without false positives
---
```

### Example HANDBACK Block

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-05-config-audit-{service-name}
timestamp: 2026-05-05T09:16:45Z
status: complete
service: {service-name}
audit_timestamp: 2026-05-05T09:16:45Z
scope: full
status: WARN
deviations:
  - file: "env/.env.prod"
    line: 3
    rule: "DNS_ROOT_DOMAIN must be set"
    current: "# DNS_ROOT_DOMAIN=evolutionrollersports.com"
    severity: high
    remediation: "Uncomment or populate DNS_ROOT_DOMAIN=evolutionrollersports.com"
deviation_count: 1
high_severity: 1
medium_severity: 0
low_severity: 0
compliance_score: 99
last_audit: 2026-04-28T16:00:00Z
trend: stable
recommendation: "Fix high-severity issue (uncomment DNS_ROOT_DOMAIN in prod env). Otherwise passing audit."
---
```

### Implementation Success Criteria (Week 2 Engineer)

- [ ] Agent reads ERS configuration standard from skills directory
- [ ] Agent reads service Makefile, CDK, env files, CLAUDE.md
- [ ] Agent compares each rule against actual files
- [ ] Agent identifies all deviations with file + line number
- [ ] Severity ratings (high/medium/low) are documented and consistent
- [ ] Remediation guidance is specific and actionable
- [ ] Compliance score calculated and accurate
- [ ] Trend (improving/stable/declining) tracked across audits
- [ ] Can be invoked repeatedly without false positives

### Open Questions for Design Review

1. **Scope Options**: Should audit support granular scope (e.g., `scope: "makefile"` to skip CDK check)? Yes, include in design.
2. **Auto-Fix Requests**: Should Config Audit recommend escalation to Config Enforcement Agent for auto-fixing? If yes, under what conditions?
3. **Service-Specific Rules**: Should standard have per-service rules (e.g., {service-name} doesn't need all Go checks)? Recommendation: mark rules as `applies_to: [all] or [service_list]`.

---

## Agent 4: Config Enforcement

**Purpose**: Auto-fixes configuration deviations identified by Config Audit; applies fixes to files; validates that fixes work; escalates if uncertain.

**Current Issue**: No automated config enforcement; deviations accumulate; manual fixup required.

### Role & Model Assignment

| Field | Value | Rationale |
|-------|-------|-----------|
| **Role** | Senior Engineer (executor) | Applies fixes; can write code/config; good at handling edge cases |
| **Model** | claude-sonnet-4-6 | Balance of capability and cost; fixes are usually straightforward |
| **Effort** | high | Must verify fixes don't break anything |

### Input Requirements (DELEGATE Block)

```yaml
input:
  source: Config Audit (escalation) or Orchestrator (direct)
  provides:
    - deviations:
        - file: "Makefile"
          remediation: "Add: -include env/.env.$(ENV_NAME)"
          severity: "high"
          confidence: 0.95
    - dry_run: true (validate fixes without applying)
    - auto_approve_below_confidence: 0.8 (only auto-fix if confidence >= this)
```

### Output Requirements (HANDBACK Block)

```yaml
output:
  fixes_applied: 2
  fixes_skipped: 0
  fixes_escalated: 0
  results:
    - file: "Makefile"
      fix: "Added -include env/.env.$(ENV_NAME)"
      status: "APPLIED"
      validation: "Makefile syntax check passed"
    - file: "cdk/main.go"
      fix: "Added os.Getenv(\"DNS_ROOT_DOMAIN\")"
      status: "ESCALATED"
      reason: "Requires code change + test; confidence 0.65 < threshold 0.8"
  git_diff: "... diff output ..."
  validation_results:
    - test: "make lint"
      status: "PASS"
    - test: "make test"
      status: "PASS"
  recommendation: "All applied fixes validated. 1 escalated fix requires human review."
```

### Integration Points

**Invoked From**:
- Config Audit Agent (escalates detected deviations)
- Quality Gate Orchestrator (optional self-healing phase)

**Invokes**:
- Config Audit Agent (re-audit after applying fixes)

### Example DELEGATE Block

```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-05-config-enforce-{service-name}
timestamp: 2026-05-05T09:17:00Z
role: Config Enforcement Agent (Senior Engineer)
model: claude-sonnet-4-6
effort: high
scope: >
  Apply remediation fixes identified by Config Audit. Fix Makefile (add env include) 
  and env file (uncomment DNS_ROOT_DOMAIN). Validate fixes with lint + test. 
  Apply only fixes with confidence >= 0.8. Escalate uncertain fixes for human review.
context:
  - Deviations from Config Audit (just completed)
  - Auto-approval threshold: confidence >= 0.8
  - Service: {service-name}
  - Must pass: make lint, make test
plan:
  1. Receive deviations from Config Audit HANDBACK
  2. For each deviation:
     a. If confidence >= 0.8: apply fix
     b. Else: escalate to human (include reasoning)
  3. After each applied fix, validate (lint/test)
  4. Generate git diff showing all changes
  5. If all changes pass validation, commit (or return diff for human)
  6. Re-run Config Audit to verify full compliance
  7. Return HANDBACK with applied + escalated counts
success_criteria:
  - High-confidence fixes applied automatically
  - Low-confidence fixes escalated with reasoning
  - All applied fixes pass lint + test validation
  - Git diff is clear and reviewable
  - Config Audit re-run shows improved compliance score
  - Escalated fixes documented for human follow-up
---
```

### Example HANDBACK Block

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-05-config-enforce-{service-name}
timestamp: 2026-05-05T09:18:30Z
status: complete
fixes_applied: 1
fixes_skipped: 0
fixes_escalated: 1
results:
  - file: "env/.env.prod"
    fix: "Uncommented DNS_ROOT_DOMAIN=evolutionrollersports.com"
    status: APPLIED
    confidence: 0.95
    validation: "No syntax impact; file is sourced by Makefile"
  - file: "cdk/main.go"
    fix: "Replace hardcoded \"evolutionrollersports.com\" with os.Getenv(\"DNS_ROOT_DOMAIN\")"
    status: ESCALATED
    confidence: 0.65
    reason: "Requires code change + unit test; recommend human review to ensure no edge cases"
git_diff: |
  diff --git a/env/.env.prod b/env/.env.prod
  index abc123..def456 100644
  --- a/env/.env.prod
  +++ b/env/.env.prod
  @@ -2,3 +2,3 @@
   APP_NAME=prod-{service-name}
  -# DNS_ROOT_DOMAIN=evolutionrollersports.com
  +DNS_ROOT_DOMAIN=evolutionrollersports.com
validation_results:
  - test: "shell syntax check on env/.env.prod"
    status: PASS
compliance_score_after: 100
recommendation: "Applied fix validated. Escalated fix requires human review for code safety."
---
```

### Implementation Success Criteria (Week 2 Engineer)

- [ ] Agent receives deviations from Config Audit
- [ ] Agent applies only fixes with confidence >= threshold
- [ ] Agent escalates low-confidence fixes with reasoning
- [ ] Agent validates each applied fix (lint/test)
- [ ] Agent generates clean git diff
- [ ] Agent re-runs Config Audit after fixes
- [ ] Agent documents all escalations for human follow-up
- [ ] Can be invoked in dry-run mode (validate without applying)

### Open Questions for Design Review

1. **Auto-Commit**: Should Config Enforcement auto-commit fixes (with structured message) or return diff for human approval? Recommendation: return diff + offer commit option.
2. **Validation Scope**: Beyond lint/test, should enforcement run make verify (full pipeline)? Recommendation: no (too expensive); lint/test sufficient for config changes.
3. **Rollback Strategy**: If applied fix breaks downstream (e.g., CDK deploy fails), should enforce auto-rollback or escalate? Recommendation: escalate (requires human judgment).

---

## Agent 5: CICD Monitor

**Purpose**: Watches GitHub Actions quality gates; polls with 120s intervals; reports status; escalates on timeout/failure; supports Phase 5.10 critical path.

**Current Issue**: Manual monitoring of GitHub Actions; no structured polling; no audit trail; delays in detecting failures.

### Role & Model Assignment

| Field | Value | Rationale |
|-------|-------|-----------|
| **Role** | Orchestrator (specialized) | Coordinates polling + escalation; lightweight decision-making |
| **Model** | claude-haiku-4-5 | Simple status checks; can run frequently without cost impact |
| **Effort** | medium | Periodic polling; structured reporting |

### Input Requirements (DELEGATE Block)

```yaml
input:
  source: Orchestrator (post-push) or CI system
  provides:
    - repo: "{service-name}"
    - ref: "main" or commit sha
    - workflow_name: "main.yaml"
    - max_wait_minutes: 30
    - poll_interval_seconds: 120
    - escalate_on_timeout: true
    - escalate_on_failure: true
```

### Output Requirements (HANDBACK Block)

```yaml
output:
  status: "SUCCESS" | "FAILURE" | "TIMEOUT" | "PENDING"
  workflow_run_id: "1234567890"
  run_duration_seconds: 245
  conclusion: "success" | "failure" | "timed_out"
  jobs_completed:
    - name: "lint"
      conclusion: "success"
      duration_seconds: 45
    - name: "test"
      conclusion: "success"
      duration_seconds: 78
    - name: "build"
      conclusion: "success"
      duration_seconds: 34
    - name: "deploy-dev"
      conclusion: "success"
      duration_seconds: 88
  jobs_failed:
    - name: "deploy-prod"
      conclusion: "failure"
      failure_log_excerpt: "error: S3 bucket not found"
  escalation_path: null | { agent: "Lead Engineer", reason: "..." }
  poll_count: 15
  poll_interval_seconds: 120
  total_wait_seconds: 1800
  logs_available: true
  recommendation: "Deploy to prod failed; check S3 bucket configuration"
```

### Integration Points

**Invoked From**:
- Orchestrator (after push to main)
- Manual trigger: `make wait-for-ci`

**Timing**: Invoked immediately after push; polls every 120s until completion (max 30 min)

### Example DELEGATE Block

```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-05-cicd-monitor-{service-name}
timestamp: 2026-05-05T10:30:00Z
role: CICD Monitor (Orchestrator)
model: claude-haiku-4-5
effort: medium
scope: >
  Monitor GitHub Actions quality-gate workflow for {service-name} commit abc123def456. 
  Poll every 120 seconds. Report status when complete. Escalate if timeout (>30 min) 
  or failure detected. Provide job-by-job results and failure logs.
context:
  - Repo: {service-name}
  - Commit: abc123def456
  - Workflow: main.yaml (lint → test → build → deploy-dev → deploy-prod)
  - Expected duration: 4-6 minutes typical
  - Poll interval: 120 seconds (conserve API calls)
  - Max wait: 30 minutes (hard timeout)
  - Phase 5.10 depends on successful deploy-prod
plan:
  1. Trigger GitHub Actions API check (get latest run for commit)
  2. Poll every 120s for workflow completion
  3. Track job-by-job status (lint, test, build, deploy-dev, deploy-prod)
  4. On completion:
     a. If success: return HANDBACK with status SUCCESS
     b. If failure: capture failure logs, return HANDBACK with FAILURE + escalation
     c. If timeout: return HANDBACK with TIMEOUT + escalation
  5. Count polls + total wait time in HANDBACK
success_criteria:
  - Workflow completion detected (not timed out)
  - All job results reported (passed or failed)
  - Failure logs captured if failure detected
  - Escalation path set if needed
  - Poll count and wait time accurate
  - Can detect timeout after 30 minutes
---
```

### Example HANDBACK Block

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-05-cicd-monitor-{service-name}
timestamp: 2026-05-05T10:35:15Z
status: complete
workflow_status: FAILURE
workflow_run_id: 5432109876
run_duration_seconds: 302
conclusion: failure
jobs_completed:
  - name: lint
    conclusion: success
    duration_seconds: 42
  - name: test
    conclusion: success
    duration_seconds: 85
  - name: build
    conclusion: success
    duration_seconds: 38
  - name: deploy-dev
    conclusion: success
    duration_seconds: 92
jobs_failed:
  - name: deploy-prod
    conclusion: failure
    failure_log_excerpt: |
      Error: Unable to assume IAM role arn:aws:iam::666109694932:role/prod-{service-name}
      Reason: AccessDenied (MissingPermission for sts:AssumeRole on resource)
escalation_path:
  agent: Lead Engineer
  reason: "Prod deploy IAM permissions issue; requires infra team or manual IAM policy update"
poll_count: 3
poll_interval_seconds: 120
total_wait_seconds: 305
logs_available: true
recommendation: "Deploy-prod failed due to IAM role assumption error. Check AWS account permissions or role trust policy."
---
```

### Implementation Success Criteria (Week 2 Engineer)

- [ ] Agent polls GitHub Actions API every 120s
- [ ] Agent detects workflow completion (success/failure/timeout)
- [ ] Agent captures all job results (passed and failed)
- [ ] Agent extracts failure log excerpts for failed jobs
- [ ] Agent times out after 30 minutes (hard stop)
- [ ] Agent returns HANDBACK with poll count + total wait time
- [ ] Escalation path set for failures and timeouts
- [ ] Can be invoked from `make wait-for-ci` wrapper
- [ ] Handles GitHub API rate limits gracefully

### Open Questions for Design Review

1. **Notification Strategy**: Should CICD Monitor invoke Voice Notify Agent on failure? Or just return escalation path? Recommendation: return escalation path (Voice Notify invoked separately by Orchestrator).
2. **Retry on Failure**: Should monitor support retry (e.g., re-run failed job and re-poll)? Recommendation: no (leave retry to human or GitHub Actions UI).
3. **Log Capture**: How much of failure log to capture? (Current plan: excerpt only, full logs available on GitHub). Recommendation: keep excerpt short (<500 chars) to fit in HANDBACK.

---

## Agent 6: Cleanup

**Purpose**: Archives completed plans; removes temporary files; consolidates documentation; prepares for next phase.

**Current Issue**: No structured cleanup process; plans accumulate; temp files clutter workspace; docs scattered.

### Role & Model Assignment

| Field | Value | Rationale |
|-------|-------|-----------|
| **Role** | Engineer (executor) | File/doc management; straightforward consolidation |
| **Model** | claude-haiku-4-5 | Simple operations; low complexity |
| **Effort** | high | Must validate before deleting; multiple file types |

### Input Requirements (DELEGATE Block)

```yaml
input:
  source: Orchestrator (end-of-phase) or manual trigger
  provides:
    - phase: 5 (archive phase plans)
    - cleanup_scope: "plans" | "temp" | "docs" | "all"
    - dry_run: true (list what would be deleted/archived)
    - consolidation_rules:
        plans: "archive to ~/.claude/plans/archive/"
        temp: "delete matching patterns"
        docs: "consolidate to skills/SKILLS-INDEX.md"
```

### Output Requirements (HANDBACK Block)

```yaml
output:
  cleanup_scope: "all"
  dry_run: false
  plans_archived: 3
  temp_files_deleted: 12
  docs_consolidated: 2
  actions:
    - type: archive
      source: "/home/user/.claude/plans/phase-5-quality-gates.md"
      destination: "/home/user/.claude/plans/archive/phase-5-quality-gates-2026-04-28.md"
      status: success
    - type: delete
      path: "/tmp/{service-name}*.txt"
      count: 12
      status: success
    - type: consolidate
      from: ["skills/PHASE-5.10-MONITORING-PLAN.md", "skills/PHASE-5.10-AGENT-BASED-ORCHESTRATION.md"]
      to: "skills/SKILLS-INDEX.md"
      status: success
  git_status:
    - deleted: "skills/PHASE-5.10-MONITORING-PLAN.md"
    - modified: "skills/SKILLS-INDEX.md"
  disk_freed_mb: 2.3
  recommendation: "Cleanup complete. 3 plans archived, 12 temp files deleted. Ready for Phase 6."
```

### Integration Points

**Invoked From**:
- Orchestrator (end of phase, before Phase 6)
- Manual trigger: `make cleanup`

**Timing**: After validation phase completes; before next phase begins

### Example DELEGATE Block

```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-05-cleanup-phase-5
timestamp: 2026-06-02T17:00:00Z
role: Cleanup Agent (Engineer)
model: claude-haiku-4-5
effort: high
scope: >
  Archive completed Phase 5 plans. Consolidate Phase 5.10 monitoring docs into 
  SKILLS-INDEX.md. Remove temporary files from /tmp/ers-*. Prepare workspace 
  for Phase 6 transition. Validate nothing critical is deleted.
context:
  - Phase: 5 (completed)
  - Plans to archive: ~/.claude/plans/phase-5-*.md
  - Docs to consolidate: skills/PHASE-5.10-MONITORING-PLAN.md, skills/PHASE-5.10-AGENT-BASED-ORCHESTRATION.md
  - Temp file pattern: /tmp/ers-*
  - Consolidation rule: merge docs into SKILLS-INDEX.md
plan:
  1. Dry-run cleanup to list what would be done
  2. Archive Phase 5 plans to ~/.claude/plans/archive/
  3. Delete temp files matching /tmp/ers-*
  4. Consolidate Phase 5.10 docs into SKILLS-INDEX.md
  5. Git diff all changes
  6. Validate no critical files deleted
  7. Return HANDBACK with counts + git status
success_criteria:
  - All Phase 5 plans archived with timestamp in filename
  - All temp files deleted
  - Phase 5.10 docs merged into SKILLS-INDEX.md
  - Git diff shows deliberate, reviewable changes
  - No critical files in deleted list
  - Disk space freed calculation correct
---
```

### Example HANDBACK Block

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-05-cleanup-phase-5
timestamp: 2026-06-02T17:02:30Z
status: complete
cleanup_scope: all
dry_run: false
plans_archived: 3
temp_files_deleted: 12
docs_consolidated: 2
actions:
  - type: archive
    source: ~/.claude/plans/phase-5-quality-gates.md
    destination: ~/.claude/plans/archive/phase-5-quality-gates-2026-06-02.md
    status: success
  - type: archive
    source: ~/.claude/plans/phase-5-remediation.md
    destination: ~/.claude/plans/archive/phase-5-remediation-2026-06-02.md
    status: success
  - type: archive
    source: ~/.claude/plans/phase-5-agent-designs.md
    destination: ~/.claude/plans/archive/phase-5-agent-designs-2026-06-02.md
    status: success
  - type: delete
    pattern: /tmp/ers-*.txt
    count: 12
    total_size_mb: 1.8
    status: success
  - type: consolidate
    from: [skills/PHASE-5.10-MONITORING-PLAN.md, skills/PHASE-5.10-AGENT-BASED-ORCHESTRATION.md]
    to: skills/SKILLS-INDEX.md
    status: success
git_status:
  deleted:
    - skills/PHASE-5.10-MONITORING-PLAN.md
    - skills/PHASE-5.10-AGENT-BASED-ORCHESTRATION.md
  modified:
    - skills/SKILLS-INDEX.md
disk_freed_mb: 2.3
recommendation: "Phase 5 workspace cleaned. Ready for Phase 6. All changes reviewable in git diff."
---
```

### Implementation Success Criteria (Week 2 Engineer)

- [ ] Agent supports dry-run mode (list actions without executing)
- [ ] Agent archives plans with timestamp in filename
- [ ] Agent deletes temp files matching pattern
- [ ] Agent consolidates docs into SKILLS-INDEX.md
- [ ] Agent validates no critical files in delete list
- [ ] Agent generates git-compatible diff
- [ ] Agent returns HANDBACK with counts + disk freed
- [ ] Can be invoked via `make cleanup`

### Open Questions for Design Review

1. **Consolidation Rules**: Should consolidation delete original files or keep them? Recommendation: delete originals (they're superseded).
2. **Archive Strategy**: Should archives be git-committed or kept as workspace files? Recommendation: git-commit (history + auditability).
3. **Scope Customization**: Should cleanup support fine-grained scope (e.g., `cleanup_scope: "plans-only"`)? Recommendation: yes, include.

---

## Agent 7: Voice Notify

**Purpose**: Provides voice/audio notifications for orchestration events (completion, escalation, critical issues); supports different personality voices for different agent types.

**Current Issue**: No structured notification system; status depends on active log monitoring; delays in alerting to issues.

### Role & Model Assignment

| Field | Value | Rationale |
|-------|-------|-----------|
| **Role** | Engineer (lightweight notifier) | Simple voice output; no logic; direct text-to-speech |
| **Model** | claude-haiku-4-5 | Minimal processing; mostly pass-through to TTS |
| **Effort** | low | Stateless; no complex orchestration |

### Input Requirements (DELEGATE Block)

```yaml
input:
  source: Other agents (Quality Orchestrator, Config Audit, CICD Monitor, etc)
  provides:
    - message: "Quality gate passed for {service-name}"
    - notification_type: "success" | "warning" | "escalation" | "progress"
    - agent_type: "Quality Engineer" | "Orchestrator" | "Security" (affects voice personality)
    - urgency: "low" | "medium" | "high" (affects TTS speed/volume)
    - voice_preference: "default" | "optimistic" | "serious" | "technical"
```

### Output Requirements (HANDBACK Block)

```yaml
output:
  message: "Quality gate passed for {service-name}"
  notification_type: "success"
  audio_file: "/tmp/notification-abc123.m4a"
  duration_seconds: 3.2
  agent_voice: "optimistic" (personality matched to agent type)
  urgency_level: "low"
  delivery_method: "stdout" (and optionally: system-tts, file)
  status: "delivered"
  recommendation: "User heard notification; quality gate results ready"
```

### Integration Points

**Invoked From**:
- Quality Gate Orchestrator (on completion)
- Config Audit Agent (on critical findings)
- CICD Monitor (on failure/timeout)
- Any agent needing to alert user (notification type = escalation)

**Timing**: Asynchronous; agent invokes, then proceeds (doesn't wait for voice playback)

### Example DELEGATE Block

```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-05-notify-quality-gate-pass-{service-name}
timestamp: 2026-05-05T09:35:00Z
role: Voice Notify Agent (Engineer)
model: claude-haiku-4-5
effort: low
scope: >
  Deliver voice notification: "Quality gate passed for {service-name}. All checks 
  green. Ready to merge." Use optimistic personality voice. Urgency: low.
context:
  - Agent initiating: Quality Gate Orchestrator
  - Message: "Quality gate passed for {service-name}. All checks green."
  - Voice personality: optimistic (agent is Orchestrator/coordinator)
  - Notification type: success
  - Urgency: low (not time-critical)
plan:
  1. Receive message + voice personality preference
  2. Generate TTS audio (use system TTS or pre-recorded voice)
  3. Play audio via stdout or system audio
  4. Return HANDBACK with delivery status
success_criteria:
  - Audio played successfully
  - Message intelligible
  - Personality voice matched to agent type
  - HANDBACK includes audio duration + delivery method
---
```

### Example HANDBACK Block

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-05-notify-quality-gate-pass-{service-name}
timestamp: 2026-05-05T09:35:03Z
status: complete
message: "Quality gate passed for {service-name}. All checks green."
notification_type: success
audio_file: /tmp/notification-abc123def456.m4a
duration_seconds: 4.1
agent_voice: optimistic
urgency_level: low
delivery_method: system-tts
status: delivered
system_output: |
  [Voice]: "Quality gate passed for {service-name}. All checks green."
  (4.1 second audio playback)
recommendation: "Notification delivered. User can proceed with merge."
---
```

### Implementation Success Criteria (Week 2 Engineer)

- [ ] Agent accepts message + notification_type + urgency
- [ ] Agent matches voice personality to agent type
- [ ] Agent generates TTS audio (using system macOS speak, AWS Polly, or pre-recorded voices)
- [ ] Agent plays audio via system audio or stdout
- [ ] Agent returns HANDBACK with duration + delivery status
- [ ] Can be invoked asynchronously (doesn't block caller)
- [ ] Handles cases where TTS unavailable (graceful degradation to text output)

### Open Questions for Design Review

1. **TTS Service**: Which TTS service? macOS `say` command (simple, works locally)? AWS Polly (cloud, higher quality, costs money)? Pre-recorded voice files? Recommendation: macOS `say` for dev, AWS Polly optional for prod.
2. **Voice Personalities**: How many voice options? Current plan: default, optimistic, serious, technical. Recommendation: start with 3 (optimistic, serious, technical).
3. **Async Handling**: Should Voice Notify block until audio plays or return immediately? Recommendation: return immediately (don't block orchestration).

---

## Integration Dependencies & Data Flow

```
Orchestrator (entry point)
  │
  ├─→ Token Advisor (budget check) → recommends model tier
  │     ↓
  ├─→ Quality Gate Orchestrator (master coordinator)
  │     ├─→ Security Agent (DELEGATE)
  │     ├─→ Testing Agent (DELEGATE)
  │     ├─→ Metrics Agent (DELEGATE)
  │     └─→ Healer Agent (DELEGATE)
  │           ├─→ Config Audit (identify issues)
  │           └─→ Config Enforcement (fix issues)
  │
  ├─→ CICD Monitor (watch GitHub Actions)
  │
  ├─→ Cleanup Agent (end-of-phase archival)
  │
  └─→ Voice Notify (async notifications from any agent)
```

---

## Week 1 Design Completion Checklist

- [x] Agent 1: Quality Gate Orchestrator (complete spec + open questions)
- [x] Agent 2: Token Advisor (complete spec + open questions)
- [x] Agent 3: Config Audit (complete spec + open questions)
- [x] Agent 4: Config Enforcement (complete spec + open questions)
- [x] Agent 5: CICD Monitor (complete spec + open questions)
- [x] Agent 6: Cleanup (complete spec + open questions)
- [x] Agent 7: Voice Notify (complete spec + open questions)
- [x] Integration dependencies documented
- [x] Open questions identified for design review
- [x] All DELEGATE/HANDBACK examples provided
- [x] Implementation success criteria defined for each agent

---

## Open Design Questions for Orchestrator

These questions should be addressed before Week 2 implementation begins:

1. **Fast-Path Optimization**: Should Quality Orchestrator support fast-path skipping unchanged checks? (See Quality Gate Orchestrator, Q1)
2. **Token Budget Escalation**: At what token threshold should Token Advisor escalate to human? (See Token Advisor, Q3)
3. **Config Auto-Fix Approval**: Should Config Enforcement auto-commit fixes or require human approval? (See Config Enforcement, Q1)
4. **CICD Notification**: Should CICD Monitor invoke Voice Notify on failure, or just return escalation path? (See CICD Monitor, Q1)
5. **TTS Service Selection**: macOS `say`, AWS Polly, or pre-recorded voices for Voice Notify? (See Voice Notify, Q1)
6. **Phase Transition Timing**: When should Cleanup Agent run? (End of phase? Before next phase begins?) (See Cleanup, Questions section)

---

## Success Criteria for Week 1 (Principal Engineer Completion)

- [x] All 7 agents have complete design specifications
- [x] No "to be determined" fields (all decisions made)
- [x] Example DELEGATE/HANDBACK blocks provided for each agent
- [x] Integration points documented (clear data flow)
- [x] Open questions identified for clarification
- [x] Document ready for Week 2 engineers to implement

---

## Next Steps (Week 2 Implementation)

Week 2 engineers will receive this design document and implement skill documents for each agent:
- Create `/home/user/git/ers/agentic-engineers/skills/{agent-name}.md` for each
- Full implementation of DELEGATE/HANDBACK protocol
- Integration with existing skills + orchestration scripts
- Testing + validation per success criteria

Week 3: Senior Engineer refactors git hooks + orchestration  
Week 4: QE + Lead validate end-to-end workflow  
Target: 2026-06-02 (Phase 5.10 unblocked)
