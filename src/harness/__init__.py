"""OpenCode harness runtime validation.

Validates OpenCode harness configuration at startup to catch configuration
errors early and provide actionable remediation steps.

See docs/HARNESS-OPENCODE-TROUBLESHOOTING.md for usage.
"""

from .harness_checker import (
    HarnessChecker,
    HarnessCheckError,
    CheckResult,
)

__all__ = [
    "HarnessChecker",
    "HarnessCheckError",
    "CheckResult",
]
