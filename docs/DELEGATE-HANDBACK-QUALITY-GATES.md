---
name: Delegate/Handback Quality Gates & Re-work Mechanism
description: Quality gates, acceptance criteria, and re-work policy ensuring every HANDBACK meets minimum standards before Orchestrator acts on it
created: 2026-06-02
type: policy
owner: Quality Engineer
status: APPROVED
references:
  - orchestration/QUALITY.md
  - orchestration/HANDOFF.md
  - docs/quality-standards.md
  - docs/quality-validation-rules.md
  - orchestration/agents/quality_validator.py
  - orchestration/agents/decision_engine.py
---

# Delegate/Handback Quality Gates & Re-work Mechanism

## Executive Summary

This document defines the end-to-end quality lifecycle for every DELEGATE and HANDBACK in
the agentic-engineers system. It closes three gaps identified in the current implementation:

1. **No Orchestrator pre-delegation checklist** — DELEGATE quality is validated by
   `quality_validator.py` Layer 1/2, but Orchestrator has no structured gate _before_ the
   block is written.
2. **No retry-limit enforcement** — `decision_engine.py` outputs `action: rework` but no
   mechanism caps retries at 2 or routes to Principal Engineer on the third failure.
3. **No canonical metrics record** — tokens, duration, and quality score appear in
   HANDBACKs but are not aggregated into a single schema consumed by Model Engineer.

---

## Current State Assessment

### Prior Delegation Analysis

A review of existing DELEGATE/HANDBACK artifacts reveals the following patterns:

| Dimension | Finding | Gap |
|-----------|---------|-----|
| **Success criteria defined?** | ✅ Yes — all reviewed DELEGATEs include `success_criteria` | Success criteria are sometimes aspirational ("reference-quality") rather than verifiable |
| **Plan completeness** | ✅ Yes — numbered steps, concrete actions | No enforcement that plan steps map 1:1 to HANDBACK deliverables |
| **Deliverable validation** | ⚠️ Partial — structural check (Layer 3 in `quality_validator.py`) only | Content verification (do deliverables actually exist? do tests pass?) not automated |
| **Re-work performed** | ❌ No evidence — all reviewed tasks completed first-try | Rework path defined in QUALITY.md but never exercised; no retry counter anywhere |
| **Metrics tracked** | ⚠️ Partial — `tokens_in`, `tokens_out`, `duration_minutes`, `quality_score` in HANDBACKs | No aggregated record with `re_work_count`, `success_criteria_met %`, `validation_pass_rate` |
| **Quality score source** | ⚠️ Dual-sourced — agent self-reports `quality_score`; validator computes it independently | Risk of score inflation when agent self-reports; validator score should be authoritative |

### What Already Works Well

- **`quality_validator.py`** — Three-layer validation (Layer 1: DELEGATE structure,
  Layer 2: task quality / routing, Layer 3: HANDBACK structure) with composite scoring.
- **`decision_engine.py`** — Post-execution evaluation: `proceed` (≥80, all criteria met),
  `rework` (70–79 or partial criteria), `escalate` (<70 or agent escalated).
- **`orchestration/QUALITY.md`** — Tier 1/2/3 agent-facing checklists with worked examples.
- **`orchestration/HANDOFF.md`** — Canonical DELEGATE/HANDBACK YAML schema with mandatory
  fields, validation rules, and `qe_feedback` block.
- **`docs/quality-standards.md`** — Human-readable companion to validation rules with
  anti-patterns and routing thresholds.

---

## 1. Pre-Delegation Quality Gates (DELEGATE Checklist)

### Rationale

Sending a poor DELEGATE is the single biggest driver of re-work. A well-formed DELEGATE
costs ~30 seconds of Orchestrator thought; fixing a bad one costs the full agent execution
cost plus re-work tokens.

### DELEGATE Pre-flight Checklist

Orchestrator MUST verify every item before emitting a DELEGATE block:

#### Group A — Structure (Non-negotiable; any `NO` = do not send)

