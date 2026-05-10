# Quality Checklist

Pre-submission gate to prevent re-work loops. Each Engineer tier completes the checklist before emitting the HANDBACK block.

**Golden Rule:** If any Tier 1 item is "no", the task is incomplete. Fix first; do not emit HANDBACK.

---

## Tier 1 — All Engineer Tasks (Non-Negotiable)

Required for: Engineer, Senior Engineer, Lead Engineer, Principal Engineer, Security Engineer

Run through this checklist **before** emitting the HANDBACK block. Estimate time: 5–10 minutes.

- [ ] **Lint + Test Pass** — Run `make verify` (or equivalent for repo) and paste full output. All tests must pass.
- [ ] **No new errors introduced** — No new compilation errors, type errors, or linter warnings. (Suppress pre-existing warnings only if marked with `//nolint` or similar.)
- [ ] **In-scope changes only** — All modified files are within the `scope` defined in the DELEGATE block. No scope creep (e.g. did not refactor unrelated code).
- [ ] **Tests added/updated** — For any new function or behavior, a test was added or updated. If no test was added, the reason is documented (e.g. "integration test handles this").
- [ ] **No production hazards** — No `panic`, `log.Fatal`, hardcoded secrets (API keys, URLs, tokens), or commented-out code left behind. All error handling is explicit.

**TDD Validation:** Take a completed Engineer task (e.g. {example-service} token timeout fix). Walk through Tier 1. Each item must map to something observable in the final code or test output. If not, the checklist is incomplete.

---

## Tier 2 — Senior Engineer, Lead Engineer, Principal Engineer

Required for: Senior Engineer and above (in addition to Tier 1)

Estimate time: 10–15 minutes.

- [ ] **Test coverage maintained or improved** — Coverage % for the modified package did not decrease. (Example: modified `lambda/api/main.go`, coverage was 87% before, now 89%.) If coverage decreased, add tests.
- [ ] **No new exported symbols without docs** — If you added a public function or type (capitalized), it has a one-line documentation comment above it.
- [ ] **Plan completeness** — The DELEGATE block's `plan` steps were all executed. Nothing was skipped; nothing extra was added. (If you deviated, document why in HANDBACK `notes`.)

---

## Tier 3 — Principal Engineer, Security Engineer

Required for: Principal Engineer and Security Engineer only (in addition to Tier 1 + Tier 2)

Estimate time: 15–30 minutes.

- [ ] **Architecture adherence** — Changes follow existing patterns. If a new pattern is introduced, it is documented in code comments or a brief architectural decision record (e.g. "// Architecture: Using gRPC instead of REST because..."). No style drift.
- [ ] **IAM/Security correctness** — If IAM changes were made, they follow the principle of least privilege. Permissions granted are no broader than necessary. If new API endpoints were added, they enforce auth/scopes correctly.
- [ ] **Cross-service contracts** — If this change affects the API contract with other services (request/response shape, error codes, headers), all consuming services were identified and tested. No breaking changes without notification.

---

## HANDBACK Block Validity Rule

The HANDBACK block is not valid until **all checklist items for your tier are checked ✓**.

If you skip an item, fix it and re-check. Do not emit HANDBACK with unchecked items.

---

## Example: Quality Check for Token Timeout Fix

**Task:** {example-service} token expiry grace period (Engineer tier, Tier 1 only)

```
[✓] Lint + Test Pass
    $ cd {example-service} && make verify
    ... [output shows all 48 tests passed, 0 errors] ...

[✓] No new errors introduced
    golangci-lint output: 0 issues. No type errors from tsc.

[✓] In-scope changes only
    Modified: lambda/api/main.go (lines 92–95)
    Added: lambda/api/main_test.go (TestTokenExpiryGracePeriod)
    All within scope: "Fix token validation timeout" ✓

[✓] Tests added/updated
    Added new test TestTokenExpiryGracePeriod covering the 30s grace period edge case.

[✓] No production hazards
    - No panic, log.Fatal, or hardcoded secrets added
    - Error at line 100 is explicit: "return fmt.Errorf(...)"
    - All TODOs removed; all PRINTFs changed to proper logging
```

Ready to emit HANDBACK block ✓

---

## Running the Checklist

**Step 1:** Copy the checklist for your tier (Tier 1, 1+2, or 1+2+3).  
**Step 2:** Work through each item, **doing the work before checking the box** (not checking first and then fixing).  
**Step 3:** Paste the checklist (with boxes checked) into your HANDBACK block's `notes` field (optional but recommended for complex tasks).  
**Step 4:** Emit HANDBACK.

