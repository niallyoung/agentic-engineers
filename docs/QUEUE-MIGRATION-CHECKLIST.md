# Queue Migration Implementation Checklist

**Status**: Ready for Team Review  
**Last Updated**: 2025-05-24  
**Owner**: Principal Engineer  

---

## Pre-Implementation Review (Week 0)

### Architecture Review
- [ ] **Leads review** ARCHITECTURE-QUEUE-UNIFIED.md
  - Sign-off on design approach
  - Confirm gradual migration strategy acceptable
  - Approve 4-phase timeline

- [ ] **Engineers review** ARCHITECTURE-QUEUE-UNIFIED-IMPLEMENTATION.md
  - Understand Phase 1 task breakdown
  - Confirm effort estimates realistic
  - Identify any blockers

- [ ] **QA review** ARCHITECTURE-QUEUE-VISUAL.md
  - Understand test strategy
  - Confirm fixtures migration plan
  - Identify test scenarios

### Project Setup
- [ ] Create sprint planning card: "Queue Architecture Redesign (4-week project)"
- [ ] Allocate engineering capacity: ~25 hours (can be distributed)
- [ ] Schedule weekly status sync (Mondays 10am)
- [ ] Create Slack channel: #queue-migration
- [ ] Share documents with team

### Risk Mitigation Setup
- [ ] Verify queue-isolation tests passing locally
  ```bash
  python3 -m pytest src/skills/_meta/queue-isolation/tests/ -v
  ```
- [ ] Create backup scripts for queue data
  ```bash
  mkdir -p scripts/queue-backup/
  # (scripts in docs/ARCHITECTURE-QUEUE-UNIFIED.md - Appendix)
  ```
- [ ] Prepare rollback procedures
- [ ] Document communication plan (users, stakeholders)

---

## Phase 1: Foundation & Orchestrator (Week 1-2)

### Task 1.1: Verify queue-isolation Skill

**Owner**: [Engineer]  
**Effort**: 1 hour  
**Status**: ⏳ Not Started

- [ ] Run queue-isolation tests
  ```bash
  cd /Users/niall/git/agentic-engineers
  python3 -m pytest src/skills/_meta/queue-isolation/tests/ -v
  ```
- [ ] Verify coverage: 100%
  ```bash
  python3 -m pytest src/skills/_meta/queue-isolation/tests/ \
    --cov=src/skills/_meta/queue-isolation \
    --cov-report=term-missing
  ```
- [ ] Document test results
- [ ] **Deliverable**: Screenshot/log showing ✅ all 28 tests passing

**Sign-off**: [ ] Engineer | [ ] QA

---

### Task 1.2: Update Orchestrator QueueManager

**Owner**: [Engineer]  
**Effort**: 4 hours  
**Status**: ⏳ Not Started  
**File**: `src/orchestration/agents/orchestrator.py`

**Changes Required**:

1. [ ] Add queue-isolation import at module level
   ```python
   def _try_import_queue_isolation():
       """Attempt to import queue_isolation; return module or None on failure."""
       try:
           from src.skills._meta.queue_isolation.scripts import queue_isolation as qi
           return qi
       except ImportError:
           return None

   _QUEUE_ISOLATION = _try_import_queue_isolation()
   ```

2. [ ] Update `QueueManager.__init__()` to implement dual-path logic
   - Try isolation first if available
   - Log which path is used (`_using_isolation` flag)
   - Fallback to legacy paths gracefully
   - Initialize same subdirectories for both paths

3. [ ] Add logging statements
   - Log path selection (isolation vs legacy)
   - Log session ID and harness
   - Log any fallback events

4. [ ] Run existing tests
   ```bash
   python3 -m pytest tests/test_orchestration/ -v -k queue
   ```

5. [ ] **Deliverable**: 
   - [ ] Code change reviewed
   - [ ] All existing tests passing (no regressions)
   - [ ] New test: isolation path preferred when available
   - [ ] New test: fallback when isolation unavailable

**Code Review Checklist**:
- [ ] Fallback logic clear and tested
- [ ] Logging adequate for debugging
- [ ] No breaking changes to API
- [ ] Comments explain dual-path strategy
- [ ] Backward compatibility preserved

**Sign-off**: [ ] Engineer | [ ] Lead Engineer | [ ] QA

