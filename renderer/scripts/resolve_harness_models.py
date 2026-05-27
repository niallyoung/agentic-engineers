#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from renderer.model_registry import HarnessModelRegistry


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve harness-specific agent models")
    parser.add_argument("--harness", required=True, choices=["copilot", "claude", "opencode", "pi"])
    parser.add_argument("--agent", help="Resolve a single agent name")
    parser.add_argument("--list-agent-models", action="store_true", help="Print all agent\tmodel pairs")
    args = parser.parse_args()

    registry = HarnessModelRegistry(repo_root=REPO_ROOT)

    if args.agent:
        print(registry.render_model(args.agent, args.harness))
        return 0

    if args.list_agent_models:
        for target in registry.model_targets(args.harness):
            print(f"{target.agent_name}\t{target.model}")
        return 0

    parser.error("choose --agent or --list-agent-models")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
