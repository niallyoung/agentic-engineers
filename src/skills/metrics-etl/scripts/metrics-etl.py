"""
Metrics ETL Pipeline — Aggregate token metrics for analysis

Reads metrics from ~/.claude/metrics/ and aggregates into JSON format
for local analysis and reporting.

Usage:
    ./metrics-etl.py --aggregate [--days 7]
    ./metrics-etl.py --export json [--output metrics.json]
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Any, Dict, List

# Prometheus text format template
PROMETHEUS_FORMAT = """{help}
{metric_lines}"""


class MetricsETL:
    """Extract, transform, and load metrics for dashboards."""

    def __init__(self, metrics_dir: str = None):
        if metrics_dir is None:
            metrics_dir = os.path.expanduser("~/.claude/metrics")
        self.metrics_dir = Path(metrics_dir)
        self.aggregated: Dict[str, Any] = {}

    def aggregate_metrics(self, days: int = 7) -> Dict[str, Any]:
        """Aggregate metrics from the past N days."""
        self.aggregated = defaultdict(
            lambda: {
                "total_tokens": 0,
                "total_cost": 0.0,
                "quality_scores": [],
                "role_breakdown": defaultdict(lambda: {"tokens": 0, "cost": 0.0, "count": 0}),
                "model_breakdown": defaultdict(lambda: {"tokens": 0, "cost": 0.0, "count": 0}),
                "task_types": defaultdict(lambda: {"tokens": 0, "cost": 0.0, "count": 0}),
            }
        )

        # Iterate through past N days
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            date_path = self.metrics_dir / date

            if not date_path.exists():
                continue

            # Load per-task JSON files
            for json_file in date_path.glob("task_*.json"):
                try:
                    with open(json_file) as f:
                        metric = json.load(f)

                    tokens = metric.get("tokens_in", 0) + metric.get("tokens_out", 0)
                    cost = metric.get("cost", 0.0)
                    role = metric.get("role", "unknown")
                    model = metric.get("model", "unknown")
                    task_type = metric.get("task_type", "unknown")
                    quality = metric.get("quality_score", 0.0)

                    # Aggregate by date
                    self.aggregated[date]["total_tokens"] += tokens
                    self.aggregated[date]["total_cost"] += cost
                    self.aggregated[date]["quality_scores"].append(quality)
                    self.aggregated[date]["role_breakdown"][role]["tokens"] += tokens
                    self.aggregated[date]["role_breakdown"][role]["cost"] += cost
                    self.aggregated[date]["role_breakdown"][role]["count"] += 1
                    self.aggregated[date]["model_breakdown"][model]["tokens"] += tokens
                    self.aggregated[date]["model_breakdown"][model]["cost"] += cost
                    self.aggregated[date]["model_breakdown"][model]["count"] += 1
                    self.aggregated[date]["task_types"][task_type]["tokens"] += tokens
                    self.aggregated[date]["task_types"][task_type]["cost"] += cost
                    self.aggregated[date]["task_types"][task_type]["count"] += 1

                except (json.JSONDecodeError, KeyError):
                    continue

        # Calculate averages
        for date_data in self.aggregated.values():
            if date_data["quality_scores"]:
                date_data["avg_quality"] = sum(date_data["quality_scores"]) / len(
                    date_data["quality_scores"]
                )
                date_data.pop("quality_scores")
            else:
                date_data["avg_quality"] = 0.0

        return dict(self.aggregated)

    def export_json_format(self) -> str:
        """Export aggregated metrics as JSON."""
        return json.dumps(self.aggregated, indent=2, default=str)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Metrics ETL Pipeline for dashboards"
    )
    parser.add_argument(
        "--aggregate",
        action="store_true",
        help="Aggregate metrics from past N days",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to aggregate (default 7)",
    )
    parser.add_argument(
        "--export",
        choices=["json"],
        help="Export format",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file (default stdout)",
    )
    parser.add_argument(
        "--metrics-dir",
        default=os.path.expanduser("~/.claude/metrics"),
        help="Path to metrics directory",
    )

    args = parser.parse_args()

    etl = MetricsETL(metrics_dir=args.metrics_dir)
    etl.aggregate_metrics(args.days)

    # Export
    if args.export == "json":
        output = etl.export_json_format()
    else:
        # Default: show aggregated data summary
        agg = etl.aggregated
        lines = []
        lines.append(f"=== Metrics Aggregation ({args.days} days) ===\n")
        lines.append("Daily Summary:")
        for date in sorted(agg.keys(), reverse=True):
            data = agg[date]
            lines.append(
                f"  {date}: {data['total_tokens']:,} tokens, "
                f"${data['total_cost']:.2f}, quality {data['avg_quality']:.0f}%"
            )
        output = "\n".join(lines)

    # Output
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"✓ Exported to {args.output}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
