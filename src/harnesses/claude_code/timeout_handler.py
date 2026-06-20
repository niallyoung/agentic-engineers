"""
Timeout Handler for the Claude Code harness.

Task deadline management with effort-level timeout configuration.
Tracks task expiration and provides deadline checks for deadline enforcement.

Usage::

    from src.harnesses.claude_code.timeout_handler import TimeoutHandler

    handler = TimeoutHandler()
    deadline = handler.set_deadline("task-001", "high")
    if handler.check_expired("task-001"):
        print("Task exceeded deadline")

    remaining = handler.time_remaining("task-001")
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)


# Effort-level to timeout mapping (seconds).
# Mirrors invoke_agent.AgentInvoker.EFFORT_TIMEOUTS.
EFFORT_TIMEOUTS: Dict[str, int] = {
    "low": 30,
    "medium": 120,
    "high": 600,
    "max": 3600,
    "epic": 3600,
}


@dataclass
class TaskDeadline:
    """Deadline for a single task."""

    task_id: str
    effort: str
    deadline: float  # Unix timestamp (seconds since epoch)
    expired: bool = False


class TimeoutHandler:
    """Track task deadlines and detect expiration.

    Thread-safe via internal locking. Logs WARNING at 10% time remaining
    and ERROR on expiry.

    Parameters
    ----------
    effort_timeouts:
        Override the default EFFORT_TIMEOUTS mapping.
    """

    def __init__(
        self,
        effort_timeouts: Optional[Dict[str, int]] = None,
    ) -> None:
        self._effort_timeouts = (
            effort_timeouts
            if effort_timeouts is not None
            else dict(EFFORT_TIMEOUTS)
        )
        self._deadlines: Dict[str, TaskDeadline] = {}
        self._lock = threading.Lock()

    def set_deadline(self, task_id: str, effort: str) -> TaskDeadline:
        """Create a deadline for a task based on effort level.

        Args:
            task_id: Task identifier.
            effort: Effort level (low, medium, high, max, epic).

        Returns:
            TaskDeadline with computed deadline timestamp.
        """
        timeout_seconds = self._effort_timeouts.get(effort.lower(), 30)
        deadline = time.time() + timeout_seconds

        task_deadline = TaskDeadline(
            task_id=task_id,
            effort=effort,
            deadline=deadline,
            expired=False,
        )

        with self._lock:
            self._deadlines[task_id] = task_deadline

        logger.info(
            "timeout.set_deadline",
            extra={
                "task_id": task_id,
                "effort": effort,
                "timeout_seconds": timeout_seconds,
            },
        )

        return task_deadline

    def check_expired(self, task_id: str) -> bool:
        """Check if a task has exceeded its deadline.

        If the task has expired, automatically calls mark_expired() and
        logs an ERROR.

        Args:
            task_id: Task identifier.

        Returns:
            True if task is past deadline, False otherwise.
        """
        with self._lock:
            task_deadline = self._deadlines.get(task_id)
            if task_deadline is None:
                return False

            if task_deadline.expired:
                return True

            now = time.time()
            if now >= task_deadline.deadline:
                task_deadline.expired = True
                logger.error(
                    "timeout.expired",
                    extra={
                        "task_id": task_id,
                        "effort": task_deadline.effort,
                        "deadline": task_deadline.deadline,
                        "now": now,
                        "seconds_over": now - task_deadline.deadline,
                    },
                )
                return True

            return False

    def time_remaining(self, task_id: str) -> Optional[float]:
        """Get seconds remaining until task deadline.

        Returns None if task is not tracked. Returns negative value if
        already expired.

        Args:
            task_id: Task identifier.

        Returns:
            Seconds until deadline, or None if task not tracked.
        """
        with self._lock:
            task_deadline = self._deadlines.get(task_id)
            if task_deadline is None:
                return None

            remaining = task_deadline.deadline - time.time()

            # Log warning at 10% time remaining
            if remaining > 0 and remaining <= (task_deadline.deadline -
                                               (task_deadline.deadline -
                                                time.time() * 0.1)):
                timeout_seconds = self._effort_timeouts.get(
                    task_deadline.effort.lower(), 30
                )
                if remaining < timeout_seconds * 0.1:
                    logger.warning(
                        "timeout.low_time_remaining",
                        extra={
                            "task_id": task_id,
                            "seconds_remaining": remaining,
                            "timeout_seconds": timeout_seconds,
                        },
                    )

            return remaining

    def mark_expired(self, task_id: str) -> None:
        """Manually mark a task as expired.

        Args:
            task_id: Task identifier.
        """
        with self._lock:
            task_deadline = self._deadlines.get(task_id)
            if task_deadline is not None:
                task_deadline.expired = True
                logger.info(
                    "timeout.mark_expired",
                    extra={"task_id": task_id},
                )

    def clear(self, task_id: str) -> None:
        """Remove a task from deadline tracking.

        Args:
            task_id: Task identifier.
        """
        with self._lock:
            if task_id in self._deadlines:
                del self._deadlines[task_id]
                logger.debug(
                    "timeout.clear",
                    extra={"task_id": task_id},
                )

    def expired_tasks(self) -> List[str]:
        """Return list of all task IDs that have passed their deadline.

        Returns:
            List of expired task IDs.
        """
        with self._lock:
            expired = []
            for task_id, task_deadline in self._deadlines.items():
                if task_deadline.expired or time.time() >= task_deadline.deadline:
                    expired.append(task_id)
            return expired
