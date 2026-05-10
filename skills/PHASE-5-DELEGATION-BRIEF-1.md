---
name: Phase 5.2 — Engineer 1 Track (Testing Skills)
description: Build 4 testing orchestration skills for unit, integration, E2E, and business logic
type: delegation-brief
version: 1.0
date: 2026-04-27
---

# Phase 5.2: Engineer 1 Track — Testing Orchestration Skills

**Delegation**: Engineer 1 (Sonnet)  
**Timeline**: 1.5 days  
**Blocking**: None — foundational track  
**Deliverables**: 4 skill .md files + git commits

---

## Skills to Build

### 1. test-unit-orchestration.md
**Purpose**: Discover, execute, and report unit tests with coverage analysis

**Input Spec**:
```
service_path: str           # path to service (e.g., $WORKSPACE_ROOT/{example-service})
test_filter: str = None     # optional glob pattern (e.g., "*/auth/*_test.go")
coverage_threshold: int = 80  # min coverage %
fail_on_below_threshold: bool = True
```

**Output Spec**:
```json
{
  "service": "{example-service}",
  "tests_found": 42,
  "tests_passed": 40,
  "tests_failed": 2,
  "coverage_percent": 82.5,
  "coverage_status": "PASS",  // or "FAIL"
  "failed_tests": [
    {
      "test_name": "TestUserCreation",
      "error": "expected user ID to be non-empty"
    }
  ],
  "mutation_recommendations": [
    "test edge case: negative user ID",
    "test boundary: max string length for email"
  ]
}
```

**Implementation Notes**:
- Language detection: Go (go test), Node (jest), Python (pytest)
- Test discovery: `find /path -name "*_test.go"` for Go, `find /path -name "*.test.js"` for Node
- Execute: `make test` or `npm test` or equivalent
- Coverage parsing: `go tool cover`, jest coverage reporter
- Return failed tests for diagnostic engine input
- Mutation recommendations: identify untested edge cases from coverage gaps

**Success Criteria**:
✓ Discover >30 unit tests in {example-service}  
✓ Report coverage >=80% (actual coverage for {example-service} is ~82%)  
✓ Identify failed tests correctly  
✓ Output matches spec exactly (JSON)

**Related Specs**:
- PHASE-5-SKILL-SPECIFICATIONS.md § Skill 1

---

### 2. test-integration-orchestration.md
**Purpose**: Run integration tests with service mocking (DynamoDB, SNS, Lambda events)

**Input Spec**:
```
service_path: str
environment: str = "test"  # dev, staging, test
test_filter: str = None
mock_dynamodb: bool = True
mock_eventbridge: bool = True
mock_sns: bool = True
```

**Output Spec**:
```json
{
  "service": "{service-name}",
  "integration_tests": 15,
  "passed": 13,
  "failed": 2,
  "skipped": 0,
  "failed_tests": [
    {
      "test_name": "test_event_fanout_to_members",
      "error": "SNS mock not receiving messages"
    }
  ],
  "mocks_used": ["DynamoDB", "SNS"],
  "execution_time_sec": 42.5
}
```

**Implementation Notes**:
- Service mocking strategy: localstack (Docker) or serverless-offline for Lambda
- DynamoDB: use local instance or mock library (moto for Python, aws-sdk-go test utilities)
- SNS/SQS: mock via test fixtures or localstack
- Set up test fixtures: seed data, pre-publish test events
- Execution: run from Makefile (make integration-test) or language-specific runner
- Fail fast if critical mocks unavailable

**Success Criteria**:
✓ Mock DynamoDB for {service-name} tests  
✓ Mock SNS for event consumer tests  
✓ Report which mocks were used  
✓ Execution time reasonable (<60s per service)

**Related Specs**:
- PHASE-5-SKILL-SPECIFICATIONS.md § Skill 2

---

### 3. test-e2e-orchestration.md
**Purpose**: Orchestrate Playwright E2E tests with filtering and parallelization

**Input Spec**:
```
scenario_filter: str = None  # optional: "login", "create_event", etc.
headless: bool = True
trace_on_failure: bool = True
parallel_workers: int = 2
```

**Output Spec**:
```json
{
  "scenarios_found": 8,
  "scenarios_run": 3,  // filtered
  "passed": 3,
  "failed": 0,
  "execution_time_sec": 125,
  "traces": [
    {
      "scenario": "login",
      "status": "PASSED",
      "trace_file": null
    }
  ]
}
```

