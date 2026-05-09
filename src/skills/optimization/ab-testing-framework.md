# A/B Testing Framework — Model & Effort Optimization

**Role Summary:** Automate A/B test design, allocation, monitoring, and analysis. Continuously run model/effort comparisons to optimize cost-quality tradeoff.

**Model:** claude-haiku-4-5 | **Effort:** high | **Cost Tier:** 1x | **Token Multiplier:** ~2x (test coordination + analysis)

---

## What This Skill DOES

- ✅ Design A/B test proposals (control vs. test arms)
- ✅ Allocate tasks to arms (randomized, stratified)
- ✅ Monitor test progress (sample size, power analysis)
- ✅ Detect early stopping conditions (winner clear, losers failing)
- ✅ Analyze results (statistical significance, confidence intervals)
- ✅ Recommend adoption/rejection of test arm
- ✅ Implement winning assignment (update model routing)
- ✅ Archive test results for historical analysis
- ✅ Run multiple concurrent tests

---

## Standard A/B Test Protocol

### Test Template

```yaml
---
test_id: "test_haiku-vs-sonnet_auth_2026-04-24"
hypothesis: "Sonnet medium-effort achieves 90+ quality at <1.5x cost of Haiku high-effort on auth tasks"
duration_days: 14
sample_size_per_arm: 5
priority: "medium"  # low/medium/high (affects sampling rate)

control_arm:
  name: "Haiku High (Current)"
  model: "claude-haiku-4-5"
  effort: "high"
  task_filter:
    domain: "auth"
    complexity: "medium"
    estimated_tokens: "15k-25k"
  historical_data:
    sample_size: 12
    avg_quality: 90
    avg_tokens: 18500
    avg_cost_usd: 0.13

test_arm:
  name: "Sonnet Medium (Proposed)"
  model: "claude-sonnet-4-6"
  effort: "medium"
  task_filter: (same as control)
  historical_data:
    sample_size: 3
    avg_quality: 94
    avg_tokens: 22500
    avg_cost_usd: 0.16

success_criteria:
  primary: "test_arm.cost_per_quality < control_arm.cost_per_quality"
  secondary: "test_arm.quality >= 92 AND test_arm.cost_per_quality <= control + 5%"
  quality_floor: 85  # Reject if either arm drops below this

metrics:
  track:
    - quality_score
    - tokens_in
    - tokens_out
    - cost_per_quality
    - escalation_rate
    - rework_required
    - duration_minutes
  
allocation_strategy: "alternating"  # control, test, control, test, ...
randomization: "deterministic_seed"  # reproducible if needed

stopping_rules:
  early_stop_if_winner_clear: true
    power_threshold: 0.95  # 95% confidence winner
  early_stop_if_loser_fails: true
    failure_threshold: 0.80  # If quality <80, stop
  sample_size_insufficient: 3  # Min 3 per arm to declare anything
```

### Test Phases

**Phase 1: Design (Orchestrator)**
```
Model Engineer proposes test (hypothesis, arms, success criteria)
  ↓
Orchestrator approves (or modifies) test spec
  ↓
Test enters "SCHEDULED" state
  ↓
Test waits for first matching task
```

**Phase 2: Allocation (Orchestrator)**
```
Task arrives (domain=auth, complexity=medium, tokens ~18K)
  ↓
Orchestrator checks: Is there an active A/B test for this task type?
  ↓
If yes: Allocate to next arm (round-robin: control, test, control, ...)
  ↓
Engineer delegates with model from assigned arm
  ↓
Metrics recorded with test_id tag
```

**Phase 3: Monitoring (TokenAdvisor)**
```
Each day: Check test progress
  ↓
Sample sizes:
  Control: 0, 1, 2, 3... (growing)
  Test: 0, 1, 2, 3... (growing)
  ↓
Power analysis: Are we 95% confident about winner yet?
  ↓
If yes, or if sample_size ≥ n_target: Declare result
  ↓
If no, and duration < max_days: Continue test
```

**Phase 4: Analysis (Model Engineer)**
```
Test reaches n=5 per arm (or max_duration exceeded)
  ↓
Analyze results:
  Control: quality=90, cost_per_quality=$0.00144
  Test:    quality=93, cost_per_quality=$0.00159
  ↓
Statistical test: t-test on quality, cost comparison
  ↓
Decision:
  quality similar (within ±3) but cost_per_quality worse
  → Control wins (Haiku is still better value)
  ↓
Recommendation: Keep Haiku for medium auth tasks
  ↓
Archive results: save to ~/.claude/metrics/tests/
```

