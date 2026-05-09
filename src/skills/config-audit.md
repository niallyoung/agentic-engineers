---
name: ERS Configuration Audit & Enforcement
description: Audit all ERS services against the Configuration & Dependency Management Standard
type: skill
delegable_to: [Quality Engineer, Lead Engineer]
---

# ERS Configuration Audit & Enforcement Skill

## Quick Audit Command

Run this to audit all ERS services:

```bash
#!/bin/bash
for repo in {service-name} {service-name} {service-name} {service-name} {service-name} {service-name} {service-name} {service-name}; do
  echo "=== Checking $repo ==="
  cd ~/git/ers/$repo 2>/dev/null || { echo "SKIP: repo not found"; continue; }
  
  # Check Makefile
  echo "Makefile:"
  grep -E "^ENV_NAME|^-include|^export" Makefile | head -3
  
  # Check .env files
  echo ".env.dev:"
  head -5 env/.env.dev 2>/dev/null | grep -v "^#"
  
  # Check for quotes in env files
  if grep -q '="' env/.env.* 2>/dev/null; then
    echo "⚠️  FOUND QUOTES in .env files (should be removed)"
    grep '="' env/.env.* 2>/dev/null
  fi
  
  # Check CDK for silent defaults
  echo "CDK patterns:"
  grep -n "StringParameter_ValueForStringParameter\|jsii.String(\"\")" cdk/stacks/*.go 2>/dev/null | head -5
  
  echo ""
done
```

## Audit Checklist per Service

For each service, verify all items:

### 1. Makefile Structure
```bash
grep -A 5 "^SHELL\|^ENV_NAME" Makefile | head -20
```
**Expected**:
```makefile
SHELL:=/bin/bash
ENV_NAME ?= dev
-include env/.env.$(ENV_NAME)
export
```
✅ = Present and correct
❌ = Missing or wrong format

### 2. Environment Files (.env.dev and .env.prod)
```bash
cat env/.env.dev env/.env.prod
```
**Rules**:
- No quotes on values (`ENV_NAME=dev` not `ENV_NAME="dev"`)
- All required vars present
- Optional vars can be empty
- Comments explain each var

✅ Example:
```
ENV_NAME=dev
APP_NAME=dev-{service-name}
AWS_ACCOUNT=417772279096
AWS_REGION=ap-southeast-2
FILES_API_URL=
```

❌ Wrong:
```
ENV_NAME="dev"    # ← WRONG: quotes
APP_NAME="dev-{service-name}"  # ← WRONG
AWS_ACCOUNT="417772279096"  # ← WRONG
```

### 3. CDK Code (cdk/stacks/*.go)

**Check for required dependencies**:
```bash
grep "StringParameter_ValueForStringParameter" cdk/stacks/*.go
```

Each should have a comment explaining:
- Why it's REQUIRED or OPTIONAL
- What happens if missing
- How to fix if missing

✅ Example:
```go
// REQUIRED: {service-name} API URL (core dependency)
membersAPIURL := awsssm.StringParameter_ValueForStringParameter(
    stack, 
    jsii.String("/"+props.EnvName+"-{service-name}/APIUrl"), 
    nil,
)
```

❌ Wrong (no comment):
```go
filesAPIURL := awsssm.StringParameter_ValueForStringParameter(stack, jsii.String("/..."), nil)
```

**Check for optional features**:
```bash
grep -B 2 'jsii.String("")' cdk/stacks/*.go
```

Each empty string must have documentation:

✅ Example:
```go
// OPTIONAL: {service-name} integration (profile pictures)
// Why optional: not required for core query functionality
// Behavior if missing: profile endpoints return null
filesAPIURL := jsii.String("")
```

❌ Wrong (no explanation):
```go
filesAPIURL := jsii.String("")
```

### 4. Lambda Handlers

**Check for env var validation**:
```bash
grep -n "os.Getenv\|Fatalf\|Panic" lambda/*/main.go
```

