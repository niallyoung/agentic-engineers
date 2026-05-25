# Version-Manager Remediation Plan

**Principal Engineer Use**: Decision & Implementation Guide

---

## Executive Decision Matrix

| Option | Best For | Effort | Risk | PR Impact |
|--------|----------|--------|------|-----------|
| **A: Delete** | All scenarios | 1-2 hrs | ✅ None | ✅ Unblocked |
| **B: Fix** | If preview needed | 4-6 hrs | ⚠️ Moderate | ⚠️ Improved |
| **C: Convention-changelog** | Standard workflows | 3-4 hrs | ✅ Low | ✅ Unblocked |

**Security Engineer Recommendation**: **Option A**

---

## Option A Implementation: DELETE version-manager

### Phase 1: Analysis & Planning (15 minutes)

**Pre-implementation checklist**:
- [ ] Security briefing reviewed by Principal Engineer
- [ ] Team consensus on removing skill (vs fixing/replacing)
- [ ] No active PRs depending on version-manager

**Decision point**: Approve for implementation? → YES / NO

---

### Phase 2: Code Changes (30-45 minutes)

#### Step 1: Update Pre-Commit Hook

**File**: `.githooks/pre-commit`

**Current** (lines 42-71):
```bash
# ─── Agent frontmatter consistency check ───────────────────────────────
# [version-manager related code]
validate_agent_frontmatter() {
    # ... version-manager specific logic ...
}

# Run validation (only if docs/AGENTS.md and src/agents/ exist)
REPO_ROOT_HOOK=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
if [ -f "$REPO_ROOT_HOOK/docs/AGENTS.md" ] && [ -d "$REPO_ROOT_HOOK/src/agents" ]; then
    if ! validate_agent_frontmatter "$REPO_ROOT_HOOK"; then
        # ...
    fi
fi
```

