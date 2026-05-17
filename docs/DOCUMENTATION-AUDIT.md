# Documentation Audit — May 2026

**Audited:** 2026-05-17  
**Auditor:** Lead Engineer  
**Scope:** All documentation files across repo root and `docs/`

---

## Summary

| Category | Count | Action |
|----------|-------|--------|
| Root-level implementation reports | 10 | Move to `docs/archive/phase-reports/` |
| `docs/` active files | ~145 | Categorized below |
| `docs/archive/` files | 17 | Retain as-is |
| Stale/redundant docs | ~30 | Flag for archival |
| Missing docs | 4 | Create (quick-start guides, index) |

---

## Root-Level Clutter (Move to Archive)

These files should not be in the repo root — they are implementation reports from past phases:

| File | Destination |
|------|-------------|
| `BUDGET_CHECKER_IMPLEMENTATION.md` | `docs/archive/phase-reports/` |
| `CODE-REVIEW-CHECKLIST.md` | `docs/archive/phase-reports/` |
| `COST-ATTRIBUTION-IMPLEMENTATION.md` | `docs/archive/phase-reports/` |
| `DRY_RUN_COMPLETION_REPORT.md` | `docs/archive/phase-reports/` |
| `FUNCTION_DESIGN_ANALYSIS.md` | `docs/archive/phase-reports/` |
| `IMPLEMENTATION_SUMMARY_DRY_RUN.md` | `docs/archive/phase-reports/` |
| `IMPLEMENTATION_SUMMARY_TOKEN_COST_ALERTS.md` | `docs/archive/phase-reports/` |
| `IMPLEMENTATION_SUMMARY_TOKEN_TRACKER.md` | `docs/archive/phase-reports/` |
| `ORCHESTRATOR_CLI_IMPLEMENTATION.md` | `docs/archive/phase-reports/` |
| `ORCHESTRATOR_CLI_QUICK_REFERENCE.md` | `docs/` (keep — useful reference) |
| `SHADOW_MODE_IMPLEMENTATION_SUMMARY.md` | `docs/archive/phase-reports/` |
| `TOKEN_COST_ALERTS_COMPLETION.md` | `docs/archive/phase-reports/` |

---

## Active docs/ Files (Keep)

### Core Protocol
- `docs/SPEC.md` — Implementation specification (source of truth)
- `docs/AGENTS.md` — Agent routing reference
- `docs/HANDOFF.md` — DELEGATE/HANDBACK format
- `docs/PROTOCOL.md` — Queue protocol
- `docs/QUEUE-PROTOCOL.md` — Queue mechanics
- `docs/SKILLS.md` — Skills overview
- `docs/QUALITY.md` — Quality gates

### Installation & Setup
- `docs/OPENCODE-INSTALL.md`
- `docs/CLAUDE-INSTALL.md`
- `docs/INSTALL.md`
- `docs/ONBOARDING.md`

### Operations
- `docs/TOKEN-COST-MONITORING.md`
- `docs/TOKEN-USAGE-TRACKING.md`
- `docs/USAGE-BUDGET-MANAGER.md`
- `docs/SHADOW_MODE.md`
- `docs/TROUBLESHOOTING.md`

### Enforcement
- `docs/SDLC-HOOKS.md`
- `docs/BYPASS-PROCEDURES.md`
- `docs/WORKFLOW.md`

---

## Stale / Redundant Docs (Candidates for Archive)

These docs reference old phase numbers, outdated paths, or are superseded:

- `docs/PHASE-3-*.md` (7 files) — Phase 3 planning docs, now complete
- `docs/PHASE-4-*.md` (5 files) — Phase 4 design docs, superseded by implementation
- `docs/HARNESS-*.md` (4 files) — Harness analysis, superseded by OPENCODE-INSTALL.md
- `docs/IMPLEMENTATION-SUMMARY.md` — Superseded by SPEC.md
- `docs/ORCHESTRATOR-PARALLEL-DELEGATION-*.md` (3 files) — Merged into AGENTS.md

---

## Missing Documentation (Create)

- `docs/QUICK-START-TOKEN-VISIBILITY.md` — How to monitor token usage
- `docs/QUICK-START-BUDGET-CHECKING.md` — How to set and check budgets
- `docs/QUICK-START-PRODUCTION-DEPLOYMENT.md` — How to deploy to production
- `docs/INDEX.md` — Master documentation index

---

## Key Issues Found

1. **README.md is 1,591 lines** — Contains duplicated sections, stale references to `~/.copilot/` paths, and content from multiple phases mixed together. Needs rewrite to <500 lines.

2. **TODO.md is dated May 9, 2025** — Over a year stale. All items show 0% progress. Needs complete refresh to reflect May 2026 actual state.

3. **SPEC.md is missing Phase 3 features** — Token visibility, budget checking, and production deployment requirements added in Phases B-E are not documented in SPEC.md.

4. **Root directory has 12 implementation report files** — Should be in `docs/archive/phase-reports/`.

5. **No documentation index** — 145 docs files with no navigation guide.

---

## Recommendations

1. Rewrite README.md to <500 lines focusing on: what it is, quick start, architecture overview, harness comparison, key docs
2. Rewrite TODO.md with current May 2026 status
3. Add Phase 3 section to SPEC.md
4. Move root-level `*_IMPLEMENTATION.md` files to `docs/archive/phase-reports/`
5. Create `docs/INDEX.md` as master navigation
6. Create 3 quick-start guides for Phase 3 features
