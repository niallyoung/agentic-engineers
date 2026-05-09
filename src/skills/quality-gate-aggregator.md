---
name: Quality Gate Aggregator
description: Analyzes QG sub-agent results, trends health metrics, recommends threshold adjustments
type: skill
phase: 6.1
status: ACTIVE
model: claude-haiku
effort: medium
---

# Quality Gate Aggregator — Health Trend Analysis & Auto-Tuning

Analyzes Quality Gate sub-agent results (Security, Testing, Metrics, Healing) and recommends dynamic threshold adjustments.

## Role

Post-QG analysis system that:
- Aggregates results from 4 parallel sub-agents
- Detects trend patterns (improving? degrading? stable?)
- Recommends threshold adjustments
- Alerts on anomalies (sudden increase in escalations)

## Input: Sub-Agent HANDBACKs

Receives from Quality Gate Orchestrator:

```yaml
security_agent_handback:
  status: PASS
  credentials_found: 0
  vulnerabilities: 0
  severity: NONE
  confidence: 0.98

testing_agent_handback:
  status: PASS
  tests_passed: 342
  tests_failed: 0
  coverage_pct: 87
  severity: NONE
  confidence: 0.95

metrics_agent_handback:
  status: PASS
  health_score: 88
  p99_latency_ms: 245
  error_rate_pct: 0.2
  severity: NONE
  confidence: 0.92

healing_agent_handback:
  status: PASS
  issues_found: 2
  fixes_applied: 2
  severity: MEDIUM
  confidence: 0.85
```

## Analysis Logic

