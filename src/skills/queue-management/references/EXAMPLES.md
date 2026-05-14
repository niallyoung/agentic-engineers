# Queue Operations: Usage Examples

## Basic Workflow

### Create and Track a Task

```python
from skills.queue_management.scripts import QueueOperations

# Initialize
queue = QueueOperations(session_id="my-session")

# Create a DELEGATE
result = queue.create_delegate(
    task_id="auth-refactor-001",
    role="Senior Engineer",
    scope="Refactor authentication system to support OAuth2, JWT tokens, and multi-factor authentication with comprehensive testing and documentation",
    plan=[
        "Design new OAuth2 architecture with provider integration points",
        "Implement JWT token generation and validation with secure storage",
        "Add multi-factor authentication support for enhanced security",
        "Write comprehensive unit and integration tests for all components",
        "Document API changes and create migration guide for users",
    ],
    context="Authentication is critical for user security. Current system lacks OAuth2 and MFA support. See SPEC.md for detailed requirements and security considerations.",
)

print(f"Created: {result['task_id']} at {result['queue_path']}")

# Move to processing
queue.move_task("auth-refactor-001", "incoming", "processing")

# Simulate work...
# queue.move_task("auth-refactor-001", "processing", "done")
```

---

## Parent-Child Task Workflow

### Create Subtasks for Parallel Work

```python
from skills.queue_management.scripts import QueueOperations

queue = QueueOperations(session_id="my-session")

# Create parent task
parent = queue.create_delegate(
    task_id="microservices-migration-001",
    role="Principal Engineer",
    scope="Plan and execute migration from monolith to microservices architecture with proper service boundaries and communication patterns",
    plan=[
        "Design microservices architecture with clear service boundaries",
        "Create subtasks for parallel service implementation",
        "Implement service mesh and inter-service communication",
        "Aggregate results and perform integration testing",
    ],
    context="Microservices migration is core to Q2-Q3 initiative.",
)

# Create subtasks for parallel work
subtasks = [
    {
        "task_id": "auth-service-001",
        "role": "Senior Engineer",
        "scope": "Implement authentication microservice with OAuth2 and JWT support for decoupled identity management",
        "plan": [
            "Design auth service API contract with OpenAPI spec",
            "Implement OAuth2 provider integration layer",
            "Create comprehensive test suite for auth flows",
        ],
        "context": "Auth service will be shared by all other microservices",
    },
    {
        "task_id": "api-gateway-001",
        "role": "Senior Engineer",
        "scope": "Implement API gateway for routing, rate limiting, and authentication across all microservices",
        "plan": [
            "Design gateway routing rules and request transformation",
            "Implement rate limiting and circuit breaker patterns",
            "Create monitoring and logging for gateway operations",
        ],
        "context": "Gateway is entry point for all external requests",
    },
    {
        "task_id": "data-service-001",
        "role": "Senior Engineer",
        "scope": "Implement data access microservice with database abstraction and caching layer for optimal performance",
        "plan": [
            "Design database schema for distributed access",
            "Implement data access layer with caching",
            "Create migration tools for data consistency",
        ],
        "context": "Data service will handle all persistent storage",
    },
]

# Create all subtasks
for subtask_spec in subtasks:
    subtask = queue.create_delegate(
        task_id=subtask_spec["task_id"],
        role=subtask_spec["role"],
        scope=subtask_spec["scope"],
        plan=subtask_spec["plan"],
        context=subtask_spec["context"],
        parent_task_id="microservices-migration-001",
    )
    print(f"Created subtask: {subtask['task_id']}")

# Query all subtasks
children = queue.query_tasks("incoming", parent_task_id="microservices-migration-001")
print(f"Total subtasks: {len(children)}")

# Process subtasks
for child in children:
    queue.move_task(child["task_id"], "incoming", "processing")
```

---

## Subtask Aggregation Workflow

### Aggregate Results from Multiple Subtasks

