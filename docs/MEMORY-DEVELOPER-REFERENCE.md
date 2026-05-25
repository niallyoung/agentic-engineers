# Memory System Developer Reference

## API Reference

### SessionMemoryManager (Lifecycle Management)

Main entry point for managing session memory.

```python
from src.orchestration.memory import SessionMemoryManager

manager = SessionMemoryManager(session_id="session-001")
```

#### Methods

##### `initialize(metadata: Dict[str, Any] = None) → bool`

Initialize memory for a session and create directory structure.

```python
manager.initialize(metadata={
    "user": "alice",
    "project": "api-refactor",
    "harness": "local"
})
```

**Parameters:**
- `metadata`: Optional dict with session metadata

**Returns:** `True` if successful, `False` if already initialized

---

##### `collect_memory_event(event_type: str, event_data: Dict) → None`

Record a memory event (DELEGATE or HANDBACK).

```python
# Record a DELEGATE
manager.collect_memory_event("delegate", {
    "task_id": "task-001",
    "role": "Engineer",
    "model": "claude-haiku-4.5",
    "effort": "high",
    "timestamp": datetime.utcnow().isoformat(),
})

# Record a HANDBACK
manager.collect_memory_event("handback", {
    "task_id": "task-001",
    "status": "complete",
    "quality_score": 95,
    "tokens_used": 1200,
    "timestamp": datetime.utcnow().isoformat(),
})
```

**Parameters:**
- `event_type`: "delegate" or "handback"
- `event_data`: Dict with event details

**Raises:** `ValueError` if event_type is invalid

---

##### `aggregate_memory() → Dict[str, Any]`

Aggregate all memory files into a unified index. **Must call before querying.**

```python
index = manager.aggregate_memory()

# Returns:
# {
#   "session_id": "session-001",
#   "delegates": [...],
#   "handbacks": [...],
#   "metrics": {...},
#   "summary": {...}
# }
```

**Returns:** Complete index dict

**Raises:** `OSError` if memory directory doesn't exist

---

##### `get_delegates(role: str = None, effort: str = None) → List[Dict]`

Get all DELEGATEs, optionally filtered by role or effort.

```python
# Get all delegates
all = manager.get_delegates()

# Get by role
engineers = manager.get_delegates(role="Engineer")

# Get by effort
high_effort = manager.get_delegates(effort="high")
```

**Parameters:**
- `role`: Optional role filter (e.g., "Engineer", "Senior Engineer")
- `effort`: Optional effort filter (e.g., "low", "medium", "high", "max")

**Returns:** List of DELEGATE dicts

---

##### `get_handbacks(status: str = None) → List[Dict]`

Get all HANDBACKs, optionally filtered by status.

```python
# Get all handbacks
all = manager.get_handbacks()

# Get completed only
completed = manager.get_handbacks(status="complete")

# Get escalated/blocked tasks
escalated = manager.get_handbacks(status="escalated")
```

**Parameters:**
- `status`: Optional status filter (e.g., "complete", "failed", "escalated")

**Returns:** List of HANDBACK dicts

---

##### `query_by_task_id(task_id: str) → Dict[str, Any]`

Query memory for a specific task.

```python
result = manager.query_by_task_id("task-001")

# Returns:
# {
#   "task_id": "task-001",
#   "delegates": [...],      # DELEGATE records
#   "handbacks": [...]       # HANDBACK records
# }
```

**Parameters:**
- `task_id`: Task ID to query

**Returns:** Dict with task info or empty if not found

---

##### `query_by_role(role: str) → Dict[str, Any]`

Query memory for a specific role.

```python
result = manager.query_by_role("Engineer")

# Returns:
# {
#   "role": "Engineer",
#   "count": 15,
#   "delegates": [...],      # All Engineer DELEGATEs
#   "handbacks": [...]       # All Engineer HANDBACKs
# }
```

**Parameters:**
- `role`: Role name to query

**Returns:** Dict with role stats and tasks

---

##### `get_metrics() → Dict[str, Any]`

Get aggregated session metrics.

```python
metrics = manager.get_metrics()

print(f"Total tasks: {metrics['total_delegates']}")
print(f"Completed: {metrics['completed_tasks']}")
print(f"Failed: {metrics['failed_tasks']}")
print(f"Tokens: {metrics['total_tokens']:,}")
print(f"Quality: {metrics['average_quality_score']:.1f}/100")
```

**Returns:** Dict with session metrics

---

##### `export_summary() → Path`

Export human-readable session summary to file.

