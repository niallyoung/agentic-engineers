# Quality Standards

**What makes a good DELEGATE and HANDBACK**

This document describes the quality expectations for task-handoff YAML blocks
flowing through the agentic-engineers orchestration system.  It is the human-
readable companion to the machine-enforced rules in
[quality-validation-rules.md](quality-validation-rules.md).

---

## Why Quality Standards Exist

Every DELEGATE block is a contract between the Orchestrator and an agent.
A vague, incomplete, or structurally invalid contract causes:

- **Rework loops** — agent produces wrong output, task re-queued
- **Mis-routing** — task sent to wrong role, wasted tokens and time
- **Lost context** — HANDBACK cannot be correlated to its DELEGATE
- **Stalled pipelines** — validation fails, task blocked in queue

Following these standards eliminates the most common failure modes before work
even starts.

---

## DELEGATE Standards

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `handoff_type` | string | **Must be `DELEGATE`** — identifies block type |
| `task_id` | string | Unique task identifier (see format below) |
| `role` | string | Target agent role (see valid roles below) |
| `scope` | string | What must be accomplished (see scope standards) |
| `effort` | string | Effort estimate: `low`, `medium`, `high`, `max`, `epic` |

### Recommended Fields

| Field | When Required | Description |
|-------|---------------|-------------|
| `plan` | Always for `effort: high/max/epic` | Numbered steps the agent should follow |
| `success_criteria` | Always for `effort: high/max/epic` | Measurable acceptance criteria |
| `model` | Optional | Preferred model (defaults to role default) |
| `blocked_by` | When applicable | Task IDs this task depends on |
| `context` | Optional | Relevant background / links to prior work |

---

### `task_id` Format

```
[a-z0-9][a-z0-9\-]{0,62}[a-z0-9]
```

- **Lowercase alphanumeric and hyphens only** — no spaces, underscores, or uppercase
- **2–64 characters**
- **Descriptive and unique** — include feature/area name
- Must be **stable across retries** (same task = same base ID, add `-retry-N` suffix for rework)

**Good examples:**
```
implement-auth-service
fix-login-validation-bug
migrate-db-schema-v3
quality-gates-phase3
```

**Bad examples:**
```
task1                   # too generic
Fix_Login_Bug           # uppercase + underscores
my task                 # spaces
implement-the-new-authentication-service-with-jwt-and-refresh-logic-v2  # too long (>64)
```

---

### Scope Standards

The `scope` field is the most important quality signal.  A good scope:

1. **Contains an action verb** — what should be *done*: implement, fix, create, refactor, migrate, investigate, validate, configure
2. **Names the subject** — what component, service, or behaviour is affected
3. **States the outcome** — what success looks like in concrete terms
4. **Is ≥ 15 words** for non-trivial tasks (5 words minimum is enforced)

**Good scope (high effort):**
```yaml
scope: |
  Implement a JWT authentication service that provides secure login, logout,
  and token refresh endpoints.  Service must support RS256 signing, 1-hour
  token expiry, and blacklisting revoked tokens in Redis.  Expose via REST
  at /auth/login, /auth/logout, /auth/refresh.
```

**Poor scope (vague):**
```yaml
scope: Authentication work
```

**Poor scope (too short):**
```yaml
scope: Fix the bug
```

---

### Plan Standards (required for high/max/epic effort)

Plans must:

- Be a **numbered list of concrete steps**
- Each step should be independently verifiable
- Steps should cover: design → implementation → testing → documentation
- Avoid vague phrases like "just do it" or "implement everything"

**Good plan:**
```yaml
plan: |
  1. Create auth module skeleton in src/auth/.
  2. Implement JWT token generation with RS256 signing.
  3. Add /auth/login endpoint with bcrypt password verification.
  4. Add /auth/logout endpoint with Redis token blacklisting.
  5. Add /auth/refresh endpoint with sliding-window expiry.
  6. Write unit tests for all endpoints (target: 90%+ coverage).
  7. Update API documentation in docs/api.md.
```

**Poor plan:**
```yaml
plan: Implement the auth service end to end.
```

---

### Role Selection Guide

