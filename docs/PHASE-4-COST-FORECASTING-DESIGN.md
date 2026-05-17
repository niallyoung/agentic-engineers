# Phase 4: Cost Forecasting Module — Design Document

## Overview

The Cost Forecasting Module predicts future token usage and costs based on historical trends,
enabling proactive budget management, scenario planning, and early warning of budget exhaustion.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Cost Forecasting Module                       │
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────────────────────┐  │
│  │  Historical Data │    │       Forecasting Engine         │  │
│  │                  │    │                                  │  │
│  │ TimeSeriesStore  │───►│ LinearTrendForecaster            │  │
│  │ daily_agg        │    │ ExponentialSmoothingForecaster   │  │
│  │ weekly_agg       │    │ SeasonalDecompositionForecaster  │  │
│  └──────────────────┘    │ EnsembleForecaster               │  │
│                          └──────────────┬───────────────────┘  │
│                                         │                        │
│                                         ▼                        │
│                          ┌──────────────────────────────────┐  │
│                          │       Scenario Engine            │  │
│                          │                                  │  │
│                          │ BaselineScenario                 │  │
│                          │ OptimisticScenario               │  │
│                          │ PessimisticScenario              │  │
│                          │ CustomScenario (what-if)         │  │
│                          └──────────────┬───────────────────┘  │
│                                         │                        │
│                                         ▼                        │
│                          ┌──────────────────────────────────┐  │
│                          │       Budget Integration         │  │
│                          │                                  │  │
│                          │ ExhaustionPredictor              │  │
│                          │ BudgetAdjustmentAdvisor          │  │
│                          │ AlertThresholdCalculator         │  │
│                          └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Forecasting Methods

### 1. Linear Trend Forecaster

Simple linear regression on daily cost/token data. Best for stable, growing trends.

```python
class LinearTrendForecaster:
    """Linear regression-based forecaster."""
    
    def fit(self, dates: List[str], values: List[float]) -> None:
        """Fit linear model to historical data."""
        # y = mx + b, where x = days since start
        
    def predict(self, horizon_days: int) -> ForecastResult:
        """Predict next N days with confidence intervals."""
        # Returns point estimates + 80% and 95% confidence intervals
```

**Suitable for:** Stable workloads, early-stage data (< 2 weeks history)

### 2. Exponential Smoothing Forecaster

Holt-Winters exponential smoothing. Adapts to recent trends faster than linear.

```python
class ExponentialSmoothingForecaster:
    """Holt-Winters double exponential smoothing."""
    
    def __init__(self, alpha: float = 0.3, beta: float = 0.1):
        """
        alpha: smoothing factor for level (0-1, higher = more weight on recent)
        beta: smoothing factor for trend (0-1)
        """
        
    def fit(self, values: List[float]) -> None:
        """Fit model to historical data."""
        
    def predict(self, horizon_days: int) -> ForecastResult:
        """Predict with exponentially-weighted trend."""
```

**Suitable for:** Trending workloads, 2-4 weeks of history

### 3. Seasonal Decomposition Forecaster

Decomposes data into trend + weekly seasonality + residual. Best for weekly patterns.

```python
class SeasonalDecompositionForecaster:
    """STL-style seasonal decomposition."""
    
    def fit(self, values: List[float], period: int = 7) -> None:
        """Decompose into trend + seasonal + residual."""
        
    def predict(self, horizon_days: int) -> ForecastResult:
        """Predict using trend + seasonal components."""
```

**Suitable for:** Workloads with weekly patterns (e.g., less activity on weekends)

### 4. Ensemble Forecaster (Default)

Combines all three methods with weighted averaging based on historical accuracy.

```python
class EnsembleForecaster:
    """Weighted ensemble of all forecasting methods."""
    
    def __init__(self):
        self.forecasters = [
            LinearTrendForecaster(),
            ExponentialSmoothingForecaster(),
            SeasonalDecompositionForecaster(),
        ]
    
    def fit(self, dates: List[str], values: List[float]) -> None:
        """Fit all forecasters and compute weights from backtesting."""
        # Weights based on MAE from last 7-day holdout
        
    def predict(self, horizon_days: int) -> ForecastResult:
        """Weighted average prediction with combined confidence intervals."""
```

