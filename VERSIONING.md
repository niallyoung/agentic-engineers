# Semantic Versioning Strategy

## Overview

This project follows **Semantic Versioning 2.0.0** (`major.minor.patch`).

- **Initial Release:** `v0.8.0` (baseline)
- **Next Releases:** `v0.8.1`, `v0.8.2`, etc. (patch bumps)
- **Future:** `v0.9.0` (minor bump), `v1.0.0` (major bump)

## Version Management

### Automatic Semantic Versioning

The CI/CD pipeline (`.github/workflows/ci.yml`) automatically:

1. **Detects version changes** from commit messages (follows Conventional Commits)
   - `fix:` → patch version bump (v0.8.0 → v0.8.1)
   - `feat:` → minor version bump (v0.8.0 → v0.9.0)
   - `BREAKING CHANGE:` → major version bump (v0.8.0 → v1.0.0)

2. **Creates Git Tag** using `mathieudutour/github-tag-action`
   - Reads commit history since last tag
   - Calculates next version
   - Pushes tag to repository
   - Starts at `v0.8.0` if no tags exist

3. **Creates GitHub Release** using `ncipollo/release-action`
   - Generates release notes with changelog
   - Attaches tag
   - Makes release publicly visible

4. **Git tags are the primary and only source of truth**
   - `setup.py` reads version from git tags (via `get_version.py`)
   - No manual VERSION file to maintain — everything is automatic
   - This eliminates sync issues by making tags the authoritative version

### Files Involved

- **Git tags** — Primary version source (created automatically by CI/CD)
- **.github/workflows/ci.yml** — Automatic tagging and release
- **scripts/get_version.py** — Version utility (read/bump versions)

### Why No [Unreleased] Sections in CHANGELOG?

The CHANGELOG does NOT contain `[Unreleased]` sections because:

1. **Git tags are the source of truth** - Versions are determined by CI/CD from commit messages, not by manual CHANGELOG entries
2. **No developer versioning burden** - Developers don't maintain version numbers; they just commit code
3. **Incompatible workflow** - `[Unreleased]` sections are designed for local versioning workflows (manual releases), not CI/CD-driven workflows (automatic releases)
4. **Single source of truth** - Git tags (created by CI/CD) are the authoritative version; CHANGELOG is just documentation

**Example:**
- ❌ WRONG: Developer manually maintains `## [Unreleased] - v0.35.0` in CHANGELOG, then CI/CD creates the tag
- ✅ RIGHT: CI/CD creates git tag `v0.35.0` from commits; CHANGELOG is updated manually later (optional) as release notes documentation

See `CHANGELOG-FIX-PLAN.md` for detailed analysis of why `version-manager` pre-commit hook was disabled.

### How Versioning Works

#### 1. Local Development
- Write code with conventional commit messages:
  ```bash
  git commit -m "fix: resolve issue with X"  # Will bump patch
  git commit -m "feat: add new feature Y"    # Will bump minor
  git commit -m "fix!: breaking change"      # Will bump major
  ```

#### 2. CI/CD Automation
- Push to `main` branch → Quality Gate runs
- Quality Gate passes → Tag Release job runs
- Tag Release job:
  - Reads commit messages since last tag
  - Calculates new version
  - Creates tag (e.g., `v0.8.1`)
  - Creates GitHub Release with changelog
  - Pushes all to repository

#### 3. Version Source Priority
- **Primary & Only Source:** Git tags (authoritative, read by `setup.py` via `get_version.py`)
- **Last resort:** Hardcoded fallback (0.8.0) — for offline/no-git scenarios only

**Note:** The VERSION file has been removed as it was stale and unnecessary. Git tags are the single source of truth. The hardcoded "0.8.0" fallback ensures installations work even without git history (e.g., distributions, shallow clones).

### Reading Current Version

```bash
# Use the utility script to get version from git tags
python3 scripts/get_version.py

# Get next patch version
python3 scripts/get_version.py next-patch

# Get next minor version
python3 scripts/get_version.py next-minor
```

### Important Notes

- **Conventional Commits Required:** Use proper commit message format for automatic versioning
- **Only main branch triggers release:** Tags are only created from `main` branch
- **Quality gate must pass:** CI/CD lint, test, and verify jobs must pass before tagging
- **Immutable tags:** Once tagged, a version is immutable
- **Fast-forward merges recommended:** Keeps history clean for semantic versioning

## Version History

| Version | Date | Notes |
|---------|------|-------|
| v0.8.0 | 2026-05-23 | Initial release baseline |
| v0.8.1+ | TBD | Patch fixes (automatic) |
| v0.9.0 | TBD | New features (automatic) |
| v1.0.0 | TBD | Breaking changes / Major release |

## Rollback Procedure

If a release needs to be rolled back:

1. Delete the GitHub Release in the UI
2. Delete the Git tag: `git push --delete origin v0.8.1`
3. Fix the code
4. Create new commit on `main`
5. Let CI/CD create new tag automatically

---

## References

- [Semantic Versioning 2.0.0](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [mathieudutour/github-tag-action](https://github.com/mathieudutour/github-tag-action)
- [ncipollo/release-action](https://github.com/ncipollo/release-action)
