---
name: Spec-Driven Quality Gate Integration
description: Add Spec Engineer as 5th Quality Gate sub-agent - validate code against specification
type: integration-guide
phase: 6
status: SPEC_COMPLETE
---

# Spec-Driven Quality Gate: Integration Guide

**Goal**: Add specification validation to Quality Gate. Detect spec drift, undocumented changes, and unintended feature deletions.

---

## Architecture: Updated Quality Gate with Spec Engineer

```
Quality Gate Orchestrator (Sonnet)
  │
  ├─ DELEGATE Security Agent (Opus)
  │  └─ HANDBACK: credentials, permissions, vulns
  │
  ├─ DELEGATE Testing Agent (Haiku)
  │  └─ HANDBACK: test counts, coverage, failures
  │
  ├─ DELEGATE Metrics Agent (Haiku)
  │  └─ HANDBACK: health score, latency, anomalies
  │
  ├─ DELEGATE Healing Agent (Sonnet)
  │  └─ HANDBACK: fixes applied, escalations
  │
  ├─ DELEGATE Spec Engineer (Sonnet) [NEW]
  │  └─ HANDBACK: spec compliance score, drift detected
  │
  └─ Aggregate results → final decision (PROCEED/ESCALATE)
```

---

## Spec Engineer Sub-Agent

**Role**: Validates code against specification  
**Model**: claude-sonnet-4-6 (complex analysis)  
**Effort**: medium  
**Invoked**: On every commit (part of Quality Gate)  
**Timeout**: 2 minutes per commit

---

## Workflow: Spec-Driven Quality Gate

### On Every Commit:

```
1. Developer commits code
         ↓
2. Pre-commit hook runs:
   - Write DELEGATE to artifacts/
   - Call make quality-gate
         ↓
3. Quality Gate Orchestrator delegates:
   - Security Agent (scan credentials)
   - Testing Agent (run tests)
   - Metrics Agent (check health)
   - Healing Agent (auto-fix issues)
   - [NEW] Spec Engineer (validate against spec)
         ↓
4. Spec Engineer validates:
   - Read docs/SPEC.md
   - Read current code
   - Read git diff (what changed?)
   - Compare: spec vs code vs diff
   - Detect drift (TYPE_A, B, C, D)
   - Calculate compliance_score
         ↓
5. Decision:
   - compliance_score == 100% AND no drift?
     → PASS (allow commit)
   - Drift detected (TYPE_B, C)?
     → ESCALATE with drift details
   - Breaking change (TYPE_D)?
     → ESCALATE, require manual review
         ↓
6. Orchestrator aggregates:
   - ALL 5 sub-agents must PASS for PROCEED
   - ANY escalation → final ESCALATE
         ↓
7. Git hook reads final_decision:
   - PROCEED → allow commit
   - ESCALATE → reject, show reason
```

---

## Spec Engineer Drift Detection

### TYPE_A: Regression (Documented Feature Missing)
```
SPEC says: "CreateUser endpoint exists"
Code has: No CreateUser function
Drift: REGRESSION (feature was deleted)
Action: ESCALATE - "CreateUser endpoint removed!"
```

### TYPE_B: Undocumented Change (Code Feature Not in Spec)
```
SPEC has: OAuth2 flow documented
Code has: TokenRefreshRotation feature (NEW)
Drift: UNDOCUMENTED (feature added without docs)
Action: ESCALATE - "Update SPEC.md with TokenRefreshRotation"
```

### TYPE_C: Mismatch (Spec and Code Disagree)
```
SPEC says: "Refresh token lasts 90 days"
Code has: Refresh token lasts 30 days
Drift: MISMATCH (spec outdated or code wrong)
Action: ESCALATE - "Spec/code mismatch: refresh token lifetime"
```

### TYPE_D: Breaking Change (Feature Deleted Without Notice)
```
SPEC says: "DeleteUser endpoint for compliance"
Code has: DeleteUser removed
No deprecation notice in SPEC
Drift: BREAKING CHANGE
Action: ESCALATE - "Breaking change detected: DeleteUser removed"
```

---

## Integration with Healing Agent

Healing Agent can auto-fix some spec drift:

```
Spec Engineer detects TYPE_B (undocumented feature):
  - Suggestion: Run spec-extract to regenerate SPEC.md
         ↓
Healing Agent receives:
  - High-confidence fix: "Run spec-extract to update SPEC.md"
         ↓
Healing Agent executes:
  - Runs spec-extract skill
  - Commits updated docs/SPEC.md
  - Spec Engineer re-validates
  - Should now PASS
```

