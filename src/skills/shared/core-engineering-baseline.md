# Core Engineering Baseline

**Shared by:** Engineer, Senior Engineer, Lead Engineer, Quality Engineer

**Purpose:** Universal foundational skills required for all engineer roles. This baseline consolidates essential knowledge across Git workflow, TDD implementation, code review standards, testing frameworks, GitHub CLI operations, and CDK stack patterns.

---

## Section 1: Git Workflow

Git workflow, SSH setup, and commit/push mechanics for the ERS platform.

### Overview

**Trunk-based development**: commit and push directly to `main` with local quality gates. Remote pushes trigger GitHub Actions (expensive E2E + deploy), while local hooks handle fast feedback.

```
edit code
  → git add + git commit   [pre-commit hook: lint + test]
  → git push               [pre-push hook: E2E + diff review + "Push to main? [y/N]"]
  → main on GitHub ✅      [GitHub Actions: deploy dev + deploy prod + tag]
```

### SSH & 1Password Setup

**All pushes use SSH, not HTTPS.** SSH bypasses OAuth token scope restrictions and uses 1Password ssh-agent.

#### Remote URLs

All ERS repos must use SSH (not HTTPS):

```bash
# Verify
git remote get-url origin
# Should be: git@github.com:{your-org}/REPO.git

# If HTTPS, change it:
git remote set-url origin git@github.com:{your-org}/REPO.git
```

#### 1Password SSH Agent

Unlocking 1Password activates ssh-agent on your Mac. SSH operations trigger a 1Password popup to confirm access.

When using Claude Code or other tools:
- If `git push` fails with "Permission denied (publickey)", ask for 1Password authentication
- Wait for the user to unlock 1Password and confirm the SSH prompt
- Do NOT try to work around by using on-disk keys or HTTPS credentials

### Commit & Push Workflow

#### 1. Edit and commit

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

#### 2. Push to main

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

#### 3. GitHub Actions deploys

Once push lands on main, GitHub Actions runs:
- Lint + test (redundant, cached)
- Deploy dev
- Deploy prod
- Tag release (semantic versioning)

This is the "expensive CI" — offloaded to the cloud so your local push is fast.

### Makefile Standard Targets

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

### Branch Policy

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

### Safety Rules

#### Always follow
- ✅ Use SSH (git@github.com:..., not HTTPS)
- ✅ Use 1Password ssh-agent (unlock 1Password before pushing)
- ✅ Commit to main (no feature branches for routine work)
- ✅ Push direct to main (no PRs unless risky)
- ✅ Run `make verify` during development
- ✅ Let pre-commit/pre-push hooks run fully
- ✅ Use `gh` CLI ONLY for querying GitHub (gh pr view, gh issue list, etc)
- ✅ Use `ERS_AUTO_PUSH=1` for non-interactive push (skips confirm, keeps E2E)

#### Never do
- ❌ Use HTTPS remotes or OAuth tokens
- ❌ Use `git push --no-verify` (bypass hooks)
- ❌ Use `git commit --no-verify` (bypass pre-commit hook)
- ❌ Use `gh` for commits or pushes
- ❌ Force push to main
- ❌ Amend published commits

---

## Section 2: TDD & Implementation

Test-driven development (red-green-refactor) is the foundation of all implementation work.

### What Implementation DOES

- [ ] Receives a pre-planned DELEGATE block with detailed scope, context, and implementation steps
- [ ] **RED phase**: Writes failing test first (never code without a test)
- [ ] **GREEN phase**: Implements minimal code to make test pass
- [ ] **REFACTOR phase**: Improves code without changing behavior
- [ ] Investigates and fixes **root causes**, not symptoms
- [ ] Follows existing architectural patterns and conventions (CQRS/Event Sourcing, NOSTR, IAM SigV4)
- [ ] Re-uses established patterns before creating new ones (consistency over novelty)
- [ ] Maintains **80-95% test coverage** with high-value, user-focused tests
- [ ] Runs `make verify` (lint + tests) before commit
- [ ] Creates conventional commits with clear "why" (not "what")

### What Implementation DOES NOT DO

