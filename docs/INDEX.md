# Documentation Index

**Last Updated:** 2025-05-24  
**Active docs:** 21 files at root level  
**Archived docs:** 46 files in `docs/archive/` (historical, design, reference)  
**Total documentation:** 67 markdown files

> **Note:** This index lists only active documentation. For archived files (design docs, analysis, historical), see [docs/archive/INDEX.md](archive/INDEX.md).

---

## 🚀 Start Here

| Document | Purpose | Read Time |
|----------|---------|-----------|
| [README.md](../README.md) | Project overview, quick start, architecture | 10 min |
| [ONBOARDING.md](ONBOARDING.md) | New developer onboarding | 15 min |
| [AGENTS.md](AGENTS.md) | 8 roles + routing decision tree | 15 min |

---

## 📋 Core Protocol & Architecture

| Document | Purpose |
|----------|---------|
| [SPEC.md](SPEC.md) | **Source of truth** — implementation specification |
| [PROTOCOL.md](PROTOCOL.md) | Queue protocol documentation |
| [HANDOFF.md](HANDOFF.md) | DELEGATE/HANDBACK format + examples |
| [QUEUE-PROTOCOL.md](QUEUE-PROTOCOL.md) | Queue mechanics + state machine |
| [SYSTEM.md](SYSTEM.md) | System architecture and operations |
| [WORKFLOW.md](WORKFLOW.md) | SDLC lifecycle and enforcement gates |

---

## 🛠️ Core Concepts & Implementation

| Document | Purpose |
|----------|---------|
| [SKILLS.md](SKILLS.md) | Skills overview and creation |
| [QUALITY.md](QUALITY.md) | Quality gates and validation |
| [ENTRYPOINT.md](ENTRYPOINT.md) | Standard execution model |
| [DELEGATE-HANDBACK-QUALITY-GATES.md](DELEGATE-HANDBACK-QUALITY-GATES.md) | Quality gate implementation |
| [SELF-REFERENTIAL-WORKFLOW.md](SELF-REFERENTIAL-WORKFLOW.md) | Self-improvement patterns |
| [SPAN-CAPTURE-INTEGRATION.md](SPAN-CAPTURE-INTEGRATION.md) | OpenTelemetry integration |

---

## 🚀 Getting Started

| Document | Purpose |
|----------|---------|
| [CORE-PROTOCOL-QUICKSTART.md](CORE-PROTOCOL-QUICKSTART.md) | Protocol quick start |
| [config-standard.md](config-standard.md) | Configuration standards |

**For detailed setup guides:** See `archive/` for archived installation docs (OpenCode, Claude, MSMTP setup)

---

## 📊 Token Visibility & Cost

| Document | Purpose |
|----------|---------|
| [docs/TOKEN-COST-MONITORING.md](TOKEN-COST-MONITORING.md) | Full monitoring reference |
| [docs/TOKEN-USAGE-TRACKING.md](TOKEN-USAGE-TRACKING.md) | Token accounting details |
| [docs/TOKEN-VISIBILITY-BEST-PRACTICES.md](TOKEN-VISIBILITY-BEST-PRACTICES.md) | Best practices |
| [docs/TOKEN-COST-MONITORING-QUICK-REFERENCE.md](TOKEN-COST-MONITORING-QUICK-REFERENCE.md) | Quick reference card |
| [docs/USAGE-BUDGET-MANAGER.md](USAGE-BUDGET-MANAGER.md) | Budget manager reference |
| [docs/USAGE-BUDGET-INTEGRATION.md](USAGE-BUDGET-INTEGRATION.md) | Budget integration with Orchestrator |
| [docs/COST-ATTRIBUTION.md](COST-ATTRIBUTION.md) | Cost attribution per agent/role |
| [docs/OPENCODE-TOKEN-VISIBILITY-SOLUTION.md](OPENCODE-TOKEN-VISIBILITY-SOLUTION.md) | Token visibility solution design |

---

## 🔒 SDLC Enforcement

