"""
Token Budget Manager for the Claude Code harness.

Per-agent token budget tracking for the session. Enforces allocation limits
and provides budget utilization reporting for cost control.

Usage::

    from src.harnesses.claude_code.token_budget import TokenBudgetManager

    manager = TokenBudgetManager(session_budget=200_000)
    status = manager.record_usage("orchestrator", 1500)
    print(status.percent, status.warn, status.blocked)

    summary = manager.session_summary()
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


# Per-agent token budget allocations (as fraction of session budget).
AGENT_ALLOCATIONS: Dict[str, float] = {
    "orchestrator": 0.60,
    "engineer": 0.18,
    "senior-engineer": 0.07,
    "lead-engineer": 0.05,
    "quality-engineer": 0.05,
    "principal-engineer": 0.03,
    "security-engineer": 0.01,
    "model-engineer": 0.01,
}

# Default session budget (tokens per session, from SPEC.md)
SESSION_BUDGET_DEFAULT = 200_000

# Threshold for warning log (85% utilization)
WARN_THRESHOLD = 0.85

# Threshold for blocking further tasks (100% utilization)
BLOCK_THRESHOLD = 1.00


@dataclass
class BudgetStatus:
    """Status of budget for a single agent."""

    agent: str
    used: int
    allocated: int
    percent: float
    warn: bool
    blocked: bool


class TokenBudgetManager:
    """Track per-agent token usage and enforce budget limits.

    Thread-safe via internal locking. Logs WARNING at 85% utilization
    and ERROR when budget is exhausted.

    Parameters
    ----------
    session_budget:
        Total token budget for the session (default: 200,000).
    allocations:
        Override the default per-agent allocations dict.
    """

    def __init__(
        self,
        session_budget: int = SESSION_BUDGET_DEFAULT,
        allocations: Optional[Dict[str, float]] = None,
    ) -> None:
        self._session_budget = session_budget
        self._allocations = (
            allocations if allocations is not None else dict(AGENT_ALLOCATIONS)
        )
        self._usage: Dict[str, int] = {
            agent: 0 for agent in self._allocations.keys()
        }
        self._lock = threading.Lock()

    def record_usage(self, agent: str, tokens: int) -> BudgetStatus:
        """Record token usage for an agent and return current status.

        Args:
            agent: Agent name.
            tokens: Number of tokens to record.

        Returns:
            BudgetStatus with current utilization and warn/blocked flags.
        """
        with self._lock:
            if agent not in self._usage:
                # Initialize unknown agent with zero allocation
                self._usage[agent] = 0

            self._usage[agent] += tokens
            status = self._compute_status(agent)

            # Log warnings and errors
            if status.blocked:
                logger.error(
                    "token_budget.exhausted",
                    extra={
                        "agent": agent,
                        "used": status.used,
                        "allocated": status.allocated,
                    },
                )
            elif status.warn:
                logger.warning(
                    "token_budget.warn_threshold",
                    extra={
                        "agent": agent,
                        "percent": status.percent,
                        "used": status.used,
                        "allocated": status.allocated,
                    },
                )

            return status

    def check_budget(self, agent: str) -> BudgetStatus:
        """Check current budget status for an agent without recording usage.

        Args:
            agent: Agent name.

        Returns:
            BudgetStatus with current utilization.
        """
        with self._lock:
            return self._compute_status(agent)

    def session_summary(self) -> Dict[str, Any]:
        """Return aggregate session budget utilization summary.

        Returns:
            Dictionary with total used, per-agent breakdown, and
            utilization percentage.
        """
        with self._lock:
            total_used = sum(self._usage.values())
            total_allocated = self._session_budget

            per_agent = {}
            for agent, used in self._usage.items():
                allocated = int(
                    self._allocations.get(agent, 0) * total_allocated
                )
                percent = (used / allocated * 100) if allocated > 0 else 0.0
                per_agent[agent] = {
                    "used": used,
                    "allocated": allocated,
                    "percent": percent,
                }

            return {
                "total_used": total_used,
                "total_allocated": total_allocated,
                "utilization_percent": (
                    (total_used / total_allocated * 100)
                    if total_allocated > 0
                    else 0.0
                ),
                "per_agent": per_agent,
            }

    def reset(self) -> None:
        """Clear all recorded usage for the session."""
        with self._lock:
            for agent in self._usage:
                self._usage[agent] = 0
            logger.info("token_budget.reset")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_status(self, agent: str) -> BudgetStatus:
        """Compute budget status for an agent (internal, assumes lock held)."""
        used = self._usage.get(agent, 0)
        agent_fraction = self._allocations.get(agent, 0.0)
        allocated = int(agent_fraction * self._session_budget)

        if allocated == 0:
            percent = 0.0
        else:
            percent = used / allocated

        warn = percent >= WARN_THRESHOLD
        blocked = percent >= BLOCK_THRESHOLD

        return BudgetStatus(
            agent=agent,
            used=used,
            allocated=allocated,
            percent=percent,
            warn=warn,
            blocked=blocked,
        )
