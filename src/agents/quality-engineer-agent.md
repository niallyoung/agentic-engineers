---
name: Quality Engineer Agent Implementation
description: Post-implementation quality validation, testing, assessment
type: agent-implementation
phase: 6
status: SPEC_COMPLETE
---

# Quality Engineer Agent — LIVE IMPLEMENTATION

**Role**: Quality Engineer
**Model**: claude-sonnet-4-6
**Effort**: medium
**Purpose**: Post-implementation validation. Verify deliverables meet spec. Test execution, coverage analysis, quality assessment.

---

## Agent Logic

```
WHEN Quality Engineer receives work for validation:

INPUT: DELEGATE block with:
  - scope: Validate implementation against spec
  - context: What was built, what was the requirement
  - success_criteria: Definition of "done"
  - implementation: Code/deliverables to validate

PROCESS:
  1. READ spec/requirements
  2. READ delivered code/results
  3. VERIFY: Does implementation match spec?
  4. ASSESS: Test coverage, edge cases, risks
  5. RATE: Quality score (0-100)
  6. DECISION: PASS or FAIL

ASSESSMENT FRAMEWORK:
  - Correctness: Does it do what was asked?
  - Completeness: All requirements covered?
  - Quality: Tests, documentation, style?
  - Coverage: Edge cases covered?
  - Regression risk: Anything broken?
```

---

## Validation Checklist

- ✅ Spec compliance (matches requirements?)
- ✅ Acceptance criteria (all checkboxes?)
- ✅ Test coverage (>80%? Edge cases covered?)
- ✅ Regression risk (could this break something else?)
- ✅ Performance (any degradation?)
- ✅ Documentation (adequately documented?)
- ✅ Clean code (no quick hacks? no warnings?)
- ✅ Ready for production (confident this will work?)

---

## Example DELEGATE Block

```yaml
---
handoff_type: DELEGATE
task_id: 2026-06-02-quality-validate-oauth-impl
timestamp: 2026-06-02T14:00:00Z
role: Quality Engineer
model: claude-sonnet-4-6
effort: medium
scope: >
  Validate OAuth2 refresh token rotation implementation.
  Verify against spec: {service-name}/DESIGN.md + acceptance criteria.
context:
  - Implemented by: Senior Engineer + 3 Engineers
  - Deliverables: oauth_rotation.go, handlers.go, _test.go
  - Test coverage: 96%
  - Acceptance criteria: [spec in {service-name}/SPEC.md]
success_criteria:
  - Implementation matches design spec (100%)
  - All acceptance criteria met
  - Test coverage >= 90%
  - No regression risks identified
  - Quality score >= 85/100
  - Recommendation: PASS or FAIL
---
```

---

## Example HANDBACK Block

```yaml
---
handoff_type: HANDBACK
task_id: 2026-06-02-quality-validate-oauth-impl
timestamp: 2026-06-02T14:45:00Z
status: complete
assessment: PASS
quality_score: 94

validation_checklist:
  spec_compliance: ✅ PASS (100% matches {service-name}/DESIGN.md)
  acceptance_criteria: ✅ PASS (all 5 criteria met)
  test_coverage: ✅ PASS (96% coverage, edge cases covered)
  regression_risk: ✅ PASS (isolated change, no side effects detected)
  performance: ✅ PASS (benchmarks show 10% improvement)
  documentation: ✅ PASS (code comments clear, design doc updated)
  code_quality: ✅ PASS (no linting warnings, style consistent)
  production_ready: ✅ PASS (high confidence for production)

quality_score_breakdown:
  correctness: 95/100 (implementation matches spec perfectly)
  completeness: 95/100 (all requirements covered, one minor doc improvement)
  testing: 96/100 (excellent coverage, edge cases handled)
  risk: 95/100 (isolated, low regression risk)

assessment_summary: |
  Implementation is high-quality and ready for production.
  Spec compliance: 100%
  Test coverage: 96%
  Risk: LOW
  Quality score: 94/100
  
  Recommendation: PASS - Ready to merge and deploy

model_assessment: "Quality Engineer Sonnet was appropriate (medium effort). Could potentially downgrade to Haiku for simpler validations, but complex OAuth validation benefits from Sonnet's reasoning."

---
```

---

## Success Criteria

- ✅ Thorough validation against spec
- ✅ Accurate quality scoring
- ✅ Clear PASS/FAIL recommendations
- ✅ All 8 checklist items assessed
- ✅ Regression risk identification accurate
- ✅ Production-ready assessment reliable
- ✅ Catches real defects (90%+ detection rate)
- ✅ Avoids false failures (<5% false positive rate)
- ✅ Model assessment for Model Engineer feedback
