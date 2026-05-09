# Engineer-Specific Skills

**Role:** Engineer (Implementation Specialist)  
**Purpose:** Deep-dive knowledge for Engineer role that extends the Core Engineering Baseline.

These skills are specialized for the Engineer implementation role and should NOT be assumed to apply to other roles (Senior Engineer, Lead Engineer, Quality Engineer). They complement the shared baseline with Engineer-specific patterns, tools, and workflows.

---

## Section 1: Local CI Pipeline

Running the full local CI pipeline before pushing ensures code quality gates are met.

### What Local CI DOES

- Runs lint + unit tests (`make verify`) — same as the pre-commit hook
- Runs E2E tests when applicable (frontend applications only)
- Shows a diff of what would be pushed
- Reports pass/fail for each step clearly

### What Local CI DOES NOT DO

- Does not deploy — cloud CI handles deployment after push
- Does not run code review automatically — that is a manual, discretionary step
- Does not skip steps unless the repo type genuinely does not apply

### Pipeline Stages

#### 1. Git State Check

```bash
# Ensure on the correct branch and working tree is clean
git branch --show-current   # should be main for trunk-based flow
git status --porcelain      # show any uncommitted changes
```

#### 2. Lint + Unit Tests (same as pre-commit)

```bash
ENV_NAME=dev make verify    # runs: make lint && make test
```

- Every repo has a `verify` target (or separate `lint` + `test` targets)
- Repos without a Makefile skip gracefully

#### 3. E2E Tests (frontend apps only)

```bash
CI=true npx playwright test    # runs Playwright across all browsers
```

- Only applicable in frontend application repos
- Skip in Go service repos

#### 4. Code Review (optional — user's discretion)

Invoke the `/review` skill manually when desired. Not part of the automated pipeline. User controls frequency — not every commit needs a model review.

#### 5. Diff Review

```bash
# Show what would be pushed
git --no-pager diff --color -U5 --stat origin/main..HEAD
git --no-pager diff --color -U5 origin/main..HEAD
```

### Repo Type Detection

Detect repo type from the working directory:

| Signals | Type | Steps |
|---------|------|-------|
| `go.mod` + `Makefile` + `cdk/` | Go service | `make verify` |
| `go.mod` + `Makefile`, no `cdk/` | Go library | `make verify` |
| `package.json` + `vite.config.ts` | Frontend app | `make verify` + E2E |
| No `Makefile` | Meta/docs repo | diff only |

### Environment

- `ENV_NAME=dev` is the default for local runs
- Go services: use golangci-lint version pinned in `Makefile`
- Frontend: Node 20+, Playwright (run `npx playwright install` if browsers missing)

### Non-Interactive Mode

For automated contexts, set an env var to skip interactive diff review and push confirmation while still running all quality gates:

```bash
AUTO_PUSH=1 git push    # runs E2E (frontend), skips diff review + confirm
```

Three push modes:
- **Interactive** (default): `git push` → E2E + diff review + confirm prompt
- **Non-interactive**: `AUTO_PUSH=1 git push` → E2E only, auto-approve
- **Emergency bypass**: `git push --no-verify` → skips all hooks (never use unless truly unavoidable)

### Quality Checklist

- [ ] Steps run in order: git state → lint+test → E2E (if applicable) → diff
- [ ] Stop on first failure and report clearly
- [ ] `ENV_NAME=dev` set for all `make` invocations
- [ ] E2E run with `CI=true` — not bare `npx playwright test`
- [ ] Diff reviewed before push (automated or manual)

### Escalation Rules

- If lint fails with a rule that seems wrong or overly strict, escalate to lead-engineer before disabling the rule
- If E2E tests are flaky (fail intermittently without code changes), escalate to quality-engineer
- If `make verify` is unavailable (no Makefile), check the repo's README for the equivalent command before skipping

---

## Section 2: Lambda Handler Patterns

Go Lambda functions follow two main archetypes. Ensure AWS clients are created once in `main()` and reused across invocations.

### What Lambda Handler DOES

