# TDD Skill: Red-Green-Refactor Pattern

**Version:** 1.0  
**Owner:** Lead Engineer  
**Status:** Canonical — all engineers MUST follow  
**Applies to:** All code changes (features, bug fixes, refactoring, infrastructure)  
**Does NOT apply to:** Pure documentation edits, comment-only changes, configuration value updates with no logic

---

## Purpose

Ensure every code change in this repository is validated by tests *before* it is written. Tests are the specification. Code is the proof. No code ships without passing tests that existed before it.

---

## Workflow: Red → Green → Refactor

### Phase 1 — RED: Write Failing Tests First

**Goal:** Capture the desired behaviour in executable test form. Confirm the tests actually fail.

**Steps:**

1. Understand the requirement. Write it as one-sentence acceptance criteria.
2. Create or update the test file (`tests/test_<module>.py`) for the module under change.
3. Write tests covering:
   - **Happy path** — expected inputs produce expected outputs.
   - **Edge cases** — boundary values, empty inputs, max values.
   - **Error cases** — invalid inputs, dependency failures, missing config.
   - **Regression guards** — any bug being fixed must have a test that reproduces it first.
4. Run the tests. **Verify they FAIL.** A test that passes before implementation is either testing the wrong thing or already covered elsewhere.
5. Commit the test skeleton with message prefix `test(wip):`.

```bash
# Confirm RED state before proceeding
python3 -m pytest tests/test_<module>.py -v
# Expected: FAILED for new tests
```

**Exit criteria for RED:**
- [ ] New tests exist in `tests/test_<module>.py`
- [ ] All new tests fail when run against the current codebase
- [ ] Failure messages confirm the tests are exercising the right behaviour
- [ ] Tests are committed (WIP commit)

---

### Phase 2 — GREEN: Write Minimum Code to Pass

**Goal:** Make tests pass with the simplest correct implementation. No premature optimisation.

**Steps:**

1. Implement only what is needed to make the failing tests pass.
2. Do not refactor during this phase — ugly code that passes is correct here.
3. Run the full test suite (not just new tests) after every significant change.
4. Once all tests pass — **stop adding code**.
5. Commit with message prefix `feat:`, `fix:`, or `refactor:` as appropriate.

```bash
# Confirm GREEN state
python3 -m pytest --tb=short -q
# Expected: all new tests PASS, no regressions introduced
```

**Exit criteria for GREEN:**
- [ ] All new tests pass
- [ ] No previously-passing tests now fail (no regressions)
- [ ] Implementation committed

---

### Phase 3 — REFACTOR: Clean Without Breaking

**Goal:** Improve code quality while tests remain green.

**Steps:**

1. Remove duplication, rename for clarity, extract helpers.
2. Run tests after *each* refactoring step — do not batch changes without testing.
3. Update inline comments and docstrings to reflect final implementation.
4. Check for linting issues: `make lint` or equivalent.
5. Update related documentation if public behaviour changed.
6. Final commit with message prefix `refactor:` or `chore:`.

```bash
# Verify REFACTOR did not break anything
python3 -m pytest --tb=short -q
make lint   # or: flake8 src/ tests/
```

**Exit criteria for REFACTOR:**
- [ ] All tests still pass
- [ ] No new linting warnings
- [ ] Code is readable by a developer unfamiliar with this change
- [ ] Documentation updated if behaviour changed
- [ ] Coverage ≥ 85% for the changed module

---

## Applicability Rules

| Change Type | TDD Required? | Notes |
|---|---|---|
| New feature | **YES** | Tests before any implementation |
| Bug fix | **YES** | Write a failing test that reproduces the bug first |
| Refactoring | **YES** | Tests must exist before changing any logic |
| New skill/tool added | **YES** | Tests verify skill behaviour and error cases |
| Infrastructure move (files, imports) | **YES** | Tests verify new paths resolve correctly |
| Documentation only | No | No code paths affected |
| Config value change (no logic) | No | Covered by integration tests |
| Dependency version bump | Conditional | If API changes, write tests against new API first |

---

## Coverage Requirements

| Scope | Minimum | Target |
|---|---|---|
| Changed module (net new lines) | 85% | 95% |
| Overall repository | 73% (current) | 85% |
| Critical paths (orchestrator, routing, quality gates) | 90% | 95% |

Run coverage to check before opening a PR:

```bash
python3 -m coverage run -m pytest
python3 -m coverage report --include="src/*" --fail-under=85
```

---

## Test File Conventions

```
tests/
  test_<module_name>.py        # Unit tests — fast, fully mocked
  test_<module_name>_integration.py   # Integration tests — real dependencies
```

**Test class naming:**

```python
class TestModuleNameHappyPath:     # Expected behaviour
class TestModuleNameEdgeCases:     # Boundary / unusual inputs  
class TestModuleNameErrors:        # Error handling
class TestModuleNameIntegration:   # Cross-module behaviour
```

**Individual test naming:**

```python
def test_<action>_<scenario>_<expected_outcome>(self):
    # e.g. test_route_task_with_unknown_role_returns_error
```

---

## Enforcement Points

| Gate | Tool | Behaviour |
|---|---|---|
| Pre-commit | `.git/hooks/pre-commit` | Blocks commit if tests for changed source files are missing |
| CI/CD | GitHub Actions | Full test suite must pass; coverage report published |
| Code review | Lead Engineer checklist | TDD checklist verified before approval |
| Merge gate | Branch protection | All checks must be green |

---

## Common TDD Anti-Patterns to Avoid

| Anti-Pattern | Why It Fails |
|---|---|
| Writing tests after the code | Tests are biased toward the implementation, not the requirement |
| Testing implementation details (private methods, internal state) | Couples tests to code structure — refactoring breaks tests unnecessarily |
| One test for the happy path only | Edge cases and errors are where bugs live |
| Commenting out failing tests | Hides regressions. Delete or fix — never comment out |
| Testing with `assert True` placeholders | False confidence; test never actually validates behaviour |
| Mocking everything including the unit under test | Tests pass regardless of implementation correctness |

---

## Skill Invocation

Any engineer receiving a DELEGATE task that involves code changes MUST open this skill at the start of their session and complete each phase in order. Do not proceed to implementation without completing the RED phase checklist.

**Reference this skill in HANDBACK:**

```yaml
tdd_compliance:
  red_phase: complete        # tests written and confirmed failing
  green_phase: complete      # all tests passing
  refactor_phase: complete   # linting clean, coverage ≥ 85%
  coverage_delta: "+12%"     # coverage change for changed modules
```
