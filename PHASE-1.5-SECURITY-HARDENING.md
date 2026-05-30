# Phase 1.5: Express Security Hardening Implementation Plan

**Status:** Ready for Implementation  
**Duration:** ~45 minutes  
**Branch:** `feature/spec-audit-phase1-5-security-hardening` (from `origin/main`)  
**Success Criteria:** All 35+ tests passing, 5 critical fixes implemented and integrated

---

## Executive Summary

Before Phase 1 (spec audit) can safely proceed, 5 critical security issues identified in the Phase 1 security assessment must be addressed with runtime safeguards and protocol extensions.

### The 5 Critical Fixes

| # | Issue | Severity | Fix Approach | Location |
|---|-------|----------|--------------|----------|
| 1 | Queue path ambiguity enables injection/poisoning | 🔴 CRITICAL | Enforce canonical path in runtime + git hook | `src/skills/_meta/queue-path-validator/`, `.githooks/pre-push` |
| 2 | Removing version stamps breaks audit trail | 🟡 HIGH | Keep stamps, add `spec_version` to DELEGATE/HANDBACK/SPAN | `src/orchestration/` schemas, `SPEC.md` |
| 3 | Agent definition drift enables model downgrade attacks | 🔴 CRITICAL | Tri-level verification: git hook + DELEGATE field + runtime | `src/orchestration/`, `.agents_verification_sha` |
| 4 | Missing security-critical fields underfunds security tasks | 🔴 CRITICAL | Add `security_scope`, `approval_gate`, `audit_required` to DELEGATE | `src/orchestration/delegate-schema.yaml` |
| 5 | Weak orchestrator enforcement enables bypass attacks | 🔴 CRITICAL | Implement `@enforce_delegate_requirement` decorator | `src/orchestration/decorators.py` |

---

## FIX #1: Queue Path Enforcement (Runtime + Git Hook)

### Problem
SPEC.md contains contradictory queue paths:
- Line 21: `artifacts/queue/`
- Lines 37, 72: `~/.copilot/queue/{session-id}/incoming/`
- Lines 504-546: `~/.agentic-engineers/{session-id}/{harness}/queue/` (canonical)

**Security Impact:** Enables queue injection/poisoning if paths not enforced

### Implementation

**1.1 Create Queue Path Validator Skill**
- Location: `src/skills/_meta/queue-path-validator/`
- Validate queue paths at runtime in Orchestrator
- Enforce canonical path: `~/.agentic-engineers/{session-id}/{harness}/queue/`
- Reject non-standard paths in DELEGATE/HANDBACK
- Error: "Queue path must follow canonical format: ~/.agentic-engineers/{session-id}/{harness}/queue/"

**1.2 Update Orchestrator Runtime Checks**
- Add path validation to DELEGATE processing
- Fail loudly if path deviates from canonical format
- Log rejected paths to audit trail

**1.3 Git Hook Enforcement (.githooks/pre-push)**
- Fail if SPEC.md contains: `artifacts/queue/` or `~/.copilot/queue/`
- Fail if any DELEGATE/HANDBACK uses non-canonical path
- Error message with fix instructions

### Testing (5 test cases)
- ✅ Canonical path accepted in DELEGATE
- ✅ Legacy path `artifacts/queue/` rejected
- ✅ Legacy path `~/.copilot/queue/` rejected
- ✅ Path injection attempts blocked (e.g., `~/.agentic-engineers/../../../tmp/queue/`)
- ✅ Git hook blocks non-canonical paths in commits

---

## FIX #2: Audit Trail via spec_version Field (DELEGATE/HANDBACK/SPAN)

### Problem
Removing version stamps from SPEC.md breaks security audit trail linking tasks to spec versions.

**Critical Use Case:** "Which SPEC version authorized this model selection? Did spec drift occur?"

### Implementation

**2.1 Update DELEGATE Schema**
```yaml
spec_version:
  type: string
  pattern: "^\\d+\\.\\d+(-.+)?$"
  description: "SPEC.md version that authorized this DELEGATE (required)"
  examples:
    - "1.0"
    - "1.1-2026-05-28"
  required: true
```

**2.2 Update HANDBACK Schema**
```yaml
spec_version:
  type: string
  description: "Inherited from DELEGATE spec_version (must match)"
  required: true
```

**2.3 Update SPAN Records**
- Add `spec_version: string` field to SPAN records
- Capture at task invocation time
- Enable audit queries: "Which tasks executed under spec v1.0?"

**2.4 Update SPEC.md**
- **KEEP** `version: "1.0"`
- **KEEP** `last_updated: "2026-05-28"`
- Add note: "DELEGATE/HANDBACK/SPAN records include spec_version for audit trail linkage"

