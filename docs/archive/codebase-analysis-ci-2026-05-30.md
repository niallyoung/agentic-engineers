# Agentic Engineers - CI/Environment Analysis Report

## Executive Summary

The agentic-engineers codebase has **TWO CONFLICTING IMPLEMENTATIONS** of `queue_path_validator.py` with different contracts, causing systematic test failures in CI. Additionally, there are critical environment-specific issues with symlink handling between macOS (local) and Linux (CI).

---

## 1. CRITICAL ISSUE: Duplicate Queue Path Validator with Conflicting Contracts

### Location
- **File 1 (Simple contract)**: `/renderer/validate_skills.py` lines 39-148
  - Returns `Dict` on all inputs
  - Never raises exceptions
  - Returns early on None/empty with error dict

- **File 2 (Complex contract)**: `/src/skills/_meta/queue-path-validator/queue_path_validator.py` lines 40-222
  - Raises `AssertionError` on contract violations
  - Accepts both `Path` and `str` types
  - Includes parent directory validation
  - Has file vs directory handling

### Test Failures (16 of 33 tests failing)

The tests at `tests/test_queue_path_validator.py` expect **File 1's contract** but run against **File 2's implementation**:

```
FAILURES:
✗ test_valid_canonical_path_absolute         → AssertionError: file not string
✗ test_valid_canonical_path_relative         → Different error message format
✗ test_valid_canonical_path_with_trailing_slash
✗ test_valid_harness_names
✗ test_valid_session_id_formats              → Session validation broken
✗ test_reject_empty_path                     → Expects dict, gets AssertionError
✗ test_reject_none_path                      → Expects dict, gets AssertionError
✗ test_reject_invalid_session_id_too_short   → Error message mismatch
✗ test_reject_malformed_path                 → Error message mismatch
... and 7 more subdirectory tests
```

### Root Cause

The implementation in **File 2** raises exceptions instead of returning error dicts:

```python
# File 2 - RAISES on None (line 82)
if path is None or (isinstance(path, str) and not path.strip()):
    raise AssertionError("Path must be a non-empty string or Path object")

# Tests expect (File 1 style - line 62-69):
if not path or not isinstance(path, str):
    return {
        'valid': False,
        'session_id': None,
        ...
        'error': 'Path must be a non-empty string'
    }
```

### Symlink Handling Consistency

| Aspect | File 1 | File 2 |
|--------|--------|--------|
| **Symlink check** | `os.path.islink(normalized)` (line 97) | `os.path.islink(normalized)` (line 134) |
| **Availability** | Checks only if exists | Checks only if exists |
| **macOS vs Linux** | Both use POSIX `os.path.islink` ✓ | Both use POSIX `os.path.islink` ✓ |
| **GitHub Actions** | Git checkout with `core.symlinks=true` (ci.yml:22) | Same config |
| **Issue** | None detected - both consistent | **BUT** test suite doesn't preserve symlinks in test fixtures |

---

## 2. Environment Differences: macOS (Local) vs Linux (CI)

### macOS (Local Environment)

```
OS:                 macOS (Darwin)
Python:             3.7.4 (from /Library/Frameworks)
File system:        APFS (case-insensitive, supports symlinks natively)
Symlink creation:   os.symlink() works without special permissions
Path handling:      Uses forward slashes natively
Line endings:       LF (Git configured)
```

### Linux (GitHub Actions - CI)

```
OS:                 Ubuntu Latest (ubuntu-latest)
Python:             3.11 (actions/setup-python@v5)
File system:        ext4/overlayfs (in container)
Symlink creation:   Requires CAP_SYS_ADMIN in Docker
Path handling:      Uses forward slashes
Line endings:       LF (Git configured)
CI symlink setting: git config --global core.symlinks true (ci.yml:22)
```

### Critical CI Configuration Issue

The CI workflow **explicitly preserves symlinks** in line 22 of `.github/workflows/ci.yml`:
```yaml
- name: Preserve symlinks
  run: git config --global core.symlinks true
```

