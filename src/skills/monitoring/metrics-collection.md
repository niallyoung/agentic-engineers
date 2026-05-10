# Orchestrator — Metrics Collection

**Role:** Orchestrator (Haiku, low effort)  
**Purpose:** Collect, validate, and store task metrics for optimization analysis and cost tracking

---

## Overview

Metrics Collection captures task execution data from HANDBACK and records it to `~/.claude/metrics/` for analysis by TokenAdvisor and Model Engineer.

**Input:** HANDBACK markup from Agent with tokens, quality score, execution data  
**Output:** Validated JSON file in `~/.claude/metrics/YYYY-MM-DD/task_id.json` ready for analysis

**Goal:** Maintain authoritative record of all task execution metrics for cost optimization and continuous improvement.

---

## Metrics Schema

```json
{
  "schema_version": "1.0",
  "task_id": "2026-04-24-redis-caching",
  "timestamp": "2026-04-24T18:30:00Z",
  
  "task_metadata": {
    "task_type": "feature",
    "repo": "{example-service}",
    "language": "go",
    "complexity_estimate": "medium",
    "complexity_actual": "low",
    "scope_estimate": 150,
    "scope_actual": 140
  },
  
  "assignment": {
    "role": "Engineer",
    "model": "claude-haiku-4-5",
    "effort": "high",
    "thinking": "disabled",
    "confidence": 0.95
  },
  
  "execution": {
    "start_time": "2026-04-24T17:00:00Z",
    "end_time": "2026-04-24T18:30:00Z",
    "duration_minutes": 90,
    "rework_loops": 0
  },
  
  "tokens": {
    "input": 18500,
    "output": 2100,
    "total": 20600,
    "cache_hits": 0,
    "cache_misses": 0
  },
  
  "cost": {
    "model_cost": 0.13,
    "currency": "USD",
    "cost_per_token": 0.0000063
  },
  
  "quality": {
    "quality_score": 92,
    "qe_verdict": "PASS",
    "tier_1_status": "PASS",
    "tier_2_status": "PASS",
    "tier_3_status": "N/A",
    "test_coverage": 87,
    "escalations": 0
  },
  
  "deliverables": [
    "Modified: lambda/query/main.go:45-80 (cache logic)",
    "Added: lambda/query/cache_test.go (tests)"
  ],
  
  "qe_feedback": {
    "recommendation": "haiku_suitable",
    "reasoning": "Task was well-scoped. Haiku handled pattern correctly. Cost-effective choice.",
    "confidence_for_similar_tasks": 0.92,
    "notes": "Excellent test coverage (87%), clear error handling"
  },
  
  "model_engineer_input": {
    "quality_delta": 0,
    "cost_delta": 0,
    "pattern_type": "caching",
    "familiarity_score": 0.9,
    "recommendation_for_next": "haiku_high_effort"
  }
}
```

---

## Collection Process

### Step 1: Receive HANDBACK

Agent returns HANDBACK markup with:
- `task_id`
- `status` (complete, incomplete, escalated)
- `tokens_in`, `tokens_out`
- `quality_score` (1-100)
- Deliverables list
- Duration in minutes
- Escalations count

### Step 2: Validate HANDBACK

Check required fields:

```
Required for all tasks:
✓ task_id (must match DELEGATE)
✓ status (complete/incomplete/escalated)
✓ tokens_in (>0)
✓ tokens_out (>0)
✓ quality_score (1-100)
✓ model (haiku/sonnet/opus)
✓ effort (low/medium/high)
✓ duration_minutes (>0)

Required if status=complete:
✓ deliverables (non-empty list)
✓ qe_feedback (quality assessment)
✓ qe_verdict (PASS/FAIL)

Required if status=incomplete or escalated:
✓ escalation_reason
✓ root_cause (explanation)
```

If validation fails, return to Agent with specific errors before recording.

### Step 3: Compute Derived Fields

From tokens and model, calculate:
```
cost_usd = (tokens_in + tokens_out) * model_cost_per_1m_tokens / 1_000_000
cost_per_quality_point = cost_usd / quality_score
quality_per_dollar = quality_score / cost_usd
```

### Step 4: Record to File

Save to `~/.claude/metrics/YYYY-MM-DD/{task_id}.json` (formatted JSON).

Example:
```
~/.claude/metrics/2026-04-24/2026-04-24-redis-caching.json
```

### Step 5: Update Session Log

Append to `~/.claude/metrics/YYYY-MM-DD/session.jsonl` (one JSON object per line):

```
{"timestamp": "2026-04-24T18:30:00Z", "task_id": "2026-04-24-redis-caching", "model": "haiku", "quality": 92, "cost": 0.13}
{"timestamp": "2026-04-24T19:15:00Z", "task_id": "2026-04-24-test-fix", "model": "haiku", "quality": 88, "cost": 0.09}
```

---

## HANDBACK to Metrics Mapping

