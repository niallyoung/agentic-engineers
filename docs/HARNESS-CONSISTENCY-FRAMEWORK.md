# Harness Consistency Framework

**Document ID:** HARNESS-CONSISTENCY-FRAMEWORK  
**Task ID:** 2026-05-16-harness-consistency-framework  
**Author:** Lead Engineer  
**Date:** 2026-05-16  
**Status:** Draft — Phase 3 Planning  
**Scope:** Cross-harness consistency, feature parity, drift prevention, testing strategy, maintenance procedures

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Analysis](#2-current-state-analysis)
3. [Feature Parity Definition](#3-feature-parity-definition)
4. [Unified Harness Interface](#4-unified-harness-interface)
5. [Testing Strategy](#5-testing-strategy)
6. [Documentation Standards](#6-documentation-standards)
7. [Drift Prevention Mechanisms](#7-drift-prevention-mechanisms)
8. [Implementation Roadmap](#8-implementation-roadmap)
9. [Future Harness Addition Protocol](#9-future-harness-addition-protocol)
10. [Appendix: Compliance Matrices](#10-appendix-compliance-matrices)

---

## 1. Executive Summary

The agentic-engineers framework currently ships four harness renderers — OpenCode, Claude Code, π.dev, and Copilot CLI — that translate canonical source definitions into platform-specific configuration directories. After the Phase 2 review and improvement cycle (2026-05-16), all four harnesses are functional and documented, but they differ significantly in architecture, capability, and maintenance approach.

This document defines a **cross-harness consistency framework** to:

1. **Prevent drift** — Stale model IDs, outdated documentation, and divergent feature sets accumulate silently without a formal parity model.
2. **Ensure feature parity** — Define which features are mandatory, optional, and platform-constrained so that each harness is evaluated against appropriate expectations.
3. **Enable consistent testing** — No harness currently has automated tests; this framework defines a test strategy that works across all four.
4. **Reduce maintenance burden** — Shared code, shared patterns, and clear ownership reduce the cost of keeping four harnesses in sync.
5. **Support future harness additions** — A formal interface and checklist enables new harnesses to be added without re-inventing patterns.

### Key Findings

| Harness | Compliance Tier | Primary Gap | Priority |
|---------|----------------|-------------|----------|
| **OpenCode** | Tier A (Reference) | Provider hardcoded; fragile AGENTS.md parser | Low |
| **Claude Code** | Tier A | No docs/AGENTS.md lookup; simplified model mapping | Medium |
| **π.dev** | Tier B | Static files; no content transformation; speculative features | Medium |
| **Copilot CLI** | Tier C (Intentional) | Skills only by platform constraint | Low |

### Recommended Approach

Adopt a **tiered parity model** where harnesses are evaluated against capability tiers (A/B/C) rather than a single universal standard. This acknowledges platform constraints while still enforcing quality within each tier.

---

## 2. Current State Analysis

### 2.1 Architectural Patterns

Four distinct architectural patterns exist across the harnesses:

**Pattern 1: Dynamic Transform (OpenCode, Claude Code)**
```
src/agents/*-agent.md  ──┐
docs/AGENTS.md  ──────────┤→ render script → platform-specific files
src/skills/*/SKILL.md  ──┘
```
Source files are transformed at install time. Model IDs, descriptions, and frontmatter are mapped to platform-specific formats. This is the most maintainable pattern: changes to canonical sources propagate automatically on next install.

**Pattern 2: Static Copy (π.dev)**
```
renderer/pi-dev-src/  ──→ Python renderer → ~/.pi/agent/
```
Manually-maintained source files are copied verbatim. No transformation occurs. Changes to canonical sources (`docs/AGENTS.md`, `src/agents/`) do NOT propagate automatically — `renderer/pi-dev-src/` must be manually kept in sync.

**Pattern 3: Skills-Only (Copilot CLI)**
```
src/skills/*/SKILL.md  ──→ render-copilot.sh → ~/.copilot/skills/
```
Only skills are installed; agents are not supported by the platform. This is intentionally minimal and correct for the platform's capabilities.

### 2.2 Shared Code Analysis

After the Phase 2 `lib.sh` extraction, the following code is shared:

| Function | lib.sh | OpenCode | Claude Code | Copilot CLI | π.dev |
|----------|--------|----------|-------------|-------------|-------|
| `list_source_skills` | ✅ | sources | sources | sources | N/A |
| `list_source_agents` | ✅ | sources | sources | N/A | N/A |
| `extract_fm` | ✅ | sources | sources | N/A | N/A |
| `strip_fm` | ✅ | sources | sources | N/A | N/A |
| `extract_body_model` | ✅ | sources | sources | N/A | N/A |

**Remaining duplication:**
- Install/uninstall/status loop logic for skills (~40 lines each) — structurally identical across OpenCode, Claude Code, and Copilot CLI but not extracted
- Git hooks installation block (~10 lines) — duplicated in all three Bash harnesses

### 2.3 Known Drift Vectors

The following are the primary mechanisms by which harnesses drift from the canonical model:

| Drift Vector | Affected Harnesses | Detection | Current Mitigation |
|---|---|---|---|
| Stale model IDs | π.dev (manual sync), Claude Code (tier names) | Manual review | None automated |
| Stale role count | π.dev | Manual review | Updated in Phase 2 |
| Fragile AGENTS.md parser | OpenCode | Silent empty result | None |
| Provider hardcoding | OpenCode | Manual review | Code comment |
| No docs/AGENTS.md lookup | Claude Code | Manual review | Convention |
| Speculative features | π.dev | Manual review | Marked in files |
| Undocumented platform limits | Copilot CLI | User confusion | Documented in Makefile |

---

## 3. Feature Parity Definition

### 3.1 Tiered Parity Model

Not all features are achievable on all platforms. The tiered model defines what is **mandatory**, **recommended**, and **platform-constrained** for each capability tier.

#### Tier A: Full-Featured Harness
Harnesses that support both agents and skills with dynamic content transformation.

**Mandatory:**
- [ ] Dynamic agent rendering from `src/agents/*-agent.md`
- [ ] Dynamic skill rendering from `src/skills/*/SKILL.md`
- [ ] Canonical 8 roles rendered
- [ ] Current model IDs (not stale by more than one major version)
- [ ] Idempotent installs (re-running does not corrupt state)
- [ ] Foreign file protection (refuse to overwrite non-managed files)
- [ ] Per-skill marker files (`.agentic-engine{service-name}`)
- [ ] Agent manifest file for tracking managed agents
- [ ] Uninstall support (removes only managed files)
- [ ] Status/drift detection (per-skill diff comparison)
- [ ] Git hooks installation (core.hooksPath = .githooks)
- [ ] Dedicated installation documentation

**Recommended:**
- [ ] docs/AGENTS.md lookup for canonical model/effort/description
- [ ] Atomic writes (`.tmp` + `mv` for manifests)
- [ ] Rollback on partial failure
- [ ] Provider auto-detection at install time

**Platform-Constrained (document if absent):**
- Config file management (OpenCode has `opencode.jsonc`; Claude Code uses `CLAUDE.md` pattern)
- Global rules file (OpenCode has `AGENTS.md`; Claude Code uses `CLAUDE.md`)
- Mode field (OpenCode-specific: `mode: all|subagent`)
- Temperature mapping (OpenCode maps effort → temperature; Claude Code omits)

**Current Tier A Harnesses:** OpenCode ✅, Claude Code ✅ (with noted gaps)

#### Tier B: Partial-Transform Harness
Harnesses that use static or semi-static source files rather than dynamic transformation.

**Mandatory:**
- [ ] Canonical 8 roles documented
- [ ] Current model IDs (not stale by more than one major version)
- [ ] Idempotent installs
- [ ] Marker file strategy (at minimum, a single install marker)
- [ ] Uninstall support
- [ ] Status reporting
- [ ] Speculative/unverified features clearly marked
- [ ] Dedicated installation documentation

**Recommended:**
- [ ] Per-file markers for granular foreign protection
- [ ] Automated sync from canonical sources

**Current Tier B Harnesses:** π.dev ✅

#### Tier C: Skills-Only Harness
Harnesses that support only skills due to platform constraints.

**Mandatory:**
- [ ] All 14 canonical skills installed
- [ ] Per-skill marker files
- [ ] Idempotent installs
- [ ] Foreign file protection for skills
- [ ] Uninstall support
- [ ] Status/drift detection
- [ ] Git hooks installation
- [ ] Clear documentation that agents are not supported (and why)

**Current Tier C Harnesses:** Copilot CLI ✅

### 3.2 Feature Parity Matrix (Current State)

| Feature | OpenCode (A) | Claude Code (A) | π.dev (B) | Copilot CLI (C) | Tier Required |
|---------|:---:|:---:|:---:|:---:|:---:|
| Dynamic agent rendering | ✅ | ✅ | ❌ | N/A | A |
| Dynamic skill rendering | ✅ | ✅ | ❌ | ✅ | A/C |
| Canonical 8 roles | ✅ | ✅ | ✅ | N/A | A/B |
| Current model IDs | ✅ | ⚠️ tiers | ✅ | N/A | A/B |
| Idempotent installs | ✅ | ✅ | ✅ | ✅ | All |
| Foreign file protection | ✅ | ✅ | ⚠️ partial | ✅ | All |
| Per-skill markers | ✅ | ✅ | ❌ | ✅ | All |
| Agent manifest | ✅ | ✅ | N/A | N/A | A |
| Uninstall support | ✅ | ✅ | ✅ | ✅ | All |
| Status/drift detection | ✅ | ✅ | ✅ | ✅ | All |
| Git hooks installation | ✅ | ✅ | ✅ | ✅ | All |
| docs/AGENTS.md lookup | ✅ | ❌ | ❌ | N/A | A (recommended) |
| Atomic writes | ✅ | ✅ | N/A | N/A | A |
| Dedicated install doc | ✅ | ✅ | ✅ | ⚠️ inline | All |
| Speculative features marked | N/A | N/A | ✅ | N/A | B |

**Parity Score:**
- OpenCode: 14/14 mandatory ✅ (reference impl)
- Claude Code: 12/14 mandatory (missing: docs/AGENTS.md lookup, version-specific model IDs)
- π.dev: 8/9 Tier B mandatory (missing: per-file markers)
- Copilot CLI: 7/8 Tier C mandatory (missing: dedicated install doc)

---

## 4. Unified Harness Interface

### 4.1 Interface Contract

All harnesses MUST implement a consistent CLI interface:

```bash
render-<harness>.sh REPO_ROOT DEST_DIR [--install|--uninstall|--status]
```

**Parameters:**
- `REPO_ROOT` — Absolute path to the agentic-engineers repository root
- `DEST_DIR` — Absolute path to the harness-specific destination directory
- `MODE` — One of: (empty/`install`), `--uninstall`, `--status`

**Exit codes:**
- `0` — Success
- `1` — Fatal error (missing prerequisite, validation failure)
- `2` — Unknown mode (invalid third argument)

**Output conventions:**
- `📦` prefix for installation actions
- `✅` prefix for success messages
- `⚠️` prefix for warnings (non-fatal, operation continues)
- `❌` prefix for errors (fatal, operation stops)
- `🧹` prefix for uninstall actions
- `🔄` suffix for drift-detected items in status mode

### 4.2 Install Mode Contract

```
PRECONDITIONS:
  - REPO_ROOT exists and is a valid agentic-engineers repo
  - DEST_DIR is writable (or will be created)

POSTCONDITIONS:
  - All managed files installed to DEST_DIR
  - Marker files written for all managed items
  - Manifest file written (for harnesses with agent support)
  - Git hooks configured (core.hooksPath = .githooks)
  - Exit 0

INVARIANTS:
  - Foreign files (not managed by this harness) are NEVER overwritten
  - Operation is idempotent (running twice produces same result)
  - Partial failure does not leave corrupt state (atomic writes where possible)
```

### 4.3 Uninstall Mode Contract

```
PRECONDITIONS:
  - REPO_ROOT and DEST_DIR provided

POSTCONDITIONS:
  - All managed files removed from DEST_DIR
  - Marker files and manifests removed
  - Foreign files untouched
  - Exit 0

INVARIANTS:
  - Only files tracked by marker/manifest are removed
  - If not installed (no marker), uninstall is a no-op (not an error)
```

### 4.4 Status Mode Contract

```
PRECONDITIONS:
  - REPO_ROOT and DEST_DIR provided

POSTCONDITIONS:
  - Per-item status printed to stdout
  - Summary line printed (counts of ok/drift/missing/foreign)
  - Exit 0 (status mode never fails)

OUTPUT FORMAT:
  ✅ <name>                    — installed, in sync
  🔄 <name> (drift)            — installed, content differs from source
  ❌ <name> (not installed)    — source exists, not installed
  ⚠️  <name> (foreign)         — destination exists, not managed by us
  
  Summary: "<N> ok / <N> drift / <N> missing / <N> foreign"
```

### 4.5 Shared Library Contract (`lib.sh`)

The shared library at `renderer/scripts/lib.sh` MUST provide:

```bash
# Required caller-set variables:
#   SRC_SKILLS — path to src/skills/
#   SRC_AGENTS — path to src/agents/ (if using agent functions)

list_source_skills()    # → newline-separated skill names
list_source_agents()    # → newline-separated agent names (without -agent.md)
extract_fm <file> <key> # → value of frontmatter key, or empty
strip_fm <file>         # → file body with frontmatter removed
extract_body_model <file> # → model ID from body text, or empty
```

**Proposed additions to `lib.sh`:**

```bash
# Install/uninstall/status loop for skills (DRY across all harnesses)
install_skills DST_SKILLS SKILL_MARKER
uninstall_skills DST_SKILLS SKILL_MARKER
status_skills SRC_SKILLS DST_SKILLS SKILL_MARKER

# Git hooks installation (shared across all Bash harnesses)
install_git_hooks REPO_ROOT

# Prerequisite checks
check_prereqs [rsync] [python3] [diff] [awk]
```

### 4.6 Marker File Standard

All harnesses MUST use consistent marker file naming and content:

| Item | Marker Location | Marker Name | Content |
|------|----------------|-------------|---------|
| Skill directory | `$DST_SKILLS/<name>/` | `.agentic-engine{service-name}` | ISO 8601 timestamp |
| Agent manifest | `$DST_AGENTS/` | `.agentic-engine{service-name}` | Newline-separated agent names |
| Install root (π.dev) | `$PI_AGENT/` | `.agentic-engine-pi` | ISO 8601 timestamp |

**Timestamp format:** `date -u +"%Y-%m-%dT%H:%M:%SZ"` (UTC ISO 8601)

---

## 5. Testing Strategy

### 5.1 Testing Philosophy

No harness currently has automated tests. The testing strategy must be:
- **Lightweight** — Tests run in temporary directories, no system-level side effects
- **Portable** — Tests run on macOS and Linux without additional dependencies
- **Fast** — Full test suite completes in < 30 seconds
- **Deterministic** — Tests produce the same result on every run

### 5.2 Test Categories

#### Category 1: Unit Tests (lib.sh functions)
Test each shared library function in isolation.

```bash
# tests/harness/test_lib.sh
test_list_source_skills() {
    # Given: a temp dir with 2 skill dirs (each with SKILL.md) and 1 without
    # When: list_source_skills is called
    # Then: returns exactly the 2 dirs with SKILL.md
}

test_extract_fm() {
    # Given: a file with frontmatter containing "model: claude-haiku-4-5"
    # When: extract_fm file model
    # Then: returns "claude-haiku-4-5"
}

test_strip_fm() {
    # Given: a file with frontmatter and body
    # When: strip_fm file
    # Then: returns only the body (no --- delimiters)
}
```

#### Category 2: Integration Tests (per-harness install/uninstall/status)
Test each harness's full lifecycle using temporary directories.

```bash
# tests/harness/test_render_opencode.sh
test_install_creates_skills() {
    # Given: temp DEST_DIR, real REPO_ROOT
    # When: render-opencode.sh REPO_ROOT DEST_DIR install
    # Then: all 14 skills present in DEST_DIR/skills/
    #       all 8 agents present in DEST_DIR/agents/
    #       opencode.jsonc present
    #       AGENTS.md present
    #       all marker files present
}

test_install_is_idempotent() {
    # Given: already-installed DEST_DIR
    # When: render-opencode.sh REPO_ROOT DEST_DIR install (second time)
    # Then: exit 0, no errors, same files present
}

test_foreign_file_protection() {
    # Given: DEST_DIR with a foreign skill (no marker)
    # When: render-opencode.sh REPO_ROOT DEST_DIR install
    # Then: foreign skill is NOT overwritten (warning printed)
    #       other skills are installed normally
}

test_uninstall_removes_managed_only() {
    # Given: installed DEST_DIR with one foreign file added
    # When: render-opencode.sh REPO_ROOT DEST_DIR --uninstall
    # Then: managed files removed, foreign file untouched
}

test_status_detects_drift() {
    # Given: installed DEST_DIR, then one skill file modified
    # When: render-opencode.sh REPO_ROOT DEST_DIR --status
    # Then: drifted skill shown as "🔄 <name> (drift)"
    #       other skills shown as "✅ <name>"
}
```

#### Category 3: Cross-Harness Parity Tests
Tests that verify all harnesses produce equivalent outcomes for shared features.

```bash
# tests/harness/test_cross_harness_parity.sh
test_all_harnesses_install_same_skills() {
    # Given: fresh DEST_DIRs for each harness
    # When: each harness installed
    # Then: skill names are identical across OpenCode, Claude Code, Copilot CLI
    #       (π.dev excluded — different architecture)
}

test_all_harnesses_use_current_model_ids() {
    # Given: docs/AGENTS.md canonical model table
    # When: each harness renders agents
    # Then: no rendered agent references a model ID older than N-1 versions
    #       (model staleness check)
}

test_all_harnesses_install_git_hooks() {
    # Given: fresh install of each harness
    # When: install completes
    # Then: git config core.hooksPath == .githooks in REPO_ROOT
}
```

#### Category 4: Model ID Freshness Tests
Automated checks that model IDs in all harnesses match the canonical list in `docs/AGENTS.md`.

```bash
# tests/harness/test_model_freshness.sh
test_opencode_model_map_covers_canonical_models() {
    # Parse docs/AGENTS.md for all model IDs
    # Verify each appears in render-opencode.sh's map_model_opencode()
}

test_pi_dev_model_ids_are_current() {
    # Parse renderer/pi-dev-src/settings.json and pi.yml for model IDs
    # Verify they match docs/AGENTS.md canonical IDs
}

test_claude_model_tiers_cover_canonical_models() {
    # Parse docs/AGENTS.md for all model IDs
    # Verify each maps to haiku/sonnet/opus in render-claude.sh
}
```

### 5.3 Test Infrastructure

**Test runner:** `tests/harness/run_tests.sh` — discovers and runs all `test_*.sh` files

**Test framework:** Minimal bash-based assertions (no external dependencies):
```bash
# tests/harness/assert.sh
assert_equal() { [ "$1" = "$2" ] || fail "Expected '$2', got '$1'"; }
assert_file_exists() { [ -f "$1" ] || fail "File not found: $1"; }
assert_dir_exists() { [ -d "$1" ] || fail "Dir not found: $1"; }
assert_contains() { grep -q "$2" "$1" || fail "File $1 does not contain '$2'"; }
assert_not_contains() { ! grep -q "$2" "$1" || fail "File $1 should not contain '$2'"; }
```

**Makefile integration:**
```makefile
test-harness:
    @bash tests/harness/run_tests.sh

test-harness-verbose:
    @bash tests/harness/run_tests.sh --verbose
```

### 5.4 CI Integration

Add harness tests to the pre-push hook (non-blocking warn) and to a GitHub Actions workflow:

```yaml
# .github/workflows/harness-tests.yml
name: Harness Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run harness tests
        run: make test-harness
```

### 5.5 Test Coverage Targets

| Test Category | Target Coverage | Current | Gap |
|---|---|---|---|
| lib.sh unit tests | 100% of functions | 0% | All functions |
| OpenCode integration | 5 lifecycle scenarios | 0% | All scenarios |
| Claude Code integration | 5 lifecycle scenarios | 0% | All scenarios |
| Copilot CLI integration | 3 lifecycle scenarios | 0% | All scenarios |
| π.dev integration | 3 lifecycle scenarios | 0% | All scenarios |
| Cross-harness parity | 3 parity checks | 0% | All checks |
| Model freshness | 3 freshness checks | 0% | All checks |

---

## 6. Documentation Standards

### 6.1 Per-Harness Documentation Requirements

Every harness MUST have a dedicated installation guide with the following sections:

```markdown
# <Harness Name> Installation Guide

## Prerequisites
- Required tools (rsync, python3, etc.)
- Supported platforms (macOS, Linux)
- Required versions

## Quick Start
- One-command install
- Verification step

## What Gets Installed
- Table: file/directory → destination → managed by us?
- Marker file locations

## Configuration
- Harness-specific config options
- Known limitations (platform constraints)

## Uninstall
- Command to uninstall
- What is and is not removed

## Troubleshooting
- Common errors and solutions
- How to check installation status

## Known Limitations
- Platform-specific constraints
- Speculative/unverified features (if any)
- Deferred items from the roadmap
```

**Current compliance:**
- OpenCode: ✅ `docs/OPENCODE-INSTALL.md`
- Claude Code: ✅ `docs/CLAUDE-INSTALL.md`
- π.dev: ✅ `renderer/PI-DEV-RENDERER.md`
- Copilot CLI: ❌ Missing — only inline Makefile comments

### 6.2 Harness Comparison Table (Canonical)

`docs/HARNESS-FINAL-SUMMARY.md` is the canonical cross-harness comparison document. It MUST be updated whenever:
- A new harness is added
- A harness's tier changes
- A known limitation is resolved
- A new known limitation is discovered

**Update trigger:** Any merge to `main` that touches `renderer/scripts/render-*.sh` or `renderer/pi-dev-src/` MUST include an update to `docs/HARNESS-FINAL-SUMMARY.md`.

### 6.3 Inline Code Documentation Standards

All render scripts MUST include:

1. **File header** — Purpose, inputs, outputs, key design decisions
2. **Function docstrings** — For every function > 5 lines
3. **Limitation comments** — `# LIMITATION: <description>` for known fragilities
4. **Future enhancement markers** — `# FUTURE: <description>` for planned improvements
5. **Platform-specific notes** — Comments explaining why platform-specific choices were made

**Example:**
```bash
# Map canonical model ID → OpenCode provider/model ID.
#
# LIMITATION: Provider hardcoded to github-copilot/. Users with anthropic/ provider
# need different IDs. See FUTURE note below.
#
# FUTURE: Detect available providers from `opencode models` output at install time
# and select the best match dynamically.
map_model_opencode() { ... }
```

### 6.4 Change Log Standard

Each render script MUST maintain a change log comment block at the top:

```bash
# CHANGE LOG:
#   2026-05-16: Extracted shared functions to lib.sh (Phase 2 improvement)
#   2026-05-16: Added git hooks installation
#   2026-04-XX: Initial implementation
```

### 6.5 Model ID Currency Standard

Model IDs in all harnesses MUST be updated within **30 days** of a new canonical model being added to `docs/AGENTS.md`. The responsible party for each harness:

| Harness | Responsible | Update Mechanism |
|---------|-------------|-----------------|
| OpenCode | Maintainer | Update `map_model_opencode()` in `render-opencode.sh` |
| Claude Code | Maintainer | Update `map_model()` in `render-claude.sh` (tier names auto-resolve) |
| π.dev | Maintainer | Update `renderer/pi-dev-src/settings.json` and `pi.yml` manually |
| Copilot CLI | N/A | No model IDs (skills only) |

---

## 7. Drift Prevention Mechanisms

### 7.1 Automated Drift Detection

**Mechanism 1: `make status` cross-harness check**

Extend the existing `make status` target to report cross-harness parity gaps:

```bash
make status-parity
# Output:
#   OpenCode:    14/14 skills ✅  8/8 agents ✅
#   Claude Code: 14/14 skills ✅  8/8 agents ✅
#   Copilot CLI: 14/14 skills ✅  (agents: N/A)
#   π.dev:       5/5 files ✅
#   
#   Parity gaps:
#   ⚠️  Claude Code: model IDs are tier-names only (not version-specific)
#   ⚠️  π.dev: no dynamic rendering from src/agents/
```

**Mechanism 2: Model freshness check script**

```bash
# renderer/scripts/check-model-freshness.sh
# Parses docs/AGENTS.md for canonical model IDs
# Checks each harness's model mapping for coverage
# Exits non-zero if any harness is missing a canonical model
```

Integrate into `make verify` and pre-push hook.

**Mechanism 3: docs/AGENTS.md change detection**

Add a post-merge hook check: if `docs/AGENTS.md` changes, warn that harness model mappings may need updating:

```bash
# .githooks/post-merge
if git diff HEAD@{1} HEAD -- docs/AGENTS.md | grep -q "^+.*claude-"; then
    echo "⚠️  docs/AGENTS.md model IDs changed — check harness model mappings:"
    echo "   renderer/scripts/render-opencode.sh (map_model_opencode)"
    echo "   renderer/scripts/render-claude.sh (map_model)"
    echo "   renderer/pi-dev-src/settings.json"
    echo "   renderer/pi-dev-src/pi.yml"
fi
```

### 7.2 Sentinel-Based Staleness Detection

Extend the existing marker file strategy to include a **source hash**:

```bash
# Current marker content:
2026-05-16T10:00:00Z

# Proposed marker content:
2026-05-16T10:00:00Z
source_hash: <sha256 of src/skills/<name>/>
```

During `--status`, compare the stored hash against the current source hash. If they differ, report drift even if the destination files haven't changed (e.g., if the source was updated but the harness hasn't been re-run).

### 7.3 π.dev Sync Automation

The π.dev harness is the highest drift risk because it uses manually-maintained static files. Mitigate this with a sync validation script:

```bash
# renderer/scripts/check-pi-dev-sync.sh
# Compares key fields between docs/AGENTS.md and renderer/pi-dev-src/
# Checks:
#   - Role count matches (8 roles)
#   - Model IDs match canonical IDs
#   - No removed roles still referenced
# Exits non-zero if out of sync
```

Integrate into `make verify` and CI.

### 7.4 Quarterly Review Checklist

A formal quarterly review should check:

```markdown
## Quarterly Harness Review Checklist

### Model IDs
- [ ] docs/AGENTS.md model IDs are current (no deprecated models)
- [ ] render-opencode.sh map_model_opencode() covers all canonical IDs
- [ ] render-claude.sh map_model() covers all canonical tiers
- [ ] renderer/pi-dev-src/settings.json uses current model IDs
- [ ] renderer/pi-dev-src/pi.yml uses current model IDs

### Role Count
- [ ] All 4 harnesses reference exactly 8 canonical roles
- [ ] No removed roles remain in any harness

### Documentation
- [ ] All 4 harnesses have up-to-date installation guides
- [ ] docs/HARNESS-FINAL-SUMMARY.md reflects current state
- [ ] Known limitations are still accurate

### Platform Compatibility
- [ ] OpenCode schema URL (opencode.ai/config.json) is still valid
- [ ] Claude Code tier names (haiku/sonnet/opus) still accepted
- [ ] Copilot CLI skills directory (~/.copilot/skills/) still correct
- [ ] π.dev agent directory (~/.pi/agent/) still correct

### Test Coverage
- [ ] All new harness features have corresponding tests
- [ ] All known bugs have regression tests
```

---

## 8. Implementation Roadmap

### 8.1 Tier 1: Critical Gaps (< 1 week effort)

These items address compliance gaps and prevent immediate drift.

| # | Item | Harness | Effort | Owner | Priority |
|---|------|---------|--------|-------|----------|
| 1.1 | Create `docs/COPILOT-INSTALL.md` | Copilot CLI | 2h | Maintainer | HIGH |
| 1.2 | Add model freshness check script (`check-model-freshness.sh`) | All | 3h | Maintainer | HIGH |
| 1.3 | Add π.dev sync validation script (`check-pi-dev-sync.sh`) | π.dev | 2h | Maintainer | HIGH |
| 1.4 | Add post-merge hook: warn on docs/AGENTS.md model ID changes | All | 1h | Maintainer | HIGH |
| 1.5 | Integrate freshness checks into `make verify` | All | 1h | Maintainer | HIGH |

**Total Tier 1 effort:** ~9 hours

### 8.2 Tier 2: Quality Improvements (1–2 weeks effort)

These items improve robustness and reduce maintenance burden.

| # | Item | Harness | Effort | Owner | Priority |
|---|------|---------|--------|-------|----------|
| 2.1 | Extract skills install/uninstall/status loops to `lib.sh` | All Bash | 4h | Maintainer | MEDIUM |
| 2.2 | Extract git hooks installation to `lib.sh` | All Bash | 2h | Maintainer | MEDIUM |
| 2.3 | Add docs/AGENTS.md lookup to Claude Code harness | Claude Code | 4h | Maintainer | MEDIUM |
| 2.4 | Add proper YAML escaping to Claude Code (`yaml_escape_inline`) | Claude Code | 1h | Maintainer | MEDIUM |
| 2.5 | Add source hash to skill marker files | All | 3h | Maintainer | MEDIUM |
| 2.6 | Harden docs/AGENTS.md table parser in OpenCode (parse failure detection) | OpenCode | 2h | Maintainer | MEDIUM |
| 2.7 | Add prerequisite checks (`check_prereqs`) to all harnesses | All | 3h | Maintainer | MEDIUM |
| 2.8 | Add `make status-parity` cross-harness comparison target | All | 3h | Maintainer | MEDIUM |

**Total Tier 2 effort:** ~22 hours

### 8.3 Tier 3: Strategic Improvements (2–4 weeks effort)

These items address architectural limitations and enable future growth.

| # | Item | Harness | Effort | Owner | Priority |
|---|------|---------|--------|-------|----------|
| 3.1 | Implement harness test suite (Category 1–4 tests) | All | 16h | Maintainer | HIGH |
| 3.2 | OpenCode provider auto-detection (`opencode models` at install time) | OpenCode | 6h | Maintainer | MEDIUM |
| 3.3 | π.dev dynamic content generation from `src/agents/` | π.dev | 12h | Maintainer | LOW |
| 3.4 | Fix π.dev Python renderer argument parsing (explicit `--src`/`--dest` flags) | π.dev | 3h | Maintainer | LOW |
| 3.5 | Fix π.dev `__init__` directory creation (defer until render_all) | π.dev | 1h | Maintainer | LOW |
| 3.6 | Add skill rollback on partial failure (OpenCode, Claude Code) | OpenCode, Claude Code | 4h | Maintainer | LOW |
| 3.7 | Add CI workflow for harness tests | All | 2h | Maintainer | MEDIUM |
| 3.8 | Quarterly review automation (script to run review checklist) | All | 4h | Maintainer | LOW |

**Total Tier 3 effort:** ~48 hours

### 8.4 Effort Summary

| Tier | Items | Total Effort | Recommended Timeline |
|------|-------|-------------|---------------------|
| Tier 1 (Critical) | 5 items | ~9 hours | Week 1 |
| Tier 2 (Quality) | 8 items | ~22 hours | Weeks 2–3 |
| Tier 3 (Strategic) | 8 items | ~48 hours | Weeks 4–7 |
| **Total** | **21 items** | **~79 hours** | **7 weeks** |

### 8.5 Phase 3 Recommendations

For Phase 3 work, the recommended priority order is:

**Immediate (Phase 3, Week 1):**
1. Tier 1.1 — `docs/COPILOT-INSTALL.md` (closes last documentation gap)
2. Tier 1.2 — Model freshness check (prevents silent model staleness)
3. Tier 1.3 — π.dev sync validation (highest drift risk harness)
4. Tier 3.1 — Harness test suite (no tests is the biggest quality gap)

**Short-term (Phase 3, Weeks 2–3):**
5. Tier 2.1–2.2 — Extract more shared code to lib.sh
6. Tier 2.3 — Claude Code docs/AGENTS.md lookup
7. Tier 2.8 — `make status-parity` target
8. Tier 3.7 — CI workflow for harness tests

**Medium-term (Phase 3, Weeks 4–7):**
9. Tier 2.4–2.7 — Remaining quality improvements
10. Tier 3.2 — OpenCode provider auto-detection
11. Tier 3.3 — π.dev dynamic generation (highest architectural improvement)

---

## 9. Future Harness Addition Protocol

### 9.1 New Harness Checklist

When adding a new harness, the following checklist MUST be completed:

**Pre-implementation:**
- [ ] Determine capability tier (A, B, or C) based on platform capabilities
- [ ] Document platform constraints (what is/isn't supported and why)
- [ ] Identify destination directory convention
- [ ] Identify config file format (JSON, YAML, TOML, etc.)
- [ ] Identify agent frontmatter schema (if agents are supported)
- [ ] Identify model ID format (fully-qualified, tier names, etc.)

**Implementation:**
- [ ] Create `renderer/scripts/render-<harness>.sh` (or `.py` for Python-based)
- [ ] Implement all mandatory features for the determined tier
- [ ] Source `renderer/scripts/lib.sh` for shared functions
- [ ] Use consistent marker file naming (`.agentic-engine{service-name}`)
- [ ] Implement install/uninstall/status modes with standard interface
- [ ] Add git hooks installation
- [ ] Write inline documentation (header, function docstrings, limitation comments)

**Testing:**
- [ ] Add integration tests to `tests/harness/test_render_<harness>.sh`
- [ ] Add cross-harness parity tests if applicable
- [ ] Verify all tests pass: `make test-harness`

**Documentation:**
- [ ] Create `docs/<HARNESS>-INSTALL.md` with all required sections
- [ ] Update `docs/HARNESS-FINAL-SUMMARY.md` comparison table
- [ ] Update root `Makefile` with `install-<harness>`, `uninstall-<harness>` targets
- [ ] Update `renderer/Makefile` if applicable
- [ ] Update `README.md` with new harness mention

**Validation:**
- [ ] Run `make install-<harness>` and verify output
- [ ] Run `make status` and verify new harness appears
- [ ] Run `make uninstall-<harness>` and verify clean removal
- [ ] Run `make install-<harness>` again (idempotency check)
- [ ] Run `make test-harness` and verify all tests pass

### 9.2 Capability Tier Decision Tree

```
Does the platform support custom agents?
├── YES → Does it support dynamic content transformation?
│         ├── YES → Tier A (Full-Featured)
│         └── NO  → Tier B (Partial-Transform)
└── NO  → Does it support skills?
          ├── YES → Tier C (Skills-Only)
          └── NO  → Not worth implementing (document why)
```

### 9.3 Model ID Mapping Requirements

Every new harness MUST document its model ID format:

| Format | Example | Notes |
|--------|---------|-------|
| Fully-qualified | `github-copilot/claude-sonnet-4.6` | Provider-specific; may need auto-detection |
| Tier name | `sonnet` | Version-agnostic; resolves to latest |
| Canonical ID | `claude-sonnet-4-6` | Direct; requires platform to accept this format |
| Custom | Platform-specific | Document the mapping function |

---

## 10. Appendix: Compliance Matrices

### 10.1 Mandatory Feature Compliance (Current State)

| Feature | OpenCode | Claude Code | π.dev | Copilot CLI |
|---------|:---:|:---:|:---:|:---:|
| **Tier A Mandatory** | | | | |
| Dynamic agent rendering | ✅ | ✅ | N/A | N/A |
| Dynamic skill rendering | ✅ | ✅ | N/A | ✅ |
| Canonical 8 roles | ✅ | ✅ | ✅ | N/A |
| Current model IDs | ✅ | ⚠️ | ✅ | N/A |
| Idempotent installs | ✅ | ✅ | ✅ | ✅ |
| Foreign file protection | ✅ | ✅ | ⚠️ | ✅ |
| Per-skill markers | ✅ | ✅ | ❌ | ✅ |
| Agent manifest | ✅ | ✅ | N/A | N/A |
| Uninstall support | ✅ | ✅ | ✅ | ✅ |
| Status/drift detection | ✅ | ✅ | ✅ | ✅ |
| Git hooks installation | ✅ | ✅ | ✅ | ✅ |
| Dedicated install doc | ✅ | ✅ | ✅ | ❌ |
| **Tier B Mandatory** | | | | |
| Speculative features marked | N/A | N/A | ✅ | N/A |
| Install marker | N/A | N/A | ✅ | N/A |
| **Tier C Mandatory** | | | | |
| All 14 skills installed | ✅ | ✅ | N/A | ✅ |
| Agents-not-supported doc | N/A | N/A | N/A | ✅ |

### 10.2 Recommended Feature Compliance (Current State)

| Feature | OpenCode | Claude Code | π.dev | Copilot CLI |
|---------|:---:|:---:|:---:|:---:|
| docs/AGENTS.md lookup | ✅ | ❌ | ❌ | N/A |
| Atomic writes | ✅ | ✅ | N/A | N/A |
| Rollback on partial failure | ❌ | ❌ | N/A | N/A |
| Provider auto-detection | ❌ | N/A | N/A | N/A |
| Source hash in markers | ❌ | ❌ | ❌ | ❌ |
| Prerequisite checks | ❌ | ❌ | ❌ | ❌ |
| Automated tests | ❌ | ❌ | ❌ | ❌ |

### 10.3 Documentation Compliance (Current State)

| Document | OpenCode | Claude Code | π.dev | Copilot CLI |
|---------|:---:|:---:|:---:|:---:|
| Dedicated install guide | ✅ | ✅ | ✅ | ❌ |
| Prerequisites section | ✅ | ✅ | ✅ | N/A |
| What gets installed table | ✅ | ✅ | ✅ | N/A |
| Known limitations section | ✅ | ✅ | ✅ | N/A |
| Troubleshooting section | ✅ | ✅ | ⚠️ | N/A |
| Inline code comments | ✅ | ✅ | ✅ | ✅ |
| Limitation comments | ✅ | ⚠️ | ✅ | ⚠️ |
| Change log | ❌ | ❌ | ❌ | ❌ |

---

## Document Revision History

| Date | Author | Change |
|------|--------|--------|
| 2026-05-16 | Lead Engineer | Initial framework design document |

---

*This document is the authoritative reference for cross-harness consistency in the agentic-engineers framework. Update it when harness implementations change, new harnesses are added, or the parity model evolves.*
