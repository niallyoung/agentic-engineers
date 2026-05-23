# Versioning Strategy Analysis & Recommendations
**Principal Engineer Review** | agentic-engineers

---

## EXECUTIVE SUMMARY

**Current State:** Versioning is **partially implemented** but has a **critical sync gap**.

- ✅ Semantic versioning documented (VERSIONING.md)
- ✅ CI/CD tagging automation configured (mathieudutour/github-tag-action)
- ✅ get_version.py script reads from VERSION file
- ✅ setup.py reads VERSION file for package metadata
- ❌ **VERSION file NOT auto-updated when tags are created**
- ❌ **9 commits since v0.8.0 tag with no new release**
- ❌ **VERSION file (0.8.0) is stale and out of sync with git state**

**Risk Level:** 🔴 **HIGH** — Package builds, PyPI uploads, and version checks are unreliable.

---

## DETAILED ANALYSIS

### 1. Current Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CI/CD Release Pipeline                       │
└─────────────────────────────────────────────────────────────────┘
       ↓
   Commit pushed to main
       ↓
   Quality Gate (lint, test, verify)
       ↓
   [IF PASS] Tag Release Job
       ├─→ mathieudutour/github-tag-action (creates git tag)
       │   └─→ Reads commits since last tag
       │   └─→ Calculates new version (semantic)
       │   └─→ Creates tag v0.8.1, v0.9.0, etc.
       │   └─→ ✅ Outputs new_tag to $GITHUB_STEP_SUMMARY
       │
       └─→ ncipollo/release-action (creates GitHub Release)
           └─→ ✅ Creates Release with changelog
           
   ❌ NO STEP TO UPDATE VERSION FILE
   ❌ VERSION file remains stale after tag
```

### 2. Current State Snapshot

| Component | Value | Status |
|-----------|-------|--------|
| **VERSION file** | `0.8.0` | ⚠️ Stale |
| **Latest git tag** | `v0.8.0` | ✅ Current |
| **Commits since tag** | 9 | ⚠️ Unreleased work |
| **Commit types** | 5 `fix:`, others `docs:`, `cleanup:` | ⚠️ Should trigger patch bump |
| **VERSIONING.md claim** | "VERSION file updated after tag" | ❌ NOT TRUE |
| **setup.py reads** | VERSION file | ⚠️ Gets stale version |
| **get_version.py logic** | Reads VERSION file, falls back to git tags | ⚠️ Fallback logic never tested |

### 3. Root Cause Analysis

**Why VERSION file isn't auto-updated:**

1. **CI/CD workflow (.github/workflows/ci.yml) is incomplete**
   - Creates git tag ✅
   - Creates GitHub Release ✅
   - **Missing step:** Update VERSION file in git repository ❌

2. **VERSIONING.md documents the intended behavior (line 33-35):**
   ```
   3. **Updates VERSION file** (read by `setup.py`)
      - Tracks current version for documentation
      - Used by `scripts/get_version.py`
   ```
   But this is **aspirational, not implemented**.

3. **CI/CD automation provides tag output**
   - `${{ steps.tag.outputs.new_tag }}` contains the new tag (e.g., `v0.8.1`)
   - Could easily be used to update VERSION file

4. **No feedback loop between tagging and VERSION**
   - Tag creation doesn't trigger VERSION update
   - No protection against accidental VERSION drift

### 4. Impact of Current Gap

#### a) **Setup.py builds with stale version**
```python
# setup.py reads VERSION file (line 10)
version = version_file.read_text().strip()  # Gets "0.8.0"
```
- PyPI package metadata shows outdated version
- Package installation confusion
- Version mismatch between source and installed package

#### b) **get_version.py has unused fallback logic**
```python
# Line 39-47: Reads VERSION file first, then git tags
def get_current_version():
    try:
        with open(".../VERSION") as f:
            return f.read().strip()  # Always succeeds, returns stale version
    except:
        tag = get_latest_tag()  # Never reaches here
        if tag:
            return tag.lstrip("v")
        return "0.8.0"
