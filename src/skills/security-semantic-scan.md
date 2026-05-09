---
name: security-semantic-scan
description: Claude-based semantic security scanning — data flow analysis, multi-component vulnerability detection, adversarial verification
type: skill
version: 1.0
track: security
---

# security-semantic-scan

Semantic security scanning using Claude to trace data flows across components, identify complex
multi-component vulnerabilities (especially in CQRS/event-driven architectures), and filter
findings through adversarial verification before surfacing.

Pattern matching misses CQRS/event-driven vulnerabilities. This skill reads code like a human
security researcher: trace data across services, reason about trust boundaries, identify gaps
that only appear at the intersection of components.

## Usage

```
/security-semantic-scan service_path=/home/user/git/ers/{service-name}
/security-semantic-scan service_path={service-name} focus_areas=["auth","data_flow"]
/security-semantic-scan service_path={service-name} focus_areas=["crypto"] verify_findings=true
```

## Input

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `service_path` | str | required | Absolute or relative path to service root |
| `focus_areas` | list | `["auth","data_flow","crypto"]` | Scan focus: `auth`, `data_flow`, `crypto` |
| `verify_findings` | bool | true | Run adversarial verification to filter false positives |

## Output

```json
{
  "service": "{service-name}",
  "focus_areas": ["auth", "data_flow"],
  "findings": [
    {
      "id": "SEC-001",
      "severity": "HIGH",
      "title": "JWT scope not re-validated in Lambda handler",
      "description": "API Gateway validates JWT issuer and expiry but does not enforce OAuth2 scope. The Lambda handler proceeds without re-checking scope, allowing any authenticated user to invoke admin-only commands.",
      "file": "lambda/command/main.go:142",
      "data_flow": "JWT → API Gateway (issuer+expiry check) → Lambda (gap: no scope re-validation) → command handler",
      "remediation": "Extract claims from JWT in handler and assert required scope (e.g., auth.evolutionrollersports.com/admin) before processing command. Do not rely solely on API Gateway authorizer.",
      "verified": true,
      "adversarial_challenge": "API Gateway authorizer could be configured with scope enforcement",
      "adversarial_result": "Confirmed gap: authorizer config checked — scope not in authorizer policy"
    }
  ],
  "false_positives_filtered": 1,
  "execution_time_sec": 48,
  "escalation": "REQUIRED — all findings must be reviewed by Security Engineer before acting"
}
```

`severity`: `HIGH` | `MEDIUM` | `LOW`

## Severity Classification

| Severity | Category | ERS Examples |
|----------|----------|-------------|
| **HIGH** | Privilege escalation, injection, auth bypass | JWT scope not checked in Lambda; event published without sender validation allowing privilege escalation; unsanitised input reaching DynamoDB expression |
| **MEDIUM** | Weak crypto, insecure defaults, over-broad IAM | MD5/SHA-1 used for token derivation; JWT token not rotated; Lambda IAM role with wildcard resource |
| **LOW** | Sensitive data in logs, missing rate limiting | User ID or email logged at DEBUG; no rate limiting on command endpoint |

## Implementation

### Step 1: Enumerate Entry Points

```pseudo
func enumerate_entry_points(service_path, focus_areas):
  entry_points = []

  // Lambda HTTP handlers
  find {service_path} -name "main.go" | xargs grep -l "lambda.Start\|apigatewayv2"
  for each handler file:
    locate: func handler(ctx, request) — the outermost request entry point
    entry_points.add({ file, function, type: "http_lambda" })

  // Event consumers (SNS/SQS)
  find {service_path} -name "*.go" | xargs grep -l "events.SNSEvent\|events.SQSEvent"
  for each consumer file:
    locate: handler function signature
    entry_points.add({ file, function, type: "event_consumer" })

  return entry_points
```

### Step 2: Trace Data Flows

For each entry point, trace the data path through the service:

