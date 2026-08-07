# Security Infrastructure — Architecture & Status

**Date:** 2026-06-25  
**Phase:** 3.1 (Consolidation)  
**Status:** Audit complete; unused modules moved to experimental

## Overview

The agentic-engineers framework has multiple layers of security infrastructure designed to protect the DELEGATE/HANDBACK protocol lifecycle, credential handling, and resource enforcement.

This document clarifies what is **currently active** vs. **experimental/future**, and provides a roadmap for protocol hardening phases.

---

## Active Security Infrastructure

### 1. EntropyDetector (Pattern-Only Mode)

**Location:** `src/orchestration/security/entropy_detector.py`  
**Status:** ✅ ACTIVE & INTEGRATED  
**Integration Points:**
- Pre-commit hooks for credential detection
- File scanning before commits
- Dictionary value validation

**Capabilities:**
- ✅ Pattern-based credential detection (AWS, GitHub, JWT, API keys, etc.)
- ✅ Field name heuristics with entropy validation (conservative)
- ❌ Pure entropy-only detection (disabled due to false positives)

**Entropy Settings:**
- `MIN_ENTROPY_THRESHOLD = 4.8` bits/character
- Field-name heuristics use 2.5-bit threshold (more conservative)
- Excludes: hashes, UUIDs, URLs, hex colors, import statements

**Example Usage:**
```python
from src.orchestration.security import EntropyDetector

detector = EntropyDetector()

# Pattern-based detection (high confidence)
is_cred, reason = detector.detect_in_value("AKIAIOSFODNN7EXAMPLE")
# → (True, "Matches pattern: aws_access_key")

# Field name + entropy (conservative)
is_cred, reason = detector.detect_in_value(
    "x9kL7mP2qJa5nB3tVc6rD2fG9hJ",
    field_name="api_key"
)
# → (True, "Suspicious field 'api_key' with high entropy")

# Scan file for credentials
findings = detector.scan_file(Path("config.py"))
```

### 2. RateLimiter (Agent-Level)

**Location:** `src/orchestration/security/rate_limiter.py`  
**Status:** ✅ ACTIVE  
**Purpose:** Prevent excessive agent invocations (per-agent, per-role tracking)

**Note:** A separate `RateLimiter` exists in `src/skills/queue-management/scripts/rate_limiter.py`
for per-session rate limiting. This module provides agent-level enforcement.

**Default Limits:**
| Agent | Per-Minute | Per-Hour |
|-------|-----------|----------|
| orchestrator | 100 | 1,000 |
| engineer | 10 | 100 |
| senior_engineer | 15 | 150 |
| lead_engineer | 20 | 200 |
| principal_engineer | 10 | 100 |
| security_engineer | 5 | 50 |
| quality_engineer | 10 | 100 |
| model_engineer | 10 | 100 |

**Example Usage:**
```python
from src.orchestration.security import RateLimiter

limiter = RateLimiter()

# Check if agent can call
is_allowed, reason, retry_after = limiter.check_rate_limit(
    agent_id="eng-001",
    agent_role="engineer"
)

if is_allowed:
    # Record the call
    limiter.record_call("eng-001")
else:
    print(f"Rate limited: {reason}. Retry in {retry_after}s")

# Get stats
stats = limiter.get_stats("eng-001", "engineer")
# → {
#     'calls_in_minute': 5,
#     'limit_per_minute': 10,
#     'headroom_minute': 5,
#     'calls_in_hour': 42,
#     'limit_per_hour': 100,
#     'headroom_hour': 58,
# }
```

### 3. BudgetEnforcer

**Location:** `src/orchestration/security/rate_limiter.py`  
**Status:** ✅ ACTIVE  
**Purpose:** Enforce token budgets across time periods

**Default Budgets (tokens):**
| Agent | Per-Day | Per-Week | Per-Month |
|-------|---------|----------|-----------|
| orchestrator | 500K | 2M | 8M |
| engineer | 100K | 400K | 1.6M |
| senior_engineer | 200K | 800K | 3.2M |
| lead_engineer | 150K | 600K | 2.4M |
| principal_engineer | 250K | 1M | 4M |
| security_engineer | 80K | 320K | 1.28M |
| quality_engineer | 80K | 320K | 1.28M |
| model_engineer | 150K | 600K | 2.4M |

