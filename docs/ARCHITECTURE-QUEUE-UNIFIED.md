# Architectural Redesign: Unified Queue Path Migration

**Status**: DESIGN & PLANNING PHASE (No Implementation Yet)  
**Role**: Principal Engineer  
**Effort**: High  
**Timeline**: 4 phases, ~8 weeks  
**Risk Level**: HIGH (data loss risk) → MEDIUM (with mitigation)  

---

## Executive Summary

### The Problem: Critical Data Loss Risk

The current queue architecture stores session artifacts in **`~/.copilot/queue/{session-id}/`**, which is **INSIDE the harness config directory**. When `make install-fresh` runs:

1. It **backs up** the entire `~/.copilot/` directory
2. It **wipes** the entire `~/.copilot/` directory  
3. It **restores only** the managed subdirectories (agents/, skills/)
4. **Result**: All session queue data is LOST

### The Solution: Separate Session Artifacts

Move all session artifacts to **`~/.agentic-engineers/{session-id}/`**, which is **OUTSIDE the harness config directory**:

- ✅ Session data survives `make install-fresh`
- ✅ No data loss on fresh installs
- ✅ Harness configs remain clean
- ✅ Multi-harness isolation preserved (Claude/Copilot/GPT/local)
- ✅ Backward compatibility maintained during migration

---

## Current Architecture (Broken)

```
CURRENT STATE: Data at risk
═══════════════════════════

~/.copilot/                         ← Harness config (backed up/wiped)
├── agents/
│   ├── orchestrator-agent.md
│   └── engineer-agent.md
├── skills/
│   ├── queue-management/
│   └── ...
└── queue/                          ← ⚠️  PROBLEM: Inside harness dir!
    └── {session-id}/
        ├── incoming/               ← Gets wiped by install-fresh
        ├── processing/
        ├── done/
        └── failed/

artifacts/                          ← Repository (readonly)
├── delegates/                      ← Example payloads
├── handbacks/                      ← Orphaned (not used)
└── queue/                          ← Orphaned (not used)
```

### Current Component Locations

```
Orchestration Module:
  └── src/orchestration/
      ├── agents/orchestrator.py        ← QueueManager init, session_queue_dir
      ├── agents/invoke_agent.py        ← Queue reads/writes
      ├── queue_compat.py               ← Backwards-compat shim (deprecated)
      └── [15+ agents]                  ← Use orchestrator's QueueManager

Skills (Queue Operations):
  └── src/skills/
      ├── queue-management/
      │   ├── queue_manager.py          ← CLI-facing queue operations
      │   └── scripts/queue_ops.py      ← Queue API (DEFAULT_QUEUE_PATH)
      └── _meta/queue-isolation/
          ├── scripts/queue_isolation.py ← NEW: Path isolation logic
          └── tests/                     ← 28 comprehensive tests
```

### Session Artifact Categories (Currently ALL at risk)

| Category | Current Path | Contents | Risk |
|----------|--------------|----------|------|
| **Queue** | `~/.copilot/queue/{sid}/` | DELEGATE/HANDBACK files | **LOST** |
| **Delegates** | `~/.copilot/queue/{sid}/incoming/` | Active DELEGATE payloads | **LOST** |
| **Handbacks** | `~/.copilot/queue/{sid}/done/` | Agent responses | **LOST** |
| **Failed** | `~/.copilot/queue/{sid}/failed/` | Error tasks (DLQ) | **LOST** |
| **Metadata** | Not stored | Session-level metadata | **MISSING** |
| **Spans** | Not stored | Request tracing data | **MISSING** |
| **Logs** | Not stored | Session logs | **MISSING** |

---

## Target Architecture (Safe)

