#!/usr/bin/env python3
"""
Test Agent: Echo Agent

Simple test agent that:
1. Reads DELEGATE from processing/ directory
2. Writes HANDBACK with status=success
3. Returns immediately

Used for testing basic DELEGATE → HANDBACK flow without actual work.

Usage:
    python echo_agent.py <queue_path> <task_id>

Example:
    python echo_agent.py ~/.agentic-engineers/test-session/test/queue task-001
"""

import sys
import yaml
from pathlib import Path
from datetime import datetime


def main():
    if len(sys.argv) < 3:
        print("Usage: echo_agent.py <queue_path> <task_id>", file=sys.stderr)
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

    # Create HANDBACK
    handback = {
        "handoff_type": "HANDBACK",
        "task_id": task_id,
        "agent": delegate.get("agent", "unknown"),
        "status": "success",
        "output": f"Echo agent processed {task_id}. Task completed successfully.",
        "metrics": {
            "quality": 0.95,
            "tokens": 1000,
            "cost": 0.02,
            "duration_seconds": 1,
        },
        "confidence": 0.95,
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
