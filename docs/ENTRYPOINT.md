# Agentic Engineers: Standard Execution Model

**Canonical workflow for running agentic-engineers**

The system works across multiple agent contexts with per-session queue partitioning:
- **Copilot agents** queue work in `~/.copilot/queue/{session-id}/` (each session has isolated queue)
- **Claude agents** queue work in `~/.claude/queue/{session-id}/` (each session has isolated queue)
- Both use identical DELEGATE/HANDBACK protocol
- Orchestrator auto-detects session-id and uses session-specific queue partition
- Multiple simultaneous Copilot/Claude instances don't interfere with each other
- Legacy queue structure automatically migrated on first run

---

## 🎯 How to Use Agentic Engineers

When you have work to do:

### 1. Queue the work (create a DELEGATE block)

```bash
cd ~/.copilot/session-state/YOUR-SESSION/files/agentic-engineers
# OR
cd /home/user/agentic-engineers
```

Create a DELEGATE YAML in the appropriate session-specific queue:

**For Copilot agents:**
```bash
# Queue paths are now partitioned by session-id
# Get your session-id from COPILOT_SESSION_ID env var or ~/.copilot/session-state/
COPILOT_SESSION_ID=$(echo $COPILOT_SESSION_ID)  # Or discover from session-state

mkdir -p ~/.copilot/queue/$COPILOT_SESSION_ID/incoming
cat > ~/.copilot/queue/$COPILOT_SESSION_ID/incoming/{task_id}.yaml <<'EOF'
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
EOF
```

**For Claude agents:**
```bash
# Queue paths are now partitioned by session-id
CLAUDE_SESSION_ID=$(echo $CLAUDE_SESSION_ID)  # Or discover from session-state

mkdir -p ~/.claude/queue/$CLAUDE_SESSION_ID/incoming
cat > ~/.claude/queue/$CLAUDE_SESSION_ID/incoming/{task_id}.yaml <<'EOF'
# Same YAML structure as above
EOF
```

See `orchestration/HANDOFF.md` for complete DELEGATE format.

### 2. Start the Orchestrator Agent

The **Orchestrator** is a special agent defined in `orchestration/AGENTS.md` that:
- Auto-detects whether running in Claude or Copilot context
- Polls the correct queue (`~/.claude/queue/` or `~/.copilot/queue/`)
- Routes tasks to appropriate agents using AGENTS.md decision tree
- Delegates work via DELEGATE/HANDBACK protocol
- Processes results and moves tasks through queue states
- Captures observability (span data, indexing)
- Continues until queue is empty

**Invoke Orchestrator:**

The Orchestrator is invoked by the agent harness (Claude or Copilot CLI). Queue a DELEGATE task specifying `role: Orchestrator`:

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
  Tasks in queue awaiting delegation (Orchestrator auto-detects correct queue).
plan:
  - Auto-detect agent context (Claude vs Copilot)
  - Poll correct queue (~/.claude/queue or ~/.copilot/queue)
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

## 🔀 Multi-Session Queue Partitioning

When multiple Copilot or Claude instances run concurrently, each session has its own isolated queue partition:

### Session-ID Concept

- **Session-ID** is a UUID assigned to each Copilot/Claude instance
- Location: `~/.copilot/session-state/{session-id}/` or `~/.claude/session-state/{session-id}/`
- Each session's Orchestrator only polls its own queue partition
- No cross-contamination between simultaneous sessions

### Queue Paths by Session

```
~/.copilot/queue/
├── 54744939-4acb-430c-b2c4-3b8322289d0b/
│   ├── incoming/     # Tasks for this session only
│   ├── processing/
│   └── done/
├── 606ff436-b44b-47c5-90b8-f4bcc3fdb413/  # Different session
│   ├── incoming/
│   ├── processing/
│   └── done/
└── .migration-log    # Record of queue migrations
```

### Automatic Migration

When upgrading to session-id partitioning:
1. Old queue structure (`~/.copilot/queue/{incoming,processing,done}`) is auto-detected
2. Files are copied to new session-specific location
3. Old directories renamed to backup (e.g., `incoming-legacy-20260503-143022/`)
4. Migration logged in `.migration-log` for audit trail
5. Zero data loss — all work preserved

### Session-ID Detection

The Orchestrator detects your session-id using:
1. **COPILOT_SESSION_ID** environment variable (highest priority)
2. **CLAUDE_SESSION_ID** environment variable
3. Scan of `~/.copilot/session-state/` or `~/.claude/session-state/` (most recent session)

You can check your session-id:
```bash
# Print current session-id
echo $COPILOT_SESSION_ID

# Or find it from session-state
ls ~/.copilot/session-state/
```

### Troubleshooting Queue Not Found

If you see "queue not found" errors:
1. Verify your session-id: `echo $COPILOT_SESSION_ID`
2. Check queue exists: `ls ~/.copilot/queue/$COPILOT_SESSION_ID/incoming/`
3. Check migration log: `cat ~/.copilot/queue/.migration-log`
4. Verify session-state dir: `ls ~/.copilot/session-state/`

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

1. **Queue a task** → Create DELEGATE YAML in `~/.copilot/queue/{session-id}/incoming/`
   - Session-id auto-detected from environment or filesystem
2. **Start Orchestrator** → It polls your session's queue and delegates work
   - Multi-session support: Each session has isolated queue
3. **Check results** → Review `~/.copilot/queue/{session-id}/done/` and generated files
4. **Commit** → Add artifacts to git

That's it. Orchestrator handles routing, execution, observability, session isolation, and queue management. Everything is agent-based, auditable, and framework-native.