```python
summary_path = manager.export_summary()
print(f"Summary exported to: {summary_path}")
```

**Returns:** Path to exported summary.md file

---

### ArtifactMemoryStore (Storage Engine)

Low-level storage operations.

```python
from src.orchestration.memory import ArtifactMemoryStore

store = ArtifactMemoryStore(session_id="session-001")
```

#### Methods

##### `write(key: str, data: Dict, subdir: str = "metadata") → Path`

Write JSON data to memory.

```python
store.write("my-data", {
    "status": "success",
    "count": 42,
    "timestamp": datetime.now().isoformat()
}, subdir="metrics")

# Creates: ~/.agentic-engineers/session-001/memory/metrics/my-data.json
```

**Parameters:**
- `key`: Filename (without extension)
- `data`: Dict to write (JSON serializable)
- `subdir`: Subdirectory (default: "metadata")

**Returns:** Path to written file

---

##### `read(key: str, subdir: str = "metadata") → Dict[str, Any]`

Read JSON data from memory.

```python
data = store.read("my-data", subdir="metrics")
print(data["status"])  # "success"
```

**Parameters:**
- `key`: Filename (without extension)
- `subdir`: Subdirectory (default: "metadata")

**Returns:** Dict with "data" key containing file contents

**Raises:** `FileNotFoundError` if file doesn't exist

---

##### `append_metric(metric_name: str, value: Any, subdir: str = "metrics") → None`

Append data to JSONL metrics file (one JSON object per line).

```python
# Append quality score
store.append_metric("quality", {
    "task_id": "task-001",
    "score": 95,
    "timestamp": datetime.now().isoformat()
}, subdir="metrics")

# Creates: ~/.agentic-engineers/session-001/memory/metrics/quality.jsonl
# Each line is a valid JSON object
```

**Parameters:**
- `metric_name`: Metric name (JSONL filename)
- `value`: Value to append (JSON serializable)
- `subdir`: Subdirectory (default: "metrics")

---

##### `list_all(subdir: str) → List[Path]`

List all files in a memory subdirectory.

```python
# List all metrics
metrics = store.list_all("metrics")
for metric_file in metrics:
    print(metric_file.name)

# List all delegate records
delegates = store.list_all("delegates")
```

**Parameters:**
- `subdir`: Subdirectory to list

**Returns:** List of Path objects

---

##### `aggregate_session() → Dict[str, Any]`

Aggregate all session memory (delegates, handbacks, metrics).

```python
index = store.aggregate_session()

# Returns complete session index
```

**Returns:** Dict with aggregated memory

---

### SessionMemoryAggregator (Collection)

Advanced aggregation and querying.

```python
from src.orchestration.memory.aggregator import SessionMemoryAggregator

aggregator = SessionMemoryAggregator(session_id="session-001")
```

#### Methods

##### `collect_delegates() → List[Dict]`

Collect all DELEGATEs from queue and artifacts.

```python
delegates = aggregator.collect_delegates()
for delegate in delegates:
    print(f"{delegate['task_id']}: {delegate['role']}")
```

**Returns:** List of DELEGATE records

---

##### `collect_handbacks() → List[Dict]`

Collect all HANDBACKs from queue and artifacts.

```python
handbacks = aggregator.collect_handbacks()
for handback in handbacks:
    print(f"{handback['task_id']}: {handback['status']}")
```

**Returns:** List of HANDBACK records

---

##### `collect_logs() → List[Dict]`

Collect all execution logs.

```python
logs = aggregator.collect_logs()
for log in logs:
    print(f"{log['source']}: {log['size']} bytes")
```

**Returns:** List of log records

---

##### `aggregate_all() → Dict[str, Any]`

Full aggregation across all memory sources.

```python
index = aggregator.aggregate_all()

# Access data
print(f"Tasks: {len(index['delegates'])}")
print(f"Completed: {len(index['handbacks'])}")
```

**Returns:** Complete aggregated index

---

## Common Patterns

### Pattern 1: Adding Memory Collection to a New Agent