| # | Check | How to Verify |
|---|-------|--------------|
| A1 | `task_id` uses kebab-case `YYYY-MM-DD-slug` format | Regex: `^[a-z0-9][a-z0-9\-]{0,62}[a-z0-9]$` |
| A2 | `task_id` is unique (not used by another task in the same session) | Search `artifacts/` for existing use |
| A3 | `role` is valid (matches `AGENTS.md` role column exactly) | One of: engineer, senior_engineer, lead_engineer, principal_engineer, security_engineer, quality_engineer, model_engineer |
| A4 | `model` matches the role's default (or justified override) | Cross-check `AGENTS.md` model column |
| A5 | `effort` is appropriate for the scope (not mismatched) | See mismatch table below |
| A6 | `scope` is ≥15 words, contains an action verb, names the subject | Read aloud — does it answer "what will be done to what?" |
| A7 | No secrets embedded (passwords, tokens, API keys, private keys) | Grep DELEGATE text for: `password`, `secret`, `token`, `api_key` |

#### Group B — Content Quality (any `NO` = refine before sending)

| # | Check | How to Verify |
|---|-------|--------------|
| B1 | `success_criteria` are **measurable and testable** (not "good code") | Ask: "Can I verify this in 30 seconds without reading the implementation?" |
| B2 | `success_criteria` are **complete** (all expected outputs covered) | List outputs → map each to a criterion |
| B3 | `plan` steps are **numbered and concrete** (not "implement the feature") | Each step should name a specific file, command, or action |
| B4 | `plan` steps **cover testing** (not just implementation) | At least one step references running tests or adding test coverage |
| B5 | `context` provides sufficient background for agent to start immediately | Ask: "Would a new agent need to ask a clarifying question?" |
| B6 | Scope is **bounded** (explicit out-of-scope list for ≥medium effort) | High-effort tasks must say what NOT to do |
| B7 | `effort` estimate is **realistic** (not artificially low to save tokens) | If task requires 500+ lines, effort should be `high` or `max` |

#### Group C — Routing Sanity

| # | Check | Failure = |
|---|-------|-----------|
| C1 | `effort: high/max` → `role` is senior_engineer or above | Downgrade effort or upgrade role |
| C2 | Security-scoped task → `role: security_engineer` | Re-route |
| C3 | Cross-service architecture → `role: principal_engineer` | Re-route |
| C4 | Code review / quality audit → `role: lead_engineer` or `quality_engineer` | Re-route |

#### Effort × Role Mismatch Table

| effort | Minimum role | Reason |
|--------|-------------|--------|
| `low` | engineer | Routine, well-defined |
| `medium` | engineer | Moderate complexity |
| `high` | senior_engineer | Design decisions required |
| `max` | lead_engineer | Architecture impact |
| `epic` | principal_engineer | Cross-service, strategic |

### Red Flags That Require Rework of the DELEGATE

These indicate the DELEGATE needs to be rewritten before sending:

```
❌ scope: "Fix the bug"           → Too vague. Add file:line, root cause, expected behaviour.
❌ plan: "Implement everything"   → Not actionable. Number the steps.
❌ success_criteria: "Works well" → Not testable. What passes? What fails?
❌ effort: low, plan: 12 steps    → Effort underestimated. Upgrade to medium/high.
❌ role: engineer, effort: max    → Mis-routed. Upgrade to senior/lead.
❌ context: (empty)               → Agent will ask for more info. Provide it upfront.
```

---

## 2. Post-HANDBACK Quality Gates (HANDBACK Checklist)

### Layer System (Existing → Extended)

The existing three-layer system in `quality_validator.py` is the authoritative engine.
This checklist defines the _human-readable_ interpretation of each layer's requirements.

#### Layer 1 — Format Gate (Structural Integrity, Weight: 40%)

Validated automatically by `quality_validator.py` before any human review:

| Field | Requirement | Failure Severity |
|-------|------------|-----------------|
| `handoff_type` | Must equal `"HANDBACK"` | CRITICAL (−25) |
| `task_id` | Must exactly match the DELEGATE `task_id` | CRITICAL (−25) |
| `status` | Must be one of: `complete`, `failed`, `partial` | ERROR (−15) |
| `deliverables` | Required for `effort: high/max/epic` | ERROR (−10) |
| `tests` | Required for engineer-tier roles | ERROR (−10) |
| `notes` | ≥5 words; must explain outcome | ERROR (−10) |
| `tokens_in` | Present and positive integer | WARNING (−5) |
| `tokens_out` | Present and positive integer | WARNING (−5) |
| `duration_minutes` | Present and positive | WARNING (−5) |

