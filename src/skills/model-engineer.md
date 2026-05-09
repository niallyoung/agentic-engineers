---
name: Model Engineer
description: Token efficiency analyzer & model recommender - continuous feedback loop for agent optimization
type: skill
phase: 6.1
status: ACTIVE
model: claude-haiku
effort: medium
---

# Model Engineer Skill — AI Model Optimization Feedback Loop

Analyzes agent execution metrics and recommends optimal Claude models for future similar tasks.

## Role

**Continuous learning system** that tracks:
- Which model performed best (tokens/quality ratio)
- Task complexity vs. model choice accuracy
- Cost efficiency trends
- Confidence score calibration

## Input: HANDBACK Metrics

Receives from any sub-agent HANDBACK:

```yaml
---
handoff_type: HANDBACK
task_id: {task_id}
routed_agent: {agent_name}
routed_model: {model_used}
metrics:
  tokens_used: 2400
  duration_seconds: 180
  quality_score: 92
  complexity_estimate: "high"
  has_plan: false
  routing_confidence: 0.88
---
```

## Analysis Engine

```
WHEN HANDBACK received from sub-agent:

1. EXTRACT metrics
   - tokens_used: 2400
   - duration_seconds: 180
   - quality_score: 92
   - task_complexity: high
   - model_used: sonnet-4-6
   - routing_confidence: 0.88

2. CALCULATE efficiency scores
   
   token_efficiency = quality_score / tokens_used
     Example: 92 / 2400 = 0.0383 (quality per token)
   
   time_efficiency = quality_score / duration_seconds
     Example: 92 / 180 = 0.511 (quality per second)
   
   cost_per_point = tokens_used / quality_score
     Example: 2400 / 92 = $0.026 per quality point
   
   overall_efficiency = (token_efficiency + time_efficiency) / 2

3. LOOKUP historical data for same task type
   
   Similar tasks with same:
   - task_type (feature, bugfix, refactor, etc.)
   - complexity_estimate (high, medium, low)
   - has_plan (true/false)
   
   Compare:
   - Haiku efficiency on similar tasks
   - Sonnet efficiency on similar tasks
   - Opus efficiency on similar tasks (if available)

4. DETERMINE model recommendation
   
   IF this model (e.g., Sonnet) outperformed others:
     CONFIDENCE += 0.05 (up to 0.95)
     RECOMMEND: Use Sonnet for next similar task
   
   ELIF another model (e.g., Haiku) would be more efficient:
     CONFIDENCE -= 0.05 (down to 0.65)
     RECOMMEND: Try Haiku next time, measure results
   
   ELIF model choice was wrong (high confidence but low quality):
     FLAG: Routing decision was inaccurate
     NOTIFY: General Orchestrator to adjust routing rules

5. CALCULATE routing accuracy
   
   routing_accuracy = actual_quality / expected_quality
   
   If confidence was 0.88 and quality was 92 (expected ~90):
     accuracy = 92 / 90 = 1.02 (102% — routing was good!)
   
   Track: Did confident routing decisions yield good results?

6. UPDATE confidence scores
   
   FOR EACH future similar task:
     model_confidence[sonnet] = 0.92 (demonstrated excellence)
     model_confidence[haiku] = 0.65 (underperformed on this complexity)
     model_confidence[opus] = 0.80 (would be overkill for cost)

7. WRITE analysis to metrics database
   
   ```json
   {
     "task_id": "2026-05-07-feature-oauth-rotation",
     "task_type": "feature",
     "complexity": "high",
     "has_plan": false,
     "routed_agent": "Senior Engineer",
     "routed_model": "sonnet-4-6",
     "routed_confidence": 0.88,
     "actual_quality": 92,
     "tokens_used": 2400,
     "duration_seconds": 180,
     "token_efficiency": 0.0383,
     "time_efficiency": 0.511,
     "routing_accuracy": 1.02,
     "recommendation": {
       "model": "sonnet-4-6",
       "confidence_update": "+0.05 → 0.93",
       "reason": "Excellent execution on complex work without plan. Sonnet ideal for this task type."
     }
   }
   ```

8. AGGREGATE weekly trends
   
   Every 7 days, calculate:
   - Average routing accuracy (target: >0.95)
   - Model efficiency distribution (which model best per complexity?)
   - Cost trends (total tokens trending up/down?)
   - Quality trends (QA scores improving?)
   
   OUTPUT: Trend report for next week's routing adjustments

9. TRIGGER feedback to General Orchestrator
   
   IF routing accuracy < 0.90 for task type:
     ALERT: "Routing rules for {task_type} need adjustment"
     SUGGEST: "Consider routing {complexity} tasks to {better_model}"
   
   IF model efficiency changed significantly:
     UPDATE: General Orchestrator confidence tables
     REASON: "Historical data shows Haiku now more efficient for this pattern"
```

## Output: Recommendation Report

