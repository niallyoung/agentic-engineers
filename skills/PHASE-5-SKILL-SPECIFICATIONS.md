---
name: Phase 5 Skill Specifications — Complete Build Guide
description: Detailed specifications for all 12 Quality Engineer + Self-Healing skills
type: implementation-guide
version: 1.0
date: 2026-04-27
---

# Phase 5: 12 Skills — Complete Specifications

## Quick Reference

| # | Skill | Purpose | Owner | Days | Blocking |
|---|-------|---------|-------|------|----------|
| 1 | test-unit-orchestration | Unit test discovery + execution + coverage | Eng1 | 1 | Design |
| 2 | test-integration-orchestration | Integration tests + ERS mocking | Eng1 | 1 | Design |
| 3 | test-e2e-orchestration | Playwright E2E scenario filtering | Eng1 | 0.5 | Design |
| 4 | test-business-logic | Parametric + edge case + state machine tests | Eng2 | 1 | Design |
| 5 | security-semantic-scan | Claude data flow analysis + verification | SecEng | 1 | Design |
| 6 | security-dependency-scan | go vuln + npm audit + cargo check | Eng2 | 0.5 | Design |
| 7 | security-secret-detection | Hardcoded creds + API keys | SecEng | 0.5 | Design |
| 8 | requirement-mapping | REQ → test → code traceability | Eng3 | 0.75 | Design |
| 9 | requirement-verification | Pre-deploy requirement gate | Eng3 | 0.5 | Design |
| 10 | spec-compliance-verification | Verify against extracted specs | Eng3 | 0.5 | Design |
| 11 | issue-diagnostic-engine | Root cause + confidence scoring | Lead | 1 | Design |
| 12 | healer-engineer | Auto-fix low-risk issues + PR | Lead | 0.5 | Design |
| - | quality-gate-orchestration | Master orchestrator + self-healing loop | Principal | 1 | All above |
| - | Documentation + Integration | SKILLS-INDEX, role defs, examples | Senior | 0.75 | All skills |

---

## Skill 1: test-unit-orchestration.md

**Purpose**: Orchestrate unit test discovery, execution, coverage reporting

**Input**:
```
service_path: str           # path to service
test_filter: str = None     # optional glob pattern (e.g., "*/auth/*_test.go")
coverage_threshold: int = 80  # min coverage %
fail_on_below_threshold: bool = True
```

**Output**:
```
{
  "service": "{service-name}",
  "tests_found": 42,
  "tests_passed": 40,
  "tests_failed": 2,
  "coverage_percent": 82.5,
  "coverage_status": "PASS",
  "failed_tests": [...],
  "mutation_recommendations": ["test edge case: negative user ID", ...]
}
```

**Implementation Notes**:
- Detect test framework (go test, jest, pytest, etc.)
- Discover tests via `find`, `grep`, or language-specific tools
- Execute: `make test` or `npm test` or language equivalent
- Parse coverage output (go tool cover, jest coverage, etc.)
- Report coverage % and pass/fail status
- Return failed test list for diagnostic engine

**Success Criteria**:
- Discover >30 tests in {service-name}
- Report coverage >=80%
- Identify failed tests correctly

---

## Skill 2: test-integration-orchestration.md

**Purpose**: Run integration tests with ERS service mocking (EventBridge, DynamoDB, SNS, Lambda)

**Input**:
```
service_path: str
environment: str = "test"  # dev, staging, test
test_filter: str = None
mock_dynamodb: bool = True
mock_eventbridge: bool = True
mock_sns: bool = True
```

**Output**:
```
{
  "service": "{service-name}",
  "integration_tests": 15,
  "passed": 13,
  "failed": 2,
  "skipped": 0,
  "failed_tests": ["test_event_fanout_to_members", ...],
  "mocks_used": ["DynamoDB", "SNS"],
  "execution_time_sec": 42.5
}
```

**Implementation Notes**:
- Mock ERS services: use localstack, moto, serverless-offline, or equivalent
- Set up test fixtures (seed DynamoDB, pre-publish events, etc.)
- Run integration tests (slower than unit, ~30-60s per service)
- Report which mocks were used
- Fail fast if core service mocks unavailable

**Success Criteria**:
- Can mock DynamoDB for {service-name} tests
- Can mock SNS for event consumer tests
- Report coverage of service integrations

---

## Skill 3: test-e2e-orchestration.md

**Purpose**: Orchestrate Playwright E2E tests with scenario filtering

**Input**:
```
scenario_filter: str = None  # optional: "login", "create_event", etc.
headless: bool = True
trace_on_failure: bool = True
parallel_workers: int = 2
```

