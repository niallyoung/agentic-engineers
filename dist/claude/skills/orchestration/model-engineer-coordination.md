# Orchestrator — Model Engineer Coordination

**Role:** Orchestrator (Haiku, low effort)  
**Purpose:** Coordinate feedback from Quality Engineer to Model Engineer, enabling continuous improvement of model assignments

---

## Overview

Model Engineer Coordination manages the feedback loop from QE verification back to Model Engineer analysis, ensuring that quality observations improve future routing decisions.

**Input:** Task completion with QE feedback, previous model assignment, quality score  
**Output:** Updated model assignment recommendations ready for next similar task

**Goal:** Create a self-improving system where each task makes future similar tasks better routed.

---

## Feedback Flow Architecture

```
Task Execution
   ↓
HANDBACK (Agent returns with tokens, quality estimate)
   ↓
Metrics Collection (Orchestrator records to ~/.claude/metrics/)
   ↓
Quality Verification (QE reviews, adds model_assessment feedback)
   ↓
Metrics Update (Orchestrator records QE feedback)
   ↓
Model Engineer Analysis (reads task metrics + QE feedback)
   ├─ model-analysis.md (analyze quality/cost/tokens)
   ├─ quality-feedback-analysis.md (extract patterns from QE notes)
   ├─ model-comparison.md (compare models across samples)
   └─ cost-quality-tradeoff.md (evaluate upgrade/downgrade)
   ↓
Model Engineer Recommendation (outputs ranking of best models)
   ↓
Orchestrator Applies (next similar task uses rank_1 recommendation)
```

---

## Real-Time Feedback Integration

As QE completes verification:

1. **QE provides model_assessment** (haiku_suitable, sonnet_suitable, etc.)
2. **Orchestrator adds to metrics** (metrics-collection.md appends QE feedback)
3. **Model Engineer flag set** (task ready for model analysis)
4. **Next similar task** checks for updated recommendation

Example metrics update:

```
Before QE:
~/.claude/metrics/2026-04-24/2026-04-24-redis-caching.json
{
  "quality_score": 92,
  "model": "haiku",
  "tokens_in": 18500
}

After QE:
~/.claude/metrics/2026-04-24/2026-04-24-redis-caching.json
{
  "quality_score": 92,
  "model": "haiku",
  "tokens_in": 18500,
  "qe_feedback": {
    "recommendation": "haiku_suitable",
    "confidence_for_similar_tasks": 0.92
  }
}
```

---

## Model Assignment Update Process

### Trigger: New Task Arrives

1. **Orchestrator identifies task type** (task_type, repo, complexity)
2. **Look up historical data:**
   - Previous tasks with same signature (task_type + repo + complexity)
   - Model Engineer recommendations for this signature
3. **Apply recommendation** (if confidence ≥ 0.60)
4. **Create DELEGATE** with recommended model/effort

Example:

```
Task: Feature in {service-name}, medium-complexity
Historical lookup: 5 previous medium-complexity features in {service-name}
Model Engineer recommendation: Haiku high-effort (confidence 0.92)
Action: Use Haiku in DELEGATE
```

### Trigger: Quality Anomaly Detected

If QE feedback differs from expectation:

```
Scenario: Haiku task returned quality 72 (expected 90+)
QE assessment: "haiku_would_be_better" (indicates model was under-scoped)

Action:
1. Flag task for Model Engineer review
2. Next similar task: downgrade confidence on Haiku
3. If pattern continues (2+ anomalies): escalate to Sonnet
4. Trigger A/B test to evaluate Sonnet on this task type
```

### Trigger: Model Engineer Generates Recommendation

After Model Engineer completes analysis:

1. **Update assignment table** (replace previous recommendation with new one)
2. **Record decision log** (what changed and why)
3. **Apply to pending tasks** (any tasks waiting for this signature get updated)
4. **Log the change** (timestamp, old model, new model, reasoning)

Example log:

```json
{
  "timestamp": "2026-04-24T19:00:00Z",
  "task_signature": {
    "task_type": "feature",
    "repo": "{service-name}",
    "complexity": "medium"
  },
  "previous_assignment": {
    "model": "haiku",
    "effort": "high",
    "confidence": 0.75
  },
  "new_assignment": {
    "model": "haiku",
    "effort": "high",
    "confidence": 0.92
  },
  "change_reason": "5 new samples, all 90+, cost stable at $0.13",
  "samples_analyzed": 5,
  "avg_quality": 90.4,
  "escalation_rate": 0.0
}
```

---

## Coordination Workflows

### Workflow 1: Regular Task → Updated Recommendation

```
Day 1: Task "medium-complexity auth" completes
  → HANDBACK: quality 90, tokens 18.5K, cost $0.13
  → Metrics recorded
  → QE: "haiku_suitable" (confidence 0.88)
  
Day 1 (17:00): TokenAdvisor analyzes metrics
  → Finds 1 sample for this task signature
  → Model Engineer flags for continued data collection
  
Day 7: Same task type arrives (medium-complexity auth)
  → Look up assignment: 1 sample, confidence 0.88, model haiku
  → Use haiku (acceptable confidence)
  
Day 30: After 5+ samples collected
  → Model Engineer analyzes: quality avg 90.4, cost $0.13
  → Generates recommendation: haiku (confidence 0.92)
  → Orchestrator updates assignment table
  → Future auth tasks get 0.92 confidence
```

### Workflow 2: Anomaly Detection & Escalation

