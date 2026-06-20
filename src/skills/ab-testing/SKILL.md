---
name: ab-testing
description: Experiment orchestration framework with traffic allocation, statistical analysis, and early stopping detection. Use to test routing changes, model upgrades, and role assignments with Welch's t-test significance testing.
license: Proprietary
compatibility: Designed for agentic-engineers framework
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
0 18 * * * cd <project-root> && python agentic-engineers/skills/ab-testing/scripts/ab-testing.py --monitor
```

## Configuration

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

## Self-Improvement

This skill participates in the framework's continuous improvement cycle
(see [skill-improvement-feedback](../skill-improvement-feedback/SKILL.md)).

When you use **ab-testing** during a task, include a skill_feedback entry
in your HANDBACK to help improve it over time:

```yaml
skill_feedback:
  - skill_name: ab-testing
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
