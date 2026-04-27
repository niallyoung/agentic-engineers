---
name: security-secret-detection
description: Detect hardcoded secrets — AWS credentials, API keys, private keys, JWT tokens — with immediate deployment block
type: skill
version: 1.0
track: security
---

# security-secret-detection

Detect hardcoded secrets before they reach the repository or are deployed. Conservative
pattern matching errs toward false positives over false negatives — a missed secret is
far worse than a false alarm. Any detection is CRITICAL severity and immediately blocks
deployment.

## Usage

```
/security-secret-detection
/security-secret-detection scan_source=git_diff
/security-secret-detection scan_source=commit_range commit_hash=abc123..HEAD
/security-secret-detection scan_source=file fail_on_found=false
```

## Input

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `scan_source` | str | `git_diff` | Source to scan: `git_diff`, `file`, `commit_range` |
| `commit_hash` | str | null | For `commit_range`: `abc123..HEAD` or single commit hash |
| `fail_on_found` | bool | true | BLOCK gate if any secret detected |

## Output

```json
{
  "scan_source": "git_diff",
  "secrets_found": 2,
  "detections": [
    {
      "type": "AWS_ACCESS_KEY_ID",
      "file": ".env.local",
      "line": 5,
      "match": "AKIA...REDACTED",
      "context": "AWS_ACCESS_KEY_ID=AKIA...",
      "severity": "CRITICAL"
    },
    {
      "type": "PRIVATE_KEY_PEM",
      "file": "lambda/secrets/key.pem",
      "line": 1,
      "match": "-----BEGIN RSA PRIVATE KEY-----",
      "context": "-----BEGIN RSA PRIVATE KEY-----",
      "severity": "CRITICAL"
    }
  ],
  "gate_result": "BLOCK",
  "gate_reason": "2 secret(s) detected — deployment blocked, immediate rotation required",
  "remediation": [
    "Rotate all detected credentials immediately — assume compromised",
    "Remove secrets from file(s) — use environment variables or AWS Secrets Manager",
    "git filter-branch or BFG Repo-Cleaner to purge from git history if committed",
    "Check git log to confirm secret was not previously committed"
  ]
}
```

`gate_result`: `PASS` | `BLOCK`

All detections are severity `CRITICAL`. There are no lower severity levels for secrets.

## Secret Pattern Library

```pseudo
PATTERNS = [
  // AWS credentials
  {
    type: "AWS_ACCESS_KEY_ID",
    regex: r"(?i)(AWS_ACCESS_KEY_ID|aws_access_key)[^=]*=\s*['\"]?(AKIA[0-9A-Z]{16})['\"]?",
    also: r"\bAKIA[0-9A-Z]{16}\b"   // raw key anywhere in file
  },
  {
    type: "AWS_SECRET_ACCESS_KEY",
    regex: r"(?i)(AWS_SECRET_ACCESS_KEY|aws_secret)[^=]*=\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?",
    note: "40-char base64 string in secret key context"
  },
  {
    type: "AWS_SESSION_TOKEN",
    regex: r"(?i)(AWS_SESSION_TOKEN)[^=]*=\s*['\"]?([A-Za-z0-9/+=]{100,})['\"]?"
  },

  // Private keys (PEM format)
  {
    type: "PRIVATE_KEY_PEM",
    regex: r"-----BEGIN\s+(RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
  },
  {
    type: "CERTIFICATE",
    regex: r"-----BEGIN CERTIFICATE-----",
    note: "Certs themselves are public, but flag for review — may be bundled with private key"
  },

  // Generic high-entropy tokens
  {
    type: "GENERIC_API_KEY",
    regex: r"(?i)(api_key|apikey|api-key)[^=]*[=:]\s*['\"]?([A-Za-z0-9_\-]{20,})['\"]?",
    note: "Conservative: 20+ char value in key= context"
  },
  {
    type: "GENERIC_SECRET",
    regex: r"(?i)(secret|password|passwd|pwd|token)[^=]*[=:]\s*['\"]?([^\s'\"]{8,})['\"]?",
    exclude_patterns: [
      "placeholder", "changeme", "your-secret-here", "xxxxx", "<secret>",
      "${", "%(", "{{",      // template variables
      "os.Getenv", "process.env", "ssm.GetParameter",  // env var references
      "example", "sample", "test", "dummy", "fake"
    ]
  },

  // JWT tokens
  {
    type: "JWT_TOKEN",
    regex: r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
    note: "base64url-encoded JWT: header.payload.signature"
  },

  // Database connection strings
  {
    type: "DATABASE_URL",
    regex: r"(?i)(DATABASE_URL|DB_PASSWORD|POSTGRES_PASSWORD|MYSQL_PASSWORD)[^=]*=\s*['\"]?[^\s'\"]{8,}['\"]?",
    exclude_patterns: ["${", "%(", "{{", "os.Getenv", "process.env"]
  },

  // OAuth / third-party tokens
  {
    type: "GITHUB_TOKEN",
    regex: r"(?i)(github_token|gh_token|GITHUB_PAT)[^=]*=\s*['\"]?(ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{82})['\"]?"
  },
  {
    type: "SLACK_TOKEN",
    regex: r"xox[baprs]-[0-9A-Za-z\-]+"
  },
  {
    type: "STRIPE_KEY",
    regex: r"(sk_live_|pk_live_|rk_live_)[0-9a-zA-Z]{24}"
  },

  // ERS-specific
  {
    type: "COGNITO_CLIENT_SECRET",
    regex: r"(?i)(cognito.*secret|client_secret)[^=]*=\s*['\"]?([A-Za-z0-9+/]{30,})['\"]?",
    exclude_patterns: ["${", "process.env", "os.Getenv", "ssm"]
  }
]
```

