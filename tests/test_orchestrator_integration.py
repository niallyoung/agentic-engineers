"""
Tests for OrchestratorAgent integration with TokenTracker and OrchestratorCLI.

Covers:
- Initialization of MetricsRegistry, TokenTracker, OrchestratorCLI
- _process_task() calls on_task_complete() after successful HANDBACK
- _process_task() skips synthetic HANDBACKs
- run_poll_cycle() returns token metrics
- poll_and_process() prints session summary
- Budget enforcement integration
- NO_COLOR mode
- End-to-end integration with real tracker
"""

import os
import time
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from io import StringIO

from src.orchestration.agents.orchestrator import OrchestratorAgent
from src.orchestration.monitoring.metrics import MetricsRegistry
from src.orchestration.monitoring.token_tracker import TokenTracker
from src.orchestration.monitoring.orchestrator_cli import OrchestratorCLI
from src.orchestration.monitoring.budget_checker import BudgetStatus, BudgetResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_queue(tmp_path):
    """Create a temporary queue directory with session-id structure."""
    # Provide a fake session-id via env var
    session_id = "test-session-0000-0000-000000000000"
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()
    (queue_dir / session_id / "incoming").mkdir(parents=True)
    (queue_dir / session_id / "processing").mkdir(parents=True)
    (queue_dir / session_id / "done").mkdir(parents=True)
    return queue_dir, session_id


@pytest.fixture
def orchestrator(tmp_queue, monkeypatch):
    """Create OrchestratorAgent with temp queue and mocked session-id."""
    queue_dir, session_id = tmp_queue
    monkeypatch.setenv("COPILOT_SESSION_ID", session_id)
    agent = OrchestratorAgent(
        queue_dir=str(queue_dir),
        idle_timeout=1,
    )
    return agent


def _write_delegate(queue_dir, session_id, filename, delegate_data):
    """Helper: write a DELEGATE yaml file to incoming queue."""
    path = queue_dir / session_id / "incoming" / filename
    with open(path, "w") as f:
        yaml.dump(delegate_data, f)
    return path


# ---------------------------------------------------------------------------
# Initialization tests
# ---------------------------------------------------------------------------

class TestOrchestratorInitialization:

    def test_orchestrator_initializes_metrics_registry(self, orchestrator):
        assert hasattr(orchestrator, "metrics_registry")
        assert isinstance(orchestrator.metrics_registry, MetricsRegistry)

    def test_orchestrator_initializes_token_tracker(self, orchestrator):
        assert hasattr(orchestrator, "token_tracker")
        assert isinstance(orchestrator.token_tracker, TokenTracker)

    def test_orchestrator_initializes_orchestrator_cli(self, orchestrator):
        assert hasattr(orchestrator, "orchestrator_cli")
        assert isinstance(orchestrator.orchestrator_cli, OrchestratorCLI)

    def test_token_tracker_uses_same_registry(self, orchestrator):
        """TokenTracker should be wired to the same MetricsRegistry."""
        assert orchestrator.token_tracker.registry is orchestrator.metrics_registry

    def test_orchestrator_cli_uses_same_token_tracker(self, orchestrator):
        """OrchestratorCLI should be wired to the same TokenTracker."""
        assert orchestrator.orchestrator_cli.tracker is orchestrator.token_tracker

    def test_no_color_mode_from_env(self, tmp_queue, monkeypatch):
        """NO_COLOR env var should enable no-color mode."""
        queue_dir, session_id = tmp_queue
        monkeypatch.setenv("COPILOT_SESSION_ID", session_id)
        monkeypatch.setenv("NO_COLOR", "1")
        agent = OrchestratorAgent(queue_dir=str(queue_dir))
        assert agent.orchestrator_cli.formatter.no_color is True

    def test_no_color_mode_explicit_false(self, tmp_queue, monkeypatch):
        """Explicit no_color=False should override env var."""
        queue_dir, session_id = tmp_queue
        monkeypatch.setenv("COPILOT_SESSION_ID", session_id)
        monkeypatch.delenv("NO_COLOR", raising=False)
        agent = OrchestratorAgent(queue_dir=str(queue_dir), no_color=False)
        assert agent.orchestrator_cli.formatter.no_color is False

    def test_budget_config_path_passed_to_cli(self, tmp_queue, monkeypatch, tmp_path):
        """Custom budget_config_path should be passed to OrchestratorCLI."""
        queue_dir, session_id = tmp_queue
        monkeypatch.setenv("COPILOT_SESSION_ID", session_id)
        budget_path = tmp_path / "my_budget.yaml"
        # BudgetChecker expects config nested under "budget" key
        budget_path.write_text("budget:\n  session_usd: 10.0\n")
        agent = OrchestratorAgent(
            queue_dir=str(queue_dir),
            budget_config_path=budget_path,
        )
        # BudgetChecker should have loaded the config
        assert agent.orchestrator_cli.budget_checker.budget_config.get("session_usd") == 10.0

    def test_handle_budget_exceeded_callback_wired(self, orchestrator):
        """OrchestratorCLI should have _handle_budget_exceeded as callback."""
        assert orchestrator.orchestrator_cli.on_budget_exceeded == orchestrator._handle_budget_exceeded


# ---------------------------------------------------------------------------
# _handle_budget_exceeded tests
# ---------------------------------------------------------------------------

class TestHandleBudgetExceeded:

    def test_handle_budget_exceeded_critical(self, orchestrator, caplog):
        import logging
        budget_result = BudgetResult(
            status=BudgetStatus.CRITICAL,
            message="Critical: 90% used",
            pct_used=90.0,
            remaining_usd=0.5,
            budget_usd=5.0,
        )
        with caplog.at_level(logging.WARNING):
            orchestrator._handle_budget_exceeded(budget_result)
        assert "CRITICAL" in caplog.text or "Critical" in caplog.text

    def test_handle_budget_exceeded_blocked(self, orchestrator, caplog):
        import logging
        budget_result = BudgetResult(
            status=BudgetStatus.BLOCKED,
            message="Blocked: budget exhausted",
            pct_used=100.0,
            remaining_usd=0.0,
            budget_usd=5.0,
        )
        with caplog.at_level(logging.ERROR):
            orchestrator._handle_budget_exceeded(budget_result)
        assert "BLOCKED" in caplog.text or "blocked" in caplog.text.lower()


# ---------------------------------------------------------------------------
# _process_task() integration tests
# ---------------------------------------------------------------------------

class TestProcessTaskTokenTracking:

    def _make_delegate(self, task_id="task-001"):
        return {
            "handoff_type": "DELEGATE",
            "task_id": task_id,
            "role": "engineer",
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "scope": "Test task",
            "plan": ["Step 1", "Step 2"],
        }

    def _make_handback(self, task_id="task-001"):
        return {
            "handoff_type": "HANDBACK",
            "task_id": task_id,
            "status": "complete",
            "quality_score": 92,
            "tokens_in": 1000,
            "tokens_out": 500,
            "cached_tokens": 100,
            "cost_usd": 0.045,
        }

    def test_process_task_calls_on_task_complete(self, orchestrator, tmp_queue):
        """on_task_complete() should be called after successful HANDBACK."""
        queue_dir, session_id = tmp_queue
        delegate = self._make_delegate()
        _write_delegate(queue_dir, session_id, "task-001.yaml", delegate)

        handback = self._make_handback()
        mock_cli = MagicMock()
        orchestrator.orchestrator_cli = mock_cli
        mock_cli.should_block_new_tasks.return_value = False

        # Mock agent execution to return our handback
        mock_agent = MagicMock()
        mock_agent.execute.return_value = handback
        orchestrator.task_router.route_task = MagicMock(return_value=("engineer", mock_agent))
        orchestrator.has_children = MagicMock(return_value=False)

        orchestrator._process_task("task-001.yaml")

        mock_cli.on_task_complete.assert_called_once()
        call_args = mock_cli.on_task_complete.call_args
        assert call_args[0][1].get("task_id") == "task-001"

    def test_process_task_skips_synthetic_handbacks(self, orchestrator, tmp_queue):
        """on_task_complete() should NOT be called for synthetic HANDBACKs."""
        queue_dir, session_id = tmp_queue
        delegate = self._make_delegate("task-002")
        _write_delegate(queue_dir, session_id, "task-002.yaml", delegate)

        handback = self._make_handback("task-002")
        handback["_synthetic"] = True

        mock_cli = MagicMock()
        orchestrator.orchestrator_cli = mock_cli
        mock_cli.should_block_new_tasks.return_value = False

        mock_agent = MagicMock()
        mock_agent.execute.return_value = handback
        orchestrator.task_router.route_task = MagicMock(return_value=("engineer", mock_agent))
        orchestrator.has_children = MagicMock(return_value=False)

        orchestrator._process_task("task-002.yaml")

        mock_cli.on_task_complete.assert_not_called()

    def test_process_task_checks_budget_after_completion(self, orchestrator, tmp_queue):
        """should_block_new_tasks() should be called after task completes."""
        queue_dir, session_id = tmp_queue
        delegate = self._make_delegate("task-003")
        _write_delegate(queue_dir, session_id, "task-003.yaml", delegate)

        handback = self._make_handback("task-003")

        mock_cli = MagicMock()
        orchestrator.orchestrator_cli = mock_cli
        mock_cli.should_block_new_tasks.return_value = False

        mock_agent = MagicMock()
        mock_agent.execute.return_value = handback
        orchestrator.task_router.route_task = MagicMock(return_value=("engineer", mock_agent))
        orchestrator.has_children = MagicMock(return_value=False)

        orchestrator._process_task("task-003.yaml")

        mock_cli.should_block_new_tasks.assert_called()


