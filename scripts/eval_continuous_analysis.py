#!/usr/bin/env python3
"""
Continuous CI/CD Analysis Script

Analyzes evaluation results, detects regressions, generates reports and dashboard.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.skills._meta.evaluation_framework.regression_detector import RegressionDetector
from src.skills._meta.evaluation_framework.baseline_manager import BaselineManager
from src.skills._meta.evaluation_framework.dashboard_generator import DashboardGenerator


def main():
    """Main analysis function."""
    # Aggregate results from all evaluation suites
    results_dir = Path("/tmp/results")
    aggregated = {
        "evals_002": None,
        "evals_003": None,
        "evals_004": None,
    }

    for eval_num, artifact in enumerate([
        "evals-002-results",
        "evals-003-results",
        "evals-004-results"
    ], start=2):
        json_file = results_dir / artifact / f"evals_00{eval_num}_results.json"
        if json_file.exists():
            try:
                with open(json_file) as f:
                    aggregated[f"evals_00{eval_num}"] = json.load(f)
                    print(f"✅ Loaded EVALS-{eval_num:03d} results")
            except Exception as e:
                print(f"⚠️ Warning: Could not load {json_file}: {e}")

    # Write aggregated results
    agg_file = Path("/tmp/aggregated_results.json")
    with open(agg_file, "w") as f:
        json.dump(aggregated, f, indent=2)
    print(f"📝 Aggregated results written to {agg_file}")

    # Load baseline if exists
    baseline_mgr = BaselineManager()
    baseline = baseline_mgr.get_current_baseline()

    # Check for regressions
    regressions = []
    if baseline:
        detector = RegressionDetector()
        current_results = aggregated.get("evals_002", {})
        regressions = detector.detect(
            baseline.get("results", {}),
            current_results
        )

        print(f"\n### Regression Detection Summary ###")
        summary = detector.get_summary()
        print(f"Total Regressions: {summary['total_regressions']}")
        print(f"Critical: {summary['critical']}")
        print(f"High: {summary['high']}")
        print(f"Medium: {summary['medium']}")

        # Write regressions to file
        with open("/tmp/regressions.json", "w") as f:
            json.dump(detector.to_dict_list(), f, indent=2)
        print(f"📊 Regressions written to /tmp/regressions.json")

        # Generate dashboard
        dashboard = DashboardGenerator(
            current_results,
            baseline,
            detector.to_dict_list()
        )
        dashboard.generate("/tmp/dashboard.html")
        print(f"🎨 Dashboard generated: /tmp/dashboard.html")
    else:
        print("⚠️ No baseline found. Creating initial baseline...")
        # Create initial baseline from current results
        current_results = aggregated.get("evals_002", {})
        if current_results:
            baseline_path = baseline_mgr.save_baseline(current_results)
            print(f"✅ Initial baseline created: {baseline_path}")

    print(f"\n✅ Analysis complete!")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
