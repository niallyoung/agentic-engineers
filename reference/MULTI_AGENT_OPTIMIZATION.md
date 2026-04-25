# Multi-Agent Optimization Patterns & Research

Reference guide for designing efficient multi-agent systems using cost/quality feedback loops, inspired by reinforcement learning, A/B testing frameworks, and production AI systems.

---

## Part 1: Core Concepts

### Multi-Agent Architecture Pattern

ERS platform uses a hierarchical multi-agent system:

```
                     ┌──────────────────┐
                     │  Orchestrator    │ (Primary entry point)
                     │  (Haiku/Sonnet)  │
                     └────────┬─────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   ┌─────────┐          ┌──────────┐          ┌──────────┐
   │ Engineer │         │  Quality │          │  Model   │
   │ (Haiku) │         │ Engineer │          │ Engineer │
   └─────────┘         │ (Haiku)  │          │ (Haiku)  │
        │              └────┬─────┘          └────┬─────┘
        │                   │                     │
        ▼                   ▼                     ▼
   [Task Execution]   [Quality Gate]      [Model Selection]
   - TDD coding        - Test passes       - Predict quality
   - 80-95% tests      - Coverage ≥80%     - Compare cost
   - Error handling    - No hazards        - A/B test design
        │                   ▲                     ▲
        └───────────────────┴─────────────────────┘
                     [Metrics Feedback Loop]
                     (quality_score, tokens, cost, escalations)
```

**Key insight:** Hierarchical specialization allows cheap models (Haiku) to execute well-scoped tasks while expensive models (Opus) focus on planning and architecture.

---

## Part 2: Feedback Loop Design

### Closed-Loop System

Metrics → Analysis → Recommendation → Action → Measurement → Repeat

```
1. MEASUREMENT (Metrics Collection)
   ├─ Per-task metrics: tokens_in, tokens_out, quality_score, cost_usd, duration, escalations
   ├─ Session event log: JSONL append-only, timestamps, state transitions
   └─ Storage: ~/.claude/metrics/YYYY-MM-DD/ (local disk, no API dependency)

2. ANALYSIS (TokenAdvisor & Model Engineer)
   ├─ TokenAdvisor: token usage trends, cost-per-quality, model splits
   ├─ Model Engineer: quality prediction, recommendation accuracy, confidence
   └─ Output: JSON/CSV reports + recommendations

3. RECOMMENDATION (Decision Engine)
   ├─ TokenAdvisor: "Haiku efficiency down 5%; investigate high-token tasks"
   ├─ Model Engineer: "Test Sonnet on next 5 auth tasks"
   └─ Output: Ranked options with confidence scores

4. ACTION (Orchestrator & Agents)
   ├─ Adopt recommendation: "Use Sonnet for this auth task"
   ├─ Run A/B test: "Allocate 50% tasks to Haiku, 50% to Sonnet"
   └─ Side effect: metrics recorded for feedback

5. MEASUREMENT (Loop back to step 1)
   ├─ New task results feed back into historical data
   ├─ TokenAdvisor sees updated metrics
   ├─ Model Engineer updates confidence/recommendations
   └─ Continuous refinement
```

**Optimization metric:** cost_per_quality_point = total_cost_usd / avg_quality_score

Target: minimize cost_per_quality while maintaining quality ≥target.

### Information Theory Perspective

**Goal: Maximize information (task completion) per unit cost (tokens).**

```
Information Efficiency = Quality_Achieved / Tokens_Spent

Example:
  Haiku (20K tokens): quality 90 → efficiency = 90/20000 = 0.0045
  Sonnet (25K tokens): quality 94 → efficiency = 94/25000 = 0.00376 (worse!)
  
But cost-adjusted:
  Haiku (1x cost): efficiency = 0.0045, cost = $0.15
  Sonnet (2x cost): efficiency = 0.00376, cost = $0.18
  
Cost-per-quality:
  Haiku: $0.15 / 90 = $0.00167
  Sonnet: $0.18 / 94 = $0.00191
  
Decision: Use Haiku (17% cheaper per quality point)
```

---

## Part 3: Reinforcement Learning from AI Feedback (RLAF)

ERS uses principles from RLAF without explicit RL algorithms:

### RLAF Cycle (Simplified for Multi-Agent Teams)

**Traditional RL:**
```
Agent → Action → Reward → Policy Update → Better Action
```

