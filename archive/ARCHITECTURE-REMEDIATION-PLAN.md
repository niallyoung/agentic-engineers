---
name: Architecture Remediation Plan
description: Full 4-week plan to achieve AGENTS.md + DELEGATE/HANDBACK compliance across all workflows
type: implementation-plan
phase: framework-cleanup
created: 2026-04-28
owner: Orchestrator (Haiku)
status: READY_FOR_DELEGATION
---

# Architecture Remediation Plan: AGENTS.md Compliance

## Goal

Refactor all ERS platform + agentic-engineers workflows to use **AGENTS.md routing + DELEGATE/HANDBACK protocol**. No out-of-band scripts in critical paths.

**Outcome**: Clean, auditable, budget-aware agent network. Phase 5.10 Quality Orchestrator built on solid foundation.

---

## Master Plan (4 Weeks)

### Week 1: Framework Design & Planning (5 days)
**Owner**: Principal Engineer (Opus)
**Deliverable**: 7 Agent Spec Designs (no implementation yet)

### Week 2: Agent Implementation (5 days)
**Owner**: Engineers (Sonnet/Haiku)
**Deliverable**: 7 complete agent skill documents with DELEGATE/HANDBACK

### Week 3: Git Hooks + Orchestration Refactoring (5 days)
**Owner**: Senior Engineer (Sonnet)
**Deliverable**: Refactored hooks, updated orchestration scripts

### Week 4: Integration Testing & Validation (5 days)
**Owner**: Quality Engineer (Sonnet) + Lead Engineer (Sonnet)
**Deliverable**: Green end-to-end workflow, audit trails verified

---

## Week 1: Framework Design (Principal Engineer)

### Task 1.1: Design Quality Gate Orchestrator Agent

**Scope**: Master entry point for all quality checks

**DELEGATE Block Template**:
```yaml
---
handoff_type: DELEGATE
task_id: 2026-04-28-design-quality-orchestrator
role: Principal Engineer
model: claude-opus-4-7
effort: high
scope: >
  Design Quality Gate Orchestrator agent that serves as master entry point
  for all quality checks (security, testing, metrics, healing). Include:
  - Entry point (make quality-gate target)
  - Parallel delegation to 4 sub-agents
  - HANDBACK aggregation logic
  - Final PROCEED/ESCALATE decision
  - CloudWatch optional integration
  - No shell scripts in critical path
context:
  - Architecture framework: agentic-engineers/orchestration/AGENTS.md
  - Handoff protocol: agentic-engineers/orchestration/HANDOFF.md
  - Phase 5.10 will use this as master orchestrator
  - Sub-agents: Security (Opus), Testing (Sonnet), Metrics (Sonnet), Healer (Sonnet)
plan:
  1. Review AGENTS.md routing rules
  2. Design Quality Orchestrator role (Orchestrator? Lead? Principal?)
  3. Define parallel delegation strategy
  4. Define HANDBACK aggregation algorithm
  5. Create agent spec template (markdown format)
  6. Include DELEGATE/HANDBACK examples
success_criteria:
  - Agent spec is complete (no shell scripts)
  - DELEGATE/HANDBACK examples provided
  - Sub-agent coordination clear
  - Entry point defined (git hook? Makefile? Direct invocation?)
---
```

### Task 1.2: Design Token Advisor Agent

**Scope**: Budget coordination and model selection

**Key Questions**:
- Role: Model Engineer (Sonnet) or new role?
- Frequency: Pre-delegation? Periodic checkpoints?
- Output: What goes in HANDBACK for Orchestrator to use?

### Task 1.3: Design Config Audit Agent

**Scope**: Configuration compliance verification

**Key Questions**:
- Input: Service path? Full repo scan? Specific checks?
- Output: Deviations + severity + remediation guidance?
- Integration: Part of quality gate or separate?

### Task 1.4: Design Config Enforcement Agent

**Scope**: Auto-fix configuration issues (self-healing)

**Key Questions**:
- When triggered: Always? Only on detected issues?
- Scope: What can be auto-fixed safely?
- Constraints: Need human review before applying fixes?

