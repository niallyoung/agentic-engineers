# Agent Onboarding: Protocol Compliance Checklist

> All agents must complete this checklist before assuming an operational role in
> agentic-engineers. Reference: [ORCHESTRATION-PROTOCOL.md](ORCHESTRATION-PROTOCOL.md)

---

## DELEGATE Understanding

- [ ] Read `orchestration/ORCHESTRATION-PROTOCOL.md` Sections 2–3
- [ ] Understand all required DELEGATE fields (task_id, role, model, effort, estimated_hours, scope, success_criteria, plan, context)
- [ ] Know effort bands: `low` (1-4h), `medium` (5-16h), `high` (17-48h), `max` (49-120h), `epic` (121h+)
- [ ] Can write measurable success_criteria — testable in 30s without reading the implementation (not "good code")
- [ ] Know Groups A/B/C validation will be enforced by pre-commit hook before any commit lands
- [ ] Understand `task_id` format: `YYYY-MM-DD-kebab-case` (e.g. `2026-05-09-add-jwt-validation`)
- [ ] Know that secrets (passwords, tokens, API keys) in a DELEGATE will block the commit

---

## HANDBACK Understanding

- [ ] Read `orchestration/ORCHESTRATION-PROTOCOL.md` Sections 3–5
- [ ] Understand all 12 required HANDBACK fields (task_id, handoff_type, status, deliverables, tests, quality_score, effort_actual, tokens_in, tokens_out, duration_minutes, notes, agent)
- [ ] Know quality score routing: `90-100` = proceed ✅, `80-89` = proceed ✅, `70-79` = Lead Engineer review ⚠️, `60-69` = auto-rework 🔄, `<60` = escalate 🚨
- [ ] Know that the **validator-computed score is authoritative** — agent self-reported `quality_score` is for calibration only
- [ ] Understand `MAX_RETRIES = 2` hard cap; exceeding 2 retries escalates automatically to Principal Engineer
- [ ] Understand the `retry_context` block required on all re-work DELEGATEs (previous score, failure reasons, specific failures)
- [ ] Know task_id retry suffix convention: `-retry-1`, `-retry-2`, `-escalated`

---

## Metrics Understanding

- [ ] Read `orchestration/ORCHESTRATION-PROTOCOL.md` Section 7
- [ ] Know metrics are collected automatically per HANDBACK to `artifacts/metrics/YYYY-MM-DD-{task_id}-metrics.yaml`
- [ ] Understand what `efficiency_score` measures: `quality_score_validator / (tokens_total / 1000)`
- [ ] Understand what `rework_cost_ratio` measures: `tokens_total_all_attempts / tokens_total`
- [ ] Know metrics enable Model Engineer to optimize routing and lower cost over time
- [ ] Know `flag_for_model_engineer: true` triggers when `cost_overrun_pct > 50` or `re_work_count >= 2`
- [ ] Can interpret quality score feedback and layer breakdown (Layer 1/2/3 weights: 40/35/25%)

---

## Enforcement Understanding

- [ ] Pre-commit hook validates all DELEGATE blocks before every commit (Groups A/B/C)
- [ ] Orchestrator runs pre-flight checks internally before emitting any DELEGATE
- [ ] Bad DELEGATEs will be **blocked and returned** with specific error messages — fix the error, do not work around it
- [ ] HANDBACKs require passing tests; coverage must not drop below 70% for modified packages
- [ ] Know all escalation paths (Section 9): when to escalate and to whom

---

## Questions & Escalation

- [ ] Know to ask clarifying questions **before starting** the task, not after completing wrong work
- [ ] Know how to request Principal Engineer escalation: set `status: blocked` in HANDBACK with clear explanation
- [ ] Know who to ask for each question type:
  - **Protocol questions** → Lead Engineer
  - **Metrics & cost optimization** → Model Engineer
  - **Architecture decisions** → Principal Engineer
  - **Quality thresholds** → Quality Engineer
  - **Security concerns** → Security Engineer
  - **Implementation bugs** → Senior Engineer

---

## Sign-Off

I confirm I have reviewed and understand the following before taking on tasks:

- [✓] `ORCHESTRATION-PROTOCOL.md` (Sections 2–7 minimum — estimated 20 min read)
- [✓] Agent responsibilities in Section 10 (my specific role)
- [✓] Examples & troubleshooting in Section 11 (at least 3 examples reviewed)
- [✓] Escalation paths in Section 9 (when and how to escalate)
- [✓] Metrics schema in Section 7 (what gets collected and why)

```
Agent Name:               _______________
Role:                     _______________
Date:                     _______________
Lead Engineer Sign-off:   _______________
```

> **Note:** This checklist is reviewed during onboarding and updated whenever the
> protocol changes. Monthly protocol reviews are conducted by the Principal Engineer.
> If anything is unclear, raise it with the Lead Engineer before starting work.
