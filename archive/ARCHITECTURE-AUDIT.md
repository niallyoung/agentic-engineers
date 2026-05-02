---
name: Agentic Engineers Architecture Audit
description: Comprehensive review of all workflows to ensure AGENTS.md + DELEGATE/HANDBACK compliance
type: audit
created: 2026-04-28
status: FINDINGS DOCUMENTED
---

# Architecture Audit: AGENTS.md + DELEGATE/HANDBACK Compliance

## Executive Summary

**CRITICAL FINDING**: Multiple workflows bypass AGENTS.md and DELEGATE/HANDBACK protocol, using out-of-band shell scripts instead.

**Current State**: ~40% agent-compliant, 60% non-compliant (scripts + implicit orchestration)

**Risk**: Phase 5.10 mistake almost repeated — shell scripts masquerading as orchestration layer

**Solution**: Standardize ALL workflows to use AGENTS.md routing + DELEGATE/HANDBACK protocol

---

## Audit Findings

### ❌ Non-Compliant: Git Hooks (Local Quality Gates)

**Files**: `/home/user/git/ers/{service-name}/githooks/pre-commit`, `pre-push`, `commit-msg`

**Current**: Shell scripts that directly run `make lint`, `make test`, `make app.e2e`

**Issue**: 
- Implicit orchestration (no DELEGATE/HANDBACK)
- No budget awareness
- No model selection optimization
- No audit trail
- No escalation path to agents

**Current Workflow**:
```
Developer runs: git commit
  ↓ (implicit)
  → pre-commit hook (bash)
    → make lint
    → make test
  ↓
  → Succeeds or fails locally
```

**Correct Workflow** (should be):
```
Developer runs: git commit
  ↓ (thin validation)
  → pre-commit hook (bash)
    → Quick syntax check only (no expensive ops)
    → DELEGATE to Quality Engineer agent for lint+test
  ↓
Quality Engineer Agent:
  → DELEGATE to Engineer for lint execution
  → DELEGATE to Engineer for test execution
  → HANDBACK results
  ↓
  → Commit proceeds or fails with audit trail
```

---

### ❌ Non-Compliant: Token Usage Monitoring

**Files**: 
- `orchestration/AUTOMATIC-INVOCATION.md` (describes shell script invocation)
- `skills/usage-tracking/scripts/capture_token_usage.sh`
- `skills/usage-tracking/scripts/usage-tracking.sh`
- `orchestration/scripts/usage-budget.sh`

**Current**: Scripts called directly by Orchestrator (implicit)

**Issue**:
- No DELEGATE block (script invocation is implicit)
- Budget decisions made outside agent network
- Model selection not visible in HANDBACK
- No structured audit trail

**Current Workflow**:
```
Orchestrator needs budget info:
  ↓ (implicit)
  → bash skills/usage-tracking/scripts/usage-tracking.sh analyze --json
  ↓
  → Decides model tier (Haiku vs Sonnet vs Opus)
  ↓
  → Creates DELEGATE with budget_context field
```

**Correct Workflow** (should be):
```
Orchestrator needs budget info:
  ↓ (DELEGATE)
  → Token Advisor Agent (defined role)
     receives: DELEGATE with budget_analysis task
     executes: token usage analysis
     returns: HANDBACK with:
       - session_pct
       - trend
       - velocity
       - recommended_model
       - budget_status
  ↓
Orchestrator receives HANDBACK:
  → Uses model recommendation in next DELEGATE
  → Audit trail captures all decisions
```

---

### ❌ Non-Compliant: Quality Control Scripts

**Files**:
- `agentic-engineers/skills/quality-gate-orchestration.sh` (just deprecated)
- `agentic-engineers/skills/setup-cloudwatch-monitoring.sh` (tool script, not agent)
- `agentic-engineers/skills/cicd-monitoring.md` (documents shell patterns, not agents)
- `agentic-engineers/skills/cleanup.md` (marked delegable, but no agent spec)

**Issue**: Skills documented with bash code, not agent DELEGATE/HANDBACK specs

**Current Workflow**:
```
Developer needs cleanup:
  → Skill document says: "bash cleanup.sh"
  → Unclear who should execute
  → No DELEGATE/HANDBACK
  → No audit trail
```

**Correct Workflow**:
```
Developer needs cleanup:
  ↓ (DELEGATE)
  → Cleanup Agent (defined in skills)
     receives: DELEGATE with cleanup task
     executes: per-phase cleanup
     returns: HANDBACK with artifact counts + consolidations
  ↓
  → Audit trail: what was cleaned, what consolidated, what deleted
```

---

### ❌ Non-Compliant: CICD Monitoring

**File**: `agentic-engineers/skills/cicd-monitoring.md`