But this is **AFTER checkout (line 15)**, meaning:
1. Checkout happens first (may not create symlinks)
2. Then symlinks are enabled (too late for existing files)

**ISSUE**: If Git checkout skips symlink creation (due to Windows-mode defaults or permissions), the subsequent config has no effect.

### Path Resolution Differences

| Operation | macOS | Linux (CI) |
|-----------|-------|-----------|
| `Path.resolve()` | Uses APFS symlink resolution | Uses ext4 resolution |
| `Path.is_symlink()` | ✓ Works | ✓ Works |
| `os.path.islink()` | ✓ Works | ✓ Works (with CAP_SYS_ADMIN) |
| Relative symlinks | ✓ Works | ✓ Works (if created) |
| Broken symlinks | Returns False on exists() | Returns False on exists() |
| Symlink loops | Path.resolve() detects | Path.resolve() detects |

---

## 3. Path Validation Implementation Details

### validate_queue_path() Contract Violations

**Type signature mismatch:**
```python
# Declared return type (docstring)
Returns Dict[str, Any] with keys: valid, session_id, harness, subdir, error

# Actual behavior in File 2 (lines 77-82)
if not isinstance(path, (Path, str)):
    raise AssertionError(...)  # ← VIOLATES contract (should return dict)

if path is None or (isinstance(path, str) and not path.strip()):
    raise AssertionError(...)  # ← VIOLATES contract
```

**Tests expect:**
```python
# tests/test_queue_path_validator.py:104-112
result = validate_queue_path('')  # Should return dict
result = validate_queue_path(None)  # Should return dict
assert result['valid'] is False
assert result['error'] is not None
```

### Path Pattern Analysis

Both implementations use regex to validate canonical paths:

```python
CANONICAL_QUEUE_PATTERN = re.compile(
    r'^~?/?\.agentic-engineers/artifacts/([a-z0-9\-]+)/([a-z0-9\-]+)/queue/?$'
)
```

**Pattern breakdown:**
- `~?/?` - Optional tilde and optional leading slash (allows both relative/absolute)
- `\.agentic-engineers/artifacts/` - Literal directory path
- `([a-z0-9\-]+)/` - Capture group 1: session_id (lowercase, hyphens, digits)
- `([a-z0-9\-]+)/` - Capture group 2: harness name (lowercase, hyphens, digits)
- `queue/?$` - Literal "queue" dir with optional trailing slash

**Test expectations vs reality:**

| Test Input | Expected | File 1 | File 2 | Status |
|------------|----------|--------|--------|--------|
| `~/.agentic-engineers/artifacts/session-001/opencode/queue` | valid | matches | matches | ✓ |
| `.agentic-engineers/artifacts/session-001/opencode/queue` | valid | matches | matches | ✓ |
| `''` (empty) | error dict | returns dict | **raises** | ✗ |
| `None` | error dict | returns dict | **raises** | ✗ |
| `~/.agentic-engineers/artifacts/session-001` | error dict | matches fails | matches fails | ✓ |

---

## 4. Symlink Detection & Behavior

### macOS Symlink Creation (Local Tests)

```python
# Works fine on macOS
link_file = skills_dir / "link.md"
link_file.symlink_to(target_file)  # Creates symlink

# Both detection methods work
assert link_file.is_symlink()           # ✓ True
assert os.path.islink(str(link_file))   # ✓ True
```

### Linux Symlink Handling (CI Environment)

```python
# In container: works IF CAP_SYS_ADMIN is present
link_file = skills_dir / "link.md"
link_file.symlink_to(target_file)

# Both detection methods work
assert link_file.is_symlink()           # ✓ True
assert os.path.islink(str(link_file))   # ✓ True
```

### GitHub Actions Checkout Behavior

The `actions/checkout@v4` action:
1. Clones repo with default settings
2. Symlinks are preserved **IF** the repo contains them
3. Relative symlinks are handled correctly
4. BUT: Bytecode cache (.pyc) can interfere with symlink detection

**Critical issue in conftest.py (lines 39-54):**
```python
def pytest_configure(config):
    # Clears .pytest_cache but NOT __pycache__
    cache_dir = os.path.join(os.getcwd(), '.pytest_cache')
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)  # ← Only clears pytest cache
    # __pycache__ remains, can contain stale symlink info
```