**Example Usage:**
```python
from src.orchestration.security import BudgetEnforcer

enforcer = BudgetEnforcer()

# Check if agent can spend tokens
tokens_needed = 5000
is_allowed, reason, remaining = enforcer.check_budget(
    agent_id="eng-001",
    agent_role="engineer",
    tokens_to_spend=tokens_needed
)

if is_allowed:
    # Record the spending
    enforcer.record_spending("eng-001", tokens_needed)
else:
    print(f"Budget exceeded: {reason}. Remaining: {remaining}")

# Get spending stats
stats = enforcer.get_spending("eng-001", "engineer")
```

### 4. Model Resolution (FALLBACK_DEFAULTS)

**Location:** `src/orchestration/models/canonical_resolver.py`  
**Status:** ✅ ACTIVE & SYNCHRONIZED  
**Guarantee:** FALLBACK_DEFAULTS are **derived from models.yaml**, not hardcoded

**Key Properties:**
- ✅ Single source of truth: `src/config/models.yaml`
- ✅ Derived defaults computed from canonical registry
- ✅ Cached per-file to ensure consistency
- ✅ Test validates synchronization (`tests/test_model_resolver_consistency.py`)

**What This Prevents:**
- Model configuration drift between hardcoded defaults and registry
- Inconsistent model assignments across the codebase
- Stale fallback values after config updates

**Example:**
```python
from src.orchestration.models.canonical_resolver import ModelResolver

resolver = ModelResolver()

# FALLBACK_DEFAULTS are derived from models.yaml 'claude' provider
print(resolver.FALLBACK_DEFAULTS['engineer'])
# → 'claude-haiku-4.5' (from models.yaml: engineer → claude → claude-haiku-4.5)

# Verify consistency
assert resolver.FALLBACK_DEFAULTS['engineer'] == resolver.resolve('engineer')
# Always true: resolve() returns FALLBACK_DEFAULTS when no provider specified
```

---

## Experimental / Deprecated Infrastructure

Moved to `src/internal/experimental/security/` for future protocol hardening phases.

### 1. PKISigner

**Location:** `src/internal/experimental/security/pki_signer.py`  
**Status:** ⏸️ EXPERIMENTAL (not integrated)  
**Purpose:** Cryptographic signing of DELEGATE/HANDBACK payloads

**Current Status:**
- Well-designed RSA 2048-bit signing implementation
- Full coverage of DELEGATE/HANDBACK signing and verification
- Tests passing
- **Not integrated:** No active calls in orchestrator or quality gates

**To Re-Enable:**
```
1. Add PKISigner to Orchestrator.__init__()
2. Call signer.add_signature_to_delegate() when creating DELEGATE
3. Call signer.verify_delegate_signature() in quality gate validation
4. Similar pattern for HANDBACK in result processing
5. Update protocol_audit.py to check for signature fields
```

**Design Benefits:**
- Detects tampering during transit
- Prevents spoofed protocol messages
- Auditable signature trail

### 2. AgentIdentity

**Location:** `src/internal/experimental/security/agent_identity.py`  
**Status:** ⏸️ EXPERIMENTAL (not integrated)  
**Purpose:** Identity verification and spoofing prevention in delegation chains

**Current Status:**
- Per-agent UUID generation and tracking
- Identity chain tracking through delegation hierarchy
- Cryptographic signature verification using agent public keys
- Tests passing
- **Not integrated:** No active usage in DELEGATE/HANDBACK pipeline

**To Re-Enable:**
```
1. Create AgentIdentity for Orchestrator at startup
2. Create AgentIdentity for each sub-agent in Agent tool
3. Call add_identity_to_delegate() when delegating
4. Call verify_delegate_identity() in protocol validation
5. Track identity_chain through the full delegation tree
```

**Design Benefits:**
- Prevents spoofing (agent claiming to be another agent)
- Tracks delegation chains end-to-end
- Detects compromised agents
- Auditable identity verification

### 3. AuditLogger

**Location:** `src/internal/experimental/security/audit_logger.py`  
**Status:** ⏸️ EXPERIMENTAL (superseded by session_manager)  
**Purpose:** Immutable audit trail for protocol transitions

**Current Status:**
- Append-only JSONL logs with tamper detection
- Event types: DELEGATE, HANDBACK, VALIDATION, SECURITY_CHECK, RATE_LIMIT_VIOLATION, BUDGET_VIOLATION, COMPLIANCE_CHECK
- Queryable event history
- Checksum verification
- Daily log rotation
- **Superseded by:** `src/orchestration/memory/session_manager.py`

