# TDD Roadmap — Coverage Improvement Plan

**Date:** 2026-05-09  
**Owner:** Lead Engineer  
**Goal:** Raise overall coverage from 73% → 85%, eliminate all 15 test failures, and establish TDD as the default working pattern

---

## Priority Tiers

| Tier | Criteria | Timeline |
|---|---|---|
| P0 — Immediate | Currently failing tests (broken CI) | Before next merge |
| P1 — Critical | Core modules below 60% coverage | Sprint 1 |
| P2 — Important | Modules 60–84%, no dedicated test file | Sprint 2 |
| P3 — Standard | Ongoing TDD compliance for all new work | Continuous |

---

## P0 — Fix Failing Tests (15 failures blocking CI)

These must be resolved before any new work lands. They represent broken contracts.

### P0.1 — Decision Engine Regression (6 failures)
**File:** `tests/test_decision_engine.py`  
**Issue:** Decision thresholds/scoring changed in refactor; tests reflect the old contract.  
**Action Required:**

1. Determine which is correct: the tests or the implementation.
   - If the old thresholds were correct → revert decision_engine.py changes
   - If new thresholds are correct → update tests to match and document the contract change
2. Fix boundary condition tests for scores 80 and 85.
3. Verify SecurityCriterion scoring logic is correct.
4. No test should be deleted — only corrected.

**Assignee:** Engineer (Senior or QE)  
**Effort:** S (2–4 hours)

---