**Current**: Documents 120-second sleep patterns + shell monitoring loops

**Issue**: 
- Describes how to monitor builds, not agent architecture
- Could be delegated to CICD Monitor Agent
- Currently implicit (developer runs monitor, not DELEGATE)

**Correct Workflow** (should be):
```
Orchestrator needs CICD monitoring:
  ↓ (DELEGATE)
  → CICD Monitor Agent (defined role)
     receives: DELEGATE with service list, build job info
     monitors: with 120s sleep intervals
     returns: HANDBACK when all green or failure detected
  ↓
  → Result: PROCEED or ESCALATE to human
```

---

### ❌ Non-Compliant: Configuration Audit & Enforcement

**Files**:
- `agentic-engineers/skills/config-standard.md` (defines standard, good)
- `agentic-engineers/skills/config-audit.md` (audit patterns, needs agent spec)
- `agentic-engineers/skills/config-enforcement.md` (fix patterns, needs agent spec)

**Issue**: Skills describe what to do, not agent DELEGATE/HANDBACK

**Should be**: Config Audit Agent, Config Enforcement Agent with DELEGATE/HANDBACK specs

---

### ⚠️ Semi-Compliant: Plan Iteration & Engineering Execution

**Files**:
- `agentic-engineers/skills/plan-iterate.md` (workflow defined, agents implied)
- `agentic-engineers/skills/engineer-execution.md` (workflow defined, agents implied)
- `agentic-engineers/skills/implementation-workflow.md` (workflow defined, agents implied)

**Status**: Workflow architectures are correct, but need explicit DELEGATE/HANDBACK examples

**Improvement Needed**: Add concrete DELEGATE/HANDBACK templates to each

---

### ✅ Compliant: Agent Role Definitions

**Files**:
- `agentic-engineers/orchestration/AGENTS.md` (correct)
- `agentic-engineers/orchestration/HANDOFF.md` (correct)

**Status**: Framework is sound. All other components must conform to it.

---

## Architecture Principles That Were Violated

1. **All Work Through Agents**: ❌ Shell scripts bypass agents
2. **Explicit Handoffs**: ❌ Implicit invocations (no DELEGATE blocks)
3. **Audit Trail**: ❌ No HANDBACK blocks = no audit trail
4. **Model Optimization**: ❌ Budget decisions outside agent network
5. **AGENTS.md Routing**: ❌ Scripts don't use routing rules
6. **Testability**: ❌ Each component in isolation is hard to verify

---

## Compliance Checklist

### For Each Skill / Workflow Component

- [ ] **Has agent spec** (not just bash code)
- [ ] **Uses DELEGATE block** (if receives work)
- [ ] **Uses HANDBACK block** (if returns results)
- [ ] **Follows AGENTS.md role** (Orchestrator, Engineer, Lead, Principal, Security, Quality, Model)
- [ ] **Includes model assignment** (claude-haiku-4-5, claude-sonnet-4-6, etc.)
- [ ] **Includes effort level** (low, medium, high, max)
- [ ] **Has success criteria** (in DELEGATE)
- [ ] **Has audit trail** (via HANDBACK)
- [ ] **Integrates with budget tracking** (Token Advisor agent or equivalent)

---

## Remediation: Refactor All Workflows to Agent-Based

### Phase A: Define Missing Agent Roles

**New Agent Specs to Create**:

1. **Quality Gate Orchestrator** ← Quality control entry point
   - Role: Orchestrator (Haiku, low effort routing)
   - Delegates to: Security, Testing, Metrics, Healer agents
   - Returns: PROCEED / ESCALATE decision

2. **Token Advisor Agent** ← Budget intelligence
   - Role: Model Engineer (Sonnet)
   - Input: None (reads usage history)
   - Output: HANDBACK with usage%, trend, recommended_model
   - Used by: Orchestrator pre-delegation

3. **Config Audit Agent** ← Configuration compliance
   - Role: Lead Engineer (Sonnet)
   - Input: Service path, audit scope
   - Output: HANDBACK with deviations, severity, remediation
   - Used by: Quality Orchestrator

4. **Config Enforcement Agent** ← Configuration fixes
   - Role: Engineer (Sonnet)
   - Input: Config deviations to fix
   - Output: HANDBACK with fixes applied, tests passing
   - Used by: Quality Orchestrator (self-healing loop)

5. **CICD Monitor Agent** ← Build monitoring
   - Role: Orchestrator or Model Engineer
   - Input: Services to monitor, timeout
   - Output: HANDBACK when all green or failure
   - Used by: Orchestrator (during deployment waits)

6. **Cleanup Agent** ← Artifact cleanup
   - Role: Engineer (Haiku)
   - Input: Cleanup scope (plans, temps, docs)
   - Output: HANDBACK with artifacts removed, consolidations done
   - Used by: Pre-push quality gate

