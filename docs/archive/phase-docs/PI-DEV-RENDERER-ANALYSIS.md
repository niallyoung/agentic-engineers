# π.dev Renderer — Gap Analysis & Implementation Roadmap

**Task ID**: 2026-05-16-pi-dev-renderer-analysis  
**Author**: Senior Engineer  
**Date**: 2026-05-16  
**Status**: Complete (analysis only — no implementation)  
**Source**: `renderer/scripts/render-pi-dev.py`, `renderer/scripts/render-pi.sh`, `renderer/pi-dev-src/`

---

## Executive Summary

The π.dev renderer (`render-pi-dev.py` + `render-pi.sh`) is a functional but immature harness. It correctly installs five files to `~/.pi/agent/` and handles install/uninstall/status lifecycle modes. However, it carries two confirmed bugs, five structural limitations, and a documentation gap that collectively reduce its reliability and maintainability. This document provides root-cause analysis, impact assessment, and a tiered implementation roadmap.

**Overall Maturity Rating**: ⚠️ Beta — functional for basic use, not production-ready

---

## 1. Confirmed Bugs

### Bug 1 — Argument Parsing Heuristic (render-pi-dev.py, line 312)

**Location**: `main()` function, single-argument branch  
**Code**:
```python
if "/.pi" in argv[0] or argv[0].endswith(".pi"):
    # treat as destination
else:
    # treat as source
```

**Root Cause**:  
When the script receives a single positional argument, it must decide whether the user passed a source directory or a destination directory. The heuristic checks whether the string `"/.pi"` appears anywhere in the path, or whether the path ends with `.pi`. This is a string-matching shortcut that substitutes for proper CLI design.

**Failure Modes**:

| Scenario | Argument | Expected Behavior | Actual Behavior |
|----------|----------|-------------------|-----------------|
| Source dir with `.pi` in name | `/home/user/.pi-backup/src` | Treat as source | Treated as destination ❌ |
| Destination not under home | `/mnt/data/pi-config` | Treat as destination | Treated as source ❌ |
| Relative path `./pi-dev-src` | `./pi-dev-src` | Treat as source | Treated as source ✅ (coincidence) |
| Destination `~/projects/.pi` | `~/projects/.pi` | Treat as destination | Treated as destination ✅ |

**Impact**: Medium. The failure modes are edge cases in typical use, but they are silent — the renderer will proceed with the wrong interpretation and either fail to find source files or write to an unexpected location. No error is raised until a file operation fails.

**Proposed Fix**:  
Replace positional argument ambiguity with explicit named flags:
```python
# Replace current single-arg heuristic with:
parser = argparse.ArgumentParser(description="π.dev Harness Renderer")
parser.add_argument("--src", default=None, help="Source directory (default: renderer/pi-dev-src/)")
parser.add_argument("--dest", default=None, help="Destination base (default: ~/.pi)")
parser.add_argument("--uninstall", action="store_true")
parser.add_argument("--status", action="store_true")
# Preserve backward-compatible positional args for existing callers
parser.add_argument("src_pos", nargs="?", default=None)
parser.add_argument("dest_pos", nargs="?", default=None)
```

This eliminates the heuristic entirely. Named flags are unambiguous; positional args can remain for backward compatibility but without the string-matching logic.

**Effort**: Small — 1–2 hours. Requires updating `render-pi.sh` to use `--src`/`--dest` flags.

---

### Bug 2 — Premature Directory Creation in `__init__` (render-pi-dev.py, line 65)

**Location**: `PiDevRenderer.__init__()`, line 65  
**Code**:
```python
def __init__(self, src_dir: str, dest_dir: str):
    self.src_dir = Path(src_dir)
    self.dest_dir = Path(dest_dir)
    self.agent_dir = self.dest_dir / "agent"
    
    # Ensure destination directories exist
    self.agent_dir.mkdir(parents=True, exist_ok=True)  # ← BUG
```

**Root Cause**:  
`PiDevRenderer` is instantiated before the mode (install/status/uninstall) is determined. The constructor unconditionally creates `~/.pi/agent/` regardless of what operation will follow. This violates the principle of minimal side effects: constructors should not perform I/O unless the object's purpose is inherently I/O-bound.

**Failure Modes**:

| Mode | Expected Side Effect | Actual Side Effect |
|------|---------------------|-------------------|
| `--status` on clean system | None (report "not installed") | Creates `~/.pi/agent/` ❌ |
| `--uninstall` on clean system | None (report "nothing to uninstall") | Creates `~/.pi/agent/` ❌ |
| `--status` on installed system | None | Creates `~/.pi/agent/` (already exists, harmless) ✅ |
| Install | Create `~/.pi/agent/` | Creates `~/.pi/agent/` ✅ |

