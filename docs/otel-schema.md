---
name: OpenTelemetry Schema for Agent Spans
description: Standard span format for all agent invocations, mappable to CloudWatch Logs and Bedrock
created: 2026-04-28
type: specification
---

# OpenTelemetry Schema for Agent Spans

## Overview

All agent invocations produce OpenTelemetry spans. This enables:
- Local observability (artifacts/ directory)
- Future CloudWatch integration (Phase 8+)
- Bedrock migration (spans → CloudWatch Logs)
- Cost analysis (token tracking per agent)
- Performance analysis (latency, throughput)

---

## Span Format (YAML)

```yaml
---
# SPAN Structure (OpenTelemetry compliant)
trace_id: "abc123def456ghi789jkl"
  # Unique identifier for the entire quality-gate operation
  # Same trace_id for all spans in a single commit workflow
  # Format: UUID or random hex string

span_id: "security-agent-001"
  # Unique identifier for this specific agent invocation
  # Format: {agent_name}-{sequence}

parent_span_id: "orchestrator-quality-gate"
  # Reference to parent span
  # Null for root spans

span_name: "agent.security.analysis"
  # Naming convention: "agent.{agent_name}.{operation}"
  # Examples:
  #   - "agent.security.analysis"
  #   - "agent.testing.unit_tests"
  #   - "orchestrator.decision.aggregation"

start_time: "2026-04-28T09:00:15Z"
  # ISO 8601 timestamp when agent started processing

end_time: "2026-04-28T09:03:45Z"
  # ISO 8601 timestamp when agent finished

duration_ms: 210000
  # Milliseconds elapsed (for performance trending)

status: "success"
  # One of: success, error, deadline_exceeded
  # Maps to OpenTelemetry Status Code (0=OK, 1=ERROR, 2=DEADLINE_EXCEEDED)

# Attributes (OpenTelemetry semantic conventions)
attributes:
  
  # Agent Identity
  agent_type: "security"
    # One of: orchestrator, security, testing, metrics, healing,
    #         model_engineer, pattern_recognition, etc.
  
  agent_model: "claude-opus-4-7"
    # Model used by this agent
  
  agent_role: "Security Engineer"
    # Role from AGENTS.md (Security Engineer, Quality Engineer, etc.)
  
  # Resource (Service Being Checked)
  service_name: "{service-name}"
    # ERS service being quality-checked
  
  service_commit_sha: "abc123def..."
    # Git commit SHA being checked
  
  # Token Usage
  input_tokens: 1245
    # Tokens sent to model
  
  output_tokens: 1600
    # Tokens received from model
  
  total_tokens: 2845
    # Sum of input + output
  
  cost_usd: 0.0854
    # (input_tokens * input_price + output_tokens * output_price) / 100
    # Updated as pricing changes; tracks actual cost per span
  
  # Quality Signals
  findings_count: 0
    # Number of issues/findings detected
  
  severity: "PASS"
    # One of: PASS, INFO, LOW, MEDIUM, HIGH, CRITICAL
  
  confidence: 0.95
    # Agent confidence in result (0.0-1.0)
  
  # Decision (for decision-making agents)
  decision: "PASS"
    # Agent's decision (PASS, FAIL, ESCALATE, etc.)
  
  recommended_action: "proceed"
    # What the agent recommends (proceed, escalate, investigate, fix, etc.)
  
  # OpenTelemetry Standard Attributes
  otel.status_code: 0
    # 0=Ok, 1=Error, 2=Deadline_Exceeded
  
  otel.status_description: ""
    # Error description (if status != Ok)

# Events (key moments during execution)
events:
  - timestamp: "2026-04-28T09:00:20Z"
    name: "credential_scan_started"
    # Events are structured moments in the span
    # Allows detailed tracing of agent steps
  
  - timestamp: "2026-04-28T09:02:15Z"
    name: "credential_scan_completed"
    attributes:
      files_scanned: 45
      credentials_found: 0
  
  - timestamp: "2026-04-28T09:03:40Z"
    name: "analysis_complete"
    attributes:
      recommendation: "pass_security_check"
```

---

## Agent-Specific Attributes

### Security Agent
```yaml
attributes:
  agent_type: "security"
  agent_model: "claude-opus-4-7"
  
  # Security-specific
  credential_scans: 0
  permission_scans: 0
  vulnerability_scans: 0
  severity: "PASS"  # or HIGH, CRITICAL
  confidence: 0.99
```

### Testing Agent
```yaml
attributes:
  agent_type: "testing"
  agent_model: "claude-sonnet-4-6"
  
  # Testing-specific
  unit_tests: 45
  unit_test_failures: 0
  e2e_tests: 12
  e2e_test_failures: 0
  coverage_percent: 87.3
  flaky_tests: 0
  decision: "PASS"  # or FAIL
  confidence: 0.92
```

### Metrics Agent
```yaml
attributes:
  agent_type: "metrics"
  agent_model: "claude-haiku-4-5"
  
  # Metrics-specific
  health_score: 93
  latency_p50_ms: 42
  latency_p95_ms: 156
  latency_p99_ms: 248
  throughput_rps: 1200
  error_rate: 0.001
  anomalies_detected: 0
  trend: "stable"  # or increasing, decreasing, critical
  decision: "PASS"
  confidence: 0.85
```

