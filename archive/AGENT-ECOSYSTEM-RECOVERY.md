---
name: Agent Ecosystem Recovery & Full SDLC Mapping
description: Complete agent setup mapping - current vs. missing - sorted by model and cost
type: architecture
date: 2026-04-28
status: RECOVERY_ANALYSIS
---

# Agent Ecosystem Recovery: Current State vs. Full Vision

**Critical Finding**: We have narrowed scope from **full SDLC orchestration** (8+ agent types) to **Quality Gate only** (4 sub-agents). Missing implementations need recovery.

---

## Summary: All Agents by Model (Ascending Cost)

### Current State: 6 Agents Implemented ✅

| Model | Role | Effort | Cost/Task | Status | File |
|-------|------|--------|-----------|--------|------|
| **Haiku** | Testing Agent | medium | $0.034 | ✅ IMPLEMENTED | `testing-agent.md` |
| **Haiku** | Metrics Agent | low | $0.028 | ✅ IMPLEMENTED | `metrics-agent.md` |
| **Haiku** | Model Engineer Agent | medium | $0.009 | ✅ IMPLEMENTED | `model-engineer-agent.md` |
| **Sonnet** | Quality Gate Orchestrator | high | $0.026 | ✅ IMPLEMENTED | `quality-gate-orchestrator-agent.md` |
| **Sonnet** | Healing Agent | high | $0.096 | ✅ IMPLEMENTED | `healing-agent.md` |
| **Opus** | Security Agent | max | $0.085 | ✅ IMPLEMENTED | `security-agent.md` |

**Total Phase 5.10**: $0.278/commit (optimized)

---

### Missing from AGENTS.md: 6+ Agents ❌

| Model | Role | Effort | Cost/Task | Scope | Status | Notes |
|-------|------|--------|-----------|-------|--------|-------|
| **Haiku** | Orchestrator (General SDLC) | low | $0.03 | Routing, task assignment | ❌ MISSING | Entry point for all work |
| **Haiku** | Engineer | high | $0.03 | Well-scoped implementation | ❌ MISSING | Direct code execution |
| **Sonnet** | Quality Engineer | medium | $0.09 | Code review, validation | ❌ MISSING | Post-implementation QA |
| **Sonnet** | Senior Engineer | high | $0.09 | Complex coding, diagnosis | ❌ MISSING | Without pre-written plan |
| **Sonnet** | Lead Engineer | high | $0.09 | Architecture guidance, decisions | ❌ MISSING | Code review, medium planning |
| **Opus** | Principal Engineer | high | $0.15 | Cross-service architecture | ❌ MISSING | Design decisions, 2+ repos |

**Missing SDLC Total**: ~$0.60/task (for complex work)

---

## Architecture: Two Separate Systems

We have **TWO distinct agent systems** that got conflated:

### System 1: Quality Gate Orchestration (Phase 5.10) ✅ COMPLETE

**Purpose**: Automated quality checks on every git commit  
**Entry Point**: `make quality-gate` / git hook  
**Agents**: Master orchestrator + 4 parallel sub-agents  
**Decision**: Binary (PROCEED/ESCALATE)  
**Timeline**: 4–5 min per commit  
**Cost**: $0.278/commit

**Implemented Agents**:
```
Quality Gate Orchestrator (Sonnet) [master]
  ├─ Security Agent (Opus)
  ├─ Testing Agent (Haiku)
  ├─ Metrics Agent (Haiku)
  └─ Healing Agent (Sonnet)

Async:
  └─ Model Engineer Agent (Haiku) [feedback loop]
```

---

### System 2: General SDLC Orchestration (NOT IMPLEMENTED) ❌

**Purpose**: Route all software engineering work to optimal agents  
**Entry Point**: User request / task assignment  
**Agents**: Master orchestrator + 6 specialized roles  
**Decision**: Which agent + model + effort for this task?  
**Timeline**: Variable (minutes to hours)  
**Cost**: Per-task, optimized by feedback loop

**Should Exist**:
```
Orchestrator (Haiku) [master]
  ├─ Engineer (Haiku) — well-scoped tasks
  ├─ Senior Engineer (Sonnet) — complex work, no plan
  ├─ Lead Engineer (Sonnet) — reviews, medium planning
  ├─ Principal Engineer (Opus) — cross-service architecture
  ├─ Security Engineer (Opus) — security-critical work
  └─ Quality Engineer (Sonnet) — code review, validation

Feedback:
  └─ Model Engineer (Haiku) — recommends model/effort for next similar task
```

---

## Historical Context: What Was Built

### Week 1 Designs (AGENT-SPECS-WEEK1-DESIGNS.md)
Defined **7 operational agents** supporting Quality Gate:
1. Quality Gate Orchestrator (master)
2. Token Advisor (Model Engineer) 
3. Config Audit (Quality Engineer role)
4. Config Enforcement (Senior Engineer role)
5. CICD Monitor 
6. Cleanup (Engineer role)
7. Voice Notify (Engineer role)

