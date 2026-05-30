"""
CLI interface for the evaluation framework

Provides command-line interface for running tests, loading test cases, and generating reports.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from .framework import TestRunner
from .reporters import JSONReporter, MarkdownReporter, CSVReporter


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        description="Evaluation Framework for agentic-engineers harness compatibility testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python -m src.skills._meta.evaluation_framework.main --run-tests tests/evals/

  # Run specific harnesses
  python -m src.skills._meta.evaluation_framework.main --run-tests tests/evals/ --harnesses opencode copilot

  # Generate reports
  python -m src.skills._meta.evaluation_framework.main --run-tests tests/evals/ --json-report report.json --md-report report.md

  # Run with specific test filter
  python -m src.skills._meta.evaluation_framework.main --run-tests tests/evals/ --filter "test-delegate*"
        """
    )
    
    parser.add_argument(
        "--run-tests",
        type=str,
        help="Directory containing test case YAML files to run"
    )
    
    parser.add_argument(
        "--load-tests",
        type=str,
        help="Directory containing test cases to load (without running)"
    )
    
    parser.add_argument(
        "--harnesses",
        nargs="+",
        default=None,
        help="Harnesses to test (opencode, copilot, claude-code, pi-dev)"
    )
    
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="Models to test (haiku, sonnet, opus)"
    )
    
    parser.add_argument(
        "--json-report",
        type=str,
        default=None,
        help="Path to write JSON report"
    )
    
    parser.add_argument(
        "--md-report",
        type=str,
        default=None,
        help="Path to write Markdown report"
    )
    
    parser.add_argument(
        "--csv-report",
        type=str,
        default=None,
        help="Path to write CSV report"
    )
    
    parser.add_argument(
        "--filter",
        type=str,
        default=None,
        help="Filter test cases by ID pattern (glob)"
    )
    
    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=95.0,
        help="Minimum pass rate for success (default: 95.0)"
    )
    
    parser.add_argument(
        "--working-dir",
        type=str,
        default=".",
        help="Working directory for test execution"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser


def main(argv: Optional[List[str]] = None):
    """
    Main CLI entry point.
    
    Args:
        argv: Command-line arguments (default: sys.argv[1:])
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # Validate arguments
    if not args.run_tests and not args.load_tests:
        parser.print_help()
        return 1
    
    # Initialize test runner
    runner = TestRunner(working_dir=args.working_dir)
    
    # Load test cases
    if args.load_tests:
        tests_dir = Path(args.load_tests)
        print(f"Loading test cases from {tests_dir}...")
        try:
            runner.load_test_cases(tests_dir)
            print(f"Loaded {len(runner.test_cases)} test cases")
        except Exception as e:
            print(f"Error loading test cases: {e}", file=sys.stderr)
            return 1
    
    if args.run_tests:
        tests_dir = Path(args.run_tests)
        print(f"Loading test cases from {tests_dir}...")
        try:
            runner.load_test_cases(tests_dir)
            print(f"Loaded {len(runner.test_cases)} test cases")
        except Exception as e:
            print(f"Error loading test cases: {e}", file=sys.stderr)
            return 1
        
        # Filter test cases if specified
        if args.filter:
            from fnmatch import fnmatch
            filtered = [tc for tc in runner.test_cases if fnmatch(tc.id, args.filter)]
            print(f"Filtered to {len(filtered)} test cases matching '{args.filter}'")
            runner.test_cases = filtered
        
        # Run tests
        print("\nRunning tests...")
        try:
            matrix = runner.run_all_tests(
                harnesses=args.harnesses,
                models=args.models
            )
        except Exception as e:
            print(f"Error running tests: {e}", file=sys.stderr)
            return 1
        
        # Generate reports
        if args.json_report:
            print(f"\nGenerating JSON report: {args.json_report}")
            json_reporter = JSONReporter(matrix)
            json_reporter.write(Path(args.json_report))
        
        if args.md_report:
            print(f"Generating Markdown report: {args.md_report}")
            md_reporter = MarkdownReporter(matrix)
            md_reporter.write(Path(args.md_report))
        
        if args.csv_report:
            print(f"Generating CSV report: {args.csv_report}")
            csv_reporter = CSVReporter(matrix)
            csv_reporter.write(Path(args.csv_report))
        
        # Print summary
        summary = matrix.get_summary()
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Timeout: {summary['timeout']}")
        print(f"Error: {summary['error']}")
        print(f"Skipped: {summary['skipped']}")
        print(f"Pass Rate: {summary['pass_rate']}%")
        print(f"Avg Duration: {summary['avg_duration_ms']}ms")
        print("=" * 60)
        
        # Check minimum pass rate
        if summary['pass_rate'] < args.min_pass_rate:
            print(f"\n❌ FAILED: Pass rate {summary['pass_rate']}% < {args.min_pass_rate}%")
            return 1
        else:
            print(f"\n✅ PASSED: Pass rate {summary['pass_rate']}% >= {args.min_pass_rate}%")
            return 0
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