### Task 1.5: Design CICD Monitor Agent

**Scope**: Build monitoring with 120s sleep intervals

**Key Questions**:
- Role: Orchestrator or Engineer?
- Timeout: How long to monitor (max 30 minutes)?
- Failure handling: Escalate immediately or collect results?

### Task 1.6: Design Cleanup Agent

**Scope**: Plan archival, temp file removal, doc consolidation

**Key Questions**:
- Trigger: Manual? Pre-push hook? End of phase?
- Scope: Plans only? Temp files? Docs? All three?
- Consolidation rules: Where do docs go?

### Task 1.7: Design Voice Notify Agent

**Scope**: Progress notifications and alerts

**Key Questions**:
- Integration point: How does this get called from other agents?
- Personalities: Different voices for different agent types?
- Escalation alerts: How urgent is "urgent"?

### Deliverable (End of Week 1)

**File**: `AGENT-SPECS-WEEK1-DESIGNS.md` (7 agent design documents)

Each includes:
- [ ] Role assignment (from AGENTS.md)
- [ ] Model + effort level
- [ ] Input requirements
- [ ] Output requirements (HANDBACK fields)
- [ ] Integration points
- [ ] Example DELEGATE block
- [ ] Example HANDBACK block
- [ ] Success criteria for implementation

---

## Week 2: Agent Implementation (Engineers)

### Task 2.1-2.7: Implement 7 Agent Skills

**Pattern for each**:

```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-05-implement-[agent-name]-agent
role: Engineer | Senior Engineer
model: claude-sonnet-4-6
effort: high
scope: >
  Implement [Agent Name] agent skill document with full DELEGATE/HANDBACK spec.
  File: agentic-engineers/skills/[agent-name]-agent.md
context:
  - Design from Week 1: AGENT-SPECS-WEEK1-DESIGNS.md
  - Agent role: [Role from AGENTS.md]
  - Model: [Model assigned]
  - Integration point: [How this gets invoked]
plan:
  1. Create skills/[agent-name]-agent.md
  2. Write agent spec (role, model, effort, input, output)
  3. Include DELEGATE block template
  4. Include HANDBACK block template
  5. Document integration with Orchestrator
  6. Add success criteria
success_criteria:
  - Skill file created with complete spec
  - DELEGATE/HANDBACK templates provided
  - Integration points documented
  - No shell scripts in spec
  - Ready for Orchestrator delegation
---
```

**Agents to implement**:
1. Quality Gate Orchestrator (Sonnet, high effort)
2. Token Advisor Agent (Engineer, high effort)
3. Config Audit Agent (Engineer, high effort)
4. Config Enforcement Agent (Senior, high effort) — self-healing complexity
5. CICD Monitor Agent (Engineer, medium effort)
6. Cleanup Agent (Engineer, medium effort)
7. Voice Notify Agent (Engineer, medium effort)

### Deliverable (End of Week 2)

**Files**: 7 new skill documents in `agentic-engineers/skills/`

Each with:
- [ ] Full agent spec (role, model, effort, input, output)
- [ ] Complete DELEGATE block example
- [ ] Complete HANDBACK block example
- [ ] Integration instructions
- [ ] Success criteria

---

## Week 3: Refactoring & Integration (Senior Engineer)

### Task 3.1: Refactor Git Hooks

**Current**: Direct `make lint`, `make test`

**New**: Thin hooks + optional agent delegation

```bash
# pre-commit (new)
#!/bin/bash
# THIN validation only — expensive checks delegated to agents

# Block obvious violations (local, fast)
git diff --cached | grep -E "AKIA|private_key|aws_secret" && exit 1

# For lint+test: Orchestrator will handle via Quality Gate Agent
# (requires Claude session, implicit for now during local dev)
# When in CI: DELEGATE to Quality Gate Orchestrator
```

**Why**: Keep local dev fast, but CICD uses full agent workflow

### Task 3.2: Refactor Orchestration Scripts

