---
name: Testing Agent Implementation
type: agent-implementation
phase: 5.10
---

# Testing Agent — LIVE IMPLEMENTATION

**Role**: Engineer  
**Model**: claude-haiku-4-5  
**Effort**: medium (downgraded from Sonnet for cost optimization)

**Why Haiku**: Structured output parsing (make test) is mechanical. Haiku excels at this.
**Cost savings**: 78% reduction (Sonnet $0.154 → Haiku $0.034)

## Agent Logic

```
WHEN Orchestrator writes DELEGATE to artifacts/:

1. READ: DELEGATE block
   repo_path = $WORKSPACE_ROOT/{service}
   cd repo_path

2. RUN TESTS:
   Execute: make test
   Capture: all output, return codes
   
   Parse output:
   - unit_tests = count of unit test cases
   - unit_test_failures = count of failures
   - e2e_tests = count of E2E test cases
   - e2e_test_failures = count of failures
   - flaky_tests = tests that fail intermittently
   
3. CALCULATE COVERAGE:
   From test reports or code analysis:
   coverage_percent = (lines_covered / total_lines) * 100
   
   Warn if coverage < 80%
   Fail if coverage < 60%

4. DETERMINE STATUS:
   status = "PASS" if unit_test_failures == 0 AND e2e_test_failures == 0
   
   confidence = 0.95 if all_pass else 0.70 + (1.0 - failure_ratio) * 0.25

5. WRITE HANDBACK:
   HANDBACK = {
     handoff_type: "HANDBACK",
     task_id: ...,
     status: status,
     unit_tests: unit_tests,
     unit_test_failures: unit_test_failures,
     e2e_tests: e2e_tests,
     e2e_test_failures: e2e_test_failures,
     coverage_percent: coverage_percent,
     flaky_tests: flaky_tests,
     confidence: confidence,
     severity: "PASS" if status == "PASS" else "HIGH"
   }

6. WRITE SPAN to artifacts/SPAN-{timestamp}-agent-testing.yaml
```

## HANDBACK Format

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-26-commit-{example-service}-abc123-testing
timestamp: 2026-05-26T09:04:20Z
status: PASS  # or FAIL
unit_tests: 45
unit_test_failures: 0
e2e_tests: 12
e2e_test_failures: 0
coverage_percent: 87.3
flaky_tests: 0
severity: PASS
confidence: 0.95
recommendation: "All tests passing with good coverage"
```
