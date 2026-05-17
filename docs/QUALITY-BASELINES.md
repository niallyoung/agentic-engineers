# Quality Baselines — Phase I

Established: 2026-05-17  
Status: Active  
Owner: Quality Engineer

---

## Overview

This document defines the quality baselines for the agentic-engineers framework.
Baselines are the minimum acceptable quality scores for each task type, used by
`ThresholdEnforcer` to gate task completion and trigger escalations.

---

## Baseline Thresholds by Task Type

| Task Type     | Minimum Score | Rationale                                              |
|---------------|:-------------:|--------------------------------------------------------|
| code          | 90            | Production code must be high quality; rework is costly |
| test          | 90            | Tests are the safety net; low quality = false safety   |
| documentation | 85            | Docs degrade slower; some incompleteness acceptable    |
| performance   | 85            | Perf regressions are caught by benchmarks separately   |
| security      | 95            | Security failures have outsized blast radius           |
| default       | 85            | Catch-all for unclassified task types                  |

---

## Escalation Policy

| Condition                              | Action                              |
|----------------------------------------|-------------------------------------|
| Score ≥ threshold                      | PASS — proceed to done/             |
| Score < threshold, gap < 10 pts        | WARNING — request rework (max 2×)   |
| Score < threshold, gap ≥ 10 pts        | ERROR — escalate to Lead Engineer   |
| Security task, score < 95             | CRITICAL — escalate immediately     |

---

## Metric Definitions

### Code Quality (score 0–100)
- **Coverage**: test coverage % (weight 30%)
- **Complexity**: cyclomatic complexity (weight 20%)
- **Style**: linting / formatting (weight 20%)
- **Correctness**: spec compliance (weight 30%)

### Test Quality (score 0–100)
- **Pass rate**: % tests passing (weight 40%)
- **Coverage**: branch + line coverage (weight 30%)
- **Performance**: test suite runtime (weight 15%)
- **Edge cases**: boundary conditions covered (weight 15%)

### Documentation Quality (score 0–100)
- **Completeness**: all public APIs documented (weight 40%)
- **Accuracy**: docs match implementation (weight 40%)
- **Clarity**: readability score (weight 20%)

### Performance Quality (score 0–100)
- **Latency**: p99 latency vs baseline (weight 40%)
- **Throughput**: requests/sec vs baseline (weight 30%)
- **Overhead**: memory/CPU overhead (weight 30%)

---

## Trend Monitoring

Moving averages are computed over two windows:

| Window  | Purpose                              |
|---------|--------------------------------------|
| 7-day   | Current performance indicator        |
| 30-day  | Baseline for trend direction         |

**Trend classification:**
- **Improving**: 7-day avg ≥ 30-day avg + 2.0 points
- **Degrading**: 7-day avg ≤ 30-day avg − 2.0 points
- **Stable**: within ±2.0 points

**Alert trigger**: any degrading trend generates an alert in the dashboard.

---

## Feedback Cycle Stages

Each completed task triggers a five-stage feedback cycle:

1. **task_execution** — task runs (Engineer/Senior Engineer)
2. **quality_assessment** — Quality Engineer scores the output
3. **feedback_collection** — QE HANDBACK `model_assessment` captured
4. **trend_analysis** — TrendMonitor records new data point
5. **routing_improvement** — Model Engineer recommendation applied

Cycle completion rate target: **≥ 95%** of tasks complete all five stages.

---

## Baseline Rationale

These baselines were set based on:
- Industry standard for production software (90% code coverage)
- Security-first posture (95% for security tasks)
- Practical tolerance for documentation drift (85%)
- Observed quality scores from Phase H (median: 88, p10: 82)

Baselines should be reviewed quarterly and adjusted based on:
- Model Engineer trend analysis
- Observed compliance rates
- Escalation frequency

---

## Compliance Targets

| Metric                  | Target  |
|-------------------------|---------|
| Overall compliance rate | ≥ 90%   |
| Escalation rate         | ≤ 5%    |
| Cycle completion rate   | ≥ 95%   |
| Degrading task types    | 0       |

---

## Change Log

| Date       | Change                              | Author          |
|------------|-------------------------------------|-----------------|
| 2026-05-17 | Initial baselines established       | Quality Engineer |
