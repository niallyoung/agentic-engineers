"""
Queue Operations — atomic DELEGATE/HANDBACK enqueue with audit trail,
ancestry-based cycle detection, and per-session/per-harness path isolation.

MANDATORY ENQUEUE CONTRACT: ``QueueOperations.enqueue()`` is the ONLY
sanctioned way to write a DELEGATE/HANDBACK into the queue directory. Direct
writes to incoming/processing/done/failed/ bypass schema validation and are
forbidden — see src/AGENTS.md > Audit-Trail Strategy.

In the direct sub-agent spawn execution model the queue is a durable AUDIT
TRAIL, not a dispatch mechanism: dispatch already happened via a direct
Agent/Task-tool spawn before enqueue() is called. enqueue() writes the
DELEGATE to incoming/{task_id}.yaml at spawn time and the HANDBACK to
processing/{task_id}.yaml when the spawn call returns, enforcing canonical
schema (handoff_type, agent, task_id, metrics, status), rejecting legacy
fields (type/role/quality_score), writing atomically (temp-file + rename),
and checking ancestry-based cycles/depth for DELEGATEs. See
docs/specs/protocol-core-v1.0.yaml for the schema and src/AGENTS.md for the
full protocol.
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional

import yaml  # DELEGATE/HANDBACK queue files are SPEC-compliant YAML

# ---------------------------------------------------------------------------
# Canonical schema constants (single source of truth for enqueue validation —
# must stay in sync with src/skills/protocol-validator/scripts/protocol_validator.py)
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

_TASK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$")

# Legacy field names that are no longer accepted in canonical schema.
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

_DEFAULT_QUEUE_PATH = "~/.agentic-engineers"
_QUEUE_SUBDIRS = ("incoming", "processing", "done", "failed")

# Recursion limits (see src/AGENTS.md > Recursion Limits). Ancestry length is
# hops from the root DELEGATE; a depth-3 agent must not itself spawn.
MAX_DELEGATION_DEPTH = 3


# ---------------------------------------------------------------------------
# Path isolation (inlined from the now-deleted src/skills/_meta/queue-isolation
# skill — session/harness-scoped queue paths with traversal-safe validation)
# ---------------------------------------------------------------------------

# session_id / harness are interpolated directly into the queue path. Restrict
# to a filename-safe character set so neither can escape the canonical
# ~/.agentic-engineers/ root via path separators, ".." references, or
# absolute paths.
_SAFE_PATH_COMPONENT_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def _validate_path_component(value: str, *, field: str) -> str:
    """Validate a session_id/harness value before using it in a queue path."""
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string, got {type(value).__name__}")
    if value in ("", ".", ".."):
        raise ValueError(f"{field} is empty or a path reference: {value!r}")
    if "/" in value or "\\" in value or "\x00" in value:
        raise ValueError(f"{field} contains illegal path separators: {value!r}")
    if not _SAFE_PATH_COMPONENT_RE.match(value):
        raise ValueError(
            f"{field} contains illegal characters "
            f"(allowed: letters, digits, '.', '_', '-'): {value!r}"
        )
    return value


def detect_harness() -> str:
    """Detect the current AI harness from environment variables.

    Priority: AGENTIC_HARNESS (explicit) > CLAUDE_SESSION_ID > COPILOT_SESSION_ID
    > OPENAI_API_KEY > 'local' (fallback).
    """
    explicit = os.environ.get("AGENTIC_HARNESS")
    if explicit:
        return explicit
    if os.environ.get("CLAUDE_SESSION_ID"):
        return "claude"
    if os.environ.get("COPILOT_SESSION_ID"):
        return "copilot"
    if os.environ.get("OPENAI_API_KEY"):
        return "gpt"
    return "local"


def get_session_id() -> str:
    """Retrieve the current session ID from environment, or generate a UUID4."""
    for var in ("AGENTIC_SESSION_ID", "CLAUDE_SESSION_ID", "COPILOT_SESSION_ID"):
        value = os.environ.get(var)
        if value:
            return value
    return str(uuid.uuid4())


def get_queue_path(session_id: str, harness: str, *, base_dir: Optional[Path] = None) -> Path:
    """Canonical queue path: <base_dir>/<harness>/<session_id>/queue/."""
    base = Path(base_dir) if base_dir is not None else Path.home() / ".agentic-engineers"
    safe_session = _validate_path_component(session_id, field="session_id")
    safe_harness = _validate_path_component(harness, field="harness")
    return base / safe_harness / safe_session / "queue"


# ---------------------------------------------------------------------------
# Atomic write (inlined — was src/skills/queue-management/scripts/consistency.py)
# ---------------------------------------------------------------------------

def _write_atomic(target_path: Path, content: str) -> None:
    """Write a file atomically via temp-file-then-rename (POSIX semantics)."""
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Optional[str] = None
    try:
        with NamedTemporaryFile(
            mode="w", dir=target_path.parent, delete=False, prefix=".tmp-", suffix=".yaml"
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        os.replace(tmp_path, target_path)
    except Exception as exc:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise IOError(f"Atomic write failed for {target_path}: {exc}") from exc


# ---------------------------------------------------------------------------
# Cycle detection over ancestry (replaces the old @parent-chain file-tree walk
# now that DELEGATEs carry their own ancestry list instead of relying on the
# queue to reconstruct it — see src/AGENTS.md > Recursion Limits)
# ---------------------------------------------------------------------------

def has_cycle(target_role: str, ancestry: Optional[List[str]]) -> bool:
    """True if ``target_role`` already appears in ``ancestry`` (root..parent,
    inclusive) — e.g. Lead Engineer's follow-on DELEGATE re-targeting the
    senior-engineer that escalated to it for the same task."""
    return bool(ancestry) and target_role in ancestry


def exceeds_max_depth(ancestry: Optional[List[str]], max_depth: int = MAX_DELEGATION_DEPTH) -> bool:
    """True if issuing a DELEGATE from this ancestry chain would exceed
    MAX_DELEGATION_DEPTH spawn hops from the root DELEGATE."""
    return bool(ancestry) and len(ancestry) >= max_depth


class QueueOperations:
    """Atomic queue operations for the DELEGATE/HANDBACK audit trail."""

    def __init__(
        self,
        session_id: str,
        queue_path: str = _DEFAULT_QUEUE_PATH,
        harness: Optional[str] = None,
    ):
        """Initialize with session/harness isolation.

        An explicit ``queue_path`` (e.g. a tempdir in tests) bypasses the
        canonical ``~/.agentic-engineers/{harness}/{session_id}/queue/``
        layout in favor of a flat ``<queue_path>/<session_id>/`` layout, so
        tests can fully control where files land.
        """
        if not session_id or not isinstance(session_id, str):
            raise ValueError("session_id must be a non-empty string")

        self.session_id = session_id
        using_default_path = queue_path == _DEFAULT_QUEUE_PATH

        if using_default_path:
            self.harness = harness or detect_harness()
            self.session_queue_path = get_queue_path(session_id, self.harness)
            self.queue_path = self.session_queue_path.parent.parent  # <base>/
        else:
            self.harness = harness or "local"
            self.queue_path = Path(queue_path).expanduser()
            self.session_queue_path = self.queue_path / session_id

        for subdir in _QUEUE_SUBDIRS:
            (self.session_queue_path / subdir).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # enqueue() — the one sanctioned write path
    # ------------------------------------------------------------------

    def enqueue(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        """
        MANDATORY entry point for recording a DELEGATE or HANDBACK.

        Validates canonical schema, writes atomically, and appends an
        append-only audit-trail line. See module docstring for full contract.

        Args:
            artifact: Dict representing the DELEGATE or HANDBACK to record.

        Returns:
            {"status": "enqueued", "handoff_type": str, "task_id": str,
             "timestamp": str, "queue_path": str}

        Raises:
            ValueError: Schema validation failed (message lists all errors).
            RuntimeError: Ancestry-based cycle or depth limit violated.
        """
        errors: List[str] = []

        for legacy_field, guidance in _REJECTED_LEGACY_FIELDS.items():
            if legacy_field in artifact:
                errors.append(f"Rejected legacy field '{legacy_field}': {guidance}")
        if errors:
            raise ValueError(
                "enqueue() rejected artifact with legacy schema fields. "
                "All agents must use canonical schema.\n" + "\n".join(f"  - {e}" for e in errors)
            )

        handoff_type = artifact.get("handoff_type")
        if not handoff_type:
            errors.append("handoff_type: required — must be 'DELEGATE' or 'HANDBACK'")
        elif handoff_type not in VALID_HANDOFF_TYPES:
            errors.append(
                f"handoff_type: invalid value '{handoff_type}' — must be one of {sorted(VALID_HANDOFF_TYPES)}"
            )

        task_id = artifact.get("task_id")
        if not task_id or not isinstance(task_id, str):
            errors.append("task_id: required, must be a non-empty string")
        elif not _TASK_ID_PATTERN.match(task_id):
            errors.append("task_id: must be kebab-case, 3-50 chars ([a-z0-9][a-z0-9-]{1,48}[a-z0-9])")

        agent = artifact.get("agent")
        if not agent or not isinstance(agent, str):
            errors.append("agent: required — use hyphenated name e.g. 'senior-engineer'")
        elif agent not in VALID_AGENTS:
            errors.append(f"agent: invalid value '{agent}' — must be one of {sorted(VALID_AGENTS)}")

        if handoff_type == "DELEGATE":
            errors.extend(self._validate_delegate_fields(artifact))
        elif handoff_type == "HANDBACK":
            errors.extend(self._validate_handback_fields(artifact))

        if errors:
            raise ValueError(
                "enqueue() schema validation failed — artifact rejected:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

        # Ancestry-based cycle / depth check (DELEGATE only)
        if handoff_type == "DELEGATE":
            ancestry = artifact.get("ancestry")
            if ancestry:
                if has_cycle(agent, ancestry):
                    raise RuntimeError(
                        f"Cycle detected: target agent '{agent}' already appears in ancestry {ancestry}"
                    )
                if exceeds_max_depth(ancestry):
                    raise RuntimeError(
                        f"Max delegation depth ({MAX_DELEGATION_DEPTH}) exceeded: ancestry {ancestry}"
                    )

        target_state = "incoming" if handoff_type == "DELEGATE" else "processing"
        now_iso = datetime.now(tz=timezone.utc).isoformat()
        artifact_with_meta = {**artifact, "enqueued_at": now_iso, "queue_state": target_state}

        file_path = self.session_queue_path / target_state / f"{task_id}.yaml"
        _write_atomic(
            file_path,
            yaml.safe_dump(artifact_with_meta, sort_keys=False, default_flow_style=False),
        )

        self._append_audit(handoff_type, task_id, agent, now_iso)

        return {
            "status": "enqueued",
            "handoff_type": handoff_type,
            "task_id": task_id,
            "timestamp": now_iso,
            "queue_path": str(file_path),
        }

    def _validate_delegate_fields(self, artifact: Dict[str, Any]) -> List[str]:
        errors: List[str] = []

        scope = artifact.get("scope", "")
        if not scope or not isinstance(scope, str):
            errors.append("scope: required for DELEGATE, must be a string")
        elif len(scope.split()) < 15:
            errors.append(f"scope: must be >=15 words (got {len(scope.split())})")

        plan = artifact.get("plan")
        if plan is None:
            errors.append("plan: required for DELEGATE")
        elif not isinstance(plan, list):
            errors.append("plan: must be a list of strings")
        elif len(plan) < 2:
            errors.append(f"plan: must have >=2 steps (got {len(plan)})")
        else:
            for i, step in enumerate(plan):
                if not isinstance(step, str):
                    errors.append(f"plan[{i}]: each step must be a string")
                elif len(step.split()) < 3:
                    errors.append(f"plan[{i}]: each step must be >=3 words (got '{step}')")

        context = artifact.get("context")
        if context is None:
            errors.append("context: required for DELEGATE")
        elif isinstance(context, str):
            if len(context.split()) < 20:
                errors.append(f"context: must be >=20 words when string (got {len(context.split())})")
        elif isinstance(context, list):
            if len(context) == 0:
                errors.append("context: must be non-empty when provided as list")
        else:
            errors.append("context: must be a string or list of strings")

        sc = artifact.get("success_criteria")
        if sc is None:
            errors.append("success_criteria: required for DELEGATE")
        elif not isinstance(sc, list) or len(sc) == 0:
            errors.append("success_criteria: must be a non-empty list")

        return errors

    def _validate_handback_fields(self, artifact: Dict[str, Any]) -> List[str]:
        errors: List[str] = []

        status = artifact.get("status")
        if not status:
            errors.append(f"status: required for HANDBACK — must be one of {sorted(VALID_STATUSES)}")
        elif status not in VALID_STATUSES:
            errors.append(f"status: invalid value '{status}' — must be one of {sorted(VALID_STATUSES)}")

        if "output" not in artifact:
            errors.append("output: required for HANDBACK")

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
                errors.append(f"metrics.quality: must be float 0.0-1.0 (got {q!r})")

            tokens = metrics.get("tokens")
            if tokens is None:
                errors.append("metrics.tokens: required (non-negative integer)")
            elif not isinstance(tokens, int) or isinstance(tokens, bool) or tokens < 0:
                errors.append(f"metrics.tokens: must be non-negative integer (got {tokens!r})")

            cost = metrics.get("cost")
            if cost is None:
                errors.append("metrics.cost: required (non-negative number)")
            elif not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0:
                errors.append(f"metrics.cost: must be non-negative number (got {cost!r})")

            dur = metrics.get("duration_seconds")
            if dur is None:
                errors.append("metrics.duration_seconds: required (non-negative number)")
            elif not isinstance(dur, (int, float)) or isinstance(dur, bool) or dur < 0:
                errors.append(f"metrics.duration_seconds: must be non-negative number (got {dur!r})")

        return errors

    # ------------------------------------------------------------------
    # Audit trail (append-only)
    # ------------------------------------------------------------------

    def _append_audit(self, handoff_type: str, task_id: str, agent: str, timestamp: str) -> None:
        """Append one line to the session's append-only audit log — a durable
        record distinct from the per-task queue-state YAML files, so history
        survives a later move_task() or cleanup of the per-task file."""
        audit_path = self.session_queue_path.parent / "audit.log"
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        with open(audit_path, "a", encoding="utf-8") as fh:
            fh.write(f"{timestamp}\t{handoff_type}\t{task_id}\t{agent}\n")

    def move_task(self, task_id: str, from_state: str, to_state: str) -> Dict[str, Any]:
        """Atomically move a task's queue file between states (e.g.
        processing/ -> done/ once a spawned agent's HANDBACK is resolved)."""
        valid_states = set(_QUEUE_SUBDIRS)
        if from_state not in valid_states or to_state not in valid_states:
            raise ValueError(f"Invalid state: must be one of {valid_states}")

        from_path = self.session_queue_path / from_state / f"{task_id}.yaml"
        if not from_path.exists():
            raise FileNotFoundError(f"Task {task_id} not found in {from_state}")

        to_path = self.session_queue_path / to_state / f"{task_id}.yaml"
        to_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(from_path, to_path)

        return {
            "status": "moved",
            "task_id": task_id,
            "from_state": from_state,
            "to_state": to_state,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }
