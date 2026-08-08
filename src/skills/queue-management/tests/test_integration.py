"""Integration tests for complete workflows."""

import json
import pytest
import tempfile
from pathlib import Path
from threading import Thread

from scripts.queue_ops import QueueOperations
from tests.conftest import VALID_SCOPE, VALID_CONTEXT, VALID_PLAN_STEP1, VALID_PLAN_STEP2


@pytest.fixture
def temp_queue():
    """Create temporary queue directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def queue_ops(temp_queue):
    """Create QueueOperations instance."""
    return QueueOperations(session_id="test-session", queue_path=temp_queue)


class TestCompleteWorkflow:
    """Tests for complete workflow."""

    def test_full_workflow(self, queue_ops):
        """Test workflow: create -> processing -> done."""
        result = queue_ops.create_delegate(
            task_id="workflow-test",
            role="engineer",
            scope=VALID_SCOPE,
            plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            context=VALID_CONTEXT,
        )

        assert result["status"] == "created"

        queue_ops.move_task("workflow-test", "incoming", "processing")
        queue_ops.move_task("workflow-test", "processing", "done")

        done = queue_ops.query_tasks("done")
        assert len(done) == 1


class TestSubtaskWorkflow:
    """Tests for parent-child workflows."""

    def test_parent_child_creation(self, queue_ops):
        """Test creating parent and children."""
        queue_ops.create_delegate(
            task_id="parent",
            role="engineer",
            scope=VALID_SCOPE,
            plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            context=VALID_CONTEXT,
        )

        for i in range(3):
            queue_ops.create_delegate(
                task_id=f"child-{i}",
                role="engineer",
                scope=VALID_SCOPE,
                plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
                context=VALID_CONTEXT,
                parent_task_id="parent",
            )

        children = queue_ops.query_tasks("incoming", parent_task_id="parent")
        assert len(children) == 3


class TestErrorHandling:
    """Tests for error handling."""

    def test_duplicate_task_error(self, queue_ops):
        """Test duplicate task_id raises FileExistsError."""
        queue_ops.create_delegate(
            task_id="dup-task",
            role="engineer",
            scope=VALID_SCOPE,
            plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            context=VALID_CONTEXT,
        )

        with pytest.raises(FileExistsError):
            queue_ops.create_delegate(
                task_id="dup-task",
                role="engineer",
                scope=VALID_SCOPE,
                plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
                context=VALID_CONTEXT,
            )


class TestSessionIsolation:
    """Tests for session isolation."""

    def test_multiple_sessions_isolated(self, temp_queue):
        """Test sessions are isolated."""
        s1 = QueueOperations(session_id="session-1", queue_path=temp_queue)
        s2 = QueueOperations(session_id="session-2", queue_path=temp_queue)

        s1.create_delegate(
            task_id="task-1",
            role="engineer",
            scope=VALID_SCOPE,
            plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            context=VALID_CONTEXT,
        )

        s2.create_delegate(
            task_id="task-2",
            role="engineer",
            scope=VALID_SCOPE,
            plan=[VALID_PLAN_STEP1, VALID_PLAN_STEP2],
            context=VALID_CONTEXT,
        )

        s1_tasks = s1.query_tasks("incoming")
        s2_tasks = s2.query_tasks("incoming")

        assert len(s1_tasks) == 1
        assert len(s2_tasks) == 1
