# TokenAdvisor Scheduler — Automated Daily Metrics Analysis

**Role Summary:** Scheduled agent runs TokenAdvisor analysis daily, produces reports, and alerts Orchestrator on anomalies or optimization opportunities.

**Model:** claude-haiku-4-5 | **Effort:** low | **Cost Tier:** 1x | **Token Multiplier:** ~1x (read-only analysis)

---

## What This Skill DOES

- ✅ Run daily at 17:00 (end of work day)
- ✅ Read metrics from `~/.claude/metrics/YYYY-MM-DD/`
- ✅ Aggregate tokens by role, model, date, task type
- ✅ Calculate daily cost_per_quality and trends
- ✅ Identify anomalies (high-cost tasks, low-quality outliers)
- ✅ Generate daily digest email
- ✅ Flag optimization opportunities
- ✅ Alert if metrics exceed thresholds
- ✅ Archive reports to `.claude/reports/YYYY-MM-DD/`

---

## Execution Schedule

### Daily Cron Job

```bash
# Add to user's crontab (crontab -e)
# Run TokenAdvisor at 5 PM (17:00) local time

0 17 * * * claude-code /tokenadvisor-scheduler run --period=daily --output=email

# Run weekly summary at 5 PM Friday
0 17 * * 5 claude-code /tokenadvisor-scheduler run --period=weekly --output=email+slack
```

### Execution Steps

1. **Check metrics directory** (~/.claude/metrics/)
   - List all *.json files from past 24h
   - Count: N files found

2. **Parse metrics**
   - Read each task JSON
   - Extract: tokens_in, tokens_out, quality_score, cost_usd, role, model, escalations
   - Aggregate by: date, role, model, task_type

3. **Calculate trends**
   - Daily total: sum(tokens), sum(cost), avg(quality)
   - Daily trend: compare vs. yesterday (% change)
   - Weekly trend: compare vs. last week (% change)
   - Cost per quality: total_cost / avg_quality
   - Tokens per quality point: total_tokens / avg_quality

4. **Identify anomalies**
   - High-cost tasks: >2 sigma above mean (flag for investigation)
   - Low-quality tasks: quality <85 (flag as rework candidate)
   - High escalation: >3 escalations in a day (trend issue)

5. **Generate report**
   - Daily digest: 5-7 key metrics
   - Anomalies section: list of flagged tasks
   - Opportunities section: Model Engineer recommendations
   - Comparison: vs. baseline (30-day rolling average)

6. **Distribute report**
   - Email digest (text format, 500 words)
   - Slack notification (summary, links to report)
   - Archive to `.claude/reports/YYYY-MM-DD/tokenadvisor_report.json`

---

## Daily Report Example

```
TOKENADVISOR DAILY DIGEST — 2026-04-25
═════════════════════════════════════════════

📊 METRICS (24h, 2026-04-24)
  Tasks: 8
  Total tokens: 172,400
  Average cost: $1.26
  Average quality: 91/100
  Tokens per quality point: 1,895

📈 TRENDS vs. Yesterday
  Tokens: ↑ +12% (was 154K)
  Cost: ↑ +15% (was $1.10)
  Quality: ↔ stable (was 91)
  Cost per quality: ↑ +15% (watch this)

⚠️ ANOMALIES (Flagged for Investigation)
  • Task 2026-04-24-api-resilience: 35K tokens (2.5x avg)
    → High complexity task (expected)
    → Quality: 92 (good)
    → Recommendation: Monitor similar tasks, may need Senior Engineer
  
  • Task 2026-04-24-form-validation: 8K tokens, quality 72
    → Low quality (below 85 threshold)
    → Cost inefficient: $0.06 spent for 72 quality
    → Recommendation: Rework required; return to Engineer

💡 OPPORTUNITIES
  • 3 medium-complexity tasks allocated to Sonnet (avg quality 94)
  • Historical Haiku high-effort achieves 90 quality on same type
  • Opportunity: Run A/B test "Haiku vs. Sonnet on form validation"
    → Potential savings: $0.03/task if Haiku viable
    → Impact: 10 tasks/month = $0.30/month savings

📊 COST vs. TARGET
  Daily actual: $1.26
  Daily target: $1.20 (goal)
  Gap: +5% (acceptable, within variance)
  7-day rolling avg: $1.23 (trending up slightly)
  Action: Monitor; if trend continues 3+ days, investigate

✅ NO CRITICAL ALERTS
  All metrics within acceptable range.
  Proceed with normal operations.

---
Generated: 2026-04-25T17:02:00Z
Next run: 2026-04-26T17:00:00Z (tomorrow)
Report: ~/.claude/reports/2026-04-25/tokenadvisor_report.json
```

