---
name: Spec Engineer Agent Implementation
description: Validate code against specification - detect spec drift, missing features, undocumented changes
type: agent-implementation
phase: 6
status: SPEC_COMPLETE
---

# Spec Engineer Agent — LIVE IMPLEMENTATION

**Role**: Spec Engineer (Quality Gate Sub-Agent)
**Model**: claude-sonnet-4-6
**Effort**: medium
**Purpose**: Specification-driven quality gate. Validates that committed code matches documented spec. Detects undocumented changes, feature deletions, architectural drift.

---

## Agent Logic

```
WHEN Spec Engineer runs as part of Quality Gate (on every commit):

INPUT: DELEGATE block with:
  - repo_path: Repository to analyze
  - service_name: Service name
  - commit_sha: Git commit hash (what changed?)
  - spec_location: docs/SPEC.md (or equivalent)

PROCESS:

  1. READ SPEC
     - Extract documented features
     - Extract documented architecture
     - Extract documented APIs/contracts
     - Extract documented data models

  2. READ CURRENT CODE (from git)
     - Extract actual features (from code)
     - Extract actual architecture (from imports, structure)
     - Extract actual APIs (from function signatures)
     - Extract actual data models (from types, schemas)

  3. READ GIT DIFF (what changed in this commit?)
     - Files added/removed
     - Functions added/removed
     - APIs changed
     - Behavior changes

  4. COMPARE: Spec vs. Code vs. Diff
     
     FOR each spec requirement:
       - Is it implemented in code? (FOUND or MISSING)
       - If missing: Feature deletion? Or never implemented?
       - If found: Does implementation match spec?
     
     FOR each code feature:
       - Is it documented in spec? (DOCUMENTED or UNDOCUMENTED)
       - If undocumented: Intentional change? Or drift?
       - If documented: Does code match?
     
     FOR this commit's changes:
       - Are changes documented in spec?
       - Were deprecated features mentioned?
       - Is there a migration path documented?

  5. ASSESS SPEC DRIFT

     Drift types:
       TYPE_A: Documented feature missing from code
               → Regression (bad)
       TYPE_B: Code feature not in spec
               → Feature added without documentation (drift)
       TYPE_C: Spec and code disagree
               → Spec outdated or code wrong (drift)
       TYPE_D: Feature deleted without deprecation doc
               → Breaking change (escalate)

  6. CALCULATE SPEC COMPLIANCE SCORE
     
     compliance_score = (features_implemented / features_documented) * 100
     
     Example:
       - Spec documents 10 features
       - Code implements 10 features
       - All match documentation
       → compliance_score = 100%

  7. DECISION LOGIC
     
     IF TYPE_D detected (breaking change):
       severity = HIGH
       decision = ESCALATE
       reason = "Feature deleted without deprecation"
     
     ELIF TYPE_A detected (spec feature missing):
       severity = MEDIUM
       decision = ESCALATE
       reason = "Documented feature missing from code"
     
     ELIF TYPE_B or TYPE_C detected (drift):
       severity = MEDIUM
       decision = ESCALATE
       reason = "Code/spec mismatch (drift detected)"
       suggestion = "Update SPEC.md or fix code"
     
     ELIF compliance_score == 100% AND no undocumented changes:
       severity = PASS
       decision = PASS
       reason = "Spec and code aligned"
     
     ELIF compliance_score >= 95% AND undocumented changes are minor:
       severity = LOW
       decision = PASS_WITH_NOTE
       reason = "Minor drift detected; update spec before next release"

OUTPUT:

  HANDBACK = {
    status: PASS | ESCALATE,
    severity: PASS | LOW | MEDIUM | HIGH,
    compliance_score: 0-100,
    
    spec_analysis: {
      documented_features: [list],
      implemented_features: [list],
      missing_features: [list],
      undocumented_features: [list]
    },
    
    drift_detected: {
      type_a_count: 0,  # Regressions
      type_b_count: 0,  # Undocumented additions
      type_c_count: 0,  # Mismatch
      type_d_count: 0   # Breaking changes
    },
    
    findings: [
      {
        type: "TYPE_B",
        feature: "TokenRefreshRotation",
        issue: "Added to code but not documented in SPEC.md",
        severity: "MEDIUM",
        action: "Update SPEC.md before merge"
      }
    ],
    
    recommendation: "Update SPEC.md with new TokenRefreshRotation feature",
    confidence: 0.92
  }
```

