---
name: Model Selection Strategy
description: Principle-driven approach to selecting AI models based on task requirements, not vendor or cost alone
type: architecture
created: 2026-04-28
---

# Model Selection Strategy: Capability-First, Cost-Aware

## Core Principle

**Match model capabilities to task requirements.** Every agent task has inherent complexity and output structure. Select the smallest model that reliably solves that task, regardless of vendor.

This applies to:
- Anthropic models (Haiku, Sonnet, Opus)
- Future models from other vendors (OpenAI, Google, Meta, etc.)
- Open-source models (running locally or via inference API)

---

## Model Strength Profiles

### Anthropic Models (Current)

#### Claude Haiku 4.5
**Strengths**:
- Structured output parsing (JSON, YAML, test results)
- Numeric analysis and arithmetic (token efficiency ratios, percentages, scoring)
- Simple routing and classification
- State management (reading/writing parameters)
- Fast inference (ideal for time-sensitive tasks)

**Use cases**:
- Testing Agent: Parse `make test` output, count tests, calculate coverage %
- Metrics Agent: Score service health (0-100 scale), detect anomalies
- Model Engineer: Token efficiency analysis, confidence scoring
- Pattern Recognition: Classify recurring issues
- Budget Optimizer: Arithmetic on costs and allocations

**Cost**: $0.80/$2.40 per 1M tokens (input/output)
**Latency**: ~500ms–1s (fastest)
**Confidence**: 95%+ on structured tasks

---

#### Claude Sonnet 4.6
**Strengths**:
- Multi-step reasoning and planning
- Code generation and refactoring
- Complex problem decomposition
- Trade-off analysis
- Context aggregation from multiple sources

**Use cases**:
- Quality Gate Orchestrator: Aggregate 4 sub-agent results, decide PROCEED/ESCALATE
- Healing Agent: Auto-fix code, configs, Makefiles (generate corrected files)
- Engineer Agent: Implement features, write tests
- Config Enforcement: Apply fixes, verify compliance
- Senior Engineer: Architecture planning, complex refactoring

**Cost**: $3/$15 per 1M tokens (input/output)
**Latency**: ~2–5s
**Confidence**: 85–90% on complex reasoning

---

#### Claude Opus 4.7
**Strengths**:
- Security-critical analysis (zero false negatives)
- Threat modeling and attack surface analysis
- Complex policy interpretation
- High-stakes decision support
- Cross-domain reasoning (finance, legal, security combined)

**Use cases**:
- Security Agent: Credential scanning, permission analysis, vulnerability detection
  - False positives acceptable (human review catches them)
  - False negatives UNACCEPTABLE (security breach)
- Principal Engineer: Cross-service architecture review
- Legal/Compliance: Terms of service, compliance interpretation

**Cost**: $15/$45 per 1M tokens (input/output)
**Latency**: ~5–10s
**Confidence**: 95%+ on security-critical tasks

---

## Decision Tree: Which Model to Use

```
Task requirements?
│
├─ "Output structured data (JSON, YAML, counts, percentages)"
│  └─ Try HAIKU first
│     If success rate > 95%: ✅ STAY HAIKU
│     If success rate 80–95%: Try SONNET
│     If success rate < 80%: Escalate to OPUS
│
├─ "Multi-step reasoning, code generation, trade-offs"
│  └─ Use SONNET
│     If task is novel/experimental: Consider OPUS first
│     If task is repetitive/routine: Consider HAIKU after validation
│
├─ "Security-critical, zero false negatives required"
│  └─ Use OPUS (non-negotiable)
│
├─ "Fast routing, simple classification"
│  └─ Use HAIKU
│
└─ "Unknown / first time solving this problem"
   └─ Start with SONNET (safest middle ground)
      After 5–10 runs, analyze token usage:
      - If < 50% of predicted tokens: Downgrade to HAIKU
      - If 50–80%: SONNET is appropriate
      - If > 80%: Consider OPUS for more capacity
```

---

## Evaluation Framework: From Haiku to Sonnet to Opus

When introducing a new task or agent:

### Phase 1: Validation (Use Sonnet)
- Run task 5–10 times
- Measure: success rate, token usage, latency
- Measure: false positive/negative rate (if applicable)
- Document: actual requirements vs. predicted

### Phase 2: Cost Optimization (Evaluate Downgrade)
- If Haiku success rate ≥ 95%: **Downgrade to Haiku**, save 73% cost
- If Sonnet uses < 50% of predicted tokens: **Downgrade to Haiku**, save cost
- If Sonnet is appropriate: **Keep Sonnet**
- If Sonnet fails < 80%: **Upgrade to Opus**, gain confidence

### Phase 3: Continuous Learning (Model Engineer Agent)
- Track outcome (PASS/FAIL) after each run
- If downgraded model fails: increase confidence of Sonnet
- If Sonnet underutilized: confidence of Haiku increases
- After 20 runs, finalize model selection with > 80% confidence

---

