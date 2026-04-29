---
name: Agent Implementation Guide
description: Complete guide for implementing all 13 agents following spec and DELEGATE/HANDBACK protocol
phase: 6
status: READY_FOR_IMPLEMENTATION
---

# Agent Implementation Guide

**Purpose**: Template and patterns for implementing all 13 agents in Phase 6.

---

## Agent Implementation Pattern

Every agent follows this pattern:

### 1. Agent Stub (Python-like pseudocode)

```python
class AgentName:
    """Agent implementation for {role} - {description}"""
    
    MODEL = "claude-{model}-{version}"  # from spec
    EFFORT = "{low|medium|high}"         # from spec
    
    def __init__(self, task_id, delegate_block):
        self.task_id = task_id
        self.delegate = delegate_block  # YAML parsed
        self.handback = {
            "handoff_type": "HANDBACK",
            "task_id": task_id,
            "status": None,  # PASS | ESCALATE
            "severity": None,  # PASS | LOW | MEDIUM | HIGH
        }
    
    def execute(self):
        """Main execution method"""
        try:
            # 1. Validate DELEGATE input
            self.validate_input()
            
            # 2. Execute task
            result = self.do_work()
            
            # 3. Generate HANDBACK
            self.handback["status"] = "PASS"
            self.handback["severity"] = "PASS"
            self.handback["deliverables"] = result
            
        except Exception as e:
            self.handback["status"] = "ESCALATE"
            self.handback["severity"] = "MEDIUM"
            self.handback["error"] = str(e)
        
        return self.handback
    
    def validate_input(self):
        """Validate DELEGATE block has required fields"""
        required = ["task_id", "role", "model", "effort", "scope"]
        for field in required:
            if field not in self.delegate:
                raise ValueError(f"Missing required field: {field}")
    
    def do_work(self):
        """Override in subclass - actual work logic"""
        raise NotImplementedError
```

### 2. DELEGATE/HANDBACK Pattern

**Input (DELEGATE block)**:
```yaml
---
handoff_type: DELEGATE
task_id: 2026-MM-DD-unique-identifier
role: {agent_name}
model: {claude-model}
effort: {low|medium|high}
scope: >
  One-sentence scope + what is explicitly out-of-scope.
context:
  - File: path:line-range
  - Error: error message
  - Attempted: what was tried
  - Related: CLAUDE.md sections
success_criteria:
  - Observable outcome 1
  - Observable outcome 2
plan:
  1. Step 1
  2. Step 2
```

**Output (HANDBACK block)**:
```yaml
---
handoff_type: HANDBACK
task_id: {matches_DELEGATE}
timestamp: ISO8601
status: PASS | ESCALATE
severity: PASS | LOW | MEDIUM | HIGH

{agent_specific_fields}

deliverables:
  - outcome 1
  - outcome 2

confidence: 0.0-1.0
token_metrics:
  input_tokens: N
  output_tokens: N
  total_tokens: N
quality_score: 0-100

recommendation: |
  {next_steps_if_escalate}
```

---

## Week 1 Implementation Order

### 1. General Orchestrator (Haiku 4.5)

**File**: `orchestration/agents/general-orchestrator-agent.py` (pseudocode/doc)

**Core Logic**:
```
WHEN receives work request:
  1. Parse request (or read DELEGATE block)
  2. Determine agent to route to:
     - Is it security-scoped? → Security Engineer (Opus 4.7)
     - Is it cross-service arch? → Principal Engineer (Opus 4.7)
     - Is it complex without plan? → Senior Engineer (Sonnet 4.6)
     - Is it code review? → Lead Engineer (Sonnet 4.6)
     - Is it well-planned, low-medium complexity? → Engineer (Haiku 4.5)
     - Otherwise? → Quality Engineer or escalate
  3. Generate DELEGATE block
  4. Delegate work to agent
  5. Wait for HANDBACK (timeout: 5 min)
  6. Apply Model Engineer recommendations for next task
```

**Tests**:
- Route 20 diverse tasks correctly (99%+ accuracy)
- Generate valid DELEGATE YAML
- Handle timeouts gracefully

### 2. Engineer Agent (Haiku 4.5)

**File**: `orchestration/agents/engineer-agent.py`

