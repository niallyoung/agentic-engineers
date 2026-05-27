# Skills Matrix & Registry

> **Architecture:** Queue-based — skills are referenced via `skill_refs` in DELEGATE packets.  
> Role-specific skill definitions live in `src/skills/roles/`.  
> All 8 agents are listed in [`src/AGENTS.md`](AGENTS.md).

---

## Role × Capability Matrix

| Capability | Orchestrator | Engineer | Model Eng | Quality Eng | Lead Eng | Senior Eng | Principal | Security |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Task routing & delegation | ✅ Primary | — | — | — | ✅ | — | — | — |
| Queue management | ✅ Primary | — | — | — | — | — | — | — |
| File edits (simple, scoped) | — | ✅ Primary | — | — | — | ✅ | — | — |
| Unit test writing | — | ✅ Primary | — | ✅ | — | ✅ | — | — |
| Multi-file refactoring | — | — | — | — | ✅ | ✅ Primary | ✅ | — |
| Architecture decisions | — | — | — | — | ✅ Primary | ✅ | ✅ | — |
| Complex debugging | — | — | — | — | — | ✅ | ✅ Primary | — |
| Code review (8-point) | — | — | — | ✅ | ✅ Primary | ✅ | — | — |
| Post-impl. validation | — | — | — | ✅ Primary | — | — | — | — |
| Model selection / cost opt. | ✅ | — | ✅ Primary | ✅ | — | — | — | — |
| Metrics collection | ✅ | — | ✅ Primary | ✅ | — | — | — | — |
| A/B test orchestration | ✅ | — | ✅ Primary | ✅ | — | — | — | — |
| Security audit | — | — | — | — | — | — | — | ✅ Primary |
| Threat modelling | — | — | — | — | — | — | ✅ | ✅ Primary |
| Vulnerability assessment | — | — | — | — | — | — | — | ✅ Primary |
| CI/CD configuration | — | ✅ | — | ✅ | ✅ Primary | ✅ | — | — |
| Local CI (lint/test/build) | — | ✅ Primary | — | ✅ | — | ✅ | — | — |
| Documentation | ✅ | ✅ Primary | — | — | — | ✅ | — | — |
| Dependency updates | — | ✅ Primary | — | ✅ | — | ✅ | — | ✅ Review |
| Spec validation | — | ✅ | — | ✅ Primary | ✅ | — | — | — |
| Git workflow | ✅ | ✅ Primary | — | — | — | ✅ | — | — |
| Cross-service analysis | — | — | — | — | ✅ | ✅ | ✅ Primary | — |
| Token budget advisory | ✅ | — | ✅ Primary | ✅ | — | — | — | — |

---

## Role Skill Definitions

| Role | Skill File | Model | Cost Tier |
|------|-----------|-------|-----------|
| Orchestrator | [`src/skills/roles/engineer.md`](skills/roles/engineer.md) → [`orchestration/task-routing.md`](skills/orchestration/task-routing.md) | `claude-haiku-4.5` | 💰 Cheap |
| Engineer | [`src/skills/roles/engineer.md`](skills/roles/engineer.md) | `claude-haiku-4.5` | 💰 Cheap |
| Model Engineer | [`src/skills/roles/model-engineer.md`](skills/roles/model-engineer.md) | `claude-sonnet-4.6` | 💰💰 Medium |
| Quality Engineer | [`src/skills/roles/quality-engineer.md`](skills/roles/quality-engineer.md) | `claude-sonnet-4.6` | 💰💰 Medium |
| Lead Engineer | [`src/skills/roles/lead-engineer.md`](skills/roles/lead-engineer.md) | `claude-sonnet-4.6` | 💰💰 Medium |
| Senior Engineer | [`src/skills/roles/senior-engineer.md`](skills/roles/senior-engineer.md) | `claude-sonnet-4.6` | 💰💰 Medium |
| Principal Engineer | [`src/skills/roles/principal-engineer.md`](skills/roles/principal-engineer.md) | `claude-opus-4-6` | 💰💰💰 Premium |
| Security Engineer | [`src/skills/roles/security-engineer.md`](skills/roles/security-engineer.md) | `claude-opus-4.7` | 💰💰💰 Premium |

