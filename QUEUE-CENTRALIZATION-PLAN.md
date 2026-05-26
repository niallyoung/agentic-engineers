# Implementation Plan: Centralize Queue Infrastructure to ~/.agentic-engineers/

**Objective:** Remove legacy path fallback logic and enforce canonical queue path for ALL harnesses.

**Status:** PLANNING

---

## Current State Analysis

### 1. Code Structure
- **orchestrator.py** (lines 469-515): Contains "PHASE 2: Fallback to legacy paths" with full fallback logic
- **queue_compat.py**: Migration layer with docstring referencing "Phase 1-4" migration
- **artifact_manager.py**: Docstring only mentions "artifacts/" (already generic)
- **QUEUE-PROTOCOL.md**: References `~/.copilot/queue/` and `~/.claude/queue/`
- **5+ agent files**: Document paths inconsistently

### 2. Legacy Paths (To Remove)
- `~/.copilot/queue/`
- `~/.claude/queue/`
- `artifacts/queue/` (in active code)

### 3. Canonical Path (To Enforce)
- `~/.agentic-engineers/{session-id}/{harness}/queue/`

---

## Implementation Plan

### PHASE 1: Code Consolidation (15 minutes)

#### 1.1 - orchestrator.py (lines 469-515): Replace fallback logic
**File:** `src/orchestration/agents/orchestrator.py`

**Changes:**
- Remove lines 469-515 (entire "PHASE 2: Fallback to legacy paths" section)
- Replace with error-on-missing-isolation logic
- Update docstring (lines 424-432) to document canonical path
- Update module docstring (lines 1-11) to reference canonical path

**New code:**
```python
# ========================================================================
# PHASE 2: Enforce canonical queue path only
# ========================================================================
if not self._using_isolation:
    raise RuntimeError(
        "Canonical queue path is ~/.agentic-engineers/ for all harnesses. "
        "Legacy paths (~/.copilot/queue/, ~/.claude/queue/, artifacts/queue/) "
        "are NO LONGER SUPPORTED. Ensure queue-isolation skill is properly initialized."
    )
```

#### 1.2 - queue_compat.py: Mark as DEPRECATED
**File:** `src/orchestration/queue_compat.py`

**Changes:**
- Add DEPRECATED marker at top of file
- Update module docstring to indicate migration complete
- Keep file for historical reference only

**New docstring:**
```python
"""
[DEPRECATED] Backward Compatibility Layer for Queue Path Migration (Phase 1-4)

Legacy migration layer (Phase 1-4 completed 2026-05-26). Only for historical reference.
Only ~/.agentic-engineers/ is supported now. This file is kept for migration understanding only.

This module provided utilities for:
1. Detecting legacy queue paths (~/.copilot/queue/{session_id}/)
2. Validating queue path migration integrity (no data loss)
3. Providing migration status and diagnostics
"""
```

#### 1.3 - artifact_manager.py: Update docstring
**File:** `src/orchestration/agents/artifact_manager.py`

**Changes:**
- Update docstring (lines 1-7) to clarify artifacts now in ~/.agentic-engineers/

**New docstring:**
```python
"""
Artifact Manager - Read/Write DELEGATE/HANDBACK/FEEDBACK YAML blocks

Manages serialization of DELEGATE, HANDBACK, and FEEDBACK blocks to the
canonical artifacts directory: ~/.agentic-engineers/{session-id}/{harness}/
Supports date-keyed organization for historical archival.
"""
```

---

### PHASE 2: Documentation Consolidation (15 minutes)

#### 2.1 - docs/QUEUE-PROTOCOL.md
**File:** `docs/QUEUE-PROTOCOL.md`

**Changes:**
- Update line 5 canonical path reference
- Add new section "Queue Structure (All Harnesses)" after line 8
- Remove all legacy path references
- Add note about migration completion

**Old (line 5):**
```
**CANONICAL EXECUTION MODEL:** Orchestrator agent continuously polls `~/.copilot/queue/{session-id}/incoming/` (or `~/.claude/queue/` for Claude context)...
```

**New (line 5):**
```
**CANONICAL PATH:** ~/.agentic-engineers/{session-id}/{harness}/queue/ (same for all harnesses)

**CANONICAL EXECUTION MODEL:** Orchestrator agent continuously polls the canonical queue directory...
```

**New Section (after line 8):**
```markdown
## Queue Structure (All Harnesses)

As of 2026-05-26, ALL harnesses (Claude, Copilot, GPT, Local) use the same base directory:

```
~/.agentic-engineers/
├── {session-id}/
│   ├── claude/
│   │   └── queue/
│   │       ├── incoming/
│   │       ├── processing/
│   │       └── done/
│   ├── copilot/
│   │   └── queue/
│   │       ├── incoming/
│   │       ├── processing/
│   │       └── done/
│   ├── gpt/
│   │   └── queue/ ...
│   └── local/
│       └── queue/ ...
```
```

