"""
Claude Code harness — skill rendering, agent dispatch, and observability.

Provides:
  - SkillRenderer: loads and validates skills from dist/claude/skills/
  - AgentDispatch: routes tasks to the correct agent with complexity-based
    model selection (Haiku/Sonnet/Opus tiers)
  - HANDBACKProcessor: parses and validates HANDBACK YAML blocks
  - TokenBudgetManager: per-agent token budget tracking (thread-safe)
  - TimeoutHandler: task deadline management with effort-level timeouts
  - HarnessSpanCapture: captures operation spans as JSONL for observability
  - ModelRegistry: model lifecycle registry with deprecation awareness
  - ErrorClassifier: error classification and retry/escalation policy
"""

from .skill_renderer import (
    SkillRenderer,
    SkillRenderOutput,
    CORE_SKILLS,
    REQUIRED_METADATA_FIELDS,
)
from .agent_dispatch import (
    AgentDispatch,
    DispatchResult,
    DispatchError,
    ModelTier,
    TIER_MODELS,
    EFFORT_TIER,
    AGENT_ROSTER,
    ROLE_MODEL_PINS,
    DEFAULT_MODEL,
)
from .handback_processor import (
    HANDBACKProcessor,
    HandbackValidationResult,
)
from .token_budget import (
    TokenBudgetManager,
    BudgetStatus,
    AGENT_ALLOCATIONS,
    SESSION_BUDGET_DEFAULT,
)
from .timeout_handler import (
    TimeoutHandler,
    TaskDeadline,
    EFFORT_TIMEOUTS,
)
from .span_capture import (
    HarnessSpanCapture,
    HarnessSpan,
)
from .model_registry import (
    ModelRegistry,
    MODEL_VERSIONS,
)
from .error_handler import (
    ErrorClassifier,
    ErrorType,
    RetryPolicy,
)

__all__ = [
    # Skill rendering
    "SkillRenderer",
    "SkillRenderOutput",
    "CORE_SKILLS",
    "REQUIRED_METADATA_FIELDS",
    # Agent dispatch
    "AgentDispatch",
    "DispatchResult",
    "DispatchError",
    "ModelTier",
    "TIER_MODELS",
    "EFFORT_TIER",
    "AGENT_ROSTER",
    "ROLE_MODEL_PINS",
    "DEFAULT_MODEL",
    # HANDBACK processing
    "HANDBACKProcessor",
    "HandbackValidationResult",
    # Token budgeting
    "TokenBudgetManager",
    "BudgetStatus",
    "AGENT_ALLOCATIONS",
    "SESSION_BUDGET_DEFAULT",
    # Timeout management
    "TimeoutHandler",
    "TaskDeadline",
    "EFFORT_TIMEOUTS",
    # Span capture
    "HarnessSpanCapture",
    "HarnessSpan",
    # Model registry
    "ModelRegistry",
    "MODEL_VERSIONS",
    # Error handling
    "ErrorClassifier",
    "ErrorType",
    "RetryPolicy",
]
