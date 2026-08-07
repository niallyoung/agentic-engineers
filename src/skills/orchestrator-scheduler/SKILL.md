---
name: orchestrator-scheduler
description: "Harness-native queue polling scheduler. Invokes Orchestrator skill on a recurring schedule to process queued DELEGATEs. Uses environment variables (read live) to detect session ID and harness. Implements queue polling as a SKILL—no external daemons, cron jobs, or background processes needed. Can be re-awakened via skill invocation."
license: Proprietary
compatibility: agentic-engineers framework v5.10+. Requires Python 3.11+
metadata:
  author: agentic-engineers
  version: "1.0.0"
  category: orchestration
  role: orchestrator
  model: claude-haiku-4.5
  effort: low
  thinking: false
  dependencies:
    - orchestrator
---

# orchestrator-scheduler

**Purpose:** Enable automatic DELEGATE pickup and processing without external daemons or cron jobs. Orchestrator polling is implemented entirely as a SKILL that can be re-invoked on-demand or scheduled via harness integration.

**Status:** ✅ Implemented

---

## Overview

The `orchestrator-scheduler` SKILL provides:

1. **Environment-driven session detection** — reads `CLAUDE_SESSION_ID`, `COPILOT_SESSION_ID`, `AGENTIC_SESSION_ID` at invocation time (not startup)
2. **Queue polling** — invokes `OrchestratorSkill.poll_queue()` to process all available DELEGATEs
3. **Harness support** — auto-detects harness from environment (claude, copilot, gpt, etc.)
4. **On-demand invocation** — can be called via `/orchestrator-scheduler` at any time
5. **Re-awakening** — if processing stalls, can be invoked again to resume

---

## Usage

### Interactive Invocation

```bash
# Manually trigger queue polling
/orchestrator-scheduler
```

### Single-Cycle Invocation (--poll-once)

For harness idle-loop integration (Phase G), use `--poll-once`. It processes
all DELEGATEs in `queue/incoming/` exactly once, holds a file-based queue lock
during the cycle, enforces a soft timeout (default 30s), and prints a single
JSON line to stdout for the harness to consume.

```bash
# Single polling cycle, JSON result on stdout
orchestrator-scheduler --poll-once

# Override the per-cycle soft timeout (seconds)
orchestrator-scheduler --poll-once --timeout 30

# Override session ID (testing / automation; bypasses env detection)
orchestrator-scheduler --poll-once --session-id my-test-session
```

**Exit codes:** `0` if no errors recorded, `1` if the `errors` array is non-empty.

#### JSON Return Format

```json
{
  "processed": 3,
  "failed": 0,
  "duration_ms": 2400,
  "queue_empty": false,
  "session_id": "abc-def-ghi",
  "harness": "claude",
  "lock_skipped": false,
  "errors": []
}
```

| Field | Meaning |
|-------|---------|
| `processed` | DELEGATEs processed to a terminal state this cycle |
| `failed` | DELEGATEs/operations that errored this cycle |
| `duration_ms` | Wall-clock duration of the poll cycle |
| `queue_empty` | True if `incoming/` is empty after the cycle |
| `session_id` / `harness` | Resolved session + harness for this poll |
| `lock_skipped` | True if the cycle was skipped because another harness held the lock |
| `errors` | List of `{stage, message}` — `stage` is one of `init`, `lock`, `scan`, `timeout`, `process`, `fatal` |

#### CLI Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--poll-once` | off | Single cycle with lock + soft timeout; emits JSON |
| `--session-id ID` | env-detected | Explicit session override (testing/automation) |
| `--timeout N` | 30 | Soft per-cycle timeout in seconds (poll-once only) |
| `--retry N` | 1 | Retry attempts for legacy `run()` (ignored with `--poll-once`) |
| `--verbose` | off | Debug logging |

### Programmatic Usage

```python
from src.skills.orchestrator_scheduler.scripts.orchestrator_scheduler import OrchestratorScheduler

scheduler = OrchestratorScheduler()
processed, failed = scheduler.run()
print(f"Processed: {processed} | Failed: {failed}")
```

