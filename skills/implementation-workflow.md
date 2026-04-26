---
name: Implementation Workflow (Plan → Execute → Review → Iterate)
description: End-to-end workflow combining plan iteration, task execution, and final reviews
type: skill
delegable_to: [Orchestrator]
relates_to: [plan-iterate.md, engineer-execution.md]
---

# Implementation Workflow: Plan → Execute → Review → Finalize

Complete end-to-end workflow for converting an approved plan into implemented, reviewed, finalized work.

## Workflow Phases

```
Phase 0: Plan Iteration (approx. 3-4 hours)
  Orchestrator drafts plan → Senior Engineer review → Principal Engineer review → Security Engineer review
  Output: Fully vetted plan with all recommendations integrated

Phase 1: Task Execution (variable, depends on plan scope)
  Orchestrator assigns tasks from approved plan → Engineer executes → Escalates if needed
  Output: Completed work, committed to git

Phase 2: Final Review (approx. 1-2 hours)
  Senior Engineer reviews implementation → Principal Engineer reviews if needed
  Output: Sign-off that implementation matches plan intent

Phase 3: Security Review (if necessary only)
  Security Engineer spot-checks implementation for threat mitigation
  Output: Security sign-off or required mitigations

Phase 4: Plan Finalization
  Orchestrator integrates reviews → Updates TODO.md → Marks plan complete
  Output: Archived plan + lessons learned
```

## Phase 0: Plan Iteration (Draft → Final)

### Entry Criteria
- Plan drafted in TODO.md (or similar)
- Plan has clear phases, tasks, success criteria
- Owner and timeline identified

### Workflow

1. **Senior Engineer Review** (Sonnet 4.6 — feasibility)
   - Input: Draft plan
   - Focus: Can this be executed as written? Are tasks sized right? Known unknowns?
   - Output: REVIEW-SENIOR-*.md with 6 concrete recommendations
   - Time: 30-45 min

2. **Principal Engineer Review** (Opus 4.7 — strategy)
   - Input: Draft plan + Senior feedback
   - Focus: Is this strategically right? Long-term implications? MVP scope? Governance fit?
   - Output: REVIEW-PRINCIPAL-*.md with 5 strategic recommendations
   - Time: 20-30 min (builds on Senior work)

3. **Security Engineer Review** (Sonnet 4.6 — threats)
   - Input: Draft plan + both prior reviews
   - Focus: What could go wrong? Threats? Data residency? Supply chain?
   - Output: REVIEW-SECURITY-*.md with 5 required controls + implementation phase
   - Time: 45-60 min (deep threat modeling)

4. **Orchestrator Integration**
   - Input: All three reviews
   - Task: Synthesize into updated plan
   - Update TODO.md with: phase adjustments, task reordering, security controls, scope deferrals
   - Status: "Ready for execution"
   - Time: 30-45 min

### Exit Criteria (Plan → Execution)
- ✅ All three reviews complete
- ✅ Recommendations integrated into plan
- ✅ Security blockers identified and phased correctly
- ✅ Escalation gates documented (when to go Lead/Principal/Security during execution)
- ✅ Success criteria are testable/measurable

---

## Phase 1: Task Execution (Approved Plan → Working Implementation)

### Entry Criteria
- Plan approved and finalized (from Phase 0)
- Tasks assigned to Engineer
- Estimated effort provided for each task

### Workflow

1. **Orchestrator assigns tasks**
   - Select next unstarted task from TODO.md
   - Format as TASK_ASSIGNMENT (see engineer-execution.md)
   - Assign to Engineer with: description, success criteria, constraints, effort estimate

2. **Engineer executes task** (Sonnet 4.6)
   - Input: Task assignment
   - Process: Execute the task, test success criteria, commit work
   - **If no blockers**: Report completion; Orchestrator marks TODO.md as done
   - **If blocker**: Escalate to Lead Engineer with description of blocker

3. **Lead Engineer unblocks** (Sonnet or Opus)
   - Input: Engineer's escalation (blocked work, options considered)
   - Process: Review, make decision or escalate further
   - **If unblockable by Lead**: Escalate to Principal/Security
   - Output: Decision + guidance for Engineer to retry

4. **Engineer retries** with Lead's guidance
   - Implement the decision
   - Commit work or escalate if new blocker found

5. **Repeat** until all tasks in plan are completed

### Task Assignment Template

