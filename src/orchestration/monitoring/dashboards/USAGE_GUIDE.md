# Grafana Dashboard Usage Guide

**Dashboard**: Agentic Engineers — Orchestrator Overview  
**UID**: `agentic-engineers-orchestrator`  
**Version**: 2.0  
**Updated**: May 17, 2026

---

## Quick Start

### Accessing the Dashboard

1. Open Grafana: `http://localhost:3000` (or your Grafana URL)
2. Navigate to **Dashboards** → **Agentic Engineers — Orchestrator Overview**
3. Or use direct URL: `/d/agentic-engineers-orchestrator`

### Dashboard Overview

The dashboard is organized into 5 sections:

1. **KPI Cards** (Row 0) — High-level metrics at a glance
2. **Performance Metrics** (Rows 4-12) — Throughput, latency, queue depth
3. **Token Metrics** (Rows 28-36) — Token consumption and caching
4. **Cost Metrics** (Rows 44-60) — Cost analysis and trends

---

## Section 1: KPI Cards (Row 0)

Quick overview of system health and status.

### Panel 1: Tasks Total
- **Shows**: Total number of tasks processed
- **Color**: Blue (background)
- **What to watch**: Should increase over time
- **Action**: No action needed; informational

### Panel 2: Task Success Rate
- **Shows**: Percentage of tasks completed successfully
- **Thresholds**:
  - 🟢 Green: ≥95% (excellent)
  - 🟡 Yellow: 90-95% (good, watch)
  - 🔴 Red: <90% (investigate)
- **Action if red**: Check "Validation Errors" panel for failure causes

### Panel 3: Error Rate
- **Shows**: Percentage of tasks that failed
- **Thresholds**:
  - 🟢 Green: <1% (excellent)
  - 🟡 Yellow: 1-5% (acceptable)
  - 🔴 Red: >5% (investigate)
- **Action if red**: Review error logs, check "Validation Errors" panel

### Panel 4: Queue Depth
- **Shows**: Number of pending tasks in queue
- **Thresholds**:
  - 🟢 Green: 0-50 (healthy)
  - 🟡 Yellow: 50-100 (backlog building)
  - 🔴 Red: >100 (severe backlog)
- **Action if yellow/red**: Scale up orchestrator or reduce incoming load

### Panel 5: Average Quality Score
- **Shows**: Average quality score of completed tasks (0-100)
- **Thresholds**:
  - 🟢 Green: ≥85 (excellent)
  - 🟡 Yellow: 70-85 (acceptable)
  - 🔴 Red: <70 (investigate)
- **Action if red**: Review task quality in metrics, check for model issues

---

## Section 2: Performance Metrics (Rows 4-20)

Detailed performance analysis.

### Panel 6: Task Throughput
- **Shows**: Tasks processed per minute (completed and failed)
- **Metrics**:
  - Blue line: Total tasks/min
  - Green line: Completed tasks/min
  - Red line: Failed tasks/min
- **What to watch**: Throughput consistency, failure spikes
- **Action**: Spikes in red line indicate increased failures; investigate

### Panel 7: Task Duration
- **Shows**: Task execution time percentiles (P50, P95, P99)
- **Interpretation**:
  - P50: Median task duration
  - P95: 95% of tasks complete within this time
  - P99: 99% of tasks complete within this time
- **Action if increasing**: Tasks becoming slower; check resource usage

### Panel 8: Token Usage (Legacy)
- **Shows**: Overall token consumption rate
- **Interpretation**: Aggregate tokens per 5-minute window
- **Note**: See "Token Throughput" panel for detailed breakdown

### Panel 9: Queue Depth Over Time
- **Shows**: Queue depth trend (pending vs processing)
- **Metrics**:
  - Blue line: Pending tasks
  - Orange line: Currently processing tasks
- **What to watch**: Queue buildup, processing capacity
- **Action if pending increases**: Throughput insufficient; scale up

### Panel 10: Routing Latency
- **Shows**: Time to route tasks to agents (P95)
- **Interpretation**: 95% of routing decisions complete within this time
- **Normal range**: <100ms
- **Action if high**: Orchestrator may be overloaded; check CPU/memory

### Panel 11: Validation Errors
- **Shows**: Rate of validation errors per second
- **What to watch**: Sudden spikes
- **Action if spiking**: Check error logs for validation failure patterns

---

## Section 3: Token Metrics (Rows 28-36)

Detailed token consumption analysis.

### Panel 12: Token Throughput (Input/Output/Cached)
- **Shows**: Real-time token consumption breakdown
- **Metrics**:
  - Blue line: Input tokens/second
  - Orange line: Output tokens/second
  - Green line: Cached tokens/second
- **Interpretation**:
  - Higher input = more complex prompts
  - Higher output = longer responses
  - Higher cached = good prompt reuse
- **What to watch**: 
  - Input/output ratio (should be ~1:0.5 typically)
  - Cached tokens indicate prompt caching working
- **Action if no cached tokens**: Prompt caching not enabled or ineffective

### Panel 13: Token Usage by Model
- **Shows**: Pie chart of token distribution across models
- **Models**:
  - Haiku: Budget-conscious, fast
  - Sonnet: Balanced cost/capability
  - Opus: High-capability, expensive
