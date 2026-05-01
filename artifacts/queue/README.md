# Queue System

Active queue-based workflow. Orchestrator continuously monitors this directory.

## Directories

- **incoming/** — New work from external sources; Orchestrator polls every 30-60s
- **processing/** — Work assigned to agent; awaiting HANDBACK from agent
- **done/** — Completed work; Orchestrator decides next step (PROCEED, REWORK, ESCALATE)

## Artifact Lifecycle

### 1. Incoming

Orchestrator finds task here:
```
incoming/
└── 2026-04-30-fix-token-timeout-NEW.yaml
```

Orchestrator reads, creates DELEGATE, sends to agent, moves task to:

### 2. Processing

Agent receives DELEGATE, executes work, returns HANDBACK:
```
processing/
└── 2026-04-30-fix-token-timeout-HANDBACK-Engineer.yaml
```

Orchestrator polls this directory, routes HANDBACK to Quality Engineer.

### 3. Done

Quality Engineer verifies, adds feedback, moves to:
```
done/
├── 2026-04-30-fix-token-timeout-complete.yaml       # PROCEED
├── 2026-04-30-fix-token-timeout-rejected.yaml       # REWORK (QE rejected)
└── 2026-04-30-another-task-escalated.yaml            # ESCALATE (to Senior Engineer)
```

Orchestrator polls this directory, acts on final decision.

## File Naming

| Stage | Format | Example |
|-------|--------|---------|
| Incoming | `{task_id}-NEW.yaml` | `2026-04-30-fix-timeout-NEW.yaml` |
| Processing | `{task_id}-HANDBACK-{role}.yaml` | `2026-04-30-fix-timeout-HANDBACK-Engineer.yaml` |
| Done | `{task_id}-{status}.yaml` | `2026-04-30-fix-timeout-complete.yaml` |

## Retention

- **incoming/** — Purged after 4 hours (task should move to processing within that time)
- **processing/** — Purged after 8 hours (agent should complete within that time)
- **done/** — Purged after 24 hours (Orchestrator should make final decision)
- Archived tasks moved to `../archive/YYYY-MM-DD/` for historical reference

## Orchestrator Loop

```python
while True:
    # Poll every 30-60 seconds
    
    # 1. Check incoming/
    for task in list_files("incoming/"):
        delegate = create_delegate(task)
        route_to_agent(delegate)
        move(task, f"processing/{task.id}-NEW.yaml")
    
    # 2. Check processing/
    for handback in list_files("processing/"):
        if handback.status == "complete":
            route_to_quality_engineer(handback)
        elif handback.status == "blocked":
            route_to_senior_engineer(handback)
    
    # 3. Check done/
    for result in list_files("done/"):
        if result.decision == "PROCEED":
            merge(result.repo, result.commit)
        elif result.decision == "REWORK":
            create_new_delegate(result)
            move_to_incoming(new_delegate)
        elif result.decision == "ESCALATE":
            escalate_and_notify(result)
    
    sleep(30)
```

## Integration Points

- **DELEGATE artifacts** stored in `../delegates/YYYY-MM-DD/` (not in queue; stays in queue for ref)
- **Feedback loops** stored in `../feedback/` (model recommendations, pattern analysis)
- **Archive** in `../archive/YYYY-MM-DD/` (historical tasks, searchable by date)

