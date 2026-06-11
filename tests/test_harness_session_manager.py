"""Tests for HarnessSessionManager.

Tests cover:
- Harness detection from environment variables
- Session ID detection and generation
- Queue structure creation (idempotent)
- Metadata persistence
- Canonical path validation
- CLI argument handling
"""

import json
import os
import tempfile
import uuid
from pathlib import Path
from unittest import mock

import pytest

from src.opencode.harness_session_manager import HarnessSessionManager


class TestHarnessDetection:
    """Test harness type detection from environment."""

    def test_detect_harness_explicit_override(self):
        """AGENTIC_HARNESS env var always wins."""
        with mock.patch.dict(
            os.environ,
            {
                "AGENTIC_HARNESS": "opencode",
                "OPENCODE_API": "1",
                "CLAUDE_SESSION_ID": "claude-123",
                "COPILOT_SESSION_ID": "copilot-456",
            },
        ):
            harness = HarnessSessionManager._detect_harness_from_env()
            assert harness == "opencode"

    def test_detect_harness_opencode_api(self):
        """OPENCODE_API env var detected as 'opencode'."""
        with mock.patch.dict(
            os.environ,
            {"OPENCODE_API": "1", "CLAUDE_SESSION_ID": "claude-123"},
            clear=True,
        ):
            harness = HarnessSessionManager._detect_harness_from_env()
            assert harness == "opencode"

    def test_detect_harness_claude_session(self):
        """CLAUDE_SESSION_ID env var detected as 'claude-code'."""
        with mock.patch.dict(
            os.environ, {"CLAUDE_SESSION_ID": "claude-123"}, clear=True
        ):
            harness = HarnessSessionManager._detect_harness_from_env()
            assert harness == "claude-code"

    def test_detect_harness_copilot_session(self):
        """COPILOT_SESSION_ID env var detected as 'copilot'."""
        with mock.patch.dict(
            os.environ, {"COPILOT_SESSION_ID": "copilot-456"}, clear=True
        ):
            harness = HarnessSessionManager._detect_harness_from_env()
            assert harness == "copilot"

    def test_detect_harness_default_local(self):
        """Default fallback is 'local'."""
        with mock.patch.dict(os.environ, {}, clear=True):
            harness = HarnessSessionManager._detect_harness_from_env()
            assert harness == "local"


class TestSessionIDDetection:
    """Test session ID detection from environment."""

    def test_detect_session_id_agentic_override(self):
        """AGENTIC_SESSION_ID env var always wins."""
        session_uuid = str(uuid.uuid4())
        with mock.patch.dict(
            os.environ,
            {
                "AGENTIC_SESSION_ID": session_uuid,
                "OPENCODE_SESSION_ID": str(uuid.uuid4()),
                "CLAUDE_SESSION_ID": "claude-123",
            },
        ):
            session_id = HarnessSessionManager._detect_session_id_from_env()
            assert session_id == session_uuid

    def test_detect_session_id_opencode_session(self):
        """OPENCODE_SESSION_ID env var is detected."""
        session_uuid = str(uuid.uuid4())
        with mock.patch.dict(
            os.environ,
            {"OPENCODE_SESSION_ID": session_uuid, "CLAUDE_SESSION_ID": "claude-123"},
            clear=True,
        ):
            session_id = HarnessSessionManager._detect_session_id_from_env()
            assert session_id == session_uuid

    def test_detect_session_id_claude_session(self):
        """CLAUDE_SESSION_ID env var is detected."""
        with mock.patch.dict(
            os.environ, {"CLAUDE_SESSION_ID": "claude-123"}, clear=True
        ):
            session_id = HarnessSessionManager._detect_session_id_from_env()
            assert session_id == "claude-123"

    def test_detect_session_id_copilot_session(self):
        """COPILOT_SESSION_ID env var is detected."""
        with mock.patch.dict(
            os.environ, {"COPILOT_SESSION_ID": "copilot-456"}, clear=True
        ):
            session_id = HarnessSessionManager._detect_session_id_from_env()
            assert session_id == "copilot-456"

    def test_detect_session_id_generates_new_uuid(self):
        """Generates new UUID if no env var set."""
        with mock.patch.dict(os.environ, {}, clear=True):
            session_id = HarnessSessionManager._detect_session_id_from_env()
            # Should be a valid UUID
            uuid.UUID(session_id)


