"""
Tests for OrchestratorCLI — Unified CLI Integration Layer

Comprehensive test suite covering:
- Task completion handling and token recording
- Formatted output printing
- Budget checking and enforcement
- Callback invocation on budget thresholds
- Session summary printing
- Task blocking decisions
- Session lifecycle management
- Integration with all components
"""

import pytest
import os
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch, call
import yaml

from src.orchestration.monitoring.orchestrator_cli import OrchestratorCLI
from src.orchestration.monitoring.token_tracker import TokenTracker, TokenMetrics, TokenStats
from src.orchestration.monitoring.cli_formatter import CLIFormatter
from src.orchestration.monitoring.budget_checker import BudgetStatus, BudgetResult
from src.orchestration.monitoring.metrics import MetricsRegistry


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def metrics_registry():
    """Create a fresh MetricsRegistry for each test."""
    return MetricsRegistry()


@pytest.fixture
def token_tracker(metrics_registry):
    """Create a fresh TokenTracker for each test."""
    return TokenTracker(metrics_registry)


@pytest.fixture
def orchestrator_cli(token_tracker):
    """Create a fresh OrchestratorCLI for each test."""
    return OrchestratorCLI(token_tracker=token_tracker)


@pytest.fixture
def sample_delegate():
    """Create a sample DELEGATE block."""
    return {
        "task_id": "task-001",
        "role": "engineer",
        "model": "claude-haiku-4.5",
        "effort": "high",
    }


@pytest.fixture
def sample_handback():
    """Create a sample HANDBACK block."""
    return {
        "task_id": "task-001",
        "status": "complete",
        "tokens_in": 1000,
        "tokens_out": 500,
        "cached_tokens": 100,
        "cost_usd": 0.05,
    }


# ===========================================================================
# Initialization Tests
# ===========================================================================

class TestOrchestratorCLIInit:
    """Test OrchestratorCLI initialization."""
    
    def test_init_with_required_args(self, token_tracker):
        """Test initialization with only required arguments."""
        cli = OrchestratorCLI(token_tracker=token_tracker)
        
        assert cli.tracker is token_tracker
        assert isinstance(cli.formatter, CLIFormatter)
        assert cli.on_budget_exceeded is None
    
    def test_init_with_all_args(self, token_tracker):
        """Test initialization with all arguments."""
        callback = Mock()
        
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "budget.yaml"
            config_path.write_text("budget:\n  session_usd: 10.0\n")
            
            cli = OrchestratorCLI(
                token_tracker=token_tracker,
                budget_config_path=config_path,
                no_color=True,
                on_budget_exceeded=callback,
            )
            
            assert cli.tracker is token_tracker
            assert cli.formatter.no_color is True
            assert cli.on_budget_exceeded is callback
    
    def test_init_respects_no_color_flag(self, token_tracker):
        """Test that no_color flag is passed to formatter."""
        cli = OrchestratorCLI(token_tracker=token_tracker, no_color=True)
        
        assert cli.formatter.no_color is True


# ===========================================================================
# on_task_complete Tests
# ===========================================================================