**Phase 5: Action (Orchestrator)**
```
Test declared complete with winner
  ↓
If Test Arm Won:
  → Update model routing: use test model for this task type
  → Log decision: "Upgraded medium-auth tasks to Sonnet medium"
  ↓
If Control Won (or inconclusive):
  → No change to routing
  → Log decision: "Haiku high-effort remains optimal for auth"
  ↓
Archive test report:
  - hypothesis
  - results per arm
  - winner + confidence
  - recommendations
```

---

## Test Design Examples

### Example 1: Model Comparison (Cheap vs. Balanced)

```yaml
test_id: "haiku-vs-sonnet-lowcomplexity-2026-05"
hypothesis: "Haiku can handle low-complexity tasks as well as Sonnet, saving cost"

control_arm:
  model: "haiku-4-5"
  effort: "high"
  historical_baseline: { quality: 88, cost: $0.12 }

test_arm:
  model: "sonnet-4-6"
  effort: "low"  # Lower effort, but model is smarter
  historical_baseline: { quality: 92, cost: $0.14 }

success_criteria:
  primary: "test_arm.quality >= 90 AND cost_per_quality < control"
  # i.e., if Sonnet low-effort achieves 90+ quality at <cost, switch

expected_outcome: "Control wins (Haiku is cheaper)"
```

### Example 2: Effort Optimization (Max vs. Medium)

```yaml
test_id: "effort-max-vs-med-complex-api-2026-05"
hypothesis: "Medium effort is sufficient for complex API tasks; max effort is overkill"

control_arm:
  model: "sonnet-4-6"
  effort: "max"  # High effort, high thinking
  historical_baseline: { quality: 95, cost: $0.22 }

test_arm:
  model: "sonnet-4-6"
  effort: "medium"
  historical_baseline: { quality: 93, cost: $0.15 }  (extrapolated)

success_criteria:
  primary: "test_arm.quality >= 93 AND cost < 70% of control"
  # i.e., if medium effort achieves 93 quality at <70% cost, downgrade

expected_outcome: "Test wins (medium effort sufficient, saves 30% cost)"
```

### Example 3: New Model Evaluation

```yaml
test_id: "haiku-4.6-vs-haiku-4.5-2026-06"
hypothesis: "New Haiku 4.6 model achieves better quality at same cost"

control_arm:
  model: "haiku-4-5"
  effort: "high"
  historical_baseline: { quality: 90, cost: $0.13 }

test_arm:
  model: "haiku-4-6"  # New model (same 1x cost tier)
  effort: "high"
  historical_baseline: (unknown, estimated: quality 92, cost $0.13)

success_criteria:
  primary: "test_arm.quality >= 91 AND cost_per_quality <= control"
  # i.e., if Haiku 4.6 is better quality at same cost, upgrade

expected_outcome: "Test wins (upgrade all Haiku roles to 4.6)"
```

---

## Randomization & Allocation

### Simple Alternating (No Randomization)

```
Task 1 → Control (Haiku)
Task 2 → Test (Sonnet)
Task 3 → Control (Haiku)
Task 4 → Test (Sonnet)
...
```

**Pros:** Simple, deterministic
**Cons:** Biased if task difficulty varies over time (morning tasks harder than afternoon)

### Stratified Randomization (By Task Type)

```
For auth tasks, allocate:
  50% → Control
  50% → Test
  (respects task type boundaries)

For API tasks, allocate:
  50% → Control (same models)
  50% → Test

Ensures balanced distribution across task types
```

**Pros:** Balanced per task type, controls for variation
**Cons:** Requires task type classification

### Probabilistic (With Seed)

```go
// Deterministic randomization using task hash
seed := hash(test_id + task_id)
rand := seededRandom(seed)

if rand.Float() < 0.5 {
  allocate_to_control()
} else {
  allocate_to_test()
}
```

**Pros:** True randomization, reproducible
**Cons:** Requires careful seed management

---

## Stopping Rules

### Powered Sample Size

For normal distributions, required sample size:

```
n = 2 × (z_alpha + z_beta)^2 × (σ_control^2 + σ_test^2) / (μ_test - μ_control)^2

Example: Quality comparison
  σ ≈ 3 (std dev of quality scores)
  μ_test - μ_control = 2 (we want to detect 2-point difference)
  z_alpha = 1.96 (95% confidence)
  z_beta = 0.84 (80% power)
  
  n = 2 × (1.96 + 0.84)^2 × (9 + 9) / (4)
    = 2 × 7.8 × 18 / 4
    = 70.2
  
  → Need n=70 per arm (impractical)
  → Simplify: use n=5 per arm (what we do), accept lower power
```

### Early Stopping (Sequential Testing)

**Stop if winner is clear:**
```
After n=3 per arm:
  Control quality: 90 ± 2 (88-92)
  Test quality: 86 ± 2 (84-88)
  No overlap → Clear loser (Test)
  → Stop early, declare Control winner
  → Save resources (avoid running n=2 more)
```

