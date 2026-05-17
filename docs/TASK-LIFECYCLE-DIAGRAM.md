# Agentic-Engineers Task Lifecycle Diagram

## Complete Task Flow (Single Diagram)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                        AGENTIC-ENGINEERS TASK LIFECYCLE                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌──────────────────┐
                                    │  USER REQUEST    │
                                    │  (via @mention)  │
                                    └────────┬─────────┘
                                             │
                                             ▼
                        ┌────────────────────────────────────────┐
                        │     ORCHESTRATOR RECEIVES TASK         │
                        │  • Parse requirements & scope          │
                        │  • Estimate complexity & tokens        │
                        │  • Analyze task type                   │
                        └────────────┬─────────────────────────┘
                                     │
                                     ▼
                    ┌────────────────────────────────────────────────┐
                    │  SMART ROUTING DECISION (9-SIGNAL PRIORITY)    │
                    │  1. Explicit role requirement?                 │
                    │  2. Quality gate check (baseline ≥85/100)      │
                    │  3. Security scope?                            │
                    │  4. Cross-service architecture?                │
                    │  5. Skill affinity match?                      │
                    │  6. Code review needed?                        │
                    │  7. Complexity level?                          │
                    │  8. Agent success rate (trending)?             │
                    │  9. Default fallback (Engineer)                │
                    └────────────┬─────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
        ┌───────────▼──────────────┐  ┌──────▼──────────────────┐
        │  COST-AWARE ROUTING      │  │  QUALITY ENFORCEMENT    │
        │  • Select lowest-cost    │  │  • Check baseline       │
        │    agent meeting         │  │  • Verify threshold     │
        │    quality threshold     │  │  • Escalate if needed   │
        │  • 5 optimization types: │  │  • 4-band enforcement:  │
        │    - Model downgrade     │  │    - PROCEED (≥90%)     │
        │    - Effort reduction    │  │    - WARN (85-90%)      │
        │    - Parallelization     │  │    - FAIL (<85%)        │
        │    - Caching             │  │    - BLOCK (repeated)   │
        │    - Model upgrade       │  │                         │
        └───────────┬──────────────┘  └──────┬──────────────────┘
                    │                         │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌────────────────────────────────────────┐
                    │  CREATE DELEGATE (YAML/JSON)           │
                    │  • Task ID (YYYY-MM-DD-kebab-case)     │
                    │  • Role (Engineer/Senior/Lead/etc)     │
                    │  • Model (Haiku/Sonnet/Opus)           │
                    │  • Effort (low/medium/high)            │
                    │  • Plan (step-by-step if needed)       │
                    │  • Success criteria                    │
                    │  • Token budget estimate               │
                    │  • Skill requirements                  │
                    │  • Quality baseline                    │
                    └────────────┬─────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────────────────────┐
                    │  QUEUE MANAGEMENT                      │
                    │  • Validate DELEGATE schema            │
                    │  • Check for duplicates                │
                    │  • Move to artifacts/queue/incoming/   │
                    │  • Update TODO.md                      │
                    │  • Git commit & push                   │
                    └────────────┬─────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────────────────────┐
                    │  SPECIALIST AGENT EXECUTES             │
                    │  • Load DELEGATE from queue            │
                    │  • Execute task per plan               │
                    │  • Collect metrics (tokens, time)      │
                    │  • Track quality signals               │
                    │  • Generate deliverables               │
                    │  • Test & validate                     │
                    └────────────┬─────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────────────────────┐
                    │  CREATE HANDBACK (YAML/JSON)           │
                    │  • Task ID (matches DELEGATE)          │
                    │  • Status (success/partial/failed)     │
                    │  • Deliverables (files/code/docs)      │
                    │  • Tests (count, pass rate)            │
                    │  • Metrics:                            │
                    │    - Tokens used                       │
                    │    - Time elapsed                      │
                    │    - Quality score (0-100)             │
                    │    - Cost (USD)                        │
                    │  • Model assessment feedback           │
                    │  • Issues/blockers                     │
                    │  • Recommendations                     │
                    └────────────┬─────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────────────────────┐
                    │  QUEUE MANAGEMENT (HANDBACK)           │
                    │  • Move to artifacts/queue/processing/ │
                    │  • Validate HANDBACK schema            │
                    │  • Extract metrics                     │
                    │  • Git commit                          │
                    └────────────┬─────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────────────────────┐
                    │  QUALITY ENGINEER REVIEW               │
                    │  • Verify deliverables                 │
                    │  • Check test coverage                 │
                    │  • Validate quality score              │
                    │  • Approve or request changes          │
                    │  • Move to artifacts/queue/done/       │
                    └────────────┬─────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────────────────────┐
                    │  FEEDBACK LOOP & METRICS               │
                    │  • Record task outcome                 │
                    │  • Update quality baselines            │
                    │  • Trend analysis (7/30-day MA)        │
                    │  • Feedback cycle (5-stage):           │
                    │    1. Outcome recording                │
                    │    2. Quality assessment               │
                    │    3. Feedback collection              │
                    │    4. Trend analysis                   │
                    │    5. Routing improvement              │
                    │  • Cost tracking & optimization        │
                    │  • Model Engineer recommendations      │
                    └────────────┬─────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────────────────────┐
                    │  CONTINUOUS IMPROVEMENT                │
                    │  • Update smart router signals         │
                    │  • Adjust cost-aware routing           │
                    │  • Refine quality thresholds           │
                    │  • Optimize model selection            │
                    │  • Improve success rates               │
                    │  • Reduce token spend                  │
                    └────────────┬─────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────────────────────┐
                    │  DELIVERABLES TO USER                  │
                    │  • Code/features merged                │
                    │  • Tests passing (≥90% coverage)       │
                    │  • Quality ≥90/100                     │
                    │  • Documentation updated               │
                    │  • Metrics collected & analyzed        │
                    │  • Feedback for next iteration         │
                    └────────────────────────────────────────┘
