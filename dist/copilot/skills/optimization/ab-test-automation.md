# A/B Test Automation — Continuous Experiment Coordination

**Role Summary:** Automated A/B test lifecycle management. Designs tests, allocates tasks, monitors progress, analyzes results, and recommends model/effort changes.

**Model:** claude-haiku-4-5 | **Effort:** high | **Cost Tier:** 1x | **Token Multiplier:** ~2x (analysis + coordination)

---

## What This Skill DOES

- ✅ Propose A/B tests based on Model Engineer recommendations
- ✅ Design test spec (hypothesis, control, test, success criteria)
- ✅ Allocate tasks to control/test arms (round-robin, stratified)
- ✅ Monitor test progress (sample size, power, early stopping)
- ✅ Analyze results (t-test, effect size, confidence)
- ✅ Recommend adoption/rejection of test arm
- ✅ Implement winning arm (update model routing)
- ✅ Archive test results and rationale
- ✅ Run multiple concurrent tests

---

## Automated Test Proposal Generation

### Monthly Proposal Review

**Trigger:** First Monday of month, 09:00 AM

```
Step 1: Identify test opportunities
  TokenAdvisor reports:
    • Cost trend: up 5% this month (investigate)
    • Low-quality task: form-validation at quality 72 (rework candidate)
    • Model underutilization: Sonnet at 54% (higher than target 35%)
  
  Model Engineer reports:
    • Haiku capable on medium-complexity? Confidence 81%
    • New Sonnet 4.7 available. Evaluate on 5 auth tasks.
    • Effort tuning: max-effort vs. medium on complex API tasks

Step 2: Score opportunities by impact
  Impact score = (cost_savings) × (confidence_that_win) × (volume_of_tasks)
  
  Opportunity 1: Haiku on medium-complexity (cost $0.03/task savings)
    Confidence in win: 81% (Model Engineer prediction)
    Monthly volume: 40 medium tasks
    Expected savings: $0.03 × 0.81 × 40 = $0.97/month
    Score: High (but low monthly savings)
  
  Opportunity 2: Sonnet 4.7 evaluation (cost neutral, quality improvement)
    Confidence in win: 60% (new model, unknown)
    Monthly volume: 10 auth tasks
    Expected quality gain: +2 points if win
    Score: Medium (learn opportunity)
  
  Opportunity 3: Effort tuning on complex API (cost $0.10/task savings)
    Confidence in win: 50% (unproven)
    Monthly volume: 5 complex API tasks
    Expected savings: $0.10 × 0.50 × 5 = $0.25/month
    Score: Medium (risky but high ROI if win)

Step 3: Prioritize tests to run this month
  Priority 1: Sonnet 4.7 eval (learn about new model, low cost)
  Priority 2: Haiku medium-complexity (higher confidence, steady progress)
  Priority 3: Effort tuning (only if resources available)

Step 4: Schedule tests
  Week 1: Set up Sonnet 4.7 eval (allocate 5 auth tasks)
  Week 2-3: Run Haiku medium-complexity test (allocate 20 medium tasks, 10 per arm)
  Week 4: Analyze and decide
```

### Auto-Generated Test Spec

```yaml
---
test_id: "test_sonnet-4.7-eval-auth_2026-05"
generated_by: "A/B Test Automation"
hypothesis: "Sonnet 4.7 achieves ≥94 quality on auth tasks at 2x cost (vs. Haiku 4.5 at 1x)"
duration_days: 14
sample_size_per_arm: 5
priority: "high"  # Learn about new model

control_arm:
  name: "Haiku 4.5 High (Current Baseline)"
  model: "claude-haiku-4-5"
  effort: "high"
  task_filter:
    domain: "auth"
    complexity: "medium"
    estimated_tokens: "15k-25k"
  historical_data:
    sample_size: 8
    avg_quality: 90
    avg_cost_usd: 0.13

test_arm:
  name: "Sonnet 4.7 Medium (New Model)"
  model: "claude-sonnet-4-7"
  effort: "medium"
  task_filter: (same as control)
  historical_data:
    sample_size: 0  # New model, no prior history
    estimated_quality: 93  # Extrapolated from 4.6
    estimated_cost_usd: 0.16

success_criteria:
  primary: "test_arm.quality >= 94"
  secondary: "test_arm.cost_per_quality < control * 1.2"  # Allow 20% premium for new model
  quality_floor: 85

metrics:
  track:
    - quality_score
    - tokens_in, tokens_out
    - cost_usd
    - escalation_rate
    - duration_minutes

allocation_strategy: "alternating"
randomization: "deterministic"

stopping_rules:
  early_stop_if_winner_clear: true
    power_threshold: 0.90
  early_stop_if_loser_fails: true
    failure_threshold: 0.85
  sample_size_insufficient: 3

decision_framework:
  if_test_wins: "Upgrade all auth tasks to Sonnet 4.7. Monitor for 2 weeks. Adjust if needed."
  if_control_wins: "Keep Haiku. Mark Sonnet 4.7 not viable for auth."
  if_inconclusive: "Extend test to n=10 per arm. Increase confidence threshold."
---
```

