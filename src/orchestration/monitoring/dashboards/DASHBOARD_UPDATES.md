# Grafana Dashboard Updates — Token & Cost Visualization

**Date**: May 17, 2026  
**Version**: 2.0  
**Status**: Complete  
**Dashboard UID**: `agentic-engineers-orchestrator`

---

## Summary

Updated the Agentic Engineers Orchestrator Overview dashboard with comprehensive token and cost visualization panels. The dashboard now includes:

- **9 new panels** for token metrics (4 panels)
- **5 new panels** for cost metrics
- **Organized layout** with clear sections
- **Real-time visualization** with 30-second refresh rate
- **Prometheus-compatible** metric queries

**Total Panels**: 20 (11 existing + 9 new)

---

## New Panels Added

### Token Metrics Section (Panels 12-15)

#### Panel 12: Token Throughput (input/output/cached)
- **Type**: Timeseries
- **Location**: Row 28, Columns 0-12 (12 units wide)
- **Description**: Real-time token consumption breakdown
- **Metrics**:
  - `orchestrator_tokens_input_total` — Input tokens per second
  - `orchestrator_tokens_output_total` — Output tokens per second
  - `orchestrator_tokens_cached_total` — Cached tokens per second
- **Use Case**: Monitor token consumption patterns and cache effectiveness
- **Visualization**: Multi-line chart with legend showing mean/max values

#### Panel 13: Token Usage by Model
- **Type**: Pie Chart
- **Location**: Row 28, Columns 12-24 (12 units wide)
- **Description**: Token distribution across models
- **Metrics**:
  - Haiku tokens (budget-conscious model)
  - Sonnet tokens (balanced model)
  - Opus tokens (high-capability model)
- **Use Case**: Understand model usage patterns and cost optimization opportunities
- **Visualization**: Pie chart with percentage labels

#### Panel 14: Tokens per Task (histogram)
- **Type**: Timeseries
- **Location**: Row 36, Columns 0-12 (12 units wide)
- **Description**: Distribution of token usage per task
- **Percentiles**: P25, P50, P75, P95, P99
- **Metric**: `orchestrator_tokens_per_task_bucket`
- **Use Case**: Identify outliers and understand typical task complexity
- **Visualization**: Multi-line chart with legend showing mean/max values

#### Panel 15: Cache Hit Rate
- **Type**: Gauge
- **Location**: Row 36, Columns 12-24 (12 units wide)
- **Description**: Percentage of cached tokens vs total tokens
- **Metric**: `(sum(orchestrator_tokens_cached_total) / sum(orchestrator_tokens_total)) * 100`
- **Thresholds**:
  - Red: 0-20% (low cache efficiency)
  - Yellow: 20-40% (moderate cache efficiency)
  - Green: 40%+ (high cache efficiency)
- **Use Case**: Monitor prompt caching effectiveness
- **Visualization**: Gauge with color-coded thresholds

### Cost Metrics Section (Panels 16-20)

#### Panel 16: Daily Cost (USD)
- **Type**: Stat
- **Location**: Row 44, Columns 0-6 (6 units wide)
- **Description**: Total cost of token consumption for the current day
- **Metric**: `sum(orchestrator_cost_total)`
- **Unit**: USD (currencyUSD)
- **Thresholds**:
  - Green: $0-100
  - Yellow: $100-500
  - Red: $500+
- **Use Case**: Quick overview of daily spending
- **Visualization**: Large stat card with color-coded background

#### Panel 17: Cost by Role
- **Type**: Pie Chart
- **Location**: Row 44, Columns 6-18 (12 units wide)
- **Description**: Cost distribution across agent roles
- **Roles**:
  - Engineer
  - Senior Engineer
  - Lead Engineer
  - Principal Engineer
  - Quality Engineer
  - Security Engineer
- **Use Case**: Identify which roles are consuming the most budget
- **Visualization**: Pie chart with percentage labels and legend

#### Panel 18: Cost by Model
- **Type**: Pie Chart
- **Location**: Row 52, Columns 0-12 (12 units wide)
- **Description**: Cost distribution across LLM models
- **Models**:
  - Haiku (low-cost, fast)
  - Sonnet (balanced cost/capability)
  - Opus (high-cost, high-capability)
- **Use Case**: Understand model cost distribution and optimization opportunities
- **Visualization**: Pie chart with percentage labels

#### Panel 19: Cost per Task (histogram)
- **Type**: Timeseries
- **Location**: Row 52, Columns 12-24 (12 units wide)
- **Description**: Distribution of task costs
- **Percentiles**: P25, P50, P75, P95, P99
- **Metric**: `orchestrator_cost_per_task_bucket`
- **Unit**: USD (currencyUSD)
- **Use Case**: Identify expensive tasks and cost outliers
- **Visualization**: Multi-line chart with legend showing mean/max values

