"""
Tests for BudgetChecker — Budget Tracking & Enforcement

Comprehensive test suite covering:
- Budget status determination (OK, WARNING, CRITICAL, BLOCKED)
- Threshold calculations and percentage tracking
- Configuration loading (YAML and defaults)
- Budget blocking decisions
- Edge cases and boundary conditions
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
import yaml

from src.orchestration.monitoring.budget_checker import (
    BudgetChecker,
    BudgetStatus,
    BudgetResult,
)
from src.orchestration.monitoring.token_tracker import TokenStats


class TestBudgetStatus:
    """Test BudgetStatus enum."""
    
    def test_status_values(self):
        """Verify all status values are defined."""
        assert BudgetStatus.OK.value == "ok"
        assert BudgetStatus.WARNING.value == "warning"
        assert BudgetStatus.CRITICAL.value == "critical"
        assert BudgetStatus.BLOCKED.value == "blocked"


class TestBudgetResult:
    """Test BudgetResult dataclass."""
    
    def test_budget_result_creation(self):
        """Verify BudgetResult can be created with all fields."""
        result = BudgetResult(
            status=BudgetStatus.OK,
            pct_used=50.0,
            remaining_usd=2.50,
            message="Budget OK",
            budget_usd=5.0,
        )
        assert result.status == BudgetStatus.OK
        assert result.pct_used == 50.0
        assert result.remaining_usd == 2.50
        assert result.message == "Budget OK"
        assert result.budget_usd == 5.0
    
    def test_budget_result_str(self):
        """Verify BudgetResult string representation."""
        result = BudgetResult(
            status=BudgetStatus.WARNING,
            pct_used=75.0,
            remaining_usd=1.25,
            message="Budget warning",
            budget_usd=5.0,
        )
        result_str = str(result)
        assert "WARNING" in result_str
        assert "75.0%" in result_str
        assert "1.25" in result_str


class TestBudgetCheckerStatusDetermination:
    """Test budget status determination logic."""
    
    def test_status_ok_below_warn_threshold(self):
        """Verify OK status when below warning threshold (70%)."""
        checker = BudgetChecker()
        stats = TokenStats(total_cost_usd=3.0)  # 60% of $5.00 budget
        
        result = checker.check(stats)
        
        assert result.status == BudgetStatus.OK
        assert result.pct_used == 60.0
        assert result.remaining_usd == 2.0
        assert "Budget OK" in result.message
    
    def test_status_warning_at_warn_threshold(self):
        """Verify WARNING status at warning threshold (70%)."""
        checker = BudgetChecker()
        stats = TokenStats(total_cost_usd=3.5)  # 70% of $5.00 budget
        
        result = checker.check(stats)
        
        assert result.status == BudgetStatus.WARNING
        assert result.pct_used == 70.0
        assert result.remaining_usd == 1.5
        assert "warning" in result.message.lower()
    
    def test_status_warning_between_thresholds(self):
        """Verify WARNING status between warn (70%) and critical (90%)."""
        checker = BudgetChecker()
        stats = TokenStats(total_cost_usd=4.0)  # 80% of $5.00 budget
        
        result = checker.check(stats)
        
        assert result.status == BudgetStatus.WARNING
        assert result.pct_used == 80.0
        assert result.remaining_usd == 1.0
    
    def test_status_critical_at_critical_threshold(self):
        """Verify CRITICAL status at critical threshold (90%)."""
        checker = BudgetChecker()
        stats = TokenStats(total_cost_usd=4.5)  # 90% of $5.00 budget
        
        result = checker.check(stats)
        
        assert result.status == BudgetStatus.CRITICAL
        assert result.pct_used == 90.0
        assert result.remaining_usd == 0.5
        assert "critical" in result.message.lower()
    
    def test_status_critical_above_critical_threshold(self):
        """Verify CRITICAL status above critical threshold but below block."""
        checker = BudgetChecker()
        stats = TokenStats(total_cost_usd=4.75)  # 95% of $5.00 budget
        
        result = checker.check(stats)
        
        assert result.status == BudgetStatus.CRITICAL
        assert result.pct_used == 95.0
        assert result.remaining_usd == 0.25
    
    def test_status_blocked_at_block_threshold(self):
        """Verify BLOCKED status at block threshold (100%)."""
        checker = BudgetChecker()
        stats = TokenStats(total_cost_usd=5.0)  # 100% of $5.00 budget
        
        result = checker.check(stats)
        
        assert result.status == BudgetStatus.BLOCKED
        assert result.pct_used == 100.0
        assert result.remaining_usd == 0.0
        assert "exhausted" in result.message.lower()
    
    def test_status_blocked_over_budget(self):
        """Verify BLOCKED status when over budget."""
        checker = BudgetChecker()
        stats = TokenStats(total_cost_usd=5.5)  # 110% of $5.00 budget
        
        result = checker.check(stats)
        
        assert result.status == BudgetStatus.BLOCKED
        assert result.pct_used == pytest.approx(110.0, abs=0.01)
        assert result.remaining_usd == 0.0  # Clamped to 0
    
    def test_status_ok_at_zero_cost(self):
        """Verify OK status with zero cost."""
        checker = BudgetChecker()
        stats = TokenStats(total_cost_usd=0.0)
        
        result = checker.check(stats)
        
        assert result.status == BudgetStatus.OK
        assert result.pct_used == 0.0
        assert result.remaining_usd == 5.0


class TestBudgetCheckerBlocking:
    """Test budget blocking decisions."""
    
    def test_should_block_returns_true_when_blocked(self):
        """Verify should_block returns True when status is BLOCKED."""
        checker = BudgetChecker()
        stats = TokenStats(total_cost_usd=5.0)  # At budget limit
        
        assert checker.should_block(stats) is True
    
    def test_should_block_returns_false_when_ok(self):
        """Verify should_block returns False when status is OK."""
        checker = BudgetChecker()
        stats = TokenStats(total_cost_usd=2.0)  # Well below limit
        
        assert checker.should_block(stats) is False
    
    def test_should_block_returns_false_when_warning(self):
        """Verify should_block returns False when status is WARNING."""
        checker = BudgetChecker()
        stats = TokenStats(total_cost_usd=3.5)  # At warning threshold
        
        assert checker.should_block(stats) is False
    
    def test_should_block_returns_false_when_critical(self):
        """Verify should_block returns False when status is CRITICAL."""
        checker = BudgetChecker()
        stats = TokenStats(total_cost_usd=4.5)  # At critical threshold
        
        assert checker.should_block(stats) is False


class TestBudgetCheckerConfiguration:
    """Test configuration loading and defaults."""
    
    def test_loads_config_from_yaml_file(self):
        """Verify config loads correctly from YAML file."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "token_budget.yaml"
            config_data = {
                "budget": {
                    "session_usd": 10.0,
                    "daily_usd": 50.0,
                    "warn_pct": 75,
                    "critical_pct": 85,
                    "block_pct": 100,
                },
                "display": {
                    "mode": "detailed",
                    "show_per_task": False,
                    "show_session_summary": True,
                }
            }
            
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            checker = BudgetChecker(config_path)
            
            assert checker.budget_config["session_usd"] == 10.0
            assert checker.budget_config["warn_pct"] == 75
            assert checker.display_config["mode"] == "detailed"
            assert checker.display_config["show_per_task"] is False
    
    def test_falls_back_to_defaults_when_no_config(self):
        """Verify defaults are used when config file doesn't exist."""
        checker = BudgetChecker(config_path=Path("/nonexistent/path.yaml"))
        
        assert checker.budget_config["session_usd"] == 5.0
        assert checker.budget_config["warn_pct"] == 70
        assert checker.budget_config["critical_pct"] == 90
        assert checker.budget_config["block_pct"] == 100
        assert checker.display_config["mode"] == "compact"
    
    def test_falls_back_to_defaults_when_config_is_none(self):
        """Verify defaults are used when config_path is None."""
        checker = BudgetChecker(config_path=None)
        
        assert checker.budget_config["session_usd"] == 5.0
        assert checker.budget_config["warn_pct"] == 70
    
    def test_merges_partial_config_with_defaults(self):
        """Verify partial config is merged with defaults."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "token_budget.yaml"
            config_data = {
                "budget": {
                    "session_usd": 15.0,
                    # Other budget fields will use defaults
                }
            }
            
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            checker = BudgetChecker(config_path)
            
            # Custom value
            assert checker.budget_config["session_usd"] == 15.0
            # Default values
            assert checker.budget_config["warn_pct"] == 70
            assert checker.budget_config["critical_pct"] == 90
    
    def test_handles_empty_yaml_file(self):
        """Verify defaults are used for empty YAML file."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "token_budget.yaml"
            
            with open(config_path, 'w') as f:
                f.write("")
            
            checker = BudgetChecker(config_path)
            
            assert checker.budget_config["session_usd"] == 5.0
            assert checker.budget_config["warn_pct"] == 70


