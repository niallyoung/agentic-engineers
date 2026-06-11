"""
# OpenCode TaskRunner - Complete API Reference and Usage Guide

## Overview

The TaskRunner is a queue-based task execution engine providing complete lifecycle management for the OpenCode runner infrastructure. It implements atomic state transitions, error handling with exponential backoff retry logic, and dead-letter queue functionality.

### Key Features

- **Queue Polling**: Continuously monitors incoming queue and transitions tasks to processing state
- **Atomic State Transitions**: File-based locking ensures safe concurrent operations
- **Automatic Retry Logic**: Exponential backoff with configurable max retries (default: 3)
- **Dead-Letter Queue**: Permanently failed tasks moved to dead-letter for inspection
- **Result Retrieval**: Complete execution context and results preserved
- **CLI Tool**: Full command-line interface for task management

## Architecture

### Task States

The TaskRunner implements a state machine with the following states:

```
┌─────────┐
│ INCOMING│ (task submitted to queue)
└────┬────┘
     │ poll_queue()
     ↓
┌──────────────┐
│ PROCESSING   │ (task being executed)
└────┬────────┬┘
     │        │
   success    failure
     ↓        ↓
┌────────┐  ┌─────────┐
│  DONE  │  │ INCOMING│ (retry with backoff)
└────────┘  └─────────┘
                 ↓
            [after 3 retries]
                 ↓
            ┌──────────────┐
            │ DEAD-LETTER  │ (manual recovery required)
            └──────────────┘
```

### File Organization

Tasks are organized in state-specific directories:

```
~/.agentic-engineers/{harness}/{session-id}/queue/
├── incoming/          # Newly submitted tasks
├── processing/        # Tasks being executed
├── done/             # Successfully completed tasks
├── failed/           # Cancelled tasks
└── dead-letter/      # Permanently failed tasks (after max retries)
```

Each task is stored as a YAML file: `{TASK-ID}.yaml`

## TaskRunner Class

### Initialization

```python
from src.opencode.runner import TaskRunner
from pathlib import Path

# Explicit initialization
runner = TaskRunner(
    queue_root=Path.home() / ".agentic-engineers" / "queue",
    session_id="my-session",
    harness="opencode",
)

# Or use auto-detection from environment
runner = TaskRunner.from_session(
    session_id="auto-detect",  # Uses AGENTIC_SESSION_ID env var
    harness="auto-detect",     # Uses AGENTIC_HARNESS env var
)

# Initialize queue structure
runner.initialize()
```

### Task Submission

```python
# Submit a task
task_id = runner.submit_task({
    "role": "engineer",
    "description": "Fix bug in auth module",
    "files": ["src/auth.py"],
})

# Submit with explicit task ID
task_id = runner.submit_task(
    {"role": "engineer"},
    task_id="TASK-CUSTOM-001"
)
```

### Queue Polling

```python
# Poll for new tasks (typically in a loop)
polled_task_ids = runner.poll_queue(timeout_s=0.1)

# Process each task
for task_id in polled_task_ids:
    def handler(context):
        # Execute task logic
        return {"result": "success"}
    
    result = runner.execute_task(task_id, handler)
    print(f"Task {task_id}: {result.state}")
```

### Task Execution

```python
# Handler function receives TaskContext
def my_handler(context):
    print(f"Executing task: {context.task_id}")
    print(f"Metadata: {context.metadata}")
    
    # Perform work...
    return {"output": "result", "status": "ok"}

# Execute with error handling
result = runner.execute_task(task_id, my_handler)

# Check result
if result.success:
    print(f"Task completed in {result.execution_time_ms}ms")
else:
    print(f"Task failed: {result.error}")
    print(f"Retry count: {result.retry_count}")
```

### Result Retrieval

```python
# Get result for completed task
result = runner.get_result(task_id)

if result:
    print(f"State: {result.state}")
    print(f"Success: {result.success}")
    print(f"Output: {result.output}")
    print(f"Error: {result.error}")
    print(f"Retries: {result.retry_count}")
else:
    print("Task still processing")

# Get full task status
status = runner.get_task_status(task_id)
if status:
    print(f"State: {status['state']}")
    print(f"Created: {status['created_at']}")
    print(f"Error: {status['error_message']}")
```

### Task Management

```python
# List all tasks
all_tasks = runner.list_tasks()

# List tasks by state
incoming = runner.list_tasks(TaskState.INCOMING)
processing = runner.list_tasks(TaskState.PROCESSING)
done = runner.list_tasks(TaskState.DONE)

# Cancel a task
success = runner.cancel_task(task_id)

# Retry a failed/dead-letter task
success = runner.retry_task(task_id)
```

## CLI Usage

### Installation

```bash
python3 -m src.opencode.cli_runner init
```

### Commands

#### Initialize Queue Structure

```bash
# Initialize with auto-detected session/harness
opencode-runner init

# Specify session and harness
opencode-runner --session my-session --harness opencode init

# JSON output
opencode-runner --format json init
```

#### Submit a Task

```bash
# Basic task submission
opencode-runner run \
    --role engineer \
    --description "Fix critical bug"

# With metadata
opencode-runner run \
    --role engineer \
    --description "Fix critical bug" \
    --metadata '{"priority": "high", "files": ["src/auth.py"]}'

# JSON output
opencode-runner --format json run --role engineer --description "..."
```

#### Get Task Status

```bash
# Get status by task ID
opencode-runner status TASK-ABC123

# Positional argument
opencode-runner status TASK-ABC123

# JSON output
opencode-runner --format json status TASK-ABC123
```

#### List Tasks

```bash
# List all tasks
opencode-runner list

# Filter by state
opencode-runner list --state incoming
opencode-runner list --state processing
opencode-runner list --state done
opencode-runner list --state dead-letter

# JSON output
opencode-runner --format json list --state done
```

#### Cancel a Task

```bash
opencode-runner cancel TASK-ABC123

# Positional argument
opencode-runner cancel TASK-ABC123
```

#### Retry a Task

```bash
opencode-runner retry TASK-ABC123

# Retry a dead-letter task
opencode-runner retry TASK-DEADLETTER-001

# Positional argument
opencode-runner retry TASK-ABC123
```

## Error Handling and Retry Logic

### Automatic Retry

Tasks that fail are automatically retried with exponential backoff:

- **Attempt 1**: 1 second delay
- **Attempt 2**: 2 seconds delay
- **Attempt 3**: 4 seconds delay
- **After 3 failures**: Task moved to dead-letter queue

### Dead-Letter Queue

Tasks that exceed max retries are moved to the dead-letter queue:

```python
# Check dead-letter tasks
dead_letter_tasks = runner.list_tasks(TaskState.DEAD_LETTER)

for task_id in dead_letter_tasks:
    status = runner.get_task_status(task_id)
    print(f"{task_id}: {status['error_message']}")

# Manually retry a dead-letter task
if runner.retry_task(task_id):
    print(f"Retry initiated for {task_id}")
    runner.poll_queue()  # Pick up the task
```

### Error Types

#### Transient Errors

Tasks that fail due to transient errors (network, temporary resource exhaustion) will be automatically retried:

```python
def handler(context):
    try:
        result = call_external_service()
        return result
    except ConnectionError as e:
        # Will trigger automatic retry
        raise ValueError(f"Service unavailable: {e}")
```

#### Permanent Errors

After 3 retries, tasks are moved to dead-letter for manual inspection:

```python
# View dead-letter task
status = runner.get_task_status(task_id)
error_msg = status['error_message']

# Fix root cause and retry
if "config error" in error_msg:
    # Fix configuration
    runner.retry_task(task_id)
```

## Best Practices

### 1. Handler Functions

Keep handlers idempotent (safe to retry):

```python
def good_handler(context):
    # Safe - multiple executions produce same result
    result = compute_result(context.metadata)
    return result

def bad_handler(context):
    # NOT SAFE - creates duplicate entries on retry
    db.insert_record(context.metadata)
    return {"status": "ok"}
```

### 2. Error Messages

Provide clear, actionable error messages:

```python
def handler(context):
    try:
        validate_input(context.metadata)
    except ValueError as e:
        # Good: clear error message
        raise ValueError(f"Invalid config at {context.metadata}: {e}")
    
    # Process...
```

### 3. Context Usage

Always access task metadata through context:

```python
def handler(context):
    # Good
    role = context.metadata.get("role")
    description = context.metadata.get("description")
    
    # Process with context...
    return {"task_id": context.task_id, "result": ...}
```

### 4. Timeout Handling

For long-running tasks, implement timeout logic:

```python
import time

def handler(context):
    start = time.time()
    max_duration_s = 300  # 5 minutes
    
    while time.time() - start < max_duration_s:
        # Do work...
        pass
    
    if time.time() - start >= max_duration_s:
        raise TimeoutError("Task exceeded max duration")
```

## Integration Examples

### With Orchestrator

```python
from src.opencode.runner import TaskRunner

# In Orchestrator main loop
runner = TaskRunner.from_session()
runner.initialize()

while True:
    # Poll for new tasks
    task_ids = runner.poll_queue()
    
    for task_id in task_ids:
        def execute_task(context):
            # Route to appropriate agent
            agent = get_agent_for_role(context.metadata["role"])
            return agent.execute(context)
        
        result = runner.execute_task(task_id, execute_task)
        
        # Log result
        log_task_result(task_id, result)
    
    time.sleep(1)  # Polling interval
```

### Monitoring and Metrics

```python
from src.opencode.runner import TaskRunner, TaskState
from collections import defaultdict

runner = TaskRunner.from_session()

# Collect metrics
metrics = {
    "total_tasks": len(runner.list_tasks()),
    "tasks_by_state": {},
}

for state in TaskState:
    tasks = runner.list_tasks(state)
    metrics["tasks_by_state"][state.value] = len(tasks)

# Report metrics
print(f"Total tasks: {metrics['total_tasks']}")
for state, count in metrics["tasks_by_state"].items():
    print(f"  {state}: {count}")

# Check dead-letter queue
dead_letter = runner.list_tasks(TaskState.DEAD_LETTER)
if dead_letter:
    print(f"⚠️  Warning: {len(dead_letter)} tasks in dead-letter queue")
```

## Testing

### Unit Tests

Run the comprehensive test suite:

```bash
python3 -m pytest tests/opencode/test_runner.py -v

# With coverage
python3 -m coverage run --source=src/opencode -m pytest tests/opencode/test_runner.py
python3 -m coverage report
```

### Integration Tests

```python
import tempfile
from pathlib import Path
from src.opencode.runner import TaskRunner

def test_full_workflow():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create runner
        runner = TaskRunner(Path(tmpdir), "test", "test")
        runner.initialize()
        
        # Submit task
        task_id = runner.submit_task({"role": "engineer"})
        
        # Poll and execute
        runner.poll_queue()
        
        def handler(ctx):
            return {"status": "complete"}
        
        result = runner.execute_task(task_id, handler)
        assert result.success
```

## Troubleshooting

### Task Stuck in Processing

If a task remains in processing state:

```python
# Check task status
status = runner.get_task_status(task_id)
print(f"State: {status['state']}")
print(f"Updated: {status['updated_at']}")

# Cancel the task
runner.cancel_task(task_id)

# Or retry (moves back to incoming)
runner.retry_task(task_id)
```

### High Retry Count

If tasks are repeatedly failing:

```python
# Check failed/dead-letter tasks
dead_letter = runner.list_tasks(TaskState.DEAD_LETTER)

for task_id in dead_letter:
    status = runner.get_task_status(task_id)
    print(f"Error: {status['error_message']}")
    print(f"Retries: {status['retry_count']}")
```

### Queue Performance

Optimize queue polling:

```python
# Increase batch size by polling less frequently
import time

while True:
    polled = runner.poll_queue(timeout_s=0.5)  # 500ms timeout
    
    if polled:
        # Process all polled tasks in batch
        for task_id in polled:
            # Execute...
    
    time.sleep(5)  # 5 second poll interval
```

## API Reference

### TaskRunner Methods

- `initialize() -> dict` - Create queue directory structure
- `submit_task(task_data, task_id=None) -> str` - Submit new task
- `poll_queue(timeout_s=0.1) -> list[str]` - Poll incoming queue
- `execute_task(task_id, handler) -> TaskResult` - Execute task with handler
- `get_result(task_id) -> Optional[TaskResult]` - Retrieve completed task result
- `get_task_status(task_id) -> Optional[dict]` - Get full task status
- `list_tasks(state=None) -> list[str]` - List tasks by state
- `cancel_task(task_id) -> bool` - Cancel task
- `retry_task(task_id) -> bool` - Retry failed task

### TaskContext Attributes

- `task_id: str` - Unique task identifier
- `state: TaskState` - Current task state
- `created_at: datetime` - Task creation timestamp
- `updated_at: datetime` - Last update timestamp
- `retry_count: int` - Number of retry attempts
- `max_retries: int` - Maximum retry attempts
- `error_message: Optional[str]` - Error description if failed
- `result: Optional[dict]` - Task result if successful
- `metadata: dict` - Task metadata/configuration

### TaskResult Attributes

- `task_id: str` - Task ID
- `success: bool` - Execution success status
- `state: TaskState` - Final task state
- `output: Optional[Any]` - Task output
- `error: Optional[str]` - Error message if failed
- `retry_count: int` - Number of retries
- `execution_time_ms: float` - Execution duration in milliseconds
- `timestamp: datetime` - Result timestamp

## Performance Characteristics

- **Queue Polling**: O(n) where n = number of incoming tasks
- **Task Submission**: O(1) with atomic file write
- **State Transition**: O(1) with atomic file operations
- **Result Retrieval**: O(5) constant time (checks 5 state directories)
- **Task Listing**: O(n) where n = number of tasks

## Concurrency

TaskRunner is thread-safe:

```python
import threading

runner = TaskRunner.from_session()
runner.initialize()

def worker():
    while True:
        polled = runner.poll_queue()
        for task_id in polled:
            def handler(ctx):
                return {"worker": threading.current_thread().name}
            runner.execute_task(task_id, handler)

# Multiple workers
threads = [
    threading.Thread(target=worker, name=f"Worker-{i}")
    for i in range(4)
]

for t in threads:
    t.daemon = True
    t.start()

# Main thread monitors dead-letter queue
while True:
    dead_letter = runner.list_tasks(TaskState.DEAD_LETTER)
    if dead_letter:
        print(f"Dead-letter tasks: {len(dead_letter)}")
    time.sleep(10)
```

## License

OpenCode TaskRunner is part of the agentic-engineers framework.
"""
