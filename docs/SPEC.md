---
name: Agentic Engineers Implementation Specification
description: Current state of the agent orchestration system and operational constraints
version: 2.0
updated: 2026-08-13
phase: Post-slimdown (SPEC-2026-005), queue removed (SPEC-2026-009)
status: Current
type: specification
---

# Agentic Engineers Implementation Specification

**Last Updated:** 2026-08-13
**Constraint:** No external scripts/tools own orchestration — all runtime work flows through AGENTS via DELEGATE/HANDBACK; Python is advisory only (see below).

---

## Executive Summary

The Agentic Engineers system routes all work through specialized AI agents — Orchestrator,
Engineer, Senior Engineer, Quality Engineer, Lead Engineer, Principal Engineer, Security
Engineer, Model Engineer — via the DELEGATE/HANDBACK protocol. The Orchestrator is the
single entry point: it builds a DELEGATE and dispatches it by directly spawning a
sub-agent with the DELEGATE as the prompt, then reads the HANDBACK from that spawn's
result, synchronously and in-context. The harness session transcript itself (every
DELEGATE as a spawn prompt, every HANDBACK as that spawn's result) is the durable
audit record.

---

## ORCHESTRATOR-FIRST EXECUTION MODEL (MANDATORY)

**This is a hard constraint. All work MUST flow through the Orchestrator. No exceptions.**

The Orchestrator is the single entry point and single router. Dispatch happens by
directly spawning a sub-agent with the DELEGATE as its prompt — control flow lives in the
Orchestrator's own agent context, not in external tooling or background processes.

1. **No Direct Agent Invocation.** Engineers MUST NOT invoke specialist agents directly
   or hand-write DELEGATE blocks and pass them out of band. All work is routed by the
   Orchestrator, which owns the decision tree.
2. **Dispatch is a Direct Sub-Agent Spawn.** The Orchestrator builds a DELEGATE per the
   DELEGATE/HANDBACK Protocol section below, spawns a sub-agent with it as the prompt via
   the harness's sub-agent tool, and reads the returned HANDBACK directly from the tool
   result. Dispatch and collection are synchronous with respect to the Orchestrator's own
   reasoning — the DELEGATE goes in as the spawn prompt, the HANDBACK comes back as the
   spawn result, all in a single agent turn.
3. **Control Flow Lives in Agent Context; Python is Advisory Only.** Routing, escalation,
   retries, and the DELEGATE → spawn → HANDBACK → gate lifecycle are executed by agent
   reasoning. Python modules MAY validate a DELEGATE against a schema, score a HANDBACK,
   compute cost/token rollups, or recommend a model — as pure functions returning data to
   the agent. They MUST NOT own the control loop, decide what runs next, or spawn/supervise
   agents. If removing a helper would halt the system rather than degrade its advice, it
   is control flow and is prohibited here.
4. **The Harness Session Transcript is the Durable Audit Record; There Is No Filesystem
   Queue.** Dispatch and results are exchanged entirely in-context: the spawning agent
   passes a DELEGATE as a sub-agent spawn's prompt and reads the HANDBACK back as that
   same spawn call's result. That spawn/result pair, as it appears in the harness's own
   session transcript, *is* the durable record — nothing is separately written to or
   read from disk to make a DELEGATE or HANDBACK "count." There is no inbox, no
   session-partitioned directory tree, and no `enqueue()` step. A task submitted while no
   Orchestrator context is live has no durable holding area under this model; it is
   handed to the Orchestrator directly the next time one is invoked.
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
   and token/cost fields where applicable. An optional `resolves_task_id` MAY link a
   remediation event chain to the failed/blocked task it addresses. Agents append; they
   MUST NOT rewrite, reorder, truncate, or delete prior lines — corrections are new events,
   never edits. No metric may be reported that is not grounded in a logged event.
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

**Why this constraint exists:** direct sub-agent spawn achieves a complete audit trail
(every spawn/handback is a real logged event), correct routing (the decision tree is
applied by the agent that owns it), and accurate cost tracking (metrics derive from logged
events, not constants). Rendering infrastructure (harness distribution, build-time skill
rendering) may use subprocess for deterministic build operations — this constraint is
about orchestration/agent runtime code, not build infrastructure.

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
and never participate in runtime orchestration. See
[RENDERING.md](RENDERING.md) for the full pipeline and per-file descriptions.

### COMPLIANT: Root `scripts/` — Advisory & Compliance Tooling

Each of these is a pure, callable advisory helper (clause 3) or a pre-commit/CI gate —
none owns dispatch, scheduling, or supervision:

| Script | Purpose |
|--------|---------|
| `format_skill_report.py` | Formats skill test/validation output |
| `run_skill_tests.py` | Test runner for skill scripts (invoked by CI/make, not autonomous) |
| `validate-spec-constraints.py` | Pre-commit SPEC constraint checker |
| `get_version.py` | Reads/reports framework version |
| `validate_opencode_config.py` | OpenCode config generation gate |
| `entropy_detector.py` | Entropy-based credential/secret detector (security gate) |
| `check-gitconfig-no-tokens.sh` | Pre-commit check for tokens leaking into gitconfig |
| `handback_rollup.py` | Advisory per-role HANDBACK cost/quality rollup (never gates); `--events` mode reads the clause-7 audit JSONL |
| `check_model_registry.py` | Advisory models.dev drift check for LOCKED_MODELS.sh (never gates) |
| `audit_append.py` | Deterministic append helper for the clause-7 audit JSONL — agents invoke it to format/validate/append one event; never gates, never owns dispatch |

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

The routing decision tree (security-scoped → Security Engineer; cross-service
architecture → Principal Engineer; unscoped complex coding → Senior Engineer;
review/quality verification → Lead Engineer or Quality Engineer; well-scoped
with a plan → Engineer; otherwise → escalate to a human) is canonical in
[`src/AGENTS.md`](../src/AGENTS.md) § Delegation Model & Routing Rules — not
duplicated here.

---

## DELEGATE/HANDBACK Protocol

The DELEGATE and HANDBACK message formats — required/optional fields, examples,
and the canonical machine-readable schema
([docs/specs/protocol-core-v1.0.yaml](specs/protocol-core-v1.0.yaml)) — are
defined in [`docs/PROTOCOL.md`](PROTOCOL.md) § 2 (Canonical Schema) and
[`src/AGENTS.md`](../src/AGENTS.md) § Handover Packet Protocol — not duplicated
here.

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

Effort tiers are comparable only *within* the same model tier — a higher effort level on
a lower-capability model does not outrank a lower effort level on a higher-capability
model (e.g. Lead Engineer's `claude-sonnet-5`/high is not "more effort" than Security
Engineer's `claude-fable-5`/max in any cross-model sense; the two axes are independent).

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
| **Codex** | *(not carried forward)* | `gpt-5.4-mini` (Orchestrator/Engineer) or `gpt-5.5` (all other roles) | Not a canonical-ID transform — Codex substitutes its own GPT-family model per agent-role tier (`CODEX_MODEL_BY_ROLE` in `renderer/scripts/render-codex.py`); it never emits a `claude-*` ID |

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
exactly, pre-commit enforced); rendered output (`dist/{copilot,claude,opencode}/agents/*`
all use hyphen format — Codex is excluded from this check because it renders its own
GPT-family models, not a `claude-*` ID, per the Harness-Specific Model Format table above).
Dot-format regressions are caught by the pre-commit hook and CI
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
│   └── skills/                    # 6 surviving skills (each a SKILL.md dir):
│       orchestrator, protocol-validator, spec-validator, spec-management,
│       skill-improvement-feedback, codex-agent-cleanup
├── docs/                          # SPEC.md (this file), PROTOCOL.md,
│                                   # specs/, decisions/, guides/, INDEX.md
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
- **[PROTOCOL.md](PROTOCOL.md)** — DELEGATE/HANDBACK validation, scoring, escalation reference
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
- **2026-08-11:** [SPEC-2026-005 — lead-engineer, framework slimdown WP-4] Consolidated rewrite, 2,035 → ~650 lines. LOCKED sections carried over near-verbatim with exactly two sanctioned edits: (a) Queue Architecture & Paths — "MUST initialize queue polling ONLY from" → "MUST read and write queue records ONLY from" (path unchanged); (b) Model Naming & Harness Compatibility — Orchestrator's assigned model changed from `claude-haiku-4.5` to `claude-sonnet-5` (commit 2b6e268). Deleted sections describing subsystems removed elsewhere in this slimdown: Phase 5.10 Span Capture & Indexing, Observability & Monitoring, Model Selection Architecture (opus-variant facts folded into a short non-LOCKED context note ahead of the LOCKED model section), Phase 3 Token Visibility, Optimization Feedback Loop, Agent Implementations, the Option-1a Dual-Layer Orchestrator Architecture and pre-direct-spawn Queue-Based Delegation Mechanics sections, Legacy Tiers, Next Steps (Phase 6), a duplicated vestigial tail, and a duplicate second SDLC-hooks section. Rewrote Repository Structure as an accurate ~20-line tree and COMPLETE SCRIPT INVENTORY from the actual surviving `scripts/` + `renderer/scripts/`. Authorizes the interim permissive floor in `renderer/scripts/check_test_regression.py` for the duration of the slimdown (WP-5 re-baselines from measured actuals).
- **2026-08-12:** [SPEC-2026-006 — lead-engineer, framework slimdown follow-up C] Corrected the harness enumeration in the LOCKED "Queue Architecture & Paths" section, which still listed `pi` (the pi harness was dropped elsewhere in the 2026-08-11 slimdown; `renderer/scripts/render-pi*.py` and its dist output no longer exist) and omitted `codex` (a supported render target since commit 1361afa, 2026-06-17 — added after this section's 2026-05-26 lock date, so its earlier absence here was accurate at the time, not an oversight). Four surgical string replacements only — the harness-directory tree comment, the "Supported Harnesses" bullet list, the subdirectory-coverage sentence, and the harness-renderers compliance sentence — each swapping the literal `pi` for `codex` in place, preserving position, count ("four harnesses"), and every other word. Path template, ordering rules, state-dir list, and the Unsupported Legacy Paths migration table are byte-identical to SPEC-2026-005. The sibling LOCKED "Model Naming & Harness Compatibility" section (which also still references `pi`/`pi.dev`) is explicitly out of scope for this proposal.
- **2026-08-12:** [SPEC-2026-007 — lead-engineer] Corrected the remaining `pi`/`pi.dev` references in the LOCKED "Model Naming & Harness Compatibility" section, left explicitly out of scope by SPEC-2026-006. The Harness-Specific Model Format table's `Pi (pi.dev)` row is replaced with a `Codex` row — not a like-for-like swap, since Codex does not carry the canonical Claude ID forward at all: it substitutes its own GPT-family model per agent-role tier (`gpt-5.4-mini` for Orchestrator/Engineer, `gpt-5.5` for all other roles) via `CODEX_MODEL_BY_ROLE` in `renderer/scripts/render-codex.py`, confirmed against rendered `dist/codex/agents/*.toml`. The Validation & Enforcement hyphen-format check's harness list drops `pi` and does NOT add `codex` in its place (`tests/test_model_naming_compliance.py` checks only `dist/{copilot,claude,opencode}/`; Codex output was never `claude-*` IDs to check), with a one-clause note explaining the exclusion. Model list, naming invariant, `.githooks/LOCKED_MODELS.sh` single-source-of-truth clause, and Model Switch Process are byte-identical.
- **2026-08-13:** [SPEC-2026-008 — lead-engineer] Corrected the LOCKED "Queue Architecture & Paths" section's Enforcement Rules, which still mandated implementation details of code deleted by the 2026-08-11 slimdown — a `QueueManager` class and a standalone `queue-isolation` skill, neither of which exists anymore (path isolation is inlined into `src/skills/queue-management/scripts/queue_ops.py`). The two bullets are restated implementation-neutrally, preserving the same invariant (queue writes MUST be confined to the canonical `~/.agentic-engineers/{harness}/{session-id}/queue/` root; a write that cannot be validated as isolated MUST fail immediately, never fall back) while naming the surviving enforcement point instead of the deleted class/skill names. Verified `queue_ops.py`'s `get_queue_path()`/`_validate_path_component()` actually raise before any write on an invalid `session_id`/`harness` — the invariant is enforced by the surviving code, not weakened to match it. The other two bullets in the same rule, and the rest of the LOCKED section, are byte-identical.
- **2026-08-13:** [SPEC-2026-009 — lead-engineer, authorized_by: user-directive
  (task-2026-08-13-queue-removal-spec-docs, ancestry:
  [task-2026-08-13-queue-removal-root])] **Removed the filesystem queue entirely.** The
  repo owner directed, in the DELEGATE that authorized this proposal, that dispatch is
  direct sub-agent spawn only and the durable audit record is the harness session
  transcript — no `~/.agentic-engineers/{harness}/{session-id}/queue/` directory tree,
  no `enqueue()`, no `incoming/`/`processing/`/`done/`/`failed/` state machine. This
  removes the LOCKED "Queue Architecture & Paths" section outright (previously
  carried over byte-identical, with only surgical corrections, through
  SPEC-2026-005/006/008) and the "Queue SLA & Governance" section that depended on it
  (its `config/queue-sla.yaml` source-of-truth file never existed in the tree — a
  pre-existing drift this deletion also resolves). ORCHESTRATOR-FIRST clause 4 is
  rewritten from "The Queue is a Durable Inbox and Audit Substrate" to state the new
  ground truth plainly. Repository Structure's skill list drops `queue-management` and
  `queue-query` (deleted in the same effort, src/side) — 8 surviving skills become 6.
  References and the script/doc cross-link list drop `docs/QUEUE-PROTOCOL.md` (deleted).
  This is the first proposal in this class to remove rather than restate a LOCKED
  section; ordinary spec-management authorization (principal/security peer review) was
  bypassed on the explicit, recorded authority of the repo owner rather than a
  Lead-Engineer self-authorization precedent like SPEC-2026-006/007/008.
  **Correction (same day, same authorization):** the concurrent `src/**`/`tests/**`
  code package for this same user-directed queue removal has since been committed and
  deleted `scripts/check_protocol_compliance.py` (the CI gate that ran the
  protocol-validator over queue-directory YAML files), its `.github/workflows/ci.yml`
  step, and its two test files — confirmed via `ls scripts/` returning no such file.
  This section's COMPLETE SCRIPT INVENTORY table is updated to drop that row; no other
  content in this Update Log entry or elsewhere in this proposal's scope changes. Folded
  into this entry rather than a new SPEC-2026-010 proposal, per the same
  authorized_by: user-directive covering the whole queue-removal effort.
- **2026-08-13:** [lead-engineer, task-2026-08-13-polish-p8-opencode-safe,
  authorized_by: user-directive (polish wave-1, ancestry:
  [task-2026-08-13-queue-removal-root, task-2026-08-13-polish-plan-wave1])]
  Deleted `scripts/opencode-safe.sh` (105 lines) — zero callers repo-wide (re-verified:
  no references in `.githooks/`, `Makefile`, `src/`, `tests/`; the one hit outside this
  section was a stale historical mention in `scripts/validate_opencode_config.py`'s
  module docstring, not an executable call site). This section's COMPLETE SCRIPT
  INVENTORY table is updated to drop that row; `check-gitconfig-no-tokens.sh` (still
  load-bearing via pre-push and `ci.yml`) and every other row are unchanged. Per the
  spec-management "3a. Self-Authorized Narrow Follow-Up" pattern; this Update Log entry
  is the record (no separate proposal file).
- **2026-08-13:** [lead-engineer, task-2026-08-13-r3-wp11-spec-floor, authorized_by:
  user-directive (round-3 planning, ancestry: [task-2026-08-13-queue-removal-root,
  task-2026-08-13-plan-round3-value])] Deduplicated the "Routing Decision Tree" and
  "DELEGATE/HANDBACK Protocol" sections, which restated content already canonical in
  `src/AGENTS.md` (§ Delegation Model & Routing Rules, § Handover Packet Protocol) and
  `docs/PROTOCOL.md` (§ 2 Canonical Schema) — replaced with one-line normative
  cross-references, the same pattern `docs/WORKFLOW.md`'s 2026-08-13 condensation
  already uses. Verified no test or CI gate parses these sections' literal content
  (`grep -rn SPEC tests/ .githooks/ .github/workflows/`); the strings the
  security-gate workflow and pre-push hook do assert on (`# Agentic Engineers
  Implementation Specification`, `ORCHESTRATOR-FIRST EXECUTION MODEL`, the
  frontmatter `version:` field, and the top-level `# ` heading) are outside the
  edited range and unchanged; the LOCKED "Model Naming & Harness Compatibility"
  section is untouched. Companion package to the same task's regression-floor
  governance review (see `renderer/scripts/check_test_regression.py` and
  `docs/REGRESSION-GATE-POLICY.md`, updated in the same task but not a SPEC.md
  change). Per the spec-management "3a. Self-Authorized Narrow Follow-Up" pattern;
  this Update Log entry is the record (no separate proposal file).
- **2026-08-14:** [orchestrator commit-curation, tasks
  task-2026-08-14-backlog4-10-cost-governance + task-2026-08-14-backlog7-modelsdev-advisory,
  authorized_by: user-directive (backlog round)] Registered two new advisory scripts in
  the COMPLETE SCRIPT INVENTORY table: `handback_rollup.py` (per-role HANDBACK
  cost/quality rollup) and `check_model_registry.py` (models.dev drift check for
  `.githooks/LOCKED_MODELS.sh`). Both advisory-only per the ORCHESTRATOR-FIRST
  "Python is advisory" clause — they report, never gate. Table-rows-plus-this-entry
  only; no other SPEC content changed; LOCKED section untouched.
- **2026-08-14:** [senior-engineer, task-2026-08-14-implement-audit-jsonl,
  authorized_by: user-directive (backlog round, ancestry:
  [task-2026-08-14-backlog-round])] Implemented ORCHESTRATOR-FIRST clause 7 (the
  append-only audit JSONL), which the clause already specified but nothing in the
  tree wrote to. Added `scripts/audit_append.py` — the deterministic,
  stdlib-only append helper (docs/SPEC.md clause 3: advisory Python) agents invoke
  to format/validate/append one clause-7 event; registered in the COMPLETE SCRIPT
  INVENTORY table above. Wired the append duty into `src/AGENTS.md` (new § Audit
  Events under Direct Sub-Agent Spawn Execution Model, recomputed
  `.agents_verification_sha` accordingly), the Orchestrator and the four
  spawn-capable role definitions (`src/agents/{orchestrator,senior-engineer,
  lead-engineer,principal-engineer,security-engineer}-agent.md`), and
  `src/skills/orchestrator/SKILL.md`'s Audit Trail section. Reconciled
  transcript-vs-JSONL language in `docs/ENTRYPOINT.md`, `docs/PROTOCOL.md` (new §7a
  Audit Events (JSONL), Glossary entry, §3.1 clarification), and
  `docs/CONTRIBUTING/README.md`'s historical note — the transcript remains what
  makes a DELEGATE/HANDBACK count (clause 4, unchanged, still literally true); the
  JSONL is an additive, queryable metrics/event log, never a substitute. Gave
  `scripts/handback_rollup.py` a `--events <path...>` mode (`parse_events()`,
  `validate_event_record()`) that aggregates `handback_received` events into the
  same per-role table `--json`/table output already produces from HANDBACK YAML,
  mixable with positional YAML sources in one invocation. Added
  `tests/test_audit_append.py` (32 cases) and extended
  `tests/test_handback_rollup.py` (+9 cases for `--events`). Wire format
  (`docs/specs/protocol-core-v1.0.yaml`) and `renderer/scripts/claude-delegate-guard.py`
  untouched; both security-gate strings, the `version:` field, and the LOCKED
  "Model Naming & Harness Compatibility" section untouched.
- **2026-08-14:** [lead-engineer, task-2026-08-14-lead-engineer-opus48-medium,
  authorized_by: user-directive (2026-08-14), ancestry:
  [task-2026-08-14-backlog-round]] Model Switch: Lead Engineer moves from
  `claude-sonnet-5`/high to `claude-opus-4.8`/medium, per the Model Switch Process
  in this same LOCKED section (`.githooks/LOCKED_MODELS.sh` updated first;
  `claude-opus-4.8` was already present in `LOCKED_MODELS`, so only
  `AGENT_MODEL_ASSIGNMENTS` changed). Three surgical edits to this LOCKED section:
  (a) the Official Model Names table drops "Lead Engineer" from the Claude Sonnet 5
  row's use-case list; (b) the Claude Opus 4.8 row is reworded from a pure
  "Emergency fallback tier" to name Lead Engineer as its primary assignment,
  preserving the existing Security Engineer fallback clause verbatim; (c) the
  Model Assignment by Agent Role list's Lead Engineer line changes model only,
  parenthetical use-case unchanged. All other rows, the Harness-Specific Model
  Format table, Model Governance, and Validation & Enforcement text are
  byte-identical. Companion edits outside this section (`src/AGENTS.md` roster row,
  `src/agents/lead-engineer-agent.md` frontmatter + body, `config/FRAMEWORK-MANIFEST.yaml`)
  land in the same task. Per the spec-management "3a. Self-Authorized Narrow
  Follow-Up" pattern; this Update Log entry is the record (no separate proposal
  file).
- **2026-08-14:** [lead-engineer, task-2026-08-14-lead-engineer-sonnet5-max,
  authorized_by: user-directive (2026-08-14), ancestry:
  [task-2026-08-14-backlog-round]] Correction (supersedes the immediately
  preceding entry, which is not deleted per the immutable-audit-trail rule):
  the user revised the directive — Lead Engineer reverts from
  `claude-opus-4.8`/medium back to `claude-sonnet-5`, with effort raised to
  `max` (the top of the low\|medium\|high\|max ladder, the existing Security
  Engineer/fable-5 precedent) rather than restoring the original `high`. Three
  surgical edits to this LOCKED section, exactly reversing the prior entry's
  (a)/(b)/(c) plus the effort change: (a) the Official Model Names table's
  Claude Sonnet 5 row use-case list regains "Lead Engineer"; (b) the Claude
  Opus 4.8 row is restored verbatim to its pre-2026-08-14 pure
  "Emergency fallback tier" / `security_engineer`-only wording; (c) the Model
  Assignment by Agent Role list's Lead Engineer line reverts to
  `claude-sonnet-5`, parenthetical use-case unchanged. All other rows, the
  Harness-Specific Model Format table, Model Governance, and Validation &
  Enforcement text are byte-identical. Verified `max` is already a
  first-class effort value throughout the render/validation pipeline via the
  existing Security Engineer precedent — no code changes were needed in
  `renderer/scripts/render-codex.py` (`REASONING_BY_EFFORT["max"] == "high"`),
  `renderer/scripts/render-opencode.sh` (`effort_to_variant`/
  `effort_to_temperature` both already match `high|max`), or
  `tests/test_src_integrity.py` (`valid_effort` already includes `"max"`);
  `renderer/validate_agents.py` does not parse effort at all (frontmatter
  never carries it — the roster table is the sole effort source). Companion
  edits outside this section (`src/AGENTS.md` roster row,
  `src/agents/lead-engineer-agent.md` frontmatter + body,
  `config/FRAMEWORK-MANIFEST.yaml`, `tests/test_agents_table_parity.py`
  fixture) land in the same task. Per the spec-management "3a.
  Self-Authorized Narrow Follow-Up" pattern; this Update Log entry is the
  record (no separate proposal file).
- **2026-08-14:** [senior-engineer, task-2026-08-14-lead-high-plus-verify-duty,
  authorized_by: user-directive (2026-08-14), ancestry:
  [task-2026-08-14-backlog-round]] Effort correction, per the accepted
  model-engineer review (task-2026-08-14-roster-mix-review): Lead Engineer's
  effort lands at `high`, not `max` — the model stays `claude-sonnet-5`, so
  this touches only the Core Architecture roster table (line ~206, not the
  LOCKED "Model Naming & Harness Compatibility" section) plus the
  non-LOCKED Effort Levels section, which gains a one-line note that effort
  tiers are comparable only within the same model tier (a higher effort on a
  lower-tier model does not outrank a higher-tier model — e.g. Lead
  Engineer's sonnet-5/high vs. Security Engineer's fable-5/max). The
  review also found that the Role Definitions prose for Lead Engineer
  (`src/AGENTS.md` ~line 182) already read `high` and was never updated to
  `max` in the immediately preceding entry above — this correction brings
  the roster table into agreement with that prose rather than the reverse.
  This finalizes the 2026-08-14 Lead Engineer sequence: `claude-sonnet-5`/
  `high`, per the model-engineer recommendation. Companion edits outside
  this document (`src/AGENTS.md` roster row, `src/agents/lead-engineer-agent.md`
  effort line, `config/FRAMEWORK-MANIFEST.yaml`, `setup/copilot-instructions.md`
  heading, `tests/test_agents_table_parity.py` fixture) land in the same task,
  alongside an unrelated companion change (mandatory Engineer-HANDBACK
  independent-verification duty, codified in `src/AGENTS.md`,
  `src/skills/orchestrator/SKILL.md`, and `src/agents/quality-engineer-agent.md`
  — process-only, no SPEC.md content). Per the spec-management "3a.
  Self-Authorized Narrow Follow-Up" pattern; this Update Log entry is the
  record (no separate proposal file).
- **2026-08-14:** [engineer, task-2026-08-14-delegation-audit-skill,
  authorized_by: user-directive (2026-08-14-backlog-round), ancestry:
  [task-2026-08-14-backlog-round]] Added seventh skill (audit-trail-review
  meta-skill) to the active skills roster. Skill is prose-only (SKILL.md +
  __init__.py only, no scripts/tests directory). Primary input: on-disk
  orchestration ledger at `~/.agentic-engineers/{harness}/{session-id}/audit/events-*.jsonl`
  (clause 7 audit trail, written by scripts/audit_append.py). Core procedure:
  ledger reconciliation — parse events, index by task_id, identify orphaned
  delegations (no handback_received), unfinalized acceptances (no gate_result),
  dropped work (status blocked/failure/escalate with no follow-up), unvisited
  refusals/limit-breaches, and working-tree orphans (artifacts tied to
  unfinalized task_ids). Single-session constraint: operates ONLY on current
  harness + session (never enumerates sibling sessions) to prevent conflating
  unrelated work. Secondary input (campaign mode): branch diffs for the 5 audit
  mandates (consistency, unfinished work, claim-vs-truth, privacy, quality).
  Companion tool: `scripts/handback_rollup.py --events` provides metrics view
  over the same ledger file. Updates: (a) `src/skills/audit-trail-review/`
  (was `delegation-audit/` before rename) created with ledger-reconciliation-focused
  SKILL.md; (b) `renderer/validate_skills.py` ACTIVE_SKILLS list updated
  (6 → 7, name: audit-trail-review); (c) `src/SKILLS.md` registry row added,
  status updated to "7 active skills", directory structure note clarified;
  (d) `tests/test_install_correctness.py` skill count assertion: 6 → 7;
  (e) `tests/test_render_harness_coverage.py` skill count test updated (6 → 7);
  (f) `docs/LANDSCAPE.md` bonus-task item 2 updated (6 → 7);
  (g) `src/skills/README.md` updated (heading "6 skills" → "7 skills", new skill
  table row); (h) this Update Log entry. No changes to AGENTS.md, agent
  frontmatter, LOCKED sections, or wire protocol (`docs/specs/protocol-core-v1.0.yaml`).
  Full validation: `python3 renderer/validate_skills.py` → 7/7 PASS;
  `make render-all` → all 4 harnesses valid; `pytest tests/ -q` → baseline count
  updated honestly. Per the engineer self-authorized narrow-follow-up pattern;
  this Update Log entry is the record (no separate proposal file).
- **2026-08-14:** [engineer, task-2026-08-14-atr-findings-fixes,
  authorized_by: user-directive (2026-08-14-backlog-round), ancestry:
  [task-2026-08-14-backlog-round, task-2026-08-14-atr-first-run]] Fixed
  audit-trail-review skill findings from maiden run: (a) SKILL.md v1.0.0 → 1.0.1
  incorporating 5 QE critiques: Dropped Work disambiguation procedure (check
  resolves_task_id, then heuristic delegate_issued within 30 min, then git-log);
  Orphan detection keys off delegate_issued alone (not subagent_spawned);
  Invocation section relabeled as illustrative-only; Report schema adds sixth
  category LEDGER-INTEGRITY; Operating Rule 4 clarifies 30-min threshold is
  measured against auditor's wall clock, not ledger mtime; maiden-run false-positive
  example added (final-consistency-audit remediated 57ms later by different task_id);
  (b) audit_append.py adds optional `--resolves-task-id <task_id>` argument,
  validated as plausible task-id string when present, omitted otherwise;
  required fields and enum unchanged; +3 tests cover present/absent/malformed cases;
  (c) handback_rollup.py compat verified: validate_event_record() tolerates new
  field (no whitelist change needed); (d) docs: SPEC.md clause 7 + one-liner in
  Update Log (this entry); PROTOCOL.md §7a + one-liner. All changes: SKILL.md,
  audit_append.py, tests/test_audit_append.py, docs/SPEC.md, docs/PROTOCOL.md.
  Verification: pytest tests/test_audit_append.py tests/test_handback_rollup.py -q green;
  pytest -q green (baseline +3); python3 renderer/validate_skills.py 7/7;
  dry-run demo: audit_append --resolves-task-id shown. No commits.

---

**Document Status:** Specification current, post-slimdown.
**Maintenance:** Update when agent roles, models, routing rules, or SKILLS change — via the `spec-management` skill.
