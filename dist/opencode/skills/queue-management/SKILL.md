---
name: queue-management
description: Atomic queue operations for DELEGATE/HANDBACK lifecycle with cycle detection, rate limiting, and validation. Enables decentralized sub-task creation and reduces orchestrator bottleneck.
license: Proprietary
compatibility: agentic-engineers framework v5.10+. Requires Python 3.8+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: task-management
  role: orchestrator
  model: claude-haiku-4.5
  effort: high
  thinking: false
  dependencies: []
---

# queue-management

## Overview

Queue Management skill provides atomic queue operations and consistency enforcement for
the DELEGATE/HANDBACK workflow. It consolidates validation logic, cycle detection,
and rate limiting into a reusable, testable module that reduces orchestrator complexity
and enables decentralized sub-task creation.

**What it does:**

1. **Atomic Queue Operations** — Create DELEGATEs, move tasks between states (incoming →
   processing → done/failed) with POSIX-level atomicity (no partial writes).
2. **Validation (Groups A/B/C)** — Consolidates validation rules: task_id format,
   required fields, scope/plan/context word counts, effort/model/role combinations.
3. **Cycle Detection** — Prevents cycles in @parent task chains (A→B→C→A). Enforces
   max depth (5 tiers) and max width (10 children per parent).
4. **Rate Limiting** — Per-session (max 100 tasks/hour) and per-parent (max 10 children)
   rate limits with sliding-window tracking.
5. **Query & Aggregation** — Query tasks by state, parent_task_id, or role for
   sub-task aggregation workflows.

**Why it matters:**

- **Decoupled Validation** — Validation logic extracted from orchestrator, enabling
  independent testing and reuse across agents.
- **Cycle Safety** — Automatic detection prevents infinite loops in task delegation
  chains, enabling safe sub-task delegation.
- **Atomic Semantics** — File-based queue with atomic operations (temp-file-then-move)
  ensures no partial writes on crash.
- **Rate Protection** — Built-in limits prevent resource exhaustion and cascade failures.
- **Session Isolation** — All operations scoped to session_id, enabling concurrent
  multi-session workflows.

---

## Invocation

### Programmatic Interface

```python
from skills.queue_management.scripts import QueueOperations

# Initialize
queue = QueueOperations(session_id="my-session", queue_path="~/.copilot/queue")

# Create DELEGATE
result = queue.create_delegate(
    task_id="feature-x-001",
    role="Senior Engineer",
    scope="Implement feature X with comprehensive documentation and testing",
    plan=[
        "Design API contract and data model",
        "Implement core business logic with error handling",
        "Write integration tests and performance benchmarks",
        "Document API and create usage guide",
    ],
    context="Feature X is critical for Q3 roadmap. See SPEC.md for requirements.",
    parent_task_id=None,  # Optional: for sub-tasks
)

# Move task through states
queue.move_task("feature-x-001", "incoming", "processing")
queue.move_task("feature-x-001", "processing", "done")

# Query tasks
done_tasks = queue.query_tasks("done", parent_task_id=None, role="Senior Engineer")

# Get rate limit status
status = queue.get_rate_limit_status("my-session")
# {
#   "tasks_this_hour": 5,
#   "limit": 100,
#   "remaining": 95
# }
```

### CLI Interface (future)

```bash
queue-ops create-delegate \
  --task-id feature-x-001 \
  --role "Senior Engineer" \
  --scope "Implement feature X..." \
  --plan "Design API" "Implement logic" \
  --context "Critical for Q3..."

queue-ops move-task feature-x-001 incoming processing

queue-ops query --state done --role "Senior Engineer"
```

---

## Validation Rules

### Group A: Format & Required Fields

**Rules:**
- `task_id`: Kebab-case, 3-50 characters, matches `[a-z0-9-]+`
- `role`: Must be one of valid roles (Engineer, Senior Engineer, Lead Engineer,
  Principal Engineer, Quality Engineer, Security Engineer, etc.)
- `scope`: Required, non-empty string
- `plan`: Required, list of ≥2 steps
- `context`: Required, non-empty string

**Example:**
```python
{
    "task_id": "auth-refactor-001",  # ✓ kebab-case
    "role": "Senior Engineer",        # ✓ valid role
    "scope": "Refactor authentication system...",  # ✓ non-empty
    "plan": ["Step 1", "Step 2"],     # ✓ list with ≥2 items
    "context": "Required for security...",  # ✓ non-empty
}
```

### Group B: Scope & Context Completeness

**Rules:**
- `scope`: ≥15 words (split by whitespace)
- `plan`: ≥2 steps, each ≥3 words
- `context`: ≥20 words

