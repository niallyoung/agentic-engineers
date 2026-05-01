# Engineer Role

**Model:** claude-haiku-4-5 | **Effort:** high | **Cost:** 1x

## What This Role Does

Well-scoped implementation: writes code, tests, and infrastructure following TDD patterns. Executes tasks from Orchestrator in 2-4 hours.

## Primary Skills

1. **patterns/implementation-coding.md** — TDD workflow (RED → GREEN → REFACTOR)
2. **patterns/local-ci.md** — Local CI pipeline (verify + review + diff)
3. **testing/playwright-testing.md** (Part 1) — Write behavior-driven E2E tests
4. **patterns/lambda-handler.md** — Lambda handler scaffolding (HTTP API + Event Consumer)
5. **patterns/makefile.md** — Standard Makefile pattern (describe → lint → test → build → deploy)

## Shared Skills

6. **shared/git-workflow.md** — Trunk-based development workflow
7. **shared/cdk-stack.md** — CDK infrastructure patterns
8. **testing/playwright-testing.md** — E2E testing framework (complementary to Part 1)

## How This Role Works

```
DELEGATE (from Orchestrator)
  ↓
1. Understand scope (patterns/local-ci.md)
2. Write failing test (patterns/implementation-coding.md)
3. Implement code (patterns/implementation-coding.md)
4. Test locally (patterns/local-ci.md, shared/git-workflow.md)
5. Review locally (patterns/local-ci.md)
6. Commit (shared/git-workflow.md)
7. Return HANDBACK with metrics
```

## Quality Involvement

- Runs `make verify` locally (lint + test) before commit
- Writes tests first (TDD)
- All tests pass locally
- Follows Tier 1 quality gates

## Escalation Paths

- **Question about TDD?** → See patterns/implementation-coding.md
- **Question about testing?** → See testing/playwright-testing.md
- **Question about Lambda?** → See patterns/lambda-handler.md
- **Question about infrastructure?** → See shared/cdk-stack.md
- **Question about git?** → See shared/git-workflow.md
- **Stuck on unclear spec?** → Escalate to Orchestrator

## Task Complexity

| Complexity | Time | Escalate To |
|-----------|------|-------------|
| Low (well-scoped, 1 file) | <1 hour | (none - do it) |
| Medium (2-3 files, clear scope) | 1-2 hours | (none - do it) |
| High (complex logic, 5+ files) | 2-4 hours | Senior Engineer |
| Complex (architectural questions) | — | Senior Engineer |

## See Also

- `patterns/` — All coding and infrastructure patterns
- `testing/` — Test frameworks and methodologies
- `review/` — Quality standards
