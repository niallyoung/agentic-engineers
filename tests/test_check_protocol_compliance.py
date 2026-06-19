from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_protocol_compliance.py"


def test_check_protocol_compliance_validates_handback(tmp_path):
    queue_dir = tmp_path / "queue" / "processing"
    queue_dir.mkdir(parents=True)

    handback = {
        "handoff_type": "HANDBACK",
        "task_id": "compliance-check-001",
        "status": "success",
        "output": {"notes": "validated"},
        "metrics": {
            "quality": 1.0,
            "tokens": 1,
            "cost": 0.0,
            "duration_seconds": 0.01,
        },
    }
    (queue_dir / "compliance-check.yaml").write_text(yaml.safe_dump(handback), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--queue-dir", str(tmp_path / "queue")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "validated" in result.stdout.lower()
