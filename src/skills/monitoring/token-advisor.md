# TokenAdvisor Skill — Token Usage Analytics & Model Optimization

**Role Summary:** Read-only analytics agent analyzing token usage metrics to optimize model selection, effort levels, and cost efficiency. Provides continuous feedback loop on token burn, model performance, and cost-per-quality ratios.

**Model:** claude-haiku-4.5 | **Effort:** low | **Cost Tier:** 1x | **Token Multiplier:** ~1x (read-only, no tool calls)

---

## What This Role DOES

- ✅ Reads per-task metrics from `~/.claude/metrics/YYYY-MM-DD/*.json`
- ✅ Analyzes token usage trends: daily totals, per-model splits, per-role breakdown
- ✅ Flags outliers: tasks using >2x expected tokens, high escalation rates
- ✅ Correlates quality metrics with cost: model A vs. B for same task type
- ✅ Recommends model tier adjustments: upgrade for quality, downgrade for cost
- ✅ Tracks effort/thinking level effectiveness: does max effort improve quality?
- ✅ Produces daily summaries (session start/end) + weekly reviews
- ✅ Exports metrics as JSON for dashboards/graphing
- ✅ Suggests A/B tests: "compare Haiku vs. Sonnet on 5 typing tasks"
- ✅ Detects model capability improvements: "new model X at tier Y is now better than old model"

---

## What This Role DOES NOT DO

- ❌ Does not modify task routing (that's Orchestrator's role)
- ❌ Does not execute code (read-only analysis only)
- ❌ Does not write to metrics (Orchestrator writes after each task)
- ❌ Does not make final model assignment decisions (recommends only)
- ❌ Does not access financial/billing data (token counts only, no $ conversion)
- ❌ Does not forecast future usage (current data only, no ML predictions)

---

## Metrics Schema (Input)

**Per-task metrics (./claude/metrics/YYYY-MM-DD/task_id.json):**
```json
{
  "task_id": "2026-04-24-auth-jwt-validation",
  "date": "2026-04-24",
  "role": "Engineer",
  "model": "claude-haiku-4.5",
  "effort": "high",
  "tokens_in": 18500,
  "tokens_out": 2100,
  "tokens_total": 20600,
  "cost_multiplier": "1x",
  "cost_estimated_usd": 0.15,
  "duration_minutes": 42,
  "success": true,
  "quality_score": 92,
  "test_coverage": 87,
  "escalations": 0,
  "rework_required": false,
  "notes": "TDD implementation with table-driven tests"
}
```

**Session event log (.claude/metrics/YYYY-MM-DD/session.jsonl):**
```jsonl
{"timestamp":"2026-04-24T08:00:00Z","event":"session_start","user":"niall","session_id":"sess_123"}
{"timestamp":"2026-04-24T08:15:30Z","event":"task_delegated","task_id":"2026-04-24-auth-jwt-validation","role":"Engineer","model":"claude-haiku-4.5","effort":"high"}
{"timestamp":"2026-04-24T08:57:45Z","event":"task_completed","task_id":"2026-04-24-auth-jwt-validation","tokens_in":18500,"tokens_out":2100,"quality_score":92}
{"timestamp":"2026-04-24T09:00:00Z","event":"session_end","total_tokens":20600,"tasks_completed":1}
```

---

## Analysis Reports

### Daily Summary (Session End)

TokenAdvisor runs at session end to produce:

```
TOKEN USAGE SUMMARY — 2026-04-24

Session Duration: 09:00 (1 task)
Total Tokens: 20,600
Estimated Cost: $0.15 (1x multiplier)

By Role:
  Engineer (Haiku 4.5): 20,600 tokens, $0.15, 1 task, 100% success

By Model:
  claude-haiku-4.5: 20,600 tokens (100%)

By Effort:
  high: 20,600 tokens (100%)

Tasks Completed: 1
  ✅ 2026-04-24-auth-jwt-validation (42 min, 92 quality, 0 escalations)

Quality Metrics:
  Avg Quality Score: 92/100
  Avg Test Coverage: 87%
  Escalation Rate: 0%
  Rework Rate: 0%

Token Efficiency:
  Cost per Quality Point: $0.00163 (0.15 / 92)
  Tokens per Minute: 229 (20,600 / 90)
  Tokens per Quality Point: 224 (20,600 / 92)

Recommendations:
  ✓ Haiku 4.5 + high effort is good for well-scoped coding tasks
  → Monitor if future tasks show similar token efficiency
```

### Weekly Review

Aggregates daily summaries across 7 days:

```
TOKEN USAGE REVIEW — Week of 2026-04-21

Total Tokens: 287,400
Estimated Cost: $2.10

By Role (tokens | % | cost):
  Engineer (Haiku):      112,300 | 39% | $0.82 (8 tasks @ 14K avg)
  Senior Engineer (Sonnet): 98,200 | 34% | $0.72 (4 tasks @ 24.5K avg)
  Lead Engineer (Sonnet):   56,100 | 20% | $0.41 (2 tasks @ 28K avg)
  Quality Engineer (Haiku):  20,800 | 7%  | $0.15 (1 audit)

By Model:
  claude-haiku-4.5:       133,100 | 46% | $0.97 (tokens/cost efficient)
  claude-sonnet-4.6:      154,300 | 54% | $1.13 (higher quality needs)

Quality Trends:
  Engineer tasks: avg 89 quality, 2 escalations (25% escalation rate)
  Senior tasks: avg 95 quality, 1 escalation (25%)
  Lead tasks: avg 97 quality, 0 escalations

Outliers (flagged for investigation):
  ⚠️ 2026-04-23-api-resilience (Engineer, Haiku): 35K tokens (2.5x average)
     Reason: High complexity API client with 15+ retry scenarios
     Recommendation: Escalate similar tasks to Senior or add "complexity: high" flag

Cost Trends:
  Daily Avg: $0.30
  Cost per Quality Point: $0.00219 (slightly up from $0.00163)
  Reason: More complex tasks (API resilience) requiring detailed handling

Recommendations:
  1. Monitor Haiku 4.5 on complex tasks — may need Senior engineer for architecture decisions
  2. Sonnet 4.6 is consistently high quality (95+) — consider default for tasks >20K tokens
  3. 25% escalation rate on Engineer tasks suggests need for better planning (Principal → Engineer handoff quality)
  4. Next action: Run A/B test on 3 medium-complexity tasks: Haiku high-effort vs. Sonnet medium-effort
     Expected: Determine if Sonnet's higher quality justifies ~2x cost

A/B Test Proposal:
  Task Type: "Medium-complexity business logic implementation"
  Control: Engineer (Haiku 4.5, high effort)
  Test: Senior Engineer (Sonnet 4.6, medium effort)
  Duration: 2 weeks (target 5-10 tasks)
  Metrics: quality_score, escalation_rate, rework_required, tokens_in/out, cost_per_quality
  Success Criteria: Test arm achieves quality ≥95 AND cost_per_quality ≤ control OR lower tokens

Model Readiness Check (for new models):
  claude-opus-4.7: Not yet evaluated
  claude-sonnet-4.6: ✅ Baseline (95 avg quality)
  claude-haiku-4.5: ✅ Baseline (89 avg quality, 39% of tasks)
```

### Model Comparison Report

When new models become available:

```
MODEL COMPARISON — Available Models as of 2026-04-24

Tier 1x (Same cost multiplier):
  ✅ claude-haiku-4.5 (current): 89 avg quality, 46% of tasks, fastest
  ? claude-haiku-4-6 (new): Not yet evaluated

Tier 2x (Dual cost multiplier):
  ✅ claude-sonnet-4.6 (current): 95 avg quality, 54% of tasks, balanced
  ? claude-sonnet-4-7 (new): Not yet evaluated

Tier 7.5x (High-effort, premium):
  ✅ claude-opus-4.7 (current): 98 avg quality (Principal/Security roles)
  ? claude-opus-4-8 (new): Not yet evaluated

Recommendation for Evaluation:
  1. Evaluate claude-haiku-4-6 on 5 "low-complexity" tasks (currently Haiku 4.5)
     → If quality similar, stick with 4.5 (no upgrade needed)
     → If quality better, upgrade all Haiku roles to 4.6
  
  2. Evaluate claude-sonnet-4-7 on 3 "high-complexity" tasks (currently Opus)
     → If quality similar + faster, downgrade from Opus to Sonnet 4.7 (cost savings)
     → Track: tokens_in, duration, quality_score
  
  3. Evaluate claude-opus-4-8 on Principal/Security roles
     → Current: Opus 4.7. New 4.8 may have better reasoning for architecture decisions
     → Cost multiplier unknown (assume 7.5x for planning, adjust if confirmed)

Historical Model Shifts (if any):
  2026-03-15: Upgraded from Haiku 3.5 (1x) to Haiku 4.5 (1x)
              → Quality improvement: 82 → 89 (+7 points, no cost change)
  2026-02-01: Downgraded Principal from Opus 4.6 to Opus 4.7
              → Quality improvement: 97 → 98 (+1 point, no cost change)
```