**Format Gate Pass threshold:** Layer 1 score ≥ 60 (Layer 2/3 are skipped below 50).

#### Layer 2 — Content Gate (Task Quality, Weight: 35%)

Verified by Decision Engine against the original DELEGATE's `success_criteria`:

| Criterion | Requirement | Weight |
|-----------|------------|--------|
| All `plan` steps executed | Each plan step maps to a deliverable or documented deviation | 30% |
| `success_criteria` addressed | Every criterion from DELEGATE is referenced in HANDBACK | 40% |
| Tests pass | `tests` field shows passing result; test count ≥ previous count | 20% |
| No scope creep | Deliverables are within DELEGATE `scope` only | 10% |

**Content Gate Pass threshold:** Layer 2 score ≥ 70.

#### Layer 3 — Quality Gate (Post-completion, Weight: 25%)

Verified by Quality Engineer (`qe_feedback` block) and automated checks:

| Check | Threshold | Source |
|-------|-----------|--------|
| Composite quality score | ≥ 80/100 for acceptance without review | `quality_validator.py` composite |
| Test coverage | ≥ 70% for modified packages | `tests.coverage` field in HANDBACK |
| No production hazards | Zero new `panic`, hardcoded secrets, commented-out code | Tier 1 checklist in `QUALITY.md` |
| QE model assessment | `qe_feedback` block present on all completed tasks | `QUALITY.md` QE Feedback section |
| Deliverables exist | All files referenced in `deliverables` field actually present on disk | Automated spot-check |

### HANDBACK Acceptance Thresholds

| Composite Score | Action | Who Decides |
|-----------------|--------|-------------|
| **90–100** | ✅ Accept immediately | Automated |
| **80–89** | ✅ Accept with notes (no re-work) | Automated |
| **70–79** | ⚠️ Manual review — Lead Engineer decides | Lead Engineer |
| **60–69** | 🔄 Re-work triggered automatically | DecisionEngine → re-DELEGATE |
| **< 60** | 🚨 Escalate to Principal Engineer | Principal Engineer |
| **Critical finding** | 🚨 Escalate immediately (regardless of score) | Principal Engineer |

### Alignment with Existing Implementation

The current `orchestrator.py` (line 824) escalates to Quality Engineer when
`quality_score < 70` and `PROCEED`s above 70. This design extends that behaviour:

| Score | Current behaviour | This design |
|-------|------------------|-------------|
| ≥80 | PROCEED | PROCEED (automated) |
| 70–79 | PROCEED | Lead Engineer manual review (new gate) |
| <70 | Escalate → Quality Engineer | Re-work (max 2 retries) → Principal Engineer |
| Critical | Escalate → Quality Engineer | Principal Engineer immediately |

The 70–79 "gray zone" manual review is a **new gate not yet implemented**. Until
implemented, existing code behaviour applies (PROCEED at 70+). Add this gate as
Priority 1 in the implementation plan below.

---

### Self-Reported vs. Computed Score Policy

**Problem identified:** Agents self-report `quality_score` in their HANDBACK, which creates
inflation risk. The `quality_validator.py` computes an independent score.

**Policy:** The **validator-computed score is authoritative**. Agent self-reported scores
are recorded in metrics as `agent_self_score` for calibration purposes only. Routing and
re-work decisions use the validator score exclusively.

---

## 3. Re-work Trigger Matrix

### Trigger Conditions → Actions

| Condition | Trigger | Action | Retry Limit |
|-----------|---------|--------|-------------|
| Layer 1 Format Gate fails (score < 50) | Automatic | Re-DELEGATE to same agent; instruct format fix only | Max 1 retry |
| Layer 2 Content Gate: criteria not met | Automatic | Re-DELEGATE with specific failing criteria listed | Max 2 retries |
| Composite score < 60 | Automatic | Re-DELEGATE to same agent | Max 2 retries |
| Composite score 60–79 | Manual review | Lead Engineer reviews; may accept or trigger re-work | No auto-retry |
| Composite score ≥ 80 | None | Accept | N/A |
| Critical finding (any score) | Immediate escalation | Principal Engineer | No retry |
| `status: failed` + no blockers documented | Automatic | Re-DELEGATE; require blocker documentation | Max 1 retry |
| `status: partial` + <80% criteria met | Automatic | Re-DELEGATE for remaining items only | Max 2 retries |
| Test coverage dropped | Automatic | Re-DELEGATE with coverage requirement explicit | Max 2 retries |
| Agent requests escalation (`status: blocked`) | Immediate | Route to role one level up | No retry |
| Re-work cost > 150% of original estimate | Manual | Principal Engineer decides: abandon, redesign, or different agent | No auto-retry |

