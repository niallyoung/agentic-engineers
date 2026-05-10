# Quality Engineer Quorum System — Distributed QA

**Role Summary:** Distributed quality gates using consensus voting. Multiple Quality Engineers independently review task output, vote pass/fail, escalate on disagreement. Enables scaling beyond single QE bottleneck while raising standards for critical tasks.

**Model:** claude-haiku-4-5 | **Effort:** medium | **Cost Tier:** 1x per QE | **Token Multiplier:** ~1.5x (review + voting)

---

## What This Skill DOES

- ✅ Distribute task reviews across multiple QEs (2-5 depending on criticality)
- ✅ Each QE independently runs Tier 1/2/3 checklist (no coordination)
- ✅ Collect votes: PASS, CONDITIONAL_PASS, NEEDS_WORK
- ✅ Determine consensus: unanimous/majority/deadlock
- ✅ Escalate to QE Lead on disagreement
- ✅ Track voting history (ground truth for QE accuracy)
- ✅ Measure inter-rater reliability (agreement %)
- ✅ Recommend voting weight adjustment based on accuracy
- ✅ Support risk-based routing (critical tasks → more voters)

---

## Voting Rules

### Vote Options (Per QE)

| Vote | Meaning | Action |
|------|---------|--------|
| **PASS** | All Tier 1 checks ✓, no concerns | Accept output |
| **CONDITIONAL_PASS** | Tier 1 ✓, minor issues noted (logging, docs) | Accept if issues logged as follow-up |
| **NEEDS_WORK** | Tier 1/2 fail, rework required | Reject, return to Engineer |

### Consensus Rules

```
Case 1: All QEs PASS
  → Result: ACCEPT (unanimous)
  → Confidence: 100%

Case 2: Majority PASS, minority CONDITIONAL
  → Result: ACCEPT (strong consensus)
  → Confidence: 90%
  → Log issues as technical debt

Case 3: Mixed PASS/CONDITIONAL/NEEDS_WORK
  → Consensus unclear, escalate to QE Lead
  → QE Lead breaks tie
  → Confidence: 70% (disputed)

Case 4: All QEs NEEDS_WORK
  → Result: REJECT (unanimous)
  → Confidence: 100%
  → Return to Engineer with feedback

Case 5: Split (3 QEs: 2 PASS, 1 NEEDS_WORK)
  → Majority rules: ACCEPT
  → Confidence: 66% (notable disagreement)
  → Log dissenting opinion + reviewer bias data
```

---

## Task Routing & QE Assignment

### Risk Tiers (Determine # of QEs)

| Risk | Complexity | Impact | # QEs | Purpose |
|------|-----------|--------|-------|---------|
| **Low** | Simple task (<100 LOC) | Single service | 1 | Speed (fast path) |
| **Medium** | Medium task (100-300 LOC) | Single service | 2 | Coverage |
| **High** | Complex (>300 LOC) | Multi-service/auth | 3 | Rigor |
| **Critical** | Cross-cutting (auth, payments, compliance) | System-wide | 5 | Consensus |

### QE Assignment Strategy

**Round-Robin with Specialization:**
```
QE Roster:
  - QE-Alice: Go expert, auth specialist
  - QE-Bob: TypeScript expert, API specialist
  - QE-Carol: Ops/infra specialist
  - QE-David: Security specialist
  - QE-Eve: Testing specialist

Task: "Add JWT audience validation in {example-service} (Go, auth)"
  Risk: High (auth, multi-service impact)
  Assigned QEs: Alice (auth expert), David (security), Carol (ops check)
  Confidence target: 85%+ (3-person consensus)
```

---

## Review Workflow

### Single QE Review (Low-Risk Tasks)

```
Engineer delivers HANDBACK
  ↓
QE-Alice (1 QE, low-risk):
  1. Run Tier 1 checklist (lint, test, coverage, in-scope, tests added, no hazards)
  2. Vote: PASS / CONDITIONAL / NEEDS_WORK
  3. Outcome: Immediate (no consensus needed)
  ↓
If PASS → Accept output
If NEEDS_WORK → Return to Engineer with feedback
```

### Quorum Review (Medium/High-Risk Tasks)

```
Engineer delivers HANDBACK
  ↓
Assign QEs: Alice, Bob, Carol (3 QEs for medium-complexity task)
  ↓
Run in Parallel:
  QE-Alice: Tier 1/2 checks → Vote
  QE-Bob: Tier 1/2 checks → Vote
  QE-Carol: Tier 1/2 checks → Vote
  ↓
Consensus Algorithm:
  If 3/3 PASS → ACCEPT (unanimous, 100% confidence)
  If 2/3 PASS, 1/3 CONDITIONAL → ACCEPT (strong, 90% confidence)
  If 2/3 PASS, 1/3 NEEDS_WORK → Escalate to QE Lead
  If 2/3 NEEDS_WORK → REJECT (return to Engineer)
  ↓
If accepted: Move to production
If rejected: Return to Engineer with consolidated feedback
```

