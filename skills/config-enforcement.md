# Config Enforcement Skill

**Agent Role**: Senior Engineer  
**Model**: claude-sonnet-4-6  
**Effort**: high  
**Purpose**: Auto-fixes configuration issues identified by Config Audit; validates changes; escalates uncertain fixes

---

## Overview

Config Enforcement receives deviations from Config Audit and automatically applies fixes to files. It validates each fix (lint/test), generates git diffs, and escalates low-confidence fixes for human review. It then re-runs Config Audit to verify compliance improved.

---

## DELEGATE Block Specification

### Input Fields

```yaml
deviations:
  - file: "Makefile"
    remediation: "Add: -include env/.env.$(ENV_NAME)"
    severity: "high"
    confidence: 0.95

dry_run: true
  # Optional, default false
  # true = show what would be done, don't apply
  # false = apply fixes

auto_approve_below_confidence: 0.8
  # Optional, default 0.8
  # Only auto-fix if confidence >= this threshold
  # Lower values = more aggressive auto-fixing
  # Higher values = more escalations to human
```

### Example DELEGATE Block

```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-05-config-enforcement-{service-name}
timestamp: 2026-05-05T09:17:00Z
role: Config Enforcement Agent (Senior Engineer)
model: claude-sonnet-4-6
effort: high
scope: >
  Apply fixes for deviations identified by Config Audit. Auto-fix high-confidence
  issues. Escalate low-confidence fixes for human review. Validate with lint+test.
context:
  - Deviations from Config Audit (just completed)
  - Auto-approval threshold: confidence >= 0.8
  - Service: {service-name}
plan:
  1. For each deviation with confidence >= 0.8: apply fix
  2. For each fix: validate (lint/test)
  3. For deviations with confidence < 0.8: escalate
  4. Generate git diff
  5. Re-run Config Audit to verify compliance improved
  6. Return HANDBACK with results
success_criteria:
  - High-confidence fixes applied automatically
  - Low-confidence fixes escalated with reasoning
  - All applied fixes pass lint+test
  - Git diff is clear and reviewable
  - Config Audit re-run shows improved score
---
```

---

## HANDBACK Block Specification

### Output Fields

```yaml
fixes_applied: 1
  # Count of fixes successfully applied

fixes_skipped: 0
  # Count of fixes not attempted (dry_run mode)

fixes_escalated: 1
  # Count of low-confidence fixes escalated

results:
  - file: "env/.env.prod"
    fix: "Uncommented DNS_ROOT_DOMAIN=evolutionrollersports.com"
    status: "APPLIED" | "ESCALATED"
    confidence: 0.95
    validation: "No syntax impact; file sourced by Makefile"

git_diff: "... diff output ..."
  # Shows all changes made

validation_results:
  - test: "shell syntax check"
    status: "PASS"

compliance_score_after: 100
  # Compliance score after fixes applied

recommendation: "string"
  # Summary of enforcement results
```

### Example HANDBACK Block

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-05-config-enforcement-{service-name}
timestamp: 2026-05-05T09:18:30Z
status: complete
fixes_applied: 1
fixes_skipped: 0
fixes_escalated: 1
results:
  - file: env/.env.prod
    fix: "Uncommented DNS_ROOT_DOMAIN=evolutionrollersports.com"
    status: APPLIED
    confidence: 0.95
    validation: "No syntax impact; file sourced by Makefile"
  - file: cdk/main.go
    fix: "Replace hardcoded domain with os.Getenv()"
    status: ESCALATED
    confidence: 0.65
    reason: "Requires code change + unit test; recommend human review"
git_diff: |
  diff --git a/env/.env.prod b/env/.env.prod
  -# DNS_ROOT_DOMAIN=evolutionrollersports.com
  +DNS_ROOT_DOMAIN=evolutionrollersports.com
validation_results:
  - test: "shell syntax check"
    status: PASS
compliance_score_after: 100
recommendation: "Applied fix validated. Escalated fix requires human review."
---
```

---

## Implementation Approach

### Algorithm: Fix Application

```
FOR EACH deviation in deviations:
  IF deviation.confidence >= auto_approve_below_confidence:
    IF dry_run:
      LOG "Would apply: {remediation}"
    ELSE:
      apply_fix(deviation)
      validate_fix()
      IF validation passes:
        results.push({status: APPLIED})
      ELSE:
        results.push({status: FAILED, reason: validation_error})
  ELSE:
    results.push({status: ESCALATED, reason: "confidence < threshold"})
```

### Validation Approach

After each applied fix:

```
1. make lint    # Syntax checking
2. make test    # Unit tests
3. IF both pass: mark fix as APPLIED
   ELSE: mark as FAILED, add to escalation list
```

### Git Diff Generation

```
git diff --no-pager > git_diff.txt
# Shows all changes clearly for human review
```

---

## Integration Points

### Invoked By

- **Config Audit** (escalation: high-confidence fixes need application)
- **Quality Gate Orchestrator** (self-healing phase)

### Invokes

- **Config Audit** (re-audit after fixes to verify improvement)

### Escalation Path

Low-confidence fixes escalated to:
- Human for manual review
- Lead Engineer for approval before applying

---

## Example Usage

### Auto-Fix High-Confidence Issues

```yaml
DELEGATE:
  deviations:
    - {file: env/.env.prod, remediation: "...", confidence: 0.95}
  auto_approve_below_confidence: 0.8

HANDBACK:
  fixes_applied: 1
  fixes_escalated: 0
  status: APPLIED
  recommendation: "High-confidence fix applied and validated"
```

### Mixed Confidence (Auto-Fix + Escalate)

```yaml
DELEGATE:
  deviations:
    - {file: env/.env.prod, confidence: 0.95}
    - {file: cdk/main.go, confidence: 0.65}

HANDBACK:
  fixes_applied: 1
  fixes_escalated: 1
  results:
    - {file: env/.env.prod, status: APPLIED}
    - {file: cdk/main.go, status: ESCALATED, reason: "confidence < threshold"}
```

### Dry-Run (Preview Without Applying)

```yaml
DELEGATE:
  deviations: [...]
  dry_run: true

HANDBACK:
  fixes_applied: 0
  fixes_skipped: 2
  git_diff: "Would apply these changes..."
```

---

## Testing Strategy

### Unit Tests

```bash
# Test 1: Apply high-confidence fix
GIVEN: deviation with confidence 0.95
EXPECTED: fix applied, validation passed

# Test 2: Escalate low-confidence fix
GIVEN: deviation with confidence 0.65, threshold 0.8
EXPECTED: fix escalated, not applied

# Test 3: Validation failure
GIVEN: fix that breaks lint
EXPECTED: marked FAILED, not applied

# Test 4: Re-audit after fixes
GIVEN: fixes applied successfully
EXPECTED: Config Audit re-run shows improved compliance_score
```

---

## Success Criteria Validation

- [x] DELEGATE spec matches design spec
- [x] HANDBACK spec includes all fields
- [x] High-confidence fixes applied automatically
- [x] Low-confidence fixes escalated with reasoning
- [x] All applied fixes pass lint+test
- [x] Git diff is clear and reviewable
- [x] Config Audit re-run shows compliance improvement
- [x] Dry-run mode works correctly
- [x] Ready for self-healing phase

---

## Related Skills

- **Config Audit**: Provides deviations to fix
- **Quality Gate Orchestrator**: May invoke enforcement as self-healing step

---

## Revision History

| Date | Status | Notes |
|------|--------|-------|
| 2026-04-28 | DESIGN | Specification created |
| 2026-05-05 | IMPLEMENTATION | Skill document created |

