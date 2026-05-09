# Testing — Testing Methodologies & Frameworks

**Skills for writing and validating automated tests.**

## Skills in This Directory

| Skill | Used By | Purpose |
|-------|---------|---------|
| **playwright-testing.md** | Engineer, Quality Engineer | E2E testing with Playwright (development + validation) |

## Part 1: Test Development (Engineer)
- Write behavior-driven E2E tests
- Page object model patterns
- Happy path + error cases

## Part 2: Test Execution (Quality Engineer)
- Run full E2E suite in CI=true mode
- Debug test failures
- Validate test results for quality gates

## When to Use

- **Writing E2E tests** — Engineer uses Part 1 of playwright-testing.md
- **Running/validating tests** — Quality Engineer uses Part 2 of playwright-testing.md
- **Debugging test failures** — Both roles use debugging section

## Test Hierarchy

1. Unit tests (vitest, handled by engineers)
2. Integration tests (using Playwright, shared pattern)
3. E2E tests (full workflow, shared pattern)

## See Also

- `../patterns/` — TDD and local CI patterns
- `../review/` — Quality gate testing requirements
- Root CLAUDE.md — {service-name} architecture and testing strategy
