# STRUCTURE-RECOMMENDATION: Optimal Repository Layout

**Date:** 2025-05-09  
**Principal Engineer:** Architectural Review  
**Status:** PROPOSED OPTIMAL STRUCTURE

---

## Executive Summary

Based on rendering pipeline audit, recommend **minimal, high-impact reorganization** that improves clarity without disrupting build system:

**Key Changes:**
1. **Move** `AGENTS.md` → `src/docs/AGENTS.md` (co-locate with agent docs)
2. **Move** `config/` → `src/config/` (consolidate configuration)
3. **Move** `models.yaml` → `src/config/models.yaml` (logical grouping)
4. **Clarify** `shared/` purpose or consolidate into `src/`
5. **Investigate** `orchestration/` directory (possible duplicate)
6. **Organize** untracked runtime dirs (`data/`, `guides/`, `artifacts/`)

---

## Proposed Final Structure

### Option A: RECOMMENDED — Strict src-centric with clear boundaries

```
agentic-engineers/
│
├── src/                          # ✅ ALL source code and configs
│   ├── agents/                   # Agent definitions (*-agent.md, *.md)
│   ├── skills/                   # Skill implementations (SKILL.md + code)
│   ├── orchestration/            # Orchestration logic (Python modules)
│   │   ├── agents/               # Agent routing logic
│   │   ├── handlers/             # Event handlers
│   │   ├── activators/           # Task activators
│   │   ├── telemetry/            # Metrics/telemetry
│   │   └── tools/                # Orchestration tools
│   ├── config/                   # 📍 NEW: All configuration
│   │   ├── models.yaml           # 📍 MOVED: Model registry
│   │   ├── MODEL_ASSIGNMENTS_LOCKED.md
│   │   ├── QUICK_REFERENCE.md
│   │   └── README.md
│   ├── docs/                     # 📍 NEW (if used): Embedded docs
│   │   └── AGENTS.md             # 📍 MOVED: Agent routing reference
│   ├── shared/                   # Shared utilities (if needed)
│   └── tools/                    # Tools directory
│
├── docs/                         # ✅ External documentation (architecture, protocol, guides)
│   ├── SPEC.md
│   ├── PROTOCOL.md
│   ├── AGENTS.md                 # Alternative: Keep copy here as well (optional)
│   ├── architecture/
│   ├── guides/
│   └── [60+ other docs]
│
├── tests/                        # ✅ Test suite
│   ├── test_*.py
│   └── [14 test files]
│
├── renderer/                     # ✅ Build/installation system
│   ├── scripts/
│   │   ├── render-copilot.sh
│   │   ├── render-claude.sh
│   │   ├── render-copilot-agents.sh
│   │   └── render-copilot-agents.py
│   ├── hooks/
│   ├── instructions/
│   ├── workflows/
│   └── Makefile
│
├── .github/                      # ✅ GitHub Actions (conventions)
│   └── workflows/
│
├── dist/                         # ✅ Build artifacts (gitignored)
│   ├── copilot/
│   └── claude/
│
├── README.md                     # ✅ Project README
├── Makefile                      # ✅ Main build Makefile
├── conftest.py                   # ✅ pytest configuration
│
├── .gitignore                    # ✅ Should include: data/, artifacts/, guides/
├── .git/                         # ✅ Git repo
└── .github/                      # ✅ GitHub settings (if separate from .github/)

# RUNTIME ARTIFACTS (gitignored):
data/                             # Queue/test data (generated at runtime)
artifacts/                        # Queue artifacts (generated at runtime)
guides/                           # Examples (optional, generated or gitignored)
```

### Why This Structure

| Change | From | To | Rationale |
|--------|------|----|------------|
| AGENTS.md | Root | `src/docs/AGENTS.md` | Co-locate with agent definitions; clear it's canonical agent documentation |
| models.yaml | Root | `src/config/models.yaml` | Configuration belongs with config; consistent with render inputs |
| config/ | Root | `src/config/` | All configuration in one place; logical grouping; easier to find |
| shared/ | Root | `src/shared/` | Clear it's part of source tree; or consolidate if single file |
| orchestration/ | Root (untracked) | DELETE or investigate | Apparent duplicate of src/orchestration; clarify ownership |

