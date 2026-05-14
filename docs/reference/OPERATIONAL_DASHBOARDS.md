# Operational Dashboards — Metrics Visualization & Monitoring

Reference guide for real-time dashboards visualizing token usage, model performance, quality metrics, and cost optimization.

---

## Part 1: Dashboard Architecture

### Data Pipeline

```
Metrics Collection (Orchestrator, per-task)
  ↓
~/.claude/metrics/YYYY-MM-DD/*.json (per-task records)
~/.claude/metrics/YYYY-MM-DD/session.jsonl (session events)
  ↓
ETL Process (daily cron job):
  - Read *.json files from past 7 days
  - Aggregate by date, role, model
  - Calculate trends (daily, weekly, monthly)
  - Write to metrics database (PostgreSQL or Timestream)
  ↓
Dashboards (Grafana, Superset, or custom)
  - Query metrics database
  - Render real-time/near-real-time charts
  - Alert on anomalies
```

---

## Part 2: Dashboard Layouts

### Dashboard 1: Token Burn (Daily)

**Purpose:** Monitor daily token usage and cost.

**Panels:**

1. **Total Tokens (24h)**
   - Display: 287,400 tokens
   - Comparison: +15% vs. yesterday
   - Sparkline: 7-day trend (should be flat or declining)

2. **Cost ($, 24h)**
   - Display: $2.10
   - Breakdown: 1x=$0.97, 2x=$0.72, 7.5x=$0.41
   - Sparkline: 7-day trend

3. **Token Burn by Model (Pie)**
   - Haiku: 46% ($0.97)
   - Sonnet: 54% ($1.13)
   - Opus: (if used) %

4. **Cost per Quality (Line)**
   - Display: $0.00219 (current)
   - Target: $0.00160 (goal from Model Engineer)
   - Gap: $0.00059 / point (15% over target)
   - Trend: 7 day, 30 day, 90 day

5. **Tokens by Role (Stacked Area)**
   - Engineer: 112K
   - Senior: 98K
   - Lead: 56K
   - Quality: 20K
   - Trend: over 7 days

6. **Efficiency Metric (Gauge)**
   - Quality achieved per $1 spent
   - Display: 428 quality points / $1
   - Target: 625 quality points / $1
   - Status: ⚠️ Needs improvement

**Alerts:**
- Token burn >300K/day: investigate high-cost tasks
- Cost per quality >target by 20%: trigger optimization review

---

### Dashboard 2: Model Performance (Weekly)

**Purpose:** Compare model effectiveness and make upgrade decisions.

**Panels:**

1. **Quality by Model (Box Plot)**
   - X: Haiku, Sonnet, Opus
   - Y: Quality score distribution (min, q1, median, q3, max)
   - Overlay: # of tasks per model
   - Insight: Haiku 88-92, Sonnet 93-96, Opus 97-99

2. **Cost per Quality (Grouped Bar)**
   - X: [low, medium, high] complexity
   - Y: cost_per_quality
   - Grouped by model
   - Target line: $0.0016 (optimal)
   - Insight: Where is each model most/least efficient?

3. **Model Allocation (Pie)**
   - Haiku: 46% (target 60% — need more)
   - Sonnet: 54% (target 35% — too much)
   - Opus: 0% (target 5% for critical only)
   - Recommendation: Shift from Sonnet to Haiku on low-complexity tasks

4. **Escalation Rate by Model (Bar)**
   - Haiku: 12% (escalated to Senior/Lead)
   - Sonnet: 8%
   - Opus: 2%
   - Insight: Haiku sometimes insufficient; Senior Engineer can handle these

5. **Model Accuracy Trend (Line)**
   - Haiku: 89% (stable)
   - Sonnet: 93% (improving)
   - Opus: 96% (very stable)
   - (Measured as: "tasks passed QE / all tasks")

6. **Recommendation Table**
   - "Haiku 4.6 available" — should we upgrade? Expected +2 quality, same cost
   - "Sonnet usage 54%" — too high, should be 35%
   - "New Opus model?" — evaluate on 5 critical tasks

**Alerts:**
- Model X accuracy <80%: investigate why quality degraded
- Any model escalation >20%: may be under-scoped for task type

---

### Dashboard 3: Quality Gates (Real-Time)

**Purpose:** Monitor QE acceptance rates and quality distribution.

**Panels:**

1. **HANDBACK Outcomes (Gauge/KPI)**
   - Accepted: 85% (green)
   - Conditional: 12% (yellow)
   - Rejected: 3% (red — investigate)
   - Target: >90% accept rate (good quality)

2. **QE Voting Distribution (Stacked Bar)**
   - QE-Alice: 20 reviews (15 PASS, 4 CONDITIONAL, 1 REJECT)
   - QE-Bob: 18 reviews (14 PASS, 3 CONDITIONAL, 1 REJECT)
   - QE-Carol: 15 reviews (12 PASS, 2 CONDITIONAL, 1 REJECT)
   - QE-David: 12 reviews (10 PASS, 2 CONDITIONAL, 0 REJECT)
   - Insight: David is most permissive; Alice is strict

