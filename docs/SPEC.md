---
name: Agentic Engineers Implementation Specification
description: Current state of the agent orchestration system, queue mechanics, and operational constraints
version: 2.0
updated: 2026-08-11
phase: Post-slimdown (SPEC-2026-005)
status: Current
type: specification
---

# Agentic Engineers Implementation Specification

**Last Updated:** 2026-08-11
**Constraint:** No external scripts/tools own orchestration — all runtime work flows through AGENTS via DELEGATE/HANDBACK; Python is advisory only (see below).

---

## Executive Summary

The Agentic Engineers system routes all work through specialized AI agents — Orchestrator,
Engineer, Senior Engineer, Quality Engineer, Lead Engineer, Principal Engineer, Security
Engineer, Model Engineer — via the DELEGATE/HANDBACK protocol. The Orchestrator is the
single entry point: it builds a DELEGATE and dispatches it by directly spawning a
sub-agent with the DELEGATE as the prompt, then reads the HANDBACK from that spawn's
result. There is no polling loop, timer, or daemon. The queue at
`~/.agentic-engineers/{harness}/{session-id}/queue/` remains a durable inbox and audit
substrate (LOCKED paths, unchanged) — not the dispatch mechanism.

---

## ORCHESTRATOR-FIRST EXECUTION MODEL (MANDATORY)

**This is a hard constraint. All work MUST flow through the Orchestrator. No exceptions.**

The Orchestrator is the single entry point and single router. Dispatch happens by
directly spawning a sub-agent with the DELEGATE as its prompt — control flow lives in the
Orchestrator's own agent context, not in a Python process polling a directory on a timer.

1. **No Direct Agent Invocation.** Engineers MUST NOT invoke specialist agents directly
   or hand-write DELEGATE blocks and pass them out of band. All work is routed by the
   Orchestrator, which owns the decision tree.
2. **Dispatch is a Direct Sub-Agent Spawn.** The Orchestrator builds a DELEGATE per the
   DELEGATE/HANDBACK Protocol section below, spawns a sub-agent with it as the prompt via
   the harness's sub-agent tool, and reads the returned HANDBACK directly from the tool
   result. There is NO polling interval, NO timer, and NO intermediate queue hop required
   for the Orchestrator to observe a result — dispatch and collection are synchronous
   with respect to the Orchestrator's own reasoning.
3. **Control Flow Lives in Agent Context; Python is Advisory Only.** Routing, escalation,
   retries, and the DELEGATE → spawn → HANDBACK → gate lifecycle are executed by agent
   reasoning. Python modules MAY validate a DELEGATE against a schema, score a HANDBACK,
   compute cost/token rollups, or recommend a model — as pure functions returning data to
   the agent. They MUST NOT own the control loop, decide what runs next, or spawn/supervise
   agents. If removing a helper would halt the system rather than degrade its advice, it
   is control flow and is prohibited here.
4. **The Queue is a Durable Inbox and Audit Substrate, Not the Dispatch Mechanism.** The
   canonical paths in the LOCKED "Queue Architecture & Paths" section remain authoritative
   and unchanged. The queue's role is narrowed to: (a) accepting work submitted while no
   Orchestrator context is live, and (b) holding durable DELEGATE/HANDBACK records for
   audit and resumption after a context ends. A live Orchestrator drains the inbox at
   start and after each task completes — it does not wake on a timer to check it.
5. **Recursion, Depth and Fan-Out Limits (MANDATORY).** Depth limit 3 — the Orchestrator
   is depth 0; a specialist it spawns is depth 1; a task at depth 3 MUST NOT spawn further
   sub-agents, it completes the work itself or returns `status: blocked`. Fan-out limit 5
   — a parent MUST NOT have more than 5 concurrent children; excess work is queued by the
   parent and dispatched as children complete. Every DELEGATE MUST carry `depth` and
   `ancestry` (ordered ancestor task_ids from the root); a parent MUST refuse to spawn a
   child whose `(agent_role, scope)` pair already appears in its own ancestry — that is a
   delegation cycle. Exceeding any limit is a refusal (`status: blocked`/`escalate` naming
   the limit hit), never a silent truncation.
6. **Permissions are Declared in Agent `tools` Frontmatter.** Each agent declares its
   allowed tools in its frontmatter `tools:` field; the sub-agent spawn tool is granted to
   the Orchestrator and, per `src/AGENTS.md`'s Tools-Frontmatter Permission Model table, to
   Senior Engineer, Lead Engineer, Principal Engineer, and Security Engineer for producing
   and dispatching implementation DELEGATEs after a review, architecture, or audit
   decision — Engineer, Quality Engineer, and Model Engineer are leaves by design and do
   not spawn. Least privilege applies to review/audit roles otherwise (read/search, not
   Write/Edit, unless a task requires it). Granting spawn capability to a new role is a
   SPEC change via `spec-management`.
7. **Audit Trail: Append-Only JSONL, Write-Only from the Agent.** Every orchestration
   event is appended as one JSON object per line to
   `~/.agentic-engineers/{harness}/{session-id}/audit/events-YYYY-MM-DD.jsonl` — required
   events: `delegate_issued`, `subagent_spawned`, `handback_received`, `gate_result`,
   `escalation`, `refusal`, `limit_exceeded`; required fields: `ts` (ISO-8601 UTC),
   `event`, `task_id`, `parent_task_id`, `depth`, `agent_role`, `agent_model`, `status`,
   and token/cost fields where applicable. Agents append; they MUST NOT rewrite, reorder,
   truncate, or delete prior lines — corrections are new events, never edits. No metric may
   be reported that is not grounded in a logged event.
