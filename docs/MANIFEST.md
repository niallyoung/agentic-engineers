# Agentic Engineers — Complete File Manifest

**Every file in the agentic-engineers system, organized by purpose and location.**

This is the authoritative index. When opening this directory, read this file to discover all content.

---

## 📋 Quick Navigation

| Section | Purpose |
|---------|---------|
| **START HERE** | Entry points for new users |
| **CONFIGURATION** | Locked settings and quick references |
| **SETUP & ENFORCEMENT** | Rules and auto-load mechanism |
| **DOCUMENTATION** | Comprehensive guides and learning materials |
| **ORCHESTRATION** | How work flows and tasks are managed |
| **OPERATIONS** | Metrics collection and cost optimization |
| **REFERENCE** | Architecture standards and patterns |
| **SKILLS** | 38 specialized capabilities by role |

---

## 🚀 START HERE (3 files)

Read these first when opening the directory:

| File | Size | Purpose | Read Time |
|------|------|---------|-----------|
| `README.md` | 445 lines | System overview, quick start, architecture | 5 min |
| `MANIFEST.md` | *this file* | Complete file listing and navigation | 10 min |
| `guides/CLAUDE.md` | 478 lines | Team context, 8-role model, integration | 10 min |

**New to the system?** Start with README.md → MANIFEST.md → guides/CLAUDE.md (25 min total).

---

## 🔐 CONFIGURATION (config/ folder, 3 files)

System configuration — locked and not meant for frequent editing.

### config/README.md
- **Purpose:** Explains the configuration folder
- **Contains:** Overview of MODEL_ASSIGNMENTS_LOCKED.md and QUICK_REFERENCE.md
- **Size:** ~50 lines
- **Read when:** Understanding folder purpose

### config/MODEL_ASSIGNMENTS_LOCKED.md
- **Purpose:** Definitive model assignments, progression hierarchy, optimization strategy
- **Contains:**
  - Base role assignments table (model, effort level, thinking flag, cost per task)
  - Model progression hierarchy: Haiku 4.5 → Sonnet 4.5 → 4.6 → Opus 4.6 → 4.7
  - Effort levels table (low/medium/high/max with cost impact)
  - Thinking flag impact on cost (-20% without, +40% with)
  - Optimization strategy algorithm (cost-first with quality gate)
  - Real-world optimization examples
  - Cost summary and Year 1 projections
- **Size:** 203 lines
- **Read when:** Understanding model assignments, cost optimization strategy

### config/QUICK_REFERENCE.md
- **Purpose:** 1-page cheat sheet for task routing (print and keep handy)
- **Contains:**
  - Role table with complexity/scope/specialty → recommended role
  - 5-step routing decision tree
  - Effort level quick reference
  - Escalation paths
  - Quality gate checklist (Tier 1)
- **Size:** 170 lines
- **Read when:** Before routing a task, print and reference during execution

---

## ⚙️ SETUP & ENFORCEMENT (setup/ folder, 3 files)

Installation rules and enforcement mechanisms that define how the system operates.

### setup/README.md
- **Purpose:** Explains setup folder and installation process
- **Contains:** New agent setup steps, hooks configuration, project initialization
- **Size:** ~40 lines
- **Read when:** Setting up a new agent or understanding enforcement

### setup/copilot-instructions.md
- **Purpose:** Enforcement rules and auto-load mechanism (REQUIRED READING)
- **Contains:**
  - Enforcement rules (what agents must/must not do)
  - Auto-load mechanism (loads entire agentic-engineers/ context)
  - Learning path (what to read and in what order)
  - Git workflow rules (SSH only, no --no-verify, conventional commits)
  - Role-specific expectations
  - Feedback loops and metrics reporting
- **Size:** 354 lines
- **Read when:** FIRST, before any task (establishes rules and context)

### setup/GLOBAL_COPILOT_INSTRUCTIONS.md
- **Purpose:** Reference copy of global Copilot CLI enforcement rules
- **Contains:** Global rules that apply to all projects
- **Size:** ~200 lines
- **Read when:** Debugging enforcement issues or understanding global context

---

## 📚 DOCUMENTATION (guides/ folder, 9 files)

Comprehensive learning materials and team documentation.