3. **Inter-Rater Reliability (Heatmap)**
   - Rows: QE pairs (Alice-Bob, Alice-Carol, etc.)
   - Values: Agreement % (85-95%)
   - Target: >85% (well-calibrated QEs)

4. **Quality Score Distribution (Histogram)**
   - X: Quality score (50-100)
   - Y: # of tasks
   - Distribution: mostly 85-95 (good), few <80 (concerning)

5. **Test Coverage (Box Plot)**
   - X: [low, medium, high] complexity
   - Y: Test coverage %
   - Target line: 85% (minimum)
   - Outliers: Complexity=medium, coverage=72% — flag for review

6. **Rework Rate (Trend)**
   - Daily rework %: [2%, 1%, 3%, 2%, 1%, 4%, 2%]
   - Trend: mostly 1-3% (good)
   - Alert if >5% (systemic issue)

**Alerts:**
- Acceptance rate <85%: QEs may be too strict, review calibration
- Rework rate >5%: Poor task planning or model selection

---

### Dashboard 4: A/B Tests (Active Experiments)

**Purpose:** Monitor ongoing A/B tests and declare winners.

**Panels:**

1. **Test Progress (Horizontal Bar)**
   - Test: "haiku-vs-sonnet_auth_2026-04"
   - Progress: ████████░░░░░░░░░░ (8/5 samples per arm — complete!)
   - Control (Haiku): n=5, quality=90±2, cost=$0.13
   - Test (Sonnet): n=5, quality=93±2, cost=$0.16
   - Status: Results analyzed; Control wins

2. **Test Results (Comparison Table)**
   - Test ID | Control | Test | Winner | P-value | Confidence
   - haiku-vs-sonnet | q=90, $0.13 | q=93, $0.16 | Control | 0.08 | 92%
   - effort-max-vs-med | q=95, $0.22 | q=93, $0.15 | Test | 0.03 | 97%
   - Insight: Test 1 favors control (cost); Test 2 favors test (savings)

3. **Effect Size (Bubble Chart)**
   - X: quality difference (control - test)
   - Y: cost difference (control - test)
   - Size: sample size (n)
   - Haiku-vs-Sonnet: (-3 quality, +$0.03 cost, n=10) → Control wins
   - Effort: (+2 quality, -$0.07 cost, n=10) → Test wins (clear winner)

4. **Scheduled Tests (Timeline)**
   - 2026-05-01: haiku-4.6-eval (estimate 2 weeks)
   - 2026-05-08: opus-downgrade-test (estimate 2 weeks)
   - 2026-05-15: new-effort-levels (estimate 1 week)
   - Insight: 3 tests queued; start first when quota available

5. **Historical Test Results (Table)**
   - Completed tests from past month
   - Winner column: "Control", "Test", "Inconclusive"
   - Adoption status: "Implemented", "Rejected", "Monitoring"

**Alerts:**
- Test sample <n_target and duration >50% of max: accelerate or extend
- P-value >0.05 and sample <n_min: may need more data
- Winner declared but not implemented: flag for Orchestrator

---

### Dashboard 5: Cost Optimization (Strategic)

**Purpose:** Identify cost reduction opportunities and track progress vs. targets.

**Panels:**

1. **Cost Trend (Area Chart)**
   - Y: Daily cost ($)
   - Current: $2.10/day (30-day avg)
   - Baseline (3 months ago): $3.50/day
   - Target (3 months ahead): $1.50/day
   - Progress: -40% toward target (green)

2. **Cost Breakdown (Waterfall)**
   - Start: $3.50 (baseline)
   - Model optimization (Haiku usage +30%): -$0.40
   - Effort tuning (medium vs. high): -$0.30
   - A/B test results: -$0.20
   - New model evaluation: TBD
   - End: $2.10 (current)
   - Opportunity: $0.60 (to reach $1.50 target)

3. **Cost per Task (Scatter)**
   - X: Task complexity (low, medium, high)
   - Y: Cost ($)
   - Point size: frequency
   - Outliers: High-complexity tasks at $0.30+ (investigate)
   - Insight: Majority within $0.12-0.18 range

4. **Model Shift Projection (Line)**
   - Current allocation: Haiku 46%, Sonnet 54%, Opus 0%
   - Target allocation: Haiku 60%, Sonnet 35%, Opus 5%
   - Projected cost: $1.75 (at target) vs. $2.10 (current)
   - Savings: $0.35/day = ~$128/month

5. **Recommendation Pipeline (Table)**
   - Opportunity | Savings | Effort | Status
   - Upgrade Haiku 4.6 | $0.10/day | Low | Pending model release
   - Shift Sonnet→Haiku on low-complexity | $0.15/day | Medium | Run A/B test
   - Downgrade Opus→Sonnet on architecture | $0.20/day | High | Requires eval
   - Reduce test coverage to 80% (from 85%) | $0.05/day | Low | Risky; skip
   - **Total opportunity: $0.50/day ($182/month)**

**Alerts:**
- Cost trending up >5%/week: investigate why (new models? more tasks?)
- Opportunity unfunded for >2 weeks: escalate to management
- Target miss >20%: revise projection

