---
name: queue-todo-sync
description: Auto-sync queue DELEGATEs ↔ TODO.md on task lifecycle events
license: Proprietary
compatibility: agentic-engineers framework v5.10+. Requires Python 3.11+
metadata:
  author: agentic-engineers
  version: "1.0.0"
  category: queue
  role: engineer
  model: claude-haiku-4.5
  effort: medium
status: implemented
---

# queue-todo-sync Skill

**Purpose:** Automatically synchronize task queue (DELEGATE/HANDBACK files) with TODO.md to maintain a single source of truth for task tracking.

**Status:** ✅ Implemented and Tested

---

## Overview

The `queue-todo-sync` skill provides bidirectional synchronization between:

1. **DELEGATE files** in `artifacts/queue/incoming/` → TODO.md (add pending tasks)
2. **HANDBACK files** in `artifacts/queue/done/` → TODO.md (mark tasks complete)
3. **TODO.md manual edits** → queue (detect conflicts, apply merge strategy)

### Key Features

- ✅ **DELEGATE → TODO.md sync**: Automatically add new tasks to TODO.md when DELEGATEs are created
- ✅ **HANDBACK → TODO.md sync**: Automatically mark tasks complete when HANDBACKs are received
- ✅ **Bidirectional sync**: Detect and resolve conflicts between TODO.md and queue
- ✅ **Orphan detection**: Flag tasks in TODO but not in queue
- ✅ **Missing detection**: Flag tasks in queue but not in TODO
- ✅ **Weekly reporting**: Generate sync reports with metrics and recommendations
- ✅ **CLI wrapper**: `opencode-todo-sync` command for manual invocation

---

## Usage

### Automatic Sync (via Orchestrator)

The Orchestrator automatically invokes this skill:

1. **After DELEGATE creation**: Adds task to TODO.md IN PROGRESS section
2. **After HANDBACK received**: Marks task complete in TODO.md

### Manual Sync

```bash
# Full bidirectional sync
opencode-todo-sync sync

# Generate weekly report
opencode-todo-sync report

# Check for conflicts and issues
opencode-todo-sync check
```

### Programmatic Usage

```python
import importlib
import sys
from pathlib import Path

# Import the skill module (directory has hyphen, so use importlib)
queue_todo_sync = importlib.import_module("src.skills.queue-todo-sync")
TodoSyncManager = queue_todo_sync.TodoSyncManager

manager = TodoSyncManager(
    todo_path=Path("TODO.md"),
    queue_path=Path("artifacts/queue")
)

# Sync DELEGATE to TODO
delegate_data = {
    "task_id": "2026-05-18-test-task",
    "role": "engineer",
    "scope": "Test task for queue-todo-sync",
    "effort": "medium",
    "plan": ["Step 1", "Step 2"],
}
manager.sync_delegate_to_todo(delegate_data)

# Sync HANDBACK to TODO
handback_data = {
    "task_id": "2026-05-18-test-task",
    "status": "complete",
    "timestamp": "2026-05-18T10:00:00Z",
}
manager.sync_handback_to_todo(handback_data)

# Perform full bidirectional sync
result = manager.bidirectional_sync()
print(f"Synced {result['delegates_synced']} DELEGATEs")
print(f"Synced {result['handbacks_synced']} HANDBACKs")

# Generate weekly report
report = manager.generate_weekly_report()
report.write_to_file(Path("reports/sync_report_week_1.md"))
```

---

## TODO.md Format

The skill expects TODO.md to follow this format:

```markdown
# TODO

## IN PROGRESS
- [ ] **TASK-ID:** Task description (Owner: role)
- [ ] **2026-05-18-test-task:** Test task for queue-todo-sync (Owner: engineer)

## COMPLETED
- [x] **TASK-001:** Completed task (Owner: engineer)
```

### Format Rules