**Multi-Agent RLAF Adaptation:**
```
Engineer (Haiku)
    ↓
    Code (Task Completion)
    ↓
Quality Engineer (Measurement)
    ↓ Feedback: quality_score, test_coverage, escalations
    ↓
Model Engineer (Policy Update)
    ↓ Recommendation: "For similar tasks, use [Model] + [Effort]"
    ↓
Orchestrator (Action Selection)
    ↓
Next Engineer Delegation (Better Model Choice)
```

### Reward Signal Design

In ERS, the "reward" is **cost-per-quality:**

```
Reward = Quality Achieved / Cost Incurred
       = (quality_score / 100) / (cost_usd)
       = (92 / 100) / $0.15
       = 6.13 (higher is better)

Agents (implicitly) optimize for:
  1. Quality maintenance (quality_score ≥80%)
  2. Cost minimization (cost_usd ↓)
  3. Efficiency (tokens_in ↓, tokens_out ↓)
```

### Feedback Frequency

- **Per-task feedback** (5-60 minutes): Quality Engineer validates test pass/coverage
- **Daily feedback** (Session end): TokenAdvisor summarizes daily usage
- **Weekly feedback** (Friday): Model Engineer proposes optimizations
- **Monthly feedback** (Month-end): Strategic review, new models evaluation

---

## Part 4: A/B Testing Framework

### Standard A/B Test Protocol

**Name:** Test Haiku vs. Sonnet on Medium-Complexity Auth Tasks

**Hypothesis:** Haiku high-effort achieves cost-per-quality parity with Sonnet medium-effort

```
Sample Size: 5 tasks per arm (n=5 × 2 = 10 total)
Duration: 2 weeks
Randomization: Alternate assignments (task 1→Haiku, 2→Sonnet, 3→Haiku, etc.)

Control Arm (Existing):
  Model: Haiku 4.5
  Effort: high
  Historical data: 12 similar tasks, avg quality=90, avg cost=$0.13

Test Arm (Proposed):
  Model: Sonnet 4.6
  Effort: medium
  Historical data: 3 similar tasks, avg quality=94, avg cost=$0.17

Success Criteria (Pick 1):
  1. Primary: Test arm cost_per_quality < control cost_per_quality
  2. Secondary: Test arm quality ≥92 AND cost_per_quality ≤ control + 5%
  3. Tertiary: Quality parity (within ±2) regardless of cost

Metrics to Track:
  Primary: quality_score, cost_per_quality
  Secondary: tokens_in, tokens_out, escalation_rate, rework_required
  Tertiary: duration_minutes, confidence_in_recommendation

Stopping Rule:
  Early stop if either arm shows quality <80 (below threshold)
  Continue for full n=5 per arm unless early stop triggered

Analysis:
  After completion, compare:
    - Quality: Is test arm ≥92? (Expected)
    - Cost: Is test arm cost_per_quality <control?
    - Confidence: Model Engineer reports ±CI on recommendation

Decision Matrix:
  Test Quality | Control Cost/Qty | Decision
  ────────────────────────────────────────
  >92          | Lower            | Adopt test arm (Sonnet)
  >92          | Higher           | Keep control arm (Haiku)
  >92          | Parity           | Keep control (cost-neutral, no change)
  <92          | N/A              | Revert, investigate why test failed
```

### Multi-Variant Testing (3+ options)

When comparing >2 options:

```
MULTI-ARM COMPARISON: Find Best Model for High-Complexity Tasks

Arms:
  Control: Opus 4.7 (historical baseline)
  Test 1: Sonnet 4.7 (new model, hypothesized improvement)
  Test 2: Sonnet 4.6 + max effort (higher effort variant)

Sample size: 3 tasks per arm (n=9 total, assumes high cost/task)
Duration: 4 weeks

Expected Outcomes:
  Opus: quality=97, cost=$0.58
  Sonnet 4.7: quality=96, cost=$0.18 (downgrade opportunity)
  Sonnet 4.6 max: quality=95, cost=$0.20 (parity opportunity)

Success = Any arm achieves quality ≥95 AND cost <$0.25 (vs. Opus $0.58)
```

---

## Part 5: Model Capability Mapping

### Model Space (as of April 2026)