```

---

## Key Components Explained

### 1. **Orchestrator** (Entry Point)
- Receives user requests via `@orchestrator` mention
- Parses task requirements and scope
- Estimates complexity and token budget
- Routes to appropriate specialist

### 2. **Smart Routing** (9-Signal Priority)
- **Signal 1**: Explicit role requirement (security, principal, etc.)
- **Signal 2**: Quality gate check (baseline ≥85/100)
- **Signal 3**: Security scope (→ Security Engineer)
- **Signal 4**: Cross-service architecture (→ Principal Engineer)
- **Signal 5**: Skill affinity match (→ matching specialist)
- **Signal 6**: Code review needed (→ Lead/Quality Engineer)
- **Signal 7**: Complexity level (→ Senior Engineer for complex)
- **Signal 8**: Agent success rate trending (→ high-performing agent)
- **Signal 9**: Default fallback (→ Engineer)

### 3. **Cost-Aware Routing**
Routes to **lowest-cost agent** meeting quality threshold:
- **Model downgrade**: Haiku for trivial, Sonnet for standard, Opus for critical
- **Effort reduction**: Simplify task scope to reduce tokens
- **Parallelization**: Split independent work streams
- **Caching**: Reuse previous results
- **Model upgrade**: Use Opus only when quality requires it

### 4. **Quality Enforcement** (4-Band)
- **PROCEED** (≥90%): Route normally
- **ESCALATE_WARN** (85-90%): Route with warning, monitor closely
- **ESCALATE_FAIL** (<85%): Escalate to Senior/Lead Engineer
- **BLOCK** (repeated failures): Require human intervention

### 5. **DELEGATE** (Task Specification)
YAML/JSON file with:
- Task ID, role, model, effort
- Step-by-step plan
- Success criteria
- Token budget estimate
- Skill requirements
- Quality baseline

### 6. **Queue Management**
- Validates DELEGATE/HANDBACK schema
- Detects duplicates
- Manages file lifecycle: `incoming/` → `processing/` → `done/`
- Updates TODO.md
- Git commits & pushes

### 7. **Specialist Execution**
- Loads DELEGATE from queue
- Executes per plan
- Collects metrics (tokens, time, quality)
- Generates deliverables
- Tests & validates

### 8. **HANDBACK** (Task Result)
YAML/JSON file with:
- Status (success/partial/failed)
- Deliverables (files, code, docs)
- Tests (count, pass rate)
- Metrics (tokens, time, quality score, cost)
- Model assessment feedback
- Issues/blockers
- Recommendations

### 9. **Quality Engineer Review**
- Verifies deliverables
- Checks test coverage
- Validates quality score
- Approves or requests changes
- Moves to `done/`

### 10. **Feedback Loop** (5-Stage Cycle)
1. **Outcome Recording**: Task result → metrics database
2. **Quality Assessment**: Compare against baseline
3. **Feedback Collection**: Gather signals from execution
4. **Trend Analysis**: 7/30-day moving averages
5. **Routing Improvement**: Update smart router signals

### 11. **Continuous Improvement**
- Update smart router signals based on success rates
- Adjust cost-aware routing thresholds
- Refine quality baselines per task type
- Optimize model selection (Haiku/Sonnet/Opus)
- Reduce token spend via 5 opportunity types
- Improve overall team efficiency

---

## Data Flow Summary

```
User Request
    ↓
