#!/usr/bin/env python3
"""
Example: Using the Session Memory System

Demonstrates practical patterns for session memory management, aggregation, and querying.
"""

from pathlib import Path
from datetime import datetime
import tempfile
import yaml

from src.orchestration.memory import (
    SessionMemoryManager,
    setup_session_memory,
    get_session_memory_dir,
)
from src.orchestration.memory.aggregator import SessionMemoryAggregator


def example_1_basic_session_lifecycle():
    """Example 1: Basic session memory lifecycle."""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Basic Session Lifecycle")
    print("=" * 60)
    
    session_id = "example-session-001"
    
    # Initialize session memory
    manager = SessionMemoryManager(session_id)
    result = manager.initialize(metadata={
        "user": "alice@example.com",
        "project": "api-refactor",
        "environment": "development",
    })
    
    print(f"✅ Session initialized: {result['session_id']}")
    print(f"   Memory dir: {result['memory_dir']}")
    
    # In a real scenario, the orchestrator would:
    # 1. Collect memory events during task execution
    # 2. Aggregate memory at session end
    # 3. Export summary
    
    index = manager.aggregate_memory()
    summary_path = manager.export_summary()
    
    print(f"✅ Memory aggregated: {index['summary']['total_delegates']} delegates collected")
    print(f"✅ Summary exported to: {summary_path}")


def example_2_query_by_task_id():
    """Example 2: Query memory by task ID."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Query by Task ID")
    print("=" * 60)
    
    session_id = "example-session-002"
    manager = SessionMemoryManager(session_id)
    manager.initialize()
    
    # Simulate some delegate/handback data
    if manager.aggregator:
        manager.aggregator.index["delegates"] = [
            {
                "task_id": "auth-module-001",
                "role": "Engineer",
                "timestamp": datetime.utcnow().isoformat(),
                "scope": "Implement JWT auth",
            }
        ]
        manager.aggregator.index["handbacks"] = [
            {
                "task_id": "auth-module-001",
                "status": "complete",
                "quality_score": 95,
                "tokens_used": 1500,
            }
        ]
    
    # Query by task ID
    result = manager.query_by_task_id("auth-module-001")
    
    print(f"✅ Found task: {result['task_id']}")
    print(f"   DELEGATEs: {len(result['delegates'])}")
    if result['delegates']:
        delegate = result['delegates'][0]
        print(f"     - Role: {delegate['role']}")
        print(f"     - Scope: {delegate['scope']}")
    
    print(f"   HANDBACKs: {len(result['handbacks'])}")
    if result['handbacks']:
        handback = result['handbacks'][0]
        print(f"     - Status: {handback['status']}")
        print(f"     - Quality: {handback['quality_score']}/100")
        print(f"     - Tokens: {handback['tokens_used']:,}")


def example_3_query_by_role():
    """Example 3: Query memory by agent role."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Query by Role")
    print("=" * 60)
    
    session_id = "example-session-003"
    manager = SessionMemoryManager(session_id)
    manager.initialize()
    
    # Simulate delegate data for multiple roles
    if manager.aggregator:
        manager.aggregator.index["delegates"] = [
            {"task_id": "t1", "role": "Engineer", "effort": "low"},
            {"task_id": "t2", "role": "Engineer", "effort": "high"},
            {"task_id": "t3", "role": "Senior Engineer", "effort": "high"},
            {"task_id": "t4", "role": "Lead Engineer", "effort": "medium"},
            {"task_id": "t5", "role": "Engineer", "effort": "low"},
        ]
    
    # Query by role
    for role in ["Engineer", "Senior Engineer", "Lead Engineer"]:
        result = manager.query_by_role(role)
        print(f"✅ {role}: {result['count']} tasks")


