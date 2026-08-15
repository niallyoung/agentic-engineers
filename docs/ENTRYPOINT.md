# Agentic Engineers: Standard Execution Model

**Canonical workflow for running agentic-engineers**

**Dispatch is direct sub-agent spawn — there is no filesystem queue.** The Orchestrator
builds a DELEGATE and spawns the target agent directly (Agent/Task tool), reading the
HANDBACK back as the tool result in the same turn:
- All harnesses (Copilot, Claude, OpenCode, Codex) use identical DELEGATE/HANDBACK
  protocol and identical dispatch mechanics
- Orchestrator auto-detects the harness from the session environment
- Multiple simultaneous harness instances don't interfere with each other — each is its
  own independent session, spawning and reading results entirely in its own context

The harness session transcript itself — every DELEGATE as a spawn prompt, every
HANDBACK as that spawn's result — is the durable audit record. Nothing is separately
written to or polled from disk to make a delegation "count." See
[src/AGENTS.md > Direct Sub-Agent Spawn Execution Model](../src/AGENTS.md#direct-sub-agent-spawn-execution-model)
for the canonical description.

Separately, agents also append a queryable metrics/event log — one JSONL line per
lifecycle event, per `docs/SPEC.md` clause 7 — which `scripts/handback_rollup.py` can
consume directly. That log is additive, not a replacement for the transcript above; see
[docs/PROTOCOL.md > Audit Events (JSONL)](PROTOCOL.md#7a-audit-events-jsonl).

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
delegate: Fix the race condition in claude-delegate-guard.py (see ISSUE #42)
```

The Orchestrator:
1. Builds a DELEGATE block from your request (`agent`, `model`, `effort`, `scope`, `context`, `plan`, `success_criteria` — see `src/AGENTS.md` for the full format)
2. Spawns the target role directly (Agent/Task tool), passing the DELEGATE as the sub-agent's prompt — this spawn, recorded in the harness session transcript, is the audit record
3. Reads the HANDBACK back as the result of the spawn call itself, synchronously and in-context
4. Repeats for any further work (re-delegation, escalation) until it has no pending DELEGATEs and no outstanding spawns — then it **pauses** (see [src/AGENTS.md > Pause Condition](../src/AGENTS.md#pause-condition))

**Authoring a DELEGATE by hand** — for scripting, or to hand the Orchestrator a
fully-specified task — still uses the same YAML shape as before; what changed is what
happens to it once written:

```yaml
handoff_type: DELEGATE
task_id: 2026-05-02-my-task
agent: engineer | senior-engineer | lead-engineer | principal-engineer | security-engineer | quality-engineer | model-engineer | orchestrator
model: claude-haiku-4.5 | claude-sonnet-5 | claude-opus-5 | claude-fable-5
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
re-delegation it issues itself. There is no directory to drop it into and no poller
that needs to notice it; the spawn call itself is the delivery. See `src/AGENTS.md`
for the complete DELEGATE format.

### 3. Orchestrator handles everything

Per request, the Orchestrator:
1. ✅ Routes the task to the appropriate agent (per AGENTS.md)
2. ✅ Spawns that agent directly, passing the DELEGATE as its prompt
3. ✅ Reads the HANDBACK back as the spawn call's result — no wait loop involved
4. ✅ Records per-event JSONL audit data via `scripts/audit_append.py` (`docs/SPEC.md` clause 7)
5. ✅ Pauses when there is no pending DELEGATE and no outstanding spawn

### 4. Check results

**Immediately:** the Orchestrator reports the HANDBACK's outcome back to you in the same
session — you don't need to watch a directory for it to finish. The DELEGATE and HANDBACK
themselves live in the harness session transcript; there is no separate file you need to
read for the *result*. There is a separate, queryable JSONL event log (`docs/SPEC.md`
clause 7, appended by agents via `scripts/audit_append.py`) if you want metrics/cost
history instead of the outcome itself — see `scripts/handback_rollup.py --events`.

**Also check:**
- Generated artifacts (updated specs, reports, code changes)
- Commit results: `git commit -m "..."`

---

## 📋 Example Workflows

### Workflow 1: Update Documentation

```
delegate: Update docs/SPEC.md with current Phase 5.10 implementation
```

The Orchestrator spawns Senior Engineer directly with a DELEGATE built from that
request (scope: update `docs/SPEC.md` for Phase 5.10; context: SKILLS.md changes,
relevant SPEC.md sections; plan: read the relevant docs, then update SPEC.md), reads
the HANDBACK back in-context, and reports the outcome to you — both the DELEGATE and the
HANDBACK live in the session transcript, not a separate file:

```bash
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
delegate: Fix race condition in the audit-JSONL append path (see ISSUE #42)
```

The Orchestrator spawns Engineer directly with a DELEGATE (RED-GREEN-REFACTOR plan),
reads the HANDBACK back, and reports the outcome directly to you — the spawn and its
result are the record; there is nothing further to `cat`.

---

## 🏗️ Audit Trail: The Session Transcript

There is no filesystem queue. The durable record of what has been dispatched and what
has completed is the harness session transcript itself: every DELEGATE appears verbatim
as a sub-agent spawn's prompt, and every HANDBACK appears verbatim as that spawn call's
result. Nothing is written to or read from a separate directory to make dispatch
*happen*, and nothing polls anything to decide what to spawn next.

**A second, queryable log exists alongside it.** `docs/SPEC.md` clause 7 requires
agents to append one JSON line per orchestration event (`delegate_issued`,
`subagent_spawned`, `handback_received`, `gate_result`, `escalation`, `refusal`,
`limit_exceeded`) to
`~/.agentic-engineers/{harness}/{session-id}/audit/events-YYYY-MM-DD.jsonl` via
`scripts/audit_append.py`. This does not change the model above — the transcript is
still what makes a DELEGATE/HANDBACK *count*; the JSONL is metrics/event data derived
from the same events, written so `scripts/handback_rollup.py` and similar tooling can
query it without re-parsing a transcript. See
[docs/PROTOCOL.md > Audit Events (JSONL)](PROTOCOL.md#7a-audit-events-jsonl).

---

## 🤖 Agent Reference

See `src/AGENTS.md` for the full agent roster, routing decision tree, and role definitions.


---

## ⚙️ Configuration

**Orchestrator behavior:**
- Dispatch: direct sub-agent spawn — there is no poll interval to configure
- Max concurrent spawns: 5 per parent (see [src/AGENTS.md > Recursion Limits](../src/AGENTS.md#recursion-limits))
- Max delegation depth: 3 (root DELEGATE = depth 0)

**Note on enforcement:** the depth/fan-out limits above are a documented contract each
agent's own definition observes (via its `tools:` frontmatter grant — see
[src/AGENTS.md > Tools-Frontmatter Permission Model](../src/AGENTS.md#tools-frontmatter-permission-model)).
No harness mechanically blocks an over-deep or over-wide spawn today; agents self-enforce.

---

## 🔀 Multi-Session Isolation

When multiple Copilot or Claude instances run concurrently, each is its own independent
harness session — spawning sub-agents and reading HANDBACKs entirely within its own
context, with no shared state and no cross-contamination between sessions. Each session's
transcript is scoped to that session, ensuring isolation by design.

---

## 🔐 Security & Constraints

✅ **All work flows through agents** — no external scripts, cron jobs, or utilities
✅ **No direct file manipulation** — only via DELEGATE/HANDBACK protocol
✅ **Audit trail** — every DELEGATE and HANDBACK is recorded in the harness session transcript; agents additionally append per-event JSONL records (`docs/SPEC.md` clause 7)
✅ **Escalation path** — for blocked or rework items
✅ **Cost tracking** — HANDBACK `metrics` (tokens, cost, quality, duration) plus the per-event JSONL audit log (`docs/SPEC.md` clause 7, `scripts/audit_append.py`)

See `docs/SPEC.md` for full architectural constraints.

---

## 📚 Reference

- **src/AGENTS.md** — Full agent definitions, routing rules
- **src/SKILLS.md** — How each agent executes their role
- **docs/SPEC.md** — Canonical system specification with DELEGATE/HANDBACK formats

---

## 🚀 TL;DR

1. **Tell the Orchestrator what you want** → it builds the DELEGATE for you and spawns the right agent directly (Agent/Task tool)
2. **Orchestrator handles everything** → routes, spawns, reads the HANDBACK back in-context, and aggregates results — the spawn/result pair in the session transcript is already the audit record
   - Multi-session support: each harness session is independently isolated, with nothing shared between concurrent sessions
3. **Check results** → the outcome is reported to you directly, plus generated files
4. **Commit** → add artifacts to git

That's it. Orchestrator handles routing, direct-spawn execution, observability, session
isolation, and the audit trail. Everything is agent-based, auditable, and
framework-native — and nothing is waiting on a poll loop to notice your request.