Orchestrator (parse, estimate, route)
    ↓
Smart Router (9-signal priority)
    ↓
Cost-Aware Router (lowest-cost agent)
    ↓
Quality Enforcer (4-band threshold)
    ↓
DELEGATE (task spec) → Queue
    ↓
Specialist Agent (execute)
    ↓
HANDBACK (result) → Queue
    ↓
Quality Engineer (review)
    ↓
Feedback Loop (metrics, trends, improvement)
    ↓
Continuous Improvement (routing, cost, quality)
    ↓
Deliverables to User
```

---

## Metrics Collected at Each Stage

| Stage | Metrics |
|-------|---------|
| **DELEGATE** | Estimated tokens, effort, complexity |
| **Execution** | Actual tokens used, time elapsed, quality signals |
| **HANDBACK** | Quality score (0-100), cost (USD), test pass rate |
| **Review** | Coverage %, regressions, approval status |
| **Feedback** | Trend (7/30-day MA), baseline comparison, recommendations |
| **Improvement** | Success rate, cost savings, quality trend |

---

## Quality Baselines by Task Type

| Task Type | Baseline | Enforcement |
|-----------|----------|-------------|
| **Security** | 95/100 | BLOCK if <95 |
| **Code/Test** | 90/100 | ESCALATE_FAIL if <85 |
| **Architecture** | 90/100 | ESCALATE_FAIL if <85 |
| **Docs/Perf** | 85/100 | ESCALATE_WARN if <85 |
| **Trivial** | 80/100 | PROCEED if ≥80 |

---

## Cost Optimization Opportunities

| Opportunity | Savings | Example |
|-------------|---------|---------|
| **Model Downgrade** | 67% | Haiku for trivial tasks |
| **Effort Reduction** | 20% | Simplify scope |
| **Parallelization** | 10% | Split independent work |
| **Caching** | 60% | Reuse previous results |
| **Model Upgrade** | 15-30% net | Use Opus only when needed |

**Target**: 8-12% total cost reduction while maintaining quality ≥90/100

---

## Example Task Flow

### Scenario: Add feature to orchestrator

```
1. User: "@orchestrator Add cost-aware routing to smart router"

2. Orchestrator:
   - Parses: Feature addition, medium complexity, ~2-3 hours
   - Estimates: ~5K tokens, Sonnet model, medium effort
   - Analyzes: Code change, needs test coverage, no security scope

3. Smart Router:
   - Signal 1: No explicit role → continue
   - Signal 2: Quality baseline 90/100 → check threshold
   - Signal 3: Not security → continue
   - Signal 4: Not cross-service → continue
   - Signal 5: Skill match: Engineer (routing) → Engineer
   - Signal 6: Code review needed → Lead Engineer for review
   - Signal 7: Medium complexity → Engineer can handle
   - Signal 8: Engineer success rate 92% → good choice
   - Signal 9: Route to Engineer