**Example:**
```python
{
    # ✓ 16 words
    "scope": "Refactor authentication system to support OAuth2 and implement MFA for enhanced security",
    
    # ✓ Each step ≥3 words
    "plan": [
        "Implement OAuth2 provider integration with third party services",
        "Add multi factor authentication support for user accounts",
        "Write comprehensive integration tests and documentation",
    ],
    
    # ✓ 20+ words
    "context": "Authentication is critical for security. See SPEC.md for detailed requirements and timeline constraints.",
}
```

### Group C: Effort & Model Validity

**Rules:**
- `effort` (optional): One of {`low`, `medium`, `high`}
- `model` (optional): One of valid models (gpt-5.4, claude-sonnet-4.6, claude-haiku-4.5, etc.)

**Valid Models:**
- GPT series: gpt-5.5, gpt-5.4, gpt-5.3-codex, gpt-5.2-codex, gpt-5.2, gpt-5.4-mini, gpt-5-mini, gpt-4.1
- Claude series: claude-sonnet-4.6, claude-sonnet-4.5, claude-haiku-4.5, claude-opus-4.7

---

## Cycle Detection

### Algorithm

Prevents cycles in @parent task chains by:
1. Following parent chain up to max_depth (default 5)
2. Detecting revisits (A→B→C→A indicates cycle)
3. Rejecting if task_id appears in parent chain

### Limits

- **Max Depth:** 5 tiers (task_tier ≤ 5)
- **Max Width:** 10 children per parent task
- **Validation:** Parent must exist in queue (incoming, processing, or done states)

### Examples

```python
# ✓ No cycle: linear chain
A→B→C (D can link to C)

# ✓ No cycle: tree structure
    A
   / \
  B   C (D can link to B or C)

# ✗ Cycle detected: 2-node
A→B→A

# ✗ Cycle detected: 3-node
A→B→C→A

# ✗ Width limit exceeded
A (parent)
├─ B
├─ C
├─ ...
├─ K (10th child) ✓
└─ L (11th child) ✗ REJECTED

# ✗ Depth limit exceeded
A (tier 0)
└─ B (tier 1)
   └─ C (tier 2)
      └─ D (tier 3)
         └─ E (tier 4)
            └─ F (tier 5) ✓
               └─ G (tier 6) ✗ REJECTED
```

---

## Rate Limiting

### Per-Session Limit

- **Max 100 tasks/hour** per session
- Sliding window: counts tasks created in last 60 minutes
- Resets automatically at 60-minute boundary

### Per-Parent Limit

- **Max 10 sub-tasks** per parent task
- Applies per parent, not per session
- Checked when creating child with `parent_task_id`

### Status API

```python
status = queue.get_rate_limit_status("my-session")
# {
#     "tasks_this_hour": 42,
#     "limit": 100,
#     "remaining": 58,
#     "reset_at": "2024-05-23T15:30:00"
# }

# When creating with parent:
allowed, status = queue.rate_limiter.check_limit(
    "my-session",
    parent_task_id="parent-task"
)
# status also includes:
# {
#     "children_count": 8,
#     "children_limit": 10,
#     "children_remaining": 2
# }
```

---

## Error Handling

### Common Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| `FileExistsError: Task X already exists` | Duplicate task_id | Use unique task_id or check existing tasks |
| `ValueError: DELEGATE validation failed: scope must be ≥15 words` | Scope too short | Expand scope description to ≥15 words |
| `RuntimeError: Rate limit exceeded: 100/100 tasks/hour` | Session limit hit | Wait for hour window to roll over |
| `RuntimeError: Cycle detected: A → B creates cycle` | Parent chain has cycle | Choose different parent or adjust task hierarchy |
| `ValueError: Invalid parent task: Parent task X not found` | Parent doesn't exist | Create parent first, then child |

### Validation Errors

All validation errors are raised as `ValueError` with detailed messages:

```python
try:
    queue.create_delegate(
        task_id="short",        # ✗ 5 chars, < 3 valid
        scope="too short",      # ✗ 2 words, < 15 required
        ...
    )
except ValueError as e:
    # ValueError: DELEGATE validation failed: task_id must be 3-50 characters, scope must be ≥15 words
```

---

## Queue States

Tasks move through these states:

```
incoming  →  processing  →  done
           ↘  failed     ↗
```

- **incoming:** Task created, ready to process
- **processing:** Task actively being worked on
- **done:** Task completed successfully
- **failed:** Task failed and needs retry or escalation

---

## API Reference

### QueueOperations

#### `__init__(session_id: str, queue_path: str = "~/.copilot/queue")`
Initialize queue operations for a session.

