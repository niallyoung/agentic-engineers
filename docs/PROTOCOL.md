---
title: Orchestration Protocol — Master Reference
version: 1.0.0
status: APPROVED
created: 2026-05-09
owner: Lead Engineer
references:
  - orchestration/AGENTS.md
  - orchestration/DELEGATE-HANDBACK-QUALITY-GATES.md
  - orchestration/delegate-schema.yaml
  - orchestration/handback-schema.yaml
  - orchestration/agents/quality_validator.py
  - orchestration/agents/decision_engine.py
  - orchestration/agents/delegate_validator.py
  - orchestration/agents/metrics_writer.py
---

# Orchestration Protocol — Master Reference

> **Source of truth for all DELEGATE/HANDBACK interactions in the agentic-engineers system.**
> All agents must follow this protocol. See [AGENT-ONBOARDING.md](AGENT-ONBOARDING.md) before
> assuming an operational role.

---

## 1. Executive Summary

### What This Protocol Is

The Orchestration Protocol governs how work is delegated to specialist agents
(DELEGATE) and how results are returned (HANDBACK) in the agentic-engineers system.
It defines quality gates, routing rules, retry mechanics, and metrics collection so
that every unit of work is tracked, validated, and continuously improved.

### Why It Matters

Without this protocol the system accumulates three failure modes:

| Failure | Consequence |
|---------|-------------|
| **Poor DELEGATE** | Agent does wrong work; wasted tokens; costly re-work |
| **Unchecked HANDBACK** | Bad code merges; silent quality regression |
| **Missing metrics** | No learning signal; Model Engineer cannot optimize routing |

With the protocol in place:
- **Re-work rate** drops from untracked to ≤20% target
- **Escalation rate** capped at ≤5% (Principal Engineer is reserved for true hard problems)
- **Pre-flight validation** blocks bad DELEGATEs before any tokens are spent
- **Metrics feed** Model Engineer with data to lower cost over time

### Key Outcomes Expected

| Metric | Target |
|--------|--------|
| Pre-flight validation pass rate | ≥95% |
| HANDBACK merge rate (90–100 score) | ≥70% |
| Rework rate (60–69 score) | ≤20% |
| Escalation rate (<60 score) | ≤5% |
| Test coverage across modified packages | ≥85% |

---

## 2. DELEGATE Format & Validation

A DELEGATE is a structured YAML block that transfers a task from the Orchestrator
to a specialist agent.

### 2.1 Required Fields

| Field | Type | Validation Rule |
|-------|------|----------------|
| `task_id` | string | `^[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9][a-z0-9\-]{0,62}[a-z0-9]$` |
| `role` | enum | One of 7 valid roles (see Section 10) |
| `model` | string | Default per role or justified override |
| `effort` | enum | `low \| medium \| high \| max \| epic` |
| `estimated_hours` | integer | Must align with effort band |
| `scope` | string | ≥15 words; action verb; names specific subject |
| `success_criteria` | array | ≥1 measurable, testable criterion per 4 estimated hours |
| `plan` | array | Numbered concrete steps; must include testing step |
| `context` | array/string | Sufficient background for agent to start immediately |

### 2.2 Optional Fields (with Defaults)

| Field | Default | Purpose |
|-------|---------|---------|
| `handoff_type` | `DELEGATE` | Protocol identifier |
| `spec_version` | string | Protocol version for audit trail and compatibility |
| `budget_context` | null | Token budget hint for metrics baseline |
| `token_quota` | object | Optional token budget/ceiling for this task |
| `out_of_scope` | null | Required for `effort: high/max/epic` |
| `retry_context` | null | Present on re-work DELEGATEs (see Section 6) |
| `dependencies` | [] | Upstream task IDs that must complete first |
| `deadline` | null | ISO-8601 timestamp if time-sensitive |
| `priority` | `normal` | `critical \| high \| normal \| low` |
| `notes` | null | Free-form notes for the receiving agent |

### 2.3 Validation Groups

**Group A — Structure (Hard gates: any failure = DO NOT SEND)**

| Check | Rule |
|-------|------|
| A1 | `task_id` matches date-prefixed kebab-case regex |
| A2 | `task_id` is unique (not reused from another task this session) |
| A3 | `role` is in the valid role enum |
| A4 | `model` matches role default or has written justification |
| A5 | `effort` band aligns with `estimated_hours` |
| A6 | `scope` ≥15 words, contains an action verb, names subject |
| A7 | No secrets embedded (grep for `password`, `secret`, `token`, `api_key`) |

**Group B — Content Quality (any failure = refine before sending)**

| Check | Rule |
|-------|------|
| B1 | `success_criteria` are measurable/testable (not "good code" or "works well") |
| B2 | `success_criteria` cover all expected outputs |
| B3 | `plan` steps are numbered and concrete (file/command/action named) |
| B4 | `plan` includes at least one testing step |
| B5 | `context` is self-contained (agent needs no additional clarification) |
| B6 | `out_of_scope` present for `effort: medium` or above |
| B7 | `effort` is realistic (not artificially low to save tokens) |

