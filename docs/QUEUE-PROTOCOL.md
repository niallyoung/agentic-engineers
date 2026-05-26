# Queue-Based Delegation Mechanics

⚠️ **SPECIFICATION LOCKED (2026-05-26)**

This specification is LOCKED as of 2026-05-26. The canonical queue path is `~/.agentic-engineers/`.

**Key Facts:**
- All 4 harnesses (copilot, claude, opencode, pi) use the SAME base directory: `~/.agentic-engineers/{session-id}/{harness}/queue/`
- Legacy paths (~.copilot/queue, ~/.claude/queue, artifacts/queue) are DEPRECATED and UNSUPPORTED
- Queue-isolation skill REQUIRED (no fallback logic)
- Changes to queue paths require approval via **spec-management skill**

See **docs/SPEC.md - Queue Architecture & Paths (LOCKED SPEC)** for full specification and enforcement rules.

---

# Queue-Based Delegation Mechanics (Details)

Simple file-based queue system for DELEGATE/HANDBACK protocol. Enables agent-based delegation workflow via queue instead of direct messages. Each Copilot or Claude session has its own isolated queue, identified by session-id.

**CANONICAL EXECUTION MODEL:** Orchestrator agent continuously polls `~/.agentic-engineers/artifacts/{session-id}/{harness}/queue/incoming/` for new DELEGATE blocks, routes tasks to appropriate agents via AGENTS.md decision tree, processes HANDBACK results, and manages queue state transitions. **This is the ONLY way work flows through agentic-engineers.**

All harnesses (Claude, Copilot, GPT, Local) use the same canonical directory structure under `~/.agentic-engineers/artifacts/`.

---

## Queue Structure (All Harnesses - Unified)

**As of 2026-05-26:** All harnesses (Claude, Copilot, GPT, Local) use the same canonical directory structure.

```
~/.agentic-engineers/
└── artifacts/
    └── {session-id}/                   # UUID: unique per session
        ├── claude/                     # Claude harness
        │   ├── metadata.json           # Harness metadata
        │   └── queue/
        │       ├── incoming/           # New work, ready for Orchestrator
        │       ├── processing/         # Work assigned to agent, awaiting HANDBACK
        │       ├── done/               # Completed work, ready for decision
        │       └── failed/             # Errored tasks
        ├── copilot/                    # GitHub Copilot harness
        │   ├── metadata.json
        │   └── queue/
        │       ├── incoming/
        │       ├── processing/
        │       ├── done/
        │       └── failed/
        ├── gpt/                        # OpenAI GPT harness
        │   ├── metadata.json
        │   └── queue/ ...
        └── local/                      # Local harness
            ├── metadata.json
            └── queue/ ...
    └── {other-session-id}/             # Other session
        ├── claude/ ...
        ├── copilot/ ...
        └── ...
```

**Legacy Structure (Deprecated):**
```
~/.copilot/queue/          ❌ NO LONGER SUPPORTED
~/.claude/queue/           ❌ NO LONGER SUPPORTED
artifacts/queue/           ❌ NO LONGER SUPPORTED (was local repo artifact path)
```

**Migration completed:** All tasks from legacy paths are migrated to canonical path.
Queue-isolation skill provides mandatory isolation. No backward compatibility.

---

## How It Works

### 1. Incoming Queue

**New task arrives as:** `~/.agentic-engineers/artifacts/{session-id}/{harness}/queue/incoming/{task_id}.yaml`

Example path: `~/.agentic-engineers/artifacts/54744939-4acb-430c-b2c4-3b8322289d0b/claude/queue/incoming/2026-04-30-fix-token-timeout.yaml`

```yaml
---
task_id: 2026-04-30-fix-token-timeout
description: "Fix token validation timeout in {example-service}"
priority: high
# (Simple task description; Orchestrator will create DELEGATE)
---
```

**Orchestrator agent (running in harness) polls `{session-id}/incoming/` every 30-60s and:**
1. Reads task
2. Applies AGENTS.md routing rules
3. Creates DELEGATE (HANDOFF.md format)
4. Stores DELEGATE in `artifacts/delegates/YYYY-MM-DD/`
5. Sends DELEGATE to appropriate agent
6. Deletes from `{session-id}/incoming/` (or moves to archive)

### 2. Processing Queue

**Agent returns work as:** `~/.agentic-engineers/artifacts/{session-id}/{harness}/queue/processing/{task_id}-HANDBACK-{role}.yaml`

