# Quality Engineer — Code Quality Analysis for Model Optimization

**Role:** Quality Engineer (Haiku/Sonnet, coordinated with Model Engineer)  
**Purpose:** Provide structured quality feedback during HANDBACK verification to enable Model Engineer analysis and continuous improvement

---

## Overview

Code Quality Analysis captures QE observations beyond pass/fail verdicts, enabling Model Engineer to analyze patterns in model strengths/weaknesses.

**Input:** HANDBACK deliverables, QUALITY.md gate checklist results  
**Output:** Structured feedback record with quality observations and model assignment recommendations

**Goal:** Feed rich quality signal to Model Engineer for better routing recommendations.

---

## Feedback Structure

Every HANDBACK should include Quality Engineer notes:

```yaml
handoff_type: HANDBACK
task_id: 2026-04-24-redis-caching
status: complete
qe_feedback:
  tier_1_verdict: PASS
  tier_2_verdict: PASS
  tier_3_verdict: N/A
  
  # Structured observations (help Model Engineer analyze patterns)
  code_quality:
    test_coverage: 87
    coverage_assessment: "Good; covers happy path, hit/miss scenarios, error cases"
    error_handling: "defensive"
    error_handling_notes: "All potential failures handled gracefully; clear error messages"
  
  pattern_adherence: "Follows {example-service} conventions perfectly; no deviations"
  
  completeness:
    scope_adherence: "in_scope"
    completeness_notes: "All acceptance criteria met; no gold-plating"
  
  testing:
    test_quality: "excellent"
    test_notes: "Table-driven tests; clear test names; edge cases covered"
  
  maintainability:
    documentation_quality: "good"
    documentation_notes: "Decision comments explain WHY, not WHAT"
    code_clarity: "clear"
    code_clarity_notes: "Variable names are descriptive; logic is easy to follow"
  
  # Assessment for model selection feedback
  model_assessment:
    recommendation: "Haiku is suitable for this task"
    reasoning: "Implementation was straightforward, patterns were well-known, model executed efficiently"
    complexity_actual: "medium"
    complexity_assessment: "matches initial estimate"
    escalation_needed: false
  
  # Concerns or flags (if any)
  concerns: []
  
  # Overall quality score (1-100)
  quality_score: 92
---
```

---

## Feedback Categories

### Code Quality Dimensions

**Test Coverage & Quality**
- Coverage percentage
- Are edge cases covered? (panic cases, error paths, boundary conditions)
- Are test names descriptive?
- Does testing strategy match task type?
- Example: "87% coverage, excellent edge case coverage, clear table-driven tests"

**Error Handling**
- Are all error paths handled?
- Do error messages help debugging?
- Is error handling defensive (fails safe)?
- Example: "Defensive; all potential errors handled with clear messages"

**Pattern Adherence**
- Does code follow repo conventions?
- Are established patterns used correctly?
- Any anti-patterns introduced?
- Example: "Follows {example-service} conventions; no deviations"

**Completeness**
- Are all acceptance criteria met?
- Any gold-plating or scope creep?
- Is scope clearly bounded?
- Example: "In-scope; all acceptance criteria met; no over-engineering"

**Maintainability**
- Are decision comments explaining WHY?
- Is code self-documenting?
- Will future maintainers understand this?
- Example: "Good documentation of decisions; clear variable names; logic easy to follow"

---

## Quality Assessment for Model Engineer

When completing Tier 1 verification, note:

```yaml
model_assessment:
  # Key question: Did the assigned model handle this task appropriately?
  recommendation: "haiku_suitable" | "sonnet_suitable" | "sonnet_would_be_better" | "opus_required"
  
  reasoning: |
    One sentence explaining why the model was (or wasn't) appropriate.
    Consider: scope clarity, complexity, pattern familiarity, edge case handling.
  
  complexity_actual: "low" | "medium" | "high"
  complexity_assessment: "matches_estimate" | "simpler_than_estimated" | "more_complex_than_estimated"
  
  # Was the effort level appropriate?
  effort_assessment: "appropriate" | "insufficient" | "excessive"
  
  # Any need to escalate during execution?
  escalation_needed: false | true
  escalation_reason: "if true, explain what would have helped"
  
  # Confidence in this model for similar future tasks
  confidence_for_similar_tasks: 0.0..1.0
```

---

## Feedback Examples

### Example 1: Haiku Excels

```yaml
qe_feedback:
  model_assessment:
    recommendation: "haiku_suitable"
    reasoning: "Task was well-scoped with clear acceptance criteria. Model correctly identified patterns from existing code and applied them. No over-engineering."
    complexity_actual: "low"
    complexity_assessment: "matches_estimate"
    effort_assessment: "appropriate"
    escalation_needed: false
    confidence_for_similar_tasks: 0.95
  quality_score: 94
```

### Example 2: Sonnet Adds Value

```yaml
qe_feedback:
  model_assessment:
    recommendation: "sonnet_suitable"
    reasoning: "Complex refactor with architectural implications. Sonnet thoroughly analyzed impact on other services and documented decisions well."
    complexity_actual: "high"
    complexity_assessment: "matches_estimate"
    effort_assessment: "appropriate"
    escalation_needed: false
    confidence_for_similar_tasks: 0.92
  
  code_quality:
    test_coverage: 91
    error_handling: "defensive"
    pattern_adherence: "excellent"
    documentation_quality: "excellent"
    documentation_notes: "Architecture decisions clearly documented with rationale"
  
  quality_score: 93
```

