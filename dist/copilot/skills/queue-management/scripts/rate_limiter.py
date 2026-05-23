"""
Rate Limiter Module

Per-session rate limiting for task creation.
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple


class RateLimiter:
    """Per-session rate limiting."""

    # Rate limit constants
    DEFAULT_MAX_PER_HOUR = 100
    DEFAULT_MAX_CHILDREN_PER_PARENT = 10

    def __init__(
        self,
        max_per_hour: int = DEFAULT_MAX_PER_HOUR,
        max_children_per_parent: int = DEFAULT_MAX_CHILDREN_PER_PARENT,
        state_dir: str = "~/.copilot/rate-limits",
    ):
        """
        Initialize rate limiter.

        Args:
            max_per_hour: Max tasks per hour per session (default 100)
            max_children_per_parent: Max sub-tasks per parent (default 10)
            state_dir: Directory to store rate limit state
        """
        self.max_per_hour = max_per_hour
        self.max_children_per_parent = max_children_per_parent
        self.state_dir = Path(state_dir).expanduser()
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def check_limit(
        self, session_id: str, parent_task_id: Optional[str] = None
    ) -> Tuple[bool, Dict]:
        """
        Check if request exceeds rate limit.

        Checks:
          • Per-session: 100 tasks/hour
          • Per-parent: 10 sub-tasks max

        Args:
            session_id: Session identifier
            parent_task_id: Optional parent task ID (for sub-task limits)

        Returns:
            (allowed: bool, status: {
                "tasks_this_hour": int,
                "limit": int,
                "remaining": int,
                "children_count": int (if parent specified),
                "children_limit": int (if parent specified)
            })
        """
        # Check session-level rate limit
        session_status = self._get_session_status(session_id)
        tasks_this_hour = session_status["tasks_this_hour"]

        # Check if over session limit
        session_allowed = tasks_this_hour < self.max_per_hour

        status = {
            "tasks_this_hour": tasks_this_hour,
            "limit": self.max_per_hour,
            "remaining": self.max_per_hour - tasks_this_hour,
        }

        # Check parent-level limit if specified
        if parent_task_id:
            parent_status = self._get_parent_status(session_id, parent_task_id)
            children_count = parent_status["children_count"]

            parent_allowed = children_count < self.max_children_per_parent

            status["children_count"] = children_count
            status["children_limit"] = self.max_children_per_parent
            status["children_remaining"] = (
                self.max_children_per_parent - children_count
            )

            return session_allowed and parent_allowed, status

        return session_allowed, status

    def record_task(
        self,
        session_id: str,
        task_id: str,
        parent_task_id: Optional[str] = None,
    ) -> None:
        """
        Record task creation for rate limit tracking.

        Args:
            session_id: Session identifier
            task_id: Task ID being created
            parent_task_id: Optional parent task ID
        """
        # Record in session log
        session_log = self._get_session_log_path(session_id)
        entry = {
            "task_id": task_id,
            "parent_task_id": parent_task_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        session_log.parent.mkdir(parents=True, exist_ok=True)
        with open(session_log, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_status(self, session_id: str) -> Dict:
        """
        Get current rate limit status for a session.

        Args:
            session_id: Session identifier

        Returns:
            {
                "tasks_this_hour": int,
                "limit": int,
                "remaining": int,
                "reset_at": str (ISO timestamp)
            }
        """
        status = self._get_session_status(session_id)
        return {
            "tasks_this_hour": status["tasks_this_hour"],
            "limit": self.max_per_hour,
            "remaining": self.max_per_hour - status["tasks_this_hour"],
            "reset_at": status.get("reset_at", ""),
        }

    def _get_session_status(self, session_id: str) -> Dict:
        """
        Get task count for session in current hour.

        Returns:
            {
                "tasks_this_hour": int,
                "hour_start": str (ISO timestamp),
                "reset_at": str (ISO timestamp)
            }
        """
        log_path = self._get_session_log_path(session_id)

        # Calculate hour window
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)

        # Count tasks in last hour
        task_count = 0
        if log_path.exists():
            try:
                with open(log_path) as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            entry = json.loads(line)
                            timestamp_str = entry.get("timestamp", "")
                            timestamp = datetime.fromisoformat(timestamp_str)
                            if timestamp > hour_ago:
                                task_count += 1
                        except (json.JSONDecodeError, ValueError):
                            continue
            except IOError:
                pass

        # Calculate next reset
        reset_at = (hour_ago + timedelta(hours=1)).isoformat()

        return {
            "tasks_this_hour": task_count,
            "hour_start": hour_ago.isoformat(),
            "reset_at": reset_at,
        }

    def _get_parent_status(self, session_id: str, parent_task_id: str) -> Dict:
        """
        Get child task count for a parent task.

        Returns:
            {"children_count": int}
        """
        log_path = self._get_session_log_path(session_id)

        child_count = 0
        if log_path.exists():
            try:
                with open(log_path) as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            entry = json.loads(line)
                            if entry.get("parent_task_id") == parent_task_id:
                                child_count += 1
                        except json.JSONDecodeError:
                            continue
            except IOError:
                pass

        return {"children_count": child_count}

    def _get_session_log_path(self, session_id: str) -> Path:
        """Get path to session rate limit log file."""
        return self.state_dir / f"{session_id}.jsonl"
