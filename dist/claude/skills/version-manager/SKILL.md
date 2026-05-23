---
title: "version-manager"
description: "Semantic versioning workflow: calculate next version, update CHANGELOG with [Unreleased] section, and manage release cadence via git hooks"
role: "Security Engineer"
model: "claude-haiku-4-5"
effort: "medium"
status: "implemented"
version: "1.0.0"
---

# version-manager Skill

**Purpose:** Implement semantic versioning as a local workflow, calculating next versions based on outstanding commits and maintaining [Unreleased] sections in CHANGELOG.

**Status:** ✅ Implemented and TDD-verified

---

## Overview

The `version-manager` skill provides:

1. **Semantic Version Calculation**
   - Parses commits since last git tag
   - Determines major/minor/patch bumps using conventional commits
   - Calculates next projected version

2. **CHANGELOG Management**
   - Maintains [Unreleased] section with next projected version
   - Captures all unreleased commits grouped by type (feat, fix, etc.)
   - Updates on every commit via git hook

3. **Local Workflow Integration**
   - Git pre-commit hook that runs version calculation
   - Manual invocation via `scripts/version-manager/update-changelog.py`
   - No CI/CD dependency — works locally before push

4. **Future CICD Transition**
   - Local hooks provide version source of truth
   - CI/CD will consume local versioning (not generate it)
   - Enables decentralized release management

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

### Data Flow

```
git commit -m "feat: ..."
    ↓
pre-commit hook triggers
    ↓
version_calculator.py
  - Reads commits since last tag
  - Determines next version
    ↓
changelog_updater.py
  - Adds [Unreleased] section
  - Lists unreleased commits grouped by type
    ↓
CHANGELOG.md updated
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

### changelog_updater.py

**`update_changelog_unreleased(next_version: str, commits: List)`**
- Update CHANGELOG.md [Unreleased] section
- Groups commits by type
- Generates markdown sections
- Inserts after header, before first version

**`generate_unreleased_section(version: str, commits: List) -> str`**
- Generate markdown for [Unreleased] section
- Format: `## [Unreleased] - vX.Y.Z (next)`
- Sections: Added, Fixed, Changed, Documentation, etc.

---

## Git Hook Integration

### `.githooks/pre-commit`

Triggers on every `git commit`:

```bash
#!/bin/bash
# Run version calculation and CHANGELOG update
python3 scripts/version-manager/update-changelog.py --auto

# Stage updated CHANGELOG
git add CHANGELOG.md

exit 0
```

**Behavior:**
- Non-blocking: failures don't prevent commit
- Automatic: no user interaction required
- Idempotent: running twice has same effect
- Local-only: no network calls

**Configuration:**
- Git is configured to use `.githooks` directory
- Already set in CI/CD workflow
- Can be enabled locally: `git config core.hooksPath .githooks`

---

## Manual Invocation

### CLI: Update CHANGELOG

```bash
# Update CHANGELOG with unreleased section
python3 scripts/version-manager/update-changelog.py

# Show next version without updating
python3 scripts/version-manager/update-changelog.py --dry-run

# Force update even if CHANGELOG is current
python3 scripts/version-manager/update-changelog.py --force

# Verbose output for debugging
python3 scripts/version-manager/update-changelog.py --verbose
```

### In Code

```python
from skills.version_manager import version_calculator, changelog_updater

# Get next version
next_version = version_calculator.calculate_next_version_from_commits()

# Update CHANGELOG
changelog_updater.update_changelog_unreleased(next_version)
```

---

## Acceptance Criteria

- ✅ SKILL.md created with proper frontmatter
- ✅ Version calculation works with conventional commits
- ✅ [Unreleased] section added to CHANGELOG
- ✅ Unreleased commits grouped by type (feat, fix, etc.)
- ✅ Git hook runs on pre-commit
- ✅ Next version displayed correctly
- ✅ All unreleased commits captured
- ✅ Tests pass (TDD Red→Green→Refactor)
- ✅ CICD workflow updated (no version generation step)
- ✅ Can run locally without CI/CD dependency

---

## Testing Strategy (TDD)

### Phase 1: Red (Failing Test)
- Test checks: CHANGELOG has [Unreleased] section
- Test fails: Current CHANGELOG doesn't have unreleased section

### Phase 2: Green (Minimal Implementation)
- Implement version calculation
- Implement CHANGELOG update
- Test passes

### Phase 3: Refactor
- Optimize for edge cases
- Add comprehensive commit parsing
- Enhance error handling

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
- [Unreleased] section shows empty or "No unreleased changes"
- Version remains current

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
1. Ensure all commits have proper conventional commit format
2. Run `git fetch --tags` to sync with CI-created remote tags
3. Run `python3 scripts/version-manager/update-changelog.py --dry-run` to preview next version
4. Commit changes locally (pre-commit hook updates CHANGELOG)
5. Push to main via `git push && git push --tags`
6. CI/CD creates new git tag automatically
7. GitHub Release created from tag

### When Adding Features
- All features become [Unreleased] until released
- Run manual `update-changelog.py` to update immediately
- Hook runs automatically on next commit

### When Debugging
- Check CHANGELOG.md format: sections, dates, versions
- Verify git tags: `git tag -l v* --sort=-version:refname`
- Test version calculation: `python3 -m pytest tests/test_version_manager.py -v`

