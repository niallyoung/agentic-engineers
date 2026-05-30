# Git Hooks Documentation

This directory contains Git hooks that enforce quality gates and prevent common errors from being committed to the repository.

## Installation

Hooks are automatically installed by running:

```bash
make setup
```

This command:
- Configures Git to use `.githooks/` directory: `git config core.hooksPath .githooks`
- Makes all hook scripts executable
- Verifies hook functionality

## Available Hooks

### pre-commit

**When:** Runs automatically before `git commit`

**Duration:** < 3 seconds (optimized for minimal dev friction)

**Enforces (6 core checks):**

1. **Syntax Validation**
   - Python: `python3 -m py_compile` (all staged .py files)
   - Shell: `bash -n` (all staged .sh/.bash files)
   - Optional: `shellcheck` if installed (recommendations only)
   - **Blocks commit:** ❌ Yes (syntax errors are hard failures)

2. **Linting (Python Style)**
   - Uses: `pylint` (if available)
   - Suppresses: missing-docstring, line-too-long, too-many-args, fixme (too strict)
   - Checks: staged Python files (excluding tests)
   - **Blocks commit:** ⚠️ Warning only (informational, not blocking)

3. **Type Checking**
   - Uses: `mypy --ignore-missing-imports` (if available)
   - Checks: staged source files (excluding tests, vendor code)
   - **Blocks commit:** ⚠️ Warning only (mypy can be noisy with partial stubs)

4. **Secrets Detection**
   - Patterns: API keys, passwords, tokens, AWS keys, env vars
   - Checks: all staged files (skips binaries/images)
   - **Blocks commit:** ❌ Yes (secrets in git = permanent exposure)

5. **Contract Validation**
   - Checks: decorator mismatches (@property with params, @staticmethod with self)
   - Pattern matching: basic decorator patterns
   - **Blocks commit:** ⚠️ Warning only (false positives possible)

6. **File Permissions**
   - Rejects: executable bits on .md, .yaml, .yml, .txt, .json, .jsonc files
   - Rationale: documentation should never be executable
   - **Blocks commit:** ❌ Yes (permissions errors indicate accidents)

**Additional Checks (beyond the 6 core):**

