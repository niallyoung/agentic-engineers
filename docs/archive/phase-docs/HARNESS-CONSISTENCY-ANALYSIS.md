# Harness Consistency Analysis — Master Document

**Document ID:** HARNESS-CONSISTENCY-ANALYSIS  
**Task ID:** 2026-05-16-harness-consistency-analysis  
**Author:** Lead Engineer  
**Date:** 2026-05-16  
**Status:** Complete — Phase 2 Consolidation  
**Scope:** Consolidated gap analysis across all four agentic-engineers harnesses  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Harness Overview & Architecture](#2-harness-overview--architecture)
3. [Unified Feature Matrix](#3-unified-feature-matrix)
4. [Consolidated Gap Analysis](#4-consolidated-gap-analysis)
5. [Implementation Roadmap](#5-implementation-roadmap)
6. [Risk Assessment](#6-risk-assessment)
7. [Cross-Harness Recommendations](#7-cross-harness-recommendations)
8. [Source Document Index](#8-source-document-index)

---

## 1. Executive Summary

The agentic-engineers framework ships four harness renderers — **OpenCode**, **Claude Code**, **π.dev**, and **Copilot CLI** — that translate canonical source definitions into platform-specific configuration directories. This document consolidates findings from five Phase 1 analysis documents into a single authoritative reference for Phase 3 planning.

### Overall Assessment

After the Phase 2 review and improvement cycle (2026-05-16), all four harnesses are functional and documented. However, they differ significantly in architecture, capability, and maintenance posture. The framework is **production-ready** but carries a set of well-understood gaps that, if left unaddressed, will compound into maintenance debt.

**Key headline findings:**

1. **OpenCode is the reference impl** — 14/14 mandatory features complete, most sophisticated architecture, strongest safety model. Primary remaining gaps are provider hardcoding and fragile AGENTS.md table parsing.

2. **Claude Code is production-ready at 85% parity** — All core features work correctly. Three meaningful gaps exist: no `docs/AGENTS.md` lookup, simplified model mapping (tier names only), and minor YAML escaping issue. These are enhancements, not blockers.

3. **π.dev is functional but structurally fragile** — Two confirmed bugs (argument parsing heuristic, premature directory creation). Six structural limitations, the most critical being the absence of a content transformation pipeline. All static files are manually maintained, creating inevitable drift risk.

4. **Copilot CLI is intentionally minimal and correctly designed** — Renders 14 skills; agents are intentionally omitted because the platform does not support custom agent registration. The only gap is a missing dedicated installation guide.

5. **No harness has automated tests** — This is the single largest quality gap across the entire framework.

### Compliance Summary

| Harness | Capability Tier | Mandatory Features | Production Ready | Primary Risk |
|---------|----------------|-------------------|-----------------|--------------|
| **OpenCode** | A (Reference) | 14/14 ✅ | Yes | Provider hardcoding; fragile parser |
| **Claude Code** | A | 12/14 ⚠️ | Yes | Drift from docs/AGENTS.md |
| **π.dev** | B | 8/9 ⚠️ | Beta | Manual sync; structural drift |
| **Copilot CLI** | C | 7/8 ⚠️ | Yes | Missing install documentation |

### Recommended Priority Order

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| P1 | Automated harness test suite | 16h | Highest — no regression detection |
| P2 | Copilot CLI install guide | 2h | Quick win — closes last doc gap |
| P3 | Model freshness check script | 3h | Prevents silent model staleness |
| P4 | π.dev sync validation script | 2h | Mitigates highest drift risk |
| P5 | Claude Code docs/AGENTS.md lookup | 4h | Closes medium-priority parity gap |
| P6 | π.dev argument parsing fix | 2h | Fixes confirmed bug |
| P7 | π.dev premature mkdir fix | 0.25h | Trivial correctness fix |
| P8 | Provider auto-detection (OpenCode) | 6h | Enables multi-provider support |

---

## 2. Harness Overview & Architecture

### 2.1 The Four Harnesses

The agentic-engineers framework supports four distinct AI coding assistant platforms, each with a dedicated renderer:

| Harness | Renderer | Destination | Platform |
|---------|----------|-------------|----------|
| **OpenCode** | `render-opencode.sh` | `~/.config/opencode/` | OpenCode AI assistant |
| **Claude Code** | `render-claude.sh` | `~/.claude/` | Anthropic Claude Code |
| **π.dev** | `render-pi-dev.py` + `render-pi.sh` | `~/.pi/agent/` | π.dev AI assistant |
| **Copilot CLI** | `render-copilot.sh` | `~/.copilot/skills/` | GitHub Copilot CLI |

### 2.2 Architectural Patterns

Three distinct architectural patterns exist across the harnesses:

**Pattern 1: Dynamic Transform (OpenCode, Claude Code)**

Source files are transformed at install time. Model IDs, descriptions, and frontmatter are mapped to platform-specific formats. Changes to canonical sources (`docs/AGENTS.md`, `src/agents/`) propagate automatically on next install. This is the most maintainable pattern.

```
src/agents/*-agent.md  ──┐
docs/AGENTS.md  ──────────┤→ render script → platform-specific files
src/skills/*/SKILL.md  ──┘
```

**Pattern 2: Static Copy (π.dev)**

Manually-maintained source files are copied verbatim. No transformation occurs. Changes to canonical sources do NOT propagate automatically — `renderer/pi-dev-src/` must be manually kept in sync. This is the highest-maintenance pattern and the primary drift risk.

```
renderer/pi-dev-src/  ──→ Python renderer → ~/.pi/agent/
```

**Pattern 3: Skills-Only (Copilot CLI)**

Only skills are installed; agents are not supported by the platform. Intentionally minimal and correct for the platform's capabilities.

```
src/skills/*/SKILL.md  ──→ render-copilot.sh → ~/.copilot/skills/
```

### 2.3 Shared Code (lib.sh)

After the Phase 2 `lib.sh` extraction, the following functions are shared across harnesses:

| Function | Purpose | Used By |
|----------|---------|---------|
| `list_source_skills` | Enumerate skill directories | OpenCode, Claude Code, Copilot CLI |
| `list_source_agents` | Enumerate agent files | OpenCode, Claude Code |
| `extract_fm` | Extract frontmatter key/value | OpenCode, Claude Code |
| `strip_fm` | Remove frontmatter from file | OpenCode, Claude Code |
| `extract_body_model` | Extract model ID from body text | OpenCode, Claude Code |

**Remaining duplication** (not yet extracted):
- Skills install/uninstall/status loop logic (~40 lines each, structurally identical across three Bash harnesses)
- Git hooks installation block (~10 lines, duplicated in all three Bash harnesses)

### 2.4 Safety Model Comparison

All harnesses implement some form of managed-file protection, but with varying sophistication:

| Safety Feature | OpenCode | Claude Code | π.dev | Copilot CLI |
|----------------|:--------:|:-----------:|:-----:|:-----------:|
| Per-skill marker files | ✅ | ✅ | ❌ | ✅ |
| Agent manifest (sidecar) | ✅ | ✅ | N/A | N/A |
| Atomic writes (.tmp + mv) | ✅ | ✅ | ❌ | ❌ |
| Foreign file protection | ✅ Full | ✅ Full | ⚠️ Partial | ✅ Full |
| Sentinel comments in files | ✅ JSONC + HTML | ❌ | ❌ | ❌ |
| Install-level marker | ✅ | ✅ | ✅ | ✅ |

**Key insight:** OpenCode's sentinel-based safety model (JSONC comments in config files, HTML comments in Markdown files, per-skill timestamp markers, atomic manifest writes) is the most robust and should be adopted as the standard for other harnesses where applicable.

---

## 3. Unified Feature Matrix

This matrix covers 26 features across all four harnesses, organized by category.

### 3.1 Core Rendering

| Feature | OpenCode | Claude Code | π.dev | Copilot CLI | Notes |
|---------|:--------:|:-----------:|:-----:|:-----------:|-------|
| Agent rendering | ✅ Dynamic | ✅ Dynamic | ⚠️ Static | ❌ N/A | Platform constraint for Copilot CLI |
| Skill rendering | ✅ 14 skills | ✅ 14 skills | ❌ None | ✅ 14 skills | π.dev has no skill support |
| Canonical 8 roles | ✅ | ✅ | ✅ | N/A | π.dev updated in Phase 2 |
| Content transformation | ✅ | ✅ | ❌ | N/A | π.dev copies static files |
| Idempotent installs | ✅ | ✅ | ✅ | ✅ | All harnesses safe to re-run |

### 3.2 Metadata Strategy

| Feature | OpenCode | Claude Code | π.dev | Copilot CLI | Notes |
|---------|:--------:|:-----------:|:-----:|:-----------:|-------|
| docs/AGENTS.md lookup | ✅ | ❌ | ❌ | N/A | Claude Code gap (Medium priority) |
| Source frontmatter | ✅ | ✅ | N/A | N/A | Both Tier A harnesses |
| Hybrid metadata strategy | ✅ | ❌ | N/A | N/A | OpenCode only |
| Body model extraction | ✅ | ✅ | N/A | N/A | Fallback chain |
| Model IDs (current) | ✅ Full IDs | ⚠️ Tier names | ✅ Current | N/A | Claude Code version-agnostic |
| Effort → temperature | ✅ 0.3/0.5 | ❌ | N/A | N/A | Low priority gap |
| YAML description escaping | ✅ Proper | ⚠️ Simple | N/A | N/A | Minor Claude Code gap |

### 3.3 Configuration Management

| Feature | OpenCode | Claude Code | π.dev | Copilot CLI | Notes |
|---------|:--------:|:-----------:|:-----:|:-----------:|-------|
| Config file (managed) | ✅ opencode.jsonc | ❌ N/A | ⚠️ settings.json | ❌ N/A | By design for Claude Code, Copilot |
| Global rules file | ✅ AGENTS.md | ❌ N/A | ⚠️ SYSTEM.md | ❌ N/A | By design |
| Compaction tuning | ✅ 30K tokens | ❌ | ❌ | ❌ | OpenCode-specific |
| Permission lockdown | ✅ | ❌ | ❌ | ❌ | OpenCode-specific |
| Custom provider entry | ✅ | ❌ | ❌ | ❌ | OpenCode-specific |
| Speculative features marked | N/A | N/A | ✅ | N/A | π.dev pi.yml/settings.json |

### 3.4 Lifecycle Management

| Feature | OpenCode | Claude Code | π.dev | Copilot CLI | Notes |
|---------|:--------:|:-----------:|:-----:|:-----------:|-------|
| Install mode | ✅ | ✅ | ✅ | ✅ | All complete |
| Uninstall mode | ✅ | ✅ | ✅ | ✅ | All complete |
| Status/drift detection | ✅ | ✅ | ✅ | ✅ | All complete |
| Git hooks installation | ✅ | ✅ | ✅ | ✅ | All complete |

### 3.5 Safety & Protection

| Feature | OpenCode | Claude Code | π.dev | Copilot CLI | Notes |
|---------|:--------:|:-----------:|:-----:|:-----------:|-------|
| Per-skill marker files | ✅ | ✅ | ❌ | ✅ | π.dev gap |
| Agent manifest tracking | ✅ | ✅ | N/A | N/A | Tier A required |
| Foreign file protection | ✅ Full | ✅ Full | ⚠️ Partial | ✅ Full | π.dev partial |
| Atomic writes | ✅ | ✅ | ❌ | ❌ | Tier A recommended |
| Sentinel comments | ✅ | ❌ | ❌ | ❌ | OpenCode best practice |
| Rollback on partial failure | ❌ | ❌ | ❌ | ❌ | Gap across all harnesses |

### 3.6 Documentation & Testing

| Feature | OpenCode | Claude Code | π.dev | Copilot CLI | Notes |
|---------|:--------:|:-----------:|:-----:|:-----------:|-------|
| Dedicated install guide | ✅ | ✅ | ✅ | ❌ | Copilot CLI gap |
| Troubleshooting section | ✅ | ⚠️ Partial | ⚠️ Partial | ❌ | Gaps in Claude Code, Copilot |
| Inline code documentation | ✅ | ✅ | ✅ | ✅ | All adequate |
| Limitation comments | ✅ | ⚠️ | ✅ | ⚠️ | Minor gaps |
| Change log | ❌ | ❌ | ❌ | ❌ | Missing across all |
| Automated tests | ❌ | ❌ | ❌ | ❌ | **Critical gap — all harnesses** |
| CI integration | ❌ | ❌ | ❌ | ❌ | No CI for harness tests |

### 3.7 Parity Scores

| Harness | Mandatory Features | Recommended Features | Documentation | Overall |
|---------|:-----------------:|:-------------------:|:-------------:|:-------:|
| OpenCode | 14/14 (100%) | 2/7 (29%) | 6/8 (75%) | **Reference** |
| Claude Code | 12/14 (86%) | 2/7 (29%) | 5/8 (63%) | **Good** |
| π.dev | 8/9 (89%) | 0/4 (0%) | 5/8 (63%) | **Beta** |
| Copilot CLI | 7/8 (88%) | 1/5 (20%) | 3/8 (38%) | **Good** |

---

## 4. Consolidated Gap Analysis

Gaps are organized by tier (critical/important/strategic) and cross-referenced to the source Phase 1 documents.

### 4.1 Tier 1 — Critical Gaps (Address Immediately)

These gaps represent confirmed bugs, missing safety features, or documentation failures that affect user experience or system correctness.

#### Gap T1-1: No Automated Tests (All Harnesses)
**Severity:** Critical  
**Affected:** All four harnesses  
**Description:** No harness has any automated tests. There is no regression detection, no lifecycle verification, and no cross-harness parity checking. Any change to a renderer script could silently break install, uninstall, or status behavior.  
**Impact:** High — any refactor or model update could introduce silent regressions  
**Effort:** 16 hours  
**Source:** `HARNESS-CONSISTENCY-FRAMEWORK.md` §5  
**Recommended fix:** Implement test suite covering: lib.sh unit tests, per-harness integration tests (install/uninstall/status/idempotency/foreign-protection), cross-harness parity tests, model freshness tests.

---

#### Gap T1-2: Copilot CLI Missing Install Documentation
**Severity:** High  
**Affected:** Copilot CLI  
**Description:** No dedicated `COPILOT-INSTALL.md` exists. Users must rely on inline Makefile comments. All other harnesses have comprehensive installation guides.  
**Impact:** Medium — users don't understand why agents are omitted, how to troubleshoot, or how to uninstall  
**Effort:** 2 hours  
**Source:** `COPILOT-CLI-HARNESS-ANALYSIS.md` §6.1  
**Recommended fix:** Create `docs/COPILOT-INSTALL.md` mirroring the structure of `OPENCODE-INSTALL.md` and `CLAUDE-INSTALL.md`, explicitly documenting why agents are not supported.

---

#### Gap T1-3: π.dev Premature Directory Creation Bug
**Severity:** High  
**Affected:** π.dev  
**Description:** `PiDevRenderer.__init__()` unconditionally creates `~/.pi/agent/` before the mode (install/status/uninstall) is determined. This causes `--status` to report "installed" on a clean system (false positive) and `--uninstall` to create then immediately find an empty directory.  
**Impact:** Medium — silent false-positive status reports; misleading uninstall behavior  
**Effort:** 15 minutes  
**Source:** `PI-DEV-RENDERER-ANALYSIS.md` §1 Bug 2  
**Recommended fix:** Move `self.agent_dir.mkdir(parents=True, exist_ok=True)` from `__init__()` to `render_all()` only.

---

#### Gap T1-4: No Model Freshness Validation (All Harnesses)
**Severity:** High  
**Affected:** All harnesses (especially π.dev, Claude Code)  
**Description:** No automated mechanism detects when model IDs in harnesses drift from the canonical list in `docs/AGENTS.md`. The π.dev harness had stale model IDs (`claude-3-5-sonnet-20241022`) that were only caught by manual review. Claude Code uses tier names only (version-agnostic), which masks version staleness.  
**Impact:** High — stale model IDs silently degrade agent quality without user awareness  
**Effort:** 3 hours  
**Source:** `PI-DEV-RENDERER-ANALYSIS.md` §2 Limitation 3; `HARNESS-CONSISTENCY-FRAMEWORK.md` §7.1  
**Recommended fix:** Implement `renderer/scripts/check-model-freshness.sh` that parses `docs/AGENTS.md` for canonical model IDs and verifies each harness's model mapping covers them. Integrate into `make verify` and pre-push hook.

---

#### Gap T1-5: π.dev No Per-File Sentinel Protection
**Severity:** Medium  
**Affected:** π.dev  
**Description:** π.dev has a single install-level marker file (`.agentic-engine-pi`) but no per-file markers. If a user edits `~/.pi/agent/AGENTS.md` directly, the next `make install-pi` will silently overwrite their changes without warning.  
**Impact:** Medium — potential silent data loss for users who edit managed files  
**Effort:** 3–4 hours  
**Source:** `PI-DEV-RENDERER-ANALYSIS.md` §2 Limitation 2  
**Recommended fix:** Add sentinel header to each rendered file; check for sentinel before overwriting; require `--force` to proceed if sentinel absent.

---

### 4.2 Tier 2 — Important Improvements (Address in Phase 3)

These gaps reduce maintainability, increase drift risk, or represent meaningful feature parity shortfalls.

#### Gap T2-1: Claude Code No docs/AGENTS.md Lookup
**Severity:** Medium  
**Affected:** Claude Code  
**Description:** Claude Code reads model/description from source frontmatter only. It does not consult `docs/AGENTS.md` (the canonical source of truth). If `docs/AGENTS.md` is updated (e.g., model changed), Claude Code agents won't reflect the change until source frontmatter is also manually updated.  
**Impact:** Medium — drift risk between OpenCode and Claude Code agent configurations  
**Effort:** 1–2 hours  
**Source:** `CLAUDE-CODE-HARNESS-ANALYSIS.md` §3 Gap 1  
**Recommended fix:** Copy `docs_lookup_role()` function from `render-opencode.sh` to `render-claude.sh`; adapt to Claude Code's simpler frontmatter format.

---

#### Gap T2-2: π.dev Argument Parsing Heuristic Bug
**Severity:** Medium  
**Affected:** π.dev  
**Description:** `render-pi-dev.py` uses a string-matching heuristic (`"/.pi" in argv[0]`) to determine whether a single positional argument is a source or destination directory. This silently misroutes edge-case paths (e.g., source dirs containing `.pi` in the name, destinations not under home).  
**Impact:** Medium — silent wrong behavior; no error raised until file operation fails  
**Effort:** 2 hours  
**Source:** `PI-DEV-RENDERER-ANALYSIS.md` §1 Bug 1  
**Recommended fix:** Replace heuristic with explicit `argparse` named flags (`--src`, `--dest`); preserve backward-compatible positional args.

---

#### Gap T2-3: π.dev No Content Transformation Pipeline
**Severity:** Medium  
**Affected:** π.dev  
**Description:** The π.dev renderer copies files from `renderer/pi-dev-src/` verbatim. Unlike OpenCode and Claude Code, it does not pull content from `src/agents/` or apply any transformation pipeline. Five source files must be manually kept in sync with canonical sources.  
**Impact:** High (structural) — any change to canonical agent model requires manual updates to 4–5 files; drift is structurally inevitable  
**Effort:** 8–12 hours (full pipeline); 2 hours (sync check only)  
**Source:** `PI-DEV-RENDERER-ANALYSIS.md` §2 Limitation 1  
**Recommended fix (short-term):** Add `make check-pi-sync` target that diffs `renderer/pi-dev-src/AGENTS.md` against `docs/AGENTS.md` and fails if they diverge. **Recommended fix (long-term):** Implement transformation pipeline generating `pi-dev-src/` files from `src/agents/` and `docs/AGENTS.md`.

---

#### Gap T2-4: Claude Code YAML Description Escaping
**Severity:** Low  
**Affected:** Claude Code  
**Description:** Claude Code uses simple double-to-single quote replacement (`${desc//\"/\'}`) instead of proper YAML escaping. Descriptions containing single quotes will produce invalid YAML.  
**Impact:** Low — only affects descriptions with single quotes; no current agent descriptions contain them  
**Effort:** 30 minutes  
**Source:** `CLAUDE-CODE-HARNESS-ANALYSIS.md` §2.5  
**Recommended fix:** Use `yaml_escape_inline()` function (already in `lib.sh` or add it) for proper YAML escaping with newline collapse.

---

#### Gap T2-5: π.dev Speculative Features Not Documented in Primary Guide
**Severity:** Medium  
**Affected:** π.dev  
**Description:** `PI-DEV-RENDERER.md` presents `pi.yml` as enabling "Sub-agent orchestration configuration" without noting that the routing rules are unverified against the actual π.dev runtime. Users reading only this file will not know the limitation.  
**Impact:** Medium — user confusion; wasted effort configuring features that may have no effect  
**Effort:** 1 hour  
**Source:** `PI-DEV-RENDERER-ANALYSIS.md` §3 Gap 2  
**Recommended fix:** Add "Known Limitations" section to `PI-DEV-RENDERER.md` mirroring the warnings already present in `pi.yml` and `SUB_AGENT_SETUP.md`.

---

#### Gap T2-6: No Rollback on Partial Failure (OpenCode, Claude Code)
**Severity:** Low  
**Affected:** OpenCode, Claude Code  
**Description:** If a render fails mid-way (e.g., rsync error on skill 7 of 14), already-rendered files remain in place. The agent manifest uses atomic `.tmp` → `mv` writes, but skills have no equivalent rollback.  
**Impact:** Low — incomplete installation that may cause confusion; re-running install fixes it  
**Effort:** 2 hours per harness  
**Source:** `OPENCODE-HARNESS-BEST-PRACTICES.md` §3.1 Limitation 4  
**Recommended fix:** Track rendered skills in a temporary manifest; roll back on error.

---

#### Gap T2-7: OpenCode Provider Hardcoding
**Severity:** Medium  
**Affected:** OpenCode  
**Description:** Model IDs in `render-opencode.sh` are hardcoded to the `github-copilot/` provider. Users with the `anthropic/` provider would need different IDs (e.g., `anthropic/claude-haiku-4-5`).  
**Impact:** Medium — limits portability; users on non-GitHub-Copilot providers cannot use the harness without manual modification  
**Effort:** 6 hours  
**Source:** `OPENCODE-HARNESS-BEST-PRACTICES.md` §3.1 Limitation 1  
**Recommended fix:** Implement provider auto-detection at install time using `opencode models` output; select appropriate model ID format dynamically.

---

#### Gap T2-8: OpenCode Fragile docs/AGENTS.md Table Parser
**Severity:** Medium  
**Affected:** OpenCode  
**Description:** The awk parser for the `docs/AGENTS.md` markdown table is sensitive to formatting changes (column order, bold markers, spacing). If the table format changes, the parser silently returns empty, causing agents to be skipped with no error.  
**Impact:** Medium — silent failure; all agents skipped if table format changes  
**Effort:** 1–2 hours  
**Source:** `OPENCODE-HARNESS-BEST-PRACTICES.md` §3.1 Limitation 2  
**Recommended fix:** Add validation step that warns if `docs_lookup_role` returns empty for all agents; fail loudly rather than silently.

---

#### Gap T2-9: π.dev PyYAML Undocumented Dependency
**Severity:** Low  
**Affected:** π.dev  
**Description:** `render-pi-dev.py` imports `yaml` (PyYAML) for YAML validation, but this is not documented in `PI-DEV-RENDERER.md` and causes a hard `ImportError` on minimal Python environments.  
**Impact:** Low — setup friction; hard failure with no guidance  
**Effort:** 30 minutes  
**Source:** `PI-DEV-RENDERER-ANALYSIS.md` §2 Limitation 6  
**Recommended fix:** Add graceful fallback (`try/except ImportError`) with warning message; document PyYAML as a prerequisite in `PI-DEV-RENDERER.md`.

---

#### Gap T2-10: No Cross-Harness Parity Status Target
**Severity:** Low  
**Affected:** All harnesses  
**Description:** No `make status-parity` target exists to compare feature parity across all harnesses simultaneously. Users must check each harness individually.  
**Impact:** Low — operational inconvenience; no single view of cross-harness health  
**Effort:** 3 hours  
**Source:** `HARNESS-CONSISTENCY-FRAMEWORK.md` §7.1  
**Recommended fix:** Implement `make status-parity` that reports installed status, agent/skill counts, and known parity gaps for all four harnesses.

---

### 4.3 Tier 3 — Strategic Improvements (Phase 4+)

These items address architectural limitations and enable long-term maintainability. Higher effort, higher long-term value.

#### Gap T3-1: π.dev API Verification
**Severity:** Low  
**Affected:** π.dev  
**Description:** `settings.json` and `pi.yml` contain `packages`, `extensions`, `skills`, and `routing.rules` keys that are not verified against the actual π.dev runtime. These may have no effect.  
**Impact:** Low — system works via `SYSTEM.md` prompt-based routing regardless  
**Effort:** 4 hours (requires π.dev access and testing)  
**Source:** `PI-DEV-RENDERER-ANALYSIS.md` §2 Limitation 5  
**Recommended fix:** Verify π.dev API against actual runtime; remove unverified keys or replace with verified equivalents.

---

#### Gap T3-2: Claude Code Effort → Temperature Mapping
**Severity:** Low  
**Affected:** Claude Code  
**Description:** Claude Code agents don't include `temperature` in frontmatter. OpenCode maps effort (low/medium → 0.3, high/max → 0.5). This information is lost for Claude Code.  
**Impact:** Low — Claude Code uses default temperature; effort is tracked by Orchestrator routing  
**Effort:** 1 hour (if Claude Code supports temperature)  
**Source:** `CLAUDE-CODE-HARNESS-ANALYSIS.md` §3 Gap 2  
**Recommended fix:** Verify Claude Code agent schema supports `temperature` field; implement mapping if supported.

---

#### Gap T3-3: Unified Harness Interface (render-all.sh)
**Severity:** Low  
**Affected:** All harnesses  
**Description:** No meta-script exists to invoke all harnesses consistently. Users must run separate commands for each harness.  
**Impact:** Low — operational convenience  
**Effort:** 2–3 hours  
**Source:** `CLAUDE-CODE-HARNESS-ANALYSIS.md` §5.1  
**Recommended fix:** Create `renderer/scripts/render-all.sh` that calls all four renderers with unified `--status` output.

---

#### Gap T3-4: Source Hash in Marker Files
**Severity:** Low  
**Affected:** All harnesses  
**Description:** Skill marker files contain only a timestamp. If source files are updated but the harness hasn't been re-run, `--status` won't detect the staleness (it compares destination against source, which is correct, but the marker provides no provenance).  
**Impact:** Low — `--status` already detects drift correctly via diff  
**Effort:** 3 hours  
**Source:** `HARNESS-CONSISTENCY-FRAMEWORK.md` §7.2  
**Recommended fix:** Add SHA-256 hash of source directory to marker file content; use in status reporting.

---

#### Gap T3-5: Incremental Rendering (OpenCode)
**Severity:** Low  
**Affected:** OpenCode  
**Description:** No way to re-render a single agent or skill without running the full install.  
**Impact:** Low — developer experience; full install is fast enough for most use cases  
**Effort:** 3 hours  
**Source:** `OPENCODE-HARNESS-BEST-PRACTICES.md` §4.3  
**Recommended fix:** Add `--agent <name>` and `--skill <name>` flags for incremental rendering.

---

#### Gap T3-6: Quarterly Review Automation
**Severity:** Low  
**Affected:** All harnesses  
**Description:** No automated script runs the quarterly review checklist (model IDs, role counts, documentation currency, platform compatibility).  
**Impact:** Low — process gap; manual reviews are currently ad-hoc  
**Effort:** 4 hours  
**Source:** `HARNESS-CONSISTENCY-FRAMEWORK.md` §7.4  
**Recommended fix:** Implement `renderer/scripts/quarterly-review.sh` that runs all checklist items automatically.

---

### 4.4 Gap Summary by Harness

| Gap ID | Description | Harness | Tier | Effort |
|--------|-------------|---------|------|--------|
| T1-1 | No automated tests | All | 1 | 16h |
| T1-2 | Missing Copilot install guide | Copilot CLI | 1 | 2h |
| T1-3 | π.dev premature mkdir bug | π.dev | 1 | 0.25h |
| T1-4 | No model freshness validation | All | 1 | 3h |
| T1-5 | π.dev no per-file sentinels | π.dev | 1 | 3–4h |
| T2-1 | Claude Code no AGENTS.md lookup | Claude Code | 2 | 1–2h |
| T2-2 | π.dev argument parsing bug | π.dev | 2 | 2h |
| T2-3 | π.dev no transformation pipeline | π.dev | 2 | 2–12h |
| T2-4 | Claude Code YAML escaping | Claude Code | 2 | 0.5h |
| T2-5 | π.dev speculative features undocumented | π.dev | 2 | 1h |
| T2-6 | No rollback on partial failure | OpenCode, Claude Code | 2 | 4h |
| T2-7 | OpenCode provider hardcoding | OpenCode | 2 | 6h |
| T2-8 | OpenCode fragile AGENTS.md parser | OpenCode | 2 | 1–2h |
| T2-9 | π.dev PyYAML undocumented | π.dev | 2 | 0.5h |
| T2-10 | No cross-harness parity status | All | 2 | 3h |
| T3-1 | π.dev API verification | π.dev | 3 | 4h |
| T3-2 | Claude Code temperature mapping | Claude Code | 3 | 1h |
| T3-3 | Unified harness interface | All | 3 | 2–3h |
| T3-4 | Source hash in markers | All | 3 | 3h |
| T3-5 | Incremental rendering | OpenCode | 3 | 3h |
| T3-6 | Quarterly review automation | All | 3 | 4h |

---

## 5. Implementation Roadmap

### 5.1 Phase 3A — Critical Fixes (Week 1, ~21 hours)

**Goal:** Close all Tier 1 gaps; establish test infrastructure.

| # | Item | Gap | Effort | Owner | Success Criteria |
|---|------|-----|--------|-------|-----------------|
| 3A.1 | Fix π.dev premature mkdir | T1-3 | 0.25h | Engineer | `--status` on clean system reports "not installed" |
| 3A.2 | Create `docs/COPILOT-INSTALL.md` | T1-2 | 2h | Engineer | Guide covers install, uninstall, status, why no agents |
| 3A.3 | Add PyYAML graceful fallback + docs | T2-9 | 0.5h | Engineer | `ImportError` replaced with warning; prerequisite documented |
| 3A.4 | Document π.dev speculative features | T2-5 | 1h | Engineer | `PI-DEV-RENDERER.md` has "Known Limitations" section |
| 3A.5 | Implement model freshness check | T1-4 | 3h | Engineer | `check-model-freshness.sh` exits non-zero on stale IDs |
| 3A.6 | Implement π.dev sync validation | T2-3 (partial) | 2h | Engineer | `check-pi-dev-sync.sh` detects AGENTS.md drift |
| 3A.7 | Add post-merge hook for model ID changes | T1-4 | 1h | Engineer | Hook warns when `docs/AGENTS.md` model IDs change |
| 3A.8 | Implement harness test suite (Phase 1) | T1-1 | 12h | Senior Engineer | lib.sh unit tests + OpenCode integration tests pass |

**Total Phase 3A effort:** ~21.75 hours  
**Recommended timeline:** 1 week  
**Blocking dependencies:** None — all items independent

---

### 5.2 Phase 3B — Quality Improvements (Weeks 2–3, ~22 hours)

**Goal:** Close high-priority Tier 2 gaps; complete test coverage.

| # | Item | Gap | Effort | Owner | Success Criteria |
|---|------|-----|--------|-------|-----------------|
| 3B.1 | Fix π.dev argument parsing (argparse) | T2-2 | 2h | Engineer | Explicit `--src`/`--dest` flags; no heuristic |
| 3B.2 | Add Claude Code docs/AGENTS.md lookup | T2-1 | 2h | Engineer | All 8 agents render with canonical model/description |
| 3B.3 | Fix Claude Code YAML description escaping | T2-4 | 0.5h | Engineer | Descriptions with single quotes render correctly |
| 3B.4 | Add π.dev per-file sentinel headers | T1-5 | 4h | Engineer | Re-render warns before overwriting manually edited files |
| 3B.5 | Harden OpenCode AGENTS.md table parser | T2-8 | 2h | Engineer | Parse failure produces loud error, not silent empty |
| 3B.6 | Extract skills loops + git hooks to lib.sh | (shared) | 4h | Engineer | ~80 lines of duplication removed |
| 3B.7 | Add `make status-parity` target | T2-10 | 3h | Engineer | Single command shows cross-harness health |
| 3B.8 | Complete test suite (Claude Code, Copilot, π.dev) | T1-1 | 5h | Senior Engineer | All four harnesses have integration tests |

**Total Phase 3B effort:** ~22.5 hours  
**Recommended timeline:** 2 weeks  
**Dependencies:** Phase 3A complete (especially lib.sh extraction)

---

### 5.3 Phase 3C — Strategic Improvements (Weeks 4–7, ~30 hours)

**Goal:** Address architectural limitations; add CI; close remaining Tier 2 gaps.

| # | Item | Gap | Effort | Owner | Success Criteria |
|---|------|-----|--------|-------|-----------------|
| 3C.1 | OpenCode provider auto-detection | T2-7 | 6h | Senior Engineer | Harness works with anthropic/ and github-copilot/ providers |
| 3C.2 | Add rollback on partial failure | T2-6 | 4h | Engineer | Failed render leaves no partial state |
| 3C.3 | Add CI workflow for harness tests | T1-1 | 2h | Engineer | GitHub Actions runs `make test-harness` on push |
| 3C.4 | π.dev dynamic transformation pipeline | T2-3 | 12h | Senior Engineer | `pi-dev-src/` generated from `src/agents/`; no manual sync |
| 3C.5 | Unified harness interface (render-all.sh) | T3-3 | 3h | Engineer | Single command installs/checks all harnesses |
| 3C.6 | Quarterly review automation | T3-6 | 4h | Engineer | Script runs all checklist items; exits non-zero on failures |

**Total Phase 3C effort:** ~31 hours  
**Recommended timeline:** 4 weeks  
**Dependencies:** Phase 3B complete

---

### 5.4 Phase 4+ — Nice-to-Have (Future)

| # | Item | Gap | Effort | Notes |
|---|------|-----|--------|-------|
| 4.1 | Claude Code effort → temperature mapping | T3-2 | 1h | Requires Claude Code schema verification first |
| 4.2 | Source hash in marker files | T3-4 | 3h | Low ROI; `--status` already detects drift |
| 4.3 | Incremental rendering (OpenCode) | T3-5 | 3h | Developer experience improvement |
| 4.4 | π.dev API verification | T3-1 | 4h | Requires π.dev access and testing |
| 4.5 | Claude Code troubleshooting guide | (doc) | 2h | Currently inline only |
| 4.6 | OpenCode drift repair (`--repair` flag) | (UX) | 1h | One-command fix for drifted files |
| 4.7 | OpenCode dry-run mode | (UX) | 1h | Preview before rendering |

---

### 5.5 Effort Summary

| Phase | Items | Total Effort | Timeline | Priority |
|-------|-------|-------------|----------|----------|
| **3A** (Critical) | 8 items | ~22h | Week 1 | Must Do |
| **3B** (Quality) | 8 items | ~23h | Weeks 2–3 | Should Do |
| **3C** (Strategic) | 6 items | ~31h | Weeks 4–7 | Important |
| **4+** (Future) | 7 items | ~15h | Phase 4+ | Nice to Have |
| **Total** | **29 items** | **~91h** | **7 weeks** | — |

---

## 6. Risk Assessment

### 6.1 Risk Matrix

| Risk | Likelihood | Impact | Mitigation | Gap ID |
|------|-----------|--------|-----------|--------|
| Model IDs drift silently across harnesses | **High** | Medium | T1-4: freshness check script | T1-4 |
| π.dev content diverges from canonical sources | **High** | Medium | T2-3: sync validation + pipeline | T2-3 |
| Harness regression introduced by refactor | **Medium** | High | T1-1: automated test suite | T1-1 |
| OpenCode AGENTS.md parser silently fails | **Medium** | High | T2-8: parser hardening | T2-8 |
| Claude Code agents drift from docs/AGENTS.md | **Medium** | Medium | T2-1: AGENTS.md lookup | T2-1 |
| π.dev `--status` false positive on clean system | **Medium** | Low | T1-3: defer mkdir | T1-3 |
| User edits π.dev managed files; silently overwritten | **Low** | Medium | T1-5: per-file sentinels | T1-5 |
| π.dev argument parsing misroutes edge-case paths | **Low** | Medium | T2-2: argparse fix | T2-2 |
| OpenCode breaks on non-github-copilot provider | **Low** | High | T2-7: provider auto-detection | T2-7 |
| π.dev PyYAML not installed | **Low** | Low | T2-9: graceful fallback | T2-9 |
| π.dev routing rules have no effect | **High** (already true) | Low | T2-5: document clearly | T2-5 |

### 6.2 Highest-Risk Items

**Immediate action required:**

1. **Silent model staleness** — The π.dev harness has already experienced stale model IDs once (caught only by manual review). Without an automated freshness check, this will recur. The Claude Code harness's tier-name model mapping masks version staleness entirely.

2. **No regression detection** — With no automated tests, any change to any renderer script could silently break install, uninstall, or status behavior. This risk compounds as the codebase evolves.

3. **π.dev structural drift** — The static-copy architecture guarantees that `renderer/pi-dev-src/` will drift from canonical sources over time. Every model update, role change, or documentation improvement requires manual synchronization across 4–5 files.

---

## 7. Cross-Harness Recommendations

### 7.1 Adopt OpenCode Patterns Across All Harnesses

OpenCode's architecture represents the gold standard for this framework. The following patterns should be adopted by other harnesses where applicable:

**Sentinel-based safety model:**
- JSONC comments for JSON/JSONC config files (avoids schema validation failures)
- HTML comments for Markdown files (line 1, detectable with `head`)
- Per-item timestamp marker files for directories
- Atomic manifest writes (`.tmp` → `mv`) for agent collections

**Hybrid metadata strategy:**
- `docs/AGENTS.md` as authoritative source for model/effort/description
- Source frontmatter as fallback
- Body content as final fallback
- Clear precedence prevents ambiguity

**Validation at render time:**
- Warn loudly if metadata lookup fails for all agents (not silent empty)
- Check prerequisites (`rsync`, `python3`, etc.) before starting
- Report per-item status with consistent emoji conventions

### 7.2 Establish the Tiered Parity Model

Not all features are achievable on all platforms. The tiered model (defined in `HARNESS-CONSISTENCY-FRAMEWORK.md`) should be the authoritative standard for evaluating each harness:

- **Tier A** (OpenCode, Claude Code): Full-featured with dynamic transformation
- **Tier B** (π.dev): Partial-transform with static source files
- **Tier C** (Copilot CLI): Skills-only by platform constraint

Each harness should be evaluated against its tier's mandatory features, not against a universal standard that ignores platform constraints.

### 7.3 Invest in the Test Suite First

The single highest-leverage investment is the automated test suite. With 16 hours of effort, the framework gains:
- Regression detection for all four harnesses
- Confidence to refactor shared code without breaking installs
- Cross-harness parity verification
- Model freshness validation

Without tests, every improvement carries the risk of silent regression.

### 7.4 Prioritize π.dev Structural Fixes

The π.dev harness carries the most structural risk. The static-copy architecture is a fundamental design limitation that will compound over time. The recommended investment sequence:

1. **Immediate (0.25h):** Fix premature mkdir bug
2. **Short-term (2h):** Fix argument parsing bug
3. **Short-term (2h):** Add sync validation script
4. **Medium-term (12h):** Implement transformation pipeline

The transformation pipeline is the only permanent solution to the drift problem, but the sync validation script provides meaningful protection at much lower cost.

### 7.5 Maintain the Quarterly Review Checklist

The `HARNESS-CONSISTENCY-FRAMEWORK.md` quarterly review checklist should be formalized as a scheduled process. Key items:
- Model IDs in all harnesses match `docs/AGENTS.md` canonical list
- All harnesses reference exactly 8 canonical roles
- All installation guides are accurate and current
- Platform compatibility (directory paths, config formats) verified

---

## 8. Source Document Index

This master document synthesizes findings from five Phase 1 analysis documents. All findings are cross-referenced below.

| Document | Author | Lines | Key Findings |
|----------|--------|-------|--------------|
| [`docs/PI-DEV-RENDERER-ANALYSIS.md`](PI-DEV-RENDERER-ANALYSIS.md) | Senior Engineer | 433 | 2 confirmed bugs, 6 structural limitations, 3 documentation gaps, Tier 1/2/3 roadmap for π.dev |
| [`docs/CLAUDE-CODE-HARNESS-ANALYSIS.md`](CLAUDE-CODE-HARNESS-ANALYSIS.md) | Engineer | 1,010 | 5 feature gaps, comparison matrices vs. OpenCode/Copilot/π.dev, Phase 3–5 roadmap |
| [`docs/COPILOT-CLI-HARNESS-ANALYSIS.md`](COPILOT-CLI-HARNESS-ANALYSIS.md) | Engineer | 597 | Design constraints analysis, intentional minimalism justification, Tier 1/2/3 expansion opportunities |
| [`docs/OPENCODE-HARNESS-BEST-PRACTICES.md`](OPENCODE-HARNESS-BEST-PRACTICES.md) | Engineer | 1,265 | Architecture deep-dive, 20 best practices, 11 improvement opportunities, testing strategy |
| [`docs/HARNESS-CONSISTENCY-FRAMEWORK.md`](HARNESS-CONSISTENCY-FRAMEWORK.md) | Lead Engineer | 946 | Tiered parity model, unified interface contract, testing strategy, drift prevention mechanisms, 21-item roadmap |

### Key Cross-References

| Topic | Primary Source | Secondary Sources |
|-------|---------------|------------------|
| π.dev bugs | `PI-DEV-RENDERER-ANALYSIS.md` §1 | `HARNESS-CONSISTENCY-FRAMEWORK.md` §8.3 |
| Claude Code gaps | `CLAUDE-CODE-HARNESS-ANALYSIS.md` §3 | `HARNESS-CONSISTENCY-FRAMEWORK.md` §3.2 |
| Copilot CLI design rationale | `COPILOT-CLI-HARNESS-ANALYSIS.md` §3 | `HARNESS-CONSISTENCY-FRAMEWORK.md` §3.1 |
| OpenCode best practices | `OPENCODE-HARNESS-BEST-PRACTICES.md` §2 | `HARNESS-CONSISTENCY-FRAMEWORK.md` §4 |
| Tiered parity model | `HARNESS-CONSISTENCY-FRAMEWORK.md` §3 | `CLAUDE-CODE-HARNESS-ANALYSIS.md` Appendix A |
| Testing strategy | `HARNESS-CONSISTENCY-FRAMEWORK.md` §5 | `OPENCODE-HARNESS-BEST-PRACTICES.md` §5.3 |
| Drift prevention | `HARNESS-CONSISTENCY-FRAMEWORK.md` §7 | `PI-DEV-RENDERER-ANALYSIS.md` §5 |
| Model ID mapping | `OPENCODE-HARNESS-BEST-PRACTICES.md` §1.3 | `CLAUDE-CODE-HARNESS-ANALYSIS.md` §2.3 |
| Sentinel safety model | `OPENCODE-HARNESS-BEST-PRACTICES.md` §1.2 | `HARNESS-CONSISTENCY-FRAMEWORK.md` §4.6 |
| Shared lib.sh | `HARNESS-CONSISTENCY-FRAMEWORK.md` §2.2 | `CLAUDE-CODE-HARNESS-ANALYSIS.md` §4.1 |

---

## Document Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-16 | Lead Engineer | Initial master document — consolidation of Phase 1 analysis |

---

*This document is the authoritative consolidation of Phase 1 harness analysis findings. For detailed implementation guidance on any specific harness, refer to the source documents listed in §8. For the cross-harness consistency framework and testing strategy, see `docs/HARNESS-CONSISTENCY-FRAMEWORK.md`.*
