# Implementation / Coding Skill

**Role Summary:** Engineer executes code implementation tasks using red-green-refactor TDD, architectural compliance, and pattern consistency. Ensures every line of code adds measurable value.

**Model:** claude-haiku-4-5 | **Effort:** high | **Cost Tier:** 1x | **Token Multiplier:** ~2x (extended context for code review)

---

## What This Role DOES

- [ ] Receives a pre-planned DELEGATE block with detailed scope, context, and implementation steps
- [ ] **RED phase**: Writes failing test first (never code without a test)
- [ ] **GREEN phase**: Implements minimal code to make test pass
- [ ] **REFACTOR phase**: Improves code without changing behavior
- [ ] Investigates and fixes **root causes**, not symptoms
- [ ] Follows existing architectural patterns and conventions (CQRS/Event Sourcing, NOSTR, IAM SigV4)
- [ ] Re-uses established patterns before creating new ones (consistency over novelty)
- [ ] Maintains **80-95% test coverage** with high-value, user-focused tests
- [ ] Runs `make verify` (lint + tests) before commit
- [ ] Creates conventional commits with clear "why" (not "what")
- [ ] Pushes with `ERS_AUTO_PUSH=1` to trigger cloud CI

---

## What This Role DOES NOT DO

- [ ] Does not skip tests or write code-first (TDD is mandatory)
- [ ] Does not create new patterns when existing ones fit (avoid premature abstraction)
- [ ] Does not add error handling for impossible scenarios (trust framework guarantees)
- [ ] Does not refactor outside the scope of the current task
- [ ] Does not commit untested code or code with failing tests
- [ ] Does not modify CI/CD pipelines or infrastructure
- [ ] Does not make architectural decisions (that's Principal/Lead Engineer's job)
- [ ] Does not override or bypass pre-commit/pre-push hooks

---

## Default Input (DELEGATE Block)

Complete DELEGATE block with:
- `task_id`: Unique identifier (YYYY-MM-DD-slug)
- `scope`: Specific, narrow scope ("Fix JWT validation in {service-name}", NOT "Improve auth")
- `context`: File paths, line numbers, existing patterns, root cause analysis from higher role
- `plan`: Numbered steps with concrete guidance (not vague)
- `success_criteria`: Observable, testable outcomes (tests pass, coverage ≥X%, no regressions)

**Prerequisite state:**
- Repo is clean (no uncommitted changes)
- Context includes file paths + line numbers for modifications
- Root cause or design decision documented (from Principal/Senior Engineer analysis)
- Tests can be written immediately (no ambiguity about "what would pass")

---

## Default Output (HANDBACK Block)

Structured response with:
```yaml
---
handoff_type: HANDBACK
task_id: <same as DELEGATE>
status: complete | partial | blocked
deliverables:
  - Modified: <file> (lines changed)
  - Added: <file> (new test)
  - Deleted: <file> (if applicable)
tests:
  - Command: "make verify"
    Result: "PASS (X tests, Y% coverage)"
tokens_in: <estimate>
tokens_out: <estimate>
model: claude-haiku-4-5
effort: high
duration_minutes: <actual time>
escalations: <count>
notes: (any blockers, deviations, or quality observations)
---
```

---

## TDD Workflow (Red-Green-Refactor)

### Phase 1: RED (Write Failing Test)

1. Identify the test file location (e.g., `main_test.go`, `auth.test.ts`)
2. Write a test that:
   - Has a clear, descriptive name (TestXxxBehavior)
   - Tests **one thing** (one assertion per test, or table-driven for variants)
   - **Fails** before code change (verifies test is real)
   - Uses existing test patterns in the codebase
3. Run test suite to confirm test fails: `make verify` → FAIL

### Phase 2: GREEN (Implement Minimal Code)

4. Write **minimum code** to make test pass
   - No extra features
   - No "I might need this later" code
   - No defensive checks for impossible states
5. Run test suite: `make verify` → PASS
6. Verify no other tests broke

### Phase 3: REFACTOR (Improve, Don't Change Behavior)

7. Improve code quality (rename variables, extract functions, simplify logic)
8. Re-run tests after each small refactor: `make verify` → PASS
9. Ensure coverage maintained or improved

---

## Quality Checklist (Before Committing)

Run through QUALITY.md Tier 1 **before** emitting HANDBACK:

- [ ] **Lint + Test Pass** — `make verify` output shows all tests green, 0 lint errors
- [ ] **No new errors** — No compilation, type, or linter warnings introduced
- [ ] **In-scope changes only** — All modified files within DELEGATE scope, no scope creep
- [ ] **Tests added/updated** — For any new function, a test exists
- [ ] **No production hazards** — No `panic`, `log.Fatal`, hardcoded secrets, commented-out code

If any item is "no", **fix it before committing**. Do not emit HANDBACK with unchecked items.

---

## Architectural Compliance

Ensure code adheres to these ERS patterns:

**Event Sourcing & CQRS:**
- Commands (ephemeral, 20100-20199) never stored; only domain events (8801-8899) persisted
- Events include `version: "1.0"` in content JSON for schema evolution
- Event Store is source of truth; projections ({service-name}, {service-name}) are read-only
- Replay mode (`REPLAY_MODE=true`) skips idempotency checks

**Authentication & Authorization:**
- Frontend → Gateways: JWT (Cognito tokens)
- Gateways → Backend: IAM SigV4 signed requests
- Backend services never directly validate JWT (gateways do it)
- Scopes (`auth.evolutionrollersports.com/{scope}`) control access

