---
title: "git-operations"
description: "Git workflow helpers for the agentic-engineers framework: push with tags, tag management, and standard release workflow"
role: "Senior Engineer"
model: "claude-haiku-4-5"
effort: "low"
status: "implemented"
version: "1.0.0"
---

# git-operations Skill

**Purpose:** Standardise git push and tag-management operations across the agentic-engineers
framework. The canonical release workflow is `git push && git push --tags`; this skill
encapsulates that pattern in a reusable shell function and documents the reasoning.

**Status:** ✅ Implemented and TDD-verified

---

## Overview

The `git-operations` skill provides:

1. **`git_push_with_tags`** — push commits and all local tags to the remote in one safe step.
2. **Tag validation** — confirm expected tags exist locally before pushing.
3. **Standard release workflow** — documents the authoritative sequence for releasing a version.

---

## Architecture

```
src/skills/_meta/git-operations/
├── SKILL.md                  # This file
├── scripts/
│   └── git_push.sh           # Shell helpers (git_push_with_tags, etc.)
└── tests/
    └── test_git_push.sh      # Bats / shell unit tests
```

---

## Standard Release Workflow

The canonical workflow after completing a local feature:

```bash
# 1. Commit (pre-commit hook runs: lint + test + version bump)
git add <files>
git commit -m "feat|fix|refactor|...(scope): description"

# 2. Push commits AND tags (standard release step)
git push && git push --tags
```

> `git push --tags` is the standard second step — it transmits all annotated/lightweight tags
> that exist locally but are absent on the remote. CI creates GitHub Releases from matching tags.

---

## Key Functions

### `scripts/git_push.sh`

#### `git_push_with_tags()`

Push the current branch to its upstream remote, then push all tags.

```bash
source scripts/git_push.sh
git_push_with_tags          # push commits + all tags
git_push_with_tags --dry-run  # dry-run: show what would be pushed
```

**Logic:**
1. Resolve the current branch and its upstream remote (falls back to `origin`).
2. Run `git push <remote> HEAD` — fast-fail on network or auth errors.
3. Run `git push <remote> --tags` — transmits all local tags not yet on remote.

**Returns:** 0 on success; non-zero on any git error (caller can trap).

#### `git_validate_tags(tag...)`

Assert that each named tag exists locally before a push.

```bash
git_validate_tags v1.2.3 v1.2.3-rc1
# exits 1 if any tag is missing
```

---

## Why `git push --tags` Is Standard

- **Annotated tags** are not pushed by `git push` alone — you must use `--tags` or `--follow-tags`.
- GitHub Actions CI/CD in this repo is configured to auto-create a GitHub Release whenever a
  matching semver tag lands on `main`.
- Running `git push --tags` as a discrete step (not `--follow-tags`) gives full control: you can
  push commits first, verify CI passes, then push tags to trigger releases.

---

## Safety Rules

| Rule | Reason |
|------|--------|
| ✅ `git push && git push --tags` | Separates commit push from tag push for clarity |
| ✅ Use `--dry-run` in automated contexts | Prevents accidental pushes in CI sandbox |
| ❌ `git push --force` on main | Rewrites history, breaks others |
| ❌ `git push --tags --force` | Can overwrite released tags, corrupts release history |
| ❌ Skip `git push --tags` | GitHub Release CI won't trigger |

---

## Usage in Agent Workflow

Agents finishing a task should use:

```bash
# Standard agent commit-and-release sequence
git add <changed files>
git commit -m "refactor(scope): description"
git push && git push --tags
```

Or via the helper:

```bash
source src/skills/_meta/git-operations/scripts/git_push.sh
git_push_with_tags
```

---

## Testing Strategy

Tests in `tests/test_git_push.sh` use a local bare git repository to avoid any network calls:

1. **happy path** — `git_push_with_tags` pushes commits + tags to a local remote.
2. **dry-run** — `--dry-run` emits what would be pushed without executing.
3. **tag validation** — `git_validate_tags` passes for present tags, fails for absent ones.
4. **remote error** — `git_push_with_tags` propagates non-zero exit when push fails.

---

## Acceptance Criteria

- ✅ `git_push_with_tags` pushes HEAD commits to upstream remote
- ✅ `git_push_with_tags` also pushes all local tags
- ✅ `--dry-run` flag works end-to-end (no network calls)
- ✅ `git_validate_tags` fails fast when expected tags are absent
- ✅ All tests pass with a local bare-repo fixture (no network required)
- ✅ SKILL.md documents canonical release workflow

---

## References

- `RENDERING.md` — src/ → dist/ → ~/.harness/ workflow (this repo)
- `src/skills/_meta/version-manager/SKILL.md` — version calculation and tag creation
- `.githooks/pre-commit` — local quality gate before every commit
- `.github/workflows/ci.yml` — GitHub Actions release trigger from git tags
