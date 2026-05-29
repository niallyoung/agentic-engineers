# -*- coding: utf-8 -*-
"""
CostAwareRouter — Route tasks to the lowest-cost agent that meets quality threshold.

Decision logic:
  1. Score all eligible candidates for the task
  2. Filter candidates that meet the minimum quality threshold
  3. Among passing candidates, select the lowest-cost option
  4. Apply budget constraints (per-agent and global)
  5. Track cost efficiency metrics

Candidate scoring:
  - base_cost = estimated_tokens * cost_per_token * model_multiplier
  - quality_score = model quality baseline (adjusted by role history)
  - efficiency = quality_score / base_cost

Usage::

    router = CostAwareRouter(quality_threshold=90.0)
    router.set_budget("engineer", daily_limit=5.0)
    candidate = router.route(task)
    print(candidate.agent, candidate.model, candidate.estimated_cost)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import threading
from datetime import datetime, date


# ---------------------------------------------------------------------------
# Model cost and quality constants (aligned with model_selector.py)
# ---------------------------------------------------------------------------

MODEL_COST_MULTIPLIERS: Dict[str, float] = {
    "haiku-4-5":  0.33,
    "sonnet-4-6": 1.00,
    "opus-4-6":   3.00,
    "opus-4-8":   3.00,
}

MODEL_QUALITY_BASELINES: Dict[str, float] = {
    "haiku-4-5":  82.0,
    "sonnet-4-6": 93.0,
    "opus-4-6":   97.0,
    "opus-4-8":   98.0,
}

BASE_COST_PER_TOKEN: float = 0.0003  # Sonnet rate in USD


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class CostBudget:
    """Budget constraints for an agent or globally."""
    daily_limit: float = float("inf")
    weekly_limit: float = float("inf")
    monthly_limit: float = float("inf")
    spent_today: float = 0.0
    spent_this_week: float = 0.0
    spent_this_month: float = 0.0
    last_reset: str = field(default_factory=lambda: date.today().isoformat())

    def has_capacity(self, estimated_cost: float) -> bool:
        """Return True if budget can absorb the estimated cost."""
        return (
            self.spent_today + estimated_cost <= self.daily_limit
            and self.spent_this_week + estimated_cost <= self.weekly_limit
            and self.spent_this_month + estimated_cost <= self.monthly_limit
        )

    def record_spend(self, cost: float) -> None:
        """Record actual spend against all budget windows."""
        self.spent_today += cost
        self.spent_this_week += cost
        self.spent_this_month += cost

    def remaining_daily(self) -> float:
        return max(0.0, self.daily_limit - self.spent_today)

    def utilization_pct(self) -> float:
        if self.daily_limit == float("inf"):
            return 0.0
        return (self.spent_today / self.daily_limit) * 100


@dataclass
class RoutingCandidate:
    """A candidate agent/model pairing for a task."""
    agent: str
    role: str
    model: str
    estimated_cost: float
    quality_score: float
    cost_multiplier: float
    within_budget: bool
    efficiency_score: float  # quality / cost (higher is better)
    rationale: str
    selected: bool = False


@dataclass
class RoutingResult:
    """Result of a routing decision."""
    task_id: str
    selected: Optional[RoutingCandidate]
    all_candidates: List[RoutingCandidate]
    quality_threshold: float
    timestamp: str
    fallback_used: bool = False
    rejection_reason: str = ""

    def summary(self) -> str:
        if self.selected:
            return (
                f"Task {self.task_id}: routed to {self.selected.agent} "
                f"[{self.selected.model}] "
                f"cost=${self.selected.estimated_cost:.4f} "
                f"quality={self.selected.quality_score:.1f}"
            )
        return f"Task {self.task_id}: no viable candidate — {self.rejection_reason}"


# ---------------------------------------------------------------------------
# CostAwareRouter
# ---------------------------------------------------------------------------

class CostAwareRouter:
    """
    Route tasks to the lowest-cost agent that meets the quality threshold.

    Thread-safe for concurrent routing operations.
    """

    DEFAULT_QUALITY_THRESHOLD: float = 90.0

    def __init__(self, quality_threshold: float = DEFAULT_QUALITY_THRESHOLD):
        self._quality_threshold = quality_threshold
        self._budgets: Dict[str, CostBudget] = {}
        self._global_budget: CostBudget = CostBudget()
        self._routing_history: List[RoutingResult] = []
        self._spend_by_agent: Dict[str, float] = {}
        self._spend_by_model: Dict[str, float] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Budget management
    # ------------------------------------------------------------------

    def set_budget(
        self,
        agent: str,
        daily_limit: float = float("inf"),
        weekly_limit: float = float("inf"),
        monthly_limit: float = float("inf"),
    ) -> None:
        """Set budget constraints for a specific agent."""
        with self._lock:
            self._budgets[agent] = CostBudget(
                daily_limit=daily_limit,
                weekly_limit=weekly_limit,
                monthly_limit=monthly_limit,
            )

    def set_global_budget(
        self,
        daily_limit: float = float("inf"),
        weekly_limit: float = float("inf"),
        monthly_limit: float = float("inf"),
    ) -> None:
        """Set global budget constraints across all agents."""
        with self._lock:
            self._global_budget = CostBudget(
                daily_limit=daily_limit,
                weekly_limit=weekly_limit,
                monthly_limit=monthly_limit,
            )

    def get_budget(self, agent: str) -> CostBudget:
        """Return the budget for an agent (or unlimited if not set)."""
        with self._lock:
            return self._budgets.get(agent, CostBudget())

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def route(
        self,
        task_id: str,
        candidates: List[Dict],
        estimated_tokens: int = 1000,
        security_sensitive: bool = False,
        required_quality: Optional[float] = None,
    ) -> RoutingResult:
        """
        Select the lowest-cost candidate that meets quality and budget constraints.

        Args:
            task_id: Unique task identifier
            candidates: List of dicts with keys: agent, role, model
            estimated_tokens: Estimated token count for cost calculation
            security_sensitive: If True, enforce Opus minimum
            required_quality: Override default quality threshold for this task

        Returns:
            RoutingResult with selected candidate and full candidate list
        """
        threshold = required_quality if required_quality is not None else self._quality_threshold
        timestamp = datetime.utcnow().isoformat() + "Z"

        scored = self._score_candidates(candidates, estimated_tokens, security_sensitive)

        # Filter by quality and budget
        viable = [c for c in scored if c.quality_score >= threshold and c.within_budget]

        if not viable:
            # Fallback: best quality regardless of cost
            fallback = max(scored, key=lambda c: c.quality_score) if scored else None
            if fallback:
                fallback.selected = True
            result = RoutingResult(
                task_id=task_id,
                selected=fallback,
                all_candidates=scored,
                quality_threshold=threshold,
                timestamp=timestamp,
                fallback_used=True,
                rejection_reason="no candidate meets quality threshold and budget",
            )
        else:
            # Select lowest cost among viable
            best = min(viable, key=lambda c: c.estimated_cost)
            best.selected = True
            result = RoutingResult(
                task_id=task_id,
                selected=best,
                all_candidates=scored,
                quality_threshold=threshold,
                timestamp=timestamp,
            )

        # Record spend
        if result.selected:
            self._record_spend(result.selected)

        with self._lock:
            self._routing_history.append(result)

        return result

    def _score_candidates(
        self,
        candidates: List[Dict],
        estimated_tokens: int,
        security_sensitive: bool,
    ) -> List[RoutingCandidate]:
        scored = []
        for c in candidates:
            agent = c.get("agent", "unknown")
            role = c.get("role", "unknown")
            model = c.get("model", "sonnet-4-6")

            # Security override: Opus minimum (4.8 for security tasks)
            if security_sensitive and model not in ("opus-4-6", "opus-4-8"):
                model = "opus-4-8"

            multiplier = MODEL_COST_MULTIPLIERS.get(model, 1.0)
            quality = MODEL_QUALITY_BASELINES.get(model, 90.0)

            # Apply role-specific quality adjustment from history
            quality = self._adjust_quality_for_role(agent, quality)

            cost = estimated_tokens * BASE_COST_PER_TOKEN * multiplier
            efficiency = quality / cost if cost > 0 else 0.0

            # Check budget
            agent_budget = self._budgets.get(agent, CostBudget())
            within_budget = (
                agent_budget.has_capacity(cost)
                and self._global_budget.has_capacity(cost)
            )

            rationale = (
                f"{agent} [{model}]: cost=${cost:.4f} "
                f"quality={quality:.1f} "
                f"efficiency={efficiency:.1f} "
                f"budget={'ok' if within_budget else 'exceeded'}"
            )

            scored.append(RoutingCandidate(
                agent=agent,
                role=role,
                model=model,
                estimated_cost=cost,
                quality_score=quality,
                cost_multiplier=multiplier,
                within_budget=within_budget,
                efficiency_score=efficiency,
                rationale=rationale,
            ))

        # Sort by cost ascending (cheapest first)
        scored.sort(key=lambda c: c.estimated_cost)
        return scored

    def _adjust_quality_for_role(self, agent: str, base_quality: float) -> float:
        """Adjust quality estimate based on historical performance for this agent."""
        # Future: load from metrics history; for now return base
        return base_quality

    def _record_spend(self, candidate: RoutingCandidate) -> None:
        """Record actual spend for budget tracking."""
        with self._lock:
            agent_budget = self._budgets.get(candidate.agent)
            if agent_budget:
                agent_budget.record_spend(candidate.estimated_cost)
            self._global_budget.record_spend(candidate.estimated_cost)
            self._spend_by_agent[candidate.agent] = (
                self._spend_by_agent.get(candidate.agent, 0.0) + candidate.estimated_cost
            )
            self._spend_by_model[candidate.model] = (
                self._spend_by_model.get(candidate.model, 0.0) + candidate.estimated_cost
            )

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_spend_by_agent(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._spend_by_agent)

    def get_spend_by_model(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._spend_by_model)

    def get_routing_history(self) -> List[RoutingResult]:
        with self._lock:
            return list(self._routing_history)

    def get_efficiency_metrics(self) -> Dict[str, float]:
        """Return cost efficiency metrics across all routing decisions."""
        with self._lock:
            history = list(self._routing_history)

        if not history:
            return {"total_tasks": 0, "total_cost": 0.0, "avg_quality": 0.0, "fallback_rate": 0.0}

        total_cost = sum(
            r.selected.estimated_cost for r in history if r.selected
        )
        qualities = [r.selected.quality_score for r in history if r.selected]
        fallbacks = sum(1 for r in history if r.fallback_used)

        return {
            "total_tasks": len(history),
            "total_cost": total_cost,
            "avg_quality": sum(qualities) / len(qualities) if qualities else 0.0,
            "fallback_rate": fallbacks / len(history),
            "avg_cost_per_task": total_cost / len(history),
        }

    def clear_history(self) -> None:
        """Clear routing history and spend tracking (for testing)."""
        with self._lock:
            self._routing_history.clear()
            self._spend_by_agent.clear()
            self._spend_by_model.clear()
