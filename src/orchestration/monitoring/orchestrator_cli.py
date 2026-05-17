"""
OrchestratorCLI — Unified CLI Integration Layer

Ties together TokenTracker, CLIFormatter, and BudgetChecker into a single
integration point for the Orchestrator. Provides formatted output, budget
enforcement, and session management.

Usage:
    tracker = TokenTracker(registry)
    cli = OrchestratorCLI(
        token_tracker=tracker,
        budget_config_path=Path("config/token_budget.yaml"),
        on_budget_exceeded=handle_budget_alert,
    )
    
    # After each task completes
    cli.on_task_complete(delegate, handback)
    
    # At end of session
    cli.print_session_summary()
    
    # Check if new tasks should be blocked
    if cli.should_block_new_tasks():
        print("Budget exhausted, blocking new tasks")
"""

from typing import Callable, Optional, Dict, Any
from pathlib import Path
from src.orchestration.monitoring.token_tracker import TokenTracker, TokenMetrics, TokenStats
from src.orchestration.monitoring.cli_formatter import CLIFormatter
from src.orchestration.monitoring.budget_checker import BudgetChecker, BudgetStatus, BudgetResult


class OrchestratorCLI:
    """
    Unified CLI integration for token tracking, formatting, and budget enforcement.
    
    Wraps TokenTracker, CLIFormatter, and BudgetChecker to provide a single
    entry point for:
    - Recording task completion and token metrics
    - Formatting and printing task output
    - Checking budget status and enforcing limits
    - Printing session summaries
    - Managing session lifecycle (init, finalization)
    
    Thread-safe for use in concurrent environments.
    """
    
    def __init__(
        self,
        token_tracker: TokenTracker,
        budget_config_path: Optional[Path] = None,
        no_color: bool = False,
        on_budget_exceeded: Optional[Callable[[BudgetResult], None]] = None,
    ):
        """
        Initialize OrchestratorCLI with dependencies.
        
        Args:
            token_tracker: TokenTracker instance for recording metrics
            budget_config_path: Path to token_budget.yaml config file.
                               If not provided, uses default budget config.
            no_color: If True, disable ANSI color codes in output.
                     Also respects NO_COLOR environment variable.
            on_budget_exceeded: Optional callback function called when budget
                               reaches WARNING, CRITICAL, or BLOCKED status.
                               Receives BudgetResult as argument.
        """
        self.tracker = token_tracker
        self.formatter = CLIFormatter(no_color=no_color)
        self.budget_checker = BudgetChecker(config_path=budget_config_path)
        self.on_budget_exceeded = on_budget_exceeded
    
    def on_task_complete(self, delegate: Dict[str, Any], handback: Dict[str, Any]) -> None:
        """
        Called after a task completes. Records metrics, prints formatted output,
        and checks budget status.
        
        Workflow:
        1. Extract token metrics from handback
        2. Record metrics in TokenTracker
        3. Get current stats and format task line
        4. Print formatted output
        5. Check budget status
        6. If warning/critical/blocked, call on_budget_exceeded callback
        
        Args:
            delegate: DELEGATE block with task_id, role, model, effort
            handback: HANDBACK block with tokens_in, tokens_out, cost_usd
        
        Raises:
            ValueError: If required fields are missing from handback
        """
        # Extract required fields from handback
        task_id = handback.get("task_id")
        if not task_id:
            raise ValueError("HANDBACK missing required field: task_id")
        
        # Extract token metrics (with sensible defaults for synthetic HANDBACKs)
        tokens_in = handback.get("tokens_in", 0)
        tokens_out = handback.get("tokens_out", 0)
        cached_tokens = handback.get("cached_tokens", 0)
        cost_usd = handback.get("cost_usd", 0.0)
        
        # Get agent from delegate
        agent = delegate.get("role", "unknown")
        
        # Record metrics in tracker
        self.tracker.record_task_tokens(
            task_id=task_id,
            agent=agent,
            input_tokens=tokens_in,
            output_tokens=tokens_out,
            cached_tokens=cached_tokens,
            cost_usd=cost_usd,
        )
        
        # Get current stats for formatting
        stats = self.tracker.get_stats()
        
        # Format and print task line
        metrics = TokenMetrics(
            task_id=task_id,
            agent=agent,
            input_tokens=tokens_in,
            output_tokens=tokens_out,
            cached_tokens=cached_tokens,
            cost_usd=cost_usd,
        )
        task_line = self.formatter.format_task_line(metrics, session_cost=stats.total_cost_usd)
        print(task_line)
        
        # Check budget status
        budget_result = self.budget_checker.check(stats)
        
        # If budget threshold exceeded, call callback
        if budget_result.status in (BudgetStatus.WARNING, BudgetStatus.CRITICAL, BudgetStatus.BLOCKED):
            if self.on_budget_exceeded:
                try:
                    self.on_budget_exceeded(budget_result)
                except Exception:
                    pass  # Callback errors must not crash OrchestratorCLI
            else:
                # Print alert if no callback provided
                self._print_budget_alert(budget_result)
    
    def print_session_summary(self) -> None:
        """
        Print full session summary at end of session.
        
        Displays:
        - Task count
        - Total tokens (input, output, cached)
        - Total cost
        - Per-agent breakdown with percentages
        - Budget status
        """
        stats = self.tracker.get_stats()
        budget_config = self.budget_checker.budget_config
        budget_usd = budget_config.get("session_usd", 5.0)
        
        # Format and print summary
        summary = self.formatter.format_session_summary(stats, budget_usd=budget_usd)
        print("\n" + summary)
        
        # Check final budget status
        budget_result = self.budget_checker.check(stats)
        if budget_result.status != BudgetStatus.OK:
            print()
            self._print_budget_alert(budget_result)
    
    def should_block_new_tasks(self) -> bool:
        """
        Determine if new tasks should be blocked due to budget exhaustion.
        
        Returns:
            True if budget is exhausted (status == BLOCKED), False otherwise
        """
        stats = self.tracker.get_stats()
        return self.budget_checker.should_block(stats)
    
    def reset_session(self) -> None:
        """
        Reset token tracker for new session.
        
        Clears all recorded metrics and resets counters.
        """
        self.tracker.clear()
    
    def get_session_stats(self) -> TokenStats:
        """
        Get current session statistics.
        
        Returns:
            TokenStats object with aggregated metrics
        """
        return self.tracker.get_stats()
    
    def get_budget_status(self) -> BudgetResult:
        """
        Get current budget status.
        
        Returns:
            BudgetResult with status, percentage used, remaining budget
        """
        stats = self.tracker.get_stats()
        return self.budget_checker.check(stats)
    
    def _print_budget_alert(self, budget_result: BudgetResult) -> None:
        """
        Print a formatted budget alert.
        
        Args:
            budget_result: BudgetResult from budget check
        """
        color_map = {
            BudgetStatus.WARNING: self.formatter.ANSI_YELLOW,
            BudgetStatus.CRITICAL: self.formatter.ANSI_RED,
            BudgetStatus.BLOCKED: self.formatter.ANSI_RED,
        }
        
        color = color_map.get(budget_result.status, "")
        alert_line = f"⚠️  BUDGET ALERT: {budget_result.message}"
        print(self.formatter._colorize(alert_line, color))
