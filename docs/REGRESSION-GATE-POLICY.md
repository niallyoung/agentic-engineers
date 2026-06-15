# Regression Gate Policy

**Status**: Active  
**Effective**: 2026-06-14  
**Owner**: Quality Engineer  
**Gate implementation**: `scripts/check_test_regression.py`  
**CI enforcement**: `.github/workflows/ci.yml` — Gate 5

---

## Purpose

The regression gate is a CI-enforced hard stop that prevents merges whenever the
test count for any harness drops below its Wave 2 baseline. It ensures that
improvements made during Milestone 2 harness hardening are never silently reversed.

---

## Wave 2 Baselines

Baselines were captured from `docs/archive/audits/harness-compatibility-baseline.md`
(generated 2026-06-14, signed off by Quality Engineer on branch `chore/m2-harness-eval-baseline`).

| Harness | Test Path | Minimum Tests | Current (2026-06-14) |
|---|---|---|---|
| OpenCode | `tests/harnesses/opencode/` | **94** | 94 |
| Claude Code | `tests/harnesses/claude_code/` | **103** | 103 |
| Copilot CLI | `tests/harnesses/copilot-cli/` | **71** | 71 |
| Full suite | `tests/` | **4925** | 5189 |

The full-suite baseline (4925) is the total tests collected at Wave 2 sign-off
(4771 passed + 149 skipped + 5 xfailed = 4925 total).

---

## How the Gate Works

`scripts/check_test_regression.py` runs `pytest --collect-only` for each harness
path and the full suite. It compares the collected count against the baseline.
If any count is below the minimum, the script exits non-zero and CI fails.

The gate runs as "Gate 5" in `.github/workflows/ci.yml`, after the test suite
completes. It does not re-execute tests; it only counts what is collectible,
making it fast (adds ~10s to CI runtime).

---

## Updating Baselines

Baselines must only be raised (never lowered) under the following conditions:

1. New tests were added that increase the count legitimately.
2. A Quality Engineer has reviewed and signed off on the new count.
3. The baseline update is accompanied by a documented reason in this file.

To update a baseline:
1. Edit the `BASELINES` dict in `scripts/check_test_regression.py`.
2. Update the table above with the new counts and date.
3. Include a "Baseline Change Log" entry (see below).

Lowering a baseline requires Principal Engineer approval and a recorded exception.

---

## Recovery Procedure (CI Failing)

When Gate 5 fails, the CI output will show which harness regressed and by how many tests.

**Step 1 — Identify the regression**

```bash
python scripts/check_test_regression.py
```

**Step 2 — Find the removed tests**

```bash
# Compare test discovery between current branch and main
git stash
python3 -m pytest tests/harnesses/opencode/ --collect-only -q > /tmp/main_tests.txt
git stash pop
python3 -m pytest tests/harnesses/opencode/ --collect-only -q > /tmp/branch_tests.txt
diff /tmp/main_tests.txt /tmp/branch_tests.txt
```

**Step 3 — Triage**

| Cause | Action |
|---|---|
| Tests accidentally deleted | Restore the deleted test file/class |
| Test file moved | Update import path; ensure new path is under the harness directory |
| Test collection error (import fail) | Fix the import error in the test file |
| Intentional deletion | Requires QE sign-off + baseline update in same PR |

**Step 4 — Verify fix**

```bash
python scripts/check_test_regression.py
```

Gate must pass locally before pushing.

---

## Baseline Change Log

| Date | Harness | Old Minimum | New Minimum | Reason | Approved By |
|---|---|---|---|---|---|
| 2026-06-14 | All | — | 94/103/71/4925 | Wave 2 baseline established | Quality Engineer |
