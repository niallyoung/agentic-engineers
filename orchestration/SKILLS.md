# Agent Skills & Workflows

Each agent role has defined skills, workflows, and quality standards. This document cascades from **AGENTS.md** (role assignments) to **SKILLS.md** (what each role does) to **QUEUE-PROTOCOL.md** (how work flows).

---

## Skill Hierarchy

```
AGENTS.md (WHO + ROUTING)
  ├─ Role definition (Engineer, Senior Engineer, etc.)
  ├─ Model assignment (Haiku, Sonnet, Opus)
  └─ Routing decision tree (when to use each role)
  
SKILLS.md (WHAT + HOW) ← You are here
  ├─ Engineer Skills
  ├─ Senior Engineer Skills
  ├─ Quality Engineer Skills
  └─ [Other roles]
  
QUEUE-PROTOCOL.md (WORKFLOW + AUTOMATION)
  ├─ Artifact lifecycle
  ├─ Orchestrator active loop
  └─ Queue transitions (incoming → processing → done)
```

---

## Engineer Skills

**Model:** claude-haiku-4-5 (high effort)  
**Use When:** Task has pre-written plan; low-medium complexity coding  
**Cost Target:** 18% of total token spend

### Red-Green TDD (MANDATORY for code changes)

When DELEGATE has `red_green_tdd_required: true`:

1. **RED Phase** — Write failing test
   - Name: Test[Feature/Bug][Condition] (e.g., `TestTokenTimeout_30sGracePeriod`)
   - Assert: Expected behavior that currently fails
   - Run: Verify it fails before implementing
   - **HANDBACK evidence:** "TestTokenTimeout_30sGracePeriod added at line 120, FAILS as expected"

2. **GREEN Phase** — Minimal implementation
   - Change: Smallest code change to pass the test
   - Run: `make verify` — test now passes
   - **HANDBACK evidence:** "Modified line 92 to accept tokens within 30s grace period; test PASSES"

3. **REFACTOR Phase** — Improve without changing behavior
   - Extract magic numbers to constants
   - Improve error messages
   - Remove duplication
   - Simplify logic
   - **HANDBACK evidence:** "Extracted grace period to const GRACE_PERIOD_SECS; improved error handling"

4. **Verify Full Suite**
   - Run: `make verify` (all tests pass)
   - Coverage: Maintained or improved
   - **HANDBACK evidence:** "Full suite PASS (47 tests, 89% coverage)"

**HANDBACK Section:**
```yaml
red_green_tdd_applied: true
red_green_evidence:
  - "[RED] TestTokenTimeout_30sGracePeriod added, FAILS"
  - "[GREEN] Modified line 92 to accept grace period, test PASSES"
  - "[REFACTOR] Extracted GRACE_PERIOD_SECS constant, improved error message"
  - "Full suite: 'make verify' PASS (47 tests, 89% coverage)"
```

### Error Handling

**MUST:**
- Never `panic()` — catch and return error
- Validate at boundaries (user input, external APIs, file I/O)
- Provide actionable error messages (not "invalid input")

**Example:**
```go
// BAD: panic
if token == "" {
  panic("token is empty")
}

// GOOD: error with context
if token == "" {
  return fmt.Errorf("token validation: empty token provided (expected JWT)")
}
```

### Code Quality Checklist

Before submitting HANDBACK:

- [ ] All tests in RED-GREEN-REFACTOR phases documented
- [ ] `make verify` passes (no new test failures, coverage maintained)
- [ ] Lint passes (`make lint` or equiv.)
- [ ] No hardcoded values (extract to constants, config, env vars)
- [ ] Error messages are helpful (include context, not just "failed")
- [ ] Comments explain WHY, not WHAT (code already shows WHAT)
- [ ] No commented-out code or TODO comments without context
- [ ] No new imports that increase dependencies
- [ ] Files modified ≤3 files (if more, scope was too broad)

### When to Escalate to Senior Engineer

- Task is incomplete after 1 HANDBACK + 1 rejection
- Architectural question arises (should we break API? refactor module?)
- Multiple interdependent changes needed
- **Action:** Contact Orchestrator via status `blocked` in HANDBACK

---

## Senior Engineer Skills

**Model:** claude-sonnet-4-6 (high effort)  
**Use When:** Complex coding without pre-written plan; diagnosis of root causes; planning  
**Cost Target:** 7% of total token spend

### Complex Task Planning

When Orchestrator delegates a task WITHOUT a pre-written plan:

1. **Diagnose:** Understand problem, constraints, dependencies
2. **Explore:** Consider multiple approaches (not just obvious one)
3. **Design:** Write detailed plan with rationale
4. **Deliver:** HANDBACK contains plan, not implementation

