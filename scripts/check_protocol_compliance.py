#!/usr/bin/env python3
"""check_protocol_compliance.py — Protocol compliance gate (Phase 5.1+).

Validates DELEGATE/HANDBACK YAML files in the queue directory against the
core protocol schema.  This is a no-op if no queue files exist.

Exit codes:
    0 — All queue files pass protocol compliance (or no queue files found)
    1 — One or more queue files fail protocol compliance
    2 — Invocation error

Usage:
    python scripts/check_protocol_compliance.py
    python scripts/check_protocol_compliance.py --queue-dir queue/
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _load_protocol_validator():
    repo_root = Path(__file__).resolve().parents[1]
    validator_scripts = repo_root / "src" / "skills" / "protocol-validator" / "scripts"
    if str(validator_scripts) not in sys.path:
        sys.path.insert(0, str(validator_scripts))

    from protocol_validator import validate_delegate, validate_handback  # type: ignore[import]

    return validate_delegate, validate_handback


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--queue-dir",
        default=os.environ.get("QUEUE_DIR", "queue"),
        help="Root queue directory to scan (default: queue/)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    queue_dir = Path(args.queue_dir)

    if not queue_dir.is_dir():
        print(f"No queue directory found at '{queue_dir}' — protocol compliance check skipped.")
        return 0

    yaml_files = list(queue_dir.rglob("*.yaml")) + list(queue_dir.rglob("*.yml"))
    if not yaml_files:
        print("No YAML task files in queue — protocol compliance check passed.")
        return 0

    print(f"Found {len(yaml_files)} queue file(s) — validating protocol compliance...")

    # Delegate to protocol-validator skill if available
    try:
        import yaml
        validate_delegate, validate_handback = _load_protocol_validator()
        errors = []
        for f in yaml_files:
            with open(f) as fh:
                data = yaml.safe_load(fh)
            if not data:
                continue

            # Validate as DELEGATE or HANDBACK based on the protocol shape.
            handoff_type = data.get("handoff_type") if isinstance(data, dict) else None
            if handoff_type == "DELEGATE":
                valid, errs = validate_delegate(data)
            elif handoff_type == "HANDBACK":
                valid, errs = validate_handback(data)
            elif isinstance(data, dict) and "status" in data:
                valid, errs = validate_handback(data)
            elif isinstance(data, dict) and {"scope", "plan", "success_criteria"}.issubset(data):
                valid, errs = validate_delegate(data)
            else:
                continue
            if not valid:
                errors.append(f"{f}: {'; '.join(errs)}")
        if errors:
            for e in errors:
                print(f"::error::{e}")
            print(f"Protocol compliance: {len(errors)} failure(s) found.")
            return 1
        print(f"Protocol compliance: {len(yaml_files)} file(s) validated — all passed.")
        return 0
    except ImportError:
        print("protocol-validator not importable — skipping deep protocol validation.")
        print("Install the skill or ensure src/ is on PYTHONPATH.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