7. **Voice Notify Agent** ← Notification delivery
   - Role: Orchestrator (Haiku)
   - Input: Message, personality, urgency
   - Output: HANDBACK with delivery status
   - Used by: All agents for progress updates

### Phase B: Refactor Git Hooks

**Current**: Direct `make` invocation

**New**: Thin git hooks + DELEGATE to agents

```bash
# pre-commit (new)
#!/bin/bash
# THIN validation only
git diff --cached | grep -E "AKIA|private_key|aws_secret" && exit 1

# For lint+test: DELEGATE to Quality Orchestrator agent
# (requires Claude Code session, so stays as implicit for local dev)
# 
# DELEGATE to Quality Orchestrator:
#   - task: lint and test current repo
#   - model: Sonnet (high effort)
#   - scope: full lint + unit test, no E2E
```

---

### Phase C: Refactor Token Tracking

**Current**: Direct script invocation in Orchestrator

**New**: Token Advisor Agent with DELEGATE/HANDBACK

```yaml
# Orchestrator creates DELEGATE:
---
handoff_type: DELEGATE
task_id: 2026-04-28-token-advisor-check
role: Model Engineer
model: claude-sonnet-4-6
effort: medium
scope: Analyze session token usage; return budget status + model recommendation
context:
  - Session started: 2026-04-28T09:00:00Z
  - Reset in: ~7.8 hours
---

# Model Engineer Agent returns HANDBACK:
---
handoff_type: HANDBACK
task_id: 2026-04-28-token-advisor-check
status: complete
deliverables:
  - Token usage analysis
metrics:
  - session_usage_pct: 45.2
  - trend: rising (+3.1%/hour)
  - hours_until_reset: 7.5
  - velocity_acceleration: normal
  - recommended_model: "sonnet"
  - recommended_effort: "high"
  - budget_status: GREEN
---
```

Orchestrator then uses this in next DELEGATE.

---

## Implementation Sequence

### Week 1: Framework Compliance (No Code Yet)
- [ ] Document all 7 missing agent specs
- [ ] Create agent spec templates
- [ ] Define DELEGATE/HANDBACK examples for each
- [ ] Approve with team

### Week 2: Implement Phase A (New Agents)
- [ ] Quality Gate Orchestrator agent skill
- [ ] Token Advisor agent skill
- [ ] Config Audit agent skill
- [ ] Config Enforcement agent skill
- [ ] CICD Monitor agent skill
- [ ] Cleanup agent skill
- [ ] Voice Notify agent skill

### Week 3: Implement Phase B (Git Hook Refactoring)
- [ ] Update pre-commit hook (thin validation + implicit DELEGATE)
- [ ] Update pre-push hook (thin validation + implicit DELEGATE)
- [ ] Test with local development workflow

### Week 4: Integration Testing
- [ ] Run full workflow: dev edit → commit → push → CICD → deployment
- [ ] Verify all DELEGATE/HANDBACK blocks logged
- [ ] Verify audit trail complete
- [ ] Verify budget tracking accurate
- [ ] Verify model selection optimized

---

## Success Criteria

- [x] All workflows documented (this audit)
- [ ] All 7 agent specs created (with DELEGATE/HANDBACK)
- [ ] All git hooks compliant
- [ ] All quality controls use agents
- [ ] All token tracking via agents
- [ ] All budget decisions visible in HANDBACK
- [ ] All audit trails machine-readable
- [ ] No out-of-band scripts in critical paths
- [ ] AGENTS.md unchanged (framework layer)

---

## Glossary

- **Agent**: Role-based executor (Orchestrator, Engineer, Lead, Principal, Security, Quality, Model)
- **DELEGATE**: Work assignment from Orchestrator to Agent
- **HANDBACK**: Results return from Agent to Orchestrator
- **Agent Spec**: Skill document with DELEGATE/HANDBACK templates
- **Implicit Invocation**: Direct script call (non-compliant)
- **Explicit Invocation**: DELEGATE block (compliant)
- **Out-of-Band**: Workflow bypasses agent network (non-compliant)

---

## Next Steps

1. **Approve audit findings** ← You are here
2. **Create all 7 agent specs** with DELEGATE/HANDBACK templates
3. **Refactor git hooks** to be thin + delegate
4. **Refactor orchestration scripts** to use Token Advisor agent
5. **Test full workflow** end-to-end
6. **Document guardrails** to prevent future architecture drift

Once complete: **All ERS platform workflows + agentic-engineers will be agent-based**. No more shells scripts in critical paths. All work flows through AGENTS.md + DELEGATE/HANDBACK.
