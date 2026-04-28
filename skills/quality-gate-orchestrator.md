# Quality Gate Orchestrator Skill

**Agent Role**: Orchestrator (specialized coordinator)  
**Model**: claude-sonnet-4-6  
**Effort**: high  
**Purpose**: Master entry point for all quality checks; coordinates 4 parallel sub-agents; aggregates results; makes PROCEED/ESCALATE decision

---

## Overview

Quality Gate Orchestrator serves as the master quality gate for all services. It receives a quality check request, delegates in parallel to Security Check, Testing, Metrics Analysis, and Healing agents, aggregates all results with audit trail, and returns a final PROCEED or ESCALATE decision. This is the foundation for Phase 5.10 Quality Orchestration.

---

## DELEGATE Block Specification

### Input Fields

```yaml
repo_path: "/home/user/git/ers/{service-name}"
  # Required. Path to service directory

service_name: "{service-name}"
  # Required. Service identifier

commit_sha: "abc123def456" (optional)
  # For CI/CD integration

force_full_checks: false (optional)
  # Skip fast-path, run all checks

budget_context:
  session_pct: 45.0
  trend: "stable"
  recommended_model: "sonnet"
```

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
  Execute full quality gate for {service-name}. Delegate to Security, Testing,
  Metrics, and Healing agents in parallel. Aggregate results. Return PROCEED
  or ESCALATE decision with audit trail.
context:
  - Service: {service-name} (Go/Lambda)
  - Budget: 45.0% session available
  - Phase 5.10 depends on this being bulletproof
plan:
  1. Read budget context
  2. DELEGATE to Security Agent (async)
  3. DELEGATE to Testing Agent (async)
  4. DELEGATE to Metrics Agent (async)
  5. DELEGATE to Healing Agent (async)
  6. Wait for all 4 HANDBACK blocks (timeout 5 min)
  7. Aggregate into final decision
  8. Return HANDBACK with audit_trail
success_criteria:
  - All 4 sub-agents complete successfully
  - Final decision is PROCEED or ESCALATE
  - Audit trail includes all sub-checks
  - Total execution < 300 seconds
---
```

---

## HANDBACK Block Specification

### Output Fields

```yaml
final_decision: "PROCEED" | "ESCALATE"
  # Final decision on whether code is ready

checks_passed:
  security:
    status: "PASS" | "WARN" | "FAIL"
    severity: "low" | "medium" | "high"
  testing:
    status: "PASS" | "FAIL"
    coverage: 87.3
  metrics:
    status: "PASS" | "WARN"
    health_score: 92
  healing:
    status: "PASS" | "ESCALATED"
    auto_fixed: 3
    escalated: 1

escalation_path: null | {agent: "...", reason: "..."}
  # Who to escalate to and why

audit_trail:
  - timestamp: "2026-05-05T09:00:15Z"
    agent: "Security Agent"
    result: "PASS - no credentials"

total_duration_seconds: 145

cloudwatch_logged: true | false

recommendation: "string"
  # Human-readable summary
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
  testing:
    status: PASS
    unit_tests: "145 passed"
    coverage: 87.3
  metrics:
    status: PASS
    health_score: 93
  healing:
    status: PASS
    auto_fixed: 2
    escalated: 0
audit_trail:
  - timestamp: 2026-05-05T09:00:15Z
    agent: Security Agent
    result: "PASS - 0 credentials, 0 violations"
  - timestamp: 2026-05-05T09:01:30Z
    agent: Testing Agent
    result: "PASS - 145 unit, 23 e2e, 87.3% coverage"
  - timestamp: 2026-05-05T09:02:45Z
    agent: Metrics Agent
    result: "PASS - health 93"
  - timestamp: 2026-05-05T09:03:20Z
    agent: Healer Agent
    result: "PASS - fixed 2 linting issues"
total_duration_seconds: 270
cloudwatch_logged: true
escalation_path: null
recommendation: "Healthy service; auto-fixes applied; ready to merge"
---
```

---

## Implementation Approach

### Parallel Delegation Algorithm

```
DELEGATE Security Agent {
  repo_path, service_name, commit_sha
}
DELEGATE Testing Agent {
  repo_path, service_name, commit_sha
}
DELEGATE Metrics Agent {
  repo_path, service_name, commit_sha
}
DELEGATE Healing Agent {
  repo_path, service_name, commit_sha, budget_context
}

WAIT_FOR_ALL(5 minute timeout)

IF ANY timeout:
  escalation_path = {agent: "Lead Engineer", reason: "Sub-agent timeout"}
  final_decision = "ESCALATE"
  return HANDBACK

FOR EACH HANDBACK:
  audit_trail.push({timestamp, agent, result})

# Decision logic:
IF ANY.status = "FAIL" OR ANY.security.severity = "high":
  final_decision = "ESCALATE"
ELSE IF ANY.status = "WARN":
  final_decision = "PROCEED" (with warning)
