# Agentic Engineers Workflow — Complete Test Example

**Purpose:** Demonstrate the complete feedback loop: Engineer → QE → Model Engineer → improved routing.

**Scenario:** Two similar tasks across two days. Day 1 task feeds data to Model Engineer; Day 2 task uses the recommendation.

---

## Day 1: Initial Task (Haiku Baseline Routing)

### Task Description

```
Feature: Add result caching to {example-service} GetEvent endpoint
Repo: {example-service}
Type: Feature (caching pattern)
Complexity: Medium (straightforward if pattern is known)
```

### Orchestrator Routes Task

**Routing Decision:**
- Scope: Clear (cache GetEvent endpoint, TTL 1 hour, clear acceptance criteria)
- Complexity: Medium (well-known pattern in codebase)
- Model assigned: Haiku (first sample, baseline)
- Confidence: 0.50 (insufficient data, initial assignment)

```yaml
---
handoff_type: DELEGATE
task_id: 2026-04-24-cache-getevent
role: Engineer
model: claude-haiku-4-5
effort: high
scope: Add Redis caching to {example-service} GetEvent endpoint. Cache key={eventID}, TTL=1h. No changes to upstream services.
context:
  - File: lambda/query/main.go:215 (GetEvent handler)
  - Pattern: Redis caching already used in GetMembers (line 150) — same pattern
  - Acceptance: Cache hit ratio >80%, all tests pass, no latency regression
plan:
  1. Read existing GetMembers caching implementation (line 150-180)
  2. Apply same pattern to GetEvent
  3. Add TestGetEventCacheTTL covering hit/miss/expiry scenarios
  4. Run "make verify"
  5. Commit with conventional message
success_criteria:
  - "make verify" PASS (all tests, >85% coverage)
  - Cache hit ratio >80% in load test
  - No new warnings or errors
---
```

### Engineer Executes

**Execution Time:** 45 minutes
**Approach:** Read GetMembers pattern, apply to GetEvent, write comprehensive tests

**HANDBACK Block:**

```yaml
---
handoff_type: HANDBACK
task_id: 2026-04-24-cache-getevent
status: complete
deliverables:
  - Modified: lambda/query/main.go (lines 215-240, cache getter logic)
  - Added: lambda/query/cache_test.go (TestGetEventCacheTTL, TestCacheHitRatio)
tests:
  - "make verify": PASS (51 tests, 88% coverage, up from 85%)
tokens_in: 16400
tokens_out: 1950
model: claude-haiku-4-5
effort: high
duration_minutes: 45
escalations: 0
notes: "Pattern identical to GetMembers. Redis implementation straightforward. Tests comprehensive (hit, miss, TTL expiry, load)."
---
```

### Quality Engineer Verifies

**Tier 1 Verification:**
- ✅ Lint + Test Pass (51 tests, 0 errors)
- ✅ No new errors (coverage improved 85% → 88%)
- ✅ In-scope (only GetEvent caching, no other changes)
- ✅ Tests added (TestGetEventCacheTTL, load test)
- ✅ No production hazards (no panic, secrets, or commented code)

**QE Adds Model Assessment:**

```yaml
qe_feedback:
  tier_1_verdict: PASS
  model_assessment: "haiku_suitable"
  reasoning: "Pattern was straightforward, well-known from GetMembers implementation. Haiku applied it correctly without over-engineering. Cost-efficient execution."
  confidence_for_similar_tasks: 0.88
  quality_dimensions:
    test_coverage: 88
    coverage_assessment: "excellent, comprehensive edge cases (hit, miss, expiry, load)"
    error_handling: "defensive, clear error messages"
    code_clarity: "clear variable names, easy to follow logic"
    pattern_adherence: "perfect match to existing GetMembers pattern"
  notes: "Haiku is well-suited for caching tasks in this codebase. Future similar tasks should use Haiku with high confidence."
```

**Final HANDBACK (with QE feedback):**

```yaml
---
handoff_type: HANDBACK
task_id: 2026-04-24-cache-getevent
status: complete
deliverables:
  - Modified: lambda/query/main.go (lines 215-240)
  - Added: lambda/query/cache_test.go (TestGetEventCacheTTL, etc.)
tests:
  - "make verify": PASS (51 tests, 88% coverage)
tokens_in: 16400
tokens_out: 1950
model: claude-haiku-4-5
effort: high
duration_minutes: 45
escalations: 0
notes: "Pattern identical to GetMembers. Redis implementation straightforward."

qe_feedback:
  tier_1_verdict: PASS
  model_assessment: "haiku_suitable"
  reasoning: "Pattern was straightforward, well-known. Haiku applied correctly without over-engineering."
  confidence_for_similar_tasks: 0.88
  quality_dimensions:
    test_coverage: 88
    error_handling: "defensive"
    pattern_adherence: "perfect match to existing pattern"
---
```

### Metrics Recorded

Orchestrator saves to `~/.claude/metrics/2026-04-24/2026-04-24-cache-getevent.json`:

```json
{
  "schema_version": "1.0",
  "task_id": "2026-04-24-cache-getevent",
  "timestamp": "2026-04-24T18:30:00Z",
  "task_metadata": {
    "task_type": "feature",
    "repo": "{example-service}",
    "language": "go",
    "complexity_estimate": "medium",
    "complexity_actual": "low"
  },
  "assignment": {
    "role": "Engineer",
    "model": "claude-haiku-4-5",
    "effort": "high",
    "confidence": 0.50
  },
  "execution": {
    "start_time": "2026-04-24T17:45:00Z",
    "end_time": "2026-04-24T18:30:00Z",
    "duration_minutes": 45,
    "rework_loops": 0
  },
  "tokens": {
    "input": 16400,
    "output": 1950,
    "total": 18350
  },
  "cost": {
    "model_cost": 0.131
  },
  "quality": {
    "quality_score": 92,
    "qe_verdict": "PASS",
    "test_coverage": 88,
    "escalations": 0
  },
  "qe_feedback": {
    "model_assessment": "haiku_suitable",
    "reasoning": "Pattern was straightforward, well-known from GetMembers. Haiku applied correctly.",
    "confidence_for_similar_tasks": 0.88
  }
}
```

### Model Engineer Analyzes

**Input:** Task metrics + QE feedback from 2026-04-24-cache-getevent

**Analysis:**
```
Task signature: feature, {example-service}, medium-complexity caching
Historical samples for this signature: 1 (this task)
Quality: 92/100 ✅
QE assessment: haiku_suitable (confidence 0.88)
Model: Haiku
Cost: $0.131
Complexity actual: lower than estimated (low vs. medium estimate)
Error rate: 0 escalations
```

**Model Engineer Recommendation:**

```json
{
  "task_signature": {
    "task_type": "feature",
    "repo": "{example-service}",
    "complexity": "medium",
    "pattern_type": "caching"
  },
  "analysis": {
    "samples": 1,
    "quality_avg": 92.0,
    "cost_avg": 0.131,
    "qe_assessment": "haiku_suitable",
    "confidence_qe": 0.88,
    "escalation_rate": 0.0,
    "complexity_delta": "actual_lower_than_estimated"
  },
  "recommendation": {
    "rank_1": {
      "model": "claude-haiku-4-5",
      "effort": "high",
      "confidence": 0.88,
      "reason": "QE confirms Haiku suitable. Task was straightforward implementation of known pattern. Cost-efficient."
    },
    "rank_2": {
      "model": "claude-haiku-4-5",
      "effort": "medium",
      "confidence": 0.65,
      "reason": "Could reduce effort to medium (unproven). Only 1 sample; insufficient confidence."
    },
    "rank_3": {
      "model": "claude-sonnet-4-6",
      "effort": "medium",
      "confidence": 0.30,
      "reason": "Not recommended. Would cost 3x more ($0.39 vs $0.13) for no quality benefit."
    }
  },
  "decision_context": {
    "next_review_trigger": "After 3 more similar tasks OR if complexity estimate changes"
  }
}
```

---

## Day 2: Second Similar Task (Using Model Engineer Recommendation)

### Task Description

```
Feature: Add result caching to {example-service} GetMember endpoint
Repo: {example-service}
Type: Feature (caching pattern — same as Day 1)
Complexity: Medium (same pattern)
```

### Orchestrator Routes Task (With Recommendation)

**Orchestrator Logic:**
1. Receive task: "Add caching to GetMember endpoint"
2. Identify signature: feature, {example-service}, medium-complexity caching
3. Check Model Engineer recommendations for this signature
4. Found: Recommendation from 2026-04-24-cache-getevent (confidence 0.88)
5. Apply rank_1: **Use Haiku high-effort with 0.88 confidence**

```yaml
---
handoff_type: DELEGATE
task_id: 2026-04-25-cache-getmember
role: Engineer
model: claude-haiku-4-5
effort: high
scope: Add Redis caching to {example-service} GetMember endpoint. Cache key={memberID}, TTL=1h. Pattern: follow GetEvent caching (task 2026-04-24-cache-getevent).
context:
  - File: lambda/query/main.go:290 (GetMember handler)
  - Reference: See 2026-04-24-cache-getevent for identical pattern
  - Pattern: Same caching approach as GetEvent and GetMembers
plan:
  1. Review GetEvent caching from task 2026-04-24-cache-getevent (lambda/query/main.go:215-240)
  2. Apply identical pattern to GetMember
  3. Add TestGetMemberCacheTTL test (same structure as GetEvent test)
  4. Run "make verify"
  5. Commit
success_criteria:
  - "make verify" PASS (>85% coverage)
  - Cache hit ratio >80%
  - No new errors
routing_source: "Model Engineer recommendation (confidence 0.88)"
---
```

### Engineer Executes

**Execution Time:** 38 minutes (faster than Day 1 due to reference task available)

**HANDBACK Block:**