- **SPEC Constraints:** No external scripts in orchestration/scripts/ or orchestration/config/*.cron
- **Agent Frontmatter:** Consistency between src/agents/*-agent.md and docs/AGENTS.md
- **YAML/JSON Validation:** Well-formedness checks
- **Bypass Markers:** Warns if --no-verify or SKIP_HOOKS=1 in committed code
- **Orphaned Bytecode:** Detects .pyc without .py source
- **Queue Path Centralization:** Enforces ~/.agentic-engineers/ (blocks legacy paths)
- **Model Naming:** Enforces locked model set (from .githooks/LOCKED_MODELS.sh)
- **OpenCode Config:** Validates opencode.jsonc structure

### pre-push

**When:** Runs automatically before `git push` (including `git push --force`)

**Duration:** Variable (tests can be slow, typically 30-60 seconds)

**Enforces (3 core checks):**

1. **Full Test Suite**
   - Command: `make test` or `pytest tests/`
   - Requirements: All 3514+ tests must pass
   - Skips: test_git_hooks.py (to avoid hook recursion)
   - **Blocks push:** ❌ Yes (test failures prevent deployment)

2. **Spec Compliance**
   - Checks: No SPEC.md drift (external scripts, cron files, Makefile violations)
   - Validates: All DELEGATE/HANDBACK protocol files
   - **Blocks push:** ❌ Yes (spec violations = architecture violations)

3. **No Linting Errors**
   - Verifies: Committed code passes pre-commit linting checks
   - Skips: pytest execution if SKIP_PYTEST=1 (for testing hook itself)
   - **Blocks push:** ⚠️ Advisory (warnings from pre-commit are not blocking)

**Additional Checks (beyond the 3 core):**

- **Agent YAML Validation:** All src/agents/*.md have valid YAML frontmatter
- **Workflow Files:** GitHub Actions YAML (.github/workflows/) well-formedness
- **Documentation:** SPEC.md, AGENTS.md, README.md existence and structure
- **DELEGATE/HANDBACK Protocol:** Valid YAML and required fields
- **Render Pipeline:** All harnesses (copilot, claude, opencode, pi, specs) render successfully
- **Concurrent Tests:** Race condition guard (test_concurrent_invocations)
- **Queue Path Validation:** DELEGATE/HANDBACK files use canonical queue paths
- **Agent Definition Verification:** .agents_verification_sha matches AGENTS.md content

## Emergency Override

Both hooks can be bypassed for emergency situations (use sparingly!):

```bash
# Skip pre-commit (commit without validation)
SKIP_HOOKS=1 git commit -m "Emergency: <reason>"

# OR use consistent environment variable
GIT_SKIP_HOOKS=1 git commit -m "Emergency: <reason>"

# Skip pre-push (push without tests/validation)
SKIP_HOOKS=1 git push

# OR use consistent environment variable
GIT_SKIP_HOOKS=1 git push
```

**Guidelines for emergency bypass:**
- ✅ Use: Critical hotfix, fire, data loss prevention
- ✅ Document: Always add reason to commit message
- ❌ Don't use: Avoiding tests, hiding linting issues
- ⚠️ Escalate: Report to Quality Engineer after push

## Hook Details

### Hook File Locations

- **pre-commit:** `.githooks/pre-commit` (~200 lines, comprehensive validation)
- **pre-push:** `.githooks/pre-push` (~560 lines, test + spec validation)
- **commit-msg:** `.githooks/commit-msg` (enforces commit message format)
- **post-merge:** `.githooks/post-merge` (updates dependencies after merge)

### Performance Targets

| Hook | Target | Actual | Status |
|------|--------|--------|--------|
| pre-commit | < 3 seconds | ~1-2s (typical) | ✅ Optimized |
| pre-push | < 10 seconds | ~30-60s (tests) | ✅ Tests slow OK |
| commit-msg | < 1 second | < 0.5s | ✅ Fast |
| post-merge | < 5 seconds | ~2-3s | ✅ Fast |

**Note:** pre-push includes full test suite, which can take 30-60 seconds. This is acceptable because tests are the primary quality gate.

## Configuration

### Check Current Status

```bash
# Verify hooks are installed
git config core.hooksPath

# Should output: .githooks
```

### Disable All Hooks (Development Only)

```bash
# Temporarily disable hooks
git config core.hooksPath ""

# Re-enable hooks
git config core.hooksPath .githooks
```

### Per-Hook Control

Some hooks support environment variables to disable specific checks:

- **SKIP_HOOKS=1**: Bypass all hook checks (emergency only)
- **GIT_SKIP_HOOKS=1**: Alias for SKIP_HOOKS=1
- **SKIP_PYTEST=1**: Skip pytest in pre-push (for testing hook itself)
- **BYPASS_HOOK_VALIDATION=true**: Skip agent frontmatter validation

## Troubleshooting

### "Hook failed" errors

1. **Pre-commit syntax errors:**
   - Check Python: `python3 -m py_compile src/file.py`
   - Check Shell: `bash -n scripts/file.sh`

2. **Pre-commit secrets detected:**
   - Remove credentials from code
   - Move to .env file or secrets manager
   - Use git filter-branch to remove from history (if critical)

3. **Pre-push test failures:**
   - Run locally: `make test`
   - Review error output
   - Fix failing tests before pushing

4. **Pre-push spec violations:**
   - Check for external scripts in orchestration/
   - Verify DELEGATE/HANDBACK files in queue/
   - Ensure Makefile follows SPEC.md patterns

### Hooks Not Running

```bash
# Re-install hooks
make setup

# Verify they're executable
ls -la .githooks/pre-commit .githooks/pre-push

# Should show: -rwxr-xr-x (executable)
```

### Slow Pre-Commit

- Pre-commit targets < 3 seconds
- Profiling: Time individual checks
- Possible causes: Large bytecode cache, slow file system
- Solution: `rm -rf __pycache__` and try again

## Integration with Framework

- **Make setup:** Installs hooks and verifies Git configuration
- **CI/CD:** GitHub Actions runs equivalent checks (`.github/workflows/`)
- **Quality Engineer:** Reviews test failures and SPEC violations
- **Senior Engineer:** Maintains hook scripts and performance

## See Also

- `.githooks/LOCKED_MODELS.sh`: Model naming enforcement configuration
- `.githooks/PRE-PUSH.md`: Detailed pre-push hook implementation notes
- `docs/SPEC.md`: Architecture and constraints enforced by hooks
- `docs/AGENTS.md`: Agent definitions and SDLC guidelines
- `Makefile`: Hook installation via `make setup`

---

**Last Updated:** 2026-05-30  
**Maintained By:** Senior Engineer  
**Status:** Production (enforces SDLC gates)
