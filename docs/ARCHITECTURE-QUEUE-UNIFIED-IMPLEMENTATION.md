# Queue Path Unification: Implementation Plan

**Status**: DESIGN PHASE - Ready for Engineer Execution  
**Document**: Companion to ARCHITECTURE-QUEUE-UNIFIED.md  
**Audience**: Engineers implementing the migration  

---

## Phase 1: Foundation & Orchestrator (Week 1-2)

### Goal
Implement dual-path architecture in core orchestrator so new code uses `~/.agentic-engineers/` while maintaining backward compatibility with `~/.copilot/queue/`.

### Tasks

#### Task 1.1: Verify queue-isolation Skill (Engineer)
**File**: `src/skills/_meta/queue-isolation/`  
**Effort**: 1 hour  
**Checklist**:
```bash
# Run all 28 tests
python3 -m pytest src/skills/_meta/queue-isolation/tests/ -v

# Verify coverage
python3 -m pytest src/skills/_meta/queue-isolation/tests/ --cov --cov-report=term-missing

# Expected: 100% coverage, all 28 tests passing
```

**Deliverable**: Test output showing ✅ all passing

---

#### Task 1.2: Update Orchestrator QueueManager (Engineer)
**File**: `src/orchestration/agents/orchestrator.py`  
**Effort**: 4 hours  
**Complexity**: HIGH (affects all queue operations)

**Current Implementation** (lines 45-120):
```python
def __init__(self, queue_dir: Optional[str] = None, agent_context: Optional[str] = None):
    self.session_id = os.environ.get("COPILOT_SESSION_ID") or \
                      os.environ.get("CLAUDE_SESSION_ID") or "local"
    self.agent_context = agent_context
    
    # Determine base queue directory based on environment
    if queue_dir:
        base_queue_dir = Path(queue_dir).expanduser()
    else:
        # Auto-detect based on available env vars
        if self.agent_context == "claude":
            claude_queue = Path.home() / ".claude" / "queue"
            if claude_queue.exists():
                base_queue_dir = claude_queue
            else:
                repo_queue = Path.cwd() / ".queue"
                base_queue_dir = repo_queue if repo_queue.exists() else claude_queue
        elif self.agent_context == "copilot":
            copilot_queue = Path.home() / ".copilot" / "queue"
            base_queue_dir = copilot_queue
        else:
            base_queue_dir = Path.home() / ".copilot" / "queue"
    
    self.base_dir = base_queue_dir
    self.session_queue_dir = self.base_dir / self.session_id
    self.incoming_dir = self.session_queue_dir / "incoming"
    self.processing_dir = self.session_queue_dir / "processing"
    self.done_dir = self.session_queue_dir / "done"
    
    # Ensure directories exist
    for d in [self.incoming_dir, self.processing_dir, self.done_dir]:
        d.mkdir(parents=True, exist_ok=True)
```

**Required Changes**:

1. **Add queue-isolation import at top of file**:
```python
def _try_import_queue_isolation():
    """Attempt to import queue_isolation; return module or None on failure."""
    try:
        from src.skills._meta.queue_isolation.scripts import queue_isolation as qi
        return qi
    except ImportError:
        return None

# At module level
_QUEUE_ISOLATION = _try_import_queue_isolation()
```

