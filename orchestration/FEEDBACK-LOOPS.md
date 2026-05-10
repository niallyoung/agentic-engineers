---
name: Agent Feedback Loop Architecture
description: Closed-loop DELEGATE/HANDBACK cycles with OpenTelemetry observability
type: architecture
created: 2026-04-28
---

# Agent Feedback Loop Architecture

## Principle: Every HANDBACK feeds back to orchestration, creating continuous improvement

---

## Cost Model: Optimized for Local Execution

Sorted by Model (Haiku → Sonnet → Opus), then by Cost.

| Model | Agent Type | Tokens/Task | Cost | When to Use | Feedback Loop |
|-------|-----------|------------|------|-------------|---------------|
| **Haiku** | Orchestrator | 500-1K | $0.01-0.03 | Routing, state mgmt, scheduling | Tokens → Budget Optimizer |
| **Haiku** | Metrics Agent | 1-3K | $0.03-0.09 | Health scoring, anomaly detect | Anomalies → Quality Analyst |
| **Haiku** | Pattern Recognition | 2-4K | $0.06-0.12 | Find recurring issues | Patterns → Continuous Improvement |
| **Haiku** | Testing Agent | 4-10K | $0.03-0.08 | Unit/E2E tests, coverage | Results → Healing Agent |
| **Haiku** | Model Engineer | 3-7K | $0.02-0.06 | Analyze token usage, recommend models | Recommendations → Orchestrator routing |
| **Sonnet** | Engineer | 2-5K | $0.06-0.15 | Well-scoped implementation | Result → Quality Engineer |
| **Sonnet** | Quality Engineer | 3-8K | $0.09-0.24 | Code review, validation | Assessment → Model Engineer |
| **Sonnet** | Senior Engineer | 5-15K | $0.15-0.45 | Complex coding, planning | Plan → Engineer (downstream) |
| **Sonnet** | Healing Agent | 3-8K | $0.09-0.24 | Auto-fixes, lint corrections | Fixes → Config Audit (re-verify) |
| **Sonnet** | Config Enforcement | 2-6K | $0.06-0.18 | Apply config fixes | Compliance Δ → Pattern Recognition |
| **Sonnet** | Orchestrator (Quality Gate) | 2-4K | $0.06-0.12 | Delegate & aggregate quality gate decisions | Decisions → HANDBACK |
| **Opus** | Security Agent | 6-15K | $0.18-0.45 | Credential scanning, threat modeling | Findings → Orchestrator decision |
| **Opus** | Principal Engineer | 10-25K | $0.30-0.75 | Cross-service architecture | Design → Lead Engineer review |

---

## Core Feedback Loop: Quality Gate Orchestrator

