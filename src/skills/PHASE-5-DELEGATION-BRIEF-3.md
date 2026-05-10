---
name: Phase 5.4 — Engineer 3 Track (Compliance Skills)
description: Build 3 compliance skills for requirement traceability and spec verification
type: delegation-brief
version: 1.0
date: 2026-04-27
---

# Phase 5.4: Engineer 3 Track — Compliance & Requirement Traceability Skills

**Delegation**: Engineer 3 (Sonnet)  
**Timeline**: 1.5 days  
**Blocking**: None — foundational track  
**Deliverables**: 3 skill .md files + git commits

---

## Skills to Build

### 8. requirement-mapping.md
**Purpose**: Map requirements to tests to code, calculate coverage %

**Input Spec**:
```
service_path: str
spec_file: str  # path to requirement spec (YAML, JSON, or Markdown)
requirement_id: str = None  # specific requirement or None for all
```

**Output Spec**:
```json
{
  "service": "{example-service}",
  "spec_file": "specs/{example-service}-requirements.yaml",
  "requirements_total": 15,
  "requirements_covered": 13,
  "coverage_percent": 86.7,
  "mappings": [
    {
      "requirement_id": "REQ-001-user-role-admin",
      "description": "Admin users can approve/reject events",
      "test_count": 3,
      "tests": [
        "handlers_test.go::TestAdminApproveEvent",
        "handlers_test.go::TestAdminRejectEvent",
        "models_test.go::TestUserRoleTransition"
      ],
      "code_files": [
        "handlers.go:AdminApprovalHandler (line 142)",
        "models.go:User.IsAdmin (line 87)"
      ],
      "test_coverage": "100%",
      "status": "COMPLETE"
    },
    {
      "requirement_id": "REQ-002-event-validation",
      "description": "All events validated before publication",
      "test_count": 2,
      "tests": ["event_test.go::TestValidateEvent"],
      "code_files": ["event.go:ValidateEvent"],
      "test_coverage": "80%",
      "status": "COMPLETE"
    }
  ],
  "unmapped_requirements": [
    {
      "requirement_id": "REQ-005-audit-logging",
      "description": "All actions logged for audit trail",
      "reason": "No tests found"
    }
  ],
  "orphaned_code": [
    {
      "file": "handlers.go:LegacyApprovalHandler",
      "reason": "No requirement found; no tests found"
    }
  ],
  "execution_time_sec": 18
}
```

**Implementation Notes**:
- Spec format support: YAML, JSON, or Markdown with front matter
- Spec parsing: extract `requirement_id`, `description` pairs
- Test discovery: scan `*_test.go` (Go), `*.test.js` (Node), etc.; grep for requirement ID in test names
- Code tracing: run test with code coverage; parse coverage output to find code files exercised by tests
- Coverage calculation: (tests passing) / (tests written for requirement) × 100%
- Orphaned code detection: grep codebase for functions with no requirement ID and no test coverage
- Output: comprehensive mapping for audit trail

**Success Criteria**:
✓ Map REQ-001 to 3+ tests in {example-service}  
✓ Calculate coverage % correctly  
✓ Identify unmapped requirements  
✓ Identify orphaned code (if any)  
✓ Support YAML and JSON spec formats

**Related Specs**:
- QUALITY-ENGINEER-DESIGN.md § Decision 3 (Requirement Traceability)
- PHASE-5-SKILL-SPECIFICATIONS.md § Skill 8

---

### 9. requirement-verification.md
**Purpose**: Pre-deployment gate: verify all requirements have passing tests

**Input Spec**:
```
service_path: str
deployment_target: str = "prod"  # dev, staging, prod
fail_on_uncovered: bool = True
```

**Output Spec**:
```json
{
  "service": "{example-service}",
  "deployment_target": "prod",
  "requirements_total": 15,
  "requirements_tested": 14,
  "requirements_untested": 1,
  "requirements_all_passing": 13,
  "requirements_has_failing": 1,
  "gate_result": "WARN",  // or "BLOCK", "PASS"
  "issues": [
    {
      "requirement_id": "REQ-003-event-approval",
      "description": "Event approval workflow",
      "test_status": "1 FAILING",
      "failing_tests": [
        {
          "test_name": "test_event_approval_permission",
          "failure_reason": "Expected: user can approve | Actual: permission_denied"
        }
      ],
      "remediation": "Fix test or requirement; if intentional, update requirement"
    },
    {
      "requirement_id": "REQ-005-audit-logging",
      "description": "All actions logged for audit trail",
      "test_status": "UNTESTED",
      "failing_tests": [],
      "remediation": "Write test for audit logging requirement"
    }
  ],
  "deployment_recommendation": "WARN: Fix 1 failing test before prod deployment",
  "execution_time_sec": 12
}
```