8. **No External Scripts, Tools, or Cron Jobs (Agent Operations).** No Python owns queue
   management, dispatch, scheduling, or supervision; no Makefile targets for Orchestrator
   operations; no shell scripts for queue automation; no cron jobs, daemons, or background
   timers for polling, wakeups, or metrics collection. Advisory Python under clause 3 is
   permitted. **Build/install-only exemptions:** `renderer/scripts/`, `make install*`,
   `make render-*` — build-time operations, not runtime agent operations.

**Prohibited, no exceptions:** reintroducing a polling loop/timer/daemon/cron for
orchestration; direct agent invocation bypassing the Orchestrator; spawning from a role
whose `tools:` frontmatter doesn't grant it; exceeding depth 3 or fan-out 5, or silently
truncating instead of refusing; spawning a child whose `(agent_role, scope)` already
appears in its own ancestry; rewriting/reordering/deleting audit-log lines; reporting an
unlogged metric; hardcoding quality scores, gate decisions, or approval constants;
approving work solely on a sub-agent's self-reported confidence; skipping quality gates
or escalation rules; using "trivial fix" or similar undefined escape clauses to bypass the
Orchestrator; letting CI/CD or external systems invoke orchestration scripts directly.

**Why this constraint exists:** the earlier polling formulation required a Python
scheduler that both violated the no-external-scripts constraint and never carried a
single real task in any live session (see SPEC-2026-004 in the Update Log). Moving control
flow into agent context and dispatching by direct spawn achieves the original intent using
the harness itself — a complete audit trail (every spawn/handback is a real logged event),
correct routing (the decision tree is applied by the agent that owns it), and accurate
cost tracking (metrics derive from logged events, not constants). Rendering infrastructure
(harness distribution, build-time skill rendering) may use subprocess for deterministic
build operations — this constraint is about orchestration/agent runtime code, not build
infrastructure.

---

## SDLC ENFORCEMENT HOOKS (MANDATORY)

Git hooks are required for all contributors and enforce SPEC compliance and quality gates
at commit/push time.

| Hook | Enforces | Severity |
|------|----------|----------|
| **pre-commit** | SPEC compliance (no external scripts, cron files, process execution); secret detection; YAML/JSON validity | ❌ BLOCK |
| **commit-msg** | Message format/length; DELEGATE/HANDBACK protocol compliance | ❌ BLOCK |
| **pre-push** | Agent YAML frontmatter validity; documentation consistency (SPEC.md/AGENTS.md/README.md presence + required fields) | ❌ BLOCK |
| **pre-push** | Test suite execution | ⚠️ WARN |

**Installation:** `make install` (or manually: `git config core.hooksPath .githooks` and
`chmod +x .githooks/pre-commit .githooks/commit-msg .githooks/pre-push`).

**Bypass (emergencies only, must include a documented reason, approver, and follow-up task):**

```bash
BYPASS_HOOK_VALIDATION=true git commit -m "emergency: reason"   # bypass SPEC/secret checks
SKIP_HOOKS=1 git commit -m "emergency: reason"                  # bypass all pre-commit checks
SKIP_HOOKS=1 git push                                            # bypass pre-push checks
```

Never bypass for lazy commits, avoiding review, skipping tests, or committing secrets.

---

## DOG-FOOD PRINCIPLE: Self-Improving Through Continuous Feedback

Every agent and quality system this framework builds is validated by the quality systems
it helps improve: agent output is checked by the quality gates it implements, gates are
reviewed by Quality Engineer, whose feedback informs Model Engineer's routing
recommendations, and better routing produces better work — improving the next round of
feedback. Proactive (code → gate → escalate-if-needed → fix → next code, minutes), not
the traditional reactive cycle (code → test → fix → deploy, days).

---

## COMPLETE SCRIPT INVENTORY

Documents every script file in the repository and its compliance status with the
ORCHESTRATOR-FIRST EXECUTION MODEL. Any script not listed here is a SPEC violation and
must be removed or converted to an Agent SKILL within 30 days of discovery.

### EXEMPT: Build-Time & Setup Scripts — `renderer/scripts/`

Rendering and installation tooling (agent/skill/spec rendering per harness, config
validation, backup/install helpers). Exempt because these run at build/setup time only
and never participate in runtime orchestration or queue processing. See
[RENDERING.md](RENDERING.md) for the full pipeline and per-file descriptions.

### COMPLIANT: Root `scripts/` — Advisory & Compliance Tooling

Each of these is a pure, callable advisory helper (clause 3) or a pre-commit/CI gate —
none owns dispatch, scheduling, or supervision:

| Script | Purpose |
|--------|---------|
| `check_protocol_compliance.py` | Validates DELEGATE/HANDBACK blocks against protocol schema |
| `detect_circular_imports.py` | Static import-cycle detector (CI gate) |
| `annotate_token_costs.py` | Advisory cost/token rollup formatting |
| `format_skill_report.py` | Formats skill test/validation output |
| `run_skill_tests.py` | Test runner for skill scripts (invoked by CI/make, not autonomous) |
| `validate_skills.py` | SKILL.md frontmatter + registry validation |
| `validate-spec-constraints.py` | Pre-commit SPEC constraint checker |
| `get_version.py` | Reads/reports framework version |
| `validate_opencode_config.py` | OpenCode config generation gate |
| `entropy_detector.py` | Entropy-based credential/secret detector (security gate) |
| `opencode-safe.sh` | OpenCode guard wrapper |
| `check-gitconfig-no-tokens.sh` | Pre-commit check for tokens leaking into gitconfig |

