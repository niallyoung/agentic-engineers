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

The canonical execution model is **direct sub-agent spawn**: the spawning agent
constructs a DELEGATE block and passes it directly as the prompt of a sub-agent
spawn (the harness's Agent/Task tool); the HANDBACK returns synchronously as that
spawn call's result, in-context. The harness session transcript itself (every
DELEGATE as a spawn prompt, every HANDBACK as that spawn's result) is the durable
audit record — this is what makes a DELEGATE/HANDBACK *count* (`docs/SPEC.md`
clause 4). See [`src/AGENTS.md` > Direct Sub-Agent Spawn Execution
Model](../src/AGENTS.md#direct-sub-agent-spawn-execution-model) for the full flow.

A second, additive record exists alongside it: agents append per-event JSONL to a
queryable audit log per `docs/SPEC.md` clause 7 — see [§7a Audit Events
(JSONL)](#7a-audit-events-jsonl). It does not change the paragraph above; it is a
metrics/event log derived from the same events, not an alternate way for a
DELEGATE/HANDBACK to "count."

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
spec_version: "1.0"
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
`criteria_results`, `error`, `interjections` (operator interjections received
mid-task, each with `ts`, `source`, `directive`, `disposition`). `skill_feedback` (structured per-skill feedback
consumed by the `skill-improvement-feedback` pattern) is accepted at runtime as a
forward-compatible field — see `protocol_validator.py`'s
`KNOWN_HANDBACK_RUNTIME_FIELDS` and `src/skills/skill-improvement-feedback/SKILL.md`
for its shape.

```yaml
handoff_type: HANDBACK
spec_version: "1.0"
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

Three independent layers check DELEGATE/HANDBACK compliance. They overlap
deliberately — no single layer is a complete gate on its own.

| Layer | What it checks | When it runs | Scope |
|---|---|---|---|
| **`protocol-validator` skill** (`src/skills/protocol-validator/scripts/protocol_validator.py`) | Full core + extension field validation against `protocol-core-v1.0.yaml`, <5ms | On demand, by any agent or script that imports it | Any DELEGATE/HANDBACK dict |
| **`.githooks/pre-commit`** DELEGATE/HANDBACK section | Regex-based core-field presence/format checks (task_id pattern, agent enum, status enum, metrics sub-fields, secret-pattern scan) on staged `.yaml`/`.yml` files that look like a DELEGATE or HANDBACK | `git commit` | Files about to be committed |
| **PreToolUse hook** (`renderer/scripts/claude-delegate-guard.py`) | Deliberately not a thin wrapper around the validator above (documented in its own docstring) — checks that a live Claude Code Agent-tool spawn targeting one of the eight framework roles carries a well-formed DELEGATE block in its prompt | Every Agent/Task-tool spawn in a Claude Code session | The one path the other two layers cannot see: an in-session spawn that never touches disk |

### 3.1 Per-Layer Field Coverage

The three enforcement layers cover different fields and operate at different times; no layer enforces all fields:

| Core Field | `protocol-validator` | `.githooks/pre-commit` | `PreToolUse` hook | Coverage |
|---|---|---|---|---|
| `handoff_type` | ✅ | ✅ | ✅ | All three |
| `task_id` format | ✅ | ✅ | ✅ | All three |
| `agent` enum | ✅ | ✅ | ✅ | All three |
| `scope` >=15 words | ✅ | — | ✅ | Skill + PreToolUse |
| `spec_version` | ✅ | — | — | Skill only |
| `skill` exists | ✅ | — | — | Skill only |
| `status` enum | ✅ | ✅ | — | Skill + pre-commit |
| `metrics` sub-fields | ✅ | ✅ | — | Skill + pre-commit |
| Secret patterns | — | ✅ | — | pre-commit only |
| `depth` <= 3 (when declared) | — | — | ✅ | PreToolUse only |
| `ancestry` cycle (when declared) | — | — | ✅ | PreToolUse only |

**Reality:** The `protocol-validator` skill is authoritative for *completeness* (all required fields); `.githooks/pre-commit` is a fast gate for committed files; `PreToolUse` guard is the gate for in-session Agent-tool spawns. An agent may also *self-enforce* its role's `spawn` recursion limits (depth, fan-out) before issuing a DELEGATE to a sub-agent — that is not a validator responsibility.

**Recursion limits are partially enforced.** The `PreToolUse` guard
(`renderer/scripts/claude-delegate-guard.py`) *does* reject a DELEGATE whose `depth`
exceeds 3, and *does* reject one whose `agent` already appears in its own `ancestry`
(a cycle). Two caveats bound that:

- `depth` and `ancestry` are **optional** extension fields. A DELEGATE that omits them
  is not checked — the guard cannot infer a depth it was not told.
- The guard sees **one spawn at a time**, so it cannot count concurrent fan-out. The
  max-fan-out-5 limit is not mechanically enforced anywhere.

No layer enforces the *calling* agent's role or fan-out count; those remain the spawning
agent's own judgment call per [Recursion Limits](../src/AGENTS.md#recursion-limits) in
`src/AGENTS.md`. The guard is Claude-harness-specific; no other harness has an
equivalent.

There is no filesystem queue and no `enqueue()` gateway — the durable audit record for
protocol validity is the harness session transcript itself (every DELEGATE as a spawn
prompt, every HANDBACK as that spawn's result), not a separately-written file. (A
separate, queryable JSONL event log does exist per `docs/SPEC.md` clause 7 — [§7a Audit
Events (JSONL)](#7a-audit-events-jsonl) — but none of these three validation layers read
or write it; it is a metrics/event record, not part of DELEGATE/HANDBACK enforcement.)
The `protocol-validator` skill remains the way to validate a DELEGATE/HANDBACK dict or
file on demand, in-process.

### 3.2 Common Mistakes

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

## 6. Cost Guardrail (Advisory)

**Why:** `docs/LANDSCAPE.md` § "What harnesses still lack" names runaway subagent cost as
the multi-agent niche's loudest pain point. The protocol already carries the fields
needed to guard against it. This section documents a **convention on existing fields**,
not a wire-format change — `docs/specs/protocol-core-v1.0.yaml` and
`renderer/scripts/claude-delegate-guard.py` are untouched by it, exactly like the
[Recursion Limits](../src/AGENTS.md#recursion-limits) it mirrors.

**The fields:** DELEGATE's `tokens_estimate` (int) and `budget` (USD float) — both
already defined as optional extensions in [§2.1](#21-delegate), both previously
under-populated in practice.

**The convention** (SHOULD/MUST language below applies to *Orchestrator behavior*, not
to schema validation):

1. The Orchestrator SHOULD set both `tokens_estimate` and `budget` on every DELEGATE it
   issues, estimated from task complexity and the target role's typical cost share (see
   the Cost Target Distribution comparison in [§7](#7-handback-cost-rollup) below).
2. Before spawning, if the operator has configured a session/task budget ceiling and a
   DELEGATE's `tokens_estimate`/`budget` would exceed it, the Orchestrator MUST NOT
   spawn. Instead — without ever calling the Agent/Task tool — it synthesizes a HANDBACK
   directly:
   ```yaml
   handoff_type: HANDBACK
   task_id: <the DELEGATE's own task_id>
   status: blocked
   output: "Refused to spawn — cost guardrail"
   error: "budget: estimated 0.35 exceeds limit 0.20"
   metrics: {quality: 0.0, tokens: 0, cost: 0.0, duration_seconds: 0.0}
   ```
   This mirrors the existing recursion-limit refusal pattern
   (`src/AGENTS.md` § [Recursion Limits](../src/AGENTS.md#recursion-limits)): stop, do
   not silently proceed or invent a workaround, and report `status: blocked` naming
   which limit was hit and why. The receiving agent (or the operator) decides how to
   proceed — split the task, raise the budget, or drop it.
3. A HANDBACK's required `metrics.tokens`/`metrics.cost` (already core fields — no
   change) are what closes the loop: they are `scripts/handback_rollup.py`'s input
   (see [§7](#7-handback-cost-rollup)).

**Enforcement: orchestrator-self + QE review.** Nothing mechanical enforces this — no
schema change, no `PreToolUse` hook change, no new validator layer in
[§3](#3-validation--enforcement). Like the recursion/fan-out limits it sits beside, this
is the spawning agent's own judgment call, checked opportunistically when Quality
Engineer reviews a session's DELEGATE/HANDBACK trail — not a runtime gate. Stating
anything stronger than that would misrepresent what actually runs.

---

## 7. HANDBACK Cost Rollup

`scripts/handback_rollup.py` (backlog item #10, `docs/LANDSCAPE.md` § Bonus-Task
Backlog) is a deterministic, dependency-light (stdlib + PyYAML) script that reads one or
more sources of HANDBACK YAML — files or stdin, fenced or bare, one or many
`---`-separated documents per source, exactly the shapes an agent actually emits in a
session transcript — and aggregates them per agent-role into a compact report: count,
total tokens, total cost, mean quality, mean duration.

**Advisory-only, by design** (`docs/SPEC.md` clause 3, "Python is advisory only"): the
script *reports*; it never *gates*. It always exits `0` on well-formed input regardless
of what the aggregated numbers show — a heavy-cost role or a quality dip is information
for a human or for Quality Engineer, not a build failure. Malformed candidate documents
(invalid YAML, or a HANDBACK missing/violating a required field) are skipped with a
warning printed in the report, never raised as an exception.

**The `agent` field convention:** the canonical HANDBACK schema ([§2.2](#22-handback))
carries no `agent`/role field — only the originating DELEGATE names its target `agent`.
To attribute cost per role, the rollup relies on a convention, not a schema requirement:
a HANDBACK MAY echo the DELEGATE's `agent` value back as its own `agent:` (or `role:`)
field. This is an ordinary forward-compatible extra field per [§1](#1-what-this-protocol-is)'s
"unknown fields warn, never fail" rule — not a wire-format change. A HANDBACK that omits
it is still aggregated, just grouped under the synthetic role `unknown`; the omission
alone is never treated as malformed.

**Cost Target Distribution comparison:** where `docs/SPEC.md`'s Agent Roster table still
defines one — as of SPEC-2026-005 it does: Orchestrator 55% · Engineer 18% · Senior
Engineer 8% · Quality Engineer 8% · Lead Engineer 3% · Model Engineer 3% · Principal
Engineer 3% · Security Engineer 2% — the rollup prints each role's actual cost share
next to that target. `tests/test_handback_rollup.py::test_cost_target_distribution_matches_spec`
fails loudly if the script's copy of the distribution drifts from the live `docs/SPEC.md`
text; if a future SPEC.md revision removes the table, that test (and the comparison
feature) should be updated to reflect its absence rather than comparing against a
fabricated target.

```
python3 scripts/handback_rollup.py session1.yaml session2.yaml
python3 scripts/handback_rollup.py --json < session.log
```

`scripts/handback_rollup.py` also accepts `--events <path...>`, reading the clause-7
JSONL audit log described in [§7a](#7a-audit-events-jsonl) instead of (or alongside)
HANDBACK YAML sources — see that section for details.

---

## 7a. Audit Events (JSONL)

**Two records, two purposes.** [§1](#1-what-this-protocol-is)'s transcript-as-audit-record
model is unchanged by this section: the harness session transcript is still what makes
a DELEGATE/HANDBACK *count*, and nothing here alters that. `docs/SPEC.md` clause 7
requires a **second, additive** record: a queryable, append-only JSONL event log,
written by agents, that tooling can consume without re-parsing a session transcript.

**Path:** `~/.agentic-engineers/{harness}/{session-id}/audit/events-YYYY-MM-DD.jsonl`
— one JSON object per line, append-only. Agents append; they MUST NOT rewrite,
reorder, truncate, or delete prior lines. Corrections are new events, never edits.

**Required events:** `delegate_issued`, `subagent_spawned`, `handback_received`,
`gate_result`, `escalation`, `refusal`, `limit_exceeded`, `operator_interjection`.

**Required fields on every event:** `ts` (ISO-8601 UTC, computed by the append helper
— never trusted from caller input), `event`, `task_id`, `parent_task_id` (may be
`null` for a root-level event, but the key is always present), `depth`, `agent_role`,
`agent_model`, `status`, plus `tokens`/`cost` where applicable. An optional `resolves_task_id`
field MAY link a remediation event chain to the failed/blocked task it addresses.

**The append helper:** `scripts/audit_append.py` (`docs/SPEC.md` § COMPLETE SCRIPT
INVENTORY) is the deterministic, stdlib-only utility agents invoke to format, validate,
and append one event. It is advisory Python under [§1](#1-what-this-protocol-is)'s
"Python is advisory only" rule (`docs/SPEC.md` clause 3): the agent decides *when* and
*what* to log; the helper owns formatting/validation/the actual append.

```bash
python3 scripts/audit_append.py --event delegate_issued \
  --task-id my-task-001 --parent-task-id orchestrator-root --depth 1 \
  --agent-role engineer --agent-model claude-haiku-4.5 --status success
```

**Validation is the one permitted failure mode.** An unknown `event` name or a missing
required field is rejected — exit 2, a clear stderr message. Any other failure (e.g. an
unwritable audit directory) exits 1. Either way, this is a **warning, never a
blocker**: a failed append MUST NOT stop a DELEGATE, a spawn, or a HANDBACK from
proceeding. See `src/AGENTS.md` § Audit Events for the full per-role duty table (which
role appends which events at which lifecycle point).

**Consuming it:** `scripts/handback_rollup.py --events <path...>` reads this format
directly, aggregating `handback_received` events' `agent_role`/`tokens`/`cost`/`status`
fields into the same per-role report [§7](#7-handback-cost-rollup) produces from
HANDBACK YAML — the two input modes can be mixed in one invocation. Advisory-only, same
as the rest of §7: it reports, it never gates.

---

## 8. Glossary

| Term | Definition |
|---|---|
| **DELEGATE** | Structured message transferring a task from a spawning agent to a specialist agent |
| **HANDBACK** | Structured result message returned by a specialist agent, in-context, as its spawn call's result |
| **ESCALATION packet** | Block embedded in a HANDBACK's `escalation:` key when `status: escalate`, naming the target role and carrying findings-so-far |
| **Audit trail** | Two records: the harness session transcript (every DELEGATE as a spawn prompt, every HANDBACK as that spawn's result) is what makes a DELEGATE/HANDBACK count — no separate file needed for that; a second, additive JSONL event log ([§7a](#7a-audit-events-jsonl)) is a queryable metrics/event record agents append via `scripts/audit_append.py` per `docs/SPEC.md` clause 7 |
| **Audit Events JSONL** | The clause-7 append-only event log at `~/.agentic-engineers/{harness}/{session-id}/audit/events-YYYY-MM-DD.jsonl` — see [§7a](#7a-audit-events-jsonl) |
| **`ancestry`** | Root-to-parent role chain on a DELEGATE, used for cycle detection and max-depth enforcement |
| **`metrics.quality`** | Self-reported (and optionally QE-reviewed) delivery quality, 0.0–1.0 |
| **Core fields** | Required DELEGATE/HANDBACK fields, strictly validated |
| **Extension fields** | Optional fields, loosely validated, forward-compatible (unknown fields warn, never fail) |
| **Cost Guardrail** | Convention (§6) on the existing `tokens_estimate`/`budget` DELEGATE extensions plus Orchestrator refusal behavior; not a schema or hook change |
| **HANDBACK Cost Rollup** | `scripts/handback_rollup.py` (§7) — advisory per-role cost/quality report derived from HANDBACK `metrics` |

---

## 9. See Also

- [`src/AGENTS.md`](../src/AGENTS.md) — agent roster, routing decision tree, role
  definitions, Direct Sub-Agent Spawn Execution Model, Recursion Limits, Cost
  Guardrail, ACK Protocol
- [`docs/specs/protocol-core-v1.0.yaml`](specs/protocol-core-v1.0.yaml) — the
  normative schema
- [`docs/CORE-PROTOCOL-QUICKSTART.md`](CORE-PROTOCOL-QUICKSTART.md) — a 30-minute
  quickstart covering only the core-field subset
- [`scripts/handback_rollup.py`](../scripts/handback_rollup.py) — the HANDBACK cost
  rollup script (§7), including its `--events` JSONL mode (§7a)
- [`scripts/audit_append.py`](../scripts/audit_append.py) — the clause-7 audit event
  append helper (§7a)
