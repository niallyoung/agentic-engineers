# Queue Polling Daemon — Phase 1

## Overview

The Queue Polling Daemon enables autonomous task routing in the agentic-engineers framework. It continuously polls the `artifacts/queue/incoming/` directory, routes tasks to appropriate agents, and tracks completion through `processing/` → `done/`.

## Architecture

```
artifacts/queue/{session-id}/
├── incoming/      ← New DELEGATE tasks land here
├── processing/    ← Tasks currently being executed
├── done/          ← Completed tasks (with HANDBACK metadata)
├── failed/        ← Tasks that exceeded retries or timed out
└── archive/       ← Corrupted or unprocessable tasks
```

### Core Components

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `AutomationController` | `src/orchestration/agents/automation.py` | Daemon loop, signal handling, metrics |
| `OrchestratorAgent` | `src/orchestration/agents/orchestrator.py` | Poll cycle, task routing, HANDBACK processing |
| `QueueManager` | `src/orchestration/agents/orchestrator.py` | Atomic queue state transitions |
| `ExtendedQueueManager` | `src/orchestration/queue_manager.py` | Adds `failed/` directory support |
| `TaskRouter` | `src/orchestration/agents/orchestrator.py` | Routes DELEGATEs to correct agent type |

### State Machine

```
incoming/ ──[move_task]──► processing/ ──[move_task]──► done/
    │                           │
    │                           └──[move_to_failed]──► failed/
    │                                                      │
    └◄──────────────[recover_failed_task]──────────────────┘
```

All transitions are **atomic** (write-then-rename pattern). No partial states.

## Running the Daemon

### Quick Start

```bash
# Run with default settings (daemon mode, 5s poll interval)
python -m src.orchestration.agents.automation

# Or via the orchestrator entry point
python -c "
from src.orchestration.agents.automation import AutomationController
ctrl = AutomationController()
result = ctrl.run()
print(result)
"
```

### Configuration Options

All options can be set via environment variables or constructor arguments:

| Option | Env Var | Default | Description |
|--------|---------|---------|-------------|
| `poll_interval` | `POLL_INTERVAL_SECONDS` | `5` | Seconds between polling cycles |
| `daemon_mode` | `AUTOMATION_DAEMON_MODE` | `true` | Run forever (true) or exit on idle (false) |
| `idle_timeout` | `AUTOMATION_IDLE_TIMEOUT` | `300` | Seconds of idle before exit (non-daemon mode) |
| `max_cycles` | `AUTOMATION_MAX_CYCLES` | `None` | Max cycles before exit (testing) |
| `log_level` | `LOG_LEVEL` | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `queue_dir` | `ORCHESTRATOR_QUEUE_DIR` | auto-detect | Override queue directory |
| `metrics_file` | `AUTOMATION_METRICS_FILE` | None | Path to write final metrics JSON |
| `dry_run` | `DRY_RUN_MODE` | `false` | No side effects (testing) |

### Example: Production Daemon

```bash
export POLL_INTERVAL_SECONDS=60
export AUTOMATION_DAEMON_MODE=true
export LOG_LEVEL=INFO
export AUTOMATION_METRICS_FILE=/var/log/orchestrator-metrics.json

python -m src.orchestration.agents.automation
```

### Example: Test Mode (5 cycles, then exit)

```bash
AUTOMATION_MAX_CYCLES=5 POLL_INTERVAL_SECONDS=1 python -c "
from src.orchestration.agents.automation import AutomationController
ctrl = AutomationController(max_cycles=5, poll_interval=1)
result = ctrl.run()
print(f'Processed {result[\"metrics\"][\"tasks_processed\"]} tasks')
"
```

## Signal Handling

| Signal | Behavior |
|--------|----------|
| `SIGTERM` | Graceful shutdown — finishes current cycle, then exits |
| `SIGINT` (Ctrl+C) | Clean shutdown — exits after current cycle |

```bash
# Graceful shutdown
kill -SIGTERM <pid>

# Immediate shutdown
kill -SIGINT <pid>
```

## Queue State Transitions

### Atomic Move Operations

All transitions use a **write-then-rename** pattern to ensure atomicity:

```python
from src.orchestration.agents.orchestrator import QueueManager

qm = QueueManager()

# incoming → processing
result = qm.move_task(
    task_id="2026-05-17-my-task",
    from_state="incoming",
    to_state="processing",
    metadata={"routing_info": {"role": "engineer"}}
)

# processing → done
result = qm.move_task(
    task_id="2026-05-17-my-task",
    from_state="processing",
    to_state="done",
    metadata=handback_dict
)
```

### Failed State (ExtendedQueueManager)

```python
from src.orchestration.queue_manager import ExtendedQueueManager

qm = ExtendedQueueManager()

# Move to failed (e.g., timeout)
result = qm.move_to_failed(
    task_id="2026-05-17-my-task",
    reason="agent timeout after 4h",
    from_state="processing"
)

# List failed tasks
failed = qm.list_failed_tasks()

# Recover for retry
result = qm.recover_failed_task("2026-05-17-my-task")
```

