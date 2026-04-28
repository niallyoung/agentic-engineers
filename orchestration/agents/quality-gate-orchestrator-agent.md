---
name: Quality Gate Orchestrator Agent Implementation
description: Live orchestrator agent for Phase 5.10 - orchestrates 4 parallel sub-agents, aggregates results, makes PROCEED/ESCALATE decision
type: agent-implementation
phase: 5.10
status: ACTIVE
---

# Quality Gate Orchestrator Agent — LIVE IMPLEMENTATION

**Role**: Orchestrator (Master Coordinator)  
**Model**: claude-sonnet-4-6  
**Effort**: high  
**Input**: DELEGATE block (repo_path, service_name, commit_sha, budget_context)  
**Output**: HANDBACK block (final_decision: PROCEED/ESCALATE, audit_trail, recommendation)  

---

## Agent Invocation Protocol

### How This Agent is Called

```bash
# From git hook, write DELEGATE block to artifacts/
cat > artifacts/2026-MM-DD/DELEGATE-{timestamp}-commit-{service}.yaml <<EOF
---
handoff_type: DELEGATE
task_id: 2026-MM-DD-commit-{service}-{sha}
timestamp: 2026-MM-DDTHH:MM:SSZ
repo_path: {workspace-root}/{service}
service_name: {service}
commit_sha: {full_sha}
budget_context:
  session_pct: 45.0
  trend: stable
  recommended_model: sonnet
EOF

# Git hook waits for HANDBACK to appear in artifacts/
# Orchestrator agent reads DELEGATE, processes, writes HANDBACK
```

### This Agent's Responsibilities

1. **Read DELEGATE block** from artifacts/ directory
2. **Delegate in parallel** to 4 sub-agents:
   - Security Agent (Opus) — credential/permission scanning
   - Testing Agent (Sonnet) — unit/E2E test execution
   - Metrics Agent (Haiku) — health scoring
   - Healing Agent (Sonnet) — auto-fix attempts
3. **Wait for all HANDBACK blocks** (5-min timeout, poll artifacts/)
4. **Aggregate results** into single decision:
   - PROCEED: all pass, health_score >= 85
   - ESCALATE: any fail, severity HIGH+, or timeout
5. **Write HANDBACK block** to artifacts/
6. **Write OpenTelemetry spans** for observability

---

## Agent Logic (Pseudo-Code)

```
WHEN git hook writes DELEGATE block to artifacts/:

  1. DETECT: Monitor artifacts/ for new DELEGATE files
     - Poll every 1 second
     - Match pattern: DELEGATE-{timestamp}-commit-*.yaml
  
  2. READ: Parse DELEGATE block
     - Extract: task_id, repo_path, service_name, commit_sha
     - Store: budget_context (session_pct, trend, recommended_model)
  
  3. TRACE: Generate trace_id (UUID)
     - Create root span: quality-gate-root
     - log: "Starting quality gate for {service_name} at {commit_sha}"
  
  4. DELEGATE TO SUB-AGENTS (parallel):
     
     FOR EACH agent IN [security, testing, metrics, healing]:
       - Create sub-DELEGATE block
       - Write to artifacts/DELEGATE-{timestamp}-{agent}.yaml
       - WAIT: For agent to pick it up and process
       - POLL: artifacts/ for matching HANDBACK-{timestamp}-{agent}.yaml
       - RECEIVE: HANDBACK block from agent
       - STORE: In memory (results[agent])
       - CREATE: OpenTelemetry span from HANDBACK
     
     TIMEOUT: If any agent doesn't return within 5 min → escalate
  
  5. AGGREGATE RESULTS:
     
     aggregate_span = create_span("decision-aggregation")
     
     escalation_reasons = []
     FOR EACH agent, handback IN results:
       - Check: handback["status"] = PASS?
       - Check: handback["severity"] >= HIGH?
       - Add to audit_trail: {agent, status, severity, findings}
       - If status != PASS: append to escalation_reasons
       - If severity >= HIGH: append to escalation_reasons
     
     IF escalation_reasons NOT empty:
       final_decision = "ESCALATE"
       recommendation = "Issues detected: " + join(escalation_reasons)
     ELSE:
       health_score = results["metrics"]["health_score"] // default 85
       IF health_score >= 85:
         final_decision = "PROCEED"
         recommendation = "All checks passed"
       ELSE:
         final_decision = "ESCALATE"
         recommendation = "Health score " + health_score + " below threshold"
     
     aggregate_span.end()
  
  6. CREATE HANDBACK:
     
     HANDBACK = {
       handoff_type: "HANDBACK",
       task_id: {task_id from DELEGATE},
       timestamp: now(),
       status: "complete",
       final_decision: {PROCEED | ESCALATE},
       audit_trail: [
         {agent: "security", status, severity, findings},
         {agent: "testing", status, coverage, failures},
         {agent: "metrics", status, health_score},
         {agent: "healing", status, fixes_applied}
       ],
       recommendation: {human-readable summary},
       attributes: {
         trace_id: {trace_id},
         sub_agents_reporting: 4,
         escalations_count: len(escalation_reasons),
         total_tokens_used: sum of all sub-agent tokens
       }
     }
  
  7. WRITE HANDBACK:
     - Write to artifacts/HANDBACK-{timestamp}-commit-{service}.yaml
     - git hook polls for this file and reads final_decision
  
  8. ASYNC: DELEGATE TO MODEL ENGINEER:
     - Create DELEGATE block for Model Engineer feedback
     - Send: observed tokens, latency, decision quality
     - Store: HANDBACK in artifacts/feedback/model-recommendations.jsonl
     - (Non-blocking, happens after HANDBACK written)

```