class TestOnTaskComplete:
    """Test on_task_complete() method."""
    
    def test_on_task_complete_records_metrics(self, orchestrator_cli, sample_delegate, sample_handback):
        """Test that on_task_complete records metrics in tracker."""
        with patch('builtins.print'):
            orchestrator_cli.on_task_complete(sample_delegate, sample_handback)
        
        stats = orchestrator_cli.tracker.get_stats()
        
        assert stats.task_count == 1
        assert stats.total_input_tokens == 1000
        assert stats.total_output_tokens == 500
        assert stats.total_cached_tokens == 100
        assert stats.total_cost_usd == 0.05
    
    def test_on_task_complete_prints_formatted_line(self, orchestrator_cli, sample_delegate, sample_handback):
        """Test that on_task_complete prints formatted task line."""
        with patch('builtins.print') as mock_print:
            orchestrator_cli.on_task_complete(sample_delegate, sample_handback)
        
        # Should have called print at least once
        assert mock_print.called
        
        # Get the printed output
        printed_output = mock_print.call_args[0][0]
        
        # Should contain key elements
        assert "[tokens]" in printed_output
        assert "engineer" in printed_output
        assert "1,000 in" in printed_output
        assert "500 out" in printed_output
    
    def test_on_task_complete_checks_budget(self, orchestrator_cli, sample_delegate, sample_handback):
        """Test that on_task_complete checks budget after recording."""
        callback = Mock()
        orchestrator_cli.on_budget_exceeded = callback
        
        with patch('builtins.print'):
            orchestrator_cli.on_task_complete(sample_delegate, sample_handback)
        
        # Budget should be OK (5% of $5.00 budget), so callback not called
        assert not callback.called
    
    def test_on_task_complete_calls_callback_on_warning(self, token_tracker, sample_delegate):
        """Test that callback is called when budget reaches WARNING status."""
        callback = Mock()
        cli = OrchestratorCLI(token_tracker=token_tracker, on_budget_exceeded=callback)
        
        # Create handback that uses 75% of budget ($3.75)
        handback = {
            "task_id": "task-001",
            "status": "complete",
            "tokens_in": 5000,
            "tokens_out": 2500,
            "cached_tokens": 0,
            "cost_usd": 3.75,
        }
        
        with patch('builtins.print'):
            cli.on_task_complete(sample_delegate, handback)
        
        # Callback should have been called with WARNING status
        assert callback.called
        budget_result = callback.call_args[0][0]
        assert budget_result.status == BudgetStatus.WARNING
    
    def test_on_task_complete_calls_callback_on_critical(self, token_tracker, sample_delegate):
        """Test that callback is called when budget reaches CRITICAL status."""
        callback = Mock()
        cli = OrchestratorCLI(token_tracker=token_tracker, on_budget_exceeded=callback)
        
        # Create handback that uses 95% of budget ($4.75)
        handback = {
            "task_id": "task-001",
            "status": "complete",
            "tokens_in": 5000,
            "tokens_out": 2500,
            "cached_tokens": 0,
            "cost_usd": 4.75,
        }
        
        with patch('builtins.print'):
            cli.on_task_complete(sample_delegate, handback)
        
        # Callback should have been called with CRITICAL status
        assert callback.called
        budget_result = callback.call_args[0][0]
        assert budget_result.status == BudgetStatus.CRITICAL
    
    def test_on_task_complete_calls_callback_on_blocked(self, token_tracker, sample_delegate):
        """Test that callback is called when budget is BLOCKED."""
        callback = Mock()
        cli = OrchestratorCLI(token_tracker=token_tracker, on_budget_exceeded=callback)
        
        # Create handback that uses 110% of budget ($5.50)
        handback = {
            "task_id": "task-001",
            "status": "complete",
            "tokens_in": 5000,
            "tokens_out": 2500,
            "cached_tokens": 0,
            "cost_usd": 5.50,
        }
        
        with patch('builtins.print'):
            cli.on_task_complete(sample_delegate, handback)
        
        # Callback should have been called with BLOCKED status
        assert callback.called
        budget_result = callback.call_args[0][0]
        assert budget_result.status == BudgetStatus.BLOCKED
    
    def test_on_task_complete_prints_alert_without_callback(self, orchestrator_cli, sample_delegate):
        """Test that budget alert is printed when no callback provided."""
        # Create handback that uses 95% of budget
        handback = {
            "task_id": "task-001",
            "status": "complete",
            "tokens_in": 5000,
            "tokens_out": 2500,
            "cached_tokens": 0,
            "cost_usd": 4.75,
        }
        
        with patch('builtins.print') as mock_print:
            orchestrator_cli.on_task_complete(sample_delegate, handback)
        
        # Should have printed alert
        printed_outputs = [call[0][0] for call in mock_print.call_args_list]
        alert_printed = any("BUDGET ALERT" in str(output) for output in printed_outputs)
        assert alert_printed
    
    def test_on_task_complete_missing_task_id_raises_error(self, orchestrator_cli, sample_delegate):
        """Test that missing task_id in handback raises ValueError."""
        handback = {
            "status": "complete",
            "tokens_in": 1000,
            "tokens_out": 500,
            "cost_usd": 0.05,
        }
        
        with pytest.raises(ValueError, match="task_id"):
            orchestrator_cli.on_task_complete(sample_delegate, handback)
    
    def test_on_task_complete_uses_default_agent_name(self, orchestrator_cli):
        """Test that default agent name is used if role not in delegate."""
        delegate = {"task_id": "task-001"}  # No role
        handback = {
            "task_id": "task-001",
            "status": "complete",
            "tokens_in": 100,
            "tokens_out": 50,
            "cost_usd": 0.01,
        }
        
        with patch('builtins.print'):
            orchestrator_cli.on_task_complete(delegate, handback)
        
        stats = orchestrator_cli.tracker.get_stats()
        assert "unknown" in stats.agent_tokens
    
    def test_on_task_complete_handles_synthetic_handback(self, orchestrator_cli, sample_delegate):
        """Test that synthetic HANDBACK (with missing optional fields) is handled."""
        # Synthetic HANDBACK might not have all fields
        handback = {
            "task_id": "task-001",
            "status": "blocked",
        }
        
        with patch('builtins.print'):
            orchestrator_cli.on_task_complete(sample_delegate, handback)
        
        stats = orchestrator_cli.tracker.get_stats()
        assert stats.task_count == 1
        assert stats.total_cost_usd == 0.0


