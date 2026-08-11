# Design Note: HANDBACK-as-DELEGATE (Direct Agent-to-Agent Delegation)

**Status:** DRAFT — design note only, no decision made
**Origin:** Deferred item from the 2026-06-10 master-prompt audit
**Question from operator:** "Is HANDBACK actually a DELEGATE / can it be, for direct agent→agent handoff vs queue-and-poll?"

> **2026-08-11 note:** SPEC-2026-004 subsequently replaced queue-and-poll dispatch with
> direct sub-agent spawn as the canonical execution model (see `docs/SPEC.md`'s
> ORCHESTRATOR-FIRST EXECUTION MODEL and `src/AGENTS.md`). This note's framing below
> ("Current Flow (Queue-and-Poll via Orchestrator)") describes the pre-SPEC-2026-004
> architecture and is retained as historical context for the options analysis; the
> "30–60s polling interval" and poll-cycle latency arguments no longer apply to Option 0.
> The schema paths below have also moved: `src/orchestration/{delegate,handback}-schema.yaml`
> is now `docs/specs/{delegate,handback}-schema.yaml`. The core question (should an
> escalation HANDBACK formally embed the next DELEGATE) remains open and undecided.

---

## Problem Statement

Today, when an agent finishes (or cannot finish) a task and the work needs to go
to *another* agent, the only path is indirect: the agent returns a HANDBACK to
the Orchestrator, and the Orchestrator synthesizes a brand-new DELEGATE and
enqueues it. The agent that knows the most about the follow-on work (what is
needed, why, and for whom) does not author the follow-on task — the Orchestrator
reconstructs it from HANDBACK fields. This adds a queue-and-poll round trip
(30–60s polling interval per `docs/QUEUE-PROTOCOL.md`), loses fidelity between
"what the agent wanted to hand off" and "what the Orchestrator delegated", and
raises the conceptual question: an escalation HANDBACK already *functions* as a
delegation request — should the protocol make that explicit?

## Current Flow (Queue-and-Poll via Orchestrator)

All protocol files are YAML (PR #52 fixed the lone JSON outlier in
queue-management; both pollers glob `incoming/*.yaml` —
`src/skills/orchestrator/scripts/orchestrator_skill.py:216` and
`src/orchestration/agents/orchestrator.py:446`).

Queue layout (LOCKED SPEC, `docs/QUEUE-PROTOCOL.md` / `docs/SPEC.md`):

```
~/.agentic-engineers/{harness}/{session-id}/queue/
├── incoming/     # {task_id}.yaml — handoff_type: DELEGATE
├── processing/   # claimed work; HANDBACKs as {task_id}-HANDBACK-{role}.yaml
├── done/         # final decisions: PROCEED | REWORK | ESCALATE
└── failed/       # errored tasks
```

The two block types are discriminated by `handoff_type: DELEGATE` vs
`handoff_type: HANDBACK`. Their canonical schemas live at
`docs/specs/delegate-schema.yaml` and
`docs/specs/handback-schema.yaml`.

Escalation today ("Escalation Chaining (C2c)", `docs/QUEUE-PROTOCOL.md`):

1. Agent returns a HANDBACK with `status: escalate`, carrying
   `output.escalate_to` (target role), `output.escalation_reason`, and an
   `escalation_chain` list.
2. The Orchestrator (`src/orchestration/agents/orchestrator.py`, ~lines
   1961–2018) detects `status == 'escalate'`, builds a **new** DELEGATE
   (`task_id: {original}-escalated-to-{role}`) embedding the original HANDBACK
   in `context`, writes it to `incoming/`, and moves the original task to
   `done/` with escalation metadata.
3. The new DELEGATE waits for the next poll cycle before the target agent sees it.

Notably, the skill-based poller has a *divergent* second implementation:
`orchestrator_skill.py:_move_task_to_escalation` (line 965) moves the task to a
sibling `escalation/` directory and writes a `{task_id}-context.json` instead of
chaining a new DELEGATE. The two escalation paths do not behave the same.

Prior art for agents authoring DELEGATEs already exists: the queue-management
skill (`src/skills/queue-management/scripts/queue_ops.py`) supports
decentralized sub-task creation via `enqueue(..., parent_task_id=...)` with
cycle detection, rate limiting, and `task_tier` depth caps (max 5, per
`delegate-schema.yaml` `subtask_fields`), and HANDBACKs report
`children_created` / `children_results`. So "agent creates a DELEGATE" is not
new — but those DELEGATEs still land in `incoming/` and flow through
Orchestrator routing.

## Proposed Alternative

Make the HANDBACK→DELEGATE relationship explicit, in one of two shapes:

- **HANDBACK carrying a follow-on DELEGATE payload** — the finishing agent
  authors the next task itself, embedded in its HANDBACK; or
- **A direct agent→agent handoff channel** — the finishing agent hands work to
  the next agent without the Orchestrator synthesizing or routing it.

## Options

### Option 0 — Status quo (baseline)

Keep C2c chaining: HANDBACK `status: escalate` → Orchestrator synthesizes a new
DELEGATE → `incoming/` → poll.

- ✅ Fully compliant with the ORCHESTRATOR-FIRST EXECUTION MODEL (MANDATORY)
  section of `docs/SPEC.md`: *"Engineers MUST NOT create DELEGATE blocks
  manually and send them to agents. Work only flows through the Orchestrator
  queue system."*
