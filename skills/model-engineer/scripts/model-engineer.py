#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Model Engineer - Feedback Loop for Task Routing Optimization

Analyzes token usage, quality metrics, and cost data to recommend optimal
model/role assignments. Continuously optimizes task routing based on performance.

Usage:
    ./model-engineer.py --analyze [--date YYYY-MM-DD]
    ./model-engineer.py --recommend [--complexity low|medium|high|max]
    ./model-engineer.py --simulate --changes role=NEW_MODEL
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Any, Dict, List, Tuple, Optional

# Model assignments from config (should read from actual config file)
MODEL_TIERS = {
    "haiku-4-5": {"cost": 0.00008, "quality_baseline": 85, "effort_suitability": ["low", "medium"]},
    "sonnet-4-6": {"cost": 0.0003, "quality_baseline": 93, "effort_suitability": ["medium", "high", "max"]},
    "opus-4-7": {"cost": 0.00015, "quality_baseline": 96, "effort_suitability": ["high", "max"], "premium": True},
}

ROLE_ASSIGNMENTS = {
    "Engineer": {"model": "haiku-4-5", "effort": "low"},
    "Senior Engineer": {"model": "sonnet-4-6", "effort": "medium"},
    "Lead Engineer": {"model": "sonnet-4-6", "effort": "high"},
    "Principal Engineer": {"model": "opus-4-7", "effort": "max"},
}

# Cost targets
COST_TARGET_PER_QUALITY = 0.0016  # Optimal cost per quality point


