# Phase 4: Optimization Recommendations Engine — Design Document

## Overview

The Optimization Recommendations Engine analyzes historical token usage, cost, and quality data
to generate actionable recommendations for reducing cost and improving quality. It extends the
existing Model Engineer feedback loop into a proactive, data-driven recommendation system.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              Optimization Recommendations Engine                 │
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐                  │
│  │  Data Ingestion  │    │  Analysis Layer  │                  │
│  │                  │    │                  │                  │
│  │ HistoricalStore  │───►│ CostAnalyzer     │                  │
│  │ QE Feedback      │    │ QualityAnalyzer  │                  │
│  │ Model Engineer   │    │ EfficiencyScorer │                  │
│  │ Recommendations  │    │ PatternMatcher   │                  │
│  └──────────────────┘    └────────┬─────────┘                  │
│                                   │                             │
│                                   ▼                             │
│                    ┌──────────────────────────┐                 │
│                    │  Recommendation Engine   │                 │
│                    │                          │                 │
│                    │ ModelDowngradeAdvisor     │                 │
│                    │ EffortReducer             │                 │
│                    │ DecompositionAdvisor      │                 │
│                    │ ParallelizationAdvisor    │                 │
│                    │ CachingAdvisor            │                 │
│                    └────────────┬─────────────┘                 │
│                                 │                               │
│                                 ▼                               │
│                    ┌──────────────────────────┐                 │
│                    │  Scoring & Ranking       │                 │
│                    │                          │                 │
│                    │ ImpactScorer             │                 │
│                    │ ConfidenceScorer         │                 │
│                    │ RiskAssessor             │                 │
│                    └────────────┬─────────────┘                 │
│                                 │                               │
│                                 ▼                               │
│                    ┌──────────────────────────┐                 │
│                    │  Output Layer            │                 │
│                    │                          │                 │
│                    │ RecommendationStore      │                 │
│                    │ OrchestratorIntegration  │                 │
│                    │ DashboardFeed            │                 │
│                    └──────────────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

## Recommendation Types

### 1. Model Downgrade Recommendations

**Trigger:** A task type consistently achieves high quality (≥90) with a high-cost model
when a cheaper model would likely suffice.

**Logic:**
```
IF role=engineer AND model=claude-sonnet-4-6 AND avg_quality >= 90 (last 30 tasks)
AND similar tasks exist with model=claude-haiku-4-5 AND avg_quality >= 85
THEN recommend: downgrade engineer to claude-haiku-4-5
WITH estimated_savings = (sonnet_cost - haiku_cost) × task_frequency
AND confidence = min(sample_size / 30, 1.0)
```

**Model downgrade paths:**
- `claude-opus-4-6` → `claude-sonnet-4-6` (if quality ≥ 88 on Sonnet)
- `claude-sonnet-4-6` → `claude-haiku-4-5` (if quality ≥ 85 on Haiku)
- `claude-opus-4-7` → `claude-opus-4-6` (security tasks only, if no critical misses)

### 2. Effort Level Reduction Recommendations

**Trigger:** A role consistently completes tasks well under its effort budget.

**Logic:**
```
IF effort=high AND avg_tokens_used < 40% of effort_budget (last 20 tasks)
AND avg_quality >= 88
THEN recommend: reduce effort to medium
WITH estimated_savings = (high_cost - medium_cost) × task_frequency
AND confidence = min(sample_size / 20, 1.0)
```

### 3. Task Decomposition Recommendations

**Trigger:** Large, long-running tasks that could be parallelized.

**Logic:**
```
IF task_duration > 60 mins AND tokens > 5000
AND task_type is decomposable (detected by keyword analysis)
AND parallel_delegation_available
THEN recommend: decompose into N sub-tasks
WITH estimated_speedup = duration / N (wall-clock)
AND estimated_cost_delta = overhead_cost (small positive)
```

**Decomposability signals:**
- Task scope mentions multiple services/repos
- Task contains list of independent items
- Historical similar tasks were successfully parallelized

### 4. Parallel Delegation Recommendations

**Trigger:** Sequential tasks that could run concurrently.

