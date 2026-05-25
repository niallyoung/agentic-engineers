---
title: "version-manager"
description: "Semantic versioning workflow: calculate next version, manage release cadence via git hooks (currently disabled in favor of CI/CD-driven versioning)"
role: "Security Engineer"
model: "claude-haiku-4-5"
effort: "medium"
status: "disabled"
version: "1.0.0"
---

# version-manager Skill

**Purpose:** Implement semantic versioning as a local workflow, calculating next versions based on outstanding commits.

**Status:** ⚠️ DISABLED - CI/CD-driven versioning is used instead (git tags are source of truth)

---

## Overview

The `version-manager` skill provides:

1. **Semantic Version Calculation**
   - Parses commits since last git tag
   - Determines major/minor/patch bumps using conventional commits
   - Calculates next projected version

2. **Local Workflow Integration**
   - Manual invocation via `scripts/version-manager/update-changelog.py`
   - No CI/CD dependency — works locally before push

**Note:** This skill was designed for local versioning workflows but is currently **disabled** in favor of CI/CD-driven semantic versioning. The project uses `mathieudutour/github-tag-action` to automatically create git tags from commit messages. The skill is retained for reference and potential future use cases.

---

## Architecture

### Components

```
skills/version-manager/
├── SKILL.md                    # This file
├── __init__.py                 # Python package init
├── version_calculator.py       # Core: semantic version calculation
├── changelog_updater.py        # Core: CHANGELOG [Unreleased] management
└── scripts/
    └── update-changelog.py     # CLI wrapper for manual invocation

.githooks/
└── pre-commit                  # Git hook that runs version updates

.github/workflows/
└── ci.yml                      # (MODIFIED) Tag/release only, no version generation
```

### Data Flow (DISABLED)

**Historical workflow (no longer active):**
```
git commit -m "feat: ..."
    ↓
(pre-commit hook was disabled)
    ↓
version_calculator.py could calculate next version
    ↓
Manual invocation only
```

**Current CI/CD workflow:**
```
git commit → push to main → CI/CD analyzes commits → git tag created
```

---

## Key Functions

### version_calculator.py

**`parse_commit_type(message: str) -> Tuple[str, bool]`**
- Parse commit message for semantic type
- Returns: (type, is_breaking)
- Supports: feat, fix, refactor, chore, docs, style, test, perf, other
- Detects: BREAKING CHANGE marker

**`get_commits_since_tag() -> List[Tuple[str, str, str]]`**
- Get all commits since last git tag
- Returns: [(commit_hash, author_date, message)]
- Falls back to all commits if no tags exist

**`calculate_next_version(commits) -> str`**
- Determine semantic version bump
- Logic:
  - If any BREAKING CHANGE: major bump
  - Else if any feat: minor bump
  - Else if any fix: patch bump
  - Else: no bump (patch if releasing)
- Returns: next version (e.g., "0.8.2")

**`get_current_version() -> str`**
- Wrapper around scripts/get_version.py
- Returns: latest git tag or fallback

### changelog_updater.py (DISABLED)

**Note:** CHANGELOG update functionality is disabled in favor of CI/CD-driven versioning. Functions are retained for reference only.

**`update_changelog_unreleased(next_version: str, commits: List)`** - DISABLED
- Historical function for CHANGELOG updates
- No longer used in active workflow

**`generate_unreleased_section(version: str, commits: List) -> str`** - DISABLED
- Historical function for section generation
- No longer used in active workflow

---

## Git Hook Integration

### `.githooks/pre-commit`

**Status: DISABLED**

The version-manager pre-commit hook has been **disabled** to align with CI/CD-driven semantic versioning.

**Why disabled:**
- Project uses CI/CD to automatically create git tags from commit messages
- Git tags are the authoritative version source
- CHANGELOG is documentation, not source of truth
- No need for automatic CHANGELOG updates on every commit

**Historical behavior (no longer active):**
```bash
# This section is commented out in .githooks/pre-commit
# python3 scripts/version-manager/update-changelog.py --auto
# git add CHANGELOG.md
```

---

## Manual Invocation (Reference Only)

**Note:** These commands are available but **not recommended** for active use. CI/CD handles versioning automatically.

### CLI: Version Calculation (if needed)

```bash
# Calculate next version without updating CHANGELOG
python3 scripts/version-manager/update-changelog.py --dry-run

# Get current version from git tags
python3 scripts/get_version.py
```

### In Code (Reference)

