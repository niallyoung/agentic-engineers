---
name: Agentic Engineers Master TODO
description: Comprehensive roadmap for agent feedback loops, observability, and Bedrock migration
created: 2026-04-28
status: IN_PROGRESS
---

# Agentic Engineers: Master TODO & Roadmap

## Executive Summary

**Vision**: Fully closed-loop, self-sustaining agent orchestration with:
- Explicit DELEGATE/HANDBACK cycles between all agents
- OpenTelemetry observability at every hop
- Local execution for cost efficiency + experimentation
- Bedrock migration pathway (future infrastructure)
- Continuous optimization via feedback loops

**Current State**: Foundation 100% (Week 4 validation complete). Ready for feedback loop integration.

**Timeline**: Phase 5.10 (1 week) → Phases 6-7 (2 weeks) → Bedrock planning (ongoing).

---

## Phase 5.10: Quality Orchestrator Activation (1 week, 2026-05-26 → 2026-06-02)

### Objective 1: Activate Quality Gate Orchestrator Agent Locally

**Status**: ✅ COMPLETE - All agent implementations done, ready for testing

**Completed Work**:
- ✅ Created `agentic-engineers/orchestration/agents/quality-gate-orchestrator-agent.md`
  - Full pseudo-code implementation of Orchestrator logic
  - Input: DELEGATE blocks from git hooks
  - Process: Parallel delegation to 4 sub-agents
  - Output: HANDBACK blocks (final_decision: PROCEED/ESCALATE)
  - OpenTelemetry instrumentation for all operations

- ✅ Implemented 5 agents:
  - Quality Gate Orchestrator (Sonnet) - master coordinator
  - Security Agent (Opus) - credential/permission scanning
  - Testing Agent (Sonnet) - unit/E2E test execution
  - Metrics Agent (Haiku) - health scoring
  - Healing Agent (Sonnet) - auto-fixes
  - Model Engineer Agent (Sonnet) - token analysis + feedback loop

- ✅ Wired git hooks to generate DELEGATE blocks
  - File: `{service-name}/githooks/pre-commit` (updated with DELEGATE generation)
  - DELEGATE blocks written to artifacts/2026-MM-DD/ on every commit
  - Contains: repo_path, service_name, commit_sha, budget_context
  - Tested: Multiple commits generate valid DELEGATE blocks

- ✅ Test end-to-end workflow
  - Commits trigger pre-commit hook
  - Hook writes DELEGATE block
  - Hook calls make quality-gate
  - DELEGATE blocks ready for agent processing

**Deliverables**:
- ✅ 5 agent specs (quality-gate-orchestrator, security, testing, metrics, healing, model-engineer)
- ✅ Git hook integration (DELEGATE block generation)
- ✅ DELEGATE block format validated
- ✅ Ready for agent testing phase

---

### Objective 2: Enable Audit Trails (Local artifacts/ directory)

**Status**: artifacts/ directory + README.md exist. Infrastructure ready.

**Work**:
- [ ] Wire all agent invocations to write spans to artifacts/
  - Format: `artifacts/2026-MM-DD/SPAN-{timestamp}-{agent}-{task_id}.yaml`
  - Contents: OpenTelemetry schema (trace_id, span_id, parent_span_id, start_time, end_time, status, attributes)
  - Includes: Tokens used, model used, latency, error codes (if any)

- [ ] Create `agentic-engineers/orchestration/telemetry/otel-schema.md`
  - Define standard span format for all agents
  - Map to OpenTelemetry semantic conventions
  - Support future Bedrock migration (spans → CloudWatch Logs)

- [ ] Add `artifacts/index.json` generation
  - Auto-generated file (no git, regenerated on each session)
  - Index all DELEGATE/HANDBACK/SPAN artifacts by task_id, timestamp, agent
  - Enables: Quick queries ("all decisions by Security Agent", "all escalations", etc.)

**Deliverables**:
- Complete OpenTelemetry telemetry schema
- Automated span capture in artifacts/
- Queryable index.json for artifact analysis

---

## Phase 6: Agent Feedback Loops & Observability (2 weeks, 2026-06-02 → 2026-06-16)

