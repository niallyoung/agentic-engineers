---
title: The DELEGATE/HANDBACK Protocol
spec_version: "1.0"
status: Draft
updated: 2026-08-14
canonical_home: https://github.com/agentic-engineers/agentic-engineers/blob/main/docs/specs/DELEGATE-HANDBACK.md
normative_schema: docs/specs/protocol-core-v1.0.yaml
---

# The DELEGATE/HANDBACK Protocol

## 1. Abstract

DELEGATE/HANDBACK is a message-pair format for delegating a bounded unit of
work from one AI agent to another and reporting its result back. A
**DELEGATE** carries a task's scope, context, plan, and success criteria to a
receiving agent; a **HANDBACK** carries that agent's outcome, status, and
quantitative metrics back to the delegator. The pair is small enough to embed
directly in an agent-spawn call's prompt and result — no broker, queue, or
network hop required — while structured enough to validate, audit, and feed
cost/quality routing decisions.

This document specifies the message formats, delegation-lifecycle semantics,
three conformance levels, and the protocol's relationship to adjacent work
(MCP, A2A, AGENTS.md, Agent Skills, and proprietary handoff mechanisms in
other agent frameworks).

### Status of This Document

This is a **draft**, versioned in lockstep with the protocol schema it
describes (`spec_version: "1.0"`, §9), extracted from and kept synchronized
with the production implementation in the
[agentic-engineers](https://github.com/agentic-engineers/agentic-engineers)
repository — this document's canonical home. `docs/specs/protocol-core-v1.0.yaml`
(JSON-Schema draft-07) is the normative machine-readable schema this document
narrates; where the two disagree, the schema wins, and where the schema and
its runtime validator disagree, the validator wins (§6). Not submitted to any
standards body — published as prior art for the gap described in §2.

---

## 2. Motivation

Every multi-agent framework surveyed in 2026 ships *some* mechanism for
handing a task from one agent to another — but no two agree on its shape, and
none treats it as a portable, independently specifiable artifact. OpenAI's
Agents SDK represents a handoff as a tool-call transfer plus conversation
history; Microsoft Agent Framework wraps it in a dedicated orchestration
layer; IBM's ACP/BeeAI frames it as structured handoff negotiation; A2A
defines task semantics for service-to-service calls. Each is coupled tightly
to its host framework's runtime. Academic surveys of LLM-agent
externalization have flagged the absence of a shared delegation/handoff
vocabulary as an open gap, distinct from the tool-calling layer (MCP) and the
service-to-service layer (A2A).

That gap is where DELEGATE/HANDBACK sits: a **format**, not a runtime — it
makes no assumption about transport. In this implementation, delegation
happens by passing the DELEGATE block as a sub-agent spawn's prompt, with the
HANDBACK returned as that spawn call's result, in-context; no queue, broker,
or network protocol is prescribed or required. Two things motivated
formalizing it as a standalone document rather than internal convention:

1. **Reusable independent of any one roster.** Nothing in the message format
   depends on the eight specific roles this repository happens to define —
   any system that spawns one agent to do bounded work for another can adopt
   the same field set.
2. **First-mover opportunity with a matching risk.** Whatever a body like the
   Linux Foundation's Agentic AI Foundation (AAIF) eventually blesses for this
   layer will likely win by default. Publishing this format now, as a legible,
   versioned, vendor-neutral document, costs little and stakes an honest claim
   to prior art.

Neither point claims superiority over any proprietary handoff mechanism —
each suits its own framework. The claim is only that the *format* is
separable from the runtime, and that separating it is useful.

---

## 3. Terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" are to be interpreted as
described in RFC 2119, as clarified by RFC 8174 (significance applies only
when the terms appear in all capitals).

- **DELEGATE** — a message from a *delegating agent* to a *receiving agent*,
  assigning a bounded, self-contained task.
- **HANDBACK** — the message a receiving agent returns on completion (or
  non-completion) of a DELEGATE, reporting a terminal `status` and
  quantitative `metrics`.
- **ESCALATION packet** — a block embedded inside a HANDBACK's `escalation`
  field when `status: escalate`, naming the role to re-route to and carrying
  findings so far (§5.4).
- **roster** — the recognized agent roles a deployment permits as a
  DELEGATE's `agent` target. This document's examples use an eight-role
  roster (`orchestrator`, `engineer`, `senior-engineer`, `lead-engineer`,
  `principal-engineer`, `security-engineer`, `quality-engineer`,
  `model-engineer`); the roster itself is deployment-defined, not part of
  this protocol's normative core.
- **harness** — the surrounding agentic coding environment (CLI, IDE
  extension, SDK runtime) providing the primitive used to dispatch a
  DELEGATE — in the reference implementation, an "Agent"/"Task" tool call
  that spawns a sub-agent and returns its result.
- **direct spawn** — the reference implementation's delegation mechanism: the
  delegating agent passes a DELEGATE block directly as a sub-agent spawn's
  prompt; the HANDBACK returns synchronously as that call's result. Not the
  only valid transport (§5.1), but the only one this document's reference
  implementations exercise.
- **producer / consumer / enforcer** — the three conformance roles (§6).

---

## 4. Message Formats

Both schemas are defined normatively in `protocol-core-v1.0.yaml`
(JSON-Schema draft-07), which distinguishes strictly-required **core fields**
from loosely-validated, forward-compatible **extension fields** (an
unrecognized extension field MUST NOT cause rejection; it MAY warn). The
tables below were generated by parsing the schema programmatically, not
hand-transcribed (§4.3), plus two fields the schema does not yet formally
list despite their use in the reference implementation's own docs/examples.

### 4.1 DELEGATE

**Core fields — 9, all REQUIRED:**

| Field | Type | Rule |
|---|---|---|
| `task_id` | string | Kebab-case, 3–50 chars: `^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$` |
| `spec_version` | string | Protocol schema version authorizing this task (e.g. `"1.0"`) |
| `handoff_type` | string | MUST equal `DELEGATE` — the message-type discriminator |
| `skill` | string | Name resolving to an installed skill/capability the receiver will load |
| `agent` | string | Target role, drawn from the deployment's roster |
| `scope` | string | What/to what/out-of-scope boundaries. MUST be >= 15 words |
| `success_criteria` | array\<string\> | Non-empty; measurable outcomes defining "done" |
| `plan` | array\<string\> | >= 2 ordered steps, each >= 3 words |
| `context` | string \| array\<string\> | Files/errors/prior art. >= 20-word string, or non-empty array |

**Extension fields — OPTIONAL, forward-compatible:**

| Field | Type | Purpose |
|---|---|---|
| `model` | string | Specific model identifier requested |
| `effort` | enum | `low`\|`medium`\|`high`\|`max` — reasoning-effort tier |
| `parent_task_id` | string | `task_id` of the DELEGATE that spawned this one |
| `parallel_plan` | array\<string\> | Sub-tasks that may execute concurrently |
| `tokens_estimate` | integer | Pre-execution token-budget estimate |
| `budget` | number | Monetary ceiling in USD |
| `priority` | integer | Scheduling priority, 1 (lowest)–10 (highest) |
| `deadline` | string | ISO-8601 timestamp |
| `dependencies` | array\<string\> | `task_id`s that must complete first |
| `retry_context` | object | Diagnostic context from a prior failed attempt |
| `token_quota` | object | Structured budget (`total`, optional `input`/`output`/`enforcement`/`source`) |

> **Not yet in the normative extensions list, but in active use:** `ancestry`
> (root-to-parent chain of roles a DELEGATE descended through) is documented
> extensively in this implementation's docs and required by convention at
> spawn depth > 0, for cycle detection and depth-limit enforcement (§5.3). It
> is absent from the schema's extension list, so the reference validator
> treats it as unrecognized — a forward-compatible warning, not a rejection.
> Implementers wanting depth/ancestry semantics SHOULD use this field name
> for interoperability ahead of its formal schema inclusion.

**Worked example:**

```yaml
handoff_type: DELEGATE
spec_version: "1.0"
task_id: add-rate-limit-header
skill: engineer
agent: engineer
scope: |
  Add a X-RateLimit-Remaining response header to the public /v1/search endpoint,
  computed from the existing token-bucket limiter state; do not change limiter
  thresholds or add new endpoints.
context:
  - "Limiter implementation: src/api/ratelimit.py:12-58 (TokenBucket class)"
  - "Endpoint handler: src/api/search.py:40 (search_handler)"
plan:
  - "Read TokenBucket.remaining() to confirm it returns an int, not a float"
  - "Add the header in search_handler's response-building path"
  - "Add a test asserting the header value decreases across repeated calls"
success_criteria:
  - "GET /v1/search response includes X-RateLimit-Remaining on every call"
  - "pytest tests/test_search.py passes with zero failures"
effort: medium
```

### 4.2 HANDBACK

**Core fields — 6, all REQUIRED:**

| Field | Type | Rule |
|---|---|---|
| `task_id` | string | MUST exactly match the originating DELEGATE's `task_id` |
| `spec_version` | string | Protocol schema version used during execution |
| `handoff_type` | string | MUST equal `HANDBACK` |
| `status` | enum | `success`\|`failure`\|`partial`\|`blocked`\|`escalate` (§5.5) |
| `output` | any | Result payload; key MUST be present, value MAY be any type |
| `metrics` | object | All four sub-fields REQUIRED: `quality` (0.0–1.0), `tokens` (non-negative int), `cost` (non-negative number, USD), `duration_seconds` (non-negative number) |

**Extension fields — OPTIONAL, forward-compatible:**

| Field | Type | Purpose |
|---|---|---|
| `token_usage` | object | Structured input/output/cached/total breakdown, superseding flat `metrics.tokens`. (Schema-wise this is a `core_fields` entry that is not in `required` — optional in practice, listed here with the other optional fields.) |
| `escalations` | integer | Count of times this task was escalated during execution |
| `model_assessment` | string | Reviewer's judgement on whether the model tier fit the task |
| `confidence` | number | Agent's self-reported confidence, 0.0–1.0 |
| `retry_count` | integer | Internal retries performed |
| `model_used` | string | Actual model that executed the task |
| `effort_actual` | enum | Actual effort tier expended |
| `children_created` | array\<string\> | `task_id`s of sub-DELEGATEs spawned during execution |
| `children_results` | object | Per-child result summary, keyed by child `task_id` |
| `flags` | array\<string\> | Free-form advisory flags |
| `criteria_results` | array | Per-`success_criteria`-item evidence and gaps |
| `error` | string | Error detail when `status` is `failure` or `blocked` |
| `interjections` | array | Operator interjections received mid-task, each recording the directive and its disposition (`required: [ts, source, directive, disposition]`) |

> **Two more fields are in active documented use but absent from the schema's
> extension list** — do not conflate them: `skill_feedback` (structured
> feedback for a skill-improvement loop) is accepted by the reference
> validator as a known forward-compatible field but is not schema-defined.
> `escalation` (singular — the embedded ESCALATION packet, §5.4) is
> documented as the canonical carrier for that packet, but is *neither*
> schema-defined *nor* on the validator's known-fields allowlist — currently
> indistinguishable from any other unrecognized field. It is distinct from
> the schema-defined `escalations` (plural, an integer count) above, whose
> near-identical name invites confusion with it.

**Worked example:**

```yaml
handoff_type: HANDBACK
spec_version: "1.0"
task_id: add-rate-limit-header
status: success
output: |
  Added X-RateLimit-Remaining to search_handler's response in src/api/search.py,
  sourced from TokenBucket.remaining(). Added test_rate_limit_header_decreases
  to tests/test_search.py; full suite passes (58 tests).
metrics:
  quality: 0.95
  tokens: 1180
  cost: 0.012
  duration_seconds: 38
confidence: 0.93
model_used: claude-haiku-4.5
```

### 4.3 Schema-Parity Verification

The tables above come from loading the schema and enumerating its keys, not
hand-transcription:

```python
import yaml
schema = yaml.safe_load(open("docs/specs/protocol-core-v1.0.yaml"))
schema["delegate"]["required"]            # -> the 9 required DELEGATE fields
schema["delegate"]["extensions"].keys()   # -> the 11 DELEGATE extensions
schema["handback"]["required"]            # -> the 6 required HANDBACK fields
schema["handback"]["extensions"].keys()   # -> the 12 HANDBACK extensions
```

`ancestry`, `skill_feedback`, and `escalation` (singular) were confirmed
absent from every key in the loaded schema by direct search — hence the
call-outs above rather than silent inclusion in the generated tables.

---

## 5. Delegation Semantics

### 5.1 Lifecycle

1. A delegating agent constructs a DELEGATE for a bounded task.
2. It dispatches the DELEGATE. The reference implementation uses **direct
   spawn**: the DELEGATE is passed as a sub-agent spawn's prompt, and the
   HANDBACK returns synchronously as that call's result. Nothing in the
   message format requires this transport — a queue, RPC call, or message
   bus could carry the same two shapes — but direct spawn is the only one
   this document's reference implementations exercise or make claims about.
3. The receiving agent performs the task (MAY itself issue further DELEGATEs
   to sub-agents, §5.3) and returns a HANDBACK.
4. The delegating agent applies the HANDBACK's `status` (§5.5) to decide what
   happens next.

### 5.2 Correlation

`task_id` is the sole correlation key: a HANDBACK's `task_id` MUST exactly
match the DELEGATE that produced it. There is no separate transaction or
session identifier in the core schema — deployments needing to correlate
across a longer-lived session MAY use `parent_task_id` chains or an
out-of-band identifier carried in `context`.

### 5.3 Depth, Ancestry, and Fan-Out

A receiving agent MAY itself delegate further. This document sets no
normative ceiling on depth or fan-out, but the reference implementation's
convention — RECOMMENDED as a default absent a stronger reason to differ — is:

- **Max delegation depth: 3**, measured in spawn hops from the root DELEGATE
  (depth 0 = the top-level entry point). An agent at depth 3 SHOULD NOT
  delegate further; it executes directly or declines.
- **Max fan-out: 5** concurrent sub-agents per delegating agent. Additional
  independent work waits for one of the first five to resolve, or is
  consolidated into a single DELEGATE.
- **Ancestry tracking.** Any DELEGATE issued at depth > 0 SHOULD carry
  `ancestry` (§4.1) — the root-to-parent role chain, inclusive. Before
  delegating, an agent SHOULD check whether its target role already appears
  in `ancestry`; if so, it SHOULD refuse rather than complete a cycle.

**Enforcement is partial.** Of the three rules above, two are mechanically
checked at delegation time by the reference spawn-time guard
(`renderer/scripts/claude-delegate-guard.py`, §6): it rejects a DELEGATE
declaring `depth` greater than 3, and rejects one whose `agent` already appears
in its own `ancestry` list. Both checks are conditional on the DELEGATE
*declaring* those optional fields — a DELEGATE that omits `depth` or `ancestry`
passes unchecked, since the guard cannot infer what it was not told.

Fan-out is **not** enforced: the guard is invoked once per spawn and holds no
state across spawns, so it cannot count concurrent sub-agents. That rule remains
self-enforced by convention, as does the choice to populate `ancestry` honestly.
A conformant *enforcer* (§6) MAY make the remaining check mechanical.

### 5.4 The ESCALATION Packet

When a receiving agent determines a task exceeds its authority, it returns a
HANDBACK with `status: escalate` and embeds an ESCALATION packet (the
`escalation` field, §4.2) naming where the work should go next:

```yaml
# Embedded in HANDBACK under the escalation field
task_id: my-task-identifier
type: ESCALATION            # keeps the older `type:` field — not itself a
                             # DELEGATE or HANDBACK
from_role: senior-engineer
to_role: principal-engineer
reason: |
  Root cause spans multiple services — requires cross-service analysis beyond
  this role's authority.
findings_so_far: |
  Summary of what was discovered before escalating, so the receiving agent
  starts with full context instead of re-investigating the same ground.
recommended_focus:
  - Specific area to investigate next
```

The receiving delegating agent constructs a new DELEGATE targeting `to_role`,
inlines `reason` and `findings_so_far` into the new DELEGATE's `context`,
appends its own role to `ancestry`, and delegates again — subject to the same
depth/fan-out/cycle conventions as any other delegation (§5.3).

### 5.5 Status Semantics

A HANDBACK's `status` is its terminal disposition:

| Status | Meaning | Typical delegator response |
|---|---|---|
| `success` | All `success_criteria` met | Accept; mark done |
| `failure` | Attempted but criteria not met | Rework, reroute, or surface to a human |
| `partial` | Some criteria met; remainder blocked/deferred | Re-delegate the remaining scope |
| `blocked` | Could not start/continue; external dependency needed | Surface the blocker; do not silently retry |
| `escalate` | Requires a higher-authority agent or human | Read the ESCALATION packet (§5.4); re-delegate at the named role |

`complete` and `failed` are common near-miss values in ad hoc
implementations of similar protocols; they are NOT valid values of this field.

---

## 6. Conformance

Three independent levels apply, since a real deployment typically plays more
than one at once (a delegating agent is a producer when issuing a DELEGATE
and a consumer when reading the resulting HANDBACK).

### 6.1 Producer

A conformant **producer** MUST emit every core field in §4.1 (DELEGATE) or
§4.2 (HANDBACK), matching each field's stated type and constraint. A producer
SHOULD include `ancestry` on any DELEGATE issued at delegation depth > 0
(§5.3), and SHOULD populate `metrics.quality` honestly rather than defaulting
to a fixed value.

### 6.2 Consumer

A conformant **consumer** MUST accept a message satisfying all core-field
constraints, and MUST NOT reject a message solely for carrying an
unrecognized extension field (forward compatibility — the reference
`ExtensionValidator` downgrades these to warnings). A consumer MAY warn on
unrecognized fields; it MUST NOT silently drop core-field data it does
recognize.

### 6.3 Enforcer

A conformant **enforcer** validates messages against the schema and reports
pass/fail. The reference implementation ships three enforcers, each covering
a different field subset at a different lifecycle point — deliberately
overlapping rather than one complete gate:

| Reference enforcer | Core-field coverage | Runs |
|---|---|---|
| `protocol-validator` skill (`protocol_validator.py`) | `task_id`, `skill`, `agent`, `scope`, `success_criteria`, `plan`, `context` on DELEGATE; `task_id`, `status`, `output`, `metrics` on HANDBACK | On demand, in-process |
| Commit-time hook (regex-based) | `task_id`, `agent`, `handoff_type` on DELEGATE; `status`, `metrics` sub-fields, `handoff_type` on HANDBACK; plus a secret-pattern scan | `git commit`, on staged files |
| Spawn-time guard (dependency-free, fails open) | `handoff_type`, `task_id` (kebab-case, 3–50 chars), `agent`, `scope` (>=15 words), `plan`, `success_criteria` on DELEGATE only; plus `depth` <= 3 and `ancestry` cycle detection when those optional fields are declared | Every in-session agent-spawn call |

**An honest gap, not an oversight:** `spec_version` is a required core field
(§4.1, §4.2) but is not currently checked for presence or format by any of
the three reference enforcers above — confirmed by inspecting each
enforcer's implementation directly. `handoff_type` fares better: it functions
as each enforcer's *discriminator* (the field used to recognize a message as
a DELEGATE or HANDBACK at all) even where not separately asserted as
"present and correct". A new enforcer aiming for full conformance should not
assume today's reference enforcers already achieve it — they are best-effort
and independently improvable.

