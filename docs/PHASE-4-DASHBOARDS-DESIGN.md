# Phase 4: Advanced Dashboards — Design Document

## Overview

Advanced Dashboards provide rich visualization of token usage trends, cost attribution,
quality metrics, performance data, budget tracking, optimization recommendations, and
anomaly detection across all agents and roles.

## Dashboard Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Dashboard System                             │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Data Layer                               │  │
│  │                                                           │  │
│  │  TimeSeriesStore ──► DashboardDataAPI ──► JSON endpoints │  │
│  │  RecommendationStore                                      │  │
│  │  ForecastStore                                            │  │
│  │  AnomalyStore                                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                       │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                Rendering Layer                            │  │
│  │                                                           │  │
│  │  TerminalDashboard (Rich/Textual — primary)              │  │
│  │  GrafanaDashboard (JSON config — secondary)              │  │
│  │  HTMLReport (static export — tertiary)                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Dashboard Panels

### Dashboard 1: Overview (Home)

**Purpose:** At-a-glance system health and cost status.

```
┌─────────────────────────────────────────────────────────────────┐
│  agentic-engineers Dashboard          [Today: 2026-05-17]       │
├─────────────┬──────────────┬──────────────┬────────────────────┤
│ TODAY'S COST│ TASKS TODAY  │ AVG QUALITY  │ BUDGET STATUS      │
│   $12.45    │     47       │    91.2      │ 62% used ($187.55) │
│ ↑ 8% vs avg │ ↑ 12% vs avg│ ↓ 1.3 pts   │ 11 days remaining  │
├─────────────┴──────────────┴──────────────┴────────────────────┤
│                    Cost Trend (30 days)                         │
│  $20 ┤                                              ╭──╮        │
│  $15 ┤              ╭──╮                     ╭──╮ ╯  ╰──       │
│  $10 ┤──────╮──────╯  ╰──────────────────────╯                 │
│   $5 ┤      ╰──                                                 │
│      └─────────────────────────────────────────────────────────│
│      Apr 17                                          May 17     │
├─────────────────────────────────────────────────────────────────┤
│  ACTIVE ANOMALIES              PENDING RECOMMENDATIONS          │
│  🔴 Cost spike: engineer +45%  💡 Downgrade engineer→haiku     │
│  🟡 Quality drop: QE -8pts     💡 Reduce effort: orchestrator  │
└─────────────────────────────────────────────────────────────────┘
```

### Dashboard 2: Token Usage Trends

**Purpose:** Detailed token consumption analysis over time.

**Panels:**
1. **Daily Token Usage** (line chart, 30-day window)
   - Input tokens, output tokens, cached tokens (stacked)
   - 7-day moving average overlay
   - Anomaly markers (red dots)

2. **Token Usage by Role** (stacked bar chart, daily)
   - Each role as a different color band
   - Shows relative contribution of each role

3. **Token Efficiency** (line chart)
   - `cached_tokens / total_tokens` ratio over time
   - Target line at 20% cache hit rate

4. **Top Token Consumers** (table, today)
   - Task ID, role, model, tokens, cost
   - Sortable by any column

5. **Token Usage Heatmap** (calendar heatmap)
   - Day × hour grid, color = token volume
   - Identifies peak usage patterns

### Dashboard 3: Cost Attribution

**Purpose:** Understand where money is being spent.

**Panels:**
1. **Cost by Role** (pie chart + table)
   - Current month cost breakdown
   - vs. target allocation from AGENTS.md

2. **Cost by Model** (pie chart)
   - Haiku vs. Sonnet vs. Opus split
   - vs. recommended model mix

3. **Cost Trend by Role** (multi-line chart, 30 days)
   - One line per role
   - Highlights roles with increasing cost

4. **Cost per Task by Role** (box plot)
   - Distribution of task costs per role
   - Outlier tasks highlighted

5. **Monthly Cost Attribution Table**
   | Role | Model | Effort | Tasks | Tokens | Cost | % Total |
   |------|-------|--------|-------|--------|------|---------|
   | engineer | haiku | high | 234 | 1.2M | $4.80 | 38.6% |
   | ... | ... | ... | ... | ... | ... | ... |

### Dashboard 4: Quality Trends

**Purpose:** Track quality scores over time to detect degradation.

**Panels:**
1. **Quality Score Trend** (line chart, 30 days)
   - Overall average quality
   - Per-role quality lines
   - Target quality line (90)