**Why Superseded:**
- SessionManager provides structured task lifecycle tracking
- Integrates with memory system for full context preservation
- Audit events are already captured in delegates/handbacks directories
- SessionManager is the canonical audit source

**To Migrate:**
```
1. Review missing event types in SessionManager
2. Migrate RATE_LIMIT_VIOLATION and BUDGET_VIOLATION to memory system
3. Integrate with protocol audit checks
4. Consider merging security audit events with task lifecycle events
```

---

## Model Selection Strategy

### Security Engineer: Fable-5 Unconditional Default

The Security Engineer role uses a single model:
- **Unconditional Default:** `claude-fable-5` (highest capability tier for threat modeling)

**Routing Logic:**
```python
resolver = ModelResolver()

# Unconditional fable-5 for all security_engineer delegations
model = resolver.resolve('security_engineer')
# → 'claude-fable-5'
```

**Model Rationale:**
- Fable-5 provides highest reasoning capability for security analysis
- Unconditional routing ensures security tasks receive the best model available
- Offensive-scope gating is enforced by DelegateValidator C5 gate, not by model routing
- See `docs/SPEC.md` > "Security Engineer: Multi-Model Strategy"

**Implementation:**
- `src/config/models.yaml` defines fable-5 as canonical default
- `canonical_resolver.py` routes unconditionally to fable-5
- Tests validate fable-5 as default (`test_model_resolver_consistency.py`)

---

## Synchronization Tests

### Model Resolver Consistency Test

**File:** `tests/test_model_resolver_consistency.py`  
**Purpose:** Validate FALLBACK_DEFAULTS are in sync with models.yaml

**Test Coverage:**
1. ✅ FALLBACK_DEFAULTS match canonical registry for all roles
2. ✅ FALLBACK_DEFAULTS provide fallback for resolve() calls
3. ✅ FALLBACK_DEFAULTS are never empty
4. ✅ All FALLBACK_DEFAULTS values are valid model names
5. ✅ Provider-specific models available for all roles
6. ✅ Fable-5 defensive routing works correctly

**Running Tests:**
```bash
python -m pytest tests/test_model_resolver_consistency.py -v
```

---

## Future Protocol Hardening Roadmap

### Phase 3.2: PKI Integration
- [ ] Wire PKISigner into Orchestrator initialization
- [ ] Add signature generation to DELEGATE creation
- [ ] Add signature verification to quality gates
- [ ] Update protocol audit to validate signatures
- [ ] Migrate tests from src/internal/experimental/

### Phase 3.3: Identity Chain Tracking
- [ ] Initialize AgentIdentity for Orchestrator and sub-agents
- [ ] Add identity fields to DELEGATE/HANDBACK
- [ ] Implement identity verification in protocol validation
- [ ] Track identity chains through delegation trees
- [ ] Add identity checks to quality gates

### Phase 3.4: Unified Audit Trail
- [ ] Migrate AuditLogger events to SessionManager
- [ ] Add RATE_LIMIT_VIOLATION and BUDGET_VIOLATION tracking
- [ ] Integrate security audit events with task lifecycle
- [ ] Create compliance report generation from audit trail
- [ ] Enable audit trail querying and analysis

### Phase 4: Cryptographic Protocol Enforcement
- [ ] All three components integrated end-to-end
- [ ] Full tamper detection and spoofing prevention
- [ ] Audit trail tied to cryptographic proof
- [ ] Compliance reporting with digital signatures

---

## Credential Detection Guidelines

### What Gets Flagged

**High Confidence (Pattern Matching):**
- ✅ AWS access keys: `AKIA[0-9A-Z]{16}`
- ✅ AWS secret keys: `aws_secret_access_key = <40-char base64>`
- ✅ GitHub tokens: `gh[ousp]_[A-Za-z0-9_]{36,255}`
- ✅ Azure keys: Base64-encoded 88-char + `==`
- ✅ Private key headers: `-----BEGIN (RSA|DSA|EC|OPENSSH|PRIVATE) KEY-----`
- ✅ Database passwords: `password|passwd|pwd = <12+ special chars>`
- ✅ API keys: `api[_-]?key = <20+ chars>`
- ✅ OAuth tokens: `(access|bearer) <token>`
- ✅ JWT tokens: `eyJ...eyJ...` format
- ✅ Stripe keys: `(sk|pk)_(test|live)_<24+ chars>`