---

## Real-Time Test Monitoring

### Daily Progress Check

**Trigger:** 10:00 AM daily

```
Check each active test:
  test_haiku-vs-sonnet_auth_2026-05:
    Status: In-Flight
    Control arm: n=2 (target 5)
    Test arm: n=2 (target 5)
    Progress: ████░░░░░░░░░░░░░ (40% complete)
    Quality so far:
      Control: avg=89.5 (range 89-90)
      Test: avg=93 (range 92-94)
    Early stopping check:
      Power: 0.40 (need 0.90, continue)
      Loser failing? No, both >85
    Action: Continue test, on track
  
  test_effort-max-vs-med_complex-api_2026-05:
    Status: In-Flight
    Control arm: n=1
    Test arm: n=1
    Progress: 20% (slow start, API tasks are rare)
    Action: Continue, wait for more API tasks to arrive

Summary email:
  "2 active tests. Both on track. No early stops. 
   Haiku-vs-Sonnet: Strong early lead for Sonnet (93 vs 89).
   Continue monitoring."
```

### Power Analysis (When to Stop)

```
Statistical significance test (t-test):

After n=5 per arm for Haiku-vs-Sonnet:
  Control: [89, 90, 89, 91, 88] → mean=89.4, sd=1.1
  Test:    [93, 92, 94, 93, 92] → mean=92.8, sd=0.8
  
  t-statistic = (92.8 - 89.4) / sqrt((1.1²/5) + (0.8²/5))
              = 3.4 / sqrt(0.242 + 0.128)
              = 3.4 / 0.607
              = 5.6
  
  p-value < 0.001 (highly significant)
  Power = 0.99 (nearly certain winner)
  
Action: STOP TEST, declare Test arm (Sonnet 4.7) winner
```

---

## Automated Result Analysis & Decision

**Trigger:** When test reaches n=5 per arm OR max_duration exceeded

```
Test completed: haiku-vs-sonnet-auth-2026-05

RESULTS ANALYSIS
═══════════════════════════════════════════════════════

Control Arm (Haiku 4.5 high-effort):
  Quality: 89 ± 1.2 (n=5)
  Tokens: 18.2K ± 1.5K
  Cost: $0.133 ± $0.01
  Escalation: 1/5 (20%)
  
Test Arm (Sonnet 4.7 medium-effort):
  Quality: 93 ± 0.8 (n=5)
  Tokens: 19.5K ± 1.2K
  Cost: $0.158 ± $0.01
  Escalation: 0/5 (0%)

STATISTICAL TEST
═══════════════════════════════════════════════════════
t-statistic: 5.6
p-value: <0.001 (highly significant)
Effect size (Cohen's d): 3.5 (very large)
Power: 0.99 (nearly certain)

Difference: +4 quality points (Test arm better)
Cost premium: +$0.025 per task (18.8% higher)
Cost-per-quality:
  Control: $0.133 / 89 = $0.00149
  Test: $0.158 / 93 = $0.00170 (14% higher)

DECISION CRITERIA CHECK
═══════════════════════════════════════════════════════
Primary criterion: test_arm.quality >= 94
  ✓ Haiku 89, Sonnet 93 (Sonnet PASSES, but slightly below 94 target)
  
Secondary criterion: cost_per_quality < control * 1.2
  ✗ Sonnet 0.00170 vs control 0.00149 * 1.2 = 0.00179
  Sonnet is within threshold (0.00170 < 0.00179) → PASSES

Quality floor: 85
  ✓ Both arms above 85

RECOMMENDATION
═══════════════════════════════════════════════════════
Test arm WINS (Sonnet 4.7)
  • Quality: +4 points (89 → 93)
  • Cost premium: 18.8% (acceptable for quality gain)
  • Zero escalations (very good)
  • High confidence (p<0.001, large effect size)

ACTION: Upgrade auth tasks to Sonnet 4.7
  Expected impact:
    • Monthly tasks: ~40 auth (est. 20 medium-complexity)
    • Quality improvement: +4 × 20 = +80 quality points/month
    • Cost increase: $0.025 × 20 = $0.50/month
    • ROI: Quality gain at small cost premium (acceptable)
  
  Monitoring period: 2 weeks (verify sustained quality)
  Rollback trigger: If quality drops below 92 for 3+ days

ARCHIVE
═══════════════════════════════════════════════════════
Test report saved to: ~/.claude/reports/tests/haiku-vs-sonnet-auth-2026-05.json
Model assignment table updated:
  auth (Go, medium) → Sonnet 4.7 medium-effort (was Haiku 4.5 high)
Confidence for Sonnet: 98% (strong empirical data)

NEXT TEST IN QUEUE
═══════════════════════════════════════════════════════
Priority 2: Haiku medium-complexity test (starting next week)
```