**Output**:
```
{
  "scenarios_found": 8,
  "scenarios_run": 3,  # filtered
  "passed": 3,
  "failed": 0,
  "execution_time_sec": 125,
  "traces": ["trace_login.zip", ...]  # if failures
}
```

**Implementation Notes**:
- Scan `e2e/` directory for Playwright test files
- Parse test names (scenario identifiers)
- Allow filtering by scenario name
- Run tests in parallel (2-4 workers)
- Capture video/trace on failure
- Report execution time

**Success Criteria**:
- Discover Playwright tests in {service-name}
- Filter and run specific scenarios
- Report failures + trace files

---

## Skill 4: test-business-logic.md

**Purpose**: Parametric testing for business logic, edge cases, state machines

**Input**:
```
service_path: str
business_logic_spec: dict  # REQ object with edge cases
state_machine_transitions: dict = None  # state A -> B transitions
```

**Output**:
```
{
  "requirement": "REQ-001-user-role-admin",
  "edge_cases_tested": 12,
  "passed": 11,
  "failed": 1,
  "uncovered_transitions": ["disabled -> active"],
  "data_interactions": {
    "user_role_change": "OK",
    "event_creation_with_new_role": "FAIL"
  }
}
```

**Implementation Notes**:
- Parse requirement spec (which business logic to test)
- Generate test variations (parametric: user roles, event types, permissions)
- Test state machine transitions (member -> admin, admin -> disabled, etc.)
- Test data interactions (role change -> what else changes?)
- Identify uncovered transitions or edge cases
- Report detailed failure analysis

**Success Criteria**:
- Test user role transitions (member -> admin -> disabled)
- Identify permission edge cases
- Report data consistency issues

---

## Skill 5: security-semantic-scan.md

**Purpose**: Claude-based semantic security scanning (data flow, component interaction)

**Input**:
```
service_path: str
focus_areas: list = ["auth", "data_flow", "crypto"]  # optional
verify_findings: bool = True  # adversarial verification
```

**Output**:
```
{
  "service": "{service-name}",
  "findings": [
    {
      "severity": "HIGH",
      "title": "JWT scope not validated in Lambda handler",
      "description": "API Gateway checks scope, but handler doesn't re-validate",
      "file": "lambda/command/main.go:142",
      "data_flow": "JWT -> API Gateway -> Lambda (gap: no re-validation)",
      "remediation": "Add scope validation in handler before processing",
      "verified": true  # adversarial check passed
    }
  ],
  "false_positives": 0,
  "execution_time_sec": 45
}
```

**Implementation Notes**:
- Use Claude Opus to analyze code semantically
- Trace data flows (input -> processing -> output)
- Identify privilege escalation, injection, crypto issues
- Focus on complex multi-component vulnerabilities
- Run adversarial verification: "prove this finding wrong" → filter false positives
- Escalation: always review findings with Security Engineer

**Success Criteria**:
- Find real vulnerability (e.g., missing scope check, missing input validation)
- Report data flow chain
- Filter false positives via adversarial verification

---

## Skill 6: security-dependency-scan.md

**Purpose**: Orchestrate dependency vulnerability scanning (go vuln, npm audit, cargo audit)

**Input**:
```
service_path: str
fail_on_critical: bool = True
fail_on_major: bool = False
fix_available_only: bool = False  # only report if fix available
```

**Output**:
```
{
  "service": "{service-name}",
  "language": "go",
  "vulnerabilities": [
    {
      "id": "GO-2026-12345",
      "package": "github.com/example/vulnerable",
      "installed_version": "1.2.3",
      "vulnerable_versions": "<=1.2.5",
      "severity": "HIGH",
      "description": "Buffer overflow in parsing",
      "fix_version": "1.2.6",
      "has_fix": true
    }
  ],
  "critical_count": 1,
  "major_count": 3,
  "gate_result": "BLOCK"  # critical found
}
```

**Implementation Notes**:
- Detect language (Go go.mod, Node package.json, Python requirements.txt, Rust Cargo.toml)
- Run: go list -json -m all | go vuln ./...
- Run: npm audit (JSON format)
- Run: cargo audit (if Rust service)
- Report: vulnerability ID, package, version range, fix available
- Escalation: critical = block, major = warn, minor = log

**Success Criteria**:
- Find vulnerable dependencies in {service-name}
- Report available fix versions
- Gate decision: critical blocks deployment

---

## Skill 7: security-secret-detection.md

**Purpose**: Detect hardcoded secrets (API keys, tokens, credentials)

**Input**:
```
scan_source: str = "git_diff"  # "git_diff", "file", "commit_range"
commit_hash: str = None
fail_on_found: bool = True
```

