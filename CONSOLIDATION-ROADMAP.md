# CONSOLIDATION-ROADMAP.md

**Date:** 2025-05-09  
**Author:** Senior Engineer  
**Status:** DESIGN — Awaiting Implementation  
**Purpose:** File-by-file plan for markdown consolidation, archival, and removal

---

## Overview

**Current tracked markdown files:** ~240  
**Target tracked markdown files:** <150  
**Reduction approach:** Archive session artifacts, remove redundant files, consolidate related docs

**Safety rule:** All files marked for removal must first be moved to `docs/archive/` in a dedicated commit. The removal commit happens only after a 2-week review period or explicit sign-off.

**Protected files (never touched):** `docs/SPEC.md`, `src/agents/*-agent.md`, `src/skills/*/SKILL.md`

---

## Archive Structure to Create

```
docs/archive/
├── README.md                    # Explains archive purpose and retrieval
├── phase5/                      # Phase 5.x implementation history
├── phase6-draft/                # Phase 6 forward-looking docs (not yet implemented)
├── sessions/                    # Session deliverables (audit summaries, handbacks)
├── legacy/                      # Superseded architecture and old guides
└── todo-history.md              # Completed TODO items (maintained by todo-maintenance skill)
```

---

## Root Level (5 files → 2 files)

| File | Action | Destination | Reason |
|------|--------|-------------|--------|
| `README.md` | KEEP | Root | Primary project documentation |
| `AUDIT-FINAL-SUMMARY.md` | ARCHIVE | `docs/archive/sessions/` | Session deliverable from May 2025 audit |
| `AUDIT-RENDERING-PIPELINE.md` | ARCHIVE | `docs/archive/sessions/` | Session deliverable; content absorbed into STRUCTURE-ARCHITECTURE.md |
| `STRUCTURE-ARCHITECTURE.md` | MOVE | `docs/decisions/ADR-structure-2025-05-09.md` | Is an ADR; belongs in decisions/ |
| `STRUCTURE-RECOMMENDATION.md` | ARCHIVE | `docs/archive/sessions/` | Superseded by STRUCTURE-ARCHITECTURE.md (the recommendation was implemented) |

**New root files (from this session):**
- `STANDARDS.md` — KEEP (permanent reference)
- `CLEANUP-STRATEGY.md` → MOVE to `docs/` after review (this document)
- `STANDARDS-DOCUMENTATION-PLAN.md` → ARCHIVE to `docs/archive/sessions/` after implementation
- `SKILL-SPECS.md` → MOVE to `docs/` after review (persistent reference)
- `CONSOLIDATION-ROADMAP.md` → ARCHIVE to `docs/archive/sessions/` after execution
- `CLEANUP-INVENTORY.md` → MOVE to `docs/` temporarily; archive once complete

**Root target state:**
```
README.md
STANDARDS.md
Makefile
.gitignore
.github/
```

---

## `docs/` Top Level (77 files → ~35 files)

### KEEP — Core Standing Documentation

