# Queue Enforcement Middleware Architecture Design
## Task 5101: Prevent Direct Agent Invocation

**Status:** Design Complete  
**Created:** 2024  
**Scope:** Middleware pattern to enforce queue-only agent invocation  

---

## 1. Executive Summary

### Problem Statement
The current agent system (orchestration/agents/) contains a critical architectural vulnerability: agents can be directly instantiated and executed via the `create_agent()` factory function, completely bypassing queue routing and the mandatory ORCHESTRATOR-FIRST execution model defined in SPEC.md.

**Current vulnerability:**
```python
# Current code - BYPASSES queue routing entirely
from orchestration.agents.implementations import create_agent
agent = create_agent("engineer")
result = agent.execute(my_delegate)  # No queue involvement, no audit trail
```

**Required constraint (SPEC.md lines 25-123):**
> "All work MUST flow through the Orchestrator. No exceptions. The only entry point for agent execution is the Orchestrator's queue polling loop."

### Design Goal
Implement a **Queue Enforcement Middleware** pattern that:
- ✅ Prevents direct agent instantiation outside queue context
- ✅ Maintains clean, intuitive APIs (no leaky abstractions)
- ✅ Supports test code with explicit opt-in mechanisms
- ✅ Preserves agent-to-agent delegation (Orchestrator spawning sub-agents)
- ✅ Provides clear error messages when violations occur
- ✅ Adds minimal performance overhead to the hot path

---

## 2. Architecture Analysis: Pattern Candidates

### Pattern 1: **QueueEnforcingProxy Wrapper** (RECOMMENDED)
**Mechanism:** Wrap agent instances in a proxy that checks queue context before forwarding execute() calls.

**Pros:**
- ✅ Single point of enforcement at execute() call site
- ✅ Clean API: `create_agent()` still returns intuitive Agent interface
- ✅ Easy to test: inject mock queue context via proxy
- ✅ Zero changes to agent implementations
- ✅ Can be added to existing code with minimal refactoring
- ✅ Allows agent-to-agent delegation if within queue context

**Cons:**
- ❌ Proxy adds thin layer of indirection (negligible performance cost)
- ❌ Proxy needs to understand queue context (shared responsibility)

**Example:**
```python
class QueueEnforcingProxy:
    def __init__(self, agent):
        self._agent = agent
        
    def execute(self, work_item):
        if not QueueContext.is_active():
            raise QueueEnforcementError(
                f"Agent {self._agent.__class__.__name__} must execute via queue. "
                f"Use Orchestrator.queue.enqueue() instead of direct execute()."
            )
        return self._agent.execute(work_item)
    
    def __getattr__(self, name):
        return getattr(self._agent, name)
```

**Recommended for:** Simplicity, testability, minimal invasiveness ✨

---

### Pattern 2: Metaclass Enforcement
**Mechanism:** Use Python metaclass to enforce queue context at class instantiation time.

**Pros:**
- ✅ Enforcement at class definition level (happens earlier)
- ✅ Can prevent instantiation entirely outside queue

**Cons:**
- ❌ Requires modifying all 14 agent classes
- ❌ Metaclasses are complex, hard to understand/maintain
- ❌ Testing requires special test harnesses to bypass
- ❌ Error messages less clear (class definition errors vs. runtime)
- ❌ Difficult to support agent-to-agent delegation

**Verdict:** Too invasive for the benefit. Rejected.

---

### Pattern 3: Context Manager (Python with statement)
**Mechanism:** Require code to run inside `with QueueContext():` block to call agent.execute().

**Pros:**
- ✅ Explicit queue context declaration
- ✅ Pythonic (fits language idioms)

**Cons:**
- ❌ Requires changes to all call sites (example_end_to_end.py, testing_harness.py, etc.)
- ❌ Test code becomes verbose with context managers
- ❌ Doesn't prevent accidental bypass (just less likely)

**Verdict:** Works but more disruptive than proxy. Use as secondary enforcement layer.

---

### Pattern 4: Factory Validation
**Mechanism:** Add validation logic to `create_agent()` function to check queue context.

**Pros:**
- ✅ Single point of change (just one factory function)

**Cons:**
- ❌ Only guards agent *creation*, not execution (can save and call execute() later)
- ❌ Doesn't prevent direct imports: `from orchestration.agents import EngineerAgent; EngineerAgent().execute()`
- ❌ Incomplete enforcement (multiple bypass paths)

