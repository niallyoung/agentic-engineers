# Agentic Engineers: Standard Execution Model

**Canonical workflow for running agentic-engineers**

The system works across multiple agent contexts with per-session queue partitioning
used as a **durable audit trail** for delegation:
- **Copilot agents** record work in `~/.agentic-engineers/copilot/{session-id}/queue/`
- **Claude agents** record work in `~/.agentic-engineers/claude/{session-id}/queue/`
- **OpenCode agents** record work in `~/.agentic-engineers/opencode/{session-id}/queue/`
- **Codex agents** record work in `~/.agentic-engineers/codex/{session-id}/queue/`
- All use identical DELEGATE/HANDBACK protocol
- Orchestrator auto-detects the harness/session partition
- Multiple simultaneous harness instances don't interfere with each other

**Dispatch is direct sub-agent spawn, not queue polling.** The Orchestrator builds a
DELEGATE and spawns the target agent directly (Agent/Task tool), reading the HANDBACK
back as the tool result in the same turn. The queue above still exists and is still
written to — every DELEGATE (at spawn) and every HANDBACK (at completion) is recorded
via `enqueue()` — but it is a record of what happened, not something anything polls to
decide what to do next. See
[src/AGENTS.md > Direct Sub-Agent Spawn Execution Model](../src/AGENTS.md#direct-sub-agent-spawn-execution-model)
for the canonical description.

---

## 🎯 How to Use Agentic Engineers

When you have work to do, invoke the Orchestrator in your harness and tell it what you
want — you do not need to hand-write a DELEGATE YAML file for anything to find.

### 1. Invoke the Orchestrator

```bash
# Claude Code
claude --agent orchestrator

# OpenCode CLI
opencode --agent orchestrator

# Copilot CLI
copilot --agent orchestrator
```

### 2. Give it your request

```
delegate: Fix the race condition in span capture (see ISSUE #42)
```

The Orchestrator:
1. Builds a DELEGATE block from your request (`agent`, `model`, `effort`, `scope`, `context`, `plan`, `success_criteria` — see `src/AGENTS.md` for the full format)
2. Spawns the target role directly (Agent/Task tool), passing the DELEGATE as the sub-agent's prompt
3. Records the DELEGATE to the queue via `enqueue()` (audit trail) at or immediately after the spawn call
4. Reads the HANDBACK back as the result of the spawn call itself — no polling, no wait loop
5. Records the HANDBACK to `done/` via `enqueue()` once the spawn call returns
6. Repeats for any further work (re-delegation, escalation) until it has no pending DELEGATEs and no outstanding spawns — then it **pauses** (see [src/AGENTS.md > Pause Condition](../src/AGENTS.md#pause-condition))

**Authoring a DELEGATE by hand** — for scripting, or to hand the Orchestrator a
fully-specified task — still uses the same YAML shape as before; what changed is what
happens to it once written:

```yaml
handoff_type: DELEGATE
task_id: 2026-05-02-my-task
agent: engineer | senior-engineer | lead-engineer | principal-engineer | security-engineer | quality-engineer | model-engineer | orchestrator
model: claude-haiku-4.5 | claude-sonnet-4.6 | claude-opus-4.7
effort: low | medium | high | max
scope: |
  Clear, one-sentence description of what the task is.
  What's in scope, what's out of scope.
context:
  - Key files: src/AGENTS.md, src/SKILLS.md
  - Related: Any prior commits or context
plan:
  - 1. First step
  - 2. Second step
success_criteria:
  - What "done" looks like
```

You pass this to the Orchestrator directly — as your prompt, or as the payload of a
re-delegation it issues itself — rather than dropping it into `queue/incoming/` for a
poller to notice. See `src/AGENTS.md` for the complete DELEGATE format.

### 3. Orchestrator handles everything

Per request, the Orchestrator:
1. ✅ Routes the task to the appropriate agent (per AGENTS.md)
2. ✅ Spawns that agent directly, passing the DELEGATE as its prompt
3. ✅ Reads the HANDBACK back as the spawn call's result — no wait loop involved
4. ✅ Captures span data (observability)
5. ✅ Updates `artifacts/index.json`
6. ✅ Records the DELEGATE and HANDBACK to the queue (`incoming/` and `done/`) for audit
7. ✅ Pauses when there is no pending DELEGATE and no outstanding spawn

### 4. Check results

**Immediately:** the Orchestrator reports the HANDBACK's outcome back to you in the same
session — you don't need to watch a directory for it to finish.

**For the audit trail:**
- Review `~/.agentic-engineers/<harness>/<session-id>/queue/done/{task_id}-HANDBACK-{role}.yaml`
- Check generated artifacts (updated specs, reports, code changes)
- Review `artifacts/index.json` for metrics
- Commit results: `git add artifacts/ && git commit -m "..."`

---

## 📋 Example Workflows

### Workflow 1: Update Documentation

```
delegate: Update docs/SPEC.md with current Phase 5.10 implementation
```

The Orchestrator spawns Senior Engineer directly with a DELEGATE built from that
request (scope: update `docs/SPEC.md` for Phase 5.10; context: SKILLS.md changes,
SPAN-CAPTURE-INTEGRATION.md; plan: read the relevant docs, then update SPEC.md), reads
the HANDBACK back in-context, and reports the outcome to you. Both the DELEGATE and the
HANDBACK are recorded to the queue for audit:

```bash
cat ~/.agentic-engineers/<harness>/<session-id>/queue/done/2026-05-02-update-spec-HANDBACK-senior-engineer.yaml
git log --oneline | head -1
```

### Workflow 2: Code Review & Validation

```
delegate: Validate implementation against docs/SPEC.md
```

The Orchestrator spawns Lead Engineer directly, reads back the HANDBACK (validation
report), and reports the outcome:

```bash
cat artifacts/spec-validation-report.md
```

### Workflow 3: Fix Code Issues

```
delegate: Fix race condition in Orchestrator span capture (see ISSUE #42)
```

The Orchestrator spawns Engineer directly with a DELEGATE (RED-GREEN-REFACTOR plan),
reads the HANDBACK back, and reports the outcome:

```bash
cat ~/.agentic-engineers/<harness>/<session-id>/queue/done/2026-05-02-fix-orchestrator-bug-HANDBACK-engineer.yaml
```

---

## 🏗️ Queue Structure (Audit Trail)

The queue is a durable record of what has been dispatched and what has completed. It is
written to at spawn time and at completion time, and it is never read to decide what to
spawn next:

```
~/.agentic-engineers/<harness>/<session-id>/queue/
├── incoming/                          # Audit copy of each DELEGATE, recorded at spawn time
│   ├── 2026-05-02-my-task.yaml
│   └── 2026-05-02-another-task.yaml
└── done/                              # Audit copy of each HANDBACK, recorded at completion
    ├── 2026-05-02-my-task-HANDBACK-engineer.yaml
    └── [results + metrics]
```

---

## 🤖 Key Agents (See AGENTS.md for full details)

| Role | Model | When to Use |
|------|-------|------------|
| **Engineer** | Haiku (fast) | Well-scoped work with a plan (code, docs, fixes) |
| **Senior Engineer** | Sonnet (strong) | Complex work, research, design, spec extraction |
| **Lead Engineer** | Sonnet (strong) | Code review, validation, quality gates |
| **Principal Engineer** | Opus (premium) | Cross-service architecture, major decisions |
| **Security Engineer** | Opus (premium) | Security reviews, auth, crypto, compliance |
| **Quality Engineer** | Sonnet (strong) | Test quality, coverage, best practices |
| **Model Engineer** | Sonnet (strong) | Cost-quality tradeoffs, recommendations |
| **Orchestrator** | All models | Routing, direct spawn dispatch, observability, audit-trail management |

See `src/AGENTS.md` for full decision tree.

---

## 📊 Observability & Metrics

After tasks complete, Orchestrator generates:

**SPAN files** (Structured span records):
```
artifacts/2026-05-02/
├── SPAN-2026-05-02T10:20:00Z-Engineer.yaml
├── SPAN-2026-05-02T10:25:00Z-Senior\ Engineer.yaml
└── SPAN-2026-05-02T10:30:00Z-Lead\ Engineer.yaml
```

**Index** (for searching):
```
artifacts/index.json
{
  "by_file_type": {
    "DELEGATE": [...],
    "HANDBACK": [...],
    "SPAN": [...]
  },
  "by_task_id": {...},
  "by_agent_type": {...},
  "stats": {
    "total_tokens": 125000,
    "total_cost": "$2.50",
    "total_tasks": 8,
    "success_rate": 1.0
  }
}
```

---

## ⚙️ Configuration

**Orchestrator behavior:**
- Dispatch: direct sub-agent spawn — there is no poll interval to configure
- Max concurrent spawns: 5 per parent (see [src/AGENTS.md > Recursion Limits](../src/AGENTS.md#recursion-limits))
- Max delegation depth: 3 (root DELEGATE = depth 0)
- Retry limit: 3 attempts before escalate
- Span capture: Enabled by default
- Index generation: After each HANDBACK

**Note on enforcement:** the depth/fan-out limits above are a documented contract each
agent's own definition observes (via its `tools:` frontmatter grant — see
[src/AGENTS.md > Tools-Frontmatter Permission Model](../src/AGENTS.md#tools-frontmatter-permission-model)).
No harness mechanically blocks an over-deep or over-wide spawn today; agents self-enforce.

---

## 🔀 Multi-Session Queue Partitioning

When multiple Copilot or Claude instances run concurrently, each session has its own
isolated queue partition for its audit trail:

### Session-ID Concept

- **Session-ID** is a UUID assigned to each Copilot/Claude instance
- Location: `~/.copilot/session-state/{session-id}/` or `~/.claude/session-state/{session-id}/`
- Each session's Orchestrator records only to its own queue partition
- No cross-contamination between simultaneous sessions

### Queue Paths by Session

```
~/.agentic-engineers/copilot/{session-id}/queue/
├── 54744939-4acb-430c-b2c4-3b8322289d0b/
│   ├── incoming/     # Audit records for this session only
│   └── done/
├── 606ff436-b44b-47c5-90b8-f4bcc3fdb413/  # Different session
│   ├── incoming/
│   └── done/
└── .migration-log    # Record of queue migrations
```

### Automatic Migration

When upgrading to session-id partitioning:
1. Old queue structure (`~/.copilot/queue/{incoming,done}`) is auto-detected
2. Files are copied to new session-specific location
3. Old directories renamed to backup (e.g., `incoming-legacy-20260503-143022/`)
4. Migration logged in `.migration-log` for audit trail
5. Zero data loss — all work preserved

### Session-ID Detection

The Orchestrator detects your session-id using:
1. **COPILOT_SESSION_ID** environment variable (highest priority)
2. **CLAUDE_SESSION_ID** environment variable
3. Scan of `~/.copilot/session-state/` or `~/.claude/session-state/` (most recent session)

You can check your session-id:
```bash
# Print current session-id
echo $COPILOT_SESSION_ID

# Or find it from session-state
ls ~/.copilot/session-state/
```

### Troubleshooting Queue Not Found

If you see "queue not found" errors:
1. Verify your session-id: `echo $COPILOT_SESSION_ID`
2. Check queue exists: `ls ~/.agentic-engineers/copilot/$COPILOT_SESSION_ID/queue/incoming/`
3. Check migration log: `cat ~/.agentic-engineers/copilot/.migration-log`
4. Verify session-state dir: `ls ~/.copilot/session-state/`

---

## 🔐 Security & Constraints

✅ **All work flows through agents** — no external scripts, cron jobs, or utilities
✅ **No direct file manipulation** — only via DELEGATE/HANDBACK protocol
✅ **Audit trail** — every DELEGATE and HANDBACK is recorded to the queue and spans
✅ **Escalation path** — for blocked or rework items
✅ **Cost tracking** — SPAN files capture tokens and cost per task

See `docs/SPEC.md` for full architectural constraints.

---

## 📚 Reference

- **src/AGENTS.md** — Full agent definitions, routing rules
- **src/SKILLS.md** — How each agent executes their role
- **docs/SPEC.md** — Canonical system specification with DELEGATE/HANDBACK/FEEDBACK formats
- **docs/SPEC.md** — Complete specification & constraints

---

## 🚀 TL;DR

1. **Tell the Orchestrator what you want** → it builds the DELEGATE for you and spawns the right agent directly (Agent/Task tool)
2. **Orchestrator handles everything** → routes, spawns, reads the HANDBACK back in-context, aggregates, and records both to the queue for audit
   - Multi-session support: each session has an isolated audit-trail partition
3. **Check results** → the outcome is reported to you directly; the audit trail lives in `~/.agentic-engineers/{harness}/{session-id}/queue/done/` and generated files
4. **Commit** → add artifacts to git

That's it. Orchestrator handles routing, direct-spawn execution, observability, session
isolation, and the audit trail. Everything is agent-based, auditable, and
framework-native — and nothing is waiting on a poll loop to notice your request.