**Logic:**
```
IF task_sequence has no dependencies between tasks
AND each task takes > 15 mins
AND total_sequential_time > 45 mins
THEN recommend: run tasks in parallel
WITH estimated_speedup = max(task_durations) / sum(task_durations)
```

### 5. Caching Optimization Recommendations

**Trigger:** Low cache hit rate for repeated similar tasks.

**Logic:**
```
IF cache_hit_rate < 20% (last 7 days)
AND similar_task_patterns detected (cosine similarity > 0.8)
THEN recommend: enable prompt caching for task type
WITH estimated_savings = (cached_tokens × cache_discount) × frequency
```

## Data Model

```python
@dataclass
class Recommendation:
    """A single optimization recommendation."""
    id: str                          # UUID
    created_at: datetime
    recommendation_type: str         # model_downgrade, effort_reduce, decompose, parallelize, cache
    title: str                       # Human-readable title
    description: str                 # Detailed explanation
    
    # Targeting
    target_role: Optional[str]       # Which role this applies to
    target_model: Optional[str]      # Which model to change FROM
    suggested_model: Optional[str]   # Which model to change TO
    target_effort: Optional[str]     # Current effort level
    suggested_effort: Optional[str]  # Suggested effort level
    
    # Impact
    estimated_savings_usd: float     # Monthly cost savings estimate
    estimated_savings_pct: float     # Percentage cost reduction
    estimated_quality_delta: float   # Expected quality change (negative = risk)
    estimated_speedup: float         # Wall-clock speedup factor (1.0 = no change)
    
    # Confidence
    impact_score: float              # 0-100: how much cost/quality impact
    confidence_score: float          # 0-1: how confident we are
    risk_score: float                # 0-100: risk of quality degradation
    sample_size: int                 # Number of tasks used for analysis
    
    # Evidence
    evidence: List[str]              # Supporting data points
    supporting_task_ids: List[str]   # Task IDs used as evidence
    
    # Status
    status: str                      # pending, accepted, rejected, applied, expired
    applied_at: Optional[datetime]
    outcome: Optional[str]           # Result after applying recommendation
    
    @property
    def priority_score(self) -> float:
        """Combined priority: impact × confidence × (1 - risk/100)."""
        return self.impact_score * self.confidence_score * (1 - self.risk_score / 100)
```

## Scoring System

### Impact Score (0-100)

```
impact_score = (
    cost_savings_weight × normalized_savings +
    quality_improvement_weight × normalized_quality_delta +
    speedup_weight × normalized_speedup
)

Where:
  cost_savings_weight = 0.6
  quality_improvement_weight = 0.3
  speedup_weight = 0.1
  
  normalized_savings = min(estimated_savings_usd / 100, 1.0) × 100
  normalized_quality_delta = max(0, estimated_quality_delta) × 10
  normalized_speedup = min((estimated_speedup - 1.0) × 50, 100)
```

### Confidence Score (0-1)

```
confidence_score = min(
    sample_size_factor × recency_factor × consistency_factor,
    1.0
)

Where:
  sample_size_factor = min(sample_size / 30, 1.0)
  recency_factor = 1.0 if data is <7 days old, 0.7 if <30 days, 0.4 if older
  consistency_factor = 1 - std_dev(quality_scores) / mean(quality_scores)
```

### Risk Score (0-100)

```
risk_score = (
    quality_variance_risk +
    model_capability_gap_risk +
    task_complexity_risk
)

Where:
  quality_variance_risk = std_dev(quality_scores) × 2  (high variance = risky)
  model_capability_gap_risk = {
    opus→sonnet: 10,
    sonnet→haiku: 20,
    opus→haiku: 40
  }
  task_complexity_risk = {
    security_task: 30,
    architecture_task: 20,
    implementation_task: 10,
    review_task: 5
  }
```

## Components

### RecommendationEngine

