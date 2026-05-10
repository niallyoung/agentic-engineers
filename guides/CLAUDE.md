# Agentic Engineers System — CLAUDE.md

**Specialized Context:** Multi-agent team with 8 roles, orchestration, quality gates, cost optimization feedback loops, and 38 domain-specific skills.

**This directory is self-contained and complete.** Load `agentic-engineers/` as a unit to get the full team, all skills, all rules, and all context.

**First read:** [`../setup/copilot-instructions.md`](../setup/copilot-instructions.md) — enforcement rules, auto-load mechanism, learning path.

---

## Quick Start (Load This Context)

**New Collaborator?** Start here:

1. Read `../README.md` (system overview)
2. Read `../orchestration/AGENTS.md` (the 8-role model)
3. Read `../orchestration/HANDOFF.md` (how agents hand work off)
4. Explore `../skills/*/` (38 specialized skills)
5. Reference `../operations/` (metrics, dashboards, automation)

**Running a Task?** Use this workflow:

```yaml
Receive task (from user)
  ↓
Orchestrator (AGENTS.md routing rules) → determine best agent
  ↓
DELEGATE (HANDOFF.md markup) → send to chosen agent with full context
  ↓
Agent executes (using relevant skills from skills/ directory)
  ↓
HANDBACK (markup) → return results + metrics
  ↓
Quality Engineer (QUALITY.md gates) → verify before acceptance
  ↓
Metrics recorded (~/.claude/metrics/) → feeds optimization loops
```

---

## Directory Structure

```
agentic-engineers/
├── README.md ........................... Overview & quick reference
│
├── config/ ............................ System configuration (locked)
│   ├── README.md ....................... Folder guide
│   ├── MODEL_ASSIGNMENTS_LOCKED.md ..... Locked model assignments & progression
│   └── QUICK_REFERENCE.md .............. 1-page routing cheat sheet
│
├── setup/ ............................. Installation & enforcement
│   ├── README.md ....................... Folder guide
│   ├── copilot-instructions.md ......... Enforcement rules & auto-load (READ FIRST)
│   └── GLOBAL_COPILOT_INSTRUCTIONS.md . Global rules reference
│
├── guides/ ............................ Documentation & learning materials
│   ├── README.md ....................... Folder guide
│   ├── CLAUDE.md ....................... This file (team context)
│   ├── INDEX.md ........................ Complete file catalog & manifest
│   ├── DEPLOYMENT_STATUS.md ............ Phase tracking + metrics
│   ├── SYSTEM_INTEGRATION.md ........... 12-month roadmap + architecture
│   ├── WORKFLOW_TEST_EXAMPLE.md ........ End-to-end example with metrics
│   ├── IMPLEMENTATION_COMPLETE.md ...... Phase 2C summary
│   ├── AUDIT_AGENTS_ROLES_SKILLS.md ... System audit (archived)
│   └── ORCHESTRATION_v1_ARCHIVED.md ... Earlier version (reference only)
│
├── orchestration/ ...................... Agent routing & quality
│   ├── README.md ....................... Folder guide
│   ├── AGENTS.md ....................... 8-role model + routing rules
│   ├── HANDOFF.md ...................... DELEGATE/HANDBACK markup protocol
│   └── QUALITY.md ...................... Tier 1/2/3 quality gates
│
├── operations/ ......................... Metrics & automation
│   ├── README.md ....................... Folder guide
│   ├── METRICS.md ...................... Per-task JSON + session JSONL schemas
│   └── TOKENADVISOR.md ................. Metrics analysis framework
│
├── reference/ ......................... Architecture & coding standards
│   ├── CODING_STANDARDS.md ............ Go/TypeScript/CDK conventions
│   ├── DESIGN_PATTERNS.md ............. Architecture & refactoring patterns
│   ├── CQRS_AND_EVENT_SOURCING.md .... Event-driven architecture
│   ├── MULTI_AGENT_OPTIMIZATION.md ... Research on model selection & cost
│   ├── OPERATIONAL_DASHBOARDS.md ..... Metrics visualization setup
│   └── TODO.md ........................ Phase checklist & deliverables
│
└── skills/ ............................ 38 role-based and shared skills
    ├── shared/
    │   ├── github-cli.md
    │   ├── git-workflow.md
    │   ├── cdk-stack.md
    │   └── sigv4-client.md
    ├── orchestrator/skills/
    │   ├── task-routing.md
    │   ├── metrics-collection.md
    │   ├── model-engineer-coordination.md
    │   ├── github-cli-operations.md
    │   ├── cicd-watch.md
    │   ├── token-advisor.md (operationalized)
    │   ├── tokenadvisor-scheduler.md (automation)
    │   ├── model-engineer.md
    │   ├── model-engineer-automation.md (automation)
    │   ├── ab-testing-framework.md
    │   └── ab-test-automation.md (automation)
    ├── engineer/skills/
    │   ├── implementation-coding.md
    │   ├── local-ci-skill.md
    │   ├── playwright-ui-testing.md
    │   ├── lambda-handler.md
    │   └── makefile.md
    ├── senior-engineer/skills/
    │   ├── api-resilience.md
    │   └── event-consumer.md
    ├── lead-engineer/skills/
    │   └── code-review.md
    ├── principal-engineer/skills/
    │   ├── architecture-design.md
    │   ├── design-decision-documentation.md
    │   └── system-tradeoff-analysis.md
    ├── security-engineer/skills/
    │   ├── threat-modeling.md
    │   ├── vulnerability-assessment.md
    │   └── security-architecture-review.md
    ├── model-engineer/skills/
    │   ├── model-analysis.md
    │   ├── model-recommendation.md
    │   ├── cost-quality-tradeoff.md
    │   ├── model-comparison.md
    │   └── quality-feedback-analysis.md
    └── quality-engineer/skills/
        ├── overview.md
        ├── code-quality-analysis.md
        ├── quorum-qe.md
        └── e2e-playwright.md
```

