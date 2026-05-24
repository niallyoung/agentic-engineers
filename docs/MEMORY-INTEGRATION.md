# Memory Aggregation & Session Integration

## Overview

The memory aggregation infrastructure collects all session events (DELEGATEs, HANDBACKs, logs, metrics) into a unified, queryable session memory store. This enables:

- **Session playback** - Reconstruct what happened in a session
- **Analytics** - Analyze patterns across tasks, agents, and time
- **Debugging** - Trace execution flow and identify issues
- **Metrics** - Calculate token usage, quality scores, and performance

## Architecture

### Directory Structure

Session memory is stored in `~/.agentic-engineers/{session_id}/memory/`:

```
~/.agentic-engineers/
├── {session_id}/
│   └── memory/
│       ├── delegates/          # DELEGATE event copies
│       ├── handbacks/          # HANDBACK event copies
│       ├── logs/               # Agent execution logs
│       ├── thinking/           # Reasoning output
│       ├── metrics/            # Token usage, timing, quality
│       ├── index.json          # Aggregated metadata (machine-readable)
│       ├── index.md            # Aggregated metadata (human-readable)
│       └── summary.md          # Session summary report
```

### Components

#### 1. SessionMemoryManager (Lifecycle)

Main entry point for session memory management. Handles initialization, collection, and aggregation.

```python
from src.orchestration.memory import SessionMemoryManager

# Initialize session memory
manager = SessionMemoryManager(session_id="my-session-001")
result = manager.initialize(metadata={"user": "alice", "project": "api-refactor"})

# Collect memory events (called from orchestrator)
manager.collect_memory_event("delegate", {"task_id": "t1", ...})
manager.collect_memory_event("handback", {"task_id": "t1", "status": "complete", ...})

# Aggregate all memory at session end
index = manager.aggregate_memory()

# Generate and export summary
summary_path = manager.export_summary()

# Query memory
delegates = manager.get_delegates()
delegates_by_role = manager.get_delegates(role="Engineer")
completed_tasks = manager.get_handbacks(status="complete")
metrics = manager.get_metrics()
task_info = manager.query_by_task_id("t1")
role_info = manager.query_by_role("Senior Engineer")
```

#### 2. SessionMemoryAggregator (Collection)

Collects memory from queue directories and artifacts.

```python
from src.orchestration.memory.aggregator import SessionMemoryAggregator

aggregator = SessionMemoryAggregator(session_id="my-session-001")

# Collect specific components
delegates = aggregator.collect_delegates()    # From queue/incoming + artifacts
handbacks = aggregator.collect_handbacks()    # From queue/processing + queue/done
logs = aggregator.collect_logs()              # From log directories
thinking = aggregator.collect_thinking()      # From thinking output
metrics = aggregator.collect_metrics()        # Aggregated metrics

# Full aggregation
index = aggregator.aggregate_all()

# Export index
index_path = aggregator.export_index(pretty=True)

# Query
result = aggregator.query_by_task_id("task-001")
result = aggregator.query_by_role("Engineer")
```

#### 3. Directory Setup

Creates and manages memory directory structure.

```python
from src.orchestration.memory.directory_setup import (
    setup_session_memory,
    get_session_memory_dir,
    initialize_memory_index,
    get_memory_stats,
)

# Set up memory directories
subdirs = setup_session_memory("my-session-001")
# subdirs = {
#   "delegates": Path(...),
#   "handbacks": Path(...),
#   "logs": Path(...),
#   "thinking": Path(...),
#   "metrics": Path(...),
# }

# Get memory directory
memory_dir = get_session_memory_dir("my-session-001")

# Initialize empty index
index_path = initialize_memory_index("my-session-001")

# Get stats
stats = get_memory_stats("my-session-001")
# stats = {
#   "exists": True,
#   "session_id": "my-session-001",
#   "delegates_count": 5,
#   "handbacks_count": 4,
#   "logs_count": 8,
#   "thinking_count": 3,
#   "metrics_count": 1,
# }
```

## Integration with Orchestrator

The orchestrator automatically collects memory during task lifecycle:

1. **DELEGATE phase** - Orchestrator copies DELEGATE to memory/delegates/
2. **HANDBACK phase** - Orchestrator copies HANDBACK to memory/handbacks/
3. **Session end** - Orchestrator calls aggregate_memory() to create index

