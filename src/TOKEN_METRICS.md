# Token Metrics Specification

> **Purpose:** Track cost, efficiency, and model usage across all agent calls.  
> **Owned by:** Model Engineer role — collects, analyses, and reports metrics.  
> **Storage:** `~/.copilot/metrics/daily/YYYY-MM-DD.md` (daily files, never in-repo).

---

## Why Track Token Metrics

1. **Cost control** — Know what each role costs before it becomes a problem
2. **Model calibration** — Identify over-specced roles (Opus used where Haiku would do)
3. **Efficiency trends** — Spot degrading agents (token usage creeping up)
4. **Feedback loop** — Model Engineer uses metrics to improve future routing

---

## Metric Collection Points

Metrics are recorded in three places:

| Source | When | What |
|--------|------|------|
| HANDBACK YAML | On task completion | Per-task: tokens_used, duration_ms, quality_score, model_used |
| Orchestrator poll | After each routing decision | Route taken, estimated vs. actual cost |
| Weekly summary | Every Monday | Aggregated role-level efficiency, delegation ratio |

---

## Daily Metrics File Format

**Path:** `~/.copilot/metrics/daily/YYYY-MM-DD.md`

```markdown
# Token Metrics — YYYY-MM-DD

## Summary

| Metric | Value |
|--------|-------|
| Total sessions | N |
| Total agent calls | N |
| Total estimated cost | $N.NN |
| Total actual tokens | N |

## By Role

| Role | Calls | Tokens Used | Est. Cost | Avg Quality Score | Avg Efficiency |
|------|-------|-------------|-----------|-------------------|----------------|
| Orchestrator | N | N | $N.NN | N/A | N.NN |
| Engineer | N | N | $N.NN | N.NN | N.NN |
| Model Engineer | N | N | $N.NN | N/A | N.NN |
| Quality Engineer | N | N | $N.NN | N.NN | N.NN |
| Lead Engineer | N | N | $N.NN | N.NN | N.NN |
| Senior Engineer | N | N | $N.NN | N.NN | N.NN |
| Principal Engineer | N | N | $N.NN | N.NN | N.NN |
| Security Engineer | N | N | $N.NN | N.NN | N.NN |

## Delegation Ratio

| Tier | Calls | % of Total |
|------|-------|-----------|
| Cheap (Haiku: Orchestrator + Engineer) | N | N% |
| Medium (Sonnet: ME + QE + Lead + Senior) | N | N% |
| Premium (Opus: Principal + Security) | N | N% |

## Efficiency Highlights

- Most efficient role today: [Role] (efficiency ratio: N.NN)
- Least efficient role today: [Role] (efficiency ratio: N.NN)
- Tasks that overran budget: [list TASK-IDs or "none"]

## Notes

<!-- Observations: unusual spikes, new patterns, cost anomalies -->
```

---

## Weekly Summary Format

**Path:** `~/.copilot/metrics/weekly/YYYY-WNN.md` (ISO week number)

Generated every Monday by the Orchestrator using `monitoring/tokenadvisor-scheduler.md`.

```markdown
# Weekly Token Metrics — Week NN, YYYY

## Totals

| Metric | This Week | Last Week | Δ |
|--------|-----------|-----------|---|
| Agent calls | N | N | ±N |
| Estimated cost | $N.NN | $N.NN | ±$N.NN |
| Cheap tier % | N% | N% | ±N% |
| Premium tier % | N% | N% | ±N% |
| Avg quality score | N.NN | N.NN | ±N.NN |

## Model Engineer Recommendations Applied

| Recommendation | Applied? | Impact |
|----------------|----------|--------|
| [recommendation text] | Yes/No | [observed cost/quality change] |

## Efficiency Trend

[Narrative: improving / stable / degrading, and why]

## Recommended Actions for Next Week

1. [Specific recommendation with rationale]
2. [Specific recommendation with rationale]
```

---

## Monthly Summary Format

**Path:** `~/.copilot/metrics/monthly/YYYY-MM.md`

Generated on the 1st of each month.

