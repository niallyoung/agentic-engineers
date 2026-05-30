"""
CLI commands for baseline management

Provides commands for creating, loading, and managing evaluation baselines.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, List

from .baseline_manager import BaselineManager


def create_baseline_parser() -> argparse.ArgumentParser:
    """Create argument parser for baseline CLI."""
    parser = argparse.ArgumentParser(
        description="Evaluation Framework Baseline Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate new baseline from current results
  evals-baseline --generate results.json

  # Get current baseline
  evals-baseline --current

  # List all snapshots
  evals-baseline --list-snapshots

  # Cleanup old snapshots
  evals-baseline --cleanup --keep 10

  # Get baseline history
  evals-baseline --history --limit 5
        """
    )

    parser.add_argument(
        "--generate",
        type=str,
        default=None,
        help="Generate new baseline from results file"
    )

    parser.add_argument(
        "--current",
        action="store_true",
        help="Get the current baseline"
    )

    parser.add_argument(
        "--list-snapshots",
        action="store_true",
        help="List all available snapshots"
    )

    parser.add_argument(
        "--snapshot",
        type=str,
        default=None,
        help="Get a specific snapshot by date (YYYY-MM-DD)"
    )

    parser.add_argument(
        "--history",
        action="store_true",
        help="Get baseline history for trend analysis"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Limit number of items to return (default: 10)"
    )

    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Cleanup old snapshots"
    )

    parser.add_argument(
        "--keep",
        type=int,
        default=12,
        help="Number of snapshots to keep during cleanup (default: 12)"
    )

    parser.add_argument(
        "--baseline-dir",
        type=str,
        default=None,
        help="Baseline directory (default: .github/baseline_snapshots)"
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for baseline management CLI.

    Args:
        argv: Command-line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = create_baseline_parser()
    args = parser.parse_args(argv)

    # Initialize baseline manager
    baseline_dir = Path(args.baseline_dir) if args.baseline_dir else None
    manager = BaselineManager(baseline_dir)

    try:
        # Generate new baseline
        if args.generate:
            results_file = Path(args.generate)
            if not results_file.exists():
                print(f"Error: Results file not found: {results_file}", file=sys.stderr)
                return 1

            try:
                with open(results_file) as f:
                    results = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in results file: {e}", file=sys.stderr)
                return 1

            # Save baseline
            baseline_path = manager.save_baseline(results)
            print(f"✅ Baseline saved: {baseline_path}")

            # Also create monthly snapshot
            snapshot_path = manager.create_monthly_snapshot(results)
            print(f"✅ Snapshot created: {snapshot_path}")

            return 0

        # Get current baseline
        elif args.current:
            baseline = manager.get_current_baseline()
            if baseline:
                print(json.dumps(baseline, indent=2))
                return 0
            else:
                print("No baseline found", file=sys.stderr)
                return 1

        # List snapshots
        elif args.list_snapshots:
            snapshots = manager.list_snapshots()
            if snapshots:
                print(f"Found {len(snapshots)} snapshots:\n")
                for i, snapshot in enumerate(snapshots[:args.limit], 1):
                    print(f"{i}. {snapshot['filename']}")
                    print(f"   Timestamp: {snapshot['timestamp']}")
                    print(f"   Path: {snapshot['path']}\n")
                return 0
            else:
                print("No snapshots found")
                return 1

        # Get specific snapshot
        elif args.snapshot:
            parts = args.snapshot.split("-")
            if len(parts) != 3:
                print("Error: Date format should be YYYY-MM-DD", file=sys.stderr)
                return 1

            try:
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            except ValueError:
                print("Error: Invalid date format", file=sys.stderr)
                return 1

            snapshot = manager.get_snapshot_by_date(year, month, day)
            if snapshot:
                print(json.dumps(snapshot, indent=2))
                return 0
            else:
                print(f"Snapshot not found for date: {args.snapshot}", file=sys.stderr)
                return 1

        # Get baseline history
        elif args.history:
            history = manager.get_baseline_history(limit=args.limit)
            if history:
                print(f"Baseline history ({len(history)} items):\n")
                for i, item in enumerate(history, 1):
                    summary = item.get("summary", {})
                    print(f"{i}. {item['filename']}")
                    print(f"   Timestamp: {item['timestamp']}")
                    print(f"   Pass Rate: {summary.get('pass_rate', 'N/A'):.1f}%")
                    print(f"   Tests: {summary.get('total_tests', 'N/A')}\n")
                return 0
            else:
                print("No baseline history found")
                return 1

        # Cleanup old snapshots
        elif args.cleanup:
            deleted = manager.cleanup_old_snapshots(keep_count=args.keep)
            if deleted:
                print(f"✅ Cleaned up {len(deleted)} old snapshots")
                for path in deleted:
                    print(f"   Deleted: {path}")
                return 0
            else:
                print("No snapshots to cleanup")
                return 0

        else:
            parser.print_help()
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
