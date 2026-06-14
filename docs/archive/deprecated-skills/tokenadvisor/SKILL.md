---
name: tokenadvisor
description: DEPRECATED — merged into usage-tracking as role-analysis sub-command (Wave 3, m3-skills-deprecation, 2026-06-14). Use usage-tracking/scripts/role_analysis.py instead.
license: Proprietary
compatibility: Designed for agentic-engineers framework
metadata:
  author: agentic-engineers
  version: "1.0"
  category: monitoring
  role: orchestrator
  model: haiku-4-5
  schedule: "0 17 * * *"
  status: DEPRECATED
  deprecated_by: usage-tracking
  deprecated_at: "2026-06-14"
  migration: "Use: src/skills/usage-tracking/scripts/role_analysis.py"
---

> **DEPRECATED**: Merged into `usage-tracking` as `scripts/role_analysis.py`.
> Use `usage-tracking` skill directly for role-based cost analysis.


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
0 17 * * * cd <project-root> && python agentic-engineers/skills/tokenadvisor/scripts/tokenadvisor.py --daily
```

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
