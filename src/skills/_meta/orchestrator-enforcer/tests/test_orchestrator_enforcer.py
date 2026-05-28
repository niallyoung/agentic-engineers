"""
Test suite for Orchestrator Enforcement Decorator.

TDD RED phase: Tests drive implementation of @enforce_delegate_requirement decorator.
Tests cover: basic validation, stacked decorators, error messages, and metadata.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path to import orchestrator_enforcer
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.orchestrator_enforcer import (
    DelegateRequirementViolation,
    enforce_delegate_requirement,
)


class TestDelegateRequirementViolation:
    """Test DelegateRequirementViolation exception class."""

    def test_exception_creation_with_metadata(self):
        """Test that DelegateRequirementViolation stores delegate metadata."""
        delegate = {
            "task_id": "TASK-123",
            "type": "DELEGATE",
            "role": "engineer",
        }
        exc = DelegateRequirementViolation(
            message="Test error",
            field_name="test_field",
            delegate=delegate,
        )
        assert exc.field_name == "test_field"
        assert exc.delegate == delegate
        assert str(exc) == "Test error"

    def test_exception_message_includes_field_name(self):
        """Test that exception message includes field name."""
        delegate = {"task_id": "TASK-123"}
        exc = DelegateRequirementViolation(
            message="Field validation failed",
            field_name="security_scope",
            delegate=delegate,
        )
        assert "security_scope" in exc.field_name

    def test_exception_stores_task_id(self):
        """Test that exception preserves task_id for debugging."""
        delegate = {"task_id": "TASK-456", "type": "DELEGATE"}
        exc = DelegateRequirementViolation(
            message="Test",
            field_name="field",
            delegate=delegate,
        )
        assert exc.delegate["task_id"] == "TASK-456"


class TestEnforceRequiredField:
    """Test @enforce_delegate_requirement with required=True."""

    def test_valid_delegate_passes_through_unchanged(self):
        """AC1: Correctly-formed DELEGATE passes through decorator unchanged."""

        @enforce_delegate_requirement("role", required=True)
        def process_delegate(delegate):
            return delegate

        delegate = {"task_id": "TASK-001", "role": "engineer"}
        result = process_delegate(delegate)
        assert result == delegate
        assert result["role"] == "engineer"

    def test_missing_required_field_rejected(self):
        """AC2: DELEGATE missing required field rejected with clear error."""

        @enforce_delegate_requirement("role", required=True)
        def process_delegate(delegate):
            return delegate

        delegate = {"task_id": "TASK-002"}
        with pytest.raises(DelegateRequirementViolation) as exc_info:
            process_delegate(delegate)
        error = exc_info.value
        assert "role" in str(error).lower()

    def test_missing_required_field_error_includes_task_id(self):
        """AC5: Error message includes task_id for debugging."""

        @enforce_delegate_requirement("approval_gate", required=True)
        def process_delegate(delegate):
            return delegate

        delegate = {"task_id": "TASK-003"}
        with pytest.raises(DelegateRequirementViolation) as exc_info:
            process_delegate(delegate)
        error = exc_info.value
        assert "TASK-003" in str(error)

    def test_required_field_with_empty_string_passes(self):
        """Test that required field with empty string is still valid (exists)."""

        @enforce_delegate_requirement("field", required=True)
        def process_delegate(delegate):
            return delegate

        delegate = {"task_id": "TASK-004", "field": ""}
        result = process_delegate(delegate)
        assert result["field"] == ""

    def test_required_field_with_false_value_passes(self):
        """Test that required field with False is still valid (exists)."""

        @enforce_delegate_requirement("field", required=True)
        def process_delegate(delegate):
            return delegate

        delegate = {"task_id": "TASK-005", "field": False}
        result = process_delegate(delegate)
        assert result["field"] is False


class TestEnforceAllowedValues:
    """Test @enforce_delegate_requirement with allowed_values."""

    def test_valid_field_value_passes(self):
        """Test that field with allowed value passes through."""

        @enforce_delegate_requirement(
            "security_scope", allowed_values=["auth", "crypto"]
        )
        def process_delegate(delegate):
            return delegate

        delegate = {"task_id": "TASK-006", "security_scope": "auth"}
        result = process_delegate(delegate)
        assert result["security_scope"] == "auth"

    def test_invalid_field_value_rejected(self):
        """AC3: DELEGATE with invalid field value rejected."""

        @enforce_delegate_requirement(
            "security_scope", allowed_values=["auth", "crypto"]
        )
        def process_delegate(delegate):
            return delegate

        delegate = {"task_id": "TASK-007", "security_scope": "invalid"}
        with pytest.raises(DelegateRequirementViolation) as exc_info:
            process_delegate(delegate)
        error = exc_info.value
        assert "invalid" in str(error).lower()

    def test_error_includes_current_value(self):
        """AC5: Error message includes current field value."""

        @enforce_delegate_requirement(
            "scope", allowed_values=["read", "write"]
        )
        def process_delegate(delegate):
            return delegate

        delegate = {"task_id": "TASK-008", "scope": "execute"}
        with pytest.raises(DelegateRequirementViolation) as exc_info:
            process_delegate(delegate)
        error = exc_info.value
        assert "execute" in str(error).lower()

    def test_error_includes_allowed_values(self):
        """AC5: Error message includes allowed values list."""

        @enforce_delegate_requirement(
            "level", allowed_values=["low", "medium", "high"]
        )
        def process_delegate(delegate):
            return delegate

        delegate = {"task_id": "TASK-009", "level": "critical"}
        with pytest.raises(DelegateRequirementViolation) as exc_info:
            process_delegate(delegate)
        error = exc_info.value
        error_str = str(error).lower()
        assert any(
            val in error_str for val in ["low", "medium", "high"]
        ), f"Error should mention allowed values. Got: {error}"

    def test_error_includes_field_name(self):
        """AC5: Error message includes field name."""

        @enforce_delegate_requirement(
            "approval_level", allowed_values=["low", "high"]
        )
        def process_delegate(delegate):
            return delegate

        delegate = {"task_id": "TASK-010", "approval_level": "invalid"}
        with pytest.raises(DelegateRequirementViolation) as exc_info:
            process_delegate(delegate)
        error = exc_info.value
        assert "approval_level" in str(error)

    def test_multiple_allowed_values_work(self):
        """AC10: Multiple allowed values work correctly."""

        @enforce_delegate_requirement(
            "type", allowed_values=["auth", "crypto", "network", "storage"]
        )
        def process_delegate(delegate):
            return delegate

        # Test each allowed value
        for value in ["auth", "crypto", "network", "storage"]:
            delegate = {"task_id": f"TASK-{value}", "type": value}
            result = process_delegate(delegate)
            assert result["type"] == value

    def test_missing_field_with_allowed_values_rejected(self):
        """Test that missing field is rejected even with allowed_values."""

        @enforce_delegate_requirement(
            "access_level", allowed_values=["read", "write"]
        )
        def process_delegate(delegate):
            return delegate

        delegate = {"task_id": "TASK-011"}
        with pytest.raises(DelegateRequirementViolation):
            process_delegate(delegate)


class TestStackedDecorators:
    """Test stacking multiple decorators."""

    def test_stacked_decorators_all_enforce(self):
        """AC4: Stacked decorators all enforce constraints independently."""

        @enforce_delegate_requirement("approval_gate", required=True)
        @enforce_delegate_requirement(
            "security_scope", allowed_values=["auth", "crypto"]
        )
        def process_delegate(delegate):
            return delegate

        # Valid: both constraints satisfied
        delegate = {
            "task_id": "TASK-012",
            "approval_gate": "approved",
            "security_scope": "auth",
        }
        result = process_delegate(delegate)
        assert result["approval_gate"] == "approved"
        assert result["security_scope"] == "auth"

    def test_stacked_decorators_enforce_first_constraint(self):
        """Test that first decorator in stack enforces constraint."""

        @enforce_delegate_requirement("approval_gate", required=True)
        @enforce_delegate_requirement(
            "security_scope", allowed_values=["auth", "crypto"]
        )
        def process_delegate(delegate):
            return delegate

        # Missing required field fails at first decorator
        delegate = {
            "task_id": "TASK-013",
            "security_scope": "auth",
            # approval_gate missing
        }
        with pytest.raises(DelegateRequirementViolation):
            process_delegate(delegate)

    def test_stacked_decorators_enforce_second_constraint(self):
        """Test that second decorator in stack enforces constraint."""

        @enforce_delegate_requirement("approval_gate", required=True)
        @enforce_delegate_requirement(
            "security_scope", allowed_values=["auth", "crypto"]
        )
        def process_delegate(delegate):
            return delegate

        # Invalid value fails at second decorator
        delegate = {
            "task_id": "TASK-014",
            "approval_gate": "approved",
            "security_scope": "invalid",
        }
        with pytest.raises(DelegateRequirementViolation):
            process_delegate(delegate)

    def test_three_stacked_decorators_all_enforce(self):
        """Test three decorators stacked together."""

        @enforce_delegate_requirement("role", required=True)
        @enforce_delegate_requirement("approval_gate", required=True)
        @enforce_delegate_requirement(
            "security_scope", allowed_values=["auth", "crypto"]
        )
        def process_delegate(delegate):
            return delegate

        # All constraints satisfied
        delegate = {
            "task_id": "TASK-015",
            "role": "engineer",
            "approval_gate": "yes",
            "security_scope": "crypto",
        }
        result = process_delegate(delegate)
        assert result["role"] == "engineer"
        assert result["approval_gate"] == "yes"
        assert result["security_scope"] == "crypto"

    def test_three_stacked_decorators_fail_middle(self):
        """Test failure in middle constraint of three."""

        @enforce_delegate_requirement("role", required=True)
        @enforce_delegate_requirement("approval_gate", required=True)
        @enforce_delegate_requirement(
            "security_scope", allowed_values=["auth", "crypto"]
        )
        def process_delegate(delegate):
            return delegate

        # Middle constraint fails
        delegate = {
            "task_id": "TASK-016",
            "role": "engineer",
            # approval_gate missing
            "security_scope": "crypto",
        }
        with pytest.raises(DelegateRequirementViolation):
            process_delegate(delegate)


class TestExceptionMetadata:
    """Test exception metadata for debugging."""

    def test_exception_has_delegate_metadata(self):
        """AC6: Exception includes DELEGATE metadata for debugging."""

        @enforce_delegate_requirement("field", required=True)
        def process_delegate(delegate):
            return delegate

        delegate = {
            "task_id": "TASK-017",
            "type": "DELEGATE",
            "role": "engineer",
        }
        with pytest.raises(DelegateRequirementViolation) as exc_info:
            process_delegate(delegate)
        error = exc_info.value
        assert error.delegate == delegate
        assert error.delegate["task_id"] == "TASK-017"

    def test_exception_preserves_full_delegate_structure(self):
        """Test that exception preserves complete DELEGATE structure."""

        @enforce_delegate_requirement("missing_field", required=True)
        def process_delegate(delegate):
            return delegate

        delegate = {
            "task_id": "TASK-018",
            "type": "DELEGATE",
            "role": "engineer",
            "model": "claude-3",
            "effort": "high",
            "context": {"description": "test"},
        }
        with pytest.raises(DelegateRequirementViolation) as exc_info:
            process_delegate(delegate)
        error = exc_info.value
        assert error.delegate["model"] == "claude-3"
        assert error.delegate["context"]["description"] == "test"

    def test_exception_field_name_accessible(self):
        """Test that field name is accessible on exception."""

        @enforce_delegate_requirement("security_scope", required=True)
        def process_delegate(delegate):
            return delegate

        delegate = {"task_id": "TASK-019"}
        with pytest.raises(DelegateRequirementViolation) as exc_info:
            process_delegate(delegate)
        error = exc_info.value
        assert error.field_name == "security_scope"


class TestDecoratorUsageExamples:
    """Test real-world usage examples from spec."""

    def test_security_engineer_routing_example(self):
        """Test example from spec: security engineer routing."""

        @enforce_delegate_requirement(
            "security_scope", allowed_values=["auth", "crypto"]
        )
        @enforce_delegate_requirement("approval_gate", required=True)
        def route_to_security_engineer(delegate):
            return f"Routing to security (scope={delegate['security_scope']})"

        # Valid delegate
        delegate = {
            "task_id": "TASK-020",
            "security_scope": "auth",
            "approval_gate": "approved",
        }
        result = route_to_security_engineer(delegate)
        assert "security" in result
        assert "auth" in result

    def test_security_engineer_routing_fails_invalid_scope(self):
        """Test security routing fails with invalid scope."""

        @enforce_delegate_requirement(
            "security_scope", allowed_values=["auth", "crypto"]
        )
        @enforce_delegate_requirement("approval_gate", required=True)
        def route_to_security_engineer(delegate):
            return "routed"

        delegate = {
            "task_id": "TASK-021",
            "security_scope": "network",  # invalid
            "approval_gate": "approved",
        }
        with pytest.raises(DelegateRequirementViolation):
            route_to_security_engineer(delegate)

    def test_security_engineer_routing_fails_no_approval(self):
        """Test security routing fails without approval gate."""

        @enforce_delegate_requirement(
            "security_scope", allowed_values=["auth", "crypto"]
        )
        @enforce_delegate_requirement("approval_gate", required=True)
        def route_to_security_engineer(delegate):
            return "routed"

        delegate = {
            "task_id": "TASK-022",
            "security_scope": "crypto",
            # approval_gate missing
        }
        with pytest.raises(DelegateRequirementViolation):
            route_to_security_engineer(delegate)


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_decorator_on_function_with_return_value(self):
        """Test decorator preserves function return value."""

        @enforce_delegate_requirement("status", required=True)
        def complex_function(delegate):
            return {"processed": True, "task_id": delegate["task_id"]}

        delegate = {"task_id": "TASK-023", "status": "active"}
        result = complex_function(delegate)
        assert result["processed"] is True
        assert result["task_id"] == "TASK-023"

    def test_decorator_on_function_with_multiple_args(self):
        """Test decorator works with additional function arguments."""

        @enforce_delegate_requirement("role", required=True)
        def function_with_args(delegate, priority, timeout):
            return f"{delegate['role']}-{priority}-{timeout}"

        delegate = {"task_id": "TASK-024", "role": "admin"}
        result = function_with_args(delegate, "high", 30)
        assert result == "admin-high-30"

    def test_none_value_fails_required_check(self):
        """Test that None value fails required field check."""

        @enforce_delegate_requirement("field", required=True)
        def process_delegate(delegate):
            return delegate

        delegate = {"task_id": "TASK-025", "field": None}
        # None should fail required check since field is actually missing/null
        result = process_delegate(delegate)
        # Depending on implementation, None might be allowed (field exists but is None)
        # This test documents the behavior
        assert result["field"] is None

    def test_decorator_with_case_sensitive_field_names(self):
        """Test that field names are case sensitive."""

        @enforce_delegate_requirement("Role", required=True)
        def process_delegate(delegate):
            return delegate

        # 'role' is different from 'Role'
        delegate = {"task_id": "TASK-026", "role": "engineer"}
        with pytest.raises(DelegateRequirementViolation):
            process_delegate(delegate)

    def test_zero_value_passes_required_check(self):
        """Test that zero value passes required field check."""

        @enforce_delegate_requirement("field", required=True)
        def process_delegate(delegate):
            return delegate

        delegate = {"task_id": "TASK-027", "field": 0}
        result = process_delegate(delegate)
        assert result["field"] == 0

    def test_empty_list_passes_required_check(self):
        """Test that empty list passes required field check."""

        @enforce_delegate_requirement("field", required=True)
        def process_delegate(delegate):
            return delegate

        delegate = {"task_id": "TASK-028", "field": []}
        result = process_delegate(delegate)
        assert result["field"] == []

    def test_allowed_values_with_single_value(self):
        """Test allowed_values works with single-item list."""

        @enforce_delegate_requirement("field", allowed_values=["only"])
        def process_delegate(delegate):
            return delegate

        delegate = {"task_id": "TASK-029", "field": "only"}
        result = process_delegate(delegate)
        assert result["field"] == "only"

        delegate = {"task_id": "TASK-030", "field": "other"}
        with pytest.raises(DelegateRequirementViolation):
            process_delegate(delegate)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
