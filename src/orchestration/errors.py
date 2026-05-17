"""
src/orchestration/errors.py — Unified error classes for agentic-engineers.

Consolidates all custom exception types into a single module to eliminate
duplication across orchestration, agents, and skills.

Hierarchy:
    AgenticEngineersError (base)
    ├── ValidationError          — invalid DELEGATE/HANDBACK schema
    ├── RoutingError             — task routing failure
    ├── QueueError               — queue state/file operation failure
    │   └── DuplicateTaskError   — task already exists in queue
    ├── ModelError               — model resolution/invocation failure
    │   └── ModelNotFoundError   — requested model not registered
    ├── BudgetError              — token/cost budget exceeded
    ├── HandbackError            — HANDBACK validation failure
    └── ImmutableError           — attempt to mutate immutable record

Usage::

    from src.orchestration.errors import ValidationError, QueueError

    raise ValidationError("Missing required field: task_id")
    raise QueueError("Could not move task to processing")
"""


class AgenticEngineersError(Exception):
    """Base exception for all agentic-engineers errors."""


class ValidationError(AgenticEngineersError):
    """
    Raised when a DELEGATE or HANDBACK block fails schema validation.

    Replaces the duplicate ValidationError definitions in:
    - src/orchestration/agents/model_resolver.py
    - src/skills/queue-management/queue_manager.py
    - src/skills/agent-creator/__init__.py
    """


class RoutingError(AgenticEngineersError):
    """Raised when a task cannot be routed to an appropriate agent."""


class QueueError(AgenticEngineersError):
    """Raised when a queue file/state operation fails."""


class DuplicateTaskError(QueueError):
    """Raised when a task with the same task_id already exists in the queue."""


class ModelError(AgenticEngineersError):
    """Raised when model resolution or invocation fails."""


class ModelNotFoundError(ModelError):
    """Raised when the requested model is not registered in the model registry."""


class BudgetError(AgenticEngineersError):
    """Raised when a token or cost budget threshold is exceeded."""


class HandbackError(AgenticEngineersError):
    """
    Raised when a HANDBACK block fails validation.

    Replaces HandbackValidationError in src/orchestration/agents/invoke_agent.py.
    """


class ImmutableError(AgenticEngineersError):
    """
    Raised when an attempt is made to mutate an immutable record.

    Replaces ImmutableError in src/skills/spec-management/scripts/audit_logger.py.
    """


# ---------------------------------------------------------------------------
# Backward-compatibility aliases — existing code can keep its current imports
# until a future cleanup pass removes these aliases.
# ---------------------------------------------------------------------------

#: Alias: HandbackValidationError → HandbackError
HandbackValidationError = HandbackError

#: Alias: QueueManagementError → QueueError
QueueManagementError = QueueError

#: Alias: GitError (queue-management) — maps to QueueError
GitError = QueueError
