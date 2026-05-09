# Orchestration — Task Routing & Coordination

**Skills for routing tasks to appropriate roles and coordinating between agents.**

## Skills in This Directory

| Skill | Used By | Purpose |
|-------|---------|---------|
| **task-routing.md** | Orchestrator | Make task routing decisions using AGENTS.md rules |
| **todo-management.md** | Orchestrator, Lead Engineer, Principal Engineer, Security Engineer | Planning & task tracking (TODO.md), daily checkpoints, blockers |
| **model-engineer-coordination.md** | Orchestrator | Work with Model Engineer on model optimization |
| **github-cli.md** | All roles | GitHub API operations (PR/issue/workflow management) |
| **github-cli-operations.md** | Orchestrator | GitHub CLI automation for orchestration tasks |

## When to Use

- **Receiving a task** — Orchestrator uses task-routing.md to pick the right role
- **Planning session work** — Orchestrator creates TODO.md using todo-management.md; other roles contribute status updates
- **Daily checkpoint** — Orchestrator runs hourly updates using TODO.md format (completed, in-progress, blocked)
- **Optimizing future tasks** — Orchestrator uses model-engineer-coordination.md
- **Managing GitHub** — Any role uses github-cli.md for API operations
- **Automating GitHub tasks** — Orchestrator uses github-cli-operations.md

## Orchestration Flow

```
User tasks arrive
  ↓
Orchestrator (todo-management.md): Create TODO.md
  ↓
Orchestrator (task-routing.md): complexity? scope? specialty?
  ↓
→ Route to appropriate role
  ↓
Create DELEGATE markup (orchestration/HANDOFF.md)
  ↓
Update TODO.md → IN_PROGRESS
  ↓
Agent executes
  ↓
Update TODO.md → DONE (log completion time, result)
  ↓
Return HANDBACK with metrics
  ↓
Orchestrator: Record metrics, plan next task
```

## See Also

- `../orchestration/` (root) — AGENTS.md, HANDOFF.md, QUALITY.md
- `../monitoring/` — Metrics that feed routing decisions
- `../optimization/` — Model recommendations for routing
