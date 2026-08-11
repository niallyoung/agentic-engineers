#!/usr/bin/env python3
"""
Regression gate: enforce minimum test counts per harness and overall.

INTERIM STATE (SPEC-2026-005, framework slimdown, WP-0 — 2026-08-11):
The Wave 2 per-harness and full-suite baselines below have been set
PERMISSIVE (floors of 0) for the duration of the multi-package slimdown
(~165k LOC across src/orchestration, src/harnesses, src/examples,
src/internal, src/harness, src/claude, src/copilot, src/evals,
src/standardization, src/audit, src/config, src/opencode, most of docs/,
17 auxiliary skills, and ~67k LOC of tests). A volume-based floor cannot
gate a deliberate mass deletion. The three per-harness baselines
(opencode/claude_code/copilot-cli) have been dropped entirely: those test
directories cover src/harnesses/ modules with zero production callers and
are deleted as part of this slimdown.

WP-5 of the slimdown re-baselines this gate from measured post-deletion
actuals and restores real (non-zero) floors. Until then this gate is a
no-op that exists only so CI keeps a "Gate 5" step to re-populate later.

Prior baselines (from harness-compatibility-baseline.md, 2026-06-14, now
retired — kept here for historical reference only):
  - OpenCode harness tests:    94  (tests/harnesses/opencode/)   [removed]
  - Claude Code harness tests: 103 (tests/harnesses/claude_code/) [removed]
  - Copilot CLI harness tests:  71 (tests/harnesses/copilot-cli/) [removed]
  - Full test suite:          4925 (total passing, excluding skipped/xfailed)

Exit 0 = all gates pass. Exit 1 = regression detected (CI will fail the build).
"""

import subprocess
import sys
import os
import re

# Baselines — update only via SPEC change + QE sign-off (see docs/REGRESSION-GATE-POLICY.md).
# Interim permissive floor during SPEC-2026-005 slimdown; WP-5 restores real minimums.
BASELINES = {
    "full_suite": {
        "path": "tests/",
        "minimum": 0,
        "label": "Full test suite",
    },
}


# Script lives at <repo>/renderer/scripts/check_test_regression.py, so the repo
# root is three levels up (scripts/ -> renderer/ -> repo). Test paths below are
# resolved relative to REPO_ROOT and pytest runs with cwd=REPO_ROOT.
REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


def count_collected(test_path: str) -> int:
    """Return number of tests collected by pytest for a given path."""
    abs_path = os.path.join(REPO_ROOT, test_path)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", abs_path, "--collect-only", "-q", "--tb=no"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    # Parse "N tests collected" or "N test collected" from stdout or stderr
    # Example line: "94 tests collected in 0.09s"
    # Strip ANSI color codes first (pytest may include them)
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    output = ansi_escape.sub('', result.stdout + result.stderr)
    for line in reversed(output.splitlines()):
        line = line.strip()
        if "collected" in line:
            parts = line.split()
            for i, part in enumerate(parts):
                if part in ("collected", "test", "tests") and i > 0:
                    try:
                        count = int(parts[0])
                        return count
                    except (ValueError, IndexError):
                        pass
    return 0


def main() -> int:
    failures = []
    print("Regression Gate — interim permissive baseline (SPEC-2026-005)")
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