### Testing (5 test cases)
- ✅ DELEGATE requires spec_version field
- ✅ HANDBACK spec_version must match DELEGATE
- ✅ Mismatched spec_versions detected and rejected
- ✅ Audit queries work: list tasks by spec version
- ✅ Spec version format validation (pattern: `\d+\.\d+(-.+)?`)

---

## FIX #3: Agent Definition Verification (Tri-Level: Git + Field + Runtime)

### Problem
No mechanism verifies SPEC.md agent definitions match implementation.

**Attack Scenario:** SPEC says Security Engineer uses `claude-opus-4.7`, but implementation silently uses `claude-sonnet-4.6` → security tasks are underfunded without awareness.

### Implementation

**3.1 Generate Agent Verification SHA**
- Calculate SHA256 of `src/orchestration/agents-manifest.yaml` (or agents config)
- Store in repository as `.agents_verification_sha` file
- Update whenever agent definitions change
- File format: `agent_sha256={sha}\ngenerated_at={timestamp}\n`

**3.2 Add model_verification_sha to DELEGATE Schema**
```yaml
model_verification_sha:
  type: string
  pattern: "^[a-f0-9]{64}$"
  description: "SHA256 of AGENTS.md that authorized this model (required)"
  required: true
```

**3.3 Git Hook Enforcement**
- Pre-push hook validates model_verification_sha in DELEGATE/HANDBACK
- Must match current `.agents_verification_sha`
- Error: "Agent definition mismatch detected — model specs may have changed"
- Allows override with documented justification

**3.4 Runtime Check in Orchestrator**
- Before invoking agent, verify model exists in current AGENTS.md
- Add `model_mismatch` flag to SPAN if model not found
- Log warning: "Model [name] not found in AGENTS.md v[sha]"
- Fail task if mismatch detected

### Testing (5 test cases)
- ✅ Verification SHA generated correctly
- ✅ Verification SHA matches for unmodified AGENTS.md
- ✅ SHA changes when AGENTS.md modified
- ✅ DELEGATE with matching SHA accepted
- ✅ DELEGATE with mismatched SHA rejected (model downgrade blocked)

---

## FIX #4: Security-Critical DELEGATE Fields

### Problem
No way to flag security tasks → security work gets routed to general engineers and underfunded.

### Implementation

**4.1 Add to DELEGATE Schema**
```yaml
security_scope:
  type: string
  enum: [none, auth, crypto, pii, secrets, injection, supply_chain]
  default: none
  description: "Security category (none = not a security task)"

approval_gate:
  type: string
  enum: [none, lead_engineer, principal_engineer, security_engineer, cto]
  default: none
  description: "Required approval level before task can execute"

audit_required:
  type: boolean
  default: false
  description: "Whether task must be included in security audit"
```

**4.2 Routing Rules in Orchestrator**
- If `security_scope != none` → route to Security Engineer (minimum)
- If `approval_gate == security_engineer` → route to Security Engineer
- If `approval_gate == principal_engineer` → route to Principal Engineer
- If `approval_gate == cto` → escalate with CTO notification
- Otherwise use normal role routing

**4.3 Validation in Pre-Push Hook**
- If DELEGATE has `security_scope`, must have `approval_gate` set (not "none")
- If `approval_gate` set, must have `audit_required=true`
- Error: "Security DELEGATE requires approval_gate and audit_required=true"

### Testing (10 test cases)
- ✅ Non-security tasks: security_scope=none, approval_gate=none
- ✅ Auth tasks: routed to Security Engineer
- ✅ Crypto tasks: routed to Security Engineer
- ✅ PII tasks: routed to Security Engineer
- ✅ Secret-related: approval_gate=principal_engineer required
- ✅ Injection vulnerabilities: approval_gate=security_engineer required
- ✅ Supply chain: approval_gate=cto triggers escalation
- ✅ Validation: missing approval_gate rejected for security tasks
- ✅ Validation: missing audit_required=true rejected when approval_gate set
- ✅ Routing verified: security tasks don't go to engineer role

---

## FIX #5: Orchestrator Enforcement Decorator (@enforce_delegate_requirement)

### Problem
Weak orchestrator enforcement enables bypass attacks; DELEGATEs can be routed without validation.

### Implementation

**5.1 Create Decorator: @enforce_delegate_requirement**
- Location: `src/orchestration/decorators.py`
- Applied to all Orchestrator.invoke() and Orchestrator.delegate() methods
- Runs all checks before executing task:
  - ✅ DELEGATE is valid (passes schema validation)
  - ✅ All required fields present
  - ✅ Queue path is canonical
  - ✅ spec_version matches current SPEC.md version
  - ✅ model_verification_sha matches current AGENTS.md
  - ✅ security_scope routing is respected
  - ✅ approval gates are honored

