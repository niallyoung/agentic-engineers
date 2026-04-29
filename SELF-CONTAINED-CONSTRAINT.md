# Self-Contained Constraint

**Critical Architectural Decision:** agentic-engineers is a FULLY SELF-CONTAINED system with ZERO external dependencies.

---

## What This Means

### ✅ agentic-engineers IS:

1. **Agent-driven orchestration system**
   - All work flows between agents
   - Agents delegate to agents via DELEGATE/HANDBACK protocol
   - No agent calls external systems

2. **Model-agnostic**
   - Agents are implemented as other agents
   - Recursion depth: agents → agents → agents
   - No actual Claude API calls (that's outside this system)

3. **Self-contained**
   - Zero external integrations
   - No APIs, no shell scripts, no services
   - All computation is internal DELEGATE/HANDBACK exchanges

4. **Fully internal**
   - Artifact files only (DELEGATE/HANDBACK/FEEDBACK blocks)
   - All communication is structured YAML/JSON
   - No stdio, no environment variables, no CLI

---

### ❌ agentic-engineers IS NOT:

1. **An API system**
   - ❌ No Claude API calls
   - ❌ No REST APIs
   - ❌ No gRPC, no HTTP, no network

2. **A shell/script system**
   - ❌ No bash, no python subprocess
   - ❌ No tool execution
   - ❌ No `os.system()`, no `subprocess.run()`

3. **Cloud-dependent**
   - ❌ No AWS services
   - ❌ No GitHub API
   - ❌ No external auth/secrets

4. **A build/deployment system**
   - ❌ No `make`, no `docker`, no CI/CD
   - ❌ No code execution
   - ❌ No artifact building

5. **An LLM client**
   - ❌ Not for calling Claude
   - ❌ Not for calling any model API
   - ❌ Not for prompting

---

## Example: What to Do vs What NOT to Do

### ❌ WRONG: Agent calls Claude API

```python
# FORBIDDEN - breaks self-contained constraint
def do_work(self) -> Dict:
    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-opus-4-7",
        messages=[{"role": "user", "content": "analyze this..."}]
    )
    return {"result": response.text}
```

### ✅ CORRECT: Agent delegates to sub-agent

```python
# CORRECT - agent-to-agent delegation
def do_work(self) -> Dict:
    # Decide which sub-agent handles this
    sub_agent_role = "threat_modeler"
    
    # Build DELEGATE for sub-agent
    delegate = {
        "handoff_type": "DELEGATE",
        "task_id": self.task_id,
        "role": sub_agent_role,
        "scope": self.delegate_block.get("scope")
    }
    
    # Delegate (sub-agent is another agent in our system)
    from implementations import create_agent
    agent = create_agent(sub_agent_role)
    handback = agent.execute(delegate)
    
    # Return result from sub-agent
    return handback
```

---

### ❌ WRONG: Agent executes shell command

```python
# FORBIDDEN - breaks self-contained constraint
def do_work(self) -> Dict:
    import subprocess
    result = subprocess.run(["make", "test"], capture_output=True)
    return {"tests_passed": result.returncode == 0}
```

### ✅ CORRECT: Agent delegates to test-execution agent

```python
# CORRECT - agent-to-agent delegation
def do_work(self) -> Dict:
    # Delegate testing to test-execution agent
    delegate = {
        "handoff_type": "DELEGATE",
        "task_id": self.task_id,
        "role": "test_executor",
        "scope": "Run test suite"
    }
    
    from implementations import create_agent
    agent = create_agent("test_executor")
    handback = agent.execute(delegate)
    
    return handback
```

---

### ❌ WRONG: Agent uses environment variables

```python
# FORBIDDEN - breaks self-contained constraint
import os

def do_work(self) -> Dict:
    api_key = os.getenv("GITHUB_TOKEN")
    # Use api_key to call GitHub...
```

### ✅ CORRECT: Agent receives all context via DELEGATE

```python
# CORRECT - all context from DELEGATE block
def do_work(self) -> Dict:
    # DELEGATE block contains everything needed
    context = self.delegate_block.get("context", {})
    credentials = context.get("credentials", {})
    
    # Use what was passed in
    return {"status": "processed"}
```

---

## Implications

### 1. Agent Implementation

Every agent's `do_work()` method must:
- ✅ Extract inputs from `self.delegate_block`
- ✅ Validate inputs (raise ValueError if invalid)
- ✅ Determine sub-agents to delegate to
- ✅ Build DELEGATE blocks for sub-agents
- ✅ Call `create_agent(role).execute(delegate)` for each sub-agent
- ✅ Parse HANDBACK from sub-agents
- ✅ Return structured HANDBACK dict

### 2. Testing

Tests must:
- ✅ Create test DELEGATE blocks
- ✅ Execute agents with those blocks
- ✅ Inspect returned HANDBACK blocks
- ✅ Write artifacts to disk for audit trail
- ❌ NOT call external services
- ❌ NOT shell out to anything
- ❌ NOT use environment variables

### 3. Data Flow

```
Outside System
  │ (DELEGATE block written to disk)
  ▼
agentic-engineers
  │ Agent A receives DELEGATE
  │ A decides to delegate to B, C, D
  │ A builds 3 DELEGATE blocks
  │ ├─→ B.execute(delegate_b) → HANDBACK_B
  │ ├─→ C.execute(delegate_c) → HANDBACK_C
  │ └─→ D.execute(delegate_d) → HANDBACK_D
  │ A parses HAN[DBACK]s, generates its own HANDBACK
  ▼
Outside System
  │ (HANDBACK block written to disk)
  ▼
```

All communication is DELEGATE/HANDBACK blocks. Nothing else crosses the boundary.

### 4. Spec Implications

SPEC.md must describe:
- ✅ Agent roles and responsibilities (what each agent decides & delegates)
- ✅ DELEGATE/HANDBACK structure (data contracts)
- ✅ Routing tree (which agent delegates to which)
- ✅ Confidence algorithm (how agents calculate confidence)
- ✅ Feedback loops (how FEEDBACK flows between agents)

SPEC.md must NOT describe:
- ❌ External API calls
- ❌ Shell commands
- ❌ Environment setup
- ❌ Build processes

### 5. What "Agent Implementation" Means

**NOT:** "Replace stub with Claude API call"

**CORRECTLY:** "Replace stub with delegation to appropriate sub-agent(s)"

Example:
- SecurityEngineerAgent's `do_work()`:
  - Decides work is "threat modeling"
  - Delegates to ThreatModelingAgent (another agent in the system)
  - ThreatModelingAgent maybe delegates to VulnerabilityAnalysisAgent
  - Eventually some agent returns results
  - SecurityEngineerAgent composes final HANDBACK

### 6. Testing Implications

Testing doesn't execute external code:
```python
# Test doesn't need real implementations
# Just needs agents to exist and return HANDBACKs

def test_orchestrator_routing():
    delegate = {...}
    orch = create_agent("orchestrator")
    handback = orch.execute(delegate)
    assert handback["routing_decision"] in ["engineer", "senior_engineer", ...]
    assert handback["status"] in ["PASS", "ESCALATE"]
```

---

## Why This Constraint?

1. **Autonomy:** System doesn't depend on external services being up
2. **Auditability:** Every decision is an artifact (DELEGATE/HANDBACK blocks)
3. **Composability:** Agents can be replaced/upgraded without changing others
4. **Testability:** No mocking of external services needed
5. **Portability:** No cloud provider lock-in, no credentials needed
6. **Future flexibility:** External integration happens at boundary, not internally

---

## What Changes This Enables

When agentic-engineers is **completely implemented as agent-to-agent delegation**, it becomes:

1. **Pluggable into any external system**
   - External system writes DELEGATE blocks
   - agentic-engineers processes them
   - External system reads HANDBACK blocks
   - No coupling, clean boundary

2. **Replaceable by real Claude integration**
   - One day: agents delegate to agents
   - Another day: agents delegate to Claude API
   - Implementation detail, not architecture

3. **Measurable and optimizable**
   - Every DELEGATE/HANDBACK pair is a data point
   - Analyze patterns, bottlenecks, costs
   - Optimize agent routing without changing spec

---

## Enshrinement

This constraint is **permanent** for agentic-engineers:

- ✅ Specified in SPEC.md (Section 🔒 Constraint)
- ✅ Enforced in AGENT-IMPLEMENTATION-TEMPLATE.py
- ✅ Validated by spec_validator.py (TYPE_D check)
- ✅ Documented in every agent spec
- ✅ In README.md, GETTING-STARTED.md, all guides

**Every new agent, every implementation, every test must follow this constraint.**

---

## Summary

**agentic-engineers is pure agent orchestration. All work is delegation. No external calls.**

This is not a limitation—it's the core strength. It's what makes the system:
- Auditable (every decision is logged)
- Composable (agents can be replaced)
- Testable (no mocking needed)
- Portable (no external dependencies)
- Future-proof (ready for any integration)
