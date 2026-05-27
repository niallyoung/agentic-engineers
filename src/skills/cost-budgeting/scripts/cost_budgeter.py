#!/usr/bin/env python3
"""
cost_budgeter.py — Cost Budgeting & Enforcement (COST-001)

Tracks agent spend at multiple time granularities (session / hour / day / week / month),
enforces hard limits, and emits graduated alerts before budgets are exhausted.

Key design decisions:
- Persist state to ~/.copilot/costs/{session_id}/{granularity}.json (crash-safe)
- Load provider cost rates from src/config/models.yaml at runtime (no hard-codes)
- Independent budgets per session (no cross-session contamination)
- Thread-safe writes via atomic rename pattern
- Double-alert prevention via `alerts_fired` list

Usage:
    from scripts.cost_budgeter import CostBudgeter, CostBudget

    budgeter = CostBudgeter()
    allowed  = budgeter.enforce_budget("sess-001", task_cost=0.05, granularity="session")
    level    = budgeter.graceful_degrade(spend_percent=82.0)
    cost_usd = budgeter.calculate_provider_cost("anthropic", {"input": 5000, "output": 1500}, "claude-sonnet")
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_GRANULARITIES = ("session", "hour", "day", "week", "month")

DEFAULT_ALERT_THRESHOLDS = [0.50, 0.75, 0.90, 1.00]

DEGRADATION_LEVELS = [
    (0.90, "blocked"),
    (0.75, "critical"),
    (0.50, "caution"),
    (0.00, "safe"),
]

# Fallback rates when provider/model not found in models.yaml (gpt-4o rates)
FALLBACK_COST_RATES = {"input": 0.0025, "output": 0.01}

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class CostBudget:
    """
    Budget tracking record for one (session_id, granularity) pair.

    All monetary values are in USD.
    """

    session_id: str
    granularity: str                          # 'session' | 'hour' | 'day' | 'week' | 'month'
    limit_usd: float                          # hard spending limit
    current_spend: float = 0.0               # accumulated spend this window
    alert_thresholds: List[float] = field(default_factory=lambda: list(DEFAULT_ALERT_THRESHOLDS))
    hard_limit_action: str = "block"         # 'warn' | 'block' | 'escalate'
    provider_splits: Dict[str, float] = field(default_factory=dict)
    period_start: str = ""                   # ISO-8601 UTC window start
    alerts_fired: List[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.granularity not in VALID_GRANULARITIES:
            raise ValueError(
                f"Invalid granularity '{self.granularity}'. "
                f"Must be one of {VALID_GRANULARITIES}"
            )
        if self.limit_usd <= 0:
            raise ValueError(f"limit_usd must be positive, got {self.limit_usd}")
        if self.hard_limit_action not in ("warn", "block", "escalate"):
            raise ValueError(
                f"Invalid hard_limit_action '{self.hard_limit_action}'. "
                "Must be 'warn', 'block', or 'escalate'."
            )
        if not self.period_start:
            self.period_start = _utcnow_iso()

    @property
    def spend_percent(self) -> float:
        """Current spend as a percentage of limit (0-inf)."""
        return (self.current_spend / self.limit_usd) * 100.0

    @property
    def remaining_usd(self) -> float:
        """Remaining budget in USD (may be negative if over limit)."""
        return self.limit_usd - self.current_spend

    @property
    def is_over_limit(self) -> bool:
        return self.current_spend >= self.limit_usd

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CostBudget":
        return cls(**data)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _window_start(granularity: str, now: Optional[datetime] = None) -> str:
    """Return the ISO-8601 start of the current budget window for *granularity*."""
    if now is None:
        now = _utcnow()
    if granularity == "session":
        # Session windows don't roll over automatically; keep whatever was stored
        return now.strftime("%Y-%m-%dT%H:%M:%SZ")
    if granularity == "hour":
        start = now.replace(minute=0, second=0, microsecond=0)
    elif granularity == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif granularity == "week":
        # ISO week starts Monday
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    elif granularity == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        return now.strftime("%Y-%m-%dT%H:%M:%SZ")
    return start.strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_expired(budget: CostBudget, now: Optional[datetime] = None) -> bool:
    """Return True if the budget window has expired and should be reset."""
    if budget.granularity == "session":
        return False  # Session budgets never auto-expire
    if not budget.period_start:
        return False
    if now is None:
        now = _utcnow()
    try:
        start = datetime.fromisoformat(budget.period_start.replace("Z", "+00:00"))
    except ValueError:
        return False
    if budget.granularity == "hour":
        delta = timedelta(hours=1)
    elif budget.granularity == "day":
        delta = timedelta(days=1)
    elif budget.granularity == "week":
        delta = timedelta(weeks=1)
    elif budget.granularity == "month":
        # Approximate: 30 days
        delta = timedelta(days=30)
    else:
        return False
    return now >= start + delta


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class CostBudgeter:
    """
    Cost budgeting and enforcement for agentic-engineers.

    Manages independent budgets per (session_id, granularity) pair.
    Persists state to ~/.copilot/costs/{session_id}/{granularity}.json.
    Loads provider cost rates from src/config/models.yaml.

    Thread safety: individual JSON writes are atomic (write-then-rename).
    """

    def __init__(
        self,
        costs_dir: Optional[Path] = None,
        models_yaml: Optional[Path] = None,
    ) -> None:
        """
        Args:
            costs_dir:   Override base directory for budget JSON files.
                         Defaults to ~/.copilot/costs/.
            models_yaml: Override path to models.yaml.
                         Defaults to src/config/models.yaml relative to repo root.
        """
        self._costs_dir = costs_dir or Path.home() / ".copilot" / "costs"
        self._models_yaml = models_yaml or self._find_models_yaml()
        self._cost_rates: Dict[str, Dict[str, Dict[str, float]]] = {}
        self._load_cost_rates()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_models_yaml() -> Path:
        """Locate models.yaml relative to this file (up to repo root)."""
        here = Path(__file__).resolve()
        for parent in here.parents:
            candidate = parent / "src" / "config" / "models.yaml"
            if candidate.exists():
                return candidate
        # Fallback: search from cwd
        candidate = Path("src") / "config" / "models.yaml"
        if candidate.exists():
            return candidate.resolve()
        return here.parents[3] / "src" / "config" / "models.yaml"

    def _load_cost_rates(self) -> None:
        """Load provider cost rates from models.yaml. Silently uses fallback if missing."""
        if not self._models_yaml.exists():
            logger.warning("models.yaml not found at %s; using fallback rates", self._models_yaml)
            return
        try:
            with open(self._models_yaml, "r") as fh:
                data = yaml.safe_load(fh) or {}
            self._cost_rates = data.get("providers", {})
            logger.debug("Loaded cost rates for %d providers", len(self._cost_rates))
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load models.yaml: %s; using fallback rates", exc)

    def _budget_path(self, session_id: str, granularity: str) -> Path:
        """Return filesystem path for a budget JSON file."""
        return self._costs_dir / session_id / f"{granularity}.json"

    def _load_raw(self, path: Path) -> Optional[dict]:
        """Load JSON from path; return None on any error."""
        try:
            return json.loads(path.read_text())
        except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
            if not isinstance(exc, FileNotFoundError):
                logger.error("Failed to read budget file %s: %s", path, exc)
            return None

    def _save(self, budget: CostBudget) -> None:
        """Atomically persist budget to disk."""
        path = self._budget_path(budget.session_id, budget.granularity)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(budget.to_dict(), indent=2))
            tmp.replace(path)
        except OSError as exc:
            logger.error("Failed to save budget %s: %s", path, exc)
            raise

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_budget(
        self,
        session_id: str,
        granularity: str = "session",
        default_limit_usd: float = 5.00,
        hard_limit_action: str = "block",
    ) -> CostBudget:
        """
        Load or create a CostBudget for (session_id, granularity).

        If the stored budget's window has expired, it is reset automatically.

        Args:
            session_id:         Unique session identifier.
            granularity:        One of 'session' | 'hour' | 'day' | 'week' | 'month'.
            default_limit_usd:  Limit to use when creating a new budget.
            hard_limit_action:  Action on hard-limit hit for new budgets.

        Returns:
            CostBudget instance (possibly freshly created or reset).
        """
        if granularity not in VALID_GRANULARITIES:
            raise ValueError(f"Unknown granularity '{granularity}'")

        path = self._budget_path(session_id, granularity)
        raw = self._load_raw(path)

        if raw is not None:
            try:
                budget = CostBudget.from_dict(raw)
                if _is_expired(budget):
                    logger.info(
                        "Budget %s/%s expired; resetting (was %.4f USD)",
                        session_id, granularity, budget.current_spend,
                    )
                    budget = CostBudget(
                        session_id=session_id,
                        granularity=granularity,
                        limit_usd=budget.limit_usd,
                        hard_limit_action=budget.hard_limit_action,
                        alert_thresholds=budget.alert_thresholds,
                        period_start=_window_start(granularity),
                    )
                    self._save(budget)
                return budget
            except Exception as exc:  # noqa: BLE001
                logger.error("Corrupted budget file %s (%s); recreating", path, exc)

        # Create fresh budget
        budget = CostBudget(
            session_id=session_id,
            granularity=granularity,
            limit_usd=default_limit_usd,
            hard_limit_action=hard_limit_action,
            period_start=_window_start(granularity),
        )
        self._save(budget)
        return budget

    def record_spend(
        self,
        session_id: str,
        amount: float,
        granularity: str = "session",
        provider: Optional[str] = None,
    ) -> CostBudget:
        """
        Increment the accumulated spend for (session_id, granularity) by *amount* USD.

        Args:
            session_id:  Session to update.
            amount:      Non-negative USD cost to add.
            granularity: Budget window.
            provider:    Optional provider name; updates provider_splits.

        Returns:
            Updated CostBudget after recording spend.

        Raises:
            ValueError: If amount is negative.
        """
        if amount < 0:
            raise ValueError(f"Spend amount must be non-negative, got {amount}")

        budget = self.get_budget(session_id, granularity)
        budget.current_spend += amount

        if provider:
            budget.provider_splits[provider] = (
                budget.provider_splits.get(provider, 0.0) + amount
            )

        self._save(budget)
        logger.debug(
            "Recorded spend %.6f USD for %s/%s (total: %.6f / %.6f)",
            amount, session_id, granularity, budget.current_spend, budget.limit_usd,
        )
        return budget

    def calculate_provider_cost(
        self,
        provider: str,
        tokens: Dict[str, int],
        model: str,
    ) -> float:
        """
        Calculate task cost in USD using provider-specific token rates.

        Falls back to gpt-4o rates if provider/model not found.

        Args:
            provider: Provider name (e.g. 'anthropic', 'openai', 'google', 'github_copilot').
            tokens:   Dict with 'input' and/or 'output' token counts.
            model:    Model name (e.g. 'claude-sonnet', 'gpt-4o-mini').

        Returns:
            Cost in USD.

        Raises:
            ValueError: If token counts are negative.
        """
        input_tokens = tokens.get("input", 0)
        output_tokens = tokens.get("output", 0)

        if input_tokens < 0 or output_tokens < 0:
            raise ValueError(f"Token counts must be non-negative: {tokens}")

        rates = self._resolve_rates(provider, model)
        cost = (input_tokens / 1000.0) * rates["input"] + (output_tokens / 1000.0) * rates["output"]
        logger.debug(
            "Cost for %s/%s: %d in + %d out = $%.6f",
            provider, model, input_tokens, output_tokens, cost,
        )
        return cost

    def _resolve_rates(self, provider: str, model: str) -> Dict[str, float]:
        """Return per-1K-token rates for (provider, model), with fallback."""
        provider_rates = self._cost_rates.get(provider, {})
        if not provider_rates:
            logger.warning("Unknown provider '%s'; using fallback rates", provider)
            return FALLBACK_COST_RATES

        model_rates = provider_rates.get(model)
        if not model_rates:
            # Try partial match (e.g. 'claude-sonnet-4.6' -> 'claude-sonnet')
            for key, rates in provider_rates.items():
                if key in model or model in key:
                    logger.debug("Resolved '%s' -> '%s' via partial match", model, key)
                    return rates
            logger.warning(
                "Unknown model '%s' for provider '%s'; using fallback rates", model, provider
            )
            return FALLBACK_COST_RATES

        return model_rates

    def enforce_budget(
        self,
        session_id: str,
        task_cost: float,
        granularity: str = "session",
    ) -> bool:
        """
        Check whether a task costing *task_cost* USD is allowed under the budget.

        The spend is NOT recorded here — call record_spend() separately after
        the task completes so you don't pre-deduct.

        Args:
            session_id:  Session identifier.
            task_cost:   Estimated cost of the task in USD.
            granularity: Budget window to check.

        Returns:
            True  -> task is allowed.
            False -> task is blocked (hard limit would be reached or exceeded).

        Raises:
            ValueError: If task_cost is negative.
        """
        if task_cost < 0:
            raise ValueError(f"task_cost must be non-negative, got {task_cost}")

        budget = self.get_budget(session_id, granularity)
        projected = budget.current_spend + task_cost

        if projected > budget.limit_usd:
            if budget.hard_limit_action == "warn":
                logger.warning(
                    "Budget %s/%s would exceed limit (%.4f + %.4f > %.4f) - WARNING only",
                    session_id, granularity, budget.current_spend, task_cost, budget.limit_usd,
                )
                return True  # warn mode allows the task
            elif budget.hard_limit_action == "escalate":
                logger.critical(
                    "Budget %s/%s ESCALATION: %.4f + %.4f > %.4f",
                    session_id, granularity, budget.current_spend, task_cost, budget.limit_usd,
                )
                return False  # escalate also blocks
            else:  # 'block' (default)
                logger.warning(
                    "Budget %s/%s BLOCKED: %.4f + %.4f > %.4f",
                    session_id, granularity, budget.current_spend, task_cost, budget.limit_usd,
                )
                return False

        return True

    def alert_at_threshold(
        self,
        session_id: str,
        current_spend: float,
        limit: float,
        granularity: str = "session",
        suppress_duplicates: bool = True,
    ) -> str:
        """
        Check whether any alert threshold has been crossed and return an alert message.

        Thresholds are loaded from the stored budget.  Alerts that have already
        been fired are suppressed (no double-alert) when suppress_duplicates is True.

        Args:
            session_id:          Session identifier.
            current_spend:       Current total spend in USD.
            limit:               Budget limit in USD.
            granularity:         Budget window.
            suppress_duplicates: Skip thresholds already in alerts_fired.

        Returns:
            Alert message string, or "" if no new threshold crossed.
        """
        if limit <= 0:
            return ""

        pct = current_spend / limit  # fraction 0-inf
        budget = self.get_budget(session_id, granularity)
        alert_thresholds = sorted(budget.alert_thresholds, reverse=True)

        for threshold in alert_thresholds:
            if pct >= threshold:
                if suppress_duplicates and threshold in budget.alerts_fired:
                    continue
                # Record alert fired
                if suppress_duplicates:
                    budget.alerts_fired.append(threshold)
                    self._save(budget)

                label = int(threshold * 100)
                level = self.graceful_degrade(pct * 100)
                msg = (
                    f"[COST ALERT] {session_id}/{granularity}: "
                    f"{label}% threshold reached "
                    f"(spent ${current_spend:.4f} of ${limit:.4f}) - "
                    f"level={level}"
                )
                logger.warning(msg)
                return msg

        return ""

    def graceful_degrade(self, spend_percent: float) -> str:
        """
        Map spend percentage to a degradation level.

        Levels (all thresholds inclusive):
          0-49%   -> 'safe'
          50-74%  -> 'caution'
          75-89%  -> 'critical'
          90%+    -> 'blocked'

        Args:
            spend_percent: Current spend as a percentage of limit (0-inf).

        Returns:
            One of: 'safe', 'caution', 'critical', 'blocked'.
        """
        for threshold_pct, level in DEGRADATION_LEVELS:
            if spend_percent >= threshold_pct * 100:
                return level
        return "safe"

    def reset_expired_budgets(self, session_id: str) -> int:
        """
        Check all granularities for session_id and reset any expired windows.

        Returns:
            Number of budgets that were reset.
        """
        reset_count = 0
        for granularity in VALID_GRANULARITIES:
            path = self._budget_path(session_id, granularity)
            raw = self._load_raw(path)
            if raw is None:
                continue
            try:
                budget = CostBudget.from_dict(raw)
                if _is_expired(budget):
                    new_budget = CostBudget(
                        session_id=session_id,
                        granularity=granularity,
                        limit_usd=budget.limit_usd,
                        hard_limit_action=budget.hard_limit_action,
                        alert_thresholds=budget.alert_thresholds,
                        period_start=_window_start(granularity),
                    )
                    self._save(new_budget)
                    reset_count += 1
                    logger.info("Reset expired budget %s/%s", session_id, granularity)
            except Exception as exc:  # noqa: BLE001
                logger.error("Could not process %s/%s: %s", session_id, granularity, exc)

        return reset_count


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _cli() -> None:  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="Cost budgeting CLI")
    sub = parser.add_subparsers(dest="command")

    # status
    s = sub.add_parser("status", help="Show budget status")
    s.add_argument("--session", required=True)
    s.add_argument("--granularity", default="session")

    # spend
    sp = sub.add_parser("spend", help="Record a spend increment")
    sp.add_argument("--session", required=True)
    sp.add_argument("--amount", type=float, required=True)
    sp.add_argument("--granularity", default="session")
    sp.add_argument("--provider")

    # estimate
    e = sub.add_parser("estimate", help="Estimate task cost")
    e.add_argument("--provider", required=True)
    e.add_argument("--model", required=True)
    e.add_argument("--input", type=int, default=0, dest="input_tokens")
    e.add_argument("--output", type=int, default=0, dest="output_tokens")

    args = parser.parse_args()
    budgeter = CostBudgeter()

    if args.command == "status":
        b = budgeter.get_budget(args.session, args.granularity)
        print(json.dumps({
            "session_id": b.session_id,
            "granularity": b.granularity,
            "limit_usd": b.limit_usd,
            "current_spend": b.current_spend,
            "remaining_usd": b.remaining_usd,
            "spend_percent": round(b.spend_percent, 2),
            "level": budgeter.graceful_degrade(b.spend_percent),
        }, indent=2))

    elif args.command == "spend":
        b = budgeter.record_spend(args.session, args.amount, args.granularity, args.provider)
        print(f"Recorded ${args.amount:.6f}. Total: ${b.current_spend:.6f} / ${b.limit_usd:.6f}")

    elif args.command == "estimate":
        cost = budgeter.calculate_provider_cost(
            args.provider,
            {"input": args.input_tokens, "output": args.output_tokens},
            args.model,
        )
        print(f"Estimated cost: ${cost:.6f} USD")

    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()
