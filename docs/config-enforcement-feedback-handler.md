---
name: Config Enforcement Feedback Handler
description: Verify fixes work, build confidence in auto-correction
type: handler
phase: 6
status: IMPLEMENTATION_READY
---

# Config Enforcement Feedback Handler

**Purpose**: After Config Enforcement Agent applies a fix, re-run Config Audit to verify improvement. Use outcome to refine confidence in future similar fixes.

---

## Feedback Loop

```
Config Audit Agent
  │
  ├─ HANDBACK: {deviations, compliance_score, severity}
  │    e.g., ["env file missing DATABASE_URL", "Makefile target missing"]
  │
  ▼
Config Enforcement Agent
  │
  ├─ Applies high-confidence fixes (≥0.8)
  │    e.g., "add DATABASE_URL to .env" (confidence: 0.95)
  │
  ├─ Escalates low-confidence fixes (<0.8)
  │    e.g., "add missing Makefile target?" (confidence: 0.60)
  │
  └─ HANDBACK: {fixes_attempted, fixes_succeeded, escalations, new_compliance_score}
  
       ▼
  [RE-VERIFY LOOP]
       │
       ├─ Re-run Config Audit
       │
       ├─ Compare: compliance_score before vs. after
       │    Before: 65%
       │    After:  85%
       │
       ├─ DECISION:
       │    IF after > before: FIX SUCCESSFUL
       │    IF after <= before: FIX FAILED or INEFFECTIVE
       │
       └─ UPDATE confidence for this fix type
            IF successful: confidence += 0.1 (trust it next time)
            IF failed: confidence -= 0.2 (avoid it next time)

  ▼ [ASYNC]
  Store outcome in artifacts/feedback/config-fixes.jsonl
```

---

## Handler Logic

```
WHEN Config Enforcement Agent writes HANDBACK with fixes_applied:

INPUT:
  - config_audit_handback_before: {
      deviations: [...],
      compliance_score: {before_score},
      timestamp: {before_timestamp}
    }
  - config_enforcement_handback: {
      fixes_attempted: [...],
      fixes_succeeded: [...],
      escalations: [...],
      new_compliance_score: {after_score},
      fixes_applied: [
        {fix: "add DATABASE_URL", confidence: 0.95, status: APPLIED},
        {fix: "add CACHE_REDIS_URL", confidence: 0.92, status: APPLIED},
      ]
    }

PROCESS:

  1. TRIGGER Config Audit Agent (re-run)
     Command: Re-run Config Audit on same service/commit
     Input: Same repo_path, service_name
     Output: New Config Audit HANDBACK (post-fix)
  
  2. COMPARE compliance scores
     compliance_before = {before_score} (from initial audit)
     compliance_after = {after_score} (from re-verification)
     
     improvement = compliance_after - compliance_before
     percent_improvement = (improvement / (100 - compliance_before)) * 100
  
  3. EVALUATE each fix
     
     FOR each fix in fixes_applied:
       
       fix_description = {fix description}
       applied_confidence = {confidence when applied}
       
       # Determine if fix was necessary and effective
       WAS_NEEDED = (fix_description was in deviations list)
       WAS_EFFECTIVE = (compliance_after > compliance_before)
       
       IF WAS_NEEDED AND WAS_EFFECTIVE:
         outcome = SUCCESS
         new_confidence = min(applied_confidence + 0.1, 1.0)
         reason = "Fix was needed and improved compliance"
       
       ELIF WAS_NEEDED AND NOT WAS_EFFECTIVE:
         outcome = FAILED
         new_confidence = max(applied_confidence - 0.2, 0.0)
         reason = "Fix was needed but didn't improve compliance"
       
       ELIF NOT WAS_NEEDED:
         outcome = UNNECESSARY
         new_confidence = applied_confidence  # No update
         reason = "Fix was not in deviation list"
       
       Log outcome:
       {
         fix: fix_description,
         applied_confidence: applied_confidence,
         new_confidence: new_confidence,
         outcome: outcome,
         reason: reason,
         timestamp: {iso8601}
       }
  
  4. STORE outcomes in artifacts/
     File: artifacts/feedback/config-fixes.jsonl (append-only)
     
     Each line is a JSON record:
     ```json
     {
       "timestamp": "2026-05-26T09:05:30Z",
       "service": "{service-name}",
       "fix": "add DATABASE_URL to .env",
       "fix_type": "env-variable-missing",
       "applied_confidence": 0.95,
       "outcome": "SUCCESS",
       "compliance_before": 65,
       "compliance_after": 85,
       "new_confidence": 1.0
     }
     ```
  
  5. AGGREGATE confidence per fix type
     Query all records in config-fixes.jsonl:
       success_count = {fixes with outcome: SUCCESS}
       total_count = {total fixes attempted}
       success_rate = success_count / total_count
       
       new_baseline_confidence = (
         initial_confidence * (1 - success_rate) +
         (initial_confidence + 0.1) * success_rate
       )
  
  6. UPDATE fix template confidence
     File: orchestration/config-templates.yaml
     
     Current:
     ```yaml
     - fix_id: "env-var-missing"
       pattern: "Missing required env var"
       fix_template: "Add {var_name} = {default_value}"
       confidence: 0.90
     ```
     
     Updated:
     ```yaml
     - fix_id: "env-var-missing"
       pattern: "Missing required env var"
       fix_template: "Add {var_name} = {default_value}"
       confidence: 0.95  # ← Updated based on 10 successful applications
       success_rate: 1.0  # ← 10/10 successful
       sample_size: 10
     ```
  
  7. WRITE summary to artifacts/
     File: artifacts/2026-MM-DD/HANDBACK-{timestamp}-config-enforcement-verify.yaml
     
     ```yaml
     handoff_type: HANDBACK
     task_id: {original_task_id}
     timestamp: {iso8601}
     status: VERIFICATION_COMPLETE
     
     verification_result:
       compliance_before: 65.0
       compliance_after: 85.0
       improvement: +20.0 percentage points
       fixes_verified: 2
       fixes_successful: 2
       fixes_failed: 0
     
     per_fix_outcomes:
       - fix: "add DATABASE_URL"
         outcome: SUCCESS
         applied_confidence: 0.95
         new_confidence: 1.0
       - fix: "add CACHE_REDIS_URL"
         outcome: SUCCESS
         applied_confidence: 0.92
         new_confidence: 1.0
     
     attributes:
       config_fix_type: "environment-variable"
       service: "{service-name}"
       total_deviations_resolved: 2
       escalation_needed: false
     ```
  
  8. WRITE OpenTelemetry span
     - span_name: "config-enforcement-verify"
     - attributes: {
         fixes_verified, fixes_successful, compliance_improvement,
         service_name, fix_types_applied
       }
     - events: [
         {name: "fix_applied", attributes: {fix, confidence}},
         {name: "verification_complete", attributes: {outcome}}
       ]

DECISION AFTER VERIFICATION:

  IF compliance_after > compliance_before:
    final_decision = PROCEED
    reason = "Fixes successfully improved compliance"
  
  ELIF compliance_after == compliance_before:
    final_decision = INVESTIGATE
    reason = "Fixes applied but compliance unchanged (may need investigation)"
  
  ELSE (compliance_after < compliance_before):
    final_decision = ESCALATE
    reason = "Fixes applied but compliance worsened (rollback needed)"
```