### ENFORCEMENT CLAUSE

Any script outside `renderer/scripts/` (build-time exempt) or the root `scripts/` table
above is non-compliant. It must be removed immediately or converted to a properly-scoped
Agent SKILL (with a `SKILL.md`) within 30 days of discovery.

---

## Core Architecture

### Agents & Roles (Multi-Agent Model)

All work enters via **Orchestrator** (default entry point), which applies the routing
decision tree below to delegate to specialists.

| Role | Model | Effort | Purpose |
|------|-------|--------|---------|
| **Orchestrator** | claude-sonnet-5 | low | Entry point; routing decisions; direct sub-agent dispatch; metrics collection |
| **Engineer** | claude-haiku-4.5 | high | Execute well-scoped tasks with pre-written plans |
| **Senior Engineer** | claude-sonnet-5 | high | Complex coding without a plan; diagnosis; planning |
| **Lead Engineer** | claude-sonnet-5 | high | Code review; quality verification; unblock stuck tasks |
| **Quality Engineer** | claude-sonnet-5 | medium | Tier 1 quality checks; model suitability assessment |
| **Principal Engineer** | claude-opus-5 | high | Cross-service architecture; complex multi-step planning |
| **Security Engineer** | claude-fable-5 | max | Security analysis; vulnerability audits; threat modeling (defensive-scope only, see LOCKED model section) |
| **Model Engineer** | claude-sonnet-5 | high | Analyze feedback; recommend optimal model/effort |

**Cost Target Distribution:** Orchestrator 55% · Engineer 18% · Senior Engineer 8% ·
Quality Engineer 8% · Lead Engineer 3% · Model Engineer 3% · Principal Engineer 3% ·
Security Engineer 2%. (Rebalanced from the prior Haiku-Orchestrator distribution now that
Orchestrator runs on Sonnet-tier; see Update Log SPEC-2026-005.)

---

## Routing Decision Tree (Orchestrator)

When the Orchestrator receives a task (a user request, or work drained from the durable
inbox at context start):

1. **Security-scoped?** (auth, crypto, data protection, vulnerability) → **Security
   Engineer** (blocks all other routes)
2. **Cross-service architecture?** (affects >2 repos, service boundaries) → **Principal
   Engineer**
3. **Complex coding WITHOUT a pre-written plan?** → **Senior Engineer** (writes the plan
   first; returns HANDBACK with a plan, not code)
4. **Code review or quality verification?** → **Lead Engineer** or **Quality Engineer**
5. **Well-scoped with a pre-written plan, low-medium complexity?** → **Engineer** (Red-Green
   TDD for code changes)
6. **Otherwise** → escalate to a human (unclear scope)

---

## Queue Architecture & Paths (LOCKED SPEC)

**⚠️ SPECIFICATION LOCKED as of 2026-05-26 — path order revised 2026-06-11**

This section defines the canonical queue path architecture for all harnesses. Changes to
queue paths require approval via the `spec-management` skill.

> **2026-06-11 change:** the path order is now **`{harness}/{session-id}`**, the
> reverse of the original `{session-id}/{harness}`. Rationale: humans and
> operators browse the tree by harness name, not by opaque session UUID, and
> session IDs cannot collide across harnesses when harness is the top level.
> `setup/migrate-queue-paths.sh` migrates existing installs to the new order.

### Canonical Queue Path

**All harnesses MUST use: `~/.agentic-engineers/`**

Queue directory structure (**harness first, then session-id**) — identical shape repeats
under each of the four harness directories:
```
~/.agentic-engineers/
└── copilot/                            # or claude/, opencode/, pi/ — identical below
    └── {session-id}/                   # UUID: 54744939-4acb-430c-b2c4-3b8322289d0b
        ├── queue/
        │   ├── incoming/               # New DELEGATEs waiting for routing
        │   ├── processing/             # Work assigned to agents, HANDBACKs awaiting review
        │   ├── done/                   # Completed work
        │   └── failed/                 # Failed work (optional, for archival)
        └── session-state/
```

**Supported Harnesses (ALL REQUIRE SAME BASE):**
- **copilot**: Uses `~/.agentic-engineers/copilot/{session-id}/queue/`
- **claude**: Uses `~/.agentic-engineers/claude/{session-id}/queue/`
- **opencode**: Uses `~/.agentic-engineers/opencode/{session-id}/queue/`
- **pi**: Uses `~/.agentic-engineers/pi/{session-id}/queue/`

**CRITICAL:** There are NO EXCEPTIONS. All four harnesses use the same `~/.agentic-engineers/` base directory. No harness may use its own legacy path.

### Queue Subdirectories (Standard)

All queue directories MUST contain four standard subdirectories:

