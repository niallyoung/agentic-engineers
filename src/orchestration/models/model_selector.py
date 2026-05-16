# -*- coding: utf-8 -*-
"""
ModelSelector — Route tasks to the optimal model tier based on complexity.

Decision tree:
  ComplexityLevel.TRIVIAL  → Haiku   (0.33× cost)
  ComplexityLevel.LOW      → Haiku   (0.33× cost)
  ComplexityLevel.MEDIUM   → Sonnet  (1× cost)
  ComplexityLevel.HIGH     → Sonnet  (default) or Opus if quality > 95
  ComplexityLevel.CRITICAL → Opus    (3× cost)

Override rules (applied after base decision):
  - security_sensitive → Opus minimum
  - is_cross_service   → Sonnet minimum
  - required_quality_score > 95 → upgrade one tier

Available models (relative cost multipliers vs Sonnet = 1×):
  haiku-4-5   0.33×
  sonnet-4-6  1.00×
  opus-4-7    3.00×
  gpt-5-4     1.00×  (GPT-5.4 parity)
  gpt-5-5     7.50×  (GPT-5.5 premium)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from .complexity_scorer import ComplexityLevel, ComplexityScorer, TaskAttributes


# ---------------------------------------------------------------------------
# Model catalogue
# ---------------------------------------------------------------------------

class ModelTier(Enum):
    """Available model tiers with relative cost multipliers."""
    HAIKU = "haiku-4-5"
    SONNET = "sonnet-4-6"
    OPUS = "opus-4-7"
    GPT_5_4 = "gpt-5-4"
    GPT_5_5 = "gpt-5-5"


# Cost multipliers relative to Sonnet = 1.0
MODEL_COST_MULTIPLIERS: Dict[ModelTier, float] = {
    ModelTier.HAIKU:   0.33,
    ModelTier.SONNET:  1.00,
    ModelTier.OPUS:    3.00,
    ModelTier.GPT_5_4: 1.00,
    ModelTier.GPT_5_5: 7.50,
}

# Quality baselines (0–100) based on Phase 2 observations
MODEL_QUALITY_BASELINES: Dict[ModelTier, float] = {
    ModelTier.HAIKU:   82.0,
    ModelTier.SONNET:  93.0,
    ModelTier.OPUS:    97.0,
    ModelTier.GPT_5_4: 92.0,
    ModelTier.GPT_5_5: 98.0,
}

# Tier ordering for upgrade/downgrade logic
_TIER_ORDER = [
    ModelTier.HAIKU,
    ModelTier.SONNET,
    ModelTier.OPUS,
]


# ---------------------------------------------------------------------------
# RoutingDecision
# ---------------------------------------------------------------------------

@dataclass
class RoutingDecision:
    """Result of a model selection decision."""

    model: ModelTier
    """Selected model tier."""

    complexity_score: float
    """Numeric complexity score (0–100)."""

    complexity_level: ComplexityLevel
    """Discrete complexity level."""

    cost_multiplier: float
    """Relative cost vs Sonnet (1.0)."""

    quality_baseline: float
    """Expected quality score for this model."""

    rationale: str
    """Human-readable explanation of the decision."""

    override_applied: bool = False
    """True if a policy override changed the base decision."""

    override_reason: str = ""
    """Description of the override that was applied."""

    @property
    def model_id(self) -> str:
        return self.model.value

    def __str__(self) -> str:
        lines = [
            f"Model: {self.model_id}  (complexity {self.complexity_score:.1f} → {self.complexity_level.value})",
            f"  Cost multiplier: {self.cost_multiplier:.2f}×",
            f"  Quality baseline: {self.quality_baseline:.1f}%",
            f"  Rationale: {self.rationale}",
        ]
        if self.override_applied:
            lines.append(f"  Override: {self.override_reason}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# ModelSelector
# ---------------------------------------------------------------------------

class ModelSelector:
    """
    Route a task to the optimal model tier.

    Usage::

        selector = ModelSelector()
        attrs = TaskAttributes(effort="high", task_type="refactor", has_plan=False)
        decision = selector.select(attrs)
        print(decision.model_id)  # "sonnet-4-6" or "opus-4-7"

    The selector is intentionally stateless — it does not load metrics.
    For data-driven routing, combine with RecommendationsEngine.
    """

    def __init__(self, scorer: Optional[ComplexityScorer] = None):
        self._scorer = scorer or ComplexityScorer()

    # ------------------------------------------------------------------
    # Primary API
    # ------------------------------------------------------------------

    def select(self, attrs: TaskAttributes) -> RoutingDecision:
        """Select the optimal model for the given task attributes."""
        score, level = self._scorer.score(attrs)
        base_model = self._base_model(level)
        rationale = self._base_rationale(level, score)

        # Apply override rules
        final_model, override_applied, override_reason = self._apply_overrides(
            base_model, attrs
        )

        return RoutingDecision(
            model=final_model,
            complexity_score=score,
            complexity_level=level,
            cost_multiplier=MODEL_COST_MULTIPLIERS[final_model],
            quality_baseline=MODEL_QUALITY_BASELINES[final_model],
            rationale=rationale,
            override_applied=override_applied,
            override_reason=override_reason,
        )

    def select_from_dict(self, data: dict) -> RoutingDecision:
        """Select from a plain dict (e.g. parsed DELEGATE YAML)."""
        score, level = self._scorer.score_from_dict(data)
        attrs = TaskAttributes(
            effort=data.get("effort", "medium"),
            task_type=data.get("task_type", "general"),
            has_plan=data.get("has_plan", True),
            scope_clarity=data.get("scope_clarity", 1.0),
            estimated_tokens=data.get("estimated_tokens"),
            num_files_affected=data.get("num_files_affected"),
            has_external_dependencies=data.get("has_external_dependencies", False),
            is_cross_service=data.get("is_cross_service", False),
            prior_escalation_count=data.get("prior_escalation_count", 0),
            required_quality_score=data.get("required_quality_score", 85.0),
            security_sensitive=data.get("security_sensitive", False),
            tags=data.get("tags", []),
        )
        return self.select(attrs)

    # ------------------------------------------------------------------
    # Decision tree helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _base_model(level: ComplexityLevel) -> ModelTier:
        """Map complexity level to base model tier (no overrides)."""
        mapping = {
            ComplexityLevel.TRIVIAL:  ModelTier.HAIKU,
            ComplexityLevel.LOW:      ModelTier.HAIKU,
            ComplexityLevel.MEDIUM:   ModelTier.SONNET,
            ComplexityLevel.HIGH:     ModelTier.SONNET,
            ComplexityLevel.CRITICAL: ModelTier.OPUS,
        }
        return mapping[level]

    @staticmethod
    def _base_rationale(level: ComplexityLevel, score: float) -> str:
        rationales = {
            ComplexityLevel.TRIVIAL:  f"Trivial task (score {score:.1f}) — Haiku is sufficient and cost-optimal",
            ComplexityLevel.LOW:      f"Low-complexity task (score {score:.1f}) — Haiku handles well at 0.33× cost",
            ComplexityLevel.MEDIUM:   f"Medium-complexity task (score {score:.1f}) — Sonnet provides quality/cost balance",
            ComplexityLevel.HIGH:     f"High-complexity task (score {score:.1f}) — Sonnet with careful planning; Opus if quality >95 required",
            ComplexityLevel.CRITICAL: f"Critical-complexity task (score {score:.1f}) — Opus required for architectural depth",
        }
        return rationales[level]

    @staticmethod
    def _apply_overrides(
        model: ModelTier, attrs: TaskAttributes
    ) -> tuple[ModelTier, bool, str]:
        """Apply policy overrides. Returns (final_model, override_applied, reason)."""
        reasons = []
        final = model

        # Security-sensitive → Opus minimum
        if attrs.security_sensitive and _TIER_ORDER.index(final) < _TIER_ORDER.index(ModelTier.OPUS):
            final = ModelTier.OPUS
            reasons.append("security-sensitive task requires Opus minimum")

        # Cross-service → Sonnet minimum
        if attrs.is_cross_service and final == ModelTier.HAIKU:
            final = ModelTier.SONNET
            reasons.append("cross-service task requires Sonnet minimum")

        # High quality requirement → upgrade one tier
        if attrs.required_quality_score > 95 and final in (ModelTier.HAIKU, ModelTier.SONNET):
            idx = _TIER_ORDER.index(final)
            if idx + 1 < len(_TIER_ORDER):
                final = _TIER_ORDER[idx + 1]
                reasons.append(f"required_quality_score={attrs.required_quality_score:.0f} → upgrade one tier")

        override_applied = final != model
        return final, override_applied, "; ".join(reasons)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def estimate_cost(self, attrs: TaskAttributes, base_cost_per_token: float = 0.0003) -> float:
        """
        Estimate task cost in USD given a base cost per token (Sonnet rate).

        Args:
            attrs: Task attributes (must include estimated_tokens).
            base_cost_per_token: Cost per token for Sonnet (default $0.0003).

        Returns:
            Estimated cost in USD, or 0.0 if estimated_tokens is None.
        """
        if attrs.estimated_tokens is None:
            return 0.0
        decision = self.select(attrs)
        return attrs.estimated_tokens * base_cost_per_token * decision.cost_multiplier