**Current**: Token tracking via shell scripts

**New**: Token Advisor Agent delegation

```bash
# Example: Orchestrator pre-delegation
# OLD: bash skills/usage-tracking/scripts/usage-tracking.sh analyze --json
# NEW: DELEGATE to Token Advisor Agent (returns HANDBACK with budget info)
```

### Task 3.3: Update AUTOMATIC-INVOCATION.md

**Current**: Documents shell script calls

**New**: Documents agent delegation

Example:
```
Session Start (T+0):
  Orchestrator DELEGATEs to Token Advisor Agent
    Input: None
    Output: HANDBACK with session_usage_pct, trend, recommended_model
    
Pre-Delegation Check:
  Orchestrator DELEGATEs to Token Advisor Agent
    Input: Task scope
    Output: HANDBACK with model recommendation + budget context
    
Periodic Checkpoints:
  Token Advisor Agent returns HANDBACK every 30 min with:
    - Current usage %
    - Trend (rising/stable/falling)
    - Velocity (tokens/hour)
    - Recommended next model
```

### Deliverable (End of Week 3)

**Files Modified**:
- [ ] `{workspace-name}/githooks/pre-commit` (thin validation)
- [ ] `{workspace-name}/githooks/pre-push` (thin validation)
- [ ] Orchestration scripts → Token Advisor Agent delegation
- [ ] `AUTOMATIC-INVOCATION.md` (updated with agent workflow)

---

## Week 4: Integration Testing & Validation (QE + Lead)

### Test Matrix

| Workflow | Test | Expected Result |
|----------|------|-----------------|
| Local dev: edit → commit | pre-commit hook thin validation | PASS (fast, local only) |
| Local dev: commit → push | pre-push hook thin validation | PASS (fast, local only) |
| CICD: push → build | Quality Gate Agent delegation | PASS (security + tests green) |
| CICD: build → deploy | Token Advisor coordination | PASS (budget tracked, model optimal) |
| End-to-end: edit → deploy | All 7 agents + Quality Orchestrator | PASS (audit trail complete) |

### Validation Checklist

- [ ] **DELEGATE blocks present** for all agent invocations
- [ ] **HANDBACK blocks returned** with audit trail
- [ ] **Budget tracking visible** in each HANDBACK
- [ ] **Model selection documented** in DELEGATE/HANDBACK
- [ ] **No shell scripts** in critical paths (only tools)
- [ ] **AGENTS.md routing respected** (no direct role bypassing)
- [ ] **Audit trail machine-readable** (JSON/YAML in HANDBACK)
- [ ] **Integration points clear** (who calls whom, when)
- [ ] **Error handling via escalation** (not silent failures)
- [ ] **All 7 agents tested** in isolation + integration

### Deliverable (End of Week 4)

**File**: `ARCHITECTURE-REMEDIATION-COMPLETION-REPORT.md`

Including:
- [ ] Test results (pass/fail)
- [ ] Audit trail samples
- [ ] Budget tracking verification
- [ ] Agent coordination verified
- [ ] No shell scripts in critical paths
- [ ] AGENTS.md compliance: 100%
- [ ] Ready for Phase 5.10? YES

---

## Risk Mitigation

### Risk 1: Agents Don't Coordinate Properly

**Mitigation**: 
- Week 1: Pair Principal Engineer with 2 Engineers for design review
- Week 2: Integration tests early (sub-agents talking to Orchestrator)
- Week 3: Staging environment for full workflow test

### Risk 2: Performance Degradation

**Mitigation**:
- Measure baseline (current shell script speed)
- Profile agent network (DELEGATE/HANDBACK overhead)
- Optimize token usage in agents
- Keep local dev thin (no agent invocation, only CICD)

### Risk 3: Budget Tracking Breaks

**Mitigation**:
- Token Advisor Agent has comprehensive test suite
- Verify token estimates accurate
- Compare old vs new budget tracking

### Risk 4: Audit Trail Incomplete

**Mitigation**:
- Every HANDBACK must include full audit fields
- Schema validation (HANDBACK matches expected format)
- Sample audit trails from real runs

