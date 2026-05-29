# Git Workflow and Development Standards

Git workflow, authentication setup, and commit/push mechanics for the agentic-engineers framework.

## Overview

**Trunk-based development**: commit and push directly to `main` with local quality gates. Remote pushes trigger GitHub Actions (expensive E2E + deploy), while local hooks handle fast feedback.

```
edit code
  → git add + git commit   [pre-commit hook: lint + test]
  → git push               [pre-push hook: E2E + diff review + "Push to main? [y/N]"]
  → main on GitHub ✅      [GitHub Actions: deploy dev + deploy prod + tag]
```

## Git Authentication Setup

**Use your Git configuration of choice (SSH or HTTPS).** The framework supports both authentication methods.

### Remote URLs

Configure your remote based on your organization's Git authentication policy:

```bash
# Verify current remote
git remote get-url origin

# If you use SSH:
git remote set-url origin git@github.com:{your-org}/REPO.git

# If you use HTTPS:
git remote set-url origin https://github.com/{your-org}/REPO.git
```

### Authentication Configuration

Whatever Git authentication method your organization requires (SSH keys, HTTPS tokens, OAuth, etc.), ensure it is properly configured before pushing.

If `git push` fails with a permission error:
- Verify your Git credentials are configured
- Ensure the credentials have appropriate permissions on the remote repository
- Consult your organization's Git authentication documentation

## Commit & Push Workflow

### 1. Edit and commit

```bash
# Local work — lint/test run automatically
git add <files>
git commit -m "feat|fix|refactor|test|docs|chore(scope): description"
```

**Pre-commit hook runs:**
- `make lint` — golangci-lint, go fmt, go vet
- `make test` — unit tests only
- Commit message validation — Conventional Commits

If hook fails, fix the issue and commit again (not amend).

### 2. Push to main

```bash
# Non-interactive (skip diff review + confirm)
ERS_AUTO_PUSH=1 git push origin main

# Interactive (shows diff + asks "Push to main? [y/N]")
git push origin main
```

**Pre-push hook runs:**
- `make test` again (redundant but fast — cached)
- E2E tests ({service-name} only)
- Color diff review + confirmation

**NEVER use `--no-verify`** — hooks are your local quality gate.

### 3. GitHub Actions deploys

Once push lands on main, GitHub Actions runs:
- Lint + test (redundant, cached)
- Deploy dev
- Deploy prod
- Tag release (semantic versioning)

This is the "expensive CI" — offloaded to the cloud so your local push is fast.

## Makefile Standard Targets

All Go services follow the same pattern:

```bash
make describe    # Print service context (name, version, etc)
make lint        # golangci-lint + go fmt/vet
make test        # Unit tests only
make build       # Compile binaries (Linux for Lambda)
make deploy      # `cdk deploy --all --require-approval never`
make verify      # lint + test (no build/deploy)
make clean       # Remove build artifacts
make all         # describe → lint → test → build (no deploy)
```

**Example workflow:**

```bash
# During development
make verify      # Fast local feedback (lint + test)

# Before push
make all         # Full build pipeline (verify + build)

# After push succeeds
git push origin main
```

## Branch Policy

- **No feature branches for routine work** — push direct to main
- **Feature branches only for:**
  - Collaborative changes requiring PRs
  - Sensitive/risky changes needing extra review
  - CI/CD pipeline changes (require `workflow` scope; not available in standard OAuth tokens)

**If you must use a feature branch:**

```bash
git checkout -b chore/description
# ... make changes ...
git commit
git push origin chore/description
# Open PR on GitHub, get review, squash merge, delete branch
```

## Safety Rules

### Always follow
- ✅ Use your configured Git authentication method (SSH, HTTPS, token-based, etc.)
- ✅ Commit to main (no feature branches for routine work)
- ✅ Push direct to main (no PRs unless risky)
- ✅ Run `make verify` during development
- ✅ Let pre-commit/pre-push hooks run fully
- ✅ Use `gh` CLI ONLY for querying GitHub (gh pr view, gh issue list, etc)
- ✅ Use `AUTO_PUSH=1` for non-interactive push (skips confirm, keeps E2E)

### Never do
- ❌ Use `git push --no-verify` (bypass hooks)
- ❌ Use `git commit --no-verify` (bypass pre-commit hook)
- ❌ Use `gh` for commits or pushes
- ❌ Force push to main
- ❌ Amend published commits

## Troubleshooting

### "Permission denied (publickey)"

Your Git credentials may need to be reconfigured or re-authenticated. Please:
- Verify your Git authentication method is correctly configured
- Check that your credentials have appropriate permissions on the remote repository
- Retry the push after ensuring authentication is set up

### "fatal: ambiguous argument 'origin/main..HEAD'"

Pre-push hook tried to diff against a non-existent upstream ref. This occurs on first push to a new branch or after `git reset --hard @{u}`.

**Fix:** Use `git push -u origin main` or `ERS_AUTO_PUSH=1 git push origin main` to force the push through the hook.

### "refusing to allow an OAuth App to create or update workflow"

This error indicates an authentication scope limitation. This typically occurs when using token-based authentication that lacks certain permissions.

**Fix:** Ensure your Git authentication method (whether SSH, HTTPS token, or other) has the required permissions for the operations you're performing. Check with your organization's Git configuration guidelines.

## Related Skills

- `{example-service}` — Makefile structure and per-Lambda targets
- `{example-service}` — Lambda handler patterns
- `{example-service}` — CDK deployment

## References

- Root `/home/user/git/ers/CLAUDE.md` — Platform overview, architecture, CI/CD
- Hook scripts: `{workspace-name}/githooks/` — pre-commit, pre-push, commit-msg
- Hook install: `{workspace-name}/scripts/install-hooks.sh`
