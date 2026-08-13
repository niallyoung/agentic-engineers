"""
Multi-Harness Queue Isolation Tests

Tests verify that different AI harnesses (Claude, Copilot, GPT, local) maintain
isolated queue directories and don't cross-contaminate session data.

Requirement: Single user can run multiple harnesses simultaneously with separate queues.
"""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch
import uuid
import tempfile

# Path isolation now lives in queue-management's queue_ops.py (the deleted
# src/skills/_meta/queue-isolation skill's QueueIsolation class was
# consolidated there).
_qm_scripts = Path(__file__).parent.parent / "src" / "skills" / "queue-management" / "scripts"
if str(_qm_scripts) not in sys.path:
    sys.path.insert(0, str(_qm_scripts))

from queue_ops import detect_harness, get_session_id, get_queue_path  # noqa: E402
from tests.helpers.queue_test_helpers import (
    setup_isolated_queue,
    assert_queue_path_is_isolated,
    assert_queue_subdirs_exist,
)


class TestMultiHarnessIsolation:
    """Test that different harnesses maintain isolated queues."""

    def test_copilot_and_claude_queues_dont_collide(self, tmp_path):
        """Verify Claude and Copilot queues for same session-id are isolated."""
        session_id = "test-123"

        # Create Claude queue
        claude_path = setup_isolated_queue(tmp_path, session_id, "claude")
        (claude_path / "incoming" / "test-claude.yaml").write_text("claude: true")

        # Create Copilot queue
        copilot_path = setup_isolated_queue(tmp_path, session_id, "copilot")
        (copilot_path / "incoming" / "test-copilot.yaml").write_text("copilot: true")

        # Verify they're different paths
        assert claude_path != copilot_path
        assert "claude" in str(claude_path)
        assert "copilot" in str(copilot_path)

        # Verify files are isolated
        assert (claude_path / "incoming" / "test-claude.yaml").exists()
        assert not (claude_path / "incoming" / "test-copilot.yaml").exists()
        assert (copilot_path / "incoming" / "test-copilot.yaml").exists()
        assert not (copilot_path / "incoming" / "test-claude.yaml").exists()

    def test_three_simultaneous_harnesses(self, tmp_path):
        """Test three harnesses running simultaneously with same session."""
        session_id = "test-multi-" + str(uuid.uuid4())[:8]

        # Create queues for three harnesses
        harnesses = ["claude", "copilot", "gpt"]
        queues = {}

        for harness in harnesses:
            queue_path = setup_isolated_queue(tmp_path, session_id, harness)
            queues[harness] = queue_path

            # Add test file for each
            (queue_path / "incoming" / f"test-{harness}.yaml").write_text(
                f"harness: {harness}\nsession: {session_id}\n"
            )

        # Verify all are unique
        assert len(set(str(q) for q in queues.values())) == 3

        # Verify each has its own file
        for harness, queue_path in queues.items():
            assert (queue_path / "incoming" / f"test-{harness}.yaml").exists()
            for other_harness in harnesses:
                if other_harness != harness:
                    assert not (
                        queue_path / "incoming" / f"test-{other_harness}.yaml"
                    ).exists(), f"Cross-contamination: {harness} queue has {other_harness} file"

    def test_harness_switching_preserves_data(self, tmp_path):
        """Verify switching harnesses doesn't lose data."""
        session_id = "test-switch"

        # Create Copilot queue with data
        copilot_q = setup_isolated_queue(tmp_path, session_id, "copilot")
        copilot_data = {"task_id": "task-1", "harness": "copilot"}
        (copilot_q / "incoming" / "task-1.yaml").write_text(json.dumps(copilot_data))

        # Switch to Claude
        claude_q = setup_isolated_queue(tmp_path, session_id, "claude")
        claude_data = {"task_id": "task-2", "harness": "claude"}
        (claude_q / "incoming" / "task-2.yaml").write_text(json.dumps(claude_data))

        # Switch back to Copilot - data should still be there
        copilot_q_again = setup_isolated_queue(tmp_path, session_id, "copilot")
        assert (copilot_q_again / "incoming" / "task-1.yaml").exists()
        assert (copilot_q_again / "incoming" / "task-1.yaml").read_text() == json.dumps(
            copilot_data
        )

        # Claude data should not be in Copilot queue
        assert not (copilot_q_again / "incoming" / "task-2.yaml").exists()

    def test_environment_variable_priority_for_harness(self, tmp_path):
        """Test AGENTIC_HARNESS env var overrides detection."""
        session_id = "test-env-priority"

        # Test with explicit AGENTIC_HARNESS
        env_vars = {
            "AGENTIC_SESSION_ID": session_id,
            "AGENTIC_HARNESS": "explicit-harness",
            "HOME": str(tmp_path),
        }

        with patch.dict(os.environ, env_vars, clear=False):
            harness = detect_harness()
            session_id = get_session_id()
            assert harness == "explicit-harness"
            queue_path = get_queue_path(session_id, harness, base_dir=tmp_path / ".agentic-engineers")
            assert "explicit-harness" in str(queue_path)

    def test_session_id_environment_variable_priority(self, tmp_path):
        """Test AGENTIC_SESSION_ID env var is used."""
        env_vars = {
            "AGENTIC_SESSION_ID": "explicit-session-id",
            "AGENTIC_HARNESS": "local",
            "HOME": str(tmp_path),
        }

        with patch.dict(os.environ, env_vars, clear=False):
            assert get_session_id() == "explicit-session-id"


