# Archive Index

This directory preserves historical documentation, completed phase reports,
one-time analysis files, and superseded materials. Nothing here is needed for
day-to-day development — see the [docs/ README](../README.md) for active docs.

---

## What Was Archived and Why

### `phase-docs/` — Phase completion reports, session logs, investigations

These files served a purpose during active development but are now superseded
by the current architecture, active guides, and permanent references in `docs/`.

| File | Why Archived |
|------|-------------|
| `PHASE-6-COMPLETE.md` | Phase 6 completion marker; superseded by current codebase |
| `PHASE-6-DEPLOYMENT-GUIDE.md` | Phase-specific deployment; superseded by `docs/INSTALL.md` + production guides |
| `PHASE-6-VALIDATION-COMPLETE.md` | Validation sign-off; no longer actionable |
| `PHASE-H-TEST-COVERAGE-PLAN.md` | Planning doc; coverage now tracked in `TODO.md` + CI |
| `ORCHESTRATOR-SESSION-2026-05-19.md` | Single-session log; historical context only |
| `ARCHITECTURE-AUDIT-2026-05-17.md` | Point-in-time audit; superseded by `docs/architecture/` |
| `CONSOLIDATION-SUMMARY.md` | Consolidation sprint summary; changes are now in git history |
| `DOCUMENTATION-AUDIT.md` | One-time audit; resolved items are done |
| `plan-iterate.md` | Planning scratch doc from a past session |
| `pure-orchestrator-before-after.md` | Before/after comparison; architecture now stable |
| `PI-DEV-RENDERER-ANALYSIS.md` | pi-dev renderer investigation; resolved |
| `HARNESS-REVIEW.md` | Harness code review; findings incorporated |
| `HARNESS-CONSISTENCY-ANALYSIS.md` | Analysis completed; standards in `docs/reference/CODING_STANDARDS.md` |
| `HARNESS-CONSISTENCY-FRAMEWORK.md` | Framework design; now implemented |
| `CLAUDE-CODE-HARNESS-ANALYSIS.md` | Claude Code harness investigation; resolved |
| `COPILOT-CLI-HARNESS-ANALYSIS.md` | Copilot CLI harness investigation; resolved |
| `OPENCODE-CONFIG-INVESTIGATION.md` | opencode config debugging; resolved |
| `OPENCODE-CONFIG-RECOVERY.md` | Recovery procedure; one-time use |
| `PROTOCOL-EXPANSION-INITIATIVE.md` | Initiative planning doc; expansion complete |
| `PROTOCOL-IMPLEMENTATION-SUMMARY.md` | Implementation notes; superseded by `docs/PROTOCOL.md` |
| `spec-audit.md` | Spec audit; findings incorporated into `docs/SPEC.md` |
| `spec-compliance-verification.md` | Verification pass; complete |
| `requirement-mapping.md` | Requirement traceability during planning; done |
| `requirement-verification.md` | Verification checklist; done |
| `STANDARDS-DOCUMENTATION-PLAN.md` | Standards planning; now executed, see `docs/STANDARDS-INDEX.md` |
| `STANDARDS-ROADMAP.md` | Standards roadmap; current state is the roadmap destination |
| `AGENTIC-ENGINEERS-ARCHITECTURE-DIAGRAMS.md` | Superseded by `docs/architecture/` subdirectory |
| `LEVEL-3-GRADUATION-CHECKLIST.md` | Graduation checklist; milestone passed |

---

### `root/` — Root-level files cleaned up

These files lived at the repository root but did not belong there.

| File | Why Archived / What It Was |
|------|---------------------------|
| `COMPLETION_SUMMARY.md` | Session completion report — historical, not a permanent doc |
| `FIX_SUMMARY.md` | Summary of a specific bug fix — historical notes |
| `VERSION_STRATEGY_ANALYSIS.md` | One-time versioning analysis; findings in `VERSIONING.md` |
| `SECURITY_ANALYSIS.md` | CI failure security analysis — investigation closed |
| `SECURITY_ASSESSMENT.md` | Security assessment of a specific fix — closed |
| `plan.md` | Active session planning scratch file |
| `user_profile.py` | Demo module illustrating a bug scenario (educational only) |
| `test_user_profile.py` | Regression tests for the demo bug scenario above |

> `ORCHESTRATOR_CLI_QUICK_REFERENCE.md` was **removed** from root (not archived)
> because an identical copy already exists at `docs/ORCHESTRATOR_CLI_QUICK_REFERENCE.md`.

---

### Pre-existing archived material (unchanged)

| Directory | Contents |
|-----------|---------|
| `deprecated/` | Experimental code, PHASE 3–5 docs, research files, session summaries |
| `phase-reports/` | Implementation reports for individual features |
| `bin/` | Retired shell scripts |

---

## Active Documentation (not archived)

Current reference docs live in:

| Path | Description |
|------|-------------|
| `docs/README.md` | Documentation index |
| `docs/SPEC.md` | System specification |
| `docs/PROTOCOL.md` | DELEGATE/HANDBACK protocol |
| `docs/WORKFLOW.md` | Development workflow |
| `docs/SYSTEM.md` | System overview |
| `docs/architecture/` | Architecture design docs |
| `docs/reference/` | Coding standards, patterns, dashboards |
| `docs/runbooks/` | Operational runbooks |
| `docs/operations/` | Metrics, tokenadvisor ops |
| `docs/specs/` | Protocol YAML specs |

---

_Last updated: 2026-05-23 — file-cleanup skill consolidation pass_
