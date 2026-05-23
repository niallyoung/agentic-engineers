# Queue Operations API Reference

## QueueOperations Class

Main class for atomic queue operations.

### Initialization

```python
from skills.queue_management.scripts import QueueOperations

queue = QueueOperations(
    session_id="my-session",
    queue_path="~/.copilot/queue"  # Optional, default shown
)
```

**Parameters:**
- `session_id` (str, required): Unique session identifier for isolation
- `queue_path` (str, optional): Root queue directory path, default "~/.copilot/queue"

**Raises:**
- `ValueError`: If session_id is empty or not a string

---

## Methods

### create_delegate

Create a DELEGATE and atomically write to incoming/ queue.

```python
result = queue.create_delegate(
    task_id="feature-001",
    role="Senior Engineer",
    scope="Implement feature with comprehensive testing...",
    plan=["Step 1", "Step 2", "Step 3"],
    context="Required context...",
    parent_task_id=None,  # Optional
    priority=0  # Optional, 0-10
)
```

**Parameters:**
- `task_id` (str, required): Kebab-case identifier, 3-50 chars, unique
- `role` (str, required): Agent role (must be valid)
- `scope` (str, required): Task description, ≥15 words
- `plan` (List[str], required): ≥2 implementation steps, each ≥3 words
- `context` (str, required): Context/rationale, ≥20 words
- `parent_task_id` (str, optional): Parent task ID for sub-tasks
- `priority` (int, optional): Priority level 0-10, default 0

**Returns:**
```python
{
    "status": "created",
    "task_id": "feature-001",
    "timestamp": "2024-05-23T10:15:30.123456",
    "queue_path": "/home/user/.copilot/queue/my-session/incoming/feature-001.json",
    "parent_task_id": None or "parent-id"
}
```

**Raises:**
- `ValueError`: Validation failed (Groups A/B/C)
- `FileExistsError`: Task with task_id already exists
- `RuntimeError`: Rate limit exceeded or cycle detected

---

### validate_delegate

Pre-flight validation of DELEGATE dict without creating.

```python
valid, errors = queue.validate_delegate(delegate_dict)

if not valid:
    for error in errors:
        print(f"Validation error: {error}")
```

**Parameters:**
- `delegate` (Dict): DELEGATE dict to validate

**Returns:**
```python
(
    True,  # or False if invalid
    []  # List of error messages (empty if valid)
)
```

---

### move_task

Atomically move task between queue states.

```python
result = queue.move_task(
    task_id="feature-001",
    from_state="incoming",
    to_state="processing"
)
```

**Parameters:**
- `task_id` (str): Task identifier
- `from_state` (str): Current state (incoming, processing, done, failed)
- `to_state` (str): Target state

**Returns:**
```python
{
    "status": "moved",
    "task_id": "feature-001",
    "from_state": "incoming",
    "to_state": "processing",
    "timestamp": "2024-05-23T10:20:45.654321"
}
```

**Raises:**
- `FileNotFoundError`: Task not found in from_state
- `ValueError`: Invalid state name

---

### query_tasks

Query tasks by state, parent, and/or role.

```python
# All tasks in processing state
tasks = queue.query_tasks("processing")

# All sub-tasks of parent
children = queue.query_tasks("incoming", parent_task_id="parent-001")

# All Engineer tasks in done state
eng_done = queue.query_tasks("done", role="Engineer")

# All children of parent who are Engineers
specific = queue.query_tasks(
    "processing",
    parent_task_id="parent-001",
    role="Senior Engineer"
)
```

**Parameters:**
- `state` (str): Queue state (incoming, processing, done, failed)
- `parent_task_id` (str, optional): Filter by parent task ID
- `role` (str, optional): Filter by agent role

**Returns:**
```python
[
    {
        "task_id": "feature-001",
        "role": "Senior Engineer",
        "scope": "...",
        "plan": [...],
        "context": "...",
        "parent_task_id": None,
        "priority": 0,
        "created_at": "2024-05-23T10:15:30.123456",
        "status": "processing"
    },
    # ... more tasks
]
```

---

### validate_handback

Pre-flight validation of HANDBACK dict.

```python
valid, errors = queue.validate_handback("task-id", handback_dict)

if not valid:
    raise ValueError(f"HANDBACK invalid: {errors}")
```

**Parameters:**
- `task_id` (str): Task identifier
- `handback` (Dict): HANDBACK dict to validate

**Returns:**
```python
(
    True,  # or False if invalid
    []  # List of error messages
)
```

