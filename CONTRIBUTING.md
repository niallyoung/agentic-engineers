# Contributing to agentic-engineers

> **Philosophy:** Use agentic-engineers itself to improve agentic-engineers. Delegate changes to the framework's own agents and skills.

---

## Quick Start

```bash
git clone https://github.com/niallyoung/agentic-engineers.git && cd agentic-engineers
make install && make verify && make test
```

You're ready to contribute.

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
- `~/.pi/` — π.dev experimental config
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
   - Code changes? Edit directly and run tests

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

All framework extensions run through the validation pipeline automatically. See [`src/AGENTS.md`](src/AGENTS.md) and [`src/SKILLS.md`](src/SKILLS.md) for the complete roster.

---

## Making Changes

1. **Branch:** `git checkout -b feature/your-change`
2. **Use framework skills** to scaffold agents, skills, or designs
3. **Test locally:** `make verify` and `python3 -m pytest tests/ -q`
4. **Commit:** Use [conventional commits](https://www.conventionalcommits.org/) (e.g., `feat(skills): add X`, `fix(agents): correct Y`)
5. **Push & request review:** CI enforces all standards automatically

**Commit scopes:** `agents`, `skills`, `renderer`, `src`, `tests`, `ci`, `deps`

---

## Working with Background Agents

When using background agents (e.g., `skill-creator`, `agent-creator`) to create implementation files:

**Background agents MUST explicitly commit their files to git.** This ensures:
- ✅ Created files persist beyond the agent's session
- ✅ Tests aren't lost to bytecode caching
- ✅ HANDBACK includes proof of commitment (commit SHA)
- ✅ Orchestrator can validate files actually reached git

**Read:** [`docs/BACKGROUND-AGENT-COMMIT-PROTOCOL.md`](docs/BACKGROUND-AGENT-COMMIT-PROTOCOL.md) for the detailed protocol agents must follow.

**Read:** [`docs/FILE-LOSS-PREVENTION.md`](docs/FILE-LOSS-PREVENTION.md) for comprehensive prevention mechanisms and troubleshooting.

---

## Preventing Orphaned Files

The framework automatically validates:

1. **Pre-commit hook** — Rejects any `.pyc` bytecode (never staged)
2. **Pytest plugin** — Verifies all tests come from `.py` source (not cache)
3. **CI/CD validation** — Checks no orphaned bytecode in commits
4. **HANDBACK schema** — Requires `commit_sha` for file-creating agents

**If you encounter issues with missing files:**
- See [`docs/FILE-LOSS-PREVENTION.md#troubleshooting`](docs/FILE-LOSS-PREVENTION.md#troubleshooting)
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

## Testing

```bash
# Run all tests with coverage (recommended)
make test

# Run specific test file
pytest tests/test_invoke_agent.py -v

# Run concurrent tests (required before push)
make test-concurrent
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

The `TestConcurrentInvocations` test class validates that concurrent agent
invocations work correctly under thread concurrency. This test class guards
against a class of **TOCTOU race conditions** where a HANDBACK file poller
reads an empty file that is still being written by a writer thread.

**Run it before every push:**

```bash
make test-concurrent
```

Or equivalently:

```bash
python3 -m pytest tests/test_invoke_agent.py::TestConcurrentInvocations -v --tb=short
```

The pre-push hook (`.githooks/pre-push`) runs this automatically. If it fails
locally it **will** fail in CI — do not bypass with `SKIP_HOOKS=1` unless you
have an unrelated emergency.

**Root cause history:** CI builds were failing with
`HandbackValidationError('HANDBACK file does not contain a YAML mapping (dict)')`
because `open(path, 'w')` creates the file on disk before `yaml.dump()` writes
its content. The poller saw `path.exists() == True`, read an empty file, and
failed validation. The fix is:

1. **Test helper** (`write_handback_after_delay`): atomic write via `os.replace`
   after writing to a `.tmp` sibling file.
2. **Production code** (`_read_and_validate_handback`): returns `None` for empty
   files instead of raising, signalling the polling loop to continue retrying.

---

## Model Selection (Locked)

**CRITICAL: Model choices are LOCKED by strategic decision and enforced by pre-commit hooks.**

We have chosen these Claude models today for cost-quality alignment:
- **claude-haiku-4.5** — engineers, orchestrator (fast, cost-effective)
- **claude-sonnet-4.5** — model-engineer (analysis, cost-quality balance)
- **claude-sonnet-4.6** — lead, quality, senior engineers (complex tasks)
- **claude-opus-4.7** — security, principal engineers (high-stakes decisions)

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
- ✅ `claude-opus-4.7`

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

| Harness | Source | Renders to | Why |
|---------|--------|------------|-----|
| **Copilot CLI** | `claude-opus-4.7` | `claude-opus-4.7` | Uses Anthropic API format (dots required) |
| **OpenCode** | `claude-opus-4.7` | `claude-opus-4-7` | CLI requires hyphens in version (platform constraint) |
| **Claude Code** | `claude-opus-4.7` | `opus` | Web UI uses short aliases for UX |
| **Pi.dev** | `claude-opus-4.7` | `claude-opus-4-7` | Anthropic API format (hyphens) |

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
     - claude-opus-4.7
   To request a model change, contact the Orchestrator
```

**Options:**
1. Use a locked model (recommended for standard tasks)
2. Request new model from Orchestrator (include reason and impact)
3. Discuss with team (if locked models don't fit your use case)

### See Also

- **Lock rationale:** [`.githooks/LOCKED_MODELS_RATIONALE.md`](./.githooks/LOCKED_MODELS_RATIONALE.md)
- **Locked models:** [`.githooks/LOCKED_MODELS.sh`](./.githooks/LOCKED_MODELS.sh)
- **Full architecture:** [`docs/SPEC.md`](docs/SPEC.md) — "Approved Claude Models" section
- **Tests:** [`tests/test_model_naming_compliance.py`](tests/test_model_naming_compliance.py) — compliance verification
- **Agent registry:** [`docs/AGENTS.md`](docs/AGENTS.md) — model assignments by role

---

## References

- **Agent Roster:** [`src/AGENTS.md`](src/AGENTS.md) — all roles and responsibilities
- **Skills Matrix:** [`src/SKILLS.md`](src/SKILLS.md) — available skills and capabilities
- **Routing Logic:** [`src/DECISION-MAKING.md`](src/DECISION-MAKING.md) — how agents are selected
- **Protocol Spec:** [`src/CLI-PERMISSIONS.md`](src/CLI-PERMISSIONS.md) — tool access control
- **Cost Model:** [`src/TOKEN_METRICS.md`](src/TOKEN_METRICS.md) — token spend specification

---

## FAQ

- **How do I add an agent?** Use `agent-creator` skill or read [`src/AGENTS.md`](src/AGENTS.md)
- **How do I add a skill?** Use `skill-creator` skill or read [`src/SKILLS.md`](src/SKILLS.md)
- **What if CI fails?** Run `make verify` locally — it checks everything
- **Need help?** Check the references above or open an issue

---

**Start here:** Clone, install, verify, then use the framework's own meta-skills to extend it.