**Core Logic**:
```
WHEN receives DELEGATE with plan:
  1. Validate: plan exists, is concrete, has success criteria
  2. If invalid: ESCALATE with message "Plan required"
  3. If valid:
     - Execute plan steps sequentially
     - Validate: each step produces observable output
     - Run success criteria tests
     - If all pass: HANDBACK status=PASS
     - If any fail: HANDBACK status=ESCALATE
  4. Calculate quality_score (% success criteria met)
  5. Track token usage
  6. Return HANDBACK with deliverables + confidence
```

**Tests**:
- 5 well-scoped tasks (code edit, doc, test, refactor, feature)
- Reject tasks without plans
- Accept tasks with good plans
- Quality scores reflect actual outcomes

### 3. Senior Engineer Agent (Sonnet 4.6)

**File**: `orchestration/agents/senior-engineer-agent.py`

**Core Logic**:
```
WHEN receives DELEGATE without plan OR complex task:
  1. Diagnose: understand the root issue/requirement
  2. Write plan: detailed steps for Engineer or self
  3. Decide: execute self (complex) or delegate to Engineer
     - If delegate to Engineer: generate sub-DELEGATE block
     - Wait for Engineer HANDBACK
     - Aggregate with own analysis
  4. Return HANDBACK with:
     - status: PASS or ESCALATE
     - plan_quality_score: how detailed/clear is the plan?
     - recommendation: next steps
```

**Tests**:
- 3 complex tasks without plans
- Plans should be detailed, actionable
- Delegation decisions correct

### 4. Lead Engineer Agent (Sonnet 4.6)

**File**: `orchestration/agents/lead-engineer-agent.py`

**Core Logic**:
```
WHEN reviews completed work (from Engineer, Senior Engineer, etc.):
  1. Apply 8-point checklist:
     a) Correctness: does it work?
     b) Completeness: all requirements met?
     c) Clarity: would another engineer understand?
     d) Consistency: follows project conventions?
     e) Examples: well-documented?
     f) Structure: organized well?
     g) Testability: can we verify it works?
     h) Re-implementability: could someone rebuild from this?
  2. For each point: PASS, CONCERN, or REJECT
  3. Generate feedback: specific, actionable
  4. model_assessment: was the agent suitable for this task?
  5. Return HANDBACK status: APPROVE, REQUEST_CHANGES, or REJECT
```

**Tests**:
- Review 5 completed tasks
- Feedback is specific and actionable
- Model assessment helps Model Engineer learn

### 5. Quality Engineer Agent (Sonnet 4.6)

**File**: `orchestration/agents/quality-engineer-agent.py`

**Core Logic**:
```
WHEN receives Engineer HANDBACK:
  1. Validate against success criteria (from original DELEGATE)
  2. Calculate quality_score (0-100):
     - % success criteria met
     - artifact quality (tests, docs, code style)
     - risk assessment (will this break other things?)
  3. Generate model_assessment: was the assigned model right for this?
     - Too powerful (overpowered)?
     - Too weak (underpowered)?
     - Just right?
  4. Confidence: how confident in this assessment? (0-1.0)
  5. Return HANDBACK with quality metrics
```

**Tests**:
- Validate 5 completed tasks
- Quality scores reflect actual quality
- Model assessments are reasonable

### 6. Model Engineer Agent (Haiku 4.5 — downgraded)

**File**: `orchestration/agents/model-engineer-agent.py`

**Core Logic**:
```
WHEN receives Quality Engineer HANDBACK:
  1. Extract metrics: tokens_used, latency, quality_score, model_assessment
  2. Calculate confidence (for next similar task):
     baseline = 0.70
     QE_PASS: +0.15, QE_ESCALATE: -0.20
     sample_size > 20: +0.10, < 3: -0.15
     consistency: +0.05
     confidence = clamp(0.30, 1.00)
  3. Generate recommendations:
     - rank_1: best model (confidence_score)
     - rank_2: exploratory
     - rank_3: fallback
  4. Store in artifacts/feedback/model-recommendations.jsonl
  5. Orchestrator applies rank_1 to next similar task
```

**Tests**:
- Process 10 tasks, verify confidence stabilizes
- Recommendations should be consistent

### 7. Principal Engineer Agent (Opus 4.7)