class ModelEngineer:
    """Optimize task routing based on metrics and quality."""

    def __init__(self, metrics_dir: str = None):
        if metrics_dir is None:
            metrics_dir = os.path.expanduser("~/.claude/metrics")
        self.metrics_dir = Path(metrics_dir)
        self.metrics_data: List[Dict[str, Any]] = []

    def load_metrics(self, date_str: str = None) -> bool:
        """Load metrics from date."""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        date_path = self.metrics_dir / date_str
        if not date_path.exists():
            return False

        self.metrics_data = []

        # Load per-task JSON files
        for json_file in date_path.glob("task_*.json"):
            try:
                with open(json_file) as f:
                    self.metrics_data.append(json.load(f))
            except json.JSONDecodeError:
                continue

        return len(self.metrics_data) > 0

    def analyze_cost_quality_tradeoff(self) -> Dict[str, Any]:
        """Analyze cost vs. quality for each role/model combination."""
        role_stats = defaultdict(
            lambda: {
                "total_tokens": 0,
                "total_cost": 0.0,
                "quality_score": 0.0,
                "count": 0,
                "escalations": 0,
            }
        )

        for metric in self.metrics_data:
            role = metric.get("role", "Unknown")
            tokens = metric.get("tokens_in", 0) + metric.get("tokens_out", 0)
            cost = metric.get("cost", 0.0)
            quality = metric.get("quality_score", 0.0)
            escalated = metric.get("escalated", False)

            role_stats[role]["total_tokens"] += tokens
            role_stats[role]["total_cost"] += cost
            role_stats[role]["quality_score"] += quality
            role_stats[role]["count"] += 1
            if escalated:
                role_stats[role]["escalations"] += 1

        # Calculate averages and efficiency
        analysis = {}
        for role, stats in role_stats.items():
            count = stats["count"]
            avg_quality = stats["quality_score"] / count if count > 0 else 0
            cost_per_quality = stats["total_cost"] / avg_quality if avg_quality > 0 else float("inf")
            escalation_rate = stats["escalations"] / count if count > 0 else 0

            analysis[role] = {
                "avg_quality": avg_quality,
                "cost_per_quality": cost_per_quality,
                "escalation_rate": escalation_rate,
                "total_cost": stats["total_cost"],
                "task_count": count,
                "efficiency": "good"
                if cost_per_quality < COST_TARGET_PER_QUALITY * 1.1
                else "fair"
                if cost_per_quality < COST_TARGET_PER_QUALITY * 1.3
                else "poor",
            }

        return analysis

    def recommend_routing(
        self, complexity: str = "medium", task_type: str = "general"
    ) -> Dict[str, Any]:
        """Recommend best role/model for a task based on complexity and historical data."""
        analysis = self.analyze_cost_quality_tradeoff()

        # Determine required effort level
        effort_map = {
            "low": ["Engineer"],
            "medium": ["Engineer", "Senior Engineer"],
            "high": ["Senior Engineer", "Lead Engineer"],
            "max": ["Lead Engineer", "Principal Engineer"],
        }

        candidate_roles = effort_map.get(complexity, ["Senior Engineer"])

        # Score candidates by cost-effectiveness
        recommendations = []
        for role in candidate_roles:
            if role in analysis:
                stats = analysis[role]
                score = 100.0  # Base score

                # Adjust for quality
                if stats["avg_quality"] < 80:
                    score -= 20

                # Adjust for cost efficiency
                if stats["efficiency"] == "good":
                    score += 10
                elif stats["efficiency"] == "poor":
                    score -= 10

                # Adjust for escalation rate
                if stats["escalation_rate"] > 0.1:
                    score -= 15

                recommendations.append({
                    "role": role,
                    "score": max(0, score),
                    "quality": stats["avg_quality"],
                    "cost_per_quality": stats["cost_per_quality"],
                    "escalation_rate": stats["escalation_rate"],
                })

        # Sort by score
        recommendations.sort(key=lambda x: x["score"], reverse=True)

        return {
            "complexity": complexity,
            "task_type": task_type,
            "top_recommendation": recommendations[0] if recommendations else None,
            "alternatives": recommendations[1:3] if len(recommendations) > 1 else [],
        }

    def generate_optimization_report(self, date_str: str = None) -> str:
        """Generate optimization recommendations."""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        if not self.load_metrics(date_str):
            return f"No metrics available for {date_str}"

        analysis = self.analyze_cost_quality_tradeoff()

        if not analysis:
            return "No task data found"

        report = []
        report.append("=== Model Engineer Optimization Report ===\n")
        report.append(f"Date: {date_str}\n")

        # Current state
        report.append("Current Role Performance:")
        for role, stats in sorted(
            analysis.items(), key=lambda x: x[1]["cost_per_quality"]
        ):
            efficiency = stats["efficiency"]
            status = "✓" if efficiency == "good" else "⚠" if efficiency == "fair" else "❌"
            report.append(
                f"  {role}:"
                f" avg quality={stats['avg_quality']:.0f}%,"
                f" cost/quality=${stats['cost_per_quality']:.2e},"
                f" escalations={stats['escalation_rate']*100:.1f}% {status}"
            )

        # Recommendations
        report.append("\nOptimization Opportunities:")

        # Find inefficiencies
        inefficiencies = []
        for role, stats in analysis.items():
            if stats["efficiency"] == "poor":
                inefficiencies.append(
                    f"  • {role} has high cost/quality ratio (${stats['cost_per_quality']:.2e}). "
                    f"Consider downgrading to cheaper model or improving task pre-planning."
                )
            if stats["escalation_rate"] > 0.15:
                inefficiencies.append(
                    f"  • {role} has {stats['escalation_rate']*100:.1f}% escalation rate. "
                    f"May be under-scoped for assigned task complexity."
                )

        if inefficiencies:
            report.extend(inefficiencies)
        else:
            report.append("  ✓ All roles operating within acceptable efficiency ranges")

        # Task routing examples
        report.append("\nTask Routing Examples:")
        for complexity in ["low", "medium", "high", "max"]:
            rec = self.recommend_routing(complexity)
            top = rec.get("top_recommendation")
            if top:
                report.append(
                    f"  {complexity.upper()} complexity → {top['role']} "
                    f"(quality {top['quality']:.0f}%, score {top['score']:.0f})"
                )

        return "\n".join(report)

    def generate_feedback_for_tokenadvisor(self) -> str:
        """Generate feedback loop response to TokenAdvisor recommendations."""
        analysis = self.analyze_cost_quality_tradeoff()

        feedback = []
        feedback.append("=== Model Engineer Response to TokenAdvisor ===\n")

        # Check for role imbalances and propose fixes
        for role, stats in analysis.items():
            if stats["cost_per_quality"] > COST_TARGET_PER_QUALITY * 1.2:
                feedback.append(
                    f"TokenAdvisor flagged {role} inefficiency. "
                    f"Recommendation: Reduce allocation by 10-15% and re-test."
                )

        feedback.append("\nNext A/B Test Proposal:")
        feedback.append("  Experiment: Reduce Senior Engineer allocation by 10%")
        feedback.append("  Redirect to: Engineer (with improved task pre-planning)")
        feedback.append("  Expected impact: 5-10% cost reduction with same quality")
        feedback.append("  Duration: 2 weeks")
        feedback.append("  Success criteria: Cost/quality ratio improves by 3% or more")

        return "\n".join(feedback)