### Audit Trail

Every transition appends an entry to `_audit_trail` in the task YAML:

```yaml
_audit_trail:
  - timestamp: "2026-05-17T10:00:00"
    action: move_task
    from_state: incoming
    to_state: processing
    task_id: 2026-05-17-my-task
  - timestamp: "2026-05-17T10:05:00"
    action: move_task
    from_state: processing
    to_state: done
    task_id: 2026-05-17-my-task
```

## Task Routing

The `TaskRouter` maps DELEGATE fields to agent types:

| Condition | Agent |
|-----------|-------|
| `role: security_engineer` or `is_security_scoped: true` | SecurityEngineerAgent |
| `role: principal_engineer` or cross-service scope | PrincipalEngineerAgent |
| `complexity: high` + no plan | SeniorEngineerAgent |
| `role: lead_engineer` | LeadEngineerAgent |
| `role: quality_engineer` | QualityEngineerAgent |
| `role: model_engineer` | ModelEngineerAgent |
| Default (has plan, medium complexity) | EngineerAgent |

## HANDBACK Processing

After an agent completes, the HANDBACK is evaluated by quality score:

| Score | Action |
|-------|--------|
| ≥ 90 | PROCEED (merge) |
| 80–89 | PROCEED (minor notes) |
| 70–79 | MANUAL_REVIEW (Lead Engineer) |
| 60–69 | REWORK (retry, same agent, max 2 attempts) |
| < 60 | ESCALATE (Principal Engineer) |
| `status: failed` or `status: blocked` | ESCALATE (regardless of score) |

## Logging

The daemon emits structured log lines:

```
[2026-05-17 10:00:00] [AutomationController] [INFO] 🚀 AutomationController starting
[2026-05-17 10:00:00] [AutomationController] [INFO] Mode: daemon
[2026-05-17 10:00:00] [AutomationController] [INFO] Poll interval: 60s
[2026-05-17 10:01:00] [AutomationController] [INFO] [Cycle 1] Processed 2 tasks in 45.2s
[2026-05-17 11:00:00] [AutomationController] [INFO] Heartbeat: {"cycles_completed": 60, "tasks_processed": 12, ...}
```

Heartbeats are emitted every 60 seconds with cumulative metrics.

## Metrics

Final metrics are returned from `ctrl.run()` and optionally written to `AUTOMATION_METRICS_FILE`:

```json
{
  "status": "COMPLETE",
  "exit_reason": "sigterm",
  "metrics": {
    "start_time": "2026-05-17T10:00:00",
    "end_time": "2026-05-17T18:00:00",
    "total_duration_seconds": 28800,
    "cycles_completed": 480,
    "tasks_processed": 24,
    "tasks_success": 22,
    "tasks_escalated": 2,
    "tasks_failed": 0,
    "error_count": 0
  }
}
```

## Troubleshooting

### Tasks stuck in incoming/

1. Check that the daemon is running: `ps aux | grep automation`
2. Verify the queue directory: `ls artifacts/queue/*/incoming/`
3. Check logs for routing errors
4. Validate DELEGATE YAML: `python -c "import yaml; yaml.safe_load(open('path/to/task.yaml'))"`

### Tasks stuck in processing/

1. Check if the agent is still running (long-running tasks)
2. Look for HANDBACK files in `done/`
3. If timed out, use `ExtendedQueueManager.move_to_failed()` then `recover_failed_task()`

### Daemon exits immediately

1. Check `AUTOMATION_DAEMON_MODE=true` is set
2. Verify `AUTOMATION_MAX_CYCLES` is not set to a small value
3. Check `AUTOMATION_IDLE_TIMEOUT` if in non-daemon mode

### Session ID detection failures

The `QueueManager` partitions queues by session ID. If detection fails:

```bash
# Set explicitly
export COPILOT_SESSION_ID=my-session-id
# or
export CLAUDE_SESSION_ID=my-session-id
```

### Corrupted YAML in incoming/

Corrupted files are automatically moved to `archive/` with a timestamp prefix. Check `artifacts/queue/archive/` for debugging.

## Testing

```bash
# Run all queue polling daemon tests
python3 -m pytest tests/orchestration/test_queue_polling_daemon.py -v

# Run with coverage
python3 -m pytest tests/orchestration/test_queue_polling_daemon.py --cov=src.orchestration -v

# Run existing automation tests
python3 -m pytest tests/test_automation.py tests/test_automation_integration.py -v
```

## Backwards Compatibility

All existing APIs remain unchanged:

- `QueueManager.move_to_processing(filename)` — still works
- `QueueManager.move_to_done(filename, handback)` — still works  
- `QueueManager.list_incoming_tasks()` — still works
- `QueueManager.read_task(filename)` — still works
- `OrchestratorAgent.poll_and_process()` — still works
- `OrchestratorAgent.run_poll_cycle()` — still works

New additions are additive only:
- `ExtendedQueueManager` (new class, extends `QueueManager`)
- `src/orchestration/queue_manager.py` (new module, re-exports `QueueManager`)
