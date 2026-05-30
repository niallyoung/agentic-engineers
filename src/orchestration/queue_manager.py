"""
Queue Manager - Standalone module for atomic queue operations.

Extends the base QueueManager from agents/orchestrator.py with:
- failed/ directory support for error recovery
- Explicit move_to_failed() method
- Convenience wrappers for daemon-mode polling

This module re-exports QueueManager from orchestrator.py and adds
the failed-state extensions needed by the queue polling daemon.

Usage:
    from src.orchestration.queue_manager import QueueManager, ExtendedQueueManager

    # Use ExtendedQueueManager for daemon mode (includes failed/ support)
    qm = ExtendedQueueManager(queue_dir="/path/to/queue")
    qm.move_to_failed("task-id", reason="agent timeout")
"""

import shutil
import yaml
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Re-export base QueueManager for backwards compatibility
from src.orchestration.agents.orchestrator import (
    QueueManager,
    sanitize_path_component,
    ensure_within_directory,
)

logger = logging.getLogger(__name__)

__all__ = ["QueueManager", "ExtendedQueueManager"]


class ExtendedQueueManager(QueueManager):
    """
    Extended QueueManager with failed/ directory support.

    Adds:
    - failed/ directory for tasks that exceed retry limits or timeout
    - move_to_failed() atomic transition
    - list_failed_tasks() for monitoring
    - recover_failed_task() to retry failed tasks

    All transitions are atomic (write-then-move pattern).
    """

    def __init__(self, queue_dir: Optional[str] = None, agent_context: Optional[str] = None):
        super().__init__(queue_dir=queue_dir, agent_context=agent_context)
        # Add failed directory alongside existing queue dirs
        self.failed_dir = self.session_queue_dir / "failed"
        self.failed_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"ExtendedQueueManager: failed_dir={self.failed_dir}")

    def move_to_failed(
        self,
        task_id: str,
        reason: str = "unknown",
        from_state: str = "processing",
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Move a task to the failed/ directory atomically.

        Args:
            task_id:    Task identifier (used to find task file)
            reason:     Human-readable failure reason
            from_state: Source state ("incoming" or "processing")
            metadata:   Optional additional metadata to attach

        Returns:
            Dict with success, moved_from, moved_to, task_id, filename, timestamp, message

        Raises:
            FileNotFoundError: Task file not found in source state
            RuntimeError: Atomic transition failed
        """
        # Determine source directory
        if from_state == "incoming":
            from_dir = self.incoming_dir
        elif from_state == "processing":
            from_dir = self.processing_dir
        else:
            raise ValueError(f"Invalid from_state for failed transition: '{from_state}'")

        # Sanitize the task_id before it is used either to match files or to
        # build the destination filename (prevents path traversal / poisoning).
        task_id = sanitize_path_component(task_id, field="task_id")

        # Find task file
        task_filename = None
        for task_file in sorted(from_dir.glob("*.yaml")):
            if task_id in task_file.name:
                task_filename = task_file.name
                break

        if not task_filename:
            raise FileNotFoundError(f"Task '{task_id}' not found in '{from_state}' state")

        from_path = from_dir / task_filename

        # Read task data
        with open(from_path, "r") as f:
            content = f.read()
        docs = [d.strip() for d in content.split("---") if d.strip()]
        task_data = yaml.safe_load(docs[0]) if docs else yaml.safe_load(content)

        if not isinstance(task_data, dict):
            raise ValueError(f"Task file is not a valid YAML dictionary: {from_path}")

        # Attach failure metadata
        now = datetime.now().isoformat()
        task_data["_failed_at"] = now
        task_data["_failure_reason"] = reason
        task_data["_failed_from_state"] = from_state

        if metadata:
            task_data.update(metadata)

        # Extend audit trail
        if "_audit_trail" not in task_data:
            task_data["_audit_trail"] = []
        task_data["_audit_trail"].append(
            {
                "timestamp": now,
                "action": "move_to_failed",
                "from_state": from_state,
                "to_state": "failed",
                "task_id": task_id,
                "reason": reason,
            }
        )

        # Atomic write: temp file → rename
        failed_filename = f"{task_id}-FAILED.yaml"
        to_path = self.failed_dir / failed_filename
        temp_path = self.failed_dir / f".tmp_{failed_filename}"
        ensure_within_directory(to_path, self.failed_dir, field="failed_path")
        ensure_within_directory(temp_path, self.failed_dir, field="failed_temp_path")

        with open(temp_path, "w") as f:
            yaml.dump(task_data, f, default_flow_style=False, sort_keys=False)

        # Verify temp file
        with open(temp_path, "r") as f:
            yaml.safe_load(f.read())

        shutil.move(str(temp_path), str(to_path))

        # Remove from source
        if from_path.exists():
            from_path.unlink()

        logger.info(f"Task '{task_id}' moved to failed/: {reason}")
        return {
            "success": True,
            "moved_from": from_state,
            "moved_to": "failed",
            "task_id": task_id,
            "filename": failed_filename,
            "timestamp": now,
            "message": f"Task '{task_id}' moved to failed: {reason}",
        }

    def list_failed_tasks(self) -> List[str]:
        """List all task files in the failed/ directory."""
        if not self.failed_dir.exists():
            return []
        return sorted([f.name for f in self.failed_dir.glob("*.yaml")])

    def recover_failed_task(self, task_id: str) -> Dict:
        """
        Move a failed task back to incoming/ for retry.

        Args:
            task_id: Task identifier

        Returns:
            Dict with success, moved_from, moved_to, task_id, filename, timestamp, message

        Raises:
            FileNotFoundError: Task not found in failed/
        """
        # Find task in failed/
        task_filename = None
        # Sanitize task_id before matching / filename reconstruction.
        task_id = sanitize_path_component(task_id, field="task_id")
        for task_file in sorted(self.failed_dir.glob("*.yaml")):
            if task_id in task_file.name:
                task_filename = task_file.name
                break

        if not task_filename:
            raise FileNotFoundError(f"Task '{task_id}' not found in failed/")

        from_path = self.failed_dir / task_filename

        with open(from_path, "r") as f:
            content = f.read()
        docs = [d.strip() for d in content.split("---") if d.strip()]
        task_data = yaml.safe_load(docs[0]) if docs else yaml.safe_load(content)

        if not isinstance(task_data, dict):
            raise ValueError(f"Task file is not a valid YAML dictionary: {from_path}")

        now = datetime.now().isoformat()

        # Clear failure markers
        task_data.pop("_failed_at", None)
        task_data.pop("_failure_reason", None)
        task_data.pop("_failed_from_state", None)

        if "_audit_trail" not in task_data:
            task_data["_audit_trail"] = []
        task_data["_audit_trail"].append(
            {
                "timestamp": now,
                "action": "recover_failed_task",
                "from_state": "failed",
                "to_state": "incoming",
                "task_id": task_id,
            }
        )

        # Determine recovery filename (strip -FAILED suffix)
        recovery_filename = task_filename.replace("-FAILED.yaml", ".yaml")
        if not recovery_filename.endswith(".yaml"):
            recovery_filename = f"{task_id}.yaml"

        to_path = self.incoming_dir / recovery_filename
        temp_path = self.incoming_dir / f".tmp_{recovery_filename}"
        ensure_within_directory(to_path, self.incoming_dir, field="recovery_path")
        ensure_within_directory(temp_path, self.incoming_dir, field="recovery_temp_path")

        with open(temp_path, "w") as f:
            yaml.dump(task_data, f, default_flow_style=False, sort_keys=False)

        with open(temp_path, "r") as f:
            yaml.safe_load(f.read())

        shutil.move(str(temp_path), str(to_path))

        if from_path.exists():
            from_path.unlink()

        logger.info(f"Task '{task_id}' recovered from failed/ to incoming/")
        return {
            "success": True,
            "moved_from": "failed",
            "moved_to": "incoming",
            "task_id": task_id,
            "filename": recovery_filename,
            "timestamp": now,
            "message": f"Task '{task_id}' recovered to incoming/ for retry",
        }
