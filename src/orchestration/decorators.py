"""Decorators for enforcing DELEGATE requirements at runtime."""

import functools
from typing import Callable, Dict, Any, List, Optional


class SecurityError(Exception):
    """Raised when security requirements are not met."""
    pass


def enforce_delegate_requirement(
    required_fields: Optional[List[str]] = None,
    security_scope: Optional[str] = None,
    approval_gate: Optional[str] = None
):
    """
    Decorator to enforce DELEGATE requirements before task execution.
    
    Args:
        required_fields: List of required DELEGATE fields
        security_scope: Required security scope (e.g., 'auth', 'crypto')
        approval_gate: Required approval gate (e.g., 'security_engineer')
    
    Raises:
        SecurityError: If DELEGATE requirements not met
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(delegate: Dict[str, Any], *args, **kwargs):
            # Validate DELEGATE schema (basic checks)
            if not isinstance(delegate, dict):
                raise SecurityError("DELEGATE must be a dictionary")
            
            # Check required fields.
            # FAIL CLOSED: a required field is only satisfied by a present,
            # non-null, non-empty value. An empty / whitespace-only string is
            # treated as missing so it cannot be used to bypass an enforced
            # field (e.g. approval_gate="").
            if required_fields:
                for field in required_fields:
                    value = delegate.get(field)
                    if (
                        field not in delegate
                        or value is None
                        or (isinstance(value, str) and not value.strip())
                    ):
                        raise SecurityError(
                            f"DELEGATE missing required field: {field}"
                        )
            
            # Check security scope
            if security_scope:
                if delegate.get('security_scope') != security_scope:
                    raise SecurityError(
                        f"DELEGATE security_scope must be '{security_scope}', "
                        f"got '{delegate.get('security_scope')}'"
                    )
            
            # Check approval gate
            if approval_gate:
                if delegate.get('approval_gate') != approval_gate:
                    raise SecurityError(
                        f"DELEGATE approval_gate must be '{approval_gate}', "
                        f"got '{delegate.get('approval_gate')}'"
                    )
            
            # Execute function with validated DELEGATE
            return func(delegate, *args, **kwargs)
        
        return wrapper
    return decorator
