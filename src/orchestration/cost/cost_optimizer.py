# -*- coding: utf-8 -*-
"""
CostOptimizer — Analyze historical data and generate cost optimization recommendations.

Capabilities:
  - Identify over-provisioned tasks (expensive model for simple work)
  - Identify parallelization opportunities
  - Identify caching opportunities (repeated similar tasks)
  - Score opportunities by impact and risk
  - Support A/B test proposals
  - Track optimization effectiveness over time

Usage::

    optimizer = CostOptimizer()
    optimizer.load(metrics)
    opportunities = optimizer.analyze()
    for opp in opportunities:
        print(opp.description, opp.estimated_savings_pct)
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime


# ---------------------------------------------------------------------------
# Opportunity types
# ---------------------------------------------------------------------------

class OpportunityType(Enum):
    MODEL_DOWNGRADE = "model_downgrade"       # Use cheaper model
    MODEL_UPGRADE = "model_upgrade"           # Use better model (reduce re-runs)
    PARALLELIZATION = "parallelization"       # Run tasks concurrently
    CACHING = "caching"                       # Cache repeated task results
    EFFORT_REDUCTION = "effort_reduction"     # Lower effort level
    BATCH_PROCESSING = "batch_processing"     # Batch similar tasks


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class OptimizationOpportunity:
    """A single cost optimization opportunity."""
    type: OpportunityType
    role: str
    description: str
    estimated_savings_pct: float    # Positive = cost reduction
    estimated_quality_impact: float  # Negative = quality loss
    confidence: float               # 0.0–1.0
    risk: RiskLevel
    priority: int                   # 1 (highest) – 5 (lowest)
    affected_tasks: int
    ab_test_recommended: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def impact_score(self) -> float:
        """Composite score: savings weighted by confidence and inverse risk."""
        risk_penalty = {"low": 1.0, "medium": 0.8, "high": 0.5}[self.risk.value]
        return self.estimated_savings_pct * self.confidence * risk_penalty

    def __str__(self) -> str:
        return (
            f"[{self.type.value}] {self.role}: {self.description}\n"
            f"  Savings: {self.estimated_savings_pct:.1f}%  "
            f"Quality impact: {self.estimated_quality_impact:+.1f}%  "
            f"Confidence: {self.confidence:.0%}  "
            f"Risk: {self.risk.value}  "
            f"Priority: {self.priority}"
        )


@dataclass
class OptimizationReport:
    """Full optimization analysis report."""
    date: str
    total_tasks_analyzed: int
    total_cost_analyzed: float
    opportunities: List[OptimizationOpportunity]
    estimated_total_savings_pct: float
    quality_maintained: bool  # True if savings don't compromise quality threshold

    def summary(self) -> str:
        lines = [
            f"=== Cost Optimization Report ({self.date}) ===",
            f"Tasks analyzed: {self.total_tasks_analyzed}  "
            f"Total cost: ${self.total_cost_analyzed:.4f}",
            f"Estimated savings: {self.estimated_total_savings_pct:.1f}%  "
            f"Quality maintained: {'✓' if self.quality_maintained else '✗'}",
            "",
            f"Opportunities ({len(self.opportunities)}):",
        ]
        for opp in sorted(self.opportunities, key=lambda o: o.priority):
            lines.append(f"\n{opp}")
        return "\n".join(lines)

    def high_priority(self) -> List[OptimizationOpportunity]:
        return [o for o in self.opportunities if o.priority <= 2]

    def by_type(self, opp_type: OpportunityType) -> List[OptimizationOpportunity]:
        return [o for o in self.opportunities if o.type == opp_type]


# ---------------------------------------------------------------------------
# CostOptimizer
# ---------------------------------------------------------------------------

class CostOptimizer:
    """
    Analyze historical task metrics and generate cost optimization opportunities.

    Metrics record schema:
        {
            "role": str,
            "model": str,
            "tokens_in": int,
            "tokens_out": int,
            "cost": float,
            "quality_score": float,
            "complexity_score": float,
            "task_type": str,
            "duration_ms": int,
            "cache_hit": bool,
            "escalated": bool,
            "task_id": str,
        }
    """

    # Thresholds
    OVER_PROVISION_COMPLEXITY_THRESHOLD: float = 40.0  # Opus for complexity < 40
    SONNET_OVER_PROVISION_THRESHOLD: float = 20.0      # Sonnet for complexity < 20
    HIGH_ESCALATION_RATE: float = 0.15
    CACHE_SIMILARITY_THRESHOLD: float = 0.8            # task_type repetition rate
    PARALLELIZATION_MIN_TASKS: int = 3                 # Min tasks to suggest parallel
    QUALITY_FLOOR: float = 90.0                        # Minimum acceptable quality

    def __init__(self, quality_floor: float = QUALITY_FLOOR):
        self._metrics: List[dict] = []
        self._quality_floor = quality_floor
        self._effectiveness_history: List[dict] = []

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load(self, metrics: List[dict]) -> None:
        """Load task metrics for analysis."""
        self._metrics = list(metrics)

    # ------------------------------------------------------------------
    # Primary API
    # ------------------------------------------------------------------

    def analyze(self, date: Optional[str] = None) -> OptimizationReport:
        """Run full optimization analysis on loaded metrics."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        if not self._metrics:
            return OptimizationReport(
                date=date,
                total_tasks_analyzed=0,
                total_cost_analyzed=0.0,
                opportunities=[],
                estimated_total_savings_pct=0.0,
                quality_maintained=True,
            )

        opportunities: List[OptimizationOpportunity] = []

        opportunities.extend(self._find_model_downgrade_opportunities())
        opportunities.extend(self._find_model_upgrade_opportunities())
        opportunities.extend(self._find_parallelization_opportunities())
        opportunities.extend(self._find_caching_opportunities())
        opportunities.extend(self._find_effort_reduction_opportunities())

        # Sort by impact score descending
        opportunities.sort(key=lambda o: (-o.impact_score(), o.priority))

        total_cost = sum(m.get("cost", 0.0) for m in self._metrics)

        # Estimate total savings (weighted average, capped at 30%)
        if opportunities:
            weighted_savings = sum(
                o.estimated_savings_pct * o.confidence
                for o in opportunities
            ) / len(opportunities)
            total_savings_pct = min(30.0, weighted_savings)
        else:
            total_savings_pct = 0.0

        # Quality maintained if no opportunity degrades below floor
        quality_maintained = all(
            (o.estimated_quality_impact > -5.0 or o.risk == RiskLevel.LOW)
            for o in opportunities
        )

        return OptimizationReport(
            date=date,
            total_tasks_analyzed=len(self._metrics),
            total_cost_analyzed=total_cost,
            opportunities=opportunities,
            estimated_total_savings_pct=total_savings_pct,
            quality_maintained=quality_maintained,
        )

    # ------------------------------------------------------------------
    # Opportunity finders
    # ------------------------------------------------------------------

    def _find_model_downgrade_opportunities(self) -> List[OptimizationOpportunity]:
        """Find tasks where a cheaper model would suffice."""
        opps = []
        by_role: Dict[str, List[dict]] = {}
        for m in self._metrics:
            role = m.get("role", "unknown")
            by_role.setdefault(role, []).append(m)

        for role, records in by_role.items():
            opus_low = [
                r for r in records
                if "opus" in r.get("model", "").lower()
                and r.get("complexity_score", 100) < self.OVER_PROVISION_COMPLEXITY_THRESHOLD
            ]
            sonnet_trivial = [
                r for r in records
                if "sonnet" in r.get("model", "").lower()
                and r.get("complexity_score", 100) < self.SONNET_OVER_PROVISION_THRESHOLD
            ]

            if opus_low:
                savings_pct = (1.0 - 1.0 / 3.0) * 100  # Sonnet is 1/3 of Opus cost
                opps.append(OptimizationOpportunity(
                    type=OpportunityType.MODEL_DOWNGRADE,
                    role=role,
                    description=(
                        f"{len(opus_low)} tasks used Opus for low-complexity work "
                        f"(complexity < {self.OVER_PROVISION_COMPLEXITY_THRESHOLD}). "
                        f"Switch to Sonnet."
                    ),
                    estimated_savings_pct=savings_pct,
                    estimated_quality_impact=-4.0,  # Opus→Sonnet quality delta
                    confidence=min(0.95, 0.65 + len(opus_low) * 0.02),
                    risk=RiskLevel.LOW,
                    priority=1,
                    affected_tasks=len(opus_low),
                    ab_test_recommended=len(opus_low) >= 5,
                    metadata={"from_model": "opus-4-8", "to_model": "sonnet-4-6"},
                ))

            if sonnet_trivial:
                savings_pct = (1.0 - 0.33) * 100  # Haiku is 0.33× Sonnet
                opps.append(OptimizationOpportunity(
                    type=OpportunityType.MODEL_DOWNGRADE,
                    role=role,
                    description=(
                        f"{len(sonnet_trivial)} trivial tasks used Sonnet "
                        f"(complexity < {self.SONNET_OVER_PROVISION_THRESHOLD}). "
                        f"Switch to Haiku."
                    ),
                    estimated_savings_pct=savings_pct,
                    estimated_quality_impact=-11.0,  # Sonnet→Haiku quality delta
                    confidence=min(0.90, 0.60 + len(sonnet_trivial) * 0.02),
                    risk=RiskLevel.MEDIUM,
                    priority=2,
                    affected_tasks=len(sonnet_trivial),
                    ab_test_recommended=True,
                    metadata={"from_model": "sonnet-4-6", "to_model": "haiku-4-5"},
                ))

        return opps

    def _find_model_upgrade_opportunities(self) -> List[OptimizationOpportunity]:
        """Find tasks where escalation suggests under-provisioning."""
        opps = []
        by_role: Dict[str, List[dict]] = {}
        for m in self._metrics:
            role = m.get("role", "unknown")
            by_role.setdefault(role, []).append(m)

        for role, records in by_role.items():
            escalated = [r for r in records if r.get("escalated", False)]
            escalation_rate = len(escalated) / len(records) if records else 0.0

            if escalation_rate > self.HIGH_ESCALATION_RATE:
                # Upgrading reduces re-runs; net cost may decrease
                opps.append(OptimizationOpportunity(
                    type=OpportunityType.MODEL_UPGRADE,
                    role=role,
                    description=(
                        f"{role} has {escalation_rate:.0%} escalation rate "
                        f"({len(escalated)}/{len(records)} tasks). "
                        f"Upgrade model to reduce re-runs."
                    ),
                    estimated_savings_pct=escalation_rate * 30,  # Re-run cost savings
                    estimated_quality_impact=5.0,
                    confidence=min(0.85, 0.5 + escalation_rate),
                    risk=RiskLevel.MEDIUM,
                    priority=2,
                    affected_tasks=len(escalated),
                    ab_test_recommended=True,
                ))

        return opps

    def _find_parallelization_opportunities(self) -> List[OptimizationOpportunity]:
        """Find task types that could run concurrently to reduce wall-clock time."""
        opps = []
        by_type: Dict[str, List[dict]] = {}
        for m in self._metrics:
            task_type = m.get("task_type", "unknown")
            by_type.setdefault(task_type, []).append(m)

        for task_type, records in by_type.items():
            if len(records) >= self.PARALLELIZATION_MIN_TASKS:
                avg_duration = statistics.mean(
                    r.get("duration_ms", 0) for r in records
                )
                if avg_duration > 5000:  # Only worth parallelizing if > 5s each
                    opps.append(OptimizationOpportunity(
                        type=OpportunityType.PARALLELIZATION,
                        role="all",
                        description=(
                            f"{len(records)} '{task_type}' tasks could run in parallel "
                            f"(avg duration {avg_duration/1000:.1f}s). "
                            f"Estimated wall-clock reduction: "
                            f"{(1 - 1/len(records))*100:.0f}%."
                        ),
                        estimated_savings_pct=10.0,  # Reduced retry/timeout costs
                        estimated_quality_impact=0.0,
                        confidence=0.70,
                        risk=RiskLevel.LOW,
                        priority=3,
                        affected_tasks=len(records),
                        ab_test_recommended=False,
                        metadata={"task_type": task_type, "avg_duration_ms": avg_duration},
                    ))

        return opps

    def _find_caching_opportunities(self) -> List[OptimizationOpportunity]:
        """Find repeated task types that could benefit from result caching."""
        opps = []
        by_type: Dict[str, int] = {}
        for m in self._metrics:
            task_type = m.get("task_type", "unknown")
            by_type[task_type] = by_type.get(task_type, 0) + 1

        total = len(self._metrics)
        for task_type, count in by_type.items():
            repetition_rate = count / total if total > 0 else 0.0
            if repetition_rate >= self.CACHE_SIMILARITY_THRESHOLD and count >= 3:
                cache_hit_rate = 0.6  # Estimated cache hit rate for repeated tasks
                opps.append(OptimizationOpportunity(
                    type=OpportunityType.CACHING,
                    role="all",
                    description=(
                        f"'{task_type}' appears in {repetition_rate:.0%} of tasks "
                        f"({count} occurrences). "
                        f"Caching could reduce cost by ~{cache_hit_rate*100:.0f}% "
                        f"for repeated calls."
                    ),
                    estimated_savings_pct=cache_hit_rate * repetition_rate * 100,
                    estimated_quality_impact=0.0,
                    confidence=0.75,
                    risk=RiskLevel.LOW,
                    priority=2,
                    affected_tasks=count,
                    ab_test_recommended=False,
                    metadata={"task_type": task_type, "repetition_rate": repetition_rate},
                ))

        return opps

    def _find_effort_reduction_opportunities(self) -> List[OptimizationOpportunity]:
        """Find tasks where effort level could be reduced."""
        opps = []
        high_effort_low_complexity = [
            m for m in self._metrics
            if m.get("effort", "medium") == "high"
            and m.get("complexity_score", 100) < 30
        ]

        if high_effort_low_complexity:
            opps.append(OptimizationOpportunity(
                type=OpportunityType.EFFORT_REDUCTION,
                role="all",
                description=(
                    f"{len(high_effort_low_complexity)} tasks used 'high' effort "
                    f"for low-complexity work (score < 30). "
                    f"Reduce to 'medium' effort."
                ),
                estimated_savings_pct=20.0,  # High→medium effort ~20% token reduction
                estimated_quality_impact=-2.0,
                confidence=0.80,
                risk=RiskLevel.LOW,
                priority=2,
                affected_tasks=len(high_effort_low_complexity),
                ab_test_recommended=False,
            ))

        return opps

    # ------------------------------------------------------------------
    # Effectiveness tracking
    # ------------------------------------------------------------------

    def record_outcome(
        self,
        opportunity_type: OpportunityType,
        role: str,
        outcome: str,  # "pass" | "fail"
        actual_savings_pct: float = 0.0,
    ) -> None:
        """Record whether an optimization recommendation worked."""
        self._effectiveness_history.append({
            "type": opportunity_type.value,
            "role": role,
            "outcome": outcome,
            "actual_savings_pct": actual_savings_pct,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

    def get_effectiveness_summary(self) -> Dict[str, Any]:
        """Summarize effectiveness of past recommendations."""
        if not self._effectiveness_history:
            return {"total": 0, "pass_rate": 0.0, "avg_savings_pct": 0.0}

        total = len(self._effectiveness_history)
        passes = sum(1 for e in self._effectiveness_history if e["outcome"] == "pass")
        avg_savings = statistics.mean(
            e["actual_savings_pct"] for e in self._effectiveness_history
        )
        return {
            "total": total,
            "pass_rate": passes / total,
            "avg_savings_pct": avg_savings,
        }