**Action**: Keep this (it's agent frontmatter validation, not version-manager)

**NEW SECTION TO DELETE** (Find & remove version-manager related hooks):

Search for and remove:
- [ ] `update-changelog.py --auto` calls
- [ ] Version-manager git add commands
- [ ] Any `CHANGELOG.md` staging in pre-commit

**Result**: Pre-commit hook should have NO version-manager logic

---

#### Step 2: Deprecate Skill

**File**: `skills/version-manager/SKILL.md`

**Action**: Replace entire content with:

```markdown
---
title: "version-manager (DEPRECATED)"
description: "DEPRECATED — Removed 2026-05-26 due to architectural conflicts"
role: "Security Engineer"
status: "deprecated"
deprecation_date: "2026-05-26"
reason: "Git tags (from CI/CD) are the authoritative version source. Local version-manager creates conflicting sources of truth, introduces merge conflicts, and provides no benefits over existing git tag-based versioning."
replacement: "Use `git tag` directly or GitHub Releases (created automatically by CI/CD)"
---

# version-manager (DEPRECATED)

## Deprecation Notice

**This skill is deprecated as of 2026-05-26 and should not be used.**

### Why Deprecated

1. **Architectural Conflict**: VERSIONING.md states "git tags are the ONLY source of truth," but version-manager creates a second source in CHANGELOG
2. **Design Flaw**: `[Unreleased] - vX.Y.Z` violates semantic versioning standards
3. **Workflow Impact**: Auto-updating CHANGELOG on every commit causes merge conflicts on parallel PRs
4. **Bypass Risk**: Git hooks are easily bypassed (`--no-verify`)

### What to Use Instead

**For version management**: Git tags (created automatically by CI/CD in `.github/workflows/ci.yml`)

**For CHANGELOG**: 
1. Keep `[Unreleased]` section (without version numbers)
2. Update only at release time (not on every commit)
3. Validate in CI/CD before merge

### Migration

If you have local `.git/hooks/pre-commit` from this skill:
```bash
git config core.hooksPath .githooks  # Use repo hooks (version-manager removed)
```

### References

- Security Audit: docs/SECURITY-AUDIT-VERSION-MANAGER.md
- Briefing: SECURITY-BRIEFING-VERSION-MANAGER.md
- Versioning Strategy: VERSIONING.md

---

**Last Updated**: 2026-05-26
```

---

#### Step 3: Update Documentation

**File**: `VERSIONING.md`

**Section to Update** (lines 1-30):

Delete OR mark deprecated:
```markdown
### Automatic Semantic Versioning (DEPRECATED - use git tags only)
```

**Replace with**:
```markdown
## Version Management Strategy

All versioning is managed through **git tags** created automatically by CI/CD. 

See `.github/workflows/ci.yml` for the automated tagging workflow.

No local version-manager skill is required — tags are the single authoritative source.
```

**Remove sections**:
- "Automatic Semantic Versioning" (if version-manager specific)
- "Local Workflow Integration" (if version-manager specific)
- Any references to `scripts/version-manager/update-changelog.py`

---

#### Step 4: Update Contributing Guide

**File**: `CONTRIBUTING.md`

**Add section** (new):

```markdown
## Release Process

When releasing a new version:

1. **Verify CHANGELOG.md is current**
   - Add section: `## [X.Y.Z] - YYYY-MM-DD`
   - Move unreleased changes under this section
   - No auto-generation — manual update only

2. **Create git tag**
   ```bash
   git tag vX.Y.Z
   git push --tags
   ```

3. **CI/CD handles the rest**
   - GitHub Actions detects tag
   - Creates GitHub Release automatically
   - Generates release notes from git history

4. **Verify release**
   - Check GitHub Releases page
   - Verify tag matches CHANGELOG version
```

---

#### Step 5: Clean Up TODO.md

**File**: `TODO.md`

**Action**: Remove any TODOs related to:
- [ ] version-manager maintenance
- [ ] [Unreleased] section updates
- [ ] CHANGELOG validation

---

### Phase 3: File Deletion (5 minutes)

**Delete these files**:
- [ ] `skills/version-manager/` (entire directory)
- [ ] `scripts/version-manager/` (if it exists)
- [ ] `dist/*/skills/version-manager/` (generated copies)

**Verify deletion**:
```bash
cd /Users/niall/git/agentic-engineers
find . -type d -name "*version-manager*" 2>/dev/null
# Should return: (no results)
```

---

### Phase 4: Testing (15 minutes)

#### Test 1: Verify hooks work

```bash
# Ensure hooks are enabled
git config core.hooksPath
# Should output: .githooks

# Test hook execution
cd /tmp && mkdir test-agentic && cd test-agentic
git clone /Users/niall/git/agentic-engineers .

# Make a test commit
git config user.email "test@example.com"
git config user.name "Test User"
echo "test" > test.txt
git add test.txt
git commit -m "test: verify hooks work"
# Should succeed without version-manager errors
```

#### Test 2: Verify no version-manager logic remains

```bash
# Search for references
grep -r "version-manager\|update-changelog\|[Unreleased]" \
  .githooks/*.sh \
  scripts/*.py \
  --include="*.sh" --include="*.py" 2>/dev/null || echo "No references found (good)"
```

#### Test 3: Manual release (dry-run)

```bash
# Simulate release process
git log v0.8.0..HEAD --oneline | grep "^feat\|^fix" | wc -l
# Count commits to determine version bump

# Example: 15 commits with mix of feat/fix → minor bump → v0.9.0
git tag v0.9.0 2>/dev/null || echo "Tag would be v0.9.0"
git tag -d v0.9.0 2>/dev/null || true  # Clean up test tag

echo "✅ Manual release process works"
```

---

### Phase 5: Validation (10 minutes)

**Checklist before merging**:
- [ ] No `.githooks/` files reference version-manager
- [ ] `skills/version-manager/` directory deleted
- [ ] `VERSIONING.md` updated (no version-manager references)
- [ ] `CONTRIBUTING.md` has release process documented
- [ ] `TODO.md` cleaned of version-manager items
- [ ] Manual git tag works correctly
- [ ] CHANGELOG.md has proper format (no [Unreleased] versions)

---

### Phase 6: Code Review & Merge

**Code Review Checklist**:
- [ ] Security audit reviewed (SECURITY-AUDIT-VERSION-MANAGER.md)
- [ ] Briefing reviewed (SECURITY-BRIEFING-VERSION-MANAGER.md)
- [ ] All hooks tested successfully
- [ ] No remaining version-manager references
- [ ] Documentation accurate and complete

**Commit Message**:
```
chore(security): remove version-manager skill

Removes version-manager skill and related local versioning automation
due to architectural conflicts with git tag-based versioning strategy.

VERSIONING.md established that "git tags are the ONLY source of truth,"
but version-manager created conflicting [Unreleased] versions in CHANGELOG,
caused merge conflicts on parallel PRs, and introduced hook bypass risks.

Changes:
- Delete skills/version-manager/ directory
- Remove version-manager hooks from .githooks/pre-commit
- Update VERSIONING.md and CONTRIBUTING.md
- All versioning now via git tags (CI/CD creates automatically)

Security Issues Resolved:
- Eliminates git hook bypass risk (git commit --no-verify)
- Removes CHANGELOG.md corruption vulnerability
- Eliminates [Unreleased] merge conflicts
- Single source of truth (git tags only)

See SECURITY-BRIEFING-VERSION-MANAGER.md for full analysis.

Fixes: PR merge workflow blocking on CHANGELOG conflicts
```

---

## Option B Implementation: FIX version-manager (Alternative)

**Only if team prefers to keep local version preview**

### Required Changes

1. **Remove version numbers from [Unreleased]**
   - File: `changelog_updater.py` line 125
   - Change: `f"## [Unreleased] - v{next_version}"` → `"## [Unreleased]"`

2. **Make hooks manual-only**
   - File: `.githooks/pre-commit`
   - Remove: auto-invocation of `update-changelog.py`
   - Users run manually: `python3 scripts/version-manager/update-changelog.py`

3. **Add atomic writes**
   - File: `changelog_updater.py` write_changelog()
   - Use: tempfile + fsync + os.replace() for atomic writes

4. **Add CI/CD validation**
   - File: Create `scripts/validate_changelog_ci.py`
   - Check: [Unreleased] matches git history

5. **Update pre-merge gate**
   - File: `.github/workflows/ci.yml`
   - Add: Validation step before merge

**Effort**: 4-6 hours  
**Risk**: Moderate (still has hook bypasses)  
**Ongoing Maintenance**: Medium

---

## Option C Implementation: conventional-changelog (Alternative)

**For industry-standard automated CHANGELOG generation**

### Required Changes

1. **Install conventional-changelog**
   - File: `.github/workflows/ci.yml`
   - Add: `npm install conventional-changelog-cli` or use GitHub Action

2. **Remove local version-manager**
   - Delete `skills/version-manager/`
   - Delete `.githooks/pre-commit` version-manager logic

3. **Update release workflow**
   - File: `.github/workflows/ci.yml` release step
   - Add: `conventional-changelog -i CHANGELOG.md -s` before tag

4. **Manual CHANGELOG updates**
   - CHANGELOG generated only on release (in CI/CD)
   - No local development updates
   - Still maintain `[Unreleased]` for development PRs

**Effort**: 3-4 hours  
**Risk**: Low (CI/CD controlled)  
**Dependencies**: Node.js in GitHub Actions (acceptable)

---

## Decision Record

**Principal Engineer**: _________________

**Date**: _________________

**Approved Option**:
- [ ] Option A: Delete version-manager
- [ ] Option B: Fix version-manager  
- [ ] Option C: Use conventional-changelog

**Rationale**: 

```
_________________________________________________________________

_________________________________________________________________
```

**Implementation By**: _________________

**Testing Lead**: _________________

**Code Review Lead**: _________________

---

## Post-Implementation Validation

**After merging security fix**:

1. **Verify no regresssion**
   ```bash
   grep -r "[Unreleased] - v" . --include="*.md"
   # Should return: only in docs/SECURITY-AUDIT-VERSION-MANAGER.md (examples)
   ```

2. **Test release workflow**
   - Create test tag
   - Verify CI/CD creates release
   - Verify CHANGELOG format is correct

3. **Monitor next 3 releases**
   - Check for CHANGELOG conflicts
   - Verify merge process smooth
   - No hook bypass issues

---

## Success Criteria

**Implementation is successful when**:
- ✅ No version-manager files in codebase
- ✅ No CHANGELOG merge conflicts in next 3 PRs
- ✅ Manual release process tested and works
- ✅ `git commit --no-verify` no longer modifies CHANGELOG
- ✅ All developers understand new release process
- ✅ No `[Unreleased]` with version numbers remains

---

**Document Status**: READY FOR PRINCIPAL ENGINEER REVIEW  
**Created**: 2026-05-26  
**Last Updated**: 2026-05-26
