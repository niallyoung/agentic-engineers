"""
CLI Formatter — Format TokenStats into ANSI-colored console output.

Provides formatted display of token metrics with color-coded budget status.
Respects NO_COLOR environment variable for plain-text output.

Usage:
    formatter = CLIFormatter()
    
    # Format a single task's metrics
    line = formatter.format_task_line(metrics, session_cost=0.12)
    print(line)
    
    # Format full session summary
    summary = formatter.format_session_summary(stats, budget_usd=10.0)
    print(summary)
"""

import os
from typing import Optional
from .token_tracker import TokenMetrics, TokenStats


class CLIFormatter:
    """Format token metrics into ANSI-colored console output."""
    
    # ANSI color codes
    ANSI_GREEN = "\033[32m"
    ANSI_YELLOW = "\033[33m"
    ANSI_RED = "\033[31m"
    ANSI_BOLD = "\033[1m"
    ANSI_RESET = "\033[0m"
    ANSI_DIM = "\033[2m"
    
    def __init__(self, no_color: bool = False):
        """
        Initialize CLIFormatter.
        
        Args:
            no_color: If True, disable all ANSI color codes.
                     Also respects NO_COLOR environment variable.
        """
        self.no_color = no_color or os.environ.get("NO_COLOR") is not None
    
    def format_task_line(
        self,
        metrics: TokenMetrics,
        session_cost: float = 0.0,
    ) -> str:
        """
        Format a compact one-liner for a completed task.
        
        Format: [tokens] {agent}: {in:,} in / {out:,} out | ${cost:.4f} | session: ${session_cost:.2f}
        Example: [tokens] engineer: 1,234 in / 567 out | $0.0045 | session: $0.12
        
        Args:
            metrics: TokenMetrics for the task
            session_cost: Total session cost so far
        
        Returns:
            Formatted string with ANSI colors (or plain if no_color=True)
        """
        # Format the base line
        line = (
            f"[tokens] {metrics.agent}: "
            f"{metrics.input_tokens:,} in / {metrics.output_tokens:,} out | "
            f"${metrics.cost_usd:.4f} | "
            f"session: ${session_cost:.2f}"
        )
        
        # Apply color based on cost (as a simple heuristic for budget usage)
        # For a single task, we'll use green by default
        color = self._budget_color(0.0)  # 0% of budget for single task
        
        return self._colorize(line, color)
    
    def format_session_summary(
        self,
        stats: TokenStats,
        budget_usd: float = 0.0,
    ) -> str:
        """
        Format a full session summary table.
        
        Shows:
        - Task count
        - Total tokens (input, output, cached)
        - Total cost
        - Per-agent breakdown with percentages
        
        Args:
            stats: TokenStats with aggregated metrics
            budget_usd: Optional budget limit for color coding
        
        Returns:
            Formatted multi-line string with ANSI colors
        """
        lines = []
        
        # Header
        lines.append(self._colorize("━━━ Token Session Summary ━━━", self.ANSI_BOLD))
        
        # Task count
        lines.append(f"  Tasks:    {stats.task_count}")
        
        # Total tokens
        total_line = (
            f"  Total in: {stats.total_input_tokens:,} | "
            f"out: {stats.total_output_tokens:,} | "
            f"cached: {stats.total_cached_tokens:,}"
        )
        lines.append(total_line)
        
        # Total cost
        cost_pct = 0.0
        if budget_usd > 0:
            cost_pct = (stats.total_cost_usd / budget_usd) * 100
        
        cost_color = self._budget_color(cost_pct)
        cost_line = f"  Cost:     ${stats.total_cost_usd:.2f} USD"
        if budget_usd > 0:
            cost_line += f" ({cost_pct:.1f}% of ${budget_usd:.2f})"
        lines.append(self._colorize(cost_line, cost_color))
        
        # Per-agent breakdown
        if stats.agent_tokens:
            lines.append("  By agent:")
            
            # Sort agents by cost (descending)
            sorted_agents = sorted(
                stats.agent_tokens.items(),
                key=lambda x: stats.agent_costs.get(x[0], 0.0),
                reverse=True,
            )
            
            for agent, tokens in sorted_agents:
                cost = stats.agent_costs.get(agent, 0.0)
                count = stats.agent_counts.get(agent, 0)
                
                # Calculate percentages
                token_pct = (tokens / stats.effective_tokens * 100) if stats.effective_tokens > 0 else 0
                cost_pct = (cost / stats.total_cost_usd * 100) if stats.total_cost_usd > 0 else 0
                
                # Format agent line
                agent_line = (
                    f"    {agent:15} {tokens:7,} tokens  "
                    f"${cost:7.2f}  ({cost_pct:5.1f}%)"
                )
                
                # Color based on agent's cost percentage
                agent_color = self._budget_color(cost_pct)
                lines.append(self._colorize(agent_line, agent_color))
        
        return "\n".join(lines)
    
    def _colorize(self, text: str, color: str) -> str:
        """
        Apply ANSI color to text if not in no_color mode.
        
        Args:
            text: Text to colorize
            color: ANSI color code (e.g., ANSI_GREEN)
        
        Returns:
            Colorized text or plain text if no_color=True
        """
        if self.no_color or not color:
            return text
        return f"{color}{text}{self.ANSI_RESET}"
    
    def _budget_color(self, pct: float) -> str:
        """
        Return appropriate ANSI color for budget percentage.
        
        Color scheme:
        - Green: < 70% of budget
        - Yellow: 70-90% of budget
        - Red: >= 90% of budget
        
        Args:
            pct: Percentage of budget used (0-100)
        
        Returns:
            ANSI color code string
        """
        if pct >= 90:
            return self.ANSI_RED
        elif pct >= 70:
            return self.ANSI_YELLOW
        else:
            return self.ANSI_GREEN