---

## Spec Engineer HANDBACK

```yaml
---
handoff_type: HANDBACK
task_id: 2026-06-02-commit-{example-service}-abc123
timestamp: 2026-06-02T09:05:00Z
status: PASS | ESCALATE

spec_validation:
  compliance_score: 95  # (0-100)
  spec_location: docs/SPEC.md
  
  documented_features: 5  # From SPEC
  implemented_features: 6  # From code
  
  drift_detected:
    type_a: 0  # Regressions
    type_b: 1  # Undocumented additions
    type_c: 0  # Mismatches
    type_d: 0  # Breaking changes
  
  issues:
    - type: TYPE_B
      feature: TokenRefreshRotation
      message: "Feature added to code but not documented in SPEC.md"
      severity: MEDIUM
      action: "Update SPEC.md before merge"
  
  recommendation: "Update SPEC.md with TokenRefreshRotation feature"
  decision: ESCALATE (if drift detected) or PASS (if aligned)
  confidence: 0.92
---
```

---

## Full Quality Gate Aggregation (Updated)

**All 5 sub-agents must contribute**:

```
IF Security Agent severity >= HIGH:
  → ESCALATE

ELIF Testing fails (coverage < 80% or tests fail):
  → ESCALATE

ELIF Metrics health_score < 70:
  → ESCALATE

ELIF Healing escalations > 0 (low-confidence fixes):
  → ESCALATE

ELIF Spec Engineer detects drift (TYPE_A, B, C, D):
  → ESCALATE

ELSE (ALL PASS):
  → PROCEED

Final decision: PROCEED or ESCALATE
```

---

## Prevents

✅ **Feature Deletion Without Notice**
- Code deletes CreateUser endpoint
- SPEC still documents it
- Spec Engineer detects TYPE_A regression
- Escalates: "CreateUser missing from code"

✅ **Undocumented Features**
- Code adds TokenRefreshRotation
- SPEC doesn't mention it
- Spec Engineer detects TYPE_B drift
- Escalates: "Update SPEC.md"

✅ **Architectural Drift**
- SPEC says "Data cached in Redis"
- Code changes to "Data cached in DynamoDB"
- Spec Engineer detects TYPE_C mismatch
- Escalates: "Spec/code mismatch"

✅ **Unintended API Changes**
- SPEC documents error handling
- Code removes error case
- Spec Engineer detects TYPE_C mismatch
- Escalates: "API behavior changed"

---

## Setup: Add Spec Engineer to Quality Gate

**File**: `orchestration/quality-gate-orchestrator-agent.md`

Update sub-agent delegation section:

```yaml
DELEGATE to Spec Engineer (Sonnet)
  Input:
    - repo_path: service repository
    - spec_location: docs/SPEC.md
    - commit_sha: git commit hash
  Output: HANDBACK with compliance_score, drift_detected
  Timeout: 2 minutes
```

Update aggregation logic:

```
IF spec_engineer_handback.status == ESCALATE:
  final_decision = ESCALATE
  reason = spec_engineer_handback.recommendation
```

---

## Prerequisites

Each service must have:
- ✅ `docs/SPEC.md` (service specification)
- ✅ Code with docstrings/comments (for extraction)
- ✅ Spec Engineer agent implemented
- ✅ Spec-Extract skill available

---

## Benefits

1. **Prevents Spec Drift**: Spec always reflects code
2. **Prevents Accidental Deletions**: Breaking changes caught
3. **Documents New Features**: Forces spec updates for new work
4. **Source of Truth**: SPEC.md becomes authoritative
5. **Onboarding**: New engineers read SPEC.md to understand service

---

## Timeline

- **Phase 6**: Spec Engineer agent + skill implemented
- **Phase 6**: Integrated into Quality Gate (5th sub-agent)
- **Phase 6**: Testing (10+ commits through spec validation)
- **Phase 7**: Automated spec-extract in Healing Agent (auto-update SPEC.md)

---

## Success Criteria

- ✅ Spec Engineer detects drift accurately (TYPE_A, B, C, D)
- ✅ Compliance scoring fair and useful (0-100 meaningful)
- ✅ Escalates breaking changes 100% of the time
- ✅ Allows undocumented small features (with note) vs. rejecting breaking changes
- ✅ 10+ commits through pipeline with 0% false positives
- ✅ SPEC.md stays current with code
- ✅ No regressions (features aren't accidentally deleted)
