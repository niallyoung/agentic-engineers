# Queue Enforcement Rules Reference

**Status:** Phase 4 Implementation  
**Author:** Principal Engineer  
**Last Updated:** 2024  
**Constraint Reference:** SPEC.md lines 25-123 (ORCHESTRATOR-FIRST EXECUTION MODEL)

---

## Overview

Queue enforcement middleware prevents direct agent invocation and ensures all work flows through the Orchestrator's queue system. This document defines the enforcement rules, violation cases, and proper usage patterns.

### Core Principle

> **ORCHESTRATOR-FIRST**: All agent execution MUST flow through the Orchestrator's queue. No exceptions.

---

## Enforcement Rules

### Rule 1: Queue Context Required

**Rule:** `agent.execute()` can ONLY be called within active queue context.

**Definition of "active queue context":**
- Code running inside `with QueueContextManager():`
- Code running inside Orchestrator's task processing loop
- Test code that explicitly activates context

**Violation:**
```python
# ❌ VIOLATES Rule 1 - No queue context
from orchestration.agents.queue_enforcement_middleware import QueueContextManager
from orchestration.agents.implementations import create_agent

agent = create_agent("engineer")  # OK - context not checked at factory
result = agent.execute(work_item)  # ❌ FAILS - No queue context
# QueueEnforcementError: Agent 'engineer' attempted to execute() outside queue context
```

**Compliant:**
```python
# ✅ COMPLIES with Rule 1 - Queue context active
from orchestration.agents.queue_enforcement_middleware import QueueContextManager
from orchestration.agents.implementations import create_agent

with QueueContextManager():  # Activate queue context
    agent = create_agent("engineer")  # OK
    result = agent.execute(work_item)  # OK - queue context active
```

---

### Rule 2: Explicit Context Marking Required for Tests

**Rule:** Test code MUST explicitly opt into queue context via `QueueContextManager`.

**Rationale:** Makes testing intent explicit. Prevents accidental bypasses.

**Violation:**
```python
# ❌ VIOLATES Rule 2 - Test code without context
def test_engineer_agent():
    engineer = create_agent("engineer")
    result = engineer.execute(test_item)  # ❌ FAILS - No context
```

**Compliant:**
```python
# ✅ COMPLIES with Rule 2 - Explicit context
def test_engineer_agent():
    with QueueContextManager():  # Explicit opt-in
        engineer = create_agent("engineer")
        result = engineer.execute(test_item)  # OK
        assert result.success
```

**Alternative (setup/teardown):**
```python
# ✅ Also compliant - Context in setup
class TestEngineerAgent:
    def setup_method(self):
        self.ctx = QueueContextManager()
        self.ctx.__enter__()
    
    def teardown_method(self):
        self.ctx.__exit__(None, None, None)
    
    def test_execution(self):
        engineer = create_agent("engineer")
        result = engineer.execute(test_item)  # OK
```

---

### Rule 3: Non-Execute Methods Always Allowed

**Rule:** Non-execute methods can be called regardless of queue context.

**Definition:** Methods other than `execute()`, properties, attributes.

**Examples of allowed calls:**
```python
with QueueContextManager():
    agent = create_agent("engineer")

# ✅ All these work regardless of context
config = agent.config
role = agent.role
validation = agent.validate_input()
doc = agent.__doc__
repr_str = repr(agent)
```

**Rationale:** Enables non-executing agent introspection without requiring queue context.

---

### Rule 4: Agent-to-Agent Delegation Within Context

**Rule:** Agents can create and execute other agents if within active queue context.

**Violation:**
```python
# ❌ VIOLATES Rule 4 - Agent delegate without context
class OrchestratorAgent(Agent):
    def do_work(self):
        # No queue context inherited!
        engineer = create_agent("engineer")
        result = engineer.execute(task)  # ❌ FAILS - No context
```

**Compliant:**
```python
# ✅ COMPLIES with Rule 4 - Explicit context
class OrchestratorAgent(Agent):
    def execute(self, work_item):
        with QueueContextManager():  # Activate context for delegation
            # Now sub-agents can execute
            engineer = create_agent("engineer")
            result = engineer.execute(task)  # OK
            return result
```

