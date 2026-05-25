# Phase 3 Quality Validation: Test Migration & Harness Integration

**Status**: In Progress  
**Baseline**: 2745 tests passing  
**Target**: All tests passing with new queue paths + 14-22 new tests  
**Effort**: HIGH (16 hours estimated)

---

## Overview

This document tracks Phase 3 implementation: updating all tests to use new queue paths from queue-isolation skill, adding multi-harness isolation tests, and verifying fresh install scenarios.

### New Path Structure
```
~/.agentic-engineers/artifacts/{session_id}/{harness}/queue/
  ├── incoming/
  ├── processing/
  ├── done/
  └── failed/
```

### Legacy Path (deprecated but supported during migration)
```
~/.copilot/queue/{session_id}/
  ├── incoming/
  ├── processing/
  └── done/
```

---

## Phase 3 Deliverables Checklist

### 1. Test Fixtures Migration ✓ PLANNED
- [ ] Create `tests/helpers/queue_test_helpers.py` with fixtures for isolated and legacy queues
- [ ] Update `tests/conftest.py` to include new fixtures
- [ ] Migrate all queue path fixtures in test files

**Files to Update**:
- `tests/test_queue_management.py` (26 tests)
- `tests/test_queue_state_transitions.py` (15 tests)
- `tests/test_queue_state_transitions_integration.py` (6 tests)
- `tests/test_session_queue_partitioning.py` (15 tests)
- `tests/test_queue_enforcement.py` (TBD)
- `tests/test_orchestrator_integration.py` (TBD)
- `tests/test_invoke_agent.py` (TBD)
- All other queue-related tests

**Target**: All 60+ existing queue tests passing with new paths

### 2. Multi-Harness Isolation Tests ✓ PLANNED
**New File**: `tests/test_multi_harness_isolation.py`

Tests to add:
- [ ] `test_cli_copilot_session_id_isolated_from_claude`
- [ ] `test_queue_artifacts_isolated_by_harness`
- [ ] `test_three_simultaneous_harnesses_with_same_user`
- [ ] `test_session_data_survives_harness_config_wipe`
- [ ] `test_harness_switching_doesnt_cross_contaminate`
- [ ] `test_metadata_json_per_harness`
- [ ] `test_isolation_across_concurrent_delegates`
- [ ] `test_legacy_fallback_works_when_isolation_unavailable`

**Target**: 8-12 new tests, all passing

### 3. Fresh Install Verification Tests ✓ PLANNED
**New File**: `tests/test_fresh_install_with_unified_queue.py`

Tests to add:
- [ ] `test_make_install_fresh_preserves_queue_data`
- [ ] `test_legacy_queue_data_migrated_to_new_location`
- [ ] `test_queue_operations_work_post_fresh_install`
- [ ] `test_delegation_works_after_fresh_install`
- [ ] `test_multi_harness_queues_preserved_on_install_fresh`
- [ ] `test_artifacts_directory_survives_install_operations`
- [ ] `test_handback_files_persisted_across_install`

**Target**: 6-10 new tests, all passing

### 4. Harness Integration Code Updates ✓ PLANNED

**Files to Update**:
- `src/harnesses/copilot_cli/__init__.py`
  - [ ] Update to detect `AGENTIC_HARNESS=copilot`
  - [ ] Use queue-isolation for path detection
  - [ ] Pass `AGENTIC_SESSION_ID` if available

- `src/orchestration/agents/orchestrator.py` - QueueManager
  - [ ] Try queue-isolation first, fall back to legacy
  - [ ] Update `__init__` to use isolation paths
  - [ ] Document dual-path behavior

- Harness detection in tests
  - [ ] Verify all harness-specific tests work with new structure

**Target**: All harness code uses new paths, backward compatible

### 5. Test Coverage Summary

**Existing Tests to Verify Still Pass**:
- ✅ 26 tests in `test_queue_management.py`
- ✅ 15 tests in `test_queue_state_transitions.py`
- ✅ 6 tests in `test_queue_state_transitions_integration.py`
- ✅ 15 tests in `test_session_queue_partitioning.py`
- ✅ Various tests in orchestration/ (93 tests)
- ___ tests in `test_queue_enforcement.py`
- ___ tests in `test_orchestrator_integration.py`
- ___ tests in `test_invoke_agent.py`

**Total Existing Tests**: 60+ queue-related tests  
**New Tests to Add**: 14-22 tests  
**Total After Phase 3**: 2745 + (14-22) = 2759-2767 tests

---

## Implementation Approach

### Step 1: Create Test Helpers (2 hours)
1. Create `tests/helpers/queue_test_helpers.py`
2. Implement `isolated_queue_env` fixture
3. Implement `legacy_queue_env` fixture
4. Add utility functions for path assertions

### Step 2: Migrate Existing Tests (4 hours)
1. Update `tests/conftest.py` to import helpers
2. Migrate `test_queue_management.py` fixtures
3. Migrate `test_queue_state_transitions.py` fixtures
4. Migrate `test_session_queue_partitioning.py` fixtures
5. Verify all migrations with test runs

### Step 3: Add Multi-Harness Tests (2 hours)
1. Create `tests/test_multi_harness_isolation.py`
2. Implement 8-12 isolation tests
3. Verify harness detection logic
4. Test session ID collision prevention

### Step 4: Add Fresh Install Tests (2 hours)
1. Create `tests/test_fresh_install_with_unified_queue.py`
2. Implement 6-10 fresh install tests
3. Mock `make install-fresh` operations
4. Verify data persistence

### Step 5: Update Harness Code (2 hours)
1. Update `src/harnesses/copilot_cli/__init__.py`
2. Update QueueManager in `orchestrator.py` to prefer isolation
3. Add fallback logic for backward compatibility
4. Test harness integration

### Step 6: Comprehensive Testing (1 hour)
1. Run full test suite
2. Verify no regressions
3. Validate coverage >80% for new paths
4. Run performance benchmarks

---

## Success Criteria

✅ All 60+ existing queue tests pass with new paths  
✅ 8-12 multi-harness isolation tests added & passing  
✅ 6-10 fresh install verification tests added & passing  
✅ No test regressions from baseline  
✅ Harness code updated for new paths  
✅ Backward compatibility maintained (legacy fallback)  
✅ Full test suite: 2759+ tests passing  
✅ Code coverage: >85% for new/modified code  
✅ Ready for Phase 4  

---

## Regression Risk Assessment

**Low Risk** (isolated changes, backward compatible):
- New fixtures don't affect existing tests
- Harness code changes use fallback logic
- Legacy paths still work during migration

**Medium Risk** (integration points):
- QueueManager dual-path logic
- Session ID detection priority order
- Environment variable interactions

**Mitigation**:
- Comprehensive test coverage
- Backward compatibility layer (fallback to legacy)
- CI/CD validation before merge
- Manual spot-checks of critical paths

---

## Blockers & Dependencies

None identified. All requirements are clear from architecture document.

---

## Phase 4 Readiness

After Phase 3 completion, ready for Phase 4:
- ✅ Documentation updates
- ✅ CHANGELOG updates  
- ✅ Migration guide creation
- ✅ Deprecation timeline announcement
- ✅ Code cleanup (remove legacy after week 4)
