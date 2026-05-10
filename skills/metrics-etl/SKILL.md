---
name: metrics-etl
description: Data pipeline that aggregates daily metrics to Prometheus format for Grafana dashboards. Use for continuous metrics collection and visualization across all automation agents.
license: Proprietary
compatibility: Designed for agentic-engineers framework (ERS platform)
metadata:
  author: agentic-engineers
  version: "1.0"
  category: monitoring
  role: orchestrator
  schedule: "0 * * * *"
---

## Overview

Metrics ETL aggregates metrics from daily logs and transforms them to Prometheus format for Grafana visualization. Silent background job (no voice notifications).

**What it does:**
1. Aggregates metrics from daily logs
2. Transforms to Prometheus format
3. Exports for dashboard visualization
4. Maintains time-series data for trends
5. Compresses old data (30-day retention)

## Invocation

### Manual Run
```bash
python scripts/metrics-etl.py --aggregate --days 7
python scripts/metrics-etl.py --export prometheus --output metrics.txt
python scripts/metrics-etl.py --export json --output metrics.json
```

### Automated (Cron)
Hourly (every hour on the hour) via `orchestration/config/metrics-etl.cron`

```bash
0 * * * * cd ~/git/ers/{workspace-name} && python agentic-engineers/skills/metrics-etl/scripts/metrics-etl.py --aggregate --days 7
```

## Voice Notifications

**None** — Silent background job, no voice alerts.

## Configuration

- **Metrics source:** `agentic-engineers/data/metrics/`
- **Prometheus output:** `agentic-engineers/data/prometheus/metrics.txt`
- **JSON output:** `agentic-engineers/data/metrics-daily.json`
- **Retention:** 30 days (auto-cleanup)

## Integration

**Input:** Daily task metrics  
**Output:** Prometheus format for Grafana scraping  
**Dashboards:** Token Burn, Model Performance, Quality Gates, Cost Optimization, A/B Testing

## Scripts

- `metrics-etl.py` — Main ETL pipeline (pure data transformation, no AI model)
