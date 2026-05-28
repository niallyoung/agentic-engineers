r"""
spec_version_validator.py - Audit Trail via spec_version Field

Implements spec_version field validation for DELEGATE and HANDBACK schemas.
Enables audit trail linking tasks to SPEC versions for compliance and debugging.

Pattern: ^\d+\.\d+(-.+)?$
Valid examples: '1.0', '1.1', '1.1-2026-05-28', '1.0-rc1'
Invalid examples: 'v1.0', '1', '1.0.0'

Public API:
- validate_spec_version_format(version: str) -> bool
- validate_spec_version_match(block: dict, delegate: dict | None) -> bool
- find_tasks_by_spec_version(tasks: list, spec_version: str) -> list
- SpecVersionValidationError: Exception class
"""

import re
from typing import Optional, List, Dict, Any


class SpecVersionValidationError(Exception):
    """Raised when spec_version validation fails"""

    pass


def validate_spec_version_format(version: str) -> bool:
    r"""
    Validate spec_version format against pattern: ^\d+\.\d+(-.+)?$

    Args:
        version: Version string to validate

    Returns:
        True if format is valid, False otherwise

    Valid examples:
        '1.0'          → True (major.minor)
        '1.1'          → True (major.minor)
        '1.0-2026-05-28'  → True (major.minor-suffix)
        '1.0-rc1'      → True (major.minor-suffix)
        '2.0-alpha-beta'  → True (multi-part suffix)

    Invalid examples:
        'v1.0'         → False (v-prefix)
        '1'            → False (single version)
        '1.0.0'        → False (three-part version)
        ''             → False (empty)
        'a.b'          → False (non-numeric)
    """
    if not isinstance(version, str) or len(version) == 0:
        return False

    pattern = r"^\d+\.\d+(-.+)?$"
    return re.match(pattern, version) is not None


def validate_spec_version_match(
    block: Dict[str, Any], delegate: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Validate spec_version field in DELEGATE or HANDBACK.

    For DELEGATE blocks:
    - Ensures spec_version field exists and has valid format
    - Returns True if valid

    For HANDBACK blocks (when delegate provided):
    - Ensures spec_version field exists and has valid format
    - Ensures HANDBACK spec_version matches DELEGATE spec_version
    - Raises SpecVersionValidationError if mismatch

    Args:
        block: DELEGATE or HANDBACK block to validate
        delegate: DELEGATE block for comparison (None for DELEGATE validation)

    Returns:
        True if validation passes

    Raises:
        SpecVersionValidationError: If validation fails

    Examples:
        # DELEGATE validation
        delegate = {"task_id": "2026-05-30-task", "spec_version": "1.0"}
        validate_spec_version_match(delegate, None)  # → True

        # HANDBACK validation (matching)
        handback = {"task_id": "2026-05-30-task", "spec_version": "1.0"}
        validate_spec_version_match(handback, delegate)  # → True

        # HANDBACK validation (mismatch)
        handback = {"task_id": "2026-05-30-task", "spec_version": "1.1"}
        validate_spec_version_match(handback, delegate)  # → SpecVersionValidationError
    """
    task_id = block.get("task_id", "unknown")
    block_type = block.get("type", "unknown")

    # Check if spec_version field exists
    if "spec_version" not in block:
        raise SpecVersionValidationError(
            f"DELEGATE/HANDBACK {task_id}: spec_version field is required but missing"
        )

    spec_version = block.get("spec_version")

    # Validate format
    if not validate_spec_version_format(spec_version):
        raise SpecVersionValidationError(
            f"{block_type} {task_id}: spec_version '{spec_version}' has invalid format. "
            f"Expected format: major.minor[-suffix] (e.g., '1.0', '1.0-2026-05-28')"
        )

    # If delegate provided, check for matching spec_version
    if delegate is not None:
        if "spec_version" not in delegate:
            raise SpecVersionValidationError(
                f"HANDBACK {task_id}: DELEGATE missing spec_version field"
            )

        delegate_version = delegate.get("spec_version")

        if spec_version != delegate_version:
            raise SpecVersionValidationError(
                f"HANDBACK {task_id}: spec_version mismatch. "
                f"DELEGATE: {delegate_version}, HANDBACK: {spec_version}. "
                f"HANDBACK must match DELEGATE version for audit trail integrity."
            )

    return True


def find_tasks_by_spec_version(
    tasks: List[Dict[str, Any]], spec_version: str
) -> List[Dict[str, Any]]:
    """
    Audit query: Find all tasks matching a specific spec_version.

    Enables audit trail queries like "Which tasks executed under spec v1.0?"

    Args:
        tasks: List of DELEGATE or HANDBACK blocks
        spec_version: Version string to search for (e.g., '1.0', '1.1-2026-05-28')

    Returns:
        List of task blocks matching the spec_version

    Examples:
        tasks = [
            {"task_id": "2026-05-30-task-001", "spec_version": "1.0"},
            {"task_id": "2026-05-30-task-002", "spec_version": "1.1"},
            {"task_id": "2026-05-30-task-003", "spec_version": "1.0"},
        ]

        results = find_tasks_by_spec_version(tasks, "1.0")
        # → [task_001, task_003]

        results = find_tasks_by_spec_version(tasks, "2.0")
        # → []
    """
    if not isinstance(tasks, list):
        return []

    matching_tasks = []
    for task in tasks:
        if isinstance(task, dict) and task.get("spec_version") == spec_version:
            matching_tasks.append(task)

    return matching_tasks


__all__ = [
    "validate_spec_version_format",
    "validate_spec_version_match",
    "find_tasks_by_spec_version",
    "SpecVersionValidationError",
]
