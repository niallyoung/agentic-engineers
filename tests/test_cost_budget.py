# -*- coding: utf-8 -*-
"""
Test suite for CostBudget — Multi-level budget tracking with hard enforcement.

Comprehensive coverage of:
- Budget initialization and validation
- Multi-level tracking (all 5 budget types)
- Hard block at 100% utilization
- Budget reset logic (hourly, daily, weekly, monthly)
- Transaction support and rollback
- Alert thresholds
- Edge cases (concurrent requests, budget overflow)
- Thread safety

≥25 tests covering all major functionality.
"""

import pytest
from datetime import datetime, timedelta
import threading
import time
from unittest.mock import patch

from src.orchestration.cost.budget import (
    CostBudget,
    BudgetLevel,
    BudgetStatus,
    BudgetPeriod,
    AlertLevel,
    OperationResult,
    TransactionContext,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def basic_budget():
    """Create a basic budget for testing."""
    return CostBudget(
        session_budget=100.0,
        hour_budget=10.0,
        day_budget=50.0,
        week_budget=300.0,
        month_budget=1000.0,
    )


@pytest.fixture
def unlimited_budget():
    """Create a budget with unlimited limits."""
    return CostBudget()


@pytest.fixture
def tight_budget():
    """Create a budget with tight limits (for easy overflow testing)."""
    return CostBudget(
        session_budget=5.0,
        hour_budget=1.0,
        day_budget=5.0,
        week_budget=10.0,
        month_budget=20.0,
    )


# ============================================================================
# Test Initialization and Validation
# ============================================================================

class TestBudgetInitialization:
    """Test budget initialization and validation."""

    def test_budget_initialization_with_custom_limits(self):
        """Test creating a budget with custom limits."""
        budget = CostBudget(
            session_budget=100.0,
            hour_budget=10.0,
            day_budget=50.0,
            week_budget=300.0,
            month_budget=1000.0,
        )
        assert budget is not None

    def test_budget_initialization_with_defaults(self):
        """Test creating a budget with default unlimited limits."""
        budget = CostBudget()
        limits = budget.get_limits()
        assert all(v == float("inf") for v in limits.values())

    def test_budget_initialization_with_zero_budgets(self):
        """Test creating budget with zero limits."""
        budget = CostBudget(session_budget=0.0, day_budget=0.0)
        limits = budget.get_limits()
        assert limits["session"] == 0.0
        assert limits["daily"] == 0.0

    def test_budget_initialization_rejects_negative_session(self):
        """Test that negative session budget raises ValueError."""
        with pytest.raises(ValueError, match="session"):
            CostBudget(session_budget=-10.0)

    def test_budget_initialization_rejects_negative_hour(self):
        """Test that negative hour budget raises ValueError."""
        with pytest.raises(ValueError, match="hour"):
            CostBudget(hour_budget=-5.0)

    def test_budget_initialization_rejects_negative_day(self):
        """Test that negative day budget raises ValueError."""
        with pytest.raises(ValueError, match="day"):
            CostBudget(day_budget=-50.0)

    def test_budget_initialization_rejects_negative_week(self):
        """Test that negative week budget raises ValueError."""
        with pytest.raises(ValueError, match="week"):
            CostBudget(week_budget=-100.0)

    def test_budget_initialization_rejects_negative_month(self):
        """Test that negative month budget raises ValueError."""
        with pytest.raises(ValueError, match="month"):
            CostBudget(month_budget=-500.0)


# ============================================================================
# Test Budget Checking (check_operation)
# ============================================================================

class TestBudgetChecking:
    """Test checking if operations can proceed."""

    def test_check_operation_allowed_within_all_limits(self, basic_budget):
        """Test check_operation returns can_proceed=True when within all limits."""
        result = basic_budget.check_operation(1.0)
        assert result.can_proceed is True
        assert result.alert_level == AlertLevel.OK

    def test_check_operation_rejects_negative_amount(self, basic_budget):
        """Test check_operation rejects negative amounts."""
        with pytest.raises(ValueError):
            basic_budget.check_operation(-1.0)

    def test_check_operation_rejects_nan(self, basic_budget):
        """Test check_operation rejects NaN."""
        with pytest.raises(ValueError):
            basic_budget.check_operation(float("nan"))

    def test_check_operation_blocks_at_session_limit(self, basic_budget):
        """Test check_operation blocks when session budget would be exceeded."""
        # Use 98 out of 100 session budget without exceeding hourly/daily
        # Use small amounts (2.0) with hourly/daily resets: 2.0 * 49 = 98
        for _ in range(49):
            basic_budget.record_spend(2.0)
            basic_budget.reset_period(BudgetPeriod.HOURLY)
            basic_budget.reset_period(BudgetPeriod.DAILY)

        # Now session is at 98.0, so 3.0 would exceed it
        result = basic_budget.check_operation(3.0)
        assert result.can_proceed is False
        assert result.limiting_period == BudgetPeriod.SESSION

    def test_check_operation_blocks_at_hour_limit(self, basic_budget):
        """Test check_operation blocks when hour budget would be exceeded."""
        # Use up most of hourly budget
        basic_budget.record_spend(9.9)

        result = basic_budget.check_operation(0.2)
        assert result.can_proceed is False
        assert result.limiting_period == BudgetPeriod.HOURLY

    def test_check_operation_allows_exact_remaining(self, basic_budget):
        """Test check_operation allows spending exact remaining amount."""
        basic_budget.record_spend(9.0)

        result = basic_budget.check_operation(1.0)  # Exact hour budget remaining
        assert result.can_proceed is True

    def test_check_operation_does_not_modify_budget(self, basic_budget):
        """Test check_operation does not modify budget state."""
        initial_util = basic_budget.utilization()

        basic_budget.check_operation(5.0)
        basic_budget.check_operation(10.0)

        after_util = basic_budget.utilization()
        assert initial_util == after_util


# ============================================================================
# Test Spending (record_spend)
# ============================================================================

class TestRecordSpend:
    """Test recording spending against budgets."""

    def test_record_spend_updates_all_levels(self, basic_budget):
        """Test that record_spend updates all budget levels."""
        basic_budget.record_spend(5.0)

        util = basic_budget.utilization()
        # All levels should show 5.0 spent
        assert util["session"] == pytest.approx((5.0 / 100.0) * 100)
        assert util["hourly"] == pytest.approx((5.0 / 10.0) * 100)
        assert util["daily"] == pytest.approx((5.0 / 50.0) * 100)

    def test_record_spend_rejects_negative(self, basic_budget):
        """Test that record_spend rejects negative amounts."""
        with pytest.raises(ValueError):
            basic_budget.record_spend(-1.0)

    def test_record_spend_rejects_nan(self, basic_budget):
        """Test that record_spend rejects NaN."""
        with pytest.raises(ValueError):
            basic_budget.record_spend(float("nan"))

    def test_record_spend_raises_if_over_capacity(self, basic_budget):
        """Test that record_spend raises if budget already exceeded."""
        basic_budget.record_spend(9.9)

        with pytest.raises(RuntimeError):
            basic_budget.record_spend(1.0)

    def test_record_spend_accumulates(self, basic_budget):
        """Test that multiple record_spend calls accumulate."""
        basic_budget.record_spend(2.0)
        basic_budget.record_spend(3.0)

        util = basic_budget.utilization()
        assert util["hourly"] == pytest.approx(50.0)  # 5/10

    def test_record_spend_returns_status(self, basic_budget):
        """Test that record_spend returns BudgetStatus."""
        status = basic_budget.record_spend(5.0)
        assert isinstance(status, BudgetStatus)


# ============================================================================
# Test Alert Levels
# ============================================================================

class TestAlertLevels:
    """Test alert level calculation."""

    def test_alert_level_ok(self, basic_budget):
        """Test OK alert level at low utilization."""
        basic_budget.record_spend(1.0)  # 2% of hour budget
        assert basic_budget.alert_level() == AlertLevel.OK

    def test_alert_level_warning_at_75_percent(self, basic_budget):
        """Test WARNING alert at 75% utilization."""
        basic_budget.record_spend(7.5)  # 75% of hour budget
        assert basic_budget.alert_level() == AlertLevel.WARNING

    def test_alert_level_critical_at_90_percent(self, basic_budget):
        """Test CRITICAL alert at 90% utilization."""
        basic_budget.record_spend(9.0)  # 90% of hour budget
        assert basic_budget.alert_level() == AlertLevel.CRITICAL

    def test_alert_level_blocked_at_100_percent(self, basic_budget):
        """Test BLOCKED alert at 100% utilization."""
        basic_budget.record_spend(10.0)  # 100% of hour budget
        assert basic_budget.alert_level() == AlertLevel.BLOCKED

    def test_alert_level_most_severe(self, basic_budget):
        """Test that alert_level returns most severe across all periods."""
        # Use 90% of hour budget (most restrictive is 9.0 out of 10)
        basic_budget.record_spend(9.0)
        assert basic_budget.alert_level() == AlertLevel.CRITICAL


# ============================================================================
# Test Transaction Support
# ============================================================================

class TestTransactions:
    """Test transaction context manager and rollback."""

    def test_transaction_succeeds_and_records_spend(self, basic_budget):
        """Test successful transaction records spend."""
        initial_session = basic_budget.utilization()["session"]

        with basic_budget.transaction(5.0):
            pass  # Successful completion

        final_session = basic_budget.utilization()["session"]
        assert final_session > initial_session

    def test_transaction_rolls_back_on_exception(self, basic_budget):
        """Test transaction rolls back on exception."""
        initial_session = basic_budget.utilization()["session"]

        with pytest.raises(ValueError):
            with basic_budget.transaction(5.0):
                raise ValueError("Operation failed")

        final_session = basic_budget.utilization()["session"]
        assert final_session == initial_session

    def test_transaction_rolls_back_on_explicit_call(self, basic_budget):
        """Test transaction can be explicitly rolled back."""
        initial_session = basic_budget.utilization()["session"]

        with basic_budget.transaction(5.0) as txn:
            txn.rollback()

        final_session = basic_budget.utilization()["session"]
        assert final_session == initial_session

    def test_transaction_blocks_if_over_budget(self, basic_budget):
        """Test transaction raises if operation would exceed budget."""
        basic_budget.record_spend(9.9)

        with pytest.raises(RuntimeError, match="blocked"):
            with basic_budget.transaction(0.2):
                pass

    def test_transaction_multiple_rollbacks_are_idempotent(self, basic_budget):
        """Test multiple rollbacks don't double-refund."""
        initial_session = basic_budget.utilization()["session"]

        with basic_budget.transaction(5.0) as txn:
            txn.rollback()
            txn.rollback()  # Second rollback should be no-op

        final_session = basic_budget.utilization()["session"]
        assert final_session == initial_session


# ============================================================================
# Test Budget Reset Logic
# ============================================================================

class TestBudgetReset:
    """Test automatic and manual budget reset."""

    def test_manual_reset_of_daily_budget(self, basic_budget):
        """Test manually resetting daily budget."""
        basic_budget.record_spend(5.0)
        assert basic_budget.utilization()["daily"] == pytest.approx(10.0)

        basic_budget.reset_period(BudgetPeriod.DAILY)
        assert basic_budget.utilization()["daily"] == 0.0

    def test_manual_reset_of_weekly_budget(self, basic_budget):
        """Test manually resetting weekly budget."""
        basic_budget.record_spend(10.0)
        assert basic_budget.utilization()["weekly"] > 0

        basic_budget.reset_period(BudgetPeriod.WEEKLY)
        assert basic_budget.utilization()["weekly"] == 0.0

    def test_reset_period_rejects_session(self, basic_budget):
        """Test that reset_period rejects SESSION budget."""
        with pytest.raises(ValueError, match="SESSION"):
            basic_budget.reset_period(BudgetPeriod.SESSION)

    def test_reset_all_resets_all_periods_except_session(self, basic_budget):
        """Test reset_all resets all except session."""
        basic_budget.record_spend(5.0)

        # Verify all periods have spending
        util_before = basic_budget.utilization()
        assert all(u > 0 for u in util_before.values())

        basic_budget.reset_all()

        # All non-session levels should be reset to 0
        util_after = basic_budget.utilization()
        assert util_after["hourly"] == 0.0
        assert util_after["daily"] == 0.0
        assert util_after["weekly"] == 0.0
        assert util_after["monthly"] == 0.0
        # Session is NOT reset by reset_all() (it's persistent per session)
        assert util_after["session"] == pytest.approx(5.0)


# ============================================================================
# Test Status Queries
# ============================================================================

class TestStatusQueries:
    """Test querying budget status."""

    def test_status_all_periods(self, basic_budget):
        """Test status() returns all periods when period=None."""
        basic_budget.record_spend(5.0)
        statuses = basic_budget.status()

        assert isinstance(statuses, dict)
        assert len(statuses) == 5
        assert all(p.value in statuses for p in BudgetPeriod)

    def test_status_single_period(self, basic_budget):
        """Test status() returns single period when specified."""
        basic_budget.record_spend(5.0)
        status = basic_budget.status(BudgetPeriod.DAILY)

        assert isinstance(status, BudgetStatus)
        assert status.period == BudgetPeriod.DAILY

    def test_utilization_all_periods(self, basic_budget):
        """Test utilization() returns all periods."""
        basic_budget.record_spend(5.0)
        util = basic_budget.utilization()

        assert isinstance(util, dict)
        assert len(util) == 5
        assert all(0 <= v <= 100 for v in util.values())

    def test_remaining_budget_all_periods(self, basic_budget):
        """Test remaining_budget() returns all periods."""
        basic_budget.record_spend(5.0)
        remaining = basic_budget.remaining_budget()

        assert isinstance(remaining, dict)
        assert remaining["session"] == pytest.approx(95.0)
        assert remaining["hourly"] == pytest.approx(5.0)

    def test_remaining_budget_single_period(self, basic_budget):
        """Test remaining_budget() returns single period."""
        basic_budget.record_spend(5.0)
        remaining = basic_budget.remaining_budget(BudgetPeriod.DAILY)

        assert isinstance(remaining, float)
        assert remaining == pytest.approx(45.0)


# ============================================================================
# Test Budget Level Class
# ============================================================================

class TestBudgetLevel:
    """Test individual BudgetLevel functionality."""

    def test_budget_level_creation(self):
        """Test creating a BudgetLevel."""
        level = BudgetLevel(BudgetPeriod.DAILY, 50.0)
        assert level.period == BudgetPeriod.DAILY
        assert level.limit == 50.0
        assert level.spent == 0.0

    def test_budget_level_utilization_percentage(self):
        """Test utilization calculation."""
        level = BudgetLevel(BudgetPeriod.DAILY, 50.0)
        level.add_spend(25.0)

        assert level.utilization_pct() == 50.0

    def test_budget_level_remaining(self):
        """Test remaining budget calculation."""
        level = BudgetLevel(BudgetPeriod.DAILY, 50.0)
        level.add_spend(20.0)

        assert level.remaining() == 30.0

    def test_budget_level_has_capacity(self):
        """Test capacity checking."""
        level = BudgetLevel(BudgetPeriod.DAILY, 50.0)
        level.add_spend(40.0)

        assert level.has_capacity(10.0) is True
        assert level.has_capacity(11.0) is False

    def test_budget_level_add_spend(self):
        """Test adding spend."""
        level = BudgetLevel(BudgetPeriod.DAILY, 50.0)
        level.add_spend(10.0)
        level.add_spend(20.0)

        assert level.spent == 30.0

    def test_budget_level_subtract_spend(self):
        """Test subtracting spend (rollback)."""
        level = BudgetLevel(BudgetPeriod.DAILY, 50.0)
        level.add_spend(30.0)
        level.subtract_spend(10.0)

        assert level.spent == 20.0

    def test_budget_level_subtract_spend_never_goes_negative(self):
        """Test that subtract_spend doesn't make spent negative."""
        level = BudgetLevel(BudgetPeriod.DAILY, 50.0)
        level.add_spend(5.0)
        level.subtract_spend(20.0)

        assert level.spent == 0.0

    def test_budget_level_alert_level_ok(self):
        """Test alert level calculation for OK."""
        level = BudgetLevel(BudgetPeriod.DAILY, 50.0)
        level.add_spend(20.0)

        assert level.alert_level() == AlertLevel.OK

    def test_budget_level_alert_level_warning(self):
        """Test alert level calculation for WARNING."""
        level = BudgetLevel(BudgetPeriod.DAILY, 50.0)
        level.add_spend(37.5)  # 75%

        assert level.alert_level() == AlertLevel.WARNING

    def test_budget_level_alert_level_critical(self):
        """Test alert level calculation for CRITICAL."""
        level = BudgetLevel(BudgetPeriod.DAILY, 50.0)
        level.add_spend(45.0)  # 90%

        assert level.alert_level() == AlertLevel.CRITICAL

    def test_budget_level_alert_level_blocked(self):
        """Test alert level calculation for BLOCKED."""
        level = BudgetLevel(BudgetPeriod.DAILY, 50.0)
        level.add_spend(50.0)  # 100%

        assert level.alert_level() == AlertLevel.BLOCKED


# ============================================================================
# Test Edge Cases and Boundary Conditions
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_budget_blocks_immediately(self):
        """Test that zero budget blocks any operation."""
        budget = CostBudget(session_budget=0.0)
        result = budget.check_operation(0.01)
        assert result.can_proceed is False

    def test_very_small_amounts(self, basic_budget):
        """Test handling of very small spend amounts."""
        result = basic_budget.check_operation(0.0001)
        assert result.can_proceed is True

        status = basic_budget.record_spend(0.0001)
        assert isinstance(status, BudgetStatus)

    def test_very_large_amounts_blocked(self, basic_budget):
        """Test that very large amounts are blocked."""
        result = basic_budget.check_operation(1000.0)
        assert result.can_proceed is False

    def test_unlimited_budget_never_blocks(self, unlimited_budget):
        """Test that unlimited budget allows any operation."""
        for amount in [1.0, 100.0, 1000.0, 10000.0]:
            result = unlimited_budget.check_operation(amount)
            assert result.can_proceed is True

    def test_budget_limits_can_be_updated(self, basic_budget):
        """Test that budget limits can be updated."""
        basic_budget.set_limits(session_budget=50.0, day_budget=25.0)
        limits = basic_budget.get_limits()

        assert limits["session"] == 50.0
        assert limits["daily"] == 25.0

    def test_updating_limits_rejects_negative(self, basic_budget):
        """Test that updating limits rejects negative values."""
        with pytest.raises(ValueError):
            basic_budget.set_limits(session_budget=-10.0)


# ============================================================================
# Test Thread Safety
# ============================================================================

class TestThreadSafety:
    """Test concurrent/thread-safe operations."""

    def test_concurrent_check_operations(self, basic_budget):
        """Test multiple threads checking operations concurrently."""
        results = []
        errors = []

        def check_op():
            try:
                result = basic_budget.check_operation(1.0)
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=check_op) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 10

    def test_concurrent_spend_recording(self, basic_budget):
        """Test multiple threads recording spend concurrently."""
        errors = []

        def record_spend():
            try:
                basic_budget.record_spend(1.0)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_spend) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # Total spend should be 5.0
        assert basic_budget.utilization()["session"] == pytest.approx(5.0 / 100.0 * 100)


