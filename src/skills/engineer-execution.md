---
name: Engineer Task Execution & Escalation Pattern
description: Base-level engineer execution of implementation tasks with clear escalation to Lead/Principal/Security as needed
type: skill
delegable_to: [Engineer, Lead Engineer, Principal Engineer, Security Engineer]
relates_to: [plan-iterate.md, config-standard.md]
---

# Engineer Task Execution & Escalation Pattern

Base-level engineers execute implementation tasks from an approved plan, with clear escalation paths for blockers, design decisions, and security concerns.

## Purpose

Decouple planning review (Senior → Principal → Security) from implementation execution (Engineer → Lead → Principal/Security escalate). Allows cheaper models to execute tasks while reserving expensive models for blockers and design decisions only.

## The Pattern

```
Orchestrator (assigns tasks from approved TODO.md)
    ↓
Engineer (Sonnet) — executes task, implements code/docs
    ├─ No blockers? → commit, update TODO.md "completed"
    └─ Blocker detected? → escalate to Lead Engineer
         ↓
      Lead Engineer (Sonnet/Opus) — reviews, unblocks, or escalates
         ├─ Unblocked? → Engineer retries
         └─ Design decision needed? → escalate to Principal
              ↓
           Principal Engineer (Opus) — makes strategic decision, returns guidance
              ├─ Decision made? → Engineer retries
              └─ Security concern? → escalate to Security
                   ↓
                Security Engineer (Sonnet) — threat assessment, mitigations
                   ├─ Mitigations feasible? → Engineer integrates and retries
                   └─ Blocker? → loop back to Principal
```

## Engineer Task Execution

### Handoff Format

Orchestrator assigns task to Engineer:

```yaml
---
handoff_type: TASK_ASSIGNMENT
task_id: 2026-04-27-spec-extract-phase-1-inventory
role: Engineer
model: sonnet
owner: [Engineer name or TBD]
estimated_effort: 3 hours
from_plan: {service-name}/TODO.md → spec-extract → Phase 1
---

### Task Description

Scan all 8 ERS services for pattern occurrences and synthesize INVENTORY.md.

**Input**: Planning notes, pattern heuristics doc
**Output**: INVENTORY.md with pattern categories, service matrix, quick links
**Success Criteria**:
- All 8 services scanned for: Makefile, GitHub Actions, CDK, Go modules, tests, security patterns
- INVENTORY.md created with clear structure and cross-references
- Ready for Phase 1.5 scanner spike team to consume as input

**Known constraints**:
- No external dependencies
- Can run in parallel with other Phase 1 tasks
- Estimated 3 hours; if exceeds 4.5 hours, escalate blockers to Lead

### Checklist Before Handoff
- [ ] Task description is clear and unambiguous
- [ ] Success criteria are testable/measurable
- [ ] Estimated effort is realistic for Engineer (not multi-week)
- [ ] No known blockers at handoff time
- [ ] If multi-phase, clearly mark what's Phase 1 vs. Phase 2, etc.
```

### Execution Workflow (Engineer)

1. **Accept task** — Confirm you understand the task, success criteria, and constraints
2. **Execute** — Do the work: write code, create docs, run tests, etc.
3. **Verify success criteria** — Test that output matches criteria, no blockers found
4. **Commit** — Create a commit with the work (can be wip/ branch or direct to main depending on repo)
5. **Report outcome**:
   - **No blockers**: "Task complete. Committed {SHA}. Moved to Completed in TODO.md."
   - **Blocker found**: Describe the blocker, what you tried, why you're blocked. Escalate to Lead.

### When to Escalate (Engineer → Lead)

Escalate when:
- ❌ **Design ambiguity** — Two valid approaches; not sure which is right
- ❌ **External dependency** — Waiting on another task or team; blocking your work
- ❌ **Success criteria unclear** — What you produced doesn't clearly match criteria
- ❌ **Estimated effort exceeded** — You've hit 4.5 hours and not done; need guidance on scope
- ⚠️ **Uncertainty about approach** — You're not confident the approach is correct (not a blocker yet, but worth validating)