```
WHEN Quality Gate Orchestrator finishes (all 4 sub-agents done):

1. AGGREGATE results into single view
   
   overall_status = PASS if all agents PASS
   escalation_reasons = [any ESCALATE statuses]
   max_severity = MAX(security, testing, metrics, healing severity)
   avg_confidence = AVG(security, testing, metrics, healing confidence)
   
2. RECORD into daily QG log
   
   File: ~/.agents/agentic-engineers/data/qg/daily-qg-log.yaml
   
   ```yaml
   - date: 2026-05-07
     time: 14:35:00Z
     commit_sha: abc123def456
     overall_status: PASS
     results:
       security: PASS (0 vulns, confidence 0.98)
       testing: PASS (342/342, 87% coverage)
       metrics: PASS (health 88, p99 245ms)
       healing: PASS (2 fixes applied)
     max_severity: MEDIUM (from healing)
     avg_confidence: 0.925
     escalation_reasons: []
   ```

3. TREND ANALYSIS (hourly, daily, weekly)
   
   // Hourly: Last 60 commits
   CALCULATE:
     - pass_rate (how many QG runs passed?)
     - escalation_frequency (escalations per 10 commits)
     - avg_health_score (from Metrics agent)
     - avg_coverage (from Testing agent)
     - vulnerability_trend (up/down/stable?)
   
   // Daily: Last 24 hours
   CALCULATE:
     - daily_pass_rate (target: 95%+)
     - escalation_count (baseline: <2 per day)
     - max_severity_observed (should be none)
     - avg_latency_trend (p99, p95)
     - auto_fix_success_rate (Healing: fixes that actually worked)
   
   // Weekly: Last 7 days
   CALCULATE:
     - week_pass_rate (target: 98%+)
     - escalation_trend (increasing? decreasing?)
     - quality_trend (coverage up/down?)
     - cost_trend (QG tokens stable?)

4. DETECT ANOMALIES
   
   IF escalation_frequency > baseline * 2:
     ALERT: "Escalations doubled compared to baseline"
     SUGGEST: "Check recent commits; may have introduced issues"
   
   IF avg_health_score drops > 5 points:
     ALERT: "System health degraded"
     SUGGEST: "Review metrics agent data; check for resource issues"
   
   IF vulnerability_count increases:
     ALERT: "New vulnerabilities detected"
     SUGGEST: "Security review needed; escalate to Security Engineer"
   
   IF test_coverage drops < 80%:
     ALERT: "Coverage below threshold"
     SUGGEST: "New code needs tests; enforce coverage gate"

5. CALCULATE threshold recommendations
   
   Current thresholds (hardcoded):
   - health_score >= 85 (PASS)
   - test_coverage >= 80% (PASS)
   - error_rate < 1% (PASS)
   - p99_latency < 500ms (PASS)
   - vulnerabilities = 0 (PASS)
   
   DYNAMIC ADJUSTMENT:
   
   IF daily_pass_rate > 98% for 3 consecutive days:
     RECOMMEND: Tighten thresholds (higher quality bar)
     Example: "health_score: 85 → 88" (3-point improvement)
   
   IF daily_pass_rate < 90% for 2 consecutive days:
     RECOMMEND: Loosen thresholds (service having issues)
     Example: "health_score: 85 → 82" (temporary accommodation)
   
   IF escalation_frequency stable and low:
     RECOMMEND: No change (thresholds well-calibrated)

6. WRITE recommendations to weekly report
   
   File: ~/.agents/agentic-engineers/data/qg/weekly-qg-report.yaml
   
   ```yaml
   week_2026_05_07:
     total_qg_runs: 47
     pass_rate: 0.96 (45/47, target 0.95 ✅)
     escalation_rate: 0.04 (2/47, baseline 0.03)
     avg_health_score: 86.2 (trend: ↑ +1.2)
     avg_coverage: 84.5 (trend: ↑ +2.1)
     max_severity: MEDIUM (from Healing, x2)
     anomalies:
       - "Healing agent found 2 config issues this week (normal)"
       - "Security clean all week (0 vulnerabilities)"
       - "Coverage trending up (good trend)"
     threshold_recommendations:
       - "PASS: Maintain current thresholds (well-calibrated)"
       - "SUGGESTED: Consider raising health_score 85→87 (trending up)"
       - "MONITOR: Escalation rate slightly above baseline (+33%)"
     action_items:
       - "No immediate action needed"
       - "Continue monitoring escalation trend"
       - "Congratulate team on improving coverage"
   ```

7. ALERT on critical changes
   
   IF escalation_frequency > baseline * 3:
     IMMEDIATE_ALERT: Page on-call
     REASON: "QG escalations tripled; investigate cause"
   
   IF vulnerabilities found after clean period:
     ESCALATE: Security Engineer
     REASON: "Vulnerability introduced; requires review"
   
   IF coverage drops > 10 points suddenly:
     ALERT: Quality Engineering team
     REASON: "Sudden coverage drop; may indicate broken tests"

8. INTEGRATE with Model Engineer
   
   SEND: Weekly aggregate scores to Model Engineer
   MESSAGE: "QG health metrics for optimization analysis"
   INCLUDE: Pass rate, escalation rate, severity trends
   
   RECEIVE: Routing accuracy feedback
   MESSAGE: "Did QG agents predict real issues?"
   ADJUST: Confidence in QG thresholds based on false positives/negatives

9. PUBLISH weekly dashboard update
   
   File: ~/.agents/agentic-engineers/data/qg/dashboard-data.json
   
   ```json
   {
     "week": "2026-05-07",
     "metrics": {
       "pass_rate": 0.96,
       "escalation_rate": 0.04,
       "health_score": 86.2,
       "coverage": 84.5,
       "vulnerability_count": 0
     },
     "trends": {
       "pass_rate": "↑ stable",
       "escalation_rate": "→ stable",
       "health_score": "↑ improving",
       "coverage": "↑ improving",
       "vulnerability_count": "✅ clean"
     },
     "recommendations": [
       "Maintain current thresholds (well-calibrated)",
       "Consider raising health_score threshold by 2 points",
       "Escalations normal; continue monitoring"
     ]
   }
   ```
```

## Output: Weekly QG Trend Report