**Impact**: Low-Medium. For `--status`, the bug causes a false positive: `self.agent_dir.exists()` returns `True` even on a clean system, so the status check reports "installed" with all files missing rather than "not installed." For `--uninstall`, the directory is created and immediately found empty, so the uninstall reports success with 0 files removed — which is technically correct but misleading.

**Proposed Fix**:  
Defer `mkdir` to `render_all()` only:
```python
def __init__(self, src_dir: str, dest_dir: str):
    self.src_dir = Path(src_dir)
    self.dest_dir = Path(dest_dir)
    self.agent_dir = self.dest_dir / "agent"
    # Do NOT create directories here

def render_all(self) -> int:
    # Create directories only when actually rendering
    self.agent_dir.mkdir(parents=True, exist_ok=True)
    ...
```

**Effort**: Trivial — 15 minutes. One line moved from `__init__` to `render_all()`.

---

## 2. Structural Limitations

### Limitation 1 — No Content Transformation

**Description**:  
The renderer copies files from `renderer/pi-dev-src/` verbatim. Unlike the OpenCode renderer (`render-opencode.sh`) and Claude Code renderer (`render-claude.sh`), it does not pull content from `src/agents/` or apply any transformation pipeline. The five source files (`SYSTEM.md`, `AGENTS.md`, `settings.json`, `pi.yml`, `SUB_AGENT_SETUP.md`) are manually maintained and must be kept in sync with the canonical sources by hand.

**Root Cause**:  
The π.dev renderer was built as a simpler alternative to the shell-based renderers. The decision to use a static source directory (`pi-dev-src/`) rather than a dynamic transformation pipeline was intentional, but the maintenance burden was underestimated.

**Current Sync Requirements** (manual, error-prone):
- `docs/AGENTS.md` changes → must update `renderer/pi-dev-src/AGENTS.md`
- Model ID changes in `docs/AGENTS.md` → must update `settings.json`, `pi.yml`, `SYSTEM.md`, `SUB_AGENT_SETUP.md`
- New agent role → must update all five files
- Role removal → must update all five files

**Impact**: High. Any change to the canonical agent model requires manual updates to five files. Drift is likely over time — and has already occurred (see Limitation 4: stale model IDs).

**Workaround**: Manual sync discipline + checklist in `SUB_AGENT_SETUP.md` (currently documented).

**Fix Options**:
- **Option A (Minimal)**: Add a `make check-pi-sync` target that diffs `renderer/pi-dev-src/AGENTS.md` against `docs/AGENTS.md` and fails if they diverge. Low effort, catches drift.
- **Option B (Full)**: Implement a transformation pipeline that generates `pi-dev-src/` files from `src/agents/` and `docs/AGENTS.md`, similar to how `render-opencode.sh` works. High effort, eliminates drift permanently.

**Effort**: Option A = 2 hours; Option B = 8–12 hours.

---

### Limitation 2 — No Per-File Sentinel Protection

**Description**:  
The renderer has no mechanism to detect whether a managed file has been modified outside the renderer. If a user edits `~/.pi/agent/AGENTS.md` directly, the next `make install-pi` will silently overwrite their changes.

The marker file (`.agentic-engine-pi`) indicates that the renderer was used, but it is a single installation-level marker — not a per-file content hash or sentinel comment.

**Root Cause**:  
The other harnesses (OpenCode, Claude Code) use sentinel comments embedded in rendered files (e.g., `<!-- managed by agentic-engineers render-opencode.sh; user edits to AGENTS.md.local will be loaded after this file -->`). The π.dev renderer was not designed with this pattern.

**Impact**: Low in practice (users are unlikely to edit `~/.pi/agent/` files directly), but medium in principle (silent data loss is a serious UX failure).

**Proposed Fix**:  
Add a sentinel header to each rendered file:
```
<!-- managed by agentic-engineers render-pi-dev.py — do not edit directly -->
<!-- source: renderer/pi-dev-src/AGENTS.md — re-render with: make install-pi -->
```

On re-render, check for the sentinel before overwriting. If absent, warn the user and require `--force` to proceed.

**Effort**: Medium — 3–4 hours (add sentinel injection to `copy_file()`, add sentinel check, add `--force` flag).

---

### Limitation 3 — Stale Model IDs

**Description**:  
At the time of the HARNESS-REVIEW.md audit (2026-05-15), the source files contained `claude-3-5-sonnet-20241022` and `claude-3-5-opus-20250514` — model IDs from 2024 that do not match the canonical framework model IDs.