| Directory | Purpose | Contents |
|-----------|---------|----------|
| **incoming/** | New work waiting for routing | DELEGATE blocks from humans or Orchestrator |
| **processing/** | Work assigned to agents | HANDBACKs awaiting review by Quality Engineer |
| **done/** | Completed work | Final decisions ready for human action |
| **failed/** | Failed work (optional) | HANDBACKs with status=failed or blocked beyond recovery |

All subdirectories exist across all four harnesses (copilot, claude, opencode, pi).

### Unsupported Legacy Paths (DEPRECATED)

The following paths are **DEPRECATED and MUST NOT be used**:

| Legacy Path | Status | Migration |
|-------------|--------|-----------|
| `~/.copilot/queue/` | ❌ DEPRECATED | Migrated to `~/.agentic-engineers/copilot/{session-id}/queue/` |
| `~/.claude/queue/` | ❌ DEPRECATED | Migrated to `~/.agentic-engineers/claude/{session-id}/queue/` |
| `artifacts/queue/` | ❌ DEPRECATED | Migrated to `~/.agentic-engineers/*/{session-id}/queue/` |

**Migration Completed:** 2026-05-26

**Effect of Using Legacy Paths:** Using any legacy path will cause a `RuntimeError` from the queue isolation layer (queue-isolation skill) because those paths are no longer monitored by the Orchestrator or harness renderers.

### Enforcement Rules

**1. Queue-Isolation REQUIRED (No Fallback Logic)**
- QueueManager MUST have queue-isolation skill available at runtime
- If queue-isolation is unavailable, QueueManager raises `RuntimeError` immediately
- Error message MUST mention canonical path and list all unsupported legacy paths
- NO fallback to legacy paths; NO conditional logic to support old paths

**2. Orchestrator Hard Constraint**
- Orchestrator MUST read and write queue records ONLY from `~/.agentic-engineers/{harness}/{session-id}/queue/`
- Orchestrator detects session-id from COPILOT_SESSION_ID or CLAUDE_SESSION_ID environment variables
- Orchestrator MUST NOT check for legacy paths (e.g., `~/.copilot/queue/`)
- Orchestrator MUST NOT implement conditional logic for different harnesses; all use same base

**3. Harness Renderers (Build-Time Compliance)** — all harness configuration renderers
(copilot, claude, opencode, pi) MUST output `QUEUE_PATH=~/.agentic-engineers/{harness}/{session-id}/queue/`;
build-time validation checks correct path; pre-commit hooks validate no legacy paths in
harness code.

**4. Pre-Commit Hooks (Enforcement Gate)** — git hooks MUST block commits introducing
legacy paths (`~/.copilot/queue`, `~/.claude/queue`, `artifacts/queue`), erroring with
`"Legacy queue paths found in {file} — use ~/.agentic-engineers/ instead"`. Exception:
allowed in `src/orchestration/queue_compat.py` (marked DEPRECATED) and `_archive/`.

**5. Testing Validation (CI Gate)** — `tests/test_queue_path_centralization.py` (8+
tests) validates the Orchestrator initializes ONLY from the canonical path, all 4
harnesses use the same base, and no legacy paths exist in active source code.

### Validation Procedures

**Pre-Merge Gate (automated):** grep `src/` for `\.copilot/queue`, `\.claude/queue`, and
`artifacts/queue` (must return 0 matches outside `_archive/`/`queue_compat.py`); verify
every harness config emits the canonical `QUEUE_PATH`; run
`pytest tests/test_queue_path_centralization.py -v` (all 8+ tests, covering isolation-skill
requirement, canonical-path-only checks, cross-harness consistency, and pre-commit
enforcement); the same suite runs in CI on every push and blocks merge on failure.

---

## Queue SLA & Governance

Queue health is enforced when a live Orchestrator drains the inbox (no daemon, no cron,
no timer). Detection resolution is bounded below by how often an Orchestrator context is
active; SLA targets shorter than that are aspirational, not precisely enforceable.

### SLA Thresholds

| Transition | Target | Warn | Breach | On breach |
|------------|--------|------|--------|-----------|
| incoming -> processing (claim) | 30s | 180s | 600s | Escalate to operator (no live Orchestrator) |
| processing -> done/failed (normal) | - | 300s | 600s | Orphan -> crash recovery |
| processing -> done/failed (effort: high\|max) | - | 600s | 900s | Orphan -> crash recovery |
| failed -> retry (per attempt) | - | - | backoff curve | Re-enqueue to retry-pending/ |
| retry attempts exhausted | - | - | 3 attempts | Move to failed/, escalate to Lead Engineer |

### Retry & Backoff
- `retry_max_attempts = 3`. Delay before attempt *n*: `min(retry_base_sec * 2^(n-1), retry_max_delay_sec)` with +/-20% jitter (base 60s, cap 600s → ~60s, 120s, 240s).
- A task whose `retry_count >= retry_max_attempts` is terminal-failed and escalated.

### Orphan / Stall Detection
- A `processing/` task is stalled when `now - claimed_at > deadline_for(effort)`, where
  `claimed_at` is read from `{task_id}.meta.json`. There is no mid-task heartbeat;
  `claimed_at + deadline` is the canonical liveness proxy. Stalled tasks enter crash
  recovery (increment retry_count, route to retry-pending/ or failed/).

### Escalation Routing
| Condition | Escalate to |
|-----------|-------------|
| Incoming starvation (no claim within breach) | Operator / human |
| Task stalled, retries remain | (auto) retry-pending/, same agent |
| Retries exhausted | Lead Engineer (unblock) |
| HANDBACK status: escalate | Model Engineer -> role promotion |

### Source of Truth
All thresholds live in `config/queue-sla.yaml`. Orchestrator and audit/monitoring skills
MUST read values from that file; they MUST NOT hardcode SLA constants. Changes are
governed by the `spec-management` skill.

---

## DELEGATE/HANDBACK Protocol

### DELEGATE Format (Orchestrator → Agent)

```yaml
---
handoff_type: DELEGATE
task_id: {unique_id}
role: Engineer | Senior Engineer | Lead Engineer | Quality Engineer | ...
model: claude-haiku-4.5 | claude-sonnet-5 | claude-opus-5 | claude-fable-5
effort: low | medium | high | max
depth: {int, 0 at Orchestrator}
ancestry: [ordered ancestor task_ids from the root]
scope: "Clear one-sentence scope + explicit out-of-scope boundaries (>=15 words)"
context: [relevant files, error messages, root cause analysis]
success_criteria: [measurable criteria; tests must pass, coverage maintained, etc.]
plan: [required for Engineer; step-by-step concrete steps; include Red-Green TDD phases for code changes]
---
```

### HANDBACK Format (Agent → Orchestrator)

```yaml
---
handoff_type: HANDBACK
task_id: {matching_delegate_task_id}
status: success | failure | partial | blocked | escalate
# success  — all success_criteria met
# failure  — attempted but could not be completed
# partial  — some success_criteria met, work remains
# blocked  — cannot proceed; external dependency or decision required
# escalate — requires higher-tier agent or human intervention
output: "Summary of what was delivered (any value; key must be present)"
metrics:
  quality: {0.0-1.0}
  tokens: {non-negative integer}
  cost: {non-negative USD}
  duration_seconds: {non-negative}