```
Task: medium-complexity feature in {service-name}
DELEGATE: Use haiku (baseline assignment)
HANDBACK: quality 76 (lower than expected)
QE: "sonnet_would_be_better" (task was more complex than estimated)

Orchestrator detects anomaly:
  → Expected quality ≥85, got 76
  → QE recommends upgrade
  
Action:
  1. Flag task for Model Engineer review (anomaly)
  2. Next similar task: check Model Engineer recommendation before using baseline
  3. If no recommendation yet: escalate to Senior Engineer as precaution
  4. Trigger A/B test for {service-name} medium-complexity (Haiku vs Sonnet)
```

### Workflow 3: Model Upgrade Decision

```
After A/B test completes (10 tasks, 5 Haiku vs 5 Sonnet):
  Haiku avg quality: 85.2, cost: $0.13
  Sonnet avg quality: 92.1, cost: $0.18

Model Engineer analyzes cost-quality-tradeoff:
  Quality improvement: +6.9 points
  Cost increase: +38%
  Cost-per-point improvement: $0.0072
  Recommendation: "Consider Sonnet for {service-name}"

Orchestrator decision:
  → If cost target active: Keep Haiku, monitor
  → If quality target active: Upgrade to Sonnet
  → Default: Escalate to human for business decision
```

---

## Decision Logging

Maintain log of all routing decisions and why:

```json
{
  "task_id": "2026-04-24-cache-feature",
  "timestamp": "2026-04-24T17:00:00Z",
  
  "routing_decision": {
    "role": "Engineer",
    "model": "haiku",
    "effort": "high",
    "confidence": 0.95
  },
  
  "decision_basis": "Model Engineer recommendation for medium-complexity {service-name} features",
  
  "assignment_source": "model_engineer_recommendation",
  "recommendation_id": "redis-caching-2026-04-24",
  "recommendation_confidence": 0.92,
  
  "alternative_considered": {
    "model": "sonnet",
    "reason": "Not recommended for this signature; cost premium not justified"
  }
}
```

This log enables tracking:
- Which recommendations were used (and which ignored)
- Whether recommendations improved outcomes
- Recommendation accuracy over time

---

## Handling Recommendation Gaps

**If no Model Engineer recommendation exists:**

1. Use baseline assignment from AGENTS.md routing rules
2. Collect QE feedback as usual
3. Flag task for Model Engineer to build initial recommendation
4. After 3-5 samples: Model Engineer generates recommendation

**If Model Engineer recommendation changes mid-day:**

1. Tasks already in progress: continue with original assignment
2. Tasks dispatched after update: use new assignment
3. Log all transitions for anomaly tracking

**If confidence drops below 0.60:**

1. Escalate to next higher model (Haiku → Sonnet)
2. Collect more data before reverting
3. Trigger A/B test if multiple rework loops observed

---

## Integration Points

### With Metrics Collection

- Metrics collector records model recommendation ID for each task
- Enables tracking: "How many tasks used this recommendation?"
- Enables analysis: "Did recommendation improve outcomes?"

### With TokenAdvisor

- TokenAdvisor reads Model Engineer recommendations
- Proposes cost optimization opportunities
- Escalates confidence concerns

### With A/B Testing

- Orchestrator coordinates A/B test task allocation
- Uses Model Engineer recommendations to select control arm
- Tests recommendation for predicted improvement

---

## SLA & Cadence

### Model Engineer Turnaround

- **Real-time tasks:** Analyze within 5 min of QE completion (high-priority issues)
- **Daily batch:** Analyze all tasks daily at 17:00 (TokenAdvisor scheduler)
- **Weekly review:** Generate recommendations weekly (update assignment table)
- **Monthly recalibration:** Full analysis on all task signatures

### Orchestrator Response

- **Check recommendation:** On every new task (~1 sec)
- **Apply recommendation:** Use rank_1 if confidence ≥ 0.85
- **Escalate if needed:** Use rank_2 if confidence 0.60-0.85 (use with caution)
- **Revert if needed:** Use fallback if confidence <0.60 (flag for investigation)

---

## Success Metrics

Track coordination effectiveness:

```json
{
  "metrics": {
    "recommendations_used": 42,
    "recommendations_used_percent": 95,
    "tasks_improved_by_recommendation": 40,
    "improvement_rate": 95.2,
    "avg_recommendation_confidence": 0.88,
    "tasks_escalated_due_to_anomaly": 2,
    "escalation_rate": 4.8
  }
}
```

**Target:** 
- ≥90% recommendations used (shows adoption)
- ≥85% improvement rate (recommendations are accurate)
- Escalation rate <5% (system is stable)
- Avg confidence ≥0.80 (recommendations are confident)

---

## Failure Modes & Recovery

### Anomaly: Recommendation Not Accurate

If Model Engineer recommendation predicts quality 90 but actual is 75:
1. Investigate root cause (was complexity underestimated? task scope changed?)
2. Update confidence score downward
3. Review all similar outstanding tasks
4. Trigger targeted A/B test for this signature

### Anomaly: Confidence Drifting Down

If recommendation confidence drops from 0.92 to 0.60 over 3 weeks:
1. Analyze new samples for quality variations
2. Check if task type characteristics changing
3. Review QE feedback for consistent concerns
4. Escalate to human if pattern unclear

### Anomaly: Cost Increasing Despite Recommendation

If recommended model's cost rising while quality flat:
1. Check if token usage increasing (scope creep?)
2. Review DELEGATE clarity (are requirements changing?)
3. Escalate to Orchestrator for task scope review
4. Consider downgrading model if cost becomes critical

---

## Documentation & Transparency

Every recommendation includes:
- Task signature (what tasks it applies to)
- Confidence level (how sure we are)
- Historical data (number of samples, date range)
- Reasoning (why this model over alternatives)
- Next review trigger (when to reassess)

This transparency enables:
- Engineers to understand routing decisions
- Model Engineer to justify recommendations
- Orchestrator to override when appropriate
- Continuous learning and improvement
