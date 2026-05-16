#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
daily-model-optimization.py — Daily model selection optimization script.

Runs the full optimization pipeline:
  1. Load today's task metrics
  2. Analyze cost-quality tradeoffs
  3. Generate recommendations
  4. Propose A/B tests for top recommendations
  5. Output structured JSON for queue processing

Usage:
    python scripts/daily-model-optimization.py [--date YYYY-MM-DD] [--metrics-dir PATH]
    python scripts/daily-model-optimization.py --dry-run
    python scripts/daily-model-optimization.py --complexity-demo

Cron (daily at 17:30 UTC, after tokenadvisor at 17:00):
    30 17 * * * cd ~/git/agentic-engineers && python src/orchestration/models/scripts/daily-model-optimization.py
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.orchestration.models import (
    ComplexityScorer,
    CostQualityAnalyzer,
    ModelSelector,
    RecommendationsEngine,
    TaskAttributes,
)
from src.orchestration.models.ab_testing import ABTestingFramework


def load_metrics_from_dir(metrics_dir: str, date_str: str) -> list:
    """Load task metrics from ~/.claude/metrics/YYYY-MM-DD/task_*.json"""
    base = Path(metrics_dir) / date_str
    if not base.exists():
        return []

    records = []
    for json_file in base.glob("task_*.json"):
        try:
            with open(json_file) as f:
                records.append(json.load(f))
        except (json.JSONDecodeError, OSError):
            continue

    # Also load session JSONL
    session_file = base / "session.jsonl"
    if session_file.exists():
        try:
            with open(session_file) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            records.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except OSError:
            pass

    return records


