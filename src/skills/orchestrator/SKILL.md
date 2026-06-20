---
name: orchestrator
description: "In-harness queue orchestration system that implements the DELEGATE/HANDBACK protocol lifecycle. Manages queue state machine (7 states: incoming, claimed, processing, done, failed, crashed, retry-pending), polls queue for new tasks, spawns sub-agents via Agent tool, correlates HANDBACK results, recovers from crashes, invokes quality gates, and detects idle conditions. Core system that makes DELEGATE/HANDBACK actually work."
license: Proprietary
compatibility: agentic-engineers framework v5.10+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: orchestration
  role: orchestrator
  model: claude-haiku-4.5
  effort: high
  thinking: false
---

# orchestrator

## Overview

The Orchestrator skill is the **in-harness queue management system** that coordinates all DELEGATE/HANDBACK protocol flow. It aims to:

1. **Queue polling** — continuously monitor `incoming/` for new DELEGATE blocks
2. **Task claiming** — atomically move tasks from `incoming/` → `processing/` with timestamps
3. **Sub-agent spawning** — invoke the Agent tool with full DELEGATE context
4. **HANDBACK correlation** — parse HANDBACK text, extract task_id, apply routing decisions
5. **Crash recovery** — detect orphaned tasks in `processing/` by claimed_at timeout
6. **Quality gating** — invoke quality-engineer validation before marking done
7. **Idle detection** — implement 3-minute sleep, 3-cycle threshold, deep sleep
8. **State transitions** — 7-state queue machine with atomic file moves

## Architecture

### Queue State Machine (7 States)

```
incoming/       → new DELEGATEs waiting for pickup
  ↓
claimed/        → task claimed by orchestrator (timestamp: claimed_at)
  ↓
processing/     → sub-agent is executing the task
  ├─→ done/     (success)
  ├─→ failed/   (error)
  └─→ crashed/  (orphaned / timeout after 600s)
  
retry-pending/  → task queued for retry (after crash recovery)
```

### Queue Path Structure

All paths are per-session, per-harness (via queue-isolation):

```
~/.agentic-engineers/artifacts/{session_id}/{harness}/queue/
  incoming/        – new DELEGATE files
  processing/      – tasks being executed (with claimed_at)
  done/            – completed tasks (with HANDBACK files)
  failed/          – failed tasks (with error context)
```

### Queue File Naming

```
DELEGATE:   {task_id}.yaml
HANDBACK:   {task_id}-HANDBACK-{role}.yaml
Metadata:   {task_id}.meta.json (claimed_at, retry_count, last_error)
```

## Core Methods

### `poll_queue()`

**Purpose:** Main polling loop — read incoming/, validate, claim, spawn.

**Behavior:**
1. Read all `.yaml` files from `incoming/`
2. Validate each DELEGATE format (handoff_type, task_id, scope, plan, success_criteria, agent)
3. For each valid DELEGATE:
   - Call `claim_task(task_id)` → atomic move to `processing/`
   - Call `spawn_sub_agent(delegate_dict)` → invoke Agent tool
   - Call `handle_handback(task_id, handback_text)` → wait for HANDBACK, route result
4. Continue until `incoming/` is empty
5. Increment `clean_poll_count`
6. If `clean_poll_count >= 3` → call `run_idle_loop()`

**Returns:** `(processed_count: int, failed_count: int)`

---

### `claim_task(task_id: str) -> dict`

**Purpose:** Atomically move task from incoming/ → processing/ with claimed_at timestamp.

**Behavior:**
1. Read `incoming/{task_id}.yaml` (DELEGATE)
2. Create `processing/{task_id}.meta.json` with:
   ```json
   {
     "task_id": "...",
     "claimed_at": "ISO8601 timestamp",
     "retry_count": 0,
     "last_error": null
   }
   ```
3. Move `incoming/{task_id}.yaml` → `processing/{task_id}.yaml`
4. Return the parsed DELEGATE dict

**Exceptions:** `FileNotFoundError` if task doesn't exist, `IOError` on move failure.

---

### `spawn_sub_agent(delegate: dict) -> str`

**Purpose:** Invoke Agent tool with full DELEGATE context.