# ---------------------------------------------------------------------------
# run_poll_cycle() token metrics tests
# ---------------------------------------------------------------------------

class TestRunPollCycleTokenMetrics:

    def test_run_poll_cycle_returns_token_metrics_key(self, orchestrator):
        """run_poll_cycle() result must include 'tokens' key."""
        result = orchestrator.run_poll_cycle()
        assert "tokens" in result

    def test_run_poll_cycle_token_metrics_structure(self, orchestrator):
        """Token metrics dict must have input, output, cached, cost_usd keys."""
        result = orchestrator.run_poll_cycle()
        tokens = result["tokens"]
        assert "input" in tokens
        assert "output" in tokens
        assert "cached" in tokens
        assert "cost_usd" in tokens

    def test_run_poll_cycle_includes_cost_usd(self, orchestrator):
        """cost_usd should be 0.0 when no tasks processed."""
        result = orchestrator.run_poll_cycle()
        assert result["tokens"]["cost_usd"] == 0.0

    def test_run_poll_cycle_token_metrics_after_task(self, orchestrator, tmp_queue):
        """Token metrics should reflect actual task token usage."""
        queue_dir, session_id = tmp_queue
        delegate = {
            "handoff_type": "DELEGATE",
            "task_id": "task-tok-001",
            "role": "engineer",
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "scope": "Token test",
            "plan": ["Step 1"],
        }
        _write_delegate(queue_dir, session_id, "task-tok-001.yaml", delegate)

        handback = {
            "handoff_type": "HANDBACK",
            "task_id": "task-tok-001",
            "status": "complete",
            "quality_score": 90,
            "tokens_in": 2000,
            "tokens_out": 800,
            "cached_tokens": 200,
            "cost_usd": 0.09,
        }

        mock_agent = MagicMock()
        mock_agent.execute.return_value = handback
        orchestrator.task_router.route_task = MagicMock(return_value=("engineer", mock_agent))
        orchestrator.has_children = MagicMock(return_value=False)

        result = orchestrator.run_poll_cycle()

        assert result["tokens"]["input"] == 2000
        assert result["tokens"]["output"] == 800
        assert result["tokens"]["cached"] == 200
        assert abs(result["tokens"]["cost_usd"] - 0.09) < 0.001

    def test_run_poll_cycle_existing_metrics_preserved(self, orchestrator):
        """Standard result keys still present alongside tokens."""
        result = orchestrator.run_poll_cycle()
        assert "tasks_processed" in result
        assert "tasks_success" in result
        assert "tasks_escalated" in result
        assert "tasks_failed" in result


# ---------------------------------------------------------------------------
# poll_and_process() session summary tests
# ---------------------------------------------------------------------------

class TestPollAndProcessSessionSummary:

    def test_poll_and_process_prints_session_summary(self, orchestrator, capsys):
        """poll_and_process() should print session summary before exiting."""
        # With idle_timeout=1 and empty queue, it should exit quickly
        orchestrator.idle_timeout = 1
        orchestrator.last_task_time = time.time() - 2  # Already past idle timeout

        orchestrator.poll_and_process()

        captured = capsys.readouterr()
        # Should print separator lines and session summary
        assert "=" * 10 in captured.out  # At least some separator

    def test_poll_and_process_calls_print_session_summary(self, orchestrator):
        """print_session_summary() should be called exactly once."""
        orchestrator.idle_timeout = 1
        orchestrator.last_task_time = time.time() - 2

        mock_cli = MagicMock()
        orchestrator.orchestrator_cli = mock_cli

        orchestrator.poll_and_process()

        mock_cli.print_session_summary.assert_called_once()


