---
name: spec-audit
description: Validates services against canonical ERS patterns and reports compliance gaps
type: skill
applies_to: [agentic-engineers framework, ERS services]
phase: "Phase 3 Implementation"
---

# spec-audit Skill — Service Compliance Validation

Validates services against 8 canonical ERS architectural patterns. Reports compliance gaps with remediation guidance.

**Inverse of spec-extract**: While spec-extract discovers patterns, spec-audit validates against them.

## Quick Start

```bash
# Audit current service
/spec-audit .

# Audit specific service
/spec-audit {workspace-root}/{service-name}

# With options
/spec-audit {workspace-root}/{service-name} --fail-on-critical --json
```

## Patterns Validated (8 Total)

| ID | Pattern | Validates |
|----|---------|-----------|
| P-001 | Makefile 3-Phase | lint→test→build→deploy structure |
| P-002 | Environment Sourcing | env/ files, Makefile sourcing |
| P-003 | GitHub Actions | branch.yaml, main.yaml workflows |
| P-004 | CDK Stack | cdk/ structure, ENV_NAME injection |
| P-005 | Go Modules | go.mod, module path, dependencies |
| P-006 | Lambda Handler | lambda.Start(), handler signatures |
| P-007 | Table-Driven Testing | *_test.go files, test pattern |
| P-008 | Security Patterns | JWT, OAuth, SigV4, secrets |

## Usage

### Basic

```bash
/spec-audit /path/to/service
# Outputs: Console summary + audit report in ./audit/
```

### With Options

```bash
# Dry-run (no files written)
/spec-audit /path/to/service --no-write

# Specific patterns only
/spec-audit /path/to/service --patterns P-001,P-002,P-003

# Fail on critical deviations (for CI/pre-push)
/spec-audit /path/to/service --fail-on-critical

# JSON output (for CI integration)
/spec-audit /path/to/service --json

# Custom report directory
/spec-audit /path/to/service --output-dir /custom/audit/path
```

## Output Format

### Console Output

```
Auditing: {service-name}

  P-001 Makefile 3-Phase                    ✓ COMPLIANT (100%)
  P-002 Environment Sourcing                ✓ COMPLIANT (100%)
  P-003 GitHub Actions                      ◐ PARTIAL (88%)
  P-004 CDK Stack                           ✓ COMPLIANT (100%)
  P-005 Go Modules                          ✓ COMPLIANT (100%)
  P-006 Lambda Handler                      ✓ COMPLIANT (100%)
  P-007 Table-Driven Testing                ✓ COMPLIANT (100%)
  P-008 Security Patterns                   ✓ COMPLIANT (100%)

Service Compliance: 7.5/8 patterns (93.75%)
Audit Report: ./audit/{service-name}.md

Status: 0 critical, 1 minor deviations
```

### Audit Report (Markdown)

```markdown
# Audit Report: {service-name}

**Generated**: 2026-04-27
**Service**: {service-name}
**Overall Compliance**: 7.5/8 patterns

## Pattern-by-Pattern Results

### P-001: Makefile 3-Phase
- **Status**: ✓ COMPLIANT (100%)
- **Heuristics Met**: 5/5

### P-003: GitHub Actions
- **Status**: ◐ PARTIAL (88%)
- **Heuristics Met**: 4/5
- **Deviations**:
  - H5: Deploy depends on lint and test [MINOR]

[... continue for all patterns ...]
```

### JSON Output (`--json` flag)

```json
{
  "service": "{service-name}",
  "overall_compliance": {
    "patterns_compliant": 7,
    "patterns_total": 8,
    "compliance_percentage": 87.5
  },
  "patterns": [
    {
      "pattern_id": "P-001",
      "status": "COMPLIANT",
      "compliance_percentage": 100,
      "deviations": []
    }
  ]
}
```

## Severity Levels

### CRITICAL
- **Required heuristic missing entirely**
- **Example**: No Makefile at service root
- **Impact**: Fundamentally non-compliant
- **Action**: Must fix before deployment
- **Exit Code**: 1 (if `--fail-on-critical`)

### MAJOR
- **Required pattern element missing**
- **Example**: 'deploy' target missing from Makefile
- **Impact**: Partial non-compliance
- **Action**: Should fix soon
- **Exit Code**: 0 (default)

