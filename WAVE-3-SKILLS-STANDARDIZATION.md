# Wave 3: Skills Standardization & Test Coverage

**Status:** PLAN/TODO (Ready for execution, not started)  
**Date Created:** 2026-06-15  
**Baseline:** Wave 2 completion (all harnesses 100% delegation success)

---

## Overview

Wave 3 focuses on **precision standardization, test coverage completion, and harness re-render validation** to achieve production-ready skills quality. All consolidations from Wave 2 have been completed successfully; Wave 3 addresses remaining quality gaps and finalizes defect fixes.

**Execution Model:** 5 parallel engineer streams + validation (26-33 hours total)

---

## Current State (Post-Wave 2)

### Skill Inventory Summary (23 total skills)

**CORE skills (8):** queue-management, protocol-validator, spec-management, spec-validator, orchestrator, cost-aggregation, model-selection, model-engineer

**UTILITY skills (12):** queue-query, queue-todo-sync, harness-integration-tracker, session-analyzer, file-sync, doc-quality-monitor, local-model-runtime, workflow-review, testing, agent-creator, consistency-checker, usage-tracking

**EXPERIMENTAL skills (1):** ab-testing

**FIXED skills (1):** cost-budgeting (SKILL.md added in Wave 2)

**INFRASTRUCTURE skills (1):** metrics-etl

**NEW skills (Wave 1):** queue-monitor (curses TUI dashboard)

### Test Coverage Baseline (Wave 2)

| Metric | Baseline |
|--------|----------|
| Full Test Suite | 5,189 |
| OpenCode Harness | 94 |
| Claude Code Harness | 103 |
| Copilot CLI Harness | 81 |
| Regression Gate | ENFORCED |

---

## Wave 3 Phases

### Phase W3-A: Deletions ✅ COMPLETE
- Deleted `src/skills/monitoring/` (doc-only)
- Deleted `src/skills/spec-extract/` (unintegrated script)
- Archived deprecated skills to `docs/archive/deprecated-skills/`

### Phase W3-B: Defect Fixes (READY TO EXECUTE)

**Task:** cost-budgeting SKILL.md validation + test coverage audit

