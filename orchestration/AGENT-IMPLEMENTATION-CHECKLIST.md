# Agent Implementation Checklist

Use this checklist when implementing any of the 13 agents in Phase 6.

## Pre-Implementation

- [ ] **Read the specification**
  - [ ] Review agent role in `docs/SPEC.md`
  - [ ] Understand DELEGATE block requirements
  - [ ] Understand HANDBACK block structure
  - [ ] Review confidence scoring algorithm

- [ ] **Study reference impls**
  - [ ] `ORCHESTRATOR-IMPLEMENTATION-REFERENCE.py` (routing logic)
  - [ ] `ENGINEER-IMPLEMENTATION-REFERENCE.py` (execution pattern)
  - [ ] `AGENT-IMPLEMENTATION-TEMPLATE.py` (starting point)

- [ ] **Review testing**
  - [ ] Read `QUALITY-GATE-TEST-FRAMEWORK.md` (test scenarios)
  - [ ] Run `testing_harness.py` to see expected behavior
  - [ ] Understand what your agent needs to pass

- [ ] **Understand your agent**
  - [ ] Read agent spec in `orchestration/agents/{agent-name}-agent.md`
  - [ ] Understand role, input, output, success criteria
  - [ ] Note any special requirements or edge cases

## Implementation

### 1. Set Up

- [ ] **Find your stub implementation**
  ```bash
  grep -n "class YOUR_AGENT_NAME" orchestration/agents/implementations.py
  ```

- [ ] **Understand the stub structure**
  - Agent inherits from `Agent` base class
  - `__init__()` calls `super().__init__(CONFIG)`
  - `do_work()` method is where real logic goes

### 2. Implement do_work()

- [ ] **Extract inputs from DELEGATE**
  ```python
  scope = self.delegate_block.get("scope", "")
  context = self.delegate_block.get("context", {})
  ```

- [ ] **Validate required fields**
  ```python
  if not scope:
      raise ValueError("scope is required")
  ```

- [ ] **Build Claude prompt**
  - Clear task description
  - Include context
  - Specify output format (JSON recommended)
  - Set expectations for confidence/evidence

- [ ] **Call Claude API**
  ```python
  response = anthropic_client.messages.create(
      model=self.config.model,  # Use config, not hardcoded
      max_tokens=2048,
      messages=[{"role": "user", "content": prompt}]
  )
  ```

- [ ] **Parse response**
  - Handle both structured (JSON) and free-form text
  - Extract key fields
  - Validate parsed data

- [ ] **Calculate confidence**
  - Baseline from algorithm in SPEC.md
  - Adjust based on result quality
  - Clamp to [0.30, 1.00]

- [ ] **Return HANDBACK fields**
  ```python
  return {
      "result": parsed_result,
      "deliverables": [...],
      "quality_score": score,
      "confidence": confidence,
      "token_metrics": {
          "input_tokens": ...,
          "output_tokens": ...
      }
  }
  ```

### 3. Testing

- [ ] **Unit test: valid DELEGATE**
  ```python
  agent = create_agent("your_agent")
  delegate = {...}  # Valid DELEGATE block
  result = agent.execute(delegate)
  assert result["status"] == "PASS"
  ```

- [ ] **Unit test: missing required field**
  ```python
  delegate = {...}  # Missing required field
  result = agent.execute(delegate)
  assert result["status"] == "ESCALATE"
  ```

- [ ] **Integration test: through orchestrator**
  ```python
  python orchestration/agents/example_end_to_end.py
  # Verify your agent in the chain
  ```

- [ ] **Quality Gate test scenarios**
  - [ ] Run `testing_harness.py`
  - [ ] Verify scenarios involving your agent
  - [ ] Check accuracy (0% false positives, <2% false negatives)

- [ ] **Performance test**
  - [ ] Token usage reasonable for model/effort
  - [ ] Latency acceptable (<30s for QG, <5s per agent)
  - [ ] Cost within budget ($0.003-$0.375 per execution)

### 4. Code Review

- [ ] **Read your own code**
  - Does it follow the pattern from reference impls?
  - Is error handling comprehensive?
  - Are comments clear where needed?

- [ ] **Validate HANDBACK structure**
  - [ ] `handoff_type: "HANDBACK"`
  - [ ] `task_id` from DELEGATE
  - [ ] `status`: PASS or ESCALATE
  - [ ] `severity`: PASS, LOW, MEDIUM, HIGH
  - [ ] `confidence`: 0.0-1.0
  - [ ] All agent-specific fields present

- [ ] **Check artifact writing**
  ```python
  # In workflow.py, verify your agent's results are written:
  artifacts.write_handback(task_id, result)
  ```

- [ ] **Token metrics accuracy**
  - Real implementation: count actual tokens from Claude
  - Stub: rough estimate (len(text) / 4 tokens)
  - Budget: <5000 tokens per agent execution

### 5. Documentation

- [ ] **Update agent spec** (if needed)
  ```bash
  cat orchestration/agents/{agent-name}-agent.md
  ```
  - Add any implementation notes
  - Document edge cases discovered
  - Record confidence algorithm customization

- [ ] **Add examples to README**
  ```bash
  # Add example usage to orchestration/agents/README.md
  ```

- [ ] **Comment tricky code**
  - Why (not what)
  - Non-obvious invariants
  - Edge case handling

### 6. Integration

