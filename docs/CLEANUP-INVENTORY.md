# CLEANUP-INVENTORY.md

**Date:** 2025-05-09  
**Author:** Senior Engineer  
**Status:** DESIGN — Prioritized list of cleanup opportunities  
**Total Opportunities:** 18 identified

---

## Overview

This document catalogs specific, actionable cleanup opportunities across the agentic-engineers repository. Each item includes a priority, effort estimate, and acceptance criteria.

Items are organized by priority. Once `todo-maintenance` skill is operational, this list will be imported into `TODO.md`.

---

## 🔴 Priority Opportunities (Do First)

### P1 — Create `TODO.md`
**Category:** Governance  
**Effort:** Small (1-2 hours)  
**Impact:** High — establishes single source of truth for all work items  

**Description:**  
No `TODO.md` exists in the repository. Work items are scattered across session deliverables, PHASE docs, HANDBACK files, and individual skill notes. Create the canonical TODO.md file with the structure defined in SKILL-SPECS.md.

**Acceptance Criteria:**
- [ ] `TODO.md` created at repository root
- [ ] Follows structure defined in SKILL-SPECS.md (skill 1)
- [ ] All Priority and Standard items from this inventory are listed
- [ ] `make verify` passes after creation

**Notes:** Pre-populate with items from this inventory and any pending items found in PHASE-6-TASKS.md before archiving that file.

---

### P2 — Archive `src/skills/` PHASE-5.x Documentation (19 files)
**Category:** Source Tree Hygiene  
**Effort:** Small (1 hour)  
**Impact:** High — 19 non-skill files polluting the skills source tree  

**Description:**  
The `src/skills/` directory contains 19 `PHASE-5*.md` files that are implementation history, not skill definitions. They were created during Phase 5 development sessions and never relocated. They confuse the skill index and make it harder to find actual skills.

**Acceptance Criteria:**
- [ ] `docs/archive/phase5/` directory created
- [ ] All 19 PHASE-5*.md files moved from `src/skills/` to `docs/archive/phase5/`
- [ ] `src/skills/README.md` updated to not reference archived files
- [ ] `make verify` passes (no rendering impact)
- [ ] No broken links in remaining docs

**Files to Move:** See CONSOLIDATION-ROADMAP.md for complete list.

---

### P3 — Archive Root-Level Session Audit Files (4 files)
**Category:** Root Directory Hygiene  
**Effort:** Small (30 minutes)  
**Impact:** Medium — root directory should only contain essential project files  

**Description:**  
Four files at the repository root are session deliverables from the May 2025 audit:
- `AUDIT-FINAL-SUMMARY.md` 
- `AUDIT-RENDERING-PIPELINE.md`
- `STRUCTURE-RECOMMENDATION.md`
- `STRUCTURE-ARCHITECTURE.md` (→ ADR in `docs/decisions/`)

**Acceptance Criteria:**
- [ ] `docs/archive/sessions/` directory created
- [ ] `AUDIT-*.md` and `STRUCTURE-RECOMMENDATION.md` moved to archive
- [ ] `STRUCTURE-ARCHITECTURE.md` moved to `docs/decisions/ADR-structure-2025-05-09.md`
- [ ] `README.md` links to these files (if any) updated
- [ ] Root directory contains only: `README.md`, `STANDARDS.md`, `Makefile`, `.gitignore`, `.github/`

---

### P4 — Create `docs/SPEC-CHANGELOG.md`
**Category:** Governance Infrastructure  
**Effort:** Small (30 minutes)  
**Impact:** Medium — required by `spec-management` skill; establishes audit trail for SPEC changes  

**Description:**  
`docs/SPEC.md` has been modified many times with no change log. Create `docs/SPEC-CHANGELOG.md` with a retroactive entry for the most recent known update (2026-05-02, Phase 5.10), and populate future entries using the `spec-management` skill.

**Acceptance Criteria:**
- [ ] `docs/SPEC-CHANGELOG.md` created
- [ ] Initial entry documents current SPEC.md state (version 1.0, Phase 5.10)
- [ ] Format matches template in SKILL-SPECS.md (skill 3)
- [ ] SPEC.md frontmatter updated with changelog reference

---

## 🟡 Standard Opportunities (Active Backlog)

### S1 — Create `STANDARDS.md`
**Category:** Standards Documentation  
**Effort:** Medium (2-4 hours)  
**Impact:** High — establishes standards alignment foundation  

