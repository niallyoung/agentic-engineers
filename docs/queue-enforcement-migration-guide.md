# Queue Enforcement Migration Guide

**How to Migrate Code to Queue-Enforced Agent Execution**

**Status:** Phase 4 Implementation  
**Target:** All agent execution  
**Timeline:** Immediate

---

## Quick Start: 3-Step Fix

If you have code that fails with `QueueEnforcementError`:

### Step 1: Add Import
```python
from orchestration.agents.queue_enforcement_middleware import QueueContextManager
```

### Step 2: Wrap Execution
```python
# BEFORE
agent = create_agent("engineer")
result = agent.execute(work_item)

# AFTER
with QueueContextManager():
    agent = create_agent("engineer")
    result = agent.execute(work_item)
```

### Step 3: Verify
```bash
cd 
python3 -m pytest orchestration/agents/test_queue_enforcement.py -v
```

---

## Detailed Migration Path

### Phase 1: Test Code Migration

**Priority:** HIGH - All test code must be updated

#### 1.1 Test Harnesses

**File:** `orchestration/agents/testing_harness.py`

**Before:**
```python
def test_engineer_agent():
    engineer = create_agent("engineer")
    result = engineer.execute(test_item)
    assert result.success
```

**After:**
```python
from orchestration.agents.queue_enforcement_middleware import QueueContextManager

def test_engineer_agent():
    with QueueContextManager():
        engineer = create_agent("engineer")
        result = engineer.execute(test_item)
        assert result.success
```

#### 1.2 Orchestrator Test Harness

**File:** `orchestration/agents/orchestrator_testing_harness.py`

**Before:**
```python
def test_orchestrator_routing():
    orchestrator = create_agent("orchestrator")
    result = orchestrator.execute(work_item)
    assert result["routing_decision"]
```

**After:**
```python
from orchestration.agents.queue_enforcement_middleware import QueueContextManager

def test_orchestrator_routing():
    with QueueContextManager():
        orchestrator = create_agent("orchestrator")
        result = orchestrator.execute(work_item)
        assert result["routing_decision"]
```

#### 1.3 Integration Tests

**Pattern:** Wrap entire test or use class-level setup/teardown.

**Option A: Wrap test function**
```python
def test_agent_integration():
    with QueueContextManager():
        # All agent operations here
        agent1 = create_agent("engineer")
        agent2 = create_agent("senior_engineer")
        
        result1 = agent1.execute(task1)
        result2 = agent2.execute(task2)
        
        assert result1.success and result2.success
```

**Option B: Class-level setup (recommended)**
```python
class TestAgentIntegration:
    @classmethod
    def setup_class(cls):
        from orchestration.agents.queue_enforcement_middleware import QueueContext
        QueueContext.activate()
    
    @classmethod
    def teardown_class(cls):
        from orchestration.agents.queue_enforcement_middleware import QueueContext
        QueueContext.deactivate()
    
    def test_agent_execution(self):
        # No wrapping needed - context active at class level
        agent = create_agent("engineer")
        result = agent.execute(task)
        assert result.success
```

**Option C: Fixture (recommended for pytest)**
```python
import pytest
from orchestration.agents.queue_enforcement_middleware import QueueContextManager

@pytest.fixture
def queue_context():
    """Provide active queue context for tests."""
    with QueueContextManager():
        yield

def test_agent_with_context(queue_context):
    # queue_context fixture provides active queue context
    agent = create_agent("engineer")
    result = agent.execute(task)
    assert result.success
```

---

### Phase 2: Example Code Migration

**Priority:** MEDIUM - All examples must show proper patterns

#### 2.1 End-to-End Examples

**File:** `orchestration/agents/example_end_to_end.py`

**Before:**
```python
def example():
    """Example: Create and execute an agent."""
    engineer = create_agent("engineer")
    result = engineer.execute(work_item)
    return result
```

**After:**
```python
from orchestration.agents.queue_enforcement_middleware import QueueContextManager

def example():
    """Example: Create and execute an agent with queue enforcement."""
    with QueueContextManager():  # ✅ Queue context required
        engineer = create_agent("engineer")
        result = engineer.execute(work_item)
        return result
```

#### 2.2 Workflow Examples

**File:** `orchestration/agents/workflow.py`

**Before:**
```python
def multi_agent_workflow():
    """Execute multiple agents in sequence."""
    orchestrator = create_agent("orchestrator")
    result1 = orchestrator.execute(task1)
    
    engineer = create_agent("engineer")
    result2 = engineer.execute(task2)
    
    return [result1, result2]
```