These are **operational agents** (not SDLC agents), but we only implemented Quality Gate + its 4 sub-agents.

### AGENTS.md (Foundational)
Defined **8 SDLC agent roles** for general work routing:
1. Orchestrator (Haiku, low effort) — entry point
2. Engineer (Haiku, high effort) — implementation
3. Quality Engineer (Sonnet, medium effort) — validation
4. Senior Engineer (Sonnet, high effort) — complex coding
5. Lead Engineer (Sonnet, high effort) — architecture guidance
6. Principal Engineer (Opus, high effort) — cross-service design
7. Security Engineer (Opus, max effort) — security-critical
8. Model Engineer (Sonnet, high effort) — feedback & recommendations

We have **model selection strategy** for these but no **agent implementations**.

---

## Why We Narrowed Scope

**Deliberate Decision** (Context: Phase 5.10 focus):
- User said: "Focus on agentic-engineers → AGENTS with SKILLS primarily, we want all loops and activity coordinated here in claude/copilot cli"
- We prioritized: Quality Gate (CI/CD integration, immediate value)
- We deferred: General SDLC agents (broader but less urgent)

**Trade-off Made**:
- ✅ Shipped: Fully optimized Quality Gate (6 agents, 28% cost reduction, Phase 6 feedback loops designed)
- ❌ Deferred: General SDLC routing (would need Orchestrator + 6 agent implementations)

---

## Current Implementation Status

| Agent Type | Phase 5.10 | Phase 6+ | General SDLC |
|------------|-----------|---------|---|
| Quality Gate Orchestrator | ✅ Done | ✅ Designed (feedback loops) | — |
| Security Agent (Opus) | ✅ Done | ✅ Designed | ❌ Missing spec |
| Testing Agent (Haiku) | ✅ Done | ✅ Designed | ❌ Missing spec |
| Metrics Agent (Haiku) | ✅ Done | ✅ Designed | ❌ Missing spec |
| Healing Agent (Sonnet) | ✅ Done | ✅ Designed | ❌ Missing spec |
| Model Engineer (Haiku) | ✅ Done | ✅ Designed | ❌ Missing spec |
| **Orchestrator (SDLC)** | ❌ Missing | — | ❌ No spec |
| **Engineer** | ❌ Missing | — | ❌ No spec |
| **Senior Engineer** | ❌ Missing | — | ❌ No spec |
| **Lead Engineer** | ❌ Missing | — | ❌ No spec |
| **Principal Engineer** | ❌ Missing | — | ❌ No spec |
| **Quality Engineer** | ❌ Missing | — | ❌ No spec |
| **Security Engineer** | ❌ Missing | — | ❌ No spec |

---

## What AGENTS.md Says (Foundational Framework)

```yaml
Entry Point: Orchestrator (Haiku, low effort)

Routing Rules:
  IF security-scoped → Security Engineer (Opus)
  ELIF cross-service architecture → Principal Engineer (Opus)
  ELIF complex coding without plan → Senior Engineer (Sonnet, to write plan first)
  ELIF code review or validation → Quality Engineer (Sonnet)
  ELIF architectural guidance → Lead Engineer (Sonnet)
  ELIF well-planned, low-medium complexity → Engineer (Haiku)

Feedback Loop:
  After Quality Engineer validates
    → Model Engineer analyzes token efficiency
    → Recommends optimal model/effort for next similar task
    → Orchestrator applies recommendation
```

This is **NOT implemented as agents**. It exists as **routing logic only**.

---

## Re-Integration Plan: Option A (Full SDLC)

If we want **complete agentic-engineers** (not just Quality Gate):

### Phase 5.10–6 (Current)
✅ Keep Quality Gate as-is (4 sub-agents, fully optimized)

### Phase 6 Extension (New)
Create 6 SDLC agent specs:
- `orchestration/agents/general-orchestrator-agent.md` (Haiku, low effort)
- `orchestration/agents/engineer-agent.md` (Haiku, high effort)
- `orchestration/agents/senior-engineer-agent.md` (Sonnet, high effort)
- `orchestration/agents/lead-engineer-agent.md` (Sonnet, high effort)
- `orchestration/agents/principal-engineer-agent.md` (Opus, high effort)
- `orchestration/agents/quality-engineer-agent.md` (Sonnet, medium effort)

Each would be **similar structure** to Security/Testing agents:
- Input: DELEGATE block with task scope, context, plan
- Process: Execute work (code, review, design, architecture)
- Output: HANDBACK block with deliverables, tokens, assessment

### Phase 7
- General Orchestrator routes incoming work to appropriate agent
- Model Engineer feedback loop optimizes model/effort recommendations
- Pattern Recognition detects "Engineer always needs code review after" → auto-delegate to Quality Engineer

