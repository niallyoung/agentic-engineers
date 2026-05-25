# Phase 2: Orchestrator Routing & DELEGATE/HANDBACK Consolidation — Implementation Plan

**Task ID**: 2026-05-24-queue-migration-phase2  
**Status**: PLANNING  
**Complexity**: HIGH  
**Effort**: ~12,000 tokens (4 parallel Engineer streams)  
**Duration**: 4-6 hours (parallel work)

---

## Executive Summary

**Goal**: Migrate DELEGATE/HANDBACK storage from split repo-level paths to unified home directory structure.

**Current State**:
- DELEGATE blocks written to: `artifacts/delegates/` (repo level)
- HANDBACK blocks written to: `queue/processing/` (repo level)
- Queue structure partitioned by session-id but not by harness
- Orchestrator and invoke_agent use inconsistent path detection

**Target State**:
- DELEGATE blocks: `~/.agentic-engineers/artifacts/{session_id}/{harness}/delegates/`
- HANDBACK blocks: `~/.agentic-engineers/artifacts/{session_id}/{harness}/queue/processing/`
- Unified path structure via queue-isolation skill
- Single source of truth for task file locations
- Backward compatibility maintained during migration

**Impact**:
- Affects 2 core files: orchestrator.py (1737 lines), invoke_agent.py (590 lines)
- Requires updating 40+ tests
- No API changes (paths hidden inside QueueManager)
- All external interfaces unchanged

---

## Current Path Architecture (What's Being Replaced)

### DELEGATE Storage (Repo Level)
```
artifacts/delegates/
├── DELEGATE-task-1.yaml
├── DELEGATE-task-2.yaml
└── ...
```
**Read by**: orchestrator.py (for task submission context)  
**Written by**: invoke_agent.py (for reference during agent subprocess)

### Queue Storage (Session Partitioned)
```
artifacts/queue/
├── {session_id}/
│   ├── incoming/
│   │   ├── DELEGATE-task-1.yaml
│   │   └── ...
│   ├── processing/
│   │   ├── task-1-HANDBACK-engineer.yaml
│   │   └── ...
│   ├── done/
│   │   └── ...
│   └── failed/
│       └── ...
```
**OR** `~/.copilot/queue/{session_id}/...` (fallback)

**Problems**:
1. Dual storage: delegates at repo level + queue elsewhere
2. Inconsistent paths during migration
3. Task files scattered across multiple directories
4. Difficult to archive complete task session

---

## Target Path Architecture (After Phase 2)

### Unified Structure
```
~/.agentic-engineers/artifacts/
├── {session_id}/
│   ├── {harness}/                    # New: partition by harness (local, gha, etc.)
│   │   ├── delegates/                # NEW: moved from artifacts/delegates/
│   │   │   ├── DELEGATE-task-1.yaml
│   │   │   └── ...
│   │   ├── queue/
│   │   │   ├── incoming/
│   │   │   │   ├── DELEGATE-task-1.yaml
│   │   │   │   └── ...
│   │   │   ├── processing/
│   │   │   │   ├── task-1-HANDBACK-engineer.yaml
│   │   │   │   └── ...
│   │   │   ├── done/
│   │   │   │   └── ...
│   │   │   └── failed/
│   │   │       └── ...
│   │   └── metadata.json             # Session + harness metadata
│   └── ...
```

**Advantages**:
1. Single unified location
2. Complete task session containment
3. Easier to archive entire session
4. Matches queue-isolation design
5. Clear harness-based partitioning

---

## Implementation Plan

### Phase 2, Stream 1: Update Orchestrator Task Routing

**File**: `src/orchestration/agents/orchestrator.py`  
**Complexity**: HIGH  
**Effort**: 2500 tokens

#### Changes Required

1. **Import queue-isolation** (new)
   - At module top, add import pattern for queue-isolation
   - Use try/except to gracefully fall back if unavailable
   - Store as module-level `_QUEUE_ISOLATION` singleton

2. **Update `__init__` initialization**
   - Call queue-isolation to detect session_id
   - Call queue-isolation to detect harness
   - Call queue-isolation to initialize queue structure
   - Store both `session_id` and `harness` as instance variables
   - Fall back to current behavior if queue-isolation unavailable

