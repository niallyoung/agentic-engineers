"""OpenCode harness configuration validation package.

Security-critical: validates opencode.jsonc before commit, install, and runtime
to protect the Orchestrator's primary harness from configuration errors.

See docs/OPENCODE-CONFIG-VALIDATION-GUIDE.md for usage.
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

__all__ = [
    "OpenCodeConfigValidator",
    "ValidationError",
    "ValidationResult",
    "Severity",
    "validate_file",
    "validate_text",
    "main",
]
