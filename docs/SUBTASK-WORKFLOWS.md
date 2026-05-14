# Sub-Task Workflows

> **Phase 2** of the decentralised sub-task creation system.  
> Enables agents to create child tasks directly, reducing Orchestrator load by
> 60–70% and unlocking parallel task execution.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Schema Reference](#3-schema-reference)
4. [Creating Sub-Tasks](#4-creating-sub-tasks)
5. [Result Aggregation](#5-result-aggregation)
6. [Depth and Width Limits](#6-depth-and-width-limits)
7. [Failure Modes](#7-failure-modes)
8. [Orchestrator Integration](#8-orchestrator-integration)
9. [Examples](#9-examples)
10. [Testing](#10-testing)

---

## 1. Overview

Prior to Phase 2, all task decomposition had to be orchestrated centrally,
creating a single-point bottleneck. Phase 2 allows any agent to break its work
into smaller, parallel sub-tasks by directly writing to the queue. The
Orchestrator automatically detects when a parent task has children and waits for
them before aggregating results.

**Key properties:**

- **Decentralised creation**: any agent can queue child tasks directly
- **Automatic tier tracking**: `task_tier` is calculated and stored automatically
- **Effort-weighted aggregation**: quality scores use effort-level weights
- **Depth and width enforcement**: max 5 levels deep, 10 children per parent
- **Cycle prevention**: parent→child chains are validated against ancestor graphs
- **Backward compatible**: root tasks (no parent) work exactly as before

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                         │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  _process_task()                                     │    │
│  │    ├─ has_children(task_id) ──► False ──► do_work()  │    │
│  │    └─ has_children(task_id) ──► True                 │    │
│  │         └─ execute_with_result_aggregation()         │    │
│  │              ├─ wait_for_children(timeout=60m)       │    │
│  │              └─ aggregate_child_results()            │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘

Queue layout:
  incoming/    ← new tasks arrive here
  processing/  ← task is being worked on
  done/        ← completed tasks (HANDBACK written here)

Sub-task keys:
  parent_task_id  → links child to parent
  task_tier       → depth in tree (0 = root, 1 = child, …)
```

**Two queue implementations exist** (they coexist):

| Layer | File | Format | Used by |
|-------|------|--------|---------|
| Skill layer | `skills/queue-management/scripts/queue_ops.py` | JSON | Tests, queue-management skill |
| Orchestrator layer | `src/orchestration/agents/orchestrator.py::QueueManager` | YAML | Live OrchestratorAgent |

Phase 2 changes target **both** layers but do not merge them.

---

## 3. Schema Reference

### 3.1 DELEGATE — new optional fields

```yaml
# src/orchestration/delegate-schema.yaml → subtask_fields
parent_task_id:
  type: string
  description: ID of the parent task (omit for root tasks)
  pattern: "^[a-z0-9][a-z0-9-]{1,}[a-z0-9]$"
  minLength: 3

task_tier:
  type: integer
  description: Depth of this task in the hierarchy (auto-calculated)
  minimum: 0
  maximum: 5
```

### 3.2 HANDBACK — new optional fields

```yaml
# src/orchestration/handback-schema.yaml → subtask_fields
children_created:
  type: array
  items: {type: string}
  description: Task IDs of all sub-tasks created during execution

children_results:
  type: object
  description: >
    Keyed by task_id. Each value must include:
      status   — complete | failed | timed_out
      output   — arbitrary dict
      quality  — int 0–100

children_failed:
  type: array
  items: {type: string}
  description: Task IDs that failed or were blocked

result_aggregation_status:
  type: string
  enum: [all_complete, partial, timed_out]
```

---

## 4. Creating Sub-Tasks

### 4.1 Via `QueueOperations` (JSON skill layer)

```python
from scripts.queue_ops import QueueOperations

ops = QueueOperations(queue_dir="/path/to/queue", session_id="my-session")

# Create the parent task
ops.create_delegate(
    task_id="master-task-001",
    role="senior_engineer",
    scope="Analyse all microservices and produce a combined report covering ...",
    plan=["Step 1: ...", "Step 2: ..."],
    context="We are refactoring the auth service...",
)

# Agent creates child tasks
for service in ["auth", "billing", "notifications"]:
    ops.create_delegate(
        task_id=f"subtask-{service}-001",
        role="engineer",
        scope=f"Analyse the {service} service and identify bottlenecks in ...",
        plan=["Read codebase", "Profile endpoints", "Document findings"],
        context="Parent task: master-task-001",
        parent_task_id="master-task-001",   # ← link to parent
        # task_tier is auto-calculated (parent_tier + 1)
    )
```

### 4.2 Via YAML (Orchestrator layer)

The Orchestrator's own `QueueManager` writes YAML files. The agent appends
`parent_task_id` and `task_tier` to the DELEGATE before writing:

```yaml
task_id: subtask-auth-001
handoff_type: DELEGATE
role: engineer
scope: "Analyse the auth service and identify bottlenecks..."
plan:
  - Read codebase
  - Profile endpoints
  - Document findings
parent_task_id: master-task-001   # NEW
task_tier: 1                       # NEW (auto-calculated)
```

### 4.3 Validation

`SubTaskValidator` (in `skills/queue-management/scripts/subtask_validators.py`)
runs the following checks before a sub-task is accepted:

| Check | Rule |
|-------|------|
| Parent existence | Parent must be found in `incoming/`, `processing/`, or `done/` |
| No self-reference | `task_id != parent_task_id` |
| No cycle | Parent must not be a descendant of this task |
| Tier depth | `task_tier ≤ 5` (auto-calculated; manual override raises `ValueError`) |
| Child count | Parent must have fewer than 10 existing children |
| Scope subset | Child scope must be a subset of parent scope (word overlap ≥ 20%) |

---

## 5. Result Aggregation

`ResultAggregator` (`skills/queue-management/scripts/result_aggregator.py`)
combines child HANDBACKs into a single summary.

### 5.1 Aggregation steps

```python
from scripts.result_aggregator import ResultAggregator

aggregator = ResultAggregator(queue_dir="/path/to/queue")
result = aggregator.aggregate(
    parent_task_id="master-task-001",
    children_handbacks=[
        {"task_id": "subtask-auth-001", "status": "complete", "quality": 92, ...},
        {"task_id": "subtask-billing-001", "status": "complete", "quality": 78, ...},
    ],
    failure_mode="partial",   # or "all_or_nothing"
)
```

### 5.2 Output structure

```python
{
    "children_created": ["subtask-auth-001", "subtask-billing-001"],
    "children_results": {
        "subtask-auth-001":    {"status": "complete", "output": {...}, "quality": 92},
        "subtask-billing-001": {"status": "complete", "output": {...}, "quality": 78},
    },
    "children_failed": [],
    "result_aggregation_status": "all_complete",
    "aggregate_quality_score": 85.0,         # effort-weighted average
    "aggregate_tokens_used": 12400,          # sum
    "aggregate_cost_usd": 0.0248,            # sum
}
```

### 5.3 Quality score formula

Scores are **effort-weighted averages** using the child task's `effort` field:

| Effort level | Weight |
|-------------|--------|
| `high`      | 3      |
| `medium`    | 2      |
| `low`       | 1      |

```
score = Σ(quality_i × weight_i) / Σ(weight_i)
```

---

## 6. Depth and Width Limits

| Constraint | Value | Error raised |
|-----------|-------|-------------|
| Maximum task_tier (depth) | 5 | `ValueError: task_tier 6 exceeds maximum (5)` |
| Maximum children per parent | 10 | `RuntimeError: master-task-001 already has 10 children (max 10 per parent)` |
| Maximum tasks per session/hour | 100 | `RuntimeError: Rate limit exceeded` |

### Visualising depth

```
Tier 0: master-task-001           ← root (no parent)
Tier 1: ├─ subtask-auth-001       ← child
Tier 1: └─ subtask-billing-001    ← child
Tier 2:    └─ subtask-billing-eu  ← grandchild
...
Tier 5:       └─ deep-leaf-task   ← max depth
```

---

## 7. Failure Modes

### 7.1 `partial` (default)

- Failed children are recorded in `children_failed`
- Successful children are aggregated normally
- `result_aggregation_status = "partial"`
- Parent task is **not** failed

### 7.2 `all_or_nothing`

- If **any** child fails, the entire aggregation fails
- `result_aggregation_status = "partial"` with `children_failed` populated
- Caller is responsible for deciding whether to fail the parent

### 7.3 Timeout

- `ChildWaiter` polls for completion with configurable interval and timeout
- Default: `timeout_minutes=60`, `poll_interval=1.0s`
- On timeout: `result_aggregation_status = "timed_out"`
- Available results are included in `children_results`

---

## 8. Orchestrator Integration

The `OrchestratorAgent` (`src/orchestration/agents/orchestrator.py`) gains four
new methods and an updated `_process_task` that branches on whether a task has
children.

### 8.1 New methods

```python
# Check if any task in any queue state has this parent_task_id
has_children(task_id: str) -> bool

# Poll done/ until all children complete or timeout
wait_for_children(parent_task_id: str, timeout_minutes: int = 60) -> list[dict]

# Build aggregated result from a list of completed HANDBACK dicts
aggregate_child_results(parent_task_id: str, children_handbacks: list) -> dict

# Full workflow: wait + aggregate + write HANDBACK
execute_with_result_aggregation(task_id: str, agent_name: str) -> dict
```

### 8.2 Updated `_process_task` branching

```python
def _process_task(self, task: dict) -> None:
    task_id = task.get("task_id")
    if self.has_children(task_id):
        result = self.execute_with_result_aggregation(task_id, agent_name=...)
    else:
        result = self.do_work(task)
    self.queue_manager.write_handback(task_id, result)
```

---

## 9. Examples

### 9.1 Three-child parallel analysis

```python
ops.create_delegate("analysis-001", role="senior_engineer",
    scope="Analyse all three payment services and create a consolidated risk report ...",
    plan=["Create sub-tasks", "Aggregate results", "Write report"])

for svc in ["stripe", "paypal", "crypto"]:
    ops.create_delegate(f"analysis-{svc}-001", role="engineer",
        scope=f"Analyse {svc} payment service and identify security risks ...",
        plan=["Review code", "Check deps", "Document findings"],
        parent_task_id="analysis-001")

# Orchestrator picks up analysis-001, sees 3 children, waits, aggregates.
```

### 9.2 Two-tier hierarchy

```python
# Tier 0
ops.create_delegate("epic-001", role="principal_engineer",
    scope="Design new authentication system architecture ...", ...)

# Tier 1 (parent=epic-001)
ops.create_delegate("epic-001-design", role="senior_engineer",
    scope="Design the OAuth2 flow for the auth system ...", ...,
    parent_task_id="epic-001")

# Tier 2 (parent=epic-001-design)
ops.create_delegate("epic-001-design-spec", role="engineer",
    scope="Write technical specification for the OAuth2 auth system ...", ...,
    parent_task_id="epic-001-design")
```

### 9.3 Handling partial results

```python
result = aggregator.aggregate(
    parent_task_id="analysis-001",
    children_handbacks=[
        {"task_id": "analysis-stripe-001", "status": "complete", "quality": 90, ...},
        {"task_id": "analysis-paypal-001", "status": "failed", "quality": 0, ...},
    ],
    failure_mode="partial",
)

assert result["result_aggregation_status"] == "partial"
assert result["children_failed"] == ["analysis-paypal-001"]
assert "analysis-stripe-001" in result["children_results"]
```

---

## 10. Testing

39 integration tests in `tests/test_subtask_workflows.py` cover all scenarios:

```bash
# Run sub-task workflow tests
python3 -m pytest tests/test_subtask_workflows.py -v

# Run full queue-management test suite (should show 43 passing)
python3 -m pytest skills/queue-management/tests/ -v

# Run combined (run separately to avoid sys.path conflicts)
python3 -m pytest skills/queue-management/tests/ tests/test_subtask_workflows.py -v
```

### Test categories

| Category | Tests |
|---------|-------|
| Single child creation | 2 |
| Multiple children | 2 |
| Task tier tracking | 3 |
| Result aggregation | 3 |
| Partial results | 1 |
| Timeout handling | 1 |
| Quality score calculation | 3 |
| Token/cost aggregation | 2 |
| Invalid parent_task_id | 2 |
| Invalid task_tier | 2 |
| Orphan child detection | 2 |
| Child completion ordering | 1 |
| Concurrent child creation | 1 |
| Session isolation | 2 |
| Backward compatibility | 2 |
| HANDBACK children validation | 3 |
| Aggregation status enum | 4 |
| Performance (10 children) | 2 |

---

*See also:*
- `docs/PROTOCOL.md` § 14 — Protocol spec additions
- `src/orchestration/delegate-schema.yaml` → `subtask_fields`
- `src/orchestration/handback-schema.yaml` → `subtask_fields`
- `skills/queue-management/scripts/subtask_validators.py`
- `skills/queue-management/scripts/result_aggregator.py`
