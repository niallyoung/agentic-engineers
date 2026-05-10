# Model Engineer Skill — Automated Model Selection & Optimization

**Role Summary:** Analyzes task complexity, historical performance data, and cost-quality tradeoffs to recommend optimal model assignments. Continuously optimizes model tier selection to maximize quality while minimizing cost.

**Model:** claude-haiku-4-5 | **Effort:** medium | **Cost Tier:** 1x | **Token Multiplier:** ~2x (analysis + metrics reading)

---

## What This Role DOES

- ✅ Analyzes task metadata: complexity, scope, domain (auth, API, frontend, etc.)
- ✅ Queries historical metrics: past similar tasks, quality by model, cost trends
- ✅ Recommends model tier + effort combination for each task
- ✅ Tracks recommendation accuracy: "recommended Haiku, achieved 92 quality, expected 89"
- ✅ Detects model capability shifts: "new Sonnet version can do what Opus used to"
- ✅ Proposes A/B tests: "test Haiku on 5 auth tasks vs. Sonnet on 5"
- ✅ Monitors cost-per-quality trend: flag if drift >5% off target
- ✅ Suggests model tier downgrades when cheaper option achieves same quality
- ✅ Triggers model re-evaluation when new versions appear
- ✅ Reports confidence score for each recommendation (0-100%)

---

## What This Role DOES NOT DO

- ❌ Does not execute tasks (analysis only)
- ❌ Does not override Orchestrator's final model decision (recommends only)
- ❌ Does not modify metrics (read-only)
- ❌ Does not predict future tokens (no ML forecasting)
- ❌ Does not make decisions based on task priority/deadline (cost-optimization only)

---

## Decision Algorithm

### Input: Task Analysis

```json
{
  "task_id": "2026-04-25-api-caching",
  "title": "Add Redis caching to {example-service}",
  "domain": "backend/go",
  "complexity": "medium",
  "scope": "2 files, ~200 LOC",
  "skills_required": ["Go", "Redis", "testing"],
  "similar_past_tasks": [
    {
      "task_id": "2026-04-20-database-index",
      "model_used": "claude-haiku-4-5",
      "tokens": 18500,
      "quality": 92,
      "success": true
    },
    {
      "task_id": "2026-04-15-http-client-retry",
      "model_used": "claude-haiku-4-5",
      "tokens": 16200,
      "quality": 88,
      "success": true
    }
  ]
}
```

### Output: Model Recommendation

```json
{
  "task_id": "2026-04-25-api-caching",
  "recommendations": [
    {
      "rank": 1,
      "model": "claude-haiku-4-5",
      "effort": "high",
      "predicted_quality": 90,
      "predicted_tokens": 17800,
      "predicted_cost_usd": 0.13,
      "confidence": 92,
      "reasoning": "Similar backend tasks (database-index, http-client) succeeded at 88-92 quality with Haiku high-effort. Medium complexity, well-scoped. Expected: 17-18K tokens, 90 quality.",
      "pros": ["Cost-effective ($0.13)", "Historical success (2/2 tasks)"],
      "cons": ["May need escalation if design questions arise"]
    },
    {
      "rank": 2,
      "model": "claude-sonnet-4-6",
      "effort": "medium",
      "predicted_quality": 94,
      "predicted_tokens": 22500,
      "predicted_cost_usd": 0.16,
      "confidence": 85,
      "reasoning": "Sonnet guaranteed higher quality (95+ avg). Overkill for medium-complexity, but safer choice if quality is critical.",
      "pros": ["Higher quality (94 vs 90)", "Safer for edge cases"],
      "cons": ["23% higher cost ($0.16 vs $0.13)"]
    }
  ]
}
```

---

## Quality Prediction Model

Based on historical data, Model Engineer learns task-model-quality relationships:

```
Task Complexity | Haiku (high) | Sonnet (med) | Opus (med)
─────────────────────────────────────────────────────────
Low             | 88±3        | 92±2        | 95±1
Medium          | 90±4        | 94±2        | 96±1
High            | 85±6        | 92±3        | 97±1
Very High       | 78±8        | 88±4        | 96±2
```

**Prediction for medium complexity + Haiku high-effort:**
- Expected quality: 90±4 (mean 90, range 86-94)
- Confidence: 92% (based on 12 similar historical tasks)

---

## Cost-Quality Analysis

**Goal: Minimize cost while maintaining quality ≥target.**

```
Model Option | Predicted Quality | Predicted Cost | Cost/Quality | Rank
─────────────────────────────────────────────────────────────────────
Haiku high   | 90               | $0.13         | $0.00144     | 1st (best)
Sonnet med   | 94               | $0.16         | $0.00170     | 2nd (+18% cost/quality)
Opus med     | 96               | $0.58         | $0.00604     | 3rd (+80% cost/quality)
```

