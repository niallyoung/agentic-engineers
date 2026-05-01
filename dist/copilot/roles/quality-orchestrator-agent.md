---
name: Quality Orchestrator Agent
description: Master quality coordinator - delegates to testing, security, healing, metrics agents. Aggregates results and makes quality gate decision.
type: agent-implementation
phase: 5.10
status: ACTIVE
---

# Quality Orchestrator — Quality & Testing Coordinator

**Role**: Orchestrator (Quality Master)  
**Model**: claude-sonnet-4-6  
**Effort**: high  
**Input**: DELEGATE block (repo_path, service_name, commit_sha, context)  
**Output**: HANDBACK block (final_decision: PROCEED/ESCALATE, audit_trail, recommendations)  

---

## Responsibilities

Master orchestrator that coordinates all quality checks:
1. **Testing** — Unit/E2E tests, coverage analysis
2. **Healing** — Auto-fix issues found by other agents
3. **Security** — Credential/vulnerability scanning  
4. **Metrics** — System health scoring

**Final Decision**: PROCEED (all pass) or ESCALATE (any fail / health < threshold)

---

## Agent Invocation Protocol

```bash
# Task arrives with quality context
DELEGATE block contains:
  - task_id: unique identifier
  - repo_path: service location
  - service_name: which ERS service
  - commit_sha: what code to test
  - context: files changed, requirements
```

---

## Agent Logic

```
WHEN Quality Orchestrator receives DELEGATE:

1. READ: DELEGATE block
   - Extract: repo_path, service_name, commit_sha
   - Store: task context

2. DELEGATE TO SUB-AGENTS (parallel):
   
   Spawn 4 parallel tasks:
   
   a) Testing Agent (Haiku)
      - Run: make test
      - Measure: coverage, failures, flaky tests
      - Report: PASS/FAIL with severity
   
   b) Healing Agent (Sonnet)
      - Receive: issues from other agents
      - Attempt: auto-fixes (lint, config, tests)
      - Report: fixes_applied, fixes_failed, confidence
   
   c) Security Agent (Opus)
      - Scan: credentials, dependencies, vulnerabilities
      - Report: findings with severity levels
   
   d) Metrics Agent (Haiku)
      - Calculate: system health score
      - Check: latency, error rates, resource usage
      - Report: health_score (0-100), status

3. WAIT: For all sub-agents to return HANDBACK
   - Timeout: 5 minutes
   - If timeout: mark as escalation

4. AGGREGATE RESULTS:
   
   escalation_reasons = []
   for each agent_result:
     - Check: status == PASS?
     - Check: severity >= HIGH?
     - If not pass: add to escalation_reasons
   
   health_score = metrics_agent_health_score
   
   if escalation_reasons:
     final_decision = "ESCALATE"
     reasons = escalation_reasons
   elif health_score < 85:
     final_decision = "ESCALATE"
     reasons = ["Health score " + health_score + " below 85"]
   else:
     final_decision = "PROCEED"
     reasons = []

5. CREATE HANDBACK:
   
   HANDBACK = {
     task_id: ...,
     timestamp: now(),
     status: "complete",
     final_decision: PROCEED | ESCALATE,
     audit_trail: {
       testing: {status, coverage, failures},
       healing: {fixes_attempted, fixes_succeeded, escalations},
       security: {findings_count, severity_levels},
       metrics: {health_score, p99_latency, error_rate}
     },
     recommendation: "human-readable summary",
     escalation_reasons: reasons (if any)
   }

6. WRITE HANDBACK:
   - Write to artifacts/HANDBACK-{timestamp}.yaml
   - Caller polls for this file

7. DELEGATE TO MODEL ENGINEER (async, non-blocking):
   - Send: token usage, latency, decision quality
   - Receive feedback: confidence adjustments
```

---

## Sub-Agent Delegation Details

### Testing Agent
- **Model**: Haiku (mechanical test parsing)
- **Task**: Run tests, measure coverage, report failures
- **Output**: test counts, coverage %, flaky tests, status

### Healing Agent  
- **Model**: Sonnet (can reason about fixes)
- **Task**: Attempt auto-fixes for issues found
- **Output**: fixes_applied, fixes_succeeded, escalations, confidence

### Security Agent
- **Model**: Opus (maximum reasoning for security)
- **Task**: Scan for credentials, vulns, misconfigurations
- **Output**: findings, severity levels, compliance status

### Metrics Agent
- **Model**: Haiku (structured health scoring)
- **Task**: Calculate system health score
- **Output**: health_score, latency, error_rate, resource usage

---

## Decision Matrix

| Testing | Healing | Security | Metrics (≥85) | Decision |
|---------|---------|----------|---------------|----------|
| ✅ PASS | ✅ OK   | ✅ PASS  | ✅ yes        | PROCEED  |
| ❌ FAIL | ✅ OK   | ✅ PASS  | ✅ yes        | ESCALATE |
| ✅ PASS | ❌ FAIL | ✅ PASS  | ✅ yes        | ESCALATE |
| ✅ PASS | ✅ OK   | ❌ FAIL  | ✅ yes        | ESCALATE |
| ✅ PASS | ✅ OK   | ✅ PASS  | ❌ no (<85)   | ESCALATE |

**ANY failure or health < 85 → ESCALATE**

---

## HANDBACK Example

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-26-quality-{service-name}
timestamp: 2026-05-26T09:05:00Z
status: complete
final_decision: PROCEED
audit_trail:
  testing:
    status: PASS
    unit_tests: 45
    unit_failures: 0
    coverage: 87.3%
  healing:
    status: PASS
    fixes_attempted: 2
    fixes_succeeded: 2
    escalations: []
  security:
    status: PASS
    findings: 0
    severity_max: NONE
  metrics:
    status: PASS
    health_score: 92
    p99_latency_ms: 245
    error_rate: 0.1%
recommendation: All quality gates passed. Ready to proceed.
escalation_reasons: []
```

---

## When This Agent is Triggered

- **After Engineer executes work** — Quality check before merge
- **Pre-deployment** — Full quality gate before shipping
- **On-demand** — Manual quality check requested
- **From CI/CD hooks** — Automated quality validation

---

## Protocol

**Input**: DELEGATE (task_id, repo_path, service_name, commit_sha)  
**Output**: HANDBACK (final_decision, audit_trail, escalation_reasons)  
**Sub-agents**: Testing, Healing, Security, Metrics (parallel, 5-min timeout)  
**Decision**: PROCEED (all pass) or ESCALATE (any fail)