```yaml
---
handoff_type: TASK_ASSIGNMENT
task_id: [unique ID]
phase: [Phase 1, 2, 3, etc.]
role: Engineer
owner: [name or TBD]
estimated_effort: [hours]
from_plan: [path to TODO.md section]
---

### Task Description
[What needs to be done]

### Success Criteria
- [ ] Criterion 1 (testable/measurable)
- [ ] Criterion 2
- [ ] Criterion 3

### Constraints
- Known blockers/dependencies
- Tools available, tools not available
- Time limit before escalate

### Checklist
- [ ] Understand the task
- [ ] Execute
- [ ] Verify success criteria
- [ ] Commit
- [ ] Report outcome
```

### Exit Criteria (Execution → Final Review)
- ✅ All planned tasks completed
- ✅ All work committed to git
- ✅ TODO.md updated with completion status
- ✅ Any security controls integrated
- ✅ No unresolved blockers

---

## Phase 2: Final Review (Implementation → Sign-off)

### Entry Criteria
- All implementation tasks complete
- All work committed
- Security controls integrated (if needed)

### Workflow

1. **Senior Engineer Final Review** (Sonnet 4.6 — implementation quality)
   - Input: Implementation work (git diff, new files, updated docs)
   - Focus: Did implementation match plan intent? Are success criteria met? Code quality OK?
   - Output: REVIEW-FINAL-SENIOR-*.md — thumbs up, feedback, or rework request
   - Time: 30-45 min

2. **Principal Engineer Review** (if needed; Opus 4.7 — strategic fit)
   - Input: Senior feedback + implementation
   - Focus: Does implementation align with strategic decisions? Any unintended scope creep?
   - **If no concerns**: Sign-off
   - **If concerns**: Provide guidance for adjustment
   - Time: 20-30 min (if needed)

3. **Decision**:
   - **All reviews positive**: Proceed to Phase 3 (Security check) OR Phase 4 (finalize) if no security controls
   - **Minor feedback**: Engineer makes adjustments, re-submit to Senior for quick re-check
   - **Major rework needed**: Return to task execution with specific guidance

### Exit Criteria (Review → Security Check or Finalize)
- ✅ Senior Engineer sign-off
- ✅ Principal Engineer sign-off (if involved)
- ✅ All feedback integrated
- ✅ Implementation matches plan intent

---

## Phase 3: Security Review (Implementation → Threat Validation)

### When to Invoke

**Always**: If plan called for security controls to be implemented
**Optional**: If Senior/Principal flagged concerns or unknown risks

**Skip if**: 
- No security-critical work in the plan
- Security review already happened during plan iteration (Phase 0)

### Workflow

1. **Security Engineer Final Review** (Sonnet 4.6 — threat validation)
   - Input: Implementation + security controls from plan
   - Focus: Are required controls actually implemented? Any threat gaps? Supply chain issues?
   - Output: REVIEW-FINAL-SECURITY-*.md — thumbs up or required mitigations
   - Time: 30-45 min

2. **Decision**:
   - **All controls implemented, no gaps**: Sign-off
   - **Mitigations needed but feasible**: Provide specific guidance; Engineer implements, re-submit
   - **Blocker**: Escalate to Principal for scope adjustment

### Exit Criteria (Security → Finalize)
- ✅ All required controls implemented
- ✅ No unmitigated threats
- ✅ Security sign-off

---

## Phase 4: Plan Finalization (Sign-off → Archived)

### Entry Criteria
- All implementation tasks complete
- All reviews passed (Senior + Principal + Security if needed)
- No rework requests outstanding

### Workflow

1. **Orchestrator finalizes**
   - Move completed tasks in TODO.md to "Completed" section
   - Add note: "Completed 2026-04-27 — see REVIEW-FINAL-*.md for sign-offs"
   - Archive review documents (keep in git, link from TODO.md)
   - Create "Lessons Learned" section in TODO.md (what went well, what to improve for next time)

2. **Commit final state**
   - Commit TODO.md with completion status
   - Message: `chore: finalize [plan name] — all reviews passed, work completed`

3. **Notification**
   - Voice notify or report: "Plan complete and signed off"
   - Link all review documents in a summary

### Exit Criteria (Finalize → Done)
- ✅ All reviews passed
- ✅ TODO.md marked complete
- ✅ Review documents archived
- ✅ Lessons learned documented

---

## Decision Tree: When to Escalate During Execution

