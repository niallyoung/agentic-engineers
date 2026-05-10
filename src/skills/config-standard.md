---
name: ERS Configuration & Dependency Management Standard
description: Defines how all ERS services handle configuration, environment variables, and cross-service dependencies
type: skill
applies_to: [all ERS services]
---

# ERS Configuration & Dependency Management Standard

**Intent**: Fail loudly on missing required configuration; be explicit about optional features. No silent defaults.

## Configuration Hierarchy (in order of enforcement)

### 1. Required Dependencies (Must Exist)
- SSM parameters that other services depend on (e.g., `/dev-{service-name}/APIUrl`)
- Environment variables that Lambda requires to function
- **Behavior**: Fail immediately at CDK synthesis time with clear error message
- **Error message must include**:
  - Which parameter/variable is missing
  - Which service needs it (e.g., "{example-service} requires /dev-{service-name}/APIUrl")
  - How to create/fix it (e.g., "Deploy {service-name} first")

**Example (CDK Go)**:
```go
// REQUIRED: {service-name} API URL
membersAPIURL := awsssm.StringParameter_ValueForStringParameter(
    stack, 
    jsii.String("/"+props.EnvName+"-{service-name}/APIUrl"), 
    nil,  // ← nil = fail if missing
)
```

### 2. Optional Features (Graceful Degradation)
- Features that can be disabled if a dependency isn't available
- Only used in specific optional handlers (e.g., profile pictures require {service-name})
- **Behavior**: 
  - Document explicitly why it's optional
  - Default to empty string or null (with clear intent)
  - Lambda handler must handle gracefully (return null, skip feature, log)
  - Never silently use wrong behavior

**Example (CDK Go)**:
```go
// OPTIONAL: {service-name} integration (profile pictures)
// Why optional: {service-name} not required for core query functionality
// Behavior if missing: profile picture endpoints return null
// TODO: When {service-name} deployed, fetch dynamically: 
//   awsssm.StringParameter_ValueForStringParameter(...)
filesAPIURL := jsii.String("")
```

**Example (Lambda Go)**:
```go
if h.filesAPIURL == "" {
    log.Printf("ProfilePicture: files API not configured, returning null")
    return jsonResponse(http.StatusOK, map[string]interface{}{"picture": nil})
}
```

### 3. Configuration Variables (Env-Driven)
All environment variables must be:
1. Explicitly declared in CDK with comments
2. Listed in `.env.dev` and `.env.prod` files
3. Validated at Lambda startup if critical
4. Documented in service's CLAUDE.md

**Example structure**:
```go
Environment: &map[string]*string{
    "APP_NAME":        jsii.String(props.AppName),
    "MEMBERS_API_URL": membersAPIURL,  // REQUIRED: set by {service-name}
    "FILES_API_URL":   filesAPIURL,    // OPTIONAL: empty if {service-name} not deployed
    "LOG_LEVEL":       jsii.String("INFO"),
}
```

## Environment Files (.env.dev / .env.prod)

**Rules**:
1. No shell-style quotes (`ENV_NAME="dev"` ❌ → `ENV_NAME=dev` ✅)
2. All variables exported via Makefile's `export` statement
3. All required variables must have values
4. Optional variables can be empty (but must exist)

**Template**:
```bash
# .env.prod
ENV_NAME=prod
APP_NAME=prod-{example-service}
AWS_ACCOUNT=666109694932
AWS_REGION=ap-southeast-2
# Optional: empty if not deployed
FILES_API_URL=
```

## Makefile Pattern (Consistent Across All Services)

Every Makefile must:
1. Include env file at the top with `export`
2. Never manually source env files in recipes
3. CDK and Lambda targets inherit all env vars automatically

```makefile
SHELL:=/bin/bash

ENV_NAME ?= dev
-include env/.env.$(ENV_NAME)
export

# Targets inherit all exported env vars automatically
deploy: describe lint test build
	@printf "$(MAGENTA)######## make deploy$(RESET)\n"
	@cd cdk && cdk deploy --all --require-approval never && cd -
.PHONY: deploy
```

## CDK Pattern (Consistent Across All Services)

Every CDK stack must:
1. Read required configs and fail loudly if missing
2. Explicitly document optional vs required
3. Pass configs to Lambda via environment variables
4. Never provide silent defaults for required values

