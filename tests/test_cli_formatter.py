"""
Tests for CLIFormatter — ANSI-colored token metrics display.

Comprehensive test suite covering:
- Compact task line formatting
- Session summary formatting
- ANSI color application
- NO_COLOR environment variable handling
- Budget percentage color coding
"""

import os
import pytest
from datetime import datetime
from src.orchestration.monitoring.token_tracker import TokenMetrics, TokenStats
from src.orchestration.monitoring.cli_formatter import CLIFormatter


# ===========================================================================
# Compact Task Line Tests
# ===========================================================================

class TestCompactTaskLine:
    """Test format_task_line() output."""
    
    def test_compact_line_format_correct(self):
        """Test that compact line has correct format and values."""
        metrics = TokenMetrics(
            task_id="task-001",
            agent="engineer",
            input_tokens=1234,
            output_tokens=567,
            cached_tokens=0,
            cost_usd=0.0045,
        )
        
        formatter = CLIFormatter()
        line = formatter.format_task_line(metrics, session_cost=0.12)
        
        # Should contain all key elements
        assert "[tokens]" in line
        assert "engineer" in line
        assert "1,234 in" in line
        assert "567 out" in line
        assert "$0.0045" in line
        assert "session: $0.12" in line
    
    def test_compact_line_with_zero_cost(self):
        """Test compact line with zero cost."""
        metrics = TokenMetrics(
            task_id="task-002",
            agent="orchestrator",
            input_tokens=100,
            output_tokens=50,
            cached_tokens=10,
            cost_usd=0.0,
        )
        
        formatter = CLIFormatter()
        line = formatter.format_task_line(metrics, session_cost=0.0)
        
        assert "orchestrator" in line
        assert "100 in" in line
        assert "50 out" in line
        assert "$0.0000" in line
    
    def test_compact_line_with_large_numbers(self):
        """Test compact line with large token counts."""
        metrics = TokenMetrics(
            task_id="task-003",
            agent="quality-engineer",
            input_tokens=50000,
            output_tokens=25000,
            cached_tokens=5000,
            cost_usd=0.75,
        )
        
        formatter = CLIFormatter()
        line = formatter.format_task_line(metrics, session_cost=2.50)
        
        # Numbers should be formatted with commas
        assert "50,000 in" in line
        assert "25,000 out" in line
        assert "$0.7500" in line
        assert "session: $2.50" in line
    
    def test_compact_line_no_color_mode(self):
        """Test that no_color=True removes ANSI codes."""
        metrics = TokenMetrics(
            task_id="task-004",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=0,
            cost_usd=0.05,
        )
        
        formatter = CLIFormatter(no_color=True)
        line = formatter.format_task_line(metrics, session_cost=0.10)
        
        # Should not contain ANSI escape codes
        assert "\033[" not in line
        assert "[tokens]" in line
        assert "engineer" in line
    
    def test_compact_line_respects_NO_COLOR_env(self):
        """Test that NO_COLOR environment variable disables colors."""
        metrics = TokenMetrics(
            task_id="task-005",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=0,
            cost_usd=0.05,
        )
        
        # Set NO_COLOR environment variable
        old_no_color = os.environ.get("NO_COLOR")
        try:
            os.environ["NO_COLOR"] = "1"
            formatter = CLIFormatter()
            line = formatter.format_task_line(metrics, session_cost=0.10)
            
            # Should not contain ANSI escape codes
            assert "\033[" not in line
        finally:
            # Restore original environment
            if old_no_color is None:
                os.environ.pop("NO_COLOR", None)
            else:
                os.environ["NO_COLOR"] = old_no_color


# ===========================================================================
# Session Summary Tests
# ===========================================================================