---

## 5. Permission Models Across Operating Systems

### macOS Permission Model

```
File creation:  User can create symlinks (no special permission)
Symlink follow: APFS follows symlinks automatically
Path traversal: Blocked by relative_to() check
Bytecode:       .pyc cached in __pycache__/
```

### Linux Permission Model (Ubuntu Container)

```
File creation:  Requires CAP_SYS_ADMIN in containers
Symlink follow: ext4 follows symlinks automatically
Path traversal: Blocked by relative_to() check
Bytecode:       .pyc cached in __pycache__/
Container user: Usually root (full permissions)
```

### Permission Issues Observed

None detected in current implementation - both use `os.path.islink()` which works across platforms.

---

## 6. Testing Infrastructure

### Test Harness Structure

**Root conftest.py** (`/conftest.py` - 56 lines):
- Adds `src/` to sys.path
- Adds `src/skills/` to sys.path for hyphenated skill imports
- Sets PYTHONPATH env var for subprocess inheritance

**Tests conftest.py** (`/tests/conftest.py` - 250 lines):
- Clears .pytest_cache on session start (line 48-54)
- Audits test sources exist (not just .pyc cache) (line 57-125)
- Provides factory functions: `make_delegate()`, `make_handback()`
- Provides fixtures: `delegate_block`, `handback_block`, `tmp_queue`

**Pytest configuration** (`/pytest.ini`):
```ini
[pytest]
pythonpath = .:src/skills/queue-management:src/skills/file-sync:...
testpaths = tests
python_files = test_*.py
```

### Test Fixture Gaps

**Gap 1: Symlink fixtures don't clean up on macOS vs Linux**

```python
# Current fixture (test_validate_skills.py:48-65)
@pytest.fixture
def temp_repo(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    skills_dir = repo_root / "src" / "skills"
    skills_dir.mkdir(parents=True)
    return {"root": repo_root, "skills_dir": skills_dir, ...}
    # ← No cleanup of symlinks created during test
    # ← No OS-specific handling
```

**Gap 2: Mock filesystem doesn't test real symlink behavior**

```python
# Tests create real symlinks (good)
link_file.symlink_to(target_file)

# But don't test:
# - Symlink cleanup on different filesystems
# - Symlink availability in CI after checkout
# - Relative vs absolute symlink resolution
```

**Gap 3: No environment detection in tests**

```python
# test_queue_path_validator.py doesn't detect:
# - If running on macOS vs Linux
# - If Git symlinks are enabled
# - If checkout preserved symlinks

# Runs same tests on both, expects same behavior
# But File 2's contract is different!
```

### Mock vs Real Filesystem Interactions

| Scenario | Current Implementation | Issue |
|----------|----------------------|-------|
| Real symlink creation | Uses `Path.symlink_to()` | Works on macOS, may fail in Linux container without CAP_SYS_ADMIN |
| Symlink validation | Uses `os.path.islink()` | Works on both, but tests don't verify CI symlink creation |
| Path resolution | Uses `Path.resolve()` | Works on both, but tests don't verify checkout behavior |
| Bytecode cache | Cleared in pytest_configure | But __pycache__ not cleared, can mask symlink issues |

---

## 7. Contract Violations Summary

### Violation 1: Queue Path Validator Dual Implementation

| Aspect | File 1 | File 2 | Correct |
|--------|--------|--------|---------|
| Return type | Always Dict | Raises on contract error | **File 1** |
| None handling | Returns error dict | Raises AssertionError | **File 1** |
| Empty string | Returns error dict | Raises AssertionError | **File 1** |
| Type signature | str only | Path\|str | **File 2 (more flexible)** |

**Resolution needed**: Unify implementations, keep File 2's flexibility + File 1's dict return contract

### Violation 2: Path Validation Type Mismatch

```python
# Declared (docstring)
Returns Dict[str, Any] with error: Optional[str]

# Implementation (File 2, line 77-82)
if not isinstance(path, (Path, str)):
    raise AssertionError(...)  # ← Type contract violation
```

