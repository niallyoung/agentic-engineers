---
name: security-dependency-scan
description: Orchestrate dependency vulnerability scanning — go vuln, npm audit, cargo audit — with deployment gate
type: skill
version: 1.0
track: security
---

# security-dependency-scan

Detect known CVEs and security advisories in third-party dependencies. Detects language
automatically, runs the appropriate scanner, parses output, and returns a structured gate
decision. Critical vulnerabilities block deployment; major vulnerabilities trigger Security
Engineer review.

## Usage

```
/security-dependency-scan service_path=$WORKSPACE_ROOT/{example-service}
/security-dependency-scan service_path={service-name} fail_on_major=true
/security-dependency-scan service_path={service-name} fix_available_only=true
```

## Input

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `service_path` | str | required | Absolute or relative path to service root |
| `fail_on_critical` | bool | true | BLOCK gate if any critical vulnerability found |
| `fail_on_major` | bool | false | BLOCK gate if any major (high) vulnerability found |
| `fix_available_only` | bool | false | Only report vulnerabilities with a fix version available |

## Output

```json
{
  "service": "{example-service}",
  "language": "go",
  "scanner": "govulncheck",
  "vulnerabilities": [
    {
      "id": "GO-2026-12345",
      "package": "github.com/aws/aws-sdk-go-v2/service/s3",
      "installed_version": "1.30.0",
      "vulnerable_versions": "< 1.30.2",
      "severity": "CRITICAL",
      "description": "Path traversal in presigned URL generation allows reading arbitrary S3 objects",
      "fix_version": "1.30.2",
      "has_fix": true,
      "call_stacks": ["lambda/main.go:84 → s3client.GetObject"]
    }
  ],
  "critical_count": 1,
  "major_count": 0,
  "minor_count": 2,
  "total_count": 3,
  "gate_result": "BLOCK",
  "gate_reason": "1 critical vulnerability found — deployment blocked until resolved",
  "execution_time_sec": 18
}
```

`gate_result`: `PASS` | `WARN` | `BLOCK`

## Severity Mapping

| Scanner Severity | Normalised | Gate |
|-----------------|-----------|------|
| CRITICAL / 9.0–10.0 CVSS | CRITICAL | BLOCK (if `fail_on_critical=true`) |
| HIGH / 7.0–8.9 CVSS | MAJOR | BLOCK (if `fail_on_major=true`) / WARN |
| MEDIUM / 4.0–6.9 CVSS | MINOR | LOG |
| LOW / 0.1–3.9 CVSS | LOW | LOG |

## Implementation

### Step 1: Detect Language

```pseudo
func detect_language(service_path):
  if exists(service_path + "/go.mod"):
    return "go"
  if exists(service_path + "/package.json"):
    return "node"
  if exists(service_path + "/Cargo.toml"):
    return "rust"
  if exists(service_path + "/requirements.txt") or exists(service_path + "/pyproject.toml"):
    return "python"
  error("No dependency manifest found in " + service_path)
```

### Step 2: Run Scanner

**Go — govulncheck:**
```bash
cd {service_path}
govulncheck -json ./... 2>&1
```

If `govulncheck` is not installed:
```bash
go install golang.org/x/vuln/cmd/govulncheck@latest
govulncheck -json ./...
```

Fallback (older toolchain):
```bash
go list -json -m all | govulncheck -
```

**Node — npm audit:**
```bash
cd {service_path}
npm audit --json 2>&1
```

If using yarn:
```bash
yarn audit --json 2>&1
```

**Rust — cargo audit:**
```bash
cd {service_path}
cargo audit --json 2>&1
```

If `cargo-audit` not installed:
```bash
cargo install cargo-audit
cargo audit --json
```

**Python — pip-audit (safety fallback):**
```bash
cd {service_path}
pip-audit --format json 2>&1
# fallback:
safety check --json 2>&1
```

### Step 3: Parse Output

**Go (govulncheck JSON):**
```pseudo
func parse_govulncheck(json_output):
  results = parse_json(json_output)
  vulnerabilities = []

  for finding in results where finding.type == "finding":
    osv = finding.finding.osv
    vuln = {
      id: osv.id,                        // e.g., "GO-2026-12345"
      package: finding.finding.trace[0].module,
      description: osv.summary,
      severity: map_cvss_to_severity(osv.database_specific.severity),
      fix_version: osv.affected[0].ranges[0].events.find(e => e.fixed).fixed,
      has_fix: fix_version != null,
      call_stacks: format_call_stacks(finding.finding.trace)
    }
    vulnerabilities.append(vuln)

  return vulnerabilities
```

**Node (npm audit JSON):**
```pseudo
func parse_npm_audit(json_output):
  audit = parse_json(json_output)
  vulnerabilities = []

  for name, advisory in audit.vulnerabilities:
    vuln = {
      id: "GHSA-" + advisory.via[0].source,
      package: name,
      installed_version: advisory.nodes[0].version (from node_modules),
      vulnerable_versions: advisory.range,
      severity: advisory.severity.toUpperCase(),  // critical/high/moderate/low
      description: advisory.via[0].title,
      fix_version: advisory.fixAvailable.version or null,
      has_fix: advisory.fixAvailable != false,
      url: advisory.via[0].url
    }
    vulnerabilities.append(vuln)

  return vulnerabilities
```

