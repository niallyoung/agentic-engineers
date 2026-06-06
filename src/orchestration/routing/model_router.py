# -*- coding: utf-8 -*-
"""
ModelRouter — task type → (role, model, effort, budget) routing decisions.

Phase 5.2 implementation. A deliberately *hardcoded* decision matrix backed
by Phase 4 metrics. ML-based routing is deferred to Phase 6.

Design:
  - Rules are evaluated in priority order (lowest priority_rank wins ties).
  - First matching rule whose `match(task)` returns True is selected.
  - A guaranteed fallback rule ensures every task receives a decision.
  - Budgets are sourced from src/config/token-budgets.yaml so role caps
    cannot drift between the router and budget monitor.

Public API::

    router = load_default_router()
    decision = router.route({
        "task_type": "bug_fix",
        "scope": "Fix off-by-one in pagination",
        "estimated_complexity": "low",
    })
    decision.role     # "engineer"
    decision.model    # "claude-haiku"
    decision.effort   # "high"
    decision.budget   # 1500

Rules (current set, derived from Phase 4.1-4.3):
  1. code_review / audit       → lead_engineer (Sonnet, 2500)
  2. security / threat-model   → security_engineer (Opus, 5000)
  3. architecture / cross-svc  → principal_engineer (Opus, 5000)
  4. complex / unscoped impl   → senior_engineer (Sonnet, 2500)
  5. quality_gate / qe-review  → quality_engineer (Sonnet, 1000)
  6. cost_analysis / metrics   → model_engineer (Sonnet, 1500)
  7. orchestration / routing   → general_orchestrator (Haiku, 500)
  8. fallback (well-scoped)    → engineer (Haiku, 1500)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RoutingDecision:
    """Final routing decision for a task."""
    role: str
    model: str
    effort: str
    budget: int
    rule_name: str
    rationale: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "model": self.model,
            "effort": self.effort,
            "budget": self.budget,
            "rule_name": self.rule_name,
            "rationale": self.rationale,
        }


@dataclass
class RoutingRule:
    """A single routing rule. Lower priority_rank evaluated first."""
    name: str
    role: str
    model: str
    effort: str
    priority_rank: int
    rationale: str
    match: Callable[[Dict[str, Any]], bool]


# ---------------------------------------------------------------------------
# Matchers — small composable predicates
# ---------------------------------------------------------------------------

_REVIEW_KEYS = {"code_review", "review", "audit", "pr_review"}
_SECURITY_KEYS = {"security", "threat_model", "stride", "vuln", "vulnerability"}
_ARCH_KEYS = {"architecture", "cross_service", "design", "rfc"}
_COMPLEX_KEYS = {"refactor", "diagnosis", "investigation", "complex_impl"}
_QUALITY_KEYS = {"quality_gate", "qe_review", "test_review"}
_COST_KEYS = {"cost_analysis", "model_recommendation", "metrics_review"}
_ORCH_KEYS = {"orchestration", "routing", "delegate"}


def _has(task: Dict[str, Any], key: str, values) -> bool:
    val = task.get(key)
    if val is None:
        return False
    return str(val).lower() in {str(v).lower() for v in values}


def _is_review(t: Dict[str, Any]) -> bool:
    return _has(t, "task_type", _REVIEW_KEYS)


def _is_security(t: Dict[str, Any]) -> bool:
    return (
        _has(t, "task_type", _SECURITY_KEYS)
        or _has(t, "security_scope", {"auth", "crypto", "pii", "secrets", "injection"})
    )


def _is_architecture(t: Dict[str, Any]) -> bool:
    return _has(t, "task_type", _ARCH_KEYS) or t.get("approval_gate") == "principal_engineer"


def _is_complex(t: Dict[str, Any]) -> bool:
    if _has(t, "task_type", _COMPLEX_KEYS):
        return True
    return str(t.get("estimated_complexity", "")).lower() in {"high", "complex", "unscoped"}


def _is_quality(t: Dict[str, Any]) -> bool:
    return _has(t, "task_type", _QUALITY_KEYS)


def _is_cost(t: Dict[str, Any]) -> bool:
    return _has(t, "task_type", _COST_KEYS)


def _is_orchestration(t: Dict[str, Any]) -> bool:
    return _has(t, "task_type", _ORCH_KEYS)


def _always(t: Dict[str, Any]) -> bool:  # fallback
    return True


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class ModelRouter:
    """Evaluates rules in priority order and returns a RoutingDecision."""

    def __init__(self, rules: List[RoutingRule], budgets: Dict[str, int]) -> None:
        if not rules:
            raise ValueError("ModelRouter requires at least one rule")
        # Stable sort by priority_rank
        self._rules: List[RoutingRule] = sorted(rules, key=lambda r: r.priority_rank)
        self._budgets: Dict[str, int] = dict(budgets)
        # Verify a catch-all exists
        if not any(r.match is _always for r in self._rules):
            raise ValueError("ModelRouter requires a fallback rule (match=_always)")

    @property
    def rules(self) -> List[RoutingRule]:
        return list(self._rules)

    def route(self, task: Dict[str, Any]) -> RoutingDecision:
        """Pick the first matching rule and emit a RoutingDecision."""
        if not isinstance(task, dict):
            raise TypeError(f"task must be a dict, got {type(task).__name__}")
        for rule in self._rules:
            try:
                matched = bool(rule.match(task))
            except Exception:
                matched = False
            if matched:
                budget = self._budgets.get(rule.role, 1500)
                return RoutingDecision(
                    role=rule.role,
                    model=rule.model,
                    effort=rule.effort,
                    budget=budget,
                    rule_name=rule.name,
                    rationale=rule.rationale,
                )
        # Unreachable given the fallback invariant
        raise RuntimeError("No rule matched and no fallback present")


# ---------------------------------------------------------------------------
# Default ruleset + loader
# ---------------------------------------------------------------------------

DEFAULT_RULES: List[RoutingRule] = [
    RoutingRule(
        name="security_first",
        role="security_engineer",
        model="claude-opus",
        effort="max",
        priority_rank=10,
        rationale="Security tasks always route to Opus — non-negotiable.",
        match=_is_security,
    ),
    RoutingRule(
        name="architecture_to_principal",
        role="principal_engineer",
        model="claude-opus",
        effort="high",
        priority_rank=20,
        rationale="Cross-service / architectural decisions need Principal review.",
        match=_is_architecture,
    ),
    RoutingRule(
        name="code_review_to_lead",
        role="lead_engineer",
        model="claude-sonnet",
        effort="high",
        priority_rank=30,
        rationale="Phase 4.3 showed Sonnet-Lead at 2k tokens for comprehensive audit.",
        match=_is_review,
    ),
    RoutingRule(
        name="quality_gate_to_qe",
        role="quality_engineer",
        model="claude-sonnet",
        effort="medium",
        priority_rank=40,
        rationale="8-point checklist needs Sonnet judgment, bounded scope.",
        match=_is_quality,
    ),
    RoutingRule(
        name="cost_to_model_engineer",
        role="model_engineer",
        model="claude-sonnet",
        effort="medium",
        priority_rank=50,
        rationale="Cost/model recommendation work — structured metric synthesis.",
        match=_is_cost,
    ),
    RoutingRule(
        name="complex_to_senior",
        role="senior_engineer",
        model="claude-sonnet",
        effort="high",
        priority_rank=60,
        rationale="Unscoped / complex implementation needs Sonnet headroom.",
        match=_is_complex,
    ),
    RoutingRule(
        name="orchestration_to_haiku",
        role="general_orchestrator",
        model="claude-haiku",
        effort="high",
        priority_rank=70,
        rationale="Pure routing is ~300 tokens — Haiku is the right tool.",
        match=_is_orchestration,
    ),
    RoutingRule(
        name="fallback_engineer",
        role="engineer",
        model="claude-haiku",
        effort="high",
        priority_rank=999,
        rationale="Default: well-scoped, planned work → Haiku Engineer (Phase 4.1/4.2).",
        match=_always,
    ),
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_budgets(path: Optional[Path] = None) -> Dict[str, int]:
    """Load per-role budgets from token-budgets.yaml."""
    path = path or _repo_root() / "src" / "config" / "token-budgets.yaml"
    with open(path, "r") as fh:
        data = yaml.safe_load(fh) or {}
    roles = data.get("roles", {}) or {}
    return {role: int(cfg.get("budget", 1500)) for role, cfg in roles.items()}


def load_default_router(budgets_path: Optional[Path] = None) -> ModelRouter:
    """Construct the default router with built-in rules + YAML budgets."""
    budgets = load_budgets(budgets_path)
    return ModelRouter(rules=DEFAULT_RULES, budgets=budgets)
