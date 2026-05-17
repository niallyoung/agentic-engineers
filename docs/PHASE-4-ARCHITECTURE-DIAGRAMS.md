# Phase 4: Architecture Diagrams

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Phase 4: Historical Analysis & Intelligence               │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Data Sources (Existing)                       │   │
│  │                                                                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ TokenTracker │  │ HANDBACK YAML│  │ opencode.db  │              │   │
│  │  │ (real-time)  │  │ artifacts/   │  │ (sessions)   │              │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │   │
│  │         └─────────────────┼─────────────────┘                       │   │
│  └───────────────────────────┼─────────────────────────────────────────┘   │
│                              │                                               │
│                              ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Historical Analysis System (NEW)                   │   │
│  │                                                                       │   │
│  │  MetricsCollector ──► TimeSeriesStore (SQLite) ──► TrendAnalyzer    │   │
│  │                              │                    ──► AnomalyDetector│   │
│  │                              │                    ──► ReportGenerator│   │
│  │                              │                                        │   │
│  │                         history.db                                    │   │
│  │                    (task_metrics, daily_agg,                          │   │
│  │                     weekly_agg, anomaly_events)                       │   │
│  └───────────────────────────┬─────────────────────────────────────────┘   │
│                              │                                               │
│              ┌───────────────┼───────────────┐                              │
│              │               │               │                              │
│              ▼               ▼               ▼                              │
│  ┌───────────────┐  ┌────────────────┐  ┌──────────────────────────────┐  │
│  │  Optimization │  │  Cost          │  │  Advanced Dashboards          │  │
│  │  Engine (NEW) │  │  Forecasting   │  │  (NEW)                        │  │
│  │               │  │  (NEW)         │  │                               │  │
│  │ Advisors:     │  │ Forecasters:   │  │  Terminal (Rich)              │  │
│  │ - ModelDown   │  │ - Linear       │  │  Grafana JSON export          │  │
│  │ - EffortReduc │  │ - ExpSmoothing │  │  HTML report export           │  │
│  │ - Decompose   │  │ - Seasonal     │  │                               │  │
│  │ - Parallelize │  │ - Ensemble     │  │  Panels:                      │  │
│  │ - Caching     │  │               │  │  Overview, Cost, Quality,     │  │
│  │               │  │ ScenarioEngine │  │  Performance, Budget,         │  │
│  │ Scoring:      │  │ ExhaustionPred │  │  Recommendations, Anomalies   │  │
│  │ Impact/Conf/  │  │ BudgetAdvisor  │  │                               │  │
│  │ Risk          │  │               │  │  DashboardDataAPI             │  │
│  └───────┬───────┘  └───────┬────────┘  └──────────────────────────────┘  │
│          │                  │                                               │
│          ▼                  ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Integration Layer (Existing + Enhanced)           │   │
│  │                                                                       │   │
│  │  Orchestrator ◄── RoutingOverrides ◄── OrchestratorIntegration      │   │
│  │  BudgetChecker ◄── ForecastAlerts ◄── ExhaustionPredictor           │   │
│  │  Model Engineer ◄── Recommendations ◄── RecommendationEngine        │   │
│  │  Prometheus ◄── Metrics ◄── PrometheusExporter (existing)           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow: Metrics → Storage → Analysis → Action

```
Task Execution
     │
     ▼
HANDBACK emitted (YAML)
     │
     ├──────────────────────────────────────────────────────────┐
     │                                                          │
     ▼                                                          ▼
MetricsCollector                                          TokenTracker
.collect_from_handback()                                  (real-time)
     │                                                          │
     └──────────────────────┬───────────────────────────────────┘
                            │
                            ▼
                   TimeSeriesStore
                   .insert_task()
                            │
                   ┌────────┴────────┐
                   │                 │
                   ▼                 ▼
            aggregate_hourly()  aggregate_daily()
                   │                 │
                   └────────┬────────┘
                            │
                            ▼
                   AnomalyDetector
                   .run_all_checks()
                            │
                   ┌────────┴────────┐
                   │                 │
              No anomaly         Anomaly detected
                   │                 │
                   │                 ▼
                   │          AnomalyEvent stored
                   │          + Alert triggered
                   │          (voice-notify / email)
                   │
                   ▼
           [Daily at 06:00 UTC]
                   │
          ┌────────┴─────────────────────────────┐
          │                                       │
          ▼                                       ▼
RecommendationEngine                    EnsembleForecaster
.generate_recommendations()             .predict(horizon=30)
          │                                       │
          ▼                                       ▼
RecommendationStore                     ForecastStore
(pending recommendations)               (forecast history)
          │                                       │
          └────────────────┬──────────────────────┘
                           │
                           ▼
                  DashboardDataAPI
                           │
                  ┌────────┴────────┐
                  │                 │
                  ▼                 ▼
           TerminalDashboard   GrafanaExporter
           (agentic-dashboard)  (grafana-dashboards/)
```

