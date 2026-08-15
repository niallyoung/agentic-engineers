# Setup & Enforcement — Installation & Rules

**This directory contains setup instructions and enforcement rules for the agentic-engineers system.**

## Files

| File | Purpose |
|------|---------|
| **copilot-instructions.md** | Enforcement rules and auto-load mechanism. Required reading for all agents. |
| **GLOBAL_COPILOT_INSTRUCTIONS.md** | Global Copilot CLI enforcement rules. |

## Installation

### New Agent Setup

1. Read `copilot-instructions.md` (enforcement rules, learning path)
2. Load `agentic-engineers/` as a unit via CLAUDE.md auto-load
3. Read `src/AGENTS.md` (your role definition)
4. Reference `src/SKILLS.md` for available skills

### Hooks & Validation

- Pre-commit: `make lint` + `make test`
- Commit-msg: Conventional commit format enforcement
- Git workflow: SSH only, 1Password ssh-agent, no `--no-verify`

### Project Initialization

This system assumes:
- Git repository with pre-commit hooks installed
- agentic-engineers framework (CLAUDE.md, AGENTS.md, src/)
- Metrics collection to `~/.claude/metrics/`

## When You Need This

- **First time setting up?** Start with copilot-instructions.md
- **Debugging enforcement issues?** Check GLOBAL_COPILOT_INSTRUCTIONS.md
- **Understanding git rules?** See copilot-instructions.md (git workflow section)
- **Understanding the framework?** Start with the root [README.md](../README.md)

## See Also

- `src/AGENTS.md` — Agent roster and routing rules
- `src/SKILLS.md` — Available skills catalog
- `docs/SPEC.md` — Framework specification
