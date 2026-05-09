---
name: spec-compliance-verification
description: Verify ERS service code complies with extracted architecture and pattern specs
type: skill
version: 1.0
track: compliance
---

# spec-compliance-verification

Verify that a service implementation matches extracted ERS specs (Makefile patterns,
CDK structure, event schemas, API contracts, config standards). Reports compliance %
and specific deviations with severity.

## Usage

```
/spec-compliance-verification service_path={service-name}
/spec-compliance-verification service_path={service-name} spec_dir={service-name}/specs
/spec-compliance-verification service_path={service-name} spec_id=SPEC-E-001
```

## Input

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `service_path` | str | required | Path to service root |
| `spec_dir` | str | `{service-name}/specs` | Directory containing extracted specs |
| `spec_id` | str | null | Filter to single spec |
| `severity_threshold` | str | `minor` | Minimum severity to report |

## Output

```json
{
  "service": "{service-name}",
  "specs_evaluated": 8,
  "specs_compliant": 7,
  "specs_deviated": 1,
  "compliance_percent": 87.5,
  "gate_result": "WARN",
  "results": [
    {
      "spec_id": "SPEC-M-001",
      "spec_name": "Standard Makefile Pattern",
      "status": "COMPLIANT",
      "checks_passed": 6,
      "checks_total": 6
    },
    {
      "spec_id": "SPEC-C-003",
      "spec_name": "CDK Stack: Lambda Environment Variables",
      "status": "DEVIATED",
      "checks_passed": 4,
      "checks_total": 5,
      "deviations": [
        {
          "check": "All Lambda env vars must reference SSM parameters for cross-service URLs",
          "expected": "SSM lookup: /{appName}/APIUrl",
          "actual": "Hardcoded string: 'https://api.example.com'",
          "file": "cdk/stacks/command_stack.go:87",
          "severity": "major",
          "remediation": "Replace hardcoded URL with ssm.StringParameter.valueFromLookup"
        }
      ]
    }
  ]
}
```

## Implementation

### Step 1: Discover Applicable Specs

```pseudo
func discover_specs(spec_dir, service_path, spec_id):
  service_name = basename(service_path)
  all_specs = load_specs_from_dir(spec_dir)
  
  if spec_id:
    return [s for s in all_specs if s.id == spec_id]
  
  # Filter to specs applicable to this service
  applicable = []
  for spec in all_specs:
    if spec.applies_to == "all":
      applicable.append(spec)
    elif service_name in spec.applies_to:
      applicable.append(spec)
    elif spec.service_type in get_service_types(service_path):
      applicable.append(spec)
  
  return applicable
```

Service types detected from service_path:
- `go-lambda` — has go.mod + cdk/ directory
- `react-pwa` — has package.json + src/ + vite.config.ts
- `go-library` — has go.mod, no cdk/
- `event-consumer` — has consumers/ directory with SQS handlers

### Step 2: Built-In ERS Spec Checks

#### SPEC-M-001: Standard Makefile Pattern

```pseudo
func check_makefile_pattern(service_path):
  makefile = read(service_path + "/Makefile")
  
  checks = [
    ("has describe target", "describe:" in makefile),
    ("has lint target", "lint:" in makefile),
    ("has test target", "test:" in makefile),
    ("has build target", "build:" in makefile),
    ("has deploy target", "deploy:" in makefile),
    ("includes env file", "-include env/.env.$(ENV_NAME)" in makefile),
    ("exports env vars", "export" in makefile),
    ("uses make verify", "verify:" in makefile or "lint test" in makefile),
    ("ARM64 build flags", "GOARCH=arm64" in makefile),
    ("lambda.norpc tag", "-tags lambda.norpc" in makefile)
  ]
  
  return evaluate_checks(checks)
```

#### SPEC-C-001: CDK Stack Structure

```pseudo
func check_cdk_structure(service_path):
  cdk_dir = service_path + "/cdk"
  
  checks = [
    ("cdk/ directory exists", exists(cdk_dir)),
    ("main.go entrypoint", exists(cdk_dir + "/main.go")),
    ("stacks/ subdirectory", exists(cdk_dir + "/stacks/")),
    ("env dir exists", exists(service_path + "/env/")),
    ("env files not committed", not in_git(service_path + "/env/.env.*")),
    ("one stack per component", count_stacks(cdk_dir + "/stacks/") >= 1)
  ]
  
  return evaluate_checks(checks)
```

#### SPEC-E-001: Event Schema Versioning

```pseudo
func check_event_schema(service_path):
  # Find all event Content structs
  event_structs = grep(service_path, "Version.*string", "*.go")
  
  checks = []
  for struct in event_structs:
    # Check version field exists in content structs
    checks.append((f"{struct.name} has Version field", has_field(struct, "Version")))
    # Check version default is "1.0"
    checks.append((f"{struct.name} version default is 1.0", 
                   grep(service_path, f'Version.*"1.0"', "*.go")))
  
  # Check pubkey/sig placeholders for domain events
  domain_events = find_domain_event_publishers(service_path)
  for event in domain_events:
    checks.append((f"{event} uses empty pubkey/sig",
                   uses_placeholder_pubkey_sig(event)))
  
  return evaluate_checks(checks)
```

#### SPEC-A-001: Auth Flow (JWT → SigV4)

