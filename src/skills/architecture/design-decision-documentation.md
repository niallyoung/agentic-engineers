# Principal Engineer — Design Decision Documentation

**Role:** Principal Engineer (Opus 4.6, high effort)  
**Purpose:** Document architectural decisions so they persist beyond the decision-maker

---

## Overview

Good architecture decisions get lost in Slack, meetings, and git commit messages. This skill captures the reasoning so future maintainers understand *why* the system is designed this way.

**Input:** Completed architecture design (from architecture-design.md)  
**Output:** ADR (Architecture Decision Record) or design decision document

**Goal:** Record decisions as reference for future changes, onboarding, and system evolution.

---

## Architecture Decision Record (ADR) Format

ADRs are one-page documents that capture:
1. **Status** — proposed, accepted, superseded
2. **Context** — what was the situation?
3. **Decision** — what did we decide?
4. **Rationale** — why did we choose this?
5. **Consequences** — what changed as a result?
6. **Alternatives** — what didn't we choose, and why?

### Template

```markdown
# ADR-[NUMBER]: [Title]

**Status:** Accepted | Proposed | Superseded

**Date:** YYYY-MM-DD

## Context

[What is the situation that required this decision?]

- Current state: [describe]
- Problem: [what doesn't work?]
- Constraints: [deadline, budget, team capability, compliance]
- Scope: [which services/teams affected?]

## Decision

[What did we decide to do?]

We will [action] because [rationale].

## Rationale

[Why this decision over alternatives?]

### Trade-offs

- **Benefit A:** [what we gain]
  - Cost: [what we give up for this]

- **Benefit B:** [what we gain]
  - Cost: [what we give up for this]

## Consequences

### Positive
- [what improves]
- [what becomes easier]

### Negative
- [what gets harder]
- [what new risks we took]
- [what we can't do easily]

### Operational Impact
- Deployment: [how does this change deployment?]
- Monitoring: [new metrics to watch]
- On-call: [new failure modes]
- Knowledge: [what teams need to learn?]

## Alternatives Considered

### Option A: [Name]
- Pros: [benefits]
- Cons: [drawbacks]
- Why rejected: [specific reason]

### Option B: [Name]
- Pros: [benefits]
- Cons: [drawbacks]
- Why rejected: [specific reason]

## Supersedes

[If this overrides a previous decision, reference it]

## Related Decisions

- ADR-N: [related decision]
- ADR-M: [related decision]

## References

- GitHub issue: [link]
- Design doc: [link]
- Implementation: [repo/PR]
```

---

## When to Document

**Always document if:**
- Decision affects >2 services
- Decision is not a variant of existing pattern
- Decision involves new technology or approach
- Decision has significant tradeoffs
- Decision reversed a previous decision (supersedes old ADR)

**Maybe document if:**
- Single-service change, but unusual/novel
- Sets a pattern for future similar decisions
- Helps with onboarding new team members

**Don't need ADR if:**
- Straightforward implementation of established pattern
- Bug fix (document in commit message instead)
- Internal refactoring with no external impact

---

## Storage & Indexing

**Location:** Each repo's `docs/adr/` directory  
**Naming:** `ADR-0001-description.md`, `ADR-0002-description.md` (sequential)

**Create an index** (`docs/adr/README.md`):
```markdown
# Architecture Decision Records

| # | Title | Status | Date |
|---|-------|--------|------|
| [001](ADR-0001-cqrs-event-sourcing.md) | Implement CQRS with Event Sourcing | Accepted | 2026-01-15 |
| [002](ADR-0002-redis-caching.md) | Add Redis caching layer | Accepted | 2026-02-20 |
| [003](ADR-0003-graphql-vs-rest.md) | Reject GraphQL, standardize on REST | Accepted | 2026-03-10 |
```

---

## Key Principles

### 1. Record Reasoning, Not Just Decisions

❌ **Bad:** "We chose Redis"  
✅ **Good:** "We chose Redis because PostgreSQL queries for related entities were taking 500ms. Redis cache with 1hr TTL reduces avg query time to 50ms while accepting eventual consistency (acceptable per requirements). Operational trade-off: need Redis monitoring and cluster management."

### 2. Include Alternatives

❌ **Bad:** "We decided to use event sourcing"  
✅ **Good:** "We chose event sourcing over traditional CRUD because:
- Option A (CRUD): simpler to build, but audit log requires separate table, reconciliation risk
- Option B (event sourcing): higher learning curve, but audit is free, replay is built-in
- We chose B because audit trail is critical and future compliance may require replay."

### 3. Be Honest About Constraints

❌ **Bad:** "We decided to monolithic because monoliths are simple"  
✅ **Good:** "We chose monolithic because:
- Timeline: feature required in 4 weeks, microservices would add 6 weeks design+delivery
- Team capability: team is new to distributed systems, monolithic reduces failure modes
- We'll extract services later as the service grows"

### 4. Record Consequences Clearly

❌ **Bad:** "Deployment is easier now"  
✅ **Good:** "Deployment consequences:
- Positive: single artifact to deploy, simpler CI/CD
- Negative: database schema changes block all service updates, increased coordination needed
- Operations: on-call incidents related to schema locks now affect entire platform, not one service"

---

## Obsolescence

**When to supersede an ADR:**
- Technology changes (new tool is clearly better)
- Requirements change (constraint no longer applies)
- Lessons learned (decision worked poorly)
- Architecture evolved (decision still applies but different scope)

**Superseding steps:**
1. Update old ADR status to "Superseded by ADR-NNN"
2. Write new ADR with reference to old one
3. Explain what changed and why

---

## Integration with Architecture Design

**architecture-design.md** → detailed plan for HOW to implement  
**design-decision-documentation.md** → recorded REASONING for WHY we chose this architecture

**Typical flow:**
1. Principal designs → architecture-design.md (phases, timelines, rollback)
2. Team implements → code + commits
3. Principal writes → ADR (captures decision for future)
4. Engineer reads → implements per design
5. Future maintainer reads → ADR explains WHY, can make informed decisions about changes

---

## Success Criteria

✅ Reader understands why this decision was made, not just what was decided  
✅ Alternatives are documented (why did we NOT choose them?)  
✅ Consequences are explicit (what does this cost us operationally?)  
✅ Decision can be understood 2 years later by someone who wasn't there  
✅ If requirements change, reader knows which parts of the decision are flexible
