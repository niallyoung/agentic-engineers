# spawn_sub_agent: Intended Runtime Pattern

**Status**: Accepted design (deferred item from the 2026-06-10 audit)
**Last Updated**: 2026-06-12

`spawn_sub_agent` is mocked in Python — and that is intentional. Real
Orchestrator→sub-agent invocation is a harness-runtime behaviour
("AGENTS-with-SKILLS", e.g. Claude Code's Task tool), not something a Python
daemon performs. This document records what the code does today, why, and what
the real execution path is.

## 1. What spawn_sub_agent does today (mocked)

`OrchestratorSkill.spawn_sub_agent()` lives at
`src/skills/orchestrator/scripts/orchestrator_skill.py:314`. It is called from
the polling loop `poll_queue()` (same file, line 242) after a DELEGATE is
validated and claimed. Instead of invoking an agent, it fabricates a
successful HANDBACK (lines 340–354: `quality: 0.90`, `confidence: 0.95` —
deliberately high enough to pass the QE gate) and returns it as YAML. The
in-code comment at lines 336–338 states the intent:

> For now, we return a mock HANDBACK since actual Agent tool invocation
> requires integration with the Claude Code harness. In a real deployment,
> this would call the Agent tool directly.

Everything *around* the mock is real: DELEGATE validation
(`_validate_delegate`, line 852), atomic claim (`claim_task`, line 264),
HANDBACK parsing/validation (`handle_handback`, line 371; `_validate_handback`,
line 862), the QE gate (`invoke_qe_gate`, line 671), and span capture
(`capture_span`, line 703).

## 2. Why a Python daemon does not spawn agents

Agents in this framework are markdown definitions (`src/agents/*.md`), rendered
per harness into `dist/{claude,copilot,opencode,pi}` by
`renderer/scripts/render-claude.sh`, `render-opencode.sh`,
`render-copilot-agents.py`, and `render-pi-dev.py` (driven by the Makefile
`render-*` targets), then installed to `~/.claude/agents/` etc. Sub-agent
invocation is a capability of the harness runtime that loads those
definitions, not of any Python process:

- **Claude Code** — the Task tool. The rendered agent files say so explicitly:
  `dist/claude/agents/engineer.md:211` — "Can be automatically invoked by
  orchestrator agents via Task tool."
- **OpenCode** — `mode: subagent` frontmatter
  (`dist/opencode/agents/engineer.md:3`) registers each specialist as a native
  OpenCode subagent.
- **Copilot CLI / pi.dev** — equivalent agent-selection mechanisms
  (`--agent <name>` invocation).

So the real execution path is:

```
Orchestrator agent (running inside a harness, with the orchestrator skill)
  ├─ reads a DELEGATE from the session queue (incoming/)
  ├─ invokes the specialist via the harness's native sub-agent tool,
  │    passing the full DELEGATE YAML as the prompt
  ├─ specialist executes and emits a HANDBACK YAML block
  └─ Orchestrator parses/validates the HANDBACK, applies the QE gate,
       and moves the task to done/ or failed/
```

A Python daemon has no handle on the Task tool — it exists only inside a live
harness session. `TaskRouter.route_task()` in
`src/orchestration/agents/orchestrator.py` (class at line 1000) reflects this:
it returns `(agent_name, None)` and its docstring notes "Agent execution is
handled by AgentInvoker (subprocess) or OrchestratorAgent" — routing by name
only, never instantiating agent stubs.

## 3. Role of the Python layer

The Python code is the protocol substrate, not the executor:

- **Validation** — DELEGATE/HANDBACK schema checks
  (`orchestrator_skill.py:852,862`; `src/orchestration/agents/delegate_validator.py`;
  the `protocol-validator` skill).
- **Queue state machine** — atomic incoming→processing→done/failed transitions,
  crash recovery, retries, idle detection (`orchestrator_skill.py`;
  the `queue-management` skill; `src/orchestration/queue_compat.py`).
- **Metrics & observability** — span capture per lifecycle step
  (`capture_span`, `orchestrator_skill.py:703`; `src/orchestration/span-schema.yaml`).
- **Quality gates** — QE thresholds on quality/confidence
  (`invoke_qe_gate`, `orchestrator_skill.py:671`).
- **Routing** — agent/model selection (`TaskRouter`, `orchestrator.py`;
  `src/orchestration/routing-rules.yaml`).

## 4. If true headless spawning were ever desired

A subprocess seam already exists:
`src/orchestration/agents/invoke_agent.py` — `AgentInvoker.invoke_agent()`
(line 201) spawns an arbitrary `agent_command` via `subprocess.Popen`
(line 256), passes the DELEGATE on stdin plus a `DELEGATE_PATH` env var, polls
for a HANDBACK file, and synthesises a `_synthetic=True` HANDBACK on
timeout/crash. Wiring real headless execution would mean setting
`agent_command` to a harness CLI in non-interactive mode, e.g.
`claude -p "<DELEGATE YAML>" --agent engineer` (headless/print mode), the
Claude Agent SDK, or `opencode --agent engineer` / `copilot --agent engineer`.

Trade-offs:

- **Cost** — each spawn is a cold session: no shared context or prompt cache
  with the parent; token spend multiplies versus in-session Task-tool fan-out.
- **Permissions** — headless runs need pre-granted permissions
  (`--allow`-style flags or sandbox config); no interactive prompts.
- **Auth & session state** — credentials, model routing, and per-session queue
  isolation (`SESSION_ID`/`HARNESS` env, already threaded through
  `invoke_agent.py`) must be managed explicitly.
- **Observability** — sub-agent token/cost telemetry arrives via files and exit
  codes instead of the harness's native sub-agent tracking.
- **Concurrency** — the daemon must own parallelism limits and crash recovery
  that the harness otherwise provides.

Note: the daemon-side *polling* is implemented within the Orchestrator agent
via its polling SKILL (iterative queue checking with backoff and signal handling),
not as a separate standalone controller class.

## 5. The mock is intentional

The mock in `spawn_sub_agent` is a deliberate test seam, not an unfinished
TODO. It lets the full lifecycle — poll → validate → claim → spawn → HANDBACK
→ QE gate → done/failed — be tested hermetically without a live harness:

- `src/skills/orchestrator/tests/test_orchestrator_skill.py:679`
  (`test_full_workflow_success`) drives the built-in mock end-to-end and
  asserts the task lands in `done/`.
- `src/skills/orchestrator/tests/test_orchestrator_skill.py:707`
  (`test_full_workflow_qe_rejection`) patches `spawn_sub_agent` (line 736) with
  a low-confidence HANDBACK and asserts the QE gate routes it to `failed/`.

Replacing the mock with a real call would be a harness-integration change (see
section 4), and the skill's prose contract already describes the real
behaviour: `src/skills/orchestrator/SKILL.md` lines 111–117 ("Invoke Agent
tool with full DELEGATE context").