```
- Fallback logic to git tags is dead code
- Script always returns stale VERSION file
- If git logic were used, it would be correct (v0.8.0-9-g7c82452)

#### c) **Documentation vs Reality mismatch**
- VERSIONING.md documents auto-update ❌ Not implemented
- Developers follow documented procedure ❌ Fails
- Causes confusion and manual workarounds

#### d) **Risk to releases and deployments**
- If PyPI upload uses VERSION file: **wrong version published**
- If version checks use get_version.py: **detects wrong version**
- If monitoring/logging uses VERSION: **incorrect telemetry**

### 5. Problem Classification

This is a **design implementation gap**, not a bug report:

- ✅ The design is sound (auto-update in CI/CD)
- ✅ The workflow configuration exists
- ✅ The trigger point (tag creation) is identified
- ❌ The update step was never implemented in the workflow
- ❌ The documentation promises a feature that doesn't exist

---

## RECOMMENDED SOLUTION: Option C (Git-Based with Verification)

### Why Not Other Options?

#### Option A: Auto-update VERSION in CI/CD ❌
**Pros:** Simple, documented behavior  
**Cons:**  
- Requires git commit + push in CI/CD (potential circular runs)
- Needs careful handling to avoid triggering CI/CD again
- Adds workflow complexity
- VERSION file becomes redundant

#### Option B: Keep VERSION Manual ❌
**Pros:** Simple, no automation needed  
**Cons:**
- Error-prone (developers forget to update)
- Breaks existing workflow expectations
- Violates VERSIONING.md documentation
- Version drift is guaranteed over time

#### Option C: Git Tags as Source of Truth ✅ **RECOMMENDED**
**Pros:**
- Single source of truth (git tags)
- No dual maintenance burden
- Eliminates sync gaps by design
- Works offline (git tag available locally)
- Compliant with semantic versioning best practices
- Scalable and maintainable

**Cons:**
- Requires refactoring setup.py and get_version.py
- Minimal work (2 files, ~20 lines total)

#### Option D: Hybrid (Verify + Auto-Correct) ✅ **ALTERNATIVE**
**Approach:** Use git tags as primary, VERSION file as fallback/cache
**Best for:** Gradual migration while maintaining backward compatibility

---

## IMPLEMENTATION PLAN: Option C (Recommended)

### Phase 1: Update get_version.py (Primary Source: Git Tags)

**Current logic (fallback only):**
```python
def get_current_version():
    try:
        with open(".../VERSION") as f:
            return f.read().strip()
    except:
        tag = get_latest_tag()  # Fallback
        if tag:
            return tag.lstrip("v")
        return "0.8.0"
```

**New logic (git-first):**
```python
def get_current_version():
    """Get current version from git tags (primary), VERSION file (fallback)."""
    try:
        # Primary: Read git tags
        tag = get_latest_tag()
        if tag:
            return tag.lstrip("v")
    except:
        pass
    
    # Fallback: Read VERSION file
    try:
        with open(".../VERSION") as f:
            return f.read().strip()
    except:
        return "0.8.0"  # Absolute fallback
```

**Rationale:**
- Git tags are always accurate (immutable after push)
- Developers can't accidentally break versioning
- Works in CI/CD before tags exist (falls back to VERSION)
- Handles edge cases gracefully

### Phase 2: Update setup.py (Dynamic Version Detection)

**Current logic:**
```python
version_file = Path(__file__).parent / "VERSION"
if version_file.exists():
    version = version_file.read_text().strip()
else:
    version = "0.8.0"
```

**New logic (call get_version.py):**
```python
import subprocess
import sys