### Objective 1: Closed Feedback Loops (Agents → Orchestrator → Decision)

**Core Principle**: Every agent result feeds back to a parent/coordinator agent for aggregation and decision.

#### 1.1 Quality Gate Orchestrator Feedback Cycle

```
Quality Gate Orchestrator (Sonnet)
  ├─ DELEGATE to Security Agent (Opus)
  │  └─ HANDBACK: {status, findings, severity, confidence}
  │     → Orchestrator ingests immediately
  │
  ├─ DELEGATE to Testing Agent (Sonnet)
  │  └─ HANDBACK: {unit_tests, e2e_tests, coverage, failures}
  │     → Orchestrator ingests immediately
  │
  ├─ DELEGATE to Metrics Agent (Haiku)
  │  └─ HANDBACK: {health_score, latency, throughput, anomalies}
  │     → Orchestrator ingests immediately
  │
  └─ DELEGATE to Healing Agent (Sonnet)
     └─ HANDBACK: {auto_fixes_applied, escalations, warnings}
        → Orchestrator ingests immediately

  Aggregation Logic:
  - If ANY sub-agent severity >= HIGH: escalate to human
  - If ALL sub-agents status = PASS + health_score >= 85: PROCEED
  - Else: ESCALATE with details
  
  Final HANDBACK to git hook:
  - final_decision: PROCEED | ESCALATE
  - audit_trail: [all sub-agent results with timestamps]
  - recommendation: human-readable summary
```

**Work**:
- [ ] Design Quality Gate Orchestrator feedback handler
  - Input: HANDBACK blocks from 4 sub-agents (async, await all before aggregating)
  - Logic: Decision tree (security > testing > metrics > healing priority)
  - Output: Single consolidated HANDBACK
  - Instrumentation: Log each sub-agent result with OpenTelemetry span

- [ ] Implement sub-agent HANDBACK capture
  - Each sub-agent writes HANDBACK to artifacts/
  - Orchestrator polls artifacts/ for HANDBACK matching task_id
  - Timeout: 5 min per sub-agent (escalate if exceeded)

#### 1.2 Model Engineer Feedback Loop

```
Quality Gate Orchestrator
  ├─ Delegates work
  ├─ Receives HANDBACK
  └─ (asynchronously)
     → DELEGATE to Model Engineer
        - Analyze: token_usage, latency, quality_score
        - Recommend: model_tier + effort for next similar task
        - Confidence: 0.0-1.0 (higher = more confident)
        └─ HANDBACK: {recommendation, confidence, reasoning}
           → Stored in artifacts/
           → Orchestrator applies to future routing
```

**Work**:
- [ ] Create Model Engineer feedback agent
  - Input: Quality Gate HANDBACK + observed tokens + latency
  - Analysis: Was Sonnet overkill? Should we try Haiku next time?
  - Output: {recommended_model, effort, confidence, reasoning}
  - Store in: `artifacts/2026-MM-DD/FEEDBACK-{timestamp}-model-engineer.yaml`

- [ ] Wire Model Engineer recommendations back to Orchestrator routing
  - Maintain decision history: [task_type → {recommended_model, confidence, actual_result}]
  - Apply: If confidence > 0.7, use recommendation for next similar task

#### 1.3 Config Enforcement Feedback Loop

```
Config Audit Agent
  └─ HANDBACK: {deviations[], compliance_score, severity}
     → DELEGATE to Config Enforcement Agent
        - Apply high-confidence fixes (≥0.8)
        - Escalate low-confidence fixes (<0.8)
        └─ HANDBACK: {fixes_applied, escalations, new_compliance_score}
           → Re-DELEGATE to Config Audit (verify)
              └─ HANDBACK: {compliance_improved: bool}
                 → Decision: PROCEED if improved, ESCALATE if not
```

**Work**:
- [ ] Create Config Enforcement feedback handler
  - After applying fix: Re-run Config Audit to verify improvement
  - If compliance_score increases: confidence += 0.1 (trust this fix)
  - If compliance_score decreases: confidence -= 0.2 (avoid this fix)
  - Store outcomes in `artifacts/` for future decision-making