**Description:**  
No `STANDARDS.md` exists. See STANDARDS-DOCUMENTATION-PLAN.md for full content plan. This is Phase 1 of the cleanup strategy.

**Acceptance Criteria:**
- [ ] `STANDARDS.md` created at repository root
- [ ] All 4 targeted standards documented (AGENTS.md, Claude Code, GitHub Copilot, agentskills.io)
- [ ] Compliance matrix complete with current status
- [ ] Roadmap section lists compliance gaps
- [ ] Links validated

---

### S2 — Add "Standards Compliance" Section to `README.md`
**Category:** Standards Documentation  
**Effort:** Small (30 minutes)  
**Impact:** Medium — README is the first touchpoint for new contributors  
**Depends on:** S1 (STANDARDS.md must exist first)

**Description:**  
`README.md` (1,326 lines) has no mention of standards alignment. Add a brief "Standards Compliance" section (5-10 lines + table) linking to STANDARDS.md.

**Acceptance Criteria:**
- [ ] "Standards Compliance" section added to README.md
- [ ] 4 standards listed in a table with links
- [ ] Link to STANDARDS.md included
- [ ] Existing README.md content unchanged
- [ ] Section placed logically (after Architecture, before Getting Started)

---

### S3 — Append "Standards Alignment" Section to `docs/SPEC.md`
**Category:** Standards Documentation  
**Effort:** Small (1 hour)  
**Impact:** Medium — SPEC.md is the authoritative system document  
**Authority Required:** Lead Engineer or Principal Engineer  
**Depends on:** S1, S2

**Description:**  
Append a new "Standards Alignment" section at the end of SPEC.md. No existing content changes. See STANDARDS-DOCUMENTATION-PLAN.md §2 for exact content.

**Acceptance Criteria:**
- [ ] "Standards Alignment" section appended to SPEC.md
- [ ] No existing SPEC.md content modified
- [ ] Standards table matches STANDARDS.md
- [ ] `make verify` passes
- [ ] Change logged in SPEC-CHANGELOG.md

---

### S4 — Archive PHASE-6 Forward-Looking Documents (6 files)
**Category:** Documentation Hygiene  
**Effort:** Small (30 minutes)  
**Impact:** Medium — PHASE-6 is not yet implemented; these docs create confusion  

**Description:**  
Six `PHASE-6-*.md` files in `docs/` describe planned but unimplemented future phases. They should be moved to `docs/archive/phase6-draft/` to make it clear they are drafts, not standing documentation.

**Before archiving:** Extract any remaining TODO items into `TODO.md`.

**Acceptance Criteria:**
- [ ] `docs/archive/phase6-draft/` created
- [ ] All 6 PHASE-6-*.md files moved to archive
- [ ] Any remaining TODO items captured in TODO.md
- [ ] No broken links in remaining docs

---

### S5 — Implement `todo-maintenance` Skill
**Category:** Skill Implementation  
**Effort:** Large (1-2 sessions)  
**Impact:** High — automates TODO.md maintenance going forward  
**Depends on:** P1 (TODO.md exists), SKILL-SPECS.md design approved  

**Description:**  
Implement the `todo-maintenance` skill per SKILL-SPECS.md §1. Use the `skill-creator` skill to scaffold, then implement the scripts.

**Acceptance Criteria:**
- [ ] `src/skills/todo-maintenance/SKILL.md` created (agentskills.io compliant)
- [ ] Scripts implemented and tested
- [ ] Skill renders to `~/.copilot/skills/todo-maintenance/` and `~/.claude/skills/todo-maintenance/`
- [ ] Integration test with sample HANDBACK files passes
- [ ] `make verify` passes

---

### S6 — Implement `doc-quality` Skill
**Category:** Skill Implementation  
**Effort:** Large (1-2 sessions)  
**Impact:** High — automated documentation quality gate  
**Depends on:** Phase 2 consolidation (clean baseline), SKILL-SPECS.md design approved  

**Description:**  
Implement the `doc-quality` skill per SKILL-SPECS.md §2. Start with link validation and cross-reference checks; add duplicate detection and staleness in v1.1.

**Acceptance Criteria:**
- [ ] `src/skills/doc-quality/SKILL.md` created (agentskills.io compliant)
- [ ] All 5 checks implemented (links, cross-refs, formatting, duplicates, staleness)
- [ ] SPEC.md correctly excluded from all checks
- [ ] PR creation for auto-fixes works
- [ ] `make verify` passes

---