2. **Update `__init__` to use isolation first**:
```python
def __init__(self, queue_dir: Optional[str] = None, agent_context: Optional[str] = None):
    self.agent_context = agent_context
    
    # ========== PHASE 1: Try queue-isolation (new) ==========
    if _QUEUE_ISOLATION is not None:
        try:
            self.session_id = _QUEUE_ISOLATION.get_session_id()
            harness = _QUEUE_ISOLATION.detect_harness()
            
            # Initialize queue structure (idempotent)
            _QUEUE_ISOLATION.init_queue_structure(self.session_id, harness)
            
            # Get queue path from isolation
            queue_root = _QUEUE_ISOLATION.get_queue_path(self.session_id, harness)
            self.base_dir = queue_root.parent.parent  # artifacts/
            self.session_queue_dir = queue_root
            self._using_isolation = True
        except Exception as e:
            logger.warning(f"queue-isolation failed, falling back to legacy: {e}")
            self._using_isolation = False
            # Fall through to legacy code below
    else:
        self._using_isolation = False
    
    # ========== PHASE 2: Fallback to legacy paths ==========
    if not self._using_isolation:
        self.session_id = os.environ.get("COPILOT_SESSION_ID") or \
                          os.environ.get("CLAUDE_SESSION_ID") or "local"
        
        if queue_dir:
            base_queue_dir = Path(queue_dir).expanduser()
        else:
            # Auto-detect based on available env vars (existing logic)
            if self.agent_context == "claude":
                base_queue_dir = Path.home() / ".claude" / "queue"
            elif self.agent_context == "copilot":
                base_queue_dir = Path.home() / ".copilot" / "queue"
            else:
                base_queue_dir = Path.home() / ".copilot" / "queue"
        
        self.base_dir = base_queue_dir
        self.session_queue_dir = self.base_dir / self.session_id
    
    # Initialize queue subdirectories (same for both paths)
    self.incoming_dir = self.session_queue_dir / "incoming"
    self.processing_dir = self.session_queue_dir / "processing"
    self.done_dir = self.session_queue_dir / "done"
    
    for d in [self.incoming_dir, self.processing_dir, self.done_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"QueueManager initialized: {self.session_queue_dir} "
                f"(session={self.session_id}, using_isolation={self._using_isolation})")
```

**Testing**:
- Run existing queue tests (should all pass)
- Add new test: isolation path preferred when available
- Add new test: fallback to legacy when isolation unavailable
- Add new test: dual-path compatibility

**Verification**:
```bash
# Verify isolation is used when available
AGENTIC_SESSION_ID=test-session-123 python3 -c "
from src.orchestration.agents.orchestrator import QueueManager
qm = QueueManager()
print(f'Session: {qm.session_id}')
print(f'Queue dir: {qm.session_queue_dir}')
assert '.agentic-engineers' in str(qm.session_queue_dir)
"

# Verify fallback when isolation unavailable
COPILOT_SESSION_ID=test-session-456 python3 -c "
from src.orchestration.agents.orchestrator import QueueManager
qm = QueueManager()
print(f'Session: {qm.session_id}')
print(f'Queue dir: {qm.session_queue_dir}')
"
```

---

#### Task 1.3: Verify ExtendedQueueManager (Engineer)
**File**: `src/orchestration/queue_manager.py`  
**Effort**: 1 hour  
**Checklist**:
- Verify it inherits from updated QueueManager
- Test `move_to_failed()` method works with both paths
- Run existing tests

**Code Review** (lines 48-52):
```python
class ExtendedQueueManager(QueueManager):
    def __init__(self, queue_dir: Optional[str] = None, agent_context: Optional[str] = None):
        super().__init__(queue_dir=queue_dir, agent_context=agent_context)
        # This will now use either isolation or legacy path automatically
        self.failed_dir = self.session_queue_dir / "failed"
        self.failed_dir.mkdir(parents=True, exist_ok=True)
```

✅ **No changes needed** — inherits dual-path behavior from parent

---

#### Task 1.4: Run Orchestration Tests (Quality Engineer)
**Effort**: 2 hours  
**Checklist**:
```bash
# Run all orchestration queue tests
python3 -m pytest tests/test_orchestration/ -v -k queue

# Run full orchestration suite
python3 -m pytest tests/test_orchestration/ -v

# Expected: 100% passing (backward compatibility maintained)
```

**Verification**: All tests pass, no regressions

---

### Phase 1 Deliverables