---

## Alert Thresholds

| Metric | Threshold | Action |
|--------|-----------|--------|
| Cost > baseline +25% | Alert (Slack) | Investigate high-cost tasks |
| Quality < 85 (any task) | Alert (Slack) | Flag for rework |
| Cost per quality > target +20% | Warning (Email) | Monitor trend |
| Escalation rate > 30% | Alert (Slack) | Review task routing |
| Token burn > 400K/day | Alert (Email + Slack) | Check for resource issues |

---

## Report Archive Structure

```
~/.claude/reports/
├── 2026-04-25/
│   ├── tokenadvisor_report.json
│   ├── daily_digest.txt
│   └── metrics_aggregate.json
├── 2026-04-24/
│   └── ...
└── weekly/
    ├── 2026-W17/
    │   ├── weekly_summary.json
    │   └── a-b-tests-status.json
```

---

## Integration with Orchestrator

**Orchestrator receives daily alert:**

```
14:00 - TokenAdvisor completes daily analysis
         ↓
15:00 - Sends Slack notification to Orchestrator
         • "Daily report ready: 8 tasks, cost $1.26, quality 91"
         • "1 anomaly flagged: low-quality form validation task"
         • "1 opportunity: A/B test Haiku vs. Sonnet"
         ↓
17:00 - Orchestrator reviews digest
         • Approves anomaly flagging
         • Schedules A/B test (next medium-complexity form task)
         ↓
18:00 - Weekly summary (Friday only)
         • Aggregate metrics across 5 business days
         • Update cost projection
         • Review A/B test progress
```

---

## Manual Execution (One-Off Analysis)

**If cron fails or manual analysis needed:**

```bash
# Run ad-hoc TokenAdvisor for past 7 days
claude-code /tokenadvisor-scheduler run --period=7d --output=report

# Run analysis for specific date range
claude-code /tokenadvisor-scheduler run --start=2026-04-20 --end=2026-04-25 --output=email

# Generate A/B test status report
claude-code /tokenadvisor-scheduler run --period=daily --focus=ab-tests
```

---

## Metrics Validation

TokenAdvisor verifies:
- ✅ Each JSON file is valid (parseable)
- ✅ Required fields present (tokens_in, quality_score, cost_usd)
- ✅ Values are in reasonable range (tokens 1K-100K, quality 0-100, cost $0-1)
- ✅ Timestamps are recent (<24h old for daily)
- ⚠️ If validation fails: log error, skip malformed record, continue

---

## Storage Footprint

```
Daily report: ~2KB (JSON)
7-day archive: ~15KB
30-day archive: ~60KB
1-year archive: ~700KB

Retention policy:
  - Keep daily reports for 90 days (3 months)
  - Keep weekly summaries for 1 year
  - Archive older reports to cold storage (optional)
```

---

## Skill Validation

This skill is correct if it can:
1. Read metrics from `~/.claude/metrics/YYYY-MM-DD/` directory
2. Parse JSON task records and extract key fields
3. Aggregate tokens/cost by role, model, date, task type
4. Calculate daily totals, trends, and anomalies
5. Generate readable daily digest (5-7 key metrics)
6. Flag anomalies (high-cost, low-quality, high-escalation)
7. Identify A/B test opportunities
8. Compare actual vs. target and report gaps
9. Archive reports to `~/.claude/reports/`
10. Integrate with Orchestrator (Slack/email notifications)
11. Run on schedule (cron) and manually on-demand
