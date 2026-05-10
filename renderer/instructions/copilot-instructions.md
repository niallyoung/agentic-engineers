# Global Copilot Instructions

## Enforcement Rules (NON-NEGOTIABLE)
1. **Never use `--no-verify`** on git commands. Commit hooks must always run.
2. **Never modify `~/.github/hooks/`** or **`~/.github/scripts/`** — enforcement infrastructure is protected.
3. **Run `make check` or `make ci`** before committing when a Makefile exists.
4. **Never force-push** without explicit user approval.

## Voice Notifications (NON-NEGOTIABLE)
Call `~/.copilot/scripts/voice-notify.sh <voice_key> "message"` at every milestone.
**Always pass the correct voice_key** — never omit it or use a generic default.

The `<voice_key>` can be an agent type, character name, or skill name. The script resolves all three.

### Characters = SDLC Archetypes

| Character      | Archetype       | When to use                          |
|----------------|-----------------|--------------------------------------|
| **Scout**      | Discovery       | Exploring, searching, status checks  |
| **Architect**  | Design          | Planning, infra, system design       |
| **Builder**    | Construction    | Writing code, creating artifacts     |
| **Inspector**  | Quality         | Code review, testing, validation     |
| **Oracle**     | Orchestration   | Multi-step coordination, general     |
| **Cheer**      | Success         | Commits, pushes, tests pass          |
| **Gloom**      | Failure         | Errors, build failures               |

### Skill → Default Character

| Skills                                                    | Character      |
|-----------------------------------------------------------|----------------|
| {example-service}, {example-service}-consumer, {example-service}, {example-service} | **Builder** |
| docx, xlsx, pdf, pptx, marp-slides, frontend-design      | **Builder**    |
| btc-cracker, btc-generator, claude-api, theme-factory     | **Builder**    |
| {example-service}, {example-service}, customize-cloud-agent        | **Architect**  |
| skill-creator, mcp-builder, brand-guidelines              | **Architect**  |
| {example-service}, webapp-testing                                | **Inspector**  |
| doc-coauthoring, internal-comms                           | **Oracle**     |
| linux-progress, btc-pipeline                              | **Scout**      |

### Override Rules
1. **Error/Success always win** — failures → Gloom, milestones → Cheer
2. **Activity trumps skill default** — reviewing in {example-service} → Inspector
3. **Planning → Architect** — even within a Builder skill
4. **Exploring → Scout** — even within a Builder skill
5. **Skill default** — when no override applies
6. **Oracle** — fallback when nothing else matches

### Message Rules
1. Match the voice_key to what you are currently doing, not a fixed default.
2. Keep messages under 15 words, natural phrasing.
3. First call in a session: lead with character name ("Builder here. Starting fixes.").

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
