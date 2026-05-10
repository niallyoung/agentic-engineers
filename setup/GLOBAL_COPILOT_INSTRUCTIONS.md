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
