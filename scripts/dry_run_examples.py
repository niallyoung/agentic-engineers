#!/usr/bin/env python3
"""
Dry-Run Mode Examples and Demonstrations

This script demonstrates various use cases for dry-run mode:
1. Basic operation logging
2. Simulating a complete orchestration cycle
3. Analyzing operation patterns
4. Performance testing
5. Audit trail inspection
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestration.dry_run import (
    dry_run_mode,
    DryRunContext,
    initialize_dry_run,
    get_dry_run_context,
)


def example_1_basic_operations():
    """Example 1: Basic operation logging."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Basic Operation Logging")
    print("=" * 80)
    
    with dry_run_mode(enabled=True) as dry_run:
        # Log various operations
        dry_run.log_file_write("/queue/incoming/task-1.yaml", "---\ntask_id: task-1\n")
        dry_run.log_queue_move("task-1", "incoming", "processing")
        dry_run.log_file_write("/queue/processing/task-1.yaml", "---\ntask_id: task-1\n")
        dry_run.log_git_commit("Process task-1", files=["task-1.yaml"])
        dry_run.log_api_call("POST", "/tasks/1/complete", {"status": "success"})
        dry_run.log_queue_move("task-1", "processing", "done")
        
        # Print summary
        print(dry_run.print_summary())
        
        # Print operations
        audit = dry_run.get_audit_trail()
        print("\nOperations:")
        for i, op in enumerate(audit["operations"], 1):
            print(f"  {i}. {op['description']}")


def example_2_complete_cycle():
    """Example 2: Simulating a complete orchestration cycle."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Complete Orchestration Cycle")
    print("=" * 80)
    
    with dry_run_mode(enabled=True) as dry_run:
        # Simulate processing 3 tasks
        for task_num in range(1, 4):
            task_id = f"task-{task_num}"
            
            print(f"\n📋 Processing {task_id}...")
            
            # Move to processing
            dry_run.log_queue_move(task_id, "incoming", "processing")
            
            # Write task file
            dry_run.log_file_write(
                f"/queue/processing/{task_id}.yaml",
                f"---\ntask_id: {task_id}\nstatus: processing\n"
            )
            
            # Commit changes
            dry_run.log_git_commit(
                f"Process {task_id}",
                files=[f"{task_id}.yaml"]
            )
            
            # Call API
            dry_run.log_api_call(
                "POST",
                f"/tasks/{task_num}/complete",
                {"task_id": task_id, "status": "success"}
            )
            
            # Move to done
            dry_run.log_queue_move(task_id, "processing", "done")
            
            # Archive result
            dry_run.log_file_write(
                f"/queue/done/{task_id}-complete.yaml",
                f"---\ntask_id: {task_id}\nstatus: complete\n"
            )
        
        # Print summary
        print(dry_run.print_summary())
        
        # Print operation counts
        audit = dry_run.get_audit_trail()
        print("\nOperation Breakdown:")
        for op_type, count in sorted(audit["operation_counts"].items()):
            print(f"  • {op_type}: {count}")


def example_3_analyze_patterns():
    """Example 3: Analyzing operation patterns."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Analyzing Operation Patterns")
    print("=" * 80)
    
    with dry_run_mode(enabled=True) as dry_run:
        # Simulate various operations
        operations_by_type = {
            "file_write": 10,
            "file_move": 5,
            "git_commit": 3,
            "queue_move": 15,
            "api_call": 8,
        }
        
        for op_type, count in operations_by_type.items():
            for i in range(count):
                if op_type == "file_write":
                    dry_run.log_file_write(f"/file{i}.txt", f"content{i}")
                elif op_type == "file_move":
                    dry_run.log_file_move(f"/old/file{i}.txt", f"/new/file{i}.txt")
                elif op_type == "git_commit":
                    dry_run.log_git_commit(f"Commit {i}")
                elif op_type == "queue_move":
                    dry_run.log_queue_move(f"task-{i}", "incoming", "processing")
                elif op_type == "api_call":
                    dry_run.log_api_call("POST", f"/endpoint{i}", {"id": i})
        
        # Analyze patterns
        audit = dry_run.get_audit_trail()
        
        print(f"\nTotal operations: {audit['total_operations']}")
        print(f"Duration: {audit['duration_seconds']}s")
        print("\nOperation Distribution:")
        
        total = sum(audit["operation_counts"].values())
        for op_type, count in sorted(
            audit["operation_counts"].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            percentage = (count / total) * 100
            bar = "█" * int(percentage / 5)
            print(f"  {op_type:20} {count:3} ({percentage:5.1f}%) {bar}")


def example_4_error_handling():
    """Example 4: Handling operations with errors."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Error Handling")
    print("=" * 80)
    
    with dry_run_mode(enabled=True) as dry_run:
        # Successful operations
        dry_run.log_file_write("/path/to/file.txt", "content")
        dry_run.log_git_commit("Fix: bug")
        
        # Operations that would fail
        dry_run.log_file_write(
            "/protected/file.txt",
            "content",
            would_succeed=False,
            error_message="Permission denied"
        )
        
        dry_run.log_git_push(
            "origin",
            "main",
            would_succeed=False,
            error_message="Remote rejected"
        )
        
        # Analyze results
        audit = dry_run.get_audit_trail()
        
        print("\nOperation Results:")
        for op in audit["operations"]:
            status = "✅" if op["would_succeed"] else "❌"
            print(f"  {status} {op['description']}")
            if op["error_message"]:
                print(f"     Error: {op['error_message']}")


def example_5_audit_trail_export():
    """Example 5: Exporting audit trail to JSON."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Audit Trail Export")
    print("=" * 80)
    
    import tempfile
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        log_file = f.name
    
    try:
        with dry_run_mode(enabled=True, log_file=log_file) as dry_run:
            # Log operations
            dry_run.log_file_write("/file.txt", "content")
            dry_run.log_queue_move("task-1", "incoming", "processing")
            dry_run.log_git_commit("Fix: bug")
        
        # Read and display audit trail
        with open(log_file) as f:
            audit = json.load(f)
        
        print(f"\n📄 Audit Trail saved to: {log_file}")
        print(f"\nAudit Trail Summary:")
        print(f"  • Total operations: {audit['total_operations']}")
        print(f"  • Duration: {audit['duration_seconds']}s")
        print(f"  • Start time: {audit['start_time']}")
        print(f"  • End time: {audit['end_time']}")
        
        print(f"\nOperation Types:")
        for op_type, count in sorted(audit["operation_counts"].items()):
            print(f"  • {op_type}: {count}")
        
        print(f"\nFirst 3 Operations:")
        for op in audit["operations"][:3]:
            print(f"  • {op['description']}")
        
        # Pretty print JSON
        print(f"\nFull JSON (first 500 chars):")
        json_str = json.dumps(audit, indent=2)
        print(json_str[:500] + "...")
        
    finally:
        # Cleanup
        Path(log_file).unlink(missing_ok=True)