**Group C — Routing Sanity (failure = re-route)**

| Check | Failure Action |
|-------|---------------|
| C1 | `effort: high/max` → role must be `senior_engineer` or above | Upgrade role |
| C2 | Security-scoped task → `role: security_engineer` | Re-route |
| C3 | Cross-service architecture → `role: principal_engineer` | Re-route |
| C4 | Code review / audit → `role: lead_engineer` or `quality_engineer` | Re-route |

### 2.4 Example: Correct DELEGATE

```yaml
handoff_type: DELEGATE
task_id: 2026-05-09-add-jwt-validation
role: senior_engineer
model: claude-sonnet-4.6
effort: medium
estimated_hours: 8
scope: |
  Implement JWT validation middleware for the API gateway, including token
  signature verification, expiry grace-period handling, and rejection of
  malformed tokens. Add integration tests for all branches.
out_of_scope:
  - Do not modify Cognito configuration
  - Do not change upstream identity service
context:
  - Key file: src/api/middleware.py:45
  - Auth design: docs/auth-design.md
  - Related PR: #201 (auth refactor, merged)
plan:
  1. Read src/api/middleware.py to understand current validation
  2. Add test_jwt_validation.py covering valid, expired, malformed, and missing tokens
  3. Implement validate_jwt() with 30s grace period constant
  4. Wire middleware into API gateway request lifecycle
  5. Run pytest -v to confirm all tests pass (zero failures)
  6. Check coverage ≥85% for modified packages
success_criteria:
  - pytest returns zero failures (all existing + new tests pass)
  - validate_jwt() rejects tokens expired >30s, accepts tokens expired ≤30s
  - Test coverage ≥85% for src/api/middleware.py
  - No secrets committed to repo
```

### 2.5 Common Mistakes

```
❌ scope: "Fix the bug"                 → Add file:line, root cause, expected behaviour
❌ plan: "Implement everything"          → Number every step; name specific files
❌ success_criteria: "Works well"        → What test proves it? What metric confirms it?
❌ effort: low, plan: 15 steps           → Upgrade effort to medium/high
❌ role: engineer, effort: max           → Upgrade role to senior_engineer or lead_engineer
❌ context: (empty)                      → Agent will stall; provide key files upfront
```

---

## 3. HANDBACK Format & Acceptance

A HANDBACK is a structured YAML block the agent returns after completing (or failing) a task.

### 3.1 Required Fields

| Field | Type | Rule |
|-------|------|------|
| `task_id` | string | Must exactly match the DELEGATE `task_id` |
| `handoff_type` | string | Must be `"HANDBACK"` |
| `spec_version` | string | Protocol version used during execution |
| `status` | enum | `complete \| failed \| partial \| blocked` |
| `deliverables` | array | File paths created/modified (min 1 for high/max effort) |
| `tests` | object | `{passed, failed, coverage, framework, notes}` |
| `quality_score` | integer | Agent self-score (0–100); validator score is authoritative |
| `effort_actual` | enum | Actual effort band consumed |
| `tokens_in` | integer | Tokens consumed reading context |
| `tokens_out` | integer | Tokens produced in response |
| `token_usage` | object | Structured token usage report for migration |
| `duration_minutes` | integer | Wall-clock minutes from start to HANDBACK |
| `notes` | string | ≥5 words explaining outcome, decisions, and deviations |
| `agent` | string | Role that executed the task |

### 3.2 Optional Fields

| Field | Purpose |
|-------|---------|
| `qe_feedback` | Quality Engineer assessment block (see QUALITY.md) |
| `retry_context` | Present on re-work attempts (see Section 6) |
| `escalation_reason` | Required when `status: blocked` |
| `scope_deviations` | Any deliberate deviations from DELEGATE scope |
| `model_actual` | If different from DELEGATE (e.g., escalated mid-task) |
| `blockers` | External blockers encountered (for partial/blocked status) |
| `next_steps` | Optional follow-on work recommendations |
| `artifacts` | Non-file artifacts (URLs, IDs, docs) |

### 3.3 Three-Layer Validation

**Layer 1 — Format Gate (40% weight of composite score)**

Validated automatically by `quality_validator.py`. Any critical failure drops score severely.

| Field | Severity | Score Impact |
|-------|----------|-------------|
| `handoff_type: HANDBACK` missing/wrong | CRITICAL | −25 |
| `task_id` mismatch with DELEGATE | CRITICAL | −25 |
| `status` invalid value | ERROR | −15 |
| `deliverables` missing (high+ effort) | ERROR | −10 |
| `tests` missing for engineer roles | ERROR | −10 |
| `notes` < 5 words | ERROR | −10 |
| `tokens_in/out` missing or zero | WARNING | −5 each |
| `duration_minutes` missing | WARNING | −5 |

