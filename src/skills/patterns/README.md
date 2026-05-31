# Patterns — Reusable Coding & Architecture Patterns

**Proven patterns for implementation, infrastructure, resilience, and event handling.**

These skills document reusable patterns extracted from production agentic-engineers code. Use when implementing new features or services following established best practices.

## Skills in This Directory

| Skill | Used By | Purpose |
|-------|---------|---------|
| **implementation-coding.md** | Engineer | TDD workflow (RED → GREEN → REFACTOR) |
| **lambda-handler.md** | Engineer, Senior | Lambda handler scaffolding (HTTP API, Event Consumer) |
| **makefile.md** | Engineer, Senior | Standard Makefile pattern (describe → lint → test → build → deploy) |
| **local-ci.md** | Engineer | Local CI pipeline (verify + review + diff) |
| **api-resilience.md** | Senior Engineer | Resilient API client patterns (retry, token refresh, maintenance) |
| **event-consumer.md** | Senior Engineer | Event consumer pattern (SNS FIFO → SQS FIFO → Lambda with idempotency) |
| **cdk-stack.md** | Engineer, Senior | CDK infrastructure patterns (3-tier stack architecture) |
| **git-workflow.md** | All roles | Git best practices and trunk-based development |

## When to Use These Skills

- **Before writing code** — Check implementation-coding.md for TDD workflow
- **Building new Lambda service** — Reference lambda-handler.md scaffold
- **Creating Makefile** — Use makefile.md as template
- **Running pre-push CI** — Follow local-ci.md for validation
- **Building resilient API client** — Use api-resilience.md patterns
- **Building event consumer** — Use event-consumer.md patterns
- **Creating infrastructure** — Use cdk-stack.md as CDK reference
- **Committing code** — Follow git-workflow.md standards

## Pattern Hierarchy

These patterns are ordered by **scope**:

1. **Code patterns** (implementation-coding, makefile, lambda-handler)
2. **Infrastructure patterns** (cdk-stack)
3. **Service patterns** (api-resilience, event-consumer, local-ci)
4. **Workflow patterns** (git-workflow)

## Key Principles

All patterns follow these principles:
- **Production-tested** — Used in live agentic-engineers services
- **Minimal** — No unnecessary abstractions
- **Documented** — Examples included
- **Reusable** — Work across projects
- **Composable** — Can be combined (e.g., TDD + lambda-handler)

## See Also

- `../shared/` — Cross-cutting utilities
- `../testing/` — Testing patterns
- `../roles/` — Which roles use which patterns
