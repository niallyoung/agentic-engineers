# Queue-Based Delegation Integration

Complete refactoring to implement queue-based delegation with Orchestrator as a harness agent.

---

## What Changed

### 1. Queue System (Simple File-Based)

**Before:** Direct agent-to-agent delegation; Orchestrator sent DELEGATEs via messages.

**After:** Indirect delegation via queue files:
- `artifacts/queue/incoming/` — New work (Orchestrator polls)
- `artifacts/queue/processing/` — Work in progress (HANDBACK from agents)
- `artifacts/queue/done/` — Completed (human decides: merge/rework/escalate)

**Benefit:** Decouples agents, enables batch processing, audit trail via files.

### 2. Red-Green TDD (Engineer Skill, Not Gate)

**Before:** Mandatory enforcement; QE rejects if missing evidence.

**After:** Optional practice in Engineer SKILLS.md
- Engineer can use Red-Green TDD for code quality
- Quality Engineer does NOT check for Red-Green evidence
- No `red_green_tdd_required` field in DELEGATE
- No `red_green_evidence` in HANDBACK

**Benefit:** Simplifies, removes enforcement overhead, focuses on outcomes not methodology.

### 3. Orchestrator (Harness Agent, Not External Tool)

**Before:** Implied external orchestration service.

**After:** Orchestrator runs as harness agent
- Implemented in AGENTS.md + SKILLS.md
- Polls queues every 30-60s (in harness loop)
- Routes per AGENTS.md decision tree
- No external cron jobs, shell scripts, or external tools
- 100% pure agent-based

**Benefit:** Self-contained, no external dependencies, harness integrates naturally.

---

## Core Documents

### AGENTS.md (Who + When + Routing)

Defines:
- 8 SDLC agent roles (Engineer, Senior Engineer, Lead Engineer, Principal, Security, Quality, Model, Orchestrator)
- Model assignments (Haiku, Sonnet, Opus)
- Cost targets per role
- Routing decision tree (which role for which task)
- Mandatory constraints:
  - Queue-based delegation (`incoming/ → processing/ → done/`)
  - Engineer needs pre-written plan
  - Orchestrator doesn't perform work
  - Role-specific rules (escalations, blockers)

### SKILLS.md (How + Execution)

Defines per-role:
- **Engineer:** Execute well-scoped plan; recommend Red-Green TDD for code quality
- **Senior Engineer:** Design solutions; diagnose complex bugs; write plans
- **Lead Engineer:** Code review (Tier 1/2/3); unblock stuck tasks
- **Quality Engineer:** Run Tier 1 checklist; assess model performance
- **Principal Engineer:** Cross-service architecture design
- **Security Engineer:** Vulnerability scanning, threat modeling
- **Model Engineer:** Analyze feedback; recommend routing optimizations
- **Orchestrator:** Route tasks; manage queue transitions; apply recommendations

### QUEUE-PROTOCOL.md (Mechanics)

Defines:
- Queue structure (`incoming/processing/done/`)
- DELEGATE/HANDBACK storage locations
- File naming conventions
- How Orchestrator polls and routes
- Integration with AGENTS.md (uses routing tree)

### HANDOFF.md (Format)

Defines:
- DELEGATE block structure (minimal, no Red-Green TDD fields)
- HANDBACK block structure (outcome + metrics)
- Example flows
- Quality Engineer verification process

---

## Workflow Example

```
1. Task arrives in artifacts/queue/incoming/

2. Orchestrator polls every 30-60s
   └─ Reads task, applies AGENTS.md routing tree
   └─ Creates DELEGATE (HANDOFF.md format)
   └─ Stores in artifacts/delegates/YYYY-MM-DD/
   └─ Sends to appropriate agent

3. Agent receives DELEGATE
   └─ Reads SKILLS.md for role-specific guidance
   └─ Executes work (Engineer can opt for Red-Green TDD)
   └─ Returns HANDBACK with results

4. Orchestrator polls processing/
   └─ Routes complete work to Quality Engineer
   └─ Escalates blocked work to Lead/Senior Engineer

5. Quality Engineer verifies
   └─ Runs Tier 1 checklist (tests pass, lint clean, no scope creep)
   └─ Assesses model performance (was Haiku suitable?)
   └─ Adds qe_feedback
   └─ Moves to artifacts/queue/done/

6. Orchestrator polls done/
   └─ PROCEED → merge to main
   └─ REWORK → create new DELEGATE with feedback
   └─ ESCALATE → promote to higher role

7. Feedback loop (async)
   └─ Model Engineer analyzes QE feedback
   └─ Generates routing recommendations
   └─ Orchestrator uses for next similar task
```

---

## Integration Checklist

- [x] Queue system files created (`incoming/processing/done/`)
- [x] AGENTS.md updated (queue constraints, simplified)
- [x] SKILLS.md rewritten (role-specific workflows)
- [x] QUEUE-PROTOCOL.md simplified (just mechanics)
- [x] HANDOFF.md cleaned (removed Red-Green TDD enforcement)
- [x] All Red-Green TDD enforcement removed from quality gates
- [x] Orchestrator defined as harness agent (polls in loop)
- [x] No external tools referenced (100% agent-based)

---

## Key Properties

✅ **Platform-Independent** — Works with any harness (Claude Code, custom, open-source)  
✅ **Agent-Based** — Everything is AGENTS.md + SKILLS.md; no external services  
✅ **Queue-Decoupled** — Agents don't know about each other; queue is mediator  
✅ **Auditable** — All DELEGATE/HANDBACK stored in artifacts/  
✅ **Flexible** — Red-Green TDD optional; focuses on outcomes  
✅ **Scalable** — Can migrate queue to database later (API layer on top)

---

## What's Ready

✅ **Architecture complete** — AGENTS.md + SKILLS.md + QUEUE-PROTOCOL.md + HANDOFF.md aligned  
✅ **Queue structure created** — `artifacts/queue/{incoming,processing,done}/` ready  
✅ **Examples included** — Sample DELEGATEs and HANDBACKs in artifacts/  
✅ **No external dependencies** — Pure harness + file queue  

---

## What's Next

1. **Implement Orchestrator agent** (runs in harness, polls queue loop)
2. **Integrate agents** with existing harness
3. **Test end-to-end** workflow with real tasks
4. **Optimize** based on operational feedback

---

## Files

| Document | Purpose |
|----------|---------|
| AGENTS.md | Role definitions, routing, constraints |
| SKILLS.md | Role-specific execution workflows |
| QUEUE-PROTOCOL.md | Queue mechanics (incoming/processing/done/) |
| HANDOFF.md | DELEGATE/HANDBACK format and examples |
| artifacts/queue/ | Queue directories with examples |

