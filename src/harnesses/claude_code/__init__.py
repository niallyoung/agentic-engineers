"""
Claude Code harness — skill rendering and agent dispatch.

Provides:
  - SkillRenderer: loads and validates skills from dist/claude/skills/
  - AgentDispatch: routes tasks to the correct agent with complexity-based
    model selection (Haiku/Sonnet/Opus tiers)
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

__all__ = [
    "SkillRenderer",
    "SkillRenderOutput",
    "CORE_SKILLS",
    "REQUIRED_METADATA_FIELDS",
    "AgentDispatch",
    "DispatchResult",
    "DispatchError",
    "ModelTier",
    "TIER_MODELS",
    "EFFORT_TIER",
    "AGENT_ROSTER",
    "ROLE_MODEL_PINS",
    "DEFAULT_MODEL",
]