```
TARGET STATE: Data protected
════════════════════════════

~/.agentic-engineers/               ← Session artifacts (SEPARATE, safe)
└── artifacts/
    └── {session-id}/               ← Unique per session
        ├── local/                  ← Default harness
        │   ├── metadata.json       ← Session metadata (created_at, harness)
        │   ├── queue/
        │   │   ├── incoming/       ← New DELEGATEs (safe!)
        │   │   ├── processing/     ← Tasks in-flight
        │   │   ├── done/           ← Completed HANDBACKs
        │   │   └── failed/         ← Error tasks (DLQ)
        │   ├── delegates/          ← Active protocol payloads
        │   ├── handbacks/          ← Responses from agents
        │   ├── spans/              ← Request tracing
        │   └── logs/               ← Session logs
        ├── claude/                 ← Claude harness (isolated)
        │   ├── metadata.json
        │   └── queue/ ...
        ├── copilot/                ← Copilot harness (isolated)
        │   ├── metadata.json
        │   └── queue/ ...
        └── gpt/                    ← GPT harness (isolated)
            ├── metadata.json
            └── queue/ ...

~/.copilot/                         ← Harness config only (clean)
├── agents/
│   ├── orchestrator-agent.md
│   └── engineer-agent.md
└── skills/
    ├── queue-management/
    └── ...

artifacts/                          ← Repository examples (readonly)
├── delegates/                      ← Archived DELEGATEs
├── handbacks/                      ← Archived HANDBACKs
└── queue/                          ← Archived queue examples
```

### Target Benefits

✅ **Session data persists across `make install-fresh`**  
✅ **Harness config stays clean and independent**  
✅ **Multi-harness isolation enforced by design**  
✅ **Future analytics available via metadata.json**  
✅ **Backward compatibility during transition**  
✅ **No data loss for existing users**  

---

## Impact Analysis

### Affected Components

#### 1. **Orchestration Module** (`src/orchestration/`)

| Component | Current | Changes Required | Severity |
|-----------|---------|-------------------|----------|
| `agents/orchestrator.py` | Uses `~/.copilot/queue/` | Support both paths during migration | **HIGH** |
| `agents/invoke_agent.py` | Reads from orchestrator.queue_manager | No direct changes (uses manager) | **LOW** |
| `queue_manager.py` | Wraps orchestrator's QueueManager | Update fallback paths | **HIGH** |
| `agents/delegate_validator.py` | Validates DELEGATE files | No changes (path-agnostic) | **LOW** |
| 15+ Agent implementations | Use queue via orchestrator | No changes | **NONE** |

#### 2. **Queue Management Skill** (`src/skills/queue-management/`)

| Component | Current | Changes Required | Severity |
|-----------|---------|-------------------|----------|
| `queue_manager.py` (CLI) | Calls `_try_import_queue_isolation()` | Already prepared for this! | **DONE** |
| `scripts/queue_ops.py` | `_DEFAULT_QUEUE_PATH` | Update to new path | **MEDIUM** |
| `tests/` | Mock queue paths | Update test fixtures | **MEDIUM** |

#### 3. **Queue Isolation Skill** (`src/skills/_meta/queue-isolation/`)

| Component | Current | Changes Required | Severity |
|-----------|---------|-------------------|----------|
| `scripts/queue_isolation.py` | Target architecture | **Already implemented!** | **DONE** |
| `tests/` | 28 comprehensive tests | Already covers migration | **DONE** |

#### 4. **Tests** (`tests/`)

| Test Type | Current | Changes Required | Severity |
|-----------|---------|-------------------|----------|
| `test_orchestration/test_queue_*` | Use `~/.copilot/queue/` | Update paths | **MEDIUM** |
| Mocked queue directories | Hardcoded paths | Use isolation helpers | **MEDIUM** |
| Integration tests | End-to-end flows | Update as needed | **LOW** |

#### 5. **Build System** (`Makefile`)

| Target | Current | Changes Required | Severity |
|--------|---------|-------------------|----------|
| `install-fresh` | Backs up/wipes entire `~/.copilot/` | No changes needed | **NONE** |
| Verification steps | Counts files in `~/.copilot/` | Update to include `~/.agentic-engineers/` | **LOW** |