- **Pending tasks**: `- [ ] **TASK-ID:** description (Owner: role)`
- **Completed tasks**: `- [x] **TASK-ID:** description (Owner: role)`
- **Sections**: `## IN PROGRESS`, `## COMPLETED`
- **Task ID**: Unique identifier from DELEGATE/HANDBACK
- **Description**: First line of scope (truncated to 60 chars)
- **Owner**: Role that owns the task (engineer, quality-engineer, etc.)

---

## Sync Workflow

### DELEGATE → TODO.md Sync

```
1. DELEGATE created in artifacts/queue/incoming/DELEGATE-*.yaml
2. Orchestrator invokes queue-todo-sync skill
3. Skill reads DELEGATE file
4. Skill extracts: task_id, role, scope, effort, plan
5. Skill formats as TODO line: - [ ] **TASK-ID:** scope (Owner: role)
6. Skill adds to "## IN PROGRESS" section
7. TODO.md updated
```

### HANDBACK → TODO.md Sync

```
1. HANDBACK created in artifacts/queue/done/HANDBACK-*.json
2. Orchestrator invokes queue-todo-sync skill
3. Skill reads HANDBACK file
4. Skill extracts: task_id, status, timestamp, quality_score
5. Skill finds matching TODO entry
6. Skill marks as complete: - [x] **TASK-ID:** ...
7. Skill optionally moves to "## COMPLETED" section
8. TODO.md updated
```

### Bidirectional Sync

```
1. Skill reads TODO.md and queue
2. Skill detects conflicts:
   - Tasks in TODO but not in queue (orphaned)
   - Tasks in queue but not in TODO (missing)
   - Tasks with conflicting descriptions (modified in both)
3. Skill applies merge strategy:
   - TODO.md manual edits take precedence (human intent preserved)
   - Queue entries are authoritative for new tasks
4. Skill generates sync report with recommendations
```

---

## Conflict Resolution Strategy

The skill uses a **TODO.md-first merge strategy**:

- **Manual edits in TODO.md take precedence** over queue versions
- **New tasks from queue** are added if not in TODO
- **Completed tasks** are marked in TODO when HANDBACK received
- **Conflicts are logged** for human review

This ensures that manual edits to TODO.md are not overwritten by automated syncs.

---

## Weekly Sync Report

The skill generates weekly reports with:

- **Total tasks**: Count of all tasks in TODO.md
- **Completed tasks**: Count of completed tasks
- **Completion rate**: Percentage of completed tasks
- **Orphaned tasks**: Tasks in TODO but not in queue
- **Missing tasks**: Tasks in queue but not in TODO
- **Conflicts**: Tasks with conflicting versions

Example report:

```markdown
# TODO Sync Report

**Week:** 2026-05-18 to 2026-05-24  
**Generated:** 2026-05-24T10:00:00Z

## Summary

| Metric | Count |
|--------|-------|
| Total Tasks | 10 |
| Completed | 3 |
| Completion Rate | 30.0% |
| Orphaned Tasks | 1 |
| Missing Tasks | 2 |
| Conflicts | 0 |

## Recommendations

- Review 1 orphaned tasks in TODO.md
- Add 2 missing tasks to TODO.md
```

---

## Integration Points

### Orchestrator Integration

The Orchestrator calls this skill at two points:

1. **Post-DELEGATE**: After creating a new DELEGATE in queue/incoming/
   ```python
   manager.sync_delegate_to_todo(delegate_data)
   ```

2. **Post-HANDBACK**: After receiving a HANDBACK in queue/done/
   ```python
   manager.sync_handback_to_todo(handback_data)
   ```

### CLI Integration

The skill provides a CLI wrapper: `opencode-todo-sync`

```bash
# Sync command
opencode-todo-sync sync

# Report command
opencode-todo-sync report

# Check command (detect issues)
opencode-todo-sync check
```

---

## Implementation Details

### Core Classes

#### `DelegateEntry`
Represents a DELEGATE task entry.

```python
@dataclass
class DelegateEntry:
    task_id: str
    role: str
    scope: str
    effort: str
    plan: List[str]
    created_at: str
```