**Layer 2 — Content Gate (35% weight)**

Verified by Decision Engine against the original DELEGATE's `success_criteria`:

| Check | Weight |
|-------|--------|
| All plan steps executed (or deviation documented) | 30% |
| All `success_criteria` from DELEGATE addressed | 40% |
| Tests pass with count ≥ previous count | 20% |
| No scope creep beyond DELEGATE scope | 10% |

**Layer 3 — Quality Gate (25% weight)**

| Check | Threshold |
|-------|-----------|
| Composite quality score | ≥80 for auto-accept |
| Test coverage | ≥70% for modified packages |
| No production hazards | Zero panics, hardcoded secrets, commented-out code |
| `qe_feedback` present | Required on all completed tasks |
| Deliverables physically exist on disk | Automated spot-check |

### 3.4 Quality Score Thresholds

| Score | Action | Who Decides |
|-------|--------|-------------|
| **90–100** | ✅ Accept immediately | Automated |
| **80–89** | ✅ Accept with notes (no re-work) | Automated |
| **70–79** | ⚠️ Manual review — Lead Engineer decides | Lead Engineer |
| **60–69** | 🔄 Auto rework triggered (max 2 retries) | Decision Engine |
| **<60** | 🚨 Escalate to Principal Engineer | Principal Engineer |
| **Critical finding** | 🚨 Escalate immediately (any score) | Principal Engineer |

### 3.5 Accepted HANDBACK Example (Score 87)

```yaml
handoff_type: HANDBACK
task_id: 2026-05-09-add-jwt-validation
agent: senior_engineer
status: complete
deliverables:
  - src/api/middleware.py
  - tests/test_jwt_validation.py
tests:
  passed: 34
  failed: 0
  coverage: 91.2
  framework: pytest
  notes: "All JWT branches covered; grace period boundary tests included"
quality_score: 87
effort_actual: medium
tokens_in: 3200
tokens_out: 1100
token_usage:
  input: 3200
  output: 1100
  cached: 400
  total: 4300
  billable_total: 3900
  source: api_usage
duration_minutes: 24
notes: |
  Implemented validate_jwt() with configurable GRACE_PERIOD_SECS=30 constant.
  Added 12 new tests covering: valid token, expired token (>30s rejected),
  grace period boundary (≤30s accepted), missing header, and malformed signature.
  Coverage 91.2% on middleware.py. All 34 tests pass.
```

### 3.6 Gray-Zone HANDBACK Example (Score 74, Conditional)

```yaml
# Score 74: Routed to Lead Engineer for manual review
# Lead Engineer assessment: accept with required follow-up
# Conditional approval: merge now; file coverage issue as P2 task
quality_score: 74
tests:
  passed: 22
  failed: 0
  coverage: 68.5   # Below 70% threshold — flagged
notes: "Implementation complete but coverage fell short of 70% threshold"
```

### 3.7 Failed HANDBACK Example (Score 55, Escalated)

```yaml
# Score 55: Escalated to Principal Engineer after 2 retries
quality_score: 55
status: partial
tests:
  passed: 18
  failed: 6
  coverage: 58.0
notes: "Test failures persist in JWT expiry branch; root cause unclear after 2 attempts"
```

---

## 4. Quality Gates & Thresholds

### 4.1 Composite Scoring Formula

```
composite_score = (layer1_score × 0.40) + (layer2_score × 0.35) + (layer3_score × 0.25)
```

Where each layer score is 0–100 based on the checks in Section 3.3.

### 4.2 Layer Weight Rationale

| Layer | Weight | Rationale |
|-------|--------|-----------|
| Layer 1 — Format | 40% | Format errors prevent automation; highest leverage |
| Layer 2 — Content | 35% | Content quality is the core value delivered |
| Layer 3 — Quality | 25% | Quality signals matter but require human judgment in edge cases |

### 4.3 Critical Finding Override

Any of these findings immediately escalates regardless of composite score:
- Hardcoded secret, password, or API key in deliverables
- Production-hazard code (`panic`, unrecovered error in critical path)
- Security vulnerability (injection, auth bypass, privilege escalation)
- Data loss risk in database migrations without rollback

---

## 5. Routing Decisions

### 5.1 Score Bands

| Band | Score | Action |
|------|-------|--------|
| PROCEED | 90–100 | Accept immediately; move to done/ |
| PROCEED | 80–89 | Accept with notes; move to done/ |
| MANUAL_REVIEW | 70–79 | Route to Lead Engineer; see Section 5.3 |
| REWORK | 60–69 | Auto-rework (max 2 retries); see Section 6 |
| ESCALATE | <60 | Principal Engineer; no auto-retry |

### 5.2 Routing Flow