- ✅ `src/orchestration/agents/orchestrator.py` — dual-path logic
- ✅ All orchestration tests passing
- ✅ Backward compatibility verified
- ✅ Ready for Phase 2

---

## Phase 2: Skills & Documentation (Week 2)

### Goal
Update queue management skill and mark legacy paths as deprecated in docs.

### Tasks

#### Task 2.1: Verify Queue Operations Skill (Engineer)
**File**: `src/skills/queue-management/scripts/queue_ops.py`  
**Effort**: 1 hour

**Current State** (line 18):
```python
_DEFAULT_QUEUE_PATH = "~/.agentic-engineers/artifacts"
```

✅ **Already correct!** No changes needed.

**Verification**:
```bash
# Check default path
grep _DEFAULT_QUEUE_PATH src/skills/queue-management/scripts/queue_ops.py

# Run skill tests
python3 -m pytest src/skills/queue-management/tests/test_queue_ops.py -v
```

---

#### Task 2.2: Verify Queue Management CLI (Engineer)
**File**: `src/skills/queue-management/queue_manager.py`  
**Effort**: 1 hour

**Current State** (lines 92-99):
```python
@staticmethod
def _get_default_queue_dir() -> str:
    qi = _try_import_queue_isolation()
    if qi is not None:
        session_id = qi.get_session_id()
        harness = qi.detect_harness()
        queue_root = qi.get_queue_path(session_id, harness)
        qi.init_queue_structure(session_id, harness)
        return str(queue_root / "incoming")
    
    # Fall back to legacy
    queue_base = os.path.expanduser("~/.copilot/queue")
    return os.path.join(queue_base, session_id, "incoming")
```

✅ **Already prepared!** Already uses isolation with fallback.

**Verification**:
```bash
# Test queue manager CLI
python3 -m pytest src/skills/queue-management/tests/test_queue_*.py -v
```

---

#### Task 2.3: Update Documentation - Part 1 (Senior Engineer)
**Files**:
- `docs/QUEUE-PROTOCOL.md` — Add dual-path section
- `artifacts/queue/SCHEMA.md` — Add deprecation notice
- `src/AGENTS.md` — Update path references
- `src/TODO.md.template` — Update path references

**Effort**: 2 hours

**Changes for each file**:

**docs/QUEUE-PROTOCOL.md** — Add section at top:
```markdown
> **⚠️ PATH MIGRATION**: Session artifacts are transitioning from `~/.copilot/queue/` 
> to `~/.agentic-engineers/artifacts/{session-id}/{harness}/queue/`.
> 
> Both paths work during migration (Phase 1-4, weeks 1-4).
> After week 4, only the new path will be supported.
> See [Migration Guide](./ARCHITECTURE-QUEUE-UNIFIED.md) for details.
```

**artifacts/queue/SCHEMA.md** — Replace all instances:
- `~/.copilot/queue/{session-id}/` → `~/.agentic-engineers/artifacts/{session-id}/{harness}/queue/`
- Add note: "(legacy: `~/.copilot/queue/{session-id}/`)"

**src/AGENTS.md** — Update queue examples:
```markdown
- Queue location: `~/.agentic-engineers/artifacts/{session-id}/{harness}/queue/incoming/`
  (legacy: `~/.copilot/queue/{session-id}/incoming/`)
```

**src/TODO.md.template** — Update path examples

---

#### Task 2.4: Update Skill Documentation (Engineer)
**Files**:
- `src/skills/queue-management/SKILL.md` — Document dual-path behavior
- `src/skills/_meta/queue-isolation/SKILL.md` — Highlight as primary path

**Effort**: 1 hour

**Change**: Add section to queue-management SKILL.md:
```markdown
## Path Architecture

### Phase 1 (During Migration)
- **Preferred path**: `~/.agentic-engineers/artifacts/{session}/{harness}/queue/`
  (created automatically by queue-isolation)
- **Fallback path**: `~/.copilot/queue/{session}/` (legacy, for backward compatibility)

### Phase 2 (After Migration)
- **Only path**: `~/.agentic-engineers/artifacts/{session}/{harness}/queue/`
```