---

### Objective 2: Observability & Metrics Collection

#### 2.1 OpenTelemetry Integration

**Spans to capture**:
```yaml
Span Hierarchy:
├─ trace_id: unique per commit
├─ root_span: "quality-gate-commit" (Quality Gate Orchestrator)
│  ├─ child_span: "agent-security" (Security Agent)
│  │  ├─ attribute: model = "claude-opus-4-7"
│  │  ├─ attribute: tokens_used = 2845
│  │  ├─ attribute: duration_ms = 3400
│  │  ├─ attribute: status = PASS
│  │  └─ event: "credential_scan_completed"
│  │
│  ├─ child_span: "agent-testing" (Testing Agent)
│  │  ├─ attribute: model = "claude-sonnet-4-6"
│  │  ├─ attribute: tokens_used = 5120
│  │  ├─ attribute: duration_ms = 4200
│  │  ├─ attribute: coverage = 0.873
│  │  └─ event: "test_summary_calculated"
│  │
│  ├─ child_span: "agent-metrics" (Metrics Agent)
│  ├─ child_span: "agent-healing" (Healing Agent)
│  │
│  ├─ child_span: "decision-aggregation" (Orchestrator)
│  │ ├─ attribute: final_decision = "PROCEED"
│  │ ├─ attribute: escalations_count = 0
│  │ └─ attribute: total_duration_ms = 15800
│  │
│  └─ child_span: "model-engineer-feedback" (Model Engineer)
│     ├─ attribute: recommended_model = "sonnet"
│     ├─ attribute: confidence = 0.82
│     └─ attribute: reasoning = "tokens_used was high, Sonnet could handle"
```

**Work**:
- [ ] Create `agentic-engineers/orchestration/telemetry/otel-exporter.md`
  - Define span capture mechanism (write to artifacts/SPAN-*.yaml)
  - Map all agent activities to OpenTelemetry semantic conventions
  - Enable future migration: artifacts/ → CloudWatch → Bedrock metrics

- [ ] Implement span writing in all agent HANDBACK logic
  - After each agent completes: write span with all attributes
  - Include: model, tokens_used, duration, status, key findings
  - Parent: reference orchestrator trace_id

#### 2.2 Metrics Dashboard (Local)

**Work**:
- [ ] Create `agentic-engineers/orchestration/metrics/dashboard.md`
  - Query artifacts/index.json
  - Calculations:
    - Avg tokens per agent per task
    - Model utilization (% Haiku vs Sonnet vs Opus)
    - Decision distribution (% PROCEED vs ESCALATE)
    - Escalation reasons (categories)
    - Agent latencies (p50, p95, p99)
    - Token velocity (tokens/hour trend)

- [ ] Create `agentic-engineers/orchestration/metrics/query-helpers.sh`
  - Helper functions: `query_by_agent()`, `query_by_model()`, `query_escalations()`, etc.
  - Usage: `source query-helpers.sh && query_by_agent Security | jq ...`

---

### Objective 3: Agent Skill Refinement

**All existing agent skills must be updated** to include HANDBACK feedback loops.

#### 3.1 Quality Gate Orchestrator (update)
- [ ] Add feedback loop handler (aggregates sub-agent HANDBACK blocks)
- [ ] Add Model Engineer delegation logic (post-decision)
- [ ] Update HANDBACK format to include audit_trail with all sub-agent results

#### 3.2 Security Agent (update)
- [ ] Ensure HANDBACK includes: {status, severity, findings_count, confidence}
- [ ] Add context: what types of issues found (credentials, permissions, etc.)
- [ ] Enable: Orchestrator to prioritize escalation if severity > threshold

#### 3.3 Testing Agent (update)
- [ ] HANDBACK format: {status, unit_tests, e2e_tests, coverage, flaky_tests, failures}
- [ ] Add: Recommendation if coverage < 80% (escalate or attempt healing)

#### 3.4 Metrics Agent (update)
- [ ] HANDBACK format: {health_score, latency_p50, throughput, anomalies, trend}
- [ ] Add: Anomaly detection (if health_score dropped since last check)

