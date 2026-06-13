"""
Queue Isolation Module

Provides session-scoped, harness-scoped queue path isolation for the
agentic-engineers multi-harness workflow.

Queue structure:
    ~/.agentic-engineers/{harness}/{session_id}/queue/
        incoming/   – new DELEGATEs waiting for pickup
        processing/ – tasks currently being executed
        done/       – completed tasks (HANDBACKs)
        failed/     – tasks that errored out
    ~/.agentic-engineers/{harness}/{session_id}/metadata.json

Design decisions:
    - Base directory is ~/.agentic-engineers/ (never ~/.copilot/).
    - AGENTIC_HARNESS env var always wins for harness detection.
    - AGENTIC_SESSION_ID > CLAUDE_SESSION_ID > COPILOT_SESSION_ID > generated UUID.
    - All functions accept an optional ``base_dir`` kwarg for testing isolation.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Subdirectories created under <queue_root>/
_QUEUE_SUBDIRS = ("incoming", "processing", "done", "failed")

# session_id / harness are interpolated directly into the queue path. They must
# be restricted to a filename-safe character set so they cannot escape the
# canonical ~/.agentic-engineers/artifacts/ root via path separators, parent
# references ("..") or absolute paths.
_SAFE_PATH_COMPONENT_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def _validate_path_component(value: str, *, field: str) -> str:
    """Validate a session_id/harness value before using it in a queue path.

    Raises:
        ValueError: if the value is empty, a path reference, or contains any
            character that could enable path traversal.
    """
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


def _default_base_dir() -> Path:
    """Return the default base directory, resolving HOME lazily.

    Using a function (rather than a module-level constant) ensures the correct
    HOME is picked up even if tests monkeypatch the HOME environment variable
    after module import.
    """
    return Path.home() / ".agentic-engineers"


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def detect_harness() -> str:
    """
    Detect the current AI harness from environment variables.

    Detection priority (first match wins):
        1. AGENTIC_HARNESS   – explicit override, always wins
        2. CLAUDE_SESSION_ID – Claude / Anthropic harness
        3. COPILOT_SESSION_ID – GitHub Copilot harness
        4. OPENAI_API_KEY    – GPT / OpenAI harness
        5. 'local'           – fallback default

    Returns:
        str: one of 'claude', 'copilot', 'gpt', 'local', or whatever
             AGENTIC_HARNESS is set to.
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
    """
    Retrieve the current session ID from environment or generate a UUID.

    Detection priority (first non-empty value wins):
        1. AGENTIC_SESSION_ID
        2. CLAUDE_SESSION_ID
        3. COPILOT_SESSION_ID
        4. Generate a new UUID4

    Returns:
        str: A non-empty session identifier.
    """
    for var in ("AGENTIC_SESSION_ID", "CLAUDE_SESSION_ID", "COPILOT_SESSION_ID"):
        value = os.environ.get(var)
        if value:
            return value

    return str(uuid.uuid4())


