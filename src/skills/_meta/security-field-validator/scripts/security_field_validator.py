"""
Security Field Validator for DELEGATE blocks.

This module validates security-critical DELEGATE fields:
- security_scope: enum [none|auth|crypto|pii|secrets|injection|supply_chain]
- approval_gate: enum [none|lead_engineer|principal_engineer|security_engineer|cto]
- audit_required: boolean

Validation Rules:
1. If security_scope != none, approval_gate MUST be set (not "none")
2. If approval_gate is set, audit_required MUST be true
3. Security scopes route to Security Engineer minimum
"""

from typing import Dict, Any, Optional, List


class SecurityFieldValidator:
    """
    Validator for security-critical DELEGATE fields.
    
    Enforces:
    - Enum constraints for security_scope and approval_gate
    - Dependent field constraints (security_scope → approval_gate → audit_required)
    - Routing logic (security_scope → required_role)
    """
    
    SECURITY_SCOPES = ["none", "auth", "crypto", "pii", "secrets", "injection", "supply_chain"]
    APPROVAL_GATES = ["none", "lead_engineer", "principal_engineer", "security_engineer", "cto"]
    
    def validate(self, delegate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate security fields in a DELEGATE block.
        
        Args:
            delegate: DELEGATE block (dict) to validate
            
        Returns:
            {
                "valid": bool,
                "errors": list of error messages,
                "warnings": list of warning messages,
                "security_scope": str (resolved value),
                "approval_gate": str (resolved value),
                "audit_required": bool (resolved value),
                "required_role": str or None (routing requirement)
            }
        """
        errors = []
        warnings = []
        
        # Get fields with defaults (non-security tasks default to "none")
        security_scope = delegate.get("security_scope", "none")
        approval_gate = delegate.get("approval_gate", "none")
        audit_required = delegate.get("audit_required", False)
        
        # Validate enum values
        if security_scope not in self.SECURITY_SCOPES:
            errors.append(
                f"security_scope '{security_scope}' not in {self.SECURITY_SCOPES}"
            )
        
        if approval_gate not in self.APPROVAL_GATES:
            errors.append(
                f"approval_gate '{approval_gate}' not in {self.APPROVAL_GATES}"
            )
        
        # Validation Rule 1: If security_scope != none, approval_gate MUST be set (not "none")
        if security_scope != "none" and approval_gate == "none":
            errors.append(
                f"Invalid combination: security_scope='{security_scope}' requires approval_gate "
                f"to be set (not 'none'). Got approval_gate='{approval_gate}'"
            )
        
        # Validation Rule 2: If approval_gate is set, audit_required MUST be true
        if approval_gate != "none" and not audit_required:
            errors.append(
                f"Invalid combination: approval_gate='{approval_gate}' requires audit_required=true. "
                f"Got audit_required={audit_required}"
            )
        
        # Determine required role based on security_scope
        required_role = self._determine_required_role(security_scope)
        
        result = {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "security_scope": security_scope,
            "approval_gate": approval_gate,
            "audit_required": audit_required,
            "required_role": required_role,
        }
        
        return result
    
    def _determine_required_role(self, security_scope: str) -> Optional[str]:
        """
        Determine minimum required role based on security scope.
        
        Args:
            security_scope: The security scope value
            
        Returns:
            Role name ("security_engineer") or None if no special routing required
        """
        if security_scope in ["auth", "crypto", "pii", "secrets", "injection", "supply_chain"]:
            return "security_engineer"
        return None
    
    def apply_defaults(self, delegate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply default values for security fields if not present.
        
        Args:
            delegate: DELEGATE block to update
            
        Returns:
            Updated delegate dict
        """
        if "security_scope" not in delegate:
            delegate["security_scope"] = "none"
        if "approval_gate" not in delegate:
            delegate["approval_gate"] = "none"
        if "audit_required" not in delegate:
            delegate["audit_required"] = False
        
        return delegate


def validate_security_fields(delegate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to validate security fields in a DELEGATE block.
    
    Args:
        delegate: DELEGATE block (dict) to validate
        
    Returns:
        Validation result dict
    """
    validator = SecurityFieldValidator()
    return validator.validate(delegate)