A minimal enforcer, to claim conformance with this document, MUST at least
check: `handoff_type` matches the expected discriminator, `task_id` matches
the required pattern, and (for HANDBACK) `status` is one of the five valid
values with `metrics`' four sub-fields present and correctly typed. Fuller
conformance additionally validates every remaining core field in §4.1/§4.2.

---

## 7. Relationship to Other Work

**MCP (Model Context Protocol).** MCP standardizes the agent↔tool layer — how
an agent discovers and invokes external tools and data sources.
DELEGATE/HANDBACK operates one layer up: agent↔agent task assignment. The two
are complementary — a receiving agent executing a DELEGATE is free to use
MCP-exposed tools internally, and nothing about this protocol's message
shapes conflicts with MCP's.

**A2A (Agent-to-Agent Protocol).** A2A standardizes service-to-service agent
communication (JSON-RPC, agent cards, task semantics) between independent
network services, potentially owned by different organizations.
DELEGATE/HANDBACK is orthogonal: designed for in-process delegation within a
single harness session (direct spawn, §5.1), where both agents share a
runtime and need no network-addressable discovery. Bridging the two — e.g. a
DELEGATE routed to a remote A2A-addressable agent — is a reasonable extension
this document does not currently specify.

**OpenAI Agents SDK handoffs / Microsoft Agent Framework handoff
orchestration.** Both are proprietary equivalents to the same problem inside
their respective frameworks' runtimes: the Agents SDK represents a handoff as
a tool-call transfer carrying conversation history; MAF wraps it in a
dedicated orchestration/workflow layer. Neither is intended for adoption
outside its host SDK. DELEGATE/HANDBACK's distinguishing choice is treating
the message format as separable from any particular runtime, at the cost of
not (yet) having those frameworks' surrounding tooling.