---

## The 8-Role Model

### Primary Execution Roles (7)

| Role | Model | Use For | Escalation |
|------|-------|---------|-----------|
| **Orchestrator** | Haiku | All entry; routing; task mgmt; metrics | Lead Engineer |
| **Engineer** | Haiku | Well-scoped, low-medium complexity | Senior Engineer |
| **Senior Engineer** | Sonnet | Complex coding without plan | Lead Engineer |
| **Lead Engineer** | Sonnet | Reviews, quality, medium planning | Principal Engineer |
| **Principal Engineer** | Opus | Cross-service architecture, design | Security (if needed) |
| **Security Engineer** | Opus | Security analysis, threat modeling | (Final escalation) |
| **Quality Engineer** | Haiku/Sonnet | Post-implementation QA gates | QE Lead (human) |

### Coordination Role (1)

| Role | Model | Coordinates | Works With |
|------|-------|-------------|-----------|
| **Model Engineer** | Opus | Cost optimization, model selection | Quality Engineer feedback |

Model Engineer analyzes task metrics and QE feedback to generate recommendations for future model assignments. This enables continuous improvement: each task makes future similar tasks better routed.

**Routing Rules:** See `orchestration/AGENTS.md` lines 28-50  
**Optimization Workflow:** See `skills/orchestrator/skills/model-engineer-coordination.md`

---

## Key Concepts

### DELEGATE/HANDBACK Protocol

Compact, structured markup for agent-to-agent handoffs (~80% context savings vs. full briefing).

**Orchestrator → Engineer:**
```yaml
---
handoff_type: DELEGATE
task_id: 2026-04-24-redis-caching
role: Engineer
model: claude-haiku-4-5
effort: high
scope: Add Redis caching to {example-service}
context:
  - File: lambda/query/main.go:45
  - Problem: Cache misses, DynamoDB hits on every query
plan:
  1. Initialize Redis client
  2. Implement cache getter (1hr TTL)
  3. Write tests (hit/miss scenarios)
success_criteria:
  - "make verify" passes
  - Cache hit ratio >80%
---
```

**Engineer → Orchestrator:**
```yaml
---
handoff_type: HANDBACK
task_id: 2026-04-24-redis-caching
status: complete
deliverables:
  - Modified: lambda/query/main.go:45-80 (cache logic)
  - Added: lambda/query/cache_test.go (tests)
tests:
  - "make verify": PASS (48 tests, 87% coverage)
tokens_in: 18500
tokens_out: 2100
model: claude-haiku-4-5
effort: high
duration_minutes: 42
escalations: 0
---
```

See `orchestration/HANDOFF.md` for full spec.

### Quality Gates (Tier 1/2/3)