```python
from skills.queue_management.scripts import QueueOperations
import json

queue = QueueOperations(session_id="my-session")

# Create parent
queue.create_delegate(
    task_id="feature-integration-001",
    role="Lead Engineer",
    scope="Integrate multiple feature implementations into cohesive system with comprehensive testing and documentation",
    plan=[
        "Create subtasks for parallel feature development",
        "Monitor and coordinate subtask completion",
        "Aggregate results and perform system integration testing",
        "Deploy integrated system to staging environment",
    ],
    context="Multiple teams working on different features",
)

# Create subtasks for different teams
team_features = {
    "search-feat-001": "Senior Engineer",
    "export-feat-001": "Senior Engineer",
    "analytics-feat-001": "Engineer",
}

for feature_id, role in team_features.items():
    queue.create_delegate(
        task_id=feature_id,
        role=role,
        scope=f"Implement {feature_id} with comprehensive testing and documentation for integration",
        plan=[
            "Design feature architecture and API contract",
            "Implement core functionality with error handling",
            "Write tests and create documentation",
            "Prepare for integration with main system",
        ],
        context="Part of feature-integration-001 initiative",
        parent_task_id="feature-integration-001",
    )

# Aggregation point: wait for all children to complete
def wait_for_children_completion(parent_id, max_retries=10):
    """Poll until all children are done."""
    for attempt in range(max_retries):
        children = queue.query_tasks("done", parent_task_id=parent_id)
        expected_count = 3
        if len(children) == expected_count:
            return True
        print(f"Attempt {attempt+1}: {len(children)}/{expected_count} children done")
        import time
        time.sleep(5)
    return False

if wait_for_children_completion("feature-integration-001"):
    print("All features ready for integration")
    # Aggregate results
    done_children = queue.query_tasks("done", parent_task_id="feature-integration-001")
    print(f"Integrated results from {len(done_children)} features")
else:
    print("Not all features completed in time")
```

---

## Validation Before Creation

### Pre-validate DELEGATE Spec

```python
from skills.queue_management.scripts import QueueOperations

queue = QueueOperations(session_id="my-session")

# Prepare DELEGATE spec
delegate_spec = {
    "task_id": "invalid-task",
    "role": "Engineer",
    "scope": "Too short",  # ✗ < 15 words
    "plan": ["Single step"],  # ✗ < 2 steps
    "context": "Minimal context",  # ✗ < 20 words
}

# Validate before creating
valid, errors = queue.validate_delegate(delegate_spec)

if not valid:
    print("Validation errors:")
    for error in errors:
        print(f"  - {error}")
    # Fix errors
    delegate_spec = {
        "task_id": "valid-task-001",
        "role": "Engineer",
        "scope": "Implement new validation system with comprehensive error reporting and support for custom validators",
        "plan": [
            "Design validation framework architecture with plugin system",
            "Implement core validators and error handling logic",
            "Write integration tests covering all validator types",
        ],
        "context": "Current validation system lacks extensibility. See SPEC.md for requirements and design patterns to follow.",
    }
    
    # Validate again
    valid, errors = queue.validate_delegate(delegate_spec)
    if valid:
        result = queue.create_delegate(**delegate_spec)
        print(f"Created: {result['task_id']}")
```

---

## Rate Limiting

### Monitor and Handle Rate Limits

```python
from skills.queue_management.scripts import QueueOperations

queue = QueueOperations(session_id="my-session")

# Check rate limit before creating
allowed, status = queue.rate_limiter.check_limit("my-session")

print(f"Tasks this hour: {status['tasks_this_hour']}/{status['limit']}")
print(f"Remaining: {status['remaining']}")

if not allowed:
    print(f"⚠️ Rate limit reached! Reset at {status['reset_at']}")
    # Handle gracefully
    import time
    from datetime import datetime
    reset_time = datetime.fromisoformat(status['reset_at'])
    wait_seconds = (reset_time - datetime.utcnow()).total_seconds()
    if wait_seconds > 0:
        print(f"Waiting {wait_seconds:.0f} seconds...")
        time.sleep(wait_seconds)
else:
    # Safe to create
    result = queue.create_delegate(
        task_id="rate-test-001",
        role="Engineer",
        scope="Test rate limiting with multiple task creations in single session window",
        plan=[
            "Create tasks up to rate limit threshold",
            "Verify limit enforcement at boundary",
            "Test cleanup after hour window expires",
        ],
        context="Testing rate limiter functionality",
    )
```

