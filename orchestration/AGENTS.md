# Agent Orchestration & Effort Profiles

A guide to efficiently assign AI agents (Anthropic Opus, Sonnet, Haiku) across 8 specialized roles, with continuous optimization feedback loop for cost and quality.

**Primary Entry Point:** Orchestrator (Haiku, low effort) routes all work to specialists based on task complexity and requirements.

**Active Queue Loop:** Orchestrator continuously monitors `artifacts/queue/incoming/ → processing/ → done/`, ensuring work flows smoothly and escalations are handled automatically (see [QUEUE-PROTOCOL.md](QUEUE-PROTOCOL.md)).

**Red-Green TDD Enforcement:** ALL code changes require Red-Green TDD (write failing test → implement fix → refactor). Evidence of each phase must appear in HANDBACK or work is rejected by Quality Engineer (see [SKILLS.md](SKILLS.md) > Engineer Skills).

**Optimization Loop:** Engineer → Quality Engineer → Model Engineer → Orchestrator (improved routing for future similar tasks).

**Goal:** Minimize cost, reduce latency, and maximize quality using right agent + effort combo. Self-improving through feedback-driven model selection.

**Key Feature:** Model Engineer analyzes QE feedback to recommend optimal model/effort combinations, creating autonomous cost optimization.

---

## Primary Assignments (Dark Factory Model)

**Default Entry Point:** Orchestrator (Haiku 4.5, Low Effort)  
**Entry Rule:** All work flows through Orchestrator for routing. No direct delegation from external sources.

| Role | Model | Effort | Cost/Task | Use When |
|---|---|---|---|---|
| **Orchestrator** | claude-haiku-4-5 | low | $0.03 | All entry points; routing decisions; task management; metrics collection; model recommendations |
| **Engineer** | claude-haiku-4-5 | high | $0.03 | Well-scoped task with pre-written plan; low-medium complexity coding/implementation |
| **Quality Engineer** | claude-sonnet-4-5 | medium | $0.09 | Post-implementation quality gate; code review; model suitability assessment |
| **Senior Engineer** | claude-sonnet-4-5 | high | $0.09 | Complex coding tasks; implementation without fully pre-planned spec; diagnosis of root causes |
| **Lead Engineer** | claude-sonnet-4-6 | high | $0.09 | Code review; quality decisions; medium-complexity planning; architectural guidance |
| **Principal Engineer** | claude-opus-4-6 | high | $0.15 | Cross-service architecture; complex multi-step planning; design decisions affecting >2 repos |
| **Security Engineer** | claude-opus-4-7 | max | $0.15 | Security analysis; threat modeling; vulnerability audits; final escalation path |
| **Model Engineer** | claude-sonnet-4-5 | high | $0.09 | Analyzes quality/cost feedback from QE; recommends optimal model/effort combinations for future similar tasks |

**Routing Rules** (for Orchestrator):
- If task is security-scoped → Security Engineer (block all other routes)
- Else if task requires cross-service architecture → Principal Engineer
- Else if task has no pre-written plan AND is complex coding → Senior Engineer (to write plan first)
- Else if task is code review or quality verification → Quality Engineer
- Else if task is architectural guidance or medium planning → Lead Engineer
- Else if task is well-planned, low-medium complexity → Engineer
- Else → (escalate to human for clarification)

**Optimization Loop** (automatic, post-execution):
- After Quality Engineer verifies task → Model Engineer analyzes (quality/cost/tokens/QE feedback)
- Model Engineer generates model/effort recommendations with confidence scores
- Orchestrator applies recommendations to next similar task
- System improves routing over time with no manual intervention

