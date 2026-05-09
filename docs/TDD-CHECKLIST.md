# TDD Checklist — Engineer Reference Card

Use this checklist for every code change. Complete each section in order.
Copy this into your HANDBACK or PR description to show compliance.

---

## Pre-Work

- [ ] I have read `docs/TDD-SKILL.md` for this session
- [ ] I understand the requirement I am implementing
- [ ] I know which source file(s) will change: `src/orchestration/agents/<module>.py`
- [ ] I know which test file(s) to create or update: `tests/test_<module>.py`
- [ ] I confirmed no existing tests already cover this behaviour

---

## Phase 1 — RED (Tests First)

- [ ] Test file created or updated **before** touching source code
- [ ] Tests cover happy path, edge cases, and error cases
- [ ] Ran tests; all new tests **FAIL** (confirmed red state)
- [ ] Failure messages are meaningful — they point to the right missing behaviour
- [ ] WIP test commit made (`test(wip): <description>`)

**Evidence:** Paste the failing test output here:

```
# PASTE: pytest -v output showing FAILED for new tests
```

---

## Phase 2 — GREEN (Minimum Implementation)

- [ ] Implemented minimum code to make failing tests pass
- [ ] Ran full suite: **all new tests PASS**
- [ ] No regressions: all previously-passing tests still pass
- [ ] No extra code added beyond what tests require
- [ ] Implementation committed

**Evidence:** Paste the passing test output here:

```
# PASTE: pytest -v output showing all new tests PASSED
```

---

## Phase 3 — REFACTOR (Clean Up)

- [ ] Removed code duplication
- [ ] Renamed variables/functions for clarity
- [ ] Added or updated docstrings
- [ ] Ran `make lint` (or `flake8 src/ tests/`) — **no new warnings**
- [ ] Updated related documentation if public API changed
- [ ] Ran full suite again — **all tests still pass**
- [ ] Final commit made

---

## Coverage Gate

- [ ] Ran coverage report: `python3 -m coverage run -m pytest && python3 -m coverage report --include="src/*"`
- [ ] Changed module coverage ≥ **85%**
- [ ] Overall coverage did not regress

**Coverage for changed module:**

```
Name                         Stmts   Miss  Cover
# PASTE: coverage report line for your module
```

---

## Final Checklist

- [ ] All tests pass (`pytest --tb=short -q` shows 0 failures)
- [ ] Coverage ≥ 85% for changed module
- [ ] No new linting warnings
- [ ] HANDBACK includes `tdd_compliance` section
- [ ] No test was commented out or deleted to make suite green

---

## HANDBACK tdd_compliance Block

Copy into your HANDBACK:

```yaml
tdd_compliance:
  red_phase: complete          # tests written before code, confirmed failing
  green_phase: complete        # all tests pass, no regressions
  refactor_phase: complete     # linting clean, docs updated
  tests_added: N               # number of new test cases
  coverage_module: "XX%"       # coverage for changed module
  coverage_delta: "+X%"        # change from baseline
  failures_resolved: []        # list any pre-existing failures you fixed
```

---

## Quick Reference — Test Failure Triage

| Symptom | Likely Cause | Action |
|---|---|---|
| Test passes before implementation | Testing wrong thing or duplicate coverage | Rewrite to target actual missing behaviour |
| Test fails after refactor | Implementation detail leaked into test | Fix test to test behaviour, not internals |
| Coverage below 85% | Edge/error cases not tested | Add tests for error paths and boundaries |
| Old test now fails | Regression introduced | Fix the code, not the test |
| Import error in test | Wrong mock path or missing `__init__.py` | Update import path, check `conftest.py` |

---

## Commands Reference

```bash
# Run all tests
python3 -m pytest --tb=short -q

# Run single test file
python3 -m pytest tests/test_<module>.py -v

# Run single test
python3 -m pytest tests/test_<module>.py::TestClass::test_method -v

# Coverage for src modules
python3 -m coverage run -m pytest
python3 -m coverage report --include="src/*"

# Lint
flake8 src/ tests/ --max-line-length=120

# Confirm failing tests (RED phase verification)
python3 -m pytest tests/test_<module>.py -v 2>&1 | grep -E "PASSED|FAILED"
```
