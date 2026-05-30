"""
Security Field Validator Package

Validates security-critical DELEGATE fields:
- security_scope
- approval_gate
- audit_required
"""

__version__ = "1.0.0"
__author__ = "Principal Engineer"

from scripts.security_field_validator import (
    SecurityFieldValidator,
    validate_security_fields,
)

__all__ = [
    "SecurityFieldValidator",
    "validate_security_fields",
]