#### 2.2 - src/agents/orchestrator-agent.md
**File:** `src/agents/orchestrator-agent.md`

**Changes:**
- Search for "artifacts/queue/incoming" or "~/.copilot/queue" references
- Replace with "~/.agentic-engineers/{session-id}/{harness}/queue/incoming"

#### 2.3 - src/agents/orchestration-agents-README.md
**File:** `src/agents/orchestration-agents-README.md`

**Changes:**
- Find "Artifacts storage" or queue path section
- Update to document centralized path structure
- Remove harness-specific references

#### 2.4 - src/agents/model-engineer-agent.md
**File:** `src/agents/model-engineer-agent.md`

**Changes:**
- Update queue path references to use ~/.agentic-engineers/
- Ensure consistency with other agent files

#### 2.5 - src/skills/_meta/queue-isolation/SKILL.md
**File:** `src/skills/_meta/queue-isolation/SKILL.md`

**Changes:**
- Emphasize ~/.agentic-engineers/ is the ONLY supported path (line 33 already correct)
- Verify directory structure examples are clear per harness
- Add note: "All 4 harnesses use the same base directory"

---

### PHASE 3: Verification (20 minutes)

#### 3.1 - Grep checks for legacy paths
```bash
grep -r "\.copilot/queue" src/ --exclude-dir=_archive
grep -r "\.claude/queue" src/ --exclude-dir=_archive
grep -r "artifacts/queue" src/ --exclude-dir=_archive
```

**Success:** All should return ZERO matches in active code.

#### 3.2 - Test suite
```bash
pytest tests/ -q
```

**Expected:** 2,900+ tests passing

#### 3.3 - Manual verification
- Ensure orchestrator.py QueueManager.__init__ raises RuntimeError if queue_isolation unavailable
- Verify RuntimeError message is clear and helpful
- Check no stale comments referencing legacy paths

---

### PHASE 4: Git Commit (5 minutes)

**Commit message:**
```
refactor: centralize queue paths to ~/.agentic-engineers/ (all harnesses)

- Remove legacy path fallback logic from orchestrator.py (lines 469-515)
- Consolidate queue documentation across 5 files
- Ensure all 4 harnesses use canonical path: ~/.agentic-engineers/
- queue_compat.py marked DEPRECATED (migration Phase 1-4 complete)
- All tests pass (2,900+ tests)

Legacy paths NO LONGER SUPPORTED:
- ~/.copilot/queue/
- ~/.claude/queue/
- artifacts/queue/

Canonical path for all harnesses: ~/.agentic-engineers/{session-id}/{harness}/queue/
```

---

## Success Criteria (MUST VERIFY ALL)

- [ ] orchestrator.py raises RuntimeError if queue-isolation unavailable
- [ ] Module docstring updated to show canonical path
- [ ] queue_compat.py marked DEPRECATED
- [ ] All 5 documentation files updated consistently
- [ ] ZERO legacy path references in active src/ code
- [ ] All 2,900+ tests passing
- [ ] Code compiles and imports successfully
- [ ] One clean commit documenting consolidation

---

## Files to Change

### Code Files (3)
1. `src/orchestration/agents/orchestrator.py` (lines 1-11, 424-432, 469-515)
2. `src/orchestration/queue_compat.py` (top of file)
3. `src/orchestration/agents/artifact_manager.py` (lines 1-7)

### Documentation Files (5)
1. `docs/QUEUE-PROTOCOL.md` (line 5, add section after line 8)
2. `src/agents/orchestrator-agent.md` (search for path references)
3. `src/agents/orchestration-agents-README.md` (queue path section)
4. `src/agents/model-engineer-agent.md` (queue path references)
5. `src/skills/_meta/queue-isolation/SKILL.md` (verify clarity)

### Test Files (0)
No test changes needed; tests should verify behavior automatically.

---

## Estimated Effort

- Code changes: 15 minutes
- Documentation changes: 15 minutes
- Testing & verification: 20 minutes
- **Total: 50 minutes**

---

## Decision Log

**Why enforce immediately instead of gradual migration?**
- Phase 1-4 migration is complete (May 2026)
- Legacy paths are already marked for removal
- Queue-isolation is fully functional and required
- Enforcing improves clarity and prevents accidental use of legacy paths

**Why not deprecation warning first?**
- Already completed Phase 1-4 migration (soft deprecation)
- Clear error message will guide users to fix configuration
- Better than silent fallback which could hide problems

**Why keep queue_compat.py instead of deleting?**
- Historical reference for future migrations
- No harm keeping (it's not imported/used in active code)
- Provides implementation pattern for similar projects