### S7 — Implement `spec-management` Skill
**Category:** Skill Implementation  
**Effort:** Large (2-3 sessions)  
**Impact:** High — controlled SPEC.md modification process  
**Authority Required:** Principal Engineer design approval  
**Depends on:** S4 (SPEC-CHANGELOG.md exists), SKILL-SPECS.md design approved by PE  

**Description:**  
Implement the `spec-management` skill per SKILL-SPECS.md §3. This is the most sensitive of the three skills — requires Principal Engineer review of the authority model before implementation begins.

**Acceptance Criteria:**
- [ ] Authority model reviewed and approved by Principal Engineer
- [ ] `src/skills/spec-management/SKILL.md` created
- [ ] Authority validation rejects non-PE/LE delegates
- [ ] All 4 validation checks implemented
- [ ] SPEC-CHANGELOG.md updated on every successful change
- [ ] `make verify` passes

---

### S8 — Model Documentation Consolidation
**Category:** Documentation Consolidation  
**Effort:** Medium (2-4 hours)  
**Impact:** Medium — reduce 7 model docs to 1-2 clear references  
**Depends on:** Archive structure created (P3 done)  

**Description:**  
Consolidate scattered model documentation into a single `docs/MODEL-REFERENCE.md`. See CONSOLIDATION-ROADMAP.md for source files.

**Acceptance Criteria:**
- [ ] `docs/MODEL-REFERENCE.md` created with consolidated content
- [ ] Source files archived to `docs/archive/`
- [ ] `MODEL-CENTRALIZATION-INDEX.md` updated to reference new file
- [ ] No broken links
- [ ] `make verify` passes

---

### S9 — Queue Documentation Consolidation
**Category:** Documentation Consolidation  
**Effort:** Medium (2-4 hours)  
**Impact:** Medium — reduce 5 queue docs to 1-2 clear references  
**Depends on:** Archive structure created (P3 done)  

**Description:**  
Consolidate scattered queue enforcement documentation into `docs/QUEUE-PROTOCOL.md` (which already exists). Archive historical design and migration docs.

**Acceptance Criteria:**
- [ ] `docs/QUEUE-PROTOCOL.md` updated with any missing content from source files
- [ ] Historical/migration docs archived
- [ ] `QUEUE-PROTOCOL.md` is the single authoritative source for queue rules
- [ ] No broken links

---

## 🔵 Optional Opportunities (Nice to Have)

### O1 — Add ADR for Orchestrator-First Constraint
**Category:** Documentation Completeness  
**Effort:** Small (1-2 hours)  
**Impact:** Low — valuable for posterity, not urgent  

**Description:**  
The ORCHESTRATOR-FIRST constraint is a major architectural decision but has no ADR. Create `docs/decisions/ADR-orchestrator-first.md` documenting the decision, context, and consequences.

**Acceptance Criteria:**
- [ ] ADR follows same format as `docs/decisions/ADR-model-centralization.md`
- [ ] Documents context, decision, and consequences
- [ ] References SPEC.md section on ORCHESTRATOR-FIRST

---

### O2 — Add ADR for Queue Protocol
**Category:** Documentation Completeness  
**Effort:** Small (1-2 hours)  
**Impact:** Low — valuable for posterity  

**Description:**  
The file-based queue protocol is a significant design choice. Document it as `docs/decisions/ADR-queue-protocol.md`.

---

### O3 — Verify All SKILL.md Files for agentskills.io Compliance
**Category:** Standards Compliance  
**Effort:** Medium (2-4 hours)  
**Impact:** Medium — required for STANDARDS.md to honestly claim compliance  

**Description:**  
Audit all 148 `src/skills/` markdown files (specifically the `SKILL.md` files) for agentskills.io compliance. Check `name` field format, `description` length, required fields present. Report violations.

**Acceptance Criteria:**
- [ ] All SKILL.md files audited
- [ ] Violations listed in `TODO.md` as individual items
- [ ] At least critical violations (missing required fields) fixed

---

### O4 — Clarify or Consolidate `shared/` Directory
**Category:** Source Tree Hygiene  
**Effort:** Small (1 hour)  
**Impact:** Low — one file, unclear purpose  

**Description:**  
`shared/quality-assessment-baseline.md` (634 lines) exists at the root level `shared/` directory. It's unclear if this is still active or superseded by `src/skills/shared/core-engineering-baseline.md`. Evaluate and either consolidate or document the distinction.

**Acceptance Criteria:**
- [ ] Decision documented: keep both or consolidate
- [ ] If consolidate: merged into `src/skills/shared/` and `shared/` removed
- [ ] If keep both: README.md in `shared/` explains the distinction

