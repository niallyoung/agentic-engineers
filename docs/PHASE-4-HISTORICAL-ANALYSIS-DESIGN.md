# Phase 4: Historical Analysis System — Design Document

## Overview

The Historical Analysis System provides time-series storage, trend analysis, anomaly detection,
and reporting for token usage, cost, and quality metrics across all agents and roles.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Historical Analysis System                    │
│                                                                  │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────────┐  │
│  │  Collectors │───►│  Time-Series │───►│  Analysis Engine  │  │
│  │             │    │    Store     │    │                   │  │
│  │ TokenTracker│    │ (SQLite TSB) │    │ TrendAnalyzer     │  │
│  │ BudgetCheck │    │             │    │ AnomalyDetector   │  │
│  │ QE Feedback │    │ Hourly agg  │    │ PatternMatcher    │  │
│  │ HANDBACK    │    │ Daily agg   │    │                   │  │
│  └─────────────┘    │ Weekly agg  │    └────────┬──────────┘  │
│                     │ Monthly agg │             │              │
│                     └──────────────┘             ▼              │
│                                         ┌───────────────────┐  │
│                                         │  Report Generator │  │
│                                         │                   │  │
│                                         │ Daily summary     │  │
│                                         │ Weekly trends     │  │
│                                         │ Anomaly alerts    │  │
│                                         └───────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Data Storage

### Storage Backend: SQLite with WAL mode

SQLite is chosen over InfluxDB/TimescaleDB because:
- Zero infrastructure dependencies (self-contained)
- Sufficient for expected data volumes (<10M rows/year)
- Already used by OpenCode (`opencode.db`)
- Easy to query with standard SQL
- Portable (single file, easy backup)

**Database location:** `~/.local/share/agentic-engineers/history.db`

### Schema

```sql
-- Raw task metrics (one row per task execution)
CREATE TABLE task_metrics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         TEXT NOT NULL,
    timestamp       INTEGER NOT NULL,  -- Unix epoch seconds
    date            TEXT NOT NULL,     -- YYYY-MM-DD (for partitioning)
    role            TEXT NOT NULL,     -- engineer, senior_engineer, etc.
    model           TEXT NOT NULL,     -- claude-haiku-4-5, etc.
    effort          TEXT NOT NULL,     -- low, medium, high, extra_high
    input_tokens    INTEGER NOT NULL DEFAULT 0,
    output_tokens   INTEGER NOT NULL DEFAULT 0,
    cached_tokens   INTEGER NOT NULL DEFAULT 0,
    cost_usd        REAL NOT NULL DEFAULT 0.0,
    quality_score   REAL,              -- 0-100, nullable (not always available)
    duration_mins   REAL,              -- task duration in minutes
    status          TEXT NOT NULL,     -- complete, failed, partial, blocked
    parent_task_id  TEXT,              -- for parallel delegation tracking
    session_id      TEXT,
    UNIQUE(task_id)
);

-- Hourly aggregations
CREATE TABLE hourly_agg (
    hour            TEXT NOT NULL,     -- YYYY-MM-DD HH (UTC)
    role            TEXT NOT NULL,
    model           TEXT NOT NULL,
    task_count      INTEGER NOT NULL DEFAULT 0,
    input_tokens    INTEGER NOT NULL DEFAULT 0,
    output_tokens   INTEGER NOT NULL DEFAULT 0,
    cached_tokens   INTEGER NOT NULL DEFAULT 0,
    cost_usd        REAL NOT NULL DEFAULT 0.0,
    avg_quality     REAL,
    avg_duration    REAL,
    failed_count    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (hour, role, model)
);

-- Daily aggregations
CREATE TABLE daily_agg (
    date            TEXT NOT NULL,     -- YYYY-MM-DD
    role            TEXT NOT NULL,
    model           TEXT NOT NULL,
    task_count      INTEGER NOT NULL DEFAULT 0,
    input_tokens    INTEGER NOT NULL DEFAULT 0,
    output_tokens   INTEGER NOT NULL DEFAULT 0,
    cached_tokens   INTEGER NOT NULL DEFAULT 0,
    cost_usd        REAL NOT NULL DEFAULT 0.0,
    avg_quality     REAL,
    p50_quality     REAL,
    p95_quality     REAL,
    avg_duration    REAL,
    failed_count    INTEGER NOT NULL DEFAULT 0,
    blocked_count   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (date, role, model)
);

-- Weekly aggregations
CREATE TABLE weekly_agg (
    week            TEXT NOT NULL,     -- YYYY-WNN (ISO week)
    role            TEXT NOT NULL,
    model           TEXT NOT NULL,
    task_count      INTEGER NOT NULL DEFAULT 0,
    total_cost_usd  REAL NOT NULL DEFAULT 0.0,
    avg_quality     REAL,
    trend_quality   REAL,              -- week-over-week quality delta
    trend_cost      REAL,              -- week-over-week cost delta
    PRIMARY KEY (week, role, model)
);

-- Anomaly events
CREATE TABLE anomaly_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at     INTEGER NOT NULL,  -- Unix epoch
    anomaly_type    TEXT NOT NULL,     -- cost_spike, quality_drop, token_surge, etc.
    severity        TEXT NOT NULL,     -- low, medium, high, critical
    role            TEXT,
    model           TEXT,
    metric_name     TEXT NOT NULL,
    expected_value  REAL NOT NULL,
    actual_value    REAL NOT NULL,
    deviation_pct   REAL NOT NULL,
    description     TEXT NOT NULL,
    resolved_at     INTEGER,
    resolution_note TEXT
);

-- Indexes for common queries
CREATE INDEX idx_task_metrics_date ON task_metrics(date);
CREATE INDEX idx_task_metrics_role ON task_metrics(role, date);
CREATE INDEX idx_task_metrics_model ON task_metrics(model, date);
CREATE INDEX idx_anomaly_events_type ON anomaly_events(anomaly_type, detected_at);
```

