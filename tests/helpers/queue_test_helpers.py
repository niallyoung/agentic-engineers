"""
Test helpers for queue isolation during migration.

Provides fixtures for testing both new (isolated) and legacy queue paths.
"""

import os
import sys
import uuid
import pytest
from pathlib import Path
from unittest.mock import patch
from typing import Generator, Tuple
import importlib

# Handle hyphenated skill directory name (queue-isolation -> queue_isolation)
queue_isolation_path = Path(__file__).parent.parent.parent / "src" / "skills" / "_meta" / "queue-isolation" / "scripts"
sys.path.insert(0, str(queue_isolation_path))
import queue_isolation


def setup_isolated_queue(
    tmp_path: Path,
    session_id: str = "test-session",
    harness: str = "local",
) -> Path:
    """
    Set up an isolated queue structure for testing.

    Args:
        tmp_path: Temporary directory for test isolation
        session_id: Session ID for the queue
        harness: Harness name (copilot, claude, gpt, local, etc.)

    Returns:
        Path to the queue root: tmp_path/.agentic-engineers/{harness}/{session}/queue/
    """
    qi = queue_isolation.QueueIsolation(
        session_id=session_id,
        harness=harness,
        base_dir=tmp_path / ".agentic-engineers",
    )
    qi.initialise()
    return qi.queue_path


def setup_legacy_queue(
    tmp_path: Path,
    session_id: str = "test-session",
) -> Path:
    """
    Set up a legacy queue structure for backward compatibility testing.

    Args:
        tmp_path: Temporary directory for test isolation
        session_id: Session ID for the queue

    Returns:
        Path to the legacy queue root: tmp_path/.copilot/queue/{session}/
    """
    legacy_path = tmp_path / ".copilot" / "queue" / session_id
    legacy_path.mkdir(parents=True, exist_ok=True)
    (legacy_path / "incoming").mkdir(exist_ok=True)
    (legacy_path / "processing").mkdir(exist_ok=True)
    (legacy_path / "done").mkdir(exist_ok=True)
    return legacy_path


@pytest.fixture
def isolated_queue_env(tmp_path: Path) -> Generator[Tuple[Path, dict], None, None]:
    """
    Fixture providing isolated queue with environment variables for testing.

    Yields:
        Tuple of (queue_path, env_vars_dict)
    """
    session_id = "test-session-" + str(uuid.uuid4())[:8]

    queue_path = setup_isolated_queue(tmp_path, session_id, "local")

    env_vars = {
        "AGENTIC_SESSION_ID": session_id,
        "AGENTIC_HARNESS": "local",
        "HOME": str(tmp_path),
    }

    with patch.dict(os.environ, env_vars, clear=False):
        yield queue_path, env_vars


@pytest.fixture
def isolated_queue_copilot(tmp_path: Path) -> Generator[Tuple[Path, dict], None, None]:
    """Fixture for isolated Copilot queue."""
    session_id = "test-copilot-" + str(uuid.uuid4())[:8]
    queue_path = setup_isolated_queue(tmp_path, session_id, "copilot")

    env_vars = {
        "AGENTIC_SESSION_ID": session_id,
        "AGENTIC_HARNESS": "copilot",
        "HOME": str(tmp_path),
    }

    with patch.dict(os.environ, env_vars, clear=False):
        yield queue_path, env_vars


@pytest.fixture
def isolated_queue_claude(tmp_path: Path) -> Generator[Tuple[Path, dict], None, None]:
    """Fixture for isolated Claude queue."""
    session_id = "test-claude-" + str(uuid.uuid4())[:8]
    queue_path = setup_isolated_queue(tmp_path, session_id, "claude")

    env_vars = {
        "AGENTIC_SESSION_ID": session_id,
        "AGENTIC_HARNESS": "claude",
        "HOME": str(tmp_path),
    }

    with patch.dict(os.environ, env_vars, clear=False):
        yield queue_path, env_vars