def example_4_metrics_dashboard():
    """Example 4: Display metrics dashboard."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Metrics Dashboard")
    print("=" * 60)
    
    session_id = "example-session-004"
    manager = SessionMemoryManager(session_id)
    manager.initialize()
    
    # Simulate metrics
    if manager.aggregator:
        manager.aggregator.index["summary"] = {
            "total_delegates": 10,
            "total_handbacks": 9,
            "completed_tasks": 9,
            "failed_tasks": 0,
            "total_tokens": 125000,
            "average_quality_score": 91.3,
        }
    
    metrics = manager.get_metrics()
    
    print("Session Metrics:")
    print(f"  📊 Total DELEGATEs: {metrics.get('total_delegates', 0)}")
    print(f"  📊 Total HANDBACKs: {metrics.get('total_handbacks', 0)}")
    print(f"  ✅ Completed Tasks: {metrics.get('completed_tasks', 0)}")
    print(f"  ❌ Failed Tasks: {metrics.get('failed_tasks', 0)}")
    print(f"  🔥 Tokens Used: {metrics.get('total_tokens', 0):,}")
    print(f"  ⭐ Avg Quality: {metrics.get('average_quality_score', 0):.1f}/100")


def example_5_generate_summary():
    """Example 5: Generate and display session summary."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Generate Summary")
    print("=" * 60)
    
    session_id = "example-session-005"
    manager = SessionMemoryManager(session_id)
    manager.initialize()
    
    # Simulate data
    if manager.aggregator:
        manager.aggregator.index["summary"] = {
            "total_delegates": 8,
            "total_handbacks": 7,
            "completed_tasks": 6,
            "failed_tasks": 1,
            "total_tokens": 95000,
            "average_quality_score": 89.5,
        }
        manager.aggregator.index["delegates"] = [
            {"task_id": f"t{i}", "role": role}
            for i, role in enumerate([
                "Engineer", "Engineer", "Senior Engineer",
                "Lead Engineer", "Engineer", "Quality Engineer",
                "Model Engineer", "Senior Engineer",
            ])
        ]
    
    # Generate summary
    summary = manager.generate_summary()
    
    print("Generated Summary:")
    print(summary)
    
    # Export to file
    summary_path = manager.export_summary()
    print(f"\n✅ Summary exported to: {summary_path}")


def example_6_directory_structure():
    """Example 6: Inspect directory structure."""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Memory Directory Structure")
    print("=" * 60)
    
    session_id = "example-session-006"
    
    # Create memory structure
    subdirs = setup_session_memory(session_id)
    memory_dir = get_session_memory_dir(session_id)
    
    print(f"✅ Memory directory created: {memory_dir}")
    print("\nSubdirectories:")
    for name, path in sorted(subdirs.items()):
        # Only show relative path if it exists
        if path.exists():
            print(f"  📁 {name}/")
            # Show .keep file
            keep_file = path / ".keep"
            if keep_file.exists():
                print(f"     └─ .keep (marker file)")


def example_7_orchestrator_integration():
    """Example 7: How orchestrator integrates with memory system."""
    print("\n" + "=" * 60)
    print("EXAMPLE 7: Orchestrator Integration Pattern")
    print("=" * 60)
    
    print("""
Integration Pattern (in orchestrator.py):

```python
from src.orchestration.memory import SessionMemoryManager

class Orchestrator:
    def __init__(self, session_id):
        self.session_id = session_id
        self.memory = SessionMemoryManager(session_id)
        self.memory.initialize(metadata={
            "started_at": datetime.utcnow().isoformat(),
        })
    
    def delegate_task(self, delegate):
        # ... existing delegate logic ...
        
        # Record memory event
        self.memory.collect_memory_event("delegate", {
            "task_id": delegate["task_id"],
            "role": delegate["role"],
        })
    
    def process_handback(self, handback):
        # ... existing handback logic ...
        
        # Record memory event
        self.memory.collect_memory_event("handback", {
            "task_id": handback["task_id"],
            "status": handback["status"],
            "quality_score": handback["quality_score"],
        })
    
    def finalize_session(self):
        # Aggregate and export memory
        self.memory.aggregate_memory()
        self.memory.export_summary()
        
        # Get metrics for reporting
        return self.memory.get_metrics()
```
""")
    
    print("✅ Integration pattern shows how orchestrator uses memory system")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SESSION MEMORY SYSTEM - USAGE EXAMPLES")
    print("=" * 60)
    
    try:
        example_1_basic_session_lifecycle()
        example_2_query_by_task_id()
        example_3_query_by_role()
        example_4_metrics_dashboard()
        example_5_generate_summary()
        example_6_directory_structure()
        example_7_orchestrator_integration()
        
        print("\n" + "=" * 60)
        print("✅ ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nFor more details, see: docs/MEMORY-INTEGRATION.md")
        
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback
        traceback.print_exc()