| HANDBACK Field | Metrics Field | Notes |
|---|---|---|
| `task_id` | `task_id` | Unique identifier |
| `status` | `execution.status` | complete/incomplete/escalated |
| `tokens_in` | `tokens.input` | From HANDBACK |
| `tokens_out` | `tokens.output` | From HANDBACK |
| `model` | `assignment.model` | From DELEGATE |
| `effort` | `assignment.effort` | From DELEGATE |
| `quality_score` | `quality.quality_score` | From QE assessment |
| `duration_minutes` | `execution.duration_minutes` | Wall clock time |
| `escalations` | `quality.escalations` | Count of escalation events |
| `deliverables` | `deliverables` | Files modified/created |
| `qe_verdict` | `quality.qe_verdict` | PASS/FAIL |
| `qe_feedback` | `qe_feedback` | Full feedback block |

---

## Quality Score Normalization

HANDBACK may provide quality score as:
- Explicit score: `quality_score: 92`
- Pass/fail: `qe_verdict: PASS` → normalize to 90 (default pass score)
- Feedback: If no explicit score, derive from QE assessment

Normalize to 1-100 scale:
- 1-59: Needs rework (fail)
- 60-79: Acceptable with issues (marginal pass)
- 80-89: Good (pass)
- 90-100: Excellent (strong pass)

---

## Cost Calculation

For each model, use standard rates:

| Model | $/1M input tokens | $/1M output tokens |
|-------|---|---|
| claude-haiku-4-5 | 0.80 | 4.00 |
| claude-sonnet-4-6 | 3.00 | 15.00 |
| claude-opus-4-7 | 15.00 | 75.00 |

Calculate:
```
cost_usd = (tokens_in * input_rate + tokens_out * output_rate) / 1_000_000
```

Example (Haiku):
```
tokens_in: 18,500
tokens_out: 2,100
cost = (18500 * 0.80 + 2100 * 4.00) / 1_000_000
     = (14,800 + 8,400) / 1_000_000
     = 23,200 / 1_000_000
     = $0.0232
```

---

## Validation Rules

### Sanity Checks

- **Tokens:** 0 < tokens_in < 100,000 (reject outliers)
- **Quality:** 1 ≤ quality_score ≤ 100
- **Duration:** 0 < duration_minutes < 480 (reject tasks >8 hours without escalation)
- **Rework loops:** 0 ≤ rework_loops ≤ 5 (reject >5 loops)
- **Escalations:** 0 ≤ escalations ≤ 10 (reject >10 escalations in one task)

### Consistency Checks

- Task ID format: `YYYY-MM-DD-{slug}` (validates timestamp matches file date)
- Model matches DELEGATE assignment
- Quality score matches QE verdict (PASS ≥ 80, FAIL < 80)
- Deliverables non-empty if status=complete

If any check fails:
```
Log error with task_id and specific failure reason
Return HANDBACK to Agent for correction
Do not record invalid metric
```

---

## Collection Example

**Incoming HANDBACK:**
```yaml
---
handoff_type: HANDBACK
task_id: 2026-04-24-redis-caching
status: complete
deliverables:
  - Modified: lambda/query/main.go:45-80
  - Added: lambda/query/cache_test.go
tests:
  - "make verify": PASS (87% coverage)
tokens_in: 18500
tokens_out: 2100
model: claude-haiku-4-5
effort: high
duration_minutes: 90
escalations: 0
quality_score: 92
qe_feedback:
  recommendation: haiku_suitable
  confidence_for_similar_tasks: 0.92
---
```

**Validation:**
✓ All required fields present
✓ Status = complete
✓ Tokens in range
✓ Quality score in range
✓ Model matches DELEGATE
✓ Deliverables present

**Calculation:**
```
cost = (18500 * 0.80 + 2100 * 4.00) / 1_000_000 = $0.0232
cost_per_quality_point = 0.0232 / 92 = $0.00025
quality_per_dollar = 92 / 0.0232 = 3965
```

**Output file:** `~/.claude/metrics/2026-04-24/2026-04-24-redis-caching.json` with full metrics.

**Session log append:**
```
{"timestamp": "2026-04-24T18:30:00Z", "task_id": "2026-04-24-redis-caching", "model": "haiku", "quality": 92, "cost": 0.0232}
```

---

## Storage & Retention

**Location:** `~/.claude/metrics/YYYY-MM-DD/`

**File naming:**
- Per-task: `{task_id}.json`
- Session log: `session.jsonl`
- Daily summary (TokenAdvisor): `daily_summary.json`

**Retention:**
- Per-task JSON: Indefinite (historical record)
- Session JSONL: Rolling 90 days (automatic cleanup)
- Daily summaries: Keep for 12 months

**Backup:** Manual backups weekly to external storage (optional).

---

## Integration with Analysis

Collected metrics feed into:
1. **TokenAdvisor** (daily analysis at 17:00)
2. **Model Engineer** (immediate analysis for model recommendations)
3. **Cost tracking** (monthly budget review)
4. **Quality trending** (identify degradation)
5. **A/B testing** (compare model arms)

---

## Errors & Recovery

### If HANDBACK is rejected for validation error:

1. Return to Agent with specific field errors
2. Agent corrects HANDBACK and resubmits
3. Collect on resubmission

### If file write fails:

1. Log error with task_id
2. Retry write (up to 3 times)
3. If persistent failure, alert Orchestrator

### If metrics become corrupted:

1. Reconstruct from HANDBACK logs
2. Revalidate
3. Investigate root cause
