---
name: queue-query
description: >
  Local-queue visibility skill — query and inspect the per-session, per-harness
  filesystem queue by state (incoming backlog, processing orphans to resume,
  done results/next-steps). Format-agnostic (json + yaml). The local stepping
  stone toward the external memory-API queue interface.
license: Proprietary
compatibility: agentic-engineers framework v5.10+. Requires Python 3.11+
metadata:
  author: agentic-engineers
  version: "1.0.1"
  category: observability
  role: orchestrator
  model: claude-haiku-4.5
  effort: medium
  dependencies: []
entry_points:
  - scripts/queue_query.py
tests:
  - tests/test_queue_query.py
coverage_minimum: 85
---

# queue-query: Local Queue Visibility

Read-oriented queries over the canonical filesystem queue, complementing the
write/move operations in `queue-management`. Provides the visibility the
orchestrator poll-loop does not expose: backlog sizing, stale-task (orphan)
detection for resumption, and completed-task summaries.

Path isolation (session/harness detection, traversal-safe path construction) is
self-contained — inlined the same way as `queue-management/scripts/queue_ops.py`,
rather than imported from the deleted `_meta/queue-isolation` skill. Reads are
**format-agnostic** so the whole queue is observable regardless of whether a
task was written as `*.json` or `*.yaml`.

## Canonical queue layout

```
~/.agentic-engineers/<harness>/<session_id>/queue/
  incoming/    processing/    done/    failed/
```

## API

### `QueueQuery`

```python
from scripts.queue_query import QueueQuery

q = QueueQuery(session_id=None, harness=None, base_dir=None)  # auto-detect by default
```

| Method | Purpose |
|---|---|
| `ls(state)` | List every task in a state (json + yaml). |
| `count(state)` | Number of tasks in a state. |
| `count_by_state()` | `{incoming, processing, done, failed}` → counts. |
| `find_orphans(older_than_minutes)` | Processing tasks idle > N minutes (resume candidates). |
| `summarize_done()` | `{total, by_status, tasks[]}` for completed work. |

Orphan staleness is measured from each task file's modification time, which is
format-agnostic and updated on every state transition.

## CLI

```bash
python scripts/queue_query.py size                      # counts across all states
python scripts/queue_query.py size --state incoming     # backlog depth
python scripts/queue_query.py states --json             # machine-readable counts
python scripts/queue_query.py ls --state processing     # what's in flight
python scripts/queue_query.py orphans --older-than 30   # stale > 30 min (resume)
python scripts/queue_query.py summary --json            # done/ results + next-steps
```

Global flags: `--session-id`, `--harness`, `--base-dir` (testing), `--json`.

## Toward the external memory-API

`count_by_state`, `find_orphans`, and `summarize_done` are designed as the
local equivalents of future API endpoints. Swapping the filesystem backend for
the central queue API later requires changing only the data-access layer, not
the orchestrator call sites that consume these methods.

## Self-Improvement

This skill participates in the framework's continuous improvement cycle
(see [skill-improvement-feedback](../skill-improvement-feedback/SKILL.md)).

When you use **queue-query** during a task, include a skill_feedback entry
in your HANDBACK to help improve it over time:

```yaml
skill_feedback:
  - skill_name: queue-query
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