def complexity_demo():
    """Demonstrate complexity scoring with example tasks."""
    scorer = ComplexityScorer()
    selector = ModelSelector(scorer)

    examples = [
        ("Simple routing decision", TaskAttributes(
            effort="low", task_type="routing", estimated_tokens=500)),
        ("Standard implementation", TaskAttributes(
            effort="medium", task_type="implementation", estimated_tokens=10_000)),
        ("Complex refactor (no plan)", TaskAttributes(
            effort="high", task_type="refactor", has_plan=False,
            scope_clarity=0.5, num_files_affected=8, estimated_tokens=30_000)),
        ("Architectural decision", TaskAttributes(
            effort="max", task_type="architecture", is_cross_service=True,
            has_plan=False, scope_clarity=0.3, estimated_tokens=80_000)),
        ("Security audit", TaskAttributes(
            effort="high", task_type="security", security_sensitive=True,
            estimated_tokens=20_000)),
    ]

    print("=== Complexity Scoring Demo ===\n")
    for name, attrs in examples:
        score, level = scorer.score(attrs)
        decision = selector.select(attrs)
        cost = selector.estimate_cost(attrs)
        print(f"Task: {name}")
        print(f"  Score: {score:.1f}/100  Level: {level.value.upper()}")
        print(f"  → Model: {decision.model_id}  Cost: ${cost:.4f}  "
              f"Quality baseline: {decision.quality_baseline:.0f}%")
        if decision.override_applied:
            print(f"  ⚡ Override: {decision.override_reason}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Daily Model Selection Optimization")
    parser.add_argument("--date", default=None, help="Date to analyze (YYYY-MM-DD)")
    parser.add_argument(
        "--metrics-dir",
        default=os.path.expanduser("~/.claude/metrics"),
        help="Path to metrics directory",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without writing files")
    parser.add_argument("--complexity-demo", action="store_true", help="Show complexity scoring examples")
    parser.add_argument("--output-dir", default=None, help="Write JSON report to this directory")
    args = parser.parse_args()

    if args.complexity_demo:
        complexity_demo()
        return 0

    start_time = time.time()
    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    print(f"=== Daily Model Selection Optimization: {date_str} ===\n")

    # 1. Load metrics
    metrics = load_metrics_from_dir(args.metrics_dir, date_str)
    print(f"Loaded {len(metrics)} task metrics from {args.metrics_dir}/{date_str}")

    if not metrics:
        print("⚠  No metrics available. Using synthetic demo data for report structure.")
        # Generate synthetic data for demonstration
        import random
        random.seed(42)
        metrics = []
        for i in range(50):
            role = random.choice(["Engineer", "Senior Engineer", "Lead Engineer"])
            model = {"Engineer": "haiku-4-5", "Senior Engineer": "sonnet-4-6", "Lead Engineer": "sonnet-4-6"}[role]
            complexity = random.uniform(10, 80)
            metrics.append({
                "role": role,
                "model": model,
                "quality_score": random.uniform(75, 98),
                "cost": random.uniform(0.0001, 0.005),
                "tokens_in": random.randint(500, 10_000),
                "tokens_out": random.randint(200, 5_000),
                "complexity_score": complexity,
                "escalated": random.random() < 0.08,
            })
        print(f"  Using {len(metrics)} synthetic records for demonstration.\n")

    # 2. Run recommendations engine
    engine = RecommendationsEngine()
    engine.load_metrics(metrics)
    report = engine.generate_daily_report(date=date_str)

    # 3. Print summary
    print(report["summary"])

    # 4. Show A/B test proposals
    proposals = report["ab_test_proposals"]
    if proposals:
        print(f"\n=== A/B Test Proposals ({len(proposals)}) ===")
        for i, proposal in enumerate(proposals, 1):
            print(f"\n{i}. {proposal['name']}")
            print(f"   Hypothesis: {proposal['hypothesis']}")
            print(f"   Control: {proposal['control']}")
            print(f"   Variant: {proposal['variant']}")
            print(f"   Duration: {proposal['duration_days']} days")

    # 5. Build structured output
    duration = int(time.time() - start_time)
    efficiency = report["efficiency_report"]
    recs = report["recommendations"]

    alerts = []
    for rec in recs:
        if rec.priority <= 2:
            alerts.append({
                "severity": "warning" if rec.type.value == "upgrade" else "info",
                "message": f"{rec.role}: {rec.type.value} {rec.current_model} → {rec.proposed_model}",
                "action": rec.type.value,
                "confidence": rec.confidence,
                "rationale": rec.rationale,
                "should_email": rec.priority == 1,
                "should_voice": False,
            })

    structured_log = {
        "timestamp": datetime.now().isoformat() + "Z",
        "job": "daily-model-optimization",
        "date": date_str,
        "status": "success",
        "duration_seconds": duration,
        "metrics": {
            "tasks_analyzed": efficiency.total_tasks,
            "total_cost": round(efficiency.total_cost, 6),
            "avg_cost_per_quality": round(efficiency.avg_cost_per_quality, 6),
            "recommendations_generated": len(recs),
            "high_priority_recommendations": len([r for r in recs if r.priority <= 2]),
            "ab_test_proposals": len(proposals),
            "over_provisioned_tasks": len(efficiency.over_provisioned_tasks),
            "under_provisioned_tasks": len(efficiency.under_provisioned_tasks),
            "outliers": len(efficiency.outliers),
        },
        "alerts": alerts,
        "recommendations": [
            {
                "type": r.type.value,
                "role": r.role,
                "current_model": r.current_model,
                "proposed_model": r.proposed_model,
                "confidence": r.confidence,
                "cost_delta_pct": r.estimated_cost_delta_pct,
                "quality_delta_pct": r.estimated_quality_delta_pct,
                "priority": r.priority,
            }
            for r in recs
        ],
        "feeds_to": "ab-testing",
    }

    print("\n===== STRUCTURED LOG =====")
    print(json.dumps(structured_log, indent=2))
    print("===== END STRUCTURED LOG =====")

    if not args.dry_run:
        # Write to queue
        queue_dir = Path("data/logs/QUEUE/pending")
        queue_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().isoformat().replace(":", "-").replace(".", "-")

        for i, alert in enumerate(alerts):
            alert_file = queue_dir / f"alert-model-optimization-{ts}-{i}.json"
            alert["job"] = "daily-model-optimization"
            alert["timestamp"] = datetime.now().isoformat() + "Z"
            with open(alert_file, "w") as f:
                json.dump(alert, f, indent=2)

        # Write full report
        if args.output_dir:
            out_dir = Path(args.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            report_file = out_dir / f"model-optimization-{date_str}.json"
            with open(report_file, "w") as f:
                json.dump(structured_log, f, indent=2)
            print(f"\n✓ Report written to {report_file}")

        if alerts:
            print(f"\n✓ {len(alerts)} alert(s) written to queue")
    else:
        print("\n[dry-run] No files written.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
