---
name: issue-diagnostic-engine
description: Analyze quality gate failures, diagnose root cause, assign confidence + risk score, route to Healer or escalate
type: skill
version: 1.0
track: self-healing
---

# issue-diagnostic-engine

Receives a quality gate failure, identifies the root cause category, scores confidence and risk,
suggests a fix, and decides whether the issue is eligible for automated healing or requires human review.

## Usage

```
/issue-diagnostic-engine failure_log={...} service_path={example-service} failure_type=config_missing
/issue-diagnostic-engine failure_log={...} service_path={service-name} failure_type=test_failure
/issue-diagnostic-engine failure_log={...} service_path={example-service} failure_type=security_finding
```

## Input

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `failure_log` | dict | required | Raw failure output from quality gate (test log, security finding, config error) |
| `service_path` | str | required | Absolute or relative path to service root |
| `failure_type` | str | required | `test_failure` \| `security_finding` \| `config_missing` \| `dependency_issue` \| `infra_issue` |

### failure_log structure (varies by failure_type)

**test_failure**:
```json
{
  "test_name": "TestCreateUser_MissingDatabaseURL",
  "error_output": "dial tcp: missing env DATABASE_URL",
  "file": "handlers/user_test.go:112",
  "exit_code": 1
}
```

**config_missing**:
```json
{
  "error": "environment variable DATABASE_URL not found",
  "context": "Lambda startup",
  "stack": "{example-service}"
}
```

**security_finding**:
```json
{
  "severity": "HIGH",
  "title": "JWT scope not validated in handler",
  "file": "lambda/command/main.go:142",
  "tool": "security-semantic-scan"
}
```

**dependency_issue**:
```json
{
  "vulnerability_id": "GO-2026-12345",
  "package": "github.com/example/lib",
  "installed_version": "1.2.3",
  "fix_version": "1.2.6",
  "severity": "MEDIUM"
}
```

## Output

```json
{
  "failure": "test failed: missing env var DATABASE_URL",
  "root_cause": "configuration",
  "root_cause_details": "Environment variable DATABASE_URL not set in Lambda environment config",
  "confidence": "HIGH",
  "risk_level": "LOW",
  "suggested_fix": "Add DATABASE_URL to cdk/stacks/command_stack.go Lambda environment vars block",
  "healer_eligible": true,
  "issue_type": "config_missing",
  "escalation_needed": false,
  "escalation_reason": null,
  "escalate_to": null,
  "diagnostic_notes": "Pattern-matched: known env var missing pattern. Safe single-file CDK change."
}
```

### Field Reference

| Field | Values | Description |
|-------|--------|-------------|
| `root_cause` | `configuration` \| `dependency` \| `test_flakiness` \| `logic` \| `infrastructure` \| `security` | Root cause category |
| `confidence` | `HIGH` \| `LOW` | HIGH = pattern-matchable, LOW = ambiguous or novel |
| `risk_level` | `LOW` \| `HIGH` | LOW = safe isolated change, HIGH = side effects or security |
| `healer_eligible` | bool | true only when confidence=HIGH AND risk_level=LOW |
| `escalate_to` | `lead` \| `principal` \| `security` \| null | Role to escalate to if not healer-eligible |

## Root Cause Categories

### 1. configuration — Missing or wrong env var / path / permission

**Patterns**:
- `"environment variable X not found"`
- `"missing required env: X"`
- `"cannot find config key X"`
- `"no such file or directory: /path/to/config"`

**Confidence logic**: HIGH if the missing name is found in CDK stack or .env files; LOW if unknown origin.

**Risk**: LOW — adding a named env var to a CDK stack is isolated and reversible.

**ERS example**:
- Error: `Lambda startup: environment variable SNS_TOPIC_ARN not found`
- Fix: Add `SNS_TOPIC_ARN` to env vars block in `cdk/stacks/members_stack.go`
- healer_eligible: true

---

### 2. dependency — Missing, outdated, or vulnerable package

**Patterns**:
- `"cannot find module X"` / `"package X: cannot load"`
- `"requires go 1.XX, using 1.YY"`
- Vulnerability ID with `fix_version` available