**After:**
```python
from orchestration.agents.queue_enforcement_middleware import QueueContextManager

def multi_agent_workflow():
    """Execute multiple agents in sequence with queue enforcement."""
    with QueueContextManager():  # ✅ Single context for all agents
        orchestrator = create_agent("orchestrator")
        result1 = orchestrator.execute(task1)
        
        engineer = create_agent("engineer")
        result2 = engineer.execute(task2)
        
        return [result1, result2]
```

---

### Phase 3: Production Code Migration

**Priority:** MEDIUM - Integrate into agent implementations

#### 3.1 Orchestrator Integration

**File:** `orchestration/agents/orchestrator.py`

**Before:**
```python
class OrchestratorAgent(Agent):
    def do_work(self):
        """Process queue tasks."""
        while True:
            task = self.queue.dequeue()
            if not task:
                break
            
            # No queue context!
            agent = create_agent(task.route)
            result = agent.execute(task)
            
            self.queue.mark_complete(task)
            yield result
```

**After:**
```python
from orchestration.agents.queue_enforcement_middleware import QueueContextManager

class OrchestratorAgent(Agent):
    def execute(self, work_item):
        """Process queue tasks with enforcement."""
        with QueueContextManager():  # ✅ Activate for entire task loop
            # All sub-agent execution happens with active context
            while True:
                task = self.queue.dequeue()
                if not task:
                    break
                
                agent = create_agent(task.route)
                result = agent.execute(task)
                
                self.queue.mark_complete(task)
                yield result
```

#### 3.2 Agent Delegation Pattern

If agents delegate to other agents:

**Before:**
```python
class LeadEngineerAgent(Agent):
    def do_work(self):
        """Review and delegate."""
        # No queue context inherited
        engineer = create_agent("engineer")
        result = engineer.execute(self.delegate_block)
        return result
```

**After:**
```python
class LeadEngineerAgent(Agent):
    def do_work(self):
        """Review and delegate."""
        # ✅ Delegate is called within Orchestrator's queue context
        # Queue context is inherited from parent
        engineer = create_agent("engineer")
        result = engineer.execute(self.delegate_block)
        return result
```

**Explanation:** Since `do_work()` is called by Orchestrator's `execute()`, which has active queue context, delegation automatically works without additional wrapping.

---

### Phase 4: Review and Testing

#### 4.1 Verify All Tests Pass

```bash
# Run queue enforcement tests
python3 -m pytest orchestration/agents/test_queue_enforcement.py -v

# Run all agent tests
python3 -m pytest orchestration/agents/ -v

# Run integration tests
python3 -m pytest orchestration/ -v
```

#### 4.2 Check for Remaining Violations

Search for patterns that might still violate enforcement:

```bash
# Find all create_agent calls
grep -r "create_agent" orchestration/ --include="*.py" | grep -v test | grep -v "with QueueContextManager"

# Find all .execute( calls
grep -r "\.execute(" orchestration/ --include="*.py" | grep -v test | grep -v "# OK" | head -20
```

#### 4.3 Code Review Checklist

- [ ] All test code uses `QueueContextManager` or equivalent context activation
- [ ] All example code shows queue context activation
- [ ] Orchestrator activates context for task loop
- [ ] Agent delegation inherits context from parent
- [ ] All enforcement tests pass (38/38)
- [ ] No violations detected in integration tests
- [ ] Error messages are clear and actionable
- [ ] Documentation is complete and accurate

---

## Common Patterns & Fixes

### Pattern 1: Test with Setup/Teardown

**Problem:** Tests in a class use `setUp()` and `tearDown()`.

**Before:**
```python
class TestAgents(unittest.TestCase):
    def setUp(self):
        self.agent = create_agent("engineer")  # ❌ Fails
    
    def test_execute(self):
        result = self.agent.execute(task)
```

**After:**
```python
class TestAgents(unittest.TestCase):
    def setUp(self):
        self.ctx = QueueContextManager()
        self.ctx.__enter__()
    
    def tearDown(self):
        self.ctx.__exit__(None, None, None)
    
    def test_execute(self):
        result = self.agent.execute(task)  # ✅ Works
```

---

### Pattern 2: Parametrized Tests

**Problem:** Parametrized tests with multiple agents.

**Before:**
```python
@pytest.mark.parametrize("role", ["engineer", "senior_engineer"])
def test_agent(role):
    agent = create_agent(role)  # ❌ Fails
    result = agent.execute(task)
```