---

## Re-Integration Plan: Option B (Quality Gate Only)

Keep current narrowed scope:

### Phase 5.10–7
✅ Keep Quality Gate + feedback loops (complete)

### Phase 8+
If/when general SDLC work needed, implement agents then.

**Rationale**: Quality Gate has immediate CI/CD value. General SDLC can come later.

---

## Recommendation: Hybrid Approach

**Keep**: Quality Gate (fully implemented, optimized, Phase 6 designed)

**Add**: Lightweight SDLC routing
- Create `general-orchestrator-agent.md` (Haiku, routes work)
- Keep existing agents (don't change them)
- Wire Orchestrator to delegate to existing agents where applicable
  - "Complex coding" → delegate to Senior Engineer (or use Model Engineer to recommend)
  - "Code review" → delegate to Testing Agent (partial) or escalate to Quality Engineer (future)

**Defer**: Individual SDLC agents (Engineer, Senior Engineer, Lead, Principal)
- Document specs (AGENT-SPECS-SDLC.md)
- Implement in Phase 7 if needed

---

## Cost Analysis: Full SDLC vs. Quality Gate Only

### Quality Gate Only (Current)
- Per commit: $0.278
- Per day (10–20 commits): $2.78–$5.56
- Per month: $83–$167
- Annual: ~$1,000–$2,000

### Full SDLC (If Added)
- Per quality gate: $0.278 (unchanged)
- Per engineering task (average): $0.15–$0.45
  - Simple implementation: $0.03 (Haiku)
  - Code review: $0.09 (Sonnet)
  - Architecture design: $0.15–$0.30 (Sonnet/Opus)
- Highly variable based on work type

---

## Decision Required: What Should agentic-engineers Be?

### Option 1: Quality Gate Focused (Current)
✅ **Scope**: Automated quality checks on every commit  
✅ **Implementation**: 6 agents, Phase 6 designed, ready for testing  
✅ **Cost**: $0.278/commit, fully optimized  
❌ **General SDLC work**: Not covered  
⏱️ **Timeline**: Phase 5.10 testing now, Phase 6–7 feedback loops

### Option 2: Full SDLC Orchestration
✅ **Scope**: Route ALL engineering work to optimal agents  
✅ **Framework**: AGENTS.md provides routing logic  
❌ **Implementation**: 8 agents, none implemented  
⏱️ **Timeline**: Phase 5.10 Quality Gate first, Phase 6+ add SDLC agents  
💰 **Cost**: Variable, depends on work type

### Option 3: Hybrid (Recommended)
✅ **Scope**: Quality Gate (complete) + lightweight SDLC routing  
✅ **Implementation**: Keep Quality Gate, add master Orchestrator  
✅ **Timeline**: Phase 5.10 Quality Gate, Phase 6 add Orchestrator  
📈 **Growth path**: Add individual SDLC agents as needed (Phase 7+)

---

## What User Intended (Re-reading Context)

From earlier messages:
> "Focus on agentic-engineers → AGENTS with SKILLS primarily... all loops and activity coordinated here in claude/copilot cli by sub-agents of varying $Token/Cost"

This suggests:
- **Primary goal**: agentic-engineers = home for ALL agent specs (Orchestrator, Engineer, Senior Engineer, etc.)
- **Phase 5.10**: Quality Gate (immediate, CI/CD integration)
- **Phase 6+**: SDLC routing, feedback loops, optimization

We've delivered Phase 5.10 but skipped documenting/designing the SDLC agents.

---

## Recommendation for Next Session

### Immediate (Today): Decision
- [ ] Confirm: Is agentic-engineers **Quality Gate only** or **full SDLC orchestration**?
- [ ] If full SDLC: Create AGENT-SPECS-SDLC.md with 6 missing agents
- [ ] If Quality Gate only: Document that explicitly in README

### Phase 6 (If Full SDLC chosen)
- Implement General Orchestrator (Haiku, low effort) — routes work
- Defer individual SDLC agents to Phase 7

### Phase 7+
- Implement SDLC agents as needed (Engineer, Senior Engineer, Lead, Principal, Quality Engineer)
- Wire feedback loops to optimize model/effort per agent

---

## Files Needed for Full SDLC Recovery

**New files** (if choosing Option 2 or 3):
1. `orchestration/agents/general-orchestrator-agent.md` — Master router
2. `orchestration/AGENT-SPECS-SDLC.md` — Specs for 6 SDLC agents
3. Update `TODO.md` — Add SDLC implementation timeline

**Existing files** (do not change):
- ✅ AGENTS.md (routing framework — keep as-is)
- ✅ AGENT-SPECS-WEEK1-DESIGNS.md (operational agents — keep as-is)
- ✅ agents/*.md (Quality Gate agents — keep as-is)
