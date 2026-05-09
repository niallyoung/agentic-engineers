# CLEANUP-STRATEGY.md

**Date:** 2025-05-09  
**Author:** Senior Engineer  
**Status:** DESIGN PHASE — Implementation Pending  
**Scope:** Documentation cleanup, standards alignment, skill design, and repository hygiene

---

## Executive Summary

The agentic-engineers repository has accumulated **~240 markdown files** across 6+ directory levels after 6 phases of development. This strategy defines a structured, phased approach to bring documentation into a maintainable, standards-compliant state without disrupting the production system.

**Guiding Principle:** _Documentation serves the reader, not the writer._ Historical artifacts, session deliverables, and phase reports should be archived or removed unless they contain information essential to understanding or operating the system today.

**Scope Exclusion:** `docs/SPEC.md` is managed exclusively by Principal Engineer or Lead Engineer. No changes to SPEC.md except via the controlled process described in Phase 3.

---

## Current State Assessment

### File Counts
| Location | Count | Health |
|----------|-------|--------|
| Root level `.md` files | 5 | ⚠️ 4 are session audit artifacts |
| `docs/` top level | 77 | ❌ Too many; mixed naming conventions |
| `docs/guides/` | 12 | ⚠️ Some stale/archived |
| `docs/decisions/` | 1 | ✅ Good structure, needs growth |
| `src/skills/` PHASE docs | 19 | ❌ Session artifacts in source dir |
| `src/skills/` total | 148 | ⚠️ Many non-skill docs mixed in |

**Total:** ~240 markdown files tracked in the repository.

### Key Problems Identified
1. **Session artifacts at root** — AUDIT-*.md, STRUCTURE-*.md are session deliverables that belong in docs/decisions/ or an archive
2. **19 PHASE-5.x docs in `src/skills/`** — Implementation logs polluting the skills source tree
3. **Mixed naming conventions** — `docs/` mixes `UPPERCASE.md` and `lowercase.md` with no clear distinction
4. **PHASE-6 forward-looking docs** — 6 files in `docs/` describing unimplemented future phases
5. **Principal Engineer session artifacts** — PRINCIPAL-ENGINEER-HANDBACK.md, REVIEW-ACTIONS.md, REVIEW-SUMMARY.md are session deliverables, not standing documentation
6. **Stale operational guides** — IMMEDIATE-ACTION-REQUIRED.md, MSMTP-SETUP.md, MSMTP-UNATTENDED.md have unclear current relevance
7. **No standards documentation** — No STANDARDS.md or alignment section in SPEC.md/README.md
8. **No TODO.md** — No centralized tracking of approved work items

---

## Phase 1: Standards Documentation

**Goal:** Create authoritative documentation of which AI agent ecosystem standards the framework targets.

**Priority:** Medium  
**Estimated effort:** 1 session  
**Dependencies:** None

### 1.1 Update `docs/SPEC.md`
- **Action:** Append a new "Standards Alignment" section at the end (no existing logic changes)
- **Owner:** Lead Engineer or Principal Engineer only
- **Content:** List all targeted standards, compliance criteria, and links
- **Constraint:** SPEC.md is protected — only append, never modify existing sections

### 1.2 Update `README.md`
- **Action:** Add "Standards Compliance" section with brief summary + link to STANDARDS.md
- **Owner:** Senior Engineer or above
- **Content:** 3-5 bullet points naming key standards; link to detailed STANDARDS.md

### 1.3 Create `STANDARDS.md` (new file)
- **Action:** Create comprehensive standards reference document
- **Location:** Repository root (parallel to README.md)
- **Content:** Compliance matrix, roadmap, contribution guide
- **Details:** See STANDARDS-DOCUMENTATION-PLAN.md

---

## Phase 2: Documentation Consolidation

**Goal:** Reduce doc count by 40-50% through principled consolidation and archival.

**Priority:** Low-Medium  
**Estimated effort:** 2-3 sessions  
**Dependencies:** Phase 1 complete (so SPEC.md is clean before reorganization)

### 2.1 Establish Naming Convention

Going forward, all `docs/` files must follow one of two conventions:
- **`UPPER-CASE.md`** — Standing documentation (operational, reference, specification)
- **`lower-case.md`** — Architecture decision records and design notes (informational only)

This convention already exists partially in `docs/`; we need to enforce it and rename violators.

### 2.2 Create Archive Structure

```
docs/archive/
├── phase5/          ← All PHASE-5.x docs from src/skills/
├── phase6-draft/    ← PHASE-6 forward-looking docs (not yet implemented)
├── sessions/        ← Session deliverables (PRINCIPAL-ENGINEER-*.md, AUDIT-*.md)
└── legacy/          ← ORCHESTRATION_v1, plan-implementer-legacy, etc.
```

### 2.3 Root-Level Cleanup