#### 6. **Documentation** (`docs/`, `artifacts/`)

| File | Current | Changes Required | Severity |
|------|---------|-------------------|----------|
| `QUEUE-PROTOCOL.md` | References `~/.copilot/queue/` | Update paths | **MEDIUM** |
| `artifacts/queue/SCHEMA.md` | References `~/.copilot/queue/` | Update paths | **MEDIUM** |
| `src/AGENTS.md` | References `~/.copilot/queue/` | Update paths | **MEDIUM** |
| `src/TODO.md.template` | References `~/.copilot/queue/` | Update paths | **MEDIUM** |

#### 7. **Environment Detection**

| Env Var | Current | Changes Required | Severity |
|---------|---------|-------------------|----------|
| `COPILOT_SESSION_ID` | Used for session ID | Still used (queue-isolation) | **NONE** |
| `CLAUDE_SESSION_ID` | Used for session ID | Still used (queue-isolation) | **NONE** |
| `AGENTIC_SESSION_ID` | Not used | New (explicit override) | **NEW** |
| `AGENTIC_HARNESS` | Not used | New (explicit override) | **NEW** |

---

## Migration Strategy

### Option A: Gradual Migration (RECOMMENDED)

**Timeline**: 4 weeks  
**Risk**: LOW (backward compatible)  
**Approach**: New code uses `~/.agentic-engineers/`, old code uses `~/.copilot/` as fallback

#### Phase 1: Foundation (Week 1-2)
- ✅ Verify queue-isolation skill is production-ready (28 tests passing)
- Update `src/orchestration/agents/orchestrator.py` to:
  - Try `queue-isolation` first → `~/.agentic-engineers/`
  - Fallback to legacy `~/.copilot/queue/` (backward compatibility)
- Update `src/orchestration/queue_manager.py` to use orchestrator's logic
- Verify all agent implementations use orchestrator's queue_manager

**Deliverables**:
- `src/orchestration/agents/orchestrator.py` v2 (dual-path aware)
- Backward compatibility verified (old code still works)
- 0 broken tests

#### Phase 2: Skills Migration (Week 2)
- Update `src/skills/queue-management/scripts/queue_ops.py`:
  - `_DEFAULT_QUEUE_PATH` → Use queue-isolation
  - Fallback to legacy if queue-isolation unavailable
- Update CLI tests to use isolation helpers
- Documentation updates: flag `~/.copilot/queue/` as legacy

**Deliverables**:
- `src/skills/queue-management/scripts/queue_ops.py` v2 (isolation-aware)
- Updated skill documentation
- Test coverage: 100%

#### Phase 3: Test Suite Migration (Week 3)
- Update all test fixtures to use isolation helpers:
  - `tests/test_orchestration/test_queue_*.py`
  - `tests/test_skills/test_queue_management.py`
  - Replace hardcoded `~/.copilot/queue/` with `QueueIsolation.from_env()`
- Add new tests for multi-harness isolation
- Verify zero data loss scenarios

**Deliverables**:
- All test fixtures updated
- 100% test suite passing
- New: multi-harness collision detection tests

#### Phase 4: Documentation & Cutover (Week 4)
- Update documentation:
  - `docs/QUEUE-PROTOCOL.md` — dual-path architecture
  - `docs/ARCHITECTURE-QUEUE-UNIFIED.md` → This doc
  - `artifacts/queue/SCHEMA.md` — path updates
  - `src/AGENTS.md` — path updates
- Add migration notes to `CHANGELOG.md`
- Remove legacy code (after 4-week deprecation period)

**Deliverables**:
- All docs updated
- `CHANGELOG.md` entry
- Migration guide for users

### Option B: Cut-over (Not Recommended)

**Timeline**: 1-2 weeks  
**Risk**: HIGH (breaks backward compatibility)  
**Approach**: All code switches at once

