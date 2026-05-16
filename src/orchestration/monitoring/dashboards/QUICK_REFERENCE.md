# Dashboard Quick Reference Card

**Dashboard**: Agentic Engineers — Orchestrator Overview  
**UID**: `agentic-engineers-orchestrator`  
**URL**: `/d/agentic-engineers-orchestrator`  
**Refresh**: 30 seconds  

---

## Panel Quick Reference

### KPI Cards (Row 0)
| Panel | Metric | Green | Yellow | Red |
|-------|--------|-------|--------|-----|
| 1 | Tasks Total | N/A | N/A | N/A |
| 2 | Success Rate | ≥95% | 90-95% | <90% |
| 3 | Error Rate | <1% | 1-5% | >5% |
| 4 | Queue Depth | 0-50 | 50-100 | >100 |
| 5 | Quality Score | ≥85 | 70-85 | <70 |

### Performance (Rows 4-20)
| Panel | Metric | Type | Key Insight |
|-------|--------|------|-------------|
| 6 | Task Throughput | Timeseries | Tasks/min trend |
| 7 | Task Duration | Timeseries | P50/P95/P99 latency |
| 8 | Token Usage | Timeseries | Tokens/5min rate |
| 9 | Queue Depth | Timeseries | Pending vs processing |
| 10 | Routing Latency | Timeseries | Routing decision time |
| 11 | Validation Errors | Timeseries | Error rate/sec |

### Token Metrics (Rows 28-36)
| Panel | Metric | Type | What to Watch |
|-------|--------|------|---------------|
| 12 | Token Throughput | Timeseries | Input/output/cached ratio |
| 13 | Token by Model | Pie Chart | Haiku/Sonnet/Opus distribution |
| 14 | Tokens per Task | Histogram | P25-P99 distribution |
| 15 | Cache Hit Rate | Gauge | Caching effectiveness (%) |

### Cost Metrics (Rows 44-60)
| Panel | Metric | Type | Thresholds |
|-------|--------|------|-----------|
| 16 | Daily Cost | Stat | 🟢<$100, 🟡$100-500, 🔴>$500 |
| 17 | Cost by Role | Pie Chart | Engineer/Senior/Lead/Principal |
| 18 | Cost by Model | Pie Chart | Haiku/Sonnet/Opus distribution |
| 19 | Cost per Task | Histogram | P25-P99 cost distribution |
| 20 | Cost Trend | Timeseries | 7-day cost trend |

---

## Metric Queries Cheat Sheet

### Token Metrics
```promql
# Input tokens per second
rate(orchestrator_tokens_input_total[1m])

# Output tokens per second
rate(orchestrator_tokens_output_total[1m])

# Cache hit percentage
(sum(orchestrator_tokens_cached_total) / sum(orchestrator_tokens_total)) * 100

# Tokens per task percentiles
histogram_quantile(0.95, rate(orchestrator_tokens_per_task_bucket[5m]))
```

### Cost Metrics
```promql
# Total daily cost
sum(orchestrator_cost_total)

# Cost by model
sum(orchestrator_cost_total) by (model)

# Cost by role
sum(orchestrator_cost_total) by (role)

# Cost per task percentiles
histogram_quantile(0.95, rate(orchestrator_cost_per_task_bucket[5m]))
```

---

## Troubleshooting Checklist

### Panel Shows "No Data"
- [ ] Prometheus is running
- [ ] Metrics are being exported
- [ ] Data source is configured
- [ ] Query syntax is correct

### Incorrect Values
- [ ] Pricing table is current
- [ ] Token counts are accurate
- [ ] Labels are correct
- [ ] Time range is appropriate

### Performance Issues
- [ ] Check Panel 2 (Success Rate)
- [ ] Check Panel 3 (Error Rate)
- [ ] Check Panel 11 (Validation Errors)
- [ ] Check Panel 4 (Queue Depth)

### High Costs
- [ ] Check Panel 18 (Cost by Model)
- [ ] Check Panel 17 (Cost by Role)
- [ ] Check Panel 14 (Tokens per Task)
- [ ] Check Panel 15 (Cache Hit Rate)

---

## Common Workflows

### Daily Review (5 min)
1. Panel 16 (Daily Cost) — Within budget?
2. Panel 20 (Cost Trend) — Increasing?
3. Panel 2 (Success Rate) — Above 95%?
4. Panel 4 (Queue Depth) — Normal?

### Weekly Analysis (15 min)
1. Panel 20 (Cost Trend) — Weekly pattern?
2. Panel 18 (Cost by Model) — Distribution optimal?
3. Panel 15 (Cache Hit Rate) — Above 40%?
4. Panel 14 (Tokens per Task) — Outliers?