**HANDBACK Format:**
```python
{
    "task_id": "feature-001",
    "status": "complete",  # or "escalated"
    "quality_score": 85,  # 0-100
    "deliverables": ["file1.py", "tests.py"],
    "test_results": {  # Optional
        "passed": 10,
        "total": 10
    },
    "metrics": {  # Optional
        "tokens_used": 5000,
        "time_seconds": 3600
    }
}
```

---

### get_rate_limit_status

Get current rate limit usage for session.

```python
status = queue.get_rate_limit_status("my-session")

print(f"Tasks this hour: {status['tasks_this_hour']}/{status['limit']}")
print(f"Remaining: {status['remaining']}")
print(f"Resets at: {status['reset_at']}")
```

**Parameters:**
- `session_id` (str): Session identifier

**Returns:**
```python
{
    "tasks_this_hour": 42,
    "limit": 100,
    "remaining": 58,
    "reset_at": "2024-05-23T11:15:30.000000"
}
```

---

## Validators

### DelegateValidator

```python
from skills.queue_management.scripts import DelegateValidator

validator = DelegateValidator(queue_path=queue.session_queue_path)

# Validate all groups
valid, errors = validator.validate_groups(delegate_dict)

# Validate individual groups
group_a_errors = validator.check_group_a(delegate_dict)
group_b_errors = validator.check_group_b(delegate_dict)
group_c_errors = validator.check_group_c(delegate_dict)
```

---

### HandbackValidator

```python
from skills.queue_management.scripts import HandbackValidator

validator = HandbackValidator()
valid, errors = validator.validate(handback_dict)
```

---

### CycleDetector

```python
from skills.queue_management.scripts import CycleDetector

detector = CycleDetector(queue_path=queue.session_queue_path)

# Check for cycle
has_cycle = detector.has_cycle("new-task", "parent-task")

# Validate parent exists
valid, error = detector.validate_parent("parent-task")

# Check width limit
valid, count = detector.check_width_limit("parent-task")
```

---

## Rate Limiter

### RateLimiter

```python
from skills.queue_management.scripts import RateLimiter

limiter = RateLimiter(
    max_per_hour=100,  # Per-session limit
    max_children_per_parent=10,  # Per-parent limit
    state_dir="~/.copilot/rate-limits"
)

# Check if allowed
allowed, status = limiter.check_limit("session-1")
allowed, status = limiter.check_limit("session-1", parent_task_id="parent-1")

# Record task
limiter.record_task("session-1", "task-1")
limiter.record_task("session-1", "task-2", parent_task_id="parent-1")

# Get status
status = limiter.get_status("session-1")
```

---

## Atomic Operations

### AtomicQueueOps

```python
from skills.queue_management.scripts import AtomicQueueOps

ops = AtomicQueueOps(queue_path=Path("~/.copilot/queue/session-1"))

# Write atomically (temp-then-move)
ops.write_atomic(Path("file.json"), json.dumps(data))

# Move atomically
ops.move_file(Path("from"), Path("to"))

# Read
content = ops.read_atomic(Path("file.json"))

# Delete
ops.delete_atomic(Path("file.json"))

# Rename
ops.rename_atomic(Path("old"), Path("new"))
```

---

## Error Classes

All errors are built-in Python exceptions:
- `ValueError`: Validation errors (Groups A/B/C, invalid params)
- `FileExistsError`: Duplicate task_id or file exists
- `FileNotFoundError`: Task or parent not found
- `RuntimeError`: Rate limit exceeded or cycle detected
- `IOError`: Atomic write/move failures

---

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| create_delegate | <100ms | Includes validation + atomic write |
| move_task | <10ms | File rename only |
| query_tasks | O(n) | n = tasks in state |
| validate_delegate | <50ms | Regex + word count |
| cycle_detection | <50ms | Max 5-tier traversal |

---

## Constants

Rate limits and constraints are configurable:

```python
# Default constants in RateLimiter
DEFAULT_MAX_PER_HOUR = 100
DEFAULT_MAX_CHILDREN_PER_PARENT = 10

# In CycleDetector
max_depth = 5  # Max task tiers
max_width = 10  # Max children per parent
```

---

## Type Hints

All methods use Python type hints (3.8+):

```python
from typing import Dict, List, Optional, Tuple

def create_delegate(
    self,
    task_id: str,
    role: str,
    scope: str,
    plan: List[str],
    context: str,
    parent_task_id: Optional[str] = None,
    priority: int = 0,
) -> Dict: ...

def query_tasks(
    self,
    state: str,
    parent_task_id: Optional[str] = None,
    role: Optional[str] = None,
) -> List[Dict]: ...

def validate_delegate(
    self,
    delegate: Dict
) -> Tuple[bool, List[str]]: ...
```