**Why not this**: 
- Users with existing sessions in `~/.copilot/queue/` lose access
- Scripts and integrations break immediately
- No fallback if new code has bugs
- Can't easily roll back

---

## Data Loss Prevention Strategy

### Pre-Migration Checklist

- [ ] Identify all sessions with active queue data
  ```bash
  find ~/.copilot/queue/ -type f -name "*.yaml" | wc -l
  ```

- [ ] Inventory session directories
  ```bash
  ls -la ~/.copilot/queue/
  ```

- [ ] Verify no in-flight DELEGATEs
  ```bash
  find ~/.copilot/queue/*/processing/ -type f -name "*.yaml"
  ```

### Safe Migration Process

1. **Week 1**: Deploy new code with fallback to old paths
2. **Week 2-3**: Collect metrics on new path adoption
3. **Week 3 end**: Announce 4-week deprecation period
4. **Week 7**: Remove old code fallback

### Data Recovery Procedures

If migration encounters issues:

```bash
# Step 1: Preserve all existing queue data
cp -r ~/.copilot/queue ~/.copilot/queue.backup.$(date +%Y%m%d-%H%M%S)

# Step 2: Verify isolation paths created
ls -la ~/.agentic-engineers/artifacts/

# Step 3: Manual migration of lost data (if needed)
for session_dir in ~/.copilot/queue/*/; do
  SESSION_ID=$(basename "$session_dir")
  rsync -av "$session_dir" ~/.agentic-engineers/artifacts/$SESSION_ID/local/queue/
done
```

### Validation Checkpoints

- [ ] Old paths still work (backward compatibility)
- [ ] New paths created and populated
- [ ] metadata.json generated correctly
- [ ] Zero data loss in migration
- [ ] Queue operations work from both paths
- [ ] Tests pass with 100% coverage

---

## Component-Level Code Changes

### 1. Orchestrator QueueManager

**File**: `src/orchestration/agents/orchestrator.py`

**Current State** (lines 45-75):
```python
def __init__(self, queue_dir: Optional[str] = None, agent_context: Optional[str] = None):
    self.session_id = os.environ.get("COPILOT_SESSION_ID") or "local"
    self.base_dir = Path.home() / ".copilot" / "queue"
    self.session_queue_dir = self.base_dir / self.session_id
    # ... rest of init
```

**Required Changes**:
1. Try to import `queue_isolation` (optional)
2. If available, use `queue-isolation` paths
3. Fall back to `~/.copilot/queue/` for backward compatibility
4. Initialize queue structure using isolation helpers

**Pseudo-code**:
```python
def __init__(self, queue_dir: Optional[str] = None, agent_context: Optional[str] = None):
    # 1. Try isolation first
    try:
        from src.skills._meta.queue_isolation.scripts import queue_isolation
        self.session_id = queue_isolation.get_session_id()
        harness = queue_isolation.detect_harness()
        queue_isolation.init_queue_structure(self.session_id, harness)
        queue_path = queue_isolation.get_queue_path(self.session_id, harness)
        self.base_dir = queue_path.parent.parent  # artifacts/
        self.session_queue_dir = queue_path
    except ImportError:
        # 2. Fall back to legacy paths
        self.session_id = os.environ.get("COPILOT_SESSION_ID") or "local"
        self.base_dir = Path.home() / ".copilot" / "queue"
        self.session_queue_dir = self.base_dir / self.session_id
    
    # 3. Initialize queue subdirectories
    self.incoming_dir = self.session_queue_dir / "incoming"
    self.processing_dir = self.session_queue_dir / "processing"
    self.done_dir = self.session_queue_dir / "done"
    for d in [self.incoming_dir, self.processing_dir, self.done_dir]:
        d.mkdir(parents=True, exist_ok=True)
```

**Impact**: HIGH — Controls all queue operations  
**Breakage**: None (backward compatible)  
**Tests affected**: All orchestration tests

### 2. Queue Manager CLI

**File**: `src/skills/queue-management/queue_manager.py`