# ---------------------------------------------------------------------------
# Budget enforcement tests
# ---------------------------------------------------------------------------

class TestBudgetEnforcement:

    def test_should_block_new_tasks_when_budget_ok(self, orchestrator):
        """should_block_new_tasks() returns False when budget is OK."""
        # No tasks recorded, budget should be fine
        assert orchestrator.orchestrator_cli.should_block_new_tasks() is False

    def test_should_block_new_tasks_when_budget_exceeded(self, orchestrator):
        """should_block_new_tasks() returns True when budget is exhausted."""
        # Record massive token usage to exceed budget
        orchestrator.token_tracker.record_task_tokens(
            task_id="big-task",
            agent="engineer",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            cached_tokens=0,
            cost_usd=1000.0,  # Way over any reasonable budget
        )
        assert orchestrator.orchestrator_cli.should_block_new_tasks() is True


# ---------------------------------------------------------------------------
# End-to-end integration test
# ---------------------------------------------------------------------------

class TestIntegrationEndToEnd:

    def test_integration_end_to_end_with_real_tracker(self, orchestrator, tmp_queue):
        """Full integration: task processed, tokens recorded, metrics returned."""
        queue_dir, session_id = tmp_queue

        delegate = {
            "handoff_type": "DELEGATE",
            "task_id": "e2e-task-001",
            "role": "engineer",
            "model": "claude-sonnet-4-6",
            "effort": "medium",
            "scope": "End-to-end integration test",
            "plan": ["Implement", "Test", "Review"],
        }
        _write_delegate(queue_dir, session_id, "e2e-task-001.yaml", delegate)

        handback = {
            "handoff_type": "HANDBACK",
            "task_id": "e2e-task-001",
            "status": "complete",
            "quality_score": 95,
            "tokens_in": 3000,
            "tokens_out": 1200,
            "cached_tokens": 300,
            "cost_usd": 0.12,
        }

        mock_agent = MagicMock()
        mock_agent.execute.return_value = handback
        orchestrator.task_router.route_task = MagicMock(return_value=("engineer", mock_agent))
        orchestrator.has_children = MagicMock(return_value=False)

        result = orchestrator.run_poll_cycle()

        # Verify task was processed
        assert result["tasks_processed"] == 1

        # Verify token metrics are correct
        assert result["tokens"]["input"] == 3000
        assert result["tokens"]["output"] == 1200
        assert result["tokens"]["cached"] == 300
        assert abs(result["tokens"]["cost_usd"] - 0.12) < 0.001

        # Verify tracker state
        stats = orchestrator.token_tracker.get_stats()
        assert stats.task_count == 1
        assert stats.total_input_tokens == 3000
        assert stats.total_output_tokens == 1200
        assert stats.total_cached_tokens == 300
        assert abs(stats.total_cost_usd - 0.12) < 0.001

    def test_multiple_tasks_accumulate_tokens(self, orchestrator, tmp_queue):
        """Token metrics should accumulate across multiple tasks in a cycle."""
        queue_dir, session_id = tmp_queue

        for i in range(3):
            delegate = {
                "handoff_type": "DELEGATE",
                "task_id": f"multi-task-{i:03d}",
                "role": "engineer",
                "model": "claude-sonnet-4-6",
                "effort": "low",
                "scope": f"Task {i}",
                "plan": ["Do it"],
            }
            _write_delegate(queue_dir, session_id, f"multi-task-{i:03d}.yaml", delegate)

        def make_handback(task_id):
            return {
                "handoff_type": "HANDBACK",
                "task_id": task_id,
                "status": "complete",
                "quality_score": 90,
                "tokens_in": 1000,
                "tokens_out": 400,
                "cached_tokens": 0,
                "cost_usd": 0.03,
            }

        call_count = [0]

        def route_side_effect(delegate_data):
            task_id = delegate_data.get("task_id", "unknown")
            mock_agent = MagicMock()
            mock_agent.execute.return_value = make_handback(task_id)
            return ("engineer", mock_agent)

        orchestrator.task_router.route_task = MagicMock(side_effect=route_side_effect)
        orchestrator.has_children = MagicMock(return_value=False)

        result = orchestrator.run_poll_cycle()

        assert result["tasks_processed"] == 3
        assert result["tokens"]["input"] == 3000
        assert result["tokens"]["output"] == 1200
        assert abs(result["tokens"]["cost_usd"] - 0.09) < 0.001
