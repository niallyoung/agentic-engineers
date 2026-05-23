"""
TDD test suite for queue-isolation skill.

Tests cover:
- Harness detection from environment variables
- Session ID generation/retrieval
- Queue path construction
- Directory structure initialisation
- Metadata file creation and tracking
- Multi-harness isolation (different harnesses → different paths)
- Session isolation (different sessions → different paths)
- Idempotent initialisation
"""

import json
import os
import tempfile
import uuid
from pathlib import Path
from unittest import mock

import pytest

# Import under test – will fail (RED phase) until module is created.
# conftest.py adds <skill>/scripts/ to sys.path, so we import directly.
from queue_isolation import (
    QueueIsolation,
    detect_harness,
    get_session_id,
    get_queue_path,
    init_queue_structure,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh_base(tmp_path: Path) -> Path:
    """Return a fresh base directory inside tmp_path (does not yet exist)."""
    return tmp_path / ".agentic-engineers"


# ===========================================================================
# 1. detect_harness()
# ===========================================================================

class TestDetectHarness:
    """Tests for harness detection logic."""

    def test_detect_harness_returns_claude_from_env(self, monkeypatch):
        """CLAUDE_SESSION_ID set → harness is 'claude'."""
        monkeypatch.setenv("CLAUDE_SESSION_ID", "abc-123")
        monkeypatch.delenv("COPILOT_SESSION_ID", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("AGENTIC_HARNESS", raising=False)
        assert detect_harness() == "claude"

    def test_detect_harness_returns_copilot_from_env(self, monkeypatch):
        """COPILOT_SESSION_ID set → harness is 'copilot'."""
        monkeypatch.setenv("COPILOT_SESSION_ID", "session-999")
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("AGENTIC_HARNESS", raising=False)
        assert detect_harness() == "copilot"

    def test_detect_harness_returns_gpt_from_openai_key(self, monkeypatch):
        """OPENAI_API_KEY set (no other harness vars) → harness is 'gpt'."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
        monkeypatch.delenv("COPILOT_SESSION_ID", raising=False)
        monkeypatch.delenv("AGENTIC_HARNESS", raising=False)
        assert detect_harness() == "gpt"

    def test_detect_harness_explicit_override(self, monkeypatch):
        """AGENTIC_HARNESS env var always wins."""
        monkeypatch.setenv("AGENTIC_HARNESS", "local")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "abc")
        assert detect_harness() == "local"

    def test_detect_harness_falls_back_to_local(self, monkeypatch):
        """No recognised env vars → harness is 'local'."""
        monkeypatch.delenv("AGENTIC_HARNESS", raising=False)
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
        monkeypatch.delenv("COPILOT_SESSION_ID", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert detect_harness() == "local"

    def test_detect_harness_returns_string(self, monkeypatch):
        """Return value is always a non-empty string."""
        monkeypatch.delenv("AGENTIC_HARNESS", raising=False)
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
        monkeypatch.delenv("COPILOT_SESSION_ID", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        result = detect_harness()
        assert isinstance(result, str)
        assert len(result) > 0


# ===========================================================================
# 2. get_session_id()
# ===========================================================================

class TestGetSessionId:
    """Tests for session ID retrieval/generation."""

    def test_get_session_id_from_agentic_env(self, monkeypatch):
        """AGENTIC_SESSION_ID takes priority."""
        monkeypatch.setenv("AGENTIC_SESSION_ID", "my-session-id")
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
        monkeypatch.delenv("COPILOT_SESSION_ID", raising=False)
        assert get_session_id() == "my-session-id"

    def test_get_session_id_from_claude_env(self, monkeypatch):
        """CLAUDE_SESSION_ID used when AGENTIC_SESSION_ID absent."""
        monkeypatch.delenv("AGENTIC_SESSION_ID", raising=False)
        monkeypatch.setenv("CLAUDE_SESSION_ID", "claude-sess-001")
        monkeypatch.delenv("COPILOT_SESSION_ID", raising=False)
        assert get_session_id() == "claude-sess-001"

    def test_get_session_id_from_copilot_env(self, monkeypatch):
        """COPILOT_SESSION_ID used when higher-priority vars absent."""
        monkeypatch.delenv("AGENTIC_SESSION_ID", raising=False)
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
        monkeypatch.setenv("COPILOT_SESSION_ID", "copilot-sess-42")
        assert get_session_id() == "copilot-sess-42"

    def test_get_session_id_generates_uuid_when_no_env(self, monkeypatch):
        """Generates a valid UUID when no env var is set."""
        monkeypatch.delenv("AGENTIC_SESSION_ID", raising=False)
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
        monkeypatch.delenv("COPILOT_SESSION_ID", raising=False)
        result = get_session_id()
        # Must be valid UUID4 string
        parsed = uuid.UUID(result, version=4)
        assert str(parsed) == result

    def test_get_session_id_returns_string(self, monkeypatch):
        """Always returns a non-empty string."""
        monkeypatch.delenv("AGENTIC_SESSION_ID", raising=False)
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
        monkeypatch.delenv("COPILOT_SESSION_ID", raising=False)
        result = get_session_id()
        assert isinstance(result, str)
        assert len(result) > 0


# ===========================================================================
# 3. get_queue_path()
# ===========================================================================

class TestGetQueuePath:
    """Tests for queue path construction."""

    def test_get_queue_path_structure(self, tmp_path):
        """Path follows ~/.agentic-engineers/artifacts/{session}/{harness}/queue/."""
        base = _fresh_base(tmp_path)
        result = get_queue_path("sess-abc", "claude", base_dir=base)
        expected = base / "artifacts" / "sess-abc" / "claude" / "queue"
        assert result == expected

    def test_get_queue_path_is_path_object(self, tmp_path):
        """Returns a pathlib.Path, not a string."""
        base = _fresh_base(tmp_path)
        result = get_queue_path("sess-abc", "claude", base_dir=base)
        assert isinstance(result, Path)

    def test_get_queue_path_different_harnesses_differ(self, tmp_path):
        """Two different harnesses produce different paths for same session."""
        base = _fresh_base(tmp_path)
        path_claude = get_queue_path("session-1", "claude", base_dir=base)
        path_gpt = get_queue_path("session-1", "gpt", base_dir=base)
        assert path_claude != path_gpt

    def test_get_queue_path_different_sessions_differ(self, tmp_path):
        """Two different sessions produce different paths for same harness."""
        base = _fresh_base(tmp_path)
        path_a = get_queue_path("session-A", "claude", base_dir=base)
        path_b = get_queue_path("session-B", "claude", base_dir=base)
        assert path_a != path_b

    def test_get_queue_path_uses_default_home_dir(self, monkeypatch, tmp_path):
        """Without explicit base_dir, defaults to ~/.agentic-engineers/."""
        fake_home = tmp_path / "fakehome"
        fake_home.mkdir()
        monkeypatch.setenv("HOME", str(fake_home))
        result = get_queue_path("sess-xyz", "local")
        expected_base = fake_home / ".agentic-engineers"
        assert str(result).startswith(str(expected_base))


# ===========================================================================
# 4. init_queue_structure()
# ===========================================================================

class TestInitQueueStructure:
    """Tests for directory/file structure initialisation."""

    def test_init_creates_queue_subdirs(self, tmp_path):
        """init_queue_structure creates incoming/, processing/, done/, failed/."""
        base = _fresh_base(tmp_path)
        init_queue_structure("sess-001", "claude", base_dir=base)
        queue_root = base / "artifacts" / "sess-001" / "claude" / "queue"
        for subdir in ("incoming", "processing", "done", "failed"):
            assert (queue_root / subdir).is_dir(), f"Missing subdir: {subdir}"

    def test_init_creates_keep_me_stubs(self, tmp_path):
        """init_queue_structure creates .keep.me files in each subdir."""
        base = _fresh_base(tmp_path)
        init_queue_structure("sess-002", "gpt", base_dir=base)
        queue_root = base / "artifacts" / "sess-002" / "gpt" / "queue"
        for subdir in ("incoming", "processing", "done", "failed"):
            keep = queue_root / subdir / ".keep.me"
            assert keep.exists(), f"Missing .keep.me in {subdir}"

    def test_init_creates_metadata_file(self, tmp_path):
        """init_queue_structure creates metadata.json in artifacts/<session>/<harness>/."""
        base = _fresh_base(tmp_path)
        init_queue_structure("sess-003", "local", base_dir=base)
        meta_path = base / "artifacts" / "sess-003" / "local" / "metadata.json"
        assert meta_path.exists()

    def test_metadata_contains_required_fields(self, tmp_path):
        """metadata.json has session_id, harness, created_at, last_accessed_at."""
        base = _fresh_base(tmp_path)
        init_queue_structure("sess-004", "claude", base_dir=base)
        meta_path = base / "artifacts" / "sess-004" / "claude" / "metadata.json"
        with meta_path.open() as fh:
            meta = json.load(fh)
        assert meta["session_id"] == "sess-004"
        assert meta["harness"] == "claude"
        assert "created_at" in meta
        assert "last_accessed_at" in meta

    def test_init_is_idempotent(self, tmp_path):
        """Calling init_queue_structure twice does not raise."""
        base = _fresh_base(tmp_path)
        init_queue_structure("sess-idem", "claude", base_dir=base)
        init_queue_structure("sess-idem", "claude", base_dir=base)  # Should not raise

    def test_init_updates_last_accessed_on_second_call(self, tmp_path):
        """Second call updates last_accessed_at in metadata.json."""
        import time
        base = _fresh_base(tmp_path)
        init_queue_structure("sess-time", "claude", base_dir=base)
        meta_path = base / "artifacts" / "sess-time" / "claude" / "metadata.json"
        with meta_path.open() as fh:
            first = json.load(fh)
        time.sleep(0.01)
        init_queue_structure("sess-time", "claude", base_dir=base)
        with meta_path.open() as fh:
            second = json.load(fh)
        # created_at must not change; last_accessed_at must be >= first value
        assert first["created_at"] == second["created_at"]
        assert second["last_accessed_at"] >= first["last_accessed_at"]


# ===========================================================================
# 5. Multi-harness and session isolation
# ===========================================================================

class TestIsolation:
    """Tests validating that harnesses and sessions are truly isolated."""

    def test_multi_harness_isolation_no_shared_dirs(self, tmp_path):
        """Two harnesses for same session have completely separate queue dirs."""
        base = _fresh_base(tmp_path)
        init_queue_structure("shared-session", "claude", base_dir=base)
        init_queue_structure("shared-session", "gpt", base_dir=base)

        claude_queue = base / "artifacts" / "shared-session" / "claude" / "queue"
        gpt_queue = base / "artifacts" / "shared-session" / "gpt" / "queue"

        assert claude_queue.exists()
        assert gpt_queue.exists()
        assert claude_queue != gpt_queue

        # Writing to claude dir does not appear in gpt dir
        (claude_queue / "incoming" / "claude-task.json").write_text("{}")
        assert not (gpt_queue / "incoming" / "claude-task.json").exists()

    def test_session_isolation_no_shared_dirs(self, tmp_path):
        """Two sessions for same harness have completely separate queue dirs."""
        base = _fresh_base(tmp_path)
        init_queue_structure("session-A", "local", base_dir=base)
        init_queue_structure("session-B", "local", base_dir=base)

        queue_a = base / "artifacts" / "session-A" / "local" / "queue"
        queue_b = base / "artifacts" / "session-B" / "local" / "queue"

        assert queue_a.exists()
        assert queue_b.exists()

        # Writing to session-A does not affect session-B
        (queue_a / "incoming" / "task-a.json").write_text("{}")
        assert not (queue_b / "incoming" / "task-a.json").exists()

    def test_auto_dir_creation_on_first_use(self, tmp_path):
        """Directories are created on first call; base_dir need not pre-exist."""
        base = _fresh_base(tmp_path)
        assert not base.exists(), "Precondition: base dir must not exist yet"
        init_queue_structure("new-session", "claude", base_dir=base)
        assert (base / "artifacts" / "new-session" / "claude" / "queue").exists()


# ===========================================================================
# 6. QueueIsolation class interface
# ===========================================================================

class TestQueueIsolationClass:
    """Tests for the high-level QueueIsolation class."""

    def test_class_instantiation(self, tmp_path):
        """QueueIsolation can be instantiated with session_id and harness."""
        base = _fresh_base(tmp_path)
        qi = QueueIsolation(session_id="sess-cls", harness="claude", base_dir=base)
        assert qi.session_id == "sess-cls"
        assert qi.harness == "claude"

    def test_class_queue_path_property(self, tmp_path):
        """QueueIsolation.queue_path returns correct path."""
        base = _fresh_base(tmp_path)
        qi = QueueIsolation(session_id="sess-cls2", harness="gpt", base_dir=base)
        expected = base / "artifacts" / "sess-cls2" / "gpt" / "queue"
        assert qi.queue_path == expected

    def test_class_initialise_creates_structure(self, tmp_path):
        """QueueIsolation.initialise() creates full queue structure."""
        base = _fresh_base(tmp_path)
        qi = QueueIsolation(session_id="sess-init", harness="local", base_dir=base)
        qi.initialise()
        assert (qi.queue_path / "incoming").is_dir()
        assert (qi.queue_path / "done").is_dir()
        meta = base / "artifacts" / "sess-init" / "local" / "metadata.json"
        assert meta.exists()