```
┌─────────────────────────────────────────────────────────────────┐
│ Quality Gate Orchestrator (Sonnet, Trace Root)                  │
│                                                                   │
│ INPUT: DELEGATE {repo_path, service_name, commit_sha}          │
│                                                                   │
│ ┌─ SPAN: quality-gate-root                                      │
│ │ ├─ start_time: 2026-05-26T09:00:00Z                          │
│ │ ├─ trace_id: abc123...                                        │
│ │ │                                                              │
│ │ ├─ [Parallel] DELEGATE to Security Agent (Opus)              │
│ │ │ └─ SPAN: agent-security [async, 0-5min]                   │
│ │ │    └─ HANDBACK: {status, severity, findings_count}        │
│ │ │       → Orchestrator receives via artifacts/               │
│ │ │       → Attributes: severity, confidence, token_usage      │
│ │ │                                                              │
│ │ ├─ [Parallel] DELEGATE to Testing Agent (Haiku)             │
│ │ │ └─ SPAN: agent-testing [async, 0-5min]                    │
│ │ │    └─ HANDBACK: {status, coverage, failures, flaky}       │
│ │ │       → Orchestrator receives via artifacts/               │
│ │ │       → Attributes: coverage %, failure count              │
│ │ │                                                              │
│ │ ├─ [Parallel] DELEGATE to Metrics Agent (Haiku)              │
│ │ │ └─ SPAN: agent-metrics [async, 0-5min]                    │
│ │ │    └─ HANDBACK: {health_score, latency, anomalies}        │
│ │ │       → Orchestrator receives via artifacts/               │
│ │ │       → Attributes: health_score, p99_latency              │
│ │ │                                                              │
│ │ └─ [Parallel] DELEGATE to Healing Agent (Sonnet)             │
│ │   └─ SPAN: agent-healing [async, 0-5min]                    │
│ │    └─ HANDBACK: {auto_fixes, escalations, confidence}       │
│ │       → Orchestrator receives via artifacts/                 │
│ │       → Attributes: fixes_count, escalations_count           │
│ │                                                                │
│ ├─ SPAN: decision-aggregation                                   │
│ │ ├─ Orchestrator polls artifacts/ for all HANDBACK blocks    │
│ │ ├─ Timeout: 5min (escalate if not all received)             │
│ │ │                                                              │
│ │ ├─ Decision Logic:                                            │
│ │ │ IF any severity >= HIGH: escalate = true                  │
│ │ │ ELIF all status = PASS AND health_score >= 85: PROCEED   │
│ │ │ ELSE: escalate = true + details                            │
│ │ │                                                              │
│ │ ├─ Attributes:                                                │
│ │ │ ├─ final_decision: PROCEED | ESCALATE                     │
│ │ │ ├─ escalation_reason: string (if escalate=true)           │
│ │ │ ├─ audit_trail: [all sub-agent results]                   │
│ │ │ ├─ sub_agent_count: 4                                      │
│ │ │ └─ total_tokens_used: sum of all sub-agents               │
│ │ │                                                              │
│ │ └─ SPAN: agent-aggregation [sync, <1sec]                    │
│ │    └─ Combines all HANDBACK blocks into single decision      │
│ │                                                                │
│ ├─ [Async] DELEGATE to Model Engineer (Haiku)                 │
│ │ ├─ Input: observed tokens, latency, quality_score           │
│ │ ├─ SPAN: agent-model-engineer [async, 0-5min]              │
│ │ │ └─ Analysis:                                                │
│ │ │    Was model choice correct?                               │
│ │ │    Token usage: too high / just right / too low?           │
│ │ │    Latency: acceptable / slow?                             │
│ │ │                                                              │
│ │ │ └─ HANDBACK: {recommended_model, effort, confidence}      │
│ │ │    Attributes:                                              │
│ │ │    ├─ recommended_model: haiku | sonnet | opus            │
│ │ │    ├─ confidence: 0.0-1.0                                  │
│ │ │    ├─ reasoning: string                                     │
│ │ │    └─ token_analysis: {used, estimate_next}               │
│ │ │                                                              │
│ │ └─ Store in artifacts/feedback/model-recommendations.jsonl   │
│ │                                                                │
│ └─ end_time: 2026-05-26T09:05:00Z                              │
│    total_duration_ms: 300000                                    │
│    status: success                                               │
│                                                                   │
│ OUTPUT: HANDBACK                                                │
│   ├─ final_decision: PROCEED | ESCALATE                        │
│   ├─ audit_trail: [Security, Testing, Metrics, Healing results]│
│   ├─ recommendation: human-readable summary                     │
│   └─ attributes:                                                 │
│       ├─ trace_id: abc123...                                    │
│       ├─ model_recommendation: from Model Engineer             │
│       └─ next_suggested_model: for similar task                │
│                                                                   │
│ FEEDBACK LOOP:                                                  │
│   Model Engineer recommendation stored → used for next similar  │
│   decision → outcome tracked → confidence increases/decreases   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Config Audit → Enforcement → Verification Loop

```
┌─ Config Audit Agent (Quality Engineer)
│  └─ HANDBACK: {deviations[], compliance_score, severity, trend}
│     Attributes: compliance_score_delta, deviation_count
│
├─→ [IF deviations exist]
│   └─ DELEGATE to Config Enforcement Agent (Senior Engineer)
│      ├─ Input: high-confidence deviations (≥0.8)
│      ├─ Apply fixes automatically
│      └─ HANDBACK: {fixes_applied, escalations, new_compliance_score}
│         Attributes: fixes_count, fix_confidence_per_fix
│
├─→ [Re-verify with Config Audit]
│   └─ DELEGATE to Config Audit Agent again
│      └─ HANDBACK: {compliance_improved: bool, new_score}
│         Attributes: score_delta (improvement vs degradation)
│
└─→ [FEEDBACK]
    ├─ If improved: Config Enforcement confidence += 0.1
    ├─ If degraded: Config Enforcement confidence -= 0.2
    └─ Store outcome in artifacts/feedback/config-enforcement.jsonl