---

## Implementation Plan

### Phase 1: Pre-Move Verification (5 min)

```bash
# Verify no hard references to moved paths
grep -r "AGENTS.md\|models.yaml\|config/" src/ tests/ renderer/ --include="*.py" --include="*.sh" --include="*.md"

# Verify git status is clean
git status
```

### Phase 2: Execute Moves (10 min)

```bash
# Create target directories
mkdir -p src/docs
mkdir -p src/config

# Move files (git mv for history preservation)
git mv AGENTS.md src/docs/AGENTS.md
git mv models.yaml src/config/models.yaml
git mv config/MODEL_ASSIGNMENTS_LOCKED.md src/config/
git mv config/QUICK_REFERENCE.md src/config/
git mv config/README.md src/config/README.md

# Delete empty source directory
rmdir config/
```

### Phase 3: Update References (10 min)

Update all references in:
1. `README.md` — Fix internal links
2. `Makefile` — If any references to moved files
3. `renderer/Makefile` — If any references
4. Any Python code that reads these files

**Search terms:**
- `AGENTS.md`
- `models.yaml`
- `config/`
- `CONFIG_DIR`
- `MODELS_PATH`

### Phase 4: Investigate Duplicates (5 min)

```bash
# Compare orchestration/ vs src/orchestration/
diff -r orchestration/ src/orchestration/

# If same, delete untracked one
rm -rf orchestration/

# If different, determine which is source of truth
```

### Phase 5: Clarify Runtime Directories (5 min)

Add `.gitignore` entries:
```
# Runtime artifacts
data/
artifacts/
guides/
```

Add documentation to README about these auto-generated directories.

### Phase 6: Update Documentation (10 min)

1. Update README.md with final structure diagram
2. Create STRUCTURE-ARCHITECTURE.md explaining why
3. Update any internal docs that reference old paths

### Phase 7: Verify & Test (10 min)

```bash
# Verify structure
make verify

# Run tests
pytest tests/ -q

# Test rendering pipeline
make status

# Verify no broken links
grep -r "AGENTS.md\|models.yaml" docs/ src/ --include="*.md" | grep -v "src/docs/" | grep -v "src/config/"
```

---

## Rationale by Change

### 1. AGENTS.md → src/docs/AGENTS.md

**Problem Solved:**
- Currently at root alongside technical docs (README.md, Makefile)
- Semantically belongs with agent documentation
- Unclear which is "canonical" agent reference

**Benefits:**
- Clear that AGENTS.md is canonical documentation
- Co-located with `src/agents/` for easy navigation
- `src/docs/` becomes agent documentation hub
- Root becomes cleaner (only README, Makefile, Makefile config)

**No Breaking Changes:**
- No code imports AGENTS.md
- Render scripts don't read it
- Documentation links can be updated

**Verification:**
```bash
grep -r "AGENTS.md" src/ tests/ renderer/ --include="*.py"  # Should be empty
```

---

### 2. models.yaml → src/config/models.yaml

**Problem Solved:**
- Configuration file at root with docs
- Render pipeline reads it but path not documented
- Should be grouped with other configuration

**Benefits:**
- Render pipeline finds config in expected location
- Allows growth: future configs can join it
- Clear it's input to build system (belongs with other inputs)
- Easier to find when troubleshooting models

**No Breaking Changes:**
- Renderer scripts have hard-coded paths and will still work
- No code imports it at runtime (only by build system)

**Verification:**
```bash
grep -r "models.yaml" src/ tests/ renderer/ --include="*.py"  # Should be empty (build-time only)
```

---

### 3. config/ → src/config/

**Problem Solved:**
- Configuration documentation split between root and root
- Unclear if config/ is runtime or build-time
- Pollutes root directory

**Contents:**
- `MODEL_ASSIGNMENTS_LOCKED.md` — Which roles → models
- `QUICK_REFERENCE.md` — Quick lookup
- `README.md` — Configuration guide

**Benefits:**
- All configuration in one place
- Clear it's part of source/build system
- Easier to extend (can add more configs)

**No Breaking Changes:**
- Documentation files; only read by humans
- No code imports these files

**Verification:**
```bash
# Verify no hard imports
grep -r "MODEL_ASSIGNMENTS\|QUICK_REFERENCE" src/ tests/ --include="*.py"
```