**Confidence logic**: HIGH if `fix_version` is known and semver-compatible (patch/minor). LOW for major version bumps.

**Risk**: LOW for patch versions; HIGH for major version bumps (breaking changes possible).

**ERS example**:
- Error: `GO-2026-12345: github.com/aws/aws-sdk-go v1.44.0 has fix in v1.44.3`
- Fix: Bump version in `go.mod`, regenerate `go.sum`
- healer_eligible: true (patch bump)

---

### 3. test_flakiness — Non-deterministic or timing-dependent test failure

**Patterns**:
- Same test passes in isolation, fails in suite
- Error contains `"context deadline exceeded"`, `"connection refused"`, `"timeout"`
- Test output differs across runs with same input

**Confidence logic**: HIGH if failure rate <100% or test contains timing/concurrency primitives. LOW if always fails.

**Risk**: LOW — adding retry or stabilizing test fixture doesn't touch production code.

**ERS example**:
- Error: `TestSNSPublish: context deadline exceeded (intermittent)`
- Fix: Add `t.Retry(3)` or increase timeout in test setup
- healer_eligible: true

---

### 4. logic — Code bug / incorrect business logic

**Patterns**:
- `"expected X, got Y"` where X/Y are domain values (not config/env)
- Assertion failures against business rules
- Regression in core handler or model behavior

**Confidence logic**: Always LOW — logic bugs require code understanding, not pattern matching.

**Risk**: Always HIGH — incorrect logic fix could silently corrupt data or break other tests.

**ERS example**:
- Error: `TestAdminApproveEvent: expected status 200, got 403`
- healer_eligible: false
- escalate_to: lead

---

### 5. infrastructure — Service unavailable / network / AWS

**Patterns**:
- `"connection refused"` to real AWS endpoints
- `"no such host"`, `"timeout dialing"`, `"AWS service unavailable"`
- Lambda cold start timeouts

**Confidence logic**: HIGH if error clearly names an AWS service. LOW if ambiguous network error.

**Risk**: HIGH — infra issues may indicate misconfigured IAM, VPC, or deployment problem.

**ERS example**:
- Error: `DynamoDB: connection refused (us-east-1)`
- healer_eligible: false
- escalate_to: principal

---

### 6. security — Security finding from scanner

**Confidence logic**: Always LOW — security findings require human judgment to assess impact.

**Risk**: Always HIGH — incorrect security fix could introduce new vulnerabilities.

**ERS examples**:
- JWT scope bypass finding from `security-semantic-scan`
- Hardcoded credential from `security-secret-detection`
- healer_eligible: false
- escalate_to: security

---

## Routing Decision

```
Issue received
  ↓
Parse failure_log, match pattern → root_cause category
  ↓
Score confidence (HIGH / LOW)
  ↓
Score risk (LOW / HIGH)
  ↓
healer_eligible = (confidence == HIGH AND risk_level == LOW)
  ├─ true  → route to healer-engineer
  └─ false → escalate_to: lead | principal | security
```

### Escalation routing by category

| root_cause | Typical escalate_to |
|------------|---------------------|
| configuration | healer (if HIGH/LOW) |
| dependency (patch) | healer (if HIGH/LOW) |
| dependency (major) | lead |
| test_flakiness | healer (if HIGH/LOW) |
| logic | lead |
| infrastructure | principal |
| security | security |

## Implementation

### Step 1: Parse failure_log

```pseudo
func parse_failure(failure_log, failure_type):
  error_text = extract_error_string(failure_log)  # main error message
  context = failure_log.get("context", "")
  file = failure_log.get("file", "")
  return {error_text, context, file}
```

### Step 2: Pattern match to root cause

