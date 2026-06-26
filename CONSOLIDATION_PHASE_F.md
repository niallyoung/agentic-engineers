# Agentic-Engineers Consolidation Initiative (Phase F)
**Date:** 2026-06-25 (updated 2026-06-26)  
**Scope:** Architecture unification, enforcement modernization, cleanup  
**Target:** Single source-of-truth for config, specs, harness structure; shift from hard rules to principle-based positive reinforcement; remove dead code and stale artifacts.

---

## Completion Status (2026-06-26)

| Phase | Status | Highlights |
|-------|--------|-----------|
| **F-1 → F-4** | ✅ **COMPLETE** | Single source-of-truth config/specs, unified `src/harnesses/` structure, single model resolver, enforcement modernized, dead code removed. **~5,170 tests**, **~22 files changed**. |
| **G-1** Harness idle-loop integration | ✅ **COMPLETE** | 3 harnesses (Claude Code, OpenCode, Copilot CLI); **567 harness tests** + 64 infra (21 scheduler + 43 backoff). DELEGATE auto-processing works end-to-end. |
| **G-2** Continuous in-process polling | ✅ **COMPLETE** | Exponential backoff (5s→600s) + file-watch wake; **60 new tests** (14 G-2 integration + 46 backoff); 5 DELEGATEs in 71ms, backoff overhead <2ms. **656+ tests total passing** across G work. |
| **G-3** External daemon mode | ⏸️ Deferred (optional) | Not required — G-2 provides continuous polling with no external daemon. |

**Conclusion:** Full harness queue cooperation is implemented. DELEGATEs
**auto-process without manual invocation** — each harness polls its session queue
during idle periods, backing off when empty and waking immediately on arrival,
entirely in-process (no external daemon, cron, or system service). See
[`src/orchestration/PHASE_G_HARNESS_COOPERATION.md`](src/orchestration/PHASE_G_HARNESS_COOPERATION.md)
and [`docs/guides/harness-queue-polling.md`](docs/guides/harness-queue-polling.md).

---

## Executive Summary

Four parallel audits (Principal Engineer, Security Engineer, Codebase Cleanliness, File Organization) identified **six major inconsistency clusters**:

1. **Model truth fragmented across 6 sources** (models.yaml, model-config.yaml, LOCKED_MODELS.sh, 2x model_registry.py, fallback defaults, 2x AGENTS.md)
2. **Harness structure incomplete migration** (3 old flat per-harness modules + 2 new nested modules coexist)
3. **Config/Spec split** (src/config/ vs config/, AGENTS.md in 3 places, SPEC.md in 3 places)
4. **Dead code & unused infrastructure** (src/standardization, src/examples, src/claude, orchestration Python lib, 16 _meta/ skills hidden from dist/, unused security crypto/PKI)
5. **Enforcement inconsistencies** (hard rules mixed with principles, SHA check warn-only, fallback defaults diverge, entropy detection disabled)
6. **Documentation rot & cleanup needed** (docs/INDEX.md 63% broken links, DEPRECATED-SKILLS contradictory, WAVE-3 plans in root, multiple guide copies)

**High-leverage fixes:** unify model truth, resolve AGENTS.md drift, complete harness migration, delete dead modules. **Principles-based shift:** wire unused security infra or remove, shift threat detection to observation + escalation.

---

## Detailed Findings Summary

### Cluster 1: Model Truth Fragmentation (6 Sources → 1)

**Current state:**
- `src/config/models.yaml` — canonical provider/pricing/lifecycle
- `src/config/model-config.yaml` — agent→model assignments (different naming: claude-haiku vs claude-haiku-4.5)
- `.githooks/LOCKED_MODELS.sh` — hardcoded AGENT_MODEL_ASSIGNMENTS array (maintenance hazard)
- `src/orchestration/agents/model_resolver.py` FALLBACK_DEFAULTS (lines 51–67) — disagrees with canonical (senior-engineer wrongly defaults to sonnet-4.6 not 4.5)
- `renderer/model_registry.py` (145 LOC) + `src/harnesses/claude_code/model_registry.py` (154 LOC) — dual implementations with overlapping concerns
- Plus: `src/copilot/model_router.py`, `src/orchestration/model_config_loader.py`, `src/orchestration/agents/model_resolver.py`, `src/orchestration/models/model_selector.py` (6 total resolvers across codebase)

**Impact:** Model policy changes require edits in 6+ places; fallback defaults introduce a model-selection bypass; fable-5 absent from resolver.

**Solution:** Single ModelResolver over `src/config/models.yaml`; derive `.githooks/LOCKED_MODELS.sh` from YAML (remove hardcoded array); consolidate 6 resolvers into 1; remove FALLBACK_DEFAULTS or derive them from YAML.

