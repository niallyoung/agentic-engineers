"""
authorizer.py — Role-based access control for SPEC.md changes.

Enforces:
- Only Principal/Security/Lead Engineers can propose changes
- Approval chain routing based on proposer role and change severity
- Multi-level authorization (peer review, security review, principal review)

Author: Principal Engineer
"""

from typing import List


class Authorizer:
    """Controls access to SPEC.md change management."""
    
    # Roles that can PROPOSE changes
    PROPOSER_ROLES = {
        "principal-engineer",
        "security-engineer",
        "lead-engineer"
    }
    
    # Roles that can APPROVE changes
    APPROVER_ROLES = {
        "principal-engineer",
        "security-engineer",
        "lead-engineer"
    }
    
    # Approval chain routing: proposer_role -> [approver_roles]
    # (ordered by authority level)
    APPROVAL_CHAINS = {
        "principal-engineer": [
            "principal-engineer",      # Peer review
            "security-engineer",        # Security review (optional)
        ],
        "security-engineer": [
            "principal-engineer",       # Principal review
            "security-engineer",        # Peer review
        ],
        "lead-engineer": [
            "principal-engineer",       # Principal review
            "security-engineer",        # Security review
        ]
    }
    
    def can_propose(self, role: str) -> bool:
        """Check if role is authorized to propose changes.
        
        Args:
            role: Role to check (e.g., "principal-engineer", "engineer")
            
        Returns:
            True if role can propose, False otherwise
        """
        return role in self.PROPOSER_ROLES
    
    def can_approve(self, role: str) -> bool:
        """Check if role is authorized to approve changes.
        
        Args:
            role: Role to check
            
        Returns:
            True if role can approve, False otherwise
        """
        return role in self.APPROVER_ROLES
    
    def get_approval_chain(self, proposer_role: str) -> List[str]:
        """Get approval chain for a proposer role.
        
        Returns the roles that must approve before a proposal from the given
        proposer role can be applied. Ordered by authority level.
        
        Args:
            proposer_role: Role of proposal author
            
        Returns:
            List of approver roles in order
        """
        return self.APPROVAL_CHAINS.get(proposer_role, [])
    
    def requires_security_review(self, proposal) -> bool:
        """Check if proposal requires security review.
        
        Args:
            proposal: ChangeProposal to check
            
        Returns:
            True if security review is required
        """
        # Breaking changes always need security review
        if hasattr(proposal, 'breaking_change') and proposal.breaking_change:
            return True
        
        # Changes affecting "SECURITY", "AUTHORIZATION", etc. need review
        security_keywords = ["security", "authorization", "authentication", "audit", "privacy"]
        if hasattr(proposal, 'affected_sections'):
            for section in proposal.affected_sections:
                if any(kw in section.lower() for kw in security_keywords):
                    return True
        
        return False
    
    def is_final_approval(self, approver_role: str) -> bool:
        """Check if role's approval is final (no further review needed).
        
        Args:
            approver_role: Role of approver
            
        Returns:
            True if approval from this role is final
        """
        return approver_role == "principal-engineer"