| Document | Purpose |
|----------|---------|
| [docs/SDLC-HOOKS.md](SDLC-HOOKS.md) | Git hooks reference (pre-commit, commit-msg, pre-push) |
| [docs/WORKFLOW.md](WORKFLOW.md) | Full SDLC lifecycle with 7 enforcement gates |
| [docs/BYPASS-PROCEDURES.md](BYPASS-PROCEDURES.md) | Emergency bypass procedures |
| [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Troubleshooting guide (30+ scenarios) |

---

## 🏗️ Architecture

| Document | Purpose |
|----------|---------|
| [docs/AGENTIC-ENGINEERS-ARCHITECTURE-DIAGRAMS.md](AGENTIC-ENGINEERS-ARCHITECTURE-DIAGRAMS.md) | Architecture diagrams |
| [docs/REPOSITORY-STRUCTURE.md](REPOSITORY-STRUCTURE.md) | Full directory reference |
| [docs/SYSTEM.md](SYSTEM.md) | System overview |
| [docs/ENTRYPOINT.md](ENTRYPOINT.md) | Standard execution model |
| [docs/LOGGING-QUEUE-ARCHITECTURE.md](LOGGING-QUEUE-ARCHITECTURE.md) | Logging and queue architecture |
| [docs/decisions/](decisions/) | Architecture Decision Records (ADRs) |

---

## 🔄 Parallel Delegation

| Document | Purpose |
|----------|---------|
| [docs/PARALLEL-DELEGATION-GUIDE.md](PARALLEL-DELEGATION-GUIDE.md) | Full parallel delegation guide |
| [docs/PARALLEL-DELEGATION-TROUBLESHOOTING.md](PARALLEL-DELEGATION-TROUBLESHOOTING.md) | Troubleshooting parallel tasks |
| [docs/CONCURRENT-SUBAGENT-CAPACITY.md](CONCURRENT-SUBAGENT-CAPACITY.md) | Subagent capacity analysis |
| [docs/CONCURRENT-SUBAGENT-TESTING-GUIDE.md](CONCURRENT-SUBAGENT-TESTING-GUIDE.md) | Testing concurrent agents |
| [docs/MAX-CONCURRENT-SUBAGENTS.md](MAX-CONCURRENT-SUBAGENTS.md) | Concurrency limits |

---

## 🔍 Shadow Mode & Dry Run

| Document | Purpose |
|----------|---------|
| [docs/SHADOW_MODE.md](SHADOW_MODE.md) | Shadow mode overview |
| [docs/SHADOW_MODE_RUNBOOK.md](SHADOW_MODE_RUNBOOK.md) | Shadow mode runbook |
| [docs/DRY_RUN_MODE.md](DRY_RUN_MODE.md) | Dry run mode reference |

---

## 🚀 Production & Operations

| Document | Purpose |
|----------|---------|
| [docs/PHASE-3-DEPLOYMENT-PLAYBOOK.md](PHASE-3-DEPLOYMENT-PLAYBOOK.md) | Deployment playbook |
| [docs/PHASE-3-PRODUCTION-READINESS-CHECKLIST.md](PHASE-3-PRODUCTION-READINESS-CHECKLIST.md) | Production readiness checklist |
| [docs/PROMETHEUS_EXPORTER_GUIDE.md](PROMETHEUS_EXPORTER_GUIDE.md) | Prometheus metrics export |
| [docs/cloudwatch-queries.md](cloudwatch-queries.md) | CloudWatch query reference |
| [docs/cicd-monitoring.md](cicd-monitoring.md) | CI/CD monitoring |
| [docs/operations/](operations/) | Operational runbooks |
| [docs/runbooks/](runbooks/) | Incident runbooks |

---

## 📐 Standards & Compliance

| Document | Purpose |
|----------|---------|
| [docs/STANDARDS-INDEX.md](STANDARDS-INDEX.md) | Standards navigation guide |
| [docs/STANDARDS-ALIGNMENT.md](STANDARDS-ALIGNMENT.md) | Standards alignment analysis |
| [docs/STANDARDS-COMPLIANCE-MATRIX.md](STANDARDS-COMPLIANCE-MATRIX.md) | Compliance matrix |
| [docs/STANDARDS-ROADMAP.md](STANDARDS-ROADMAP.md) | Standards implementation roadmap |
| [docs/LINUX-FOUNDATION-STANDARD.md](LINUX-FOUNDATION-STANDARD.md) | Linux Foundation standard |
| [docs/quality-standards.md](quality-standards.md) | Quality standards |

---

## 🔬 Quality Gates

| Document | Purpose |
|----------|---------|
| [docs/DELEGATE-HANDBACK-QUALITY-GATES.md](DELEGATE-HANDBACK-QUALITY-GATES.md) | Quality gates detail |
| [docs/QUALITY-GATES-QUICK-REFERENCE.md](QUALITY-GATES-QUICK-REFERENCE.md) | Quick reference |
| [docs/QUALITY-GATE-TEST-FRAMEWORK.md](QUALITY-GATE-TEST-FRAMEWORK.md) | Test framework |
| [docs/SPEC-DRIVEN-QUALITY-GATE.md](SPEC-DRIVEN-QUALITY-GATE.md) | SPEC-driven validation |
| [docs/SPEC-VALIDATION-FRAMEWORK.md](SPEC-VALIDATION-FRAMEWORK.md) | Validation framework |

---

## 🤖 Agent-Specific

| Document | Purpose |
|----------|---------|
| [docs/QUALITY-ENGINEER-DESIGN.md](QUALITY-ENGINEER-DESIGN.md) | Quality Engineer design |
| [docs/AUTOMATIC-INVOCATION.md](AUTOMATIC-INVOCATION.md) | Automatic agent invocation |
| [docs/SUBTASK-WORKFLOWS.md](SUBTASK-WORKFLOWS.md) | Subtask workflow patterns |
| [docs/SELF-REFERENTIAL-WORKFLOW.md](SELF-REFERENTIAL-WORKFLOW.md) | Self-referential improvement |
| [docs/FEEDBACK-LOOPS.md](FEEDBACK-LOOPS.md) | Feedback loop documentation |

---

## 🛠️ Skills

| Document | Purpose |
|----------|---------|
| [docs/SKILLS.md](SKILLS.md) | Skills overview |
| [docs/SKILLS-OVERVIEW.md](SKILLS-OVERVIEW.md) | Detailed skills overview |
| [docs/SKILL-SPECS.md](SKILL-SPECS.md) | Skill specifications |
| [docs/TDD-SKILL.md](TDD-SKILL.md) | TDD skill reference |

---

## 🔬 Research & Analysis

| Document | Purpose |
|----------|---------|
| [docs/FRAMEWORKS/](FRAMEWORKS/) | AI framework research (45 frameworks) |
| [docs/HARNESS-FINAL-SUMMARY.md](HARNESS-FINAL-SUMMARY.md) | Harness comparison summary |
| [docs/HARNESS-CONSISTENCY-FRAMEWORK.md](HARNESS-CONSISTENCY-FRAMEWORK.md) | Harness consistency analysis |

---

## 📁 Archive

| Location | Contents |
|----------|---------|
| [docs/archive/](archive/) | Archived documentation |
| [docs/archive/research-2026-05/](archive/research-2026-05/) | Framework research archive |
| [docs/archive/sessions/](archive/sessions/) | Session notes archive |
| [docs/archive/phase-reports/](archive/phase-reports/) | Phase implementation reports |

---

## 📊 Audit & Maintenance

| Document | Purpose |
|----------|---------|
| [docs/DOCUMENTATION-AUDIT.md](DOCUMENTATION-AUDIT.md) | Documentation audit (May 2026) |
| [docs/spec-audit.md](spec-audit.md) | SPEC audit |
| [docs/config-audit.md](config-audit.md) | Config audit |
| [docs/SKILLS-CLEANUP-REPORT.md](SKILLS-CLEANUP-REPORT.md) | Skills cleanup report |

---

## Maintenance Status

| Category | Status | Last Updated |
|----------|--------|-------------|
| Core Protocol docs | ✅ Current | 2026-05-02 |
| Quick Start guides | ✅ Current | 2026-05-17 |
| Installation guides | ✅ Current | 2026-05-16 |
| Token visibility docs | ✅ Current | 2026-05-17 |
| Architecture docs | ✅ Current | 2026-05-16 |
| Phase planning docs | ⚠️ Stale | 2026-04 (archive candidates) |
| Framework research | ✅ Complete | 2026-05 (paused) |