class TestSessionSummary:
    """Test format_session_summary() output."""
    
    def test_session_summary_contains_all_agents(self):
        """Test that summary includes all agents."""
        stats = TokenStats(
            total_input_tokens=45678,
            total_output_tokens=23456,
            total_cached_tokens=1234,
            total_cost_usd=0.89,
            task_count=12,
            agent_tokens={
                "engineer": 32000,
                "orchestrator": 9000,
                "quality-engineer": 4000,
            },
            agent_costs={
                "engineer": 0.64,
                "orchestrator": 0.18,
                "quality-engineer": 0.08,
            },
            agent_counts={
                "engineer": 5,
                "orchestrator": 4,
                "quality-engineer": 3,
            },
        )
        
        formatter = CLIFormatter()
        summary = formatter.format_session_summary(stats, budget_usd=1.0)
        
        # Should contain header
        assert "Token Session Summary" in summary
        
        # Should contain task count
        assert "Tasks:    12" in summary
        
        # Should contain total tokens
        assert "45,678" in summary
        assert "23,456" in summary
        assert "1,234" in summary
        
        # Should contain total cost
        assert "$0.89" in summary
        
        # Should contain all agents
        assert "engineer" in summary
        assert "orchestrator" in summary
        assert "quality-engineer" in summary
        
        # Should contain token counts
        assert "32,000" in summary
        assert "9,000" in summary
        assert "4,000" in summary
        
        # Should contain costs (with possible spacing for alignment)
        assert "0.64" in summary
        assert "0.18" in summary
        assert "0.08" in summary
    
    def test_session_summary_no_agents(self):
        """Test summary with no agents (empty session)."""
        stats = TokenStats(
            total_input_tokens=0,
            total_output_tokens=0,
            total_cached_tokens=0,
            total_cost_usd=0.0,
            task_count=0,
        )
        
        formatter = CLIFormatter()
        summary = formatter.format_session_summary(stats)
        
        assert "Token Session Summary" in summary
        assert "Tasks:    0" in summary
        assert "$0.00" in summary
    
    def test_session_summary_no_color_mode(self):
        """Test that no_color=True removes ANSI codes from summary."""
        stats = TokenStats(
            total_input_tokens=1000,
            total_output_tokens=500,
            total_cached_tokens=100,
            total_cost_usd=0.50,
            task_count=5,
            agent_tokens={"engineer": 1500},
            agent_costs={"engineer": 0.50},
            agent_counts={"engineer": 5},
        )
        
        formatter = CLIFormatter(no_color=True)
        summary = formatter.format_session_summary(stats, budget_usd=1.0)
        
        # Should not contain ANSI escape codes
        assert "\033[" not in summary
        assert "Token Session Summary" in summary
    
    def test_session_summary_with_budget(self):
        """Test summary shows budget percentage."""
        stats = TokenStats(
            total_input_tokens=1000,
            total_output_tokens=500,
            total_cached_tokens=100,
            total_cost_usd=0.50,
            task_count=5,
            agent_tokens={"engineer": 1500},
            agent_costs={"engineer": 0.50},
            agent_counts={"engineer": 5},
        )
        
        formatter = CLIFormatter()
        summary = formatter.format_session_summary(stats, budget_usd=1.0)
        
        # Should show budget percentage
        assert "50.0%" in summary
        assert "$1.00" in summary
    
    def test_session_summary_agents_sorted_by_cost(self):
        """Test that agents are sorted by cost (descending)."""
        stats = TokenStats(
            total_input_tokens=6000,
            total_output_tokens=3000,
            total_cached_tokens=0,
            total_cost_usd=0.90,
            task_count=3,
            agent_tokens={
                "quality-engineer": 1000,
                "engineer": 5000,
                "orchestrator": 3000,
            },
            agent_costs={
                "quality-engineer": 0.10,
                "engineer": 0.60,
                "orchestrator": 0.20,
            },
            agent_counts={
                "quality-engineer": 1,
                "engineer": 1,
                "orchestrator": 1,
            },
        )
        
        formatter = CLIFormatter()
        summary = formatter.format_session_summary(stats)
        
        # Engineer should appear before orchestrator, which should appear before quality-engineer
        engineer_pos = summary.find("engineer")
        orchestrator_pos = summary.find("orchestrator")
        quality_pos = summary.find("quality-engineer")
        
        assert engineer_pos < orchestrator_pos < quality_pos


# ===========================================================================
# Budget Color Tests
# ===========================================================================