### MINOR
- **Optional enhancement or acceptable variation**
- **Example**: Missing 'help' target in Makefile
- **Impact**: Negligible
- **Action**: Nice-to-have
- **Exit Code**: 0

## Compliance Calculation

```
Compliance % = (Required heuristics met / Total required heuristics) × 100

Pattern Status:
- ✓ COMPLIANT: All required heuristics met (≥100%)
- ◐ PARTIAL: Some required heuristics missing (50-99%)
- ✗ NON_COMPLIANT: Critical heuristics missing (<50%)

Service Overall:
- Compliance Score: (Compliant patterns / Total patterns) × 100%
```

## Integration Points

### Standalone

Use for manual audits and reporting:
```bash
/spec-audit {workspace-root}/{service-name}
cat ./audit/{service-name}.md  # Review findings
```

### Pre-push Hook (Future)

```bash
/spec-audit . --fail-on-critical
# Exit 1 if critical deviations found, preventing push
```

### CI/CD Pipeline

```bash
/spec-audit . --json | jq '.overall_compliance.compliance_percentage'
# Use in GitHub Actions or other CI for policy enforcement
```

## Examples

### Audit Single Service

```bash
cd {workspace-root}/{service-name}
/spec-audit .
# Outputs audit report to ./audit/{service-name}.md
```

### Batch Audit All Services

```bash
for service in {service-name} {service-name} {service-name} {service-name} {service-name} {service-name} {service-name} {service-name}; do
  echo "Auditing $service..."
  /spec-audit {workspace-root}/$service --output-dir {workspace-root}/{service-name}/audits
done
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Audit service compliance
  run: |
    /spec-audit . --fail-on-critical --json > audit-report.json
    echo "Compliance: $(jq '.overall_compliance.compliance_percentage' audit-report.json)%"
```

### Pre-push Hook (When Available)

```bash
# In .git/hooks/pre-push (future integration)
/spec-audit . --fail-on-critical || exit 1
```

## Understanding Deviations

Each deviation report includes:
- **Pattern ID** & **Heuristic ID**: Which pattern/heuristic failed
- **Description**: What was expected
- **Severity**: Critical/Major/Minor
- **Issue**: What's missing or wrong
- **Guidance**: How to fix it

### Example Deviation

```
Pattern: P-008 (Security Patterns)
Heuristic: H3 (Refresh token rotation)
Severity: MAJOR
Issue: No refresh token rotation detected
File: lambda/identity/main.go (line 142)
Guidance: Implement 30-day token refresh cycle using CloudWatch scheduled event
Reference: PATTERN-HEURISTICS.md (P-008)
```

## Exit Codes

| Code | Meaning | Trigger |
|------|---------|---------|
| 0 | Compliant or no critical issues | Default (unless --fail-on-critical) |
| 1 | Critical deviations found | `--fail-on-critical` flag set AND critical issues present |

## Skill Architecture

**Tool**: Copilot Skill (integrated with Claude Code)  
**Runtime**: Python 3.11+  
**Location**: `agentic-engineers/skills/spec-audit/`

**Design rationale**: 
- Same as spec-extract: no supply chain risk, familiar to ERS team
- Validates against PATTERN-HEURISTICS.md (single source of truth)
- Produces both human-readable (Markdown) and machine-readable (JSON) output
- Supports future pre-push hook integration

## Known Limitations

1. **Heuristic matching**: Uses regex/file checks, not semantic analysis
   - Cannot verify that JWT validation checks issuer/audience/expiry
   - Cannot verify that cdk synth succeeds
   - Cannot verify test coverage percentage

2. **False positives/negatives**: May flag acceptable variations as deviations
   - Will be refined through Phase 4 testing

3. **No execution**: Does not run `make lint`, `go test`, or `cdk synth`
   - Only static analysis

These are design trade-offs for speed and safety. Phase 4 validation testing will refine heuristics.

## Related Skills

- `spec-extract.md` — Discovers patterns and generates specs (inverse of spec-audit)
- `planning-standard.md` — TODO.md-only planning
- `engineer-execution.md` — Task execution with escalation

## See Also

- `SPEC-AUDIT-DESIGN.md` — Full architecture design document
- `PATTERN-HEURISTICS.md` — Canonical pattern definitions (8 patterns)
- `{service-name}/specs/INDEX.md` — Phase 2 discovery output (58 spec files)
