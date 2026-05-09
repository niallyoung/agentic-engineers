---
name: Phase 5.10 - Agent-Based Quality Orchestration (Corrected Architecture)
description: Quality gate monitoring via agent network, not shell scripts
type: implementation-plan
phase: 5.10
status: REPLANNING
created: 2026-04-28
notes: CRITICAL ARCHITECTURE CORRECTION - shell scripts removed, agent-based workflow adopted
---

# Phase 5.10: Agent-Based Quality Orchestration

## Critical Architecture Correction

**WRONG APPROACH** (previous plan):
- quality-gate-orchestration.sh (monolithic shell script)
- Out-of-band metric collection
- No proper handoff protocol
- AGENTS.md stays untouched (correct)

**CORRECT APPROACH** (this plan):
- Quality Orchestrator (Haiku, Orchestrator role) routes work
- Sub-agents handle specific quality checks via DELEGATE/HANDBACK
- Each quality metric → separate agent delegation
- Security scans → Security Engineer
- Healer analysis → dedicated agent
- Metrics aggregation → Model Engineer
- AGENTS.md unchanged (enforced)

---

## Agent Roles & Handoffs (Phase 5.10)

### Quality Orchestrator (Haiku, Orchestrator Role)
**Responsibilities**:
- Entry point for quality gate checks
- Routes to appropriate sub-agents (Security Engineer, Lead Engineer, Model Engineer, etc.)
- Collects audit metrics and creates CloudWatch entries
- Aggregates quality gate decisions
- Makes final PROCEED/ESCALATE decision

**Does NOT**:
- Execute tests or security scans directly
- Analyze audit logs
- Calculate metrics
- Fix issues

**Workflow**:
```
Quality Orchestrator receives: service_path, deployment_target, skip_e2e
  1. DELEGATE to Security Engineer (security scans)
  2. DELEGATE to Lead Engineer (test orchestration)
  3. DELEGATE to Model Engineer (audit analysis + metrics)
  4. DELEGATE to Healer Engineer (diagnostic + healing)
  5. Aggregate all HANDBACK results
  6. Publish audit trail to CloudWatch
  7. Make final decision: PROCEED or ESCALATE
```

### Security Engineer (Opus, delegated by Orchestrator)
**Task**: Execute security scans (dependencies, secrets, semantic analysis)

**DELEGATE Input**:
- Service path
- Deployment target (dev/prod)
- Scan scope (full or differential)

**HANDBACK Output**:
- Security findings (HIGH/MEDIUM/LOW severity)
- Confidence scores
- Remediation guidance
- Gate decision: PASS, WARN, FAIL

### Lead Engineer (Sonnet, delegated by Orchestrator)
**Task**: Orchestrate testing (unit, integration, E2E)

**DELEGATE Input**:
- Service path
- Test filter (optional)
- Skip E2E flag

**HANDBACK Output**:
- Test results (PASS/FAIL counts)
- Coverage metrics
- Failure details
- Gate decision: PASS, WARN, FAIL

### Model Engineer (Sonnet, delegated by Orchestrator)
**Task**: Analyze audit logs and calculate metrics for Level 3 readiness

**DELEGATE Input**:
- Audit log path(s) for past N days
- Deployment target
- Focus: healer success rate, escalation rate, confidence calibration

**HANDBACK Output**:
- Healer success rate (%)
- Auto-merge rate (%)
- Escalation rate (%)
- Confidence calibration error (%)
- Level 3 readiness: YES/NO/PENDING_DATA
- Trends (24h, 7d, 30d)

### Healer Engineer (Sonnet, delegated by Orchestrator)
**Task**: Diagnostic analysis and optional auto-fixing (if confidence HIGH + risk LOW)

**DELEGATE Input**:
- Failed quality gate results
- Issue type and severity
- Suggested fix (from diagnostic engine)

**HANDBACK Output**:
- Diagnosis: root cause + confidence + risk level
- Action taken: auto-fixed or escalated
- PR created (if applicable)
- Next gate re-validation result

---

## Audit Trail & Metrics (Cloud-Native, No Shell Scripts)

### CloudWatch Logs Integration

**Log Entry Format** (JSON, pushed by each agent):
```json
{
  "timestamp": "2026-04-28T15:21:00Z",
  "session_id": "abc123def456",
  "service": "{service-name}",
  "deployment_target": "prod",
  "phase": "security",
  "agent_role": "SecurityEngineer",
  "status": "PASS",
  "findings": {
    "high_severity": 0,
    "medium_severity": 1,
    "low_severity": 3
  },
  "gate_decision": "PASS"
}
```

**CloudWatch Logs Group**: `/ers/quality-gates/agent-orchestration`
**Log Streams**: `{service}-{environment}` (e.g., `{service-name}`)

### CloudWatch Metrics (Pushed by Quality Orchestrator)

**Namespace**: `ERS/QualityGates`

**Metrics Published**:
- `ExecutionTimeSeconds` (dimension: Service, DeploymentTarget)
- `QualityGatePass` (count by service)
- `QualityGateFail` (count by service)
- `SecurityFindingsCount` (dimension: Severity)
- `HealerInvoked` (count)
- `HealerSuccess` (count)
- `HealerEscalated` (count)

