# Model Engineer — Model Comparison

**Role:** Model Engineer (Opus, coordinated by Quality Engineer)  
**Purpose:** Compare model effectiveness across historical data to identify patterns in when each model excels or struggles

---

## Overview

Model Comparison analyzes how different models perform on similar tasks to identify task characteristics that favor particular models.

**Input:** Historical metrics for tasks completed with different models, task signatures, complexity levels  
**Output:** Comparison matrix showing model strengths/weaknesses by task type and complexity

**Goal:** Build institutional knowledge about which model fits which task type, enabling better future routing.

---

## Comparison Dimensions

### By Task Type

```json
{
  "feature": {
    "haiku_avg_quality": 89.2,
    "sonnet_avg_quality": 92.1,
    "opus_avg_quality": 94.5,
    "quality_delta_h_to_s": 2.9,
    "quality_delta_s_to_o": 2.4,
    "haiku_cost": 0.13,
    "sonnet_cost": 0.18,
    "opus_cost": 0.65,
    "cost_per_point_h": 1.46,
    "cost_per_point_s": 1.95,
    "cost_per_point_o": 6.88,
    "recommendation": "Use Haiku for well-scoped features; consider Sonnet if scope unclear"
  },
  "refactor": {
    "haiku_avg_quality": 85.4,
    "sonnet_avg_quality": 90.6,
    "opus_avg_quality": 92.1,
    "quality_delta_h_to_s": 5.2,
    "quality_delta_s_to_o": 1.5,
    "recommendation": "Sonnet preferred; quality gap vs Haiku too large (5+ points)"
  },
  "bug_fix": {
    "haiku_avg_quality": 91.2,
    "sonnet_avg_quality": 91.8,
    "recommendation": "Haiku sufficient; Sonnet adds minimal value"
  }
}
```

### By Complexity

```json
{
  "low": {
    "task_count": 24,
    "haiku_quality": 92.3,
    "haiku_escalations": 0,
    "sonnet_quality": 93.1,
    "sonnet_escalations": 0,
    "recommendation": "Use Haiku exclusively; saves cost with no quality loss"
  },
  "medium": {
    "task_count": 18,
    "haiku_quality": 88.9,
    "haiku_escalations": 1,
    "sonnet_quality": 92.4,
    "sonnet_escalations": 0,
    "quality_gap": 3.5,
    "cost_difference": 0.05,
    "recommendation": "Haiku acceptable; Sonnet provides insurance against escalations"
  },
  "high": {
    "task_count": 8,
    "haiku_quality": 82.1,
    "haiku_escalations": 3,
    "sonnet_quality": 91.2,
    "sonnet_escalations": 0,
    "quality_gap": 9.1,
    "recommendation": "Require Sonnet; Haiku too risky on high-complexity"
  }
}
```

### By Repository

```json
{
  "{example-service}": {
    "task_count": 12,
    "models_tried": ["haiku"],
    "haiku_quality": 90.4,
    "haiku_cost": 0.13,
    "untested": ["sonnet", "opus"],
    "recommendation": "Haiku performing well; A/B test Sonnet before considering change"
  },
  "{service-name}": {
    "task_count": 8,
    "models_tried": ["haiku", "sonnet"],
    "haiku_quality": 86.2,
    "sonnet_quality": 93.5,
    "quality_gap": 7.3,
    "recommendation": "Sonnet preferred for {service-name}; higher complexity (React, state management)"
  }
}
```

---

## Pattern Recognition

### Haiku Strength Patterns

Haiku excels when:
- Task is well-scoped (< 500 LOC change)
- Implementation is straightforward (algorithm known, pattern clear)
- Complexity = low or medium (not architectural design)
- Task type = feature, bug_fix, documentation
- Test coverage goal already clear
- No ambiguity in success criteria

Haiku struggles when:
- Scope is vague or sprawling (multiple services)
- Architecture decisions required
- Complexity = high or unknown
- Error handling edge cases unclear
- Interacts with unfamiliar code patterns

### Sonnet Strength Patterns