Example path: `~/.agentic-engineers/artifacts/54744939-4acb-430c-b2c4-3b8322289d0b/claude/queue/processing/2026-04-30-fix-token-timeout-HANDBACK-engineer.yaml`

```yaml
---
handoff_type: HANDBACK
task_id: 2026-04-30-fix-token-timeout
status: complete | blocked | partial
deliverables: [...]
tests: [...]
tokens_in: 1200
tokens_out: 820
model: claude-haiku-4-5
effort: high
duration_minutes: 18
escalations: 0
---
```

**Orchestrator agent polls `{session-id}/processing/` and:**
1. Routes complete work to Quality Engineer
2. Escalates blocked work to Lead/Senior Engineer
3. Moves to `{session-id}/done/` after decision

### 3. Done Queue

**Final decision stored as:** `~/.agentic-engineers/artifacts/{session-id}/{harness}/queue/done/{task_id}-{decision}.yaml`

Example path: `~/.agentic-engineers/artifacts/54744939-4acb-430c-b2c4-3b8322289d0b/claude/queue/done/2026-04-30-fix-token-timeout-PROCEED.yaml`

```yaml
task_id: 2026-04-30-fix-token-timeout
decision: PROCEED | REWORK | ESCALATE
notes: "Quality Engineer verified; ready to merge"
```

**Human/external system reads from `{session-id}/done/` for:**
- Merge decisions (PROCEED)
- Rework notifications (REWORK)
- Escalation alerts (ESCALATE)

---

## Orchestrator Agent Behavior

Orchestrator is a harness agent (defined in AGENTS.md) that:

1. **Runs continuously** (loop in harness or periodic invocation)
2. **Polls queues** every 30-60 seconds
3. **Routes work** using AGENTS.md decision tree
4. **Creates DELEGATEs** in HANDOFF.md format
5. **Sends to agents** via harness (Claude Code or equiv.)
6. **Manages transitions** (incoming → processing → done)
7. **Applies recommendations** from Model Engineer feedback loop

**No external tools**, no cron jobs, no shell scripts — 100% agent-based.

---

## Session-ID Based Partitioning

Each Copilot or Claude session has its own isolated queue, identified by a unique session-id (UUID). This ensures that multiple simultaneous Copilot/Claude instances don't interfere with each other's tasks.

### Session-ID Detection

The Orchestrator detects the session-id using the following priority:

1. **COPILOT_SESSION_ID Environment Variable** (highest priority)
   - Set automatically by Copilot CLI runtime
   - Example: `export COPILOT_SESSION_ID=54744939-4acb-430c-b2c4-3b8322289d0b`

2. **CLAUDE_SESSION_ID Environment Variable**
   - Set automatically by Claude runtime (if running in Claude context)
   - Example: `export CLAUDE_SESSION_ID=...`

3. **Filesystem Scan** (lowest priority)
   - Scan `~/.copilot/session-state/` or `~/.claude/session-state/`
   - Find the most recently modified session directory
   - Use its directory name (UUID) as the session-id
   - Example: `~/.copilot/session-state/54744939-4acb-430c-b2c4-3b8322289d0b/`

### Multiple Simultaneous Sessions

When multiple harnesses run concurrently, each harness gets a unique queue partition within its session:

```
~/.agentic-engineers/artifacts/
├── 54744939-4acb-430c-b2c4-3b8322289d0b/     # Session 1
│   ├── claude/
│   │   └── queue/
│   │       ├── incoming/ ← Claude tasks for session 1
│   │       ├── processing/
│   │       └── done/
│   └── copilot/
│       └── queue/
│           ├── incoming/ ← Copilot tasks for session 1
│           ├── processing/
│           └── done/
├── 606ff436-b44b-47c5-90b8-f4bcc3fdb413/     # Session 2
│   ├── claude/
│   │   └── queue/ ...
│   └── copilot/
│       └── queue/ ...
```

Each harness's Orchestrator only polls and processes its own queue partition. No cross-contamination, no race conditions.

---

## Migration History (Completed 2026-05-26)

⚠️ **Queue path consolidation is COMPLETE.** Legacy paths are NO LONGER SUPPORTED.

**Historical:** Phases 1-4 involved gradual migration from:
- `~/.copilot/queue/` → ❌ DEPRECATED
- `~/.claude/queue/` → ❌ DEPRECATED
- `artifacts/queue/` → ❌ DEPRECATED

**Current:** All harnesses now use the canonical path:
- `~/.agentic-engineers/artifacts/{session-id}/{harness}/queue/` ✅ REQUIRED