```
HANDBACK received
    │
    ├─ [Layer 1 < 50] ──────────────────────→ Re-DELEGATE (max 1 retry)
    │                                              │
    │                                    [Still < 50 after 1]
    │                                              ↓
    │                                    Lead Engineer manual review
    │
    ├─ [Score 60–79] ───────────────────────→ Re-DELEGATE (max 2 retries)
    │                                              │
    │                                [Still 60–79 after 2 retries]
    │                                              ↓
    │                                    Principal Engineer
    │
    ├─ [Score < 60] ────────────────────────→ Re-DELEGATE (max 2 retries)
    │                                              │
    │                                  [Still < 60 after 2 retries]
    │                                              ↓
    │                                    Principal Engineer
    │
    ├─ [Critical finding, any score] ───────→ Principal Engineer immediately
    │
    ├─ [Agent status: blocked] ─────────────→ One role up immediately
    │                                         Engineer → Senior Engineer
    │                                         Senior → Lead Engineer
    │                                         Lead → Principal Engineer
    │
    └─ [Re-work cost > 150% original] ──────→ Principal Engineer
                                               (flag for Model Engineer)
```

### 5.3 Gray-Zone Review (70–79)

When composite score is 70–79, Lead Engineer performs manual review:

1. **Read** the HANDBACK notes, deliverables, and test results
2. **Assess** what criteria were met and which fell short
3. **Decide** one of three outcomes:
   - **Accept**: Quality sufficient; merge with notes
   - **Conditional Accept**: Merge now; create follow-up P2 task for gaps
   - **Rework**: Gaps too significant; trigger rework DELEGATE

Lead Engineer documents decision in `qe_feedback.lead_review` block.

### 5.4 Retry Mechanics

```python
MAX_RETRIES = 2   # Hard cap — no exceptions

# In orchestrator.py post-HANDBACK processing:
if decision["action"] == "rework":
    if task_metadata["retry_count"] >= MAX_RETRIES:
        route_to_principal_engineer(task, reason="Max retries exceeded")
    else:
        task_metadata["retry_count"] += 1
        issue_rework_delegate(task)
```

---

## 6. Re-work & Retry Mechanism

### 6.1 Trigger Conditions (10 Total)

| Condition | Action | Limit |
|-----------|--------|-------|
| Layer 1 Format Gate < 50 | Re-DELEGATE (format fix only) | Max 1 |
| Layer 2 Content: criteria unmet | Re-DELEGATE (specific failures listed) | Max 2 |
| Composite score < 60 | Re-DELEGATE to same agent | Max 2 |
| Composite score 60–79 | Manual review → may trigger rework | No auto-retry |
| `status: failed` + no blockers documented | Re-DELEGATE + require blocker docs | Max 1 |
| `status: partial` + <80% criteria met | Re-DELEGATE for remaining items | Max 2 |
| Test coverage dropped | Re-DELEGATE with explicit coverage requirement | Max 2 |
| Agent requests escalation (`status: blocked`) | Immediate role escalation | None |
| Re-work cost >150% of original estimate | Principal Engineer decides | None |
| Critical finding | Principal Engineer immediately | None |

### 6.2 Automatic vs. Manual Rework

| Trigger | Type |
|---------|------|
| Score-based thresholds | Automatic (Decision Engine) |
| Gray-zone 70–79 | Manual (Lead Engineer) |
| Critical finding | Manual (Principal Engineer) |
| Agent blocked | Manual (next role up) |

### 6.3 Task ID Retry Suffix Convention

```
Original:   2026-05-09-add-jwt-validation
Retry 1:    2026-05-09-add-jwt-validation-retry-1
Retry 2:    2026-05-09-add-jwt-validation-retry-2
Escalated:  2026-05-09-add-jwt-validation-escalated
```

### 6.4 retry_context Block (Required on All Re-work DELEGATEs)

```yaml
retry_context:
  original_task_id: 2026-05-09-add-jwt-validation
  retry_count: 1                    # 1-based
  previous_quality_score: 65
  failure_reasons:
    - "Test coverage 62% < 70% threshold"
    - "success_criteria 'all endpoints tested' not met"
  specific_failures:
    - criterion: "pytest returns zero failures"
      passed: false
      evidence: "3 tests failing in test_jwt_expiry.py (see HANDBACK tests field)"
```

### 6.5 Re-work DELEGATE Construction Rules

1. Copy the original DELEGATE exactly (same scope, role, model, effort)
2. Add `retry_context` block (as above)
3. Replace `plan` with a targeted plan addressing only the failing criteria
4. Reference the previous HANDBACK explicitly in `context`
5. Keep `success_criteria` identical (bar must not be lowered)

---

## 7. Metrics Collection & Storage

### 7.1 35-Field Canonical Schema

Every completed task produces one metrics record at:
`artifacts/metrics/YYYY-MM-DD-{task_id}-metrics.yaml`

**Routing fields:**
`agent_type`, `model_used`, `model_intended`, `effort_declared`, `effort_actual`

**Outcome fields:**
`status`, `final_decision`, `re_work_count`, `escalated`, `escalation_target`

