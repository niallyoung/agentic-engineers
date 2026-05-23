"""
spec_manager.py — Main orchestrator for SPEC.md change management.

Coordinates validation, authorization, impact analysis, approval routing,
and application of changes to SPEC.md with full audit trail.

Author: Principal Engineer
Phase: TDD Implementation (GREEN-phase)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime
import re
from pathlib import Path

from .change_validator import ChangeValidator, ValidationResult
from .authorizer import Authorizer
from .impact_analyzer import ImpactAnalyzer
from .audit_logger import AuditLogger
from .changelog_generator import ChangelogGenerator
from .rollback_manager import RollbackManager


@dataclass
class ChangeProposal:
    """Structured change proposal to SPEC.md"""
    change_id: str
    proposer: str
    proposer_role: str
    timestamp: str
    affected_sections: List[str]
    proposed_changes: Dict[str, str]
    rationale: str
    compatibility_notes: Optional[str] = None
    breaking_change: bool = False
    migration_path: Optional[str] = None


@dataclass
class SubmissionResult:
    """Result of proposal submission"""
    status: str  # "pending_approval", "approved", "rejected", "revision_required"
    change_id: str
    reason: Optional[str] = None
    requires_migration_path: bool = False
    next_steps: Optional[str] = None
    approval_chain: List[str] = field(default_factory=list)


class SpecManager:
    """Main orchestrator for SPEC.md change management.
    
    Coordinates:
    - Proposal validation
    - Authorization checks
    - Impact analysis
    - Approval routing
    - Change application
    - Audit trail recording
    - Changelog updates
    - Rollback capability
    """
    
    def __init__(self, spec_path: str = "$REPO_ROOT/docs/SPEC.md"):
        # Resolve $REPO_ROOT in path
        if "$REPO_ROOT" in spec_path:
            import os
            repo_root = os.getenv("REPO_ROOT", "")
            if not repo_root:
                # Fallback: find SPEC.md relative to this script
                # This file is at src/skills/spec-management/scripts/spec_manager.py
                # So we need to go up 5 levels to repo root
                spec_path = str(Path(__file__).parent.parent.parent.parent.parent / "docs" / "SPEC.md")
            else:
                spec_path = spec_path.replace("$REPO_ROOT", repo_root)
        self.spec_path = Path(spec_path)
        self.validator = ChangeValidator()
        self.authorizer = Authorizer()
        self.impact_analyzer = ImpactAnalyzer()
        self.audit_logger = AuditLogger()
        self.changelog_generator = ChangelogGenerator()
        self.rollback_manager = RollbackManager()
        
        # Proposals in-flight
        self._proposals = {}
    
    # ========================================================================
    # PROPOSAL SUBMISSION & VALIDATION
    # ========================================================================
    
    def parse_proposal(self, proposal_dict: Dict) -> ChangeProposal:
        """Parse proposal from dict/JSON/YAML input."""
        return ChangeProposal(
            change_id=proposal_dict.get("change_id", ""),
            proposer=proposal_dict.get("proposer", ""),
            proposer_role=proposal_dict.get("proposer_role", ""),
            timestamp=proposal_dict.get("timestamp", ""),
            affected_sections=proposal_dict.get("affected_sections", []),
            proposed_changes=proposal_dict.get("proposed_changes", {}),
            rationale=proposal_dict.get("rationale", ""),
            compatibility_notes=proposal_dict.get("compatibility_notes"),
            breaking_change=proposal_dict.get("breaking_change", False),
            migration_path=proposal_dict.get("migration_path")
        )
    
    def validate_proposal(self, proposal: ChangeProposal) -> ValidationResult:
        """Validate proposal format and completeness.
        
        Checks:
        - change_id format (SPEC-YYYY-NNN)
        - All required fields present
        - Timestamp is valid ISO-8601
        - Affected sections non-empty
        - Rationale ≥ 50 characters
        - Breaking change has migration path
        
        Args:
            proposal: ChangeProposal to validate
            
        Returns:
            ValidationResult with is_valid flag and list of errors
        """
        return self.validator.validate(proposal)
    
    def submit_proposal(self, proposal: ChangeProposal) -> SubmissionResult:
        """Submit a change proposal for processing.
        
        Flow:
        1. Validate proposal format
        2. Check authorization
        3. Perform impact analysis
        4. Route for approval
        5. Record in audit trail
        
        Args:
            proposal: ChangeProposal to submit
            
        Returns:
            SubmissionResult with status and next steps
        """
        # Step 1: Validate proposal format
        validation = self.validate_proposal(proposal)
        if not validation.is_valid:
            self.audit_logger.log_action(
                action="rejected",
                change_id=proposal.change_id,
                actor=proposal.proposer,
                actor_role=proposal.proposer_role,
                details={"reason": "validation_failed", "errors": validation.errors}
            )
            return SubmissionResult(
                status="rejected",
                change_id=proposal.change_id,
                reason=f"Validation failed: {'; '.join(validation.errors[:2])}"
            )
        
        # Step 2: Check authorization
        if not self.authorizer.can_propose(proposal.proposer_role):
            self.audit_logger.log_action(
                action="rejected",
                change_id=proposal.change_id,
                actor=proposal.proposer,
                actor_role=proposal.proposer_role,
                details={"reason": "unauthorized_role"}
            )
            return SubmissionResult(
                status="rejected",
                change_id=proposal.change_id,
                reason=f"Unauthorized role: {proposal.proposer_role}. Only principal-engineer, security-engineer, and lead-engineer can propose changes."
            )
        
        # Step 3: Validate breaking change requirements
        if proposal.breaking_change and not proposal.migration_path:
            self.audit_logger.log_action(
                action="rejected",
                change_id=proposal.change_id,
                actor=proposal.proposer,
                actor_role=proposal.proposer_role,
                details={"reason": "breaking_change_without_migration_path"}
            )
            return SubmissionResult(
                status="rejected",
                change_id=proposal.change_id,
                reason="Breaking changes must include migration_path pointing to migration guide",
                requires_migration_path=True
            )
        
        # Step 4: Perform impact analysis
        analysis = self.impact_analyzer.analyze(proposal)
        self.audit_logger.log_action(
            action="analyzed",
            change_id=proposal.change_id,
            actor="system",
            actor_role="spec-manager",
            details={"impact_analysis": analysis.__dict__}
        )
        
        # Step 5: Route for approval
        approval_chain = self.authorizer.get_approval_chain(proposal.proposer_role)
        
        # Log proposal submission
        self.audit_logger.log_action(
            action="proposed",
            change_id=proposal.change_id,
            actor=proposal.proposer,
            actor_role=proposal.proposer_role,
            details={"proposal": proposal.__dict__, "approval_chain": approval_chain}
        )
        
        # Store proposal
        self._proposals[proposal.change_id] = proposal
        
        return SubmissionResult(
            status="pending_approval",
            change_id=proposal.change_id,
            reason=None,
            next_steps=f"Awaiting approval from: {', '.join(approval_chain)}",
            approval_chain=approval_chain
        )
    
    # ========================================================================
    # APPROVAL WORKFLOW
    # ========================================================================
    
    def approve_change(self, change_id: str, approver: str, approver_role: str, 
                      comments: Optional[str] = None) -> SubmissionResult:
        """Approve a change proposal.
        
        Args:
            change_id: ID of change to approve
            approver: Name of approver
            approver_role: Role of approver
            comments: Optional approval comments
            
        Returns:
            SubmissionResult with approval status
        """
        # Verify approver authorization
        if not self.authorizer.can_approve(approver_role):
            self.audit_logger.log_action(
                action="approval_denied",
                change_id=change_id,
                actor=approver,
                actor_role=approver_role,
                details={"reason": "approver_not_authorized"}
            )
            return SubmissionResult(
                status="rejected",
                change_id=change_id,
                reason=f"Approver role not authorized: {approver_role}"
            )
        
        # Log approval
        from .audit_logger import ApprovalEntry
        approval = ApprovalEntry(
            change_id=change_id,
            approver=approver,
            approver_role=approver_role,
            approval_timestamp=datetime.utcnow().isoformat() + "Z",
            status="approved",
            comments=comments
        )
        
        self.audit_logger.log_approval(approval)
        
        # Check if this is final approval
        approval_entries = self.audit_logger.get_entries_for_change(change_id)
        final_approval = approver_role == "principal-engineer"
        
        if final_approval:
            # Apply change immediately
            return self._apply_change(change_id)
        
        return SubmissionResult(
            status="pending_approval",
            change_id=change_id,
            reason=f"Approved by {approver}; awaiting final approval"
        )
    
    def reject_change(self, change_id: str, rejector: str, rejector_role: str,
                     comments: str) -> SubmissionResult:
        """Reject a change proposal.
        
        Args:
            change_id: ID of change to reject
            rejector: Name of person rejecting
            rejector_role: Role of rejector
            comments: Required reason for rejection
            
        Returns:
            SubmissionResult with rejection status
        """
        from .audit_logger import ApprovalEntry
        rejection = ApprovalEntry(
            change_id=change_id,
            approver=rejector,
            approver_role=rejector_role,
            approval_timestamp=datetime.utcnow().isoformat() + "Z",
            status="rejected",
            comments=comments
        )
        
        self.audit_logger.log_approval(rejection)
        
        return SubmissionResult(
            status="rejected",
            change_id=change_id,
            reason=f"Rejected by {rejector}: {comments}"
        )
    
    # ========================================================================
    # CHANGE APPLICATION
    # ========================================================================
    
    def _apply_change(self, change_id: str) -> SubmissionResult:
        """Apply approved change to SPEC.md.
        
        Args:
            change_id: ID of change to apply
            
        Returns:
            SubmissionResult with application status
        """
        if change_id not in self._proposals:
            return SubmissionResult(
                status="rejected",
                change_id=change_id,
                reason="Change not found in proposals"
            )
        
        proposal = self._proposals[change_id]
        
        try:
            # Compute hash of current SPEC.md
            previous_hash = self.compute_spec_hash()
            
            # Read current SPEC.md
            spec_content = self.spec_path.read_text()
            
            # Apply changes
            for section, new_text in proposal.proposed_changes.items():
                # Simple replacement (in production, would be more sophisticated)
                spec_content = spec_content.replace(
                    f"## {section}",
                    f"## {section}\n{new_text}"
                )
            
            # Write updated SPEC.md
            self.spec_path.write_text(spec_content)
            
            # Compute hash of new SPEC.md
            new_hash = self.compute_spec_hash()
            
            # Generate changelog entry
            self.changelog_generator.add_entry(
                change_id=proposal.change_id,
                title=proposal.rationale,
                author=proposal.proposer,
                timestamp=proposal.timestamp
            )
            
            # Record in audit trail with hashes
            self.audit_logger.log_action(
                action="applied",
                change_id=proposal.change_id,
                actor="system",
                actor_role="spec-manager",
                details={
                    "previous_hash": previous_hash,
                    "new_hash": new_hash,
                    "sections_changed": list(proposal.proposed_changes.keys())
                }
            )
            
            # Create version entry
            self.rollback_manager.create_version(
                change_id=proposal.change_id,
                previous_hash=previous_hash,
                new_hash=new_hash,
                changes=proposal.proposed_changes
            )
            
            return SubmissionResult(
                status="approved",
                change_id=proposal.change_id,
                reason=None,
                next_steps=f"Change {proposal.change_id} applied to SPEC.md and CHANGELOG updated"
            )
            
        except Exception as e:
            self.audit_logger.log_action(
                action="failed",
                change_id=proposal.change_id,
                actor="system",
                actor_role="spec-manager",
                details={"error": str(e)}
            )
            return SubmissionResult(
                status="rejected",
                change_id=proposal.change_id,
                reason=f"Failed to apply change: {str(e)}"
            )
    
    # ========================================================================
    # VERSION TRACKING & ROLLBACK
    # ========================================================================
    
    def compute_spec_hash(self) -> str:
        """Compute SHA-256 hash of current SPEC.md."""
        if not self.spec_path.exists():
            return ""
        
        import hashlib
        content = self.spec_path.read_text()
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get_change_history(self) -> List:
        """Get complete change history."""
        return self.rollback_manager.get_history()
    
    def rollback(self, steps: int = 1, initiated_by: str = "system") -> Dict:
        """Rollback one or more changes.
        
        Args:
            steps: Number of changes to revert
            initiated_by: User initiating rollback
            
        Returns:
            Dict with success status and details
        """
        result = self.rollback_manager.rollback(steps)
        
        if result.get("success"):
            # Log rollback
            self.audit_logger.log_action(
                action="reverted",
                change_id=result.get("last_reverted_change_id", "unknown"),
                actor=initiated_by,
                actor_role="principal-engineer",
                details=result
            )
        
        return result
    
    def rollback_to_version(self, version_id: str, initiated_by: str = "system") -> Dict:
        """Rollback to specific version.
        
        Args:
            version_id: Version to rollback to (e.g., "SPEC-v5.9.2")
            initiated_by: User initiating rollback
            
        Returns:
            Dict with success status and details
        """
        result = self.rollback_manager.rollback_to_version(version_id)
        
        if result.get("success"):
            self.audit_logger.log_action(
                action="reverted",
                change_id=version_id,
                actor=initiated_by,
                actor_role="principal-engineer",
                details=result
            )
        
        return result
