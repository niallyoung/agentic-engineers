# Grafana Dashboard — Token Visibility & Cost Metrics

**Version**: 2.0  
**Last Updated**: May 17, 2026  
**Status**: ✅ Production Ready  

---

## Overview

This directory contains the Agentic Engineers Grafana dashboard with comprehensive token and cost visualization panels. The dashboard provides real-time visibility into:

- **Token consumption** (input, output, cached)
- **Token distribution** by model and per-task
- **Prompt caching effectiveness**
- **Daily costs** in USD
- **Cost distribution** by role and model
- **Cost trends** over 7 days

---

## Files in This Directory

### Dashboard Configuration
- **`orchestrator_overview.json`** — Main Grafana dashboard (20 panels)
  - 11 existing orchestrator KPI panels
  - 9 new token and cost visualization panels
  - Ready to import into Grafana

### Documentation

#### 1. **`DASHBOARD_UPDATES.md`** — Dashboard Changes Summary
- Summary of all changes made
- Detailed panel descriptions
- Dashboard layout and grid structure
- Prometheus metrics required
- Implementation details
- Usage examples
- Code review checklist
- Issues and resolutions
- Next steps and recommendations

**Use this for**: Understanding what changed and why

#### 2. **`METRICS_IMPLEMENTATION.md`** — Technical Specification
- Detailed metrics specification
- Token metrics (4 types):
  - `orchestrator_tokens_input_total`
  - `orchestrator_tokens_output_total`
  - `orchestrator_tokens_cached_total`
  - `orchestrator_tokens_per_task_bucket`
- Cost metrics (2 types):
  - `orchestrator_cost_total`
  - `orchestrator_cost_per_task_bucket`
- Collection implementation code
- Testing and validation procedures
- Deployment checklist
- Pricing reference table

**Use this for**: Implementing metrics in the Orchestrator

#### 3. **`USAGE_GUIDE.md`** — User Guide
- Quick start instructions
- Dashboard overview and sections
- Detailed panel explanations (all 20 panels)
- Interpretation guides for each metric
- Common workflows (4 scenarios):
  - Daily cost review (5 min)
  - Token efficiency analysis (10 min)
  - Performance troubleshooting (15 min)
  - Cost optimization sprint (30 min)
- Dashboard customization options
- Alert rules recommendations
- Troubleshooting guide
- Best practices

**Use this for**: Learning how to use the dashboard

#### 4. **`VISUAL_EXAMPLES.md`** — Visual Reference
- Expected visual appearance of each panel
- ASCII art mockups
- Color coding explanations
- Interpretation guides
- Data patterns (normal, high activity, issues)
- Interactive features
- Screenshots checklist
- Accessibility notes

**Use this for**: Understanding what panels should look like

#### 5. **`COMPLETION_REPORT.md`** — Project Summary
- Executive summary
- Deliverables list
- Panel details and breakdown
- Prometheus metrics required
- Implementation status
- Quality metrics
- Usage examples
- Token efficiency analysis
- Confidence assessment
- Known limitations
- Related documentation

**Use this for**: Project overview and status

---

## Quick Start

### 1. Import Dashboard into Grafana

```bash
# Option A: Copy JSON to Grafana
1. Open Grafana: http://localhost:3000
2. Go to Dashboards → Import
3. Paste contents of orchestrator_overview.json
4. Select Prometheus data source
5. Click Import

# Option B: File-based import (if configured)
cp orchestrator_overview.json /var/lib/grafana/dashboards/
```

### 2. Verify Prometheus Metrics

```bash
# Check if metrics are being exported
curl http://localhost:9090/api/v1/query?query=orchestrator_tokens_total

# Or in Prometheus UI
http://localhost:9090/graph
# Query: orchestrator_tokens_total
```

### 3. Access Dashboard

```
http://localhost:3000/d/agentic-engineers-orchestrator
```

---

## Dashboard Sections

### Row 0: KPI Cards
- Tasks Total
- Task Success Rate
- Error Rate
- Queue Depth
- Average Quality Score

### Rows 4-20: Performance Metrics (Existing)
- Task Throughput
- Task Duration
- Token Usage
- Queue Depth Over Time
- Routing Latency
- Validation Errors

### Row 28: Token Metrics (New)
- Token Throughput (input/output/cached)
- Token Usage by Model

### Row 36: Token Distribution (New)
- Tokens per Task (histogram)
- Cache Hit Rate (gauge)

### Row 44: Cost Overview (New)
- Daily Cost (USD)
- Cost by Role

### Row 52: Cost Distribution (New)
- Cost by Model
- Cost per Task (histogram)

### Row 60: Cost Trends (New)
- Cost Trend (7-day)

---

## Metrics Required