| File | Keep Reason |
|------|-------------|
| `SPEC.md` | Protected system specification |
| `PROTOCOL.md` | Active protocol definition |
| `AGENTS.md` | Active agent routing reference |
| `QUALITY.md` | Active quality standards |
| `SYSTEM.md` | Active system overview |
| `SKILLS.md` | Active skills reference |
| `SKILLS-OVERVIEW.md` | Active skills overview |
| `ONBOARDING.md` | Active onboarding doc |
| `INSTALL.md` | Active install guide |
| `MANIFEST.md` | Active file manifest |
| `ENTRYPOINT.md` | Active entrypoint documentation |
| `HANDOFF.md` | Active handoff protocol |
| `DELEGATE-HANDBACK-QUALITY-GATES.md` | Active quality gate reference |
| `PROTOCOL-QUICK-REFERENCE.md` | Active quick reference |
| `AUTOMATIC-INVOCATION.md` | Active invocation reference |
| `AUTOMATION.md` | Active automation documentation |
| `SELF-CONTAINED-CONSTRAINT.md` | Active constraint documentation |
| `QUEUE-PROTOCOL.md` | Active queue protocol |
| `LOGGING-QUEUE-ARCHITECTURE.md` | Active architecture reference |
| `MODEL-SELECTION-STRATEGY.md` | Active model selection guide |
| `MODEL-CENTRALIZATION-INDEX.md` | Active model centralization reference |
| `AGENT-IMPLEMENTATION-GUIDE.md` | Active implementation guide |
| `AGENT-IMPLEMENTATION-CHECKLIST.md` | Active implementation checklist |
| `LEAD-REVIEW-PROCESS.md` | Active review process |
| `ORCHESTRATION-README.md` | Active orchestration documentation |
| `ORCHESTRATOR-CHECKLIST.md` | Active checklist |
| `TOKEN-USAGE-TRACKING.md` | Active tracking documentation |
| `FEEDBACK-LOOPS.md` | Active feedback loop documentation |
| `QUALITY-GATE-TEST-FRAMEWORK.md` | Active test framework |
| `SPEC-DRIVEN-QUALITY-GATE.md` | Active quality gate spec |
| `SPEC-VALIDATION-FRAMEWORK.md` | Active validation framework |
| `SPAN-CAPTURE-INTEGRATION.md` | Active span capture docs |
| `USAGE-BUDGET-INTEGRATION.md` | Active budget docs |
| `USAGE-BUDGET-MANAGER.md` | Active budget manager |
| `otel-schema.md` | Active observability schema |

### ARCHIVE → `docs/archive/sessions/` — Session Deliverables

| File | Archive Reason |
|------|---------------|
| `PRINCIPAL-ENGINEER-HANDBACK.md` | Session deliverable, not standing doc |
| `PRINCIPAL-ENGINEER-REVIEW-ACTIONS.md` | Session deliverable |
| `PRINCIPAL-ENGINEER-REVIEW-SUMMARY.md` | Session deliverable |
| `IMPLEMENTATION_REPORT.md` | Session deliverable |
| `DESIGN-DELIVERABLES.md` | Session deliverable |
| `CLEANUP-SECURITY-LOG.md` | Session log, not standing doc |
| `IMMEDIATE-ACTION-REQUIRED.md` | Session-specific urgency doc; likely stale |
| `PROTOCOL-REVIEW-SUMMARY.md` | Session review artifact |
| `PROTOCOL-IMPLEMENTATION-STATUS.md` | Session status; superseded by PROTOCOL.md |
| `AGENT-SPECS-WEEK1-DESIGNS.md` | Historical week 1 design doc (1,198 lines) |

### ARCHIVE → `docs/archive/phase5/` — Phase 5 Documentation

| File | Archive Reason |
|------|---------------|
| `PHASE-5.10-INTEGRATION-GUIDE.md` | Phase-specific; now in SPEC.md |

### ARCHIVE → `docs/archive/phase6-draft/` — Future Phase Docs

| File | Archive Reason |
|------|---------------|
| `PHASE-6-DELIVERABLES.md` | Future phase; not yet implemented |
| `PHASE-6-IMPLEMENTATION-ROADMAP.md` | Future phase; not yet implemented |
| `PHASE-6-INTEGRATION-GUIDE.md` | Future phase; not yet implemented |
| `PHASE-6-STATUS.md` | Future phase; not yet implemented |
| `PHASE-6-TASKS.md` | Future phase; not yet implemented |

### EVALUATE — Requires Human Decision

| File | Question |
|------|----------|
| `MSMTP-SETUP.md` | Is email/msmtp still used in production? |
| `MSMTP-UNATTENDED.md` | Same question as above |
| `HANDOFF.md` | Is this distinct from PROTOCOL.md? Possible merge candidate |
| `DESIGN-DELIVERABLES.md` | Is this a design artifact or standing doc? |

### CONSOLIDATE — Merge Into Single Files

**Model documentation** (7 files → 1 file `MODEL-REFERENCE.md`):
- `architecture-model-centralization.md` → archive after merge
- `model-centralization-design-summary.md` → archive after merge
- `model-centralization-migration-guide.md` → keep if migration still ongoing; else archive
- `model-configuration-guide.md` → keep (operational reference)
- `model-engineer-feedback-handler.md` → consolidate into MODEL-REFERENCE.md
- `model-implementation-roadmap.md` → archive (roadmap completed)
- `MODEL-CENTRALIZATION-INDEX.md` → keep as index pointing to MODEL-REFERENCE.md

