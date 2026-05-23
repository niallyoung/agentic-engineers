# Plan: Fix Path Resolution xfail Tests

## Executive Summary
Six tests in `tests/test_render_pi_dev_args.py` are marked as `@pytest.mark.xfail` with the reason "CI environment has different path resolution than local dev environment". However, all tests are **XPASS** (unexpectedly passing) both locally and in CI. This indicates:
1. The underlying path resolution issue has already been fixed
2. The xfail markers are no longer needed
3. Removing them will achieve 100% passing tests

**Current Status:**
- Local test run: `7 passed, 6 xpassed` (expecting all 13 to pass)
- CI test run: Same pattern
- Goal: Remove xfail markers and achieve `13 passed, 0 xfailed, 0 xpassed`

## Investigation Findings

### 1. Commit Context
**Commit 1941b3d** added xfail markers with commit message:
```
fix: mark render_pi_dev_args tests as xfail for CI
CI environment has different path resolution than local dev environment.
Tests pass locally but fail in CI. Marked as xfail since feature works
in both environments.
```

This suggests the markers were added as a "band-aid" to suppress known failures without fixing the root cause.

### 2. Tests Marked as xfail
1. `test_help_flag_works` — Tests --help flag
2. `test_no_args_uses_defaults` — Tests default arguments
3. `test_single_positional_arg_rejected` — Tests single arg rejection
4. `test_pi_path_no_longer_heuristic` — Tests that /.pi heuristic is rejected
5. `test_uninstall_with_dest_flag` — Tests --uninstall with --dest
6. `test_uninstall_flag_without_dest` — Tests --uninstall without --dest

### 3. Path Resolution Logic Analysis
**render-pi-dev.py (lines 412-450)** shows the current logic:

```python
# Resolve source directory: Priority: --src > src_pos (with dest_pos) > default
if args.src is not None:
    src_dir = Path(args.src)
elif args.src_pos is not None and args.dest_pos is not None:
    # Two positional args: unambiguous
    src_dir = Path(args.src_pos)
elif args.src_pos is not None and args.dest_pos is None:
    # Single positional arg: REJECTED with clear error
    print("⚠️  Ambiguous invocation...", file=sys.stderr)
    return 2
else:
    src_dir = default_src

# Resolve destination: Priority: --dest > dest_pos (with src_pos) > default
if args.dest is not None:
    dest_dir = Path(args.dest)
elif args.src_pos is not None and args.dest_pos is not None:
    dest_dir = Path(args.dest_pos)
else:
    dest_dir = default_dest

# Ensure paths are absolute (KEY FIX)
src_dir = src_dir.resolve()
dest_dir = dest_dir.resolve()
```

**Key observations:**
1. Uses `Path.resolve()` to make paths absolute (platform-independent)
2. Clear rejection of single positional args (not a heuristic)
3. Logic is identical in local and CI environments
4. No environment-specific path handling

### 4. Why Tests Pass
The path resolution logic is now environment-agnostic:
- `Path.resolve()` works consistently on macOS (local) and Linux (CI)
- No reliance on shell expansion or environment variables
- No heuristic logic that differs by OS
- Clear error messages that are consistent

### 5. Test Environment Differences Checked
**Local (macOS):**
- Python 3.7.4
- Uses tmp_path fixture (pytest temporary directories)
- Subprocess calls to the script

**CI (Ubuntu Linux via GitHub Actions):**
- Python 3.11
- Same tmp_path fixture
- Same subprocess calls
- Same pytest configuration (pytest.ini with pythonpath = .)

**Conclusion:** The environment difference mentioned in the xfail reason no longer exists or never existed as a problem.

## Root Cause of Original Issue (Historical)

The original problem was likely one of:
1. **Heuristic path detection** — Early version may have tried to guess if a single path was src or dest based on naming (e.g., containing "/.pi")
2. **Default path resolution** — Differences in how `Path.home()` resolved `~` on different systems
3. **Script location assumptions** — Differences in how `Path(__file__).parent` resolved relative to script location

The current code has fixed all of these with explicit, deterministic logic.

## Solution

### Phase 1: Remove xfail Markers
**File:** `tests/test_render_pi_dev_args.py`
- Remove `@pytest.mark.xfail(reason="CI environment path resolution differs from local")` from 6 tests
- Keep test logic unchanged (tests are correct)
- Result: 6 tests will show as PASS instead of XPASS

### Phase 2: Verify No Configuration Changes Needed
**Files checked:**
- `pytest.ini` — Already correct (pythonpath = .)
- `.github/workflows/ci.yml` — Already correct (runs `make test`)
- `Makefile` — Already correct (test target uses python3 -m pytest)
- No environment-specific path setup needed

### Phase 3: Final Verification
Run: `make test` locally
Expected: `13 passed, 0 xfailed, 0 xpassed`

Run: GitHub Actions CI
Expected: `13 passed, 0 xfailed, 0 xpassed`

## Files to Modify

1. **tests/test_render_pi_dev_args.py**
   - Remove 6 xfail markers
   - Lines: 31, 41, 66, 74, 84, 123
   - Test logic remains unchanged

## Success Criteria

✅ All 13 tests in test_render_pi_dev_args.py pass
✅ No xfail or xpass markers
✅ Tests pass locally on macOS
✅ Tests pass in CI (GitHub Actions on Ubuntu)
✅ Path resolution is deterministic and environment-agnostic
✅ No additional configuration changes needed

## Risk Assessment

**Risk Level: LOW**
- Test logic is already correct (tests pass)
- Only removing markers, not changing logic
- No changes to render-pi-dev.py script itself
- No framework or configuration changes

**Testing Strategy:**
1. Remove markers
2. Run locally: `python3 -m pytest tests/test_render_pi_dev_args.py -v`
3. Run full suite: `make test`
4. Push to CI and verify GitHub Actions passes
