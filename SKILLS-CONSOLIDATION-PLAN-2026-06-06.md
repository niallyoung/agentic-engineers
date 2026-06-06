# Skills Consolidation & Reorganization Plan
**Date**: 2026-06-06  
**Branch**: unify/2026-06-05-consolidated-cleanup  
**Status**: APPROVED - AWAITING EXECUTION

---

## Executive Summary

Consolidate and reorganize 37 skills to:
1. **Simplify** by merging duplicate validators
2. **Clarify** via consistent naming prefixes
3. **Isolate** meta-skills (framework internal) in `src/skills/meta/`
4. **Apply** harness-specific naming: `harness-opencode-*`, `harness-claude-*`, etc.

**Three phases (Low → High risk):**
- **Phase 2A+2B** (LOW): Rename `todo-maintenance` → `queue-todo-sync` + `opencode-feature-sync` → `harness-opencode-feature-sync`
- **Phase 3** (MEDIUM): Delete `voice-notify` entirely (24+ file updates)
- **Phase 1** (HIGH): Merge `protocol-validation` INTO `protocol-validator` (3 callers, import paths)

---

## PHASE 2A: Rename todo-maintenance → queue-todo-sync

**Risk Level**: 🟢 LOW  
**Files Modified**: 9  
**Impact**: Pure rename, no logic changes

### Files to Update

| # | File | Change | Details |
|---|------|--------|---------|
| 1 | `src/skills/todo-maintenance/` | **RENAME** → `src/skills/queue-todo-sync/` | `git mv` command |
| 2 | `src/skills/queue-todo-sync/SKILL.md` | Update frontmatter | `name: "queue-todo-sync"` |
| 3 | `config/FRAMEWORK-MANIFEST.yaml` | Key + name field | `queue-todo-sync:` and `name: queue-todo-sync` |
| 4 | `docs/SKILLS-AVAILABLE.md` | Table entry | Rename in skill registry table |
| 5 | `TODO.md` | Line 44, 534 | Update references: `todo-maintenance` → `queue-todo-sync` |
| 6 | `src/skills/repo-init/assets/todo-template.md` | Line 70 | Update skill name in template |
| 7 | `docs/archive/deprecated-skills/repo-init/assets/todo-template.md` | Line 70 | Update skill name in template |
| 8 | `src/SKILLS.md` | Category 4 section | Rename row in "Queue Management" |
| 9 | `docs/SKILLS.md` | Category 4 section | Rename row in "Queue Management" |

### Execution Steps

```bash
# 1. Move directory
git mv src/skills/todo-maintenance src/skills/queue-todo-sync

# 2. Update SKILL.md frontmatter
# Edit: src/skills/queue-todo-sync/SKILL.md
# OLD: name: "todo-maintenance"
# NEW: name: "queue-todo-sync"

# 3. Update FRAMEWORK-MANIFEST.yaml
# OLD: todo-maintenance:
# NEW: queue-todo-sync:
# OLD:   name: todo-maintenance
# NEW:   name: queue-todo-sync

# 4. Update all remaining files (use Edit tool)
# docs/SKILLS-AVAILABLE.md, TODO.md, src/skills/repo-init/assets/todo-template.md, etc.

# 5. Verify
git status
grep -r "todo-maintenance" src/ docs/ --include="*.py" --include="*.yaml" --include="*.md" | grep -v archive
# Should return empty

# 6. Run tests
python -m pytest tests/claude/conftest.py -v
```

### Verification

✓ Directory renamed with `git mv`  
✓ No references to `todo-maintenance` remain in active code  
✓ Tests still pass  
✓ `queue-*` prefix grouping complete: `queue-management`, `queue-query`, `queue-todo-sync`

---

## PHASE 2B: Rename opencode-feature-sync → harness-opencode-feature-sync

**Risk Level**: 🟢 LOW  
**Files Modified**: 5  
**Impact**: Naming consistency for harness-specific skills

### Files to Update

