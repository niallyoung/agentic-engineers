# CHANGELOG [Unreleased] Issue - Root Cause Analysis & Fix Plan

## PROBLEM STATEMENT

The CHANGELOG.md has a persistent `## [Unreleased] - v0.35.0` section that:
- Keeps reappearing after manual deletion attempts
- Blocks PR merge workflow
- Is injected on every commit by the `version-manager` pre-commit hook
- Contradicts the project's actual versioning strategy

## ROOT CAUSE ANALYSIS

### The Design Mismatch

**Version-Manager Design (Local Workflow):**
- Maintains `[Unreleased]` section in CHANGELOG on EVERY commit via pre-commit hook
- Intended for projects where developers manually manage version numbers
- Accumulates commits into [Unreleased] until a manual release is made
- Example: dev writes [Unreleased] section → developer tags release → [Unreleased] becomes v0.35.0

**Project's Actual Versioning (CI/CD-Driven):**
- Git tags are created automatically by CI/CD pipeline (`.github/workflows/ci.yml`)
- Semantic version calculated from commits by `mathieudutour/github-tag-action`
- GitHub Release created automatically from tags
- Version source of truth = git tags (not CHANGELOG)
- No manual versioning needed by developers

**The Conflict:**
```
Developer commits → pre-commit hook runs version-manager
                 → version-manager adds [Unreleased] to CHANGELOG
                 → CHANGELOG is now out of sync with git-driven workflow
                 → Git tag created later by CI/CD (different version)
                 → Mismatch between CHANGELOG [Unreleased] and actual git tags
```

### Why Previous Fixes Failed

Multiple commits tried to "fix" this by manually editing CHANGELOG:
- `fix(changelog): remove version from [Unreleased]` (commit 9975d9e)
- `fix(changelog): repair versioning sync corruption` (commit 9d7170a)
- etc.

These were all **symptom fixes, not root cause fixes**. On the next `git commit`, the pre-commit hook would re-run `version-manager` and re-inject `[Unreleased]`.

### Evidence

1. **VERSIONING.md explicitly states:**
   - "Git tags are the primary and only source of truth"
   - "No manual VERSION file to maintain — everything is automatic"
   - "CI/CD calculates version, creates tag, creates release"

2. **Pre-commit hook explicitly runs version-manager:**
   ```bash
   # From .githooks/pre-commit (lines ~470+)
   if [ ! -f ".git/hooks/skip-version-manager" ] && command -v python3 >/dev/null 2>&1; then
     python3 "$REPO_ROOT_VERSION/skills/version-manager/scripts/update-changelog.py" --auto
     if git diff --name-only | grep -q "^CHANGELOG.md$"; then
       git add CHANGELOG.md
     fi
   fi
   ```

3. **Version-manager design purpose:**
   - From SKILL.md: "maintains [Unreleased] sections in CHANGELOG"
   - "Updates on every commit via git hook"
   - But this contradicts the actual CI/CD workflow

## CORRECT SOLUTION

**The project should NOT auto-update CHANGELOG on every commit.**

Why:
1. Git tags are the authoritative version source
2. CHANGELOG is just documentation of what was released
3. Developers shouldn't maintain [Unreleased] sections
4. Version-manager was designed for a different workflow

## FIX OPTIONS

### Option A: DISABLE version-manager pre-commit hook (RECOMMENDED)
- Remove the version-manager invocation from `.githooks/pre-commit`
- Keep version-manager available for manual use if needed (future CI/CD)
- Clean CHANGELOG (remove [Unreleased] sections)
- Simple, minimal change, aligns with actual workflow
- **Impact:** Zero manual versioning burden on developers

### Option B: Remove version-manager entirely
- Delete `src/skills/version-manager/` and `skills/version-manager/`
- Remove from pre-commit hook
- Simpler but loses potential future CI/CD integration
- **Impact:** Same as A, but loses optional future tool

### Option C: Modify version-manager to NOT run in pre-commit
- Comment out the pre-commit hook invocation
- Keep skill for manual/future use
- **Impact:** Same as A, but keeps skill in place

### Option D: Fix version-manager to generate proper versions
- Change to generate `v0.35.0` sections instead of `[Unreleased]`
- Still doesn't match workflow since git tags are source of truth
- Adds complexity without solving core issue
- **NOT RECOMMENDED**

## RECOMMENDED FIX: Option A

**Steps:**
1. Remove version-manager invocation from `.githooks/pre-commit`
2. Clean CHANGELOG: remove all `[Unreleased]` sections
3. Keep CHANGELOG with only released versions (v0.34.0, v0.33.3, etc.)
4. Document the decision in VERSIONING.md

**Why this works:**
- ✅ Stops [Unreleased] from reappearing on every commit
- ✅ Aligns with actual CI/CD-driven workflow
- ✅ No manual versioning work for developers
- ✅ CHANGELOG stays clean
- ✅ Git tags remain single source of truth
- ✅ Durable fix: won't regress on next merge

**What happens after:**
- Developers commit normally (pre-commit hook runs, but no version-manager)
- CI/CD detects commits, creates git tags
- CHANGELOG stays in current state until manually updated (optional)
- No sync issues because CHANGELOG is just documentation, not source of truth

## IMPLEMENTATION PLAN

### Phase 1: Disable version-manager in pre-commit hook
**File:** `.githooks/pre-commit` (lines 468-493)
- Comment out the version-manager section
- Keep other pre-commit checks (secrets, YAML validation, etc.)

### Phase 2: Clean CHANGELOG
**File:** `CHANGELOG.md`
- Remove all `[Unreleased]` sections
- Keep only released versions (v0.34.0, v0.33.3, etc.)
- Keep format consistent

### Phase 3: Document the decision
**File:** `VERSIONING.md`
- Add section explaining why [Unreleased] is NOT used
- Explain CI/CD-driven workflow
- Note that git tags are source of truth

### Phase 4: Verify
- Make a test commit
- Verify pre-commit hook runs but does NOT update CHANGELOG
- Verify CHANGELOG stays clean

## SUCCESS CRITERIA

✅ No [Unreleased] entries in CHANGELOG
✅ Version-manager not invoked on every commit
✅ Pre-commit hook still works (other checks still run)
✅ Test commit verifies CHANGELOG NOT auto-updated
✅ Documentation updated explaining the design
✅ Fix is durable (won't regress on next PR merge)

## TIMELINE

- Phase 1-2: 10 minutes (edit files)
- Phase 3: 5 minutes (documentation)
- Phase 4: 5 minutes (test)
- **Total: ~20 minutes**

---

## APPENDIX: Why version-manager exists

Version-manager was designed for projects using a **local versioning workflow**:
```
Dev commits feat → Manual: tag as v0.35.0 → Manual: update CHANGELOG
                 ↓
            [Unreleased] section accumulates commits
                 ↓
            When ready to release: move [Unreleased] to v0.35.0
```

But this project uses a **CI/CD-driven workflow**:
```
Dev commits feat → CI/CD: auto-detects version bump → CI/CD: creates tag
                 ↓
         Git tag is the release (immutable, authoritative)
                 ↓
     CI/CD: creates GitHub Release (automatic)
```

These workflows are incompatible. The project chose CI/CD-driven (correct choice), so version-manager shouldn't run automatically.