## Data Model

```python
@dataclass
class ForecastPoint:
    """Single point in a forecast."""
    date: str                    # YYYY-MM-DD
    predicted_value: float       # Point estimate
    lower_80: float              # 80% confidence interval lower bound
    upper_80: float              # 80% confidence interval upper bound
    lower_95: float              # 95% confidence interval lower bound
    upper_95: float              # 95% confidence interval upper bound


@dataclass
class ForecastResult:
    """Complete forecast result."""
    metric: str                  # cost_usd, input_tokens, output_tokens
    role: Optional[str]          # None = all roles combined
    model: Optional[str]         # None = all models combined
    generated_at: datetime
    history_days: int            # Days of history used
    horizon_days: int            # Days forecasted
    method: str                  # linear, exponential, seasonal, ensemble
    
    points: List[ForecastPoint]  # One per forecasted day
    
    # Summary statistics
    total_predicted: float       # Sum over horizon
    daily_average: float         # Average daily value
    trend_direction: str         # increasing, decreasing, stable
    trend_pct_per_week: float    # Weekly growth rate
    
    # Accuracy metadata
    mae: Optional[float]         # Mean absolute error from backtesting
    mape: Optional[float]        # Mean absolute percentage error


@dataclass
class ExhaustionForecast:
    """Budget exhaustion prediction."""
    budget_usd: float
    spent_usd: float
    remaining_usd: float
    
    # Exhaustion dates under different scenarios
    baseline_exhaustion_date: Optional[str]    # Most likely date
    optimistic_exhaustion_date: Optional[str]  # If trend improves
    pessimistic_exhaustion_date: Optional[str] # If trend worsens
    
    days_until_exhaustion: Optional[int]       # Under baseline
    confidence: float                          # 0-1
    
    # Recommendations
    recommended_budget_increase_usd: float     # To last 30 more days
    recommended_budget_increase_pct: float


@dataclass
class ScenarioForecast:
    """What-if scenario analysis result."""
    scenario_name: str
    description: str
    assumptions: Dict[str, Any]   # e.g., {"task_volume_multiplier": 1.5}
    
    forecast: ForecastResult
    exhaustion: ExhaustionForecast
    
    vs_baseline_cost_delta: float   # Additional cost vs. baseline
    vs_baseline_cost_delta_pct: float
```

## Scenario Engine

### Built-in Scenarios

```python
SCENARIOS = {
    "baseline": {
        "description": "Current trend continues unchanged",
        "task_volume_multiplier": 1.0,
        "model_mix_change": None,
        "effort_change": None,
    },
    "optimistic": {
        "description": "Optimization recommendations applied (20% cost reduction)",
        "task_volume_multiplier": 1.0,
        "cost_reduction_pct": 0.20,
    },
    "pessimistic": {
        "description": "Task volume increases 50% (new project onboarding)",
        "task_volume_multiplier": 1.5,
        "model_mix_change": None,
    },
    "model_downgrade": {
        "description": "All engineer tasks downgraded from Sonnet to Haiku",
        "model_overrides": {"engineer": "claude-haiku-4-5"},
    },
    "scale_up": {
        "description": "Double task volume for sprint planning",
        "task_volume_multiplier": 2.0,
    },
}
```

### Custom Scenario API

```python
class ScenarioEngine:
    """Runs what-if scenario analysis."""
    
    def run_scenario(
        self,
        scenario: Union[str, ScenarioConfig],
        horizon_days: int = 30
    ) -> ScenarioForecast:
        """Run a named or custom scenario."""
        
    def compare_scenarios(
        self,
        scenarios: List[str],
        horizon_days: int = 30
    ) -> ScenarioComparison:
        """Compare multiple scenarios side-by-side."""
        
    def find_break_even(
        self,
        optimization_cost: float,
        monthly_savings: float
    ) -> int:
        """Calculate break-even days for an optimization investment."""
```

## Budget Integration

### ExhaustionPredictor