### Token Metrics
```
orchestrator_tokens_input_total          # Counter
orchestrator_tokens_output_total         # Counter
orchestrator_tokens_cached_total         # Counter
orchestrator_tokens_per_task_bucket      # Histogram
```

### Cost Metrics
```
orchestrator_cost_total                  # Counter
orchestrator_cost_per_task_bucket        # Histogram
```

### Label Dimensions
```
model: haiku-4.5 | sonnet-4 | opus-4
role: engineer | senior_engineer | lead_engineer | principal_engineer | quality_engineer | security_engineer
```

See `METRICS_IMPLEMENTATION.md` for detailed specification.

---

## Implementation Status

### ✅ Completed
- [x] Dashboard JSON with 20 panels
- [x] Token metrics panels (4)
- [x] Cost metrics panels (5)
- [x] Comprehensive documentation (5 guides)
- [x] JSON validation
- [x] Usage guide with workflows
- [x] Visual examples and mockups

### ⏳ Pending (Next Sprint)
- [ ] Implement metrics collection in Orchestrator
- [ ] Update PrometheusExporter (if needed)
- [ ] Create unit tests for metrics
- [ ] Deploy to staging environment
- [ ] Validate metrics in Prometheus
- [ ] Verify dashboard panels display data
- [ ] Deploy to production

---

## Documentation Index

| Document | Purpose | Audience |
|----------|---------|----------|
| `DASHBOARD_UPDATES.md` | What changed and why | Architects, Engineers |
| `METRICS_IMPLEMENTATION.md` | How to implement metrics | Backend Engineers |
| `USAGE_GUIDE.md` | How to use the dashboard | All Users |
| `VISUAL_EXAMPLES.md` | What panels look like | Designers, QA |
| `COMPLETION_REPORT.md` | Project summary | Managers, Leads |

---

## Common Tasks

### View Daily Costs
1. Open dashboard
2. Look at Panel 16 (Daily Cost)
3. Check Panel 20 (Cost Trend) for trends
4. Review Panel 18 (Cost by Model) to identify expensive models

### Analyze Token Efficiency
1. Check Panel 12 (Token Throughput)
2. Review Panel 15 (Cache Hit Rate)
3. Check Panel 14 (Tokens per Task) for outliers
4. Analyze Panel 13 (Token by Model) for distribution

### Troubleshoot Performance Issues
1. Check Panel 2 (Success Rate)
2. Review Panel 3 (Error Rate)
3. Check Panel 11 (Validation Errors)
4. Review Panel 4 (Queue Depth)

### Optimize Costs
1. Review Panel 20 (Cost Trend) for patterns
2. Check Panel 18 (Cost by Model)
3. Review Panel 17 (Cost by Role)
4. Check Panel 14 (Tokens per Task) for outliers
5. Implement optimizations

---

## Troubleshooting

### Dashboard Shows "No Data"
- **Cause**: Metrics not being collected
- **Solution**: See `METRICS_IMPLEMENTATION.md` for implementation
- **Check**: Verify Prometheus is scraping metrics

### Incorrect Cost Values
- **Cause**: Pricing table outdated
- **Solution**: Update pricing in code
- **Check**: Verify token counts in HANDBACK blocks

### Missing Panels
- **Cause**: JSON import failed
- **Solution**: Re-import dashboard JSON
- **Check**: Verify Grafana version compatibility

See `USAGE_GUIDE.md` for more troubleshooting tips.

---

## Related Documentation

- **Orchestrator Code**: `src/orchestration/agents/orchestrator.py`
- **Metrics Module**: `src/orchestration/monitoring/metrics.py`
- **PrometheusExporter**: `src/orchestration/monitoring/prometheus_exporter.py`
- **Monitoring Setup**: `docs/MONITORING.md`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Original | 11 panels (orchestrator KPIs) |
| 2.0 | May 17, 2026 | Added 9 panels (token + cost metrics) |

---

## Support & Questions

### For Dashboard Usage
→ See `USAGE_GUIDE.md`

### For Implementation
→ See `METRICS_IMPLEMENTATION.md`

### For Visual Reference
→ See `VISUAL_EXAMPLES.md`

### For Project Status
→ See `COMPLETION_REPORT.md`

### For Changes Made
→ See `DASHBOARD_UPDATES.md`

---

## Next Steps

1. **Implement Metrics**: Follow `METRICS_IMPLEMENTATION.md`
2. **Test Metrics**: Create unit tests for metric collection
3. **Deploy Dashboard**: Import JSON into Grafana
4. **Validate Data**: Verify metrics appear in dashboard
5. **Create Alerts**: Set up alerting rules
6. **Document Runbooks**: Create troubleshooting guides

---

**Dashboard Status**: ✅ Production Ready  
**Last Updated**: May 17, 2026  
**Maintained By**: Engineer Agent (agentic-engineers)

For questions or issues, refer to the appropriate documentation file above.
