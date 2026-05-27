# Code Review Skill

**Used by:** lead-engineer
**Model:** claude-sonnet-4.6
**Effort:** medium — apply all sections; skip domain-specific sections that do not apply to the repo under review.

Use this skill when reviewing code changes in any repository. Apply via `/review` in your CLI or as a `.github/instructions/review.instructions.md` per-repo file.

## What This Role Does

- Reviews commits and PRs against the standards below
- Identifies violations and provides specific, actionable feedback
- Approves changes that meet all standards or requests changes with clear rationale
- Ensures architectural boundaries (CQRS, event schema, security) are not violated

## What This Role Does Not Do

- Does not rewrite code during review — requests changes and explains why
- Does not approve changes with outstanding security concerns
- Does not accept "we'll fix it later" for error handling, idempotency, or auth bypass

## Default Input

- Diff of staged/unstaged changes, or a branch diff (`git diff main..HEAD`)
- Repo context (Go service, frontend, library, infrastructure)

## Default Output

- Structured review: APPROVED / CHANGES REQUESTED
- Inline feedback grouped by category
- List of blocking issues (must fix) vs. suggestions (non-blocking)

## Review Standards

### Always Check

- [ ] PR/commit description accurately reflects the actual changes
- [ ] No stale comments, dead code, or orphaned references introduced
- [ ] Error handling is explicit — no ignored errors in Go, no swallowed promises in TypeScript
- [ ] Environment variables used in code match what is defined in `env/.env.*` files
- [ ] No secrets, tokens, or credentials in code or commit messages

### CQRS Consistency

- [ ] Command handlers (write path) must NOT read/query data for business decisions
- [ ] Query handlers (read path) must NOT write or mutate data
- [ ] Event consumers must be idempotent — safe to replay without side effects duplication

### Event Architecture

- [ ] Event kind constants match the platform's allocated event kind registry
- [ ] Domain event structure is correct: id, pubkey, created_at, kind, tags, content, sig
- [ ] SNS/SQS message unwrapping follows the standard envelope pattern
- [ ] New event kinds have been allocated (not ad hoc)
- [ ] Event schema versions are explicit — breaking changes require a new version

### Go Services

- [ ] No `panic()` in production code paths
- [ ] Table-driven tests for all business logic
- [ ] golangci-lint passes without suppressed warnings
- [ ] Lambda handlers use dependency injection — no global mutable state
- [ ] AWS clients created once in `main()`, not per-invocation

### Frontend

- [ ] Optimistic updates follow CQRS pattern (update cache, then schedule revalidation)
- [ ] All API calls go through the resilience layer (retry, token refresh, maintenance mode)
- [ ] No direct token access outside the auth module

### Security

- [ ] IAM SigV4 signing for all inter-service calls — not API keys or static credentials
- [ ] JWT validation at API Gateway level only — not re-validated inside Lambda handlers
- [ ] Backend services do not accept JWT directly (IAM auth only)
- [ ] No overly permissive IAM policies (`*` actions or resources)

## Per-Repo Instructions File

Copy the Review Standards section above into `.github/instructions/review.instructions.md` in each repo. Both automated PR review tools and manual `/review` invocations will use it.

```markdown
# Review Instructions

<!-- paste Review Standards section here -->
```

## Quality Checklist (for the reviewer)

- [ ] Every section of Review Standards checked — not just the sections that seem relevant
- [ ] Blocking issues clearly labelled as blocking
- [ ] Suggestions clearly labelled as non-blocking
- [ ] Security section never skipped, even for "trivial" changes

## Escalation Rules

- If a security issue is found, block the PR immediately and notify the author — do not merge with a "fix it later" note
- If an event kind conflict is detected (same number used for different events), escalate to lead-engineer and block until resolved — this is a data corruption risk
- If a test coverage gap is found in business logic, request tests — do not accept "we'll add coverage later" for core domain logic
