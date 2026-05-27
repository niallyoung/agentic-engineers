"""
DEPRECATED: Tests for Stream 1: Orchestrator Queue Routing Updates (Phase 2)

⚠️ LEGACY TEST FILE - SKIPPED AS OF 2026-05-26
These tests validate the OLD queue path architecture with legacy fallback support.
As of 2026-05-26, legacy paths (~/.copilot/queue, ~/.claude/queue, artifacts/queue)
are NO LONGER SUPPORTED. The queue infrastructure has been centralized to:

  ~/.agentic-engineers/{session-id}/{harness}/queue/

See: tests/test_queue_path_centralization.py for new canonical path tests.

Legacy queue path logic removed in commit:
- refactor: centralize queue paths (all harnesses)
- Remove fallback to legacy paths from orchestrator.py (lines 469-515)

These tests are kept for historical reference only.

TESTS SKIPPED: All tests in this file require legacy path support which is now removed.
"""

import os
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.orchestration.agents.orchestrator import QueueManager, OrchestratorAgent

# Skip all tests in this module - legacy path tests no longer applicable
pytestmark = pytest.mark.skip(
    reason="Legacy queue path tests (pre-2026-05-26). Centralized paths now use ~/.agentic-engineers/ only. "
           "See tests/test_queue_path_centralization.py for canonical path tests."
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def tmp_queue():
    """Create temporary queue directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        queue_dir = Path(tmpdir) / "queue"
        session_id = "test-session-123"
        
        # Create directory structure
        (queue_dir / session_id / "incoming").mkdir(parents=True)
        (queue_dir / session_id / "processing").mkdir(parents=True)
        (queue_dir / session_id / "done").mkdir(parents=True)
        
        yield queue_dir, session_id


@pytest.fixture
def tmp_queue_manager(tmp_queue, monkeypatch):
    """Create QueueManager with temp queue (legacy paths)."""
    queue_dir, session_id = tmp_queue
    monkeypatch.setenv("COPILOT_SESSION_ID", session_id)
    monkeypatch.delenv("AGENTIC_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    
    manager = QueueManager(queue_dir=str(queue_dir))
    return manager, session_id


@pytest.fixture
def tmp_orchestrator(tmp_queue, monkeypatch):
    """Create OrchestratorAgent with temp queue (legacy paths)."""
    queue_dir, session_id = tmp_queue
    monkeypatch.setenv("COPILOT_SESSION_ID", session_id)
    monkeypatch.delenv("AGENTIC_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    
    agent = OrchestratorAgent(queue_dir=str(queue_dir), idle_timeout=1)
    return agent, session_id


# ============================================================================
# Tests for QueueManager
# ============================================================================

class TestQueueManagerHarnessStorage:
    """Test that QueueManager stores harness as instance variable."""
    
    def test_queue_manager_stores_harness(self, tmp_queue_manager):
        """Verify harness is stored as instance variable."""
        manager, session_id = tmp_queue_manager
        assert hasattr(manager, 'harness'), "QueueManager should have harness attribute"
        assert manager.harness is not None, "harness should not be None"
        assert isinstance(manager.harness, str), "harness should be a string"
    
    def test_queue_manager_harness_is_copilot_fallback(self, tmp_queue_manager):
        """Verify harness is set to 'copilot' when using legacy paths."""
        manager, session_id = tmp_queue_manager
        # When using legacy paths without AGENTIC_HARNESS, harness should be copilot
        assert manager.harness in ['copilot', 'claude', 'local'], f"Unexpected harness: {manager.harness}"
    
    def test_queue_manager_stores_session_id(self, tmp_queue_manager):
        """Verify session_id is stored."""
        manager, session_id = tmp_queue_manager
        assert hasattr(manager, 'session_id'), "QueueManager should have session_id attribute"
        assert manager.session_id is not None, "session_id should not be None"


class TestQueueManagerGetDelegatesDir:
    """Test get_delegates_dir() method."""
    
    def test_get_delegates_dir_returns_path(self, tmp_queue_manager):
        """Verify get_delegates_dir returns a Path object."""
        manager, _ = tmp_queue_manager
        delegates_dir = manager.get_delegates_dir()
        assert isinstance(delegates_dir, Path), "get_delegates_dir should return Path"
    
    def test_get_delegates_dir_creates_directory(self, tmp_queue_manager):
        """Verify delegates directory is created when _ensure_queue_structure is called."""
        manager, _ = tmp_queue_manager
        manager._ensure_queue_structure()
        
        delegates_dir = manager.get_delegates_dir()
        assert delegates_dir.exists(), f"Delegates directory should exist: {delegates_dir}"
    
    def test_get_delegates_dir_legacy_path_format(self, tmp_queue_manager):
        """Verify get_delegates_dir returns correct path for legacy structure."""
        manager, session_id = tmp_queue_manager
        delegates_dir = manager.get_delegates_dir()
        
        # For legacy paths, should be at a location accessible from queue
        assert "delegates" in str(delegates_dir), "Path should contain 'delegates'"
    
    def test_get_delegates_dir_idempotent(self, tmp_queue_manager):
        """Verify get_delegates_dir returns same path on multiple calls."""
        manager, _ = tmp_queue_manager
        path1 = manager.get_delegates_dir()
        path2 = manager.get_delegates_dir()
        
        assert path1 == path2, "get_delegates_dir should return same path"


class TestQueueManagerPathAccessors:
    """Test path accessor methods."""
    
    def test_incoming_queue_dir_exists(self, tmp_queue_manager):
        """Verify get_incoming_queue_dir returns existing directory."""
        manager, _ = tmp_queue_manager
        incoming_dir = manager.get_incoming_queue_dir()
        
        assert incoming_dir.exists(), f"Incoming dir should exist: {incoming_dir}"
        assert incoming_dir.is_dir(), "Incoming dir should be a directory"
    
    def test_processing_queue_dir_exists(self, tmp_queue_manager):
        """Verify get_processing_queue_dir returns existing directory."""
        manager, _ = tmp_queue_manager
        processing_dir = manager.get_processing_queue_dir()
        
        assert processing_dir.exists(), f"Processing dir should exist: {processing_dir}"
        assert processing_dir.is_dir(), "Processing dir should be a directory"
    
    def test_done_queue_dir_exists(self, tmp_queue_manager):
        """Verify get_done_queue_dir returns existing directory."""
        manager, _ = tmp_queue_manager
        done_dir = manager.get_done_queue_dir()
        
        assert done_dir.exists(), f"Done dir should exist: {done_dir}"
        assert done_dir.is_dir(), "Done dir should be a directory"


# ============================================================================
# Tests for OrchestratorAgent
# ============================================================================

class TestOrchestratorAgentHarnessExposure:
    """Test that OrchestratorAgent exposes harness and session_id."""
    
    def test_orchestrator_has_harness_attribute(self, tmp_orchestrator):
        """Verify OrchestratorAgent has harness attribute."""
        agent, session_id = tmp_orchestrator
        assert hasattr(agent, 'harness'), "OrchestratorAgent should have harness"
        assert agent.harness is not None, "harness should not be None"
    
    def test_orchestrator_has_session_id_attribute(self, tmp_orchestrator):
        """Verify OrchestratorAgent has session_id attribute."""
        agent, session_id = tmp_orchestrator
        assert hasattr(agent, 'session_id'), "OrchestratorAgent should have session_id"
        assert agent.session_id is not None, "session_id should not be None"
        assert agent.session_id == session_id, "session_id should match fixture"
    
    def test_orchestrator_harness_matches_queue_manager(self, tmp_orchestrator):
        """Verify OrchestratorAgent.harness matches queue_manager.harness."""
        agent, _ = tmp_orchestrator
        assert agent.harness == agent.queue_manager.harness, \
            "Harness should match queue_manager's harness"
    
    def test_orchestrator_session_id_matches_queue_manager(self, tmp_orchestrator):
        """Verify OrchestratorAgent.session_id matches queue_manager.session_id."""
        agent, _ = tmp_orchestrator
        assert agent.session_id == agent.queue_manager.session_id, \
            "session_id should match queue_manager's session_id"


class TestOrchestratorAgentPathAccessors:
    """Test OrchestratorAgent path accessor methods."""
    
    def test_orchestrator_get_incoming_queue_dir(self, tmp_orchestrator):
        """Verify OrchestratorAgent.get_incoming_queue_dir delegates correctly."""
        agent, _ = tmp_orchestrator
        incoming_dir = agent.get_incoming_queue_dir()
        
        assert isinstance(incoming_dir, Path), "Should return Path"
        assert incoming_dir == agent.queue_manager.get_incoming_queue_dir(), \
            "Should delegate to queue_manager"
    
    def test_orchestrator_get_processing_queue_dir(self, tmp_orchestrator):
        """Verify OrchestratorAgent.get_processing_queue_dir delegates correctly."""
        agent, _ = tmp_orchestrator
        processing_dir = agent.get_processing_queue_dir()
        
        assert isinstance(processing_dir, Path), "Should return Path"
        assert processing_dir == agent.queue_manager.get_processing_queue_dir(), \
            "Should delegate to queue_manager"
    
    def test_orchestrator_get_done_queue_dir(self, tmp_orchestrator):
        """Verify OrchestratorAgent.get_done_queue_dir delegates correctly."""
        agent, _ = tmp_orchestrator
        done_dir = agent.get_done_queue_dir()
        
        assert isinstance(done_dir, Path), "Should return Path"
        assert done_dir == agent.queue_manager.get_done_queue_dir(), \
            "Should delegate to queue_manager"
    
    def test_orchestrator_get_delegates_dir(self, tmp_orchestrator):
        """Verify OrchestratorAgent.get_delegates_dir delegates correctly."""
        agent, _ = tmp_orchestrator
        agent.queue_manager._ensure_queue_structure()  # Ensure delegates dir exists
        
        delegates_dir = agent.get_delegates_dir()
        
        assert isinstance(delegates_dir, Path), "Should return Path"
        assert delegates_dir == agent.queue_manager.get_delegates_dir(), \
            "Should delegate to queue_manager"


class TestOrchestratorAgentQueueRootHelper:
    """Test _get_queue_root helper method."""
    
    def test_get_queue_root_returns_path(self, tmp_orchestrator):
        """Verify _get_queue_root returns a Path."""
        agent, _ = tmp_orchestrator
        queue_root = agent._get_queue_root()
        
        assert isinstance(queue_root, Path), "Should return Path"
    
    def test_get_queue_root_default_uses_current(self, tmp_orchestrator):
        """Verify _get_queue_root uses current session_id and harness by default."""
        agent, session_id = tmp_orchestrator
        queue_root = agent._get_queue_root()
        
        # Should contain session_id in path
        assert session_id in str(queue_root), "Path should contain session_id"
    
    def test_get_queue_root_accepts_override(self, tmp_orchestrator):
        """Verify _get_queue_root accepts session_id and harness overrides."""
        agent, _ = tmp_orchestrator
        
        # This should work without error
        queue_root = agent._get_queue_root(session_id="test-123", harness="test-harness")
        
        assert isinstance(queue_root, Path), "Should return Path"
        assert "test-123" in str(queue_root), "Path should contain override session_id"


# ============================================================================
# Integration Tests
# ============================================================================

class TestBackwardCompatibility:
    """Test backward compatibility with legacy paths."""
    
    def test_legacy_queue_structure_still_works(self, tmp_queue_manager):
        """Verify legacy queue structure continues to work."""
        manager, session_id = tmp_queue_manager
        
        # Should be able to access all queue directories
        assert manager.get_incoming_queue_dir().exists()
        assert manager.get_processing_queue_dir().exists()
        assert manager.get_done_queue_dir().exists()
    
    def test_write_delegate_to_legacy_incoming(self, tmp_queue_manager):
        """Verify can write DELEGATE files to legacy incoming queue."""
        manager, session_id = tmp_queue_manager
        
        # Write a test DELEGATE
        delegate_data = {
            "handoff_type": "DELEGATE",
            "task_id": "test-task-001",
            "role": "engineer",
            "scope": "Test scope",
            "plan": ["Step 1", "Step 2"],
        }
        
        incoming_dir = manager.get_incoming_queue_dir()
        delegate_file = incoming_dir / "DELEGATE-test.yaml"
        
        with open(delegate_file, 'w') as f:
            yaml.dump(delegate_data, f)
        
        # Verify file was written
        assert delegate_file.exists()
        
        # Verify can read it back
        with open(delegate_file, 'r') as f:
            loaded = yaml.safe_load(f)
        
        assert loaded['task_id'] == "test-task-001"


class TestPathConsistency:
    """Test that paths are consistent across QueueManager and OrchestratorAgent."""
    
    def test_all_paths_accessible_from_agent(self, tmp_orchestrator):
        """Verify all queue paths are accessible from OrchestratorAgent."""
        agent, _ = tmp_orchestrator
        
        incoming = agent.get_incoming_queue_dir()
        processing = agent.get_processing_queue_dir()
        done = agent.get_done_queue_dir()
        delegates = agent.get_delegates_dir()
        
        # All should be under same session
        assert str(agent.session_id) in str(incoming)
        assert str(agent.session_id) in str(processing)
        assert str(agent.session_id) in str(done)
        assert str(agent.session_id) in str(delegates)
    
    def test_delegates_dir_created_on_ensure_structure(self, tmp_orchestrator):
        """Verify delegates directory is created by _ensure_queue_structure."""
        agent, _ = tmp_orchestrator
        agent.queue_manager._ensure_queue_structure()
        
        delegates_dir = agent.get_delegates_dir()
        assert delegates_dir.exists(), f"Delegates dir should be created: {delegates_dir}"


# ============================================================================
# Run tests
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