**Quality scores:**
`quality_score_validator` (authoritative), `quality_score_agent_self` (calibration only),
`layer1_score`, `layer2_score`, `layer3_score`, `success_criteria_met_pct`, `validation_pass_rate`

**Test quality:**
`test_coverage_pct`, `tests_passed`, `tests_total`, `coverage_delta`

**Cost & efficiency:**
`tokens_in`, `tokens_out`, `tokens_total`, `tokens_total_all_attempts`,
`original_token_estimate`, `cost_overrun_pct`, `duration_minutes`, `escalations_within_task`

**QE assessment:**
`qe_model_assessment`, `qe_confidence`, `qe_test_coverage_assessment`, `qe_error_handling_assessment`

**Signals for Model Engineer:**
`task_complexity_signal`, `model_appropriate`, `flag_for_model_engineer`

### 7.2 Derived Metrics

| Metric | Formula |
|--------|---------|
| `efficiency_score` | `quality_score_validator / (tokens_total / 1000)` |
| `rework_cost_ratio` | `tokens_total_all_attempts / tokens_total` |

### 7.3 Metrics Consumers

| Consumer | Fields Used | Purpose |
|----------|-------------|---------|
| **Model Engineer** | `model_used`, `quality_score_validator`, `qe_model_assessment`, `flag_for_model_engineer` | Optimize routing |
| **TokenAdvisor** | `tokens_total`, `cost_overrun_pct`, `duration_minutes` | Cost analysis |
| **Orchestrator** | `re_work_count`, `final_decision`, `success_criteria_met_pct` | Improve future DELEGATEs |
| **Quality Engineer** | All 35 fields | Calibrate thresholds |
| **Principal Engineer** | `escalated`, `flag_for_model_engineer`, `re_work_count` | Strategic decisions |

---

## 8. Consistency Enforcement

### 8.1 Pre-Commit Hook Validation

The `.git/hooks/pre-commit` hook runs Group A/B/C validation on every commit that
includes a DELEGATE block. Enforced by `orchestration/agents/delegate_validator.py`.

```
Commit attempt with DELEGATE
    ↓
Pre-commit hook fires
    ↓
Group A validation (hard gates)
    │
    ├─ [Any A failure] → Commit BLOCKED + error message
    │
    ↓
Group B validation (content quality)
    │
    ├─ [Any B failure] → Commit BLOCKED + refinement hint
    │
    ↓
Group C validation (routing sanity)
    │
    ├─ [Any C failure] → Commit BLOCKED + re-route suggestion
    │
    └─ [All pass] → Commit ALLOWED
```

### 8.2 Pre-Flight Checklist (Orchestrator)

Before emitting any DELEGATE, the Orchestrator runs through all A/B/C checks
internally. This is a second line of defense beyond the pre-commit hook.

### 8.3 Red Flags (Automatically Blocked)

```
❌ task_id format invalid or reused
❌ role not in: engineer, senior_engineer, lead_engineer, principal_engineer,
               security_engineer, quality_engineer, model_engineer
❌ scope < 15 words or contains only vague phrases ("implement it", "fix things")
❌ success_criteria: aspirational only ("good code", "clean implementation")
❌ Password, secret, token, or API key found in DELEGATE text
❌ effort:low with plan > 8 steps (under-estimation red flag)
```

---

## 9. Escalation Paths

| Trigger | Target | Rationale |
|---------|--------|-----------|
| Score <60 after 2 retries | Principal Engineer | Persistent failure; approach may be wrong |
| Critical finding (any score) | Principal Engineer immediately | Security/architecture risk |
| Retry count >2 | Principal Engineer | Hard cap exceeded |
| `status: failed` with no recovery path | Principal Engineer | Blocked task needs senior judgment |
| Agent requests escalation (`status: blocked`) | Role one level up | Blocker requires higher authority |
| Gray-zone after Lead Engineer review (conditional) | Principal Engineer | If Lead cannot resolve |

### 9.1 Escalation Notice Format

```yaml
escalation_notice:
  task_id: 2026-05-09-add-jwt-validation
  escalation_reason: "Quality score 58/100 after 2 retries"
  retry_history:
    - attempt: 1
      quality_score: 65
      failure_reasons: ["coverage 62% < 70%", "3 tests failing"]
    - attempt: 2
      quality_score: 58
      failure_reasons: ["coverage 59% < 70%", "root cause unclear"]
  total_tokens_consumed: 9200
  original_estimate_tokens: 3200
  recommendation: "Task may be under-scoped; consider principal_engineer"
  flag_for_model_engineer: true
```

---

## 10. Agent Responsibilities