4. Cost-Aware Router:
   - Engineer cost: 1.0x (baseline)
   - Quality threshold: 90/100
   - Model: Sonnet (1.0x cost)
   - Effort: medium (5K tokens)
   - Decision: Route to Engineer with Sonnet

5. Quality Enforcer:
   - Baseline: 90/100 for code
   - Current: 90/100 (from trend)
   - Status: PROCEED (≥90%)

6. DELEGATE created:
   - Task ID: 2026-05-17-cost-aware-routing
   - Role: Engineer
   - Model: Sonnet
   - Effort: medium
   - Plan: [step-by-step]
   - Quality baseline: 90/100

7. Engineer executes:
   - Implements cost-aware router
   - Writes 15 tests
   - Achieves 95% coverage
   - Quality score: 92/100
   - Tokens used: 4,200
   - Time: 2.5 hours

8. HANDBACK created:
   - Status: success
   - Tests: 15 passed
   - Quality: 92/100
   - Cost: $0.42
   - Feedback: "Excellent implementation, consider caching optimization"

9. Quality Engineer:
   - Reviews code: ✓
   - Checks tests: ✓ (95% coverage)
   - Validates quality: ✓ (92/100)
   - Approves: ✓

10. Feedback Loop:
    - Outcome: success
    - Quality: 92/100 (vs 90/100 baseline) → +2%
    - Trend: Engineer success rate 92% → 93%
    - Cost: $0.42 (within budget)
    - Recommendation: "Continue routing similar tasks to Engineer"

11. Continuous Improvement:
    - Update Engineer success rate: 93%
    - Update cost-aware router: Sonnet effective for this task type
    - Update quality baseline: Consider raising to 91/100
    - Metrics: Task completed, quality improved, cost optimized
```

---

## Integration Points

- **OpenCode CLI**: `orchestrator-cli` command for task submission
- **GitHub**: Commits, PRs, Actions for CI/CD
- **Metrics**: Prometheus format for Grafana dashboards
- **Feedback**: Task outcome → quality assessment → routing improvement
- **Skills**: Auto-discovery and matching via skill registry
- **Configuration**: Unified `config/orchestration.yaml`

---

## Autonomy & Polling

**Orchestrator Autonomy:**
- ✅ Polls `artifacts/queue/incoming/` every 30-60 seconds
- ✅ Routes tasks continuously while queue has items
- ✅ Pauses when queue is empty (waits for new input)
- ✅ Collects metrics from HANDBACKs
- ✅ Feeds data to Model Engineer for optimization

**No Direct Execution:**
- ❌ Orchestrator does NOT execute work
- ❌ All work delegated to specialists
- ✅ Orchestrator only routes, coordinates, and improves

---

## Success Metrics (May 31st Deadline)

| Metric | Target | Current |
|--------|--------|---------|
| **Tests Passing** | ≥2,400 | 2,456 ✓ |
| **Code Coverage** | ≥90% | 99% ✓ |
| **Quality Score** | ≥90/100 | 90/100 ✓ |
| **Regressions** | 0 | 0 ✓ |
| **Cost Reduction** | 8-12% | On track |
| **Deployment** | Production ready | Phase B complete ✓ |

---

## Next Steps (Phase 4 Implementation)

1. **Historical Analysis**: Analyze past task outcomes, identify patterns
2. **Optimization Engine**: Automated recommendations for routing/cost/quality
3. **Cost Forecasting**: Predict token spend, budget alerts
4. **Dashboards**: Real-time metrics, trends, alerts
5. **Self-Improvement**: Feedback loops drive continuous optimization

**Timeline**: 14 days remaining (May 17-31)
**Token Budget**: ~50K remaining (from ~200K total)
**Quality Target**: Maintain ≥90/100, trending upward
