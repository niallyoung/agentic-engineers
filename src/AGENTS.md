# Agent Roster & Handover Packet Protocol

> **Architecture:** Direct sub-agent spawn DELEGATE/HANDBACK — the spawning agent (Orchestrator, or another role with spawn authority) constructs a DELEGATE block and passes it directly as the prompt of a sub-agent spawn (the harness's Agent/Task tool); the HANDBACK returns synchronously as that tool call's result, in-context. The durable audit record of every DELEGATE and HANDBACK is the harness session transcript itself — there is no separate filesystem queue to write to. See [Direct Sub-Agent Spawn Execution Model](#direct-sub-agent-spawn-execution-model).
> **Autonomy mode:** Reduced — agents pause when there is no pending or in-flight delegated work, rather than inventing new work.
> **Model selection:** Informed by the Model Engineer feedback loop; see the Model Engineer role below.

---

## Philosophy

- **Direct spawn, not ad-hoc** — every task is delegated by constructing a DELEGATE block and passing it directly as the prompt of a sub-agent spawn (the harness's Agent/Task tool); there is no free-form delegation outside this mechanism, and only agents whose frontmatter grants `spawn_subagent` may do it (see [Tools-Frontmatter Permission Model](#tools-frontmatter-permission-model))
- **Transcript-as-audit** — the harness session transcript already contains every DELEGATE (as a spawn prompt) and every HANDBACK (as that spawn's result); this is the durable audit record. There is no separate queue write step
- **Reduced autonomy** — agents pause when there is no pending or in-flight delegated work; they do NOT invent work
- **Start cheap, escalate deliberately** — each role's default model is the cheapest tier capable of that role's job (see the Agent Roster table); a low-quality HANDBACK triggers rework or reroutes to a higher-tier role, not a live mid-task model upgrade
- **Root-cause fixes** — address the actual problem; never disable tests, add workarounds, or avoid failures
- **Cold-context agents** — every DELEGATE is self-contained; the receiving agent cannot rely on session state
- **Parallel by default** — the Orchestrator fans out multiple DELEGATEs simultaneously when tasks are independent
- **Token-conscious** — cite line numbers, suppress verbose output, trust tool confirmations; measure with Model Engineer

---

## Agent Roster

**MODEL NAMING (LOCKED):** Models use canonical format with a DOT version separator,
`claude-{variant}-{major}.{minor}` (e.g. `claude-haiku-4.5`, `claude-opus-4.8`). Current-generation
models carry a **single-part version** and therefore have no separator at all:
`claude-opus-5`, `claude-sonnet-5`, `claude-fable-5`. The invariant is "never a hyphen as the
version separator" (`claude-opus-4-7` is a per-harness render, never source).
See [SPEC.md > Model Naming Architecture](../docs/SPEC.md).

**SINGLE SOURCE OF TRUTH:** Model assignments are defined in `.githooks/LOCKED_MODELS.sh`
(`LOCKED_MODELS` + `AGENT_MODEL_ASSIGNMENTS`). All hooks, validators, and this table must
stay synchronized with it — see [SPEC.md > Model Governance](../docs/SPEC.md) for the
switch process.

| Role | Model | Effort | Multi-Model? | Use When |
|---|---|---|---|---|
| **Orchestrator** | claude-sonnet-5 | low | — | All entry points; routing decisions; task management; metrics collection; model recommendations |
| **Engineer** | claude-haiku-4.5 | high | — | Well-scoped task with pre-written plan; low-medium complexity coding/implementation |
| **Quality Engineer** | claude-sonnet-5 | medium | — | Post-implementation quality gate; code review; model suitability assessment |
| **Senior Engineer** | claude-sonnet-5 | high | — | Complex coding tasks; implementation without fully pre-planned spec; diagnosis of root causes |
| **Lead Engineer** | claude-sonnet-5 | max | — | Code review; quality decisions; medium-complexity planning; architectural guidance |
| **Principal Engineer** | claude-opus-5 | high | opus-5 (default) \| 4.8 (fallback) | Cross-service architecture; complex multi-step planning; design decisions affecting >2 repos |
| **Security Engineer** | claude-fable-5 | max | fable-5 (default) \| opus-4.8 (fallback) | Security analysis; threat modeling; vulnerability audits; final escalation path |
| **Model Engineer** | claude-sonnet-5 | high | — | Analyzes quality/cost feedback from QE; recommends optimal model/effort combinations for future similar tasks |

> **This table is load-bearing, not documentation.** `renderer/lib/render-lib.sh:parse_agents_md()`
> reads the Model and Effort columns to render the Claude Code and OpenCode harnesses. Editing an
> agent's frontmatter without editing this row ships the *old* model to those two harnesses.

**Multi-Model column notes:** Principal Engineer uses `claude-opus-5` for all planning and
cross-repo design; `claude-opus-4.8` is an emergency fallback only (opus-5 unavailable),
documented in HANDBACK. Security Engineer uses `claude-fable-5` unconditionally;
`claude-opus-4.8` is an emergency fallback only. The defensive-only scope constraint
applies on **every** model, not just fable-5 — restricted-topic work is out of scope
framework-wide and is rejected by the Orchestrator's DelegateValidator C5 gate rather
than re-routed. See [SPEC.md > Model Selection Architecture](../docs/SPEC.md).

**Rule:** Start cheap, escalate only when needed. The Orchestrator routes all work; it never implements.

---

## Orchestrator Entry Point

**All work flows through the Orchestrator** — your default handler, which never performs
implementation work itself: it routes, coordinates, and applies Model Engineer
recommendations. Why Orchestrator-first: auditability (all work tracked as DELEGATE/
HANDBACK pairs in the harness session transcript), cost discipline (each role has a fixed, cost-appropriate model; a
low-quality HANDBACK reroutes to a higher tier rather than upgrading mid-task), protocol
enforcement, and parallel execution of independent work. Direct `@agent-name` invocation
is an advanced escape hatch that skips protocol enforcement and audit trails — the
canonical flow always goes through Orchestrator. See
[Delegation Model & Routing Rules](#delegation-model--routing-rules) for the full chain.

---

## Canonical DELEGATE/HANDBACK Schema

Quick reference — see [Handover Packet Protocol](#handover-packet-protocol) below for the
full annotated format including ESCALATION and extension fields.

```yaml
---
handoff_type: DELEGATE
agent: engineer                    # target specialist role (hyphenated)
task_id: unique-identifier
scope: "Clear, bounded description of what will be done (≥15 words)"
context:
  - "Relevant file: src/module.py (lines 45-67)"
plan:
  - "Step 1: Read and understand requirement"
  - "Step 2: Implement feature"
success_criteria:
  - "All tests pass"
tokens_estimate: 1500
---
```

```yaml
---
handoff_type: HANDBACK
task_id: unique-identifier
status: success                    # success | failure | partial | blocked | escalate
output: |
  Modified src/module.py to implement feature. All unit tests pass (47 tests).
metrics:
  quality: 0.95                    # 0.0-1.0 float
  tokens: 1200                     # total input + output
  cost: 0.019                      # USD
  duration_seconds: 42             # wall-clock time
confidence: 0.95                   # 0.0-1.0 float
---
```

---

## Delegation Model & Routing Rules

```
User / External Trigger
  └─► Orchestrator  (sonnet-5 — routing)
        ├─► Engineer               ← well-scoped tasks with full plans
        ├─► Senior Engineer        ← unscoped or multi-file work
        │     ├─► Lead Engineer    ← architecture decisions, code review
        │     ├─► Principal Eng    ← hard debugging, cross-service analysis
        │     └─► Security Eng     ← auth, crypto, threat modelling
        ├─► Quality Engineer       ← post-implementation validation (always)
        └─► Model Engineer         ← after QE HANDBACK, analyses metrics
```

1. **Security-scoped** → Security Engineer (always, no exceptions)
2. **Cross-service / architecture** → Principal Engineer
3. **Code review / validation** → Lead Engineer or Quality Engineer
4. **Unscoped complex work** → Senior Engineer (plan phase) → Engineer (execute phase)
5. **Well-scoped with plan** → Engineer
6. **Default** → Engineer with context

---

## Role Definitions

Detailed capabilities, boundaries, and escalation triggers for each role.

### 1. Orchestrator

**Model:** `claude-sonnet-5`, effort `low`. Entry point for all user requests; routes via
the decision tree above; never implements. Parses requests into DELEGATE blocks, spawns
the target agent directly (Agent/Task tool), fans out up to 5 concurrent spawns for
independent work, and receives each HANDBACK in-context — the session transcript is the
audit record, so there is no separate bookkeeping step. Re-delegates ESCALATION packets at
the higher tier. **MUST NOT:** write code, make architecture/security decisions, hold
cross-session state, or spawn beyond the recursion/fan-out limits (see [Recursion
Limits](#recursion-limits)). **Escalates to:** nobody — top of the chain; pause and surface
to the user if human input is required. **Pauses when:** no pending DELEGATEs and no
outstanding spawns.

### 2. Engineer

**Model:** `claude-haiku-4.5`, effort `high`. Executes well-scoped tasks at known
file:line addresses — the cheapest implementation role. Single-file or straightforward
multi-file edits (≤3 files, same package), unit tests to a clear spec, documentation
updates, dependency bumps, simple bug fixes with a clear root cause. **MUST NOT:**
explore multiple files to build context, make architectural/API decisions, or modify
public contracts without instruction. **Escalates to Senior Engineer** when touching >3
files/packages, needing multi-file context, or 2 failed test-fix attempts; **to Lead
Engineer** for architecture/API decisions; **to Security Engineer** if auth/crypto/secrets
surface.

### 3. Senior Engineer

**Model:** `claude-sonnet-5`, effort `high`. Plans unscoped work; handles multi-file
implementations requiring architectural awareness — reads related files first,
moderate-complexity refactors, CI/CD changes, breaking dependency updates, reviews
Engineer output when QE flags it. **MUST NOT:** make cross-repo API contract decisions,
resolve inter-service architectural disputes, or conduct formal security audits.
**Escalates to Lead Engineer** for architecture/API contract or cross-repo coordination;
**to Principal Engineer** for root causes spanning >2 services or >2 failed attempts;
**to Security Engineer** for auth/crypto/compliance implications.

### 4. Lead Engineer

**Model:** `claude-sonnet-5`, effort `high`. Makes architecture decisions authoritatively
(API contracts, domain boundaries, data models), conducts 8-point code review
(correctness, safety, patterns, performance, security surface, maintainability, test
coverage, documentation), resolves competing-design conflicts, coordinates cross-repo
consistency, and produces implementation DELEGATEs. **MUST NOT:** conduct formal threat
modelling or implement code changes directly. **Escalates to Principal Engineer** for
fundamentally hard architectural problems; **to Security Engineer** for security-critical
design decisions (auth flows, crypto selection).

### 5. Quality Engineer

**Model:** `claude-sonnet-5`, effort `medium`. Post-implementation validation: verifies
acceptance criteria against delivered changes, runs `CONFIG=dev make lint && make test &&
make build`, assesses whether the model/effort tier was appropriate, populates
`metrics.quality` in the HANDBACK, and flags regressions/missing tests. **MUST NOT:**
implement fixes for issues it finds (produce a DELEGATE instead) or make architecture
decisions. **Escalates to Lead Engineer** after 2 persistent build/lint-failure re-runs;
**to Security Engineer** for security-related failure patterns; **to Principal Engineer**
for a systemic pattern across multiple tasks.

### 6. Model Engineer

**Model:** `claude-sonnet-5`, effort `high`. Analyses HANDBACK `metrics` blocks (tokens,
cost, quality, duration_seconds) across task history, compares actual vs. estimated token
usage, recommends model/effort adjustments, identifies mismatches, and writes
recommendations. **MUST NOT:** implement code changes, or approve/reject tasks —
recommendations only. **Escalates to Principal Engineer** for a system-level quality
regression spanning multiple roles; **to Lead Engineer** for a contested recommendation.

### 7. Principal Engineer

**Model:** `claude-opus-5` (fallback `claude-opus-4.8`), effort `high`. Cross-service
architecture, hard debugging, critical design decisions — escalation only. Root-cause
analysis across deep stack traces or multiple services, complex architectural analysis
(data flow, race conditions, distributed semantics), takes over after Senior has ≥2 failed
attempts, produces structured findings with exact file:line references and DELEGATEs for
cheaper tiers to implement. **MUST NOT:** implement fixes directly or conduct formal
security audits. **Escalates to Security Engineer** for security-critical design
decisions; otherwise top of the non-security chain — surface to the user if blocked.

### 8. Security Engineer

**Model:** `claude-fable-5` (unconditional default; fallback `claude-opus-4.8`), effort
`max`. Threat modelling (STRIDE, attack surface), vulnerability assessment (OWASP Top 10,
injection, broken auth, secrets exposure), compliance review (OAuth 2.0, zero-trust, GDPR
surface), CLI permission policy review — always assigned for security-scoped work.
Produces a findings table (severity, file:line, description, recommendation) and
implementation DELEGATEs for cheaper tiers. **MUST NOT:** implement fixes directly, or be
skipped for any auth/crypto/secrets/compliance task. **Escalates to:** nobody — top of the
security chain; surface to the user for findings requiring executive/compliance sign-off.

---

## Handover Packet Protocol

All work is delegated via a **DELEGATE block** — constructed by the spawning agent and passed directly as the prompt of a sub-agent spawn call (the harness's Agent/Task tool). On completion, the receiving agent returns a **HANDBACK block** directly as that spawn call's result, in-context; the spawning agent never polls or reads a file to get it.

The harness session transcript already contains every DELEGATE (as a spawn prompt) and every HANDBACK (as that spawn's result) — it is the durable audit record, with no separate write step; see [Direct Sub-Agent Spawn Execution Model](#direct-sub-agent-spawn-execution-model).

### DELEGATE Block Format

> **Canonical schema:** `docs/specs/protocol-core-v1.0.yaml` (single source of truth)
> **Deprecated:** `type: DELEGATE` — use `handoff_type: DELEGATE` instead.

```yaml
# Passed directly as the sub-agent spawn prompt (dispatch); the spawn call
# itself, recorded in the harness session transcript, is the audit copy.
---
task_id: my-task-identifier    # kebab-case, 3-50 chars (^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$)
handoff_type: DELEGATE         # canonical discriminator (NOT type:)
agent: senior-engineer         # hyphenated role name — see VALID_AGENTS below
skill: senior-engineer         # skill name resolving to src/skills/<skill>/
model: claude-sonnet-5         # must be explicit — no implicit defaults
effort: high                   # low | medium | high

scope: |
  One sentence or paragraph describing what will be done, to what, and
  explicit out-of-scope boundaries. Must be >= 15 words.

context:
  - "Relevant file: path/to/relevant/file.py (lines 45-67)"
  - "Repo: github.com/owner/repo-name, branch: feature/branch-name"
  - "Root cause: describe the problem and why this approach solves it"

plan:
  - "Step 1: Read and understand the relevant files"
  - "Step 2: Implement the required changes"
  - "Step 3: Write or update tests (TDD: Red → Green)"
  - "Step 4: Verify with repro command"

success_criteria:
  - "AC1: describe what done looks like"
  - "AC2: describe measurable outcome"

# --- Optional extension fields (forward-compatible) ---
tokens_estimate: 8000          # estimated max tokens for this task
budget: 0.09                   # $ ceiling based on model + estimate
priority: 5                    # 1 (lowest) - 10 (highest)
dependencies: []               # task_ids that must complete first
ancestry: [orchestrator]       # chain of agent roles from root to this DELEGATE's
                                # spawning parent, inclusive. REQUIRED whenever the
                                # spawning agent was itself spawned (depth > 0) — used
                                # to enforce max delegation depth and detect cycles.
                                # See Recursion Limits.
```

> **Required core fields:** `task_id`, `handoff_type`, `agent`, `skill`, `scope` (>=15 words),
> `plan` (>=2 steps, each >=3 words), `success_criteria` (>=1 item), `context` (>=20 words or non-empty array).
> `ancestry` is an additive, forward-compatible extension field, not a redesign of the required core.
>
> **Valid agents:** `orchestrator`, `engineer`, `senior-engineer`, `lead-engineer`,
> `principal-engineer`, `security-engineer`, `quality-engineer`, `model-engineer`
> (hyphens only).

### HANDBACK Block Format

Canonical schema: [`docs/specs/protocol-core-v1.0.yaml`](../docs/specs/protocol-core-v1.0.yaml).
Required core fields: `task_id`, `status`, `output`, `metrics` (with `quality`, `tokens`, `cost`, `duration_seconds`).

> **Deprecated:** `type: HANDBACK` — use `handoff_type: HANDBACK` instead.

```yaml
# Returned directly as the spawn call's result (dispatch), in-context; that
# result, recorded in the harness session transcript, is the audit copy.
---
task_id: my-task-identifier    # must match the originating DELEGATE's task_id
handoff_type: HANDBACK         # canonical discriminator (NOT type:)
status: success                # success | failure | partial | blocked | escalate

output: |
  One-paragraph summary of what was done, files changed, and key decisions.

metrics:                       # ALL four sub-fields are REQUIRED
  quality: 0.88                # float 0.0–1.0, self-assessed delivery quality
  tokens: 5840                 # non-negative int, total tokens (input + output)
  cost: 0.09                   # non-negative float, USD
  duration_seconds: 42         # non-negative float, wall-clock execution seconds

# --- Optional extension fields (forward-compatible) ---
model_used: claude-sonnet-5
effort_actual: medium
confidence: 0.9                # 0.0–1.0
flags: []                      # advisory flags / anomalies
error: null                    # error detail when status is failure or blocked
escalation: null               # or ESCALATION block (see below) if status: escalate
```

> **Status values:** `success` (all criteria met), `failure` (criteria not met),
> `partial` (some criteria met), `blocked` (external dependency needed),
> `escalate` (requires higher-tier agent or human decision). `complete`/`failed` are NOT valid.

### ESCALATION Packet Format

When an agent hits an escalation trigger, it MUST stop implementation work and emit:

```yaml
# Embedded in HANDBACK under the `escalation:` key
---
task_id: my-task-identifier
type: ESCALATION              # ESCALATION packets retain type: (not a DELEGATE/HANDBACK)
from_role: senior-engineer
to_role: principal-engineer
reason: |
  Root cause spans multiple services — requires cross-service analysis
  beyond Senior's authority. Specifically: [details of what was tried and why it failed]
findings_so_far: |
  Summary of what was discovered before escalation, so the receiving
  agent starts with full context and does not re-investigate the same ground.
recommended_focus:
  - Specific area to investigate
```

The agent that receives this HANDBACK (the Orchestrator, or whichever role spawned the
escalating agent) reads the ESCALATION block in-context, constructs a new DELEGATE block
targeting `to_role` with the escalation content inlined in `context` and its own role
appended to `ancestry`, and spawns `to_role` directly — subject to the same
depth/fan-out/cycle checks as any other spawn.

---

## ACK Protocol

Every agent MUST emit an ACK as its **first output** before performing any work.

```
✅ [Role Name] ACK — [TASK-ID]                              # Standard

⚠️ [Role Name] BLOCKED — [TASK-ID]                           # Missing context
Missing: [list of what's missing or unclear]
Request: [what information is needed to proceed]

❌ MODEL_MISMATCH — expected claude-sonnet-5, got claude-haiku-4.5   # Wrong model
Stopping. Orchestrator must re-delegate with the correct model.
```

Every agent MUST include in its final output a completion footer:

```
MODEL_USED: claude-sonnet-5   # actual model used (not the requested model)
```

---

## Direct Sub-Agent Spawn Execution Model

> **Why this changed:** the framework previously specified an Orchestrator that polled a
> filesystem queue, claimed tasks, and spawned agents as subprocesses correlated by
> HANDBACK files. An audit of 16 live session partitions found **zero tasks** ever
> traversed the queue that way — every real delegation happened via a direct sub-agent
> spawn instead. This section documents the model that was actually running. The
> filesystem queue itself has since been removed entirely: the harness session transcript
> is the durable audit record, satisfying `docs/SPEC.md`'s "NO Python scripts for queue
> management".

### Full Flow

```
1.  User request arrives, or the current agent generates a DELEGATE from prior
    HANDBACK output (e.g. re-delegating remaining work, or an ESCALATION)
2.  The spawning agent applies routing rules and selects the target role
3.  The spawning agent SPAWNS the target agent directly (Agent/Task tool),
    passing the DELEGATE block as the sub-agent's prompt. For independent
    tasks, it fans out multiple spawns in parallel — up to 5 concurrent per
    parent (see Recursion Limits)
4.  Each spawned agent ACKs, loads its skill, performs work (and MAY itself
    spawn further sub-agents if its frontmatter grants `spawn_subagent`,
    subject to the same depth/fan-out/cycle checks), and returns a HANDBACK
    directly as the spawn call's result — nothing to poll for this to complete
5.  Convention, not automatic: the spawning agent MAY spawn Quality Engineer
    to validate the HANDBACK against success_criteria and populate metrics.quality
6.  Convention, not automatic: likewise it MAY spawn Model Engineer afterward
    to analyse metrics and recommend model/effort adjustments
7.  The spawning agent reads the HANDBACK in-context and applies the routing
    decision (success/partial/blocked/escalate — see Applying the HANDBACK below)
8.  If no pending DELEGATEs and no outstanding spawns remain → the
    Orchestrator PAUSES
```

The harness session transcript already contains every DELEGATE (as a spawn prompt) and
every HANDBACK (as that spawn's result), so no step above depends on writing or reading a
separate audit file.

**Applying the HANDBACK:** `success` → mark done in `TODO.md`; `partial` → re-delegate the
remainder (direct spawn); `blocked` → surface to the user with the blocker; `escalate` →
re-delegate the ESCALATION block at the higher tier (direct spawn).

### Recursion Limits

These limits are the framework's convention for bounding recursion depth and fan-out in
the delegation tree. **No runtime code counts depth, counts fan-out, or detects cycles
at spawn time** — see [Tools-Frontmatter Permission Model](#tools-frontmatter-permission-model)
below. Every agent is expected to self-enforce:

- **Max delegation depth: 3.** Depth is measured in spawn hops from the root DELEGATE
  (depth 0 = the Orchestrator's own top-level DELEGATE). An agent at depth 3 MUST NOT
  itself spawn — it executes or refuses. This is why Engineer and Quality Engineer never
  need `spawn_subagent`: every routing path reaches them at the final hop.
- **Max fan-out: 5** concurrent sub-agents per parent. Additional independent work waits
  for one of the first 5 to complete, or is grouped into a consolidating DELEGATE.
- **Ancestry tracking (cycle detection).** Every DELEGATE issued by an agent spawned at
  depth > 0 MUST set the `ancestry` extension field (root-to-parent role chain,
  inclusive). Before spawning, check whether the target role already appears in
  `ancestry` — if so, refuse (e.g. Senior Engineer escalates to Lead Engineer, and Lead's
  implementation DELEGATE incorrectly targets `senior-engineer` again for the same task).

**When a limit is hit:** stop; do not silently proceed or drop the work. Return a
HANDBACK with `status: blocked` (procedural — likely resolvable by restructuring the
fan-out) or `status: escalate` (a genuine cycle, or a task needing more than 3 hops),
stating which limit was hit and why. The receiving agent decides how to proceed.

### Cost Guardrail

A documented convention on the DELEGATE extension fields `tokens_estimate` and `budget`
(`docs/specs/protocol-core-v1.0.yaml` — unchanged), not a new mechanism: the Orchestrator
SHOULD set both on every DELEGATE it issues, and MUST NOT spawn a sub-agent whose
estimate would exceed an operator-configured session/task budget — instead it returns a
synthetic `status: blocked` HANDBACK naming which budget limit was hit, exactly like the
recursion-limit refusal above, without ever calling the Agent/Task tool. HANDBACK
`metrics.tokens`/`metrics.cost` (already required core fields) close the loop as input
to `scripts/handback_rollup.py`'s per-role cost/quality report. **Enforcement:
orchestrator-self + QE review** — no schema change, no PreToolUse hook change; see
`docs/PROTOCOL.md` § Cost Guardrail for the full convention and a worked HANDBACK
example.

### Audit Events

`docs/SPEC.md` clause 7 requires a separate, queryable event log alongside the
transcript: an append-only JSONL at
`~/.agentic-engineers/{harness}/{session-id}/audit/events-YYYY-MM-DD.jsonl`. This is
additive to — not a replacement for — the transcript-as-audit-record model above: the
transcript remains what makes a DELEGATE/HANDBACK *count* (clause 4); the JSONL is the
metrics/event record `scripts/handback_rollup.py` and other tooling can query without
re-parsing a session transcript. Agents append to it directly via
`scripts/audit_append.py` (`docs/SPEC.md` § COMPLETE SCRIPT INVENTORY) — a pure,
stdlib-only formatting/validation helper (clause 3: advisory Python), never a control-flow
owner.

**Who appends what, when** (every role in the table below, for its own spawns):
- **`delegate_issued`** + **`subagent_spawned`** — appended when constructing and then
  issuing a DELEGATE via a direct sub-agent spawn (both fire together, at spawn time).
- **`handback_received`** + **`gate_result`** — appended once the HANDBACK comes back
  as the spawn call's result (`gate_result` records how the spawning agent applied the
  HANDBACK's `status` — see [Applying the HANDBACK](#full-flow)).
- **`refusal`** / **`limit_exceeded`** — appended instead of `subagent_spawned` when a
  spawn is refused (depth/fan-out/cycle/budget — see Recursion Limits and Cost
  Guardrail above); the Agent/Task tool is never called.
- **`escalation`** — appended when re-delegating an ESCALATION packet at a higher tier.

Invocation is a single CLI call per event, e.g.:

```bash
python3 scripts/audit_append.py --event delegate_issued \
  --task-id my-task --parent-task-id orchestrator-root --depth 1 \
  --agent-role senior-engineer --agent-model claude-sonnet-5 --status success
```

**Failures are warnings, never blockers.** `audit_append.py` exits 2 only for a
malformed event (unknown `event` name or a missing required field per clause 7); any
other failure (e.g. an unwritable audit directory) exits 1. Either way, the spawning
agent notes the failure and proceeds with its actual work — a failed audit append MUST
NOT stop a DELEGATE, a spawn, or a HANDBACK from being applied.

### Tools-Frontmatter Permission Model

The `tools:` key in each agent's source frontmatter (`src/agents/<name>-agent.md`) states
which roles are *meant* to spawn sub-agents — a convention, not an enforced permission.
Neither harness renderer enforces it: Claude Code's `render-claude.sh` drops `tools:`
entirely (every rendered sub-agent gets full default tool access); OpenCode's
`render-opencode.sh` uses uniform allow-all permissions by design (social constraint
model, not technical). The PreToolUse hook (`renderer/scripts/claude-delegate-guard.py`)
only checks that a spawn call carries a well-formed DELEGATE block — not the calling
agent's role, ancestry, depth, or fan-out. Compliance below is the spawning agent's own
judgment call.

| Role | Spawns sub-agents? | Why |
|---|---|---|
| Orchestrator | Yes | Root of every delegation chain; routes to any specialist |
| Senior Engineer | Yes | Delegates to Engineer, or escalates to Lead/Principal/Security |
| Lead Engineer | Yes | Produces implementation DELEGATEs after an architecture decision |
| Principal Engineer | Yes | Produces implementation DELEGATEs after a cross-service finding |
| Security Engineer | Yes | Produces implementation DELEGATEs for each audit finding |
| Model Engineer | No | Recommendations only — returns findings in its own HANDBACK |
| Engineer | No | Leaf by design — escalates via HANDBACK `status: escalate` |
| Quality Engineer | No | Leaf by design — issues go in QE's own HANDBACK |

### Pause Condition

The Orchestrator **pauses** when it has no pending DELEGATEs to issue and no outstanding
sub-agent spawns awaiting a HANDBACK. It does NOT invent new work — reduced autonomy
prevents runaway scope. To resume: give the Orchestrator a new request, or add a task to
`TODO.md`.

---

## Example Workflow — Escalation Chain (Engineer → Senior → Lead)

**Step 1: Engineer hits an escalation trigger** and returns a HANDBACK with
`status: escalate`, embedding an ESCALATION block (`from_role: engineer`,
`to_role: senior-engineer`, `reason`, `findings_so_far`, `recommended_focus`) — e.g. a
payment refactor touching 5 files across 2 packages exceeds Engineer's 3-file boundary
and needs an API-contract decision.

**Step 2: Orchestrator reads the HANDBACK, spawns Senior Engineer directly** with a new
DELEGATE (`task_id: task-202-senior-payment-arch`, `agent: senior-engineer`,
`ancestry: [orchestrator]`) whose `scope`/`context` inline the escalation's findings so
Senior does not re-investigate. Both the original HANDBACK and this new DELEGATE are
recorded in the session transcript for audit.

**Step 3: Senior Engineer determines the decision exceeds its own authority** (a
cross-package API contract) and escalates again — HANDBACK with `status: escalate`,
`ancestry: [orchestrator, senior-engineer]`, targeting `lead-engineer`.

**Step 4: Lead Engineer makes the architecture decision** and produces two implementation
DELEGATEs — one to Senior Engineer for the new type, one to Engineer for the call-site
update — each spawned directly, with the transcript as the audit record.

This is the general escalation pattern for every role pair in the routing chain: the
receiving agent never re-investigates ground the escalating agent already covered, and
`ancestry` grows by exactly one role per hop so cycle detection stays accurate.

---

## Role Summary Table

| Role | When to Use | Escalates To |
|------|-------------|--------------|
| Orchestrator | All task entry points | User (for critical decisions) |
| Engineer | Scoped tasks, file edits, tests | Senior / Lead / Security |
| Senior Engineer | Planning, multi-file changes | Lead / Principal / Security |
| Lead Engineer | Code review, arch guidance | Principal / Security |
| Quality Engineer | Post-implementation validation | Lead / Security / Principal |
| Model Engineer | After QE HANDBACK with metrics | Lead / Principal |
| Principal Engineer | Hard bugs, cross-service design | Security / User |
| Security Engineer | All security-scoped work | User |

Each role's full definition (capabilities, boundaries, escalation triggers) is in
[Role Definitions](#role-definitions) above; source frontmatter lives at
`src/agents/<name>-agent.md`.