| Role | Model | Effort | Protocol Responsibilities |
|------|-------|--------|--------------------------|
| **Orchestrator** | Haiku | low | Route all work; emit valid DELEGATEs; enforce Group A/B/C pre-flight; track retry counts; emit metrics |
| **Engineer** | Haiku | high | Accept well-planned DELEGATEs; return complete HANDBACKs; report `blocked` immediately if stuck |
| **Senior Engineer** | Sonnet | high | Design solutions; write plans for Engineer; accept complex DELEGATEs; mentor Engineers |
| **Lead Engineer** | Sonnet | high | Code review; gray-zone HANDBACK decisions; conditional approvals; quality oversight |
| **Quality Engineer** | Sonnet | medium | Post-implementation validation; `qe_feedback` block on every HANDBACK; metrics analysis |
| **Principal Engineer** | Opus | high | Escalated complex tasks; cross-service decisions; protocol oversight; monthly reviews |
| **Security Engineer** | Opus | max | Security-scoped tasks only; threat modeling; vulnerability review |
| **Model Engineer** | Sonnet | high | Analyze metrics; recommend model/effort optimizations; flag cost anomalies |

### 10.1 Role Escalation Chain

```
Engineer → Senior Engineer → Lead Engineer → Principal Engineer
Security Engineer (isolated path — invoke only for security scope)
Model Engineer (metrics/optimization — not task execution)
```

---

## 11. Examples & Troubleshooting

### 11.1 Complete Passing DELEGATE (Groups A/B/C all pass)

See Section 2.4 for the full example with all required fields.

### 11.2 Complete Accepted HANDBACK (Score 87)

See Section 3.5 for the full HANDBACK example.

### 11.3 Gray-Zone HANDBACK (Score 74, Conditional Approval)

See Section 3.6. Lead Engineer outcome: "Accept conditionally; file P2 task for
coverage to reach 85% within 2 weeks."

### 11.4 Failed HANDBACK (Score 55, Escalated)

See Section 3.7. After 2 retries both below 60, escalated to Principal Engineer
with full retry history and token cost overrun report.

### 11.5 Common Issues & Remediation

| Issue | Symptom | Fix |
|-------|---------|-----|
| DELEGATE blocked by pre-commit | Hook error on commit | Fix Group A/B/C failures in error output |
| HANDBACK score unexpectedly low | Score <80 despite "complete" | Check Layer 1 for format errors; check Layer 2 for unmet criteria |
| Agent reports `status: blocked` | Task stuck | Orchestrator escalates to next role; provide blocker context |
| Retry count at 2, still failing | Escalation notice generated | Principal Engineer reviews approach; may redesign or re-scope |
| `task_id` mismatch | Layer 1 CRITICAL failure (−25) | HANDBACK `task_id` must be byte-for-byte identical to DELEGATE |
| Coverage dropped | Layer 3 warning | Always run coverage report before submitting HANDBACK |
| Scope creep detected | Layer 2 penalty | Stay within DELEGATE scope; document any necessary deviations |

---

## 12. Implementation Status

| Phase | Deliverable | Status |
|-------|-------------|--------|
| **Week 1** | Pre-flight validation system | ✅ Complete |
| **Week 1** | `delegate-schema.yaml` | ✅ Complete |
| **Week 1** | `handback-schema.yaml` | ✅ Complete |
| **Week 1** | `delegate_validator.py` (Groups A/B/C) | ✅ Complete |
| **Week 1** | Pre-commit hook | ✅ Complete |
| **Week 1** | 33+ protocol validation tests | ✅ Complete |
| **Week 2** | `route_handback()` function | ⏳ In Progress |
| **Week 2** | `collect_metrics()` function | ⏳ In Progress |
| **Week 2** | `metrics_writer.py` module | ✅ Module exists |
| **Week 2** | Retry count cap (MAX_RETRIES=2) | ⏳ In Progress |
| **Week 2** | `retry_context` block construction | ⏳ In Progress |
| **Week 3** | Gray-zone reviewer module | ⏳ In Progress |
| **Week 3** | Lead Engineer review CLI | ⏳ In Progress |
| **Week 3** | Orchestrator gray-zone integration | ⏳ In Progress |
| **Week 4** | `ORCHESTRATION-PROTOCOL.md` (this file) | ✅ Complete |
| **Week 4** | `AGENT-ONBOARDING.md` | ✅ Complete |
| **Week 4** | `PROTOCOL.md — Appendix G (Quick Reference)` | ✅ Complete |
| **Week 4** | `PROTOCOL-IMPLEMENTATION-STATUS.md` | ✅ Complete |
| **Week 4** | `tools/protocol_audit.py` | ✅ Complete |

### 12.1 Enforcement Readiness

| Gate | Status |
|------|--------|
| Pre-commit hook blocks bad DELEGATEs | ✅ Active |
| Orchestrator pre-flight checks | ✅ Active |
| Post-HANDBACK scoring | ✅ Active |
| Retry cap enforcement | ⏳ Week 2 |
| Gray-zone review routing | ⏳ Week 3 |
| Metrics canonical record | ⏳ Week 2 |

### 12.2 Rollout Timeline

