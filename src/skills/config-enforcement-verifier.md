---
name: Config Enforcement Verifier
description: Validates that Healing Agent auto-fixes actually resolved issues, tracks fix accuracy
type: skill
phase: 6.1
status: ACTIVE
model: claude-haiku
effort: medium
---

# Config Enforcement Verifier — Auto-Fix Validation & Accuracy Tracking

Monitors Healing Agent auto-fixes, verifies they actually work, and improves fix accuracy over time.

## Role

Post-healing validation system that:
- Confirms auto-fixes actually resolved the issues
- Tracks fix success rate (did it help or recur?)
- Identifies problematic patterns (fixes that keep breaking)
- Improves Healing Agent suggestions based on real outcomes

## Input: Healing Agent HANDBACK + Follow-up QG Runs

From Healing Agent:

```yaml
healing_handback:
  issues_found: 2
  fixes_applied:
    - issue: "ENVIRONMENT_VARIABLE_QUOTED"
      file: "env/.env.dev"
      fix: "Removed shell quotes from ENV_NAME=dev"
      confidence: 0.85
    
    - issue: "CDK_RESOURCE_PREFIX_MISSING"
      file: "cdk/main.go"
      fix: "Added default CDK_RESOURCE_PREFIX from env"
      confidence: 0.78
  
  severity: MEDIUM
  confidence: 0.82
```

## Verification Logic

