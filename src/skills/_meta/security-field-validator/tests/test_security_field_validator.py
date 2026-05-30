"""
Test suite for security-critical DELEGATE field validator.

Tests cover:
1. Default values for non-security tasks
2. Security scope routing to Security Engineer
3. Approval gate enforcement
4. Validation rule constraints (dependent fields)
5. Invalid combinations rejection
"""

import pytest
import sys
from pathlib import Path

# Add scripts directory to path to import the validator
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from security_field_validator import SecurityFieldValidator


# ============================================================================
# TEST CASES (TDD RED phase - all should fail initially)
# ============================================================================

class TestSecurityFieldDefaults:
    """AC1: Non-security tasks have correct defaults"""
    
    def test_non_security_task_defaults_to_none(self):
        """Test 1: Non-security task should default to security_scope=none, approval_gate=none"""
        validator = SecurityFieldValidator()
        delegate = {}  # No security fields specified
        
        result = validator.validate(delegate)
        
        assert result["valid"] is True
        assert result["security_scope"] == "none"
        assert result["approval_gate"] == "none"
        assert result["audit_required"] is False
        assert result["required_role"] is None
    
    def test_non_security_task_with_explicit_none_values(self):
        """Test 2: Explicitly setting none values should work"""
        validator = SecurityFieldValidator()
        delegate = {
            "security_scope": "none",
            "approval_gate": "none",
            "audit_required": False,
        }
        
        result = validator.validate(delegate)
        
        assert result["valid"] is True
        assert result["errors"] == []


class TestSecurityScopeRouting:
    """AC2: Auth/crypto/pii/secrets/injection/supply_chain routed to Security Engineer"""
    
    def test_auth_scope_routes_to_security_engineer(self):
        """Test 3: auth scope requires Security Engineer routing"""
        validator = SecurityFieldValidator()
        delegate = {
            "security_scope": "auth",
            "approval_gate": "lead_engineer",
            "audit_required": True,
        }
        
        result = validator.validate(delegate)
        
        assert result["valid"] is True
        assert result["required_role"] == "security_engineer"
    
    def test_crypto_scope_routes_to_security_engineer(self):
        """Test 4: crypto scope requires Security Engineer routing"""
        validator = SecurityFieldValidator()
        delegate = {
            "security_scope": "crypto",
            "approval_gate": "security_engineer",
            "audit_required": True,
        }
        
        result = validator.validate(delegate)
        
        assert result["valid"] is True
        assert result["required_role"] == "security_engineer"
    
    def test_pii_scope_routes_to_security_engineer(self):
        """Test 5: pii scope requires Security Engineer routing"""
        validator = SecurityFieldValidator()
        delegate = {
            "security_scope": "pii",
            "approval_gate": "principal_engineer",
            "audit_required": True,
        }
        
        result = validator.validate(delegate)
        
        assert result["valid"] is True
        assert result["required_role"] == "security_engineer"
    
    def test_secrets_scope_routes_to_security_engineer(self):
        """Test 6: secrets scope requires Security Engineer routing"""
        validator = SecurityFieldValidator()
        delegate = {
            "security_scope": "secrets",
            "approval_gate": "security_engineer",
            "audit_required": True,
        }
        
        result = validator.validate(delegate)
        
        assert result["valid"] is True
        assert result["required_role"] == "security_engineer"
    
    def test_injection_scope_routes_to_security_engineer(self):
        """Test 7: injection scope requires Security Engineer routing"""
        validator = SecurityFieldValidator()
        delegate = {
            "security_scope": "injection",
            "approval_gate": "lead_engineer",
            "audit_required": True,
        }
        
        result = validator.validate(delegate)
        
        assert result["valid"] is True
        assert result["required_role"] == "security_engineer"
    
    def test_supply_chain_scope_routes_to_security_engineer(self):
        """Test 8: supply_chain scope requires Security Engineer routing"""
        validator = SecurityFieldValidator()
        delegate = {
            "security_scope": "supply_chain",
            "approval_gate": "principal_engineer",
            "audit_required": True,
        }
        
        result = validator.validate(delegate)
        
        assert result["valid"] is True
        assert result["required_role"] == "security_engineer"


