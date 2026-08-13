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

**Enforces (3 core checks, staged files only):**

1. **Syntax Validation**
   - Python: `python3 -m py_compile` (all staged .py files)
   - Shell: `bash -n` (all staged .sh/.bash files)
   - Optional: `shellcheck` if installed (recommendations only)
   - **Blocks commit:** ❌ Yes (syntax errors are hard failures)

2. **Secrets Detection**
   - Patterns: API keys, passwords, tokens, AWS keys, literal-valued sensitive env vars
   - Checks: all staged files (skips binaries/images)
   - **Blocks commit:** ❌ Yes (secrets in git = permanent exposure)

3. **File Permissions**
   - Rejects: executable bits on .md, .yaml, .yml, .txt, .json, .jsonc files
   - Rationale: documentation should never be executable
   - **Blocks commit:** ❌ Yes (permissions errors indicate accidents)

**Additional Checks (beyond the 3 core):**

- **SPEC Constraints:** No external scripts in orchestration/scripts/ or orchestration/config/*.cron
- **Agent Frontmatter:** Consistency between src/agents/*-agent.md model/effort and src/AGENTS.md
- **YAML/JSON Validation:** Well-formedness checks
- **Bypass Markers:** Warns if --no-verify or SKIP_HOOKS=1 in committed code
- **Orphaned Bytecode:** Detects .pyc without .py source
- **Model Naming:** Enforces locked model set (from .githooks/LOCKED_MODELS.sh)
- **OpenCode Config:** Validates opencode.jsonc structure (when staged)
- **DELEGATE/HANDBACK Protocol:** Required fields on staged protocol YAML files

> **2026-08-13 infra consolidation:** removed the former pylint and mypy
> checks (both optional — skipped entirely when the tool wasn't installed —
> and warn-only even when they ran, so neither could ever block a commit)
> and the contract-validation heuristic (also warn-only). See
> `.githooks/pre-commit`'s inline NOTEs at each removal site.

### pre-push

**When:** Runs automatically before `git push` (including `git push --force`)

**Duration:** A few seconds — deliberately does **not** re-run the test suite
or a render pass; both duplicate `ci.yml`, which runs them as the real,
blocking gate within minutes of every push.

**Enforces:**

- **Agent YAML Validation:** All src/agents/*.md have valid YAML frontmatter
- **Workflow Files:** GitHub Actions YAML (.github/workflows/) well-formedness
- **Documentation:** SPEC.md, AGENTS.md, README.md existence and structure
- **Spec Compliance:** No SPEC.md drift (external scripts, cron files,
  Makefile violations); `scripts/validate-spec-constraints.py`
- **Agent Definition Verification:** `.agents_verification_sha` matches
  `src/AGENTS.md` content
- **Gitconfig Credential Guard:** No embedded tokens in `~/.gitconfig` /
  `~/.git-credentials`
- **Main/master push warning:** advisory only, does not block

> **2026-08-13 infra consolidation:** removed the DELEGATE/HANDBACK artifact
> scan (scanned `artifacts/delegates/`, a filesystem-queue path that has
> never existed since dispatch became direct sub-agent spawn — always a
> no-op), the render-pipeline step (referenced a `render-pi` Makefile target
> that no longer exists — always failed and only ever warned), and the full
> test-suite run (warn-only; could never actually block a push, and cost up
> to 180s for that). Run `make test` yourself before pushing — the pre-push
> hook no longer does it for you. See `.githooks/pre-push`'s inline NOTEs at
> each removal site.

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

- **pre-commit:** `.githooks/pre-commit` (staged-file validation)
- **pre-push:** `.githooks/pre-push` (agent/workflow/SPEC validation — no test run)
- **commit-msg:** `.githooks/commit-msg` (enforces commit message format)
- **post-merge:** `.githooks/post-merge` (documentation-drift check, informational only)

### Performance Targets

| Hook | Target | Status |
|------|--------|--------|
| pre-commit | < 5 seconds | ✅ Staged files only |
| pre-push | < 5 seconds | ✅ No test/render pass |
| commit-msg | < 1 second | ✅ Fast |
| post-merge | < 5 seconds | ✅ Fast |

**Note:** neither hook runs the test suite — `ci.yml` is the test gate, and
runs within minutes of every push. Run `make test` yourself before pushing
if you want local confidence ahead of CI.

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
- **BYPASS_HOOK_VALIDATION=true**: Skip agent frontmatter / opencode.jsonc / protocol validation

## Troubleshooting

### "Hook failed" errors

1. **Pre-commit syntax errors:**
   - Check Python: `python3 -m py_compile src/file.py`
   - Check Shell: `bash -n scripts/file.sh`

2. **Pre-commit secrets detected:**
   - Remove credentials from code
   - Move to .env file or secrets manager
   - Use git filter-branch to remove from history (if critical)

3. **Test failures (caught by CI, not pre-push):**
   - The pre-push hook does not run the test suite — run `make test` locally
     before pushing for confidence ahead of CI
   - Review CI's "Test" step output if a push fails there

4. **Pre-push spec violations:**
   - Check for external scripts in orchestration/scripts/ or cron files in
     orchestration/config/
   - Ensure Makefile follows SPEC.md patterns (no direct script invocations
     outside renderer/scripts/)

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

## CI Environment Simulation (Local Testing Before Push)

**Before** relying on GitHub Actions CI, test your changes locally with Docker:

```bash
# Test in container that matches GitHub Actions environment
make test-ci                # Informational run (first time OK to fail)
make test-ci-force          # Strict: all tests must pass
make test-ci-shell          # Interactive debug shell in container
```

**What this catches that pre-push hooks don't:**
- **Symlink issues:** Tests verify symlink creation, resolution, relative paths, and path traversal security
- **Path platform differences:** Container tests validate paths with spaces, special chars, absolute/relative resolution
- **File permissions:** Tests verify read/write/execute permissions on files and directories
- **Python 3.11 specific features:** Tests confirm async/await, pathlib.match(), typing module, exception groups
- **System dependencies:** Validates git, python3, pytest, pyyaml availability in container

**Workflow:**
```bash
# 1. Make local changes
# 2. Pre-commit hook runs (staged files, a few seconds)
# 3. Run the test suite yourself (pre-push does not run it): make test
# 4. Still want CI-exact confidence? Test in container first
make test-ci-force

# 5. If green, push
git push
```

**Container tests included (46 total):**
- TestContainerSymlinks (5 tests): symlink operations
- TestContainerFilePaths (6 tests): path resolution
- TestContainerFilePermissions (6 tests): permission handling
- TestPython311Compatibility (6 tests): Python 3.11 features
- TestSystemDependencies (4 tests): required tools
- TestDockerfileBuild (5 tests): Dockerfile validation
- TestMakefileTargets (5 tests): CI targets
- TestGitConfiguration (2 tests): Git setup
- TestPlatformDetection (3 tests): OS detection
- TestContainerIntegration (2 tests): full integration
- TestErrorMessages (1 test): error handling

See `tests/test_ci_container_environment.py` for full test suite.

---

- `.githooks/LOCKED_MODELS.sh`: Model naming enforcement configuration
- `.githooks/PRE-PUSH.md`: Detailed pre-push hook implementation notes
- `docs/SPEC.md`: Architecture and constraints enforced by hooks
- `docs/AGENTS.md`: Agent definitions and SDLC guidelines
- `Makefile`: Hook installation via `make setup`

---

**Last Updated:** 2026-05-30  
**Maintained By:** Senior Engineer  
**Status:** Production (enforces SDLC gates)