### guides/README.md
- **Purpose:** Explains guides folder
- **Contains:** Core learning path, documentation index, audience guide
- **Size:** ~50 lines
- **Read when:** Finding specific documentation

### guides/CLAUDE.md
- **Purpose:** Team context, role definitions, integration with ERS platform
- **Contains:**
  - 8-role model overview
  - Directory structure (detailed)
  - Key concepts (DELEGATE/HANDBACK, quality gates, metrics)
  - Operational automation schedule (daily loops)
  - Integration points
  - Onboarding instructions
- **Size:** 478 lines
- **Read when:** Understanding the full team structure and how it works

### guides/INDEX.md
- **Purpose:** Complete file catalog and quick reference by topic
- **Contains:**
  - Core documents reading order
  - File index by category (orchestration, operations, reference, skills)
  - Complete directory tree (current structure)
  - Quick links by role
  - Support reference (question → file mapping)
  - Team manager checklist
- **Size:** 422 lines
- **Read when:** Finding a specific file or topic

### guides/DEPLOYMENT_STATUS.md
- **Purpose:** Phase tracking, capacity, and cost projections
- **Contains:** Current deployment phase, milestones, metrics, Year 1 projections
- **Size:** ~200 lines
- **Read when:** Understanding project status and timeline

### guides/SYSTEM_INTEGRATION.md
- **Purpose:** 12-month roadmap and full architecture
- **Contains:**
  - Phase breakdown (Phase 1-4+)
  - Architecture design decisions
  - Integration patterns
  - Automation roadmap
  - Success metrics
- **Size:** ~300 lines
- **Read when:** Strategic planning or understanding full roadmap

### guides/WORKFLOW_TEST_EXAMPLE.md
- **Purpose:** End-to-end workflow example with metrics
- **Contains:**
  - Complete example task flow
  - DELEGATE markup example
  - Agent execution
  - HANDBACK with metrics
  - Quality Engineer verification
  - Metrics recording
- **Size:** ~200 lines
- **Read when:** Learning by example (most practical guide)

### guides/IMPLEMENTATION_COMPLETE.md
- **Purpose:** Summary of Phase 2C completion
- **Contains:**
  - Phase 2C deliverables
  - System readiness checklist
  - Known limitations
  - Next phase preview
- **Size:** ~150 lines
- **Read when:** Understanding current system readiness

### guides/AUDIT_AGENTS_ROLES_SKILLS.md
- **Purpose:** Comprehensive audit of consistency and gaps (archived reference)
- **Contains:**
  - Agent-by-agent skill inventory
  - Gap analysis
  - Overlap detection
  - Consistency checks
- **Size:** ~300 lines
- **Read when:** Reviewing system completeness (historical reference)

### guides/ORCHESTRATION_v1_ARCHIVED.md
- **Purpose:** Earlier orchestration version (reference only)
- **Contains:**
  - Previous orchestration design
  - Why it changed
  - Historical context
- **Size:** ~150 lines
- **Read when:** Understanding design evolution

---

## 🔄 ORCHESTRATION (orchestration/ folder, 11+ files)

How work flows through the system, from task assignment to completion, plus real-time usage budget tracking.

### orchestration/README.md
- **Purpose:** Explains orchestration folder
- **Contains:**
  - Workflow overview (task → routing → execution → QA → acceptance)
  - File purposes
  - Key concepts (routing decision tree, quality gates)
  - When to use each file
- **Size:** ~50 lines
- **Read when:** Understanding folder purpose

### orchestration/AGENTS.md
- **Purpose:** 8-role model with routing rules and cost tiers
- **Contains:**
  - Role table (role, model, effort, cost tier, primary use)
  - Escalation paths
  - 5-step routing decision tree (complexity, scope, specialty → role)
  - Example DELEGATE/HANDBACK blocks
  - Escalation procedures
- **Size:** 382 lines
- **Read when:** Routing a task (most critical file for task distribution)

### orchestration/HANDOFF.md
- **Purpose:** DELEGATE/HANDBACK markup protocol and validation
- **Contains:**
  - DELEGATE markup specification (task details to send agent)
  - HANDBACK markup specification (results to return)
  - Validation rules (required fields, formatting)
  - Example workflows (4 complete scenarios)
  - Metrics reporting in HANDBACK
- **Size:** 302 lines
- **Read when:** Creating task handoffs or understanding markup format