| Role | When to Use | Effort Range |
|------|-------------|--------------|
| `engineer` | Well-scoped tasks with a clear plan | low, medium |
| `senior_engineer` | Complex tasks requiring design decisions | medium, high |
| `lead_engineer` | Code review, team quality gates, critical path changes | medium, high |
| `principal_engineer` | Cross-service architecture, strategic design | high, max, epic |
| `quality_engineer` | Quality audits, test strategy, coverage analysis | low, medium |
| `model_engineer` | Token/cost analysis, model selection optimisation | low, medium |
| `security_engineer` | Security review, IAM changes, secret management | high, max |
| `orchestrator` | Queue management, routing decisions | low, medium |

---

### Secrets Policy

**Never embed secrets in DELEGATE blocks.**

The queue is stored on disk and may be logged.  If a DELEGATE is found to
contain a field named `password`, `token`, `secret`, `api_key`, `private_key`,
or `credential`, the Quality Validator will flag it as CRITICAL and block routing.

Instead, use environment variable references:
```yaml
scope: "Rotate the database password stored in AWS Secrets Manager (secret: db/prod/password)"
```

---

## HANDBACK Standards

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `handoff_type` | string | **Must be `HANDBACK`** |
| `task_id` | string | **Must match the original DELEGATE `task_id`** |
| `status` | string | `complete`, `failed`, or `partial` |
| `notes` | string | Summary of what was delivered (≥ 5 words) |

### Recommended Fields

| Field | When Required | Description |
|-------|---------------|-------------|
| `tests_passed` | Engineering roles | e.g. `47/47` — tests that pass |
| `deliverables` | For `effort: high/max/epic` | List of concrete artefacts produced |
| `duration_minutes` | Optional | Actual wall-clock time taken |
| `model` | Optional | Model actually used |
| `tokens_in` / `tokens_out` | Optional | Token usage for metrics |

---

### Status Field Values

| Status | Meaning |
|--------|---------|
| `complete` | All scope items done, success criteria met |
| `partial` | Some items done; `notes` must explain what's missing and why |
| `failed` | Task could not be completed; `notes` must explain the failure in ≥ 5 words |

**Failure notes must explain the reason:**

Good:
```yaml
status: failed
notes: "External Stripe API returned 503 on all 3 retry attempts. Needs manual investigation."
```

Poor:
```yaml
status: failed
notes: "Error"
```

---

### Deliverables Documentation

For high-effort tasks, list concrete artefacts:

```yaml
deliverables:
  - "src/auth/service.py — JWT authentication service (247 lines)"
  - "tests/test_auth.py — unit tests (89 lines, 23 test cases)"
  - "docs/api.md — API reference updated with auth endpoints"
```

---

### Quality Checklist Before Emitting HANDBACK

Before writing a HANDBACK block, verify:

- [ ] All `plan` steps were executed (or deviation documented in `notes`)
- [ ] Tests were added for new behaviour
- [ ] `tests_passed` reflects actual test run output
- [ ] No hardcoded secrets or debug print statements in deliverables
- [ ] `task_id` **exactly matches** the DELEGATE `task_id`
- [ ] `notes` contains a meaningful summary (not just "done")

---

## Quality Score Thresholds

The Quality Validator assigns a composite score (0–100) and routes tasks accordingly:

| Score Range | Routing | Action |
|-------------|---------|--------|
| 80–100 | HIGH | Direct dispatch to role agent |
| 60–79 | MEDIUM | Route to Lead Engineer for refinement |
| 40–59 | LOW | Route to Principal Engineer for redesign |
| < 40 or CRITICAL finding | CRITICAL | Escalate with detailed analysis |

---

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| `scope: authentication` | No verb, no detail | Add action and outcome |
| `plan: implement everything` | Not actionable | Number the steps |
| `task_id: task1` | Not unique, not descriptive | Use kebab-case description |
| Missing `success_criteria` for epic task | Can't verify completion | Add measurable criteria |
| `status: done` in HANDBACK | Not a valid status value | Use `complete` |
| `notes: ok` on a failed task | No explanation | Explain the failure |
| `effort: high` with `role: engineer` | Likely mis-routed | Escalate to senior_engineer |

---

## Glossary

| Term | Definition |
|------|------------|
| DELEGATE | Task specification sent to an agent |
| HANDBACK | Completion report returned by an agent |
| Quality Score | 0–100 composite score from Layer 1 + Layer 2 + Layer 3 validation |
| Routing Decision | HIGH / MEDIUM / LOW / CRITICAL — determines next step for a task |
| Layer 1 | Pre-routing structural validation |
| Layer 2 | Task quality / routing optimisation validation |
| Layer 3 | Post-completion HANDBACK validation |
