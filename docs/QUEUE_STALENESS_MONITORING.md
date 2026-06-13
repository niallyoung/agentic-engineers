# Queue Staleness Monitoring

## Overview

Timestamp tracking and staleness monitoring for queue tasks ensures that tasks don't silently disappear from the queue. The Orchestrator proactively detects and flags aged tasks with two levels of alerts:

- **ALERT** (5 minutes): Task has been pending longer than expected
- **ESCALATE** (10 minutes): Task requires manual intervention

## Architecture

### Components

1. **queue_staleness_monitoring.py** – Core staleness detection module
   - `record_task_timestamp()` – Records creation/state-change timestamps
   - `get_task_age_seconds()` – Calculates task age since creation
   - `detect_stale_tasks()` – Scans queue for stale tasks

2. **orchestrator_staleness_integration.py** – Integration points for OrchestratorSkill
   - `get_task_staleness_metadata()` – SLA configuration management
   - `update_staleness_check_timestamp()` – Update last check time
   - `_record_task_timestamp()` – Method stub for OrchestratorSkill
   - `monitor_staleness()` – Method stub for OrchestratorSkill

3. **queue_isolation.py** – Enhanced with staleness metadata
   - Creates `staleness.json` on queue initialization
   - Tracks `alert_threshold_sec` (5 min default)
   - Tracks `escalation_threshold_sec` (10 min default)

## Timestamp File Format

Each task maintains a `.timestamps.json` sidecar file in its queue state directory:

```
~/.agentic-engineers/{harness}/{session_id}/queue/{state}/{task_id}.timestamps.json
```

Example structure:

```json
{
  "created_at": "2026-06-13T15:30:45.123456+00:00",
  "last_updated": "2026-06-13T15:35:12.654321+00:00",
  "state_changes": [
    {
      "timestamp": "2026-06-13T15:30:45.123456+00:00",
      "action": "created",
      "state": "incoming"
    },
    {
      "timestamp": "2026-06-13T15:30:50.234567+00:00",
      "action": "claimed",
      "state": "processing"
    }
  ]
}
```

### Fields

- **created_at** (ISO 8601, immutable) – When task was first created
- **last_updated** (ISO 8601) – Last modification time
- **state_changes** (array) – History of {timestamp, action, state} transitions

## Usage

### Recording Task Timestamps

When a task is created or transitions states, record the timestamp:

```python
# In claim_task() method
self._record_task_timestamp(task_id, "processing", "claimed")

# When task completes
self._record_task_timestamp(task_id, "done", "completed")

# When task fails
self._record_task_timestamp(task_id, "failed", "failed")
```

### Monitoring Staleness

Call `monitor_staleness()` periodically (e.g., in poll_queue or separate monitoring loop):

```python
result = self.monitor_staleness()
print(f"Alerted: {result['alerted_count']}, Escalated: {result['escalated_count']}")

for task in result['stale_tasks']:
    print(f"{task['task_id']} ({task['state']}): {task['age_sec']:.0f}s / {task['alert_level']}")
```

### SLA Configuration

Staleness thresholds are stored in `staleness.json` (session-scoped):

```json
{
  "session_id": "abc-123-def-456",
  "queue_created_at": "2026-06-13T15:00:00+00:00",
  "alert_threshold_sec": 300,
  "escalation_threshold_sec": 600,
  "last_staleness_check": "2026-06-13T15:35:12+00:00"
}
```

To customize thresholds, edit `staleness.json` before starting the orchestrator:

```json
{
  "alert_threshold_sec": 600,      // Change alert to 10 minutes
  "escalation_threshold_sec": 1200 // Change escalation to 20 minutes
}
```

## Monitoring States

Staleness detection monitors these queue states:

| State | Monitored | Reason |
|-------|-----------|--------|
| `incoming/` | ✓ Yes | Tasks waiting to be claimed |
| `processing/` | ✓ Yes | Tasks actively being executed (should complete quickly) |
| `done/` | ✗ No | Already resolved, no action needed |
| `failed/` | ✗ No | Already resolved, no action needed |

## Alert Levels

### ALERT (5 minutes)

Task has exceeded the alert threshold (default 300 seconds):

```
STALE TASK ALERTED: task-001 in processing/ (age=320s, threshold=300s)
```