class TestQueueInitialization:
    """Test queue structure creation."""

    def test_initialize_queue_structure_creates_directories(self):
        """Initializes all required queue subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = HarnessSessionManager("opencode", "test-session-001", base_dir=tmpdir)
            result = mgr.initialize_queue_structure()

            assert result["success"] is True
            assert result["session_id"] == "test-session-001"
            assert result["harness"] == "opencode"

            # Verify all subdirectories exist
            for subdir in ("incoming", "processing", "done", "failed"):
                subdir_path = Path(result["subdirs"][subdir])
                assert subdir_path.is_dir(), f"{subdir} directory not created"
                assert (subdir_path / ".keep.me").exists()

    def test_initialize_queue_structure_creates_metadata(self):
        """Creates metadata.json with correct structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = HarnessSessionManager("opencode", "test-session-001", base_dir=tmpdir)
            result = mgr.initialize_queue_structure()

            assert result["success"] is True
            metadata_path = Path(result["metadata_path"])
            assert metadata_path.exists()

            # Verify metadata content
            with metadata_path.open() as fh:
                metadata = json.load(fh)

            assert metadata["session_id"] == "test-session-001"
            assert metadata["harness"] == "opencode"
            assert "created_at" in metadata
            assert "last_accessed_at" in metadata
            assert metadata["spec_version"] == "1.0"

    def test_initialize_queue_structure_idempotent(self):
        """Repeated initialization preserves created_at."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = HarnessSessionManager("opencode", "test-session-001", base_dir=tmpdir)

            # First initialization
            result1 = mgr.initialize_queue_structure()
            assert result1["success"] is True

            with open(result1["metadata_path"]) as fh:
                metadata1 = json.load(fh)
            created_at_1 = metadata1["created_at"]

            # Second initialization (same session/harness)
            mgr2 = HarnessSessionManager(
                "opencode", "test-session-001", base_dir=tmpdir
            )
            result2 = mgr2.initialize_queue_structure()
            assert result2["success"] is True

            with open(result2["metadata_path"]) as fh:
                metadata2 = json.load(fh)

            # created_at should be preserved
            assert metadata2["created_at"] == created_at_1
            # last_accessed_at should be updated
            assert metadata2["last_accessed_at"] >= metadata1["last_accessed_at"]

    def test_initialize_queue_structure_handles_corrupted_metadata(self):
        """Handles corrupted metadata.json gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = HarnessSessionManager("opencode", "test-session-001", base_dir=tmpdir)
            mgr.initialize_queue_structure()

            # Corrupt metadata.json
            with open(mgr.metadata_path, "w") as fh:
                fh.write("{ invalid json")

            # Re-initialize should succeed and create fresh metadata
            mgr2 = HarnessSessionManager(
                "opencode", "test-session-001", base_dir=tmpdir
            )
            result = mgr2.initialize_queue_structure()

            assert result["success"] is True

            with open(result["metadata_path"]) as fh:
                metadata = json.load(fh)
            assert metadata["session_id"] == "test-session-001"


class TestCanonicalPaths:
    """Test canonical path generation."""

    def test_queue_root_path_format(self):
        """Queue root follows canonical format."""
        mgr = HarnessSessionManager("opencode", "test-session-001")
        expected = Path.home() / ".agentic-engineers" / "opencode" / "test-session-001" / "queue"
        assert mgr.queue_root == expected

    def test_harness_root_path(self):
        """Harness root is parent of queue/."""
        mgr = HarnessSessionManager("opencode", "test-session-001")
        expected = Path.home() / ".agentic-engineers" / "opencode" / "test-session-001"
        assert mgr.session_root == expected

    def test_metadata_path(self):
        """Metadata.json is in harness root."""
        mgr = HarnessSessionManager("opencode", "test-session-001")
        expected = mgr.session_root / "metadata.json"
        assert mgr.metadata_path == expected

    def test_canonical_path_isolation_by_session(self):
        """Different sessions have isolated queue paths."""
        mgr1 = HarnessSessionManager("opencode", "session-001")
        mgr2 = HarnessSessionManager("opencode", "session-002")

        assert mgr1.queue_root != mgr2.queue_root
        assert "session-001" in str(mgr1.queue_root)
        assert "session-002" in str(mgr2.queue_root)

    def test_canonical_path_isolation_by_harness(self):
        """Different harnesses have isolated queue paths."""
        mgr1 = HarnessSessionManager("opencode", "test-session")
        mgr2 = HarnessSessionManager("copilot", "test-session")

        assert mgr1.queue_root != mgr2.queue_root
        assert "opencode" in str(mgr1.queue_root)
        assert "copilot" in str(mgr2.queue_root)


