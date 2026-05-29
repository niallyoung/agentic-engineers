# Agentic Engineers — Complete Index & Manifest

**Self-contained multi-agent team system.** This document catalogs every file, role, skill, and rule.

---

## 📚 Core Documents (Read in Order)

| # | File | Purpose | Read Time |
|---|------|---------|-----------|
| 1 | `setup/copilot-instructions.md` | Enforcement rules, auto-load, learning path | 10 min |
| 2 | `config/QUICK_REFERENCE.md` | 1-page cheat sheet (print this!) | 5 min |
| 3 | `guides/CLAUDE.md` | Team context, role definitions, integration points | 10 min |
| 4 | `README.md` | System overview, quick start, directory map | 5 min |

**First session:** Read 1-4 above (30 min total). Then pick your role and start accepting tasks.

---

## 📋 Orchestration (How Work Gets Done)

**Directory:** `orchestration/`

| File | Purpose | Key Sections |
|------|---------|--------------|
| `AGENTS.md` | 7-role model with routing rules | Role table, decision tree, cost tiers |
| `HANDOFF.md` | DELEGATE/HANDBACK protocol | Markup examples, validation rules, workflows |
| `QUALITY.md` | Quality gate checklist | Tier 1/2/3, mandatory items, escalation |

**Key concept:** Every task flows through these 3 documents.

---

## 🔧 Operations (Metrics & Feedback Loops)

**Directory:** `operations/`

| File | Purpose | Key Features |
|------|---------|--------------|
| `METRICS.md` | Per-task JSON + session JSONL schema | Directory structure, field definitions, examples |
| `TOKENADVISOR.md` | Daily metrics analysis framework | Cost trends, anomaly detection, recommendations |

**Key concept:** Metrics collected per-task → TokenAdvisor analyzes daily → recommendations improve Model Engineer assignments.

---

## 📚 Reference (Architecture & Patterns)

**Directory:** `reference/`

All reference docs are architecture/coding standards extracted from production agentic-engineers codebase. Use for implementation guidance.

| File | Audience | When to Read |
|------|----------|--------------|
| `CODING_STANDARDS.md` | Engineers | Before writing code (Go/TypeScript/CDK patterns) |
| `DESIGN_PATTERNS.md` | Senior Engineers | Before architecture decisions (handlers, idempotency, caching) |
| `CQRS_AND_EVENT_SOURCING.md` | System Architects | Before event system changes (domain events, projection rebuild) |
| `MULTI_AGENT_OPTIMIZATION.md` | Principal Engineer | Strategic research on RLAF, model selection, optimization |
| `OPERATIONAL_DASHBOARDS.md` | Orchestrator | Week 3+ (metrics visualization setup) |
| `TODO.md` | Project Managers | Phase tracking, deliverables checklist |

---

## 👥 Skills by Role

**Directory:** `skills/`

Each role has specialized skills. Load your role's directory when assigned to a task.

### Orchestrator (Haiku, Low Effort)
**11 skills:** Task routing, metrics collection, model coordination, automation, A/B testing, TokenAdvisor, CI/CD monitoring, GitHub CLI

Directory: `skills/orchestrator/skills/`
- task-routing.md
- metrics-collection.md
- model-engineer-coordination.md
- github-cli-operations.md
- cicd-watch.md
- token-advisor.md
- tokenadvisor-scheduler.md
- model-engineer.md
- model-engineer-automation.md
- ab-testing-framework.md
- ab-test-automation.md

### Engineer (Haiku, High Effort)
**5 skills:** TDD implementation, local CI, UI testing, Lambda handler scaffolding, Makefile patterns

Directory: `skills/engineer/skills/`
- implementation-coding.md
- local-ci-skill.md
- playwright-ui-testing.md
- lambda-handler.md
- makefile.md

### Senior Engineer (Sonnet, High Effort)
**2 skills:** Complex coding (API resilience), event consumer patterns

Directory: `skills/senior-engineer/skills/`
- api-resilience.md
- event-consumer.md

### Lead Engineer (Sonnet, High Effort)
**1 skill:** Code review standards

Directory: `skills/lead-engineer/skills/`
- code-review.md

### Principal Engineer (Opus, High Effort)
**3 skills:** Architecture design, design decision documentation, system tradeoff analysis

Directory: `skills/principal-engineer/skills/`
- architecture-design.md
- design-decision-documentation.md
- system-tradeoff-analysis.md

