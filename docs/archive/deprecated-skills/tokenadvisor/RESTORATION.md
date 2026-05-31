# tokenadvisor Restoration Guide

## Status

**Deprecated:** 2026-05-30  
**Reason:** Low maintenance priority, no test coverage, minimal implementation. Core functionality covered by usage-tracking and model-engineer skills.

## Deprecation Rationale

- **No test coverage** — metrics analysis without validation
- **Minimal implementation** — only 1 primary script despite complex analysis requirements
- **Functional overlap** — usage-tracking provides metrics collection; model-engineer provides optimization analysis
- **Underutilized** — no evidence of daily adoption
- **Better alternatives** — decompose functionality into usage-tracking (data) + model-engineer (analysis)

## Historical Context

`tokenadvisor` was designed to provide daily metrics analysis for cost optimization:
- Aggregate metrics by role and task type
- Identify cost inefficiencies and outliers
- Flag anomalies in token spend
- Recommend optimizations
- Generate daily reports

However:
- `usage-tracking` skill already collects all necessary metrics
- `model-engineer` skill already analyzes metrics and recommends optimizations
- Daily reports can be generated as simple aggregations
- Combining two specialized skills is clearer than one umbrella skill

## Alternatives & Migration Paths

**For token usage analysis and cost optimization, use one of these alternatives:**

1. **usage-tracking + model-engineer** (RECOMMENDED)
   - usage-tracking: Real-time/historical collection, analysis, forecasting
   - model-engineer: Cost-quality analysis, generates recommendations
   - Both integrated with DELEGATE/HANDBACK protocol
   - Clearer separation of concerns

2. **Daily metrics CSV export** (SIMPLE APPROACH)
   - Simple Python script to aggregate daily metrics to CSV
   - Use Excel/Sheets for trend analysis
   - Manual review instead of automated recommendations
   - Works for small teams

3. **GitHub Insights** (FOR GITHUB-NATIVE TEAMS)
   - Use GitHub's built-in workflow usage analytics
   - Track token spend via CI/CD logs
   - Simpler if primary data is in GitHub

4. **Custom dashboard** (FOR ADVANCED MONITORING)
   - Query metrics database directly
   - Build custom Grafana dashboard
   - Real-time alerting on cost thresholds
   - For teams requiring sophisticated monitoring

## When to Restore

**Do NOT restore this skill unless:**
1. You want a unified daily report combining metrics + optimization recommendations
2. Comprehensive test suite is added (≥15 tests for aggregation and anomaly detection)
3. Clear metrics show actual usage

**Restore if:** Your team prefers a single daily report to checking usage-tracking and model-engineer separately.

## Git Commands to Restore

**Option A: Restore from archive**
```bash
cp -r docs/archive/deprecated-skills/tokenadvisor ~/.claude/skills/tokenadvisor
# Update __init__.py
pytest tests/test_tokenadvisor.py -v
git add -A
git commit -m "restore: re-enable tokenadvisor with comprehensive test suite"
git push
```

**Option B: Restore from git history**
```bash
git log --oneline --all -- .claude/skills/tokenadvisor | head -5
git show <commit_hash>:.claude/skills/tokenadvisor > /tmp/backup.tar
tar -xf /tmp/backup.tar ~/.claude/skills/tokenadvisor
```

## How to Re-Enable

**BEFORE re-enabling, address deprecation concerns:**

1. **Add comprehensive test suite:**
   ```bash
   tests/test_tokenadvisor.py (minimum 15 tests)
   - test_aggregate_metrics_by_role
   - test_identify_cost_inefficiencies
   - test_detect_outlier_token_usage
   - test_flag_unusual_patterns
   - test_recommend_optimizations
   - test_generate_daily_report
   - test_calculate_cost_per_quality
   - test_identify_overprovisioned_models
   - test_suggest_model_downgrades
   - test_integration_with_usage_tracking
   - test_integration_with_model_engineer
   - test_forecast_weekly_costs
   - test_alert_on_budget_threshold
   - test_export_to_json
   + 1 more
   ```

2. **Re-register in __init__.py:**
   ```python
   from .tokenadvisor import TokenAdvisor
   AVAILABLE_SKILLS['tokenadvisor'] = TokenAdvisor
   ```

3. **Update routing rules:**
   ```yaml
   - skill: tokenadvisor
     condition: "scheduling == 'daily' AND report_type == 'metrics-analysis'"
     role: orchestrator
     tier: lightweight
   ```

4. **Update docs/SKILLS-AVAILABLE.md**

5. **Commit:**
   ```bash
   git add tests/ skills/ .opencode/ docs/
   git commit -m "restore: re-enable tokenadvisor with comprehensive test suite

   - Added 15+ tests for aggregation, anomaly detection, recommendations
   - Integrated with usage-tracking for data collection
   - Integrated with model-engineer for optimization recommendations
   - Added daily report generation and export"
   
   make verify
   git push
   ```

## Archive Location

```
docs/archive/deprecated-skills/tokenadvisor/
├── SKILL.md (original skill definition)
├── scripts/ (original implementation)
├── RESTORATION.md (this file)
└── tests/ (original tests, if any)
```

## Last Known State

- **Deprecation Commit:** d84e255e (2026-05-30)
- **Test Coverage:** 0% (no tests in original)
- **Scripts:** 1-2 implementation files
- **Category:** metrics

## Daily Report Template (if restored)

```markdown
# Token Usage Report - 2026-05-30

## Summary
- Total tokens used: 45,230
- Cost: $0.89
- Compared to yesterday: +12% (within normal range)

## By Role
| Role | Tokens | % of Total | Cost | Quality Score |
|------|--------|-----------|------|---------------|
| Orchestrator | 12,150 | 26.8% | $0.23 | 95 |
| Engineer | 18,500 | 40.9% | $0.36 | 92 |
| Quality Engineer | 8,200 | 18.1% | $0.15 | 98 |
| Senior Engineer | 4,800 | 10.6% | $0.09 | 94 |
| Others | 1,580 | 3.5% | $0.03 | 91 |

## Anomalies Detected
- ⚠️ Senior Engineer usage +45% (investigate if planning phase expanded)
- ✓ Overall efficiency maintained despite increased volume

## Recommendations
1. Consider downgrading 2 Quality Engineer tasks to Engineer
2. Haiku model sufficient for 3 upcoming routing tasks
3. Next week: A/B test Sonnet vs. Opus for complex planning

## Cost Forecast
- Weekly trend: $6.23 (based on last 7 days)
- Monthly projection: $26.99 (within budget)
```

## Questions?

Refer to:
- `docs/DEPRECATED-SKILLS.md` — Master index
- `docs/SKILLS-AVAILABLE.md` → usage-tracking and model-engineer skills
- `docs/TOKEN-USAGE-TRACKING.md` — Detailed metrics API
