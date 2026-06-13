---
name: queue-isolation
description: Session-scoped, harness-scoped queue path isolation for multi-harness agentic-engineers workflows. Ensures Claude, Copilot, GPT, and local agents never collide on the same queue directories.
license: Proprietary
compatibility: agentic-engineers framework v5.10+. Requires Python 3.7+
metadata:
  author: agentic-engineers
  version: "1.0.0"
  category: infrastructure
  role: orchestrator
  model: claude-haiku-4.5
  effort: low
  thinking: false
  dependencies: []
---

# queue-isolation

## Overview

`queue-isolation` provides **mandatory startup isolation** for the DELEGATE/HANDBACK
queue when multiple AI harnesses (Claude, GitHub Copilot, GPT, local) operate within
the same user environment.

Without isolation, two harnesses could pick up each other's DELEGATE files, leading to
duplicate task execution, lost HANDBACKs, and corrupt queue state.

---

## Queue Path Structure

```
~/.agentic-engineers/
└── artifacts/
    └── {session_id}/               ← unique per session
        ├── claude/                 ← one dir per harness
        │   ├── metadata.json
        │   └── queue/
        │       ├── incoming/       ← new DELEGATEs
        │       │   └── .keep.me
        │       ├── processing/     ← tasks being executed
        │       │   └── .keep.me
        │       ├── done/           ← completed (HANDBACKs)
        │       │   └── .keep.me
        │       └── failed/         ← errored tasks
        │           └── .keep.me
        ├── copilot/
        │   ├── metadata.json
        │   └── queue/ ...
        └── gpt/
            ├── metadata.json
            └── queue/ ...
```

The `.agentic-engineers/` root is excluded from git via `.gitignore`.

---

## Session Lifecycle

1. **Startup (mandatory)** — Orchestrator or agent calls `init_queue_structure()`
   before any queue operations. This is idempotent; calling it twice is safe.

2. **Operation** — All queue reads/writes use paths from `get_queue_path()` so
   that paths are always session- and harness-scoped.

3. **Shutdown** — No explicit teardown required. Directories persist for audit.
   Future analytics can correlate activity via `metadata.json`.

---

## Harness Detection

`detect_harness()` inspects environment variables in priority order:

| Priority | Env Variable         | Returns     |
|----------|----------------------|-------------|
| 1        | `AGENTIC_HARNESS`    | value as-is |
| 2        | `CLAUDE_SESSION_ID`  | `"claude"`  |
| 3        | `COPILOT_SESSION_ID` | `"copilot"` |
| 4        | `OPENAI_API_KEY`     | `"gpt"`     |
| default  | (none matched)       | `"local"`   |

Set `AGENTIC_HARNESS=local` to force local mode in any environment.

---

## Session ID Detection

`get_session_id()` reads env vars in this order and falls back to a generated UUID:

1. `AGENTIC_SESSION_ID`
2. `CLAUDE_SESSION_ID`
3. `COPILOT_SESSION_ID`
4. Generate `uuid.uuid4()`

---

## metadata.json Schema

```json
{
  "session_id": "abc-123",
  "harness": "claude",
  "created_at": "2025-01-15T10:00:00+00:00",
  "last_accessed_at": "2025-01-15T10:05:00+00:00"
}
```

`created_at` is immutable after first creation. `last_accessed_at` is updated
every time `init_queue_structure()` is called for an existing session.

---

## Staleness Monitoring

The queue-isolation skill includes **advisory staleness detection** for monitoring
task health without modifying task state.

### SLA Thresholds

- **Stale (WARN)**: Tasks > 300 seconds (5 minutes) in processing state
- **Crash (ESCALATE)**: Tasks > 600 seconds (10 minutes) since claimed_at
- Both thresholds are configurable via function parameters

### Task Timestamp Tracking

Each task stores timestamps in a sidecar file: `<queue_state>/<task_id>.timestamps.json`