---

### Task 1.3: Verify ExtendedQueueManager

**Owner**: [Engineer]  
**Effort**: 1 hour  
**Status**: ⏳ Not Started  
**File**: `src/orchestration/queue_manager.py`

- [ ] Review `ExtendedQueueManager.__init__()` inherits from updated `QueueManager`
- [ ] Test `move_to_failed()` with isolation path
- [ ] Verify `failed_dir` created correctly in both paths
- [ ] Run tests:
  ```bash
  python3 -m pytest tests/test_orchestration/test_extended_queue_manager.py -v
  ```
- [ ] **Deliverable**: All tests passing, no code changes needed

**Sign-off**: [ ] Engineer | [ ] QA

---

### Task 1.4: Run Full Orchestration Test Suite

**Owner**: [Quality Engineer]  
**Effort**: 2 hours  
**Status**: ⏳ Not Started

- [ ] Run full orchestration tests
  ```bash
  python3 -m pytest tests/test_orchestration/ -v
  ```
- [ ] Verify 100% passing
- [ ] No regressions from Phase 1 changes
- [ ] Collect baseline metrics (test time, coverage)
- [ ] **Deliverable**: Test report showing all passing

**Sign-off**: [ ] QA Lead | [ ] Lead Engineer

---

### Phase 1 Completion

**Before moving to Phase 2:**
- [ ] All 4 tasks complete and signed off
- [ ] Orchestrator using dual-path logic (verified)
- [ ] All tests passing (100%)
- [ ] Backward compatibility confirmed
- [ ] **Status**: ✅ READY FOR PHASE 2

---

## Phase 2: Skills & Documentation (Week 2)

### Task 2.1: Verify Queue Operations Skill

**Owner**: [Engineer]  
**Effort**: 1 hour  
**Status**: ⏳ Not Started

- [ ] Check `_DEFAULT_QUEUE_PATH` in `src/skills/queue-management/scripts/queue_ops.py`
  ```bash
  grep "_DEFAULT_QUEUE_PATH" src/skills/queue-management/scripts/queue_ops.py
  ```
- [ ] Verify it points to new path: `~/.agentic-engineers/artifacts`
- [ ] Run skill tests:
  ```bash
  python3 -m pytest src/skills/queue-management/tests/ -v
  ```
- [ ] **Deliverable**: Verification that no code changes needed (already correct!)

**Sign-off**: [ ] Engineer | [ ] QA

---

### Task 2.2: Verify Queue Management CLI

**Owner**: [Engineer]  
**Effort**: 1 hour  
**Status**: ⏳ Not Started

- [ ] Review `queue_manager.py` `_get_default_queue_dir()` method
- [ ] Verify it uses `_try_import_queue_isolation()`
- [ ] Verify fallback to legacy path implemented
- [ ] Run tests:
  ```bash
  python3 -m pytest src/skills/queue-management/tests/test_queue_*.py -v
  ```
- [ ] **Deliverable**: Verification that no code changes needed (already prepared!)

**Sign-off**: [ ] Engineer | [ ] QA

---

### Task 2.3: Update Documentation

**Owner**: [Senior Engineer]  
**Effort**: 2 hours  
**Status**: ⏳ Not Started

#### docs/QUEUE-PROTOCOL.md
- [ ] Add "PATH MIGRATION" notice at top
  ```markdown
  > **⚠️ PATH MIGRATION**: Session artifacts are transitioning...
  > Both paths work during migration (Phase 1-4).
  ```
- [ ] Update all `~/.copilot/queue/` references
  ```
  OLD: ~/.copilot/queue/{session-id}/
  NEW: ~/.agentic-engineers/artifacts/{session-id}/{harness}/queue/
  (legacy: ~/.copilot/queue/{session-id}/)
  ```

#### artifacts/queue/SCHEMA.md
- [ ] Update state machine references (same path change as above)
- [ ] Add deprecation notice for old paths
- [ ] Update all file path examples

#### src/AGENTS.md
- [ ] Update queue-first protocol references
- [ ] Update path examples
- [ ] Add note about multi-harness isolation

#### src/TODO.md.template
- [ ] Update queue path examples