#### 3.5 Healing Agent (update)
- [ ] HANDBACK format: {auto_fixes, escalations, confidence_by_fix, warnings}
- [ ] Add: Confidence score for each attempted fix (for Model Engineer feedback)

#### 3.6 Model Engineer (new/update)
- [ ] DELEGATE input: {previous_decisions, token_usage, latency, quality_score}
- [ ] HANDBACK output: {recommended_model, effort, confidence, reasoning}
- [ ] Store: All recommendations in `artifacts/feedback/model-recommendations.jsonl`

#### 3.7 Config Audit Agent (update)
- [ ] HANDBACK format: {deviations[], compliance_score, trend, escalations}
- [ ] Add: Reference to previous compliance_score (track improvement)

#### 3.8 Config Enforcement Agent (update)
- [ ] HANDBACK format: {fixes_applied, escalations, new_compliance_score, warnings}
- [ ] Add: Confidence for each fix attempt
- [ ] Add: Auto re-audit trigger (verify fix worked)

---

## Phase 7: Self-Sustaining Optimization Loop (2 weeks, 2026-06-16 → 2026-06-30)

### Objective 1: Pattern Recognition & Continuous Improvement

**Work**:
- [ ] Create Pattern Recognition Agent
  - Input: Last 50 commits (artifacts/ DELEGATE/HANDBACK blocks)
  - Analysis:
    - What issues are recurring? (e.g., "linting always fails on feature/*")
    - What models are over-provisioned? (e.g., "Opus for trivial issues")
    - What escalations are preventable?
  - Output: {pattern, frequency, recommendation, confidence}
  - Store: `artifacts/patterns/recurring-issues.jsonl`

- [ ] Create Continuous Improvement Agent
  - Input: Pattern Recognition output + Model Engineer recommendations
  - Decision: Which improvements to implement?
  - Actions:
    - Suggest new linter rules (if pattern detected)
    - Recommend model downgrades (Opus → Sonnet)
    - Propose new healing rules
  - Output: HANDBACK with ranked suggestions

### Objective 2: Token Budget Management (Feedback Loop)

**Work**:
- [ ] Update Token Advisor agent to track:
  - Session token usage over time
  - Model-specific costs (Haiku 50K/day, Sonnet 100K/day, Opus 200K/day budgets)
  - Velocity: tokens/hour, tokens/task
  - Trend: increasing/stable/decreasing
  - Recommendation: escalate if >80%, warn if >60%

- [ ] Create Budget Optimizer Agent
  - Input: Token Advisor metrics + Model Engineer recommendations
  - Decision: Should we downgrade expensive tasks to cheaper models?
  - Outputs:
    - `optimized_routing`: {task_type → [models_to_try] sorted by cost}
    - `confidence`: for each recommendation
  - Store: `artifacts/budget/routing-optimizations.jsonl`

- [ ] Wire Budget Optimizer output back to Orchestrator
  - Orchestrator uses optimized_routing for next similar task
  - Tracks: actual vs recommended model performance
  - Feeds back to Model Engineer for refinement

### Objective 3: Quality & Reliability Tracking

**Work**:
- [ ] Create Quality Analyst Agent
  - Input: All HANDBACK blocks (last 100 decisions)
  - Metrics:
    - Decision accuracy: % of PROCEED decisions that were correct (measure: did no issues appear in prod)
    - Escalation accuracy: % of ESCALATE decisions that were necessary
    - False positive rate: % of ESCALATE decisions that were unnecessary
  - Output: {quality_score, confidence_intervals, recommendations}

- [ ] Create Reliability Dashboard
  - Track: Mean time between escalations (MTBE)
  - Track: Mean time to resolution (MTTR) for escalated issues
  - Track: Healing success rate (% of escalations resolved by Healing Agent)

---

## Bedrock Migration Plan (Documentation Only, Phase 8+)

### Objective: Design pathway for scaling agentic-engineers to AWS Bedrock

