# metrics-etl Restoration Guide

## Status

**Deprecated:** 2026-05-30  
**Reason:** Low maintenance priority, no test coverage, minimal implementation. Better served by dedicated usage-tracking skill and simplified metrics collection.

## Deprecation Rationale

- **No test coverage** — ETL pipeline without validation
- **Minimal implementation** — only 1 script for complex data pipeline
- **Functional overlap** — usage-tracking skill provides real-time metrics; simpler approach works
- **Grafana complexity** — assuming Grafana/Prometheus setup may not match real deployments
- **Underutilized** — no evidence of active usage in monitoring

## Historical Context

`metrics-etl` was designed to aggregate daily metrics into Prometheus format for Grafana dashboards:
- Collect daily metrics from all automation agents
- Transform to Prometheus exposition format
- Store in format readable by Grafana
- Enable visualization of token usage, costs, and performance

However:
- `usage-tracking` skill already provides real-time metrics collection
- Most teams use simple logs or GitHub metrics rather than Grafana
- Prometheus/Grafana setup is deployment-specific
- Simpler CSV or JSON export is often sufficient

## Alternatives & Migration Paths

**For metrics collection and visualization, use one of these alternatives:**

1. **usage-tracking skill** (RECOMMENDED)
   - Already provides real-time and historical token usage
   - Captures, analyzes, and forecasts metrics
   - Integrated with DELEGATE/HANDBACK protocol
   - Simpler than ETL pipeline

2. **CSV/JSON export** (SIMPLE APPROACH)
   - Export metrics to CSV for Excel analysis
   - Export to JSON for dashboard APIs
   - Simple Python script (10-20 lines) to do the transformation
   - Works everywhere, no external dependencies

3. **Grafana + Prometheus** (IF YOU HAVE IT)
   - Use if already deployed in your infrastructure
   - Use `usage-tracking` with custom Prometheus exporter
   - Standard visualization platform

4. **GitHub Insights + GitHub Analytics** (FOR GITHUB-NATIVE TEAMS)
   - Use GitHub's built-in workflow usage analytics
   - Use GitHub Issues for cost tracking
   - Simpler if your primary data is in GitHub

## When to Restore

**Do NOT restore this skill unless:**
1. You already have Grafana deployed
2. You need complex time-series metrics aggregation
3. Comprehensive test suite is added (≥10 tests for ETL transformations)
4. Clear metrics show actual usage

**Restore if:** Your SRE team standardizes on Grafana and requires metrics-etl as part of deployment.

## Git Commands to Restore

**Option A: Restore from archive**
```bash
cp -r docs/archive/deprecated-skills/metrics-etl ~/.claude/skills/metrics-etl
# Update __init__.py
pytest tests/test_metrics_etl.py -v
git add -A
git commit -m "restore: re-enable metrics-etl with test suite"
git push
```

**Option B: Restore from git history**
```bash
git log --oneline --all -- .claude/skills/metrics-etl | head -5
git show <commit_hash>:.claude/skills/metrics-etl > /tmp/backup.tar
tar -xf /tmp/backup.tar ~/.claude/skills/metrics-etl
```

## How to Re-Enable

**BEFORE re-enabling, address deprecation concerns:**

1. **Add comprehensive test suite:**
   ```bash
   tests/test_metrics_etl.py (minimum 10 tests)
   - test_collect_daily_metrics
   - test_transform_to_prometheus_format
   - test_aggregate_by_agent
   - test_aggregate_by_role
   - test_calculate_cost_metrics
   - test_export_to_prometheus_exposition
   - test_handle_missing_data
   - test_timestamp_normalization
   - test_prometheus_format_validity
   - test_integration_with_usage_tracking
   ```

2. **Re-register in __init__.py:**
   ```python
   from .metrics_etl import MetricsETL
   AVAILABLE_SKILLS['metrics-etl'] = MetricsETL
   ```

3. **Update routing rules:**
   ```yaml
   - skill: metrics-etl
     condition: "metrics_export == 'prometheus' AND grafana_enabled == true"
     role: orchestrator
     tier: lightweight
   ```

4. **Update docs/SKILLS-AVAILABLE.md**

5. **Commit:**
   ```bash
   git add tests/ skills/ .opencode/ docs/
   git commit -m "restore: re-enable metrics-etl with comprehensive test suite"
   make verify
   git push
   ```

## Archive Location

```
docs/archive/deprecated-skills/metrics-etl/
├── SKILL.md (original skill definition)
├── scripts/ (original implementation)
├── RESTORATION.md (this file)
└── tests/ (original tests, if any)
```

## Last Known State

- **Deprecation Commit:** d84e255e (2026-05-30)
- **Test Coverage:** 0% (no tests in original)
- **Scripts:** 1 implementation file
- **Category:** metrics

## Questions?

Refer to:
- `docs/DEPRECATED-SKILLS.md` — Master index
- `docs/SKILLS-AVAILABLE.md` → usage-tracking skill (preferred alternative)
- `docs/TOKEN-USAGE-TRACKING.md` — Metrics API reference
