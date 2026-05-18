# Phase H: Test Coverage Improvements — Implementation Plan

**Date**: 2026-05-18  
**Status**: In Progress  
**Target**: 85%+ coverage per module, 0% → 100% for critical modules  
**Effort**: 1 week  
**Owner**: Quality Engineer + Engineer

---

## Overview

Phase H focuses on improving test coverage for 14 modules currently at 0% coverage. These modules are critical for queue management, protocol validation, and orchestration.

**Current State:**
- Overall coverage: 76% (11,160 statements, 2,715 uncovered)
- 0% coverage modules: 14 (total 1,361 statements)
- Test failures: 7 failed, 21 errors (pre-existing, unrelated to consolidation)
- Test passes: 2,452 passing

**Target State:**
- Overall coverage: 85%+ (reduce uncovered statements by 50%)
- 0% coverage modules: 100% (all critical modules tested)
- Test failures: 0 (fix pre-existing failures)
- Test passes: 2,500+ passing

---

## Module Priority & Implementation Plan

### TIER 1: CRITICAL (HIGH PRIORITY, >100 statements)

#### 1. `src/skills/queue-management/scripts/core_protocol_validator.py` (150 stmts)
**Purpose**: Protocol validation for DELEGATE/HANDBACK  
**Coverage**: 0%  
**Risk**: HIGH (validates all protocol messages)  
**Plan**:
- [ ] Create `tests/skills/queue-management/test_core_protocol_validator.py`
- [ ] Test valid DELEGATE/HANDBACK structures
- [ ] Test invalid field combinations
- [ ] Test schema validation errors
- [ ] Test edge cases (empty fields, null values, type mismatches)
- **Target**: 95%+ coverage (150 stmts → 7-8 stmts uncovered)

#### 2. `src/orchestration/tools/protocol_audit.py` (201 stmts)
**Purpose**: Protocol compliance auditing  
**Coverage**: 0%  
**Risk**: HIGH (audits all protocol compliance)  
**Plan**:
- [ ] Create `tests/orchestration/tools/test_protocol_audit.py`
- [ ] Test audit report generation
- [ ] Test compliance checking
- [ ] Test violation detection
- [ ] Test report formatting
- **Target**: 90%+ coverage (201 stmts → 20 stmts uncovered)

#### 3. `src/skills/healer-metrics-analyzer.py` (137 stmts)
**Purpose**: Metrics analysis and healing  
**Coverage**: 0%  
**Risk**: MEDIUM (analysis tool, not critical path)  
**Plan**:
- [ ] Create `tests/skills/test_healer_metrics_analyzer.py`
- [ ] Test metrics aggregation
- [ ] Test anomaly detection
- [ ] Test healing recommendations
- [ ] Test output formatting
- **Target**: 85%+ coverage (137 stmts → 20 stmts uncovered)

#### 4. `src/orchestration/queue_manager.py` (96 stmts)
**Purpose**: Queue management operations  
**Coverage**: 0%  
**Risk**: HIGH (core queue operations)  
**Plan**:
- [ ] Create `tests/orchestration/test_queue_manager.py`
- [ ] Test queue initialization
- [ ] Test task enqueue/dequeue
- [ ] Test state transitions
- [ ] Test error handling
- **Target**: 95%+ coverage (96 stmts → 5 stmts uncovered)

### TIER 2: IMPORTANT (MEDIUM PRIORITY, 50-100 statements)

#### 5. `src/skills/queue-management/tests/test_validators.py` (104 stmts)
**Purpose**: Test suite for validators (currently 0% coverage)  
**Coverage**: 0%  
**Risk**: MEDIUM (test file, but needs coverage)  
**Plan**:
- [ ] Implement actual test cases (currently empty)
- [ ] Test validator instantiation
- [ ] Test validation logic
- [ ] Test error reporting
- **Target**: 90%+ coverage

#### 6. `src/skills/queue-management/tests/test_rate_limiting.py` (69 stmts)
**Purpose**: Test suite for rate limiting (currently 0% coverage)  
**Coverage**: 0%  
**Risk**: MEDIUM (test file, but needs coverage)  
**Plan**:
- [ ] Implement actual test cases (currently empty)
- [ ] Test rate limit enforcement
- [ ] Test token bucket algorithm
- [ ] Test burst handling
- **Target**: 90%+ coverage

