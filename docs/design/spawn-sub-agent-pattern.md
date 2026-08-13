# spawn_sub_agent: Intended Runtime Pattern

**Status**: Accepted design — reconciled with the now-canonical
[Direct Sub-Agent Spawn Execution Model](../../src/AGENTS.md#direct-sub-agent-spawn-execution-model)
**Last Updated**: 2026-08-09

`OrchestratorSkill.spawn_sub_agent()` (the Python method) is not implemented —
and that is intentional. Real Orchestrator→sub-agent invocation is a
harness-runtime behaviour ("AGENTS-with-SKILLS", e.g. Claude Code's Agent/Task
tool), not something a Python daemon performs. This document records what the
code does today, why, and how that maps onto the canonical execution model
now specified in `src/AGENTS.md`.

> **Canonical reference:** `src/AGENTS.md`'s
> [Direct Sub-Agent Spawn Execution Model](../../src/AGENTS.md#direct-sub-agent-spawn-execution-model)
> section is the single source of truth for the DELEGATE/HANDBACK spawn
> pattern, recursion limits, the tools-frontmatter permission model, and the
> audit-trail strategy. This document is a narrower, code-focused companion:
> it explains why the `orchestrator_skill.py` layer stops short of real
> invocation and cites the exact functions involved. Where the two disagree,
> `src/AGENTS.md` wins.

## 1. What `spawn_sub_agent` does today

`OrchestratorSkill.spawn_sub_agent()` lives at
`src/skills/orchestrator/scripts/orchestrator_skill.py:673`. It is called from
`poll_queue()` (same file, line 372) after a DELEGATE is validated and claimed
(`claim_task`, line 397). It does **not** fabricate a HANDBACK. It logs an
error and raises `SubAgentError` (wrapping a `NotImplementedError`), which
`poll_queue()` treats as a task failure and routes to `failed/`.

This is a deliberate change from an earlier version of this method, which
returned a hardcoded "success" HANDBACK with invented metrics
(`quality: 0.88`, `confidence: 0.95` — high enough to pass the QE gate) on
every call, regardless of whether any work happened. That behaviour was
identified as a security issue (fabricated success records silently
populating the queue's `done/` audit trail) and removed: the method's
docstring at lines 699–708 records the finding and the fix. It now fails
loudly instead of lying about task completion.

Everything *around* the raise is real: DELEGATE validation
(`_validate_delegate`, line 1467), atomic claim (`claim_task`, line 397,
using `os.link()` so exactly one racer wins under concurrent claims — see
`test_orchestrator_skill.py`'s claim-race test), HANDBACK
parsing/validation (`handle_handback`, line 731; `_validate_handback`, line
1491), the QE gate (`invoke_qe_gate`, line 1043), and span capture
(`capture_span`, line 1283).

Because the method always raises, unit tests that exercise the full
poll → claim → spawn → HANDBACK → QE gate → done/failed lifecycle patch it
per-test with an explicit mock HANDBACK (`test_full_workflow_success`,
`test_full_workflow_qe_rejection` in
`src/skills/orchestrator/tests/test_orchestrator_skill.py`) rather than
relying on a built-in fabricated default. See [§5](#5-why-the-method-raises-instead-of-mocking).

## 2. Why a Python daemon does not spawn agents

Agents in this framework are markdown definitions (`src/agents/*.md`), rendered
per harness into `dist/{claude,copilot,opencode,pi}` by
`renderer/scripts/render-claude.sh`, `render-opencode.sh`,
`render-copilot-agents.py`, and `render-pi-dev.py` (driven by the Makefile
`render-*` targets), then installed to `~/.claude/agents/` etc. Sub-agent
invocation is a capability of the harness runtime that loads those
definitions, not of any Python process:

- **Claude Code** — the Agent/Task tool. The rendered agent files say so
  explicitly: `dist/claude/agents/engineer.md:227` — "Can be automatically
  invoked by orchestrator agents via Task tool."
- **OpenCode** — `mode: subagent` frontmatter
  (`dist/opencode/agents/engineer.md:3`) registers each specialist as a native
  OpenCode subagent.
- **Copilot CLI / pi.dev** — equivalent agent-selection mechanisms
  (`--agent <name>` invocation).

So the real execution path — as specified authoritatively in `src/AGENTS.md`'s
[Full Flow](../../src/AGENTS.md#full-flow) — is:

```
Spawning agent (Orchestrator, or another role holding spawn_subagent authority)
  ├─ constructs a DELEGATE block (from a user request or prior HANDBACK output)
  ├─ passes the DELEGATE directly as the prompt of a sub-agent spawn
  │    (the harness's Agent/Task tool) — this call IS dispatch
  ├─ the spawned agent ACKs, executes, and returns a HANDBACK directly as
  │    the result of that same spawn call — no file is written or polled for
  │    this step to complete
  └─ the spawning agent reads the HANDBACK in-context, applies the QE gate
       and routing decision, and separately records both DELEGATE and
       HANDBACK to the queue via enqueue() for audit — after dispatch, not
       instead of it
```

A Python daemon has no handle on the Agent/Task tool — it exists only inside a
live harness session. `TaskRouter.route_task()` in
`src/orchestration/agents/orchestrator.py` (class at line 1020) reflects this:
it returns `(agent_name, None)` and its docstring notes that the previous
subprocess-spawn class (`AgentInvoker`, formerly
`src/orchestration/agents/invoke_agent.py`) **has been removed** in favor of
direct sub-agent spawning via the harness's Agent tool, "which is not yet
wired up at this layer" (see `OrchestratorAgent._process_task`'s `agent is
None` seam) — routing by name only, never instantiating agent stubs or
shelling out to a subprocess.

## 3. Role of the Python layer

The Python code is the protocol substrate, not the executor:

- **Validation** — DELEGATE/HANDBACK schema checks
  (`orchestrator_skill.py:1467,1491`; `src/orchestration/agents/delegate_validator.py`;
  the `protocol-validator` skill).
- **Queue state machine** — atomic incoming→processing→done/failed transitions
  (`claim_task`, `orchestrator_skill.py:397`), crash recovery, retries, idle
  detection (`orchestrator_skill.py`; the `queue-management` skill;
  `src/orchestration/queue_compat.py`). Under the current model this state
  machine is the audit trail described in `src/AGENTS.md`'s
  [Audit-Trail Strategy](../../src/AGENTS.md#audit-trail-strategy) — it
  records what a direct spawn already did, rather than driving dispatch.
- **Metrics & observability** — span capture per lifecycle step
  (`capture_span`, `orchestrator_skill.py:1283`; `src/orchestration/span-schema.yaml`).
- **Quality gates** — QE thresholds on quality/confidence
  (`invoke_qe_gate`, `orchestrator_skill.py:1043`).
- **Routing** — agent/model selection (`TaskRouter`, `orchestrator.py:1020`;
  `src/orchestration/routing-rules.yaml`).

## 4. There is no subprocess seam today

An earlier version of this document pointed to
`src/orchestration/agents/invoke_agent.py` (`AgentInvoker.invoke_agent()`) as
a subprocess seam that could be wired up for true headless spawning: spawn an
`agent_command` via `subprocess.Popen`, pass the DELEGATE on stdin plus a
`DELEGATE_PATH` env var, poll for a HANDBACK file, and synthesize a
`_synthetic=True` HANDBACK on timeout/crash.

**That file has been deleted.** `AgentInvoker` is gone; `TaskRouter` no longer
has anything to hand an `agent_name` to at the Python layer (see §2). There is
currently no code-level fallback path for headless/subprocess agent
invocation — the only specified path is the direct in-harness Agent/Task-tool
spawn described in `src/AGENTS.md`.

If true headless spawning (a harness CLI in non-interactive mode, e.g.
`claude -p "<DELEGATE YAML>" --agent engineer`, the Claude Agent SDK, or
`opencode --agent engineer` / `copilot --agent engineer`) were ever desired
again, the trade-offs that made the team defer it remain the same as before:

- **Cost** — each spawn is a cold session: no shared context or prompt cache
  with the parent; token spend multiplies versus in-session Agent/Task-tool
  fan-out.
- **Permissions** — headless runs need pre-granted permissions
  (`--allow`-style flags or sandbox config); no interactive prompts.
- **Auth & session state** — credentials, model routing, and per-session queue
  isolation (`SESSION_ID`/`HARNESS` env) must be managed explicitly.
- **Observability** — sub-agent token/cost telemetry would arrive via files
  and exit codes instead of the harness's native sub-agent tracking.
- **Concurrency** — a daemon would have to own parallelism limits and crash
  recovery that the harness otherwise provides — duplicating what
  `src/AGENTS.md`'s [Recursion Limits](../../src/AGENTS.md#recursion-limits)
  (max depth 3, max fan-out 5) and
  [Tools-Frontmatter Permission Model](../../src/AGENTS.md#tools-frontmatter-permission-model)
  already specify as agent-observed behaviour.

Re-introducing a subprocess seam is not currently planned; this section is
retained as a record of why one existed, and why it was removed rather than
extended.

## 5. Why the method raises instead of mocking

The original mock in `spawn_sub_agent` was framed as a deliberate test seam —
it let the full lifecycle (poll → validate → claim → spawn → HANDBACK →
QE gate → done/failed) be tested hermetically without a live harness. In
practice it also ran unmodified outside tests and populated the queue's
`done/` directory with fabricated "success" records for work that never
happened (§1). That is now treated as a defect, not a feature: the method
raises `SubAgentError` unconditionally instead.

Tests that need the full lifecycle now supply their own HANDBACK explicitly
via `unittest.mock.patch.object(orchestrator, 'spawn_sub_agent',
side_effect=mock_spawn)`:

- `src/skills/orchestrator/tests/test_orchestrator_skill.py::test_full_workflow_success`
  drives the lifecycle end-to-end with an explicit mocked HANDBACK and asserts
  the task lands in `done/`.
- `src/skills/orchestrator/tests/test_orchestrator_skill.py::test_full_workflow_qe_rejection`
  supplies a low-confidence mocked HANDBACK and asserts the QE gate routes it
  to `failed/`.

This keeps the hermetic-testing benefit of the original seam while removing
its ability to silently fabricate evidence of completed work — the audit
trail can no longer be populated by anything other than a real spawn result
or a test that says explicitly that it is mocking one.