---

### Phase 2 Deliverables

- ✅ Skills verified (already correct)
- ✅ Documentation updated with dual-path notices
- ✅ Deprecation timeline communicated
- ✅ Ready for Phase 3

---

## Phase 3: Test Suite Migration (Week 3)

### Goal
Update all test fixtures to use queue-isolation instead of hardcoded paths.

### Tasks

#### Task 3.1: Audit All Queue Tests (Quality Engineer)
**Effort**: 2 hours

**Find all queue-related tests**:
```bash
find tests/ -name "*queue*.py" -o -name "test_orchestration.py"
```

**Files to update**:
- `tests/test_orchestration/test_queue_*.py`
- `tests/test_orchestration/test_delegate_*.py`
- `tests/test_skills/test_queue_management.py`
- `tests/conftest.py` — add queue fixtures

---

#### Task 3.2: Create Test Helpers (Engineer)
**File**: `tests/helpers/queue_test_helpers.py` (new)  
**Effort**: 2 hours

```python
"""Test helpers for queue isolation during migration."""

import os
from pathlib import Path
from unittest.mock import patch
import tempfile
from typing import Generator, Tuple

def setup_isolated_queue(
    tmp_path: Path,
    session_id: str = "test-session",
    harness: str = "local"
) -> Path:
    """
    Set up an isolated queue structure for testing.
    
    Returns the queue root path: tmp_path/.agentic-engineers/artifacts/{session}/{harness}/queue/
    """
    from src.skills._meta.queue_isolation.scripts import queue_isolation
    
    # Mock HOME to use tmp_path
    with patch.dict(os.environ, {"HOME": str(tmp_path)}):
        qi = queue_isolation.QueueIsolation(
            session_id=session_id,
            harness=harness,
            base_dir=tmp_path / ".agentic-engineers"
        )
        qi.initialise()
        return qi.queue_path


@pytest.fixture
def isolated_queue_env(tmp_path: Path) -> Generator[Tuple[Path, dict], None, None]:
    """Fixture providing isolated queue with env vars for testing."""
    session_id = "test-session-" + str(uuid.uuid4())[:8]
    
    queue_path = setup_isolated_queue(tmp_path, session_id, "local")
    
    env_vars = {
        "AGENTIC_SESSION_ID": session_id,
        "AGENTIC_HARNESS": "local",
        "HOME": str(tmp_path),
    }
    
    with patch.dict(os.environ, env_vars):
        yield queue_path, env_vars


@pytest.fixture
def legacy_queue_env(tmp_path: Path) -> Generator[Tuple[Path, dict], None, None]:
    """Fixture providing legacy queue path for backward compatibility tests."""
    session_id = "test-session-" + str(uuid.uuid4())[:8]
    
    legacy_path = tmp_path / ".copilot" / "queue" / session_id
    legacy_path.mkdir(parents=True, exist_ok=True)
    (legacy_path / "incoming").mkdir(exist_ok=True)
    (legacy_path / "processing").mkdir(exist_ok=True)
    (legacy_path / "done").mkdir(exist_ok=True)
    
    env_vars = {
        "COPILOT_SESSION_ID": session_id,
        "HOME": str(tmp_path),
    }
    
    with patch.dict(os.environ, env_vars):
        yield legacy_path, env_vars
```

---

#### Task 3.3: Migrate Test Fixtures (Quality Engineer)
**Effort**: 4 hours

**Pattern for each test file**:

**Before**:
```python
import pytest
from pathlib import Path

@pytest.fixture
def queue_dir(tmp_path):
    queue_path = tmp_path / ".copilot" / "queue" / "test-session"
    queue_path.mkdir(parents=True, exist_ok=True)
    return queue_path

def test_queue_operations(queue_dir):
    from src.orchestration.queue_manager import QueueManager
    qm = QueueManager(str(queue_dir))
    # test code
```