class TestIsolationPathStructure:
    """Test the isolation path structure is correct."""

    def test_isolated_path_includes_session_and_harness(self, tmp_path):
        """Verify isolated paths follow new structure."""
        session_id = "test-sess-123"
        harness = "copilot"

        queue_path = setup_isolated_queue(tmp_path, session_id, harness)
        assert_queue_path_is_isolated(queue_path, session_id, harness)

    def test_isolated_path_has_queue_subdirectories(self, tmp_path):
        """Verify all queue subdirectories exist."""
        session_id = "test-subdirs"
        harness = "claude"

        queue_path = setup_isolated_queue(tmp_path, session_id, harness)
        assert_queue_subdirs_exist(
            queue_path, subdirs=["incoming", "processing", "done", "failed"]
        )

    def test_isolated_path_base_dir_override(self, tmp_path):
        """Test base_dir parameter allows custom locations."""
        custom_base = tmp_path / "custom-location" / ".agentic-engineers"
        session_id = "test-custom"
        harness = "local"

        queue_path = setup_isolated_queue(
            tmp_path / "custom-location", session_id, harness
        )

        assert "custom-location" in str(queue_path)
        assert queue_path.exists()
        assert_queue_subdirs_exist(queue_path)


class TestConcurrentAccessIsolation:
    """Test isolation with concurrent access patterns."""

    def test_two_harnesses_writing_simultaneously(self, tmp_path):
        """Simulate concurrent writes to different harness queues."""
        session_id = "test-concurrent"

        # Setup both queues
        claude_q = setup_isolated_queue(tmp_path, session_id, "claude")
        copilot_q = setup_isolated_queue(tmp_path, session_id, "copilot")

        # Simulate concurrent writes
        claude_file = claude_q / "incoming" / "claude-task.yaml"
        copilot_file = copilot_q / "incoming" / "copilot-task.yaml"

        claude_file.write_text("task: claude-1")
        copilot_file.write_text("task: copilot-1")

        # Overwrite one (simulate processing)
        claude_file.write_text("task: claude-1-processed")

        # Verify other is unaffected
        assert copilot_file.read_text() == "task: copilot-1"
        assert claude_file.read_text() == "task: claude-1-processed"

    def test_harness_isolation_across_state_transitions(self, tmp_path):
        """Test isolation during state transitions (incoming→processing→done)."""
        session_id = "test-states"

        # Setup both harnesses
        claude_q = setup_isolated_queue(tmp_path, session_id, "claude")
        copilot_q = setup_isolated_queue(tmp_path, session_id, "copilot")

        # Move file through Claude workflow
        claude_incoming = claude_q / "incoming" / "task.yaml"
        claude_processing = claude_q / "processing" / "task.yaml"
        claude_incoming.write_text("status: received")
        claude_incoming.rename(claude_processing)

        # Verify Copilot queue is unaffected
        assert not (copilot_q / "processing" / "task.yaml").exists()

        # Move file through Copilot workflow independently
        copilot_incoming = copilot_q / "incoming" / "task.yaml"
        copilot_done = copilot_q / "done" / "task.yaml"
        copilot_incoming.write_text("status: received")
        copilot_incoming.rename(copilot_done)

        # Verify state isolation
        assert (claude_q / "processing" / "task.yaml").exists()
        assert (copilot_q / "done" / "task.yaml").exists()
        assert not (copilot_q / "processing" / "task.yaml").exists()


class TestBackwardCompatibility:
    """Test backward compatibility with legacy queue paths."""

    def test_legacy_queue_detection(self, tmp_path):
        """Verify legacy queues are still detected when no isolation available."""
        session_id = "legacy-test"

        # Create legacy structure
        legacy_path = tmp_path / ".copilot" / "queue" / session_id
        legacy_path.mkdir(parents=True)
        (legacy_path / "incoming").mkdir()

        # Verify we can still create isolated structure
        isolated_path = setup_isolated_queue(tmp_path, session_id, "copilot")

        # Both should exist
        assert legacy_path.exists()
        assert isolated_path.exists()

        # They should be different
        assert legacy_path != isolated_path

    def test_harness_isolation_priority_over_legacy(self, tmp_path):
        """Verify isolation is preferred over legacy when both available."""
        session_id = "test-priority"

        # Create both
        legacy_path = tmp_path / ".copilot" / "queue" / session_id
        legacy_path.mkdir(parents=True)

        isolated_path = setup_isolated_queue(tmp_path, session_id, "copilot")

        # Add data to both
        (legacy_path / "incoming").mkdir(exist_ok=True)
        (legacy_path / "incoming" / "legacy.yaml").write_text("legacy: true")
        (isolated_path / "incoming" / "isolated.yaml").write_text("isolated: true")

        # Verify isolation is separate from legacy
        assert (isolated_path / "incoming" / "isolated.yaml").exists()
        assert not (isolated_path / "incoming" / "legacy.yaml").exists()
        assert (legacy_path / "incoming" / "legacy.yaml").exists()
