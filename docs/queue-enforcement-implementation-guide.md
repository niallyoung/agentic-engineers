# Queue Enforcement Middleware: Implementation Roadmap
## Task 5101: Step-by-Step Implementation Guide

**For:** Engineer agents tasked with implementing queue enforcement  
**Based On:** Architecture design in `docs/architecture-queue-enforcement-5101.md`  
**Timeline:** 3 weeks  

---

## Phase 1: Core Enforcement Layer (3-4 days)

### Step 1.1: Create `orchestration/agents/queue_enforcement.py`

This file contains all the core enforcement machinery. Create new file with complete `QueueContext`, `QueueContextManager`, `QueueEnforcementError`, and `QueueEnforcingProxy` classes.

**Implementation checklist:**
- [ ] `QueueContext` singleton class (thread-safe context tracking)
- [ ] `QueueContextManager` context manager
- [ ] `QueueEnforcementError` exception class
- [ ] `QueueEnforcingProxy` wrapper class
- [ ] All docstrings complete
- [ ] Type hints on all methods

**Key requirements:**
- Thread-local context tracking (use `threading.local()`)
- Clear error messages with fix instructions
- Transparent attribute forwarding via `__getattr__`
- Minimal performance overhead (single flag check)

**Tests to write:**
- `test_queue_context_activate_deactivate()`: Context state changes
- `test_queue_context_is_active_default_false()`: Default state
- `test_queue_context_thread_isolation()`: Contexts don't leak between threads
- `test_queue_context_manager_enter_exit()`: Context manager works
- `test_proxy_execute_succeeds_in_queue_context()`: execute() works when active
- `test_proxy_execute_fails_outside_context()`: execute() raises QueueEnforcementError
- `test_proxy_attribute_forwarding()`: Other methods/attributes pass through
- `test_proxy_repr()`: String representation works

**File size estimate:** ~250 lines (including docstrings and type hints)

---

### Step 1.2: Update `orchestration/agents/implementations.py`

Modify the `create_agent()` factory function to use queue enforcement.

**Changes needed (around line 376-399):**

**Before:**
```python
def create_agent(role):
    """Create an agent instance."""
    if role not in AGENTS:
        raise ValueError(f"Unknown role: {role}")
    agent_class = AGENTS[role]
    return agent_class()
```

**After:**
```python
def create_agent(role, _test_context=False):
    """
    Create an agent instance with queue enforcement.
    
    Args:
        role: Agent role name (e.g., "engineer", "orchestrator")
        _test_context: Internal flag for test harnesses (do not use in production)
    
    Returns:
        QueueEnforcingProxy-wrapped agent instance
    
    Raises:
        QueueEnforcementError: If called outside queue context and not in test
        ValueError: If role is unknown
    """
    from .queue_enforcement import QueueContext, QueueEnforcementError, QueueEnforcingProxy
    
    # Validate role
    if role not in AGENTS:
        raise ValueError(
            f"Unknown agent role '{role}'. Valid roles: {', '.join(AGENTS.keys())}"
        )
    
    # Check queue context (unless explicitly testing)
    if not _test_context and not QueueContext.is_active():
        raise QueueEnforcementError(
            f"create_agent('{role}') called outside queue context. "
            f"Route through Orchestrator.queue.enqueue() instead of direct execution."
        )
    
    # Instantiate agent
    agent_class = AGENTS[role]
    agent = agent_class()
    
    # Wrap with enforcement proxy
    return QueueEnforcingProxy(agent, role)
```

**Implementation checklist:**
- [ ] Import enforcement classes at top of function
- [ ] Keep role validation logic
- [ ] Add queue context check
- [ ] Wrap return in QueueEnforcingProxy
- [ ] Update docstring with queue requirement
- [ ] Add type hints

**Tests to write:**
- `test_create_agent_unknown_role()`: ValueError on bad role
- `test_create_agent_outside_context()`: QueueEnforcementError when not in queue
- `test_create_agent_inside_context()`: Succeeds when queue context active
- `test_create_agent_returns_proxy()`: Returns QueueEnforcingProxy instance
- `test_create_agent_all_roles()`: Works for all 14 agent roles

**Lines modified:** ~10 lines changed, ~5 lines added

---

### Step 1.3: Update `orchestration/agents/__init__.py`

Export the new enforcement classes so they can be imported by test code and orchestrator.

**Changes needed (around exports section, line 240-260):**

