---
name: model-engineer
description: Cost-quality optimization agent that analyzes tradeoffs, scores routing candidates, and proposes A/B tests. Use to generate task routing recommendations and experiment designs based on TokenAdvisor findings.
license: Proprietary
compatibility: Designed for agentic-engineers framework
metadata:
  author: agentic-engineers
  version: "1.0"
  category: optimization
  role: senior-engineer
  model: sonnet-4-6
  schedule: "0 17 * * *"
---

## Overview

Model Engineer analyzes TokenAdvisor findings and generates cost-quality optimizations, including task routing recommendations and A/B test proposals.

**What it does:**
1. Analyzes cost-quality tradeoffs by role and model
2. Scores task routing candidates (Engineer, Senior, Lead, Principal)
3. Generates feedback to TokenAdvisor findings
4. Proposes A/B test designs with hypotheses
5. Calculates efficiency (cost per quality point)
6. Recommends model upgrades and role shifts

## Invocation

### Manual Run
```bash
python scripts/model-engineer.py --analyze
python scripts/model-engineer.py --recommend --complexity medium
python scripts/model-engineer.py --feedback
```

### Automated (Cron)
Daily at 17:15 UTC (15 min after TokenAdvisor) via `orchestration/config/model-engineer.cron`

```bash
0 17 * * * sleep 900 && cd <project-root> && python agentic-engineers/skills/model-engineer/scripts/model-engineer.py --analyze
```

## Voice Notifications

Status phrases (via voice-notify skill):
- `"Model Engineer ready. Route low-complexity to Engineer."` — Routing change
- `"Test variant: Reduce Senior by 10%."` — A/B test proposal
- `"Upgrade to Sonnet on high-complexity."` — Model upgrade
- `"Consider Principal for refactors."` — Role recommendation

## Configuration

- **Cost target:** $0.0016 per quality point
- **Models:** Haiku 4.5, Sonnet 4.6, Opus 4.8
- **Roles:** Engineer, Senior, Lead, Principal
- **Input:** TokenAdvisor output + `agentic-engineers/data/metrics/`
- **Output:** `agentic-engineers/data/logs/model-engineer-YYYY-MM-DD.log`

## Integration

**Input:** TokenAdvisor recommendations + historical metrics  
**Output:** Feeds to A/B Testing Framework (test proposals)  
**Dashboard:** Model Performance (Grafana)

## Scripts

- `model-engineer.py` — Main optimization agent (Sonnet 4.6)