```
Engineer hits blocker
  │
  ├─ "I don't know the answer" → Escalate to Lead Engineer
  │   └─ Lead clarifies / makes design decision
  │       └─ If Principal decision needed → Lead escalates to Principal
  │
  ├─ "I found a security issue" → Escalate to Lead + Security
  │   └─ Security assesses threat severity
  │       ├─ Mitigations feasible → Engineer implements
  │       └─ Blocker → Lead/Principal adjusts scope
  │
  ├─ "External dependency not ready" → Escalate to Orchestrator (via Lead)
  │   └─ Orchestrator coordinates across teams
  │       └─ Or marks task as blocked pending external work
  │
  └─ "Effort exceeded estimate significantly" → Escalate to Lead
      └─ Lead investigates: scope creep? wrong estimate? underestimated complexity?
          ├─ Adjust estimate for similar future tasks
          └─ Continue or escalate for scope adjustment
```

---

## Metrics & Feedback Loop

### Per-Implementation Metrics

Track:
- **Plan→Execution time**: How long from "plan approved" to "all tasks done"?
- **Escalations per task**: Average escalations per Engineer task?
- **Review feedback**: How much rework after final reviews?
- **Task estimation accuracy**: Estimate vs. actual effort (by task type)
- **Security findings**: Were security controls actually needed? Any gaps?

### Lessons Learned Template

After finalizing a plan:

```markdown
## Lessons Learned: [Plan Name]

### What Went Well
- [Specific thing that was efficient/smooth]
- [Good decision that paid off]
- [Helpful guidance that unblocked quick]

### What Could Improve
- [Task under-specified? How to improve for next time?]
- [Estimation off? Pattern to track?]
- [Escalation pattern that was inefficient?]

### Reusable Patterns
- [Technique or decision that could apply to other plans]
- [Review feedback that recurs]

### For Next Time
- [Specific change to task specification, effort estimate, or escalation gates]
```

---

## Integration with Existing Skills

This workflow combines:
- **plan-iterate.md** — Phases 0 & 2-3 (plan + final reviews)
- **engineer-execution.md** — Phase 1 (task execution + escalation)
- **config-standard.md** — Applied during plan Phase 0 (feasibility check)
- **cleanup.md** — Applied after Phase 4 (post-completion cleanup)

---

## Timeline Reference

| Phase | Duration | Owner | Key Handoff |
|-------|----------|-------|-------------|
| **Phase 0** | 3-4 hours | Orchestrator → Senior/Principal/Security | 3 review docs + finalized plan |
| **Phase 1** | Variable (depends on plan scope) | Engineer → Lead (escalates as needed) | Completed implementation in git |
| **Phase 2** | 1-2 hours | Senior + Principal (if needed) | Final review sign-offs |
| **Phase 3** | 0.5-1 hour (if needed) | Security | Security sign-off or mitigations |
| **Phase 4** | 15-30 min | Orchestrator | Finalized TODO.md + lessons learned |

**Total for medium plan (Phase 1 = 4-5 hours of Engineer work)**: ~1 day elapsed time
**Total for large plan (Phase 1 = 15-20 hours of Engineer work)**: ~2-3 days elapsed time

---

## Example: spec-extract Implementation Walkthrough

**Phase 0**: Plan iteration (3-4 hours)
- Senior: Phase feasibility, task breakdown, Phase 1.5 spike recommendation
- Principal: MVP scope (defer multi-language), pilot strategy (2 services opt-in), schema as ADR
- Security: Scrub pass + secret scan gate required before Phase 2 Day 1
- Orchestrator: Integrate all feedback, update TODO.md, mark "Ready for execution"

**Phase 1**: Task execution (approx. 12-16 hours Engineer work across 4-5 days)
- Week 1: Engineer executes Phase 1 (research + INVENTORY.md) — 3 days, no escalations expected
- Week 2: Phase 1.5 (scanner spike design) — 1-2 days, likely 1 escalation for schema ADR validation
- Week 2-3: Phase 2 (extraction engine) — 3-4 days, likely 2-3 escalations (security controls, detection method choices)
- Week 3: Phase 3 (audit + validation) — 3-4 days, escalations for enforcement repo coordination
- Week 3-4: Phase 4 (docs + pilot) — 2-3 days, minimal escalations

**Phase 2**: Final review (1-2 hours)
- Senior Engineer: Implementation matches plan intent? Yes.
- Principal: Strategic decisions respected (pilot scope, deferral, ADR)? Yes.
- No rework needed.

**Phase 3**: Security review (0.5-1 hour)
- Security: Scrub pass + secret scan gate implemented as required? Yes. Sign-off.

**Phase 4**: Finalization (15-30 min)
- Orchestrator: Mark complete, archive reviews, document lessons learned
- Commit to git with final status

**Total**: ~1 day planning + 1 week execution + 0.5 day review = ~1.5 weeks calendar time

---