**Implementation Notes**:
- Scan: `find {service-name}/e2e -name "*.spec.ts"` (Playwright convention)
- Parse test names: extract scenario identifiers (e.g., "test_login_success" → "login")
- Filtering: regex match on scenario name
- Parallelization: `--workers=N` in playwright config
- Capture trace on failure: `--trace=on`
- Video capture optional but recommended

**Success Criteria**:
✓ Discover Playwright tests in {service-name}  
✓ Filter by scenario name  
✓ Run in parallel (2 workers)  
✓ Report traces for failed scenarios

**Related Specs**:
- PHASE-5-SKILL-SPECIFICATIONS.md § Skill 3

---

### 4. test-business-logic.md
**Purpose**: Parametric testing of business logic, edge cases, and state machines

**Input Spec**:
```
service_path: str
business_logic_spec: dict  # Example:
# {
#   "requirement": "REQ-001-user-role-admin",
#   "edge_cases": [
#     {"input": "user_role=admin, event_type=calendar", "expect": "can_approve"},
#     {"input": "user_role=member, event_type=calendar", "expect": "cannot_approve"}
#   ],
#   "state_transitions": [
#     {"from": "member", "to": "admin", "expect": "success"},
#     {"from": "admin", "to": "disabled", "expect": "success"}
#   ]
# }
state_machine_transitions: dict = None
```

**Output Spec**:
```json
{
  "requirement": "REQ-001-user-role-admin",
  "edge_cases_tested": 12,
  "passed": 11,
  "failed": 1,
  "uncovered_transitions": ["disabled -> active"],
  "data_interactions": {
    "user_role_change": "OK",
    "event_creation_with_new_role": "FAIL"
  },
  "failed_case": {
    "input": "user_role=admin, event_type=calendar",
    "expected": "can_approve",
    "actual": "permission_denied"
  }
}
```

**Implementation Notes**:
- Parse requirement spec (from requirement-mapping output or spec file)
- Generate test variations: all combinations of inputs (user roles, event types, permissions)
- Execute parametric tests: iterate through edge_cases, assert expected output
- State machine testing: verify all transitions work (member → admin → disabled)
- Data consistency check: after role change, verify side effects (e.g., event approvals cascade)
- Report uncovered transitions (gaps in test coverage)

**Success Criteria**:
✓ Test user role transitions (member → admin → disabled)  
✓ Identify permission edge cases  
✓ Report data consistency issues  
✓ Suggest missing test cases

**Related Specs**:
- PHASE-5-SKILL-SPECIFICATIONS.md § Skill 4

---

## Integration Points

**After This Track**:
- Test results feed into `issue-diagnostic-engine.md` (track 4)
- Test coverage data feeds into `requirement-mapping.md` (track 3)
- Test failures inform `healer-engineer.md` (track 4)

**Success Criteria for Track**:
- All 4 skills implemented + tested locally
- Each skill callable as independent Python module or CLI
- Output JSON matches spec exactly
- No external dependencies missing (Playwright, localstack, etc.)

---

## Implementation Steps

1. **Create skill files** (this session or first 2 hours):
   - test-unit-orchestration.md
   - test-integration-orchestration.md
   - test-e2e-orchestration.md
   - test-business-logic.md

2. **Implement in parallel** (hours 2-20):
   - Each skill as standalone Python class (recommended) or CLI script
   - Implement output to match JSON spec
   - Test with real {example-service}, {service-name}, {service-name} services

3. **Validate** (hours 20-24):
   - Run each skill against actual codebase
   - Verify coverage calculations
   - Check integration inputs from Track 3 (requirement-mapping)

4. **Git commit**:
   - One commit per skill file: `feat(skills): add test-unit-orchestration skill`
   - Conventional commits required
   - Commit message includes success criteria met

---

## Success Definition

Track is complete when:
- [ ] All 4 .md skill files created in `/skills/`
- [ ] Each file includes: purpose, input spec, output spec, implementation notes
- [ ] Local testing proves each skill works against real ERS service
- [ ] Output JSON format matches spec exactly
- [ ] All 4 committed to git with clear messages
- [ ] No blocking issues preventing integration in next tracks

---

**Version**: 1.0  
**Status**: Ready for delegation  
**Owner**: Engineer 1 (Sonnet)  
**Start Date**: 2026-04-27  
**Target Date**: 2026-04-29