**File**: `orchestration/agents/principal-engineer-agent.py`

**Core Logic**:
```
WHEN receives cross-service architecture question:
  1. Map affected services
  2. Identify constraints (backwards compat, perf, security)
  3. Research 3-5 options:
     - Option A: pros, cons, risk, cost, timeline
     - Option B: ...
     - Option C: ...
  4. Recommend best option with rationale
  5. Alternative option + fallback
  6. Implementation roadmap (weeks/milestones)
  7. Risk mitigation
  8. Confidence: how sure about this recommendation?
  9. Return HANDBACK with all above
```

**Tests**:
- 3 architecture questions
- Options well-analyzed
- Recommendations sound

---

## Week 2: Quality Gate Sub-Agents

### 8. Security Agent (Opus 4.7)

```
Input: code diff or commit
Output: HANDBACK with severity (PASS, LOW, MEDIUM, HIGH)
Logic:
  - Scan for hardcoded credentials
  - Detect vulnerabilities (SQL injection, XSS, etc.)
  - Check insecure patterns
  - Return findings + severity
```

### 9. Testing Agent (Haiku 4.5)

```
Input: test output (make test)
Output: HANDBACK with test count, pass/fail, coverage
Logic:
  - Parse test output
  - Extract: total tests, passed, failed
  - Extract: coverage %
  - Decision: coverage >= 80% = PASS
```

### 10. Metrics Agent (Haiku 4.5)

```
Input: system metrics (latency, errors, capacity)
Output: HANDBACK with health_score (0-100)
Logic:
  - Score health: latency, error rate, capacity
  - health_score: 0-100 (>= 70 = PASS)
  - Return trend: improving/stable/degrading
```

### 11. Healing Agent (Sonnet 4.6)

```
Input: configuration deviations
Output: HANDBACK with fixes applied + confidence
Logic:
  - Identify issues (env mismatches, CDK params, etc.)
  - Apply auto-fixes
  - Verify fixes work
  - Return confidence (0-1.0) in each fix
  - Integration: Config Enforcement loop verifies post-fix
```

### 12. Spec Engineer Agent (Sonnet 4.6)

```
Input: docs/SPEC.md + current code + git diff
Output: HANDBACK with compliance_score + drift_detected
Logic:
  - Read SPEC, read code, read diff
  - Compare: spec vs code vs diff
  - Detect drift (TYPE_A/B/C/D)
  - compliance_score: (implemented / documented) * 100
  - Decision: 100% + no drift = PASS, else ESCALATE
```

### 13. Quality Gate Orchestrator (Sonnet 4.6)

```
Input: task_id for Quality Gate validation
Output: HANDBACK with final decision (PROCEED/ESCALATE)
Logic:
  - Delegate to 5 sub-agents in parallel
  - Wait for all 5 HANDBACK blocks (timeout: 5 min)
  - Aggregate with priority:
    - Security HIGH → ESCALATE
    - Testing failures → ESCALATE
    - Metrics < 70 → ESCALATE
    - Healing escalations > 0 → ESCALATE
    - Spec Engineer drift → ESCALATE
    - Else → PROCEED
  - Write final HANDBACK with decision + audit trail
```

---

## Feedback Loops Implementation

### Loop 1: Quality Gate Feedback Handler

```
WHEN QG Orchestrator completes:
  1. Read all 5 sub-agent HANDBACK blocks
  2. Aggregate into single audit trail
  3. Store: decision + reason + all 5 results
  4. Track decision confidence
  Output: FEEDBACK block with audit
```

### Loop 2: Model Engineer Feedback Handler

```
WHEN Quality Engineer provides model_assessment:
  1. Read: tokens_used, latency, quality_score, model_assessment
  2. Calculate confidence (formula in Model Engineer)
  3. Generate recommendations (rank_1/2/3)
  4. Store in artifacts/feedback/model-recommendations.jsonl
  Output: Orchestrator reads and applies rank_1 next time
```

### Loop 3: Config Enforcement Feedback Handler

```
WHEN Healing Agent applies fix:
  1. Re-audit configuration post-fix
  2. Measure: did compliance improve?
  3. Update fix confidence:
     - Improved: +0.1
     - Degraded: -0.2
  4. Track: which fix types work reliably
  5. Automation rules:
     - >= 0.95: auto-fix without review
     - 0.80-0.95: auto-fix with QE review
     - < 0.80: escalate to human
  Output: FEEDBACK block with outcome
```