```pseudo
func trace_data_flow(entry_point, focus_areas):
  flow = { source: entry_point, steps: [], sinks: [] }

  // Read handler + called functions (up to 3 levels deep)
  read source file
  identify all function calls within handler
  for each called function: read its implementation
  
  // Track data transformations
  flow.steps = ordered list of:
    - where data enters (JWT claims, request body, event payload)
    - where it is validated (if at all)
    - where it is used (DynamoDB write, SNS publish, Cognito call)
    - where it exits (response body, logs, downstream event)

  // Identify trust boundary crossings
  flag: data crossing from untrusted (external request) to trusted (internal service call)
  flag: data from SNS event used without verifying sender identity
  flag: JWT claims used after initial parse but without re-assertion

  return flow
```

### Step 3: Apply Vulnerability Pattern Library

```pseudo
PATTERNS = {
  "auth": [
    {
      id: "AUTH-001",
      name: "JWT scope not re-validated in Lambda",
      signal: "JWT claims extracted but scope/role assertion absent before privileged operation",
      severity: "HIGH",
      ers_context: "API Gateway JWT authorizer checks signature+expiry; Lambda must additionally assert scope"
    },
    {
      id: "AUTH-002",
      name: "Event consumer accepts events without sender validation",
      signal: "SNS/SQS event payload used without checking event kind, pubkey, or source topic ARN",
      severity: "HIGH",
      ers_context: "SNS FIFO topic ARN should be verified; event kind (8801-8899) should be asserted"
    },
    {
      id: "AUTH-003",
      name: "IAM role over-permissioned",
      signal: "Lambda execution role uses wildcard resource in policy statement",
      severity: "MEDIUM"
    }
  ],
  "data_flow": [
    {
      id: "FLOW-001",
      name: "Unvalidated input reaches DynamoDB expression",
      signal: "Request field used directly in DynamoDB ExpressionAttributeValues without type/length check",
      severity: "HIGH"
    },
    {
      id: "FLOW-002",
      name: "Sensitive field in structured log",
      signal: "Email, phone, or token value passed to log.Printf/zap.Info without redaction",
      severity: "LOW"
    },
    {
      id: "FLOW-003",
      name: "Event payload forwarded without schema validation",
      signal: "Incoming NOSTR event content deserialized and re-published without validating required fields",
      severity: "MEDIUM"
    }
  ],
  "crypto": [
    {
      id: "CRYPTO-001",
      name: "Weak hashing algorithm",
      signal: "md5.New() or sha1.New() used for security-sensitive derivation",
      severity: "MEDIUM"
    },
    {
      id: "CRYPTO-002",
      name: "JWT token not rotated / no expiry enforcement",
      signal: "JWT parsed and claims used without checking exp claim in handler",
      severity: "MEDIUM",
      ers_context: "API Gateway checks exp; Lambda may skip it if using raw claim extraction"
    },
    {
      id: "CRYPTO-003",
      name: "Hardcoded secret or salt",
      signal: "String literal matching key/secret/salt/password pattern used in crypto context",
      severity: "HIGH"
    }
  ]
}

func apply_patterns(data_flows, focus_areas):
  candidate_findings = []
  for flow in data_flows:
    for area in focus_areas:
      for pattern in PATTERNS[area]:
        if pattern_matches(flow, pattern):
          candidate_findings.add({
            pattern_id: pattern.id,
            severity: pattern.severity,
            title: pattern.name,
            file: flow.source.file,
            data_flow: format_flow_chain(flow),
            ...
          })
  return candidate_findings
```

### Step 4: Adversarial Verification

For each candidate finding, challenge it before surfacing:

