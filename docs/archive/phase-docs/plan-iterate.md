---
name: Multi-Stage Plan Iteration via Expert Review
description: Delegate plan refinement through Senior → Principal → Security engineers (or other review chain) to minimize tokens and maximize expertise
type: skill
delegable_to: [Senior Engineer, Principal Engineer, Security Engineer, Lead Engineer]
relates_to: [planning-standard.md]
---

# Plan Iteration via Multi-Stage Expert Review

A cost-efficient delegation pattern for iterating plans through multiple expert reviews. Cheaper models (Senior Engineer) work first, then escalate findings to more expensive models (Principal, Security) for synthesis and deeper validation.

## Purpose

When a plan is drafted but needs refinement:
- Don't have one expert review everything (expensive)
- Chain reviews through increasing levels of expertise
- Each stage builds on the previous stage's output
- Minimize total token usage; maximize effort density

## The Pattern: Three-Stage Review Chain

### Stage 1: Senior Engineer Review
**Model**: Sonnet 4.6 (cheaper, deep Go/architecture knowledge)  
**Input**: Original plan + brief context  
**Output**: Feedback document with:
- Phase feasibility assessment
- Task breakdown quality check
- Known unknowns and research gaps
- Suggestions for phase reordering or scope adjustment

**Deliverable format**: `TODO.md task section + REVIEW-SENIOR.md`

**Time**: 30-45 min  
**Tokens**: Moderate

### Stage 2: Principal Engineer Review
**Model**: Opus 4.7 (expensive, strategic thinking)  
**Input**: Original plan + Senior Engineer feedback  
**Output**: Strategic synthesis:
- Are phases in the right order?
- Is scope appropriate (MVP vs. full feature)?
- Are success criteria testable?
- Cross-service concerns?
- Long-term implications (will this decision age well)?

**Deliverable format**: `REVIEW-PRINCIPAL.md`

**Time**: 20-30 min (builds on Senior work, no deep re-reading needed)  
**Tokens**: Lower (builds on prior analysis)

### Stage 3: Security Engineer Review
**Model**: Sonnet 4.6 (security domain expertise)  
**Input**: Original plan + both prior reviews  
**Output**: Security & compliance assessment:
- Are security concerns identified?
- Are secrets/credentials handled safely?
- Are access controls implicit in the plan?
- Compliance implications (SOC2, data residency, etc.)?

**Deliverable format**: `REVIEW-SECURITY.md`

**Time**: 20-30 min  
**Tokens**: Moderate

### Final: Orchestrator Integration
**Input**: Original plan + all 3 reviews  
**Output**: Refined plan in TODO.md with:
- Adjusted task list reflecting feedback
- Phase reordering if warranted
- Success criteria refined for testability
- Security checkpoints added
- Status updated: "Planning" → "Ready for Implementation"

## Workflow

```
1. Orchestrator drafts plan in TODO.md
   └─ Save as: {workspace-name}/TODO.md or service/TODO.md

2. Orchestrator delegates to Senior Engineer
   Input: Link to plan (TODO.md section)
   Task: Review feasibility, break down tasks, identify gaps
   Output: REVIEW-SENIOR.md with feedback

3. Orchestrator delegates to Principal Engineer
   Input: Original plan + REVIEW-SENIOR.md
   Task: Strategic assessment, reordering, success criteria
   Output: REVIEW-PRINCIPAL.md with synthesis

4. Orchestrator delegates to Security Engineer
   Input: Original plan + both reviews
   Task: Security & compliance assessment
   Output: REVIEW-SECURITY.md with checkpoints

5. Orchestrator integrates all feedback
   Update: TODO.md with refined task list, phases, success criteria
   Mark: Status = "Ready for Implementation" (if reviews positive)
   Archive: Move REVIEW-*.md to a doc directory or commit to git
```

## Delegation Format for Each Stage

### Senior Engineer Handoff

```yaml
---
handoff_type: DELEGATE
task_id: 2026-04-27-plan-iterate-spec-extract-senior
role: Senior Engineer
model: sonnet
context: spec-extract skill planning for multi-repo pattern catalog
---

### Plan to Review

See: {workspace-name}/TODO.md section "spec-extract"

### Your Task

Review the 5-phase spec-extract skill plan for:
1. **Phase feasibility** — Can each phase be executed as described?
2. **Task breakdown** — Are tasks specific and actionable?
3. **Unknowns** — What research is missing? What assumptions need validation?
4. **Reordering** — Should any phase move earlier/later?
5. **Scope creep** — Any over-scoping? Under-scoping?

### Success Criteria

Produce REVIEW-SENIOR.md with sections:
- [ ] Phase Feasibility Assessment
- [ ] Task Breakdown Quality
- [ ] Known Unknowns & Gaps
- [ ] Phase Reordering Suggestions
- [ ] Scope Adjustments

```