class TestValidation:
    """Test queue structure validation."""

    def test_validate_queue_structure_success(self):
        """Validates complete queue structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = HarnessSessionManager("opencode", "test-session-001", base_dir=tmpdir)
            mgr.initialize_queue_structure()

            is_valid, msg = mgr.validate_queue_structure()
            assert is_valid is True
            assert "valid" in msg.lower()

    def test_validate_queue_structure_missing_root(self):
        """Detects missing queue root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = HarnessSessionManager("opencode", "test-session-001", base_dir=tmpdir)
            # Don't initialize

            is_valid, msg = mgr.validate_queue_structure()
            assert is_valid is False
            assert "does not exist" in msg

    def test_validate_queue_structure_missing_subdir(self):
        """Detects missing queue subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = HarnessSessionManager("opencode", "test-session-001", base_dir=tmpdir)
            mgr.initialize_queue_structure()

            # Delete one subdir (and its .keep.me file first)
            incoming = mgr.queue_root / "incoming"
            (incoming / ".keep.me").unlink()
            incoming.rmdir()

            is_valid, msg = mgr.validate_queue_structure()
            assert is_valid is False
            assert "missing" in msg.lower()

    def test_validate_queue_structure_missing_metadata(self):
        """Detects missing metadata.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = HarnessSessionManager("opencode", "test-session-001", base_dir=tmpdir)
            mgr.initialize_queue_structure()

            # Delete metadata
            mgr.metadata_path.unlink()

            is_valid, msg = mgr.validate_queue_structure()
            assert is_valid is False
            assert "metadata" in msg.lower()


class TestFactoryMethods:
    """Test factory methods for creating instances."""

    def test_from_env_with_explicit_harness(self):
        """from_env() uses AGENTIC_HARNESS."""
        with mock.patch.dict(
            os.environ,
            {
                "AGENTIC_HARNESS": "opencode",
                "AGENTIC_SESSION_ID": "test-session-001",
            },
        ):
            mgr = HarnessSessionManager.from_env()
            assert mgr.harness == "opencode"
            assert mgr.session_id == "test-session-001"

    def test_from_env_generates_session_id(self):
        """from_env() generates session ID if not provided."""
        with mock.patch.dict(os.environ, {"AGENTIC_HARNESS": "opencode"}, clear=True):
            mgr = HarnessSessionManager.from_env()
            assert mgr.harness == "opencode"
            # Should be valid UUID
            uuid.UUID(mgr.session_id)

    def test_from_cli_args_overrides_env(self):
        """from_cli_args() overrides environment variables."""
        with mock.patch.dict(
            os.environ,
            {
                "AGENTIC_HARNESS": "copilot",
                "AGENTIC_SESSION_ID": "env-session",
            },
        ):
            mgr = HarnessSessionManager.from_cli_args(
                harness="opencode", session_id="cli-session"
            )
            assert mgr.harness == "opencode"
            assert mgr.session_id == "cli-session"

    def test_from_cli_args_uses_env_fallback(self):
        """from_cli_args() falls back to environment if CLI args not provided."""
        with mock.patch.dict(
            os.environ,
            {
                "AGENTIC_HARNESS": "opencode",
                "AGENTIC_SESSION_ID": "env-session",
            },
        ):
            mgr = HarnessSessionManager.from_cli_args()
            assert mgr.harness == "opencode"
            assert mgr.session_id == "env-session"