| # | File | Change | Details |
|---|------|--------|---------|
| 1 | `src/skills/opencode-feature-sync/` | **RENAME** → `src/skills/harness-opencode-feature-sync/` | `git mv` command |
| 2 | `src/skills/harness-opencode-feature-sync/SKILL.md` | Update frontmatter | `name: "harness-opencode-feature-sync"` |
| 3 | `config/FRAMEWORK-MANIFEST.yaml` | Key + name field | `harness-opencode-feature-sync:` and name |
| 4 | `src/SKILLS.md` | Skill reference | Update `opencode-feature-sync` → `harness-opencode-feature-sync` |
| 5 | `docs/SKILLS.md` | Skill reference | Update `opencode-feature-sync` → `harness-opencode-feature-sync` |

### Execution Steps

```bash
# 1. Move directory
git mv src/skills/opencode-feature-sync src/skills/harness-opencode-feature-sync

# 2. Update SKILL.md frontmatter
# OLD: name: "opencode-feature-sync"
# NEW: name: "harness-opencode-feature-sync"

# 3. Update FRAMEWORK-MANIFEST.yaml
# OLD: opencode-feature-sync:
# NEW: harness-opencode-feature-sync:

# 4. Update SKILLS.md entries
# Update references in src/SKILLS.md and docs/SKILLS.md

# 5. Check for other harness-specific skills
find src/skills -name SKILL.md -exec grep -l "claude\|copilot\|pi\.dev" {} \;
# Apply same harness-* prefix if found

# 6. Verify
grep -r "opencode-feature-sync" src/ --include="*.py" --include="*.yaml" --include="*.md"
# Should return empty
```

### Harness Naming Convention

After this change, harness-specific skills follow pattern:
- `harness-opencode-feature-sync` (OpenCode integration)
- Future: `harness-claude-*`, `harness-copilot-*`, `harness-pi-*` (if skills exist)

### Verification

✓ Directory renamed with `git mv`  
✓ No references to `opencode-feature-sync` remain  
✓ Consistent `harness-*` prefix applied  
✓ Tests pass

---

## COMBINED PHASE 2 COMMIT

After both 2A and 2B complete:

```bash
git add -A
git commit -m "refactor(skills): rename queue-todo-sync and harness-opencode-feature-sync for consistency

- Rename todo-maintenance → queue-todo-sync (queue-related operations)
- Rename opencode-feature-sync → harness-opencode-feature-sync (harness-specific)
- Apply consistent prefix grouping: queue-*, harness-*

Updates FRAMEWORK-MANIFEST.yaml, SKILLS.md, TODO.md, and skill definitions.
All references verified in active code."
```

---

## PHASE 3: Remove voice-notify Skill Entirely

**Risk Level**: 🟠 MEDIUM  
**Files Modified**: 24+  
**Impact**: Removes audio notification integration across shell scripts, CI, docs, tests

### Files to Delete

```
src/skills/voice-notify/              (entire directory)
src/skills/voice-notify.md            (standalone markdown, if exists)
```

### Files to Update (23 locations)

#### Documentation (7 files)

| # | File | Lines | Action |
|---|------|-------|--------|
| 1 | `docs/SPEC.md` | 321–325 | Delete 5 lines with voice-notify script paths |
| 2 | `SPEC.md` (root) | 321–325 | Delete same 5 lines |
| 3 | `docs/SYSTEM.md` | 120 | Remove voice-notify from directory tree |
| 4 | `docs/AGENTS.md` | 470, 488, 500, 547, 864 | Remove 5 references to voice-notify from workflow |
| 5 | `docs/SKILLS-AVAILABLE.md` | (table) | Remove voice-notify row |
| 6 | `docs/CLAUDE_SKILL_MANAGEMENT.md` | 156 | Remove voice-notify entry |
| 7 | `docs/research/claude-docs/CLAUDE_SKILL_MANAGEMENT.md` | 156 | Remove voice-notify entry |

#### Renderer & CI Instructions (3 files)

| # | File | Lines | Action |
|---|------|-------|--------|
| 8 | `renderer/instructions/copilot-instructions.md` | 10 | Remove voice-notify.sh call |
| 9 | `renderer/scripts/copilot-session-init.sh` | 6 | Remove `VOICE_SCRIPT` env var |
| 10 | `setup/GLOBAL_COPILOT_INSTRUCTIONS.md` | 24 | Remove voice-notify instruction |