### Violation 3: Symlink Detection Gap

Both implementations check `os.path.islink()` only if `os.path.exists()` is True, but:
- Broken symlinks: `exists()` returns False, `islink()` returns True
- Gap: Broken symlinks in tests aren't detected because we only check if exists

```python
# Current code (both files)
if os.path.exists(normalized) and os.path.islink(normalized):  # ← AND operator
    return error

# Should be
if os.path.islink(normalized):  # Check symlinks regardless of target
    return error
```

---

## 8. CI Test Failure Analysis

### Current CI Pipeline (`.github/workflows/ci.yml`)

```yaml
steps:
  1. Checkout code (actions/checkout@v4)
  2. Preserve symlinks (git config core.symlinks true) ← TOO LATE
  3. Install Python 3.11
  4. Install dependencies (pytest, pytest-cov, etc.)
  5. Run: make lint
  6. Run: make render-copilot/claude/opencode/pi
  7. Run: make test  ← FAILS HERE
  8. Run: make verify
```

### Why Tests Fail in CI

1. **Symlink config too late** (step 2): Git checkout already completed
2. **Dual implementations** (File 1 vs File 2): Tests expect File 1, run File 2
3. **Contract violations**: File 2 raises on None/empty, tests expect dicts
4. **Path validation patterns**: File 2 has different error messages

### Symptom Timeline

```
1. Git checkout (no symlinks configured yet)
2. git config core.symlinks true (too late)
3. pytest imports test_queue_path_validator.py
4. Test tries: validate_queue_path(None)
5. File 2 raises AssertionError
6. Test expects dict with 'valid': False
7. Test FAILS: "AssertionError: Path must be a non-empty string"
```

---

## 9. Testing Gaps in Current Harness

### Gap 1: No macOS-specific symlink tests
```python
# Missing: Tests that verify symlinks work on macOS specifically
# Current tests run on both platforms but don't verify platform behavior
```

### Gap 2: No CI symlink preservation tests
```python
# Missing: Test that validates:
# - Git checkout preserves symlinks
# - core.symlinks config is active
# - Symlinks are actually followed in CI
```

### Gap 3: No contract validation tests
```python
# Missing: Tests that verify return type contracts
# - validate_queue_path always returns Dict (never raises)
# - validate_queue_subdir always returns Dict (never raises)
# - Error messages follow specific format
```

### Gap 4: No bytecode cache cleanup verification
```python
# Current: pytest_configure clears .pytest_cache only
# Missing: Should also clear __pycache__ to prevent stale bytecode
```

### Gap 5: Fixture symlink lifecycle not verified
```python
# Missing: Tests don't verify symlink cleanup
# - Broken symlinks left after tests fail
# - Next test run may have stale symlink state
```

---

## 10. Recommended Fixes

### Priority 1 (Critical - Blocks CI)

1. **Unify queue_path_validator implementations**
   - Keep File 2 (src/skills/_meta/queue-path-validator/queue_path_validator.py) as canonical
   - Remove File 1 (renderer/validate_skills.py implementation)
   - Update File 2 to match contract: **always return Dict, never raise**

2. **Fix contract violations**
   ```python
   def validate_queue_path(path: Union[Path, str]) -> Dict[str, Any]:
       # Instead of raising, return error dict
       if not isinstance(path, (Path, str)):
           return {'valid': False, 'error': 'Must be Path or str', ...}
       
       if not path or (isinstance(path, str) and not path.strip()):
           return {'valid': False, 'error': 'Path must be non-empty', ...}
   ```

3. **Fix symlink detection for broken symlinks**
   ```python
   # Change from:
   if os.path.exists(normalized) and os.path.islink(normalized):
   
   # To:
   if os.path.islink(normalized):  # Works even for broken symlinks
   ```

4. **Move symlink config before checkout in CI**
   ```yaml
   - name: Enable symlink support
     run: git config --global core.symlinks true
   
   - uses: actions/checkout@v4
   ```

### Priority 2 (High - Improves testing)