### In HANDBACK (with skill_feedback)

```yaml
skill_feedback:
  - skill_name: orchestrator-scheduler
    effectiveness_score: 0.95
    usage_context: "Scheduler invoked to process 3 pending DELEGATEs"
```

---

## Architecture

### Session & Harness Detection (Runtime)

The scheduler reads environment variables **at invocation time** to ensure it uses the current session:

| Priority | Env Variable | Fallback |
|----------|---|---|
| 1 | `CLAUDE_SESSION_ID` | (required for claude harness) |
| 2 | `OPENCODE_SESSION_ID` | (required for opencode harness) |
| 3 | `COPILOT_SESSION_ID` | (required for copilot harness) |
| 4 | `AGENTIC_SESSION_ID` | (generic session override) |
| 5 | `CLAUDE_CODE_SESSION_ID` | (local CLI) |
| — | `AGENTIC_HARNESS` | `claude` (default) |

A `--session-id` CLI flag overrides all of the above for testing/automation.

**Key:** Session ID is read fresh each invocation—no caching, no startup assumptions.

### Queue Polling Loop

```python
def run(self):
    """
    Poll queue and process DELEGATEs.
    
    1. Detect session ID from environment (runtime)
    2. Initialize OrchestratorSkill with detected session
    3. Call poll_queue() to process incoming DELEGATEs
    4. Return (processed_count, failed_count)
    """
```

### File-Based Queue Locking (Multi-Harness Coordination)

`--poll-once` serializes polling across harnesses that share a session queue
using an atomic lock file:

- **Path:** `~/.agentic-engineers/{harness}/{session}/queue/.lock`
- **Atomic acquire:** `os.open(..., O_CREAT | O_EXCL | O_WRONLY)` — fails if held
- **Contents:** PID, ISO-8601 timestamp, harness name (for debugging races)
- **Contention:** if held by another live harness, the cycle is skipped
  (`lock_skipped: true`, `processed: 0`) — not treated as an error
- **Stale cleanup:** a lock whose mtime is older than 300s is presumed orphaned
  by a crashed harness; it is removed and reacquired
- **Release:** always released in a `finally` block, even on processing errors
- **Logging:** every acquire/release/stale-cleanup is logged at INFO for race debugging

### Exponential Backoff (Phase G-2)

Between idle polls, the harness uses an adaptive **exponential backoff** so an
empty queue does not cause busy-polling. The continuous engine lives in
`src/harnesses/shared/backoff_poller.py` (`BackoffPoller`); the scheduler's
`--poll-once` is the unit of work it repeats.

**When the harness detects an empty queue, the sleep duration increases:**

```
5s → 30s → 180s → 600s   (capped at 600s / 10 minutes)
```

Each consecutive *empty* poll advances one rung up the ladder. The backoff
**resets to 5s** on the next DELEGATE detection or whenever processing occurs —
i.e. whenever a poll processes ≥ 1 DELEGATE, **or** the file-watch on
`queue/incoming/` detects a newly-arrived DELEGATE during a sleep.

**Example:**

```
Empty queue → backs off 5s → 30s → 180s → 600s (deep idle)
  → DELEGATE arrives → file-watch wakes the harness → processes immediately
  → backoff reset to 5s (active state)
```

This keeps idle sessions cheap (a ~10-minute deep-sleep cadence) while still
reacting to new work within a single watch slice (default 0.5s). Backoff
overhead is < 2ms per cycle. The ladder is configurable via the harness
`idle_loop.backoff_intervals` settings block (see
[harness-queue-polling guide](../../../docs/guides/harness-queue-polling.md)).

### Integration Points

**Harness Idle-Loop (Phase G):** When idle, a harness invokes
`orchestrator-scheduler --poll-once` and reads the JSON result. The bounded
timeout guarantees the harness is not blocked indefinitely.

**Claude Code Idle-Loop (Phase G-1):** The Claude Code harness is wired via:

- **Config:** `dist/claude/settings.json` → `idle_loop` section:

  ```json
  "idle_loop": {
    "enabled": true,
    "interval_seconds": 180,
    "action": "invoke_skill",
    "skill": "orchestrator-scheduler",
    "args": ["--poll-once"]
  }
  ```

- **Module:** `src/harnesses/claude_code/idle_loop.py` (`ClaudeIdleLoop`).
  Detects idle (user idle ≥ `interval_seconds`, no task in progress, message
  queue empty), then invokes `orchestrator-scheduler --poll-once` as a bounded
  subprocess (default 35s hard cap), parses the JSON result, and logs:
  - `Claude idle for Ns, polling queue`
  - `Queued N DELEGATEs, duration Xs`
  - `Queue poll error: ...` (timeouts/errors are non-fatal — the harness continues)

  The harness drives it by calling `on_user_activity()`,
  `set_task_in_progress(...)`, and `check_idle(message_queue_empty=...)` on its
  event-loop tick.

**Claude Code Profile:** Can be set to invoke scheduler on a timer:

```yaml
# ~/.claude/orchestrator-scheduler.yaml (future)
schedule:
  interval: 30  # seconds
  mode: "manual-invoke"  # requires /orchestrator-scheduler call
```

**Harness Integration:** Renderer should include wrapper scripts:

```bash
# dist/claude/orchestrator-scheduler command
claude-orchestrator-scheduler --poll
```

---

## Design Decisions

✅ **No external daemons** — scheduler runs as a SKILL, invoked by harness  
✅ **No cron jobs** — polling triggered explicitly or via harness timers  
✅ **Runtime session detection** — reads env vars fresh each invocation  
✅ **Environment-driven** — respects `CLAUDE_SESSION_ID`, `AGENTIC_HARNESS`  
✅ **Simple & testable** — pure Python, no subprocess management  

---

## Failure Modes & Recovery

| Scenario | Behavior | Recovery |
|---|---|---|
| DELEGATEs in incoming/ | Picks up, processes, moves to done/ | Automatic |
| Failed DELEGATE | Moves to failed/, logs error | Re-invoke after fixing root cause |
| Network/timeout | Logs and continues | Retry via manual `/orchestrator-scheduler` |
| Session ID missing | Raises error with suggestion | Set a session env var or pass `--session-id` |
| Lock held by another harness | Cycle skipped (`lock_skipped: true`) | Automatic — retried next idle cycle |
| Stale lock (age > 300s) | Cleaned up, lock reacquired | Automatic |
| Lock acquire OS error | Retries 3× with exponential backoff, then fails gracefully | Automatic |
| Cycle exceeds timeout | Records `timeout` error; remaining items deferred | Automatic next cycle |

---

## Testing

```bash
# Run tests
pytest src/skills/orchestrator-scheduler/tests/ -v

# Manual test with environment override
CLAUDE_SESSION_ID=test-session-123 /orchestrator-scheduler
```

---

## Future Enhancements

- [ ] Harness-native timer integration (e.g., every 30 seconds)
- [ ] Metrics collection (tasks/sec, error rate)
- [ ] Graceful shutdown handling
- [ ] Multi-harness coordination

---

## See Also

- [orchestrator](../orchestrator/SKILL.md) — Core queue orchestration
- [queue-isolation](../_meta/queue-isolation/SKILL.md) — Session/harness queue paths
- [DELEGATE/HANDBACK Protocol](../../docs/QUEUE-PROTOCOL.md)

---

## Self-Improvement

This skill participates in the framework's continuous improvement cycle
(see [skill-improvement-feedback](../skill-improvement-feedback/SKILL.md)).

When you use **orchestrator-scheduler**, include a skill_feedback entry in your HANDBACK:

```yaml
skill_feedback:
  - skill_name: orchestrator-scheduler
    effectiveness_score: 0.90
    usage_context: "Scheduled queue polling processed 3 DELEGATEs in 45 seconds"
```
