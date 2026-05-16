# Parallel Delegation Troubleshooting Guide

**Common issues and solutions for parallel delegation in the agentic-engineers framework.**

---

## Table of Contents

1. [Child Task Stuck in Processing](#1-child-task-stuck-in-processing)
2. [Aggregation Quality Score Incorrect](#2-aggregation-quality-score-incorrect)
3. [Parent Task Timed Out](#3-parent-task-timed-out)
4. [Children Failed or Blocked](#4-children-failed-or-blocked)
5. [Validation Errors](#5-validation-errors)
6. [Performance Issues](#6-performance-issues)
7. [Debugging Techniques](#7-debugging-techniques)

---

## 1. Child Task Stuck in Processing

### Symptom

Child task remains in `artifacts/queue/processing/` for >2 hours with no progress.

### Diagnosis

**Step 1: Check queue status**
```bash
# Count tasks in processing
ls -la artifacts/queue/processing/ | wc -l

# Check if child task exists
ls -la artifacts/queue/processing/ | grep "payment-analysis-stripe-001"
```

**Step 2: Check Orchestrator logs**
```bash
# Look for errors related to child task
tail -100 logs/orchestrator.log | grep "payment-analysis-stripe-001"

# Look for queue-related errors
tail -100 logs/orchestrator.log | grep -i "queue\|processing"
```

**Step 3: Verify parent task completed**
```bash
# Check if parent task is in done/
ls -la artifacts/queue/done/ | grep "payment-analysis-001"

# Check parent HANDBACK
cat artifacts/queue/done/payment-analysis-001.yaml | grep -A 20 "children_created"
```

**Step 4: Check if queue is full**
```bash
# Count total tasks in queue
find artifacts/queue -name "*.yaml" | wc -l

# If >100, rate limit may be triggered
```

### Solutions

**Solution 1: Verify child task is valid YAML**
```bash
# Check YAML syntax
python3 -c "import yaml; yaml.safe_load(open('artifacts/queue/processing/payment-analysis-stripe-001.yaml'))"

# If error, fix YAML syntax
```

**Solution 2: Check if parent task is detected**
```bash
# Verify parent_task_id is set correctly
cat artifacts/queue/processing/payment-analysis-stripe-001.yaml | grep "parent_task_id"

# Should output: parent_task_id: payment-analysis-001
```

**Solution 3: Manually move to done/ (last resort)**
```bash
# Only if stuck >4 hours and confirmed no agent is working on it
# Create a HANDBACK manually
cat > artifacts/queue/done/payment-analysis-stripe-001.yaml << 'EOF'
---
handoff_type: HANDBACK
task_id: payment-analysis-stripe-001
status: blocked
deliverables: []
tests: []
tokens_in: 0
tokens_out: 0
model: unknown
effort: unknown
duration_minutes: 0
escalations: 0
notes: "Manually moved to done/ due to stuck processing. Investigate root cause."
---
EOF

# Then notify Principal Engineer
```

**Solution 4: Escalate to Principal Engineer**
```bash
# If stuck >2 hours and no clear cause
# Create escalation task
cat > artifacts/queue/incoming/escalation-stuck-task.yaml << 'EOF'
---
handoff_type: DELEGATE
task_id: 2026-05-16-escalation-stuck-payment-analysis-stripe
role: principal_engineer
scope: "Investigate stuck child task: payment-analysis-stripe-001. Task in processing for >2 hours."
context:
  - Parent task: payment-analysis-001
  - Child task: payment-analysis-stripe-001
  - Status: stuck in processing/
  - Duration: >2 hours
plan:
  1. Check Orchestrator logs for errors
  2. Verify child task YAML validity
  3. Check if parent task completed
  4. Determine root cause
  5. Recommend fix or manual recovery
success_criteria:
  - Root cause identified
  - Fix or recovery plan documented
---
EOF
```

---

## 2. Aggregation Quality Score Incorrect

### Symptom

Parent quality score doesn't match expected value. Example: expected 90, got 85.

### Diagnosis

**Step 1: Extract child quality scores**
```bash
# Get all child HANDBACKs
cat artifacts/queue/done/payment-analysis-stripe-001.yaml | grep "quality:"
cat artifacts/queue/done/payment-analysis-paypal-001.yaml | grep "quality:"
cat artifacts/queue/done/payment-analysis-crypto-001.yaml | grep "quality:"

# Output example:
# quality: 92
# quality: 88
# quality: 85
```

**Step 2: Extract effort levels**
```bash
# Get effort level for each child
cat artifacts/queue/done/payment-analysis-stripe-001.yaml | grep "^effort:"
cat artifacts/queue/done/payment-analysis-paypal-001.yaml | grep "^effort:"
cat artifacts/queue/done/payment-analysis-crypto-001.yaml | grep "^effort:"

# Output example:
# effort: high
# effort: high
# effort: medium
```

**Step 3: Manual calculation**
```python
# Manual weighted average calculation
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
# Expected quality: 88.75

# Compare with actual
actual = 85
print(f"Difference: {expected - actual}")
# Difference: 3.75
```

### Solutions

**Solution 1: Verify effort levels in child HANDBACKs**
```bash
# Check if effort field is present and correct
for file in artifacts/queue/done/payment-analysis-*.yaml; do
    echo "File: $file"
    grep "^effort:" "$file"
done
```

**Solution 2: Check for failed children**
```bash
# If some children failed, they're excluded from aggregation
cat artifacts/queue/done/payment-analysis-001.yaml | grep -A 10 "children_failed:"

# If children_failed is not empty, quality is calculated only from successful children
```

**Solution 3: Verify parent HANDBACK calculation**
```bash
# Check parent HANDBACK for quality calculation notes
cat artifacts/queue/done/payment-analysis-001.yaml | grep -A 5 "aggregate_quality"
```

**Solution 4: Report to Quality Engineer**
```bash
# If calculation is still wrong after verification
# Create a task for Quality Engineer
cat > artifacts/queue/incoming/qa-quality-score-issue.yaml << 'EOF'
---
handoff_type: DELEGATE
task_id: 2026-05-16-qa-quality-score-issue
role: quality_engineer
scope: "Verify quality score calculation for parent task payment-analysis-001. Expected: 88.75, Actual: 85."
context:
  - Parent task: payment-analysis-001
  - Expected quality: 88.75
  - Actual quality: 85
  - Difference: 3.75
plan:
  1. Review child HANDBACKs and effort levels
  2. Manually calculate expected quality
  3. Identify discrepancy
  4. Report findings
success_criteria:
  - Discrepancy identified
  - Root cause documented
  - Recommendation provided
---
EOF
```

---

## 3. Parent Task Timed Out

### Symptom

`result_aggregation_status = timed_out`, some children still in `processing/`.

### Diagnosis

**Step 1: Check parent HANDBACK**
```bash
# Look for timed_out status
cat artifacts/queue/done/payment-analysis-001.yaml | grep "result_aggregation_status"

# Output: result_aggregation_status: timed_out
```

**Step 2: Check which children are still processing**
```bash
# Look for children in processing/
ls artifacts/queue/processing/ | grep "payment-analysis"

# Output example:
# payment-analysis-paypal-001.yaml
# payment-analysis-crypto-001.yaml
```

**Step 3: Check how long children have been running**
```bash
# Check file modification time
ls -la artifacts/queue/processing/payment-analysis-paypal-001.yaml

# Compare with current time
date

# If >60 minutes, timeout occurred
```

**Step 4: Check if children are making progress**
```bash
# Look at Orchestrator logs for child task activity
tail -200 logs/orchestrator.log | grep "payment-analysis-paypal-001"

# If no recent activity, child may be blocked
```

### Solutions

**Solution 1: Increase timeout (if children need more time)**
```bash
# Edit Orchestrator config
# In src/orchestration/agents/orchestrator.py or config file
# Change: timeout_minutes=60 to timeout_minutes=120

# Then restart Orchestrator
```

**Solution 2: Check if children are blocked**
```bash
# Look for "blocked" status in child HANDBACKs
cat artifacts/queue/processing/payment-analysis-paypal-001.yaml | grep "status:"

# If status: blocked, child is waiting for external input
# Escalate to appropriate role to unblock
```

**Solution 3: Manually complete parent task**
```bash
# If timeout is acceptable and partial results are sufficient
# Create parent HANDBACK with partial results

cat > artifacts/queue/done/payment-analysis-001.yaml << 'EOF'
---
handoff_type: HANDBACK
task_id: payment-analysis-001
status: complete
children_results:
  payment-analysis-stripe-001:
    status: complete
    quality: 92
  payment-analysis-paypal-001:
    status: null  # Still processing
  payment-analysis-crypto-001:
    status: null  # Still processing
  payment-analysis-square-001:
    status: complete
    quality: 95
result_aggregation_status: timed_out
notes: "Timeout after 60 minutes. 2 of 4 children completed. Partial results included."
---
EOF
```

**Solution 4: Retry failed children**
```bash
# Create new DELEGATE for timed-out children
cat > artifacts/queue/incoming/retry-payment-analysis-paypal.yaml << 'EOF'
---
handoff_type: DELEGATE
task_id: 2026-05-16-retry-payment-analysis-paypal-001
role: security_engineer
scope: "Retry security audit of PayPal payment service (previous attempt timed out)."
context:
  - Parent task: payment-analysis-001
  - Previous attempt: timed out after 60 minutes
  - Reason: may have been rate-limited
plan:
  1. Review PayPal integration code
  2. Check dependencies
  3. Document findings
success_criteria:
  - PayPal audit completed
  - Findings documented
---
EOF
```

---

## 4. Children Failed or Blocked

### Symptom

`children_failed` list is not empty. One or more children failed or are blocked.

### Diagnosis

**Step 1: Check which children failed**
```bash
# Look at parent HANDBACK
cat artifacts/queue/done/payment-analysis-001.yaml | grep -A 5 "children_failed:"

# Output example:
# children_failed:
#   - payment-analysis-paypal-001
#   - payment-analysis-crypto-001
```

**Step 2: Check child HANDBACK for failure reason**
```bash
# Look at failed child HANDBACK
cat artifacts/queue/done/payment-analysis-paypal-001.yaml | grep -A 10 "status:\|notes:"

# Output example:
# status: failed
# notes: "Unable to access PayPal API. Rate limiting prevented analysis."
```

**Step 3: Check if failure is temporary or permanent**
```bash
# Temporary: rate limiting, network issue, timeout
# Permanent: invalid credentials, API changed, scope out of bounds

# Look at error message in notes
cat artifacts/queue/done/payment-analysis-paypal-001.yaml | grep "notes:"
```

### Solutions

**Solution 1: Retry failed child (if temporary failure)**
```bash
# Create new DELEGATE for failed child
cat > artifacts/queue/incoming/retry-payment-analysis-paypal.yaml << 'EOF'
---
handoff_type: DELEGATE
task_id: 2026-05-16-retry-payment-analysis-paypal-001
role: security_engineer
scope: "Retry security audit of PayPal (previous attempt failed due to rate limiting)."
context:
  - Parent task: payment-analysis-001
  - Previous failure: rate limiting
  - Retry reason: temporary issue, should succeed now
plan:
  1. Retry PayPal security audit
  2. Use exponential backoff if rate-limited again
  3. Document findings
success_criteria:
  - PayPal audit completed
  - Findings documented
---
EOF
```

**Solution 2: Escalate blocked child (if permanent failure)**
```bash
# Create escalation task for blocked child
cat > artifacts/queue/incoming/escalation-payment-analysis-crypto.yaml << 'EOF'
---
handoff_type: DELEGATE
task_id: 2026-05-16-escalation-payment-analysis-crypto
role: principal_engineer
scope: "Investigate why Crypto payment service audit is blocked. Determine if scope is out of bounds or if external blocker exists."
context:
  - Parent task: payment-analysis-001
  - Child task: payment-analysis-crypto-001
  - Status: blocked
  - Reason: unknown
plan:
  1. Review child task DELEGATE and HANDBACK
  2. Determine root cause of blockage
  3. Recommend fix or alternative approach
  4. Document findings
success_criteria:
  - Root cause identified
  - Fix or alternative approach recommended
---
EOF
```

**Solution 3: Continue with partial results**
```bash
# If acceptable to continue with partial results
# Update parent HANDBACK with explanation

cat > artifacts/queue/done/payment-analysis-001.yaml << 'EOF'
---
handoff_type: HANDBACK
task_id: payment-analysis-001
status: complete
children_results:
  payment-analysis-stripe-001:
    status: complete
    quality: 92
  payment-analysis-paypal-001:
    status: failed
    quality: 0
  payment-analysis-crypto-001:
    status: blocked
    quality: 0
  payment-analysis-square-001:
    status: complete
    quality: 95
children_failed:
  - payment-analysis-paypal-001
  - payment-analysis-crypto-001
result_aggregation_status: partial
notes: "2 of 4 services analyzed. PayPal failed (rate limiting), Crypto blocked (unknown reason). Recommend retry after 1 hour."
---
EOF
```

---

## 5. Validation Errors

### Symptom

Child task creation fails with validation error. Examples:
- `ValueError: parent_task_id not found`
- `ValueError: task_tier exceeds maximum (5)`
- `RuntimeError: already has N children (max 10)`

### Diagnosis & Solutions

**Error: `ValueError: parent_task_id not found`**

Cause: Parent task doesn't exist in queue.

Solution:
```bash
# Verify parent task exists
ls artifacts/queue/incoming/ | grep "payment-analysis-001"
ls artifacts/queue/processing/ | grep "payment-analysis-001"
ls artifacts/queue/done/ | grep "payment-analysis-001"

# If not found, create parent task first
# Then create children
```

**Error: `ValueError: task_tier exceeds maximum (5)`**

Cause: Trying to create child at tier 6 or deeper.

Solution:
```bash
# Check current tier depth
cat artifacts/queue/done/parent-task.yaml | grep "task_tier:"

# If tier 5, cannot create children
# Flatten hierarchy or create sibling instead of child
```

**Error: `RuntimeError: already has N children (max 10)`**

Cause: Parent already has 10 children.

Solution:
```bash
# Count existing children
cat artifacts/queue/done/parent-task.yaml | grep -A 20 "children_created:" | wc -l

# If 10, create new parent task for additional children
# Split work across multiple parents
```

**Error: `ValueError: cycle detected`**

Cause: Trying to link to ancestor (would create cycle).

Solution:
```bash
# Check parent_task_id
# Verify it's not an ancestor of current task

# Example of cycle:
# Task A → Task B (parent)
# Task B → Task C (parent)
# Task C → Task A (parent) ← CYCLE!

# Fix: Don't link Task C to Task A
```

**Error: `ValueError: scope overlap < 20%`**

Cause: Child scope doesn't overlap parent scope enough.

Solution:
```bash
# Check child scope
# Ensure it's a subset of parent scope

# Example:
# Parent: "Analyze payment services"
# Child: "Analyze Stripe payment service" ← Good (overlap >20%)
# Child: "Analyze database performance" ← Bad (overlap <20%)
```

---

## 6. Performance Issues

### Symptom

Parallel delegation is slower than expected, or Orchestrator is slow.

### Diagnosis

**Step 1: Check wall-clock time**
```bash
# Get parent task start and end times
cat artifacts/queue/done/payment-analysis-001.yaml | grep "duration_minutes:"

# Compare with expected
# Expected: max(child_duration) + 10min overhead
# Actual: should be close to expected
```

**Step 2: Check child task durations**
```bash
# Get duration for each child
for file in artifacts/queue/done/payment-analysis-*.yaml; do
    echo "File: $(basename $file)"
    grep "duration_minutes:" "$file"
done

# Output example:
# File: payment-analysis-stripe-001.yaml
# duration_minutes: 58
# File: payment-analysis-paypal-001.yaml
# duration_minutes: 62
# File: payment-analysis-crypto-001.yaml
# duration_minutes: 60
# File: payment-analysis-square-001.yaml
# duration_minutes: 55

# Max: 62 minutes
# Expected parent duration: 62 + 10 = 72 minutes
```

**Step 3: Check Orchestrator polling interval**
```bash
# Look at Orchestrator logs
tail -500 logs/orchestrator.log | grep "polling\|wait_for_children"

# If polling interval is too long (>5 seconds), increase frequency
```

### Solutions

**Solution 1: Increase Orchestrator polling frequency**
```bash
# In src/orchestration/agents/orchestrator.py
# Change: poll_interval=1.0 to poll_interval=0.5 (faster polling)

# Restart Orchestrator
```

**Solution 2: Reduce number of children per parent**
```bash
# If >10 children, split into multiple parents
# Example: 20 children → 2 parents with 10 children each

# Parallel execution of 2 parents + children:
# Parent 1 (10 children): ~1 hour
# Parent 2 (10 children): ~1 hour (concurrent)
# Total: ~1 hour (same as single parent with 10 children)
```

**Solution 3: Profile child task execution**
```bash
# Check if children are CPU-bound or I/O-bound
# If CPU-bound, parallelism helps
# If I/O-bound, parallelism may not help (depends on I/O concurrency)

# Look at child task notes for clues
cat artifacts/queue/done/payment-analysis-stripe-001.yaml | grep "notes:"
```

---

## 7. Debugging Techniques

### Technique 1: Enable Debug Logging

```bash
# Set debug log level
export LOG_LEVEL=DEBUG

# Restart Orchestrator
python3 src/orchestration/agents/orchestrator.py

# Check logs for detailed information
tail -1000 logs/orchestrator.log | grep -i "debug\|parent\|child"
```

### Technique 2: Inspect Queue State

```bash
# Check all queue directories
echo "=== INCOMING ==="
ls artifacts/queue/incoming/ | wc -l

echo "=== PROCESSING ==="
ls artifacts/queue/processing/ | wc -l

echo "=== DONE ==="
ls artifacts/queue/done/ | wc -l

# Check specific task
echo "=== PARENT TASK ==="
cat artifacts/queue/done/payment-analysis-001.yaml | head -30
```

### Technique 3: Manual Aggregation Calculation

```python
# Python script to manually calculate aggregation
import yaml

# Load parent HANDBACK
with open("artifacts/queue/done/payment-analysis-001.yaml") as f:
    parent = yaml.safe_load(f)

# Extract children results
children = parent.get("children_results", {})

# Calculate quality
weights = {"high": 3, "medium": 2, "low": 1}
total_quality = 0
total_weight = 0

for task_id, result in children.items():
    if result["status"] == "complete":
        # Load child HANDBACK to get effort
        with open(f"artifacts/queue/done/{task_id}.yaml") as f:
            child = yaml.safe_load(f)
        effort = child.get("effort", "medium")
        weight = weights.get(effort, 1)
        quality = result.get("quality", 0)
        total_quality += quality * weight
        total_weight += weight

# Calculate average
if total_weight > 0:
    avg_quality = total_quality / total_weight
    print(f"Calculated quality: {avg_quality}")
    print(f"Actual quality: {parent.get('aggregate_quality', 'N/A')}")
```

### Technique 4: Trace Child Execution

```bash
# Find all log entries for a specific child
grep "payment-analysis-stripe-001" logs/orchestrator.log | head -50

# Check timestamps
grep "payment-analysis-stripe-001" logs/orchestrator.log | grep -o "^\[.*\]" | head -5

# Look for errors
grep "payment-analysis-stripe-001" logs/orchestrator.log | grep -i "error\|failed\|blocked"
```

### Technique 5: Compare Sequential vs. Parallel

```bash
# Sequential execution (old approach)
# 1. Create parent task
# 2. Parent creates children one by one
# 3. Each child completes before next starts
# 4. Total time: sum(child_duration)

# Parallel execution (new approach)
# 1. Create parent task
# 2. Parent creates all children at once
# 3. All children execute concurrently
# 4. Total time: max(child_duration)

# To verify parallelism is working:
# Check if children start times are close together
grep "payment-analysis-.*-001" logs/orchestrator.log | grep "assigned\|started" | head -10
```

---

## Quick Reference

| Issue | Symptom | Quick Fix |
|-------|---------|-----------|
| Child stuck | >2 hours in processing/ | Check Orchestrator logs, verify parent completed |
| Quality wrong | Actual ≠ Expected | Verify effort levels, check for failed children |
| Timeout | `timed_out` status | Increase timeout_minutes, check if children blocked |
| Failed child | `children_failed` not empty | Retry (temporary) or escalate (permanent) |
| Validation error | `ValueError` or `RuntimeError` | Check parent exists, tier depth, children count |
| Slow performance | Wall-clock > expected | Increase polling frequency, reduce children count |

---

**See also:**
- [PARALLEL-DELEGATION-GUIDE.md](PARALLEL-DELEGATION-GUIDE.md#10-troubleshooting)
- [AGENTS.md — Parallel Delegation](AGENTS.md#parallel-delegation-phase-2-feature)
- [HANDOFF.md — Parallel Protocol](HANDOFF.md#parallel-delegation-protocol-phase-2)

For additional help, escalate to Principal Engineer.
