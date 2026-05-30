"""
spec-version-validator package - Audit trail via spec_version field
"""

from .scripts.spec_version_validator import (
    validate_spec_version_format,
    validate_spec_version_match,
    find_tasks_by_spec_version,
    SpecVersionValidationError,
)

__all__ = [
    "validate_spec_version_format",
    "validate_spec_version_match",
    "find_tasks_by_spec_version",
    "SpecVersionValidationError",
]