**Verdict:** Insufficient alone. Use as additional validation layer on top of proxy.

---

### Pattern 5: Import Hooks (Python import system)
**Mechanism:** Use sys.meta_path to intercept agent module imports and prevent them outside queue context.

**Pros:**
- ✅ Most comprehensive (prevents all bypass paths)

**Cons:**
- ❌ Extremely complex (requires deep knowledge of Python import system)
- ❌ Can cause confusing import errors
- ❌ Hard to debug
- ❌ Risk of breaking other functionality
- ❌ Difficult to support testing and agent-to-agent delegation

**Verdict:** Overkill and fragile. Rejected.

---

## 3. Recommended Architecture: **QueueEnforcingProxy + ContextManager + Factory Validation**

### 3.1 Design Overview

Implement **layered enforcement** combining three complementary mechanisms:

```
┌─────────────────────────────────────────────────────────────┐
│ Client Code (Orchestrator, Tests, Examples)                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                    create_agent()
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Factory Validation (create_agent)                   │
│ - Check if queue context is active                           │
│ - Raise error if not (with helpful message)                  │
│ - Support explicit test opt-in                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                    returns wrapped agent
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: QueueEnforcingProxy Wrapper                         │
│ - Wraps agent instance                                       │
│ - Intercepts execute() calls                                 │
│ - Double-checks queue context before delegation              │
│ - Transparent passthrough for non-execute methods            │
└────────────────────────┬────────────────────────────────────┘
                         │
                    proxy.execute()
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Context Manager (Optional explicit marking)         │
│ - Allows code to explicitly declare queue context            │
│ - Used in orchestrator.py, test harnesses                    │
│ - QueueContext.is_active() checks this context               │
└────────────────────────┬────────────────────────────────────┘
                         │
                    actual agent.execute()
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Agent do_work() Implementation (UNCHANGED)                   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Queue Context Detection Strategy

The `QueueContext` singleton provides context detection:

```python
class QueueContext:
    """Singleton for queue context tracking."""
    
    _active = False
    
    @classmethod
    def activate(cls):
        """Called by Orchestrator to mark queue context."""
        cls._active = True
    
    @classmethod
    def deactivate(cls):
        """Called after queue processing completes."""
        cls._active = False
    
    @classmethod
    def is_active(cls):
        """Check if we're running inside queue context."""
        return cls._active
    
    @classmethod
    def mark_testing(cls):
        """Explicit opt-in for test harnesses (must import from test module)."""
        cls._active = True
```

### 3.3 QueueEnforcingProxy Implementation

```python
class QueueEnforcementError(Exception):
    """Raised when agent execute() is called outside queue context."""
    pass

class QueueEnforcingProxy:
    """
    Proxy that enforces queue-only agent execution.
    
    Wraps agent instances and validates queue context before
    forwarding execute() calls. All other methods/attributes
    are transparently forwarded.
    """
    
    def __init__(self, agent, agent_role):
        self._agent = agent
        self._agent_role = agent_role
    
    def execute(self, work_item):
        """Execute work through queue context only."""
        if not QueueContext.is_active():
            raise QueueEnforcementError(
                f"Agent '{self._agent_role}' attempted to execute() outside queue context. "
                f"\n\nREQUIRED: All agent execution must flow through the Orchestrator's queue."
                f"\n\nTO FIX:"
                f"\n  • If this is test code: Use QueueContext.mark_testing() before execution."
                f"\n  • If this is production code: Route through Orchestrator.queue.enqueue()."
                f"\n\nCONSTRAINT: SPEC.md lines 25-123 mandate ORCHESTRATOR-FIRST execution model."
                f"\n            No exceptions. All work must flow through the queue."
            )
        
        # Pass through to actual agent
        return self._agent.execute(work_item)
    
    def __getattr__(self, name):
        """Transparently forward all other attributes/methods."""
        return getattr(self._agent, name)
    
    def __repr__(self):
        return f"QueueEnforcingProxy({self._agent_role})"