**After:**
```python
@pytest.mark.parametrize("role", ["engineer", "senior_engineer"])
def test_agent(role):
    with QueueContextManager():  # ✅ Works
        agent = create_agent(role)
        result = agent.execute(task)
```

---

### Pattern 3: Async/Threaded Execution

**Problem:** Agent execution in separate thread.

**Before:**
```python
import threading

def worker():
    agent = create_agent("engineer")
    result = agent.execute(task)  # ❌ Fails - no inherited context

thread = threading.Thread(target=worker)
thread.start()
```

**After:**
```python
import threading
from orchestration.agents.queue_enforcement_middleware import QueueContextManager

def worker():
    with QueueContextManager():  # ✅ Activate in worker thread
        agent = create_agent("engineer")
        result = agent.execute(task)  # OK

thread = threading.Thread(target=worker)
thread.start()
```

---

### Pattern 4: Conditional Execution

**Problem:** Execute agent conditionally.

**Before:**
```python
if should_execute:
    agent = create_agent("engineer")  # ❌ Fails
    result = agent.execute(task)
```

**After:**
```python
with QueueContextManager():
    if should_execute:  # Context still active
        agent = create_agent("engineer")
        result = agent.execute(task)  # ✅ Works
```

---

### Pattern 5: Multiple Sequential Executions

**Problem:** Execute multiple agents in sequence.

**Before:**
```python
# ❌ Each execute() fails independently
for role in ["engineer", "senior_engineer"]:
    agent = create_agent(role)
    result = agent.execute(task)
```

**After:**
```python
# ✅ Single context for all executions
with QueueContextManager():
    for role in ["engineer", "senior_engineer"]:
        agent = create_agent(role)
        result = agent.execute(task)
```

---

## Troubleshooting

### Error: "Agent attempted to execute() outside queue context"

**Cause:** Code is calling `agent.execute()` without queue context.

**Solution:** Wrap in `QueueContextManager()`:
```python
with QueueContextManager():
    result = agent.execute(task)
```

---

### Error: ImportError - Can't import QueueContextManager

**Cause:** Module not installed or import path wrong.

**Solution:** Check import:
```python
from orchestration.agents.queue_enforcement_middleware import QueueContextManager
```

---

### Error: Test hangs or times out

**Cause:** Nested context managers or context not deactivating.

**Solution:** Ensure context deactivates:
```python
# ✅ Correct - context deactivates in finally block
try:
    with QueueContextManager():
        # test code
        pass
finally:
    # context automatically deactivates
    pass
```

---

### Error: Thread-local context not shared

**Cause:** Thread has its own context state.

**Solution:** Activate context in each thread:
```python
def worker():
    with QueueContextManager():  # Activate in worker thread
        agent = create_agent("engineer")
        result = agent.execute(task)
```

---

## Rollback Plan

If enforcement needs to be temporarily disabled:

```python
# In queue_enforcement_middleware.py, comment out enforcement:
def execute(self, work_item):
    # Temporarily disabled for debugging
    # if not QueueContext.is_active():
    #     raise QueueEnforcementError(...)
    
    return self._agent.execute(work_item)
```

**WARNING:** This removes enforcement. Re-enable after debugging.

---

## Summary

Queue enforcement migration is straightforward:

1. **Identify:** Find code calling `agent.execute()`
2. **Wrap:** Add `with QueueContextManager():` around it
3. **Test:** Run tests to verify it works
4. **Review:** Code review for compliance

Total changes needed: ~10-15 lines of imports and wrapping across the codebase.

Expected time: 1-2 hours for full migration.

---

## Related Documents

- **docs/queue-enforcement-rules.md**: Enforcement rules reference
- **docs/architecture-queue-enforcement-5101.md**: Architecture design
- **orchestration/agents/queue_enforcement_middleware.py**: Implementation
- **orchestration/agents/test_queue_enforcement.py**: Test suite
- **SPEC.md** (lines 25-123): ORCHESTRATOR-FIRST requirement

---

## Success Criteria Checklist

After migration, verify:

- [ ] All imports of `QueueContextManager` are correct
- [ ] All `agent.execute()` calls are within queue context
- [ ] Test code uses explicit context activation
- [ ] Example code shows proper patterns
- [ ] All tests pass (38/38 enforcement tests)
- [ ] No `QueueEnforcementError` exceptions in normal usage
- [ ] Clear error messages appear if violations occur
- [ ] Code review approved migration quality
- [ ] Performance impact < 1% on typical workloads
- [ ] Documentation updated and accurate
