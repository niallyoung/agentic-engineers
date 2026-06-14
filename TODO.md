# TODO: agentic-engineers

**Last Updated:** 2026-06-14  
**Status:** Active — Phase G Complete, Doc Consolidation Round 2 Complete, README Refactored, Phase H Complete (633 tests TIER1/2/3), Cost Management Complete (3 skills merged), **Phase 1.5 Security Hardening Complete (5 FIXes + 38+ tests)**, **Milestone 2/3 DELEGATEs queued (2026-06-14)**

---

## Milestone 2 — Harness Stability (Wave 1-3, 2026-06-14)

Queue path: `~/.agentic-engineers/claude/2026-06-14-111501/queue/incoming/`  
10 DELEGATEs staged; Orchestrator to process in 3 waves.

### Wave 1 (parallel, no dependencies)
- [ ] `m2-harness-eval-baseline` — quality-engineer: run eval suite, capture harness x model x feature matrix
- [ ] `m3-skills-inventory-audit` — lead-engineer: run skills_auditor, produce 6-dimension scorecard + CORE/UTILITY/EXPERIMENTAL
- [ ] `queue-monitor-dashboard` — engineer: live queue dashboard (curses TUI, polling, metrics)

### Wave 2 (depends on baseline)
- [ ] `m2-opencode-stability` — senior-engineer: harden OpenCode harness to 95% target
- [ ] `m2-claude-stability` — senior-engineer: harden Claude Code harness to 95% target
- [ ] `m2-copilot-stability` — senior-engineer: harden Copilot CLI harness to 95% target
- [ ] `m3-skills-consolidation-plan` — lead-engineer: consolidation plan for redundancy clusters

### Wave 3 (depends on Wave 2)
- [ ] `m2-harness-regression-gate` — quality-engineer: lock in regression gate, CI-enforced
- [ ] `m3-skills-deprecation` — engineer: execute deprecations per consolidation plan
- [ ] `m3-skills-standardization` — engineer: standardize remaining skills to SPEC

---

## Milestone 3 — Skills Consolidation Plan (m3-skills-consolidation-plan HANDBACK, 2026-06-14)

**Lead Engineer review complete. Plan ready for Wave 3 execution (m3-skills-deprecation).**

Wave 1 audit (m3-skills-inventory-audit) was not yet in queue/done/ at review time.
This plan is derived from direct inspection of all 27 skill directories in src/skills/,
SKILL.md frontmatter, test counts, LOC, and harness rendering state.

### Current Inventory (27 total items in src/skills/)

| Skill | Tests | LOC | SKILL.md | In Harness | Category |
|---|---|---|---|---|---|
| ab-testing | 0 | 581 | Y | Y | EXPERIMENTAL |
| agent-creator | 3 | 1139 | Y | Y | CORE |
| consistency-checker | 21 | 1391 | Y | Y | CORE |
| cost-aggregation | 116 | 2465 | Y | Y | CORE |
| cost-budgeting | 83 | 1659 | N | N | CORE |
| doc-quality-monitor | 0 | 835 | Y | Y | UTILITY |
| file-sync | 41 | 1472 | Y | Y | UTILITY |
| harness-integration-tracker | 74 | 1636 | Y | Y | UTILITY |
| harness-opencode-feature-sync | 19 | 870 | Y | Y | UTILITY |
| local-model-runtime | 30 | 840 | Y | Y | UTILITY |
| metrics-etl | 0 | 293 | Y | Y | UTILITY |
| model-engineer | 3 | 493 | Y | Y | CORE |
| model-selection | 123 | 1749 | Y | Y | CORE |
| monitoring | 0 | ~200 | N | N | DEPRECATED |
| orchestrator | 81 | 4157 | Y | Y | CORE |
| protocol-validator | 55 | 1921 | Y | Y | CORE |
| queue-management | 131 | 6123 | Y | Y | CORE |
| queue-query | 30 | 765 | Y | Y | CORE |
| queue-todo-sync | 20 | 1529 | Y | Y | UTILITY |
| repo-init | 76 | 5660 | Y | Y | DISABLED |
| session-analyzer | 7 | 1138 | Y | Y | UTILITY |
| skill-creator | 3 | 207 | Y | Y | UTILITY |
| spec-management | 23 | 4447 | Y | Y | CORE |
| spec-validator | 3 | 1758 | Y | Y | CORE |
| testing | 0 | 1020 | Y | Y | UTILITY |
| tokenadvisor | 0 | 584 | Y | Y | UTILITY |
| usage-tracking | 3 | 1465 | Y | Y | UTILITY |
| workflow-review | 3 | 718 | Y | Y | UTILITY |

**Note:** `spec-extract` directory exists in src/skills/ (1 file: scanner.sh) but is NOT rendered
to any harness. It is a dead fragment — immediate deletion candidate.

---

### Redundancy Clusters Identified

#### Cluster A — Cost/Token Analytics (4 skills with overlapping purposes)

Skills: `tokenadvisor`, `usage-tracking`, `cost-aggregation`, `metrics-etl`

**Overlap analysis:**
- `tokenadvisor` (584 LOC, 0 tests): role-based daily cost analysis and optimization recommendations. Read-only analytics, scheduled daily. Documented in `monitoring/token-advisor.md` as well — duplicated concept.
- `usage-tracking` (1465 LOC, 3 tests): real-time token capture + forecasting. Session-scoped shell scripts. Bash-based, light test coverage.
- `cost-aggregation` (2465 LOC, 116 tests): multi-provider cost consolidation. Well-tested, Python, COST-002.
- `metrics-etl` (293 LOC, 0 tests): Prometheus/Grafana metrics pipeline. Zero tests, scheduled background job.

**Verdict:** Two distinct concerns exist — (1) cost/token *analysis* for decision-making (tokenadvisor + usage-tracking) and (2) cost *aggregation* across providers (cost-aggregation). `metrics-etl` is infrastructure plumbing.

**Recommendation:**
- MERGE `tokenadvisor` → `usage-tracking`: Both are read-only session/daily analytics. Absorb tokenadvisor's role-analysis logic into usage-tracking as a sub-command. usage-tracking becomes the unified token analytics skill. `tokenadvisor` deprecated.
- RETAIN `cost-aggregation`: Distinct responsibility (multi-provider cost normalization), well-tested.
- RETAIN `metrics-etl`: Distinct responsibility (Prometheus export pipeline), but flag for test addition.
- DELETE `monitoring/`: Doc-only directory of `.md` files that duplicate content in the above skills' own SKILL.md. No code, never rendered. Archive to `docs/archive/deprecated-skills/monitoring-docs/`.

#### Cluster B — Cost Enforcement (2 skills with overlapping purposes)

Skills: `cost-budgeting`, `model-selection`

**Overlap analysis:**
- `cost-budgeting` (1659 LOC, 83 tests, NO SKILL.md, NOT in harness): COST-001. Enforces per-session/hour/day budgets. Well-tested Python but missing SKILL.md and excluded from harness rendering.
- `model-selection` (1749 LOC, 123 tests): COST-003. Recommends optimal model given cost/quality/latency constraints. Depends on cost-budgeting.

**Verdict:** Not duplicates — cost-budgeting enforces limits, model-selection optimizes within limits. However, cost-budgeting's absence from the harness is a defect, not intentional. It needs a SKILL.md and harness registration.

