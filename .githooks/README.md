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
   - Patterns: API keys, passwords, tokens, AWS keys, Anthropic keys (`sk-ant-`),
     GitHub tokens (`ghp_`/`gho_`/`ghu_`/`ghs_`/`ghr_`, `github_pat_`), `client_secret`
     assignments, PEM private-key headers, literal-valued sensitive env vars
   - Checks: the staged content of every added, copied, modified or **renamed**
     file (`--diff-filter=ACMR`); filenames are NUL-separated so names with spaces
     are scanned. Binary files are skipped by content; executable scripts are scanned.
   - **Blocks commit:** ❌ Yes (secrets in git = permanent exposure)

3. **File Permissions**
   - Rejects: executable bits on .md, .yaml, .yml, .txt, .json, .jsonc files
   - Rationale: documentation should never be executable
   - **Blocks commit:** ❌ Yes (permissions errors indicate accidents)

**Additional Checks (beyond the 3 core):**

- **Agent Frontmatter:** Consistency between src/agents/*-agent.md model/effort and src/AGENTS.md
- **YAML/JSON Validation:** Well-formedness checks
- **Bypass Markers:** Warns if --no-verify or SKIP_HOOKS=1 in committed code
- **Bytecode:** Rejects staged `.pyc` files
- **Model Registry:** Staged `src/agents/*-agent.md` models must be known registry IDs (`scripts/models.py is-known`); when registry-related files are staged, `models.py check` (shape, fallback policy, family `min_pin` floor, pin_history, generated targets current) and `sync --check` must pass. No version allowlist lives in the hook; needs PyYAML (fails loudly without it)
- **OpenCode Config:** Validates opencode.jsonc structure (when staged)

> **Hook cleanup:** removed the DELEGATE/HANDBACK protocol-file validation
> (pre-commit) and the DELEGATE/HANDBACK commit-message validation (commit-msg),
> since no protocol YAML is ever committed; the orchestration/ re-introduction
> checks (pre-commit and pre-push; the guard now lives only in
> `scripts/validate-spec-constraints.py`); and the warn-only bytecode timestamp and
> test-without-implementation sub-checks.
>
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
- **Spec Compliance:** `scripts/validate-spec-constraints.py`
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

There is exactly **one** bypass variable: `SKIP_HOOKS=1`. It applies to every
hook (use sparingly!). The former `GIT_SKIP_HOOKS`, `BYPASS_HOOK_VALIDATION` and
`SKIP_COMMIT_MSG_HOOK` variables no longer do anything.

```bash
# Skip pre-commit (commit without validation). commit-msg still requires a
# documented reason of 10+ characters in the message (see below).
SKIP_HOOKS=1 git commit -m "fix: hotfix" -m "SKIP_HOOKS: P0 outage, rolling back release 1.2.3"

# Skip pre-push (push without validation)
SKIP_HOOKS=1 git push
```

Under `SKIP_HOOKS=1`: pre-commit and pre-push exit immediately (including the model
registry checks); post-merge skips; commit-msg skips its format and audit checks but
still fails unless the message carries `SKIP_HOOKS: <reason>` (or `reason:`,
`emergency:`, `justification:`) with at least 10 characters after the colon.

**Guidelines for emergency bypass:**
- ✅ Use: Critical hotfix, fire, data loss prevention
- ✅ Document: Always add reason to commit message
- ❌ Don't use: Avoiding tests, hiding linting issues
- ⚠️ Escalate: Report to Quality Engineer after push

## Hook Details

### Hook File Locations

- **pre-commit:** `.githooks/pre-commit` (staged-file validation)
- **pre-push:** `.githooks/pre-push` (agent/workflow/SPEC validation — no test run)
- **commit-msg:** `.githooks/commit-msg` (enforces commit message format and the `SKIP_HOOKS` reason rule; a `pin_history` rewrite in `config/models.yaml` produces a warning, never a failure; no pin trailer is required, see docs/SPEC.md Model Pin Change)
- **post-merge:** `.githooks/post-merge` (documentation-drift check on `docs/SPEC.md` and `src/AGENTS.md`, informational only)

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

- **SKIP_HOOKS=1**: the single documented bypass for all hooks (emergency only; see
  Emergency Override above). There are no per-check bypass variables.

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

---

- `config/models.yaml` + `scripts/models.py`: the model pin registry the hooks enforce
- `docs/SPEC.md`: Architecture and constraints enforced by hooks
- `docs/AGENTS.md`: Agent definitions and SDLC guidelines
- `Makefile`: Hook installation via `make setup`

---

**Last Updated:** 2026-05-30  
**Maintained By:** Senior Engineer  
**Status:** Production (enforces SDLC gates)