```python
class RecommendationEngine:
    """Main engine that generates and ranks recommendations."""
    
    def __init__(self, store: TimeSeriesStore, config: RecommendationConfig):
        self.store = store
        self.advisors = [
            ModelDowngradeAdvisor(store, config),
            EffortReducerAdvisor(store, config),
            DecompositionAdvisor(store, config),
            ParallelizationAdvisor(store, config),
            CachingAdvisor(store, config),
        ]
    
    def generate_recommendations(
        self,
        lookback_days: int = 30
    ) -> List[Recommendation]:
        """Generate all recommendations, ranked by priority score."""
        all_recs = []
        for advisor in self.advisors:
            recs = advisor.analyze(lookback_days)
            all_recs.extend(recs)
        
        # Deduplicate (same role+model+type)
        all_recs = self._deduplicate(all_recs)
        
        # Rank by priority score
        all_recs.sort(key=lambda r: r.priority_score, reverse=True)
        
        return all_recs
    
    def apply_recommendation(
        self,
        rec_id: str,
        orchestrator_config: Path
    ) -> ApplyResult:
        """Apply a recommendation to the Orchestrator routing config."""
```

### OrchestratorIntegration

```python
class OrchestratorIntegration:
    """Integrates recommendations with Orchestrator routing decisions."""
    
    def get_routing_overrides(self) -> Dict[str, RoutingOverride]:
        """Return active routing overrides from accepted recommendations."""
        
    def apply_model_override(
        self,
        role: str,
        model: str,
        effort: str,
        expires_at: datetime
    ) -> None:
        """Apply a model/effort override for a role (with expiry)."""
        
    def record_outcome(
        self,
        rec_id: str,
        task_id: str,
        quality_score: float,
        cost_usd: float
    ) -> None:
        """Record outcome of a task run under a recommendation."""
```

## Recommendation Lifecycle

```
GENERATED (by engine, daily run)
    │
    ▼
PENDING (stored, awaiting review)
    │
    ├──► ACCEPTED (by Orchestrator or human)
    │        │
    │        ▼
    │    APPLIED (routing override active)
    │        │
    │        ├──► outcome recorded (quality, cost delta)
    │        │
    │        └──► EXPIRED (after 30 days or manual override)
    │
    └──► REJECTED (by human review)
```

## CLI Interface

```bash
# List current recommendations
agentic-optimize list --status pending --min-impact 50

# Show recommendation detail
agentic-optimize show <rec-id>

# Accept a recommendation (applies routing override)
agentic-optimize accept <rec-id>

# Reject a recommendation
agentic-optimize reject <rec-id> --reason "too risky for security tasks"

# Run recommendation engine manually
agentic-optimize analyze --lookback-days 30

# Show recommendation history
agentic-optimize history --days 90
```

## Integration with Model Engineer

The Optimization Engine extends (not replaces) the Model Engineer feedback loop:

| Aspect | Model Engineer (existing) | Optimization Engine (new) |
|---|---|---|
| Trigger | After each QE HANDBACK | Daily scheduled run |
| Scope | Single task type | All task types, cross-role |
| Output | rank_1/2/3 recommendations | Scored, ranked recommendation list |
| Application | Orchestrator applies next task | Orchestrator applies with expiry |
| Evidence | QE model_assessment | 30-day historical data |
| Confidence | Qualitative | Quantitative (0-1 score) |

## File Layout

```
src/
  skills/
    optimization-engine/
      SKILL.md
      scripts/
        __init__.py
        engine.py                  # RecommendationEngine
        advisors/
          __init__.py
          model_downgrade.py       # ModelDowngradeAdvisor
          effort_reducer.py        # EffortReducerAdvisor
          decomposition.py         # DecompositionAdvisor
          parallelization.py       # ParallelizationAdvisor
          caching.py               # CachingAdvisor
        scoring.py                 # ImpactScorer, ConfidenceScorer, RiskAssessor
        store.py                   # RecommendationStore (SQLite)
        orchestrator_integration.py
        cli.py
      tests/
        test_engine.py
        test_advisors.py
        test_scoring.py
        test_orchestrator_integration.py
```

## Success Criteria

- [ ] RecommendationEngine generates all 5 recommendation types
- [ ] Impact/confidence/risk scoring implemented and calibrated
- [ ] Recommendations ranked by priority score
- [ ] OrchestratorIntegration applies routing overrides with expiry
- [ ] Outcome tracking records quality/cost delta after applying
- [ ] CLI provides list/accept/reject interface
- [ ] Integrates with Historical Analysis System
- [ ] 90%+ test coverage
- [ ] Generates at least 1 actionable recommendation from 30 days of sample data
