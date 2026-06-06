# Global Copilot Instructions

## Enforcement Rules (NON-NEGOTIABLE)
1. **Never use `--no-verify`** on git commands. Commit hooks must always run.
2. **Never modify `~/.github/hooks/`** or **`~/.github/scripts/`** — enforcement infrastructure is protected.
3. **Run `make check` or `make ci`** before committing when a Makefile exists.
4. **Never force-push** without explicit user approval.

## Session Management
Maintain session state in TODO.md and monitor progress through the Orchestrator.

## Workflow
Every project should have a Makefile. Standard targets:
- `make ci` — full local pipeline
- `make check` — project-specific validation
- `make lint` — linting
- `make help` — show available targets

---

## Agent Framework (load agentic-engineers)

When working with multi-agent coordination, reference the framework:

```
load agentic-engineers
```

**Location**: `~/.agents/agentic-engineers/`

**Bootstrap file**: `~/.agents/agentic-engineers/SYSTEM.md` contains:
- 8 agent roles, models, and routing rules
- DELEGATE/HANDBACK protocol for explicit handoffs
- Quality gates and verification checklist
- Orchestration rules and best practices

### Key Roles

| Role | Model | Use Case |
|------|-------|----------|
| **Orchestrator** | Haiku 4.5 | Routing, checkpoints, delegation |
| **Engineer** | Haiku/Sonnet | Implementation, TDD |
| **Senior Engineer** | Sonnet | Complex code, architecture |
| **Lead Engineer** | Sonnet | Code review, quality |
| **Principal Engineer** | Opus | Design, strategy |
| **Security Engineer** | Sonnet | Threat modeling, audits |
| **Quality Engineer** | Sonnet | Testing, E2E verification |
| **Model Engineer** | Haiku | Metrics, optimization |

### Framework Files

- `SYSTEM.md` — Central bootstrap
- `orchestration/AGENTS.md` — Role definitions
- `orchestration/HANDOFF.md` — Protocol documentation
- `orchestration/QUALITY.md` — Quality gates
- `skills/usage-tracking/` — Token budget monitoring

### Explicit Handoff (DELEGATE/HANDBACK)

Use these markers when delegating work between agents:

```yaml
---
handoff_type: DELEGATE
task_id: 2026-04-25-task-name
role: [role]
model: [model]
budget_context:
  session_pct: XX%
  status: GREEN|YELLOW|RED
---
[context and success criteria]
```

Then handback with metrics:

```yaml
---
handoff_type: HANDBACK
task_id: 2026-04-25-task-name
status: complete|partial|blocked
metrics:
  tokens_consumed: XXXX
---
[results and next steps]
```

### Installation & Setup

Install framework to `~/.agents/`:

```bash
cd ~/git/agentic-engineers
make install
```

Optional: Add to shell startup (.zshrc/.bashrc):

```bash
if [ -f "$HOME/.agents/agentic-engineers/setup/session-init.sh" ]; then
    source "$HOME/.agents/agentic-engineers/setup/session-init.sh"
fi
```

Check usage budget:

```bash
bash ~/.agents/agentic-engineers/skills/usage-tracking/scripts/usage-tracking.sh analyze
```

### Repository

- Source: `~/git/agentic-engineers/`
- Remote: `git@github.com:{your-org}/agentic-engineers.git`
- See also: `~/.claude/` (Claude Code configuration)
