# Model Engineer — Quality Feedback Analysis

**Role:** Model Engineer (Opus, coordinated by Quality Engineer)  
**Purpose:** Extract signal from Quality Engineer feedback to identify systematic patterns in code quality issues, model strengths/weaknesses, and improvement opportunities

---

## Overview

Quality Feedback Analysis transforms QE notes, pass/fail verdicts, and Tier 1/2/3 checklist results into actionable insights for model selection.

**Input:** Quality Engineer HANDBACK feedback, QUALITY.md gate results, rework loop counts  
**Output:** Pattern analysis with implications for future model assignments

**Goal:** Use QE expertise to continuously improve model recommendations.

---

## Feedback Categories

### Tier 1 Failures

Failures on mandatory items (lint, test, coverage, production hazards):

```json
{
  "failure_type": "test_coverage_below_80",
  "frequency": 3,
  "models_affected": ["haiku"],
  "pattern": "Haiku undertests on complex functions; average coverage 76% vs Sonnet 89%",
  "implication": "For high-complexity tasks, Sonnet's test coverage better (5+ hours of rework saved per task)",
  "recommendation": "Require Sonnet for tasks >200 LOC with complex logic"
}
```

### Tier 2 Failures

Failures on best-practices (documentation, architecture adherence):

```json
{
  "failure_type": "missing_architecture_decision_docs",
  "frequency": 2,
  "models_affected": ["haiku"],
  "pattern": "Haiku skips decision documentation on refactors; Sonnet includes WHY",
  "implication": "Future maintainers struggle with Haiku-generated code",
  "recommendation": "For refactors, Sonnet's documented decisions worth 23% cost premium"
}
```

### Rework Loops

Tasks requiring >1 QE iteration:

```json
{
  "task_id": "2026-04-24-auth-timeout",
  "model": "haiku",
  "rework_count": 2,
  "failure_1": "Test coverage 74% (need ≥80%)",
  "failure_2": "Panic on edge case",
  "total_rework_time": "2.5 hours",
  "root_cause": "Task complexity (high) > Haiku capability for this type",
  "decision": "Upgrade similar high-complexity tasks to Sonnet"
}
```

### Pass Patterns

Successful completions with notable feedback:

```json
{
  "task_id": "2026-04-24-cache-feature",
  "model": "haiku",
  "quality_score": 94,
  "qe_feedback": "Excellent test coverage (92%), clear error handling, follows patterns perfectly",
  "pattern": "Haiku excels on well-scoped, pattern-following tasks in known repos",
  "implication": "Haiku is optimally cost-efficient here; no change needed"
}
```

---

## Analysis Methods

### Failure Root Cause Analysis

For each HANDBACK failure:

1. **What failed?** (lint, test coverage, edge case, security, performance)
2. **Why?** (model capability, scope creep, unclear requirements, task type mismatch)
3. **Could different model prevent this?** (Y/N/Maybe)
4. **How many hours of rework?**
5. **Cost to prevent:** (cost_of_better_model - cost_of_haiku) vs rework_hours saved

**Example:**
```
Task: {service-name} refactor
Failure: Test coverage 72% (need ≥80%)
Why: Haiku didn't identify all edge cases in React component state logic
Could Sonnet prevent? Yes (Sonnet 18/20 on similar tasks, Haiku 12/20)
Rework hours: 3 hours
Cost to prevent: $0.05 (Sonnet cost) vs $0.13 (Haiku cost) = +$0.05
Rework value: 3 hours * $50/hr (approx cost to fix) = $150
Decision: Upgrade to Sonnet (cost $0.05 << value of preventing 3hr rework)
```

### Escalation Trigger Analysis

When QE escalates (marks as "needs Senior Engineer review"):

```json
{
  "escalation_type": "needs_architecture_review",
  "frequency": 2,
  "models_responsible": ["haiku"],
  "pattern": "Haiku handles implementation fine but misses architectural implications",
  "implication": "Task type = 'complex refactor' should route to Sonnet or Lead Engineer directly",
  "confidence": 0.80
}
```

### Success Factor Analysis

What conditions lead to first-pass HANDBACK acceptance?

```json
{
  "high_success_factors": [
    "Well-defined acceptance criteria in DELEGATE",
    "Task within known patterns (previous similar tasks existed)",
    "Low-medium complexity",
    "Single service (not cross-service)",
    "Clear repo structure"
  ],
  "low_success_factors": [
    "Vague scope in DELEGATE",
    "First time implementing pattern",
    "High-complexity or ambiguous requirements",
    "Multiple services involved",
    "Unclear test strategy"
  ],
  "implication": "DELEGATE quality matters more than model choice for simple tasks"
}
```

---

## Feedback Record

