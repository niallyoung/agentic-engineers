# Agent Rendering Pipeline

This document explains how agent definitions flow from source to deployment for GitHub Copilot CLI.

## Architecture

```
src/agents/*.md (canonical source)
         ↓
    [render-copilot-agents.py]
         ↓
~/.copilot/agents/*.agent.md (Copilot CLI format)
         ↓
    [Copilot CLI uses agents]
```

## Source of Truth: `src/agents/`

All agent definitions are stored in canonical format in the repository:

```
src/agents/
├── engineer.md
├── senior-engineer.md
├── orchestrator.md
├── principal-engineer.md
├── lead-engineer.md
├── security-engineer.md
├── quality-engineer.md
├── model-engineer.md
├── metrics.md
├── testing.md
├── spec-engineer.md
├── healing-engineer.md
└── spec-engineer-orchestrator.md
```

Each file includes:
- **YAML Frontmatter** (name, description, model)
- **Markdown Prompt** (agent behavior and responsibilities)

Example structure:
```markdown
---
name: Engineer
description: Executes well-scoped implementation tasks
model: claude-haiku-4-5
---

# Engineer Agent

You are an Engineer specialized in...

## Your Responsibilities
...
```

## Rendering: `src/agents/` → `~/.copilot/agents/`

The rendering pipeline converts canonical agent definitions to Copilot CLI format:

### 1. Python Renderer (`renderer/scripts/render-copilot-agents.py`)

**Purpose**: Convert source agents to Copilot CLI agent profiles

**Process**:
1. Read each source agent file (`engineer.md`)
2. Extract and validate YAML frontmatter
3. Ensure required fields (name, description, model)
4. Rename file with `.agent.md` suffix (`engineer.agent.md`)
5. Write to destination directory

**Usage**:
```bash
python3 renderer/scripts/render-copilot-agents.py [src_dir] [dest_dir]

# Defaults: src_dir=src/agents, dest_dir=~/.copilot/agents
python3 renderer/scripts/render-copilot-agents.py
```

### 2. Shell Wrapper (`renderer/scripts/render-copilot-agents.sh`)

**Purpose**: Convenient entry point with proper paths

**Usage**:
```bash
bash renderer/scripts/render-copilot-agents.sh
```

### 3. Makefile Target (`renderer/Makefile`)

**Purpose**: Integrate with standard build workflow

**Usage**:
```bash
make install                # Render agents + install to Copilot & Claude (main entry point)
make install-copilot        # Render agents + install to Copilot CLI
make install-claude         # Render agents + install to Claude Code
make install-all            # Install to Copilot, Claude, and GitHub directories
make status                 # Show drift report across all targets
make uninstall-copilot      # Remove Copilot agents/skills
make uninstall-claude       # Remove Claude agents/skills
make uninstall-all          # Remove all installations
```

## Output: `~/.copilot/agents/*.agent.md`

Rendered agents are ready for Copilot CLI:

```
~/.copilot/agents/
├── README.md
├── engineer.agent.md
├── senior-engineer.agent.md
├── orchestrator.agent.md
├── principal-engineer.agent.md
├── lead-engineer.agent.md
├── security-engineer.agent.md
├── quality-engineer.agent.md
├── model-engineer.agent.md
├── metrics.agent.md
├── testing.agent.md
├── spec-engineer.agent.md
├── healing-engineer.agent.md
└── spec-engineer-orchestrator.agent.md
```

Each file follows Copilot CLI spec:
- Named as `*.agent.md`
- YAML frontmatter with: name, description, model
- Prompt content (markdown body)

## Workflow for Updates

When updating agents:

1. **Edit source file**:
   ```bash
   vim src/agents/engineer.md
   ```

2. **Install to all targets** (renders and installs):
   ```bash
   make install
   ```
   This renders agents from `src/agents/` and installs to:
   - `~/.copilot/agents/` (Copilot CLI)
   - `~/.copilot/skills/` (Copilot CLI skills)
   - `~/.claude/agents/` (Claude Code)
   - `~/.claude/skills/` (Claude Code skills)

3. **Test with Copilot CLI**:
   ```bash
   copilot --agent=engineer --prompt "..."
   /agent  # Select in interactive mode
   ```

4. **Commit changes**:
   ```bash
   git add src/agents/engineer.md
   git commit -m "Update engineer agent"
   ```

## Design Principles

1. **Single Source of Truth**: All agent definitions in `src/agents/`
2. **Stateless Rendering**: Renderer is deterministic, no state
3. **No Manual Edits in ~/.copilot/agents/**: Files are generated, not edited
4. **Reproducible Builds**: Running render-agents always produces identical output
5. **Spec Compliant**: Output always matches Copilot CLI requirements

## Validation

The rendering pipeline validates:

- **Frontmatter Presence**: All files must start with `---`
- **Required Fields**: name, description, model must be present
- **File Naming**: Output uses `*.agent.md` suffix
- **Directory Structure**: Creates `~/.copilot/agents/` if needed

## CI/CD Integration

To include agent rendering in CI/CD:

```bash
# GitHub Actions example
- name: Install and Render Agents
  run: make install

- name: Verify agents
  run: |
    test -d ~/.copilot/agents/
    test -f ~/.copilot/agents/engineer.agent.md
```

## Troubleshooting

### Agents not updating
1. Edit source in `src/agents/`
2. Run `make install` (rendering is automatic)
3. Verify output in `~/.copilot/agents/`

### Render script fails
1. Check Python 3 is installed: `python3 --version`
2. Check source directory exists: `ls src/agents/`
3. Check write permissions: `touch ~/.copilot/agents/.test`

### Copilot CLI not finding agents
1. Verify agents exist: `ls ~/.copilot/agents/*.agent.md`
2. Check Copilot CLI version: `copilot --version` (should be v1.40+)
3. Verify agent format: `head -5 ~/.copilot/agents/engineer.agent.md`

## See Also

- [GitHub Copilot CLI Documentation](https://docs.github.com/en/copilot/how-tos/copilot-cli)
- [Custom Agents Specification](https://docs.github.com/en/copilot/reference/custom-agents-configuration)
- `renderer/README.md` — Renderer overview
- `src/agents/README.md` — Agent definitions overview
