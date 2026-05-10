# Model Engineer Automation — Per-Task Model Selection

**Role Summary:** Automated model selection engine. Analyzes task metadata, queries historical data, predicts quality/cost for each model tier, and recommends optimal assignment.

**Model:** claude-haiku-4-5 | **Effort:** medium | **Cost Tier:** 1x | **Token Multiplier:** ~1.5x (analysis + lookup)

---

## What This Skill DOES

- ✅ Receive task analysis (domain, complexity, scope, token estimate)
- ✅ Query historical metrics for similar tasks
- ✅ Predict quality per model tier (with confidence)
- ✅ Calculate cost-quality tradeoff
- ✅ Generate ranked recommendations (1st/2nd/3rd choice)
- ✅ Explain rationale for each recommendation
- ✅ Track prediction accuracy (did outcome match prediction?)
- ✅ Update model assignment table monthly
- ✅ Detect model capability shifts (new versions available)

---

## Automation Workflow

### Step 1: Orchestrator Requests Recommendation

```yaml
---
action: recommend_model
task_analysis:
  title: "Add Redis caching to {example-service}"
  domain: "backend/go"
  complexity: "medium"
  scope: "2 files, ~200 LOC"
  estimated_tokens: "15k-20k"
  skills_required: ["Go", "Redis", "testing"]
  critical: false
---
```

### Step 2: Model Engineer Performs Analysis

```
1. Classify task:
   Domain: backend/go
   Complexity: medium
   Risk: low (single service, no auth)
   Est. duration: <2 hours

2. Look up historical similar tasks:
   SELECT * FROM metrics 
   WHERE domain="backend/go" 
     AND complexity IN ["low", "medium"]
     AND tokens BETWEEN 12000 AND 25000
   
   Results (last 4 weeks):
   - database-index (Haiku high): 18.5K tokens, quality 92
   - http-client-retry (Haiku high): 16.2K tokens, quality 88
   - redis-ttl-cleanup (Sonnet med): 22.5K tokens, quality 94
   - config-validation (Haiku high): 14K tokens, quality 89

3. Predict quality for each model:
   Based on complexity="medium" and historical baseline:
   
   Haiku high-effort:
     - Historical avg quality: 90 (based on 3 similar tasks)
     - Historical std dev: 2.5
     - Predicted quality: 90 ± 3
     - Confidence: 92% (3 historical samples)
   
   Sonnet medium-effort:
     - Historical avg quality: 94 (based on 1 similar task)
     - Historical std dev: N/A (only 1 sample)
     - Predicted quality: 93 ± 4 (wide range, low confidence)
     - Confidence: 65% (only 1 historical sample)

4. Estimate tokens:
   Haiku: 18K ± 2K (from database-index, http-client tasks)
   Sonnet: 22K ± 2K (from redis-ttl task)

5. Calculate costs:
   Haiku (1x): 18K tokens × $0.00007/token = $1.26 task ÷ 60 min = $0.21/min ÷ 10 = $0.021 task
              (simplifying: ~$0.13 per task historically)
   Sonnet (3x): 22K tokens × $0.00007/token × 3 = $4.62 ÷ 60 min = $0.077/min ÷ 10 = $0.077 ÷ min
              (simplifying: ~$0.16 per task historically)

6. Calculate cost_per_quality:
   Haiku: $0.13 ÷ 90 = $0.00144 per quality point
   Sonnet: $0.16 ÷ 94 = $0.00170 per quality point

7. Rank recommendations:
   Rank 1: Haiku high-effort (lower cost, proven quality, high confidence)
   Rank 2: Sonnet medium-effort (higher quality, proven on similar task, lower confidence)
   Rank 3: (N/A — only 2 viable options for medium-complexity)

8. Generate recommendation report:
   See output format below.
```

### Step 3: Orchestrator Receives Recommendation

```yaml
---
action_response: model_recommendation
task_id: "2026-04-25-redis-caching"
recommendations:
  - rank: 1
    model: "claude-haiku-4-5"
    effort: "high"
    predicted_quality: 90
    predicted_tokens: 18000
    predicted_cost_usd: 0.13
    confidence: 92
    reasoning: |
      Similar backend/Go tasks (database-index, http-client-retry) 
      completed with Haiku high-effort at 88-92 quality, 16-18.5K tokens.
      This task has identical scope (medium complexity, single service).
      Expected outcome: 90 ± 3 quality, $0.13 cost.
    pros:
      - Lowest cost ($0.13 vs. $0.16 for Sonnet)
      - Proven track record on identical task type (3/3 success)
      - High confidence (92%, based on historical data)
    cons:
      - Slight quality dip vs. Sonnet (90 vs. 94, but still >85 floor)
      - May need escalation if Redis library underdocumented
  
  - rank: 2
    model: "claude-sonnet-4-6"
    effort: "medium"
    predicted_quality: 94
    predicted_tokens: 22000
    predicted_cost_usd: 0.16
    confidence: 65
    reasoning: |
      One similar Sonnet task (redis-ttl-cleanup) showed quality 94 
      with 22.5K tokens. Extrapolating to this task (slightly smaller scope) 
      suggests 93-94 quality, $0.16 cost.
    pros:
      - Higher quality (94 vs. 90)
      - Safer if Redis documentation sparse or edge cases arise
    cons:
      - 23% higher cost ($0.16 vs. $0.13)
      - Lower confidence (only 1 historical Sonnet sample on Redis)
      - Cost-per-quality worse (0.00170 vs. 0.00144)
  
  - rank: 3
    model: "N/A"
    reasoning: "Not recommended. Opus is 7.5x cost; overkill for this scope."

suggested_decision: "Allocate to Haiku high-effort (Rank 1). High confidence, proven track record."
---
```