**Architecture**:
```
Current (Local):
Git Hook → make quality-gate → Orchestrator Agent (Haiku) → 4 sub-agents → artifacts/

Future (Bedrock):
Git Hook → CloudFormation Stack (invoke Bedrock Agent Pool)
         → Bedrock Agent: Quality Gate Orchestrator
            ├─ Bedrock Agent: Security Agent
            ├─ Bedrock Agent: Testing Agent
            ├─ Bedrock Agent: Metrics Agent
            └─ Bedrock Agent: Healing Agent
         → CloudWatch Logs (telemetry)
         → S3 (artifacts storage)
```

**Work** (documentation only):
- [ ] Create `agentic-engineers/bedrock/MIGRATION-PLAN.md`
  - Current local agents → Bedrock Agent APIs
  - Telemetry mapping: artifacts/ spans → CloudWatch Logs
  - Context management: How to pass service context through Bedrock agents
  - Cost comparison: Local execution vs Bedrock vs CloudWatch

- [ ] Create `agentic-engineers/bedrock/CICD-TASK-DESIGN.md`
  - Use case: CICD container can submit tasks to Bedrock Agent pool
  - Example: GitHub Actions workflow → invoke Bedrock agent → get HANDBACK
  - Managed context: How agents maintain context across invocations
  - State: Where to store decision history (DynamoDB?)

- [ ] Create `agentic-engineers/bedrock/COST-ANALYSIS.md`
  - Estimate: Bedrock agent costs (token pricing, invocation pricing)
  - Compare: Local execution cost (current) vs Bedrock cost (projected)
  - Break-even: At what scale does Bedrock become cheaper?

- [ ] Create `agentic-engineers/bedrock/OPENTELEMETRY-MAPPING.md`
  - Current: artifacts/ SPAN-*.yaml files
  - Future: CloudWatch Logs with OpenTelemetry format
  - Semantic conventions: Map to AWS/Bedrock conventions
  - Observability: How to query Bedrock agent metrics

---

## Artifacts/ as Central Scaling Mechanism (TBD: Phase 9+)

**Note**: artifacts/ directory is designed to scale from local file-based storage to distributed backend.

Current (Phase 5.10-7):
- artifacts/ = YAML files on disk
- Agent communication via file I/O
- Observability via local queries

Future (Phase 9+):
- artifacts/ abstraction layer
- Backend options: DynamoDB, Redis, PostgreSQL, or Bedrock-managed state
- Agent delegation/handoff via artifacts/ API (not direct function calls)
- Retrieval: query artifacts/ by trace_id, task_id, agent_type, timestamp
- This enables: distributed agents, cloud scaling, multi-region orchestration

**Design Principle**: artifacts/ is the central nervous system. All agent communication flows through artifacts/, not direct APIs. This keeps orchestration decoupled from infrastructure.

**Documentation**: TBD in Phase 9+ planning. For now, treat artifacts/ as file-based, scalable design will follow.

---

## Summary of Deliverables by Phase

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 5.10 | Quality Gate Orchestrator activation + audit trails | IN PROGRESS |
| 6 | Feedback loops + OpenTelemetry telemetry | TODO |
| 7 | Self-sustaining optimization loop | TODO |
| 8+ | Bedrock migration documentation | TODO (docs only) |
| 9+ | artifacts/ backend abstraction + scaling infrastructure | TBD |

---

## Key Principles (Reinforced)

1. **Closed-Loop Feedback**: Every agent result → parent agent → decision → next iteration
2. **Observability**: Every agent hop instrumented with OpenTelemetry spans
3. **Cost Efficiency**: Haiku for routine, Sonnet for complex, Opus for critical
4. **Local Execution**: All orchestration happens in Claude/Copilot (minimize AWS costs)
5. **Self-Sustaining**: Pattern recognition + Model Engineer feedback continuously improve routing
6. **Bedrock-Ready**: OpenTelemetry spans enable future Bedrock migration without rework

---

## Next: Execution Checklist

- [ ] Save this TODO.md to git
- [ ] Reload agentic-engineers context
- [ ] Begin Phase 5.10 (Quality Gate Orchestrator activation)
- [ ] Begin Phase 6 (feedback loops + observability)
- [ ] Document Bedrock plan (Phase 8+, no implementation yet)
