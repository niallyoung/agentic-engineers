# Local CI Skill

**Used by:** engineer
**Model:** claude-sonnet-4-6
**Effort:** low — run before every push; each step is fast if quality gates are maintained.

Use this skill when running the full local CI pipeline before pushing, or when asked to verify changes are ready to ship. Trigger on: "local ci", "verify", "ready to push", "check everything", "run ci locally", "pre-push check".

## What This Role Does

- Runs lint + unit tests (`make verify`) — same as the pre-commit hook
- Runs E2E tests when applicable (frontend applications only)
- Shows a diff of what would be pushed
- Reports pass/fail for each step clearly

## What This Role Does Not Do

- Does not deploy — cloud CI handles deployment after push
- Does not run code review automatically — that is a manual, discretionary step
- Does not skip steps unless the repo type genuinely does not apply

## Default Input

- Current working directory (repo root)
- Environment name (default: dev)

## Default Output

- Pass/fail for each pipeline step
- Clear error output on first failure (stop and report)

## Pipeline

### 1. Git State Check

```bash
# Ensure on the correct branch and working tree is clean
git branch --show-current   # should be main for trunk-based flow
git status --porcelain      # show any uncommitted changes
```

### 2. Lint + Unit Tests (same as pre-commit)

```bash
ENV_NAME=dev make verify    # runs: make lint && make test
```

- Every repo has a `verify` target (or separate `lint` + `test` targets)
- Repos without a Makefile skip gracefully

### 3. E2E Tests (frontend apps only)

```bash
CI=true npx playwright test    # runs Playwright across all browsers
```

- Only applicable in frontend application repos
- Skip in Go service repos

### 4. Code Review (optional — user's discretion)

Invoke the `/review` skill manually when desired. Not part of the automated pipeline. User controls frequency — not every commit needs a model review.

### 5. Diff Review

```bash
# Show what would be pushed
git --no-pager diff --color -U5 --stat origin/main..HEAD
git --no-pager diff --color -U5 origin/main..HEAD
```

## Repo Type Detection

Detect repo type from the working directory:

| Signals | Type | Steps |
|---------|------|-------|
| `go.mod` + `Makefile` + `cdk/` | Go service | `make verify` |
| `go.mod` + `Makefile`, no `cdk/` | Go library | `make verify` |
| `package.json` + `vite.config.ts` | Frontend app | `make verify` + E2E |
| No `Makefile` | Meta/docs repo | diff only |

## Environment

- `ENV_NAME=dev` is the default for local runs
- Go services: use golangci-lint version pinned in `Makefile`
- Frontend: Node 20+, Playwright (run `npx playwright install` if browsers missing)

## Non-Interactive Mode

For automated contexts, set an env var to skip interactive diff review and push confirmation while still running all quality gates:

```bash
AUTO_PUSH=1 git push    # runs E2E (frontend), skips diff review + confirm
```

Three push modes:
- **Interactive** (default): `git push` → E2E + diff review + confirm prompt
- **Non-interactive**: `AUTO_PUSH=1 git push` → E2E only, auto-approve
- **Emergency bypass**: `git push --no-verify` → skips all hooks (never use unless truly unavoidable)

## Quality Checklist

- [ ] Steps run in order: git state → lint+test → E2E (if applicable) → diff
- [ ] Stop on first failure and report clearly
- [ ] `ENV_NAME=dev` set for all `make` invocations
- [ ] E2E run with `CI=true` — not bare `npx playwright test`
- [ ] Diff reviewed before push (automated or manual)

## Escalation Rules

- If lint fails with a rule that seems wrong or overly strict, escalate to lead-engineer before disabling the rule
- If E2E tests are flaky (fail intermittently without code changes), escalate to quality-engineer
- If `make verify` is unavailable (no Makefile), check the repo's README for the equivalent command before skipping
