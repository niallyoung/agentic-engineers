#!/usr/bin/env python3
"""
Test Agent: Delay Agent

Test agent that:
1. Reads DELEGATE from processing/ directory
2. Sleeps for 2 seconds (simulates work)
3. Writes HANDBACK with status=success

Used for testing async/concurrent DELEGATE processing with timing.

Usage:
    python delay_agent.py <queue_path> <task_id>

Example:
    python delay_agent.py ~/.agentic-engineers/test-session/test/queue task-001
"""

import sys
import yaml
import time
from pathlib import Path
from datetime import datetime


def main():
    if len(sys.argv) < 3:
        print("Usage: delay_agent.py <queue_path> <task_id>", file=sys.stderr)
        sys.exit(1)

    queue_path = Path(sys.argv[1])
    task_id = sys.argv[2]

    processing_dir = queue_path / "processing"

    # Read DELEGATE
    delegate_file = processing_dir / f"{task_id}.yaml"
    if not delegate_file.exists():
        print(f"Error: DELEGATE not found: {delegate_file}", file=sys.stderr)
        sys.exit(1)

    with open(delegate_file, "r") as f:
        delegate = yaml.safe_load(f)

    # Simulate work
    print(f"Processing {task_id}...")
    time.sleep(2)

    # Create HANDBACK
    handback = {
        "handoff_type": "HANDBACK",
        "task_id": task_id,
        "agent": delegate.get("agent", "unknown"),
        "status": "success",
        "output": f"Delay agent processed {task_id} after 2 second delay. Task completed successfully.",
        "metrics": {
            "quality": 0.90,
            "tokens": 1500,
            "cost": 0.03,
            "duration_seconds": 2,
        },
        "confidence": 0.90,
        "escalations": [],
        "timestamp": datetime.now().isoformat(),
    }

    # Write HANDBACK
    handback_file = processing_dir / f"HANDBACK-{task_id}.yaml"
    with open(handback_file, "w") as f:
        yaml.dump(handback, f)

    print(f"✓ HANDBACK written: {handback_file}")
    sys.exit(0)


if __name__ == "__main__":
    main()
