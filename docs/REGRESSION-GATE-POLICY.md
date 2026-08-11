# Regression Gate Policy

**Status:** Interim permissive (SPEC-2026-005 framework slimdown, WP-0)
**Gate implementation:** `renderer/scripts/check_test_regression.py`
**CI enforcement:** `.github/workflows/ci.yml`

The Wave 2 per-harness baselines (OpenCode/Claude Code/Copilot CLI: 94/103/71
tests; full suite: 4925) are **suspended for the duration of the slimdown**.
The gate currently checks only `tests/` against a floor of `0` — a volume
floor cannot gate a deliberate mass deletion of ~165k LOC and ~67k LOC of
tests across `src/orchestration`, `src/harnesses`, `src/examples`,
`src/internal`, most of `docs/`, and 17 auxiliary skills.

**WP-5 of the slimdown re-baselines this gate** from measured post-deletion
actuals and restores real, non-zero floors. Until then this is a no-op that
keeps CI's "Gate 5" step in place to re-populate later.

Update baselines only via a `spec-management` proposal + Quality Engineer
sign-off. See `renderer/scripts/check_test_regression.py`'s header for the
full historical baseline record and interim-state rationale.
