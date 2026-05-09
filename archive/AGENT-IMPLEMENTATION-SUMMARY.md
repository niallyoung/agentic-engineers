# Copilot CLI Agents: Source-to-Render Implementation

**Status**: ✅ COMPLETE  
**Date**: 2026-05-02  
**Verification**: All 13 agents successfully rendered and deployable

## What Was Implemented

### 1. Canonical Source Definitions (`src/agents/`)

Created 13 agent definition files in `src/agents/`:

- **Core Agents** (4): engineer, senior-engineer, orchestrator, principal-engineer
- **Specialized Agents** (5): lead-engineer, security-engineer, quality-engineer, spec-engineer, healing-engineer
- **Support Agents** (4): model-engineer, metrics, testing, spec-engineer-orchestrator

Each source agent includes:
- YAML frontmatter (name, description, model)
- Detailed markdown prompt with responsibilities and workflows
- Escalation paths and decision criteria

### 2. Rendering Pipeline

**Components Created**:

1. **Python Renderer** (`renderer/scripts/render-copilot-agents.py`)
   - Reads source agents from `src/agents/`
   - Validates YAML frontmatter
   - Outputs Copilot CLI format to `~/.copilot/agents/`
   - Renames files with `.agent.md` suffix

2. **Shell Wrapper** (`renderer/scripts/render-copilot-agents.sh`)
   - Entry point for shell users
   - Handles path resolution
   - Sets appropriate permissions

3. **Makefile Target** (`renderer/Makefile`)
   - `make install` — Render agents + install to all targets (main entry point)
   - `make install-copilot` — Render agents + install to Copilot CLI
   - `make install-claude` — Render agents + install to Claude Code
   - Integrated with existing build system

### 3. Rendered Output (`~/.copilot/agents/`)

All 13 agents rendered to Copilot CLI format:
- 13 files as `*.agent.md`
- 100% YAML frontmatter compliance
- Spec-compliant for Copilot CLI discovery
- All prompts under 30KB limit

### 4. Documentation

Created three comprehensive guides:

1. **AGENT-RENDERING-PIPELINE.md** (repo root)
   - Architecture and data flow
   - Rendering process explanation
   - Workflow for updates
   - Troubleshooting guide

2. **src/agents/README.md** (source directory)
   - Source structure and format
   - Agent categories
   - Model assignment rationale
   - Editing and adding agents
   - YAML frontmatter requirements

3. **~/.copilot/agents/README.md** (deployed directory)
   - Agent overview
   - Usage in Copilot CLI
   - Specification compliance
   - Model selection guide

## Key Features

### ✅ Single Source of Truth
- All agents defined once in `src/agents/`
- No manual editing of rendered files
- Changes propagate via rendering

### ✅ Reproducible Builds
- Rendering is deterministic
- Re-running produces identical output
- Safe to delete and recreate agents

### ✅ Spec Compliance
- All agents follow Copilot CLI custom agent specification
- Valid YAML frontmatter with required fields
- Correct naming convention (*.agent.md)
- Prompt content under 30KB limit

### ✅ Integration Ready
- Works with `/agent` slash command
- Works with `--agent` CLI flag
- Auto-discovery in prompts
- Verified with Copilot CLI v1.40+

## Verification Results

```
✅ 13/13 agents rendered successfully
✅ 13/13 agents have valid YAML frontmatter
✅ 13/13 agents follow naming convention
✅ 13/13 agents have Copilot CLI compliance
✅ Renderer successfully tested in 2+ cycles
✅ Re-render cycle confirmed idempotent
✅ All documentation created and linked
```

## Files Created/Modified

### New Files
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
├── spec-engineer-orchestrator.md
└── README.md

renderer/scripts/
├── render-copilot-agents.py (1,340 lines)
└── render-copilot-agents.sh (40 lines)

Documentation:
├── AGENT-RENDERING-PIPELINE.md (5,282 chars)
└── src/agents/README.md (5,881 chars)
```

### Modified Files
```
renderer/Makefile
├── Added: render-agents target
├── Updated: install-copilot to depend on render-agents
├── Updated: documentation comments
```

## Usage

### For Developers

**Edit an agent**:
```bash
vim src/agents/engineer.md
```

**Install agents and all configurations**:
```bash
make install
```

This single command:
- Renders agents from `src/agents/` to `~/.copilot/agents/` (Copilot CLI format)
- Installs all skills to `~/.copilot/skills/`
- Renders agents to `~/.claude/agents/` (Claude Code format)
- Installs all skills to `~/.claude/skills/`

**Test with Copilot CLI**:
```bash
copilot --agent=engineer --prompt "..."
```

### For Copilot CLI Users

**Select agent interactively**:
```bash
copilot
> /agent
# Select from 13 available agents
```

**Explicit agent selection**:
```bash
copilot --agent=engineer --prompt "Fix the token timeout"
```

**Auto-inference in prompts**:
```bash
copilot --prompt "Use the security-engineer to review this for vulnerabilities"
```

## Future Enhancements

Possible improvements (not in scope):
1. Multi-provider support (same source → multiple providers)
2. Agent inheritance/composition
3. Automated agent testing
4. Agent performance tracking
5. Dynamic model selection based on metrics

## References

- [GitHub Copilot CLI Documentation](https://docs.github.com/en/copilot/how-tos/copilot-cli)
- [Custom Agents Specification](https://docs.github.com/en/copilot/reference/custom-agents-configuration)
- `AGENT-RENDERING-PIPELINE.md` — Detailed rendering documentation
- `src/agents/README.md` — Source agent documentation
- `~/.copilot/agents/README.md` — Deployed agent documentation

## Conclusion

All agent definitions are now:
- **Captured in source** (`src/agents/*.md`)
- **Rendered to Copilot CLI format** (`~/.copilot/agents/*.agent.md`)
- **Ready for deployment and use**
- **Documented for maintenance**

Re-rendering the agents is as simple as:
```bash
make install
```

This ensures that if `~/.copilot/agents` or `~/.claude/agents` is deleted or modified, running install will recreate identical agents from source.