ELSE:
  final_decision = "PROCEED"
```

### Sub-Agent Specifications

Each sub-agent receives same repo_path + service_name and returns HANDBACK with:

| Agent | Input | Output |
|-------|-------|--------|
| **Security** | repo_path, service_name | status, credential_scans, violations, severity |
| **Testing** | repo_path, service_name | status, unit_tests, e2e_tests, coverage |
| **Metrics** | repo_path, service_name | status, health_score, latency_p95, trend |
| **Healing** | repo_path, service_name, budget_context | status, auto_fixed, escalated |

### Aggregation Logic

```
final_decision_algorithm:
  
IF healing.status = "ESCALATED":
  escalation_path = {agent: "Lead Engineer", reason: "Healer escalated"}
  decision = "ESCALATE"
  
ELIF security.severity IN ["high", "critical"]:
  escalation_path = {agent: "Security Engineer", reason: security.reason}
  decision = "ESCALATE"
  
ELIF testing.status = "FAIL":
  escalation_path = {agent: "Lead Engineer", reason: "Tests failing"}
  decision = "ESCALATE"
  
ELIF metrics.status = "FAIL":
  escalation_path = {agent: "Lead Engineer", reason: "Health metrics below threshold"}
  decision = "ESCALATE"
  
ELSE:
  decision = "PROCEED"
```

---

## Integration Points

### Invoked From

- `make quality-gate` target (thin wrapper)
- GitHub Actions pre-merge workflow
- Manual developer trigger (local verification)

### Invokes (Sub-Agents)

1. **Security Agent**: DELEGATE for credential + compliance scanning
2. **Testing Agent**: DELEGATE for unit + e2e testing + coverage
3. **Metrics Agent**: DELEGATE for health scoring + trend analysis
4. **Healing Agent**: DELEGATE for auto-fixing + issue identification

### DELEGATE/HANDBACK Signatures

```go
// To sub-agents:
type QualityCheckDelegate struct {
  RepoPath         string
  ServiceName      string
  CommitSHA        string  // optional
  BudgetContext    BudgetInfo
}

// From sub-agents:
type QualityCheckHandback struct {
  Status         string // PASS, WARN, FAIL
  Result         string // detailed result
  Severity       string // low, medium, high (security only)
  Duration       int    // seconds
  Timestamp      time.Time
}
```

---

## Timeout & Error Handling

### Sub-Agent Timeout

```
IF sub-agent doesn't respond within 5 min:
  - Log warning: "Sub-agent timeout: {agent_name}"
  - Include in audit_trail as "TIMEOUT"
  - Set escalation_path to Lead Engineer
  - final_decision = "ESCALATE"
  - Return HANDBACK with timeout noted
```

### Parallel Execution Safety

```
- All 4 sub-agents run in parallel (not sequential)
- Orchestrator waits for all to complete or timeout
- No sub-agent is blocking; failures don't prevent others from running
- Audit trail captures all results (passes + failures)
```

---

## Testing Strategy

### Unit Tests (with Mocked Sub-Agents)

```bash
# Test 1: All sub-agents pass
MOCK: All 4 return status=PASS
EXPECTED: final_decision=PROCEED, escalation_path=null

# Test 2: Security finds violation
MOCK: Security returns severity=high
EXPECTED: final_decision=ESCALATE, escalation_path=Security Engineer

# Test 3: Testing fails
MOCK: Testing returns status=FAIL
EXPECTED: final_decision=ESCALATE, escalation_path=Lead Engineer

# Test 4: Sub-agent timeout
MOCK: Metrics Agent times out after 300s
EXPECTED: final_decision=ESCALATE, audit_trail notes timeout

# Test 5: Parallel execution
MOCK: All 4 sub-agents respond within 2-3s each
EXPECTED: total_duration < 5s (parallel, not sequential)
```

---

## Success Criteria Validation

- [x] All 4 sub-agents delegated in parallel
- [x] Waits for all HANDBACK blocks (5 min timeout)
- [x] Final decision is PROCEED or ESCALATE (no ambiguous states)
- [x] Audit trail includes all sub-check results
- [x] Total execution < 300 seconds (5 min)
- [x] CloudWatch logging works (if ENABLE_CLOUDWATCH=true)
- [x] Can be invoked from `make quality-gate`
- [x] Can be invoked from GitHub Actions
- [x] Ready for Phase 5.10 integration

---

## Related Skills

- **Security Agent**: Credential + compliance scanning
- **Testing Agent**: Unit + e2e testing
- **Metrics Agent**: Health scoring + trends
- **Healing Agent**: Auto-fixing + escalations
- **Token Advisor**: Budget awareness for delegations
- **CICD Monitor**: Build monitoring (separate track)
- **Voice Notify**: Audio notifications on completion

---

## Revision History

| Date | Status | Notes |
|------|--------|-------|
| 2026-04-28 | DESIGN | Specification created |
| 2026-05-05 | IMPLEMENTATION | Skill document created |