**Add to exports:**
```python
from .queue_enforcement import (
    QueueContext,
    QueueContextManager,
    QueueEnforcementError,
    QueueEnforcingProxy,
)

__all__ = [
    # ... existing exports ...
    "QueueContext",
    "QueueContextManager", 
    "QueueEnforcementError",
    "QueueEnforcingProxy",
]
```

**Implementation checklist:**
- [ ] Import all enforcement classes
- [ ] Add to `__all__` list
- [ ] Verify imports work with `from orchestration.agents import QueueContext`

**Tests to write:**
- `test_enforcement_classes_importable()`: Can import from orchestration.agents

**Lines modified:** ~10 lines

---

### Step 1.4: Update `orchestration/agents/orchestrator.py`

Activate queue context when processing tasks.

**Changes needed (in `do_work()` method):**

**Before:**
```python
def do_work(self, work_item):
    """Poll and process queue tasks."""
    while True:
        task = self.queue.dequeue()
        agent = create_agent(task.route)
        result = agent.execute(task)
        yield result
```

**After:**
```python
def do_work(self, work_item):
    """Poll and process queue tasks."""
    from .queue_enforcement import QueueContextManager
    
    with QueueContextManager():
        while True:
            task = self.queue.dequeue()
            agent = create_agent(task.route)
            result = agent.execute(task)
            yield result
```

**Implementation checklist:**
- [ ] Import QueueContextManager
- [ ] Wrap task processing loop with context manager
- [ ] Verify orchestrator still works end-to-end

**Tests to write:**
- `test_orchestrator_activates_queue_context()`: Context is active during processing
- `test_orchestrator_can_create_agents()`: create_agent() succeeds in orchestrator context

**Lines modified:** ~5 lines changed, ~1 import added

---

### Phase 1 Success Criteria
- [ ] All 3 new files/modifications in place
- [ ] All Phase 1 unit tests pass
- [ ] No regressions in existing tests
- [ ] Code review approved

**Estimated time:** 3-4 days

---

## Phase 2: Test Harness Updates (2-3 days)

### Step 2.1: Update `orchestration/agents/testing_harness.py`

Add context management to all test functions that create agents.

**Pattern to apply to every test:**

**Before:**
```python
def test_engineer_basic():
    engineer = create_agent("engineer")
    result = engineer.execute(work_item)
    assert result.success
```

**After:**
```python
def test_engineer_basic():
    from orchestration.agents import QueueContextManager
    
    with QueueContextManager():
        engineer = create_agent("engineer")
        result = engineer.execute(work_item)
        assert result.success
```

**Implementation checklist:**
- [ ] Identify all test functions that call `create_agent()`
- [ ] Wrap each in `with QueueContextManager():`
- [ ] Run tests to verify they pass
- [ ] Check for any test setup/teardown that should also use context

**Tests affected:** Likely 15-30 test functions

**Lines modified:** ~2 lines per test function (opening and closing context manager)

---

### Step 2.2: Update `orchestration/agents/example_end_to_end.py`

Apply same pattern to example code.

**Before:**
```python
def main():
    orchestrator = create_agent("orchestrator")
    results = orchestrator.execute(work_items)
```

**After:**
```python
def main():
    from orchestration.agents import QueueContextManager
    
    with QueueContextManager():
        orchestrator = create_agent("orchestrator")
        results = orchestrator.execute(work_items)
```

**Implementation checklist:**
- [ ] Add context manager imports
- [ ] Wrap all create_agent() calls
- [ ] Verify example still runs end-to-end
- [ ] Example should produce same results as before

**Tests to write:**
- Manual test: Run example_end_to_end.py and verify output

---

### Step 2.3: Find and Update All Other Test Files

Search for other files that use `create_agent()`.

**Command to find candidates:**
```bash
grep -r "create_agent(" orchestration/agents/ --include="*.py" | grep -v "def create_agent" | grep -v ".pyc"
```

**Likely candidates:**
- `orchestration/agents/workflow.py` (if exists)
- `orchestration/agents/test_*.py` (any test files)
- Integration test files

**For each file found:**
- [ ] Add import: `from orchestration.agents import QueueContextManager`
- [ ] Wrap agent creation blocks in context manager
- [ ] Run tests to verify
- [ ] No behavior changes (just context management added)

**Implementation checklist:**
- [ ] Search complete
- [ ] All files updated
- [ ] All tests pass
- [ ] No regressions

**Estimated files:** 3-5 additional files

---

