"""
Agent Dispatch for the Claude Code harness.

Routes DELEGATE tasks to the correct specialist agent with complexity-based
model selection.  The three model tiers map directly to effort levels:

    low    -> claude-haiku-4.5   (fast, cost-effective)
    medium -> claude-sonnet-4.5  (balanced)
    high   -> claude-opus-4.8    (maximum capability)

The dispatcher also supports per-role model overrides so that pinned roles
(e.g. security-engineer always uses Opus) are not downgraded by the generic
complexity heuristic.

Usage::

    from src.harnesses.claude_code.agent_dispatch import AgentDispatch

    dispatch = AgentDispatch()
    result = dispatch.route(
        agent="senior-engineer",
        effort="high",
        task_description="Refactor the event store...",
    )
    print(result.model, result.agent)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Model tiers
# ---------------------------------------------------------------------------


class ModelTier(str, Enum):
    """Model complexity tier."""

    HAIKU = "haiku"
    SONNET = "sonnet"
    OPUS = "opus"


# Canonical model names per tier used by the Claude Code harness.
TIER_MODELS: Dict[ModelTier, str] = {
    ModelTier.HAIKU: "claude-haiku-4.5",
    ModelTier.SONNET: "claude-sonnet-4.5",
    ModelTier.OPUS: "claude-opus-4.8",
}

# Effort-level to tier mapping (complexity-based routing).
EFFORT_TIER: Dict[str, ModelTier] = {
    "low": ModelTier.HAIKU,
    "medium": ModelTier.SONNET,
    "high": ModelTier.OPUS,
    "max": ModelTier.OPUS,
}

# ---------------------------------------------------------------------------
# Agent roster and pinned model overrides
# ---------------------------------------------------------------------------

# All 8 agents supported by the framework.
AGENT_ROSTER: List[str] = [
    "orchestrator",
    "engineer",
    "senior-engineer",
    "lead-engineer",
    "quality-engineer",
    "principal-engineer",
    "security-engineer",
    "model-engineer",
]

# Per-role model pins.  When a role has a pinned model the effort-level
# heuristic is overridden.  This ensures security-critical roles always
# get the appropriate capability level.
ROLE_MODEL_PINS: Dict[str, str] = {
    "orchestrator": "claude-haiku-4.5",
    "engineer": "claude-haiku-4.5",
    "security-engineer": "claude-opus-4.8",
    "principal-engineer": "claude-opus-4.8",
}

# Default model used when no pin and no effort hint is provided.
DEFAULT_MODEL = "claude-haiku-4.5"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class DispatchResult:
    """Result of an agent dispatch decision."""

    agent: str
    model: str
    tier: ModelTier
    effort: Optional[str]
    pinned: bool  # True when model was set by ROLE_MODEL_PINS
    explanation: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Always True for a completed dispatch (agent was in roster)."""
        return True