### orchestration/QUALITY.md
- **Purpose:** Quality gate checklist (Tier 1/2/3)
- **Contains:**
  - Tier 1 checklist (all tasks: lint, tests, coverage, no hazards)
  - Tier 2 checklist (Senior+: documentation, completeness)
  - Tier 3 checklist (Principal/Security: architecture, IAM, contracts)
  - Verification procedures
  - Escalation when gates fail
- **Size:** 206 lines
- **Read when:** Verifying task completion (Quality Engineer primary use)

### orchestration/USAGE-BUDGET-MANAGER.md
- **Purpose:** Real-time token budget tracking and dynamic model recommendations
- **Contains:**
  - Session and weekly budget monitoring
  - Intelligent recommendations based on budget status
  - Warning system for model complexity reduction
  - Integration with Orchestrator role
  - Configuration for temporary session-only adjustments
- **Size:** 280 lines
- **Read when:** Understanding usage budget awareness (Orchestrator primary use)

### orchestration/USAGE-BUDGET-INTEGRATION.md
- **Purpose:** Integration guide for Usage Budget Manager into Orchestrator workflow
- **Contains:**
  - Quick reference for budget checking commands
  - Orchestrator workflow integration examples
  - Handoff protocol with budget awareness
  - User interaction points and approval workflow
  - Escalation levels and alerting
- **Size:** 220 lines
- **Read when:** Implementing budget-aware task routing (Orchestrator setup)

### orchestration/TOKEN-USAGE-TRACKING.md
- **Purpose:** Historical token usage capture and trend analysis over time
- **Contains:**
  - Automated snapshot capture (session/weekly percentages)
  - Trend analysis with velocity and reset forecasting
  - Cron setup for periodic collection
  - Voice alerts on usage thresholds
  - Integration with Orchestrator workflow
  - Troubleshooting and future enhancements
- **Size:** 350 lines
- **Read when:** Setting up historical usage tracking or analyzing trends (Orchestrator setup)

### orchestration/scripts/usage-budget.sh
- **Purpose:** Shell wrapper for budget checking and recommendations
- **Contains:** Argument parsing, Python script invocation, output routing
- **Size:** ~60 lines
- **Used by:** Orchestrator (called every 30 minutes during active sessions)
- **Read when:** Understanding budget check integration

### orchestration/scripts/usage_budget_check.py
- **Purpose:** Core budget calculation and recommendation logic
- **Contains:**
  - Budget status determination (GREEN/YELLOW/RED)
  - Model tier recommendations
  - Human-readable report formatting
  - JSON output for automation
  - Reset check logic
- **Size:** ~320 lines
- **Used by:** usage-budget.sh wrapper script
- **Read when:** Understanding budget calculation algorithms

### orchestration/scripts/capture_token_usage.sh
- **Purpose:** Snapshot current token usage to historical log (JSON Lines)
- **Contains:**
  - Calls usage_budget_check.py for current state
  - Appends timestamp, session%, weekly%, status to usage_history.jsonl
  - Voice alerts on usage thresholds (70% warning, 85% critical)
  - Optional verbose output
- **Size:** ~110 lines
- **Used by:** usage-tracking.sh, cron jobs
- **Read when:** Setting up automated usage capture

### orchestration/scripts/analyze_usage_trends.py
- **Purpose:** Analyze historical usage data and compute trend metrics
- **Contains:**
  - Load JSON Lines history
  - Calculate min/max/avg, velocity (% per hour), trend direction
  - Estimate time to reset based on consumption rate
  - Human-readable report and JSON output
  - Confidence in forecasts
- **Size:** ~200 lines
- **Used by:** usage-tracking.sh
- **Read when:** Understanding trend analysis algorithms

### orchestration/scripts/usage-tracking.sh
- **Purpose:** Unified wrapper for token usage tracking commands
- **Contains:**
  - `capture` — record current usage now
  - `analyze` — show trend report
  - `snapshot` — capture + show current
  - `logs` — show recent entries
  - `cron-setup` — print cron job instructions
- **Size:** ~90 lines
- **Used by:** End users (CLI interface)
- **Read when:** Executing usage tracking commands

---

## 📊 OPERATIONS (operations/ folder, 3 files)

Metrics collection, analysis, and cost optimization.

