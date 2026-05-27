# Model Engineer — Model Recommendation

**Role:** Model Engineer (Sonnet 4.5, coordinated by Quality Engineer)  
**Purpose:** Find cheapest model + effort + thinking combo that meets quality gate

---

## Overview

Model Recommendation systematically tries cheaper model/effort/thinking combinations, working down the progression until quality fails. Then backs up to last passing combo.

**Input:** Task type, current model/effort/thinking, historical quality samples  
**Output:** Cheapest model + effort + thinking that passes quality gate

**Goal:** Always use cheapest viable combination. Quality gate: best_quality - 5 points.

---

## Model Progression (Hierarchy)

**Fixed progression for cost optimization:**
```
1. Haiku 4.5         ($0.03/task)  ← Always try first
2. Sonnet 4.5        ($0.09/task)  ← If Haiku fails quality gate
3. Sonnet 4.6        ($0.09/task)  ← Same cost as 4.5, try if 4.5 insufficient
4. Opus 4.6          ($0.15/task)  ← If Sonnet fails
5. Opus 4.7          ($0.15/task)  ← Same cost as 4.6, last resort
```

**Effort levels (combined with models):**
```
Low     → minimal compute (rare)
Medium  → balanced (try first with cheaper models)
High    → standard (current baseline)
Max     → full power (only if others fail)
```

**Thinking:**
```
No      → standard inference (try first, cheaper)
Yes     → extended thinking (try if quality too low)
```

**Combination strategy:** For each model in progression, try:
```
Model X, Effort Medium, Thinking No    ← Cheapest combo
Model X, Effort High,   Thinking No    ← Standard
Model X, Effort Max,    Thinking Yes   ← Full power
```

Then move to next model in progression.

---

## Optimization Strategy (Cost-First, Always)

**PRIMARY METRIC: Cost/Token Burn. Non-negotiable.**

**Decision Rule:**
```
IF cheaper_model_quality >= acceptable_threshold:
  ALWAYS recommend cheaper_model
ELSE:
  Try next cheaper option
```

**Quality threshold:** best_quality - 5 points (acceptable quality gap)
- If Opus 4.7 quality = 95 pts, acceptable min = 90 pts
- Haiku 4.5 quality = 91 pts → acceptable, pick Haiku
- Haiku quality = 88 pts → NOT acceptable, try Sonnet

**Result:** Always use the cheapest model that passes quality gate. No exceptions.

**Starting approach (where to test first):**

1. **Effort & Thinking variations** (10-20% cost impact)
   - Cheapest lever: disable thinking, reduce effort
   - Test first because cost-effective experiments

2. **Model/version changes** (50-100% cost impact)
   - Downgrade to Haiku if quality acceptable
   - Try Sonnet 4.5 instead of 4.6 (same cost, proven)
   - Downgrade Opus 4.6 → Sonnet if quality acceptable

3. **Task structure** (30% cost impact, if needed)
   - Pre-write plans, batch tasks, split complexity
   - Only if cheaper models can't meet quality gate

**Base Model Assignments (LOCKED):**
```
Haiku 4.5 (Orchestrator, Engineer)
Sonnet 4.5 (Quality, Senior, Model Engineer)
Sonnet 4.6 (Lead)
Opus 4.6 (Principal)
Opus 4.7 (Security)
```

**Real examples:**
- Senior Engineer assigned Sonnet 4.5. If Haiku 4.5 + thinking meets quality gate → downgrade to Haiku
- Lead Engineer assigned Sonnet 4.6. If Sonnet 4.5 achieves same quality → downgrade to 4.5
- Quality Engineer assigned Sonnet 4.5. If Haiku can do code review → downgrade to Haiku
- Principal Engineer assigned Opus 4.6. If Sonnet 4.6 + thinking=yes meets quality gate → downgrade to Sonnet

---

## Recommendation Algorithm

### Step 1: Walk Down Progression (Cheapest First)

For each task type with sufficient data (n ≥ 5 samples):

```
Current: Senior Engineer, Sonnet 4.5, effort=high, thinking=yes

Try in order (stop when quality fails):
  
  MODEL 1: Haiku 4.5 ($0.03)
    ├─ Haiku 4.5, effort=medium, thinking=no    (cheapest combo)
    ├─ Haiku 4.5, effort=high, thinking=no      (if above fails)
    └─ Haiku 4.5, effort=max, thinking=yes      (if above fails)
  
  MODEL 2: Sonnet 4.5 ($0.09) — only if Haiku fails quality gate
    ├─ Sonnet 4.5, effort=medium, thinking=no
    ├─ Sonnet 4.5, effort=high, thinking=no
    └─ Sonnet 4.5, effort=max, thinking=yes
  
  MODEL 3: Sonnet 4.6 ($0.09) — same cost as 4.5, try if 4.5 insufficient
    ├─ Sonnet 4.6, effort=medium, thinking=no
    ├─ Sonnet 4.6, effort=high, thinking=no
    └─ Sonnet 4.6, effort=max, thinking=yes
  
  MODEL 4: Opus 4.6 ($0.15) — only if Sonnet fails
  MODEL 5: Opus 4.7 ($0.15) — last resort
```

**Progression rule:** Only move to next model if current model + all effort/thinking combos fail quality gate.

### Step 2: Test Each Combo (Walk Progression)

For each combo in progression order:

```
min_quality = best_quality - 5 points

Test: Haiku 4.5, effort=medium, thinking=no
  IF avg_quality >= min_quality:
    ✅ PASS → Recommend this (cheapest viable) → DONE
  ELSE:
    ❌ FAIL → Try next combo
      
Test: Haiku 4.5, effort=high, thinking=no
  IF passes:
    ✅ Recommend → DONE
  ELSE:
    ❌ Try next
      
Test: Haiku 4.5, effort=max, thinking=yes
  IF passes:
    ✅ Recommend → DONE
  ELSE:
    ❌ All Haiku combos failed → Move to Sonnet 4.5
```

### Step 3: Output Single Recommendation

Once any combo passes quality gate:

```
Recommend:
  - Model: [cheapest that passed]
  - Effort: [level tested]
  - Thinking: [yes/no]
  - Quality: [avg_quality achieved]
  - Cost: [$/task]
  - Confidence: [based on sample_size]
```

**Stop immediately** when quality gate passes. Don't test other models.

**Examples:**
- Best quality ever = 95 pts, min acceptable = 90 pts
  - Test: Haiku 4.5, effort=medium, thinking=no → quality = 91 pts ✅ PASS
  - Recommend Haiku with effort=medium, thinking=no. Done.
  - Don't test Haiku high/max or any Sonnet (Haiku passed)
  
- Haiku all combos fail (all < 90 pts)
  - Haiku medium/no = 89 pts ❌
  - Haiku high/no = 87 pts ❌
  - Haiku max/yes = 88 pts ❌
  - Move to Sonnet 4.5
  - Test: Sonnet 4.5, medium/no → quality = 92 pts ✅ PASS
  - Recommend Sonnet 4.5 with effort=medium, thinking=no

**Result:** Always recommend the FIRST (cheapest) combo that passes quality gate.

---

## Recommendation Record

```json
{
  "task_signature": {
    "task_type": "feature",
    "repo": "{example-service}",
    "complexity": "medium",
    "language": "go"
  },
  "recommendation": {
    "rank_1": {
      "model": "claude-haiku-4.5",
      "effort": "high",
      "thinking": "disabled",
      "confidence": 0.92,
      "reason": "5 samples, avg quality 90.4, cost $0.13. Haiku has proven track record on medium-complexity Go.",
      "samples": 5,
      "avg_quality": 90.4,
      "cost_usd": 0.13,
      "escalation_rate": 0.0
    },
    "rank_2": {
      "model": "claude-haiku-4.5",
      "effort": "medium",
      "thinking": "disabled",
      "confidence": 0.65,
      "reason": "Unproven, but could save tokens. Only 1 sample. Recommend testing.",
      "samples": 1,
      "avg_quality": 89.0,
      "cost_usd": 0.10,
      "escalation_rate": 0.0
    },
    "rank_3": {
      "model": "claude-sonnet-4.6",
      "effort": "medium",
      "thinking": "disabled",
      "confidence": 0.42,
      "reason": "Higher cost ($0.18 vs $0.13). Could try A/B test if quality gap matters.",
      "samples": 2,
      "avg_quality": 93.5,
      "cost_usd": 0.18,
      "escalation_rate": 0.0
    }
  },
  "decision_context": {
    "current_assignment": {
      "model": "claude-haiku-4.5",
      "effort": "high",
      "thinking": "disabled"
    },
    "recommendation_type": "stable",
    "suggested_action": "Maintain rank_1. Consider A/B test for rank_2 if cost target pressures arise.",
    "next_review_trigger": "After 3 more medium-complexity Go tasks OR when cost target changes"
  }
}
```

---

## Recommendation Types

**Stable:** Same model recommended with high confidence  
→ Use immediately, no change needed

**Upgrade:** Better model recommended with comparable or lower cost  
→ Use immediately, potentially improved quality at same cost

**Cost Optimization:** Lower cost model recommended with acceptable quality delta  
→ Use immediately if cost target active; quality maintains >baseline

**Exploratory:** New model/effort untested but promising  
→ Run A/B test (allocate 20% of tasks to rank_2) before committing

**Unclear:** No consensus (all candidates low confidence)  
→ Continue collecting data, or trigger on-demand A/B test

---

## Key Decision Rules

### Never Recommend If:
- Sample size <3 (insufficient confidence)
- Avg quality < (current avg - 5 points) (quality regression)
- Cost > (current cost + $0.05/task) (too expensive relative to current)
- Escalation rate > 10% on recommended model (too many errors)

### Can Recommend If:
- Sample size ≥3 (confidence ≥ 0.70)
- Avg quality ≥ (current avg - 2 points) (acceptable for cost savings)
- Escalation rate ≤5% (model is reliable)

### Must A/B Test If:
- Quality improvement >5 points but cost ↑20% (explore value tradeoff)
- Cost savings >15% but quality delta uncertain (explore cost tradeoff)
- New model version available (5-task eval required)

---

## Integration with Orchestrator

Orchestrator receives recommendation JSON and:

1. **Stable/Upgrade:** Use rank_1 immediately for next matching task
2. **Cost Optimization:** Use rank_1 if cost target active
3. **Exploratory:** Propose A/B test to user
4. **Unclear:** Continue routing per current assignment, request more data

---

## Success Criteria

✓ Recommendations provided within 5 seconds of analysis  
✓ Confidence scores reflect actual prediction accuracy (calibrated monthly)  
✓ Rank_1 recommendations improve quality or reduce cost >95% of the time  
✓ No recommendation surprises (all reasoning transparent)  
✓ New model versions evaluated within 1 week of release