---

### Rule 5: Thread-Local Context Isolation

**Rule:** Queue context is thread-local and does NOT propagate across threads.

**Definition:** Each thread has its own independent queue context state.

**Example:**
```python
# Main thread: no context
assert not QueueContext.is_active()

def worker_thread():
    # Worker thread inherits no context
    assert not QueueContext.is_active()
    # Must activate context if needed
    with QueueContextManager():
        agent = create_agent("engineer")
        result = agent.execute(task)  # OK

thread = threading.Thread(target=worker_thread)
thread.start()
thread.join()
```

**Implication:** Async/threaded work must activate context in each thread.

---

## Violation Cases

### Case 1: Direct Execution Outside Orchestrator

**Pattern:**
```python
# ❌ Violation
from orchestration.agents.implementations import create_agent
agent = create_agent("engineer")
result = agent.execute(work_item)
```

**Reason:** Bypasses queue routing and audit trail. SPEC.md violation.

**Fix:**
```python
# ✅ Correct
with QueueContextManager():
    agent = create_agent("engineer")
    result = agent.execute(work_item)
```

---

### Case 2: Test Code Without Context

**Pattern:**
```python
# ❌ Violation
def test_agent():
    agent = create_agent("engineer")
    result = agent.execute(task)
```

**Reason:** Creates ambiguity about test execution context.

**Fix:**
```python
# ✅ Correct
def test_agent():
    with QueueContextManager():
        agent = create_agent("engineer")
        result = agent.execute(task)
```

---

### Case 3: Example Code Without Context

**Pattern:**
```python
# ❌ Violation
def example():
    agent = create_agent("engineer")
    result = agent.execute(work_item)
    return result
```

**Reason:** Sets bad example for developers.

**Fix:**
```python
# ✅ Correct
def example():
    with QueueContextManager():
        agent = create_agent("engineer")
        result = agent.execute(work_item)
        return result
```

---

### Case 4: Agent Delegation Without Context

**Pattern:**
```python
# ❌ Violation
class OrchestratorAgent(Agent):
    def do_work(self):
        sub = create_agent("engineer")
        result = sub.execute(task)
```

**Reason:** Sub-agents execute outside context.

**Fix:**
```python
# ✅ Correct
class OrchestratorAgent(Agent):
    def execute(self, work_item):
        with QueueContextManager():
            sub = create_agent("engineer")
            result = sub.execute(task)
            return result
```

---

## Proper Usage Patterns

### Pattern 1: Orchestrator Context Activation

The Orchestrator activates queue context for its entire task processing loop:

```python
class OrchestratorAgent(Agent):
    def execute(self, work_item):
        with QueueContextManager():  # Activate queue context once
            # All work in this loop has active context
            while True:
                task = self.queue.dequeue()
                if not task:
                    break
                
                # These all work (context is active)
                agent = create_agent(task.route)
                result = agent.execute(task)
                self.queue.mark_complete(task)
                
                yield result
```

---

### Pattern 2: Test Harness Context

Test code explicitly activates context for testing:

```python
# testing_harness.py
from orchestration.agents.queue_enforcement_middleware import QueueContextManager

def test_engineer_execution():
    with QueueContextManager():
        engineer = create_agent("engineer")
        result = engineer.execute({
            "task_id": "test-123",
            "scope": "small task",
            "plan": ["step 1", "step 2"]
        })
        assert result["status"] == "PASS"

def test_orchestrator_routing():
    with QueueContextManager():
        orchestrator = create_agent("orchestrator")
        result = orchestrator.execute({
            "task_id": "route-123",
            "scope": "complex work",
            "complexity": "high"
        })
        assert result["routing_decision"] == "senior_engineer"
```

---

### Pattern 3: Agent-to-Agent Delegation

An agent can delegate to other agents if within queue context:

```python
# Within QueueContextManager context
class LeadEngineerAgent(Agent):
    def execute(self, work_item):
        # This works because called from Orchestrator with active context
        # (Orchestrator activates context, calls execute())
        sub_agent = create_agent("engineer")
        for subtask in work_item["subtasks"]:
            result = sub_agent.execute(subtask)
            yield result
```