# ===========================================================================
# print_session_summary Tests
# ===========================================================================

class TestPrintSessionSummary:
    """Test print_session_summary() method."""
    
    def test_print_session_summary_shows_all_agents(self, orchestrator_cli, sample_delegate):
        """Test that session summary includes all agents."""
        # Record multiple tasks from different agents
        handback1 = {
            "task_id": "task-001",
            "status": "complete",
            "tokens_in": 1000,
            "tokens_out": 500,
            "cost_usd": 0.05,
        }
        delegate1 = {**sample_delegate, "role": "engineer"}
        
        handback2 = {
            "task_id": "task-002",
            "status": "complete",
            "tokens_in": 500,
            "tokens_out": 250,
            "cost_usd": 0.025,
        }
        delegate2 = {**sample_delegate, "task_id": "task-002", "role": "orchestrator"}
        
        with patch('builtins.print'):
            orchestrator_cli.on_task_complete(delegate1, handback1)
            orchestrator_cli.on_task_complete(delegate2, handback2)
        
        with patch('builtins.print') as mock_print:
            orchestrator_cli.print_session_summary()
        
        printed_output = "\n".join([str(call[0][0]) for call in mock_print.call_args_list])
        
        # Should contain header
        assert "Token Session Summary" in printed_output
        
        # Should contain both agents
        assert "engineer" in printed_output
        assert "orchestrator" in printed_output
    
    def test_print_session_summary_shows_task_count(self, orchestrator_cli, sample_delegate, sample_handback):
        """Test that session summary shows task count."""
        with patch('builtins.print'):
            orchestrator_cli.on_task_complete(sample_delegate, sample_handback)
        
        with patch('builtins.print') as mock_print:
            orchestrator_cli.print_session_summary()
        
        printed_output = "\n".join([str(call[0][0]) for call in mock_print.call_args_list])
        
        assert "Tasks:" in printed_output
        assert "1" in printed_output
    
    def test_print_session_summary_shows_total_cost(self, orchestrator_cli, sample_delegate, sample_handback):
        """Test that session summary shows total cost."""
        with patch('builtins.print'):
            orchestrator_cli.on_task_complete(sample_delegate, sample_handback)
        
        with patch('builtins.print') as mock_print:
            orchestrator_cli.print_session_summary()
        
        printed_output = "\n".join([str(call[0][0]) for call in mock_print.call_args_list])
        
        assert "Cost:" in printed_output
        assert "$0.05" in printed_output
    
    def test_print_session_summary_shows_budget_percentage(self, orchestrator_cli, sample_delegate, sample_handback):
        """Test that session summary shows budget percentage."""
        with patch('builtins.print'):
            orchestrator_cli.on_task_complete(sample_delegate, sample_handback)
        
        with patch('builtins.print') as mock_print:
            orchestrator_cli.print_session_summary()
        
        printed_output = "\n".join([str(call[0][0]) for call in mock_print.call_args_list])
        
        # Should show percentage of $5.00 budget
        assert "1.0%" in printed_output or "1%" in printed_output
    
    def test_print_session_summary_empty_session(self, orchestrator_cli):
        """Test that session summary works with empty session."""
        with patch('builtins.print') as mock_print:
            orchestrator_cli.print_session_summary()
        
        printed_output = "\n".join([str(call[0][0]) for call in mock_print.call_args_list])
        
        assert "Token Session Summary" in printed_output
        assert "Tasks:    0" in printed_output


# ===========================================================================
# should_block_new_tasks Tests
# ===========================================================================