- Verify SKILL.md present in all 4 harnesses (dist/*/skills/cost-budgeting/)
- Coverage audit: `pytest src/skills/cost-budgeting/tests/ --cov --cov-report=html`
- Target: ≥85% line coverage on cost_budgeter.py + models.py
- Expected: No new tests required if existing 83 tests cover ≥85%

**Risk:** LOW (validation-only)

### Phase W3-C: Test Coverage Standardization (READY TO EXECUTE)

Six skills require test coverage improvements:

| Skill | Current Tests | Target | Effort | Notes |
|-------|---|---|---|---|
| **spec-validator** | 3 | ~80+ | 8-12 hrs | Core validation skill, 1,758 LOC |
| **metrics-etl** | 0 | ~15 | 2-3 hrs | Infrastructure ETL, smoke tests |
| **doc-quality-monitor** | 0-25* | ~25 | 3-4 hrs | Link validator, audit if exists |
| **testing** | 0 | ~20 | 3-4 hrs | Test utility, fixture-sync logic |
| **ab-testing** | 0 | ~15 | 2-3 hrs | A/B testing framework, stats tests |
| **TOTAL** | - | **+190** | **~26 hrs** | Parallel execution (5 streams) |

*doc-quality-monitor may have existing tests in tests/audit/ — audit first

**Execution Approach:**
- Use TDD: RED phase (write failing tests), GREEN phase (fix code)
- Parallel streams: C2/C3/C4/C5 can run simultaneously
- C1 (spec-validator) runs sequentially (largest addition)

### Phase W3-D: Harness Re-Render Validation (READY TO EXECUTE)

After all Wave 3 fixes complete:

```bash
# 1. Full render
make render-all

# 2. Verify regression gate passes
python scripts/check_test_regression.py

# 3. Validate rendered skill counts
ls dist/claude/skills/ | wc -l     # ≥23
ls dist/copilot/skills/ | wc -l    # ≥23
ls dist/opencode/skills/ | wc -l   # ≥23

# 4. Update regression gate baseline
# OLD: 5,189 (Wave 2)
# NEW: 5,379 (Wave 3, +190 tests)
# Gate: python scripts/check_test_regression.py --update-baseline 5379
```

---

## Test Impact Analysis

| Phase | Action | Test Δ | Cumulative |
|-------|--------|--------|-----------|
| Wave 2 Baseline | 23 skills consolidated | +264 | 5,189 |
| W3-B: cost-budgeting | Coverage audit only | 0 | 5,189 |
| W3-C1: spec-validator | Add ~80 tests | +80 | 5,269 |
| W3-C2: metrics-etl | Add ~15 smoke tests | +15 | 5,284 |
| W3-C3: doc-quality-monitor | Add ~25 tests | +25 | 5,309 |
| W3-C4: testing | Add ~20 tests | +20 | 5,329 |
| W3-C5: ab-testing | Add ~15 tests | +15 | 5,344 |
| **Post-Wave 3** | All tests passing | **+190** | **5,379** |

**New Regression Gate Baseline:** ≥5,379 (update `scripts/check_test_regression.py` after merge)

---

## Dependencies & Merge Order

**Sequence 1 — Independent (parallel):**
- [ ] W3-C2: metrics-etl
- [ ] W3-C3: doc-quality-monitor
- [ ] W3-C4: testing

**Sequence 2 — Sequential:**
- [ ] W3-C1: spec-validator (largest, benefits from focus)
- [ ] W3-C5: ab-testing

**Sequence 3 — Validation & Release:**
- [ ] W3-B: cost-budgeting coverage validation
- [ ] Harness re-render + regression gate validation
- [ ] Update baseline in scripts/check_test_regression.py
- [ ] Tag v0.44.0

---

## Wave 3 Execution Checklist

### Pre-Execution
- [ ] Branch: `feature/wave3-skills-standardization` created
- [ ] Baseline recorded: `pytest --collect-only -q | tail -1`
- [ ] Regression gate policy understood

### Phase W3-B
- [ ] cost-budgeting SKILL.md verified in all 4 harnesses
- [ ] Coverage audit: `pytest src/skills/cost-budgeting/tests/ --cov`
- [ ] All tests pass

### Phase W3-C1
- [ ] spec-validator coverage gap analyzed
- [ ] TDD RED phase: write failing tests for ≥85% coverage
- [ ] Tests green: `pytest src/skills/spec-validator/tests/ -v`
- [ ] Coverage report ≥85%

### Phase W3-C2/C3/C4/C5
- [ ] Parallel execution of remaining skill tests
- [ ] All tests pass
- [ ] Coverage targets met

### Phase W3-D
- [ ] Full suite: `pytest tests/ -x` (no failures)
- [ ] Regression gate: `python scripts/check_test_regression.py`
- [ ] Re-render: `make render-all`
- [ ] Harness validation: skill counts ≥23 in all 4 harnesses
- [ ] Update baseline: `scripts/check_test_regression.py` (5,189 → 5,379)

### Post-Execution
- [ ] All tests passing locally
- [ ] CI green on feature/wave3-skills-standardization
- [ ] Code review approved
- [ ] Merge to main
- [ ] Tag v0.44.0

---

## Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Test coverage explosion (>100 tests) | Low | Low | If needed, split across multiple PRs |
| Harness render breaks for one provider | Low | High | Render dry-run in CI; validate all 4 |
| Regression gate baseline calculation wrong | Low | Medium | Manual verify: `pytest --collect-only -q \| tail -1` |
| Defect in cost-budgeting found during audit | Low | Medium | Already fixed in Wave 2; audit validates |
| Test count delta doesn't match estimates | Medium | Low | Delta estimates are rough; actual verified pre-merge |

**Overall Risk: LOW** (all work is additive, git history preserves rollback)

---

## Success Criteria

- ✅ AC1: All consolidation targets identified (Wave 2: complete; W3 gaps identified)
- ✅ AC2: Merge strategy defined (3-sequence plan with per-skill gates)
- ✅ AC3: Test impact analysis complete (+190 tests, 5,189 → 5,379)
- ✅ AC4: Harness re-render impacts documented (4-harness validation checklist)
- ✅ AC5: Wave 3 execution checklist ready (26-33 hours estimate)

---

## How to Execute Wave 3

When ready to execute:

1. **Create branch:**
   ```bash
   git checkout -b feature/wave3-skills-standardization
   ```

2. **Queue Wave 3 DELEGATEs** via Orchestrator:
   - W3-B: cost-budgeting audit (quality-engineer)
   - W3-C1: spec-validator tests (engineer, 8-12 hrs)
   - W3-C2/C3/C4/C5: parallel skills tests (4 engineers, 2-4 hrs each)
   - W3-D: harness validation + release (quality-engineer)

3. **Merge when complete:**
   ```bash
   git merge --no-ff feature/wave3-skills-standardization
   git tag -a v0.44.0 -m "v0.44.0: Wave 3 skills standardization"
   ```

---

## References

- **Wave 2 Completion Report:** `~/.agentic-engineers/claude/wave2-2026-06-15/WAVE_2_COMPLETION_REPORT.md`
- **Consolidation Plan:** `~/.agentic-engineers/claude/wave2-2026-06-15/queue/done/DELEGATE-2026-06-15-014-skills-consolidation-plan-HANDBACK-lead-engineer.yaml`
- **Regression Gate Policy:** `docs/REGRESSION-GATE-POLICY.md`
- **SPEC Compliance:** `docs/SPEC.md`

---

**Status:** READY TO EXECUTE (plan complete, no blockers)  
**Decision Point:** User to decide when to queue Wave 3 execution