**Effort:** Medium. **Risk:** Low (all resolvers already tested independently).

---

### Cluster 2: Harness Structure Incomplete Migration (3+2 → 1)

**Current state:**
- Old flat per-harness: `src/claude/`, `src/copilot/`, `src/opencode/`, `src/harness/` (4 dirs, mostly superseded)
- New nested per-harness: `src/harnesses/claude_code/`, `src/harnesses/copilot_cli/` (2 dirs, incomplete)
- Orphaned code: `src/claude/agent_verifier.py`, `src/copilot/model_router.py` have no counterparts in `src/harnesses/copilot_cli/`
- Naming collision: `src/harness/` (singular) vs `src/harnesses/` (plural) for the same concept

**Impact:** Dead code (src/examples 0 refs, src/claude 0 prod refs, src/standardization 0 prod refs); two conventions invite confusion; incomplete migration leaves both old and new code maintained in parallel.

**Solution:** Complete migration: `src/{claude,copilot,opencode,harness}` → `src/harnesses/` (with per-harness subdirs: `src/harnesses/{claude_code,copilot_cli,opencode,shared}/`); delete orphaned old implementations.

**Effort:** High (code relocation + test updates). **Risk:** Medium (relocation can break imports if not careful).

---

### Cluster 3: Config & Spec Fragmentation (3 AGENTS.md, 3 SPEC.md, 2 config/ → 1 each)

**Current state:**
- **AGENTS.md in 3 places:** `src/AGENTS.md` (893 lines, canonical per render), `docs/AGENTS.md` (1214 lines, divergent), `renderer/pi-dev-src/AGENTS.md` (PI template, duplicate)
- **SPEC.md in 3 places:** `SPEC.md` root (35-line pointer), `docs/SPEC.md` (1959 lines, canonical per render-specs.sh), no dist version tracked
- **Config in 2 places:** `config/*.yaml` (framework-manifest, orchestration, deployment, token_budget — byte-identical to dist/specs/ output) + `src/config/*.yaml` (models.yaml, model-config.yaml)
- **Naming inconsistency:** `models.yaml` uses canonical names (claude-haiku), `model-config.yaml` uses full version numbers (claude-haiku-4.5)

**Impact:** AGENTS.md drift means renderers use `src/` while docs use `docs/` — model/role data can diverge. PI templates are external to `src/`. Config `src/ → render` pipeline unclear: is `config/` source or generated staging?

**Solution:**
1. Declare `src/AGENTS.md` canonical; delete `renderer/pi-dev-src/AGENTS.md`; keep `docs/AGENTS.md` as a symlink/generated view.
2. Move `renderer/pi-dev-src/` → `src/harnesses/pi/` so all harness source lives under `src/`.
3. Move `config/*.yaml` → `src/config/`; update `render-specs.sh` to source from `src/config/` only.
4. Standardize model naming: choose one style (canonical = claude-haiku; derived = claude-haiku-4.5) and apply consistently.

**Effort:** Medium. **Risk:** Low (all are source-only files; no runtime code depends on their location beyond render path).

---

### Cluster 4: Dead Code & Unused Infrastructure (Remove ~15K LOC)

**Candidates:**
- `src/standardization/` (4 files, 0 production imports) — only tests + old WAVE-3 docs reference
- `src/examples/` (8 files, 0 references anywhere) — demo scripts, not used in docs or Makefile
- `src/claude/` (4 files, mostly superseded) — `agent_verifier.py`, `skill_catalog.py`, `skill_manager.py`, `startup_check.py` only used by tests
- `src/copilot/` (4 files, 1 ref only) — mostly superseded; `model_router.py` kept, rest reviewed
- `src/orchestration/security/` crypto/PKI/audit (5 modules, 0 production callers) — tested thoroughly, wired nowhere
- `src/orchestration/queue_compat.py` — explicitly deprecated (DEPRECATED marker, migration complete 2026-05-26)
- Duplicate validators: `src/orchestration/quality/threshold_enforcer.py` + `threshold_enforcement.py` (same class name, same dir)
- Duplicate scripts: `scripts/validate_skills.py` vs `renderer/validate_skills.py` (divergent copies)
- Hidden skills: `src/skills/_meta/` (16 skills, 0 dist/ output, invisible to official registry)

**Impact:** Inflates surface area for maintenance; confuses new contributors (is X still used?); test coverage hides dead-code issue.

**Solution:** Delete src/standardization, src/examples, unused copilot modules; consolidate threshold_enforcer; unify validate_scripts; move _meta/ skills to `src/internal/` or explicitly promote to first-class; delete queue_compat.py.