class TestShouldBlockNewTasks:
    """Test should_block_new_tasks() method."""
    
    def test_should_block_returns_false_when_ok(self, orchestrator_cli, sample_delegate, sample_handback):
        """Test that should_block returns False when budget is OK."""
        with patch('builtins.print'):
            orchestrator_cli.on_task_complete(sample_delegate, sample_handback)
        
        assert orchestrator_cli.should_block_new_tasks() is False
    
    def test_should_block_returns_false_when_warning(self, token_tracker, sample_delegate):
        """Test that should_block returns False when budget is WARNING."""
        cli = OrchestratorCLI(token_tracker=token_tracker)
        
        handback = {
            "task_id": "task-001",
            "status": "complete",
            "tokens_in": 5000,
            "tokens_out": 2500,
            "cost_usd": 3.75,  # 75% of budget
        }
        
        with patch('builtins.print'):
            cli.on_task_complete(sample_delegate, handback)
        
        assert cli.should_block_new_tasks() is False
    
    def test_should_block_returns_false_when_critical(self, token_tracker, sample_delegate):
        """Test that should_block returns False when budget is CRITICAL."""
        cli = OrchestratorCLI(token_tracker=token_tracker)
        
        handback = {
            "task_id": "task-001",
            "status": "complete",
            "tokens_in": 5000,
            "tokens_out": 2500,
            "cost_usd": 4.75,  # 95% of budget
        }
        
        with patch('builtins.print'):
            cli.on_task_complete(sample_delegate, handback)
        
        assert cli.should_block_new_tasks() is False
    
    def test_should_block_returns_true_when_blocked(self, token_tracker, sample_delegate):
        """Test that should_block returns True when budget is BLOCKED."""
        cli = OrchestratorCLI(token_tracker=token_tracker)
        
        handback = {
            "task_id": "task-001",
            "status": "complete",
            "tokens_in": 5000,
            "tokens_out": 2500,
            "cost_usd": 5.50,  # 110% of budget
        }
        
        with patch('builtins.print'):
            cli.on_task_complete(sample_delegate, handback)
        
        assert cli.should_block_new_tasks() is True
    
    def test_should_block_empty_session(self, orchestrator_cli):
        """Test that should_block returns False for empty session."""
        assert orchestrator_cli.should_block_new_tasks() is False


# ===========================================================================
# reset_session Tests
# ===========================================================================

class TestResetSession:
    """Test reset_session() method."""
    
    def test_reset_session_clears_tracker(self, orchestrator_cli, sample_delegate, sample_handback):
        """Test that reset_session clears all metrics."""
        with patch('builtins.print'):
            orchestrator_cli.on_task_complete(sample_delegate, sample_handback)
        
        # Verify metrics were recorded
        stats_before = orchestrator_cli.tracker.get_stats()
        assert stats_before.task_count == 1
        
        # Reset
        orchestrator_cli.reset_session()
        
        # Verify metrics were cleared
        stats_after = orchestrator_cli.tracker.get_stats()
        assert stats_after.task_count == 0
        assert stats_after.total_cost_usd == 0.0


# ===========================================================================
# get_session_stats Tests
# ===========================================================================

class TestGetSessionStats:
    """Test get_session_stats() method."""
    
    def test_get_session_stats_returns_stats(self, orchestrator_cli, sample_delegate, sample_handback):
        """Test that get_session_stats returns TokenStats."""
        with patch('builtins.print'):
            orchestrator_cli.on_task_complete(sample_delegate, sample_handback)
        
        stats = orchestrator_cli.get_session_stats()
        
        assert isinstance(stats, TokenStats)
        assert stats.task_count == 1
        assert stats.total_cost_usd == 0.05


# ===========================================================================
# get_budget_status Tests
# ===========================================================================

class TestGetBudgetStatus:
    """Test get_budget_status() method."""
    
    def test_get_budget_status_returns_result(self, orchestrator_cli, sample_delegate, sample_handback):
        """Test that get_budget_status returns BudgetResult."""
        with patch('builtins.print'):
            orchestrator_cli.on_task_complete(sample_delegate, sample_handback)
        
        result = orchestrator_cli.get_budget_status()
        
        assert isinstance(result, BudgetResult)
        assert result.status == BudgetStatus.OK
        assert result.pct_used == 1.0


# ===========================================================================
# Integration Tests
# ===========================================================================