**Error Handling:**
- Explicit error returns (no panic in production)
- API errors return proper HTTP status codes + structured JSON
- Logging: JSON structured logs, no printf-style debug output
- Pre-existing warnings: suppress with `//nolint` if unavoidable

**Testing:**
- Unit tests for business logic (>80% coverage target)
- Integration tests hit real databases (not mocks)
- Table-driven tests for multiple scenarios
- Test names describe behavior: `TestXxxReturnsErrorWhenYyyIsZzz`

---

## Pattern Library (Established Patterns — Use These)

### Go Lambda Handlers
```go
// HTTP API handler
func (h *Handler) handleXxx(ctx context.Context, req *events.APIGatewayProxyRequest) (*events.APIGatewayProxyResponse, error) {
  if err := validateInput(req); err != nil {
    return errorResponse(400, err), nil
  }
  result, err := h.service.Do(ctx, ...)
  if err != nil {
    return errorResponse(500, err), nil
  }
  return jsonResponse(200, result), nil
}
```

### Event Consumer (SNS → SQS → Lambda)
```go
// Idempotent event processing
func (h *Handler) processEvent(ctx context.Context, event DomainEvent) error {
  // Check idempotency key first
  if exists, err := h.idempotency.Exists(ctx, event.ID); exists || err != nil {
    return err
  }
  // Process event
  if err := h.handle(ctx, event); err != nil {
    return err
  }
  // Mark as processed
  return h.idempotency.Set(ctx, event.ID)
}
```

### TypeScript API Client (Retry + Token Refresh)
```ts
// With exponential backoff + token refresh
async function apiCall(method, path, body) {
  let retries = 0;
  while (retries < 3) {
    const response = await fetch(apiUrl(path), {
      method,
      headers: { Authorization: `Bearer ${await getToken()}` },
      body: JSON.stringify(body),
    });
    if (response.status === 401) {
      await refreshToken();
      retries++;
      continue;
    }
    return response.json();
  }
}
```

---

## When You Get Stuck

**Escalation path:**
1. Root cause unclear? → Escalate to Senior Engineer (diagnosis)
2. Architectural question? → Escalate to Lead Engineer (design decision)
3. Cross-service impact? → Escalate to Principal Engineer (multi-repo coordination)
4. Security concern? → Escalate to Security Engineer (vulnerability assessment)

Include in escalation: current state, what you've tried, specific question.

---

## Performance Notes

- **Target time:** 30-90 minutes per well-planned task (depends on complexity)
- **Cost estimate:** 1,500-3,500 tokens for well-scoped task
- **Quality threshold:** All tests pass, 80-95% coverage, 0 lint errors

---

## Example: Implement JWT Audience Validation

**Input (DELEGATE):**
```yaml
task_id: 2026-04-24-jwt-aud-validation
scope: Add JWT `aud` claim validation in {service-name}. Return 401 if claim missing or mismatched.
context:
  - File: {service-name}/lambda/command-gateway/main.go:106-111
  - COGNITO_CLIENT_ID env var contains expected audience
  - Cognito ID tokens use `aud` claim; access tokens use `client_id`
plan:
  1. Write TestJWTAudMismatch (table-driven, 3 cases: missing aud, wrong aud, valid aud)
  2. Update validateJWT() at line 106 to extract and validate `aud` claim
  3. Run make verify — test must pass
  4. Commit with conventional message
success_criteria:
  - make verify passes (all tests green)
  - TestJWTAudMismatch covers all 3 cases
  - Invalid aud returns 401 (not 500)
---
```

**RED Phase:**
```go
func TestJWTAudMismatch(t *testing.T) {
  tests := []struct {
    name    string
    token   string
    wantErr bool
    wantCode int
  }{
    {"missing_aud", tokenWithoutAud, true, 401},
    {"wrong_aud", tokenWithWrongAud, true, 401},
    {"valid_aud", validToken, false, 200},
  }
  for _, tt := range tests {
    t.Run(tt.name, func(t *testing.T) {
      err := validateJWT(tt.token)
      if (err != nil) != tt.wantErr { t.Fail() }
    })
  }
}
```
→ `make verify` → FAIL (validateJWT doesn't check aud yet)

**GREEN Phase:**
```go
func validateJWT(token string) error {
  claims := parseToken(token) // already works
  expectedAud := os.Getenv("COGNITO_CLIENT_ID")
  if expectedAud == "" {
    return errors.New("COGNITO_CLIENT_ID not set")
  }
  if claims.Aud != expectedAud && claims.ClientID != expectedAud {
    return errors.New("aud claim mismatch")
  }
  return nil
}
```
→ `make verify` → PASS

**REFACTOR Phase:**
- Extract claim validation into separate function
- Add logging for security events
→ `make verify` → still PASS

**Output (HANDBACK):**
```yaml
task_id: 2026-04-24-jwt-aud-validation
status: complete
deliverables:
  - Modified: {service-name}/lambda/command-gateway/main.go (lines 106-115)
  - Added: {service-name}/lambda/command-gateway/main_test.go (TestJWTAudMismatch)
tests:
  - Command: "make verify"
    Result: "PASS (124 tests, 87% coverage)"
tokens_in: 2100
tokens_out: 1400
model: claude-haiku-4-5
effort: high
duration_minutes: 35
escalations: 0
---
```

---

## TDD Validation

This skill is correct if it can:
1. Take a complete DELEGATE block (with plan and context)
2. Write a failing test first (before touching production code)
3. Implement minimal code to pass the test
4. Refactor without breaking tests
5. Produce a HANDBACK with verified test results
6. All within 30-90 minutes for well-scoped tasks, using ~2K tokens