2. **Quality Distribution** (histogram)
   - Distribution of quality scores
   - Highlight below-threshold tasks

3. **Quality by Model** (bar chart)
   - Average quality score per model
   - Shows quality-cost tradeoff

4. **Failed/Blocked Task Rate** (line chart)
   - Daily failure rate per role
   - Alert threshold line at 20%

5. **Quality vs. Cost Scatter** (scatter plot)
   - Each task = one dot
   - X = cost, Y = quality
   - Color = role
   - Ideal zone highlighted (high quality, low cost)

### Dashboard 5: Performance Metrics

**Purpose:** Track latency, throughput, and system efficiency.

**Panels:**
1. **Task Duration Distribution** (histogram by role)
   - P50, P95, P99 duration per role
   - Target SLA lines

2. **Throughput** (line chart)
   - Tasks completed per hour
   - Parallel vs. sequential breakdown

3. **Queue Depth** (line chart)
   - Tasks in incoming/processing/done over time
   - Backlog indicator

4. **Parallel Delegation Efficiency** (bar chart)
   - Wall-clock speedup from parallelization
   - Tasks that benefited from parallel delegation

5. **Escalation Rate** (line chart)
   - % of tasks escalated (blocked → senior/lead)
   - By role, over time

### Dashboard 6: Budget Tracking & Forecasting

**Purpose:** Budget status, burn rate, and exhaustion prediction.

**Panels:**
1. **Budget Gauge** (gauge chart)
   - Current spend vs. budget
   - Color: green/yellow/red based on status
   - Days remaining estimate

2. **Daily Burn Rate** (bar chart, 30 days)
   - Daily spend with 7-day moving average
   - Budget daily target line

3. **Forecast: Next 30 Days** (line chart)
   - Historical actuals (solid line)
   - Forecast (dashed line)
   - 80% and 95% confidence intervals (shaded)
   - Budget limit line (red)

4. **Scenario Comparison** (table)
   | Scenario | 30-day Cost | Exhaustion Date | vs. Baseline |
   |---|---|---|---|
   | Baseline | $387 | Jun 28 | — |
   | Optimistic | $310 | Jul 15 | -$77 |
   | Pessimistic | $581 | Jun 14 | +$194 |
   | Model Downgrade | $295 | Jul 22 | -$92 |

5. **Budget Adjustment Recommendation** (callout)
   - "To last through June 30, increase budget to $450 (+12.5%)"

### Dashboard 7: Optimization Recommendations

**Purpose:** Actionable recommendations to reduce cost and improve quality.

**Panels:**
1. **Recommendation Summary** (KPI cards)
   - Total pending recommendations
   - Estimated monthly savings if all accepted
   - Recommendations applied this month
   - Savings realized this month

2. **Recommendations Table** (sortable)
   | Priority | Type | Description | Savings/mo | Confidence | Risk | Action |
   |---|---|---|---|---|---|---|
   | 🔴 High | Model Downgrade | engineer: Sonnet→Haiku | $45 | 87% | Low | Accept |
   | 🟡 Med | Effort Reduce | orchestrator: high→medium | $12 | 72% | Low | Review |

3. **Recommendation History** (line chart)
   - Cumulative savings from applied recommendations
   - Projected savings from pending recommendations

4. **Impact vs. Risk Matrix** (scatter plot)
   - X = risk score, Y = impact score
   - Each dot = one recommendation
   - Quadrant labels: Quick Wins, High Value, Low Priority, Avoid

### Dashboard 8: Anomaly Detection

**Purpose:** Surface and track anomalies requiring attention.

**Panels:**
1. **Active Anomalies** (alert list)
   - Severity icon, type, description, detected time
   - Link to relevant trend chart

2. **Anomaly Timeline** (event chart, 30 days)
   - Timeline with anomaly markers by severity
   - Click to drill down

3. **Anomaly Frequency by Type** (bar chart)
   - Cost spikes, quality drops, token surges, failure rates
   - Last 30 days

4. **Mean Time to Resolve** (KPI)
   - Average time from anomaly detection to resolution
   - Trend over time

## Terminal Dashboard Implementation

### Technology: Rich + Textual

Using Python `rich` library for terminal rendering (already used in the codebase):

