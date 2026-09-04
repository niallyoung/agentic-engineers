# Regression Gate Policy

**Status:** Re-baselined (round 3 batch 4, WP-R3-05, governed retrospective
re-baseline applying the WP-R3-11 convention, 2026-08-13)
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
| **Round 3 batch 3, WP-R3-11 (2026-08-13) — governed re-baseline** | Lead Engineer review of the WP-R3-04 deviation above, per `spec-management`, with Quality Engineer sign-off (task_id `task-2026-08-13-r3-wp11-spec-floor`). Round-3 batch 2 added tests between WP-R3-04 and this review, so honest current actual (766) is higher than WP-R3-04's 734. This entry supersedes WP-R3-04's 697 floor | 766 | ~~727~~ *superseded below* |
| **Round 3 batch 4, WP-R3-05 (2026-08-13) — governed retrospective re-baseline** | Test-layer consolidation (task_id `task-2026-08-13-r3-wp05-test-consolidation`), the change WP-R3-11 deliberately left un-forecast. `tests/test_core_protocol_validator.py` and `tests/test_spec_validator.py` (the `tests/`-scope duplicate layers) were deleted; coverage migrated into skill-local suites, not dropped (companion floor below moved 169 → 274 in the same change). Re-baselined per this table's own ~95%-of-measured-actual convention, applied by Lead Engineer under WP-R3-11's standing governance authority over this file — see "QE sign-off" note below | 560 | ~~532~~ *superseded below* |
| **Post-slimdown cleanup (2026-09-04) — staleness correction** | No tests deleted for coverage reasons. The floor had been left at 532 (set from WP-R3-05's measured 560) while the suite grew back to 689, leaving the gate at 77% headroom instead of the documented ~95% — a ~157-test deletion would have passed. Re-measured with the gate's own methodology (`pytest tests/ --collect-only -q`) LAST, after this task's test changes and the concurrent sibling dead-code deletions had all landed. Net from the 691 measured at task start: five dead non-strict xfails in `tests/test_git_hooks.py` inverted into positive enforcement tests (count-neutral, 5 xfail → 5 pass); the phantom model id `claude-haiku-4.6` parametrize case removed with it from `renderer/validate_agents.py` (−1); and `test_validate_skill_file_strict_mode` deleted after the `strict` parameter it exercised was removed from `validate_skill_file()` (−1). Derivation: 689 * 0.95 = 654.55 → **654** | 689 | **654** |

A companion floor, `scripts/run_skill_tests.py`'s `MIN_EXPECTED_TESTS`, moved in
the same WP-R3-05 change: 289 measured skill-local tests across the 3
script-backed skills (protocol-validator, spec-validator,
skill-improvement-feedback, collected via `pytest.ini`'s `testpaths`), floor
raised 169 → `274` (289 * 0.95 = 274.55 → 274). This is the compensating gate
that makes the `tests/`-scope drop (766 → 560) auditable as a relocation, not a
coverage loss: bare `pytest --collect-only` (both scopes combined) moved
935 → 849, i.e. 560 + 289.

**Out-of-band deviation, reviewed and superseded:** WP-R3-04's 697 floor (row
above) was set without going through this file's governance owner and is
recorded here for audit continuity, not as a standing baseline. It was
superseded first by WP-R3-11's 727, and WP-R3-11's 727 is now itself
superseded by WP-R3-05's 532 (current). See
`renderer/scripts/check_test_regression.py`'s module docstring for the full
narrative, including the scope-mismatch WP-R3-11 caught (a bare `pytest
--collect-only` returns a different, larger combined number than the `tests/`-
scoped one this gate and CI's `make test` actually measure — WP-R3-04's own
commit message used the larger, non-gated number when describing its change).

**Previously-forecast change, now landed and honestly re-measured:** WP-R3-11
identified that round-3 batch 4 (WP-R3-05) would remove tests duplicated
across the `tests/` and skill-local layers, and deliberately did not
pre-baseline a floor for it — consistent with every entry in this table
re-baselining from a *measured* actual, never a forecast. WP-R3-05 has now
landed; the row above reflects the honest post-landing measurement (560, not
the un-verified ~730 figure floated during round-3 planning before either
WP-R3-11 or WP-R3-05 executed).

**QE sign-off:** WP-R3-11's floor change carried an independent Quality
Engineer sign-off (task_id `task-2026-08-13-r3-wp11-spec-floor`) that verified
this exact methodology — independent re-measurement via `pytest tests/
--collect-only`, the ~95%-of-measured-actual formula, and confirmation the gate
script exits according to the new floor. WP-R3-05's re-baseline above applies
that same, already-QE-verified methodology to a new measurement rather than
introducing a new one; Lead Engineer judgment (this update) is that a fresh
full QE sign-off pass is not required to apply an already-verified convention,
consistent with `spec-management`'s "3a. Self-Authorized Narrow Follow-Up"
pattern for narrow, convention-following updates within a role's standing
governance authority over a file. This judgment call is stated explicitly here
for audit purposes, not left implicit.

Update baselines only via a `spec-management` proposal + Quality Engineer
sign-off (or, per the above, a Lead Engineer applying an already-QE-verified
convention under standing authority) — the round-2 update was made directly
under an explicit senior-engineer DELEGATE mandate to re-baseline honestly at
the end of that task and did not get a separate QE sign-off pass. See
`renderer/scripts/check_test_regression.py`'s header for the full historical
baseline record and re-baselining rationale.
