# Skills Matrix & Registry

> **Architecture:** Queue-based — skills are referenced via `skill_refs` in DELEGATE packets.  
> Role-specific skill definitions live in `src/skills/roles/`.  
> All 8 agents are listed in [`src/AGENTS.md`](AGENTS.md).

---

## Rendered Skills Inventory (41 Active)

This is the canonical registry of all rendered skills available for agents to reference. Each skill has a corresponding `SKILL.md` frontmatter file with metadata (name, description, roles, model, effort, version).

### Skill Definitions

| Skill | Path | Description |
|-------|------|-------------|
| ab-testing | `src/skills/ab-testing/SKILL.md` | Experiment orchestration framework with traffic allocation, statistical analysis, and early stopping detection. |
| add-feature-to-framework | `src/skills/_meta/add-feature-to-framework/SKILL.md` | Comprehensive checklist ensuring all new features are integrated into the framework correctly. |
| agent-creator | `src/skills/agent-creator/SKILL.md` | Scaffolds new SPEC-compliant agentic-engineers agents with a single call. |
| agent-definition-verifier | `src/skills/_meta/agent-definition-verifier/SKILL.md` | Validates agent definitions against framework specifications and detects configuration errors. |
| code-hygiene-git-workflow | `src/skills/_meta/code-hygiene-git-workflow/SKILL.md` | Enforces code hygiene and git workflow standards across all commits and branches. |
| consistency-checker | `src/skills/consistency-checker/SKILL.md` | Automated cross-validation of protocol queue integrity. |
| cost-aggregation | `src/skills/cost-aggregation/SKILL.md` | Consolidates provider-specific AI costs into unified metrics across Anthropic, OpenAI, Google Gemini, GitHub Copilot, and Ollama. |
| doc-quality-monitor | `src/skills/doc-quality-monitor/SKILL.md` | Automated documentation-quality monitoring (MONITORING-001). |
| evaluation-framework | `src/skills/_meta/evaluation_framework/SKILL.md` | Framework for comprehensive agent and skill evaluation with metrics collection and analysis. |
| file-cleanup | `src/skills/_meta/file-cleanup/SKILL.md` | Automated cleanup of unused, deprecated, or stale files in the codebase. |
| file-sync | `src/skills/file-sync/SKILL.md` | Discovers and analyzes scripts in the repository, scoring them for utility and integration. |
| gh-actions-monitor | `src/skills/_meta/gh-actions-monitor/SKILL.md` | Monitors GitHub Actions workflow status and alerts on failures or anomalies. |
| git-operations | `src/skills/_meta/git-operations/SKILL.md` | Low-level git operation utilities for automation and workflow scripting. |
| harness-integration-tracker | `src/skills/harness-integration-tracker/SKILL.md` | Continuously discover and document agent/sub-agent integration code/docs/info across all harnesses (OpenCode, Copilot, Claude, PI) to prevent drift and keep integrations fresh. |
| harness-opencode-feature-sync | `src/skills/harness-opencode-feature-sync/SKILL.md` | Drift/feature sync between OpenCode's agent and sub-agent integration points and the agentic-engineers OpenCode renderer. |
| local-model-runtime | `src/skills/local-model-runtime/SKILL.md` | Local Model Runtime support (COST-004) — detects a running local Ollama instance, lists locally-available models, and routes tasks to a zero-cost local model when a suitable one exists, falling back to a cloud provider otherwise. |
| metrics-etl | `src/skills/metrics-etl/SKILL.md` | Data pipeline that aggregates daily metrics to Prometheus format for Grafana dashboards. |
| model-engineer | `src/skills/model-engineer/SKILL.md` | Cost-quality optimization agent that analyzes tradeoffs, scores routing candidates, and proposes A/B tests. |
| model-selection | `src/skills/model-selection/SKILL.md` | Model Selection Optimization (COST-003) — recommends optimal AI models for tasks given budget constraints, quality targets, and latency requirements. |
| orchestrator | `src/skills/orchestrator/SKILL.md` | In-harness queue orchestration system that implements the DELEGATE/HANDBACK protocol lifecycle. |
| orchestrator-enforcer | `src/skills/_meta/orchestrator-enforcer/SKILL.md` | Enforces orchestrator routing rules and validates delegation protocol compliance. |
| protocol-validator | `src/skills/protocol-validator/SKILL.md` | Runtime protocol validation for DELEGATEs/HANDBACKs against protocol-core-v1. |
| queue-isolation | `src/skills/_meta/queue-isolation/SKILL.md` | Ensures queue isolation and prevents cross-contamination between concurrent task executions. |
| queue-management | `src/skills/queue-management/SKILL.md` | Atomic queue operations for DELEGATE/HANDBACK lifecycle with cycle detection, rate limiting, and validation. |
| queue-path-validator | `src/skills/_meta/queue-path-validator/SKILL.md` | Validates queue file paths and detects filesystem consistency issues. |
| queue-query | `src/skills/queue-query/SKILL.md` | Local-queue visibility skill — query and inspect the per-session, per-harness filesystem queue by state (incoming backlog, processing orphans to resume, done results/next-steps). |
| queue-todo-sync | `src/skills/queue-todo-sync/SKILL.md` | Auto-sync queue DELEGATEs ↔ TODO. |
| repo-init | `src/skills/repo-init/SKILL.md` | [DISABLED] Initializes new repositories with the agentic-engineers framework. |
| security-field-validator | `src/skills/_meta/security-field-validator/SKILL.md` | Validates sensitive fields and enforces security constraints in configuration and data. |
| session-analyzer | `src/skills/session-analyzer/SKILL.md` | Meta-skill for automated session transcript analysis and quality recommendations. |
| skill-creator | `src/skills/skill-creator/SKILL.md` | Create new agentic-engineers skills following the agentskills. |
| skill-template | `src/skills/_meta/skill-template/SKILL.md` | Template and checklist for creating new skills with proper structure and documentation. |
| spec-management | `src/skills/spec-management/SKILL.md` | Exclusive SPEC. |
| spec-validator | `src/skills/spec-validator/SKILL.md` | Validates implementation compliance with SPEC. |
| spec-version-validator | `src/skills/_meta/spec-version-validator/SKILL.md` | Validates spec version compatibility and detects incompatible version changes. |
| task-orchestration | `src/skills/_meta/task-orchestration/SKILL.md` | Encodes task execution framework principle for parallel task execution and decision points. |
| test-sync-validator | `src/skills/testing/SKILL.md` | Validates test fixture synchronization with code changes. |
| tokenadvisor | `src/skills/tokenadvisor/SKILL.md` | Daily metrics analysis agent that aggregates metrics by role, identifies cost inefficiencies, flags outliers, and recommends optimizations. |
| usage-tracking | `src/skills/usage-tracking/SKILL.md` | Real-time and historical token usage capture, analysis, and forecasting skill for agents. |
| workflow-review | `src/skills/workflow-review/SKILL.md` | Validates end-to-end delegation workflows for correctness. |

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
 | Security Engineer | [`src/skills/roles/security-engineer.md`](skills/roles/security-engineer.md) | `claude-opus-4.8` | 💰💰💰 Premium |

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
| CI/CD Watch | `src/skills/monitoring/cicd-watch.md` | Engineer, Senior Eng, Lead Eng, Quality Eng | Core post-merge behaviour: watch pipeline to green; fix on new branch + PR; repeat |
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
| Queue Query | `src/skills/queue-query/SKILL.md` | Orchestrator | Read-only queue visibility (size, ls, orphans, done-summary) |
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
| Protocol Validator | `src/skills/protocol-validator/SKILL.md` | All | Canonical DELEGATE/HANDBACK validator (single source of truth for evals, renderer, queue). Runtime spec-driven validation with core + extension checking. <5ms validation time. |
| Repo Init | `src/skills/repo-init/SKILL.md` | Senior, Lead | Bootstrap a new repo with standard structure |
| Skill Creator | `src/skills/skill-creator/SKILL.md` | Lead, Senior | Author new skills with consistent YAML frontmatter |
| Spec Management | `src/skills/spec-management/SKILL.md` | Senior, Lead | Maintain SPEC.md and track compliance |
| Spec Validator | `src/skills/spec-validator/SKILL.md` | QE | Validate code against SPEC.md requirements |
| Token Advisor (standalone) | `src/skills/tokenadvisor/SKILL.md` | Model Eng | Dedicated token budgeting advisor |
| Usage Tracking | `src/skills/usage-tracking/SKILL.md` | Orchestrator, Model Eng | Aggregate and report usage + cost data |