### Security Engineer (Opus, Max Effort)
**3 skills:** Threat modeling, vulnerability assessment, security architecture review

Directory: `skills/security-engineer/skills/`
- threat-modeling.md
- vulnerability-assessment.md
- security-architecture-review.md

### Model Engineer (Opus, High Effort)
**5 skills:** Model analysis, recommendations, cost-quality tradeoffs, model comparison, quality feedback analysis

Directory: `skills/model-engineer/skills/`
- model-analysis.md
- model-recommendation.md
- cost-quality-tradeoff.md
- model-comparison.md
- quality-feedback-analysis.md

**Coordination:** Works with Quality Engineer to analyze task outcomes and recommend optimal model assignments for future similar tasks. See model-engineer-coordination.md for integration workflow.

### Quality Engineer (Haiku/Sonnet, Low Effort)
**4 skills:** QA gates, code quality analysis, quorum voting, E2E testing

Directory: `skills/quality-engineer/skills/`
- SKILLS.md (overview)
- code-quality-analysis.md
- quorum-qe.md
- e2e-playwright.md

### Shared Cross-Role Skills
**4 skills:** GitHub CLI operations, Git workflow standards, AWS CDK infrastructure patterns, IAM SigV4 signing

Directory: `skills/shared/`
- github-cli.md
- git-workflow.md
- cdk-stack.md
- sigv4-client.md

**Usage:** Available to all roles as needed (not role-specific).

---

## 🔒 Global Rules & Enforcement

File: `GLOBAL_COPILOT_INSTRUCTIONS.md` (copied from {service-name} for reference)

Contains:
- Git enforcement (no --no-verify, conventional commits)
- Voice notification characters (Scout, Architect, Builder, Inspector, Oracle, Cheer, Gloom)
- Workflow standards

**All rules also stated in:** `setup/copilot-instructions.md` (main file for this team)

---

## 📊 Metrics & Progress

File: `guides/DEPLOYMENT_STATUS.md`

Current status:
- ✅ Week 1: Foundation setup complete
- ⏳ Week 2: Skills operationalization (pending)
- ⏳ Week 3: Metrics & dashboards (pending)
- ⏳ Week 4: A/B testing (pending)

Contains rollout metrics, current capacity, cost projections.

---

## 🗂️ Directory Tree (Complete)

