# Orchestration — How Work Flows Through the System

**This directory defines how tasks flow through the agentic-engineers system.**

## Files

| File | Purpose |
|------|---------|
| **AGENTS.md** | 8-role model, routing rules, cost tiers, escalation paths. Reference for task routing. |
| **HANDOFF.md** | DELEGATE/HANDBACK protocol, markup examples, validation rules. Required for all agent-to-agent work transfers. |
| **QUALITY.md** | Tier 1/2/3 quality gate checklists. Verify before accepting HANDBACK. |
| **USAGE-BUDGET-MANAGER.md** | Real-time token usage monitoring skill. Tracks session/weekly budgets, recommends model tiers, alerts on limits. |
| **USAGE-BUDGET-INTEGRATION.md** | Integration guide for Orchestrator workflow. Budget-aware delegation, model reduction approval, break recommendations. |
| **TOKEN-USAGE-TRACKING.md** | Historical token usage capture and trend analysis. Automated snapshots, analytics, forecasting. |

## Workflow (High-Level)

```
User/Orchestrator
  ↓
Receive task
  ↓
AGENTS.md: Route to appropriate role
  ↓
HANDOFF.md: Create DELEGATE markup
  ↓
[Agent executes task]
  ↓
HANDOFF.md: Create HANDBACK markup
  ↓
Quality Engineer
  ↓
QUALITY.md: Verify against Tier gates
  ↓
Accept or reject
```

## Key Concepts

- **Routing:** Decision tree in AGENTS.md (complexity, scope, specialty → role)
- **Handoff Protocol:** Structured DELEGATE/HANDBACK blocks in HANDOFF.md
- **Quality Gates:** Tier 1 (lint/test), Tier 2 (coverage/docs), Tier 3 (arch/security)
- **Escalation:** Engineer → Senior → Lead → Principal → Security

## When You Need This

- **Receiving a task?** Check AGENTS.md routing rules
- **Sending work to another agent?** Use HANDOFF.md markup
- **Verifying quality?** Use QUALITY.md checklist
- **Deciding who should do this?** AGENTS.md decision tree
- **Checking token budget now?** Use USAGE-BUDGET-MANAGER.md for real-time status
- **Integrating budget awareness into delegation?** See USAGE-BUDGET-INTEGRATION.md
- **Analyzing usage over time?** Use TOKEN-USAGE-TRACKING.md (capture, analyze, forecast trends)
- **Forecasting when limits reset?** Token usage tracking script estimates based on consumption rate

## See Also

- `../MANIFEST.md` — Complete file listing of entire system (discovery tool)
- `../config/QUICK_REFERENCE.md` — 1-page routing cheat sheet
- `../config/MODEL_ASSIGNMENTS_LOCKED.md` — Models for each role
- `../guides/CLAUDE.md` — Integration with ERS platform