## Components

### 1. MetricsCollector

Ingests data from existing sources:

```python
class MetricsCollector:
    """Collects metrics from existing system components."""
    
    def collect_from_handback(self, handback_yaml: dict) -> TaskMetrics:
        """Parse HANDBACK block into TaskMetrics."""
        
    def collect_from_token_tracker(self, stats: TokenStats) -> List[TaskMetrics]:
        """Convert TokenTracker stats into historical records."""
        
    def collect_from_metrics_dir(self, metrics_dir: Path) -> List[TaskMetrics]:
        """Scan artifacts/metrics/ YAML files and ingest."""
        
    def collect_from_opencode_db(self, db_path: Path) -> List[TaskMetrics]:
        """Read session data from opencode.db for token data."""
```

### 2. TimeSeriesStore

Manages the SQLite database with aggregation:

```python
class TimeSeriesStore:
    """SQLite-backed time-series storage with automatic aggregation."""
    
    def insert_task(self, metrics: TaskMetrics) -> None:
        """Insert raw task metrics and trigger aggregation update."""
        
    def aggregate_hourly(self, hour: str) -> None:
        """Recompute hourly aggregation for given hour."""
        
    def aggregate_daily(self, date: str) -> None:
        """Recompute daily aggregation for given date."""
        
    def query_trend(
        self,
        metric: str,
        role: Optional[str],
        model: Optional[str],
        start_date: str,
        end_date: str,
        granularity: str = "daily"
    ) -> List[TrendPoint]:
        """Query time-series trend data."""
        
    def query_top_costs(self, date: str, limit: int = 10) -> List[CostRecord]:
        """Top N most expensive tasks for a given date."""
```

### 3. TrendAnalyzer

Statistical analysis of historical data:

```python
class TrendAnalyzer:
    """Analyzes trends in historical metrics."""
    
    def compute_moving_average(
        self, values: List[float], window: int = 7
    ) -> List[float]:
        """7-day moving average for smoothing."""
        
    def compute_week_over_week(
        self, metric: str, role: str
    ) -> float:
        """Week-over-week percentage change."""
        
    def compute_month_over_month(
        self, metric: str, role: str
    ) -> float:
        """Month-over-month percentage change."""
        
    def identify_patterns(
        self, data: List[TrendPoint]
    ) -> List[Pattern]:
        """Identify recurring patterns (daily peaks, weekly cycles)."""
        
    def compute_cost_attribution(
        self, date: str
    ) -> Dict[str, float]:
        """Cost breakdown by role, model, effort for a given date."""
```

### 4. AnomalyDetector

Detects statistical outliers and anomalies:

```python
class AnomalyDetector:
    """Detects anomalies using statistical methods."""
    
    # Detection methods
    METHODS = ["zscore", "iqr", "rolling_std"]
    
    def detect_cost_spike(
        self, role: str, current_cost: float, window_days: int = 14
    ) -> Optional[AnomalyEvent]:
        """Detect if today's cost is anomalously high vs. 14-day baseline."""
        
    def detect_quality_drop(
        self, role: str, current_quality: float, window_days: int = 7
    ) -> Optional[AnomalyEvent]:
        """Detect if quality score dropped significantly."""
        
    def detect_token_surge(
        self, model: str, current_tokens: int, window_days: int = 7
    ) -> Optional[AnomalyEvent]:
        """Detect anomalous token consumption for a model."""
        
    def detect_failure_rate_spike(
        self, role: str, failure_rate: float
    ) -> Optional[AnomalyEvent]:
        """Detect if task failure rate is unusually high."""
        
    def _zscore(self, value: float, baseline: List[float]) -> float:
        """Compute Z-score of value against baseline distribution."""
```