**Current State** (as of 2026-05-16, post-update):  
The source files have been updated to use current model IDs:
- `claude-haiku-4.5` (Orchestrator, Engineer)
- `claude-sonnet-4-20250514` (Senior Engineer, Lead Engineer, Quality Engineer, Model Engineer)
- `claude-opus-4-20250514` (Principal Engineer, Security Engineer)

**Residual Risk**:  
Because there is no content transformation pipeline (Limitation 1), model IDs are hardcoded in four separate files. The next model generation update will require manual changes to all four files again. The pattern of staleness is structural, not a one-time oversight.

**Proposed Fix**:  
Define model IDs in a single source-of-truth file (e.g., `renderer/pi-dev-src/models.json`) and generate the other files from it. Until a transformation pipeline exists, add model IDs to the sync checklist.

**Effort**: Low (checklist update) to High (transformation pipeline).

---

### Limitation 4 — Role Count Mismatch (9 vs. 8)

**Description**:  
At the time of the HARNESS-REVIEW.md audit, the π.dev source files documented 9 roles (including "Spec Engineer" and "Healing Engineer") while the canonical framework defines 8 roles. The HARNESS-REVIEW.md compliance table noted this as a content issue.

**Current State** (as of 2026-05-16):  
The source files have been updated to the canonical 8-role model. `AGENTS.md`, `SYSTEM.md`, `pi.yml`, and `SUB_AGENT_SETUP.md` all now document exactly 8 roles.

**Residual Risk**:  
Same as Limitation 3 — the structural absence of a transformation pipeline means any future role addition or removal requires manual updates to multiple files.

**Proposed Fix**:  
Same as Limitation 3 — single source of truth for role definitions.

---

### Limitation 5 — Speculative Sub-Agent Features

**Description**:  
`pi.yml` and `settings.json` contain features that are not verified against the actual π.dev runtime:

**In `settings.json`**:
```json
{
  "packages": ["orchestration-framework"],
  "extensions": ["agent-orchestrator", "specialized-agents"],
  "skills": ["delegate", "handback", "route-task", "collect-metrics", "verify-completion"]
}
```

**In `pi.yml`**:
```yaml
routing:
  rules:
    - condition: "security-scoped"
      agent: "security-engineer"
      priority: 1
    ...
```

These `packages`, `extensions`, `skills`, and `routing.rules` keys are not documented in the π.dev API. The `pi.yml` file itself carries a prominent warning comment, and `SUB_AGENT_SETUP.md` documents the limitation clearly. However, `PI-DEV-RENDERER.md` (the primary user-facing documentation) does not warn users that these features may have no effect.

**Root Cause**:  
The π.dev API was researched but not fully verified at the time the renderer was built. The speculative features were included to provide a complete configuration template, with the expectation that they would be verified and either confirmed or removed.

**Impact**: Medium. Users who rely on `pi.yml` routing for actual sub-agent dispatch will be disappointed. The routing conditions (`"security-scoped"`, `"cross-service-architecture"`) are not π.dev API strings — they are agentic-engineers concepts that π.dev has no knowledge of.

**Workaround**: The `SYSTEM.md` system prompt instructs the Orchestrator to route tasks manually using the decision tree. This works because π.dev reads `SYSTEM.md` as the system prompt. Sub-agent routing via `pi.yml` is a bonus if it works; the system functions without it.

**Proposed Fix**:
1. **Short-term**: Update `PI-DEV-RENDERER.md` to clearly mark speculative features (same warning as `pi.yml` and `SUB_AGENT_SETUP.md`).
2. **Medium-term**: Verify π.dev API against actual runtime. Remove unverified keys or replace with verified equivalents.
3. **Long-term**: If π.dev does not support native sub-agent routing, remove `routing.rules` from `pi.yml` and rely entirely on `SYSTEM.md` prompt-based routing.

**Effort**: Documentation update = 1 hour; API verification = 2–4 hours (requires π.dev access and testing).

---

### Limitation 6 — PyYAML Dependency

**Description**:  
`render-pi-dev.py` imports `yaml` (PyYAML) for YAML validation of `pi.yml`. PyYAML is not part of the Python standard library and is not always available in base Python environments.

**Root Cause**:  
The renderer was written assuming a development environment with common packages installed. The other harnesses (OpenCode, Claude Code) use shell scripts with no external dependencies.

**Impact**: Low in practice (most developer environments have PyYAML), but it creates a setup friction point and is not documented in `PI-DEV-RENDERER.md`.

**Proposed Fix**:
- Add `pyyaml` to `requirements.txt` or document it as a prerequisite.
- Alternatively, make YAML validation optional with a graceful fallback:
```python
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("⚠️  PyYAML not installed — skipping YAML validation (pip install pyyaml)")
```