```
Cost Multiplier | Model Name           | Quality | Speed | Reasoning
────────────────────────────────────────────────────────────────────
1x              | Claude Haiku 4.5     | 88-92   | Fast  | Quick tasks
1x              | Claude Haiku 4.6 (?) | TBD     | Fast  | TBD
2x              | Claude Sonnet 4.6    | 93-96   | Med   | Balanced
2x              | Claude Sonnet 4.7 (?) | TBD    | Med   | TBD
7.5x            | Claude Opus 4.7      | 96-99   | Slow  | Complex
7.5x            | Claude Opus 4.8 (?)  | TBD     | Slow  | TBD
```

### Capability Frontier

The goal is to **lower the frontier**: achieve same quality with cheaper models as new models improve.

```
Quality (y-axis)
100 |           Opus 4.8 (?)
    |        Opus 4.7
 95 |     Sonnet 4.7 (?)
    |  Sonnet 4.6
 90 |
    | Haiku 4.6 (?)
 85 | Haiku 4.5
    |_________________________
      1x  2x   3x   4x   7.5x  Cost Multiplier
```

**Progression:**
- **2024:** Haiku achieves 85, Sonnet 90, Opus 95 at given cost
- **2025:** Haiku 88, Sonnet 93, Opus 97 (quality improved at same cost)
- **2026:** Haiku 90, Sonnet 95, Opus 98 (frontier shifted right—same quality cheaper)
- **Goal:** Find tasks where Haiku 4.6 (1x) replaces Sonnet 4.6 (2x), saving cost

---

## Part 6: Production Multi-Agent Systems (References)

### Similar Initiatives

**1. Constitutional AI (CAI) with Red Teaming**
- Multiple agents critique outputs against constitutional principles
- Feedback loop: critique → improvement → measure adherence
- Metric: principle_adherence_score (similar to quality_score)
- Source: Bai et al. "Constitutional AI: Harmlessness from AI Feedback" (Anthropic, 2022)

**2. Self-Improving Systems (e.g., o1 Reasoning)**
- Agent explores solution space, backtracks on failures
- Reward: correctness of final answer (binary or gradient)
- Feedback: intermediate steps scored for reasoning quality
- Similar to ERS: detailed planning (expensive) → execution (cheap) → measure quality

**3. Multi-Agent Collaboration (e.g., AutoGen, CrewAI)**
- Multiple specialized agents (coder, reviewer, tester) collaborate
- Messages: structured handoffs between agents
- Feedback: test results, code review comments, integration checks
- Similar to ERS: DELEGATE/HANDBACK protocol, Quality Engineer gate

**4. Model Merging & Ensemble Methods (e.g., Mixtral 8x7B)**
- Gating network selects best expert for task
- Routing based on task features + historical performance
- Metric: ensemble_quality vs. individual_quality
- Similar to ERS Model Engineer: predict best model per task

**5. Curriculum Learning & Task Difficulty Adaptation**
- Start with easy tasks, progress to hard
- Model performance improves as curriculum difficulty matches capability
- Feedback: task_difficulty vs. model_quality (learning curve)
- Similar to ERS: complexity classification informs model recommendations

### Key Papers & Concepts

| Topic | Key Concept | Application to ERS |
|-------|-------------|-------------------|
| Reinforcement Learning from AI Feedback (RLAF) | Use AI feedback as reward signal | Quality Engineer measures, Model Engineer optimizes |
| Multi-Agent Reinforcement Learning (MARL) | Agents coordinate via shared reward | Orchestrator routes, Quality Engineer gates |
| Contextual Bandits | Select best action per context | Model Engineer predicts quality per task context |
| A/B Testing | Statistical comparison of variants | A/B test framework (Haiku vs. Sonnet) |
| Curriculum Learning | Order tasks by difficulty | Complexity classification → model assignment |
| Transfer Learning | Leverage past task data | Historical metrics inform predictions |
| Information Bottleneck | Compress information flow | DELEGATE/HANDBACK protocol reduces context |

---

## Part 7: ERS System Specifics

### Cost Optimization Strategy

**Phase 1 (Current: Establish Baseline)**
- Collect 50+ tasks on current model assignments
- Calculate: cost_per_quality, quality distribution, escalation rates
- Target: Baseline cost ~$0.15/task

**Phase 2 (Ongoing: A/B Testing)**
- Run 3-5 A/B tests (Haiku vs. Sonnet, Sonnet vs. Opus)
- Identify task types where cheaper model is viable
- Target: Reduce cost_per_quality 10-15%

