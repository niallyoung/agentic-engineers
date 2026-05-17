"""
BudgetChecker — Budget Tracking & Enforcement

Loads budget configuration, checks cumulative token costs against thresholds,
and returns enforcement decisions. Integrates with TokenTracker to provide
real-time budget status and blocking decisions.

Usage:
    checker = BudgetChecker(config_path=Path("config/token_budget.yaml"))
    result = checker.check(stats)
    
    if result.status == BudgetStatus.BLOCKED:
        print("Budget exhausted, blocking new tasks")
    elif result.status == BudgetStatus.CRITICAL:
        print(f"WARNING: {result.message}")
"""

from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
import copy

from .token_tracker import TokenStats


class BudgetStatus(Enum):
    """Budget status enumeration."""
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    BLOCKED = "blocked"


@dataclass
class BudgetResult:
    """Result of a budget check operation."""
    status: BudgetStatus
    pct_used: float
    remaining_usd: float
    message: str
    budget_usd: float
    
    def __str__(self) -> str:
        """Return human-readable budget status."""
        return f"[{self.status.value.upper()}] {self.pct_used:.1f}% used (${self.remaining_usd:.2f} remaining) - {self.message}"


class BudgetChecker:
    """
    Tracks and enforces token budget constraints.
    
    Loads budget configuration from YAML, checks current spending against
    configured thresholds (warning, critical, block), and provides enforcement
    decisions for task execution.
    
    Thread-safe implementation suitable for use in concurrent environments.
    """
    
    DEFAULT_CONFIG = {
        "budget": {
            "session_usd": 5.0,
            "daily_usd": 20.0,
            "warn_pct": 70,
            "critical_pct": 90,
            "block_pct": 100,
        },
        "display": {
            "mode": "compact",
            "show_per_task": True,
            "show_session_summary": True,
        }
    }
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize BudgetChecker with optional config file.
        
        Args:
            config_path: Path to token_budget.yaml config file.
                        If not provided, uses DEFAULT_CONFIG.
        """
        self.config = self._load_config(config_path)
        self.budget_config = self.config.get("budget", {})
        self.display_config = self.config.get("display", {})
    
    def check(self, stats: TokenStats) -> BudgetResult:
        """
        Check current spending against budget thresholds.
        
        Args:
            stats: TokenStats from TokenTracker.get_stats()
        
        Returns:
            BudgetResult with status, percentage used, remaining budget, and message
        """
        budget_usd = self.budget_config.get("session_usd", 5.0)
        warn_pct = self.budget_config.get("warn_pct", 70)
        critical_pct = self.budget_config.get("critical_pct", 90)
        block_pct = self.budget_config.get("block_pct", 100)
        
        current_cost = stats.total_cost_usd
        
        # Handle zero budget edge case
        if budget_usd == 0:
            if current_cost > 0:
                pct_used = float('inf')  # Infinite percentage
                status = BudgetStatus.BLOCKED
                message = f"Budget exhausted: ${current_cost:.2f} spent with $0.00 budget"
                remaining_usd = 0.0
            else:
                pct_used = 0.0
                status = BudgetStatus.OK
                message = "Budget OK: No cost incurred"
                remaining_usd = 0.0
        else:
            pct_used = (current_cost / budget_usd * 100)
            remaining_usd = max(0.0, budget_usd - current_cost)
            
            # Determine status based on percentage thresholds
            if pct_used >= block_pct:
                status = BudgetStatus.BLOCKED
                message = f"Budget exhausted: ${current_cost:.2f} of ${budget_usd:.2f} spent"
            elif pct_used >= critical_pct:
                status = BudgetStatus.CRITICAL
                message = f"Critical budget level: {pct_used:.1f}% of ${budget_usd:.2f} spent"
            elif pct_used >= warn_pct:
                status = BudgetStatus.WARNING
                message = f"Budget warning: {pct_used:.1f}% of ${budget_usd:.2f} spent"
            else:
                status = BudgetStatus.OK
                message = f"Budget OK: {pct_used:.1f}% of ${budget_usd:.2f} spent"
        
        return BudgetResult(
            status=status,
            pct_used=pct_used,
            remaining_usd=remaining_usd,
            message=message,
            budget_usd=budget_usd,
        )
    
    def should_block(self, stats: TokenStats) -> bool:
        """
        Determine if new tasks should be blocked based on budget.
        
        Args:
            stats: TokenStats from TokenTracker.get_stats()
        
        Returns:
            True if budget is exhausted (status == BLOCKED), False otherwise
        """
        result = self.check(stats)
        return result.status == BudgetStatus.BLOCKED
    
    def _load_config(self, path: Optional[Path]) -> Dict[str, Any]:
        """
        Load configuration from YAML file, falling back to defaults.
        
        Args:
            path: Path to config file, or None to use defaults
        
        Returns:
            Configuration dictionary with budget and display settings
        """
        if path is None:
            return copy.deepcopy(self.DEFAULT_CONFIG)
        
        config_path = Path(path)
        if not config_path.exists():
            # Fall back to defaults if file doesn't exist
            return copy.deepcopy(self.DEFAULT_CONFIG)
        
        try:
            with open(config_path, 'r') as f:
                loaded_config = yaml.safe_load(f)
                if loaded_config is None:
                    return copy.deepcopy(self.DEFAULT_CONFIG)
                
                # Merge with defaults to ensure all keys exist
                merged = copy.deepcopy(self.DEFAULT_CONFIG)
                if "budget" in loaded_config:
                    merged["budget"].update(loaded_config["budget"])
                if "display" in loaded_config:
                    merged["display"].update(loaded_config["display"])
                
                return merged
        except (yaml.YAMLError, IOError):
            # Fall back to defaults on any error
            return copy.deepcopy(self.DEFAULT_CONFIG)