**Effort**: Trivial — 30 minutes.

---

## 3. Documentation Gaps

### Gap 1 — PI-DEV-RENDERER.md "What It Does" Table

The table at the top of `PI-DEV-RENDERER.md` lists only 3 files:

| File | Purpose | Bootstrap Impact |
|------|---------|------------------|
| SYSTEM.md | Complete system prompt | Replaces pi default |
| AGENTS.md | Agent role definitions | Appended as project context |
| settings.json | Model & UI defaults | Loaded on pi startup |

The renderer actually manages 5 files (`pi.yml` and `SUB_AGENT_SETUP.md` are missing). This is a documentation accuracy issue.

**Fix**: Add `pi.yml` and `SUB_AGENT_SETUP.md` rows to the table, with appropriate "Speculative" notes for `pi.yml`.

---

### Gap 2 — No Warning for Speculative Features in PI-DEV-RENDERER.md

`PI-DEV-RENDERER.md` presents `pi.yml` as enabling "Sub-agent orchestration configuration" without noting that the routing rules are unverified. Users reading only this file will not know the limitation.

**Fix**: Add a "Known Limitations" section to `PI-DEV-RENDERER.md` mirroring the warnings in `SUB_AGENT_SETUP.md`.

---

### Gap 3 — No Dependency Documentation

`PI-DEV-RENDERER.md` does not mention the `pyyaml` dependency. Users on minimal Python environments will encounter an `ImportError` with no guidance.

**Fix**: Add a "Prerequisites" section listing `python3` and `pyyaml`.

---

## 4. render-pi.sh Assessment

The Bash wrapper script is well-implemented:

| Feature | Status | Notes |
|---------|--------|-------|
| Prerequisite checks | ✅ | Validates renderer and source dir before proceeding |
| Marker file | ✅ | Writes `.agentic-engine-pi` timestamp on install |
| Uninstall guard | ✅ | Checks marker before removing — safe on clean systems |
| Error propagation | ✅ | `set -euo pipefail` — exits on any error |
| Mode handling | ✅ | Clean `case` statement for install/uninstall/status |

**One discrepancy**: The marker file (`.agentic-engine-pi`) is written by `render-pi.sh` but is not in `MANAGED_FILES` in `render-pi-dev.py`. This means the Python renderer will not remove the marker during uninstall — but `render-pi.sh` handles this correctly by removing the marker separately after calling the Python renderer. The behavior is correct; the design is slightly incoherent (the marker is managed by the shell wrapper, not the Python renderer).

**No bugs found** in `render-pi.sh`.

---

## 5. Implementation Roadmap

### Tier 1 — Critical Fixes (Do First)

These fixes address confirmed bugs and high-impact documentation gaps. All are low-effort.

| ID | Item | File | Effort | Impact |
|----|------|------|--------|--------|
| T1-1 | Fix `__init__` premature `mkdir` | `render-pi-dev.py` | 15 min | Fixes false-positive status, spurious dir creation |
| T1-2 | Add speculative features warning to `PI-DEV-RENDERER.md` | `PI-DEV-RENDERER.md` | 1 hr | Prevents user confusion about `pi.yml` routing |
| T1-3 | Add `pi.yml` and `SUB_AGENT_SETUP.md` to "What It Does" table | `PI-DEV-RENDERER.md` | 15 min | Documentation accuracy |
| T1-4 | Add PyYAML graceful fallback | `render-pi-dev.py` | 30 min | Prevents hard failure on minimal environments |

**Total Tier 1 effort**: ~2 hours

---

### Tier 2 — Important Improvements (Do Soon)

These address the argument parsing bug and add basic drift detection.

| ID | Item | File | Effort | Impact |
|----|------|------|--------|--------|
| T2-1 | Replace `"/.pi"` heuristic with `argparse` + explicit flags | `render-pi-dev.py`, `render-pi.sh` | 2 hr | Eliminates silent misrouting on edge-case paths |
| T2-2 | Add `make check-pi-sync` target to detect content drift | `renderer/Makefile` | 2 hr | Catches AGENTS.md / model ID drift before it ships |
| T2-3 | Add sentinel header to rendered files | `render-pi-dev.py` | 3 hr | Warns users before overwriting manual edits |
| T2-4 | Document PyYAML prerequisite in `PI-DEV-RENDERER.md` | `PI-DEV-RENDERER.md` | 15 min | Setup clarity |

**Total Tier 2 effort**: ~7–8 hours

---

### Tier 3 — Strategic Improvements (Phase 3+)