```json
{
  "reporting_period": "2026-04-01 to 2026-04-30",
  "tasks_reviewed": 42,
  "pass_first_try": 38,
  "require_rework": 4,
  "escalated": 1,
  "feedback_summary": {
    "strength_areas": [
      "Haiku excels on well-scoped bug fixes (24/24 pass, 0 escalations)",
      "Sonnet better on refactors (6/6 pass vs Haiku 2/4 pass on refactors)",
      "Both models handle documentation equally well"
    ],
    "weakness_areas": [
      "Haiku undertests on complex logic (3 coverage failures)",
      "Haiku misses edge cases in error handling (2 panic failures)",
      "Sonnet sometimes over-engineers simple solutions (adds unnecessary abstraction)"
    ],
    "rework_root_causes": {
      "test_coverage": 2,
      "edge_case_missing": 1,
      "architecture_violation": 1
    }
  },
  "model_specific_insights": {
    "haiku": {
      "patterns": "Excellent on straightforward implementations; struggles with complexity/edge cases",
      "tier1_pass_rate": 0.95,
      "avg_coverage": 0.82,
      "escalation_rate": 0.05,
      "rework_count": 4,
      "recommendation": "Keep for low-medium complexity; upgrade high-complexity to Sonnet"
    },
    "sonnet": {
      "patterns": "Stronger on complex logic and architectural thinking; sometimes over-builds simple tasks",
      "tier1_pass_rate": 1.0,
      "avg_coverage": 0.91,
      "escalation_rate": 0.0,
      "rework_count": 0,
      "recommendation": "Use for refactors, high-complexity, and architectural decisions"
    }
  },
  "action_items": [
    {
      "finding": "Haiku test coverage averaging 80% (meets baseline but borderline)",
      "action": "Require Haiku+high_effort for tasks >150 LOC; recommend Sonnet for >200 LOC",
      "owner": "Model Engineer",
      "timeline": "Immediate"
    },
    {
      "finding": "Sonnet adds abstraction 2/6 times (premature optimization)",
      "action": "Add note to Sonnet DELEGATE: 'Prefer simple implementations unless architecture requires abstraction'",
      "owner": "Orchestrator",
      "timeline": "Next DELEGATE template"
    },
    {
      "finding": "Haiku edge case detection 2/4 failures on {service-name}",
      "action": "Schedule A/B test: Haiku vs Sonnet on {service-name} tasks",
      "owner": "Model Engineer (A/B Testing)",
      "timeline": "Week of 2026-05-01"
    }
  ]
}
```

---

## Feedback Sources

### Direct QE Notes

QE can add structured notes to HANDBACK:

```yaml
handoff_type: HANDBACK
task_id: 2026-04-24-cache-feature
qe_feedback:
  tier_1_pass: true
  coverage: 92
  notes:
    - "Excellent edge case handling in cache eviction logic"
    - "Clear error messages — helpful for debugging"
    - "Test names are descriptive and follow patterns"
  strengths:
    - "Test coverage exceeds requirements"
    - "Error handling is defensive"
  areas_for_improvement: []
  model_assignment_feedback: "Haiku is well-suited for this task; cost-effective choice"
---
```

### Failure Patterns

When QE fails a task, capture:
- Which gate failed (Tier 1/2/3, specific check)
- Severity (major blocker vs. minor issue)
- Estimated rework time
- Whether a different model might have prevented this

### Escalation Notes

When QE escalates rather than approving:

```yaml
qe_escalation:
  reason: "Architectural decision requires Lead Engineer review"
  summary: "Implementation is technically correct but architecture pattern choice needs validation"
  recommend_model: "Sonnet or Lead Engineer (to provide better architecture guidance)"
```

---

## Pattern Detection Algorithm

For each feedback type, track:

1. **Frequency:** How often does this issue occur? (<5% is noise, >20% is systematic)
2. **Model correlation:** Which models have this issue? (Is it a model limitation or task characteristic?)
3. **Preventability:** Could a better model choice prevent this? (5-point rubric: definitely not, probably not, maybe, probably yes, definitely yes)
4. **Cost-benefit:** Cost to prevent (model upgrade) vs. cost to fix (rework hours)?

Example threshold rules:
- Issue >20% frequency AND preventable by model upgrade → adjust routing rules
- Issue 5-20% frequency AND low cost to prevent → consider A/B test
- Issue <5% frequency → monitor but don't change routing yet

---

## Integration with Model Engineer

Quality Feedback Analysis feeds into:

1. **Model selection decisions** (QE data validates/challenges Model Analysis recommendations)
2. **A/B test planning** (identifies most promising experiments)
3. **Confidence scoring** (QE agreement/disagreement affects confidence in model assignment)
4. **Escalation rules** (task characteristics that need model upgrade mid-execution)
5. **DELEGATE quality improvements** (feedback on how clear/scoped DELEGATE markup is)

---

## Constraints & Calibration

**Monthly calibration:**
- Review all patterns to detect anomalies or trends
- Recalibrate model assignment thresholds if patterns shift
- Validate that recommended models actually reduce rework

**Guard rails:**
- Never recommend model downgrade based on single failure (need ≥3 samples)
- Always review escalations manually before using as routing signal
- If two models tied in quality, cost differential determines choice