**Behavior:**
1. Serialize DELEGATE as YAML
2. Call Agent tool with:
   - Role: `delegate['agent']`
   - Model: from routing table (engineer→haiku, senior-engineer→sonnet, etc.)
   - Input: Full DELEGATE YAML as context
3. Wait for subprocess to complete (via AgentInvoker timeout)
4. Capture stdout/stderr
5. Return combined output (contains HANDBACK YAML block)

**Returns:** `output_text: str` (may contain HANDBACK block or error message)

---

### `handle_handback(task_id: str, handback_text: str) -> dict`

**Purpose:** Parse HANDBACK from Agent output, apply routing, invoke QE gate, transition state.

**Behavior:**
1. Parse HANDBACK YAML block from `handback_text`
   - Extract task_id, status, output, metrics, confidence
2. Validate HANDBACK schema (required fields)
3. Move file from `processing/{task_id}.yaml` → temp location
4. Apply routing decision:
   - If `status == 'success'` → invoke `invoke_qe_gate(task_id, handback)`
   - If `status == 'failure'` → move to `failed/{task_id}-HANDBACK.yaml`
   - If `status == 'escalate'` → escalation chaining (C2c): synthesize a follow-on
     `{task_id}-escalated-to-{role}` DELEGATE into `incoming/` for the escalation
     target (`output.escalate_to`, default `lead-engineer`) and archive the original
     task to `done/` with escalation audit metadata. There is no `escalation/` state
     directory in the queue protocol.
5. Write `done/{task_id}-HANDBACK.yaml` (or `failed/`)
6. Increment metrics (tokens, cost, duration)
7. Return parsed HANDBACK dict

**Exceptions:** `ValueError` if HANDBACK is malformed.

---

### `recover_crashed_tasks()`

**Purpose:** Scan processing/ for orphaned tasks (claimed_at + 600s deadline).

**Behavior:**
1. List all `.meta.json` files in `processing/`
2. For each file:
   - Parse `claimed_at` timestamp
   - If `now - claimed_at > 600s` (10 minutes):
     - Increment `retry_count`
     - If `retry_count >= 3` → move to `failed/`
     - Else → move to `retry-pending/`, reschedule
3. Write recovery log with timestamps and retry decisions

**Returns:** `(recovered_count: int, failed_count: int)`

---

### `wake_timer() -> Dict[str, Any]`

**Purpose:** Wake-timer mechanism to detect and recover stalled tasks (no heartbeat for N seconds).

**Behavior:**
1. Detect tasks in processing/ without recent heartbeat (> heartbeat_interval seconds)
2. For each stalled task:
   - Increment retry_count
   - If retry_count >= retry_max_attempts → escalate to manual review
   - Else → move to retry-pending/ with exponential backoff
3. Log detection and recovery metrics
4. Capture span for observability

**Thresholds (from SPEC queue SLA design):**
- **Heartbeat interval:** config.heartbeat_interval (default 30 seconds, configurable)
- **Stale (WARN):** config.stale_threshold_sec (300 seconds since last_heartbeat)
- **Crash (ESCALATE):** config.crash_threshold_sec (600 seconds since claimed_at, LOCKED)

**Returns:**
```python
{
    'stalled_detected': int,    # Number of stalled tasks found
    'recovered': int,           # Tasks moved to retry-pending
    'escalated': int,           # Tasks escalated to manual review
    'wake_reason': str          # 'heartbeat_timeout' or 'no_stalled_tasks'
}
```

---

### `run_idle_loop() -> Dict[str, Any]`

**Purpose:** Implement intelligent idle detection with 3-minute polling sleep and deep sleep after 3 consecutive clean polls.

**Behavior:**
1. **Normal polling (clean_poll_count < 3):**
   - Sleep for `POLL_INTERVAL_SEC` (180 seconds / 3 minutes)
   - Return: `{'work_processed': 0, 'idle_entered': False, 'wake_reason': 'normal'}`

2. **Idle detected (clean_poll_count >= 3):**
   - Log "Queue idle ({IDLE_THRESHOLD_POLLS} clean polls), entering deep sleep"
   - Call `_deep_sleep()` to block until woken
   - Reset `clean_poll_count = 0`
   - Return: `{'work_processed': 0, 'idle_entered': True, 'wake_reason': <wake_type>}`