---

## Example: Fix Verification Success

**Initial Config Audit**: Compliance 65% (missing env vars and targets)

```yaml
deviations:
  - "Missing DATABASE_URL in .env"
  - "Missing DATABASE_PASSWORD in .env"
  - "Missing test target in Makefile"
```

**Config Enforcement Applied Fixes**:

```yaml
fixes_applied:
  - fix: "add DATABASE_URL to .env"
    confidence: 0.95
    status: APPLIED
  - fix: "add DATABASE_PASSWORD to .env"
    confidence: 0.93
    status: APPLIED
  - fix: "add test target to Makefile"
    confidence: 0.60  # Low confidence (would escalate)
    status: ESCALATED
```

**Re-Verification**: Config Audit runs again, compliance 85%

```yaml
new_deviations:
  - "Missing test target in Makefile"  # (escalated fix, not applied)

# No longer present (fixes worked):
# - DATABASE_URL ✓ FIXED
# - DATABASE_PASSWORD ✓ FIXED
```

**Outcome Analysis**:

```json
{
  "fix": "add DATABASE_URL to .env",
  "applied_confidence": 0.95,
  "outcome": "SUCCESS",
  "improvement": "+10 pp",
  "new_confidence": 1.0
}

{
  "fix": "add DATABASE_PASSWORD to .env",
  "applied_confidence": 0.93,
  "outcome": "SUCCESS",
  "improvement": "+10 pp",
  "new_confidence": 1.0
}

{
  "fix": "add test target to Makefile",
  "applied_confidence": 0.60,
  "outcome": "ESCALATED",
  "action": "human review needed",
  "confidence": 0.60  # unchanged
}
```

---

## Continuous Learning

**After 10 runs of "add DATABASE_URL to .env"**:

```yaml
fix_id: "env-var-database-url"
success_count: 10
total_count: 10
success_rate: 100%

confidence_evolution:
  run_1: 0.95  # Initial
  run_2: 1.00  # First success → +0.1
  run_3: 1.00  # Stays at max
  ...
  run_10: 1.0  # 100% success

decision: "Increase applied_confidence to 0.98"
reason: "Proven fix, auto-apply next time without escalation threshold"
```

---

## Integration: Using Confidence in Future Fixes

**Phase 7+: Continuous Improvement Loop**

When Config Enforcement considers a fix:

```
IF fix.learned_confidence >= 0.9:
  APPLY immediately (high trust)
  NO human review needed

ELIF fix.learned_confidence 0.7-0.9:
  APPLY but flag for post-verification
  (will re-verify compliance)

ELIF fix.learned_confidence < 0.7:
  ESCALATE (low trust)
  Request human review
```

Over time, proven fixes are applied faster. Unproven/risky fixes are escalated or re-verified.

---

## Success Criteria (Phase 6 Testing)

- ✅ Config Enforcement handback triggers re-verification
- ✅ Config Audit re-run completes within 1 minute
- ✅ Compliance score correctly compared before/after
- ✅ Per-fix outcomes calculated correctly
- ✅ Append-only log in config-fixes.jsonl works
- ✅ Confidence scores updated (+0.1 for success, -0.2 for failure)
- ✅ Success rate calculation accurate across 10+ runs
- ✅ OpenTelemetry spans capture fix outcomes
- ✅ Summary HANDBACK written with verification results
- ✅ No false successes (compliance actually improved)