**Medium Confidence (Field Name + Entropy):**
- ⚠️ Field names: password, secret, token, api_key, private_key, etc.
- ⚠️ High entropy in suspicious fields (entropy > 2.5 bits/char)

### What Gets Excluded

**Legitimate high-entropy patterns (not flagged):**
- ❌ Hashes: `[a-f0-9]{32,}` (MD5, SHA1, SHA256)
- ❌ UUIDs: Standard UUID format
- ❌ URLs: `https://...`
- ❌ Hex colors: `#[0-9a-fA-F]{6}`
- ❌ Shebangs: `#!/usr/bin/env python`
- ❌ Python paths: Paths containing 'python'
- ❌ Import statements: `from X import Y`
- ❌ Base64: Likely base64 strings

### Configuration

**Adjust detection sensitivity:**
```python
# Looser threshold (more false positives, fewer false negatives)
detector = EntropyDetector(entropy_threshold=4.0)

# Stricter threshold (fewer false positives, more false negatives)
detector = EntropyDetector(entropy_threshold=5.5)
```

**Current default:** 4.8 bits/character (balanced for Python code)

---

## Integration Examples

### Pre-Commit Hook Integration

```python
from src.orchestration.security import EntropyDetector
from pathlib import Path

detector = EntropyDetector()

# Scan staged files
for file_path in staged_files:
    findings = detector.scan_file(Path(file_path))
    if findings:
        print(f"⚠️  Credentials detected in {file_path}:")
        for finding in findings:
            print(f"  - Line {finding['line']}: {finding['reason']}")
        raise PreCommitCheckFailed()
```

### Rate Limiting in Orchestrator

```python
from src.orchestration.security import RateLimiter, BudgetEnforcer

limiter = RateLimiter()
budget = BudgetEnforcer()

def delegate_to_agent(role: str, agent_id: str, tokens_needed: int) -> bool:
    # Check rate limit
    is_allowed, reason, retry = limiter.check_rate_limit(agent_id, role)
    if not is_allowed:
        logger.warning(f"Rate limited: {reason}")
        return False

    # Check token budget
    is_allowed, reason, remaining = budget.check_budget(
        agent_id, role, tokens_needed
    )
    if not is_allowed:
        logger.warning(f"Budget exceeded: {reason}")
        return False

    # Record and proceed
    limiter.record_call(agent_id)
    budget.record_spending(agent_id, tokens_needed)
    return True
```

### Future: Full PKI Integration

```python
from src.internal.experimental.security import PKISigner, AgentIdentity
from src.orchestration.security import RateLimiter, BudgetEnforcer, EntropyDetector

class SecureOrchestrator:
    def __init__(self):
        self.pki = PKISigner()
        self.identity = AgentIdentity("orchestrator")
        self.limiter = RateLimiter()
        self.budget = BudgetEnforcer()
        self.detector = EntropyDetector()

    def create_delegate(self, role: str, task_spec: dict) -> dict:
        # Create DELEGATE
        delegate = {
            "task_id": task_spec["id"],
            "agent": role,
            "scope": task_spec["scope"],
        }

        # Add identity
        delegate = self.identity.add_identity_to_delegate(delegate)

        # Add cryptographic signature
        delegate = self.pki.add_signature_to_delegate(delegate)

        return delegate

    def validate_handback(self, handback: dict) -> bool:
        # Verify signature
        is_valid, error = self.pki.verify_handback_signature(handback)
        if not is_valid:
            logger.error(f"Invalid handback signature: {error}")
            return False

        # Verify identity
        is_valid, agent_id, error = self.identity.verify_handback_identity(handback)
        if not is_valid:
            logger.error(f"Invalid agent identity: {error}")
            return False

        # Verify no credentials leaked
        findings = self.detector.scan_dict(handback)
        if findings:
            logger.error(f"Credentials detected in handback: {findings}")
            return False

        return True
```

---

## References

- `docs/SPEC.md`: Framework specification and governance
- `src/config/models.yaml`: Canonical model registry
- `src/orchestration/models/canonical_resolver.py`: Model resolution
- `src/orchestration/security/`: Active security infrastructure
- `src/internal/experimental/security/`: Experimental modules
- `tests/test_model_resolver_consistency.py`: Model sync tests
- `tests/test_security_core.py`: Security module tests

---

**Last Updated:** 2026-06-25  
**Reviewed By:** Phase 3.1 Consolidation Task  
**Next Review:** Before Phase 3.2 (PKI Integration)