```pseudo
func adversarial_verify(finding, service_path):
  // Attempt to disprove the finding
  challenge_questions = [
    "Is there a middleware or wrapper that enforces this before the handler runs?",
    "Is validation happening in a shared library called earlier in the stack?",
    "Is the data sink actually unreachable from untrusted input?",
    "Does the IAM policy actually restrict this at the AWS level?"
  ]

  for each question:
    search service_path for evidence that disproves the finding
    // e.g., grep for scope validation in shared middleware
    // e.g., check CDK stack for restrictive IAM policy

  if disproving_evidence_found:
    mark finding as false_positive, record reason
    return { verified: false, reason: disproving_evidence }
  else:
    mark finding as verified
    record adversarial challenge attempted and failed
    return { verified: true, adversarial_challenge: question_asked, adversarial_result: "No disproving evidence found" }
```

### Step 5: Format & Gate

```pseudo
func format_results(verified_findings, false_positives):
  return {
    service: basename(service_path),
    focus_areas: focus_areas,
    findings: verified_findings.map(format_finding),
    false_positives_filtered: len(false_positives),
    execution_time_sec: elapsed,
    escalation: "REQUIRED — all findings must be reviewed by Security Engineer before acting"
  }
```

## ERS-Specific Focus Areas

### {service-name} (most critical surface)

- **Auth**: Confirm scope assertion after JWT parse in each command handler. API Gateway authorizer validates signature; Lambda must additionally check `scope` claim matches the command's required privilege level.
- **Data flow**: Trace request body fields → DynamoDB `ExpressionAttributeValues`. Confirm no direct string interpolation into filter expressions.
- **Event publishing**: Verify NOSTR event content is constructed from validated fields only; no raw user input forwarded into the event store.

```bash
# Key files to trace
find /home/user/git/ers/{service-name} -name "*.go" | xargs grep -l "Claims\|scope\|putItem\|PutItem"
```

### {service-name} (trust boundary)

- **Auth**: Verify callers are IAM-authenticated (SigV4). Confirm no public endpoint.
- **Event validation**: Check that event kind is in the allowed range (8801-8899) before storing.
- **Replay mode**: Confirm `REPLAY_MODE` is not user-controllable via request parameter.

### {service-name} (SNS consumer)

- **Sender validation**: Verify SNS source topic ARN is checked before processing event payload.
- **Idempotency bypass in replay**: Confirm `REPLAY_MODE=true` can only be set via Lambda env var (not request body).

### {service-name} (Cognito bridge)

- **Privilege in event handler**: `UserCreated` triggers Cognito user creation. Confirm event payload fields (email, given_name, family_name) are length/format validated before passing to Cognito API.
- **Side-effect replay guard**: ResendInvitation and ResetPassword handlers must be skipped during replay. Verify the guard is present and tested.

## Escalation

**All findings from this skill require Security Engineer review before any action is taken.**

Reason: semantic analysis has inherent false positive risk. A finding that looks real may have
mitigations not visible from static analysis (runtime middleware, CDK IAM policy, API Gateway
configuration). The Security Engineer assesses each finding in full context before escalating
to fix or closing as false positive.

```
Escalation path:
  HIGH finding → Security Engineer (immediate, same session)
  MEDIUM finding → Security Engineer (before next deployment)
  LOW finding → Security Engineer review queue
  Any finding → NEVER auto-fix without Security Engineer sign-off
```

## Integration

- Called by `quality-gate-orchestration` in the security scan phase (parallel with `security-dependency-scan` and `security-secret-detection`)
- Findings passed to Security Engineer role for review
- HIGH findings → block deployment gate until reviewed
- Verified findings fed to `issue-diagnostic-engine` with `failure_type: "security_finding"`
- Model recommendation: Claude Opus (Opus 4 or later) for analysis steps 2–4; Sonnet acceptable for step 1 enumeration

## Success Criteria

- Trace data flow from HTTP request body through to DynamoDB write in {service-name}
- Identify at least one real vulnerability pattern (e.g., missing scope check, unvalidated event field)
- Filter false positives via adversarial verification (challenge + search for disproving evidence)
- Never surface a finding without adversarial verification step completed
- Always include escalation notice in output
