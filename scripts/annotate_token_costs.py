#!/usr/bin/env python3
"""annotate_token_costs.py — Token cost annotation for CI step summaries (Phase 5.1+).

Reads the most recent JSON file from data/metrics/ and emits a Markdown
table suitable for GitHub Actions step summaries.

Non-failing: exits 0 even if no metrics exist (just emits a placeholder message).

Usage:
    python scripts/annotate_token_costs.py
    python scripts/annotate_token_costs.py >> "$GITHUB_STEP_SUMMARY"
    python scripts/annotate_token_costs.py --metrics-dir data/metrics
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metrics-dir",
        default="data/metrics",
        help="Directory containing JSON metrics files (default: data/metrics)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    metrics_dir = Path(args.metrics_dir)

    print("## Token Cost Tracking")
    print()

    if not metrics_dir.is_dir():
        print(f"_`{metrics_dir}/` not found — token tracking not yet active._")
        print("_See Phase 5.2: wire usage-tracking skill to emit per-commit cost data._")
        return 0

    json_files = sorted(metrics_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not json_files:
        print(f"_No metrics files in `{metrics_dir}` — token tracking not yet active._")
        return 0

    latest = json_files[0]
    print(f"Latest metrics file: `{latest.name}`")
    print()

    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"_Metrics file present but could not be parsed: {e}_")
        return 0

    total = data.get("total_tokens", data.get("tokens_used", "N/A"))
    cost = data.get("estimated_cost_usd", "N/A")
    model = data.get("model", "N/A")
    session = data.get("session_id", data.get("session", "N/A"))

    print("| Metric | Value |")
    print("|--------|-------|")
    print(f"| Total tokens | {total} |")
    print(f"| Estimated cost (USD) | ${cost} |")
    if model != "N/A":
        print(f"| Model | {model} |")
    if session != "N/A":
        print(f"| Session | {session} |")

    print()
    print("_Token cost data is informational only. Phase 5.2 will add a hard budget gate._")
    return 0


if __name__ == "__main__":
    sys.exit(main())