3. **Update path accessor methods** (lines 458-468)
   - `get_incoming_queue_dir()` → return `~/.agentic-engineers/artifacts/{sid}/{harness}/queue/incoming/`
   - `get_processing_queue_dir()` → return `~/.agentic-engineers/artifacts/{sid}/{harness}/queue/processing/`
   - `get_done_queue_dir()` → return `~/.agentic-engineers/artifacts/{sid}/{harness}/queue/done/`
   - Add new: `get_delegates_dir()` → return `~/.agentic-engineers/artifacts/{sid}/{harness}/delegates/`

4. **Update route_task()** (line 731)
   - Pass both `session_id` and `harness` to agent invocation
   - Pass new delegates path to invoke_agent

5. **Update queue transition methods**
   - `move_to_processing()` (line 489) → use new path
   - `move_to_done()` (line 496) → use new path
   - `move_task()` (line 523) → use new path
   - `archive_task()` (line 514) → use new path
   - `move_to_failed()` → use new path

#### Backward Compatibility
- Detect if running under queue-isolation
- If yes: use new unified paths
- If no: fall back to current behavior
- No impact on external API

#### Testing
- All 25+ existing orchestrator tests must pass
- Add new tests:
  - Test with queue-isolation available
  - Test with queue-isolation unavailable (fallback)
  - Test harness detection and partitioning

---

### Phase 2, Stream 2: Consolidate DELEGATE/HANDBACK Storage

**Files**:
- `src/orchestration/agents/orchestrator.py`
- `src/orchestration/agents/invoke_agent.py`

**Complexity**: HIGH  
**Effort**: 2000 tokens

#### Changes Required

1. **DELEGATE Storage Migration**
   - Remove `artifacts/delegates/` at repo level (no longer written at runtime)
   - Update orchestrator to write DELEGATE files to: `~/.agentic-engineers/artifacts/{sid}/{harness}/delegates/`
   - Update invoke_agent to read from new path

2. **HANDBACK Storage Migration**
   - Update queue paths to include harness partition
   - HANDBACK written to: `~/.agentic-engineers/artifacts/{sid}/{harness}/queue/processing/`
   - Reading remains in processing_dir (now new path)

3. **Path Construction Logic**
   - Create helper method: `_get_queue_root(session_id, harness)` → returns base path
   - Use consistently across both files
   - Accept both explicit paths and auto-detection

#### Validation
- Grep repo for any remaining references to old `artifacts/delegates/` path
- Confirm no dual-writing
- Confirm all reads use new paths

---

### Phase 2, Stream 3: Update invoke_agent Path Handling

**File**: `src/orchestration/agents/invoke_agent.py`  
**Complexity**: HIGH  
**Effort**: 1800 tokens

#### Changes Required

1. **Constructor Update** (line 52-141)
   - Accept explicit `delegates_dir` parameter
   - Accept `session_id` and `harness` parameters
   - Call queue-isolation for auto-detection if not provided
   - Initialize:
     ```python
     self.session_id = session_id or qi.get_session_id()
     self.harness = harness or qi.detect_harness()
     self.queue_root = qi.get_queue_path(self.session_id, self.harness)
     self.delegates_dir = self.queue_root.parent / "delegates"
     self.processing_dir = self.queue_root / "processing"
     ```

2. **DELEGATE Write Path** (line 188)
   - From: currently writes to passed delegates_dir
   - To: ensure delegates_dir = `~/.agentic-engineers/artifacts/{sid}/{harness}/delegates/`

3. **HANDBACK Read Path** (line 230, 247, 260)
   - From: currently reads from processing_dir
   - To: ensure processing_dir = `~/.agentic-engineers/artifacts/{sid}/{harness}/queue/processing/`

4. **Environment Variable Passing**
   - Pass `DELEGATE_PATH` to subprocess (existing)
   - Add: `SESSION_ID` env var
   - Add: `HARNESS` env var (for nested agent calls)

#### Testing
- All 15+ invoke_agent tests must pass
- Add tests:
  - Test with explicit paths
  - Test with queue-isolation auto-detection
  - Test nested agent calls (agent invoking another agent)

---

### Phase 2, Stream 4: Update Queue Transition Methods

**Files**:
- `src/orchestration/agents/orchestrator.py`
- `src/orchestration/queue_manager.py`

**Complexity**: HIGH  
**Effort**: 1500 tokens

#### Changes Required

