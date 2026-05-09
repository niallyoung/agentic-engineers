---
name: Phase 6 Integration Guide
description: Wiring diagram for closed-loop feedback with 3 feedback handlers
type: guide
phase: 6
status: READY_FOR_IMPLEMENTATION
---

# Phase 6: Closed-Loop Feedback Integration

**Timeline**: 2026-06-02 → 2026-06-16 (2 weeks)

**Goal**: Every agent result feeds back to parent/coordinator for continuous learning and optimization.

---

## Architecture: 3 Feedback Loops

```
Quality Gate Orchestrator (Sonnet)
│
├─ DELEGATES to 4 sub-agents (parallel)
│  ├─ Security Agent (Opus)
│  ├─ Testing Agent (Haiku)
│  ├─ Metrics Agent (Haiku)
│  └─ Healing Agent (Sonnet)
│
├─ [LOOP 1] RECEIVES HANDBACK from all 4 agents
│  └─ Quality Gate Feedback Handler (in this session)
│     ├─ Polls artifacts/ for HANDBACK blocks (5-min timeout)
│     ├─ Aggregates results
│     ├─ Applies decision logic (PROCEED/ESCALATE)
│     └─ Writes consolidated HANDBACK
│
├─ [LOOP 2] (ASYNC) DELEGATES to Model Engineer
│  └─ Model Engineer Feedback Handler (async)
│     ├─ Analyzes token efficiency per agent
│     ├─ Looks up historical success rates
│     ├─ Recommends optimal model for next run
│     ├─ Updates confidence scores
│     └─ Stores recommendations in artifacts/feedback/
│        → Next quality gate uses recommendations (confidence > 0.7)
│
└─ [LOOP 3] Config Enforcement Feedback Loop (if applicable)
   └─ Config Enforcement Feedback Handler
      ├─ After fix applied: Re-run Config Audit
      ├─ Compare compliance before/after
      ├─ Update fix confidence based on success
      ├─ Store in artifacts/feedback/config-fixes.jsonl
      └─ Future runs use learned confidence

Git Hook
│
├─ 1. Write DELEGATE → artifacts/2026-MM-DD/
│
├─ 2. Trigger make quality-gate
│    (invokes orchestrator in Claude Code)
│
├─ 3. Poll artifacts/ for HANDBACK (5-min timeout)
│    [Quality Gate Feedback Handler runs here]
│
├─ 4. Read final_decision from HANDBACK
│    ├─ PROCEED → allow commit
│    └─ ESCALATE → reject commit
│
└─ 5. (ASYNC) Model Engineer recommendations
     written to artifacts/feedback/
     (read by orchestrator for next commit)
```

---

## Feedback Loop Details

### Loop 1: Quality Gate Feedback Handler (Synchronous)

**Timing**: Runs synchronously in main quality gate flow
**Duration**: <1 second (just aggregation)
**Input**: 4 HANDBACK blocks from sub-agents
**Output**: 1 consolidated HANDBACK (final_decision: PROCEED/ESCALATE)

```
Git Hook writes DELEGATE
         ↓
[Parallel] 4 sub-agents run (3-5 min)
    Security (Opus) → HANDBACK
    Testing (Haiku) → HANDBACK
    Metrics (Haiku) → HANDBACK
    Healing (Sonnet) → HANDBACK
         ↓
Quality Gate Feedback Handler (this session)
  - Polls artifacts/ for all 4 HANDBACK blocks
  - Timeout: 5 min (escalate if missing)
  - Aggregates into audit_trail
  - Decision logic: IF security HIGH → ESCALATE, ELIF testing fails → ESCALATE, ELIF health_score < 70 → ESCALATE, ELSE → PROCEED
         ↓
Consolidated HANDBACK written to artifacts/
         ↓
Git Hook reads final_decision
  → PROCEED: commit allowed
  → ESCALATE: commit rejected
```

**Implementation File**: `orchestration/handlers/quality-gate-feedback-handler.md`

---

### Loop 2: Model Engineer Feedback Handler (Asynchronous)

