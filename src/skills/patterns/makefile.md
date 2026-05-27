# Makefile Skill

**Used by:** engineer
**Model:** claude-sonnet-4.6
**Effort:** low — copy template, replace placeholders, add per-Lambda targets.

Use this skill when creating or modifying a Makefile for a Go microservice that deploys via AWS CDK and Lambda.

## What This Role Does

- Scaffolds the standard 3-phase Makefile (environment loading → quality gates → CDK deploy)
- Adds per-Lambda lint/test/build targets for each function in the service
- Ensures `deploy` always depends on `all` (quality gates cannot be bypassed)

## What This Role Does Not Do

- Does not write Makefile targets for non-Go languages — adapt the pattern for your toolchain
- Does not configure CI/CD workflows — Makefile is for local and cloud-CI use only
- Does not manage environment files — those live in `env/.env.{ENV_NAME}` and are repo-specific

## Default Input

- Service name (`APP_NAME`)
- List of Lambda function names
- Architecture (amd64 for most; arm64 if explicitly required)
- golangci-lint version (match what CI uses)

## Default Output

- Complete `Makefile` at repo root with all standard targets

## Pattern

All Go services follow a 3-phase Makefile:

1. **Environment loading**: `cp -f env/.env.${ENV_NAME} env/.env && set -a && source env/.env && set +a`
2. **Quality gates**: `all: describe lint test build` (always in this order)
3. **Local verification**: `verify: lint test` (fast dev-loop target, no build/deploy)
4. **CDK deploy**: `deploy: all` (deploys only after all gates pass)

## Template

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

smoke-test:
	@printf "$(MAGENTA)################ make smoke-test$(RESET)\n"
	@cp -f env/.env.${ENV_NAME} env/.env && \
	set -a && source env/.env && set +a && \
	./scripts/smoke-test.sh
.PHONY: smoke-test

deploy: all
	@printf "$(MAGENTA)################ make deploy$(RESET)\n"
	@cp -f env/.env.${ENV_NAME} env/.env && \
	set -a && source env/.env && set +a && \
	cd cdk && cdk deploy --all --require-approval never && cd -
.PHONY: deploy

destroy:
	@printf "$(MAGENTA)################ make destroy$(RESET)\n"
	@cp -f env/.env.${ENV_NAME} env/.env && \
	set -a && source env/.env && set +a && \
	cd cdk && cdk destroy --all --force && cd -
.PHONY: destroy

ESC := \033
RED     := $(ESC)[0;31m
GREEN   := $(ESC)[0;32m
YELLOW  := $(ESC)[0;33m
BLUE    := $(ESC)[0;34m
MAGENTA := $(ESC)[0;35m
CYAN    := $(ESC)[0;36m
WHITE   := $(ESC)[0;37m
RESET   := $(ESC)[0m

.PHONY: version
version:
	@git describe --tags --always 2>/dev/null || echo "v0.0.0-untagged"
```

## Quality Checklist

- [ ] `GOARCH=amd64` used unless explicitly overridden for a specific architecture requirement
- [ ] `CGO_ENABLED=0` and `-tags lambda.norpc` on every Lambda build
- [ ] golangci-lint version pinned (match what cloud CI uses)
- [ ] Environment config loads from `env/.env.${ENV_NAME}` — not hardcoded values
- [ ] `deploy` depends on `all` — quality gates cannot be bypassed
- [ ] Per-Lambda targets follow naming convention: `lambda.{name}.lint`, `lambda.{name}.test`, `lambda.{name}.build`
- [ ] `verify` target exists for fast dev-loop use (lint + test, no build)

## Escalation Rules

- If a Lambda needs a different architecture (e.g., arm64), document the exception clearly in the Makefile comment and verify CDK runtime matches
- If a new shared `make` target is needed across all services, escalate to lead-engineer to update the template