- [ ] **Verify in example_end_to_end.py**
  ```bash
  python orchestration/agents/example_end_to_end.py
  ```
  - Your agent executes correctly
  - HANDBACK written to artifacts/
  - Next agent receives HANDBACK properly

- [ ] **Verify in testing_harness.py**
  ```bash
  python orchestration/agents/testing_harness.py
  ```
  - All 10 scenarios pass
  - Your agent's behavior correct for each scenario
  - Confidence scores reasonable

- [ ] **Verify in workflow.py**
  ```bash
  python orchestration/agents/workflow.py
  ```
  - Complete task execution pipeline works
  - Artifacts written correctly
  - Summary printed properly

### 7. Cost & Performance

- [ ] **Estimate cost**
  - Model cost from pricing table in README
  - Token usage from implementation
  - Daily/weekly/monthly projections

- [ ] **Measure latency**
  - Time from execute() to return
  - Target: <5s per agent, <30s for QG

- [ ] **Track metrics**
  - Token usage per task type
  - Confidence distribution (avg, min, max)
  - Error/escalation rates

### 8. Final Validation

- [ ] **All tests pass**
  ```bash
  python -m pytest orchestration/agents/test_*.py -v
  ```

- [ ] **Example runs without error**
  ```bash
  python orchestration/agents/example_end_to_end.py
  ```

- [ ] **Harness pass rate**
  ```bash
  python orchestration/agents/testing_harness.py
  # Should show 100% pass rate (all 10 scenarios)
  ```

- [ ] **Artifact inspection**
  ```bash
  ls artifacts/2026-04-29/
  cat artifacts/2026-04-29/HANDBACK-*.yaml
  # Verify correct structure and values
  ```

- [ ] **Code review checklist**
  - [ ] Follows reference impl patterns
  - [ ] Error handling comprehensive
  - [ ] HANDBACK structure correct
  - [ ] Confidence calculation reasonable
  - [ ] Comments explain why, not what
  - [ ] No hardcoded values (use config)
  - [ ] Token metrics included

## Week-by-Week Targets

### Week 1 (SDLC Agents)

Implement in this order:
1. GeneralOrchestrator (routing decision tree)
2. EngineerAgent (plan execution)
3. SeniorEngineerAgent (analysis & planning)
4. LeadEngineerAgent (8-point code review)
5. PrincipalEngineerAgent (architecture analysis)
6. QualityEngineerAgent (quality assessment)
7. ModelEngineerAgent (confidence + recommendations)
8. SecurityEngineerAgent (threat modeling)

**Success:** All 8 agents pass testing_harness.py

### Week 2 (QG Sub-Agents)

1. SecurityAgentQG (credential/vulnerability scanning)
2. TestingAgent (coverage metrics)
3. MetricsAgent (system health)
4. HealingAgent (config validation)
5. SpecEngineerAgent (spec drift detection)
6. QualityGateOrchestrator (aggregation)

**Success:** All 10 test scenarios pass (PROCEED/ESCALATE correct)

### Week 3 (Feedback Loops)

1. Quality Gate Feedback Handler
2. Model Engineer Feedback Handler
3. Config Enforcement Feedback Handler

**Success:** Feedback flows to appropriate handlers

### Week 4 (Integration & Tuning)

- End-to-end testing with real commits
- Performance optimization
- Cost analysis
- Documentation finalization

## Common Pitfalls

❌ **Don't:**
- Hardcode model names (use self.config.model)
- Skip error handling (raise ValueError, RuntimeError)
- Calculate confidence without bounds [0.30, 1.00]
- Forget task_id in HANDBACK
- Forget confidence in HANDBACK
- Forget token_metrics in HANDBACK
- Skip artifact writing
- Use stub placeholder results in real implementation

✅ **Do:**
- Extract inputs from delegate_block
- Validate required fields
- Call Claude with appropriate model
- Parse response carefully
- Calculate confidence based on result quality
- Return complete HANDBACK dict
- Write artifacts for debugging
- Test with harness before integration

## Troubleshooting

**Agent returns ESCALATE when should PROCEED:**
- [ ] Check HANDBACK status field
- [ ] Check confidence score (should be >0.70 for PASS)
- [ ] Check if required HANDBACK fields present
- [ ] Look for validation errors in error field

**Token count too high:**
- [ ] Reduce prompt verbosity
- [ ] Split large tasks into steps
- [ ] Use cheaper model if possible
- [ ] Increase max_tokens cap (if needed)

**Confidence too low:**
- [ ] Review confidence algorithm in SPEC.md
- [ ] Check quality_score calculation
- [ ] Verify it's within [0.30, 1.00] bounds
- [ ] Compare with reference impls

**Testing harness fails for your agent:**
- [ ] Run example_end_to_end.py in isolation
- [ ] Print HANDBACK to debug structure
- [ ] Check artifact files in artifacts/YYYY-MM-DD/
- [ ] Verify decision logic matches expectations

## Sign-Off

Once implementation complete:

- [ ] **Code review** (by Lead Engineer)
- [ ] **Testing** (all 10 scenarios pass)
- [ ] **Performance** (meets latency/cost targets)
- [ ] **Documentation** (agent spec updated)
- [ ] **Integration** (works in full pipeline)

---

**Week 1 Target:** 8 SDLC agents complete  
**Week 2 Target:** 5 QG sub-agents + orchestrator complete  
**Week 3 Target:** 3 feedback loops complete  
**Week 4 Target:** Full integration & tuning complete  

**Total Phase 6 Duration:** 4 weeks, 116-142 hours
