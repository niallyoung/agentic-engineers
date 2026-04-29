---
name: Immediate Action Required - SDLC Agent Recovery
type: decision-log
date: 2026-04-28
priority: HIGH
---

# Immediate Action Required: Recover Full SDLC Agent Ecosystem

## The Issue

**We have narrowed scope from FULL SDLC to QUALITY GATE ONLY.**

### Current State ✅ (6 Agents)
- Quality Gate Orchestrator (Sonnet)
- Security Agent (Opus)
- Testing Agent (Haiku)
- Metrics Agent (Haiku)
- Healing Agent (Sonnet)
- Model Engineer Agent (Haiku)

**Cost**: $0.278/commit (optimized)  
**Scope**: Automated quality checks on every git commit  
**Timeline**: Phase 5.10 testing now, Phase 6–7 feedback loops

---

### Original Vision ❌ (Missing 6+ Agents)
From AGENTS.md:
```
Orchestrator (Haiku) — Route all work
├─ Engineer (Haiku) — Well-scoped implementation
├─ Senior Engineer (Sonnet) — Complex coding without plan
├─ Lead Engineer (Sonnet) — Architecture guidance
├─ Principal Engineer (Opus) — Cross-service design
├─ Quality Engineer (Sonnet) — Code review/validation
└─ Security Engineer (Opus) — Security-critical work
```

**Cost**: Variable per task ($0.15–$0.45)  
**Scope**: Route ALL software engineering work  
**Status**: Framework exists (AGENTS.md), implementations missing

---

## How This Happened

**Deliberate narrowing for Phase 5.10:**
1. User priority: "Quality Gate with feedback loops" (immediate CI/CD value)
2. We delivered: Fully optimized Quality Gate (6 agents, 28% cost reduction)
3. We deferred: SDLC routing (framework exists, agents missing)

**But user's original intent:** "agentic-engineers is home for all agents + skills... full SDLC"

---

## What Exists Now

| Component | Status | File |
|-----------|--------|------|
| **Quality Gate System** | ✅ Complete | `orchestration/agents/quality-gate-*.md` |
| **Feedback Loop Design** | ✅ Complete | `orchestration/handlers/*` |
| **SDLC Framework** | ✅ Done | `AGENTS.md` (routing rules) |
| **SDLC Agent Specs** | ❌ Missing | Need to create |
| **SDLC Agent Implementations** | ❌ Missing | Need to implement |

---

## Options

### Option 1: Keep Quality Gate Only (Current Path)
- Continue Phase 5.10 testing (QG focused)
- Continue Phase 6–7 feedback loops
- Document: "agentic-engineers = CI/CD quality gate"
- **Cost**: $0.278/commit
- **Scope**: Quality gates only

✅ Pros: Focused, complete, optimized  
❌ Cons: Not "full SDLC" as intended

---

### Option 2: Recover Full SDLC (Recommended) 🎯
- Phase 5.10: Quality Gate testing (as planned)
- **Phase 6**: Add General Orchestrator (Haiku, routing master)
- **Phase 7**: Add SDLC agents (Engineer, Senior Engineer, Quality Engineer)
- **Phase 8**: Add Principal Engineer (architecture)
- Document: "agentic-engineers = Full SDLC orchestration"

✅ Pros: Complete vision, full routing, all agent types  
❌ Cons: More work, 2+ week extension to Phase 6

---

### Option 3: Minimal Recovery (Hybrid)
- Phase 5.10: Quality Gate testing (as planned)
- **Phase 6**: Add General Orchestrator (Haiku, routing only)
- Defer SDLC agent implementations to Phase 7–8

✅ Pros: Quick, routing framework in place, agents can follow  
❌ Cons: Incomplete until agents added

---

## Recommendation: Option 2 (Full SDLC Recovery)

**Why**: 
1. Original vision was full SDLC orchestration
2. Framework (AGENTS.md) already exists
3. Quality Gate is complete; adding routing is natural next step
4. Agents can be phased in (no blocking dependencies)
5. All agents follow same DELEGATE/HANDBACK pattern (no surprises)

**Timeline**:
- Phase 5.10 (May 26–Jun 2): Quality Gate testing ✅
- Phase 6 (Jun 2–16): Feedback loops + General Orchestrator
- Phase 7 (Jun 16–30): SDLC agent implementations
- Phase 8 (Jul+): Principal Engineer, pattern recognition

**Cost Impact**: Quality Gate unchanged ($0.278/commit). SDLC tasks cost per-task ($0.15–0.36).

---

## Work Needed (If Choosing Option 2 or 3)