### operations/README.md
- **Purpose:** Explains operations folder
- **Contains:**
  - Metrics flow overview (execution → HANDBACK → recording → analysis → recommendations)
  - File purposes
  - Key metrics tracked
  - When to use each file
- **Size:** ~50 lines
- **Read when:** Understanding folder purpose

### operations/METRICS.md
- **Purpose:** Metrics collection schema (per-task JSON and session JSONL)
- **Contains:**
  - Per-task metrics JSON schema (all fields with types)
  - Session JSONL format (aggregated metrics)
  - Directory structure (~/.claude/metrics/YYYY-MM-DD/)
  - Example metrics files
  - Field definitions and purposes
- **Size:** 432 lines
- **Read when:** Recording metrics or understanding data structure

### operations/TOKENADVISOR.md
- **Purpose:** Daily metrics analysis framework
- **Contains:**
  - Analysis methodology (cost trends, anomalies, opportunities)
  - Report structure and format
  - Confidence scoring for recommendations
  - Real-world optimization examples
  - A/B test proposal generation
- **Size:** 275 lines
- **Read when:** Analyzing metrics or generating recommendations

---

## 📖 REFERENCE (reference/ folder, 7 files)

Architecture standards, coding patterns, and design guidance from production ERS code.

### reference/README.md
- **Purpose:** Explains reference folder
- **Contains:**
  - File purposes and audiences
  - When to read each document
  - Key concept areas
- **Size:** ~50 lines
- **Read when:** Understanding folder purpose

### reference/CODING_STANDARDS.md
- **Purpose:** Go/TypeScript/CDK naming, testing, and error handling conventions
- **Contains:**
  - Language-specific conventions
  - Naming patterns
  - Testing strategies
  - Error handling patterns
  - Code organization principles
- **Size:** ~250 lines
- **Read when:** Before writing code (primary reference for Engineers)

### reference/DESIGN_PATTERNS.md
- **Purpose:** Architecture and refactoring patterns from production
- **Contains:**
  - Handler patterns (HTTP API, event consumer)
  - Idempotency implementations
  - Caching strategies
  - Concurrency patterns
  - Performance optimization techniques
- **Size:** ~300 lines
- **Read when:** Before architecture decisions (Senior Engineer+ use)

### reference/CQRS_AND_EVENT_SOURCING.md
- **Purpose:** Event-driven architecture, CQRS principles, event replay
- **Contains:**
  - CQRS pattern explanation
  - Event sourcing principles
  - Domain events vs. commands
  - Replay and projection rebuild procedures
  - Event versioning strategy
- **Size:** ~350 lines
- **Read when:** Before event system changes or understanding architecture

### reference/MULTI_AGENT_OPTIMIZATION.md
- **Purpose:** Research on model selection, cost optimization, RLAF
- **Contains:**
  - Model selection algorithms
  - Token burn analysis methodologies
  - Quality-cost tradeoff evaluation
  - A/B testing frameworks
  - Long-term optimization strategies
- **Size:** ~400 lines
- **Read when:** Strategic planning or optimization research (Principal Engineer)

### reference/OPERATIONAL_DASHBOARDS.md
- **Purpose:** Metrics visualization and monitoring setup guide
- **Contains:**
  - Dashboard design principles
  - Key metrics visualization
  - Real-time vs. historical views
  - Alerting and thresholds
  - Tools and implementation
- **Size:** ~200 lines
- **Read when:** Week 3+ (setting up monitoring dashboards)

### reference/TODO.md
- **Purpose:** Phase checklist, deliverables, and milestone tracking
- **Contains:**
  - Phase breakdown with deliverables
  - Milestone tracking
  - Completion checklist by phase
  - Current status markers
  - Next phase preview
- **Size:** ~150 lines
- **Read when:** Project managers tracking progress

---

## 🛠️ SKILLS (skills/ folder, 39 files total)

38 specialized capabilities organized by role, plus folder README.

### skills/README.md
- **Purpose:** Explains skills folder and how to use skills
- **Contains:**
  - Skill distribution by role (38 total)
  - How to load skills when assigned a task
  - Shared skills documentation
  - Skill template structure
- **Size:** ~150 lines
- **Read when:** Learning about skills system

### skills/shared/ (4 files)

Shared skills used by multiple roles.