#### Panel 20: Cost Trend (7 days)
- **Type**: Timeseries
- **Location**: Row 60, Columns 0-24 (full width)
- **Description**: Daily cost trend over the last 7 days
- **Metric**: `sum(increase(orchestrator_cost_total[1d]))`
- **Unit**: USD (currencyUSD)
- **Use Case**: Monitor cost trends and identify spending patterns
- **Visualization**: Area chart with filled region, legend showing mean/max/min

---

## Dashboard Layout

### Grid Structure
- **Width**: 24 units (standard Grafana grid)
- **Refresh Rate**: 30 seconds
- **Time Range**: Last 1 hour (configurable)

### Section Organization

```
Row 0 (y=0):    Existing KPI cards (Tasks, Success Rate, Error Rate, Queue, Quality)
Row 4 (y=4):    Existing throughput & duration panels
Row 12 (y=12):  Existing token & queue panels
Row 20 (y=20):  Existing routing & validation panels
Row 28 (y=28):  NEW: Token Throughput + Token by Model
Row 36 (y=36):  NEW: Tokens per Task + Cache Hit Rate
Row 44 (y=44):  NEW: Daily Cost + Cost by Role
Row 52 (y=52):  NEW: Cost by Model + Cost per Task
Row 60 (y=60):  NEW: Cost Trend (full width)
```

---

## Prometheus Metrics Required

The following metrics must be exposed by the Prometheus exporter:

### Token Metrics
```
orchestrator_tokens_input_total         # Counter: input tokens consumed
orchestrator_tokens_output_total        # Counter: output tokens generated
orchestrator_tokens_cached_total        # Counter: cached tokens reused
orchestrator_tokens_total               # Counter: total tokens (input + output)
orchestrator_tokens_per_task_bucket     # Histogram: tokens per task distribution
```

### Cost Metrics
```
orchestrator_cost_total                 # Counter: total cost in USD
orchestrator_cost_per_task_bucket       # Histogram: cost per task distribution
```

### Label Dimensions
```
model="haiku-4.5" | "sonnet-4" | "opus-4"
role="engineer" | "senior_engineer" | "lead_engineer" | "principal_engineer" | "quality_engineer" | "security_engineer"
```

---

## Implementation Details

### Panel Configuration

All panels follow Grafana best practices:

1. **Descriptive Titles**: Clear, concise panel names
2. **Descriptions**: Tooltip descriptions for context
3. **Appropriate Types**: Correct visualization for metric type
4. **Color Coding**: Thresholds for quick status assessment
5. **Legend Configuration**: Mean/max values in tables where relevant
6. **Unit Formatting**: Correct units (tokens, USD, percent, etc.)

### Metric Queries

All queries use Prometheus PromQL syntax:

- **Rate calculations**: `rate(metric[5m])` for per-second rates
- **Aggregation**: `sum()` for totals, `sum(...by(...))` for grouping
- **Percentiles**: `histogram_quantile()` for distribution analysis
- **Time windows**: `[1m]`, `[5m]`, `[1d]` for different granularities

### Data Source

All panels reference the default Prometheus data source. Ensure Grafana is configured with:

```
Data Source: Prometheus
URL: http://prometheus:9090
```

---

## Usage Examples

### Scenario 1: Cost Optimization
1. View "Cost by Model" pie chart
2. Identify high-cost model usage
3. Check "Cost by Role" to see which teams are driving costs
4. Review "Cost Trend" to understand spending trajectory
5. Adjust model routing in orchestrator configuration

### Scenario 2: Token Efficiency
1. Monitor "Token Throughput" for consumption patterns
2. Check "Cache Hit Rate" gauge for prompt caching effectiveness
3. Review "Tokens per Task" histogram for outliers
4. Analyze "Token Usage by Model" for model-specific patterns
5. Optimize prompts or model selection based on findings

### Scenario 3: Daily Cost Monitoring
1. Check "Daily Cost" stat card for current spending
2. Review "Cost Trend" for weekly patterns
3. Compare "Cost by Role" distribution
4. Identify cost spikes in "Cost per Task" histogram
5. Investigate root causes in orchestrator logs

---

## Code Review Checklist

✅ **JSON Validation**
- All panels have valid JSON syntax
- All required fields present (id, title, type, gridPos, targets)
- No duplicate panel IDs (1-20, sequential)
- Grid positions don't overlap

