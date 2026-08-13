# Contributing to agentic-engineers

> **Philosophy:** Use agentic-engineers itself to improve agentic-engineers. Delegate changes to the framework's own agents and skills.

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

3. **Make your changes** using the framework's own tools:
    - New agent? Use `agent-creator` skill
    - New skill? Use `skill-creator` skill
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
       - "make test FILTER=test_postal passes with no failures"
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

**Don't manually create or edit files.** Use the framework's meta-skills:

- **New agent?** Delegate to `agent-creator` — scaffolds definitions, validates YAML, updates registries.
- **New skill?** Delegate to `skill-creator` — scaffolds structure, handles SKILL.md, validates against roster.
- **Code review?** Use the `Lead Engineer` agent for architectural guidance.
- **Complex planning?** Use the `Senior Engineer` agent to plan unscoped work.

All framework extensions run through the validation pipeline automatically. See [`src/AGENTS.md`](../../src/AGENTS.md) and [`src/SKILLS.md`](../../src/SKILLS.md) for the complete roster.

---

## Creating New Skills

**Important:** Skills are always created in the **framework source**, not in user config directories.

### Correct Workflow

1. **Create skill in framework source:**
   ```bash
   # Skills live in src/skills/{category}/{skill-name}/
   mkdir -p ~/git/agentic-engineers/src/skills/{category}/{skill-name}/{scripts,references}
   
   # Example: test-sync-validator in testing category
   mkdir -p ~/git/agentic-engineers/src/skills/testing/test-sync-validator/{scripts,references}
   ```

2. **Create SKILL.md with frontmatter:**
   ```yaml
   ---
   name: test-sync-validator
   description: Detects test fixture drift from code changes...
   license: Proprietary
   metadata:
     author: agentic-engineers
     version: "1.0"
     category: testing
     role: quality-engineer
   ---
   ```

3. **Add scripts to scripts/ subdirectory:**
   - Keep scripts modular and focused
   - One responsibility per script
   - Include error handling and help text

4. **Build and install:**
   ```bash
   # Build renders src/ → dist/ → ~/.claude/, ~/.copilot/, etc.
   make install
   
   # Verify skill was rendered to all harnesses
   ls -la ~/.claude/skills/test-sync-validator/
   ls -la ~/.copilot/skills/test-sync-validator/
   ls -la ~/.config/opencode/skills/test-sync-validator/
   ```

### ❌ Anti-Pattern: Don't Create Directly in User Config

**WRONG:**
```bash
# Never do this!
mkdir -p ~/.claude/skills/my-skill
# This gets overwritten by make install
```

**RIGHT:**
```bash
# Always do this
mkdir -p ~/git/agentic-engineers/src/skills/{category}/my-skill
make install  # Renders to ~/.claude/, ~/.copilot/, etc.
```

### Directory Structure Reference

```
agentic-engineers/
├── src/skills/          # ← Authoritative source
│   ├── testing/
│   │   ├── test-sync-validator.md      # Main spec
│   │   └── scripts/
│   │       └── test_sync_validator.py  # Implementation
│   ├── orchestration/
│   ├── optimization/
│   └── ...
├── dist/                # ← Generated build artifacts
│   ├── claude/skills/   # Rendered for Claude CLI
│   ├── copilot/skills/  # Rendered for Copilot CLI
│   └── opencode/skills/ # Rendered for OpenCode
├── ~/.claude/skills/    # ← User installation (auto-generated, don't edit)
├── ~/.copilot/skills/   # ← User installation (auto-generated, don't edit)
└── ~/.config/opencode/skills/ # ← User installation (auto-generated, don't edit)
```

### Test Fixture Synchronization

When making code changes, ensure tests stay in sync:

1. **Use test-sync-validator to detect drift:**
   ```bash
   git diff origin/main...HEAD | \
     python src/skills/testing/scripts/test_sync_validator.py \
       --diff /dev/stdin --mode pre-merge --fail-on-critical
   ```

2. **Fix discovered mismatches before commit:**
   - Update LOCKED_MODELS if models change
   - Update router expectations if logic changes
   - Update cost/quality thresholds if tiers change

3. **Commit test updates with code changes:**
   ```bash
   git add src/agents/security-engineer-agent.md
   git add tests/test_model_naming_compliance.py  # test fixture sync
   git commit -m "feat(agents): upgrade to claude-opus-4.8"
   ```

---

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
   across all harnesses; see [docs/RENDERING.md](../RENDERING.md).
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
  `model-*` skills recommend cost-quality-optimal routing.

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

When using background agents (e.g., `skill-creator`, `agent-creator`) to create implementation files:

**Background agents MUST explicitly commit their files to git.** This ensures:
- ✅ Created files persist beyond the agent's session
- ✅ Tests aren't lost to bytecode caching
- ✅ HANDBACK includes proof of commitment (commit SHA)
- ✅ Orchestrator can validate files actually reached git

**Read:** [`docs/BACKGROUND-AGENT-COMMIT-PROTOCOL.md`](../BACKGROUND-AGENT-COMMIT-PROTOCOL.md) for the detailed protocol agents must follow.

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


- ✅ Calculates next semantic version

**You don't need to manually edit CHANGELOG.md** — it's automated. Just write descriptive commit messages:

```bash
git commit -m "feat(skills): add cache invalidation"      # → Added section
git commit -m "fix(agents): resolve race condition"      # → Fixed section
git commit -m "docs: update installation guide"          # → Documentation section
```

**If CHANGELOG doesn't update:**
```bash
# Manually add an entry to the [Unreleased] section in CHANGELOG.md

# Review changes
git diff CHANGELOG.md

# Stage and commit
git add CHANGELOG.md
git commit --amend  # Add to current commit
```

**CI validates CHANGELOG consistency:**
- ✅ All commits must have corresponding CHANGELOG entries
- ✅ CHANGELOG uses direct versioned entries (## [vX.Y.Z] - YYYY-MM-DD format)
- ✅ Semantic version calculation must be correct

If CI fails on CHANGELOG validation:
```bash
python3 scripts/validate_changelog_ci.py  # See what's missing
# Manually update CHANGELOG.md [Unreleased] section
git add CHANGELOG.md
git commit --amend
```

---

## CI/CD Requirements

All contributions pass through a multi-gate CI pipeline defined in
`.github/workflows/ci.yml`. This section documents each gate, what it checks,
and how to satisfy it locally before pushing.

### Gates Overview

| Gate | Script | Failing Exit |
|------|--------|-------------|
| Credential scan | `scripts/check-gitconfig-no-tokens.sh` | Hard fail |
| Lint | `make lint` | Hard fail |
| **SKILL.md frontmatter + registry + compliance** | `renderer/validate_skills.py` | Hard fail on errors; warn on warnings |
| **Skill template conformance report** | `renderer/validate_skills.py --json` + `scripts/format_skill_report.py` | Non-failing (audit trail) |
| **Orphaned bytecode check** | Inline (folded in from the former `validate-sources.yml`) | Hard fail |
| Render agents + skills | `make render-*` | Hard fail |
| Test suite | `make test` | Hard fail |
| **Harness regression check** | `renderer/scripts/check_test_regression.py` | Hard fail |
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

Use the `skill-creator` skill (or `agent-creator` for agents) to scaffold a
conformant skill/agent directly — see `src/SKILLS.md` / `src/AGENTS.md`.

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
[docs/REGRESSION-GATE-POLICY.md](../REGRESSION-GATE-POLICY.md) for the baseline and
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
pytest tests/orchestration/test_orchestrator_integration.py -v
```

All new code must have tests. CI enforces >85% coverage.

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
[Direct Sub-Agent Spawn Execution Model](../../src/AGENTS.md#direct-sub-agent-spawn-execution-model):
a spawned sub-agent's HANDBACK is now returned directly as the result of the Agent/Task
tool call, in-context, with no separate file poller reading it. As of SPEC-2026-009
(2026-08-13) the filesystem queue itself — and the `enqueue()` calls that used to record
DELEGATE/HANDBACK to it for audit purposes — no longer exist either; the harness session
transcript is the sole durable audit record. Neither the removed subprocess seam nor the
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

- **Lock rationale:** [`.githooks/LOCKED_MODELS_RATIONALE.md`](../../.githooks/LOCKED_MODELS_RATIONALE.md)
- **Locked models:** [`.githooks/LOCKED_MODELS.sh`](../../.githooks/LOCKED_MODELS.sh)
- **Full architecture:** [`docs/SPEC.md`](../SPEC.md) — "Approved Claude Models" section
- **Tests:** [`tests/test_model_naming_compliance.py`](../../tests/test_model_naming_compliance.py) — compliance verification
- **Agent registry:** [`src/AGENTS.md`](../../src/AGENTS.md) — model assignments by role

---

## Automation Roadmap (Phase 4–6)

This section consolidates opportunities to automate manual workflows and reduce human churn.

### Phase 4: Git Hooks Enforcement (HIGH PRIORITY)

**Current State:** Pre-commit and pre-push hooks validate but only warn; they do not reject commits.
**Gap:** Several checks should REJECT commits instead of warning.

#### 4.1 Pre-Commit: File Permissions Enforcement
- **Implementation:** Update `.githooks/pre-commit` to REJECT commits with executable `.md`, `.yaml`, `.json` files
- **Reject if:** Scripts are NOT executable (`+x`)
- **Allow bypass:** `ENFORCE_PERMS=0` for git-related workflows (rare)
- **Effort:** 30 minutes

#### 4.2 Pre-Commit: Staging Purity
- **Implementation:** Validate that only staged changes are committed (no uncommitted changes outside staging area)
- **Reject if:** `git status --short` shows unstaged changes
- **Exception:** `.gitignore`'d files are OK
- **Effort:** 45 minutes

#### 4.3 Commit Message Task ID Enforcement
- **Current State:** `commit-msg` hook validates format; warnings are informational only
- **Gap:** Task ID format and conventional commits should be ERRORS (not warnings)
- **Implementation:**
  - Require task ID format: `YYYY-MM-DD-kebab-case`
  - Require conventional commit: `type(scope): subject`
  - Reject if missing (allow `GIT_SKIP_HOOKS=1` bypass with audit trail)
- **Effort:** 20 minutes

**Implementation Priority:**
| Item | Effort | Impact | Blocker? |
|------|--------|--------|----------|
| File permissions REJECT | 30min | Medium | No |
| Staging purity check | 45min | Medium | No |
| Task ID enforcement | 20min | High | No |

---

### Phase 5: PR & Merge Automation (MEDIUM PRIORITY)

#### 5.1 PR Body Auto-Generation (Future)
- **Input:** Commit messages + SPEC.md cross-references
- **Output:** Structured PR body (scannable, consistent)
- **New skill:** `pr-body-generator` (reusable)
- **Trigger:** CI on PR creation, or on-demand
- **Effort:** 2–3 hours

#### 5.2 Merge Strategy Enforcement (Future)
- **Policy:** Always squash feature branches
- **Implementation:** GitHub branch protection (simpler than custom workflow)
- **Effort:** 1 hour

#### 5.3 Post-Merge Branch Cleanup (NICE-TO-HAVE)
- **Current:** Manual `gh pr merge --delete-branch`
- **Future:** GitHub Actions post-merge workflow
- **Effort:** 30 minutes

---

### Phase 6: Extended Memory & Observability (FUTURE)

**Current Status:** Code ready for merge (all CI checks passing, no regressions).

**Deferred Phases:**
- **Phase 5:** External memory-API infrastructure (REST/GraphQL backend)

---

## OpenCode Renderer (Phase 4 Details) — PARTIALLY IMPLEMENTED

The `renderer/scripts/render-opencode.sh` emits agent frontmatter and `opencode.jsonc`
for OpenCode integration. Two defects were originally identified: a no-op `thinking:`
block, and overstated permission enforcement. **Only the first is fixed.** The second —
per-role spawn/permission gating — is **not implemented**, and this section previously
claimed otherwise. That was corrected here on 2026-08-09 after independent verification
(see below); treat the "IMPLEMENTED"/"COMPLETE" language that used to be on this
section as having been inaccurate.

### Defect 1: No-op `thinking:` Block — FIXED

**Was:** Emitted a `thinking:` key, but OpenCode ignores it (not in `KNOWN_KEYS`), so extended thinking was never enabled for principal-engineer / security-engineer.
**Fix (done):** The `thinking:` block was removed and replaced with the supported `variant:` key (`effort_to_variant`: medium→medium, high/max→high, low→omit). `variant` is in OpenCode `KNOWN_KEYS` and maps to Anthropic extended-thinking budgets. Protocol metadata (`role`/`accepts`/`returns`), which are also non-`KNOWN_KEYS`, were moved under the recognized `options:` block so they are preserved rather than silently swept away.

### Defect 2: Uniform Permissions vs. Claimed Granularity — NOT IMPLEMENTED

**Verified current behavior (2026-08-09):** `render-opencode.sh` (around lines 353-360)
emits a single **global** `permission` block into `opencode.jsonc` — not a per-role
one:

```json
"permission": {
  "read": "allow",
  "edit": "allow",
  "bash": "allow",
  "task": "allow",
  "glob": "allow",
  "grep": "allow",
  "webfetch": "allow"
}
```

Every agent gets this same allow-all block, including `task` — the permission that
gates spawning a sub-agent. The renderer's own generated `AGENTS.md` rules file says as
much explicitly ("All agents use uniform **allow-all** permissions"). There is no
`emit_permission_block()` function and no per-role permission lookup in the OpenCode
renderer today — that was aspirational, not shipped.

**What the real permission model is, and where it lives:** the intended least-privilege
design — including which roles may spawn sub-agents — is the **tools-frontmatter
permission model** defined per-role in `src/agents/*-agent.md` (`tools: [spawn_subagent]`
vs. `tools: []`) and documented in
[src/AGENTS.md > Tools-Frontmatter Permission Model](../../src/AGENTS.md#tools-frontmatter-permission-model).
Per that document, spawn authority (`spawn_subagent`) is granted to **five** roles —
orchestrator, senior-engineer, lead-engineer, principal-engineer, and security-engineer
— not just orchestrator and senior-engineer as an earlier version of the matrix below
implied. **No renderer currently propagates this model into any harness.** It is a
contract each agent's own definition and prompt must self-enforce; nothing in
OpenCode's (or any other harness's) generated config blocks or refuses an unauthorized
or over-deep spawn. The same is true of the depth-3 / fan-out-5 / ancestry-tracking
recursion limits (see
[src/AGENTS.md > Recursion Limits](../../src/AGENTS.md#recursion-limits)): documented
required behavior, not mechanically enforced behavior.

### Per-Role Permission Matrix — INTENDED DESIGN, NOT YET IMPLEMENTED BY ANY RENDERER

The table below reflects the *intended* least-privilege design (spawn authority per
`src/AGENTS.md`'s Tools-Frontmatter Permission Model; other columns per this project's
original least-privilege intent for OpenCode). None of it is live — every OpenCode
agent currently gets the uniform allow-all block shown above instead.

| Role | read | glob | grep | webfetch | websearch | edit | bash | task (spawn) |
|------|:----:|:----:|:----:|:--------:|:---------:|:----:|:----:|:----:|
| orchestrator      | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| principal-engineer| ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| senior-engineer   | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| engineer          | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| lead-engineer     | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| quality-engineer  | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| security-engineer | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| model-engineer    | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

**Rationale (design intent, not current behavior):** Orchestrator routes without direct
edits. Review roles are read-only. Implementation roles get edit/bash. Spawn authority
(`task`) is intended for orchestrator, senior-engineer, lead-engineer,
principal-engineer, and security-engineer per `src/AGENTS.md`; engineer,
quality-engineer, and model-engineer are meant to be leaves.

### Implementation Steps (Phase 4) — OUTSTANDING

1. ✅ Removed the `thinking:` case from `render-opencode.sh`
2. ✅ Added per-role reasoning `variant` emission (`effort_to_variant`)
3. ✅ Provider blocks in `opencode.jsonc` declare `reasoning: true` per model
4. ❌ **Not done:** replace the uniform global `permission` block with a least-privilege per-role lookup
5. ❌ **Not done:** gate `task` permission to the five spawn-authorized roles per `src/AGENTS.md`
6. ❌ **Not done:** differentiate `websearch` by role (currently uniform `allow`, bundled into the same global block)
7. ✅ Moved no-op protocol keys (`role`/`accepts`/`returns`) under the recognized `options:` block
8. ❓ **Unverified:** whether `harness-opencode-feature-sync` reports drift for this gap — re-run it rather than trusting the old "No drift detected" claim, since that claim was made about a permission model that (per this correction) was never actually shipped

---

## References

- **Agent Roster & Routing:** [`src/AGENTS.md`](../../src/AGENTS.md) — all roles, responsibilities, routing decision tree, and tool-access model
- **Skills Matrix:** [`src/SKILLS.md`](../../src/SKILLS.md) — available skills and capabilities
- **Specification:** [`docs/SPEC.md`](../SPEC.md) — protocol and model assignments

---

## FAQ

- **How do I add an agent?** Use `agent-creator` skill or read [`src/AGENTS.md`](../../src/AGENTS.md)
- **How do I add a skill?** Use `skill-creator` skill or read [`src/SKILLS.md`](../../src/SKILLS.md)
- **What if CI fails?** Run `make verify` locally — it checks everything
- **Need help?** Check the references above or open an issue

---

**Start here:** Clone, install, verify, then use the framework's own meta-skills to extend it.

---

## Cost & Budget Reports

The per-role token-budget config, routing matrix, and `cost-aggregation`/`cost-budgeting`
tooling this section used to document were removed in the 2026-08-11 framework slimdown
(SPEC-2026-005) along with the auxiliary skills that implemented them. Model/effort
assignment per role is now documented directly in `docs/SPEC.md`'s Core Architecture and
Model Naming & Harness Compatibility sections. If you need per-task cost reporting,
propose it via the `spec-management` skill rather than reviving the deleted tooling.