```
agentic-engineers/
│
├── README.md                           # Overview, quick start
│
├── config/                             # System configuration (locked)
│   ├── README.md
│   ├── MODEL_ASSIGNMENTS_LOCKED.md     # Locked model assignments & progression
│   └── QUICK_REFERENCE.md              # 1-page cheat sheet (print this!)
│
├── setup/                              # Installation & enforcement
│   ├── README.md
│   ├── copilot-instructions.md         # Enforcement + auto-load (READ FIRST)
│   └── GLOBAL_COPILOT_INSTRUCTIONS.md  # Global rules reference
│
├── guides/                             # Documentation & learning materials
│   ├── README.md
│   ├── CLAUDE.md                       # Team context & integration
│   ├── INDEX.md                        # This file (complete catalog)
│   ├── DEPLOYMENT_STATUS.md            # Phase tracking + metrics
│   ├── SYSTEM_INTEGRATION.md           # 12-month roadmap
│   ├── WORKFLOW_TEST_EXAMPLE.md        # End-to-end example
│   ├── IMPLEMENTATION_COMPLETE.md      # Phase 2C summary
│   ├── AUDIT_AGENTS_ROLES_SKILLS.md    # System audit (archived)
│   └── ORCHESTRATION_v1_ARCHIVED.md    # Earlier orchestration version
│
├── orchestration/                      # How work flows through the system
│   ├── README.md
│   ├── AGENTS.md                       # 8-role model + routing decision tree
│   ├── HANDOFF.md                      # DELEGATE/HANDBACK protocol
│   └── QUALITY.md                      # Quality gates Tier 1/2/3
│
├── operations/                         # Metrics, analytics, optimization
│   ├── README.md
│   ├── METRICS.md                      # Per-task JSON schema + session JSONL
│   └── TOKENADVISOR.md                 # Daily metrics analysis framework
│
├── reference/                          # Architecture & coding standards
│   ├── CODING_STANDARDS.md             # Go/TypeScript/CDK style guide
│   ├── DESIGN_PATTERNS.md              # Architecture & refactoring patterns
│   ├── CQRS_AND_EVENT_SOURCING.md      # Event-driven architecture
│   ├── MULTI_AGENT_OPTIMIZATION.md     # Research on RLAF + model selection
│   ├── OPERATIONAL_DASHBOARDS.md       # Metrics visualization guide
│   └── TODO.md                         # Phase checklist
│
└── skills/
    ├── shared/
    │   ├── github-cli.md
    │   ├── git-workflow.md
    │   ├── cdk-stack.md
    │   └── sigv4-client.md
    │
    ├── orchestrator/skills/
    │   ├── task-routing.md
    │   ├── metrics-collection.md
    │   ├── model-engineer-coordination.md
    │   ├── github-cli-operations.md
    │   ├── cicd-watch.md
    │   ├── token-advisor.md
    │   ├── tokenadvisor-scheduler.md
    │   ├── model-engineer.md
    │   ├── model-engineer-automation.md
    │   ├── ab-testing-framework.md
    │   └── ab-test-automation.md
    │
    ├── engineer/skills/
    │   ├── implementation-coding.md
    │   ├── local-ci-skill.md
    │   ├── playwright-ui-testing.md
    │   ├── lambda-handler.md
    │   └── makefile.md
    │
    ├── senior-engineer/skills/
    │   ├── api-resilience.md
    │   └── event-consumer.md
    │
    ├── lead-engineer/skills/
    │   └── code-review.md
    │
    ├── principal-engineer/skills/
    │   ├── architecture-design.md
    │   ├── design-decision-documentation.md
    │   └── system-tradeoff-analysis.md
    │
    ├── security-engineer/skills/
    │   ├── threat-modeling.md
    │   ├── vulnerability-assessment.md
    │   └── security-architecture-review.md
    │
    ├── model-engineer/skills/
    │   ├── model-analysis.md
    │   ├── model-recommendation.md
    │   ├── cost-quality-tradeoff.md
    │   ├── model-comparison.md
    │   └── quality-feedback-analysis.md
    │
    └── quality-engineer/skills/
        ├── overview.md
        ├── code-quality-analysis.md
        ├── quorum-qe.md
        └── e2e-playwright.md
```

---

## 🚀 How to Use This Index

### I'm a new team member
1. Read `setup/copilot-instructions.md` (enforcement + auto-load)
2. Read `config/QUICK_REFERENCE.md` (cheat sheet)
3. Read `orchestration/AGENTS.md` (roles + routing)
4. Wait for task assignment

### I have a task assigned
1. Read the DELEGATE markup (contains context + plan)
2. Find your role in `orchestration/AGENTS.md`
3. Load `skills/{your-role}/` directory
4. Check relevant reference docs (`reference/CODING_STANDARDS.md`, etc.)
5. Execute TDD: RED → GREEN → REFACTOR
6. Record HANDBACK + metrics to `~/.claude/metrics/`

### I'm reviewing code (Quality Engineer)
1. Load `orchestration/QUALITY.md` (Tier 1/2/3 checklist)
2. Load `skills/quality-engineer/skills/` (QA patterns)
3. Verify HANDBACK against Tier 1 items
4. Record voting decision + notes
5. Metrics recorded automatically by Orchestrator

### I'm analyzing metrics (TokenAdvisor)
1. Read `operations/METRICS.md` (schema)
2. Read `operations/TOKENADVISOR.md` (analysis framework)
3. Read `reference/MULTI_AGENT_OPTIMIZATION.md` (research)
4. Analyze daily metrics from `~/.claude/metrics/`
5. Produce recommendations report

### I need to understand a concept
- **How work flows:** `orchestration/AGENTS.md` → `orchestration/HANDOFF.md` → `orchestration/QUALITY.md`
- **Code patterns:** `reference/CODING_STANDARDS.md` + `reference/DESIGN_PATTERNS.md`
- **Event architecture:** `reference/CQRS_AND_EVENT_SOURCING.md`
- **Cost optimization:** `reference/MULTI_AGENT_OPTIMIZATION.md`
- **Metrics:** `operations/METRICS.md` + `operations/TOKENADVISOR.md`

---

## 🔍 Quick Links (By Topic)

### Workflow
- `config/QUICK_REFERENCE.md` — routing tree, escalation rules
- `orchestration/AGENTS.md` — role definitions, cost tiers
- `orchestration/HANDOFF.md` — DELEGATE/HANDBACK markup
- `orchestration/QUALITY.md` — quality gate checklist