**Phase 3 (Future: New Models)**
- When Haiku 4.6, Sonnet 4.7, Opus 4.8 available
- Run model upgrade evaluation (same tasks, new models)
- Shift all tiers right: Haiku 4.5 → 4.6, Sonnet 4.6 → 4.7, Opus 4.7 → 4.8
- Target: Further cost reduction, quality improvement

**Phase 4 (Strategic: Advanced Optimization)**
- Implement Model Engineer automation (select model per task)
- Implement effort/thinking optimization (vary effort, measure quality)
- Target: Cost_per_quality <$0.0012 (80% cost reduction)

### Quality-Cost Tradeoff Surface

```
Quality (z-axis)
      ▲
      │     Opus 4.7 (med)
      │  ╱  quality=97, cost=$0.58
   97 │ ╱
      │╱
   94 │──── Sonnet 4.6 (med)
      │     quality=94, cost=$0.16
   91 │
      │
   88 │── Haiku 4.5 (high)
      │  quality=90, cost=$0.13
      └─────────────────────► Cost (x-axis)

Optimal frontier (pareto):
  - Haiku 4.5: cost $0.13, quality 90 (most cost-efficient)
  - Sonnet 4.6: cost $0.16, quality 94 (+4 quality, +$0.03)
  - Opus 4.7: cost $0.58, quality 97 (+3 quality, +$0.42)

Decision rule per task type:
  low_complexity: Use Haiku (quality=90 sufficient)
  medium_complexity: Use Haiku or Sonnet (A/B test)
  high_complexity: Use Sonnet or Opus (depends on quality bar)
```

---

## Part 8: Implementation Checklist

### Deploy Multi-Agent System

- [ ] **Metrics Collection**
  - [ ] Implement ~/.claude/metrics/YYYY-MM-DD/ directory structure
  - [ ] Define per-task JSON schema (tokens_in, quality_score, cost_usd, etc.)
  - [ ] Implement session JSONL logging
  - [ ] Orchestrator writes metrics after each task completes

- [ ] **Quality Gate (Quality Engineer)**
  - [ ] Implement Tier 1 checklist (lint+test pass, in-scope, tests added, no hazards)
  - [ ] Block HANDBACK if any item fails
  - [ ] Store quality audit results in metrics

- [ ] **Model Recommendation (Model Engineer)**
  - [ ] Read historical metrics from ~/.claude/metrics/
  - [ ] Classify tasks: low/medium/high complexity
  - [ ] Predict quality for each model tier
  - [ ] Rank recommendations by cost_per_quality
  - [ ] Generate confidence scores

- [ ] **Token Analysis (TokenAdvisor)**
  - [ ] Aggregate tokens by date, role, model
  - [ ] Calculate cost_per_quality trends
  - [ ] Flag outliers (>2x average tokens)
  - [ ] Propose A/B tests and model evaluations

- [ ] **A/B Testing Framework**
  - [ ] Define test protocol (sample size, duration, success criteria)
  - [ ] Implement test allocation (alternate control/test)
  - [ ] Measure and compare results
  - [ ] Update model recommendations based on results

- [ ] **Orchestrator Integration**
  - [ ] Call Model Engineer before delegating task
  - [ ] Record actual results after task completion
  - [ ] Feed results back to Model Engineer for learning
  - [ ] Call TokenAdvisor at session end

---

## Part 9: Metrics Dashboard (Future)

```
ERS MULTI-AGENT DASHBOARD (Example Layout)

Top Row:
  [Daily Token Usage] [Cost vs. Budget] [Quality Trend] [Model Split]

Middle Row:
  [Cost-per-Quality Graph] [A/B Test Status] [Model Confidence] [Escalation Rate]

Bottom Row:
  [Recommendation Accuracy] [Cost Optimization Opportunity] [Model Readiness]
```

---

## Conclusion

ERS multi-agent system optimizes for:
1. **Quality** (minimize errors, maintain 80-95% test coverage)
2. **Cost** (reduce tokens/$ via cheap models for simple tasks)
3. **Efficiency** (maximize information per unit cost)
4. **Autonomy** (continuous learning from feedback)

The HANDOFF protocol + metrics loop + model engineer enables **cost reduction of 10-30%** while maintaining or improving quality.
