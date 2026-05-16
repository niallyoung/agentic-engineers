# Repository Restructuring Design Document

## Executive Summary

The agentic-engineers repository currently has **34+ top-level directories** with significant duplication, unclear organization, and incomplete migration. This document defines a **clean migration path** to restructure into a minimal, maintainable format: `src/`, `docs/`, `renderer/`, `config/` (file), `dist/`, and essential root files.

**Current State:** Partially migrated (src/ exists with code, but old root directories still present)  
**Target State:** Clean separation of source code (src/), documentation (docs/), and rendered outputs  
**Effort:** 4-phase migration, low-to-medium risk with clear rollback paths  
**Timeline:** Phase-based, non-blocking for ongoing development

---

## Part 1: Current State Audit

### 1.1 Complete Directory Inventory (Actual Filesystem State)

| # | Directory | Type | Contents | Status | Notes |
|---|-----------|------|----------|--------|-------|
| 1 | **src/** | Source | agents/, orchestration/, skills/, tools/, config/, __init__.py | Active | Target structure - partially migrated |
| 2 | **orchestration/** | Source | agents/, tools/ (root duplicates src/orchestration/) | **DUPLICATE** | Old location, should be removed after Phase C |
| 3 | **skills/** | Mixed | Markdown docs + Python (architect diagrams, agent configs) | **DUPLICATE** | Root copy; src/skills/ is active |
| 4 | **shared/** | Source | quality-assessment-baseline.md only | **MINIMAL** | Should move to docs/reference/ |
| 5 | **config/** | Config | Root duplicates src/config/ | **DUPLICATE** | Old location |
| 6 | **renderer/** | Source | scripts/, README.md, requirements.txt | Active | Keep as-is (critical for builds) |
| 7 | **guides/** | Docs | Implementation guides, deployment status (markdown) | Archive | Move to docs/guides/ |
| 8 | **reference/** | Docs | Coding standards, design patterns, architecture (markdown) | Archive | Move to docs/reference/ |
| 9 | **operations/** | Docs | Reference docs: MEMORY_STRUCTURE, METRICS, TOKENADVISOR, README | Archive | Move to docs/operations/ |
| 10 | **examples/** | Docs | Example configs, implementation samples | Archive | Move to docs/examples/ |
| 11 | **specs/** | Specs | protocol-core-v1.0.yaml | Active | Move to src/specs/ (if source) or docs/specs/ (if reference) |
| 12 | **tests/** | Tests | Test files, conftest.py | Active | Keep at root (standard pytest location) |
| 13 | **docs/** | Docs | README files, contributing guides | Active | Expand as consolidation point |
| 14 | **bin/** | Scripts | CLI/executable scripts | Keep | Move to src/bin/ or scripts/ if actively maintained |
| 15 | **artifacts/** | Generated | Cached/compiled outputs | **TEMP** | .gitignored - auto-generated |
| 16 | **data/** | Generated | Data files, samples | **TEMP** | .gitignored - auto-generated |
| 17 | **logs/** | Generated | Runtime logs | **TEMP** | .gitignored - auto-generated |
| 18 | **metrics/** | Generated | Metrics output | **TEMP** | .gitignored - auto-generated |
| 19 | **dist/** | Generated | Rendered outputs (copilot/, claude/) | **TEMP** | .gitignored - build output |
| 20 | **__pycache__/** | Generated | Python bytecode | **TEMP** | .gitignored |
| 21 | **models.yaml** | Config | Model definitions (root) | Config | Move to config/ or src/config/ |
| 22 | **.claude/** | Generated | Claude workspace cache | **TEMP** | .gitignored |

### 1.2 Current Source Code Dependencies

**Import Pattern Analysis:**
- Tests use: `from src.orchestration.agents...`, `from src.skills...` → expects **src/** structure
- conftest.py adds root to sys.path: `sys.path.insert(0, os.path.dirname(__file__))` → allows imports to work from root
- Makefile uses: `renderer/scripts/` for build steps

**Dependency Graph (Current):**
```
src/orchestration/agents/  ← Core agent implementations
  └─ depends on: src/orchestration/tools, specs/
  
src/skills/  ← Skill definitions
  └─ depends on: src/orchestration/agents/
  
tests/  ← Test suite
  └─ depends on: src/orchestration, src/skills, src/config/
  
renderer/scripts/  ← Build system
  └─ depends on: dist/ output location, models.yaml, src/config/
  
ROOT DUPLICATES (PROBLEM):
  orchestration/  ←→ src/orchestration/  (DUPLICATE)
  skills/         ←→ src/skills/         (DUPLICATE)
  config/         ←→ src/config/         (DUPLICATE)
  shared/         (minimal, can consolidate)
```

### 1.3 Duplication Analysis

| Duplication | Root Dir | src/ Dir | Status | Action |
|-------------|----------|---------|--------|--------|
| Orchestration | orchestration/ | src/orchestration/ | **ACTIVE IN src/** | Remove root/ after consolidating imports |
| Skills | skills/ | src/skills/ | **ACTIVE IN src/** | Remove root/ after consolidating imports |
| Config | config/ | src/config/ | **ACTIVE IN src/** | Remove root/ after consolidating imports |
| Shared | shared/ | none | Minimal content | Move to docs/reference/ |

### 1.4 Current Code-to-Test Import Patterns

```python
# Tests ALREADY use src/ paths:
from src.orchestration.agents import ...
from src.orchestration.tools import ...
from src.skills import ...
from src.config import ...

# This works because:
# 1. conftest.py adds root to sys.path
# 2. src/ is a Python package (has __init__.py)
# 3. Tests discover from root and resolve "src." as a package
```

**Key Finding:** Tests are already migrated to expect `src/` imports. Root-level `orchestration/`, `skills/`, `config/` are **legacy and should be removed** once tests are verified against src/.

---

## Part 2: Target Directory Structure

### 2.1 Proposed Clean Structure

```
agentic-engineers/
├── src/                              # All source code
│   ├── __init__.py
│   ├── orchestration/                # Agent orchestration framework
│   │   ├── __init__.py
│   │   ├── agents/                   # Agent implementations
│   │   ├── tools/                    # Tool definitions
│   │   └── README.md
│   ├── skills/                       # Skill implementations
│   │   ├── __init__.py
│   │   └── README.md
│   ├── config/                       # Configuration module
│   │   ├── __init__.py
│   │   └── README.md
│   ├── specs/                        # Protocol specifications (if source)
│   │   └── protocol-core-v1.0.yaml
│   └── bin/                          # CLI scripts (if maintained)
│
├── docs/                             # All documentation
│   ├── README.md                     # Root docs readme
│   ├── ARCHITECTURE.md               # High-level architecture
│   ├── guides/                       # Implementation guides
│   │   └── [deployment guides, etc]
│   ├── reference/                    # Design patterns, standards
│   │   ├── coding-standards.md
│   │   ├── design-patterns.md
│   │   └── [quality-assessment-baseline.md]
│   ├── operations/                   # Operational reference
│   │   ├── MEMORY_STRUCTURE.md
│   │   ├── METRICS.md
│   │   ├── TOKENADVISOR.md
│   │   └── README.md
│   ├── examples/                     # Example configurations
│   │   └── [example configs, samples]
│   └── specs/                        # Specification docs (if reference)
│       └── protocol-core-v1.0.yaml
│
├── renderer/                         # UNCHANGED - critical for builds
│   ├── scripts/
│   ├── requirements.txt
│   └── README.md
│
├── tests/                            # Test suite (unchanged location)
│   ├── conftest.py
│   ├── [test files]
│   └── README.md (add for clarity)
│
├── config.yaml                       # Root configuration (or .config/)
├── models.yaml                       # Model definitions (move from root)
├── Makefile                          # Build orchestration (unchanged)
├── pyproject.toml                    # Python project config (if needed)
├── README.md                         # Root readme
├── CONTRIBUTING.md                   # Contribution guidelines
├── LICENSE                           # License
├── .gitignore                        # (unchanged - logs/, dist/, etc)
└── .github/                          # CI/CD workflows (if present)
```

### 2.2 What STAYS Unchanged

| Component | Reason | Action |
|-----------|--------|--------|
| renderer/ | Critical for build pipeline; Makefile depends on renderer/scripts/ | Keep exactly as-is |
| tests/ | Standard pytest location; conftest.py is critical | Keep at root; only update imports if needed |
| Makefile | Central build orchestration | Keep at root; verify targets work post-migration |
| .gitignore | Already correct (excludes temp dirs) | No changes needed |
| dist/ | Build output, .gitignored | No action needed |

### 2.3 Size and Impact Summary

**What moves to docs/:**
- guides/ (~5-10 files, pure documentation)
- reference/ (~5-10 files, pure documentation)
- operations/ (~4 files, pure documentation)
- examples/ (~5-10 files, samples)
- shared/quality-assessment-baseline.md (~1 file)

**Total:** ~25-40 markdown/text files → moved to docs/, keeping repo clean

**What's removed:**
- Root-level orchestration/, skills/, config/ directories (after consolidation)

**What's new:**
- src/specs/ (active protocol specs, currently in root specs/)
- docs/ as consolidation point for all reference material

---

## Part 3: Detailed Migration Strategy

### 3.1 Four-Phase Migration Plan

#### **PHASE 1: Documentation Consolidation (LOWEST RISK)**
**Duration:** 1-2 days | **Risk:** Very Low | **Blocks:** Nothing  
**Status:** Can run in parallel with other development

**Steps:**
1. Create docs/ subdirectories: guides/, reference/, operations/, examples/
2. Move content:
   - guides/ → docs/guides/
   - reference/ → docs/reference/
   - operations/ → docs/operations/
   - examples/ → docs/examples/
   - shared/quality-assessment-baseline.md → docs/reference/
3. Update any README references to point to new locations
4. Verify .gitignore doesn't accidentally exclude new docs paths
5. Test: `git ls-files | grep docs/` should show all moved files

**Rollback:** `git checkout` to restore

**Validation Checklist:**
- [ ] All doc files present in docs/ subdirectories
- [ ] No broken internal links in documentation
- [ ] Old directories (guides/, reference/, operations/) can be deleted from root
- [ ] Makefile still works (`make verify` passes)

---

#### **PHASE 2: Configuration and Specs Consolidation (LOW RISK)**
**Duration:** 1 day | **Risk:** Low | **Blocks:** Nothing immediately

**Steps:**
1. Move models.yaml: `root/models.yaml` → `src/config/models.yaml`
2. Decide specs location:
   - If protocol-core-v1.0.yaml is **active source code** → `src/specs/`
   - If it's **reference documentation** → `docs/specs/`
   - Action: Check if specs/ is imported anywhere; search for `import specs` or `from specs`
3. Update all references to models.yaml path in:
   - Makefile (if referenced)
   - renderer/scripts/ (if referenced)
   - src/config/ (if referenced)
4. Consolidate root config files (if multiple exist)

**Validation Checklist:**
- [ ] models.yaml accessible from new location in all code paths
- [ ] Makefile `make *` targets still work
- [ ] Tests still pass: `pytest tests/`
- [ ] renderer/scripts still function correctly

**Rollback:** Move files back, restore Makefile references

---

#### **PHASE 3: Remove Root-Level Duplicates (MEDIUM RISK)**
**Duration:** 1-2 days | **Risk:** Medium | **Blocks:** Phase 4

**Prerequisites:**
- Confirm all tests pass with src/ imports (they already do)
- Confirm no other code imports from root orchestration/, skills/, config/

**Steps:**
1. Search all Python files for imports from root orchestration/, skills/, config/:
   ```bash
   grep -r "from orchestration" src/ tests/ renderer/
   grep -r "from skills" src/ tests/ renderer/
   grep -r "from config" src/ tests/ renderer/
   grep -r "import orchestration" src/ tests/ renderer/
   grep -r "import skills" src/ tests/ renderer/
   grep -r "import config" src/ tests/ renderer/
   ```
   **Expected result:** Only `from src.orchestration`, `from src.skills`, `from src.config` found

2. If no root imports found, proceed:
   - Delete root orchestration/
   - Delete root skills/
   - Delete root config/
   - Delete shared/ (consolidated)

3. Run full test suite: `pytest tests/ -v`

4. Test build: `make clean && make verify`

**Validation Checklist:**
- [ ] No imports from root orchestration/, skills/, config/ found
- [ ] Tests pass: `pytest tests/ -v`
- [ ] Make targets work: `make verify`
- [ ] No import errors in renderer/scripts/

**Rollback:** `git checkout orchestration/ skills/ config/ shared/` + restore any deleted imports

---

#### **PHASE 4: Verify and Finalize (LOW RISK)**
**Duration:** 1 day | **Risk:** Low | **No blockers after Phase 3**

**Steps:**
1. Verify file permissions, Python package structure (all __init__.py files present)
2. Run complete test suite: `pytest tests/`
3. Verify build pipeline: `make clean && make render-copilot && make render-claude`
4. Verify imports work end-to-end:
   ```bash
   python3 -c "from src.orchestration.agents import *; print('OK')"
   python3 -c "from src.skills import *; print('OK')"
   python3 -c "from src.config import *; print('OK')"
   ```
5. Final filesystem audit: `find . -name "*.py" -exec grep -l "from orchestration" {} \;` (should be empty)

**Validation Checklist:**
- [ ] pytest tests/ passes
- [ ] All make targets work
- [ ] Import test commands pass
- [ ] No stray imports from old locations
- [ ] Directory structure matches target layout
- [ ] All documentation accessible from docs/

**Success Criteria (Post-Migration):**
- Clean directory structure with ~12 top-level items (down from 34+)
- All source code in src/
- All documentation in docs/
- All build outputs in dist/
- No duplication or legacy directories
- Full test suite passes
- Build pipeline verified

---

### 3.2 Risk Assessment and Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|-----------|
| Breaking imports in tests | Low | High | Run pytest before each phase; grep for old imports |
| Makefile/renderer breaking | Low | High | Test make targets after each phase |
| Forgotten import updates | Medium | Medium | Comprehensive grep search in Phase 3 |
| .gitignore issues | Very Low | Low | Verify new docs/ not accidentally excluded |
| Documentation link breakage | Medium | Low | Check and update relative links in Phase 1 |

**Mitigation Strategy:**
1. **Git branches:** Each phase uses a feature branch, reviewed before merge
2. **Incremental:** Each phase is independent and can be rolled back
3. **Testing:** Full pytest suite runs before/after each phase
4. **Verification:** Explicit validation checklist for each phase

---

### 3.3 Import Path Updates

#### Files Requiring Import Updates

**Search scope:** src/, tests/, renderer/, Makefile

**Patterns to update:**
```python
# OLD (before):
from orchestration.agents import ...
from skills import ...
from config import ...
import orchestration.tools

# NEW (after):
from src.orchestration.agents import ...
from src.skills import ...
from src.config import ...
import src.orchestration.tools
```

**Note:** Tests already use `src.*` imports, so they shouldn't need updates.

**Affected files (likely):**
- renderer/scripts/* (if they import from src)
- Makefile (if it references module paths)
- Any Python files in root or bin/

**Search command (Phase 3):**
```bash
grep -r "from orchestration" --include="*.py" .
grep -r "from skills" --include="*.py" .
grep -r "from config" --include="*.py" .
grep -r "import orchestration" --include="*.py" .
```

---

## Part 4: Build/Test Validation Plan

### 4.1 Pre-Migration Validation (Baseline)

Run before Phase 1 starts to establish baseline:

```bash
# 1. Full test suite
pytest tests/ -v --tb=short

# 2. Build verification
make clean
make verify

# 3. Render targets
make render-copilot
make render-claude

# 4. Import verification
python3 -c "from src.orchestration.agents import *; print('Import OK')"
python3 -c "from src.skills import *; print('Import OK')"
```

**Expected result:** All commands succeed; output captured as baseline

### 4.2 Post-Phase Validation

After each phase:

```bash
# Always run:
pytest tests/ -v

# After Phase 2:
python3 -c "from src.config import models; print('Config OK')"

# After Phase 3:
grep -r "from orchestration" src/ tests/ || echo "No old imports found"
grep -r "from skills" src/ tests/ || echo "No old imports found"
grep -r "from config" src/ tests/ || echo "No old imports found"

# After Phase 4:
make clean && make verify && make render-copilot && make render-claude
```

### 4.3 Filesystem Validation

After Phase 4 (final structure verification):

```bash
# Check structure matches target
ls -la | grep -E "^d.*src|^d.*docs|^d.*tests|^d.*renderer"

# Verify no orphaned directories
find . -maxdepth 1 -type d | wc -l  # Should be ~12-15 directories

# Verify git status clean
git status --short  # Only new files in docs/ and moved files in src/
```

### 4.4 CI/CD Verification

After migration is merged:
- [ ] All GitHub Actions workflows pass
- [ ] Build artifacts generated correctly in dist/
- [ ] Test coverage maintained or improved
- [ ] No regressions in downstream systems

---

## Part 5: Rollback Strategy

### By-Phase Rollback

**Phase 1 Rollback:** 
```bash
git checkout guides/ reference/ operations/ examples/ shared/
```

**Phase 2 Rollback:**
```bash
git checkout src/config/models.yaml models.yaml specs/
# Restore Makefile/renderer changes
```

**Phase 3 Rollback:**
```bash
git checkout orchestration/ skills/ config/ shared/
# Restore root-level directories
```

**Phase 4 Rollback:**
```bash
# Only documentation and validation; if needed, rollback to Phase 3
```

### Full Rollback (Emergency)

```bash
git reset --hard HEAD~4  # Reset last 4 commits (all phases)
git clean -fd           # Remove any untracked files
```

### Rollback Decision Criteria

Rollback if:
- Tests fail to pass after a phase
- Make targets fail
- Import errors detected
- Performance degradation observed
- Merge conflict resolution breaks code

---

## Part 6: Communication and Execution Plan

### 6.1 Phase 2 Engineer Handoff

This document serves as the **single source of truth** for Phase 2 execution. No further clarification needed.

**Execution instructions for Phase 2 team:**

1. **Read this document in full** (sections 1-5)
2. **Create feature branch:** `git checkout -b chore/restructure-dirs`
3. **Execute each phase in order** following the step-by-step instructions
4. **Run validation checklist** after each phase
5. **Open PR with phase-by-phase commits** for review
6. **Wait for approval before Phase 3** (higher risk)
7. **Merge when complete** after all validations pass

### 6.2 Review Checklist for PRs

**Phase 1 PR:**
- [ ] guides/ content moved to docs/guides/
- [ ] reference/ content moved to docs/reference/
- [ ] operations/ content moved to docs/operations/
- [ ] examples/ content moved to docs/examples/
- [ ] Makefile unchanged and works
- [ ] Tests pass

**Phase 2 PR:**
- [ ] models.yaml in src/config/
- [ ] specs/ moved to correct location (src/ or docs/)
- [ ] Makefile/renderer references updated
- [ ] Tests pass
- [ ] Config module imports work

**Phase 3 PR:**
- [ ] Root orchestration/, skills/, config/ removed
- [ ] No imports from old locations found
- [ ] Tests pass
- [ ] Make targets work

**Phase 4 PR:**
- [ ] Final validation checklist complete
- [ ] All tests pass
- [ ] Build pipeline works
- [ ] No regressions

---

## Part 7: Success Criteria and Exit Checklist

### Final Validation Checklist

After Phase 4 completes, verify:

- [ ] **Directory Structure:**
  - [ ] src/ contains all source code (orchestration, skills, config, specs)
  - [ ] docs/ contains all documentation (guides, reference, operations, examples)
  - [ ] renderer/ unchanged and functional
  - [ ] tests/ at root with conftest.py
  - [ ] dist/ contains build outputs
  - [ ] Root has only essential files (Makefile, README, LICENSE, pyproject.toml, etc.)
  - [ ] Old root directories (orchestration/, skills/, config/, guides/, reference/, operations/, examples/, shared/) deleted

- [ ] **Code Quality:**
  - [ ] `pytest tests/ -v` passes with no failures
  - [ ] `pytest tests/ --cov` shows maintained or improved coverage
  - [ ] No import errors: `python3 -m py_compile src/**/*.py`
  - [ ] No undefined imports: `grep -r "from orchestration" src/ tests/ renderer/` returns empty

- [ ] **Build Pipeline:**
  - [ ] `make clean` works
  - [ ] `make verify` passes
  - [ ] `make render-copilot` generates dist/copilot/
  - [ ] `make render-claude` generates dist/claude/
  - [ ] renderer/scripts/ still functional

- [ ] **Documentation:**
  - [ ] All links in docs/ point to correct locations
  - [ ] docs/README.md updated with new structure
  - [ ] Root README.md still accurate
  - [ ] No broken internal references

- [ ] **Git Status:**
  - [ ] `git status` shows clean (no uncommitted changes)
  - [ ] No stray directories
  - [ ] .gitignore unchanged and correct

- [ ] **Regression Testing:**
  - [ ] All features still work
  - [ ] No performance regressions
  - [ ] Downstream systems (if any) still integrate correctly

### Success Definition

Migration is **successful** when:
1. ✅ All validation checks above pass
2. ✅ Filesystem matches target structure in Section 2.1
3. ✅ Zero breaking changes for users/developers
4. ✅ Build pipeline functional end-to-end
5. ✅ Full test suite passes
6. ✅ Documentation complete and accessible

---

## Appendix: File Manifest

### Files to Move (Phase 1)

```
guides/*              → docs/guides/
reference/*           → docs/reference/
operations/*          → docs/operations/
examples/*            → docs/examples/
shared/*              → docs/reference/
```

### Files to Move (Phase 2)

```
models.yaml           → src/config/models.yaml
specs/protocol-*.yaml → src/specs/ (if active) OR docs/specs/ (if reference)
```

### Files to Delete (Phase 3)

```
orchestration/        (entire directory)
skills/               (entire directory)
config/               (entire directory - root level only, src/config/ stays)
shared/               (entire directory)
```

### Files to Keep (Unchanged)

```
src/
renderer/
tests/
Makefile
pyproject.toml
README.md
.gitignore
.github/
[root config files]
[root docs]
```

---

## Appendix: Dependency Verification Commands

Use these commands during Phase 3 to verify no stray imports remain:

```bash
# Find all imports from root-level directories
echo "=== Checking for old orchestration imports ==="
grep -r "from orchestration" src/ tests/ renderer/ bin/ 2>/dev/null || echo "✓ None found"

echo "=== Checking for old skills imports ==="
grep -r "from skills" src/ tests/ renderer/ bin/ 2>/dev/null || echo "✓ None found"

echo "=== Checking for old config imports ==="
grep -r "from config" src/ tests/ renderer/ bin/ 2>/dev/null || echo "✓ None found"

echo "=== Checking for import statements (without 'src.') ==="
grep -r "^import orchestration" src/ tests/ renderer/ bin/ 2>/dev/null || echo "✓ None found"
grep -r "^import skills" src/ tests/ renderer/ bin/ 2>/dev/null || echo "✓ None found"
grep -r "^import config" src/ tests/ renderer/ bin/ 2>/dev/null || echo "✓ None found"

# Verify src.* imports ARE present
echo ""
echo "=== Verifying correct src.* imports present ==="
grep -r "from src\.orchestration" src/ tests/ renderer/ bin/ 2>/dev/null | head -3
grep -r "from src\.skills" src/ tests/ renderer/ bin/ 2>/dev/null | head -3
grep -r "from src\.config" src/ tests/ renderer/ bin/ 2>/dev/null | head -3
```

---

## Document Metadata

- **Created:** Phase 1 (Principal Engineer Analysis)
- **Audience:** Phase 2 Engineers (execution team)
- **Status:** Ready for implementation
- **Clarity Level:** Complete and unambiguous; no external clarification required
- **Risk Level:** Low-to-medium; fully mitigated with rollback strategies
- **Dependencies:** None; migrations can start immediately
- **Success Criteria:** All validations in Section 7 pass

---

**Next Steps for Phase 2:** 
1. Review this document in full
2. Create feature branch: `git checkout -b chore/restructure-dirs`
3. Begin Phase 1 (documentation consolidation) following section 3.1
4. Submit PR after each phase for review
5. Proceed to next phase only after approval