---
```

**Optional extension fields** (loosely validated, forward-compatible):
`deliverables`, `tests`, `escalations`, `model_assessment` (haiku_suitable |
sonnet_would_be_better | opus_required), `confidence` (0.0-1.0), `retry_count`,
`model_used`, `effort_actual`, `children_created`, `children_results`, `flags`, `error`.

Canonical machine-readable schemas: [docs/specs/protocol-core-v1.0.yaml](specs/protocol-core-v1.0.yaml),
[docs/specs/delegate-schema.yaml](specs/delegate-schema.yaml),
[docs/specs/handback-schema.yaml](specs/handback-schema.yaml).

---

## Agent Autonomy Model

Agents operate in **reduced autonomy mode**: continue autonomously when additional work
is documented, pause when the current scope is complete and nothing further is queued.

**Core rule:** did the agent complete the assigned DELEGATE and meet all
`success_criteria`? If additional todos exist in `TODO.md` (marked `- [ ]`), continue to
the next one and update `TODO.md` as work progresses. If the scope is complete and
`TODO.md` has no pending items, pause: state what was completed, what (if anything)
remains, and "Pausing here. Ready for next task or input." Always pause when scope
boundaries are unclear rather than assuming more work exists.

`TODO.md` (repository root) is the canonical, sole source of truth for outstanding work —
no SQL tables, spreadsheets, or session-workspace substitutes.

This does not change ORCHESTRATOR-FIRST: agents still only receive work via DELEGATE and
only return HANDBACKs; they never invoke each other directly or bypass the queue. Reduced
autonomy governs *when* an agent stops working within its current task, not *how* work
enters the system.

---

## Task Orchestration: Parallelization & Decision Protocol

All agents default to the reduced autonomy pattern specified in
`src/AGENTS.md` (Direct Sub-Agent Spawn Execution Model / Pause Condition): **maximize throughput by parallelizing
all independent tasks; pause only for genuine decisions, never for task sequencing.**

| Type | Definition | Agent action |
|------|-----------|--------------|
| **Task sequencing** | Ordering/prioritisation of independent items | Always autonomous — never ask the user |
| **Genuine decision** | Irreversible architectural or technology choice | Always pause — present shorthand and wait |

When a genuine decision must be presented, use numbered-option shorthand (`1a. Option
one`, `1b. Option two`, ...); the user responds with the letter(s) (e.g. `1b`, or `1a,
2c` for multiple concurrent decisions). See the SKILL.md for the full pattern and the
Python classification API.

---

## SKILLS: Role-Specific Execution Details

Complements `src/AGENTS.md` (who, when, routing) — this section is the compact per-role
workflow reference; see `src/AGENTS.md`'s Role Definitions for full escalation examples.

| Role | Workflow | Escalation trigger |
|------|----------|---------------------|
| **Engineer** | Read DELEGATE → follow plan steps in order → Red-Green TDD → `make verify` before HANDBACK | Architectural conflict or missing context → `status: blocked` |
| **Senior Engineer** | Explore 2-3 approaches → write detailed plan with rationale → HANDBACK with plan, not code (planning); reproduce → trace → file:line root cause → suggest fixes (diagnosis) | Cross-service/architectural/security impact → `status: blocked` |
| **Lead Engineer** | Code review checklist: tests pass, lint clean, coverage ≥85%, no secrets/panics/scope-creep; verdict PASS/FAIL with specific feedback; unblock stuck tasks | N/A — top of the review escalation chain below Principal |
| **Quality Engineer** | Tier 1 checks (tests, lint, secrets, scope match) → `model_assessment` (haiku_suitable / sonnet_would_be_better / opus_required) with confidence | Feeds Model Engineer for routing optimization |
| **Principal Engineer** | Map dependencies → identify contracts → design approach (breaking vs. compatible vs. versioned) → propose rollout | Reserved for true cross-repo/cross-service problems |
| **Security Engineer** | Scan for vulnerabilities, dependency risk, access-control gaps; findings by severity (CRITICAL/HIGH/MEDIUM/LOW); defensive-scope only (see LOCKED model section) | Offensive-scope request → reject + escalate to user |
| **Model Engineer** | Analyze completed-task feedback (~10-100 samples); rank models for next similar task (Rank 1 = highest confidence, Rank 2 = exploratory, Rank 3 = fallback) | Recommendations only — never delegates |
| **Orchestrator** | Route via the decision tree above → dispatch by direct sub-agent spawn → read HANDBACK from tool result → apply Model Engineer's Rank 1 recommendation for similar tasks | Ambiguous scope → escalate to human |

---

## Constraints & Mandatory Rules

**Planning & Escalation**
- Engineer MUST NOT receive a task without a pre-written `plan` in the DELEGATE — no
  exceptions. Unclear scope → `status: blocked`; Orchestrator escalates to Senior Engineer
  to write the plan.
- Engineer unable to execute the plan → `status: blocked`; Orchestrator escalates to
  Senior Engineer. Blocked tasks and rejections escalate automatically per the routing
  decision tree.

**Role-Specific Rules**
- Security Engineer invoked ONLY for security-scoped tasks.
- Quality Engineer provides `model_assessment` in every HANDBACK (for Model Engineer).
- Lead Engineer/Senior Engineer unblock or redirect Engineer when a task is blocked.

**Handoff Protocol** — all agent-to-agent work transfer uses structured DELEGATE/HANDBACK
blocks (see format above): compact context transfer, machine-readable tracking, metrics
per task.

**Unattended Mode** — no interactive prompts; agents make in-scope decisions without
human approval; only pause for a merge conflict, a post-push CI failure, or a discovered
out-of-scope issue; human reviews post-completion.

**No External Tools** — no external Python scripts, Makefile targets, or shell scripts
own orchestration, queue management, or metrics; 100% agent-based via DELEGATE/HANDBACK
(see ORCHESTRATOR-FIRST EXECUTION MODEL above for the full, authoritative statement of
this constraint).

---

## Effort Levels & Token Budget

| Level | Cost | Use Case | Expected Output |
|-------|------|----------|-----------------|
| **Low** | Minimal | Code cleanup, lint fixes, simple PRs | Minimal explanation, direct changes, no exploration |
| **Medium** | Moderate | Bugs with clear root cause, standard features, security fixes | Balanced: explain what changed, why, test verification |
| **High** | Standard | Complex bugs, architectural changes, security hardening | Deep reasoning, multiple approaches considered, thorough testing |
| **Max** | Unconstrained | CI failures with unclear root cause, major refactors, advanced analysis | Full exploration and validation, no cost/time constraints |

---

## Model Fallback & Defensive-Scope Notes

Context for the LOCKED section below (not itself LOCKED): Principal Engineer defaults
unconditionally to `claude-opus-5`; fallback to `claude-opus-4.8` only on opus-5
unavailability (documented in HANDBACK `model_assessment`) — never a cost-driven
downgrade. Security Engineer defaults unconditionally to `claude-fable-5` for its
highest-capability reasoning on threat modeling and vulnerability assessment; fallback to
`claude-opus-5` only on fable-5 unavailability. Fable-5 is approved **exclusively for
defensive security analysis** — vulnerability assessment, threat modelling of existing
systems, compliance review, audit-finding triage. It is never approved for exploit
development, offensive research, adversarial/jailbreak work, or destructive-capability
tasks, on any model — the Orchestrator MUST reject and escalate to the user rather than
route such a request to any model. Platform-level safeguard pauses (`stop_reason:
refusal`) are hard stops agents MUST NOT rephrase, fragment, or retry around; they are
recorded passively via HANDBACK `safeguard_events` and escalated, never re-routed.

---

## Model Naming & Harness Compatibility (LOCKED SPEC)

This section documents the approved AI model names and their official sources. Model naming is **CRITICAL** for harness compatibility and MUST NOT be changed without updating all validators, tests, and this specification.

### Official Model Names (AUTHORITATIVE)

**Source:** [Anthropic Claude API Documentation](https://docs.anthropic.com/claude/docs/models-overview)

Canonical (source) model IDs use a **dot** in the two-part version
(`claude-<tier>-<major>.<minor>`). Each harness transforms this at render time
(see the Harness-Specific Model Format table below):

| Model | Canonical (source) ID | Context Window | Max Output | Use Case |
|-------|-----------------------|-----------------|------------|----------|
| **Claude Haiku 4.5** | `claude-haiku-4.5` | 200K | 64K | Fast, low-cost; Engineer |
| **Claude Sonnet 5** | `claude-sonnet-5` | 1M | 128K | Balanced; Orchestrator, Senior Engineer, Lead Engineer, Quality Engineer, Model Engineer. Same $3/$15 per MTok as Sonnet 4.6, but ~30% more tokens for the same text. Single-part version — no transformation in any harness. |
| **Claude Opus 5** | `claude-opus-5` | 1M | 128K | High capability; Principal Engineer. Single-part version — no transformation in any harness. |
| **Claude Fable 5** | `claude-fable-5` | 1M | 128K | Highest-capability tier; Security Engineer (unconditional default). Most expensive model in the roster ($10/$50 per MTok, 2x Opus 5) — a capability upgrade, never a cost saving. Single-part version — identical in every harness, no transformation. |
| **Claude Sonnet 4.6** | `claude-sonnet-4.6` | 1M | 128K | Still locked/approved; no longer assigned to a role |
| **Claude Opus 4.6** | `claude-opus-4.6` | 1M | 64K | Still locked/approved; no longer assigned to a role |
| **Claude Opus 4.7** | `claude-opus-4.7` | 1M | 128K | Still locked/approved; no longer assigned to a role |
| **Claude Opus 4.8** | `claude-opus-4.8` | 1M | 128K | Emergency fallback tier. **Fallback for `security_engineer`** — used only if fable-5 is unavailable. |

**CRITICAL RULE — canonical IDs:** the two-part version uses a **dot**
(`claude-opus-4.8`), never an underscore or uppercase. The fully-hyphenated form
(`claude-opus-4-8`) is **not** a source ID — it is the OpenCode / Anthropic-API
render target produced by the dot→hyphen transformation below. A single-part
version (`claude-fable-5`) has no dot to transform and is byte-identical in every
harness.

### Harness-Specific Model Format

Each harness transforms the canonical ID for its runtime. Official sources: the
[Anthropic Claude API](https://docs.anthropic.com/claude/docs/models-overview)
and GitHub's [Copilot Supported Models](https://docs.github.com/en/copilot/reference/ai-models/supported-models).

| Harness | Canonical ID | Rendered Format | Transformation |
|---------|--------------|-----------------|----------------|
| **Claude (Claude Code)** | `claude-opus-5` | `opus` (tier alias) or full ID | Tier alias where the runtime accepts it; else no transformation (single-part) |
| **Copilot CLI** | `claude-opus-5` | `claude-opus-5` | None (single-part) |
| **OpenCode** | `claude-opus-5` | `anthropic/claude-opus-5` | `anthropic/` prefix (single-part, no dot→hyphen) |
| **Pi (pi.dev)** | `claude-opus-5` | `claude-opus-5` | No transformation (single-part) |

### Model Assignment by Agent Role

As of 2026-08-11:

- **Orchestrator:** `claude-sonnet-5` (routing)
- **Engineer:** `claude-haiku-4.5` (fast, pre-planned tasks)
- **Senior Engineer:** `claude-sonnet-5` (complex coding, unscoped work)
- **Lead Engineer:** `claude-sonnet-5` (code review, architectural guidance)
- **Quality Engineer:** `claude-sonnet-5` (quality gates, verification)
- **Model Engineer:** `claude-sonnet-5` (metrics analysis, recommendations)
- **Principal Engineer:** `claude-opus-5` (cross-service architecture)
- **Security Engineer:** `claude-fable-5` (unconditional; highest capability for threat modeling, vulnerability analysis).
  `ModelResolver.resolve('security_engineer')` unconditionally returns `claude-fable-5`.
  Defensive-scope enforcement is applied by the C5 offensive-scope gate in `DelegateValidator`,
  not by model routing. Fallback to `claude-opus-5` if fable-5 is unavailable (documented in HANDBACK).

### Model Governance: Locking & Switching

**Philosophy — positive enforcement.** Models are locked by *explicit strategic choice*,
not by forbidding patterns — "these are the approved models" rather than a rejection
blocklist. Users *can* request changes through the process below; every change is
auditable.

**Single source of truth — `.githooks/LOCKED_MODELS.sh`.** Contains `LOCKED_MODELS` (the
canonical approved list), `AGENT_MODEL_ASSIGNMENTS` (which agent uses which model), and
validation/display helpers. All hooks and validators source this file to stay consistent.

**Model Switch Process:** Request (agent, requested model, reason, cost/quality-delta
impact) → Evaluation (budget impact, task-profile fit, consistency, timeline) → Decision
(✅ Approved → implement; ⏸️ Deferred → revisit; ❌ Denied → documented reason) →
Implementation (update `LOCKED_MODELS` + `AGENT_MODEL_ASSIGNMENTS` in
`.githooks/LOCKED_MODELS.sh`, PR with rationale/cost impact, merge so pre-commit enforces
the new lock; keep `src/config/models.yaml`, if present, and this section in sync).

### Validation & Enforcement

**Mandatory checks (all must pass):** source files (`src/agents/*.md` `model:` fields use
hyphen format `claude-{family}-{version-with-hyphens}`, validated by
`renderer/validate_agents.py`'s `KNOWN_MODELS`, which rejects dotted forms like
`claude-opus-4.7`); documentation (`src/AGENTS.md`'s roster matches source agent files
exactly, pre-commit enforced); rendered output (`dist/{copilot,claude,opencode,pi}/agents/*`
all use hyphen format). Dot-format regressions are caught by the pre-commit hook and CI
(`test_model_naming_compliance.py`); Quality Engineer review is a further mandatory step.
To add/update an approved model: verify the official source, update this section and
`KNOWN_MODELS`, update `src/AGENTS.md`, run `make test`, commit citing the source.

---

## Repository Structure

```
agentic-engineers/
├── src/
│   ├── AGENTS.md                  # canonical roster, routing, execution model
│   ├── SKILLS.md                  # canonical skill roster & role workflows
│   ├── TODO.md.template
│   ├── agents/                    # 8 role definitions: *-agent.md
│   └── skills/                    # 8 surviving skills (each a SKILL.md dir):
│       orchestrator, queue-management, queue-query, protocol-validator,
│       spec-validator, spec-management, skill-improvement-feedback,
│       codex-agent-cleanup
├── docs/                          # SPEC.md (this file), PROTOCOL.md, QUEUE-PROTOCOL.md,
│                                   # specs/, spec-proposals/, design/, decisions/, guides/
├── renderer/                      # build-time render/install pipeline (scripts/, lib/)
├── scripts/                       # advisory/compliance tooling (see COMPLETE SCRIPT INVENTORY)
├── tests/                         # test suite
└── config/                        # FRAMEWORK-MANIFEST.yaml + orchestration/deployment/token_budget YAMLs
```

`src/AGENTS.md` and `src/SKILLS.md` are canonical; `docs/AGENTS.md` and `docs/SKILLS.md`
are thin pointers into `src/`. See [RENDERING.md](RENDERING.md) for how `src/` is rendered
into `dist/<harness>/` and installed to each harness's home directory.

---

## References

- **`src/AGENTS.md`** — canonical agent roster, routing decision tree, recursion limits, tools-frontmatter permission model; **`src/SKILLS.md`** — canonical skill roster and role workflows
- **[QUEUE-PROTOCOL.md](QUEUE-PROTOCOL.md)** — queue mechanics, DELEGATE/HANDBACK storage; **[PROTOCOL.md](PROTOCOL.md)** — validation, scoring, escalation reference
- **[RENDERING.md](RENDERING.md)** — render/install pipeline
- **[ONBOARDING.md](ONBOARDING.md)**, **[CORE-PROTOCOL-QUICKSTART.md](CORE-PROTOCOL-QUICKSTART.md)** — developer/agent onboarding

---

## Update Log

- **2026-05-02:** Phase 5.10 specification published. Documented ORCHESTRATOR-FIRST EXECUTION MODEL, removed deprecated external scripts and cron jobs, added span capture and artifact indexing requirements (span capture/indexing since removed — see 2026-08-11 entry).
- **2026-05-16:** Added SDLC Enforcement Hooks section documenting the three git hooks (pre-commit, commit-msg, pre-push), installation, and bypass procedures.
- **2026-05-17:** Added Phase 3 Token Visibility & Budget Checking section (removed — see 2026-08-11 entry; the CLI tooling it documented no longer exists).
- **2026-05-25:** Added Model Naming & Harness Compatibility section. Documents approved model names per official Anthropic/GitHub/pi.dev sources, validates hyphen format across all harnesses, adds no-regression tests and enforcement procedures.
- **2026-06-08:** Reconciled queue path contradictions throughout early sections. Canonical path is `~/.agentic-engineers/{harness}/{session-id}/queue/` per the locked section. Locked section unchanged (it is the authoritative source).
- **2026-06-11:** Reversed the canonical queue path order to `{harness}/{session-id}` (was `{session-id}/{harness}`) in the locked Queue Architecture section. Also fixed the self-contradicting model-naming CRITICAL RULE and corrected the stale harness-render table.
- **2026-06-12:** [SPEC-2026-001 — principal-engineer, approved by security-engineer] Consolidated CU-5: migrated model-governance content (positive-enforcement philosophy, `.githooks/LOCKED_MODELS.sh` single source of truth, and the Model Switch Process) from the deprecated root `SPEC.md` into the Model Naming & Harness Compatibility section; root `SPEC.md` reduced to a pointer at `docs/SPEC.md`. No behavioural change.
- **2026-06-13:** [SPEC-2026-002 — lead-engineer] Fixed residuals from the 2026-06-11 queue-path reversal (CU-4): four spots still presented the old `{session-id}/{harness}` order as current. All now show the canonical `~/.agentic-engineers/{harness}/{session-id}/queue/`. Legacy *source* paths in the migration table intentionally unchanged (they document deprecated paths).
- **2026-06-13:** [SPEC-2026-003 — principal-engineer, approved by security-engineer] Replaced a stale `AutomationController` reference (removed in the 2026-05-17 daemon-removal refactor) with a description of harness-initiated idle-loop polling as the then-current mechanism. Superseded by SPEC-2026-004 below.
- **2026-08-09:** [SPEC-2026-004 — principal-engineer, approved by security-engineer + lead-engineer] Execution Model redesign: replaced queue-polling dispatch (never functional — a 2026-08-09 sweep of 16 live session partitions found zero tasks ever traversed the queue that way) with direct sub-agent spawn as the canonical ORCHESTRATOR-FIRST mechanism. Queue paths (LOCKED section) unchanged; the queue's role narrows to durable inbox + audit substrate. Governance-only; no code changed by the proposal itself.
- **2026-08-11:** [SPEC-2026-005 — lead-engineer, framework slimdown WP-4] Consolidated rewrite, 2,035 → ~650 lines. LOCKED sections carried over near-verbatim with exactly two sanctioned edits: (a) Queue Architecture & Paths — "MUST initialize queue polling ONLY from" → "MUST read and write queue records ONLY from" (path unchanged); (b) Model Naming & Harness Compatibility — Orchestrator's assigned model changed from `claude-haiku-4.5` to `claude-sonnet-5` (commit 2b6e268). Deleted sections describing subsystems removed elsewhere in this slimdown: Phase 5.10 Span Capture & Indexing, Observability & Monitoring, Model Selection Architecture (opus-variant facts folded into a short non-LOCKED context note ahead of the LOCKED model section), Phase 3 Token Visibility, Optimization Feedback Loop, Agent Implementations, the Option-1a Dual-Layer Orchestrator Architecture and pre-direct-spawn Queue-Based Delegation Mechanics sections, Legacy Tiers, Next Steps (Phase 6), a duplicated vestigial tail, and a duplicate second SDLC-hooks section. Rewrote Repository Structure as an accurate ~20-line tree and COMPLETE SCRIPT INVENTORY from the actual surviving `scripts/` + `renderer/scripts/`. Authorizes the interim permissive floor in `renderer/scripts/check_test_regression.py` for the duration of the slimdown (WP-5 re-baselines from measured actuals). See `docs/spec-proposals/SPEC-2026-005.yaml`.

---

**Document Status:** Specification current, post-slimdown.
**Maintenance:** Update when agent roles, models, routing rules, or SKILLS change — via the `spec-management` skill.