### Principal Engineer Handoff

```yaml
---
handoff_type: DELEGATE
task_id: 2026-04-27-plan-iterate-spec-extract-principal
role: Principal Engineer
model: opus
context: spec-extract skill planning — strategic review (builds on Senior feedback)
---

### Plan + Prior Review

See: {workspace-name}/TODO.md section "spec-extract"  
Prior feedback: REVIEW-SENIOR.md (attached/linked)

### Your Task

Strategic synthesis:
1. **Phase ordering** — Given Senior feedback, are phases in optimal order?
2. **Success criteria** — Are they testable? Measurable?
3. **Long-term implications** — Will this pattern scale? Age well?
4. **Cross-service concerns** — Are there inter-service dependencies?
5. **MVP vs. full feature** — Is scope right-sized?

### Success Criteria

Produce REVIEW-PRINCIPAL.md with sections:
- [ ] Strategic Assessment (phase ordering, scope)
- [ ] Success Criteria Validation (testability)
- [ ] Long-term Implications
- [ ] Cross-service Concerns
- [ ] Recommendations for Integration
```

### Security Engineer Handoff

```yaml
---
handoff_type: DELEGATE
task_id: 2026-04-27-plan-iterate-spec-extract-security
role: Security Engineer
model: sonnet
context: spec-extract skill planning — security & compliance review
---

### Plan + Prior Reviews

See: {workspace-name}/TODO.md section "spec-extract"  
Prior feedback:
- REVIEW-SENIOR.md
- REVIEW-PRINCIPAL.md

### Your Task

Security & compliance assessment:
1. **Security concerns** — What could go wrong? Secrets/credentials handling?
2. **Access controls** — Are they implicit in the plan? Explicit?
3. **Data handling** — Spec catalog = data. How is it protected?
4. **Compliance** — SOC2, data residency, audit trail implications?
5. **Secrets management** — Do pattern specs ever include credentials?

### Success Criteria

Produce REVIEW-SECURITY.md with sections:
- [ ] Security Concerns Identified
- [ ] Access Control Assessment
- [ ] Data Handling & Protection
- [ ] Compliance Implications
- [ ] Secrets Management Checkpoints
```

## Post-Review Integration

After all 3 reviews, Orchestrator:

1. **Read all reviews** (REVIEW-SENIOR.md, REVIEW-PRINCIPAL.md, REVIEW-SECURITY.md)
2. **Synthesize findings** into refined plan:
   - Reorder phases if recommended
   - Adjust task list based on Senior feedback
   - Strengthen success criteria per Principal feedback
   - Add security checkpoints per Security feedback
3. **Update TODO.md** with refined version
4. **Change status** from "Planning" to "Ready for Implementation"
5. **Archive reviews** (commit to git or move to docs/)

**Example refined section**:
```markdown
### spec-extract Skill — Software Specification & Pattern Extraction

**Status**: Ready for Implementation ✅  
**Owner**: [Assigned during implementation]  
**Target completion**: 2026-05-15

**Refinements from expert review**:
- Senior Engineer: Reorder Phase 1 & 2 (research + extraction in parallel)
- Principal Engineer: Success criteria now include compliance audit validation
- Security Engineer: Added step 2.5 for secrets scanning in pattern specs

[Rest of plan with refined phases, tasks, success criteria]
```

## Token & Time Economics

| Stage | Model | Time | Tokens | Cumulative |
|-------|-------|------|--------|------------|
| Senior | Sonnet | 35 min | ~45k | 45k |
| Principal | Opus | 25 min | ~35k | 80k |
| Security | Sonnet | 25 min | ~30k | 110k |
| **Total** | **Mixed** | **85 min** | **110k** | **110k** |

**vs. single Opus review**: 1 × Opus = ~80 min, ~65k tokens, but lower quality (no domain specialists)

**vs. three Opus reviews**: 3 × Opus = 120 min, ~195k tokens (more expensive, marginal benefit)

**Why this works**: Senior Engineer catches structural issues early. Principal Engineer doesn't re-audit feasibility, just synthesizes. Security Engineer has context from prior reviews, doesn't start from scratch.

## When to Use This Pattern