---

## Complete Skills Inventory

### Category 1: Orchestration (4 skills)

| Skill | File | Roles | Purpose |
|-------|------|-------|---------|
| Task Routing | `src/skills/orchestration/task-routing.md` | Orchestrator | Decision tree for routing tasks to the right agent |
| GitHub CLI Operations | `src/skills/orchestration/github-cli-operations.md` | Orchestrator, Engineer | PR management, CI status, branch operations |
| Model Engineer Coordination | `src/skills/orchestration/model-engineer-coordination.md` | Orchestrator, Model Eng | When + how to trigger model recommendation cycle |
| TODO Management | `src/skills/orchestration/todo-management.md` | Orchestrator | TODO.md CRUD — task creation, status transitions |

### Category 2: Monitoring (5 skills)

| Skill | File | Roles | Purpose |
|-------|------|-------|---------|
| CI/CD Watch | `src/skills/monitoring/cicd-watch.md` | Quality Eng | Watch pipeline, detect failures, trigger alerts |
| Metrics Collection | `src/skills/monitoring/metrics-collection.md` | Orchestrator, Model Eng | Collect + store token/cost/quality metrics |
| Quality Feedback Analysis | `src/skills/monitoring/quality-feedback-analysis.md` | Model Eng, Quality Eng | Analyse HANDBACK quality scores; spot trends |
| Token Advisor | `src/skills/monitoring/token-advisor.md` | Model Eng | Per-task token budget recommendations |
| Token Advisor Scheduler | `src/skills/monitoring/tokenadvisor-scheduler.md` | Orchestrator | Periodic (weekly) token report generation |

### Category 3: Optimization (7 skills)

| Skill | File | Roles | Purpose |
|-------|------|-------|---------|
| A/B Test Automation | `src/skills/optimization/ab-test-automation.md` | Model Eng, QE | Automate model A/B experiment execution |
| A/B Testing Framework | `src/skills/optimization/ab-testing-framework.md` | Model Eng | Framework for comparing model variants |
| Cost-Quality Tradeoff | `src/skills/optimization/cost-quality-tradeoff.md` | Model Eng, Orchestrator | Evaluate cost vs quality for model selection |
| Model Analysis | `src/skills/optimization/model-analysis.md` | Model Eng | Analyse model performance across task types |
| Model Comparison | `src/skills/optimization/model-comparison.md` | Model Eng | Side-by-side model evaluation |
| Model Engineer Automation | `src/skills/optimization/model-engineer-automation.md` | Model Eng | Automate the feedback loop end-to-end |
| Model Recommendation | `src/skills/optimization/model-recommendation.md` | Model Eng | Generate actionable model swap recommendations |

### Category 4: Queue Management (1 skill + references)

| Skill | File | Roles | Purpose |
|-------|------|-------|---------|
| Queue Management | `src/skills/queue-management/SKILL.md` | Orchestrator | DELEGATE/HANDBACK protocol; queue lifecycle |
| — | `src/skills/queue-management/references/EXAMPLES.md` | All | DELEGATE + HANDBACK YAML examples |
| — | `src/skills/queue-management/references/QUEUE-OPS-API.md` | All | Queue operations API reference |

### Category 5: Patterns (6 skills)

| Skill | File | Roles | Purpose |
|-------|------|-------|---------|
| API Resilience | `src/skills/patterns/api-resilience.md` | Engineer, Senior | Retry, circuit breaker, timeout patterns |
| Event Consumer | `src/skills/patterns/event-consumer.md` | Engineer, Senior | Event-driven consumer implementation pattern |
| Implementation Coding | `src/skills/patterns/implementation-coding.md` | Engineer, Senior | Standard coding conventions and checklist |
| Lambda Handler | `src/skills/patterns/lambda-handler.md` | Engineer | AWS Lambda handler structure + cold start handling |
| Local CI | `src/skills/patterns/local-ci.md` | Engineer, Senior | Run lint + test + build locally before push |
| Makefile | `src/skills/patterns/makefile.md` | Engineer, Senior, Lead | Makefile conventions and standard targets |