```yaml
---
handoff_type: MODEL_ENGINEER_ANALYSIS
task_id: 2026-05-07-feature-oauth-rotation
timestamp: 2026-05-07T14:35:00Z
original_routing:
  agent: Senior Engineer
  model: sonnet-4-6
  confidence: 0.88
actual_results:
  quality_score: 92
  tokens_used: 2400
  duration_seconds: 180
analysis:
  token_efficiency: 0.0383 (quality/token)
  time_efficiency: 0.511 (quality/second)
  routing_accuracy: 1.02 (102% — routing was accurate!)
  model_assessment:
    sonnet_4_6:
      efficiency_score: 0.85 (excellent)
      vs_haiku: "Sonnet 2.5x more efficient for complex planning"
      vs_opus: "Sonnet same quality, 40% cheaper than Opus"
      recommendation: "Excellent choice. Use Sonnet for similar complexity."
recommendation:
  next_model_for_similar_tasks: "sonnet-4-6"
  confidence_adjustment: "+0.05 → 0.93"
  reasoning: "Demonstrated expertise on complex unscoped work. Routing decision was sound."
weekly_trends:
  avg_routing_accuracy: 0.96 (target: >0.95 ✅)
  best_model_by_complexity:
    high: "sonnet-4-6 (0.92 avg quality)"
    medium: "haiku-4-5 (0.88 avg quality, 60% cheaper)"
    low: "haiku-4-5 (0.85+ quality, 40% faster)"
  cost_trend: "stable (no drift)"
  quality_trend: "↑ improving (+2 pts this week)"
feedback_to_orchestrator:
  action: "Update confidence tables"
  changes:
    - task_type: "feature"
      complexity: "high"
      has_plan: false
      model: "sonnet-4-6"
      confidence: 0.93 (was 0.88)
---
```

## Data Schema: Metrics Store

```yaml
# File: ~/.agents/agentic-engineers/data/metrics/task-metrics.yaml
task_metrics:
  - task_id: "2026-05-07-feature-oauth-rotation"
    timestamp: "2026-05-07T14:35:00Z"
    task_type: "feature"
    complexity: "high"
    has_plan: false
    is_cross_service: false
    is_security_scoped: false
    routed_agent: "Senior Engineer"
    routed_model: "sonnet-4-6"
    routed_confidence: 0.88
    actual_quality: 92
    tokens_used: 2400
    duration_seconds: 180
    token_efficiency: 0.0383
    time_efficiency: 0.511
    routing_accuracy: 1.02
    model_recommendation: "sonnet-4-6"
    confidence_update: 0.05
    feedback_status: "updated"
```

## Weekly Trend Aggregation

```yaml
# File: ~/.agents/agentic-engineers/data/metrics/weekly-trends.yaml
week_2026_05_07:
  total_tasks: 12
  avg_routing_accuracy: 0.96
  total_tokens: 28000
  avg_tokens_per_task: 2333
  avg_quality: 88
  quality_trend: "↑ +2 from last week"
  model_distribution:
    haiku:
      tasks: 5
      avg_quality: 84
      avg_tokens: 1200
      efficiency: 0.07
      use_cases: ["low-medium complexity with plan", "validation", "testing"]
    sonnet:
      tasks: 6
      avg_quality: 91
      avg_tokens: 3100
      efficiency: 0.029
      use_cases: ["complex work without plan", "design", "planning"]
    opus:
      tasks: 1
      avg_quality: 96
      avg_tokens: 5200
      efficiency: 0.0185
      use_cases: ["security-critical", "cross-service architecture"]
  routing_accuracy_by_type:
    feature: 0.94
    bugfix: 0.98
    refactor: 0.91
    review: 0.96
    design: 0.89
  cost_analysis:
    total_cost: "$0.42 (sample week)"
    cost_per_quality_point: "$0.0048"
    vs_previous_week: "-3% (improvement)"
  recommendations:
    - "Haiku showing excellent value on medium-complexity, planned work"
    - "Sonnet dominant on complex design (expected)"
    - "Opus used 1x; consider if alternatives available"
    - "Refactor routing confidence should increase (0.91 → 0.94 opportunity)"
```

## Integration Points

**Input:**
- Sub-agent HANDBACK blocks (any agent)
- General Orchestrator routing decisions
- Quality Gate results

**Output:**
- Confidence table updates (JSON)
- Trend reports (YAML)
- Alerts to General Orchestrator (if routing broken)
- Weekly recommendation emails

**Feedback Loop:**
- Task executed → metrics collected → analysis → recommendations → next task uses updated confidence

## Success Criteria

- ✅ Accuracy detection (routing decisions proved right/wrong)
- ✅ Efficiency scoring (tokens, time, quality normalized)
- ✅ Model comparison (which model best for this pattern?)
- ✅ Confidence calibration (confident high → high quality)
- ✅ Weekly trend reports (cost, quality, accuracy)
- ✅ Routing feedback (alerts when accuracy < 0.90)
- ✅ Continuous improvement (confidence scores update in real-time)

## Example: Weekly Report

```
## Model Engineer Weekly Report — Week of 2026-05-07

**Overall Performance:** Excellent (96% routing accuracy, +2 quality points)

**Model Efficiency Ranking:**
1. Haiku-4-5: 0.07 quality/token (best value)
2. Sonnet-4-6: 0.029 quality/token (best for complex)
3. Opus-4-7: 0.0185 quality/token (max capability)

**Cost Trend:** -3% vs last week ($0.42 → $0.41 average)

**Routing Recommendations:**
- Increase Sonnet confidence for complex-no-plan: 0.88 → 0.93 ✅
- Increase Haiku confidence for medium-with-plan: 0.85 → 0.90 ✅
- Monitor refactor routing: accuracy 0.91 (target >0.95)

**Action Items:**
- General Orchestrator to update confidence tables
- Next similar high-complexity task: Use Sonnet (0.93 confidence)
- Consider Haiku trial on next medium-complexity task (cost test)
```

---

## Phase 6.1 Integration

Part of three-pronged feedback loop:
1. **Model Engineer** (this file) — Model optimization
2. **Quality Gate Aggregation Handler** — Trend analysis
3. **Config Enforcement Verification** — Auto-fix validation
