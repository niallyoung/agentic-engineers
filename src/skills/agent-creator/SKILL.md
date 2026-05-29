---
name: agent-creator
description: Scaffolds new SPEC-compliant agentic-engineers agents with a single call. Generates SKILL.md frontmatter, test scaffolds (TDD RED-phase), __init__.py, scripts/ layout, and DELEGATE/HANDBACK protocol templates. Use when creating any new automation agent, task handler, or operational tool. Validates role, model, effort, naming, and dependency graphs (circular dep detection) before writing files. Supports dry-run mode for planning without side effects.
license: Proprietary
compatibility: agentic-engineers framework v5.10+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: orchestration
  role: senior-engineer
  model: claude-sonnet-4.6
  effort: medium
  thinking: false
---

# agent-creator

## Overview

Automates creation of new agent templates that are immediately SPEC-compliant and ready for TDD-driven development.

**What it does:**
1. Validates config (name pattern, role enum, model enum, effort enum)
2. Checks dependency graph — detects circular dependencies before writing any files
3. Verifies integration — naming conflicts, role/model compatibility warnings
4. Generates: `SKILL.md`, `__init__.py`, `scripts/__init__.py`, `tests/test_<agent>.py`
5. Embeds DELEGATE/HANDBACK protocol templates directly in `SKILL.md`
6. Returns `CreationResult` with SPAN metadata (timing, file count)

## Usage

### Python API (preferred)

```python
from src.skills.agent_creator import AgentConfig, AgentCreator
from pathlib import Path

cfg = AgentConfig(
    name="my-agent",
    role="engineer",
    description="Handles X and Y tasks.",
    model="claude-haiku-4.5",
    effort="low",
)

creator = AgentCreator(output_root=Path("src/skills"))
result = creator.create(cfg)
print(result)
# [SUCCESS] my-agent
#   deliverables: 4 files
```

### Dry-run (validate only, no file writes)

```python
result = creator.create(cfg, dry_run=True)
# Returns SUCCESS with planned deliverables but writes nothing to disk
```

### CLI

```bash
python src/skills/agent-creator/scripts/agent_creator.py \
  --name my-agent \
  --role engineer \
  --effort low \
  --description "Handles X and Y."

# Dry-run:
python src/skills/agent-creator/scripts/agent_creator.py \
  --name my-agent --role engineer --dry-run
```

## Configuration

| Parameter     | Type    | Required | Default           | Allowed Values |
|---------------|---------|----------|-------------------|----------------|
| `name`        | str     | ✅       | —                 | `^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]?$` |
| `role`        | str     | ✅       | —                 | See [Allowed Roles](#allowed-roles) |
| `model`       | str     | ❌       | `claude-haiku-4.5` | See [Allowed Models](#allowed-models) |
| `effort`      | str     | ❌       | `low`             | `low`, `medium`, `high` |
| `thinking`    | bool    | ❌       | `false`           | `true`, `false` |
| `authority`   | str     | ❌       | `null`            | Any role name |
| `description` | str     | ❌       | `""`              | 0–1024 chars |
| `category`    | str     | ❌       | `orchestration`   | Any string |
| `dependencies`| list    | ❌       | `[]`              | List of existing agent names |
| `tools`       | list    | ❌       | `[]`              | List of tool names |
| `version`     | str     | ❌       | `"1.0"`           | Semantic version |

### Allowed Roles

- `engineer`
- `senior-engineer`
- `lead-engineer`
- `principal-engineer`
- `security-engineer`
- `quality-engineer`

### Allowed Models

- `claude-haiku-4.5` ← default (recommended for engineer role)
- `claude-sonnet-4.5`, `claude-sonnet-4.6` (recommended for senior/lead/quality)
- `claude-opus-4.8` (recommended for principal/security)
- `gpt-4o-mini`, `gpt-4`, `gpt-4o`, `gpt-4-turbo`
- `gemini-2.0-flash`, `gemini-1-5-pro`, `gemini-2-pro`

## Generated File Layout

```
src/skills/agent-creator/<agent-name>/
├── SKILL.md                          # Frontmatter + DELEGATE/HANDBACK templates
├── __init__.py                       # Package init with module docstring
├── scripts/
│   └── __init__.py                   # scripts package init
└── tests/
    └── test_<agent_name>.py          # TDD RED-phase test scaffold
```

## Validation Rules

### Name
- Lowercase alphanumeric + hyphens only
- No leading/trailing/consecutive hyphens (`--`)
- Max 64 characters
- Min 1 character

### Dependency Graph
- Circular dependencies are detected via DFS before any files are written
- Self-dependencies (`name` in own `dependencies`) are rejected
- Missing dependencies in provided graph are reported

### Integration
- Naming conflicts with existing agents produce a hard error
- Role/model tier mismatches (e.g. principal-engineer with haiku) produce a warning

## DELEGATE / HANDBACK Protocol

All generated agents inherit the DELEGATE/HANDBACK protocol. The `SKILL.md` for each
generated agent includes ready-to-use DELEGATE and HANDBACK YAML templates
pre-filled with the agent's role, model, and effort values.

## Output: CreationResult

```python
@dataclass
class CreationResult:
    status: CreationStatus        # SUCCESS | FAILED | DRY_RUN
    agent_name: str
    deliverables: List[str]       # Absolute file paths created
    errors: List[str]             # Non-empty → FAILED
    warnings: List[str]           # Non-fatal advisories
    span: Dict                    # {"files_created": N, "duration_ms": N}
```

## Tests

```bash
python3 -m pytest tests/test_agent_creator.py -v
# 100 tests, 98% coverage
```

## Integration

**Input:**  `AgentConfig` (Python) or CLI flags  
**Output:** Scaffolded agent directory + `CreationResult`  
**Used by:** Orchestrator when routing `DELEGATE` tasks for new agent creation  

## Scripts

- `agent_creator.py` — Core implementation (ConfigValidator, TemplateGenerator,
  DependencyValidator, IntegrationChecker, AgentCreator)