**Agent Implementations**:
- ✅ [Orchestrator Agent](./agents/general-orchestrator-agent.md)
- ✅ [Engineer Agent](./agents/engineer-agent.md)
- ✅ [Senior Engineer Agent](./agents/senior-engineer-agent.md)
- ✅ [Lead Engineer Agent](./agents/lead-engineer-agent.md)
- ✅ [Quality Engineer Agent](./agents/quality-engineer-agent.md)
- ✅ [Principal Engineer Agent](./agents/principal-engineer-agent.md)
- ✅ [Spec Engineer Agent](./agents/spec-engineer-agent.md) (Quality Gate sub-agent)
- ✅ [Security Engineer Agent](./agents/security-agent.md) (Quality Gate sub-agent)
- ✅ [Model Engineer Agent](./agents/model-engineer-agent.md) (Feedback loop)

**Mandatory Constraints:**

**QUEUE-BASED ROUTING** (see [QUEUE-PROTOCOL.md](QUEUE-PROTOCOL.md)):
- ALL work MUST flow through `artifacts/queue/incoming/ → processing/ → done/` queue system
- Orchestrator actively monitors queue every 30-60 seconds and routes appropriately
- DELEGATE artifacts stored in `artifacts/delegates/YYYY-MM-DD/` for reference
- HANDBACK stored in `artifacts/queue/processing/` before Quality Engineer verification
- Work must include both DELEGATE (what) and HANDBACK (outcome) artifacts

**RED-GREEN TDD ENFORCEMENT**:
- Engineer MUST apply Red-Green TDD to ALL code changes (`red_green_tdd_required: true` in DELEGATE)
- RED phase: Write failing test demonstrating bug/requirement
- GREEN phase: Implement minimal fix to pass test
- REFACTOR phase: Improve code without changing behavior
- HANDBACK MUST include `red_green_evidence` documenting each phase with line numbers
- Quality Engineer MUST verify evidence exists and is clear; if missing → **REJECT** (status: rejected)

**PLAN & ESCALATION**:
- Engineer MUST NOT receive a task without a pre-written `plan` in the DELEGATE block (except one-sentence bug fixes)
- If Engineer cannot execute plan → status `blocked` in HANDBACK; Orchestrator re-routes to Senior Engineer
- If work rejected by QE → Orchestrator creates rework DELEGATE; retry limit = 3 before escalate to Senior Engineer

**ORCHESTRATOR CONSTRAINTS**:
- **Orchestrator MUST NOT perform work — only route, track, and apply Model Engineer recommendations.** ALL execution work (code edits, implementations, reviews, documentation work) MUST be delegated via HANDOFF to appropriate role. Direct execution pollutes Orchestrator context and prevents isolated Engineer sessions.
- Orchestrator MUST use QUEUE-PROTOCOL active loop for task coordination (no manual handoffs)
- Orchestrator MUST apply Model Engineer recommendations for next similar task

**ROLE-SPECIFIC RULES**:
- Security Engineer is invoked ONLY for security-scoped tasks; no other role escalates directly to Security Engineer (go through Principal first)
- Quality Engineer MUST provide `model_assessment` feedback in HANDBACK for Model Engineer analysis
- Spec Engineer (Quality Gate) validates code against docs/SPEC.md on every commit
- Lead Engineer/Senior Engineer unblock Engineer when status `blocked` is reported

**Routing Decision Tree (for Orchestrator):**

When Orchestrator polls `artifacts/queue/incoming/` and finds a new task:

1. Is task security-scoped? → **Security Engineer** (see [SKILLS.md](SKILLS.md) > Security Engineer Skills)
2. Is task cross-service architecture (affects >2 repos)? → **Principal Engineer** (see [SKILLS.md](SKILLS.md) > Principal Engineer Skills)
3. Is task complex coding WITHOUT pre-written plan? → **Senior Engineer** (to plan first; see [SKILLS.md](SKILLS.md) > Senior Engineer Skills)
4. Is task code review or quality verification? → **Lead Engineer** or **Quality Engineer** (see [SKILLS.md](SKILLS.md) > Lead Engineer Skills, Quality Engineer Skills)
5. Is task well-planned, low-medium complexity? → **Engineer** (see [SKILLS.md](SKILLS.md) > Engineer Skills)
6. Otherwise → Escalate to human (unclear scope)