**Implementation Notes**:
- Input: use requirement-mapping output as baseline (previous skill)
- Execution: run all tests for each requirement
- Parse test output: identify passing vs. failing tests per requirement
- Gate logic:
  - All requirements tested + all passing → gate_result: "PASS"
  - Any requirement untested → gate_result: "WARN" (or "BLOCK" if fail_on_uncovered)
  - Any requirement has failing test → gate_result: "WARN" (never "PASS")
- Deployment recommendation: suggest remediation for each issue
- Escalation: BLOCK gates prevent deployment; WARN allows human review

**Success Criteria**:
✓ Verify all requirements in {example-service} have tests  
✓ Report any failing tests per requirement  
✓ Gate decision: proceed only if all green  
✓ Suggest remediation for each failing requirement

**Related Specs**:
- QUALITY-ENGINEER-DESIGN.md § Decision 3 (Requirement Traceability)
- PHASE-5-SKILL-SPECIFICATIONS.md § Skill 9

---

### 10. spec-compliance-verification.md
**Purpose**: Verify code complies with extracted specs ({workspace-name}/specs/*)

**Input Spec**:
```
service_path: str
spec_dir: str = "{workspace-name}/specs"
```

**Output Spec**:
```json
{
  "service": "{example-service}",
  "specs_total": 8,
  "specs_compliant": 7,
  "compliance_percent": 87.5,
  "deviations": [
    {
      "spec_id": "SPEC-P-003",
      "spec_name": "GitHub Actions main.yaml structure",
      "pattern": "main.yaml must have: [lint, test, build, deploy]",
      "expected": "Deploy step depends on test success",
      "actual": "Deploy runs after test (correct)",
      "deviation": "PASS"
    },
    {
      "spec_id": "SPEC-M-001",
      "spec_name": "Makefile pattern",
      "pattern": "Must have: [describe, lint, test, build, deploy] targets",
      "expected": "describe target outputs build metadata",
      "actual": "describe outputs git sha + version",
      "deviation": "MINOR - comment says 'git sha' but does not include version metadata"
    }
  ],
  "compliance_status": "PASS",  // or "WARN" if deviations
  "execution_time_sec": 8
}
```

**Implementation Notes**:
- Load extracted specs from `{workspace-name}/specs/*.yaml`
- Spec structure: each spec defines a pattern + expected behavior
- Compliance check: for each spec, verify service implementation matches pattern
- Deviation types: PASS (compliant), MINOR (style/comment), WARN (functional), FAIL (breaks spec)
- Check areas:
  - Makefile structure (describe, lint, test, build, deploy targets)
  - GitHub Actions structure (main.yaml, branch.yaml)
  - CDK stack pattern (3-tier: resources, functions, integrations)
  - Test coverage thresholds
- Integration: works with spec-audit skill (from Phase 4)

**Success Criteria**:
✓ Verify {example-service} Makefile follows spec pattern  
✓ Verify GitHub Actions spec compliance  
✓ Report deviations with severity  
✓ Support YAML spec format

**Related Specs**:
- PHASE-5-SKILL-SPECIFICATIONS.md § Skill 10

---

## Integration Points

**Inputs from Previous Tracks**:
- Test results from Track 1 (test coverage feeds requirement mapping)
- Requirement coverage from Track 1 unit/integration tests

**Outputs for Later Tracks**:
- Requirement mapping output feeds into `issue-diagnostic-engine.md` (track 4)
- Requirement verification gate feeds quality orchestrator (track 5)
- Spec compliance feeds quality orchestrator (track 5)

**Success Criteria for Track**:
- All 3 skills implemented + tested locally
- Each skill callable as independent module or CLI
- Output JSON matches spec exactly
- Requirement mapping works with real ERS requirements
- Requirement verification gates deploy decisions

---

## Implementation Steps

1. **Create skill files** (hours 0-2):
   - requirement-mapping.md
   - requirement-verification.md
   - spec-compliance-verification.md

2. **Implement in parallel** (hours 2-24):
   - requirement-mapping: spec parsing + test discovery + code tracing
   - requirement-verification: test execution + gate logic
   - spec-compliance-verification: spec parsing + pattern matching
   - Test with real ERS requirements

3. **Validate** (hours 24-28):
   - Run requirement-mapping on {example-service}
   - Run requirement-verification with passing + failing tests
   - Run spec-compliance-verification on all services

4. **Git commit**:
   - One commit per skill file: `feat(skills): add requirement-mapping skill`

---

## Success Definition

Track is complete when:
- [ ] All 3 .md skill files created in `/skills/`
- [ ] Each file includes: purpose, input spec, output spec, implementation notes
- [ ] requirement-mapping finds real requirements + maps to tests
- [ ] requirement-verification gates deployment correctly
- [ ] spec-compliance-verification reports accurate deviations
- [ ] All output JSON matches spec
- [ ] All 3 committed to git with clear messages
- [ ] Ready to integrate with Track 4 (diagnostic engine)

---

**Version**: 1.0  
**Status**: Ready for delegation  
**Owner**: Engineer 3 (Sonnet)  
**Start Date**: 2026-04-27  
**Target Date**: 2026-04-29
