"""OpenCode harness session management and task runner infrastructure.

Key modules:

1. harness_session_manager: Detects harness type and manages session IDs, routing
   work through canonical queue paths in ~/.agentic-engineers/{harness}/{session-id}/queue/

2. runner: Queue-based task execution engine with full lifecycle management,
   atomic state transitions, error handling, and retry logic.

3. cli_runner: Command-line interface for task submission, monitoring, and management.

NOTE (SPEC-2026-005 framework slimdown, WP-0): config_validator (formerly a
module here) has moved to scripts/validate_opencode_config.py — it was a
pure-stdlib file with no dependency on the rest of this package, rescued
ahead of this src/opencode/ tree being deleted in a later WP. Import it as
``from scripts.validate_opencode_config import validate_file`` etc. going
forward. See docs/OPENCODE-CONFIG-VALIDATION-GUIDE.md for usage.

See docs/OPENCODE-SESSION-MANAGEMENT.md for session management usage.
See docs/OPENCODE-RUNNER-GUIDE.md for task runner usage.
"""

from .harness_session_manager import HarnessSessionManager
from .runner import (
    TaskRunner,
    TaskContext,
    TaskResult,
    TaskState,
)
from .cli_runner import CLIRunner

__all__ = [
    "HarnessSessionManager",
    "TaskRunner",
    "TaskContext",
    "TaskResult",
    "TaskState",
    "CLIRunner",
]