**Current State** (lines 92-109):
```python
@staticmethod
def _get_default_queue_dir() -> str:
    qi = _try_import_queue_isolation()
    if qi is not None:
        # Use isolation paths
        ...
    # Fall back to legacy
    queue_base = os.path.expanduser("~/.copilot/queue")
    return os.path.join(queue_base, session_id, "incoming")
```

**Status**: ✅ ALREADY PREPARED  
- Skill already tries to import `queue-isolation`
- Falls back to legacy paths
- No changes needed! (already matches target)

### 3. Queue Operations Skill

**File**: `src/skills/queue-management/scripts/queue_ops.py`

**Current State** (line 18):
```python
_DEFAULT_QUEUE_PATH = "~/.agentic-engineers/artifacts"
```

**Status**: ✅ ALREADY CORRECT  
- Default path is already new target path
- No changes needed!

### 4. Tests

**Pattern**: Multiple test files use hardcoded paths

**Files affected**:
- `tests/test_orchestration/test_queue_*.py`
- `tests/test_skills/test_queue_management.py`
- `tests/conftest.py` (fixtures)

**Current pattern**:
```python
@pytest.fixture
def queue_dir(tmp_path):
    return tmp_path / ".copilot" / "queue" / "test-session"

def test_queue_operations(queue_dir):
    qm = QueueManager(str(queue_dir))
    # ...
```

**Required changes**:
```python
@pytest.fixture
def queue_isolation(monkeypatch, tmp_path):
    # Mock isolation paths
    from src.skills._meta.queue_isolation.scripts import queue_isolation as qi_module
    
    mock_session = "test-session-123"
    mock_harness = "local"
    qi = qi_module.QueueIsolation.from_env()
    qi._base_dir = tmp_path
    return qi

def test_queue_operations(queue_isolation):
    qm = QueueManager(str(queue_isolation.queue_path))
    # ...
```

---

## Risk Assessment

### Technical Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Path detection fails in CI/CD | MEDIUM | Provide explicit `AGENTIC_SESSION_ID` env var |
| Existing sessions orphaned | HIGH | Graceful fallback + migration script |
| Tests break during transition | MEDIUM | Run full test suite before cutover |
| Metadata.json creation fails | LOW | Permission check + mkdir fallback |

### Deployment Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| install-fresh wipes new paths | MEDIUM | Update Makefile to exclude ~/.agentic-engineers |
| Users on old code miss new features | LOW | Graceful degradation (fallback paths) |
| Harness collision in multi-harness env | LOW | Isolation enforced by design |

### Data Loss Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Queue data lost on migration | **CRITICAL** | Backup scripts + dual-path fallback |
| Incomplete migration leaves orphaned data | HIGH | Migration validator script |
| Archive cleanup deletes too much | MEDIUM | Retention policy enforcement |

---

## Implementation Timeline

```
WEEK 1-2: Foundation & Testing
┌─────────────────────────────────────┐
│ ✓ Verify queue-isolation (28 tests) │
│ ✓ Update orchestrator.py dual-path  │
│ ✓ Backward compatibility tests       │
└─────────────────────────────────────┘

WEEK 2: Skills & Documentation
┌──────────────────────────────────────┐
│ ✓ Verify queue_ops.py (already ok)  │
│ ✓ Update test fixtures               │
│ ✓ Docs: mark old paths as legacy    │
└──────────────────────────────────────┘

WEEK 3: Test Suite & Metrics
┌────────────────────────────────────────┐
│ ✓ Migrate all test fixtures            │
│ ✓ Multi-harness collision tests        │
│ ✓ Collect adoption metrics             │
└────────────────────────────────────────┘

WEEK 4: Documentation & Cleanup
┌──────────────────────────────────────┐
│ ✓ CHANGELOG.md + migration guide     │
│ ✓ Remove fallback code (after Week7) │
│ ✓ Final verification                 │
└──────────────────────────────────────┘
```

---

## Success Criteria

