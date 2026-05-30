# -*- coding: utf-8 -*-
"""
CostBudget — Multi-level budget tracking with hard enforcement.

This module provides comprehensive budget management with:
- 5 budget levels: session, hourly, daily, weekly, monthly
- Hard enforcement at 100% utilization (operations blocked)
- Atomic transaction rollback on budget violation
- Alert thresholds at 75% (warning) and 100% (block)
- Thread-safe concurrent operation support
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta
import threading
from contextlib import contextmanager


# ============================================================================
# Enums and Constants
# ============================================================================

class AlertLevel(Enum):
    """Budget alert severity levels."""
    OK = "ok"
    WARNING = "warning"  # At 75% utilization
    CRITICAL = "critical"  # At 90% utilization
    BLOCKED = "blocked"  # At 100% utilization


class BudgetPeriod(Enum):
    """Budget reset periods."""
    SESSION = "session"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# Alert thresholds as percentage of budget
ALERT_THRESHOLDS = {
    AlertLevel.OK: 0.0,
    AlertLevel.WARNING: 75.0,
    AlertLevel.CRITICAL: 90.0,
    AlertLevel.BLOCKED: 100.0,
}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class BudgetStatus:
    """Status of a budget level."""
    period: BudgetPeriod
    budget_limit: float
    spent: float
    utilization_pct: float
    remaining: float
    alert_level: AlertLevel
    message: str
    can_proceed: bool

    def __str__(self) -> str:
        """User-friendly string representation."""
        status_symbol = {
            AlertLevel.OK: "✓",
            AlertLevel.WARNING: "⚠",
            AlertLevel.CRITICAL: "⚠⚠",
            AlertLevel.BLOCKED: "✕",
        }[self.alert_level]

        return (
            f"{status_symbol} {self.period.value.upper():8s} | "
            f"${self.spent:7.2f} / ${self.budget_limit:7.2f} "
            f"({self.utilization_pct:5.1f}%) | "
            f"${self.remaining:6.2f} remaining"
        )


@dataclass
class OperationResult:
    """Result of a budget operation check."""
    can_proceed: bool
    message: str
    limiting_period: Optional[BudgetPeriod] = None
    estimated_utilization_pct: float = 0.0
    alert_level: AlertLevel = AlertLevel.OK

    def __str__(self) -> str:
        """User-friendly string representation."""
        return self.message


@dataclass
class BudgetLevel:
    """A single budget constraint at one time period."""
    period: BudgetPeriod
    limit: float
    spent: float = 0.0
    last_reset: datetime = field(default_factory=datetime.now)

    def utilization_pct(self) -> float:
        """Return utilization as percentage (0-100+)."""
        if self.limit == 0:
            return 0.0 if self.spent == 0 else 100.0
        return (self.spent / self.limit) * 100.0

    def remaining(self) -> float:
        """Return remaining budget (clamped to 0)."""
        return max(0.0, self.limit - self.spent)

    def has_capacity(self, amount: float) -> bool:
        """Check if budget can accommodate the amount."""
        return (self.spent + amount) <= self.limit

    def add_spend(self, amount: float) -> None:
        """Add to spent amount (does not check capacity)."""
        if amount < 0:
            raise ValueError(f"Spend amount must be non-negative, got {amount}")
        self.spent += amount

    def subtract_spend(self, amount: float) -> None:
        """Subtract from spent amount (for rollback)."""
        if amount < 0:
            raise ValueError(f"Refund amount must be non-negative, got {amount}")
        self.spent = max(0.0, self.spent - amount)

    def reset_if_needed(self) -> bool:
        """Reset budget if period has elapsed. Returns True if reset."""
        now = datetime.now()

        # Determine if we need to reset based on period
        should_reset = False
        next_reset = self.last_reset

        if self.period == BudgetPeriod.SESSION:
            should_reset = False  # Session budgets never auto-reset
        elif self.period == BudgetPeriod.HOURLY:
            next_reset = self.last_reset + timedelta(hours=1)
            should_reset = now >= next_reset
        elif self.period == BudgetPeriod.DAILY:
            next_reset = self.last_reset + timedelta(days=1)
            should_reset = now >= next_reset
        elif self.period == BudgetPeriod.WEEKLY:
            next_reset = self.last_reset + timedelta(weeks=1)
            should_reset = now >= next_reset
        elif self.period == BudgetPeriod.MONTHLY:
            # For monthly, advance by day-of-month
            year = self.last_reset.year
            month = self.last_reset.month
            day = self.last_reset.day

            try:
                next_reset = self.last_reset.replace(year=year, month=month + 1, day=day)
            except ValueError:
                # Handle month overflow (e.g., Jan 31 -> Feb 31)
                if month == 12:
                    next_reset = self.last_reset.replace(year=year + 1, month=1, day=day)
                else:
                    # Use last day of next month
                    next_month_first = self.last_reset.replace(month=month + 1, day=1)
                    next_reset = next_month_first + timedelta(days=-1)

            should_reset = now >= next_reset

        if should_reset:
            self.spent = 0.0
            self.last_reset = now
            return True

        return False

    def alert_level(self) -> AlertLevel:
        """Determine current alert level based on utilization."""
        util = self.utilization_pct()

        if util >= 100.0:
            return AlertLevel.BLOCKED
        elif util >= 90.0:
            return AlertLevel.CRITICAL
        elif util >= 75.0:
            return AlertLevel.WARNING
        else:
            return AlertLevel.OK

    def get_status(self) -> BudgetStatus:
        """Get current status of this budget level."""
        util = self.utilization_pct()
        alert = self.alert_level()

        # Build message
        if alert == AlertLevel.BLOCKED:
            message = f"{self.period.value} budget exhausted"
        elif alert == AlertLevel.CRITICAL:
            message = f"{self.period.value} budget critical (90%+)"
        elif alert == AlertLevel.WARNING:
            message = f"{self.period.value} budget warning (75%+)"
        else:
            message = f"{self.period.value} budget OK"

        return BudgetStatus(
            period=self.period,
            budget_limit=self.limit,
            spent=self.spent,
            utilization_pct=util,
            remaining=self.remaining(),
            alert_level=alert,
            message=message,
            can_proceed=(alert != AlertLevel.BLOCKED),
        )


# ============================================================================
# Transaction Support
# ============================================================================

@dataclass
class TransactionContext:
    """Context manager for atomic budget transactions."""
    budget: CostBudget
    amount: float
    rolled_back: bool = False

    def rollback(self) -> None:
        """Explicitly rollback this transaction."""
        if not self.rolled_back:
            self.budget._subtract_all_levels(self.amount)
            self.rolled_back = True

    def __enter__(self) -> TransactionContext:
        """Enter context; amount already deducted in __init__."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context; rollback if exception or explicit rollback."""
        if exc_type is not None or self.rolled_back:
            self.rollback()
        return False


