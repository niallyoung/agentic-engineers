# Engineer Role

**Model:** claude-haiku-4-5 | **Effort:** high | **Cost:** 1x

## What This Role Does

Well-scoped implementation: writes code, tests, and infrastructure following TDD patterns. Executes tasks from Orchestrator in 2-4 hours.

## Primary Skills

1. **shared/core-engineering-baseline.md** — Baseline skills shared by all 4 engineer roles
   - Section 1: Git Workflow
   - Section 2: TDD & Implementation
   - Section 3: Code Review Standards
   - Section 4: Testing Overview (Playwright)
   - Section 5: GitHub CLI Essentials
   - Section 6: CDK Stack Patterns

2. **shared/quality-assessment-baseline.md** — Shared quality framework for self-evaluation
   - Use Sections 1-2 to understand quality dimensions and scoring bands
   - Self-evaluate before requesting Lead Engineer review

3. **shared/engineer-specifics.md** — Engineer-only specialist skills
   - Local CI Pipeline (Section 1)
   - Lambda Handler Patterns (Section 2)
   - Makefile Standards (Section 3)

4. **monitoring/cicd-watch.md** — Monitor CI/CD pipelines after pushing code
5. **orchestration/todo-management.md** — Track and manage task todos

## Detailed References (Deep Dives)

- `patterns/implementation-coding.md` — Complete TDD workflow (referenced in baseline)
- `patterns/local-ci.md` — Complete Local CI reference (referenced in engineer-specifics)
- `testing/playwright-testing.md` — Complete Playwright reference (Part 1 for engineers)
- `patterns/lambda-handler.md` — Complete Lambda patterns (referenced in engineer-specifics)
- `patterns/makefile.md` — Complete Makefile reference (referenced in engineer-specifics)

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
- **Question about quality assessment?** → See shared/quality-assessment-baseline.md
- **Stuck on unclear spec?** → Escalate to Orchestrator

## Pattern Ownership

- `patterns/api-resilience.md` and `patterns/event-consumer.md` are Advanced Patterns authored by Senior Engineer
- Engineers implement these patterns with reference to Senior Engineer documentation
- Questions about these patterns should be escalated to Senior Engineer

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
