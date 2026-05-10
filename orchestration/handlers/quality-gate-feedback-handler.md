---
name: Quality Gate Orchestrator Feedback Handler
description: Aggregates HANDBACK blocks from 5 sub-agents into single decision (Security, Testing, Metrics, Healing, Spec Engineer)
type: handler
phase: 6
status: IMPLEMENTATION_READY
---

# Quality Gate Orchestrator Feedback Handler

**Purpose**: Receive HANDBACK blocks from 5 parallel sub-agents, aggregate results, make PROCEED/ESCALATE decision. Sub-agents: Security, Testing, Metrics, Healing, Spec Engineer.

---

## Handler Logic

```
WHEN Quality Gate Orchestrator has delegated to 5 sub-agents:

INPUT:
  - task_id: "2026-MM-DD-commit-{service}-{sha}"
  - HANDBACK blocks location: artifacts/2026-MM-DD/HANDBACK-{timestamp}-*-{task_id}.yaml

PROCESS:
  
  1. POLL artifacts/ for HANDBACK blocks matching task_id
     For each sub-agent (security, testing, metrics, healing, spec-engineer):
       - Look for: HANDBACK-*-{service}-{task_id}.yaml
       - Timeout: 5 minutes per agent (escalate if exceeded)
       - Mark received when HANDBACK file found
  
  2. READ all 4 HANDBACK blocks
     Security HANDBACK: {status, severity, findings_count, confidence}
     Testing HANDBACK: {status, unit_tests, coverage, failures, flaky}
     Metrics HANDBACK: {status, health_score, latency_p99, anomalies}
     Healing HANDBACK: {status, fixes_attempted, fixes_succeeded, escalations}
  
  3. AGGREGATE results with priority order:
     Priority 1: Security (ANY HIGH/CRITICAL severity → ESCALATE)
     Priority 2: Testing (ANY failures → investigate)
     Priority 3: Healing (escalations → review fixes)
     Priority 4: Metrics (health_score < 85 → flag but non-blocking)
  
  4. DECISION LOGIC:
     
     IF security.severity >= HIGH:
       decision = ESCALATE
       reason = f"Security: {security.findings_count} findings, severity {security.severity}"
     
     ELIF testing.unit_test_failures > 0 OR testing.e2e_test_failures > 0:
       decision = ESCALATE
       reason = f"Testing: {testing.unit_test_failures} unit failures, {testing.e2e_test_failures} E2E failures"
     
     ELIF testing.coverage_percent < 60:
       decision = ESCALATE
       reason = f"Testing: Coverage {testing.coverage_percent}% below threshold (60%)"
     
     ELIF healing.escalations > 0 AND healing.fixes_succeeded < healing.fixes_attempted:
       decision = ESCALATE
       reason = f"Healing: {healing.escalations} fixes escalated (low confidence)"
     
     ELIF metrics.health_score < 70:
       decision = ESCALATE
       reason = f"Metrics: Health score {metrics.health_score} below threshold (70)"
     
     ELIF (testing.status == PASS AND 
           metrics.health_score >= 85 AND 
           healing.fixes_succeeded == healing.fixes_attempted):
       decision = PROCEED
       reason = "All checks passed, health good, no low-confidence fixes"
     
     ELSE:
       decision = ESCALATE
       reason = "Combined assessment indicates human review needed"
  
  5. BUILD audit_trail (chronological list of sub-agent results)
     audit_trail = [
       {agent: "security", status: ..., timestamp: ..., summary: "..."},
       {agent: "testing", status: ..., timestamp: ..., summary: "..."},
       {agent: "metrics", status: ..., timestamp: ..., summary: "..."},
       {agent: "healing", status: ..., timestamp: ..., summary: "..."}
     ]
  
  6. BUILD recommendation (human-readable summary)
     recommendation = f"""
     Quality Gate Summary:
     
     Security: {security.findings_count} findings
       - Severity: {security.severity}
       - Confidence: {security.confidence}
     
     Testing: {testing.unit_tests} unit tests, {testing.e2e_tests} E2E tests
       - Coverage: {testing.coverage_percent}%
       - Failures: {testing.unit_test_failures} unit, {testing.e2e_test_failures} E2E
     
     Metrics: Health Score {metrics.health_score}/100
       - P99 Latency: {metrics.latency_p99}ms
       - Anomalies: {metrics.anomalies_count}
     
     Healing: {healing.fixes_succeeded}/{healing.fixes_attempted} fixes applied
       - Auto-fixes: {healing.fixes_succeeded} succeeded, {healing.fixes_attempted - healing.fixes_succeeded} failed
       - Escalations: {healing.escalations}
     
     Decision: {decision}
     Rationale: {reason}
     """

OUTPUT:
  
  HANDBACK = {
    handoff_type: HANDBACK,
    task_id: {task_id},
    timestamp: {iso8601_now},
    status: COMPLETE,
    final_decision: PROCEED | ESCALATE,
    audit_trail: [...],
    recommendation: "...",
    attributes: {
      trace_id: {parent_trace_id},
      sub_agents_reporting: 4,
      escalations_count: {count of escalation reasons},
      total_tokens_used: {sum of all sub-agent tokens},
      aggregation_duration_ms: {time to aggregate}
    }
  }
  
  Write to: artifacts/2026-MM-DD/HANDBACK-{timestamp}-orchestrator-{task_id}.yaml
  
  7. ASYNC: Create Model Engineer DELEGATE
     (See model-engineer-feedback-handler.md)
     Pass: orchestrator_handback, observed_tokens_per_agent, latency
  
  8. WRITE OpenTelemetry span
     - span_name: "decision-aggregation"
     - parent_span_id: {quality-gate-root}
     - attributes: final_decision, escalations_count, total_tokens_used
     - events: [{name: "aggregation_complete", timestamp, attributes: {decision}}]

TIMEOUT HANDLING:
  If any sub-agent HANDBACK not received after 5 minutes:
    - escalate = true
    - reason = f"Timeout waiting for {missing_agents} HANDBACK"
    - decision = ESCALATE
    - audit_trail includes "TIMEOUT" entries for missing agents
```

