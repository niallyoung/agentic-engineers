"""
EXPERIMENTAL / DEPRECATED Security Infrastructure

This module contains security infrastructure that was designed for DELEGATE/HANDBACK
protocol hardening but is not currently wired into the active queue lifecycle.

Deprecated modules:
- PKISigner: Cryptographic signing for protocol payloads (not integrated)
- AgentIdentity: Agent identity verification and spoofing prevention (not integrated)
- AuditLogger: Immutable audit trail for protocol transitions (superseded by session_manager)

Status:
- Pattern-only EntropyDetector is active in src/orchestration/security/
- RateLimiter and BudgetEnforcer remain active and integrated
- These modules are preserved for future protocol hardening rounds

To re-integrate:
1. Wire PKISigner into orchestrator_protocol_integration.py
2. Add AgentIdentity verification to DELEGATE/HANDBACK validation
3. Migrate AuditLogger events to the session memory system

See: docs/architecture-security-infrastructure.md
"""

from .pki_signer import PKISigner
from .agent_identity import AgentIdentity
from .audit_logger import AuditLogger

__all__ = [
    "PKISigner",
    "AgentIdentity",
    "AuditLogger",
]
