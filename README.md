# Agentic Engineers System

Complete multi-agent orchestration framework with 8 specialized roles, queue-based delegation, quality gates, and autonomous feedback loops.

**Installation:**
```bash
make install                    # Install to both ~/.claude/ and ~/.copilot/
make install-copilot           # Install to ~/.copilot/ only
make install-claude            # Install to ~/.claude/ only
```

**Standard Execution Model (CANONICAL WORKFLOW):**
```bash
# 1. Queue a task (create DELEGATE YAML in artifacts/queue/incoming/)
# 2. Start Orchestrator: it polls queue and delegates to agents
# 3. Check results in artifacts/queue/done/ and generated files
# 4. Commit: git add artifacts/ && git commit
```

**📖 QUICK START:**
→ **See [ENTRYPOINT.md](ENTRYPOINT.md)** for complete workflow examples, code samples, and canonical execution model.

**Verification:**
```bash
make status                     # Check installation status
make verify                     # Verify framework structure
```

---

## What Is This?

A production-ready multi-agent framework with:

- **8 Specialized Roles:** Orchestrator, Engineer, Senior Engineer, Lead Engineer, Principal Engineer, Security Engineer, Quality Engineer, Model Engineer
- **38 Domain-Specific Skills:** Implementation, testing, security review, architecture design, threat modeling, cost optimization, etc.
- **Quality Infrastructure:** Tier 1/2/3 gates, quorum voting, distributed QA
- **Cost Optimization:** A/B testing, model selection automation, continuous feedback loops
- **Usage Budget Manager:** Real-time session/weekly usage tracking, dynamic model recommendations, intelligent break suggestions
- **Token Usage Tracking:** Historical capture and trend analysis, velocity calculation, reset forecasting, cron integration
- **Autonomous Operations:** Daily metrics analysis, test proposals, model recommendations

**Result:** Self-improving system that gets cheaper and better every day, while staying within token budgets.

---

## 🗂️ Find Everything Here

**[MANIFEST.md](MANIFEST.md) — Complete file listing with every file documented**

75+ files organized by purpose. Use MANIFEST.md to discover:
- Every file in the system
- Purpose and size of each file
- When to read each document
- Navigation by role, topic, or folder
- Quick reference tables

Both Claude Code and GitHub Copilot: Start here for complete file discovery.

---

## 📁 Directory Structure

```
agentic-engineers/
├── README.md                 This file
├── MANIFEST.md              Complete file listing & discovery guide
├── QUEUE-INTEGRATION-SUMMARY.md  Queue architecture overview
├── config/                  System configuration
│   ├── MODEL_ASSIGNMENTS_LOCKED.md
│   └── QUICK_REFERENCE.md
├── setup/                   Installation & harness integration
│   ├── copilot-instructions.md
│   ├── GLOBAL_COPILOT_INSTRUCTIONS.md
│   └── STARTUP-CHECKLIST.md
├── guides/                  Learning & documentation
│   ├── CLAUDE.md (team context)
│   └── SYSTEM_INTEGRATION.md (12-month roadmap)
├── orchestration/           Agent definitions & workflow
│   ├── AGENTS.md (8 roles, routing rules)
│   ├── SKILLS.md (role-specific workflows)
│   ├── HANDOFF.md (DELEGATE/HANDBACK format)
│   ├── QUEUE-PROTOCOL.md (queue mechanics)
│   ├── QUALITY.md (quality gates)
│   └── agents/*.md (detailed role specs)
├── operations/              Metrics & optimization
│   ├── METRICS.md
│   └── TOKENADVISOR.md
├── skills/                  Role-based skills (38 total)
│   ├── orchestrator/skills/
│   ├── engineer/skills/
│   ├── senior-engineer/skills/
│   ├── lead-engineer/skills/
│   ├── principal-engineer/skills/
│   ├── security-engineer/skills/
│   ├── quality-engineer/skills/
│   ├── model-engineer/skills/
│   └── shared/skills/
├── artifacts/               Runtime & queue files
│   └── queue/
│       ├── incoming/        New tasks
│       ├── processing/      In-progress work
│       └── done/            Completed work
├── dist/                    Rendered distributions
│   ├── claude/              For ~/.claude/ installation
│   └── copilot/             For ~/.copilot/ installation
├── scripts/                 Installation scripts
│   ├── install-claude.sh
│   └── install-copilot.sh
└── Makefile                 Build & install targets
```