```
WHEN Healing Agent reports fixes applied:

1. RECORD fix attempt
   
   File: ~/.agents/agentic-engineers/data/healing/fix-attempts.yaml
   
   ```yaml
   - timestamp: "2026-05-07T14:35:00Z"
     issue_type: "ENVIRONMENT_VARIABLE_QUOTED"
     fix_applied: "Removed shell quotes from ENV_NAME=dev"
     affected_file: "env/.env.dev"
     healing_confidence: 0.85
     commit_sha: "abc123"
     status: "PENDING_VERIFICATION"
   ```

2. WAIT for next QG run (next commit/deployment)
   
   // Check: Did same issue recur?
   // Check: Did fix break something else?
   // Outcome: Fix successful or regressed?

3. ANALYZE next QG result
   
   Next QG run has same commit/deployment?
   NO → Different commit tested, can't verify this fix
     ACTION: Flag as "INCONCLUSIVE" (can't verify in isolation)
   
   YES → Same code affected, can now judge fix
     COMPARE Healing output vs. current QG result
     
     IF issue still appears in next QG:
       VERDICT: FIX FAILED (regression)
       STATUS: "FAILED" (fix didn't work)
       NOTIFY: Healing Agent (fix confidence -0.15)
     
     IF issue gone in next QG:
       VERIFY: Did new issues appear?
       
       NEW_ISSUES = current_QG_issues - previous_QG_issues
       
       IF new_issues.length == 0:
         VERDICT: FIX SUCCESSFUL (clean)
         STATUS: "SUCCESS" (issue resolved, no regressions)
         NOTIFY: Healing Agent (fix confidence +0.10)
       
       ELSE:
         VERDICT: FIX PARTIAL (helped but created new issues)
         STATUS: "PARTIAL" (fix worked but side effects)
         NOTIFY: Healing Agent (fix confidence +0.05, minus new issues)

4. UPDATE fix history
   
   File: ~/.agents/agentic-engineers/data/healing/fix-history.yaml
   
   ```yaml
   - timestamp: "2026-05-07T14:35:00Z"
     issue_type: "ENVIRONMENT_VARIABLE_QUOTED"
     fix_applied: "Removed shell quotes from ENV_NAME=dev"
     confidence_healing: 0.85
     verified_at: "2026-05-07T15:02:00Z"
     verification_method: "QG run on next commit"
     verdict: "SUCCESS"
     issue_recurred: false
     new_issues_introduced: 0
     confidence_updated: 0.95 (was 0.85, +0.10 for success)
     notes: "Clean fix. Environment variables now parsing correctly."
   ```

5. CALCULATE fix accuracy metrics
   
   Weekly aggregation:
   
   success_rate = successful_fixes / total_fixes_attempted
   
   // Example:
   // - Total fixes: 14
   // - Successful: 11
   // - Failed: 2
   // - Partial: 1
   // success_rate = 11/14 = 0.786 (78.6%)
   
   // Track by issue type:
   fix_accuracy_by_type = {
     "ENVIRONMENT_VARIABLE_QUOTED": 0.92 (11/12),
     "CDK_RESOURCE_PREFIX_MISSING": 0.75 (3/4),
     "MISSING_REQUIRED_PARAMETER": 0.67 (2/3),
   }
   
   // High-confidence fixes work better?
   correlation_analysis = compare(healing_confidence, actual_success_rate)
   
   IF correlation > 0.80:
     INSIGHT: "Healing Agent confidence scores are well-calibrated"
     RECOMMENDATION: "Trust confidence scores for priority flagging"
   
   IF correlation < 0.60:
     INSIGHT: "Healing Agent confidence is not predictive"
     RECOMMENDATION: "Need more training data or better scoring"

6. IDENTIFY problematic patterns
   
   // Which fixes keep failing?
   FIND: Issues where fix_success_rate < 70%
   
   PATTERN: "CDK_RESOURCE_PREFIX_MISSING has 75% success"
   REASON: "Healing Agent suggests adding default, but doesn't account for all code paths"
   RECOMMENDATION: "Improve fix logic to cover edge cases"
   
   PATTERN: "ENVIRONMENT_VARIABLE_QUOTED has 92% success"
   REASON: "Clear rule, high confidence, easy fix"
   RECOMMENDATION: "Use this as template for similar issues"

7. FEEDBACK to Healing Agent
   
   File: ~/.agents/agentic-engineers/data/healing/feedback-to-healing.yaml
   
   ```yaml
   week_2026_05_07:
     total_fixes_attempted: 14
     total_fixes_verified: 13 (1 inconclusive)
     successful: 11
     failed: 2
     partial: 1
     overall_success_rate: 0.85
     confidence_calibration: "Good (0.82 correlation)"
     
     feedback_by_issue_type:
       - issue: "ENVIRONMENT_VARIABLE_QUOTED"
         success_rate: 0.92
         confidence: 0.90
         feedback: "Excellent fix. Keep current approach."
       
       - issue: "CDK_RESOURCE_PREFIX_MISSING"
         success_rate: 0.75
         confidence: 0.78
         feedback: "Some edge cases failing. Review fix logic for multi-module CDK stacks."
       
       - issue: "MISSING_REQUIRED_PARAMETER"
         success_rate: 0.67
         confidence: 0.60
         feedback: "Low success rate. Consider when to apply vs. escalate to Quality Engineer."
     
     recommendations:
       - "Continue using high-success fixes (ENVIRONMENT_VARIABLE_QUOTED)"
       - "Debug CDK fix failures (73.8 only works, missing 26.2%)"
       - "Escalate MISSING_REQUIRED_PARAMETER to manual review (too risky)"
     
     next_week_goals:
       - "Improve CDK fix success: 75% → 85%"
       - "Reduce escalation rate for MISSING_REQUIRED_PARAMETER"
       - "Maintain high accuracy on ENVIRONMENT_VARIABLE_QUOTED"
   ```

8. TRACK false negatives (should have fixed but didn't)
   
   IF Healing Agent said "issue not auto-fixable" but later found to be fixable:
     MISSED_OPPORTUNITY: Flag for future improvement
     ACTION: Add to escalation rules (this CAN be auto-fixed)
     EXAMPLE: "Could have auto-fixed 3 more issues this week"

9. ESCALATE safety-critical failures
   
   IF fix introduces security vulnerability:
     IMMEDIATE_ALERT: "Auto-fix introduced security issue!"
     SEVERITY: CRITICAL
     ACTION: Revert fix, escalate to Security Engineer
   
   IF fix breaks core functionality:
     ALERT: "Auto-fix caused regression"
     SEVERITY: HIGH
     ACTION: Investigate fix logic, improve specificity

10. PUBLISH weekly fix verification report
    
    File: ~/.agents/agentic-engineers/data/healing/weekly-fix-report.yaml
    
    ```yaml
    week_2026_05_07:
      metrics:
        total_fixes: 14
        success_rate: 0.85
        confidence_calibration: 0.82
        false_negative_rate: 0.07 (issues that could have been auto-fixed)
      
      best_performing_fixes:
        - "ENVIRONMENT_VARIABLE_QUOTED: 92% success"
        - "MAKEFILE_SYNTAX_ERROR: 88% success"
      
      needs_improvement:
        - "MISSING_REQUIRED_PARAMETER: 67% success"
        - "CDK_STACK_ORDER_DEPENDENCY: 75% success"
      
      trend: "↑ Success rate improving (+5% vs last week)"
      
      recommendation: "Continue tuning CDK-related fixes; strong overall accuracy."
    ```
```

