# Render Pipeline Documentation

## Overview

The render pipeline transforms source entity definitions into deployable artifacts across multiple targets (Copilot, Claude, OpenCode).

```
SOURCE → BUILD → DEPLOY → RUNTIME
  ↓        ↓        ↓         ↓
src/   dist/    ~/.copilot/ Copilot CLI
       agents    ~/.claude/  Claude CLI
       skills    ~/.opencode OpenCode
```

## Source Layer (Canonical)

**Location**: `src/agents/`, `src/skills/`, `src/orchestration/`

All entity definitions originate here. These are the authoritative versions tracked in git.

### Agents
- **Convention**: `*-agent.md` (e.g., `engineer-agent.md`)
- **Fields**: name, description, model, effort, type, instructions
- **Metadata**: Frontmatter YAML at top of file
- **Example**: `src/agents/engineer-agent.md`

### Skills
- **Convention**: `{skill-name}/SKILL.md` (e.g., `queue-management/SKILL.md`)
- **Fields**: name, description, type, tools, required_by
- **Metadata**: Frontmatter YAML in SKILL.md
- **Example**: `src/skills/queue-management/SKILL.md`

### Specs
- **Convention**: `*.yaml` in `src/orchestration/`
- **Examples**: `delegate-schema.yaml`, `handback-schema.yaml`
- **Purpose**: Validation schemas for protocol enforcement

## Build Layer

**Location**: `dist/{copilot|claude|opencode}/`

Build process generates deployment-ready artifacts from source:

```bash
# Render agents
renderer/scripts/render-copilot-agents.py

# Render skills
renderer/scripts/render-copilot.sh

# Render hooks
renderer/scripts/render-hooks.sh
```

### Naming Transformation

| Source | Target | Tool | Transform |
|--------|--------|------|-----------|
| `src/agents/engineer-agent.md` | `dist/copilot/agents/engineer-agent.agent.md` | `render-copilot-agents.py` | Add `.agent` to filename |
| `src/skills/queue-management/SKILL.md` | `dist/copilot/skills/queue-management/SKILL.md` | `render-copilot.sh` | Copy with marker |

## Deploy Layer

**Locations**: 
- `~/.copilot/agents/` — Copilot CLI agents
- `~/.copilot/skills/` — Copilot CLI skills
- `~/.claude/agents/` — Claude CLI agents
- `~/.claude/skills/` — Claude CLI skills

Deployment copies build artifacts to user environments. Installation via `make install`.

### Backward Compatibility

For Copilot CLI compatibility, symlinks are created:
- `engineer.agent.md` → `engineer-agent.agent.md` (symlink)
- Allows old naming convention to resolve to new canonical files

## Runtime Layer

Agents and skills are loaded by their respective CLIs at execution time.

**Copilot CLI**:
```bash
copilot task orchestrator # Loads ~/.copilot/agents/orchestrator.agent.md
```

**Claude CLI**:
```bash
claude-cli agent security-engineer # Loads ~/.claude/agents/security-engineer.md
```

## Unified Render Library

**Location**: `renderer/lib/render-lib.sh`

Common functions used by all render scripts:

### Functions

- `list_source_agents()` — Find all `*-agent.md` files
- `list_source_skills()` — Find all `*/SKILL.md` files
- `extract_fm()` — Extract YAML frontmatter from file
- `get_entity_name()` — Get `name:` field from frontmatter
- `validate_frontmatter()` — Verify required fields present
- `transform_entity_filename()` — Apply naming transformation
- `yaml_escape_inline()` — Escape YAML values safely

### Usage

```bash
#!/bin/bash
source renderer/lib/render-lib.sh

for agent_file in $(list_source_agents); do
  name=$(get_entity_name "$agent_file")
  validate_frontmatter "$agent_file"
  output_file=$(transform_entity_filename "$agent_file" "agents" ".agent")
  cp "$agent_file" "$output_file"
done
```

## Consistency Validation

### Framework Consistency Gates

6 gates prevent drift and enforce consistency:

1. **No Orphaned Agents** — All `src/agents/*-agent.md` listed in docs/AGENTS.md
2. **No Archived Deployed** — Stale agents never in user environments
3. **Skills Have Markers** — All skills have SKILL.md, no orphaned .md files
4. **Naming Consistency** — Source: `-agent.md`, Rendered: `.agent.md`
5. **Manifest Valid** — FRAMEWORK-MANIFEST.yaml structure and completeness
6. **No Duplicates** — No stale or duplicate files in deployments

### Running Gates

**Locally** (pre-commit):
```bash
pytest tests/test_framework_consistency.py -v
pytest tests/test_render_pipeline.py -v
```

**In CI** (GitHub Actions):
```bash
.github/workflows/framework-integrity.yml
```

**Via Makefile**:
```bash
make framework-validate      # Run all gates
make framework-audit         # Detailed report
make framework-clean-stale   # Remove stale files
```

## Migration Path: Fixing Naming Issues

If discovered that old naming convention exists in production:

```bash
# 1. Verify old files
find ~/.copilot/agents -name "*.agent.md" | grep -v "-agent.agent.md"

# 2. Create symlinks for backward compat
cd ~/.copilot/agents
ln -s engineer-agent.agent.md engineer.agent.md
ln -s lead-engineer-agent.agent.md lead-engineer.agent.md
# ... for all agents

# 3. Run gates to verify consistency
make framework-validate

# 4. Once stable, remove symlinks (optional, requires CLI update)
rm ~/.copilot/agents/*.agent.md  # Keep only canonical files
```

## Root Cause: Why Drift Happened

**Problem**: Renderer created new files but didn't clean old ones.

**Example**:
```
2026-05-03: Renderer creates:
  ~/.copilot/agents/engineer-agent.agent.md (NEW)
  
2026-05-24: Old files remain:
  ~/.copilot/agents/engineer.agent.md (OLD, from v0.1)
  
Result: 13 agents deployed instead of 8 (5 duplicates = 5 archived agents)
```

**Solution**: 
- FRAMEWORK-MANIFEST.yaml as source-of-truth
- Automated gates detect duplicates before they cause issues
- `make framework-clean-stale` removes orphaned files

## Recommended Workflow

1. **Update source** (`src/agents/*-agent.md`, `src/skills/*/SKILL.md`)
2. **Update FRAMEWORK-MANIFEST.yaml** (if adding new entities)
3. **Run gates locally** (`make framework-validate`)
4. **Render** (`make render`)
5. **Verify dist/** (`make framework-audit`)
6. **Commit & push** (CI gates re-validate)
7. **Install** (`make install`)
8. **Verify runtime** (agents load without errors)

## Testing the Render Pipeline

```bash
# Unit tests
pytest tests/test_render_pipeline.py -v

# Integration tests
bash renderer/scripts/render-copilot.sh src ~/.copilot --status

# Verify consistency
find src/agents -name "*-agent.md" | wc -l  # Should match deployed count
```