```markdown
# Monthly Token Metrics — YYYY-MM

## Month Overview

| Metric | Value |
|--------|-------|
| Total agent calls | N |
| Total estimated cost | $N.NN |
| Avg daily cost | $N.NN |
| Peak day | YYYY-MM-DD ($N.NN) |
| Lowest day | YYYY-MM-DD ($N.NN) |

## Role Breakdown (Month Total)

| Role | Calls | % Total | Avg Quality | Cost |
|------|-------|---------|-------------|------|
| ... | ... | ... | ... | ... |

## Efficiency Progress

[Month-over-month comparison: are we getting more done for less?]

## Cost Targets vs Actuals

| Target | Goal | Actual | Status |
|--------|------|--------|--------|
| Cheap tier ≥ 70% of calls | 70% | N% | ✅/❌ |
| Premium tier ≤ 10% of calls | 10% | N% | ✅/❌ |
| Avg quality score ≥ 0.80 | 0.80 | N.NN | ✅/❌ |
| Efficiency ratio ≥ 0.60 | 0.60 | N.NN | ✅/❌ |
```

---

## HANDBACK Metrics Fields

Every HANDBACK YAML must include a `metrics` block:

```yaml
metrics:
  tokens_used: 5840           # actual tokens consumed (input + output)
  tokens_estimated: 8000      # budget from the DELEGATE
  efficiency_ratio: 0.73      # tokens_used / tokens_estimated
  model_used: claude-sonnet-4.6
  duration_ms: 42000          # wall-clock time
  quality_score: 0.88         # 0.0–1.0, self-assessed by agent
```

### Efficiency Ratio Interpretation

| Ratio | Interpretation | Model Engineer Action |
|-------|---------------|----------------------|
| < 0.40 | Task was much smaller than estimated | Suggest downgrade or lower budget |
| 0.40–0.60 | Underutilised — model may be over-specced | Flag for review; suggest downgrade |
| 0.60–0.85 | Healthy utilisation | No action — keep same model |
| 0.85–1.00 | Near-capacity — model well-matched | Monitor; may need upgrade if trend continues |
| > 1.00 | Budget overrun | Investigate; suggest larger budget or scope reduction |

### Quality Score Guidelines

Agents self-assess quality_score using this rubric:

| Score | Meaning |
|-------|---------|
| 0.9–1.0 | All acceptance criteria met; CI passes; clean, reviewable code |
| 0.8–0.9 | AC met; minor rough edges (non-blocking comments) |
| 0.7–0.8 | AC mostly met; one or two outstanding items documented |
| 0.6–0.7 | Partial — some AC not met; needs follow-up task |
| < 0.6 | Significant gaps; should not be marked COMPLETE |

---

## Efficiency Targets

| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| Cheap model usage (Haiku) | ≥ 70% of agent calls | < 60% → investigate |
| Premium model usage (Opus) | ≤ 10% of agent calls | > 20% → escalate to ME |
| Average quality score | ≥ 0.80 | < 0.70 → quality gate failure |
| Average efficiency ratio | ≥ 0.60 | < 0.45 → over-specced models |
| Budget overruns (ratio > 1.0) | ≤ 5% of tasks | > 15% → review budget estimation |

---

## Model Engineer Feedback Loop

After each Quality Engineer HANDBACK, the Model Engineer runs:

```
1. Read HANDBACK.metrics (tokens, efficiency, quality, model)
2. Compare against task_type baseline (from metrics-etl)
3. Classify: DOWNGRADE / KEEP / UPGRADE / EXPAND_BUDGET
4. Write recommendation to ~/.copilot/metrics/recommendations/TASK-NNN.md
5. Orchestrator reads recommendations before next routing decision
```

### Recommendation Format

```markdown
# Model Engineer Recommendation — TASK-NNN

## Analysis
- Task type: [classification]
- Model used: claude-sonnet-4.6
- Efficiency ratio: 0.48
- Quality score: 0.85

## Recommendation
**DOWNGRADE** to claude-haiku-4.5 for similar tasks.

## Reasoning
Efficiency ratio of 0.48 indicates the Sonnet model had significant headroom.
Quality was good (0.85), confirming the task did not require higher reasoning.
Haiku would deliver similar quality at 67% lower cost.

## Confidence
0.82 — high confidence (5 similar tasks in history all showed same pattern)

## Applied By
[ ] Orchestrator — accept / reject this recommendation
```

---

## Cost Reference

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Typical task cost |
|-------|-----------------------|------------------------|-------------------|
| claude-haiku-4.5 | $0.80 | $4.00 | $0.03–0.05 |
| claude-sonnet-4.6 | $3.00 | $15.00 | $0.09 |
 | claude-opus-4-6 | $15.00 | $75.00 | $0.15 |
 | claude-opus-4.8 | $15.00 | $75.00 | $0.15 |

> Prices are approximate and subject to Anthropic pricing changes. Verify at [anthropic.com/pricing](https://www.anthropic.com/pricing).