### Example Orchestrator Integration

```python
# In orchestrator.py

from src.orchestration.memory import SessionMemoryManager

class Orchestrator:
    def __init__(self, session_id):
        self.session_id = session_id
        self.memory_manager = SessionMemoryManager(session_id)
        self.memory_manager.initialize(metadata={
            "started_at": datetime.utcnow().isoformat(),
        })
    
    def delegate_task(self, task):
        # ... existing delegation logic ...
        
        # Record in memory
        self.memory_manager.collect_memory_event("delegate", {
            "task_id": task.id,
            "role": task.role,
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    def process_handback(self, handback):
        # ... existing handback logic ...
        
        # Record in memory
        self.memory_manager.collect_memory_event("handback", {
            "task_id": handback.task_id,
            "status": handback.status,
            "quality_score": handback.quality_score,
        })
    
    def finalize_session(self):
        # Aggregate all memory
        index = self.memory_manager.aggregate_memory()
        
        # Export summary
        self.memory_manager.export_summary()
        
        # Return metrics
        return self.memory_manager.get_metrics()
```

## Usage Patterns

### Pattern 1: Session Playback

Reconstruct what happened in a session:

```python
manager = SessionMemoryManager("session-001")
manager.initialize()
manager.aggregate_memory()

# Get all tasks
delegates = manager.get_delegates()
for delegate in delegates:
    print(f"Task: {delegate['task_id']}")
    print(f"  Role: {delegate['role']}")
    print(f"  Effort: {delegate['effort']}")
    
    # Get result
    result = manager.query_by_task_id(delegate['task_id'])
    handbacks = result['handbacks']
    if handbacks:
        print(f"  Result: {handbacks[0]['status']}")
        print(f"  Quality: {handbacks[0]['quality_score']}/100")
```

### Pattern 2: Role Analysis

Analyze performance by role:

```python
manager = SessionMemoryManager("session-001")
manager.initialize()
manager.aggregate_memory()

roles = ["Engineer", "Senior Engineer", "Lead Engineer"]
for role in roles:
    info = manager.query_by_role(role)
    print(f"{role}: {info['count']} tasks")
```

### Pattern 3: Metrics Dashboard

Display session metrics:

```python
manager = SessionMemoryManager("session-001")
manager.initialize()
manager.aggregate_memory()

metrics = manager.get_metrics()
print(f"Total Tokens: {metrics['total_tokens']:,}")
print(f"Completed Tasks: {metrics['completed_tasks']}")
print(f"Failed Tasks: {metrics['failed_tasks']}")
print(f"Avg Quality: {metrics['average_quality_score']:.1f}/100")

# Export summary
manager.export_summary()
```

### Pattern 4: Export & Migration

Export memory for archival or analysis:

```python
from pathlib import Path
import shutil

manager = SessionMemoryManager("session-001")
manager.initialize()
manager.aggregate_memory()

# Export to archive
archive_dir = Path("~/session-exports/session-001").expanduser()
archive_dir.mkdir(parents=True, exist_ok=True)

# Copy memory to archive
memory_dir = manager.memory_manager.memory_dir
shutil.copytree(memory_dir, archive_dir / "memory")

# Export summary
manager.export_summary()
```

## Memory Index Format

The `index.json` file contains aggregated metadata:

```json
{
  "session_id": "session-001",
  "created_at": "2026-05-24T11:42:13.926470",
  "updated_at": "2026-05-24T12:45:22.123456",
  "delegates": [
    {
      "task_id": "task-001",
      "timestamp": "2026-05-24T11:45:00Z",
      "role": "Engineer",
      "model": "claude-haiku-4.5",
      "effort": "low",
      "scope": "Implement user authentication module",
      "source": "queue-incoming",
      "source_file": "queue/session-001/incoming/task-001.yaml"
    }
  ],
  "handbacks": [
    {
      "task_id": "task-001",
      "timestamp": "2026-05-24T11:55:00Z",
      "status": "complete",
      "quality_score": 95,
      "tokens_used": 1200,
      "source": "queue-done",
      "source_file": "queue/session-001/done/task-001-handback.yaml"
    }
  ],
  "logs": [],
  "thinking": [],
  "metrics": {
    "total_delegates": 5,
    "total_handbacks": 4,
    "total_tokens": 50000,
    "average_quality_score": 92.5,
    "completed_tasks": 4,
    "failed_tasks": 0
  },
  "summary": {
    "total_delegates": 5,
    "total_handbacks": 4,
    "completed_tasks": 4,
    "failed_tasks": 0,
    "total_tokens": 50000,
    "average_quality_score": 92.5,
    "total_logs": 0,
    "total_thinking_files": 0
  }
}
```