### Category 13: Standalone Markdown Skills (3 skills)

| Skill | File | Roles | Purpose |
|-------|------|-------|---------|
| Engineer Execution | `src/skills/engineer-execution.md` | Engineer | Step-by-step execution checklist for the Engineer |
| Quality Gate Aggregator | `src/skills/quality-gate-aggregator.md` | QE | Aggregate results from multiple quality gate checks |
| Quality Gate Orchestration | `src/skills/quality-gate-orchestration.md` | QE, Orchestrator | Orchestrate parallel quality gate execution |

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
| Harness Integration Tracker | `harness-integration-tracker/SKILL.md` | ✅ Active | `scripts/harness_integration_tracker.py` + tests |
| Metrics ETL | `metrics-etl/SKILL.md` | ✅ Active | `scripts/metrics-etl.py` |
| Model Engineer (agent) | `model-engineer/SKILL.md` | ✅ Active | `scripts/model-engineer.py` (scheduled) |
| Protocol Validator | `protocol-validator/SKILL.md` | ✅ Active | `scripts/protocol_validator.py` + tests |
| Queue Management | `queue-management/SKILL.md` | ✅ Active | `queue_manager.py` + `scripts/queue_ops.py` + tests |
| Queue Query | `queue-query/SKILL.md` | ✅ Active | `scripts/queue_query.py` + tests |
| Repo Init | `repo-init/SKILL.md` | ✅ Active | `scripts/repo_init.py` + assets + tests |
| Skill Creator | `skill-creator/SKILL.md` | ✅ Active | Authoring guide (instruction-only) |
| Spec Management | `spec-management/SKILL.md` | ✅ Active | `scripts/spec_manager.py` + audit trail |
| Spec Validator | `spec-validator/SKILL.md` | ✅ Active | `scripts/spec_validator.py` |
| Token Advisor | `tokenadvisor/SKILL.md` | ✅ Active | `scripts/tokenadvisor.py` (scheduled) |
| Usage Tracking | `usage-tracking/SKILL.md` | ✅ Active | `scripts/usage-tracking.sh` + `capture_token_usage.sh` |

### Standalone Markdown Skills (no script, instruction-only)

| Skill | File | Status |
|-------|------|--------|
| Engineer Execution | `engineer-execution.md` | ✅ Active |
| Quality Gate Aggregator | `quality-gate-aggregator.md` | ✅ Active |
| Quality Gate Orchestration | `quality-gate-orchestration.md` | ✅ Active |

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
