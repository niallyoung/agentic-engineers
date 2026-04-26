---
name: ERS Configuration Enforcement Actions
description: Delegate configuration compliance fixes to Quality/Lead Engineers via agentic-engineers
type: skill
delegable_to: [Quality Engineer, Lead Engineer]
relates_to: [{service-name}.md, {service-name}.md]
---

# ERS Configuration Enforcement — Delegation Pattern

When a configuration non-compliance is detected in CICD or code review, delegate fixes using this pattern:

## DELEGATE Handoff Format

```yaml
---
handoff_type: DELEGATE
task_id: 2026-04-27-{service-name}[service]
role: Quality Engineer or Lead Engineer
model: sonnet (Sonnet 4.6)
budget_context:
  session_pct_at_delegation: XX%
  status: GREEN|YELLOW|RED
---

### Issue
[Service]: Configuration non-compliance detected

**What failed**: [Describe the specific failure]
- Example: {service-name} #41 failed: "Unable to fetch parameters [/dev-{service-name}/APIUrl]"
- Root cause: Missing explicit OPTIONAL/REQUIRED designation

**Compliance gaps**:
- [ ] Makefile: missing `export` statement
- [ ] .env files: values have quotes (should be removed)
- [ ] CDK: required dependency fetch has no error handling comment
- [ ] CDK: optional feature missing rationale comment
- [ ] Lambda: env var validation missing
- [ ] GitHub Actions: workflow uses manual cdk deploy instead of `make deploy`
- [ ] CLAUDE.md: missing environment variable documentation
- [x] Other: [describe]

### Success Criteria
1. All environment files (.env.dev, .env.prod) have no quotes on values
2. CDK code explicitly comments why each dependency is REQUIRED or OPTIONAL
3. Required dependencies fail loudly if SSM parameter missing
4. Optional features use empty string with documented rationale
5. Lambda validates REQUIRED env vars at startup, logs OPTIONAL ones
6. GitHub Actions workflow uses `make deploy` (not manual cdk)
7. CLAUDE.md documents all env vars with Required/Optional designation
8. All changes pass `make verify` (lint + test)
9. Commit follows conventional commits format

### Reference Standards
- Read: `{service-name}.md` — the baseline standard
- Read: `{service-name}.md` — audit checklist
- Checklist: Use audit checklist for verification

### Scope
- **Single service or all 8?** [Specify which repos]
- **Risky areas**: Makefile, CDK, .env files, GitHub Actions workflows
- **Safe to test locally**: `make verify` validates all changes locally
- **No data loss risk**: These are all configuration/code changes

### Context
- Branch: main (trunk-based development)
- Deployment: Changes automatically trigger CI/CD
- Rollback: Can revert commits if deployment fails

---
```

## Common Fixes & Patterns

### Fix 1: Remove Quotes from .env Files

**Issue**: `.env.dev` and `.env.prod` have shell-style quotes

**Bad** ❌:
```bash
ENV_NAME="dev"
APP_NAME="dev-{service-name}"
AWS_ACCOUNT="417772279096"
```

**Good** ✅:
```bash
ENV_NAME=dev
APP_NAME=dev-{service-name}
AWS_ACCOUNT=417772279096
```

**How to fix**:
```bash
cd ~/git/ers/[service]
sed -i '' 's/="\([^"]*\)"/=\1/g' env/.env.*
git diff  # Review changes
git add env/
git commit -m "fix: remove quotes from environment files"
```

### Fix 2: Add Makefile Export Statement

**Issue**: Makefile missing `export` statement

**Bad** ❌:
```makefile
SHELL:=/bin/bash
ENV_NAME ?= dev
-include env/.env.$(ENV_NAME)
# No 'export' here!
```

**Good** ✅:
```makefile
SHELL:=/bin/bash

ENV_NAME ?= dev
-include env/.env.$(ENV_NAME)
export
```

**How to fix**:
1. Open `Makefile`
2. After `-include env/.env.$(ENV_NAME)` line, add blank line + `export`
3. Verify: `grep -A 1 "^-include" Makefile` should show `export` right after

### Fix 3: Add CDK Comments for Required vs Optional

**Issue**: CDK code missing explanation of why dependency is REQUIRED or OPTIONAL

**Bad** ❌:
```go
membersAPIURL := awsssm.StringParameter_ValueForStringParameter(stack, jsii.String("/"+props.EnvName+"-{service-name}/APIUrl"), nil)
filesAPIURL := awsssm.StringParameter_ValueForStringParameter(stack, jsii.String("/"+props.EnvName+"-{service-name}/APIUrl"), nil)
```