## Output: Weekly Fix Verification Report

```yaml
---
handoff_type: CONFIG_ENFORCEMENT_REPORT
period: "week_2026_05_07"
timestamp: 2026-05-12T23:59:00Z

executive_summary:
  total_fixes_attempted: 14
  fixes_verified: 13 (1 inconclusive)
  success_rate: 0.85 (11/13 successful)
  confidence_calibration: "Good (0.82 correlation)"
  trend: "↑ improving"
  recommendation: "Continue current approach; improve CDK fixes"

detailed_results:
  successful_fixes: 11
    - "ENVIRONMENT_VARIABLE_QUOTED: 3/3 (100%)"
    - "MAKEFILE_SYNTAX_ERROR: 2/2 (100%)"
    - "CDK_REGION_MISMATCH: 2/3 (66%)"
    - "IAM_ROLE_MISSING: 2/2 (100%)"
    - "ENV_EXPORT_MISSING: 2/2 (100%)"
  
  failed_fixes: 2
    - "CDK_RESOURCE_PREFIX_MISSING: 1 failure (didn't apply to all stacks)"
    - "MISSING_REQUIRED_PARAMETER: 1 failure (parameter still unset after fix)"
  
  partial_fixes: 1
    - "PARAMETER_VALUE_INVALID: Fixed value but missing validation"

accuracy_by_issue_type:
  - issue: "ENVIRONMENT_VARIABLE_QUOTED"
    attempts: 3
    success: 3
    rate: 1.0 (100%) ✅
    confidence: 0.90
    feedback: "Perfect. Keep using this fix."
  
  - issue: "MAKEFILE_SYNTAX_ERROR"
    attempts: 2
    success: 2
    rate: 1.0 (100%) ✅
    confidence: 0.88
    feedback: "Excellent. Clear syntax rules work well."
  
  - issue: "CDK_RESOURCE_PREFIX_MISSING"
    attempts: 2
    success: 1
    rate: 0.5 (50%)
    confidence: 0.78
    feedback: "NEEDS IMPROVEMENT. Fix misses nested module cases."
    action: "Review CDK fix logic; add multi-module support"
  
  - issue: "MISSING_REQUIRED_PARAMETER"
    attempts: 1
    success: 0
    rate: 0.0 (0%)
    confidence: 0.60
    feedback: "TOO RISKY. Don't auto-fix; escalate to manual review."
    action: "Remove from auto-fix candidates"

confidence_calibration:
  correlation_healing_vs_actual: 0.82 (good)
  interpretation: "Healing confidence scores are predictive of success"
  high_confidence_items:
    - "ENVIRONMENT_VARIABLE_QUOTED (0.90 → 100% success)"
    - "MAKEFILE_SYNTAX_ERROR (0.88 → 100% success)"
  low_confidence_items:
    - "MISSING_REQUIRED_PARAMETER (0.60 → 0% success)"
  recommendation: "Confidence scoring is well-calibrated; trust for prioritization"

safety_analysis:
  security_regressions: 0 (clean)
  functionality_regressions: 0 (clean)
  false_positives: 0 (no unneeded fixes)
  false_negatives: 1 (one fix marked unautomatable but was)
  incidents: 0 (no critical failures)

trend_analysis:
  success_rate_trend: "↑ +5% vs last week (80% → 85%)"
  confidence_calibration_trend: "stable (0.80-0.85 range)"
  issue_frequency_trend: "↓ -15% (fewer auto-fixable issues, good!)"
  recommendation: "System improving. Config quality better."

feedback_to_healing_agent:
  action: "Update fix confidence scores"
  changes:
    - "ENVIRONMENT_VARIABLE_QUOTED: 0.90 → 0.95 (+0.05 for perfect week)"
    - "MAKEFILE_SYNTAX_ERROR: 0.88 → 0.92 (+0.04)"
    - "CDK_RESOURCE_PREFIX_MISSING: 0.78 → 0.70 (-0.08 for failures)"
    - "MISSING_REQUIRED_PARAMETER: 0.60 → 0.40 (-0.20, remove from auto-fix)"

next_week_improvements:
  action_items:
    - "Fix CDK_RESOURCE_PREFIX_MISSING logic (multi-module support)"
    - "Remove MISSING_REQUIRED_PARAMETER from auto-fix candidates"
    - "Celebrate 100% success on ENVIRONMENT_VARIABLE_QUOTED"
  
  success_targets:
    - "Overall success rate: 85% → 90%"
    - "CDK fixes: 50% → 80%"
    - "Zero regressions (maintain)"

report_confidence: 0.94
---
```