**Timing**: Runs asynchronously, after main quality gate completes
**Duration**: 1-2 seconds (analysis only)
**Input**: Orchestrator HANDBACK + sub-agent token usage
**Output**: Recommendations stored in artifacts/feedback/model-recommendations.jsonl

```
Orchestrator writes final HANDBACK
         ↓
[ASYNC] Model Engineer Feedback Handler (separate agent)
  - Reads quality gate result
  - Extracts token_observed vs token_estimated per agent
  - Calculates efficiency ratio
  - Looks up historical data (model-recommendations.jsonl)
  - Calculates success_rate_by_model
  - Determines recommendation + confidence
  - Stores: artifacts/feedback/FEEDBACK-{timestamp}-model-engineer.yaml
           artifacts/feedback/model-recommendations.jsonl (append)
         ↓
Next similar commit:
  - Orchestrator checks artifacts/feedback/
  - IF prior recommendation exists AND confidence > 0.7:
    → Use recommended model for next quality gate
  - After execution:
    → Model Engineer updates recommendation
    → confidence += 0.1 if PASS, -= 0.2 if FAIL
         ↓
[Continuous Loop] After 20 runs, model selection converges to optimal
```

**Implementation File**: `orchestration/handlers/model-engineer-feedback-handler.md`

---

### Loop 3: Config Enforcement Feedback Loop (If Config Work Needed)

**Timing**: Async, triggered after Config Enforcement Agent applies fixes
**Duration**: 1-2 minutes (includes re-audit)
**Input**: Config Enforcement HANDBACK (fixes_applied)
**Output**: Compliance improvement tracked, fix confidence updated

```
Config Audit detects deviations
  e.g., missing DATABASE_URL
         ↓
Config Enforcement Agent applies fix (if confidence >= 0.8)
  e.g., "add DATABASE_URL to .env" (confidence 0.95)
         ↓
Config Enforcement Feedback Handler (this session)
  - Re-runs Config Audit
  - Compares compliance_before vs compliance_after
  - Evaluates: Fix successful? (compliance improved)
  - Updates confidence:
    IF successful: confidence += 0.1
    IF failed: confidence -= 0.2
  - Stores outcome in artifacts/feedback/config-fixes.jsonl
         ↓
Future Config Enforcement runs:
  - Check config-fixes.jsonl for fix confidence
  - IF confidence >= 0.95: apply immediately (no escalation)
  - IF confidence 0.7-0.95: apply + verify
  - IF confidence < 0.7: escalate for human review
         ↓
[Continuous Loop] Proven fixes applied faster, risky fixes escalated
```

**Implementation File**: `orchestration/handlers/config-enforcement-feedback-handler.md`

---

## Data Flow: Artifacts Directory Structure