### Step 4: Orchestrator Delegates with Recommended Model

```yaml
---
handoff_type: DELEGATE
task_id: 2026-04-25-redis-caching
role: Engineer
model: claude-haiku-4-5  # ← From Model Engineer recommendation
effort: high
scope: Add Redis caching to {example-service} (cache user memberships)
context:
  - File: lambda/query/main.go:45 (membership lookup)
  - Current: Cache miss, every query hits DynamoDB
  - Goal: Cache hit ratio >80%, latency <100ms
plan:
  1. Add Redis client initialization
  2. Implement cache getter with 1hr TTL
  3. Write tests for hit/miss scenarios
  4. Benchmark cache vs. no-cache
success_criteria:
  - "make verify" passes
  - Cache hit ratio >80% on benchmark
  - No performance regression on other queries
---
```

### Step 5: After Task Completion, Model Engineer Learns

```
Task completed by Engineer:
  - Model: Haiku high-effort
  - Tokens: 18,500 (predicted 18K ± 2K ✓)
  - Quality: 91 (predicted 90 ± 3 ✓)
  - Cost: $0.13 (predicted 0.13 ✓)
  
Model Engineer updates:
  - Predicted quality: 90
  - Actual quality: 91
  - Error: +1 point (0.1% error, within margin)
  - Confidence adjustment: 92% → 92% (unchanged, within range)
  
  - Predicted tokens: 18K
  - Actual tokens: 18.5K
  - Error: +500 tokens (2.8% error)
  - Confidence adjustment: 92% → 92% (still good)
  
  Historical update:
  - Add to "backend/go, medium complexity" cluster
  - New cluster baseline: 4 tasks, avg quality 90.75, avg tokens 17.6K
  - Confidence increasing (more samples)
```

---

## Model Assignment Table (Auto-Updated Monthly)

```
TASK TYPE | COMPLEXITY | CURRENT MODEL | RECOMMENDED | QUALITY | COST | CONFIDENCE | NOTES
────────────────────────────────────────────────────────────────────────────────────
auth (Go) | low | Haiku high | Haiku high | 88 | $0.11 | 95% | Proven
auth (Go) | medium | Haiku high | Haiku high | 90 | $0.13 | 92% | Good track record
auth (Go) | high | Sonnet med | Sonnet med | 94 | $0.16 | 88% | Solid performance
API (Go) | low | Haiku high | Haiku high | 89 | $0.12 | 93% | Proven
API (Go) | medium | Haiku high | Sonnet med* | 90 | $0.13 | 81% | Opportunity: test Sonnet
API (Go) | high | Sonnet med | Sonnet med | 92 | $0.15 | 87% | Good
Redis/Cache | low | Haiku high | Haiku high | 88 | $0.11 | 90% | Just established
Redis/Cache | medium | (new) | Haiku high | 91 | $0.13 | 92% | Predicted (task completed)
Frontend (TS) | low | Haiku high | Haiku high | 87 | $0.10 | 90% | Proven
Frontend (TS) | medium | Sonnet med | Haiku high* | 91 | $0.13 | 79% | Opportunity: downgrade to Haiku

* = Recommendation differs from current assignment; A/B test opportunity
```

---

## Monthly Confidence Calibration

**Procedure:**
1. Collect all completed tasks for the month
2. Compare predicted quality vs. actual quality for each
3. Calculate mean absolute error (MAE) per model
4. Adjust confidence scores if MAE > 5 points

**Example:**
```
Haiku predictions (10 tasks, month of April):
  Predicted: [90, 88, 92, 89, 91, 87, 93, 90, 89, 92]
  Actual:    [91, 87, 91, 90, 92, 88, 92, 89, 88, 93]
  Error:     [+1, -1, -1, +1, +1, +1, -1, -1, -1, +1]
  MAE: 0.9 points (very good)
  Confidence adjustment: 92% → 93% (slight increase)

Sonnet predictions (3 tasks):
  Predicted: [93, 94, 92]
  Actual:    [95, 92, 94]
  Error:     [+2, -2, +2]
  MAE: 2.0 points (acceptable)
  Confidence adjustment: 80% → 82% (slight increase, more data)
```

---

## New Model Evaluation Trigger

**When new model available (e.g., Haiku 4.6):**

1. Request 5 sample tasks of type "low-complexity coding"
2. Allocate to new Haiku 4.6
3. Compare quality vs. Haiku 4.5 baseline:
   - If quality ≥ baseline AND cost ≤ baseline → **Upgrade all**
   - If quality > but cost ↑ → **Run A/B test**
   - If quality < → **Keep old model**

**Decision criteria:**
```
Haiku 4.5 (baseline): quality 88, cost $0.11/task
Haiku 4.6 (new):      quality 90, cost $0.11/task (same cost tier)

Decision: ✅ UPGRADE to Haiku 4.6
  Quality improvement: +2 points (2.3% increase)
  Cost: same ($0.11)
  Cost per quality: $0.11/88 = $0.00125 → $0.11/90 = $0.00122 (2% improvement)
  
  Action: Update all Haiku assignments to 4.6
  Impact: Quality improvement across all low-complexity tasks
```

---

## Skill Validation

This skill is correct if it can:
1. Receive task analysis (domain, complexity, estimated tokens)
2. Query historical metrics for similar tasks
3. Predict quality per model tier (with confidence interval)
4. Estimate tokens and cost
5. Calculate cost-per-quality tradeoff
6. Generate ranked recommendations (1st/2nd/3rd)
7. Track prediction accuracy and adjust confidence
8. Update model assignment table monthly
9. Detect new model availability and trigger evaluation
10. Integrate with Orchestrator (receive task → recommend model → track outcome)