These address the structural limitation of no content transformation pipeline. Higher effort, higher long-term value.

| ID | Item | Effort | Impact |
|----|------|--------|--------|
| T3-1 | Verify π.dev API: confirm which `settings.json` / `pi.yml` keys are recognized | 4 hr | Removes speculative uncertainty; enables cleanup |
| T3-2 | Remove unverified keys from `settings.json` and `pi.yml` (if unverified) | 1 hr | Reduces noise; cleaner config |
| T3-3 | Implement content transformation pipeline (generate `pi-dev-src/` from `src/agents/`) | 8–12 hr | Eliminates manual sync; prevents model ID drift permanently |
| T3-4 | Add per-file content hash to marker system | 3 hr | Enables change detection; supports `--force` flag |

**Total Tier 3 effort**: ~16–20 hours

---

## 6. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| User hits `"/.pi"` heuristic bug | Low | Medium (silent wrong behavior) | T2-1: replace with argparse |
| `--status` creates spurious directory | Medium | Low (cosmetic) | T1-1: defer mkdir |
| Model IDs drift again on next update | High | Medium (stale config) | T2-2: sync check; T3-3: pipeline |
| User edits `~/.pi/agent/` files manually | Low | Medium (silent overwrite) | T2-3: sentinel header |
| PyYAML not installed | Low | Low (hard failure) | T1-4: graceful fallback |
| `pi.yml` routing has no effect | High (already true) | Low (system works via SYSTEM.md) | T1-2: document clearly |
| π.dev API changes break `settings.json` | Medium | Medium | T3-1: verify API; T3-2: cleanup |

---

## 7. Summary of Findings

### Bugs (2 confirmed)

1. **Argument parsing heuristic** (`"/.pi" in argv[0]`): brittle string matching that silently misroutes edge-case paths. Fix: replace with `argparse` explicit flags.
2. **Premature `mkdir` in `__init__`**: creates `~/.pi/agent/` even in `--status`/`--uninstall` modes, causing false-positive status reports. Fix: defer `mkdir` to `render_all()`.

### Limitations (6 identified)

1. **No content transformation**: files are manually maintained, not generated from canonical sources. Drift is inevitable without a sync check or pipeline.
2. **No per-file sentinel protection**: silent overwrite of user edits on re-render.
3. **Stale model IDs** (resolved 2026-05-16, but structurally recurrent without a pipeline).
4. **Role count mismatch** (resolved 2026-05-16, same structural root cause as #3).
5. **Speculative sub-agent features**: `pi.yml` routing and `settings.json` extensions are not verified against the π.dev runtime and may have no effect.
6. **PyYAML dependency**: undocumented, causes hard failure if not installed.

### Documentation Gaps (3 identified)

1. `PI-DEV-RENDERER.md` "What It Does" table omits `pi.yml` and `SUB_AGENT_SETUP.md`.
2. `PI-DEV-RENDERER.md` does not warn users that `pi.yml` routing is speculative.
3. `PI-DEV-RENDERER.md` does not document the PyYAML prerequisite.

### What Works Well

- Core file copy logic is correct and idempotent.
- YAML and JSON validation are properly implemented.
- `render-pi.sh` wrapper is clean, well-guarded, and handles all modes correctly.
- Uninstall correctly removes only managed files, preserving π.dev-managed files.
- `SUB_AGENT_SETUP.md` is honest about speculative features.
- `pi.yml` carries clear warning comments about unverified features.
- Source files are now up-to-date with the canonical 8-role model and current model IDs.

---

## 8. Recommended Phase 3 Work

Based on this analysis, the recommended Phase 3 priorities are:

1. **T1-1** (15 min): Fix premature `mkdir` — trivial, immediate correctness improvement.
2. **T1-2** (1 hr): Document speculative features in `PI-DEV-RENDERER.md` — user-facing clarity.
3. **T1-3** (15 min): Fix "What It Does" table — documentation accuracy.
4. **T1-4** (30 min): PyYAML graceful fallback — defensive coding.
5. **T2-1** (2 hr): Replace argument parsing heuristic — eliminates the most surprising bug.
6. **T2-2** (2 hr): Add `make check-pi-sync` — prevents future content drift.

Items T3-1 through T3-4 (API verification and transformation pipeline) are Phase 4+ work, contingent on the π.dev harness being actively used and the team having bandwidth for a larger refactor.

---

*Analysis complete. No implementation performed. All findings are based on static code review of `render-pi-dev.py`, `render-pi.sh`, `renderer/pi-dev-src/`, `renderer/PI-DEV-RENDERER.md`, and `docs/HARNESS-REVIEW.md` (lines 169–268).*