## Querying Memory

The aggregator provides typed query methods:

### Query by Task ID

```python
result = aggregator.query_by_task_id("task-001")
# Returns:
# {
#   "task_id": "task-001",
#   "delegates": [...],    # All DELEGATEs for this task
#   "handbacks": [...]     # All HANDBACKs for this task
# }
```

### Query by Role

```python
result = aggregator.query_by_role("Engineer")
# Returns:
# {
#   "role": "Engineer",
#   "delegates": [...],    # All DELEGATEs assigned to this role
#   "count": 5             # Number of tasks
# }
```

## Testing

The system includes comprehensive integration tests:

```bash
# Run memory integration tests
python3 -m pytest tests/test_session_memory_integration.py -v

# Run with coverage
python3 -m pytest tests/test_session_memory_integration.py --cov=src.orchestration.memory
```

Test coverage includes:
- ✅ Directory structure creation
- ✅ DELEGATE collection from queue and artifacts
- ✅ HANDBACK collection from queue and artifacts
- ✅ Full memory aggregation
- ✅ Index export (JSON format)
- ✅ Memory queries by task ID and role
- ✅ Session memory initialization
- ✅ Summary generation

## Performance Considerations

### Disk Usage

Each session memory stores copies of all events:
- **DELEGATEs**: ~2-5 KB each (typically 5-50 per session)
- **HANDBACKs**: ~3-8 KB each (typically 5-50 per session)
- **Logs**: Variable (typically 10-100 MB per session)
- **Total typical session**: 50-200 MB

### Collection Time

Aggregation is O(n) where n = number of events:
- **Typical session (50 DELEGATEs, 50 HANDBACKs)**: ~100-500ms
- **Large session (500+ events)**: ~1-5s

### Memory Efficiency

Index queries are O(1) lookups via JSON in-memory:
- **Task lookup**: ~1-5ms
- **Role aggregation**: ~10-50ms (depends on number of events)

## Best Practices

1. **Initialize at session start**
   ```python
   manager.initialize(metadata={"user": "alice", "project": "api"})
   ```

2. **Collect events during execution**
   ```python
   manager.collect_memory_event("delegate", {...})
   ```

3. **Aggregate at session end**
   ```python
   manager.aggregate_memory()
   manager.export_summary()
   ```

4. **Archive old sessions**
   ```python
   # Move completed sessions to archive
   from src.orchestration.memory.directory_setup import cleanup_session_memory
   cleanup_session_memory("session-001", archive=True)
   ```

5. **Query for insights**
   ```python
   # Analyze performance
   metrics = manager.get_metrics()
   delegates_by_role = manager.get_delegates(role="Engineer")
   ```

## Troubleshooting

### No DELEGATEs collected

**Issue**: `collect_delegates()` returns empty list

**Solution**: 
- Check queue directory exists: `~/.copilot/queue/{session-id}/incoming/`
- Verify DELEGATE files have `handoff_type: DELEGATE`
- Check file permissions (should be readable)

### Memory index not found

**Issue**: `index.json` doesn't exist

**Solution**:
- Run `manager.aggregate_memory()` first
- Call `manager.export_index()` to save
- Check `~/.agentic-engineers/{session-id}/memory/` directory

### Query returns empty results

**Issue**: `query_by_task_id()` or `query_by_role()` returns no matches

**Solution**:
- Ensure `aggregate_memory()` was called
- Check task ID spelling (case-sensitive)
- Verify role names match exactly

## See Also

- `src/orchestration/memory/aggregator.py` - Memory aggregation
- `src/orchestration/memory/session_manager.py` - Session lifecycle
- `src/orchestration/memory/directory_setup.py` - Directory management
- `tests/test_session_memory_integration.py` - Integration tests