### Phase 2 Success Criteria
- [ ] All test files use QueueContextManager
- [ ] All tests pass
- [ ] Examples run without errors
- [ ] No behavior changes (only context management added)

**Estimated time:** 2-3 days

---

## Phase 3: Integration Testing (2 days)

### Step 3.1: Write Queue Enforcement Integration Tests

Create `orchestration/agents/test_queue_enforcement.py` with integration tests.

**Test scenarios:**

1. **Queue context lifecycle:**
```python
def test_queue_context_lifecycle():
    """Verify context activates and deactivates properly."""
    assert not QueueContext.is_active()
    
    with QueueContextManager():
        assert QueueContext.is_active()
        # Context is active here
    
    assert not QueueContext.is_active()
    # Context is deactivated
```

2. **Nested contexts:**
```python
def test_nested_queue_contexts():
    """Verify nested contexts don't break."""
    with QueueContextManager():
        assert QueueContext.is_active()
        
        with QueueContextManager():
            assert QueueContext.is_active()
        
        assert QueueContext.is_active()
```

3. **Agent creation enforcement:**
```python
def test_agent_creation_without_context_fails():
    """Verify agents can't be created outside queue context."""
    with pytest.raises(QueueEnforcementError):
        create_agent("engineer")

def test_agent_creation_with_context_succeeds():
    """Verify agents can be created with active queue context."""
    with QueueContextManager():
        engineer = create_agent("engineer")
        assert isinstance(engineer, QueueEnforcingProxy)
```

4. **Agent execution enforcement:**
```python
def test_agent_execution_requires_context():
    """Verify agents can't execute outside queue context."""
    with QueueContextManager():
        engineer = create_agent("engineer")
    
    # Agent is created, but execute() should fail (context now inactive)
    with pytest.raises(QueueEnforcementError):
        engineer.execute(test_work_item)

def test_agent_execution_succeeds_with_context():
    """Verify agents execute successfully within queue context."""
    with QueueContextManager():
        engineer = create_agent("engineer")
        result = engineer.execute(test_work_item)
        assert result.success
```

5. **Orchestrator integration:**
```python
def test_orchestrator_executes_agents_in_queue_context():
    """Verify orchestrator maintains active queue context."""
    orchestrator = create_agent("orchestrator")
    # Inside orchestrator.do_work(), queue context should be active
    # Verify by checking that agents can be created and executed
    results = list(orchestrator.execute(work_item))
    assert len(results) > 0
```

**Implementation checklist:**
- [ ] Create test_queue_enforcement.py
- [ ] Implement all 5 scenario tests
- [ ] All tests pass
- [ ] Code review approved

**Tests to write:** ~15-20 test functions

**File size estimate:** ~300 lines

---

### Step 3.2: End-to-End Smoke Tests

Run complete system end-to-end to verify enforcement doesn't break normal operation.

**Manual testing:**
- [ ] Run `python orchestration/agents/example_end_to_end.py`
- [ ] Verify expected output produced
- [ ] Run full test suite: `pytest orchestration/agents/ -v`
- [ ] Verify all tests pass
- [ ] Check for any performance regressions (should be negligible)

**Automated testing:**
- [ ] Add smoke test to CI pipeline (if applicable)
- [ ] Verify on multiple Python versions (3.8+)

---

### Phase 3 Success Criteria
- [ ] All integration tests pass
- [ ] End-to-end examples work correctly
- [ ] No performance regressions
- [ ] Full test suite passes

**Estimated time:** 2 days

---

## Phase 4: Documentation & Cleanup (1 day)

### Step 4.1: Update Code Comments and Docstrings

Ensure all enforcement code is well-documented.

**Checklist:**
- [ ] All queue_enforcement.py classes have complete docstrings
- [ ] create_agent() docstring clearly explains queue requirement
- [ ] Agent base class has comment about queue requirement
- [ ] Test code has comments explaining context manager usage

**Quality bar:** Docstrings should be clear enough that someone unfamiliar with the project understands:
- What the code does
- Why queue context is required
- How to use it correctly
- What happens if queue context is missing

---

### Step 4.2: Update SPEC.md

Add section referencing queue enforcement pattern.