**HANDBACK Format:**
```yaml
handoff_type: HANDBACK
task_id: 2026-04-30-refactor-token-validation
status: complete
deliverables:
  - Artifact: "orchestration/plan-token-validation-refactor.md"
  - Approach 1: Extract token validation to separate module
  - Approach 2: Use middleware pattern in HTTP handler
  - Recommended: Approach 1 (cleaner, reusable, testable)
plan:
  1. Create token_validation.go module with public API
  2. Move validation logic from handler to module
  3. Update tests to use module API
  4. Refactor handler to call module
  5. Verify: All tests pass, coverage maintained
```

### Root Cause Analysis

When task is "diagnose bug":

1. **Reproduce:** Create minimal test case showing the bug
2. **Trace:** Follow code flow; identify where assumption breaks
3. **Evidence:** Point to specific line numbers and state
4. **Hypothesis:** Root cause with evidence
5. **Options:** Possible fixes (tradeoffs)

**HANDBACK Example:**
```yaml
root_cause: "Clock skew between mobile device and server"
evidence:
  - "File: lambda/api/main.go:92 checks time.Now() vs. token claim exp"
  - "Mobile devices with clock lag: device clock behind server by 10-60s"
  - "At 1hr boundary, mobile device time < token expiry, server time > token expiry"
  - "Result: Token accepted on device, rejected on server"
options:
  - "Option A: Add 30s grace period (simple, low-risk)"
  - "Option B: Sync client clock via headers (complex, requires app change)"
  - "Recommended: Option A"
```

### When to Escalate to Principal Engineer

- Change affects >2 repos or cross-service contracts
- Architectural question impacts system design
- Security implications beyond local module
- **Action:** Status `blocked` in HANDBACK with escalation reason

---

## Lead Engineer Skills

**Model:** claude-sonnet-4-6 (high effort)  
**Use When:** Code review; quality decisions; medium-complexity planning; unblock Engineer  
**Cost Target:** 2% of total token spend

### Code Review (QE Role)

After Engineer submits HANDBACK, Lead Engineer (or Quality Engineer) verifies:

**Tier 1 Checklist (ALL code changes):**
- [ ] `make verify` passes (tests, lint, coverage)
- [ ] Tests added/updated for new behavior
- [ ] No new errors or warnings
- [ ] In-scope: changes match DELEGATE scope
- [ ] No production hazards (panic, secrets, hardcoded values)

**Verdict:** PASS or FAIL (if FAIL, reject with specific feedback)

**Tier 2 Checklist (Senior Engineer changes):**
- [ ] Test coverage ≥ 85%
- [ ] No new exported symbols without docs
- [ ] Plan completeness (all steps executed, nothing extra)
- [ ] Error handling is defensive (no panics)

**Tier 3 Checklist (Principal Engineer changes):**
- [ ] Architecture adherence (follows patterns)
- [ ] IAM/Security correctness (least privilege)
- [ ] Cross-service contracts (no breaking changes without migration)

### Red-Green TDD Verification

When reviewing HANDBACK:

- [ ] `red_green_tdd_applied: true` (required for code changes)?
- [ ] Evidence shows RED phase? (test added, fails initially)
- [ ] Evidence shows GREEN phase? (fix implemented, test passes)
- [ ] Evidence shows REFACTOR phase? (code improved)
- [ ] If missing RED or GREEN → **REJECT** (status: rejected)

**Rejection Response:**
```yaml
handoff_type: HANDBACK
task_id: 2026-04-30-fix-token-timeout
status: rejected
rejection_reason: "Red-Green TDD evidence missing"
detailed_feedback:
  - "RED phase missing: no test added showing bug"
  - "GREEN phase exists but not documented in evidence"
  - "REFACTOR phase: none visible"
instructions:
  - "Resubmit with clear evidence of RED-GREEN-REFACTOR cycle"
  - "Include: test name, failure mode, fix applied, refactoring notes"
```

### Unblock Engineer (Escalation Responder)

When Engineer reports `status: blocked`:

1. **Analyze:** Understand blocker
2. **Recommend:** Path forward (break contract? refactor? add feature?)
3. **Provide:** Next steps or revised plan

---

## Quality Engineer Skills

**Model:** claude-sonnet-4-6 (medium effort)  
**Use When:** Post-implementation quality gate; model suitability assessment  
**Cost Target:** 8% of total token spend

### Quality Gate Verification

After Engineer completes HANDBACK:

1. **Run Tier 1 checklist** (see Lead Engineer Skills above)
2. **If FAIL:** Reject with specific feedback
3. **If PASS:** Proceed to model assessment

### Model Suitability Assessment

Analyze:
- Was assigned model appropriate for task complexity?
- Token efficiency: cost / quality ratio
- Code quality (test coverage, error handling, clarity)
- Execution quality (right approach, no rework needed)

