# Queue-Based Delegation Mechanics

Simple file-based queue system for DELEGATE/HANDBACK protocol. Enables agent-based delegation workflow via queue instead of direct messages.

**CANONICAL EXECUTION MODEL:** Orchestrator agent continuously polls `artifacts/queue/incoming/`, routes tasks to appropriate agents via AGENTS.md decision tree, processes HANDBACK results, and manages queue state transitions. **This is the ONLY way work flows through agentic-engineers.**

---

## Queue Structure

```
artifacts/queue/
├── incoming/      # New work, ready for Orchestrator agent to process
├── processing/    # Work assigned to agent, awaiting HANDBACK
└── done/          # Completed work, ready for human decision
```

---

## How It Works

### 1. Incoming Queue

**New task arrives as:** `artifacts/queue/incoming/{task_id}.yaml`

```yaml
---
task_id: 2026-04-30-fix-token-timeout
description: "Fix token validation timeout in {service-name}"
priority: high
# (Simple task description; Orchestrator will create DELEGATE)
---
```

**Orchestrator agent (running in harness) polls `incoming/` every 30-60s and:**
1. Reads task
2. Applies AGENTS.md routing rules
3. Creates DELEGATE (HANDOFF.md format)
4. Stores DELEGATE in `artifacts/delegates/YYYY-MM-DD/`
5. Sends DELEGATE to appropriate agent
6. Deletes from `incoming/` (or moves to archive)

### 2. Processing Queue

**Agent returns work as:** `artifacts/queue/processing/{task_id}-HANDBACK-{role}.yaml`

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

**Orchestrator agent polls `processing/` and:**
1. Routes complete work to Quality Engineer
2. Escalates blocked work to Lead/Senior Engineer
3. Moves to `done/` after decision

### 3. Done Queue

**Final decision stored as:** `artifacts/queue/done/{task_id}-{decision}.yaml`

```yaml
task_id: 2026-04-30-fix-token-timeout
decision: PROCEED | REWORK | ESCALATE
notes: "Quality Engineer verified; ready to merge"
```

**Human/external system reads from `done/` for:**
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

## DELEGATE/HANDBACK Storage

| Artifact | Path | Created By | Used By |
|----------|------|-----------|---------|
| DELEGATE | `artifacts/delegates/YYYY-MM-DD/DELEGATE-{task_id}-{role}.yaml` | Orchestrator | Agent (receives), Orchestrator (ref) |
| HANDBACK | `artifacts/queue/processing/{task_id}-HANDBACK-{role}.yaml` | Agent | Orchestrator (routes), QE (verifies) |
| Decision | `artifacts/queue/done/{task_id}-{decision}.yaml` | Orchestrator | Human / external system |

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