---

## Parent Child Limit

### Handle Parent Child Limits

```python
from skills.queue_management.scripts import QueueOperations

queue = QueueOperations(session_id="my-session")

# Create parent
parent = queue.create_delegate(
    task_id="batch-processor-001",
    role="Senior Engineer",
    scope="Implement batch processing system with support for multiple parallel workers and error recovery",
    plan=[
        "Design batch task distribution architecture",
        "Create worker pool management system",
        "Implement error recovery and retry logic",
    ],
    context="Batch processor for distributed data processing",
)

# Create up to 10 children
for i in range(10):
    result = queue.create_delegate(
        task_id=f"batch-item-{i:03d}",
        role="Engineer",
        scope=f"Process batch item {i} with validation and error handling for data consistency",
        plan=[
            "Validate input data for item",
            "Process item according to batch rules",
            "Validate output and report completion status",
        ],
        context=f"Item {i} of batch processing job",
        parent_task_id="batch-processor-001",
    )

# Check status before creating 11th
allowed, status = queue.rate_limiter.check_limit(
    "my-session",
    parent_task_id="batch-processor-001"
)

if status["children_count"] >= status["children_limit"]:
    print(f"⚠️ Parent limit reached: {status['children_count']}/{status['children_limit']}")
    print("Cannot create more subtasks for this parent")
else:
    print(f"Safe to create: {status['children_remaining']} slots remaining")
```

---

## Cycle Detection

### Detect and Prevent Cycles

```python
from skills.queue_management.scripts import QueueOperations

queue = QueueOperations(session_id="my-session")

# Create task hierarchy
queue.create_delegate(
    task_id="task-a",
    role="Engineer",
    scope="Task A with comprehensive scope and detailed requirements for implementation",
    plan=[
        "Step A1 with detailed description",
        "Step A2 with implementation details",
    ],
    context="Task A context with relevant information",
)

queue.create_delegate(
    task_id="task-b",
    role="Engineer",
    scope="Task B with comprehensive scope and detailed requirements for implementation",
    plan=[
        "Step B1 with detailed description",
        "Step B2 with implementation details",
    ],
    context="Task B context with relevant information",
    parent_task_id="task-a",  # B is child of A
)

queue.create_delegate(
    task_id="task-c",
    role="Engineer",
    scope="Task C with comprehensive scope and detailed requirements for implementation",
    plan=[
        "Step C1 with detailed description",
        "Step C2 with implementation details",
    ],
    context="Task C context with relevant information",
    parent_task_id="task-b",  # C is child of B (A→B→C)
)

# Try to create task that would close the cycle: A→B→C→A
try:
    queue.create_delegate(
        task_id="task-a-2",
        role="Engineer",
        scope="Attempt cycle with comprehensive scope and detailed requirements description",
        plan=[
            "Step with description",
            "Another step",
        ],
        context="Context information",
        parent_task_id="task-c",  # Would create A→B→C→A (CYCLE!)
    )
except RuntimeError as e:
    print(f"✓ Cycle prevented: {e}")
```

---

## Query Patterns

### Common Query Patterns

```python
from skills.queue_management.scripts import QueueOperations

queue = QueueOperations(session_id="my-session")

# Get all tasks in specific state
all_processing = queue.query_tasks("processing")

# Get all subtasks of a parent
children = queue.query_tasks("incoming", parent_task_id="parent-001")

# Get all tasks assigned to role
engineers = queue.query_tasks("processing", role="Engineer")

# Complex query: senior engineers with done tasks
done_seniors = queue.query_tasks("done", role="Senior Engineer")

# Complex query: all children of parent who are senior engineers
senior_children = [
    t for t in queue.query_tasks("processing", parent_task_id="parent-001")
    if t["role"] == "Senior Engineer"
]

print(f"Total processing: {len(all_processing)}")
print(f"Subtasks of parent: {len(children)}")
print(f"Engineer assignments: {len(engineers)}")
print(f"Done (Senior): {len(done_seniors)}")
print(f"Senior children: {len(senior_children)}")
```

---

## Error Handling

### Robust Error Handling

