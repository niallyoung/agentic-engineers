# Agent & Integration Renderers

Renders agentic-engineers configurations for different tools:
- **Copilot CLI** (`~/.copilot/agents/`)
- **π.dev Harness** (`~/.pi/agent/`)
- **Codex** (`~/.codex/agents/`, `~/.codex/skills/`)

## Quick Start

### For π.dev (Recommended)

```bash
python3 renderer/scripts/render-pi-dev.py
```

Renders agentic-engineers system prompt and agent roles into `~/.pi/agent/`. Then:

```bash
cd /your/project
pi
# Now running with agentic-engineers identity & agent roles
```

See [PI-DEV-RENDERER.md](./PI-DEV-RENDERER.md) for full documentation.

### For Copilot CLI (Legacy)

```bash
python3 renderer/scripts/render-copilot-agents.py
```

Renders agentic-engineers agent definitions into `~/.copilot/agents/`.

## Structure

```
renderer/
├── pi-dev-src/                      — π.dev config sources
│   ├── SYSTEM.md                    — System prompt (replaces π.dev default)
│   ├── AGENTS.md                    — Agent role definitions
│   └── settings.json                — Model/UI defaults
│
├── scripts/
│   ├── render-pi-dev.py             — π.dev renderer (NEW)
│   ├── render-codex.py              — Codex renderer
│   └── render-copilot-agents.py     — Copilot CLI renderer
│
├── PI-DEV-RENDERER.md               — π.dev integration guide
├── instructions/                    — Global instructions
├── hooks/                           — Enforcement hooks
└── README.md                        — This file
```

## Renderers

### π.dev Renderer

**What**: Renders agentic-engineers into π.dev harness
**How**: `python3 renderer/scripts/render-pi-dev.py`
**Where**: `renderer/pi-dev-src/` → `~/.pi/agent/`
**Docs**: [PI-DEV-RENDERER.md](./PI-DEV-RENDERER.md)

**Key features**:
- 100% system prompt control from bootstrap
- No π.dev forking required
- Works with standard `pi` binary (v0.74.0+)
- SYSTEM.md completely replaces π.dev default

**Files generated**:
- `~/.pi/agent/SYSTEM.md` — Master system prompt
- `~/.pi/agent/AGENTS.md` — Agent role context
- `~/.pi/agent/settings.json` — Model defaults

### Copilot CLI Renderer

**What**: Renders agentic-engineers agents for Copilot CLI
**How**: `python3 renderer/scripts/render-copilot-agents.py`
**Docs**: See script documentation

### Codex Renderer

**What**: Renders agentic-engineers custom agents, skills, and config for Codex
**How**: `make render-codex` for `dist/codex/`, or `make install-codex` for the explicit Codex install path
**Where**: `src/agents/` → `~/.codex/agents/`; `src/skills/` → `~/.codex/skills/`

Codex custom agents are TOML files and are spawned only when explicitly
requested by the user/session. The renderer installs a concise `AGENTS.md`
that preserves the Orchestrator-first DELEGATE/HANDBACK workflow.

## Maintenance

### Source Files

All source files are committed:
```bash
git log renderer/pi-dev-src/        # View history
git log renderer/scripts/render-*.py # View renderer history
```

### Rendered Output

Rendered files in `~/.pi/`, `~/.copilot/` are **local only** (not committed).

### Update Workflow

1. **Modify** source files in `renderer/pi-dev-src/` (or `src/agents/`)
2. **Render** with the appropriate renderer script
3. **Test** with pi or copilot CLI
4. **Commit** source file changes to git

Example:
```bash
# Edit system prompt
vim renderer/pi-dev-src/SYSTEM.md

# Render to ~/.pi/agent/
python3 renderer/scripts/render-pi-dev.py

# Test
pi "What can you do?"

# Commit source changes
git add renderer/pi-dev-src/SYSTEM.md
git commit -m "Update agentic-engineers system prompt"
```

## Integration Timeline

- **π.dev** (May 2026): Primary integration, full system prompt control
- **Copilot CLI** (ongoing): Agent definitions, custom agents

## See Also

- [PI-DEV-RENDERER.md](./PI-DEV-RENDERER.md) — π.dev integration guide
- [Global Enforcement Infrastructure](../setup/) — Copilot CLI enforcement hooks
