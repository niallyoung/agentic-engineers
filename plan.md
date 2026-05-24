# Implementation Plan: Fix CHANGELOG [Unreleased] Issue

## Summary

The project uses **CI/CD-driven semantic versioning** where git tags are created automatically by CI/CD. However, `version-manager` was designed for **local versioning workflows** and automatically injects `[Unreleased]` sections on every commit, causing a design mismatch.

**Root cause:** version-manager pre-commit hook contradicts the actual versioning strategy.

**Solution:** Disable version-manager from auto-running on commits. Keep CHANGELOG with only released versions.

## Phase 1: Disable version-manager in pre-commit hook

**File:** `.githooks/pre-commit` (lines 468-493)

**What to do:**
1. Locate the "Version manager — update CHANGELOG" section
2. Comment out the entire section (all 29 lines)
3. Keep the comment explaining WHY it's disabled

**Rationale:**
- version-manager contradicts CI/CD-driven workflow
- Developers shouldn't maintain [Unreleased] sections
- Git tags are source of truth

## Phase 2: Clean CHANGELOG.md

**File:** `CHANGELOG.md`

**What to do:**
1. Remove all `## [Unreleased]` sections
2. Keep only released versions (## [v0.34.0], ## [v0.33.3], etc.)
3. Remove empty sections (no ### subsections without content)

**Example:**
```markdown
# Changelog

## [v0.34.0] - 2026-05-24

### Added
- File-sync skill: analyze repository scripts for utility
...

## [v0.33.3] - 2026-05-24
...
```

## Phase 3: Update VERSIONING.md

**File:** `VERSIONING.md`

**What to add:**
1. New section: "Why No [Unreleased] Section"
2. Explain: CI/CD-driven versioning doesn't need [Unreleased] tracking
3. Note: version-manager was designed for different workflow
4. Clarify: Git tags are single source of truth

## Phase 4: Verification

**Test that fix works:**
1. Make a test commit: `git commit -m "test: verify version-manager disabled"`
2. Check that pre-commit hook runs (other checks still work)
3. Verify CHANGELOG.md is NOT modified/staged
4. Verify no [Unreleased] appears in CHANGELOG

**Success indicators:**
- ✅ Pre-commit hook completes successfully
- ✅ CHANGELOG is NOT auto-updated
- ✅ No new [Unreleased] entries
- ✅ CHANGELOG remains clean

## Files to Change

1. `.githooks/pre-commit` - Comment out version-manager section
2. `CHANGELOG.md` - Remove [Unreleased] entries
3. `VERSIONING.md` - Document the decision

## Rollback Plan

If something goes wrong:
1. Restore `.githooks/pre-commit` from git history
2. Restore `CHANGELOG.md` from git history
3. Revert `VERSIONING.md` changes

## Timeline

- Phase 1: 5 minutes (edit pre-commit hook)
- Phase 2: 5 minutes (clean CHANGELOG)
- Phase 3: 5 minutes (update docs)
- Phase 4: 5 minutes (verify)
- **Total: 20 minutes**

---

## Decision Log

**Why disable rather than fix version-manager?**
- version-manager is designed for local version workflows
- Project uses CI/CD-driven workflow (different paradigm)
- Fixing version-manager would add complexity without matching workflow
- Disabling is simpler, aligns with actual process, is durable

**Why not remove version-manager entirely?**
- Skill might be useful for future CI/CD enhancements
- Keep it in codebase for reference
- Just disable auto-run on commits

**Why keep version-manager skill around?**
- May be useful in future if workflow changes
- Doesn't hurt to keep (disabled)
- Provides reference implementation for similar projects
