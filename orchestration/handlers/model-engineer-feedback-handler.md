---
name: Model Engineer Feedback Handler
description: Analyzes token efficiency and recommends optimal model for next similar task
type: handler
phase: 6
status: IMPLEMENTATION_READY
---

# Model Engineer Feedback Handler

**Purpose**: Async feedback loop. After quality gate completes, analyze token usage per agent and recommend optimal model tier for next similar task.

---

## Handler Logic

```
WHEN Quality Gate Orchestrator writes final HANDBACK:

INPUT:
  - orchestrator_handback: {final_decision, audit_trail, ...}
  - sub_agent_handbacks (from artifacts/):
    * Security Agent: {status, tokens_used, model}
    * Testing Agent: {status, tokens_used, model}
    * Metrics Agent: {status, tokens_used, model}
    * Healing Agent: {status, tokens_used, model}
  - task_type: inferred from commit message or repo_path
  - observed_latency_ms: total time for all sub-agents

PROCESS:

  1. EXTRACT observed token usage per agent
     For each agent:
       tokens_observed = {actual tokens from handback}
       tokens_estimated = {pre-estimated from agent spec}
       efficiency = tokens_observed / tokens_estimated
  
  2. ANALYZE efficiency per agent
     
     FOR security_agent:
       efficiency = observed_tokens / 3000
       IF efficiency < 0.5:
         recommendation = DOWNGRADE_CANDIDATE
       ELIF efficiency 0.5-0.8:
         recommendation = APPROPRIATE
       ELSE (efficiency > 0.8):
         recommendation = UPGRADE_CANDIDATE
     
     # Similar logic for testing, metrics, healing
  
  3. CALCULATE confidence per recommendation
     
     base_confidence = 0.70  # Start conservative
     
     IF agent_status == PASS:
       confidence += 0.15  # Works correctly
     ELSE:
       confidence -= 0.20  # Failed, be cautious
     
     IF sample_size > 20:
       confidence += 0.10  # Enough data to trust
     ELIF sample_size < 3:
       confidence -= 0.15  # Too few samples
     
     IF recommendation == APPROPRIATE:
       confidence = max(confidence, 0.90)  # Stay the course
     
     IF recommendation == DOWNGRADE:
       confidence = min(confidence, 0.85)  # Downgrades are risky
  
  4. LOOKUP historical recommendations
     Query artifacts/feedback/ for task_type:
       prev_recommendations = [
         {model: sonnet, confidence: 0.80, actual_result: PASS},
         {model: sonnet, confidence: 0.75, actual_result: PASS},
         {model: haiku, confidence: 0.60, actual_result: FAIL},
       ]
     
     Calculate: success_rate_by_model = {
       sonnet: 2/2 = 100%,
       haiku: 0/1 = 0%
     }
  
  5. DETERMINE next recommendation
     
     RECOMMENDATION = {
       agent_type: "testing",
       current_model: "haiku",
       recommended_model: "sonnet",
       reasoning: f"
         Efficiency: {efficiency:.1%} (high utilization).
         Status: PASS (working correctly).
         Success rate: 100% on Sonnet (100%) vs 0% on Haiku (0%).
         Recommend staying with Sonnet.
       ",
       confidence: 0.88,
       sample_size: 5,
       next_action: "USE_RECOMMENDED" if confidence > 0.7 else "COLLECT_MORE_DATA"
     }
  
  6. STORE recommendations in artifacts/
     File: artifacts/2026-MM-DD/FEEDBACK-{timestamp}-model-engineer.yaml
     
     Format:
     ```yaml
     task_type: commit-quality-gate
     timestamp: {iso8601}
     recommendations:
       security:
         current_model: opus
         recommended_model: opus
         confidence: 0.92
         reasoning: "Tokens 2845/3000 (95%), status PASS. Keep Opus for security."
       testing:
         current_model: haiku
         recommended_model: haiku
         confidence: 0.95
         reasoning: "Tokens 1200/5120 (24%), status PASS. Haiku sufficient."
       metrics:
         current_model: haiku
         recommended_model: haiku
         confidence: 0.90
         reasoning: "Tokens 950/1500 (63%), status PASS. Haiku appropriate."
       healing:
         current_model: sonnet
         recommended_model: sonnet
         confidence: 0.88
         reasoning: "Tokens 3200/4000 (80%), status PASS. Sonnet working well."
     total_tokens_used: 8195
     efficiency_score: 0.64
     next_suggested_models:
       security: opus
       testing: haiku
       metrics: haiku
       healing: sonnet
     ```
  
  7. UPDATE decision history (append-only log)
     File: artifacts/feedback/model-recommendations.jsonl (newline-delimited JSON)
     
     Append one line per run:
     ```json
     {"timestamp": "2026-05-26T09:04:35Z", "task_type": "commit-quality-gate", "agent": "testing", "current_model": "haiku", "recommended_model": "haiku", "confidence": 0.95, "outcome": "PASS"}
     ```
  
  8. WRITE OpenTelemetry span
     - span_name: "model-engineer-feedback"
     - parent_span_id: {quality-gate-root}
     - attributes: {
         current_model, recommended_model, confidence,
         tokens_observed, tokens_estimated, efficiency,
         outcome_pass_fail
       }
     - events: [{name: "recommendation_generated", attributes: {recommendation}}]

OUTPUT:

  HANDBACK = {
    handoff_type: HANDBACK,
    task_id: {original_task_id},
    timestamp: {iso8601_now},
    status: complete,
    recommendations: { per-agent details },
    total_tokens_used: {sum},
    efficiency_score: {mean efficiency},
    decision_quality: {PASS/FAIL based on actual outcome},
    confidence: {mean confidence across recommendations},
    next_suggested_models: { agent → model mapping },
    attributes: {
      task_type: "commit-quality-gate",
      sample_size: {how many runs collected},
      success_rate_vs_recommended: {e.g., 95%},
      cost_savings_potential: {e.g., "$50/month if downgrade applied"}
    }
  }
  
  Write to: artifacts/2026-MM-DD/FEEDBACK-{timestamp}-model-engineer.yaml

FEEDBACK LOOP CLOSURE:

  Next similar commit arrives (same task_type):
    
    IF recommendation.confidence > 0.7:
      → Use recommended_model instead of current default
      → Track outcome (PASS/FAIL)
      → After execution:
         IF outcome == PASS:
           confidence += 0.1 (validate recommendation)
         ELSE:
           confidence -= 0.2 (recommendation failed)
        → Update recommendation in artifacts/feedback/
    
    ELSE:
      → Use default model
      → Collect more data (3-5 more runs)
      → Recalculate confidence
```

