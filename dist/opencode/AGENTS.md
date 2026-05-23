<!-- managed by agentic-engineers render-opencode.sh; user edits to AGENTS.md.local will be loaded after this file -->
# agentic-engineers — Global Rules

This OpenCode install is managed by the [agentic-engineers framework](https://github.com/niallyoung/agentic-engineers).
Eight specialised subagents (in `agents/`) collaborate via a structured
DELEGATE/HANDBACK protocol on a queue-based work pipeline.

## Mandatory Constraints

### Queue-based routing
- ALL work flows through `artifacts/queue/incoming/ → processing/ → done/`.
- The Orchestrator polls the queue and routes per the decision tree in
  `docs/AGENTS.md`. No direct delegation from external sources.
- DELEGATEs live in `artifacts/delegates/YYYY-MM-DD/`; HANDBACKs in
  `artifacts/queue/processing/` until the Quality Engineer reviews them.

### Orchestrator constraints
- The Orchestrator MUST NOT perform work — it only routes, coordinates, and
  applies Model Engineer recommendations.
- It runs in-harness via a polling loop (no external cron / outbound tools).
- ALL execution work is delegated to a specialist via DELEGATE/HANDBACK.

### Role-specific rules
- **Security Engineer** is invoked ONLY for security-scoped tasks.
- **Engineer** MUST NOT receive a task without a pre-written `plan` in the
  DELEGATE (except trivial fixes); blocked tasks escalate to Senior Engineer.
- **Quality Engineer** provides `model_assessment` feedback in every HANDBACK
  (consumed by the Model Engineer feedback loop).
- **Lead/Senior Engineer** unblock or redirect Engineer when blocked.
- Each role has specialised skills under `skills/` (see `docs/SKILLS.md`).

## Layout in this install
- `agents/` — 8 subagents; invoke via `@<agent-name>` or the task tool
  (e.g. `@orchestrator`, `@engineer`, `@security-engineer`).
- `skills/` — workflow modules loaded on demand via the skill tool.
- `opencode.jsonc` — managed config (compaction, permissions); do not edit.
- `AGENTS.md.local` — *optional, user-authored*; if present, OpenCode loads
  it after this file. Use it for personal overrides that survive re-render.

## OpenCode-specific quirks
- **Compaction** is automatic with `reserved: 30000` tokens of headroom (vs
  upstream default 20000). The TUI signals when compaction triggers.
- **Skill tool outputs are PRUNE_PROTECTED** — invoke skills aggressively;
  their output survives compaction. Other tool output may be pruned.
- 8 subagents are installed. Mention them with `@` or invoke programmatically
  via the task tool.

## Full specification
See [`docs/AGENTS.md`](https://github.com/niallyoung/agentic-engineers), [`docs/HANDOFF.md`](https://github.com/niallyoung/agentic-engineers),
[`docs/QUEUE-PROTOCOL.md`](https://github.com/niallyoung/agentic-engineers), and [`docs/SKILLS.md`](https://github.com/niallyoung/agentic-engineers)
in the source repository for the authoritative protocol.