Move these 4 root files → `docs/decisions/` or `docs/archive/sessions/`:
- `AUDIT-FINAL-SUMMARY.md` → `docs/archive/sessions/`
- `AUDIT-RENDERING-PIPELINE.md` → `docs/archive/sessions/`
- `STRUCTURE-ARCHITECTURE.md` → `docs/decisions/ADR-structure-2025-05-09.md`
- `STRUCTURE-RECOMMENDATION.md` → `docs/archive/sessions/`

Root should contain only: `README.md`, `STANDARDS.md`, `Makefile`, `.gitignore`

### 2.4 `src/skills/` Cleanup

All PHASE-*.md files must leave the skills source tree:
- **19 PHASE-5.x files** → `docs/archive/phase5/`
- SDLC-ORCHESTRATOR-DIAGRAMS.md → `docs/` (if still relevant) or archive
- AGENTIC-ENGINEERS-ARCHITECTURE-DIAGRAMS.md → `docs/` (if still relevant) or archive
- QUALITY-ENGINEER-DESIGN.md, QUALITY-GATES-QUICK-REFERENCE.md → `docs/` if still active
- SKILLS-INDEX.md → merge into `src/skills/README.md`

### 2.5 `docs/guides/` Cleanup

- `ORCHESTRATION_v1_ARCHIVED.md` → `docs/archive/legacy/`
- `plan-implementer-legacy.md` → `docs/archive/legacy/`
- `DEPLOYMENT_STATUS.md` → update and keep or archive
- Remaining guides: evaluate relevance, consolidate where possible

### 2.6 Consolidation Targets in `docs/`

See CONSOLIDATION-ROADMAP.md for detailed file-by-file decisions.

---

## Phase 3: Skill Design and Implementation

**Goal:** Encode documentation discipline into the automated quality pipeline.

**Priority:** Medium  
**Estimated effort:** 3-4 sessions  
**Dependencies:** Phase 2 complete (clean baseline)

Three new skills will be designed and then implemented:

### 3.1 `todo-maintenance` Skill
Manages `TODO.md` — the single source of truth for approved work items.
See SKILL-SPECS.md for full specification.

### 3.2 `doc-quality` Skill
Automated documentation quality checks (links, consistency, duplicates, freshness).
See SKILL-SPECS.md for full specification.

### 3.3 `spec-management` Skill
Controlled, audited access to SPEC.md modifications.
See SKILL-SPECS.md for full specification.

---

## Phase 4: Cleanup Inventory Execution

**Goal:** Act on the specific cleanup opportunities identified in CLEANUP-INVENTORY.md.

**Priority:** Low (after Phases 1-3)  
**Estimated effort:** 1-2 sessions  
**Dependencies:** Phases 1-3 complete, skills operational

### 4.1 Execute consolidations per CONSOLIDATION-ROADMAP.md
### 4.2 Create `TODO.md` with items from CLEANUP-INVENTORY.md
### 4.3 Run `doc-quality` skill to verify clean baseline
### 4.4 Verify SPEC compliance after all changes

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Root-level `.md` files | 5 | 2 (README.md, STANDARDS.md) |
| Total `.md` files (tracked) | ~240 | <150 |
| `src/skills/` non-skill `.md` files | 25+ | <5 |
| Broken internal links | Unknown | 0 |
| Naming convention violations | Many | 0 |
| Standards documented | 0 | ≥4 |
| SPEC compliance | ✅ | ✅ (maintained) |

---

## Constraints and Guard Rails

1. **SPEC.md is protected** — Only append via Lead/Principal approval. Never modify existing sections without explicit sign-off.
2. **No breaking changes to rendering pipeline** — `src/skills/*/SKILL.md` and `src/agents/*-agent.md` are consumed by renderer; their locations and formats must not change.
3. **Archive before delete** — All removals go to `docs/archive/` in a dated commit before the delete commit. This allows rollback.
4. **Test after each phase** — Run `make verify` and full test suite after each phase to confirm SPEC compliance and zero regressions.
5. **docs/decisions/ ADRs are permanent** — Architecture Decision Records are never deleted, only superseded.

---

## Implementation Order

```
Phase 1 (Standards Docs)
    ↓
Phase 2 (Consolidation)  ←── depends on Phase 1 complete
    ↓
Phase 3 (Skill Design)   ←── parallel to Phase 2 (design while doing Phase 2)
    ↓
Phase 3 (Skill Impl)     ←── depends on Phase 2 complete
    ↓
Phase 4 (Inventory)      ←── depends on Phase 3 skills operational
```

---

## Related Documents

- `STANDARDS-DOCUMENTATION-PLAN.md` — Detailed plan for Phase 1
- `SKILL-SPECS.md` — Skill design specifications for Phase 3
- `CONSOLIDATION-ROADMAP.md` — File-by-file plan for Phase 2
- `CLEANUP-INVENTORY.md` — Prioritized list of cleanup opportunities
- `docs/SPEC.md` — System specification (protected)
- `docs/decisions/ADR-model-centralization.md` — Example ADR format
