# Contributing to agentic-engineers

> **Architecture:** Queue-based DELEGATE/HANDBACK multi-agent framework with 8 specialized roles.  
> **Philosophy:** Use agentic-engineers itself to improve agentic-engineers. The framework validates all work automatically.

---

## Quick Start

```bash
# Clone, install, verify, and test
git clone https://github.com/niallyoung/agentic-engineers.git
cd agentic-engineers
make install && make verify && python3 -m pytest tests/ -q
```

**Done.** You're ready to contribute.

---

## The Framework Improves Itself

Rather than follow manual procedures, **use the framework's meta-skills to extend it:**

- **Adding a new agent?** Use the `agent-creator` skill to scaffold the agent definition.
- **Adding a new skill?** Use the `skill-creator` skill to scaffold the skill definition.
- **Concerned about code quality?** The CI pipeline enforces standards automatically (`make verify` locally validates everything).
- **Need to review a design?** Use the `Lead Engineer` agent for architectural guidance.
- **Building something complex?** Use the `Senior Engineer` agent to plan unscoped work.

See [`src/AGENTS.md`](src/AGENTS.md) and [`src/SKILLS.md`](src/SKILLS.md) for the complete roster.

---

## Development Workflow

1. **Branch:** `git checkout -b feature/your-change`
2. **Edit:** Make your changes (code, agents, skills, or docs)
3. **Validate:** Run `make verify` locally (runs lint, tests, validators)
4. **Commit:** Use [conventional commits](https://www.conventionalcommits.org/) (e.g., `feat(skills): add X`, `fix(agents): correct Y`)
5. **Push & PR:** `git push` and create a PR with a clear title and description
6. **CI:** All checks must pass; request review only when CI is green

### Conventional Commit Format

```
<type>(<scope>): <description>

feat(skills): add new skill for X
fix(agents): correct routing in orchestrator
docs: update README with new examples
test: add edge case coverage
perf: optimize queue traversal
```

**Scopes:** `agents`, `skills`, `renderer`, `src`, `tests`, `ci`, `deps`

---

## Adding Agents & Skills

**Don't manually create files.** Use the framework to improve itself:

- **Agents:** Delegate to `agent-creator` skill — it scaffolds definitions, validates YAML, updates registries
- **Skills:** Delegate to `skill-creator` skill — it scaffolds skill structure, handles SKILL.md templates, validates against roster

Both skills are available in `src/skills/` and run the full validation pipeline automatically.

If you're manually extending the framework (rare):
- Agents: `src/agents/<name>-agent.md` (update `src/AGENTS.md` too)
- Skills: `src/skills/<category>/` (update `src/SKILLS.md` too)
- Validators run automatically on `make verify`

---

## Test Suite

```bash
# Run all tests
python3 -m pytest tests/ -q

# Run with coverage
python3 -m pytest tests/ --cov=src --cov-report=term-missing -q

# Run a specific test
python3 -m pytest tests/test_renderer.py -v
```

All new code must have tests. CI enforces >85% coverage.

---

## What Happens After You Push

1. **GitHub Actions** runs `make verify` (lint, format, validators, tests)
2. **Automated checks** validate agents, skills, and protocol compliance
3. **Lead Engineer** reviews code quality and architectural fit
4. **Model Engineer** analyzes token spend and recommends optimizations
5. **Once CI passes:** Request review from maintainers

---

## Key References

- **Agent Roster:** [`src/AGENTS.md`](src/AGENTS.md) — 8 roles, routing rules, cost tiers
- **Skills Matrix:** [`src/SKILLS.md`](src/SKILLS.md) — 40+ skills organized by role
- **Decision Rules:** [`src/DECISION-MAKING.md`](src/DECISION-MAKING.md) — Orchestrator routing logic
- **Protocol Spec:** [`src/CLI-PERMISSIONS.md`](src/CLI-PERMISSIONS.md) — Tool access control
- **Cost Tracking:** [`src/TOKEN_METRICS.md`](src/TOKEN_METRICS.md) — Token spend specification

---

## Project Structure

```
src/
  ├── AGENTS.md               ← Agent roster
  ├── SKILLS.md               ← Skill matrix
  ├── DECISION-MAKING.md      ← Routing logic
  ├── agents/                 ← Agent definitions
  └── skills/                 ← Skill implementations
renderer/
  ├── validate_agents.py      ← Agent validator
  └── validate_skills.py      ← Skill validator
tests/                         ← Test suite
Makefile                       ← Build targets (run `make help`)
```

---

## Help & Questions

- **How do I add an agent?** → Use `agent-creator` skill or see [`src/AGENTS.md`](src/AGENTS.md)
- **How do I add a skill?** → Use `skill-creator` skill or see [`src/SKILLS.md`](src/SKILLS.md)
- **What are the test commands?** → See "Test Suite" above or run `make help`
- **What's the commit format?** → See "Conventional Commit Format" above
- **What if my PR fails CI?** → Run `make verify` locally; it checks everything CI checks

---

**Ready to start?** Clone the repo, run `make install && make verify`, and make your first contribution using the framework's own meta-skills.
