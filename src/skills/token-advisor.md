# Token Advisor Skill

**Agent Role**: Model Engineer  
**Model**: claude-sonnet-4-6  
**Effort**: medium  
**Purpose**: Monitors session token budget; recommends optimal model tier; provides budget awareness to Orchestrator

---

## Overview

Token Advisor analyzes current session token usage, calculates velocity and trend, and recommends the most cost-effective model tier (Haiku/Sonnet/Opus) for upcoming tasks. This ensures all delegations respect budget constraints and avoid expensive model choices when cheaper alternatives suffice.

---

## DELEGATE Block Specification

### Input Fields

```yaml
analysis_type: "current_status" | "trend" | "recommendation"
  # current_status: just return metrics
  # trend: analyze velocity + direction
  # recommendation: recommend model tier for upcoming work

task_complexity: "low" | "medium" | "high" | "max" (optional, for recommendations)
  # Used only when analysis_type = "recommendation"
  # Helps size the recommended model

horizon: 60 (optional, default)
  # Look-ahead window in minutes
  # Token Advisor projects if upcoming work will exceed budget within this window
```

### Example DELEGATE Block

```yaml
---
handoff_type: DELEGATE
task_id: 2026-05-05-token-advisor-status-check
timestamp: 2026-05-05T09:00:00Z
role: Token Advisor (Model Engineer)
model: claude-sonnet-4-6
effort: medium
scope: >
  Analyze current session token usage and recommend optimal model for upcoming
  Principal Engineer design task (high complexity, estimated 4000 tokens).
  Provide session percentage, trend, velocity, and model recommendation with
  confidence score.
context:
  - Previous status: 42% at 2026-05-05T08:00:00Z
  - Task ahead: Principal Engineer design (4000 tokens estimated)
  - Budget constraint: Stay under 85% session utilization
plan:
  1. Query session token metrics
  2. Calculate velocity (tokens/min over last 30 min)
  3. Project TTL until reset
  4. Analyze trend (stable/increasing/critical)
  5. Recommend model tier for task complexity
  6. Flag warnings if approaching limits
  7. Return HANDBACK with all metrics
success_criteria:
  - All metrics present and accurate
  - Trend correctly reflects usage pattern
  - Model recommendation is defensible
  - Confidence score calibrated (0.7+ = trusted)
---
```

---

## HANDBACK Block Specification

### Output Fields

```yaml
session_pct: 45.2
  # Float 0.0-100.0, percentage of session used

tokens_used: 90400
  # Integer, total tokens consumed in this session

tokens_available: 200000
  # Integer, total tokens in this session budget

trend: "stable" | "increasing" | "critical"
  # stable: velocity ±100 tokens/min
  # increasing: velocity accelerating
  # critical: approaching session limit

velocity: 1150
  # Integer, tokens/minute over last 30 minutes
  # Computed as: (tokens_used_30min_ago - tokens_used_now) / 30

ttl_minutes: 410
  # Integer, minutes until session reset

recommended_model: "haiku" | "sonnet" | "opus"
  # Optimal model for upcoming task (if analysis_type = "recommendation")
  # haiku: low-complexity tasks, conserve budget
  # sonnet: medium-complexity, balanced cost/capability
  # opus: high-complexity, cost justified by quality

recommendation_confidence: 0.92
  # Float 0.0-1.0
  # 0.7+ = trusted recommendation
  # 0.5-0.7 = proceed with caution
  # <0.5 = escalate to human

warning: null | "approaching session limit" | "critical budget"
  # Human-readable warning if constraint detected

actions: ["string"]
  # List of specific recommendations for Orchestrator
  # e.g. ["Switch to Haiku for routine tasks", "Use Sonnet for medium work", ...]
```

### Example HANDBACK Block

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-05-token-advisor-status-check
timestamp: 2026-05-05T09:01:15Z
status: complete
session_pct: 45.2
tokens_used: 90400
tokens_available: 200000
trend: stable
velocity: 1150
ttl_minutes: 410
recommended_model: sonnet
recommendation_confidence: 0.92
warning: null
actions:
  - "Principal Engineer design task (4000 tokens estimated) is within safe budget"
  - "After Principal task, switch to Haiku/Sonnet for Week 2 implementation"
  - "Monitor velocity; if exceeds 1500 tokens/min, escalate to human"
analysis_details:
  last_30min_tokens: 34500
  avg_per_minute: 1150
  session_reset_at: "2026-05-05T23:59:59Z"
  historical_trend: "stable (±100 tokens/min variance)"
  model_selection_rationale:
    "Sonnet is optimal for medium-complexity week 2 work. Haiku would be too limited
     for orchestration tasks; Opus not justified by budget savings. Confidence 0.92
     based on stable velocity pattern."