- Scaffolds Lambda `main()` with dependency injection and AWS SDK client setup
- Implements HTTP API handlers (routing, JWT claim extraction, structured error responses)
- Implements SQS event consumer handlers (message unwrapping, idempotency, event routing)
- Ensures AWS clients are created once in `main()` and reused across invocations

### What Lambda Handler DOES NOT DO

- Does not provision CDK infrastructure (see `cdk-stack.md`)
- Does not design event schemas or allocate event kind numbers
- Does not write business logic — delegates to domain functions/services

### Archetype A: HTTP API Handler

Single Lambda behind API Gateway with JWT authorizer. Receives HTTP requests, routes to handlers.

```go
package main

import (
	"context"
	"os"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go-v2/config"
)

func main() {
	cfg, err := config.LoadDefaultConfig(context.Background())
	if err != nil {
		panic("unable to load SDK config: " + err.Error())
	}

	// Dependency injection — create clients once, reuse across invocations
	iamClient := NewIAMSigningClient(cfg)
	appName := os.Getenv("APP_NAME")

	handler := &Handler{
		iamClient: iamClient,
		appName:   appName,
	}

	lambda.Start(handler.Route)
}

// Route dispatches based on HTTP method + path
func (h *Handler) Route(ctx context.Context, req events.APIGatewayV2HTTPRequest) (events.APIGatewayV2HTTPResponse, error) {
	// Extract user context from JWT claims (set by API Gateway authorizer)
	userID := req.RequestContext.Authorizer.JWT.Claims["sub"]
	userEmail := req.RequestContext.Authorizer.JWT.Claims["email"]

	switch req.RouteKey {
	case "POST /commands/CreateItem":
		return h.handleCreateItem(ctx, req, userID, userEmail)
	case "GET /queries/ListItems":
		return h.handleListItems(ctx, req, userID)
	default:
		return respond(404, `{"error":"not found"}`)
	}
}

func respond(status int, body string) (events.APIGatewayV2HTTPResponse, error) {
	return events.APIGatewayV2HTTPResponse{
		StatusCode: status,
		Headers:    map[string]string{"Content-Type": "application/json"},
		Body:       body,
	}, nil
}
```

### Archetype B: Event Consumer

Lambda triggered by SQS FIFO queue. Processes domain events with idempotency tracking.

```go
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
)

const (
	StatusProcessing = "PROCESSING"
	StatusCompleted  = "COMPLETED"
	StatusFailed     = "FAILED"
)

func main() {
	cfg, err := config.LoadDefaultConfig(context.Background())
	if err != nil {
		panic("unable to load SDK config: " + err.Error())
	}

	ddb := dynamodb.NewFromConfig(cfg)
	tableNames := map[string]string{
		"idempotency": os.Getenv("IDEMPOTENCY_TABLE"),
		"events":      os.Getenv("EVENTS_TABLE"),
	}

	handler := &Handler{
		ddb:        ddb,
		tableNames: tableNames,
	}

	lambda.Start(handler.ProcessMessage)
}

// ProcessMessage handles SQS messages containing domain events
func (h *Handler) ProcessMessage(ctx context.Context, sqsEvent events.SQSEvent) error {
	for _, msg := range sqsEvent.Records {
		var domainEvent DomainEvent
		if err := json.Unmarshal([]byte(msg.Body), &domainEvent); err != nil {
			log.Printf("Failed to unmarshal event: %v", err)
			return err
		}

		// Check idempotency: if already processed, skip silently
		key := fmt.Sprintf("event#%s", domainEvent.ID)
		idempotencyKey, err := h.getIdempotencyKey(ctx, key)
		if err != nil {
			return err
		}
		if idempotencyKey == StatusCompleted {
			log.Printf("Event %s already processed", domainEvent.ID)
			continue
		}

		// Mark as processing
		if err := h.setIdempotencyKey(ctx, key, StatusProcessing); err != nil {
			return err
		}

		// Process the event
		if err := h.handleEvent(ctx, domainEvent); err != nil {
			h.setIdempotencyKey(ctx, key, StatusFailed)
			return err
		}

		// Mark as completed
		if err := h.setIdempotencyKey(ctx, key, StatusCompleted); err != nil {
			return err
		}
	}

	return nil
}
```

### Key Principles

