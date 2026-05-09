# Agentic Engineers — Quick Reference

## One-Page Architecture

```
                          ┌─────────────────────┐
                          │  WORK ARRIVES       │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │ GENERAL ORCHESTRATOR│
                          │  (Task Router)      │
                          └──────────┬──────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          │                          │                          │
    ┌─────▼─────┐         ┌──────────▼────────┐         ┌──────▼───────┐
    │ SECURITY  │         │     COMPLEX       │         │ SIMPLE SCOPED│
    │           │         │  WITH NO PLAN     │         │  WITH PLAN   │
    │ Security  │         │                   │         │              │
    │ Engineer  │         │ Senior Engineer   │         │ Engineer     │
    │ (Opus)    │         │ (Sonnet)          │         │ (Haiku)      │
    └─────┬─────┘         └──────────┬────────┘         └──────┬───────┘
          │                          │                         │
          │                    (plan created)                   │
          │                          │                         │
          └──────────────────────────┼─────────────────────────┘
                                     │ (work complete)
                          ┌──────────▼──────────┐
                          │ QUALITY ORCHESTRATOR│
                          │  (Quality Master)   │
                          └──────────┬──────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           │                         │                         │ (parallel)
        ┌──▼──┐     ┌────────┐  ┌────▼───┐    ┌───────────┐   │
        │TEST │     │ HEAL   │  │SECURITY│    │ METRICS   │   │
        └──┬──┘     └────┬───┘  └────┬───┘    └─────┬─────┘   │
           │             │           │              │         │
           └─────────────┼───────────┼──────────────┘         │
                         │           │ (results aggregate)    │
                         └─────┬─────┘                        │
                               │                             │
                    ┌──────────▼──────────┐                   │
                    │  DECISION ENGINE    │                   │
                    │                     │                   │
                    │ IF all pass &       │                   │
                    │ health >= 85:       │                   │
                    │  → PROCEED ✓        │                   │
                    │ ELSE:               │                   │
                    │  → ESCALATE ⚠       │                   │
                    └─────────────────────┘                   │
```

## Agent Responsibilities

| Agent | Role | Model | Input | Output |
|-------|------|-------|-------|--------|
| **General Orchestrator** | Route all tasks | Haiku | Task description | Agent assignment + confidence |
| **Security Engineer** | Threat modeling | Opus | Service architecture | Threat model + risk scores |
| **Principal Engineer** | Cross-service design | Opus | Architecture question | 2-3 design options + trade-offs |
| **Senior Engineer** | Analysis & planning | Sonnet | Complex unscoped work | Root cause analysis + detailed plan |
| **Engineer** | Execution | Haiku | Plan + scope | Code + tests + metrics |
| **Quality Engineer** | Post-execution validation | Sonnet | Completed work | Approval/rework/escalate decision |
| **Lead Engineer** | Code review | Sonnet | Implemented code | Style feedback + merge recommendation |
| **Quality Orchestrator** | Quality gate | Sonnet | Completed work | PROCEED/ESCALATE + audit trail |
| **Testing Agent** | Test execution | Haiku | Code + tests | Pass/fail + coverage |
| **Healing Agent** | Auto-fixes | Sonnet | Test failures | Fixes applied + status |
| **Security Agent** | Vulnerability scan | Opus | Code | Findings + severity |
| **Metrics Agent** | Health scoring | Haiku | System state | Health score + latency/error |

## DELEGATE → HANDBACK Flow

```
┌────────────────────────────────┐
│ Orchestrator sends DELEGATE    │
│ (task_id, scope, context)      │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ Agent processes DELEGATE       │
│ (analysis or execution)        │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ Agent returns HANDBACK         │
│ (results, metrics, confidence) │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ Orchestrator aggregates        │
│ (multi-agent results)          │
└────────────┬───────────────────┘
             │
             ▼
┌────────────────────────────────┐
│ Final decision made            │
│ (PROCEED or ESCALATE)          │
└────────────────────────────────┘
```

## Decision Trees

### General Orchestrator (Entry Point)

```
Is task security-focused?
  YES → Security Engineer (Opus) [confidence: 0.95]
  NO  ↓

Does task need cross-service architecture?
  YES → Principal Engineer (Opus) [confidence: 0.90]
  NO  ↓

Is this a code review?
  YES → Lead Engineer (Sonnet) [confidence: 0.92]
  NO  ↓

Is this complex work with NO plan?
  YES → Senior Engineer (Sonnet) [confidence: 0.88]
  NO  ↓

Is this simple/medium work WITH plan?
  YES → Engineer (Haiku) [confidence: 0.93]
  NO  ↓

Unknown/default:
  → Engineer (Haiku) [confidence: 0.70]
  (escalate if insufficient)
```

### Quality Orchestrator (Aggregation)

```
Testing Agent: PASS? ✓
Healing Agent: PASS? ✓
Security Agent: PASS? ✓
Metrics Agent: health >= 85? ✓

IF all pass:
  → PROCEED ✓ [confidence: 0.95]

IF any fail:
  → ESCALATE ⚠ [reason: failures]
```

## Example: Feature Implementation Timeline

```
10:00 ─ Work arrives
10:05 ─ General Orchestrator routes to Senior Engineer
10:10 ─ Senior Engineer analyzes (4 hours of analysis)
14:10 ─ Senior Engineer returns plan + confidence 0.95
14:15 ─ General Orchestrator routes to Engineer with plan
14:20 ─ Engineer executes (4.5 hours of coding)
18:50 ─ Engineer returns HANDBACK (code + tests + metrics)
18:55 ─ Quality Orchestrator spawns 4 parallel agents
        • Testing Agent: run tests → 2 min
        • Healing Agent: check fixes → 1 min
        • Security Agent: scan → 3 min
        • Metrics Agent: health score → 1 min
19:07 ─ All 4 agents return results
19:08 ─ Quality Orchestrator aggregates: PROCEED ✓
19:10 ─ (Optional) Lead Engineer code review: APPROVE ✓
19:15 ─ Merge to main
19:20 ─ CI/CD deploys to dev/prod

Total: 9 hours 20 minutes
Tokens: ~4,800
Quality: 92/100
Success rate: 100%
```

## Communication Patterns

### Success Path
```
Engineer → Quality Orchestrator → [4 agents in parallel] → Aggregate → PROCEED
```

### Rework Path
```
Engineer → Quality Orchestrator → [4 agents] → Testing fails → ESCALATE
           ↓
       [feedback to engineer]
       [engineer fixes, resubmits]
       ↓
     → Quality Orchestrator → [4 agents] → All pass → PROCEED
```

### Escalation Path
```
Engineer → Quality Orchestrator → Security Agent finds vulnerability → ESCALATE
                                   ↓
                              Security Engineer
                              (threat model + fix)
                                   ↓
                              Engineer (implement fix)
                                   ↓
                              Quality Orchestrator → PROCEED
```

## Key Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| **Quality Score** | >85/100 | 92/100 |
| **Test Coverage** | >80% | 87% |
| **Security Issues** | 0 | 0 |
| **Health Score** | ≥85/100 | 92/100 |
| **Escalation Rate** | <5% | 3.2% |
| **Confidence** | >0.90 | 0.95 |
| **Plan Accuracy** | >95% | 98% |
| **Token Efficiency** | <budget | 95% of budget |

---

**For detailed workflow with example flows and DELEGATE/HANDBACK message formats, see: [WORKFLOW.md](WORKFLOW.md)**
