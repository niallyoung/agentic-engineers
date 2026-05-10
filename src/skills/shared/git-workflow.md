# {service-name} Skill

Git workflow, SSH setup, and commit/push mechanics for the ERS platform.

## Overview

**Trunk-based development**: commit and push directly to `main` with local quality gates. Remote pushes trigger GitHub Actions (expensive E2E + deploy), while local hooks handle fast feedback.

```
edit code
  → git add + git commit   [pre-commit hook: lint + test]
  → git push               [pre-push hook: E2E + diff review + "Push to main? [y/N]"]
  → main on GitHub ✅      [GitHub Actions: deploy dev + deploy prod + tag]
```

## SSH & 1Password Setup

**All pushes use SSH, not HTTPS.** SSH bypasses OAuth token scope restrictions and uses 1Password ssh-agent.

### Remote URLs

All ERS repos must use SSH (not HTTPS):

```bash
# Verify
git remote get-url origin
# Should be: git@github.com:{your-org}/REPO.git

# If HTTPS, change it:
git remote set-url origin git@github.com:{your-org}/REPO.git
```

### 1Password SSH Agent

Unlocking 1Password activates ssh-agent on your Mac. SSH operations trigger a 1Password popup to confirm access.

When using Claude Code or other tools:
- If `git push` fails with "Permission denied (publickey)", ask for 1Password authentication
- Wait for the user to unlock 1Password and confirm the SSH prompt
- Do NOT try to work around by using on-disk keys or HTTPS credentials

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
- ✅ Use SSH (git@github.com:..., not HTTPS)
- ✅ Use 1Password ssh-agent (unlock 1Password before pushing)
- ✅ Commit to main (no feature branches for routine work)
- ✅ Push direct to main (no PRs unless risky)
- ✅ Run `make verify` during development
- ✅ Let pre-commit/pre-push hooks run fully
- ✅ Use `gh` CLI ONLY for querying GitHub (gh pr view, gh issue list, etc)
- ✅ Use `ERS_AUTO_PUSH=1` for non-interactive push (skips confirm, keeps E2E)

### Never do
- ❌ Use HTTPS remotes or OAuth tokens
- ❌ Use `git push --no-verify` (bypass hooks)
- ❌ Use `git commit --no-verify` (bypass pre-commit hook)
- ❌ Use `gh` for commits or pushes
- ❌ Force push to main
- ❌ Amend published commits

## Troubleshooting

### "Permission denied (publickey)"

1Password ssh-agent may be inactive. Ask user to:
- Unlock 1Password on their Mac
- Retry the push
- A 1Password popup may appear asking to confirm SSH access

Do NOT attempt to work around with on-disk keys or HTTPS credentials — this defeats the security model.

### "fatal: ambiguous argument 'origin/main..HEAD'"

Pre-push hook tried to diff against a non-existent upstream ref. This occurs on first push to a new branch or after `git reset --hard @{u}`.

**Fix:** Use `git push -u origin main` or `ERS_AUTO_PUSH=1 git push origin main` to force the push through the hook.

### "refusing to allow an OAuth App to create or update workflow"

HTTPS push with OAuth token that lacks `workflow` scope. This error indicates:
- Remote is HTTPS (should be SSH)
- Token doesn't have `workflow` scope (should use SSH instead)

**Fix:** Switch remote to SSH and retry.

```bash
git remote set-url origin git@github.com:{your-org}/REPO.git
git push origin main
```

## Related Skills

- `{example-service}` — Makefile structure and per-Lambda targets
- `{example-service}` — Lambda handler patterns
- `{example-service}` — CDK deployment

## References

- Root `/home/user/git/ers/CLAUDE.md` — Platform overview, architecture, CI/CD
- Hook scripts: `{workspace-name}/githooks/` — pre-commit, pre-push, commit-msg
- Hook install: `{workspace-name}/scripts/install-hooks.sh`