1. **Dependency Injection**: Create AWS clients once in `main()`, pass to handler
2. **No Global State**: Handler struct holds all state
3. **Explicit Error Handling**: Return errors, don't panic
4. **Idempotency**: Event consumers track processed event IDs
5. **Structured Logging**: Use JSON logs for debugging

---

## Section 3: Makefile Standards

Makefile pattern for Go microservices. Ensures quality gates cannot be bypassed.

### What Makefile DOES

- Scaffolds the standard 3-phase Makefile (environment loading → quality gates → CDK deploy)
- Adds per-Lambda lint/test/build targets for each function in the service
- Ensures `deploy` always depends on `all` (quality gates cannot be bypassed)

### What Makefile DOES NOT DO

- Does not write Makefile targets for non-Go languages — adapt the pattern for your toolchain
- Does not configure CI/CD workflows — Makefile is for local and cloud-CI use only
- Does not manage environment files — those live in `env/.env.{ENV_NAME}` and are repo-specific

### Pattern Overview

All Go services follow a 3-phase Makefile:

1. **Environment loading**: `cp -f env/.env.${ENV_NAME} env/.env && set -a && source env/.env && set +a`
2. **Quality gates**: `all: describe lint test build` (always in this order)
3. **Local verification**: `verify: lint test` (fast dev-loop target, no build/deploy)
4. **CDK deploy**: `deploy: all` (deploys only after all gates pass)

### Template

```makefile
SHELL:=/bin/bash

ENV_NAME?=prod
NAME:={{SERVICE_NAME}}
HASH:=$(shell git rev-parse --short HEAD 2>/dev/null || echo "dev")

all: describe lint test build
.PHONY: all

# Local verification (lint + test, no build/deploy)
verify: lint test
.PHONY: verify

clean:
	@printf "$(MAGENTA)################ make clean$(RESET)\n"
	rm -rf ./cdk/cdk.out ./cdk/node_modules ./cdk/cdk.context.json
	{{CLEAN_LAMBDA_LINES}}
.PHONY: clean

describe:
	@printf "$(MAGENTA)################ make describe$(RESET)\n"
	@cp -f env/.env.${ENV_NAME} env/.env && \
	set -a && source env/.env && set +a && \
	echo "ENV_NAME=$$ENV_NAME" && \
	echo "APP_NAME=$$APP_NAME" && \
	echo "AWS_ACCOUNT=$$AWS_ACCOUNT" && \
	echo "AWS_REGION=$$AWS_REGION"
.PHONY: describe

lint: cdk.lint {{LAMBDA_LINT_TARGETS}}
.PHONY: lint

test: cdk.test {{LAMBDA_TEST_TARGETS}}
.PHONY: test

build: cdk.build
.PHONY: build

cdk.synth:
	@printf "$(MAGENTA)######## make cdk.synth$(RESET)\n"
	@cp -f env/.env.${ENV_NAME} env/.env && \
	set -a && source env/.env && set +a && \
	cd cdk && cdk synth -q && cd -
.PHONY: cdk.synth

cdk.build: {{LAMBDA_BUILD_TARGETS}} cdk.synth
	@printf "$(MAGENTA)######## make cdk.build$(RESET)\n"
.PHONY: cdk.build

cdk.lint:
	@printf "$(MAGENTA)################ make cdk.lint$(RESET)\n"
	@cp -f env/.env.${ENV_NAME} env/.env && \
	set -a && source env/.env && set +a && \
	cd cdk && go run github.com/golangci/golangci-lint/cmd/golangci-lint@{{GOLANGCI_VERSION}} run --timeout=5m ./... && cd -
.PHONY: cdk.lint

cdk.test:
	@printf "$(MAGENTA)################ make cdk.test$(RESET)\n"
	@cp -f env/.env.${ENV_NAME} env/.env && \
	set -a && source env/.env && set +a && \
	cd cdk && go test ./... && cd -
.PHONY: cdk.test

# Per-Lambda targets — repeat this block for each Lambda function:
#
# lambda.{{LAMBDA_NAME}}.lint:
# 	@printf "$(MAGENTA)################ make lambda.{{LAMBDA_NAME}}.lint$(RESET)\n"
# 	cd lambda/{{LAMBDA_NAME}} && go run github.com/golangci/golangci-lint/cmd/golangci-lint@{{GOLANGCI_VERSION}} run --timeout=5m ./... && cd -
# .PHONY: lambda.{{LAMBDA_NAME}}.lint
#
# lambda.{{LAMBDA_NAME}}.build:
# 	@printf "$(MAGENTA)################ make lambda.{{LAMBDA_NAME}}.build$(RESET)\n"
# 	cd lambda/{{LAMBDA_NAME}} && GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -tags lambda.norpc -o bootstrap . && zip bootstrap.zip bootstrap && cd -
# .PHONY: lambda.{{LAMBDA_NAME}}.build
#
# lambda.{{LAMBDA_NAME}}.test:
# 	@printf "$(MAGENTA)################ make lambda.{{LAMBDA_NAME}}.test$(RESET)\n"
# 	cd lambda/{{LAMBDA_NAME}} && go test ./... && cd -
# .PHONY: lambda.{{LAMBDA_NAME}}.test
#
# {{LAMBDA_NAME}}_GOARCH?=amd64  # Override to arm64 if needed
#
# After updating per-Lambda targets, the main `lint`, `test`, `build` targets automatically include all per-Lambda steps.

# Deployment (only after all quality gates pass)
deploy: all
	@printf "$(MAGENTA)################ make deploy$(RESET)\n"
	@cp -f env/.env.${ENV_NAME} env/.env && \
	set -a && source env/.env && set +a && \
	cd cdk && cdk deploy --all --require-approval never && cd -
.PHONY: deploy
```