```pseudo
func identify_root_cause(error_text, failure_type):
  if failure_type == "security_finding":
    return "security", confidence="LOW", risk="HIGH"

  config_patterns = [
    r"environment variable (\w+) not found",
    r"missing required env[: ]+(\w+)",
    r"cannot find config key (\w+)",
    r"no such file or directory: (.+\.env.*)",
  ]

  dependency_patterns = [
    r"cannot find module ([\w/.-]+)",
    r"package ([\w/.-]+): cannot load",
    r"requires go ([\d.]+)",
    r"vulnerability.*fix.*version ([\d.]+)",
  ]

  flakiness_patterns = [
    r"context deadline exceeded",
    r"connection refused.*\(intermittent\)",
    r"timeout",
    r"race condition",
  ]

  logic_patterns = [
    r"expected \w+, got \w+",
    r"assertion failed",
    r"test.*FAIL.*handlers",
  ]

  infra_patterns = [
    r"AWS.*unavailable",
    r"DynamoDB.*connection refused",
    r"Lambda.*timeout",
    r"no such host",
  ]

  match patterns in order: config → dependency → flakiness → infra → logic
  default: return "logic", confidence="LOW", risk="HIGH"
```

### Step 3: Score confidence

```pseudo
func score_confidence(root_cause, error_text, service_path):
  if root_cause == "configuration":
    # HIGH if missing var name found in CDK stack or .env files
    var_name = extract_var_name(error_text)
    if var_name and (found_in_cdk(var_name, service_path) or found_in_env_files(var_name)):
      return "HIGH"
    return "LOW"  # unknown var, ambiguous origin

  if root_cause == "dependency":
    fix_version = extract_fix_version(error_text)
    if fix_version and is_patch_or_minor_bump(fix_version):
      return "HIGH"
    return "LOW"  # major bump or no known fix

  if root_cause == "test_flakiness":
    # HIGH if failure is intermittent (not 100% fail rate)
    if "intermittent" in error_text or "timeout" in error_text:
      return "HIGH"
    return "LOW"

  # logic, infrastructure, security: always LOW
  return "LOW"
```

### Step 4: Score risk

```pseudo
func score_risk(root_cause, confidence):
  LOW_risk = {"configuration", "test_flakiness"}
  HIGH_risk = {"logic", "infrastructure", "security"}

  if root_cause in LOW_risk:
    return "LOW"
  if root_cause == "dependency":
    # patch/minor bump = LOW, major = HIGH
    return "LOW" if confidence == "HIGH" else "HIGH"
  return "HIGH"
```

### Step 5: Build output

```pseudo
func build_diagnostic(root_cause, confidence, risk_level, error_text, service_path):
  healer_eligible = (confidence == "HIGH" and risk_level == "LOW")
  escalate_to = None
  if not healer_eligible:
    escalate_to = route_escalation(root_cause)

  suggested_fix = generate_fix_suggestion(root_cause, error_text, service_path)

  return DiagnosticOutput(
    failure=error_text,
    root_cause=root_cause,
    root_cause_details=...,
    confidence=confidence,
    risk_level=risk_level,
    suggested_fix=suggested_fix,
    healer_eligible=healer_eligible,
    issue_type=failure_type,
    escalation_needed=not healer_eligible,
    escalate_to=escalate_to,
  )
```

### Step 6: Generate suggested_fix

```pseudo
func generate_fix_suggestion(root_cause, error_text, service_path):
  if root_cause == "configuration":
    var_name = extract_var_name(error_text)
    cdk_file = find_cdk_stack(service_path)
    return f"Add {var_name} to Lambda env vars in {cdk_file}"

  if root_cause == "dependency":
    package = extract_package(error_text)
    fix_version = extract_fix_version(error_text)
    lang = detect_language(service_path)
    if lang == "go":
      return f"Bump {package} to {fix_version} in go.mod, run go mod tidy"
    if lang == "node":
      return f"Update {package} to {fix_version} in package.json, run npm install"

  if root_cause == "test_flakiness":
    test_name = extract_test_name(error_text)
    return f"Add retry logic or increase timeout in {test_name}"

  return "Requires human review — see root_cause_details"
```

## ERS-Specific Examples

### Example 1: Missing env var (healer_eligible: true)

**Input**:
```json
{
  "failure_log": {
    "test_name": "TestCommandHandler_Integration",
    "error_output": "environment variable SNS_TOPIC_ARN not found",
    "file": "handlers/command_test.go:88"
  },
  "service_path": "{example-service}",
  "failure_type": "config_missing"
}
```