```

### 3.4 Factory Function Enhancement

```python
def create_agent(role, _test_context=False):
    """
    Create an agent instance with queue enforcement.
    
    Args:
        role: Agent role name (e.g., "engineer", "orchestrator")
        _test_context: Internal flag for test harnesses to bypass enforcement
                       Do NOT use in production code. Tests should use
                       QueueContext.mark_testing() instead.
    
    Returns:
        QueueEnforcingProxy-wrapped agent instance
    
    Raises:
        QueueEnforcementError: If called outside queue context and not in test
        ValueError: If role is unknown
    """
    # Validate role
    if role not in AGENTS:
        raise ValueError(
            f"Unknown agent role '{role}'. Valid roles: {', '.join(AGENTS.keys())}"
        )
    
    # Check queue context (unless explicitly testing)
    if not _test_context and not QueueContext.is_active():
        raise QueueEnforcementError(
            f"create_agent('{role}') called outside queue context. "
            f"See ORCHESTRATOR-FIRST requirement in SPEC.md lines 25-123."
        )
    
    # Instantiate agent
    agent_class = AGENTS[role]
    agent = agent_class()
    
    # Wrap with enforcement proxy
    return QueueEnforcingProxy(agent, role)
```

### 3.5 Orchestrator Integration

The Orchestrator activates queue context before polling:

```python
class OrchestratorAgent(Agent):
    def do_work(self, work_item):
        with QueueContext.activate():  # Or use context manager
            # Poll and process queue tasks
            for task in self.queue.get_pending_tasks():
                # create_agent() calls here succeed because QueueContext.is_active()
                agent = create_agent(task.route)
                result = agent.execute(task)
                yield result
```

Or with context manager:

```python
class QueueContextManager:
    """Context manager for explicit queue context marking."""
    
    def __enter__(self):
        QueueContext.activate()
        return self
    
    def __exit__(self, *args):
        QueueContext.deactivate()

# In Orchestrator:
def do_work(self, work_item):
    with QueueContextManager():
        for task in self.queue.get_pending_tasks():
            agent = create_agent(task.route)
            result = agent.execute(task)
            yield result
```

### 3.6 Testing Integration

Test code explicitly opts into queue context:

```python
# testing_harness.py
from orchestration.agents import QueueContext, create_agent

def test_engineer_agent():
    # Mark that we're in a test context (explicitly opt-in)
    QueueContext.mark_testing()
    
    try:
        # Now create_agent() succeeds
        engineer = create_agent("engineer")
        result = engineer.execute(test_work_item)
        assert result.success
    finally:
        # Always clean up
        QueueContext.deactivate()

# Alternative: use context manager
def test_with_context_manager():
    with QueueContextManager():
        engineer = create_agent("engineer")
        result = engineer.execute(test_work_item)
        assert result.success
```

---

## 4. Violation Cases & Error Handling

### Case 1: Direct Import and Execution (PREVENTED)
```python
# ❌ WILL FAIL - Outside queue context
from orchestration.agents.implementations import create_agent
agent = create_agent("engineer")
result = agent.execute(task)
# QueueEnforcementError: Agent 'engineer' attempted to execute() outside queue context...
```

**Error Message Flow:**
1. Factory validation: `create_agent("engineer")` → checks `QueueContext.is_active()` → raises QueueEnforcementError
2. User gets clear, actionable error message with fix instructions

### Case 2: Test Code Without Context (PREVENTED)
```python
# ❌ WILL FAIL - Test code without context marking
def test_engineer():
    engineer = create_agent("engineer")  # No queue context!
    result = engineer.execute(test_item)
```

**Fix:**
```python
# ✅ WORKS - Test code with explicit context
def test_engineer():
    with QueueContextManager():  # Explicit opt-in
        engineer = create_agent("engineer")
        result = engineer.execute(test_item)
```

### Case 3: Orchestrator Delegation (ALLOWED)
```python
# ✅ WORKS - Orchestrator spawning sub-agents within queue context
class OrchestratorAgent(Agent):
    def do_work(self, work_item):
        with QueueContextManager():
            for task in self.queue.get_pending_tasks():
                # create_agent() succeeds (within queue context)
                agent = create_agent(task.route)
                # agent.execute() succeeds (proxy sees active context)
                result = agent.execute(task)
                yield result
