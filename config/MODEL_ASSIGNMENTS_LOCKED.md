# Model Assignments — LOCKED & FINAL

**Date:** 2026-04-24  
**Status:** ✅ IMMUTABLE — Do not change without explicit user request  
**Optimization:** Cost-first, quality-gated, progression-based

---

## Base Role Assignments (DO NOT CHANGE)

| Rank | Role | Model | Effort | Thinking | Cost/Task | Monthly Estimate |
|------|------|-------|--------|----------|-----------|------------------|
| 1 | **Orchestrator** | Haiku 4.5 | Low | ❌ No | $0.03 | $0.90 |
| 2 | **Engineer** | Haiku 4.5 | High | ❌ No | $0.03 | $0.90 |
| 3 | **Quality Engineer** | Sonnet 4.5 | Medium | ❌ No | $0.09 | $2.70 |
| 4 | **Senior Engineer** | Sonnet 4.5 | High | ✅ Yes | $0.09 | $2.70 |
| 5 | **Lead Engineer** | Sonnet 4.6 | High | ✅ Yes | $0.09 | $2.70 |
| 6 | **Principal Engineer** | Opus 4.6 | High | ✅ Yes | $0.15 | $4.50 |
| 7 | **Security Engineer** | Opus 4.7 | Max | ✅ Yes | $0.15 | $4.50 |
| 8 | **Model Engineer** | Sonnet 4.5 | High | ✅ Yes | $0.09 | $2.70 |
| | | | | **TOTAL** | | **~$21.60/mo** |

---

## Model Progression (For Optimization)

**Cost hierarchy (always try cheaper models first):**

```
1. Haiku 4.5       ($0.03/task)  ← Always start here
2. Sonnet 4.5      ($0.09/task)  ← If Haiku fails quality gate
3. Sonnet 4.6      ($0.09/task)  ← Same cost as 4.5, try if 4.5 insufficient
4. Opus 4.6        ($0.15/task)  ← If Sonnet fails
5. Opus 4.7        ($0.15/task)  ← Last resort
```

---

## Effort Levels (Tunable Parameter)

Effort affects token burn and thinking capability:

| Level | Characteristics | Cost Impact | When to Try |
|-------|-----------------|------------|-------------|
| **Low** | Minimal compute, simple output | -30% | Rare; only if others overkill |
| **Medium** | Balanced reasoning, moderate tokens | -15% | Try first with cheaper models |
| **High** | Full reasoning, standard tokens | 0% (baseline) | Current baseline for most roles |
| **Max** | Full extended thinking, max tokens | +30% | Only if quality too low |

---

## Thinking Flag (Tunable Parameter)

Extended thinking enables more complex reasoning at cost of higher token burn:

| Setting | Characteristics | Cost Impact | When to Try |
|---------|-----------------|------------|-------------|
| **No** | Standard inference, fast | -20% | Try first (cheaper) |
| **Yes** | Extended thinking, slower | +40% | If quality too low with thinking=no |

---

## Optimization Strategy (Algorithm)

**PRIMARY METRIC: Cost. Quality is gating constraint.**

### Quality Gate
```
min_quality = best_quality_observed - 5 points

Any combo that achieves >= min_quality PASSES.
Any combo that achieves < min_quality FAILS.
```

### Progression Walk
```
For each task type (with n >= 5 samples):

FOR model IN [Haiku, Sonnet4.5, Sonnet4.6, Opus4.6, Opus4.7]:
  FOR effort IN [medium, high, max]:
    FOR thinking IN [no, yes]:
      Test: model + effort + thinking
      
      IF avg_quality >= min_quality:
        ✅ RECOMMEND (stop here, found cheapest viable)
      ELSE:
        ❌ Try next combo
```

### Decision Rule
```
ALWAYS pick the FIRST combo in progression that passes quality gate.
Never test remaining models/combos once any passes.
Cost wins. Always.
```

---

## Examples of Model Engineer Recommendations