**Recommendation:**
- FIX `cost-budgeting`: Add SKILL.md (copy pattern from model-selection), register in harness. Not a consolidation — this is a defect.
- RETAIN both skills as distinct: enforcement vs. optimization are separate concerns.

#### Cluster C — Scaffolding/Creator Tools (2 skills with near-identical purpose)

Skills: `agent-creator`, `skill-creator`

**Overlap analysis:**
- `agent-creator` (1139 LOC, 3 tests): Scaffolds new agents — SKILL.md frontmatter, TDD test scaffold, __init__.py, scripts/, DELEGATE/HANDBACK templates. Validates naming, role, model, circular deps.
- `skill-creator` (207 LOC, 3 tests): Scaffolds new skills following agentskills.io spec. Directory structure, SKILL.md, script templates, documentation.

**Verdict:** Near-identical purpose with same user-facing goal: "create a new thing that follows SPEC." The split appears arbitrary — agents are just skills with role assignments in this framework. skill-creator is underpowered (207 LOC) vs agent-creator (1139 LOC with real validation logic).

**Recommendation:**
- MERGE `skill-creator` → `agent-creator`: Absorb skill-creator's agentskills.io scaffolding into agent-creator as a `--type skill` flag. agent-creator already does the harder work. skill-creator is the weaker duplicate. After merge, agent-creator handles `--type agent` (default) and `--type skill`.
- Add 3 tests for the new `--type skill` path in agent-creator before deprecating skill-creator.

#### Cluster D — Protocol/Spec Validation (3 skills with overlapping gates)

Skills: `protocol-validator`, `spec-validator`, `consistency-checker`

**Overlap analysis:**
- `protocol-validator` (1921 LOC, 55 tests): Runtime DELEGATE/HANDBACK schema validation against protocol-core-v1.0.yaml. <5ms. Single-message validation.
- `spec-validator` (1758 LOC, 3 tests): SPEC.md compliance for code changes. Detects violations in git diffs. Pre-merge gate.
- `consistency-checker` (1391 LOC, 21 tests): Cross-validates the entire queue — scans all states, detects cycles, orphans, rate-limit breaches. Depends on protocol-validator.

**Verdict:** These serve different scopes: protocol-validator (per-message), spec-validator (per-diff), consistency-checker (whole-queue). They are NOT redundant — they are layered validation at different granularities. However, spec-validator's 3 tests is a quality gap.

**Recommendation:**
- RETAIN all three: Each has a distinct validation scope.
- Flag spec-validator for test coverage improvement (3 tests for 1758 LOC is unacceptably low — should be ≥85% coverage target per framework standards).

#### Cluster E — Harness Tracking (2 narrowly-scoped skills)

Skills: `harness-integration-tracker`, `harness-opencode-feature-sync`

**Overlap analysis:**
- `harness-integration-tracker` (1636 LOC, 74 tests): Cross-harness drift detection — all 4 harnesses (OpenCode, Copilot, Claude, PI). Generates integration-summary.yaml per harness.
- `harness-opencode-feature-sync` (870 LOC, 19 tests): OpenCode-specific renderer drift — KNOWN_KEYS schema, permission patterns, reasoning variants. Feeds into harness-integration-tracker registry.

**Verdict:** `harness-opencode-feature-sync` is a *source* for harness-integration-tracker. It handles OpenCode-specific parsing that would bloat the tracker. Architecturally sound as separate skill, but narrow scope and manually triggered only.

**Recommendation:**
- MERGE `harness-opencode-feature-sync` → `harness-integration-tracker` as a sub-module: The OpenCode-specific sync logic becomes `scripts/opencode_sync.py` inside harness-integration-tracker. Reduces the number of harness-scoped skills from 2 to 1 without losing functionality.
- Migration: harness-integration-tracker calls opencode_sync internally; external callers use harness-integration-tracker directly.

#### Cluster F — Docs & Pattern References (doc-only directories, not real skills)

Items: `monitoring/`, `spec-extract/`, `src/skills/architecture/`, `src/skills/optimization/`, `src/skills/orchestration/`, `src/skills/patterns/`, `src/skills/roles/`, `src/skills/security/`, `src/skills/shared/`

**Analysis:** These directories exist in src/skills/ but are reference/doc directories or shared libraries, not rendered skills. They are not in ~/.claude/skills/ (not harness-rendered). Some contain markdown guidance docs, others contain Python shared modules.

**Recommendation:**
- `monitoring/` — DELETE (doc-only, content duplicated in tokenadvisor/usage-tracking SKILL.md)
- `spec-extract/` — DELETE (single shell script, not integrated, not rendered)
- `architecture/`, `optimization/`, `orchestration/`, `patterns/`, `roles/`, `security/`, `shared/` — AUDIT in Wave 3: determine which are shared Python modules (should move to `src/lib/` or `src/shared/`) vs. stale reference docs (archive or delete). Do NOT render as skills.

#### Cluster G — Disabled Skill

Skill: `repo-init` (5660 LOC, 76 tests, DISABLED in SKILL.md)

**Verdict:** Explicitly disabled by user policy concern. High LOC and tests but zero production utility.

**Recommendation:**
- ARCHIVE `repo-init` → `docs/archive/deprecated-skills/repo-init/`: Move entire directory out of src/skills/. Preserve in archive with restoration instructions per framework convention. Remove from harness rendering.
- Re-enable only via explicit user decision (follow spec-management approval flow for un-deprecating).

---

### Before/After Skill Matrix

| Before | After | Action | Phase |
|---|---|---|---|
| tokenadvisor | merged → usage-tracking | DEPRECATE | Wave 3 |
| usage-tracking | usage-tracking (absorbs tokenadvisor) | ENHANCE | Wave 3 |
| skill-creator | merged → agent-creator | DEPRECATE | Wave 3 |
| agent-creator | agent-creator (--type skill added) | ENHANCE | Wave 3 |
| harness-opencode-feature-sync | merged → harness-integration-tracker | DEPRECATE | Wave 3 |
| harness-integration-tracker | harness-integration-tracker (opencode sub-module) | ENHANCE | Wave 3 |
| monitoring/ | deleted | DELETE | Wave 3 |
| spec-extract/ | deleted | DELETE | Wave 3 |
| repo-init | archived to docs/archive/ | ARCHIVE | Wave 3 |
| cost-budgeting | SKILL.md added + harness registered | FIX | Wave 3 |
| spec-validator | test coverage improved (3 → ≥85%) | FIX | Wave 3 |
| cost-aggregation | retained | RETAIN | — |
| metrics-etl | retained (tests needed) | RETAIN+FIX | Wave 3 |
| model-selection | retained | RETAIN | — |
| model-engineer | retained | RETAIN | — |
| consistency-checker | retained | RETAIN | — |
| protocol-validator | retained | RETAIN | — |
| spec-management | retained | RETAIN | — |
| orchestrator | retained | RETAIN | — |
| queue-management | retained | RETAIN | — |
| queue-query | retained | RETAIN | — |
| queue-todo-sync | retained | RETAIN | — |
| doc-quality-monitor | retained (tests needed: 0 currently) | RETAIN+FIX | Wave 3 |
| session-analyzer | retained | RETAIN | — |
| file-sync | retained | RETAIN | — |
| testing | retained (tests needed: 0 currently) | RETAIN+FIX | Wave 3 |
| local-model-runtime | retained | RETAIN | — |
| ab-testing | retained (tests needed: 0 currently) | RETAIN+FIX | Wave 3 |
| workflow-review | retained | RETAIN | — |