#### Skill Cross-References (5 files)

| # | File | Lines | Action |
|---|------|-------|--------|
| 11 | `src/skills/ab-testing/SKILL.md` | 45 | Remove voice-notify reference |
| 12 | `src/skills/tokenadvisor/SKILL.md` | 44 | Remove voice-notify reference |
| 13 | `src/skills/skill-creator/SKILL.md` | 117, 121, 166 | Remove voice-notify examples |
| 14 | `src/skills/model-engineer/SKILL.md` | 45 | Remove voice-notify reference |
| 15 | `src/skills/usage-tracking/SKILL.md` | 159, 235, 252 | Remove voice-notify integration |

#### Shell Scripts (2 files)

| # | File | Lines | Action |
|---|------|-------|--------|
| 16 | `src/skills/tokenadvisor/scripts/daily-email-summary.sh` | 93, 95 | Remove/guard voice-notify calls |
| 17 | `src/skills/usage-tracking/scripts/capture_token_usage.sh` | 64, 66 | Remove/guard voice_notify.sh calls |

#### Skill Registries (2 files)

| # | File | Section | Action |
|---|------|---------|--------|
| 18 | `src/SKILLS.md` | Category 12 + 13 | Remove voice-notify row(s) |
| 19 | `docs/SKILLS.md` | Category 12 + 13 | Remove voice-notify row(s) |

#### Test Files (3 files)

| # | File | Lines | Action |
|---|------|-------|--------|
| 20 | `tests/claude/conftest.py` | 54 | Remove `"voice-notify"` from test list |
| 21 | `tests/harnesses/copilot-cli/test_streaming.py` | 50, 75, 91, 194 | Remove from fixtures, update count |
| 22 | `src/evals/skill_matrix/matrix_runner.py` | 39 | Remove from `ALL_SKILLS` |

#### Deprecation Record (1 file)

| # | File | Action |
|---|------|--------|
| 23 | `docs/DEPRECATED-SKILLS.md` | Add entry: `voice-notify` (2026-06-06, simplification) |

### Execution Steps

```bash
# 1. Delete skill directory
git rm -r src/skills/voice-notify/

# 2. Update documentation files
# Use Edit tool to remove voice-notify references from:
# - docs/SPEC.md, SPEC.md (root)
# - docs/SYSTEM.md, docs/AGENTS.md
# - docs/SKILLS-AVAILABLE.md, docs/CLAUDE_SKILL_MANAGEMENT.md
# - renderer/instructions/copilot-instructions.md
# - renderer/scripts/copilot-session-init.sh
# - setup/GLOBAL_COPILOT_INSTRUCTIONS.md

# 3. Update skill cross-references
# - src/skills/ab-testing/SKILL.md
# - src/skills/tokenadvisor/SKILL.md
# - src/skills/skill-creator/SKILL.md
# - src/skills/model-engineer/SKILL.md
# - src/skills/usage-tracking/SKILL.md

# 4. Update shell scripts
# - src/skills/tokenadvisor/scripts/daily-email-summary.sh
# - src/skills/usage-tracking/scripts/capture_token_usage.sh

# 5. Update skill registries
# - src/SKILLS.md (remove Category 12/13 entries)
# - docs/SKILLS.md (remove Category 12/13 entries)

# 6. Update test fixtures
# - tests/claude/conftest.py (remove from test_skills_list)
# - tests/harnesses/copilot-cli/test_streaming.py (remove from fixtures, update counts)
# - src/evals/skill_matrix/matrix_runner.py (remove from ALL_SKILLS)

# 7. Add deprecation record
# - Create/update docs/DEPRECATED-SKILLS.md with voice-notify entry

# 8. Verify no lingering references
grep -r "voice-notify" src/ renderer/ tests/ docs/ --include="*.py" --include="*.sh" --include="*.md" | grep -v archive | grep -v deprecated
# Should return empty

# 9. Run tests
python -m pytest tests/claude/conftest.py -v
python -m pytest tests/harnesses/copilot-cli/test_streaming.py -v
python -m pytest src/evals/skill_matrix/matrix_runner.py -v
```