**Do NOT escalate for:**
- ✅ Technical bugs or errors (keep trying, fix them)
- ✅ Clarification questions (check the task description again, ask in comments)
- ✅ Trying multiple approaches (it's OK to explore)

### Escalation Handoff to Lead

```yaml
---
handoff_type: ESCALATE_TO_LEAD
task_id: [original task ID]
role: Lead Engineer
blocker_type: [design_ambiguity | external_dependency | scope_unclear | effort_exceeded | uncertainty]
effort_so_far: [hours spent]
---

### What I've Tried

[Brief description of your approach, what you've tested, why you're stuck]

### Options

[2-3 possible paths forward; pros/cons of each]

### What I Need

[Specific guidance: design decision, scope clarification, external coordination, etc.]

### Current State

[Any work in progress that Lead should review]
```

---

## Lead Engineer Review & Unblocking

### Lead's Role

Review Engineer's work, identify the root blocker, and either:
1. **Unblock** — Provide guidance, clarification, or design decision; Engineer retries
2. **Escalate** — If Principal or Security decision needed, escalate with context
3. **Abort** — If task is invalid or out of scope, halt and report back to Orchestrator

### Lead Handoff Response

```yaml
---
handoff_type: LEAD_DECISION
task_id: [task ID]
decision: [unblock | escalate | abort]
---

### Decision

[Your decision: which path forward, design choice, etc.]

### Rationale

[Why this choice; what informed your decision]

### Next Steps for Engineer

[Specific guidance on how to proceed; what to try next]

### If Escalating

[Reason for escalation; what Principal/Security decision is needed]
```

---

## Principal Engineer Escalation (Design Decisions)

When Lead escalates a design ambiguity to Principal:

**Principal's role:**
- Make the design decision (or clarify constraints that inform the decision)
- Return guidance that unblocks the Engineer

**Principal handoff back to Engineer:**
- Clear decision statement (not options, but which option and why)
- Rationale (so Engineer understands the tradeoff)
- Implementation guidance (how to execute the decision)

Engineer retries with Principal's guidance.

---

## Security Engineer Escalation (Threats)

When Engineer or Lead encounters a security concern:

**Security's role:**
- Threat assessment (is this actually a security issue?)
- Mitigations (how to address the threat without major rework)
- Sign-off (can we proceed with the mitigation, or is it a blocker?)

**Security handoff response:**
- Threat assessment (severity, exploitability)
- Recommended mitigations (specific, implementable)
- Effort to implement (hours, can fit in current phase or deferred?)
- Blocking or non-blocking

Engineer integrates mitigations and retries. If Security says "blocker, can't fix in current phase," escalate back to Lead/Principal for scope adjustment.

---

## Escalation Gates & Triggers

| Situation | Escalate To | Why | Example |
|-----------|-------------|-----|---------|
| **Design ambiguity** — Two valid approaches | Lead | Needs experienced judgment | "Scrub pass: regex vs. AST vs. manual templates" |
| **External dependency** — Other task not ready | Orchestrator (via Lead) | Needs coordination; may unblock in parallel | "Waiting for Phase 1 INVENTORY.md to finalize heuristics" |
| **Effort exceeded** | Lead | May indicate scope creep or estimation error | "Phase 1 research is at 4h, estimated 3h; still not done" |
| **Ambiguous success criteria** | Lead | Task was under-specified | "What counts as 'all 8 services scanned'? Just Makefile or all patterns?" |
| **Security concern** | Security (via Lead) | Needs threat modeling expertise | "Scrub pass: are we scrubbing enough content?" |
| **Strategic conflict** | Principal (via Lead) | Blocks implementation of task due to bigger tradeoff | "Should Phase 1.5 spike test non-ERS repos for generalizability?" |

---

## Metrics & Feedback

### Per-Task Metrics

For each task, track:
- **Time to completion** — How long did Engineer spend? Compare to estimate.
- **Escalations** — How many times did it escalate? Why?
- **Iterations** — How many attempts before success?
- **Success criteria** — Did output match criteria on first submission?

### Learning Loop

After a batch of tasks (e.g., Phase 1 complete):
- Which task types escalated most? (Pattern?)
- Which escalation types were most helpful? (Design decision? Clarification?)
- Any estimates that were way off? (Revisit estimation for similar tasks)
- Any success criteria that were unclear? (Improve task specification)

---

## Task Types & Escalation Patterns

### Type 1: Pure Execution (Low Escalation Risk)

Example: "Scan all 8 services for Makefile patterns and document occurrences."

**Escalation pattern**: Unlikely. Clear success criteria, no design decisions needed.

**Lead's role**: Spot check output; accept or request refinement.

### Type 2: Decision-Heavy (Medium Escalation Risk)

Example: "Design the spec file format (YAML vs. Markdown vs. JSON); produce sample output."

**Escalation pattern**: Expected. Multiple valid answers; needs design judgment.

**Lead's role**: Engineer proposes options; Lead picks one with rationale.

### Type 3: Security-Critical (High Escalation Risk)

Example: "Implement scrub pass for spec output; redact account IDs, Cognito IDs, etc."

**Escalation pattern**: Expected. Security needs to validate the scrub is complete.

**Lead's role**: Engineer implements; Lead coordinates with Security for review.

### Type 4: External Dependencies (Variable Risk)

Example: "Finalize Phase 1.5 spike design; requires coordination with Phase 2 team."

**Escalation pattern**: May escalate to Orchestrator for coordination.

**Lead's role**: Lead identifies blockers early; Orchestrator handles cross-team sync.

---

## When Escalation Becomes a Pattern

If a task escalates more than once, or if Engineer keeps hitting the same blocker:

**Lead's decision**: 
- Is the task itself under-specified? (Improve and retry)
- Is the Engineer the wrong fit? (Reassign to someone with more relevant experience)
- Is the blocker systemic? (Escalate to Principal for a design decision that affects the whole phase)

---

## Feedback to Orchestrator

After task completion (or escalation):

**Engineer reports**:
- Task ID, completion status
- Time spent (vs. estimate)
- Any blockers escalated (with description)
- Any changes to success criteria or scope discovered during execution

**Lead reports** (if escalations happened):
- What blocked the Engineer?
- How was it resolved?
- Any feedback for the Orchestrator on task specification?

This feeds back into task specification improvements for future similar work.

---

## FAQ

**Q: Should Engineer always escalate if there's any ambiguity?**  
A: No. Engineer should make reasonable decisions and move forward. Escalate only when you're genuinely blocked or uncertain about the approach.

**Q: What if Engineer and Lead disagree on the approach?**  
A: Lead's decision is final for that task. If Engineer thinks Lead's decision is strategically wrong, that's a Principal question (later). For now, execute Lead's guidance.

**Q: Can Engineer skip Lead and escalate directly to Principal?**  
A: No. Always go through Lead first. Lead filters trivial questions and coordinates the escalation. Direct escalation overloads Principal.

**Q: How long should Lead take to respond?**  
A: Within 1-2 hours ideally. If longer, Engineer can unblock themselves by making a reasonable call and documenting the decision.

**Q: What if a task is genuinely impossible?**  
A: Escalate to Lead immediately with evidence of why. Lead decides whether to abort, rework the task, or escalate for scope adjustment.

**Q: Does every task need a post-mortem?**  
A: No. Just track metrics (time, escalations, success criteria met). Full postmortem only if something went very wrong.

---

## Example Walkthrough

**Task**: Phase 1 — Scan GitHub Actions patterns in all 8 services

**Engineer execution**:
1. Scans {service-name}, {service-name}, {service-name}, {service-name}, {service-name}, {service-name}, {service-name}, {service-name}
2. Documents main.yaml and branch.yaml patterns in INVENTORY.md
3. Notices {service-name} has a custom .github/workflows/deploy.yaml that doesn't fit the pattern
4. Unsure: should custom workflows be documented as a deviation, or ignored?
5. **Escalates to Lead**: "Found 1 service with custom workflow; how should I handle this?"

**Lead review**:
- Asks Engineer: "Is {service-name} still being used? Or deprecated?"
- (Engineer checks: it's deprecated per CLAUDE.md)
- **Decision**: "{service-name} is deprecated. Exclude it from the pattern analysis. Note in INVENTORY.md: '7/8 services follow main.yaml + branch.yaml pattern. {service-name} deprecated, excluded.'"
- Engineer retries; task complete.

**Result**: No escalation to Principal; Lead unblocked it in 5 minutes.

---

## Integration with plan-iterate Skill

- **plan-iterate**: Multi-stage review of plans (Senior → Principal → Security)
- **engineer-execution**: Multi-stage execution of tasks (Engineer → Lead → Principal/Security escalate)

Both skills use the same escalation pattern; reuse the templates and role expectations.