```python
# In your agent code
import os
import logging
from datetime import datetime
from src.orchestration.memory import ArtifactMemoryStore

class MyAgent:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.session_id = os.environ.get("SESSION_ID", "default")
        
        # Initialize memory store
        self.store = ArtifactMemoryStore(self.session_id)
        
        # Set up logging to memory
        self._setup_logging()
    
    def _setup_logging(self):
        """Route logs to memory."""
        log_dir = self.store.memory_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(log_dir / f"agent-{self.task_id}.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        logger = logging.getLogger(__name__)
        logger.addHandler(handler)
        self.logger = logger
    
    def execute(self, scope: str):
        """Execute task and record thinking."""
        self.logger.info(f"Starting task: {self.task_id}")
        
        # Do work...
        result = self._do_work(scope)
        
        # Record thinking output
        self.store.write(f"thinking-{self.task_id}", {
            "task_id": self.task_id,
            "scope": scope,
            "reasoning": "...",
            "decision": "...",
            "timestamp": datetime.utcnow().isoformat(),
        }, subdir="thinking")
        
        self.logger.info(f"Task complete: {self.task_id}")
        return result
```

### Pattern 2: Adding Memory Collection to a New Skill

```python
# In your skill script
import os
import json
from src.orchestration.memory import ArtifactMemoryStore

def my_skill(input_data, session_id=None):
    """Execute skill and record to memory."""
    session_id = session_id or os.environ.get("SESSION_ID", "default")
    store = ArtifactMemoryStore(session_id)
    
    # Do skill work
    result = process_input(input_data)
    
    # Record execution
    store.write("skill-execution", {
        "input": input_data,
        "output": result,
        "status": "success",
    }, subdir="metrics")
    
    return result
```

### Pattern 3: Querying Memory in Post-Processing

```python
# In orchestrator or post-processor
from src.orchestration.memory import SessionMemoryManager

def analyze_session(session_id: str):
    """Analyze completed session."""
    manager = SessionMemoryManager(session_id)
    manager.initialize()
    manager.aggregate_memory()
    
    # Get all tasks
    delegates = manager.get_delegates()
    
    # Calculate stats
    total = len(delegates)
    completed = len(manager.get_handbacks(status="complete"))
    rate = completed / total * 100 if total > 0 else 0
    
    # Get role breakdown
    roles = {}
    for delegate in delegates:
        role = delegate["role"]
        roles[role] = roles.get(role, 0) + 1
    
    # Print report
    print(f"Session: {session_id}")
    print(f"Tasks: {total}")
    print(f"Completed: {completed} ({rate:.1f}%)")
    print(f"By role: {roles}")
    
    # Export summary
    manager.export_summary()
```

### Pattern 4: Custom Querying with Filters

```python
from src.orchestration.memory import SessionMemoryManager

manager = SessionMemoryManager("session-001")
manager.initialize()
manager.aggregate_memory()

# Find high-effort tasks that failed
delegates = manager.get_delegates(effort="high")
failed_handbacks = manager.get_handbacks(status="failed")
failed_task_ids = {h["task_id"] for h in failed_handbacks}

high_effort_failures = [
    d for d in delegates if d["task_id"] in failed_task_ids
]

for task in high_effort_failures:
    print(f"Failed high-effort task: {task['task_id']}")
    print(f"  Role: {task['role']}")
    print(f"  Scope: {task['scope'][:80]}...")
```

---

## Environment Variables Reference

| Variable | Purpose | Default | Example |
|----------|---------|---------|---------|
| `AGENTIC_ENGINEERS_HOME` | Memory root directory | `~/.agentic-engineers` | `/custom/path` |
| `SESSION_ID` | Current session ID | `"default"` | `"session-001"` |
| `MEMORY_DEBUG` | Enable debug logging | `"0"` | `"1"` |
| `MEMORY_METRICS_DIR` | Override metrics dir | Auto-detected | `/custom/metrics` |
| `MEMORY_RETENTION_DAYS` | Retention policy (days) | `0` (infinite) | `90` |

**Usage:**
```bash
export AGENTIC_ENGINEERS_HOME=~/.my-memory
export SESSION_ID=production-001
export MEMORY_DEBUG=1

python my_script.py
```

---

## Error Handling

### Common Exceptions

```python
from src.orchestration.memory import SessionMemoryManager

manager = SessionMemoryManager("session-001")

try:
    manager.initialize()
except OSError as e:
    # Directory creation failed
    print(f"Failed to initialize: {e}")

try:
    manager.aggregate_memory()
except ValueError as e:
    # Invalid data format
    print(f"Aggregation failed: {e}")

try:
    result = manager.query_by_task_id("missing-task")
except KeyError:
    # Task not found (returns None instead)
    pass
```

### Debugging Memory Issues

