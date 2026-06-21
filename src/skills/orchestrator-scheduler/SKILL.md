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
| 2 | `COPILOT_SESSION_ID` | (required for copilot harness) |
| 3 | `AGENTIC_SESSION_ID` | (generic session override) |
| 4 | `AGENTIC_HARNESS` | `claude` (default) |

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

### Integration Points

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
| Session ID missing | Raises error with suggestion | Set `CLAUDE_SESSION_ID` in environment |

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
