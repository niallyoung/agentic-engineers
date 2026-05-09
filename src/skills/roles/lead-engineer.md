# Lead Engineer Role

**Model:** claude-sonnet-4-6 | **Effort:** high + thinking | **Cost:** 3x

## What This Role Does

Quality verification, code review, medium-level planning, escalation decisions. Final gate before code merges.

## Primary Skills

1. **shared/quality-assessment-baseline.md** — Blocking authority framework
   - Section 3: Blocking criteria (what makes code unmergeable)
   - Section 6: Role coordination (Lead's authority and responsibilities)
   - Use this as source of truth for APPROVE/REWORK/ESCALATE decisions

2. **shared/core-engineering-baseline.md** — Baseline skills shared by all 4 engineer roles
   - Section 1: Git Workflow
   - Section 3: Code Review Standards (authority)
   - Section 4: Testing Overview
   - Section 5: GitHub CLI Essentials
   - Section 6: CDK Stack Patterns (read-only context)
   - Section 2: TDD & Implementation (read-only context)

## Specialist Skills (Lead Engineer)

3. **review/code-review.md** — Authority on 8-point checklist, blocking decisions
4. **review/code-quality-analysis.md** — Code quality scoring and assessment
5. **orchestration/todo-management.md** — Code review planning and session management
6. **monitoring/cicd-watch.md** — Pipeline operations and monitoring

## Detailed References (Deep Dives)

- `patterns/lambda-handler.md` — Infrastructure verification context

## When Escalated To

- Code review of complex/critical changes
- Quality gate disputes
- Pipeline failures to diagnose
- Escalation decisions

## Escalation To

- Architecture questions → Principal Engineer
- Security concerns → Security Engineer
- Performance issues → Senior Engineer + Orchestrator

## See Also

- `review/` — All review and quality skills
- `monitoring/` — Pipeline monitoring
- `orchestration/QUALITY.md` — Quality gates this role enforces