### Re-work Task ID Convention

To maintain traceability across retries, use this `task_id` suffix convention:

```
Original:   2026-06-02-implement-auth-service
Retry 1:    2026-06-02-implement-auth-service-retry-1
Retry 2:    2026-06-02-implement-auth-service-retry-2
Escalated:  2026-06-02-implement-auth-service-escalated
```

The re-DELEGATE block MUST include:
```yaml
retry_context:
  original_task_id: 2026-06-02-implement-auth-service
  retry_count: 1            # 1-based
  previous_quality_score: 65
  failure_reasons:
    - "Test coverage 62% < 70% threshold"
    - "success_criteria 'all endpoints tested' not met"
  specific_failures:        # from DecisionEngine criteria_results
    - criterion: "make verify passes"
      passed: false
      evidence: "3 tests failing (see HANDBACK tests field)"
```

### Re-work DELEGATE Construction Rules

When constructing a re-work DELEGATE:
1. **Copy the original DELEGATE exactly** (same scope, role, model, effort)
2. **Add `retry_context` block** (as shown above)
3. **Replace `plan`** with a targeted re-work plan addressing only the failing criteria
4. **Explicitly reference the previous HANDBACK** in context
5. **Keep success_criteria identical** — re-work must still meet the original bar

---

## 4. Escalation Policy

### Escalation Path

```
HANDBACK received
    │
    ├─ [Format Gate < 50] ──────────────────────────→ Re-DELEGATE (max 1 retry)
    │                                                       │
    │                                              [Still < 50 after 1]
    │                                                       ↓
    │                                              Lead Engineer manual review
    │
    ├─ [Score 60-79 or partial criteria] ──────────→ Re-DELEGATE (max 2 retries)
    │                                                       │
    │                                     [Still 60-79 after 2 retries]
    │                                                       ↓
    │                                              Principal Engineer
    │                                              → decides: fix approach /
    │                                                different agent / blocked
    │
    ├─ [Score < 60 (first occurrence)] ────────────→ Re-DELEGATE (max 2 retries)
    │                                                       │
    │                                        [Still < 60 after 2 retries]
    │                                                       ↓
    │                                              Principal Engineer
    │
    ├─ [Critical finding, any score] ──────────────→ Principal Engineer immediately
    │                                                  (no retries)
    │
    ├─ [Agent status: blocked] ─────────────────────→ One level up immediately:
    │                                                  Engineer → Senior Engineer
    │                                                  Senior → Lead Engineer
    │                                                  Lead → Principal Engineer
    │
    └─ [Re-work cost > 150% original] ─────────────→ Principal Engineer
                                                       (flag for Model Engineer analysis)
```

### Escalation Role Mapping

| Trigger | Escalation Target | Reason |
|---------|------------------|--------|
| Format gate failure after 1 retry | Lead Engineer | Format is Orchestrator-controllable; Lead reviews process |
| Score 60–79 after 2 retries | Principal Engineer | Persistent mediocre quality; approach may be wrong |
| Score < 60 after 2 retries | Principal Engineer | Consistent failure; task may be mis-scoped |
| Critical finding | Principal Engineer | Security/architecture risk; needs senior judgment |
| Agent blocked | Role +1 (see above) | Blocker requires higher authority |
| Re-work cost overrun | Principal Engineer + Model Engineer | Cost anomaly; model or effort may be mismatched |
| Score 70–79 (gray zone, first occurrence) | Lead Engineer | Borderline; Lead decides accept-with-notes or re-work |

### Preventing Infinite Loops

**Retry Cap Rule:** No task may be re-worked more than **2 times** automatically. After
2 failed retries, all further action requires a human decision by Principal Engineer.

**Implementation requirements in `orchestrator.py`:**