**Tier 1 (All tasks, mandatory):**
- ✓ Lint + test pass
- ✓ No new errors/warnings
- ✓ In-scope changes only
- ✓ Tests added/updated for new code
- ✓ No production hazards (panic, hardcoded secrets, commented code)

**Tier 2 (Senior+ tasks):**
- ✓ Test coverage ≥80%
- ✓ Documented decisions (WHY not WHAT)
- ✓ Plan completeness check

**Tier 3 (Principal/Security):**
- ✓ Architecture adherence
- ✓ IAM correctness
- ✓ Cross-service contracts validated

See `orchestration/QUALITY.md` for checklist.

### Metrics & Feedback Loops

Every task produces metrics and QE feedback → feeds optimization loops → improves future task routing.

**Feedback flow:**
```
Engineer executes → HANDBACK (tokens, quality estimate)
  ↓
Quality Engineer verifies → adds model_assessment feedback
  ↓
Orchestrator records metrics → saves to ~/.claude/metrics/
  ↓
Model Engineer analyzes:
  - Quality/cost/token tradeoffs
  - QE feedback patterns
  - Historical model comparisons
  ↓
Model Engineer generates recommendations (ranked with confidence)
  ↓
Orchestrator applies recommendations to next similar task
```

**Collected per task:**
- tokens_in, tokens_out, tokens_total
- quality_score (1-100)
- cost_usd (calculated)
- escalations (count)
- duration_minutes
- rework_required (boolean)
- qe_feedback (model_assessment + notes)

**Stored in:** `~/.claude/metrics/YYYY-MM-DD/*.json`

**Analyzed by:** 
- Model Engineer (per-task, provides recommendations)
- TokenAdvisor Scheduler (daily, produces opportunity reports)

See `operations/METRICS.md` for schema, `skills/model-engineer/` for analysis details.

---

## Operational Automation (Phase 2E+)

The system is self-improving and autonomous:

**Daily Loop:**
```
09:00 - A/B Test Automation
        Propose tests from Model Engineer recommendations
        
10:00 - Model Engineer Analysis
        Analyze task metrics + QE feedback
        Generate model/effort recommendations with confidence scores
        
17:00 - TokenAdvisor Scheduler
        Read metrics from past 24h → generate daily digest
        Flag anomalies, identify cost optimization opportunities
        
18:00 - Orchestrator
        Review Model Engineer recommendations
        Route next batch using recommended models
        Apply cost/quality optimizations from TokenAdvisor
```

**Result:** Self-correcting system where every task improves future routing and reduces costs.

---

## Key Decisions

**When to use Quorum Voting (Quality Engineer):**
- 1 QE: Low-risk (<100 LOC, single service)
- 3 QEs: Medium-risk (100-300 LOC, multi-service or auth)
- 5 QEs: Critical (>300 LOC, compliance, payments, security)

**When to run A/B Tests:**
- Run if: cost impact >$0.02/task OR quality impact >5 points
- Skip if: minor improvement, well-understood change

**When to upgrade models:**
- Evaluate new model on 5 sample tasks
- If quality ≥ old AND cost ≤ old → upgrade all
- If quality > but cost ↑ → run A/B test

**Cost optimization target (Year 1):**
- Haiku: 60% of work (low-complexity, well-scoped)
- Sonnet: 35% of work (medium-complexity, ambiguous)
- Opus: 5% of work (critical architecture/security only)

---

## Integration Points (External Systems)

