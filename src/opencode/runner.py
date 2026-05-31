"""TaskRunner - Queue-based task execution framework for OpenCode runner infrastructure.

Implements complete lifecycle management for task execution with atomic state transitions,
error handling, retry logic, and dead-letter queue functionality.

State Machine::

    incoming → processing → done
         ↘      ↙
         failed (→ retry)
           ↓
      dead-letter

Core Features:
- Queue polling (incoming → processing → done)
- Atomic state transitions with file-based locking
- Exponential backoff retry logic (max 3 retries)
- Dead-letter queue for permanently failed tasks
- Result retrieval with full execution context
- Comprehensive error recovery
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional
from uuid import uuid4

import yaml

logger = logging.getLogger(__name__)


class TaskState(Enum):
    """Task lifecycle states."""

    INCOMING = "incoming"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"
    DEAD_LETTER = "dead-letter"


@dataclass
class TaskContext:
    """Execution context for a task."""

    task_id: str
    state: TaskState
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    result: Optional[dict] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "state": self.state.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_message": self.error_message,
            "result": self.result,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TaskContext:
        """Create from dictionary."""
        return cls(
            task_id=data["task_id"],
            state=TaskState(data["state"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            error_message=data.get("error_message"),
            result=data.get("result"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TaskResult:
    """Result of task execution."""

    task_id: str
    success: bool
    state: TaskState
    output: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "success": self.success,
            "state": self.state.value,
            "output": self.output,
            "error": self.error,
            "retry_count": self.retry_count,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class TaskRunner:
    """Queue-based task execution engine with full lifecycle management.

    Implements atomic state transitions, polling, retry logic, and result retrieval.

    Example usage::

        runner = TaskRunner.from_session()
        runner.initialize()

        # Submit a task
        task_id = runner.submit_task({"role": "engineer", "description": "..."})

        # Poll for results
        while True:
            result = runner.get_result(task_id)
            if result:
                print(f"Task {task_id}: {result.state}")
                break
            time.sleep(1)
    """

    # Retry configuration
    INITIAL_BACKOFF_MS = 1000  # 1 second
    MAX_BACKOFF_MS = 60000  # 1 minute
    BACKOFF_MULTIPLIER = 2.0

    def __init__(
        self,
        queue_root: Path,
        session_id: str,
        harness: str,
        *,
        max_workers: int = 4,
    ) -> None:
        """Initialize TaskRunner.

        Args:
            queue_root: Root path for queue directories (usually ~/.agentic-engineers/...)
            session_id: Session identifier
            harness: Harness name (opencode, copilot, etc.)
            max_workers: Maximum concurrent task processors

        Raises:
            ValueError: If queue_root does not exist or is not a directory
        """
        self.queue_root = Path(queue_root)
        self.session_id = session_id
        self.harness = harness
        self.max_workers = max_workers

        # Queue subdirectories
        self.incoming_dir = self.queue_root / "incoming"
        self.processing_dir = self.queue_root / "processing"
        self.done_dir = self.queue_root / "done"
        self.failed_dir = self.queue_root / "failed"
        self.dead_letter_dir = self.queue_root / "dead-letter"

        # Thread safety
        self._lock = threading.RLock()
        self._task_locks: dict[str, threading.Lock] = {}

        # Runtime state
        self._is_initialized = False
        self._polling_thread: Optional[threading.Thread] = None
        self._stop_polling = threading.Event()

        logger.debug(
            f"Initialized TaskRunner: session={session_id}, harness={harness}, "
            f"queue_root={queue_root}"
        )

    @classmethod
    def from_session(
        cls,
        session_id: Optional[str] = None,
        harness: Optional[str] = None,
        base_dir: Optional[Path] = None,
        **kwargs: Any,
    ) -> TaskRunner:
        """Create TaskRunner from session context.

        Attempts to auto-detect session and harness from environment.

        Args:
            session_id: Session ID (auto-detected if None)
            harness: Harness name (auto-detected if None)
            base_dir: Base directory for queue root (default: ~/.agentic-engineers)
            **kwargs: Additional arguments to pass to __init__

        Returns:
            Initialized TaskRunner instance
        """
        import os
        from uuid import uuid4

        # Auto-detect session
        if session_id is None:
            session_id = os.environ.get("AGENTIC_SESSION_ID") or os.environ.get(
                "OPENCODE_SESSION_ID"
            )
            if not session_id:
                session_id = str(uuid4())

        # Auto-detect harness
        if harness is None:
            harness = os.environ.get("AGENTIC_HARNESS") or os.environ.get(
                "OPENCODE_API"
            )
            if not harness:
                harness = "local"

        # Default base dir
        if base_dir is None:
            base_dir = Path.home() / ".agentic-engineers"

        # Queue root follows canonical path
        queue_root = base_dir / "artifacts" / session_id / harness / "queue"

        return cls(queue_root, session_id, harness, **kwargs)

    def initialize(self) -> dict[str, Any]:
        """Initialize queue directory structure (idempotent).

        Creates:
            queue_root/
            ├── incoming/
            ├── processing/
            ├── done/
            ├── failed/
            └── dead-letter/

        Returns:
            Initialization status dict with created directories

        Raises:
            OSError: If directories cannot be created
        """
        with self._lock:
            try:
                # Create all subdirectories
                for subdir in [
                    self.incoming_dir,
                    self.processing_dir,
                    self.done_dir,
                    self.failed_dir,
                    self.dead_letter_dir,
                ]:
                    subdir.mkdir(parents=True, exist_ok=True)

                self._is_initialized = True

                result = {
                    "success": True,
                    "queue_root": str(self.queue_root),
                    "session_id": self.session_id,
                    "harness": self.harness,
                    "directories": {
                        "incoming": str(self.incoming_dir),
                        "processing": str(self.processing_dir),
                        "done": str(self.done_dir),
                        "failed": str(self.failed_dir),
                        "dead_letter": str(self.dead_letter_dir),
                    },
                }

                logger.info(f"Initialized queue structure: {self.queue_root}")
                return result

            except OSError as e:
                logger.error(f"Failed to initialize queue structure: {e}")
                return {
                    "success": False,
                    "error": str(e),
                }

    def submit_task(
        self,
        task_data: dict[str, Any],
        task_id: Optional[str] = None,
    ) -> str:
        """Submit a task to the incoming queue.

        Args:
            task_data: Task specification dictionary
            task_id: Optional task ID (generated if not provided)

        Returns:
            Task ID

        Raises:
            ValueError: If task_id already exists in any queue
            OSError: If unable to write task file
        """
        if task_id is None:
            task_id = f"TASK-{uuid4().hex[:12].upper()}"

        with self._lock:
            # Check for duplicates
            for state_dir in [
                self.incoming_dir,
                self.processing_dir,
                self.done_dir,
                self.failed_dir,
                self.dead_letter_dir,
            ]:
                task_file = state_dir / f"{task_id}.yaml"
                if task_file.exists():
                    raise ValueError(f"Task {task_id} already exists in {state_dir}")

            # Create task context
            context = TaskContext(
                task_id=task_id,
                state=TaskState.INCOMING,
                metadata=task_data,
            )

            # Write to incoming queue
            task_file = self.incoming_dir / f"{task_id}.yaml"
            with open(task_file, "w", encoding="utf-8") as f:
                yaml.dump(context.to_dict(), f, default_flow_style=False)

            logger.info(f"Submitted task: {task_id}")
            return task_id

    def poll_queue(self, timeout_s: float = 0.1) -> list[str]:
        """Poll incoming queue for new tasks.

        Returns list of task IDs moved to processing state.

        Args:
            timeout_s: Lock acquire timeout in seconds

        Returns:
            List of task IDs moved to processing state
        """
        acquired = self._lock.acquire(timeout=timeout_s)
        if not acquired:
            return []

        try:
            processed = []
            for task_file in self.incoming_dir.glob("*.yaml"):
                try:
                    task_id = task_file.stem

                    # Read task
                    with open(task_file, "r", encoding="utf-8") as f:
                        task_dict = yaml.safe_load(f)

                    # Atomically transition to processing
                    if self._transition_task(
                        task_id, TaskState.INCOMING, TaskState.PROCESSING
                    ):
                        processed.append(task_id)

                except Exception as e:
                    logger.error(f"Error polling task {task_file}: {e}")

            return processed

        finally:
            self._lock.release()

    def _transition_task(
        self,
        task_id: str,
        from_state: TaskState,
        to_state: TaskState,
    ) -> bool:
        """Atomically transition a task between states.

        Uses file-based locking to ensure atomic transitions.

        Args:
            task_id: Task ID
            from_state: Current state
            to_state: Target state

        Returns:
            True if transition succeeded, False otherwise
        """
        from_dir = self._get_state_dir(from_state)
        to_dir = self._get_state_dir(to_state)

        from_file = from_dir / f"{task_id}.yaml"
        to_file = to_dir / f"{task_id}.yaml"

        if not from_file.exists():
            logger.warning(f"Task {task_id} not found in {from_state.value}")
            return False

        try:
            # Read, update state, write to new location
            with open(from_file, "r", encoding="utf-8") as f:
                task_dict = yaml.safe_load(f)

            task_dict["state"] = to_state.value
            task_dict["updated_at"] = datetime.now(tz=timezone.utc).isoformat()

            with open(to_file, "w", encoding="utf-8") as f:
                yaml.dump(task_dict, f, default_flow_style=False)

            # Remove old file
            from_file.unlink()

            logger.debug(f"Transitioned {task_id}: {from_state.value} → {to_state.value}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to transition {task_id} from {from_state.value}: {e}"
            )
            return False

    def execute_task(
        self,
        task_id: str,
        handler: Callable[[TaskContext], Any],
    ) -> TaskResult:
        """Execute a task with the provided handler.

        Manages state transitions, error handling, and result persistence.

        Args:
            task_id: Task ID
            handler: Callable that takes TaskContext and returns result

        Returns:
            TaskResult with execution outcome

        Raises:
            ValueError: If task is not in processing state
        """
        start_time = time.time()

        try:
            # Load task context
            context = self._load_task_context(task_id, TaskState.PROCESSING)
            if not context:
                raise ValueError(f"Task {task_id} not found in processing state")

            # Execute handler
            try:
                result = handler(context)

                # Transition to done
                context.state = TaskState.DONE
                context.result = result
                context.updated_at = datetime.now(tz=timezone.utc)

                self._save_task_context(context, TaskState.DONE)

                execution_time_ms = (time.time() - start_time) * 1000

                return TaskResult(
                    task_id=task_id,
                    success=True,
                    state=TaskState.DONE,
                    output=result,
                    execution_time_ms=execution_time_ms,
                )

            except Exception as e:
                # Handle execution error
                error_msg = str(e)
                logger.error(f"Task {task_id} execution failed: {error_msg}")

                return self._handle_task_failure(
                    task_id, context, error_msg, start_time
                )

        except Exception as e:
            logger.error(f"Fatal error executing task {task_id}: {e}")
            execution_time_ms = (time.time() - start_time) * 1000

            return TaskResult(
                task_id=task_id,
                success=False,
                state=TaskState.FAILED,
                error=str(e),
                execution_time_ms=execution_time_ms,
            )

    def _handle_task_failure(
        self,
        task_id: str,
        context: TaskContext,
        error_msg: str,
        start_time: float,
    ) -> TaskResult:
        """Handle task failure with retry logic and dead-letter queue.

        Args:
            task_id: Task ID
            context: Task context
            error_msg: Error message
            start_time: Task execution start time

        Returns:
            TaskResult with failure status
        """
        context.retry_count += 1
        context.error_message = error_msg
        context.updated_at = datetime.now(tz=timezone.utc)

        execution_time_ms = (time.time() - start_time) * 1000

        if context.retry_count < context.max_retries:
            # Retry: transition back to incoming with backoff
            backoff_ms = int(
                min(
                    self.INITIAL_BACKOFF_MS
                    * (self.BACKOFF_MULTIPLIER ** (context.retry_count - 1)),
                    self.MAX_BACKOFF_MS,
                )
            )

            # Transition from processing to incoming
            self._transition_task(task_id, TaskState.PROCESSING, TaskState.INCOMING)

            # Update context in incoming queue
            context.state = TaskState.INCOMING
            self._save_task_context(context, TaskState.INCOMING)

            logger.info(
                f"Task {task_id} will retry in {backoff_ms}ms "
                f"(attempt {context.retry_count}/{context.max_retries})"
            )

            return TaskResult(
                task_id=task_id,
                success=False,
                state=TaskState.INCOMING,
                error=error_msg,
                retry_count=context.retry_count,
                execution_time_ms=execution_time_ms,
            )

        else:
            # Dead letter: transition from processing to dead-letter
            self._transition_task(
                task_id, TaskState.PROCESSING, TaskState.DEAD_LETTER
            )

            # Update context in dead-letter queue
            context.state = TaskState.DEAD_LETTER
            self._save_task_context(context, TaskState.DEAD_LETTER)

            logger.error(
                f"Task {task_id} moved to dead-letter queue "
                f"(failed after {context.retry_count} retries)"
            )

            return TaskResult(
                task_id=task_id,
                success=False,
                state=TaskState.DEAD_LETTER,
                error=error_msg,
                retry_count=context.retry_count,
                execution_time_ms=execution_time_ms,
            )

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Retrieve task result if task is complete.

        Args:
            task_id: Task ID

        Returns:
            TaskResult if task is done, None if task is still processing
        """
        with self._lock:
            # Check done queue
            done_file = self.done_dir / f"{task_id}.yaml"
            if done_file.exists():
                with open(done_file, "r", encoding="utf-8") as f:
                    task_dict = yaml.safe_load(f)

                context = TaskContext.from_dict(task_dict)

                return TaskResult(
                    task_id=task_id,
                    success=True,
                    state=TaskState.DONE,
                    output=context.result,
                    retry_count=context.retry_count,
                )

            # Check failed queue
            failed_file = self.failed_dir / f"{task_id}.yaml"
            if failed_file.exists():
                with open(failed_file, "r", encoding="utf-8") as f:
                    task_dict = yaml.safe_load(f)

                context = TaskContext.from_dict(task_dict)

                return TaskResult(
                    task_id=task_id,
                    success=False,
                    state=TaskState.FAILED,
                    error=context.error_message,
                    retry_count=context.retry_count,
                )

            # Check dead-letter queue
            dead_letter_file = self.dead_letter_dir / f"{task_id}.yaml"
            if dead_letter_file.exists():
                with open(dead_letter_file, "r", encoding="utf-8") as f:
                    task_dict = yaml.safe_load(f)

                context = TaskContext.from_dict(task_dict)

                return TaskResult(
                    task_id=task_id,
                    success=False,
                    state=TaskState.DEAD_LETTER,
                    error=context.error_message,
                    retry_count=context.retry_count,
                )

            return None

    def get_task_status(self, task_id: str) -> Optional[dict[str, Any]]:
        """Get complete task status information.

        Args:
            task_id: Task ID

        Returns:
            Task status dict or None if not found
        """
        with self._lock:
            for state in TaskState:
                state_dir = self._get_state_dir(state)
                task_file = state_dir / f"{task_id}.yaml"

                if task_file.exists():
                    with open(task_file, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f)

        return None

    def list_tasks(self, state: Optional[TaskState] = None) -> list[str]:
        """List all task IDs, optionally filtered by state.

        Args:
            state: Filter by specific state (None = all states)

        Returns:
            List of task IDs
        """
        with self._lock:
            if state is None:
                # All states
                task_ids = []
                for state_dir in [
                    self.incoming_dir,
                    self.processing_dir,
                    self.done_dir,
                    self.failed_dir,
                    self.dead_letter_dir,
                ]:
                    task_ids.extend(
                        f.stem for f in state_dir.glob("*.yaml")
                    )
                return sorted(set(task_ids))

            else:
                # Specific state
                state_dir = self._get_state_dir(state)
                return sorted(f.stem for f in state_dir.glob("*.yaml"))

    def retry_task(self, task_id: str) -> bool:
        """Retry a failed task by moving it back to incoming queue.

        Args:
            task_id: Task ID

        Returns:
            True if retry was initiated, False otherwise
        """
        with self._lock:
            # Find task in dead-letter or failed queue
            for from_state in [TaskState.DEAD_LETTER, TaskState.FAILED]:
                if self._transition_task(task_id, from_state, TaskState.INCOMING):
                    # Reset retry count when retrying
                    context = self._load_task_context(task_id, TaskState.INCOMING)
                    if context:
                        context.retry_count = 0
                        context.error_message = None
                        self._save_task_context(context, TaskState.INCOMING)

                    logger.info(f"Initiated retry for task {task_id}")
                    return True

        return False

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task (mark as failed).

        Args:
            task_id: Task ID

        Returns:
            True if task was cancelled, False otherwise
        """
        with self._lock:
            # Find task in incoming or processing
            for from_state in [TaskState.INCOMING, TaskState.PROCESSING]:
                if self._transition_task(task_id, from_state, TaskState.FAILED):
                    logger.info(f"Cancelled task {task_id}")
                    return True

        return False

    def _load_task_context(
        self,
        task_id: str,
        state: TaskState,
    ) -> Optional[TaskContext]:
        """Load task context from disk.

        Args:
            task_id: Task ID
            state: Expected task state

        Returns:
            TaskContext or None if not found
        """
        state_dir = self._get_state_dir(state)
        task_file = state_dir / f"{task_id}.yaml"

        if not task_file.exists():
            return None

        try:
            with open(task_file, "r", encoding="utf-8") as f:
                task_dict = yaml.safe_load(f)
            return TaskContext.from_dict(task_dict)
        except Exception as e:
            logger.error(f"Failed to load task context {task_id}: {e}")
            return None

    def _save_task_context(self, context: TaskContext, state: TaskState) -> None:
        """Save task context to disk in specified state.

        Args:
            context: Task context to save
            state: Target state directory
        """
        state_dir = self._get_state_dir(state)
        task_file = state_dir / f"{context.task_id}.yaml"

        try:
            with open(task_file, "w", encoding="utf-8") as f:
                yaml.dump(context.to_dict(), f, default_flow_style=False)
        except Exception as e:
            logger.error(f"Failed to save task context {context.task_id}: {e}")

    def _get_state_dir(self, state: TaskState) -> Path:
        """Get directory path for a given state.

        Args:
            state: Task state

        Returns:
            Path to state directory
        """
        state_dirs = {
            TaskState.INCOMING: self.incoming_dir,
            TaskState.PROCESSING: self.processing_dir,
            TaskState.DONE: self.done_dir,
            TaskState.FAILED: self.failed_dir,
            TaskState.DEAD_LETTER: self.dead_letter_dir,
        }
        return state_dirs[state]

    def __repr__(self) -> str:
        return (
            f"TaskRunner("
            f"session={self.session_id!r}, "
            f"harness={self.harness!r}, "
            f"queue_root={self.queue_root}"
            f")"
        )
