# Contributing to agentic-engineers

> **Philosophy:** Use agentic-engineers itself to improve agentic-engineers. Delegate changes to the framework's own agents and skills.

> **A note on paths.** This file is `docs/CONTRIBUTING/README.md`, and the repo-root
> `CONTRIBUTING.md` is a symlink to it — so the same bytes are rendered at two different
> depths and no single relative link can resolve from both. Cross-directory references are
> therefore written as plain backticked paths from the repo root (`src/AGENTS.md`), not as
> markdown links. Please keep that convention when editing.

---

## Quick Start

```bash
git clone https://github.com/niallyoung/agentic-engineers.git && cd agentic-engineers
make install && make verify && make test
```

You're ready to contribute.

### Python Version (Pinned: 3.11)

This project targets **Python 3.11**. The GitHub Actions workflows are the **source of truth** — every workflow uses `actions/setup-python` pinned to 3.11 (none of them use the Dockerfile), and `setup.py` requires `>=3.11`. A `.python-version` file pins 3.11 for pyenv/local tooling. The `Dockerfile` and `test-ci*` Makefile targets below are a local CI-parity mirror, not what CI itself runs.

To run the test suite under a local approximation of the CI Python version without installing 3.11 locally, use the container target:

```bash
make test-ci         # Run tests in the python:3.11 container (matches CI exactly)
make test-ci-force   # Strict mode: fails if any test fails
```

This avoids environment-specific failures caused by a mismatched local Python version.

---

## Contributor Setup Guide

### Automatic Setup (What Happens After Clone)

After `make install`, the framework automatically:

✅ **Git Hooks Installed**
- Pre-commit hook: Prevents bytecode (`.pyc`) from being staged
- Commit-msg hook: Validates conventional commit format (`feat(scope): message`)
- Pre-push hook: Runs concurrent tests to detect race conditions
- 📍 Location: `.githooks/` → configured via `git config core.hooksPath`
- ✅ **Automatic:** No manual action needed

✅ **Directory Structure Created**
- `~/.copilot/` — Copilot CLI agents + skills
- `~/.claude/` — Claude Code agents
- `~/.config/opencode/` — OpenCode agents + skills
- ✅ **Automatic:** Created by `make install-*` targets

✅ **Local Development Environment**
- Python virtual environment ready (via `setup.py`)
- All dependencies installed
- Pytest configured with coverage reporting
- ✅ **Automatic:** Done by `make install`

### What You Need to Do (Manual Steps)

1. **Clone & install:**
   ```bash
   git clone https://github.com/niallyoung/agentic-engineers.git
   cd agentic-engineers
   make install        # Installs to all 4 harnesses
   # Or: make install-opencode (if using OpenCode only)
   ```

2. **Create a branch for your work:**
   ```bash
   git checkout -b feature/your-feature
   ```

3. **Make your changes**:
    - New agent? Author a `src/agents/<name>-agent.md` directly, following the structure
      of an existing one (e.g. `src/agents/engineer-agent.md`), then register it in
      `src/AGENTS.md` and `config/FRAMEWORK-MANIFEST.yaml`.
    - New skill? Author a `src/skills/<category>/<name>/SKILL.md` directly, following the
      structure of an existing one (e.g. `spec-validator`), then register it in
      `src/SKILLS.md` and `config/FRAMEWORK-MANIFEST.yaml`. See "Creating New Skills" below.
    - Code changes? Delegate to the Orchestrator!

      Instead of editing files directly, use the delegation format. Here's an example:

     ```yaml
     ---
     handoff_type: DELEGATE
     task_id: 2026-05-29-add-postal-validation
     role: engineer
     model: claude-haiku-4.5
     effort: high
     scope: Add AU PostalCode validation rule to the address validator. PostalCode is optional but when present must be exactly 4 digits.
     context:
       - File: src/validation/postal.py
       - File: tests/test_postal.py
     plan:
       1. Add 4-digit AU postcode regex rule
       2. Add unit tests for valid and invalid cases
       3. Run make verify to confirm all tests pass
     success_criteria:
       - "PostalCode '2000' and '0800' pass validation"
       - "PostalCode 'ABC', '123', '12345' are rejected with a clear error message"
       - "make test passes with no failures"
     ---
     ```

     When delegating work:
     - Describe the goal or outcome in sufficient detail with descriptive language
     - Don't be too prescriptive about implementation details
     - Prefer generalized, flexible principles and positive reinforcement over inflexible rules
     - Provide the Orchestrator with a list of related tasks and outcomes end-to-end
     - Give enough context so the Orchestrator can plan and implement a decent solution

 4. **Verify locally before pushing:**
   ```bash
   make verify         # Full verification (structure + agents + skills)
   make test           # Run all tests with coverage
   make lint           # Lint Python, Shell, YAML
   make quality-gate   # Pre-push checks (all of the above)
   ```