**This system integrates with:**
1. **User/Copilot Interface** — Orchestrator receives tasks
2. **Code Repositories** (~/git/ers/*) — Engineer clones, edits, commits
3. **GitHub Actions CI** — Tests run post-push
4. **Metrics Storage** (~/.claude/metrics/) — Local JSON disk storage
5. **Reference Docs** (external to this dir: CODING_STANDARDS.md, DESIGN_PATTERNS.md, CQRS+ES.md)

**Does NOT integrate with:**
- Slack, email, external APIs (those are user-initiated)
- Database systems (all data on disk in JSON)
- Cloud services (fully local, autonomous)

---

## Common Tasks

### "I have a task for the team"

```
1. Provide to Orchestrator (AGENTS.md routing rules determine agent)
2. Orchestrator creates DELEGATE markup (HANDOFF.md)
3. Engineer/Senior/etc. executes
4. Returns HANDBACK markup
5. Quality Engineer verifies (QUALITY.md gates)
6. Task complete, metrics recorded
```

### "I want to understand the 7-role model"

Read `orchestration/AGENTS.md` (lines 18-50 for model, 28-50 for routing rules)

### "I want to add a new skill"

1. Create file: `skills/<role>/skills/<skill-name>.md`
2. Follow template from existing skill (e.g., `implementation-coding.md`)
3. Include: purpose, capabilities, constraints, examples, validation checklist

### "I want to understand how metrics flow"

```
Task execution
  ↓
Engineer writes HANDBACK with tokens_in/out, quality_score
  ↓
Metrics written to ~/.claude/metrics/YYYY-MM-DD/task_id.json
  ↓
TokenAdvisor Scheduler reads daily at 17:00
  ↓
Report produced with cost trends, anomalies, opportunities
  ↓
Model Engineer Automation uses report to improve future recommendations
```

See `operations/METRICS.md` and `operations/TOKENADVISOR.md`

### "I want to run an A/B test"

1. Identify opportunity (Model Engineer recommends)
2. Design test spec (hypothesis, control, test, success criteria)
3. Use `ab-test-automation.md` to allocate tasks
4. Monitor progress daily
5. Analyze results (t-test, effect size)
6. Implement winning arm

See `skills/orchestrator/skills/ab-test-automation.md`

---

## Files to NOT Edit

These are generated/archived, not hand-edited:

- `~/.claude/metrics/` (auto-generated by Orchestrator)
- `~/.claude/reports/` (auto-generated by TokenAdvisor, A/B Test Automation)
- Model assignment tables (auto-updated monthly by Model Engineer)

**DO edit:**
- `orchestration/AGENTS.md` — if routing rules change
- `orchestration/QUALITY.md` — if quality standards change
- `skills/*/` — to add/improve skills
- `operations/` — if metric schema or automation needs adjustment

---

## Support & Escalation

**If Orchestrator can't route a task:**
→ Escalate to human with unclear scope

**If Engineer hits root cause unclear:**
→ Escalate to Senior Engineer (diagnosis)

**If blocking issue in architecture:**
→ Escalate to Lead/Principal Engineer (design)

**If security concern:**
→ Escalate to Security Engineer (threat modeling)

**If quality gate fails:**
→ Return to Engineer (QUALITY.md gates prevent bad merges)

---

## Onboarding New Agent

1. **Load context:** This file + orchestration/AGENTS.md + orchestration/HANDOFF.md
2. **Understand routing:** Memorize the 5-step decision tree (AGENTS.md lines 41-49)
3. **Study your role's skills:** Read your role's skills/ subdirectory
4. **Understand quality gates:** QUALITY.md Tier X checklist for your role
5. **See an example:** Review AGENTS.md example DELEGATE/HANDBACK blocks
6. **Practice:** Run through 1-2 sample tasks with feedback

---

## Version & Roadmap

**Current:** Phase 2E+ (Operational Automation Complete)

**Phases:**
- Phase 1: Foundation (HANDOFF, AGENTS, QUALITY, METRICS)
- Phase 2A: Modernization (7-role model)
- Phase 2B: Reference & Tooling (CODING_STANDARDS, skills)
- Phase 2C: Advanced Optimization (advanced skills, research)
- Phase 2D: Quality at Scale (quorum voting, A/B testing, dashboards)
- Phase 2E+: Operational Automation (schedulers, automation, self-improving loops)
- Phase 3: Advanced Features (multi-team, enterprise analytics)
- Phase 4+: Strategic (AI-powered planning, continuous learning)

See `SYSTEM_INTEGRATION.md` for full roadmap.

---

## Quick Reference

| Need | File |
|------|------|
| Agent roles & routing | orchestration/AGENTS.md |
| How to hand off work | orchestration/HANDOFF.md |
| Quality standards | orchestration/QUALITY.md |
| Metrics schema | operations/METRICS.md |
| Cost analysis | operations/TOKENADVISOR.md |
| Implementation TDD | skills/engineer/skills/implementation-coding.md |
| Security review | skills/quality-engineer/skills/quorum-qe.md |
| A/B testing | skills/orchestrator/skills/ab-test-automation.md |
| Full roadmap | SYSTEM_INTEGRATION.md |

---

**This directory is self-contained and portable. Load `agentic-engineers/` as a unit for complete agent system context.**
