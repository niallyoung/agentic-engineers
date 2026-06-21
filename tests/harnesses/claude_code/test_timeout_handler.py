"""
Regression tests for Claude Code harness TimeoutHandler.

Tests for task deadline management, expiration detection, and
concurrent access safety.
"""

from __future__ import annotations

import time
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.harnesses.claude_code.timeout_handler import (
    EFFORT_TIMEOUTS,
    TaskDeadline,
    TimeoutHandler,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def handler() -> TimeoutHandler:
    """Fresh TimeoutHandler instance for each test."""
    return TimeoutHandler()


@pytest.fixture
def handler_custom() -> TimeoutHandler:
    """TimeoutHandler with custom effort timeouts."""
    custom_timeouts = {
        "low": 10,
        "medium": 30,
        "high": 60,
    }
    return TimeoutHandler(effort_timeouts=custom_timeouts)


# ---------------------------------------------------------------------------
# D3.1: Deadline creation
# ---------------------------------------------------------------------------


class TestDeadlineCreation:
    """Task deadline creation and initialization."""

    def test_set_deadline_creates_entry(self, handler: TimeoutHandler) -> None:
        """set_deadline() creates a TaskDeadline entry."""
        deadline = handler.set_deadline("task-001", "medium")
        assert isinstance(deadline, TaskDeadline)
        assert deadline.task_id == "task-001"
        assert deadline.effort == "medium"
        assert deadline.expired is False

    def test_set_deadline_with_low_effort(
        self, handler: TimeoutHandler
    ) -> None:
        """Low effort timeout is 30 seconds."""
        before = time.time()
        deadline = handler.set_deadline("task-low", "low")
        after = time.time()

        # Deadline should be roughly now + 30 seconds
        expected_deadline = before + 30
        # Allow 0.1s tolerance for execution time
        assert expected_deadline - 0.1 <= deadline.deadline <= after + 30 + 0.1

    def test_set_deadline_with_medium_effort(
        self, handler: TimeoutHandler
    ) -> None:
        """Medium effort timeout is 120 seconds."""
        before = time.time()
        deadline = handler.set_deadline("task-med", "medium")
        after = time.time()

        expected_deadline = before + 120
        assert expected_deadline - 0.1 <= deadline.deadline <= after + 120 + 0.1

    def test_set_deadline_with_high_effort(
        self, handler: TimeoutHandler
    ) -> None:
        """High effort timeout is 600 seconds."""
        before = time.time()
        deadline = handler.set_deadline("task-high", "high")
        after = time.time()

        expected_deadline = before + 600
        assert expected_deadline - 0.1 <= deadline.deadline <= after + 600 + 0.1

    def test_set_deadline_with_max_effort(
        self, handler: TimeoutHandler
    ) -> None:
        """Max effort timeout is 3600 seconds."""
        before = time.time()
        deadline = handler.set_deadline("task-max", "max")
        after = time.time()

        expected_deadline = before + 3600
        assert expected_deadline - 0.1 <= deadline.deadline <= after + 3600 + 0.1

    def test_set_deadline_with_unknown_effort_defaults_to_30_seconds(
        self, handler: TimeoutHandler
    ) -> None:
        """Unknown effort level defaults to 30 seconds."""
        before = time.time()
        deadline = handler.set_deadline("task-unknown", "unknown")
        after = time.time()

        expected_deadline = before + 30
        assert expected_deadline - 0.1 <= deadline.deadline <= after + 30 + 0.1

    def test_set_deadline_case_insensitive(self, handler: TimeoutHandler) -> None:
        """Effort level is case-insensitive."""
        deadline1 = handler.set_deadline("task1", "HIGH")
        deadline2 = handler.set_deadline("task2", "high")

        # Both should have same timeout (600 seconds for high)
        assert abs(deadline1.deadline - deadline2.deadline) < 0.1

    def test_set_deadline_replaces_existing(
        self, handler: TimeoutHandler
    ) -> None:
        """Setting deadline for same task_id replaces previous."""
        handler.set_deadline("task-001", "low")
        deadline2 = handler.set_deadline("task-001", "high")

        # Should use high effort timeout
        assert deadline2.effort == "high"


# ---------------------------------------------------------------------------
# D3.2-D3.3: Expiration checking
# ---------------------------------------------------------------------------


class TestExpirationChecking:
    """Task expiration detection and state tracking."""

    def test_check_expired_false_before_deadline(
        self, handler: TimeoutHandler
    ) -> None:
        """check_expired() returns False before deadline."""
        handler.set_deadline("task-001", "high")  # 600 second timeout
        expired = handler.check_expired("task-001")
        assert expired is False

    def test_check_expired_true_after_deadline(
        self, handler_custom: TimeoutHandler
    ) -> None:
        """check_expired() returns True after deadline."""
        # Create task with 0.1 second timeout via custom handler
        handler_custom._effort_timeouts["quick"] = 0  # 0 second timeout
        handler_custom.set_deadline("task-expired", "quick")
        time.sleep(0.05)  # Wait for expiry

        expired = handler_custom.check_expired("task-expired")
        assert expired is True

    def test_check_expired_untracked_task_returns_false(
        self, handler: TimeoutHandler
    ) -> None:
        """check_expired() for untracked task returns False."""
        expired = handler.check_expired("nonexistent-task")
        assert expired is False

    def test_check_expired_marks_expired_state(
        self, handler_custom: TimeoutHandler
    ) -> None:
        """check_expired() marks the task as expired."""
        # Use a very short timeout to ensure expiry
        handler_custom._effort_timeouts["quick"] = 0.05
        handler_custom.set_deadline("task-001", "quick")
        time.sleep(0.15)

        expired = handler_custom.check_expired("task-001")
        assert expired is True

        # Second call should also return True (persistent state)
        expired_again = handler_custom.check_expired("task-001")
        assert expired_again is True

    def test_check_expired_once_marked_stays_expired(
        self, handler_custom: TimeoutHandler
    ) -> None:
        """Once expired, task remains expired."""
        handler_custom._effort_timeouts["quick"] = 0.05
        handler_custom.set_deadline("task-001", "quick")
        time.sleep(0.1)

        first_check = handler_custom.check_expired("task-001")
        assert first_check is True

        # Subsequent checks should still return True
        second_check = handler_custom.check_expired("task-001")
        assert second_check is True


# ---------------------------------------------------------------------------
# D3.4-D3.5: Time remaining calculation
# ---------------------------------------------------------------------------


class TestTimeRemaining:
    """Time remaining calculation and status reporting."""

    def test_time_remaining_positive(self, handler: TimeoutHandler) -> None:
        """time_remaining() returns positive seconds until deadline."""
        handler.set_deadline("task-001", "high")  # 600 second timeout
        remaining = handler.time_remaining("task-001")

        assert remaining is not None
        assert remaining > 0
        assert remaining <= 600

    def test_time_remaining_negative_when_expired(
        self, handler_custom: TimeoutHandler
    ) -> None:
        """time_remaining() returns negative after deadline."""
        handler_custom._effort_timeouts["quick"] = 0.05
        handler_custom.set_deadline("task-001", "quick")
        time.sleep(0.1)

        remaining = handler_custom.time_remaining("task-001")
        assert remaining is not None
        assert remaining < 0

    def test_time_remaining_untracked_task_returns_none(
        self, handler: TimeoutHandler
    ) -> None:
        """time_remaining() for untracked task returns None."""
        remaining = handler.time_remaining("nonexistent-task")
        assert remaining is None

    def test_time_remaining_decreases_over_time(
        self, handler: TimeoutHandler
    ) -> None:
        """time_remaining() decreases as time passes."""
        handler.set_deadline("task-001", "medium")  # 120 second timeout
        remaining1 = handler.time_remaining("task-001")

        time.sleep(0.1)
        remaining2 = handler.time_remaining("task-001")

        assert remaining1 is not None
        assert remaining2 is not None
        assert remaining2 < remaining1

    def test_time_remaining_with_zero_timeout(
        self, handler_custom: TimeoutHandler
    ) -> None:
        """time_remaining() with zero timeout shows negative immediately."""
        handler_custom._effort_timeouts["instant"] = 0
        handler_custom.set_deadline("task-001", "instant")
        time.sleep(0.01)

        remaining = handler_custom.time_remaining("task-001")
        assert remaining is not None
        assert remaining < 0


# ---------------------------------------------------------------------------
# D3.6: Expired tasks listing
# ---------------------------------------------------------------------------


class TestExpiredTasksList:
    """Querying list of expired tasks."""

    def test_expired_tasks_list_empty_initially(
        self, handler: TimeoutHandler
    ) -> None:
        """expired_tasks() returns empty list when no tasks tracked."""
        expired = handler.expired_tasks()
        assert expired == []

    def test_expired_tasks_list_only_expired(
        self, handler_custom: TimeoutHandler
    ) -> None:
        """expired_tasks() returns only tasks past deadline."""
        handler_custom._effort_timeouts["quick"] = 0.05
        handler_custom._effort_timeouts["slow"] = 600

        # Quick task will expire
        handler_custom.set_deadline("task-quick", "quick")
        # Slow task will not
        handler_custom.set_deadline("task-slow", "slow")

        time.sleep(0.1)

        expired = handler_custom.expired_tasks()
        assert "task-quick" in expired
        assert "task-slow" not in expired

    def test_expired_tasks_list_multiple_expired(
        self, handler_custom: TimeoutHandler
    ) -> None:
        """expired_tasks() returns all expired tasks."""
        handler_custom._effort_timeouts["quick"] = 0.05

        for i in range(3):
            handler_custom.set_deadline(f"task-{i}", "quick")

        time.sleep(0.1)

        expired = handler_custom.expired_tasks()
        assert len(expired) == 3
        assert all(f"task-{i}" in expired for i in range(3))

    def test_expired_tasks_after_mark_expired(
        self, handler: TimeoutHandler
    ) -> None:
        """expired_tasks() includes manually marked tasks."""
        handler.set_deadline("task-001", "high")
        handler.mark_expired("task-001")

        expired = handler.expired_tasks()
        assert "task-001" in expired


# ---------------------------------------------------------------------------
# D3.7: Task clearing
# ---------------------------------------------------------------------------


class TestTaskClearing:
    """Task removal and cleanup."""

    def test_clear_removes_task(self, handler: TimeoutHandler) -> None:
        """clear() removes a task from tracking."""
        handler.set_deadline("task-001", "high")
        handler.clear("task-001")

        # Task should not be tracked anymore
        remaining = handler.time_remaining("task-001")
        assert remaining is None

    def test_clear_nonexistent_task_is_safe(self, handler: TimeoutHandler) -> None:
        """clear() on untracked task is safe."""
        handler.clear("nonexistent-task")  # Should not raise

    def test_clear_allows_reuse_of_task_id(self, handler: TimeoutHandler) -> None:
        """Task ID can be reused after clear()."""
        handler.set_deadline("task-001", "low")
        handler.clear("task-001")
        # Now set new deadline with same ID
        deadline2 = handler.set_deadline("task-001", "high")

        assert deadline2.effort == "high"
        remaining = handler.time_remaining("task-001")
        assert remaining is not None
        assert remaining > 0

    def test_clear_after_expiry(self, handler_custom: TimeoutHandler) -> None:
        """clear() works after task has expired."""
        handler_custom._effort_timeouts["quick"] = 0.05
        handler_custom.set_deadline("task-001", "quick")
        time.sleep(0.1)

        # Task is expired
        assert handler_custom.check_expired("task-001")

        # Now clear it
        handler_custom.clear("task-001")

        # No longer tracked
        remaining = handler_custom.time_remaining("task-001")
        assert remaining is None


# ---------------------------------------------------------------------------
# Manual expiration marking
# ---------------------------------------------------------------------------


class TestManualExpiration:
    """Manual task expiration marking."""

    def test_mark_expired_flags_task(self, handler: TimeoutHandler) -> None:
        """mark_expired() flags a task as expired."""
        handler.set_deadline("task-001", "high")
        handler.mark_expired("task-001")

        assert handler.check_expired("task-001") is True

    def test_mark_expired_nonexistent_task_is_safe(
        self, handler: TimeoutHandler
    ) -> None:
        """mark_expired() on untracked task is safe."""
        handler.mark_expired("nonexistent-task")  # Should not raise

    def test_mark_expired_persists_across_calls(
        self, handler: TimeoutHandler
    ) -> None:
        """mark_expired() state persists."""
        handler.set_deadline("task-001", "high")
        handler.mark_expired("task-001")

        # Multiple checks should all return True
        assert handler.check_expired("task-001") is True
        assert handler.check_expired("task-001") is True


# ---------------------------------------------------------------------------
# Custom effort timeouts
# ---------------------------------------------------------------------------


class TestCustomEffortTimeouts:
    """Custom effort-to-timeout mappings."""

    def test_custom_effort_timeouts_respected(
        self, handler_custom: TimeoutHandler
    ) -> None:
        """Custom effort timeouts override defaults."""
        # "low" should be 10 seconds, not 30
        before = time.time()
        deadline = handler_custom.set_deadline("task-001", "low")
        after = time.time()

        expected = before + 10
        assert expected - 0.1 <= deadline.deadline <= after + 10 + 0.1

    def test_default_effort_timeouts_match_constant(self) -> None:
        """Default handler uses EFFORT_TIMEOUTS constant."""
        handler = TimeoutHandler()
        # Check by creating a deadline and verifying the timeout applied
        before = time.time()
        deadline = handler.set_deadline("task-001", "high")
        after = time.time()

        expected_timeout = EFFORT_TIMEOUTS["high"]
        expected = before + expected_timeout
        assert expected - 0.1 <= deadline.deadline <= after + expected_timeout + 0.1
