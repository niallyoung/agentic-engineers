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

- [ ] Read `docs/PROTOCOL.md` sections on HANDBACK structure and quality gates
- [ ] Understand required HANDBACK fields (task_id, handoff_type, status, output, metrics {quality, tokens, cost, duration_seconds}, effort_actual, notes, agent)
- [ ] Know quality score routing: `0.9-1.0` = proceed ✅, `0.8-0.89` = proceed ✅, `0.7-0.79` = Lead Engineer review ⚠️, `0.6-0.69` = auto-rework 🔄, `<0.6` = escalate 🚨
- [ ] Know that quality metrics are authoritative — metrics.quality is the canonical score (0.0-1.0 float)
- [ ] Understand `MAX_RETRIES = 2` hard cap; exceeding 2 retries escalates automatically to Principal Engineer
- [ ] Understand the `retry_context` block required on all re-work DELEGATEs (previous score, failure reasons, specific failures)
- [ ] Know task_id retry suffix convention: `-retry-1`, `-retry-2`, `-escalated`

---

## Metrics Understanding

- [ ] Read `docs/PROTOCOL.md` section on metrics collection
- [ ] Know metrics are collected automatically per HANDBACK: quality (0.0-1.0), tokens (int), cost (USD), duration_seconds (float)
- [ ] Understand cost-quality tradeoffs via Model Engineer's optimization recommendations
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