```json
{
  "created_at": "2025-01-15T10:00:00+00:00",
  "last_updated": "2025-01-15T10:05:00+00:00",
  "claimed_at": "2025-01-15T10:00:05+00:00",
  "last_heartbeat": "2025-01-15T10:04:30+00:00",
  "state_changes": [
    {
      "timestamp": "2025-01-15T10:00:01+00:00",
      "action": "created",
      "state": "incoming"
    },
    {
      "timestamp": "2025-01-15T10:00:05+00:00",
      "action": "claimed",
      "state": "processing"
    },
    {
      "timestamp": "2025-01-15T10:04:30+00:00",
      "action": "heartbeat",
      "state": "processing"
    }
  ]
}
```

**Timestamp Fields:**
- `created_at` (immutable): When task was first created
- `last_updated`: Most recent modification time
- `claimed_at`: When task was claimed by an agent (moved to processing)
- `last_heartbeat`: Most recent agent heartbeat (for staleness detection)
- `state_changes`: Array of all state transitions with timestamps and actions

### API Functions

#### record_task_timestamp()

```python
from queue_isolation import record_task_timestamp

record_task_timestamp(
    task_id="my-task",
    queue_root=Path("/home/user/.agentic-engineers/claude/session-id/queue"),
    state="processing",
    action="heartbeat"
)
```

Creates or updates a task's timestamp sidecar with state changes.

#### check_task_staleness()

```python
from queue_isolation import check_task_staleness

result = check_task_staleness(
    task_id="my-task",
    queue_root=queue_root,
    state="processing",
    stale_threshold_sec=300.0,      # 5 minutes
    escalation_threshold_sec=600.0  # 10 minutes
)

# Returns:
# {
#   "task_id": "my-task",
#   "age_seconds": 350.5,
#   "heartbeat_age_seconds": 10.2,  # seconds since last heartbeat
#   "is_stale": True,
#   "is_crashed": False,
#   "status": "stale",      # ok | stale | crashed | unknown
#   "action": "warn"        # none | warn | escalate
# }
```

Checks if a single task is stale or crashed. **Uses last_heartbeat if available**,
otherwise falls back to creation time. Returns status and recommended action.

**Staleness Detection Logic:**
1. If `last_heartbeat` exists: measure age from last heartbeat timestamp
2. Else: measure age from `created_at` timestamp
3. Compare against thresholds: stale (300s) then escalation (600s)

#### scan_queue_for_staleness()

```python
from queue_isolation import scan_queue_for_staleness

result = scan_queue_for_staleness(
    queue_root=queue_root,
    state="processing",
    stale_threshold_sec=300.0,
    escalation_threshold_sec=600.0
)

# Returns:
# {
#   "scanned_at": "2025-01-15T10:05:00+00:00",
#   "state": "processing",
#   "tasks_checked": 42,
#   "stale_tasks": [...],    # Tasks 300-600s old
#   "crashed_tasks": [...],  # Tasks > 600s old
#   "ok_tasks": [...]        # Tasks < 300s old
# }
```

Scans entire queue state directory, categorizing all tasks by health status.

### QueueIsolation Class Methods

```python
from queue_isolation import QueueIsolation

qi = QueueIsolation.from_env()
qi.initialise()

# Check a single task
result = qi.check_staleness("my-task", state="processing")

# Scan entire processing queue
scan = qi.scan_staleness(state="processing")
print(f"Found {len(scan['stale_tasks'])} stale tasks")
print(f"Found {len(scan['crashed_tasks'])} crashed tasks")
```

### Staleness is Advisory (NOT State-Modifying)

- Staleness **NEVER changes** task state or marks tasks as failed
- Staleness is **informational only** — generates WARN logs and health metrics
- Crashed tasks (> 600s) may **trigger automatic retry logic** (separate system)
- Escalation to Quality Engineer occurs only after retry exhaustion (retry_count >= 3)