def main():
    """Main entry point."""
    import argparse
    import time

    start_time = time.time()

    parser = argparse.ArgumentParser(description="Model Engineer — Task Routing Optimizer")
    parser.add_argument("--analyze", action="store_true", help="Analyze current metrics")
    parser.add_argument("--recommend", action="store_true", help="Recommend task routing")
    parser.add_argument(
        "--complexity",
        choices=["low", "medium", "high", "max"],
        default="medium",
        help="Task complexity for recommendation",
    )
    parser.add_argument(
        "--feedback", action="store_true", help="Generate feedback to TokenAdvisor"
    )
    parser.add_argument("--date", default=None, help="Analyze specific date (YYYY-MM-DD)")
    parser.add_argument(
        "--metrics-dir",
        default=os.path.expanduser("~/.claude/metrics"),
        help="Path to metrics directory",
    )

    args = parser.parse_args()

    engineer = ModelEngineer(metrics_dir=args.metrics_dir)

    if args.recommend:
        rec = engineer.recommend_routing(args.complexity)
        top = rec.get("top_recommendation")
        if top:
            print(f"\nRecommended role for {args.complexity} complexity:")
            print(f"  → {top['role']} (score: {top['score']:.0f})")
            print(f"    Avg quality: {top['quality']:.0f}%")
            print(f"    Cost/quality: ${top['cost_per_quality']:.2e}")
            if rec.get("alternatives"):
                print("\nAlternatives:")
                for alt in rec["alternatives"]:
                    print(f"  • {alt['role']} (score: {alt['score']:.0f})")
        else:
            print("No recommendations available (no metrics)")
    elif args.feedback:
        print(engineer.generate_feedback_for_tokenadvisor())
    else:
        # Default: analyze
        print(engineer.generate_optimization_report(args.date))

    # Generate structured JSON for queue processing
    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    if engineer.load_metrics(date_str):
        analysis = engineer.analyze_cost_quality_tradeoff()

        alerts = []
        for role, stats in analysis.items():
            if stats["efficiency"] == "poor":
                alerts.append({
                    "severity": "warning",
                    "message": f"{role} has high cost/quality ratio (${stats['cost_per_quality']:.2e})",
                    "action": "optimize_model_assignment",
                    "should_email": True,
                    "should_voice": False
                })
            if stats["escalation_rate"] > 0.15:
                alerts.append({
                    "severity": "warning",
                    "message": f"{role} has {stats['escalation_rate']*100:.1f}% escalation rate",
                    "action": "review_task_complexity",
                    "should_email": True,
                    "should_voice": False
                })

        # Get top routing recommendations
        recommendations = []
        for complexity in ["low", "medium", "high", "max"]:
            rec = engineer.recommend_routing(complexity)
            top = rec.get("top_recommendation")
            if top:
                recommendations.append({
                    "complexity": complexity,
                    "role": top["role"],
                    "score": top["score"]
                })

        structured_log = {
            "timestamp": datetime.now().isoformat() + "Z",
            "job": "model-engineer",
            "status": "success",
            "duration_seconds": int(time.time() - start_time),
            "metrics": {
                "roles_analyzed": len(analysis),
                "recommendations_generated": len(recommendations),
                "inefficiencies_detected": len(alerts)
            },
            "alerts": alerts,
            "recommendations": recommendations,
            "feeds_to": "ab-testing"
        }

        print("\n===== STRUCTURED LOG =====")
        print(json.dumps(structured_log, indent=2))
        print("===== END STRUCTURED LOG =====")

        # Write alerts to queue for processing
        queue_dir = Path("agentic-engineers/data/logs/QUEUE/pending")
        queue_dir.mkdir(parents=True, exist_ok=True)

        for i, alert in enumerate(alerts):
            timestamp = datetime.now().isoformat().replace(":", "-").replace(".", "-")
            alert_file = queue_dir / f"alert-model-engineer-{timestamp}-{i}.json"
            alert["job"] = "model-engineer"
            alert["timestamp"] = datetime.now().isoformat() + "Z"
            with open(alert_file, "w") as f:
                json.dump(alert, f, indent=2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