**Assessment Options:**
- `haiku_suitable` — Task matched well; Haiku sufficient
- `sonnet_would_be_better` — Could have been done by Sonnet with less rework
- `opus_required` — Task was too complex for Haiku; should have escalated

**Confidence Score:** 0.0–1.0 (likelihood this assessment is correct for similar tasks)

**HANDBACK Addition:**
```yaml
qe_feedback:
  tier_1_verdict: PASS
  model_assessment: "haiku_suitable"
  reasoning: "Task was well-scoped, plan was clear. Haiku executed efficiently; no rework needed."
  confidence_for_similar_tasks: 0.92
  quality_dimensions:
    test_coverage: 89
    error_handling: "defensive"
    code_clarity: "excellent"
    red_green_tdd: "clear evidence of all phases"
```

### Feedback to Model Engineer

QE assessment feeds into Model Engineer's analysis:
- Did the model/effort combo work?
- For next similar task, should we use the same model or promote/demote?
- What signals predict whether a model will succeed?

---

## Principal Engineer Skills

**Model:** claude-opus-4-6 (high effort)  
**Use When:** Cross-service architecture; complex multi-step planning; design decisions  
**Cost Target:** 1% of total token spend

### Cross-Service Architecture Planning

When a task affects >2 repos or touches service boundaries:

1. **Map dependencies:** Which services depend on which?
2. **Identify contracts:** What APIs/contracts must be maintained?
3. **Consider options:** Breaking changes vs. compatibility layers vs. versioning
4. **Recommend approach:** Tradeoffs (cost, risk, maintenance)
5. **Plan migration:** Step-by-step rollout if needed

**HANDBACK:** Detailed plan with architecture diagrams (text-based)

---

## Security Engineer Skills

**Model:** claude-opus-4-7 (max effort)  
**Use When:** Security analysis; threat modeling; vulnerability audits  
**Cost Target:** 1% of total token spend

### Security Audit

When Orchestrator routes security-scoped task:

1. **Threat Model:** Identify attack vectors
2. **Code Review:** Search for vulnerabilities (OWASP Top 10)
3. **Dependencies:** Check for known CVEs
4. **Access Control:** Verify least-privilege principle
5. **Generate:** TODO.md with findings and recommendations

**Severity Levels:**
- **CRITICAL** — Exploitable, data loss / system compromise → immediate fix required
- **HIGH** — Serious weakness → fix before release
- **MEDIUM** — Improves security posture → plan in next sprint
- **LOW** — Best practice → document, consider for refactoring

**HANDBACK:** SECURITY_AUDIT_TODO.md with findings by severity

### Post-Audit Implementation

After Security Engineer completes audit:
1. Orchestrator delegates fix tasks to Engineer (per TODO.md)
2. Engineer implements fixes following Red-Green TDD
3. Security Engineer verifies fixes (re-audit subset)

---

## Model Engineer Skills

**Model:** claude-sonnet-4-6 (high effort)  
**Use When:** Analyze metrics and quality feedback; recommend model/effort combos  
**Cost Target:** 3% of total token spend

### Token Analysis & Cost Optimization

Inputs: QE feedback from 100+ completed tasks

**Analysis:**
- Which task types consume most tokens?
- Which models consistently outperform?
- Where does rework happen? (indicates model mismatch)
- Token efficiency: cost per unit of quality

**Output:** Recommendations for next similar task

**Example Finding:**
```
Task Type: Bug diagnosis (root-cause analysis)
Current: Engineer (Haiku) → blocked, escalated to Senior Engineer (Sonnet)
Recommendation: For future bug diagnosis without clear root cause → route directly to Senior Engineer
Confidence: 0.88 (6 samples, all escalated; Sonnet needed every time)
Savings: Avoid wasted Engineer tokens; direct Sonnet reduces total cost by 15%
```

### Routing Optimization

Every completed task generates feedback:

```
Task 1: Engineer (Haiku) → PASS, QE: "haiku_suitable", confidence: 0.92
Task 2: Engineer (Haiku) → BLOCKED, escalated to Senior Engineer (Sonnet)
Task 3: Senior Engineer (Sonnet) → PASS, QE: "sonnet_would_be_better", confidence: 0.85
...
Task 100: [pattern emerges]
```

**Model Engineer Generates:**
```yaml
recommendations:
  - rank: 1
    task_type: "bug_fix_simple"
    model: "claude-haiku-4-5"
    effort: "high"
    confidence: 0.94
    reason: "10/11 samples completed without escalation; average efficiency 0.91"
  
  - rank: 2
    task_type: "bug_diagnosis"
    model: "claude-sonnet-4-6"
    effort: "high"
    confidence: 0.88
    reason: "Engineer escalated 6/8 times; Sonnet completes directly; 15% cost savings"
  
  - rank: 3
    task_type: "architecture_review"
    model: "claude-opus-4-6"
    effort: "high"
    confidence: 0.92
    reason: "Prevents escalation from Principal Engineer; avoids rework"
```