### Example 3: Model Limits Identified

```yaml
qe_feedback:
  model_assessment:
    recommendation: "sonnet_would_be_better"
    reasoning: "Haiku missed edge case in error recovery path. Required manual fix during QE review. Task complexity was high."
    complexity_actual: "high"
    complexity_assessment: "more_complex_than_estimated"
    effort_assessment: "insufficient"
    escalation_needed: true
    escalation_reason: "Should have escalated to Sonnet when requirements became clearer during implementation"
    confidence_for_similar_tasks: 0.45
  
  code_quality:
    test_coverage: 78
    coverage_assessment: "Below target; edge case not covered"
    error_handling: "incomplete"
    error_handling_notes: "Race condition in cache eviction not handled"
  
  quality_score: 72
```

---

## Assessment Rubric

### Recommendation Mapping

**haiku_suitable:**
- Quality score ≥85
- No rework needed
- Complexity matches estimate
- Patterns applied correctly
- Test coverage ≥80%

**sonnet_suitable:**
- Quality score ≥90
- Task is complex/architectural
- Decisions well-documented
- Edge cases covered
- Test coverage ≥85%

**sonnet_would_be_better:**
- Quality score 70-85
- Rework needed
- Complexity was underestimated
- Model missed edge cases
- Test coverage <80%

**opus_required:**
- Cross-service architecture changes
- Multiple teams need alignment
- Complex tradeoff analysis required
- Security implications unclear
- Existing pattern not adequate

### Confidence Scoring

```
1.0 = Certain this model is right for similar tasks
0.8-0.99 = Confident, but small risk of edge cases
0.6-0.79 = Moderate confidence; consider A/B test if high-stakes
0.4-0.59 = Low confidence; recommend exploring alternatives
<0.4 = Model likely not suited; recommend upgrade or major change
```

---

## Integration with Model Engineer Workflow

Quality Engineer feedback follows this path:

1. **QE completes Tier 1 verification** → adds `model_assessment` and `quality_score` to HANDBACK
2. **HANDBACK recorded** with quality feedback in `~/.claude/metrics/YYYY-MM-DD/task_id.json`
3. **Model Engineer analyzes** using quality-feedback-analysis.md skill
4. **Model Engineer generates recommendation** in model-recommendation.md
5. **Orchestrator uses recommendation** for next similar task routing

Example JSON flow:

```json
{
  "task_id": "2026-04-24-redis-caching",
  "qe_feedback": {
    "model_assessment": {
      "recommendation": "haiku_suitable",
      "reasoning": "...",
      "confidence_for_similar_tasks": 0.92
    },
    "quality_score": 92
  },
  "model_engineer_analysis": {
    "quality_feedback_signal": 0.92,
    "cost_feedback": "$0.13",
    "recommendation": "haiku_high_effort"
  }
}
```

---

## Guidelines for Consistent Feedback

### When to Say "haiku_suitable"
- Task executed without rework
- Quality meets/exceeds expectations
- Patterns applied correctly
- No complexity surprises

### When to Say "sonnet_would_be_better"
- Task needed rework (1+ loop)
- Edge case or error handling missed
- Complexity was underestimated
- Quality score <85

### When to Escalate During Execution
- Requirements become ambiguous mid-task
- Complexity higher than DELEGATE indicated
- Cross-service implications discovered
- Pattern doesn't apply

When escalating, note: "Would have benefited from Sonnet's broader perspective on architecture implications."

---

## Quality Score Interpretation

**90-100:** Excellent  
- All gates pass
- High test coverage
- Clear code, good decisions
- Model is suitable or exceeded expectations

**80-89:** Good  
- All gates pass
- Acceptable coverage (80%+)
- Functional but some minor improvements possible
- Model is suitable

**70-79:** Fair  
- Passed with minor issues
- Some rework needed
- Coverage/clarity could improve
- Model may be under-scoped

**60-69:** Poor  
- Failed at least one gate initially
- Significant rework required
- Quality gaps in testing or error handling
- Model is likely unsuitable

**<60:** Unacceptable  
- Multiple failures
- Extensive rework needed
- Major issues in patterns or safety
- Escalation required

---

## Feedback Template

Include this in every HANDBACK:

```yaml
qe_feedback:
  tier_1_verdict: PASS | FAIL
  
  code_quality:
    test_coverage: <number>
    coverage_assessment: <string>
    error_handling: "defensive" | "adequate" | "incomplete"
    error_handling_notes: <string>
  
  pattern_adherence: <string>
  completeness_notes: <string>
  
  testing:
    test_quality: "excellent" | "good" | "adequate" | "poor"
    test_notes: <string>
  
  maintainability:
    documentation_quality: "excellent" | "good" | "adequate" | "poor"
    documentation_notes: <string>
    code_clarity: "clear" | "readable" | "unclear"
  
  model_assessment:
    recommendation: "haiku_suitable" | "sonnet_suitable" | "sonnet_would_be_better" | "opus_required"
    reasoning: <one sentence>
    complexity_actual: "low" | "medium" | "high"
    complexity_assessment: "matches_estimate" | "simpler" | "more_complex"
    escalation_needed: true | false
    confidence_for_similar_tasks: 0.0..1.0
  
  quality_score: <1-100>
```

This feedback structure enables Model Engineer to continuously refine routing recommendations.