✅ **Use for:**
- Major new features (spec-extract, new microservice architecture)
- Cross-service initiatives (multi-repo changes)
- Infrastructure redesigns (CDK patterns, CICD overhaul)
- Security or compliance initiatives
- Plans >1000 lines or >20 tasks

❌ **Skip for:**
- Single-file bugfixes
- Small refactorings
- Obvious implementation tasks
- Emergency patches

## Lessons Learned (Updated 2026-04-27)

After first use on spec-extract skill:

**What worked well:**
- Three-stage chain catches different angles (feasibility → strategy → security)
- Senior Engineer feedback on task granularity very actionable
- Principal Engineer strategic input (pilot scope, deferral decisions) high-value
- Security Engineer threat modeling prevents week-1 incidents
- Phase 1.5 "spike" recommendation was critical for unblocking parallelism
- Each review built on prior; later stages didn't re-audit earlier work

**Process improvements:**
- Schema/ADR freezing in Phase 1.5 is load-bearing decision — flag it explicitly
- MVP scope decisions (what to defer) matter more than architectural ones
- Security review should flag specific controls + phase to integrate them (not retrofit)
- Adoption criteria (real usage during build) prevents over-engineering
- UX/triage decisions (severity, suppression) belong in implementation, not just planning

**Scaling the pattern:**
- Can apply same three-stage review to implementation: Engineer → Lead → Principal/Security
- Base Engineer fixes tasks; Lead reviews; Principal/Security escalates on blockers
- Reuse the review prompts; they're role-specific and repeatable

## Building on This Skill Over Time

This skill is a template. As we iterate more plans and implementations:

1. **Add role-specific templates** — Create reusable review prompts per role (DONE for planning; add for implementation)
2. **Track review quality** — Which feedback led to better implementations?
3. **Refine the chain** — Maybe we add "DevOps Engineer" for infrastructure plans; "Product Manager" for feature scope
4. **Reuse feedback** — Catalog common patterns in reviews (e.g., "missing error handling", "scope creep on Phase X")
5. **Automate where possible** — Can some reviews be partially automated? (lint checks, security scans)
6. **Escalation gates** — When does Engineer work get escalated to Lead? When to involve Principal?

## FAQ

**Q: Why not just have Opus review everything?**  
A: Opus is expensive and generalist. Senior Engineer specializes in architecture/Go; Security Engineer specializes in threats. Domain expertise matters.

**Q: Can stages run in parallel?**  
A: No — each stage benefits from prior reviews. But theoretically, you could run Principal & Security in parallel if time matters more than token efficiency.

**Q: What if reviews disagree?**  
A: Orchestrator synthesizes. If Principal and Security conflict (e.g., security wants more checks, Principal wants simplicity), Orchestrator decides. Document the tradeoff in the refined plan.

**Q: Do we always need all 3 stages?**  
A: No. Smaller plans might just need Senior → Principal. Security-critical plans might add a 4th stage (Compliance Engineer).

**Q: Should review documents be committed to git?**  
A: Yes — they become part of the planning record. Future engineers can see what was considered. Commit as REVIEW-*.md or link from TODO.md.

---

## Example: spec-extract Plan Iteration

**Initial draft**: {workspace-name}/TODO.md (this session)

**Stage 1 - Senior Engineer**:  
Output: REVIEW-SENIOR-spec-extract.md
- Suggests parallelizing Phase 1 research + Phase 2 tool design
- Flags that pattern scanner complexity is underestimated (add 1 week)
- Questions success criteria "usable on any repo" (too vague)

**Stage 2 - Principal Engineer**:  
Output: REVIEW-PRINCIPAL-spec-extract.md
- Agrees on parallelization
- Questions whether Phase 5 (generalization) belongs in MVP
- Suggests deferring to Phase 6, focus first 4 phases on ERS-specific patterns
- Success criteria refined: "spec-extract works on 2+ non-ERS repos" (concrete)

**Stage 3 - Security Engineer**:  
Output: REVIEW-SECURITY-spec-extract.md
- Spec catalog might contain sensitive patterns (e.g., credential handling)
- Recommends: Don't commit raw Secrets Manager patterns to git
- Suggests: Phase 2.5 for "sanitize spec catalog before publishing"

**Orchestrator Integration**:  
- Reorder: Phase 1 → parallel with Phase 2
- Defer: Phase 5 to Phase 6 (post-MVP)
- Add: Phase 2.5 (sanitize)
- Refine success criteria per Principal feedback
- Status: "Ready for Implementation" ✅

