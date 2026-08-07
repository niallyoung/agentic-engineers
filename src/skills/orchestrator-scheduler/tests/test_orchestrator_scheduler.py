"""Tests for OrchestratorScheduler."""

import os
import time
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import after path setup — use importlib to handle the hyphenated directory name.
import sys
import importlib.util

_skill_root = Path(__file__).parent.parent
_script_path = _skill_root / "scripts" / "orchestrator_scheduler.py"
_spec = importlib.util.spec_from_file_location("orchestrator_scheduler", _script_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
OrchestratorScheduler = _mod.OrchestratorScheduler
QueueLock = _mod.QueueLock
LockTimeoutError = _mod.LockTimeoutError


class TestSessionDetection:
    """Test runtime session ID detection from environment."""

    def test_detect_session_id_from_claude_session_id(self):
        """Should detect CLAUDE_SESSION_ID from environment."""
        with patch.dict(os.environ, {'CLAUDE_SESSION_ID': 'test-session-123'}):
            scheduler = OrchestratorScheduler()
            assert scheduler.session_id == 'test-session-123'

    def test_detect_session_id_from_claude_code_session_id(self):
        """Should detect CLAUDE_CODE_SESSION_ID from environment."""
        with patch.dict(os.environ, {'CLAUDE_CODE_SESSION_ID': 'code-session-456'}, clear=False):
            # Clear CLAUDE_SESSION_ID to test fallback
            os.environ.pop('CLAUDE_SESSION_ID', None)
            scheduler = OrchestratorScheduler()
            assert scheduler.session_id == 'code-session-456'

    def test_detect_harness_from_agentic_harness(self):
        """Should detect AGENTIC_HARNESS from environment."""
        with patch.dict(os.environ, {
            'CLAUDE_SESSION_ID': 'test-session',
            'AGENTIC_HARNESS': 'copilot'
        }):
            scheduler = OrchestratorScheduler()
            assert scheduler.harness == 'copilot'

    def test_detect_harness_defaults_to_claude(self):
        """Should default to 'claude' harness."""
        with patch.dict(os.environ, {'CLAUDE_SESSION_ID': 'test-session'}):
            scheduler = OrchestratorScheduler()
            assert scheduler.harness == 'claude'

    def test_missing_session_id_raises_error(self):
        """Should raise RuntimeError if no session ID found."""
        with patch.dict(os.environ, {}, clear=True):
            # Set a fake harness detection to avoid issues
            with patch('os.environ.get', return_value=None):
                with pytest.raises(RuntimeError, match="No session ID found"):
                    OrchestratorScheduler()


class TestSchedulerInitialization:
    """Test OrchestratorScheduler initialization."""

    def test_scheduler_initializes_with_env_vars(self):
        """Should initialize scheduler with environment variables."""
        with patch.dict(os.environ, {
            'CLAUDE_SESSION_ID': 'test-session-123',
            'AGENTIC_HARNESS': 'claude'
        }):
            scheduler = OrchestratorScheduler()
            assert scheduler.session_id == 'test-session-123'
            assert scheduler.harness == 'claude'
            assert scheduler.orchestrator is None  # Lazy loaded


class TestSchedulerRun:
    """Test queue polling execution."""

    def test_run_loads_orchestrator_skill(self):
        """Should lazy-load OrchestratorSkill on first run."""
        with patch.dict(os.environ, {'CLAUDE_SESSION_ID': 'test-session'}):
            scheduler = OrchestratorScheduler()

            # Mock the OrchestratorSkill pre-injected (bypasses lazy-import machinery)
            mock_orch = MagicMock()
            mock_orch.poll_queue.return_value = (2, 0)
            scheduler.orchestrator = mock_orch

            processed, failed = scheduler.run()

            assert processed == 2
            assert failed == 0
            mock_orch.poll_queue.assert_called_once()

    def test_run_handles_tuple_return(self):
        """Should handle tuple return from poll_queue."""
        with patch.dict(os.environ, {'CLAUDE_SESSION_ID': 'test-session'}):
            scheduler = OrchestratorScheduler()

            # Mock orchestrator
            mock_orch = MagicMock()
            mock_orch.poll_queue.return_value = (3, 1)
            scheduler.orchestrator = mock_orch

            processed, failed = scheduler.run()

            assert processed == 3
            assert failed == 1


def _make_scheduler(queue_root: Path, delegate_files=0) -> "OrchestratorScheduler":
    """
    Build a scheduler with a mock OrchestratorSkill rooted at queue_root.

    Args:
        queue_root: temp queue root; incoming/ is created under it.
        delegate_files: number of *.yaml DELEGATE files to seed in incoming/.
    """
    with patch.dict(os.environ, {'CLAUDE_SESSION_ID': 'test-session'}):
        scheduler = OrchestratorScheduler()

    incoming = queue_root / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    for i in range(delegate_files):
        (incoming / f"task-{i}.yaml").write_text(
            f"handoff_type: DELEGATE\ntask_id: task-{i}\nagent: engineer\n"
        )

    mock_orch = MagicMock()
    mock_orch.queue_root = queue_root
    scheduler.orchestrator = mock_orch
    return scheduler


class TestQueueLock:
    """File-based queue lock: acquire/release, contention, stale cleanup."""

    def test_acquire_creates_lock_file(self, tmp_path):
        lock = QueueLock(tmp_path / "queue" / ".lock", harness="claude")
        lock.acquire()
        assert lock.lock_path.exists()
        contents = lock.lock_path.read_text().splitlines()
        assert contents[0] == str(os.getpid())
        assert contents[2] == "claude"
        lock.release()
        assert not lock.lock_path.exists()

    def test_concurrent_acquire_blocked(self, tmp_path):
        """A second harness cannot acquire a lock held by the first."""
        lock_path = tmp_path / "queue" / ".lock"
        first = QueueLock(lock_path, harness="claude", acquire_timeout_seconds=1)
        first.acquire()

        second = QueueLock(lock_path, harness="opencode", acquire_timeout_seconds=1)
        with pytest.raises(LockTimeoutError):
            second.acquire()

        first.release()
        # Now the second harness can acquire.
        second.acquire()
        assert second.lock_path.exists()
        second.release()

    def test_stale_lock_cleanup(self, tmp_path):
        """Lock older than stale threshold is removed and reacquired."""
        lock_path = tmp_path / "queue" / ".lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text("99999\nold\nclaude\n")

        # Backdate mtime by 400s (> 300s default).
        old = time.time() - 400
        os.utime(lock_path, (old, old))

        lock = QueueLock(lock_path, harness="claude", stale_age_seconds=300)
        lock.acquire()  # Should clean up stale lock and acquire.
        assert lock.lock_path.read_text().splitlines()[0] == str(os.getpid())
        lock.release()

    def test_release_is_idempotent(self, tmp_path):
        lock = QueueLock(tmp_path / "queue" / ".lock")
        lock.acquire()
        lock.release()
        lock.release()  # Should not raise.


class TestPollOnce:
    """--poll-once behavior: single cycle, JSON result, locking, batching."""

    def test_poll_once_empty_queue(self, tmp_path):
        scheduler = _make_scheduler(tmp_path / "queue", delegate_files=0)
        result = scheduler.poll_queue_once()

        assert result["processed"] == 0
        assert result["failed"] == 0
        assert result["queue_empty"] is True
        assert result["errors"] == []
        assert "duration_ms" in result
        # poll_queue should not even be called for an empty queue.
        scheduler.orchestrator.poll_queue.assert_not_called()

    def test_poll_once_processes_batch(self, tmp_path):
        """Process 3+ DELEGATEs in a single poll cycle."""
        queue_root = tmp_path / "queue"
        scheduler = _make_scheduler(queue_root, delegate_files=3)

        def _consume():
            # Simulate orchestrator draining incoming/.
            for f in (queue_root / "incoming").glob("*.yaml"):
                f.unlink()
            return (3, 0)

        scheduler.orchestrator.poll_queue.side_effect = _consume

        result = scheduler.poll_queue_once()

        assert result["processed"] == 3
        assert result["failed"] == 0
        assert result["queue_empty"] is True
        assert result["errors"] == []
        scheduler.orchestrator.poll_queue.assert_called_once()

    def test_poll_once_returns_json_serializable(self, tmp_path):
        import json
        scheduler = _make_scheduler(tmp_path / "queue", delegate_files=0)
        result = scheduler.poll_queue_once()
        # Must round-trip through JSON for harness consumption.
        assert json.loads(json.dumps(result))["session_id"] == "test-session"

    def test_poll_once_skips_when_locked(self, tmp_path):
        """If lock held by another harness, poll-once skips (not an error)."""
        queue_root = tmp_path / "queue"
        scheduler = _make_scheduler(queue_root, delegate_files=2)

        # Pre-hold the lock from a "different" harness (fresh, not stale).
        held = QueueLock(queue_root / ".lock", harness="opencode")
        held.acquire()
        scheduler.lock_acquire_timeout_seconds = 1

        result = scheduler.poll_queue_once()

        assert result["lock_skipped"] is True
        assert result["processed"] == 0
        scheduler.orchestrator.poll_queue.assert_not_called()
        held.release()

    def test_poll_once_releases_lock_after(self, tmp_path):
        """Lock file must not remain after a successful poll cycle."""
        queue_root = tmp_path / "queue"
        scheduler = _make_scheduler(queue_root, delegate_files=1)

        def _consume():
            for f in (queue_root / "incoming").glob("*.yaml"):
                f.unlink()
            return (1, 0)

        scheduler.orchestrator.poll_queue.side_effect = _consume
        scheduler.poll_queue_once()
        assert not (queue_root / ".lock").exists()

    def test_poll_once_releases_lock_on_error(self, tmp_path):
        """Lock is released even if poll_queue raises."""
        queue_root = tmp_path / "queue"
        scheduler = _make_scheduler(queue_root, delegate_files=1)
        scheduler.orchestrator.poll_queue.side_effect = RuntimeError("boom")

        result = scheduler.poll_queue_once()

        assert result["failed"] == 1
        assert any(e["stage"] == "process" for e in result["errors"])
        assert not (queue_root / ".lock").exists()


class TestSessionOverride:
    """--session-id override path."""

    def test_explicit_session_id_overrides_env(self):
        with patch.dict(os.environ, {'CLAUDE_SESSION_ID': 'env-session'}):
            scheduler = OrchestratorScheduler(session_id="override-session")
            assert scheduler.session_id == "override-session"

    def test_explicit_session_id_without_env(self):
        with patch.dict(os.environ, {}, clear=True):
            scheduler = OrchestratorScheduler(session_id="standalone-session")
            assert scheduler.session_id == "standalone-session"


class TestE2EQueueToDone:
    """End-to-end: DELEGATE in incoming/ → poll-once → real OrchestratorSkill."""

    def test_e2e_queue_to_done(self, tmp_path, monkeypatch):
        """
        Wire a real OrchestratorSkill rooted at a temp queue, stub agent
        spawning, and verify a DELEGATE moves incoming/ → done/ via poll-once.
        """
        # Make the orchestrator importable.
        # __file__ = src/skills/orchestrator-scheduler/tests/<this>; 4x parent = src/.
        src = Path(__file__).parent.parent.parent.parent
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))
        try:
            from skills.orchestrator.scripts.orchestrator_skill import OrchestratorSkill
        except Exception as e:  # pragma: no cover
            pytest.skip(f"OrchestratorSkill unavailable: {e}")

        queue_root = tmp_path / "queue"
        orch = OrchestratorSkill(
            session_id="e2e-session",
            harness="claude",
            queue_root=str(queue_root),
        )

        # Stub agent spawn to return a valid HANDBACK YAML block.
        def _fake_spawn(delegate):
            tid = delegate["task_id"]
            return (
                f"handoff_type: HANDBACK\n"
                f"task_id: {tid}\n"
                f"status: success\n"
                f"output: done by stub\n"
                f"metrics:\n"
                f"  quality: 0.9\n  tokens: 100\n  cost: 0.01\n  duration_seconds: 1\n"
            )

        monkeypatch.setattr(orch, "spawn_sub_agent", _fake_spawn)
        # Approve the QE gate so a success HANDBACK lands in done/.
        monkeypatch.setattr(orch, "invoke_qe_gate", lambda task_id, hb: True)

        # Seed a DELEGATE in incoming/.
        delegate = (
            "handoff_type: DELEGATE\n"
            "task_id: e2e-task-1\n"
            "agent: engineer\n"
            "scope: 'End to end queue processing validation with the orchestrator skill flow'\n"
            "context: []\n"
            "plan: []\n"
            "success_criteria: []\n"
        )
        (queue_root / "incoming" / "e2e-task-1.yaml").write_text(delegate)

        with patch.dict(os.environ, {'CLAUDE_SESSION_ID': 'e2e-session'}):
            scheduler = OrchestratorScheduler()
        scheduler.orchestrator = orch

        result = scheduler.poll_queue_once()

        assert result["processed"] == 1, result
        assert result["failed"] == 0, result
        # incoming/ drained; done/ has the DELEGATE and its HANDBACK.
        assert list((queue_root / "incoming").glob("*.yaml")) == []
        assert (queue_root / "done" / "e2e-task-1.yaml").exists()
        assert (queue_root / "done" / "e2e-task-1-HANDBACK.yaml").exists()
        assert not (queue_root / ".lock").exists()
