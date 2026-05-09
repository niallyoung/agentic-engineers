---
name: Healing Agent Implementation
type: agent-implementation
phase: 5.10
---

# Healing Agent — LIVE IMPLEMENTATION

**Role**: Senior Engineer  
**Model**: claude-sonnet-4-6  
**Effort**: high

## Agent Logic

```
WHEN Orchestrator writes DELEGATE to artifacts/:

1. READ: DELEGATE block + issues from other agents
   repo_path = /home/user/git/ers/{service}
   issues = [issues from Security, Testing, Metrics agents]

2. FOR EACH issue, attempt auto-fix:
   
   IF issue.type == "lint_error":
     - Attempt: Auto-format code (go fmt, prettier)
     - Verify: Run make lint again
     - confidence = 0.95 if fixed, 0.30 if not
   
   ELIF issue.type == "test_failure":
     - Analyze: What's the test expecting?
     - Attempt: Fix test or fix code
     - Verify: Run make test again
     - confidence = 0.70 if fixed (might be fragile)
   
   ELIF issue.type == "config_issue":
     - Attempt: Fix env var, Makefile, CDK config
     - Verify: make verify succeeds
     - confidence = 0.92 if fixed
   
   ELIF issue.type == "dependency_issue":
     - Attempt: Update dependency version
     - Verify: Builds and tests pass
     - confidence = 0.60 (risky, might break things)
   
   ELSE:
     - Escalate: Can't auto-fix this
     - confidence = 0.0
     - Store in escalations[]

3. TRACK RESULTS:
   auto_fixes_attempted = count(all attempted fixes)
   auto_fixes_succeeded = count(fixes that passed verification)
   auto_fixes_failed = auto_fixes_attempted - auto_fixes_succeeded
   escalations = [unfixable_issues]
   confidence_per_fix = [confidence scores for each attempt]

4. DETERMINE STATUS:
   IF escalations.length > 0:
     status = "PASS_WITH_ESCALATIONS"
     severity = "MEDIUM"
   ELSE IF auto_fixes_failed > 0:
     status = "PARTIAL_SUCCESS"
     severity = "LOW"
   ELSE:
     status = "PASS"
     severity = "PASS"
   
   confidence = mean(confidence_per_fix) if auto_fixes else 0.95

5. WRITE HANDBACK:
   HANDBACK = {
     handoff_type: "HANDBACK",
     task_id: ...,
     status: status,
     auto_fixes_attempted: auto_fixes_attempted,
     auto_fixes_succeeded: auto_fixes_succeeded,
     auto_fixes_failed: auto_fixes_failed,
     escalations: escalations,
     confidence_per_fix: confidence_per_fix,
     confidence: confidence,
     severity: severity,
     warnings: [any_warnings],
     recommendation: "Ready to merge" if status == PASS else ...
   }

6. WRITE SPAN to artifacts/SPAN-{timestamp}-agent-healing.yaml
```

## HANDBACK Format

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-26-commit-{service-name}
timestamp: 2026-05-26T09:03:15Z
status: PASS
auto_fixes_attempted: 3
auto_fixes_succeeded: 2
auto_fixes_failed: 1
escalations:
  - type: "flaky_test"
    description: "Test timing-dependent, needs refactoring"
confidence_per_fix: [0.95, 0.92, 0.45]
confidence: 0.77
severity: PASS
warnings:
  - "Fix #3 has low confidence, may need human review"
recommendation: "2 out of 3 fixes applied. 1 issue escalated for review."
```

## Key Principle

**High-confidence fixes (≥ 0.8) are applied automatically.**  
**Low-confidence fixes (< 0.8) are escalated for human review.**

This prevents breaking changes while still delivering value through auto-fixes.
