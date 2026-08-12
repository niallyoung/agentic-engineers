# Queue-Based Delegation Mechanics

⚠️ **SPECIFICATION LOCKED (2026-05-26)**

This specification is LOCKED as of 2026-05-26. The canonical queue path is `~/.agentic-engineers/`.

**Key Facts:**
- All 4 harnesses (copilot, claude, opencode, pi) use the SAME base directory: `~/.agentic-engineers/{harness}/{session-id}/queue/`
- Legacy paths (~.copilot/queue, ~/.claude/queue, artifacts/queue) are DEPRECATED and UNSUPPORTED
- Queue-isolation skill REQUIRED (no fallback logic)
- Changes to queue paths require approval via **spec-management skill**

See **docs/SPEC.md - Queue Architecture & Paths (LOCKED SPEC)** for full specification and enforcement rules.

---

# Queue-Based Delegation Mechanics (Details)

Simple file-based **audit trail** for the DELEGATE/HANDBACK protocol — not the
delegation mechanism itself (see below). Each harness/session pair has its own
isolated queue, identified by session-id.

**CANONICAL EXECUTION MODEL:** The spawning agent (the Orchestrator, or any other
role whose frontmatter grants `spawn_subagent` — see `src/AGENTS.md`'s
Tools-Frontmatter Permission Model) builds a DELEGATE and dispatches it by
directly spawning a sub-agent with the DELEGATE as its prompt, reading the
HANDBACK back from the tool result — no timer, no poll interval, no intermediate
queue hop (see `docs/SPEC.md`'s ORCHESTRATOR-FIRST EXECUTION MODEL). The queue
described in this document is a durable audit substrate: every DELEGATE (at
spawn) and every HANDBACK (at completion) is recorded there via `enqueue()`.
**All work is routed through the Orchestrator by convention** (see
`src/AGENTS.md` > Orchestrator Entry Point) — the queue records the resulting
DELEGATEs/HANDBACKs regardless of which role spawned them.

All harnesses (Claude, Copilot, GPT, Local) use the same canonical directory structure under `~/.agentic-engineers/`.

---

## Queue Structure (All Harnesses - Unified)

**As of 2026-05-26:** All harnesses (Claude, Copilot, GPT, Local) use the same canonical directory structure.

Canonical path (matches `get_queue_path()` in
`src/skills/queue-management/scripts/queue_ops.py`): **harness outer,
session-id inner** — `~/.agentic-engineers/{harness}/{session-id}/queue/`.

```
~/.agentic-engineers/
├── claude/                             # Claude harness
│   ├── {session-id}/                   # UUID: unique per session
│   │   ├── metadata.json               # Harness metadata
│   │   └── queue/
│   │       ├── incoming/               # New work, ready for Orchestrator
│   │       ├── processing/             # Work assigned to agent, awaiting HANDBACK
│   │       ├── done/                   # Completed work, ready for decision
│   │       └── failed/                 # Errored tasks
│   └── {other-session-id}/ ...
├── copilot/                            # GitHub Copilot harness
│   └── {session-id}/
│       ├── metadata.json
│       └── queue/
│           ├── incoming/
│           ├── processing/
│           ├── done/
│           └── failed/
├── opencode/                           # OpenCode harness
│   └── {session-id}/
│       ├── metadata.json
│       └── queue/ ...
└── pi/                                 # Pi.dev harness
    └── {session-id}/
        ├── metadata.json
        └── queue/ ...
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

**New task arrives as:** `~/.agentic-engineers/{harness}/{session-id}/queue/incoming/{task_id}.yaml`

Example path: `~/.agentic-engineers/claude/54744939-4acb-430c-b2c4-3b8322289d0b/queue/incoming/2026-04-30-fix-token-timeout.yaml`

```yaml
---
task_id: 2026-04-30-fix-token-timeout
description: "Fix token validation timeout in {example-service}"
priority: high
# (Simple task description; Orchestrator will create DELEGATE)
---
```

**Orchestrator drains `{session-id}/incoming/` at context start and after each task completes (no timer, no poll interval) and:**
1. Reads task
2. Applies AGENTS.md routing rules
3. Constructs the DELEGATE block per the DELEGATE/HANDBACK Protocol format
4. Spawns a sub-agent directly with the DELEGATE as its prompt
5. Records the DELEGATE via `enqueue()` for audit
6. Marks the item processed in `{session-id}/incoming/` (moved/archived)

### 2. Processing Queue

**`enqueue()` writes the HANDBACK as:** `~/.agentic-engineers/{harness}/{session-id}/queue/processing/{task_id}.yaml`

Example path: `~/.agentic-engineers/claude/54744939-4acb-430c-b2c4-3b8322289d0b/queue/processing/2026-04-30-fix-token-timeout.yaml`

```yaml
---
handoff_type: HANDBACK
task_id: 2026-04-30-fix-token-timeout
status: success | failure | partial | blocked | escalate
output: "Summary of what was done"
metrics:
  quality: 0.9
  tokens: 2020
  cost: 0.02
  duration_seconds: 1080
---
```

**The spawning agent reads the HANDBACK directly from the spawn's tool result** (the
write above is the audit copy, recorded via `enqueue()` after the fact — see
[`src/AGENTS.md` > Audit-Trail Strategy](../src/AGENTS.md#audit-trail-strategy)) and
applies the routing decision per `status` (see
[`docs/PROTOCOL.md` §4](PROTOCOL.md#4-quality-assessment)). Convention, not
automatic: the spawning agent MAY additionally spawn Quality Engineer to review the
HANDBACK before deciding.

### 3. Done Queue

There is no automatic `incoming/`→`processing/`→`done/` transition — `enqueue()`
only ever writes to `incoming/` (DELEGATE) or `processing/` (HANDBACK). Moving a
task's audit record to `done/` (or `failed/`) is an explicit
`QueueOperations.move_task(task_id, from_state, to_state)` call by whichever agent
decided the task is finished, and preserves the filename
(`~/.agentic-engineers/{harness}/{session-id}/queue/done/{task_id}.yaml`). There is
no separate machine-readable "decision" artifact (`PROCEED`/`REWORK`/`ESCALATE`) —
the HANDBACK's own `status` field is the decision signal; a human or external
system reading `{session-id}/done/` reads that field directly.

---

## Orchestrator Agent Behavior

Orchestrator is a harness agent (defined in AGENTS.md) that:

1. **Runs in agent context** (a live Orchestrator session, not a background loop)
2. **Drains queues** at context start and after each task completes — no timer, no poll interval
3. **Routes work** using AGENTS.md decision tree
4. **Constructs DELEGATEs** per the DELEGATE/HANDBACK Protocol format
5. **Dispatches by direct sub-agent spawn** (harness Agent/Task tool), reading the HANDBACK from the tool result
6. **Manages transitions** (incoming → processing → done) and records them via `enqueue()` for audit
7. **Applies recommendations** from Model Engineer feedback loop

**No external tools**, no cron jobs, no shell scripts — 100% agent-based.

---

## Escalation Chaining

When an agent returns a HANDBACK with `status: escalate`, it embeds an
**ESCALATION packet** (`from_role`, `to_role`, `reason`, `findings_so_far`,
`recommended_focus`) under the HANDBACK's `escalation:` key. The receiving agent
(whichever role spawned the escalating agent — typically the Orchestrator) reads
it in-context, builds a new DELEGATE targeting `to_role` with the escalation
content inlined in `context`, appends its own role to `ancestry`, and spawns
`to_role` directly. The full packet format, the worked example (Engineer → Senior
→ Lead), and the depth/fan-out/cycle checks that bound this chain (max delegation
depth 3, `ancestry`-based cycle detection) are defined once, canonically, in
[`src/AGENTS.md` > ESCALATION Packet
Format](../src/AGENTS.md#escalation-packet-format) and [Recursion
Limits](../src/AGENTS.md#recursion-limits) — not duplicated here.

This document's concern is only the audit-trail side of that chain: both the
original HANDBACK (with its embedded `escalation:` block) and the new DELEGATE it
produces are `enqueue()`d exactly like any other DELEGATE/HANDBACK — the escalation
hop leaves the same `incoming/`+`processing/` trail as a normal spawn, one entry
per hop. `ancestry` growing by one role per hop is what keeps
`queue-management`'s cycle detection (`has_cycle()`, `exceeds_max_depth()`)
accurate across an escalation chain, the same as for ordinary sub-tasks.

---

## Session-ID Based Partitioning

Each Copilot or Claude session has its own isolated queue, identified by a unique session-id (UUID). This ensures that multiple simultaneous Copilot/Claude instances don't interfere with each other's tasks.

### Session-ID and Harness Detection

`queue_ops.py`'s `get_session_id()` and `detect_harness()` resolve these purely
from environment variables — no filesystem scan:

**Session ID priority:** `AGENTIC_SESSION_ID` > `CLAUDE_SESSION_ID` >
`COPILOT_SESSION_ID` > a freshly generated `uuid.uuid4()` if none are set.

**Harness priority:** `AGENTIC_HARNESS` (explicit override) > `CLAUDE_SESSION_ID`
set → `claude` > `COPILOT_SESSION_ID` set → `copilot` > `OPENAI_API_KEY` set →
`gpt` > `local` (fallback).

### Multiple Simultaneous Sessions

When multiple harnesses run concurrently, each harness gets its own top-level
partition, and each session within a harness gets its own subdirectory (see the
canonical path in [Queue Structure](#queue-structure-all-harnesses---unified)
above):

```
~/.agentic-engineers/
├── claude/
│   ├── 54744939-4acb-430c-b2c4-3b8322289d0b/     # Session 1
│   │   └── queue/
│   │       ├── incoming/ ← Claude tasks for session 1
│   │       ├── processing/
│   │       └── done/
│   └── 606ff436-b44b-47c5-90b8-f4bcc3fdb413/     # Session 2
│       └── queue/ ...
└── copilot/
    └── 54744939-4acb-430c-b2c4-3b8322289d0b/     # Session 1, different harness
        └── queue/
            ├── incoming/ ← Copilot tasks for session 1
            ├── processing/
            └── done/
```

Each harness/session pair is its own isolated queue partition. No
cross-contamination, no race conditions.

---

## Migration History (Completed 2026-05-26)

⚠️ **Queue path consolidation is COMPLETE.** Legacy paths are NO LONGER SUPPORTED.

**Historical:** Phases 1-4 involved gradual migration from:
- `~/.copilot/queue/` → ❌ DEPRECATED
- `~/.claude/queue/` → ❌ DEPRECATED
- `artifacts/queue/` → ❌ DEPRECATED

**Current:** All harnesses now use the canonical path:
- `~/.agentic-engineers/{harness}/{session-id}/queue/` ✅ REQUIRED

All harnesses now use the canonical queue path structure with no additional configuration needed.

---

## Runtime Enforcement: enqueue() is the Mandatory Gateway

**`QueueOperations.enqueue()` is the ONLY sanctioned way to create DELEGATE or HANDBACK files.**

Queue files live at `~/.agentic-engineers/{harness}/{session-id}/queue/` — outside git control.  
The pre-commit hook validates example files in the repo; `enqueue()` is the gate for runtime artifacts.

### Why enqueue() is mandatory

- Validates canonical schema before any file is written (no partial/invalid artifacts on disk)
- Enforces atomic writes (no torn files visible to a concurrently draining Orchestrator)
- Applies rate limiting, duplicate-id checks, and cycle detection
- Returns a structured result including the written file path for auditability

### Enforcement rules

| Rule | What happens if violated |
|------|--------------------------|
| Missing `handoff_type` | `ValueError` — must be `DELEGATE` or `HANDBACK` |
| Using `type:` instead of `handoff_type:` | `ValueError` — rejected as legacy field |
| Using `role:` instead of `agent:` | `ValueError` — rejected as legacy field |
| Top-level `quality_score:` | `ValueError` — must be `metrics.quality` (0.0-1.0 float) |
| Invalid `agent:` name | `ValueError` — must be hyphenated e.g. `senior-engineer` |
| Invalid `status:` in HANDBACK | `ValueError` — must be `success\|failure\|partial\|blocked\|escalate` |
| Missing `metrics` in HANDBACK | `ValueError` — `quality`, `tokens`, `cost`, `duration_seconds` all required |
| Duplicate `task_id` | `FileExistsError` |
| Rate limit exceeded | `RuntimeError` |

### Canonical Schema

**DELEGATE** (required fields):
```yaml
handoff_type: DELEGATE            # REQUIRED — was "type" in old schema
task_id: my-task-001              # kebab-case, 3-50 chars
agent: engineer                   # hyphenated lowercase — NOT "role: Engineer"
scope: ">=15 words describing the task scope"
plan:
  - "Step 1 with at least 3 words"
  - "Step 2 with at least 3 words"
context: ">=20 words of context"  # or non-empty list
success_criteria:
  - "Criterion 1"
# Optional: effort, model, priority, deadline, parent_task_id
```

**HANDBACK** (required fields):
```yaml
handoff_type: HANDBACK            # REQUIRED
task_id: my-task-001              # matches DELEGATE task_id
agent: engineer                   # agent that completed the work
status: success                   # success | failure | partial | blocked | escalate
output: {}                        # any value — result of the work
metrics:                          # REQUIRED — NOT top-level quality_score
  quality: 0.95                   # float 0.0-1.0 — NOT 0-100
  tokens: 3200                    # non-negative integer
  cost: 0.016                     # non-negative float (USD)
  duration_seconds: 38.5          # non-negative float
# Optional: model_used, effort_actual, flags, error, children_created
```

### Usage

```python
from skills.queue_management.scripts.queue_ops import QueueOperations

ops = QueueOperations(session_id=session_id)

# Enqueue a DELEGATE — validated, atomic, rate-limited
result = ops.enqueue({
    "handoff_type": "DELEGATE",
    "task_id": "fix-auth-timeout",
    "agent": "engineer",
    "scope": "Fix the token validation timeout that causes intermittent 401 errors under load",
    "plan": [
        "Read src/auth/token_validator.py to understand current timeout logic",
        "Identify the race condition in the concurrent validation path",
        "Apply fix with appropriate locking and update tests",
    ],
    "context": [
        "Service: auth-service (Go/Lambda)",
        "Problem: 401s spike under 100+ concurrent requests",
        "Token validator uses Redis with a 30s TTL; concurrent reads race on expiry",
    ],
    "success_criteria": [
        "No 401 errors under 200 concurrent requests in load test",
        "All existing auth tests still pass",
    ],
})
# result: {"status": "enqueued", "handoff_type": "DELEGATE", "task_id": "fix-auth-timeout", ...}

# NEVER write directly to the queue directory:
# open("~/.agentic-engineers/.../incoming/fix-auth-timeout.yaml", "w")  # FORBIDDEN
```

---

## DELEGATE/HANDBACK Storage

| Artifact | Path | Created By | Used By |
|----------|------|-----------|---------|
| DELEGATE | `~/.agentic-engineers/{harness}/{session-id}/queue/incoming/{task_id}.yaml` | `enqueue()` only | Spawning agent (records at spawn time), any agent auditing the trail |
| HANDBACK | `~/.agentic-engineers/{harness}/{session-id}/queue/processing/{task_id}.yaml` | `enqueue()` only | Spawning agent (records at completion), QE (verifies) |
| Archived record | `~/.agentic-engineers/{harness}/{session-id}/queue/done/{task_id}.yaml` (or `failed/`) | `move_task()` | Human / external system |

---

## File Naming

| Queue | Format | Example |
|-------|--------|---------|
| incoming | `{task_id}.yaml` | `fix-token-timeout.yaml` |
| processing | `{task_id}.yaml` | `fix-token-timeout.yaml` |
| done / failed | `{task_id}.yaml` | `fix-token-timeout.yaml` |

Note: All queue files are YAML (written by `enqueue()`) and named by `task_id`
only — `task_id` no longer requires a date prefix (see
[`docs/PROTOCOL.md` §2.1](PROTOCOL.md#21-delegate)). The state is tracked by
which subdirectory (`incoming/`, `processing/`, `done/`, `failed/`) the file
lives in; `move_task()` moves a file between subdirectories without renaming it.

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

## Integration with docs/SKILLS.md

Each agent role (Engineer, Senior Engineer, etc.) has a section in
[`docs/SKILLS.md`](SKILLS.md) covering how to execute their role, quality
standards, escalation triggers, and specific workflows (e.g. Red-Green TDD for
Engineer). An agent consults `docs/SKILLS.md` when receiving a DELEGATE, ensuring
consistent execution.

---

## Escalation & Rework Paths

**Blocked task:** the spawning agent reads a `status: blocked` HANDBACK, surfaces
the blocker (per [`docs/PROTOCOL.md` §4](PROTOCOL.md#4-quality-assessment)), and
either unblocks the task itself with guidance or escalates per the role's
`src/AGENTS.md` escalation trigger. There is no fixed numeric retry cap in the
current system — see [`docs/PROTOCOL.md` §4](PROTOCOL.md#4-quality-assessment).

**Quality issues:** if Quality Engineer's review finds the delivered work falls
short of `success_criteria`, the spawning agent constructs a new DELEGATE
targeting the same or an escalated role with the QE finding inlined in `context`,
and spawns it directly — the same mechanism as any other DELEGATE, not a special
"return to incoming/ for rework" path.

---

## Archive & Historical Lookup (Not Yet Implemented)

No archive mechanism exists in the current codebase — this section describes a
possible future extension, not present behavior. Today, historical lookup means
reading `done/`/`failed/` directly, or scanning `enqueue()`'s append-only audit
log (`{session-id}/audit.log`, one line per DELEGATE/HANDBACK).

---

## Future: Database Migration

This queue is file-based for simplicity. Can later migrate to:
- NoSQL (DynamoDB, Firestore)
- SQL (PostgreSQL, MySQL)
- Message queue (SQS, Kafka)

API layer would then sit atop the database, replacing file I/O.

---

## Summary

The queue is a **durable audit trail for direct agent-to-agent delegation**, not
the delegation mechanism itself — dispatch happens via a direct sub-agent spawn;
`enqueue()` records what happened, both at spawn and at completion.

Benefits:
- Auditable (every DELEGATE/HANDBACK durably recorded via `enqueue()`)
- Durable (the record persists if a harness session restarts, even though the
  in-flight spawn does not)
- No external tools, no polling, no timer — the spawning agent enqueues as part
  of the spawn, not as a separate mechanism

See `src/AGENTS.md` for routing rules (Delegation Model & Routing Rules), role
escalation triggers (Role Definitions), and the full execution model (Direct
Sub-Agent Spawn Execution Model); see `docs/SKILLS.md` for per-role execution
detail.

