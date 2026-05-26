---
name: spec-validator
description: Validates implementation compliance with SPEC.md. Parses SPEC.md requirements and constraints, analyzes git diffs, detects violations and rollbacks, and generates compliance reports. Use as a pre-merge gate or post-merge audit to prevent spec drift.
license: Proprietary
compatibility: agentic-engineers framework v5.10+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: governance
  role: quality-engineer
  trigger: pre-merge | on-demand | post-merge-audit
---

## Overview

Spec-Validator enforces implementation compliance with `SPEC.md`. It reads the specification, analyzes code changes (git diffs), and produces actionable compliance reports identifying:

1. **Constraint violations** — Code changes that break `MUST NOT` rules
2. **Requirement regressions** — Deletions that roll back mandatory features  
3. **Undocumented changes** — Code touching domains not covered by the SPEC
4. **Rollback detections** — Feature deletions without corresponding SPEC updates

Works alongside **spec-management** (which governs changes *to* SPEC.md).  
This skill governs changes *against* SPEC.md.

**What it does:**
1. Parses SPEC.md — extracts requirements (REQ-NNN), features, and constraints
2. Analyzes the git diff — identifies modified, added, and deleted files
3. Correlates diff hunks with SPEC sections via keyword matching
4. Checks compliance — detects constraint violations and security heuristics
5. Detects gaps — finds undocumented changes and spec drift
6. Detects rollbacks — identifies deleted files that remove mandatory features
7. Generates reports — produces JSON (machine-parseable) and Markdown (human-readable) output

## Invocation

### Pre-Merge Gate (CI/CD)
```bash
# Fail the pipeline if violations are found
git diff main...HEAD > /tmp/changes.diff
python scripts/spec_validator.py --spec docs/SPEC.md --diff /tmp/changes.diff --mode pre-merge
# Exit code: 0 = pass, 1 = violations found, 2 = error
```

### Audit Mode (post-merge or manual)
```bash
# Always produces a report; never fails the pipeline
python scripts/spec_validator.py \
  --spec docs/SPEC.md \
  --diff /tmp/changes.diff \
  --mode audit \
  --format json \
  --output artifacts/compliance-report.json
```

### Read diff from stdin
```bash
git diff HEAD~1 | python scripts/spec_validator.py --spec docs/SPEC.md --stdin --mode pre-merge
```

### Python API
```python
from src.skills.spec_validator.scripts.spec_validator import SpecValidator, ValidationMode  # note: Python module uses underscore (spec_validator) since hyphens are invalid in module names

validator = SpecValidator()
result = validator.validate(
    spec_content=open("docs/SPEC.md").read(),
    diff_content=open("changes.diff").read(),
    mode=ValidationMode.PRE_MERGE,
)

if not result.passed:
    print(f"Compliance FAILED: {result.compliance_result.critical_count} critical violations")
    for v in result.compliance_result.violations:
        print(f"  [{v.severity.value}] {v.rule}: {v.description}")
```

## SPEC.md Format Requirements

The validator expects SPEC.md to use standard patterns:

### Requirements
```markdown
### REQ-001: Authentication
All API endpoints MUST require authentication using JWT bearer tokens.
Unauthenticated requests MUST return HTTP 401.
```

### Features  
```markdown
## Features
- **Feature A**: User authentication via JWT tokens. REQUIRED.
- **Feature B**: Dark mode support. OPTIONAL.
```

### Constraints
```markdown
## Constraints
- MUST NOT store plaintext passwords.
- MUST NOT expose internal stack traces to clients.
- MUST use TLS 1.2+ for all connections.
```

## Output Formats

### JSON Report (machine-parseable)
```json
{
  "overall_status": "FAIL",
  "generated_at": "2025-01-01T12:00:00+00:00",
  "summary": "Violations: 1 (CRITICAL=1, HIGH=0, MEDIUM=0, LOW=0) | Gaps: 0 | Rollbacks: 0",
  "violations": [
    {
      "rule": "CONSTRAINT-MUST-NOT-STORE-PLAINTEX",
      "description": "Constraint violated: MUST NOT store plaintext passwords.",
      "severity": "CRITICAL",
      "file_path": "src/users.py",
      "evidence": "return self.db.insert(username=username, password=password)"
    }
  ],
  "gaps": [],
  "rollbacks": []
}
```

### Markdown Report (human-readable)
```markdown
# Spec-Validator Compliance Report

**Status:** ❌ **FAIL**
**Generated:** 2025-01-01T12:00:00+00:00

## Summary
Violations: 1 (CRITICAL=1, HIGH=0, ...) | Gaps: 0 | Rollbacks: 0

## Violations (1)

### 🔴 [CRITICAL] CONSTRAINT-MUST-NOT-STORE-PLAINTEX
**Description:** Constraint violated: MUST NOT store plaintext passwords.
**File:** `src/users.py`
**Evidence:**
```
return self.db.insert(username=username, password=password)
```
```

## Validation Modes

| Mode | Behavior | Exit Code |
|------|----------|-----------|
| `pre-merge` | Strict — fails if ANY CRITICAL or HIGH violation found | 1 on fail |
| `audit` | Lenient — always produces full report, never blocks | 0 always |

## Violation Severities

| Severity | Trigger |
|----------|---------|
| CRITICAL | `MUST NOT` constraint violated (e.g. plaintext passwords) |
| HIGH | Mandatory requirement regressed by file deletion |
| MEDIUM | Potential stack trace exposure, risky patterns |
| LOW | Informational — style / convention issues |

## CI/CD Integration

### GitHub Actions
```yaml
- name: Spec Compliance Check
  run: |
    git diff ${{ github.event.before }}...${{ github.sha }} > /tmp/changes.diff
    python src/skills/spec-validator/scripts/spec_validator.py \
      --spec docs/SPEC.md \
      --diff /tmp/changes.diff \
      --mode pre-merge \
      --format json \
      --output artifacts/spec-compliance.json
```

### Pre-commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit
git diff --cached > /tmp/staged.diff
python src/skills/spec-validator/scripts/spec_validator.py \
  --spec docs/SPEC.md \
  --diff /tmp/staged.diff \
  --mode pre-merge
```

## Architecture

```
SpecValidator (orchestrator)
├── SpecParser       — parse SPEC.md, extract requirements/features/constraints
├── DiffAnalyzer     — parse unified diffs, correlate hunks with SPEC sections
├── ComplianceChecker — detect violations (constraints + security heuristics)
├── GapDetector      — detect undocumented changes + rollbacks
└── ComplianceReporter — render JSON and Markdown reports
```

## Configuration

No external configuration required. The validator:
- Reads SPEC.md from the path you provide (`--spec`)
- Reads the diff from a file (`--diff`), stdin (`--stdin`), or via Python API
- Outputs reports to stdout or a file (`--output`)
- Uses keyword-based heuristics (no external NLP/ML dependencies)

## Constraints

- Does **not** modify SPEC.md — that is the responsibility of `spec-management`
- Does **not** require network access
- Does **not** execute the code being validated
- Works on any unified diff format (`git diff`, `git format-patch`, `diff -u`)
- Python 3.7+ compatible; no third-party dependencies

## SPAN Capture

After each validation run, capture a SPAN with:
- `spec_sections_parsed`: count of sections found in SPEC.md
- `requirements_found`: count of REQ-NNN requirements
- `violations_total`: total violations detected
- `overall_status`: PASS / WARN / FAIL
- `mode`: pre-merge / audit
