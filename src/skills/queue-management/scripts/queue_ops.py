"""
Queue Operations Module

Atomic queue operations for DELEGATE/HANDBACK workflow with cycle detection,
rate limiting, and validation.

MANDATORY ENQUEUE CONTRACT
--------------------------
``QueueOperations.enqueue()`` is the ONLY sanctioned way to create a DELEGATE
or HANDBACK file in the queue directory.  Direct file writes to any queue
subdirectory (incoming/, processing/, done/, failed/) bypass schema validation
and are explicitly forbidden.

All agents MUST use the ``queue-management`` skill (and therefore enqueue())
to create queue artifacts.  The method enforces:

  * Canonical schema: ``handoff_type`` (DELEGATE|HANDBACK), ``agent``
    (hyphenated), ``metrics`` (nested object with quality/tokens/cost/
    duration_seconds), ``status`` (success|failure|partial|blocked|escalate).
  * Rejection of legacy fields: ``type``, ``role`` (use ``agent``),
    top-level ``quality_score`` (move inside ``metrics``).
  * Atomic write via ``AtomicQueueOps`` — no partial files.
  * Rate limiting, cycle detection, and duplicate prevention.

See docs/QUEUE-PROTOCOL.md for the full specification.
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
# Canonical schema constants (single source of truth for enqueue validation)
# ---------------------------------------------------------------------------

VALID_HANDOFF_TYPES = {"DELEGATE", "HANDBACK"}

VALID_AGENTS = {
    "orchestrator",
    "engineer",
    "senior-engineer",
    "lead-engineer",
    "principal-engineer",
    "security-engineer",
    "quality-engineer",
    "model-engineer",
}

VALID_STATUSES = {"success", "failure", "partial", "blocked", "escalate"}

# Legacy field names that are no longer accepted in canonical schema
_REJECTED_LEGACY_FIELDS = {
    "type": (
        "Use 'handoff_type' (value: 'DELEGATE' or 'HANDBACK') instead of 'type'. "
        "Old 'type:' field is no longer accepted."
    ),
    "role": (
        "Use 'agent' (hyphenated lowercase, e.g. 'senior-engineer') instead of 'role'. "
        "Old 'role:' field is no longer accepted."
    ),
    "quality_score": (
        "Move 'quality_score' inside the 'metrics' object as 'metrics.quality' (0.0-1.0 float). "
        "Top-level 'quality_score' is no longer accepted."
    ),
}

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


_DEFAULT_QUEUE_PATH = "~/.agentic-engineers"


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
        ``~/.agentic-engineers/{session_id}/{harness}/queue/``.

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

    def enqueue(self, artifact: Dict) -> Dict:
        """
        MANDATORY entry point for creating DELEGATE or HANDBACK queue files.

        This is the ONLY sanctioned way to write a file to any queue
        subdirectory.  Direct file writes to ``incoming/``, ``processing/``,
        ``done/``, or ``failed/`` are forbidden and bypass schema validation.

        Validates canonical schema:
          * ``handoff_type``: must be ``DELEGATE`` or ``HANDBACK``
          * ``agent``: must be hyphenated lowercase agent name
          * ``task_id``: required, kebab-case
          * DELEGATE: requires ``scope`` (≥15 words), ``plan`` (≥2 steps),
            ``context``, ``success_criteria``
          * HANDBACK: requires ``status`` (canonical enum), ``output``,
            ``metrics`` (object with ``quality``, ``tokens``, ``cost``,
            ``duration_seconds``)
          * Legacy fields ``type``, ``role``, ``quality_score`` are rejected
            with clear error messages.
          * Rate limit and duplicate-task-id checks are applied for DELEGATEs.

        Args:
            artifact: Dict representing the DELEGATE or HANDBACK to enqueue.

        Returns:
            {
                "status": "enqueued",
                "handoff_type": str,
                "task_id": str,
                "timestamp": str,
                "queue_path": str,
            }

        Raises:
            ValueError: Schema validation failed — message lists all errors.
            FileExistsError: Duplicate task_id (DELEGATE only).
            RuntimeError: Rate limit exceeded or cycle detected.
        """
        errors: List[str] = []

        # ------------------------------------------------------------------
        # 1. Reject legacy field names immediately with actionable messages
        # ------------------------------------------------------------------
        for legacy_field, guidance in _REJECTED_LEGACY_FIELDS.items():
            if legacy_field in artifact:
                errors.append(f"Rejected legacy field '{legacy_field}': {guidance}")

        if errors:
            raise ValueError(
                "enqueue() rejected artifact with legacy schema fields. "
                "All agents must use canonical schema.\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

        # ------------------------------------------------------------------
        # 2. Validate handoff_type
        # ------------------------------------------------------------------
        handoff_type = artifact.get("handoff_type")
        if not handoff_type:
            errors.append(
                "handoff_type: required — must be 'DELEGATE' or 'HANDBACK'"
            )
        elif handoff_type not in VALID_HANDOFF_TYPES:
            errors.append(
                f"handoff_type: invalid value '{handoff_type}' — "
                f"must be one of {sorted(VALID_HANDOFF_TYPES)}"
            )

        # ------------------------------------------------------------------
        # 3. Validate task_id (common to both types)
        # ------------------------------------------------------------------
        task_id = artifact.get("task_id")
        if not task_id or not isinstance(task_id, str):
            errors.append("task_id: required, must be a non-empty string")
        elif len(task_id) < 3 or len(task_id) > 50:
            errors.append(
                f"task_id: must be 3-50 characters (got {len(task_id)})"
            )
        elif not __import__("re").match(r"^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$", task_id):
            errors.append(
                "task_id: must be kebab-case [a-z0-9-]+ (lowercase, digits, hyphens)"
            )

        # ------------------------------------------------------------------
        # 4. Validate agent
        # ------------------------------------------------------------------
        agent = artifact.get("agent")
        if not agent or not isinstance(agent, str):
            errors.append(
                "agent: required — use hyphenated name e.g. 'senior-engineer'"
            )
        elif agent not in VALID_AGENTS:
            errors.append(
                f"agent: invalid value '{agent}' — "
                f"must be one of {sorted(VALID_AGENTS)}"
            )

        # ------------------------------------------------------------------
        # 5. Type-specific field validation
        # ------------------------------------------------------------------
        if handoff_type == "DELEGATE":
            errors.extend(self._validate_delegate_fields(artifact))
        elif handoff_type == "HANDBACK":
            errors.extend(self._validate_handback_fields(artifact))

        if errors:
            raise ValueError(
                "enqueue() schema validation failed — artifact rejected:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

        # ------------------------------------------------------------------
        # 6. DELEGATE-specific runtime checks (rate limit, duplicate, cycle)
        # ------------------------------------------------------------------
        parent_task_id = artifact.get("parent_task_id")

        if handoff_type == "DELEGATE":
            # Rate limit check
            allowed, rate_info = self.rate_limiter.check_limit(
                self.session_id, parent_task_id
            )
            if not allowed:
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

            # Duplicate task_id check
            if task_id and self._task_exists(task_id):
                raise FileExistsError(
                    f"Task '{task_id}' already exists in queue"
                )

            # Cycle detection
            if parent_task_id and task_id:
                if self.cycle_detector.has_cycle(task_id, parent_task_id):
                    raise RuntimeError(
                        f"Cycle detected: {task_id} -> {parent_task_id} creates a cycle"
                    )

        # ------------------------------------------------------------------
        # 7. Determine target queue state and write atomically
        # ------------------------------------------------------------------
        if handoff_type == "DELEGATE":
            target_state = "incoming"
        else:
            # HANDBACKs land in processing for Orchestrator to pick up
            target_state = "processing"

        artifact_with_meta = {
            **artifact,
            "enqueued_at": datetime.utcnow().isoformat(),
            "queue_state": target_state,
        }

        state_dir = self.session_queue_path / target_state
        state_dir.mkdir(parents=True, exist_ok=True)
        file_path = state_dir / f"{task_id}.json"
        self.atomic_ops.write_atomic(
            file_path, json.dumps(artifact_with_meta, indent=2, default=str)
        )

        # Record rate limit for DELEGATEs
        if handoff_type == "DELEGATE" and task_id:
            self.rate_limiter.record_task(self.session_id, task_id, parent_task_id)

        return {
            "status": "enqueued",
            "handoff_type": handoff_type,
            "task_id": task_id,
            "timestamp": artifact_with_meta["enqueued_at"],
            "queue_path": str(file_path),
        }

    def _validate_delegate_fields(self, artifact: Dict) -> List[str]:
        """Validate DELEGATE-specific required fields. Returns list of errors."""
        errors: List[str] = []

        # scope: required, >=15 words
        scope = artifact.get("scope", "")
        if not scope or not isinstance(scope, str):
            errors.append("scope: required for DELEGATE, must be a string")
        elif len(scope.split()) < 15:
            errors.append(
                f"scope: must be >=15 words (got {len(scope.split())})"
            )

        # plan: required, >=2 steps, each >=3 words
        plan = artifact.get("plan")
        if plan is None:
            errors.append("plan: required for DELEGATE")
        elif not isinstance(plan, list):
            errors.append("plan: must be a list of strings")
        elif len(plan) < 2:
            errors.append(
                f"plan: must have >=2 steps (got {len(plan)})"
            )
        else:
            for i, step in enumerate(plan):
                if not isinstance(step, str):
                    errors.append(f"plan[{i}]: each step must be a string")
                elif len(step.split()) < 3:
                    errors.append(
                        f"plan[{i}]: each step must be >=3 words (got '{step}')"
                    )

        # context: required, >=20 words (string) or non-empty list
        context = artifact.get("context")
        if context is None:
            errors.append("context: required for DELEGATE")
        elif isinstance(context, str):
            if len(context.split()) < 20:
                errors.append(
                    f"context: must be >=20 words when string (got {len(context.split())})"
                )
        elif isinstance(context, list):
            if len(context) == 0:
                errors.append("context: must be non-empty when provided as list")
        else:
            errors.append("context: must be a string or list of strings")

        # success_criteria: required, non-empty list
        sc = artifact.get("success_criteria")
        if sc is None:
            errors.append("success_criteria: required for DELEGATE")
        elif not isinstance(sc, list) or len(sc) == 0:
            errors.append("success_criteria: must be a non-empty list")

        return errors

    def _validate_handback_fields(self, artifact: Dict) -> List[str]:
        """Validate HANDBACK-specific required fields. Returns list of errors."""
        errors: List[str] = []

        # status: required, canonical enum
        status = artifact.get("status")
        if not status:
            errors.append(
                "status: required for HANDBACK — "
                f"must be one of {sorted(VALID_STATUSES)}"
            )
        elif status not in VALID_STATUSES:
            errors.append(
                f"status: invalid value '{status}' — "
                f"must be one of {sorted(VALID_STATUSES)}"
            )

        # output: required (any value acceptable)
        if "output" not in artifact:
            errors.append("output: required for HANDBACK")

        # metrics: required object with quality, tokens, cost, duration_seconds
        metrics = artifact.get("metrics")
        if metrics is None:
            errors.append("metrics: required for HANDBACK")
        elif not isinstance(metrics, dict):
            errors.append("metrics: must be an object")
        else:
            q = metrics.get("quality")
            if q is None:
                errors.append("metrics.quality: required (float 0.0-1.0)")
            elif not isinstance(q, (int, float)) or isinstance(q, bool) or not (0.0 <= q <= 1.0):
                errors.append(
                    f"metrics.quality: must be float 0.0-1.0 (got {q!r})"
                )

            tokens = metrics.get("tokens")
            if tokens is None:
                errors.append("metrics.tokens: required (non-negative integer)")
            elif not isinstance(tokens, int) or isinstance(tokens, bool) or tokens < 0:
                errors.append(
                    f"metrics.tokens: must be non-negative integer (got {tokens!r})"
                )

            cost = metrics.get("cost")
            if cost is None:
                errors.append("metrics.cost: required (non-negative number)")
            elif not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0:
                errors.append(
                    f"metrics.cost: must be non-negative number (got {cost!r})"
                )

            dur = metrics.get("duration_seconds")
            if dur is None:
                errors.append("metrics.duration_seconds: required (non-negative number)")
            elif not isinstance(dur, (int, float)) or isinstance(dur, bool) or dur < 0:
                errors.append(
                    f"metrics.duration_seconds: must be non-negative number (got {dur!r})"
                )

        return errors

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