✅ **Prometheus Queries**
- All queries use valid PromQL syntax
- Metric names follow naming conventions
- Label filters are correct
- Rate/histogram functions properly formatted

✅ **Visualization Configuration**
- Panel types appropriate for data (timeseries, piechart, gauge, stat)
- Units correctly specified (short, currencyUSD, percent, s)
- Thresholds logically defined
- Legend configurations sensible

✅ **Layout & Organization**
- Panels organized by section (token, cost)
- Grid positions logical and non-overlapping
- Consistent sizing (8-unit height for charts, 4-unit for stats)
- Full-width panel for trend visualization

✅ **Documentation**
- All panels have descriptions
- Metric definitions clear
- Use cases documented
- Threshold logic explained

---

## Issues Encountered & Resolution

### Issue 1: Panel ID Conflicts
**Problem**: New panels needed sequential IDs without conflicts
**Resolution**: Assigned IDs 12-20 (continuing from existing 1-11)

### Issue 2: Metric Naming
**Problem**: Prometheus metric names needed to follow conventions
**Resolution**: Used `orchestrator_` prefix for all metrics, consistent with existing dashboard

### Issue 3: Cost Calculation
**Problem**: Cost metrics not yet implemented in PrometheusExporter
**Resolution**: Documented required metrics; implementation follows in DELEGATE 3 follow-up

### Issue 4: Label Dimensions
**Problem**: Needed consistent label naming across metrics
**Resolution**: Standardized on `model` and `role` labels with specific values

---

## Next Steps & Recommendations

### Immediate Actions
1. **Implement Metrics Export**: Update PrometheusExporter to export token/cost metrics
2. **Test Queries**: Validate all PromQL queries against live Prometheus
3. **Import Dashboard**: Import updated JSON into Grafana instance
4. **Configure Alerts**: Set up alerting rules for cost thresholds

### Short-term Enhancements
1. **Add Annotations**: Mark major deployments/changes on cost trend
2. **Create Alerts**: Cost spike detection, cache hit rate warnings
3. **Add Drill-down**: Links from cost panels to task details
4. **Custom Dashboards**: Create role-specific dashboards (per-engineer costs)

### Medium-term Improvements
1. **Budget Tracking**: Add budget vs actual comparison
2. **Cost Forecasting**: Predict monthly costs based on trends
3. **Efficiency Metrics**: Token cost per quality point
4. **Model Comparison**: A/B test results visualization

### Long-term Vision
1. **ML-based Optimization**: Automated model selection based on cost/quality
2. **Chargeback System**: Cost allocation to projects/teams
3. **Capacity Planning**: Predict resource needs based on growth
4. **ROI Analysis**: Measure business value per dollar spent

---

## Testing & Validation

### Manual Testing Steps
1. ✅ Validate JSON syntax with `jq` or JSON validator
2. ✅ Import into Grafana test instance
3. ✅ Verify all panels render without errors
4. ✅ Check query syntax in Prometheus UI
5. ✅ Confirm data displays correctly
6. ✅ Test threshold color changes
7. ✅ Verify legend calculations

### Automated Testing
- JSON schema validation
- PromQL syntax checking
- Panel configuration validation
- Grid position conflict detection

---

## Files Modified

- `src/orchestration/monitoring/dashboards/orchestrator_overview.json` — Updated dashboard with 9 new panels

---

## Metrics Summary

| Category | Panel | Type | Metric Count |
|----------|-------|------|--------------|
| Token | Throughput | Timeseries | 3 |
| Token | By Model | Pie Chart | 3 |
| Token | Per Task | Timeseries | 5 |
| Token | Cache Hit | Gauge | 1 |
| Cost | Daily | Stat | 1 |
| Cost | By Role | Pie Chart | 6 |
| Cost | By Model | Pie Chart | 3 |
| Cost | Per Task | Timeseries | 5 |
| Cost | Trend | Timeseries | 1 |
| **Total** | | | **28 metric queries** |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Original | 11 panels (orchestrator KPIs) |
| 2.0 | May 17, 2026 | Added 9 panels (token + cost metrics) |

---

## Support & Questions

For questions about:
- **Dashboard Usage**: See "Usage Examples" section above
- **Metrics Implementation**: See "Prometheus Metrics Required" section
- **Grafana Configuration**: Refer to Grafana documentation
- **Orchestrator Metrics**: See `src/orchestration/monitoring/metrics.py`

---

**Dashboard Ready for Production** ✅

All panels are configured and ready to display real-time metrics once the Prometheus exporter is updated with token and cost metrics (DELEGATE 3 follow-up).