```python
# Task state tracking (add to task metadata / queue record)
task_metadata = {
    "task_id": "...",
    "retry_count": 0,          # increment on each re-DELEGATE
    "MAX_RETRIES": 2,          # hard cap
    "escalation_chain": [],    # record of escalation decisions
    "total_tokens_all_attempts": 0,  # cumulative across retries
    "original_estimate_tokens": 0,
}

# In post-HANDBACK processing:
if decision["action"] == "rework":
    if task_metadata["retry_count"] >= MAX_RETRIES:
        # Escalate instead of retry
        route_to_principal_engineer(task, reason="Max retries exceeded")
    else:
        task_metadata["retry_count"] += 1
        issue_rework_delegate(task)
```

### Escalation Notice Format

When escalating to Principal Engineer, include:

```yaml
escalation_notice:
  task_id: 2026-06-02-implement-auth-service
  escalation_reason: "Quality score 58/100 after 2 retries"
  retry_history:
    - attempt: 1
      quality_score: 62
      failure_reasons: ["coverage 65% < 70%", "endpoint /auth/refresh not tested"]
    - attempt: 2
      quality_score: 58
      failure_reasons: ["coverage 61% < 70%", "3 tests still failing"]
  total_tokens_consumed: 8400
  original_estimate_tokens: 3000
  recommendation: "Task may be under-scoped for engineer tier; consider senior_engineer"
  flag_for_model_engineer: true
```

---

## 5. Metrics Collection Definition

### Canonical Task Metrics Record

Every completed task (regardless of outcome) MUST produce one metrics record. This is the
single source of truth consumed by Model Engineer and TokenAdvisor.

```yaml
# Schema: artifacts/metrics/YYYY-MM-DD-{task_id}-metrics.yaml

task_id: 2026-06-02-implement-auth-service
session_date: 2026-06-02
timestamp_completed: 2026-06-02T14:32:00Z

# ── Routing ──────────────────────────────────────────────────────────────────
agent_type: senior_engineer         # role from DELEGATE
model_used: claude-sonnet-4.6       # actual model (may differ if escalated)
model_intended: claude-sonnet-4.6   # model from DELEGATE
effort_declared: high               # effort from DELEGATE
effort_actual: high                 # effort from HANDBACK

# ── Outcome ──────────────────────────────────────────────────────────────────
status: complete                    # complete | failed | partial | escalated
final_decision: proceed             # proceed | rework | escalate
re_work_count: 0                    # 0 = no retries; 1 = one retry; etc.
escalated: false
escalation_target: null             # null | lead_engineer | principal_engineer

# ── Quality Scores ────────────────────────────────────────────────────────────
quality_score_validator: 87         # AUTHORITATIVE — from quality_validator.py
quality_score_agent_self: 90        # agent self-reported (for calibration only)
layer1_score: 95                    # DELEGATE structural integrity (0-100)
layer2_score: 82                    # Content quality / routing (0-100)
layer3_score: 78                    # HANDBACK post-completion (0-100)
success_criteria_met_pct: 100       # % of success_criteria from DELEGATE that passed
validation_pass_rate: 95            # % of individual validation checks passed

# ── Test Quality ──────────────────────────────────────────────────────────────
test_coverage_pct: 87               # coverage% for modified packages (null if non-code)
tests_passed: 47                    # total passing tests
tests_total: 47                     # total tests run
coverage_delta: +2                  # change from before task (+/- %)

# ── Cost & Efficiency ─────────────────────────────────────────────────────────
tokens_in: 2800                     # tokens consumed reading context
tokens_out: 1400                    # tokens produced in response
tokens_total: 4200                  # sum of tokens_in + tokens_out
tokens_total_all_attempts: 4200     # includes all retries (same if re_work_count = 0)
original_token_estimate: 3000       # from DELEGATE budget_context
cost_overrun_pct: 40                # ((actual - estimate) / estimate) * 100
duration_minutes: 22                # wall-clock from DELEGATE to HANDBACK
escalations_within_task: 0         # model escalations during task execution

# ── QE Assessment ─────────────────────────────────────────────────────────────
qe_model_assessment: haiku_suitable  # from qe_feedback block
qe_confidence: 0.88                  # confidence for similar tasks
qe_test_coverage_assessment: good    # excellent | good | acceptable | poor
qe_error_handling_assessment: defensive

# ── Signals for Model Engineer ─────────────────────────────────────────────────
task_complexity_signal: medium      # inferred from effort + re_work_count + score
model_appropriate: true             # true if qe_model_assessment is *_suitable
flag_for_model_engineer: false      # true if cost_overrun_pct > 50 or re_work_count >= 2
```

