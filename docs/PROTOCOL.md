---
title: Orchestration Protocol — Master Reference
version: 2.0.0
status: APPROVED
updated: 2026-08-13
owner: Lead Engineer
references:
  - src/AGENTS.md
  - docs/specs/protocol-core-v1.0.yaml
---

# Orchestration Protocol — Master Reference

> **Source of truth for the DELEGATE/HANDBACK message format, its validation and
> enforcement tooling, and how quality and escalation are handled.** For *who* does
> the work and *how* it's routed (the agent roster, the routing decision tree, model
> assignments, role boundaries), see [`src/AGENTS.md`](../src/AGENTS.md) — this
> document does not duplicate that content.

---

## 1. What This Protocol Is

The Orchestration Protocol defines the structured message pair — **DELEGATE** (a
task handed to a specialist agent) and **HANDBACK** (the result returned) — that
every unit of work in agentic-engineers flows through, plus the tooling that
validates and enforces it. It exists so that every delegated task is auditable,
every result carries measurable outcomes, and quality/cost signals feed back into
routing decisions.

### Current Architecture (Direct Sub-Agent Spawn)

The canonical execution model is **direct sub-agent spawn**, not queue-and-poll:
the spawning agent constructs a DELEGATE block and passes it directly as the
prompt of a sub-agent spawn (the harness's Agent/Task tool); the HANDBACK returns
synchronously as that spawn call's result, in-context. There is no polling
interval, no dispatch-by-file-write, and no filesystem queue at all — the
harness session transcript itself (every DELEGATE as a spawn prompt, every
HANDBACK as that spawn's result) is the durable audit record. See
[`src/AGENTS.md` > Direct Sub-Agent Spawn Execution
Model](../src/AGENTS.md#direct-sub-agent-spawn-execution-model) for the full
flow.

### Why It Matters

| Failure mode without the protocol | Consequence |
|---|---|
| Poorly-specified DELEGATE | Agent does the wrong work; wasted tokens; rework |
| Unstructured HANDBACK | No measurable outcome; no signal for routing/cost decisions |
| No audit trail | Crash recovery and historical analysis become impossible |

---

## 2. Canonical Schema

**Normative source:** [`docs/specs/protocol-core-v1.0.yaml`](specs/protocol-core-v1.0.yaml)
(JSON-Schema draft-07). Its own header comment states the precedence chain when
reconciling drift: the runtime validator
(`src/skills/protocol-validator/scripts/protocol_validator.py`) is authoritative for
*enforcement*; this YAML file is the canonical *description*; `src/AGENTS.md` and this
document are human-readable narrative. A byte-identical copy ships at
`src/skills/protocol-validator/schema/protocol-core-v1.0.yaml` so the skill resolves
its schema correctly when installed outside the repo — the two copies are
guaranteed identical by `tests/test_protocol_schema_copy_identity.py`; never edit
the skill-local copy directly.

### 2.1 DELEGATE

**Required core fields:** `task_id`, `handoff_type`, `skill`, `agent`, `scope`,
`success_criteria`, `plan`, `context`, `spec_version`.

| Field | Rule |
|---|---|
| `task_id` | kebab-case, 3–50 chars: `^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$` |
| `handoff_type` | must equal `DELEGATE` (the `type:` field is a deprecated alias, warned not rejected) |
| `skill` | name resolving to an entry under `skills/` |
| `agent` | one of the eight hyphenated roles — see `src/AGENTS.md` Agent Roster |
| `scope` | what will be done, to what, and out-of-scope boundaries; **>=15 words** |
| `success_criteria` | non-empty array of measurable outcomes |
| `plan` | **>=2 steps**, each **>=3 words**; ordered and concrete |
| `context` | relevant files/errors/prior art; a **>=20-word** string or a non-empty array |

**Optional extensions** (loosely validated, forward-compatible; unknown fields warn,
never fail): `model`, `effort` (`low\|medium\|high\|max`), `parent_task_id`,
`parallel_plan`, `tokens_estimate`, `budget`, `priority` (1–10),
`deadline`, `dependencies`, `retry_context`, `token_quota`, and — set whenever the
spawning agent was itself spawned (depth > 0) — `ancestry` (root-to-parent role
chain, used for cycle/depth detection; see [§5](#5-escalation)).

```yaml
handoff_type: DELEGATE
task_id: add-jwt-validation
skill: senior-engineer
agent: senior-engineer
scope: |
  Implement JWT validation middleware for the API gateway, including signature
  verification, expiry grace-period handling, and rejection of malformed tokens.
context:
  - "Key file: src/api/middleware.py:45"
  - "Related PR: #201 (auth refactor, merged)"
plan:
  - "Read src/api/middleware.py to understand current validation"
  - "Add test_jwt_validation.py covering valid, expired, malformed, missing tokens"
  - "Implement validate_jwt() with a 30s grace period constant"
  - "Run pytest -v to confirm zero failures"
success_criteria:
  - "pytest returns zero failures (all existing + new tests pass)"
  - "validate_jwt() rejects tokens expired >30s, accepts tokens expired <=30s"
effort: high
```

### 2.2 HANDBACK

**Required core fields:** `task_id`, `handoff_type`, `status`, `output`, `metrics`,
`spec_version`.

| Field | Rule |
|---|---|
| `task_id` | must exactly match the originating DELEGATE's `task_id` |
| `handoff_type` | must equal `HANDBACK` |
| `status` | `success \| failure \| partial \| blocked \| escalate` — `complete`/`failed` are **not** valid |
| `output` | any value (typically a human-readable summary); key must be present |
| `metrics` | object; **all four sub-fields required**: `quality` (float 0.0–1.0), `tokens` (non-negative int), `cost` (non-negative float, USD), `duration_seconds` (non-negative float) |

**Optional extensions:** `token_usage` (structured input/output/cached breakdown),
`escalations`, `model_assessment`, `confidence` (0.0–1.0), `retry_count`,
`model_used`, `effort_actual`, `children_created`, `children_results`, `flags`,
`criteria_results`, `error`. `skill_feedback` (structured per-skill feedback
consumed by the `skill-improvement-feedback` pattern) is accepted at runtime as a
forward-compatible field — see `protocol_validator.py`'s
`KNOWN_HANDBACK_RUNTIME_FIELDS` and `src/skills/skill-improvement-feedback/SKILL.md`
for its shape.

```yaml
handoff_type: HANDBACK
task_id: add-jwt-validation
status: success
output: |
  Implemented validate_jwt() with a configurable 30s grace period. Added 12 tests
  covering valid, expired, boundary, missing-header, and malformed-signature cases.
metrics:
  quality: 0.94
  tokens: 4300
  cost: 0.14
  duration_seconds: 1440
confidence: 0.9
```

> **Quality scale is always 0.0–1.0.** There is no 0–100 `quality_score` field and
> no automated multi-layer composite-scoring formula in the current system — see
> [§4](#4-quality-assessment).

### 2.3 Sub-Task / Parent-Child Fields

Any agent may decompose its task into child tasks by directly spawning multiple
sub-agents with a shared `parent_task_id`, subject to ancestry-based cycle detection
and the max-depth-3/max-fan-out-5 limits the spawning agent self-enforces (see
[Recursion Limits](../src/AGENTS.md#recursion-limits) in `src/AGENTS.md`) — there is no
separate queue-write step that performs this checking on the agent's behalf. A parent's
HANDBACK may report the results via the extension fields `children_created` (task_ids),
`children_results` (per-child status/output/quality, keyed by task_id), and
`criteria_results` (per-success-criterion evidence). There is no separate `parallel_plan`
execution runtime beyond the DELEGATE extension field of the same name — parallel
fan-out is the spawning agent directly issuing multiple concurrent spawns.

---

## 3. Validation & Enforcement

Four independent layers check DELEGATE/HANDBACK compliance. They overlap
deliberately — no single layer is a complete gate on its own.

| Layer | What it checks | When it runs | Scope |
|---|---|---|---|
| **`protocol-validator` skill** (`src/skills/protocol-validator/scripts/protocol_validator.py`) | Full core + extension field validation against `protocol-core-v1.0.yaml`, <5ms | On demand, by any agent or script that imports it | Any DELEGATE/HANDBACK dict |
| **`scripts/check_protocol_compliance.py`** | Same validator, run over a directory of DELEGATE/HANDBACK YAML files | CI gate (invoked explicitly; no-op if no such files are present) | Files on disk (e.g. `docs/examples/`, ad hoc exports) |
| **`.githooks/pre-commit`** DELEGATE/HANDBACK section | Regex-based core-field presence/format checks (task_id pattern, agent enum, status enum, metrics sub-fields, secret-pattern scan) on staged `.yaml`/`.yml` files that look like a DELEGATE or HANDBACK | `git commit` | Files about to be committed |
| **PreToolUse hook** (`renderer/scripts/claude-delegate-guard.py`) | Deliberately not a thin wrapper around the validator above (documented in its own docstring) — checks that a live Claude Code Agent-tool spawn targeting one of the eight framework roles carries a well-formed DELEGATE block in its prompt | Every Agent/Task-tool spawn in a Claude Code session | The one path the other three layers cannot see: an in-session spawn that never touches disk |

None of these layers enforces the *calling* agent's role, ancestry, spawn depth, or
fan-out count — that is the spawning agent's own judgment call per
[Recursion Limits](../src/AGENTS.md#recursion-limits) in `src/AGENTS.md`.

There is no filesystem queue and no `enqueue()` gateway — the durable audit record is
the harness session transcript itself (every DELEGATE as a spawn prompt, every HANDBACK
as that spawn's result), not a separately-written file. `check_protocol_compliance.py`
and the schema tooling above remain useful for validating DELEGATE/HANDBACK YAML
wherever it appears on disk (examples, exports, ad hoc authoring) — they no longer have
a queue directory to scan by default.

### 3.1 Common Mistakes

```
❌ scope: "Fix the bug"                    → Add file:line, root cause, expected behavior (>=15 words)
❌ plan: ["Implement everything"]           → Number every step; name specific files (>=2 steps, >=3 words each)
❌ success_criteria: ["Works well"]         → What test proves it? What metric confirms it?
❌ role: senior_engineer                    → Use the canonical field name "agent:" and hyphenated value "senior-engineer"
❌ type: DELEGATE                           → Use "handoff_type:" (type: is a deprecated, warned alias)
❌ quality_score: 92                        → Use "metrics.quality: 0.92" (0.0-1.0 float, nested under metrics)
❌ status: complete / failed                → Use "success" / "failure" ("complete"/"failed" are not valid)
❌ task_id: 2026-05-09-fix-bug              → Date prefix is no longer required; plain kebab-case, 3-50 chars
```

---

## 4. Quality Assessment

There is no automated multi-layer composite-scoring formula in the current
system — the earlier Layer 1/2/3 weighted-percentage design (`quality_validator.py`)
was part of the pre-slimdown Python orchestration pipeline and no longer exists.
Quality is:

1. **Self-reported by the completing agent** in `metrics.quality` (0.0–1.0), based
   on how fully `success_criteria` were met.
2. **Reviewed by convention, not automatically**, by Quality Engineer: the spawning
   agent MAY spawn Quality Engineer after a HANDBACK to verify `success_criteria`
   against the actual delivered change, run the project's lint/test/build gate, and
   adjust `metrics.quality` if the self-report was optimistic. This is a judgment
   call per `src/AGENTS.md`'s Quality Engineer role definition, not a scripted gate.
3. **Disputes go to Lead Engineer**, and systemic quality patterns across multiple
   tasks go to Model Engineer (routing/model recommendations) or Principal Engineer
   (if the pattern indicates a deeper problem).

There is no fixed numeric acceptance threshold (no "90–100 auto-accept, 70–79
manual review" table) — the spawning agent applies the HANDBACK's `status` per
`src/AGENTS.md`'s [Applying the HANDBACK](../src/AGENTS.md#direct-sub-agent-spawn-execution-model):
`success` → done; `partial` → re-delegate the remainder; `blocked` → surface to the
user; `escalate` → re-delegate the ESCALATION block at the higher tier.

---

## 5. Escalation

When an agent hits an escalation trigger (see its role's `src/AGENTS.md`
definition for that role's specific triggers), it stops implementation work and
returns a HANDBACK with `status: escalate`, embedding an **ESCALATION packet**
under the `escalation:` key:

```yaml
# Embedded in HANDBACK under the `escalation:` key
task_id: my-task-identifier
type: ESCALATION              # ESCALATION packets retain type: (not a DELEGATE/HANDBACK)
from_role: senior-engineer
to_role: principal-engineer
reason: |
  Root cause spans multiple services — requires cross-service analysis beyond
  Senior's authority.
findings_so_far: |
  Summary of what was discovered before escalation, so the receiving agent starts
  with full context and does not re-investigate the same ground.
recommended_focus:
  - Specific area to investigate
```

The receiving agent (the Orchestrator, or whichever role spawned the escalating
agent) reads the ESCALATION block in-context, constructs a new DELEGATE targeting
`to_role` with the escalation content inlined in `context`, appends its own role to
`ancestry`, and spawns `to_role` directly — subject to the same depth/fan-out/cycle
checks (max delegation depth 3, max fan-out 5) as any other spawn. Full mechanics,
the worked example (Engineer → Senior → Lead), and the recursion-limit rules live
in `src/AGENTS.md` — see [ESCALATION Packet
Format](../src/AGENTS.md#escalation-packet-format) and [Recursion
Limits](../src/AGENTS.md#recursion-limits); this document does not duplicate them.

---

## 6. Glossary

| Term | Definition |
|---|---|
| **DELEGATE** | Structured message transferring a task from a spawning agent to a specialist agent |
| **HANDBACK** | Structured result message returned by a specialist agent, in-context, as its spawn call's result |
| **ESCALATION packet** | Block embedded in a HANDBACK's `escalation:` key when `status: escalate`, naming the target role and carrying findings-so-far |
| **Audit trail** | The harness session transcript itself — every DELEGATE as a spawn prompt, every HANDBACK as that spawn's result; there is no separate filesystem record |
| **`ancestry`** | Root-to-parent role chain on a DELEGATE, used for cycle detection and max-depth enforcement |
| **`metrics.quality`** | Self-reported (and optionally QE-reviewed) delivery quality, 0.0–1.0 |
| **Core fields** | Required DELEGATE/HANDBACK fields, strictly validated |
| **Extension fields** | Optional fields, loosely validated, forward-compatible (unknown fields warn, never fail) |

---

## 7. See Also

- [`src/AGENTS.md`](../src/AGENTS.md) — agent roster, routing decision tree, role
  definitions, Direct Sub-Agent Spawn Execution Model, Recursion Limits, ACK Protocol
- [`docs/specs/protocol-core-v1.0.yaml`](specs/protocol-core-v1.0.yaml) — the
  normative schema
- [`docs/CORE-PROTOCOL-QUICKSTART.md`](CORE-PROTOCOL-QUICKSTART.md) — a 30-minute
  quickstart covering only the core-field subset
