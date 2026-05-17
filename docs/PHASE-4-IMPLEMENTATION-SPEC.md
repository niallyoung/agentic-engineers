# Phase 4: Implementation Specification

## Overview

This document provides the detailed implementation specification for all Phase 4 components:
Historical Analysis, Optimization Engine, Cost Forecasting, and Advanced Dashboards.

---

## Implementation Order

Phase 4 components have the following dependency chain:

```
Historical Analysis System (foundation)
    │
    ├──► Optimization Engine (depends on historical data)
    ├──► Cost Forecasting (depends on historical data)
    │
    └──► Advanced Dashboards (depends on all three above)
```

**Recommended implementation order:**
1. Historical Analysis System (Week 1-2)
2. Optimization Engine (Week 2-3, parallel with Forecasting)
3. Cost Forecasting (Week 2-3, parallel with Optimization)
4. Advanced Dashboards (Week 4)

---

## Phase 4.1: Historical Analysis System

### Sprint 1 (Days 1-3): Database & Ingestion

**Deliverables:**
- `src/skills/historical-analysis/scripts/store.py` — TimeSeriesStore
- `src/skills/historical-analysis/scripts/collector.py` — MetricsCollector
- `src/skills/historical-analysis/tests/test_store.py`
- `src/skills/historical-analysis/tests/test_collector.py`

**Implementation steps:**

1. Create SQLite schema (all tables + indexes)
2. Implement `TimeSeriesStore`:
   - `insert_task(metrics: TaskMetrics) -> None`
   - `aggregate_hourly(hour: str) -> None`
   - `aggregate_daily(date: str) -> None`
   - `query_trend(metric, role, model, start, end, granularity) -> List[TrendPoint]`
   - `query_top_costs(date, limit) -> List[CostRecord]`
3. Implement `MetricsCollector`:
   - `collect_from_handback(yaml: dict) -> TaskMetrics`
   - `collect_from_metrics_dir(path: Path) -> List[TaskMetrics]`
   - `collect_from_opencode_db(path: Path) -> List[TaskMetrics]`
4. Write tests (90%+ coverage)

**Acceptance criteria:**
- Insert 1000 task metrics in < 1 second
- Query 30-day trend in < 50ms
- Aggregations are idempotent (safe to re-run)
- All tests pass

### Sprint 2 (Days 4-6): Analysis & Anomaly Detection

**Deliverables:**
- `src/skills/historical-analysis/scripts/trend_analyzer.py`
- `src/skills/historical-analysis/scripts/anomaly_detector.py`
- `src/skills/historical-analysis/tests/test_trend_analyzer.py`
- `src/skills/historical-analysis/tests/test_anomaly_detector.py`

**Implementation steps:**

1. Implement `TrendAnalyzer`:
   - `compute_moving_average(values, window=7) -> List[float]`
   - `compute_week_over_week(metric, role) -> float`
   - `compute_month_over_month(metric, role) -> float`
   - `compute_cost_attribution(date) -> Dict[str, float]`
2. Implement `AnomalyDetector`:
   - `detect_cost_spike(role, current_cost, window_days=14) -> Optional[AnomalyEvent]`
   - `detect_quality_drop(role, current_quality, window_days=7) -> Optional[AnomalyEvent]`
   - `detect_token_surge(model, current_tokens, window_days=7) -> Optional[AnomalyEvent]`
   - `detect_failure_rate_spike(role, failure_rate) -> Optional[AnomalyEvent]`
   - `_zscore(value, baseline) -> float`
3. Write tests with synthetic data

**Acceptance criteria:**
- Z-score anomaly detection correctly identifies 2σ and 3σ outliers
- Moving average smoothing works correctly for 7-day window
- Week-over-week calculation handles missing days gracefully

### Sprint 3 (Days 7-8): Reports & CLI

**Deliverables:**
- `src/skills/historical-analysis/scripts/report_generator.py`
- `src/skills/historical-analysis/scripts/cli.py`
- `src/skills/historical-analysis/SKILL.md`

**Implementation steps:**

1. Implement `ReportGenerator`:
   - `daily_summary(date) -> DailySummaryReport`
   - `weekly_trend_report(week) -> WeeklyTrendReport`
   - `monthly_cost_attribution(month) -> CostAttributionReport`
   - `anomaly_report(start, end) -> AnomalyReport`
2. Implement CLI (`agentic-history` command)
3. Write SKILL.md documentation
4. Integration test: ingest real `artifacts/metrics/` files

---

## Phase 4.2: Optimization Engine

### Sprint 1 (Days 1-3): Core Engine & Advisors

**Deliverables:**
- `src/skills/optimization-engine/scripts/engine.py`
- `src/skills/optimization-engine/scripts/advisors/model_downgrade.py`
- `src/skills/optimization-engine/scripts/advisors/effort_reducer.py`
- `src/skills/optimization-engine/scripts/scoring.py`

**Implementation steps:**

