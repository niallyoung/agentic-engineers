"""
Orchestrator Enforcement Decorator.

Provides @enforce_delegate_requirement decorator for runtime validation
of DELEGATE fields, ensuring orchestrator constraints are enforced
before function execution.

Usage:
    @enforce_delegate_requirement('security_scope', allowed_values=['auth','crypto'])
    @enforce_delegate_requirement('approval_gate', required=True)
    def route_to_security_engineer(delegate):
        # Won't execute if requirements not met
        ...
"""

from functools import wraps
from typing import Any, Dict, List, Optional


class DelegateRequirementViolation(Exception):
    """Exception raised when a DELEGATE fails requirement validation.
    
    Stores metadata about the violation for debugging and logging.
    """

    def __init__(
        self,
        message: str,
        field_name: str,
        delegate: Dict[str, Any],
        current_value: Optional[Any] = None,
        allowed_values: Optional[List[Any]] = None,
    ):
        """Initialize DelegateRequirementViolation.
        
        Args:
            message: Human-readable error message
            field_name: Name of the field that failed validation
            delegate: The DELEGATE dict that failed validation
            current_value: The actual value of the field (optional)
            allowed_values: List of allowed values if validation is value-based (optional)
        """
        self.message = message
        self.field_name = field_name
        self.delegate = delegate
        self.current_value = current_value
        self.allowed_values = allowed_values
        super().__init__(message)


def enforce_delegate_requirement(
    field_name: str,
    allowed_values: Optional[List[str]] = None,
    required: bool = True,
):
    """Decorator factory for DELEGATE field requirement enforcement.
    
    Creates a decorator that validates DELEGATE fields before function execution.
    Supports stacking multiple decorators on the same function.
    
    Args:
        field_name: Name of the field to validate
        allowed_values: Optional list of allowed values. If provided, the field
                       value must be in this list.
        required: If True (default), field must exist in delegate.
                 If False, field is optional but must match allowed_values if present.
    
    Returns:
        Decorator function
        
    Raises:
        DelegateRequirementViolation: When DELEGATE fails validation
        
    Example:
        @enforce_delegate_requirement('security_scope', allowed_values=['auth','crypto'])
        @enforce_delegate_requirement('approval_gate', required=True)
        def route_to_security_engineer(delegate):
            # Won't execute if requirements not met
            return process(delegate)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(delegate, *args, **kwargs):
            # Validate that delegate is a dict
            if not isinstance(delegate, dict):
                raise DelegateRequirementViolation(
                    message=f"DELEGATE must be a dict, got {type(delegate).__name__}",
                    field_name=field_name,
                    delegate=delegate if isinstance(delegate, dict) else {},
                )

            task_id = delegate.get("task_id", "unknown")
            field_value = delegate.get(field_name)

            # Check if field is required
            if required and field_name not in delegate:
                message = (
                    f"Required field '{field_name}' missing from DELEGATE {task_id}"
                )
                raise DelegateRequirementViolation(
                    message=message,
                    field_name=field_name,
                    delegate=delegate,
                    current_value=None,
                    allowed_values=allowed_values,
                )

            # Check if field value is in allowed_values (if specified)
            if allowed_values is not None and field_name in delegate:
                if field_value not in allowed_values:
                    message = (
                        f"Field '{field_name}' has invalid value '{field_value}' "
                        f"in DELEGATE {task_id}. "
                        f"Allowed values: {allowed_values}"
                    )
                    raise DelegateRequirementViolation(
                        message=message,
                        field_name=field_name,
                        delegate=delegate,
                        current_value=field_value,
                        allowed_values=allowed_values,
                    )

            # Validation passed, call the wrapped function
            return func(delegate, *args, **kwargs)

        return wrapper

    return decorator