---

### Pattern 4: Non-Execute Method Access

Access agent configuration and metadata without context:

```python
# These work OUTSIDE queue context
agent = create_agent("engineer")
config = agent.config  # No context needed
role = agent.role
model = agent.config.model

# Only execute() requires context
# with QueueContextManager():
#     result = agent.execute(work_item)
```

---

## Error Messages & Debugging

### Understanding the Error

When you get `QueueEnforcementError`, the message provides:

1. **Which agent:** "Agent 'engineer' attempted to execute()..."
2. **What rule:** "outside queue context"
3. **Why it matters:** "SPEC.md lines 25-123 mandate ORCHESTRATOR-FIRST"
4. **How to fix (test code):** "Use QueueContextManager"
5. **How to fix (production):** "Route through Orchestrator.queue"

Example error message:
```
QueueEnforcementError: Agent 'engineer' attempted to execute() outside queue context.

REQUIREMENT: All agent execution must flow through the Orchestrator's queue.
See SPEC.md lines 25-123 (ORCHESTRATOR-FIRST EXECUTION MODEL).

TO FIX:
  • If this is test code:
      from orchestration.agents.queue_enforcement_middleware import QueueContextManager
      with QueueContextManager():
          agent = create_agent('engineer')
          result = agent.execute(work_item)

  • If this is production code:
      Route through Orchestrator.queue.enqueue() instead of direct execution.
      The Orchestrator will create and execute the agent in queue context.
```

---

## Compliance Checklist

Use this checklist when writing or reviewing code:

- [ ] Is `agent.execute()` called within `QueueContextManager()`?
- [ ] Does test code explicitly activate context?
- [ ] Does example code show proper context usage?
- [ ] Are non-execute methods called without context (when appropriate)?
- [ ] Does agent delegation happen within active context?
- [ ] Are error messages clear when violations occur?
- [ ] Is queue context thread-local isolation respected?
- [ ] Have all tests passed?

---

## Enforcement Levels

The enforcement is layered:

### Level 1: Factory Validation (Early Detection)
`create_agent()` checks context at call time. *(Currently not enforced, but available)*

### Level 2: Proxy Enforcement (Execution Time)
`QueueEnforcingProxy.execute()` checks context before forwarding. *(PRIMARY ENFORCEMENT)*

### Level 3: Error Messages (Guidance)
Clear, actionable error messages guide developers to correct usage. *(ALWAYS ACTIVE)*

### Level 4: Logging (Audit Trail)
`QueueEnforcementLogger` records all enforcement events. *(Optional, for debugging)*

---

## FAQ

### Q: Why is direct agent execution not allowed?

**A:** SPEC.md requires all work to flow through the Orchestrator for:
- Centralized routing and scheduling
- Audit trail and observability
- Consistency and reliability
- Cost control and token management

### Q: Why can test code bypass the requirement?

**A:** Test code needs explicit context marking to:
- Make testing intent clear
- Allow unit testing of agents
- Avoid false positives in test infrastructure
- Provide explicit opt-in mechanism

### Q: Does non-execute work need context?

**A:** No. Only `execute()` requires context. Configuration, metadata, validation can be done without context.

### Q: What about agent-to-agent delegation?

**A:** Allowed if the parent agent is executing within queue context (inherited from Orchestrator).

### Q: How do I migrate existing code?

**A:** See docs/queue-enforcement-migration-guide.md for step-by-step instructions.

---

## Related Documents

- **SPEC.md** (lines 25-123): ORCHESTRATOR-FIRST constraint definition
- **docs/architecture-queue-enforcement-5101.md**: Architecture design
- **docs/queue-enforcement-migration-guide.md**: How to fix violations
- **orchestration/agents/queue_enforcement_middleware.py**: Implementation
- **orchestration/agents/test_queue_enforcement.py**: Test suite

---

## Summary

Queue enforcement ensures:
✅ All agent work flows through Orchestrator  
✅ Clear audit trail for all executions  
✅ Centralized routing and scheduling  
✅ Easy detection and prevention of violations  
✅ Clear guidance when violations occur  
✅ Zero impact on legitimate usage  
