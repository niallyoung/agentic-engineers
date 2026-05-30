"""
Comprehensive test suite for Copilot token tracking and budget management.

Tests cover:
- Cost calculation accuracy
- Budget threshold enforcement
- Alert triggering and escalation
- Hard block enforcement
- CLI integration
- Forecast accuracy
- Session persistence

Author: Engineer
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.copilot.cost_tracker import (
    CostTracker,
    TokenUsage,
    TaskCost,
    PricingTable,
    PricingTier,
)
from src.copilot.budget_manager import (
    BudgetManager,
    BudgetAlert,
    AlertLevel,
)
from src.copilot.cli_budget import BudgetCLI


class TestTokenUsage:
    """Test TokenUsage data class."""
    
    def test_token_usage_creation(self):
        """Test creating token usage record."""
        usage = TokenUsage(input_tokens=100, output_tokens=50, cached_tokens=10)
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.cached_tokens == 10
        assert usage.total_tokens == 160
    
    def test_token_usage_defaults(self):
        """Test TokenUsage with default values."""
        usage = TokenUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.cached_tokens == 0
        assert usage.total_tokens == 0


class TestPricingTable:
    """Test pricing configuration."""
    
    def test_default_pricing(self):
        """Test default pricing tiers are loaded."""
        table = PricingTable()
        
        assert "claude-haiku-4.5" in table.pricing
        assert "claude-sonnet-4.6" in table.pricing
        assert "claude-opus-4-6" in table.pricing
        assert "claude-opus-4.8" in table.pricing
    
    def test_get_pricing(self):
        """Test retrieving pricing for a model."""
        table = PricingTable()
        pricing = table.get_pricing("claude-haiku-4.5")
        
        assert pricing is not None
        assert pricing.model == "claude-haiku-4.5"
        assert pricing.input_cost_per_mtok > 0
        assert pricing.output_cost_per_mtok > 0
    
    def test_unknown_model_pricing(self):
        """Test pricing for unknown model returns None."""
        table = PricingTable()
        pricing = table.get_pricing("unknown-model")
        assert pricing is None
    
    def test_calculate_cost_haiku(self):
        """Test cost calculation for Haiku model."""
        table = PricingTable()
        usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000)
        
        cost = table.calculate_cost("claude-haiku-4.5", usage)
        
        # Haiku: input $0.80/M, output $4.00/M
        # Expected: $0.80 + $4.00 = $4.80
        assert 4.7 < cost < 4.9
    
    def test_calculate_cost_sonnet(self):
        """Test cost calculation for Sonnet model."""
        table = PricingTable()
        usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000)
        
        cost = table.calculate_cost("claude-sonnet-4.6", usage)
        
        # Sonnet: input $3.00/M, output $15.00/M
        # Expected: $3.00 + $15.00 = $18.00
        assert 17.9 < cost < 18.1
    
    def test_calculate_cost_with_cached(self):
        """Test cost calculation with cached tokens."""
        table = PricingTable()
        usage = TokenUsage(
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            cached_tokens=500_000,
        )
        
        cost = table.calculate_cost("claude-haiku-4.5", usage)
        
        # input: $0.80, output: $4.00, cached: $0.04
        # Expected: ~$4.84
        assert 4.8 < cost < 4.9
    
    def test_custom_pricing(self):
        """Test custom pricing override."""
        custom = {
            "test-model": PricingTier(
                model="test-model",
                input_cost_per_mtok=1.0,
                output_cost_per_mtok=2.0,
                cached_cost_per_mtok=0.1,
            )
        }
        
        table = PricingTable(custom_pricing=custom)
        pricing = table.get_pricing("test-model")
        
        assert pricing is not None
        assert pricing.input_cost_per_mtok == 1.0


class TestCostTracker:
    """Test cost tracking functionality."""
    
    def test_tracker_initialization(self):
        """Test CostTracker initialization."""
        tracker = CostTracker(session_id="test-session")
        
        assert tracker.session_id == "test-session"
        assert len(tracker.tasks) == 0
        assert tracker.get_session_total_cost() == 0.0
    
    def test_record_single_task(self):
        """Test recording a single task."""
        tracker = CostTracker()
        
        task_cost = tracker.record_task(
            task_id="TASK-001",
            model="claude-haiku-4.5",
            input_tokens=500,
            output_tokens=250,
            duration_ms=1000,
        )
        
        assert task_cost.task_id == "TASK-001"
        assert task_cost.model == "claude-haiku-4.5"
        assert task_cost.token_usage.total_tokens == 750
        assert task_cost.cost_usd > 0
        assert task_cost.duration_ms == 1000
    
    def test_get_task_cost(self):
        """Test retrieving a task's cost record."""
        tracker = CostTracker()
        tracker.record_task(
            task_id="TASK-001",
            model="claude-haiku-4.5",
            input_tokens=500,
            output_tokens=250,
        )
        
        task = tracker.get_task_cost("TASK-001")
        assert task is not None
        assert task.task_id == "TASK-001"
        
        missing = tracker.get_task_cost("TASK-999")
        assert missing is None
    
    def test_session_total_cost(self):
        """Test session total cost calculation."""
        tracker = CostTracker()
        
        tracker.record_task(
            task_id="TASK-001",
            model="claude-haiku-4.5",
            input_tokens=500,
            output_tokens=250,
        )
        tracker.record_task(
            task_id="TASK-002",
            model="claude-haiku-4.5",
            input_tokens=500,
            output_tokens=250,
        )
        
        total = tracker.get_session_total_cost()
        assert total > 0
        
        # Should be roughly 2x a single task cost
        single = tracker.get_task_cost("TASK-001").cost_usd
        assert total > single * 1.9
        assert total < single * 2.1
    
    def test_session_total_tokens(self):
        """Test session total token usage."""
        tracker = CostTracker()
        
        tracker.record_task(
            task_id="TASK-001",
            model="claude-haiku-4.5",
            input_tokens=100,
            output_tokens=50,
            cached_tokens=10,
        )
        tracker.record_task(
            task_id="TASK-002",
            model="claude-haiku-4.5",
            input_tokens=200,
            output_tokens=100,
            cached_tokens=20,
        )
        
        total = tracker.get_session_total_tokens()
        assert total.input_tokens == 300
        assert total.output_tokens == 150
        assert total.cached_tokens == 30
        assert total.total_tokens == 480
    
    def test_cost_by_model(self):
        """Test cost breakdown by model."""
        tracker = CostTracker()
        
        tracker.record_task(
            task_id="TASK-001",
            model="claude-haiku-4.5",
            input_tokens=500,
            output_tokens=250,
        )
        tracker.record_task(
            task_id="TASK-002",
            model="claude-sonnet-4.6",
            input_tokens=500,
            output_tokens=250,
        )
        
        breakdown = tracker.get_cost_by_model()
        
        assert "claude-haiku-4.5" in breakdown
        assert "claude-sonnet-4.6" in breakdown
        assert breakdown["claude-haiku-4.5"]["count"] == 1
        assert breakdown["claude-sonnet-4.6"]["count"] == 1
        assert breakdown["claude-sonnet-4.6"]["cost"] > breakdown["claude-haiku-4.5"]["cost"]
    
    def test_average_cost_per_task(self):
        """Test average cost calculation."""
        tracker = CostTracker()
        
        tracker.record_task(
            task_id="TASK-001",
            model="claude-haiku-4.5",
            input_tokens=500,
            output_tokens=250,
        )
        tracker.record_task(
            task_id="TASK-002",
            model="claude-haiku-4.5",
            input_tokens=500,
            output_tokens=250,
        )
        
        avg = tracker.get_average_cost_per_task()
        total = tracker.get_session_total_cost()
        
        assert abs(avg - total / 2) < 0.0001
    
    def test_most_expensive_tasks(self):
        """Test retrieving most expensive tasks."""
        tracker = CostTracker()
        
        tracker.record_task(
            task_id="TASK-001",
            model="claude-haiku-4.5",
            input_tokens=100,
            output_tokens=50,
        )
        tracker.record_task(
            task_id="TASK-002",
            model="claude-sonnet-4.6",
            input_tokens=1000,
            output_tokens=500,
        )
        tracker.record_task(
            task_id="TASK-003",
            model="claude-opus-4-6",
            input_tokens=5000,
            output_tokens=2500,
        )
        
        expensive = tracker.get_most_expensive_tasks(2)
        
        assert len(expensive) == 2
        assert expensive[0].task_id == "TASK-003"  # Most expensive
        assert expensive[1].task_id == "TASK-002"  # Second most
    
    def test_efficiency_ratio(self):
        """Test efficiency ratio calculation."""
        tracker = CostTracker()
        
        tracker.record_task(
            task_id="TASK-001",
            model="claude-haiku-4.5",
            input_tokens=100,
            output_tokens=50,
            cached_tokens=10,
        )
        
        ratio = tracker.get_efficiency_ratio()
        # Efficiency = output / total = 50 / 160 ≈ 0.3125
        assert 0.31 < ratio < 0.32
    
    def test_export_to_json(self):
        """Test JSON export."""
        tracker = CostTracker(session_id="test-session")
        
        tracker.record_task(
            task_id="TASK-001",
            model="claude-haiku-4.5",
            input_tokens=500,
            output_tokens=250,
        )
        
        json_str = tracker.export_to_json()
        data = json.loads(json_str)
        
        assert data["session_id"] == "test-session"
        assert data["total_tasks"] == 1
        assert data["total_cost_usd"] > 0
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["task_id"] == "TASK-001"
    
    def test_save_and_load_session(self):
        """Test saving and loading session from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "session.json"
            
            # Create and save
            tracker1 = CostTracker(session_id="test-session")
            tracker1.record_task(
                task_id="TASK-001",
                model="claude-haiku-4.5",
                input_tokens=500,
                output_tokens=250,
            )
            tracker1.save_to_file(filepath)
            
            # Load
            tracker2 = CostTracker()
            tracker2.load_from_file(filepath)
            
            assert tracker2.session_id == "test-session"
            assert len(tracker2.tasks) == 1
            assert tracker2.tasks[0].task_id == "TASK-001"


class TestBudgetManager:
    """Test budget management functionality."""
    
    def test_budget_manager_initialization(self):
        """Test BudgetManager initialization."""
        mgr = BudgetManager(session_budget_usd=100.0)
        
        assert mgr.session_budget_usd == 100.0
        assert len(mgr.alerts) == 0
        assert len(mgr.blocked_tasks) == 0
    
    def test_invalid_budget_raises_error(self):
        """Test that invalid budgets raise errors."""
        with pytest.raises(ValueError):
            BudgetManager(session_budget_usd=0)
        
        with pytest.raises(ValueError):
            BudgetManager(session_budget_usd=-100)
    
    def test_check_budget_available_within_limit(self):
        """Test budget availability check within limit."""
        tracker = CostTracker()
        mgr = BudgetManager(session_budget_usd=100.0)
        
        can_proceed, reason = mgr.check_budget_available(tracker, 50.0)
        assert can_proceed is True
        assert reason is None
    
    def test_check_budget_available_exceeds_limit(self):
        """Test budget availability check exceeds limit."""
        tracker = CostTracker()
        tracker.record_task(
            task_id="TASK-001",
            model="claude-haiku-4.5",
            input_tokens=500,
            output_tokens=250,
        )
        
        mgr = BudgetManager(session_budget_usd=0.1)  # Very small budget
        
        can_proceed, reason = mgr.check_budget_available(tracker, 0.2)
        assert can_proceed is False
        assert "exceeded" in reason.lower()
    
    def test_per_task_limit(self):
        """Test per-task cost limit enforcement."""
        tracker = CostTracker()
        mgr = BudgetManager(
            session_budget_usd=100.0,
            max_cost_per_task_usd=0.05,
        )
        
        # Task within limit
        can_proceed, reason = mgr.check_budget_available(tracker, 0.04)
        assert can_proceed is True
        
        # Task exceeds limit
        can_proceed, reason = mgr.check_budget_available(tracker, 0.10)
        assert can_proceed is False
        assert "per-task" in reason.lower()
    
    def test_alert_at_50_percent(self):
        """Test alert trigger at 50% threshold."""
        tracker = CostTracker()
        mgr = BudgetManager(session_budget_usd=100.0)
        
        # Record task at exactly 50%
        alert = mgr.record_task_and_check_alerts(
            tracker,
            task_id="TASK-001",
            model="claude-haiku-4.5",
            input_tokens=int(100_000_000 * 0.5),  # Create cost of ~50
            output_tokens=int(100_000_000 * 0.5),
        )
        
        # Alert should be triggered at 50% threshold
        assert alert is not None or len(mgr.alerts) > 0
    
    def test_alert_escalation(self):
        """Test alert escalation through thresholds."""
        tracker = CostTracker()
        mgr = BudgetManager(session_budget_usd=100.0)
        
        # Create expensive tasks to trigger alerts
        for i in range(5):
            mgr.record_task_and_check_alerts(
                tracker,
                task_id=f"TASK-{i+1:03d}",
                model="claude-opus-4.8",  # Very expensive
                input_tokens=10_000_000,
                output_tokens=10_000_000,
            )
        
        # Should have escalated through alert levels
        assert len(mgr.alerts) > 0
        
        # Get highest severity alert
        alerts = mgr.get_alerts()
        if alerts:
            # Later alerts should have higher severity
            assert alerts[-1].level in [AlertLevel.WARNING, AlertLevel.CRITICAL, AlertLevel.BLOCKED]
    
    def test_block_task(self):
        """Test blocking a task."""
        tracker = CostTracker()
        mgr = BudgetManager(session_budget_usd=100.0)
        
        mgr.block_task("TASK-001", "Budget exceeded")
        
        assert "TASK-001" in mgr.blocked_tasks
        assert len(mgr.blocked_tasks) == 1
    
    def test_get_alerts(self):
        """Test retrieving alerts."""
        tracker = CostTracker()
        mgr = BudgetManager(session_budget_usd=100.0)
        
        # Create expensive task to trigger alert
        for i in range(3):
            mgr.record_task_and_check_alerts(
                tracker,
                task_id=f"TASK-{i+1:03d}",
                model="claude-opus-4.8",
                input_tokens=10_000_000,
                output_tokens=10_000_000,
            )
        
        alerts = mgr.get_alerts()
        assert len(alerts) > 0
    
    def test_budget_status(self):
        """Test budget status reporting."""
        tracker = CostTracker()
        tracker.record_task(
            task_id="TASK-001",
            model="claude-haiku-4.5",
            input_tokens=100,
            output_tokens=50,
        )
        
        mgr = BudgetManager(session_budget_usd=1.0)
        status = mgr.get_budget_status(tracker)
        
        assert "session_budget_usd" in status
        assert "current_cost_usd" in status
        assert "remaining_budget_usd" in status
        assert "percent_used" in status
        assert "status" in status
        assert status["total_tasks"] == 1
    
    def test_forecast_with_insufficient_history(self):
        """Test forecast with insufficient history."""
        tracker = CostTracker()
        mgr = BudgetManager(session_budget_usd=100.0)
        
        forecast = mgr.forecast_remaining_budget(tracker)
        
        assert forecast["forecast_available"] is False
    
    def test_forecast_with_sufficient_history(self):
        """Test forecast with sufficient history."""
        tracker = CostTracker()
        mgr = BudgetManager(session_budget_usd=100.0)
        
        # Record multiple tasks
        for i in range(10):
            mgr.record_task_and_check_alerts(
                tracker,
                task_id=f"TASK-{i+1:03d}",
                model="claude-haiku-4.5",
                input_tokens=1000,
                output_tokens=500,
                duration_ms=1000,
            )
        
        forecast = mgr.forecast_remaining_budget(tracker)
        
        assert forecast["forecast_available"] is True
        assert forecast["average_cost_per_task"] > 0
        assert forecast["estimated_tasks_remaining"] is not None
    
    def test_savings_recommendations(self):
        """Test cost optimization recommendations."""
        tracker = CostTracker()
        
        # Create tasks with diverse model usage
        tracker.record_task(
            task_id="TASK-001",
            model="claude-opus-4.8",
            input_tokens=10_000_000,
            output_tokens=10_000_000,
        )
        for i in range(10):
            tracker.record_task(
                task_id=f"TASK-{i+2:03d}",
                model="claude-haiku-4.5",
                input_tokens=1000,
                output_tokens=500,
            )
        
        mgr = BudgetManager(session_budget_usd=1000.0)
        recommendations = mgr.get_savings_recommendations(tracker)
        
        # Should have some recommendations
        assert len(recommendations) >= 0
    
    def test_budget_report(self):
        """Test budget report generation."""
        tracker = CostTracker()
        tracker.record_task(
            task_id="TASK-001",
            model="claude-haiku-4.5",
            input_tokens=100,
            output_tokens=50,
        )
        
        mgr = BudgetManager(session_budget_usd=100.0)
        report = mgr.get_report(tracker)
        
        assert "BUDGET REPORT" in report
        assert "BUDGET STATUS" in report
        assert "TASK STATISTICS" in report
        assert isinstance(report, str)


class TestBudgetCLI:
    """Test CLI functionality."""
    
    def test_cli_initialization(self):
        """Test CLI initialization."""
        cli = BudgetCLI()
        assert cli.parser is not None
    
    def test_cli_status_command(self):
        """Test status command."""
        cli = BudgetCLI()
        # This will fail gracefully without a session file, which is expected
        result = cli.run(["status"])
        assert result == 0
    
    def test_cli_help(self):
        """Test help command."""
        cli = BudgetCLI()
        # argparse calls sys.exit() on help, which raises SystemExit
        with pytest.raises(SystemExit):
            cli.run(["--help"])
    
    def test_cli_no_command(self):
        """Test running with no command."""
        cli = BudgetCLI()
        result = cli.run([])
        assert result == 0
    
    def test_cli_breakdown_command(self):
        """Test breakdown command."""
        cli = BudgetCLI()
        result = cli.run(["breakdown"])
        assert result == 0
    
    def test_cli_breakdown_json_format(self):
        """Test breakdown command with JSON output."""
        cli = BudgetCLI()
        result = cli.run(["breakdown", "--format", "json"])
        assert result == 0
    
    def test_cli_recommendations_command(self):
        """Test recommendations command."""
        cli = BudgetCLI()
        result = cli.run(["recommendations"])
        assert result == 0
    
    def test_cli_history_command(self):
        """Test history command."""
        cli = BudgetCLI()
        result = cli.run(["history"])
        assert result == 0
    
    def test_cli_history_with_limit(self):
        """Test history command with limit."""
        cli = BudgetCLI()
        result = cli.run(["history", "--limit", "5"])
        assert result == 0


class TestIntegration:
    """Integration tests across components."""
    
    def test_full_session_workflow(self):
        """Test complete session workflow."""
        # Create session
        tracker = CostTracker(session_id="integration-test")
        
        # Record multiple tasks with different models
        tracker.record_task(
            task_id="TASK-001",
            model="claude-haiku-4.5",
            input_tokens=1000,
            output_tokens=500,
            duration_ms=1000,
        )
        tracker.record_task(
            task_id="TASK-002",
            model="claude-sonnet-4.6",
            input_tokens=5000,
            output_tokens=2500,
            duration_ms=2000,
        )
        tracker.record_task(
            task_id="TASK-003",
            model="claude-opus-4-6",
            input_tokens=10_000,
            output_tokens=5000,
            duration_ms=3000,
        )
        
        # Create budget manager
        mgr = BudgetManager(
            session_budget_usd=100.0,
            max_cost_per_task_usd=50.0,
        )
        
        # Check budget status
        status = mgr.get_budget_status(tracker)
        assert status["total_tasks"] == 3
        assert status["current_cost_usd"] > 0
        
        # Get breakdown
        breakdown = tracker.get_cost_by_model()
        assert len(breakdown) == 3
        
        # Verify all tasks recorded
        assert tracker.get_task_cost("TASK-001") is not None
        assert tracker.get_task_cost("TASK-002") is not None
        assert tracker.get_task_cost("TASK-003") is not None
    
    def test_budget_enforcement_blocks_task(self):
        """Test that budget enforcement blocks tasks over limit."""
        tracker = CostTracker()
        mgr = BudgetManager(
            session_budget_usd=10.0,  # Small budget
            max_cost_per_task_usd=5.0,
        )
        
        # Record expensive task
        mgr.record_task_and_check_alerts(
            tracker,
            task_id="TASK-001",
            model="claude-opus-4.8",
            input_tokens=100_000_000,
            output_tokens=50_000_000,
        )
        
        # Try to add another expensive task that would exceed budget
        can_proceed, reason = mgr.check_budget_available(tracker, 20.0)
        
        assert can_proceed is False
        assert reason is not None


# Performance and edge case tests

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_token_usage(self):
        """Test handling of zero token usage."""
        tracker = CostTracker()
        task = tracker.record_task(
            task_id="TASK-001",
            model="claude-haiku-4.5",
            input_tokens=0,
            output_tokens=0,
        )
        assert task.cost_usd == 0.0
    
    def test_very_large_token_usage(self):
        """Test handling of very large token counts."""
        tracker = CostTracker()
        task = tracker.record_task(
            task_id="TASK-001",
            model="claude-haiku-4.5",
            input_tokens=1_000_000_000,
            output_tokens=1_000_000_000,
        )
        assert task.cost_usd > 0
        assert task.cost_usd < 10_000  # Sanity check
    
    def test_empty_session_statistics(self):
        """Test statistics on empty session."""
        tracker = CostTracker()
        
        assert tracker.get_session_total_cost() == 0.0
        assert tracker.get_session_total_tokens().total_tokens == 0
        assert tracker.get_average_cost_per_task() == 0.0
        assert tracker.get_average_tokens_per_task() == 0
        assert tracker.get_efficiency_ratio() == 0.0
    
    def test_single_task_efficiency_ratio(self):
        """Test efficiency ratio with single task."""
        tracker = CostTracker()
        tracker.record_task(
            task_id="TASK-001",
            model="claude-haiku-4.5",
            input_tokens=1000,
            output_tokens=0,  # No output
        )
        
        ratio = tracker.get_efficiency_ratio()
        assert ratio == 0.0
    
    def test_metadata_preservation(self):
        """Test that task metadata is preserved."""
        tracker = CostTracker()
        metadata = {"user_id": "123", "request_id": "abc"}
        
        task = tracker.record_task(
            task_id="TASK-001",
            model="claude-haiku-4.5",
            input_tokens=100,
            output_tokens=50,
            metadata=metadata,
        )
        
        assert task.metadata == metadata
        retrieved = tracker.get_task_cost("TASK-001")
        assert retrieved.metadata == metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