```python
class ExhaustionPredictor:
    """Predicts when budget will be exhausted."""
    
    def predict_exhaustion(
        self,
        budget_usd: float,
        spent_usd: float,
        forecast: ForecastResult
    ) -> ExhaustionForecast:
        """Predict budget exhaustion date under baseline forecast."""
        
    def days_until_warning_threshold(
        self,
        budget_usd: float,
        spent_usd: float,
        warning_pct: float = 0.80
    ) -> Optional[int]:
        """Days until 80% budget consumed (warning threshold)."""
```

### BudgetAdjustmentAdvisor

```python
class BudgetAdjustmentAdvisor:
    """Recommends budget adjustments based on forecasts."""
    
    def recommend_budget(
        self,
        target_days: int,
        forecast: ForecastResult,
        safety_margin_pct: float = 0.15
    ) -> float:
        """Recommend budget to last N days with 15% safety margin."""
        
    def recommend_alert_thresholds(
        self,
        budget_usd: float,
        forecast: ForecastResult
    ) -> AlertThresholds:
        """Recommend warning/critical/block thresholds for budget alerts."""
```

## Forecast Accuracy Tracking

Forecasts are stored and compared against actuals to track accuracy over time:

```sql
CREATE TABLE forecast_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    generated_at    INTEGER NOT NULL,
    metric          TEXT NOT NULL,
    role            TEXT,
    model           TEXT,
    method          TEXT NOT NULL,
    horizon_days    INTEGER NOT NULL,
    
    -- Stored as JSON array of {date, predicted, lower_80, upper_80}
    forecast_json   TEXT NOT NULL,
    
    -- Filled in after actuals available
    actual_json     TEXT,
    mae             REAL,
    mape            REAL,
    within_80ci_pct REAL,   -- % of actuals within 80% CI
    within_95ci_pct REAL
);
```

**Accuracy targets:**
- MAPE < 15% for 7-day horizon
- MAPE < 25% for 30-day horizon
- 80% CI coverage ≥ 75% (i.e., 75% of actuals fall within 80% CI)

## CLI Interface

```bash
# Forecast costs for next 30 days
agentic-forecast cost --horizon 30

# Forecast by role
agentic-forecast cost --role senior_engineer --horizon 14

# Predict budget exhaustion
agentic-forecast exhaustion --budget 500

# Run scenario analysis
agentic-forecast scenario --name pessimistic --horizon 30
agentic-forecast scenario --name model_downgrade --horizon 30

# Compare scenarios
agentic-forecast compare baseline optimistic pessimistic --horizon 30

# Custom what-if
agentic-forecast what-if --task-volume-multiplier 1.5 --horizon 14

# Show forecast accuracy history
agentic-forecast accuracy --days 90
```

## Minimum Data Requirements

| Horizon | Minimum History | Recommended History |
|---|---|---|
| 7 days | 7 days | 14 days |
| 14 days | 14 days | 30 days |
| 30 days | 21 days | 60 days |
| 90 days | 45 days | 180 days |

If insufficient history: fall back to linear extrapolation with wide confidence intervals
and display a data quality warning.

## File Layout

```
src/
  skills/
    cost-forecasting/
      SKILL.md
      scripts/
        __init__.py
        forecasters/
          __init__.py
          linear.py              # LinearTrendForecaster
          exponential.py         # ExponentialSmoothingForecaster
          seasonal.py            # SeasonalDecompositionForecaster
          ensemble.py            # EnsembleForecaster
        scenario_engine.py       # ScenarioEngine
        budget_integration.py    # ExhaustionPredictor, BudgetAdjustmentAdvisor
        accuracy_tracker.py      # Forecast accuracy tracking
        cli.py
      tests/
        test_forecasters.py
        test_scenario_engine.py
        test_budget_integration.py
        test_accuracy_tracker.py
```

## Success Criteria

- [ ] EnsembleForecaster implemented with all 3 methods
- [ ] Forecast accuracy: MAPE < 15% for 7-day horizon (validated on synthetic data)
- [ ] ExhaustionPredictor produces accurate budget exhaustion dates
- [ ] 5 built-in scenarios implemented
- [ ] Custom what-if scenario API works
- [ ] Forecast accuracy tracking stores and evaluates predictions
- [ ] CLI provides all forecast and scenario commands
- [ ] Integrates with Historical Analysis System (TimeSeriesStore)
- [ ] Integrates with existing BudgetChecker
- [ ] 90%+ test coverage
