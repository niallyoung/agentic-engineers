# Lead Engineer Gray-Zone Review Process

## Scope: Quality Score 70–79

This gate applies to HANDBACKs with validator-computed quality score in 70–79 range.

## Review Checklist (Lead Engineer must assess all 5)

### 1. Risk Assessment
- [ ] Does this change risk production? (Y/N)
- [ ] Are there untested code paths? (Y/N)
- [ ] Does this introduce new dependencies? (Y/N)
- [ ] Severity if wrong: high/medium/low

### 2. Criterion-by-Criterion Analysis
- [ ] Which criteria from original DELEGATE are not fully met?
- [ ] For each unmet criterion, is it:
  - (a) Critical to function? (block = must rework)
  - (b) Important but deferrable? (conditional = accept + follow-up)
  - (c) Nice-to-have? (accept as-is)

### 3. Deliverable Verification
- [ ] All listed deliverables actually exist?
- [ ] Files match scope and plan?
- [ ] Any unexpected files created? (scope creep)

### 4. Test Coverage Assessment
- [ ] Test coverage meets DELEGATE requirement?
- [ ] New tests cover modified code?
- [ ] Any failing tests? (must rework)
- [ ] Coverage dropped vs previous version?

### 5. Code Quality Spot Check
- [ ] Code follows repo style guide?
- [ ] Docstrings present on public APIs?
- [ ] Error handling reasonable?
- [ ] Any obvious bugs or anti-patterns?

## Decision Matrix

Based on above assessment:

| Risk | Criteria Met | Coverage | Decision |
|------|-------------|----------|----------|
| Low | ≥3/4 | ≥90% | ✅ ACCEPT |
| Low | 2/4 | 85–89% | ⚠️ CONDITIONAL |
| Low | ≤1/4 | <85% | ❌ REWORK |
| Medium | ≥4/4 | ≥95% | ✅ ACCEPT |
| Medium | 3/4 | 90–94% | ⚠️ CONDITIONAL |
| Medium | ≤2/4 | <90% | ❌ REWORK |
| High | Any | Any | ❌ REWORK |

## Decision Actions

### ✅ ACCEPT
- Merge to main immediately
- Add note: "Accepted despite 70–79 score; verified low risk"
- No follow-up required

### ⚠️ CONDITIONAL
- Merge to main with follow-up issue created
- Add note: "Conditional acceptance; follow-up: [specific items]"
- Create GitHub issue with:
  - Title: "{task_id}: Conditional approval follow-up"
  - Body: List specific follow-up items (tests, docs, refactoring)
  - Label: `follow-up` `technical-debt`
  - Assign to original agent or Owner

### ❌ REWORK
- Do NOT merge; return to agent for rework
- Build rework DELEGATE with:
  - Previous score and failing criteria listed
  - Evidence quoted/referenced
- Set max_retries counter; follow normal rework flow

## SLA

Lead Engineer reviews gray-zone HANDBACKs within 2 hours of routing.

## Metrics Tracked

- Gray-zone reviews per week
- ACCEPT vs CONDITIONAL vs REWORK distribution
- Average time to review
- Follow-up issue completion rate (for CONDITIONAL)
