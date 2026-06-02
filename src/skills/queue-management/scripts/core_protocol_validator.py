"""
Core Protocol Validator — compatibility shim.

The canonical DELEGATE/HANDBACK validation logic now lives in the
`protocol-validation` skill:

    src/skills/protocol-validation/scripts/protocol_validation.py

This module re-exports that skill's validators so existing callers that import
from queue-management keep working unchanged. New code should prefer importing
the functional API (`validate_delegate`, `validate_handback`) directly from the
protocol-validation skill.

Provides:
- validate_delegate(delegate) -> (valid, errors)   [delegates to skill]
- validate_handback(handback) -> (valid, errors)   [delegates to skill]
- CoreProtocolValidator, ExtensionValidator         [re-exported classes]
- VALID_AGENTS, VALID_STATUSES, VALID_EFFORTS, TASK_ID_PATTERN
"""

import sys
from pathlib import Path

# Locate the protocol-validation skill's scripts directory and import the
# canonical implementation from there (single source of truth).
#   skills/queue-management/scripts/core_protocol_validator.py -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[4]
_PV_SCRIPTS = _REPO_ROOT / "src" / "skills" / "protocol-validation" / "scripts"
if str(_PV_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_PV_SCRIPTS))

from protocol_validation import (  # noqa: E402
    validate_delegate,
    validate_handback,
    CoreProtocolValidator,
    ExtensionValidator,
    VALID_AGENTS,
    VALID_STATUSES,
    VALID_EFFORTS,
    TASK_ID_PATTERN,
)

# Private helpers re-exported for backward compatibility with existing tests
# that imported them directly from this module.
from protocol_validation import _count_words, _skill_exists  # noqa: E402,F401

__all__ = [
    "validate_delegate",
    "validate_handback",
    "CoreProtocolValidator",
    "ExtensionValidator",
    "VALID_AGENTS",
    "VALID_STATUSES",
    "VALID_EFFORTS",
    "TASK_ID_PATTERN",
    "_count_words",
    "_skill_exists",
]