## Example: Testing Agent Optimization

**Initial (Week 1)**: Assigned to Sonnet (safe, unknown task)
- Token usage: 4–10K (predicted 6K)
- Output: Structured (test counts, coverage %, failures)
- Success rate: 100% (test parsing is deterministic)
- Analysis: **Task is structured parsing, well within Haiku capability**

**Decision**: Downgrade to Haiku
- Cost reduction: $0.154 → $0.034 (78% savings)
- Risk: Negligible (parsing is mechanical)
- Confidence: 95%+

**Outcome**: ✅ No regressions, 100% continued success, $50/month saved

---

## Non-Anthropic Models: Future Readiness

### Evaluation Criteria

When evaluating new models (OpenAI GPT-4o, Google Gemini 2.0, Meta Llama, etc.):

1. **Benchmark against Anthropic baseline**
   - Same task, same inputs, measure: success rate, cost, latency
   - Test on both routine and edge-case scenarios

2. **Check compatibility**
   - Can output be parsed reliably (JSON, YAML)?
   - Does it support structured output format?
   - Is API stable and well-documented?

3. **Cost-performance trade-off**
   - Haiku task: Is new model cheaper + equal/better success?
   - Sonnet task: Cost vs. success rate vs. latency
   - Opus task: Cost vs. confidence on security/critical tasks

4. **Operational considerations**
   - Rate limits and quota handling
   - Fallback strategy if model becomes unavailable
   - Data residency and privacy (EU regulations, etc.)

### Template for New Model Addition

If a new model meets criteria, add to `Cost Model` table:

```markdown
| Model | Vendor | Agent Type | Cost | When to Use | Notes |
|-------|--------|-----------|------|-------------|-------|
| GPT-4o mini | OpenAI | Structured Parsing | $0.015/1M | Alternative to Haiku | Evaluate on 10 test runs |
| Gemini 2.0 Flash | Google | Routing | $0.05/1M | Fast inference | Check data residency |
| Llama 3.1 70B | Meta (via Together) | Code Generation | $0.90/1M input | Cost-sensitive tasks | Local/self-hosted option |
```

---

## Cost Model: Current Hierarchy (Sorted by Cost per Task)

| Task Type | Haiku | Sonnet | Opus | Selection |
|-----------|-------|--------|------|-----------|
| Parsing + Counting | $0.02–0.05 | $0.06–0.15 | — | **Haiku** |
| Numeric Analysis | $0.02–0.06 | $0.09–0.21 | — | **Haiku** |
| Routing | $0.01–0.03 | $0.06–0.15 | — | **Haiku** |
| Code Review | — | $0.09–0.24 | $0.27–0.60 | **Sonnet** |
| Auto-fix Code | — | $0.09–0.24 | $0.27–0.60 | **Sonnet** |
| Security Scanning | — | $0.15–0.45 | $0.18–0.45 | **Opus** |
| Architecture Design | — | $0.15–0.45 | $0.30–0.75 | **Sonnet** (or Opus) |
| Complex Reasoning | — | $0.06–0.24 | $0.18–0.60 | **Sonnet** |

---

## Principles in Practice

### ✅ Do This

- Start with the smallest capable model
- Measure real outcomes (success rate, token usage)
- Downgrade if data supports it
- Continuously re-evaluate (Model Engineer Agent)
- Document rationale for each model choice (why Haiku for Testing, why Opus for Security)

### ❌ Don't Do This

- Automatically use the largest/most expensive model
- Assume "more compute = better results" (often false for structured tasks)
- Neglect to measure actual token usage and success rates
- Upgrade a model without data supporting the upgrade
- Choose vendor loyalty over performance (evaluate all vendors)

---

## Future: Bedrock Integration

When migrating to AWS Bedrock (Phase 8+):

1. **Replicate current model selection** with Bedrock equivalents
   - Anthropic models available via Bedrock
   - Cross-test OpenAI, Cohere, Llama models
   
2. **Maintain OpenTelemetry spans** with `model_name` attribute
   - Facilitates future model swaps
   - Enables cost per agent per model analysis

3. **Add A/B testing capability**
   - Sample 10% of tasks with alternative model
   - Compare: success rate, cost, latency, token efficiency
   - Migrate if new model is demonstrably better

---

## Governance: Adding a New Model

Before deploying a new model to production:

- [ ] Benchmarked on 10+ real tasks
- [ ] Success rate ≥ baseline (or justified exception)
- [ ] Cost-performance analyzed
- [ ] OpenTelemetry spans updated (`model_name` attribute)
- [ ] Fallback strategy documented
- [ ] Team review + approval
- [ ] Documentation updated (this file)

---

## Review & Update Cadence

- **Monthly**: Check Model Engineer recommendations, update costs
- **Quarterly**: Evaluate new models from other vendors, benchmark
- **Semi-annually**: Deep cost analysis, potential model swaps
- **Ad-hoc**: When new capabilities needed or vendor changes pricing