**For each route:** Orchestrator creates DELEGATE block with mandatory fields:
- `role`, `model`, `effort` (from AGENTS.md columns)
- `plan` (pre-written concrete steps, required for Engineer)
- `red_green_tdd_required: true` (for code changes)
- Store DELEGATE in `artifacts/delegates/YYYY-MM-DD/DELEGATE-{task_id}-{role}.yaml`
- Move task to `processing/` and await HANDBACK

**Handoff Protocol (Mandatory):**
All agent-to-agent work transfer uses structured DELEGATE/HANDBACK markup blocks (see [HANDOFF.md](HANDOFF.md) for format). Markup enables:
- Compact context transfer (no re-summarisation)
- Machine-readable task tracking
- Metrics collection per task (see METRICS.md)

**Example:**
Orchestrator → Engineer (via DELEGATE block):
```yaml
---
handoff_type: DELEGATE
task_id: 2026-04-24-fix-token-timeout
role: Engineer
model: claude-haiku-4-5
effort: high
scope: Fix token validation timeout in {service-name}; do not change Cognito config
context:
  - File: lambda/api/main.go:92 (expiry check)
  - Error: "Token rejected after 1hr on mobile"
  - Root cause from Lead Engineer: clock skew on device
plan:
  1. Add 30s grace period to exp claim check at line 92
  2. Write test TestTokenExpiryGracePeriod
  3. Run "make verify"
success_criteria:
  - "make verify" passes
  - Mobile e2e auth passes
---
```

Engineer → Orchestrator (via HANDBACK block):
```yaml
---
handoff_type: HANDBACK
task_id: 2026-04-24-fix-token-timeout
status: complete
deliverables:
  - Modified: lambda/api/main.go:92
  - Added: lambda/api/main_test.go (TestTokenExpiryGracePeriod)
tests:
  - "make verify": PASS (48 tests)
tokens_in: 1200
tokens_out: 820
model: claude-haiku-4-5
effort: high
duration_minutes: 18
escalations: 0
---
```

**Unattended Mode (YOLO Operation):**
- Voice-notify every 5–10 min with progress checkpoint (tokens, task count, blockers)
- No interactive prompts — escalate decisions autonomously, don't wait for human input
- Architect (Sonnet, high effort) has authority to make architectural calls without human approval (within security review scope)
- Engineer implements immediately per Architect guidance
- Only pause if: (1) merge conflict, (2) CI failure post-push, (3) out-of-scope issue discovered
- Proceed with full autonomy; human reviews post-completion

**Optimization Feedback Loop** (New in Phase 2C):

After task completion:
```
1. Engineer executes → returns HANDBACK
2. Quality Engineer verifies → adds model_assessment feedback
3. Orchestrator records metrics to ~/.claude/metrics/
4. Model Engineer analyzes:
   - Quality score vs. expected (for assigned model)
   - Token efficiency (cost_per_quality_point)
   - QE model suitability feedback
   - Historical samples for same task signature
5. Model Engineer generates recommendations:
   - Rank 1 (highest confidence): use for next similar task
   - Rank 2 (exploratory): consider A/B test
   - Rank 3 (alternative): fallback if rank 1 unavailable
6. Orchestrator applies rank_1 for next matching task
```

This creates autonomous cost optimization: each task makes future similar tasks better routed.

**Legacy Tiers (still valid, now mapped to roles):**
- **Lightweight** → Haiku Orchestrator (low) or Haiku Worker (high)
- **Standard** → Sonnet (high) or Opus 4.6 (high)
- **Advanced** → Opus 4.7 (max) or Opus 4.6 (high)

---

## Effort Levels & Token Budget

Set effort level when assigning to sub-agents. Effort controls reasoning depth and exploration scope.

