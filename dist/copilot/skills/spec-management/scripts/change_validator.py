"""
change_validator.py — Validates change proposals for format and completeness.

Enforces:
- change_id format (SPEC-YYYY-NNN)
- Required fields (change_id, proposer, affected_sections, rationale, etc.)
- Field constraints (timestamp ISO-8601, rationale ≥ 50 chars)
- Breaking change requirements (migration_path required)

Author: Principal Engineer
"""

from dataclasses import dataclass
from typing import List, Optional
import re
from datetime import datetime


@dataclass
class ValidationResult:
    """Result of proposal validation"""
    is_valid: bool
    errors: List[str]


class ChangeValidator:
    """Validates change proposals."""
    
    # Pattern for change_id: SPEC-YYYY-NNN
    CHANGE_ID_PATTERN = re.compile(r'^SPEC-\d{4}-\d{3}$')
    
    # ISO-8601 timestamp pattern
    TIMESTAMP_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$')
    
    # Constants
    MIN_RATIONALE_LENGTH = 50
    MIN_CHANGE_ID_LENGTH = 3
    MAX_CHANGE_ID_LENGTH = 64
    
    def validate(self, proposal) -> ValidationResult:
        """Validate a change proposal.
        
        Args:
            proposal: ChangeProposal object to validate
            
        Returns:
            ValidationResult with is_valid flag and errors
        """
        errors = []
        
        # Validate change_id
        if not hasattr(proposal, 'change_id') or not proposal.change_id:
            errors.append("change_id is required")
        elif not self.CHANGE_ID_PATTERN.match(proposal.change_id):
            errors.append(f"change_id must match format SPEC-YYYY-NNN (got: {proposal.change_id})")
        elif len(proposal.change_id) > self.MAX_CHANGE_ID_LENGTH:
            errors.append(f"change_id must be ≤ {self.MAX_CHANGE_ID_LENGTH} characters")
        
        # Validate proposer
        if not hasattr(proposal, 'proposer') or not proposal.proposer:
            errors.append("proposer is required")
        
        # Validate proposer_role
        if not hasattr(proposal, 'proposer_role') or not proposal.proposer_role:
            errors.append("proposer_role is required")
        
        # Validate timestamp
        if not hasattr(proposal, 'timestamp') or not proposal.timestamp:
            errors.append("timestamp is required")
        elif not self.TIMESTAMP_PATTERN.match(proposal.timestamp):
            errors.append(f"timestamp must be ISO-8601 format (got: {proposal.timestamp})")
        else:
            # Try to parse to verify validity
            try:
                datetime.fromisoformat(proposal.timestamp.replace('Z', '+00:00'))
            except ValueError:
                errors.append(f"timestamp is not a valid ISO-8601 datetime")
        
        # Validate affected_sections
        if not hasattr(proposal, 'affected_sections') or not proposal.affected_sections:
            errors.append("affected_sections is required and must be non-empty")
        elif not isinstance(proposal.affected_sections, list):
            errors.append("affected_sections must be a list")
        
        # Validate proposed_changes
        if not hasattr(proposal, 'proposed_changes') or not proposal.proposed_changes:
            errors.append("proposed_changes is required and must be non-empty")
        elif not isinstance(proposal.proposed_changes, dict):
            errors.append("proposed_changes must be a dict")
        elif any(not v for v in proposal.proposed_changes.values()):
            errors.append("proposed_changes values cannot be empty")
        
        # Validate rationale
        if not hasattr(proposal, 'rationale') or not proposal.rationale:
            errors.append("rationale is required")
        elif len(proposal.rationale) < self.MIN_RATIONALE_LENGTH:
            errors.append(f"rationale must be ≥ {self.MIN_RATIONALE_LENGTH} characters (got: {len(proposal.rationale)})")
        
        # Validate breaking change requirements
        if hasattr(proposal, 'breaking_change') and proposal.breaking_change:
            if not hasattr(proposal, 'migration_path') or not proposal.migration_path:
                errors.append("breaking_change=true requires migration_path")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )
