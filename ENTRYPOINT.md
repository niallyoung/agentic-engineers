# Agentic Engineers: Standard Execution Model

**Canonical workflow for running agentic-engineers from `~/.copilot/`**

---

## 🎯 How to Use Agentic Engineers

When you have work to do:

### 1. Queue the work (create a DELEGATE block)

```bash
cd ~/.copilot/session-state/YOUR-SESSION/files/agentic-engineers
# OR
cd /home/user/agentic-engineers
```

Create a DELEGATE YAML in `artifacts/queue/incoming/{task_id}.yaml`:

```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-02-my-task
role: Engineer | Senior Engineer | Lead Engineer | Principal Engineer | Security Engineer | Quality Engineer | Model Engineer | Orchestrator
model: claude-haiku-4-5 | claude-sonnet-4-6 | claude-opus-4-7
effort: low | medium | high | max
scope: |
  Clear, one-sentence description of what the task is.
  What's in scope, what's out of scope.
context:
  - Key files: orchestration/AGENTS.md, orchestration/SKILLS.md
  - Related: Any prior commits or context
plan:
  - 1. First step
  - 2. Second step
success_criteria:
  - What "done" looks like
---
```

See `orchestration/HANDOFF.md` for complete DELEGATE format.

### 2. Start the Orchestrator Agent

The **Orchestrator** is a special agent defined in `orchestration/AGENTS.md` that:
- Polls `~/.copilot/queue/incoming/` every 30-60 seconds
- Routes tasks to appropriate agents using AGENTS.md decision tree
- Delegates work via DELEGATE/HANDBACK protocol
- Processes results and moves tasks through queue states
- Captures observability (span data, indexing)
- Continues until queue is empty

**Invoke Orchestrator:**

The Orchestrator is invoked by the Copilot CLI harness (not as a direct script). Queue a DELEGATE task specifying `role: Orchestrator`:

```yaml
---
handoff_type: DELEGATE
task_id: orchestrator-polling-session
role: Orchestrator
model: claude-haiku-4-5
effort: low
scope: |
  Poll queue and delegate all work to appropriate agents.
  Process until idle (no tasks for 60+ seconds).
context: |
  6 tasks in ~/.copilot/queue/incoming/ awaiting delegation.
plan:
  - Poll queue every 45 seconds
  - Route each task per AGENTS.md
  - Delegate with proper context
  - Wait for HANDBACK
  - Move to done/
  - Continue until idle
success_criteria:
  - All incoming tasks routed
  - HANDBACK results processed
  - Tasks moved through queue states
  - Exited cleanly on idle timeout
---
```

Then the Copilot CLI harness will invoke the Orchestrator agent which implements the SKILLs defined in `orchestration/SKILLS.md`.

### 3. Orchestrator handles everything

Once running, the Orchestrator:
1. ✅ Polls `artifacts/queue/incoming/` 
2. ✅ Routes tasks to appropriate agents (per AGENTS.md)
3. ✅ Delegates via DELEGATE blocks
4. ✅ Waits for agents to complete
5. ✅ Processes HANDBACK results
6. ✅ Captures span data (observability)
7. ✅ Updates `artifacts/index.json`
8. ✅ Moves tasks through queue: incoming → processing → done
9. ✅ Idles when queue is empty

### 4. Check results

**While Orchestrator is running:**
- Watch `artifacts/queue/processing/` for active tasks
- Watch `artifacts/queue/done/` for completed tasks
- Check `artifacts/` for generated files (SPAN files, index.json, reports)

**After Orchestrator completes:**
- Review `artifacts/queue/done/{task_id}-HANDBACK-{role}.yaml`
- Check generated artifacts (updated specs, reports, code changes)
- Review `artifacts/index.json` for metrics
- Commit results: `git add artifacts/ && git commit -m "..."`

---

## 📋 Example Workflows

### Workflow 1: Update Documentation

```bash
# 1. Create DELEGATE for spec extraction
cat > artifacts/queue/incoming/2026-05-02-update-spec.yaml << 'EOF'
---
handoff_type: DELEGATE
task_id: 2026-05-02-update-spec
role: Senior Engineer
model: claude-sonnet-4-6
effort: high
scope: Update docs/SPEC.md with current Phase 5.10 implementation
context:
  - Phase 5.10 just completed (span capture + indexing)
  - Update SPEC.md to reflect new SKILLS responsibilities
plan:
  - Read orchestration/SKILLS.md (Orchestrator + Model Engineer sections)
  - Review orchestration/SPAN-CAPTURE-INTEGRATION.md
  - Update docs/SPEC.md with Phase 5.10 details
  - Commit with Co-authored-by trailer
success_criteria:
  - docs/SPEC.md is current and complete
  - Phase 5.10 changes are documented
  - All implementation details match actual code
---
EOF

# 2. Start Orchestrator (it will pick up the task and delegate to Senior Engineer)
# Orchestrator polls queue, routes to Senior Engineer, receives HANDBACK
# Senior Engineer updates docs/SPEC.md and commits

# 3. Check results
cat artifacts/queue/done/2026-05-02-update-spec-HANDBACK-Senior\ Engineer.yaml
git log --oneline | head -1
```

### Workflow 2: Code Review & Validation

