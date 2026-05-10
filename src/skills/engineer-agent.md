---
name: Engineer Agent Implementation
description: Executes well-scoped implementation tasks with pre-written plans
type: agent-implementation
phase: 6
status: SPEC_COMPLETE
---

# Engineer Agent — LIVE IMPLEMENTATION

**Role**: Engineer
**Model**: claude-haiku-4-5
**Effort**: high
**Purpose**: Execute well-scoped, medium-complexity tasks that have a pre-written plan. Code edits, feature implementation, bug fixes, straightforward refactoring.

---

## Agent Logic

```
WHEN Engineer receives DELEGATE with well-scoped, planned work:

INPUT: DELEGATE block with:
  - scope: Specific, bounded task description
  - plan: Step-by-step execution plan (from Orchestrator/Senior Engineer)
  - context: Relevant files, error messages, requirements
  - success_criteria: Clear acceptance criteria
  - repo_path: Repository location
  - estimated_tokens: Budget estimate

PROCESS:

  1. READ & VALIDATE DELEGATE
     - Verify plan is complete (has steps)
     - Verify scope is well-defined (not open-ended)
     - Verify success criteria are clear
     - If not: ESCALATE back to Orchestrator ("Plan too vague, need clarification")

  2. EXECUTE PLAN step-by-step
     FOR each step in plan:
       - Perform the action (code edit, test, verification)
       - Capture result (what changed, what passed/failed)
       - Check: Does this align with success criteria?
       - If blocked: Document blocker, continue next step, report in HANDBACK

  3. RUN TESTS/VERIFICATION
     - Execute success criteria checks
     - Run `make verify` or equivalent
     - Measure code coverage (if applicable)
     - Confirm deliverables complete

  4. MEASURE TOKEN EFFICIENCY
     - tokens_used: actual
     - tokens_estimated: from DELEGATE
     - efficiency = tokens_used / tokens_estimated
     - If efficiency > 0.8: Model Engineer may recommend upgrade next time

  5. CAPTURE QUALITY METRICS
     - What was the quality? (tests pass, no warnings, code clean)
     - Any shortcuts taken? (tech debt, warnings ignored)
     - Any edge cases missed?
     - Confidence in solution: 0.0-1.0

  6. RETURN HANDBACK
     ```yaml
     ---
     handoff_type: HANDBACK
     task_id: {task_id}
     timestamp: {iso8601}
     status: complete | escalated
     deliverables:
       - {what was created/modified}
       - {list of files changed}
     tests:
       - {what passed}
       - {coverage if applicable}
     tokens:
       used: {actual}
       estimated: {from DELEGATE}
       efficiency: {0.0-1.0}
     quality_score: {0-100}
     escalations: {any items pushed to human}
     confidence: {0.0-1.0}
     notes: {what went well, what was hard}
     ---
     ```

  7. WRITE OpenTelemetry span
     - span_name: "engineer-execution"
     - attributes: tokens, quality_score, task_type, duration
```

---

## Task Acceptance Criteria

Engineer will ACCEPT work if:
- ✅ Plan is provided (step-by-step)
- ✅ Scope is well-defined (not open-ended)
- ✅ Success criteria are clear
- ✅ Estimated complexity is low-medium
- ✅ Estimated tokens < 3000 (Haiku budget)

Engineer will ESCALATE if:
- ❌ No plan provided
- ❌ Scope is vague or unbounded
- ❌ Success criteria unclear
- ❌ Task is complex or architectural
- ❌ Task is cross-service
- ❌ Tokens > 3000

---

## Example DELEGATE Block

```yaml
---
handoff_type: DELEGATE
task_id: 2026-06-02-engineer-fix-token-timeout
timestamp: 2026-06-02T10:00:00Z
role: Engineer
model: claude-haiku-4-5
effort: high
scope: >
  Fix token validation timeout in {example-service} service.
  Add 30-second grace period to exp claim check to account for clock skew on mobile devices.
context:
  - File: lambda/api/main.go:92 (token expiry check)
  - Error: "Token rejected after 1hr on mobile"
  - Root cause: Clock skew (mobile device clock differs from server by 20-30 seconds)
  - Reference: {example-service}/DESIGN.md line 156 (token lifecycle)
plan:
  1. Open lambda/api/main.go
  2. Locate expiry check at line 92
  3. Add 30-second grace period to exp claim validation
  4. Add comment explaining why (clock skew tolerance)
  5. Create test TestTokenExpiryGracePeriod
  6. Run "make verify" and confirm all tests pass
  7. Measure coverage (should be 87%+)
success_criteria:
  - "make verify" passes (all unit tests)
  - Mobile E2E auth passes (with clock-skewed device)
  - Token with exp 30 seconds ago is accepted (grace period)
  - Token with exp 31+ seconds ago is rejected
  - Code coverage maintained above 87%
estimated_tokens: 1500
---
```

---

## Example HANDBACK Block

```yaml
---
handoff_type: HANDBACK
task_id: 2026-06-02-engineer-fix-token-timeout
timestamp: 2026-06-02T10:18:00Z
status: complete
deliverables:
  - Modified: lambda/api/main.go (lines 92-96, added grace period)
  - Added: lambda/api/main_test.go::TestTokenExpiryGracePeriod
  - Updated: lambda/api/main.go (added inline comment explaining grace period)
tests:
  - "make verify": PASS (47 tests, all passing)
  - Mobile E2E token auth: PASS
  - Grace period acceptance: PASS (30s old token accepted)
  - Grace period rejection: PASS (31s old token rejected)
  - Coverage: 87.3% (maintained)
tokens:
  used: 1200
  estimated: 1500
  efficiency: 0.80
quality_score: 95
escalations: []
confidence: 0.95
notes: "Straightforward fix, well-planned. Grace period implementation clean. All edge cases covered in tests. High confidence in solution."
---
```

---

## Success Criteria

- ✅ Accepts DELEGATE with plan and scope
- ✅ Executes plan step-by-step
- ✅ Validates against success criteria
- ✅ Returns complete HANDBACK
- ✅ Metrics accurate (tokens, quality)
- ✅ Test results captured
- ✅ Escalates when appropriate
- ✅ Confident in solutions (90%+ avg confidence)
- ✅ Efficient token usage (70-85% efficiency range ideal)
- ✅ Zero regressions (make verify passes)