**Returns:**
```python
{
    'work_processed': int,    # 0 in idle loop (for future extension)
    'idle_entered': bool,     # True if deep sleep was triggered
    'wake_reason': str        # 'normal' | 'timeout' | 'file_event' | 'signal'
}
```

**Wake Reasons:**
- `'normal'` — completed POLL_INTERVAL_SEC sleep (normal polling cycle)
- `'timeout'` — deep sleep duration (DEEP_SLEEP_SEC) completed without event
- `'file_event'` — new file detected in `incoming/` directory (wakes early)
- `'signal'` — received SIGUSR1 signal (external wake)

---

### `_deep_sleep() -> str`

**Purpose:** Enter deep sleep and block until woken by file system event or signal.

**Behavior:**
1. Setup SIGUSR1 signal handler
2. Attempt to use inotify (Linux) to watch `incoming/` for new files
   - If available: wait for file creation event with timeout
   - If not available: fall back to `_deep_sleep_polling()`
3. On wake: return wake_reason and restore signal handler

**Returns:** `'file_event' | 'signal' | 'timeout'`

---

### `_deep_sleep_polling() -> str`

**Purpose:** Fallback deep sleep implementation using polling and signal handling.

**Behavior:**
1. Get initial file count in `incoming/`
2. Setup SIGUSR1 signal handler
3. Loop with ~10-second poll interval:
   - Check if new files have appeared in `incoming/`
   - If found: return `'file_event'`
   - If SIGUSR1 received: return `'signal'`
   - If DEEP_SLEEP_SEC timeout reached: return `'timeout'`
4. Restore signal handler

**Returns:** `'file_event' | 'signal' | 'timeout'`

---

### `invoke_qe_gate(task_id: str, handback: dict) -> bool`

**Purpose:** Invoke Quality Engineer validation before marking done.

**Behavior:**
1. Create QE DELEGATE:
   ```yaml
   handoff_type: DELEGATE
   agent: quality-engineer
   task_id: {task_id}-qe-gate
   scope: "Validate {original_task_id} HANDBACK against success criteria"
   context:
     - original_task_id: {task_id}
     - handback: {serialized HANDBACK}
     - success_criteria: from original DELEGATE
   ```
2. Spawn quality-engineer via Agent tool
3. Wait for QE HANDBACK with approval/rejection
4. If approved → return True (proceed to done/)
5. If rejected → return False (move to failed/)

---

### `capture_span(method_name: str, **attrs) -> None`

**Purpose:** Write OpenTelemetry SPAN file for observability.

**Behavior:**
1. Create SPAN dict:
   ```json
   {
     "span_name": "orchestrator-{method_name}",
     "span_id": "{uuid}",
     "trace_id": "{session_id}",
     "start_time": "ISO8601",
     "end_time": "ISO8601",
     "duration_ms": int,
     "attributes": {
       ...attrs
     }
   }
   ```
2. Write to `{queue_root}/spans/{task_id}-{method}.span.json`
3. Log span in metrics registry

---

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `poll_interval_fast` | int | 30 | Polling interval when tasks are processing (seconds) |
| `poll_interval_idle` | int | 180 | Polling interval when queue is idle (seconds) |
| `heartbeat_interval` | int | 30 | Expected interval between heartbeats (seconds, configurable) |
| `heartbeat_timeout_sec` | int | 120 | Max time without task update before stalled (seconds) |
| `task_deadline_sec` | int | 600 | Max claimed time before crash recovery (seconds) |
| `stale_threshold_sec` | int | 300 | Threshold for WARN status (seconds since last_heartbeat) |
| `crash_threshold_sec` | int | 600 | Threshold for ESCALATE (seconds since claimed_at, LOCKED) |
| `idle_threshold_polls` | int | 3 | Clean polls before deep sleep |
| `idle_sleep_sec` | int | 600 | Deep sleep duration (seconds) |
| `retry_max_attempts` | int | 3 | Max retries for crashed/stalled tasks |
| `retry_backoff_multiplier` | float | 1.5 | Exponential backoff multiplier for retries |

## Dependencies