---

## Success Criteria (End of Remediation)

- [x] **Architecture audit completed** (60% non-compliant identified)
- [ ] **7 agent specs designed** (Week 1)
- [ ] **7 agents implemented** (Week 2)
- [ ] **Git hooks refactored** (Week 3)
- [ ] **Orchestration refactored** (Week 3)
- [ ] **All workflows tested** (Week 4)
- [ ] **100% AGENTS.md compliant** (verified)
- [ ] **All audit trails machine-readable** (verified)
- [ ] **No shell scripts in critical paths** (verified)
- [ ] **Budget tracking accurate** (verified)
- [ ] **Ready for Phase 5.10** (YES)

---

## Phase 5.10 Readiness

**After Remediation Complete**:

Quality Orchestrator Agent will:
- ✅ Route to Security Engineer via DELEGATE
- ✅ Route to Lead Engineer via DELEGATE
- ✅ Route to Model Engineer via DELEGATE
- ✅ Route to Healer Engineer via DELEGATE
- ✅ Aggregate HANDBACK results
- ✅ Make final PROCEED/ESCALATE decision
- ✅ Publish audit trail
- ✅ Track budget and model optimization
- ✅ No shell scripts, no implicit orchestration
- ✅ Full audit trail for continuous improvement

---

## Orchestrator Delegation

This plan is ready for **Orchestrator to delegate to Engineers**.

```yaml
---
handoff_type: DELEGATE
task_id: 2026-04-28-architecture-remediation
role: [See individual tasks above]
model: [Varies by task]
effort: [Varies by task]
scope: >
  Full 4-week architecture remediation to achieve AGENTS.md compliance.
  Use this plan as master roadmap. Each week has specific deliverables
  and success criteria. All work via DELEGATE/HANDBACK protocol.
plan:
  Week 1: Principal Engineer designs 7 agent specs (no implementation)
  Week 2: Engineers implement 7 agent skills (DELEGATE/HANDBACK specs)
  Week 3: Senior Engineer refactors git hooks + orchestration
  Week 4: QE + Lead validate end-to-end workflow
success_criteria:
  - 100% AGENTS.md compliant (verified)
  - 0% shell scripts in critical paths
  - All audit trails machine-readable
  - Phase 5.10 ready to proceed
---
```

Orchestrator will track progress via weekly HANDBACK from team leads.

---

## Files Created

- [x] `ARCHITECTURE-AUDIT.md` (findings, violations, compliance checklist)
- [x] `ARCHITECTURE-REMEDIATION-PLAN.md` (this file, master plan)
- [ ] `AGENT-SPECS-WEEK1-DESIGNS.md` (Week 1 deliverable)
- [ ] `ARCHITECTURE-REMEDIATION-COMPLETION-REPORT.md` (Week 4 deliverable)
- [ ] 7 agent skill documents (Week 2 deliverables)
- [ ] Updated git hooks (Week 3 deliverable)
- [ ] Updated AUTOMATIC-INVOCATION.md (Week 3 deliverable)

---

## Timeline

```
2026-04-28: Planning (this document)
2026-05-05: Week 1 starts (Principal Engineer designs)
2026-05-12: Week 2 starts (Engineers implement)
2026-05-19: Week 3 starts (Senior refactors)
2026-05-26: Week 4 starts (QE validates)
2026-06-02: Phase 5.10 ready to proceed
```

---

## Open Questions for Orchestrator

1. **Should local dev use agent delegation?** (No — too slow. Only CICD.)
2. **Voice Notify integration point?** (All agents use it? Or just Orchestrator?)
3. **Config Enforcement scope?** (Only low-risk fixes? Or full repairs?)
4. **CICD Monitor timeout?** (Max 30 min? Or follow build timeout?)
5. **Budget tracking frequency?** (Periodic checkpoints every 30 min? Or on-demand?)

---

## Next Step

✅ Plan complete. Ready for **Orchestrator to delegate Week 1 design task to Principal Engineer**.