### P0.2 — Entrypoint Script Deleted (1 failure)
**File:** `tests/test_automation_integration.py::TestEntrypointScript::test_entrypoint_script_exists`  
**Issue:** `bin/run-automation-controller.sh` was deleted in cleanup commit `3c94429`.  
**Action Required:** Choose one:
- Option A: Restore `bin/run-automation-controller.sh` (preferred if it's still needed)
- Option B: Delete the test and update documentation to remove the entrypoint reference
- Option C: Update test to point to new entrypoint location if it was moved, not deleted

**Assignee:** Engineer  
**Effort:** XS (< 1 hour)

---

### P0.3 — Automation Controller Interface (4 failures)
**File:** `tests/test_automation_integration.py` (E2E tests)  
**Issue:** `AutomationController` and `QueueManager` API changed during restructure.  
**Action Required:**

1. Compare the test expectations against current `automation.py` and `orchestrator.py` interfaces.
2. Update tests to reflect current interface — or restore interface to match original contract.
3. Ensure `test_full_automation_cycle` exercises a real end-to-end path.

**Assignee:** Engineer  
**Effort:** M (4–8 hours)

---

### P0.4 — Orchestrator run_poll_cycle (3 failures)
**File:** `tests/test_invoke_agent.py`  
**Issue:** `run_poll_cycle` method was removed or renamed from `OrchestratorAgent`.  
**Action Required:**

1. Check `orchestrator.py` for current polling method name.
2. Update test to reference correct method.
3. Verify the polling behaviour is still tested.

**Assignee:** Engineer  
**Effort:** XS (< 1 hour)

---

### P0.5 — Pre-commit Hook Missing (1 failure + hardcoded path bug)
**File:** `tests/test_protocol_validation.py::TestIntegration::test_pre_commit_hook_exists`  
**Issue:** Two problems:
1. The pre-commit hook was never implemented.
2. Test has hardcoded path `/home/user/agentic-engineers/` which is wrong on this machine.

**Action Required:**
1. Fix the hardcoded path to use a dynamic project root (use `pathlib` + `git rev-parse --show-toplevel`).
2. Implement `.git/hooks/pre-commit` (see TDD-SKILL.md enforcement section) OR skip the test with a documented reason if hook installation is out of scope.

**Assignee:** Engineer  
**Effort:** S (2–4 hours)

---

## P1 — Critical Coverage (Sprint 1)

### P1.1 — orchestrator.py: 53% → 85%
**Gap:** 248 uncovered statements out of 525 total.  
**This is the core of the system.** Low coverage here means the most critical code paths are unverified.

**Create:** `tests/test_orchestrator.py`  
**Test areas needed:**
- Task state transition logic (incoming → processing → done → archived)
- `run_poll_cycle` / polling loop (whatever the current method is named)
- Error handling when queue is empty
- Error handling when delegate validation fails
- Concurrent task handling
- QueueManager integration

**Approach:** TDD — write tests first against the documented interface, then fix any gaps in implementation.  
**Effort:** L (1–2 days)  
**Assignee:** Senior Engineer

---

### P1.2 — model_resolver.py: 55% → 85%
**Gap:** 91 uncovered statements out of 204.  
**This is the model routing brain.** Failures here silently route tasks to wrong models.

**Existing:** `tests/test_model_resolver.py` (partial coverage)  
**Test areas needed:**
- All AGENTS.md role mappings resolve correctly from new path (`docs/AGENTS.md`)
- Fallback behaviour when a role is not in models.yaml
- `models.yaml` parsing with missing/malformed entries
- Model override logic
- Cost-tier selection

**Effort:** M (4–8 hours)  
**Assignee:** Engineer

---

### P1.3 — implementations.py: 39% → 85%
**Gap:** 70 uncovered statements out of 115.

**Create:** `tests/test_implementations.py`  
**Test areas needed:**
- Each implementation class's execute/invoke path
- Error handling for each implementation type
- Return value contracts

**Effort:** M (4–8 hours)  
**Assignee:** Engineer

---

### P1.4 — lead_review_cli.py: 26% → 85%
**Gap:** 66 uncovered statements out of 89.  

**Create:** `tests/test_lead_review_cli.py`  
**Test areas needed:**
- CLI argument parsing (valid and invalid inputs)
- Review output format
- Exit codes for pass/fail/error
- Integration with quality validator

**Effort:** M (4–8 hours)  
**Assignee:** Engineer

---

## P2 — Important Coverage (Sprint 2)

### P2.1 — artifact_manager.py: 0% → 85%
No test file exists. Source: `src/orchestration/agents/artifact_manager.py`  
**Create:** `tests/test_artifact_manager.py`  
**Effort:** M

### P2.2 — metrics_writer.py: 81% → 90%
Indirect coverage only. Need direct tests for error paths and metric format validation.  
**Create:** `tests/test_metrics_writer.py`  
**Effort:** S

### P2.3 — spec_validator.py: 0% → 85%
No test file exists.  
**Create:** `tests/test_spec_validator.py`  
**Effort:** M

### P2.4 — workflow.py: 0% → 85%
No test file exists.  
**Create:** `tests/test_workflow.py`  
**Effort:** M

### P2.5 — delegate_validator.py: Direct tests
Currently exercised only through quality_validator integration. Add dedicated tests.  
**Create:** `tests/test_delegate_validator.py`  
**Effort:** S

### P2.6 — gray_zone_reviewer.py: 81% → 90%
Add direct unit tests for reviewer decision logic.  
**Update:** `tests/test_protocol_gray_zone.py` or add `tests/test_gray_zone_reviewer.py`  
**Effort:** S

---

## P3 — Continuous TDD Compliance (Ongoing)

### P3.1 — Pre-commit Hook Installation
Once the hook is implemented (P0.5), document the setup in README.md so all contributors install it.

### P3.2 — CI Coverage Gate
Add to CI/CD pipeline:
```yaml
- name: Coverage Gate
  run: |
    python3 -m coverage run -m pytest
    python3 -m coverage report --include="src/*" --fail-under=85
```
This makes coverage regression a build failure, not a code review concern.

### P3.3 — PR Template with TDD Checklist
Add `.github/PULL_REQUEST_TEMPLATE.md` with the TDD checklist embedded so every PR author is prompted to complete it.

### P3.4 — Lead Engineer Review Gate
All PRs touching `src/orchestration/` require Lead Engineer sign-off verifying:
- TDD checklist completed
- Coverage did not regress
- No new test failures

### P3.5 — Quarterly Coverage Audit
Review coverage report quarterly. Flag any module that has regressed below 85% for immediate remediation.

---

## Coverage Progress Tracker

| Milestone | Target | Measure |
|---|---|---|
| P0 complete | 0 failing tests | `pytest --tb=no -q \| tail -1` |
| P1 complete | ≥ 85% on orchestrator, model_resolver, implementations, lead_review_cli | `coverage report` |
| P2 complete | All modules have dedicated test file | `ls tests/test_*.py` |
| P3 running | CI gate enforcing ≥ 85% overall | CI pipeline |
| Long-term goal | ≥ 85% overall | Coverage badge in README |