### Task Routing & Orchestration
- `skills/orchestrator/skills/task-routing.md` — decision tree for task assignment
- `skills/orchestrator/skills/metrics-collection.md` — capturing task execution data
- `skills/orchestrator/skills/model-engineer-coordination.md` — feedback loop to Model Engineer

### Model Selection & Optimization
- `skills/model-engineer/skills/model-analysis.md` — analyze quality/cost/tokens
- `skills/model-engineer/skills/model-recommendation.md` — generate ranked recommendations
- `skills/model-engineer/skills/cost-quality-tradeoff.md` — evaluate upgrade/downgrade decisions
- `skills/model-engineer/skills/model-comparison.md` — compare models across data
- `skills/model-engineer/skills/quality-feedback-analysis.md` — extract patterns from QE feedback

### Quality Feedback
- `skills/quality-engineer/skills/code-quality-analysis.md` — provide structured feedback for optimization
- `orchestration/QUALITY.md` — quality gate checklist

### Coding
- `reference/CODING_STANDARDS.md` — naming, testing, error handling
- `reference/DESIGN_PATTERNS.md` — handlers, idempotency, caching
- `skills/engineer/skills/implementation-coding.md` — TDD workflow

### Architecture
- `reference/CQRS_AND_EVENT_SOURCING.md` — event model, replay, versioning
- `reference/DESIGN_PATTERNS.md` — patterns for Go + React
- `reference/MULTI_AGENT_OPTIMIZATION.md` — system design decisions

### Cost & Metrics
- `operations/METRICS.md` — what to record, schema
- `operations/TOKENADVISOR.md` — how metrics are analyzed
- `reference/OPERATIONAL_DASHBOARDS.md` — visualizing metrics
- `reference/MULTI_AGENT_OPTIMIZATION.md` — cost targets + strategy

### Testing
- `skills/engineer/skills/playwright-ui-testing.md` — E2E testing
- `skills/quality-engineer/skills/e2e-playwright.md` — QA patterns
- `reference/DESIGN_PATTERNS.md` — testing patterns (table-driven, mocks)

---

## ✅ Checklist for Team Managers

**Setup complete?**
- [ ] Load entire `agentic-engineers/` directory
- [ ] All agents have read `setup/copilot-instructions.md`
- [ ] All agents have read `config/QUICK_REFERENCE.md`
- [ ] All agents know their role (from `orchestration/AGENTS.md`)
- [ ] All agents can access `~/.claude/metrics/` for recording metrics
- [ ] TokenAdvisor can run daily analysis (scheduled or manual)

**First task ready?**
- [ ] Create DELEGATE markup (reference `orchestration/HANDOFF.md`)
- [ ] Assign to appropriate role (use `orchestration/AGENTS.md` decision tree)
- [ ] Agent returns HANDBACK within 1-2 hours
- [ ] Quality Engineer verifies (use `orchestration/QUALITY.md` Tier 1)
- [ ] Metrics recorded to `~/.claude/metrics/YYYY-MM-DD/`
- [ ] Task logged in `reference/TODO.md` progress tracking

**Running smoothly?**
- [ ] Metrics flowing daily to `~/.claude/metrics/`
- [ ] TokenAdvisor analyzing metrics (daily or per-task)
- [ ] Model Engineer recommendations improving (check accuracy trend)
- [ ] QE acceptance rate >90% (check `guides/DEPLOYMENT_STATUS.md`)
- [ ] Cost tracking toward $0.15/day target (check `reference/TODO.md`)

---

## 📞 Support

**Question about:** → **See:**
- Roles + routing | `config/QUICK_REFERENCE.md` + `orchestration/AGENTS.md`
- Task markup | `orchestration/HANDOFF.md`
- Quality standards | `orchestration/QUALITY.md`
- Code style | `reference/CODING_STANDARDS.md`
- Architecture | `reference/DESIGN_PATTERNS.md` + `reference/CQRS_AND_EVENT_SOURCING.md`
- Metrics | `operations/METRICS.md` + `operations/TOKENADVISOR.md`
- A skill | `skills/{role}/skills/{skill-name}.md`
- Phase progress | `reference/TODO.md`

---

**Status:** Complete, self-contained, ready for production.

Last updated: 2026-04-24 | Phase: Week 1 Complete | Next: Week 2 Operationalization
