---
name: tokenadvisor
description: Daily metrics analysis agent that aggregates metrics by role, identifies cost inefficiencies, flags outliers, and recommends optimizations. Use for continuous monitoring of token spend, cost distribution, and role-based performance.
license: Proprietary
compatibility: Designed for agentic-engineers framework (ERS platform)
metadata:
  author: agentic-engineers
  version: "1.0"
  category: monitoring
  role: orchestrator
  model: haiku-4-5
  schedule: "0 17 * * *"
---

## Overview

TokenAdvisor analyzes daily metrics across all AI agents and roles to identify inefficiencies, cost overages, and performance issues.

**What it does:**
1. Aggregates metrics from past 7 days
2. Analyzes by role (Orchestrator, Engineer, Senior, Lead, Principal)
3. Identifies cost inefficiencies and escalation spikes
4. Flags outliers (tasks in 90th percentile by token usage)
5. Recommends adjustments (routing changes, role rebalancing)
6. Emits voice notification with status summary

## Invocation

### Manual Run
```bash
python scripts/tokenadvisor.py --daily
python scripts/tokenadvisor.py --daily --date 2026-04-24
```

### Automated (Cron)
Daily at 17:00 UTC via `orchestration/config/tokenadvisor.cron`

```bash
0 17 * * * cd ~/git/ers/{workspace-name} && python agentic-engineers/skills/tokenadvisor/scripts/tokenadvisor.py --daily
```

## Voice Notifications

Status phrases (via voice-notify skill):
- `"TokenAdvisor complete. Distribution healthy."` — All roles within budget
- `"Engineer over budget by 3%."` — Specific role exceeds threshold
- `"Escalation spike detected."` — Unusual re-routing rates

## Configuration

- **Metrics input:** `agentic-engineers/data/metrics/YYYY-MM-DD/`
- **Cost targets:** `agentic-engineers/config/MODEL_ASSIGNMENTS_LOCKED.md`
- **Output:** `agentic-engineers/data/logs/tokenadvisor-YYYY-MM-DD.log`

## Integration

**Feeds to:** Model Engineer (15 min later)  
**Dashboard:** Token Burn (Grafana)

Recommendations from TokenAdvisor become input for Model Engineer, which proposes A/B tests and routing changes.

## Scripts

- `tokenadvisor.py` — Main analysis agent (Haiku 4.5)
- `daily-email-summary.sh` — Optional 24h activity report