### Category 6: Architecture (3 skills)

| Skill | File | Roles | Purpose |
|-------|------|-------|---------|
| Architecture Design | `src/skills/architecture/architecture-design.md` | Lead, Senior, Principal | System design principles and patterns |
| Design Decision Documentation | `src/skills/architecture/design-decision-documentation.md` | Lead, Principal | How to document ADRs and architectural choices |
| System Tradeoff Analysis | `src/skills/architecture/system-tradeoff-analysis.md` | Lead, Senior, Principal | Framework for evaluating design tradeoffs |

### Category 7: Security (3 skills)

| Skill | File | Roles | Purpose |
|-------|------|-------|---------|
| Security Architecture Review | `src/skills/security/security-architecture-review.md` | Security | Full security review of architecture components |
| Threat Modelling | `src/skills/security/threat-modeling.md` | Security, Principal | STRIDE-based threat analysis |
| Vulnerability Assessment | `src/skills/security/vulnerability-assessment.md` | Security | CVE scanning, dependency audit, findings report |

### Category 8: Shared / Cross-Role (6 skills)

| Skill | File | Roles | Purpose |
|-------|------|-------|---------|
| CDK Stack | `src/skills/shared/cdk-stack.md` | Engineer, Senior | AWS CDK stack construction patterns |
| Core Engineering Baseline | `src/skills/shared/core-engineering-baseline.md` | All | Minimum baseline: CI, tests, docs, naming |
| Engineer Specifics | `src/skills/shared/engineer-specifics.md` | Engineer | Execution-level conventions for the Engineer role |
| Git Workflow | `src/skills/shared/git-workflow.md` | All | Branch, commit, PR, merge conventions |
| GitHub CLI | `src/skills/shared/github-cli.md` | All | `gh` CLI cheatsheet — PRs, issues, Actions |
| SigV4 Client | `src/skills/shared/sigv4-client.md` | Engineer, Senior | AWS SigV4 request signing implementation |

### Category 9: Review (3 skills)

| Skill | File | Roles | Purpose |
|-------|------|-------|---------|
| Code Quality Analysis | `src/skills/review/code-quality-analysis.md` | Lead, QE | Static analysis conventions and quality metrics |
| Code Review | `src/skills/review/code-review.md` | Lead, QE | 8-point code review checklist |
| Quorum QE | `src/skills/review/quorum-qe.md` | QE, Lead | Multi-reviewer quorum validation for critical changes |

### Category 10: Testing (1 skill)

| Skill | File | Roles | Purpose |
|-------|------|-------|---------|
| Playwright Testing | `src/skills/testing/playwright-testing.md` | Engineer, QE | E2E browser test authoring and execution |

### Category 11: Roles (8 skills)

| Skill | File | Roles | Purpose |
|-------|------|-------|---------|
| Engineer | `src/skills/roles/engineer.md` | Engineer | Full Engineer role definition |
| Healer Engineer | `src/skills/roles/healer-engineer.md` | Engineer | Self-healing pattern for automated recovery |
| Lead Engineer | `src/skills/roles/lead-engineer.md` | Lead | Full Lead Engineer role definition |
| Model Engineer | `src/skills/roles/model-engineer.md` | Model Eng | Full Model Engineer role definition |
| Principal Engineer | `src/skills/roles/principal-engineer.md` | Principal | Full Principal Engineer role definition |
| Quality Engineer | `src/skills/roles/quality-engineer.md` | QE | Full Quality Engineer role definition |
| Security Engineer | `src/skills/roles/security-engineer.md` | Security | Full Security Engineer role definition |
| Senior Engineer | `src/skills/roles/senior-engineer.md` | Senior | Full Senior Engineer role definition |

