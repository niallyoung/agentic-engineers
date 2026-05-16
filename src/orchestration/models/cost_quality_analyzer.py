# -*- coding: utf-8 -*-
"""
CostQualityAnalyzer — Analyze cost-quality tradeoffs across tasks.

Reads task metric records (dicts with role, model, tokens, cost, quality_score)
and produces:
  - Per-role efficiency reports
  - Over-provisioned task detection (Opus for trivial work)
  - Under-provisioned task detection (Haiku for complex work)
  - Cost-per-quality-point calculations
  - Actionable recommendations

Metric record schema (all fields optional except where noted):
  {
    "role": str,              # required
    "model": str,             # required
    "tokens_in": int,
    "tokens_out": int,
    "cost": float,            # USD
    "quality_score": float,   # 0–100
    "complexity_score": float,# 0–100 (from ComplexityScorer)
    "escalated": bool,
    "task_id": str,
  }
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .model_selector import ModelTier, MODEL_COST_MULTIPLIERS, MODEL_QUALITY_BASELINES

# Cost target: $0.0016 per quality point (from existing model-engineer config)
COST_TARGET_PER_QUALITY_POINT: float = 0.0016

# Thresholds for over/under provisioning
OVER_PROVISION_THRESHOLD: float = 0.5   # cost_multiplier / expected_multiplier > this
UNDER_PROVISION_QUALITY_GAP: float = 10.0  # quality gap below baseline triggers flag


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RoleStats:
    """Aggregated statistics for a single role."""
    role: str
    model: str
    task_count: int
    avg_quality: float
    avg_cost: float
    total_cost: float
    cost_per_quality_point: float
    avg_tokens: float
    escalation_rate: float
    efficiency: str  # "good" | "fair" | "poor"
    over_provisioned_count: int = 0
    under_provisioned_count: int = 0


@dataclass
class EfficiencyReport:
    """Full efficiency analysis across all roles."""
    date: str
    role_stats: Dict[str, RoleStats]
    over_provisioned_tasks: List[dict] = field(default_factory=list)
    under_provisioned_tasks: List[dict] = field(default_factory=list)
    outliers: List[dict] = field(default_factory=list)
    total_cost: float = 0.0
    total_tasks: int = 0
    avg_cost_per_quality: float = 0.0

    def summary(self) -> str:
        lines = [
            f"=== Cost-Quality Efficiency Report ({self.date}) ===",
            f"Total tasks: {self.total_tasks}  |  Total cost: ${self.total_cost:.4f}",
            f"Avg cost/quality point: ${self.avg_cost_per_quality:.4f}  "
            f"(target: ${COST_TARGET_PER_QUALITY_POINT:.4f})",
            "",
            "Role Performance:",
        ]
        for role, stats in sorted(
            self.role_stats.items(), key=lambda x: x[1].cost_per_quality_point
        ):
            status = {"good": "✓", "fair": "⚠", "poor": "❌"}.get(stats.efficiency, "?")
            lines.append(
                f"  {status} {role} [{stats.model}]: "
                f"quality={stats.avg_quality:.1f}%  "
                f"cost/quality=${stats.cost_per_quality_point:.4f}  "
                f"tasks={stats.task_count}  "
                f"escalations={stats.escalation_rate*100:.1f}%"
            )
        if self.over_provisioned_tasks:
            lines.append(f"\nOver-provisioned tasks: {len(self.over_provisioned_tasks)}")
        if self.under_provisioned_tasks:
            lines.append(f"Under-provisioned tasks: {len(self.under_provisioned_tasks)}")
        if self.outliers:
            lines.append(f"Outliers (unusual token usage): {len(self.outliers)}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# CostQualityAnalyzer
# ---------------------------------------------------------------------------

class CostQualityAnalyzer:
    """
    Analyze cost-quality tradeoffs from task metric records.

    Usage::

        analyzer = CostQualityAnalyzer()
        analyzer.load(metrics_list)
        report = analyzer.analyze()
        print(report.summary())
    """

    def __init__(self):
        self._metrics: List[dict] = []

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load(self, metrics: List[dict]) -> None:
        """Load a list of task metric dicts."""
        self._metrics = list(metrics)

    def load_from_file(self, path: str) -> bool:
        """Load metrics from a JSON-lines file. Returns True on success."""
        import json
        from pathlib import Path

        p = Path(path)
        if not p.exists():
            return False

        records = []
        with open(p) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        self._metrics = records
        return bool(records)

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def analyze(self, date: str = "today") -> EfficiencyReport:
        """Run full cost-quality analysis on loaded metrics."""
        if not self._metrics:
            return EfficiencyReport(
                date=date,
                role_stats={},
                total_cost=0.0,
                total_tasks=0,
                avg_cost_per_quality=0.0,
            )

        role_buckets: Dict[str, List[dict]] = defaultdict(list)
        for m in self._metrics:
            role = m.get("role", "Unknown")
            role_buckets[role].append(m)

        role_stats: Dict[str, RoleStats] = {}
        over_provisioned: List[dict] = []
        under_provisioned: List[dict] = []
        outliers: List[dict] = []

        all_costs: List[float] = []
        all_quality: List[float] = []

        for role, records in role_buckets.items():
            stats = self._compute_role_stats(role, records)
            role_stats[role] = stats
            all_costs.extend(r.get("cost", 0.0) for r in records)
            all_quality.extend(r.get("quality_score", 0.0) for r in records if r.get("quality_score"))

        # Detect over/under provisioned tasks
        for m in self._metrics:
            if self._is_over_provisioned(m):
                over_provisioned.append(m)
            if self._is_under_provisioned(m):
                under_provisioned.append(m)

        # Detect outliers (token usage > 3σ from mean)
        all_tokens = [
            (m.get("tokens_in", 0) + m.get("tokens_out", 0))
            for m in self._metrics
        ]
        if len(all_tokens) >= 3:
            mean_t = statistics.mean(all_tokens)
            stdev_t = statistics.stdev(all_tokens)
            for m, t in zip(self._metrics, all_tokens):
                if stdev_t > 0 and abs(t - mean_t) > 2.5 * stdev_t:
                    outliers.append({**m, "_token_count": t, "_z_score": (t - mean_t) / stdev_t})

        total_cost = sum(all_costs)
        avg_cpq = (
            total_cost / statistics.mean(all_quality)
            if all_quality and statistics.mean(all_quality) > 0
            else 0.0
        )

        return EfficiencyReport(
            date=date,
            role_stats=role_stats,
            over_provisioned_tasks=over_provisioned,
            under_provisioned_tasks=under_provisioned,
            outliers=outliers,
            total_cost=total_cost,
            total_tasks=len(self._metrics),
            avg_cost_per_quality=avg_cpq,
        )

    # ------------------------------------------------------------------
    # Role stats computation
    # ------------------------------------------------------------------

    def _compute_role_stats(self, role: str, records: List[dict]) -> RoleStats:
        qualities = [r.get("quality_score", 0.0) for r in records]
        costs = [r.get("cost", 0.0) for r in records]
        tokens = [
            r.get("tokens_in", 0) + r.get("tokens_out", 0)
            for r in records
        ]
        escalations = sum(1 for r in records if r.get("escalated", False))

        avg_quality = statistics.mean(qualities) if qualities else 0.0
        avg_cost = statistics.mean(costs) if costs else 0.0
        total_cost = sum(costs)
        avg_tokens = statistics.mean(tokens) if tokens else 0.0
        escalation_rate = escalations / len(records) if records else 0.0

        cpq = total_cost / avg_quality if avg_quality > 0 else float("inf")
        efficiency = self._efficiency_label(cpq)

        # Count over/under provisioned within role
        over_count = sum(1 for r in records if self._is_over_provisioned(r))
        under_count = sum(1 for r in records if self._is_under_provisioned(r))

        model = records[0].get("model", "unknown") if records else "unknown"

        return RoleStats(
            role=role,
            model=model,
            task_count=len(records),
            avg_quality=avg_quality,
            avg_cost=avg_cost,
            total_cost=total_cost,
            cost_per_quality_point=cpq,
            avg_tokens=avg_tokens,
            escalation_rate=escalation_rate,
            efficiency=efficiency,
            over_provisioned_count=over_count,
            under_provisioned_count=under_count,
        )

    # ------------------------------------------------------------------
    # Provisioning detection
    # ------------------------------------------------------------------

    @staticmethod
    def _is_over_provisioned(m: dict) -> bool:
        """
        Over-provisioned: expensive model used for a low-complexity task.
        Heuristic: model is Opus but complexity_score < 40 (LOW or TRIVIAL).
        """
        model = m.get("model", "")
        complexity = m.get("complexity_score")
        if complexity is None:
            return False
        if "opus" in model.lower() and complexity < 40:
            return True
        if "sonnet" in model.lower() and complexity < 20:
            return True
        return False

    @staticmethod
    def _is_under_provisioned(m: dict) -> bool:
        """
        Under-provisioned: cheap model used for a high-complexity task.
        Heuristic: model is Haiku but complexity_score >= 60 (HIGH or CRITICAL).
        """
        model = m.get("model", "")
        complexity = m.get("complexity_score")
        quality = m.get("quality_score")
        if complexity is None:
            return False
        if "haiku" in model.lower() and complexity >= 60:
            return True
        # Also flag if quality is significantly below model baseline
        if quality is not None and "haiku" in model.lower():
            baseline = MODEL_QUALITY_BASELINES.get(ModelTier.HAIKU, 82.0)
            if quality < baseline - UNDER_PROVISION_QUALITY_GAP:
                return True
        return False

    @staticmethod
    def _efficiency_label(cpq: float) -> str:
        if cpq <= COST_TARGET_PER_QUALITY_POINT * 1.1:
            return "good"
        elif cpq <= COST_TARGET_PER_QUALITY_POINT * 1.3:
            return "fair"
        else:
            return "poor"

    # ------------------------------------------------------------------
    # Cost comparison helpers
    # ------------------------------------------------------------------

    @staticmethod
    def compare_models(
        tokens: int,
        quality_a: float,
        quality_b: float,
        model_a: ModelTier,
        model_b: ModelTier,
        base_cost_per_token: float = 0.0003,
    ) -> dict:
        """
        Compare cost-quality tradeoff between two models for a given task.

        Returns a dict with cost, quality, and efficiency metrics for both.
        """
        cost_a = tokens * base_cost_per_token * MODEL_COST_MULTIPLIERS[model_a]
        cost_b = tokens * base_cost_per_token * MODEL_COST_MULTIPLIERS[model_b]
        cpq_a = cost_a / quality_a if quality_a > 0 else float("inf")
        cpq_b = cost_b / quality_b if quality_b > 0 else float("inf")

        return {
            "model_a": {
                "model": model_a.value,
                "cost": cost_a,
                "quality": quality_a,
                "cost_per_quality": cpq_a,
                "efficiency": CostQualityAnalyzer._efficiency_label(cpq_a),
            },
            "model_b": {
                "model": model_b.value,
                "cost": cost_b,
                "quality": quality_b,
                "cost_per_quality": cpq_b,
                "efficiency": CostQualityAnalyzer._efficiency_label(cpq_b),
            },
            "winner": model_a.value if cpq_a <= cpq_b else model_b.value,
            "cost_delta_pct": (cost_b - cost_a) / cost_a * 100 if cost_a > 0 else 0.0,
            "quality_delta_pct": (quality_b - quality_a) / quality_a * 100 if quality_a > 0 else 0.0,
        }
