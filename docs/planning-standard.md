---
name: Planning Standards and TODO.md-Only Enforcement
description: Centralized planning documentation via TODO.md only — no plan.md files or scattered planning documents
type: skill
delegable_to: [Orchestrator, Lead Engineer]
relates_to: [config-standard.md]
---

# Planning Standards — TODO.md-Only Enforcement

All planning work for ERS platform initiatives must be documented in **TODO.md files only**. No scatter planning documents, no plan.md files, no separate planning repos.

## Standard

### Where Plans Go

- **Default location**: `{workspace-name}/TODO.md` (meta-repo level concerns, cross-service initiatives, specs, skills)
- **Service-specific plans**: Individual service's `TODO.md` (service-level features, refactoring, deployment strategies)
- **No other files**: Do not create `plan.md`, `PLAN.md`, `planning.md`, or separate planning documents

### Structure

Each service/workspace should have a single `TODO.md` with clear sections:

```markdown
# [Service/Workspace] TODO

## In Progress

### [Feature/Task Name]

**Status**: Planning/In Progress/Blocked  
**Owner**: [Name or TBD]  
**Target completion**: YYYY-MM-DD  
**Context**: [Link to related issues, specs, or PRs]

#### Overview
[What we're building and why]

#### Goals
1. [Specific, measurable goal]
2. [Specific, measurable goal]

#### Approach
[How we'll solve it]

#### Tasks (Breakdown)
- [ ] Phase 1: Research
- [ ] Phase 2: Implementation
- [ ] Phase 3: Validation

#### Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2

#### Notes
[Blockers, dependencies, open questions]

---

## Completed

- ✅ [Completed task 1]
- ✅ [Completed task 2]
```

### Enforcement Rules

1. **No plan.md files** — All work planning goes into TODO.md
2. **No scattered docs** — Don't create feature-specific planning documents
3. **TODO.md is comprehensive** — Include research, phases, success criteria, blockers
4. **Link to code PRs** — Reference the actual work (git branches, commits) from TODO.md
5. **Archive completed items** — Move finished work to "Completed" section with checkmarks

### Examples

**Good**: `{workspace-name}/TODO.md` with a `spec-extract` task documented comprehensively  
**Bad**: `{workspace-name}/spec-extract-PLAN.md` or separate planning document  

**Good**: `{example-service}/TODO.md` with "event replay enhancement" detailed with phases  
**Bad**: `{example-service}/ENHANCEMENT-PLAN.md` or in-code comments describing the plan  

### When to Use TODO.md vs. Other Docs

| Document | Purpose | Example |
|----------|---------|---------|
| **TODO.md** | Planning work, tracking progress, documenting decisions | "spec-extract skill implementation phases" |
| **CLAUDE.md** | Service architecture, patterns, how-to operate | "{example-service} architecture, API reference" |
| **README.md** | Getting started, quick reference | "Build & test commands, deployment steps" |
| **SKILLS-INDEX.md** | Inventory of reusable skills | "List of available skills with descriptions" |
| **Code comments** | "Why", not "what" — only non-obvious behavior | "Refresh token rotation required due to 90-day expiry" |

### Compliance Checklist

Before starting a new initiative:

- [ ] Is this planning work (not operational docs)? → Goes in TODO.md
- [ ] Does it describe "what we're building"? → Belongs in TODO.md
- [ ] Does it describe "how the system works"? → Belongs in CLAUDE.md or README.md
- [ ] Have we considered blocking/dependencies? → Document in TODO.md "Notes" section
- [ ] Are phases/tasks broken down? → List in TODO.md "Tasks" section
- [ ] Do we have success criteria? → Document in TODO.md

### Git Integration

- TODO.md files are committed to `main` like any other source file
- Updates to TODO.md are part of regular commits (no separate planning commits)
- When work is complete, update TODO.md to move task to "Completed" section and commit

### Skill Integration

Planning enforcement is checked during:
- **Manual review**: Code reviewers verify planning docs follow this standard
- **Pre-push (optional)**: Can add a hook to warn on `plan.md` files or new planning docs outside TODO.md
- **Orchestrator handoff**: When delegating work, reference the TODO.md task specifically

### Rationale

**Why TODO.md only?**
1. Single source of truth — easier to find active work
2. Version controlled — planning evolves with code
3. Co-located with implementation — PR references the TODO.md task directly
4. Reduces friction — don't hunt for separate planning docs
5. Natural archiving — completed tasks in same file, easy to review what was done

**Why not multiple plan.md files?**
1. Scattered planning makes it hard to track what's active
2. Hard to keep in sync with actual code progress
3. Creates confusion about which document is current
4. Reduces discoverability (not in standard location)

---

## Checklist for New Initiatives

When starting a new feature or refactoring task:

1. **Find the right TODO.md** (workspace-level or service-level)
2. **Create a new section** under "In Progress"
3. **Include all elements**:
   - Status, owner, target completion
   - Overview and goals
   - Approach and phases
   - Success criteria
   - Known blockers/dependencies
4. **Link from code** (commit messages, code comments can reference "see {workspace-name}/TODO.md: spec-extract")
5. **Update as you go** (add sub-tasks as they become clear)
6. **Move to Completed** when finished (with checkmarks showing what was done)

---

## FAQ

**Q: Can I have multiple TODO.md files in a single repo?**  
A: No. One TODO.md per repository/workspace. If you need multiple sections, use headers.

**Q: Should high-level initiatives be in {workspace-name}/TODO.md or individual service TODOs?**  
A: If it spans multiple services → {workspace-name}/TODO.md. If it's service-specific → that service's TODO.md.

**Q: What if a feature is too big to fit in one TODO.md section?**  
A: Break it into multiple tasks in the same TODO.md, not separate files. Use sub-headings and link them.

**Q: Should we version the TODO.md (TODO-v1.md, TODO-v2.md)?**  
A: No. Single TODO.md, archive completed sections. Git history preserves old versions.

**Q: Is TODO.md only for engineering, or for ops/infra work too?**  
A: For all planned work. Deployments, infrastructure changes, spec extraction, etc. all go in TODO.md.

