# -*- coding: utf-8 -*-
"""
A/B Testing Framework - Automated experiment orchestration and analysis

Tests changes to task routing, model allocation, and role assignments.
Handles traffic allocation, metric collection, statistical analysis, and early stopping.

Usage:
    ./ab-testing.py --create --name "test-name" --hypothesis "..." --duration 7
    ./ab-testing.py --start EXPERIMENT_ID
    ./ab-testing.py --stop EXPERIMENT_ID [--winner control|variant]
    ./ab-testing.py --analyze EXPERIMENT_ID
    ./ab-testing.py --list [--status running|completed]
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

EXPERIMENTS_DIR = Path(os.path.expanduser("~/.claude/experiments"))


class ExperimentStatus(Enum):
    """Experiment lifecycle statuses."""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Experiment:
    """A/B Test experiment definition."""

    id: str
    name: str
    hypothesis: str
    control: Dict[str, Any]  # Current configuration
    variant: Dict[str, Any]  # New configuration to test
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_days: int = 7
    traffic_split: float = 0.5  # 50/50 split by default
    status: str = ExperimentStatus.DRAFT.value
    created_at: str = None
    updated_at: str = None
    hypothesis_accepted: Optional[bool] = None
    notes: str = ""

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()


class ABTestingFramework:
    """Orchestrate and analyze A/B testing experiments."""

    def __init__(self):
        EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)

    def create_experiment(
        self,
        name: str,
        hypothesis: str,
        control: Dict[str, Any],
        variant: Dict[str, Any],
        duration_days: int = 7,
        traffic_split: float = 0.5,
    ) -> str:
        """Create a new experiment definition."""
        # Generate experiment ID from name + hash
        name_hash = hashlib.md5(
            (name + datetime.now().isoformat()).encode()
        ).hexdigest()[:8]
        experiment_id = f"{name.lower().replace(' ', '-')}-{name_hash}"

        experiment = Experiment(
            id=experiment_id,
            name=name,
            hypothesis=hypothesis,
            control=control,
            variant=variant,
            duration_days=duration_days,
            traffic_split=traffic_split,
        )

        exp_file = EXPERIMENTS_DIR / f"{experiment_id}.json"
        with open(exp_file, "w") as f:
            json.dump(asdict(experiment), f, indent=2)

        return experiment_id

    def load_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Load experiment from file."""
        exp_file = EXPERIMENTS_DIR / f"{experiment_id}.json"
        if not exp_file.exists():
            return None

        with open(exp_file) as f:
            data = json.load(f)

        return Experiment(**data)

    def start_experiment(self, experiment_id: str) -> bool:
        """Start an experiment (move to running status)."""
        exp = self.load_experiment(experiment_id)
        if not exp:
            return False

        if exp.status != ExperimentStatus.DRAFT.value:
            print(f"❌ Cannot start experiment in {exp.status} status")
            return False

        exp.status = ExperimentStatus.RUNNING.value
        exp.start_date = datetime.now().isoformat()
        exp.end_date = (
            datetime.now() + timedelta(days=exp.duration_days)
        ).isoformat()
        exp.updated_at = datetime.now().isoformat()

        self._save_experiment(exp)
        return True

    def stop_experiment(
        self, experiment_id: str, winner: Optional[str] = None
    ) -> bool:
        """Stop an experiment and record result."""
        exp = self.load_experiment(experiment_id)
        if not exp:
            return False

        if exp.status != ExperimentStatus.RUNNING.value:
            print(f"❌ Cannot stop experiment in {exp.status} status")
            return False

        # Analyze results
        analysis = self.analyze_experiment(experiment_id)

        if winner in ["control", "variant"]:
            exp.hypothesis_accepted = winner == "variant"
        else:
            # Auto-determine winner if not specified
            if analysis["significance"] and analysis["variant_better"]:
                exp.hypothesis_accepted = True
                winner = "variant"
            else:
                exp.hypothesis_accepted = False
                winner = "control"

        exp.status = ExperimentStatus.COMPLETED.value
        exp.updated_at = datetime.now().isoformat()
        exp.notes = f"Concluded: {winner} is winner (p={analysis['significance']:.4f})"

        self._save_experiment(exp)
        return True

    def analyze_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """Analyze experiment results and compute statistics."""
        exp = self.load_experiment(experiment_id)
        if not exp:
            return {}

        # Collect metrics for control and variant groups
        control_metrics = self._collect_group_metrics(experiment_id, "control")
        variant_metrics = self._collect_group_metrics(experiment_id, "variant")

        if not control_metrics or not variant_metrics:
            return {
                "status": "insufficient_data",
                "control_count": len(control_metrics),
                "variant_count": len(variant_metrics),
            }

        # Calculate statistics
        control_quality = [m.get("quality_score", 0) for m in control_metrics]
        control_cost = [m.get("cost", 0) for m in control_metrics]
        variant_quality = [m.get("quality_score", 0) for m in variant_metrics]
        variant_cost = [m.get("cost", 0) for m in variant_metrics]

        avg_control_quality = sum(control_quality) / len(control_quality)
        avg_variant_quality = sum(variant_quality) / len(variant_quality)
        avg_control_cost = sum(control_cost) / len(control_cost)
        avg_variant_cost = sum(variant_cost) / len(variant_cost)

        # T-test for significance (simplified)
        pvalue = self._ttest_pvalue(control_quality, variant_quality)

        return {
            "control_count": len(control_metrics),
            "variant_count": len(variant_metrics),
            "control_avg_quality": avg_control_quality,
            "variant_avg_quality": avg_variant_quality,
            "quality_improvement": (
                (avg_variant_quality - avg_control_quality)
                / avg_control_quality
                * 100
            ),
            "control_avg_cost": avg_control_cost,
            "variant_avg_cost": avg_variant_cost,
            "cost_reduction": (
                (avg_control_cost - avg_variant_cost) / avg_control_cost * 100
            ),
            "significance": pvalue,
            "significant": pvalue < 0.05,
            "variant_better": avg_variant_quality > avg_control_quality
            and avg_variant_cost < avg_control_cost,
            "power": min(len(control_metrics), len(variant_metrics)) / 100.0,
        }

    def generate_report(self, experiment_id: str) -> str:
        """Generate experiment results report."""
        exp = self.load_experiment(experiment_id)
        if not exp:
            return f"Experiment {experiment_id} not found"

        analysis = self.analyze_experiment(experiment_id)

        report = []
        report.append(f"=== A/B Test Report: {exp.name} ===\n")
        report.append(f"Experiment ID: {experiment_id}")
        report.append(f"Status: {exp.status}")
        report.append(f"Duration: {exp.duration_days} days")
        report.append(f"Hypothesis: {exp.hypothesis}\n")

        if analysis.get("status") == "insufficient_data":
            report.append(
                "⚠️  Insufficient data:"
                f" Control={analysis['control_count']}, Variant={analysis['variant_count']}"
            )
            return "\n".join(report)

        report.append("Results:")
        report.append(
            f"  Control: {analysis['control_count']} tasks, "
            f"avg quality {analysis['control_avg_quality']:.1f}%, "
            f"cost ${analysis['control_avg_cost']:.3f}"
        )
        report.append(
            f"  Variant: {analysis['variant_count']} tasks, "
            f"avg quality {analysis['variant_avg_quality']:.1f}%, "
            f"cost ${analysis['variant_avg_cost']:.3f}"
        )

        report.append("\nImpact:")
        report.append(
            f"  Quality: {analysis['quality_improvement']:+.1f}% "
            f"(p={analysis['significance']:.4f})"
        )
        report.append(
            f"  Cost: {analysis['cost_reduction']:+.1f}% reduction"
        )

        report.append("\nConclusion:")
        if exp.hypothesis_accepted is None:
            report.append("  Experiment in progress or not concluded")
        elif exp.hypothesis_accepted:
            report.append(
                "  ✓ Hypothesis ACCEPTED — variant is better, apply to production"
            )
        else:
            report.append(
                "  ✗ Hypothesis REJECTED — control is better, keep current"
            )

        return "\n".join(report)

    def list_experiments(self, status: Optional[str] = None) -> List[Experiment]:
        """List all experiments, optionally filtered by status."""
        experiments = []
        for exp_file in EXPERIMENTS_DIR.glob("*.json"):
            exp = self.load_experiment(exp_file.stem)
            if exp:
                if status is None or exp.status == status:
                    experiments.append(exp)
        return sorted(
            experiments, key=lambda x: x.created_at, reverse=True
        )

    # Private methods

    def _save_experiment(self, exp: Experiment):
        """Save experiment to file."""
        exp_file = EXPERIMENTS_DIR / f"{exp.id}.json"
        with open(exp_file, "w") as f:
            json.dump(asdict(exp), f, indent=2)

    def _collect_group_metrics(
        self, experiment_id: str, group: str
    ) -> List[Dict[str, Any]]:
        """Collect metrics for control or variant group."""
        metrics_dir = Path(os.path.expanduser("~/.claude/metrics"))
        metrics = []

        for date_dir in sorted(metrics_dir.glob("*"))[:7]:  # Last 7 days
            for json_file in date_dir.glob("task_*.json"):
                try:
                    with open(json_file) as f:
                        metric = json.load(f)

                    # Check if metric belongs to this experiment group
                    if metric.get("experiment_id") == experiment_id:
                        if metric.get("experiment_group") == group:
                            metrics.append(metric)
                except (json.JSONDecodeError, KeyError):
                    continue

        return metrics

    def _ttest_pvalue(
        self, group1: List[float], group2: List[float]
    ) -> float:
        """Simplified t-test p-value calculation."""
        if not group1 or not group2:
            return 1.0

        import statistics

        try:
            mean1 = statistics.mean(group1)
            mean2 = statistics.mean(group2)
            stdev1 = statistics.stdev(group1) if len(group1) > 1 else 0
            stdev2 = statistics.stdev(group2) if len(group2) > 1 else 0

            if stdev1 == 0 and stdev2 == 0:
                return 0.0 if mean1 != mean2 else 1.0

            # Simplified t-test (Welch's approximation)
            se = (
                (stdev1 ** 2 / len(group1) + stdev2 ** 2 / len(group2))
                ** 0.5
            )
            if se == 0:
                return 1.0

            t = (mean1 - mean2) / se

            # Approximate p-value from t-distribution
            # For df >= 30, approximately normal
            from math import erf

            p = (
                1 - erf(abs(t) / (2 ** 0.5)) / 2
            )  # Two-tailed
            return max(0.0, min(1.0, p))
        except Exception:
            return 1.0