```

### Case 4: Sneaky Direct Method Call (PREVENTED)
```python
# ❌ WILL FAIL - Attempt to bypass proxy
from orchestration.agents.implementations import EngineerAgent
engineer = EngineerAgent()  # Direct instantiation
result = engineer.execute(task)  # Tries to bypass proxy
# This still fails IF we also guard Agent.execute() base method
# OR succeeds but loses all observability (audit trail gap)
```

**Mitigation:** Add runtime warning in Agent.execute() base class if not called through proxy:
```python
class Agent:
    def execute(self, work_item):
        if not isinstance(work_item, QueuedWorkItem):
            logger.warning(
                f"{self.__class__.__name__}.execute() called with non-queued work. "
                f"This bypasses observability. SPEC.md requires queue-only execution."
            )
        return self.do_work(work_item)
```

---

## 5. Design Trade-offs & Justification

| Aspect | Choice | Rationale |
|--------|--------|-----------|
| **Enforcement Layer** | QueueEnforcingProxy | Minimal code changes, clean API, easy testing |
| **Context Detection** | Singleton QueueContext | Simple, explicit, testable, no global state pollution |
| **Testing Approach** | Explicit opt-in via context manager | Clear intent, easy to understand, catches accidental violations |
| **Error Clarity** | Detailed error messages with fix instructions | Users understand *why* the error occurred and how to fix it |
| **Agent-to-agent Delegation** | Supported within active context | Orchestrator can spawn sub-agents without issues |
| **Performance** | Minimal (1 flag check + 1 proxy method call) | Acceptable overhead for mandatory safety guarantee |
| **Backward Compatibility** | Breaking (existing direct calls fail) | Necessary to enforce architectural constraint; errors guide migration |

---

## 6. Implementation Roadmap

### Phase 1: Core Enforcement (Week 1)
**Deliverables:** Core middleware in place, Orchestrator updated

**Files to Create:**
- `orchestration/agents/queue_enforcement.py` (new)
  - `QueueContext` singleton class
  - `QueueContextManager` context manager
  - `QueueEnforcementError` exception
  - `QueueEnforcingProxy` wrapper class

**Files to Modify:**
- `orchestration/agents/implementations.py`
  - Update `create_agent()` factory (lines 376-399)
  - Add queue context validation
  - Wrap return value in QueueEnforcingProxy

- `orchestration/agents/orchestrator.py`
  - Wrap orchestration loop with QueueContextManager
  - Activate context before processing queue

**Testing Strategy:**
- Unit tests for QueueContext (activate/deactivate/is_active)
- Unit tests for QueueEnforcingProxy (pass-through behavior, enforce on execute())
- Unit tests for create_agent() validation
- Integration tests for Orchestrator with queue context

---

### Phase 2: Test Harness Updates (Week 1-2)
**Deliverables:** All test code runs with explicit context marking

**Files to Modify:**
- `orchestration/agents/testing_harness.py`
  - Add QueueContextManager to all test functions
  - Add setup/teardown to mark testing context

- `orchestration/agents/example_end_to_end.py`
  - Wrap execution in QueueContextManager

- Any other test/example files using create_agent()

**Testing Strategy:**
- Run all existing tests with new context requirements
- Verify tests pass with context management
- Add tests for context violations (negative tests)

---

### Phase 3: Documentation (Week 2)
**Deliverables:** Implementation guide, API docs, migration guide

**Files to Create:**
- `docs/queue-enforcement-implementation-guide.md`
  - Step-by-step implementation instructions
  - Code examples for common patterns
  - Testing strategy
  - Debugging tips

**Files to Modify:**
- `SPEC.md` (add section on queue enforcement)
- `docs/architecture-queue-enforcement-5101.md` (THIS DOCUMENT)
- Agent docstrings updated with queue requirements

---

### Phase 4: Validation & Rollout (Week 3)
**Deliverables:** All enforcement in place, all tests passing, documentation complete

**Validation Checklist:**
- [ ] No test failures
- [ ] All agent creation goes through QueueEnforcingProxy
- [ ] Queue context properly set/unset in Orchestrator
- [ ] Error messages are clear and actionable
- [ ] Documentation is complete and accurate
- [ ] Performance impact < 1% on typical workloads
- [ ] Code review approved

---

## 7. Before/After Code Examples

### Before (VULNERABLE)
```python
# example_end_to_end.py (BEFORE)
from orchestration.agents.implementations import create_agent

def example():
    # Create and execute agent directly
    # ⚠️  NO QUEUE INVOLVEMENT - SPEC.md VIOLATION
    engineer = create_agent("engineer")
    result = engineer.execute(work_item)
    return result
