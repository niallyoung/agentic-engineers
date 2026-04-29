---
name: Agent Setup Summary (Current State)
description: All agents sorted by model, effort, and cost - with gap analysis
type: reference
date: 2026-04-28
---

# Current Agent Setup: Model, Effort, Cost

## All Agents Sorted by Model (Ascending Cost)

### HAIKU ($0.80/$2.40 per 1M input/output tokens)

| Agent | Role | Effort | Cost/Task | Status | File | Purpose |
|-------|------|--------|-----------|--------|------|---------|
| **Testing Agent** | Engineer | medium | $0.034 | ✅ Done | `testing-agent.md` | Parse test output, count tests, coverage % |
| **Metrics Agent** | Orchestrator | low | $0.028 | ✅ Done | `metrics-agent.md` | Health scoring (0-100), anomaly detect |
| **Model Engineer Agent** | Model Engineer | medium | $0.009 | ✅ Done | `model-engineer-agent.md` | Token efficiency analysis, confidence scoring |
| **General Orchestrator** | Orchestrator (SDLC) | low | $0.03 | ❌ Missing | — | Route all work to appropriate agent |
| **Engineer** | Engineer (SDLC) | high | $0.03 | ❌ Missing | — | Well-scoped implementation |

**Haiku Subtotal**: 3 implemented, 2 missing

---

### SONNET ($3.00/$15.00 per 1M input/output tokens)

| Agent | Role | Effort | Cost/Task | Status | File | Purpose |
|-------|------|--------|-----------|--------|------|---------|
| **Quality Gate Orchestrator** | Orchestrator (QG) | high | $0.026 | ✅ Done | `quality-gate-orchestrator-agent.md` | Master QG coordinator, delegates to 4 sub-agents |
| **Healing Agent** | Senior Engineer | high | $0.096 | ✅ Done | `healing-agent.md` | Auto-fix lint, config, test issues |
| **Senior Engineer** | Senior Engineer (SDLC) | high | $0.09 | ❌ Missing | — | Complex coding without pre-written plan |
| **Lead Engineer** | Lead Engineer (SDLC) | high | $0.09 | ❌ Missing | — | Code review, architecture guidance |
| **Quality Engineer** | Quality Engineer (SDLC) | medium | $0.09 | ❌ Missing | — | Post-implementation validation |

**Sonnet Subtotal**: 2 implemented, 3 missing

---

### OPUS ($15.00/$45.00 per 1M input/output tokens)

| Agent | Role | Effort | Cost/Task | Status | File | Purpose |
|-------|------|--------|-----------|--------|------|---------|
| **Security Agent** | Security Engineer | max | $0.085 | ✅ Done | `security-agent.md` | Credential scanning, permission analysis |
| **Principal Engineer** | Principal Engineer (SDLC) | high | $0.15 | ❌ Missing | — | Cross-service architecture design |

**Opus Subtotal**: 1 implemented, 1 missing

---

## Summary by Status

### ✅ IMPLEMENTED (6 Agents)

```
Total Cost (combined): $0.278/commit (Quality Gate) + async Model Engineer loop

By Model:
  Haiku (3):        Testing, Metrics, Model Engineer
  Sonnet (2):       Quality Gate Orchestrator, Healing Agent
  Opus (1):         Security Agent

By Role:
  Orchestrator:     Quality Gate Orchestrator (Sonnet)
  Engineer:         Testing Agent (Haiku), Healing Agent (Sonnet)
  Security:         Security Agent (Opus)
  Feedback:         Model Engineer Agent (Haiku)
  Metrics:          Metrics Agent (Haiku)
```

**All 6 are Quality Gate sub-agents or feedback loop agents.**

---

### ❌ MISSING (6+ Agents)

```
Total if implemented (estimated): $0.60–$1.00/task

SDLC Routing (required for general work):
  Haiku (2):        General Orchestrator (low), Engineer (high)
  Sonnet (3):       Senior Engineer, Lead Engineer, Quality Engineer
  Opus (1):         Principal Engineer

Supporting (optional):
  Plus any operational agents (CICD Monitor, Cleanup, Voice Notify from Week 1)
```

**All missing are SDLC agents (general engineering work, not Quality Gate).**

---

## Gap Analysis: What's Missing

### Category 1: Master Orchestrator (SDLC)
**Missing**: General Orchestrator (Haiku, low effort, ~$0.03)
- **Purpose**: Routes ALL engineering work to appropriate agent
- **Currently**: Only have Quality Gate Orchestrator (quality checks specific)
- **Impact**: Can't route general SDLC work to right agent
- **Priority**: HIGH (foundational)

### Category 2: Implementation Agents
**Missing**: 
- Engineer (Haiku, high effort, ~$0.03)
- Senior Engineer (Sonnet, high effort, ~$0.09)

**Currently**: Have Healing Agent (auto-fixes), but not general implementation
**Impact**: Can't execute well-scoped or complex coding tasks autonomously
**Priority**: MEDIUM (can use human engineers in interim)

### Category 3: Review & Validation Agents
**Missing**:
- Quality Engineer (Sonnet, medium effort, ~$0.09)
- Lead Engineer (Sonnet, high effort, ~$0.09)