#### 7. `src/skills/queue-management/tests/test_queue_ops.py` (63 stmts)
**Purpose**: Test suite for queue operations (currently 0% coverage)  
**Coverage**: 0%  
**Risk**: MEDIUM (test file, but needs coverage)  
**Plan**:
- [ ] Implement actual test cases (currently empty)
- [ ] Test queue operations
- [ ] Test task creation/deletion
- [ ] Test state management
- **Target**: 90%+ coverage

#### 8. `src/orchestration/agents/testing_harness.py` (56 stmts)
**Purpose**: Testing harness for agents  
**Coverage**: 0%  
**Risk**: LOW (testing utility, not critical path)  
**Plan**:
- [ ] Create `tests/orchestration/agents/test_testing_harness.py`
- [ ] Test harness initialization
- [ ] Test mock agent execution
- [ ] Test result capture
- **Target**: 85%+ coverage

### TIER 3: OPTIONAL (LOW PRIORITY, <50 statements)

#### 9. `src/orchestration/agents/AGENT-IMPLEMENTATION-TEMPLATE.py` (63 stmts)
**Purpose**: Template for agent implementation  
**Coverage**: 0%  
**Risk**: LOW (template, not executed)  
**Plan**:
- [ ] Create `tests/orchestration/agents/test_agent_template.py`
- [ ] Test template structure
- [ ] Test method signatures
- **Target**: 80%+ coverage

#### 10. `src/skills/queue-management/tests/test_integration.py` (42 stmts)
**Purpose**: Integration test suite (currently 0% coverage)  
**Coverage**: 0%  
**Risk**: MEDIUM (integration tests)  
**Plan**:
- [ ] Implement actual test cases (currently empty)
- [ ] Test end-to-end workflows
- [ ] Test component integration
- **Target**: 85%+ coverage

#### 11. `src/orchestration/agents/orchestrator_testing_harness.py` (36 stmts)
**Purpose**: Orchestrator-specific testing harness  
**Coverage**: 0%  
**Risk**: LOW (testing utility)  
**Plan**:
- [ ] Create `tests/orchestration/agents/test_orchestrator_harness.py`
- [ ] Test harness initialization
- [ ] Test orchestrator mocking
- **Target**: 80%+ coverage

#### 12. `src/orchestration/errors.py` (13 stmts)
**Purpose**: Error definitions  
**Coverage**: 0%  
**Risk**: LOW (error definitions)  
**Plan**:
- [ ] Create `tests/orchestration/test_errors.py`
- [ ] Test error instantiation
- [ ] Test error messages
- **Target**: 100% coverage (13 stmts)

#### 13. `src/skills/queue-management/tests/conftest.py` (5 stmts)
**Purpose**: Pytest configuration  
**Coverage**: 0%  
**Risk**: LOW (configuration)  
**Plan**:
- [ ] Ensure conftest is imported by tests
- [ ] Test fixture availability
- **Target**: 100% coverage (5 stmts)

#### 14. `src/skills/queue-management/tests/test_core_protocol_validator.py` (324 stmts)
**Purpose**: Test suite for core protocol validator (currently 0% coverage)  
**Coverage**: 0%  
**Risk**: HIGH (test file for critical module)  
**Plan**:
- [ ] Implement actual test cases (currently empty)
- [ ] Test protocol validation
- [ ] Test error handling
- [ ] Test edge cases
- **Target**: 95%+ coverage

---

## Implementation Schedule

### Week 1 (2026-05-18 to 2026-05-24)

**Day 1-2: TIER 1 Critical Modules**
- [ ] `core_protocol_validator.py` — 150 stmts
- [ ] `protocol_audit.py` — 201 stmts
- [ ] `queue_manager.py` — 96 stmts
- **Target**: 3 modules, 447 stmts, 95%+ coverage each

**Day 3: TIER 1 Continued**
- [ ] `healer-metrics-analyzer.py` — 137 stmts
- [ ] `test_validators.py` — 104 stmts
- **Target**: 2 modules, 241 stmts, 90%+ coverage each

**Day 4-5: TIER 2 Important Modules**
- [ ] `test_rate_limiting.py` — 69 stmts
- [ ] `test_queue_ops.py` — 63 stmts
- [ ] `testing_harness.py` — 56 stmts
- [ ] `AGENT-IMPLEMENTATION-TEMPLATE.py` — 63 stmts
- **Target**: 4 modules, 251 stmts, 85%+ coverage each

