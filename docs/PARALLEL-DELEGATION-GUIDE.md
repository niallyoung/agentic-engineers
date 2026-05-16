# Parallel Delegation Guide

**Comprehensive guide to parallel task execution in the agentic-engineers framework.**

> **Phase 2 Feature:** Enables agents to decompose work into independent child tasks that execute concurrently, reducing Orchestrator bottleneck by 60-70% and enabling true parallel execution.

---

## Table of Contents

1. [What is Parallel Delegation?](#1-what-is-parallel-delegation)
2. [When to Use Parallel Delegation](#2-when-to-use-parallel-delegation)
3. [How It Works](#3-how-it-works)
4. [Creating Sub-Tasks](#4-creating-sub-tasks)
5. [Result Aggregation](#5-result-aggregation)
6. [Constraints & Limits](#6-constraints--limits)
7. [Failure Modes](#7-failure-modes)
8. [Best Practices](#8-best-practices)
9. [Real-World Examples](#9-real-world-examples)
10. [Troubleshooting](#10-troubleshooting)
11. [Performance Considerations](#11-performance-considerations)

---

## 1. What is Parallel Delegation?

Parallel delegation is a Phase 2 feature that allows any agent to break its assigned task into independent child tasks and queue them directly to the work queue. The Orchestrator automatically detects parent-child relationships and waits for all children to complete before aggregating results.

### Key Concepts

**Parent Task**
- Original task assigned to an agent
- Can create 1-10 child tasks
- Waits for all children to complete
- Aggregates results into final HANDBACK

**Child Task**
- Sub-task created by parent agent
- Linked to parent via `parent_task_id`
- Executes independently in parallel with siblings
- Returns HANDBACK with results

**Task Tier**
- Depth in the task hierarchy
- Tier 0 = root task (no parent)
- Tier 1 = child of root
- Tier 2 = grandchild
- Maximum depth: Tier 5

**Result Aggregation**
- Orchestrator waits for all children (60-minute timeout)
- Combines quality scores (effort-weighted average)
- Sums tokens and costs
- Writes parent HANDBACK with `children_results`

### Benefits

✅ **Decentralized task creation** — agents create sub-tasks without Orchestrator routing
✅ **Reduced bottleneck** — Orchestrator load reduced by 60-70%
✅ **Parallel execution** — children run concurrently (wall-clock time savings)
✅ **Automatic aggregation** — quality, tokens, costs combined automatically
✅ **Backward compatible** — root tasks (no parent) work unchanged
✅ **Cycle prevention** — validator prevents circular dependencies
✅ **Flexible depth** — up to 5 levels of nesting

### Limitations

❌ **Max 10 children per parent** — more = coordination overhead
❌ **Max 5 tiers deep** — prevents runaway hierarchies
❌ **Max 100 tasks per session** — rate limiting
❌ **60-minute timeout** — children must complete within this window
❌ **No cross-task dependencies** — children must be independent

---

## 2. When to Use Parallel Delegation

Use parallel delegation when:

### ✅ Good Use Cases

**Multi-service analysis**
- Analyze 3+ microservices in parallel
- Each service gets an Engineer
- Results aggregated into consolidated report
- Example: Security audit of 4 payment services

**Batch processing**
- Migrate 10 databases in parallel
- Analyze 5 code repositories
- Test 8 API endpoints
- Each batch item gets independent task

**Feature implementation across services**
- Implement feature in 4+ backend services
- Each service gets an Engineer
- All work in parallel
- Results aggregated for deployment

**Security audits**
- Audit multiple repos/services
- Each gets a Security Engineer
- Results combined into threat assessment
- Parallel execution saves days

**Data processing**
- Process 6+ data files in parallel
- Transform, validate, aggregate
- Each file gets independent task
- Results combined into final output

### ❌ Poor Use Cases

**Sequential work**
- Task A must complete before B starts
- Use sequential delegation instead
- Parallel adds overhead without benefit

**Single large task**
- One task that cannot be decomposed
- Use direct delegation (no children)
- Parallel overhead not justified

**Tightly coupled work**
- Children depend on each other
- Use sequential delegation
- Parallel introduces coordination complexity

**Very small tasks**
- Each child takes <5 minutes
- Overhead of parallel coordination exceeds benefit
- Use sequential delegation

**Real-time constraints**
- Must complete in <5 minutes
- Parallel coordination adds latency
- Use sequential delegation

---

## 3. How It Works

### Architecture

```
┌─────────────────────────────────────────────────────┐
│  Parent Task (Senior Engineer)                      │
│  "Analyze all 4 payment services"                   │
│                                                     │
│  1. Reads DELEGATE block                            │
│  2. Creates 4 child tasks via queue-management      │
│  3. Queues children to incoming/                    │
│  4. Returns HANDBACK with children_created          │
└─────────────────────────────────────────────────────┘
           │
           ├─► Child 1: Stripe (Engineer)
           ├─► Child 2: PayPal (Engineer)
           ├─► Child 3: Crypto (Engineer)
           └─► Child 4: Square (Engineer)
                │         │         │         │
                ├─────────┼─────────┼─────────┤
                │ (all run in parallel)
                │
           ┌────┴─────────────────┐
           │ Orchestrator detects │
           │ parent-child link    │
           │ (has_children=True)  │
           └────────┬─────────────┘
                    │
           ┌────────▼──────────────┐
           │ Waits for all 4       │
           │ children to complete  │
           │ (60-min timeout)      │
           └────────┬──────────────┘
                    │
           ┌────────▼──────────────┐
           │ Aggregates results:   │
           │ - Quality (weighted)  │
           │ - Tokens (sum)        │
           │ - Cost (sum)          │
           └────────┬──────────────┘
                    │
           ┌────────▼──────────────┐
           │ Writes parent HANDBACK│
           │ with children_results │
           └───────────────────────┘
```

### Workflow Steps

1. **Orchestrator routes parent task** to appropriate agent (e.g., Senior Engineer)
2. **Agent reads DELEGATE** with scope, plan, context
3. **Agent decomposes work** — identifies independent sub-tasks
4. **Agent creates children** using `queue-management` skill
   - Each child gets unique task_id
   - Each child links to parent via `parent_task_id`
   - Each child has auto-calculated `task_tier`
5. **Agent returns HANDBACK** with `children_created` list
6. **Orchestrator detects children** via `has_children(parent_task_id)`
7. **Orchestrator waits** for all children (polls done/ every 1 second, timeout 60 min)
8. **Orchestrator aggregates** results:
   - Quality: effort-weighted average
   - Tokens: sum of all children
   - Cost: sum of all children
9. **Orchestrator writes parent HANDBACK** with `children_results` populated
10. **Parent task moves to done/**

### Timeline Example (4 parallel children)

```
Time  Parent Task         Child 1         Child 2         Child 3         Child 4
────  ─────────────────   ─────────────   ─────────────   ─────────────   ─────────────
 0:00 ├─ Receives DELEGATE
 0:05 ├─ Creates 4 children
 0:10 ├─ Returns HANDBACK
      │  (children_created=[...])
      │
 0:10 │                   ├─ Assigned      ├─ Assigned      ├─ Assigned      ├─ Assigned
 0:15 │                   ├─ Starts work   ├─ Starts work   ├─ Starts work   ├─ Starts work
      │
 0:30 │ ├─ Detects children
 0:30 │ ├─ Starts waiting...
      │
 1:00 │                   ├─ Completes    ├─ Completes    ├─ Completes    ├─ Completes
 1:05 │ ├─ All children done
 1:05 │ ├─ Aggregates results
 1:10 │ ├─ Writes parent HANDBACK
 1:10 │ └─ Moves to done/

Wall-clock: 1 hour 10 minutes (vs. 4+ hours if sequential)
```

---

## 4. Creating Sub-Tasks

### Using queue-management Skill

```python
from skills.queue_management.scripts.queue_ops import QueueOperations

# Initialize queue operations
ops = QueueOperations(queue_dir="/path/to/queue", session_id="my-session")

# Create parent task (done by Orchestrator)
ops.create_delegate(
    task_id="payment-analysis-001",
    role="senior_engineer",
    scope="Analyze all payment services for security risks...",
    plan=["Create sub-tasks", "Aggregate results", "Write report"],
    context="Security audit of payment infrastructure",
)

# Agent creates child tasks
for service in ["stripe", "paypal", "crypto", "square"]:
    ops.create_delegate(
        task_id=f"payment-analysis-{service}-001",
        role="engineer",
        model="claude-haiku-4-5",
        effort="high",
        scope=f"Analyze {service} payment service for security risks...",
        plan=[
            f"Review {service} integration code",
            "Check dependency versions for CVEs",
            "Analyze webhook security",
            "Document findings"
        ],
        context=f"Parent task: payment-analysis-001",
        parent_task_id="payment-analysis-001",  # Link to parent
        # task_tier is auto-calculated
    )
```

### DELEGATE Block Format (Sub-Task)

```yaml
---
handoff_type: DELEGATE
task_id: payment-analysis-stripe-001
role: engineer
model: claude-haiku-4-5
effort: high
scope: >
  Analyze Stripe payment service for security risks, performance bottlenecks,
  and dependency vulnerabilities. Focus on payment processing, webhook handling,
  and error recovery paths.
context:
  - Parent task: payment-analysis-001
  - Repo: stripe-integration/
  - Focus areas: Payment processing, webhook handling, error recovery
  - Related: docs/stripe-integration-guide.md
plan:
  1. Review payment processing code (src/payments/stripe.go)
  2. Check webhook validation and signature verification
  3. Analyze error handling and recovery logic
  4. Check dependency versions against CVE database
  5. Document findings in security report
success_criteria:
  - Security report completed
  - All CVEs documented with severity
  - Recommendations provided for each finding
  - Code review checklist completed
parent_task_id: payment-analysis-001        # NEW: Link to parent
task_tier: 1                                # NEW: Auto-calculated (parent_tier + 1)
---
```

### Field Reference

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `parent_task_id` | string | Yes (for sub-tasks) | Task ID of parent; must exist in queue |
| `task_tier` | integer | No | Auto-calculated; do not set manually |

### Validation Rules

**Parent existence:**
- Parent must exist in `incoming/`, `processing/`, or `done/`
- Validator checks all queue states
- Error: `ValueError: parent_task_id not found`

**No self-reference:**
- `task_id != parent_task_id`
- Error: `ValueError: cannot link to self`

**No cycles:**
- Parent must not be descendant of child
- Validator checks ancestor graph
- Error: `ValueError: cycle detected`

**Scope overlap:**
- Child scope must overlap parent scope by ≥20% (word overlap)
- Ensures child is actually sub-task of parent
- Error: `ValueError: scope overlap < 20%`

**Tier depth:**
- `task_tier ≤ 5` (auto-calculated)
- Do not manually set `task_tier`
- Error: `ValueError: task_tier exceeds maximum (5)`

---

## 5. Result Aggregation

### Aggregation Process

When all children complete, the Orchestrator:

1. **Collects all child HANDBACKs** from done/
2. **Validates each HANDBACK** (status, quality, tokens)
3. **Calculates weighted quality** using effort levels
4. **Sums tokens and costs**
5. **Writes parent HANDBACK** with `children_results` populated

### Quality Score Calculation

Child quality scores are **effort-weighted averages**:

```
weighted_quality = Σ(quality_i × weight_i) / Σ(weight_i)
```

| Effort | Weight | Example |
|--------|--------|---------|
| high   | 3×     | 3 children × 3 = 9 weight |
| medium | 2×     | 2 children × 2 = 4 weight |
| low    | 1×     | 1 child × 1 = 1 weight |

**Example 1: Three high-effort children**
```
Children: [92, 88, 85] with efforts [high, high, high]
Weights: [3, 3, 3]
Numerator: (92×3) + (88×3) + (85×3) = 276 + 264 + 255 = 795
Denominator: 3 + 3 + 3 = 9
Result: 795 / 9 = 88.33
```

**Example 2: Mixed effort levels**
```
Children: [92, 88, 85] with efforts [high, high, medium]
Weights: [3, 3, 2]
Numerator: (92×3) + (88×3) + (85×2) = 276 + 264 + 170 = 710
Denominator: 3 + 3 + 2 = 8
Result: 710 / 8 = 88.75
```

**Example 3: With failed child (partial)**
```
Children: [92, 88, 0] with efforts [high, high, high]
Status: [complete, complete, failed]
Only aggregate successful: [92, 88]
Numerator: (92×3) + (88×3) = 276 + 264 = 540
Denominator: 3 + 3 = 6
Result: 540 / 6 = 90.0
```

### Token Aggregation

Tokens are **summed** (not averaged):

```
total_tokens = Σ(tokens_in_i + tokens_out_i)
```

**Example:**
```
Child 1: tokens_in=1200, tokens_out=800 → total=2000
Child 2: tokens_in=1100, tokens_out=900 → total=2000
Child 3: tokens_in=1300, tokens_out=700 → total=2000
Parent total: 2000 + 2000 + 2000 = 6000 tokens
```

### Cost Aggregation

Costs are **summed** (not averaged):

```
total_cost = Σ(cost_i)
```

**Example:**
```
Child 1: 2000 tokens × $0.0005/token = $1.00
Child 2: 2000 tokens × $0.0005/token = $1.00
Child 3: 2000 tokens × $0.0005/token = $1.00
Parent total: $1.00 + $1.00 + $1.00 = $3.00
```

### Parent HANDBACK Structure

```yaml
---
handoff_type: HANDBACK
task_id: payment-analysis-001
status: complete
deliverables:
  - Report: payment-analysis-report.md
  - Summary: 6 total risks identified, 9 mitigations recommended
children_created:
  - payment-analysis-stripe-001
  - payment-analysis-paypal-001
  - payment-analysis-crypto-001
  - payment-analysis-square-001
children_results:
  payment-analysis-stripe-001:
    status: complete
    output:
      risks: 2
      mitigations: 3
      critical_findings:
        - "Webhook validation missing in error path"
        - "Rate limiting insufficient for DDoS protection"
    quality: 92
  payment-analysis-paypal-001:
    status: complete
    output:
      risks: 1
      mitigations: 2
      critical_findings:
        - "Dependency outdated: paypal-sdk@2.1.0 (CVE-2025-1234)"
    quality: 88
  payment-analysis-crypto-001:
    status: complete
    output:
      risks: 3
      mitigations: 4
      critical_findings:
        - "Key rotation not implemented"
        - "Entropy source weak (Math.random)"
        - "No rate limiting on API calls"
    quality: 85
  payment-analysis-square-001:
    status: complete
    output:
      risks: 0
      mitigations: 0
      critical_findings: []
    quality: 95
children_failed: []
result_aggregation_status: all_complete
tokens_in: 4600
tokens_out: 3400
model: claude-sonnet-4-6
effort: high
duration_minutes: 65
escalations: 0
notes: "All four services analyzed in parallel. Stripe and Crypto require immediate attention. Square is well-secured. Recommend prioritized remediation plan."
---
```

---

## 6. Constraints & Limits

### Hard Limits

| Constraint | Value | Error |
|-----------|-------|-------|
| Max depth (task_tier) | 5 | `ValueError: task_tier X exceeds maximum (5)` |
| Max children per parent | 10 | `RuntimeError: parent already has N children (max 10)` |
| Max tasks per session/hour | 100 | `RuntimeError: Rate limit exceeded` |
| Max task_id length | 64 chars | `ValueError: task_id too long` |
| Max scope length | 1000 chars | `ValueError: scope too long` |

### Soft Limits (Best Practices)

| Constraint | Recommended | Reason |
|-----------|------------|--------|
| Children per parent | 3-8 | More = coordination overhead |
| Max depth | 2-3 | Deeper = harder to debug |
| Task duration | 1-2 hours | Longer = higher timeout risk |
| Scope overlap | ≥20% | Ensures child is sub-task |

### Depth Visualization

```
Tier 0: master-task-001                          ← root (no parent)
Tier 1: ├─ subtask-auth-001                      ← child
Tier 1: ├─ subtask-billing-001                   ← child
Tier 1: └─ subtask-notifications-001             ← child
Tier 2:    ├─ subtask-auth-oauth-001             ← grandchild
Tier 2:    └─ subtask-auth-mfa-001               ← grandchild
Tier 3:       └─ subtask-auth-oauth-google-001   ← great-grandchild
Tier 4:          └─ subtask-auth-oauth-google-impl-001
Tier 5:             └─ subtask-auth-oauth-google-impl-test-001  ← max depth
```

---

## 7. Failure Modes

### Partial (Default)

Failed children are recorded; successful children are aggregated normally.

```yaml
result_aggregation_status: partial
children_failed: [payment-analysis-paypal-001]
children_results:
  payment-analysis-stripe-001:
    status: complete
    quality: 92
  payment-analysis-paypal-001:
    status: failed
    quality: 0
  payment-analysis-crypto-001:
    status: complete
    quality: 85
```

**Behavior:**
- Parent task continues
- Quality score calculated from successful children only
- Failed children listed in `children_failed`
- Caller (Orchestrator) decides whether to fail parent

**Quality calculation:**
```
Only aggregate successful: [92, 85]
Result: (92×3 + 85×3) / (3+3) = 88.5
```

### All-or-Nothing

If any child fails, aggregation fails.

```yaml
result_aggregation_status: partial
children_failed: [payment-analysis-paypal-001]
# Caller decides whether to fail parent
```

**Behavior:**
- Caller receives aggregation with `children_failed` populated
- Caller decides: continue parent or fail parent
- Useful for critical work where all children must succeed

### Timeout

Children don't complete within 60-minute window.

```yaml
result_aggregation_status: timed_out
children_results:
  payment-analysis-stripe-001:
    status: complete
    quality: 92
  payment-analysis-paypal-001:
    status: null  # Still in processing/
  payment-analysis-crypto-001:
    status: complete
    quality: 85
```

**Behavior:**
- Partial results included (completed children)
- Missing children not yet complete
- Caller decides: wait longer, fail, or continue with partial

### Handling Failures

**In parent HANDBACK:**
```yaml
children_failed: [payment-analysis-paypal-001]
notes: "PayPal analysis failed due to rate limiting. Recommend retry in 1 hour."
```

**In Orchestrator:**
```python
if result["result_aggregation_status"] == "partial":
    if result["children_failed"]:
        # Log failed children
        logger.warning(f"Failed children: {result['children_failed']}")
        # Decide: retry, escalate, or continue
```

---

## 8. Best Practices

### ✅ DO

**Use for naturally decomposable work**
- Multiple services, repos, domains
- Each child is independent
- Results combine meaningfully

**Limit children to 3-10 per parent**
- 3-5: Ideal (low coordination overhead)
- 6-10: Acceptable (moderate overhead)
- >10: Rejected by validator

**Set realistic timeouts**
- Default: 60 minutes
- Adjust if children need more time
- Monitor actual completion times

**Use effort levels appropriately**
- high: Complex analysis, deep reasoning
- medium: Standard implementation
- low: Simple, straightforward work
- Quality scores weighted by effort

**Monitor token consumption**
- Parallel = more concurrent usage
- Sum tokens across all children
- May exceed sequential approach
- Cost is usually same (tokens same)

**Document parent-child relationship**
- Include parent task_id in child context
- Explain why decomposition makes sense
- Help future readers understand structure

### ❌ DON'T

**Create circular dependencies**
- Validator prevents this
- Parent cannot be descendant of child
- Error: `ValueError: cycle detected`

**Go deeper than tier 5**
- Max depth: 5 levels
- Validator prevents this
- Error: `ValueError: task_tier exceeds maximum`

**Create >10 children per parent**
- Max children: 10
- Validator prevents this
- Error: `RuntimeError: already has N children (max 10)`

**Use for sequential work**
- Children must be independent
- If A depends on B, use sequential
- Parallel adds overhead without benefit

**Ignore failed children**
- Check `children_failed` in HANDBACK
- Decide: retry, escalate, or continue
- Don't silently ignore failures

**Manually set task_tier**
- Auto-calculated: `parent_tier + 1`
- Manual override raises error
- Let system calculate

**Create tasks with overlapping scope**
- Child scope must overlap parent by ≥20%
- Ensures child is actually sub-task
- Validator checks word overlap

---

## 9. Real-World Examples

### Example 1: Security Audit (4 Services)

**Scenario:** Audit security in 4 microservices (Stripe, PayPal, Crypto, Square).

**Sequential approach (old):**
- Orchestrator → Security Engineer (4 hours)
- Wall-clock: 4 hours
- Cost: $0.30

**Parallel approach (new):**

**Step 1: Orchestrator creates parent task**
```yaml
---
handoff_type: DELEGATE
task_id: security-audit-payments-001
role: senior_engineer
model: claude-sonnet-4-6
effort: high
scope: "Audit security in all 4 payment services..."
plan:
  1. Create sub-tasks for each service
  2. Wait for all to complete
  3. Aggregate findings into consolidated report
---
```

**Step 2: Senior Engineer creates 4 children**
```python
for service in ["stripe", "paypal", "crypto", "square"]:
    ops.create_delegate(
        task_id=f"security-audit-{service}-001",
        role="security_engineer",
        scope=f"Audit {service} payment service for security risks...",
        parent_task_id="security-audit-payments-001",
    )
```

**Step 3: Orchestrator routes 4 children to 4 Security Engineers**
- Security Engineer 1 → Stripe (1 hour)
- Security Engineer 2 → PayPal (1 hour)
- Security Engineer 3 → Crypto (1 hour)
- Security Engineer 4 → Square (1 hour)

**Step 4: All run in parallel**
- Wall-clock: 1 hour (vs. 4 hours sequential)
- Cost: $0.30 (same)
- **Benefit: 3 hours saved (75% faster)**

**Step 5: Orchestrator aggregates results**
```yaml
children_created:
  - security-audit-stripe-001
  - security-audit-paypal-001
  - security-audit-crypto-001
  - security-audit-square-001
children_results:
  security-audit-stripe-001:
    status: complete
    quality: 92
  security-audit-paypal-001:
    status: complete
    quality: 88
  security-audit-crypto-001:
    status: complete
    quality: 85
  security-audit-square-001:
    status: complete
    quality: 95
result_aggregation_status: all_complete
aggregate_quality: 90.0
```

### Example 2: Database Migration (10 Databases)

**Scenario:** Migrate 10 databases to new schema.

**Sequential approach:**
- 10 databases × 1 hour each = 10 hours
- Cost: $0.50

**Parallel approach:**

**Step 1: Create parent task**
```yaml
scope: "Migrate all 10 databases to new schema..."
plan:
  1. Create sub-task for each database
  2. Wait for all to complete
  3. Verify all migrations successful
```

**Step 2: Create 10 children**
```python
for db_id in range(1, 11):
    ops.create_delegate(
        task_id=f"db-migration-{db_id:02d}-001",
        role="engineer",
        scope=f"Migrate database {db_id} to new schema...",
        parent_task_id="db-migration-master-001",
    )
```

**Step 3: All run in parallel**
- Wall-clock: 1 hour (vs. 10 hours sequential)
- Cost: $0.50 (same)
- **Benefit: 9 hours saved (90% faster)**

### Example 3: Code Review (5 Repositories)

**Scenario:** Review code changes in 5 repositories.

**Sequential approach:**
- 5 repos × 2 hours each = 10 hours
- Cost: $0.45

**Parallel approach:**

**Step 1: Create parent task**
```yaml
scope: "Review code changes in all 5 repositories..."
plan:
  1. Create sub-task for each repository
  2. Wait for all reviews to complete
  3. Aggregate findings
```

**Step 2: Create 5 children**
```python
for repo in ["auth", "billing", "notifications", "api", "worker"]:
    ops.create_delegate(
        task_id=f"code-review-{repo}-001",
        role="lead_engineer",
        scope=f"Review code changes in {repo} repository...",
        parent_task_id="code-review-master-001",
    )
```

**Step 3: All run in parallel**
- Wall-clock: 2 hours (vs. 10 hours sequential)
- Cost: $0.45 (same)
- **Benefit: 8 hours saved (80% faster)**

---

## 10. Troubleshooting

### Child Task Stuck in "processing"

**Symptom:** Child task in `artifacts/queue/processing/` for >2 hours, no progress.

**Diagnosis:**
1. Check Orchestrator logs for errors
2. Verify parent task completed
3. Check if queue is full (>100 tasks)
4. Verify child task is valid YAML

**Solution:**
```bash
# Check queue status
ls -la artifacts/queue/processing/ | wc -l

# Check Orchestrator logs
tail -100 logs/orchestrator.log | grep "payment-analysis-stripe-001"

# If stuck >2 hours, escalate to Principal Engineer
```

### Aggregation Quality Score Seems Wrong

**Symptom:** Parent quality score doesn't match expected value.

**Diagnosis:**
1. Verify effort levels in child HANDBACKs
2. Check quality scores of each child
3. Manually calculate weighted average

**Solution:**
```python
# Manual calculation
children = [
    {"quality": 92, "effort": "high"},
    {"quality": 88, "effort": "high"},
    {"quality": 85, "effort": "medium"},
]

weights = {"high": 3, "medium": 2, "low": 1}
numerator = sum(c["quality"] * weights[c["effort"]] for c in children)
denominator = sum(weights[c["effort"]] for c in children)
expected = numerator / denominator

print(f"Expected quality: {expected}")
# If actual != expected, check effort levels
```

### Parent Task Timed Out Waiting for Children

**Symptom:** `result_aggregation_status = timed_out`, some children still in processing/.

**Diagnosis:**
1. Check how long children have been running
2. Verify children are making progress
3. Check if children are blocked

**Solution:**
```bash
# Check child task status
cat artifacts/queue/processing/payment-analysis-paypal-001.yaml

# Check if child is blocked
grep "status: blocked" artifacts/queue/processing/*.yaml

# Increase timeout (if children need more time)
# In Orchestrator config: timeout_minutes=120
```

### Can I Create Sub-Tasks of Sub-Tasks?

**Question:** Can a child create its own children?

**Answer:** Yes, up to tier 5 (5 levels deep).

```yaml
Tier 0: master-task-001
Tier 1: ├─ subtask-001
Tier 2:    └─ subsubtask-001
Tier 3:       └─ subsubsubtask-001
Tier 4:          └─ subsubsubsubtask-001
Tier 5:             └─ subsubsubsubsubtask-001  ← max depth
```

**Limitation:** Tier 5 cannot create children (max depth reached).

### What If 2 of 3 Children Fail?

**Scenario:** 3 children created; 1 fails, 2 succeed.

**Result:**
```yaml
result_aggregation_status: partial
children_failed: [payment-analysis-paypal-001]
children_results:
  payment-analysis-stripe-001:
    status: complete
    quality: 92
  payment-analysis-paypal-001:
    status: failed
    quality: 0
  payment-analysis-crypto-001:
    status: complete
    quality: 85
```

**Quality calculation:**
- Only aggregate successful: [92, 85]
- Result: (92×3 + 85×3) / (3+3) = 88.5

**Parent decision:**
- Continue with partial results
- Retry failed child
- Escalate to human

### How Do I Know When Parallel Is Better?

**Use parallel when:**
- ✅ Work can be split into independent sub-tasks
- ✅ Sub-tasks take similar time (no bottleneck)
- ✅ Wall-clock time matters more than token cost
- ✅ You have 3+ sub-tasks (overhead not worth it for 1-2)

**Use sequential when:**
- ❌ Work is sequential (A depends on B)
- ❌ Sub-tasks take very different times
- ❌ Token cost is critical (parallel = more concurrent usage)
- ❌ You have 1-2 sub-tasks (overhead not justified)

---

## 11. Performance Considerations

### Wall-Clock Time Savings

**Parallel execution saves wall-clock time proportional to parallelism:**

```
Wall-clock (parallel) = max(child_duration) + coordination_overhead
Wall-clock (sequential) = sum(child_duration)

Speedup = sum(child_duration) / max(child_duration)
```

**Example: 4 children, 1 hour each**
```
Parallel: max(1h, 1h, 1h, 1h) + 10min overhead = 1h 10min
Sequential: 1h + 1h + 1h + 1h = 4h
Speedup: 4h / 1h 10min = 3.4x
```

**Example: 4 children, different durations (1h, 2h, 1.5h, 1h)**
```
Parallel: max(1h, 2h, 1.5h, 1h) + 10min overhead = 2h 10min
Sequential: 1h + 2h + 1.5h + 1h = 5.5h
Speedup: 5.5h / 2h 10min = 2.5x
```

### Token Cost

**Token cost is usually the same (parallel vs. sequential):**

```
Parallel tokens = sum(child_tokens)
Sequential tokens = sum(child_tokens)
```

**Example:**
```
Child 1: 2000 tokens
Child 2: 2000 tokens
Child 3: 2000 tokens
Total: 6000 tokens (same whether parallel or sequential)
```

**Exception: Coordination overhead**
- Parent task creates children: +500 tokens
- Orchestrator waits/aggregates: +200 tokens
- Total overhead: ~700 tokens

**Cost comparison:**
```
Sequential: 6000 tokens × $0.0005/token = $3.00
Parallel: (6000 + 700) tokens × $0.0005/token = $3.35
Difference: +$0.35 (11% more)
```

**But wall-clock savings (75%) usually justify token overhead (11%).**

### Orchestrator Load Reduction

**Parallel delegation reduces Orchestrator load by 60-70%:**

```
Before (Phase 1):
- Orchestrator routes every task
- 100 tasks = 100 routing decisions
- Orchestrator load: 100%

After (Phase 2):
- Orchestrator routes parent tasks only
- 100 tasks = 10 parent tasks + 90 child tasks
- Only 10 routing decisions
- Orchestrator load: 10%
- Reduction: 90% (or 60-70% in practice with overhead)
```

### Coordination Overhead

**Parallel coordination adds latency:**

| Operation | Latency |
|-----------|---------|
| Create child task | 100ms |
| Queue child task | 50ms |
| Detect children | 200ms |
| Wait for children (per poll) | 1s |
| Aggregate results | 500ms |
| Write parent HANDBACK | 100ms |
| **Total overhead** | **~2-3 seconds** |

**For 1-hour tasks, 2-3 seconds overhead is negligible (<0.1%).**

### Scaling Considerations

**Parallel delegation scales well up to:**
- 10 children per parent ✅
- 5 tiers deep ✅
- 100 tasks per session ✅

**Beyond these limits:**
- Validator rejects (prevents runaway)
- Orchestrator may slow down
- Consider splitting into multiple parent tasks

**Example: 50 databases to migrate**
```
Option 1: 1 parent + 50 children
- Rejected: >10 children per parent

Option 2: 5 parents + 10 children each
- Parent 1: databases 1-10
- Parent 2: databases 11-20
- Parent 3: databases 21-30
- Parent 4: databases 31-40
- Parent 5: databases 41-50
- All 5 parents run in parallel
- Total wall-clock: ~1 hour (vs. 50 hours sequential)
```

---

## Summary

Parallel delegation is a powerful Phase 2 feature that enables:

✅ **Decentralized task creation** — agents create sub-tasks without Orchestrator routing
✅ **Reduced bottleneck** — Orchestrator load reduced by 60-70%
✅ **Parallel execution** — wall-clock time savings of 2-10x
✅ **Automatic aggregation** — quality, tokens, costs combined automatically
✅ **Backward compatible** — root tasks work unchanged
✅ **Safe** — validator prevents cycles, limits depth/width

Use parallel delegation for naturally decomposable work (multiple services, repos, domains) where wall-clock time matters more than token cost.

For questions or issues, see [Troubleshooting](#10-troubleshooting) or escalate to Principal Engineer.

---

**See also:**
- [AGENTS.md — Parallel Delegation Section](AGENTS.md#parallel-delegation-phase-2-feature)
- [HANDOFF.md — Parallel Delegation Protocol](HANDOFF.md#parallel-delegation-protocol-phase-2)
- [SUBTASK-WORKFLOWS.md — Implementation Details](SUBTASK-WORKFLOWS.md)
- [PROTOCOL.md § 14 — Protocol Spec](PROTOCOL.md#14-sub-task-workflows-phase-2)