**AGENTS.md and Agent Skills (SKILL.md).** Both are adjacent, independently
published open standards this implementation conforms to rather than
competes with: AGENTS.md (de facto standard across 20-30+ coding tools)
describes how a repository communicates project-specific instructions to an
agent; Agent Skills (agentskills.io, published Dec 2025) describes how a
reusable capability is packaged and discovered. Neither addresses how one
agent hands work to another mid-session — the gap this document addresses.
This implementation's `skill` field (§4.1) is a direct integration point with
Agent Skills: it names the skill a receiving agent should load to perform the
delegated task.

---

## 8. Security Considerations

**Prompt injection via DELEGATE fields.** `scope`, `context`, and `plan` are
free-text fields interpreted by an LLM-driven receiving agent, not parsed as
inert data. A DELEGATE from an untrusted or compromised source could embed
text attempting to override the receiver's configured behavior, permissions,
or safety policy (e.g. text phrased as system-level authorization, or claims
that following it has already been approved). Implementers MUST treat
DELEGATE field content as task instructions only, never as a grant of
elevated permission — no field in this protocol is a permissions channel,
and no enforcer in §6 sanitizes field content for this purpose. This is a
property receiving agents themselves must maintain; the format cannot
enforce it.

**Guard fail-open rationale.** The reference spawn-time enforcer (§6.3) fails
open: on a parse error or unexpected exception, it allows the spawn to
proceed rather than blocking it. This favors availability (a bug in the
enforcer must never wedge every agent-spawn call in a session) over strict
enforcement (an attacker who can reliably crash or confuse the enforcer's
parser bypasses its checks entirely, rather than being denied). Deployments
with a stronger threat model than "an internal delegation format" should not
rely on this specific enforcer as a security boundary — it is a
protocol-compliance gate, not an adversarial one.

