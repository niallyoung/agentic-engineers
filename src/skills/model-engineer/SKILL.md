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
  effort: high
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

## Configuration

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

## Self-Improvement

This skill participates in the framework's continuous improvement cycle
(see [skill-improvement-feedback](../skill-improvement-feedback/SKILL.md)).

When you use **model-engineer** during a task, include a skill_feedback entry
in your HANDBACK to help improve it over time:

```yaml
skill_feedback:
  - skill_name: model-engineer
    effectiveness_score: 0.85        # required: 0.0–1.0
    clarity_score: 0.90              # optional
    coverage_gaps:
      - "Specific scenario the skill did not address"
    improvement_suggestions:
      - "Concrete change that would have helped"
    usage_context: "One sentence on how you used this skill"
```

Positive feedback is as valuable as critical feedback. Three or more
feedback items for this skill automatically trigger an improvement task.