**Output**:
```json
{
  "failure": "environment variable SNS_TOPIC_ARN not found",
  "root_cause": "configuration",
  "root_cause_details": "SNS_TOPIC_ARN not present in Lambda env vars. Found referenced in cdk/stacks/command_stack.go but not declared in environment block.",
  "confidence": "HIGH",
  "risk_level": "LOW",
  "suggested_fix": "Add SNS_TOPIC_ARN to Lambda env vars in cdk/stacks/command_stack.go environment block. Value: /${appName}/SNSTopicARN from SSM.",
  "healer_eligible": true,
  "issue_type": "config_missing",
  "escalation_needed": false,
  "escalate_to": null
}
```

### Example 2: Logic bug (healer_eligible: false)

**Input**:
```json
{
  "failure_log": {
    "test_name": "TestAdminApproveCalendarEvent",
    "error_output": "expected status 200, got 403 — admin role not recognized",
    "file": "handlers/calendar_test.go:201"
  },
  "service_path": "{example-service}",
  "failure_type": "test_failure"
}
```

**Output**:
```json
{
  "failure": "expected status 200, got 403 — admin role not recognized",
  "root_cause": "logic",
  "root_cause_details": "Admin role check in calendar event handler returning 403. Possible regression in scope validation or role mapping.",
  "confidence": "LOW",
  "risk_level": "HIGH",
  "suggested_fix": "Review AdminApprovalHandler in handlers/calendar.go — verify scope claim parsing matches OAuth2 scope format auth.evolutionrollersports.com/admin",
  "healer_eligible": false,
  "issue_type": "test_failure",
  "escalation_needed": true,
  "escalate_to": "lead"
}
```

### Example 3: Security finding (healer_eligible: false)

**Input**:
```json
{
  "failure_log": {
    "severity": "HIGH",
    "title": "JWT scope not re-validated in Lambda handler",
    "file": "lambda/command/main.go:142",
    "tool": "security-semantic-scan"
  },
  "service_path": "{example-service}",
  "failure_type": "security_finding"
}
```

**Output**:
```json
{
  "failure": "JWT scope not re-validated in Lambda handler",
  "root_cause": "security",
  "root_cause_details": "API Gateway validates JWT scope but Lambda handler at main.go:142 trusts forwarded claims without re-validation. Potential scope bypass.",
  "confidence": "LOW",
  "risk_level": "HIGH",
  "suggested_fix": "Add explicit scope check in Lambda handler before processing command. See OAuth2 scopes: auth.evolutionrollersports.com/{scope}",
  "healer_eligible": false,
  "issue_type": "security_finding",
  "escalation_needed": true,
  "escalate_to": "security"
}
```

### Example 4: Dependency patch bump (healer_eligible: true)

**Input**:
```json
{
  "failure_log": {
    "vulnerability_id": "GO-2026-12345",
    "package": "github.com/aws/aws-sdk-go",
    "installed_version": "1.44.0",
    "fix_version": "1.44.3",
    "severity": "MEDIUM"
  },
  "service_path": "{service-name}",
  "failure_type": "dependency_issue"
}
```

**Output**:
```json
{
  "failure": "GO-2026-12345: github.com/aws/aws-sdk-go v1.44.0 vulnerable, fix in v1.44.3",
  "root_cause": "dependency",
  "root_cause_details": "Patch version bump available. MEDIUM severity, no breaking changes expected in 1.44.0→1.44.3.",
  "confidence": "HIGH",
  "risk_level": "LOW",
  "suggested_fix": "Bump github.com/aws/aws-sdk-go to v1.44.3 in go.mod, run go mod tidy to regenerate go.sum",
  "healer_eligible": true,
  "issue_type": "dependency_issue",
  "escalation_needed": false,
  "escalate_to": null
}
```

## Integration

- **Called by**: `quality-gate-orchestration` after any gate failure
- **Routes to**: `healer-engineer` (healer_eligible=true) or human escalation (healer_eligible=false)
- **Output feeds**: `healer-engineer` `diagnostic` input field directly
