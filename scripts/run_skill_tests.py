#!/usr/bin/env python3
"""
run_skill_tests.py — Execute every src/skills/**/tests/ suite in CI.

## Why this exists (C6)

`pytest.ini` sets `testpaths = tests`, so tests living under `src/skills/*/tests/`
are never collected by `make test` / CI on their own — each surviving skill's
test files need their own CI visibility via this runner. Of the 8 skills, 3 are
script-backed and carry a tests/ suite: protocol-validator, spec-validator and
skill-improvement-feedback.

The obvious fix — add `src/skills` to `testpaths` and run one big `pytest`
session — does NOT work correctly here: many skills use the identical
in-skill import pattern

    sys.path.insert(0, <own skill dir>)
    from scripts.foo import Bar

Because each skill's `scripts/` package is a *regular* package (it has
`__init__.py`), Python caches the first `scripts` package it resolves in
`sys.modules['scripts']`. Every subsequent skill's `sys.path.insert` is
silently ignored — the cached module wins. Collected in one process, only
the first skill's `scripts.*` imports resolve correctly; the rest raise
`ModuleNotFoundError`, or worse, run against a different skill's code
without erroring at all.

This runner sidesteps the collision by giving every skill's test suite its
own subprocess (its own fresh `sys.modules`), which is exactly the
isolation each skill already relied on when its tests were run standalone.
Coverage data from every subprocess is accumulated into the same
`.coverage` file via `--cov-append`, so `make test` (which also writes to
`.coverage`) and this script combine into one coverage report.

Usage:
    python3 scripts/run_skill_tests.py            # run + summarize
    python3 scripts/run_skill_tests.py --list      # just list discovered dirs
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = REPO_ROOT / "src" / "skills"

# Below this many total collected tests, something regressed (a skill's
# tests dir went missing, got excluded, etc.) — fail loudly rather than
# silently reporting a shrinking number.
#
# Floor is ~95% of the measured actual (289 tests across the 3 script-backed
# skills), matching renderer/scripts/check_test_regression.py's convention.
# Rationale and re-baselining rules: docs/REGRESSION-GATE-POLICY.md.
MIN_EXPECTED_TESTS = 274

# Some skill suites exercise the real repository tree end-to-end rather than an
# isolated fixture, so they run slower than a typical unit suite. Bounded.
SUBPROCESS_TIMEOUT_SECONDS = 600

# Matches every count-bearing token in pytest's final summary line, e.g.:
#   "41 passed in 24.28s"
#   "1 failed, 6 passed in 0.06s"
#   "3 passed, 2 skipped, 1 warning in 0.4s"
#   "no tests ran in 0.01s"
SUMMARY_COUNT_RE = re.compile(r"(\d+) (passed|failed|error|errors|skipped)")


def discover_skill_test_dirs() -> list[Path]:
    """Every directory under src/skills containing a tests/ dir with test_*.py files."""
    dirs = []
    for tests_dir in sorted(SKILLS_ROOT.glob("**/tests")):
        if not tests_dir.is_dir():
            continue
        if any(tests_dir.glob("test_*.py")):
            dirs.append(tests_dir)
    return dirs


def _count_from_summary(output: str) -> int:
    """Sum every counted bucket (passed/failed/error/skipped) in pytest's final summary line."""
    lines = output.strip().splitlines()
    for line in reversed(lines):
        matches = SUMMARY_COUNT_RE.findall(line)
        if matches:
            return sum(int(n) for n, _ in matches)
    return 0


def run_one(tests_dir: Path, cov_append: bool) -> tuple[bool, str, int]:
    """Run one skill's tests in an isolated subprocess. Returns (ok, tail_output, count)."""
    rel = tests_dir.relative_to(REPO_ROOT)
    skill_dir = tests_dir.parent
    cov_target = skill_dir.relative_to(REPO_ROOT)

    cmd = [
        sys.executable, "-m", "pytest", str(rel),
        "--import-mode=importlib",
        # Scope `scripts` package resolution to THIS skill only. Several
        # skills' tests do `from scripts.foo import Bar` without their own
        # sys.path.insert, relying on the ini-level `pythonpath`. Overriding
        # it per-subprocess (rather than listing every skill in pytest.ini)
        # is what actually gives each skill an isolated, correct `scripts`
        # package — see the pytest.ini and module-docstring notes.
        "-o", f"pythonpath={cov_target}",
        "-q", "--tb=short",
        f"--cov={cov_target}",
        "--cov-report=",
    ]
    if cov_append:
        cmd.append("--cov-append")

    try:
        proc = subprocess.run(
            cmd, cwd=REPO_ROOT, capture_output=True, text=True,
            timeout=SUBPROCESS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        partial = (exc.stdout or "") + (exc.stderr or "")
        tail = "\n".join(partial.strip().splitlines()[-15:])
        return False, (
            f"TIMED OUT after {SUBPROCESS_TIMEOUT_SECONDS}s\n{tail}"
        ), 0

    output = proc.stdout + proc.stderr
    last_lines = "\n".join(output.strip().splitlines()[-15:])

    ok = proc.returncode == 0
    count = _count_from_summary(output)

    return ok, last_lines, count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List discovered skill test dirs and exit")
    parser.add_argument("--no-cov-append", action="store_true", help="Don't accumulate coverage (faster, standalone runs)")
    args = parser.parse_args()

    test_dirs = discover_skill_test_dirs()

    if args.list:
        for d in test_dirs:
            print(d.relative_to(REPO_ROOT))
        print(f"\n{len(test_dirs)} skill test directories discovered")
        return 0

    print(f"Running {len(test_dirs)} isolated skill test suites "
          f"(each in its own subprocess to avoid cross-skill 'scripts' package collisions)...\n")

    total_tests = 0
    failures = []
    start = time.time()

    for i, tests_dir in enumerate(test_dirs, 1):
        rel = tests_dir.relative_to(REPO_ROOT)
        ok, tail, count = run_one(tests_dir, cov_append=not args.no_cov_append)
        total_tests += count
        status = "ok" if ok else "FAIL"
        print(f"[{i:>2}/{len(test_dirs)}] {status:<4} {rel}  ({count} tests)")
        if not ok:
            failures.append((rel, tail))

    elapsed = time.time() - start
    print(f"\n{'=' * 70}")
    print(f"Skill test suites: {len(test_dirs)} directories, "
          f"{total_tests} tests, {len(failures)} failing suites, "
          f"{elapsed:.1f}s")

    if failures:
        print("\nFAILING SUITES:\n")
        for rel, tail in failures:
            print(f"--- {rel} ---")
            print(tail)
            print()
        print(f"❌ {len(failures)} skill test suite(s) failed")
        return 1

    if total_tests < MIN_EXPECTED_TESTS:
        print(
            f"❌ Only {total_tests} skill tests collected, expected at least "
            f"{MIN_EXPECTED_TESTS}. A skill's tests/ dir may have been lost, "
            f"renamed, or excluded — investigate before lowering this floor."
        )
        return 1

    print(f"✅ All skill test suites passed ({total_tests} tests)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
