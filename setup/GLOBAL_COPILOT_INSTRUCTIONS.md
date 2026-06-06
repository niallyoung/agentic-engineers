# Global Copilot Instructions

## Session Initialization (RUN AT STARTUP)

**When**: Every new session, before any other work
**What**: `bash agentic-engineers/setup/session-init.sh`

This initializes:
- ✅ Token usage tracking (automatic, no action needed)
- ✅ Budget monitoring (GREEN/YELLOW/RED status)
- ✅ Baseline metrics

**Safe to run multiple times** — checks if already initialized and skips.

---

## Enforcement Rules (NON-NEGOTIABLE)
1. **Never use `--no-verify`** on git commands. Commit hooks must always run.
2. **Never modify `~/.github/hooks/`**, `~/.github/scripts/`, or the `{service-name}` repo.
3. **Run `make check` or `make ci`** before committing when a Makefile exists.
4. **Never force-push** without explicit user approval.

## Workflow
Every project should have a Makefile. Standard targets:
- `make ci` — full local pipeline
- `make check` — project-specific validation
- `make lint` — linting
- `make help` — show available targets