def get_version():
    """Get version from git tags or VERSION file."""
    try:
        result = subprocess.run(
            [sys.executable, "scripts/get_version.py"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    
    # Fallback: Direct file read
    version_file = Path(__file__).parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    
    return "0.8.0"

setup(
    name="agentic-engineers",
    version=get_version(),
    ...
)
```

**Alternative (Simpler, recommended):**
```python
import sys
sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from get_version import get_current_version

setup(
    name="agentic-engineers",
    version=get_current_version(),
    ...
)
```

**Rationale:**
- Eliminates VERSION file read from setup.py
- setup.py gets version from same source as CLI tools
- Consistent version everywhere

### Phase 3: Update .github/workflows/ci.yml (Optional: Verify step)

**Add verification step after GitHub Release (line 99):**
```yaml
      - name: Verify Version Consistency
        if: steps.tag.outputs.new_tag
        run: |
          NEW_TAG=${{ steps.tag.outputs.new_tag }}
          NEW_VERSION=${NEW_TAG#v}  # Remove 'v' prefix
          
          echo "Created tag: $NEW_TAG"
          echo "Version:     $NEW_VERSION"
          
          # Verify get_version.py returns the new version
          SCRIPT_VERSION=$(python3 scripts/get_version.py)
          if [ "$SCRIPT_VERSION" != "$NEW_VERSION" ]; then
            echo "ERROR: Version mismatch!"
            echo "  Expected: $NEW_VERSION"
            echo "  Got:      $SCRIPT_VERSION"
            exit 1
          fi
          
          echo "✅ Version verified: $NEW_VERSION"
```

**Rationale:**
- Catches version mismatches in CI/CD
- Fails release if version inconsistent
- Prevents silent failures

### Phase 4: Update VERSIONING.md (Documentation)

**Update lines 33-35 to reflect new reality:**
```markdown
3. **Git Tags as Source of Truth**
   - `get_version.py` reads from git tags (primary source)
   - `VERSION` file retained for fallback (documentation only)
   - Ensures automatic consistency: tag created → version reflects immediately
   - No manual VERSION updates needed
```

**Update "Reading Current Version" section (lines 68-82):**
```bash
# Get version from git tags (primary source)
python3 scripts/get_version.py

# Get next patch version (calculates from current tag)
python3 scripts/get_version.py next-patch

# VERSION file is maintained as fallback only
cat VERSION  # Optional, for reference
```

---

## TRANSITION STRATEGY

### Minimal Migration (Recommended)

1. **Update get_version.py** (git-first logic)
   - Time: 5 minutes
   - Risk: Low (backward compatible)

2. **Update setup.py** (use get_version.py)
   - Time: 10 minutes
   - Risk: Low (same source of truth)

3. **Update VERSIONING.md** (document reality)
   - Time: 5 minutes
   - Risk: None (docs only)

4. **Update VERSION file** (optional cleanup)
   - Time: 1 minute
   - Current: `0.8.0` → Update to next version or remove
   - Recommendation: Keep for reference, but mark as fallback

### No Breaking Changes

- ✅ get_version.py still works with same CLI interface
- ✅ setup.py still provides `version` parameter
- ✅ All existing workflows continue to work
- ✅ Gradual, non-breaking migration

---

## VERIFICATION CHECKLIST

After implementation, verify:

- [ ] `python3 scripts/get_version.py` returns latest git tag (without `v`)
- [ ] `python3 scripts/get_version.py next-patch` calculates correct next version
- [ ] `python3 setup.py --version` matches `get_version.py` output
- [ ] VERSION file exists but is not the primary source
- [ ] VERSIONING.md accurately documents the git-first approach
- [ ] Test with and without git tags (edge cases)
- [ ] Test in CI/CD (before and after tag creation)

---

## BENEFITS OF THIS APPROACH

| Aspect | Before | After |
|--------|--------|-------|
| **Source of truth** | VERSION file (stale) | Git tags (immutable) |
| **Manual sync needed?** | Yes ❌ | No ✅ |
| **Consistency** | Poor (sync gap) | Perfect (by design) |
| **Risk of drift** | High | None |
| **CI/CD complexity** | High (needs update step) | Low (no extra step) |
| **Offline usage** | Not viable | Works with git tags |
| **Scalability** | Limited | Scales indefinitely |
| **Documentation accuracy** | Misleading | Accurate |

---

## ROLLBACK PLAN

If implementation causes issues:

1. **Revert get_version.py** changes:
   ```bash
   git revert <commit-hash>
   ```

2. **Revert setup.py** changes:
   ```bash
   git revert <commit-hash>
   ```

3. System returns to reading VERSION file only (no worse than current state)

---

## NEXT STEPS

1. **Principal Engineer approval** ✅ (this document)
2. **Create implementation ticket** → Assign to Senior Engineer
3. **Implement Phase 1-3** (30 minutes total)
4. **Test in branch** before merging to main
5. **Verify in next release** (when next tag is created)
6. **Monitor** for version discrepancies in logs

---

## NOTES FOR SENIOR ENGINEER

**When implementing:**
- Start with get_version.py (lowest risk)
- Test git tag fallback edge case (no tags exist)
- Verify setup.py import works in build environment
- Add docstrings explaining git-first logic
- Update any other scripts that read VERSION file (if any)
- Consider adding version verification to Makefile verify target

**Testing:**
- Unit test get_current_version() with mock git tags
- Integration test setup.py with and without VERSION file
- Test in CI/CD pipeline before and after tag
- Test local dev environment (git clone fresh repo)

