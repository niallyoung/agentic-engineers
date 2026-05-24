# Contributing to agentic-engineers

> **Philosophy:** Use agentic-engineers itself to improve agentic-engineers. Delegate changes to the framework's own agents and skills.

---

## Quick Start

```bash
git clone https://github.com/niallyoung/agentic-engineers.git && cd agentic-engineers
make install && make verify && python3 -m pytest tests/ -q
```

You're ready to contribute.

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
# Manually trigger version-manager
python3 skills/version-manager/scripts/update-changelog.py --verbose

# Review changes
git diff CHANGELOG.md

# Stage and commit
git add CHANGELOG.md
git commit --amend  # Add to current commit
```

**CI validates CHANGELOG consistency:**
- ✅ All commits must have corresponding CHANGELOG entries
- ✅ [Unreleased] section must match commits since last release tag
- ✅ Semantic version calculation must be correct

If CI fails on CHANGELOG validation:
```bash
python3 scripts/validate_changelog_ci.py  # See what's missing
python3 skills/version-manager/scripts/update-changelog.py --force
git add CHANGELOG.md
git commit --amend
```

---

## Testing

```bash
# Run all tests
python3 -m pytest tests/ -q

# With coverage
python3 -m pytest tests/ --cov=src --cov-report=term-missing -q

# Concurrent/race-condition guard (required before push)
python3 -m pytest tests/test_invoke_agent.py::TestConcurrentInvocations -v --tb=short
```

All new code must have tests. CI enforces >85% coverage.

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