**After**:
```python
import pytest
from pathlib import Path
from tests.helpers.queue_test_helpers import isolated_queue_env

def test_queue_operations_isolated(isolated_queue_env):
    queue_path, env_vars = isolated_queue_env
    from src.orchestration.queue_manager import QueueManager
    qm = QueueManager()  # No path needed — auto-detects from env
    assert str(queue_path) == str(qm.session_queue_dir)
    # test code

def test_queue_operations_legacy(legacy_queue_env):
    legacy_path, env_vars = legacy_queue_env
    from src.orchestration.queue_manager import QueueManager
    qm = QueueManager()  # Falls back to legacy
    assert str(legacy_path) == str(qm.session_queue_dir)
    # test code
```

**Files to update** (in order):
1. `tests/conftest.py` — Add helpers and fixtures
2. `tests/test_orchestration/test_queue_*.py` — Migrate fixtures (4-5 files)
3. `tests/test_skills/test_queue_management.py` — Migrate fixtures
4. Integration tests — Update as needed

---

#### Task 3.4: Add Multi-Harness Collision Tests (Quality Engineer)
**File**: `tests/test_orchestration/test_queue_isolation.py` (new)  
**Effort**: 2 hours

```python
"""Test multi-harness queue isolation."""

import pytest
from src.orchestration.agents.orchestrator import QueueManager


def test_multi_harness_isolation(tmp_path, monkeypatch):
    """Verify Claude and Copilot queues don't collide."""
    monkeypatch.setenv("HOME", str(tmp_path))
    
    # Create Claude queue
    monkeypatch.setenv("AGENTIC_SESSION_ID", "test-123")
    monkeypatch.setenv("AGENTIC_HARNESS", "claude")
    qm_claude = QueueManager()
    
    # Create Copilot queue
    monkeypatch.setenv("AGENTIC_HARNESS", "copilot")
    qm_copilot = QueueManager()
    
    # Verify they're different
    assert qm_claude.session_queue_dir != qm_copilot.session_queue_dir
    assert "claude" in str(qm_claude.session_queue_dir)
    assert "copilot" in str(qm_copilot.session_queue_dir)


def test_isolated_queue_persists(tmp_path, monkeypatch):
    """Verify queue data persists across operations."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AGENTIC_SESSION_ID", "test-persist")
    
    # Create queue and add file
    qm1 = QueueManager()
    test_file = qm1.incoming_dir / "test-task.yaml"
    test_file.write_text("test content")
    
    # Recreate queue (should find same path)
    qm2 = QueueManager()
    assert (qm2.incoming_dir / "test-task.yaml").read_text() == "test content"
```

---

#### Task 3.5: Run Full Test Suite (Quality Engineer)
**Effort**: 1 hour

**Comprehensive testing**:
```bash
# Run ALL tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov --cov-report=term-missing

# Run specific suites
python3 -m pytest tests/test_orchestration/ -v
python3 -m pytest tests/test_skills/test_queue_management.py -v

# Expected: 100% passing, no regressions
```

---

### Phase 3 Deliverables

- ✅ Test helpers created and documented
- ✅ All test fixtures migrated to isolation
- ✅ Multi-harness collision tests added
- ✅ 100% test suite passing
- ✅ Ready for Phase 4

---

## Phase 4: Documentation & Cutover (Week 4)

### Goal
Complete documentation, announce deprecation, and prepare for legacy code removal.

### Tasks

#### Task 4.1: Finalize Architecture Document (Senior Engineer)
**Effort**: 1 hour
- Review this implementation plan
- Add execution notes (decisions, gotchas, metrics)
- Publish in docs/

---

#### Task 4.2: Update CHANGELOG (Senior Engineer)
**Effort**: 30 minutes