### Verification

✓ `src/skills/voice-notify/` deleted  
✓ Zero references to `voice-notify` in active code  
✓ Test fixture counts updated  
✓ Tests pass  
✓ Deprecation documented

---

## PHASE 1: Merge protocol-validation INTO protocol-validator

**Risk Level**: 🔴 HIGH  
**Files Modified**: 10+  
**Impact**: Import path changes in 3 production callers; dependency cycle risk

### Current State (Why 3 Skills, Not Duplicates)

| Skill | Purpose | Keep/Merge |
|-------|---------|-----------|
| `protocol-validation` | Base library: core field validator (no I/O, <5ms) | MERGE INTO protocol-validator |
| `protocol-validator` | Spec-driven wrapper: ValidationResult, forward-compat, warnings | KEEP (receives merged) |
| `consistency-checker` | Queue audit: DFS cycles, rate limits, pass-rate report | KEEP (distinct) |

**Result**: 3 skills → 2 skills (`protocol-validator` + `consistency-checker`)

### Files to Update

#### Python Callers (3 production files)

| # | File | Current Import | Update To | Risk |
|---|------|-----------------|-----------|------|
| 1 | `renderer/validate_agents.py` | `src/skills/protocol-validation/scripts` | `src/skills/protocol-validator/scripts` | HIGH |
| 2 | `src/skills/_meta/evaluation_framework/harness_invoker.py` | `src/skills/protocol-validation/scripts` (2 locations) | `src/skills/protocol-validator/scripts` | HIGH |
| 3 | `src/skills/queue-management/scripts/core_protocol_validator.py` | imports from `protocol-validation` | keep imports clean (re-export from validator) | HIGH |

#### Documentation & Examples (7 files)

| # | File | Change | Action |
|---|------|--------|--------|
| 4 | `docs/guides/manual-eval-testing.md` | Line 101 | `protocol-validation` → `protocol-validator` |
| 5 | `src/evals/skill_matrix/protocol.py` | Line 105 (comment) | Update reference |
| 6 | `src/skills/_meta/evaluation_framework/harness_invoker.py` | Lines 156, 164 (DELEGATE example) | `"skill": "protocol-validation"` → `"protocol-validator"` |
| 7 | `tests/test_skill_interop_matrix.py` | Lines 17, 222, 402 (comments) | Update references |
| 8 | `src/SKILLS.md` | Skill registry | Remove `protocol-validation` row, update `protocol-validator` description |
| 9 | `docs/SKILLS.md` | Skill registry | Remove `protocol-validation` row, update `protocol-validator` description |
| 10 | `docs/SKILLS-AVAILABLE.md` | Skill table | Remove `protocol-validation` row |

### Execution Steps

```bash
# 1. Prepare protocol-validator for merge
# - Ensure protocol-validator/scripts/protocol_validator.py exports:
#   - validate_delegate() as module-level function
#   - validate_handback() as module-level function
#   - ProtocolValidator class (already exists)
# - Add backward-compat aliases if needed

# 2. Move protocol-validation content into protocol-validator
# Option A: Copy src/skills/protocol-validation/scripts/* into protocol-validator/scripts/
# Option B: Delete protocol-validation and keep as stub for imports

# 3. Update imports in 3 production callers
# renderer/validate_agents.py
# OLD: from src.skills.protocol-validation.scripts import ...
# NEW: from src.skills.protocol-validator.scripts import ...

# src/skills/_meta/evaluation_framework/harness_invoker.py (2 locations)
# OLD: from src.skills.protocol-validation.scripts import ...
# NEW: from src.skills.protocol-validator.scripts import ...

# src/skills/queue-management/scripts/core_protocol_validator.py
# VERIFY: imports don't create cycle (validator → core_protocol_validator → validator)

# 4. Update documentation references
# docs/guides/manual-eval-testing.md, src/evals/skill_matrix/protocol.py
# harness_invoker.py (DELEGATE example), tests/test_skill_interop_matrix.py
# Update all references: protocol-validation → protocol-validator

# 5. Update skill registries
# src/SKILLS.md, docs/SKILLS.md, docs/SKILLS-AVAILABLE.md
# Remove protocol-validation entries
# Update protocol-validator description: "Canonical DELEGATE/HANDBACK validator (single source of truth)"

# 6. Delete protocol-validation directory
git rm -r src/skills/protocol-validation/

# 7. Run full test suite to catch import breakage
python -m pytest tests/ -v
python -m pytest src/skills/protocol-validator/tests/ -v

# 8. Verify no lingering references to protocol-validation
grep -r "protocol-validation" src/ --include="*.py" --include="*.yaml" --include="*.md"
# Should return empty (except in deprecated/archive)
```