- [ ] **Zero data loss** during migration (validated with script)
- [ ] **All 28 queue-isolation tests passing**
- [ ] **100% test suite passing** (all orchestration + skills + integration)
- [ ] **Backward compatibility maintained** (old code still works Week 1-7)
- [ ] **Dual-path architecture documented** in code comments
- [ ] **Migration metrics collected** (adoption rate, fallback usage)
- [ ] **Production safety** — no regressions in queue operations
- [ ] **Documentation updated** across all 5 files
- [ ] **Ready for Engineers to execute** with confidence

---

## Dependencies & Prerequisites

### Already Complete ✅

- ✅ `queue-isolation` skill designed (SKILL.md)
- ✅ `queue_isolation.py` script implemented (100+ lines)
- ✅ 28 comprehensive tests written
- ✅ Fallback logic in `queue_manager.py`
- ✅ Default paths in `queue_ops.py` point to new location

### Required Before Implementation

- [ ] This design document approved
- [ ] Data loss mitigation scripts written
- [ ] Makefile reviewed (ensure install-fresh safe)
- [ ] Environment variable strategy finalized
- [ ] Rollback procedures documented

---

## Next Steps

### Approval Gate

**Review Checklist**:
- [ ] Architecture diagram makes sense
- [ ] Risk assessment acceptable
- [ ] Timeline realistic for team
- [ ] Data loss prevention sufficient
- [ ] Implementation plan complete

### Handoff to Engineering

Once approved, create DELEGATE blocks for each phase:

1. **Phase 1 DELEGATE** → Engineer (Foundation & backward compat)
2. **Phase 2 DELEGATE** → Engineer (Skills migration)
3. **Phase 3 DELEGATE** → Quality Engineer (Test suite)
4. **Phase 4 DELEGATE** → Lead Engineer (Docs & cutover)

---

## Appendix: File Reference Summary

### Source Files to Modify

```
src/orchestration/
├── agents/orchestrator.py                    ← HIGH: Dual-path logic
├── queue_manager.py                          ← HIGH: Fallback updates
├── agents/invoke_agent.py                    ← LOW: No direct changes
└── 15+ other agents                          ← NONE: Use manager

src/skills/
├── queue-management/queue_manager.py         ← DONE: Already prepared
├── queue-management/scripts/queue_ops.py     ← DONE: Already correct
└── _meta/queue-isolation/                    ← DONE: Fully implemented

tests/
├── test_orchestration/test_queue_*.py        ← MEDIUM: Update fixtures
├── test_skills/test_queue_management.py      ← MEDIUM: Update fixtures
└── conftest.py                               ← MEDIUM: New helpers

docs/
├── QUEUE-PROTOCOL.md                         ← MEDIUM: Path updates
├── artifacts/queue/SCHEMA.md                 ← MEDIUM: Path updates
├── src/AGENTS.md                             ← MEDIUM: Path updates
├── src/TODO.md.template                      ← MEDIUM: Path updates
└── ARCHITECTURE-QUEUE-UNIFIED.md             ← NEW: This doc

Build/Config:
├── Makefile                                  ← LOW: Verify safe
└── .gitignore                                ← NONE: Already excludes ~/.agentic-engineers/
```

### Estimated Token/Effort

| Component | Tokens | Effort | Parallelizable? |
|-----------|--------|--------|-----------------|
| Orchestrator (dual-path) | 2000 | 4h | No (foundation) |
| Queue manager updates | 800 | 2h | Yes (after phase 1) |
| Test fixture migration | 3000 | 6h | Yes (parallel) |
| Documentation updates | 1500 | 3h | Yes (parallel) |
| Validation & testing | 2000 | 4h | No (final gate) |
| **TOTAL** | **9300** | **19h** | 60% parallelizable |

---

**Document Version**: 1.0  
**Last Updated**: 2025-05-24  
**Author**: Principal Engineer  
**Status**: READY FOR REVIEW & IMPLEMENTATION