**Currently**: Have Testing Agent (test output parsing), but not full code review
**Impact**: Can't do post-implementation review without human
**Priority**: MEDIUM (can use human reviewers in interim)

### Category 4: Architecture Agent
**Missing**: Principal Engineer (Opus, high effort, ~$0.15)

**Currently**: None
**Impact**: Can't make cross-service architecture decisions autonomously
**Priority**: LOW (can escalate to humans)

---

## Cost Breakdown (If All Agents Implemented)

### Quality Gate Operations (Per Commit)
```
Security Agent (Opus):          $0.085
Testing Agent (Haiku):          $0.034
Metrics Agent (Haiku):          $0.028
Healing Agent (Sonnet):         $0.096
Quality Gate Orchestrator:      $0.026
Model Engineer (async):         $0.009
─────────────────────────────────────
Total per commit:               $0.278
```

### SDLC Operations (Per Task, Varies by Complexity)

#### Simple Task (Well-scoped implementation)
```
General Orchestrator:           $0.03
Engineer (Haiku):               $0.03
Quality Engineer (review):      $0.09
─────────────────────────────────────
Total:                          $0.15
```

#### Complex Task (Architecture-level)
```
General Orchestrator:           $0.03
Senior Engineer (Sonnet):       $0.09
Lead Engineer (review):         $0.09
Principal Engineer (arch):      $0.15
─────────────────────────────────────
Total:                          $0.36
```

---

## Current Capability Matrix

| Capability | Current | Missing | Workaround |
|------------|---------|---------|-----------|
| **Commit-level QC** | ✅ Full | — | Auto on every commit |
| **Security audit** | ✅ Full (Opus) | — | Embedded in QG |
| **Test execution** | ✅ Full (Haiku) | — | Embedded in QG |
| **Auto-fix lint/config** | ✅ Full (Sonnet) | — | Healing Agent |
| **Cost optimization** | ✅ Full (Model Engineer) | — | Feedback loop |
| **General implementation** | ❌ None | Engineer + Senior Engineer | Manual (human) |
| **Code review** | ⚠️ Partial | Quality Engineer + Lead Engineer | Manual (human) |
| **Architecture decisions** | ❌ None | Principal Engineer | Manual (human) |
| **SDLC routing** | ❌ None | General Orchestrator | Manual (human) |

---

## Recommendation: What to Build Next

### Option A: Complete Quality Gate (Current Plan)
- ✅ Phase 5.10: Quality Gate testing
- ✅ Phase 6: Feedback loops
- ✅ Phase 7: Pattern recognition, optimization
- ❌ SDLC agents deferred indefinitely

**Best for**: Team using agentic-engineers as CI/CD quality gate only

---

### Option B: Add SDLC Routing (Recommended)
- ✅ Phase 5.10: Quality Gate testing
- ✅ Phase 6: Feedback loops + General Orchestrator (Haiku)
- ✅ Phase 7: SDLC agent implementations (Engineer, Senior Engineer, Quality Engineer)
- ⏳ Phase 8: Principal Engineer (architecture)

**Best for**: Team using agentic-engineers for full SDLC orchestration

---

### Option C: Minimal SDLC (Hybrid)
- ✅ Phase 5.10: Quality Gate testing
- ✅ Phase 6: Feedback loops + General Orchestrator (Haiku)
- ❌ SDLC agent implementations deferred

**Best for**: Team wanting routing framework now, agents later

---

## Implementation Checklist (If Adding SDLC)

### Phase 6 (1 week)
- [ ] Create `orchestration/agents/general-orchestrator-agent.md`
  - Input: Work scope, context, effort estimate
  - Routing logic: IF security → Security Engineer, ELIF complex → Senior Engineer, ELSE → Engineer
  - Output: HANDBACK with agent assignment + confidence
- [ ] Wire General Orchestrator to Quality Gate Orchestrator
  - After QG completes → suggest improvement workflow
- [ ] Update `AGENTS.md` with actual agent files (not just routing rules)

### Phase 7 (2 weeks)
- [ ] Implement Engineer agent (Haiku)
- [ ] Implement Senior Engineer agent (Sonnet)
- [ ] Implement Quality Engineer agent (Sonnet)
- [ ] Wire Model Engineer feedback to SDLC agents

### Phase 8 (optional)
- [ ] Implement Lead Engineer agent (Sonnet)
- [ ] Implement Principal Engineer agent (Opus)

---

## Decision Point: Cost vs. Scope

| Scenario | Cost | Scope | Agents | Timeline |
|----------|------|-------|--------|----------|
| **QG Only** | $0.278/commit | Quality gates | 6 | Phase 5–6 done |
| **QG + Routing** | $0.278/commit + $0.15–0.36/task | QG + SDLC | 7 | Phase 6–7 |
| **Full SDLC** | $0.278/commit + $0.15–0.45/task | QG + full routing | 12+ | Phase 6–8 |

**Recommendation**: Go with Option B (Routing) if you want agentic-engineers to be "full SDLC" as originally envisioned.

All agents are self-contained. No conflicts. No breaking changes to Quality Gate. Just additive.
