#!/usr/bin/env python3
"""
Regression gate: enforce minimum test counts per harness and overall.

Wave 2 baselines (from harness-compatibility-baseline.md, 2026-06-14):
  - OpenCode harness tests:    94  (tests/harnesses/opencode/)
  - Claude Code harness tests: 103 (tests/harnesses/claude_code/)
  - Copilot CLI harness tests:  71 (tests/harnesses/copilot-cli/)
  - Full test suite:          4925 (total passing, excluding skipped/xfailed)

Exit 0 = all gates pass. Exit 1 = regression detected (CI will fail the build).
"""

import sys
import os

import pytest

# Wave 2 baselines — update only via SPEC change + QE sign-off
BASELINES = {
    "opencode_harness": {
        "path": "tests/harnesses/opencode/",
        "minimum": 94,
        "label": "OpenCode harness",
    },
    "claude_code_harness": {
        "path": "tests/harnesses/claude_code/",
        "minimum": 103,
        "label": "Claude Code harness",
    },
    "copilot_cli_harness": {
        "path": "tests/harnesses/copilot-cli/",
        "minimum": 71,
        "label": "Copilot CLI harness",
    },
    "full_suite": {
        "path": "tests/",
        "minimum": 4925,
        "label": "Full test suite",
    },
}


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def count_collected(test_path: str) -> int:
    """Return number of tests collected by pytest for a given path."""
    abs_path = os.path.join(REPO_ROOT, test_path)
    collected = []

    class _CollectorPlugin:
        def pytest_collection_finish(self, session):  # type: ignore[no-untyped-def]
            collected.extend(session.items)

    rc = pytest.main([abs_path, "--collect-only", "-q", "--tb=no"], plugins=[_CollectorPlugin()])
    if rc not in (0, 5):
        return 0
    return len(collected)


def main() -> int:
    failures = []
    print("Regression Gate — Wave 2 Baseline Check")
    print("=" * 60)

    for key, spec in BASELINES.items():
        count = count_collected(spec["path"])
        minimum = spec["minimum"]
        label = spec["label"]
        status = "PASS" if count >= minimum else "FAIL"
        delta = count - minimum
        delta_str = f"+{delta}" if delta >= 0 else str(delta)
        print(f"  {status}  {label}: {count} tests (baseline {minimum}, delta {delta_str})")
        if status == "FAIL":
            failures.append(
                f"{label}: {count} tests collected, minimum is {minimum} "
                f"(regression of {abs(delta)} tests)"
            )

    print()
    if failures:
        print("REGRESSION DETECTED — the following gates failed:")
        for f in failures:
            print(f"  - {f}")
        print()
        print("Recovery: see docs/REGRESSION-GATE-POLICY.md for triage procedure.")
        return 1

    print("All regression gates PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