```go
func NewXyzStack(scope constructs.Construct, id string, props XyzStackProps) *XyzStack {
    stack := awscdk.NewStack(scope, &id, &props.StackProps)

    // REQUIRED dependencies (fail if missing)
    membersAPI := awsssm.StringParameter_ValueForStringParameter(
        stack, 
        jsii.String("/"+props.EnvName+"-{service-name}/APIUrl"), 
        nil,
    )

    // OPTIONAL dependencies (explicit, documented)
    filesAPI := jsii.String("") // OPTIONAL: empty until {service-name} deployed

    function := awslambda.NewFunction(stack, jsii.String("MyFunction"), 
        &awslambda.FunctionProps{
            Environment: &map[string]*string{
                "MEMBERS_API_URL": membersAPI,    // REQUIRED
                "FILES_API_URL":   filesAPI,      // OPTIONAL
            },
        },
    )

    return &XyzStack{Stack: stack}
}
```

## Lambda Handler Pattern

Every Lambda handler must:
1. Validate required env vars at startup
2. Log missing optional env vars
3. Handle empty strings gracefully for optional features

```go
type Handler struct {
    membersAPIURL string // REQUIRED
    filesAPIURL   string  // OPTIONAL
}

func NewHandler() *Handler {
    // REQUIRED: fail if missing
    membersAPI := os.Getenv("MEMBERS_API_URL")
    if membersAPI == "" {
        log.Fatalf("MEMBERS_API_URL is required")
    }

    // OPTIONAL: log if missing but continue
    filesAPI := os.Getenv("FILES_API_URL")
    if filesAPI == "" {
        log.Printf("FILES_API_URL not configured; profile features disabled")
    }

    return &Handler{
        membersAPIURL: membersAPI,
        filesAPIURL:   filesAPI,
    }
}

// Use optional feature gracefully
func (h *Handler) GetProfilePicture(userID string) (*ProfilePicture, error) {
    if h.filesAPIURL == "" {
        return nil, nil  // Feature disabled
    }
    // ... call {service-name}
}
```

## CICD Pattern (GitHub Actions)

Every workflow must:
1. Create env files without quotes
2. Use `make deploy` (never manual cdk deploy)
3. Let Makefile export vars to all steps
4. Fail loudly if make targets fail

```yaml
- name: Create env file
  run: |
    mkdir -p env
    cat > env/.env.dev <<'EOF'
    ENV_NAME=dev
    APP_NAME=dev-{example-service}
    AWS_ACCOUNT=417772279096
    AWS_REGION=ap-southeast-2
    EOF

- name: Deploy
  run: ENV_NAME=dev make deploy
  # ↑ Makefile's -include env/.env.dev exports all vars
  # ↑ Fails loudly if any step fails
```

## Testing Pattern

Every service must test that:
1. Required configs cause failure if missing
2. Optional configs work when empty
3. Invalid configs are caught

```go
func TestRequiredConfigMissing(t *testing.T) {
    // Simulate missing MEMBERS_API_URL
    t.Setenv("MEMBERS_API_URL", "")
    t.Setenv("FILES_API_URL", "")
    
    handler := NewHandler() // Should fatal/panic
    // Verify fatal was called
}

func TestOptionalConfigEmpty(t *testing.T) {
    t.Setenv("MEMBERS_API_URL", "https://localhost:8000")
    t.Setenv("FILES_API_URL", "")
    
    h := NewHandler() // Should succeed
    pic, err := h.GetProfilePicture("user-123")
    assert.Nil(t, pic)  // Feature gracefully disabled
    assert.Nil(t, err)
}
```

## Audit Checklist

For each ERS service, verify:

- [ ] Makefile has `ENV_NAME ?= dev` and `-include env/.env.$(ENV_NAME)` + `export` at top
- [ ] `.env.dev` and `.env.prod` have no quotes on variable values
- [ ] CDK code explicitly documents REQUIRED vs OPTIONAL dependencies
- [ ] Required SSM lookups will fail if parameter missing (no silent defaults)
- [ ] Optional dependencies have explicit empty string defaults with rationale comment
- [ ] Lambda reads env vars and validates REQUIRED ones at startup
- [ ] Lambda handles empty OPTIONAL env vars gracefully
- [ ] GitHub Actions workflow uses `ENV_NAME=X make deploy`
- [ ] Tests verify required configs cause failure, optional work when empty
- [ ] Service CLAUDE.md documents all env vars and their requirements

## Decision Record

**Why fail loudly for required configs?**
- Silent defaults hide deployment errors
- Operators can't tell if a service is working or degraded
- Cross-service dependencies must be explicit

**Why allow empty for optional features?**
- Some features genuinely aren't required (e.g., profile pictures)
- Allows graceful degradation and phased deployments
- Lambda can handle empty string and skip that feature

**Why no quotes in .env files?**
- Makefile `-include` doesn't evaluate shell syntax
- Quotes become part of the variable value
- Breaks CDK and Lambda environment variable parsing

**Why Makefile exports instead of sourcing?**
- Works in CI/CD containers without /dev/tty
- GitHub Actions can't run interactive shells
- Makefile's `-include` + `export` is the only portable solution