class TestBudgetCheckerCalculations:
    """Test budget calculation accuracy."""
    
    def test_remaining_usd_calculated_correctly(self):
        """Verify remaining USD is calculated correctly."""
        checker = BudgetChecker()
        stats = TokenStats(total_cost_usd=2.35)
        
        result = checker.check(stats)
        
        assert result.remaining_usd == pytest.approx(2.65, abs=0.01)
    
    def test_remaining_usd_clamped_to_zero(self):
        """Verify remaining USD is clamped to zero when over budget."""
        checker = BudgetChecker()
        stats = TokenStats(total_cost_usd=6.0)
        
        result = checker.check(stats)
        
        assert result.remaining_usd == 0.0
    
    def test_percentage_calculation_precision(self):
        """Verify percentage calculation is precise."""
        checker = BudgetChecker()
        stats = TokenStats(total_cost_usd=1.234)
        
        result = checker.check(stats)
        
        expected_pct = (1.234 / 5.0) * 100
        assert result.pct_used == pytest.approx(expected_pct, abs=0.01)
    
    def test_budget_result_budget_usd_field(self):
        """Verify BudgetResult contains correct budget_usd."""
        checker = BudgetChecker()
        stats = TokenStats(total_cost_usd=2.0)
        
        result = checker.check(stats)
        
        assert result.budget_usd == 5.0


class TestBudgetCheckerEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_budget(self):
        """Verify behavior with zero budget (edge case)."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "token_budget.yaml"
            config_data = {
                "budget": {
                    "session_usd": 0.0,
                }
            }
            
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            checker = BudgetChecker(config_path)
            stats = TokenStats(total_cost_usd=0.1)
            
            result = checker.check(stats)
            
            # With zero budget, any cost is over budget
            assert result.status == BudgetStatus.BLOCKED
    
    def test_very_small_cost(self):
        """Verify handling of very small costs."""
        checker = BudgetChecker()
        stats = TokenStats(total_cost_usd=0.001)
        
        result = checker.check(stats)
        
        assert result.status == BudgetStatus.OK
        assert result.pct_used == pytest.approx(0.02, abs=0.01)
    
    def test_custom_thresholds(self):
        """Verify custom thresholds are respected."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "token_budget.yaml"
            config_data = {
                "budget": {
                    "session_usd": 10.0,
                    "warn_pct": 50,
                    "critical_pct": 75,
                    "block_pct": 100,
                }
            }
            
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            checker = BudgetChecker(config_path)
            
            # 50% should trigger warning
            stats_warn = TokenStats(total_cost_usd=5.0)
            result_warn = checker.check(stats_warn)
            assert result_warn.status == BudgetStatus.WARNING
            
            # 75% should trigger critical
            stats_crit = TokenStats(total_cost_usd=7.5)
            result_crit = checker.check(stats_crit)
            assert result_crit.status == BudgetStatus.CRITICAL


class TestBudgetCheckerIntegration:
    """Integration tests with realistic scenarios."""
    
    def test_full_session_lifecycle(self):
        """Test budget tracking through a full session."""
        checker = BudgetChecker()
        
        # Start of session
        stats1 = TokenStats(total_cost_usd=1.0)
        result1 = checker.check(stats1)
        assert result1.status == BudgetStatus.OK
        
        # Mid session
        stats2 = TokenStats(total_cost_usd=3.5)
        result2 = checker.check(stats2)
        assert result2.status == BudgetStatus.WARNING
        
        # Near end
        stats3 = TokenStats(total_cost_usd=4.5)
        result3 = checker.check(stats3)
        assert result3.status == BudgetStatus.CRITICAL
        
        # At limit
        stats4 = TokenStats(total_cost_usd=5.0)
        result4 = checker.check(stats4)
        assert result4.status == BudgetStatus.BLOCKED
    
    def test_multiple_agents_tracking(self):
        """Test budget tracking with multiple agents."""
        checker = BudgetChecker()
        
        # Simulate multiple agents contributing to cost
        # 60% of $5.00 budget = $3.00, which is below 70% warning threshold
        stats = TokenStats(
            total_cost_usd=3.0,
            task_count=5,
            agent_tokens={"engineer": 2000, "orchestrator": 1500},
            agent_costs={"engineer": 2.0, "orchestrator": 1.0},
            agent_counts={"engineer": 3, "orchestrator": 2},
        )
        
        result = checker.check(stats)
        
        assert result.status == BudgetStatus.OK
        assert result.pct_used == 60.0
        assert result.remaining_usd == 2.0
