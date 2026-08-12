# Regression Gate Policy

**Status:** Final baseline restored (SPEC-2026-005 framework slimdown, WP-5, 2026-08-12)
**Gate implementation:** `renderer/scripts/check_test_regression.py`
**CI enforcement:** `.github/workflows/ci.yml`

The Wave 2 per-harness baselines (OpenCode/Claude Code/Copilot CLI: 94/103/71
tests; pre-slimdown full suite: 4925) were **suspended for the duration of the
slimdown** (WP-0 through WP-4): a volume floor cannot gate a deliberate mass
deletion of ~165k LOC and ~67k LOC of tests across `src/orchestration`,
`src/harnesses`, `src/examples`, `src/internal`, most of `docs/`, and 17
auxiliary skills. The three per-harness baselines are retired permanently —
those test directories covered `src/harnesses/` modules with zero production
callers and no longer exist.

**WP-5 re-baselines this gate** from the measured post-deletion actual: a
plain `python3 -m pytest tests/ --collect-only -q` on the fully-slimmed tree
(8 skills, 8 agents, 4 harnesses — claude/copilot/opencode/codex, no pi)
collected 940 tests. The gate's floor is now `893` (~95% of that actual),
giving headroom for small legitimate future removals without silently
re-permitting a mass regression.

A companion floor, `scripts/run_skill_tests.py`'s `MIN_EXPECTED_TESTS`, was
re-baselined the same way: 250 measured skill-local tests across the 5
script-backed skills, floor `237` (~95%).

Update baselines only via a `spec-management` proposal + Quality Engineer
sign-off. See `renderer/scripts/check_test_regression.py`'s header for the
full historical baseline record and re-baselining rationale.