---

## QE Lead Arbitration

When 2 or 3 QEs disagree (deadlock):

```
Scenario: 3 QEs vote: PASS, PASS, NEEDS_WORK (two-thirds agree but one dissents)

Option A (Majority Rules):
  Accept (2 PASS > 1 NEEDS_WORK)
  Confidence: 67% (minority concern noted)
  Action: Accept, but log dissenting review for pattern analysis

Option B (QE Lead Tiebreak):
  QE Lead (Senior QE, Sonnet model) re-reviews independently
  QE Lead votes: this becomes tie-breaker
  If QE Lead agrees with 2, accept (3-1)
  If QE Lead agrees with 1, reject (2-2, need Engineer revision)
  Confidence: 75-80% (expert arbitration)

Cost: Option A is fast (no re-review), Option B is expensive but higher confidence.
Use Option B for critical/security tasks, Option A for routine tasks.
```

---

## Feedback & Learning

### Inter-Rater Reliability (IRR)

Track QE agreement to measure consistency:

```json
{
  "period": "week_of_2026_04_21",
  "reviews": 10,
  "qe_pairs": [
    {
      "qes": ["Alice", "Bob"],
      "agreement": 0.90,
      "cases": [
        {"task": "task_1", "alice_vote": "PASS", "bob_vote": "PASS", "agree": true},
        {"task": "task_2", "alice_vote": "CONDITIONAL", "bob_vote": "PASS", "agree": false}
      ]
    },
    {
      "qes": ["Alice", "Carol"],
      "agreement": 0.85,
      "cases": [...]
    }
  ],
  "average_agreement": 0.88,
  "recommendation": "IRR 88% is good; no pattern concerns"
}
```

**Target:** IRR ≥85% (QEs are well-calibrated)
**Action if <80%:** Recalibrate Tier 1/2/3 definitions, hold QE sync meeting

### QE Accuracy Tracking

```json
{
  "qe": "Alice",
  "period": "week_of_2026_04_21",
  "reviews": 8,
  "outcomes": {
    "passed_tasks": {
      "total": 6,
      "later_issues_found": 1,  // Task passed QE but had bugs post-deploy
      "accuracy": 0.83
    },
    "rejected_tasks": {
      "total": 2,
      "rightfully_rejected": 2,  // Both had legit issues
      "false_positives": 0,
      "accuracy": 1.0
    }
  },
  "overall_accuracy": 0.89,
  "bias": "Alice is slightly more permissive (passes 75% of tasks); Alice.E Bob (50%)"
}
```

**Use for:**
- Adjust voting weight (more-accurate QEs weighted higher)
- Identify bias (permissive/strict QEs)
- Recommend specialization (Alice → auth expert)

### Voting Weight Adjustment

```
If QE has 95% accuracy over 20+ reviews:
  → Weight = 1.5x (their vote counts more in consensus)

If QE has 70% accuracy:
  → Weight = 0.8x (their vote counts less)

Consensus recalculated:
  Alice (weight 1.5, PASS) + Bob (weight 1.0, CONDITIONAL) + Carol (weight 0.8, CONDITIONAL)
  = 1.5 + 1.0 + 0.8 = 3.3 "effective votes"
  = 1.5 PASS + 1.8 CONDITIONAL
  Result: CONDITIONAL_PASS (weighted majority)
```

---

## Scaling Benefits

### Before Quorum (Single QE Bottleneck)

```
Engineer1 → QE-Alice HANDBACK review
Engineer2 → Waiting (QE-Alice busy)
Engineer3 → Waiting
Engineer4 → Waiting

Single QE is bottleneck. Throughput limited by 1 QE speed (~5 reviews/hour).
Max concurrent work: 5 engineers (1 per QE).
```

### After Quorum (Distributed QA)

```
Engineer1 → QE-Alice, Bob, Carol (3 QEs review in parallel)
Engineer2 → QE-David, Eve, Frank (3 different QEs)
Engineer3 → QE-George, Hannah (2 for simpler task)
Engineer4 → QE-Isaac (1 for lowest-risk task)

Work distributed across roster. QE utilization: ~80% (not bottlenecked).
Max concurrent: 20+ engineers (higher throughput).
Throughput: ~25 reviews/hour (5 × 5 QEs in parallel).
```

---

## Implementation Checklist

### Setup Phase

