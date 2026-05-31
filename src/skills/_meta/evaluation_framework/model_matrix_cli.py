"""
CLI for Model Compatibility Matrix

Usage:
  evals-model-matrix --model opus --scenario code-fix --harness opencode
  evals-model-matrix --show-matrix --scenario simple
  evals-model-matrix --detect-regressions
"""

import argparse
import sys
import json
from pathlib import Path
from typing import List, Optional

from .model_matrix import ModelCompatibilityMatrix, TestScenario, ScenarioMetrics, TestStatus


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for model matrix CLI."""
    parser = argparse.ArgumentParser(
        description="Model Compatibility Matrix: Test models across scenarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test specific model and scenario
  python -m evals_model_matrix --model opus --scenario code-fix
  
  # Show colored compatibility matrix
  python -m evals_model_matrix --show-matrix
  
  # Test all models on simple scenario
  python -m evals_model_matrix --scenario simple --all-models
  
  # Detect regressions
  python -m evals_model_matrix --detect-regressions --matrix report.json
  
  # Generate full report
  python -m evals_model_matrix --report output.json --matrix-report matrix.md
        """
    )
    
    parser.add_argument(
        "--model",
        choices=["haiku", "sonnet", "opus"],
        help="Model to test"
    )
    
    parser.add_argument(
        "--scenario",
        choices=["simple", "complex", "code-fix", "reasoning", "security"],
        help="Test scenario"
    )
    
    parser.add_argument(
        "--harness",
        choices=["opencode", "copilot", "claude-code", "pi-dev"],
        help="Harness to test against"
    )
    
    parser.add_argument(
        "--all-models",
        action="store_true",
        help="Test all models"
    )
    
    parser.add_argument(
        "--all-scenarios",
        action="store_true",
        help="Test all scenarios"
    )
    
    parser.add_argument(
        "--show-matrix",
        action="store_true",
        help="Display colored compatibility matrix"
    )
    
    parser.add_argument(
        "--detect-regressions",
        action="store_true",
        help="Detect quality and latency regressions"
    )
    
    parser.add_argument(
        "--matrix",
        type=str,
        help="Path to existing matrix JSON to analyze"
    )
    
    parser.add_argument(
        "--report",
        type=str,
        help="Path to write JSON report"
    )
    
    parser.add_argument(
        "--matrix-report",
        type=str,
        help="Path to write Markdown matrix report"
    )
    
    parser.add_argument(
        "--quality-baseline",
        type=float,
        default=92.0,
        help="Quality baseline for regression detection (default: 92.0)"
    )
    
    parser.add_argument(
        "--latency-baseline",
        type=float,
        default=500.0,
        help="Latency baseline in ms for regression detection (default: 500.0)"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main CLI entry point.
    
    Args:
        argv: Command-line arguments
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # Load or create matrix
    matrix = None
    if args.matrix:
        try:
            matrix_path = Path(args.matrix)
            matrix = ModelCompatibilityMatrix.from_json(matrix_path)
            if args.verbose:
                print(f"✅ Loaded matrix from {matrix_path}")
        except Exception as e:
            print(f"❌ Error loading matrix: {e}", file=sys.stderr)
            return 1
    else:
        matrix = ModelCompatibilityMatrix()
    
    # Show colored matrix
    if args.show_matrix:
        if not matrix.results:
            print("⚠️  No results in matrix. Load a matrix with --matrix or add results first.")
            return 1
        
        scenario = None
        if args.scenario:
            scenario = TestScenario(args.scenario)
        
        print(matrix.generate_colored_matrix(scenario))
        return 0
    
    # Detect regressions
    if args.detect_regressions:
        if not matrix.results:
            print("⚠️  No results in matrix. Load a matrix with --matrix or add results first.")
            return 1
        
        matrix.quality_regression_threshold = 10.0
        matrix.latency_regression_threshold = 25.0
        
        quality_regs = matrix.detect_quality_regressions(args.quality_baseline)
        latency_regs = matrix.detect_latency_regressions(args.latency_baseline)
        
        print("\n📊 Regression Detection Report\n")
        
        if quality_regs:
            print("❌ Quality Regressions (>10% drop):")
            for reg in quality_regs:
                print(f"  • {reg['model']}:{reg['scenario']} — "
                      f"baseline {reg['baseline']} → {reg['achieved']} (-{reg['drop_percent']}%)")
        else:
            print("✅ No quality regressions detected")
        
        print()
        
        if latency_regs:
            print("⚠️  Latency Regressions (>25% increase):")
            for reg in latency_regs:
                print(f"  • {reg['model']}:{reg['scenario']} — "
                      f"baseline {reg['baseline_ms']}ms → {reg['achieved_ms']}ms (+{reg['increase_percent']}%)")
        else:
            print("✅ No latency regressions detected")
        
        print()
        return 0 if not (quality_regs or latency_regs) else 1
    
    # Generate reports
    if args.report:
        if not matrix.results:
            print("⚠️  No results to report. Load a matrix or add results first.")
            return 1
        
        try:
            report_path = Path(args.report)
            matrix.save_json(report_path)
            print(f"✅ Report saved to {report_path}")
        except Exception as e:
            print(f"❌ Error writing report: {e}", file=sys.stderr)
            return 1
    
    # Generate markdown matrix report
    if args.matrix_report:
        if not matrix.results:
            print("⚠️  No results to report.")
            return 1
        
        try:
            md_path = Path(args.matrix_report)
            with open(md_path, 'w') as f:
                f.write("# Model Compatibility Matrix Report\n\n")
                f.write(f"Generated: {matrix.generated_at}\n\n")
                f.write(matrix.generate_colored_matrix())
                
                # Summary by model
                f.write("\n## Summary by Model\n\n")
                for model, stats in matrix.get_summary_by_model().items():
                    f.write(f"### {model.upper()}\n\n")
                    f.write(f"- Pass Rate: {stats['passed']}/{stats['count']}\n")
                    f.write(f"- Avg Quality: {stats['avg_quality']}/100\n")
                    f.write(f"- Avg Latency: {stats['avg_latency_ms']}ms\n")
                    f.write(f"- Avg Tokens: {stats['avg_tokens']}\n")
                    f.write(f"- Total Cost: ${stats['total_cost_usd']}\n")
                    f.write(f"- Scenarios: {', '.join(stats['scenarios'])}\n\n")
                
                # Regressions
                quality_regs = matrix.detect_quality_regressions()
                latency_regs = matrix.detect_latency_regressions()
                
                if quality_regs or latency_regs:
                    f.write("\n## Regressions Detected\n\n")
                    for reg in quality_regs + latency_regs:
                        f.write(f"- {reg['status']} {reg['model']}:{reg['scenario']}\n")
            
            print(f"✅ Matrix report saved to {md_path}")
        except Exception as e:
            print(f"❌ Error writing matrix report: {e}", file=sys.stderr)
            return 1
    
    # Test specific model/scenario
    if args.model or args.scenario:
        print(f"🧪 Testing model={args.model}, scenario={args.scenario}")
        print("⚠️  Model execution not yet implemented in CLI.")
        return 1
    
    # No action specified
    if not any([args.show_matrix, args.detect_regressions, args.report, args.matrix_report, args.model, args.scenario]):
        parser.print_help()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
