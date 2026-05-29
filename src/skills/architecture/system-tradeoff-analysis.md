# Principal Engineer — System Tradeoff Analysis

**Role:** Principal Engineer (Opus 4.6, high effort)  
**Purpose:** Analyze complex tradeoffs (performance vs. cost vs. complexity) to guide architectural decisions

---

## Overview

When an architecture decision has conflicting goals, Principal Engineer performs systematic tradeoff analysis to make principled choices.

**Input:** Multiple design options, competing objectives (fast, cheap, simple, reliable)  
**Output:** Quantified comparison table, recommendation with rationale

**Goal:** Make optimization choices defensible, traceable, and revisable as conditions change.

---

## Common Tradeoff Dimensions

| Dimension | High | Low | Cost |
|-----------|------|-----|------|
| **Performance** | Low latency, high throughput | Acceptable latency | More infrastructure, complexity |
| **Cost** | Minimal spend | High spend | Performance, features |
| **Complexity** | Simple architecture | Feature-rich, optimized | Maintenance burden, training |
| **Reliability** | 99.99% uptime | 99% uptime | Redundancy, monitoring, runbooks |
| **Consistency** | Strong (immediate) | Eventual (stale) | Synchronous calls, blocking, latency |
| **Time-to-deliver** | Ship in 2 weeks | Ship in 2 months | Technical debt, simplicity vs. elegance |

---

## Methodology

### 1. Identify Competing Objectives

**Example:** "We need fast queries AND low infrastructure costs"

```
Fast queries (~100ms avg)
vs.
Minimal infrastructure cost
```

These conflict because fast queries need caching, which adds compute cost.

### 2. Quantify Each Objective

**Performance objective:**
- Current latency: 500ms (p50), 2s (p99)
- Target latency: 100ms (p50), 500ms (p99)
- User impact: checkout takes too long

**Cost objective:**
- Current monthly cost: $10K
- Target monthly cost: $7K (30% reduction)
- Business constraint: save 30% without reducing throughput

### 3. Evaluate Tradeoff Curves

For each dimension, plot:
- **X-axis:** One objective (e.g., cost)
- **Y-axis:** Another objective (e.g., latency)

```
Latency (p50)
│
100ms │    ●
      │   ●
200ms │  ●
      │ ●
500ms │●
      └──────────────────────
        $10K   $7K    $5K   (Monthly Cost)

Option A: Cache + Redis       → $9K, 100ms
Option B: PostgreSQL tuning   → $7K, 200ms
Option C: Sharding            → $5K, 150ms
Option D: Bare minimum        → $3K, 500ms
```

**Recommendation:** Choose based on business priority:
- If latency critical → Option A ($9K, miss 30% cost target)
- If cost critical → Option B (meet target, accept higher latency)
- If balanced → Option C (compromise both)

### 4. Document Constraints

What's NOT negotiable?

```
Hard Constraints (non-negotiable):
- Must support 10K requests/sec peak
- Must comply with data residency (EU data in EU)
- Must not require new hiring (team capacity fixed)

Soft Constraints (business preference but negotiable):
- Prefer <100ms latency
- Target 30% cost reduction
- Nice to have: single-region operation
```

Hard constraints filter options immediately.  
Soft constraints guide the recommendation.

### 5. Calculate Total Cost of Ownership (TCO)

Don't just compare infrastructure cost. Include:

```
Option A (Redis Cache):
  Infrastructure: $9K/month
  Operations: $5K/month (Redis monitoring, tuning)
  Engineering: $20K (dev time + training)
  Total Year 1: $176K
  Total Year 2+: $168K/year (no dev time)

Option B (PostgreSQL Tuning):
  Infrastructure: $7K/month
  Operations: $2K/month (fewer moving parts)
  Engineering: $10K (dev time)
  Total Year 1: $124K
  Total Year 2+: $108K/year

⟹ If you operate >1 year, TCO changes the decision
```

### 6. Sensitivity Analysis

What happens if assumptions change?

```
"Our cost target is 30% savings. What if it becomes 20%?"

With 20% savings target (allow $8K/month instead of $7K):
  Option A becomes viable ($9K cost OK, but get 100ms latency)
  Option B still works ($7K cost, 200ms latency)
  Recommendation shifts

"What if traffic doubles?"

Current: 2K req/sec
Future: 4K req/sec

Some options don't scale. Re-evaluate.
```

---

## Output Template

```
# Tradeoff Analysis: [Decision Name]

## Objective Conflict

We want:
- [Objective A]: [target], because [business reason]
- [Objective B]: [target], because [business reason]

These conflict because: [explanation]

## Options Evaluated

### Option 1: [Name]
- Performance: [metric] (vs. target [X])
- Cost: [metric] (vs. target [X])
- Complexity: [simple|moderate|complex]
- Time to deliver: [weeks]
- Risk: [low|medium|high]

[Repeat for options 2, 3, ...]

## Tradeoff Matrix

| | Latency | Cost | Complexity | Time | Risk |
|---|---------|------|------------|------|------|
| **Target** | 100ms | $7K | Simple | 4 wks | Low |
| Option A | 100ms | $9K | High | 4 wks | Medium |
| Option B | 200ms | $7K | Low | 2 wks | Low |
| Option C | 150ms | $5K | Medium | 6 wks | High |

## Total Cost of Ownership (3-year)

| | Year 1 | Year 2-3 | Total |
|---|--------|----------|-------|
| Option A | $176K | $168K | $512K |
| Option B | $124K | $108K | $340K |
| Option C | $165K | $150K | $465K |

## Hard Constraints

- Must support 10K req/sec peak ← eliminates [option X]
- Must stay in EU ← eliminates [option Y]
- Team cannot grow ← impacts Option C timeline

## Recommendation

**Choose [Option X] because:**
1. Meets hard constraints (cost, performance, compliance)
2. Lowest TCO over 3 years ($340K)
3. Acceptable risk profile
4. Fastest path to 20% improvement

**Trade-off accepted:** Latency at 200ms vs. target 100ms, acceptable because [business reason]

## Sensitivity

If [assumption] changes, reassess:
- Cost target becomes $8K → Option A becomes viable
- Traffic doubles → Options A/B need re-evaluation
- EU requirement drops → Option C becomes viable

## Decision Point to Revisit

Re-evaluate in 6 months if:
- Traffic growth exceeds 30%
- New caching technology becomes available
- Cost drivers change (AWS pricing, etc.)
```

---

## When to Do Tradeoff Analysis

**Always when:**
- Competing business objectives (performance, cost, time)
- High-cost decisions (major infrastructure investment)
- Reversible decisions (can change later, but costly)

**Maybe when:**
- Single decision but with hidden costs
- Team debates multiple approaches

**Don't need when:**
- Clear winner (one option better on all dimensions)
- Low-cost choice (easily reversible)

---

## Integration with Architecture Design

**architecture-design.md** → "here's how we'll build it"  
**system-tradeoff-analysis.md** → "here's why we're building it THIS way, not THAT way"

Tradeoff analysis justifies the architecture design.

---

## Success Criteria

✅ Competing objectives are explicitly stated (not just implied)  
✅ Options are quantified (not just opinions)  
✅ Constraints are clear (hard vs. soft)  
✅ TCO includes all costs, not just infrastructure  
✅ Sensitivity analysis shows when recommendation might change  
✅ Reader understands the choice and can revisit it intelligently in 2 years