---

## Sub-Agent DELEGATE Blocks (Examples)

### For Security Agent
```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-26-commit-{service-name}
timestamp: 2026-05-26T09:00:15Z
role: Security Agent
model: claude-opus-4-7
effort: max
scope: >
  Scan {repo_path} for credential leaks, permission misconfigurations,
  and security violations. Return findings with severity levels.
context:
  repo_path: {workspace-root}/{service-name}
  service_name: {service-name}
  commit_sha: abc123...
  files_changed: [lambda/api/main.go, cdk/stacks/...]
plan:
  1. Grep for credential patterns (API keys, secrets)
  2. Check IAM policy violations
  3. Analyze code for security issues
  4. Return findings with severity
success_criteria:
  - HANDBACK includes: status, severity, findings_count
  - All security checks completed
  - Confidence score provided
```

### For Testing Agent
```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-26-commit-{service-name}
timestamp: 2026-05-26T09:00:18Z
role: Testing Agent
model: claude-sonnet-4-6
effort: high
scope: >
  Run unit and E2E tests for {service_name}. Calculate coverage.
  Report: test counts, failures, coverage %, flaky tests.
context:
  repo_path: {workspace-root}/{service-name}
  service_name: {service-name}
plan:
  1. Run: make test (unit tests)
  2. Parse output: count tests, failures
  3. Calculate coverage from test reports
  4. Identify flaky tests
  5. Return results
success_criteria:
  - HANDBACK includes: unit_tests, coverage, e2e_tests, failures
  - Status = PASS if all tests pass
  - Confidence score >= 0.8
```

### For Metrics Agent
```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-26-commit-{service-name}
timestamp: 2026-05-26T09:00:22Z
role: Metrics Agent
model: claude-haiku-4-5
effort: low
scope: >
  Analyze service health: latency, throughput, error rates, anomalies.
  Return health_score (0-100).
context:
  repo_path: {workspace-root}/{service-name}
  service_name: {service-name}
plan:
  1. Query CloudWatch metrics (if available) or estimate from code
  2. Calculate health_score: latency + throughput + errors
  3. Detect anomalies
  4. Return metrics
success_criteria:
  - HANDBACK includes: health_score, latency, throughput, anomalies
  - Health_score between 0-100
  - Confidence score >= 0.85
```

### For Healing Agent
```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-26-commit-{service-name}
timestamp: 2026-05-26T09:00:25Z
role: Healing Agent
model: claude-sonnet-4-6
effort: high
scope: >
  Attempt auto-fixes for common issues: lint errors, config problems,
  formatting issues. Report: fixes_applied, escalations, confidence.
context:
  repo_path: {workspace-root}/{service-name}
  service_name: {service-name}
  issues_from_security: [finding1, finding2]
  issues_from_testing: [flaky_test]
plan:
  1. For each issue, attempt auto-fix
  2. Run verification (make lint) after fix
  3. Track: success, failure, confidence
  4. Escalate if fix confidence < 0.8
  5. Return results
success_criteria:
  - HANDBACK includes: auto_fixes, escalations, confidence_per_fix
  - Status = PASS if fixes applied successfully
  - Escalations list any fixes that failed
```