```python
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live

class TerminalDashboard:
    """Rich-based terminal dashboard."""
    
    def __init__(self, data_api: DashboardDataAPI):
        self.api = data_api
        self.console = Console()
    
    def render_overview(self) -> Layout:
        """Render the overview dashboard."""
        
    def render_cost_attribution(self, days: int = 30) -> Table:
        """Render cost attribution table."""
        
    def render_quality_trends(self, days: int = 30) -> Panel:
        """Render quality trend panel."""
        
    def live_update(self, refresh_seconds: int = 30) -> None:
        """Live-updating dashboard with auto-refresh."""
        with Live(self.render_overview(), refresh_per_second=1) as live:
            while True:
                time.sleep(refresh_seconds)
                live.update(self.render_overview())
```

### CLI Commands

```bash
# Show overview dashboard
agentic-dashboard

# Show specific dashboard
agentic-dashboard --panel cost          # Cost attribution
agentic-dashboard --panel quality       # Quality trends
agentic-dashboard --panel budget        # Budget & forecasting
agentic-dashboard --panel optimize      # Recommendations
agentic-dashboard --panel anomalies     # Anomaly detection

# Live-updating dashboard (auto-refresh every 30s)
agentic-dashboard --live

# Export to HTML
agentic-dashboard --export html --output report.html

# Date range
agentic-dashboard --panel cost --days 7
agentic-dashboard --panel cost --from 2026-05-01 --to 2026-05-17
```

## Grafana Dashboard (Secondary)

For teams using Grafana, export dashboard JSON configs:

```bash
# Export Grafana dashboard JSON
agentic-dashboard --export grafana --output grafana-dashboards/

# Outputs:
#   grafana-dashboards/overview.json
#   grafana-dashboards/cost-attribution.json
#   grafana-dashboards/quality-trends.json
#   grafana-dashboards/budget-forecasting.json
#   grafana-dashboards/recommendations.json
#   grafana-dashboards/anomalies.json
```

Grafana dashboards use the existing Prometheus exporter (`prometheus_exporter.py`) as data source.

## Dashboard Data API

```python
class DashboardDataAPI:
    """Unified data access layer for all dashboards."""
    
    def get_overview_kpis(self) -> OverviewKPIs:
        """Today's cost, task count, quality, budget status."""
        
    def get_cost_trend(
        self, days: int = 30, role: Optional[str] = None
    ) -> List[TrendPoint]:
        """Daily cost trend data."""
        
    def get_cost_attribution(
        self, month: str
    ) -> CostAttributionData:
        """Cost breakdown by role, model, effort."""
        
    def get_quality_trend(
        self, days: int = 30, role: Optional[str] = None
    ) -> List[TrendPoint]:
        """Daily quality trend data."""
        
    def get_budget_status(self) -> BudgetStatusData:
        """Current budget status with forecast."""
        
    def get_recommendations(
        self, status: str = "pending", limit: int = 20
    ) -> List[Recommendation]:
        """Active optimization recommendations."""
        
    def get_active_anomalies(self) -> List[AnomalyEvent]:
        """Currently active (unresolved) anomalies."""
        
    def get_performance_metrics(
        self, days: int = 7
    ) -> PerformanceMetricsData:
        """Task duration, throughput, queue depth."""
```

## File Layout

```
src/
  skills/
    dashboards/
      SKILL.md
      scripts/
        __init__.py
        data_api.py              # DashboardDataAPI
        terminal/
          __init__.py
          dashboard.py           # TerminalDashboard (Rich)
          panels/
            overview.py
            cost_attribution.py
            quality_trends.py
            performance.py
            budget_forecast.py
            recommendations.py
            anomalies.py
        grafana/
          __init__.py
          exporter.py            # Grafana JSON exporter
          templates/             # Grafana dashboard JSON templates
        html/
          __init__.py
          exporter.py            # Static HTML report exporter
        cli.py
      tests/
        test_data_api.py
        test_terminal_dashboard.py
        test_grafana_exporter.py
```

## Success Criteria

- [ ] TerminalDashboard renders all 8 dashboard panels
- [ ] DashboardDataAPI provides data for all panels
- [ ] Live-updating mode works (30s refresh)
- [ ] Grafana JSON export works for all panels
- [ ] HTML report export works
- [ ] CLI provides all dashboard commands
- [ ] Integrates with Historical Analysis, Forecasting, Optimization Engine
- [ ] 85%+ test coverage (UI rendering is harder to test)
- [ ] Dashboard loads in < 2 seconds
