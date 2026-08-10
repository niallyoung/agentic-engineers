# Agent Roster & Handover Packet Protocol

> **Architecture:** Direct sub-agent spawn DELEGATE/HANDBACK — the spawning agent (Orchestrator, or another role with spawn authority) constructs a DELEGATE block and passes it directly as the prompt of a sub-agent spawn (the harness's Agent/Task tool); the HANDBACK returns synchronously as that tool call's result, in-context. Every DELEGATE and HANDBACK is *also* durably recorded to the filesystem queue as an audit trail — the queue records what happened, it no longer drives dispatch. See [Direct Sub-Agent Spawn Execution Model](#direct-sub-agent-spawn-execution-model).  
> **Autonomy mode:** Reduced — agents pause when there is no pending or in-flight delegated work, rather than inventing new work.  
> **Model selection:** Informed by the Model Engineer feedback loop; see [`src/skills/roles/model-engineer.md`](skills/roles/model-engineer.md).

---

## Philosophy

- **Direct spawn, not ad-hoc** — every task is delegated by constructing a DELEGATE block and passing it directly as the prompt of a sub-agent spawn (the harness's Agent/Task tool); there is no free-form delegation outside this mechanism, and only agents whose frontmatter grants `spawn_subagent` may do it (see [Tools-Frontmatter Permission Model](#tools-frontmatter-permission-model))
- **Audit-first, not dispatch-first** — every DELEGATE (at spawn) and every HANDBACK (at completion) MUST be durably recorded via `QueueOperations.enqueue()` (the `queue-management` skill) to `~/.agentic-engineers/{harness}/{session-id}/queue/`. This is bookkeeping written *after* the spawn already happened directly — nothing polls these directories to trigger work. Direct file writes to any queue subdirectory (`incoming/`, `processing/`, `done/`, `failed/`) are forbidden and bypass schema validation.
- **Reduced autonomy** — agents pause when the queue is empty; they do NOT invent work
- **Start cheap, escalate deliberately** — each role's default model is the cheapest tier capable of that role's job (see Cost Tiers below); a low-quality HANDBACK triggers rework or reroutes to a higher-tier role via `route_handback` (`orchestrator.py`) — this is a static per-role assignment plus post-hoc rerouting, not a live mid-task model upgrade
- **Root-cause fixes** — address the actual problem; never disable tests, add workarounds, or avoid failures
- **Cold-context agents** — every DELEGATE is self-contained; the receiving agent cannot rely on session state
- **Parallel by default** — the Orchestrator fans out multiple DELEGATEs simultaneously when tasks are independent
- **Delegate fan-out** — Codex `delegate:` / `DELEGATE:` requests may contain semicolon-separated tasks; split them into separate DELEGATEs, parallelize the independent ones, and keep same-file edits coordinated
- **Token-conscious** — cite line numbers, suppress verbose output, trust tool confirmations; measure with Model Engineer

---

## Agent Roster

**MODEL NAMING (LOCKED):** Models use canonical format with a DOT version separator,
`claude-{variant}-{major}.{minor}` (e.g. `claude-haiku-4.5`, `claude-opus-4.8`). Current-generation
models carry a **single-part version** and therefore have no separator at all:
`claude-opus-5`, `claude-sonnet-5`, `claude-fable-5`. The invariant is "never a hyphen as the
version separator" (`claude-opus-4-7` is a per-harness render, never source).
See [SPEC.md > Model Naming Architecture](../docs/SPEC.md).

**SINGLE SOURCE OF TRUTH:** Model assignments are defined in `src/config/models.yaml`.
All documentation, AGENTS.md, and configuration files must stay synchronized with this canonical
source. When updating model assignments, update `models.yaml` first, then audit related docs
(SPEC.md, README, guides, skills files) to ensure consistency.

| Role | Model | Effort | Multi-Model? | Use When |
|---|---|---|---|---|
| **Orchestrator** | claude-haiku-4.5 | low | — | All entry points; routing decisions; task management; metrics collection; model recommendations |
| **Engineer** | claude-haiku-4.5 | high | — | Well-scoped task with pre-written plan; low-medium complexity coding/implementation |
| **Quality Engineer** | claude-sonnet-5 | medium | — | Post-implementation quality gate; code review; model suitability assessment |
| **Senior Engineer** | claude-sonnet-5 | high | — | Complex coding tasks; implementation without fully pre-planned spec; diagnosis of root causes |
| **Lead Engineer** | claude-sonnet-5 | high | — | Code review; quality decisions; medium-complexity planning; architectural guidance |
| **Principal Engineer** | claude-opus-5 | high | opus-5 (default) \| 4.8 (fallback) | Cross-service architecture; complex multi-step planning; design decisions affecting >2 repos |
| **Security Engineer** | claude-fable-5 | max | fable-5 (default) \| opus-4.8 (fallback) | Security analysis; threat modeling; vulnerability audits; final escalation path |
| **Model Engineer** | claude-sonnet-5 | high | — | Analyzes quality/cost feedback from QE; recommends optimal model/effort combinations for future similar tasks |

> **This table is load-bearing, not documentation.** `renderer/lib/render-lib.sh:parse_agents_md()`
> reads the Model and Effort columns to render the Claude Code and OpenCode harnesses. Editing an
> agent's frontmatter without editing this row ships the *old* model to those two harnesses.

**Multi-Model column notes:**
- Principal Engineer: opus-5 (default, all planning and cross-repo design). claude-opus-4.8 only as emergency fallback if opus-5 is unavailable; document in HANDBACK. See [SPEC.md > Model Selection Architecture](../docs/SPEC.md).
- Security Engineer: fable-5 (default). claude-opus-4.8 only as emergency fallback if fable-5 is unavailable; document in HANDBACK. The defensive-only scope constraint applies on **every** model, not just fable-5 — restricted-topic work is out of scope framework-wide and is rejected by the Orchestrator's DelegateValidator C5 gate rather than re-routed. See [SPEC.md > Model Selection Architecture](../docs/SPEC.md).

### Cost Tiers

```
Tier 1 — Cheap (haiku-4.5):   Orchestrator + Engineer        → $0.03–0.05/task
Tier 2 — Medium (sonnet-5):   Model Eng + QE + Lead + Senior → ~$0.12/task
Tier 3 — Premium (opus-5):    Principal                      → ~$0.18/task
Tier 3 — Premium (fable-5):   Security                       → ~$0.36/task
```

Per-task figures rose at the model upgrade without any price change: Sonnet 5
keeps Sonnet 4.6's $3/$15 per MTok but its tokenizer emits ~30% more tokens for
the same text. Re-baseline with `count_tokens` against the new model instead of
scaling old token counts.

**Rule:** Start cheap, escalate only when needed. The Orchestrator routes all work; it never implements.

---

## Orchestrator Entry Point

**All work flows through the Orchestrator.** The Orchestrator is your default handler and never performs implementation work itself—it routes, coordinates, and applies Model Engineer recommendations.

```
User request / External trigger
  └─► Orchestrator (haiku — cheap routing)
        ├─► Issues DELEGATE to the correct specialist
        ├─► Specialist performs work and returns HANDBACK
        └─► Orchestrator interprets result and coordinates next steps
```

**Why Orchestrator-first?**
- **Auditability** — all work is tracked as DELEGATE/HANDBACK blocks in the queue
- **Cost discipline** — each role has a fixed, cost-appropriate model (see Cost Tiers); a low-quality HANDBACK reroutes to a higher tier rather than upgrading the model mid-task
- **Protocol enforcement** — routing rules and model selection are consistent
- **Parallel execution** — independent tasks fan out simultaneously

Direct `@agent-name` invocation is available as an advanced escape hatch but skips protocol enforcement and audit trails. The canonical flow always goes through Orchestrator.

---

## Canonical DELEGATE/HANDBACK Schema

All work follows the DELEGATE/HANDBACK protocol. DELEGATEs are enqueued by the Orchestrator, processed by specialist agents, and HANDBACKs are returned with metrics.

### DELEGATE Format (Request)

```yaml
---
handoff_type: DELEGATE
agent: engineer                    # target specialist role (hyphenated)
task_id: unique-identifier
scope: "Clear, bounded description of what will be done (≥15 words)"
context:
  - "Relevant file: src/module.py (lines 45-67)"
  - "Error message or requirement summary"
plan:
  - "Step 1: Read and understand requirement"
  - "Step 2: Identify affected files"
  - "Step 3: Implement feature"
  - "Step 4: Run tests"
success_criteria:
  - "All tests pass"
  - "Code follows style guide"
  - "No linter warnings"
estimated_tokens: 1500
---
```

### HANDBACK Format (Response)

```yaml
---
handoff_type: HANDBACK
task_id: unique-identifier
status: success                    # success | failure | partial | blocked | escalate

output: |
  Modified src/module.py to implement feature. Added tests/test_feature.py
  with 100% coverage. All unit tests pass (47 tests). Code coverage: 92%.

metrics:
  quality: 0.95                    # 0.0-1.0 float
  tokens: 1200                     # total input + output
  cost: 0.019                      # USD
  duration_seconds: 42             # wall-clock time

confidence: 0.95                   # 0.0-1.0 float
---
```

---

## Multi-Model Selection (Tier 3)

Principal Engineer and Security Engineer support model variant selection based on task complexity.

**Decision criteria:**
- Principal Engineer: Use `claude-opus-5` for all planning and cross-repo design work. `claude-opus-4.8` is an emergency fallback only (opus-5 unavailable); document the substitution in HANDBACK.
- Security Engineer: Use `claude-fable-5` for all security analysis. `claude-opus-4.8` is an emergency fallback only; document the substitution in HANDBACK. Scope limits are model-independent — see the defensive-only constraint in [SPEC.md](../docs/SPEC.md).

For detailed guidance, decision trees, and examples, see [SPEC.md > Model Selection Architecture](../docs/SPEC.md).

---

## Delegation Model

```
User / External Trigger
  └─► Orchestrator  (haiku — cheap routing)
        ├─► Engineer               ← well-scoped tasks with full plans
        ├─► Senior Engineer        ← unscoped or multi-file work
        │     ├─► Lead Engineer    ← architecture decisions, code review
        │     ├─► Principal Eng    ← hard debugging, cross-service analysis
        │     └─► Security Eng     ← auth, crypto, threat modelling
        ├─► Quality Engineer       ← post-implementation validation (always)
        └─► Model Engineer         ← after QE HANDBACK, analyses metrics
```

### Routing Rules

1. **Security-scoped** → Security Engineer (always, no exceptions)
2. **Cross-service / architecture** → Principal Engineer
3. **Code review / validation** → Lead Engineer or Quality Engineer
4. **Unscoped complex work** → Senior Engineer (plan phase) → Engineer (execute phase)
5. **Well-scoped with plan** → Engineer
6. **Default** → Engineer with context

---

## Role Definitions

Detailed capabilities, boundaries, and escalation triggers for each role.

---

### 1. Orchestrator

**Model:** `claude-haiku-4.5`  **Tier:** Cheap  **Skill:** `src/skills/orchestration/task-routing.md`

**Purpose:** Entry point for all user requests. Routes work via the decision tree. Never implements.

**Capabilities:**
- Parse incoming requests and construct DELEGATE blocks
- Route tasks to the correct role using routing rules above, then **spawn the target agent directly** (Agent/Task tool) with the DELEGATE block as its prompt
- Fan out parallel DELEGATEs when tasks are independent — up to **5 concurrent sub-agent spawns** per parent (see [Recursion Limits](#recursion-limits))
- Receive each HANDBACK directly as the spawn call's result, in-context, and update `TODO.md`
- Record every DELEGATE (at spawn) and every HANDBACK (at completion) to the queue via `enqueue()`, for audit — after dispatch, never instead of it
- Re-delegate ESCALATION packets at the higher tier via direct spawn, subject to the same depth/ancestry checks as any other DELEGATE
- Summarise squad status as tables (not prose)

**MANDATORY — Auditing DELEGATEs and HANDBACKs:**
Dispatch itself is a **direct sub-agent spawn** — the Orchestrator passes the DELEGATE block straight into the Agent/Task tool call and gets the HANDBACK back as that call's result. Separately, and in addition, every DELEGATE (at spawn time) and every HANDBACK (at completion) MUST be durably recorded via `QueueOperations.enqueue()` from the `queue-management` skill. This is the audit trail, not the transport — nothing polls the target directory to discover or trigger work.  
Direct file writes to queue directories are forbidden and bypass schema validation.

```python
# Correct — spawn directly (dispatch), then enqueue() the record (audit)
delegate_block = {
    "handoff_type": "DELEGATE",
    "task_id": "my-task-001",
    "agent": "engineer",         # NOT "role": "Engineer"
    "scope": "...",
    "plan": ["step 1 ...", "step 2 ..."],
    "context": "...",
    "success_criteria": ["criterion 1"],
}
handback = spawn_agent(agent="engineer", prompt=delegate_block)   # direct spawn — this IS dispatch

from skills.queue_management.scripts.queue_ops import QueueOperations
ops = QueueOperations(session_id=session_id)
ops.enqueue(delegate_block)   # audit record of the DELEGATE, written after dispatch
ops.enqueue(handback)         # audit record of the HANDBACK, written after completion

# FORBIDDEN — never write directly to queue dirs
# open("~/.agentic-engineers/.../incoming/my-task.json", "w")  # NO
```

**Boundaries — Orchestrator MUST NOT:**
- Write code, edit files, or run tests
- Make architecture or security decisions
- Hold state across sessions (use `TODO.md` and the queue)
- Write DELEGATE or HANDBACK files directly to the queue directory (always use `enqueue()` for the audit record)
- Spawn beyond the recursion limits (max depth 3, max 5 concurrent sub-agents per parent) — refuse and return `status: blocked`/`escalate` instead of silently proceeding (see [Recursion Limits](#recursion-limits))

**Escalation triggers:** None — the Orchestrator is the top of the routing chain. If the user's request requires human input (security/compliance critical, budget exceeded), pause and surface to the user.

**Pause condition:** No pending DELEGATEs and no outstanding sub-agent spawns awaiting a HANDBACK → Orchestrator PAUSES. Does not invent new work.

---

### 2. Engineer

**Model:** `claude-haiku-4.5`  **Tier:** Cheap  **Skill:** `src/skills/roles/engineer.md`

**Purpose:** Execute well-scoped tasks at known file:line addresses. Cheapest implementation role.

**Capabilities:**
- Single-file edits, straightforward multi-file edits (≤ 3 files, same package)
- Unit test writing (given a clear spec)
- Documentation updates at known locations
- Dependency version bumps
- Simple bug fixes with a clear root cause

**Boundaries — Engineer MUST NOT:**
- Read multiple related files to understand context before implementing
- Make architectural decisions or design choices
- Modify public API contracts without explicit instruction

**Escalation triggers:**
- Change touches > 3 files across different packages → **Senior Engineer**
- Requires reading multiple related files to understand context → **Senior Engineer**
- Test failures after 2 fix attempts → **Senior Engineer**
- Architecture or API design decision required → **Lead Engineer**
- Auth, crypto, secrets, or security implications discovered → **Security Engineer**

---

### 3. Senior Engineer

**Model:** `claude-sonnet-5`  **Tier:** Medium  **Skill:** `src/skills/roles/senior-engineer.md`

**Purpose:** Plans unscoped work; handles multi-file implementations requiring architectural awareness.

**Capabilities:**
- Read related files to understand context before implementing
- Multi-file refactoring and moderate-complexity implementations
- CI/CD pipeline changes
- Breaking dependency updates
- Code review of Engineer outputs when flagged by Quality Engineer

**Boundaries — Senior MUST NOT:**
- Make cross-repo API contract decisions
- Resolve architectural disagreements between services
- Conduct formal security audits

**Escalation triggers:**
- Architecture or API contract decisions required → **Lead Engineer**
- Cross-service or cross-repo coordination needed → **Lead Engineer**
- Debugging root cause spans > 2 services → **Principal Engineer**
- Hard problem with > 2 failed fix attempts → **Principal Engineer**
- Auth, crypto, token handling, or compliance implications → **Security Engineer**

---

### 4. Lead Engineer

**Model:** `claude-sonnet-5`  **Tier:** Medium  **Skill:** `src/skills/roles/lead-engineer.md`

**Purpose:** Architecture decisions, 8-point code review, API contract design, conflict resolution.

**Capabilities:**
- Make architecture decisions authoritatively (API contracts, domain boundaries, data models)
- Conduct 8-point code review (correctness, safety, patterns, performance, security surface, maintainability, test coverage, documentation)
- Resolve conflicts between competing design approaches
- Coordinate cross-repo work — ensure consistency across services
- Produce DELEGATE blocks for Engineer/Senior to implement decisions

**Boundaries — Lead MUST NOT:**
- Conduct formal threat modelling or vulnerability assessment
- Implement code changes (produce implementation DELEGATEs instead)

**Escalation triggers:**
- Fundamentally hard architectural problem with no clear solution → **Principal Engineer**
- Security-critical design decisions (auth flows, crypto selection) → **Security Engineer**
- Cross-repo coordination at a scale requiring principal-level analysis → **Principal Engineer**

---

### 5. Quality Engineer

**Model:** `claude-sonnet-5`  **Tier:** Medium  **Skill:** `src/skills/roles/quality-engineer.md`

**Purpose:** Post-implementation validation. Verifies HANDBACK correctness and assesses model suitability.

**Capabilities:**
- Validate acceptance criteria against delivered changes
- Run `CONFIG=dev make lint && make test && make build` and report results
- Assess whether the model/effort tier was appropriate for the task
- Populate `metrics.quality` in the HANDBACK (0.0–1.0 float)
- Flag regressions, missing tests, or inadequate implementation

**Boundaries — QE MUST NOT:**
- Implement fixes for discovered issues (produce DELEGATE blocks instead)
- Make architecture decisions

**Escalation triggers:**
- Persistent build/lint failures after 2 re-run attempts → **Lead Engineer**
- Security-related failure patterns discovered → **Security Engineer**
- Systemic failure pattern across multiple tasks → **Principal Engineer**

---

### 6. Model Engineer

**Model:** `claude-sonnet-5`  **Tier:** Medium  **Skill:** `src/skills/roles/model-engineer.md`

**Purpose:** Analyse HANDBACK efficiency metrics; recommend model or effort tier adjustments.

**Capabilities:**
- Parse HANDBACK `metrics` blocks (tokens, cost, quality, duration_seconds)
- Compare actual vs. estimated token usage across task history
- Recommend model downgrade (cost saving) or upgrade (quality improvement)
- Identify effort-level mismatches (task was too small/large for the assigned tier)
- Write recommendations to `src/TOKEN_METRICS.md` in standardised format

**Boundaries — Model Engineer MUST NOT:**
- Implement code changes
- Approve or reject tasks — recommendations only

**Escalation triggers:**
- System-level quality regression spanning multiple roles → **Principal Engineer**
- Contested metrics recommendation → **Lead Engineer**

---

### 7. Principal Engineer

**Model:** `claude-opus-5`  **Tier:** Premium  **Skill:** `src/skills/roles/principal-engineer.md`

**Purpose:** Cross-service architecture, hard debugging, critical design decisions. Escalation only.

**Capabilities:**
- Root cause analysis spanning deep stack traces or multiple services
- Complex architectural analysis (data flow, race conditions, distributed system semantics)
- Hard debugging where Senior has made ≥ 2 failed attempts
- Critical design decisions that Lead cannot resolve
- Produce structured findings with exact file:line references
- Generate DELEGATE blocks for Engineer/Senior to implement findings

**Boundaries — Principal MUST NOT:**
- Implement fixes (findings → DELEGATEs for cheaper tiers)
- Conduct formal security audits (→ Security Engineer)

**Escalation triggers:**
- Security-critical design decisions (auth, encryption, key management) → **Security Engineer**
- Principal is the top of the non-security chain; if blocked, surface to user

---

### 8. Security Engineer

**Model:** `claude-fable-5` (unconditional default) | `claude-opus-4.8` (emergency fallback)  **Tier:** Premium  **Skill:** `src/skills/roles/security-engineer.md`

**Purpose:** Threat modelling, vulnerability assessment, compliance review. Always assigned for security-scoped work.

**Capabilities:**
- Formal threat modelling (STRIDE, attack surface analysis)
- Vulnerability assessment (OWASP Top 10, injection, broken auth, secrets exposure)
- Compliance review (OAuth 2.0, zero-trust, secrets handling, GDPR surface)
- CLI permission policy review
- Produce findings table (severity, file:line, description, recommendation)
- Generate DELEGATE blocks for Engineer/Senior to implement fixes

**Boundaries — Security Engineer MUST NOT:**
- Implement fixes (findings → DELEGATEs for cheaper tiers)
- Be skipped for any auth/crypto/secrets/compliance task

**Escalation triggers:**
- Security Engineer is the top of the security chain. Surface to user if findings require
  executive decision or external compliance sign-off.

---

## Handover Packet Protocol

All work is delegated via a **DELEGATE block** — constructed by the spawning agent and passed directly as the prompt of a sub-agent spawn call (the harness's Agent/Task tool). On completion, the receiving agent returns a **HANDBACK block** directly as that spawn call's result, in-context; the spawning agent never polls or reads a file to get it.

Every DELEGATE and HANDBACK is *also* durably recorded to the filesystem queue as an audit trail (`~/.agentic-engineers/{harness}/{session-id}/queue/incoming/TASK-NNN.yaml` and `.../queue/done/TASK-NNN-handback.yaml` respectively) — this is bookkeeping for audit and crash-recovery, not the transport. Nothing polls these paths to trigger work; see [Audit-Trail Strategy](#audit-trail-strategy).

### DELEGATE Block Format

> **Canonical schema:** `docs/specs/protocol-core-v1.0.yaml` (single source of truth)  
> **Deprecated:** `type: DELEGATE` — use `handoff_type: DELEGATE` instead. Files using `type:` will pass with a deprecation warning; the field will become an error in the next major version.

```yaml
# Passed directly as the sub-agent spawn prompt (dispatch).
# Audit copy also written to: ~/.agentic-engineers/{harness}/{session-id}/queue/incoming/TASK-NNN.yaml
---
task_id: my-task-identifier    # kebab-case, 3-50 chars (^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$)
handoff_type: DELEGATE         # canonical discriminator (NOT type:)
agent: senior-engineer         # hyphenated role name — see VALID_AGENTS below
skill: senior-engineer         # skill name resolving to src/skills/<skill>/
model: claude-sonnet-4.6       # must be explicit — no implicit defaults
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
  - "AC3: repro command passes with no failures"

# --- Optional extension fields (forward-compatible) ---
tokens_estimate: 8000          # estimated max tokens for this task
budget: 0.09                   # $ ceiling based on model + estimate
priority: 5                    # 1 (lowest) - 10 (highest)
deadline: "2026-06-08T18:00:00Z"
dependencies: []               # task_ids that must complete first
ancestry: [orchestrator]       # chain of agent roles from root to this DELEGATE's
                                # spawning parent, inclusive. REQUIRED whenever the
                                # spawning agent was itself spawned (depth > 0) — used
                                # to enforce max delegation depth and detect cycles.
                                # See Recursion Limits.
```

> **Required core fields:** `task_id`, `handoff_type`, `agent`, `skill`, `scope` (>=15 words),
> `plan` (>=2 steps, each >=3 words), `success_criteria` (>=1 item), `context` (>=20 words or non-empty array).
> This core schema is unchanged by the direct-spawn execution model — `ancestry` above is an
> additive, forward-compatible extension field, not a redesign of the required core.
>
> **Valid agents:** `orchestrator`, `engineer`, `senior-engineer`, `lead-engineer`,
> `principal-engineer`, `security-engineer`, `quality-engineer`, `model-engineer`
> (hyphens only — `senior_engineer` with underscores is invalid).

### HANDBACK Block Format

Canonical schema: [`docs/specs/protocol-core-v1.0.yaml`](../docs/specs/protocol-core-v1.0.yaml).
Required core fields: `task_id`, `status`, `output`, `metrics` (with `quality`, `tokens`, `cost`, `duration_seconds`).

> **Deprecated:** `type: HANDBACK` — use `handoff_type: HANDBACK` instead (same migration as DELEGATE).

```yaml
# Returned directly as the spawn call's result (dispatch), in-context.
# Audit copy also written to: ~/.agentic-engineers/{harness}/{session-id}/queue/done/TASK-NNN-handback.yaml
---
task_id: my-task-identifier    # must match the originating DELEGATE's task_id
handoff_type: HANDBACK         # canonical discriminator (NOT type:)
status: success                # success | failure | partial | blocked | escalate

output: |
  One-paragraph summary of what was done, files changed, and key decisions.
  e.g. "Modified path/to/file.py (lines 45-67) and path/to/other.ts (12-30);
  AC1-AC3 PASS via make verify."

metrics:                       # ALL four sub-fields are REQUIRED
  quality: 0.88                # float 0.0–1.0, self-assessed delivery quality
  tokens: 5840                 # non-negative int, total tokens (input + output)
  cost: 0.09                   # non-negative float, USD
  duration_seconds: 42         # non-negative float, wall-clock execution seconds

# --- Optional extension fields (forward-compatible) ---
model_used: claude-sonnet-4.6
effort_actual: medium
confidence: 0.9                # 0.0–1.0
escalations: 0
flags: []                      # advisory flags / anomalies
error: null                    # error detail when status is failure or blocked
escalation: null               # or ESCALATION block (see below) if status: escalate
```

> **Status values:** `success` (all criteria met), `failure` (criteria not met),
> `partial` (some criteria met), `blocked` (external dependency needed),
> `escalate` (requires higher-tier agent or human decision).  
> **Invalid statuses:** `complete` and `failed` are NOT valid — use `success` and `failure`.  
>
> **metrics sub-fields** (all required — no omissions accepted):  
> - `quality`: float 0.0–1.0 (self-assessed quality of delivered work)  
> - `tokens`: non-negative integer (total input + output tokens consumed)  
> - `cost`: non-negative float (USD monetary cost)  
> - `duration_seconds`: non-negative float (wall-clock execution time)

### ESCALATION Packet Format

When an agent hits an escalation trigger, it MUST stop implementation work and emit:

```yaml
# Embedded in HANDBACK under the `escalation:` key, or as a standalone file
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
  - Specific area 1 to investigate
  - Specific area 2 to investigate
```

The agent that receives this HANDBACK (the Orchestrator, or whichever role spawned the
escalating agent) reads the ESCALATION block in-context, constructs a new DELEGATE block
targeting `to_role` (using `handoff_type: DELEGATE` and `agent: principal-engineer`) with the
escalation content inlined in `context` and its own role appended to `ancestry`, and spawns
`to_role` directly — subject to the same depth/fan-out/cycle checks as any other spawn.

---

## ACK Protocol

Every agent MUST emit an ACK as its **first output** before performing any work.

### Standard ACK

```
✅ [Role Name] ACK — [TASK-ID]
```

### Blocked ACK (missing context)

```
⚠️ [Role Name] BLOCKED — [TASK-ID]
Missing: [list of what's missing or unclear]
Request: [what information is needed to proceed]
```

### Model Mismatch

If the agent detects it is running on a different model than specified in the DELEGATE `model:` field:

```
❌ MODEL_MISMATCH — expected claude-sonnet-4.6, got claude-haiku-4.5
Stopping. Orchestrator must re-delegate with the correct model.
```

### Completion Footer

Every agent MUST include in its final output:

```
MODEL_USED: claude-sonnet-4.6   # actual model used (not the requested model)
```

---

## Direct Sub-Agent Spawn Execution Model

> **Why this changed:** the framework previously specified an Orchestrator that polled a
> filesystem queue every 30–60 seconds, claimed tasks, and spawned agents as subprocesses
> correlated by HANDBACK files. An audit of 16 live session partitions found **zero tasks**
> ever traversed the queue that way — every real delegation happened via a direct sub-agent
> spawn instead, with the polling loop dead code alongside it. This section documents the
> model that was actually running, and closes the gap between spec and behavior. The queue
> is retained — see [Audit-Trail Strategy](#audit-trail-strategy) — but as a durable record,
> not a dispatch mechanism. This also satisfies `docs/SPEC.md`'s "NO Python scripts for
> queue management" constraint: there is no longer a polling script whose job is to manage
> the queue as a work source.

### Full Flow

```
1.  User request arrives, or the current agent generates a DELEGATE from prior
    HANDBACK output (e.g. re-delegating remaining work, or an ESCALATION)

2.  The spawning agent applies routing rules and selects the target role

3.  The spawning agent SPAWNS the target agent directly (Agent/Task tool),
    passing the DELEGATE block as the sub-agent's prompt. For independent
    tasks, it fans out multiple spawns in parallel — up to 5 concurrent per
    parent (see Recursion Limits)

4.  Each spawned agent:
      a. ACKs the task (first output)
      b. Loads its skill file from skill_refs
      c. Performs work — and MAY itself spawn further sub-agents if its own
         frontmatter grants `spawn_subagent` (see Tools-Frontmatter Permission
         Model), subject to the same depth/fan-out/cycle checks
      d. Returns a HANDBACK directly, as the result of the spawn call — there
         is no file to write and nothing to poll for this step to complete

5.  **Convention, not automatic:** the spawning agent MAY spawn Quality Engineer to
    validate the HANDBACK. Nothing triggers this on its own — it only runs if the
    spawning agent issues that DELEGATE:
      - Checks acceptance_criteria are met
      - Runs repro command to verify
      - Populates metrics.quality (0.0–1.0) in the HANDBACK

6.  **Convention, not automatic:** likewise, the spawning agent MAY spawn Model Engineer
    after a Quality Engineer verdict to analyse HANDBACK metrics:
      - Compares tokens used vs. estimated across task history
      - Emits model/effort recommendation if drift detected

7.  The spawning agent reads the HANDBACK it just received, in-context:
      - success    → mark TASK-NNN done in TODO.md
      - partial    → re-delegate remaining work (direct spawn)
      - blocked    → surface to user with blocker detail
      - escalate   → re-delegate the ESCALATION block at the higher tier (direct spawn)

8.  Every DELEGATE (at spawn) and every HANDBACK (at completion) is durably
    recorded to the queue via enqueue() — the audit trail. No step above
    depends on a file existing in incoming/, processing/, or done/; the queue
    is written to, never read from, for control flow

9.  If no pending DELEGATEs and no outstanding spawns remain → the
    Orchestrator PAUSES
```

### Recursion Limits

Direct spawn removes the natural throttling a polling loop provided — a queue nobody
drains just grows silently, but a spawn chain nobody bounds recurses actively. These
limits are the framework's convention for bounding that recursion. **No runtime code
counts depth, counts fan-out, or detects cycles today** — see [Tools-Frontmatter
Permission Model](#tools-frontmatter-permission-model) for what is and isn't checked in
practice. Every agent is expected to self-enforce the following:

- **Max delegation depth: 3.** Depth is measured in spawn hops from the root DELEGATE
  (depth 0 = the Orchestrator's own top-level DELEGATE; each direct spawn increments
  depth by 1). An agent operating at depth 3 MUST NOT itself spawn — it executes or
  refuses; it does not re-delegate further. This is *why* Engineer and Quality Engineer
  never need `spawn_subagent`: every routing path in this document reaches them at the
  final hop, and they are meant to be the leaf regardless of what depth they are
  reached at.
- **Max fan-out: 5 concurrent sub-agents per parent.** A single agent may have at most 5
  spawns in flight at once. Additional independent work waits for one of the first 5 to
  complete (or is grouped into a consolidating DELEGATE); it is never spawned as a 6th
  concurrent call.
- **Ancestry tracking (cycle detection).** Every DELEGATE issued by an agent that was
  itself spawned (depth > 0) MUST set the `ancestry` extension field: the ordered list
  of agent roles from the root to this DELEGATE's spawning parent, inclusive (see the
  DELEGATE schema above). Before spawning, the spawning agent checks whether the target
  role already appears in its own ancestry chain. If it does, that is a cycle — e.g.
  Senior Engineer escalates to Lead Engineer, and Lead Engineer's implementation
  DELEGATE incorrectly targets `senior-engineer` again for the same task — and the spawn
  MUST be refused.

**What an agent does when a limit is hit:** it stops; it does not silently proceed and
it does not silently drop the work. It returns a HANDBACK with `status: blocked` (the
limit is procedural and likely resolvable by consolidating or restructuring the
remaining fan-out) or `status: escalate` (the limit indicates a design problem — a
genuine cycle, or a task that fundamentally needs more than 3 hops — that a human or a
higher-tier agent must resolve), with `output` stating which limit was hit and why. The
agent that receives that HANDBACK decides how to proceed; the refusing agent never
invents a workaround (e.g. spawning "just one more" past the limit) on its own.

### Tools-Frontmatter Permission Model

The `tools:` key in each agent's source frontmatter (`src/agents/<name>-agent.md`) states
which roles are *meant* to spawn sub-agents. **Neither harness renderer enforces it:**

- **Claude Code:** `renderer/scripts/render-claude.sh` drops the `tools:` key entirely
  when rendering `~/.claude/agents/*.md` — every rendered Claude Code sub-agent gets the
  harness's full default tool access, including Engineer and Quality Engineer.
- **OpenCode:** `renderer/scripts/render-opencode.sh` documents the same reality plainly:
  "all agents use uniform allow-all permissions... the core constraint model is social
  (shared responsibility, code review, audit trails) rather than technical restrictions."

The PreToolUse hook (`renderer/scripts/claude-delegate-guard.py`) only checks that an
Agent/Task-tool call carries a well-formed DELEGATE block (required fields present,
`scope` ≥15 words, etc.). It does not check the calling agent's role, its `tools:` grant,
ancestry, depth, or fan-out — none of those checks exist in code on either harness today.

The table below is the convention every role is expected to follow. Compliance is the
spawning agent's own judgment call, guided by this document — not a runtime guarantee.

| Role | Spawns sub-agents? | Why |
|---|---|---|
| Orchestrator | Yes | Root of every delegation chain; routes to any specialist |
| Senior Engineer | Yes | Delegates to Engineer, or escalates to Lead/Principal/Security (§3) |
| Lead Engineer | Yes | Produces implementation DELEGATEs after an architecture decision (§4) |
| Principal Engineer | Yes | Produces implementation DELEGATEs after a cross-service finding (§7) |
| Security Engineer | Yes | Produces implementation DELEGATEs for each audit finding (§8) |
| Model Engineer | No | Recommendations only — returns findings in its own HANDBACK, never delegates |
| Engineer | No | Leaf by design — escalates via HANDBACK `status: escalate`, never re-delegates |
| Quality Engineer | No | Leaf by design — issues raised go in QE's own HANDBACK, not a spawn |

### Audit-Trail Strategy

Dispatch no longer touches the filesystem queue, so the queue's contents no longer imply
that work happened — the audit trail is now an explicit obligation, not a side effect:

- **At spawn (dispatch time):** the spawning agent MUST `enqueue()` the DELEGATE block to
  `.../queue/incoming/TASK-NNN.yaml` at or immediately after the spawn call.
- **At completion:** the spawning agent MUST `enqueue()` the HANDBACK it received to
  `.../queue/done/TASK-NNN-handback.yaml` as soon as the spawn call returns.
- **At Quality Engineer verdict:** in addition to the general HANDBACK recording above, a
  QE `status: success`/`failure` verdict is recorded so the audit trail distinguishes
  "work happened" from "work was verified" — this is what audit/monitoring tooling (e.g.
  the `consistency-checker` and `session-analyzer` skills) reads to reconstruct what
  actually ran, since it can no longer observe dispatch directly.

If a DELEGATE or HANDBACK is not enqueued, it did not happen as far as the audit trail,
cost tracking (Model Engineer), and crash-recovery tooling are concerned — even though the
work itself completed in-context. Treat the `enqueue()` call as part of the spawn, not as
optional cleanup afterward.

**Known gap:** this is not happening reliably. A check of real session directories
(`~/.agentic-engineers/{harness}/{session-id}/queue/`) across ~12 live sessions found only
placeholder `.keep.me` files — no DELEGATE or HANDBACK actually recorded. Treat this
section as the target behavior, not a guarantee of what has been captured so far.

### Pause Condition

The Orchestrator **pauses** when it has no pending DELEGATEs to issue and no outstanding
sub-agent spawns awaiting a HANDBACK. It does NOT invent new work. This is by design —
reduced autonomy prevents runaway scope.

To resume: give the Orchestrator a new request, or add a task to `TODO.md`.

---

## Example Workflows

### Example 1 — Simple File Edit (Engineer)

```yaml
# Spawned directly as the Engineer sub-agent's prompt.
# Audit copy: ~/.agentic-engineers/{harness}/{session-id}/queue/incoming/TASK-101.yaml
---
task_id: task-101-postal-validation
handoff_type: DELEGATE
agent: engineer
skill: engineer
model: claude-haiku-4.5
effort: low

scope: |
  Add AU PostalCode validation rule to address validator in src/validation/postal.py.
  PostalCode is optional but when present must be exactly 4 digits. Out of scope:
  any changes to the validator public interface or other validation rules.

context:
  - "File: src/validation/postal.py (lines 12-34) — add 4-digit AU postcode regex rule"
  - "File: tests/test_postal.py — add unit tests for valid and invalid postcodes"
  - "Repo: github.com/niallyoung/payments-service, branch: feature/postal-validation"

plan:
  - "Step 1: Read src/validation/postal.py (lines 12-34) to understand existing rule structure"
  - "Step 2: Add AU_POSTCODE_REGEX and PostalCodeValidator at line 15 (4 digits only)"
  - "Step 3: Write tests for valid ('2000', '0800') and invalid ('ABC', '123', '12345') cases"
  - "Step 4: Run make test FILTER=test_postal and verify 0 failures"

success_criteria:
  - "AC1: PostalCode '2000' and '0800' pass validation"
  - "AC2: PostalCode 'ABC', '123', '12345' are rejected with a clear error message"
  - "AC3: make test FILTER=test_postal passes with no failures"

tokens_estimate: 2000
budget: 0.03
```

**Agent output:**

```
✅ Engineer ACK — TASK-101

[implements postal.py and test_postal.py changes]

Changes:
- src/validation/postal.py:15 — added AU_POSTCODE_REGEX and PostalCodeValidator rule
- tests/test_postal.py:1-28 — added tests for valid/invalid AU postcodes

CI: PASS — make test FILTER=test_postal: 6 passed
MODEL_USED: claude-haiku-4.5
```

---

### Example 2 — Escalation Chain (Engineer → Senior → Lead)

**Step 1: Engineer hits escalation trigger**

```yaml
# HANDBACK from Engineer
---
task_id: task-202-payment-refactor
handoff_type: HANDBACK
status: escalate

output: |
  Payment refactor requires changes to 5 files across payment/ and checkout/ packages.
  This exceeds the 3-file boundary for Engineer. API contract between the two domains
  needs a decision before implementation.

metrics:
  quality: 0.0
  tokens: 1200
  cost: 0.02
  duration_seconds: 18

escalation:
  task_id: task-202-payment-refactor
  type: ESCALATION
  from_role: engineer
  to_role: senior-engineer
  reason: |
    Change touches 5 files in 2 packages (payment/, checkout/).
    Architectural boundary between payment and checkout domains needs
    clarification before implementation can proceed.
  findings_so_far: |
    payment/processor.py:45-67 needs new checkout_id param.
    checkout/domain.py:12-30 needs a PaymentRef type.
    Both changes affect the public API contract.
  recommended_focus:
    - Define PaymentRef type boundary (checkout-owned vs payment-owned)
    - Confirm API contract for processor.create_payment(checkout_id)
```

**Step 2: Orchestrator re-delegates to Senior Engineer**

```yaml
# Spawned directly as the Senior Engineer sub-agent's prompt (re-delegation after ESCALATE).
# Audit copy: ~/.agentic-engineers/{harness}/{session-id}/queue/incoming/TASK-202-senior.yaml
---
task_id: task-202-senior-payment-arch
handoff_type: DELEGATE
agent: senior-engineer
skill: senior-engineer
model: claude-sonnet-4.6
effort: high

scope: |
  Determine PaymentRef type ownership (checkout/ vs payment/ package) and define the
  processor.create_payment(checkout_id) API contract. Engineer escalated TASK-202 because
  the refactor touches 5 files across two domain packages. Out of scope: implementation
  (produce DELEGATE blocks for Engineer to implement the decided design).

context:
  - "Escalation from task-202-payment-refactor: payment refactor touches 5 files in 2 packages"
  - "File: src/payment/processor.py (lines 45-67) — needs new checkout_id param"
  - "File: src/checkout/domain.py (lines 12-30) — needs a PaymentRef type"
  - "Repo: github.com/niallyoung/payments-service, branch: feature/payment-refactor"
  - "Root cause: Both changes affect the public API contract; domain boundary unclear"

plan:
  - "Step 1: Read payment/processor.py:45-67 and checkout/domain.py:12-30 to understand current boundaries"
  - "Step 2: Determine if PaymentRef belongs in checkout/ (checkout-owned) or payment/ (payment-owned)"
  - "Step 3: Define the processor.create_payment(checkout_id) API contract"
  - "Step 4: Produce DELEGATE blocks for Engineer to implement the decided contract"
  - "Step 5: Escalate to Lead Engineer if API contract decision exceeds Senior's authority"

success_criteria:
  - "AC1: PaymentRef type ownership is decided and documented"
  - "AC2: processor.create_payment API contract is defined with the checkout_id parameter"
  - "AC3: Implementation DELEGATEs produced for Engineer (or escalated to Lead)"

tokens_estimate: 8000
budget: 0.09
```

**Step 3: Senior hits arch escalation trigger → escalates to Lead**

Senior reads related files, determines the PaymentRef type crosses a domain boundary that
requires an explicit API contract decision, and emits a HANDBACK with `status: escalate`
targeting Lead Engineer — including its analysis as `findings_so_far`.

**Step 4: Lead makes the decision, produces implementation DELEGATEs**

Lead Engineer emits an architecture decision document and two DELEGATE blocks:
one targeting Senior to implement the `PaymentRef` type, one targeting Engineer for
the updated `processor.py` call site.

---

### Example 3 — Security Audit (Security Engineer)

```yaml
# Spawned directly as the Security Engineer sub-agent's prompt.
# Audit copy: ~/.agentic-engineers/{harness}/{session-id}/queue/incoming/TASK-303.yaml
---
task_id: task-303-jwt-refresh-audit
handoff_type: DELEGATE
agent: security-engineer
skill: security-engineer
model: claude-fable-5
effort: max

scope: |
  Audit the JWT refresh token flow in auth-service for vulnerabilities before shipping.
  The feature introduces sliding-window refresh: access tokens are transparently reissued
  within a 15-minute window. Audit replay attacks, missing expiry checks, and insecure
  token storage patterns. Out of scope: implementing fixes (produce DELEGATE blocks instead).

context:
  - "File: src/auth/middleware.py (lines 45-89) — token validation middleware"
  - "File: src/auth/tokens.py (lines 10-60) — token issuance and expiry logic"
  - "File: src/auth/handlers.py (lines 120-175) — refresh token redemption handler"
  - "Repo: github.com/niallyoung/auth-service, branch: feature/jwt-refresh"
  - "Concern: replay attacks on the sliding-window refresh window; missing exp validation; localStorage storage"

plan:
  - "Step 1: Read middleware.py:45-89, tokens.py:10-60, handlers.py:120-175"
  - "Step 2: Identify replay attack vectors in the sliding-window refresh flow"
  - "Step 3: Check that exp claim is validated at every token issuance and redemption path"
  - "Step 4: Review token storage patterns for secrets exposure (httpOnly cookie vs localStorage)"
  - "Step 5: Produce findings table (severity, file:line, description, recommendation)"
  - "Step 6: Produce DELEGATE blocks for Engineer/Senior to implement each finding"

success_criteria:
  - "AC1: Findings table produced (severity, file:line, description, recommendation)"
  - "AC2: DELEGATE blocks produced for each finding requiring a fix"
  - "AC3: No CRITICAL or HIGH findings left without an implementation DELEGATE"

tokens_estimate: 12000
budget: 0.15
```

**Expected output format:**

```
✅ Security Engineer ACK — TASK-303

## Findings

| Severity | File:Line | Issue | Recommendation |
|----------|-----------|-------|----------------|
| CRITICAL | src/auth/tokens.py:34 | exp claim not validated on refresh | Validate exp before issuing new token |
| HIGH     | src/auth/handlers.py:142 | refresh token not invalidated after use | Add jti blacklist on redemption |
| MEDIUM   | src/auth/middleware.py:61 | token stored in localStorage | Move to httpOnly cookie |

## Implementation DELEGATEs

[DELEGATE block for Engineer — fix exp validation at tokens.py:34]
[DELEGATE block for Senior — implement jti blacklist in handlers.py]
[DELEGATE block for Engineer — update token storage in middleware.py]

MODEL_USED: claude-opus-4.8
```

---

### Example 4 — Post-Implementation Validation (Quality Engineer)

```yaml
# Spawned directly as the Quality Engineer sub-agent's prompt.
# Audit copy: ~/.agentic-engineers/{harness}/{session-id}/queue/incoming/TASK-404-qe.yaml
---
task_id: task-404-qe-address-validation
handoff_type: DELEGATE
agent: quality-engineer
skill: quality-engineer
model: claude-sonnet-4.6
effort: medium

scope: |
  Validate the HANDBACK from task-404 (Senior Engineer refactored address validation
  module: 3 files, 87 lines changed). Verify all acceptance criteria are met, run the
  test suite, and assess whether the assigned model was appropriate for the task.
  Out of scope: implementing fixes — produce DELEGATE blocks if issues are found.

context:
  - "HANDBACK to validate: task-404 (Senior Engineer, address validation refactor)"
  - "Files changed: src/validation/address.py, src/validation/postal.py, tests/test_address.py"
  - "Repo: github.com/niallyoung/validation-service, branch: feature/address-refactor"
  - "Repro command: CONFIG=dev make lint && CONFIG=dev make test && CONFIG=dev make build"

plan:
  - "Step 1: Run CONFIG=dev make lint — verify 0 errors"
  - "Step 2: Run CONFIG=dev make test — verify all address tests green"
  - "Step 3: Run CONFIG=dev make build — verify successful build"
  - "Step 4: Verify each AC from task-404 against delivered changes"
  - "Step 5: Assess model suitability (was claude-sonnet-4.6 appropriate or would haiku suffice?)"
  - "Step 6: Populate metrics block in HANDBACK with quality score and assessment"

success_criteria:
  - "AC1: make lint passes with no errors"
  - "AC2: make test passes, all address tests green"
  - "AC3: make build succeeds"
  - "AC4: metrics block in HANDBACK populated with quality (0.0-1.0), tokens, cost, duration_seconds"

tokens_estimate: 4000
budget: 0.09
```

---

## Role Summary Table

| Role | Skill File | When to Use | Escalates To |
|------|-----------|-------------|--------------|
| Orchestrator | `src/skills/orchestration/task-routing.md` | All task entry points | User (for critical decisions) |
| Engineer | `src/skills/roles/engineer.md` | Scoped tasks, file edits, tests | Senior / Lead / Security |
| Senior Engineer | `src/skills/roles/senior-engineer.md` | Planning, multi-file changes | Lead / Principal / Security |
| Lead Engineer | `src/skills/roles/lead-engineer.md` | Code review, arch guidance | Principal / Security |
| Quality Engineer | `src/skills/roles/quality-engineer.md` | Post-implementation validation | Lead / Security / Principal |
| Model Engineer | `src/skills/roles/model-engineer.md` | After QE HANDBACK with metrics | Lead / Principal |
| Principal Engineer | `src/skills/roles/principal-engineer.md` | Hard bugs, cross-service design | Security / User |
| Security Engineer | `src/skills/roles/security-engineer.md` | All security-scoped work | User |

---

## Token Burn Reduction

- **Summarise, don't recap** — post findings as tables, not prose
- **Stay thin** — Orchestrator reads HANDBACK summaries only, not full outputs
- **No context spillover** — each DELEGATE is self-contained; receiving agent has no session state
- **Cite line numbers** — engineers work at the addresses given; no exploring
- **Chain bash commands** — use `&&` to combine related operations
- **Trust tool confirmations** — never re-read a file you just edited
- **Grep before view** — find exact lines first, then `view_range` only that section
- **Model Engineer feedback loop** — use token usage trends to downgrade over-provisioned roles

> For full cost tracking spec, see [`src/TOKEN_METRICS.md`](TOKEN_METRICS.md).