5. **Push with conventional commits:**
   ```bash
   git commit -m "feat(skills): add cache invalidation"
   git push origin feature/your-feature
   ```
   CI will validate all standards automatically.

---

## Working with Single Harnesses

If you're only working with one harness (e.g., OpenCode development), use targeted make targets:

```bash
# Install OpenCode only
make install-opencode

# Render OpenCode only
make render-opencode

# Verify OpenCode specifically
make validate-opencode

# Uninstall OpenCode only
make uninstall-opencode
```

This speeds up iteration without installing all 4 harnesses.

---

## Framework-First Approach

New skills and agents follow this repo's skills-first, minimal-tooling philosophy:
author them directly.

- **New agent?** Create `src/agents/<name>-agent.md` following the structure of an
  existing agent (e.g. `src/agents/engineer-agent.md`), then register it in
  `src/AGENTS.md` + `config/FRAMEWORK-MANIFEST.yaml`. The glob-based renderer discovers
  it automatically — no manual per-harness wiring needed.
- **New skill?** Create `src/skills/<category>/<name>/SKILL.md` following the structure
  of an existing skill (e.g. `spec-validator`), then register it in `src/SKILLS.md` +
  `config/FRAMEWORK-MANIFEST.yaml`. The glob-based renderer discovers it automatically.
- **Code review?** Use the `Lead Engineer` agent for architectural guidance.
- **Complex planning?** Use the `Senior Engineer` agent to plan unscoped work.

All framework extensions run through the validation pipeline automatically. See `src/AGENTS.md` and `src/SKILLS.md` for the complete roster.

---

## Creating New Skills

**Important:** Skills are always created in the **framework source** (`src/skills/`),
never directly in a user config directory such as `~/.claude/skills/` — `make install`
regenerates those and will overwrite anything you put there by hand.

Skills live one directory deep: `src/skills/{skill-name}/SKILL.md`. There is no
`{category}/` level and no `references/` convention.

**The authoritative, worked instructions are `src/skills/README.md` § Adding a skill.**
Follow that section rather than duplicating its steps here; it is kept in sync with the
registry in `renderer/validate_skills.py` and `config/FRAMEWORK-MANIFEST.yaml`, both of
which must also list any new skill.


## Skill Naming Conventions

As of the **Phase 3 Skills Consolidation (2026-06-06)**, skills follow
consistent prefixes so related skills group together and are easy to discover.
**New skills must adopt the matching prefix for their domain:**

| Prefix | Domain | Existing members |
|--------|--------|------------------|
| `spec-*` | SPEC.md governance | spec-validator, spec-management |
| `protocol-*` | DELEGATE/HANDBACK schema validation | protocol-validator |
| `agent-*` / `skill-*` | Scaffolding and utilities | orchestrator, codex-agent-cleanup, skill-improvement-feedback |

All skills are part of the public skill catalog in `src/skills/`.

### Framework Slimdown (2026-08-11)