```yaml
---
handoff_type: HANDBACK
task_id: 2026-04-25-cache-getmember
status: complete
deliverables:
  - Modified: lambda/query/main.go (lines 290-310, cache getter logic)
  - Added: lambda/query/cache_test.go (TestGetMemberCacheTTL)
tests:
  - "make verify": PASS (52 tests, 88% coverage, consistent with GetEvent)
tokens_in: 14200
tokens_out: 1750
model: claude-haiku-4-5
effort: high
duration_minutes: 38
escalations: 0
notes: "Identical pattern to GetEvent cache task. Reference task made implementation even faster. Comprehensive tests (hit, miss, TTL, load)."

qe_feedback:
  tier_1_verdict: PASS
  model_assessment: "haiku_suitable"
  reasoning: "Haiku was appropriate. Task was repetition of known pattern (GetEvent cache). Execution fast and correct."
  confidence_for_similar_tasks: 0.92
  quality_dimensions:
    test_coverage: 88
    error_handling: "defensive"
    pattern_adherence: "exact match to GetEvent pattern"
  notes: "Second similar task confirms Haiku confidence. Pattern mastery now evident."
---
```

### Metrics Update

Orchestrator saves to `~/.claude/metrics/2026-04-25/2026-04-25-cache-getmember.json`:

```json
{
  "task_id": "2026-04-25-cache-getmember",
  "timestamp": "2026-04-25T15:20:00Z",
  "assignment": {
    "model": "claude-haiku-4-5",
    "effort": "high",
    "confidence": 0.88,
    "routing_source": "model_engineer_recommendation"
  },
  "quality": {
    "quality_score": 93,
    "test_coverage": 88,
    "escalations": 0
  },
  "cost": {
    "model_cost": 0.128
  },
  "qe_feedback": {
    "model_assessment": "haiku_suitable",
    "confidence_for_similar_tasks": 0.92
  }
}
```

### Model Engineer Updates Recommendation

**New Samples for Signature:**
- Sample 1: 2026-04-24-cache-getevent (quality 92, Haiku, confidence 0.88)
- Sample 2: 2026-04-25-cache-getmember (quality 93, Haiku, confidence 0.92)

**Updated Recommendation:**

```json
{
  "task_signature": {
    "task_type": "feature",
    "repo": "{example-service}",
    "pattern_type": "caching"
  },
  "analysis": {
    "samples": 2,
    "quality_avg": 92.5,
    "cost_avg": 0.1295,
    "qe_assessments": ["haiku_suitable", "haiku_suitable"],
    "avg_qe_confidence": 0.90,
    "escalation_rate": 0.0
  },
  "recommendation": {
    "rank_1": {
      "model": "claude-haiku-4-5",
      "effort": "high",
      "confidence": 0.92,
      "reason": "2 consistent samples, both quality 92-93. QE confirms Haiku is optimal for {example-service} caching tasks. Proven pattern."
    },
    "rank_2": {
      "model": "claude-haiku-4-5",
      "effort": "medium",
      "confidence": 0.70,
      "reason": "Could reduce effort (2 samples suggest straightforward). Small risk; consider if cost target active."
    },
    "rank_3": {
      "model": "claude-sonnet-4-6",
      "effort": "medium",
      "confidence": 0.15,
      "reason": "Not recommended. Haiku proven cost-efficient. Would increase cost 3x for no quality gain."
    }
  },
  "insights": {
    "pattern_mastery": "{example-service} caching tasks are routine for Haiku. Recommend Haiku for all future caching tasks.",
    "cost_optimization": "At $0.1295/task, caching tasks are cost-efficient. No need to explore higher models.",
    "next_sample": "Next sample will increase confidence toward 0.95+. Consider then whether effort can reduce to medium."
  }
}
```

**Confidence Improvement:**
- Day 1: 0.88 (1 sample, good but uncertain)
- Day 2: 0.92 (2 samples, high confidence, pattern confirmed)

---

## System Effects (Cumulative)

After 2 tasks of the same signature:

1. **Routing Improvement:** Haiku confidence increased 0.88 → 0.92
2. **Cost Optimization:** Established pattern for future similar tasks ($0.1295 baseline)
3. **Effort Baseline:** Identified that medium-complexity caching = Haiku high-effort (38-45 min)
4. **Quality Consistency:** 2/2 QE assessments agree: "haiku_suitable"
5. **Confidence Toward Reduction:** Medium-effort might work (2 samples suggest routine implementation)

---

## Week 2 Testing Checklist

- ✅ Task 1 executed with baseline routing (Haiku)
- ✅ QE provided model assessment feedback (haiku_suitable, 0.88 confidence)
- ✅ Metrics recorded and analyzed by Model Engineer
- ✅ Model Engineer generated recommendation (rank_1 Haiku, 0.88 confidence)
- ✅ Task 2 used Model Engineer recommendation (higher confidence routing)
- ✅ Workflow completed end-to-end without errors
- ✅ Confidence increased with second sample (0.88 → 0.92)
- ✅ Pattern identified for future similar tasks

**Conclusion:** Feedback loop working as designed. System is self-improving — each task makes future routing better.
