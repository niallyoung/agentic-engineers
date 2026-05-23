"""
SubTask Validators Module

Validates sub-task creation rules:
  - parent_task_id existence and reachability
  - task_tier depth limits (max 5)
  - sub-task scope subset validation
  - max-width enforcement (10 children per parent)
"""

import json
from pathlib import Path
from typing import Optional, Tuple


MAX_TASK_TIER = 5
MAX_CHILDREN_PER_PARENT = 10


class SubTaskValidator:
    """Validate sub-task creation rules for DELEGATE blocks."""

    def __init__(self, queue_path: Path):
        """
        Initialize with the session queue directory.

        Args:
            queue_path: Path to the session queue directory (contains
                        incoming/, processing/, done/, failed/ sub-dirs).
        """
        self.queue_path = Path(queue_path)

    # ------------------------------------------------------------------
    # Public validation API
    # ------------------------------------------------------------------

    def validate_parent_task_id(self, parent_task_id: str) -> Tuple[bool, str]:
        """
        Verify parent task exists in done/, processing/, or incoming/.

        A parent is valid even if it is still *processing* (the agent that
        created this sub-task is the same agent that is processing the
        parent, so the parent file will be in processing/).

        Args:
            parent_task_id: Parent task ID to check.

        Returns:
            (valid: bool, error_msg: str)  — error_msg is '' when valid.
        """
        if not parent_task_id or not isinstance(parent_task_id, str):
            return False, "parent_task_id must be a non-empty string"

        for state in ("incoming", "processing", "done"):
            candidate = self.queue_path / state / f"{parent_task_id}.json"
            if candidate.exists():
                return True, ""

        return (
            False,
            f"Parent task '{parent_task_id}' not found in incoming/, processing/, or done/",
        )

    def validate_task_tier(
        self, parent_task_id: str, proposed_tier: int
    ) -> Tuple[bool, str]:
        """
        Verify that proposed_tier == parent_tier + 1 and does not exceed MAX_TASK_TIER.

        Args:
            parent_task_id: ID of the parent task.
            proposed_tier:  The task_tier value the caller wants to assign.

        Returns:
            (valid: bool, error_msg: str)
        """
        if proposed_tier > MAX_TASK_TIER:
            return (
                False,
                f"task_tier {proposed_tier} exceeds maximum allowed depth ({MAX_TASK_TIER})",
            )

        parent_task = self._load_task(parent_task_id)
        if parent_task is None:
            return False, f"Cannot load parent task '{parent_task_id}' to verify tier"

        parent_tier = parent_task.get("task_tier", 0)
        expected_tier = parent_tier + 1

        if proposed_tier != expected_tier:
            return (
                False,
                f"task_tier must be parent_tier + 1 ({parent_tier} + 1 = {expected_tier}), "
                f"got {proposed_tier}",
            )

        if expected_tier > MAX_TASK_TIER:
            return (
                False,
                f"Adding sub-task would exceed maximum depth: parent is at tier "
                f"{parent_tier}, max is {MAX_TASK_TIER}",
            )

        return True, ""

    def validate_sub_task_scope(
        self, scope: str, parent_scope: str
    ) -> Tuple[bool, str]:
        """
        Verify that child scope is a (conceptual) subset of parent scope.

        The check is intentionally lightweight — it uses keyword overlap to
        avoid false rejections caused by legitimate paraphrasing while still
        catching completely unrelated scopes.

        Rules:
          • Child scope must share at least one non-trivial keyword (≥4 chars,
            not a stop-word) with parent scope, OR
          • Child scope word count must be ≤ parent scope word count
            (narrowing is fine; broadening is a red-flag).

        Args:
            scope:        Child task scope string.
            parent_scope: Parent task scope string.

        Returns:
            (valid: bool, error_msg: str)
        """
        if not scope or not parent_scope:
            return False, "Both scope and parent_scope must be non-empty strings"

        _STOP_WORDS = {
            "the", "and", "for", "with", "that", "this", "from", "will",
            "into", "task", "work", "code", "all", "each", "only", "been",
            "have", "are", "was", "were", "not", "but", "its", "such",
        }

        def _keywords(text: str):
            return {
                w.lower()
                for w in text.split()
                if len(w) >= 4 and w.lower() not in _STOP_WORDS
            }

        child_kw = _keywords(scope)
        parent_kw = _keywords(parent_scope)

        overlap = child_kw & parent_kw
        if overlap:
            return True, ""

        # Fallback: narrowing by word count is always fine
        if len(scope.split()) <= len(parent_scope.split()):
            return True, ""

        return (
            False,
            f"Child scope appears unrelated to parent scope "
            f"(no keyword overlap and scope is broader). "
            f"Child keywords: {sorted(child_kw)[:5]}, "
            f"Parent keywords: {sorted(parent_kw)[:5]}",
        )

    def validate_child_count(self, parent_task_id: str) -> Tuple[bool, int]:
        """
        Check whether the parent task has reached the child limit.

        Args:
            parent_task_id: Parent task ID.

        Returns:
            (within_limit: bool, current_child_count: int)
        """
        count = self._count_children(parent_task_id)
        return count < MAX_CHILDREN_PER_PARENT, count

    def calculate_task_tier(self, parent_task_id: Optional[str]) -> int:
        """
        Auto-calculate the correct task_tier for a new task.

        Args:
            parent_task_id: Parent task ID, or None for a root task.

        Returns:
            int — 0 for root tasks, parent_tier + 1 for sub-tasks.

        Raises:
            ValueError: If the computed tier would exceed MAX_TASK_TIER.
        """
        if parent_task_id is None:
            return 0

        parent_task = self._load_task(parent_task_id)
        if parent_task is None:
            # Parent not found — default to tier 1 and let validate_task_tier
            # surface the proper error.
            return 1

        parent_tier = parent_task.get("task_tier", 0)
        new_tier = parent_tier + 1

        if new_tier > MAX_TASK_TIER:
            raise ValueError(
                f"Cannot create sub-task: parent is at tier {parent_tier}, "
                f"maximum allowed is {MAX_TASK_TIER}"
            )

        return new_tier

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_task(self, task_id: str) -> Optional[dict]:
        """Load a task dict from any queue state, or None if not found."""
        for state in ("incoming", "processing", "done", "failed"):
            candidate = self.queue_path / state / f"{task_id}.json"
            if candidate.exists():
                try:
                    with open(candidate) as fh:
                        return json.load(fh)
                except (json.JSONDecodeError, IOError):
                    return None
        return None

    def _count_children(self, parent_task_id: str) -> int:
        """Count all tasks whose parent_task_id matches the given value."""
        count = 0
        for state in ("incoming", "processing", "done", "failed"):
            state_path = self.queue_path / state
            if not state_path.exists():
                continue
            for task_file in state_path.glob("*.json"):
                try:
                    with open(task_file) as fh:
                        task = json.load(fh)
                    if task.get("parent_task_id") == parent_task_id:
                        count += 1
                except (json.JSONDecodeError, IOError):
                    continue
        return count