#### shared/github-cli.md
- **Purpose:** GitHub CLI operations for automation
- **Size:** ~150 lines
- **Used by:** Orchestrator, Engineer
- **Read when:** Automating GitHub operations

#### shared/git-workflow.md
- **Purpose:** Git best practices and workflow standards
- **Size:** ~200 lines
- **Used by:** All roles
- **Read when:** Before committing changes

#### shared/cdk-stack.md
- **Purpose:** CDK patterns for infrastructure
- **Size:** ~180 lines
- **Used by:** Engineer, Senior Engineer
- **Read when:** Building infrastructure

#### shared/sigv4-client.md
- **Purpose:** IAM SigV4 signing for inter-service calls
- **Size:** ~150 lines
- **Used by:** Senior Engineer, Engineer
- **Read when:** Implementing inter-service communication

### skills/orchestrator/skills/ (11 files)

Orchestrator specialization: task routing, metrics, automation.

#### orchestrator/skills/task-routing.md
- **Purpose:** Task routing decision methodology
- **Size:** ~150 lines

#### orchestrator/skills/metrics-collection.md
- **Purpose:** How to collect and record task metrics
- **Size:** ~120 lines

#### orchestrator/skills/model-engineer-coordination.md
- **Purpose:** Coordinating with Model Engineer for optimization
- **Size:** ~100 lines

#### orchestrator/skills/github-cli-operations.md
- **Purpose:** GitHub CLI automation for orchestration
- **Size:** ~100 lines

#### orchestrator/skills/cicd-watch.md
- **Purpose:** Monitoring CI/CD pipeline status
- **Size:** ~120 lines

#### orchestrator/skills/token-advisor.md
- **Purpose:** Manual token advisor analysis
- **Size:** ~150 lines

#### orchestrator/skills/tokenadvisor-scheduler.md
- **Purpose:** Automated daily metrics analysis scheduling
- **Size:** ~100 lines

#### orchestrator/skills/model-engineer.md
- **Purpose:** Model analysis and selection optimization
- **Size:** ~180 lines

#### orchestrator/skills/model-engineer-automation.md
- **Purpose:** Automated model recommendation generation
- **Size:** ~120 lines

#### orchestrator/skills/ab-testing-framework.md
- **Purpose:** A/B test design and methodology
- **Size:** ~200 lines

#### orchestrator/skills/ab-test-automation.md
- **Purpose:** Automated A/B test execution and analysis
- **Size:** ~150 lines

### skills/engineer/skills/ (5 files)

Engineer specialization: implementation, testing, builds.

#### engineer/skills/implementation-coding.md
- **Purpose:** TDD workflow (RED → GREEN → REFACTOR)
- **Size:** ~200 lines

#### engineer/skills/local-ci-skill.md
- **Purpose:** Local CI pipeline (verify, review, diff)
- **Size:** ~150 lines

#### engineer/skills/playwright-ui-testing.md
- **Purpose:** E2E testing patterns for {service-name}
- **Size:** ~180 lines

#### engineer/skills/lambda-handler.md
- **Purpose:** Lambda handler scaffolding (HTTP API, Event Consumer)
- **Size:** ~170 lines

#### engineer/skills/makefile.md
- **Purpose:** Standard Makefile patterns (describe → lint → test → build → deploy)
- **Size:** ~160 lines

### skills/senior-engineer/skills/ (2 files)

Senior Engineer specialization: complex coding, architecture.

#### senior-engineer/skills/api-resilience.md
- **Purpose:** Resilient API client patterns (retry, token refresh, maintenance)
- **Size:** ~180 lines

#### senior-engineer/skills/event-consumer.md
- **Purpose:** Event consumer patterns (SNS FIFO → SQS FIFO → Lambda with idempotency)
- **Size:** ~200 lines

### skills/lead-engineer/skills/ (1 file)

Lead Engineer specialization: code review and quality.

#### lead-engineer/skills/code-review.md
- **Purpose:** Code review standards and verification
- **Size:** ~250 lines

### skills/principal-engineer/skills/ (3 files)

Principal Engineer specialization: architecture, design, strategy.

#### principal-engineer/skills/architecture-design.md
- **Purpose:** Cross-service architecture design methodology
- **Size:** ~220 lines

#### principal-engineer/skills/design-decision-documentation.md
- **Purpose:** Architecture Decision Record (ADR) format
- **Size:** ~180 lines

