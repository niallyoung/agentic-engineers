# Skill Creation Guide

This guide explains how to create new skills in the Agentic Engineers framework.

## Overview

Skills are reusable capabilities that agents can invoke to accomplish specific tasks. Skills can be:
- **Operational tools** (queue management, file operations)
- **Analysis capabilities** (code review, metrics aggregation)
- **Integrations** (API clients, external services)
- **Utilities** (formatters, validators)

## Quick Start

Use the `skill-creator` skill to scaffold a new skill:

```bash
python3 scripts/skill-creator.py --name "database-migration" --category "infrastructure"
```

This generates:
- `src/skills/database-migration/SKILL.md` — Skill specification
- `src/skills/database-migration/scripts/main.py` — Implementation
- `tests/skills/test_database_migration.py` — Test scaffolds

## Skill Structure

### 1. Skill Specification (`SKILL.md`)

Every skill has a frontmatter block following the [agentskills.io](https://agentskills.io) specification:

```yaml
---
name: database-migration
version: 1.0.0
description: Database schema migration and rollback management
category: infrastructure
tags: [database, migration, schema]
dependencies: []
author: your-name
license: MIT
---

# Database Migration Skill

Manages database schema migrations with rollback support.

## Usage

```bash
# Apply migrations
python3 scripts/main.py apply --migration 001_add_users_table.sql

# Rollback
python3 scripts/main.py rollback --steps 1

# Status
python3 scripts/main.py status
```

## API

### `apply(migration_file: str) -> dict`

Applies a migration file to the database.

**Parameters:**
- `migration_file` — Path to SQL migration file

**Returns:**
```json
{
  "status": "success",
  "migration": "001_add_users_table.sql",
  "applied_at": "2026-06-06T16:00:00Z"
}
```

### `rollback(steps: int = 1) -> dict`

Rolls back the last N migrations.

**Parameters:**
- `steps` — Number of migrations to roll back (default: 1)

**Returns:**
```json
{
  "status": "success",
  "rolled_back": ["001_add_users_table.sql"]
}
```
```

### 2. Implementation (`scripts/main.py`)

```python
#!/usr/bin/env python3
"""
Database Migration Skill
Manages schema migrations with rollback support.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Any


class MigrationManager:
    """Manages database schema migrations."""
    
    def __init__(self, migrations_dir: Path):
        self.migrations_dir = migrations_dir
        self.applied_migrations_file = migrations_dir / ".applied"
    
    def apply(self, migration_file: str) -> Dict[str, Any]:
        """Apply a migration."""
        # Implementation here
        return {
            "status": "success",
            "migration": migration_file,
            "applied_at": "2026-06-06T16:00:00Z"
        }
    
    def rollback(self, steps: int = 1) -> Dict[str, Any]:
        """Rollback N migrations."""
        # Implementation here
        return {
            "status": "success",
            "rolled_back": ["001_add_users_table.sql"]
        }
    
    def status(self) -> Dict[str, Any]:
        """Get migration status."""
        # Implementation here
        return {
            "total": 5,
            "applied": 3,
            "pending": 2
        }


def main():
    parser = argparse.ArgumentParser(description="Database migration management")
    subparsers = parser.add_subparsers(dest="command")
    
    # Apply command
    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--migration", required=True)
    
    # Rollback command
    rollback_parser = subparsers.add_parser("rollback")
    rollback_parser.add_argument("--steps", type=int, default=1)
    
    # Status command
    subparsers.add_parser("status")
    
    args = parser.parse_args()
    
    manager = MigrationManager(Path("migrations"))
    
    if args.command == "apply":
        result = manager.apply(args.migration)
    elif args.command == "rollback":
        result = manager.rollback(args.steps)
    elif args.command == "status":
        result = manager.status()
    else:
        parser.print_help()
        sys.exit(1)
    
    print(f"Status: {result['status']}")
    return 0 if result['status'] == 'success' else 1


if __name__ == "__main__":
    sys.exit(main())
```

### 3. Tests (`tests/skills/test_database_migration.py`)

```python
import pytest
from pathlib import Path
from src.skills.database_migration.scripts.main import MigrationManager


def test_apply_migration(tmp_path):
    """Test applying a migration."""
    manager = MigrationManager(tmp_path)
    result = manager.apply("001_add_users_table.sql")
    assert result["status"] == "success"
    assert result["migration"] == "001_add_users_table.sql"


def test_rollback_migration(tmp_path):
    """Test rolling back a migration."""
    manager = MigrationManager(tmp_path)
    # Apply first
    manager.apply("001_add_users_table.sql")
    # Then rollback
    result = manager.rollback(steps=1)
    assert result["status"] == "success"
    assert "001_add_users_table.sql" in result["rolled_back"]


def test_migration_status(tmp_path):
    """Test getting migration status."""
    manager = MigrationManager(tmp_path)
    result = manager.status()
    assert "total" in result
    assert "applied" in result
    assert "pending" in result
```

## Skill Categories

| Category | Purpose | Examples |
|----------|---------|----------|
| **orchestration** | Task routing and coordination | queue-management, delegation |
| **quality** | Code review and validation | spec-validator, test-sync |
| **cost** | Cost tracking and optimization | usage-tracking, tokenadvisor |
| **infrastructure** | System operations | file-sync, cicd-monitor |
| **analytics** | Metrics and reporting | metrics-etl, ab-testing |
| **integration** | External service APIs | github-api, slack-notify |

## Dependencies

Skills can depend on other skills. Declare dependencies in `SKILL.md`:

```yaml
---
name: advanced-queue-ops
dependencies:
  - queue-management  # Core queue operations
  - protocol-validator  # DELEGATE/HANDBACK validation
---
```

**Circular dependency detection:** The framework validates dependency graphs at install time and rejects circular dependencies.

## Testing Your Skill

### 1. Unit Tests

```bash
pytest tests/skills/test_database_migration.py -v
```

### 2. Integration Tests

```bash
# Test via agent invocation
opencode --agent engineer --skill database-migration "Apply migration 001"
```

### 3. Validation

```bash
# Run skill validator
python3 scripts/validate-skill.py database-migration
# Checks:
# - SKILL.md frontmatter valid
# - scripts/main.py exists and executable
# - Tests pass
# - No circular dependencies
```

## Best Practices

1. **Single Purpose** — Each skill should do one thing well
2. **Clear API** — Document all functions, parameters, and return types
3. **Error Handling** — Return structured error responses (status, message, details)
4. **Testing** — Write comprehensive unit and integration tests
5. **Documentation** — Include usage examples in SKILL.md
6. **Versioning** — Follow semantic versioning (1.0.0, 1.1.0, 2.0.0)

## Skill Naming Conventions

**Good names:**
- `database-migration` — Clear, specific
- `token-usage-tracking` — Descriptive
- `cicd-monitor` — Concise, unambiguous

**Bad names:**
- `db-mig` — Too abbreviated
- `helper` — Too generic
- `utils` — Not specific

## Adding Skills to Agents

Agents can invoke skills via the `skill` tool. Example in agent system prompt:

```markdown
## Available Skills

- `database-migration` — Manages schema migrations
- `queue-management` — Queue operations (DELEGATE/HANDBACK)
- `usage-tracking` — Token usage capture and analysis

## Usage

When you need to apply a database migration:
1. Invoke the `database-migration` skill
2. Pass migration file path
3. Verify success before proceeding
```

## Skill Distribution

Skills are installed per-harness via the renderer pipeline:

```bash
# Install skills to OpenCode
make install-opencode
# Copies skills to ~/.opencode/skills/

# Install skills to Copilot
make install-copilot
# Copies skills to ~/.copilot/skills/
```

## Examples

### Example 1: Simple Utility Skill

```yaml
---
name: json-formatter
version: 1.0.0
description: JSON formatting and validation
category: utilities
tags: [json, formatter]
dependencies: []
---
```

```python
def format_json(data: str) -> Dict[str, Any]:
    """Format and validate JSON."""
    try:
        parsed = json.loads(data)
        formatted = json.dumps(parsed, indent=2)
        return {"status": "success", "formatted": formatted}
    except json.JSONDecodeError as e:
        return {"status": "error", "message": str(e)}
```

### Example 2: Integration Skill

```yaml
---
name: slack-notify
version: 1.0.0
description: Send notifications to Slack channels
category: integration
tags: [slack, notification]
dependencies: []
---
```

```python
def send_notification(channel: str, message: str) -> Dict[str, Any]:
    """Send a Slack notification."""
    # Implementation using Slack API
    return {"status": "success", "message_id": "12345"}
```

## Troubleshooting

### Skill not found

**Symptom:** `Error: Skill 'your-skill' not found`

**Fix:**
1. Check skill exists in `src/skills/your-skill/`
2. Verify `SKILL.md` has correct name in frontmatter
3. Run `make install-{harness}` to copy skills

### Circular dependency detected

**Symptom:** `Error: Circular dependency: skill-a → skill-b → skill-a`

**Fix:**
1. Review dependency chain in `SKILL.md` files
2. Refactor to break circular dependency
3. Consider creating a third skill with shared logic

### Skill fails in specific harness

**Symptom:** Skill works in OpenCode but fails in Copilot

**Fix:**
1. Check harness-specific compatibility (file paths, API formats)
2. Review harness limitations (e.g., Copilot has 4K context limit)
3. Add harness-specific handling if needed

## Next Steps

- [Agent Creation Guide](agent-creation.md)
- [Harness Setup](harness-setup/)
- [Testing Guide](troubleshooting.md)
