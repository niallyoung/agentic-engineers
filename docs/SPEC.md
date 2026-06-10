---
name: Agentic Engineers Implementation Specification
description: Current state of the agent orchestration system, queue mechanics, and operational constraints
version: 1.0
updated: 2026-06-08
phase: 5.10 (Monitoring & Continuous Improvement)
status: Current
type: specification
---

# Agentic Engineers Implementation Specification

**Last Updated:** 2026-06-08  
**Current Phase:** 5.10 (Monitoring & Continuous Improvement with Span Capture & Indexing)  
**Constraint:** No external scripts/tools — all work flows through AGENTS via DELEGATE/HANDBACK

---

## Executive Summary

The Agentic Engineers system uses queue-based delegation to route all work through specialized AI agents (Orchestrator, Engineer, Senior Engineer, Quality Engineer, Lead Engineer, Principal Engineer, Security Engineer, Model Engineer). Each agent is assigned a specific role, model, and effort level. Work flows through a file-based queue system (`~/.agentic-engineers/{session-id}/{harness}/queue/`) with complete audit trails. Phase 5.10 adds observability via span capture and artifact indexing, both implemented within agent SKILLS (not external tools).

---

## ORCHESTRATOR-FIRST EXECUTION MODEL (MANDATORY)

**This is a hard constraint. All work MUST flow through the Orchestrator. No exceptions.**

### What This Means

1. **No Direct Agent Invocation**
   - Engineers MUST NOT invoke agents directly via tool calls or message passing
   - Engineers MUST NOT create DELEGATE blocks manually and send them to agents
   - Work only flows through the Orchestrator queue system

2. **All Work Enters the Queue**
   - New tasks arrive as files in `~/.agentic-engineers/{session-id}/{harness}/queue/incoming/{task_id}.yaml`
   - Each session has its own isolated queue partition
   - Orchestrator polls this directory every 30-60 seconds
   - No other entry point exists (no Makefile targets, no scripts, no cron jobs, no ad-hoc invocations)

3. **Orchestrator is the Router**
   - Reads incoming task from session-partitioned queue
   - Applies AGENTS.md routing decision tree to determine which agent to delegate to
   - Creates DELEGATE block in `artifacts/delegates/YYYY-MM-DD/` with complete context
   - Sends DELEGATE to agent
   - Receives HANDBACK from agent
   - Routes HANDBACK to Quality Engineer for verification
   - Moves completed task to session-partitioned `done/` queue
   - Applies Model Engineer recommendations to improve future routing

4. **No External Scripts, Tools, or Cron Jobs (Agent Operations)**
   - **NO Python scripts** for queue management, span capture, indexing, or any other operations
   - **NO Makefile targets** for Orchestrator operations, span capture, or artifact generation (exception: `render-*` targets)
   - **NO shell scripts** for queue automation, task creation, or observability (exception: `renderer/scripts/` for installation only)
   - **NO cron jobs** for polling, index generation, or metrics collection
   - **NO external monitoring or indexing tools** beyond what agents natively produce
   - All functionality is implemented as agent SKILLS (Orchestrator SKILL for span capture, Model Engineer SKILL for artifact indexing)
   
   **EXEMPTIONS (Build & Installation Only):**
   - `renderer/scripts/` — Shell scripts for rendering agents/skills to ~/.copilot/ and ~/.claude/ (called by `make install/render` targets only)
   - `make install`, `make install-copilot`, `make install-claude` — Invoke renderer scripts for framework bootstrap
   - `make render-copilot`, `make render-claude` — Generate dist/ artifacts
   - These are build-time operations, not runtime agent operations. Once installed, all work flows through Orchestrator queue.

### Implementation Requirements for Engineers

**When creating an agent implementation:**

1. **Implement QUEUE POLLING**
   - Orchestrator SKILL detects session-id (from COPILOT_SESSION_ID or filesystem scan)
   - Orchestrator SKILL polls `~/.agentic-engineers/{session-id}/{harness}/queue/incoming/` every 30-60 seconds
   - Each poll reads new tasks from session's queue partition only
   - This is the ONLY way work enters the system

2. **Implement ROUTING**
   - Orchestrator applies AGENTS.md decision tree to route each task to the correct agent
   - Decision tree is documented in AGENTS.md; Orchestrator implements it
   - All routing logic is inside the Orchestrator agent; no external configuration

3. **Implement DELEGATE/HANDBACK PROTOCOL**
   - Orchestrator creates DELEGATE blocks in YAML format per HANDOFF.md spec
   - Agents receive DELEGATE, execute work, return HANDBACK
   - DELEGATE includes: scope, context, plan (for Engineer), success criteria
   - HANDBACK includes: status, deliverables, test results, token counts, model assessment
   - Structured format is machine-readable for metrics and span capture

4. **Implement SPAN CAPTURE**
   - When Orchestrator receives HANDBACK from any agent, capture OpenTelemetry span
   - Extract: task_id, agent_role, agent_model, status, tokens_in, tokens_out, decision
   - Write SPAN to `artifacts/2026-MM-DD/SPAN-{timestamp}-{agent_type}.yaml`
   - This is the ONLY observability mechanism; no external logging or monitoring

5. **Implement ARTIFACT INDEXING**
   - Model Engineer generates `artifacts/index.json` as part of feedback loop analysis
   - Scans artifacts/2026-*/ for DELEGATE/HANDBACK/SPAN metadata
   - Creates searchable index by: file_type, task_id, agent_type, status
   - Calculates: total_tokens, total_cost, critical_issues, escalations
   - This is the ONLY cost analysis and trend reporting mechanism

### What NOT to Do

**PROHIBITED ACTIVITIES (NO EXCEPTIONS, EVER):**

- ❌ Do NOT write Python scripts that manage queues, capture spans, or generate indexes (exception: `renderer/scripts/` for installation only)
- ❌ Do NOT add Makefile targets for Orchestrator operations (exception: `render-*` and `install*` targets that invoke renderer scripts)
- ❌ Do NOT create shell scripts for queue automation, task processing, or external invocation (exception: `renderer/scripts/` for build-time rendering only)
- ❌ Do NOT set up cron jobs for any system operations (all scheduling via agent SKILLs)
- ❌ Do NOT invoke subprocess, os.system(), or exec() in agent code (exception: `src/skills/_meta/evaluation_framework/` for real harness invocation in functional tests only)
- ❌ Do NOT invoke agents directly without going through Orchestrator queue
- ❌ Do NOT create manual DELEGATE blocks and send them to agents
- ❌ Do NOT skip quality checks or escalation rules
- ❌ Do NOT implement observability outside of agent SKILLS
- ❌ Do NOT use "trivial fixes" or other undefined escape clauses to bypass queue
- ❌ Do NOT allow CI/CD or external systems to invoke scripts directly
- ❌ Do NOT allow any automated external system to write files directly to `~/.agentic-engineers/{session-id}/{harness}/queue/incoming/` — all queue entries originate from humans or the Orchestrator
- ❌ Do NOT create automated cron job installers or pre-configured cron jobs

**Why This Constraint Exists:**
The queue-first model ensures all work is tracked, routable, optimizable, and auditable. External scripts and manual invocations create gaps in observability, break routing logic, and prevent the system from improving itself through the feedback loop. By making Orchestrator the single point of control, we guarantee:
- ✅ Complete audit trail of all work
- ✅ Correct routing via decision tree
- ✅ Accurate cost tracking via span capture

---

## SDLC ENFORCEMENT HOOKS (MANDATORY)

**Git hooks are required for all contributors.** They enforce SPEC.md compliance and quality gates at commit and push time.

### What Hooks Enforce

| Hook | Enforces | Severity |
|------|----------|----------|
| **pre-commit** | SPEC compliance (no external scripts, cron files, process execution) | ❌ BLOCK |
| **pre-commit** | Secret detection (API keys, passwords, tokens) | ❌ BLOCK |
| **pre-commit** | YAML/JSON validity | ❌ BLOCK |
| **commit-msg** | Message format and length | ❌ BLOCK |
| **commit-msg** | DELEGATE/HANDBACK protocol compliance | ❌ BLOCK |
| **pre-push** | Agent YAML frontmatter validity | ❌ BLOCK |
| **pre-push** | Test suite execution | ⚠️ WARN |
| **pre-push** | Documentation consistency | ❌ BLOCK |

### Installation

Hooks are installed automatically by `make install`:

```bash
make install
```

Or manually:

```bash
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/commit-msg .githooks/pre-push
```

### Bypassing Hooks

Bypassing hooks requires **documented justification** and is only permitted for genuine emergencies:

```bash
# Bypass SPEC/secret checks
BYPASS_HOOK_VALIDATION=true git commit -m "emergency: reason"

# Bypass all pre-commit checks
SKIP_HOOKS=1 git commit -m "emergency: reason"

# Bypass pre-push checks
SKIP_HOOKS=1 git push
```