### Phase 6 Addition (1 week)
Create **1 new agent**:
- `orchestration/agents/general-orchestrator-agent.md`
  - Input: Task scope, context, estimated complexity
  - Routing: Use AGENTS.md rules to pick optimal agent
  - Output: HANDBACK with agent recommendation + confidence

### Phase 7 Addition (2 weeks)
Create **3 SDLC agent implementations**:
- `orchestration/agents/engineer-agent.md` (Haiku, high effort)
- `orchestration/agents/senior-engineer-agent.md` (Sonnet, high effort)
- `orchestration/agents/quality-engineer-agent.md` (Sonnet, medium effort)

Each follows same pattern as Quality Gate agents:
- Input: DELEGATE with task, plan, scope
- Process: Execute work (code, review, etc.)
- Output: HANDBACK with deliverables, tokens, assessment

### Phase 8 Addition (optional)
- `orchestration/agents/lead-engineer-agent.md` (Sonnet)
- `orchestration/agents/principal-engineer-agent.md` (Opus)

---

## Documentation Created (This Session)

Two new analysis documents:

1. **AGENT-ECOSYSTEM-RECOVERY.md** (450+ lines)
   - Full breakdown of current vs. missing agents
   - Historical context (why we narrowed scope)
   - Three options with pros/cons
   - Cost analysis

2. **AGENT-SETUP-SUMMARY.md** (350+ lines)
   - All 6 current agents sorted by model + cost
   - All 6+ missing agents listed
   - Gap analysis
   - Capability matrix (what we can do, what we can't)
   - Implementation checklist

---

## Decision Matrix

| Question | QG Only | Full SDLC | Hybrid |
|----------|---------|-----------|--------|
| Is agentic-engineers a full SDLC system? | ❌ | ✅ | ⚠️ |
| Can we route all engineering work? | ❌ | ✅ | 🔄 |
| Is AGENTS.md framework used? | ❌ | ✅ | ⚠️ |
| Can we implement SDLC agents later? | ✅ | ✅ | ✅ |
| Cost impact (QG operations)? | None | None | None |
| Implementation effort? | 0 | 3 weeks | 1 week |
| Risk to Phase 5.10? | None | None | None |

---

## What We Need From You (Right Now)

### Decision #1: SDLC Scope
Choose one:
- [ ] **QG Only**: Quality gates only, simplest path
- [ ] **Full SDLC**: General Orchestrator + all SDLC agents, complete vision
- [ ] **Hybrid**: General Orchestrator in Phase 6, agents in Phase 7

### Decision #2: Timeline
If choosing SDLC recovery:
- [ ] **Phase 6**: Add General Orchestrator (routing master)
- [ ] **Phase 7**: Add SDLC agents (implementation + review)
- [ ] **Phase 8**: Add advanced agents (architecture, lead engineer)

### Decision #3: Priority
If choosing SDLC recovery, which agents first?
- [ ] Engineer (Haiku, simple tasks)
- [ ] Senior Engineer (Sonnet, complex tasks)
- [ ] Quality Engineer (Sonnet, code review)
- [ ] (All equally important)

---

## Next Steps (After Your Decision)

### If QG Only
- Continue Phase 5.10 testing as planned
- Continue Phase 6–7 feedback loops
- Update README: "agentic-engineers focuses on CI/CD quality gates"
- Close this file

### If Full SDLC Recovery
- Phase 6: Create General Orchestrator agent
  - File: `orchestration/agents/general-orchestrator-agent.md`
  - Pattern: Copy from quality-gate-orchestrator-agent.md, adapt routing
- Update AGENTS.md: Link to actual agent implementations
- Update TODO.md: Add Phase 6 extension + Phase 7 agent implementations

### If Hybrid
- Phase 6: Create General Orchestrator (same as Full SDLC)
- Phase 7: Create SDLC agent implementations
- Phase 8+: Create advanced agents

---

## No Risk to Phase 5.10

**Important**: Whatever you choose does NOT affect Phase 5.10.

- Quality Gate testing proceeds as planned
- All 6 agents continue unchanged
- Feedback loops designed in Phase 6 (proceed as planned)
- SDLC agents are additive (no breaking changes)

This is pure scope clarification + architecture recovery. Not a rollback.

---

## Files Ready for Review

1. **AGENT-ECOSYSTEM-RECOVERY.md** — Full analysis of gap + options
2. **AGENT-SETUP-SUMMARY.md** — Table of all agents + missing implementations
3. **IMMEDIATE-ACTION-REQUIRED.md** — This file (decision log)

All analysis done. Ready for your decision on scope.