@pytest.fixture
def legacy_queue_env(tmp_path: Path) -> Generator[Tuple[Path, dict], None, None]:
    """
    Fixture providing legacy queue path for backward compatibility tests.

    Yields:
        Tuple of (legacy_path, env_vars_dict)
    """
    session_id = "test-session-" + str(uuid.uuid4())[:8]

    legacy_path = setup_legacy_queue(tmp_path, session_id)

    env_vars = {
        "COPILOT_SESSION_ID": session_id,
        "HOME": str(tmp_path),
    }

    with patch.dict(os.environ, env_vars, clear=False):
        yield legacy_path, env_vars


@pytest.fixture
def queue_test_env(tmp_path: Path) -> Generator[dict, None, None]:
    """
    Fixture providing a complete test environment for queue testing.

    Includes both isolated and legacy queues pre-configured.

    Yields:
        dict with keys:
        - tmp_path: Temporary directory
        - isolated_session_id: Session ID for isolated queue
        - isolated_queue_path: Path to isolated queue
        - legacy_session_id: Session ID for legacy queue
        - legacy_queue_path: Path to legacy queue
        - isolated_env: Environment variables for isolated queue
        - legacy_env: Environment variables for legacy queue
    """
    isolated_session_id = "test-iso-" + str(uuid.uuid4())[:8]
    legacy_session_id = "test-leg-" + str(uuid.uuid4())[:8]

    isolated_queue_path = setup_isolated_queue(tmp_path, isolated_session_id, "local")
    legacy_queue_path = setup_legacy_queue(tmp_path, legacy_session_id)

    isolated_env = {
        "AGENTIC_SESSION_ID": isolated_session_id,
        "AGENTIC_HARNESS": "local",
        "HOME": str(tmp_path),
    }

    legacy_env = {
        "COPILOT_SESSION_ID": legacy_session_id,
        "HOME": str(tmp_path),
    }

    yield {
        "tmp_path": tmp_path,
        "isolated_session_id": isolated_session_id,
        "isolated_queue_path": isolated_queue_path,
        "legacy_session_id": legacy_session_id,
        "legacy_queue_path": legacy_queue_path,
        "isolated_env": isolated_env,
        "legacy_env": legacy_env,
    }


def assert_queue_path_is_isolated(queue_path: Path, session_id: str, harness: str) -> None:
    """
    Assert that a queue path follows the canonical isolation structure.

    Pattern: ~/.agentic-engineers/{harness}/{session}/queue/
    (the legacy artifacts/ segment is deprecated — see docs/SPEC.md
    Queue Architecture & Paths (LOCKED SPEC))
    """
    path_str = str(queue_path)
    assert ".agentic-engineers" in path_str, f"Expected isolated path, got {queue_path}"
    assert "artifacts" not in path_str, (
        f"Expected canonical path without deprecated artifacts/ segment, got {queue_path}"
    )
    assert session_id in path_str, f"Expected session_id {session_id} in path {queue_path}"
    assert harness in path_str, f"Expected harness {harness} in path {queue_path}"
    assert queue_path.name == "queue", f"Expected path to end with 'queue/', got {queue_path}"


def assert_queue_path_is_legacy(queue_path: Path, session_id: str) -> None:
    """
    Assert that a queue path follows the legacy structure.

    Pattern: ~/.copilot/queue/{session_id}/
    """
    path_str = str(queue_path)
    assert ".copilot" in path_str, f"Expected legacy .copilot path, got {queue_path}"
    assert "queue" in path_str, f"Expected queue in path, got {queue_path}"
    assert session_id in path_str, f"Expected session_id {session_id} in path {queue_path}"
    assert ".agentic-engineers" not in path_str, (
        f"Expected legacy path, not isolated path. Got {queue_path}"
    )


def assert_queue_subdirs_exist(queue_path: Path, subdirs: list = None) -> None:
    """
    Assert that queue subdirectories exist.

    Args:
        queue_path: Root queue path
        subdirs: List of subdirectories to check (default: incoming, processing, done, failed)
    """
    if subdirs is None:
        subdirs = ["incoming", "processing", "done", "failed"]

    for subdir in subdirs:
        subdir_path = queue_path / subdir
        assert (
            subdir_path.exists()
        ), f"Expected queue subdirectory {subdir} to exist at {subdir_path}"
        assert subdir_path.is_dir(), f"Expected {subdir_path} to be a directory"