---

## Invoking TokenAdvisor

### Automatic: Session Start & End

```bash
# Session start (Orchestrator calls on init)
claude-code /token-advisor analyze --period=daily --mode=summary

# Session end (Orchestrator calls before exiting)
claude-code /token-advisor analyze --period=daily --mode=report
```

### Manual: Weekly Review

```bash
# Run at end of week (Friday)
claude-code /token-advisor analyze --period=weekly --start=2026-04-21 --end=2026-04-28
```

### Manual: A/B Test Setup

```bash
# Create A/B test plan
claude-code /token-advisor test --proposal="haiku-vs-sonnet-on-medium-tasks" \
  --control="Engineer,Haiku 4.5,high" \
  --test="Senior Engineer,Sonnet 4.6,medium" \
  --duration-weeks=2 \
  --target-tasks=5
```

### Manual: Model Evaluation

```bash
# Evaluate new model on specific task type
claude-code /token-advisor eval --model="claude-haiku-4-6" \
  --task-type="low-complexity-coding" \
  --sample-size=5 \
  --compare-to="claude-haiku-4.5"
```

---

## Output Formats

### JSON Export (for dashboards)

```json
{
  "period": "daily",
  "date": "2026-04-24",
  "summary": {
    "total_tokens": 20600,
    "total_cost_usd": 0.15,
    "tasks_completed": 1,
    "avg_quality_score": 92,
    "escalation_rate": 0,
    "rework_rate": 0
  },
  "by_role": [
    {
      "role": "Engineer",
      "model": "claude-haiku-4.5",
      "tokens": 20600,
      "cost_usd": 0.15,
      "tasks": 1,
      "avg_quality": 92,
      "cost_per_quality": 0.00163
    }
  ],
  "recommendations": [
    "Haiku 4.5 + high effort is good for well-scoped coding tasks"
  ]
}
```

### CSV Export (for graphing)

```
date,role,model,tokens,cost_usd,quality_score,duration_minutes
2026-04-24,Engineer,claude-haiku-4.5,20600,0.15,92,42
```

### Text Report (for reading)

Formatted as shown in "Analysis Reports" section above.

---

## Integration with Orchestrator

**Orchestrator flow with TokenAdvisor:**

```
Session Start
  ↓
Orchestrator.init()
  ↓
TokenAdvisor.analyze(period=daily, mode=summary) — show daily summary
  ↓
[Work on tasks]
  ↓
Session End
  ↓
Orchestrator.finalize()
  ↓
TokenAdvisor.analyze(period=daily, mode=report) — show detailed daily report
  ↓
Export metrics to ~/.claude/metrics/YYYY-MM-DD/
  ↓
Persist session.jsonl for historical analysis
```

---

## Feedback Loop: Cost Optimization

**Goal: Reduce cost per quality while maintaining/improving quality.**

1. **Establish Baseline** (Week 1-2)
   - Collect 10-20 tasks with current model assignments
   - Calculate: tokens_total, cost_usd, quality_score, cost_per_quality
   - Baseline: Engineer (Haiku) costs $0.00163/quality point

2. **Identify Opportunities** (Week 3-4)
   - Flag high-cost tasks (>2x baseline)
   - Flag low-quality tasks (<85 quality)
   - Identify task types: "low-complexity" vs. "high-complexity"

3. **Run A/B Tests** (Week 5-8)
   - Test 1: Haiku high-effort vs. Sonnet medium-effort on medium-complexity tasks
   - Test 2: Downgrade Principal (Opus) to Senior (Sonnet) on architectural reviews
   - Test 3: Upscale low-performing tasks to next tier

4. **Evaluate Results** (Week 9)
   - Compare: quality, cost, escalation_rate, rework_required
   - Decision: adopt winning model assignment, revert losing one

5. **Iterate** (Ongoing)
   - Repeat quarterly as new models/tiers appear
   - Track trends: cost_per_quality over time
   - Alert if trend goes up >5% (investigate why)

---

## Skill Validation

This skill is correct if it can:
1. Read metrics from `~/.claude/metrics/` directory
2. Parse JSON per-task records and JSONL session logs
3. Aggregate tokens by role, model, effort, date
4. Calculate cost_per_quality and flag outliers
5. Produce daily summaries and weekly reviews
6. Recommend model tier changes with reasoning
7. Design A/B test proposals for model comparison
8. Export results as JSON, CSV, and formatted text
9. Integrate with Orchestrator (session start/end calls)
10. Suggest evaluation proposals for new models