```python
import os
from pathlib import Path

session_id = os.environ.get("SESSION_ID")
memory_dir = Path.home() / ".agentic-engineers" / session_id / "memory"

# Check directory exists
if not memory_dir.exists():
    print(f"❌ Memory directory missing: {memory_dir}")
    exit(1)

# List subdirectories
for subdir in memory_dir.glob("*"):
    count = len(list(subdir.glob("*"))) if subdir.is_dir() else 0
    print(f"{subdir.name}: {count} files")

# Check index
index_file = memory_dir / "index.json"
if index_file.exists():
    import json
    with open(index_file) as f:
        index = json.load(f)
        print(f"Index: {len(index['delegates'])} delegates, {len(index['handbacks'])} handbacks")
else:
    print("⚠️ index.json not found (need to aggregate)")
```

---

## Testing Memory Integration

### Unit Test Example

```python
import pytest
from pathlib import Path
import tempfile
from src.orchestration.memory import SessionMemoryManager

def test_memory_lifecycle():
    """Test complete memory lifecycle."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Override memory root for testing
        session_id = "test-session"
        manager = SessionMemoryManager(session_id)
        
        # Initialize
        assert manager.initialize()
        
        # Collect events
        manager.collect_memory_event("delegate", {
            "task_id": "test-1",
            "role": "Engineer",
            "timestamp": "2025-05-24T10:00:00Z",
        })
        
        manager.collect_memory_event("handback", {
            "task_id": "test-1",
            "status": "complete",
            "quality_score": 95,
            "timestamp": "2025-05-24T10:05:00Z",
        })
        
        # Aggregate
        index = manager.aggregate_memory()
        assert len(index["delegates"]) == 1
        assert len(index["handbacks"]) == 1
        
        # Query
        delegates = manager.get_delegates()
        assert len(delegates) == 1
        
        handbacks = manager.get_handbacks()
        assert len(handbacks) == 1
```

### Integration Test Example

```python
def test_memory_integration_with_orchestrator():
    """Test memory integration with orchestrator."""
    from src.orchestration.orchestrator import Orchestrator
    
    session_id = "integration-test"
    orch = Orchestrator(session_id)
    
    # Simulate task flow
    task = create_test_task("test-001")
    orch.delegate_task(task)
    
    # Verify DELEGATE recorded
    manager = orch.memory_manager
    manager.aggregate_memory()
    delegates = manager.get_delegates()
    assert len(delegates) == 1
    
    # Simulate completion
    handback = create_test_handback("test-001")
    orch.process_handback(handback)
    
    # Verify HANDBACK recorded
    manager.aggregate_memory()
    handbacks = manager.get_handbacks()
    assert len(handbacks) == 1
```

---

## Best Practices

1. **Always initialize before collecting events**
   ```python
   manager.initialize()  # Creates directories
   manager.collect_memory_event(...)  # Now safe
   ```

2. **Aggregate at session end**
   ```python
   manager.aggregate_memory()  # Build index
   manager.export_summary()     # Export report
   ```

3. **Query only after aggregation**
   ```python
   manager.aggregate_memory()
   delegates = manager.get_delegates()  # Now works
   ```

4. **Handle missing data gracefully**
   ```python
   try:
       result = manager.query_by_task_id("missing")
       if not result:
           print("Task not found")
   except (KeyError, FileNotFoundError):
       print("Query failed")
   ```

5. **Log to memory in agents and skills**
   ```python
   # All agents should write to memory/logs/
   self.store.append_metric("agent-log", log_line, subdir="logs")
   ```

---

## Performance Tips

1. **Batch memory events**
   ```python
   # Instead of many calls, batch them
   events = [...]
   for event in events:
       manager.collect_memory_event(...)
   manager.aggregate_memory()  # Once at end
   ```

2. **Use role/effort filters for large sessions**
   ```python
   # More efficient than filtering manually
   engineers = manager.get_delegates(role="Engineer")
   ```

3. **Cache aggregation results**
   ```python
   index = manager.aggregate_memory()
   # Reuse index instead of re-aggregating
   delegates = index["delegates"]
   ```

4. **Archive old sessions**
   ```bash
   # Move completed sessions to reduce active memory
   mv ~/.agentic-engineers/old-session ~/.agentic-engineers/archive/
   ```

---

## See Also

- [MEMORY-USAGE-GUIDE.md](MEMORY-USAGE-GUIDE.md) — User-focused guide
- [MEMORY-ARCHITECTURE-OVERVIEW.md](MEMORY-ARCHITECTURE-OVERVIEW.md) — System design
- [MEMORY-MIGRATION-GUIDE.md](MEMORY-MIGRATION-GUIDE.md) — Migration from old systems
- `src/orchestration/memory/` — Source code
- `tests/test_artifact_memory.py` — Comprehensive tests