```python
from skills.queue_management.scripts import QueueOperations

queue = QueueOperations(session_id="my-session")

# Error 1: Invalid validation
try:
    queue.create_delegate(
        task_id="bad-scope",
        role="Engineer",
        scope="Too short",  # < 15 words
        plan=["Single step"],  # < 2 steps
        context="Too short",  # < 20 words
    )
except ValueError as e:
    print(f"Validation error: {e}")

# Error 2: Duplicate task
try:
    queue.create_delegate(
        task_id="dup-task",
        role="Engineer",
        scope="First task with more than fifteen words for scope here",
        plan=[
            "Step one with words",
            "Step two",
        ],
        context="Context with words",
    )
    # Try again with same ID
    queue.create_delegate(
        task_id="dup-task",
        role="Engineer",
        scope="Second task with more than fifteen words for scope here",
        plan=[
            "Step one with words",
            "Step two",
        ],
        context="Context with words",
    )
except FileExistsError as e:
    print(f"Duplicate task error: {e}")

# Error 3: Invalid parent
try:
    queue.create_delegate(
        task_id="orphan-task",
        role="Engineer",
        scope="Child task with more than fifteen words for scope description",
        plan=[
            "Step one with words",
            "Step two",
        ],
        context="Context with words",
        parent_task_id="nonexistent-parent",
    )
except ValueError as e:
    print(f"Invalid parent error: {e}")

# Error 4: Cycle detected
try:
    queue.create_delegate(
        task_id="task-x",
        role="Engineer",
        scope="Task X with more than fifteen words for scope description",
        plan=[
            "Step one with words",
            "Step two",
        ],
        context="Context with words",
    )
    queue.create_delegate(
        task_id="task-y",
        role="Engineer",
        scope="Task Y with more than fifteen words for scope description",
        plan=[
            "Step one with words",
            "Step two",
        ],
        context="Context with words",
        parent_task_id="task-x",
    )
    # Try to create X with Y as parent (would be X→Y→X)
    queue.create_delegate(
        task_id="task-x-2",
        role="Engineer",
        scope="Cycle attempt with more than fifteen words for scope description",
        plan=[
            "Step one with words",
            "Step two",
        ],
        context="Context with words",
        parent_task_id="task-y",
    )
except RuntimeError as e:
    print(f"Cycle detection error: {e}")

# Error 5: Rate limit exceeded
try:
    for i in range(105):
        queue.create_delegate(
            task_id=f"rate-limit-{i:03d}",
            role="Engineer",
            scope="Rate limit test with more than fifteen words for scope here",
            plan=[
                "Step one with words",
                "Step two",
            ],
            context="Context with words",
        )
except RuntimeError as e:
    print(f"Rate limit error: {e}")
```

---

## Concurrent Operations

### Thread-Safe Concurrent Task Creation

```python
from skills.queue_management.scripts import QueueOperations
from threading import Thread
import queue as queue_module

# Use thread-safe queue for results
result_queue = queue_module.Queue()

def create_task(queue_ops, task_num):
    """Create a task in thread context."""
    try:
        result = queue_ops.create_delegate(
            task_id=f"concurrent-task-{task_num:03d}",
            role="Engineer",
            scope="Concurrent task with more than fifteen words for scope here",
            plan=[
                "Concurrent step one with words",
                "Concurrent step two",
            ],
            context="Concurrent context with words",
        )
        result_queue.put(("success", result))
    except Exception as e:
        result_queue.put(("error", str(e)))

# Create queue instance (thread-safe, uses file-based locking)
queue = QueueOperations(session_id="concurrent-session")

# Launch multiple threads
threads = []
for i in range(10):
    t = Thread(target=create_task, args=(queue, i))
    threads.append(t)
    t.start()

# Wait for completion
for t in threads:
    t.join()

# Collect results
successes = 0
errors = []
while not result_queue.empty():
    status, data = result_queue.get()
    if status == "success":
        successes += 1
    else:
        errors.append(data)

print(f"Created {successes} tasks")
if errors:
    print(f"Errors: {errors}")
```

---

## References

See also:
- **QUEUE-OPS-API.md** — Detailed API specification
- **SKILL.md** — Full skill documentation
- **tests/** — Test suite with examples