#### `create_delegate(...) -> Dict`
Create DELEGATE and move to incoming/ queue.
**Returns:** `{"status": "created", "task_id": str, "timestamp": str, "queue_path": str}`

#### `move_task(task_id: str, from_state: str, to_state: str) -> Dict`
Atomic move task between queue states.
**Returns:** `{"status": "moved", "task_id": str, "from_state": str, "to_state": str, "timestamp": str}`

#### `query_tasks(state: str, parent_task_id: Optional[str] = None, role: Optional[str] = None) -> List[Dict]`
Query tasks by state, parent, and/or role.
**Returns:** List of task metadata dicts

#### `validate_delegate(delegate: Dict) -> Tuple[bool, List[str]]`
Pre-flight validation of DELEGATE.
**Returns:** `(valid: bool, errors: List[str])`

#### `validate_handback(task_id: str, handback: Dict) -> Tuple[bool, List[str]]`
Pre-flight validation of HANDBACK.
**Returns:** `(valid: bool, errors: List[str])`

#### `get_rate_limit_status(session_id: str) -> Dict`
Get current rate limit usage.
**Returns:** `{"tasks_this_hour": int, "limit": 100, "remaining": int}`

---

## Testing

### Test Coverage

30+ test cases covering:
- ✅ Queue operations (create, move, query)
- ✅ Validators (Groups A/B/C, HANDBACK)
- ✅ Cycle detection (linear, tree, cycles, limits)
- ✅ Rate limiting (session, per-parent, tracking)
- ✅ Integration workflows (parent-child, aggregation, concurrent)
- ✅ Error handling (validation, recovery, isolation)

### Running Tests

```bash
pytest skills/queue-management/tests/ -v

# Run specific test file
pytest skills/queue-management/tests/test_queue_ops.py -v

# Run with coverage
pytest skills/queue-management/tests/ --cov=skills.queue_management --cov-report=html
```

---

## Performance

- **create_delegate:** < 100ms per call (validation + atomicity)
- **cycle_detection:** < 50ms per call (max 5-tier traversal)
- **validate_delegate:** < 50ms per call (regex + word count)
- **move_task:** < 10ms per call (atomic file move)
- **query_tasks:** O(n) where n = tasks in state (< 1000 typical)

---

## Constraints & Compatibility

- **No External Dependencies:** Uses only Python stdlib (json, pathlib, tempfile)
- **POSIX Only:** Atomicity relies on POSIX `os.replace()` semantics
- **File-Based Queue:** No database required, fully local
- **Backward Compatible:** Doesn't break existing queue structure
- **Python 3.8+:** Uses type hints (works with 3.8+)

---

## Future Enhancements (Phase 2+)

- CLI tool for queue operations
- Metrics/telemetry integration
- Distributed queue support (multi-machine)
- Priority-based scheduling
- Task dependency graphs (not just @parent)
- Webhook notifications on state changes

---

## References

- **QUEUE-OPS-API.md** — Detailed API specification
- **EXAMPLES.md** — Usage examples and patterns
- **PROTOCOL-ANALYSIS.md** — Protocol analysis that motivated this skill

---

## CLI Tool: add-to-queue

The `scripts/add-to-queue` CLI tool automates task queuing. Instead of manually creating both a DELEGATE JSON file and a TODO.md entry, users call this tool once and it handles both atomically.

**What it does:**
1. Parses task specifications (JSON or CLI args)
2. Validates against QUEUE-PROTOCOL format
3. Generates DELEGATE JSON file in `~/.copilot/queue/{session-id}/incoming/`
4. Adds entry to repo TODO.md (correct phase section)
5. Commits both files atomically in single git commit
6. Detects and prevents duplicate task_ids

### CLI Usage

```bash
# Add task via command-line arguments
add-to-queue --task-id my-feature-001 \
  --role Engineer \
  --scope "Implement new authentication system" \
  --effort high \
  --priority high

# Add task via JSON spec file
add-to-queue --spec-file task-spec.json
```

### Programmatic Usage (QueueManager)

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

### Required Fields

- `task_id` — Kebab-case identifier (must be unique)
- `role` — Assignment role (Engineer, Senior Engineer, Lead Engineer, etc.)
- `scope` — Task description
- `plan` — List of implementation steps (at least 1)
- `success_criteria` — List of success metrics (at least 1)

### Optional Fields

- `effort` — low, medium, high (default: medium)
- `priority` — low, normal, high (default: normal)
- `phase` — Phase number for TODO.md section (default: 2)
- `constraints` — List of constraints or limitations
- `context` — Additional context

### Scripts

- `scripts/add-to-queue` — CLI entry point
- `queue_manager.py` — Core QueueManager class with TODO.md integration
- `cli.py` — CLI argument parsing and dispatch
