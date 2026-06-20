---
name: codex-agent-cleanup
description: "Routine maintenance for Codex sessions: monitor queue state, close completed sub-agents, resume or escalate active work, and keep agent capacity available."
license: Proprietary
compatibility: agentic-engineers framework v5.10+
metadata:
  author: agentic-engineers
  version: "1.0.0"
  category: orchestration
  role: orchestrator
  model: claude-haiku-4.5
  effort: medium
  thinking: false
---

# codex-agent-cleanup

Codex sessions can accumulate completed sub-agents that keep slots occupied.
This skill keeps the orchestrator healthy by routinely:

- checking queue state
- closing completed agents
- resuming active or orphaned agents when needed
- escalating or re-routing stuck work
- keeping the queue clear enough to spawn new work

## When To Use

- After sub-agents finish
- Before spawning additional parallel work
- When queue capacity feels unexpectedly constrained
- When a session has many completed delegates still open

## Workflow

1. Inspect the queue and active agents.
2. Close completed agents immediately.
3. Check for running agents that have stalled or need attention.
4. Resume only agents that are still relevant to the current task.
5. Escalate or re-route blocked work instead of leaving it open.
6. Re-check queue state after cleanup.

## Operating Rules

- Prefer closure over leaving finished agents open.
- Do not close agents that still have unfinished, relevant work.
- Do not duplicate cleanup already performed in the same turn.
- Keep the queue in a state that allows new delegation.
- If queue layout or state is unclear, inspect the local queue filesystem first.

## Signals To Watch

- Completed HANDBACKs still open
- Long-lived `processing/` entries with no forward progress
- Queue directories with stale or orphaned artifacts
- Agent pool saturation during parallel fan-out

## Practical Checks

- `close_agent` for completed sub-agents
- `wait_agent` for active delegates that are still in flight
- queue inspection under `~/.agentic-engineers/`
- local repo state before spawning more parallel work

## Good Defaults

- Clean up completed agents before starting new parallel tasks.
- Treat queue hygiene as part of normal Codex orchestration, not optional housekeeping.
- Prefer small cleanup cycles instead of waiting for a backlog.