```yaml
---
handoff_type: QG_AGGREGATION_REPORT
period: "week_2026_05_07"
timestamp: 2026-05-12T23:59:00Z

executive_summary:
  overall_health: "EXCELLENT"
  pass_rate: 0.96 (45/47 runs passed)
  escalation_rate: 0.04 (2/47 escalations, baseline 0.03)
  quality_trend: "IMPROVING ↑"
  confidence: 0.94

breakdown_by_agent:
  security:
    pass_rate: 1.0 (47/47 clean)
    vulnerabilities_found: 0
    critical_issues: 0
    trend: "Excellent — no vulnerabilities all week"
    recommendation: "Current rules working perfectly"
  
  testing:
    pass_rate: 0.98 (46/47)
    avg_coverage: 84.5
    coverage_trend: "↑ +2.1 points"
    test_failures_week: 1 (in 1 commit)
    recommendation: "Encourage team — coverage improving"
  
  metrics:
    pass_rate: 0.94 (44/47)
    avg_health_score: 86.2
    health_trend: "↑ +1.2 points"
    escalations: 3 (health < 85)
    p99_latency_trend: "stable (avg 245ms, target <500ms)"
    recommendation: "Health improving; 3 escalations normal"
  
  healing:
    pass_rate: 1.0 (47/47)
    issues_found: 4
    fixes_applied: 4
    fix_success_rate: 1.0 (100%)
    recommendation: "Healing agent working perfectly"

threshold_analysis:
  current_thresholds:
    health_score_min: 85
    coverage_min: 80
    error_rate_max: 1.0
    p99_latency_max: 500
    vulnerabilities_max: 0
  
  recommendation:
    action: "TIGHTEN (incrementally)"
    reasoning: "Pass rate 96% suggests thresholds well-calibrated; can raise bar slightly"
    suggested_changes:
      - "health_score: 85 → 87 (+2 point improvement)"
      - "coverage: 80% → 82% (+2 point improvement)"
      - "error_rate: 1.0% → 0.8% (tighten by 20%)"
    expected_impact: "May cause 2-3 additional escalations/week, but higher quality"
    implementation: "Gradual: raise 1 point/week, monitor impact"

anomaly_detection:
  anomalies_found: 1
  - type: "escalation_frequency"
    severity: "LOW"
    observation: "Escalations 33% above baseline (2 vs 1.5 expected)"
    context: "Both from Metrics agent (health < 85); normal variation"
    action: "Continue monitoring; likely normal variance"

alerts_issued: 0 (clean week)

cost_analysis:
  qg_tokens_used_week: 8200
  qg_tokens_per_run: 174
  cost_per_run: "$0.026"
  trend: "stable"

feedback_to_model_engineer:
  data_sent: "47 QG run results with quality metrics"
  purpose: "Optimize agent routing; validate QG threshold accuracy"
  request: "Identify any false positives (escalated but should PASS)"

next_week_plan:
  action_items:
    - "Implement tighter thresholds (incremental)"
    - "Monitor escalation rate (target: return to <2%)"
    - "Celebrate coverage improvement with team"
  monitoring_focus:
    - "Watch for threshold-tightening side effects"
    - "Continue security clean streak (0 vulns)"
    - "Track health score trend (currently improving)"

recommendation_confidence: 0.94
---
```

## Data Schema: Daily QG Log

```yaml
# File: ~/.agents/agentic-engineers/data/qg/daily-qg-log.yaml
daily_log:
  - date: 2026-05-07
    runs:
      - time: "09:15:00Z"
        commit: "abc123"
        overall_status: PASS
        security: PASS
        testing: PASS
        metrics: PASS
        healing: PASS
        max_severity: NONE
      
      - time: "10:42:00Z"
        commit: "def456"
        overall_status: PASS
        security: PASS
        testing: ESCALATE (coverage 78%, below 80%)
        metrics: PASS
        healing: PASS
        max_severity: MEDIUM
```

## Integration Points

**Input:**
- Quality Gate Orchestrator (4 sub-agent HANDBACKs)
- Model Engineer (routing accuracy feedback)
- Daily QG log (historical comparison)

**Output:**
- Weekly QG trend report (YAML)
- Threshold recommendations (JSON)
- Alerts (if anomalies detected)
- Dashboard data (for visualization)

**Feedback Loops:**
- QG results → Aggregator → Trend analysis → Threshold recommendations → Next QG uses updated thresholds

## Success Criteria

- ✅ Accurate aggregation (all 4 agents' results captured)
- ✅ Trend detection (pass rate, escalation rate, quality trends)
- ✅ Anomaly alerts (escalations spike → alert)
- ✅ Threshold recommendations (data-driven adjustments)
- ✅ Weekly reporting (complete, actionable summaries)
- ✅ False positive detection (didn't escalate but should have?)
- ✅ Cost stability (QG tokens consistent)

## Phase 6.1 Integration

Part of three-pronged feedback loop:
1. **Model Engineer** — Model optimization
2. **Quality Gate Aggregator** (this file) — Trend analysis & auto-tuning
3. **Config Enforcement Verification** — Auto-fix validation