**Every bypass MUST include:**
- Documented reason (what's the emergency?)
- Approver name (who authorized this?)
- Follow-up task (how will this be fixed?)

**Never bypass for:**
- Lazy commits that violate SPEC
- Avoiding code review
- Skipping tests
- Committing secrets
- Routine work

### Full Reference

See [docs/SDLC-HOOKS.md](SDLC-HOOKS.md) for comprehensive hook documentation including:
- Complete list of all checks
- Exact error messages
- Troubleshooting guide (30+ scenarios)
- Bypass procedures and authorization
- Audit trail requirements

---

## DOG-FOOD PRINCIPLE: Self-Improving Through Continuous Feedback

**Core Design Principle (New in Phase 5.10):**

Every agent and quality system we build must be validated by the quality systems it helps improve. This creates a positive feedback loop where improvements compound.

### How It Works

1. **Agent Implementation** → Validated by quality gates
2. **Quality Gates** → Validated by Quality Engineer review
3. **Quality Engineer Review** → Informed by Model Engineer analysis
4. **Model Engineer Optimization** → Improves routing for next task
5. **Next Task** → Routed better → produces better work → improves feedback
6. **Cycle Repeats** → Exponential improvement

### Practical Constraints

- ✅ When implementing feature X, use the quality gates that X improves
- ✅ Agent code must pass the validation rules it implements
- ✅ Quality improvements must be validated by Quality Engineer
- ✅ Feedback from task execution must inform next task routing
- ✅ Metrics from improvements must drive optimization decisions

### Why This Matters

Traditional QA is **reactive**: code → test → fix → deploy (days/weeks)

Dog-fooding is **proactive**: code → quality gate → escalate if needed → fix → next code (minutes)

This creates exponential improvement instead of linear.

**See:** [`docs/PHILOSOPHY-DOG-FOOD.md`](../PHILOSOPHY-DOG-FOOD.md) for full philosophy

---

## DEPRECATION NOTICE: Removed External Scripts & Cron Jobs

**Effective 2026-05-02:** The following files have been removed and MUST NOT be recreated:

**Orchestration Scripts (REMOVED):**
- `orchestration/scripts/process-log-queue.sh`
- `orchestration/scripts/capture_token_usage.sh`
- `orchestration/scripts/manage-credentials.sh`
- `orchestration/scripts/setup-msmtp.sh`
- `orchestration/scripts/send-alert-email.sh`
- `orchestration/scripts/usage-tracking.sh`
- `orchestration/scripts/usage-budget.sh`
- `orchestration/install-automation.sh`

**Cron Job Definitions (REMOVED):**
- `orchestration/config/queue-processor.cron`
- `orchestration/config/metrics-etl.cron`
- `orchestration/config/tokenadvisor.cron`
- `orchestration/config/model-engineer.cron`
- `orchestration/config/ab-testing-monitor.cron`
- `orchestration/config/daily-email-summary.cron`

**Reason:** These files violated the ORCHESTRATOR-FIRST EXECUTION MODEL (MANDATORY) constraint. All logic must flow through AGENTS with SKILLS via DELEGATE/HANDBACK protocol.

**If you need the functionality these scripts provided:**
1. Implement the logic as an Agent SKILL
2. Queue work as a DELEGATE block in `~/.agentic-engineers/{session-id}/{harness}/queue/incoming/`
3. Let Orchestrator route and delegate to the appropriate agent
4. Agent executes and returns HANDBACK

This is the ONLY allowed entry point for all work.
- ✅ Autonomous optimization via Model Engineer feedback
- ✅ No bypasses or edge cases

---

## COMPLETE SCRIPT INVENTORY

This section documents all script files in the repository and their compliance status with the ORCHESTRATOR-FIRST EXECUTION MODEL.

### EXEMPT: Build-Time & Setup Scripts

**Location:** `renderer/scripts/`

These scripts are exempted because they run at build/setup time and do not affect runtime orchestration:

- `renderer/scripts/copilot-guard.sh` — Guard checks for Copilot environment
- `renderer/scripts/copilot-session-init.sh` — Session initialization utility
- `renderer/scripts/render-claude.sh` — Render tooling for Claude model setup
- `renderer/scripts/render-copilot.sh` — Render tooling for Copilot setup
- `renderer/scripts/render-copilot-agents.sh` — Agent rendering helper
- `renderer/scripts/render-copilot-agents.py` — Agent rendering Python helper

**Rationale:** These scripts execute only during development environment setup and build-time rendering. They do not participate in runtime task orchestration or queue processing and therefore do not violate the ORCHESTRATOR-FIRST constraint.

### REFERENCE: Reference Implementations (Non-Invokable)

**Location:** `orchestration/agents/`

These Python files are included as reference impls and documentation but are NOT directly invokable at runtime:

- `orchestration/agents/__init__.py` — Module initialization
- `orchestration/agents/AGENT-IMPLEMENTATION-TEMPLATE.py` — Agent pattern template
- `orchestration/agents/ENGINEER-IMPLEMENTATION-REFERENCE.py` — Engineer agent reference
- `orchestration/agents/ORCHESTRATOR-IMPLEMENTATION-REFERENCE.py` — Orchestrator reference
- `orchestration/agents/artifact_manager.py` — Artifact management utilities
- `orchestration/agents/example_end_to_end.py` — Example workflow documentation
- `orchestration/agents/implementations.py` — Implementation examples
- `orchestration/agents/spec_validator.py` — Specification validation utilities
- `orchestration/agents/testing_harness.py` — Testing framework
- `orchestration/agents/workflow.py` — Workflow utilities
- `orchestration/agents/*.md` — Agent specification documents

**Rationale:** These Python files are included as reference impls, design documentation, and utilities for agent development. All task routing flows through the Orchestrator queue via DELEGATE/HANDBACK protocol. These files are never invoked directly as autonomous scripts and therefore do not violate the ORCHESTRATOR-FIRST constraint.

### COMPLIANT: Approved Skill Scripts

**Location:** `skills/*/scripts/`

All scripts in the skills directory are approved and compliant because they are organized as SKILLS with formal specifications (SKILLS.md). These include:

- `skills/ab-testing/scripts/ab-testing.py`
- `skills/metrics-etl/scripts/metrics-etl.py`
- `skills/model-engineer/scripts/model-engineer.py`
- `skills/tokenadvisor/scripts/daily-email-summary.sh`
- `skills/tokenadvisor/scripts/tokenadvisor.py`
- `skills/usage-tracking/scripts/analyze_usage_trends.py`
- `skills/usage-tracking/scripts/capture_token_usage.sh`
- `skills/usage-tracking/scripts/usage-tracking.sh`

**Rationale:** Each skill follows the formal SKILLS.md specification and is properly invoked through the Orchestrator's task routing system. These are the ONLY scripts permitted to execute autonomous logic at runtime.

### DEPRECATED: Removal Timeline

The following files are deprecated and will be removed or converted to SKILLS within 30 days of discovery:

- `orchestration/scripts/analyze_usage_trends.py`
- `orchestration/scripts/usage_budget_check.py`

**Action Required:** Convert these to properly-scoped SKILLS via `SKILLS.md` with formal specifications, or delete them entirely.

### ENFORCEMENT CLAUSE

**Any script file not listed in the EXEMPT, REFERENCE, or COMPLIANT sets is considered a SPEC violation.**

Scripts not in these categories must be:
1. Removed immediately, OR
2. Converted to an Agent SKILL (via SKILLS.md) within 30 days of discovery

This constraint is non-negotiable. No legacy scripts, cron jobs, or autonomous processes are permitted outside the DELEGATE/HANDBACK orchestration model.

---

## Current Implementation vs. Original Spec

### What Changed in Phase 5.10

**Span Capture (Observability):**
- Orchestrator captures OpenTelemetry spans when receiving HANDBACKs from agents
- Extracts: task_id, agent_role, agent_model, status, tokens_in, tokens_out, decision
- Writes SPAN files to: `artifacts/2026-MM-DD/SPAN-{timestamp}-{agent_type}.yaml`
- SPAN includes: trace_id, span_id, duration_ms, cost_usd, status, decision, confidence
- **Implementation:** Added to Orchestrator's HANDBACK processing in Phase 6

**Artifact Indexing (Cost Analysis):**
- Model Engineer generates `artifacts/index.json` as part of feedback loop analysis
- Scans artifacts/2026-*/ for DELEGATE/HANDBACK/SPAN metadata
- Creates searchable index by: file_type, task_id, agent_type, status
- Calculates stats: total_tokens, total_cost, critical_issues, escalations
- **Implementation:** Natural extension of Model Engineer's existing feedback analysis

**Key Constraint Maintained:** No external Python scripts, no Makefile targets — all features are agent SKILLS.

---

## Core Architecture

### Agents & Roles (Multi-Agent Model)

All work enters via **Orchestrator** (default entry point). Orchestrator applies routing decision tree to delegate to specialists.

| Role | Model | Effort | Cost/Task | Purpose |
|------|-------|--------|-----------|---------|
| **Orchestrator** | claude-haiku-4.5 | low | $0.03 | Entry point; routing decisions; queue management; span capture; metrics collection |
| **Engineer** | claude-haiku-4.5 | high | $0.03 | Execute well-scoped tasks with pre-written plans |
| **Senior Engineer** | claude-sonnet-4.6 | high | $0.09 | Complex coding without plan; diagnosis; planning |
| **Lead Engineer** | claude-sonnet-4.6 | high | $0.09 | Code review; quality verification; unblock stuck tasks |
| **Quality Engineer** | claude-sonnet-4.6 | medium | $0.09 | Tier 1 quality checks; model suitability assessment |
| **Principal Engineer** | claude-opus-4-6 | high | $0.15 | Cross-service architecture; complex multi-step planning |
| **Security Engineer** | claude-opus-4.8 | max | $0.15 | Security analysis; vulnerability audits; threat modeling |
| **Model Engineer** | claude-sonnet-4.6 | high | $0.09 | Analyze feedback; recommend optimal model/effort; generate artifact index |

**Cost Target Distribution:**
- Orchestrator: 60%
- Engineer: 18%
- Senior Engineer: 7%
- Quality Engineer: 8%
- Lead Engineer: 2%
- Model Engineer: 3%
- Principal Engineer: 1%
- Security Engineer: 1%

---

## Glossary: Standardized Terminology

This section defines canonical terms used throughout the agentic-engineers framework to avoid ambiguity and ensure consistency.

| Term | Definition | Example |
|------|-----------|---------|
| **Orchestrator** | The primary entry point agent that receives all work requests, applies routing decision tree, and delegates to specialized agents. Polls `~/.agentic-engineers/{session-id}/{harness}/queue/incoming/` continuously. | "The Orchestrator received the task and routed it to the Security Engineer." |
| **DELEGATE Block** | A structured YAML file containing work request metadata (task_id, role, scope, plan, success_criteria). Placed in `~/.agentic-engineers/{session-id}/{harness}/queue/incoming/` only by humans or the Orchestrator itself. Automated external systems MUST NOT write directly to the queue. Core unit of work. | `~/.agentic-engineers/{session-id}/copilot/queue/incoming/task-2026-05-02.yaml` |
| **HANDBACK** | A structured result message returned by an agent after completing work. Placed in `~/.agentic-engineers/{session-id}/{harness}/queue/done/` by the agent. Contains deliverables, status, metrics, and confidence score. | `~/.agentic-engineers/{session-id}/copilot/queue/done/task-2026-05-02-HANDBACK.yaml` |
| **Queue System** | File-based work queue with session-id and harness-partitioned directories: `~/.agentic-engineers/{session-id}/{harness}/queue/{incoming,processing,done,failed}/`. All four harnesses (copilot, claude, opencode, pi) use the same `~/.agentic-engineers/` base. Each session has its own isolated queue partition identified by UUID. Both DELEGATE/HANDBACK protocol is identical across all harnesses. | All work coordination happens through the canonical harness-partitioned queue. No cross-session or cross-harness contamination. |
| **Agent SKILL** | A Python module implementing an agent's core capabilities. Invoked only through agent context (not external scripts). Located in `orchestration/agents/`. | `orchestration/agents/engineer_agent.py` |
| **Span Capture** | Observability mechanism that tracks work execution from initiation through completion, including decision points, delays, and handoffs. | `artifacts/spans/ directory records all task spans. |
| **Task Routing** | The process by which Orchestrator examines a DELEGATE block and applies the decision tree to select the appropriate agent role. | "Routing determined this was a security task, so Principal Engineer was selected." |
| **Model/Effort Combo** | The pairing of an LLM model (Haiku, Sonnet, Opus) with execution effort (low, medium, high, max). Determines cost and quality tradeoff. | Quality Engineer runs at Sonnet 4.6, medium effort. |

---

## Routing Decision Tree (Orchestrator)

When Orchestrator polls `~/.agentic-engineers/{session-id}/{harness}/queue/incoming/` and finds a task:

1. **Is task security-scoped?** (auth, crypto, data protection, vulnerability)  
   → **Security Engineer** (block all other routes)

2. **Is task cross-service architecture?** (affects >2 repos, service boundaries)  
   → **Principal Engineer**

3. **Is task complex coding WITHOUT pre-written plan?**  
   → **Senior Engineer** (writes plan first; returns HANDBACK with plan, not code)

4. **Is task code review or quality verification?**  
   → **Lead Engineer** OR **Quality Engineer**

5. **Is task well-scoped with pre-written plan, low-medium complexity?**  
   → **Engineer** (executes plan; uses Red-Green TDD when writing code)

6. **Otherwise** → Escalate to human (unclear scope)

---

## Queue-Based Delegation Mechanics

### Queue Structure (Session-ID Partitioned)

```
~/.agentic-engineers/
├── {session-id}/                        # UUID: 54744939-4acb-430c-b2c4-3b8322289d0b
│   ├── copilot/
│   │   └── queue/
│   │       ├── incoming/                # New tasks, ready for Orchestrator to process
│   │       ├── processing/              # Work assigned to agent, awaiting HANDBACK
│   │       ├── done/                    # Completed work, ready for human decision
│   │       └── failed/                 # Failed work (optional, for archival)
│   ├── claude/
│   │   └── queue/
│   │       ├── incoming/
│   │       ├── processing/
│   │       ├── done/
│   │       └── failed/
│   ├── opencode/
│   │   └── queue/
│   │       ├── incoming/
│   │       ├── processing/
│   │       ├── done/
│   │       └── failed/
│   └── pi/
│       └── queue/
│           ├── incoming/
│           ├── processing/
│           ├── done/
│           └── failed/
└── {other-session-id}/
    └── ...
```

**Session-ID Detection:**
- COPILOT_SESSION_ID environment variable (highest priority)
- CLAUDE_SESSION_ID environment variable
- Filesystem scan of `~/.agentic-engineers/` (lowest priority)

**Migration Status (Complete as of 2026-05-26):**
- Legacy paths (`~/.copilot/queue/`, `~/.claude/queue/`, `artifacts/queue/`) are DEPRECATED
- All queues have been migrated to `~/.agentic-engineers/{session-id}/{harness}/queue/`
- Using any legacy path raises `RuntimeError` from the queue-isolation skill

### Queue Flow

1. **Incoming** → New task arrives as `~/.agentic-engineers/{session-id}/{harness}/queue/incoming/{task_id}.yaml`
2. **Orchestrator polls** (every 30-60s):
   - Detects own session-id
   - Reads task from `~/.agentic-engineers/{session-id}/{harness}/queue/incoming/`
   - Applies routing decision tree
   - Creates DELEGATE in `artifacts/delegates/YYYY-MM-DD/DELEGATE-{task_id}-{role}.yaml`
   - Sends DELEGATE to agent
   - Deletes from `~/.agentic-engineers/{session-id}/{harness}/queue/incoming/` (or archives)
3. **Processing** → Agent returns HANDBACK to `~/.agentic-engineers/{session-id}/{harness}/queue/processing/{task_id}-HANDBACK-{role}.yaml`
4. **Orchestrator routes completion**:
   - If complete → Route to Quality Engineer
   - If blocked → Escalate to Lead/Senior Engineer
5. **Done** → Human/external system reads final decision from `~/.agentic-engineers/{session-id}/{harness}/queue/done/{task_id}-{decision}.yaml`

### Artifact Storage

| Artifact | Path | Created By | Used By |
|----------|------|-----------|---------|
| DELEGATE | `artifacts/delegates/YYYY-MM-DD/DELEGATE-{task_id}-{role}.yaml` | Orchestrator | Agent (receives), Orchestrator (ref) |
| HANDBACK | `~/.agentic-engineers/{session-id}/{harness}/queue/processing/{task_id}-HANDBACK-{role}.yaml` | Agent | Orchestrator (routes), QE (verifies) |
| SPAN | `artifacts/2026-MM-DD/SPAN-{timestamp}-{agent_type}.yaml` | Orchestrator | Model Engineer (analysis), index generation |
| Decision | `~/.agentic-engineers/{session-id}/{harness}/queue/done/{task_id}-{decision}.yaml` | Orchestrator | Human / external system |

---

## Queue Architecture & Paths (LOCKED SPEC)

**⚠️ SPECIFICATION LOCKED as of 2026-05-26**

This section defines the canonical queue path architecture for all harnesses. Changes to queue paths require approval via the `spec-management` skill.

### Canonical Queue Path

**All harnesses MUST use: `~/.agentic-engineers/`**

Queue directory structure:
```
~/.agentic-engineers/
├── {session-id}/                       # UUID: 54744939-4acb-430c-b2c4-3b8322289d0b
│   ├── copilot/
│   │   ├── queue/
│   │   │   ├── incoming/               # New DELEGATEs waiting for routing
│   │   │   ├── processing/             # Work assigned to agents, HANDBACKs awaiting review
│   │   │   ├── done/                   # Completed work
│   │   │   └── failed/                 # Failed work (optional, for archival)
│   │   └── session-state/
│   ├── claude/
│   │   ├── queue/
│   │   │   ├── incoming/
│   │   │   ├── processing/
│   │   │   ├── done/
│   │   │   └── failed/
│   │   └── session-state/
│   ├── opencode/
│   │   ├── queue/
│   │   │   ├── incoming/
│   │   │   ├── processing/
│   │   │   ├── done/
│   │   │   └── failed/
│   │   └── session-state/
│   └── pi/
│       ├── queue/
│       │   ├── incoming/
│       │   ├── processing/
│       │   ├── done/
│       │   └── failed/
│       └── session-state/
```

**Supported Harnesses (ALL REQUIRE SAME BASE):**
- **copilot**: Uses `~/.agentic-engineers/{session-id}/copilot/queue/`
- **claude**: Uses `~/.agentic-engineers/{session-id}/claude/queue/`
- **opencode**: Uses `~/.agentic-engineers/{session-id}/opencode/queue/`
- **pi**: Uses `~/.agentic-engineers/{session-id}/pi/queue/`

**CRITICAL:** There are NO EXCEPTIONS. All four harnesses use the same `~/.agentic-engineers/` base directory. No harness may use its own legacy path.

### Queue Subdirectories (Standard)

All queue directories MUST contain four standard subdirectories:

| Directory | Purpose | Contents |
|-----------|---------|----------|
| **incoming/** | New work waiting for routing | DELEGATE blocks from humans or Orchestrator |
| **processing/** | Work assigned to agents | HANDBACKs awaiting review by Quality Engineer |
| **done/** | Completed work | Final decisions ready for human action |
| **failed/** | Failed work (optional) | HANDBACKs with status=failed or blocked beyond recovery |

All subdirectories exist across all four harnesses (copilot, claude, opencode, pi).

### Unsupported Legacy Paths (DEPRECATED)

The following paths are **DEPRECATED and MUST NOT be used**:

| Legacy Path | Status | Migration |
|-------------|--------|-----------|
| `~/.copilot/queue/` | ❌ DEPRECATED | Migrated to `~/.agentic-engineers/{session-id}/copilot/queue/` |
| `~/.claude/queue/` | ❌ DEPRECATED | Migrated to `~/.agentic-engineers/{session-id}/claude/queue/` |
| `artifacts/queue/` | ❌ DEPRECATED | Migrated to `~/.agentic-engineers/{session-id}/*/queue/` |

**Migration Completed:** 2026-05-26

**Effect of Using Legacy Paths:** Using any legacy path will cause a `RuntimeError` from the queue isolation layer (queue-isolation skill) because those paths are no longer monitored by the Orchestrator or harness renderers.

### Enforcement Rules

**1. Queue-Isolation REQUIRED (No Fallback Logic)**
- QueueManager MUST have queue-isolation skill available at runtime
- If queue-isolation is unavailable, QueueManager raises `RuntimeError` immediately
- Error message MUST mention canonical path and list all unsupported legacy paths
- NO fallback to legacy paths; NO conditional logic to support old paths

**2. Orchestrator Hard Constraint**
- Orchestrator MUST initialize queue polling ONLY from `~/.agentic-engineers/{session-id}/{harness}/queue/`
- Orchestrator detects session-id from COPILOT_SESSION_ID or CLAUDE_SESSION_ID environment variables
- Orchestrator MUST NOT check for legacy paths (e.g., `~/.copilot/queue/`)
- Orchestrator MUST NOT implement conditional logic for different harnesses; all use same base

**3. Harness Renderers (Build-Time Compliance)**
- All harness configuration renderers (copilot, claude, opencode, pi) MUST output:
  ```
  QUEUE_PATH=~/.agentic-engineers/{session-id}/{harness}/queue/
  ```
- Build-time validation checks that all harness configs use correct path
- Pre-commit hooks validate no legacy paths are introduced in harness code

**4. Pre-Commit Hooks (Enforcement Gate)**
- Git hooks MUST block commits that introduce legacy paths (`~/.copilot/queue`, `~/.claude/queue`, `artifacts/queue`)
- Exception: Allow in `src/orchestration/queue_compat.py` (marked DEPRECATED) and `_archive/` directories
- Error message format:
  ```
  ERROR: Legacy queue paths found in {file}
  Use ~/.agentic-engineers/ instead (see SPEC.md: Queue Architecture & Paths)
  ```

**5. Testing Validation (CI Gate)**
- Test suite includes `tests/test_queue_path_centralization.py` with 8+ tests
- All tests validate orchestrator initializes ONLY from canonical path
- Tests validate all 4 harnesses initialize with correct path
- Tests verify no legacy paths exist in active source code

### Validation Procedures

**Pre-Merge Gate (Automated):**

1. **Grep Check for Legacy Paths:**
   ```bash
   grep -r "\.copilot/queue" src/                # Must return 0 matches (except _archive/)
   grep -r "\.claude/queue" src/                 # Must return 0 matches (except _archive/)
   grep -r "artifacts/queue" src/                # Must return 0 matches (except queue_compat.py, _archive/)
   ```

2. **Harness Config Validation:**
   - Verify all harness configs output `~/.agentic-engineers/{session-id}/{harness}/queue/`
   - Test each harness: copilot, claude, opencode, pi
   - All must use SAME base directory

3. **Test Suite Execution:**
   - Run: `pytest tests/test_queue_path_centralization.py -v`
   - All 8+ tests must pass
   - Tests cover:
     - Orchestrator requires isolation skill
     - Canonical path is only path checked
     - All 4 harnesses use same base
     - Legacy paths not referenced in active code
     - Queue subdirectory structure is standard
     - SPEC.md documents canonical path
     - Docs/QUEUE-PROTOCOL.md is locked
     - Pre-commit hook validates paths

4. **CI Gate (GitHub Actions):**
   - Same tests run on every push
   - Merge blocked if any test fails
   - All 2,900+ tests must pass (including 8+ new queue path tests)

---

## DELEGATE/HANDBACK Protocol

### DELEGATE Format (Orchestrator → Agent)

```yaml
---
handoff_type: DELEGATE
task_id: {unique_id}
role: Engineer | Senior Engineer | Lead Engineer | Quality Engineer | ...
model: claude-haiku-4.5 | claude-sonnet-4.6 | claude-opus-4-6 | ...
effort: low | medium | high | max
scope: "Clear one-sentence scope + explicit out-of-scope boundaries"
context: [relevant files, error messages, root cause analysis]
success_criteria: [measurable criteria; tests must pass, coverage maintained, etc.]
plan: [required for Engineer; step-by-step concrete steps; include Red-Green TDD phases for code changes]
---
```

### HANDBACK Format (Agent → Orchestrator)

```yaml
---
handoff_type: HANDBACK
task_id: {matching_delegate_task_id}
status: success | failure | partial | blocked | escalate
# Canonical status enum (runtime-validated):
#   success  — task completed successfully, all success_criteria met
#   failure  — task attempted but could not be completed
#   partial  — some success_criteria met, work remains
#   blocked  — cannot proceed; external dependency or decision required
#   escalate — requires higher-tier agent or human intervention
output: "Summary of what was delivered (any value; key must be present)"
metrics:
  quality: {0.0-1.0}
  tokens: {non-negative integer}
  cost: {non-negative USD}
  duration_seconds: {non-negative}
---
```

**Optional extension fields** (loosely validated, forward-compatible):
`deliverables`, `tests`, `escalations`, `model_assessment` (haiku_suitable |
sonnet_would_be_better | opus_required), `confidence` (0.0-1.0), `retry_count`,
`model_used`, `effort_actual`, `children_created`, `children_results`, `flags`,
`error`.

See [docs/specs/protocol-core-v1.0.yaml](specs/protocol-core-v1.0.yaml) for the
canonical machine-readable schema.

---

## Agent Autonomy Model

Agents operate in **reduced autonomy mode**: they continue work autonomously when additional tasks exist, but pause and wait for user input when the current scope is complete.

### Autonomy Principles

**Core Rule:** Agents should pause when assigned task scope is complete, unless additional work has been explicitly queued or is documented in their working notes.

### Autonomy Decision Workflow

When an agent completes work:

1. **Check Current Scope**
   - Did I complete the assigned task/DELEGATE?
   - Are all success criteria met?
   - Are all todos from the current scope marked done in TODO.md?

2. **Check for Remaining Work**
   - Is there a `TODO.md` with additional pending todos?
   - Is there a queued follow-up task or DELEGATE?
   - Does the repository have documented outstanding work?

3. **Decide: Continue or Pause**
   - **CONTINUE autonomously IF:** More todos exist in TODO.md (marked pending)
   - **PAUSE and wait for input IF:** Current scope is complete AND no additional work is documented in TODO.md
   - **Always pause** when uncertain about scope boundaries

### TODO Tracking (MANDATORY)

**Use TODO.md in repository ONLY for todo tracking. Do NOT use SQL databases or session artifacts.**

- Agents must read `TODO.md` from repository root to find remaining todos
- Todos are marked in markdown checklist format: `- [ ]` (pending) or `- [x]` (done)
- Agents update TODO.md directly by editing the file
- TODO.md is the canonical source of truth for all work items
- **PROHIBITED:** Do not use SQL `todos` table, spreadsheets, or external tracking systems
- Do NOT use session workspace plan.md as substitute for TODO.md

### Agent Responsibilities

**When pausing (end of current scope):**
- Clearly summarize what was completed
- List any remaining work (if known)
- Explicitly state: "Pausing here. Ready for next task or input."
- Do NOT assume there's more work; let the user decide

**When continuing (additional work exists):**
- Acknowledge remaining todos in TODO.md
- Continue executing on the next item
- Update TODO.md as you progress
- Report progress at key milestones

### Examples

**Example 1: Task Complete, Pause**
```
✓ Feature implemented and tested
✓ All success criteria met
✓ No todos remaining

→ PAUSE: "Task complete. Awaiting further input."
```

**Example 2: Multiple Todos, Continue**
```
✓ First todo (database schema) complete
→ TODO: Second todo (API routes) pending
→ TODO: Third todo (tests) pending

→ CONTINUE: "Moving to next todo: API routes."
```

**Example 3: Unclear Scope, Pause**
```
? Current task done, but not sure if more work planned
? No explicit todos documented

→ PAUSE: "Completed assigned work. Are there more tasks?"
```

### Implications for Orchestrator

The Orchestrator-first execution model (MANDATORY) is **not changed** by autonomy rules. Agents still:
- Only receive work via DELEGATE blocks from Orchestrator
- Only return HANDBACKs to Orchestrator
- Never invoke agents directly
- Never bypass the queue

Reduced autonomy is about **when agents stop working on the current task**, not about **how work enters the system**. Both constraints work together:
- **Orchestrator-first:** How work is routed (mandatory, enforced)
- **Reduced autonomy:** When agents pause within their current task scope (guidance, not enforcement)

---

## Task Orchestration: Parallelization & Decision Protocol

**All agents** must default to the autonomous task execution pattern defined in
`src/skills/_meta/task-orchestration/SKILL.md`:

> **Maximize throughput by parallelizing all independent tasks.**  
> **Pause only for genuine decisions — never for task sequencing.**

### Using the task-orchestration Skill

```python
from src.skills._meta.task_orchestration.scripts.task_orchestrator import (
    Task, TaskType, classify_task, can_parallelize,
    generate_decision_shorthand, parse_decision_response,
)
```

### Decision Points vs. Task Sequencing

| Type | Definition | Agent action |
|------|-----------|--------------|
| **Task sequencing** | Ordering or prioritisation of independent items | Always autonomous — never ask the user |
| **Genuine decision** | Irreversible architectural or technology choice | Always pause — present shorthand and wait |

### Quick Reference

```
✅ Parallelize:   classify_task(desc) == AUTONOMOUS  AND  can_parallelize(tasks) == True
⏸  Pause & ask:  classify_task(desc) == DECISION_NEEDED
🔗 Run in order:  classify_task(desc) == SEQUENTIAL_ONLY  OR  can_parallelize(tasks) == False
```

### Decision Shorthand Protocol

When a genuine decision must be presented:

```
1a. Option one
1b. Option two
1c. Option three
```

User responds: `1b` (or `1a, 2c, 3b` for multiple concurrent decisions).

Parse with: `parse_decision_response("1b")` → `{1: "b"}`

**See:** `src/skills/_meta/task-orchestration/SKILL.md` for the full pattern,
examples, and Python API reference.

---

## SKILLS: Role-Specific Execution Details

### Engineer

**Model:** claude-haiku-4.5 (high effort)  
**Cost Target:** 18%

Execute well-scoped tasks with pre-written plans.

**Workflow:**
1. Read DELEGATE carefully
2. Follow plan steps in order
3. Recommended: Use Red-Green TDD (test first, implement, refactor)
4. Run `make verify` before HANDBACK
5. Document deliverables and test results clearly

**Escalation Trigger:** Report `status: blocked` if architectural conflicts or missing context.

### Senior Engineer

**Model:** claude-sonnet-4.6 (high effort)  
**Cost Target:** 7%

Design solutions for complex tasks without pre-written plans. Diagnose bugs when root cause unclear.

**Planning Task:**
1. Explore 2-3 approaches
2. Write detailed plan with rationale
3. Return HANDBACK with plan (not code)

**Diagnosis Task:**
1. Reproduce issue
2. Trace code flow
3. Point to specific file:line
4. Explain root cause with evidence
5. Suggest fixes

**Escalation Trigger:** Cross-service changes, architectural impacts, security concerns → report `status: blocked`.

### Lead Engineer

**Model:** claude-sonnet-4.6 (high effort)  
**Cost Target:** 2%

Review code and unblock stuck tasks.

**Code Review Checklist:**
- Tests pass, lint clean, coverage maintained (≥85%)
- No secrets, panics, or scope creep
- Senior Engineer code: plan completeness verified
- Principal Engineer code: architecture patterns followed, IAM correct

**Verdict:** PASS or FAIL (with specific feedback if FAIL).

**Unblock Task:** Analyze blocker, provide path forward, return to Orchestrator.

### Quality Engineer

**Model:** claude-sonnet-4.6 (medium effort)  
**Cost Target:** 8%

Run Tier 1 quality checks. Assess model suitability.

**Quality Checks:** Tests pass, lint clean, no secrets, scope match.

**Model Assessment:** Was this model appropriate? 
- `haiku_suitable` / `sonnet_would_be_better` / `opus_required`
- Confidence score (0.0–1.0)

**Feedback:** Add to HANDBACK for Model Engineer analysis.

### Principal Engineer

**Model:** claude-opus-4-6 (high effort)  
**Cost Target:** 1%

Design when changes affect >2 repos or service boundaries.

**Task:**
1. Map dependencies
2. Identify contracts
3. Design approach (breaking vs. compatibility vs. versioning)
4. Propose rollout plan

### Security Engineer

**Model:** claude-opus-4.8 (max effort)  
**Cost Target:** 1%

Scan for vulnerabilities, check dependencies, verify access controls.

**Output:** Findings by severity (CRITICAL, HIGH, MEDIUM, LOW).

### Model Engineer

**Model:** claude-sonnet-4.6 (high effort)  
**Cost Target:** 3%

Analyze completed task feedback (~10-100 samples). Identify patterns.

**Workflow:**
1. Which models succeeded? Which failed?
2. Token efficiency patterns?
3. Generate ranking for next similar task:
   - Rank 1 = highest confidence
   - Rank 2 = exploratory
   - Rank 3 = fallback
4. Generate artifact index (NEW in Phase 5.10):
   - Scan artifacts/2026-*/ for DELEGATE/HANDBACK/SPAN metadata
   - Extract: task_id, agent_type, status, tokens, cost, severity, decision
   - Create searchable index: artifacts/index.json
   - Include stats: total_tokens, total_cost, critical_issues, escalations

**Output:** Model Engineer recommends ranking; Orchestrator applies Rank 1 for next similar task.

### Orchestrator

**Model:** claude-haiku-4.5 (low effort)  
**Cost Target:** 60%

Runs continuously in harness. Polls queues every 30-60 seconds.

**Core Workflow:**
1. Check `incoming/` → route using AGENTS decision tree → create DELEGATE → send to agent
2. Check `processing/` → if complete, route to QE; if blocked, escalate to Lead/Senior Engineer
3. Check `done/` → if PROCEED, merge; if REWORK, return to incoming with feedback; if ESCALATE, promote role
4. Apply Model Engineer recommendations (use Rank 1 model for similar tasks)

**Span Capture (NEW Phase 5.10):** When receiving HANDBACK from any agent:
1. Extract: task_id, agent_role, agent_model, status, tokens_in, tokens_out, decision
2. Calculate: duration_ms = end_time - start_time
3. Calculate: cost_usd = tokens × model pricing
4. Create SPAN with OpenTelemetry attributes:
   - trace_id, span_id, parent_span_id
   - span_name (e.g., "agent.engineer.execution")
   - start_time, end_time, duration_ms
   - status (success/error/deadline_exceeded)
   - attributes: agent_type, agent_model, service_name, input_tokens, output_tokens, total_tokens, cost_usd, status, decision, severity, confidence
5. Write SPAN to: `artifacts/2026-MM-DD/SPAN-{timestamp}-{agent_type}.yaml`
6. Queue async DELEGATE to Model Engineer to regenerate `artifacts/index.json` (non-blocking; fire-and-forget, but MUST be queued — not skipped)

**Key:** Span capture is internal observability; doesn't change agent behavior. HANDBACKs include token counts (agents already track this).

---

## Optimization Feedback Loop

### Continuous Improvement Cycle

```
1. Engineer executes → returns HANDBACK with tokens, status, confidence
2. Quality Engineer verifies → adds model_assessment feedback
3. Orchestrator records:
   - Task metrics (task_id, duration, cost, status)
   - Agent metrics (model, effort, tokens, decision)
   - Span data (for observability and cost analysis)
4. Model Engineer analyzes:
   - Quality score vs. expected (for assigned model)
   - Token efficiency (cost_per_quality_point)
   - QE model suitability feedback
   - Historical samples for same task signature
   - Generates artifact index for cost trend analysis
5. Model Engineer generates recommendations:
   - Rank 1 (highest confidence): use for next similar task
   - Rank 2 (exploratory): consider A/B test
   - Rank 3 (alternative): fallback if rank 1 unavailable
6. Orchestrator applies Rank 1 for next matching task
```

**Result:** Autonomous cost optimization — each task improves routing for similar future tasks.

---

## Constraints & Mandatory Rules

### Queue-Based Routing
- **ALL work flows through queue:** `~/.agentic-engineers/{session-id}/{harness}/queue/incoming/ → processing/ → done/`
- **Orchestrator polls** every 30-60 seconds (runs in harness, no external cron/tools)
- **DELEGATE stored** in `artifacts/delegates/YYYY-MM-DD/` for reference
- **HANDBACK stored** in `~/.agentic-engineers/{session-id}/{harness}/queue/processing/` (moved to done/ after QE review)

### Planning & Escalation
- **Engineer MUST NOT receive task without pre-written `plan`** in DELEGATE. No exceptions — all tasks require a plan. If scope is unclear, return status: blocked and Orchestrator escalates to Senior Engineer to write the plan.
- **If Engineer cannot execute plan** → report `status: blocked`; Orchestrator escalates to Senior Engineer
- **Blocked tasks and rejections escalate** automatically per AGENTS decision tree

### Orchestrator Constraints
- **Orchestrator MUST NOT perform work** (only route, coordinate, apply recommendations)
- **Orchestrator runs in harness** via polling loop (no external cron/tools)
- **ALL execution work delegated** to appropriate role via DELEGATE/HANDBACK

### Role-Specific Rules
- **Security Engineer invoked ONLY** for security-scoped tasks
- **Quality Engineer provides `model_assessment` feedback** in HANDBACK (for Model Engineer)
- **Lead Engineer/Senior Engineer unblock** or redirect Engineer when task blocked
- **Each role has specific skills** (see SKILLS section above)

### Handoff Protocol (Mandatory)
- All agent-to-agent work transfer uses structured **DELEGATE/HANDBACK markup blocks** (see format above)
- Markup enables:
  - Compact context transfer (no re-summarisation)
  - Machine-readable task tracking
  - Metrics collection per task
  - Span capture for observability

### Unattended Mode (YOLO Operation)
- Voice-notify every 5–10 min with progress checkpoint (tokens, task count, blockers)
- No interactive prompts — escalate decisions autonomously, don't wait for human input
- Agents make decisions within their scope without human approval
- Only pause if: (1) merge conflict, (2) CI failure post-push, (3) out-of-scope issue discovered
- Proceed with full autonomy; human reviews post-completion

### No External Tools
- **NO external Python scripts** — all features implemented as agent SKILLS
- **NO Makefile targets** for Orchestrator operations
- **NO shell scripts** for queue management or span capture
- **100% agent-based** — work flows through AGENTS via DELEGATE/HANDBACK

---

## Phase 5.10 Additions: Span Capture & Indexing

### Span Capture Architecture

Span capture is **built into agent SKILLS**, not external utilities:

1. **Orchestrator SKILL:** Captures spans when receiving HANDBACKs from agents
2. **Model Engineer SKILL:** Generates `artifacts/index.json` as part of feedback analysis
3. **Agents:** Continue normal workflow (receive DELEGATE → execute → return HANDBACK with token counts)

### Span Attributes (OpenTelemetry Schema)

```yaml
handoff_type: SPAN
task_id: {matching_delegate_task_id}
timestamp: {ISO8601}
span_name: "agent.{agent_type}.execution"
trace_id: {uuid, shared across parallel agents}
span_id: {uuid, unique per agent}
parent_span_id: {uuid or null}
attributes:
  agent_type: "Engineer" | "Senior Engineer" | "Quality Engineer" | etc.
  agent_model: "claude-haiku-4.5" | "claude-sonnet-4.6" | etc.
  service_name: "agentic-engineers"
  agent_role: {matching_role_from_DELEGATE}
  task_id: {task_id}
  status: "success" | "error" | "deadline_exceeded"
  decision: "PASS" | "FAIL" | "ESCALATE" | "BLOCKED"
  severity: "critical" | "high" | "medium" | "low"
  confidence: [0.0-1.0]
  input_tokens: {count}
  output_tokens: {count}
  total_tokens: {count}
  cost_usd: {calculated from tokens × model pricing}
  duration_ms: {end_time - start_time}
  escalations: {count}
```

### Artifact Index Format

Generated by Model Engineer, stored as `artifacts/index.json`:

```json
{
  "generated_at": "2026-05-02T14:30:00Z",
  "summary": {
    "total_tasks": 245,
    "total_tokens": 1_234_567,
    "total_cost_usd": 45.67,
    "critical_issues": 3,
    "escalations": 12,
    "average_tokens_per_task": 5037,
    "average_cost_per_task": 0.19
  },
  "by_agent_type": {
    "Engineer": {
      "count": 150,
      "total_tokens": 600_000,
      "total_cost": 18.00,
      "success_rate": 0.98
    },
    "Senior Engineer": {
      "count": 30,
      "total_tokens": 250_000,
      "total_cost": 7.50,
      "success_rate": 0.93
    }
  },
  "by_status": {
    "complete": 230,
    "blocked": 10,
    "partial": 5
  },
  "by_decision": {
    "PASS": 220,
    "FAIL": 5,
    "ESCALATE": 20
  },
  "critical_issues": [
    {
      "task_id": "2026-05-01-sec-audit-1",
      "agent_type": "Security Engineer",
      "severity": "critical",
      "description": "SQL injection vulnerability"
    }
  ],
  "span_metadata": [
    {
      "task_id": "2026-05-02-fix-token-1",
      "agent_type": "Engineer",
      "span_file": "artifacts/2026-05-02/SPAN-2026-05-02T14:15:00Z-Engineer.yaml",
      "tokens": 1200,
      "cost_usd": 0.04,
      "duration_ms": 45000,
      "status": "success"
    }
  ]
}
```

---

## Effort Levels & Token Budget

| Level | Cost | Use Case | Expected Output |
|-------|------|----------|-----------------|
| **Low** | Minimal | Code cleanup, lint fixes, simple PRs | Minimal explanation, direct changes, no exploration |
| **Medium** | Moderate | Bugs with clear root cause, standard features, security fixes | Balanced: explain what changed, why, test verification |
| **High** | Standard | Complex bugs, architectural changes, security hardening | Deep reasoning, multiple approaches considered, thorough testing |
| **Max** | Unconstrained | CI failures with unclear root cause, major refactors, advanced analysis | Full exploration and validation, no cost/time constraints |

---

## Legacy Tiers (Mapped to Current Roles)

- **Lightweight** → Haiku Orchestrator (low) or Haiku Engineer (high)
- **Standard** → Sonnet (high effort) roles (Senior Engineer, Lead Engineer, Quality Engineer, Model Engineer)
- **Advanced** → Opus roles (Principal Engineer: 4.6, Security Engineer: 4.8) with high/max effort

---

## Agent Implementations

All agents are defined with detailed workflows:

- ✅ **Orchestrator Agent** (`orchestration/agents/general-orchestrator-agent.md`)
- ✅ **Engineer Agent** (`orchestration/agents/engineer-agent.md`)
- ✅ **Senior Engineer Agent** (`orchestration/agents/senior-engineer-agent.md`)
- ✅ **Lead Engineer Agent** (`orchestration/agents/lead-engineer-agent.md`)
- ✅ **Quality Engineer Agent** (`orchestration/agents/quality-engineer-agent.md`)
- ✅ **Principal Engineer Agent** (`orchestration/agents/principal-engineer-agent.md`)
- ✅ **Security Engineer Agent** (`orchestration/agents/security-agent.md`)
- ✅ **Model Engineer Agent** (`orchestration/agents/model-engineer-agent.md`)

---

## Observability & Monitoring (Phase 5.10)

### Span Capture
- Orchestrator captures OpenTelemetry spans for every agent execution
- Spans stored in `artifacts/2026-MM-DD/SPAN-{timestamp}-{agent_type}.yaml`
- Includes: duration, cost, tokens, status, decision, severity, confidence

### Artifact Indexing
- Model Engineer generates searchable `artifacts/index.json`
- Index includes: task metadata, cost analysis, critical issues, escalations
- Used by: Orchestrator (routing decisions), Model Engineer (trend analysis), humans (cost reporting)

### No External Monitoring Tools
- All observability flows through agent SKILLS
- No external Python scripts, no Makefile targets
- Span data and indexing are natural extensions of agent workflows

---

## Integration Points

### With AGENTS.md
Orchestrator uses AGENTS.md to:
- Apply routing decision tree (which role for which task)
- Select model/effort combo
- Handle escalations and blocked tasks
- Apply Model Engineer recommendations

### With SKILLS.md
Each agent role has SKILLS section:
- How to execute their role
- Quality standards
- Escalation triggers
- Specific workflows (Red-Green TDD for Engineer, etc.)
- Span capture for Orchestrator
- Artifact indexing for Model Engineer

### With QUEUE-PROTOCOL.md
Orchestrator implements queue mechanics:
- Polls `incoming/`, `processing/`, `done/`
- Creates DELEGATE blocks per format
- Routes completed work to Quality Engineer
- Manages transitions and escalations

### With HANDOFF.md
All agent-to-agent communication uses DELEGATE/HANDBACK markup:
- Structured format enables metrics collection
- Machine-readable for queue processing
- Compact context transfer

---

## SDLC Enforcement Hooks

Git hooks enforce SPEC.md compliance and quality gates at commit and push time. Hooks are standalone bash scripts in `.githooks/` — they do **not** delegate to agents via the queue (hooks must be synchronous and fast).

### Hook Summary

| Hook | Trigger | Enforces | Severity |
|------|---------|----------|----------|
| **pre-commit** | Before `git commit` | SPEC compliance, secrets, YAML validity, DELEGATE/HANDBACK format | ❌ BLOCK |
| **commit-msg** | After commit message | Message format (≥10 chars), SKIP_HOOKS documentation | ❌ BLOCK |
| **pre-push** | Before `git push` | Agent YAML frontmatter, test suite, protected branch warning | ❌ BLOCK / ⚠️ WARN |

### Installation

Hooks are installed automatically by `make install`:

```bash
make install
# or manually:
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/commit-msg .githooks/pre-push
```

### Emergency Bypass

```bash
BYPASS_HOOK_VALIDATION=true git commit -m "emergency: reason"  # bypass DELEGATE/HANDBACK validation only
SKIP_HOOKS=1 git commit -m "emergency: reason"                 # bypass all pre-commit checks
SKIP_HOOKS=1 git push                                          # bypass pre-push checks
```

See `docs/BYPASS-PROCEDURES.md` for full bypass procedures and authorization requirements.

### Full Reference

See `docs/SDLC-HOOKS.md` for comprehensive hook documentation including:
- Full check details and error messages
- Troubleshooting guide
- Cross-harness support matrix
- Bypass procedures

---

## Summary Table

| Component | Role | Implementation | Status |
|-----------|------|-----------------|--------|
| Queue System | Orchestrator | File-based: incoming → processing → done | ✅ Active |
| Routing Logic | Orchestrator | Decision tree per AGENTS.md | ✅ Active |
| DELEGATE Creation | Orchestrator | Per HANDOFF.md format | ✅ Active |
| Agent Execution | All Agents | Per SKILLS.md workflows | ✅ Active |
| HANDBACK Processing | Orchestrator | Metric collection + QE routing | ✅ Active |
| Span Capture | Orchestrator SKILL | OpenTelemetry format to SPAN files | ✅ Phase 5.10 |
| Artifact Indexing | Model Engineer SKILL | Generate artifacts/index.json | ✅ Phase 5.10 |
| Cost Optimization | Model Engineer | Feedback analysis + ranking | ✅ Active |
| Escalation Handling | Orchestrator + Lead Engineer | Per decision tree + unblock | ✅ Active |
| **SDLC Hooks** | **All contributors** | **`.githooks/` bash scripts** | **✅ Active** |

---

## Next Steps (Phase 6)

- Implement Span Capture in Orchestrator code (Phase 6 development)
- Enable Artifact Indexing in Model Engineer skill (Phase 6 development)
- Monitor span data for cost trends and routing improvements
- Validate Phase 5.10 observability with real task data

---

## References

- **AGENTS.md** — Agent roles, models, effort levels, routing decision tree
- **SKILLS.md** — Role-specific execution workflows, span capture, indexing
- **QUEUE-PROTOCOL.md** — Queue mechanics, DELEGATE/HANDBACK storage, file structure
- **HANDOFF.md** — Structured markup format for agent communication
- **SPAN-CAPTURE-INTEGRATION.md** — Span capture architecture and data flow
- **`docs/ONBOARDING.md`** — Developer onboarding and workflow guide
- **FEEDBACK-LOOPS.md** — Model Engineer feedback and cost optimization
- **TOKEN-USAGE-TRACKING.md** — Token accounting and cost calculation

---

## Repository Structure

All source code lives in `src/`:

- `src/orchestration/` — Agent orchestration framework (Python modules)
  - `src/orchestration/agents/` — Routing, delegation, spec validation
  - `src/orchestration/tools/` — Orchestration utilities
- `src/skills/` — Skill implementations (each subdirectory = one SKILL)
- `src/config/` — Configuration management (`models.yaml`, assignments)
- `src/agents/` — Agent definition files (*.md role specs)
- `src/tools/` — Shared tooling utilities

All documentation lives in `docs/`:

- `docs/guides/` — Implementation guides
- `docs/reference/` — Design patterns and standards
- `docs/operations/` — Operational reference
- `docs/specs/` — Protocol specification documents
- `docs/architecture/` — Architecture decisions (ADRs)
- `docs/REPOSITORY-STRUCTURE.md` — Full directory reference

Root-level duplicate directories (`orchestration/`, `skills/`, `config/`) were removed during Phase 3 restructuring. Only `src/` contains source code.

Import statements use: `from src.orchestration.agents import ...`

For the complete directory reference see [docs/REPOSITORY-STRUCTURE.md](REPOSITORY-STRUCTURE.md).

---

## Phase 3: Token Visibility & Budget Checking (Complete)

**Status:** ✅ Complete as of 2026-05-17

### Token Visibility Requirements

1. **Real-time token tracking** across all agents and subagents in a session
   - Orchestrator sees only ~27% of actual token usage
   - Subagents account for ~73% of usage
   - Tracking must aggregate across all nested sessions

2. **CLI commands** for token visibility:
   - `opencode-tokens --session <id>` — Usage by agent
   - `opencode-budget --session <id> --limit N` — Budget status
   - `opencode-subagents --session <id>` — List all subagents

3. **Database queries** via SQLite at `~/.local/share/opencode/opencode.db`:
   - Session hierarchy (parent_id relationships)
   - Token counts per session
   - Depth calculation via recursive CTE

### Budget Checking Requirements

1. **Budget limits** configurable per session or per task
2. **Alert thresholds** (e.g., alert at 80% consumed)
3. **Graceful degradation** — agents report `status: blocked` when approaching limit
4. **DELEGATE budget field** — optional `budget_tokens` field in DELEGATE

### Cost Attribution Requirements

1. **Per-role cost tracking** — costs attributed to specific agent roles
2. **Per-task cost tracking** — costs linked to task_id for audit trail
3. **Shadow mode** — dry-run delegation that estimates costs without executing
4. **Token cost alerts** — configurable alerts on cost thresholds

### Production Deployment Requirements

1. **AutomationController** — continuous polling loop with signal handling
2. **4 deployment scenarios** — standalone, systemd, Docker, Kubernetes
3. **Health monitoring** — queue state visibility, stuck task detection
4. **Metrics export** — Prometheus-compatible metrics for Grafana dashboards

### Implementation

- `opencode-tokens` CLI: `src/tools/opencode_tokens.py`
- `opencode-budget` CLI: `src/tools/opencode_budget.py`
- `opencode-subagents` CLI: `src/tools/opencode_subagents.py`
- AutomationController: `src/orchestration/agents/automation_controller.py`
- Production entrypoint: `bin/run-automation-controller.sh`

### Documentation

- [docs/QUICK-START-TOKEN-VISIBILITY.md](QUICK-START-TOKEN-VISIBILITY.md)
- [docs/QUICK-START-BUDGET-CHECKING.md](QUICK-START-BUDGET-CHECKING.md)
- [docs/QUICK-START-PRODUCTION-DEPLOYMENT.md](QUICK-START-PRODUCTION-DEPLOYMENT.md)
- [docs/TOKEN-COST-MONITORING.md](TOKEN-COST-MONITORING.md)
- [docs/USAGE-BUDGET-MANAGER.md](USAGE-BUDGET-MANAGER.md)

---

## Model Selection Architecture

This section documents how agent roles select among approved opus model variants. Principal Engineer and Security Engineer are Tier 3 (Opus) roles where task complexity varies enough to warrant variant selection within the opus family. The Orchestrator selects the appropriate variant at DELEGATE-creation time.

### Opus Variant Comparison

| Variant | Strengths | Weaknesses | Best For |
|---------|-----------|------------|----------|
| `claude-opus-4.6` | Extended thinking; lowest cost in opus tier | No cross-repo execution edge; not for security-critical tasks | Pure architecture planning; design-only scopes |
| `claude-opus-4.7` | Balanced capability + cost; strong cross-repo reasoning | Not optimal for highest-stakes security tasks | Design decisions that drive implementation across ≥2 repos |
| `claude-opus-4.8` | Highest capability; best for threat modeling and compliance | Highest cost | Security analysis; auth flows; cryptographic selection; compliance policy |

### Principal Engineer: Variant Selection

The Orchestrator applies this decision tree when creating a DELEGATE for Principal Engineer:

| Task Profile | Model | Trigger |
|-------------|-------|---------|
| Pure architecture planning | `claude-opus-4.6` | Design-only scope; no cross-repo execution required; extended thinking sufficient |
| Design with cross-repo execution | `claude-opus-4.7` | Architecture decision drives implementation across ≥2 repos |
| Security-critical design | `claude-opus-4.8` | Involves auth flows, cryptographic selection, or compliance policy |

**Orchestrator decision tree:**
1. Pure planning (design-only, no execution)? → `claude-opus-4.6`
2. Design directly drives cross-repo implementation? → `claude-opus-4.7`
3. Security-critical design (auth/crypto/compliance)? → `claude-opus-4.8`
4. Default (unclear scope) → `claude-opus-4.6` (cheapest capable option)

### Security Engineer: Multi-Model Strategy

Security Engineer supports two approved models:

#### Default: `claude-opus-4.8` (Primary)

Security analysis is the highest-stakes task in the system. Opus 4.8 is pinned as the default because downgrading for cost savings risks missed vulnerabilities, incomplete threat models, or incorrect compliance assessments.

- Use for: threat modelling, vulnerability assessment, compliance review, secrets handling policy
- Rationale: Highest capability; best for security-critical analysis
- Fallback only: `claude-opus-4.7` (emergency-only if 4.8 unavailable due to API outage)
  - Fallback must be documented in HANDBACK `model_assessment`
  - Never downgrade by choice; never use 4.6 for Security Engineer

#### Alternative: `claude-fable-5` with `output_config.effort: medium` (Defensive-Only)

Fable-5 is approved **exclusively for defensive security analysis** — prevention, detection, and remediation of existing vulnerabilities. Fable-5 is the highest-capability tier (above Opus) and uses adaptive thinking for nuanced threat analysis. Note: Fable-5 is priced at $10/$50 per MTok — 2× Opus 4.8's $5/$25 — so this is a **capability upgrade, not a cost saving**; `effort: medium` bounds token spend per task but does not make it cheaper per token.

**Approved use cases (defensive only):**
- Vulnerability assessment (OWASP Top 10, injection, broken auth, secrets exposure)
- Threat modelling for existing systems
- Compliance review (OAuth 2.0, zero-trust, secrets handling, GDPR)
- Security audit findings triage and remediation planning
- CLI permission policy review and hardening

**Prohibited use cases (never use fable5):**
- Exploit development or proof-of-concept attacks
- Offensive security research or attack automation
- Adversarial model behavior (jailbreak techniques, prompt injection)
- Red team scenarios designed to demonstrate attack capability
- Any task requiring offensive capability, even if framed as "defensive research"

**Constraint enforcement:**
- Orchestrator MUST NOT route fable5 for offensive/research tasks (see gate logic below)
- Security Engineer receiving fable5 MUST validate scope is defensive before execution
- HANDBACK must include `model_constraint: defensive-only` field to confirm compliance
- Violation (offensive work on fable5): escalate immediately to user with rationale

**Gate logic in Orchestrator routing:**
```
IF (task_scope contains "exploit" OR "attack automation" OR "offensive" OR "red team" OR "proof-of-concept attack")
  → Route to claude-opus-4.8 (reject fable5, document in audit log)
ELIF (task_scope == "defensive vulnerability analysis" AND effort <= medium)
  → May route to fable5 with explicit defensive constraint note
ELSE
  → Default to claude-opus-4.8
```

| Model | Task Complexity | Cost (Input/Output) | Best For | Constraint |
|-------|-----------------|--------|----------|------------|
| `claude-opus-4.8` | Any | $5/$25 per MTok | All security tasks (default) | None |
| `claude-fable-5` | High-nuance defensive | $10/$50 per MTok | Deep defensive vulnerability analysis at medium effort | **Defensive-only** (no offensive use) |

### Quality Engineer: model_assessment for Tier 3

After each Tier 3 (Principal/Security) task, Quality Engineer provides `model_assessment` feedback in HANDBACK. This feeds the Model Engineer optimization loop for future routing decisions.

```yaml
model_assessment:
  role: principal-engineer
  model_used: claude-opus-4.6
  model_appropriate: true
  alternative_considered: claude-opus-4.7
  rationale: "Pure planning task; 4.6 extended thinking was sufficient; 4.7 not needed"
  recommendation: "Continue routing pure-planning Principal tasks to 4.6"
```

### Example DELEGATE Blocks with model_guidance

**Principal Engineer — pure planning (4.6):**
```yaml
handoff_type: DELEGATE
role: Principal Engineer
model: claude-opus-4.6
model_guidance: "Pure planning task — design-only, no cross-repo execution required"
task: "Design the event-sourcing schema for the new audit trail feature"
```

**Principal Engineer — cross-repo execution (4.7):**
```yaml
handoff_type: DELEGATE
role: Principal Engineer
model: claude-opus-4.7
model_guidance: "Architecture decision drives implementation across auth-service and api-gateway"
task: "Design and specify OAuth2 refresh-token rotation across 3 services"
```

**Security Engineer — default (opus 4.8):**
```yaml
handoff_type: DELEGATE
role: Security Engineer
model: claude-opus-4.8
model_guidance: "Default pinned model for all security analysis"
task: "Threat model for the new payment processing flow"
```

**Security Engineer — defensive vulnerability analysis (fable5):**
```yaml
handoff_type: DELEGATE
role: Security Engineer
model: claude-fable-5
output_config:
  effort: medium
model_guidance: "Fable-5 approved for defensive-only analysis: vulnerability assessment and remediation planning (no offensive capability)"
model_constraint: "defensive-only"
task: "Assess OWASP Top 10 vulnerabilities in user auth flow and recommend patches"
```

### Rollout Phases

| Phase | Scope | Status |
|-------|-------|--------|
| Phase 1 | Principal Engineer variant selection (4.6/4.7/4.8) | Active |
| Phase 2 | Security Engineer non-downgrade rule enforcement (opus 4.8 pinned default) | Active |
| Phase 3 | Quality Engineer model_assessment feedback loop | Active |
| Phase 4 | Model Engineer automated routing recommendations | Active |
| Phase 5 | Security Engineer fable-5 option for defensive-only analysis (effort: medium) | Active |

---

## Model Naming & Harness Compatibility (LOCKED SPEC)

This section documents the approved AI model names and their official sources. Model naming is **CRITICAL** for harness compatibility and MUST NOT be changed without updating all validators, tests, and this specification.

### Official Model Names (AUTHORITATIVE)

**Source:** [Anthropic Claude API Documentation](https://docs.anthropic.com/claude/docs/models-overview)

All agentic-engineers agents use Anthropic Claude models in the following **HYPHEN format only**:

| Model | Model ID | Claude API Alias | Context Window | Max Output | Use Case |
|-------|----------|------------------|-----------------|------------|----------|
| **Claude Haiku 4.5** | `claude-haiku-4.5` | `claude-haiku-4.5` | 200K | 64K | Fast, low-cost; Orchestrator, Engineer |
| **Claude Sonnet 4.6** | `claude-sonnet-4.6` | `claude-sonnet-4.6` | 1M | 64K | Balanced; Senior Engineer, Lead Engineer, Quality Engineer, Model Engineer |
| **Claude Opus 4.6** | `claude-opus-4-6` | `claude-opus-4-6` | 1M | 64K | High capability; Principal Engineer (when needed) |
| **Claude Opus 4.7** | `claude-opus-4.7` | `claude-opus-4.7` | 1M | 128K | Highest capability; Principal Engineer |
| **Claude Opus 4.8** | `claude-opus-4.8` | `claude-opus-4.8` | 1M | 128K | Latest, highest capability; Security Engineer |

**CRITICAL RULE:** Model names use HYPHENS (e.g., `claude-opus-4.7`), NOT DOTS (e.g., ~~claude-opus-4.7~~).

### Harness-Specific Model Format

Each harness transforms the base model ID for its runtime:

| Harness | Source Model | Rendered Format | Official Docs |
|---------|--------------|-----------------|---------------|
| **Copilot CLI** | `claude-opus-4.7` | `claude-opus-4.7` | [Supported Models](https://docs.github.com/en/copilot/reference/ai-models/supported-models) |
| **Claude (Direct API)** | `claude-opus-4.7` | `claude-opus-4.7` | [Claude API](https://docs.anthropic.com/claude/docs/models-overview) |
| **OpenCode** | `claude-opus-4.7` | `github-copilot/claude-opus-4.7` | [OpenCode Docs](https://github.com/github/opencode) |
| **Pi (pi.dev)** | `claude-opus-4.7` | `claude-opus-4.7` | [Pi.dev](https://pi.dev/) |

### Model Assignment by Agent Role

As of 2026-05-25:

- **Orchestrator:** `claude-haiku-4.5` (fast, low-cost, routing-only)
- **Engineer:** `claude-haiku-4.5` (fast, pre-planned tasks)
- **Senior Engineer:** `claude-sonnet-4.6` (complex coding, unscoped work)
- **Lead Engineer:** `claude-sonnet-4.6` (code review, architectural guidance)
- **Quality Engineer:** `claude-sonnet-4.6` (quality gates, verification)
- **Model Engineer:** `claude-sonnet-4.6` (metrics analysis, recommendations)
- **Principal Engineer:** `claude-opus-4-6` or `claude-opus-4.7` (cross-service architecture)
- **Security Engineer:** `claude-opus-4.8` (complex threat modeling, vulnerability analysis)

### Validation & Enforcement

**Mandatory Checks** (all must pass):

1. **Source Files** (`src/agents/*.md`):
   - All `model:` fields must use hyphen format: `claude-{family}-{version-with-hyphens}`
   - Pre-commit hook validates via `renderer/validate_agents.py`
   - Test: `tests/test_agent_model_names.py`

2. **Validator** (`renderer/validate_agents.py`):
   - `KNOWN_MODELS` constant must list only hyphen-format models
   - Validator rejects any model with dots (e.g., `claude-opus-4.7`)
   - Test: `tests/test_renderer_validation.py`

3. **Documentation** (`docs/AGENTS.md`):
   - Agent registry table must match source files exactly
   - Pre-commit hook enforces sync between agent files and registry
   - Test: `tests/test_agents_registry_sync.py`

4. **Rendered Output** (all harnesses):
   - `dist/copilot/agents/*.agent.md` must use hyphen format
   - `dist/claude/agents/*.md` must use hyphen format
   - `dist/opencode/agents/*.md` must use hyphen format
   - `dist/pi/agent/pi.yml` must use hyphen format
   - Test: `tests/test_render_model_names.py` (validates all renderers)

### No-Regression Tests

**Test File:** `tests/test_model_naming_compliance.py`

Tests verify:

```python
# ✅ Approved formats
"claude-haiku-4.5"  # Hyphens only
"claude-sonnet-4.6"
"claude-opus-4.7"

# ❌ Forbidden formats (tests must FAIL if found)
"claude-haiku-4.5"  # Dots NOT allowed
"claude-sonnet-4.6"
"claude.opus-4.7"   # Mixed format
"CLAUDE-HAIKU-4-5"  # Uppercase
```

### Regression Mitigation

If a model name with dots is committed:

1. **Pre-commit hook catches it** — commit is rejected with error message
2. **CI/CD catches it** — `test_model_naming_compliance.py` fails
3. **Quality Engineer review** — mandatory validation step in HANDBACK review
4. **Automatic fix available** — `scripts/fix-model-names.py` converts dots to hyphens

### Future Changes

**Procedure to add or update approved models:**

1. Verify official source (Anthropic, GitHub, pi.dev documentation)
2. Update SPEC.md (this section)
3. Add to `KNOWN_MODELS` in `renderer/validate_agents.py`
4. Update `docs/AGENTS.md` agent registry
5. Run full test suite (`make test`)
6. Commit with clear message: `fix: add/update model {name} per official docs (source: {url})`

---

## Update Log

- **2026-05-02:** Phase 5.10 specification published. Documented ORCHESTRATOR-FIRST EXECUTION MODEL, removed deprecated external scripts and cron jobs, added span capture and artifact indexing requirements.
- **2026-05-16:** Added SDLC Enforcement Hooks section documenting the three git hooks (pre-commit, commit-msg, pre-push), installation, bypass procedures, and references to docs/SDLC-HOOKS.md.
- **2026-05-17:** Added Phase 3 Token Visibility & Budget Checking section. Documents token tracking requirements, budget checking requirements, cost attribution, production deployment requirements, and implementation references.
- **2026-05-25:** Added Model Naming & Harness Compatibility section. Documents approved model names per official Anthropic/GitHub/pi.dev sources, validates hyphen format across all harnesses, adds no-regression tests and enforcement procedures.
- **2026-06-08:** Reconciled queue path contradictions throughout early sections. Canonical path is `~/.agentic-engineers/{session-id}/{harness}/queue/` per the locked section (Queue Architecture & Paths, lines ~495–541). All early references to `~/.copilot/queue/`, `~/.claude/queue/`, and `artifacts/queue/` as "current" paths updated to the canonical path. Locked section unchanged (it is the authoritative source).

---

**Document Status:** Specification current. Phase 3 complete. Phase 6 span capture in progress.  
**Maintenance:** Update when agent roles, models, routing rules, or SKILLS change.

---

## Specification

This document defines the operational specification for the Agentic Engineers framework, including the orchestrator-first execution model, agent routing, queue management, security requirements, and compliance gates.

---

## Core Requirements

1. **Orchestrator-First Execution**: All work must flow through the Orchestrator agent. No direct agent invocation is permitted.
2. **Queue-Based Delegation**: Tasks are queued in session-partitioned directories and processed by agents.
3. **Audit Trails**: Complete audit trails must be maintained for all DELEGATE/HANDBACK operations.
4. **Quality Gates**: All completed work must pass Quality Engineer verification before completion.
5. **Security Compliance**: All code must pass entropy-based credential detection and pattern matching.
6. **Version Management**: Changes are tracked via CHANGELOG and semantic versioning.

---

## Quality Gates

1. **Pre-Commit Gates**: Verify code integrity, SPEC compliance, and pre-push validation
2. **Security Gates**: Entropy detection, SPEC.md compliance, dependency scanning
3. **Framework Integrity**: Ensure consistency across all framework files
4. **Source Validation**: Verify test sources and skill/agent file integrity
5. **Quality Engineer Review**: Final validation of output quality and correctness
6. **Post-Merge Validation**: Continuous monitoring for regressions and quality drift