#### CHANGELOG.md
- [ ] Add section under `versioned entry (## [vX.Y.Z] - YYYY-MM-DD)`:
  ```markdown
  ### Added
  - Queue path unification (Phase 1 of migration)
  
  ### Changed
  - Orchestrator now prefers ~/.agentic-engineers/ paths
  
  ### Deprecated
  - ~/.copilot/queue/ (will be removed week 4)
  ```

**Deliverables**:
- [ ] All 5 files updated
- [ ] Paths consistent across docs
- [ ] Deprecation timeline clear
- [ ] Migration notices visible

**Review Checklist**:
- [ ] No broken links in docs
- [ ] Path examples accurate and consistent
- [ ] Timeline clear (phases, weeks)
- [ ] User impact explained

**Sign-off**: [ ] Documentation Lead | [ ] Lead Engineer

---

### Task 2.4: Update Skill Documentation

**Owner**: [Engineer]  
**Effort**: 1 hour  
**Status**: ⏳ Not Started

- [ ] Update `src/skills/queue-management/SKILL.md`
  - Add "Path Architecture" section
  - Document Phase 1 (dual-path) and Phase 2 (new only)
  
- [ ] Review `src/skills/_meta/queue-isolation/SKILL.md`
  - Already documents target paths
  - No changes needed

**Deliverable**: Updated queue-management SKILL.md

**Sign-off**: [ ] Engineer | [ ] Documentation Lead

---

### Phase 2 Completion

**Before moving to Phase 3:**
- [ ] All 4 tasks complete
- [ ] Documentation updated across all files
- [ ] Deprecation timeline communicated
- [ ] Skills verified (no code changes needed)
- [ ] **Status**: ✅ READY FOR PHASE 3

---

## Phase 3: Test Suite Migration (Week 3)

### Task 3.1: Audit All Queue Tests

**Owner**: [Quality Engineer]  
**Effort**: 2 hours  
**Status**: ⏳ Not Started

- [ ] Find all queue-related tests
  ```bash
  find tests/ -name "*queue*.py" -o -name "*orchestration*.py" | sort
  ```
- [ ] Document findings in `QUEUE-MIGRATION-CHECKLIST.md`
- [ ] Identify which tests need fixture updates
- [ ] Identify which tests can run unchanged
- [ ] **Deliverable**: Audit report with test inventory

**Sign-off**: [ ] QA Lead

---

### Task 3.2: Create Test Helpers

**Owner**: [Engineer]  
**Effort**: 2 hours  
**Status**: ⏳ Not Started  
**File**: `tests/helpers/queue_test_helpers.py` (NEW)

- [ ] Create helpers file with:
  - `setup_isolated_queue()` function
  - `isolated_queue_env` pytest fixture
  - `legacy_queue_env` pytest fixture
  - Documentation

- [ ] Test helpers
  ```bash
  python3 -m pytest tests/helpers/ -v
  ```

- [ ] **Deliverable**: Helper functions working and documented

**Sign-off**: [ ] Engineer | [ ] QA

---

### Task 3.3: Migrate Test Fixtures

**Owner**: [Quality Engineer]  
**Effort**: 4 hours  
**Status**: ⏳ Not Started

**Priority files** (in order):
1. [ ] `tests/conftest.py` — Add helper imports and fixtures
2. [ ] `tests/test_orchestration/test_queue_manager.py`
3. [ ] `tests/test_orchestration/test_queue_operations.py`
4. [ ] `tests/test_orchestration/test_delegate_validator.py`
5. [ ] `tests/test_skills/test_queue_management.py`

**Pattern for each file**:
- [ ] Replace hardcoded queue paths with fixtures
- [ ] Use `isolated_queue_env` for new path tests
- [ ] Use `legacy_queue_env` for backward compat tests
- [ ] Update fixture setup/teardown

**Migration Steps** (for each file):
1. Review current fixtures
2. Replace `tmp_path / ".copilot" / "queue"` with `isolated_queue_env`
3. Add new test for legacy path fallback
4. Verify all tests pass

**Deliverable**: 
- [ ] All test fixtures migrated
- [ ] Tests run successfully
- [ ] Both isolation and legacy paths tested

**Sign-off**: [ ] QA | [ ] Engineer

---

### Task 3.4: Add Multi-Harness Tests

**Owner**: [Quality Engineer]  
**Effort**: 2 hours  
**Status**: ⏳ Not Started  
**File**: `tests/test_orchestration/test_queue_isolation.py` (NEW)