class TestIntegration:
    """Integration tests combining multiple features."""
    
    def test_full_session_workflow(self, token_tracker):
        """Test complete session workflow: init → tasks → summary."""
        callback = Mock()
        cli = OrchestratorCLI(
            token_tracker=token_tracker,
            on_budget_exceeded=callback,
        )
        
        # Record multiple tasks
        delegate1 = {"task_id": "task-001", "role": "engineer"}
        handback1 = {
            "task_id": "task-001",
            "status": "complete",
            "tokens_in": 1000,
            "tokens_out": 500,
            "cost_usd": 0.05,
        }
        
        delegate2 = {"task_id": "task-002", "role": "orchestrator"}
        handback2 = {
            "task_id": "task-002",
            "status": "complete",
            "tokens_in": 500,
            "tokens_out": 250,
            "cost_usd": 0.025,
        }
        
        with patch('builtins.print'):
            cli.on_task_complete(delegate1, handback1)
            cli.on_task_complete(delegate2, handback2)
        
        # Verify stats
        stats = cli.get_session_stats()
        assert stats.task_count == 2
        assert pytest.approx(stats.total_cost_usd, abs=0.001) == 0.075
        
        # Verify budget status
        budget_result = cli.get_budget_status()
        assert budget_result.status == BudgetStatus.OK
        
        # Print summary
        with patch('builtins.print'):
            cli.print_session_summary()
        
        # Reset for next session
        cli.reset_session()
        stats_after = cli.get_session_stats()
        assert stats_after.task_count == 0
    
    def test_budget_escalation_workflow(self, token_tracker):
        """Test budget escalation: OK → WARNING → CRITICAL → BLOCKED."""
        callback = Mock()
        cli = OrchestratorCLI(
            token_tracker=token_tracker,
            on_budget_exceeded=callback,
        )
        
        delegate = {"task_id": "task-001", "role": "engineer"}
        
        # Task 1: OK (1% of budget)
        with patch('builtins.print'):
            cli.on_task_complete(delegate, {
                "task_id": "task-001",
                "status": "complete",
                "tokens_in": 1000,
                "tokens_out": 500,
                "cost_usd": 0.05,
            })
        assert not callback.called
        
        # Task 2: WARNING (75% of budget total)
        with patch('builtins.print'):
            cli.on_task_complete({**delegate, "task_id": "task-002"}, {
                "task_id": "task-002",
                "status": "complete",
                "tokens_in": 5000,
                "tokens_out": 2500,
                "cost_usd": 3.70,
            })
        assert callback.called
        assert callback.call_args[0][0].status == BudgetStatus.WARNING
        
        # Reset callback
        callback.reset_mock()
        
        # Task 3: CRITICAL (95% of budget total)
        with patch('builtins.print'):
            cli.on_task_complete({**delegate, "task_id": "task-003"}, {
                "task_id": "task-003",
                "status": "complete",
                "tokens_in": 1000,
                "tokens_out": 500,
                "cost_usd": 0.95,  # Adjusted to reach 95% total
            })
        assert callback.called
        assert callback.call_args[0][0].status == BudgetStatus.CRITICAL
    
    def test_no_color_mode_integration(self, token_tracker):
        """Test that no_color flag is respected throughout."""
        cli = OrchestratorCLI(
            token_tracker=token_tracker,
            no_color=True,
        )
        
        delegate = {"task_id": "task-001", "role": "engineer"}
        handback = {
            "task_id": "task-001",
            "status": "complete",
            "tokens_in": 1000,
            "tokens_out": 500,
            "cost_usd": 0.05,
        }
        
        with patch('builtins.print') as mock_print:
            cli.on_task_complete(delegate, handback)
        
        # Check that printed output doesn't contain ANSI codes
        printed_output = str(mock_print.call_args[0][0])
        assert "\033[" not in printed_output
    
    def test_custom_budget_config(self, token_tracker):
        """Test that custom budget config is respected."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "budget.yaml"
            config_path.write_text("""
budget:
  session_usd: 10.0
  warn_pct: 50
  critical_pct: 75
  block_pct: 100
""")
            
            cli = OrchestratorCLI(
                token_tracker=token_tracker,
                budget_config_path=config_path,
            )
            
            # Cost of 6.0 should be WARNING (60% of 10.0 budget, warn at 50%)
            delegate = {"task_id": "task-001", "role": "engineer"}
            handback = {
                "task_id": "task-001",
                "status": "complete",
                "tokens_in": 5000,
                "tokens_out": 2500,
                "cost_usd": 6.0,
            }
            
            with patch('builtins.print'):
                cli.on_task_complete(delegate, handback)
            
            budget_result = cli.get_budget_status()
            assert budget_result.status == BudgetStatus.WARNING
            assert budget_result.budget_usd == 10.0
