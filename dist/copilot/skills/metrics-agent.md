---
name: Metrics Agent Implementation
type: agent-implementation
phase: 5.10
---

# Metrics Agent — LIVE IMPLEMENTATION

**Role**: Orchestrator (Haiku)  
**Model**: claude-haiku-4-5  
**Effort**: low

## Agent Logic

```
WHEN Orchestrator writes DELEGATE to artifacts/:

1. ESTIMATE service health:
   repo_path = {workspace-root}/{service}
   
   Check code patterns:
   - Error handling present? +20 points
   - Tests exist and pass? +30 points
   - CI/CD configured? +20 points
   - Logging/monitoring? +15 points
   - Documentation? +15 points
   
   base_score = 100 (healthy until proven otherwise)

2. ASSESS ANOMALIES:
   - Recent commits break builds? -20 points
   - High technical debt? -15 points
   - Deprecated dependencies? -10 points
   - Performance regressions? -25 points

3. CALCULATE LATENCY ESTIMATES:
   From code analysis:
   - Number of external calls: latency += 50ms per call
   - Database queries: latency += 100ms per query
   - Caching present: latency -= 30ms if yes
   - p50, p95, p99 estimated from worst-case analysis

4. DETERMINE STATUS:
   health_score = base_score + assessments
   health_score = max(0, min(100, health_score))
   
   status = "PASS" if health_score >= 85 else "WARNING"
   severity = "PASS" if health_score >= 85 else "MEDIUM"
   confidence = 0.85  # Estimates have moderate confidence

5. WRITE HANDBACK:
   HANDBACK = {
     handoff_type: "HANDBACK",
     task_id: ...,
     status: status,
     health_score: health_score,
     latency_p50_ms: estimate,
     latency_p95_ms: estimate,
     latency_p99_ms: estimate,
     anomalies_detected: count,
     anomalies: [description],
     severity: severity,
     confidence: confidence
   }

6. WRITE SPAN to artifacts/SPAN-{timestamp}-agent-metrics.yaml
```

## HANDBACK Format

```yaml
---
handoff_type: HANDBACK
task_id: 2026-05-26-commit-{service-name}
timestamp: 2026-05-26T09:02:00Z
status: PASS
health_score: 93
latency_p50_ms: 42
latency_p95_ms: 156
latency_p99_ms: 248
anomalies_detected: 0
anomalies: []
severity: PASS
confidence: 0.85
recommendation: "Service health is good"
```
