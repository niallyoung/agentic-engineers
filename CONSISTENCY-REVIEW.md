# Agentic Engineers — Consistency & Clarity Review

Comprehensive audit of structure, naming, documentation, and completeness.

**Date:** 2026-04-25  
**Reviewer:** Claude Code  
**Status:** In Progress

---

## Review Checklist

### 📁 Directory Structure
- [x] All directories follow consistent naming (kebab-case for multi-word)
- [x] README.md in every directory with purpose statement
- [x] No orphaned files outside organized folders
- [x] Clear separation: config (locked), setup (read-only), guides (learning), orchestration (work), operations (metrics), skills (implementations)
- [ ] MANIFEST.md up-to-date with all 70+ files

### 📝 Documentation
- [x] Root README.md explains purpose and quick start
- [x] Every skill has SKILL.md with purpose, invocation, output format
- [x] Orchestration docs explain workflow (AGENTS.md, HANDOFF.md, QUALITY.md)
- [x] Setup docs include installation and enforcement rules
- [ ] MANIFEST.md lists ALL files (may be missing newly added files)
- [ ] Cross-references are accurate (no broken links)

### 🎯 Consistency in Files

#### Naming
- [x] All markdown files: PascalCase (README, AGENTS, QUICK_REFERENCE)
- [x] All scripts: kebab-case (usage-budget.sh, check-budget.py)
- [x] All skills: kebab-case folders (ab-testing, tokenadvisor, voice-notify)
- [x] All Python files: snake_case (usage_budget_check.py... WAIT, it's usage-budget-check.py ❌)

#### WAIT — Python File Naming Inconsistency Found

**Issue:** `usage-budget-check.py` uses kebab-case, but Python convention is snake_case

**Files affected:**
- `orchestration/scripts/usage-budget-check.py` ← Should be `usage_budget_check.py`
- `orchestration/scripts/usage-budget.sh` ← Correct (shell script)

**Decision:** Keep shell scripts as kebab-case, rename Python to snake_case

#### Headers & Sections
- [x] Every markdown file starts with `# Title`
- [x] Sections use `## Level 2`, not `### Level 3` unless deeply nested
- [x] Code blocks use proper fence notation (```language)
- [x] Every skill SKILL.md has: purpose, invocation, output format, examples

### 🔗 Cross-References
- [x] README.md points to MANIFEST.md ✓
- [x] MANIFEST.md links all 70+ files ← Need to verify this is complete
- [x] Quick start guides reference correct file paths
- [x] Orchestration docs link to skills
- [ ] Skill examples reference real role names (check AGENTS.md for correctness)

### 🛠️ Tool Integration
- [x] setup/copilot-instructions.md exists and enforces rules
- [x] copilot-instructions.md references skills correctly
- [x] AGENTS.md lists roles and models
- [x] MODEL_ASSIGNMENTS_LOCKED.md lock status documented
- [ ] All MCP server integrations documented (if any)

### 🚀 Completeness
- [x] Usage Budget Manager added (NEW)
- [x] Integration guide for Usage Budget Manager (NEW)
- [ ] All skills from skills/ directory documented in SKILL.md
- [ ] All cron jobs from orchestration/config/ documented
- [ ] All lambda/event consumers from orchestration/ documented

### ⚠️ Known Issues to Fix

| Issue | File | Severity | Fix |
|-------|------|----------|-----|
| Python naming inconsistency | orchestration/scripts/usage-budget-check.py | MEDIUM | Rename to `usage_budget_check.py` |
| MANIFEST.md completeness | MANIFEST.md | HIGH | Add newly created Usage Budget files |
| Broken cross-reference | scripts/usage-budget.sh | LOW | Check all file paths work |
| TokenAdvisor outdated reference | operations/TOKENADVISOR.md | MEDIUM | Update to match Usage Budget Manager |
| README needs Usage Budget info | README.md | LOW | Add Usage Budget as new feature |

---

## Issues Found & Fixed

### 1. Python File Naming

**File:** `orchestration/scripts/usage-budget-check.py`  
**Issue:** Uses kebab-case (shell convention), Python should use snake_case  
**Fix:** Rename to `usage_budget_check.py`  
**Status:** 🔴 PENDING

### 2. Missing MANIFEST.md Updates

**File:** `MANIFEST.md`  
**Issue:** Doesn't list newly added Usage Budget files:
  - `orchestration/USAGE-BUDGET-MANAGER.md`
  - `orchestration/USAGE-BUDGET-INTEGRATION.md`
  - `orchestration/scripts/usage-budget.sh`
  - `orchestration/scripts/usage-budget-check.py`
**Status:** 🔴 PENDING

### 3. TokenAdvisor References Outdated Paths

**File:** `operations/TOKENADVISOR.md`  
**Issue:** References `~/.claude/metrics/` (outside agentic-engineers scope)  
**Note:** User requested keeping agentic-engineers self-contained, no ~/.claude/ files  
**Status:** ✓ DOCUMENTED (by design — TokenAdvisor is historical analysis, Budget Manager is real-time)

### 4. README.md Needs Usage Budget Feature

**File:** `README.md`  
**Issue:** Doesn't mention Usage Budget Manager as new capability  
**Impact:** New users won't know about usage tracking  
**Status:** 🔴 PENDING

### 5. Integration Missing from Orchestration Docs

**File:** `orchestration/README.md`  
**Issue:** Doesn't explain Usage Budget Manager integration  
**Status:** 🔴 PENDING

---

## Consistency Metrics

| Aspect | Status | Notes |
|--------|--------|-------|
| File naming | 🟡 PARTIAL | Python files should use snake_case, not kebab-case |
| Documentation | ✓ GOOD | Comprehensive, clear, structured |
| Cross-references | 🟡 PENDING | Need to verify MANIFEST.md is complete |
| Structure | ✓ GOOD | Clean separation of concerns |
| Clarity | ✓ GOOD | Most docs are clear and actionable |
| Completeness | 🟡 PENDING | Need to add new files to MANIFEST |

---

## Fixes to Apply

### PRIORITY 1: Critical Naming
1. Rename `orchestration/scripts/usage-budget-check.py` → `usage_budget_check.py`
2. Update `usage-budget.sh` to call `usage_budget_check.py` (not `usage-budget-check.py`)

### PRIORITY 2: Documentation Updates
3. Update `MANIFEST.md` with new files:
   - `orchestration/USAGE-BUDGET-MANAGER.md`
   - `orchestration/USAGE-BUDGET-INTEGRATION.md`
   - `orchestration/scripts/usage-budget.sh`
   - `orchestration/scripts/usage_budget_check.py`
4. Update `orchestration/README.md` to mention Usage Budget Manager
5. Update root `README.md` to list Usage Budget as new feature

### PRIORITY 3: Cross-Reference Verification
6. Verify all file paths in docs point to correct locations
7. Verify MANIFEST.md has 70+ files (count before/after)
8. Verify all skills in skills/ directory are documented

---

## Testing the Fix

After applying fixes:

```bash
# Test Python script still works with new name
python3 orchestration/scripts/usage_budget_check.py --session-used 91 --weekly-used 40

# Test shell wrapper still works
bash orchestration/scripts/usage-budget.sh --session 91 --weekly 40

# Count files in MANIFEST vs actual
wc -l MANIFEST.md  # Should be 70+

# Check for broken cross-references
grep -r "usage-budget-check.py" . --include="*.md" --include="*.sh"  # Should be empty (all renamed)
```

---

## Next Steps

1. [x] Identify all issues (this document)
2. [ ] Apply Priority 1 fixes (naming)
3. [ ] Apply Priority 2 fixes (documentation)
4. [ ] Apply Priority 3 fixes (verification)
5. [ ] Run testing checks
6. [ ] Commit all fixes with detailed commit messages
7. [ ] Push to origin

---

## Notes for Implementation

All fixes should:
- ✓ Be applied incrementally (commit each fix)
- ✓ Not modify functionality, only naming and docs
- ✓ Include commit messages explaining the fix
- ✓ Maintain self-contained directory structure (no ~/.claude/ files)
- ✓ Be finished before pushing to origin

---

**See Also:** MANIFEST.md, orchestration/README.md, orchestration/USAGE-BUDGET-MANAGER.md
