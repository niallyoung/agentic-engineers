---
name: Security Agent Implementation
type: agent-implementation
phase: 5.10
---

# Security Agent — LIVE IMPLEMENTATION

**Role**: Security Engineer  
**Model**: claude-opus-4-7  
**Effort**: max  

## Agent Logic

```
WHEN Orchestrator writes DELEGATE to artifacts/:

1. READ: DELEGATE block
   - Extract: repo_path, service_name, commit_sha
   
2. SCAN repository:
   - Grep for credential patterns:
     * AWS_SECRET_ACCESS_KEY, DATABASE_PASSWORD, PRIVATE_KEY, etc.
     * Regex patterns for common secrets
   
   - Check IAM/permissions:
     * Admin-level access in configs
     * World-readable files
     * Overpermissioned roles
   
   - Analyze code for vulnerabilities:
     * SQL injection risks
     * XSS vulnerabilities
     * Authentication bypasses
     * Cryptography weaknesses
   
3. CATEGORIZE findings:
   - severity: INFO, LOW, MEDIUM, HIGH, CRITICAL
   - type: credential, permission, vulnerability, config
   - location: file:line
   
4. WRITE HANDBACK:
   findings_count = len(all_findings)
   max_severity = max(finding.severity for finding in all_findings)
   
   status = "PASS" if findings_count == 0 else "FAIL"
   severity = max_severity
   confidence = 0.95 if findings_count >= 0 else 0.85  // high confidence in finding nothing
   
   HANDBACK = {
     handoff_type: "HANDBACK",
     task_id: ...,
     status: status,
     severity: severity,
     findings_count: findings_count,
     findings: [
       {type, severity, file, line, description}
     ],
     confidence: confidence,
     recommendation: "Review and remediate findings" if status == FAIL else "Pass"
   }

5. WRITE SPAN to artifacts/SPAN-{timestamp}-agent-security.yaml
```

## HANDBACK Format

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-26-commit-{service-name}
timestamp: 2026-05-26T09:03:45Z
status: PASS  # or FAIL
severity: INFO  # or LOW, MEDIUM, HIGH, CRITICAL
findings_count: 0
findings: []
confidence: 0.99
recommendation: "No security issues detected"
attributes:
  files_scanned: 45
  credentials_found: 0
  permission_issues: 0
  vulnerabilities: 0
```