- **Interpretation**: 
  - Haiku-heavy = cost-optimized
  - Opus-heavy = complex tasks
  - Sonnet-heavy = balanced approach
- **Action**: 
  - If Opus >30%: Consider if tasks can use Sonnet
  - If Haiku <20%: Consider more low-complexity routing to Haiku

### Panel 14: Tokens per Task (Histogram)
- **Shows**: Distribution of token usage per task
- **Percentiles**:
  - P25: 25% of tasks use ≤this many tokens
  - P50: Median token usage
  - P75: 75% of tasks use ≤this many tokens
  - P95: 95% of tasks use ≤this many tokens
  - P99: 99% of tasks use ≤this many tokens
- **Interpretation**: 
  - Narrow distribution = consistent task complexity
  - Wide distribution = varied task complexity
  - High P99 = outlier tasks consuming many tokens
- **Action if P99 very high**: 
  - Investigate outlier tasks
  - Consider prompt optimization
  - May need to split complex tasks

### Panel 15: Cache Hit Rate
- **Shows**: Gauge indicating percentage of cached tokens
- **Thresholds**:
  - 🟢 Green: ≥40% (excellent caching)
  - 🟡 Yellow: 20-40% (moderate caching)
  - 🔴 Red: <20% (poor caching)
- **Interpretation**: 
  - Higher = more prompt reuse
  - Indicates prompt caching effectiveness
- **Action if red**: 
  - Enable prompt caching if not already enabled
  - Optimize prompts for better reuse
  - Check if same prompts are being reused

---

## Section 4: Cost Metrics (Rows 44-60)

Cost analysis and optimization.

### Panel 16: Daily Cost (USD)
- **Shows**: Total cost for current day
- **Thresholds**:
  - 🟢 Green: $0-100 (low cost)
  - 🟡 Yellow: $100-500 (moderate cost)
  - 🔴 Red: >$500 (high cost)
- **Interpretation**: Total token consumption cost in USD
- **Action if red**: 
  - Review "Cost by Model" to identify expensive models
  - Check "Cost by Role" to see which teams are driving costs
  - Implement cost optimization measures

### Panel 17: Cost by Role
- **Shows**: Pie chart of cost distribution across agent roles
- **Roles**:
  - Engineer: Low-complexity tasks (Haiku)
  - Senior Engineer: Medium-complexity tasks (Sonnet)
  - Lead Engineer: Complex tasks (Sonnet/Opus)
  - Principal Engineer: Architectural decisions (Opus)
  - Quality Engineer: Review tasks (Sonnet)
  - Security Engineer: Security analysis (Opus)
- **Interpretation**: 
  - Which roles are consuming the most budget
  - Helps identify cost drivers
- **Action**: 
  - If Engineer >50%: Good cost optimization
  - If Principal >30%: May indicate over-engineering
  - Review role assignments for cost efficiency

### Panel 18: Cost by Model
- **Shows**: Pie chart of cost distribution across models
- **Models**:
  - Haiku: $0.80 per 1M input, $4.00 per 1M output
  - Sonnet: $3.00 per 1M input, $15.00 per 1M output
  - Opus: $15.00 per 1M input, $75.00 per 1M output
- **Interpretation**: 
  - Haiku-heavy = cost-optimized
  - Opus-heavy = high capability but expensive
- **Action**: 
  - If Opus >40%: Consider if Sonnet can handle tasks
  - If Haiku <30%: Consider more low-complexity routing to Haiku
  - Use for A/B testing model efficiency

### Panel 19: Cost per Task (Histogram)
- **Shows**: Distribution of task costs
- **Percentiles**:
  - P25: 25% of tasks cost ≤this much
  - P50: Median task cost
  - P75: 75% of tasks cost ≤this much
  - P95: 95% of tasks cost ≤this much
  - P99: 99% of tasks cost ≤this much
- **Interpretation**: 
  - Narrow distribution = consistent task costs
  - Wide distribution = varied task complexity/cost
  - High P99 = expensive outlier tasks
- **Action if P99 very high**: 
  - Investigate expensive tasks
  - Consider prompt optimization
  - May need to split complex tasks
  - Review if cheaper model could work

### Panel 20: Cost Trend (7 days)
- **Shows**: Daily cost trend over last 7 days
- **Interpretation**: 
  - Upward trend = increasing costs
  - Downward trend = cost optimization working
  - Spikes = unusual high-cost days
- **What to watch**: 
  - Sustained upward trend
  - Sudden spikes
  - Weekly patterns (e.g., higher on weekdays)
- **Action if trending up**: 
  - Implement cost optimization
  - Review model routing
  - Check for inefficient prompts
  - Consider caching improvements

---

## Common Workflows

### Workflow 1: Daily Cost Review

**Time**: 5 minutes  
**Frequency**: Daily (morning)

1. Check **Daily Cost** (Panel 16) — is it within budget?
2. Review **Cost Trend** (Panel 20) — is it increasing?
3. Check **Cost by Model** (Panel 18) — which models are expensive?
4. Check **Cost by Role** (Panel 17) — which roles are expensive?
5. If cost is high:
   - Investigate expensive tasks in logs
   - Review model routing strategy
   - Consider prompt optimization