class TestBudgetColor:
    """Test _budget_color() method."""
    
    def test_budget_color_normal_below_70(self):
        """Test that colors are green for < 70% budget."""
        formatter = CLIFormatter()
        
        assert formatter._budget_color(0.0) == CLIFormatter.ANSI_GREEN
        assert formatter._budget_color(50.0) == CLIFormatter.ANSI_GREEN
        assert formatter._budget_color(69.9) == CLIFormatter.ANSI_GREEN
    
    def test_budget_color_warning_70_to_90(self):
        """Test that colors are yellow for 70-90% budget."""
        formatter = CLIFormatter()
        
        assert formatter._budget_color(70.0) == CLIFormatter.ANSI_YELLOW
        assert formatter._budget_color(75.0) == CLIFormatter.ANSI_YELLOW
        assert formatter._budget_color(89.9) == CLIFormatter.ANSI_YELLOW
    
    def test_budget_color_critical_above_90(self):
        """Test that colors are red for >= 90% budget."""
        formatter = CLIFormatter()
        
        assert formatter._budget_color(90.0) == CLIFormatter.ANSI_RED
        assert formatter._budget_color(95.0) == CLIFormatter.ANSI_RED
        assert formatter._budget_color(100.0) == CLIFormatter.ANSI_RED
    
    def test_budget_color_no_color_mode(self):
        """Test that _budget_color returns empty string in no_color mode."""
        formatter = CLIFormatter(no_color=True)
        
        # Even though _budget_color returns a color, _colorize will ignore it
        color = formatter._budget_color(50.0)
        colorized = formatter._colorize("test", color)
        
        assert colorized == "test"
        assert "\033[" not in colorized


# ===========================================================================
# Colorize Method Tests
# ===========================================================================

class TestColorize:
    """Test _colorize() method."""
    
    def test_colorize_with_color(self, monkeypatch):
        """Test that _colorize applies ANSI codes."""
        monkeypatch.delenv("NO_COLOR", raising=False)
        formatter = CLIFormatter()
        text = "test"
        colored = formatter._colorize(text, CLIFormatter.ANSI_GREEN)
        
        assert colored == f"{CLIFormatter.ANSI_GREEN}test{CLIFormatter.ANSI_RESET}"
    
    def test_colorize_no_color_mode(self):
        """Test that _colorize returns plain text in no_color mode."""
        formatter = CLIFormatter(no_color=True)
        text = "test"
        colored = formatter._colorize(text, CLIFormatter.ANSI_GREEN)
        
        assert colored == "test"
        assert "\033[" not in colored
    
    def test_colorize_empty_color(self):
        """Test that _colorize handles empty color string."""
        formatter = CLIFormatter()
        text = "test"
        colored = formatter._colorize(text, "")
        
        assert colored == "test"


# ===========================================================================
# Integration Tests
# ===========================================================================

class TestIntegration:
    """Integration tests combining multiple features."""
    
    def test_full_workflow_with_color(self):
        """Test complete workflow with colors enabled."""
        # Create metrics
        metrics = TokenMetrics(
            task_id="task-001",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=100,
            cost_usd=0.05,
        )
        
        # Create stats
        stats = TokenStats(
            total_input_tokens=1000,
            total_output_tokens=500,
            total_cached_tokens=100,
            total_cost_usd=0.05,
            task_count=1,
            agent_tokens={"engineer": 1500},
            agent_costs={"engineer": 0.05},
            agent_counts={"engineer": 1},
        )
        
        formatter = CLIFormatter()
        
        # Format task line
        task_line = formatter.format_task_line(metrics, session_cost=0.05)
        assert "[tokens]" in task_line
        assert "engineer" in task_line
        
        # Format summary
        summary = formatter.format_session_summary(stats, budget_usd=1.0)
        assert "Token Session Summary" in summary
        assert "engineer" in summary
    
    def test_full_workflow_no_color(self):
        """Test complete workflow with colors disabled."""
        # Create metrics
        metrics = TokenMetrics(
            task_id="task-001",
            agent="engineer",
            input_tokens=1000,
            output_tokens=500,
            cached_tokens=100,
            cost_usd=0.05,
        )
        
        # Create stats
        stats = TokenStats(
            total_input_tokens=1000,
            total_output_tokens=500,
            total_cached_tokens=100,
            total_cost_usd=0.05,
            task_count=1,
            agent_tokens={"engineer": 1500},
            agent_costs={"engineer": 0.05},
            agent_counts={"engineer": 1},
        )
        
        formatter = CLIFormatter(no_color=True)
        
        # Format task line
        task_line = formatter.format_task_line(metrics, session_cost=0.05)
        assert "\033[" not in task_line
        assert "[tokens]" in task_line
        
        # Format summary
        summary = formatter.format_session_summary(stats, budget_usd=1.0)
        assert "\033[" not in summary
        assert "Token Session Summary" in summary
