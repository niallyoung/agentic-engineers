# Cost-Quality Matrix

**Status:** Phase 5.2 baseline (2026-06-06).
**Inputs:** Phase 4.1 / 4.2 / 4.3 task metrics; provider cost multipliers from `src/orchestration/cost/cost_aware_router.py`.

This document gives engineers and the Orchestrator a one-page reference for
**which model to pick for which task type**, with the underlying cost vs.
quality data that justifies the choice.

---

## 1. Model Cost & Quality Baselines

Multipliers are relative to Sonnet (1.00x). Quality baselines are
0–100 scores derived from in-repo eval harness + Phase 4 HANDBACKs.

| Model         | Cost mult | Quality | Best for                                          |
| ------------- | --------- | ------- | ------------------------------------------------- |
| `claude-haiku-4.5`  | 0.33x | 82      | Well-scoped edits; pure routing; metric reads     |
| `claude-sonnet-5`   | 1.00x | 95      | Review, QE, complex impl, cost analysis. Same $3/$15 per MTok as 4.6, but ~30% more tokens for the same text — a task costs ~30% more at an unchanged rate |
| `claude-opus-4.7`   | 3.00x | 97.5    | Architecture, security, escalation                |
| `claude-opus-5`     | 3.00x | 98.5    | Architecture default; $5/$25 per MTok             |
| `claude-opus-4.8`   | 3.00x | 98      | Security default (pinned) — non-downgradable per policy |
| `claude-fable-5`    | 6.00x | 99      | Security Engineer defensive-only alternative (effort <= medium); 2x opus per token — capability upgrade, never a cost saving |

Source: `src/orchestration/cost/cost_aware_router.py` (constants).

---

## 2. Phase 4 Observed Performance

| Phase | Role          | Model  | Tokens | Quality | Notes                                      |
| ----- | ------------- | ------ | ------ | ------- | ------------------------------------------ |
| 4.1   | Engineer      | Haiku  | 1,200  | 97/100  | Bug fix, well-scoped                       |
| 4.2   | Engineer      | Haiku  | 800    | 96/100  | Simple refactor                            |
| 4.3   | Lead Engineer | Sonnet | 2,000  | 98/100  | Comprehensive code-review audit            |

**Takeaway:** Haiku consistently hits ≥95 quality on scoped, planned work.
Sonnet is justified when the task requires synthesis across many files
(audits, design analysis) — not by default.

---

## 3. Decision Matrix (canonical)

Implemented in `src/orchestration/routing/model_router.py`. Rules evaluated
in priority order (lowest rank wins).

| Priority | Task signal                                          | Role                  | Model  | Effort | Budget |
| -------- | ---------------------------------------------------- | --------------------- | ------ | ------ | ------ |
| 10       | security / threat-model / `security_scope` set       | `security_engineer`   | Opus   | max    | 5,000  |
| 20       | architecture / cross-service / Principal approval    | `principal_engineer`  | Opus   | high   | 5,000  |
| 30       | code review / audit / PR review                      | `lead_engineer`       | Sonnet | high   | 2,500  |
| 40       | quality gate / QE review                             | `quality_engineer`    | Sonnet | medium | 1,000  |
| 50       | cost analysis / model recommendation                 | `model_engineer`      | Sonnet | medium | 1,500  |
| 60       | complex / unscoped / `complexity=high`               | `senior_engineer`     | Sonnet | high   | 2,500  |
| 70       | orchestration / routing only                         | `general_orchestrator`| Haiku  | high   | 500    |
| 999      | **fallback** — well-scoped, planned work             | `engineer`            | Haiku  | high   | 1,500  |

Budgets resolved from `src/config/token-budgets.yaml`.

---

## 4. Cost-Quality Tradeoff Bands

Heuristic guidance for ad-hoc model selection when the matrix above doesn't
clearly apply:

| Quality requirement | Tokens budget   | Pick                  |
| ------------------- | --------------- | --------------------- |
| ≥ 95, security      | unbounded       | Opus (always)         |
| ≥ 95, code review   | ≤ 2,500         | Sonnet                |
| ≥ 90, planned impl  | ≤ 1,500         | **Haiku** (preferred) |
| ≥ 85, routing/glue  | ≤ 500           | Haiku                 |
| ≥ 90, unscoped impl | ≤ 2,500         | Sonnet                |

The Haiku band is the largest cost lever — every task incorrectly routed
to Sonnet costs ~3x. Conversely, routing security or architectural work
to Haiku is a quality risk that **always** loses on rework cost.

---

## 5. Recommendations

1. **Default to Haiku** for any DELEGATE that ships with a step-by-step plan
   and bounded scope. Phase 4 shows 96–97 quality at 0.33x cost.
2. **Promote to Sonnet** only when the task is one of: code review, complex
   diagnosis, cost analysis, or unscoped implementation.
3. **Reserve Opus** for security and architecture. Never auto-downgrade.
4. **Monitor escalations** via `monitor_budgets.py` — a sustained rise in
   `escalate` events for a role indicates the budget needs revisiting (or
   the routing rule is too aggressive).
5. **Re-baseline quarterly.** Provider pricing and model capability drift;
   the matrix is a living artifact.

---

## 6. Related artifacts

- `src/config/token-budgets.yaml` — per-role ceilings & escalation thresholds
- `src/orchestration/routing/model_router.py` — executable decision matrix
- `src/skills/cost-aggregation/scripts/monitor_budgets.py` — per-task monitor
- `src/skills/cost-aggregation/scripts/cost_dashboard.py` — rollup CLI
- `src/orchestration/cost/cost_aware_router.py` — fine-grained candidate scorer
- `CONTRIBUTING.md` § "Cost & Budget Reports" — how to read these outputs
