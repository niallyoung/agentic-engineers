"""
Test Queue Operations

Tests for QueueOperations class with proper validation strings.
"""

import json
import pytest
import tempfile
from pathlib import Path

from scripts.queue_ops import QueueOperations
from tests.conftest import VALID_SCOPE, VALID_CONTEXT, VALID_PLAN_STEP1, VALID_PLAN_STEP2


@pytest.fixture
def temp_queue():
    """Create temporary queue directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def queue_ops(temp_queue):
    """Create QueueOperations instance with temp queue."""
    return QueueOperations(session_id="test-session", queue_path=temp_queue)


class TestQueueOpsBasic:
    """Basic tests for QueueOperations."""

    def test_create_delegate_valid(self, queue_ops):
        """Test creating valid DELEGATE."""
        result = queue_ops.create_delegate(
            task_id="test-task-001",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            context=VALID_CONTEXT,
        )

        assert result["status"] == "created"
        assert result["task_id"] == "test-task-001"
        assert "timestamp" in result

    def test_create_delegate_duplicate_fails(self, queue_ops):
        """Test that duplicate task_id raises FileExistsError."""
        queue_ops.create_delegate(
            task_id="duplicate",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            context=VALID_CONTEXT,
        )

        with pytest.raises(FileExistsError):
            queue_ops.create_delegate(
                task_id="duplicate",
                role="Engineer",
                scope=VALID_SCOPE,
                plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
                context=VALID_CONTEXT,
            )

    def test_move_task_valid(self, queue_ops):
        """Test moving task between states."""
        queue_ops.create_delegate(
            task_id="move-test",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            context=VALID_CONTEXT,
        )

        result = queue_ops.move_task("move-test", "incoming", "processing")
        assert result["status"] == "moved"
        assert result["from_state"] == "incoming"
        assert result["to_state"] == "processing"

    def test_query_tasks_by_state(self, queue_ops):
        """Test querying tasks by state."""
        for i in range(3):
            queue_ops.create_delegate(
                task_id=f"task-{i}",
                role="Engineer",
                scope=VALID_SCOPE,
                plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
                context=VALID_CONTEXT,
            )

        tasks = queue_ops.query_tasks("incoming")
        assert len(tasks) == 3

    def test_validate_delegate_valid(self, queue_ops):
        """Test validation of valid DELEGATE."""
        delegate = {
            "task_id": "valid-task",
            "role": "Engineer",
            "scope": VALID_SCOPE,
            "plan": [VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            "context": VALID_CONTEXT,
        }

        valid, errors = queue_ops.validate_delegate(delegate)
        assert valid
        assert len(errors) == 0

    def test_validate_delegate_invalid_scope(self, queue_ops):
        """Test validation with invalid scope."""
        delegate = {
            "task_id": "invalid-task",
            "role": "Engineer",
            "scope": "Too short",  # < 15 words
            "plan": [VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            "context": VALID_CONTEXT,
        }

        valid, errors = queue_ops.validate_delegate(delegate)
        assert not valid
        assert any("scope" in e.lower() for e in errors)

    def test_parent_task_creation(self, queue_ops):
        """Test creating task with parent_task_id."""
        # Create parent
        queue_ops.create_delegate(
            task_id="parent",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            context=VALID_CONTEXT,
        )

        # Create child
        result = queue_ops.create_delegate(
            task_id="child",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            context=VALID_CONTEXT,
            parent_task_id="parent",
        )

        assert result["parent_task_id"] == "parent"

    def test_query_by_parent(self, queue_ops):
        """Test querying tasks by parent."""
        queue_ops.create_delegate(
            task_id="parent",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            context=VALID_CONTEXT,
        )

        for i in range(2):
            queue_ops.create_delegate(
                task_id=f"child-{i}",
                role="Engineer",
                scope=VALID_SCOPE,
                plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
                context=VALID_CONTEXT,
                parent_task_id="parent",
            )

        children = queue_ops.query_tasks("incoming", parent_task_id="parent")
        assert len(children) == 2

    def test_rate_limit_status(self, queue_ops):
        """Test getting rate limit status."""
        status = queue_ops.get_rate_limit_status("test-session")
        assert status["limit"] == 100
        assert status["tasks_this_hour"] == 0

    def test_move_task_to_done(self, queue_ops):
        """Test complete workflow: create -> processing -> done."""
        queue_ops.create_delegate(
            task_id="workflow-test",
            role="Engineer",
            scope=VALID_SCOPE,
            plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            context=VALID_CONTEXT,
        )

        queue_ops.move_task("workflow-test", "incoming", "processing")
        queue_ops.move_task("workflow-test", "processing", "done")

        done_tasks = queue_ops.query_tasks("done")
        assert len(done_tasks) == 1
        assert done_tasks[0]["task_id"] == "workflow-test"