# ============================================================================
# CostBudget — Main Class
# ============================================================================

class CostBudget:
    """
    Multi-level budget tracker with hard enforcement.

    Tracks spending across 5 time periods simultaneously:
    - session: One-time per session limit
    - hourly: Reset every hour
    - daily: Reset every day
    - weekly: Reset every week
    - monthly: Reset every month

    Operations are blocked at 100% utilization. Alerts at 75% (warning) and
    90% (critical). All operations are thread-safe.
    """

    def __init__(
        self,
        session_budget: float = float("inf"),
        hour_budget: float = float("inf"),
        day_budget: float = float("inf"),
        week_budget: float = float("inf"),
        month_budget: float = float("inf"),
    ):
        """
        Initialize CostBudget with per-period limits.

        Args:
            session_budget: Maximum spend for entire session
            hour_budget: Maximum spend per hour
            day_budget: Maximum spend per day
            week_budget: Maximum spend per week
            month_budget: Maximum spend per month

        Raises:
            ValueError: If any budget is negative
        """
        self._validate_budgets(
            session_budget, hour_budget, day_budget, week_budget, month_budget
        )

        self._levels: Dict[BudgetPeriod, BudgetLevel] = {
            BudgetPeriod.SESSION: BudgetLevel(BudgetPeriod.SESSION, session_budget),
            BudgetPeriod.HOURLY: BudgetLevel(BudgetPeriod.HOURLY, hour_budget),
            BudgetPeriod.DAILY: BudgetLevel(BudgetPeriod.DAILY, day_budget),
            BudgetPeriod.WEEKLY: BudgetLevel(BudgetPeriod.WEEKLY, week_budget),
            BudgetPeriod.MONTHLY: BudgetLevel(BudgetPeriod.MONTHLY, month_budget),
        }

        self._lock = threading.RLock()
        self._operation_history: List[Tuple[float, datetime, bool]] = []

    # ========================================================================
    # Validation
    # ========================================================================

    @staticmethod
    def _validate_budgets(session: float, hour: float, day: float, week: float, month: float) -> None:
        """Validate that all budgets are non-negative."""
        for name, val in [
            ("session", session),
            ("hour", hour),
            ("day", day),
            ("week", week),
            ("month", month),
        ]:
            if val < 0:
                raise ValueError(f"Budget {name} cannot be negative: {val}")

    # ========================================================================
    # Core Operations
    # ========================================================================

    def check_operation(self, amount: float) -> OperationResult:
        """Check if an operation of the given cost can proceed."""
        if amount < 0 or amount != amount:  # NaN check
            raise ValueError(f"Invalid operation cost: {amount}")

        with self._lock:
            self._refresh_all_periods()

            # Check each level
            blocking_level = None
            for period in BudgetPeriod:
                level = self._levels[period]
                if not level.has_capacity(amount):
                    blocking_level = period
                    break

            if blocking_level:
                level = self._levels[blocking_level]
                util_after = ((level.spent + amount) / level.limit * 100) if level.limit > 0 else 100.0
                return OperationResult(
                    can_proceed=False,
                    message=f"Operation blocked: {blocking_level.value} budget exhausted "
                    f"({level.utilization_pct():.1f}% + {amount} would exceed limit)",
                    limiting_period=blocking_level,
                    estimated_utilization_pct=util_after,
                    alert_level=AlertLevel.BLOCKED,
                )

            # All levels have capacity
            return OperationResult(
                can_proceed=True,
                message="Operation can proceed",
                alert_level=AlertLevel.OK,
            )

    def record_spend(self, amount: float) -> BudgetStatus:
        """Record a spend against all budget levels."""
        if amount < 0 or amount != amount:
            raise ValueError(f"Invalid spend amount: {amount}")

        with self._lock:
            self._refresh_all_periods()

            # Verify all levels can still accommodate
            for level in self._levels.values():
                if not level.has_capacity(amount):
                    raise RuntimeError(
                        f"Cannot record spend: {level.period.value} budget already exhausted"
                    )

            # Record against all levels
            self._add_all_levels(amount)

            # Track in history
            self._operation_history.append((amount, datetime.now(), True))

            # Return status of most restrictive level
            return self._get_most_restrictive_status()

    def _add_all_levels(self, amount: float) -> None:
        """Add spend to all budget levels (internal, no lock)."""
        for level in self._levels.values():
            level.add_spend(amount)

    def _subtract_all_levels(self, amount: float) -> None:
        """Subtract spend from all budget levels for rollback (internal, no lock)."""
        for level in self._levels.values():
            level.subtract_spend(amount)

    @contextmanager
    def transaction(self, amount: float) -> TransactionContext:
        """Execute an operation with automatic transaction rollback on error."""
        # Check before proceeding
        check = self.check_operation(amount)
        if not check.can_proceed:
            raise RuntimeError(
                f"Transaction blocked: {check.message}"
            )

        with self._lock:
            self._refresh_all_periods()
            # Pre-deduct from all levels
            self._add_all_levels(amount)

        txn = TransactionContext(self, amount)
        try:
            yield txn
        except Exception:
            txn.rollback()
            raise

    # ========================================================================
    # Status and Metrics
    # ========================================================================

    def status(self, period: Optional[BudgetPeriod] = None) -> dict:
        """Get status of one or all budget levels."""
        with self._lock:
            self._refresh_all_periods()

            if period:
                if period not in self._levels:
                    raise ValueError(f"Unknown period: {period}")
                return self._levels[period].get_status()

            return {p.value: self._levels[p].get_status() for p in BudgetPeriod}

    def utilization(self) -> Dict[str, float]:
        """Get utilization percentages for all periods."""
        with self._lock:
            self._refresh_all_periods()
            return {p.value: self._levels[p].utilization_pct() for p in BudgetPeriod}

    def alert_level(self) -> AlertLevel:
        """Get the most severe alert level across all budget periods."""
        with self._lock:
            self._refresh_all_periods()

            levels = [level.alert_level() for level in self._levels.values()]

            # Return most severe
            if AlertLevel.BLOCKED in levels:
                return AlertLevel.BLOCKED
            elif AlertLevel.CRITICAL in levels:
                return AlertLevel.CRITICAL
            elif AlertLevel.WARNING in levels:
                return AlertLevel.WARNING
            else:
                return AlertLevel.OK

    def remaining_budget(self, period: Optional[BudgetPeriod] = None) -> dict:
        """Get remaining budget for one or all periods."""
        with self._lock:
            self._refresh_all_periods()

            if period:
                if period not in self._levels:
                    raise ValueError(f"Unknown period: {period}")
                return self._levels[period].remaining()

            return {p.value: self._levels[p].remaining() for p in BudgetPeriod}

    def _get_most_restrictive_status(self) -> BudgetStatus:
        """Get status of the level with lowest remaining budget."""
        statuses = [self._levels[p].get_status() for p in BudgetPeriod]
        return min(statuses, key=lambda s: s.remaining)

    # ========================================================================
    # Reset and Maintenance
    # ========================================================================

    def _refresh_all_periods(self) -> None:
        """Refresh all budget periods (auto-reset if needed). Internal, no lock."""
        for level in self._levels.values():
            level.reset_if_needed()

    def reset_period(self, period: BudgetPeriod) -> None:
        """Manually reset a specific budget period."""
        if period == BudgetPeriod.SESSION:
            raise ValueError("Cannot manually reset SESSION budget")

        with self._lock:
            if period not in self._levels:
                raise ValueError(f"Unknown period: {period}")

            level = self._levels[period]
            level.spent = 0.0
            level.last_reset = datetime.now()

    def reset_all(self) -> None:
        """Reset all non-session budgets (for testing/maintenance)."""
        with self._lock:
            for period in [BudgetPeriod.HOURLY, BudgetPeriod.DAILY, BudgetPeriod.WEEKLY, BudgetPeriod.MONTHLY]:
                self._levels[period].spent = 0.0
                self._levels[period].last_reset = datetime.now()

    # ========================================================================
    # Configuration Access
    # ========================================================================

    def get_limits(self) -> Dict[str, float]:
        """Get all budget limits."""
        with self._lock:
            return {p.value: self._levels[p].limit for p in BudgetPeriod}

    def set_limits(
        self,
        session_budget: Optional[float] = None,
        hour_budget: Optional[float] = None,
        day_budget: Optional[float] = None,
        week_budget: Optional[float] = None,
        month_budget: Optional[float] = None,
    ) -> None:
        """Update budget limits."""
        updates = {
            BudgetPeriod.SESSION: session_budget,
            BudgetPeriod.HOURLY: hour_budget,
            BudgetPeriod.DAILY: day_budget,
            BudgetPeriod.WEEKLY: week_budget,
            BudgetPeriod.MONTHLY: month_budget,
        }

        with self._lock:
            for period, limit in updates.items():
                if limit is not None:
                    if limit < 0:
                        raise ValueError(f"Budget {period.value} cannot be negative: {limit}")
                    self._levels[period].limit = limit

    # ========================================================================
    # Testing Utilities
    # ========================================================================

    def _get_operation_history(self) -> List[Tuple[float, datetime, bool]]:
        """Get operation history for testing."""
        with self._lock:
            return list(self._operation_history)

    def _clear_history(self) -> None:
        """Clear operation history (for testing)."""
        with self._lock:
            self._operation_history.clear()
            self.reset_all()
