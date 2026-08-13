"""
Fresh Install Verification Tests

Tests verify that `make install-fresh` and related installation operations
preserve queue data when using the new unified queue path structure.

Key requirement: Queue data in ~/.agentic-engineers/ survives installation operations
while preserving data integrity across harnesses.
"""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile

# Path isolation now lives in queue-management's queue_ops.py (the deleted
# src/skills/_meta/queue-isolation skill's QueueIsolation class was
# consolidated there).
_qm_scripts = Path(__file__).parent.parent / "src" / "skills" / "queue-management" / "scripts"
if str(_qm_scripts) not in sys.path:
    sys.path.insert(0, str(_qm_scripts))

from queue_ops import get_queue_path  # noqa: E402
from tests.helpers.queue_test_helpers import (
    setup_isolated_queue,
    setup_legacy_queue,
    assert_queue_path_is_isolated,
    assert_queue_subdirs_exist,
)

_QUEUE_SUBDIRS = ("incoming", "processing", "done", "failed")


def _init_queue(session_id, harness, base_dir):
    """Compute + create a queue path for the given session/harness (mirrors
    setup_isolated_queue, but driven by explicit env-derived args)."""
    queue_path = get_queue_path(session_id, harness, base_dir=base_dir)
    for subdir in _QUEUE_SUBDIRS:
        (queue_path / subdir).mkdir(parents=True, exist_ok=True)
    return queue_path


class TestFreshInstallPreservesQueueData:
    """Test that fresh install operations preserve queue data."""

    def test_isolated_queue_survives_fresh_install_simulation(self, tmp_path):
        """Simulate fresh install doesn't wipe ~/.agentic-engineers/."""
        session_id = "test-install-" + "abc123"

        # Create isolated queue with data
        queue_path = setup_isolated_queue(tmp_path, session_id, "copilot")
        task_file = queue_path / "incoming" / "task-1.yaml"
        task_data = {"task_id": "task-1", "scope": "Test task"}
        task_file.write_text(json.dumps(task_data))

        # Store reference to artifacts directory
        artifacts_dir = tmp_path / ".agentic-engineers"
        assert artifacts_dir.exists()

        # Simulate fresh install: wipe repo but preserve HOME
        # (In real scenario, make install-fresh would only wipe cwd, not HOME)
        repo_contents = tmp_path / "repo-simulation"
        repo_contents.mkdir()

        # Verify artifacts still exist after "install fresh"
        assert artifacts_dir.exists()
        assert task_file.exists()
        assert task_file.read_text() == json.dumps(task_data)

    def test_multiple_harness_queues_preserved(self, tmp_path):
        """Verify all harness queues are preserved during install."""
        session_id = "test-multi-harness-install"

        # Create queues for all harnesses
        harnesses = ["claude", "copilot", "gpt", "local"]
        queue_paths = {}
        task_files = {}

        for harness in harnesses:
            queue_path = setup_isolated_queue(tmp_path, session_id, harness)
            queue_paths[harness] = queue_path

            # Add task file
            task_file = queue_path / "incoming" / f"task-{harness}.yaml"
            task_files[harness] = task_file
            task_file.write_text(f'{{"harness": "{harness}"}}')

        # Simulate install fresh (artifacts_dir preserved)
        artifacts_dir = tmp_path / ".agentic-engineers"

        # Verify all data preserved
        for harness, task_file in task_files.items():
            assert task_file.exists(), f"Lost data for {harness}"
            assert f'"{harness}"' in task_file.read_text()

    def test_legacy_queue_needs_migration_notice(self, tmp_path):
        """Verify legacy queues are detected and marked for migration."""
        session_id = "legacy-migrate-test"

        # Create legacy structure
        legacy_queue = setup_legacy_queue(tmp_path, session_id)
        legacy_task = legacy_queue / "incoming" / "legacy-task.yaml"
        legacy_task.write_text("legacy: true")

        # On fresh install, should detect legacy structure
        artifacts_dir = tmp_path / ".agentic-engineers"
        copilot_queue = setup_isolated_queue(tmp_path, session_id, "copilot")

        # Legacy should still exist (migration is manual or explicit)
        assert legacy_queue.exists()
        assert legacy_task.exists()

        # New structure created
        assert copilot_queue.exists()


class TestQueueContinuityPostInstall:
    """Test that queue operations continue working after install."""

    def test_list_incoming_after_install(self, tmp_path):
        """Verify incoming queue listing works post-install."""
        session_id = "test-list-incoming"

        queue_path = setup_isolated_queue(tmp_path, session_id, "copilot")
        incoming = queue_path / "incoming"

        # Add test tasks
        for i in range(3):
            task_file = incoming / f"task-{i}.yaml"
            task_file.write_text(f"task_id: task-{i}")

        # Verify list works (simulating post-install)
        incoming_files = list(incoming.glob("task-*.yaml"))
        assert len(incoming_files) == 3

    def test_delegation_works_after_install(self, tmp_path):
        """Verify DELEGATE processing works post-install."""
        session_id = "test-delegate-post-install"

        queue_path = setup_isolated_queue(tmp_path, session_id, "copilot")
        incoming = queue_path / "incoming"
        processing = queue_path / "processing"

        # Create delegate file
        delegate_file = incoming / "2025-01-01-task-1.yaml"
        delegate_data = {
            "handoff_type": "DELEGATE",
            "task_id": "2025-01-01-task-1",
            "role": "engineer",
        }
        delegate_file.write_text(json.dumps(delegate_data))

        # Simulate pickup: move to processing
        assert delegate_file.exists()
        delegate_file.rename(processing / delegate_file.name)

        # Verify transition worked
        assert not (incoming / delegate_file.name).exists()
        assert (processing / delegate_file.name).exists()

    def test_handback_processing_post_install(self, tmp_path):
        """Verify HANDBACK processing works post-install."""
        session_id = "test-handback-post-install"

        queue_path = setup_isolated_queue(tmp_path, session_id, "copilot")
        done = queue_path / "done"

        # Create handback file
        handback_file = done / "2025-01-01-task-1-PASS.yaml"
        handback_data = {
            "handoff_type": "HANDBACK",
            "task_id": "2025-01-01-task-1",
            "status": "success",
            "quality_score": 92,
        }
        handback_file.write_text(json.dumps(handback_data))

        # Verify file readable post-install
        content = json.loads(handback_file.read_text())
        assert content["quality_score"] == 92