```pseudo
func check_auth_flow(service_path):
  service_type = get_service_type(service_path)
  
  if service_type == "gateway":  # {service-name}, {service-name}
    checks = [
      ("validates JWT in handler", grep(service_path, "jwt.Parse\|ValidateToken", "*.go")),
      ("uses SigV4 for backend calls", grep(service_path, "aws.Signer\|SigV4", "*.go")),
      ("checks OAuth2 scope", grep(service_path, "scope\|Scope", "*.go")),
      ("no direct IAM from frontend", not grep(service_path, "AWS_ACCESS_KEY", "*.go"))
    ]
  
  if service_type == "backend":  # {service-name}, {service-name}, etc.
    checks = [
      ("no JWT acceptance", not grep(service_path, "jwt.Parse", "*.go")),
      ("IAM-only access", grep(service_path, "IAM\|SigV4\|iam", "cdk/stacks/*.go")),
      ("no public endpoint", not grep(service_path, "AuthorizationType.*NONE", "*.go"))
    ]
  
  return evaluate_checks(checks)
```

#### SPEC-P-001: Configuration Standard

References `{service-name}.md` — checks from that standard:

```pseudo
func check_config_standard(service_path):
  env_files = find(service_path + "/env/", ".env.*")
  
  checks = []
  for env_file in env_files:
    content = read(env_file)
    lines = [l for l in content.split("\n") if l and not l.startswith("#")]
    
    for line in lines:
      # No shell quotes around values
      checks.append((f"{env_file}: no quotes in '{line}'",
                     not regex_match(r'=["\']\S', line)))
    
    # Required vars present
    checks.append(("ENV_NAME defined", "ENV_NAME=" in content))
  
  # Makefile uses -include (not include)
  makefile = read(service_path + "/Makefile")
  checks.append(("uses -include for env", "-include env/.env." in makefile))
  
  return evaluate_checks(checks)
```

#### SPEC-G-001: GitHub Actions Pattern

```pseudo
func check_github_actions(service_path):
  main_yaml = service_path + "/.github/workflows/main.yaml"
  
  if not exists(main_yaml):
    return { status: "NOT_APPLICABLE" }
  
  content = read(main_yaml)
  
  checks = [
    ("main.yaml triggers on push to main", "branches: [main]" in content),
    ("has lint step", "lint" in content.lower()),
    ("has test step", "test" in content.lower()),
    ("deploy depends on test", job_depends_on(content, "deploy", "test")),
    ("uses make deploy", "make deploy" in content),
    ("uses CI container", "ghcr.io/{your-org}/{service-name}" in content),
    ("deploys dev then prod", "deploy-dev" in content and "deploy-prod" in content)
  ]
  
  return evaluate_checks(checks)
```

#### SPEC-R-001: Replay Mode Support (event consumers)

```pseudo
func check_replay_mode(service_path):
  if not is_event_consumer(service_path):
    return { status: "NOT_APPLICABLE" }
  
  source = grep_all(service_path, "REPLAY_MODE", "*.go")
  
  checks = [
    ("REPLAY_MODE env var read", "REPLAY_MODE" in source),
    ("skips idempotency in replay", replay_skips_idempotency(service_path)),
  ]
  
  # {service-name} also skips side-effects
  if service_name == "{service-name}":
    checks.append(("skips side-effects in replay", 
                   replay_skips_side_effects(service_path)))
  
  return evaluate_checks(checks)
```

### Step 3: Severity Classification

```pseudo
func classify_deviation_severity(spec_id, check_name, service):
  # Security-related specs
  if spec_id in ["SPEC-A-001", "SPEC-S-001"]:
    return "critical"
  
  # Core architectural patterns
  if spec_id in ["SPEC-M-001", "SPEC-C-001", "SPEC-G-001"]:
    return "major"
  
  # Configuration patterns
  if spec_id in ["SPEC-P-001"]:
    return "minor"
  
  return "minor"
```

### Step 4: Gate Decision

```pseudo
gate_result = "PASS"

critical_deviations = [d for d in all_deviations if d.severity == "critical"]
major_deviations = [d for d in all_deviations if d.severity == "major"]

if critical_deviations:
  gate_result = "BLOCK"

elif major_deviations and deployment_target == "prod":
  gate_result = "WARN"

elif any_deviations and severity_threshold <= "minor":
  gate_result = "WARN"
```

## ERS Spec Library

Reference specs (from `{service-name}/specs/` or embedded):

| Spec ID | Name | Applies To |
|---------|------|------------|
| SPEC-M-001 | Standard Makefile Pattern | all Go services |
| SPEC-C-001 | CDK Stack Structure | all services with CDK |
| SPEC-C-002 | CDK Lambda Construct | Go Lambda services |
| SPEC-E-001 | Event Schema Versioning | {service-name}, event publishers |
| SPEC-A-001 | Auth Flow (JWT→SigV4) | gateways + backends |
| SPEC-P-001 | Configuration Standard | all services |
| SPEC-G-001 | GitHub Actions Pattern | all services |
| SPEC-R-001 | Replay Mode Support | event consumers |

## Integration

- Called by `quality-gate-orchestration` in compliance phase (parallel)
- References `{service-name}.md` and `{service-name}.md` for config checks
- Works with `spec-audit.md` skill which extracts specs from codebase
- Deviations feed `issue-diagnostic-engine` for remediation
- Auto-fixable deviations (missing Makefile target, wrong env syntax) sent to `healer-engineer`

## Success Criteria

- Verify {service-name} against all 8 applicable specs
- Report major deviation (e.g., hardcoded URL) as major severity
- Report minor deviation (e.g., missing comment) as minor severity
- Block deployment on auth/security spec violations