As part of SPEC-2026-005, the framework was consolidated to focus on core capabilities.
The surviving skill roster is documented in `src/SKILLS.md`. Deleted skills include:
queue-todo-sync, metrics-etl, tokenadvisor, agent-creator, consistency-checker,
cost-aggregation, cost-budgeting, doc-quality-monitor, file-sync, harness-integration-tracker,
local-model-runtime, model-selection, session-analyzer, testing, usage-tracking, and workflow-review.

**Follow-up (2026-08-13, SPEC-2026-009):** the filesystem queue itself was removed
(dispatch is direct sub-agent spawn only; the harness session transcript is the durable
audit record). `queue-management` and `queue-query` — the two skills that implemented
and exposed that queue — were deleted in the same effort.

---

## Skill Lifecycle

Every skill moves through the same four stages. The source tree is
authoritative; everything downstream is regenerated, never hand-edited.

```
1. CREATE            2. TEST                3. RENDER              4. DEPLOY
   ──────               ────                   ──────                 ──────
   src/skills/<name>/   src/skills/<name>/     make render-all        make install
     SKILL.md             tests/      ───►     → dist/claude/   ───►  → ~/.claude/skills/
     scripts/           tests/ (cross-skill)   → dist/copilot/        → ~/.copilot/skills/
     references/        make verify            → dist/opencode/       → ~/.config/opencode/skills/
     tests/             pytest tests/ -q       → (run via test harness)
```