#### principal-engineer/skills/system-tradeoff-analysis.md
- **Purpose:** Systematic tradeoff analysis (cost, quality, timeline, risk)
- **Size:** ~200 lines

### skills/security-engineer/skills/ (3 files)

Security Engineer specialization: threat modeling, vulnerabilities, security architecture.

#### security-engineer/skills/threat-modeling.md
- **Purpose:** STRIDE threat modeling methodology
- **Size:** ~240 lines

#### security-engineer/skills/vulnerability-assessment.md
- **Purpose:** Vulnerability testing and CVE assessment
- **Size:** ~200 lines

#### security-engineer/skills/security-architecture-review.md
- **Purpose:** Security design review checklist
- **Size:** ~210 lines

### skills/quality-engineer/skills/ (4 files)

Quality Engineer specialization: QA, verification, quorum voting.

#### quality-engineer/skills/overview.md
- **Purpose:** Quality Engineer role overview and context
- **Size:** ~150 lines

#### quality-engineer/skills/code-quality-analysis.md
- **Purpose:** Code quality assessment methodology
- **Size:** ~180 lines

#### quality-engineer/skills/quorum-qe.md
- **Purpose:** Quorum voting process (1/3/5 QE verification)
- **Size:** ~160 lines

#### quality-engineer/skills/e2e-playwright.md
- **Purpose:** E2E testing with Playwright
- **Size:** ~200 lines

### skills/model-engineer/skills/ (5 files)

Model Engineer specialization: optimization, recommendations, analysis.

#### model-engineer/skills/model-analysis.md
- **Purpose:** Analyzing model performance across tasks
- **Size:** ~180 lines

#### model-engineer/skills/model-recommendation.md
- **Purpose:** Generating ranked model recommendations
- **Size:** ~200 lines

#### model-engineer/skills/cost-quality-tradeoff.md
- **Purpose:** Evaluating cost vs. quality tradeoffs
- **Size:** ~180 lines

#### model-engineer/skills/model-comparison.md
- **Purpose:** Comparing models across historical data
- **Size:** ~150 lines

#### model-engineer/skills/quality-feedback-analysis.md
- **Purpose:** Extracting patterns from QE feedback
- **Size:** ~170 lines

---

## 📊 File Statistics

| Category | Count | Lines | Purpose |
|----------|-------|-------|---------|
| **Entry Points** | 2 | ~900 | README, MANIFEST |
| **Configuration** | 3 | ~430 | Locked settings |
| **Setup** | 3 | ~600 | Enforcement, rules |
| **Documentation** | 9 | ~2,400 | Guides, learning |
| **Orchestration** | 4 | ~1,100 | Workflow, routing |
| **Operations** | 3 | ~750 | Metrics, analysis |
| **Reference** | 7 | ~2,000 | Standards, patterns |
| **Skills** | 39 | ~6,700 | 38 capabilities + README |
| **TOTAL** | **70** | **~15,000** | Complete system |

---

## 🗺️ How to Navigate This Directory

### If you're Claude Code or GitHub Copilot:

1. **First visit:** Read README.md (entry point)
2. **Second read:** Read MANIFEST.md (this file - complete listing)
3. **Orient yourself:** Read guides/CLAUDE.md (team context)
4. **Understand workflow:** Read orchestration/AGENTS.md (routing rules)
5. **Find specific content:** Use INDEX.md section mappings or search by role/topic below

### By Role (find your skills):

- **Orchestrator:** Start with orchestration/AGENTS.md, load skills/orchestrator/skills/
- **Engineer:** Start with guides/CLAUDE.md, load skills/engineer/skills/
- **Senior Engineer:** Load skills/senior-engineer/skills/ + reference/DESIGN_PATTERNS.md
- **Lead Engineer:** Load skills/lead-engineer/skills/ + orchestration/QUALITY.md
- **Principal Engineer:** Load skills/principal-engineer/skills/ + reference/MULTI_AGENT_OPTIMIZATION.md
- **Security Engineer:** Load skills/security-engineer/skills/ + reference/CQRS_AND_EVENT_SOURCING.md
- **Quality Engineer:** Load skills/quality-engineer/skills/ + orchestration/QUALITY.md
- **Model Engineer:** Load skills/model-engineer/skills/ + operations/

