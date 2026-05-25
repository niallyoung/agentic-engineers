# Security Threat Analysis: Version-Manager & CHANGELOG Workflow

**STATUS: ✅ RESOLVED & DELETED - Removed entirely (2026-05-25)**

**Resolution:** version-manager skill deleted entirely from src/skills/. All rendered artifacts deleted from dist/*/skills/. CHANGELOG now uses direct versioned entries only. CI/CD-driven semantic versioning enforced via git tags.

---

## Historical Analysis (Original Security Audit)

## Executive Summary

The `version-manager` skill has **fundamental architectural flaws** that make it unsuitable for production use:

1. **Integrity Risk (CRITICAL)**: Git hooks can be bypassed entirely (no enforcement mechanism)
2. **Design Flaw (HIGH)**: `[Unreleased]` is semantically incoherent and causes merge conflicts
3. **Automation Risk (HIGH)**: Auto-updating CHANGELOG on every commit introduces noise and race conditions
4. **Source of Truth Conflict (CRITICAL)**: CHANGELOG vs. git tags creates authoritative confusion

The `[Unreleased]` keeps reappearing because the workflow was **fundamentally mis-designed** — it attempts to solve a local version management problem using a CI/CD-style approach that git hooks cannot reliably enforce.

---

## 1. INTEGRITY RISKS: GIT HOOKS & BYPASS VECTORS

### 1.1 Git Hook Bypass Mechanisms

**Status**: ✅ BYPASSES EXIST AND ARE TRIVIAL

```bash
# Method 1: Skip hooks entirely
git commit --no-verify -m "fix: bypass pre-commit"

# Method 2: Force push (overwrites hook-generated commits)
git push --force-with-lease

# Method 3: Direct file edit (avoid commit)
nano CHANGELOG.md && git add CHANGELOG.md && git commit --no-verify

# Method 4: Partial stage + amend
git commit --no-verify && git add CHANGELOG.md && git commit --amend --no-edit

# Method 5: Delete .git/hooks
rm -rf .git/hooks && git commit

# Method 6: Clone without hooks
git clone --no-checkout ... && git config core.hooksPath /dev/null
```

**Why this matters**: The pre-commit hook that updates CHANGELOG.md has NO enforcement. Users are expected to:
- Trust that hooks are installed (`core.hooksPath .githooks`)
- Never use `--no-verify`
- Never force-push
- Never edit CHANGELOG directly

All of these are **social contracts**, not technical enforcement.

### 1.2 CHANGELOG.md Corruption Scenarios

**Race Condition Risk: MODERATE**

If two commits happen in quick succession:

```
Process 1: git commit -m "feat: A"
  ├─ pre-commit hook runs
  │  ├─ reads CHANGELOG.md (state: [Unreleased] - v0.8.0)
  │  ├─ calculates commits since tag → sees ["feat: A"]
  │  └─ writes [Unreleased] - v0.9.0 with "feat: A"
  
Process 2: git commit -m "feat: B"  # Starts before Process 1 finishes writing
  ├─ pre-commit hook runs
  │  ├─ reads CHANGELOG.md (state: old cache — still has "feat: A" only)
  │  ├─ calculates commits since tag → sees ["feat: A", "feat: B"]  
  │  └─ writes [Unreleased] - v0.9.0 with BOTH features
  
Result: ✓ No corruption (commits are sequential in git history)
```

**Actual Risk**: Not race conditions (git is sequential), but **idempotency failures**:

1. User runs `update-changelog.py` manually
2. Pre-commit hook runs automatically
3. Manual invocation runs again on CI/CD
4. **Result**: Multiple tools writing CHANGELOG simultaneously with no locking

### 1.3 Crash/Failure Scenarios

**Scenario**: `changelog_updater.py` crashes mid-write

```python
# Line 295: write_changelog(updated_content, changelog_path)
#
# If process dies here:
#   ✗ CHANGELOG.md truncated or partially written
#   ✗ [Unreleased] section malformed
#   ✗ Git index staged a corrupted file
#   ✓ Commit still succeeds (exit 0)
#   ✓ Next hook run will overwrite with new state
```

**Current State**: No atomic writes, no rollback, no validation on write.

```python
# changelog_updater.py:46-57
def write_changelog(content: str, changelog_path: Optional[Path] = None) -> None:
    if changelog_path is None:
        changelog_path = Path(get_repo_root()) / "CHANGELOG.md"
    
    changelog_path.write_text(content)  # ← NOT ATOMIC
```

**Risk Level**: MEDIUM (corruption detectable via next commit, but PR gets bad CHANGELOG)

---

## 2. DESIGN FLAWS: [UNRELEASED] & VERSIONING SEMANTICS

### 2.1 The [Unreleased] Anti-Pattern

**Problem**: `[Unreleased]` in CHANGELOG.md is not a real version — it's a **working directory preview**.

Current format (from CHANGELOG.md line 5):
```markdown
## [Unreleased] - v0.35.0

### Added
- Feature A
- Feature B
```

**Why this is broken**:

1. **No Semantic Meaning**: Is `[Unreleased] - v0.35.0` a promise? A prediction? Both are unstable.
2. **Conflicts with Real Workflow**: When you release `v0.35.0`, you must:
   - Remove `[Unreleased] - v0.35.0` section
   - Rename it to `## [v0.35.0] - 2026-05-26`
   - Create a NEW `[Unreleased] - v0.36.0` section
   - **This is a 3-way merge conflict every release**

3. **Git Blame Hell**: Every unreleased section gets rewritten → blame history is destroyed

4. **No Real-World Use Case**: 
   - CI/CD doesn't read `[Unreleased]` (uses git tags)
   - Users don't read `[Unreleased]` (unstable)
   - Release automation ignores it (creates fresh tags)

### 2.2 Correct Semantic Versioning Approach

**Standard (Keep a Changelog)**:

```markdown
# Changelog

## [Unreleased]       ← Only section, no version number

### Added
- Feature A

### Fixed
- Fix B

---

## [0.8.0] - 2026-05-23   ← Real version with date

### Added
- Initial release
```

**Why no version in [Unreleased]**:
- It's a **work-in-progress**, not a committed version
- Version is determined by **git tags**, not CHANGELOG
- Release tool converts `[Unreleased]` → `[X.Y.Z] - YYYY-MM-DD`

### 2.3 Why VERSIONING.md Contradicts This

From VERSIONING.md (lines 33-36):
```
- **Git tags** — Primary version source (created automatically by CI/CD)
- **.github/workflows/ci.yml** — Automatic tagging and release
- **scripts/get_version.py** — Version utility (read/bump versions)
```

**The Truth**:
- ✅ Git tags ARE the authoritative version (correct)
- ❌ CHANGELOG.md should NOT contain version predictions (wrong)
- ❌ `version-manager` shouldn't exist (conflicts with CI/CD automation)

---

## 3. AUTOMATION ISSUES: EVERY-COMMIT UPDATES & CI/CD CONFLICTS

### 3.1 The Every-Commit CHANGELOG Update Problem

**Current design** (from SKILL.md line 31):
> Git pre-commit hook that runs version calculation

**What this means**:

```
git commit -m "docs: typo fix"
  ↓
pre-commit hook fires
  ↓
version_calculator.py runs
  ↓ 
"No commits since tag" (docs commits don't bump version)
  ↓
changelog_updater.py runs
  ↓
CHANGELOG.md rewritten even though nothing changed
  ↓
git add CHANGELOG.md (hook adds it to stage)
  ↓
Commit amended with CHANGELOG changes
```

**Problem 1: Noise**
- Every commit modifies CHANGELOG (even trivial changes)
- Makes git history unreadable
- `git log --oneline` is full of "docs: typo" + auto-CHANGELOG updates

**Problem 2: Merge Conflicts**
- On PR merges to main, CHANGELOG is always in conflict
- Reason: Every PR changes it, every main commit changes it
- **Example**: 5 PRs in parallel → 5-way CHANGELOG conflict on main merge

**Problem 3: CI/CD Mismatch**
- Local `version-manager` calculates v0.35.0
- Mainline CI/CD (`github-tag-action`) calculates v0.35.0
- If they diverge → version mismatch
- **No validation that they stay in sync**

### 3.2 Sequence Diagram: The Corruption Flow

```
Developer's Machine:
1. git commit -m "feat: new feature"
   → pre-commit adds: ## [Unreleased] - v0.9.0
2. git push origin feature-branch

GitHub:
3. PR created, passes CI (tests don't check CHANGELOG version)
4. PR merged to main
   → CI runs github-tag-action
   → Calculates v0.35.0 (different from local v0.9.0!)
   → Creates tag v0.35.0
   → Creates Release with auto-generated notes

Result:
❌ CHANGELOG says [Unreleased] - v0.9.0
✅ Git tag is v0.35.0
✅ Release notes (from tag) are auto-generated
→ **CHANGELOG is now stale and ignored**
```

### 3.3 Why [Unreleased] Keeps Coming Back

From git history:
```
9975d9e fix(changelog): remove version from [Unreleased] (final fix)
4b983c9 fix(changelog): remove version number from [Unreleased] section
27e0680 fix(test): adjust CHANGELOG validation to match version-manager design
```

**Root Cause**: 
- Someone removes `[Unreleased]` manually
- Next commit runs pre-commit hook
- Hook regenerates `[Unreleased]` automatically
- **The hook is doing its job; the design is broken**

---

## 4. ROOT CAUSE ANALYSIS: WHY [UNRELEASED] REAPPEARS

### The Mechanism

1. **CHANGELOG manually cleaned** (remove `[Unreleased]`)
   ```bash
   nano CHANGELOG.md  # Remove [Unreleased] section
   git add CHANGELOG.md
   git commit -m "docs: remove [Unreleased] placeholder"
   ```

2. **Next commit triggers pre-commit hook**
   ```bash
   git commit -m "feat: new feature"
   ↓ (pre-commit hook runs)
   ↓ version_calculator.determine_version_bump() sees "feat: new feature"
   ↓ Calculates next_version = "v0.9.0"
   ↓ changelog_updater.generate_unreleased_section("v0.9.0", [("commit", "2026-05-26", "feat: new feature")])
   ↓ generate_unreleased_section() returns: "## [Unreleased] - v0.9.0\n..."
   ↓ insert_unreleased_section() inserts it back
   ↓ CHANGELOG.md updated
   ↓ git add CHANGELOG.md (hook stages it)
   ↓ Commit succeeds
   ```

3. **[Unreleased] is back** (because the hook WANTS it there)

### The Design Intent (from SKILL.md)

> "Maintains [Unreleased] section with next projected version"

**Translation**: The skill is **supposed** to auto-generate and regenerate `[Unreleased]` on every commit.

**Problem**: This conflicts with the stated goal:
- VERSIONING.md says: "Git tags are the only source of truth"
- But version-manager assumes CHANGELOG is a source of truth
- **Contradiction**: Can't have two sources of truth

---

## 5. THREAT ASSESSMENT TABLE

| Threat | Severity | Type | Exploitability | Detectability |
|--------|----------|------|-----------------|----------------|
| Hook bypass via `--no-verify` | CRITICAL | Integrity | Trivial | Medium |
| CHANGELOG corruption on crash | HIGH | Integrity | Requires crash | Medium |
| [Unreleased] merge conflicts | HIGH | Availability | Automatic | High |
| Version mismatch (local vs CI/CD) | HIGH | Correctness | Automatic | Low |
| [Unreleased] regeneration loop | MEDIUM | Automation | Automatic | High |
| Race conditions (low likelihood) | LOW | Integrity | Complex | High |
| Manual edit conflicts with hooks | MEDIUM | Integrity | Common | High |

---

## 6. RECOMMENDED FIXES: ARCHITECTURAL LEVEL

### Option A: DISABLE version-manager (Recommended ✅)

**Rationale**:
- Git tags are already authoritative (VERSIONING.md confirms)
- CI/CD already creates tags automatically (github-tag-action)
- Local version calculation adds nothing
- Removes all hooks + automation
- Simplifies to: **Tags only, CHANGELOG updated on release**

**Implementation**:
1. Delete: `.githooks/version-manager` entries
2. Delete: `skills/version-manager/` directory
3. Update: `.github/workflows/ci.yml` (remove version-manager steps)
4. Manual release process:
   ```bash
   git log v0.8.0..HEAD --oneline | grep "^feat\|^fix" | wc -l
   # → Decide if patch/minor/major bump manually
   # → Tag manually: git tag v0.8.1 && git push --tags
   # → Update CHANGELOG manually (once): ## [v0.8.1] - 2026-05-26
   ```

**Pros**:
- No hooks = no bypass risk
- No CHANGELOG corruption
- No merge conflicts (CHANGELOG only updated on release)
- Clear source of truth (git tags)
- Reduces maintenance burden

**Cons**:
- Manual release process (acceptable for mature projects)
- Requires discipline in tagging

### Option B: FIX version-manager (If tags not available locally)

Only if: "We want developers to see next version locally before pushing"

**Changes**:
1. **Remove** `[Unreleased] - vX.Y.Z` versioning from CHANGELOG
   - Keep: `## [Unreleased]` (no version number)
   - Reason: Version is determined by tags, not predictions

2. **Make hooks non-auto** (opt-in only)
   ```bash
   # Current: Automatic on every commit
   # Proposed: Manual only
   python3 scripts/version-manager/update-changelog.py  # Run manually
   ```

3. **Add atomic write protection**
   ```python
   def write_changelog_atomic(content: str, path: Path):
       # Write to temp file
       with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as tmp:
           tmp.write(content)
           tmp.flush()
           os.fsync(tmp.fileno())
       # Atomic rename
       os.replace(tmp.name, path)
   ```

4. **Add validation in CI/CD**
   ```bash
   # Pre-merge gate
   python3 scripts/validate_changelog_ci.py
   # Checks: [Unreleased] exists, matches git history, no version number
   ```

5. **Add conflict resolution in release**
   ```bash
   # On release: git tag creates a commit with [Unreleased] → [X.Y.Z] transition
   git commit -m "chore: release v0.8.1" -- CHANGELOG.md
   ```

**Pros**:
- Keeps local version preview feature
- Reduces merge conflicts (manual-only)
- Cleaner CHANGELOG (no bad versions)

**Cons**:
- Still requires user discipline (manual invocation)
- Still requires hook configuration locally
- More complex CI/CD validation

### Option C: Revert to CI/CD Only (Conventional Changelog)

**Use**: [`conventional-changelog`](https://github.com/conventional-changelog/conventional-changelog) library

**How it works**:
```bash
# On release (in CI/CD only):
npx conventional-changelog -p angular -i CHANGELOG.md -s
# Generates from commit history, no local version-manager needed
```

**Pros**:
- Single source of truth (git commits + tags)
- No local hooks
- No CHANGELOG merge conflicts
- Industry standard

**Cons**:
- Requires Node.js (or Python equivalent: `python-semantic-release`)
- Can't preview locally (must push to see version)

---

## 7. VALIDATION APPROACH: PREVENT REGRESSION

### Pre-Merge Gate Checks

```python
# scripts/validate_changelog_ci.py

def validate_changelog():
    """Pre-merge validation for CHANGELOG.md"""
    
    # 1. Check [Unreleased] exists (for working development)
    if "[Unreleased]" not in changelog:
        raise ValidationError("[Unreleased] section required")
    
    # 2. Check no version numbers in [Unreleased] (if Option B)
    if re.search(r"\[Unreleased\].*-\s*v?\d+\.\d+", changelog):
        raise ValidationError("[Unreleased] must not contain version number")
    
    # 3. Check released versions are immutable
    tags = get_git_tags()
    for version in extract_changelog_versions(changelog):
        if version in tags:
            # Verify CHANGELOG[version] hasn't changed since tag
            changelog_content = get_changelog_section(version)
            tag_commit = get_git_commit(f"v{version}")
            if changelog_content != get_changelog_from_commit(version, tag_commit):
                raise ValidationError(f"Released version {version} cannot be modified")
    
    # 4. Check format compliance
    if not is_valid_markdown_format(changelog):
        raise ValidationError("CHANGELOG format incorrect")
    
    return True
```

### Post-Release Validation

```bash
# After CI/CD creates tag:
# 1. Verify tag version matches CHANGELOG latest release
# 2. Verify [Unreleased] is clean (not duplicated)
# 3. Verify no [Unreleased] in released version (sanity check)
```

### Git Hook Enforcement (If Keeping Hooks)

```bash
# .githooks/pre-push
# Enforce: can't push if [Unreleased] was manually edited
if git diff HEAD~1 CHANGELOG.md | grep -E "^-.*\[Unreleased\]|^+.*\[Unreleased\]"; then
    echo "❌ [Unreleased] section was manually edited before push"
    echo "   Let the hook auto-update it automatically"
    exit 1
fi
```

---

## 8. RISK MITIGATIONS FOR RECOMMENDED APPROACH (OPTION A)

### If version-manager is DISABLED:

**Risk 1: Developers forget to tag releases**
- *Mitigation*: Require manual GitHub release creation (via web UI)
- *Validation*: CI/CD check: no tag = no release

**Risk 2: Inconsistent version numbers**
- *Mitigation*: Keep VERSIONING.md as single source of truth
- *Validation*: setup.py reads version from git tags only

**Risk 3: CHANGELOG becomes stale**
- *Mitigation*: Release checklist requires CHANGELOG update
- *Validation*: Pre-release script checks CHANGELOG has release entry

**Risk 4: Manual CHANGELOG edits cause conflicts**
- *Mitigation*: Release happens only on main (no concurrent PRs editing CHANGELOG)
- *Validation*: Don't merge PRs that edit CHANGELOG + code together

---

## 9. SUMMARY: RECOMMENDED FIX

| Aspect | Recommendation |
|--------|-----------------|
| **Best Option** | **Option A: Disable version-manager** |
| **Reason** | Tags are already authoritative; no benefit from local version-manager |
| **Changes** | Remove hooks, delete skill, update CI/CD workflow |
| **Effort** | Low (1-2 hours) |
| **Testing** | Release one version manually to validate process |
| **Maintenance** | Low (no hooks to maintain locally) |
| **Risk** | None (we lose nothing; tags still work) |

### Implementation Checklist:

- [ ] Delete `.githooks/version-manager` section from pre-commit
- [ ] Rename `skills/version-manager/` → `DEPRECATED-version-manager-skill/`
- [ ] Update SKILL.md to document deprecation
- [ ] Remove from TODO.md
- [ ] Remove from `.github/workflows/ci.yml` (if any reference)
- [ ] Update VERSIONING.md: remove version-manager references
- [ ] Add release checklist to CONTRIBUTING.md
- [ ] Test: Create manual release with git tag
- [ ] Verify: setup.py reads version correctly from tag

---

## 10. APPENDIX: EVIDENCE FOR ROOT CAUSE

**Why [Unreleased] keeps reappearing**: The skill is **working as designed**.

From SKILL.md line 32:
```
**Behavior:**
- Non-blocking: failures don't prevent commit
- Automatic: no user interaction required
- Idempotent: running twice has same effect
- Local-only: no network calls
```

The hook is **intentionally designed** to:
1. Detect new commits
2. Recalculate next version
3. Regenerate [Unreleased] section
4. Stage CHANGELOG.md

If `[Unreleased]` is manually removed, the next commit will regenerate it. This is **by design**, not a bug.

**The real problem**: The design itself is flawed (conflicts with CI/CD automation).

---

## 11. IMPACT ASSESSMENT

### On Current PR Merge Workflow

**Current State**: PRs are blocked by [Unreleased] issues

**Option A Impact** (Recommended):
- ✅ Removes CHANGELOG merge conflict entirely
- ✅ Unblocks PR merge process immediately
- ✅ No post-merge surprise version mismatches
- ✅ Simplifies workflow

**Option B Impact**:
- ⚠️ Reduces but doesn't eliminate CHANGELOG conflicts
- ⚠️ Still requires hook discipline locally
- ⚠️ More complex validation in CI/CD

**Option C Impact**:
- ✅ Solves merge conflict issue
- ⚠️ Requires Node.js dependency
- ⚠️ Different CHANGELOG format (automated)

### Security Implications

**Option A**: 
- Eliminates hook bypass risk (no hooks = no bypasses)
- Manual process = lower automation risk
- Trades automation for clarity

**Option B**:
- Reduces but doesn't eliminate hook bypass risk
- Still subject to `--no-verify` bypass
- More complexity = more attack surface

**Option C**:
- Eliminates local hook risk
- CI/CD controlled (more secure)
- Standard industry practice

---

## 12. CONCLUSION

The `version-manager` skill was designed to solve a problem that **git tags already solve**. It introduces:
- Integrity risks (hook bypasses)
- Design flaws ([Unreleased] semantics)
- Automation issues (every-commit updates)
- Source-of-truth conflicts

**Recommended action**: **Option A - Disable version-manager entirely**

This removes all associated risks while preserving the stable, working git tag-based versioning system already in place.

The recurring `[Unreleased]` problem is not a bug — it's a symptom of a fundamentally flawed design that cannot be fixed by removing symptoms. The design itself must change.

---

**Audit Date**: 2026-05-26  
**Severity**: HIGH  
**Status**: AWAITING PRINCIPAL ENGINEER DECISION  
**Recommendation**: Implement Option A (Disable version-manager)