class TestApprovalGateEnforcement:
    """AC3: Approval gates enforced"""
    
    def test_principal_engineer_approval_gate_valid(self):
        """Test 9: principal_engineer approval gate is enforced"""
        validator = SecurityFieldValidator()
        delegate = {
            "security_scope": "auth",
            "approval_gate": "principal_engineer",
            "audit_required": True,
        }
        
        result = validator.validate(delegate)
        
        assert result["valid"] is True
        assert result["approval_gate"] == "principal_engineer"
    
    def test_cto_escalation_triggering(self):
        """Test 10: CTO escalation can be triggered"""
        validator = SecurityFieldValidator()
        delegate = {
            "security_scope": "supply_chain",
            "approval_gate": "cto",
            "audit_required": True,
        }
        
        result = validator.validate(delegate)
        
        assert result["valid"] is True
        assert result["approval_gate"] == "cto"


class TestInvalidCombinations:
    """AC4: Invalid combinations are rejected"""
    
    def test_security_scope_set_but_approval_gate_none_rejected(self):
        """Test 11: security_scope set but approval_gate=none is INVALID"""
        validator = SecurityFieldValidator()
        delegate = {
            "security_scope": "auth",
            "approval_gate": "none",
            "audit_required": True,
        }
        
        result = validator.validate(delegate)
        
        assert result["valid"] is False
        assert any("approval_gate" in err for err in result["errors"])
    
    def test_approval_gate_set_but_audit_required_false_rejected(self):
        """Test 12: approval_gate set but audit_required=false is INVALID"""
        validator = SecurityFieldValidator()
        delegate = {
            "security_scope": "crypto",
            "approval_gate": "security_engineer",
            "audit_required": False,
        }
        
        result = validator.validate(delegate)
        
        assert result["valid"] is False
        assert any("audit_required" in err for err in result["errors"])
    
    def test_invalid_security_scope_enum(self):
        """Test 13: Invalid security_scope value is rejected"""
        validator = SecurityFieldValidator()
        delegate = {
            "security_scope": "invalid_scope",
            "approval_gate": "lead_engineer",
            "audit_required": True,
        }
        
        result = validator.validate(delegate)
        
        assert result["valid"] is False
        assert any("security_scope" in err for err in result["errors"])
    
    def test_invalid_approval_gate_enum(self):
        """Test 14: Invalid approval_gate value is rejected"""
        validator = SecurityFieldValidator()
        delegate = {
            "security_scope": "auth",
            "approval_gate": "invalid_gate",
            "audit_required": True,
        }
        
        result = validator.validate(delegate)
        
        assert result["valid"] is False
        assert any("approval_gate" in err for err in result["errors"])


class TestValidationRules:
    """AC5: Validation rules work correctly"""
    
    def test_rule_security_scope_requires_approval_gate(self):
        """Rule: If security_scope != none, approval_gate MUST NOT be 'none'"""
        validator = SecurityFieldValidator()
        
        # Valid: security_scope with approval_gate set
        result = validator.validate({
            "security_scope": "auth",
            "approval_gate": "security_engineer",
            "audit_required": True,
        })
        assert result["valid"] is True
        
        # Invalid: security_scope without approval_gate
        result = validator.validate({
            "security_scope": "auth",
            "approval_gate": "none",
            "audit_required": True,
        })
        assert result["valid"] is False
    
    def test_rule_approval_gate_requires_audit(self):
        """Rule: If approval_gate is set, audit_required MUST be true"""
        validator = SecurityFieldValidator()
        
        # Valid: approval_gate with audit_required=true
        result = validator.validate({
            "security_scope": "auth",
            "approval_gate": "principal_engineer",
            "audit_required": True,
        })
        assert result["valid"] is True
        
        # Invalid: approval_gate with audit_required=false
        result = validator.validate({
            "security_scope": "auth",
            "approval_gate": "principal_engineer",
            "audit_required": False,
        })
        assert result["valid"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