### Workflow 2: Token Efficiency Analysis

**Time**: 10 minutes  
**Frequency**: Weekly

1. Check **Token Throughput** (Panel 12) — what's the input/output ratio?
2. Review **Cache Hit Rate** (Panel 15) — is caching working?
3. Check **Tokens per Task** (Panel 14) — are there outliers?
4. Review **Token Usage by Model** (Panel 13) — is distribution optimal?
5. If efficiency is low:
   - Enable/improve prompt caching
   - Optimize prompts to reduce tokens
   - Consider model routing adjustments

### Workflow 3: Performance Troubleshooting

**Time**: 15 minutes  
**Frequency**: As needed (when issues occur)

1. Check **Task Success Rate** (Panel 2) — is it below 95%?
2. Review **Error Rate** (Panel 3) — is it above 1%?
3. Check **Validation Errors** (Panel 11) — are there spikes?
4. Review **Queue Depth** (Panel 4) — is queue backing up?
5. Check **Task Duration** (Panel 7) — are tasks slower than usual?
6. If issues found:
   - Check error logs for patterns
   - Review recent code changes
   - Check resource usage (CPU, memory)
   - Consider scaling up orchestrator

### Workflow 4: Cost Optimization Sprint

**Time**: 30 minutes  
**Frequency**: Monthly

1. Review **Cost Trend** (Panel 20) — what's the monthly cost?
2. Analyze **Cost by Model** (Panel 18) — which models are expensive?
3. Check **Cost by Role** (Panel 17) — which roles are expensive?
4. Review **Tokens per Task** (Panel 14) — are there optimization opportunities?
5. Check **Cache Hit Rate** (Panel 15) — can caching be improved?
6. Create optimization plan:
   - Route more tasks to Haiku
   - Improve prompt caching
   - Optimize prompts to reduce tokens
   - Consider A/B testing different models

---

## Dashboard Customization

### Time Range Selection

Click the time range selector (top right) to change:
- Last 1 hour (default)
- Last 6 hours
- Last 24 hours
- Last 7 days
- Custom range

**Recommendation**: Use "Last 24 hours" for daily reviews, "Last 7 days" for trend analysis.

### Refresh Rate

Default: 30 seconds

To change:
1. Click **Dashboard settings** (gear icon)
2. Set **Refresh interval**
3. Options: 5s, 10s, 30s, 1m, 5m, 10m, 30m

**Recommendation**: 30s for real-time monitoring, 5m for background monitoring.

### Exporting Data

To export metrics for external analysis:

1. Click **Share** (top right)
2. Select **Export** tab
3. Choose format (CSV, JSON)
4. Download data

---

## Alerts & Thresholds

Recommended alert rules to create:

### Alert 1: High Error Rate
```
alert: HighErrorRate
expr: (rate(orchestrator_errors_total[5m]) / rate(orchestrator_tasks_total[5m])) > 0.05
for: 5m
```

### Alert 2: Queue Backlog
```
alert: QueueBacklog
expr: orchestrator_queue_depth > 100
for: 10m
```

### Alert 3: High Daily Cost
```
alert: HighDailyCost
expr: sum(orchestrator_cost_total) > 500
for: 1h
```

### Alert 4: Low Cache Hit Rate
```
alert: LowCacheHitRate
expr: (sum(orchestrator_tokens_cached_total) / sum(orchestrator_tokens_total)) < 0.2
for: 30m
```

---

## Troubleshooting

### Panel Shows "No Data"

**Cause**: Metrics not being collected  
**Solution**:
1. Verify Prometheus is scraping metrics
2. Check Prometheus targets page
3. Verify metrics are being exported
4. Check Prometheus query syntax

### Incorrect Cost Values

**Cause**: Pricing table outdated  
**Solution**:
1. Verify pricing in code matches current rates
2. Check token counts in HANDBACK blocks
3. Validate cost calculation formula

### Missing Labels

**Cause**: Task metadata incomplete  
**Solution**:
1. Verify HANDBACK blocks include model and role
2. Check orchestrator is setting labels
3. Validate label values are strings

---

## Best Practices

1. **Monitor Daily**: Check KPI cards every morning
2. **Review Trends**: Check cost trend weekly
3. **Investigate Spikes**: Act quickly on error rate spikes
4. **Optimize Regularly**: Monthly cost optimization reviews
5. **Set Alerts**: Configure alerts for key thresholds
6. **Document Changes**: Note any model/routing changes
7. **Share Insights**: Share cost/efficiency reports with team

---

## Related Documentation

- **Metrics Implementation**: See `METRICS_IMPLEMENTATION.md`
- **Dashboard Updates**: See `DASHBOARD_UPDATES.md`
- **Orchestrator Code**: See `src/orchestration/agents/orchestrator.py`
- **Prometheus Setup**: See `docs/MONITORING.md`

---

**Dashboard Version**: 2.0  
**Last Updated**: May 17, 2026  
**Status**: Production Ready ✅