**Entry**:
```markdown
## [Unreleased]

### Added
- Queue path unification: session artifacts now stored in `~/.agentic-engineers/`
- Multi-harness queue isolation: Claude, Copilot, GPT, and local agents use separate queues
- `queue-isolation` skill for automatic path detection and initialization
- New environment variables: `AGENTIC_SESSION_ID`, `AGENTIC_HARNESS` for explicit control

### Changed
- **BREAKING** (Phase 2): Legacy `~/.copilot/queue/` paths no longer supported after week 4
- Queue manager now prefers isolation-based paths with automatic fallback during migration
- All queue subdirectories created in `~/.agentic-engineers/artifacts/{session}/{harness}/queue/`

### Deprecated
- `~/.copilot/queue/` — Use `~/.agentic-engineers/artifacts/` instead (will be removed week 4)
- Legacy path detection — Use `AGENTIC_SESSION_ID` and `AGENTIC_HARNESS` for explicit control

### Migration Guide
See [Queue Path Unification](./ARCHITECTURE-QUEUE-UNIFIED.md) for migration instructions.
```

---

#### Task 4.3: Create Migration Guide (Lead Engineer)
**File**: `docs/MIGRATION-GUIDE-QUEUE-PATHS.md` (new)  
**Effort**: 2 hours

```markdown
# Queue Path Migration Guide

## For End Users

### What's Changing?

Session queue data is moving from:
- Old: `~/.copilot/queue/{session-id}/`
- New: `~/.agentic-engineers/artifacts/{session-id}/{harness}/queue/`

### What You Need to Do

**Nothing!** The migration is automatic:

1. Install updated code (Week 1-4)
2. Your existing queue data is preserved (fallback logic)
3. New queue operations use the new path automatically
4. After week 4, old paths no longer work (deploy final code)

### Timeline

| Date | Event | Action |
|------|-------|--------|
| Week 1 | Code deployed with dual-path support | No action needed |
| Week 2 | Documentation updated | Review new paths (optional) |
| Week 3 | Test suite migrated | No action needed |
| Week 4 | Legacy paths deprecated | Ensure you've updated custom scripts |
| Week 7 | Old code removed | **Last chance to migrate** |

### Troubleshooting

**Q: My queue data disappeared!**
A: Check `~/.copilot/queue/` for data. If found, it was preserved. The system automatically uses the old path as fallback.

**Q: How do I force a specific harness?**
A: Set `AGENTIC_HARNESS`:
```bash
AGENTIC_HARNESS=claude python3 my_script.py
```

## For Developers

### Environment Variables

Three new variables control queue behavior:

```bash
# Force specific session ID (otherwise auto-detected from CLAUDE_SESSION_ID, etc.)
export AGENTIC_SESSION_ID="my-session-123"

# Force specific harness (otherwise auto-detected from env)
export AGENTIC_HARNESS="copilot"  # claude|copilot|gpt|local

# These variables are already honored:
export CLAUDE_SESSION_ID="..."    # Anthropic harness
export COPILOT_SESSION_ID="..."   # GitHub Copilot
export OPENAI_API_KEY="..."       # GPT harness
```

### Accessing Queue Paths Programmatically

**Old way** (deprecated):
```python
queue_dir = Path.home() / ".copilot" / "queue" / session_id
```

**New way**:
```python
from src.skills._meta.queue_isolation.scripts import queue_isolation

session_id = queue_isolation.get_session_id()
harness = queue_isolation.detect_harness()
queue_path = queue_isolation.get_queue_path(session_id, harness)
```

### Testing Your Code

Use the new test fixtures:

```python
def test_my_feature(isolated_queue_env):
    queue_path, env_vars = isolated_queue_env
    # Your test code here
    # env_vars automatically set, queue_path created
```

## For DevOps / Platform Teams

### Updated Makefile Targets

No changes to `make install-fresh`. The new queue paths are excluded from backup:

```bash
make install-fresh  # Safe — doesn't wipe ~/.agentic-engineers/
```

If you have custom scripts that reference queue paths, update them:

```bash
# Old:
find ~/.copilot/queue/ -name "*.yaml"