| Level | Cost | Use Case | Expected Output |
|-------|------|----------|-----------------|
| **Low** | Minimal | Code cleanup, lint fixes, simple PRs | Minimal explanation, direct changes, no exploration |
| **Medium** | Moderate | Bugs with clear root cause, standard features, security fixes | Balanced: explain what changed, why, test verification |
| **High** | Standard | Complex bugs, architectural changes, security hardening | Deep reasoning, multiple approaches considered, thorough testing |
| **Extra High** | Unconstrained | CI failures with unclear root cause, major refactors, advanced analysis | Full exploration and validation, no cost/time constraints |

### Effort Selection by Task

- **Simple bug fix (typo, obvious logic error):** Low effort + Lightweight agent
- **Security fix (injection, validation):** Medium effort + Lightweight agent (or High if reasoning required)
- **CI failure (first time seeing error):** High effort + Standard agent (red-green TDD)
- **Architecture review (threat modeling):** Extra High effort + Advanced agent
- **Feature branch (new API endpoint):** Medium effort + Lightweight agent (or Standard if complex logic)

---

## Voice-Notify Strategy & Personalities

Use voice notifications with distinct personalities for each (model + effort) combo. Helps reduce context-switching while long tasks run.

**Personalities (See ORCHESTRATION.md for details):**
| Combo | Personality | Character | Use |
|-------|-------------|-----------|-----|
| Haiku (Low) | **Dispatch** | Conversational, efficient | Orchestration, routing, status |
| Haiku (High) | **Engineer** | Focused, technical | Implementation, plan execution |
| Sonnet (High) | **Architect** | Confident, analytical | Planning, diagnosis, complex code |
| Opus 4.6 (High) | **Sage** | Thoughtful, nuanced | Complex planning, design |
| Opus 4.7 (Max) | **Guardian** | Authoritative, security-focused | Security analysis, threat modeling |

**Alert on:**
- ✓ Handoff between agents (voice announces new personality + task type)
- ✓ Long task completion (E2E tests, CI runs, deployments)
- ✓ Cost/token checkpoint (every 5–10 min during active work)
- ✓ Blocking issue (agent stuck, CI red, human decision needed)
- ✓ Milestones (repo complete, phase transition, group completion)

**Don't notify:** Routine progress, successful test runs, incremental changes.

**Implementation:** Platform-dependent (Claude Code: `say` with volume control). See ORCHESTRATION.md for harness integration patterns.

---

## Standard Workflows (Dark Factory)

See [ORCHESTRATION.md](ORCHESTRATION.md) for detailed handoff protocol and daily workflow examples.

### Pattern 1: Security Audit

**Stage 1:** Orchestrator (Dispatch) routes to **Guardian (Opus 4.7, max effort)**  
→ Produce SECURITY_REVIEW_TODO.md with threat assessment  
**Stage 2:** Orchestrator delegates to **Engineer (Haiku Worker, high effort)**  
→ Execute autonomy-flagged fixes from TODO.md  
**Stage 3:** Orchestrator routes to **Architect (Sonnet, high effort)**  
→ Integration testing, smoke tests, green CI  
**Voice:** Dispatch → Guardian → Engineer → Architect → Dispatch ("Security audit complete")

### Pattern 2: Bug Triage & Fix

**Stage 1:** Orchestrator routes to **Architect (Sonnet, high effort)**  
→ Reproduce, root-cause analysis, RED test + plan  
**Stage 2:** Orchestrator delegates to **Engineer (Haiku Worker, high effort)**  
→ Code fix following plan, tests green  
**If Engineer stuck:** Re-escalate to Architect with context  
**Voice:** Dispatch → Architect ("Root cause identified") → Engineer ("Fix in progress") → Dispatch ("CI green")

### Pattern 3: Feature Implementation