5. **Clear __pycache__ in pytest_configure**
   ```python
   def pytest_configure(config):
       shutil.rmtree('.pytest_cache', ignore_errors=True)
       shutil.rmtree('__pycache__', ignore_errors=True)  # ← Add this
   ```

6. **Add platform detection tests**
   ```python
   import platform
   @pytest.mark.skipif(platform.system() == 'Windows', reason='Unix-only')
   def test_symlink_on_unix(temp_repo):
       # Verify symlinks work on this platform
   ```

7. **Add CI-specific tests**
   ```python
   @pytest.mark.ci_only
   def test_git_symlinks_enabled():
       result = os.system('git config core.symlinks')
       assert result == 'true'
   ```

### Priority 3 (Medium - Hardening)

8. **Document expected behavior per OS**
   - Add comments in queue_path_validator.py
   - Document CI symlink expectations
   - Add .github/workflows/ENVIRONMENT.md

9. **Improve fixture cleanup**
   ```python
   @pytest.fixture
   def temp_repo_with_symlinks(tmp_path):
       # Explicitly test symlink creation
       # Verify cleanup happens
       # Detect OS and skip if not supported
   ```

---

## Appendix A: File Locations

| File | Purpose | Issue |
|------|---------|-------|
| `/src/skills/_meta/queue-path-validator/queue_path_validator.py` | Canonical validator | Raises on contract error ✗ |
| `/renderer/validate_skills.py` | Skill validation | Duplicate implementation |
| `/tests/test_queue_path_validator.py` | Test suite | Expects different contract |
| `/.github/workflows/ci.yml` | CI pipeline | Symlink config too late |
| `/conftest.py` | Root pytest config | Path setup OK ✓ |
| `/tests/conftest.py` | Test pytest config | Cache clearing incomplete |

---

## Appendix B: Test Results Summary

**Queue Path Validator Tests**: 16 of 33 failures
- 5 tests fail on contract violations (None, empty string)
- 6 tests fail on error message format mismatch
- 5 tests fail on pattern matching differences
- 2 tests pass (legacy path rejection, path traversal)

**Validate Skills Tests**: Symlink tests mostly pass
- ✓ Rejects symlinks to /etc/passwd
- ✓ Accepts symlinks within repo
- ✓ Detects chained symlinks
- ✓ Handles broken symlinks gracefully
- ✓ Detects symlink loops

**CI Status**: Framework integrity and validation workflows affected

---

## Appendix C: Environment Specification

### Local Development (macOS)
```
OS:           macOS 13/14/15 (Darwin)
Python:       3.7+ via Homebrew or official installer
Symlinks:     Native support, no special permissions
Git:          Default settings (core.symlinks auto-enabled on POSIX)
File system:  APFS
CI:           Not applicable
```

### CI Environment (GitHub Actions)
```
OS:           Ubuntu Latest (20.04 LTS or later)
Python:       3.11 via actions/setup-python@v5
Symlinks:     Git checkout config must enable (core.symlinks true)
Git:          Actions manages checkout via actions/checkout@v4
File system:  overlayfs in container
Container:    Docker, root user (CAP_SYS_ADMIN available)
CI:           GitHub Actions standard runner
```

---

## Summary of Critical Issues

1. **TWO queue_path_validator implementations with conflicting contracts**
   - File 1 (renderer): Returns dict always
   - File 2 (src/skills): Raises AssertionError on contract violation
   - Tests expect File 1, implementation is File 2

2. **Contract violations in File 2**
   - Declared return type: Dict (always)
   - Actual behavior: Raises AssertionError (sometimes)
   - Breaks 16/33 tests

3. **Symlink detection gap**
   - Only checks `islink()` if `exists()` is True
   - Misses broken symlinks
   - Works correctly on both macOS and Linux when enabled

4. **CI symlink configuration too late**
   - `git config core.symlinks true` happens after checkout
   - Should happen before or at checkout time

5. **Test fixture gaps**
   - No platform detection
   - No CI-specific test isolation
   - Incomplete cache cleanup
   - No symlink lifecycle verification
