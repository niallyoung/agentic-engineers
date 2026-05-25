# CHANGELOG [Unreleased] Investigation & Fix Summary

**Status:** ✅ COMPLETE - Issue fixed and verified

**Timeline:** Single session investigation and implementation

---

## Executive Summary

The CHANGELOG had persistent `[Unreleased] - v0.35.0` entries that:
- Kept reappearing after manual deletion attempts
- Blocked PR merge workflow 
- Were being auto-injected by `version-manager` on every commit

**Root Cause:** Fundamental design mismatch between version-manager (designed for local versioning workflows) and the project's actual CI/CD-driven semantic versioning system.

**Solution:** Disabled version-manager auto-update on commits. Git tags (created automatically by CI/CD) are now the only version source of truth.

**Result:** Clean CHANGELOG with only released versions. Durable fix that won't regress.

---

## Deep Investigation

### What the Code Was Doing

1. **`version-manager` skill** (`src/skills/version-manager/`)
   - Designed to maintain `[Unreleased]` sections in CHANGELOG
   - Tracks unreleased commits for upcoming release
   - Runs automatically via pre-commit hook on EVERY commit

2. **Pre-commit hook invocation** (`.githooks/pre-commit` lines 219-255)
   ```bash
   python3 $REPO_ROOT/skills/version-manager/scripts/update-changelog.py --auto
   git add CHANGELOG.md  # Auto-stage CHANGELOG changes
   ```

3. **Result of auto-update:**
   - Every commit → pre-commit hook triggers → CHANGELOG updated with [Unreleased]
   - Developers see: `[Unreleased] - v0.35.0` (projected next version)
   - Creates endless cycle of "remove [Unreleased]" commits

### Why This Was Wrong

**Project's Versioning Strategy (per VERSIONING.md):**
```
Local Code Commits → CI/CD Pipeline → Auto-creates git tags
                                    ↓
                    Tag = authoritative version (v0.34.0)
                                    ↓
                    GitHub Release created automatically
```

**version-manager Expected Strategy:**
```
Local Commits → Dev maintains [Unreleased] → Dev creates release tag manually
              ↓
        [Unreleased] becomes v0.35.0 (manual step)
```

**The Conflict:**
- Project: "We don't care about version numbers; CI/CD creates tags automatically"
- version-manager: "Let me maintain version numbers in CHANGELOG automatically"
- Result: Version-manager data (CHANGELOG [Unreleased]) ≠ actual versions (git tags)

### Why Previous Fixes Failed

**Attempted Fixes (from git history):**
1. `fix(changelog): remove version from [Unreleased]` — Commit 9975d9e
2. `fix(changelog): remove version number from [Unreleased]` — Commit 0cf19a6
3. `fix(changelog): repair versioning sync corruption` — Commit 9d7170a
4. Multiple other manual edits

**Why They Failed:**
- All were manual edits to CHANGELOG
- Pre-commit hook still active
- Next commit would re-trigger version-manager
- Re-inject [Unreleased]
- Cycle repeats infinitely

---

## The Fix (4 Phases)

### Phase 1: Disable version-manager in pre-commit hook

**File:** `.githooks/pre-commit` (lines 219-255)

**Changed:**
```bash
# FROM: Active version-manager invocation
if [ ! -f ".git/hooks/skip-version-manager" ] && command -v python3 >/dev/null 2>&1; then
  python3 "$REPO_ROOT_VERSION/skills/version-manager/scripts/update-changelog.py" --auto
  ...
fi

# TO: Commented out with documentation
# ─── Section: Version manager — DISABLED (CI/CD-driven versioning) ──────────────
# 
# NOTE: version-manager is DISABLED for the following reasons:
# 1. VERSIONING STRATEGY: Project uses CI/CD-driven semantic versioning
# 2. DESIGN MISMATCH: version-manager designed for LOCAL versioning workflows
# 3. SOLUTION: Keep CHANGELOG clean (only released versions)
#
# if [ ! -f ".git/hooks/skip-version-manager" ] && command -v python3 >/dev/null 2>&1; then
#   ...
# fi
```

**Result:** version-manager no longer runs on every commit

### Phase 2: Clean CHANGELOG

**File:** `CHANGELOG.md`

