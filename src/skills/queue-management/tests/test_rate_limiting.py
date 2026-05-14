"""
Test Rate Limiting

Tests for RateLimiter class.
"""

import pytest
import tempfile
from pathlib import Path

from scripts.rate_limiter import RateLimiter


@pytest.fixture
def temp_rate_limit_dir():
    """Create temporary rate limit directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def rate_limiter(temp_rate_limit_dir):
    """Create RateLimiter instance."""
    return RateLimiter(state_dir=temp_rate_limit_dir)


class TestSessionRateLimiting:
    """Tests for session-level rate limiting."""

    def test_check_limit_below_limit(self, rate_limiter):
        """Test request below limit is allowed."""
        allowed, status = rate_limiter.check_limit("session-1")
        assert allowed
        assert status["tasks_this_hour"] == 0
        assert status["limit"] == 100

    def test_check_limit_tracks_tasks(self, rate_limiter):
        """Test that tasks are tracked."""
        rate_limiter.record_task("session-1", "task-1")
        rate_limiter.record_task("session-1", "task-2")

        allowed, status = rate_limiter.check_limit("session-1")
        assert allowed
        assert status["tasks_this_hour"] == 2

    def test_check_limit_exceeds(self, rate_limiter):
        """Test requests exceeding limit are rejected."""
        for i in range(100):
            rate_limiter.record_task("session-1", f"task-{i}")

        allowed, status = rate_limiter.check_limit("session-1")
        assert not allowed
        assert status["tasks_this_hour"] == 100

    def test_multiple_sessions_isolated(self, rate_limiter):
        """Test different sessions have isolated limits."""
        rate_limiter.record_task("session-1", "task-1")
        rate_limiter.record_task("session-2", "task-1")

        status1 = rate_limiter.check_limit("session-1")[1]
        status2 = rate_limiter.check_limit("session-2")[1]

        assert status1["tasks_this_hour"] == 1
        assert status2["tasks_this_hour"] == 1


class TestParentChildRateLimiting:
    """Tests for parent-child rate limiting."""

    def test_child_limit_below(self, rate_limiter):
        """Test child creation when under limit."""
        allowed, status = rate_limiter.check_limit("session-1", parent_task_id="parent")
        assert allowed
        assert status["children_count"] == 0

    def test_child_limit_tracking(self, rate_limiter):
        """Test child tasks are tracked."""
        rate_limiter.record_task("session-1", "child-1", parent_task_id="parent")
        rate_limiter.record_task("session-1", "child-2", parent_task_id="parent")

        allowed, status = rate_limiter.check_limit("session-1", parent_task_id="parent")
        assert allowed
        assert status["children_count"] == 2

    def test_child_limit_exceeds(self, rate_limiter):
        """Test 11th child is rejected."""
        for i in range(10):
            rate_limiter.record_task("session-1", f"child-{i}", parent_task_id="parent")

        allowed, status = rate_limiter.check_limit("session-1", parent_task_id="parent")
        assert not allowed
        assert status["children_count"] == 10

    def test_different_parents_isolated(self, rate_limiter):
        """Test different parents have isolated limits."""
        rate_limiter.record_task("session-1", "child-1", parent_task_id="parent-1")
        rate_limiter.record_task("session-1", "child-1", parent_task_id="parent-2")

        status1 = rate_limiter.check_limit("session-1", parent_task_id="parent-1")[1]
        status2 = rate_limiter.check_limit("session-1", parent_task_id="parent-2")[1]

        assert status1["children_count"] == 1
        assert status2["children_count"] == 1


class TestGetStatus:
    """Tests for get_status method."""

    def test_get_status_empty(self, rate_limiter):
        """Test status for session with no tasks."""
        status = rate_limiter.get_status("session-1")
        assert status["tasks_this_hour"] == 0
        assert status["limit"] == 100

    def test_get_status_with_tasks(self, rate_limiter):
        """Test status after recording tasks."""
        rate_limiter.record_task("session-1", "task-1")
        rate_limiter.record_task("session-1", "task-2")

        status = rate_limiter.get_status("session-1")
        assert status["tasks_this_hour"] == 2
        assert status["remaining"] == 98