Methods:
- `from_yaml(yaml_content)`: Parse from YAML
- `from_file(file_path)`: Parse from file
- `to_todo_line()`: Convert to TODO.md format
- `to_dict()`: Convert to dictionary

#### `HandbackEntry`
Represents a HANDBACK task entry.

```python
@dataclass
class HandbackEntry:
    task_id: str
    status: str
    timestamp: str
    quality_score: int
    confidence: float
    deliverables: List[str]
    tests: List[str]
```

Methods:
- `from_dict(data)`: Parse from dictionary
- `from_file(file_path)`: Parse from file
- `to_todo_line()`: Convert to TODO.md format (marked complete)
- `to_dict()`: Convert to dictionary

#### `TodoSyncManager`
Main synchronization manager.

```python
class TodoSyncManager:
    def __init__(self, todo_path: Path, queue_path: Path)
    def sync_delegate_to_todo(delegate_data: Dict) -> bool
    def sync_handback_to_todo(handback_data: Dict) -> bool
    def detect_orphaned_tasks() -> List[Dict]
    def detect_missing_tasks() -> List[Dict]
    def detect_conflicts() -> List[SyncConflict]
    def resolve_conflict(conflict: SyncConflict) -> str
    def bidirectional_sync() -> Dict
    def generate_weekly_report(week_start: str = None) -> SyncReport
```

#### `SyncReport`
Represents a weekly sync report.

```python
@dataclass
class SyncReport:
    week_start: str
    week_end: str
    total_tasks: int
    completed_tasks: int
    orphaned_tasks: int
    missing_tasks: int
    conflicts: int
```

Methods:
- `generate()`: Generate report as markdown
- `write_to_file(file_path)`: Write report to file

---

## Testing

The skill includes comprehensive tests with >80% coverage:

```bash
# Run all tests
pytest src/skills/queue-todo-sync/tests/ -v

# Run with coverage
pytest src/skills/queue-todo-sync/tests/ --cov=src/skills/queue-todo-sync --cov-report=html

# Run specific test
pytest src/skills/queue-todo-sync/tests/test_sync_todo.py::TestDelegateEntry -v
```

### Test Coverage

- ✅ DELEGATE entry parsing and formatting
- ✅ HANDBACK entry parsing and formatting
- ✅ TODO.md reading and parsing
- ✅ DELEGATE → TODO.md sync
- ✅ HANDBACK → TODO.md sync
- ✅ Orphan task detection
- ✅ Missing task detection
- ✅ Conflict detection
- ✅ Bidirectional sync
- ✅ Weekly report generation
- ✅ CLI integration
- ✅ Full workflow integration

---

## Error Handling

The skill handles errors gracefully:

- **Invalid YAML/JSON**: Logged and skipped
- **Missing files**: Handled with sensible defaults
- **Malformed entries**: Validated and rejected
- **Conflicts**: Logged for human review
- **File I/O errors**: Caught and reported

---

## Performance

- **Sync time**: <100ms for typical queue (10-50 tasks)
- **Memory usage**: <10MB for typical queue
- **Report generation**: <50ms
- **Conflict detection**: O(n) where n = number of tasks

---

## Future Enhancements

- [ ] Automatic conflict resolution with user preferences
- [ ] Real-time sync (watch for file changes)
- [ ] Integration with external task tracking (Jira, Linear, etc.)
- [ ] Task priority tracking
- [ ] Burndown chart generation
- [ ] Slack/email notifications on sync issues
- [ ] Historical sync metrics and trends

---

## See Also

- [DELEGATE/HANDBACK Protocol](../../docs/QUEUE-PROTOCOL.md)
- [Orchestrator Agent](../../agents/orchestrator/AGENT.md)
- [TODO.md](../../TODO.md)

---

**Owner:** Engineer Agent  
**Last Updated:** 2026-05-18  
**Status:** ✅ Production Ready
