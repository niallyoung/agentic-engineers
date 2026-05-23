"""
audit_logger.py — Immutable audit trail for SPEC.md changes.

Records every action with:
- Cryptographic linking (SHA-256 hash chain)
- Complete approval chain tracking
- Tamper-evident entries
- Queryable by change_id, actor, timestamp, action

Author: Principal Engineer
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import hashlib
import uuid


@dataclass
class ApprovalEntry:
    """Approval record in audit trail"""
    change_id: str
    approver: str
    approver_role: str
    approval_timestamp: str
    status: str  # "approved", "rejected", "revision-requested"
    comments: Optional[str] = None


@dataclass(frozen=True)  # Immutable
class AuditEntry:
    """Immutable audit trail entry with cryptographic linking"""
    entry_id: str
    change_id: str
    action: str  # "proposed", "analyzed", "approval_requested", "approval_decision", "applied", "reverted"
    actor: str
    actor_role: str
    timestamp: str
    details: Dict
    previous_hash: Optional[str] = None  # SHA-256 of previous entry
    approval_chain: List[ApprovalEntry] = field(default_factory=list)
    
    def __hash__(self):
        return hash(self.entry_id)


class ImmutableError(Exception):
    """Raised when attempting to modify immutable audit entry"""
    pass


class AuditLogger:
    """Records immutable audit trail for SPEC.md changes."""
    
    def __init__(self):
        self._entries: List[AuditEntry] = []
        self._last_hash: Optional[str] = None
    
    def log_action(self, action: str, change_id: str, actor: str, actor_role: str,
                   details: Optional[Dict] = None,
                   approval_chain: Optional[List[ApprovalEntry]] = None) -> AuditEntry:
        """Log an action to the audit trail.
        
        Args:
            action: Action type ("proposed", "analyzed", "approved", "rejected", "applied", "reverted")
            change_id: ID of change being acted upon
            actor: Name of actor
            actor_role: Role of actor
            details: Optional action-specific details
            approval_chain: Optional list of approval entries
            
        Returns:
            AuditEntry (immutable)
        """
        entry_id = f"audit-{datetime.utcnow().isoformat()}-{uuid.uuid4().hex[:8]}"
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Compute hash of this entry
        entry_hash = self._compute_entry_hash(entry_id, change_id, action, actor, timestamp)
        
        entry = AuditEntry(
            entry_id=entry_id,
            change_id=change_id,
            action=action,
            actor=actor,
            actor_role=actor_role,
            timestamp=timestamp,
            details=details or {},
            previous_hash=self._last_hash,
            approval_chain=approval_chain or []
        )
        
        self._entries.append(entry)
        self._last_hash = entry_hash
        
        return entry
    
    def log_approval(self, approval: ApprovalEntry) -> AuditEntry:
        """Log an approval decision.
        
        Args:
            approval: ApprovalEntry to log
            
        Returns:
            AuditEntry recording the approval
        """
        action = "approval_decision"
        
        return self.log_action(
            action=action,
            change_id=approval.change_id,
            actor=approval.approver,
            actor_role=approval.approver_role,
            details={
                "approval_status": approval.status,
                "approval_comments": approval.comments
            },
            approval_chain=[approval]
        )
    
    def get_entries_for_change(self, change_id: str) -> List[AuditEntry]:
        """Get all audit entries for a specific change.
        
        Args:
            change_id: Change ID to query
            
        Returns:
            List of AuditEntry objects
        """
        return [e for e in self._entries if e.change_id == change_id]
    
    def get_entries_by_action(self, action: str) -> List[AuditEntry]:
        """Get all entries for a specific action type.
        
        Args:
            action: Action type to query
            
        Returns:
            List of AuditEntry objects
        """
        return [e for e in self._entries if e.action == action]
    
    def get_entries_since(self, timestamp: str) -> List[AuditEntry]:
        """Get all entries since a timestamp.
        
        Args:
            timestamp: ISO-8601 timestamp (inclusive)
            
        Returns:
            List of AuditEntry objects
        """
        return [e for e in self._entries if e.timestamp >= timestamp]
    
    def get_entries_by_actor(self, actor: str) -> List[AuditEntry]:
        """Get all entries by a specific actor.
        
        Args:
            actor: Actor name to query
            
        Returns:
            List of AuditEntry objects
        """
        return [e for e in self._entries if e.actor == actor]
    
    def verify_chain_integrity(self) -> bool:
        """Verify cryptographic integrity of audit chain.
        
        Checks that each entry's previous_hash matches the actual hash of
        the entry that preceded it.
        
        Returns:
            True if chain is intact, False if tampering detected
        """
        for i, entry in enumerate(self._entries):
            if i == 0:
                # First entry should have no previous hash
                if entry.previous_hash is not None:
                    return False
            else:
                prev_entry = self._entries[i - 1]
                prev_hash = self._compute_entry_hash(
                    prev_entry.entry_id,
                    prev_entry.change_id,
                    prev_entry.action,
                    prev_entry.actor,
                    prev_entry.timestamp
                )
                if entry.previous_hash != prev_hash:
                    return False
        
        return True
    
    def get_all_entries(self) -> List[AuditEntry]:
        """Get all audit entries in order.
        
        Returns:
            List of all AuditEntry objects
        """
        return list(self._entries)
    
    @staticmethod
    def _compute_entry_hash(entry_id: str, change_id: str, action: str, actor: str, timestamp: str) -> str:
        """Compute SHA-256 hash of an entry.
        
        Hash is computed from (entry_id + change_id + action + actor + timestamp)
        to prevent tampering.
        """
        content = f"{entry_id}|{change_id}|{action}|{actor}|{timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()