1. **Create** — Author the skill in `src/skills/<name>/` with a `SKILL.md`
   (frontmatter), `scripts/`, optional `references/`, and `tests/`. Use the
   correct naming prefix (above). See [Creating New Skills](#creating-new-skills).
2. **Test** — Add skill-local tests under `src/skills/<name>/tests/`; add
   cross-skill behavior to the top-level `tests/`. **Test against rendered
   output (`dist/`), not your dev install** (`~/.claude/` may be empty in CI).
   Keep test-fixture skill counts in sync — see
   [Test Fixture Synchronization](#test-fixture-synchronization).
3. **Render** — `make render-all` regenerates `dist/<harness>/` with
   provider-specific transformations. The skill name must appear identically
   across all harnesses; see `docs/RENDERING.md`.
4. **Deploy** — `make install` renders to the four user config directories. A
   rename or merge is only "done" once it re-renders cleanly everywhere.

> Renames use `git mv` to preserve history, and a rename is incomplete until
> every reference (registries, docs, fixtures, imports) is updated. Verify with:
> `grep -rn "<old-name>" src/ docs/ config/ | grep -v archive` returning empty.

---

## Cost Tracking & Budget Monitoring

The framework tracks token spend per task and enforces budgets so agents stay
within cost targets.

- **Per-task budgets** — A `DELEGATE` block carries a token budget; the
  executing agent should stay within it and report actuals in its `HANDBACK`.
- **Budget enforcement, token limits, and historical usage** — the standalone
  budget/usage-tracking docs and the `cost-*` skills were removed in the 2026-08-11
  framework slimdown (SPEC-2026-005); the surviving skill roster is `src/SKILLS.md`.
  If you need this functionality, propose it via `spec-management` rather than
  reviving the deleted docs.
- **Model selection drives cost** — pick the cheapest model that meets the
  quality bar (see [Model Selection (Locked)](#model-selection-locked)); the
  `model-engineer` agent recommends cost-quality-optimal routing.

**Contributor guidance:** when adding a skill or agent, set a realistic token
budget in its examples, prefer lower-cost models where quality allows, and never
hard-code spend that bypasses budget enforcement.

---

## Making Changes

1. **Branch:** `git checkout -b feature/your-change`
2. **Use framework skills** to scaffold agents, skills, or designs
3. **Test locally:** `make verify` and `python3 -m pytest tests/ -q`
4. **Commit:** Use [conventional commits](https://www.conventionalcommits.org/) (e.g., `feat(skills): add X`, `fix(agents): correct Y`)
5. **Push & request review:** CI enforces all standards automatically

**Commit scopes:** `agents`, `skills`, `renderer`, `src`, `tests`, `ci`, `deps`

---

## Security: Credential Handling

**Use SSH for all git operations. Never embed credentials in git config or write them to disk in plaintext.**

SSH keys provide stronger cryptographic guarantees than tokens and eliminate credential leakage through git configuration.

| Scenario | Do this | Why |
| --- | --- | --- |
| Local development (recommended) | SSH key: `git clone git@github.com:...` | Cryptographically secure; no credentials in config |
| GitHub API via `gh` CLI | `gh auth login` with SSH or browser auth | `gh` uses SSH for git ops; tokens stored securely in credential helper |
| One-off HTTPS clone | `git clone --config <key>=<value> ...` (repo-local only) | Repo-local config is safer; never use `--global` |
| CI/CD pipelines | Pass `GH_TOKEN` / `GITHUB_TOKEN` via runner secrets | Temporary, scoped to job, rotated per environment |

**Rules:**
- No hardcoded secrets (`ghp_`, `gho_`, `ghs_`, `x-access-token`, `sk-`, `AKIA…`) in code, scripts, workflows, or config
- Credentials belong in environment variables or secret managers—never in committed or persistent config
- Never use `git config --global url.<url>.insteadOf` with embedded tokens; this persists credentials to disk permanently
- If a secret is ever exposed, rotate it immediately at <https://github.com/settings/tokens> or <https://github.com/settings/keys>

**Enforcement:** `scripts/check-gitconfig-no-tokens.sh` runs in the `pre-push` hook and prevents pushes if `~/.gitconfig` or `~/.git-credentials` contains embedded tokens. Run standalone anytime:

```bash
scripts/check-gitconfig-no-tokens.sh
```

---

## Working with Background Agents

When using background agents (e.g., Engineer, Senior Engineer) to create implementation files:

**Background agents MUST explicitly commit their files to git.** This ensures:
- ✅ Created files persist beyond the agent's session
- ✅ Tests aren't lost to bytecode caching
- ✅ HANDBACK includes proof of commitment (commit SHA)
- ✅ Orchestrator can validate files actually reached git

**Read:** `docs/BACKGROUND-AGENT-COMMIT-PROTOCOL.md` for the detailed protocol agents must follow.

---

## Preventing Orphaned Files

The framework automatically validates:

1. **Pre-commit hook** — Rejects any `.pyc` bytecode (never staged)
2. **Pytest plugin** — Verifies all tests come from `.py` source (not cache)
3. **CI/CD validation** — Checks no orphaned bytecode in commits
4. **HANDBACK schema** — Requires `commit_sha` for file-creating agents

**If you encounter issues with missing files:**
- Common cause: Agent didn't commit files before session ended
- Fix: Recreate files or manually commit

---

## Releases & Versioning

Versioning is automated. On a merge to `main`, the **Auto-Tag (Semantic Versioning)**
job in `.github/workflows/ci.yml` derives the next semantic version from the commit
messages, creates the tag, and publishes a GitHub Release. You do not tag by hand.

Write [conventional commits](https://www.conventionalcommits.org/) so the version bump
is derived correctly:

```bash
git commit -m "feat(skills): add cache invalidation"      # minor bump
git commit -m "fix(agents): resolve race condition"       # patch bump
git commit -m "docs: update installation guide"           # patch bump
```

There is **no `CHANGELOG.md`** in this repo — the generated GitHub Release notes are the
changelog, and no CI gate validates a changelog file.

---

## CI/CD Requirements

All contributions pass through a multi-gate CI pipeline defined in
`.github/workflows/ci.yml`. This section documents each gate, what it checks,
and how to satisfy it locally before pushing.

### Gates Overview

| Gate | Script | Failing Exit |
|------|--------|-------------|
| Credential scan | `git grep` token-signature scan over the tree + `scripts/check-gitconfig-no-tokens.sh` | Hard fail |
| Lint | `make lint` | Hard fail |
| **SKILL.md frontmatter + registry + compliance** | `renderer/validate_skills.py` | Hard fail on errors; warn on warnings |
| **Skill template conformance report** | `renderer/validate_skills.py --json` + `scripts/format_skill_report.py` | Non-failing (audit trail) |
| **Orphaned bytecode check** | Inline (folded in from the former `validate-sources.yml`) | Hard fail |
| Render agents + skills | `make render-*` | Hard fail |
| Test suite | `make test` | Hard fail |
| **Harness regression check** | `renderer/scripts/check_test_regression.py` | Hard fail |
| **Gate 5 (stub): AAIF `AGENTS.md` v1.0 conformance** | `goose agents-md validate` when present on `PATH` | Non-failing (skipped until AAIF ships v1.0 tooling) |
| Verify | `make verify` | Hard fail |

**Removed (2026-08-13 infra consolidation):** the standalone circular-import gate
(`scripts/detect_circular_imports.py` scanned `src/` for `src.*`-style intra-package
imports, but no code in this repo uses that import style — skills use `sys.path`-based
imports — so it always scanned 0 modules and could never fail); the token-cost
annotation step (`scripts/annotate_token_costs.py` read `data/metrics/`, which nothing
in this repo writes); and the separate `scripts/validate_skills.py`, whose
ACTIVE_SKILLS compliance-schema checks were merged into `renderer/validate_skills.py`
so there is a single validator. `validate-sources.yml`'s `verify-test-sources` and
`check-skill-integrity` jobs were also dropped (the former duplicated `make test`'s own
collection step; the latter scanned a top-level `skills/` directory that no longer
exists post-slimdown and was therefore vacuous) — its one substantive job (orphaned
bytecode) was folded into `ci.yml` above.

### Gate: SKILL.md Frontmatter, Registry, and Compliance

`renderer/validate_skills.py` runs two passes:

1. **Frontmatter + registry** (every `SKILL.md` under `src/skills/`): required
   `name`/`description` fields, known `roles`, and two-way completeness against
   `src/SKILLS.md`.
2. **ACTIVE_SKILLS compliance audit** (only the skills listed in `ACTIVE_SKILLS`
   inside `renderer/validate_skills.py`): required frontmatter metadata keys,
   required directory structure, and presence of a `## Self-Improvement` section.

**Run locally:**
```bash
python renderer/validate_skills.py           # errors cause CI failure
python renderer/validate_skills.py --strict  # warnings also cause failure
python renderer/validate_skills.py --skill protocol-validator  # audit a single skill
python renderer/validate_skills.py --json    # ACTIVE_SKILLS compliance audit, machine-readable
```

**Required frontmatter fields:**

```yaml
---
name: <skill-name>
description: "<brief description>"
license: Proprietary
compatibility: agentic-engineers framework v5.10+. Requires Python 3.11+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: <category>
  role: <role>
  model: <model>
  effort: low | medium | high
---
```

**Required directory structure per skill:**
```
src/skills/<skill-name>/
├── SKILL.md          ← required
├── __init__.py       ← required (exports public API)
├── scripts/          ← required directory
│   └── <skill>.py
└── tests/            ← required directory
    └── test_<skill>.py   ← at least one test file required
```

Author the skill/agent directly by following the structure of an existing one
(e.g. `spec-validator` for a skill, `engineer-agent.md` for an agent) — see
`src/SKILLS.md` / `src/AGENTS.md` for the registration steps.

### Gate: Skill Template Conformance Report (Audit Trail)

This gate runs `renderer/validate_skills.py --json`, pipes it through
`scripts/format_skill_report.py`, and writes the output to the GitHub Actions step
summary. It is **non-failing** — it exists to create an audit trail of skill health
over time. Check it in the "Summary" tab of any CI run.

**Run locally:**
```bash
python renderer/validate_skills.py --json | python scripts/format_skill_report.py
```

### Harness Regression Check

`.github/workflows/ci.yml`'s "Gate 4: Harness regression check" step runs
`renderer/scripts/check_test_regression.py` after `make render-*` and `make test`,
enforcing a minimum collected-test-count floor. See
`docs/REGRESSION-GATE-POLICY.md` for the baseline and
how to update it.

---

### Pre-Push Checklist

Before pushing to a feature branch:

```bash
# 1. Lint
make lint

# 2. Skill compliance (if you touched any skill)
python renderer/validate_skills.py

# 3. Full test suite
make test

# 4. Harness render (if you touched skills or agents)
make render-copilot render-claude render-opencode render-codex render-specs

# 5. Verify manifest
make verify
```

The pre-push git hook validates agent/workflow YAML, SPEC/AGENTS/README
presence, SPEC architectural constraints, and the `.agents_verification_sha`
integrity hash — it does **not** re-run the full test suite or a render pass
(both are redundant with CI, which runs them minutes later); run `make test`
yourself before pushing. Do not bypass hooks with `SKIP_HOOKS=1` except in
documented emergencies.

---

## Testing

```bash
# Run all tests with coverage (recommended)
make test

# Run specific test file
pytest tests/test_e2e_protocol_full_cycle.py -v
```

All new code must have tests. Coverage is measured and reported, but it is
**not** a hard gate — there is no `--cov-fail-under` anywhere in the repo, so a
coverage drop will not fail CI on its own. Reviewers check it by eye.

### About make test

The `make test` target runs:
- All pytest tests
- Coverage report generation
- Automatic display of missing coverage

Equivalent to:
```bash
python3 -m pytest tests/ --cov=src --cov-report=term-missing -q
```

### Parallel & Concurrent Test Validation

**Historical context:** the `TestConcurrentInvocations` test class validated that
concurrent agent invocations were safe under thread concurrency in the old
subprocess-based `invoke_agent.py` seam, which wrote and read HANDBACK files across
threads. It guarded against a **TOCTOU race condition** where a HANDBACK file poller
read an empty file that was still being written by a writer thread.

`src/orchestration/agents/invoke_agent.py` and its file poller have since been removed
as part of the move to the
`src/AGENTS.md` (“Direct Sub-Agent Spawn Execution Model” section):
a spawned sub-agent's HANDBACK is now returned directly as the result of the Agent/Task
tool call, in-context, with no separate file poller reading it. As of SPEC-2026-009
(2026-08-13) the filesystem queue itself — and the `enqueue()` calls that used to record
DELEGATE/HANDBACK to it for audit purposes — no longer exist either; the harness session
transcript is the durable audit record for protocol validity (a separate, queryable
JSONL event log for metrics was added afterward per `docs/SPEC.md` clause 7 — see
`docs/PROTOCOL.md` § Audit Events (JSONL) — but that is additive, not a queue, and not
what this historical note is about). Neither the removed subprocess seam nor the
removed queue write path is what this test class covered.

**RESOLVED:** the `test-concurrent` Makefile target and its `quality-gate`
prerequisite, and the equivalent inline check in `.githooks/pre-push`
("6b. RUN CONCURRENT TESTS"), have been removed rather than repointed —
there is no surviving mechanism (subprocess spawn + file-poll race, or — since
SPEC-2026-009 — a queue write) for a replacement test to guard. If concurrent-spawn
coverage under the new model is wanted, that is new test coverage to design, not a
repoint of this guard.

---

## Multi-Model Agent Variants

Some Tier 3 (Opus) roles support **multi-model selection** within the opus family. Rather than a single fixed model, the Orchestrator selects the optimal opus variant when creating DELEGATEs for these roles.

### Roles with Multi-Model Support (Phase 1)

**Principal Engineer** — selects among 4.6, 4.7, 4.8:
- `claude-opus-4.6` — pure architecture planning (design-only; no cross-repo execution)
- `claude-opus-4.7` — design decisions with cross-repo execution impact
- `claude-opus-4.8` — security-critical design choices (auth, crypto, compliance)

**Security Engineer** — always fable-5 (unconditional default):
- `claude-fable-5` — always; security analysis is non-negotiable (highest capability tier)
- `claude-opus-4.8` — emergency fallback only if fable-5 is unavailable; document in HANDBACK
- Never downgrade by choice

### How It Works

1. **Orchestrator selects variant** at DELEGATE-creation time based on the incoming task profile
2. **model_guidance field** in the DELEGATE communicates the selection rationale to the receiving agent
3. **Quality Engineer** provides `model_assessment` feedback in HANDBACK (model used, appropriateness, recommendation)
4. **Model Engineer** analyzes `model_assessment` feedback and feeds recommendations back to the Orchestrator routing loop

### DELEGATE Example with model_guidance

```yaml
---
handoff_type: DELEGATE
task_id: 2026-06-05-arch-cursor-design
role: principal-engineer
model: claude-opus-4.6
model_guidance: |
  Pure architecture planning — use claude-opus-4.6.
  Escalate to 4.7 if cross-repo execution scope is discovered during analysis.
effort: high
scope: Design delta-token cursor model for event store sync.
---
```

### Future Phases

- **Phase 2** (planned): Extend multi-model selection to Senior Engineer (sonnet-4.5 vs 4.6)
- **Phase 3** (planned): Full multi-model routing for all roles, driven by Model Engineer feedback data

All changes are backward-compatible. Validators and tests require no updates for the Phase 1 rollout — `claude-opus-4.7` is now in `LOCKED_MODELS.sh`.

---

## Model Selection (Locked)

**CRITICAL: Model choices are LOCKED by strategic decision and enforced by pre-commit hooks.**

We have chosen these Claude models today for cost-quality alignment:
- **claude-haiku-4.5** — engineers, orchestrator (fast, cost-effective)
- **claude-sonnet-5** — model-engineer, quality, lead, senior engineers (complex tasks)
- **claude-opus-5** — principal-engineer (cross-service architecture)
- **claude-fable-5** — security-engineer (unconditional; highest capability for security tasks)

### Why Locked Models?

**Positive enforcement approach:**
- ✅ "These are our chosen models" (not "GPT forbidden")
- ✅ Users CAN request changes via Orchestrator
- ✅ Changes are documented and auditable
- ✅ Simpler than maintaining rejection patterns

### Adding a New Agent

When adding an agent to `src/agents/`, use the canonical format with DOTS:

```yaml
---
name: my-agent
description: Agent description
model: claude-{variant}-{major}.{minor}  # ← REQUIRED format (e.g., claude-haiku-4.5)
---
```

**Locked models** (pick one):
- ✅ `claude-haiku-4.5`
- ✅ `claude-sonnet-4.5`
- ✅ `claude-sonnet-4.6`
- ✅ `claude-opus-4.6`
- ✅ `claude-opus-4.7`
- ✅ `claude-opus-4.8`

**Not locked** (rejected by pre-commit hook):
- ❌ `claude-opus-4-7` (hyphens in version — use dots)
- ❌ `claude-opus` (unversioned — use full version)
- ❌ `gpt-4` (not a locked model — use Claude)

### Requesting a Model Change

If you need a different model for an agent:

1. **Contact Orchestrator** with:
   - Agent name (e.g., `engineer-agent`)
   - Requested model (e.g., `claude-sonnet-4.5`)
   - Reason (e.g., "Current model too slow for code review")
   - Expected impact (e.g., "Cost +$0.02/task, quality +15%")

2. **Orchestrator evaluates:**
   - Budget impact (is cost increase justified?)
   - Capability improvement (does task profile warrant it?)
   - Timeline (when should it take effect?)

3. **Decision:**
   - ✅ Approved → Model is added to locked set
   - ⏸️ Deferred → Revisit later (e.g., next budget cycle)
   - ❌ Denied → Explain why (e.g., budget constraint)

4. **If approved:**
   - Model is added to `.githooks/LOCKED_MODELS.sh`
   - PR includes rationale in commit message
   - Pre-commit hook enforces new lock from merge forward

### Why Per-Harness Transformations?

Different harnesses have incompatible model format requirements:

| Harness | Model Examples | Format |
|---------|---|---|
| Copilot CLI | `claude-opus-4.8`, `claude-opus-4.6` (multi-model) | Dots in version |
| OpenCode | `claude-opus-4.7` | Hyphens in version (limitation) |
| Claude Code | `opus` | Short alias |
| Codex | `claude-opus-5` | Codex custom format |

Note: Principal and Security Engineer roles support multi-model selection. Orchestrator chooses the appropriate opus variant (4.6, 4.7, or 4.8) at DELEGATE-creation time based on task complexity. See SPEC.md > Model Selection Architecture.

**Key principle:** Source agents use ONE canonical format (DOTS). Renderers transform per-harness. This separation makes source maintainable and allows automation of transformations.

### Workflow

1. **Choose model** → Pick from locked list (canonical format with DOTS)
   ```yaml
   model: claude-haiku-4.5  # correct
   ```

2. **Add comment** → Explain why this model fits your agent
   ```
   Agent Purpose: Fast routing/analysis (low cost, low latency)
   Model Choice: claude-haiku-4.5 (Haiku is fastest; 4.5 is stable)
   ```

3. **Verify format** → Pre-commit hook validates automatically
   ```bash
   git add src/agents/my-agent.md
   git commit -m "feat: add my-agent"
   # Pre-commit validates model is in locked set and format is correct
   ```

4. **Render & test** → Ensure all harnesses render correctly
   ```bash
   make render-all
   make test-models  # Runs model compliance tests
   ```

### If Pre-Commit Rejects Your Model

```
❌ Model not in locked set: src/agents/my-agent.md
   Model: claude-gpt-4
   Locked models (approved choices):
     - claude-haiku-4.5
     - claude-sonnet-4.5
     - claude-sonnet-4.6
     - claude-opus-4.6
     - claude-opus-4.7
     - claude-opus-4.8
   To request a model change, contact the Orchestrator
```

**Options:**
1. Use a locked model (recommended for standard tasks)
2. Request new model from Orchestrator (include reason and impact)
3. Discuss with team (if locked models don't fit your use case)

### See Also

- **Lock rationale:** `.githooks/LOCKED_MODELS_RATIONALE.md`
- **Locked models:** `.githooks/LOCKED_MODELS.sh`
- **Full architecture:** `docs/SPEC.md` — "Approved Claude Models" section
- **Tests:** `tests/test_model_naming_compliance.py` — compliance verification
- **Agent registry:** `src/AGENTS.md` — model assignments by role

---

## References

- **Agent Roster & Routing:** `src/AGENTS.md` — all roles, responsibilities, routing decision tree, and tool-access model
- **Skills Matrix:** `src/SKILLS.md` — available skills and capabilities
- **Specification:** `docs/SPEC.md` — protocol and model assignments

---

## FAQ

- **How do I add an agent?** Author `src/agents/<name>-agent.md` directly and register it — see `src/AGENTS.md`
- **How do I add a skill?** Author `src/skills/<name>/SKILL.md` and register it in `renderer/validate_skills.py` and `config/FRAMEWORK-MANIFEST.yaml` — see `src/skills/README.md` § Adding a skill
- **What if CI fails?** Run `make verify` locally — it checks everything
- **Need help?** Check the references above or open an issue

---

**Start here:** Clone, install, verify, then use the framework's own meta-skills to extend it.