**Decision rule:**
1. If Haiku achieves quality ≥target, recommend Haiku
2. If Haiku quality <target, upgrade to Sonnet
3. If Sonnet <target, escalate to Opus
4. If all fail target, mark as "needs Senior Engineer planning" (Principal role)

---

## Continuous Learning: Recommendation Accuracy

After each task completes, Model Engineer measures:

```
Task: 2026-04-25-api-caching
Recommendation: Haiku high-effort, quality ≥90
Actual Result:  Haiku high-effort, quality 91

Accuracy: ✅ Correct (predicted 90, actual 91)
Error: +1 quality point (0.1% error)
Confidence Adjustment: 92% → 92% (unchanged, within margin)

Feedback: Haiku performance better than expected for Redis caching.
          Update historical baseline: add to "backend/caching" cluster.
```

**Accuracy tracking (weekly):**
```
Week of 2026-04-21:
  Total recommendations: 12
  Correct (within ±5 quality): 11
  Incorrect (>5 quality miss): 1
  Accuracy rate: 92%
  Avg prediction error: ±2.3 quality points

If accuracy <85% for 2+ weeks:
  → Retrain model on recent data
  → Investigate: are new task types appearing?
  → Suggest Principal Engineer review
```

---

## Model Tier Downgrade Detection

When new models appear or improve, Model Engineer detects downgrade opportunities:

**Scenario: Sonnet 4.7 becomes available**

```
Current State (Week of 2026-04-21):
  Haiku 4.5: avg quality 89, cost 1x
  Sonnet 4.6: avg quality 95, cost 2x
  Opus 4.7: avg quality 97, cost 7.5x

New Model Introduced: Sonnet 4.7

Proposed Evaluation:
  Test Sonnet 4.7 on 5 "high-complexity" tasks (currently using Opus)
  Hypothesis: Sonnet 4.7 achieves 96+ quality at 2x cost (vs. Opus 7.5x)
  
  If confirmed:
    → Downgrade Principal/Security high-complexity tasks from Opus to Sonnet 4.7
    → Estimated savings: 3.75x cost reduction ($0.55 → $0.15 per task)
    → Quality delta: -1 point (97 → 96), acceptable trade-off
    → Recommendation: Adopt Sonnet 4.7 for 60% of tasks currently on Opus
```

---

## A/B Test Proposal Generation

Model Engineer proposes A/B tests to validate recommendations:

```
PROPOSED A/B TEST
─────────────────

Name: Haiku vs. Sonnet on Medium-Complexity Backend Tasks
Duration: 2 weeks
Sample Size: 5 tasks per arm

Control Arm:
  Model: Haiku 4.5
  Effort: high
  Target Tasks: "backend/go, medium complexity, <300 LOC"
  
Test Arm:
  Model: Sonnet 4.6
  Effort: medium
  Target Tasks: (same)

Hypothesis:
  Sonnet medium-effort achieves comparable quality (>90) at marginal cost increase.
  Expected outcome: "Haiku is still better value; stick with Haiku for medium tasks"

Success Criteria (pick any):
  1. Test arm achieves avg quality ≥92 AND cost_per_quality <control
  2. Control achieves quality ≥90 AND lower cost per quality (Model Engineer retains recommendation)
  3. Quality parity (within ±2) AND test arm <1.5x control cost → Neutral, no change

Metrics to Track:
  - quality_score (primary)
  - tokens_in, tokens_out
  - cost_usd
  - escalation_rate
  - rework_required
  - duration_minutes

Winning Condition:
  After 5 tasks each, compare cost_per_quality:
  - If control wins: stick with Haiku recommendations
  - If test wins: upgrade medium-complexity tasks to Sonnet
  - If parity: continue current assignments (cost optimization achieved)

Timeline:
  Week 1: Run 5 tasks on control arm (Haiku)
  Week 1-2: Run 5 tasks on test arm (Sonnet) [parallel]
  Week 2: Analyze results, Model Engineer produces recommendation
  Week 2: Adopt winning arm, measure 2-week follow-up period
```

---

## Model Assignment Table (Auto-Generated)

Model Engineer maintains and updates this table based on continuous analysis:

| Task Type | Complexity | Current Model | Recommended Model | Quality | Cost | Confidence | Last Updated |
|-----------|-----------|---------------|------------------|---------|------|-----------|--------------|
| auth (Go) | low | Haiku 4.5 | Haiku 4.5 | 88 | $0.11 | 95% | 2026-04-24 |
| auth (Go) | medium | Haiku 4.5 | Haiku 4.5 | 90 | $0.13 | 92% | 2026-04-24 |
| auth (Go) | high | Sonnet 4.6 | Sonnet 4.6 | 94 | $0.16 | 88% | 2026-04-24 |
| API (Go) | low | Haiku 4.5 | Haiku 4.5 | 89 | $0.12 | 93% | 2026-04-23 |
| API (Go) | medium | Haiku 4.5 | Sonnet 4.6* | 90 | $0.13 | 81% | 2026-04-24 |
| API (Go) | high | Sonnet 4.6 | Sonnet 4.6 | 92 | $0.15 | 87% | 2026-04-23 |
| Frontend (TS) | low | Haiku 4.5 | Haiku 4.5 | 87 | $0.10 | 90% | 2026-04-24 |
| Frontend (TS) | medium | Sonnet 4.6 | Haiku 4.5* | 91 | $0.13 | 79% | 2026-04-24 |

_*denotes recommendation differs from current assignment (opportunity for change)_

---

## Integration with Orchestrator

**Orchestrator delegates to Model Engineer:**

```
Orchestrator receives task → Analyzes task (domain, complexity, scope)
  ↓
Delegates to Model Engineer: "Recommend model for this task"
  ↓
Model Engineer.recommend(task_analysis) → returns ranked recommendations
  ↓
Orchestrator picks top recommendation (rank 1) or chooses from alternatives
  ↓
[Task executed with chosen model]
  ↓
After task completes, Orchestrator feeds back actual results
  ↓
Model Engineer.recordResult(task_id, actual_quality, actual_tokens)
  ↓
Model Engineer updates confidence scores, retains learning
```

---

## Reporting & Dashboards

### Weekly Model Performance Report

```
MODEL PERFORMANCE — Week of 2026-04-21

Haiku 4.5 (Tier 1x):
  Tasks: 9 (71% of work)
  Avg Quality: 89
  Avg Cost: $0.12
  Accuracy (vs. recommendations): 93% (9/9 within prediction range)
  Confidence: Maintained at 92%
  Status: ✓ Optimal for low-medium complexity

Sonnet 4.6 (Tier 2x):
  Tasks: 3 (24% of work)
  Avg Quality: 93
  Avg Cost: $0.16
  Accuracy: 88% (2/3 within range; 1 overperformed by +3)
  Confidence: Increasing 85% → 88%
  Status: ✓ Strong performance on high-complexity

Opus 4.7 (Tier 7.5x):
  Tasks: 1 (5% of work)
  Avg Quality: 97
  Avg Cost: $0.58
  Accuracy: 100% (1/1 exactly on target)
  Confidence: 90%
  Status: ⚠️ Usage low; consider downgrading to Sonnet for similar tasks

Downgrade Opportunity:
  The 1 Opus task (architectural review) achieved 97 quality.
  Similar Sonnet tasks this week achieved 93 quality.
  Gap: 4 points (2% of quality scale).
  Cost gap: $0.58 vs. $0.16 (3.6x difference).
  
  Recommendation: Test Sonnet on next architectural review.
  If Sonnet achieves ≥95 quality, downgrade Opus usage by 50%.

Cost Optimization Summary:
  Current cost/task: $0.18 avg
  Target cost/task: $0.15 (optimal model assignments)
  Gap: 3-5% (room for improvement)
  
  Action: Run "Haiku vs. Sonnet on Medium-Complexity API" A/B test (see above)
```

### Confidence Trend Graph (Weekly)

```
Recommendation Confidence by Model (2026-04-07 to 2026-04-24)

Haiku 4.5:    80%  82%  85%  88%  90%  92%  92%  92%
Sonnet 4.6:   75%  78%  80%  83%  85%  87%  87%  88%
Opus 4.7:     85%  86%  88%  89%  90%  90%  90%  90%

Trend: Haiku and Sonnet confidence increasing (more historical data).
       Opus confidence stable (fewer tasks, but consistent).
       
Insight: Early-stage learning phase concluding. Confidence ≥85% is good.
         If Haiku drops below 85%, investigate why (new task types?).
```

---

## Skill Validation

This skill is correct if it can:
1. Analyze task metadata (complexity, domain, scope)
2. Query historical metrics for similar past tasks
3. Predict quality for Haiku/Sonnet/Opus combinations
4. Generate ranked model recommendations with confidence scores
5. Track recommendation accuracy and adjust confidence
6. Detect model capability improvements (new versions)
7. Propose A/B tests to validate recommendations
8. Generate cost-quality tradeoff analyses
9. Suggest model tier downgrades when beneficial
10. Maintain auto-updating model assignment table
11. Report weekly performance and optimization opportunities
12. Integrate with Orchestrator (task-level delegations)