def example_6_performance_testing():
    """Example 6: Performance testing with large number of operations."""
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Performance Testing")
    print("=" * 80)
    
    import time
    
    with dry_run_mode(enabled=True) as dry_run:
        print("\nLogging 1000 operations...")
        
        start = time.time()
        for i in range(1000):
            dry_run.log_file_write(f"/file{i}.txt", f"content{i}")
        elapsed = time.time() - start
        
        print(f"✅ Logged 1000 operations in {elapsed:.3f}s")
        print(f"   Average: {(elapsed/1000)*1000:.2f}ms per operation")
        
        # Generate audit trail
        start = time.time()
        audit = dry_run.get_audit_trail()
        elapsed = time.time() - start
        
        print(f"\n✅ Generated audit trail in {elapsed:.3f}s")
        print(f"   Total operations: {audit['total_operations']}")
        print(f"   Memory size: ~{len(json.dumps(audit))/1024:.1f}KB")


def main():
    """Run all examples."""
    print("\n" + "🏜️ " * 20)
    print("DRY-RUN MODE EXAMPLES AND DEMONSTRATIONS")
    print("🏜️ " * 20)
    
    examples = [
        ("Basic Operations", example_1_basic_operations),
        ("Complete Cycle", example_2_complete_cycle),
        ("Pattern Analysis", example_3_analyze_patterns),
        ("Error Handling", example_4_error_handling),
        ("Audit Trail Export", example_5_audit_trail_export),
        ("Performance Testing", example_6_performance_testing),
    ]
    
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    
    if len(sys.argv) > 1:
        try:
            example_num = int(sys.argv[1]) - 1
            if 0 <= example_num < len(examples):
                name, func = examples[example_num]
                print(f"\n▶️  Running: {name}")
                func()
            else:
                print(f"❌ Invalid example number: {example_num + 1}")
                sys.exit(1)
        except ValueError:
            print(f"❌ Invalid input: {sys.argv[1]}")
            sys.exit(1)
    else:
        # Run all examples
        print("\n▶️  Running all examples...\n")
        for name, func in examples:
            try:
                func()
            except Exception as e:
                print(f"\n❌ Error in {name}: {e}")
                import traceback
                traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("✅ Examples completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