- [ ] Create new test file with:
  - `test_multi_harness_isolation()` — Verify Claude/Copilot don't collide
  - `test_harness_auto_detection()` — Verify env var detection
  - `test_session_id_preservation()` — Verify data persists
  - `test_isolation_initialization()` — Verify metadata.json created

- [ ] Run tests:
  ```bash
  python3 -m pytest tests/test_orchestration/test_queue_isolation.py -v
  ```

- [ ] **Deliverable**: 4+ new tests, all passing

**Sign-off**: [ ] QA Lead

---

### Task 3.5: Full Test Suite Validation

**Owner**: [Quality Engineer]  
**Effort**: 1 hour  
**Status**: ⏳ Not Started

- [ ] Run full test suite with coverage
  ```bash
  python3 -m pytest tests/ -v --cov --cov-report=term-missing
  ```
- [ ] Verify 100% passing
- [ ] Check coverage thresholds
- [ ] Compare performance to Phase 1 baseline
- [ ] **Deliverable**: Test report, coverage metrics

**Success Criteria**:
- [ ] 100% tests passing
- [ ] No regressions from Phase 1
- [ ] Coverage maintained or improved
- [ ] Performance acceptable (no slowdown)

**Sign-off**: [ ] QA Lead | [ ] Lead Engineer

---

### Phase 3 Completion

**Before moving to Phase 4:**
- [ ] All 5 tasks complete
- [ ] Test fixtures migrated
- [ ] Multi-harness isolation tested
- [ ] Full test suite passing (100%)
- [ ] **Status**: ✅ READY FOR PHASE 4

---

## Phase 4: Documentation & Cutover (Week 4)

### Task 4.1: Finalize Architecture Document

**Owner**: [Senior Engineer]  
**Effort**: 1 hour  
**Status**: ⏳ Not Started

- [ ] Review ARCHITECTURE-QUEUE-UNIFIED.md
- [ ] Add "Lessons Learned" section (after implementation)
- [ ] Document any deviations from plan
- [ ] Update metrics/effort estimates if needed
- [ ] **Deliverable**: Final architecture doc

**Sign-off**: [ ] Senior Engineer | [ ] Lead Engineer

---

### Task 4.2: Update CHANGELOG

**Owner**: [Senior Engineer]  
**Effort**: 30 minutes  
**Status**: ⏳ Not Started

- [ ] Add entry under `versioned entry (## [vX.Y.Z] - YYYY-MM-DD)` section
- [ ] Include:
  - Added: New features (isolation, env vars)
  - Changed: Breaking changes (week 5+)
  - Deprecated: Old paths (timeline)
  - Migration: Link to migration guide

**Deliverable**: CHANGELOG.md entry added

**Sign-off**: [ ] Lead Engineer

---

### Task 4.3: Create Migration Guide

**Owner**: [Lead Engineer]  
**Effort**: 2 hours  
**Status**: ⏳ Not Started  
**File**: `docs/MIGRATION-GUIDE-QUEUE-PATHS.md` (NEW)

- [ ] Sections for:
  - End Users (no action needed)
  - Developers (env vars, programmatic access)
  - DevOps (backup strategy, scripts)
  - Troubleshooting (FAQ)

- [ ] Include code examples for:
  - Setting environment variables
  - Accessing queue paths programmatically
  - Forcing specific harness/session
  - Testing custom code

**Deliverable**: Comprehensive migration guide for all audiences

**Sign-off**: [ ] Lead Engineer | [ ] Documentation Lead

---

### Task 4.4: Deploy Cutover Announcement

**Owner**: [Lead Engineer]  
**Effort**: 1 hour  
**Status**: ⏳ Not Started

- [ ] Draft announcement for team
- [ ] Post to:
  - [ ] Slack #engineering channel
  - [ ] Email to stakeholders
  - [ ] Internal wiki/docs
  
- [ ] Include:
  - What changed (high level)
  - Why (problem + solution)
  - What users need to do (nothing!)
  - Timeline (phases, weeks)
  - Link to migration guide
  - Who to contact for questions

**Deliverable**: Team announcement posted

**Sign-off**: [ ] Lead Engineer | [ ] Product Lead

---

### Task 4.5: Metrics Collection & Reporting