Should see:
- Required vars checked with Fatalf/Panic if missing
- Optional vars logged if missing
- Handlers gracefully skip features if optional vars empty

✅ Example:
```go
membersAPI := os.Getenv("MEMBERS_API_URL")
if membersAPI == "" {
    log.Fatalf("MEMBERS_API_URL is required")
}

filesAPI := os.Getenv("FILES_API_URL")
if filesAPI == "" {
    log.Printf("files API not configured; profile feature disabled")
}
```

### 5. GitHub Actions Workflow

**Check for env file creation**:
```bash
grep -A 10 "Create env file" .github/workflows/main.yaml
```

Should be:
- No shell quotes on variable values
- `cat > env/.env.${ENV_NAME}` (not with escaped quotes)
- Uses `make deploy` (not manual cdk deploy)

✅ Example:
```yaml
- name: Create env file
  run: |
    mkdir -p env
    cat > env/.env.dev <<'EOF'
    ENV_NAME=dev
    APP_NAME=dev-{service-name}
    AWS_ACCOUNT=417772279096
    EOF
```

❌ Wrong:
```yaml
    ENV_NAME="dev"    # ← Quotes!
    APP_NAME="dev-{service-name}"
```

### 6. CLAUDE.md Documentation

**Check service docs**:
```bash
grep -E "^## |Environment|Configuration|Required|Optional" CLAUDE.md | head -20
```

Should include section documenting:
- All environment variables
- Which are REQUIRED vs OPTIONAL
- What each controls
- What happens if missing

## Audit Report Template

For each service, generate:

```markdown
# ERS Configuration Audit Report — [Service Name]

## Status: ✅ COMPLIANT / ⚠️ PARTIAL / ❌ NEEDS FIXES

### Makefile
- [x] Has `ENV_NAME ?= dev`
- [x] Has `-include env/.env.$(ENV_NAME)`
- [x] Has `export` statement
- [x] No manual sourcing in recipes

### Environment Files
- [x] .env.dev exists with all required vars
- [x] .env.prod exists with all required vars
- [x] No quotes on values
- [x] Optional vars present (can be empty)
- [ ] ❌ ISSUE: AWS_ACCOUNT has quotes in .env.prod

### CDK
- [x] Required dependencies explicitly documented
- [x] Optional dependencies use empty string with rationale
- [x] No silent defaults for required values
- [ ] ❌ ISSUE: FILES_API_URL missing explanation comment

### Lambda
- [x] Required env vars validated at startup
- [x] Optional env vars logged if missing
- [x] Handlers skip features gracefully if optional vars empty

### GitHub Actions
- [x] Env file creation has no quotes
- [x] Uses `make deploy` not manual cdk
- [x] Fails loudly on errors

### CLAUDE.md
- [x] Documents all environment variables
- [ ] ❌ ISSUE: Missing explanation of which vars are REQUIRED

### Action Items
1. Remove quotes from .env.prod AWS_ACCOUNT values
2. Add explanation comment to CDK FILES_API_URL
3. Update CLAUDE.md with Required/Optional designation for all vars
```

## Automation

To automatically apply fixes across all repos:

```bash
# Fix 1: Remove quotes from all .env files
for repo in {service-name} {service-name} {service-name} {service-name} {service-name} {service-name} {service-name}; do
  cd ~/git/ers/$repo
  sed -i '' 's/="\([^"]*\)"/=\1/g' env/.env.*
done

# Fix 2: Verify Makefile pattern in all repos
for repo in {service-name} {service-name} {service-name} {service-name} {service-name} {service-name} {service-name}; do
  cd ~/git/ers/$repo
  if ! grep -q "^export$" Makefile; then
    echo "$repo: missing 'export' statement in Makefile"
  fi
done
```

## When to Audit

- [ ] After each CDK change (verify no silent defaults introduced)
- [ ] After each Makefile modification (verify pattern maintained)
- [ ] Before each deployment (verify all required configs present)
- [ ] During code review (verify compliant with standard)
- [ ] Quarterly (comprehensive audit of all 8 services)

