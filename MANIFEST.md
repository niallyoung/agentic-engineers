# Agentic Engineers Framework — Manifest

**Version:** 1.0  
**Last Updated:** 2026-06-09  
**Registry:** Framework component inventory and entry points

---

## Framework Overview

Distributed AI orchestration system for multi-agent task delegation via queue-based DELEGATE/HANDBACK protocol. All work flows through `~/.agentic-engineers/{session-id}/{harness}/queue/`.

**Installation:** See [`docs/INSTALLATION.md`](docs/INSTALLATION.md)  
**Agent Roles:** See `src/AGENTS.md`  
**Skills:** See `src/SKILLS.md`

---

## Installed Components

### Core Agents (8 roles)

| Agent | Model | Purpose |
|---|---|---|
| Orchestrator | claude-haiku-4.5 | Routing & queue management |
| Engineer | claude-haiku-4.5 | Implementation (well-scoped) |
| Senior Engineer | claude-sonnet-4.5 | Complex problem-solving |
| Lead Engineer | claude-sonnet-4.6 | Code review & quality |
| Quality Engineer | claude-sonnet-4.6 | Post-implementation verification |
| Principal Engineer | claude-opus-4.6 | Cross-service architecture |
| Security Engineer | claude-opus-4.8 | Security & threat modeling |
| Model Engineer | claude-sonnet-4.5 | Cost/quality optimization |

See `src/AGENTS.md` for full documentation.

### Skill List (26 skills)

**Task Management**
- queue-management (queue operations, isolation)
- queue-query (queue inspection)
- queue-todo-sync (TODO.md ↔ queue sync)

**Quality & Validation**
- protocol-validator (DELEGATE/HANDBACK schema)
- consistency-checker (queue integrity)
- spec-validator (SPEC.md compliance)

**Optimization**
- ab-testing (experiment orchestration, traffic allocation, statistical analysis)
- model-engineer (cost/quality analysis)
- model-selection (routing recommendations)
- cost-aggregation (multi-provider costs)
- local-model-runtime (Ollama routing)
- metrics-etl (metrics pipeline)
- tokenadvisor (token efficiency)

**Automation & Setup**
- agent-creator (new agent scaffolding)
- skill-creator (new skill scaffolding)
- repo-init (repo initialization)
- spec-management (SPEC.md updates)

**Monitoring & Integration**
- doc-quality-monitor (documentation health)
- file-sync (script integration scoring)
- harness-integration-tracker (harness drift detection)
- harness-opencode-feature-sync (OpenCode sync)
- metrics-etl (metrics pipeline)
- usage-tracking (token metrics)

**Review & Workflows**
- workflow-review (pipeline analysis)

See `src/SKILLS.md` for full documentation.

### Harnesses (4 supported)

| Harness | Provider | Config Path | Queue Path |
|---|---|---|---|
| Claude | Anthropic Claude | `~/.claude/` | `~/.agentic-engineers/{session-id}/claude/queue/` |
| Copilot | GitHub Copilot | `~/.copilot/` | `~/.agentic-engineers/{session-id}/copilot/queue/` |
| OpenCode | Anthropic OpenCode | `~/.config/opencode/` | `~/.agentic-engineers/{session-id}/opencode/queue/` |
| π.dev | π.dev | `~/.pi/` | `~/.agentic-engineers/{session-id}/pi/queue/` |

### Queue Structure (Canonical)

```
~/.agentic-engineers/
└── {session-id}/                # UUID per session
    ├── claude/
    │   └── queue/
    │       ├── incoming/        # New tasks (DELEGATE)
    │       ├── processing/      # Work-in-progress
    │       ├── done/            # Completed tasks
    │       └── failed/          # Error cases
    ├── copilot/
    │   └── queue/ ...
    ├── opencode/
    │   └── queue/ ...
    └── pi/
        └── queue/ ...
```

See `docs/QUEUE-PROTOCOL.md` for full specification.

---

## Entry Points

### Command-Line

```bash
# Session initialization (run at CLI startup)
bash setup/session-init.sh

# Makefile targets
make install              # Install to all 4 harnesses
make status              # Check installation status
make verify              # Full framework verification
make test                # Run test suite
```

### Harness-Specific

- **Claude Code:** Automatic on session init (if detected)
- **Copilot CLI:** Via `copilot-instructions.md`
- **OpenCode:** Via `setup/` configuration
- **π.dev:** Via `~/.pi/` config

---

## Specification Documents

- `SPEC.md` — Core framework specification (LOCKED)
- `docs/QUEUE-PROTOCOL.md` — Queue mechanics & paths (LOCKED)
- `src/AGENTS.md` — Agent roster & delegation protocol
- `src/SKILLS.md` — Skill registry & documentation
- `docs/AGENTS.md` — Detailed agent definitions
- `docs/INSTALLATION.md` — Install guide (all harnesses)
- `docs/CONTRIBUTING/README.md` — Contributing guidelines

---

## Framework Version & Status

- **Version:** 1.0
- **Status:** Production (LOCKED specifications as of 2026-05-26)
- **Last Verified:** 2026-06-09
- **Queue Path:** Canonical = `~/.agentic-engineers/{session-id}/{harness}/queue/`

---

## Quick Start

1. **Initialize framework:**
   ```bash
   bash setup/session-init.sh
   ```

2. **Install to harnesses:**
   ```bash
   make install
   ```

3. **Verify installation:**
   ```bash
   make status
   ```

4. **Create test session:**
   ```bash
   make create-test-session AGENTIC_SESSION_ID=test-001 AGENTIC_HARNESS=local
   ```

5. **View queue:**
   ```bash
   ls ~/.agentic-engineers/test-001/local/queue/incoming/
   ```

---

**Managed by:** agentic-engineers framework  
**Do not edit directly** (use `spec-management` skill for changes)
