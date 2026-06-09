#!/usr/bin/env python3
"""
Test Agent: Escalate Agent

Test agent that:
1. Reads DELEGATE from processing/ directory
2. Writes HANDBACK with status=escalate
3. Includes escalation reason

Used for testing escalation chain: status=escalate → creates new DELEGATE
at higher level (e.g., engineer → senior_engineer).

Usage:
    python escalate_agent.py <queue_path> <task_id> [escalation_reason]

Example:
    python escalate_agent.py ~/.agentic-engineers/test-session/test/queue task-001 "Complexity exceeds scope"
"""

import sys
import yaml
from pathlib import Path
from datetime import datetime


def main():
    if len(sys.argv) < 3:
        print("Usage: escalate_agent.py <queue_path> <task_id> [escalation_reason]", file=sys.stderr)
        sys.exit(1)

    queue_path = Path(sys.argv[1])
    task_id = sys.argv[2]
    escalation_reason = sys.argv[3] if len(sys.argv) > 3 else "Task complexity exceeds agent scope"

    processing_dir = queue_path / "processing"

    # Read DELEGATE
    delegate_file = processing_dir / f"{task_id}.yaml"
    if not delegate_file.exists():
        print(f"Error: DELEGATE not found: {delegate_file}", file=sys.stderr)
        sys.exit(1)

    with open(delegate_file, "r") as f:
        delegate = yaml.safe_load(f)

    # Create HANDBACK with escalation
    handback = {
        "handoff_type": "HANDBACK",
        "task_id": task_id,
        "agent": delegate.get("agent", "unknown"),
        "status": "escalate",
        "output": f"Escalating {task_id}: {escalation_reason}",
        "metrics": {
            "quality": 0.60,
            "tokens": 1200,
            "cost": 0.025,
            "duration_seconds": 45,
        },
        "confidence": 0.40,
        "escalations": [escalation_reason],
        "escalation_target": "senior-engineer",
        "timestamp": datetime.now().isoformat(),
    }

    # Write HANDBACK
    handback_file = processing_dir / f"HANDBACK-{task_id}.yaml"
    with open(handback_file, "w") as f:
        yaml.dump(handback, f)

    print(f"✓ HANDBACK (escalate) written: {handback_file}")
    print(f"  Escalation reason: {escalation_reason}")
    sys.exit(0)


if __name__ == "__main__":
    main()