## Data Schema: Fix History

```yaml
# File: ~/.agents/agentic-engineers/data/healing/fix-history.yaml
fixes:
  - id: "healing-2026-05-07-001"
    timestamp: "2026-05-07T14:35:00Z"
    issue_type: "ENVIRONMENT_VARIABLE_QUOTED"
    fix_applied: "Removed quotes from ENV_NAME=dev"
    healing_confidence: 0.90
    verified_at: "2026-05-07T15:02:00Z"
    verdict: "SUCCESS"
    issue_recurred: false
    new_issues: 0
    confidence_adjusted: 0.95
    notes: "Clean fix"
  
  - id: "healing-2026-05-07-002"
    timestamp: "2026-05-07T15:10:00Z"
    issue_type: "CDK_RESOURCE_PREFIX_MISSING"
    fix_applied: "Added default CDK_RESOURCE_PREFIX"
    healing_confidence: 0.78
    verified_at: "2026-05-07T16:30:00Z"
    verdict: "PARTIAL"
    issue_recurred: true
    new_issues: 0
    confidence_adjusted: 0.70
    notes: "Fix didn't apply to nested modules; need multi-module support"
```

## Integration Points

**Input:**
- Healing Agent (fix suggestions and confidence scores)
- Quality Gate Orchestrator (next QG run results)
- Fix history (previous fixes applied)

**Output:**
- Fix verification report (weekly)
- Feedback to Healing Agent (confidence adjustments)
- Safety alerts (if regressions detected)
- Accuracy metrics (JSON)

**Feedback Loops:**
- Fix applied → Wait for verification → Judge success → Update Healing Agent confidence → Improve future fixes

## Success Criteria

- ✅ Fix verification (confirmed issue resolved)
- ✅ Regression detection (new issues didn't appear)
- ✅ Success rate tracking (% of fixes that work)
- ✅ Confidence calibration (high confidence = high success?)
- ✅ Pattern identification (which fixes work best?)
- ✅ Safety validation (no security/functionality regressions)
- ✅ Feedback to Healing Agent (confidence score updates)

## Phase 6.1 Integration

Part of three-pronged feedback loop:
1. **Model Engineer** — Model optimization
2. **Quality Gate Aggregator** — Trend analysis
3. **Config Enforcement Verifier** (this file) — Auto-fix validation
