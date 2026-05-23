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

## Testing

```bash
# Run all tests
python3 -m pytest tests/ -q

# With coverage
python3 -m pytest tests/ --cov=src --cov-report=term-missing -q
```

All new code must have tests. CI enforces >85% coverage.

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