**Owner**: [Metrics/Monitoring Engineer]  
**Effort**: 2 hours  
**Status**: ⏳ Not Started

- [ ] Set up metrics collection:
  - Queue path used (isolation vs legacy)
  - Errors during path detection
  - Adoption rate tracking
  
- [ ] Create dashboard showing:
  - % isolation paths used
  - % legacy fallback used
  - Error rate
  - Adoption curve over time

- [ ] Generate report:
  - Phase 1 adoption metrics
  - Error incidents
  - Performance impact
  - User feedback

**Deliverable**: Metrics dashboard + adoption report

**Sign-off**: [ ] Engineering Lead | [ ] Metrics Team

---

### Phase 4 Completion

**Before moving to monitoring:**
- [ ] All 5 tasks complete
- [ ] Documentation finalized
- [ ] Team announcement posted
- [ ] Metrics collection active
- [ ] **Status**: ✅ READY FOR MONITORING (Weeks 5-7)

---

## Weeks 5-7: Monitoring & Cleanup

### Daily Checks (Automated)
- [ ] Error rate for path detection < 1%
- [ ] Queue operations latency unchanged
- [ ] Test suite passing (CI/CD)
- [ ] Fallback usage monitored

### Weekly Reviews
- [ ] Monday: Review metrics dashboard
- [ ] Check adoption curve (target: 90%+ new path)
- [ ] Collect user feedback
- [ ] Address any issues

### Week 7: Final Cleanup

**Before removing legacy code:**
- [ ] [ ] Adoption rate > 95%
- [ ] [ ] Fallback usage < 5%
- [ ] [ ] Zero data loss incidents
- [ ] [ ] User feedback positive

**Cleanup tasks:**
- [ ] Remove legacy path fallback from `orchestrator.py`
- [ ] Remove fallback from `queue_manager.py`
- [ ] Update docs (remove migration notices)
- [ ] Tag release v5.11.0 (BREAKING CHANGE)

**Deliverable**: Clean codebase, zero legacy code

---

## Post-Implementation

### Sign-Off
- [ ] **Principal Engineer**: Architecture complete and implemented
- [ ] **Lead Engineer**: Code reviewed and tested
- [ ] **QA**: All tests passing, quality verified
- [ ] **Product Lead**: User communication complete

### Final Metrics
| Metric | Target | Actual |
|--------|--------|--------|
| Adoption rate (week 4) | >90% | ___ |
| Error rate | <1% | ___ |
| Data loss incidents | 0 | ___ |
| Test pass rate | 100% | ___ |
| Performance impact | None | ___ |

### Retrospective
- [ ] Schedule retro meeting
- [ ] Document what went well
- [ ] Document what could improve
- [ ] Share learnings with team

---

## Rollback Procedures

### If Issues Found (Phase 1-2)

1. [ ] Stop all new queue operations
2. [ ] Revert `orchestrator.py` to before Phase 1
3. [ ] Keep all documentation updates (useful for future)
4. [ ] Investigate root cause (1-2 days)
5. [ ] Fix and restart Phase 1

### If Issues Found (Phase 3-4)

1. [ ] Pause test migration
2. [ ] Keep rolled-back main code
3. [ ] Fix identified issues
4. [ ] Resume migration

### No Data Loss in Either Scenario
(Fallback logic always available until removed in week 7)

---

## Team Sign-Offs

### Phase 1 Sign-Off
- [ ] Engineer: ________________  Date: _____
- [ ] Lead Engineer: ________________  Date: _____
- [ ] QA: ________________  Date: _____

### Phase 2 Sign-Off
- [ ] Engineer: ________________  Date: _____
- [ ] Documentation Lead: ________________  Date: _____

### Phase 3 Sign-Off
- [ ] QA Lead: ________________  Date: _____
- [ ] Engineer: ________________  Date: _____

### Phase 4 Sign-Off
- [ ] Lead Engineer: ________________  Date: _____
- [ ] Product Lead: ________________  Date: _____

### Final Sign-Off
- [ ] Principal Engineer: ________________  Date: _____
- [ ] Engineering Lead: ________________  Date: _____

---

**Checklist Version**: 1.0  
**Status**: READY FOR TEAM REVIEW  
**Print & Post**: Yes (share with engineering team)