**Effort:** Low–Medium (mostly deletions + test cleanup). **Risk:** Low (low-coupling code).

---

### Cluster 5: Enforcement Inconsistency & Security Wiring (Shift from Hard Rules → Detection + Escalation)

**Current issues:**
- **AGENTS.md SHA check is warn-only, not blocking** (`.githooks/pre-push` section 6) — model-downgrade risk on local edits silently proceeds; CI never runs hard validation.
- **Fallback model defaults bypass model policy** — `model_resolver.py` FALLBACK_DEFAULTS differ from canonical source; if YAML missing, routes work to wrong model.
- **Credential detection is pattern-only, entropy disabled** — `EntropyDetector.detect_in_value` has entropy path disabled ("too many false positives"), pure regex detection is evadable.
- **Unused security infrastructure wired nowhere** — PKISigner, AgentIdentity, AuditLogger, RateLimiter (5 modules) fully tested but never invoked in production path; test coverage is false assurance.
- **Offensive scope detection is brittle substring matching** — `OFFENSIVE_SCOPE_PATTERNS` in `delegate_validator.py` uses case-insensitive `in`, trivially evaded ("expl0it"), prone to false positives (defensive "prompt injection detection" task hits the gate).
- **Duplicate RateLimiter implementations** — `src/orchestration/security/rate_limiter.py` + `src/skills/queue-management/scripts/rate_limiter.py` with divergent APIs.

**Principles-based shift:**
1. **Keep hard gates that the CLI can't bypass** (git hooks, pre-push checks, startup harness validation).
2. **Convert soft checks to observability + escalation** — Threat detection (offensive scope, entropy, SHA drift) should *flag and escalate to user*, not block silently.
3. **Wire or deprecate unused security code** — either integrate PKI/audit into DELEGATE/HANDBACK lifecycle or move to `experimental/`.
4. **Derive enforced lists from single source** — AGENTS.md SHA + model allowlist + credential patterns all derived from canonical YAML, not hardcoded.

**Impact:** Real security layer (hard gates) stays; soft detection becomes visible + actionable (user sees flags, decides escalation); unused code clarity.

**Solution:**
- Make AGENTS.md SHA check hard-blocking in CI (framework-integrity.yml, security-gate.yml); keep warn on local intentional edits.
- Wire `EntropyDetector` into `pre-commit` over staged files (commit-time detection, not post-push CI-only).
- Move PKI/audit to `src/internal/experimental/` unless wired into production DELEGATE/HANDBACK lifecycle.
- Consolidate RateLimiters on queue-management implementation.
- Treat offensive-scope as *detection signal* (flag + escalate) rather than blocking gate.

**Effort:** Medium (wiring + test updates). **Risk:** Medium (security-related changes need validation).

---

### Cluster 6: Documentation Rot & Cleanup