@dataclass
class DispatchError:
    """Returned when routing cannot complete."""

    agent: str
    error: str
    success: bool = False


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class AgentDispatch:
    """Route DELEGATE tasks to agents with complexity-based model selection.

    Parameters
    ----------
    role_pins:
        Override the default :data:`ROLE_MODEL_PINS` table.
    tier_models:
        Override the default :data:`TIER_MODELS` table.
    effort_tiers:
        Override the default :data:`EFFORT_TIER` table.
    """

    def __init__(
        self,
        role_pins: Optional[Dict[str, str]] = None,
        tier_models: Optional[Dict[ModelTier, str]] = None,
        effort_tiers: Optional[Dict[str, ModelTier]] = None,
    ) -> None:
        self._role_pins: Dict[str, str] = (
            dict(ROLE_MODEL_PINS) if role_pins is None else role_pins
        )
        self._tier_models: Dict[ModelTier, str] = (
            dict(TIER_MODELS) if tier_models is None else tier_models
        )
        self._effort_tiers: Dict[str, ModelTier] = (
            dict(EFFORT_TIER) if effort_tiers is None else effort_tiers
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def route(
        self,
        agent: str,
        effort: Optional[str] = None,
        task_description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DispatchResult:
        """Resolve which model to use for an agent/effort combination.

        Args:
            agent: Agent name (must be in :data:`AGENT_ROSTER`).
            effort: Effort level — ``low``, ``medium``, ``high``, or ``max``.
            task_description: Optional human-readable task description (used
                in the explanation string only).
            metadata: Arbitrary key/value context attached to the result.

        Returns:
            :class:`DispatchResult` with model, tier, and routing explanation.

        Raises:
            ValueError: If ``agent`` is not in the roster.
        """
        if agent not in AGENT_ROSTER:
            raise ValueError(
                f"Unknown agent '{agent}'. "
                f"Valid agents: {', '.join(sorted(AGENT_ROSTER))}"
            )

        pinned_model = self._role_pins.get(agent)

        if pinned_model is not None:
            # Role-level pin overrides effort-level routing.
            tier = self._model_to_tier(pinned_model)
            explanation = (
                f"Agent '{agent}' has a pinned model ({pinned_model}); "
                "effort-level routing bypassed."
            )
            return DispatchResult(
                agent=agent,
                model=pinned_model,
                tier=tier,
                effort=effort,
                pinned=True,
                explanation=explanation,
                metadata=metadata or {},
            )

        # Complexity-based routing.
        effort_key = (effort or "low").lower()
        tier = self._effort_tiers.get(effort_key, ModelTier.HAIKU)
        model = self._tier_models[tier]
        explanation = (
            f"Agent '{agent}' + effort '{effort_key}' "
            f"-> tier '{tier.value}' -> model '{model}'."
        )
        if task_description:
            explanation += f" Task: {task_description[:80]}"

        return DispatchResult(
            agent=agent,
            model=model,
            tier=tier,
            effort=effort,
            pinned=False,
            explanation=explanation,
            metadata=metadata or {},
        )

    def route_batch(
        self, tasks: List[Dict[str, Any]]
    ) -> List[DispatchResult]:
        """Route multiple tasks.

        Each task dict must contain ``agent`` and optionally ``effort`` and
        ``task_description``.

        Returns:
            List of :class:`DispatchResult` in the same order as ``tasks``.
        """
        results = []
        for task in tasks:
            result = self.route(
                agent=task["agent"],
                effort=task.get("effort"),
                task_description=task.get("task_description", ""),
                metadata=task.get("metadata"),
            )
            results.append(result)
        return results

    def available_agents(self) -> List[str]:
        """Return the sorted list of available agent names."""
        return sorted(AGENT_ROSTER)

    def model_for_effort(self, effort: str) -> str:
        """Return the model name for a given effort level (no role pinning).

        Args:
            effort: ``low``, ``medium``, ``high``, or ``max``.

        Returns:
            Model name string.
        """
        tier = self._effort_tiers.get(effort.lower(), ModelTier.HAIKU)
        return self._tier_models[tier]

    def is_agent_available(self, agent: str) -> bool:
        """Return True if ``agent`` is in the roster."""
        return agent in AGENT_ROSTER

    def get_agent_model(self, agent: str, effort: Optional[str] = None) -> str:
        """Convenience: return just the model string for an agent/effort pair."""
        result = self.route(agent=agent, effort=effort)
        return result.model

    # ------------------------------------------------------------------
    # Delegation success rate measurement
    # ------------------------------------------------------------------

    def measure_delegation_success(
        self, test_scenarios: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Run representative delegation scenarios and measure success rate.

        Args:
            test_scenarios: List of scenario dicts with ``agent`` and optional
                ``effort`` keys.  Defaults to a built-in set covering all 8
                agents.

        Returns:
            Dict with ``total``, ``passed``, ``failed``, and
            ``success_rate`` keys.
        """
        if test_scenarios is None:
            test_scenarios = self._default_scenarios()

        passed = 0
        failed = 0
        failures: List[str] = []

        for scenario in test_scenarios:
            agent = scenario.get("agent", "")
            effort = scenario.get("effort")
            try:
                result = self.route(agent=agent, effort=effort)
                if result.success and result.model:
                    passed += 1
                else:
                    failed += 1
                    failures.append(f"{agent}/{effort}: no model resolved")
            except Exception as exc:
                failed += 1
                failures.append(f"{agent}/{effort}: {exc}")

        total = passed + failed
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "success_rate": passed / total if total else 0.0,
            "failures": failures,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _model_to_tier(model: str) -> ModelTier:
        """Infer the ModelTier from a model name string."""
        lower = model.lower()
        if "haiku" in lower:
            return ModelTier.HAIKU
        if "sonnet" in lower:
            return ModelTier.SONNET
        return ModelTier.OPUS

    @staticmethod
    def _default_scenarios() -> List[Dict[str, Any]]:
        """Return a comprehensive set of test scenarios covering all agents."""
        return [
            # Orchestrator — always Haiku (pinned)
            {"agent": "orchestrator", "effort": "low"},
            {"agent": "orchestrator", "effort": "high"},
            # Engineer — always Haiku (pinned)
            {"agent": "engineer", "effort": "low"},
            {"agent": "engineer", "effort": "high"},
            # Senior engineer — effort-based
            {"agent": "senior-engineer", "effort": "low"},
            {"agent": "senior-engineer", "effort": "medium"},
            {"agent": "senior-engineer", "effort": "high"},
            # Lead engineer — effort-based
            {"agent": "lead-engineer", "effort": "low"},
            {"agent": "lead-engineer", "effort": "high"},
            # Quality engineer — effort-based
            {"agent": "quality-engineer", "effort": "medium"},
            # Principal engineer — always Opus (pinned)
            {"agent": "principal-engineer", "effort": "high"},
            # Security engineer — always Opus (pinned)
            {"agent": "security-engineer", "effort": "high"},
            {"agent": "security-engineer", "effort": "low"},
            # Model engineer — effort-based
            {"agent": "model-engineer", "effort": "medium"},
            {"agent": "model-engineer", "effort": "high"},
        ]