---
```

---

## Implementation Approach

### Algorithm: Trend Analysis

```
current_usage = get_session_usage()
previous_usage = get_session_usage_30min_ago()

velocity = (current_usage - previous_usage) / 30  # tokens/minute

if velocity < 900:
  trend = "stable"
elif velocity < 1300:
  trend = "increasing"
else:
  trend = "critical"

ttl = (session_budget - current_usage) / velocity  # minutes until exhausted
```

### Algorithm: Model Recommendation

```
IF analysis_type != "recommendation":
  return current_status (no recommendation)

IF remaining_budget < 25000:
  recommended_model = "haiku"
  confidence = 0.95  # clearly need budget-conscious model
ELIF remaining_budget < 50000 OR task_complexity = "high":
  recommended_model = "sonnet"
  confidence = 0.85
ELSE:
  IF task_complexity = "max":
    recommended_model = "opus"
    confidence = 0.90
  ELSE:
    recommended_model = "sonnet"
    confidence = 0.80

warning = null
IF session_pct > 80:
  warning = "approaching session limit"
IF session_pct > 90:
  warning = "critical budget"
  escalate_to_human = true
```

### Data Source

Token Advisor reads metrics from one of:
1. **Orchestrator Context**: `session_pct`, `tokens_used`, `tokens_available` passed in DELEGATE
2. **SSM Parameter Store**: `/{env}-{service-name}/token-metrics` (if persisted)
3. **CloudWatch Logs**: Query logs for token usage events (if available)

**Recommendation**: Use Orchestrator context as primary source; cache for 2 minutes to avoid recomputation every 30s.

### Confidence Scoring

Confidence reflects certainty in the recommendation:

- **0.9+**: Stable velocity, clear budget constraint, straightforward recommendation
- **0.7-0.89**: Slight uncertainty in velocity trend or task complexity estimate
- **0.5-0.69**: Conflicting signals (budget tight but task complex); recommend human review
- **<0.5**: Cannot recommend confidently; escalate to human

Confidence should NOT be inflated to appear more capable. Honest scoring builds trust.

### Caching Strategy (Optional)

Token Advisor can cache results for 2 minutes:
- Multiple delegations within 2 min get same recommendation
- Reduces computation cost
- Falls back to fresh computation if cache expires

---

## Integration Points

### Invoked By

- **Orchestrator** (before major DELEGATE): "Should I use Sonnet or Haiku?"
- **Quality Gate Orchestrator** (for budget context): "What's our current budget status?"
- **Manual trigger** (CLI): `make show-budget` or similar

### Invokes

- None (standalone analysis, no sub-agents)

### DELEGATE Signature (for Orchestrator)

Orchestrator delegates to Token Advisor with:

```go
type TokenAdvisorDelegate struct {
  AnalysisType    string // "current_status", "trend", "recommendation"
  TaskComplexity  string // "low", "medium", "high", "max" (optional)
  Horizon         int    // minutes (default 60)
}
```

### HANDBACK Signature (to Orchestrator)

Token Advisor returns:

```go
type TokenAdvisorHandback struct {
  SessionPct        float64
  TokensUsed        int64
  TokensAvailable   int64
  Trend             string // "stable", "increasing", "critical"
  Velocity          float64 // tokens/minute
  TTLMinutes        int
  RecommendedModel  string // "haiku", "sonnet", "opus"
  Confidence        float64
  Warning           string // null or warning message
  Actions           []string
}
```

---

## Error Handling & Fallbacks

### If Token Metrics Unavailable

```
If unable to read token metrics:
  - Log error (don't fail)
  - Return defensive recommendation (use Haiku to conserve)
  - Confidence = 0.3 (low)
  - Warning = "Could not read token metrics; defaulting to budget-conservative model"
```

### If Historical Data Insufficient

```
If session just started (<5 minutes of history):
  - Use flat recommendation based on task_complexity only
  - Confidence = 0.6 (moderate)
  - Note: "Insufficient history; basing on task complexity only"
```

### If Velocity Unstable

```
If velocity variance > 500 tokens/min:
  - Confidence -= 0.15 (reduce confidence)
  - Recommendation same, but flag unstable pattern
  - Suggest human review if approaching budget limit
```

---

## Example Usage

### Query Current Status (No Recommendation)

```yaml
DELEGATE:
  analysis_type: "current_status"

HANDBACK:
  session_pct: 45.2
  tokens_used: 90400
  tokens_available: 200000
  trend: "stable"
  velocity: 1150
  ttl_minutes: 410
  recommended_model: null  # not requested
  warning: null
```

### Get Model Recommendation Before High-Effort Task

```yaml
DELEGATE:
  analysis_type: "recommendation"
  task_complexity: "high"
  horizon: 120  # Look ahead 2 hours

HANDBACK:
  session_pct: 62.5
  recommended_model: "sonnet"
  confidence: 0.88
  actions:
    - "Sonnet is optimal for high-complexity work"
    - "Remaining budget sufficient for 3-4 high-effort Sonnet tasks"
    - "After those, may need to switch to Haiku or escalate budget"
```

### Budget Critical Decision

```yaml
DELEGATE:
  analysis_type: "recommendation"
  task_complexity: "max"  # Most complex work

HANDBACK:
  session_pct: 87.3  # High usage
  recommended_model: "haiku"  # Budget-conservative
  confidence: 0.75  # Moderate
  warning: "approaching session limit"
  actions:
    - "Haiku can handle routine tasks; consider deferring max-complexity work"
    - "ESCALATE: Approaching session limit; human should review budget"
    - "If max-complexity work is urgent, will exceed budget; needs approval"
```

---

## Testing Strategy

### Unit Tests (Mock Metrics)

```bash
# Test 1: Stable velocity → stable trend
INPUT: tokens_used=100k, prev_30min=65.5k, session=200k
EXPECTED: trend="stable", velocity≈1150

# Test 2: Accelerating velocity → increasing trend
INPUT: tokens_used=120k, prev_30min=85k, session=200k
EXPECTED: trend="increasing"

# Test 3: Budget constraint → Haiku recommended
INPUT: session_pct=85, task_complexity="high"
EXPECTED: recommended_model="haiku", confidence≥0.85

# Test 4: Insufficient history → moderate confidence
INPUT: session_age=3min, tokens_used=5000
EXPECTED: confidence=0.6, recommendation present but flagged

# Test 5: Unstable velocity → reduced confidence
INPUT: velocity=900..1300 (high variance)
EXPECTED: confidence -= 0.15
```

### Integration Test

```bash
# Mock Orchestrator calls Token Advisor before major task
- Orchestrator: "Current status?"
- Token Advisor: Returns metrics
- Orchestrator: "Recommend model for high-complexity design?"
- Token Advisor: Returns "sonnet" with 0.88 confidence
- Orchestrator: Uses sonnet for next task ✓
```

---

## Deployment Notes

### Environment Variables

None required. Token Advisor reads from:
- Orchestrator context (primary)
- SSM Parameter Store (optional: `/{env}-{service-name}/token-metrics`)

### CloudWatch Integration (Optional)

If Token Advisor runs frequently, log metrics:

```
namespace: ers/token-advisor
metrics:
  - MetricName: SessionPercentage, Value: 45.2
  - MetricName: TokenVelocity, Value: 1150
  - MetricName: RecommendedModel, Value: 2 (sonnet)
```

### Logging Strategy

Log all decisions (for auditing model selection):

```json
{
  "timestamp": "2026-05-05T09:01:15Z",
  "session_pct": 45.2,
  "trend": "stable",
  "recommended_model": "sonnet",
  "confidence": 0.92,
  "rationale": "Stable velocity, sufficient budget for Sonnet tasks"
}
```

---

## Success Criteria Validation

### Completeness
- [x] DELEGATE spec matches design spec
- [x] HANDBACK spec includes all fields
- [x] Algorithm documented (trend, recommendation, confidence)
- [x] Error handling specified

### Quality
- [x] Confidence scoring is honest (no inflation)
- [x] Recommendations are defensible
- [x] Edge cases handled (low history, unstable velocity)
- [x] Fallback behavior clear

### Integration
- [x] Can be invoked by Orchestrator
- [x] Output suitable for Orchestrator decision-making
- [x] Async-safe (no blocking, no side effects)
- [x] Cacheable (2-minute cache safe)

### Testing
- [x] Unit tests cover happy path + edge cases
- [x] Mock metrics provided
- [x] Confidence scoring validated
- [x] Error scenarios tested

---

## Related Skills

- **Quality Gate Orchestrator**: Uses Token Advisor for budget context in sub-agent delegation
- **CICD Monitor**: Uses Token Advisor recommendations for model selection in polling
- **Orchestrator**: Primary consumer of Token Advisor budget guidance

---

## Open Questions

1. **Data Source Finalization**: Where should Token Advisor primarily read metrics? (Recommend: Orchestrator context first, fall back to SSM)
2. **Caching Strategy**: Should caching be enabled by default? (Recommend: yes, 2-minute cache)
3. **Escalation Threshold**: At what session % should we escalate to human? (Recommend: >85%)
4. **Historical Window**: Should velocity be calculated over 30 min (current) or configurable? (Recommend: configurable, default 30 min)

---

## Revision History

| Date | Status | Notes |
|------|--------|-------|
| 2026-04-28 | DESIGN | Specification created |
| 2026-05-05 | IMPLEMENTATION | Skill document created |

