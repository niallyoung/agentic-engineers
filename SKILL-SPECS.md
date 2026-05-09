# SKILL-SPECS.md

**Date:** 2025-05-09  
**Author:** Senior Engineer  
**Status:** DESIGN — Not Yet Implemented  
**Purpose:** Design specifications for three new agentic-engineers skills

---

## Overview

Three new skills are proposed to automate documentation governance. These specs follow the [agentskills.io specification](https://agentskills.io/specification) and the existing patterns in `src/skills/skill-creator/SKILL.md`.

All three skills are **design-only** at this stage. Implementation requires:
1. Principal Engineer review of `spec-management` skill authority model
2. Lead Engineer approval to add skills that modify `TODO.md` or `SPEC.md`
3. Normal delegation flow through Orchestrator for implementation

---

## Skill 1: `todo-maintenance`

### Purpose
Maintain `TODO.md` as the single source of truth for all approved, pending work items across the agentic-engineers project. Prevents TODO proliferation into ad-hoc notes, session deliverables, and individual skill files.

### SKILL.md Frontmatter
```yaml
---
name: todo-maintenance
description: Maintains TODO.md with approved work items from delegation queue. Organizes items by priority and status, archives completed items, and flags stale items. Triggered on HANDBACK completion or daily schedule. Use when TODO.md needs updating after a session or when new approved items need tracking.
license: Proprietary
compatibility: agentic-engineers framework v5.10+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: governance
  role: orchestrator
  trigger: daily | on-handback
---
```

### Inputs
| Input | Format | Source | Required |
|-------|--------|--------|----------|
| Approved delegations | HANDBACK YAML files in `artifacts/queue/done/` | Orchestrator | Yes |
| Current `TODO.md` | Markdown file at repo root | Filesystem | Yes |
| Quality gate results | QE HANDBACK files | Quality Engineer | No |
| Date | ISO-8601 | System | Yes |

### Outputs
| Output | Format | Destination |
|--------|--------|-------------|
| Updated `TODO.md` | Markdown | Repository root |
| Change summary | Text | HANDBACK to Orchestrator |
| Archived items | Appended to `docs/archive/todo-history.md` | Archive |

### TODO.md Structure (Enforced by This Skill)

```markdown
# TODO

**Last Updated:** YYYY-MM-DD  
**Updated By:** todo-maintenance skill

---

## 🔴 Priority (Must Do Next)
<!-- Items that block other work or are critically overdue -->

- [ ] **[ID]** Title — brief description — *Owner: Role* — *Added: YYYY-MM-DD*

## 🟡 Standard (Active Backlog)
<!-- Normal priority work items, approved and queued -->

- [ ] **[ID]** Title — brief description — *Owner: Role* — *Added: YYYY-MM-DD*

## 🔵 Optional (Nice to Have)
<!-- Low priority; do only when Priority/Standard queues are clear -->

- [ ] **[ID]** Title — brief description — *Owner: Role* — *Added: YYYY-MM-DD*

## 🔮 Future (Not Yet Scheduled)
<!-- Ideas approved in principle but not yet scheduled -->

- [ ] **[ID]** Title — brief description — *Added: YYYY-MM-DD*

---

## ✅ Recently Completed (Last 30 Days)
<!-- Auto-maintained: items completed in last 30 days -->

- [x] **[ID]** Title — *Completed: YYYY-MM-DD* — *PR: #N*
```

### Classification Rules

The skill applies these classification rules when processing new items:

| Classification | Criteria |
|----------------|----------|
| 🔴 Priority | Blocks other work; security issue; production bug; overdue >7 days |
| 🟡 Standard | Normal backlog item; newly approved; standards compliance |
| 🔵 Optional | Quality-of-life; documentation cleanup; nice-to-have |
| 🔮 Future | Approved in principle; no estimate; no owner assigned |

### Trigger Conditions
1. **On HANDBACK:** When any HANDBACK is received, check if new TODO items are referenced
2. **Daily:** Scan all HANDBACKs from last 24h, update TODO.md
3. **On Request:** Orchestrator can invoke directly via DELEGATE

### Constraints
- **Never deletes** items from TODO.md — only moves to "Recently Completed" or archives
- **Never modifies** item descriptions — only classification and status
- **Always produces** a HANDBACK with a diff summary of changes made
- **Does not create** TODO items from its own judgment — only from approved sources

### Directory Structure
```
src/skills/todo-maintenance/
├── SKILL.md
├── scripts/
│   ├── parse-handbacks.py     # Extract new items from HANDBACK files
│   ├── classify-items.py      # Apply classification rules
│   └── update-todo.py         # Write updated TODO.md
└── references/
    └── CLASSIFICATION-RULES.md
```

---

## Skill 2: `doc-quality`

### Purpose
Automated documentation quality verification. Runs during quality gate checks to ensure all `.md` files in `docs/` meet consistency, accuracy, and freshness standards. Produces actionable reports, not just warnings.

### SKILL.md Frontmatter
```yaml
---
name: doc-quality
description: Validates documentation quality across all .md files in docs/. Checks for dead links, cross-reference consistency, formatting uniformity, duplicate content, and stale information. Produces a cleanup report and optionally creates a PR with auto-fixable issues. Use during quality gate checks or when documentation is modified.
license: Proprietary
compatibility: agentic-engineers framework v5.10+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: quality
  role: quality-engineer
  trigger: on-docs-change | weekly
---
```

### Inputs
| Input | Format | Source | Required |
|-------|--------|--------|----------|
| `docs/` directory | Filesystem tree | Repository | Yes |
| Root `.md` files | Markdown files | Repository root | Yes |
| `src/skills/` docs | Markdown files | Source tree | Yes |
| Git history | `git log` output | Git | No (for staleness detection) |

### Outputs
| Output | Format | Destination |
|--------|--------|-------------|
| Quality report | Markdown | HANDBACK body |
| Auto-fix PR | GitHub PR | Repository |
| Violation list | JSON | `artifacts/doc-quality/YYYY-MM-DD.json` |

### Checks Performed

#### Check 1: Link Validation
- **What:** All internal `[text](path)` links resolve to existing files
- **What:** All external `[text](https://...)` links return HTTP 2xx
- **How:** Parse markdown, extract links, verify with filesystem + curl
- **Severity:** Internal dead links = ERROR; External dead links = WARNING

#### Check 2: Cross-Reference Consistency
- **What:** Files referenced in `docs/SPEC.md`, `README.md`, `STANDARDS.md` exist
- **What:** Agent names in `AGENTS.md` match files in `src/agents/`
- **What:** Skill names in `SKILLS-INDEX.md` match directories in `src/skills/`
- **How:** Parse reference documents, diff against filesystem
- **Severity:** Missing referenced file = ERROR; Stale reference = WARNING

#### Check 3: Formatting Uniformity
- **What:** All heading levels are consistent (no H1 → H3 jumps)
- **What:** Code blocks have language specifiers
- **What:** Tables are properly formatted (consistent column counts)
- **How:** AST parsing of markdown
- **Severity:** All = WARNING (auto-fixable)

#### Check 4: Duplicate Content Detection
- **What:** Sections with >70% content similarity across files
- **What:** Identical code blocks appearing in 3+ files
- **How:** N-gram similarity scoring
- **Severity:** WARNING (human decision required for resolution)

#### Check 5: Staleness Detection
- **What:** Files not modified in >180 days that contain "status" or "current"
- **What:** Files with dates in the past + "current status" language
- **How:** `git log --since=180.days.ago` + date pattern matching
- **Severity:** WARNING (flagged for human review, not auto-deleted)

### Constraints
- **Never modifies** `docs/SPEC.md` — explicitly excluded from all checks
- **Never auto-merges** PRs — creates PR with human required to merge
- **Never deletes** files — only flags for human decision
- **Reports only** actionable issues — no style bikeshedding

### Auto-Fix Scope (PR Only)

The skill may auto-fix in a PR:
- Broken internal links where the target file moved (has a clear rename mapping)
- Code blocks missing language specifiers (can infer from content)
- Table formatting (whitespace only)

All auto-fixes are in a dedicated PR branch: `docs/doc-quality-fixes-YYYY-MM-DD`

### Directory Structure
```
src/skills/doc-quality/
├── SKILL.md
├── scripts/
│   ├── check-links.py           # Link validation
│   ├── check-cross-refs.py      # Cross-reference consistency
│   ├── check-formatting.py      # Formatting uniformity
│   ├── check-duplicates.py      # Duplicate detection
│   ├── check-staleness.sh       # Staleness via git log
│   └── generate-report.py       # Aggregate + format report
└── references/
    ├── EXCLUDED-FILES.md         # Files exempt from checks (e.g., SPEC.md)
    └── SEVERITY-LEVELS.md
```

---

## Skill 3: `spec-management`

### Purpose
Provide a controlled, audited interface for managing changes to `docs/SPEC.md`. SPEC.md is the highest-authority document in the system — it defines the architecture, constraints, and operating rules that all agents must follow. Changes must be justified, reviewed, and logged.

### SKILL.md Frontmatter
```yaml
---
name: spec-management
description: Controlled management of docs/SPEC.md. Only invoke when Principal Engineer or Lead Engineer has explicitly approved a SPEC.md change. Validates proposed changes for internal consistency, backward compatibility, and cross-reference integrity. Produces change log and impact analysis. Any invocation without explicit PE/LE approval will be rejected.
license: Proprietary
compatibility: agentic-engineers framework v5.10+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: governance
  role: principal-engineer
  authority: principal-engineer | lead-engineer
---
```

### Authority Model

This skill enforces the following authority model:

```
Principal Engineer ──→ Can propose + approve SPEC changes
Lead Engineer      ──→ Can propose + approve SPEC changes
                        (except changes to "Standards Alignment" section)
Senior Engineer    ──→ Can propose ONLY; requires PE/LE approval
Engineer           ──→ Cannot propose or approve SPEC changes
```

Any DELEGATE to this skill must include:
```yaml
authority: principal-engineer | lead-engineer
approver: <name/role of approving PE or LE>
approval_evidence: <HANDBACK ID or explicit statement of approval>
```

If authority is not present or invalid, the skill rejects the request and returns an error HANDBACK.

### Inputs
| Input | Format | Source | Required |
|-------|--------|--------|----------|
| Proposed change | Diff or section description | Delegating agent | Yes |
| Authority evidence | HANDBACK ID or statement | Delegating agent | Yes |
| Justification | Free text | Delegating agent | Yes |
| Impact scope | List of affected components | Delegating agent | Yes |

### Outputs
| Output | Format | Destination |
|--------|--------|-------------|
| Change log entry | Markdown | Appended to `docs/SPEC-CHANGELOG.md` |
| Impact analysis | Markdown | HANDBACK body |
| Updated SPEC.md | Modified file | `docs/SPEC.md` (if approved) |
| Rejection notice | HANDBACK | Orchestrator (if not approved) |

### Validation Checks (Before Any Modification)

#### Check 1: Internal Consistency
- All agent roles named in proposed change match entries in `src/agents/`
- All queue paths referenced are valid filesystem paths
- All model names match entries in `src/config/models.yaml`
- No contradictions with existing SPEC sections

#### Check 2: Backward Compatibility Analysis
- Identify all existing code, skills, and agents that depend on the section being changed
- Flag breaking changes explicitly
- Require explicit acknowledgment of each breaking change in the DELEGATE

#### Check 3: Cross-Reference Integrity
- Ensure all internal SPEC.md cross-references (`## Section Name`) still resolve after change
- Ensure all external documents referencing the changed section are flagged for update
- Generate list of documents that need follow-up updates

#### Check 4: Standards Alignment Preservation
- If change touches "Standards Alignment" section, require Principal Engineer (not just LE)
- Ensure change doesn't reduce compliance with any targeted standard

### Change Log Format (SPEC-CHANGELOG.md)

```markdown
## YYYY-MM-DD — Change Description

**Approved By:** Principal Engineer / Lead Engineer  
**Approval Evidence:** HANDBACK-YYYYMMDD-NNNN  
**Section Changed:** `## Section Name`  
**Type:** [Addition | Modification | Deprecation | Removal]

### Summary
Brief description of what changed and why.

### Impact
- Affected agents: [list]
- Affected skills: [list]
- Breaking changes: [none | list with mitigation]

### Follow-Up Required
- [ ] Update docs/X.md to reflect change
- [ ] Update src/agents/Y-agent.md
```

### Workflow

```
1. Proposer creates DELEGATE to spec-management with:
   - Proposed change (diff or description)
   - Justification
   - Authority evidence (PE/LE approval)
   
2. spec-management validates:
   - Authority present and valid → else REJECT
   - Change parses cleanly → else REJECT
   - Runs validation checks (consistency, compatibility, cross-refs)
   
3. If validation passes:
   - Applies change to SPEC.md
   - Appends to SPEC-CHANGELOG.md
   - Creates follow-up TODO items for cross-reference updates
   - Returns HANDBACK with impact analysis
   
4. If validation fails:
   - Returns REJECT HANDBACK with specific failure reasons
   - Does NOT modify SPEC.md
   - Suggests remediation
```

### Directory Structure
```
src/skills/spec-management/
├── SKILL.md
├── scripts/
│   ├── validate-authority.py      # Check PE/LE approval
│   ├── validate-consistency.py    # Internal SPEC consistency
│   ├── analyze-impact.py          # Impact analysis
│   ├── check-compat.py            # Backward compatibility
│   └── apply-change.py            # Write change + changelog
└── references/
    ├── AUTHORITY-MODEL.md
    └── VALIDATION-RULES.md
```

---

## Implementation Notes

### Order of Implementation
1. `todo-maintenance` first (simplest, highest value, safe)
2. `doc-quality` second (read-only initially, add PR creation later)
3. `spec-management` last (requires PE review of authority model)

### Dependencies
- All three skills depend on the `docs/archive/` structure being in place (Phase 2)
- `doc-quality` depends on `STANDARDS.md` existing (Phase 1)
- `spec-management` depends on `docs/SPEC-CHANGELOG.md` being created as part of setup

### Testing Strategy
Each skill needs:
- Unit tests for each check/validation function
- Integration test with sample docs/SPEC.md/TODO.md
- Edge case tests (empty inputs, malformed markdown, missing authority)
- Regression test to ensure `doc-quality` never modifies SPEC.md

### Skill Creator Compliance
All three skills will be created using the `skill-creator` skill to ensure agentskills.io compliance.

---

## Related Documents

- `CLEANUP-STRATEGY.md` — Phase 3 context for these skills
- `src/skills/skill-creator/SKILL.md` — Template and process for creating skills
- `docs/SPEC.md` — Specification that `spec-management` protects
- `CONSOLIDATION-ROADMAP.md` — Precondition for `doc-quality` (clean baseline)