**Day 6-7: TIER 3 Optional + Fixes**
- [ ] `test_integration.py` — 42 stmts
- [ ] `orchestrator_testing_harness.py` — 36 stmts
- [ ] `errors.py` — 13 stmts
- [ ] `conftest.py` — 5 stmts
- [ ] `test_core_protocol_validator.py` — 324 stmts
- [ ] Fix pre-existing test failures (7 failed, 21 errors)
- **Target**: All modules at 85%+ coverage

---

## Testing Strategy

### TDD Red-Green-Refactor

For each module:

1. **RED**: Write failing tests (test structure, assertions)
2. **GREEN**: Implement minimal code to pass tests
3. **REFACTOR**: Improve code quality, add edge cases

### Test Structure

```python
# tests/orchestration/test_queue_manager.py
import pytest
from src.orchestration.queue_manager import QueueManager

class TestQueueManagerInitialization:
    def test_queue_manager_initializes_with_valid_path(self):
        qm = QueueManager(queue_dir="/tmp/queue")
        assert qm.queue_dir == "/tmp/queue"
    
    def test_queue_manager_raises_on_invalid_path(self):
        with pytest.raises(ValueError):
            QueueManager(queue_dir=None)

class TestQueueOperations:
    def test_enqueue_task(self):
        qm = QueueManager(queue_dir="/tmp/queue")
        task = {"task_id": "test-001", "role": "engineer"}
        qm.enqueue(task)
        assert qm.get_task("test-001") == task
    
    def test_dequeue_task(self):
        qm = QueueManager(queue_dir="/tmp/queue")
        task = qm.dequeue()
        assert task is not None
```

### Coverage Targets

| Module | Current | Target | Effort |
|--------|---------|--------|--------|
| core_protocol_validator.py | 0% | 95% | 4h |
| protocol_audit.py | 0% | 90% | 4h |
| queue_manager.py | 0% | 95% | 3h |
| healer-metrics-analyzer.py | 0% | 85% | 3h |
| test_validators.py | 0% | 90% | 2h |
| test_rate_limiting.py | 0% | 90% | 2h |
| test_queue_ops.py | 0% | 90% | 2h |
| testing_harness.py | 0% | 85% | 2h |
| AGENT-IMPLEMENTATION-TEMPLATE.py | 0% | 80% | 1h |
| test_integration.py | 0% | 85% | 2h |
| orchestrator_testing_harness.py | 0% | 80% | 1h |
| errors.py | 0% | 100% | 0.5h |
| conftest.py | 0% | 100% | 0.5h |
| test_core_protocol_validator.py | 0% | 95% | 4h |
| **TOTAL** | | | **32.5h** |

---

## Success Criteria

✅ **Coverage Targets Met**:
- All 14 modules at ≥80% coverage
- 8 modules at ≥90% coverage
- 5 modules at ≥95% coverage
- Overall coverage: 85%+

✅ **Test Quality**:
- All tests follow TDD (Red-Green-Refactor)
- All tests have clear assertions
- All tests document expected behavior
- Edge cases covered (null, empty, invalid inputs)

✅ **Pre-Existing Failures Fixed**:
- 7 failed tests fixed
- 21 errors resolved
- All 2,500+ tests passing

✅ **Documentation**:
- Test files include docstrings
- Coverage report generated
- Phase H completion documented

---

## Known Issues & Mitigations

**Issue 1**: Some modules are test files themselves (test_validators.py, test_rate_limiting.py, etc.)
- **Mitigation**: Implement actual test cases in these files (currently empty stubs)

**Issue 2**: Some modules are templates/utilities (AGENT-IMPLEMENTATION-TEMPLATE.py, testing_harness.py)
- **Mitigation**: Test structure and interface, not full functionality

**Issue 3**: Pre-existing test failures unrelated to consolidation
- **Mitigation**: Fix as part of Phase H; document root causes

---

## Next Steps

1. ✅ Identify 0% coverage modules (done)
2. ⏳ Create test scaffolds (TDD RED phase)
3. ⏳ Implement tests (TDD GREEN phase)
4. ⏳ Refactor and improve (TDD REFACTOR phase)
5. ⏳ Fix pre-existing failures
6. ⏳ Verify coverage targets met
7. ⏳ Commit Phase H completion

---

**Owner**: Quality Engineer  
**Task ID**: 2026-05-18-phase-h-test-coverage  
**Deadline**: 2026-05-24 (end of week)
