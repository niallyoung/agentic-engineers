---
name: Phase 5.3 — Security Engineer Track (Security Skills)
description: Build 3 security scanning skills for semantic analysis, dependencies, and secrets
type: delegation-brief
version: 1.0
date: 2026-04-27
---

# Phase 5.3: Security Engineer Track — Security Scanning Skills

**Delegation**: Security Engineer (Opus)  
**Timeline**: 1.5 days  
**Blocking**: None — foundational track  
**Deliverables**: 3 skill .md files + git commits

---

## Skills to Build

### 5. security-semantic-scan.md
**Purpose**: Claude-based semantic security scanning (data flow analysis, privilege escalation, injection)

**Input Spec**:
```
service_path: str
focus_areas: list = ["auth", "data_flow", "crypto"]  # optional
verify_findings: bool = True  # adversarial verification
```

**Output Spec**:
```json
{
  "service": "{service-name}",
  "findings": [
    {
      "severity": "HIGH",
      "title": "JWT scope not validated in Lambda handler",
      "description": "API Gateway validates JWT scope (e.g., 'admin'), but handler does not re-validate before processing admin-only commands",
      "file": "lambda/command/main.go:142",
      "line_range": [140, 155],
      "data_flow": "JWT (API Gateway) → Lambda handler → Command dispatch (NO scope re-check)",
      "impact": "Privilege escalation: attackers could bypass API Gateway and call Lambda directly with fake JWT",
      "remediation": "Add scope validation in handler: if !hasScope(jwt, 'admin') { return error }",
      "verified": true
    },
    {
      "severity": "MEDIUM",
      "title": "Event publisher accepts external pubkey",
      "description": "Event published to EventStore includes pubkey from request, not validated",
      "file": "handlers.go:PublishEvent()",
      "data_flow": "Request → Event → EventStore (pubkey used as-is)",
      "impact": "Event spoofing: attacker could publish events claiming to be other users",
      "remediation": "Enforce pubkey == authenticated user's pubkey",
      "verified": true
    }
  ],
  "false_positives": 0,
  "high_severity_count": 1,
  "medium_severity_count": 1,
  "execution_time_sec": 45,
  "verification_method": "Adversarial challenge: 'prove finding wrong' applied to each result"
}
```

**Implementation Notes**:
- Use Claude Opus to analyze code semantically (not pattern matching)
- Focus areas: auth (JWT, scopes, role checks), data flow (input validation), crypto (key usage), privilege escalation
- Data flow tracing: follow user input from entry point → processing → data store
- Adversarial verification: for each finding, ask Claude "why is this NOT a vulnerability?" and filter false positives
- Severity: HIGH (immediate exploit), MEDIUM (multi-step attack), LOW (requires attacker capability)
- Escalation: ALL semantic findings require Security Engineer review (not auto-fixable)

**Success Criteria**:
✓ Identify at least 1 real vulnerability in {service-name} (e.g., missing scope validation)  
✓ Report data flow chain clearly  
✓ Filter false positives via adversarial verification  
✓ Output matches spec exactly

**Related Specs**:
- QUALITY-ENGINEER-DESIGN.md § Decision 2 (Semantic Security Scanning)
- PHASE-5-SKILL-SPECIFICATIONS.md § Skill 5

---

### 6. security-dependency-scan.md
**Purpose**: Orchestrate dependency vulnerability scanning (go vuln, npm audit, cargo audit)

**Input Spec**:
```
service_path: str
fail_on_critical: bool = True
fail_on_major: bool = False
fix_available_only: bool = False
```

**Output Spec**:
```json
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
      "description": "Buffer overflow in JSON parsing",
      "fix_version": "1.2.6",
      "has_fix": true
    },
    {
      "id": "GO-2026-12346",
      "package": "github.com/aws/aws-sdk-go-v2",
      "installed_version": "1.16.0",
      "vulnerable_versions": "<=1.15.9",
      "severity": "CRITICAL",
      "description": "Authentication bypass in signature verification",
      "fix_version": "1.16.1",
      "has_fix": true
    }
  ],
  "critical_count": 1,
  "high_count": 2,
  "major_count": 1,
  "gate_result": "BLOCK",  // BLOCK if critical, WARN if major/minor
  "execution_time_sec": 12
}
```

**Implementation Notes**:
- Language detection: Go (go.mod), Node (package.json), Python (requirements.txt), Rust (Cargo.toml)
- Go: `go list -json -m all | go vuln ./...` (uses Go vulnerability database)
- Node: `npm audit --json` (npm registry vulnerabilities)
- Rust: `cargo audit --json`
- Report: vulnerability ID, package, installed version, vulnerable range, fix version
- Gate decision: CRITICAL = BLOCK, MAJOR = WARN (unless fail_on_major=true), MINOR = INFO
- Note: Haiku cost ~$0.02 per run, so batch dependency scans

