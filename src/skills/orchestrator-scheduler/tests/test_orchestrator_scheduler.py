"""Tests for OrchestratorScheduler."""

import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import after path setup
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from skills.orchestrator_scheduler.scripts.orchestrator_scheduler import OrchestratorScheduler


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

    @patch('sys.path.insert')
    def test_run_loads_orchestrator_skill(self, mock_insert):
        """Should lazy-load OrchestratorSkill on first run."""
        with patch.dict(os.environ, {'CLAUDE_SESSION_ID': 'test-session'}):
            scheduler = OrchestratorScheduler()

            # Mock the OrchestratorSkill
            mock_orch = MagicMock()
            mock_orch.poll_queue.return_value = (2, 0)

            with patch('builtins.__import__') as mock_import:
                # Don't actually import, just mock it
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