---

## Implementation: 5 Agents for Phase 5.10

### Agent 1: Quality Orchestrator
**File**: `agentic-engineers/skills/quality-orchestrator-agent.md`
**Role**: Orchestrator (Haiku, low effort routing + high effort for execution)
**Entry Point**: `quality-gate` Makefile target
**Workflow**:
1. Parse inputs (service_path, deployment_target, skip_e2e)
2. Create DELEGATE blocks for each sub-agent
3. Collect HANDBACK results
4. Aggregate metrics
5. Publish to CloudWatch (optional, graceful degradation)
6. Emit final decision

### Agent 2: Security Verification Sub-Agent
**File**: `agentic-engineers/skills/quality-security-agent.md`
**Role**: Security Engineer (Opus)
**Receives**: DELEGATE from Quality Orchestrator
**Executes**: `go vuln`, `npm audit`, secret detection, semantic scanning
**Returns**: HANDBACK with findings + confidence scores
**Escalates**: HIGH severity findings block deployment

### Agent 3: Testing Orchestration Sub-Agent
**File**: `agentic-engineers/skills/quality-testing-agent.md`
**Role**: Lead Engineer (Sonnet)
**Receives**: DELEGATE from Quality Orchestrator
**Executes**: Unit tests, integration tests, E2E tests (if skip_e2e=false)
**Returns**: HANDBACK with results + coverage
**Escalates**: Test failures for diagnostic analysis

### Agent 4: Audit Analysis Sub-Agent
**File**: `agentic-engineers/skills/quality-metrics-agent.md`
**Role**: Model Engineer (Sonnet)
**Receives**: DELEGATE from Quality Orchestrator
**Executes**: Analyze audit logs, calculate Level 3 metrics
**Returns**: HANDBACK with success rates, readiness assessment
**Uses**: `healer-metrics-analyzer.py` (local tool)

### Agent 5: Healer Diagnostic Sub-Agent
**File**: `agentic-engineers/skills/quality-healer-agent.md`
**Role**: Healer Engineer (Sonnet) OR escalates to Lead/Principal
**Receives**: DELEGATE from Quality Orchestrator (if issues found)
**Executes**: Root cause analysis, confidence assessment, auto-fix (if qualified)
**Returns**: HANDBACK with diagnosis + action taken (fix or escalate)

---

## Audit Trail Collection (No .jsonl Files, All via Agents)

### Per-Check Logging

**Security Agent logs**:
```yaml
handoff_type: HANDBACK
task_id: 2026-04-28-security-check-{service-name}
status: complete
deliverables:
  - Security scan results
findings:
  - type: "deprecated_dependency"
    severity: "MEDIUM"
    package: "golang.org/x/text v0.9.0"
    fix_version: "v0.15.0"
tests:
  - Command: "go list -json -m all | go vuln"
    Result: "PASS (3 medium issues, 0 critical)"
gate_decision: "WARN"
```

**Testing Agent logs**:
```yaml
handoff_type: HANDBACK
task_id: 2026-04-28-testing-check-{service-name}
status: complete
deliverables:
  - Test results
tests:
  - Command: "make test"
    Result: "PASS (247 tests)"
    Coverage: "84%"
gate_decision: "PASS"
```

### Metrics Collection

**Quality Orchestrator aggregates HANDBACK results and creates CloudWatch entries** (optional if AWS CLI available):

```bash
aws logs put-log-events \
  --log-group-name /ers/quality-gates/agent-orchestration \
  --log-stream-name {service-name} \
  --log-events "timestamp=$(date +%s000),message={handback_json}"
```

**All handoff blocks are stored locally in audit directory** (git-ignored, for local analysis):
```
quality-audit-{SESSION_ID}/
├── 2026-04-28-15-21-00-security-{service-name}.jsonl
├── 2026-04-28-15-22-00-testing-{service-name}.jsonl
├── 2026-04-28-15-23-00-metrics-{service-name}.jsonl
└── 2026-04-28-15-24-00-healer-{service-name}.jsonl
```

---

## Why This Is Better Than Shell Scripts

| Aspect | Shell Script (Old) | Agent-Based (New) |
|--------|-------------------|-------------------|
| **Orchestration** | Monolithic shell logic | Clear agent roles via AGENTS.md |
| **Handoffs** | Implicit (hard to audit) | Explicit DELEGATE/HANDBACK protocol |
| **Metrics Collection** | CloudWatch + local logs (duplicate) | Metrics in HANDBACK blocks, CloudWatch optional |
| **Parallelization** | Sequential bash loops | True parallel delegation (all agents start simultaneously) |
| **Extensibility** | Add more shell functions (complexity) | Add new agent role (AGENTS.md routing handles it) |
| **Testability** | Test bash script locally | Test each agent in isolation (unit-like testing) |
| **Compliance** | Quality gates == shell script behavior | Quality gates == agent network (matches AGENTS.md architecture) |
| **Cost Optimization** | Manual (hardcoded) | Automatic (Model Engineer recommends routing) |
| **Audit Trail** | Shell output + CloudWatch | Structured HANDBACK blocks (machine-readable) |