**5.2 Implementation Pattern**
```python
@enforce_delegate_requirement(strict=True)
def invoke_agent(delegate: DELEGATE) -> HANDBACK:
    # All checks passed; safe to invoke
    return self.agent.invoke(delegate)
```

**5.3 Validation Error Handling**
- Log violations to audit trail with full context
- Raise explicit `EnforcementError` with fix suggestions
- Never silently skip checks
- Include: violated check, actual value, expected value, remediation steps

**5.4 Strict Mode**
- `strict=True` (default): Fail immediately on any validation failure
- `strict=False` (testing only): Log failures but continue

### Testing (8 test cases)
- ✅ Valid DELEGATE passes all checks
- ✅ Missing required field rejected
- ✅ Invalid queue path rejected
- ✅ Mismatched spec_version rejected
- ✅ Mismatched model_verification_sha rejected
- ✅ Invalid security_scope rejected
- ✅ Error messages include remediation guidance
- ✅ Audit trail logs all validation failures

---

## Test Strategy

### Unit Tests (33 tests)
- **FIX #1:** 5 tests (queue path validation)
- **FIX #2:** 5 tests (spec_version field and audit trail)
- **FIX #3:** 5 tests (agent verification SHA)
- **FIX #4:** 10 tests (security fields and routing)
- **FIX #5:** 8 tests (decorator enforcement)

### Integration Tests (5+ tests)
- All 5 fixes together: verify no conflicts
- End-to-end security task flow
- Audit trail completeness
- Error recovery and logging

### Test Framework
- **Framework:** pytest with fixtures
- **File:** `tests/test_security_hardening.py`
- **Coverage:** 95%+ on new code
- **Execution:** All tests passing before PR creation

### Test Fixtures
```python
@pytest.fixture
def valid_delegate(): # Returns canonical DELEGATE with all required fields
@pytest.fixture
def valid_handback(): # Returns HANDBACK matching DELEGATE
@pytest.fixture
def valid_span(): # Returns SPAN with spec_version
@pytest.fixture
def security_delegate(): # DELEGATE with security_scope set
@pytest.fixture
def current_spec_version(): # Current SPEC.md version
@pytest.fixture
def current_agents_sha(): # Current AGENTS.md verification SHA
```

---

## Quality Gates (STRINGENT)

All of these MUST PASS before PR creation:

- ✅ **35+ tests passing** (5-10 per fix)
- ✅ **0 regressions** in existing tests (full suite passes)
- ✅ **Queue path enforcement** works end-to-end
- ✅ **Audit trail queryable** by spec_version
- ✅ **Agent verification** detects model mismatches
- ✅ **Security metadata routing** verified
- ✅ **Orchestrator decorator** blocks invalid DELEGATEs
- ✅ **All CI checks passing**
- ✅ **Code coverage** >95% on new code
- ✅ **PR ready** for Security Engineer sign-off

---

## Files to Create/Modify

### New Files
- `src/orchestration/decorators.py` - Enforcement decorator
- `tests/test_security_hardening.py` - Comprehensive test suite
- `.agents_verification_sha` - Agent verification SHA (generated)
- `PHASE-1.5-SECURITY-HARDENING.md` - This plan (documentation)

### Modified Files
- `src/orchestration/delegate-schema.yaml` - Add 4 new fields
- `src/orchestration/handback-schema.yaml` - Add spec_version field
- `src/orchestration/metrics/__init__.py` - Update SPAN schema
- `SPEC.md` - Keep version, add spec_version documentation
- `.githooks/pre-push` - Add new validation checks
- (Create skill files as needed for FIX #1)

---

## Success Criteria

By completion:
1. ✅ 5 critical security issues have runtime safeguards
2. ✅ No regressions in existing functionality
3. ✅ Audit trail is intact and queryable
4. ✅ Attack scenarios from assessment are blocked
5. ✅ Phase 1 (spec audit) can now safely proceed
6. ✅ Code is production-ready (no TODOs or FIXMEs in new code)
7. ✅ All 35+ tests passing
8. ✅ PR ready for Security Engineer sign-off

---

## Execution Checklist

- [ ] Create branch: `git checkout -b feature/spec-audit-phase1-5-security-hardening origin/main`
- [ ] FIX #1: Queue path validator (15 min)
- [ ] FIX #2: spec_version fields (15 min)
- [ ] FIX #3: Agent verification (15 min)
- [ ] FIX #4: Security fields (10 min)
- [ ] FIX #5: Enforcement decorator (15 min)
- [ ] Write all tests (20 min)
- [ ] Run full test suite (5 min)
- [ ] Fix any failures (10 min)
- [ ] Generate `.agents_verification_sha` (2 min)
- [ ] Update SPEC.md documentation (5 min)
- [ ] Create PR with detailed description (5 min)

**Total Expected Time:** ~45-50 minutes

