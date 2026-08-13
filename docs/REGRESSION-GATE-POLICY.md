# Regression Gate Policy

**Status:** Re-baselined (infra reduction round 2, 2026-08-13)
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

Re-baseline history (each floor is ~95% of the measured actual at that time):

| When | Event | Measured | Floor |
|------|-------|---------:|------:|
| WP-5 (2026-08-12) | Framework slimdown final state | 940 | 893 |
| SPEC-2026-009 (2026-08-13) | Filesystem queue layer removed | 866 | 822 |
| Infra reduction round 2 (2026-08-13) | Dead/vacuous CI+hook infra removed (`detect_circular_imports.py`, `annotate_token_costs.py`, duplicate `validate_skills.py` merged into `renderer/validate_skills.py`, `run_pytest.sh`); 8 tests added for the merged compliance-audit logic | 874 | 830 |

A companion floor, `scripts/run_skill_tests.py`'s `MIN_EXPECTED_TESTS`, is
unaffected by the round-2 infra reduction (no skill-local tests were touched):
178 measured skill-local tests across the 3 script-backed skills, floor `169`.

Update baselines only via a `spec-management` proposal + Quality Engineer
sign-off — the round-2 update above was made directly under an explicit
senior-engineer DELEGATE mandate to re-baseline honestly at the end of that
task; it has not yet had a separate QE sign-off pass. See
`renderer/scripts/check_test_regression.py`'s header for the full historical
baseline record and re-baselining rationale.