**Add to SPEC.md:**
```markdown
## Queue Enforcement Mechanism

All agent execution is enforced to occur exclusively within queue context.
See `docs/architecture-queue-enforcement-5101.md` for complete architectural design.

### Enforcement Layers

1. **Factory Validation** (`create_agent()`): 
   - Validates queue context at agent creation time
   - Raises QueueEnforcementError if context is missing

2. **Proxy Enforcement** (`QueueEnforcingProxy`):
   - Wraps agent instances
   - Validates context again at execute() call time
   - Provides clear error messages with fix instructions

3. **Context Management** (`QueueContextManager`):
   - Orchestrator uses this to mark active queue context
   - Test code uses this to explicitly opt into queue mode
   - Prevents accidental violations in test code

### Implementation Reference

See `orchestration/agents/queue_enforcement.py` for complete implementation.
```

---

### Step 4.3: Update MANIFEST.md

Add queue_enforcement.py to the manifest.

**Add entry:**
```markdown
### orchestration/agents/queue_enforcement.py
Core queue enforcement middleware. Provides:
- QueueContext: Singleton for queue context tracking
- QueueContextManager: Context manager for explicit context marking
- QueueEnforcementError: Exception for enforcement violations
- QueueEnforcingProxy: Transparent proxy enforcing queue-only execution

Key lines:
- 1-50: Core classes definition
- 51-150: QueueEnforcingProxy implementation
- 151-200: Docstrings and type hints

Purpose: Enforce ORCHESTRATOR-FIRST execution model by preventing
direct agent invocation outside queue routing.
```

---

### Phase 4 Success Criteria
- [ ] All code properly documented
- [ ] SPEC.md updated with enforcement reference
- [ ] MANIFEST.md updated with new file
- [ ] README updated if needed
- [ ] All documentation is accurate and complete

**Estimated time:** 1 day

---

## Summary: Files to Create/Modify

### New Files
- [ ] `orchestration/agents/queue_enforcement.py` (~250 lines)
  - QueueContext singleton
  - QueueContextManager context manager
  - QueueEnforcementError exception
  - QueueEnforcingProxy wrapper class

- [ ] `orchestration/agents/test_queue_enforcement.py` (~300 lines)
  - Unit tests for queue context
  - Unit tests for proxy
  - Integration tests for orchestrator

### Modified Files
- [ ] `orchestration/agents/implementations.py` (~10 lines modified)
  - Update create_agent() factory

- [ ] `orchestration/agents/__init__.py` (~10 lines added)
  - Export enforcement classes

- [ ] `orchestration/agents/orchestrator.py` (~5 lines added)
  - Activate queue context in do_work()

- [ ] `orchestration/agents/testing_harness.py` (~50 lines modified)
  - Add context managers to all tests

- [ ] `orchestration/agents/example_end_to_end.py` (~10 lines modified)
  - Add context manager to main()

- [ ] `docs/SPEC.md` (~20 lines added)
  - Document queue enforcement mechanism

- [ ] `MANIFEST.md` (~5 lines added)
  - Add queue_enforcement.py entry

---

## Quality Checklist

Before marking work as complete:

- [ ] All new code has type hints
- [ ] All new code has docstrings
- [ ] All functions/classes have examples in docstrings
- [ ] All error messages are clear and actionable
- [ ] All tests pass (unit + integration)
- [ ] No linting errors
- [ ] No test regressions
- [ ] Code review approved
- [ ] Documentation is accurate
- [ ] Performance impact < 1% on hot path

---

## Testing Strategy

### Unit Tests
- Test each class in isolation
- Mock dependencies as needed
- Cover success and failure paths

### Integration Tests  
- Test queue context with real agents
- Test orchestrator with enforcement
- Test end-to-end flows

### Smoke Tests
- Run examples end-to-end
- Run full test suite
- Manual testing of critical paths

---

## Troubleshooting Guide

### Problem: "QueueEnforcementError: Agent attempted to execute outside queue context"

**Cause:** Code is calling create_agent() or agent.execute() outside queue context.

**Solution:** Wrap in context manager:
```python
from orchestration.agents import QueueContextManager

with QueueContextManager():
    agent = create_agent("engineer")
    result = agent.execute(work_item)
```

### Problem: Test passes locally but fails in CI

**Cause:** CI environment might have different context initialization.

**Solution:** Ensure all tests use context manager explicitly.

### Problem: Performance regression after enforcement

**Cause:** Context checking has overhead (unlikely with flag check).

**Solution:** Profile with `cProfile` to identify bottleneck. Should be negligible.

---

**Estimated Total Time:** 8-10 days  
**Team:** 1 Engineer  
**Complexity:** Medium (straightforward changes, good error handling)  

Next steps: Start with Phase 1, complete phases in order.