## ⚡ Quick Start

**New to the system?** Start here:
1. [`setup/copilot-instructions.md`](setup/copilot-instructions.md) — Enforcement rules, learning path (READ FIRST!)
2. [`config/QUICK_REFERENCE.md`](config/QUICK_REFERENCE.md) — 1-page cheat sheet with roles & routing rules
3. [`guides/CLAUDE.md`](guides/CLAUDE.md) — Team context & integration
4. Print items 1-2, reference during execution

**Auto-Load:** When you invoke "agentic-engineers", all files load automatically (setup + config + guides + orchestration + operations + skills + reference).

---

## 📊 Visual Workflow Diagrams

**Want to see how work moves through the system?**

- **[WORKFLOW.md](WORKFLOW.md)** — Comprehensive diagram with example flow showing:
  - System architecture with all agent types
  - Complete example: feature implementation from intake through merge
  - DELEGATE/HANDBACK message formats with actual data
  - Parallel quality gate execution (Testing, Healing, Security, Metrics)
  - Decision points and escalation paths
  - ~15-minute read for full understanding

- **[QUICK-REFERENCE.md](QUICK-REFERENCE.md)** — One-page quick reference with:
  - Architecture overview diagram
  - Agent responsibilities table
  - Decision trees (routing, aggregation)
  - Example timeline (feature from start to deploy)
  - Communication patterns
  - Key metrics
  - ~5-minute read for quick lookup

---

## Quick Start (5 Minutes)

### 1. Understand the Model

```bash
cat orchestration/AGENTS.md | head -50
```

The 7 roles, cost tiers, and routing rules.

### 2. Understand How Work Gets Done

```bash
cat orchestration/HANDOFF.md | head -100
```

DELEGATE/HANDBACK markup protocol for compact handoffs.

### 3. See the Skills

```bash
ls -1 skills/*/skills/
```

22 specialized skills (implementation, testing, security, etc.)

### 4. Check Quality Standards

```bash
cat orchestration/QUALITY.md
```

Tier 1/2/3 checklists that prevent bad merges.

### 5. Understand Cost Optimization

```bash
cat operations/TOKENADVISOR.md | head -50
ls skills/orchestrator/skills/model-engineer-automation.md
ls skills/orchestrator/skills/ab-test-automation.md
```

How the system automatically improves model selection and cost.

---

## Directory Map