**Queue enforcement** (5 files → 1 file, existing `QUEUE-PROTOCOL.md`):
- `architecture-queue-enforcement-5101.md` → archive
- `queue-enforcement-implementation-guide.md` → merge into QUEUE-PROTOCOL.md or archive
- `queue-enforcement-migration-guide.md` → archive (migration done)
- `queue-enforcement-rules.md` → keep or merge into QUEUE-PROTOCOL.md

**Continuous polling** (5 files → 1 file):
- `architecture-continuous-polling-5102.md` → archive
- `deployment-guide-continuous-polling.md` → keep (operational)
- `implementation-roadmap-continuous-polling-5102.md` → archive
- `troubleshooting-continuous-polling.md` → keep (operational)
- `usage-continuous-polling-automation.md` → keep or merge with deployment guide

**Quality gates** (3 files):
- `architecture-quality-gates-5103.md` → archive
- `quality-gate-activator.md` → keep or merge into QUALITY-GATE-TEST-FRAMEWORK.md
- `quality-gate-feedback-handler.md` → keep or merge

**Before-after documentation:**
- `pure-orchestrator-before-after.md` → archive (historical comparison)
- `architecture-pure-orchestrator.md` → archive (historical)

---

## `docs/guides/` (12 files → ~6 files)

| File | Action | Reason |
|------|--------|--------|
| `README.md` | KEEP | Directory index |
| `INDEX.md` | KEEP or MERGE into README | Possible duplicate of README |
| `CLAUDE.md` | KEEP | Active Claude Code guide |
| `SYSTEM_INTEGRATION.md` | KEEP | Active integration guide |
| `AUDIT_AGENTS_ROLES_SKILLS.md` | ARCHIVE `legacy/` | Audit artifact |
| `DEPLOYMENT_STATUS.md` | UPDATE then KEEP | Update to current status |
| `IMPLEMENTATION_COMPLETE.md` | ARCHIVE `sessions/` | Historical milestone doc |
| `ORCHESTRATION_v1_ARCHIVED.md` | ARCHIVE `legacy/` | Already superseded (name says so) |
| `WORKFLOW_TEST_EXAMPLE.md` | KEEP | Active example |
| `plan-implementer-legacy.md` | ARCHIVE `legacy/` | Explicitly legacy |
| `examples/` | KEEP | Active examples directory |

---

## `docs/decisions/` (1 file → 4+ files)

| File | Action | Reason |
|------|--------|--------|
| `ADR-model-centralization.md` | KEEP | Active ADR |
| `ADR-structure-2025-05-09.md` | CREATE | Move from root (STRUCTURE-ARCHITECTURE.md) |

Future ADRs to create:
- `ADR-queue-protocol.md` — Document queue enforcement decision
- `ADR-orchestrator-first.md` — Document ORCHESTRATOR-FIRST constraint

---

## `src/skills/` Non-Skill Markdown Files

### ARCHIVE → `docs/archive/phase5/` (19 files)

All PHASE-5.x files are implementation history, not skill definitions:
- `PHASE-5-COMPLETION-SUMMARY.md`
- `PHASE-5-DELEGATION-BRIEF-1.md` through `-5.md`
- `PHASE-5-EXECUTIVE-SUMMARY.md`
- `PHASE-5-INTEGRATION-GUIDE.md`
- `PHASE-5-ORCHESTRATION-TIMELINE.md`
- `PHASE-5-ORCHESTRATOR-STATUS.md`
- `PHASE-5-README.md`
- `PHASE-5-SKILL-SPECIFICATIONS.md`
- `PHASE-5.10-AGENT-BASED-ORCHESTRATION.md`
- `PHASE-5.10-IMPLEMENTATION-SUMMARY.md`
- `PHASE-5.10-MONITORING-PLAN.md`
- `PHASE-5.8-FINAL-COMPLETION.md`
- `PHASE-5.8-IMPLEMENTATION-LOG.md`
- `PHASE-5.8-SESSION-SUMMARY.md`
- `PHASE-5.8f-TESTING-REPORT.md`

### MOVE → `docs/` (2 files, if still relevant)