**`scope`'s word-count floor is a quality heuristic, not a defense.** The
>=15-word minimum on `scope` exists because, empirically, under-specified
scopes correlated with ambiguous delegation and rework. It is trivially
satisfiable by fifteen words of adversarial content, and MUST NOT be treated
as input sanitization, injection defense, or a content-safety control. Its
only function is forcing a delegator to articulate a bounded task rather than
a one-line vague instruction.

---

## 9. Version and Changelog Policy

This document's version tracks `protocol-core-v1.0.yaml`'s `version` field
one-to-one — a change to the schema's required or extension fields requires a
corresponding revision here, and this document MUST NOT describe a field set
the schema does not also describe. The schema's own header states its
precedence chain when reconciling drift between it, its runtime validator,
and narrative documentation:

1. The runtime enforcer implementation is authoritative for what is actually
   *enforced*.
2. `protocol-core-v1.0.yaml` is authoritative for what is *described* as the
   schema.
3. Narrative documentation (this document included) is descriptive only.

A byte-identical copy of the schema ships alongside the reference
`protocol-validator` skill so resolution works when that skill is installed
outside this repository; an automated test guards the two copies against
drift. This document does not ship a machine-readable copy of itself — it is
narrative, derived from the schema (§4.3), and re-derived whenever the schema
changes.

Future schema revisions that add required core fields, remove fields, or
change validation constraints MUST bump `version` (schema) and this
document's `spec_version` (front matter) together, and SHOULD record the
change in the schema file's own history before this document is updated to
match.

---

## See Also

- [`protocol-core-v1.0.yaml`](protocol-core-v1.0.yaml) — the normative schema
  this document narrates
- [`../PROTOCOL.md`](../PROTOCOL.md) — this implementation's internal
  validation/enforcement reference (audience: contributors to this repository)
- [`../CORE-PROTOCOL-QUICKSTART.md`](../CORE-PROTOCOL-QUICKSTART.md) — a
  30-minute quickstart covering the core-field subset
- [`../../src/AGENTS.md`](../../src/AGENTS.md) — this implementation's roster,
  routing rules, and role definitions (deployment-specific, not part of this
  protocol's normative core)
- [`../LANDSCAPE.md`](../LANDSCAPE.md) — the multi-agent orchestration
  ecosystem survey this document's §2 and §7 summarize