**Removed:**
- `## [Unreleased] - v0.35.0` section (with 12 sub-items)
- Blank lines at top

**Kept:**
- `## [v0.34.0] - 2026-05-24` (and all released versions)
- All content organized by actual releases
- Consistent markdown formatting

**Result:** CHANGELOG shows only released versions (v0.34.0, v0.33.3, v0.33.2, etc.)

### Phase 3: Document the decision

**Files Modified:**
- `VERSIONING.md` — Added section: "Why No [Unreleased] Sections in CHANGELOG?"
- `CHANGELOG-FIX-PLAN.md` — Created with detailed root cause analysis

**Documentation explains:**
- Why CI/CD-driven versioning doesn't need [Unreleased] sections
- Why version-manager was designed for a different workflow
- What the correct approach is (git tags as source of truth)
- Prevents confusion in future

### Phase 4: Verify the fix

**Test Commit:** `c4bd850`
```
Message: fix(changelog): disable auto-update for CI/CD versioning
Commit: Made after implementing all changes
```

**Verification Results:**
1. ✅ Pre-commit hook ran (other checks passed)
2. ✅ NO "version-manager: Updated CHANGELOG" message
3. ✅ CHANGELOG was NOT auto-updated
4. ✅ CHANGELOG remains clean (no [Unreleased])

---

## Why This Fix is Durable

**Not a symptom fix:**
- ✅ Addresses root cause (design mismatch), not symptom ([Unreleased] entries)

**Will not regress:**
- ✅ Pre-commit hook disabled at source (not dependent on skip-flags)
- ✅ Works on all branches (feature, main, etc.)
- ✅ Not dependent on environment variables or configuration

**Won't break other workflows:**
- ✅ Other pre-commit checks still active (secrets, YAML, formatting)
- ✅ CI/CD workflow unchanged (still creates tags automatically)
- ✅ version-manager skill kept for future reference/manual use

**Can be verified on every future commit:**
```bash
# On any commit after fix:
git commit -m "test: verify version-manager disabled"
# Should see: "✅ pre-commit: all checks passed" (NO version-manager message)
# CHANGELOG should NOT be modified
```

---

## Files Changed

| File | Change | Reason |
|------|--------|--------|
| `.githooks/pre-commit` | Commented out version-manager (29 lines) | Disable auto-update |
| `CHANGELOG.md` | Removed [Unreleased] section | Clean state |
| `VERSIONING.md` | Added explanation section | Document decision |
| `CHANGELOG-FIX-PLAN.md` | Created new file | Detailed analysis |

---

## Impact on Developers

**What stays the same:**
- ✅ Normal commit workflow unchanged
- ✅ Version numbers still automatic (via CI/CD)
- ✅ Pre-commit hook still validates code

**What improves:**
- ✅ CHANGELOG no longer blocks merges
- ✅ No more "remove [Unreleased]" commit cycles
- ✅ Clean, consistent CHANGELOG

**What's different:**
- ❌ CHANGELOG no longer auto-updates on commits (not needed)
- ✅ CHANGELOG can be updated manually before releases (optional)

---

## References

### Design Rationale
- `CHANGELOG-FIX-PLAN.md` — Root cause analysis and options considered
- `VERSIONING.md` — Project's semantic versioning strategy

### Implementation Details
- `.githooks/pre-commit` — See lines 219-281 (version-manager section, commented with explanation)
- `CHANGELOG.md` — See line 1-50 (clean release history format)

### Related Code
- `src/skills/version-manager/` — Skill code (kept for reference, now disabled)
- `.github/workflows/ci.yml` — CI/CD pipeline (unchanged, still creates tags)

---

## Conclusion

The [Unreleased] issue was caused by a fundamental mismatch between:
- **version-manager** (designed for manual local versioning)
- **Project's workflow** (fully automated CI/CD versioning)

The fix disables version-manager auto-run while keeping the code and skill available. This aligns the tooling with the actual workflow and prevents the [Unreleased] entries from reappearing.

**The fix is:**
- ✅ Complete (all phases done)
- ✅ Verified (test commit confirms it works)
- ✅ Durable (won't regress)
- ✅ Documented (future maintainers understand why)
- ✅ Reversible (can be reverted if needed)