If you encounter legacy path references, ensure the queue-isolation skill is properly initialized. See `src/skills/_meta/queue-isolation/SKILL.md` for configuration details.

---

## DELEGATE/HANDBACK Storage

| Artifact | Path | Created By | Used By |
|----------|------|-----------|---------|
| DELEGATE | `~/.agentic-engineers/artifacts/{session-id}/{harness}/YYYY-MM-DD/DELEGATE-{task_id}-{role}.yaml` | Orchestrator | Agent (receives), Orchestrator (ref) |
| HANDBACK | `~/.agentic-engineers/artifacts/{session-id}/{harness}/queue/processing/{task_id}-HANDBACK-{role}.yaml` | Agent | Orchestrator (routes), QE (verifies) |
| Decision | `~/.agentic-engineers/artifacts/{session-id}/{harness}/queue/done/{task_id}-{decision}.yaml` | Orchestrator | Human / external system |

**DELEGATE Format (from HANDOFF.md):**
```yaml
handoff_type: DELEGATE
task_id: {unique_id}
role: Engineer | Senior Engineer | Lead Engineer | ...
model: claude-haiku-4-5 | claude-sonnet-4-6 | ...
effort: low | medium | high | max
scope: "Clear one-sentence scope + out-of-scope"
context: [...]
success_criteria: [...]
plan: [...]  # Required for Engineer; steps should include Red-Green TDD phases for code changes
```

**HANDBACK Format (from HANDOFF.md):**
```yaml
handoff_type: HANDBACK
task_id: {matching_delegate_task_id}
status: complete | blocked | partial
deliverables: [...]
tests: [...]
tokens_in: estimate
tokens_out: estimate
model: actual_model_used
effort: actual_effort
duration_minutes: wall_clock_time
escalations: count
```

---

## File Naming

| Queue | Format | Example |
|-------|--------|---------|
| incoming | `{task_id}.yaml` | `2026-04-30-fix-token-timeout.yaml` |
| processing | `{task_id}-HANDBACK-{role}.yaml` | `2026-04-30-fix-token-timeout-HANDBACK-Engineer.yaml` |
| done | `{task_id}-{decision}.yaml` | `2026-04-30-fix-token-timeout-PROCEED.yaml` |

---

## Integration with AGENTS.md

Orchestrator uses AGENTS.md to:
- Apply routing decision tree (which role for which task)
- Select model/effort combo
- Handle escalations and blocked tasks
- Apply Model Engineer recommendations

```yaml
# Orchestrator logic in AGENTS.md:
Routing Decision Tree:
1. Is task security-scoped? → Security Engineer
2. Is task cross-service? → Principal Engineer  
3. Is task complex without plan? → Senior Engineer (to write plan)
4. Is task code review? → Lead Engineer or Quality Engineer
5. Is task well-scoped? → Engineer
```

---

## Integration with SKILLS.md

Each agent role (Engineer, Senior Engineer, etc.) has SKILLS section:
- How to execute their role
- Quality standards
- Escalation triggers
- Specific workflows (Red-Green TDD for Engineer, etc.)

Agent reads SKILLS.md when receiving DELEGATE, ensuring consistent execution.

---

## Escalation & Rework Paths

**Blocked Task:**
- Agent returns HANDBACK with `status: blocked`
- Orchestrator reads blocker reason
- Escalates to Lead Engineer or Senior Engineer (per AGENTS.md)
- Lead Engineer unblocks with guidance or revised plan

**Quality Issues (QE Rejection):**
- Quality Engineer rejects HANDBACK (quality gate failed)
- Orchestrator creates new DELEGATE with QE feedback
- Task returns to `incoming/` for rework
- Retry limit per AGENTS.md (typically 3 attempts before escalate)

---

## Optional: Archive & Historical Lookup

After task leaves `done/`:

```
artifacts/archive/YYYY-MM-DD/{task_id}/
├── DELEGATE.yaml
├── HANDBACK.yaml
└── QE_FEEDBACK.yaml (if applicable)
```

Used for:
- Pattern analysis (Model Engineer: which models suit which task types?)
- Historical trends (cost, rejection rates, etc.)
- Task replay (if needed, re-run with updated code)

---

## Future: Database Migration

This queue is file-based for simplicity. Can later migrate to:
- NoSQL (DynamoDB, Firestore)
- SQL (PostgreSQL, MySQL)
- Message queue (SQS, Kafka)

API layer would then sit atop the database, replacing file I/O.

---

## Summary

Queue system = **indirect delegation via files** instead of direct agent-to-agent messages.