---

## Example: HANDBACK Aggregation

**Input: 4 Sub-Agent HANDBACK blocks**

```yaml
# Security Agent HANDBACK
status: PASS
severity: LOW
findings_count: 2
confidence: 0.95

# Testing Agent HANDBACK
status: PASS
unit_tests: 45
unit_test_failures: 0
e2e_tests: 12
e2e_test_failures: 0
coverage_percent: 87.3
flaky_tests: 0
confidence: 0.95

# Metrics Agent HANDBACK
status: PASS
health_score: 89
latency_p99: 120
anomalies_count: 0
confidence: 0.88

# Healing Agent HANDBACK
status: PASS
fixes_attempted: 3
fixes_succeeded: 3
escalations: 0
confidence: 0.92
```

**Output: Orchestrator HANDBACK**

```yaml
handoff_type: HANDBACK
task_id: 2026-05-26-commit-{example-service}-abc123
timestamp: 2026-05-26T09:04:35Z
status: COMPLETE
final_decision: PROCEED
audit_trail:
  - agent: security
    status: PASS
    timestamp: 2026-05-26T09:02:15Z
    summary: "2 findings (LOW severity), 0 credentials detected"
  - agent: testing
    status: PASS
    timestamp: 2026-05-26T09:04:20Z
    summary: "45 unit tests, 12 E2E tests, 87.3% coverage, 0 failures"
  - agent: metrics
    status: PASS
    timestamp: 2026-05-26T09:02:45Z
    summary: "Health 89/100, P99 120ms, 0 anomalies"
  - agent: healing
    status: PASS
    timestamp: 2026-05-26T09:03:50Z
    summary: "3/3 fixes succeeded, 0 escalations"
recommendation: |
  Quality Gate Summary:
  
  Security: 2 findings (LOW severity), confidence 0.95
  Testing: 45 unit + 12 E2E tests passing, coverage 87.3%, confidence 0.95
  Metrics: Health 89/100, P99 latency 120ms, confidence 0.88
  Healing: 3/3 auto-fixes succeeded, confidence 0.92
  
  Decision: PROCEED
  All quality gates passed. Ready for deployment.
attributes:
  trace_id: abc-123-trace-456
  sub_agents_reporting: 4
  escalations_count: 0
  total_tokens_used: 12165
  aggregation_duration_ms: 35
  decision_confidence: 0.93
```

---

## Integration with Git Hook

**Pre-commit hook flow**:

```bash
# After DELEGATE is written, hook polls for orchestrator HANDBACK
while [ $elapsed -lt 300 ]; do
  if [ -f "artifacts/2026-MM-DD/HANDBACK-*-orchestrator-{task_id}.yaml" ]; then
    # Read final_decision from HANDBACK
    decision=$(grep "final_decision:" HANDBACK | cut -d' ' -f2)
    
    if [ "$decision" = "PROCEED" ]; then
      exit 0  # Allow commit
    else
      # Print escalation details
      cat HANDBACK
      exit 1  # Reject commit
    fi
  fi
  sleep 5
  elapsed=$((elapsed + 5))
done

# Timeout
echo "Quality gate timeout (5 min)"
exit 1
```

---

## Error Handling

| Scenario | Action | Reason |
|----------|--------|--------|
| Security timeout (>5min) | ESCALATE, "Security agent timeout" | Can't guarantee security review |
| Testing timeout (>5min) | ESCALATE, "Testing agent timeout" | Can't guarantee test execution |
| Healing escalates all fixes | ESCALATE, list escalated fixes | Low confidence in auto-fixes |
| Sub-agent crash (invalid YAML) | ESCALATE, "Invalid response from {agent}" | Can't trust malformed data |
| No HANDBACK at all (5min) | ESCALATE, "All agents timeout" | Complete failure |

---

## Success Criteria (Phase 6 Testing)

- ✅ Correctly aggregates 4 HANDBACK blocks
- ✅ Decision logic produces PROCEED when all agents pass
- ✅ Decision logic produces ESCALATE on any security issue
- ✅ Timeout handling escalates after 5 minutes
- ✅ Audit trail accurate and complete
- ✅ OpenTelemetry span written with correct attributes
- ✅ Git hook reads final_decision and allows/rejects commit
- ✅ 50+ runs with 0% false positives/negatives
