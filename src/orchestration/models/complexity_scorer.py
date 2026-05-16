# -*- coding: utf-8 -*-
"""
ComplexityScorer — Analyze task attributes and produce a complexity score.

The scorer maps task attributes (token estimate, scope clarity, effort label,
task type, etc.) to a numeric complexity score (0–100) and a discrete
ComplexityLevel (trivial / low / medium / high / critical).

The score drives model selection in ModelSelector:
  trivial  (0–19)   → Haiku
  low      (20–39)  → Haiku
  medium   (40–59)  → Sonnet
  high     (60–79)  → Sonnet / Opus boundary
  critical (80–100) → Opus
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class ComplexityLevel(Enum):
    """Discrete complexity tiers mapped to model tiers."""
    TRIVIAL = "trivial"    # 0–19
    LOW = "low"            # 20–39
    MEDIUM = "medium"      # 40–59
    HIGH = "high"          # 60–79
    CRITICAL = "critical"  # 80–100


@dataclass
class TaskAttributes:
    """
    Structured representation of a task's observable attributes.

    All fields are optional so callers can supply only what they know.
    Missing fields are treated as neutral (do not increase or decrease score).
    """

    # --- Token / size signals ---
    estimated_tokens: Optional[int] = None
    """Estimated total token budget (input + output)."""

    # --- Scope / planning signals ---
    has_plan: bool = True
    """Whether a written plan is already provided (False → harder)."""

    scope_clarity: float = 1.0
    """0.0 = completely ambiguous, 1.0 = crystal-clear scope."""

    # --- Effort label from DELEGATE ---
    effort: str = "medium"
    """low | medium | high | max (from DELEGATE block)."""

    # --- Task-type signals ---
    task_type: str = "general"
    """
    Hint about the kind of work:
      routing, trivial, implementation, refactor, architecture,
      security, testing, documentation, general
    """

    # --- Structural signals ---
    num_files_affected: Optional[int] = None
    """Number of files expected to change (None = unknown)."""

    has_external_dependencies: bool = False
    """True if the task touches external APIs, DBs, or third-party services."""

    is_cross_service: bool = False
    """True if the task spans more than one service / repo."""

    # --- History / context signals ---
    prior_escalation_count: int = 0
    """How many times similar tasks have been escalated previously."""

    # --- Quality / risk signals ---
    required_quality_score: float = 85.0
    """Minimum acceptable quality score (0–100)."""

    security_sensitive: bool = False
    """True if the task involves auth, secrets, PII, or security controls."""

    # --- Free-form tags for extensibility ---
    tags: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Scoring weights (tunable constants)
# ---------------------------------------------------------------------------

_EFFORT_SCORES: Dict[str, int] = {
    "low": 10,
    "medium": 30,
    "high": 55,
    "max": 75,
}

_TASK_TYPE_SCORES: Dict[str, int] = {
    "routing": 5,
    "trivial": 5,
    "documentation": 15,
    "testing": 25,
    "general": 30,
    "implementation": 35,
    "refactor": 50,
    "architecture": 70,
    "security": 65,
}

# Token thresholds → additive score contribution
_TOKEN_THRESHOLDS: List[tuple] = [
    (0,      0),
    (2_000,  5),
    (10_000, 15),
    (25_000, 25),
    (50_000, 40),
    (100_000, 55),
]


# ---------------------------------------------------------------------------
# ComplexityScorer
# ---------------------------------------------------------------------------

class ComplexityScorer:
    """
    Score a task's complexity from its observable attributes.

    Usage::

        scorer = ComplexityScorer()
        attrs = TaskAttributes(
            estimated_tokens=5_000,
            effort="high",
            has_plan=False,
            task_type="refactor",
        )
        score, level = scorer.score(attrs)
        # score ≈ 65, level = ComplexityLevel.HIGH
    """

    def score(self, attrs: TaskAttributes) -> tuple[float, ComplexityLevel]:
        """
        Compute a numeric complexity score (0–100) and a ComplexityLevel.

        The algorithm is additive with a final clamp to [0, 100].

        Returns:
            (score: float, level: ComplexityLevel)
        """
        raw = 0.0

        # 1. Effort label (dominant signal)
        raw += _EFFORT_SCORES.get(attrs.effort.lower(), 30)

        # 2. Task type
        raw += _TASK_TYPE_SCORES.get(attrs.task_type.lower(), 30)

        # 3. Token estimate
        if attrs.estimated_tokens is not None:
            token_contrib = 0
            for threshold, contrib in _TOKEN_THRESHOLDS:
                if attrs.estimated_tokens >= threshold:
                    token_contrib = contrib
            raw += token_contrib

        # 4. Scope / planning penalties
        if not attrs.has_plan:
            raw += 10
        # scope_clarity: 1.0 = no penalty, 0.0 = +15 penalty
        raw += (1.0 - max(0.0, min(1.0, attrs.scope_clarity))) * 15

        # 5. Structural complexity
        if attrs.num_files_affected is not None:
            if attrs.num_files_affected > 10:
                raw += 15
            elif attrs.num_files_affected > 5:
                raw += 8
            elif attrs.num_files_affected > 2:
                raw += 3

        if attrs.has_external_dependencies:
            raw += 8
        if attrs.is_cross_service:
            raw += 12

        # 6. History / risk signals
        if attrs.prior_escalation_count > 0:
            raw += min(attrs.prior_escalation_count * 5, 20)

        if attrs.required_quality_score > 95:
            raw += 10
        elif attrs.required_quality_score > 90:
            raw += 5

        if attrs.security_sensitive:
            raw += 15

        # 7. Tag-based adjustments
        for tag in attrs.tags:
            tag_lower = tag.lower()
            if tag_lower in ("unscoped", "ambiguous", "unknown-scope"):
                raw += 10
            elif tag_lower in ("well-scoped", "trivial", "simple"):
                raw -= 10

        # Normalise: raw scores can exceed 100 due to additive stacking.
        # We divide by a calibration factor so that a "max" effort + complex
        # task lands near 95 and a "trivial routing" task lands near 5.
        calibration = 2.0
        score = raw / calibration

        # Clamp to [0, 100]
        score = max(0.0, min(100.0, score))

        level = self._level_from_score(score)
        return round(score, 1), level

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def score_from_dict(self, data: dict) -> tuple[float, ComplexityLevel]:
        """Score from a plain dict (e.g. parsed from a DELEGATE YAML block)."""
        attrs = TaskAttributes(
            estimated_tokens=data.get("estimated_tokens"),
            has_plan=data.get("has_plan", True),
            scope_clarity=data.get("scope_clarity", 1.0),
            effort=data.get("effort", "medium"),
            task_type=data.get("task_type", "general"),
            num_files_affected=data.get("num_files_affected"),
            has_external_dependencies=data.get("has_external_dependencies", False),
            is_cross_service=data.get("is_cross_service", False),
            prior_escalation_count=data.get("prior_escalation_count", 0),
            required_quality_score=data.get("required_quality_score", 85.0),
            security_sensitive=data.get("security_sensitive", False),
            tags=data.get("tags", []),
        )
        return self.score(attrs)

    @staticmethod
    def _level_from_score(score: float) -> ComplexityLevel:
        if score < 20:
            return ComplexityLevel.TRIVIAL
        elif score < 40:
            return ComplexityLevel.LOW
        elif score < 60:
            return ComplexityLevel.MEDIUM
        elif score < 80:
            return ComplexityLevel.HIGH
        else:
            return ComplexityLevel.CRITICAL

    @staticmethod
    def describe(attrs: TaskAttributes, score: float, level: ComplexityLevel) -> str:
        """Return a human-readable explanation of the score."""
        lines = [
            f"Complexity Score: {score:.1f}/100  →  {level.value.upper()}",
            f"  effort={attrs.effort}  task_type={attrs.task_type}",
        ]
        if attrs.estimated_tokens:
            lines.append(f"  estimated_tokens={attrs.estimated_tokens:,}")
        if not attrs.has_plan:
            lines.append("  ⚠ no plan provided (+10)")
        if attrs.scope_clarity < 0.8:
            lines.append(f"  ⚠ scope_clarity={attrs.scope_clarity:.1f} (ambiguous)")
        if attrs.security_sensitive:
            lines.append("  🔒 security-sensitive (+15)")
        if attrs.is_cross_service:
            lines.append("  🌐 cross-service (+12)")
        return "\n".join(lines)
