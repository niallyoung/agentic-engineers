"""
Security regression tests for the orchestration enforcement layer.

Covers fail-closed behaviour of:
  - @enforce_delegate_requirement (src/orchestration/decorators.py)
  - validate_json_schema (src/orchestration/protocol/validation.py)
"""

import pytest

from src.orchestration.decorators import (
    enforce_delegate_requirement,
    SecurityError,
)
from src.orchestration.protocol.validation import (
    validate_json_schema,
    DELEGATE_SCHEMA,
)


class TestEnforceDelegateRequirementFailClosed:
    """@enforce_delegate_requirement must fail CLOSED."""

    def test_missing_required_field_rejected(self):
        @enforce_delegate_requirement(required_fields=["approval_gate"])
        def handler(delegate):
            return "executed"

        with pytest.raises(SecurityError):
            handler({"task_id": "2026-05-30-x"})

    def test_none_required_field_rejected(self):
        @enforce_delegate_requirement(required_fields=["approval_gate"])
        def handler(delegate):
            return "executed"

        with pytest.raises(SecurityError):
            handler({"approval_gate": None})

    def test_empty_string_required_field_rejected(self):
        """Empty string must not satisfy an enforced field (fail-closed)."""
        @enforce_delegate_requirement(required_fields=["approval_gate"])
        def handler(delegate):
            return "executed"

        with pytest.raises(SecurityError):
            handler({"approval_gate": ""})

    def test_whitespace_required_field_rejected(self):
        @enforce_delegate_requirement(required_fields=["approval_gate"])
        def handler(delegate):
            return "executed"

        with pytest.raises(SecurityError):
            handler({"approval_gate": "   "})

    def test_non_dict_delegate_rejected(self):
        @enforce_delegate_requirement(required_fields=["approval_gate"])
        def handler(delegate):
            return "executed"

        with pytest.raises(SecurityError):
            handler("not-a-dict")

    def test_security_scope_mismatch_rejected(self):
        @enforce_delegate_requirement(security_scope="crypto")
        def handler(delegate):
            return "executed"

        with pytest.raises(SecurityError):
            handler({"security_scope": "auth"})

    def test_approval_gate_mismatch_rejected(self):
        @enforce_delegate_requirement(approval_gate="security_engineer")
        def handler(delegate):
            return "executed"

        with pytest.raises(SecurityError):
            handler({"approval_gate": "lead_engineer"})

    def test_valid_delegate_executes(self):
        @enforce_delegate_requirement(
            required_fields=["approval_gate"],
            security_scope="crypto",
            approval_gate="security_engineer",
        )
        def handler(delegate):
            return "executed"

        result = handler({
            "security_scope": "crypto",
            "approval_gate": "security_engineer",
        })
        assert result == "executed"


class TestValidateJsonSchemaFailClosed:
    """validate_json_schema must fail CLOSED when it cannot validate."""

    def test_missing_jsonschema_returns_error(self, monkeypatch):
        """If jsonschema cannot be imported, validation must NOT pass silently."""
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "jsonschema":
                raise ImportError("simulated missing jsonschema")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        errors = validate_json_schema({"task_id": "x"}, DELEGATE_SCHEMA)
        assert errors, "expected fail-closed error when jsonschema is unavailable"
        assert any("jsonschema" in e.lower() for e in errors)