### Category 12: Standalone Capability Skills (13 skills)

| Skill | File | Roles | Purpose |
|-------|------|-------|---------|
| A/B Testing | `src/skills/ab-testing/SKILL.md` | Model Eng, QE | Statistically-rigorous A/B test execution |
| Agent Creator | `src/skills/agent-creator/SKILL.md` | Lead, Senior | Create new agent definitions from template |
| Consistency Checker | `src/skills/consistency-checker/SKILL.md` | QE, Lead | Cross-file consistency validation |
| Metrics ETL | `src/skills/metrics-etl/SKILL.md` | Model Eng | Extract/transform/load metrics from HANDBACKs |
| Model Engineer (agent) | `src/skills/model-engineer/SKILL.md` | Model Eng | Scheduled cost-quality analysis agent (daily at 17:00) |
| Protocol Validator | `src/skills/protocol-validator/SKILL.md` | QE | Validate DELEGATE/HANDBACK YAML schema compliance |
| Repo Init | `src/skills/repo-init/SKILL.md` | Senior, Lead | Bootstrap a new repo with standard structure |
| Skill Creator | `src/skills/skill-creator/SKILL.md` | Lead, Senior | Author new skills with consistent YAML frontmatter |
| Spec Management | `src/skills/spec-management/SKILL.md` | Senior, Lead | Maintain SPEC.md and track compliance |
| Spec Validator | `src/skills/spec-validator/SKILL.md` | QE | Validate code against SPEC.md requirements |
| Token Advisor (standalone) | `src/skills/tokenadvisor/SKILL.md` | Model Eng | Dedicated token budgeting advisor |
| Usage Tracking | `src/skills/usage-tracking/SKILL.md` | Orchestrator, Model Eng | Aggregate and report usage + cost data |
| Voice Notify (skill dir) | `src/skills/voice-notify/SKILL.md` | Orchestrator | Full voice-notify skill with macOS + Linux scripts |

### Category 13: Standalone Markdown Skills (4 skills)

| Skill | File | Roles | Purpose |
|-------|------|-------|---------|
| Engineer Execution | `src/skills/engineer-execution.md` | Engineer | Step-by-step execution checklist for the Engineer |
| Quality Gate Aggregator | `src/skills/quality-gate-aggregator.md` | QE | Aggregate results from multiple quality gate checks |
| Quality Gate Orchestration | `src/skills/quality-gate-orchestration.md` | QE, Orchestrator | Orchestrate parallel quality gate execution |
| Voice Notify | `src/skills/voice-notify.md` | Orchestrator | macOS voice notification for long-running task completion |

---

## Skills by Role (Quick Reference)

### Orchestrator
- `orchestration/task-routing.md` — routing logic
- `orchestration/github-cli-operations.md` — CI monitoring
- `orchestration/model-engineer-coordination.md` — model optimization triggers
- `orchestration/todo-management.md` — task lifecycle
- `monitoring/token-advisor.md` — budget checks
- `monitoring/tokenadvisor-scheduler.md` — periodic reporting
- `queue-management/SKILL.md` — queue operations
- `skills/quality-gate-orchestration.md` — quality gate coordination

### Engineer
- `roles/engineer.md` — role definition
- `patterns/implementation-coding.md` — coding conventions
- `patterns/local-ci.md` — pre-push CI
- `shared/git-workflow.md` — branch + commit
- `shared/github-cli.md` — PR operations
- `skills/engineer-execution.md` — execution checklist

### Model Engineer
- `roles/model-engineer.md` — role definition
- `optimization/model-recommendation.md` — recommendations
- `optimization/cost-quality-tradeoff.md` — cost/quality analysis
- `monitoring/metrics-collection.md` — metrics input
- `monitoring/quality-feedback-analysis.md` — feedback loop
- `ab-testing/SKILL.md` — experiment execution
- `metrics-etl/SKILL.md` — data pipeline