## Implementation

### Step 1: Acquire Scan Content

```pseudo
func get_scan_content(scan_source, commit_hash):
  if scan_source == "git_diff":
    // Staged + unstaged changes
    content = run("git diff HEAD")
    if empty: content = run("git diff --cached")
    return { type: "diff", content: content }

  if scan_source == "commit_range":
    if commit_hash is None: error("commit_hash required for commit_range")
    content = run(f"git show {commit_hash} --unified=0")
    // For range: git log --patch {commit_hash}
    return { type: "diff", content: content }

  if scan_source == "file":
    // Scan all non-binary files in current directory tree
    files = run("git ls-files")  // only tracked files
    return { type: "files", files: files }
```

### Step 2: Parse Diff Into Lines (diff mode)

```pseudo
func parse_diff_lines(diff_content):
  // Only scan added lines (prefixed with "+"), not removed lines
  // Removed lines contain old secrets already in history — flag separately if needed
  lines = []
  current_file = null

  for line in diff_content.split("\n"):
    if line.startswith("diff --git"):
      current_file = extract_filename(line)   // "b/path/to/file"
    elif line.startswith("+++ b/"):
      current_file = line[6:]                  // strip "+++ b/"
    elif line.startswith("@@ "):
      current_line_number = extract_line_number(line)  // @@ -old +new @@
    elif line.startswith("+") and not line.startswith("+++"):
      lines.append({
        file: current_file,
        line_number: current_line_number,
        content: line[1:]   // strip leading "+"
      })
      current_line_number += 1

  return lines
```

### Step 3: Scan Lines Against Patterns

```pseudo
func scan_lines(lines, patterns):
  detections = []

  for line in lines:
    // Skip binary files
    if is_binary_file(line.file): continue

    // Skip known false-positive file types
    if line.file.endswith((".png", ".jpg", ".gif", ".zip", ".woff", ".woff2")): continue

    // Skip test fixture files (but log warning — test files should not contain real secrets)
    if "testdata/" in line.file or "_test.go" in line.file:
      // still scan but lower confidence — log as potential_false_positive
      pass

    for pattern in patterns:
      match = regex_search(pattern.regex, line.content)
      if match:
        // Apply exclusion filters
        if any(excl in line.content for excl in pattern.get("exclude_patterns", [])):
          continue   // skip: likely a template variable or reference

        // Redact the matched value in output (show prefix only)
        redacted_match = redact(match.group(0))

        detections.append({
          type: pattern.type,
          file: line.file,
          line: line.line_number,
          match: redacted_match,
          context: redact_value_in_line(line.content),
          severity: "CRITICAL"
        })

  return detections


func redact(match):
  // Show first 4 chars + "...REDACTED" to aid identification without exposing full secret
  if len(match) > 8:
    return match[:4] + "...REDACTED"
  return "...REDACTED"
```

### Step 4: File Mode Scanning

```pseudo
func scan_files(file_list, patterns):
  detections = []

  for filepath in file_list:
    // Skip vendored, generated, and binary files
    if any(skip in filepath for skip in ["vendor/", "node_modules/", ".git/", "dist/", "build/"]):
      continue

    content = read_file(filepath)
    lines = content.split("\n")

    for i, line_content in enumerate(lines):
      line = { file: filepath, line_number: i+1, content: line_content }
      detections.extend(scan_lines([line], patterns))

  return detections
```

### Step 5: Gate Decision

