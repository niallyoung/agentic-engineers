---
name: Agentic Engineers Implementation Specification
description: Current state of the agent orchestration system, queue mechanics, and operational constraints
version: 1.0
updated: 2026-05-02
phase: 5.10 (Monitoring & Continuous Improvement)
status: Current
type: specification
---

# Agentic Engineers Implementation Specification

**Last Updated:** 2026-05-02  
**Current Phase:** 5.10 (Monitoring & Continuous Improvement with Span Capture & Indexing)  
**Constraint:** No external scripts/tools — all work flows through AGENTS via DELEGATE/HANDBACK

---

## Executive Summary

The Agentic Engineers system uses queue-based delegation to route all work through specialized AI agents (Orchestrator, Engineer, Senior Engineer, Quality Engineer, Lead Engineer, Principal Engineer, Security Engineer, Model Engineer). Each agent is assigned a specific role, model, and effort level. Work flows through a file-based queue system (`artifacts/queue/`) with complete audit trails. Phase 5.10 adds observability via span capture and artifact indexing, both implemented within agent SKILLS (not external tools).

---

## ORCHESTRATOR-FIRST EXECUTION MODEL (MANDATORY)

**This is a hard constraint. All work MUST flow through the Orchestrator. No exceptions.**

### What This Means

1. **No Direct Agent Invocation**
   - Engineers MUST NOT invoke agents directly via tool calls or message passing
   - Engineers MUST NOT create DELEGATE blocks manually and send them to agents
   - Work only flows through the Orchestrator queue system

2. **All Work Enters the Queue**
   - New tasks arrive as files in `artifacts/queue/incoming/{task_id}.yaml`
   - Orchestrator polls this directory every 30-60 seconds
   - No other entry point exists (no Makefile targets, no scripts, no cron jobs, no ad-hoc invocations)

3. **Orchestrator is the Router**
   - Reads incoming task from `incoming/` queue
   - Applies AGENTS.md routing decision tree to determine which agent to delegate to
   - Creates DELEGATE block in `artifacts/delegates/YYYY-MM-DD/` with complete context
   - Sends DELEGATE to agent
   - Receives HANDBACK from agent
   - Routes HANDBACK to Quality Engineer for verification
   - Moves completed task to `done/` queue
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
   - Orchestrator SKILL polls `artifacts/queue/incoming/` every 30-60 seconds
   - Each poll reads new tasks and creates DELEGATEs
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
- ❌ Do NOT invoke subprocess, os.system(), or exec() in agent code
- ❌ Do NOT invoke agents directly without going through Orchestrator queue
- ❌ Do NOT create manual DELEGATE blocks and send them to agents
- ❌ Do NOT skip quality checks or escalation rules
- ❌ Do NOT implement observability outside of agent SKILLS
- ❌ Do NOT use "trivial fixes" or other undefined escape clauses to bypass queue
- ❌ Do NOT allow CI/CD or external systems to invoke scripts directly
- ❌ Do NOT create automated cron job installers or pre-configured cron jobs

**Why This Constraint Exists:**
The queue-first model ensures all work is tracked, routable, optimizable, and auditable. External scripts and manual invocations create gaps in observability, break routing logic, and prevent the system from improving itself through the feedback loop. By making Orchestrator the single point of control, we guarantee:
- ✅ Complete audit trail of all work
- ✅ Correct routing via decision tree
- ✅ Accurate cost tracking via span capture

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
2. Queue work as a DELEGATE block in `artifacts/queue/incoming/`
3. Let Orchestrator route and delegate to the appropriate agent
4. Agent executes and returns HANDBACK

This is the ONLY allowed entry point for all work.
- ✅ Autonomous optimization via Model Engineer feedback
- ✅ No bypasses or edge cases

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

### Agents & Roles (Dark Factory Model)

All work enters via **Orchestrator** (default entry point). Orchestrator applies routing decision tree to delegate to specialists.

| Role | Model | Effort | Cost/Task | Purpose |
|------|-------|--------|-----------|---------|
| **Orchestrator** | claude-haiku-4-5 | low | $0.03 | Entry point; routing decisions; queue management; span capture; metrics collection |
| **Engineer** | claude-haiku-4-5 | high | $0.03 | Execute well-scoped tasks with pre-written plans |
| **Senior Engineer** | claude-sonnet-4-6 | high | $0.09 | Complex coding without plan; diagnosis; planning |
| **Lead Engineer** | claude-sonnet-4-6 | high | $0.09 | Code review; quality verification; unblock stuck tasks |
| **Quality Engineer** | claude-sonnet-4-6 | medium | $0.09 | Tier 1 quality checks; model suitability assessment |
| **Principal Engineer** | claude-opus-4-6 | high | $0.15 | Cross-service architecture; complex multi-step planning |
| **Security Engineer** | claude-opus-4-7 | max | $0.15 | Security analysis; vulnerability audits; threat modeling |
| **Model Engineer** | claude-sonnet-4-6 | high | $0.09 | Analyze feedback; recommend optimal model/effort; generate artifact index |

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

