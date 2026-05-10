---
name: ab-testing
description: Experiment orchestration framework with traffic allocation, statistical analysis, and early stopping detection. Use to test routing changes, model upgrades, and role assignments with Welch's t-test significance testing.
license: Proprietary
compatibility: Designed for agentic-engineers framework (ERS platform)
metadata:
  author: agentic-engineers
  version: "1.0"
  category: optimization
  role: lead-engineer
  schedule: "0 18 * * *"
---

## Overview

A/B Testing Monitor conducts controlled experiments on task routing, model allocation, and role assignments with statistical rigor.

**What it does:**
1. Creates experiments from proposals
2. Allocates traffic (50/50 control/variant)
3. Monitors results (daily statistical checks)
4. Analyzes significance (Welch's t-test, p < 0.05)
5. Determines winners (cost + quality)
6. Early stops (if clear winner or regression)

## Invocation

### Manual Run
```bash
python scripts/ab-testing.py --create --name "Test name" --hypothesis "..."
python scripts/ab-testing.py --start EXPERIMENT_ID
python scripts/ab-testing.py --analyze EXPERIMENT_ID
python scripts/ab-testing.py --stop EXPERIMENT_ID
```

### Automated (Cron)
Daily at 18:00 UTC (for early stopping checks) via `orchestration/config/ab-testing-monitor.cron`

```bash
0 18 * * * cd ~/git/ers/{workspace-name} && python agentic-engineers/skills/ab-testing/scripts/ab-testing.py --monitor
```

## Voice Notifications

Status phrases (via voice-notify skill):
- `"A/B test in progress. Quality stable, cost down 5%."` — Ongoing
- `"Significant result. Variant winning, p=0.03."` — Threshold met
- `"Early stop: regression detected."` — Control better
- `"Complete: variant wins."` — Experiment concluded

## Configuration

- **Experiments stored:** `agentic-engineers/data/experiments/`
- **Min sample size:** 100 tasks per group
- **Significance threshold:** p < 0.05 (95% confidence)
- **Default duration:** 7 days
- **Traffic split:** 50/50 control/variant

## Integration

**Input:** Model Engineer proposals + metrics  
**Output:** Experiment results and winner determination  
**Dashboard:** A/B Testing (Grafana)

Winner implementation requires manual approval and deployment.

## Scripts

- `ab-testing.py` — Main orchestration engine