### Quality Engineer
- `roles/quality-engineer.md` — role definition
- `review/code-review.md` — 8-point checklist
- `review/code-quality-analysis.md` — static analysis
- `monitoring/cicd-watch.md` — pipeline watch
- `skills/quality-gate-aggregator.md` — gate results
- `protocol-validator/SKILL.md` — schema validation
- `spec-validator/SKILL.md` — spec compliance

### Lead Engineer
- `roles/lead-engineer.md` — role definition
- `review/code-review.md` — review authority
- `review/quorum-qe.md` — multi-reviewer coordination
- `architecture/architecture-design.md` — design guidance
- `architecture/design-decision-documentation.md` — ADRs
- `patterns/makefile.md` — build conventions

### Senior Engineer
- `roles/senior-engineer.md` — role definition
- `architecture/system-tradeoff-analysis.md` — design analysis
- `patterns/implementation-coding.md` — coding standards
- `patterns/local-ci.md` — CI validation
- `spec-management/SKILL.md` — spec maintenance
- `agent-creator/SKILL.md` — agent creation
- `repo-init/SKILL.md` — repo bootstrapping

### Principal Engineer
- `roles/principal-engineer.md` — role definition
- `architecture/architecture-design.md` — deep system design
- `architecture/system-tradeoff-analysis.md` — complex tradeoffs
- `security/threat-modeling.md` — architectural threat analysis

### Security Engineer
- `roles/security-engineer.md` — role definition
- `security/security-architecture-review.md` — security review
- `security/threat-modeling.md` — threat modelling
- `security/vulnerability-assessment.md` — CVE analysis
- `shared/github-cli.md` — dependency scanning

---

## Escalation Quick Reference

### Engineer → Senior Engineer
- Task spans 3+ files in different packages
- Requires understanding of system architecture
- Test failures that are not obvious fixes

### Senior → Principal
- Cross-service design decisions
- Performance-critical path changes
- Debugging that has failed twice

### Senior → Security
- Auth / authz changes
- Token / credential handling
- Input validation at trust boundaries
- Dependency with known CVEs
- Any change to encryption or hashing

### Any → Lead
- Cross-repo coordination needed
- Breaking API changes
- Conflict resolution between agents

> For full escalation rules, see [`src/DECISION-MAKING.md`](DECISION-MAKING.md).

---

## Skill Registration Status

All `SKILL.md` files discovered in `src/skills/`. Status reflects implementation completeness.

| Skill | File | Status | Implementation |
|-------|------|--------|----------------|
| A/B Testing | `ab-testing/SKILL.md` | ✅ Active | `scripts/ab-testing.py` |
| Agent Creator | `agent-creator/SKILL.md` | ✅ Active | `scripts/agent_creator.py` |
| Consistency Checker | `consistency-checker/SKILL.md` | ✅ Active | `scripts/consistency_checker.py` + tests |
| Metrics ETL | `metrics-etl/SKILL.md` | ✅ Active | `scripts/metrics-etl.py` |
| Model Engineer (agent) | `model-engineer/SKILL.md` | ✅ Active | `scripts/model-engineer.py` (scheduled) |
| Protocol Validator | `protocol-validator/SKILL.md` | ✅ Active | `scripts/protocol_validator.py` + tests |
| Queue Management | `queue-management/SKILL.md` | ✅ Active | `queue_manager.py` + `scripts/queue_ops.py` + tests |
| Repo Init | `repo-init/SKILL.md` | ✅ Active | `scripts/repo_init.py` + assets + tests |
| Skill Creator | `skill-creator/SKILL.md` | ✅ Active | Authoring guide (instruction-only) |
| Spec Management | `spec-management/SKILL.md` | ✅ Active | `scripts/spec_manager.py` + audit trail |
| Spec Validator | `spec-validator/SKILL.md` | ✅ Active | `scripts/spec_validator.py` |
| Token Advisor | `tokenadvisor/SKILL.md` | ✅ Active | `scripts/tokenadvisor.py` (scheduled) |
| Usage Tracking | `usage-tracking/SKILL.md` | ✅ Active | `scripts/usage-tracking.sh` + `capture_token_usage.sh` |
| Voice Notify | `voice-notify/SKILL.md` | ✅ Active | `scripts/voice-notify.sh` (macOS + Linux) |