**Stage 1:** Task complexity assessment (handled by Dispatch orchestrator)  
**If simple:** Delegate to **Engineer (Haiku Worker, high effort)**  
**If complex:** Route to **Sage (Opus 4.6, high effort)** for planning, then Engineer for impl  
**Voice:** Dispatch → [Sage (optional)] → Engineer → Dispatch ("Feature merged")

### Pattern 4: Routine Tasks (Cleanup, Updates, Chores)

**Direct:** Dispatch routes to **Engineer (Haiku Worker, low-medium effort)**  
- Version bumps, lint fixes, comment improvements  
- No planning needed; clear, narrow scope  
**Voice:** Dispatch → Engineer → Dispatch ("Chore completed")

---

## Cost Targets (Phase 2C with Autonomous Optimization)

Updated for Phase 2C with Model Engineer optimization role:

- **Orchestrator (Haiku Low):** 60% (routing, status, task management, applying recommendations)
- **Engineer (Haiku High):** 18% (well-scoped implementation with pre-written plans)
- **Quality Engineer (Sonnet Medium):** 8% (quality gate verification + model assessment feedback)
- **Senior Engineer (Sonnet High):** 7% (complex coding, root-cause diagnosis, planning)
- **Model Engineer (Opus 4.7 High):** 3% (analyze metrics, generate recommendations, optimize future routing)
- **Lead Engineer (Sonnet High):** 2% (code review, quality decisions, medium-complexity planning)
- **Principal Engineer (Opus 4.6 High):** 1% (cross-service architecture, rare complex decisions)
- **Security Engineer (Opus 4.7 Max):** 1% (security audits, threat modeling, final escalation)

**Target Improvement:** Model Engineer recommendations reduce overall cost by 15-25% over 3 months (through better routing + reduced rework).

Measured quarterly; adjust if cost targets drift.

---

## Dark Factory Best Practices

### Handoff Checklist

- [ ] Gather context: uncommitted files, errors, attempted approaches
- [ ] Annotate handoff: "Escalating to [Personality] for [task type]"
- [ ] Provide state: current repo, blocker, relevant TODO items
- [ ] Set expectations: effort level, completion time, success criteria
- [ ] Monitor progress: voice-notify on milestones, cost every 5–10 min

### Avoid

❌ Skipping Dispatch orchestrator (always start there)  
❌ Using Guardian for non-security analysis  
❌ Using Engineer without a detailed plan (route to Architect first)  
❌ Calling agents without `make verify` locally  
❌ Re-running analysis without state changes  

### Prefer

✓ All work flows through Dispatch (Haiku orchestrator, low effort)  
✓ Dispatch routes appropriately per handoff decision tree  
✓ Voice-notify personality announces each handoff  
✓ Cost targets: 70% Dispatch, 15% Engineer, 10% Architect, 3% Sage, 2% Guardian  
✓ Parallelizing within a repo (Dispatch coordinates multiple sub-agents)  
✓ Sequential repos (finish one, then move to next)  
✓ Monitoring voice-notify every 5–10 min during active work  

---

## Real-World Example: Security Fix Cycle

**Task:** Fix security bugs in 3 repos ({service-name}, {service-name}, {service-name}).

**Optimal Plan:**
1. Advanced agent (Extra High effort, ~2 hours) → Create detailed TODO.md per repo
2. Lightweight agents (Medium effort, parallel groups):
   - **Group A:** {service-name} + {service-name} (2 agents, 1 hour each)
   - Check cost every 5 min; voice-notify on completion
   - **Group B:** {service-name} (1 agent, 1 hour)
3. Standard agent (High effort, ~30 min) → E2E regression test + integration check
4. Voice-notify: "All 3 repos green, ready for production deploy"

**Cost:** ~40% of doing everything with Standard tier  
**Wall Clock Time:** ~4 hours (vs. 8+ hours if sequential)

---

## Notification Examples

### Completion Notifications

