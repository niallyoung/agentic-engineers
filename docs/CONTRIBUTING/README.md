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

This project targets **Python 3.11**. CI and the Docker container are the **source of truth** — all GitHub Actions workflows and the `Dockerfile` use Python 3.11, and `setup.py` requires `>=3.11`. A `.python-version` file pins 3.11 for pyenv/local tooling.

To run the test suite under the exact CI Python version without installing 3.11 locally, use the container target:

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

All framework extensions run through the validation pipeline automatically. See [`src/AGENTS.md`](src/AGENTS.md) and [`src/SKILLS.md`](src/SKILLS.md) for the complete roster.

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
│   ├── opencode/skills/ # Rendered for OpenCode
│   └── pi/skills/       # Rendered for π.dev
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

## Multi-Model Agent Variants

Some Tier 3 (Opus) roles support **multi-model selection** within the opus family. Rather than a single fixed model, the Orchestrator selects the optimal opus variant when creating DELEGATEs for these roles.

### Roles with Multi-Model Support (Phase 1)

**Principal Engineer** — selects among 4.6, 4.7, 4.8:
- `claude-opus-4.6` — pure architecture planning (design-only; no cross-repo execution)
- `claude-opus-4.7` — design decisions with cross-repo execution impact
- `claude-opus-4.8` — security-critical design choices (auth, crypto, compliance)

**Security Engineer** — always 4.8 (non-downgrade rule):
- `claude-opus-4.8` — always; security analysis is non-negotiable
- `claude-opus-4.7` — emergency fallback only if 4.8 is unavailable; document in HANDBACK
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
- **claude-sonnet-4.5** — model-engineer (analysis, cost-quality balance)
- **claude-sonnet-4.6** — lead, quality, senior engineers (complex tasks)
- **claude-opus-4.6** — principal-engineer default (pure planning tasks)
- **claude-opus-4.7** — principal-engineer variant (design+execution tasks)
- **claude-opus-4.8** — security-engineer (non-downgrade; all security tasks)

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
| π.dev | `claude-opus-4.6`, `claude-opus-4.8` | Anthropic API format (dots) |

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

- **Lock rationale:** [`.githooks/LOCKED_MODELS_RATIONALE.md`](./.githooks/LOCKED_MODELS_RATIONALE.md)
- **Locked models:** [`.githooks/LOCKED_MODELS.sh`](./.githooks/LOCKED_MODELS.sh)
- **Full architecture:** [`docs/SPEC.md`](docs/SPEC.md) — "Approved Claude Models" section
- **Tests:** [`tests/test_model_naming_compliance.py`](tests/test_model_naming_compliance.py) — compliance verification
- **Agent registry:** [`docs/AGENTS.md`](docs/AGENTS.md) — model assignments by role

---

## Automation Roadmap (Phase 4–6)

This section consolidates opportunities to automate manual workflows and reduce human churn. See [`docs/automation-analysis.md`](../automation-analysis.md) for full analysis (session artifact).

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

See [`docs/final-audit.md`](../final-audit.md) for full pre-merge readiness checklist (session artifact).

**Current Status:** Code ready for merge (all CI checks passing, no regressions).

**Deferred Phases:**
- **Phase 5:** External memory-API infrastructure (REST/GraphQL backend)
- **Phase 6:** Metrics aggregation & observability (Prometheus + Grafana)

---

## OpenCode Renderer (Phase 4 Details)

The `renderer/scripts/render-opencode.sh` emits agent frontmatter for OpenCode integration. Two defects prevent correct thinking/reasoning emission and overstate permission enforcement.

See [`docs/OPENCODE-RENDERER-FIX-PLAN.md`](../OPENCODE-RENDERER-FIX-PLAN.md) for full analysis (session artifact).

### Defect 1: No-op `thinking:` Block

**Current:** Emits `thinking:` key (lines 762–769), but OpenCode ignores it (not in `KNOWN_KEYS`).
**Impact:** Extended thinking never enabled for principal-engineer, security-engineer.
**Fix:** Replace with supported `variant:` emission (requires variant support in provider block).

### Defect 2: Uniform Permissions vs. Claimed Granularity

**Current:** Every agent gets identical `permission:` block (allow-all).
**Claim (false):** "Each agent has granular permissions enforced by OpenCode" (AGENTS.md).
**Impact:** Review roles (quality, lead, model-engineer) incorrectly receive `edit: allow` and `bash: allow`.
**Fix:** Implement least-privilege matrix (baseline `"*": deny`, explicit allows per role).

### Proposed Per-Role Permission Matrix

| Role | read | glob | grep | webfetch | websearch | edit | bash | task |
|------|:----:|:----:|:----:|:--------:|:---------:|:----:|:----:|:----:|
| orchestrator      | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| principal-engineer| ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| senior-engineer   | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| engineer          | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| lead-engineer     | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| quality-engineer  | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| security-engineer | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| model-engineer    | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

**Rationale:** Orchestrator routes without direct edits. Review roles are read-only. Implementation roles get edit/bash. Only orchestrator and senior-engineer may spawn subagents.

### Implementation Steps (Phase 4)

1. Remove the `thinking:` case from `render-opencode.sh` (lines 762–769)
2. Add per-role `variant` emission for reasoning-capable roles
3. Confirm/extend provider blocks in `opencode.jsonc` (variants + reasoning flag)
4. Replace uniform permission block with least-privilege per-role lookup
5. Gate `task` permission to orchestrator and senior-engineer only
6. Add `websearch: allow` to research-capable roles
7. Fix documentation: regenerate permission table from matrix, not hardcoded claims
8. Validate: run renderer, parse `KNOWN_KEYS`, assert compliance

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