### Monthly Optimization (30 min)
1. Panel 20 (Cost Trend) — Monthly total?
2. Panel 18 (Cost by Model) — Which models expensive?
3. Panel 17 (Cost by Role) — Which roles expensive?
4. Panel 14 (Tokens per Task) — Optimization opportunities?
5. Panel 15 (Cache Hit Rate) — Caching improvements?

---

## Threshold Reference

### Success Metrics
```
Task Success Rate:
  🟢 Green: ≥95%
  🟡 Yellow: 90-95%
  🔴 Red: <90%

Error Rate:
  🟢 Green: <1%
  🟡 Yellow: 1-5%
  🔴 Red: >5%

Quality Score:
  🟢 Green: ≥85
  🟡 Yellow: 70-85
  🔴 Red: <70
```

### Cost Metrics
```
Daily Cost:
  🟢 Green: $0-100
  🟡 Yellow: $100-500
  🔴 Red: >$500

Cache Hit Rate:
  🟢 Green: ≥40%
  🟡 Yellow: 20-40%
  🔴 Red: <20%

Queue Depth:
  🟢 Green: 0-50
  🟡 Yellow: 50-100
  🔴 Red: >100
```

---

## Model Pricing (May 2026)

| Model | Input | Output | Use Case |
|-------|-------|--------|----------|
| Haiku | $0.80/1M | $4.00/1M | Simple tasks, cost optimization |
| Sonnet | $3.00/1M | $15.00/1M | Balanced, general purpose |
| Opus | $15.00/1M | $75.00/1M | Complex, high-capability |

---

## Time Range Shortcuts

| Range | Use Case |
|-------|----------|
| Last 1h | Real-time monitoring |
| Last 6h | Trend analysis |
| Last 24h | Daily review |
| Last 7d | Weekly analysis |
| Custom | Specific period |

---

## Alert Rules (Recommended)

```promql
# High error rate
(rate(orchestrator_errors_total[5m]) / rate(orchestrator_tasks_total[5m])) > 0.05

# Queue backlog
orchestrator_queue_depth > 100

# High daily cost
sum(orchestrator_cost_total) > 500

# Low cache hit rate
(sum(orchestrator_tokens_cached_total) / sum(orchestrator_tokens_total)) < 0.2

# High task latency
histogram_quantile(0.95, rate(orchestrator_task_duration_seconds_bucket[5m])) > 60
```

---

## Dashboard Controls

| Control | Location | Purpose |
|---------|----------|---------|
| Time Range | Top right | Change time window |
| Refresh | Top right | Manual refresh |
| Settings | Gear icon | Dashboard settings |
| Export | Share menu | Export data |
| Share | Top right | Share with team |

---

## Documentation Map

```
README.md ← Start here for overview
  ├─ DASHBOARD_UPDATES.md (what changed)
  ├─ METRICS_IMPLEMENTATION.md (how to implement)
  ├─ USAGE_GUIDE.md (how to use)
  ├─ VISUAL_EXAMPLES.md (what it looks like)
  ├─ COMPLETION_REPORT.md (project summary)
  └─ QUICK_REFERENCE.md (this file)
```

---

## Key Metrics at a Glance

### Token Consumption
- **Input**: Prompt complexity
- **Output**: Response length
- **Cached**: Prompt reuse effectiveness
- **Per Task**: Task complexity distribution

### Cost Analysis
- **Daily**: Budget tracking
- **By Model**: Model cost distribution
- **By Role**: Team cost allocation
- **Per Task**: Task cost distribution
- **Trend**: Spending trajectory

### Performance
- **Success Rate**: Task completion rate
- **Error Rate**: Failure percentage
- **Quality Score**: Output quality
- **Queue Depth**: Backlog size
- **Latency**: Response time

---

## Quick Wins (Cost Optimization)

1. **Increase Haiku routing** (if <20%)
   - Cost: $0.80/$4.00 per 1M tokens
   - Use for: Simple tasks

2. **Improve cache hit rate** (if <40%)
   - Reuse prompts
   - Enable prompt caching
   - Optimize prompt templates

3. **Reduce Opus usage** (if >40%)
   - Use Sonnet for medium tasks
   - Reserve Opus for complex work

4. **Optimize prompts**
   - Reduce token count
   - Use fewer examples
   - Simplify instructions

---

**Last Updated**: May 17, 2026  
**Version**: 2.0  
**Status**: Production Ready ✅

Print this page and keep at your desk for quick reference!