Sonnet excels when:
- Task scope is ambiguous (needs clarification)
- Architectural decisions required
- Complexity = medium or high
- Task type = refactor, api-design, code-review
- Edge cases and error handling important
- Needs to understand cross-service impact

Sonnet struggles when:
- Task is trivial (over-provisioned)
- Cost is the primary concern
- Well-scoped implementation tasks (overkill)

### Opus Strength Patterns

Opus excels when:
- Cross-service architecture required
- Principal-level decisions (system-wide impact)
- Security analysis needed
- Complex tradeoff analysis (cost vs. quality vs. scale)
- First-time implementation of new pattern

Opus rarely needed for:
- Single-service changes
- Well-defined implementation tasks
- Routine code review

---

## Comparison Record

```json
{
  "reporting_period": "2026-04-01 to 2026-04-30",
  "tasks_analyzed": 42,
  "models_in_sample": ["haiku", "sonnet"],
  "comparison_by_dimension": {
    "task_type": {
      "feature": { "haiku": 90, "sonnet": 92, "delta": 2 },
      "bug_fix": { "haiku": 91, "sonnet": 91, "delta": 0 },
      "refactor": { "haiku": 85, "sonnet": 90, "delta": 5 }
    },
    "complexity": {
      "low": { "haiku": 92, "sonnet": 93, "delta": 1 },
      "medium": { "haiku": 89, "sonnet": 92, "delta": 3 },
      "high": { "haiku": 82, "sonnet": 91, "delta": 9 }
    },
    "repository": {
      "{example-service}": { "haiku": 90, "sonnet": null, "tested_models": ["haiku"] },
      "{service-name}": { "haiku": 87, "sonnet": 93, "delta": 6 },
      "{example-service}": { "haiku": 89, "sonnet": 91, "delta": 2 }
    }
  },
  "key_insights": [
    "Haiku sufficient for bug fixes (delta = 0)",
    "Sonnet +5 points on refactors — should be standard for refactor work",
    "Haiku struggles on high-complexity (82 vs 91) — need clear threshold rules",
    "{service-name} consistently benefits from Sonnet (+6 avg) — consider permanent assignment",
    "Opus never tried yet — schedule evaluation on next high-complexity cross-service task"
  ],
  "routing_implications": {
    "low_complexity_all_types": "use_haiku",
    "medium_complexity_feature": "use_haiku",
    "medium_complexity_refactor": "use_sonnet",
    "high_complexity_any": "use_sonnet",
    "app_any": "use_sonnet",
    "cross_service_design": "use_opus"
  }
}
```

---

## A/B Test Planning

When models are close in quality but differ in cost:

```json
{
  "test_design": {
    "hypothesis": "Haiku achieves 90+ quality on {example-service} medium tasks at $0.13 cost",
    "control": "haiku_high_effort",
    "test": "sonnet_medium_effort",
    "success_criteria": "haiku >= 89 AND cost <= $0.13",
    "sample_size": 5,
    "duration": "2 weeks",
    "allocation": "50% haiku, 50% sonnet"
  },
  "metrics_to_track": [
    "quality_score",
    "tokens_in",
    "tokens_out",
    "escalations",
    "cost_usd",
    "duration_minutes"
  ]
}
```

---

## Calibration

Review monthly to detect:
- **New model releases:** Schedule 5-task evaluation
- **Task mix changes:** Adjust recommendations if complexity distribution shifts
- **Cost targets changing:** Rebalance model allocation
- **Quality targets changing:** May shift Haiku/Sonnet boundary
- **Outliers:** Tasks that deviate significantly from patterns

If a model consistently underperforms on a task type, investigate:
- Is the task truly that type, or was it miscategorized?
- Are there additional task characteristics not captured?
- Did the model actually struggle, or were other factors involved (scope creep, unclear requirements)?

---

## Integration with Decision Tree

Model Comparison findings feed into:
1. **Default model assignment** for new task types
2. **Escalation criteria** (when to upgrade models mid-task)
3. **A/B test proposals** (which models to compare next)
4. **Cost optimization** (identify low-cost safe options)
5. **New model evaluation** (baselines for comparison)