```
artifacts/
│
├─ 2026-MM-DD/
│  │
│  ├─ DELEGATE-{timestamp}-commit-{service}.yaml
│  │  (input from git hook)
│  │
│  ├─ DELEGATE-{timestamp}-commit-{service}-security.yaml
│  ├─ DELEGATE-{timestamp}-commit-{service}-testing.yaml
│  ├─ DELEGATE-{timestamp}-commit-{service}-metrics.yaml
│  ├─ DELEGATE-{timestamp}-commit-{service}-healing.yaml
│  │  (sub-delegations from orchestrator)
│  │
│  ├─ HANDBACK-{timestamp}-agent-security-{task_id}.yaml
│  ├─ HANDBACK-{timestamp}-agent-testing-{task_id}.yaml
│  ├─ HANDBACK-{timestamp}-agent-metrics-{task_id}.yaml
│  ├─ HANDBACK-{timestamp}-agent-healing-{task_id}.yaml
│  │  (sub-agent results)
│  │
│  ├─ HANDBACK-{timestamp}-orchestrator-{task_id}.yaml
│  │  (aggregated decision from Quality Gate Handler)
│  │
│  ├─ SPAN-{timestamp}-quality-gate-root.yaml
│  ├─ SPAN-{timestamp}-agent-security.yaml
│  ├─ SPAN-{timestamp}-agent-testing.yaml
│  ├─ SPAN-{timestamp}-agent-metrics.yaml
│  ├─ SPAN-{timestamp}-agent-healing.yaml
│  └─ SPAN-{timestamp}-decision-aggregation.yaml
│     (OpenTelemetry spans)
│
└─ feedback/
   │
   ├─ model-recommendations.jsonl
   │  (append-only log of all model recommendations)
   │  Example lines:
   │  {"timestamp": "2026-05-26T09:04:35Z", "agent": "testing", "current_model": "haiku", "recommended_model": "haiku", "confidence": 0.95, "outcome": "PASS"}
   │  {"timestamp": "2026-05-27T10:15:22Z", "agent": "testing", "current_model": "haiku", "recommended_model": "haiku", "confidence": 0.95, "outcome": "PASS"}
   │
   ├─ FEEDBACK-{timestamp}-model-engineer.yaml
   │  (latest model engineer recommendations)
   │
   ├─ config-fixes.jsonl
   │  (append-only log of all config fix outcomes)
   │  Example:
   │  {"timestamp": "2026-05-26T09:05:30Z", "fix": "add DATABASE_URL", "outcome": "SUCCESS", "confidence_before": 0.95, "confidence_after": 1.0}
   │
   └─ FEEDBACK-{timestamp}-config-enforcement-verify.yaml
      (latest config fix verification results)

index.json
  (auto-generated, lists all artifacts with metadata)
```

---

## Feedback Loop Closure: Example Timeline

**Run 1 (2026-05-26, 09:00)**:
```
Quality Gate: Testing Agent (Sonnet) → 5120 tokens, status PASS
Model Engineer recommends: "Haiku sufficient for testing" (confidence: 0.70)
Stores: artifacts/feedback/model-recommendations.jsonl (line 1)
```

**Run 2 (2026-05-27, 10:00)**:
```
Prior recommendation exists (confidence: 0.70 > threshold)
Orchestrator uses: Testing Agent (Haiku) for this run
Testing Agent: Haiku → 1200 tokens, status PASS
Model Engineer re-analyzes: "Haiku proved sufficient" (confidence: 0.80)
Stores: artifacts/feedback/model-recommendations.jsonl (line 2, confidence updated)
```

**Run 3 (2026-05-28, 11:00)**:
```
Prior recommendation (confidence: 0.80)
Orchestrator uses: Testing Agent (Haiku)
Testing Agent: Haiku → 950 tokens, status PASS
Model Engineer: confidence += 0.1 = 0.90
```

**Run 4 (2026-05-29, 09:00)**:
```
Prior recommendation (confidence: 0.90)
Orchestrator uses: Testing Agent (Haiku)
Testing Agent: Haiku → 1100 tokens, status FAIL (flaky test detected)
Model Engineer: confidence -= 0.2 = 0.70
Recommends: "Try Sonnet next time" (confidence: 0.75)
```

**Run 5 (2026-05-30, 10:00)**:
```
Two recommendations now:
  - Haiku (confidence: 0.70)
  - Sonnet (confidence: 0.75)
Orchestrator chooses Sonnet (higher confidence)
Testing Agent: Sonnet → 4800 tokens, status PASS
Model Engineer: Sonnet recommendation += 0.1 = 0.85
```

**After 20 runs** (2026-06-10):
```
Haiku: success_rate 15/20 (75%), confidence stabilized 0.80
Sonnet: success_rate 17/20 (85%), confidence 0.88
Orchestrator conclusion: "Sonnet is more reliable for Testing Agent"
```

---

## Success Criteria: Phase 6 Testing

### Objective 1: Feedback Loops Operational

- ✅ Quality Gate Feedback Handler correctly aggregates 4 HANDBACK blocks
- ✅ Decision logic produces correct PROCEED/ESCALATE decisions
- ✅ Model Engineer Feedback Handler analyzes token efficiency correctly
- ✅ Confidence scores evolve (increase/decrease based on outcomes)
- ✅ Config Enforcement Feedback Handler re-verifies fixes
- ✅ Fix confidence updated and used for future decisions