---

## Test Rollback Procedure

**If test arm fails during monitoring period (after implementation):**

```
Monitoring period: 2026-05-08 to 2026-05-22 (2 weeks post-decision)

2026-05-10 (3 days after decision):
  Auth tasks assigned to Sonnet 4.7
  Quality: 94, 93, 95 (good)
  Escalations: 0
  Cost: $0.16/task
  Status: ✓ OK

2026-05-11:
  Quality: 91, 92, 90 (slight dip)
  Escalations: 1 task
  Cost: $0.17/task (slight increase)
  Status: ⚠️ Watch

2026-05-12:
  Quality: 89, 88, 87 (below 92 threshold)
  Escalations: 2 tasks
  Cost: $0.18/task (higher)
  Status: ✗ ROLLBACK TRIGGERED
  
Action: Revert auth tasks to Haiku 4.5
  Reason: Quality degradation (92 → 88)
  Cause: TBD (investigate)
  Monitoring: Watch for patterns
  
Next step: Investigate why Sonnet 4.7 underperformed
  • New model instability?
  • Task difficulty shift?
  • Model regression?
  
Recommendation: Re-run test after 2 weeks (new model release?)
```

---

## Test Archive & Metadata

**Stored in:** `~/.claude/reports/tests/`

```json
{
  "test_id": "test_haiku-vs-sonnet-auth-2026-05",
  "status": "completed",
  "decision": "test_arm_wins",
  "started": "2026-04-29T09:00:00Z",
  "completed": "2026-05-06T18:00:00Z",
  "duration_days": 7,
  
  "control_arm": {
    "model": "claude-haiku-4-5",
    "effort": "high",
    "quality_mean": 89,
    "quality_sd": 1.2,
    "cost_mean": 0.133,
    "cost_sd": 0.01,
    "n": 5
  },
  
  "test_arm": {
    "model": "claude-sonnet-4-7",
    "effort": "medium",
    "quality_mean": 93,
    "quality_sd": 0.8,
    "cost_mean": 0.158,
    "cost_sd": 0.01,
    "n": 5
  },
  
  "analysis": {
    "t_statistic": 5.6,
    "p_value": 0.0001,
    "effect_size_cohens_d": 3.5,
    "power": 0.99,
    "quality_diff": 4,
    "cost_premium_pct": 18.8
  },
  
  "recommendation": "Upgrade auth (medium-complexity) to Sonnet 4.7",
  "implemented": "2026-05-08T09:00:00Z",
  "monitoring_period": "2026-05-08 to 2026-05-22",
  "rollback_triggered": false,
  
  "impact": {
    "quality_improvement": 4,
    "monthly_tasks_affected": 20,
    "cost_premium_per_month": 0.50,
    "quality_improvement_per_month": 80
  }
}
```

---

## Skill Validation

This skill is correct if it can:
1. Propose A/B tests from Model Engineer recommendations
2. Generate test specs with hypothesis, arms, success criteria
3. Allocate tasks to control/test (round-robin, stratified)
4. Monitor test progress (sample size, power, early stopping)
5. Perform t-tests and calculate effect size
6. Analyze cost-quality tradeoffs
7. Generate winning/losing arm decision
8. Recommend adoption/rejection with rationale
9. Implement winning arm (update routing table)
10. Archive results and rationale
11. Manage rollback if test arm fails
12. Support concurrent tests (isolation)