```python
from skills.version_manager import version_calculator

# Get next version (for reference)
next_version = version_calculator.calculate_next_version_from_commits()

# Note: CHANGELOG update functions are disabled
```

---

## Acceptance Criteria (Historical)

**Original implementation (now disabled):**
- ✅ SKILL.md created with proper frontmatter
- ✅ Version calculation works with conventional commits
- ✅ Tests pass (TDD Red→Green→Refactor)
- ✅ Can calculate versions locally without CI/CD dependency

**Current status:**
- ✅ Disabled in favor of CI/CD-driven versioning
- ✅ Git tags are source of truth
- ✅ CHANGELOG uses direct versioned entries only

---

## Testing Strategy (TDD - Historical)

**Original TDD approach (when feature was active):**

### Phase 1: Red (Failing Test)
- Test checked for version calculation

### Phase 2: Green (Minimal Implementation)
- Implemented version calculation
- Tests passed

### Phase 3: Refactor
- Optimized for edge cases
- Added comprehensive commit parsing
- Enhanced error handling

**Current testing:** Tests verify version calculation functionality only (CHANGELOG update tests are deprecated).

---

## CICD Integration

### Current Changes to `.github/workflows/ci.yml`

**Before:**
- Workflow creates git tag (via mathieudutour/github-tag-action)
- Workflow creates GitHub Release

**After:**
- ✅ Same: creates git tag
- ✅ Same: creates GitHub Release
- ❌ Removed: version generation step
- ❌ Removed: VERSION file update

**Why:**
- Local version-manager provides version source of truth
- CICD consumes versioning from git tags + CHANGELOG
- Enables local-first development workflow

---

## Handling Edge Cases

### No Tags Exist
- Scripts fall back to calculating from commit 0
- Generates complete changelog from all commits
- Uses hardcoded v0.8.0 as baseline

### No Commits Since Tag
- Version remains current
- No changes needed

### Mixed Commit Types
- If has both feat and fix: minor bump (feat > fix)
- If has BREAKING CHANGE: major bump
- Correctly prioritizes breaking > feature > fix

### Empty Repository
- Gracefully handles zero commits
- Returns fallback version

---

## Future Enhancements

- [ ] Publish to PyPI automatically on release tags
- [ ] Generate release notes from CHANGELOG
- [ ] Support release branch workflows
- [ ] Add changelog validation to CI/CD
- [ ] Integrate with GitHub Releases API
- [ ] Support monorepo version management

---

## References

- [Semantic Versioning 2.0.0](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- Parent: agentic-engineers versioning infrastructure
- Related: `scripts/get_version.py`, `scripts/generate_semantic_changelog.py`

---

## Troubleshooting

### Git hook not running
```bash
# Enable hooks
git config core.hooksPath .githooks

# Copy hooks to .git/hooks
cp .githooks/* .git/hooks/
chmod +x .git/hooks/*
```

### Version not updating
```bash
# Force update
python3 scripts/version-manager/update-changelog.py --force

# Check current version
python3 scripts/get_version.py

# View commits since tag
git log v0.8.1..HEAD --oneline
```

### CHANGELOG format incorrect
```bash
# Validate CHANGELOG
python3 -c "import yaml; print(open('CHANGELOG.md').read()[:500])"

# Regenerate (careful: use --force)
python3 scripts/version-manager/update-changelog.py --force
```

---

## Implementation Status

| Component | Status | Tests |
|-----------|--------|-------|
| version_calculator.py | ✅ Done | ✅ 8 tests |
| changelog_updater.py | ✅ Done | ✅ 6 tests |
| update-changelog.py CLI | ✅ Done | ✅ 4 tests |
| pre-commit hook | ✅ Done | ✅ Integration test |
| CI/CD removal | ✅ Done | ✅ Verified |

---

## Notes for Maintainers

### When Releasing
1. Ensure all commits have proper conventional commit format (feat:, fix:, etc.)
2. Push to main branch
3. CI/CD Quality Gate runs (lint, test, verify)
4. If Quality Gate passes, CI/CD automatically:
   - Analyzes commits since last tag
   - Creates new git tag (e.g., v0.35.0)
   - Creates GitHub Release with notes
5. CHANGELOG can be updated manually later (optional documentation step)

### When Adding Features
- Commit with proper conventional commit messages
- CI/CD handles versioning automatically
- No manual version management needed

### When Debugging
- Check CHANGELOG.md format: sections, dates, versions
- Verify git tags: `git tag -l v* --sort=-version:refname`
- Test version calculation: `python3 -m pytest tests/test_version_manager.py -v`