- [ ] Does not skip tests or write code-first (TDD is mandatory)
- [ ] Does not create new patterns when existing ones fit (avoid premature abstraction)
- [ ] Does not add error handling for impossible scenarios (trust framework guarantees)
- [ ] Does not refactor outside the scope of the current task
- [ ] Does not commit untested code or code with failing tests

### TDD Workflow (Red-Green-Refactor)

#### Phase 1: RED (Write Failing Test)

1. Identify the test file location (e.g., `main_test.go`, `auth.test.ts`)
2. Write a test that:
   - Has a clear, descriptive name (TestXxxBehavior)
   - Tests **one thing** (one assertion per test, or table-driven for variants)
   - **Fails** before code change (verifies test is real)
   - Uses existing test patterns in the codebase
3. Run test suite to confirm test fails: `make verify` → FAIL

#### Phase 2: GREEN (Implement Minimal Code)

4. Write **minimum code** to make test pass
   - No extra features
   - No "I might need this later" code
   - No defensive checks for impossible states
5. Run test suite: `make verify` → PASS
6. Verify no other tests broke

#### Phase 3: REFACTOR (Improve, Don't Change Behavior)

7. Improve code quality (rename variables, extract functions, simplify logic)
8. Re-run tests after each small refactor: `make verify` → PASS
9. Ensure coverage maintained or improved

### Quality Checklist (Before Committing)

- [ ] **Lint + Test Pass** — `make verify` output shows all tests green, 0 lint errors
- [ ] **No new errors** — No compilation, type, or linter warnings introduced
- [ ] **In-scope changes only** — All modified files within task scope, no scope creep
- [ ] **Tests added/updated** — For any new function, a test exists
- [ ] **No production hazards** — No `panic`, `log.Fatal`, hardcoded secrets, commented-out code

---

## Section 3: Code Review Standards

Code review ensures all changes meet quality gates before merging to main.

### What Code Review DOES

- Reviews commits and PRs against the standards below
- Identifies violations and provides specific, actionable feedback
- Approves changes that meet all standards or requests changes with clear rationale
- Ensures architectural boundaries (CQRS, event schema, security) are not violated

### What Code Review DOES NOT DO

- Does not rewrite code during review — requests changes and explains why
- Does not approve changes with outstanding security concerns
- Does not accept "we'll fix it later" for error handling, idempotency, or auth bypass

### Review Standards

#### Always Check

- [ ] PR/commit description accurately reflects the actual changes
- [ ] No stale comments, dead code, or orphaned references introduced
- [ ] Error handling is explicit — no ignored errors in Go, no swallowed promises in TypeScript
- [ ] Environment variables used in code match what is defined in `env/.env.*` files
- [ ] No secrets, tokens, or credentials in code or commit messages

#### CQRS Consistency

- [ ] Command handlers (write path) must NOT read/query data for business decisions
- [ ] Query handlers (read path) must NOT write or mutate data
- [ ] Event consumers must be idempotent — safe to replay without side effects duplication

#### Event Architecture

- [ ] Event kind constants match the platform's allocated event kind registry
- [ ] Domain event structure is correct: id, pubkey, created_at, kind, tags, content, sig
- [ ] SNS/SQS message unwrapping follows the standard envelope pattern
- [ ] New event kinds have been allocated (not ad hoc)
- [ ] Event schema versions are explicit — breaking changes require a new version

#### Go Services

- [ ] No `panic()` in production code paths
- [ ] Table-driven tests for all business logic
- [ ] golangci-lint passes without suppressed warnings
- [ ] Lambda handlers use dependency injection — no global mutable state
- [ ] AWS clients created once in `main()`, not per-invocation

#### Frontend

- [ ] Optimistic updates follow CQRS pattern (update cache, then schedule revalidation)
- [ ] All API calls go through the resilience layer (retry, token refresh, maintenance mode)
- [ ] No direct token access outside the auth module

#### Security

- [ ] IAM SigV4 signing for all inter-service calls — not API keys or static credentials
- [ ] JWT validation at API Gateway level only — not re-validated inside Lambda handlers
- [ ] Backend services do not accept JWT directly (IAM auth only)
- [ ] No overly permissive IAM policies (`*` actions or resources)

