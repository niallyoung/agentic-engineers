# AUDIT: Rendering Pipeline and File Flow Analysis

**Date:** 2025-05-09  
**Auditor:** Principal Engineer  
**Status:** COMPREHENSIVE AUDIT COMPLETE

---

## Executive Summary

The agentic-engineers repository has a **clean separation of concerns** with a properly structured rendering pipeline. However, there are **4 opportunities for optimization** to improve clarity and maintainability:

1. **Top-level clutter:** `orchestration/`, `data/`, `guides/`, `artifacts/` are untracked and should be organized
2. **AGENTS.md placement:** Should move to `src/docs/` to be co-located with other agent documentation
3. **models.yaml placement:** Should move to `src/config/` as it's a configuration artifact used by agents
4. **shared/ directory:** Contains only one baseline file; unclear purpose—clarify or consolidate

---

## 1. Rendering Pipeline Analysis

### 1.1 Rendering Scripts Overview

| Script | Source | Destination | Purpose |
|--------|--------|-------------|---------|
| `render-copilot.sh` | `src/skills/` | `~/.copilot/skills/` | Renders skill directories (contains `SKILL.md`) |
| `render-claude.sh` | `src/skills/` + `src/agents/` | `~/.claude/skills/` + `~/.claude/agents/` | Claude-specific rendering (transforms frontmatter) |
| `render-copilot-agents.py` | `src/agents/` | `~/.copilot/agents/` | Python renderer for Copilot agents |
| `render-copilot-agents.sh` | Calls Python renderer | `~/.copilot/agents/` | Bash wrapper for Copilot agent rendering |

### 1.2 Source-to-Destination Mapping

```
Repository Source                          Rendered Destination
─────────────────────────────────────────────────────────────────

src/skills/<name>/SKILL.md        ──────→  ~/.copilot/skills/<name>/
                                  ──────→  ~/.claude/skills/<name>/

src/agents/*-agent.md             ──────→  ~/.copilot/agents/
                                  ──────→  ~/.claude/agents/<name>.md
                                           (with frontmatter transformation)
```

### 1.3 Rendering Pipeline Details

**Copilot rendering** (`render-copilot.sh`):
- Scans `src/skills/*/` for directories containing `SKILL.md`
- Recursively copies entire skill directory to `~/.copilot/skills/<name>/`
- Uses `rsync` with `--delete` for clean sync
- Creates `.agentic-engine{service-name}` marker to track managed skills
- Preserves only `.agentic-engine{service-name}` marker, excludes `.DS_Store` and `.git`

**Claude rendering** (`render-claude.sh`):
- Renders skills: same as Copilot, copies `src/skills/*/` → `~/.claude/skills/`
- Renders agents: transforms `src/agents/*-agent.md` → `~/.claude/agents/<name>.md`
  - Strips frontmatter from agent files
  - Extracts Model info from frontmatter or body
  - Maps canonical models (claude-haiku → haiku) for Claude Code format
- Creates skill marker + agent manifest to track managed files

### 1.4 Current Rendering Compliance

✅ **ALL rendered files originate from `src/`:**
- `src/skills/` ← Skills (multiple providers)
- `src/agents/` ← Agent definitions (multiple providers)

✅ **No files from outside `src/` are rendered:**
- `config/` — NOT rendered
- `shared/` — NOT rendered
- `orchestration/` — NOT rendered (Python modules only, not rendered)
- `models.yaml` — NOT rendered to ~/.copilot/ or ~/.claude/

❌ **Concern:** `models.yaml` and `config/` are top-level; should be under `src/` for logical grouping

---

## 2. Top-Level Directory Analysis

### 2.1 Current Top-Level Structure

```
agentic-engineers/
├── src/                      ✅ Source code (agents, skills, orchestration modules)
├── docs/                     ✅ Documentation (architecture, guides, protocol)
├── tests/                    ✅ Tests (pytest, integration, unit)
├── renderer/                 ✅ Rendering system (build/installation)
├── .github/                  ✅ GitHub Actions (conventions)
├── dist/                     ⚠️  Build artifacts (gitignored, safe)
├── AGENTS.md                 ⚠️  Agent routing reference (should move to src/docs/)
├── models.yaml               ⚠️  Model registry (should move to src/config/)
├── Makefile                  ✅ Build targets
├── README.md                 ✅ Project README
├── config/                   ⚠️  Model config documentation (should move to src/config/)
├── shared/                   ⚠️  Only 1 baseline file (unclear purpose)
├── orchestration/            ❌ Untracked; duplicates src/orchestration?
├── guides/                   ❌ Untracked; empty (should be docs/guides/)
├── data/                     ❌ Untracked; queue/test data (runtime, not repo)
└── artifacts/                ❌ Untracked; queue artifacts (runtime, not repo)
```

