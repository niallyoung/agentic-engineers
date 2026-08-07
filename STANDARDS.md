# Engineering Standards — agentic-engineers

> **Status:** Active · **Last Updated:** 2026-05-30 · **Owner:** Lead/Security Engineers
>
> This document captures the **actual** engineering standards enforced in this
> repository. It is descriptive of how the framework already works — grounded in
> `AGENTS.md`, `CONTRIBUTING.md`, the git hooks (`.githooks/`), `src/config/`,
> and the test suite — not aspirational. Where a standard is machine-enforced, the
> enforcing hook or target is named so it can be verified.

---

## Table of Contents

1. [Core Principles](#1-core-principles)
2. [TDD Workflow (RED → GREEN → REFACTOR)](#2-tdd-workflow-red--green--refactor)
3. [DELEGATE / HANDBACK Protocol](#3-delegate--handback-protocol)
4. [Model & Effort Assignment Policy](#4-model--effort-assignment-policy)
5. [Security Practices](#5-security-practices)
6. [Python Style & Conventions](#6-python-style--conventions)
7. [Commit Message Conventions](#7-commit-message-conventions)
8. [Branch & Worktree Workflow](#8-branch--worktree-workflow)
9. [Skill & Agent Authoring Standards](#9-skill--agent-authoring-standards)
10. [Quality Gates & Thresholds](#10-quality-gates--thresholds)
11. [Reference Index](#11-reference-index)

---

## 1. Core Principles

These are drawn directly from `src/AGENTS.md` and govern every contribution.

- **Queue-first** — All work enters the DELEGATE/HANDBACK queue. There are no
  ad-hoc, agent-to-agent calls.
- **Reduced autonomy** — Agents pause when the queue is empty; they do **not**
  invent new work.
- **Start cheap, escalate deliberately** — Route to the cheapest capable model
  and effort tier; upgrade only when a quality gate fails or work is blocked.
- **Root-cause fixes only** — Never disable tests, add workarounds, or mask
  failures. Address the actual problem.
- **Cold-context agents** — Every DELEGATE is self-contained; the receiving
  agent cannot rely on session state. Cite exact `file:line` references.
- **Parallel by default** — Independent tasks fan out simultaneously.
- **Token-conscious** — Summarise (tables, not prose), suppress verbose output,
  trust tool confirmations, grep before reading.
- **Framework-first** — Extend the framework using its own meta-skills
  (`agent-creator`, `skill-creator`), not by hand-editing user-config directories.

---

## 2. TDD Workflow (RED → GREEN → REFACTOR)

All code changes follow Test-Driven Development. This is `Implementation Rule #1`
in `TODO.md` and is enforced through coverage and pre-push gates.

1. **RED** — Write a failing test that encodes the acceptance criteria first.
   New behaviour starts as a failing test, never as untested code.
2. **GREEN** — Write the minimum implementation to make the test pass. Fix the
   root cause; do not weaken the test to make it pass.
3. **REFACTOR** — Clean up structure and naming with the test suite green. No
   behavioural change during refactor.

**Rules**

- Every new module/feature ships with tests. CI and `CONTRIBUTING.md` enforce
  **≥ 85 % coverage per changed module**.
- Zero regressions: the full suite must pass before commit/push.
- Keep test fixtures in sync with code. Use the `test-sync-validator` skill to
  detect drift (e.g. when `LOCKED_MODELS`, router logic, or cost tiers change).
- Tests live under `tests/`; run with `make test` (coverage) or
  `pytest tests/ -q`.

```bash
make test            # full suite with coverage (term-missing)
make test-concurrent # race-condition guard (required before push)
```

---

## 3. DELEGATE / HANDBACK Protocol

All work is delegated via a **DELEGATE** block and returned via a **HANDBACK**
block. The canonical specification lives in `src/AGENTS.md`; this is a summary of
the enforced expectations.

### 3.1 DELEGATE — required fields

`task_id`, `type` (`DELEGATE`), `role` (lowercase-hyphenated), `model`
(explicit — no implicit defaults), `context.description`, `context.repo`,
`context.branch`, `context.commit`, `acceptance_criteria`, `escalation_triggers`,
`repro`, `skill_refs`.

Strongly recommended: `effort` (`low|medium|high|max`), `priority`,
`requirements`, `constraints`, `token_budget`, `estimated_cost`.

`task_id` uses the format `YYYY-MM-DD-kebab-case` (validated by the `commit-msg`
hook when referenced in commits).

### 3.2 HANDBACK — required fields

`task_id`, `type` (`HANDBACK`), `role`, `status`
(`COMPLETE | PARTIAL | BLOCKED | ESCALATE`), `summary`, `changes`,
`acceptance_verified`, `metrics`. File-creating background agents **must** include
the resulting `commit_sha` (see §5 and `docs/BACKGROUND-AGENT-COMMIT-PROTOCOL.md`).

`metrics` carries: `tokens_used`, `tokens_estimated`, `efficiency_ratio`,
`model_used`, `duration_ms`, `quality_score` (0.0–1.0).

### 3.3 Protocol expectations

- **ACK first.** Every agent emits an ACK (`✅ [Role] ACK — [TASK-ID]`) as its
  first output before any work. Missing context → `⚠️ BLOCKED` ACK listing what
  is needed.
- **Model-mismatch guard.** If the running model differs from the DELEGATE
  `model:` field, stop and emit `❌ MODEL_MISMATCH`.
- **Completion footer.** Every agent ends with `MODEL_USED: <actual-model>`.
- **Escalation.** On hitting an escalation trigger, stop implementation and emit
  an `ESCALATION` packet (with `findings_so_far`) so the next tier starts with
  full context.
- **Canonical queue paths.** DELEGATE/HANDBACK files live under the canonical
  queue path; the `pre-push` hook rejects legacy/poisoned paths
  (`src/skills/_meta/queue-path-validator/`).
- **`spec_version`** links a HANDBACK to its DELEGATE for the audit trail; it must
  match between the two (Phase 1.5 FIX-2).

---

## 4. Model & Effort Assignment Policy

> **🔒 LOCKED — `src/config/models.yaml` is the single source of truth and MUST
> NOT be edited as part of normal work.** Model choices are a strategic decision,
> mirrored in `.githooks/LOCKED_MODELS.sh` and `src/config/MODEL_ASSIGNMENTS_LOCKED.md`,
> and enforced by the pre-commit hook.

### 4.1 Locked model set

Canonical format uses a **dot** version separator, `claude-{variant}-{major}.{minor}`.
Current-generation models carry a single-part version and so have no separator
at all (`claude-opus-5`). The rule is "never a hyphen as the version separator".

| Model | Used by |
|-------|---------|
| `claude-haiku-4.5` | Orchestrator, Engineer |
| `claude-sonnet-5` | Senior Engineer, Model Engineer, Lead Engineer, Quality Engineer |
| `claude-opus-5` | Principal Engineer |
| `claude-fable-5` | Security Engineer |
| `claude-opus-4.8` | Security Engineer resolver default; emergency fallback tier |

Rejected by the pre-commit hook: hyphenated versions (`claude-opus-4-7`),
unversioned (`claude-opus`), and non-Claude models (`gpt-4`). Per-harness
renderers transform the canonical dotted source into each harness's required
format (e.g. OpenCode uses hyphens, Claude Code uses short aliases) — the source
always stays dotted.

### 4.2 Cost tiers

```
Tier 1 — Cheap (haiku-4.5): Orchestrator + Engineer        → $0.03–0.05/task
Tier 2 — Medium (sonnet-5): Model Eng + QE + Lead + Senior → ~$0.12/task
Tier 3 — Premium (opus-5):  Principal                      → ~$0.18/task
Tier 3 — Premium (fable-5): Security                       → ~$0.36/task
```

### 4.3 Effort & thinking

- **Effort:** `low | medium | high | max`. `high` is the baseline; `max` adds
  extended thinking and ~+30 % tokens.
- **Thinking:** `yes | no`. Disabled is ~‑20 % cheaper; enable only when quality
  requires it.

### 4.4 Optimization policy (cost-first, quality-gated)

The Model Engineer walks the progression Haiku → Sonnet 4.5 → Sonnet 4.6 →
Opus 4.6 → Opus 4.8 and **picks the first combination that passes the quality
gate** (`min_quality = best_observed − 5 points`). Cost always wins among
combinations that pass.

**Allowed** Model Engineer recommendations: model up/down within the locked
progression, effort changes, thinking on/off. **Not allowed:** changing role
assignments, introducing models outside the progression, or violating the
quality gate. Any change to the locked set requires explicit Orchestrator
approval and a documented PR rationale.

---

## 5. Security Practices

Security is enforced both by routing rules and by git hooks.

- **Mandatory routing.** Any task touching auth, crypto, secrets, injection,
  PII, supply chain, or compliance routes to the **Security Engineer** — no
  exceptions (`src/AGENTS.md` routing rule #1).
- **Security-critical DELEGATE fields** (Phase 1.5 FIX-4): `security_scope`
  (`auth|crypto|pii|secrets|injection|supply_chain`), `approval_gate`
  (`lead_engineer|principal_engineer|security_engineer|cto`), and
  `audit_required`. The pre-push hook validates that a `security_scope` task
  carries an `approval_gate` and `audit_required`.
- **No secrets in git.** The `commit-msg` hook blocks messages containing
  `password|api_key|secret|token|private_key|...`. Never commit `.env`,
  `credentials.json`, or similar. Use environment variables / secret management.
- **No bytecode.** The pre-commit hook rejects any staged `.pyc`; a pytest plugin
  verifies tests load from `.py` source, not cache.
- **Agent-definition verification** (Phase 1.5 FIX-3). `.agents_verification_sha`
  pins the SHA-256 of `src/AGENTS.md`; the pre-push hook detects tampering and
  guards against model-downgrade attacks via `model_verification_sha`.
- **Hooks are not optional.** `SKIP_HOOKS` / `SKIP_COMMIT_MSG_HOOK` bypasses are
  for documented emergencies only and require a reason ≥ 10 chars in the commit
  message (see `docs/SECURITY-HOOKS.md`). **Do not bypass hooks to work around
  your own change.** If a hook fails for a reason unrelated to your change,
  capture the error and report it rather than bypassing.

---

## 6. Python Style & Conventions

Grounded in `conftest.py`, `pytest.ini`, `setup.py`, and the existing source.

- **Layout.** Source under `src/`; skills under `src/skills/{category}/`; tests
  under `tests/`. The package is installed editable via `setup.py`.
- **Test discovery** (`pytest.ini`): files `test_*.py`, classes `Test*`,
  functions `test_*`, `testpaths = tests`.
- **Naming.** `snake_case` for functions/variables/modules, `PascalCase` for
  classes, `UPPER_SNAKE` for constants. Skill/agent identifiers are
  `lowercase-hyphenated`.
- **Concurrency safety.** File writes that may be polled concurrently must be
  **atomic** — write to a `.tmp` sibling then `os.replace()`. Readers tolerate
  partially-written files (return `None`/retry rather than raise). This guards
  the documented TOCTOU race between HANDBACK pollers and writer threads
  (`CONTRIBUTING.md` → "Parallel & Concurrent Test Validation").
- **Error handling.** Prefer explicit, actionable errors with fix suggestions
  (cf. `EnforcementError` in `src/orchestration/decorators.py`); never fail
  silently.
- **Linting.** `make lint` covers Python, Shell, and YAML and must be clean
  before push.

---

## 7. Commit Message Conventions

Enforced by `.githooks/commit-msg` (Conventional Commits).

```
type(scope): subject
```

- **Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
  `chore`, `ci`, `build`, `revert`.
- **Scopes** (recommended): `agents`, `skills`, `renderer`, `src`, `tests`,
  `ci`, `deps` (e.g. `cost`, `evals` also appear in history).
- **Subject length:** 10–72 characters (hard-enforced).
- **Task ID:** include a `YYYY-MM-DD-kebab-case` task ID where applicable — the
  hook detects and acknowledges it (warns if absent).
- **No secrets** in the message (hook-blocked).
- **CHANGELOG** is automated from commit types; write descriptive subjects.

Examples (from `git log`):

```
feat(cost): implement multi-level CostBudget with enforcement
fix(cost): remove unused imports for code quality
test(EVALS-001): Add comprehensive test suite (32 tests, 85%+ coverage)
docs: add STANDARDS.md engineering standards (STANDARDS-002)
```

---

## 8. Branch & Worktree Workflow

- **Branches.** Create a feature branch per unit of work:
  `git checkout -b feature/<short-description>` (also `feat/<...>` in history).
  Never commit directly to `main`/`master`; the pre-push hook warns on protected
  branches and expects a completed Quality Engineer review before merge.
- **Isolated worktrees.** Parallel agents run in **isolated git worktrees** so
  concurrent runs cannot corrupt shared state. Do all work inside the assigned
  worktree path; never touch the main worktree or another agent's sandbox. For
  Python/pytest runs, scope `HOME` to a sandbox directory so the runtime can only
  write into the sandbox.
- **Verify before push.**

  ```bash
  make verify         # structure + agents + skills
  make test           # full suite with coverage
  make quality-gate   # lint + test + concurrent + verify + render validation
  ```

- **Push & review.** `git push -u origin <branch>`; CI enforces all standards.
  Open a PR for review — do not self-merge security or architecture changes.
- **Background agents must commit.** Files created by background agents must be
  explicitly committed (with the `commit_sha` reported in the HANDBACK), or they
  are lost (`docs/FILE-LOSS-PREVENTION.md`).

---

## 9. Skill & Agent Authoring Standards

Follow the [agentskills.io](https://agentskills.io/specification) spec and the
`skill-creator` / `agent-creator` meta-skills.

### 9.1 Skills

- **Location.** Authoritative source is `src/skills/{category}/{skill-name}/`.
  Never create skills directly in `~/.claude/`, `~/.copilot/`, or
  `~/.config/opencode/` — `make install` renders into those and will overwrite
  hand edits.
- **Structure.** `SKILL.md` (required) + optional `scripts/`, `references/`,
  `assets/`. Keep `SKILL.md` body under ~500 lines (progressive disclosure;
  push detail to `references/`).
- **Frontmatter.** Required `name` (lowercase + hyphens, ≤ 64 chars, matches the
  directory) and `description` (1–1024 chars, says *when/why* to use). Optional
  `license`, `compatibility`, `metadata` (`author`, `version`, `category`,
  `role`).
- **Categories.** `orchestration`, `monitoring`, `optimization`, `patterns`,
  `security`, `testing`, `shared`, `architecture`, `review`, `roles`.
- **Scripts.** Modular, one responsibility each, self-contained with clear error
  messages and help text.

### 9.2 Agents

- **Location.** `src/agents/*.md` with YAML frontmatter requiring at least
  `name` and `model` (validated by the pre-push hook).
- **Model.** Use a locked model in canonical dotted format (§4). The pre-commit
  hook rejects unlocked or mis-formatted models.
- **Render & test.** `make render-all` then `make test-models` (model-naming
  compliance). Renderers handle per-harness model transformations.

---

## 10. Quality Gates & Thresholds

The framework enforces a **3-layer quality-gate model** (DELEGATE structure →
routing quality → HANDBACK validation) plus the local/CI gates below.

### 10.1 `make quality-gate` (pre-push)

`quality-gate = lint + test + test-concurrent + verify + validate-renders`.

The `pre-push` hook additionally validates: agent YAML frontmatter, GitHub
Actions workflow YAML, documentation presence (`docs/SPEC.md`, `docs/AGENTS.md`,
`README.md`), DELEGATE/HANDBACK protocol compliance, canonical queue paths, agent
SHA verification, and the **concurrent-invocation race-condition guard** (a hard
failure if it trips).

### 10.2 Thresholds

| Gate | Threshold | Enforced by |
|------|-----------|-------------|
| Per-module test coverage | **≥ 85 %** | CI + `CONTRIBUTING.md` |
| Test pass rate | **100 % (zero regressions)** | `make test`, pre-push |
| Commit subject length | 10–72 chars | `commit-msg` hook |
| Conventional commit format | required | `commit-msg` hook |
| No `.pyc` staged | required | pre-commit hook |
| No secrets in commits | required | `commit-msg` hook |
| Model in locked set + dotted format | required | pre-commit hook |
| `security_scope` ⇒ `approval_gate` + `audit_required` | required | pre-push hook |
| HANDBACK `quality_score` | self-assessed 0.0–1.0; team target **≥ 0.85 (85/100)** | Quality Engineer |
| SPEC.md changes | via `spec-management` skill only | process |

### 10.3 SPEC.md protection

`SPEC.md` is excluded from doc-quality checks and may only be changed through the
`spec-management` skill's proposal → impact-analysis → approval → changelog
workflow. It is never edited ad-hoc.

---

## 11. Reference Index

| Topic | Source |
|-------|--------|
| Agent roster, DELEGATE/HANDBACK spec | `src/AGENTS.md` |
| Contributor setup & workflow | `CONTRIBUTING.md` (`docs/CONTRIBUTING/README.md`) |
| Locked model registry | `src/config/models.yaml` (🔒 LOCKED) |
| Locked model assignments & rationale | `src/config/MODEL_ASSIGNMENTS_LOCKED.md`, `.githooks/LOCKED_MODELS.sh`, `.githooks/LOCKED_MODELS_RATIONALE.md` |
| Git hooks (commit-msg / pre-commit / pre-push) | `.githooks/` |
| Architecture specification | `SPEC.md` / `docs/SPEC.md` |
| Skill authoring | `src/skills/skill-creator/SKILL.md` |
| Security hardening (Phase 1.5) | `PHASE-1.5-SECURITY-HARDENING.md` |
| Background-agent commit protocol | `docs/BACKGROUND-AGENT-COMMIT-PROTOCOL.md` |
| Hook bypass procedure | `docs/SECURITY-HOOKS.md` |
| Roadmap & implementation rules | `TODO.md` |

---

*This document reflects the standards as enforced on 2026-05-30. When a hook,
model lock, or threshold changes, update the corresponding row above so this
file stays accurate.*