---

## HANDBACK Format (What Git Hook Expects)

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-26-commit-{service-name}
timestamp: 2026-05-26T09:04:35Z
status: complete
final_decision: PROCEED  # or ESCALATE
audit_trail:
  - agent: security
    timestamp: 2026-05-26T09:03:45Z
    status: PASS
    severity: INFO
    findings_count: 0
  
  - agent: testing
    timestamp: 2026-05-26T09:04:20Z
    status: PASS
    unit_tests: 45
    coverage_percent: 87.3
    failures: 0
  
  - agent: metrics
    timestamp: 2026-05-26T09:02:00Z
    status: PASS
    health_score: 93
    latency_p99_ms: 248
    anomalies_detected: 0
  
  - agent: healing
    timestamp: 2026-05-26T09:03:15Z
    status: PASS
    auto_fixes: 2
    escalations: 0
    confidence: 0.94

recommendation: "All quality gates passed. Service is healthy. Ready to merge."
attributes:
  trace_id: abc123...
  sub_agents_reporting: 4
  escalations_count: 0
  total_tokens_used: 12450
  total_duration_ms: 275000
```

---

## Integration Points

### Git Hook Polling Logic
```bash
# After invoking make quality-gate, git hook polls for HANDBACK:

timeout=300  # 5 minutes
interval=1   # 1 second

while [ $timeout -gt 0 ]; do
  HANDBACK_FILE="artifacts/2026-MM-DD/HANDBACK-{timestamp}-commit-{service}.yaml"
  
  if [ -f "$HANDBACK_FILE" ]; then
    DECISION=$(grep "final_decision:" "$HANDBACK_FILE" | awk '{print $2}')
    
    if [ "$DECISION" = "PROCEED" ]; then
      echo "✅ Quality gate PROCEED - allowing commit"
      exit 0  # Allow commit
    elif [ "$DECISION" = "ESCALATE" ]; then
      echo "❌ Quality gate ESCALATE - rejecting commit"
      grep "recommendation:" "$HANDBACK_FILE"
      exit 1  # Reject commit
    fi
  fi
  
  sleep $interval
  ((timeout--))
done

echo "❌ Quality gate timeout (5 min) - rejecting commit"
exit 1
```

---

## OpenTelemetry Spans This Agent Produces

```
trace_id: abc123...

├─ quality-gate-root (root span)
│  ├─ start: 09:00:00
│  ├─ end: 09:04:35
│  ├─ attributes: {service_name, commit_sha, trace_id}
│  │
│  ├─ [Parallel] agent-security (delegated)
│  │  └─ [received from artifact]
│  │
│  ├─ [Parallel] agent-testing (delegated)
│  │  └─ [received from artifact]
│  │
│  ├─ [Parallel] agent-metrics (delegated)
│  │  └─ [received from artifact]
│  │
│  ├─ [Parallel] agent-healing (delegated)
│  │  └─ [received from artifact]
│  │
│  ├─ decision-aggregation (sync)
│  │  ├─ start: 09:04:30
│  │  ├─ end: 09:04:32
│  │  ├─ attributes: {final_decision, escalations_count}
│  │  └─ [SPAN written to artifacts/]
│  │
│  └─ model-engineer-feedback (async)
│     └─ [delegated, HANDBACK stored separately]
```

---

## Success Criteria (Phase 5.10)

- [ ] Orchestrator reads DELEGATE blocks from artifacts/
- [ ] Orchestrator delegates to 4 sub-agents in parallel
- [ ] Orchestrator waits for all HANDBACK blocks (5-min timeout)
- [ ] Orchestrator aggregates results correctly
- [ ] HANDBACK block written to artifacts/
- [ ] Git hook reads HANDBACK and makes decision
- [ ] Commits with PROCEED decision proceed
- [ ] Commits with ESCALATE decision are rejected
- [ ] 10+ successful commits through full pipeline
- [ ] OpenTelemetry spans written for all operations
- [ ] Audit trail complete and queryable in artifacts/

---

## Activation Timeline

**Now (Phase 5.10)**: This orchestrator is LIVE.
- Listens for DELEGATE blocks in artifacts/
- Delegates to sub-agents as they're ready
- Writes HANDBACK when all sub-agents report
- Git hooks read HANDBACK and make decisions

**Sub-agents**: Each implemented separately (next documents).