def get_queue_path(
    session_id: str,
    harness: str,
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    """
    Construct the queue directory path for a given session and harness.

    Path: <base_dir>/<harness>/<session_id>/queue/

    Args:
        session_id: Unique session identifier.
        harness: AI harness name ('claude', 'gpt', 'copilot', 'local', …).
        base_dir: Override base directory (default: ~/.agentic-engineers/).

    Returns:
        pathlib.Path pointing to the queue root (not yet guaranteed to exist).
    """
    base = Path(base_dir) if base_dir is not None else _default_base_dir()
    # Reject traversal / separator injection in session_id and harness so the
    # resulting path cannot escape the canonical queue root.
    safe_session = _validate_path_component(session_id, field="session_id")
    safe_harness = _validate_path_component(harness, field="harness")
    return base / safe_harness / safe_session / "queue"


def init_queue_structure(
    session_id: str,
    harness: str,
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    """
    Create the full queue directory structure for a session/harness pair.

    Creates:
        <base_dir>/<harness>/<session_id>/queue/incoming/.keep.me
        <base_dir>/<harness>/<session_id>/queue/processing/.keep.me
        <base_dir>/<harness>/<session_id>/queue/done/.keep.me
        <base_dir>/<harness>/<session_id>/queue/failed/.keep.me
        <base_dir>/<harness>/<session_id>/metadata.json

    The metadata.json is created on first call; subsequent calls only update
    ``last_accessed_at`` (preserving ``created_at``).

    Args:
        session_id: Unique session identifier.
        harness: AI harness name.
        base_dir: Override base directory (default: ~/.agentic-engineers/).

    Returns:
        pathlib.Path – the queue root directory.
    """
    queue_root = get_queue_path(session_id, harness, base_dir=base_dir)
    session_root = queue_root.parent  # <base>/<harness>/<session>/

    # Create queue subdirectories and .keep.me stubs
    for subdir in _QUEUE_SUBDIRS:
        subdir_path = queue_root / subdir
        subdir_path.mkdir(parents=True, exist_ok=True)
        keep_me = subdir_path / ".keep.me"
        if not keep_me.exists():
            keep_me.touch()

    # Write / update metadata.json
    meta_path = session_root / "metadata.json"
    now_iso = datetime.now(tz=timezone.utc).isoformat()

    if meta_path.exists():
        with meta_path.open("r", encoding="utf-8") as fh:
            try:
                meta = json.load(fh)
            except json.JSONDecodeError:
                meta = {}
        meta["last_accessed_at"] = now_iso
    else:
        meta = {
            "session_id": session_id,
            "harness": harness,
            "created_at": now_iso,
            "last_accessed_at": now_iso,
        }

    with meta_path.open("w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)

    # Create staleness tracking metadata
    staleness_path = session_root / "staleness.json"
    if not staleness_path.exists():
        staleness_meta = {
            "session_id": session_id,
            "harness": harness,
            "queue_created_at": now_iso,
            "alert_threshold_sec": 300,  # 5 minutes
            "escalation_threshold_sec": 600,  # 10 minutes
            "last_staleness_check": now_iso,
        }
        with staleness_path.open("w", encoding="utf-8") as fh:
            json.dump(staleness_meta, fh, indent=2)

    return queue_root


# ---------------------------------------------------------------------------
# QueueIsolation class — high-level interface
# ---------------------------------------------------------------------------

def record_task_timestamp(
    task_id: str,
    queue_root: Path,
    state: str = "incoming",
    action: str = "created",
) -> None:
    """
    Record a task timestamp event in a task metadata sidecar file.

    Creates/updates <queue_root>/<state>/<task_id>.timestamps.json with:
    - 'created_at': When the task was first created (immutable)
    - 'last_updated': When the task was last modified
    - 'state_changes': Array of {timestamp, action, state} transitions

    Args:
        task_id: Task identifier
        queue_root: Path to the queue root directory
        state: Queue state (incoming, processing, done, failed)
        action: Action description (created, claimed, completed, failed)
    """
    state_dir = queue_root / state
    state_dir.mkdir(parents=True, exist_ok=True)

    timestamps_path = state_dir / f"{task_id}.timestamps.json"
    now_iso = datetime.now(tz=timezone.utc).isoformat()

    if timestamps_path.exists():
        try:
            with timestamps_path.open("r", encoding="utf-8") as fh:
                ts_data = json.load(fh)
        except json.JSONDecodeError:
            ts_data = {"created_at": now_iso}
    else:
        ts_data = {"created_at": now_iso}

    ts_data["last_updated"] = now_iso

    if "state_changes" not in ts_data:
        ts_data["state_changes"] = []

    ts_data["state_changes"].append({
        "timestamp": now_iso,
        "action": action,
        "state": state,
    })

    with timestamps_path.open("w", encoding="utf-8") as fh:
        json.dump(ts_data, fh, indent=2)


def get_task_age_seconds(
    task_id: str,
    queue_root: Path,
    state: str = "incoming",
) -> Optional[float]:
    """
    Get the age (in seconds) of a task since creation.

    Args:
        task_id: Task identifier
        queue_root: Path to the queue root directory
        state: Queue state where task currently resides

    Returns:
        Age in seconds (as float), or None if timestamps file not found
    """
    timestamps_path = queue_root / state / f"{task_id}.timestamps.json"

    if not timestamps_path.exists():
        return None

    try:
        with timestamps_path.open("r", encoding="utf-8") as fh:
            ts_data = json.load(fh)
    except (json.JSONDecodeError, IOError):
        return None

    created_at_str = ts_data.get("created_at")
    if not created_at_str:
        return None

    try:
        created_at = datetime.fromisoformat(created_at_str)
        now = datetime.now(tz=timezone.utc)
        return (now - created_at).total_seconds()
    except (ValueError, TypeError):
        return None


def check_task_staleness(
    task_id: str,
    queue_root: Path,
    state: str = "processing",
    stale_threshold_sec: float = 300.0,
    escalation_threshold_sec: float = 600.0,
) -> dict:
    """
    Check if a task is stale or requires escalation based on age thresholds.

    Staleness is ADVISORY — it never changes task state, only generates alerts.
    Returns a dict with status, age, and recommended action.

    Args:
        task_id: Task identifier
        queue_root: Path to the queue root directory
        state: Queue state (typically 'processing')
        stale_threshold_sec: Warn threshold in seconds (default 300s = 5 min)
        escalation_threshold_sec: Escalation threshold in seconds (default 600s = 10 min)

    Returns:
        dict with keys:
        - 'task_id': The task ID
        - 'age_seconds': Age in seconds (float), or None if not found
        - 'is_stale': bool (True if age > stale_threshold)
        - 'is_crashed': bool (True if age > escalation_threshold)
        - 'status': 'ok' | 'stale' | 'crashed'
        - 'action': Recommended action ('none', 'warn', 'escalate')
    """
    age = get_task_age_seconds(task_id, queue_root, state)

    result = {
        "task_id": task_id,
        "age_seconds": age,
        "is_stale": False,
        "is_crashed": False,
        "status": "ok",
        "action": "none",
    }

    if age is None:
        result["status"] = "unknown"
        result["action"] = "none"
        return result

    # Check escalation threshold first (crash)
    if age > escalation_threshold_sec:
        result["is_crashed"] = True
        result["status"] = "crashed"
        result["action"] = "escalate"
        return result

    # Check stale threshold (warn)
    if age > stale_threshold_sec:
        result["is_stale"] = True
        result["status"] = "stale"
        result["action"] = "warn"
        return result

    return result


def scan_queue_for_staleness(
    queue_root: Path,
    state: str = "processing",
    stale_threshold_sec: float = 300.0,
    escalation_threshold_sec: float = 600.0,
) -> dict:
    """
    Scan a queue state directory for stale and crashed tasks.

    Returns a summary with lists of stale and crashed tasks.

    Args:
        queue_root: Path to the queue root directory
        state: Queue state to scan (default 'processing')
        stale_threshold_sec: Warn threshold in seconds
        escalation_threshold_sec: Escalation threshold in seconds

    Returns:
        dict with keys:
        - 'scanned_at': ISO8601 timestamp of when scan occurred
        - 'state': The state directory scanned
        - 'tasks_checked': Total tasks found
        - 'stale_tasks': List of stale tasks (age > stale_threshold)
        - 'crashed_tasks': List of crashed tasks (age > escalation_threshold)
        - 'ok_tasks': List of healthy tasks
    """
    state_dir = queue_root / state
    scanned_at = datetime.now(tz=timezone.utc).isoformat()

    stale_list = []
    crashed_list = []
    ok_list = []

    if not state_dir.exists():
        return {
            "scanned_at": scanned_at,
            "state": state,
            "tasks_checked": 0,
            "stale_tasks": [],
            "crashed_tasks": [],
            "ok_tasks": [],
        }

    # Find all task timestamps files
    for ts_file in state_dir.glob("*.timestamps.json"):
        # Extract task_id from filename
        task_id = ts_file.stem.replace(".timestamps", "")

        # Check staleness
        result = check_task_staleness(
            task_id,
            queue_root,
            state,
            stale_threshold_sec,
            escalation_threshold_sec,
        )

        if result["status"] == "crashed":
            crashed_list.append(result)
        elif result["status"] == "stale":
            stale_list.append(result)
        elif result["status"] == "ok":
            ok_list.append(result)

    return {
        "scanned_at": scanned_at,
        "state": state,
        "tasks_checked": len(stale_list) + len(crashed_list) + len(ok_list),
        "stale_tasks": stale_list,
        "crashed_tasks": crashed_list,
        "ok_tasks": ok_list,
    }


class QueueIsolation:
    """
    High-level interface for per-session, per-harness queue isolation.

    Encapsulates session_id and harness, providing convenience methods for
    obtaining paths and initialising the directory structure.

    Example usage::

        qi = QueueIsolation.from_env()
        qi.initialise()
        incoming = qi.queue_path / "incoming"

    """

    def __init__(
        self,
        session_id: str,
        harness: str,
        *,
        base_dir: Optional[Path] = None,
    ) -> None:
        """
        Args:
            session_id: Unique session identifier.
            harness: AI harness name.
            base_dir: Override base directory (default: ~/.agentic-engineers/).
        """
        self.session_id = session_id
        self.harness = harness
        self._base_dir = base_dir

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls, *, base_dir: Optional[Path] = None) -> "QueueIsolation":
        """
        Create a QueueIsolation instance from environment variables.

        Detects session_id and harness automatically.
        """
        return cls(
            session_id=get_session_id(),
            harness=detect_harness(),
            base_dir=base_dir,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def queue_path(self) -> Path:
        """Root queue directory (incoming/processing/done/failed live here)."""
        return get_queue_path(
            self.session_id, self.harness, base_dir=self._base_dir
        )

    @property
    def metadata_path(self) -> Path:
        """Path to metadata.json for this session/harness pair."""
        return self.queue_path.parent / "metadata.json"

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    def initialise(self) -> Path:
        """
        Initialise the queue directory structure (idempotent).

        Returns:
            Path to the queue root directory.
        """
        return init_queue_structure(
            self.session_id, self.harness, base_dir=self._base_dir
        )

    def get_metadata(self) -> dict:
        """
        Read and return metadata.json content.

        Returns:
            dict with session_id, harness, created_at, last_accessed_at.

        Raises:
            FileNotFoundError: if metadata.json has not been created yet.
        """
        if not self.metadata_path.exists():
            raise FileNotFoundError(
                f"metadata.json not found; call initialise() first. "
                f"Expected at: {self.metadata_path}"
            )
        with self.metadata_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def check_staleness(
        self,
        task_id: str,
        state: str = "processing",
        stale_threshold_sec: float = 300.0,
        escalation_threshold_sec: float = 600.0,
    ) -> dict:
        """
        Check if a task in this session is stale or crashed.

        Wrapper around check_task_staleness() using this instance's queue_path.

        Args:
            task_id: Task identifier
            state: Queue state (default 'processing')
            stale_threshold_sec: Warn threshold in seconds (default 300s)
            escalation_threshold_sec: Escalation threshold in seconds (default 600s)

        Returns:
            dict with staleness status, age, and recommended action
        """
        return check_task_staleness(
            task_id,
            self.queue_path,
            state,
            stale_threshold_sec,
            escalation_threshold_sec,
        )

    def scan_staleness(
        self,
        state: str = "processing",
        stale_threshold_sec: float = 300.0,
        escalation_threshold_sec: float = 600.0,
    ) -> dict:
        """
        Scan this session's queue state for stale and crashed tasks.

        Wrapper around scan_queue_for_staleness() using this instance's queue_path.

        Args:
            state: Queue state to scan (default 'processing')
            stale_threshold_sec: Warn threshold in seconds
            escalation_threshold_sec: Escalation threshold in seconds

        Returns:
            dict with scan results, lists of stale/crashed/ok tasks
        """
        return scan_queue_for_staleness(
            self.queue_path,
            state,
            stale_threshold_sec,
            escalation_threshold_sec,
        )

    def __repr__(self) -> str:
        return (
            f"QueueIsolation(session_id={self.session_id!r}, "
            f"harness={self.harness!r})"
        )