### Escalation Rules

- If a security issue is found, block the PR immediately and notify the author — do not merge with a "fix it later" note
- If an event kind conflict is detected (same number used for different events), escalate and block until resolved — this is a data corruption risk
- If a test coverage gap is found in business logic, request tests — do not accept "we'll add coverage later" for core domain logic

---

## Section 4: Testing Overview

Testing frameworks and strategies for maintaining high code quality.

### Playwright E2E Testing ({service-name})

Playwright is the primary E2E testing framework for {service-name} (React/TypeScript frontend).

#### What Engineer DOES

- ✅ Writes behavior-driven E2E tests in Playwright (TypeScript)
- ✅ Focuses on **user-centric features**: login, signup, CRUD workflows, navigation, permissions
- ✅ Tests **outcomes not implementation**: "user can create membership" not "button has className=create-btn"
- ✅ Uses page object models (POM) for maintainability and reuse
- ✅ Validates happy path + critical error cases (missing field, network timeout, permission denied)
- ✅ Integrates with Vitest test runner (same as unit tests)
- ✅ Runs full test suite locally before commit (pre-push hook with `CI=true`)
- ✅ Debugs test flakiness: retry logic, wait strategies, fixture state isolation

#### What Engineer DOES NOT DO

- ❌ Does not test visual appearance (screenshots, pixel matching, CSS assertions)
- ❌ Does not hardcode selectors (uses data-testid, accessible names, roles)
- ❌ Does not skip authentication (tests must go through real login when needed)
- ❌ Does not use sleep() for waiting (uses Playwright wait strategies)
- ❌ Does not test implementation details (component internals, prop drilling)
- ❌ Does not modify business logic while writing tests (TDD: test-first)

#### Playwright Setup ({service-name})

```bash
npm install --save-dev @playwright/test
npx playwright install
```

#### Configuration (playwright.config.ts)

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './src/**/*.e2e.test.ts',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173', // Vite dev server
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
  ],
});
```

### Unit Testing

- Table-driven tests for all business logic (Go)
- All critical paths covered (target 80-95% coverage)
- Test names describe behavior: `TestXxxReturnsErrorWhenYyyIsZzz`

---

## Section 5: GitHub CLI Essentials

GitHub CLI (`gh`) is the standard tool for all GitHub interactions.

### What GitHub CLI DOES

- Queries repository state: PRs, issues, workflow runs, releases, tags
- Watches CI pipeline progress and reports pass/fail across repos
- Opens, views, and merges pull requests
- Creates issues and comments programmatically

### What GitHub CLI DOES NOT DO

- Does not push code or create commits — use `git` for that
- Does not modify GitHub Actions workflow YAML — escalate to engineer
- Does not manage branch protection rules, org settings, or secrets — escalate to platform team

### Authentication

```bash
# Check auth status
gh auth status

# Login (first time or after token expiry)
gh auth login
```

### Pull Requests

```bash
# List open PRs
gh pr list -R owner/repo

# View a PR
gh pr view <NUMBER> -R owner/repo

# View PR with comments
gh pr view <NUMBER> -R owner/repo --comments

# Check out a PR branch locally
gh pr checkout <NUMBER>

# Create a PR
gh pr create --title "feat(scope): description" --body "$(cat <<'EOF'
## Summary
- What changed and why

## Test plan
- [ ] Unit tests pass
- [ ] E2E tests pass
EOF
)"

# Merge (squash)
gh pr merge <NUMBER> --squash --delete-branch

# Approve
gh pr review <NUMBER> --approve
```

### Issues

```bash
# List open issues
gh issue list -R owner/repo

# View an issue
gh issue view <NUMBER> -R owner/repo

# Create an issue
gh issue create --title "Bug: description" --body "Steps to reproduce..."

# Close an issue
gh issue close <NUMBER>

# Comment on an issue
gh issue comment <NUMBER> --body "Investigation update..."
```

### Workflow Runs (CI/CD)

```bash
# List recent runs
gh run list -R owner/repo --limit 5

