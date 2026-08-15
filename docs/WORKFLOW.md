---
name: SDLC Workflow with Enforcement Points
description: Complete lifecycle from user request to production, with enforcement gates at each stage
version: 1.0
updated: 2026-08-13
status: Production Ready
---

# SDLC Workflow with Enforcement Points

**Scope:** Complete SDLC lifecycle from user request through production deployment
**Status:** Production Ready — all enforcement gates implemented and tested
**Roster, DELEGATE/HANDBACK schema, routing rules, role definitions:** see `src/AGENTS.md` — not repeated here.

---

## Executive Summary

The agentic-engineers SDLC enforces quality and compliance at **7 critical gates**:

1. **User Request Gate** — Scope validation
2. **Orchestrator Gate** — Routing decision
3. **DELEGATE Gate** — Task structure validation
4. **Agent Execution Gate** — Quality baseline
5. **HANDBACK Gate** — Result validation
6. **Pre-Commit Gate** — SPEC compliance, secrets, format
7. **Pre-Push Gate** — Final quality verification

Each gate has clear decision rules, a defined failure path, and an escalation path (escalation
targets follow each role's "Escalates to" in `src/AGENTS.md` Role Definitions).

---

## Gate Flow

| # | Gate | Trigger | Key Check | Pass → | Fail → |
|---|------|---------|-----------|--------|--------|
| 1 | User Request | Task described | Scope bounded, success measurable, context sufficient | Orchestrator | Ask for clarification |
| 2 | Orchestrator Routing | Gate 1 passed | AGENTS.md routing tree applied; agent/model/effort selected | DELEGATE built | Escalate to human |
| 3 | DELEGATE Validation | DELEGATE constructed | Required fields present & valid (AGENTS.md DELEGATE Block Format) | Agent spawned | Fix and resubmit |
| 4 | Agent Execution | Agent spawned | Plan executed, tests run, quality baseline met | HANDBACK returned | `blocked`/`failure` → rework or escalate |
| 5 | HANDBACK Validation | HANDBACK returned | Quality assessed by convention (see Gate 5 below) | Merge / Lead review / Rework / Escalate | — |
| 6 | Pre-Commit | `git commit` | `.githooks/pre-commit` checks | Commit created | Commit blocked |
| 7 | Pre-Push | `git push` | `.githooks/pre-push` checks | Push proceeds | Push blocked |

**Merge to main** (final step, not a numbered gate): requires PR approval by Lead Engineer or
above, a completed Quality Engineer review, Gates 6–7 both passed, and green CI. On merge,
metrics are recorded and fed to the Model Engineer.

---

## Gate Details

### Gate 1: User Request

**Checklist:** scope clear and bounded (not "improve everything") · success criteria measurable
(not "make it better") · context provided (files, errors, background) · rough effort estimate ·
no blocking external dependencies.

**On failure:** ask for scope/criteria/context; do not proceed to Gate 2 until clear.
**Output:** Task ID (`YYYY-MM-DD-kebab-case`), ready for Orchestrator routing.

### Gate 2: Orchestrator Routing

Applies the routing decision tree in `src/AGENTS.md` § Delegation Model & Routing Rules — not
repeated here. **On failure:** unclear routing escalates to a human; a wrong effort estimate is
adjusted and re-routed. **Output:** a DELEGATE block per the canonical schema in `src/AGENTS.md`.

### Gate 3: DELEGATE Validation

Validates the DELEGATE against the required-fields table in `src/AGENTS.md` § Handover Packet
Protocol (`task_id`, `handoff_type`, `agent`, `scope` ≥15 words, `plan`, `success_criteria`,
`context`, valid YAML, no secrets). **On failure:** reject and return to the spawning agent for a
fix and resubmit; persistent issues escalate to Senior Engineer. **Output:** DELEGATE dispatched
as the sub-agent spawn prompt — the session transcript is the audit record (no separate queue
write).

### Gate 4: Agent Execution

**Process:** read & validate the DELEGATE → execute the plan step-by-step → run
tests/verification → measure quality → capture metrics (tokens, duration, quality, confidence).

**Quality baseline:** all tests passing · code coverage maintained (≥85% for critical code) · no
regressions · confidence ≥80%.

**On failure:** failing tests are fixed and re-run; a dropped coverage gets new tests; a blocked
agent reports `status: blocked`; scope creep is documented in the HANDBACK.
**Output:** a HANDBACK block per the canonical schema in `src/AGENTS.md`.

### Gate 5: HANDBACK Validation

Validates the HANDBACK against the required-fields schema, and reviews the result by convention:

**Quality assessment (by convention, not by automated formula):**
1. Agent self-reports `metrics.quality` (0.0–1.0)
2. Quality Engineer MAY spawn after the HANDBACK to verify `success_criteria` against actual
   delivered work, run lint/test/build, and adjust `metrics.quality` if the self-report was
   over- or under-optimistic
3. Routing follows the agent's `status` field:
   - `success` → done, merge
   - `partial` → new DELEGATE for remainder
   - `blocked` or `escalate` → surface to Orchestrator for further action

**On failure:** an invalid HANDBACK is rejected back to the agent for a fix and resubmit.
**Output:** HANDBACK returned in-context as the spawn call's result; metrics recorded for Model
Engineer.

### Gate 6: Pre-Commit

**Trigger:** `git commit`. Enforced by `.githooks/pre-commit` (staged files only, fast):

1. Syntax validation — Python `py_compile`, `bash -n`, optional shellcheck
2. Secrets detection — API keys, AWS keys, literal-valued sensitive env vars
3. File permissions — no executable bits on `.md`/`.yaml`/`.txt`/`.json`/`.jsonc`

Plus: SPEC constraints (no external scripts/cron in `orchestration/`), agent frontmatter
consistency (model/effort match `src/AGENTS.md`), YAML/JSON well-formedness, `opencode.jsonc`
schema validation, bypass-marker detection (warning only), source file integrity (no orphaned
bytecode, no missing test sources), LOCKED model naming compliance, and DELEGATE/HANDBACK
protocol validation.

**Decision:** errors block the commit; warnings are non-blocking.
**Bypass (emergency only, must be documented):** `SKIP_HOOKS=1 git commit` (skips everything) or
`BYPASS_HOOK_VALIDATION=true git commit` (skips only the frontmatter/opencode/DELEGATE checks).

### Gate 7: Pre-Push

**Trigger:** `git push`. Enforced by `.githooks/pre-push`: warns on push to `main`/`master`;
validates agent YAML frontmatter (`src/agents/*.md`) and workflow YAML
(`.github/workflows/*.yml`); checks documentation presence (`SPEC.md`, `AGENTS.md`,
`README.md`); checks SPEC architectural compliance; verifies `.agents_verification_sha`
integrity against `src/AGENTS.md`; and guards against embedded credentials in `~/.gitconfig`.

Deliberately does **not** re-run the full test suite or a render pass — `ci.yml` already does
both, as the real blocking gate, within minutes of the push.

**Decision:** errors block the push; warnings are non-blocking.
**Bypass (emergency only, must be documented):** `SKIP_HOOKS=1 git push`.

---

## Role Responsibilities by Gate

Condensed pointer table — full duties, boundaries, and escalation targets are in `src/AGENTS.md`
§ Role Definitions.

| Gate(s) | Role | Responsibility here |
|---|---|---|
| 1 | User | Provide bounded scope, measurable criteria, context |
| 2, 5 | Orchestrator | Apply routing tree; score and route each HANDBACK; re-delegate on rework/escalate |
| 4 | Agent (Engineer, Senior Engineer, etc.) | Execute the plan, run tests, self-score honestly, report blockers |
| 5 | Quality Engineer | Validate HANDBACK, verify deliverables against criteria, score, feed Model Engineer |
| 5 (0.7–0.79) | Lead Engineer | Manual review; approve, conditionally approve, or reject |
| 6, 7 | Developer | Keep commits SPEC/secret/format clean; keep pushes tested, documented, protocol-compliant |

---

## Metrics Collected

By convention (not auto-collected by the harness), these metrics are tracked where they matter:

| Gate | Metrics (convention) |
|---|---|
| 2 | `routing_decision`, `effort_level`, `model_assigned`, `tokens_estimate` |
| 4 | `tokens_used`, `duration_seconds`, `tests_passed`/`tests_failed`, `code_coverage`, `quality`, `confidence` |
| 5 | `quality` (self-reported, optionally QE-adjusted), `routing_decision`, `rework_count` |

---

## Update Log

- **2026-08-13:** Structural condensation (810 → 191 lines). Deduplicated against `src/AGENTS.md`
  (roster, DELEGATE/HANDBACK schema, routing rules, role definitions — replaced with one-line
  cross-references); collapsed the redundant box-diagram, "Decision Trees by Gate", and
  "Escalation Paths" sections (each restated content already covered by the Gate Details and
  Gate Flow table) into a single Gate Flow table; condensed Role Responsibilities and Metrics
  Collected into compact tables; re-verified the Gate 6/7 checklists against the current
  `.githooks/pre-commit` and `.githooks/pre-push` (dropped a stale `flake8` reference; the hook
  never ran it). No gate structure, decision rule, or scoring formula changed.
- **2026-08-13 (earlier):** Aligned with direct-spawn DELEGATE/HANDBACK model: removed artifact
  file references, updated field names (role→agent, estimated_tokens→tokens_estimate),
  standardized the HANDBACK metrics block (quality/tokens/cost/duration_seconds).
- **2026-05-16:** Initial comprehensive workflow documentation with 7 gates, decision trees,
  escalation paths, and metrics collection.
