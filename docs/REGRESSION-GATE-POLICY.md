# Regression Gate Policy

**Status:** Re-baselined (round 3 batch 3, WP-R3-11, governed re-baseline with QE
sign-off, 2026-08-13)
**Gate implementation:** `renderer/scripts/check_test_regression.py`
**CI enforcement:** `.github/workflows/ci.yml`
**Scope:** This policy and gate track `pytest tests/` only (the same explicit path
CI's `make test` passes). A companion, separately-policed floor covers the 3
skill-local test dirs — see "Companion floor" below. Do not conflate the two: a
bare `pytest --collect-only` (no path argument) picks up `pytest.ini`'s `testpaths`
and returns a larger, combined number that neither gate uses directly.

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
| Polish wave-1, P9 (2026-08-13) | `tests/test_ci_container_environment.py` deleted (change-detector, not a gate — see gate header for full rationale) | 828 | 786 |
| **Round 3 batch 1, WP-R3-04 (2026-08-13) — OUT-OF-BAND** | protocol-validator dead enum-drift/divergence scanners removed with their 52 pinning tests. Made unilaterally by that work package's engineer, outside WP-R3-11's governance authority over this file — flagged in commit 0aca2a0's message | 734 | ~~697~~ *superseded below* |
| **Round 3 batch 3, WP-R3-11 (2026-08-13) — governed re-baseline** | Lead Engineer review of the WP-R3-04 deviation above, per `spec-management`, with Quality Engineer sign-off (task_id `task-2026-08-13-r3-wp11-spec-floor`). Round-3 batch 2 added tests between WP-R3-04 and this review, so honest current actual (766) is higher than WP-R3-04's 734. This entry supersedes WP-R3-04's 697 floor | 766 | **727** |

A companion floor, `scripts/run_skill_tests.py`'s `MIN_EXPECTED_TESTS`, is
unaffected by this round's `tests/`-scoped changes (no skill-local tests were
touched): 169 measured skill-local tests across the 3 script-backed skills
collected via `pytest.ini`'s `testpaths`, floor `169`.

**Out-of-band deviation, reviewed and superseded:** WP-R3-04's 697 floor (row
above) was set without going through this file's governance owner and is
recorded here for audit continuity, not as a standing baseline — WP-R3-11's 727
floor is the current one. See `renderer/scripts/check_test_regression.py`'s
module docstring for the full narrative, including the scope-mismatch this
review caught (a bare `pytest --collect-only` returns ~935, not the 766 this
gate and CI's `make test` actually measure — WP-R3-04's own commit message used
the larger, non-gated number when describing its change).

**Not pre-baselined:** round-3 batch 4 (WP-R3-05) plans to remove tests
duplicated across the `tests/` and skill-local layers. Consistent with every
entry in this table re-baselining from a *measured* actual and never a
forecast, WP-R3-11 deliberately did not set a floor anticipating that
not-yet-landed change. Re-measure honestly and re-baseline (with QE sign-off)
once WP-R3-05 lands.

Update baselines only via a `spec-management` proposal + Quality Engineer
sign-off — the round-2 update was made directly under an explicit
senior-engineer DELEGATE mandate to re-baseline honestly at the end of that
task and did not get a separate QE sign-off pass; WP-R3-11 (this update) does
carry an independent QE sign-off — see the HANDBACK for task_id
`task-2026-08-13-r3-wp11-spec-floor`. See
`renderer/scripts/check_test_regression.py`'s header for the full historical
baseline record and re-baselining rationale.