---

## Part 3: Alerting Rules

### Critical Alerts (Page On-Call)

```
Token Burn Alert:
  Trigger: Daily tokens > 400K (25% over normal)
  Action: Page on-call engineer, investigate high-cost tasks
  Resolution: Identify root cause (new model? more complex tasks?)

Quality Below Threshold:
  Trigger: Avg quality <85 for any model
  Action: Page Senior Engineer, review recent HANDBACK rejections
  Resolution: Retrain model or escalate task type

Acceptance Rate Below Target:
  Trigger: QE acceptance <80% for >3 days
  Action: Alert QE Lead, may indicate over-strict calibration
  Resolution: QE calibration meeting, review Tier 1 definition
```

### Warning Alerts (Slack Notification)

```
Cost Trending Up:
  Trigger: 3-day trend shows +10% daily cost
  Action: Notify Model Engineer, check if model mix changed
  Resolution: May be temporary (complex tasks), monitor next 3 days

Test Approaching Completion:
  Trigger: A/B test sample size ≥90% of target
  Action: Notify Model Engineer, prepare analysis
  Resolution: Run analysis, decide implement/reject

Model Accuracy Declining:
  Trigger: Model X accuracy down >5 points over 2 weeks
  Action: Notify Orchestrator, review task assignments to that model
  Resolution: Check if task complexity shifted, may need re-routing
```

### Informational Alerts (Daily Email)

```
Daily Digest (sent 9 AM):
  - Yesterday's cost: $2.10
  - Quality average: 91/100
  - Acceptance rate: 85%
  - Active tests: 2
  - Biggest task: task_X (28K tokens)
  - Recommendation: Monitor A/B test haiku-vs-sonnet (n=5 per arm done)
```

---

## Part 4: Implementation Options

### Option A: Self-Hosted (Grafana + PostgreSQL)

```
Architecture:
  ~/.claude/metrics/*.json (source)
    ↓
  ETL script (Python, run daily)
    ↓
  PostgreSQL (metrics DB)
    ↓
  Grafana (visualization)

Pros:
  - Full control, privacy, no external dependencies
  - Can run on local machine or EC2
  - Grafana is open-source, free

Cons:
  - Requires PostgreSQL setup + maintenance
  - Grafana requires configuration
  - No built-in alerting (need to add separately)

Cost: ~$5-10/month if self-hosted

Setup Time: 2-3 hours
```

### Option B: SaaS (Datadog, New Relic)

```
Architecture:
  ~/.claude/metrics/*.json (source)
    ↓
  Agent (ship metrics to Datadog)
    ↓
  Datadog (hosted, managed)
    ↓
  Dashboards + Alerts

Pros:
  - Zero setup, fully managed
  - Great alerting + integrations
  - Reliable infrastructure

Cons:
  - Monthly cost ($15-50/month)
  - Data leaves local machine (privacy concern)
  - Overkill if we have <10 metrics

Cost: $20-30/month
```

### Option C: Lightweight (Google Sheets + Scripts)

```
Architecture:
  ~/.claude/metrics/*.json (source)
    ↓
  Google Apps Script (automate data sync)
    ↓
  Google Sheets (data warehouse)
    ↓
  Sheets charts (visualization)

Pros:
  - Minimal setup, free
  - Familiar tools (Sheets)
  - Can share easily

Cons:
  - Limited to ~10K rows (won't scale long-term)
  - Charts are basic
  - No real alerting

Cost: $0 (if using free Sheets)
```

### Recommendation

**Start with Option C (Google Sheets)** for 1-2 months (setup <1 hour).
**Migrate to Option A (Grafana) once >30 days of data** (setup 3 hours, one-time).
**Only adopt Option B if volume scales 10x** (enterprise-scale monitoring).

---

## Part 5: Key Metrics to Track

### Token Efficiency Metrics

```json
{
  "tokens_per_quality_point": 224,
  "cost_per_quality_point": 0.00219,
  "quality_per_dollar_spent": 428,
  "tokens_per_minute": 229
}
```

### Model Performance Metrics

```json
{
  "by_model": {
    "haiku-4.5": {
      "task_count": 9,
      "avg_quality": 89,
      "avg_cost": 0.12,
      "escalation_rate": 0.12,
      "accuracy": 0.89
    }
  }
}
```

### Quality Metrics

```json
{
  "acceptance_rate": 0.85,
  "test_coverage_avg": 0.87,
  "rework_rate": 0.02,
  "inter_rater_reliability": 0.88
}
```

### Cost Metrics

```json
{
  "daily_cost": 2.10,
  "cost_vs_target": 1.31,
  "cost_trend_7day": 0.05,
  "cost_opportunity": 0.60
}
```

---

## Conclusion

Operational dashboards provide visibility into:
1. **Token burn** — Are we efficient?
2. **Model performance** — Which models work best?
3. **Quality gates** — Is QE calibrated?
4. **A/B tests** — Do experiments reach conclusion?
5. **Cost optimization** — Are we on track for goals?

Start with Google Sheets; graduate to Grafana as data scales.