**Issues:**
- `docs/INDEX.md` — 54 of 85 links broken (63%); points to deleted docs (TROUBLESHOOTING.md, REPOSITORY-STRUCTURE.md, SHADOW_MODE.md, PHASE-3-*, etc.)
- `docs/DEPRECATED-SKILLS.md` — self-contradictory; lists `ab-testing`, `metrics-etl` as "deprecated 2026-05-30" but both are live skills; claims 17 RESTORATION.md files, zero exist (only 1 RESTORE.md with wrong filename)
- `docs/README.md` — 7 of 21 links broken (33%)
- `MANIFEST.md` — claims 24 skills (currently 26); links to `docs/INSTALLATION.md` (doesn't exist)
- `MEMORY-*.md` links — missing `MEMORY-MIGRATION-GUIDE.md`
- **Root-level plan clutter** — `WAVE-3-PLAN.md`, `WAVE-3-SKILLS-STANDARDIZATION.md`, `SPEC_MANAGEMENT_IMPROVEMENTS.md` are completed-work planning docs; belong in `docs/archive/plans/` or deleted
- **Duplicate guides** — `docs/guides/ORCHESTRATION_v1_ARCHIVED.md`, `plan-implementer-legacy.md` (legacy but still in live guides/)
- **Setup clutter** — `setup/copilot-instructions.md` + `setup/GLOBAL_COPILOT_INSTRUCTIONS.md` duplicate `renderer/instructions/copilot-instructions.md` (they DIFFER — drift)

**Solution:**
1. Fix/delete `docs/INDEX.md`; reconcile `docs/DEPRECATED-SKILLS.md` (fix RESTORATION→RESTORE filenames, remove ab-testing/metrics-etl from deprecated list)
2. Move WAVE-3/SPEC_MANAGEMENT/STANDARDS.md to `docs/archive/plans/`
3. Move `setup/copilot-instructions.md` → single source at `renderer/instructions/`
4. Add missing `docs/INSTALLATION.md` or fix MANIFEST links
5. Audit & delete broken guide archives

**Effort:** Low (mostly deletions/reorganization). **Risk:** Negligible.

---

## Consolidated Consolidation Plan (Priority Order)

### Phase 1: Single Source of Truth (Weeks 1–2)
**Goal:** Eliminate config/spec duplication; unify model resolver.

**Tasks:**
1. **Unify model truth** — consolidate 6 model resolvers → 1; move all config to `src/config/`; derive LOCKED_MODELS.sh from YAML
2. **Resolve AGENTS.md drift** — declare `src/AGENTS.md` canonical; delete pi-dev-src copy; redirect docs/
3. **Move PI templates** — `renderer/pi-dev-src/` → `src/harnesses/pi/`
4. **Standardize config naming** — choose one model name style; apply consistently across yaml, LOCKED_MODELS.sh, resolver defaults

**Parallel DELEGATEs:** 4 (one per task)

---

### Phase 2: Complete Harness Migration (Weeks 2–4)
**Goal:** Unified harness directory structure under `src/harnesses/`.

**Tasks:**
1. **Migrate src/{claude,copilot,opencode} → src/harnesses/** — move code, update imports, delete old dirs
2. **Consolidate harness-level modules** — merge `src/harness/harness_checker.py` into `src/harnesses/shared/`
3. **Update all renderers** — point at new locations
4. **Update imports in tests, skills, orchestration** — systematic import update
5. **Delete orphaned implementations** — src/standardization, src/examples, src/claude (old)

**Parallel DELEGATEs:** 3 (migration runner, import cleanup, cleanup deletions)

---

### Phase 3: Enforcement Modernization (Week 3–4)
**Goal:** Shift from hard rules to detection + escalation; wire or deprecate unused security infra.

**Tasks:**
1. **Make AGENTS.md SHA check hard-blocking in CI** — update security-gate.yml, framework-integrity.yml
2. **Wire EntropyDetector into pre-commit** — staged-file credential detection
3. **Evaluate PKI/audit module wiring** — wire into DELEGATE/HANDBACK or move to experimental/
4. **Consolidate RateLimiters** — keep queue-management version, delete orchestration/security/ copy
5. **Shift offensive-scope detection from blocking to flagging** — update delegate_validator.py
6. **Sync model_resolver FALLBACK_DEFAULTS to models.yaml** — add test asserting equality

**Parallel DELEGATEs:** 2 (enforcement modernization, security infrastructure)

---

### Phase 4: Cleanup & Documentation (Week 4–5)
**Goal:** Remove dead code, fix documentation rot.

**Tasks:**
1. **Delete dead modules** — src/standardization, src/examples, duplicate threshold_enforcer, queue_compat.py, old copilot modules
2. **Consolidate validators** — unify validate_skills.py, check_test_regression.py
3. **Move root docs** — WAVE-3-*, SPEC_MANAGEMENT_IMPROVEMENTS, STANDARDS.md → `docs/archive/plans/`
4. **Fix broken docs** — rewrite INDEX.md, fix DEPRECATED-SKILLS.md, add INSTALLATION.md, fix guides
5. **Promote _meta/ skills** — either move to `src/internal/` or add to first-class registry with explicit lifecycle

**Parallel DELEGATEs:** 2 (cleanup deletions, documentation repair)

---

## Expected Outcomes

**After Consolidation Phase F:**

✅ **One canonical source for each:** models, AGENTS.md, SPEC.md, config  
✅ **Unified harness structure** under `src/harnesses/{harness}/`  
✅ **Single model resolver** + derived enforcement (no parallel implementations)  
✅ **Shifted enforcement paradigm** — hard gates stay, soft checks become observation + escalation  
✅ **~15K LOC removed** (dead modules, duplicates)  
✅ **Documentation repaired** (broken links fixed, stale plans archived)  
✅ **Pipeline clarity** — `src/ → render → dist/ → install → ~/.{harness}` fully adhered  
✅ **Positive-reinforcement security** — detection + escalation, not just hard blocking  

**Not in scope:** Orchestration Python library duality (Phase G candidate); PI full-source rendering from `src/` (depends on Phase 2 completion).

---

## Model Recommendations

- **Phase 1 (config unification):** engineer (straightforward consolidation)
- **Phase 2 (harness migration):** senior-engineer (complex import/test rewiring)
- **Phase 3 (enforcement):** security-engineer + lead-engineer (policy decisions + wiring)
- **Phase 4 (cleanup):** engineer (deletions, documentation)

**Estimated effort:** 6–8 weeks of parallel work (3–4 weeks critical path).