### Standalone Markdown Skills (no script, instruction-only)

| Skill | File | Status |
|-------|------|--------|
| Engineer Execution | `engineer-execution.md` | ✅ Active |
| Quality Gate Aggregator | `quality-gate-aggregator.md` | ✅ Active |
| Quality Gate Orchestration | `quality-gate-orchestration.md` | ✅ Active |
| Voice Notify (reference only) | `voice-notify.md` | ✅ Active |

### Directories Without a SKILL.md (Not Registered)

| Directory | Contents | Action Needed |
|-----------|----------|---------------|
| `spec-extract/` | `scanner.sh` only | Create `SKILL.md` to register |
| `roles/` | No `orchestrator.md` | Add `orchestrator.md` (currently split across `orchestration/*.md`) |

> To register a missing skill, follow the **Adding a New Skill** section below.

---

## Escalation Skill Assignments

Each escalation path has specific skills that are invoked. Reference these when building DELEGATE blocks.

### Engineer → Senior Engineer
Trigger skills: `patterns/api-resilience.md`, `patterns/event-consumer.md`, `review/code-review.md`  
Senior role file: `roles/senior-engineer.md`  
Conditions: 3+ files touched, architecture needed, repeated test failure

### Senior Engineer → Principal Engineer
Trigger skills: `architecture/architecture-design.md`, `architecture/system-tradeoff-analysis.md`  
Principal role file: `roles/principal-engineer.md`  
Conditions: cross-service design, performance-critical path, debugging failed twice

### Senior / Lead → Security Engineer
Trigger skills: `security/threat-modeling.md`, `security/vulnerability-assessment.md`  
Security role file: `roles/security-engineer.md`  
Conditions: auth/authz change, credential handling, trust boundary input, known CVE dependency

### Any → Lead Engineer
Trigger skills: `review/code-review.md`, `review/quorum-qe.md`  
Lead role file: `roles/lead-engineer.md`  
Conditions: cross-repo coordination, breaking API change, conflict resolution between agents

### Quality Engineer → Model Engineer (feedback loop)
Trigger skills: `monitoring/quality-feedback-analysis.md`, `optimization/cost-quality-tradeoff.md`  
Model Eng role file: `roles/model-engineer.md`  
Conditions: quality score < threshold, repeated model failure pattern, cost anomaly detected

### Self-Healing: Quality Gate → Healer Engineer
Trigger skills: `quality-gate-orchestration.md`, `quality-gate-aggregator.md`  
Healer role file: `roles/healer-engineer.md`  
Conditions: low-risk auto-fixable failure detected (lint, dep patch, formatting)  
Blocks on: security findings, high-risk changes (escalate to Security/Lead instead)

---

## Adding a New Skill

1. Create `src/skills/<category>/<skill-name>.md` or `SKILL.md` in a new directory
2. Add YAML frontmatter (see template below)
3. Register it in this file under the correct category
4. Reference it in `skill_refs` of relevant DELEGATE blocks

### Skill YAML Frontmatter Template

```yaml
---
name: skill-name
description: One sentence — what this skill enables the agent to do
version: 1.0.0
roles:
  - engineer       # which roles can use this skill
  - senior-engineer
tags:
  - implementation # keyword tags for discovery
  - patterns
---
```

> For detailed skill authoring guidelines, see [`src/skills/skill-creator/SKILL.md`](skills/skill-creator/SKILL.md).