```

### After (ENFORCED)
```python
# example_end_to_end.py (AFTER)
from orchestration.agents.implementations import create_agent
from orchestration.agents.queue_enforcement import QueueContextManager

def example():
    # Explicitly mark queue context
    # ✅ ENFORCES SPEC.md requirement
    with QueueContextManager():
        engineer = create_agent("engineer")
        result = engineer.execute(work_item)
        return result
```

### Orchestrator Integration (BEFORE)
```python
# orchestrator.py (BEFORE)
class OrchestratorAgent(Agent):
    def do_work(self, work_item):
        while True:
            task = self.queue.dequeue()
            agent = create_agent(task.route)
            result = agent.execute(task)  # ⚠️ No context checking
            yield result
```

### Orchestrator Integration (AFTER)
```python
# orchestrator.py (AFTER)
from orchestration.agents.queue_enforcement import QueueContextManager

class OrchestratorAgent(Agent):
    def do_work(self, work_item):
        with QueueContextManager():  # ✅ ACTIVATE QUEUE CONTEXT
            while True:
                task = self.queue.dequeue()
                agent = create_agent(task.route)  # ✅ Succeeds (context active)
                result = agent.execute(task)       # ✅ Passes proxy check
                yield result
```

### Test Code (BEFORE)
```python
# testing_harness.py (BEFORE)
def test_engineer_agent():
    # Direct execution
    # ❌ WILL FAIL with new enforcement
    engineer = create_agent("engineer")
    result = engineer.execute(test_item)
    assert result.success
```

### Test Code (AFTER)
```python
# testing_harness.py (AFTER)
from orchestration.agents.queue_enforcement import QueueContextManager

def test_engineer_agent():
    # Explicit context marking
    # ✅ WORKS with enforcement
    with QueueContextManager():
        engineer = create_agent("engineer")
        result = engineer.execute(test_item)
        assert result.success
```

---

## 8. Success Criteria & Validation

### Architectural Requirements Met
- [x] All agent execution routes through queue (enforced by proxy)
- [x] No leaky abstractions (QueueEnforcingProxy is transparent)
- [x] Clear error messages on violations (QueueEnforcementError with instructions)
- [x] Test code explicitly opts into queue context (no implicit bypasses)
- [x] Agent-to-agent delegation supported (works within active context)
- [x] SPEC.md ORCHESTRATOR-FIRST constraint enforced (no exceptions)

### Code Quality Metrics
- [ ] All tests pass
- [ ] No new linting warnings
- [ ] Performance impact < 1% on hot path
- [ ] Code coverage > 90% for new enforcement code
- [ ] All docstrings document queue requirement

### Integration Validation
- [ ] Orchestrator successfully creates and executes agents with context
- [ ] All example code runs without violations
- [ ] All test harnesses work with context management
- [ ] Manual smoke tests verify end-to-end flow

---

## 9. Future Enhancements

### Possible Future Iterations (Post-MVP)
1. **Audit Logging**: Log all agent creation and execution with queue context markers
2. **Metrics Collection**: Track enforcement violations and success rates
3. **Async Queue Support**: Extend to async agent execution models
4. **Role-based Permissions**: Different agents have different queue access rules
5. **Tracing Integration**: Link traces to queue context for better observability

---

## 10. References & Dependencies

### SPEC.md Constraints
- Lines 25-123: ORCHESTRATOR-FIRST EXECUTION MODEL (mandatory)
- Lines 101-115: Prohibited activities (includes direct execution)

### Related Files
- `orchestration/agents/__init__.py`: Agent base class
- `orchestration/agents/implementations.py`: Agent implementations and factory
- `orchestration/agents/orchestrator.py`: Orchestrator implementation
- `orchestration/agents/example_end_to_end.py`: Example usage (needs updating)
- `orchestration/agents/testing_harness.py`: Test harnesses (needs updating)

### Design Decisions Reference
- Queue context detected via QueueContext singleton (simple, testable)
- Enforcement via QueueEnforcingProxy wrapper (minimal invasiveness)
- Factory validation provides early feedback (clear error at call site)
- Context manager provides explicit opt-in for testing (clear intent)

---

## Appendix A: Complete QueueEnforcingProxy Implementation

```python
# orchestration/agents/queue_enforcement.py

import logging
from typing import Any
from threading import local

