# Model Engineer — Cost-Quality Tradeoff Analysis

**Role:** Model Engineer (Opus, coordinated by Quality Engineer)  
**Purpose:** Analyze whether cost savings justify quality degradation (or vice versa) to guide model selection decisions

---

## Overview

Cost-Quality Tradeoff evaluates whether switching models makes business sense by comparing the value of quality improvements against the cost of achieving them.

**Input:** Two model/effort options with quality scores, token counts, and cost estimates  
**Output:** Tradeoff analysis with recommendation on whether upgrade/downgrade is justified

**Goal:** Make principled decisions about model selection that account for both cost and quality impact.

---

## Tradeoff Framework

### Cost-Per-Quality-Point

```
cost_per_point = (cost_usd * 1000) / quality_score

Lower is better (more quality per dollar spent).
```

**Example:**
- Haiku: $0.13 cost, quality 90 → cost_per_point = $1.44/point
- Sonnet: $0.18 cost, quality 93 → cost_per_point = $1.94/point
- **Haiku is better value** (30% more efficient)

### Quality-Per-Dollar

```
quality_per_dollar = quality_score / cost_usd

Higher is better (more quality for money spent).

Example:
- Haiku: 90 / $0.13 = 692 points/$
- Sonnet: 93 / $0.18 = 517 points/$
```

### Cost Impact Per Point

```
cost_increase_per_point = (cost_new - cost_old) / (quality_new - quality_old)

If negative: cost decreased while quality increased (always upgrade)
If 0-0.01: quality improvement very cheap (almost always upgrade)
If 0.01-0.05: quality improvement moderately priced (consider upgrade)
If >0.05: quality improvement expensive (usually skip unless critical)
```

---

## Decision Matrix

### Upgrade Decision

**Always upgrade if:**
- Quality ≥ (current + 5 points) AND cost ≤ current
- Quality ≥ (current + 2 points) AND cost < current - $0.05/task
- Escalation rate decreases >20% (fewer errors = higher effective quality)

**Consider upgrading if:**
- Quality ≥ (current + 3 points) AND cost < current + $0.02/task
- Quality ≥ (current + 5 points) AND cost < current + $0.05/task

**Rarely upgrade if:**
- Quality increase <3 points (diminishing returns)
- Cost increase >15% (too expensive relative to gain)

### Downgrade Decision

**Always downgrade if:**
- Quality ≥ (current - 2 points) AND cost < current - $0.05/task
- Cost savings >20% AND escalation rate unchanged or improved

**Consider downgrading if:**
- Quality ≥ (current - 3 points) AND cost savings 10-20%
- Escalation rate acceptable (<5%)

**Rarely downgrade if:**
- Quality decreases >5 points (too risky)
- Escalation rate increases >3% (error rate concerns)

---

## Analysis Record

```json
{
  "task_signature": {
    "task_type": "feature",
    "repo": "{service-name}",
    "complexity": "medium"
  },
  "current_model": {
    "model": "claude-haiku-4-5",
    "effort": "high",
    "avg_quality": 90,
    "avg_cost": 0.13,
    "cost_per_quality_point": 1.44,
    "escalation_rate": 0.0,
    "samples": 5
  },
  "candidate_model": {
    "model": "claude-sonnet-4-6",
    "effort": "high",
    "avg_quality": 93,
    "avg_cost": 0.18,
    "cost_per_quality_point": 1.94,
    "escalation_rate": 0.0,
    "samples": 2
  },
  "tradeoff_analysis": {
    "quality_delta": 3,
    "quality_delta_percent": 3.3,
    "cost_delta": 0.05,
    "cost_delta_percent": 38.5,
    "cost_per_point_delta": 0.5,
    "cost_increase_per_quality_point": 0.0167,
    "quality_per_dollar": {
      "current": 692,
      "candidate": 517,
      "delta": -175
    },
    "recommendation": "skip_upgrade",
    "reasoning": "3-point quality improvement costs $0.0167/point. Haiku is 34% more cost-efficient. Only upgrade if quality becomes critical business requirement.",
    "decision": "maintain_current",
    "confidence": 0.92
  },
  "scenario_analysis": {
    "if_quality_importance_high": "Upgrade to Sonnet if quality >95 is required; cost increase acceptable for critical tasks",
    "if_cost_target_active": "Maintain Haiku; cost savings ($0.05) contribute to $0.15/day target",
    "if_error_rate_critical": "Monitor escalation rate; if Sonnet drops errors >20%, may justify cost increase",
    "trigger_upgrade": "If same task type returns quality 85-88 on Haiku consistently; indicates complexity trending up"
  }
}
```

---

## Special Cases

### Effort-Level Tradeoff

Changing effort without changing model:

```json
{
  "current": "high_effort",
  "candidate": "medium_effort",
  "quality_impact": -2,
  "token_impact": -4000,
  "cost_impact": -$0.04,
  "decision": "consider_downgrade",
  "reasoning": "Save $0.04 at cost of 2-point quality. Good fit for low-risk tasks."
}
```

### Thinking Mode Tradeoff

Enabling/disabling extended thinking:

```json
{
  "current": "thinking_disabled",
  "candidate": "thinking_enabled",
  "quality_impact": +5,
  "token_impact": +8000,
  "cost_impact": +$0.08,
  "decision": "consider_for_critical",
  "reasoning": "5-point quality gain costs 23% more. Reserve for complex/critical tasks."
}
```

---

## Cost Target Alignment

**Year 1 target: $0.15/day**

When cost target is active:

1. **Evaluate all downgrades** that maintain quality ≥ baseline - 2 points
2. **Prioritize cost savings** over marginal quality improvements
3. **Run A/B tests** for borderline decisions (quality ≥ current - 3 points)
4. **Fast-track promising low-cost options** to move toward target

---

## Measurement & Calibration

Track prediction accuracy monthly:

```
For every "upgrade recommended" decision:
  - Did quality actually improve by ≥ predicted amount? (Y/N)
  - Did cost increase ≤ predicted amount? (Y/N)
  - Overall recommendation accuracy: (correct / total) * 100%
```

If accuracy drops below 80%, review:
- Historical data for outliers
- New task types not previously encountered
- Model behavior changes (new releases)
- Token cost assumptions

---

## Constraints & Guardrails

1. **Never recommend downgrade if escalations increase** (even small quality loss + higher error rate = net negative)
2. **Never skip quality analysis for cost** — 2-point quality gap on 100 tasks = 200 points lost = significant impact
3. **Review any recommendation >$0.10 cost difference** manually before auto-apply
4. **Document assumption changes** — if cost model updates, reanalyze all pending recommendations

---

## Integration with Decision Tree

Model Engineer uses this analysis to:
1. **Filter candidates** (quality within acceptable range)
2. **Rank by efficiency** (cost-per-point)
3. **Justify recommendations** (reasoning from this analysis)
4. **Guide A/B tests** (borderline cases go to testing)