## Component Interaction Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                    Phase 4 Components                             │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Historical Analysis System                   │    │
│  │                                                           │    │
│  │  ┌─────────────┐   ┌──────────────┐   ┌─────────────┐  │    │
│  │  │  Collector  │──►│  TSStore     │──►│  Analyzer   │  │    │
│  │  └─────────────┘   └──────┬───────┘   └──────┬──────┘  │    │
│  │                           │                   │          │    │
│  │                           │◄──────────────────┘          │    │
│  │                           │                              │    │
│  │                    ┌──────▼───────┐                      │    │
│  │                    │  history.db  │                      │    │
│  │                    └──────┬───────┘                      │    │
│  └───────────────────────────┼──────────────────────────────┘    │
│                              │                                    │
│              ┌───────────────┼────────────────┐                  │
│              │               │                │                  │
│              ▼               ▼                ▼                  │
│  ┌───────────────┐  ┌────────────────┐  ┌────────────────────┐  │
│  │  Optimization │  │  Forecasting   │  │  Dashboards        │  │
│  │  Engine       │  │  Module        │  │                    │  │
│  │               │  │               │  │  ┌──────────────┐  │  │
│  │  ┌─────────┐  │  │  ┌─────────┐  │  │  │ DataAPI      │  │  │
│  │  │Advisors │  │  │  │Forecast │  │  │  └──────┬───────┘  │  │
│  │  └────┬────┘  │  │  └────┬────┘  │  │         │          │  │
│  │       │       │  │       │       │  │  ┌──────▼───────┐  │  │
│  │  ┌────▼────┐  │  │  ┌────▼────┐  │  │  │  Terminal    │  │  │
│  │  │ Scoring │  │  │  │Scenario │  │  │  │  Grafana     │  │  │
│  │  └────┬────┘  │  │  └────┬────┘  │  │  │  HTML        │  │  │
│  │       │       │  │       │       │  │  └──────────────┘  │  │
│  │  ┌────▼────┐  │  │  ┌────▼────┐  │  └────────────────────┘  │
│  │  │  Store  │  │  │  │ Budget  │  │                           │
│  │  └─────────┘  │  │  └─────────┘  │                           │
│  └───────┬───────┘  └───────┬────────┘                          │
│          │                  │                                    │
│          └──────────────────┘                                    │
│                    │                                             │
│                    ▼                                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Integration Layer                            │    │
│  │                                                           │    │
│  │  Orchestrator ◄── RoutingOverrides                       │    │
│  │  BudgetChecker ◄── ForecastAlerts                        │    │
│  │  Model Engineer ◄── Recommendations                      │    │
│  │  Prometheus ◄── Metrics                                  │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

## API Interface Definitions

### Historical Analysis API

```python
# Query interface
class HistoricalAnalysisAPI:
    
    # Trend queries
    def get_cost_trend(
        self,
        start_date: str,           # YYYY-MM-DD
        end_date: str,             # YYYY-MM-DD
        role: Optional[str],       # filter by role
        model: Optional[str],      # filter by model
        granularity: str = "daily" # hourly, daily, weekly, monthly
    ) -> List[TrendPoint]: ...
    
    def get_quality_trend(
        self,
        start_date: str,
        end_date: str,
        role: Optional[str],
        granularity: str = "daily"
    ) -> List[TrendPoint]: ...
    
    def get_token_trend(
        self,
        start_date: str,
        end_date: str,
        token_type: str = "total", # input, output, cached, total
        role: Optional[str],
        granularity: str = "daily"
    ) -> List[TrendPoint]: ...
    
    # Aggregation queries
    def get_cost_attribution(
        self,
        month: str                 # YYYY-MM
    ) -> CostAttributionData: ...
    
    def get_top_tasks_by_cost(
        self,
        date: str,
        limit: int = 10
    ) -> List[TaskCostRecord]: ...
    
    # Anomaly queries
    def get_anomalies(
        self,
        start_date: str,
        end_date: str,
        severity: Optional[str],   # low, medium, high, critical
        anomaly_type: Optional[str]
    ) -> List[AnomalyEvent]: ...
    
    def get_active_anomalies(self) -> List[AnomalyEvent]: ...
    
    # Report generation
    def generate_daily_report(self, date: str) -> DailySummaryReport: ...
    def generate_weekly_report(self, week: str) -> WeeklyTrendReport: ...
    def generate_monthly_report(self, month: str) -> MonthlyReport: ...
```

### Optimization Engine API

