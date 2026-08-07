"""OpenCode harness configuration validation, session management, and task runner infrastructure.

Key modules:

1. config_validator: Security-critical validation of opencode.jsonc before commit,
   install, and runtime to protect the Orchestrator's primary harness from
   configuration errors.

2. harness_session_manager: Detects harness type and manages session IDs, routing
   work through canonical queue paths in ~/.agentic-engineers/{harness}/{session-id}/queue/

3. runner: Queue-based task execution engine with full lifecycle management,
   atomic state transitions, error handling, and retry logic.

4. cli_runner: Command-line interface for task submission, monitoring, and management.

5. idle_loop: Idle detection + orchestrator-scheduler invocation (Phase G-1).
   Detects idle periods and auto-polls the session queue via the
   ``orchestrator-scheduler --poll-once`` SKILL, with file-based lock
   coordination across harnesses.

See docs/OPENCODE-CONFIG-VALIDATION-GUIDE.md for config validation usage.
See docs/OPENCODE-SESSION-MANAGEMENT.md for session management usage.
See docs/OPENCODE-RUNNER-GUIDE.md for task runner usage.
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
from .idle_loop import OpenCodeIdleLoop, IdlePollResult
from .runner import (
    TaskRunner,
    TaskContext,
    TaskResult,
    TaskState,
)
from .cli_runner import CLIRunner

__all__ = [
    "OpenCodeConfigValidator",
    "ValidationError",
    "ValidationResult",
    "Severity",
    "validate_file",
    "validate_text",
    "main",
    "HarnessSessionManager",
    "OpenCodeIdleLoop",
    "IdlePollResult",
    "TaskRunner",
    "TaskContext",
    "TaskResult",
    "TaskState",
    "CLIRunner",
]