**Expected footprint after consolidation:**
- Before: 27 items in src/skills/ (3 deprecated, 1 doc-only fragment, 1 disabled)
- After: 22 active skills (5 fewer = 18.5% reduction)
- LOC reduction: ~3,700 LOC removed (tokenadvisor 584 + skill-creator 207 + harness-opencode-feature-sync 870 + monitoring ~200 + spec-extract ~50 + repo-init 5660 migrated out) = net active codebase reduction.
- Exceeds 10-15% footprint target.

---

### Prioritized Wave 3 Execution Order

**Phase W3-A — Deletions (zero risk, immediate wins):**
1. DELETE `src/skills/monitoring/` — doc-only, zero code, no harness rendering
2. DELETE `src/skills/spec-extract/` — single dead shell script, zero integration
3. ARCHIVE `src/skills/repo-init/` → `docs/archive/deprecated-skills/repo-init/` — disabled by policy

**Phase W3-B — Defect Fixes (unblock cost-budgeting and spec-validator):**
4. FIX `cost-budgeting`: Add SKILL.md, register in harness renderer
5. FIX `spec-validator`: Add test coverage to ≥85% (currently 3 tests / 1758 LOC)

**Phase W3-C — Merges (moderate complexity, each needs test verification):**
6. MERGE `skill-creator` → `agent-creator` (add --type skill flag, 3 new tests, then deprecate)
7. MERGE `tokenadvisor` → `usage-tracking` (absorb role-analysis sub-command, verify 0→≥10 tests)
8. MERGE `harness-opencode-feature-sync` → `harness-integration-tracker` (sub-module pattern)

**Phase W3-D — Coverage fixes (quality gate compliance):**
9. FIX `doc-quality-monitor`: Add tests (0 → ≥85% coverage)
10. FIX `testing`: Add tests (0 → ≥85% coverage)
11. FIX `ab-testing`: Add tests (0 → ≥85% coverage)
12. FIX `metrics-etl`: Add tests (0 → minimal smoke tests)

---

### Rollback Strategy Per Consolidation

**W3-A deletions:**
- Git history is the rollback. All deleted files recoverable via `git checkout <commit> -- src/skills/<name>/`.
- Archive `repo-init/` with a `RESTORE.md` per framework convention.

**W3-B defect fixes:**
- Additive-only (new SKILL.md, new tests). Rollback = revert the commit. Zero risk.

**W3-C merges:**
- Each merge executes in a separate branch (`fix/consolidate-<name>`).
- Deprecation tag added to source skill SKILL.md before deletion commit.
- Source skill directory kept in `docs/archive/deprecated-skills/<name>/` with merge commit SHA recorded.
- Rollback: restore from archive directory + re-register in renderer.
- No merge executes until all tests pass on the target skill post-absorption.

**W3-D coverage fixes:**
- TDD-first: tests written against existing code. Purely additive. Rollback = revert.

---

### Testing Requirements for Wave 3

Each consolidation must pass this gate before the source skill is deleted:

| Consolidation | Gate |
|---|---|
| skill-creator → agent-creator | agent-creator tests pass + 3 new `--type skill` tests green |
| tokenadvisor → usage-tracking | usage-tracking tests pass + role-analysis sub-command has ≥10 tests |
| harness-opencode-feature-sync → harness-integration-tracker | harness-integration-tracker tests pass + existing 19 tests ported as internal tests |
| cost-budgeting SKILL.md fix | Harness renders cost-budgeting; existing 83 tests still pass |
| spec-validator coverage | ≥85% coverage on spec_validator.py (currently ~0%) |

---

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Merge breaks dependent skill | Low | Medium | Test all dependents in CI before deleting source |
| Harness rendering broken post-fix | Low | High | Render dry-run in CI; check ~/.claude/skills/ post-render |
| repo-init archive loses test history | None | None | git log preserves all history |
| cost-budgeting SKILL.md conflicts with model-selection dependency | Low | Low | model-selection depends on cost-budgeting Python API, not SKILL.md |
| Coverage fixes reveal bugs | Medium | Low | Treat as wins — fix bugs found during W3-D |

**Overall risk: LOW.** All merges are absorb-and-deprecate patterns with git-backed rollback. No breaking API changes to framework consumers.

---

## 🎉 CATCH-UP FIX PARTY (branch `feature/catch-up-fixparty-wooooo`, 2026-06-11)

Recovered from the 2026-06-10 master prompt (full DELEGATE/HANDBACK audit
session) + the 2026-06-10/11 fable-5 + CI + YAML audit follow-ups. These were
planned but not yet implemented across the recent multi-session work.

**Source master prompt (2026-06-10):** "full audit of whether we are actually
using DELEGATE/HANDBACK via ~/.agentic-engineers/ … fix the dir naming so the
path order is `<harness>/<sessionID>` and NOT the reverse — humans cannot index
UUIDs … at the very end add evals around delegations/handbacks/quality gates …
TDD throughout."

