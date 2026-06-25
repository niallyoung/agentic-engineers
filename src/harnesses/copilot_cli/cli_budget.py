"""
CLI commands for budget management.

Provides command-line interface for budget configuration, status reporting,
cost analysis, and forecasting.

Author: Engineer
"""

import argparse
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import sys

from src.harnesses.copilot_cli.cost_tracker import CostTracker
from src.harnesses.copilot_cli.budget_manager import BudgetManager, AlertLevel


class BudgetCLI:
    """Command-line interface for budget management."""
    
    def __init__(self):
        """Initialize CLI."""
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser."""
        parser = argparse.ArgumentParser(
            description="Copilot budget management CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        
        subparsers = parser.add_subparsers(dest="command", help="Available commands")
        
        # Status command
        status_parser = subparsers.add_parser("status", help="Show budget status")
        status_parser.add_argument(
            "--session",
            type=str,
            help="Session ID or file path",
            required=False,
        )
        status_parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed status",
        )
        
        # Report command
        report_parser = subparsers.add_parser("report", help="Generate budget report")
        report_parser.add_argument(
            "--session",
            type=str,
            help="Session ID or file path",
            required=False,
        )
        report_parser.add_argument(
            "--output",
            type=str,
            help="Output file path (default: stdout)",
            required=False,
        )
        
        # Forecast command
        forecast_parser = subparsers.add_parser("forecast", help="Forecast budget exhaustion")
        forecast_parser.add_argument(
            "--session",
            type=str,
            help="Session ID or file path",
            required=False,
        )
        forecast_parser.add_argument(
            "--budget",
            type=float,
            help="Session budget in USD",
            required=True,
        )
        
        # Cost breakdown command
        breakdown_parser = subparsers.add_parser("breakdown", help="Show cost breakdown by model")
        breakdown_parser.add_argument(
            "--session",
            type=str,
            help="Session ID or file path",
            required=False,
        )
        breakdown_parser.add_argument(
            "--format",
            choices=["table", "json"],
            default="table",
            help="Output format",
        )
        
        # Recommendations command
        recc_parser = subparsers.add_parser("recommendations", help="Get cost optimization recommendations")
        recc_parser.add_argument(
            "--session",
            type=str,
            help="Session ID or file path",
            required=False,
        )
        recc_parser.add_argument(
            "--min-severity",
            choices=["low", "medium", "high"],
            default="medium",
            help="Minimum recommendation severity",
        )
        
        # History command
        history_parser = subparsers.add_parser("history", help="Show cost history")
        history_parser.add_argument(
            "--session",
            type=str,
            help="Session ID or file path",
            required=False,
        )
        history_parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Limit number of tasks shown",
        )
        history_parser.add_argument(
            "--model",
            type=str,
            help="Filter by model",
            required=False,
        )
        
        return parser
    
    def parse_args(self, args: Optional[list] = None) -> argparse.Namespace:
        """Parse command-line arguments."""
        return self.parser.parse_args(args)
    
    def run(self, args: Optional[list] = None) -> int:
        """
        Run CLI command.
        
        Args:
            args: Command arguments (default: sys.argv[1:])
            
        Returns:
            Exit code (0 for success, 1 for error)
        """
        try:
            parsed_args = self.parse_args(args)
            
            if not parsed_args.command:
                self.parser.print_help()
                return 0
            
            if parsed_args.command == "status":
                return self._cmd_status(parsed_args)
            elif parsed_args.command == "report":
                return self._cmd_report(parsed_args)
            elif parsed_args.command == "forecast":
                return self._cmd_forecast(parsed_args)
            elif parsed_args.command == "breakdown":
                return self._cmd_breakdown(parsed_args)
            elif parsed_args.command == "recommendations":
                return self._cmd_recommendations(parsed_args)
            elif parsed_args.command == "history":
                return self._cmd_history(parsed_args)
            else:
                print(f"Unknown command: {parsed_args.command}")
                return 1
        except KeyboardInterrupt:
            print("\nInterrupted")
            return 130
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    
    def _cmd_status(self, args: argparse.Namespace) -> int:
        """Show budget status."""
        tracker = self._load_session(args.session)
        
        # Create a temporary budget manager for status display
        # We use a high budget since we just want to see the spending
        budget_mgr = BudgetManager(session_budget_usd=float('inf'))
        
        status = budget_mgr.get_budget_status(tracker)
        
        print("Budget Status")
        print("-" * 50)
        print(f"Total Tasks:        {status['total_tasks']}")
        print(f"Current Spending:   ${status['current_cost_usd']:.3f}")
        print(f"Average per Task:   ${status['average_cost_per_task']:.4f}")
        print(f"Blocked Tasks:      {status['blocked_tasks']}")
        print(f"Alerts:             {status['alert_count']}")
        
        if args.verbose:
            tokens = tracker.get_session_total_tokens()
            print(f"\nToken Usage")
            print("-" * 50)
            print(f"Input Tokens:       {tokens.input_tokens:,}")
            print(f"Output Tokens:      {tokens.output_tokens:,}")
            print(f"Cached Tokens:      {tokens.cached_tokens:,}")
            print(f"Total Tokens:       {tokens.total_tokens:,}")
            print(f"Efficiency Ratio:   {tracker.get_efficiency_ratio():.2%}")
        
        return 0
    
    def _cmd_report(self, args: argparse.Namespace) -> int:
        """Generate budget report."""
        tracker = self._load_session(args.session)
        
        # Create temporary budget manager
        budget_mgr = BudgetManager(session_budget_usd=float('inf'))
        report = budget_mgr.get_report(tracker)
        
        if args.output:
            Path(args.output).write_text(report)
            print(f"Report written to {args.output}")
        else:
            print(report)
        
        return 0
    
    def _cmd_forecast(self, args: argparse.Namespace) -> int:
        """Forecast budget consumption."""
        tracker = self._load_session(args.session)
        budget_mgr = BudgetManager(session_budget_usd=args.budget)
        
        forecast = budget_mgr.forecast_remaining_budget(tracker)
        
        print("Budget Forecast")
        print("-" * 50)
        
        if not forecast["forecast_available"]:
            print(f"Forecast not available: {forecast['reason']}")
            return 0
        
        print(f"Session Budget:     ${args.budget:.2f}")
        current = tracker.get_session_total_cost()
        print(f"Current Spending:   ${current:.3f}")
        print(f"Remaining Budget:   ${forecast['remaining_budget_usd']:.3f}")
        print(f"\nForecast")
        print(f"Avg Cost per Task:  ${forecast['average_cost_per_task']:.4f}")
        print(f"Conservative Est:   ${forecast['conservative_cost_per_task']:.4f}")
        print(f"Tasks Remaining:    {forecast['estimated_tasks_remaining']}")
        
        if forecast['estimated_time_to_exhaustion_ms']:
            hours = forecast['estimated_time_to_exhaustion_ms'] / (1000 * 60 * 60)
            print(f"Time to Exhaustion: {hours:.1f} hours")
        
        return 0
    
    def _cmd_breakdown(self, args: argparse.Namespace) -> int:
        """Show cost breakdown by model."""
        tracker = self._load_session(args.session)
        breakdown = tracker.get_cost_by_model()
        total = tracker.get_session_total_cost()
        
        if args.format == "json":
            print(json.dumps(breakdown, indent=2))
            return 0
        
        # Table format
        print("Cost Breakdown by Model")
        print("-" * 70)
        print(f"{'Model':<30} {'Tasks':<8} {'Cost':<12} {'% of Total':<12}")
        print("-" * 70)
        
        for model in sorted(breakdown.keys()):
            data = breakdown[model]
            pct = (data["cost"] / total * 100) if total > 0 else 0
            print(f"{model:<30} {data['count']:<8} ${data['cost']:<11.3f} {pct:<11.1f}%")
        
        print("-" * 70)
        print(f"{'TOTAL':<30} {len(tracker.tasks):<8} ${total:<11.3f} {100.0:<11.1f}%")
        
        return 0
    
    def _cmd_recommendations(self, args: argparse.Namespace) -> int:
        """Show cost optimization recommendations."""
        tracker = self._load_session(args.session)
        budget_mgr = BudgetManager(session_budget_usd=float('inf'))
        
        recommendations = budget_mgr.get_savings_recommendations(tracker)
        
        if not recommendations:
            print("No cost optimization recommendations at this time.")
            return 0
        
        severity_order = {"low": 0, "medium": 1, "high": 2}
        min_severity_level = severity_order.get(args.min_severity, 1)
        
        filtered = [
            r for r in recommendations
            if severity_order.get(r.get("severity"), 0) >= min_severity_level
        ]
        
        if not filtered:
            print(f"No recommendations with severity >= {args.min_severity}")
            return 0
        
        print("Cost Optimization Recommendations")
        print("-" * 70)
        
        for i, rec in enumerate(filtered, 1):
            severity = rec.get("severity", "unknown").upper()
            print(f"\n{i}. [{severity}] {rec.get('suggestion', '')}")
            
            if "potential_savings" in rec:
                print(f"   Potential Savings: ${rec['potential_savings']:.3f}")
            
            if "current_cost" in rec:
                print(f"   Current Cost: ${rec['current_cost']:.3f}")
        
        return 0
    
    def _cmd_history(self, args: argparse.Namespace) -> int:
        """Show cost history."""
        tracker = self._load_session(args.session)
        
        # Get tasks
        tasks = tracker.tasks
        
        if args.model:
            tasks = [t for t in tasks if t.model == args.model]
        
        # Show most recent first
        tasks = sorted(tasks, key=lambda t: t.timestamp, reverse=True)
        tasks = tasks[:args.limit]
        
        print("Recent Task Costs")
        print("-" * 90)
        print(f"{'Task ID':<20} {'Model':<25} {'Tokens':<12} {'Cost':<10} {'Time':<15}")
        print("-" * 90)
        
        for task in tasks:
            print(
                f"{task.task_id:<20} "
                f"{task.model:<25} "
                f"{task.token_usage.total_tokens:<12} "
                f"${task.cost_usd:<9.4f} "
                f"{task.timestamp.strftime('%H:%M:%S'):<15}"
            )
        
        print("-" * 90)
        
        return 0
    
    def _load_session(self, session_arg: Optional[str]) -> CostTracker:
        """
        Load a session (from file or create new).
        
        Args:
            session_arg: Session path or ID
            
        Returns:
            CostTracker instance
        """
        if session_arg and Path(session_arg).exists():
            tracker = CostTracker()
            tracker.load_from_file(session_arg)
            return tracker
        
        # Return empty tracker
        return CostTracker()


def main(args: Optional[list] = None) -> int:
    """Entry point for CLI."""
    cli = BudgetCLI()
    return cli.run(args)


if __name__ == "__main__":
    sys.exit(main())
