---
name: requirement-verification
description: Pre-deployment gate — verify all requirements have passing tests before deploy
type: skill
version: 1.0
track: compliance
---

# requirement-verification

Pre-deployment quality gate. Uses requirement-mapping output to verify every requirement
has tests and all tests are passing. Blocks deployment if critical requirements are untested
or have failing tests.

## Usage

```
/requirement-verification service_path={service-name} deployment_target=prod
/requirement-verification service_path={service-name} deployment_target=dev fail_on_uncovered=false
/requirement-verification service_path={service-name}  # uses prod defaults
```

## Input

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `service_path` | str | required | Path to service root |
| `deployment_target` | str | `prod` | Target environment: `dev`, `staging`, `prod` |
| `fail_on_uncovered` | bool | true | BLOCK if any requirement has no tests |
| `fail_on_failing_tests` | bool | true | BLOCK if any requirement test is failing |
| `mapping_result` | dict | null | Pre-computed requirement-mapping output (skip re-run) |

## Output

```json
{
  "service": "{service-name}",
  "deployment_target": "prod",
  "requirements_total": 15,
  "requirements_tested": 14,
  "requirements_untested": 1,
  "requirements_all_passing": 13,
  "requirements_with_failures": 1,
  "coverage_percent": 86.7,
  "gate_result": "WARN",
  "issues": [
    {
      "requirement_id": "REQ-003-membership-states",
      "issue_type": "failing_test",
      "test_name": "TestMembershipTransition_CancelledToActive",
      "test_file": "handlers/membership_test.go:203",
      "error": "expected status 422, got 200",
      "severity": "HIGH",
      "remediation": "Fix handler to reject cancelled→active transition or update test"
    },
    {
      "requirement_id": "REQ-005-audit-logging",
      "issue_type": "no_tests",
      "severity": "MEDIUM",
      "remediation": "Add tests for admin action audit logging"
    }
  ],
  "deployment_recommendation": "WARN — fix 1 failing test before prod deployment"
}
```

`gate_result`: `PASS` | `WARN` | `BLOCK`

## Implementation

### Step 1: Get Requirement Mapping

```pseudo
func get_mapping(service_path, mapping_result):
  if mapping_result is provided:
    return mapping_result  # reuse from quality gate orchestrator
  
  # Run requirement-mapping skill
  return invoke_skill("requirement-mapping", {
    service_path: service_path,
    include_orphaned_code: false  # not needed for verification
  })
```

### Step 2: Verify Each Requirement

```pseudo
func verify_requirements(mapping, deployment_target):
  issues = []
  
  for req in mapping.requirements:
    # Check 1: Does the requirement have tests?
    if req.test_count == 0:
      issues.append({
        requirement_id: req.id,
        issue_type: "no_tests",
        severity: classify_severity(req, deployment_target),
        remediation: f"Add tests for: {req.description}"
      })
      continue
    
    # Check 2: Are all tests passing?
    if not req.all_tests_passing:
      for failing_test in req.failing_tests:
        issues.append({
          requirement_id: req.id,
          issue_type: "failing_test",
          test_name: failing_test.name,
          test_file: failing_test.file,
          error: failing_test.error,
          severity: classify_severity(req, deployment_target),
          remediation: "Fix test or update requirement to match implementation"
        })
  
  return issues
```

### Step 3: Severity Classification

```pseudo
func classify_severity(requirement, deployment_target):
  # prod is strictest
  if deployment_target == "prod":
    if requirement.tags contains ["security", "auth", "permissions"]:
      return "CRITICAL"
    if requirement.tags contains ["data-integrity", "state-machine"]:
      return "HIGH"
    return "MEDIUM"
  
  if deployment_target == "staging":
    # One level lower than prod
    return downgrade(classify_severity(requirement, "prod"))
  
  # dev: most lenient
  return "LOW"
```

### Step 4: Gate Decision

```pseudo
func make_gate_decision(issues, fail_on_uncovered, fail_on_failing_tests, deployment_target):
  critical_issues = [i for i in issues if i.severity == "CRITICAL"]
  high_issues = [i for i in issues if i.severity == "HIGH"]
  failing_tests = [i for i in issues if i.issue_type == "failing_test"]
  no_test_reqs = [i for i in issues if i.issue_type == "no_tests"]
  
  # Always block on critical
  if critical_issues:
    return "BLOCK", "Critical requirement issues found"
  
  # Block on high severity for prod
  if deployment_target == "prod" and high_issues:
    return "BLOCK", f"{len(high_issues)} HIGH severity issues"
  
  # Configurable: block on failing tests
  if fail_on_failing_tests and failing_tests:
    return "BLOCK", f"{len(failing_tests)} requirements have failing tests"
  
  # Configurable: block on uncovered requirements
  if fail_on_uncovered and no_test_reqs:
    return "WARN", f"{len(no_test_reqs)} requirements have no tests"
  
  if issues:
    return "WARN", "Some issues found — review before deployment"
  
  return "PASS", "All requirements verified"
```

### Step 5: Generate Recommendations

```pseudo
func generate_deployment_recommendation(gate_result, issues, deployment_target):
  if gate_result == "PASS":
    return f"PROCEED — all {requirements_total} requirements verified for {deployment_target}"
  
  if gate_result == "BLOCK":
    critical = [i for i in issues if i.severity in ["CRITICAL", "HIGH"]]
    return f"BLOCK — {len(critical)} critical issues must be resolved before {deployment_target} deployment"
  
  if gate_result == "WARN":
    return f"WARN — {len(issues)} issues found; acceptable for {deployment_target} but should be addressed"
```

## Deployment Target Strictness

| Target | Failing Tests | No Tests | Orphaned Code |
|--------|--------------|----------|---------------|
| `dev` | WARN | INFO | ignore |
| `staging` | WARN | WARN | WARN |
| `prod` | BLOCK | WARN/BLOCK | WARN |

For `prod`, security/auth requirements with no tests → BLOCK.

## ERS Pre-Deployment Checklist

Before deploying any ERS service to prod, this skill verifies:

1. **Auth requirements** (REQ-*-auth, REQ-*-jwt): Must have tests + all passing
2. **State machine requirements** (membership, user roles): Must have transition tests
3. **Data integrity requirements** (event-first ordering): Must have integration tests
4. **API contract requirements**: All handler endpoints must have tests

### Command-Line Integration

```bash
# Run as part of pre-push gate:
# (called by pre-push hook in {service-name}/githooks/pre-push)

requirement-verification \
  --service-path . \
  --deployment-target prod \
  --fail-on-uncovered \
  --fail-on-failing-tests
```

Exit codes:
- `0` → PASS
- `1` → WARN
- `2` → BLOCK

### CI Integration (GitHub Actions)

```yaml
# In .github/workflows/main.yaml:
- name: Verify Requirements
  run: |
    claude -p "$(cat <<'EOF'
    /requirement-verification service_path=. deployment_target=prod
    EOF
    )"
  # Block deployment if exit code != 0
```

## Integration

- Calls `requirement-mapping` if mapping not provided
- Called by `quality-gate-orchestration` in compliance phase
- Issues feed `issue-diagnostic-engine` for root cause analysis
- Failing test issues may be auto-fixed by `healer-engineer`
- No-test issues become tracked backlog items

## Success Criteria

- Verify all requirements for {service-name} before prod deploy
- BLOCK deployment if any auth/security requirement has failing test
- WARN (not BLOCK) if non-critical requirement has no tests
- Provide actionable remediation for every issue found
