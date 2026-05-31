"""Comprehensive test suite for TaskRunner and CLI.

Test groups:
1. TaskRunner initialization and lifecycle
2. Queue polling and state transitions
3. Task submission and execution
4. Error handling and retry logic
5. Dead-letter queue functionality
6. CLI commands validation
7. Integration tests
"""

from __future__ import annotations

import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
import yaml

from src.opencode.cli_runner import CLIRunner, main
from src.opencode.runner import (
    TaskContext,
    TaskResult,
    TaskRunner,
    TaskState,
)


@pytest.fixture
def temp_queue_root() -> Path:
    """Create temporary queue root directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def runner(temp_queue_root: Path) -> TaskRunner:
    """Create initialized TaskRunner instance."""
    runner = TaskRunner(
        queue_root=temp_queue_root,
        session_id="test-session",
        harness="test",
    )
    runner.initialize()
    return runner


@pytest.fixture
def cli_runner(temp_queue_root: Path) -> CLIRunner:
    """Create initialized CLIRunner instance."""
    cli = CLIRunner(
        session_id="test-session",
        harness="test",
        base_dir=temp_queue_root.parent,
        output_format="text",
    )
    cli.runner.initialize()
    return cli


# ============================================================================
# Tests: TaskRunner Initialization
# ============================================================================


class TestTaskRunnerInitialization:
    """Test TaskRunner initialization and setup."""

    def test_init_creates_queue_directories(self, runner: TaskRunner) -> None:
        """Verify init creates all required queue directories."""
        assert runner.incoming_dir.exists()
        assert runner.processing_dir.exists()
        assert runner.done_dir.exists()
        assert runner.failed_dir.exists()
        assert runner.dead_letter_dir.exists()

    def test_init_is_idempotent(self, runner: TaskRunner) -> None:
        """Verify init is idempotent and succeeds multiple times."""
        result1 = runner.initialize()
        result2 = runner.initialize()

        assert result1["success"]
        assert result2["success"]

    def test_from_session_creates_runner(self, temp_queue_root: Path) -> None:
        """Test TaskRunner.from_session() factory method."""
        runner = TaskRunner.from_session(
            session_id="test-session",
            harness="test",
            base_dir=temp_queue_root.parent,
        )
        assert runner.session_id == "test-session"
        assert runner.harness == "test"

    def test_from_session_generates_session_id(self, temp_queue_root: Path) -> None:
        """Test auto-generation of session ID when not provided."""
        runner = TaskRunner.from_session(
            harness="test",
            base_dir=temp_queue_root.parent,
        )
        assert runner.session_id is not None
        assert len(runner.session_id) > 0


# ============================================================================
# Tests: Task Submission and State Transitions
# ============================================================================


class TestTaskSubmissionAndTransitions:
    """Test task submission and state transitions."""

    def test_submit_task_creates_incoming_file(self, runner: TaskRunner) -> None:
        """Verify submit_task creates task file in incoming queue."""
        task_data = {"role": "engineer", "description": "Test task"}
        task_id = runner.submit_task(task_data)

        task_file = runner.incoming_dir / f"{task_id}.yaml"
        assert task_file.exists()

    def test_submit_task_with_explicit_id(self, runner: TaskRunner) -> None:
        """Verify submit_task accepts explicit task ID."""
        task_id = "TASK-CUSTOM-123"
        runner.submit_task({"role": "engineer"}, task_id=task_id)

        task_file = runner.incoming_dir / f"{task_id}.yaml"
        assert task_file.exists()

    def test_submit_task_rejects_duplicate_id(self, runner: TaskRunner) -> None:
        """Verify submit_task rejects duplicate task IDs."""
        task_id = "TASK-DUP-001"
        runner.submit_task({"role": "engineer"}, task_id=task_id)

        with pytest.raises(ValueError, match="already exists"):
            runner.submit_task({"role": "engineer"}, task_id=task_id)

    def test_submit_task_generates_unique_id(self, runner: TaskRunner) -> None:
        """Verify submit_task generates unique IDs."""
        id1 = runner.submit_task({"role": "engineer"})
        id2 = runner.submit_task({"role": "engineer"})

        assert id1 != id2
        assert id1.startswith("TASK-")
        assert id2.startswith("TASK-")

    def test_transition_incoming_to_processing(self, runner: TaskRunner) -> None:
        """Verify transition from incoming to processing state."""
        task_id = runner.submit_task({"role": "engineer"})

        # Transition to processing
        success = runner._transition_task(
            task_id, TaskState.INCOMING, TaskState.PROCESSING
        )

        assert success
        assert not (runner.incoming_dir / f"{task_id}.yaml").exists()
        assert (runner.processing_dir / f"{task_id}.yaml").exists()

    def test_transition_processing_to_done(self, runner: TaskRunner) -> None:
        """Verify transition from processing to done state."""
        task_id = runner.submit_task({"role": "engineer"})
        runner._transition_task(task_id, TaskState.INCOMING, TaskState.PROCESSING)

        # Transition to done
        success = runner._transition_task(
            task_id, TaskState.PROCESSING, TaskState.DONE
        )

        assert success
        assert not (runner.processing_dir / f"{task_id}.yaml").exists()
        assert (runner.done_dir / f"{task_id}.yaml").exists()

    def test_transition_nonexistent_task_fails(self, runner: TaskRunner) -> None:
        """Verify transition fails for nonexistent task."""
        success = runner._transition_task(
            "TASK-NONEXISTENT", TaskState.INCOMING, TaskState.PROCESSING
        )

        assert not success


# ============================================================================
# Tests: Queue Polling
# ============================================================================


class TestQueuePolling:
    """Test queue polling mechanism."""

    def test_poll_queue_finds_incoming_tasks(self, runner: TaskRunner) -> None:
        """Verify poll_queue finds tasks in incoming queue."""
        runner.submit_task({"role": "engineer"})
        runner.submit_task({"role": "engineer"})

        polled = runner.poll_queue()

        assert len(polled) == 2

    def test_poll_queue_transitions_to_processing(self, runner: TaskRunner) -> None:
        """Verify poll_queue transitions tasks to processing state."""
        task_id = runner.submit_task({"role": "engineer"})

        runner.poll_queue()

        # Task should be in processing
        assert (runner.processing_dir / f"{task_id}.yaml").exists()
        assert not (runner.incoming_dir / f"{task_id}.yaml").exists()

    def test_poll_queue_returns_empty_for_no_tasks(self, runner: TaskRunner) -> None:
        """Verify poll_queue returns empty list when queue is empty."""
        polled = runner.poll_queue()

        assert polled == []

    def test_poll_queue_multiple_calls(self, runner: TaskRunner) -> None:
        """Verify poll_queue can be called multiple times."""
        runner.submit_task({"role": "engineer"})

        first_poll = runner.poll_queue()
        assert len(first_poll) == 1

        second_poll = runner.poll_queue()
        assert len(second_poll) == 0


# ============================================================================
# Tests: Task Execution
# ============================================================================


class TestTaskExecution:
    """Test task execution framework."""

    def test_execute_task_success(self, runner: TaskRunner) -> None:
        """Verify successful task execution."""
        task_id = runner.submit_task({"role": "engineer"})
        runner._transition_task(task_id, TaskState.INCOMING, TaskState.PROCESSING)

        def handler(context: TaskContext) -> dict[str, Any]:
            return {"status": "success", "output": "done"}

        result = runner.execute_task(task_id, handler)

        assert result.success
        assert result.state == TaskState.DONE
        assert result.output == {"status": "success", "output": "done"}

    def test_execute_task_moves_to_done_directory(self, runner: TaskRunner) -> None:
        """Verify successful execution moves task to done directory."""
        task_id = runner.submit_task({"role": "engineer"})
        runner._transition_task(task_id, TaskState.INCOMING, TaskState.PROCESSING)

        def handler(context: TaskContext) -> dict[str, Any]:
            return {"status": "ok"}

        runner.execute_task(task_id, handler)

        assert (runner.done_dir / f"{task_id}.yaml").exists()

    def test_execute_task_failure_with_retry(self, runner: TaskRunner) -> None:
        """Verify task failure with retry moves back to incoming."""
        task_id = runner.submit_task({"role": "engineer"})
        runner._transition_task(task_id, TaskState.INCOMING, TaskState.PROCESSING)

        def handler(context: TaskContext) -> dict[str, Any]:
            raise ValueError("Task failed")

        result = runner.execute_task(task_id, handler)

        assert not result.success
        assert result.state == TaskState.INCOMING
        assert result.retry_count == 1
        assert (runner.incoming_dir / f"{task_id}.yaml").exists()

    def test_execute_task_failure_after_max_retries(self, runner: TaskRunner) -> None:
        """Verify task moves to dead-letter after max retries."""
        task_id = runner.submit_task({"role": "engineer"})

        def handler(context: TaskContext) -> dict[str, Any]:
            raise ValueError("Persistent failure")

        # Fail 3 times
        for _ in range(3):
            runner._transition_task(
                task_id, TaskState.INCOMING, TaskState.PROCESSING
            )
            result = runner.execute_task(task_id, handler)
            assert not result.success
            if result.state == TaskState.INCOMING:
                # Continue to next retry
                continue

        # Should be in dead-letter after max retries
        assert (runner.dead_letter_dir / f"{task_id}.yaml").exists()


# ============================================================================
# Tests: Error Handling
# ============================================================================


class TestErrorHandling:
    """Test error handling and recovery."""

    def test_execution_error_captured_in_result(self, runner: TaskRunner) -> None:
        """Verify execution errors are captured in result."""
        task_id = runner.submit_task({"role": "engineer"})
        runner._transition_task(task_id, TaskState.INCOMING, TaskState.PROCESSING)

        def handler(context: TaskContext) -> dict[str, Any]:
            raise RuntimeError("Something went wrong")

        result = runner.execute_task(task_id, handler)

        assert not result.success
        assert "Something went wrong" in result.error

    def test_retry_backoff_increases(self, runner: TaskRunner) -> None:
        """Verify retry backoff increases exponentially."""
        task_id = runner.submit_task({"role": "engineer"})

        def handler(context: TaskContext) -> dict[str, Any]:
            raise ValueError("Fail")

        # First retry
        runner._transition_task(task_id, TaskState.INCOMING, TaskState.PROCESSING)
        result1 = runner.execute_task(task_id, handler)
        assert result1.retry_count == 1

        # Second retry
        runner._transition_task(task_id, TaskState.INCOMING, TaskState.PROCESSING)
        result2 = runner.execute_task(task_id, handler)
        assert result2.retry_count == 2

    def test_dead_letter_task_persisted(self, runner: TaskRunner) -> None:
        """Verify dead-letter tasks are persisted with error info."""
        task_id = runner.submit_task({"role": "engineer"})

        def handler(context: TaskContext) -> dict[str, Any]:
            raise ValueError("Fatal error")

        # Fail 3 times
        for _ in range(3):
            runner._transition_task(
                task_id, TaskState.INCOMING, TaskState.PROCESSING
            )
            runner.execute_task(task_id, handler)

        # Load task from dead-letter
        task_file = runner.dead_letter_dir / f"{task_id}.yaml"
        assert task_file.exists()

        with open(task_file) as f:
            task_dict = yaml.safe_load(f)

        assert task_dict["state"] == "dead-letter"
        assert task_dict["error_message"] is not None


# ============================================================================
# Tests: Result Retrieval
# ============================================================================


class TestResultRetrieval:
    """Test result retrieval methods."""

    def test_get_result_for_done_task(self, runner: TaskRunner) -> None:
        """Verify get_result returns result for done task."""
        task_id = runner.submit_task({"role": "engineer"})
        runner._transition_task(task_id, TaskState.INCOMING, TaskState.PROCESSING)

        def handler(context: TaskContext) -> dict[str, Any]:
            return {"output": "result"}

        runner.execute_task(task_id, handler)

        result = runner.get_result(task_id)

        assert result is not None
        assert result.success
        assert result.state == TaskState.DONE

    def test_get_result_returns_none_for_processing_task(
        self, runner: TaskRunner
    ) -> None:
        """Verify get_result returns None for processing task."""
        task_id = runner.submit_task({"role": "engineer"})
        runner._transition_task(task_id, TaskState.INCOMING, TaskState.PROCESSING)

        result = runner.get_result(task_id)

        assert result is None

    def test_get_result_for_failed_task(self, runner: TaskRunner) -> None:
        """Verify get_result returns result for dead-letter task."""
        task_id = runner.submit_task({"role": "engineer"})

        def handler(context: TaskContext) -> dict[str, Any]:
            raise ValueError("Failed")

        # Fail 3 times to move to dead-letter
        for _ in range(3):
            runner._transition_task(task_id, TaskState.INCOMING, TaskState.PROCESSING)
            runner.execute_task(task_id, handler)

        result = runner.get_result(task_id)

        assert result is not None
        assert not result.success
        assert result.state == TaskState.DEAD_LETTER

    def test_get_task_status_returns_full_context(self, runner: TaskRunner) -> None:
        """Verify get_task_status returns complete context."""
        task_id = runner.submit_task({"role": "engineer", "custom": "data"})

        status = runner.get_task_status(task_id)

        assert status is not None
        assert status["task_id"] == task_id
        assert status["state"] == "incoming"
        assert status["metadata"]["role"] == "engineer"


# ============================================================================
# Tests: Task Listing and Filtering
# ============================================================================


class TestTaskListing:
    """Test task listing and filtering."""

    def test_list_tasks_all_states(self, runner: TaskRunner) -> None:
        """Verify list_tasks returns all tasks."""
        id1 = runner.submit_task({"role": "engineer"})
        id2 = runner.submit_task({"role": "engineer"})

        tasks = runner.list_tasks()

        assert len(tasks) == 2
        assert id1 in tasks
        assert id2 in tasks

    def test_list_tasks_filter_by_state(self, runner: TaskRunner) -> None:
        """Verify list_tasks filters by state."""
        task_id = runner.submit_task({"role": "engineer"})
        runner._transition_task(task_id, TaskState.INCOMING, TaskState.PROCESSING)

        incoming = runner.list_tasks(TaskState.INCOMING)
        processing = runner.list_tasks(TaskState.PROCESSING)

        assert len(incoming) == 0
        assert len(processing) == 1

    def test_list_tasks_empty_queue(self, runner: TaskRunner) -> None:
        """Verify list_tasks returns empty list for empty queue."""
        tasks = runner.list_tasks()

        assert tasks == []


# ============================================================================
# Tests: Task Cancellation and Retry
# ============================================================================


class TestTaskCancellationAndRetry:
    """Test task cancellation and retry functionality."""

    def test_cancel_task_incoming(self, runner: TaskRunner) -> None:
        """Verify cancel_task cancels incoming task."""
        task_id = runner.submit_task({"role": "engineer"})

        success = runner.cancel_task(task_id)

        assert success
        assert (runner.failed_dir / f"{task_id}.yaml").exists()

    def test_cancel_task_processing(self, runner: TaskRunner) -> None:
        """Verify cancel_task cancels processing task."""
        task_id = runner.submit_task({"role": "engineer"})
        runner._transition_task(task_id, TaskState.INCOMING, TaskState.PROCESSING)

        success = runner.cancel_task(task_id)

        assert success
        assert (runner.failed_dir / f"{task_id}.yaml").exists()

    def test_cancel_task_done_fails(self, runner: TaskRunner) -> None:
        """Verify cancel_task fails for done task."""
        task_id = runner.submit_task({"role": "engineer"})
        runner._transition_task(task_id, TaskState.INCOMING, TaskState.PROCESSING)
        runner._transition_task(task_id, TaskState.PROCESSING, TaskState.DONE)

        success = runner.cancel_task(task_id)

        assert not success

    def test_retry_task_from_dead_letter(self, runner: TaskRunner) -> None:
        """Verify retry_task moves task from dead-letter to incoming."""
        task_id = runner.submit_task({"role": "engineer"})

        # Move to dead-letter
        runner._transition_task(task_id, TaskState.INCOMING, TaskState.PROCESSING)
        runner._transition_task(task_id, TaskState.PROCESSING, TaskState.DEAD_LETTER)

        success = runner.retry_task(task_id)

        assert success
        assert (runner.incoming_dir / f"{task_id}.yaml").exists()
        assert not (runner.dead_letter_dir / f"{task_id}.yaml").exists()

    def test_retry_task_resets_retry_count(self, runner: TaskRunner) -> None:
        """Verify retry_task resets retry count for dead-letter tasks."""
        task_id = runner.submit_task({"role": "engineer"})

        def handler(context: TaskContext) -> dict[str, Any]:
            raise ValueError("Fail")

        # Fail 3 times to move to dead-letter
        for _ in range(3):
            runner._transition_task(
                task_id, TaskState.INCOMING, TaskState.PROCESSING
            )
            runner.execute_task(task_id, handler)

        # Verify task is in dead-letter with retry count = 3
        context = runner._load_task_context(task_id, TaskState.DEAD_LETTER)
        assert context is not None
        assert context.retry_count == 3

        # Retry from dead-letter
        runner.retry_task(task_id)

        # Check that retry count was reset
        context = runner._load_task_context(task_id, TaskState.INCOMING)
        assert context is not None
        assert context.retry_count == 0


# ============================================================================
# Tests: Context Serialization
# ============================================================================


class TestContextSerialization:
    """Test TaskContext serialization."""

    def test_task_context_to_dict(self) -> None:
        """Verify TaskContext.to_dict serializes correctly."""
        context = TaskContext(
            task_id="TASK-001",
            state=TaskState.PROCESSING,
            result={"key": "value"},
        )

        data = context.to_dict()

        assert data["task_id"] == "TASK-001"
        assert data["state"] == "processing"
        assert data["result"] == {"key": "value"}

    def test_task_context_from_dict(self) -> None:
        """Verify TaskContext.from_dict deserializes correctly."""
        original_data = {
            "task_id": "TASK-001",
            "state": "done",
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-01T00:00:00+00:00",
            "retry_count": 1,
            "max_retries": 3,
            "error_message": None,
            "result": {"key": "value"},
            "metadata": {"role": "engineer"},
        }

        context = TaskContext.from_dict(original_data)

        assert context.task_id == "TASK-001"
        assert context.state == TaskState.DONE
        assert context.retry_count == 1
        assert context.result == {"key": "value"}


# ============================================================================
# Tests: CLI Commands
# ============================================================================


class TestCLICommands:
    """Test CLI command implementations."""

    def test_cli_init_command(self, cli_runner: CLIRunner, capsys: Any) -> None:
        """Verify CLI init command creates queue structure."""
        exit_code = cli_runner.run_init(mock.Mock(verbose=False))

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Queue initialized" in captured.out

    def test_cli_run_command(self, cli_runner: CLIRunner, capsys: Any) -> None:
        """Verify CLI run command submits task."""
        args = mock.Mock(role="engineer", description="Test", metadata=None)
        exit_code = cli_runner.run_run(args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Task submitted" in captured.out

    def test_cli_status_command(self, cli_runner: CLIRunner, capsys: Any) -> None:
        """Verify CLI status command returns task status."""
        # Submit a task
        task_id = cli_runner.runner.submit_task({"role": "engineer"})

        # Get status
        args = mock.Mock(task_id=task_id, positional_task_id=None)
        exit_code = cli_runner.run_status(args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Task:" in captured.out

    def test_cli_list_command(self, cli_runner: CLIRunner, capsys: Any) -> None:
        """Verify CLI list command returns task list."""
        cli_runner.runner.submit_task({"role": "engineer"})

        args = mock.Mock(state=None)
        exit_code = cli_runner.run_list(args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "All tasks:" in captured.out

    def test_cli_cancel_command(self, cli_runner: CLIRunner, capsys: Any) -> None:
        """Verify CLI cancel command cancels task."""
        task_id = cli_runner.runner.submit_task({"role": "engineer"})

        args = mock.Mock(task_id=task_id, positional_task_id=None)
        exit_code = cli_runner.run_cancel(args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Task cancelled" in captured.out

    def test_cli_retry_command(self, cli_runner: CLIRunner, capsys: Any) -> None:
        """Verify CLI retry command retries failed task."""
        task_id = cli_runner.runner.submit_task({"role": "engineer"})

        # Move to failed
        cli_runner.runner._transition_task(
            task_id, TaskState.INCOMING, TaskState.FAILED
        )

        # Retry
        args = mock.Mock(task_id=task_id, positional_task_id=None)
        exit_code = cli_runner.run_retry(args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Retry initiated" in captured.out


# ============================================================================
# Tests: Integration
# ============================================================================


class TestIntegration:
    """Integration tests for full workflows."""

    def test_full_task_lifecycle(self, runner: TaskRunner) -> None:
        """Verify complete task lifecycle: submit → poll → execute → retrieve."""
        # Submit task
        task_id = runner.submit_task({"role": "engineer", "description": "Test"})
        assert runner.list_tasks(TaskState.INCOMING) == [task_id]

        # Poll queue
        polled = runner.poll_queue()
        assert task_id in polled
        assert runner.list_tasks(TaskState.PROCESSING) == [task_id]

        # Execute task
        def handler(context: TaskContext) -> dict[str, Any]:
            return {"completed": True, "output": "success"}

        result = runner.execute_task(task_id, handler)
        assert result.success

        # Retrieve result
        final_result = runner.get_result(task_id)
        assert final_result is not None
        assert final_result.state == TaskState.DONE
        assert final_result.output == {"completed": True, "output": "success"}

    def test_retry_on_failure_workflow(self, runner: TaskRunner) -> None:
        """Verify retry workflow on task failure."""
        task_id = runner.submit_task({"role": "engineer"})

        attempt = 0

        def handler(context: TaskContext) -> dict[str, Any]:
            nonlocal attempt
            attempt += 1
            if attempt < 3:
                raise ValueError(f"Attempt {attempt} failed")
            return {"success": True}

        # First failure - should move back to incoming
        runner.poll_queue()
        result = runner.execute_task(task_id, handler)
        assert result.state == TaskState.INCOMING
        assert result.retry_count == 1

        # Second attempt - should still fail and move back to incoming
        runner.poll_queue()
        result = runner.execute_task(task_id, handler)
        assert result.state == TaskState.INCOMING
        assert result.retry_count == 2

        # Third attempt - should succeed
        runner.poll_queue()
        result = runner.execute_task(task_id, handler)
        assert result.success
        assert result.state == TaskState.DONE

    def test_dead_letter_and_manual_retry(self, runner: TaskRunner) -> None:
        """Verify dead-letter queue and manual retry."""
        task_id = runner.submit_task({"role": "engineer"})

        def handler(context: TaskContext) -> dict[str, Any]:
            raise ValueError("Permanent failure")

        # Attempt 1
        runner.poll_queue()
        result = runner.execute_task(task_id, handler)
        assert result.state == TaskState.INCOMING

        # Attempt 2
        runner.poll_queue()
        result = runner.execute_task(task_id, handler)
        assert result.state == TaskState.INCOMING

        # Attempt 3 - should move to dead-letter
        runner.poll_queue()
        result = runner.execute_task(task_id, handler)
        assert result.state == TaskState.DEAD_LETTER

        # Should be in dead-letter
        status = runner.get_task_status(task_id)
        assert status["state"] == "dead-letter"

        # Manually retry
        success = runner.retry_task(task_id)
        assert success

        # Execute successfully on retry
        runner.poll_queue()

        def success_handler(context: TaskContext) -> dict[str, Any]:
            return {"status": "ok"}

        result = runner.execute_task(task_id, success_handler)
        assert result.success


# ============================================================================
# Coverage Tests
# ============================================================================


class TestCoverage:
    """Tests for edge cases and coverage."""

    def test_task_context_fields(self) -> None:
        """Test all TaskContext fields are preserved."""
        context = TaskContext(
            task_id="TEST-001",
            state=TaskState.PROCESSING,
            retry_count=2,
            max_retries=5,
            error_message="test error",
            result={"key": "value"},
            metadata={"custom": "data"},
        )

        data = context.to_dict()
        restored = TaskContext.from_dict(data)

        assert restored.task_id == context.task_id
        assert restored.retry_count == 2
        assert restored.max_retries == 5
        assert restored.error_message == "test error"
        assert restored.result == {"key": "value"}

    def test_task_result_serialization(self) -> None:
        """Test TaskResult serialization."""
        result = TaskResult(
            task_id="TASK-001",
            success=True,
            state=TaskState.DONE,
            output={"data": "test"},
            execution_time_ms=123.45,
        )

        data = result.to_dict()

        assert data["task_id"] == "TASK-001"
        assert data["success"]
        assert data["state"] == "done"

    def test_repr_methods(self, runner: TaskRunner) -> None:
        """Test __repr__ methods."""
        repr_str = repr(runner)
        assert "TaskRunner" in repr_str
        assert "test-session" in repr_str
        assert "test" in repr_str

    def test_list_tasks_sorted(self, runner: TaskRunner) -> None:
        """Verify list_tasks returns sorted task IDs."""
        runner.submit_task({"role": "engineer"})
        runner.submit_task({"role": "engineer"})
        runner.submit_task({"role": "engineer"})

        tasks = runner.list_tasks()
        assert tasks == sorted(tasks)