```bash
# 1. Create DELEGATE for code review
cat > artifacts/queue/incoming/2026-05-02-validate-impl.yaml << 'EOF'
---
handoff_type: DELEGATE
task_id: 2026-05-02-validate-impl
role: Lead Engineer
model: claude-sonnet-4-6
effort: high
scope: Validate implementation against docs/SPEC.md
context:
  - Spec: docs/SPEC.md
  - Implementation: orchestration/AGENTS.md, orchestration/SKILLS.md
plan:
  - Review spec
  - Audit implementation
  - Identify drift or violations
  - Create validation report
success_criteria:
  - artifacts/spec-validation-report.md created
  - All violations documented
  - No critical issues found
---
EOF

# 2. Start Orchestrator
# Orchestrator routes to Lead Engineer, receives HANDBACK, captures span data

# 3. Check report
cat artifacts/spec-validation-report.md
```

### Workflow 3: Fix Code Issues

```bash
# 1. Create DELEGATE for bug fix
cat > artifacts/queue/incoming/2026-05-02-fix-bug.yaml << 'EOF'
---
handoff_type: DELEGATE
task_id: 2026-05-02-fix-orchestrator-bug
role: Engineer
model: claude-haiku-4-5
effort: medium
scope: Fix race condition in Orchestrator span capture
context:
  - Bug: SPAN files sometimes overwrite in parallel execution
  - Root cause analysis in ISSUE #42
  - Related: orchestration/SPAN-CAPTURE-INTEGRATION.md
plan:
  - 1. RED: Write test that reproduces race condition
  - 2. GREEN: Implement file-locking mechanism
  - 3. REFACTOR: Clean up error handling
success_criteria:
  - Test passes
  - No race conditions under concurrent load
  - Code reviewed (check for violations of SKILLS.md)
---
EOF

# 2. Start Orchestrator
# Routes to Engineer, Engineer runs TDD (RED-GREEN-REFACTOR), returns HANDBACK

# 3. Check results
cat artifacts/queue/done/2026-05-02-fix-orchestrator-bug-HANDBACK-Engineer.yaml
```

---

## 🏗️ Queue Structure

```
artifacts/queue/
├── incoming/                          # New tasks, ready for Orchestrator
│   ├── 2026-05-02-my-task.yaml
│   └── 2026-05-02-another-task.yaml
├── processing/                        # Tasks assigned to agents
│   ├── 2026-05-02-my-task-HANDBACK-Engineer.yaml
│   └── [agent working...]
└── done/                              # Completed tasks
    ├── 2026-05-02-my-task-HANDBACK-Engineer.yaml
    └── [results + metrics]
```

---

## 🤖 Key Agents (See AGENTS.md for full details)

| Role | Model | When to Use |
|------|-------|------------|
| **Engineer** | Haiku (fast) | Well-scoped work with a plan (code, docs, fixes) |
| **Senior Engineer** | Sonnet (strong) | Complex work, research, design, spec extraction |
| **Lead Engineer** | Sonnet (strong) | Code review, validation, quality gates |
| **Principal Engineer** | Opus (premium) | Cross-service architecture, major decisions |
| **Security Engineer** | Opus (premium) | Security reviews, auth, crypto, compliance |
| **Quality Engineer** | Sonnet (strong) | Test quality, coverage, best practices |
| **Model Engineer** | Sonnet (strong) | Cost-quality tradeoffs, recommendations |
| **Orchestrator** | All models | Routing, delegation, observability, queue management |

See `orchestration/AGENTS.md` for full decision tree.

---

## 📊 Observability & Metrics

After tasks complete, Orchestrator generates:

**SPAN files** (OpenTelemetry):
```
artifacts/2026-05-02/
├── SPAN-2026-05-02T10:20:00Z-Engineer.yaml
├── SPAN-2026-05-02T10:25:00Z-Senior\ Engineer.yaml
└── SPAN-2026-05-02T10:30:00Z-Lead\ Engineer.yaml
```

**Index** (for searching):
```
artifacts/index.json
{
  "by_file_type": {
    "DELEGATE": [...],
    "HANDBACK": [...],
    "SPAN": [...]
  },
  "by_task_id": {...},
  "by_agent_type": {...},
  "stats": {
    "total_tokens": 125000,
    "total_cost": "$2.50",
    "total_tasks": 8,
    "success_rate": 1.0
  }
}
```

---

## ⚙️ Configuration

**Orchestrator behavior** (in future, can be configured via `orchestration/config.yaml`):
- Queue poll interval: 30-60 seconds (default: 45s)
- Max concurrent agents: 4 (default)
- Retry limit: 3 attempts before escalate
- Span capture: Enabled by default
- Index generation: After each HANDBACK

---

## 🔐 Security & Constraints

✅ **All work flows through agents** — no external scripts, cron jobs, or utilities
✅ **No direct file manipulation** — only via DELEGATE/HANDBACK protocol  
✅ **Audit trail** — all work tracked in queue and spans
✅ **Escalation path** — for blocked or rework items
✅ **Cost tracking** — SPAN files capture tokens and cost per task

See `docs/SPEC.md` for full architectural constraints.

---

## 📚 Reference

- **orchestration/AGENTS.md** — Full agent definitions, routing rules
- **orchestration/SKILLS.md** — How each agent executes their role
- **orchestration/HANDOFF.md** — DELEGATE/HANDBACK/FEEDBACK formats
- **orchestration/QUEUE-PROTOCOL.md** — Queue mechanics
- **docs/SPEC.md** — Complete specification & constraints

---

## 🚀 TL;DR

1. **Queue a task** → Create DELEGATE YAML in `artifacts/queue/incoming/`
2. **Start Orchestrator** → It polls queue and delegates work
3. **Check results** → Review `artifacts/queue/done/` and generated files
4. **Commit** → Add artifacts to git

That's it. Orchestrator handles routing, execution, observability, and queue management. Everything is agent-based, auditable, and framework-native.