### Dependency Cycle Risk (CRITICAL)

**Current state:**
```
protocol-validator → core_protocol_validator → protocol-validation
```

**After merge:**
```
protocol-validator → core_protocol_validator → protocol-validator (CYCLE!)
```

**Mitigation:**
- Make `core_protocol_validator.py` re-export from `protocol-validator` without importing back
- OR move `CoreProtocolValidator` class definition into `protocol-validator` directly
- Test for circular imports: `python -c "from src.skills.protocol_validator.scripts.protocol_validator import ProtocolValidator; print('OK')"`

### Verification

✓ All 3 production callers updated  
✓ No circular import dependencies  
✓ All tests pass (especially protocol validation tests)  
✓ No references to `protocol-validation` remain in active code  
✓ Single source of truth: `protocol-validator` is now canonical

---

## EXECUTION ORDER (CRITICAL)

Execute phases in this sequence to minimize risk:

1. **Phase 2A + 2B** ← LOW RISK (simple renames)
   - Commit after successful tests
2. **Phase 3** ← MEDIUM RISK (many files, no logic)
   - Commit after successful tests
3. **Phase 1** ← HIGH RISK (imports, possible cycles)
   - Commit after full test suite passes

**Rationale**: If Phase 2 breaks something, it's easy to revert. Phase 3 is tedious but straightforward. Phase 1 is complex—run it last when we're confident the branch is stable.

---

## SUCCESS CRITERIA

### All Phases Complete

- ✅ `src/skills/meta/` directory created with 7 meta-skills
- ✅ `todo-maintenance` → `queue-todo-sync` (all references updated)
- ✅ `opencode-feature-sync` → `harness-opencode-feature-sync` (naming consistent)
- ✅ `voice-notify` removed entirely (24+ files, zero references)
- ✅ `protocol-validation` merged into `protocol-validator` (2 skills instead of 3)
- ✅ All tests pass (4387+ tests)
- ✅ No broken imports
- ✅ Skill registries updated (src/SKILLS.md, docs/SKILLS.md)
- ✅ Deprecation documented (voice-notify in DEPRECATED-SKILLS.md)

### Naming Consistency Achieved

- ✅ `spec-*`: spec-validator, spec-management, spec-extract
- ✅ `queue-*`: queue-management, queue-query, queue-todo-sync
- ✅ `protocol-*`: protocol-validator
- ✅ `agent-*`: agent-creator
- ✅ `harness-*`: harness-integration-tracker, harness-opencode-feature-sync
- ✅ `model-*`: model-engineer, model-selection
- ✅ `cost-*`: cost-aggregation, cost-budgeting
- ✅ `skill-*`: skill-creator
- ✅ `opencode-*`: (deprecated, replaced with harness-opencode-*)

---

## ROLLBACK PLAN (If Needed)

If any phase fails:

```bash
# Revert to last successful commit
git reset --hard <commit-hash>

# Or individual phase rollback
git reset --hard HEAD~1  # Undo last commit
git clean -fd           # Clean working tree
```

---

## NOTES FOR EXECUTION

- Use `git mv` for all directory renames (preserves history)
- Test after each phase before proceeding to next
- Keep shell scripts minimal (no complex logic changes)
- Verify test fixture counts match actual skill count
- Watch for circular imports in Python code (use `python -c` to test)
- Document deprecations with dates and rationale

---

**Ready for execution. Await user approval to proceed with Phase 2A.** 🚀