# ============================================================================
# Test Documentation and Type Hints
# ============================================================================

class TestDocumentation:
    """Test that code has proper documentation."""

    def test_cost_budget_class_has_docstring(self):
        """Test CostBudget has comprehensive docstring."""
        assert CostBudget.__doc__ is not None
        assert len(CostBudget.__doc__) > 50

    def test_check_operation_method_has_docstring(self):
        """Test check_operation has docstring."""
        assert CostBudget.check_operation.__doc__ is not None

    def test_record_spend_method_has_docstring(self):
        """Test record_spend has docstring."""
        assert CostBudget.record_spend.__doc__ is not None

    def test_transaction_method_has_docstring(self):
        """Test transaction has docstring."""
        assert CostBudget.transaction.__doc__ is not None

    def test_status_method_has_docstring(self):
        """Test status has docstring."""
        assert CostBudget.status.__doc__ is not None


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests with realistic scenarios."""

    def test_full_workflow_check_then_spend(self, basic_budget):
        """Test typical workflow: check then spend."""
        # Check if we can spend $2
        result = basic_budget.check_operation(2.0)
        assert result.can_proceed is True

        # Record the spend
        status = basic_budget.record_spend(2.0)
        # Status returns most restrictive (lowest remaining) which is hourly (2/10 = 20%)
        assert status.utilization_pct == pytest.approx(20.0)

    def test_workflow_with_transaction(self, basic_budget):
        """Test workflow using transaction."""
        with basic_budget.transaction(2.0):
            # Simulate expensive operation
            time.sleep(0.01)

        # Should be recorded
        assert basic_budget.utilization()["daily"] == pytest.approx(4.0)

    def test_workflow_progressive_spending(self, basic_budget):
        """Test progressive spending across session."""
        # First operation - well under all limits
        basic_budget.record_spend(2.0)
        assert basic_budget.alert_level() == AlertLevel.OK

        # More spending - 50% of hourly
        basic_budget.record_spend(3.0)
        # 5.0 / 10.0 = 50% hourly (OK)
        assert basic_budget.alert_level() == AlertLevel.OK

        # At warning threshold - 75% of hourly
        basic_budget.record_spend(2.5)
        # 7.5 / 10.0 = 75% hourly (WARNING)
        assert basic_budget.alert_level() == AlertLevel.WARNING

        # Closer to hourly limit - 90% of hourly
        basic_budget.record_spend(1.5)
        # 9.0 / 10.0 = 90% hourly (CRITICAL)
        assert basic_budget.alert_level() == AlertLevel.CRITICAL

        # At hourly limit - 100% of hourly
        basic_budget.record_spend(1.0)
        # 10.0 / 10.0 = 100% hourly (BLOCKED)
        assert basic_budget.alert_level() == AlertLevel.BLOCKED

        # Cannot proceed further
        result = basic_budget.check_operation(0.1)
        assert result.can_proceed is False

    def test_multiple_operations_within_limits(self, basic_budget):
        """Test multiple successful operations within limits."""
        for i in range(5):
            result = basic_budget.check_operation(2.0)
            assert result.can_proceed is True
            basic_budget.record_spend(2.0)

        # 10.0 / 50.0 = 20%
        assert basic_budget.utilization()["daily"] == 20.0


# ============================================================================
# Monthly reset edge cases (day-of-month overflow)
# ============================================================================

class TestMonthlyResetEdgeCases:
    """Regression tests for monthly reset when last_reset day does not exist
    in the following month (e.g. Jan 31 -> Feb)."""

    @patch("src.orchestration.cost.budget.datetime")
    def test_jan31_does_not_reset_immediately(self, mock_dt):
        """A budget last reset on Jan 31 must NOT reset two days later;
        the next reset should land at the end of February."""
        level = BudgetLevel(BudgetPeriod.MONTHLY, limit=100.0)
        level.last_reset = datetime(2026, 1, 31, 12, 0, 0)
        level.spent = 50.0

        # Two days later — well before the next monthly boundary.
        mock_dt.now.return_value = datetime(2026, 2, 2, 12, 0, 0)
        assert level.reset_if_needed() is False
        assert level.spent == 50.0

    @patch("src.orchestration.cost.budget.datetime")
    def test_jan31_resets_at_end_of_february(self, mock_dt):
        """Once the end-of-February boundary is reached, the budget resets."""
        level = BudgetLevel(BudgetPeriod.MONTHLY, limit=100.0)
        level.last_reset = datetime(2026, 1, 31, 12, 0, 0)
        level.spent = 50.0

        mock_dt.now.return_value = datetime(2026, 2, 28, 12, 0, 1)
        assert level.reset_if_needed() is True
        assert level.spent == 0.0

    @patch("src.orchestration.cost.budget.datetime")
    def test_aug31_resets_at_end_of_september(self, mock_dt):
        """Aug 31 (Sep has only 30 days) should reset at end of September."""
        level = BudgetLevel(BudgetPeriod.MONTHLY, limit=100.0)
        level.last_reset = datetime(2026, 8, 31, 0, 0, 0)
        level.spent = 75.0

        # Sep 15 — should not have reset yet.
        mock_dt.now.return_value = datetime(2026, 9, 15, 0, 0, 0)
        assert level.reset_if_needed() is False
        # Sep 30 — boundary reached.
        mock_dt.now.return_value = datetime(2026, 9, 30, 0, 0, 1)
        assert level.reset_if_needed() is True
        assert level.spent == 0.0