---

## File Structure

```
orchestration/
├── agents/
│   ├── general-orchestrator-agent.md    (Haiku, low)
│   ├── engineer-agent.md                (Haiku, high)
│   ├── senior-engineer-agent.md         (Sonnet, high)
│   ├── lead-engineer-agent.md           (Sonnet, high)
│   ├── principal-engineer-agent.md      (Opus, high)
│   ├── quality-engineer-agent.md        (Sonnet, medium)
│   ├── model-engineer-agent.md          (Haiku, medium)
│   ├── quality-gate-orchestrator-agent.md (Sonnet, medium)
│   ├── security-agent.md                (Opus, max)
│   ├── testing-agent.md                 (Haiku, medium)
│   ├── metrics-agent.md                 (Haiku, medium)
│   ├── healing-agent.md                 (Sonnet, medium)
│   └── spec-engineer-agent.md           (Sonnet, medium)
├── handlers/
│   ├── quality-gate-feedback-handler.md
│   ├── model-engineer-feedback-handler.md
│   └── config-enforcement-feedback-handler.md
├── activators/
│   └── quality-gate-activator.md (how QG is triggered on commits)
└── AGENT-IMPLEMENTATION-GUIDE.md (this file)
```

---

## Testing Strategy

### Unit Tests (per agent)

Each agent needs tests for:
1. **Valid input**: DELEGATE block processed correctly
2. **Invalid input**: Missing fields rejected
3. **Success case**: Task completes, HANDBACK generated
4. **Failure case**: Error handled, escalated with message
5. **Edge case**: Timeout, retry, dependencies

### Integration Tests

1. **Orchestrator → Engineer**: DELEGATE created, delegated, HANDBACK received
2. **Engineer → Quality Engineer**: Quality metrics calculated correctly
3. **Quality Engineer → Model Engineer**: Confidence algorithm validated
4. **Quality Gate**: All 5 sub-agents run, decision made correctly

### End-to-End Tests (Phase 6 validation)

1. **10 test commits** through full Quality Gate
2. **Accuracy**: 10/10 correct PROCEED/ESCALATE decisions
3. **Cost**: Actual cost matches projected $0.31/commit
4. **Latency**: QG completes in < 30 sec (all 5 parallel)

---

## Artifact Management

### DELEGATE Blocks

Location: `artifacts/{YYYY-MM-DD}/DELEGATE-{timestamp}-{role}-{task_id}.yaml`

```yaml
---
handoff_type: DELEGATE
task_id: 2026-MM-DD-unique-id
role: {agent_name}
model: {claude-model}
effort: {low|medium|high}
scope: ...
context: ...
plan: ...
success_criteria: ...
```

### HANDBACK Blocks

Location: `artifacts/{YYYY-MM-DD}/HANDBACK-{timestamp}-{role}-{task_id}.yaml`

```yaml
---
handoff_type: HANDBACK
task_id: {matches_DELEGATE}
status: PASS | ESCALATE
severity: PASS | LOW | MEDIUM | HIGH
... agent-specific fields ...
confidence: 0.0-1.0
```

### FEEDBACK Blocks

Location: `artifacts/{YYYY-MM-DD}/FEEDBACK-{timestamp}-{parent_task_id}.yaml`

```yaml
---
handoff_type: FEEDBACK
parent_task_id: ...
feedback_type: {quality_gate|model_optimization|config_compliance}
observations: ...
recommendations: ...
```

---

## Success Criteria Checklist

- [ ] All 13 agents implemented (stubs + core logic)
- [ ] DELEGATE/HANDBACK protocol working
- [ ] 3 feedback loops operational
- [ ] 10+ test commits validated through Quality Gate
- [ ] 0% false positives, <2% false negatives
- [ ] Cost baseline verified ($0.31/commit)
- [ ] Confidence > 0.90 from Lead Engineer + Principal Engineer

---

**Status**: READY FOR IMPLEMENTATION  
**Start Date**: 2026-05-01  
**Completion Target**: 2026-05-26 (4 weeks)