**Success Criteria**:
✓ Detect vulnerable dependencies in {service-name} (if any exist)  
✓ Report available fix versions  
✓ Gate decision: BLOCK if critical found  
✓ Support Go, Node, Python, Rust languages

**Related Specs**:
- PHASE-5-SKILL-SPECIFICATIONS.md § Skill 6

---

### 7. security-secret-detection.md
**Purpose**: Detect hardcoded secrets (API keys, tokens, credentials)

**Input Spec**:
```
scan_source: str = "git_diff"  # "git_diff", "file", "commit_range"
commit_hash: str = None
fail_on_found: bool = True
```

**Output Spec**:
```json
{
  "secrets_found": 2,
  "detections": [
    {
      "type": "AWS_API_KEY",
      "file": ".env.local",
      "line": 5,
      "pattern": "AKIA...",
      "severity": "CRITICAL",
      "remediation": "Rotate AWS credentials immediately; regenerate access keys"
    },
    {
      "type": "PRIVATE_KEY",
      "file": "lambda/secrets/key.pem",
      "line": 1,
      "severity": "CRITICAL",
      "remediation": "Delete file; regenerate key; add *.pem to .gitignore"
    }
  ],
  "gate_result": "BLOCK"
}
```

**Implementation Notes**:
- Scan source options:
  - `git_diff`: scan staged files + unstaged changes (pre-commit context)
  - `file`: scan single file path
  - `commit_range`: scan commits between two hashes
- Tools: truffleHog, GitHub secret scanning patterns, or custom regex
- Secret patterns: AWS API keys (AKIA), private keys (PEM/RSA), tokens (jwt, bearer), credentials (username:password)
- Severity: ALWAYS CRITICAL for detected secrets
- Gate: BLOCK immediately if any secrets found
- Escalation: require Security Engineer to review before allowing commit

**Success Criteria**:
✓ Detect hardcoded AWS credentials (if injected for test)  
✓ Detect hardcoded API tokens  
✓ Block deployment if secrets found  
✓ Support git_diff mode (pre-commit use case)

**Related Specs**:
- PHASE-5-SKILL-SPECIFICATIONS.md § Skill 7

---

## Integration Points

**After This Track**:
- Dependency scan results feed into `issue-diagnostic-engine.md` (track 4)
- Semantic scan findings feed into escalation (Security Engineer review)
- Secret detection blocks pre-deployment (hard stop)

**Inputs from Previous Tracks**:
- Test failures from Track 1 may reveal security issues (e.g., missing validation)
- Requirement coverage from Track 3 may expose untested security paths

**Success Criteria for Track**:
- All 3 skills implemented + tested locally
- Each skill callable as independent module or CLI
- Output JSON matches spec exactly
- Real vulnerabilities detected (semantic scan finds ≥1 actual issue)

---

## Implementation Steps

1. **Create skill files** (hours 0-2):
   - security-semantic-scan.md
   - security-dependency-scan.md
   - security-secret-detection.md

2. **Implement in parallel** (hours 2-24):
   - Semantic scan: Claude Opus + data flow analysis
   - Dependency scan: language detection + tool orchestration
   - Secret detection: pattern matching + git integration
   - Test against real ERS services

3. **Validate** (hours 24-28):
   - Run semantic scan on {service-name}, find real issue
   - Run dependency scan on all services
   - Run secret detection on git diffs

4. **Git commit**:
   - One commit per skill file: `feat(skills): add security-semantic-scan skill`
   - Sign-off: verify with Security Engineer for semantic findings

---

## Security Best Practices

- Semantic scan: run as Opus (higher context, better analysis) vs. Haiku for simple tasks
- Dependency scan: cache results if unchanged (don't re-scan on every commit)
- Secret detection: fail fast, never log detected secrets
- False positives: semantic scan may flag legitimate patterns; adversarial verification helps filter

---

## Success Definition

Track is complete when:
- [ ] All 3 .md skill files created in `/skills/`
- [ ] Each file includes: purpose, input spec, output spec, implementation notes
- [ ] Semantic scan finds ≥1 real vulnerability
- [ ] Dependency scan reports accurate counts
- [ ] Secret detection works on git_diff
- [ ] All output JSON matches spec
- [ ] All 3 committed to git with clear messages

---

**Version**: 1.0  
**Status**: Ready for delegation  
**Owner**: Security Engineer (Opus)  
**Start Date**: 2026-04-27  
**Target Date**: 2026-04-29