**Action**: Operator should investigate why the task is taking longer than expected.

### ESCALATE (10 minutes)

Task has exceeded the escalation threshold (default 600 seconds):

```
STALE TASK ESCALATED: task-001 in processing/ (age=610s, threshold=600s)
```

**Action**: Task should be escalated to manual review or marked for recovery.

## Observability

Staleness events are emitted as OpenTelemetry spans:

### Alert Span

```json
{
  "span_name": "orchestrator-staleness_alert",
  "span_id": "uuid",
  "trace_id": "session-id",
  "timestamp": "2026-06-13T15:35:12+00:00",
  "attributes": {
    "task_id": "task-001",
    "state": "processing",
    "age_sec": 320.0,
    "alert_level": "ALERT"
  }
}
```

### Escalation Span

```json
{
  "span_name": "orchestrator-staleness_escalation",
  "span_id": "uuid",
  "trace_id": "session-id",
  "timestamp": "2026-06-13T15:35:12+00:00",
  "attributes": {
    "task_id": "task-001",
    "state": "processing",
    "age_sec": 610.0,
    "alert_level": "ESCALATE"
  }
}
```

## Integration with OrchestratorSkill

To integrate staleness monitoring into the OrchestratorSkill:

1. **Add timestamp recording to claim_task()**:
   ```python
   self._record_task_timestamp(task_id, "processing", "claimed")
   ```

2. **Add staleness monitoring to poll_queue()** or main loop:
   ```python
   staleness_result = self.monitor_staleness()
   ```

3. **Implement recovery** based on escalations:
   ```python
   if staleness_result["escalated_count"] > 0:
       # Move to retry-pending or escalate to lead-engineer
   ```

## Testing

Comprehensive test suite: `src/skills/orchestrator/tests/test_queue_staleness.py`

### 16 Test Cases

1. **Timestamp Recording** (5 tests)
   - File creation
   - Field validation (created_at, last_updated)
   - State change tracking
   - Immutability of created_at

2. **Age Calculation** (3 tests)
   - Type validation
   - Edge cases (missing files)
   - Time progression

3. **Alert Thresholds** (2 tests)
   - Alert threshold detection (5 min)
   - Escalation threshold detection (10 min)

4. **Multi-State Monitoring** (2 tests)
   - Monitor multiple states simultaneously
   - Ignore done/failed states

5. **Edge Cases** (4 tests)
   - Missing timestamps files
   - Malformed JSON
   - Empty queue
   - Custom thresholds

### Running Tests

```bash
python3 -m pytest src/skills/orchestrator/tests/test_queue_staleness.py -v
```

All 16 tests pass (100% coverage of staleness monitoring logic).

## Design Decisions

### Timestamp Sidecars

Timestamps are stored in separate `.timestamps.json` files (not in the YAML or metadata files) to:
- Isolate timestamp concerns from task metadata
- Enable independent timestamp auditing
- Support future archival/retention policies
- Minimize reads/writes to main task files

### Immutable created_at

The `created_at` timestamp is immutable to provide an audit trail of when a task was originally enqueued, even if it's retried or moved between states.

### Configurable Thresholds

SLA thresholds are session-scoped and configurable (stored in `staleness.json`) to allow:
- Different SLAs for different environments (dev, staging, prod)
- Runtime adjustment without code changes
- Per-session customization (e.g., longer timeouts for large batches)

### Monitored States Only

We only monitor `incoming/` and `processing/` because:
- `done/` tasks are complete (no staleness concern)
- `failed/` tasks are already handled (no staleness concern)
- Monitoring all states would emit false positives

## Future Enhancements

1. **Dynamic Threshold Scaling** – Adjust SLA based on queue depth
2. **Task-Specific SLAs** – Different timeouts for different task types
3. **Auto-Recovery** – Automatically retry escalated tasks
4. **Metrics Dashboard** – Time-series visualization of staleness events
5. **Integration with Alerting** – Send alerts to Slack/PagerDuty

## See Also

- `/docs/QUEUE-PROTOCOL.md` – Queue state machine and transitions
- `src/skills/orchestrator/scripts/orchestrator_skill.py` – Main orchestrator
- `src/skills/_meta/queue-isolation/scripts/queue_isolation.py` – Queue path isolation