### Healing Agent
```yaml
attributes:
  agent_type: "healing"
  agent_model: "claude-sonnet-4-6"
  
  # Healing-specific
  auto_fixes_attempted: 3
  auto_fixes_succeeded: 2
  auto_fixes_failed: 1
  escalations: 1
  confidence_per_fix: [0.95, 0.92, 0.45]
  warnings: ["Fix #1 may need human review"]
  decision: "PASS_WITH_WARNINGS"
  confidence: 0.88
```

### Model Engineer
```yaml
attributes:
  agent_type: "model_engineer"
  agent_model: "claude-sonnet-4-6"
  
  # Model analysis
  previous_model: "claude-sonnet-4-6"
  recommended_model: "claude-haiku-4-5"
  confidence: 0.82
  reasoning: "Token usage was 2K (well below Sonnet threshold); Haiku can handle"
  token_efficiency: 0.71  # actual / estimated
  decision: "RECOMMEND_DOWNGRADE"
```

---

## Span Hierarchy Example: Quality Gate Commit

```
trace_id: abc123...

root_span: "quality-gate-commit"
├─ span_id: quality-gate-root
├─ service: {service-name}
├─ start: 09:00:00
│
├─ [Parallel Spans]
│  ├─ span: "agent.security.analysis"
│  │  ├─ start: 09:00:15
│  │  ├─ end: 09:03:45
│  │  ├─ duration: 210000ms
│  │  ├─ findings: 0
│  │  ├─ severity: PASS
│  │  └─ decision: PASS
│  │
│  ├─ span: "agent.testing.run"
│  │  ├─ start: 09:00:18
│  │  ├─ end: 09:04:20
│  │  ├─ duration: 242000ms
│  │  ├─ unit_tests: 45
│  │  ├─ coverage: 87.3%
│  │  └─ decision: PASS
│  │
│  ├─ span: "agent.metrics.analyze"
│  │  ├─ start: 09:00:22
│  │  ├─ end: 09:02:00
│  │  ├─ duration: 98000ms
│  │  ├─ health_score: 93
│  │  └─ decision: PASS
│  │
│  └─ span: "agent.healing.fix"
│     ├─ start: 09:00:25
│     ├─ end: 09:03:15
│     ├─ duration: 170000ms
│     ├─ fixes_applied: 2
│     └─ decision: PASS
│
├─ span: "orchestrator.decision.aggregation"
│  ├─ start: 09:04:30
│  ├─ end: 09:04:32
│  ├─ duration: 2000ms
│  ├─ sub_agents_reporting: 4
│  ├─ final_decision: PROCEED
│  └─ status: success
│
└─ root_span ends at 09:04:35
   total_duration: 275000ms (4.6 min)
   total_tokens: 12450 (all agents)
   total_cost: $0.3735
```

---

## Storage: artifacts/ Directory

Each span written to separate YAML file:

```
artifacts/2026-04-28/
├─ SPAN-2026-04-28T09:00:00Z-quality-gate-root.yaml
├─ SPAN-2026-04-28T09:00:15Z-agent-security.yaml
├─ SPAN-2026-04-28T09:00:18Z-agent-testing.yaml
├─ SPAN-2026-04-28T09:00:22Z-agent-metrics.yaml
├─ SPAN-2026-04-28T09:00:25Z-agent-healing.yaml
├─ SPAN-2026-04-28T09:04:30Z-decision-aggregation.yaml
├─ DELEGATE-2026-04-28T09:00:00Z-commit-{service-name}.yaml
└─ HANDBACK-2026-04-28T09:00:00Z-commit-{service-name}.yaml
```

---

## Future: CloudWatch Integration (Phase 8+)

When migrating to CloudWatch Logs:

```json
{
  "timestamp": 1719586800000,
  "message": "SPAN: agent.security.analysis",
  "attributes": {
    "trace_id": "abc123def456ghi789jkl",
    "span_id": "security-agent-001",
    "parent_span_id": "orchestrator-quality-gate",
    "service_name": "{service-name}",
    "agent_type": "security",
    "agent_model": "claude-opus-4-7",
    "input_tokens": 1245,
    "output_tokens": 1600,
    "total_tokens": 2845,
    "cost_usd": 0.0854,
    "findings_count": 0,
    "severity": "PASS",
    "confidence": 0.95,
    "duration_ms": 210000,
    "status": "success"
  }
}
```

CloudWatch Insights queries:
```
fields @timestamp, trace_id, agent_type, total_tokens, cost_usd
| stats sum(total_tokens) as total_tokens, sum(cost_usd) as total_cost by agent_type
| sort total_cost desc
```

---

## OpenTelemetry Compliance

This schema maps to OpenTelemetry specification:
- Trace: single quality-gate commit workflow
- Span: single agent invocation
- Attributes: semantic conventions (service.name, model, etc.)
- Events: structured moments within span
- Status: Ok, Error, Deadline_Exceeded
- Storage: file-based (artifacts/) or CloudWatch Logs

Future Bedrock integration will consume these spans → CloudWatch Logs → Bedrock observability.

