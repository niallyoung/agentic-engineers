---
name: metrics-etl
description: DEPRECATED — This skill is no longer maintained. Prometheus and Grafana infrastructure was never implemented. Use local JSON metrics analysis instead.
license: Proprietary
compatibility: Designed for agentic-engineers framework
metadata:
  author: agentic-engineers
  version: "1.0"
  category: monitoring
  role: orchestrator
  status: deprecated
  schedule: "0 * * * *"
---

## DEPRECATED

This skill is no longer maintained. External infrastructure (Prometheus + Grafana) described here was never built and has been removed.

**Use instead:**
- Local JSON metrics in `~/.claude/metrics/`
- Direct analysis via scripts in `operations/`

## Deprecation Notice

**This skill is no longer maintained.**

The infrastructure it was designed to support (Prometheus + Grafana dashboards) was never implemented. 

For metrics analysis, use:
- Local JSON files in `~/.claude/metrics/`
- Direct Python analysis scripts
- Manual reporting via scripts in `operations/`

## Scripts

- `metrics-etl.py` — Main ETL pipeline (pure data transformation, no AI model)

## Self-Improvement

This skill participates in the framework's continuous improvement cycle
(see [skill-improvement-feedback](../skill-improvement-feedback/SKILL.md)).

When you use **metrics-etl** during a task, include a skill_feedback entry
in your HANDBACK to help improve it over time:

```yaml
skill_feedback:
  - skill_name: metrics-etl
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
