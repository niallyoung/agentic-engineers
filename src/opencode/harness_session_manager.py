"""OpenCode Harness Session and Queue Path Manager.

Detects harness type and session ID from environment context, then routes work
through canonical queue paths in the agentic-engineers framework.

Canonical path format:
    ~/.agentic-engineers/{harness}/{session-id}/queue/

This enables:
- Session-scoped work isolation (concurrent sessions don't interfere)
- Harness-scoped tracking (OpenCode vs. Copilot vs. Claude Code vs. Pi.dev)
- Metrics per session per harness
- Security gates per harness

Environment Variables (in priority order):
    AGENTIC_HARNESS      - Explicit harness override (e.g., "opencode")
    AGENTIC_SESSION_ID   - Explicit session ID override
    OPENCODE_API         - Indicates OpenCode context (auto-set by harness)
    CLAUDE_SESSION_ID    - Claude.ai session ID (fallback)
    COPILOT_SESSION_ID   - GitHub Copilot session ID (fallback)

CLI Arguments (when invoked from OpenCode):
    --harness NAME       - Override harness type (e.g., "opencode")
    --session ID         - Override session ID (e.g., "uuid-string")
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class HarnessSessionManager:
    """
    Manages harness type detection and session ID resolution for OpenCode.

    This class detects the current harness (opencode, copilot, claude-code, pi-dev)
    and either retrieves or creates a session ID, then initializes the canonical
    queue structure.

    Example usage::

        mgr = HarnessSessionManager.from_env()
        mgr.initialize_queue_structure()
        
        print(f"Harness: {mgr.harness}")
        print(f"Session: {mgr.session_id}")
        print(f"Queue root: {mgr.queue_root}")
        print(f"Metadata: {mgr.metadata}")
    """

    # Supported harnesses
    SUPPORTED_HARNESSES = {"opencode", "copilot", "claude-code", "pi-dev", "local"}

    def __init__(
        self,
        harness: str,
        session_id: str,
        *,
        base_dir: Optional[Path] = None,
    ) -> None:
        """
        Initialize the session manager with explicit harness and session ID.

        Args:
            harness: One of: opencode, copilot, claude-code, pi-dev, local
            session_id: Unique session identifier (UUID or custom string)
            base_dir: Override base directory (default: ~/.agentic-engineers/)

        Raises:
            ValueError: if harness is not in SUPPORTED_HARNESSES
        """
        if harness not in self.SUPPORTED_HARNESSES:
            raise ValueError(
                f"Unsupported harness '{harness}'. "
                f"Must be one of: {', '.join(sorted(self.SUPPORTED_HARNESSES))}"
            )

        self.harness = harness
        self.session_id = session_id
        self._base_dir = Path(base_dir) if base_dir else self._default_base_dir()
        self._metadata = None

    # -----------------------------------------------------------------------
    # Factory methods (detection from environment)
    # -----------------------------------------------------------------------

    @classmethod
    def from_env(cls, *, base_dir: Optional[Path] = None) -> "HarnessSessionManager":
        """
        Create a HarnessSessionManager by detecting harness and session from env.

        Detection order for harness:
            1. AGENTIC_HARNESS env var (explicit override)
            2. OPENCODE_API env var (indicates OpenCode context)
            3. CLAUDE_SESSION_ID env var (Claude harness)
            4. COPILOT_SESSION_ID env var (Copilot harness)
            5. Default: "local"

        Detection order for session ID:
            1. AGENTIC_SESSION_ID env var
            2. OPENCODE_SESSION_ID env var
            3. CLAUDE_SESSION_ID env var
            4. COPILOT_SESSION_ID env var
            5. Generate new UUID

        Returns:
            HarnessSessionManager instance configured from environment.
        """
        harness = cls._detect_harness_from_env()
        session_id = cls._detect_session_id_from_env()
        
        logger.info(
            f"Created HarnessSessionManager from environment: "
            f"harness={harness}, session_id={session_id[:8]}..."
        )
        
        return cls(harness, session_id, base_dir=base_dir)

    @classmethod
    def from_cli_args(
        cls,
        harness: Optional[str] = None,
        session_id: Optional[str] = None,
        *,
        base_dir: Optional[Path] = None,
    ) -> "HarnessSessionManager":
        """
        Create a HarnessSessionManager from CLI arguments.

        CLI arguments override environment variables.

        Args:
            harness: CLI --harness argument (optional)
            session_id: CLI --session argument (optional)
            base_dir: Override base directory (optional)

        Returns:
            HarnessSessionManager instance configured from CLI args + env.
        """
        # CLI args override env vars
        if harness is None:
            harness = cls._detect_harness_from_env()
        if session_id is None:
            session_id = cls._detect_session_id_from_env()

        logger.info(
            f"Created HarnessSessionManager from CLI args: "
            f"harness={harness}, session_id={session_id[:8]}..."
        )

        return cls(harness, session_id, base_dir=base_dir)

    # -----------------------------------------------------------------------
    # Environment detection helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _detect_harness_from_env() -> str:
        """
        Detect harness type from environment variables.

        Priority (first match wins):
            1. AGENTIC_HARNESS
            2. OPENCODE_API
            3. CLAUDE_SESSION_ID
            4. COPILOT_SESSION_ID
            5. Default: "local"
        """
        # Explicit override
        if os.environ.get("AGENTIC_HARNESS"):
            return os.environ["AGENTIC_HARNESS"]

        # OpenCode context
        if os.environ.get("OPENCODE_API"):
            return "opencode"

        # Claude context
        if os.environ.get("CLAUDE_SESSION_ID"):
            return "claude-code"

        # Copilot context
        if os.environ.get("COPILOT_SESSION_ID"):
            return "copilot"

        # Fallback
        return "local"

    @staticmethod
    def _detect_session_id_from_env() -> str:
        """
        Detect or create session ID from environment variables.

        Priority (first non-empty value wins):
            1. AGENTIC_SESSION_ID
            2. OPENCODE_SESSION_ID
            3. CLAUDE_SESSION_ID
            4. COPILOT_SESSION_ID
            5. Generate new UUID
        """
        for env_var in (
            "AGENTIC_SESSION_ID",
            "OPENCODE_SESSION_ID",
            "CLAUDE_SESSION_ID",
            "COPILOT_SESSION_ID",
        ):
            value = os.environ.get(env_var)
            if value:
                logger.debug(f"Session ID detected from {env_var}: {value[:8]}...")
                return value

        # Generate new UUID
        session_id = str(uuid.uuid4())
        logger.debug(f"Generated new session ID: {session_id[:8]}...")
        return session_id

    @staticmethod
    def _default_base_dir() -> Path:
        """Return the default base directory (~/.agentic-engineers/)."""
        return Path.home() / ".agentic-engineers"

    # -----------------------------------------------------------------------
    # Properties
    # -----------------------------------------------------------------------

    @property
    def base_dir(self) -> Path:
        """Base directory for agentic-engineers (~/.agentic-engineers/)."""
        return self._base_dir

    @property
    def queue_root(self) -> Path:
        """
        Canonical queue root path.

        Format: ~/.agentic-engineers/{harness}/{session-id}/queue/
        """
        return self._base_dir / self.harness / self.session_id / "queue"

    @property
    def session_root(self) -> Path:
        """
        Session root directory (parent of queue/).

        Format: ~/.agentic-engineers/{harness}/{session-id}/
        """
        return self.queue_root.parent

    @property
    def metadata_path(self) -> Path:
        """Path to metadata.json for this harness/session pair."""
        return self.session_root / "metadata.json"

    @property
    def metadata(self) -> dict:
        """
        Get cached metadata dict.

        Returns empty dict if not yet initialized.
        """
        return self._metadata or {}

    # -----------------------------------------------------------------------
    # Initialization
    # -----------------------------------------------------------------------

    def initialize_queue_structure(self) -> dict:
        """
        Create canonical queue directory structure (idempotent).

        Creates:
            ~/.agentic-engineers/{harness}/{session-id}/queue/
            ├── incoming/
            ├── processing/
            ├── done/
            ├── failed/
            └── ../metadata.json

        Returns:
            dict with initialization status and paths:
            {
                "success": bool,
                "session_id": str,
                "harness": str,
                "queue_root": str,
                "metadata_path": str,
                "subdirs": {"incoming": ..., "processing": ..., ...}
            }
        """
        logger.info(
            f"Initializing queue structure: "
            f"session_id={self.session_id[:8]}..., harness={self.harness}"
        )

        try:
            # Create queue subdirectories
            subdirs = {}
            for subdir_name in ("incoming", "processing", "done", "failed"):
                subdir_path = self.queue_root / subdir_name
                subdir_path.mkdir(parents=True, exist_ok=True)
                
                # Create .keep.me stub to ensure directory is tracked
                keep_file = subdir_path / ".keep.me"
                if not keep_file.exists():
                    keep_file.touch()
                
                subdirs[subdir_name] = str(subdir_path)

            # Write/update metadata.json
            now_iso = datetime.now(tz=timezone.utc).isoformat()

            if self.metadata_path.exists():
                try:
                    with self.metadata_path.open("r", encoding="utf-8") as fh:
                        metadata = json.load(fh)
                    metadata["last_accessed_at"] = now_iso
                    logger.debug(f"Updated existing metadata: {self.metadata_path}")
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Could not read metadata, creating fresh: {e}")
                    metadata = self._create_fresh_metadata(now_iso)
            else:
                metadata = self._create_fresh_metadata(now_iso)

            # Persist metadata
            self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
            with self.metadata_path.open("w", encoding="utf-8") as fh:
                json.dump(metadata, fh, indent=2)
            
            self._metadata = metadata
            logger.info(f"Queue structure initialized: {self.queue_root}")

            return {
                "success": True,
                "session_id": self.session_id,
                "harness": self.harness,
                "queue_root": str(self.queue_root),
                "metadata_path": str(self.metadata_path),
                "subdirs": subdirs,
            }

        except Exception as e:
            logger.error(f"Failed to initialize queue structure: {e}", exc_info=True)
            return {
                "success": False,
                "session_id": self.session_id,
                "harness": self.harness,
                "error": str(e),
            }

    def _create_fresh_metadata(self, now_iso: str) -> dict:
        """Create a fresh metadata dict."""
        return {
            "session_id": self.session_id,
            "harness": self.harness,
            "created_at": now_iso,
            "last_accessed_at": now_iso,
            "spec_version": "1.0",
        }

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------

    def validate_queue_structure(self) -> tuple[bool, str]:
        """
        Validate that the queue structure exists and is canonical.

        Returns:
            (bool, str) — (is_valid, message)
        """
        # Check queue root exists
        if not self.queue_root.exists():
            return False, f"Queue root does not exist: {self.queue_root}"

        # Check subdirectories
        for subdir in ("incoming", "processing", "done", "failed"):
            subdir_path = self.queue_root / subdir
            if not subdir_path.is_dir():
                return False, f"Queue subdir missing: {subdir_path}"

        # Check metadata
        if not self.metadata_path.exists():
            return False, f"Metadata.json not found: {self.metadata_path}"

        return True, f"Queue structure is valid: {self.queue_root}"

    # -----------------------------------------------------------------------
    # Utilities
    # -----------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"HarnessSessionManager("
            f"harness={self.harness!r}, "
            f"session_id={self.session_id[:8]!r}..."
            f")"
        )

    def to_dict(self) -> dict:
        """Export manager state as dict."""
        return {
            "harness": self.harness,
            "session_id": self.session_id,
            "base_dir": str(self.base_dir),
            "queue_root": str(self.queue_root),
            "session_root": str(self.session_root),
            "metadata_path": str(self.metadata_path),
            "metadata": self.metadata,
        }