### Per-Lambda Targets

For each Lambda function in the service, create explicit targets:

```makefile
# Example for "create-item" Lambda
lambda.create-item.lint:
	@printf "$(MAGENTA)################ make lambda.create-item.lint$(RESET)\n"
	cd lambda/create-item && \
	go run github.com/golangci/golangci-lint/cmd/golangci-lint@v1.54 run --timeout=5m ./... && \
	cd -
.PHONY: lambda.create-item.lint

lambda.create-item.test:
	@printf "$(MAGENTA)################ make lambda.create-item.test$(RESET)\n"
	cd lambda/create-item && go test ./... && cd -
.PHONY: lambda.create-item.test

lambda.create-item.build:
	@printf "$(MAGENTA)################ make lambda.create-item.build$(RESET)\n"
	cd lambda/create-item && \
	GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -tags lambda.norpc -o bootstrap . && \
	zip bootstrap.zip bootstrap && \
	cd -
.PHONY: lambda.create-item.build
```

Then add the per-Lambda targets to the main pipeline:

```makefile
lint: cdk.lint lambda.create-item.lint lambda.list-items.lint
.PHONY: lint

test: cdk.test lambda.create-item.test lambda.list-items.test
.PHONY: test

build: lambda.create-item.build lambda.list-items.build cdk.build
.PHONY: build
```

### Key Principles

1. **Environment Loading First**: Every target starts with environment setup
2. **Quality Gates Mandatory**: `deploy` always depends on `all` (no bypasses)
3. **Clear Phase Names**: `describe` → `lint` → `test` → `build` → `deploy`
4. **Per-Lambda Parallelism**: Makefile automatically parallelizes per-Lambda targets
5. **Fast Feedback Loop**: `verify` target for quick local checks (lint + test, no build)

---

## Integration with Baseline

These Engineer-specific skills:
- Assume mastery of **Core Engineering Baseline** (all 6 sections)
- Assume TDD workflow (Section 2 of baseline)
- Assume Git workflow compliance (Section 1 of baseline)
- Are ONLY for Engineer role — do not assume other roles need them

---

## See Also

- **Core Engineering Baseline:** `skills/shared/core-engineering-baseline.md` (all 4 roles)
- **Engineer Role Guide:** `skills/roles/engineer.md`
- **Local CI Detailed Reference:** `skills/patterns/local-ci.md`
- **Lambda Handler Detailed Reference:** `skills/patterns/lambda-handler.md`
- **Makefile Detailed Reference:** `skills/patterns/makefile.md`