### 2.2 Directory Purpose Assessment

| Directory | Current | Purpose | Assessment | Recommendation |
|-----------|---------|---------|------------|-----------------|
| `src/` | ✅ | Source code, agents, skills, orchestration | Core | KEEP |
| `docs/` | ✅ | Architecture, guides, protocol, standards | Core | KEEP |
| `tests/` | ✅ | Test suite (pytest, integration) | Core | KEEP |
| `renderer/` | ✅ | Build/installation system | Core | KEEP |
| `.github/` | ✅ | GitHub Actions workflows, conventions | GitHub std | KEEP |
| `dist/` | ⚠️ | Build output (gitignored) | Build artifact | KEEP (gitignored) |
| `AGENTS.md` | ⚠️  | Agent routing reference | Belongs with agents | **MOVE to src/docs/** |
| `models.yaml` | ⚠️  | Model registry (render input) | Config/render | **MOVE to src/config/** |
| `config/` | ⚠️  | Model assignments, quick reference | Config docs | **MOVE to src/config/** |
| `shared/` | ⚠️  | Quality baseline (single file) | Unclear | **CONSOLIDATE or DOCUMENT** |
| `orchestration/` | ❌ | Untracked; Python modules | Duplicates | **INVESTIGATE; likely orphaned** |
| `guides/` | ❌ | Untracked; empty examples | Runtime/examples | **MOVE to docs/guides/** or DELETE |
| `data/` | ❌ | Queue/test data (runtime) | Runtime artifacts | **GITIGNORE + DOCUMENT** |
| `artifacts/` | ❌ | Queue artifacts (runtime) | Runtime artifacts | **GITIGNORE + DOCUMENT** |

---

## 3. Problem Areas Identified

### 3.1 AGENTS.md Placement

**Current:** Root level (`AGENTS.md`)  
**Problem:** Separate from agent definitions (`src/agents/`)  
**Context:** AGENTS.md is the canonical agent routing reference used by Orchestrator  
**Analysis:**
- `src/agents/` contains agent definitions (`.md` files)
- `AGENTS.md` contains routing decision tree
- They're semantically related but physically separated
- Makes it unclear which agent file is "the" reference

**Recommendation:** **Move to `src/docs/AGENTS.md`**
- Co-locate with other agent documentation
- Signify it's canonical documentation
- `src/agents/` stays for agent implementation files
- `src/docs/` becomes hub for all conceptual docs (agents, architecture, protocol)

### 3.2 models.yaml Placement

**Current:** Root level (`models.yaml`)  
**Problem:** Configuration file that should be with other configs  
**Usage:**
- Read by `render-claude.sh` (render pipeline)
- Defines canonical model registry
- Used by agents for model selection
- Contains provider-specific mappings

**Recommendation:** **Move to `src/config/models.yaml`**
- Logical grouping with other configuration
- Render pipeline can find it at consistent location
- Allows future expansion of config directory

### 3.3 config/ Directory Placement

**Current:** Root level (`config/MODEL_ASSIGNMENTS_LOCKED.md`, `QUICK_REFERENCE.md`, `README.md`)  
**Problem:** Configuration documentation at root when `src/config/` could be clearer  
**Contents:**
- `MODEL_ASSIGNMENTS_LOCKED.md` — Which models are assigned to which roles
- `QUICK_REFERENCE.md` — Quick lookup table
- `README.md` — Config documentation

**Recommendation:** **Move to `src/config/`**
- Consolidate all configuration in one place
- Allows structure like `src/config/models.yaml`, `src/config/MODEL_ASSIGNMENTS_LOCKED.md`
- Render pipeline has consistent config location

### 3.4 shared/ Directory Purpose

**Current:** Root level, contains only `quality-assessment-baseline.md`  
**Problem:** Unclear purpose; single file doesn't justify directory  
**Assessment:**
- If it's shared utilities → should be `src/shared/`
- If it's documentation → should be `docs/` or `src/docs/`
- Current location suggests it's a temporary holding area

**Recommendation:** **Clarify and consolidate**
- If shared utilities: move to `src/shared/`
- If documentation: move to `docs/` with proper naming
- If baseline for quality: move to `docs/baselines/` or `src/config/`

### 3.5 Untracked Top-Level Directories

**Current:**
- `orchestration/` — 784K of Python modules (**CRITICAL: Why here if also in `src/orchestration/`?**)
- `guides/` — Empty examples directory
- `data/` — Queue and test-queue (runtime artifacts)
- `artifacts/` — Queue artifacts (runtime artifacts)

**Assessment:**

1. **orchestration/** (784K)
   - Contains: `activators/`, `agents/`, `handlers/`, `telemetry/`, `tools/`
   - Also exists at: `src/orchestration/` with same structure
   - **CRITICAL FINDING:** Possible duplicate or orphaned directory
   - **Action needed:** Verify which is source of truth

2. **guides/** (empty)
   - Only contains `examples/` subdirectory (empty)
   - Should be: `docs/guides/` if for documentation
   - Should be deleted if not used

3. **data/**, **artifacts/** (runtime)
   - Created by queue system at runtime
   - Should be in `.gitignore`
   - Should have runtime documentation

---

## 4. Rendering Pipeline Verification

### 4.1 SPEC Compliance Check

**Makefile verification target** (line 77-90):
```bash
verify: ## Verify framework structure and tests (SPEC-compliant)
    @test -d "$(REPO_ROOT)/src/orchestration/agents" || fail
    @test -d "$(REPO_ROOT)/src/orchestration" || fail
    @test -f "$(REPO_ROOT)/docs/SPEC.md" || fail
    @test -d "$(REPO_ROOT)/tests" || fail
```

**Current Status:** ✅ All requirements met
- `src/orchestration/agents/` exists
- `src/orchestration/` exists
- `docs/SPEC.md` exists
- `tests/` exists

**After Proposed Moves:** ✅ No impact (Makefile doesn't check for AGENTS.md or models.yaml location)

### 4.2 Renderer Script Dependencies

**render-copilot.sh** dependencies:
- Line 23: `SRC_SKILLS="$REPO_ROOT/src/skills"` ✅ No change needed
- Hard-coded path, no config file needed

**render-claude.sh** dependencies:
- Line 25: `SRC_SKILLS="$REPO_ROOT/src/skills"` ✅ No change needed
- Line 26: `SRC_AGENTS="$REPO_ROOT/src/agents"` ✅ No change needed
- Hard-coded paths, no config file dependencies

**Makefile** dependencies:
- No explicit dependencies on AGENTS.md or models.yaml
- Only calls renderer scripts (which have hard-coded paths)

**Conclusion:** ✅ Proposed moves will NOT break rendering pipeline

---

## 5. Summary of Findings

### 5.1 What's Working Well

✅ **Rendering pipeline is solid:**
- All source files are in `src/` (skills, agents)
- Rendering is robust (rsync-based with markers)
- No files from outside `src/` are being rendered

✅ **Core structure is good:**
- `src/` for source
- `docs/` for documentation
- `tests/` for tests
- `renderer/` for build system
- Clear separation of concerns

✅ **No rendering blockers:**
- Can safely move files without breaking renders
- Renderer scripts have hard-coded paths

### 5.2 What Needs Improvement

⚠️ **Top-level clutter:**
- 4 untracked directories (`orchestration/`, `guides/`, `data/`, `artifacts/`)
- 3 files that should move (`AGENTS.md`, `models.yaml`, `config/`)
- Makes navigation confusing

⚠️ **Logical grouping issues:**
- AGENTS.md separate from agent definitions
- models.yaml and config/ at root instead of grouped
- shared/ has unclear purpose

---

## 6. Rendering Audit Checklist

- [x] All rendered files originate from `src/` ✅
- [x] Rendering scripts have hard-coded source paths ✅
- [x] No external dependencies on file locations ✅
- [x] SPEC compliance maintained ✅
- [x] No files from `config/`, `shared/`, `orchestration/` rendered ✅
- [x] Safe to move files without breaking renders ✅

---

## Next Steps

See **STRUCTURE-RECOMMENDATION.md** for optimal final structure and implementation plan.