### Example 1: Success at Cheaper Model
```
Current assignment: Senior Engineer, Sonnet 4.5, effort=high, thinking=yes
Task type: Complex refactoring (5 samples)

Testing progression:
  ❌ Haiku 4.5, effort=medium, thinking=no → quality 87 (min 90)
  ❌ Haiku 4.5, effort=high, thinking=no → quality 88
  ❌ Haiku 4.5, effort=max, thinking=yes → quality 89
  ✅ Sonnet 4.5, effort=medium, thinking=no → quality 91 (min 90)

Recommendation: Sonnet 4.5, effort=medium, thinking=no
Cost savings: -$0.015/task (vs current $0.09)
```

### Example 2: Need Higher Model
```
Current: Quality Engineer, Sonnet 4.5, effort=medium, thinking=no
Task type: Code review (5 samples, complex code)

Testing progression:
  ❌ Haiku 4.5, effort=medium, thinking=no → quality 84 (min 90)
  ❌ Haiku 4.5, effort=high, thinking=no → quality 85
  ❌ Haiku 4.5, effort=max, thinking=yes → quality 88
  ❌ Sonnet 4.5, effort=medium, thinking=no → quality 89
  ✅ Sonnet 4.5, effort=high, thinking=no → quality 90

Recommendation: Sonnet 4.5, effort=high, thinking=no
(Same model/cost, increased effort to meet quality gate)
```

### Example 3: Already Optimal
```
Current: Lead Engineer, Sonnet 4.6, effort=high, thinking=yes
Task type: Architecture review (10+ samples)

Testing progression:
  ❌ All Haiku combos → quality max 87 (min 90)
  ❌ Sonnet 4.5, medium/no → quality 88
  ❌ Sonnet 4.5, high/no → quality 89
  ✅ Sonnet 4.6, medium/no → quality 91

Recommendation: Sonnet 4.6, effort=medium, thinking=no
Cost savings: -$0.018/task (vs current with thinking=yes)
```

---

## Changes Model Engineer Can Recommend

✅ **ALLOWED:**
- Model: Haiku 4.5 ↔ Sonnet 4.5 ↔ Sonnet 4.6 ↔ Opus 4.6 ↔ Opus 4.7 (down/up progression)
- Effort: low ↔ medium ↔ high ↔ max
- Thinking: yes ↔ no
- **ALWAYS downgrade if quality acceptable** (cost-first)

❌ **NOT ALLOWED:**
- Change role assignments (Orchestrator still = Haiku, etc.)
- Introduce new model versions outside progression
- Recommend Haiku 3.5, Sonnet 3.x, Opus older versions
- Violate quality gate (min_quality threshold)

---

## Cost Summary

**Baseline (current assignments):**
- 60% Haiku 4.5 @ $0.03 = $0.90/mo
- 35% Sonnet (4.5/4.6) @ $0.09 = $5.40/mo
- 5% Opus (4.6/4.7) @ $0.15 = $4.50/mo
- **Total: ~$21.60/month**

**Optimization potential:** If all roles downgrade to cheaper combos:
- Haiku 4.5 (wider usage)
- Sonnet 4.5 + effort=medium + thinking=no
- Opus 4.6 + effort=high + thinking=no (for critical roles only)
- **Potential: ~$15-18/month** (25-30% savings)

---

## Implementation Checklist

- ✅ Base models locked in AGENTS.md
- ✅ Model progression defined (Haiku → Sonnet 4.5 → 4.6 → Opus 4.6 → 4.7)
- ✅ Algorithm: walk progression, stop at first quality pass
- ✅ Quality gate: best_quality - 5 points
- ✅ Cost-first: always pick cheapest viable
- ✅ Effort/thinking co-optimized (not secondary)
- ✅ Model Engineer skill updated
- ✅ All documentation consistent in agentic-engineers/

---

## Status

🔒 **LOCKED.** Do not change base assignments without explicit user request.  
📊 **READY.** Start running tasks; Model Engineer will optimize based on metrics.  
💰 **COST-FIRST.** Every recommendation prioritizes token burn reduction.

---

**Last updated:** 2026-04-24  
**Next review:** After 30-50 tasks collected (sufficient metrics for Model Engineer optimization)
