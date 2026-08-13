#!/usr/bin/env python3
"""
Regression gate: enforce minimum test counts per harness and overall.

FINAL STATE (SPEC-2026-005, framework slimdown, WP-5 — 2026-08-12):
WP-0 through WP-4 of the slimdown deleted ~165k LOC across src/orchestration,
src/harnesses, src/examples, src/internal, src/harness, src/claude,
src/copilot, src/evals, src/standardization, src/audit, src/config,
src/opencode, most of docs/, 17 auxiliary skills, and ~67k LOC of tests. A
volume-based floor could not gate that deliberate mass deletion, so the gate
ran permissive (floor 0) for the duration. The three per-harness baselines
(opencode/claude_code/copilot-cli) were dropped entirely: those test
directories covered src/harnesses/ modules with zero production callers and
were deleted as part of the slimdown.

Prior baselines (from harness-compatibility-baseline.md, 2026-06-14, long
retired — kept here for historical reference only):
  - OpenCode harness tests:    94  (tests/harnesses/opencode/)   [removed]
  - Claude Code harness tests: 103 (tests/harnesses/claude_code/) [removed]
  - Copilot CLI harness tests:  71 (tests/harnesses/copilot-cli/) [removed]
  - Full test suite (pre-slimdown): 4925 (total passing, excluding skipped/xfailed)

Re-baseline history (each ~95% of the measured actual at that point):
  - WP-5 (2026-08-12): 940 collected -> floor 893
  - Queue-layer removal, SPEC-2026-009 (2026-08-13): 866 collected -> floor 822
  - Infra reduction, round 2 (2026-08-13): scripts/detect_circular_imports.py,
    scripts/annotate_token_costs.py, scripts/validate_skills.py (merged into
    renderer/validate_skills.py), and run_pytest.sh were deleted as dead/
    vacuous infra (no test files covered them, so collected count did not
    drop from their removal); 8 new tests were added covering the merged
    renderer/validate_skills.py compliance-audit logic. Measured actual: 874
    collected -> floor 830 (874 * 0.95 = 830.3).
  - Polish wave-1, P9 (2026-08-13): tests/test_ci_container_environment.py
    (520 lines / 46 tests) was deleted -- it statically mirrored Dockerfile/
    Makefile text (e.g. asserting "FROM python:3.11" appears) and exercised
    generic OS filesystem/permission behavior unrelated to CI; it ran in
    ~1.2s with no docker daemon interaction (its one "docker" reference just
    shells out to `docker --version` and passes either way). CI does not use
    the Dockerfile -- all GitHub Actions workflows run via actions/setup-python
    -- so this was a change-detector, not a gate ("gates meaningful not
    ceremonial"). The Dockerfile itself and the test-ci/test-ci-force/
    test-ci-shell Makefile targets are untouched and remain a documented
    local CI-parity tool (see docs/CONTRIBUTING/README.md). tests/
    test_pre_push_hook.py was also deleted in an earlier batch but
    contributed 0 collected tests, so it does not appear in the count below.
    Measured actual: 828 collected (874 - 46) -> floor 786 (828 * 0.95 =
    786.6 -> 786).
  - Round 3 batch 1, WP-R3-04 (2026-08-13, OUT-OF-BAND -- see WP-R3-11 entry
    below): protocol-validator's dead enum-drift/protocol-divergence scanners
    were removed along with the 52 tests that pinned them (TestEnumDrift-
    Detection, TestProtocolDivergenceDetection). This measured 734 collected
    in tests/ and dropped the floor 786 -> 697 (734 * 0.95 = 697.3 -> 697).
    The change was made unilaterally by that work package's engineer, outside
    WP-R3-11's governance authority (which owns this file) -- flagged in
    commit 0aca2a0's message for lead-engineer review.
  - Round 3 batch 3, WP-R3-11 governed re-baseline (2026-08-13, task_id
    task-2026-08-13-r3-wp11-spec-floor): reviewed the WP-R3-04 deviation
    above. Between WP-R3-04 and this review, round-3 batch 2 added tests
    (parseability suite, round-trip proofs), so the honest current actual is
    higher than 734. Re-measured with this script's own methodology
    (`pytest tests/ --collect-only`, the same explicit path CI's `make test`
    passes -- NOT a bare `pytest --collect-only`, which is a different,
    larger number): 766 collected in tests/ -> floor 727 (766 * 0.95 = 727.7
    -> 727). The WP-R3-04 697 floor is reviewed and superseded by this
    governed re-baseline.
    SCOPE CLARIFICATION (the source of a planning-time arithmetic error this
    review caught): WP-R3-04 also expanded `pytest.ini`'s `testpaths` to
    include 3 skill-local test dirs (protocol-validator, spec-validator,
    skill-improvement-feedback), so a bare `pytest --collect-only` with no
    path argument now collects 935 (766 tests/ + 169 skill-local), and
    WP-R3-04's commit message quoted "903 total" at that time on the same
    basis. That 935/903-style figure is NOT what this gate measures or
    guards: `count_collected()` below always passes an explicit `test_path`,
    which overrides `testpaths` in pytest.ini, and CI's `make test` likewise
    invokes `pytest tests/ ...` explicitly (see Makefile `test:` target) --
    both scope the same 766-count population this file's BASELINES track.
    The 169 skill-local tests are gated separately, by
    `scripts/run_skill_tests.py`'s own `MIN_EXPECTED_TESTS` floor, run via
    `make test-skills` in its own subprocess per skill. Do not conflate the
    two floors or re-baseline this file against the bare-pytest number.
    FORWARD NOTE: round-3 batch 4 (WP-R3-05) is planned to remove tests
    duplicated across layers. Per this policy's own convention (every prior
    entry above re-baselines from a *measured* actual, never a forecast),
    this review deliberately does NOT pre-set a floor for that not-yet-landed
    change. When WP-R3-05 lands, re-measure `pytest tests/ --collect-only`
    honestly at that time and re-baseline again with QE sign-off -- do not
    reuse any pre-computed number from this task's planning context.

Exit 0 = all gates pass. Exit 1 = regression detected (CI will fail the build).
"""

import subprocess
import sys
import os
import re

# Baselines — update only via SPEC change + QE sign-off (see docs/REGRESSION-GATE-POLICY.md).
# Re-baselined 2026-08-13 (WP-R3-11, task_id task-2026-08-13-r3-wp11-spec-floor,
# QE-signed-off governed re-baseline) from the measured actual of 766 collected
# tests in tests/ (734 at WP-R3-04's out-of-band change + tests added by round-3
# batch 2). Floor is ~95% (766 * 0.95 = 727.7 -> 727). This supersedes WP-R3-04's
# unilateral 697 floor (flagged in commit 0aca2a0 for review) -- see this file's
# module docstring "Round 3 batch 3, WP-R3-11" entry for the full trajectory,
# the scope clarification (this floor tracks `pytest tests/`, NOT the larger
# bare-`pytest` count that also pulls in skill-local test dirs), and why the
# not-yet-landed WP-R3-05 duplicate-test removal is deliberately NOT
# pre-baselined here.
BASELINES = {
    "full_suite": {
        "path": "tests/",
        "minimum": 727,
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
    print("Regression Gate — minimum collected-test-count floor")
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