---

## When Quality Fails (Returning to Engineer)

If Orchestrator (or a quality gate) detects a Tier 1 item was not met:

1. Engineer receives feedback: "Token test coverage dropped; tests: 47 → 46"
2. Engineer creates a **new** DELEGATE block (same task_id, status `rework`)
3. Rework is tracked separately in METRICS (tokens_in, duration, model)
4. Rework is expected to be small if the original checklist was thorough

---

## Anti-Pattern Examples

❌ **"I skipped the test because it's obvious"** — No. Obvious != tested. Add the test.

❌ **"Coverage decreased because existing tests were removed"** — Add new tests to compensate, or revert the deletion.

❌ **"I added a helper function but didn't document it"** — Add a one-line doc comment.

❌ **"I refactored while fixing the bug"** — Scope creep. Revert the refactor or create a separate task.

---

## TDD Validation: Does the Checklist Prevent Re-work?

Test case: An Engineer task with a failing test (expected), a missing test (implicit bug), and a hardcoded API key (hazard).

The Engineer runs the checklist:
- [ ] **Lint + Test Pass** — Test fails. Engineer adds the test + fixes the code. Then passes.
- [ ] **No new errors introduced** — Passes.
- [ ] **In-scope changes only** — Passes.
- [ ] **Tests added/updated** — Engineer realizes they forgot a test case. Adds it. Then passes.
- [ ] **No production hazards** — Engineer realizes hardcoded API key exists. Moves to env var. Then passes.

Final state: All checklist items pass. Emit HANDBACK. No re-work needed.

The checklist is complete when it catches all three issues (failing test, missing test, hardcoded secret) before HANDBACK is emitted.

---

## Quality Engineer Feedback for Model Optimization

Beyond pass/fail verdicts, Quality Engineer provides structured feedback that enables Model Engineer to improve future routing decisions.

### Model Assessment (Required on all PASSing HANDBACKs)

After verifying Tier 1/2/3 items, QE adds `qe_feedback` block to HANDBACK:

**Assessment Options:**
- `haiku_suitable` — Model was optimal for task; use Haiku for similar tasks going forward
- `sonnet_suitable` — Model matched task complexity well; continue with Sonnet
- `sonnet_would_be_better` — Task was more complex than model's capability; would benefit from Sonnet
- `opus_required` — Task required higher reasoning than model provides; escalate to Opus

**Confidence Score** (0.0-1.0):
- 1.0 = Certain this model is right for similar tasks
- 0.8-0.99 = Confident, minor risk
- 0.6-0.79 = Moderate confidence; consider A/B test
- <0.6 = Low confidence; model likely unsuitable

**Example Assessment:**

```yaml
qe_feedback:
  tier_1_verdict: PASS
  model_assessment: "haiku_suitable"
  reasoning: "Task was well-scoped, straightforward implementation, Haiku applied patterns correctly without over-engineering. Cost-effective choice."
  confidence_for_similar_tasks: 0.92
  quality_dimensions:
    test_coverage: 89
    coverage_assessment: "excellent, edge cases covered"
    error_handling: "defensive, clear error messages"
    code_clarity: "clear variable names, logic easy to follow"
    pattern_adherence: "follows conventions perfectly"
```

### How Model Engineer Uses This Feedback

Model Engineer analyzes QE feedback to:
1. **Assess model appropriateness** — Was assigned model optimal for this task type?
2. **Build confidence** — Accumulate samples → increase confidence in model assignment
3. **Detect anomalies** — When confidence drops or QE recommends upgrade
4. **Generate recommendations** — Suggest better models for future similar tasks
5. **Track patterns** — Which task types favor which models?

**Feedback → Recommendation Flow:**
```
5 tasks, all "haiku_suitable" (avg confidence 0.88)
  → Model Engineer: "High confidence in Haiku for this signature"
  → Orchestrator: "Route next similar task to Haiku"

2 tasks, QE says "sonnet_would_be_better"
  → Model Engineer: "Haiku confidence drops to 0.45"
  → Orchestrator: "Switch to Sonnet for next similar task"
  → Trigger A/B test to evaluate more systematically
```

### When QE Provides Feedback

**Always:**
- After task status = COMPLETE and Tier 1 PASS

**Format:**
- Add to HANDBACK block before returning to Orchestrator
- Part of quality verification, not separate message

**Constraints:**
- QE never makes routing decisions (only provides feedback)
- QE never recommends models (only assesses suitability)
- Model Engineer analyzes feedback and generates recommendations
- Orchestrator applies recommendations, not QE assessments