1. Implement `Recommendation` dataclass with all fields
2. Implement `ModelDowngradeAdvisor`:
   - Query historical data for role+model combinations
   - Identify cases where quality ≥ 90 on expensive model
   - Check if cheaper model achieves ≥ 85 quality on similar tasks
   - Generate recommendation with evidence
3. Implement `EffortReducerAdvisor`:
   - Identify roles using < 40% of effort budget
   - Calculate savings from effort reduction
4. Implement scoring: `ImpactScorer`, `ConfidenceScorer`, `RiskAssessor`
5. Implement `RecommendationEngine.generate_recommendations()`

### Sprint 2 (Days 4-5): Additional Advisors & Integration

**Deliverables:**
- `src/skills/optimization-engine/scripts/advisors/decomposition.py`
- `src/skills/optimization-engine/scripts/advisors/parallelization.py`
- `src/skills/optimization-engine/scripts/advisors/caching.py`
- `src/skills/optimization-engine/scripts/orchestrator_integration.py`
- `src/skills/optimization-engine/scripts/store.py`

**Implementation steps:**

1. Implement remaining advisors (decomposition, parallelization, caching)
2. Implement `RecommendationStore` (SQLite, stores recommendations + outcomes)
3. Implement `OrchestratorIntegration`:
   - `get_routing_overrides() -> Dict[str, RoutingOverride]`
   - `apply_model_override(role, model, effort, expires_at)`
   - `record_outcome(rec_id, task_id, quality_score, cost_usd)`
4. Implement CLI (`agentic-optimize` command)

---

## Phase 4.3: Cost Forecasting

### Sprint 1 (Days 1-3): Forecasting Methods

**Deliverables:**
- `src/skills/cost-forecasting/scripts/forecasters/linear.py`
- `src/skills/cost-forecasting/scripts/forecasters/exponential.py`
- `src/skills/cost-forecasting/scripts/forecasters/seasonal.py`
- `src/skills/cost-forecasting/scripts/forecasters/ensemble.py`
- `src/skills/cost-forecasting/tests/test_forecasters.py`

**Implementation steps:**

1. Implement `LinearTrendForecaster`:
   - Ordinary least squares regression
   - Confidence intervals via prediction error
2. Implement `ExponentialSmoothingForecaster`:
   - Holt-Winters double exponential smoothing
   - Alpha/beta parameters with sensible defaults
3. Implement `SeasonalDecompositionForecaster`:
   - Simple additive decomposition (trend + seasonal + residual)
   - 7-day seasonal period
4. Implement `EnsembleForecaster`:
   - Fit all three methods
   - Weight by backtesting MAE (7-day holdout)
   - Combine predictions with weighted average
5. Test with synthetic data (linear, exponential, seasonal patterns)

**Acceptance criteria:**
- MAPE < 15% on synthetic linear data (7-day horizon)
- MAPE < 20% on synthetic seasonal data (7-day horizon)
- Ensemble outperforms all individual methods on mixed data

### Sprint 2 (Days 4-5): Budget Integration & CLI

**Deliverables:**
- `src/skills/cost-forecasting/scripts/scenario_engine.py`
- `src/skills/cost-forecasting/scripts/budget_integration.py`
- `src/skills/cost-forecasting/scripts/accuracy_tracker.py`
- `src/skills/cost-forecasting/scripts/cli.py`

**Implementation steps:**

1. Implement `ScenarioEngine` with 5 built-in scenarios
2. Implement `ExhaustionPredictor`
3. Implement `BudgetAdjustmentAdvisor`
4. Implement `AccuracyTracker` (store forecasts, compare to actuals)
5. Implement CLI (`agentic-forecast` command)
6. Integrate with existing `BudgetChecker`

---

## Phase 4.4: Advanced Dashboards

### Sprint 1 (Days 1-2): Data API

**Deliverables:**
- `src/skills/dashboards/scripts/data_api.py`
- `src/skills/dashboards/tests/test_data_api.py`

**Implementation steps:**

1. Implement `DashboardDataAPI` with all data access methods
2. Wire up to Historical Analysis, Optimization Engine, Forecasting
3. Add caching layer (5-minute TTL for expensive queries)
4. Test with synthetic data

### Sprint 2 (Days 3-5): Terminal Dashboard

**Deliverables:**
- `src/skills/dashboards/scripts/terminal/dashboard.py`
- `src/skills/dashboards/scripts/terminal/panels/` (all 8 panels)
- `src/skills/dashboards/scripts/cli.py`

**Implementation steps:**

1. Implement `TerminalDashboard` using `rich`:
   - Overview panel (KPIs + cost trend + anomalies)
   - Cost attribution panel (table + breakdown)
   - Quality trends panel (trend + distribution)
   - Budget & forecasting panel (gauge + forecast chart)
   - Recommendations panel (table + impact matrix)
   - Anomalies panel (alert list + timeline)
2. Implement live-updating mode (`--live` flag)
3. Implement CLI (`agentic-dashboard` command)

### Sprint 3 (Days 6-7): Grafana & HTML Export