## Routing Decision Tree (Orchestrator)

When Orchestrator polls `artifacts/queue/incoming/` and finds a task:

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

### Queue Structure

```
artifacts/queue/
├── incoming/      # New tasks, ready for Orchestrator to process
├── processing/    # Work assigned to agent, awaiting HANDBACK
└── done/          # Completed work, ready for human decision
```

### Queue Flow

1. **Incoming** → New task arrives as `{task_id}.yaml`
2. **Orchestrator polls** (every 30-60s):
   - Reads task from `incoming/`
   - Applies routing decision tree
   - Creates DELEGATE in `artifacts/delegates/YYYY-MM-DD/DELEGATE-{task_id}-{role}.yaml`
   - Sends DELEGATE to agent
   - Deletes from `incoming/` (or archives)
3. **Processing** → Agent returns HANDBACK to `{task_id}-HANDBACK-{role}.yaml`
4. **Orchestrator routes completion**:
   - If complete → Route to Quality Engineer
   - If blocked → Escalate to Lead/Senior Engineer
5. **Done** → Human/external system reads final decision from `artifacts/queue/done/`

### Artifact Storage

| Artifact | Path | Created By | Used By |
|----------|------|-----------|---------|
| DELEGATE | `artifacts/delegates/YYYY-MM-DD/DELEGATE-{task_id}-{role}.yaml` | Orchestrator | Agent (receives), Orchestrator (ref) |
| HANDBACK | `artifacts/queue/processing/{task_id}-HANDBACK-{role}.yaml` | Agent | Orchestrator (routes), QE (verifies) |
| SPAN | `artifacts/2026-MM-DD/SPAN-{timestamp}-{agent_type}.yaml` | Orchestrator | Model Engineer (analysis), index generation |
| Decision | `artifacts/queue/done/{task_id}-{decision}.yaml` | Orchestrator | Human / external system |

---

## DELEGATE/HANDBACK Protocol

### DELEGATE Format (Orchestrator → Agent)

```yaml
---
handoff_type: DELEGATE
task_id: {unique_id}
role: Engineer | Senior Engineer | Lead Engineer | Quality Engineer | ...
model: claude-haiku-4-5 | claude-sonnet-4-6 | claude-opus-4-6 | ...
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
status: complete | blocked | partial
deliverables: [files changed, tests added, etc.]
tests: ["make verify": PASS (N tests), coverage: X%]
tokens_in: {estimate}
tokens_out: {estimate}
model: {actual_model_used}
effort: {actual_effort}
duration_minutes: {wall_clock_time}
escalations: {count}
model_assessment: [for Quality Engineer] haiku_suitable | sonnet_would_be_better | opus_required
confidence: [0.0-1.0, for Model Engineer feedback]
---
```

---

## SKILLS: Role-Specific Execution Details

### Engineer

**Model:** claude-haiku-4-5 (high effort)  
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

**Model:** claude-sonnet-4-6 (high effort)  
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

**Model:** claude-sonnet-4-6 (high effort)  
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

**Model:** claude-sonnet-4-6 (medium effort)  
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

**Model:** claude-opus-4-7 (max effort)  
**Cost Target:** 1%

Scan for vulnerabilities, check dependencies, verify access controls.

**Output:** Findings by severity (CRITICAL, HIGH, MEDIUM, LOW).

### Model Engineer

**Model:** claude-sonnet-4-6 (high effort)  
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

**Model:** claude-haiku-4-5 (low effort)  
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
6. (Optional, async) Request Model Engineer to regenerate `artifacts/index.json`

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
- **ALL work flows through queue:** `artifacts/queue/incoming/ → processing/ → done/`
- **Orchestrator polls** every 30-60 seconds (runs in harness, no external cron/tools)
- **DELEGATE stored** in `artifacts/delegates/YYYY-MM-DD/` for reference
- **HANDBACK stored** in `artifacts/queue/processing/` (moved to done/ after QE review)

### Planning & Escalation
- **Engineer MUST NOT receive task without pre-written `plan`** in DELEGATE (except trivial fixes)
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
  agent_model: "claude-haiku-4-5" | "claude-sonnet-4-6" | etc.
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
- **Advanced** → Opus roles (Principal Engineer: 4.6, Security Engineer: 4.7) with high/max effort

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
- **PHASE-5.10-INTEGRATION-GUIDE.md** — Phase 5.10 workflow from developer perspective
- **FEEDBACK-LOOPS.md** — Model Engineer feedback and cost optimization
- **TOKEN-USAGE-TRACKING.md** — Token accounting and cost calculation

---

**Document Status:** Specification complete. Implementation in progress (Phase 5.10/6).  
**Maintenance:** Update when agent roles, models, routing rules, or SKILLS change.