class TestErrorHandling:
    """Test error handling."""

    def test_invalid_harness_raises_error(self):
        """Raises ValueError for unsupported harness."""
        with pytest.raises(ValueError, match="Unsupported harness"):
            HarnessSessionManager("invalid-harness", "test-session")

    def test_initialize_queue_structure_handles_permission_error(self):
        """Gracefully handles permission errors during initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = HarnessSessionManager("opencode", "test-session-001", base_dir=tmpdir)

            # Make base directory read-only
            Path(tmpdir).chmod(0o444)

            try:
                result = mgr.initialize_queue_structure()
                # Should not raise, just return error dict
                assert result["success"] is False
                assert "error" in result
            finally:
                # Restore permissions for cleanup
                Path(tmpdir).chmod(0o755)


class TestMetadata:
    """Test metadata handling."""

    def test_metadata_property_returns_cached_value(self):
        """metadata property returns cached dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = HarnessSessionManager("opencode", "test-session-001", base_dir=tmpdir)
            mgr.initialize_queue_structure()

            metadata = mgr.metadata
            assert metadata["session_id"] == "test-session-001"
            assert metadata["harness"] == "opencode"

    def test_to_dict_exports_state(self):
        """to_dict() exports manager state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = HarnessSessionManager("opencode", "test-session-001", base_dir=tmpdir)
            mgr.initialize_queue_structure()

            state = mgr.to_dict()
            assert state["harness"] == "opencode"
            assert state["session_id"] == "test-session-001"
            assert "queue_root" in state
            assert "metadata" in state


class TestIntegration:
    """Integration tests."""

    def test_end_to_end_initialization(self):
        """End-to-end: Create manager, initialize queue, validate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create from env
            with mock.patch.dict(
                os.environ,
                {
                    "AGENTIC_HARNESS": "opencode",
                    "AGENTIC_SESSION_ID": "test-session-001",
                },
            ):
                mgr = HarnessSessionManager.from_env(base_dir=tmpdir)

            # Initialize queue
            result = mgr.initialize_queue_structure()
            assert result["success"] is True

            # Validate queue
            is_valid, msg = mgr.validate_queue_structure()
            assert is_valid is True

            # Verify canonical paths
            assert "test-session-001" in str(mgr.queue_root)
            assert "opencode" in str(mgr.queue_root)
            assert "queue" in str(mgr.queue_root)

    def test_multi_session_isolation(self):
        """Multiple sessions remain isolated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr1 = HarnessSessionManager(
                "opencode", "session-001", base_dir=tmpdir
            )
            mgr2 = HarnessSessionManager(
                "opencode", "session-002", base_dir=tmpdir
            )

            # Initialize both
            result1 = mgr1.initialize_queue_structure()
            result2 = mgr2.initialize_queue_structure()

            assert result1["success"] is True
            assert result2["success"] is True

            # Verify isolation
            path1 = Path(result1["queue_root"])
            path2 = Path(result2["queue_root"])

            assert path1 != path2
            assert path1.exists()
            assert path2.exists()

            # Incoming dirs should be separate
            incoming1 = path1 / "incoming"
            incoming2 = path2 / "incoming"
            assert incoming1.exists()
            assert incoming2.exists()
            assert incoming1 != incoming2

    def test_multi_harness_isolation(self):
        """Multiple harnesses remain isolated within same session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr1 = HarnessSessionManager(
                "opencode", "test-session", base_dir=tmpdir
            )
            mgr2 = HarnessSessionManager(
                "copilot", "test-session", base_dir=tmpdir
            )

            # Initialize both
            result1 = mgr1.initialize_queue_structure()
            result2 = mgr2.initialize_queue_structure()

            assert result1["success"] is True
            assert result2["success"] is True

            # Verify isolation
            path1 = Path(result1["queue_root"])
            path2 = Path(result2["queue_root"])

            assert path1 != path2
            assert "opencode" in str(path1)
            assert "copilot" in str(path2)
            assert path1.exists()
            assert path2.exists()
