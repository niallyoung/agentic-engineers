# -*- coding: utf-8 -*-
"""
RecommendationsEngine — Daily analysis and model-change recommendations.

Aggregates:
  - CostQualityAnalyzer efficiency reports
  - ModelSelector routing decisions
  - Historical escalation patterns

Produces:
  - Ranked list of Recommendation objects
  - Confidence scores (0.0–1.0)
  - Proposed A/B test designs
  - Daily summary report

Recommendation types:
  DOWNGRADE  — switch expensive model to cheaper one (over-provisioned)
  UPGRADE    — switch cheap model to better one (under-provisioned / quality issues)
  REROUTE    — change role assignment (escalation rate too high)
  AB_TEST    — propose a controlled experiment before committing
  MONITOR    — flag for observation (not yet actionable)
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .cost_quality_analyzer import CostQualityAnalyzer, EfficiencyReport, COST_TARGET_PER_QUALITY_POINT
from .model_selector import ModelTier, MODEL_COST_MULTIPLIERS, MODEL_QUALITY_BASELINES
from .complexity_scorer import ComplexityLevel


# ---------------------------------------------------------------------------
# Recommendation types
# ---------------------------------------------------------------------------

class RecommendationType(Enum):
    DOWNGRADE = "downgrade"
    UPGRADE = "upgrade"
    REROUTE = "reroute"
    AB_TEST = "ab_test"
    MONITOR = "monitor"


@dataclass
class Recommendation:
    """A single actionable recommendation."""
    type: RecommendationType
    role: str
    current_model: str
    proposed_model: Optional[str]
    rationale: str
    confidence: float          # 0.0–1.0
    estimated_cost_delta_pct: float  # negative = savings
    estimated_quality_delta_pct: float
    priority: int              # 1 (highest) – 5 (lowest)
    ab_test_proposal: Optional[dict] = None

    def __str__(self) -> str:
        arrow = f"{self.current_model} → {self.proposed_model}" if self.proposed_model else self.current_model
        return (
            f"[{self.type.value.upper()}] {self.role}: {arrow}  "
            f"confidence={self.confidence:.0%}  "
            f"cost_delta={self.estimated_cost_delta_pct:+.1f}%  "
            f"quality_delta={self.estimated_quality_delta_pct:+.1f}%  "
            f"priority={self.priority}\n"
            f"  Rationale: {self.rationale}"
        )


# ---------------------------------------------------------------------------
# RecommendationsEngine
# ---------------------------------------------------------------------------

class RecommendationsEngine:
    """
    Generate model-selection recommendations from efficiency data.

    Usage::

        engine = RecommendationsEngine()
        engine.load_metrics(metrics_list)
        report = engine.generate_daily_report()
        for rec in report["recommendations"]:
            print(rec)
    """

    # Thresholds
    HIGH_ESCALATION_RATE: float = 0.15
    POOR_QUALITY_THRESHOLD: float = 80.0
    OUTLIER_TOKEN_MULTIPLIER: float = 3.0

    def __init__(self):
        self._analyzer = CostQualityAnalyzer()
        self._metrics: List[dict] = []

    def load_metrics(self, metrics: List[dict]) -> None:
        self._metrics = list(metrics)
        self._analyzer.load(metrics)

    # ------------------------------------------------------------------
    # Primary API
    # ------------------------------------------------------------------

    def generate_daily_report(self, date: str = None) -> dict:
        """
        Run full daily analysis and return a structured report dict.

        Returns::
            {
                "date": str,
                "efficiency_report": EfficiencyReport,
                "recommendations": List[Recommendation],
                "ab_test_proposals": List[dict],
                "summary": str,
            }
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        efficiency = self._analyzer.analyze(date=date)
        recommendations = self._generate_recommendations(efficiency)
        ab_proposals = [r.ab_test_proposal for r in recommendations if r.ab_test_proposal]

        summary = self._format_summary(date, efficiency, recommendations)

        return {
            "date": date,
            "efficiency_report": efficiency,
            "recommendations": recommendations,
            "ab_test_proposals": ab_proposals,
            "summary": summary,
        }

    def recommend_for_role(self, role: str, current_model: str, metrics: List[dict]) -> List[Recommendation]:
        """Generate targeted recommendations for a specific role."""
        self._analyzer.load(metrics)
        efficiency = self._analyzer.analyze()
        role_stats = efficiency.role_stats.get(role)
        if not role_stats:
            return []
        return self._analyze_role(role_stats, efficiency)

    # ------------------------------------------------------------------
    # Recommendation generation
    # ------------------------------------------------------------------

    def _generate_recommendations(self, efficiency: EfficiencyReport) -> List[Recommendation]:
        recs: List[Recommendation] = []

        for role, stats in efficiency.role_stats.items():
            recs.extend(self._analyze_role(stats, efficiency))

        # Sort by priority then confidence
        recs.sort(key=lambda r: (r.priority, -r.confidence))
        return recs

    def _analyze_role(self, stats, efficiency: EfficiencyReport) -> List[Recommendation]:
        recs = []
        role = stats.role
        model = stats.model

        # 1. Over-provisioned: expensive model used for low-complexity tasks
        if stats.over_provisioned_count > 0:
            cheaper = self._cheaper_model(model)
            if cheaper:
                cost_savings = (
                    1.0 - MODEL_COST_MULTIPLIERS.get(ModelTier(cheaper), 1.0)
                    / MODEL_COST_MULTIPLIERS.get(ModelTier(model), 1.0)
                ) * 100
                recs.append(Recommendation(
                    type=RecommendationType.DOWNGRADE,
                    role=role,
                    current_model=model,
                    proposed_model=cheaper,
                    rationale=(
                        f"{stats.over_provisioned_count} tasks were over-provisioned "
                        f"(cost/quality ${stats.cost_per_quality_point:.4f} vs target "
                        f"${COST_TARGET_PER_QUALITY_POINT:.4f}). "
                        f"Downgrade to {cheaper} for low-complexity tasks."
                    ),
                    confidence=min(0.95, 0.6 + stats.over_provisioned_count * 0.02),
                    estimated_cost_delta_pct=-cost_savings,
                    estimated_quality_delta_pct=-2.0,  # small quality trade-off
                    priority=2,
                    ab_test_proposal=self._propose_ab_test(
                        role, model, cheaper,
                        f"Downgrade {role} from {model} to {cheaper} for low-complexity tasks"
                    ),
                ))

        # 2. Under-provisioned: high escalation or low quality
        if stats.escalation_rate > self.HIGH_ESCALATION_RATE or stats.avg_quality < self.POOR_QUALITY_THRESHOLD:
            better = self._better_model(model)
            if better:
                quality_gain = (
                    MODEL_QUALITY_BASELINES.get(ModelTier(better), 93.0)
                    - MODEL_QUALITY_BASELINES.get(ModelTier(model), 82.0)
                )
                cost_increase = (
                    MODEL_COST_MULTIPLIERS.get(ModelTier(better), 1.0)
                    / MODEL_COST_MULTIPLIERS.get(ModelTier(model), 1.0)
                    - 1.0
                ) * 100
                recs.append(Recommendation(
                    type=RecommendationType.UPGRADE,
                    role=role,
                    current_model=model,
                    proposed_model=better,
                    rationale=(
                        f"{role} shows escalation_rate={stats.escalation_rate:.0%} "
                        f"and avg_quality={stats.avg_quality:.1f}%. "
                        f"Upgrade to {better} to reduce escalations and improve quality."
                    ),
                    confidence=min(0.9, 0.5 + stats.escalation_rate * 2),
                    estimated_cost_delta_pct=cost_increase,
                    estimated_quality_delta_pct=quality_gain,
                    priority=1,
                    ab_test_proposal=self._propose_ab_test(
                        role, model, better,
                        f"Upgrade {role} from {model} to {better} to reduce escalations"
                    ),
                ))

        # 3. Monitor: fair efficiency with moderate escalation
        if stats.efficiency == "fair" and stats.escalation_rate > 0.05:
            recs.append(Recommendation(
                type=RecommendationType.MONITOR,
                role=role,
                current_model=model,
                proposed_model=None,
                rationale=(
                    f"{role} has fair efficiency and {stats.escalation_rate:.0%} escalation rate. "
                    "Monitor for 3 more days before acting."
                ),
                confidence=0.4,
                estimated_cost_delta_pct=0.0,
                estimated_quality_delta_pct=0.0,
                priority=4,
            ))

        # 4. Outlier flag
        if stats.over_provisioned_count + stats.under_provisioned_count > stats.task_count * 0.3:
            recs.append(Recommendation(
                type=RecommendationType.AB_TEST,
                role=role,
                current_model=model,
                proposed_model=None,
                rationale=(
                    f"{role} has {stats.over_provisioned_count + stats.under_provisioned_count} "
                    f"mis-provisioned tasks out of {stats.task_count} "
                    f"({(stats.over_provisioned_count + stats.under_provisioned_count)/stats.task_count:.0%}). "
                    "Run A/B test to validate complexity-based routing."
                ),
                confidence=0.7,
                estimated_cost_delta_pct=-10.0,
                estimated_quality_delta_pct=0.0,
                priority=3,
                ab_test_proposal=self._propose_ab_test(
                    role, model, model,
                    f"Validate complexity-based routing for {role}"
                ),
            ))

        return recs

    # ------------------------------------------------------------------
    # A/B test proposal builder
    # ------------------------------------------------------------------

    @staticmethod
    def _propose_ab_test(role: str, control_model: str, variant_model: str, hypothesis: str) -> dict:
        return {
            "name": f"{role.lower().replace(' ', '-')}-{control_model}-vs-{variant_model}",
            "hypothesis": hypothesis,
            "control": {"role": role, "model": control_model},
            "variant": {"role": role, "model": variant_model},
            "duration_days": 7,
            "traffic_split": 0.5,
            "success_criteria": {
                "min_quality_pct": 90.0,
                "max_cost_increase_pct": 5.0,
                "significance_threshold": 0.05,
            },
        }

    # ------------------------------------------------------------------
    # Model tier helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cheaper_model(model: str) -> Optional[str]:
        tier_order = [ModelTier.HAIKU, ModelTier.SONNET, ModelTier.OPUS]
        for i, tier in enumerate(tier_order):
            if tier.value in model.lower() or model.lower() in tier.value:
                if i > 0:
                    return tier_order[i - 1].value
        return None

    @staticmethod
    def _better_model(model: str) -> Optional[str]:
        tier_order = [ModelTier.HAIKU, ModelTier.SONNET, ModelTier.OPUS]
        for i, tier in enumerate(tier_order):
            if tier.value in model.lower() or model.lower() in tier.value:
                if i < len(tier_order) - 1:
                    return tier_order[i + 1].value
        return None

    # ------------------------------------------------------------------
    # Report formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _format_summary(
        date: str,
        efficiency: EfficiencyReport,
        recommendations: List[Recommendation],
    ) -> str:
        lines = [
            f"=== Model Selection Recommendations ({date}) ===",
            "",
            efficiency.summary(),
            "",
            f"Recommendations ({len(recommendations)} total):",
        ]
        for rec in recommendations[:10]:  # Top 10
            lines.append(f"\n{rec}")

        high_priority = [r for r in recommendations if r.priority <= 2]
        if high_priority:
            lines.append(f"\n⚡ {len(high_priority)} high-priority action(s) require attention")

        return "\n".join(lines)