1. **In orchestrator.py**
   - `move_to_processing()` (line 489)
     - Update source/dest paths to use new queue_root
   - `move_to_done()` (line 496)
     - Update source/dest paths to use new queue_root
   - `archive_task()` (line 514)
     - Archive to: `~/.agentic-engineers/artifacts/{sid}/{harness}/queue/archive/`

2. **In queue_manager.py** (if exists)
   - `move_task()` → update paths
   - `move_to_failed()` → update paths
   - Add: `get_failed_dir()` accessor

3. **Directory Structure Initialization**
   - Ensure all subdirs created with new paths:
     - `{harness}/delegates/`
     - `{harness}/queue/incoming/`
     - `{harness}/queue/processing/`
     - `{harness}/queue/done/`
     - `{harness}/queue/failed/`
     - `{harness}/queue/archive/`

#### Task Lifecycle States
```
incoming/DELEGATE-{task}.yaml
    ↓
processing/DELEGATE-{task}.yaml + HANDBACK-{task}-{role}.yaml
    ↓
done/{task}-{status}.yaml (HANDBACK archived)
    
OR (on failure):
    ↓
failed/{task}-{status}.yaml
    ↓
archive/{timestamp}_{task}.yaml
```

#### Testing
- All queue transition tests must pass
- Test each transition:
  - incoming → processing
  - processing → done
  - processing → failed
  - failed → archive

---

## Implementation Order (Dependencies)

```
1. p2-1-analyze-paths ──────────────────────┐
                                             ├─→ p2-2-design-new-paths
                                             │                      ↓
                                             │    ┌─────────────────┼──────────────────┐
                                             │    ↓                 ↓                  ↓
                        p2-3-stream1 (Orch)  p2-4-stream2     p2-5-stream3      p2-6-stream4
                        (Task Routing)       (Storage)        (invoke_agent)      (Transitions)
                        ↓                    ↓                 ↓                   ↓
                    p2-7-orch-tests      p2-8-invoke-tests    p2-9-verify
```

**Parallelizable Streams**:
- Stream 1: Update orchestrator routing
- Stream 2: Consolidate storage (DELEGATE/HANDBACK)
- Stream 3: Update invoke_agent paths
- Stream 4: Update queue transitions

**Sequences** (must complete in order):
1. Design phase must be complete before any implementation
2. Path accessors must be in place before tests run
3. Tests validation (steps 7-9) after implementation complete

---

## Files Modified

### Core Implementation
- `src/orchestration/agents/orchestrator.py` (1737 lines)
  - Lines 398-450: `__init__` (add harness detection)
  - Lines 458-468: Path accessors (add delegates_dir)
  - Lines 489-520: Queue transitions (update paths)
  - Lines 731-780: route_task (pass new context)
  - Add: `_get_queue_root()` helper

- `src/orchestration/agents/invoke_agent.py` (590 lines)
  - Lines 52-141: `__init__` (add session_id/harness)
  - Lines 127-141: Path initialization (use queue-isolation)
  - Lines 188-195: DELEGATE write (use new delegates_dir)
  - Lines 230-270: HANDBACK read (use new processing_dir)

- `src/orchestration/queue_manager.py` (if exists)
  - Update path methods
  - Add harness-aware initialization

### Tests (40+ files)
- `tests/test_invoke_agent.py` (15+ tests)
  - Update fixtures to use new paths
  - Add tests for harness detection
  - Add tests for nested agent calls

- `tests/test_orchestrator_integration.py` (25+ tests)
  - Update fixtures to use new paths
  - Add tests for queue transitions
  - Add tests for backward compatibility

- `tests/orchestration/test_orchestrator_protocol_integration.py`
  - Update path references

### Documentation Updates (Optional for Phase 2)
- Add migration notes to ARCHITECTURE-QUEUE-UNIFIED-IMPLEMENTATION.md
- Update path examples in docs

---

## Risk Assessment

### High Risk Areas
1. **Backward Compatibility**: Ensure fallback to legacy paths works
   - Mitigation: Comprehensive fallback logic with logging
   
2. **Test Fixtures**: 40+ tests may need adjustment
   - Mitigation: Create test helper for path setup
   
3. **Nested Agent Calls**: Agent-invoking-agent scenario
   - Mitigation: Pass SESSION_ID, HARNESS env vars
   
4. **File Loss**: Tasks in-flight during migration
   - Mitigation: Archive old locations after successful transition

