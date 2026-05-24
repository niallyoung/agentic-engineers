# Phase 2: Security Hardening Implementation Plan

## Overview
Implement 3 critical security issues + 10 workflow security gaps to harden the agentic-engineers framework.

## Critical Security Issues (1-3)

### 1. PKI Signing for DELEGATE/HANDBACK Payloads
**Goal:** Cryptographically sign all protocol payloads to prevent tampering.

**Implementation:**
- `src/orchestration/security/pki_signer.py` - RSA signature generation/verification
  - Generate RSA keypair on first run
  - Sign DELEGATE/HANDBACK blocks with private key
  - Verify signatures during validation
  - Store public key in .github for CI/CD verification

- Update `quality_validator.py` to check PKI signatures
- Add signature fields to delegate-schema.yaml and handback-schema.yaml

**Tests:**
- `tests/test_security_pki_signing.py`
  - Generate keypair
  - Sign and verify payloads
  - Detect tampering
  - Invalid signature rejection

### 2. Entropy-Based Secret Detection
**Goal:** Detect credentials in code before commit using entropy analysis.

**Implementation:**
- `src/orchestration/security/entropy_detector.py`
  - Calculate Shannon entropy for each string
  - Pattern matching (AWS_SECRET, DATABASE_PASSWORD, etc.)
  - Threshold-based detection (entropy > 3.5 bits/char)
  - Exclude common high-entropy legitimate patterns

- Update git pre-commit hook to run detector
- Add `opencode-scan-secrets` CLI command

**Tests:**
- `tests/test_security_entropy_detection.py`
  - Real credentials (AWS, DB, API keys)
  - False positive handling
  - Pattern detection
  - Exclusion lists

### 3. Agent Identity Verification
**Goal:** Prevent spoofing in DELEGATE/HANDBACK chains.

**Implementation:**
- `src/orchestration/security/agent_identity.py`
  - Generate unique agent identity on startup
  - Sign all messages with agent private key
  - Verify sender identity during routing
  - Maintain identity trust chain

- Add `agent_id` and `agent_signature` to protocol
- Update orchestrator to verify chains

**Tests:**
- `tests/test_security_agent_identity.py`
  - Identity generation
  - Chain verification
  - Spoofing detection
  - Identity revocation

## Workflow Security Gaps (4-13)

### 4. Mandatory Security Gate in Merge Flow
- Create `.github/workflows/security-gate.yml`
- Pre-merge security checks: credentials, vulnerabilities, SPEC.md compliance
- Block merge if security checks fail

### 5. SPEC.md Drift Detection
- `src/orchestration/security/spec_drift_detector.py`
- Compare code changes against SPEC.md requirements
- Flag undocumented changes before merge
- Integration with CI/CD

### 6. Audit Logging for Protocol Transitions
- `src/orchestration/security/audit_logger.py`
- Log all DELEGATE/HANDBACK state transitions
- Immutable audit trail (append-only)
- Query interface for audit reports

### 7. Rate Limiting on Sub-Agent Invocations
- `src/orchestration/security/rate_limiter.py`
- Per-agent rate limits (default: 10/min)
- Per-role rate limits (default: 50/min)
- Configurable thresholds

### 8. Token Budget Enforcement
- `src/orchestration/security/budget_enforcer.py`
- Track token spend per agent per day/week/month
- Enforce hard limits
- Alert at 75%, 90% thresholds

### 9. Post-Merge Canary Health Monitoring
- `.github/workflows/canary-monitor.yml`
- Monitor for deployment health post-merge
- Automated rollback on failure detection
- Health metrics dashboard

### 10. Credentials Scanning in CI/CD
- GitHub Secret Scanning integration
- GHAS (Advanced Security) integration
- Dependency vulnerability scanning

### 11. Protocol Validation Hardening
- Add cryptographic proof-of-work for expensive operations
- Add timestamp validation (prevent replay attacks)
- Add nonce validation (prevent replay attacks)

### 12. Secure Secret Storage
- Integration with GitHub Secrets
- Encryption at rest for local config
- Secret rotation policies

### 13. Compliance Audit Trail
- Automated SPEC.md compliance checks
- Compliance reports generation
- Audit log analysis

## Implementation Order

1. **Phase 1 (Foundations - 4 hours)**
   - Security module structure
   - PKI keypair generation
   - Entropy detector core
   - Agent identity framework

2. **Phase 2 (Protocol Integration - 3 hours)**
   - Update DELEGATE/HANDBACK schemas
   - Quality validator updates
   - Pre-commit hook updates

3. **Phase 3 (Workflow Gates - 3 hours)**
   - Security gate workflow
   - SPEC.md drift detection
   - Audit logging system

4. **Phase 4 (Enforcement - 3 hours)**
   - Rate limiting
   - Budget enforcement
   - Canary monitoring

5. **Phase 5 (Testing - 4 hours)**
   - Comprehensive security tests
   - Integration tests
   - Test coverage ≥90%

## Files to Create/Modify

### New Files
- `src/orchestration/security/__init__.py`
- `src/orchestration/security/pki_signer.py`
- `src/orchestration/security/entropy_detector.py`
- `src/orchestration/security/agent_identity.py`
- `src/orchestration/security/audit_logger.py`
- `src/orchestration/security/rate_limiter.py`
- `src/orchestration/security/budget_enforcer.py`
- `src/orchestration/security/spec_drift_detector.py`
- `tests/test_security_pki_signing.py`
- `tests/test_security_entropy_detection.py`
- `tests/test_security_agent_identity.py`
- `tests/test_security_workflow_gates.py`
- `.github/workflows/security-gate.yml`
- `.github/workflows/canary-monitor.yml`

### Modified Files
- `src/orchestration/agents/quality_validator.py` - Add PKI checks
- `src/orchestration/delegate-schema.yaml` - Add signature field
- `src/orchestration/handback-schema.yaml` - Add signature field
- `.githooks/pre-commit` - Add entropy detection
- `src/orchestration/__init__.py` - Export security modules

## Success Criteria

1. ✅ All 3 critical security issues implemented
2. ✅ All 10 workflow security gaps addressed
3. ✅ 15+ new security tests passing
4. ✅ Test coverage ≥90% for security modules
5. ✅ No existing tests broken (2631 passing → 2631+ passing)
6. ✅ CI/CD workflows updated with security gates
7. ✅ HANDBACK with status: PASS

## Risk Mitigation

- **Breaking changes:** Backward compatibility through schema versioning
- **Performance:** Security checks are minimal overhead (<10ms per DELEGATE)
- **False positives:** Exclusion lists for legitimate high-entropy patterns
- **Integration:** Gradual rollout with feature flags
