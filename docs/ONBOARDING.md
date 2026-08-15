# Agent Onboarding: Protocol Compliance Checklist

> All agents must complete this checklist before assuming an operational role in
> agentic-engineers. Reference: [PROTOCOL.md](PROTOCOL.md)

---

## DELEGATE Understanding

- [ ] Read `docs/PROTOCOL.md` sections 2-3 on DELEGATE structure and validation
- [ ] Understand all required DELEGATE fields: `task_id`, `skill`, `agent`, `scope`, `success_criteria`, `plan`, `context`, `spec_version`, `handoff_type`
- [ ] Can write measurable success_criteria — testable without reading the implementation
- [ ] Understand `task_id` format: kebab-case, 3-50 chars (date prefix optional, e.g. `my-task` or `2026-05-09-my-task`)
- [ ] Know that secrets (passwords, tokens, API keys) in a DELEGATE will block the commit

---

## HANDBACK Understanding

- [ ] Read `docs/PROTOCOL.md` sections 2 and 4 on HANDBACK structure and quality assessment
- [ ] Understand required HANDBACK fields: `task_id`, `handoff_type`, `status`, `output`, `metrics`, `spec_version`
- [ ] Know that metrics.quality (0.0-1.0) is self-reported by the agent and may be reviewed by Quality Engineer
- [ ] Know that status `success` means done; `partial` means rework is needed; `blocked`/`escalate` need higher-tier decision
- [ ] Understand that quality assessment is by convention (Quality Engineer review), not by an automated formula

---

## Metrics Understanding

- [ ] Read `docs/PROTOCOL.md` section 2.2 on metrics (required sub-fields: quality, tokens, cost, duration_seconds)
- [ ] Know metrics are reported per HANDBACK: quality (0.0-1.0), tokens (int), cost (USD), duration_seconds (float)
- [ ] Understand that metrics feed into Model Engineer's cost-quality optimization recommendations

---

## Enforcement Understanding

- [ ] Pre-commit hook validates all DELEGATE blocks before every commit
- [ ] Orchestrator runs pre-flight checks internally before emitting any DELEGATE
- [ ] Bad DELEGATEs will be **blocked and returned** with specific error messages — fix the error, do not work around it
- [ ] HANDBACKs require passing tests; coverage must not drop below 85% for modified packages
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

- [✓] `docs/PROTOCOL.md` (Sections 2–5 minimum — estimated 20 min read)
- [✓] My agent role in `src/AGENTS.md`
- [✓] Examples in `docs/CORE-PROTOCOL-QUICKSTART.md` (at least one example reviewed)
- [✓] Escalation paths in `docs/PROTOCOL.md` Section 5
- [✓] How metrics are reported in `docs/PROTOCOL.md` Section 2.2

> **Note:** This checklist is reviewed during onboarding and updated whenever the
> protocol changes. If anything is unclear, raise it with your Lead Engineer before starting work.