---

### O5 — Fix Naming Convention Violations in `docs/`
**Category:** Documentation Hygiene  
**Effort:** Medium (2-4 hours)  
**Impact:** Low — cosmetic but improves navigation  
**Depends on:** Phase 2 consolidation complete  

**Description:**  
`docs/` mixes `UPPER-CASE.md` (standing docs) and `lower-case.md` (design notes) but the convention is not applied consistently. After consolidation, audit and rename violators.

**Acceptance Criteria:**
- [ ] All standing operational docs use UPPER-CASE.md
- [ ] All design notes and ADRs use lower-case.md
- [ ] All internal links updated after renames
- [ ] `doc-quality` skill validates going forward

---

### O6 — Add `make check-standards` Target
**Category:** CI/CD  
**Effort:** Medium (2-4 hours)  
**Impact:** Low-Medium — encodes compliance checks in build system  
**Depends on:** STANDARDS.md exists, `doc-quality` skill operational  

**Description:**  
Add a Makefile target `make check-standards` that verifies agentskills.io compliance for all SKILL.md files, validates copilot-instructions.md, and runs basic link checking. This should be fast (<30 seconds) and run in CI.

**Acceptance Criteria:**
- [ ] `make check-standards` target added to Makefile
- [ ] Checks SKILL.md name/description fields
- [ ] Checks for dead internal links
- [ ] Runs in CI (`.github/workflows/`)
- [ ] Fast enough for pre-commit hook

---

## 🔮 Future Opportunities (Not Yet Scheduled)

### F1 — Structured YAML Schema for AGENTS.md
**Category:** Standards Enhancement  
**Effort:** Large  

**Description:**  
The `AGENTS.md` routing decision tree is currently structured prose. For machine-parseability (agentskills.io and future automation), consider a YAML schema alongside or replacing the prose format.

---

### F2 — Automated Dead Link Monitoring in CI
**Category:** CI/CD  
**Effort:** Medium  

**Description:**  
Add GitHub Actions job that runs weekly, checks all external links in docs/, and creates an issue if dead links found. Complements the `doc-quality` skill (which checks at modification time).

---

### F3 — Documentation Coverage Metrics
**Category:** Observability  
**Effort:** Large  

**Description:**  
Track documentation coverage: what % of skills have usage examples, what % of agents have troubleshooting guides, what % of architecture decisions have ADRs. Emit as Prometheus metrics via `metrics-etl` skill.

---

## Summary Table

| ID | Category | Priority | Effort | Impact |
|----|----------|----------|--------|--------|
| P1 | Governance | 🔴 Priority | Small | High |
| P2 | Source Tree | 🔴 Priority | Small | High |
| P3 | Root Hygiene | 🔴 Priority | Small | Medium |
| P4 | Governance Infra | 🔴 Priority | Small | Medium |
| S1 | Standards Docs | 🟡 Standard | Medium | High |
| S2 | Standards Docs | 🟡 Standard | Small | Medium |
| S3 | Standards Docs | 🟡 Standard | Small | Medium |
| S4 | Doc Hygiene | 🟡 Standard | Small | Medium |
| S5 | Skill Impl | 🟡 Standard | Large | High |
| S6 | Skill Impl | 🟡 Standard | Large | High |
| S7 | Skill Impl | 🟡 Standard | Large | High |
| S8 | Doc Consolidation | 🟡 Standard | Medium | Medium |
| S9 | Doc Consolidation | 🟡 Standard | Medium | Medium |
| O1 | Doc Completeness | 🔵 Optional | Small | Low |
| O2 | Doc Completeness | 🔵 Optional | Small | Low |
| O3 | Standards | 🔵 Optional | Medium | Medium |
| O4 | Source Tree | 🔵 Optional | Small | Low |
| O5 | Doc Hygiene | 🔵 Optional | Medium | Low |
| O6 | CI/CD | 🔵 Optional | Medium | Low-Med |
| F1 | Standards | 🔮 Future | Large | — |
| F2 | CI/CD | 🔮 Future | Medium | — |
| F3 | Observability | 🔮 Future | Large | — |

---

## Related Documents

- `CLEANUP-STRATEGY.md` — Phase-by-phase implementation plan
- `CONSOLIDATION-ROADMAP.md` — File-by-file consolidation decisions
- `SKILL-SPECS.md` — Design specs for S5, S6, S7
- `STANDARDS-DOCUMENTATION-PLAN.md` — Details for S1, S2, S3
