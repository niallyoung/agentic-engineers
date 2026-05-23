"""
Queue Operations Module

Atomic queue operations for DELEGATE/HANDBACK workflow with cycle detection,
rate limiting, and validation.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import hashlib

from .validators import DelegateValidator, HandbackValidator, CycleDetector
from .rate_limiter import RateLimiter
from .consistency import AtomicQueueOps
from .subtask_validators import SubTaskValidator

# ---------------------------------------------------------------------------
# queue-isolation integration (optional — graceful fallback)
# ---------------------------------------------------------------------------
_QUEUE_ISOLATION_SCRIPTS = (
    Path(__file__).parent.parent.parent  # src/skills/
    / "_meta" / "queue-isolation" / "scripts"
)

def _try_import_queue_isolation():
    """Attempt to import queue_isolation; return module or None on failure."""
    try:
        if str(_QUEUE_ISOLATION_SCRIPTS) not in sys.path:
            sys.path.insert(0, str(_QUEUE_ISOLATION_SCRIPTS))
        import queue_isolation as _qi  # noqa: PLC0415
        return _qi
    except ImportError:
        return None


class QueueOperations:
    """Atomic queue operations for DELEGATE/HANDBACK workflow."""
_DEFAULT_QUEUE_PATH = "~/.agentic-engineers/artifacts"


class QueueOperations:
    """Atomic queue operations for DELEGATE/HANDBACK workflow."""

    def __init__(
        self,
        session_id: str,
        queue_path: str = _DEFAULT_QUEUE_PATH,
        harness: Optional[str] = None,
    ):
        """
        Initialize with session isolation.

        When the ``queue-isolation`` skill is available **and** no explicit
        ``queue_path`` override is provided, the queue is automatically scoped to
        ``~/.agentic-engineers/artifacts/{session_id}/{harness}/queue/``.

        Passing an explicit ``queue_path`` (e.g., a temporary directory in tests)
        bypasses queue-isolation and uses the legacy session-subdirectory layout
        so that existing tests and deployments remain unaffected.

        Args:
            session_id: Unique session identifier
            queue_path: Root path for queue directories.  Defaults to
                        ``~/.agentic-engineers/artifacts``.  Override in tests with
                        a ``tempfile.TemporaryDirectory`` path.
            harness: AI harness override (auto-detected from env if omitted).
                     Only used when queue-isolation is active.

        Raises:
            ValueError: If session_id is empty
        """
        if not session_id or not isinstance(session_id, str):
            raise ValueError("session_id must be a non-empty string")

        self.session_id = session_id
        _using_default_path = (queue_path == _DEFAULT_QUEUE_PATH)

        # Use queue-isolation only when no explicit queue_path override is given
        qi = _try_import_queue_isolation() if _using_default_path else None
        if qi is not None:
            resolved_harness = harness or qi.detect_harness()
            self.harness = resolved_harness
            queue_root = qi.get_queue_path(session_id, resolved_harness)
            # Initialise the full directory structure (idempotent)
            qi.init_queue_structure(session_id, resolved_harness)
            self.queue_path = queue_root.parent.parent  # <base>/artifacts/
            self.session_queue_path = queue_root         # .../queue/
        else:
            # ---- Legacy / explicit-override path ----
            self.harness = harness or "local"
            self.queue_path = Path(queue_path).expanduser()
            self.session_queue_path = self.queue_path / session_id
            # Ensure queue directories exist
            self._ensure_queue_dirs()

        # Initialize components
        self.validator = DelegateValidator(queue_path=self.session_queue_path)
        self.handback_validator = HandbackValidator()
        self.cycle_detector = CycleDetector(queue_path=self.session_queue_path)
        self.subtask_validator = SubTaskValidator(queue_path=self.session_queue_path)
        # Rate limiter state directory - scoped to session for isolation
        rate_limit_state_dir = self.queue_path / "rate-limits"
        self.rate_limiter = RateLimiter(state_dir=str(rate_limit_state_dir))
        self.atomic_ops = AtomicQueueOps(queue_path=self.session_queue_path)

    def _ensure_queue_dirs(self) -> None:
        """Create queue directory structure if not exists."""
        for state in ["incoming", "processing", "done", "failed"]:
            (self.session_queue_path / state).mkdir(parents=True, exist_ok=True)

    def create_delegate(
        self,
        task_id: str,
        role: str,
        scope: str,
        plan: List[str],
        context: str,
        parent_task_id: Optional[str] = None,
        priority: int = 0,
    ) -> Dict:
        """
        Create DELEGATE and move to incoming/ queue.

        Validates:
          • task_id uniqueness (check incoming/ + processing/ + done/)
          • scope ≥15 words
          • Groups A/B/C validation rules
          • @parent cycle detection (if parent specified)
          • Rate limit: max 100 DELEGATEs/hour per session
          • Rate limit: max 10 sub-tasks per parent task
          • Sub-task: parent_task_id must exist in any queue state
          • Sub-task: task_tier auto-calculated, must not exceed 5
          • Sub-task: child count must not exceed 10 per parent

        Args:
            task_id: Unique task identifier (kebab-case)
            role: Agent role (Engineer, Senior Engineer, etc.)
            scope: Task description (≥15 words)
            plan: List of implementation steps
            context: Additional context information
            parent_task_id: Optional parent task ID for sub-tasks
            priority: Task priority (0-10, default 0)

        Returns:
            {
                "status": "created",
                "task_id": str,
                "timestamp": str,
                "queue_path": str,
                "parent_task_id": Optional[str],
                "task_tier": int,
            }

        Raises:
            ValueError: Validation failed
            RuntimeError: Rate limit exceeded or cycle detected
            FileExistsError: Duplicate task_id
        """
        # Check rate limits
        allowed, rate_info = self.rate_limiter.check_limit(
            self.session_id, parent_task_id
        )
        if not allowed:
            # Distinguish between session rate limit and parent child limit
            if parent_task_id and rate_info.get("children_count", 0) >= rate_info.get(
                "children_limit", 10
            ):
                raise RuntimeError(
                    f"Parent task '{parent_task_id}' already has "
                    f"{rate_info['children_count']} children (max 10 per parent)"
                )
            raise RuntimeError(
                f"Rate limit exceeded: "
                f"{rate_info['tasks_this_hour']}/{rate_info['limit']} tasks/hour"
            )

        # Check for duplicate task_id
        if self._task_exists(task_id):
            raise FileExistsError(f"Task {task_id} already exists")

        # ---- Sub-task validation ----
        task_tier = 0  # default: root task
        if parent_task_id is not None:
            # Validate parent exists
            valid, err = self.subtask_validator.validate_parent_task_id(parent_task_id)
            if not valid:
                raise ValueError(f"Invalid parent_task_id: {err}")

            # Auto-calculate tier (raises ValueError if exceeds max)
            task_tier = self.subtask_validator.calculate_task_tier(parent_task_id)

            # Check child count limit
            within_limit, child_count = self.subtask_validator.validate_child_count(
                parent_task_id
            )
            if not within_limit:
                raise RuntimeError(
                    f"Parent task '{parent_task_id}' already has {child_count} children "
                    f"(max 10 per parent)"
                )

        # Build DELEGATE dict
        delegate = {
            "task_id": task_id,
            "role": role,
            "scope": scope,
            "plan": plan,
            "context": context,
            "parent_task_id": parent_task_id,
            "task_tier": task_tier,
            "priority": priority,
            "created_at": datetime.utcnow().isoformat(),
            "status": "incoming",
        }

        # Validate Groups A/B/C (includes new task_tier/parent_task_id checks)
        valid, errors = self.validator.validate_groups(delegate)
        if not valid:
            raise ValueError(f"DELEGATE validation failed: {', '.join(errors)}")

        # Cycle detection for parent
        if parent_task_id:
            if self.cycle_detector.has_cycle(task_id, parent_task_id):
                raise RuntimeError(
                    f"Cycle detected: {task_id} -> {parent_task_id} creates cycle"
                )

        # Write atomically to incoming/
        task_path = self._write_delegate(delegate)

        # Record rate limit
        self.rate_limiter.record_task(self.session_id, task_id, parent_task_id)

        return {
            "status": "created",
            "task_id": task_id,
            "timestamp": delegate["created_at"],
            "queue_path": str(task_path),
            "parent_task_id": parent_task_id,
            "task_tier": task_tier,
        }

    def validate_delegate(self, delegate: Dict) -> Tuple[bool, List[str]]:
        """
        Pre-flight validation of DELEGATE.

        Returns:
            (valid: bool, errors: List[str])
        """
        return self.validator.validate_groups(delegate)

    def move_task(
        self, task_id: str, from_state: str, to_state: str
    ) -> Dict:
        """
        Atomic move task between queue states.

        States: incoming → processing → done (or failed)
        Implementation: temp-file-then-move for atomicity

        Args:
            task_id: Task identifier
            from_state: Current state (incoming, processing, done, failed)
            to_state: Target state

        Returns:
            {
                "status": "moved",
                "task_id": str,
                "from_state": str,
                "to_state": str,
                "timestamp": str
            }

        Raises:
            FileNotFoundError: Task not found in from_state
            ValueError: Invalid state transition
        """
        valid_states = {"incoming", "processing", "done", "failed"}
        if from_state not in valid_states or to_state not in valid_states:
            raise ValueError(f"Invalid state: must be one of {valid_states}")

        # Find task in from_state
        from_path = self.session_queue_path / from_state / f"{task_id}.json"
        if not from_path.exists():
            raise FileNotFoundError(f"Task {task_id} not found in {from_state}")

        # Atomic move via consistency module
        to_path = self.session_queue_path / to_state / f"{task_id}.json"
        self.atomic_ops.move_file(from_path, to_path)

        return {
            "status": "moved",
            "task_id": task_id,
            "from_state": from_state,
            "to_state": to_state,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def validate_handback(self, task_id: str, handback: Dict) -> Tuple[bool, List[str]]:
        """
        Pre-flight validation of HANDBACK.

        Returns:
            (valid: bool, errors: List[str])
        """
        return self.handback_validator.validate(handback)

    def query_tasks(
        self,
        state: str,
        parent_task_id: Optional[str] = None,
        role: Optional[str] = None,
    ) -> List[Dict]:
        """
        Query tasks by state, parent, and/or role.

        Args:
            state: Queue state (incoming, processing, done, failed)
            parent_task_id: Filter by parent task
            role: Filter by agent role

        Returns:
            List of task metadata (for sub-task aggregation)
        """
        state_path = self.session_queue_path / state
        if not state_path.exists():
            return []

        tasks = []
        for task_file in state_path.glob("*.json"):
            try:
                with open(task_file) as f:
                    task = json.load(f)

                # Apply filters
                if parent_task_id and task.get("parent_task_id") != parent_task_id:
                    continue
                if role and task.get("role") != role:
                    continue

                tasks.append(task)
            except (json.JSONDecodeError, IOError):
                continue

        return tasks

    def get_rate_limit_status(self, session_id: str) -> Dict:
        """
        Get current rate limit usage.

        Returns:
            {
                "tasks_this_hour": int,
                "limit": 100,
                "remaining": int
            }
        """
        status = self.rate_limiter.get_status(session_id)
        return {
            "tasks_this_hour": status["tasks_this_hour"],
            "limit": status["limit"],
            "remaining": status["remaining"],
        }

    def _task_exists(self, task_id: str) -> bool:
        """Check if task exists in any queue state."""
        for state in ["incoming", "processing", "done", "failed"]:
            task_path = self.session_queue_path / state / f"{task_id}.json"
            if task_path.exists():
                return True
        return False

    def _write_delegate(self, delegate: Dict) -> Path:
        """Write DELEGATE atomically to incoming/ queue."""
        task_id = delegate["task_id"]
        incoming_path = self.session_queue_path / "incoming"

        # Use atomic write via consistency module
        task_path = incoming_path / f"{task_id}.json"
        self.atomic_ops.write_atomic(
            task_path, json.dumps(delegate, indent=2, default=str)
        )

        return task_path