**Rust (cargo audit JSON):**
```pseudo
func parse_cargo_audit(json_output):
  report = parse_json(json_output)
  vulnerabilities = []

  for vuln in report.vulnerabilities.list:
    v = {
      id: vuln.advisory.id,
      package: vuln.package.name,
      installed_version: vuln.package.version,
      description: vuln.advisory.title,
      severity: map_cvss(vuln.advisory.cvss),
      fix_version: vuln.versions.patched[0] or null,
      has_fix: len(vuln.versions.patched) > 0,
      url: vuln.advisory.url
    }
    vulnerabilities.append(v)

  return vulnerabilities
```

### Step 4: Apply fix_available_only Filter

```pseudo
if fix_available_only:
  vulnerabilities = vulnerabilities.filter(v => v.has_fix == true)
```

### Step 5: Count by Severity

```pseudo
func count_by_severity(vulnerabilities):
  return {
    critical_count: count(v where v.severity == "CRITICAL"),
    major_count:    count(v where v.severity == "MAJOR" or v.severity == "HIGH"),
    minor_count:    count(v where v.severity == "MINOR" or v.severity == "MEDIUM"),
    low_count:      count(v where v.severity == "LOW"),
    total_count:    count(vulnerabilities)
  }
```

### Step 6: Gate Decision

```pseudo
func gate_decision(counts, fail_on_critical, fail_on_major):
  if counts.critical_count > 0 and fail_on_critical:
    return {
      gate_result: "BLOCK",
      gate_reason: f"{counts.critical_count} critical vulnerability/vulnerabilities found — deployment blocked until resolved"
    }

  if counts.major_count > 0 and fail_on_major:
    return {
      gate_result: "BLOCK",
      gate_reason: f"{counts.major_count} major vulnerability/vulnerabilities found — Security Engineer review required"
    }

  if counts.major_count > 0:
    return {
      gate_result: "WARN",
      gate_reason: f"{counts.major_count} major vulnerability/vulnerabilities found — Security Engineer review recommended"
    }

  if counts.minor_count > 0 or counts.low_count > 0:
    return {
      gate_result: "PASS",
      gate_reason: f"{counts.minor_count + counts.low_count} minor/low vulnerability/vulnerabilities logged — no gate action"
    }

  return { gate_result: "PASS", gate_reason: "No vulnerabilities found" }
```

## ERS-Specific Notes

### {example-service}, {example-service}, {service-name}, {example-service}, {service-name} (Go services)

```bash
cd $WORKSPACE_ROOT/{service}
govulncheck -json ./...
```

Key dependencies to watch:
- `github.com/aws/aws-sdk-go-v2` — active CVE history; update regularly
- `github.com/lestrrat-go/jwx` — JWT library; any critical CVE blocks auth
- `github.com/aws/aws-cdk-go/awscdk/v2` — CDK synth only, lower runtime risk

```bash
// Check installed versions
cd $WORKSPACE_ROOT/{example-service}
go list -m -json all | jq '{path:.Path, version:.Version}'
```

### {service-name} (Node/TypeScript)

```bash
cd $WORKSPACE_ROOT/{service-name}
npm audit --json
```

Key dependencies:
- `vite` — build tool; CVEs affect dev only unless output is affected
- `@aws-amplify/*` — Amplify/Cognito client; monitor for auth-related CVEs
- `react`, `react-dom` — generally low CVE surface; XSS fixes are HIGH

Distinguish build-time vs runtime vulnerabilities:
```pseudo
// devDependencies CVEs are lower risk (not shipped to users)
// but BLOCK if: vulnerability affects build output (e.g., code injection in bundler)
```

### Remediation Actions

| Gate Result | Action |
|------------|--------|
| BLOCK (critical) | Do not deploy. Open PR to update affected package. Re-run scan after update. |
| BLOCK (major, `fail_on_major=true`) | Security Engineer reviews impact. If exploitable in ERS context, treat as critical. |
| WARN (major) | Security Engineer review before next production deployment. |
| PASS with minor | Log to security tracking. Schedule update in next maintenance window. |

## Escalation

```
CRITICAL → Block deployment immediately. Notify Security Engineer.
           Healer Engineer may auto-bump patch version if fix_version available + semver-compatible.
MAJOR    → Security Engineer review required before production deployment.
           Assess exploitability in ERS context (network-accessible? data-exfiltrating?).
MINOR    → Log. Schedule update. No deployment block.
```

## Integration

- Called by `quality-gate-orchestration` in parallel with `security-semantic-scan` and `security-secret-detection`
- BLOCK result halts deployment gate
- CRITICAL findings fed to `issue-diagnostic-engine` with `failure_type: "security_finding"`, `risk_level: "HIGH"`
- Healer Engineer may auto-fix if: single package, fix_version available, semver-compatible bump, no breaking API changes
- Results stored for trend tracking (CVE count over time per service)

## Success Criteria

- Detect at least one vulnerability when pointed at a service with outdated dependencies
- Report fix version and call stack for Go vulnerabilities
- Gate BLOCK correctly on critical severity
- Gate WARN (not BLOCK) on major when `fail_on_major=false`
- Handle scanner not installed gracefully (install + retry or clear error message)