**Anomaly Thresholds:**

| Anomaly Type | Threshold | Severity |
|---|---|---|
| Cost spike | >2σ above 14-day mean | medium |
| Cost spike | >3σ above 14-day mean | high |
| Quality drop | >10 points below 7-day mean | medium |
| Quality drop | >20 points below 7-day mean | high |
| Token surge | >2.5σ above 7-day mean | medium |
| Failure rate | >20% for any role | medium |
| Failure rate | >40% for any role | critical |

### 5. ReportGenerator

Generates human-readable and machine-readable reports:

```python
class ReportGenerator:
    """Generates historical analysis reports."""
    
    def daily_summary(self, date: str) -> DailySummaryReport:
        """Daily cost, quality, and task count summary."""
        
    def weekly_trend_report(self, week: str) -> WeeklyTrendReport:
        """Week-over-week trends with top movers."""
        
    def monthly_cost_attribution(self, month: str) -> CostAttributionReport:
        """Monthly cost breakdown by role, model, effort."""
        
    def anomaly_report(
        self, start_date: str, end_date: str
    ) -> AnomalyReport:
        """All anomalies detected in a date range."""
        
    def quality_trend_report(
        self, role: str, days: int = 30
    ) -> QualityTrendReport:
        """Quality score trends for a specific role."""
```

## Integration Points

### With Existing System

| Component | Integration |
|---|---|
| `TokenTracker` | Read `TokenStats` → insert into `task_metrics` |
| `BudgetChecker` | Read budget events → anomaly detection |
| HANDBACK YAML files | Parse `artifacts/metrics/*.yaml` → ingest |
| `tokenadvisor` skill | Consume daily aggregations for analysis |
| `metrics-etl` skill | Export aggregations to Prometheus format |

### Data Flow

```
HANDBACK emitted
    │
    ▼
MetricsCollector.collect_from_handback()
    │
    ▼
TimeSeriesStore.insert_task()
    │
    ├──► aggregate_hourly()
    ├──► aggregate_daily()
    │
    ▼
AnomalyDetector.run_all_checks()
    │
    ├──► AnomalyEvent created if threshold exceeded
    │
    ▼
ReportGenerator (scheduled: daily at 00:05 UTC)
    │
    ├──► daily_summary.json → artifacts/reports/
    └──► anomaly_alerts → voice-notify / email
```

## CLI Interface

```bash
# Query cost trend for last 30 days
agentic-history trend --metric cost_usd --days 30

# Query quality trend by role
agentic-history trend --metric quality_score --role senior_engineer --days 14

# Show anomalies in last 7 days
agentic-history anomalies --days 7 --severity medium

# Generate daily summary report
agentic-history report daily --date 2026-05-17

# Generate monthly cost attribution
agentic-history report monthly --month 2026-05

# Ingest metrics from artifacts/
agentic-history ingest --source artifacts/metrics/
```

## File Layout

```
src/
  skills/
    historical-analysis/
      SKILL.md
      scripts/
        __init__.py
        collector.py          # MetricsCollector
        store.py              # TimeSeriesStore (SQLite)
        trend_analyzer.py     # TrendAnalyzer
        anomaly_detector.py   # AnomalyDetector
        report_generator.py   # ReportGenerator
        cli.py                # CLI entry point
      tests/
        test_collector.py
        test_store.py
        test_trend_analyzer.py
        test_anomaly_detector.py
        test_report_generator.py
```

## Performance Targets

| Operation | Target |
|---|---|
| Insert task metrics | <5ms |
| Query daily trend (30 days) | <50ms |
| Anomaly detection (all checks) | <200ms |
| Daily report generation | <1s |
| Ingest 1000 HANDBACK files | <10s |

## Success Criteria

- [ ] SQLite schema created with all tables and indexes
- [ ] MetricsCollector ingests from HANDBACK YAML files
- [ ] TimeSeriesStore provides daily/weekly/monthly aggregations
- [ ] TrendAnalyzer computes week-over-week and month-over-month deltas
- [ ] AnomalyDetector detects cost spikes, quality drops, token surges
- [ ] ReportGenerator produces daily and weekly reports
- [ ] CLI provides query interface
- [ ] All performance targets met
- [ ] 90%+ test coverage