```pseudo
func gate_decision(detections, fail_on_found):
  if len(detections) == 0:
    return {
      gate_result: "PASS",
      gate_reason: "No secrets detected"
    }

  if fail_on_found:
    return {
      gate_result: "BLOCK",
      gate_reason: f"{len(detections)} secret(s) detected — deployment blocked, immediate rotation required",
      remediation: [
        "Rotate all detected credentials immediately — assume compromised",
        "Remove secrets from file(s) — use environment variables or AWS Secrets Manager",
        "git filter-branch or BFG Repo-Cleaner to purge from git history if committed",
        "Check git log to confirm secret was not previously committed"
      ]
    }
  else:
    return {
      gate_result: "BLOCK",   // secrets are always BLOCK regardless of fail_on_found
      gate_reason: f"{len(detections)} secret(s) detected (fail_on_found=false but severity is always CRITICAL)"
    }
```

Note: `fail_on_found=false` is provided for audit/reporting use only. The `gate_result` is still
`BLOCK` because secrets are always critical. The parameter only suppresses the non-zero exit code
in scripted contexts where the caller handles the gate result independently.

## ERS-Specific Patterns

### What should never be hardcoded in ERS repositories

```
AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY  → Use IAM roles (Lambda execution role)
Cognito Client Secret                       → Stored in SSM Parameter Store
JWT signing keys                            → Cognito-managed, never in code
Database passwords                          → Not applicable (DynamoDB uses IAM)
SNS/SQS ARNs are NOT secrets                → ARNs are public identifiers, not credentials
GitHub PAT / Actions secrets                → GitHub Actions secrets, not in code
SES SMTP credentials                        → Use IAM + SES API (not SMTP with password)
```

### .env files in ERS services

ERS services use `env/.env.{ENV_NAME}` files for non-secret configuration (see config standard).
These files should contain only:
- Non-secret configuration (APP_NAME, ENV_NAME, region)
- SSM Parameter Store paths (not the values themselves)
- Feature flags

They must NOT contain:
- AWS credentials (use IAM roles)
- API keys or tokens
- Passwords

```bash
// Verify .env files are in .gitignore
grep -r "\.env\." .gitignore
// ERS standard: env/.env.* should be in .gitignore
```

### CDK stacks

CDK stacks must not hardcode account IDs, access keys, or secrets. Use:
```go
// Good: fetch from SSM at synth time
ssm.StringParameter_ValueForStringParameter(stack, jsii.String("param"), jsii.String("/ers/myapp/secret-arn"))

// Bad: hardcoded in stack
os.Getenv("AWS_SECRET_ACCESS_KEY")  // must not appear in CDK code either
```

## Integration with Git Hooks

This skill is designed to run in the `pre-commit` and `pre-push` hooks:

```bash
// pre-commit: scan staged changes
/security-secret-detection scan_source=git_diff

// pre-push: scan all commits being pushed
/security-secret-detection scan_source=commit_range commit_hash=origin/main..HEAD
```

Hook integration pseudo-code:
```bash
result=$(claude /security-secret-detection scan_source=git_diff)
gate=$(echo $result | jq -r '.gate_result')
if [ "$gate" == "BLOCK" ]; then
  echo "SECRET DETECTED — commit blocked"
  echo $result | jq '.detections'
  exit 1
fi
```

## Escalation

```
Any secret detected → BLOCK deployment immediately
                    → Rotate credential (assume compromised from moment of detection)
                    → Purge from git history
                    → Notify Security Engineer
                    → Post-incident: audit access logs for the leaked credential
```

**Do not:**
- Delay rotation pending investigation — rotate first, investigate after
- Assume "it was only in a local branch" — branches are often pushed accidentally
- Treat test fixtures containing real credentials as lower risk — they are the same risk

## Integration

- Called by `quality-gate-orchestration` in parallel with other security scans
- Also called directly from `pre-commit` and `pre-push` git hooks (ERS standard)
- BLOCK result immediately halts the quality gate — no further scans needed
- Detections reported to Security Engineer (never to Healer — secrets require human rotation)
- `issue-diagnostic-engine` receives detection with `failure_type: "security_finding"`, `risk_level: "HIGH"`, `healer_eligible: false`

## Success Criteria

- Detect `AKIA` AWS access key anywhere in diff or file content
- Detect PEM private key header
- Detect JWT token (`eyJ...`) hardcoded in source file
- Pass cleanly when values are environment variable references (`os.Getenv`, `process.env`, `${VAR}`)
- Gate BLOCK on any detection regardless of `fail_on_found` value
- Redact matched values in output (never log full secret)