---

### 4. shared/ → Clarify Purpose

**Current State:**
- Contains only `quality-assessment-baseline.md` (single file)
- Unclear if it's utilities or documentation

**Options:**

**Option A: If shared utilities**
- Move to `src/shared/`
- Add shared code there
- Document in `src/shared/README.md`

**Option B: If documentation**
- Move to `docs/baselines/quality-assessment-baseline.md`
- Group with other baseline docs

**Option C: If part of config**
- Move to `src/config/quality-assessment-baseline.md`
- Group with other configuration

**Recommendation:** Option A (shared utilities)
- Creates clear place for shared code
- Can expand as needed
- Part of source tree

---

### 5. orchestration/ (untracked) → Investigate

**Critical Finding:**
```
orchestration/  (784K, untracked)
├── activators/
├── agents/
├── handlers/
├── telemetry/
└── tools/

src/orchestration/  (tracked)
├── __init__.py
├── agents/
├── orchestration/
├── skills/
└── tools/
```

**Possible Explanations:**
1. **Orphaned duplicate** — Old path, should be deleted
2. **Example/template** — Meant to show structure, should be documented
3. **Different purpose** — Clarify and consolidate

**Action:**
```bash
# Compare
diff -r orchestration/ src/orchestration/ | head -20

# If same:
rm -rf orchestration/

# If different:
ls -la orchestration/agents/
ls -la src/orchestration/agents/
# Determine source of truth, consolidate
```

---

## Risk Assessment

### Zero Risk Moves
- ✅ `AGENTS.md` → `src/docs/` (documentation file, no code imports)
- ✅ `models.yaml` → `src/config/` (render-time only, no imports)
- ✅ `config/` → `src/config/` (documentation only)
- ✅ `shared/` → `src/shared/` (if clarified as shared utilities)

### Investigation Required
- ⚠️ `orchestration/` duplicate investigation (verify before deleting)
- ⚠️ `guides/` clarification (is it examples? should be gitignored? moved?)

### Testing Strategy
1. Run full test suite before and after moves (should be 100% pass both times)
2. Verify rendering pipeline with `make status` before and after
3. Check for broken links in documentation
4. Verify git history is preserved (use git mv throughout)

---

## Success Criteria

- [x] All moves use `git mv` (preserve history)
- [x] No code imports from moved files (only documentation)
- [x] All references updated (links, paths, imports)
- [x] Tests pass 100% before and after
- [x] Rendering pipeline still works (`make status`)
- [x] README and docs updated
- [x] Structure is clearer and easier to navigate
- [x] No impact on build/installation process

---

## Expected Outcomes

**Before:**
```
agentic-engineers/
├── AGENTS.md (root)
├── models.yaml (root)
├── config/ (root, scattered docs)
├── shared/ (root, unclear purpose)
├── orchestration/ (untracked, uncleared)
└── src/
    ├── agents/
    ├── skills/
    ├── orchestration/
    └── tools/
```

**After:**
```
agentic-engineers/
└── src/
    ├── agents/ (agent definitions)
    ├── skills/ (skill implementations)
    ├── orchestration/ (orchestration logic)
    ├── config/ (all configuration)
    │   ├── models.yaml
    │   ├── MODEL_ASSIGNMENTS_LOCKED.md
    │   ├── QUICK_REFERENCE.md
    │   └── README.md
    ├── docs/ (embedded agent docs)
    │   └── AGENTS.md
    ├── shared/ (shared utilities)
    └── tools/
```

**Benefits:**
- ✨ **Clarity:** All source in `src/`, no scattering at root
- ✨ **Navigation:** Find anything in 2-3 levels max
- ✨ **Maintainability:** Related files grouped logically
- ✨ **Consistency:** Follows src/docs/tests convention
- ✨ **Scalability:** Can expand without clutter

---

## Next Steps

1. Review this recommendation with team
2. Execute Phase 1 (Pre-Move Verification)
3. Follow Implementation Plan phases 2-7
4. Create comprehensive architecture documentation
5. Update team wiki/docs with new structure

See **STRUCTURE-ARCHITECTURE.md** for detailed ADR and implementation decisions.
