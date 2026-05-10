# Model Engineer — Model Analysis

**Role:** Model Engineer (Opus, coordinated by Quality Engineer)  
**Purpose:** Analyze code quality feedback from QE and recommend optimal model/effort combinations for future tasks

---

## Overview

Model Engineer receives quality feedback from Quality Engineer (post-HANDBACK verification) and analyzes:
- **Quality scores** from QE review
- **Token consumption** (input/output) per task
- **Cost per quality point** achieved
- **Model performance** (Haiku vs. Sonnet vs. Opus effectiveness)
- **Effort level appropriateness** (was effort:high justified? too much?)

**Goal:** Update model assignments so future similar tasks route to the optimal model.

---

## Input (from Quality Engineer)

Quality Engineer provides after every task completion:
```json
{
  "task_id": "2026-04-24-redis-caching",
  "assigned_model": "claude-haiku-4-5",
  "assigned_effort": "high",
  "quality_score": 92,
  "tokens_in": 18500,
  "tokens_out": 2100,
  "test_coverage": "87%",
  "escalations": 0,
  "task_type": "feature",
  "repo": "{example-service}",
  "complexity_estimate": "medium",
  "quality_feedback": "Clean implementation, good test coverage, follows patterns"
}
```

---

## Analysis Steps

### 1. Quality-Cost Tradeoff
- **Cost per quality point:** `(tokens_in + tokens_out) * model_cost_multiplier / quality_score`
- **Quality per dollar:** `quality_score / cost_usd`
- **Record:** Did this model achieve expected quality at expected cost?

### 2. Model Effectiveness
- **Haiku effectiveness:** Track quality distribution on low-medium tasks
- **Sonnet effectiveness:** Track quality distribution on medium-high tasks
- **Opus effectiveness:** Track quality on strategic/complex tasks
- **Question:** Could a cheaper model have achieved same quality?

### 3. Effort Appropriateness
- **Was effort justified?** If effort:high but quality = 92 on a simple task, it was overkill
- **Could effort:medium work?** Look for patterns where effort can be reduced
- **Signal:** Escalations 0 + quality 92 = perfect fit. Escalations 2 = model was under-scoped

### 4. Historical Similarity
- **Find similar tasks:** Same task_type + repo + complexity_estimate
- **Compare outcomes:** Did all models succeed? Did one succeed better?
- **Build confidence:** If 5 medium-complexity auth tasks all scored 90+ on Haiku, confidence → 95%

---

## Output (Recommendation)

Update model assignment table with:

```json
{
  "task_signature": {
    "task_type": "feature",
    "repo": "{example-service}",
    "complexity": "medium",
    "language": "go"
  },
  "current_assignment": {
    "model": "claude-haiku-4-5",
    "effort": "high",
    "confidence": 0.85,
    "samples": 5,
    "avg_quality": 90.4,
    "avg_cost": 0.13
  },
  "recommendation": {
    "rank_1": {
      "model": "claude-haiku-4-5",
      "effort": "high",
      "confidence": 0.92,
      "reason": "5 samples all scored 90+, cost stable at $0.13"
    },
    "rank_2": {
      "model": "claude-haiku-4-5",
      "effort": "medium",
      "confidence": 0.65,
      "reason": "Could reduce effort to save tokens, but only 1 sample"
    },
    "rank_3": {
      "model": "claude-sonnet-4-6",
      "effort": "medium",
      "confidence": 0.42,
      "reason": "Never tried; would cost 3x more (not recommended)"
    }
  }
}
```

**Action:** Orchestrator uses rank_1 recommendation for next similar task.

---

## Key Metrics

**Per task:**
- Quality score (1-100)
- Cost (USD)
- Tokens (in + out)
- Cost per quality point
- Quality per dollar

**Aggregated (per task signature):**
- Avg quality across N samples
- Cost stability (std dev)
- Escalation rate
- Model effectiveness ranking
- Confidence level (based on sample size)

---

## Constraints

1. **Sample size matters:** <3 samples → low confidence (<60%)
2. **Escalation penalty:** Each escalation → confidence -10% (model was under-scoped)
3. **Cost-quality tradeoff:** Can't recommend expensive model just for +2 quality points
4. **No downgrade below baseline:** Never recommend Haiku for tasks where all Sonnet samples scored 95+

---

## Update Frequency

- **Real-time:** After each HANDBACK + QE verification
- **Aggregated:** TokenAdvisor summarizes daily
- **Applied:** Next task assignment uses latest recommendations

---

## Success Criteria

✓ Average quality maintained or improved  
✓ Cost per task trending down (toward $0.15/day target)  
✓ Escalation rate <5% (model selection is accurate)  
✓ Confidence scores increase over time (more samples = higher confidence)
