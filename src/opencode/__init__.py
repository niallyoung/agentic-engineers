"""OpenCode harness configuration validation and session management.

Two key modules:

1. config_validator: Security-critical validation of opencode.jsonc before commit,
   install, and runtime to protect the Orchestrator's primary harness from
   configuration errors.

2. harness_session_manager: Detects harness type and manages session IDs, routing
   work through canonical queue paths in ~/.agentic-engineers/{session-id}/{harness}/queue/

See docs/OPENCODE-CONFIG-VALIDATION-GUIDE.md for config validation usage.
See docs/OPENCODE-SESSION-MANAGEMENT.md for session management usage.
"""

from .config_validator import (
    OpenCodeConfigValidator,
    ValidationError,
    ValidationResult,
    Severity,
    validate_file,
    validate_text,
    main,
)
from .harness_session_manager import HarnessSessionManager

__all__ = [
    "OpenCodeConfigValidator",
    "ValidationError",
    "ValidationResult",
    "Severity",
    "validate_file",
    "validate_text",
    "main",
    "HarnessSessionManager",
]