- **queue-management** — for all YAML queue writes (via QueueOperations)
- **queue-isolation** — for session/harness scoped queue paths
- **orchestrator.py** — routing table (agent→model mapping)
- **Agent tool** — sub-agent invocation
- **quality-engineer** — QE gating

## Integration Points

1. **Orchestrator.py routing** — import ENGINEER_CONFIG, SENIOR_ENGINEER_CONFIG, etc.
2. **QueueOperations.enqueue()** / **move_task()** — never write queue files directly
3. **Agent tool invocation** — pass full DELEGATE YAML, capture HANDBACK
4. **Model Engineer feedback** — cost/token metrics from HANDBACK
5. **Escalation chain** — when status='escalate', create escalation DELEGATE

## Examples

### Minimal Orchestrator Usage with Idle Loop

```python
from src.skills.orchestrator import OrchestratorSkill

skill = OrchestratorSkill()

# Continuous polling with idle detection
while True:
    processed, failed = skill.poll_queue()
    
    # run_idle_loop() handles both normal and deep sleep automatically
    result = skill.run_idle_loop()
    
    # Check wake reason (useful for logging/monitoring)
    if result['idle_entered']:
        print(f"Woken from deep sleep: {result['wake_reason']}")
```

### Orchestrator Agent Loop Pattern

```python
# This is how the Orchestrator agent calls run_idle_loop in a loop
skill = OrchestratorSkill(session_id="my-session", harness="claude")

for cycle in range(100):  # ~5 hours of polling
    # Poll once
    processed, failed = skill.poll_queue()
    
    # Handle idle with automatic deep sleep after 3 clean polls
    result = skill.run_idle_loop()
    
    # Log for observability
    logger.info(
        f"Poll cycle {cycle}: "
        f"processed={processed}, failed={failed}, "
        f"idle_entered={result['idle_entered']}, "
        f"wake_reason={result['wake_reason']}"
    )
```

### With Crash Recovery

```python
skill = OrchestratorSkill()

# On startup: recover any orphaned tasks
recovered, newly_failed = skill.recover_crashed_tasks()
print(f"Recovered {recovered} tasks, failed {newly_failed}")

# Then run normal polling with idle loop
while True:
    processed, failed = skill.poll_queue()
    result = skill.run_idle_loop()
```

### Manual Deep Sleep with Signal Handling

```python
import signal
import os

skill = OrchestratorSkill()
skill.clean_poll_count = 3  # Trigger deep sleep

# Send SIGUSR1 from another process to wake immediately
# os.kill(os.getpid(), signal.SIGUSR1)

result = skill.run_idle_loop()
print(f"Wake reason: {result['wake_reason']}")  # 'signal' or 'timeout'
```

## Testing

Unit tests cover:
- State machine transitions (incoming → claimed → processing → done)
- HANDBACK parsing and routing
- Crash recovery and timeout detection
- Idle detection and sleep threshold
- Atomic moves and metadata writes
- Quality gate invocation
- Escalation chain delegation

Run tests:
```bash
pytest src/skills/orchestrator/tests/
```

## Observability

All operations write OpenTelemetry SPAN files to the queue's `spans/` directory for:
- Latency measurement
- Error tracking
- Cost aggregation
- Task dependency visualization

## Self-Improvement

We aim for **orchestrator** to feel like a knowledgeable colleague rather than a rulebook. If any section felt prescriptive rather than guiding, a `tone_note` in your feedback helps us improve it.

This skill participates in the framework's continuous improvement cycle
(see [`skill-improvement-feedback`](../skill-improvement-feedback/SKILL.md)).

When you use **orchestrator** during a task, include a `skill_feedback` entry
in your HANDBACK to help improve it over time:

```yaml
skill_feedback:
  - skill_name: orchestrator
    effectiveness_score: 0.85        # required: 0.0–1.0
    clarity_score: 0.90              # optional
    coverage_gaps:
      - "Specific scenario the skill did not address"
    improvement_suggestions:
      - "Concrete change that would have helped"
    usage_context: "One sentence on how you used this skill"
```

Positive feedback is as valuable as critical feedback. Three or more
feedback items for this skill automatically trigger an improvement task.
