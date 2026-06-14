# -*- coding: utf-8 -*-
"""
TokenAdvisor - Daily metrics analysis and optimization recommendations.

Analyzes Claude token usage, cost, and quality metrics to identify optimization
opportunities and recommend task routing adjustments.

Usage:
    ./tokenadvisor.py [--date YYYY-MM-DD] [--summary | --daily | --weekly]
    ./tokenadvisor.py --date 2026-04-24 --daily
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Any, Dict, List, Tuple
from statistics import mean, median, stdev

# Role-based cost targets (from config/MODEL_ASSIGNMENTS_LOCKED.md)
ROLE_TARGETS = {
    "Orchestrator": 0.70,
    "Engineer": 0.15,
    "Senior Engineer": 0.08,
    "Lead Engineer": 0.04,
    "Principal Engineer": 0.02,
    "Quality Engineer": 0.01,
}

# Model costs (per 1K input tokens, aligned to src/config/models.yaml)
MODEL_COSTS = {
    "haiku-4-5": 0.001,
    "sonnet-4-6": 0.003,
    "opus-4-8": 0.005,
    "fable-5": 0.010,
}


class MetricsAnalyzer:
    """Analyze metrics from ~/.claude/metrics/ directory."""

    def __init__(self, metrics_dir: str = None):
        if metrics_dir is None:
            metrics_dir = os.path.expanduser("~/.claude/metrics")
        self.metrics_dir = Path(metrics_dir)
        self.metrics_data: List[Dict[str, Any]] = []

    def load_metrics(self, date_str: str = None) -> bool:
        """Load metrics from date (YYYY-MM-DD). If None, use today."""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        date_path = self.metrics_dir / date_str
        if not date_path.exists():
            print(f"⚠️  No metrics found for {date_str}")
            return False

        self.metrics_data = []

        # Load per-task JSON files
        for json_file in date_path.glob("task_*.json"):
            try:
                with open(json_file) as f:
                    self.metrics_data.append(json.load(f))
            except json.JSONDecodeError:
                print(f"⚠️  Failed to parse {json_file}")
                continue

        # Load session JSONL
        session_file = date_path / "session.jsonl"
        if session_file.exists():
            try:
                with open(session_file) as f:
                    for line in f:
                        if line.strip():
                            self.metrics_data.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"⚠️  Failed to parse {session_file}")

        return len(self.metrics_data) > 0

    def analyze_by_role(self) -> Dict[str, Any]:
        """Analyze token usage and cost by role."""
        role_stats = defaultdict(
            lambda: {
                "tokens_in": 0,
                "tokens_out": 0,
                "cost": 0.0,
                "count": 0,
            }
        )

        for metric in self.metrics_data:
            if "role" not in metric:
                continue

            role = metric.get("role", "Unknown")
            tokens_in = metric.get("tokens_in", 0)
            tokens_out = metric.get("tokens_out", 0)
            cost = metric.get("cost", 0.0)

            role_stats[role]["tokens_in"] += tokens_in
            role_stats[role]["tokens_out"] += tokens_out
            role_stats[role]["cost"] += cost
            role_stats[role]["count"] += 1

        # Calculate percentages
        total_cost = sum(s["cost"] for s in role_stats.values())
        for role in role_stats:
            if total_cost > 0:
                role_stats[role]["percent"] = (
                    role_stats[role]["cost"] / total_cost * 100
                )
                role_stats[role]["target_percent"] = ROLE_TARGETS.get(role, 0) * 100
                role_stats[role]["variance"] = (
                    role_stats[role]["percent"] - role_stats[role]["target_percent"]
                )
            else:
                role_stats[role]["percent"] = 0
                role_stats[role]["target_percent"] = ROLE_TARGETS.get(role, 0) * 100
                role_stats[role]["variance"] = 0

        return dict(role_stats)

    def analyze_by_task_type(self) -> Dict[str, Any]:
        """Analyze token usage by task type."""
        task_stats = defaultdict(
            lambda: {
                "tokens": 0,
                "cost": 0.0,
                "count": 0,
            }
        )

        for metric in self.metrics_data:
            task_type = metric.get("task_type", "unknown")
            tokens = metric.get("tokens_in", 0) + metric.get("tokens_out", 0)
            cost = metric.get("cost", 0.0)

            task_stats[task_type]["tokens"] += tokens
            task_stats[task_type]["cost"] += cost
            task_stats[task_type]["count"] += 1

        # Sort by cost
        sorted_tasks = sorted(task_stats.items(), key=lambda x: x[1]["cost"], reverse=True)
        return {task: stats for task, stats in sorted_tasks[:5]}

    def find_outliers(self, percentile: float = 90.0) -> List[Dict[str, Any]]:
        """Find tasks in the Nth percentile by token usage."""
        if not self.metrics_data:
            return []

        # Calculate token usage per task
        tasks_with_tokens = [
            {
                **m,
                "total_tokens": m.get("tokens_in", 0) + m.get("tokens_out", 0),
            }
            for m in self.metrics_data
        ]

        if not tasks_with_tokens:
            return []

        tokens_list = [t["total_tokens"] for t in tasks_with_tokens]
        if len(tokens_list) < 2:
            return []

        # Calculate percentile threshold
        sorted_tokens = sorted(tokens_list)
        threshold_idx = max(0, int(len(sorted_tokens) * (percentile / 100.0)) - 1)
        threshold = sorted_tokens[threshold_idx]

        # Find outliers
        outliers = [
            t for t in tasks_with_tokens if t["total_tokens"] >= threshold
        ]

        return sorted(outliers, key=lambda x: x["total_tokens"], reverse=True)

    def generate_session_summary(self, date_str: str = None) -> str:
        """Generate a session summary report."""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        if not self.load_metrics(date_str):
            return f"No metrics available for {date_str}"

        if not self.metrics_data:
            return f"No task data found for {date_str}"

        # Calculate totals
        total_tokens = sum(
            m.get("tokens_in", 0) + m.get("tokens_out", 0)
            for m in self.metrics_data
        )
        total_cost = sum(m.get("cost", 0.0) for m in self.metrics_data)
        task_count = len([m for m in self.metrics_data if "task_id" in m])

        # Analyze by role
        role_analysis = self.analyze_by_role()

        # Analyze by task type
        task_analysis = self.analyze_by_task_type()

        # Find outliers
        outliers = self.find_outliers(percentile=90.0)

        # Build report
        report = []
        report.append("=== TokenAdvisor Session Summary ===\n")
        report.append(f"Date: {date_str}")
        report.append(f"Total tokens: {total_tokens:,.0f}")
        report.append(f"Total cost: ${total_cost:.2f}\n")

        # Role breakdown
        report.append("By role:")
        for role, stats in sorted(
            role_analysis.items(),
            key=lambda x: x[1]["cost"],
            reverse=True,
        ):
            percent = stats.get("percent", 0)
            target = stats.get("target_percent", 0)
            variance = stats.get("variance", 0)
            status = "✓" if abs(variance) <= 10 else "⚠"
            report.append(
                f"  {role}: ${stats['cost']:.2f} ({percent:.0f}%) "
                f"[target {target:.0f}%] {status}"
            )

        # Task type breakdown
        if task_analysis:
            report.append("\nTop task types:")
            for task_type, stats in task_analysis.items():
                report.append(
                    f"  {task_type}: ${stats['cost']:.2f} ({stats['count']} tasks)"
                )

        # Outliers
        if outliers:
            report.append("\nOutlier tasks (top 3):")
            for task in outliers[:3]:
                task_id = task.get("task_id", "unknown")
                tokens = task.get("total_tokens", 0)
                role = task.get("role", "unknown")
                task_type = task.get("task_type", "unknown")
                report.append(
                    f"  {task_id}: {tokens:,.0f} tokens "
                    f"({role}, {task_type})"
                )

        # Recommendations
        report.append("\nRecommendations:")
        inefficiencies = []

        # Check role variance
        for role, stats in role_analysis.items():
            variance = stats.get("variance", 0)
            if variance > 10:
                inefficiencies.append(
                    f"  • {role} usage is {variance:.0f}% over target "
                    f"({stats['percent']:.0f}% vs. {stats['target_percent']:.0f}%). "
                    f"Consider routing simpler tasks elsewhere."
                )
            elif variance < -10:
                inefficiencies.append(
                    f"  • {role} usage is {abs(variance):.0f}% under target. "
                    f"Opportunity to increase quality gate reviews."
                )

        if inefficiencies:
            report.extend(inefficiencies)
        else:
            report.append("  ✓ Role distribution within acceptable ranges")

        return "\n".join(report)

    def generate_daily_summary(self, date_str: str = None) -> str:
        """Generate a daily summary (across all sessions in a day)."""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        if not self.load_metrics(date_str):
            return f"No metrics available for {date_str}"

        if not self.metrics_data:
            return f"No task data found for {date_str}"

        # Calculate totals
        total_tokens = sum(
            m.get("tokens_in", 0) + m.get("tokens_out", 0)
            for m in self.metrics_data
        )
        total_cost = sum(m.get("cost", 0.0) for m in self.metrics_data)

        # Analyze
        role_analysis = self.analyze_by_role()

        # Build report
        report = []
        report.append(f"=== TokenAdvisor Daily Summary ({date_str}) ===\n")
        report.append(f"Total tokens: {total_tokens:,.0f}")
        report.append(f"Total cost: ${total_cost:.2f}")
        report.append(f"Tasks completed: {len(self.metrics_data)}\n")

        report.append("By role (actual vs. target):")
        for role, stats in sorted(
            role_analysis.items(),
            key=lambda x: x[1]["cost"],
            reverse=True,
        ):
            percent = stats.get("percent", 0)
            target = stats.get("target_percent", 0)
            variance = stats.get("variance", 0)
            status = "✓" if abs(variance) <= 10 else "⚠"
            report.append(
                f"  {role}: ${stats['cost']:.2f} ({percent:.1f}%) "
                f"[target {target:.1f}%] {status}"
            )

        # Efficiency metrics
        avg_cost_per_task = total_cost / len(self.metrics_data) if self.metrics_data else 0
        report.append(f"\nEfficiency metrics:")
        report.append(f"  Avg cost per task: ${avg_cost_per_task:.2f}")

        return "\n".join(report)


def main():
    """Main entry point."""
    import argparse
    import time

    start_time = time.time()

    parser = argparse.ArgumentParser(
        description="TokenAdvisor — Daily metrics analysis"
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Analyze metrics for specific date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--summary", action="store_true", help="Generate session summary"
    )
    parser.add_argument(
        "--daily", action="store_true", help="Generate daily summary"
    )
    parser.add_argument(
        "--metrics-dir",
        default=os.path.expanduser("~/.claude/metrics"),
        help="Path to metrics directory",
    )

    args = parser.parse_args()

    analyzer = MetricsAnalyzer(metrics_dir=args.metrics_dir)

    # Default to daily summary if no format specified
    if not args.summary and not args.daily:
        args.daily = True

    if args.daily:
        report = analyzer.generate_daily_summary(args.date)
    else:
        report = analyzer.generate_session_summary(args.date)

    print(report)

    # Generate structured JSON for queue processing
    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    if analyzer.metrics_data:
        role_analysis = analyzer.analyze_by_role()

        # Detect alerts based on variance
        alerts = []
        for role, stats in role_analysis.items():
            variance = stats.get("variance", 0)
            if variance > 10:
                alerts.append({
                    "severity": "warning",
                    "message": f"{role} usage is {variance:.0f}% over target ({stats['percent']:.0f}% vs. {stats['target_percent']:.0f}%)",
                    "action": "review_routing",
                    "should_email": True,
                    "should_voice": False
                })
            elif variance < -10:
                alerts.append({
                    "severity": "info",
                    "message": f"{role} usage is {abs(variance):.0f}% under target",
                    "action": "increase_quality_gate",
                    "should_email": False,
                    "should_voice": False
                })

        structured_log = {
            "timestamp": datetime.now().isoformat() + "Z",
            "job": "tokenadvisor",
            "status": "success",
            "duration_seconds": int(time.time() - start_time),
            "metrics": {
                "roles_analyzed": len(role_analysis),
                "inefficiencies_found": len([a for a in alerts if a["severity"] == "warning"]),
                "outliers_flagged": len(analyzer.find_outliers())
            },
            "alerts": alerts,
            "feeds_to": "model-engineer"
        }

        print("\n===== STRUCTURED LOG =====")
        print(json.dumps(structured_log, indent=2))
        print("===== END STRUCTURED LOG =====")

        # Write alerts to queue for processing
        queue_dir = Path("agentic-engineers/data/logs/QUEUE/pending")
        queue_dir.mkdir(parents=True, exist_ok=True)

        for i, alert in enumerate(alerts):
            timestamp = datetime.now().isoformat().replace(":", "-").replace(".", "-")
            alert_file = queue_dir / f"alert-tokenadvisor-{timestamp}-{i}.json"
            alert["job"] = "tokenadvisor"
            alert["timestamp"] = datetime.now().isoformat() + "Z"
            with open(alert_file, "w") as f:
                json.dump(alert, f, indent=2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
