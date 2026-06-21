---
name: queue-monitor
description: >
  Live queue monitoring dashboard (curses TUI) for real-time visibility into
  DELEGATE/HANDBACK protocol queue status, metrics, and task progress across
  incoming, processing, and done states.
license: Proprietary
compatibility: agentic-engineers framework v5.10+. Requires Python 3.11+
metadata:
  author: agentic-engineers
  version: "1.0.0"
  category: observability
  role: orchestrator
  model: claude-haiku-4.5
  effort: high
  dependencies:
    - skill: queue-isolation
      optional: true
    - skill: queue-query
      optional: false
entry_points:
  - scripts/queue_monitor.py
tests:
  - tests/test_queue_monitor.py
coverage_minimum: 85
---

# queue-monitor: Live Queue Monitoring Dashboard

Real-time curses-based TUI for monitoring the agentic-engineers queue. Displays
live queue metrics, DELEGATE/HANDBACK task progress, and agent execution status
across incoming, processing, and done states.

## Features

- **Real-time polling**: Updates every 5 seconds
- **3-column view**: Incoming backlog, processing tasks, completed results
- **Metrics summary**: Task counts, success/failure rates, average duration
- **YAML parsing**: Extracts task_id, agent, duration from DELEGATE/HANDBACK files
- **Terminal-friendly**: Curses-based TUI, no external UI frameworks
- **Resize handling**: Adapts to terminal size changes gracefully

## Canonical queue layout

```
~/.agentic-engineers/<harness>/<session-id>/queue/
  incoming/    processing/    done/    failed/
```

## CLI

```bash
python scripts/queue_monitor.py --session-id wave1-2026-06-15 --harness claude
python scripts/queue_monitor.py                                              # auto-detect
python scripts/queue_monitor.py --base-dir /custom/path --harness local     # custom paths
```

Global flags: `--session-id`, `--harness`, `--base-dir` (testing).

## Dashboard layout

```
QUEUE MONITOR — Status: 3 incoming, 1 processing, 5 done

┌─────────────────────┬──────────────────┬──────────────────────┐
│     INCOMING (3)    │  PROCESSING (1)  │      DONE (5)        │
├─────────────────────┼──────────────────┼──────────────────────┤
│ [2026-06-15-001]    │ [2026-06-15-002] │ [2026-06-15-005] ✓   │
│ harness-eval        │ skills-audit     │ duration: 45s        │
│ quality-engineer    │ model-engineer   │                      │
│                     │ 15s (running)    │ [2026-06-15-004] ✓   │
│ [2026-06-15-003]    │                  │ duration: 120s       │
│ queue-monitor       │                  │                      │
│ engineer            │                  │ [2026-06-15-003] ✗   │
│                     │                  │ failure: timeout     │
│ [2026-06-15-006]    │                  │                      │
│ spec-validation     │                  │ [2026-06-15-002] ✓   │
│ security-engineer   │                  │ duration: 180s       │
│                     │                  │                      │
│                     │                  │ [2026-06-15-001] ✓   │
│                     │                  │ duration: 300s       │
└─────────────────────┴──────────────────┴──────────────────────┘

METRICS SUMMARY
Incoming: 3  │  Processing: 1  │  Done: 5 (success: 4, failure: 1)
Avg duration: 161s  │  Success rate: 80%  │  Last updated: 2026-06-15 17:45:32

Press 'q' to quit, 'r' to refresh, 's' for stats detail
```

## API

```python
from scripts.queue_monitor import QueueMonitor, QueueMonitorUI

monitor = QueueMonitor(session_id=None, harness=None, base_dir=None)
ui = QueueMonitorUI(monitor)
ui.run()
```

Methods:

| Method | Purpose |
|---|---|
| `poll()` | Refresh queue state from filesystem. |
| `get_metrics()` | Return aggregated metrics dict. |
| `get_task_details(state, task_id)` | Return parsed DELEGATE/HANDBACK details. |

## Implementation notes

- Curses rendering handles terminal resizing via `curses.SIGWINCH`
- Polling interval: 5 seconds (configurable)
- YAML parsing is format-agnostic (json + yaml supported)
- Task durations calculated from file mtimes (modified time)
- Colors used: green (success), red (failure), yellow (processing)

## Self-Improvement

This skill participates in the framework's continuous improvement cycle
(see [skill-improvement-feedback](../skill-improvement-feedback/SKILL.md)).

When you use **queue-monitor** during a task, include a skill_feedback entry
in your HANDBACK to help improve it over time:

```yaml
skill_feedback:
  - skill_name: queue-monitor
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