# View run details
gh run view <RUN_ID> -R owner/repo

# Watch run progress (real-time)
gh run watch <RUN_ID> -R owner/repo

# View run logs
gh run view <RUN_ID> -R owner/repo --log
```

---

## Section 6: CDK Stack Patterns

AWS CDK infrastructure patterns for deploying Go microservices.

### What CDK DOES

- Scaffolds CDK entry point (`cdk/cdk.go`) and stack wrappers
- Implements 3-tier stack architecture (infra → core → application)
- Wires cross-stack references, stack dependencies, and permissions boundaries
- Defines common constructs: HTTP API + Lambda, SQS event consumer, DynamoDB table

### What CDK DOES NOT DO

- Does not write application Lambda logic (see `patterns/lambda-handler.md`)
- Does not design event schemas or CQRS boundaries (escalate to senior-engineer)
- Does not manage Cognito user pools or OAuth2 configuration

### Entry Point Pattern (standardized)

Every service has `cdk/cdk.go` as the CDK app entry point:

```go
package main

import (
	"os"

	"github.com/aws/aws-cdk-go/awscdk/v2"
	"github.com/aws/aws-cdk-go/awscdk/v2/awsiam"
	"github.com/aws/jsii-runtime-go"

	"github.com/your-org/your-service/cdk/stacks"
)

func main() {
	defer jsii.Close()

	app := awscdk.NewApp(nil)
	appName := os.Getenv("APP_NAME")
	env := &awscdk.Environment{
		Account: jsii.String(os.Getenv("AWS_ACCOUNT")),
		Region:  jsii.String(os.Getenv("AWS_REGION")),
	}

	// NewMyStack returns *stacks.MyStack (a wrapper struct with a Stack awscdk.Stack field
	// for cross-stack references). Access the embedded CDK stack via stack.Stack.
	stack := stacks.NewMyStack(app, appName+"-MyStack", stacks.MyStackProps{
		StackProps: awscdk.StackProps{Env: env},
		AppName:    appName,
		EnvName:    os.Getenv("ENV_NAME"),
	})
	applyBoundary(stack.Stack)

	app.Synth(nil)
}

func applyBoundary(stack awscdk.Stack) {
	awsiam.PermissionsBoundary_Of(stack).Apply(
		awsiam.ManagedPolicy_FromManagedPolicyName(
			stack, jsii.String("CDKBoundary"), jsii.String("CDKPermissionsBoundary"),
		),
	)
}
```

### 3-Tier Stack Architecture

```
Infrastructure (DynamoDB, S3, SNS topics)
  → Core (idempotency tracking, event dispatch)
    → Application (API Gateway, Lambda, consumers)
```

Stacks are wired with `AddDependency()` and cross-stack props:

```go
infraStack := stacks.NewDDBStack(app, appName+"-DDBStack", ...)
apiStack := stacks.NewAPIStack(app, appName+"-APIStack", stacks.APIStackProps{
	TableName: infraStack.TableName,  // cross-stack reference
	TableArn:  infraStack.TableArn,
})
apiStack.AddDependency(infraStack.Stack, jsii.String("DDB"))
```

---

## See Also

- **Engineer-Specific Skills:** `skills/shared/engineer-specifics.md` — Deep dives into Local CI, Lambda Patterns, and Makefile standards (Engineer-only)
- **Individual Role Files:**
  - `skills/roles/engineer.md`
  - `skills/roles/senior-engineer.md`
  - `skills/roles/lead-engineer.md`
  - `skills/roles/quality-engineer.md`

---

## Related Skills (Referenced for Deep Dives)

- `skills/patterns/implementation-coding.md` — Full TDD workflow and architectural compliance
- `skills/review/code-review.md` — Complete code review standards
- `skills/testing/playwright-testing.md` — Playwright test development and execution
- `skills/shared/git-workflow.md` — Full Git workflow and troubleshooting
- `skills/shared/github-cli.md` — Complete GitHub CLI reference
- `skills/shared/cdk-stack.md` — CDK deployment patterns and stack types