### Metrics Storage Location

```
artifacts/metrics/
  YYYY-MM-DD-{task_id}-metrics.yaml   # one file per task attempt
  YYYY-MM-DD-{task_id}-retry-1-metrics.yaml  # retry metrics (separate file)
  YYYY-MM-DD-{task_id}-retry-2-metrics.yaml
```

### Metrics Consumers

| Consumer | Metrics Used | Purpose |
|----------|-------------|---------|
| **Model Engineer** | `model_used`, `quality_score_validator`, `qe_model_assessment`, `qe_confidence`, `flag_for_model_engineer` | Optimize model routing; detect over/under-spending |
| **TokenAdvisor** | `tokens_total`, `tokens_total_all_attempts`, `cost_overrun_pct`, `duration_minutes` | Daily cost analysis; velocity tracking |
| **Orchestrator** | `re_work_count`, `final_decision`, `success_criteria_met_pct` | Identify patterns in task failure; improve future DELEGATEs |
| **Quality Engineer** | All fields | Calibrate quality thresholds; identify systemic issues |
| **Principal Engineer** | `escalated`, `escalation_target`, `flag_for_model_engineer`, `re_work_count` | Strategic decisions on agent capability and task routing |

### Metrics Emission Timing

| Event | Metrics Action |
|-------|---------------|
| DELEGATE created | Record `task_id`, `agent_type`, `model_used`, `effort_declared`, `original_token_estimate` |
| HANDBACK received | Record `tokens_in`, `tokens_out`, `duration_minutes`, `status`, `quality_score_agent_self` |
| Validation complete | Record all layer scores, `quality_score_validator`, `success_criteria_met_pct` |
| Decision engine output | Record `final_decision`, `re_work_count` update |
| QE feedback added | Record `qe_*` fields |
| Task accepted/escalated | Finalize record; set `flag_for_model_engineer` if needed |

---

## 6. Implementation Checklist

### What Can Be Automated

| Check | Automated By | Status |
|-------|-------------|--------|
| DELEGATE format validation (Layer 1) | `quality_validator.py` | ✅ Implemented |
| Task routing quality (Layer 2) | `quality_validator.py` | ✅ Implemented |
| HANDBACK format validation (Layer 3) | `quality_validator.py` | ✅ Implemented |
| `decide: proceed/rework/escalate` | `decision_engine.py` | ✅ Implemented |
| Secret detection in DELEGATE | `quality_validator.py` Layer 1 | ✅ Implemented |
| `task_id` format regex check | `quality_validator.py` Rule 1.2/1.3 | ✅ Implemented |
| Metrics emission hook | `quality_validator.py` (partial) | ✅ Partial — needs full schema |
| **Retry count cap (MAX_RETRIES=2)** | `orchestrator.py` task metadata | ❌ **Missing** |
| **retry_context block construction** | `orchestrator.py` re-DELEGATE builder | ❌ **Missing** |
| **task_id retry suffix convention** | `orchestrator.py` task ID generator | ❌ **Missing** |
| **Metrics canonical record** | New `metrics_writer.py` module | ❌ **Missing** |
| Deliverables existence check | `decision_engine.py` spot-check | ⚠️ Partial |
| Agent self-score vs. validator score reconciliation | `orchestrator.py` | ❌ **Missing** |

### What Requires Manual Review

| Review | Performed By | When |
|--------|-------------|------|
| Score 70–79 (gray zone) acceptance decision | Lead Engineer | After validator decision |
| Critical finding assessment | Principal Engineer | Immediately on trigger |
| Architecture adherence (Tier 3) | Principal Engineer | Security / cross-service tasks |
| Re-work cost overrun (>150%) | Principal Engineer + Model Engineer | Before re-retry |
| QE model suitability assessment | Quality Engineer | After every completed task |
| Flag resolution for Model Engineer | Model Engineer | Daily batch review |

### Role-Level Review Responsibilities