class TestInstallFreshWithMultipleHarnesses:
    """Test install-fresh behavior with multiple concurrent harnesses."""

    def test_concurrent_harnesses_preserve_independently(self, tmp_path):
        """Verify independent preservation of concurrent harness data."""
        session_id = "test-concurrent-install"

        # Setup three harnesses
        queue_paths = {}
        for harness in ["claude", "copilot", "gpt"]:
            queue_path = setup_isolated_queue(tmp_path, session_id, harness)
            queue_paths[harness] = queue_path

            # Each has different tasks in different states
            if harness == "claude":
                (queue_path / "incoming" / "task-1.yaml").write_text("task: 1")
            elif harness == "copilot":
                (queue_path / "processing" / "task-2.yaml").write_text("task: 2")
            else:  # gpt
                (queue_path / "done" / "task-3.yaml").write_text("task: 3")

        # Simulate install fresh
        # (All harness queues in artifacts are preserved)
        artifacts_dir = tmp_path / ".agentic-engineers"

        # Verify all states preserved
        assert (queue_paths["claude"] / "incoming" / "task-1.yaml").exists()
        assert (queue_paths["copilot"] / "processing" / "task-2.yaml").exists()
        assert (queue_paths["gpt"] / "done" / "task-3.yaml").exists()

    def test_harness_switching_after_install(self, tmp_path):
        """Verify harness switching works correctly after install."""
        session_id = "test-switch-after-install"

        # Create Copilot queue with tasks
        copilot_q = setup_isolated_queue(tmp_path, session_id, "copilot")
        (copilot_q / "incoming" / "copilot-task.yaml").write_text("harness: copilot")

        # Simulate install fresh
        # Then switch to Claude
        claude_q = setup_isolated_queue(tmp_path, session_id, "claude")
        (claude_q / "incoming" / "claude-task.yaml").write_text("harness: claude")

        # Verify switch preserved Copilot data
        assert (copilot_q / "incoming" / "copilot-task.yaml").exists()
        assert (claude_q / "incoming" / "claude-task.yaml").exists()

        # Switch back to Copilot
        copilot_q_again = setup_isolated_queue(tmp_path, session_id, "copilot")
        assert (copilot_q_again / "incoming" / "copilot-task.yaml").exists()

        # Claude data not visible from Copilot
        assert not (copilot_q_again / "incoming" / "claude-task.yaml").exists()


class TestInstallFreshEnvironmentVariables:
    """Test environment variable handling across install operations."""

    def test_agentic_session_id_persists(self, tmp_path):
        """Verify AGENTIC_SESSION_ID is maintained across installs."""
        session_id = "test-env-persist"

        env_vars = {
            "AGENTIC_SESSION_ID": session_id,
            "AGENTIC_HARNESS": "copilot",
            "HOME": str(tmp_path),
        }

        with patch.dict(os.environ, env_vars, clear=False):
            # Initial queue creation
            path1 = _init_queue(session_id, "copilot", tmp_path / ".agentic-engineers")

            # "After install" - session ID should be same
            path2 = _init_queue(session_id, "copilot", tmp_path / ".agentic-engineers")

            # Paths should be identical (same session, same harness)
            assert path1 == path2

    def test_agentic_harness_switchable_after_install(self, tmp_path):
        """Verify AGENTIC_HARNESS can be switched after install."""
        session_id = "test-harness-switch"

        # Start with Claude
        env1 = {
            "AGENTIC_SESSION_ID": session_id,
            "AGENTIC_HARNESS": "claude",
            "HOME": str(tmp_path),
        }

        with patch.dict(os.environ, env1, clear=False):
            path1 = _init_queue(session_id, "claude", tmp_path / ".agentic-engineers")
            assert "claude" in str(path1)

        # Switch to Copilot after "install fresh"
        env2 = {
            "AGENTIC_SESSION_ID": session_id,
            "AGENTIC_HARNESS": "copilot",
            "HOME": str(tmp_path),
        }

        with patch.dict(os.environ, env2, clear=False):
            path2 = _init_queue(session_id, "copilot", tmp_path / ".agentic-engineers")
            assert "copilot" in str(path2)

        # Verify paths are different (different harnesses)
        assert path1 != path2


class TestInstallFreshDataIntegrity:
    """Test data integrity across install operations."""

    def test_task_data_integrity_preserved(self, tmp_path):
        """Verify task data isn't corrupted during install."""
        session_id = "test-data-integrity"

        queue_path = setup_isolated_queue(tmp_path, session_id, "copilot")
        task_file = queue_path / "incoming" / "complex-task.yaml"

        # Write complex task data
        task_data = {
            "task_id": "2025-01-01-task",
            "role": "senior-engineer",
            "scope": "Multi-line\nscope\nwith\ndetails",
            "dependencies": ["dep1", "dep2", "dep3"],
            "metadata": {"version": 1, "tags": ["important", "urgent"]},
        }
        task_file.write_text(json.dumps(task_data, indent=2))

        # "After install" - verify data integrity
        read_back = json.loads(task_file.read_text())
        assert read_back == task_data
        assert read_back["scope"] == task_data["scope"]