**Output**:
```
{
  "secrets_found": 2,
  "detections": [
    {
      "type": "AWS_API_KEY",
      "file": ".env.local",
      "line": 5,
      "pattern": "AKIA...",
      "severity": "CRITICAL"
    },
    {
      "type": "PRIVATE_KEY",
      "file": "lambda/secrets/key.pem",
      "line": 1,
      "severity": "CRITICAL"
    }
  ],
  "gate_result": "BLOCK"
}
```

**Implementation Notes**:
- Scan git diffs (pre-commit, pre-push context)
- Check file contents against secret patterns (AWS API key format, PEM headers, etc.)
- Use tools: truffleHog, GitHub secret scanning patterns, or custom regex
- Severity: always CRITICAL for detected secrets
- Escalation: block deployment immediately

**Success Criteria**:
- Detect hardcoded AWS credentials
- Detect hardcoded API tokens
- Block deployment if secrets found

---

## Skill 8: requirement-mapping.md

**Purpose**: Map requirements to tests to code, calculate coverage %

**Input**:
```
service_path: str
spec_file: str  # path to requirement spec
requirement_id: str = None  # specific requirement or all
```

**Output**:
```
{
  "service": "{service-name}",
  "requirements_total": 15,
  "requirements_covered": 13,
  "coverage_percent": 86.7,
  "mappings": [
    {
      "requirement_id": "REQ-001-user-role-admin",
      "description": "Admin users can approve/reject events",
      "test_count": 3,
      "tests": ["test_admin_approve", "test_admin_reject", "test_role_transition"],
      "code_files": ["handlers.go:AdminApprovalHandler", "models.go:User.IsAdmin"],
      "coverage": "100%"
    }
  ],
  "unmapped_requirements": ["REQ-005-audit-logging"],
  "orphaned_code": []
}
```

**Implementation Notes**:
- Parse requirement spec (YAML, JSON, or Markdown format)
- Search codebase for test files matching requirement ID
- Trace test → code execution (grep, AST analysis, or pattern matching)
- Calculate coverage: tests with passing status / total tests per requirement
- Report unmapped requirements (no tests)
- Report orphaned code (no requirement, no test) — flag for refactoring

**Success Criteria**:
- Map REQ-001 to 3+ tests in {service-name}
- Calculate coverage % correctly
- Identify unmapped requirements

---

## Skill 9: requirement-verification.md

**Purpose**: Pre-deployment gate: verify all requirements have passing tests

**Input**:
```
service_path: str
deployment_target: str = "prod"  # dev, staging, prod
fail_on_uncovered: bool = True
```

**Output**:
```
{
  "service": "{service-name}",
  "deployment_target": "prod",
  "requirements_total": 15,
  "requirements_tested": 14,
  "requirements_all_passing": 13,
  "gate_result": "WARN",  # 1 requirement has failing test
  "issues": [
    {
      "requirement_id": "REQ-003",
      "test_status": "1 failing",
      "test_name": "test_event_approval_permission",
      "remediation": "Fix test or requirement"
    }
  ]
}
```

**Implementation Notes**:
- Use requirement-mapping output as input
- Check each requirement: all tests passing?
- Gate logic:
  - All requirements tested + all passing → PROCEED
  - Any requirement untested → WARN or BLOCK
  - Any requirement has failing test → WARN or BLOCK
- Detailed issue report per failing requirement
- Escalation: if fail_on_uncovered, block deployment

**Success Criteria**:
- Verify all requirements in {service-name} have tests
- Report any failing tests per requirement
- Gate decision: proceed if all green

---

## Skill 10: spec-compliance-verification.md

