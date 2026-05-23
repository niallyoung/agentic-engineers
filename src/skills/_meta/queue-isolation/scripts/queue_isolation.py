"""
Queue Isolation Module

Provides session-scoped, harness-scoped queue path isolation for the
agentic-engineers multi-harness workflow.

Queue structure:
    ~/.agentic-engineers/artifacts/{session_id}/{harness}/queue/
        incoming/   – new DELEGATEs waiting for pickup
        processing/ – tasks currently being executed
        done/       – completed tasks (HANDBACKs)
        failed/     – tasks that errored out
    ~/.agentic-engineers/artifacts/{session_id}/{harness}/metadata.json

Design decisions:
    - Base directory is ~/.agentic-engineers/ (never ~/.copilot/).
    - AGENTIC_HARNESS env var always wins for harness detection.
    - AGENTIC_SESSION_ID > CLAUDE_SESSION_ID > COPILOT_SESSION_ID > generated UUID.
    - All functions accept an optional ``base_dir`` kwarg for testing isolation.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Subdirectories created under <queue_root>/
_QUEUE_SUBDIRS = ("incoming", "processing", "done", "failed")


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

    Path: <base_dir>/artifacts/<session_id>/<harness>/queue/

    Args:
        session_id: Unique session identifier.
        harness: AI harness name ('claude', 'gpt', 'copilot', 'local', …).
        base_dir: Override base directory (default: ~/.agentic-engineers/).

    Returns:
        pathlib.Path pointing to the queue root (not yet guaranteed to exist).
    """
    base = Path(base_dir) if base_dir is not None else _default_base_dir()
    return base / "artifacts" / session_id / harness / "queue"


def init_queue_structure(
    session_id: str,
    harness: str,
    *,
    base_dir: Optional[Path] = None,
) -> Path:
    """
    Create the full queue directory structure for a session/harness pair.

    Creates:
        <base_dir>/artifacts/<session_id>/<harness>/queue/incoming/.keep.me
        <base_dir>/artifacts/<session_id>/<harness>/queue/processing/.keep.me
        <base_dir>/artifacts/<session_id>/<harness>/queue/done/.keep.me
        <base_dir>/artifacts/<session_id>/<harness>/queue/failed/.keep.me
        <base_dir>/artifacts/<session_id>/<harness>/metadata.json

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
    harness_root = queue_root.parent  # <base>/artifacts/<session>/<harness>/

    # Create queue subdirectories and .keep.me stubs
    for subdir in _QUEUE_SUBDIRS:
        subdir_path = queue_root / subdir
        subdir_path.mkdir(parents=True, exist_ok=True)
        keep_me = subdir_path / ".keep.me"
        if not keep_me.exists():
            keep_me.touch()

    # Write / update metadata.json
    meta_path = harness_root / "metadata.json"
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

    return queue_root


# ---------------------------------------------------------------------------
# QueueIsolation class — high-level interface
# ---------------------------------------------------------------------------

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

    def __repr__(self) -> str:
        return (
            f"QueueIsolation(session_id={self.session_id!r}, "
            f"harness={self.harness!r})"
        )