---

## Spec Compliance Checklist

- ✅ All documented features implemented?
- ✅ All code features documented?
- ✅ APIs match documentation?
- ✅ Data models match documentation?
- ✅ Architectural changes documented?
- ✅ Deprecations documented?
- ✅ Migration paths clear?
- ✅ No breaking changes without notice?

---

## Example DELEGATE Block

```yaml
---
handoff_type: DELEGATE
task_id: 2026-06-02-spec-engineer-validate-oauth
timestamp: 2026-06-02T16:00:00Z
role: Spec Engineer
model: claude-sonnet-4-6
effort: medium
scope: >
  Validate {service-name} code against SPEC.md.
  Check: Does implemented code match documented behavior?
  Detect: Undocumented features, spec drift, feature deletions.
context:
  - Service: {service-name}
  - Spec location: docs/SPEC.md
  - Commit: abc123 (OAuth2 refresh token rotation)
  - Files changed: lambda/auth/oauth_rotation.go, lambda/auth/handlers.go
  - What to validate:
    * TokenRefreshRotation feature (is it documented?)
    * OAuth2 flow (does impl match spec?)
    * Error handling (documented in spec?)
    * Rate limiting (documented in spec?)
---
```

---

## Example HANDBACK Block

```yaml
---
handoff_type: HANDBACK
task_id: 2026-06-02-spec-engineer-validate-oauth
timestamp: 2026-06-02T16:45:00Z
status: ESCALATE
severity: MEDIUM
compliance_score: 92

spec_analysis:
  documented_features:
    - OAuth2 authorization code flow
    - Token refresh (90-day rolling window)
    - Credential validation
    - Error handling (invalid_grant, unauthorized)
    - Rate limiting
  
  implemented_features:
    - OAuth2 authorization code flow (matches spec)
    - Token refresh with 90-day window (matches spec)
    - Credential validation (matches spec)
    - Error handling (matches spec)
    - Rate limiting (matches spec)
    - [NEW] TokenRefreshRotation (new, not in spec!)
  
  missing_features: []
  
  undocumented_features:
    - TokenRefreshRotation (automatic refresh on every use)

drift_detected:
  type_a: 0 (no regressions)
  type_b: 1 (undocumented feature added)
  type_c: 0 (no mismatches)
  type_d: 0 (no breaking changes)

findings:
  - type: TYPE_B
    feature: TokenRefreshRotation
    issue: "Automatic refresh token rotation on every use - implemented in oauth_rotation.go but NOT documented in SPEC.md"
    severity: MEDIUM
    action: "Update SPEC.md to document this behavior"
    details: "Reduces refresh token lifetime from 90 days to effective reuse-based window"

recommendation: |
  Spec drift detected: TokenRefreshRotation feature added but not documented.
  
  Before merge:
    1. Update docs/SPEC.md to document TokenRefreshRotation behavior
    2. Specify: When does rotation happen? (every use?)
    3. Specify: What's the impact on token lifetime?
    4. Specify: What happens if rotation fails?
  
  This is good engineering (automatic rotation is secure!), but must be documented.

decision: ESCALATE
reason: "Undocumented feature requires spec update before merge"
confidence: 0.95

---
```

---

## Success Criteria

- ✅ Accurate spec extraction
- ✅ Accurate code analysis
- ✅ Drift detection accurate (TYPE_A, B, C, D classification correct)
- ✅ Compliance scoring fair (reflects actual alignment)
- ✅ Identifies real issues (not false positives)
- ✅ Suggests spec updates clearly
- ✅ Escalates for breaking changes
- ✅ Prevents undocumented changes
- ✅ Maintains spec as source of truth