**Deliverables:**
- `src/skills/dashboards/scripts/grafana/exporter.py`
- `src/skills/dashboards/scripts/grafana/templates/` (JSON templates)
- `src/skills/dashboards/scripts/html/exporter.py`

**Implementation steps:**

1. Create Grafana dashboard JSON templates for all 8 panels
2. Implement `GrafanaExporter` to populate templates with current config
3. Implement `HTMLExporter` for static report generation
4. Test export commands

---

## Shared Infrastructure

### Configuration File

`config/phase4.yaml`:
```yaml
historical_analysis:
  db_path: ~/.local/share/agentic-engineers/history.db
  retention_days: 365
  aggregation_schedule: "0 1 * * *"  # Daily at 01:00 UTC

optimization_engine:
  analysis_schedule: "0 6 * * *"    # Daily at 06:00 UTC
  min_sample_size: 10
  min_confidence: 0.6
  auto_apply: false                  # Require human approval

cost_forecasting:
  default_horizon_days: 30
  min_history_days: 7
  accuracy_tracking: true

dashboards:
  default_days: 30
  live_refresh_seconds: 30
  grafana_output_dir: grafana-dashboards/
```

### Shared Data Models

`src/skills/shared/models.py`:
```python
@dataclass
class TaskMetrics:
    task_id: str
    timestamp: datetime
    role: str
    model: str
    effort: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    cost_usd: float
    quality_score: Optional[float]
    duration_mins: Optional[float]
    status: str
    parent_task_id: Optional[str] = None
    session_id: Optional[str] = None

@dataclass
class TrendPoint:
    date: str
    value: float
    label: Optional[str] = None

@dataclass
class AnomalyEvent:
    detected_at: datetime
    anomaly_type: str
    severity: str
    role: Optional[str]
    model: Optional[str]
    metric_name: str
    expected_value: float
    actual_value: float
    deviation_pct: float
    description: str
```

---

## Testing Strategy

### Unit Tests (per component)
- Each class tested in isolation with mocked dependencies
- Synthetic data generators for time-series testing
- Property-based tests for statistical functions (hypothesis library)

### Integration Tests
- End-to-end: ingest HANDBACK → store → analyze → recommend → display
- Test with real `artifacts/metrics/` data (if available)
- Test with synthetic 90-day dataset

### Performance Tests
- Insert 10,000 task metrics: < 10 seconds
- Query 365-day trend: < 500ms
- Generate all recommendations: < 5 seconds
- Dashboard render: < 2 seconds

### Coverage Targets
| Component | Target |
|---|---|
| Historical Analysis | 90% |
| Optimization Engine | 90% |
| Cost Forecasting | 90% |
| Dashboards (data layer) | 85% |
| Dashboards (rendering) | 70% |

---

## Rollout Plan

### Week 1: Historical Analysis System
- Days 1-3: Database + ingestion
- Days 4-6: Analysis + anomaly detection
- Days 7-8: Reports + CLI
- Day 9: Integration testing
- Day 10: Documentation + SKILL.md

### Week 2: Optimization Engine + Cost Forecasting (parallel)
- Days 1-3: Core engine + advisors (optimization) + forecasters (forecasting)
- Days 4-5: Integration + CLI (both)
- Day 6: Cross-component integration testing

### Week 3: Advanced Dashboards
- Days 1-2: Data API
- Days 3-5: Terminal dashboard (all 8 panels)
- Days 6-7: Grafana + HTML export

### Week 4: Integration & Polish
- End-to-end testing
- Performance optimization
- Documentation
- Demo preparation

---

## Dependencies

### Python Libraries (new)
```
# Add to requirements.txt / pyproject.toml
numpy>=1.24.0          # Statistical computations
scipy>=1.10.0          # Linear regression, statistical tests
rich>=13.0.0           # Terminal dashboard (may already be present)
```

### No New Infrastructure Required
- SQLite: built into Python stdlib
- No InfluxDB, TimescaleDB, or external time-series DB
- No new services to deploy
- No new API keys or credentials

---

## Success Criteria (Phase 4 Complete)

### Functional
- [ ] Historical Analysis: ingests 90 days of data, queries trends, detects anomalies
- [ ] Optimization Engine: generates ≥1 actionable recommendation from real data
- [ ] Cost Forecasting: MAPE < 15% on 7-day horizon (validated)
- [ ] Dashboards: all 8 panels render correctly in terminal

### Quality
- [ ] All components: 90%+ test coverage (85% for dashboard rendering)
- [ ] All performance targets met
- [ ] No new security vulnerabilities (no secrets, safe YAML loading)
- [ ] All SKILL.md documentation complete

### Integration
- [ ] Historical Analysis integrates with existing TokenTracker + HANDBACK files
- [ ] Optimization Engine integrates with existing Model Engineer feedback loop
- [ ] Cost Forecasting integrates with existing BudgetChecker
- [ ] Dashboards integrate with existing Prometheus exporter + Grafana