```python
class OptimizationEngineAPI:
    
    def get_recommendations(
        self,
        status: str = "pending",       # pending, accepted, rejected, applied, expired
        recommendation_type: Optional[str],  # model_downgrade, effort_reduce, etc.
        min_impact_score: float = 0.0,
        min_confidence: float = 0.0,
        limit: int = 20
    ) -> List[Recommendation]: ...
    
    def get_recommendation(
        self,
        rec_id: str
    ) -> Recommendation: ...
    
    def accept_recommendation(
        self,
        rec_id: str,
        apply_immediately: bool = False
    ) -> AcceptResult: ...
    
    def reject_recommendation(
        self,
        rec_id: str,
        reason: str
    ) -> None: ...
    
    def run_analysis(
        self,
        lookback_days: int = 30
    ) -> List[Recommendation]: ...
    
    def get_routing_overrides(self) -> Dict[str, RoutingOverride]: ...
    
    def get_recommendation_history(
        self,
        days: int = 90
    ) -> List[RecommendationHistoryEntry]: ...
    
    def get_realized_savings(
        self,
        days: int = 30
    ) -> float: ...
```

### Cost Forecasting API

```python
class CostForecastingAPI:
    
    def forecast_cost(
        self,
        horizon_days: int = 30,
        role: Optional[str] = None,
        model: Optional[str] = None,
        method: str = "ensemble"       # linear, exponential, seasonal, ensemble
    ) -> ForecastResult: ...
    
    def forecast_tokens(
        self,
        horizon_days: int = 30,
        token_type: str = "total",
        role: Optional[str] = None
    ) -> ForecastResult: ...
    
    def predict_budget_exhaustion(
        self,
        budget_usd: float
    ) -> ExhaustionForecast: ...
    
    def run_scenario(
        self,
        scenario: Union[str, ScenarioConfig],
        horizon_days: int = 30
    ) -> ScenarioForecast: ...
    
    def compare_scenarios(
        self,
        scenarios: List[str],
        horizon_days: int = 30
    ) -> ScenarioComparison: ...
    
    def recommend_budget(
        self,
        target_days: int,
        safety_margin_pct: float = 0.15
    ) -> float: ...
    
    def get_forecast_accuracy(
        self,
        days: int = 90
    ) -> ForecastAccuracyReport: ...
```

### Dashboard Data API

```python
class DashboardDataAPI:
    
    def get_overview_kpis(self) -> OverviewKPIs: ...
    
    def get_cost_trend(
        self, days: int = 30, role: Optional[str] = None
    ) -> List[TrendPoint]: ...
    
    def get_cost_attribution(self, month: str) -> CostAttributionData: ...
    
    def get_quality_trend(
        self, days: int = 30, role: Optional[str] = None
    ) -> List[TrendPoint]: ...
    
    def get_quality_distribution(self, days: int = 30) -> QualityDistribution: ...
    
    def get_performance_metrics(self, days: int = 7) -> PerformanceMetrics: ...
    
    def get_budget_status(self) -> BudgetStatusData: ...
    
    def get_forecast(self, horizon_days: int = 30) -> ForecastResult: ...
    
    def get_scenario_comparison(
        self, scenarios: List[str], horizon_days: int = 30
    ) -> ScenarioComparison: ...
    
    def get_recommendations(
        self, status: str = "pending", limit: int = 10
    ) -> List[Recommendation]: ...
    
    def get_active_anomalies(self) -> List[AnomalyEvent]: ...
    
    def get_anomaly_timeline(self, days: int = 30) -> List[AnomalyEvent]: ...
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Developer Machine                             │
│                                                                  │
│  ~/.local/share/agentic-engineers/                              │
│    history.db              ← SQLite time-series database        │
│    recommendations.db      ← SQLite recommendations store       │
│    forecasts.db            ← SQLite forecast history            │
│                                                                  │
│  ~/git/agentic-engineers/                                       │
│    artifacts/metrics/      ← HANDBACK metrics YAML files        │
│    artifacts/reports/      ← Generated reports                  │
│    grafana-dashboards/     ← Grafana JSON exports               │
│                                                                  │
│  Scheduled Jobs (cron or systemd timer):                        │
│    01:00 UTC: agentic-history ingest --source artifacts/metrics │
│    06:00 UTC: agentic-optimize analyze                          │
│    06:05 UTC: agentic-forecast cost --horizon 30                │
│    06:10 UTC: agentic-dashboard --export html --output report   │
└─────────────────────────────────────────────────────────────────┘
```

No cloud infrastructure required. All Phase 4 components run locally.

## Phase 4 vs. Phase 3 Integration Map

| Phase 3 Component | Phase 4 Integration |
|---|---|
| `TokenTracker` | → `MetricsCollector.collect_from_token_tracker()` |
| `BudgetChecker` | ← `ExhaustionPredictor` alerts + `BudgetAdjustmentAdvisor` |
| `MetricsRegistry` | → `MetricsCollector` reads counters |
| `prometheus_exporter.py` | ← `DashboardDataAPI` provides Grafana data |
| `alerting.py` | ← `AnomalyDetector` triggers new alert types |
| `orchestrator_cli.py` | ← `agentic-dashboard` extends CLI |
| Model Engineer feedback | ← `RecommendationEngine` extends with historical data |
| `artifacts/metrics/*.yaml` | → `MetricsCollector.collect_from_metrics_dir()` |