### Medium Risk Areas
1. **Path Detection**: Multiple ways to detect session/harness
   - Mitigation: Centralize detection logic
   
2. **Concurrent Sessions**: Multiple sessions running simultaneously
   - Mitigation: queue-isolation already handles this
   
3. **Storage Quota**: Consolidating paths may impact quota
   - Mitigation: Monitor directory sizes

### Low Risk Areas
1. **External APIs**: All changes internal to orchestration layer
   - No impact on agent interfaces
   - No impact on DELEGATE/HANDBACK schemas

---

## Testing Strategy

### Unit Tests (by stream)
1. **Stream 1** (Orch Routing): 8 tests
   - Test path detection with/without queue-isolation
   - Test harness partitioning
   - Test queue transitions

2. **Stream 2** (Storage): 6 tests
   - Test DELEGATE write/read to new path
   - Test HANDBACK write/read to new path
   - Test no dual storage

3. **Stream 3** (invoke_agent): 12 tests
   - Test constructor with/without explicit paths
   - Test DELEGATE file creation
   - Test HANDBACK polling from new path
   - Test nested agent calls

4. **Stream 4** (Queue Transitions): 8 tests
   - Test each state transition
   - Test archive behavior
   - Test failed task handling

### Integration Tests
- End-to-end orchestrator cycle
- Multiple tasks in parallel
- Backward compatibility (old paths still work)

### Validation Tests
- No references to old `artifacts/delegates/` at runtime
- No dual-storage (no tasks in both old and new locations)
- All 40+ existing tests pass

---

## Success Criteria

### Functional
- ✅ Orchestrator routes via new paths
- ✅ invoke_agent reads/writes from new paths
- ✅ All queue transitions use new paths
- ✅ No more dual storage at runtime
- ✅ Backward compatibility maintained

### Quality
- ✅ All 25+ orchestrator tests pass
- ✅ All 15+ invoke_agent tests pass
- ✅ 0 new bugs introduced
- ✅ Test coverage maintained at 85%+

### Documentation
- ✅ Migration notes in architecture docs
- ✅ Path examples updated
- ✅ Deprecation timeline communicated

---

## Effort Estimate

| Task | Tokens | Duration | Parallelizable |
|------|--------|----------|---|
| Design & analysis | 1300 | 30 min | No |
| Stream 1: Orch routing | 2500 | 1.5 hrs | Yes* |
| Stream 2: Storage consolidation | 2000 | 1 hr | Yes* |
| Stream 3: invoke_agent paths | 1800 | 1 hr | Yes* |
| Stream 4: Queue transitions | 1500 | 1 hr | Yes* |
| Test fixes & validation | 1900 | 1.5 hrs | Partial |
| **Total** | **12,000** | **4-6 hrs** | |

*Streams can run in parallel after design is complete.

---

## Decision: Execute vs. Delegate

**Recommendation**: **DELEGATE to 4 parallel Engineers**

**Reasoning**:
1. **High complexity**: Multiple interacting systems (orchestrator, invoke_agent, queue_manager)
2. **Scope breadth**: 4 distinct work streams that can execute in parallel
3. **Test volume**: 40+ tests to update/validate
4. **Estimated effort**: >10,000 tokens (~4-6 hours sequential, 1-2 hours parallel)
5. **Risk mitigation**: Parallel execution reduces total time and risk concentration

**Delegation Plan**:
- **Engineer 1** (Stream 1): Orchestrator routing + path accessors
- **Engineer 2** (Stream 2): Storage consolidation (DELEGATE/HANDBACK)
- **Engineer 3** (Stream 3): invoke_agent path handling
- **Engineer 4** (Stream 4): Queue transition methods

**Orchestration**:
1. Senior Engineer writes this plan ✅
2. Senior Engineer creates 4 sub-DELEGATEs (one per stream)
3. Each Engineer executes their stream independently
4. Senior Engineer validates results and coordinates fixes
5. QE runs comprehensive test suite + validation

---

## Next Steps (After Approval)

1. Create 4 sub-DELEGATE blocks (one per stream)
2. Assign to 4 Engineers (or use task scheduling)
3. All Engineers work in parallel
4. Collect HANDBACKs from each stream
5. Validate all tests pass (40+ tests)
6. Verify no dual storage
7. Return consolidated HANDBACK with summary