```

---

## Model Engineer Continuous Feedback Loop

```
┌─ Orchestrator completes decision
│  ├─ Observed: tokens_used, latency, model_used
│  ├─ Result: final_decision (PROCEED | ESCALATE)
│  │
│  └─ [Async] DELEGATE to Model Engineer (Haiku)
│     ├─ Analyze: Was the model choice optimal?
│     │  ├─ If tokens_used < predicted: maybe Haiku would work?
│     │  ├─ If tokens_used >> predicted: Opus needed?
│     │  ├─ If latency > 5min: time to scale up?
│     │  └─ If decision quality low: need better context?
│     │
│     ├─ Create recommendation: {recommended_model, confidence, reasoning}
│     │
│     └─ FEEDBACK LOOP:
│        ├─ Store in artifacts/feedback/model-recommendations.jsonl
│        ├─ Orchestrator reads & applies to next similar task
│        ├─ Track: {recommended_model, actual_model, outcome}
│        │  ├─ If outcome = PROCEED: recommendation was good (confidence++)
│        │  ├─ If outcome = ESCALATE: recommendation was too aggressive (confidence--)
│        │  └─ Build confidence history per task type
│        │
│        └─ Model Engineer queries this history
│           └─ "For commits on main branch: Sonnet works 95% of time"
│              → recommend Sonnet for next main branch commit (confidence: 0.95)
```

---

## Pattern Recognition → Continuous Improvement Loop

```
┌─ Pattern Recognition Agent (Haiku, runs async every 10 commits)
│  ├─ Input: Last 50 commits (artifacts/ DELEGATE/HANDBACK blocks)
│  ├─ Analysis:
│  │  ├─ What issues recur? (e.g., "pre-commit linting fails 40% on feature/*")
│  │  ├─ What models over-provisioned? (e.g., "Opus used for trivial issues")
│  │  ├─ What escalations preventable? (e.g., "Security escalates 20% on generated code")
│  │  └─ Token trends: are we increasing velocity?
│  │
│  └─ HANDBACK: {pattern, frequency, recommendation, confidence}
│     Store in: artifacts/patterns/{pattern_type}.jsonl
│
├─→ [DELEGATE to Continuous Improvement Agent (Sonnet)]
│   ├─ Input: Pattern Recognition output
│   ├─ Decision: Which improvements to implement?
│   └─ Actions:
│      ├─ "Suggest lint rule" → escalate to Lead Engineer
│      ├─ "Downgrade Opus → Sonnet" → recommend via Model Engineer
│      ├─ "Add healing rule" → propose to Healing Agent
│      └─ "Faster pre-commit check" → escalate to Principal Engineer
│
└─→ [FEEDBACK: Improvements Applied]
    ├─ Track: Did this improvement reduce escalations?
    ├─ Measure: Token usage before/after improvement
    └─ Update: Pattern Recognition confidence
       (pattern detected & fixed = success)
```

---

## OpenTelemetry Span Structure

Every agent invocation creates a span:

```yaml
---
trace_id: "abc123def456ghi"  # Same for all agents in single quality-gate
span_id: "security-agent-001"
parent_span_id: "orchestrator-quality-gate"
span_name: "agent.security.analysis"
start_time: "2026-05-26T09:00:15Z"
end_time: "2026-05-26T09:03:45Z"
duration_ms: 210000
status: "success"  # or "error", "deadline_exceeded"

attributes:
  agent_type: "security"
  model_used: "claude-opus-4-7"
  input_tokens: 1245
  output_tokens: 1600
  total_tokens: 2845
  cost: 0.0854  # (1245*0.003 + 1600*0.015) / 100
  
  # Semantic attributes (OpenTelemetry standard)
  service_name: "{example-service}"
  service_commit_sha: "abc123def..."
  
  # Agent-specific attributes
  findings_count: 0
  severity: "PASS"
  confidence: 0.95
  
  # Decision attributes (for orchestrator)
  decision: "PASS"
  recommended_action: "proceed"

events:
  - timestamp: "2026-05-26T09:00:20Z"
    name: "credential_scan_started"
  - timestamp: "2026-05-26T09:02:15Z"
    name: "credential_scan_completed"
    attributes:
      files_scanned: 45
      credentials_found: 0
  - timestamp: "2026-05-26T09:03:40Z"
    name: "analysis_complete"
    attributes:
      recommendation: "pass_security_check"
```

---

## Feedback Loop Closure Checklist

For each agent HANDBACK, verify:

- [ ] **Status**: Agent returned valid HANDBACK (not error)
- [ ] **Attributes**: All required fields present (model, tokens, status, decision)
- [ ] **Span**: OpenTelemetry span written to artifacts/
- [ ] **Parent Agent**: Parent agent (Orchestrator) received HANDBACK
- [ ] **Aggregation**: Orchestrator included in final decision logic
- [ ] **Feedback**: Outcome fed back to child agent (for confidence tracking)
- [ ] **Metrics**: Tokens, latency, decision recorded in telemetry
- [ ] **Model Engineer**: Recommendation generated and stored
- [ ] **Pattern Recognition**: Artifact indexed for pattern detection
- [ ] **Archive**: artifacts/index.json updated

---

## Future: Bedrock Feedback Loops

When migrating to Bedrock, feedback loops remain unchanged:

```
Local (Current):
  Orchestrator → DELEGATE (YAML artifact)
  Sub-agent reads artifact
  Sub-agent writes HANDBACK (YAML artifact)
  Orchestrator reads HANDBACK

Bedrock (Future):
  Orchestrator → API call (invoke Bedrock Agent)
  Bedrock Agent processes
  Bedrock Agent returns JSON response
  Orchestrator parses response → OpenTelemetry span → CloudWatch Logs
```

**Key**: Spans always go to OpenTelemetry format (artifacts/ → CloudWatch), enabling seamless migration without changing feedback loop logic.