**Purpose**: Verify code complies with extracted specs ({service-name}/specs/*)

**Input**:
```
service_path: str
spec_dir: str = "{service-name}/specs"
```

**Output**:
```
{
  "service": "{service-name}",
  "specs_total": 8,
  "specs_compliant": 7,
  "compliance_percent": 87.5,
  "deviations": [
    {
      "spec_id": "SPEC-P-003",
      "pattern": "GitHub Actions main.yaml",
      "expected": "Deploy depends on test",
      "actual": "Deploy runs after test (correct)",
      "deviation": "minor - comment missing"
    }
  ]
}
```

**Implementation Notes**:
- Load extracted specs from {service-name}/specs/
- For each spec, check service compliance
- Compare actual implementation against spec requirements
- Report compliance % and deviations
- Integration: works with spec-audit skill

**Success Criteria**:
- Verify {service-name} follows Makefile pattern spec
- Verify GitHub Actions spec compliance
- Report deviations with severity

---

## Skill 11: issue-diagnostic-engine.md

**Purpose**: Analyze quality gate failures, diagnose root cause, assign confidence + risk score

**Input**:
```
failure_log: dict  # from quality gate failure (test, security, config)
service_path: str
failure_type: str  # "test_failure", "security_finding", "config_missing"
```

**Output**:
```
{
  "failure": "test failed: missing env var DATABASE_URL",
  "root_cause": "configuration",
  "root_cause_details": "Environment variable DATABASE_URL not set in Lambda env",
  "confidence": "HIGH",
  "risk_level": "LOW",
  "suggested_fix": "Add DATABASE_URL to cdk/stacks/command_stack.go env vars",
  "healer_eligible": true,
  "issue_type": "config_missing",
  "escalation_needed": false
}
```

**Implementation Notes**:
- Parse failure log (test output, security finding, config error)
- Identify root cause category: dependency, config, test flakiness, logic, infra
- Assign confidence: HIGH (pattern-matchable) or LOW (ambiguous)
- Assign risk: LOW (safe to auto-fix) or HIGH (needs human review)
- Suggest fix (code change, config update, etc.)
- Healer eligibility: HIGH confidence + LOW risk
- Escalation decision: route to Healer or escalate to human

**Success Criteria**:
- Diagnose missing env var correctly → HIGH confidence, suggest fix
- Diagnose logic bug correctly → LOW confidence, escalate
- Score confidence and risk appropriately

---

## Skill 12: healer-engineer.md

**Purpose**: Auto-fix low-risk, pattern-matchable issues; create PR + optional auto-merge

**Input**:
```
diagnostic: dict  # from issue-diagnostic-engine
service_path: str
create_pr: bool = True
auto_merge_if_ci_passes: bool = True
```

**Output**:
```
{
  "issue_fixed": true,
  "fix_type": "config_missing",
  "file_modified": "cdk/stacks/command_stack.go",
  "fix_applied": "Added DATABASE_URL to Lambda env vars",
  "pr_created": true,
  "pr_url": "https://github.com/{your-org}/{service-name}/pull/123",
  "pr_status": "CI_RUNNING",
  "auto_merge_eligible": true,
  "notes": "Fix merged successfully after CI passed"
}
```

**Implementation Notes**:
- Only execute for HIGH confidence + LOW risk issues
- Auto-fix types allowed:
  - Missing env var: add to .env + CDK stack env vars
  - Dependency version: update go.mod/package.json + regenerate lockfile
  - Flaky test: add retry logic or stabilize data setup
  - Lockfile stale: regenerate package-lock.json or go.sum
  - Import path wrong: fix import statement
- Create PR with descriptive message (e.g., "fix: add missing DATABASE_URL env var")
- Optionally auto-merge if:
  - All quality gates pass
  - No human escalations
  - Single, isolated change
- Track: what was fixed, when, outcome (for audit trail + feedback loop)

**Success Criteria**:
- Successfully auto-fix missing env var
- Create PR + optional auto-merge
- Escalate if fix PR fails CI

---

## Master Orchestration: quality-gate-orchestration.md

**Purpose**: Master orchestrator for entire quality gate + self-healing loop

**Workflow**:
```
1. Run all testing skills (parallel):
   - test-unit-orchestration
   - test-integration-orchestration
   - test-e2e-orchestration (filtered, expensive)
   - test-business-logic

2. Run all security skills (parallel):
   - security-semantic-scan
   - security-dependency-scan
   - security-secret-detection

3. Run compliance skills (parallel):
   - requirement-verification
   - spec-compliance-verification

4. Aggregate results + initial gate decision:
   - All green? → PROCEED
   - Issues found? → SELF-HEALING LOOP

5. SELF-HEALING LOOP (if issues):
   - Call issue-diagnostic-engine for each issue
   - Route to healer-engineer (HIGH confidence + LOW risk)
   - Escalate to human (LOW confidence OR HIGH risk)
   - Re-run quality gates after healing
   - If still green → PROCEED
   - If still red → Escalate (needs human 2nd look)

6. Final gate decision:
   - All checks green + healing successful → PROCEED to deployment
   - Critical issues or escalations → BLOCK + report details
```

---

## Documentation + Integration

**Deliverables**:
- Update `agentic-engineers/skills/SKILLS-INDEX.md` (add all 12 skills)
- Create `agentic-engineers/skills/HEALER-WORKFLOW.md` (Healer role guide)
- Create `agentic-engineers/skills/roles/healer-engineer.md` (new role)
- Update `agentic-engineers/skills/roles/quality-engineer.md` (orchestrator responsibilities)
- Create examples for each skill

---

**Status**: Specifications complete, ready for implementation

**Next**: Orchestrator delegates to sub-agents for parallel building