- ✅ Every hop hits pre-flight validation (delegate-schema groups A–D: task_id
  format/uniqueness, role validity, model-default A4, effort/role A5, routing
  sanity C1–C4, security D1–D3) and HANDBACK quality gates.
- ❌ Poll-cycle latency per hop; Orchestrator-synthesized DELEGATE is generic
  (fixed `success_criteria`, scope = one-line escalation reason).
- ❌ Two divergent escalation implementations (see above) — needs consolidation
  regardless of this decision.

### Option A — HANDBACK embeds a follow-on DELEGATE payload (Orchestrator-mediated)

Add an optional field to `handback-schema.yaml`, e.g. `next_delegate:` (a full
DELEGATE block authored by the finishing agent). On `status: escalate` (or a
new `status` value), the Orchestrator validates `next_delegate` through the
normal pre-flight gates and enqueues it *verbatim* into `incoming/` instead of
synthesizing one.

- ✅ Preserves Orchestrator-first: the Orchestrator still validates, routes
  (may override role/model per groups A/C), and enqueues. The agent proposes;
  the Orchestrator disposes.
- ✅ Full audit trail: the proposed DELEGATE is captured inside the HANDBACK
  file in `processing/`→`done/`, and the enqueued copy in `incoming/`.
- ✅ Higher-fidelity follow-on tasks: the agent that did the work writes the
  scope, context, plan, and success_criteria (vs today's generic synthesis).
- ✅ Cost discipline intact: model selection remains subject to A4 defaults and
  Orchestrator override, so a Haiku-tier agent cannot unilaterally burn Opus
  budget.
- ❌ Still queue-and-poll latency (no speedup, only fidelity).
- ❌ Schema change + validator change (`protocol-validator`,
  `quality_validator.py` Layer 1) + risk that an embedded DELEGATE fails
  pre-flight and strands the handoff (needs a defined rejection path).

### Option B — Direct agent→agent handoff channel (bypass Orchestrator routing)

The finishing agent writes a DELEGATE directly into `incoming/` (mechanically
already possible via queue-management `enqueue` with `parent_task_id`), or — in
the strong form — invokes the target agent directly (Task-tool spawn), with the
HANDBACK recording the handoff after the fact.

- ✅ Lowest latency in the strong form (no poll cycle, no routing hop);
  weak form (write-to-incoming) at least removes the synthesis step.
- ✅ Cycle detection, rate limiting, and `task_tier` depth caps already exist
  in queue-management and would still apply to the weak form.
- ❌ **Directly contradicts `docs/SPEC.md` ORCHESTRATOR-FIRST (MANDATORY)** —
  "No Direct Agent Invocation" and "no other entry point exists". The strong
  form requires a SPEC amendment via the spec-management skill (LOCKED spec).
- ❌ Routing/quality-gate bypass risk: agent-chosen role/model skips groups
  A4/A5/C1–C4 and D1–D3 security routing; a misrouted security-scoped task
  could land on a non-security agent.
- ❌ Cost-discipline bypass: the cheap-first escalation ladder (Haiku → Sonnet
  → Opus) is enforced by the Orchestrator; direct handoff lets any agent pick
  any model.
- ❌ Auditability degrades in the strong form: no `incoming/` artifact for the
  hop; the only record is inside the HANDBACK. Retry caps (MAX_RETRIES = 2,
  `orchestrator.py:187`) and crash recovery assume Orchestrator-managed state
  transitions.

## Open Questions

1. **Status enum drift (pre-existing):** `handback-schema.yaml` defines
   `status: complete | failed | partial | blocked` — `escalate` is not in the
   canonical schema, yet `orchestrator_skill.py:872` accepts
   `success | failure | partial | blocked | escalate` and `~/.claude/CLAUDE.md`
   documents the latter set. Which enum is canonical must be settled before
   (or alongside) any HANDBACK-as-DELEGATE change.
2. **Divergent escalation implementations:** chained-DELEGATE (C2c, in
   `orchestration/agents/orchestrator.py`) vs `escalation/` directory
   (`orchestrator_skill.py`). Consolidate first?
3. **Validation ownership (Option A):** if an embedded `next_delegate` fails
   pre-flight, does the parent HANDBACK become `partial`/`blocked`, or does the
   Orchestrator repair-and-enqueue?
4. **Depth accounting:** do escalation hops consume `task_tier` budget (max 5)
   the same way sub-tasks do?
5. **Is HANDBACK "actually" a DELEGATE?** Structurally no — disjoint required
   fields (DELEGATE: scope/plan/success_criteria; HANDBACK:
   deliverables/tests/quality_score) sharing only `task_id`, `spec_version`,
   `model_verification_sha`, and the `handoff_type` discriminator.
   Functionally, an escalation HANDBACK *is* a delegation request that the
   Orchestrator currently rewrites — which is what Option A formalizes.

## Recommendation

**The decision is explicitly deferred to the operator.** No code change should
be made on the basis of this note.

For when the operator picks this up: Option A (embedded `next_delegate`
payload, Orchestrator-mediated) is the smallest step that answers the audit
question affirmatively — it formalizes "an escalation HANDBACK is a DELEGATE
proposal" without amending the ORCHESTRATOR-FIRST mandate, and it preserves
every existing validation, routing, audit, and cost-discipline gate. Option B
(direct handoff) should be treated as a separate SPEC-amendment discussion via
the spec-management skill, not an incremental protocol tweak. Open questions
1–2 (status-enum drift, divergent escalation implementations) are worth fixing
regardless of which option — or neither — is chosen.