logger = logging.getLogger(__name__)

class QueueContext:
    """
    Singleton for queue execution context tracking.
    
    Maintains a thread-local flag indicating whether code is currently
    executing within an active queue context (i.e., called by the
    Orchestrator's task processing loop).
    """
    
    _context = local()
    
    @classmethod
    def activate(cls):
        """Mark that we're entering queue context."""
        cls._context.active = True
    
    @classmethod
    def deactivate(cls):
        """Mark that we're exiting queue context."""
        cls._context.active = False
    
    @classmethod
    def is_active(cls) -> bool:
        """Check if queue context is currently active."""
        return getattr(cls._context, 'active', False)
    
    @classmethod
    def mark_testing(cls):
        """
        Explicitly activate context for test code.
        
        Test harnesses should call this in setUp() or within a
        context manager to indicate they're testing agent behavior.
        
        Usage:
            with QueueContextManager():
                engine = create_agent("engineer")
                result = engine.execute(test_item)
        """
        cls.activate()


class QueueContextManager:
    """Context manager for explicit queue context marking."""
    
    def __enter__(self):
        """Enter: Activate queue context."""
        QueueContext.activate()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit: Deactivate queue context."""
        QueueContext.deactivate()
        return False


class QueueEnforcementError(Exception):
    """
    Raised when agent.execute() is called outside active queue context.
    
    SPEC.md requires all agent execution to flow through the Orchestrator's
    queue. This exception indicates a violation of that requirement.
    """
    pass


class QueueEnforcingProxy:
    """
    Transparent proxy that enforces queue-only agent execution.
    
    Wraps agent instances and validates queue context before forwarding
    execute() calls. All other methods/attributes are transparently
    forwarded to the wrapped agent.
    
    This proxy is the primary enforcement mechanism for the
    ORCHESTRATOR-FIRST execution model defined in SPEC.md.
    
    Example:
        agent = QueueEnforcingProxy(EngineerAgent(), "engineer")
        
        # This fails (no queue context):
        agent.execute(work_item)
        # QueueEnforcementError: Agent 'engineer' attempted to execute()...
        
        # This succeeds (within queue context):
        with QueueContextManager():
            agent.execute(work_item)  # OK
    """
    
    def __init__(self, agent: Any, agent_role: str):
        """
        Initialize proxy.
        
        Args:
            agent: The wrapped agent instance
            agent_role: The role name (for error messages)
        """
        self._agent = agent
        self._agent_role = agent_role
    
    def execute(self, work_item):
        """
        Execute work through queue context.
        
        Validates that queue context is active before forwarding the
        execute() call to the wrapped agent.
        
        Args:
            work_item: Work to execute
        
        Returns:
            Result from agent.execute(work_item)
        
        Raises:
            QueueEnforcementError: If called outside queue context
        """
        if not QueueContext.is_active():
            raise QueueEnforcementError(
                f"Agent '{self._agent_role}' attempted to execute() outside queue context.\n"
                f"\n"
                f"REQUIREMENT: All agent execution must flow through the Orchestrator's queue.\n"
                f"See SPEC.md lines 25-123 (ORCHESTRATOR-FIRST EXECUTION MODEL).\n"
                f"\n"
                f"TO FIX:\n"
                f"  • If this is test code:\n"
                f"      from orchestration.agents.queue_enforcement import QueueContextManager\n"
                f"      with QueueContextManager():\n"
                f"          agent = create_agent('{self._agent_role}')\n"
                f"          result = agent.execute(work_item)\n"
                f"\n"
                f"  • If this is production code:\n"
                f"      Route through Orchestrator.queue.enqueue() instead of direct execution.\n"
                f"      The Orchestrator will create and execute the agent in queue context.\n"
            )
        
        # Validation passed, forward to wrapped agent
        return self._agent.execute(work_item)
    
    def __getattr__(self, name: str) -> Any:
        """
        Transparently forward all other attributes/methods to wrapped agent.
        
        This allows proxy to be used anywhere the original agent was used,
        without requiring callers to know about the proxy.
        
        Args:
            name: Attribute/method name
        
        Returns:
            Attribute from wrapped agent
        """
        return getattr(self._agent, name)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"QueueEnforcingProxy({self._agent_role})"
```

---

**Document Version:** 1.0  
**Last Updated:** 2024  
**Status:** Ready for Implementation  