- `SDLC-ORCHESTRATOR-DIAGRAMS.md` → `docs/SDLC-ORCHESTRATOR-DIAGRAMS.md`
- `AGENTIC-ENGINEERS-ARCHITECTURE-DIAGRAMS.md` → `docs/ARCHITECTURE-DIAGRAMS.md`

### MERGE → `src/skills/README.md` (1 file)

- `SKILLS-INDEX.md` → Merge index content into README.md, then archive

### EVALUATE (4 files — requires human decision)

| File | Question |
|------|----------|
| `QUALITY-ENGINEER-DESIGN.md` | Is this still the active design? If yes → `docs/`; if historical → archive |
| `QUALITY-GATES-QUICK-REFERENCE.md` | Is this distinct from `docs/QUALITY-GATE-TEST-FRAMEWORK.md`? |
| `plan-iterate.md` | Is this an active planning template or historical artifact? |
| `planning-standard.md` | Is this an active standard or superseded? |

---

## Implementation Sequence

### Commit 1: Create archive structure
```bash
mkdir -p docs/archive/{phase5,phase6-draft,sessions,legacy}
echo "# Archive" > docs/archive/README.md
```

### Commit 2: Archive root-level session artifacts
```bash
git mv AUDIT-FINAL-SUMMARY.md docs/archive/sessions/
git mv AUDIT-RENDERING-PIPELINE.md docs/archive/sessions/
git mv STRUCTURE-RECOMMENDATION.md docs/archive/sessions/
git mv STRUCTURE-ARCHITECTURE.md docs/decisions/ADR-structure-2025-05-09.md
```

### Commit 3: Archive src/skills/ PHASE docs
```bash
git mv src/skills/PHASE-5*.md docs/archive/phase5/
git mv src/skills/PHASE-5.*.md docs/archive/phase5/
```

### Commit 4: Archive PHASE-6 forward-looking docs
```bash
git mv docs/PHASE-6-*.md docs/archive/phase6-draft/
```

### Commit 5: Archive session deliverables in docs/
```bash
git mv docs/PRINCIPAL-ENGINEER-HANDBACK.md docs/archive/sessions/
git mv docs/PRINCIPAL-ENGINEER-REVIEW-ACTIONS.md docs/archive/sessions/
git mv docs/PRINCIPAL-ENGINEER-REVIEW-SUMMARY.md docs/archive/sessions/
# ... etc
```

### Commit 6: Archive legacy guides
```bash
git mv docs/guides/ORCHESTRATION_v1_ARCHIVED.md docs/archive/legacy/
git mv docs/guides/plan-implementer-legacy.md docs/archive/legacy/
git mv docs/guides/AUDIT_AGENTS_ROLES_SKILLS.md docs/archive/legacy/
```

### Commit 7: Model documentation consolidation
- Merge 7 model docs → 1 MODEL-REFERENCE.md
- Archive source files

### Commit 8: Queue documentation consolidation
- Merge queue enforcement docs into QUEUE-PROTOCOL.md
- Archive source files

### Commit 9: Continuous polling consolidation
- Keep operational guides, archive historical/roadmap docs

### Commit 10: Run doc-quality skill
- Verify 0 broken links
- Verify naming convention compliance
- Fix any issues found

### Commit 11: Run make verify
- Confirm SPEC compliance maintained throughout

---

## Naming Convention Enforcement

Post-consolidation, enforce in `docs/`:
- `UPPER-CASE.md` = standing operational documentation (keep forever)
- `lower-case.md` = architecture decision notes, design documents (keep forever)
- Files in `docs/archive/` = no naming convention enforced (historical)

Audit all remaining `docs/` files for compliance after consolidation.

---

## Expected Outcome

| Metric | Before | After |
|--------|--------|-------|
| Root `.md` files | 5 (+6 from this session) | 2 (README.md, STANDARDS.md) |
| `docs/` top-level | 77 | ~35 |
| `docs/guides/` | 12 | ~6 |
| `docs/archive/` | 0 | ~50 |
| `src/skills/` non-skill | 25+ | <5 |
| Total tracked | ~240 | ~150 |

---

## Related Documents

- `CLEANUP-STRATEGY.md` — Phase 2 context
- `CLEANUP-INVENTORY.md` — Prioritized opportunities
- `docs/decisions/ADR-model-centralization.md` — ADR format example
