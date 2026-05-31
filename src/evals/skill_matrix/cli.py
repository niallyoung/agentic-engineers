"""CLI for skill interoperability matrix."""

import argparse
import sys
from pathlib import Path

from .matrix_runner import SkillInteropMatrix


def main() -> int:
    """Main CLI entry point.
    
    Usage:
        evals-skill-matrix                              # Run full matrix
        evals-skill-matrix --skill ab-testing           # Test specific skill
        evals-skill-matrix --harness opencode           # Test specific harness
        evals-skill-matrix --skill spec-validator --harness claude
    """
    parser = argparse.ArgumentParser(
        prog="evals-skill-matrix",
        description="Skill interoperability matrix test suite",
    )
    
    parser.add_argument(
        "--skill",
        type=str,
        default=None,
        help="Filter to specific skill (partial match)",
    )
    
    parser.add_argument(
        "--harness",
        type=str,
        default=None,
        help="Filter to specific harness (copilot, claude, opencode, pi)",
    )
    
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("/Users/niall/git/agentic-engineers"),
        help="Repository root directory",
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for reports",
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout per skill invocation (seconds)",
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON report instead of text",
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )
    
    args = parser.parse_args()
    
    # Create matrix runner
    matrix = SkillInteropMatrix(
        repo_root=args.repo_root,
        artifacts_dir=args.output_dir,
        timeout_seconds=args.timeout,
    )
    
    # Run tests
    if args.skill or args.harness:
        if not args.quiet:
            print(f"Running filtered matrix tests...")
            if args.skill:
                print(f"  Skill filter: {args.skill}")
            if args.harness:
                print(f"  Harness filter: {args.harness}")
            print()
        
        result = matrix.run_filtered_matrix(
            skill_filter=args.skill,
            harness_filter=args.harness,
        )
    else:
        if not args.quiet:
            print(f"Running full skill interoperability matrix...")
            print()
        
        result = matrix.run_full_matrix()
    
    print()
    
    # Output report
    if args.json:
        print(matrix.generate_json_report())
    else:
        print(matrix.generate_matrix_visualization())
    
    # Save reports
    txt_path, json_path = matrix.save_report(output_dir=args.output_dir)
    if not args.quiet:
        print(f"\nReports saved:")
        print(f"  Text: {txt_path}")
        print(f"  JSON: {json_path}")
    
    # Return exit code based on results
    if result.quality_score >= 92:
        return 0
    elif result.quality_score >= 80:
        return 1  # Warning
    else:
        return 2  # Failure


if __name__ == "__main__":
    sys.exit(main())