| Path | Purpose |
|------|---------|
| **orchestration/** | Agent routing, handoff protocol, quality gates, budget monitoring |
| `AGENTS.md` | 7-role model + routing decision tree |
| `HANDOFF.md` | DELEGATE/HANDBACK markup spec |
| `QUALITY.md` | Tier 1/2/3 quality checklists |
| `USAGE-BUDGET-MANAGER.md` | Real-time token usage monitoring skill |
| `USAGE-BUDGET-INTEGRATION.md` | Budget integration with Orchestrator workflow |
| **operations/** | Metrics infrastructure + automation |
| `METRICS.md` | Per-task JSON + session JSONL schemas |
| `TOKENADVISOR.md` | Daily metrics analysis framework |
| **skills/** | 38 role-based and shared skills |
| `orchestrator/skills/` | 11 skills (routing, automation, optimization) |
| `engineer/skills/` | 5 skills (implementation, testing, UI, handlers, tools) |
| `senior-engineer/skills/` | 2 skills (complex coding, APIs) |
| `lead-engineer/skills/` | 1 skill (code review) |
| `principal-engineer/skills/` | 3 skills (architecture, design decisions, tradeoffs) |
| `security-engineer/skills/` | 3 skills (threat modeling, vulnerabilities, architecture review) |
| `quality-engineer/skills/` | 4 skills (analysis, quorum voting, E2E, overview) |
| `model-engineer/skills/` | 5 skills (analysis, recommendations, comparisons, feedback) |
| `shared/skills/` | 4 skills (GitHub, git workflow, CDK, SigV4) |
| **guides/SYSTEM_INTEGRATION.md** | 12-month roadmap + full architecture |
| **guides/CLAUDE.md** | Team context & integration |

---

## The Workflow (Queue-Based Delegation)

### 1. Task Enters Queue

```
Task arrives → artifacts/queue/incoming/{task_id}.yaml
Example: "Fix token timeout in {service-name}"
```

### 2. Orchestrator Polls & Routes

```
Orchestrator (harness agent) polls every 30-60 seconds:
├─ Reads AGENTS.md routing rules
├─ Applies decision tree (complexity? scope? security?)
├─ Creates DELEGATE block (HANDOFF.md format)
├─ Stores in artifacts/delegates/YYYY-MM-DD/
└─ Sends to appropriate role agent
```

### 3. Agent Executes

```
Engineer (or other role) receives DELEGATE:
├─ Reads scope, context, plan, success_criteria
├─ Reads SKILLS.md for role-specific guidance
├─ Executes work (Engineer can use Red-Green TDD)
└─ Returns HANDBACK with:
   - deliverables (what changed)
   - tests (make verify status)
   - tokens_in, tokens_out (metrics)
   - duration_minutes
   - escalations (if any)
```

### 4. Orchestrator Routes HANDBACK

```
Orchestrator polls artifacts/queue/processing/:
├─ If status=complete → route to Quality Engineer
├─ If status=blocked → escalate to Lead/Senior Engineer
└─ Otherwise → determine next steps
```

### 5. Quality Engineer Verifies

```
Quality Engineer runs Tier 1/2/3 checklist:
├─ Tests pass? Lint clean? Coverage maintained?
├─ No scope creep? No security issues?
├─ Model assessment (was Haiku suitable?)
└─ Moves to artifacts/queue/done/{task_id}-{decision}.yaml
   (PASS, FAIL/REWORK, or ESCALATE)
```

### 6. Orchestrator Decides Next Step

```
Orchestrator polls artifacts/queue/done/:
├─ PROCEED → merge to main
├─ REWORK → create new DELEGATE with feedback
└─ ESCALATE → promote to higher role (Senior/Lead/Principal)
```

### 7. Feedback Loop (Async)

```
Model Engineer (runs periodically):
├─ Analyzes QE feedback from completed tasks
├─ Builds confidence scores per model/task-type
├─ Generates routing recommendations
└─ Orchestrator uses for next similar task
   (self-improving optimization)
```

---

## Cost Optimization (Self-Improving)

Every task contributes to metrics → improves future recommendations.

**Example:**

```
Day 1: Task "medium-complexity auth"
  → Routed to Haiku high-effort (recommended baseline)
  → Completed: quality 90, cost $0.13, tokens 18.5K
  → Metrics recorded

Day 2: TokenAdvisor analyzes
  → Haiku is 88-92 quality on auth (proven)
  → Model Engineer confidence: 92%

Day 7: Same task type arrives
  → Model Engineer recommends Haiku (high confidence)
  → Cost is known ($0.13), quality is known (90)
  → Same task routed optimally

Day 30: A/B test completes
  → Tested Sonnet on auth (was question mark)
  → Sonnet: quality 94, cost $0.16 (23% more expensive)
  → Decision: Keep Haiku for medium-complexity, upgrade to Sonnet for high-complexity

Day 60: New model released (Haiku 4.6)
  → Run 5-task eval on low-complexity
  → If quality ≥ current AND cost ≤ current → upgrade all
  → Automatic model shift down, cost improvements
```

**Result:** 25-30% cost reduction while maintaining/improving quality.

---

## The 8 Roles (Quick Reference)

| Role | Model | Cost | Primary Use |
|------|-------|------|-------------|
| **Orchestrator** | Haiku | 60% of spend | Route tasks, manage queue, apply recommendations |
| **Engineer** | Haiku | 18% of spend | Execute well-planned tasks (low-medium complexity) |
| **Senior Engineer** | Sonnet | 7% of spend | Complex coding, planning, diagnosis |
| **Lead Engineer** | Sonnet | 2% of spend | Code review, unblock stuck tasks |
| **Principal Engineer** | Opus | 1% of spend | Cross-service architecture |
| **Security Engineer** | Opus | 1% of spend | Security audits, threat modeling |
| **Quality Engineer** | Sonnet | 8% of spend | Quality gate verification, model assessment |
| **Model Engineer** | Sonnet | 3% of spend | Analyze feedback, optimize routing |

**Orchestrator:** Runs in harness, polls queue every 30-60s. Routes per AGENTS.md decision tree.

**Quality Engineer:** Verifies Tier 1/2/3 checklist. Assesses model suitability for Model Engineer feedback loop.

**See:** `orchestration/AGENTS.md` (role definitions)  
**See:** `orchestration/SKILLS.md` (role-specific workflows)  
**See:** `orchestration/QUEUE-PROTOCOL.md` (queue mechanics)

---

## Key Concepts

### Queue-Based Delegation

Work flows through a simple 3-state queue:

```
incoming/          → New tasks waiting for routing
  ↓
processing/        → Work assigned to agents (awaiting HANDBACK)
  ↓
done/              → Completed work (PROCEED/REWORK/ESCALATE)
```

Agents don't know about each other; the queue is the mediator.
Everything is stored for auditability: `artifacts/queue/` + `artifacts/delegates/`

### DELEGATE/HANDBACK Protocol

Compact structured markup:

**Orchestrator → Engineer (DELEGATE):**
```yaml
task_id: 2026-04-24-fix-timeout
role: Engineer
model: claude-haiku-4-5
scope: Fix token timeout in {service-name}; no Cognito changes
context:
  - File: lambda/api/main.go:92
  - Root cause: Client clock skew
plan:
  1. Write test showing grace period behavior
  2. Modify line 92 for 30s grace window
  3. Run "make verify"
success_criteria:
  - Tests pass, coverage maintained
  - Mobile e2e tests pass
```

**Engineer → Orchestrator (HANDBACK):**
```yaml
task_id: 2026-04-24-fix-timeout
status: complete
deliverables:
  - Modified: lambda/api/main.go:92
  - Added: lambda/api/main_test.go:145 (TestTokenGrace)
tests:
  - "make verify": PASS (47 tests, 89% coverage)
tokens_in: 1200
tokens_out: 820
model: claude-haiku-4-5
duration_minutes: 18
escalations: 0
```

### Quality Gates (Mandatory)

**Tier 1 (all tasks):**
- Lint + tests pass
- No new errors
- In-scope changes only
- Tests added for new code
- No production hazards

**Tier 2 (Senior+):**
- Coverage ≥80%
- Documentation of decisions
- Plan completeness

**Tier 3 (Principal/Security):**
- Architecture adherence
- IAM correctness
- Cross-service contracts

Prevent bad code from merging.

### Metrics & Feedback

Every task produces metrics → daily analysis → model recommendations improve → next task better routed.

```
Task metrics:
  tokens_in, tokens_out
  quality_score
  cost_usd
  escalations
  duration_minutes

Stored in: ~/.claude/metrics/YYYY-MM-DD/

Analyzed daily:
  TokenAdvisor Scheduler (17:00)
  → Daily digest + anomalies + opportunities

Updated based on analysis:
  Model Engineer confidence scores
  A/B test proposals
  Model assignment table

Next task routed:
  With updated model recommendations
  Self-improving loop
```

---

## When to Use This System

✅ **Good fit:**
- Codebases with 5+ services (multi-repo coordination)
- Teams wanting cost optimization (feedback loops)
- High-quality outputs (quality gates, quorum voting)
- Autonomous operation (schedulers, automation)

❌ **Not needed:**
- Single-file changes ("fix typo in README")
- Simple tasks (<30 min)
- Low-stakes work (no cost/quality concerns)

---

## Key Files

| File | Read if... |
|------|-----------|
| `orchestration/AGENTS.md` | You need to understand routing rules |
| `orchestration/HANDOFF.md` | You're handing off work to an agent |
| `orchestration/QUALITY.md` | You're reviewing code (quality gates) |
| `operations/METRICS.md` | You want to understand metrics schema |
| `operations/TOKENADVISOR.md` | You want to understand cost analysis |
| `guides/SYSTEM_INTEGRATION.md` | You want the full 12-month roadmap |
| `guides/CLAUDE.md` | You're a new team member (start here) |
| `skills/*/skills/*.md` | You need details on a specific skill |

---

## Operational Automation (Phase 2E+)

The system runs itself daily:

```
09:00 - A/B Test Automation
        Proposes tests from Model Engineer recommendations
        
10:00 - Model Engineer Automation
        Analyzes incoming task → recommends best model
        
17:00 - TokenAdvisor Scheduler
        Reads metrics from past 24h
        Generates daily digest + opportunities
        
18:00 - Orchestrator
        Routes next batch with recommended models
```

**Result:** Self-improving system with no manual intervention needed.

---

## Integration

**This system integrates with:**
- ✅ User/Copilot interface (receives tasks)
- ✅ Code repositories (git clone, edit, push)
- ✅ GitHub Actions CI (runs tests post-push)
- ✅ Local metrics storage (~/.claude/metrics/)

**This system does NOT require:**
- ❌ Cloud databases
- ❌ Slack/email (user-initiated)
- ❌ External APIs
- ❌ Special infrastructure

Fully autonomous, local, self-contained.

---

## Year 1 Projections

| Metric | Baseline | Month 3 | Month 6 | Month 12 |
|--------|----------|---------|---------|----------|
| Cost/task | $0.21 | $0.17 | $0.16 | $0.15 |
| Annual cost | $252 | $204 | $192 | $180 |
| Reduction | 0% | 19% | 24% | 29% |
| Quality | 85-90 | 90-93 | 91-94 | 91-95 |
| Throughput | 200 tasks/mo | 250-300 | 300-350 | 350-400 |

---

## Next Steps

1. **Load context:** Read `guides/CLAUDE.md` + `orchestration/AGENTS.md`
2. **Understand routing:** Memorize the 5-step decision tree
3. **Study your role:** Read your role's `skills/*/skills/` subdirectory
4. **Practice:** Run 1-2 sample tasks with feedback
5. **Operationalize:** Set up metrics directory + cron jobs for automations

See `guides/SYSTEM_INTEGRATION.md` for detailed Week 1-4 deployment checklist.

---

## Support

- **Questions about routing?** → See `orchestration/AGENTS.md`
- **Questions about handoffs?** → See `orchestration/HANDOFF.md`
- **Questions about a skill?** → See `skills/<role>/skills/<skill-name>.md`
- **Questions about quality?** → See `orchestration/QUALITY.md`
- **Questions about costs?** → See `operations/TOKENADVISOR.md`
- **Questions about roadmap?** → See `guides/SYSTEM_INTEGRATION.md`
- **New team member?** → Start with `guides/CLAUDE.md`

---

**This directory is complete, self-contained, and production-ready.**

Load `agentic-engineers/` as a unit. Everything you need is here.