---

## Example: Token Efficiency Analysis

**Scenario**: Testing Agent ran with Haiku model

```yaml
Agent: Testing
Current Model: haiku
Tokens Observed: 1200
Tokens Estimated: 5120
Efficiency: 23.4%

Status: PASS (0 failures, 87.3% coverage)

Analysis:
  - Haiku used only 23% of estimated tokens
  - Task is structured output parsing (test counting)
  - Haiku strength: parsing and counting
  - Recommendation: Keep Haiku, even more confident
  
Confidence Calculation:
  base = 0.70
  + 0.15 (status PASS)
  + 0.10 (efficiency indicates task is routine)
  = 0.95 confidence → Haiku is right choice
```

---

## Example: Upgrade Recommendation

**Scenario**: Healing Agent ran with Sonnet, used 95% of tokens, had low success rate

```yaml
Agent: Healing
Current Model: sonnet
Tokens Observed: 3800
Tokens Estimated: 4000
Efficiency: 95%

Status: PASS but escalations: 5

Analysis:
  - Sonnet used 95% of available tokens
  - High utilization suggests complexity
  - 5 low-confidence fixes escalated to human
  - Task: code generation + fix application
  - Recommendation: Try Opus for more capacity
  
Confidence Calculation:
  base = 0.70
  - 0.20 (many escalations)
  + 0.15 (status PASS despite escalations)
  + 0.10 (high efficiency suggests Sonnet was right)
  = 0.75 confidence → Opus worth trying
  
Next Action: "EVALUATE_UPGRADE"
```

---

## Success Criteria (Phase 6 Testing)

- ✅ Correctly calculates efficiency per agent
- ✅ Confidence scores range 0.0–1.0 with clear rationale
- ✅ Historical data lookup works (queries model-recommendations.jsonl)
- ✅ Recommendations store in artifacts/ with proper YAML format
- ✅ Append-only log works (newline-delimited JSON)
- ✅ 20+ runs show trending (models becoming more/less recommended)
- ✅ Downgrade recommendations have lower initial confidence than status-quo
- ✅ Upgrade recommendations only when efficiency > 80% or failures detected
- ✅ OpenTelemetry spans capture recommendation metadata
- ✅ No false recommendations (e.g., downgrading a model that's actually needed)

---

## Integration: Applying Recommendations

**Next Quality Gate run (same task_type)**:

```
Orchestrator receives DELEGATE for similar task.

Check artifacts/feedback/ for prior recommendations:
  - Task type matches?
  - Recommendation exists?
  - Confidence > 0.7?

IF yes:
  Use recommended model for sub-agents
  (e.g., if Testing recommended Haiku, use Haiku)

ELSE:
  Use default model
  Collect data for next recommendation

After execution:
  Model Engineer updates recommendation confidence:
    IF outcome PASS: confidence += 0.1
    IF outcome FAIL: confidence -= 0.2
```

This creates a continuous optimization loop that learns which model is best for each task type over time.