# New:
find ~/.agentic-engineers/artifacts/ -name "*.yaml"
```

### Backup Strategy

During migration (weeks 1-4), back up both locations:

```bash
# Old path (may contain in-flight tasks)
tar czf queue-backup-legacy-$(date +%Y%m%d).tar.gz ~/.copilot/queue/

# New path (primary location)
tar czf queue-backup-new-$(date +%Y%m%d).tar.gz ~/.agentic-engineers/artifacts/
```

After week 7, only back up new path:

```bash
tar czf queue-backup-$(date +%Y%m%d).tar.gz ~/.agentic-engineers/artifacts/
```
```

---

#### Task 4.4: Deploy Cutover Announcement (Lead Engineer)
**Effort**: 1 hour
- Post to team channel: "Week 1 cutover complete, metrics attached"
- Share adoption metrics (what % using new paths)
- Link to migration guide

---

#### Task 4.5: Metrics Collection & Reporting (Metrics Engineer)
**Effort**: 2 hours

**Metrics to collect**:
- % of queue operations using new path vs fallback
- Errors during path detection
- Test suite performance (before vs after)
- User adoption timeline

**Collection method**:
```python
# Add to QueueManager.__init__
logger.info(f"queue_manager_path={'isolation' if self._using_isolation else 'legacy'}",
            extra={
                'session_id': self.session_id,
                'harness': getattr(self, 'harness', 'unknown'),
                'path': str(self.session_queue_dir),
            })
```

**Report**: Metrics dashboard showing adoption curve

---

### Phase 4 Deliverables

- ✅ Architecture document complete
- ✅ CHANGELOG updated
- ✅ Migration guide published
- ✅ Cutover announced to team
- ✅ Metrics collected and reported
- ✅ **Ready for final code cleanup (Week 5+)**

---

## Week 5-7: Post-Deployment Monitoring

### Continuous Checks

**Daily** (automated):
- Monitor error rates for path detection
- Check queue operations latency
- Alert if fallback usage > 5%

**Weekly**:
- Review adoption metrics
- Check for edge cases or collisions
- Gather user feedback

### Final Cleanup (Week 7)

Once fallback usage drops to near-zero:

1. Remove legacy path code from `orchestrator.py`
2. Remove fallback from `queue_manager.py`
3. Update documentation to remove migration notices
4. Tag release as `v5.11.0` (major version bump due to breaking change)

---

## Success Metrics

| Metric | Target | Acceptable |
|--------|--------|-----------|
| Test pass rate | 100% | ≥98% |
| Adoption rate (week 4) | >90% | ≥80% |
| Error rate on path detection | <0.1% | <1% |
| Data loss incidents | 0 | ≤1 |
| Backward compatibility issues | 0 | ≤2 |

---

## Rollback Plan

If critical issues found during Phase 1-2:

1. **Revert changes** to `orchestrator.py` and `queue_manager.py`
2. **Keep documentation updates** (useful for future attempt)
3. **Investigate** root cause (1-2 days)
4. **Restart** Phase 1 with fixes

If issues found during Phase 3-4:

1. **Pause** test suite migration
2. **Keep** rolled-back main code
3. **Fix** identified issues
4. **Resume** migration

**No data loss** in either scenario (fallback logic always available)

---

## Dependencies

**Before starting**:
- ✅ `queue-isolation` skill fully tested (28 tests)
- ✅ This implementation plan approved
- ✅ Team understands phased approach
- ✅ Metrics collection setup ready

**Required tools**:
- Git (for commits)
- pytest (for testing)
- Python 3.7+ (for imports)
- Bash (for verification scripts)

---

**Implementation Document Version**: 1.0  
**Last Updated**: 2025-05-24  
**Ready for Engineering**: YES