### Done in prior sessions (verified)
- [x] Protocol Revival end-to-end (PR #48) — paths de-`artifacts/`-ed, hooks, wiring, TDD
- [x] Orchestrator idle poll — every 3 min, up to 3 cycles, then stop (`run_idle_loop`)
- [x] Evals scaffold — `tests/evals/` (delegate/handback/routing quality)
- [x] DELEGATE/HANDBACK written as **YAML** not JSON (PR #52) — the "never picked up" root cause
- [x] fable-5 defensive-only support + per-harness protections + no-reroute semantics (PR #49)
- [x] CI gated on PRs; main CI failures fixed (PR #50)

### Outstanding — this branch
- [x] **CU-1 — Backup timestamp collision.** `backup-harnesses.sh` uses `date +%Y%m%d`; same-day re-installs collide. Switch to `%Y%m%d-%H%M%S` (design doc `UNIFIED-INSTALL-DESIGN.md` already specifies `_HHMMSS`). Update README warning + test. — Done in PR #53 (2026-06-11)
- [x] **CU-2 — SPEC naming-rule self-contradiction.** docs/SPEC.md LOCKED naming table: "HYPHENS (e.g. `claude-opus-4.7`), NOT DOTS (e.g. ~~`claude-opus-4.7`~~)" — both examples identical; repo convention is dots for versions. Correct it. — Done in PR #53 (2026-06-11)
- [x] **CU-3 — Per-skill price-constant drift.** `tokenadvisor.py` (and peers) hardcode stale $/token rates instead of reading `src/config/models.yaml`. Correct to canonical (opus-4.8 $5/$25, fable-5 $10/$50, haiku $1/$5); add fable-5. — Done in PR #53 (2026-06-11)
- [x] **CU-4 — Reverse queue path order → `{harness}/{sessionID}`.** Master-prompt final step. Flip `~/.agentic-engineers/{session}/{harness}/queue` → `{harness}/{session}/queue` across queue_isolation, harness_session_manager, runner, queue_query, queue_migration_metrics, queue_compat; extend `migrate-queue-paths.sh` to move existing dirs; update SPEC locked section + QUEUE-PROTOCOL + ARCHITECTURE + AGENTS.md; TDD all path tests. — Done in PR #53 (2026-06-11)
- [~] **CU-5 — Consolidate root `SPEC.md` into `docs/SPEC.md`.** Implemented via the `spec-management` skill on branch `spec/cu5-consolidate-root`, open as PR #54 (CI green, awaiting merge). Proposal SPEC-2026-001 migrated the model-governance LOCKED sections (Model Switch Process tied to `.githooks/LOCKED_MODELS.sh`) into docs/SPEC.md and reduced root SPEC.md to a thin pointer.

### Deferred / needs decision (not in this branch)
- [x] **HANDBACK-as-DELEGATE direct delegation** — master prompt asked "is HANDBACK actually a DELEGATE / can it be, for direct agent→agent handoff vs queue-and-poll?" Design note captured at `docs/design/handback-as-delegate.md` (branch `chore/post-fixparty-followups`, PR pending). Implementation still needs a decision.
- [x] **`spawn_sub_agent` is mocked** — pattern documented at `docs/design/spawn-sub-agent-pattern.md` (branch `chore/post-fixparty-followups`): real Orchestrator→sub-agent invocation is a runtime "AGENTS-with-SKILLS" behaviour (Task tool), not a code daemon. Real invocation remains harness-runtime behaviour.
- [x] **Symlink toggle for harness invocation** — `make` target to force-create a symlink to toggle active harness (master prompt item 5). Done in this branch (chore/post-fixparty-followups).

---

## ✅ COMPLETED

### Phases 1–6 (Core Framework)
- [x] Queue-based DELEGATE/HANDBACK protocol
- [x] 8 specialized agent roles (Orchestrator, Engineer, Senior, Lead, QE, Security, Principal, Model Engineer)
- [x] 3-layer quality gates (DELEGATE structure, routing quality, HANDBACK validation)
- [x] AutomationController (continuous polling with signal handling)
- [x] Pure Orchestrator (zero business logic, 100% routing)
- [x] ModelResolver (centralized models.yaml)
- [x] MetricsCollector (35-field canonical record per task)
- [x] SDLC enforcement hooks (pre-commit, commit-msg, pre-push)
- [x] 4 harness renderers (OpenCode, Claude Code, Copilot CLI, π.dev)
- [x] 1047+ tests passing (100%)

### Phase 3 Features (Token Visibility & Budget)
- [x] Token tracker implementation (`opencode-tokens` CLI)
- [x] Budget checker implementation (`opencode-budget` CLI)
- [x] Cost attribution per agent/role
- [x] Shadow mode (dry-run delegation)
- [x] Token cost alerts
- [x] Orchestrator CLI quick reference

### Phase B–E (Skills & Harness Improvements)
- [x] 14 skills implemented and rendered
- [x] OpenCode harness: full agent + skill rendering, managed config
- [x] Claude Code harness: 8 agents + 14 skills
- [x] Parallel delegation support (parent-child task hierarchy)
- [x] Span capture (OpenTelemetry format)
- [x] Artifact indexing (Model Engineer generates index.json)

---

## ✅ COMPLETED

### Skills Implementation (Completed 2026-05-19)

- [x] **SKILL-TODO-001:** Implement queue-todo-sync skill
  - ✅ Auto-sync queue DELEGATEs ↔ TODO.md on HANDBACK received
  - ✅ Bidirectional sync, conflict detection, weekly reporting
  - ✅ 20/20 tests passing (100%), 80% coverage
  - ✅ Quality: 92/100, Confidence: 95%
  - Completed: 2026-05-19 | Owner: Engineer

- [x] **SKILL-DOC-QUALITY-001:** Implement doc-quality skill
  - ✅ Link validation, cross-ref checks, staleness flagging
  - ✅ Quality metrics, HTML+Markdown reports, CI/CD integration
  - ✅ SPEC.md excluded from all checks (5 dedicated tests)
  - ✅ 52/52 tests passing (100%), >80% coverage
  - ✅ Quality: 94/100, Confidence: 94%
  - Completed: 2026-05-19 | Owner: Quality Engineer

### Market Comparison Enhancement (Completed 2026-05-19)

- [x] **COMPARISON-001:** Add Steve Yegge's Gastown to market comparison
  - ✅ Research Gastown framework (15.4K stars, v1.1.0, May 2026)
  - ✅ Added to README.md Quick Comparison Table (6 columns)
  - ✅ Created detailed Gastown section (600+ words, lines 337-587)
  - ✅ Documented 9 strengths + 5 weaknesses + 6 use-cases
  - ✅ Updated comparison context (resource-aware paradigm)
  - ✅ Quality: 94/100, Confidence: 94%
  - Completed: 2026-05-19 | Owner: Engineer

### README Refactoring (Completed 2026-05-20)

- [x] **README-REFACTOR-001:** Add Key Benefits & Discoveries section
  - ✅ DELEGATE/HANDBACK protocol benefits (90+/100 quality, 40-60% faster, 80% less rework)
  - ✅ Token efficiency analysis (40-60% cost reduction via smart model selection)
  - ✅ Parallel sub-agent execution at scale (36+ concurrent agents tested)
  - ✅ Real-world cost breakdown table and token savings example (65% reduction)
  - ✅ Quality: 94/100
  - Completed: 2026-05-20 | Owner: Orchestrator

- [x] **README-REFACTOR-002:** Simplify Example section with practical DELEGATE YAML
  - ✅ Removed verbose 3-step workflow (plan → implement → review)
  - ✅ Replaced with single, practical DELEGATE YAML example (fix CI/CD timeout)
  - ✅ Shows complete workflow: plan → implement → document → verify → test → commit → push → watch CI/CD
  - ✅ Removed duplicate Model Configuration & Customization section
  - ✅ Clarified OpenCode harness (primary) vs GitHub Copilot (service)
  - ✅ Quality: 95/100
  - Completed: 2026-05-20 | Owner: Orchestrator

### Phase G: Documentation Refresh (Completed 2026-05-18)

- [x] **DOC-AUDIT-001:** Create `docs/DOCUMENTATION-AUDIT.md`
- [x] **DOC-README-001:** Rewrite README.md (<500 lines, accurate, current)
- [x] **DOC-TODO-001:** Refresh TODO.md with current May 2026 status
- [x] **DOC-SPEC-001:** Update SPEC.md with Phase 3 token visibility requirements
- [x] **DOC-QS-001:** Create `docs/QUICK-START-TOKEN-VISIBILITY.md`
- [x] **DOC-QS-002:** Create `docs/QUICK-START-BUDGET-CHECKING.md`
- [x] **DOC-QS-003:** Create `docs/QUICK-START-PRODUCTION-DEPLOYMENT.md`
- [x] **DOC-INDEX-001:** Create `docs/INDEX.md` (master documentation index)
- [x] **DOC-ARCHIVE-001:** Move root-level `*_IMPLEMENTATION.md` files to `docs/archive/phase-reports/`

---

## ✅ COMPLETED

### Doc Consolidation Round 2 (Completed 2026-05-18)

- [x] **CONSOLIDATION-001:** Audit all `docs/` for redundancy, staleness, and unnecessary files
- [x] **CONSOLIDATION-002:** Remove/merge redundant documentation
- [x] **CONSOLIDATION-003:** Update cross-references and links
- [x] **CONSOLIDATION-004:** Verify no broken links or orphaned files
- [x] **CONSOLIDATION-MANIFEST:** Created consolidation manifest with restoration instructions

---

## ✅ COMPLETED

### Phase H: Test Coverage Improvements (Completed 2026-05-28)

- [x] **COVERAGE-TIER1:** Add tests for 5 critical modules (588 stmts)
  - ✅ Modules: core_protocol_validator (150), protocol_audit (201), healer-metrics-analyzer (137), queue_manager (96), test_validators (104)
  - ✅ Target: All modules ≥90% coverage — ACHIEVED (97-99%)
  - ✅ Effort: 21:22 | Status: COMPLETE
  - ✅ 432 tests passing, 5/5 modules at 97-99% coverage
  - Completed: 2026-05-28 | Quality: 97/100

- [x] **COVERAGE-TIER2:** Add tests for important modules (251 stmts)
  - ✅ Modules: config_loader (69), atomic_queue_ops (63), rollback_manager (56), directory_setup (63)
  - ✅ Target: All modules ≥80% coverage — ACHIEVED (94-100%)
  - ✅ Effort: 28:58 | Status: COMPLETE
  - ✅ 128 tests passing, 6/6 modules improved +48pp avg
  - Completed: 2026-05-28 | Quality: 97/100

- [x] **COVERAGE-TIER3:** Add tests for optional modules (522 stmts)
  - ✅ Modules: protocol_audit, healer_metrics_analyzer, tier3_coverage extras
  - ✅ Target: All modules ≥80% coverage — ACHIEVED (100%)
  - ✅ Effort: 9:39 (bonus) | Status: COMPLETE
  - ✅ 73 tests passing, 4/4 modules at 100% coverage
  - Completed: 2026-05-28 | Quality: 97/100

### Cost & Usage Management (🎉 COMPLETED — 4 days early!)

- [x] **COST-001:** Implement cost budgeting & enforcement skill
  - ✅ Per-session, per-hour, per-day, per-week, per-month cost caps
  - ✅ Track actual spend vs. budget + alert at 50%, 75%, 90%, 100%
  - ✅ Graceful degradation: warn before blocking, then block at hard limits
  - ✅ Support provider-agnostic cost models
  - ✅ Effort: 10:23 | Status: MERGED (PR #19)
  - ✅ 99 tests, 93% coverage | Quality: 97/100
  - ✅ Fixed: Thread-safe saves (tempfile + atomic replace), concurrent RMW locking

- [x] **COST-002:** Multi-provider cost aggregation & reporting
  - ✅ Aggregate spend across Claude, GPT, Gemini, GitHub Copilot, OpenCode
  - ✅ Per-provider cost breakdown, efficiency metrics
  - ✅ Weekly/monthly spend reports with trend analysis
  - ✅ Effort: 14:20 | Status: MERGED (PR #19)
  - ✅ 113 tests, 94% coverage, <10ms performance | Quality: 97/100

- [x] **COST-003:** Model selection optimization across providers
  - ✅ Detect which provider offers best cost/quality for given task
  - ✅ Route to cheaper provider when quality delta is acceptable
  - ✅ Track provider-specific model performance
  - ✅ Effort: 53:17 | Status: MERGED (PR #20, v0.37.0 released)
  - ✅ 123 tests, 89% coverage | Quality: 97/100

**Summary:** All cost management work delivered **4 DAYS EARLY** (May 28 vs June 1 deadline)
- 3 skills implemented, tested, merged to main
- 335 total tests across COST-001/002/003
- 633 tests added across TIER1/2/3 coverage
- 0 regressions across 3,988 total tests
- v0.38.0 tagged and released

---

---

## ✅ COMPLETED

### Phase 1.5: Security Hardening (Completed 2026-05-30)

- [x] **PHASE-1.5-FIX-1:** Queue Path Enforcement (Runtime + Git Hook)
  - ✅ Implemented `src/skills/_meta/queue-path-validator/`
  - ✅ Canonical path: `~/.agentic-engineers/{session-id}/{harness}/queue/`
  - ✅ Runtime validator rejects queue injection/poisoning attempts
  - ✅ Git hook enforces canonical paths in all DELEGATE/HANDBACK files
  - ✅ 5+ tests passing, no CI failures
  - ✅ Quality: 95/100

- [x] **PHASE-1.5-FIX-2:** Audit Trail via spec_version Field
  - ✅ Added `spec_version` field to DELEGATE and HANDBACK schemas
  - ✅ Format validation: `\d+\.\d+(-.+)?` (e.g., "1.0", "1.1-2026-05-28")
  - ✅ HANDBACK spec_version must match DELEGATE (audit trail linkage)
  - ✅ SPAN records include spec_version for audit queries
  - ✅ 5+ tests passing
  - ✅ Quality: 94/100

- [x] **PHASE-1.5-FIX-3:** Agent Definition Verification (Tri-Level)
  - ✅ Generated `.agents_verification_sha` from AGENTS.md
  - ✅ Added `model_verification_sha` field to DELEGATE schema
  - ✅ Git hook validates agent definitions match current state
  - ✅ Runtime check in Orchestrator prevents model downgrade attacks
  - ✅ 5+ tests passing
  - ✅ Quality: 96/100

- [x] **PHASE-1.5-FIX-4:** Security-Critical DELEGATE Fields
  - ✅ Added `security_scope` enum (auth, crypto, pii, secrets, injection, supply_chain)
  - ✅ Added `approval_gate` field (lead_engineer, principal_engineer, security_engineer, cto)
  - ✅ Added `audit_required` boolean flag
  - ✅ Routing rules: security tasks routed to Security Engineer minimum
  - ✅ Pre-push hook validation: security_scope requires approval_gate and audit_required
  - ✅ 10+ tests passing
  - ✅ Quality: 97/100

- [x] **PHASE-1.5-FIX-5:** Orchestrator Enforcement Decorator
  - ✅ Created `@enforce_delegate_requirement` decorator in `src/orchestration/decorators.py`
  - ✅ Applied to all Orchestrator.invoke() and Orchestrator.delegate() methods
  - ✅ Validates: DELEGATE schema, required fields, queue paths, spec_version, model_verification_sha, security routing, approval gates
  - ✅ Error handling: explicit EnforcementError with fix suggestions, never silent failures
  - ✅ Audit trail logging for all validation failures
  - ✅ 8+ tests passing
  - ✅ Quality: 96/100

**Phase 1.5 Summary:**
- ✅ All 5 critical fixes implemented and tested
- ✅ 33+ unit tests + 5+ integration tests passing
- ✅ 95%+ coverage on new code
- ✅ Zero regressions across test suite
- ✅ Ready for Phase 1 (spec audit) to proceed
- ✅ Framework now self-enforces security hardening

---

## 📅 CONSOLIDATION ROADMAP

**Objective:** Simplify, stabilize, and polish the agentic-engineers framework. Focus on harness compatibility, skills audit, and production-readiness.

### Milestone 1 (CURRENT): Phase 1.5 Security Hardening ✅ COMPLETE
**Target Date:** 2026-05-30 | **Status:** ✅ DELIVERED  
**Deliverables:**
- ✅ Queue path enforcement (runtime + git hook validation)
- ✅ Audit trail via spec_version field
- ✅ Agent definition verification (tri-level)
- ✅ Security-critical DELEGATE fields (security_scope, approval_gate, audit_required)
- ✅ Orchestrator enforcement decorator with error handling

**Quality Metrics:**
- 38+ tests passing | 95%+ coverage | Zero regressions
- Quality Score: 96/100 | Confidence: 97%

---

### Milestone 2 (NEXT): Harness Stability Across All Platforms
**Target Timeline:** 2-3 weeks (2026-06-13)  
**Priority:** CRITICAL  
**Objective:** Ensure OpenCode, Claude Code, and Copilot CLI harnesses achieve ≥95% compatibility and reliability.

#### OpenCode Harness
- [ ] **OPENCODE-QUEUE-PATH-DETECTION:** Implement harness detection for canonical queue paths
  - Detect session-id and harness type from context
  - Enable proper routing of work through OpenCode harness
  - Blocks: Framework users cannot properly route tasks
  - Effort: 2-3 hours | Owner: Engineer

- [ ] **OPENCODE-HARNESS-CHECKER:** Validate harness configuration at runtime
  - Startup checks: agents loaded, skills available, queue paths valid
  - Effort: 1-2 hours | Owner: Quality Engineer

- [ ] **OPENCODE-RUNNER-INTEGRATION:** Full runner lifecycle integration
  - Task queueing, execution, result retrieval
  - Effort: 2-3 hours | Owner: Senior Engineer

#### Claude Code Harness
- [ ] **CLAUDE-AGENT-AVAILABILITY:** Ensure all 8 agents render and load
  - Verify agent definitions, role assignments, model routing
  - Effort: 2-3 hours | Owner: Quality Engineer

- [ ] **CLAUDE-SKILL-RENDERING:** Full skill catalog rendering and accessibility
  - Test all 14 skills accessible within Claude Code environment
  - Effort: 2-3 hours | Owner: Quality Engineer

#### Copilot CLI Harness
- [ ] **COPILOT-MODEL-ROUTING:** Implement intelligent model selection
  - Route tasks to appropriate model (Haiku/Sonnet/Opus) based on complexity
  - Effort: 2-3 hours | Owner: Model Engineer

- [ ] **COPILOT-TOKEN-TRACKING:** Full token usage and cost visibility
  - Track per-task costs, cumulative session spend, budget alerts
  - Effort: 2-3 hours | Owner: Model Engineer

**Success Metrics:**
- All harnesses pass 100+ compatibility tests
- ≥95% success rate on standard delegation workflows
- Zero silent failures or compatibility regressions
- Full end-to-end telemetry enabled

---

### Milestone 3 (ONGOING): Skills Audit & Consolidation
**Target Timeline:** Ongoing (continuous)  
**Priority:** HIGH  
**Objective:** Stabilize skill ecosystem, improve quality and maintainability.

#### Skills Inventory & Audit
- [ ] **SKILLS-AUDIT:** Review all 14 skills
  - Assess: value, usage, maintenance burden, test coverage
  - Categorize: core (essential), utility (helpful), experimental (proof-of-concept)
  - Effort: 2-3 hours | Owner: Lead Engineer

#### Skills Standardization
- [ ] **SKILLS-STANDARDIZATION:** Enforce consistent standards
  - SKILL.md format alignment (all 14 skills)
  - Test coverage: ≥85% per skill
  - Documentation completeness
  - Effort: 3-5 hours | Owner: Quality Engineer
  - Reference: [docs/guides/skills-standardization.md](docs/guides/skills-standardization.md) (framework + tooling)
  - Audit report regenerated by `python3 -m src.audit.run_audit` → `docs/archive/audits/SKILLS-AUDIT.md`

#### Deprecated Skills
- [ ] Review and archive low-value or experimental skills
  - Move to `docs/archive/deprecated-skills/` with restoration instructions
  - Effort: 1-2 hours | Owner: Senior Engineer

---

## 🎯 Feature Freeze & Post-Freeze Policy

**Feature Freeze Date:** 2026-06-15 (Post-Milestone 3)

### What Happens at Freeze:
No new skills or agents may be added to the framework after this date. All API additions, new agent roles, and skill implementations freeze.

### Post-Freeze Work Only (June 15 onwards):
- ✅ Bug fixes (reported issues, regressions, security)
- ✅ Performance improvements (optimization, latency reduction)
- ✅ Documentation (guides, examples, standards)
- ✅ Polish (UX, error messages, consistency)
- ✅ Dependency updates (security patches, compatibility)

### What's NOT Allowed Post-Freeze:
- ❌ New skills or agents
- ❌ New API endpoints or DELEGATE fields
- ❌ Major refactoring or architectural changes
- ❌ Feature additions or scope creep

**Rationale:** Consolidation phase focuses on stability, reliability, and polish—not feature velocity. Framework is feature-complete for production.

---

## 📋 POST-MERGE ROADMAP

> **Reconciliation note (2026-05-30):** The OpenCode integration fixes and EVALS-001…005 +
> EVALS-INFRASTRUCTURE items below are **COMPLETE on the `feature/cleanup` integration branch**
> (verified: `src/skills/_meta/evaluation_framework/`, `src/evals/`, `src/harness/`, nightly GH
> Actions). They remain checklist-tracked here until `feature/cleanup` merges to `main`.

### OpenCode Integration Fixes (Priority: HIGH)
- [x] **OPENCODE-QUEUE-PATH-DETECTION:** Implement harness detection for canonical queue paths — ✅ DONE on feature/cleanup
  - Current: OpenCode uses generic queue path detection
  - Fix: Detect session-id and harness type from context
  - Blocks: Framework users cannot properly route work through OpenCode harness
  - Effort: 2-3 hours | Owner: Engineer
  - Link: See PHASE-1.5-ORCHESTRATION-PLAN.md

- [x] **OPENCODE-HARNESS-CHECKER:** Validate harness configuration at runtime
  - Current: No validation that OpenCode harness is properly configured
  - Fix: Add startup checks: agents loaded, skills available, queue paths valid
  - Effort: 1-2 hours | Owner: Quality Engineer

### Harness Compatibility & Evaluation Testing (Priority: CRITICAL)
**Problem:** Recent harness/model updates are causing silent compatibility flaps and feature regressions. Need end-to-end feedback loop testing.

- [x] **EVALS-001: Harness Integration Tests** — ✅ DONE on feature/cleanup
   - Build comprehensive test suite for copilot|opencode|claude CLI harnesses
   - Test standard prompts/delegations/skills across all harnesses
   - Capture success/fail results with pass/fail thresholds
   - Report compatibility matrix: (harness × model × feature)
   - Effort: 2-3 weeks | Priority: CRITICAL | Owner: Quality Engineer
   - Success Metric: All harnesses pass standard eval suite with ≥95% success rate

- [x] **EVALS-002: Model Compatibility Matrix** — ✅ DONE on feature/cleanup
   - Build test suite calling each model (haiku, sonnet, opus) with standard DELEGATE blocks
   - Measure response quality, latency, cost
   - Detect model regressions early (breaking changes after model updates)
   - Effort: 1-2 weeks | Priority: HIGH | Owner: Model Engineer

- [x] **EVALS-003: Skill Interoperability Tests** — ✅ DONE on feature/cleanup
   - Test each skill against all harnesses (copilot, opencode, claude, pi)
   - Validate skill outputs meet HANDBACK schema requirements
   - Report skill-by-harness compatibility
   - Effort: 1-2 weeks | Priority: HIGH | Owner: Quality Engineer

- [x] **EVALS-004: End-to-End Delegation Workflows** — ✅ DONE on feature/cleanup
   - Create standard delegation scenarios (simple task, escalation, parallel work)
   - Run through full workflow on each harness/model combo
   - Measure success rate, latency, cost
   - Report pass/fail + threshold analysis
   - Effort: 2-3 weeks | Priority: HIGH | Owner: Senior Engineer

- [x] **EVALS-005: Continuous Evaluation Pipeline (CI/CD Integration)** — ✅ DONE on feature/cleanup
   - Add nightly evaluation job to GitHub Actions
   - Run standard eval suite against all harnesses + models
   - Generate compatibility report automatically
   - Alert on regressions (model incompatibility, harness drift)
   - Effort: 1-2 weeks | Priority: MEDIUM | Owner: Principal Engineer

- [x] **EVALS-INFRASTRUCTURE: Evaluation Framework** — ✅ DONE on feature/cleanup
   - Create reusable `src/skills/_meta/evaluation-framework/` skill
   - Standardized test case format, result reporting, threshold checking
   - Integration with CI/CD, human-readable reports
   - Effort: 2 weeks | Priority: CRITICAL | Owner: Senior Engineer
   - Deliverable: Pluggable framework for adding new evaluation scenarios

### Documentation Polish & Consolidation (Priority: MEDIUM)
- [ ] **README-POLISH:** Update top section with Phase 1.5 completion and consolidation vision
   - Add "Phase: Simplify, Reduce, and Polish" banner after intro
   - Add Evaluation & Compatibility Testing section
   - Link to evaluation roadmap
  - Explain: We are in consolidation phase, not feature-add
  - Link to TODO.md for detailed roadmap
  - Effort: 1 hour | Owner: Orchestrator

- [ ] **CONSOLIDATION-ROADMAP:** Add structured roadmap to TODO.md
  - Timeline: "Stable across copilot|opencode|claude CLI, then polish-only"
  - Focus areas: skills audit, agent role clarification, enforcement consistency
  - Feature freeze date: TBD (after harness stability achieved)
  - Effort: 1 hour | Owner: Orchestrator

### Feature Freeze & Polish Timeline
- **Milestone 1 (Current):** Phase 1.5 security hardening (COMPLETE ✅)
- **Milestone 2 (Next):** Harness stability across all platforms (2-3 weeks)
  - OpenCode harness: queue path detection, runner integration
  - Claude Code harness: agent availability, skill rendering
  - Copilot CLI harness: model routing, token tracking
- **Milestone 3:** Skills audit and consolidation (ongoing)
  - Review: 14 skills, prioritize high-value, deprecate low-value
  - Standardize: SKILL.md format, test coverage, documentation
- **Feature Freeze:** Post-milestone 3 (target: June 15, 2026)
  - No new skills or agents after freeze date
  - Focus: bug fixes, performance, documentation, polish

---

## 🔵 PLANNED (Phase J+)

- [x] **STANDARDS-002:** Create STANDARDS.md comprehensive guide
   - Full standards alignment, compliance matrix, roadmap
   - Effort: 4-6 hours | Owner: Senior Engineer
   - ✅ Completed: 2026-05-30 — Created root `STANDARDS.md` documenting actual
     enforced standards (TDD, DELEGATE/HANDBACK, locked model policy, security,
     Python conventions, conventional commits, branch/worktree workflow,
     skill/agent authoring, quality-gate thresholds). Grounded in AGENTS.md,
     CONTRIBUTING.md, .githooks/, and src/config/. models.yaml left untouched (LOCKED).

### Framework Integration (Opt-In Required)
> **Status:** ⏸️ PAUSED — Research complete. No work starts until explicitly approved.  
> **Research:** [docs/FRAMEWORKS/](docs/FRAMEWORKS/)

- [ ] **FRAMEWORK-001:** Anthropic SDK integration verification
- [ ] **FRAMEWORK-002:** OpenAI SDK integration
- [ ] **FRAMEWORK-003:** Ollama local LLM runtime
- [ ] **FRAMEWORK-004:** CrewAI orchestration layer documentation
- [ ] **FRAMEWORK-005:** Pydantic AI type-safe agents

### Cost & Usage Management (🚨 HIGH PRIORITY — June 1 deadline)
> **Context:** As of June 1, 2026 (8 days from NOW), all LLM providers charge per usage token + time, not flat subscription. Framework users need cost controls, visibility, and multi-provider optimization. April 2026 usage equivalent to $550 USD in AI credits (GitHub Copilot subsidy was ~$39 AUD/month equivalent).

- [ ] **COST-001:** Implement cost budgeting & enforcement skill
  - Per-session, per-hour, per-day, per-week, per-month cost caps (configurable in credits/$)
  - Track actual spend vs. budget + alert at 50%, 75%, 90%, 100%
  - Graceful degradation: warn before blocking, then block at hard limits
  - Support provider-agnostic cost models (different rates per provider)
  - Effort: 3-4 days | Owner: Senior Engineer + Model Engineer
  - **Critical:** Must be ready by June 1

- [ ] **COST-002:** Multi-provider cost aggregation & reporting
  - Aggregate spend across Claude (Anthropic), GPT (OpenAI), Gemini (Google), GitHub Copilot, OpenCode
  - Per-provider cost breakdown, efficiency metrics (cost per task, cost per test, etc.)
  - Weekly/monthly spend reports with trend analysis
  - Effort: 2-3 days | Owner: Metrics + Model Engineer
  - **Critical:** Must be ready by June 1

- [ ] **COST-003:** Model selection optimization across providers
  - Detect which provider offers best cost/quality for given task
  - Route to cheaper provider when quality delta is acceptable
  - Track provider-specific model performance (Haiku vs Claude-3.5-Sonnet vs GPT-4 mini, etc.)
  - Effort: 2-3 days | Owner: Model Engineer
  - **Critical:** Must be ready by June 1

- [~] **COST-004:** Local model support (Ollama, llama.cpp, Apple MLX, NVidia)
  - [x] **Phase 1 (Planning):** Define harness architecture for local LLMs
    - [x] How agents connect to local Ollama instance (`/api/tags`, injectable client)
    - [x] Fallback logic when local unavailable (route to cloud)
    - [x] Cost accounting (local = $0 but slower)
    - [x] Model availability detection + auto-selection
  - [x] **Phase 2 (Minimal impl):** Ollama integration (most popular local runtime)
    - [x] Detect Ollama instance (localhost:11434 or env var)
    - [x] List available models, select best-fit by size/quality
    - [x] Route Haiku-class tasks to local, Sonnet/Opus to cloud when local insufficient
    - [x] Fallback: if local model not available, use cloud
    - ✅ Skill: `src/skills/local-model-runtime/` — 30 tests, 95% coverage
    - ✅ Stdlib-only (urllib); reads zero-cost catalogue from `providers.yaml`
  - [ ] **Phase 3 (Future):** llama.cpp, Apple MLX, NVidia CUDA support
  - Effort: Phase 1: 1-2 days (planning) | Phase 2: 3-5 days (impl) | Phase 3: TBD
  - Owner: Principal/Senior Engineer
  - **Strategic:** Local models → 95% cost reduction long-term, essential for users running on local hardware

### Future Features
- [x] **COMPARISON-002:** Update orchestration framework comparisons to include Gas City
  - Gas City v1.0.0 released late April 2026 (refinement of Gastown by Steve Yegge)
  - Add to README.md Quick Comparison Table and detailed analysis
  - Effort: 2-3 hours | Owner: Engineer
  - ✅ Done: Gas City column added to Quick Comparison Table + dedicated "🌆 Gas City" analysis subsection. NOTE: repo had no factual details beyond version/lineage, so feature cells are marked **TBD** pending user-supplied specifics (architecture, protocol, runtime support, community metrics).
- [ ] **MONITORING-001:** Automated document quality monitoring
  - Continuous link validation, staleness detection (30+ days)
  - ✅ Done: `src/skills/doc-quality-monitor` — broken-link, missing-section,
    staleness, placeholder-leakage & structure checks; JSON + Markdown report
    with configurable health-score gate. 37 tests passing (TDD). CLI + library API.
- [ ] **ORCHESTRATOR-001:** Continuous compliance validation
  - Monthly full standards audit, automated alerts on drift
- [ ] **SKILL-REPO-INIT-001:** Implement repo-init skill for new repository onboarding
  - Effort: 3-5 days | Owner: Senior/Principal Engineer

---

## 📊 Phase Status

| Phase | Status | Completion |
|-------|--------|------------|
| 1–6: Core Framework | ✅ Complete | 100% |
| Phase 3: Token Visibility | ✅ Complete | 100% |
| Phase B–E: Skills & Harness | ✅ Complete | 100% |
| Phase G: Documentation Refresh | ✅ Complete | 100% |
| Doc Consolidation Round 2 | ✅ Complete | 100% |
| Skills: queue-todo-sync | ✅ Complete | 100% (92/100 quality) |
| Skills: doc-quality | ✅ Complete | 100% (94/100 quality) |
| Market: Gastown Comparison | ✅ Complete | 100% (94/100 quality) |
| README: Key Benefits & Discoveries | ✅ Complete | 100% (94/100 quality) |
| README: Simplified Example Section | ✅ Complete | 100% (95/100 quality) |
| Phase H: Test Coverage | ✅ Complete | 100% (633 tests TIER1/2/3) |
| Phase H-TIER1: Critical Modules | ✅ Complete | 100% (432 tests) |
| Phase H-TIER2: Important Modules | ✅ Complete | 100% (128 tests) |
| Phase H-TIER3: Optional Modules | ✅ Complete | 100% (73 tests) |
| Cost & Usage Management (COST-001/002/003) | ✅ Complete | 100% (335 tests, v0.38.0 released) |
| Phase 1.5: Security Hardening (5 FIXes) | ✅ Complete | 100% (38+ tests, all security gates passed) |
| Phase I: Standards Compliance | 🟡 In Progress | STANDARDS.md pending (see feat/standards-md) |
| Framework Integration | ⏸️ Paused | Research only |

---

## 📋 Implementation Rules

✅ **TDD-First:** All code changes follow Red-Green-Refactor  
✅ **Quality Gates:** Minimum 85% coverage per changed module  
✅ **SPEC.md Protection:** All changes routed through spec-management skill  
✅ **Queue Protocol:** All delegations go through `artifacts/queue/`  
✅ **Zero Regressions:** All tests passing before commit  
✅ **Documentation:** All changes documented, links updated  

---

**Owner:** Orchestrator Agent  
**Next Review:** 2026-05-24 (weekly)

---

## Plan close-out (2026-06-13)

Residual items from the retired PLAN.md (2026-06-08, written for PR #40 — merged as 80924f1):

- [ ] **docs/SPEC.md queue-path order inconsistency** — glossary examples (~lines 403-404)
  and the Legacy Paths migration table (lines 588-590, inside the LOCKED Queue
  Architecture section) still use the old `~/.agentic-engineers/{session-id}/{harness}/queue/`
  order; canonical per CU-4 (PR #53) is `{harness}/{session-id}`. Must be routed through
  the spec-management skill (Principal/Security/Lead only) — do not edit directly.
- [ ] **Pi.dev full-source rendering (plan 4.1)** — `renderer/scripts/render-pi-dev.py`
  derives models dynamically, but `renderer/pi-dev-src/` templates (AGENTS.md, pi.yml,
  SYSTEM.md) still hardcode structural content instead of rendering from `src/agents/*.md`.
- [ ] **Verify pi.yml routing against pi.dev runtime (plan 4.2)** — `renderer/pi-dev-src/pi.yml`
  still documents routing rules as speculative/unverified; blocked on pi.dev runtime access.
- [ ] **SPEC editorial pass remainder (plan 4.3)** — root SPEC.md consolidation is in
  PR #54; once the queue-path order fix above lands, do a final consistency sweep of
  docs/SPEC.md examples and changelog.
- [ ] **docs/SPEC.md:1421 references deleted AutomationController** — `AutomationController`
  (src/orchestration/agents/automation.py) was removed in the 2026-05-17 daemon-removal
  refactor (f9faf18); the harness now owns polling (OrchestratorSkill.run_idle_loop).
  orchestrator.py's run_poll_cycle docstring is fixed; SPEC.md is owned elsewhere — route
  via spec-management to replace the AutomationController mention with the harness/idle-loop
  model. tests/test_dry_run.py:14 docstring has the same stale mention (comment-only).
- [x] **src/skills/orchestrator/SKILL.md escalation docs stale** — line 141 said
  status=escalate "delegate to Model Engineer"; corrected to canonical C2c escalation
  chaining: synthesize `{task_id}-escalated-to-{role}` DELEGATE into incoming/ and archive
  the original to done/ with audit metadata (the old non-canonical escalation/ directory was
  removed from orchestrator_skill.py on 2026-06-13). Fixed in P1 consolidation (2026-06-13).

---

## Next: Skill Improvements & Self-Improvement Architecture (2026-06-13)

**Ref:** PLAN_skill-improvements.md (repo root)

Three DELEGATEs queued for next session execution via Orchestrator — **all delivered
via the P1 self-improvement round (PR #57, merged to main 2026-06-13):**

- [x] **DELEGATE-2026-06-13-001** — Skill Audit & Enhancement (lead-engineer)
  - Enhanced doc-quality-monitor, protocol-validator; session-analyzer meta-skill landed
    (`src/skills/session-analyzer/`).
- [x] **DELEGATE-2026-06-13-002** — Model Adaptability Config Design (principal-engineer)
  - Runtime model-selection system delivered (`src/skills/model-selection/`,
    `src/config/model-config.yaml`).
- [x] **DELEGATE-2026-06-13-003** — Meta-Skill Session Analysis (model-engineer)
  - session-analyzer skill delivered; reads transcripts and flags automation candidates.

**Principle:** All work via DELEGATE. Never manual file writes to queue. Centralize data in ~/.agentic-engineers/ (not harness dirs).

### Outstanding queue work (all complete)

- [x] **2026-06-13-orchestrator-architecture-decision** (principal-engineer) — Complete.
  Documented the in-harness Agent dispatch architecture. `spawn_sub_agent()` and 
  `invoke_qe_gate()` now have comprehensive documentation explaining how real agent 
  dispatch happens at the harness level via the Agent tool. Added 13 unit tests covering
  both methods. Commit: d25f56f (2026-06-13, feat(orchestrator)). No breaking changes.
  The two sibling DELEGATEs (queue-staleness-detection, spec-queue-sla-design) were 
  superseded by #57's staleness monitoring modules and archived to `queue/done/` with 
  audit metadata on 2026-06-13.