def main():
    """Main entry point."""
    import argparse
    import time

    start_time = time.time()

    parser = argparse.ArgumentParser(description="A/B Testing Framework")
    parser.add_argument("--create", action="store_true", help="Create new experiment")
    parser.add_argument("--name", help="Experiment name")
    parser.add_argument("--hypothesis", help="Hypothesis to test")
    parser.add_argument("--duration", type=int, default=7, help="Duration in days")
    parser.add_argument("--start", metavar="ID", help="Start experiment by ID")
    parser.add_argument("--stop", metavar="ID", help="Stop experiment by ID")
    parser.add_argument(
        "--winner",
        choices=["control", "variant"],
        help="Override winner determination",
    )
    parser.add_argument("--analyze", metavar="ID", help="Analyze experiment by ID")
    parser.add_argument("--monitor", action="store_true", help="Monitor active experiments")
    parser.add_argument("--list", action="store_true", help="List all experiments")
    parser.add_argument(
        "--status",
        choices=["draft", "running", "completed"],
        help="Filter by status",
    )

    args = parser.parse_args()

    framework = ABTestingFramework()

    if args.create:
        if not args.name or not args.hypothesis:
            print("❌ --create requires --name and --hypothesis")
            return 1

        exp_id = framework.create_experiment(
            name=args.name,
            hypothesis=args.hypothesis,
            control={"current": "configuration"},
            variant={"proposed": "configuration"},
            duration_days=args.duration,
        )
        print(f"✓ Created experiment: {exp_id}")
        return 0

    if args.start:
        if framework.start_experiment(args.start):
            print(f"✓ Started experiment: {args.start}")
            return 0
        else:
            print(f"❌ Failed to start experiment: {args.start}")
            return 1

    if args.stop:
        if framework.stop_experiment(args.stop, args.winner):
            report = framework.generate_report(args.stop)
            print(report)
            return 0
        else:
            print(f"❌ Failed to stop experiment: {args.stop}")
            return 1

    if args.analyze:
        report = framework.generate_report(args.analyze)
        print(report)
        return 0

    if args.monitor:
        # Monitor active experiments for early stopping signals
        exps = framework.list_experiments(status="running")

        alerts = []
        report = []
        report.append("=== A/B Testing Monitor ===\n")
        report.append(f"Monitoring {len(exps)} active experiments\n")

        for exp in exps:
            analysis = framework.analyze_experiment(exp.id)

            if analysis.get("status") == "insufficient_data":
                report.append(f"⏳ {exp.name}: Insufficient data ({analysis['variant_count']} samples)")
                continue

            report.append(f"▶ {exp.name}:")
            report.append(f"  Quality: {analysis['quality_improvement']:+.1f}% (p={analysis['significance']:.4f})")
            report.append(f"  Cost: {analysis['cost_reduction']:+.1f}%")

            # Check for early stopping signals
            if analysis.get("significant"):
                if analysis.get("variant_better"):
                    alerts.append({
                        "severity": "info",
                        "message": f"Experiment {exp.name}: Variant winning (p={analysis['significance']:.4f})",
                        "action": "consider_early_stop",
                        "should_email": True,
                        "should_voice": True
                    })
                    report.append(f"  ✓ SIGNIFICANT: Variant is better, consider early stop")
                else:
                    alerts.append({
                        "severity": "warning",
                        "message": f"Experiment {exp.name}: Control winning (variant underperforming)",
                        "action": "consider_rollback",
                        "should_email": True,
                        "should_voice": True
                    })
                    report.append(f"  ✗ SIGNIFICANT: Control is better, consider rollback")

        print("\n".join(report))

        # Generate structured JSON for queue processing
        structured_log = {
            "timestamp": datetime.now().isoformat() + "Z",
            "job": "ab-testing-monitor",
            "status": "success",
            "duration_seconds": int(time.time() - start_time),
            "metrics": {
                "experiments_monitored": len(exps),
                "significant_results": len([a for a in alerts if a["severity"] in ["warning", "info"]])
            },
            "alerts": alerts,
            "feeds_to": "decision-maker"
        }

        print("\n===== STRUCTURED LOG =====")
        print(json.dumps(structured_log, indent=2))
        print("===== END STRUCTURED LOG =====")

        # Write alerts to queue for processing
        queue_dir = Path("agentic-engineers/data/logs/QUEUE/pending")
        queue_dir.mkdir(parents=True, exist_ok=True)

        for i, alert in enumerate(alerts):
            timestamp = datetime.now().isoformat().replace(":", "-").replace(".", "-")
            alert_file = queue_dir / f"alert-ab-testing-{timestamp}-{i}.json"
            alert["job"] = "ab-testing"
            alert["timestamp"] = datetime.now().isoformat() + "Z"
            with open(alert_file, "w") as f:
                json.dump(alert, f, indent=2)

        return 0

    if args.list:
        exps = framework.list_experiments(status=args.status)
        if not exps:
            print("No experiments found")
            return 0

        for exp in exps:
            print(f"{exp.id}: {exp.name} ({exp.status})")

        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
