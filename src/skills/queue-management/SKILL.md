---
name: queue-management
description: Atomic DELEGATE/HANDBACK audit-trail writes with ancestry-based cycle detection and session/harness path isolation. The one sanctioned way to record a direct sub-agent spawn's DELEGATE and HANDBACK to the durable queue.
license: Proprietary
compatibility: agentic-engineers framework v5.10+. Requires Python 3.8+
metadata:
  author: agentic-engineers
  version: "2.0"
  category: task-management
  role: orchestrator
  model: claude-haiku-4.5
  effort: high
  thinking: false
  dependencies: []
---

# queue-management

## Overview

Queue Management provides the one sanctioned write path for the DELEGATE/HANDBACK
**audit trail**. In the direct sub-agent spawn execution model (see `src/AGENTS.md`),
dispatch already happens via a direct Agent/Task-tool spawn — this skill does not
dispatch anything. It durably records what already happened: every DELEGATE at spawn
time, every HANDBACK at completion.

**What it does:**

1. **Atomic enqueue()** — Writes a DELEGATE (→ `incoming/`) or HANDBACK
   (→ `processing/`) via temp-file-then-rename. No partial files, ever.
2. **Schema validation** — Canonical `handoff_type`/`agent`/`task_id`/`metrics`/`status`
   fields; rejects legacy `type`/`role`/`quality_score` with actionable errors.
3. **Ancestry-based cycle detection** — Refuses a DELEGATE whose target `agent` already
   appears in its `ancestry` extension field, and refuses ancestry chains at or beyond
   max delegation depth (3).
4. **Path isolation** — Resolves the canonical
   `~/.agentic-engineers/{harness}/{session-id}/queue/` layout, with traversal-safe
   validation of `session_id`/`harness` inputs.
5. **Append-only audit log** — Every `enqueue()` call appends one line to
   `.../{session-id}/audit.log`, independent of the per-task YAML file's later moves.

## Usage

```python
from skills.queue_management.scripts.queue_ops import QueueOperations

ops = QueueOperations(session_id=session_id)  # harness auto-detected from env

# Record a DELEGATE immediately after a direct spawn (dispatch already happened)
ops.enqueue({
    "handoff_type": "DELEGATE",
    "task_id": "my-task-001",
    "agent": "engineer",             # NOT "role": "Engineer"
    "scope": "... >= 15 words ...",
    "plan": ["step 1 ...", "step 2 ..."],
    "context": "... >= 20 words ...",
    "success_criteria": ["criterion 1"],
    "ancestry": ["orchestrator"],     # required when spawning agent itself has depth > 0
})

# Record the HANDBACK once the spawn call returns
ops.enqueue({
    "handoff_type": "HANDBACK",
    "task_id": "my-task-001",
    "agent": "engineer",
    "status": "success",
    "output": "...",
    "metrics": {"quality": 0.9, "tokens": 1200, "cost": 0.02, "duration_seconds": 30},
})

# Move a HANDBACK from processing/ to done/ once resolved (optional bookkeeping)
ops.move_task("my-task-001", "processing", "done")
```

**FORBIDDEN:** writing directly to `incoming/`, `processing/`, `done/`, or `failed/`.
Every write goes through `enqueue()` — this is what enforces schema and the audit
trail's integrity.

## Cycle & Depth Rules

`ancestry` is the ordered list of agent roles from the root DELEGATE to the spawning
parent, inclusive (see `src/AGENTS.md` > Recursion Limits). `enqueue()` raises
`RuntimeError` when:

- the target `agent` already appears in `ancestry` (a genuine cycle — e.g. Lead
  Engineer's follow-on DELEGATE re-targeting the Senior Engineer that escalated to it
  for the same task), or
- `len(ancestry) >= 3` (max delegation depth reached — the spawning agent is already at
  depth 3 and must execute or refuse, not delegate further).

`ancestry` is an optional extension field; DELEGATEs without it (e.g. the
Orchestrator's own root-level DELEGATEs) skip this check entirely.

## API Surface

`src/skills/queue-management/scripts/queue_ops.py` is the entire implementation
(~440 LOC, no other scripts in this skill):

- `QueueOperations(session_id, queue_path=..., harness=...)` — constructor; ensures
  `incoming/processing/done/failed/` exist.
- `.enqueue(artifact: dict) -> dict` — validate + atomic write + audit append.
- `.move_task(task_id, from_state, to_state) -> dict` — atomic state transition.
- `detect_harness()`, `get_session_id()`, `get_queue_path()` — path isolation helpers,
  also usable standalone by `queue-query` and other read-only inspection skills.
- `has_cycle(target_role, ancestry)`, `exceeds_max_depth(ancestry)` — the cycle/depth
  predicates `enqueue()` uses internally, exposed for reuse.

## Testing

```bash
pytest src/skills/queue-management/tests/
```

Covers: enqueue schema validation (legacy-field rejection, required fields), atomic
write (valid YAML, no leftover temp files, correct target state), audit-log
append-only behavior, path isolation (traversal rejection, session isolation), and
ancestry-based cycle/depth detection.

## Self-Improvement

This skill participates in the framework's continuous improvement cycle (see
[`skill-improvement-feedback`](../skill-improvement-feedback/SKILL.md)). Include a
`skill_feedback` entry in your HANDBACK when you use `queue-management`:

```yaml
skill_feedback:
  - skill_name: queue-management
    effectiveness_score: 0.9         # required: 0.0-1.0
    coverage_gaps: []
    improvement_suggestions: []
    usage_context: "One sentence on how you used this skill"
```