### Objective 2: Data Integrity

- ✅ Append-only logs (model-recommendations.jsonl, config-fixes.jsonl) work correctly
- ✅ No data loss between runs
- ✅ Historical data queryable (read previous 20 runs)
- ✅ Timestamps accurate

### Objective 3: Observability

- ✅ OpenTelemetry spans capture feedback loop operations
- ✅ Per-agent spans linked to root trace
- ✅ All attributes present (model, tokens, confidence, outcome)
- ✅ Spans stored in artifacts/ correctly

### Objective 4: Continuous Improvement

- ✅ 50+ commits through pipeline
- ✅ Model recommendations trending (e.g., Haiku confidence increasing for Testing)
- ✅ Fix confidence converging (proven fixes > 0.9, risky fixes < 0.7)
- ✅ No false positives (wrong recommendations harming quality)
- ✅ Recommendation accuracy > 80% (when confidence > 0.7, outcome matches)

---

## Next Phase (7): Self-Sustaining Optimization Loops

Once feedback loops are operational, Phase 7 will add:

1. **Pattern Recognition Agent** (Haiku)
   - Analyzes recurring issues across commits
   - Identifies: "This type of commit always fails testing"
   - Proposes: "Add pre-commit type check"

2. **Budget Optimizer Agent** (Haiku)
   - Watches token costs accumulate
   - If daily cost exceeds budget: trigger model downgrades
   - If quality suffers: trigger model upgrades

3. **Quality Analyst Agent** (Sonnet)
   - Reviews anomalies detected by feedback loops
   - Proposes improvements to detection logic
   - Continuously refines decision thresholds

These Phase 7 agents will feed into the feedback loops, creating a self-sustaining, self-optimizing system.

---

## Implementation Checklist: Phase 6

- [ ] Quality Gate Feedback Handler
  - [ ] Polls artifacts/ for HANDBACK blocks
  - [ ] Implements aggregation logic
  - [ ] Writes consolidated HANDBACK
  - [ ] Tested on 10+ commits
  - [ ] False positive rate < 5%

- [ ] Model Engineer Feedback Handler
  - [ ] Extracts token usage from HANDBACK
  - [ ] Calculates efficiency per agent
  - [ ] Looks up historical data
  - [ ] Stores recommendations
  - [ ] Tested on 20+ runs
  - [ ] Recommendations applied > 80% accurately

- [ ] Config Enforcement Feedback Handler
  - [ ] Re-runs Config Audit after fix
  - [ ] Compares compliance scores
  - [ ] Updates fix confidence
  - [ ] Stores outcomes
  - [ ] Tested on 10+ config fixes
  - [ ] Proven fixes applied > 90% of time

- [ ] OpenTelemetry Integration
  - [ ] All spans created with correct attributes
  - [ ] Span hierarchy correct
  - [ ] Spans stored in artifacts/
  - [ ] CloudWatch Logs integration ready (for Phase 8)

- [ ] Documentation
  - [ ] Phase 6 complete
  - [ ] Feedback loops explained
  - [ ] Success criteria validated

---

## Bedrock Readiness (Phase 8+)

Phase 6 structures all feedback data for cloud migration:

1. **Append-only logs** (JSONL format)
   - Ready to ship to S3 + CloudWatch Logs
   - Immutable audit trail
   - Queryable by task_type, agent, timestamp

2. **OpenTelemetry spans**
   - Semantic conventions aligned with CloudWatch standards
   - Can be directly exported to CloudWatch Logs or Honeycomb
   - Trace context propagation ready

3. **Decision history** (model-recommendations.jsonl, config-fixes.jsonl)
   - Perfect for ML training (feature engineering)
   - Can feed into Bedrock LLM for learning-based routing

Phase 8 will not change the local architecture—only add cloud export, storage, and querying capabilities.