### By Topic (find what you need):

- **Routing a task:** config/QUICK_REFERENCE.md, orchestration/AGENTS.md
- **Handing off work:** orchestration/HANDOFF.md
- **Checking token budget:** orchestration/USAGE-BUDGET-MANAGER.md, skills/usage-tracking/SKILL.md
- **Analyzing usage trends:** skills/usage-tracking/SKILL.md, orchestration/TOKEN-USAGE-TRACKING.md
- **Verifying quality:** orchestration/QUALITY.md, skills/quality-engineer/skills/
- **Recording metrics:** operations/METRICS.md
- **Optimizing cost:** operations/TOKENADVISOR.md, skills/model-engineer/skills/
- **Writing code:** reference/CODING_STANDARDS.md, skills/engineer/skills/
- **Architecture decisions:** reference/DESIGN_PATTERNS.md, skills/principal-engineer/skills/
- **Security review:** skills/security-engineer/skills/
- **Event architecture:** reference/CQRS_AND_EVENT_SOURCING.md
- **Understanding phase:** guides/DEPLOYMENT_STATUS.md
- **Long-term roadmap:** guides/SYSTEM_INTEGRATION.md
- **Learning by example:** guides/WORKFLOW_TEST_EXAMPLE.md

### By Folder (comprehensive by area):

| Folder | Files | Start With | Purpose |
|--------|-------|-----------|---------|
| **config/** | 3 | MODEL_ASSIGNMENTS_LOCKED.md | System configuration |
| **setup/** | 3 | copilot-instructions.md | Rules & enforcement |
| **guides/** | 9 | CLAUDE.md | Learning & documentation |
| **orchestration/** | 4 | AGENTS.md | Workflow & routing |
| **operations/** | 3 | METRICS.md | Metrics & optimization |
| **reference/** | 7 | CODING_STANDARDS.md | Standards & patterns |
| **skills/** | 41+ | [your-role]/skills/ | Role capabilities |

---

## 🛠️ Utility Skills (used across all agents)

Special-purpose skills available to any agent during session work.

### skills/voice-notify/
- **SKILL.md** — Voice notification skill definition (voice alerts on lifecycle events)
- **VOICE-CONFIG.md** — Voice palette and agent assignments (Daniel primary, Samantha secondary)
- **scripts/voice-notify.sh** — TTS wrapper (macOS say / Linux espeak)
- **Purpose:** Automatic voice alerts for agent status updates and critical events
- **Used by:** All agents (integrated with key lifecycle events)

### skills/usage-tracking/
- **SKILL.md** — Token usage capture and analysis skill
- **README.md** — Quick-start guide for agents
- **scripts/capture_token_usage.sh** — Snapshot current usage to history log
- **scripts/analyze_usage_trends.py** — Analyze historical trends and forecast resets
- **scripts/usage-tracking.sh** — Unified CLI wrapper (capture, analyze, snapshot, logs)
- **Purpose:** Real-time and historical token usage analysis for budget-aware decisions
- **Used by:** Orchestrator (primary), all agents (budget-aware decisions)
- **Integration:** Called at session start, checkpoints, pre-delegation, session end

---

## ✅ Completeness Verification

Every file listed above:
- ✓ Exists in the directory
- ✓ Has a known purpose
- ✓ Is referenced from at least one other file
- ✓ Is categorized by audience
- ✓ Is discoverable from main entry points

No hidden files. No orphaned files. No ambiguous purposes.

---

## 🎯 How This Ensures Equal Discovery

Both Claude Code and GitHub Copilot now have:

1. **README.md** — Clear entry point
2. **MANIFEST.md** (this file) — Complete file listing with purposes
3. **guides/INDEX.md** — Topic-based quick links
4. **guides/CLAUDE.md** — Full system context
5. **Each folder's README.md** — Folder-specific navigation
6. **Each file's documented purpose** — Clear reason for existence

No matter which AI assistant opens the directory first, or how they discover files, they will find:
- All 70 files
- Clear purpose for each
- Guidance on what to read and when
- Multiple navigation paths (by role, topic, folder, file)
- Equal opportunity to access any content

The system is transparent and fully navigable.

---

**Last updated: 2026-04-25 | 80+ files documented and discoverable | Includes voice-notify and usage-tracking utility skills**