---

## Implementation Sequence

### Week of April 28, 2026 (This Week)
- [ ] Create `quality-orchestrator-agent.md` (Orchestrator role definition)
- [ ] Create 5 sub-agent skill documents
- [ ] Remove `quality-gate-orchestration.sh` from active use (keep for reference)
- [ ] Update Makefile: `quality-gate` target → invokes Orchestrator agent
- [ ] First integration test: Quality Orchestrator → sub-agents → results

### Week of May 5, 2026
- [ ] Deploy agent-based quality gates to dev environment
- [ ] Verify HANDBACK protocol working correctly
- [ ] Test CloudWatch integration (optional)
- [ ] Collect first batch of audit trail metrics

### Weeks of May 12-26, 2026
- [ ] Continue collecting Healer outcomes
- [ ] Run metrics analysis (via Model Engineer agent)
- [ ] Calibrate confidence scores based on outcomes
- [ ] Weekly team reviews of quality gate effectiveness

### Week of May 26, 2026
- [ ] Assess Level 3 readiness (Model Engineer provides summary)
- [ ] Team discussion + sign-off
- [ ] Proceed to Phase 5.11 (Level 3 rollout with agents)

---

## Success Criteria (Phase 5.10 Complete)

- [x] Audit trail centralized (HANDBACK blocks + local storage)
- [x] Quality Orchestrator defined (routes to sub-agents)
- [x] 5 sub-agent skills defined (security, testing, metrics, healer, escalation)
- [x] DELEGATE/HANDBACK protocol for all handoffs
- [ ] All 5 agents tested and integrated
- [ ] Quality gates operational via agents (not shell scripts)
- [ ] 2-3 weeks of empirical data collected (end of May)
- [ ] Level 3 readiness assessment via Model Engineer
- [ ] AGENTS.md unchanged (no modifications)

---

## What Stays the Same

- **AGENTS.md**: Untouched. Our agents FOLLOW its routing rules, don't modify it.
- **healer-metrics-analyzer.py**: Still used by Model Engineer agent for analysis.
- **cloudwatch-queries.md**: Still valid for historical analysis.
- **Quality gate decisions**: PROCEED/WARN/BLOCK/ESCALATE unchanged.
- **Level 3 criteria**: 5 metrics, same thresholds.

---

## What Changes

- **Orchestration mechanism**: Shell script → Agent network
- **Handoff protocol**: Implicit → Explicit (DELEGATE/HANDBACK)
- **Agent coordination**: Sequential bash loops → Parallel delegations
- **Audit trail format**: Local .jsonl → Structured HANDBACK blocks + optional CloudWatch
- **Entry point**: `make quality-gate` → Quality Orchestrator agent receives task

---

## Files to Create (Not Modify)

New skill files (all follow AGENTS.md routing):
- `quality-orchestrator-agent.md` — Master orchestrator agent definition
- `quality-security-agent.md` — Security Engineer delegation
- `quality-testing-agent.md` — Lead Engineer delegation
- `quality-metrics-agent.md` — Model Engineer delegation
- `quality-healer-agent.md` — Healer Engineer delegation

Remove from active use (keep for reference):
- `quality-gate-orchestration.sh` → archived or deprecated
- `setup-cloudwatch-monitoring.sh` → superseded by agent metrics

---

## Next Steps (Immediate)

1. **Agree on architecture**: Confirm agent-based approach is correct
2. **Define Quality Orchestrator**: Full agent specification with entry point logic
3. **Define 5 sub-agents**: Each with DELEGATE/HANDBACK templates
4. **Integration plan**: How Makefile `quality-gate` invokes Orchestrator
5. **Testing strategy**: Verify each agent → HANDBACK → aggregation flow

---

## Relationship to AGENTS.md

**AGENTS.md is the unchanging routing framework.**

Our Phase 5.10 agents:
- ✅ Use AGENTS.md routing rules (Quality Orchestrator = Haiku Orchestrator)
- ✅ Delegate to roles defined in AGENTS.md (Security Engineer, Lead, etc.)
- ✅ Follow HANDOFF.md protocol for all inter-agent communication
- ✅ Never modify AGENTS.md itself
- ✅ Respect cost targets and effort levels from AGENTS.md

---

## Open Questions for Review

1. **Makefile integration**: Should `make quality-gate` invoke a shell wrapper that launches Orchestrator agent, or direct agent invocation?
2. **CloudWatch optional**: Should cloud metrics be tier-2 (try, don't fail), or skip entirely with local HANDBACK blocks sufficient?
3. **Healer auto-fix scope**: Should Healer agent be able to auto-commit fixes, or just create PRs for Lead Engineer review?
4. **Parallel execution**: Can Quality Orchestrator delegate all 5 sub-agents in parallel (security + testing + metrics + healer), or sequentially?

**Recommendation**: Parallel delegation for speed, with Quality Orchestrator waiting for all HANDBACK results before aggregating.