| Phase | Timeline | Milestone |
|-------|----------|-----------|
| Phase 1 | Week 1 | Pre-flight validation live |
| Phase 2 | Week 2 | Routing & metrics live |
| Phase 3 | Week 3 | Gray-zone review live |
| Phase 4 | Week 4 | Full documentation live — **current** |
| Phase 5 | Post-Week 4 | CI/CD gate integration |
| Ongoing | Monthly | Principal Engineer protocol reviews |

---

## 13. Appendices

### Appendix A: DELEGATE Schema (Formal YAML)

See `orchestration/delegate-schema.yaml` for the authoritative machine-readable schema
used by `delegate_validator.py`.

### Appendix B: HANDBACK Schema (Formal YAML)

See `orchestration/handback-schema.yaml` for the authoritative machine-readable schema
used by `quality_validator.py`.

### Appendix C: Quality Scoring Formula

```python
# Layer scores (each 0–100)
layer1 = format_gate_score()       # structural integrity
layer2 = content_gate_score()      # task quality / criteria met
layer3 = quality_gate_score()      # post-completion / QE assessment

# Composite
composite = (layer1 * 0.40) + (layer2 * 0.35) + (layer3 * 0.25)

# Routing decision
if composite >= 90:   action = "proceed"
elif composite >= 80: action = "proceed_with_notes"
elif composite >= 70: action = "manual_review"
elif composite >= 60: action = "rework"
else:                 action = "escalate"
```

### Appendix D: Metrics Schema (35 Fields)

See `orchestration/DELEGATE-HANDBACK-QUALITY-GATES.md` Section 5 for the full 35-field
canonical metrics YAML schema with all field descriptions and example values.

### Appendix E: Glossary

| Term | Definition |
|------|-----------|
| **DELEGATE** | Structured YAML task transfer from Orchestrator to a specialist agent |
| **HANDBACK** | Structured YAML result returned by a specialist agent after task execution |
| **Gray zone** | Quality score 70–79; requires Lead Engineer manual review |
| **Composite score** | Weighted average of Layer 1/2/3 scores (40/35/25%) |
| **Pre-flight** | Orchestrator-side validation of a DELEGATE before emission |
| **retry_context** | Block added to re-work DELEGATEs tracking previous attempt details |
| **MAX_RETRIES** | Hard cap of 2 automatic retries; escalates to Principal Engineer on overflow |
| **Effort band** | Bucketed estimate: low(1-4h), medium(5-16h), high(17-48h), max(49-120h), epic(121h+) |
| **Validator score** | Authoritative quality score from `quality_validator.py`; overrides agent self-score |
| **Agent self-score** | Quality score self-reported by the agent; recorded for calibration only |
| **Escalation** | Routing a task to a higher-authority role due to failure or blocker |
| **Dark factory** | Autonomous operation mode — no human interaction until completion |

### Appendix F: Contact & Escalation

| Question Type | Who to Ask |
|--------------|------------|
| Protocol interpretation | Lead Engineer |
| Metrics & cost optimization | Model Engineer |
| Architecture decisions | Principal Engineer |
| Quality thresholds | Quality Engineer |
| Security concerns | Security Engineer |
| Implementation bugs | Senior Engineer |

---

## Appendix G: Quick Reference

> **One-page cheat sheet for daily use.**

### DELEGATE Required Fields (9 core)
`task_id` · `role` · `model` · `effort` · `estimated_hours` · `scope` · `success_criteria` · `plan` · `context`

**task_id format:** `YYYY-MM-DD-kebab-case`

**Effort bands:**
| Level | Hours | Min Role |
|-------|-------|----------|
| `low` | 1–4h | engineer |
| `medium` | 5–16h | engineer |
| `high` | 17–48h | senior_engineer |
| `max` | 49–120h | lead_engineer |
| `epic` | 121h+ | principal_engineer |

### HANDBACK Required Fields (12)
`task_id` · `handoff_type` · `status` · `deliverables` · `tests` · `quality_score` · `effort_actual` · `tokens_in` · `tokens_out` · `duration_minutes` · `notes` · `agent`

**Status values:** `complete` · `failed` · `partial` · `blocked`

### Quality Routing
| Score | Action | Who |
|-------|--------|-----|
| 90–100 | Merge immediately ✅ | Automated |
| 80–89 | Merge with notes ✅ | Automated |
| 70–79 | Lead Engineer review ⚠️ | Lead Engineer |
| 60–69 | Auto-rework 🔄 | Decision Engine |
| <60 | Escalate 🚨 | Principal Engineer |

### Retry Rules
```
MAX_RETRIES = 2  (hard cap)
Retry 1: {original-id}-retry-1
Retry 2: {original-id}-retry-2
Escalated: {original-id}-escalated
```

### Red Flags (pre-commit blocks)
- task_id invalid/reused in same session
- scope < 15 words or vague
- success_criteria aspirational ("good code", "works well")
- secrets in DELEGATE text
- effort:low with >8 plan steps
- effort:high/max with role:engineer

