---
name: queue-management
description: Skill for automating task addition to both queue/ and TODO.md simultaneously. Enables one-command task queuing instead of manual DELEGATE + TODO.md entry creation.
license: Proprietary
compatibility: Designed for agentic-engineers framework (ERS platform)
metadata:
  author: agentic-engineers
  version: "1.0"
  category: task-management
  role: orchestrator
  model: claude-haiku-4.5
---

## Overview

Queue Management skill automates task queuing. Instead of manually creating both a DELEGATE JSON file and a TODO.md entry, users call this skill once and it handles both atomically.

**What it does:**
1. Parses task specifications (JSON or CLI args)
2. Validates against QUEUE-PROTOCOL format
3. Generates DELEGATE JSON file in `~/.copilot/queue/{session-id}/incoming/`
4. Adds entry to repo TODO.md (correct phase section)
5. Commits both files atomically in single git commit
6. Detects and prevents duplicate task_ids

**Why it matters:**
- Reduces manual work: one command instead of two file operations
- Ensures consistency: DELEGATE and TODO.md always in sync
- Atomic commits: both files or neither (no partial updates)
- Clear error handling: user-friendly validation messages

## Invocation

### CLI Interface

Add task via command-line arguments:
```bash
add-to-queue --task-id my-feature-001 \
  --role Engineer \
  --scope "Implement new authentication system" \
  --effort high \
  --priority high
```

Add task via JSON spec file:
```bash
add-to-queue --spec-file task-spec.json
```

### Programmatic Interface

```python
from queue_manager import QueueManager

qm = QueueManager()
spec = {
    "task_id": "feature-x-impl",
    "role": "Senior Engineer",
    "scope": "Implement feature X",
    "plan": ["Design API", "Implement", "Test"],
    "success_criteria": ["Tests pass", "Coverage 85%+"],
    "effort": "high",
}
result = qm.process_task(spec)
```

## Configuration

**Required Fields:**
- `task_id` — Kebab-case identifier (must be unique)
- `role` — Assignment role (Engineer, Senior Engineer, Lead Engineer, Principal Engineer, Quality Engineer, Security Engineer, etc.)
- `scope` — Task description
- `plan` — List of implementation steps (at least 1)
- `success_criteria` — List of success metrics (at least 1)

**Optional Fields:**
- `effort` — low, medium, high (default: medium)
- `priority` — low, normal, high (default: normal)
- `phase` — Phase number for TODO.md section (default: 2)
- `constraints` — List of constraints or limitations
- `context` — Additional context

**Directories:**
- Queue incoming: `~/.copilot/queue/{session-id}/incoming/`
- TODO.md: `{repo-root}/TODO.md`

## Features

### 1. Task Specification Parser

Accepts JSON or CLI arguments. Automatically provides defaults for optional fields.

```bash
add-to-queue --task-id test-feature --role Engineer --scope "Test feature"
# Uses defaults: effort=medium, priority=normal, plan=[scope], criteria=["Task completed"]
```

### 2. QUEUE-PROTOCOL Validator

Validates:
- All required fields present
- `task_id` is kebab-case (lowercase, numbers, hyphens only)
- `role` is in allowed list
- `plan` is not empty
- `success_criteria` is not empty

Error messages are clear and actionable:
```
❌ task_id must be kebab-case (lowercase letters, numbers, hyphens). Got: BadTaskID
```

### 3. DELEGATE Generator

Creates properly formatted DELEGATE JSON in queue/incoming/:
```json
{
  "task_id": "my-feature-001",
  "description": "Implement new authentication system",
  "role": "Engineer",
  "plan": ["Design API", "Implement", "Test"],
  "success_criteria": ["Tests pass", "Coverage 85%+"],
  "effort": "high",
  "priority": "high",
  "created_at": "2025-05-09T14:23:45.123456"
}
```

### 4. TODO.md Updater

Automatically adds entry to correct phase section with formatting:
```markdown
- [ ] **my-feature-001:** Implement new authentication system
  - Effort: high
  - Owner: Engineer
```

### 5. Git Integration

Commits both DELEGATE and TODO.md atomically:
```
queue: add task my-feature-001 to queue and TODO
```

If git fails, files are still created (with error in result).

### 6. Duplicate Detection

Checks for existing task_ids in:
- Queue directory (`~/.copilot/queue/{session-id}/incoming/`)
- TODO.md file

Rejects duplicates with clear error:
```
❌ Task ID 'duplicate-task' already exists in queue: ...queue/duplicate-task.json
```

### 7. CLI Interface

Main entry point: `add-to-queue` command with flexible arguments.

Supports both CLI args and JSON spec files for flexibility.

### 8. Error Handling

All errors have clear, actionable messages:
- **Validation errors:** Show exactly what's wrong (format, missing field, invalid value)
- **Duplicate errors:** Show where duplicate was found
- **File errors:** Show which file failed to read/write
- **Git errors:** Show what git command failed

## Integration

**Input:** Task specification (JSON or CLI args)  
**Output:** DELEGATE JSON file + TODO.md entry + git commit  
**Uses:** QUEUE-PROTOCOL validation, AGENTS.md role list  
**Used by:** Orchestrator, users (CLI), other skills  

**Workflow:**
1. User calls: `add-to-queue --task-id X --role Y --scope Z`
2. Skill parses → validates → checks duplicate
3. Skill generates DELEGATE JSON file
4. Skill adds TODO.md entry to correct phase
5. Skill commits both files atomically
6. User gets success message with file paths

## Scripts

- `queue_manager.py` — Core QueueManager class
- `cli.py` — CLI interface (add-to-queue command)

## Testing

**Test coverage:** 85%+ required

**Test categories:**
- Parsing (JSON, CLI args)
- Validation (all protocol rules)
- DELEGATE generation
- TODO.md updates
- Duplicate detection
- Git integration
- Error handling
- Full workflow integration

Run tests:
```bash
pytest tests/test_queue_management.py -v --cov=src/skills/queue_management
```