**Orchestrator Applies:** Rank 1 recommendation for next matching task

---

## Orchestrator Skills

**Model:** claude-haiku-4-5 (low effort)  
**Use When:** Routing, task management, queue coordination  
**Cost Target:** 60% of total token spend

### Task Routing (AGENTS.md Decision Tree)

When new task arrives in `artifacts/queue/incoming/`:

1. Is task security-scoped? → Security Engineer
2. Is task cross-service architecture? → Principal Engineer
3. Is task complex coding WITHOUT plan? → Senior Engineer (to plan first)
4. Is task code review or quality verification? → Lead Engineer or Quality Engineer
5. Is task well-planned, low-medium complexity? → Engineer
6. Otherwise → Escalate to human

### Queue Management (QUEUE-PROTOCOL.md Active Loop)

Every 30-60 seconds:

```
✓ Check incoming/ for new work
  ├─ Create DELEGATE for each task
  ├─ Send to appropriate agent (per routing above)
  └─ Move to processing/

✓ Check processing/ for completed work
  ├─ If status="complete" → route to Quality Engineer for verification
  ├─ If status="blocked" → route to Lead/Senior Engineer for unblocking
  └─ If status="partial" → determine next steps (accept or rework)

✓ Check done/ for final decisions
  ├─ If decision="PROCEED" → merge to main
  ├─ If decision="REWORK" → create new DELEGATE with feedback, send to incoming/
  └─ If decision="ESCALATE" → promote to higher role

✓ Generate status report (every 4 hours)
  ├─ Queue lengths, ages
  ├─ Completion rates, rejection rates
  └─ Bottleneck alerts
```

### Model Engineer Recommendation Application

When Model Engineer generates recommendations:

```yaml
recommendations:
  - rank: 1
    task_type: "bug_fix_simple"
    model: "claude-haiku-4-5"  # Use for next matching task
    confidence: 0.94
```

**Orchestrator Logic:**
```
For next task of type "bug_fix_simple":
  ├─ Check if Rank 1 model (Haiku) is available
  ├─ If yes → use Rank 1 (confidence: 0.94)
  ├─ If no → fall back to Rank 2 (alternative model)
  └─ Record decision and confidence for future analysis
```

---

## Summary: Skills by Role

| Role | Primary Skill | Escalation | When to Use |
|------|---------------|-----------|------------|
| Engineer | Red-Green TDD + well-scoped execution | to Senior Engineer | Pre-planned code, low-medium complexity |
| Senior Engineer | Complex planning + root-cause diagnosis | to Principal Engineer | No plan, architectural Q's, diagnosis |
| Lead Engineer | Code review + unblocking | to Principal Engineer | QE + escalation handling |
| Quality Engineer | Tier 1/2/3 verification + model assessment | to Lead Engineer | Post-implementation quality gate |
| Principal Engineer | Cross-service architecture + design | to Security Engineer | Cross-repo, system design |
| Security Engineer | Threat modeling + vulnerability audit | Standalone (no escalation) | Security-scoped tasks |
| Model Engineer | Metrics analysis + routing optimization | Standalone | Every ~100 tasks for continuous optimization |
| Orchestrator | Task routing + queue management | none (reports to human) | Every 30-60 seconds, active loop |

---

## Integration with Queue Protocol

Each skill above is **implemented** by the agent when they receive a DELEGATE from Orchestrator.

**Example Flow:**

```
1. Orchestrator creates DELEGATE for Engineer
   ├─ role: Engineer
   ├─ model: claude-haiku-4-5
   ├─ red_green_tdd_required: true
   └─ plan: [5 concrete steps]

2. Engineer receives DELEGATE
   ├─ Reads SKILLS.md "Engineer Skills > Red-Green TDD"
   ├─ Follows RED-GREEN-REFACTOR-VERIFY phases
   └─ Documents evidence in HANDBACK

3. Quality Engineer receives HANDBACK
   ├─ Reads SKILLS.md "Quality Engineer Skills > Quality Gate Verification"
   ├─ Runs Tier 1 checklist
   ├─ Verifies Red-Green TDD evidence
   └─ Adds qe_feedback section

4. Model Engineer analyzes historical feedback
   ├─ Reads SKILLS.md "Model Engineer Skills > Routing Optimization"
   ├─ Extracts confidence signals
   └─ Generates recommendations for Orchestrator

5. Orchestrator applies recommendations
   ├─ Reads SKILLS.md "Orchestrator Skills > Model Engineer Recommendation Application"
   ├─ Routes next matching task using Rank 1 model
   └─ Repeats
```

This creates a **closed loop:** execution → feedback → optimization → better routing.