**Good** ✅:
```go
// REQUIRED: {service-name} API URL (core query dependency)
membersAPIURL := awsssm.StringParameter_ValueForStringParameter(
    stack, 
    jsii.String("/"+props.EnvName+"-{service-name}/APIUrl"), 
    nil,
)

// OPTIONAL: {service-name} integration (profile pictures)
// Why optional: not required for core query functionality
// Behavior if missing: profile picture endpoints return null
// TODO: When {service-name} deployed, fetch dynamically from SSM
filesAPIURL := jsii.String("")
```

**How to fix**:
1. Find all `StringParameter_ValueForStringParameter` calls
2. Add 1-2 line comment above explaining REQUIRED/OPTIONAL
3. For OPTIONAL features using empty string, add longer comment with rationale

### Fix 4: Update GitHub Actions Workflow

**Issue**: Workflow uses manual `cdk deploy` instead of `make deploy`

**Bad** ❌:
```yaml
- name: Deploy
  run: |
    cd cdk
    cdk deploy --all --require-approval never
    cd -
```

**Good** ✅:
```yaml
- name: Deploy
  run: ENV_NAME=dev make deploy
```

**How to fix**:
1. Open `.github/workflows/main.yaml`
2. Find Deploy step
3. Replace with simple `ENV_NAME=X make deploy`
4. Makefile now owns the deployment logic

### Fix 5: Add Lambda Env Var Validation

**Issue**: Lambda doesn't validate required env vars at startup

**Bad** ❌:
```go
func NewHandler() *Handler {
    return &Handler{
        membersAPIURL: os.Getenv("MEMBERS_API_URL"),
        filesAPIURL:   os.Getenv("FILES_API_URL"),
    }
}
```

**Good** ✅:
```go
func NewHandler() *Handler {
    // REQUIRED
    membersAPI := os.Getenv("MEMBERS_API_URL")
    if membersAPI == "" {
        log.Fatalf("MEMBERS_API_URL is required")
    }

    // OPTIONAL
    filesAPI := os.Getenv("FILES_API_URL")
    if filesAPI == "" {
        log.Printf("FILES_API_URL not configured; profile features disabled")
    }

    return &Handler{
        membersAPIURL: membersAPI,
        filesAPIURL:   filesAPI,
    }
}
```

**How to fix**:
1. Find Lambda startup code (usually `main.go` or `handler.go`)
2. Add validation for each env var
3. REQUIRED → Fatalf if empty
4. OPTIONAL → log.Printf if empty, continue

### Fix 6: Update CLAUDE.md

**Issue**: Service docs don't list environment variables or mark as Required/Optional

**Bad** ❌:
```markdown
# {service-name}

Go service for queries.
```

**Good** ✅:
```markdown
# {service-name}

Go service: Query Gateway for all read operations.

## Environment Configuration

| Variable | Required | Source | Purpose |
|----------|----------|--------|---------|
| APP_NAME | Yes | .env | Application identifier |
| MEMBERS_API_URL | Yes | SSM | Backend service URL |
| COGNITO_ISSUER_URL | Yes | SSM | JWT validation |
| FILES_API_URL | No | Empty if not deployed | Optional profile pictures |
| LOG_LEVEL | No | Env file (default: INFO) | Logging verbosity |
```

**How to fix**:
1. Open `CLAUDE.md`
2. Add "## Environment Configuration" section
3. List each env var with Required/Optional
4. Link back to where it's set (CDK, .env file, etc.)

## Verification Checklist

After applying fixes, verify:

```bash
# 1. Lint passes
ENV_NAME=dev make lint
# Result: 0 issues

# 2. Tests pass
ENV_NAME=dev make test
# Result: all tests pass

# 3. Makefile structure correct
grep -E "^SHELL|^ENV_NAME|^-include|^export" Makefile
# Result: 4 lines (SHELL, ENV_NAME, -include, export)

# 4. No quotes in .env files
grep "=" env/.env.* | grep '"'
# Result: empty (no quotes found)

# 5. CDK has comments
grep -B 1 "StringParameter_ValueForStringParameter\|jsii.String(\"\")" cdk/stacks/*.go | grep "//"
# Result: comments present for each

# 6. GitHub Actions uses make deploy
grep "make deploy" .github/workflows/main.yaml
# Result: found in Deploy step
```

## HANDBACK Format

After completing fixes:

```yaml
---
handoff_type: HANDBACK
task_id: 2026-04-27-{service-name}[service]
status: complete
metrics:
  files_modified: [number]
  commits_created: [number]
  verification_status: "all checks passed"
---

## Changes Made
- [List specific changes]
- Removed quotes from .env files
- Added explicit REQUIRED/OPTIONAL comments to CDK
- Updated GitHub Actions to use `make deploy`
- Updated CLAUDE.md with environment variable table
- All tests and lints pass

## Verification
- ✅ make lint: 0 issues
- ✅ make test: all pass
- ✅ Makefile pattern: correct
- ✅ Environment files: no quotes
- ✅ CDK comments: all documented
- ✅ GitHub Actions: using make deploy

## Notes
[Any additional context for orchestrator]
```