**Stop if loser is failing:**
```
Control: n=5, quality=92 (passing)
Test: n=5, quality=78 (failing, <80 threshold)
  → Test arm is below quality floor
  → Stop immediately, declare Control winner
```

---

## Analysis Methods

### T-Test (Quality Comparison)

```python
import scipy.stats

control_quality = [92, 91, 90, 89, 92]  # n=5
test_quality = [88, 87, 89, 86, 87]     # n=5

# Two-sample t-test
t_stat, p_value = scipy.stats.ttest_ind(control_quality, test_quality)

# Results
if p_value < 0.05:
  print(f"Significant difference (p={p_value:.3f})")
  if mean(control_quality) > mean(test_quality):
    print("Control wins")
  else:
    print("Test wins")
else:
  print(f"No significant difference (p={p_value:.3f})")
  print("Cannot declare winner, need more data")
```

### Effect Size (Cohen's d)

```python
def cohens_d(x, y):
  nx, ny = len(x), len(y)
  dof = nx + ny - 2
  return (mean(x) - mean(y)) / sqrt(((nx-1)*var(x) + (ny-1)*var(y)) / dof)

d = cohens_d(control_quality, test_quality)

if abs(d) < 0.2:
  interpretation = "negligible"
elif abs(d) < 0.5:
  interpretation = "small"
elif abs(d) < 0.8:
  interpretation = "medium"
else:
  interpretation = f"large ({d:.2f})"

print(f"Effect size: {interpretation}")
```

---

## Cost-Benefit Analysis Post-Test

**Test: Haiku High vs. Sonnet Medium on Auth Tasks**

```
RESULTS:
  Control (Haiku high):
    Quality: 90 ± 2
    Cost: $0.13/task
    Tokens: 18.5K ± 2K
    
  Test (Sonnet med):
    Quality: 93 ± 2
    Cost: $0.16/task
    Tokens: 22K ± 2K

ANALYSIS:
  Difference: +3 quality points, +$0.03 cost
  Cost per quality point: Haiku $0.00144, Sonnet $0.00172
  Sonnet is 19% more expensive per quality point
  
  Quality gap: 3 points (3.3% of 100-point scale)
  Cost gap: $0.03 (23% more expensive)
  
DECISION:
  Primary success criterion: test_arm.cost_per_quality < control ✗
  Sonnet medium-effort does NOT meet success criterion
  
  Recommendation: KEEP CONTROL (Haiku high-effort)
  
  BUT: IF quality target is "95+", then upgrade to Sonnet
       (93 is below 95; may need Opus or Haiku + more effort)

FOLLOW-UP TESTS TO RUN:
  1. Sonnet LOW-effort (might be same quality as high, cheaper)
  2. Haiku MAX-effort (might achieve 93+ quality without upgrade)
  3. New Haiku 4.6 (may be better than 4.5 at same cost)
```

---

## Test Dashboard Metrics

```
╔═════════════════════════════════════════════════════╗
║ ACTIVE A/B TESTS (Week of 2026-04-28)              ║
╠═════════════════════════════════════════════════════╣
║ Test ID              Status    Control  Test   Sig  ║
║ ─────────────────────────────────────────────────── ║
║ haiku-vs-sonnet      In-Flight  n=2      n=2   -   ║
║ (auth, medium)       Day 4/14   q=90±2   q=93±2    ║
║                      Progress: ████░░░░░░░░░░░░░   ║
║                                                     ║
║ effort-max-vs-med    In-Flight  n=1      n=1   -   ║
║ (api, complex)       Day 2/7    q=95     q=94     ║
║                      Progress: ██░░░░░░░░░░░░░░░  ║
║                                                     ║
║ haiku-4.6-eval       Scheduled  -        -     -   ║
║ (all domains)        Start: 2026-05-01            ║
║                                                     ║
╚═════════════════════════════════════════════════════╝

Legend:
  n=X: sample size
  q: average quality
  Sig: statistical significance (✓ for p<0.05)
```

---

## Skill Validation

This skill is correct if it can:
1. Design A/B test proposals with control/test arms
2. Generate test spec YAML (hypothesis, arms, success criteria)
3. Allocate tasks to arms (round-robin, stratified, random)
4. Monitor test progress (sample size, power analysis)
5. Detect early stopping conditions (clear winner, loser below threshold)
6. Run statistical tests (t-test, effect size, confidence intervals)
7. Analyze cost-quality tradeoffs (cost_per_quality comparison)
8. Recommend test arm adoption or rejection
9. Archive test results with full report
10. Support multiple concurrent tests (isolation)