- [ ] Define QE Roster (names, models, specializations)
- [ ] Define Risk Tiers (what determines 1 vs. 3 QEs per task)
- [ ] Create Tier 1/2/3 consensus rules (majority? unanimous?)
- [ ] Create QE Lead role (arbitrate ties, calibrate standards)
- [ ] Metrics schema: voting records, agreement, accuracy

### Operational Phase

- [ ] Assign QEs to HANDBACK (based on task risk + specialization)
- [ ] Run QE reviews in parallel (concurrent calls to each QE)
- [ ] Collect votes (store in metrics)
- [ ] Apply consensus rule (auto-accept/reject or escalate)
- [ ] Track outcomes (did passed tasks have issues later?)
- [ ] Weekly IRR check (are QEs calibrated?)
- [ ] Monthly accuracy report (recommend weight adjustments)

### Optimization Phase

- [ ] Adjust voting weights based on accuracy
- [ ] Specialize QE assignments (best expert for task type)
- [ ] Reduce QE count for proven low-risk engineers
- [ ] Increase QE count for critical tasks
- [ ] A/B test: 2 QE vs. 3 QE on same-risk tasks

---

## Cost Model

### Single QE Path (Low-Risk)
```
Cost: 1 × (Haiku 1.5x effort) = ~1.5x Haiku cost
Time: 5 min review
Total: $0.015 per review
```

### Quorum Path (3 QEs, Medium-Risk)
```
Cost: 3 × (Haiku 1.5x effort, parallel) = ~4.5x Haiku cost
Time: 5 min review (parallel, not sequential)
Total: $0.045 per review
Trade-off: More cost, higher confidence (90%+ agreement)
```

### Quorum Path (5 QEs, Critical-Risk)
```
Cost: 5 × (Haiku 1.5x effort, parallel) = ~7.5x Haiku cost
Time: 5 min review (parallel)
Total: $0.075 per review
Trade-off: Highest cost, highest confidence (near-unanimous)
Value: Catches high-stakes bugs worth the cost
```

**Recommendation:**
- Use 1 QE for routine tasks (<100 LOC, single service)
- Use 3 QEs for medium (100-300 LOC, auth/multi-service)
- Use 5 QEs only for critical (compliance, payments, system-wide)

---

## Example: Auth Task Quorum Review

**Task:** Add JWT `aud` claim validation in {example-service}

**Risk Assessment:** High (auth, multi-service impact)
**Assigned QEs:** Alice (auth), David (security), Carol (ops) = 3 QEs

**Review Outcome:**
```
┌─────────────────────────────────────────────────────┐
│ QUORUM REVIEW RESULT                                │
├─────────────────────────────────────────────────────┤
│ Task ID: 2026-04-24-jwt-aud-validation              │
│ Risk: HIGH                                          │
│ QE Count: 3                                         │
├─────────────────────────────────────────────────────┤
│ QE-Alice (Auth Expert, weight=1.5):    PASS        │
│   ✓ Tests comprehensive (aud missing, wrong, valid) │
│   ✓ Handles both aud and client_id claims          │
│   ✓ Returns 401 (not 500)                          │
│   Note: Good grace period for clock skew            │
│                                                     │
│ QE-David (Security, weight=1.0):       PASS        │
│   ✓ No secrets in logs                             │
│   ✓ Empty COGNITO_CLIENT_ID returns 500 (safe)     │
│   ✓ Attack surface minimal                         │
│   Note: Consider rate limiting on 401 errors later │
│                                                     │
│ QE-Carol (Ops, weight=1.0):            CONDITIONAL │
│   ✓ Tier 1 checks pass                             │
│ ⚠ Tier 2: No docs on `aud` vs `client_id` distinction
│   Recommendation: Add inline comment explaining both claims
│                                                     │
├─────────────────────────────────────────────────────┤
│ CONSENSUS: 2.5 weighted PASS + 1.0 CONDITIONAL    │
│ Result: CONDITIONAL_PASS                           │
│ Confidence: 85%                                    │
│ Action: Accept, but log doc gap as tech debt      │
├─────────────────────────────────────────────────────┤
│ Inter-Rater Agreement: Alice-David 100%, Alice-Carol 90%
│ Average: 93% (very good)                           │
│ No escalation needed                               │
└─────────────────────────────────────────────────────┘
```

---

## Skill Validation

This skill is correct if it can:
1. Assign QEs based on task risk (1-5 QEs)
2. Run 3+ QE reviews in parallel
3. Collect votes (PASS/CONDITIONAL/NEEDS_WORK)
4. Apply consensus rules (majority/unanimous/deadlock)
5. Escalate to QE Lead on disagreement
6. Track inter-rater reliability (agreement %)
7. Measure QE accuracy (correctness over time)
8. Adjust voting weights based on accuracy
9. Recommend QE specialization (expert routing)
10. Report cost/benefit tradeoffs (1 vs. 3 vs. 5 QEs)