### Integration with Orchestrator

The Orchestrator uses staleness detection during queue polling:

```python
# In orchestrator_integration.py or equivalent
qi = QueueIsolation.from_env()
qi.initialise()

# Scan processing queue for stale/crashed tasks
staleness = qi.scan_staleness(state="processing")

# Log warnings for stale tasks (300-600s)
for task in staleness["stale_tasks"]:
    log.warn(f"Task {task['task_id']} is stale (age={task['age_seconds']}s)")

# Log alerts for crashed tasks (> 600s)
for task in staleness["crashed_tasks"]:
    log.error(f"Task {task['task_id']} has CRASHED (age={task['age_seconds']}s)")
    # Trigger crash recovery / retry logic
```

---

## Programmatic Usage

### Functional API

```python
from queue_isolation import detect_harness, get_session_id, get_queue_path, init_queue_structure

# Detect current environment
harness = detect_harness()     # 'claude' | 'copilot' | 'gpt' | 'local'
session = get_session_id()     # e.g. 'abc-123' from env or generated UUID

# Get the queue path (does not create dirs)
queue = get_queue_path(session, harness)
# → PosixPath('/Users/alice/.agentic-engineers/artifacts/abc-123/claude/queue')

# Create all dirs, .keep.me files, and metadata.json (idempotent)
init_queue_structure(session, harness)
```

### Class API

```python
from queue_isolation import QueueIsolation

# Detect everything from environment
qi = QueueIsolation.from_env()
qi.initialise()

# Use the queue
incoming = qi.queue_path / "incoming"
task_file = incoming / "my-task.json"
task_file.write_text('{"task_id": "my-task"}')

# Read metadata
meta = qi.get_metadata()
print(meta["created_at"])
```

### Integration with queue-management

```python
from queue_isolation import QueueIsolation
from scripts.queue_ops import QueueOperations

qi = QueueIsolation.from_env()
qi.initialise()

# Pass queue_path to QueueOperations
ops = QueueOperations(
    session_id=qi.session_id,
    queue_path=str(qi.queue_path.parent.parent),  # <base>/artifacts/<session>/
)
```

---

## Testing

```bash
# Run all 28 tests
python3 -m pytest src/skills/_meta/queue-isolation/tests/ -v

# Run a specific category
python3 -m pytest src/skills/_meta/queue-isolation/tests/ -v -k "Isolation"
```

### Test Coverage

- ✅ `detect_harness()` — CLAUDE_SESSION_ID, COPILOT_SESSION_ID, OPENAI_API_KEY, AGENTIC_HARNESS override, fallback to local
- ✅ `get_session_id()` — AGENTIC_SESSION_ID, CLAUDE_SESSION_ID, COPILOT_SESSION_ID, UUID generation
- ✅ `get_queue_path()` — structure, Path type, harness diff, session diff, default HOME
- ✅ `init_queue_structure()` — subdirs, .keep.me files, metadata creation, idempotency, last_accessed update
- ✅ Isolation — multi-harness, multi-session, auto dir creation
- ✅ `QueueIsolation` class — instantiation, queue_path property, initialise()

---

## Error Handling

| Scenario                         | Behaviour                          |
|----------------------------------|------------------------------------|
| No env vars set                  | harness='local', session=new UUID  |
| `init_queue_structure` called 2× | No-op for dirs; updates metadata   |
| `get_metadata` before init       | Raises `FileNotFoundError`         |
| `base_dir` does not exist        | Created automatically by `mkdir`   |

---

## See Also

- [queue-management skill](../../queue-management/SKILL.md)
- [DELEGATE/HANDBACK Protocol](../../../docs/QUEUE-PROTOCOL.md)
- [SPEC.md](../../../SPEC.md)

---

**Owner:** Senior Engineer  
**Last Updated:** 2025-01-15  
**Status:** ✅ Production Ready
