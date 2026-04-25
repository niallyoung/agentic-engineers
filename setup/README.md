# Setup & Enforcement — Installation & Rules

**This directory contains setup instructions and enforcement rules for the agentic-engineers system.**

## Files

| File | Purpose |
|------|---------|
| **copilot-instructions.md** | Enforcement rules and auto-load mechanism. Required reading for all agents. |
| **GLOBAL_COPILOT_INSTRUCTIONS.md** | Global Copilot CLI enforcement rules (reference copy from {service-name}). |

## Installation

### New Agent Setup

1. Read `copilot-instructions.md` (enforcement rules, learning path)
2. Load `agentic-engineers/` as a unit via CLAUDE.md auto-load
3. Read `../orchestration/AGENTS.md` (your role definition)
4. Reference `../config/QUICK_REFERENCE.md` during task routing

### Hooks & Validation

- Pre-commit: `make lint` + `make test`
- Commit-msg: Conventional commit format enforcement
- Git workflow: SSH only, 1Password ssh-agent, no `--no-verify`

### Project Initialization

This system assumes:
- Git repository with pre-commit hooks installed
- ERS workspace context (CLAUDE.md, AGENTS.md, orchestration/)
- Metrics collection to `~/.claude/metrics/`

## When You Need This

- **First time setting up?** Start with copilot-instructions.md
- **Debugging enforcement issues?** Check GLOBAL_COPILOT_INSTRUCTIONS.md
- **Understanding git rules?** See copilot-instructions.md (git workflow section)
- **Configuring IDE/terminal?** Follow copylot-instructions.md

## See Also

- `../MANIFEST.md` — Complete file listing of entire system (discovery tool)
- `../config/MODEL_ASSIGNMENTS_LOCKED.md` — System configuration
- `../guides/CLAUDE.md` — Team context
- `../orchestration/AGENTS.md` — Role definitions