```
"Advanced analysis complete, reviewing TODO files"
"{service-name} security fixes merged, waiting on {service-name}"
"All CI pipelines green, integration tests running"
```

### Cost Check-In (every 5–10 min during heavy work)

```
"Usage: 15K tokens used, 12K remaining in group A"
"Group B complete, moving to integration phase"
"Lightweight agent efficiency: 3 repos completed on medium budget"
```

### Blocking Issues

```
"Lightweight agent stuck on type checking, escalating to Standard"
"CI failure in {service-name}, human review needed"
"Advanced analysis flagged 3 design decisions — awaiting human guidance"
```

---

## Checklist: Before Starting Work

- [ ] Start with Dispatch (Haiku, low effort) — never skip orchestrator
- [ ] Provide task description; let Dispatch route to appropriate specialist
- [ ] Task is well-scoped (not vague, not "fix everything")
- [ ] Success criteria are clear (tests passing, CI green, code review passed)
- [ ] Repo is in valid state (no uncommitted changes, main is green)
- [ ] For security work: Guardian analysis done (TODO.md) before Engineer implementation
- [ ] For bugs: Architect diagnosis done (plan) before Engineer implementation
- [ ] Cost monitoring enabled (voice-notify every 5–10 min, personalities announced)

---

## FAQ

**Q: Should I talk directly to Guardian/Architect/Engineer, or always go through Dispatch?**  
A: Always start with Dispatch (Haiku, low effort). Dispatch routes you to the right specialist, announces personality, and coordinates handoffs. This ensures consistent cost tracking and optimal routing.

**Q: What if I know I need Guardian (security analysis)?**  
A: Tell Dispatch: "Route to Guardian for security analysis of X." Dispatch will escalate and announce the handoff.

**Q: Can Engineer implement without a plan from Architect?**  
A: Not recommended. If there's uncertainty, Dispatch routes to Architect first for a plan, then to Engineer for implementation. This avoids wasted effort and re-work.

**Q: What if Engineer gets stuck?**  
A: Engineer escalates to Architect (via Dispatch) with context: current state, attempted approaches, specific error. Architect diagnoses and refines the plan.

**Q: Can multiple agents work in parallel?**  
A: Yes, if they're in different repos or files. Dispatch coordinates; voice-notify alerts on milestones. Avoid same file (merge conflicts, contention).

**Q: Is this harness-specific?**  
A: No. AGENTS.md + ORCHESTRATION.md define the *model* assignments and *personality* framework. Any harness (Claude Code, GitHub Copilot, custom, open-harness) can implement these patterns by routing to the right Anthropic model.

**Q: How do I evolve personalities and skills?**  
A: ORCHESTRATION.md includes a roadmap for v2–v4 improvements. Quarterly reviews assess effectiveness, cost targets, and skill gaps. Updates feed back into AGENTS.md and skill definitions.

---

## Implementation Notes for Teams

This file provides a standard decision framework for AI agent assignment using **Anthropic models** (Opus, Sonnet, Haiku) as the default tier mapping.

**Model Mapping:**
- **Advanced** → Anthropic Opus 4.7
- **Standard** → Anthropic Sonnet 4.6
- **Lightweight** → Anthropic Haiku 4.5

**Harness/Provider Agnostic:** These tiers are independent of the tool used to invoke the models (Claude Code, GitHub Copilot, custom harness, open-harness, etc.). The framework remains stable as the platform evolves toward a meta-harness/open-harness approach.

## Update Log

- **2026-04-19:** Initial AGENTS.md created (vendor-neutral) during {service-name}/{service-name}/{service-name} security hardening cycle.
- **2026-04-24:** Added Model Engineer role (Phase 2C) with autonomous optimization feedback loop. QE now provides model_assessment feedback. Orchestrator applies Model Engineer recommendations for continuous cost/quality improvement.
- **Recommendation:** Review this guide quarterly and update tier assignments based on new model releases and Model Engineer recommendation trends.