### Scoring Formula
```
composite = (layer1 × 0.40) + (layer2 × 0.35) + (layer3 × 0.25)
```

### Role Quick Map
| Role | Model | Use For |
|------|-------|---------|
| engineer | Haiku | Well-planned, well-scoped tasks |
| senior_engineer | Sonnet | Complex coding without pre-written plan |
| lead_engineer | Sonnet | Code review; gray-zone decisions |
| quality_engineer | Sonnet | Post-implementation validation |
| principal_engineer | Opus | Cross-service architecture; escalations |
| security_engineer | Opus | Security scope only |
| model_engineer | Sonnet | Metrics analysis; routing optimization |

---

## 14. Sub-Task Workflows (Phase 2)

> **Added:** Phase 2 implementation. Enables agents to create sub-tasks directly,
> reducing Orchestrator load by 60–70% and enabling parallel task execution.

### 14.1 Overview

Any agent can decompose its assigned task into child tasks by queuing sub-tasks
via the `queue-management` skill. The Orchestrator detects when a parent task has
children and performs result aggregation automatically.

### 14.2 New DELEGATE Fields

```yaml
# DELEGATE (enhanced for sub-tasks)
task_id: "2026-05-13-master-arch-review"
role: senior_engineer
scope: "Review microservices architecture ..."
plan: [...]
context: "..."

# NEW (optional): Sub-task linking
parent_task_id: "2026-05-12-sprint-planning"  # parent task ID
task_tier: 1                                   # auto-calculated (parent_tier + 1)
```

| Field | Type | Required | Rules |
|-------|------|----------|-------|
| `parent_task_id` | string | optional | Must exist in any queue state; cannot be self or ancestor |
| `task_tier` | int 0–5 | optional | Auto-calculated as `parent_tier + 1`; max depth is **5** |

**Validation rules:**
- `parent_task_id` must exist in `incoming/`, `processing/`, or `done/`
- `task_tier` is **auto-calculated** — agents should not set it manually
- Maximum depth: tier 5 (grandparent→parent→child→grandchild→great-grandchild)
- Maximum width: **10 children per parent**
- Cycle detection: linking to self or ancestors is rejected

### 14.3 New HANDBACK Fields

```yaml
# HANDBACK (enhanced for parent tasks)
task_id: "2026-05-13-master-arch-review"
status: complete

# NEW (optional): Aggregated results
children_created:
  - "2026-05-13-arch-service-a"
  - "2026-05-13-arch-service-b"
children_results:
  "2026-05-13-arch-service-a":
    status: complete
    output: {bottlenecks: [], recommendations: []}
    quality: 92
  "2026-05-13-arch-service-b":
    status: complete
    output: {bottlenecks: [...], recommendations: [...]}
    quality: 88
children_failed: []
result_aggregation_status: all_complete   # all_complete | partial | timed_out
```

| Field | Type | Rules |
|-------|------|-------|
| `children_created` | list[str] | Task IDs of sub-tasks created |
| `children_results` | dict | Keyed by task_id; each entry has `status`, `output`, `quality` |
| `children_failed` | list[str] | Task IDs that failed or were blocked |
| `result_aggregation_status` | enum | `all_complete`, `partial`, `timed_out` |

### 14.4 Sub-Task Workflow Lifecycle

```
1. Orchestrator picks up parent task from incoming/
2. Agent executes and may create child tasks via queue-management skill
3. Orchestrator detects has_children(parent_task_id) → True
4. Orchestrator calls wait_for_children(parent_task_id, timeout_minutes=60)
5. All children execute in parallel (each goes through incoming→processing→done)
6. Orchestrator aggregates results: quality (weighted avg), tokens (sum), costs (sum)
7. Parent HANDBACK is stored with children_results populated
```

### 14.5 Quality Score Aggregation

Quality scores are **effort-weighted averages**:

| Effort Level | Weight |
|-------------|--------|
| `high`      | 3×     |
| `medium`    | 2×     |
| `low`       | 1×     |

Example: 3 children with scores `[90, 60, 30]` and efforts `[high, medium, low]`:
```
weighted_quality = (90×3 + 60×2 + 30×1) / (3+2+1) = 420/6 = 70.0
```

### 14.6 Failure Modes

| Mode | Behaviour |
|------|-----------|
| `partial` (default) | Parent continues; `result_aggregation_status = partial` |
| `all_or_nothing` | Parent fails if any child fails |

### 14.7 Depth & Width Limits

| Limit | Value | Error |
|-------|-------|-------|
| Max depth (task_tier) | 5 | `ValueError: task_tier X exceeds maximum` |
| Max children per parent | 10 | `RuntimeError: already has N children (max 10)` |
| Max tasks/hour (session) | 100 | `RuntimeError: Rate limit exceeded` |