```
Engineer HANDBACK
  └─ Automated: Layer 1/2/3 validation
  └─ If score ≥80: Automated accept
  └─ If score 70-79: Lead Engineer review
  └─ If score <70 after 2 retries: Principal Engineer

Senior Engineer HANDBACK
  └─ Automated: Layer 1/2/3 validation
  └─ If score ≥80: Automated accept
  └─ If score <80: Lead Engineer review
  └─ If escalated: Principal Engineer

Lead Engineer HANDBACK
  └─ Automated: Layer 1/2/3 validation
  └─ If score ≥80: Automated accept
  └─ If score <80: Principal Engineer review

Principal Engineer / Security Engineer HANDBACK
  └─ Automated: Layer 1/2/3 validation
  └─ Manual review: Quality Engineer spot-check on critical tasks
  └─ Escalation: No further escalation path — treat as final authority
```

### Implementation Priority

#### Priority 1 — Close Critical Gaps (Week 1)

1. **Add retry state to task queue records**

   ```python
   # orchestration/agents/orchestrator.py
   # Add to task state when processing queue:
   task_state = {
       "retry_count": 0,
       "MAX_RETRIES": 2,
       "original_task_id": task_id,
       "total_tokens_all_attempts": 0,
       "original_estimate_tokens": delegate.get("budget_context", {}).get("estimated_tokens_needed", 0),
   }
   ```

2. **Enforce retry cap in post-HANDBACK handling**

   After `decision_engine` returns `action: rework`:
   ```python
   if task_state["retry_count"] >= task_state["MAX_RETRIES"]:
       escalate_to_principal_engineer(task, reason="max_retries_exceeded")
   else:
       task_state["retry_count"] += 1
       issue_rework_delegate(task, task_state)
   ```

3. **Add `retry_context` block builder** to produce correctly-formatted re-DELEGATE blocks.

#### Priority 2 — Metrics Canonical Record (Week 2)

4. **Create `orchestration/agents/metrics_writer.py`** — writes the canonical metrics
   YAML schema defined in Section 5 after each task completes.

5. **Update `orchestrator.py`** to use validator-computed score as authoritative, recording
   agent self-reported score as `quality_score_agent_self` only.

#### Priority 3 — Pre-Delegation Gate (Week 3)

6. **Add pre-DELEGATE validation step to Orchestrator workflow** (Section 1 checklist).
   This can be a lightweight `validate_delegate_preflight(delegate_block)` call in
   `orchestrator.py` before writing to `artifacts/queue/incoming/`.

7. **Update `orchestration/ORCHESTRATOR-CHECKLIST.md`** to include Group A/B/C pre-flight
   checks from Section 1.

---

## Quick Reference Card

### DELEGATE Checklist (30-second pre-send gate)

```
Before sending a DELEGATE, confirm:
  ✓ task_id is YYYY-MM-DD-kebab-slug and unique
  ✓ role, model, effort are consistent (see mismatch table)
  ✓ scope ≥15 words, action verb, named subject
  ✓ success_criteria are testable (can verify in 30s)
  ✓ plan has numbered, concrete steps incl. testing
  ✓ No secrets embedded
  ✓ "Would an agent ask a clarifying question?" → If YES, fix first
```

### HANDBACK Decision Matrix (15-second post-receive gate)

```
Score ≥90          → ✅ Accept immediately
Score 80-89        → ✅ Accept with notes
Score 70-79        → ⚠️  Lead Engineer review
Score 60-69        → 🔄 Re-work (auto, max 2 retries)
Score <60          → 🔄 Re-work (auto, max 2 retries) → Principal if still failing
Critical finding   → 🚨 Principal Engineer immediately
After 2 retries    → 🚨 Principal Engineer always
```

### Metrics to Capture (10 required fields)

```
task_id, agent_type, model_used, status, final_decision,
quality_score_validator, success_criteria_met_pct, tokens_total,
duration_minutes, re_work_count
```

---

## References

| Document | Purpose |
|----------|---------|
| `orchestration/QUALITY.md` | Agent-facing Tier 1/2/3 quality checklists |
| `orchestration/HANDOFF.md` | DELEGATE/HANDBACK YAML schema specification |
| `docs/quality-standards.md` | Human-readable quality standards and anti-patterns |
| `docs/quality-validation-rules.md` | Machine-enforced validation rule reference |
| `orchestration/agents/quality_validator.py` | Three-layer validation implementation |
| `orchestration/agents/decision_engine.py` | Post-execution proceed/rework/escalate decisions |
| `orchestration/ORCHESTRATOR-CHECKLIST.md` | Orchestrator daily workflow (extend with pre-delegation gate) |
