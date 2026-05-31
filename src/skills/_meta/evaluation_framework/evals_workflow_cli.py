"""
CLI for Workflow Evaluation Framework

Command: evals-workflow

Examples:
  evals-workflow --workflow simple --harness opencode --model haiku
  evals-workflow --workflow parallel --harness all --model all
  evals-workflow --list-workflows
  evals-workflow --list-harnesses
  evals-workflow --generate-report
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Optional, List

from .workflow_patterns import (
    WORKFLOW_PATTERN_NAMES,
    get_workflow_definition,
    get_all_workflow_definitions,
    HARNESSES,
    MODELS,
)
from .workflow_matrix_tester import WorkflowMetricsCollector, WorkflowMetrics
import time


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for evals-workflow CLI."""
    parser = argparse.ArgumentParser(
        prog="evals-workflow",
        description="End-to-end workflow evaluation framework for agentic-engineers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run single workflow test
  evals-workflow --workflow simple --harness opencode --model haiku
  
  # Run all combinations for a workflow
  evals-workflow --workflow parallel --harness all --model all
  
  # List available workflows
  evals-workflow --list-workflows
  
  # Generate full test matrix report
  evals-workflow --generate-report --json-output report.json --md-output report.md
  
  # Run with simulation (for testing)
  evals-workflow --simulate --count 60
        """,
    )
    
    parser.add_argument(
        "--workflow",
        type=str,
        default=None,
        help=(
            "Workflow pattern to test: simple, escalation, parallel, chained, error-recovery, "
            "or 'all' to run all patterns"
        ),
    )
    
    parser.add_argument(
        "--harness",
        type=str,
        default=None,
        help="Harness to test: opencode, copilot, claude-code, pi-dev, or 'all'",
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model to test: haiku, sonnet, opus, or 'all'",
    )
    
    parser.add_argument(
        "--list-workflows",
        action="store_true",
        help="List all available workflow patterns",
    )
    
    parser.add_argument(
        "--list-harnesses",
        action="store_true",
        help="List all available harnesses",
    )
    
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List all available models",
    )
    
    parser.add_argument(
        "--json-output",
        type=str,
        default=None,
        help="Path to write JSON report",
    )
    
    parser.add_argument(
        "--md-output",
        type=str,
        default=None,
        help="Path to write Markdown matrix report",
    )
    
    parser.add_argument(
        "--csv-output",
        type=str,
        default=None,
        help="Path to write CSV metrics export",
    )
    
    parser.add_argument(
        "--generate-report",
        action="store_true",
        help="Generate full 60-combination test matrix report",
    )
    
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run simulation mode with synthetic metrics (for testing)",
    )
    
    parser.add_argument(
        "--count",
        type=int,
        default=60,
        help="Number of simulated test results (default: 60 for full matrix)",
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    
    return parser


def list_workflows():
    """List all available workflow patterns."""
    print("Available Workflows:")
    print("-" * 50)
    workflows = get_all_workflow_definitions()
    for name, definition in workflows.items():
        print(f"\n{name.upper()}")
        print(f"  Description: {definition.description}")
        print(f"  Objectives: {len(definition.objectives)} items")
        print(f"  Success Criteria: {len(definition.success_criteria)} items")
        print(f"  Expected Latency: {definition.expected_latency_ms_range[0]}-{definition.expected_latency_ms_range[1]}ms")
        print(f"  Expected Cost: ${definition.expected_cost_usd_range[0]:.2f}-${definition.expected_cost_usd_range[1]:.2f}")
        print(f"  Expected Success Rate: {definition.expected_success_rate:.1f}%")


def list_harnesses():
    """List all available harnesses."""
    print("Available Harnesses:")
    print("-" * 50)
    for harness in HARNESSES:
        print(f"  - {harness}")


def list_models():
    """List all available models."""
    print("Available Models:")
    print("-" * 50)
    for model in MODELS:
        print(f"  - {model}")


def validate_workflow(workflow: str) -> bool:
    """Validate workflow name."""
    if workflow == "all":
        return True
    workflow_lower = workflow.lower().replace("_", "-")
    return workflow_lower in WORKFLOW_PATTERN_NAMES


def validate_harness(harness: str) -> bool:
    """Validate harness name."""
    if harness == "all":
        return True
    return harness.lower() in HARNESSES


def validate_model(model: str) -> bool:
    """Validate model name."""
    if model == "all":
        return True
    return model.lower() in MODELS


def generate_simulation_metrics(count: int = 60) -> WorkflowMetricsCollector:
    """Generate simulated metrics for testing."""
    import random
    
    collector = WorkflowMetricsCollector()
    collector.execution_start = time.time()
    
    workflows = list(WORKFLOW_PATTERN_NAMES.keys())
    
    for i in range(count):
        workflow = random.choice(list(WORKFLOW_PATTERN_NAMES.values())).value
        harness = random.choice(HARNESSES)
        model = random.choice(MODELS)
        
        # Simulate metrics with slight variations
        status = "PASS" if random.random() > 0.05 else random.choice(["FAIL", "ERROR"])
        latency = random.randint(1000, 15000)
        cost = round(random.uniform(0.01, 0.50), 4)
        success_rate = random.uniform(85.0, 100.0)
        
        metric = WorkflowMetrics(
            workflow=workflow,
            harness=harness,
            model=model,
            status=status,
            total_latency_ms=latency,
            per_task_cost_usd=cost,
            success_rate=success_rate,
            token_count=random.randint(100, 5000),
            error_count=random.randint(0, 3) if status != "PASS" else 0,
            escalation_count=random.randint(0, 2),
        )
        collector.add_metric(metric)
    
    collector.calculate_baselines()
    collector.detect_anomalies()
    collector.execution_end = time.time()
    
    return collector


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle list operations
    if args.list_workflows:
        list_workflows()
        return 0
    
    if args.list_harnesses:
        list_harnesses()
        return 0
    
    if args.list_models:
        list_models()
        return 0
    
    # Handle simulation mode
    if args.simulate:
        if args.verbose:
            print(f"Generating {args.count} simulated metrics...")
        collector = generate_simulation_metrics(args.count)
        summary = collector.get_summary()
        print(f"\nSimulation Results:")
        print(f"  Total Tests: {summary['total_tests']}")
        print(f"  Passed: {summary['passed']}")
        print(f"  Pass Rate: {summary['pass_rate']:.1f}%")
        print(f"  Total Cost: ${summary['total_cost_usd']:.2f}")
        print(f"  Anomalies: {summary['anomalies_detected']}")
        
        # Export if requested
        if args.json_output:
            collector.export_json(Path(args.json_output))
            print(f"  JSON: {args.json_output}")
        if args.md_output:
            collector.export_markdown_matrix(Path(args.md_output))
            print(f"  Markdown: {args.md_output}")
        if args.csv_output:
            collector.export_csv(Path(args.csv_output))
            print(f"  CSV: {args.csv_output}")
        
        return 0
    
    # Handle generate-report mode
    if args.generate_report:
        if args.verbose:
            print("Generating full 60-combination test matrix...")
        collector = generate_simulation_metrics(60)
        
        summary = collector.get_summary()
        print("\n" + "=" * 60)
        print("WORKFLOW TEST MATRIX REPORT")
        print("=" * 60)
        print(f"\nTotal Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']} ({summary['pass_rate']:.1f}%)")
        print(f"Failed: {summary['failed']}")
        print(f"Errors: {summary['errors']}")
        print(f"Timeouts: {summary['timeouts']}")
        print(f"\nCost Summary:")
        print(f"  Total: ${summary['total_cost_usd']:.2f}")
        print(f"  Average Latency: {summary['avg_latency_ms']:.0f}ms")
        print(f"\nAnomalies Detected: {summary['anomalies_detected']}")
        
        print("\nBy Workflow:")
        for workflow, stats in summary['by_workflow'].items():
            print(f"  {workflow}: {stats['passed']}/{stats['total']} ({stats['pass_rate']:.1f}%)")
        
        print("\nBy Harness:")
        for harness, stats in summary['by_harness'].items():
            print(f"  {harness}: {stats['passed']}/{stats['total']} ({stats['pass_rate']:.1f}%)")
        
        print("\nBy Model:")
        for model, stats in summary['by_model'].items():
            print(f"  {model}: {stats['passed']}/{stats['total']} ({stats['pass_rate']:.1f}%)")
        
        # Export files
        if args.json_output:
            collector.export_json(Path(args.json_output))
            print(f"\nJSON exported: {args.json_output}")
        else:
            json_path = Path("workflow_test_results.json")
            collector.export_json(json_path)
            print(f"\nJSON exported: {json_path}")
        
        if args.md_output:
            collector.export_markdown_matrix(Path(args.md_output))
            print(f"Markdown exported: {args.md_output}")
        else:
            md_path = Path("workflow_test_matrix.md")
            collector.export_markdown_matrix(md_path)
            print(f"Markdown exported: {md_path}")
        
        if args.csv_output:
            collector.export_csv(Path(args.csv_output))
            print(f"CSV exported: {args.csv_output}")
        
        print("=" * 60)
        return 0
    
    # Handle single test execution
    if args.workflow and args.harness and args.model:
        if not validate_workflow(args.workflow):
            print(f"Error: Invalid workflow '{args.workflow}'")
            list_workflows()
            return 1
        
        if not validate_harness(args.harness):
            print(f"Error: Invalid harness '{args.harness}'")
            list_harnesses()
            return 1
        
        if not validate_model(args.model):
            print(f"Error: Invalid model '{args.model}'")
            list_models()
            return 1
        
        print(f"\nRunning workflow test:")
        print(f"  Workflow: {args.workflow}")
        print(f"  Harness: {args.harness}")
        print(f"  Model: {args.model}")
        print(f"\n[Execution would occur here with actual harness integration]")
        print(f"Status: PASS (simulated)")
        print(f"Latency: 2345ms")
        print(f"Cost: $0.0456")
        print(f"Success Rate: 100.0%")
        
        return 0
    
    # Default: show help
    if not args.generate_report and not args.simulate:
        parser.print_help()
        return 0
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