Benefits:
- ✅ Decouples agents (they don't need to know about each other)
- ✅ Enables batch processing (queue can hold multiple pending tasks)
- ✅ Auditable (all DELEGATE/HANDBACK stored)
- ✅ Durable (tasks persist if harness restarts)
- ✅ Agent-based (Orchestrator polls; no external tools needed)

Orchestrator implementation = AGENTS.md + SKILLS.md. See those docs for:
- Routing rules (AGENTS.md > Routing Decision Tree)
- Escalation rules (AGENTS.md > Constraints)
- Execution details (SKILLS.md > Orchestrator Skills)


---

## Queue Enforcement Rules

> Source: queue-enforcement-rules.md (consolidated here)

### Core Principle: ORCHESTRATOR-FIRST

> All agent execution MUST flow through the Orchestrator's queue. No exceptions.

### Rule 1: Queue Context Required

`agent.execute()` can ONLY be called within active queue context.

```python
# ❌ Violates Rule 1 — No queue context
agent = create_agent("engineer")
result = agent.execute(work_item)  # QueueEnforcementError

# ✅ Compliant — Queue context active
with QueueContextManager():
    agent = create_agent("engineer")
    result = agent.execute(work_item)  # OK
```

### Rule 2: Explicit Context Marking in Tests

Test code MUST explicitly opt into queue context via `QueueContextManager`. Makes testing intent explicit; prevents accidental bypasses.

```python
# ✅ Compliant
def test_engineer_agent():
    with QueueContextManager():
        engineer = create_agent("engineer")
        result = engineer.execute(test_item)
        assert result.success
```

### Rule 3: Non-Execute Methods Always Allowed

Non-execute methods (`status()`, `get_capabilities()`, etc.) can be called regardless of queue context.

### Violation Handling

| Violation | Error | Resolution |
|-----------|-------|-----------|
| execute() outside context | `QueueEnforcementError` | Wrap with `QueueContextManager()` |
| Test without context | `QueueEnforcementError` | Add explicit context to test |
| Direct instantiation bypass | `QueueEnforcementError` | Use `create_agent()` factory only |

---

## Queue Enforcement Migration Guide

> Source: queue-enforcement-migration-guide.md (consolidated here)

### 3-Step Fix for QueueEnforcementError

**Step 1:** Add import
```python
from orchestration.agents.queue_enforcement_middleware import QueueContextManager
```

**Step 2:** Wrap execution
```python
# Before
agent = create_agent("engineer")
result = agent.execute(work_item)

# After
with QueueContextManager():
    agent = create_agent("engineer")
    result = agent.execute(work_item)
```

**Step 3:** Verify
```bash
python3 -m pytest orchestration/agents/test_queue_enforcement.py -v
```

### Test Harness Pattern

```python
from orchestration.agents.queue_enforcement_middleware import QueueContextManager

class TestEngineerAgent:
    def setup_method(self):
        self.ctx = QueueContextManager()
        self.ctx.__enter__()

    def teardown_method(self):
        self.ctx.__exit__(None, None, None)

    def test_execution(self):
        engineer = create_agent("engineer")
        result = engineer.execute(test_item)
        assert result.success
```

### Orchestrator Integration Pattern

```python
with QueueContextManager():
    while orchestrator.has_pending_tasks():
        task = orchestrator.dequeue()
        agent = create_agent(task.role)
        handback = agent.execute(task.work_item)
        orchestrator.process_handback(handback)
```

---

## Queue Enforcement Implementation Reference

> Source: queue-enforcement-implementation-guide.md (consolidated here)
> See: `orchestration/agents/queue_enforcement_middleware.py` for the implementation.

### Key Classes

| Class | Purpose |
|-------|---------|
| `QueueContext` | Thread-local singleton tracking active context state |
| `QueueContextManager` | Context manager: activates/deactivates queue context |
| `QueueEnforcementError` | Exception raised when execute() called outside context |
| `QueueEnforcingProxy` | Transparent proxy wrapping agents to enforce queue rules |

### create_agent() Factory (implementations.py)

The factory wraps every returned agent in `QueueEnforcingProxy`:

```python
def create_agent(role):
    if role not in AGENTS:
        raise ValueError(f"Unknown role: {role}")
    agent = AGENTS[role]()
    return QueueEnforcingProxy(agent)   # Enforcement wrapper
```

### Validation

```bash
python3 -m pytest orchestration/agents/test_queue_enforcement.py -v
python3 -m pytest orchestration/agents/test_queue_state_transitions.py -v
```
