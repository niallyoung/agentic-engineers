# Agent Orchestration & Effort Profiles

A guide to efficiently assign AI agents (Anthropic Opus, Sonnet, Haiku) across 8 specialized roles, with continuous optimization feedback loop for cost and quality.

**Primary Entry Point:** Orchestrator (Haiku, low effort) routes all work to specialists based on task complexity and requirements.

**Direct Sub-Agent Spawn Delegation:** Orchestrator builds a DELEGATE and spawns the target agent directly (Agent/Task tool), reading the HANDBACK back as the tool result. The queue is retained as a durable audit trail — every DELEGATE and HANDBACK is recorded via `enqueue()` — but it no longer drives dispatch. See [src/AGENTS.md > Direct Sub-Agent Spawn Execution Model](../src/AGENTS.md#direct-sub-agent-spawn-execution-model) and [QUEUE-PROTOCOL.md](QUEUE-PROTOCOL.md).

**Optimization Loop:** Engineer → Quality Engineer → Model Engineer → Orchestrator (improved routing for future similar tasks).

**Goal:** Minimize cost, reduce latency, and maximize quality using right agent + effort combo. Self-improving through feedback-driven model selection.

**Key Feature:** Model Engineer analyzes QE feedback to recommend optimal model/effort combinations, creating autonomous cost optimization.

---

## Model Naming Architecture (LOCKED)

**STATUS:** Permanent. Enforced via tests, pre-commit hooks, and CI gates.

### Canonical Format (Source)

All agents in `src/agents/*.md` use **versioned Claude with DOTS**:

```
model: claude-{variant}-{major}.{minor}
Examples: claude-haiku-4.5, claude-sonnet-4.6, claude-opus-4.8
```

### Per-Harness Transformations

Each harness renders the canonical format according to its requirements:

| Harness | Transforms To | Reason |
|---------|---------------|--------|
| **Copilot CLI** | `claude-opus-4.8` (pass-through) | Accepts Anthropic API format (dots required) |
| **OpenCode** | `claude-opus-4-7` (dots→hyphens) | CLI requires hyphens in version |
| **Claude Code** | `opus` (short alias) | Web UI uses short aliases for UX |
| **Pi.dev** | `claude-opus-4-7` or dated versions | Anthropic API format (hyphens, optional date) |

### Forbidden Patterns (All Contexts)

- ❌ GPT models (gpt-4, gpt-4o, gpt-4o-mini)
- ❌ Unversioned Claude (claude-opus without -4.7)
- ❌ Mixed formats (claude-opus-4_5 or claude-opus-4-7 in source)
- ✅ Correct: Use canonical format with DOTS in source

### Rationale

Model naming broke repeatedly across commits due to confusion about per-harness format requirements. By documenting the **canonical format (source) + per-harness transformations (renderers)**, we:
1. Make source agents maintainable (one format to remember)
2. Automate harness-specific transformations
3. Prevent regressions via tests + pre-commit hooks + CI enforcement

### References

- **Complete architecture:** [SPEC.md > Model Naming Architecture](../SPEC.md)
- **Tests:** [test_model_naming_compliance.py](../tests/test_model_naming_compliance.py) (14 comprehensive tests)
- **Validator:** [validate_agents.py](../renderer/validate_agents.py) (KNOWN_MODELS)
- **Adding agents:** [CONTRIBUTING.md > Model Naming When Adding Agents](CONTRIBUTING/README.md#model-naming-when-adding-agents)

---

## Primary Assignments

See [src/AGENTS.md](../src/AGENTS.md) for the canonical agent roster.

---

## Multi-Model Selection (Tier 3)

Principal Engineer and Security Engineer support model variant selection based on task complexity.

**Decision criteria:**
- Principal Engineer: Use `claude-opus-5` for architecture and design decisions
- Security Engineer: Always use `claude-fable-5` for defensive-only analysis (effort <= medium)

For detailed guidance, decision trees, and examples, see [SPEC.md > Model Selection Architecture](../SPEC.md).

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

**DIRECT SUB-AGENT SPAWN ROUTING** (see [src/AGENTS.md > Direct Sub-Agent Spawn Execution Model](../src/AGENTS.md#direct-sub-agent-spawn-execution-model)):
- Orchestrator builds a DELEGATE and spawns the target role directly (Agent/Task tool), passing the DELEGATE block as the sub-agent's prompt, and reads the HANDBACK back as the tool result — no polling loop is involved
- Every DELEGATE (at spawn) and every HANDBACK (at completion) is durably recorded to the queue via `enqueue()` for audit purposes; the queue is written to, never read from, for control flow (see [QUEUE-PROTOCOL.md](QUEUE-PROTOCOL.md))
- DELEGATE audit copy stored under `.../queue/incoming/TASK-NNN.yaml`; HANDBACK audit copy stored under `.../queue/done/TASK-NNN-handback.yaml`

**PLANNING & ESCALATION**:
- Engineer MUST NOT receive task without pre-written `plan` in DELEGATE (except trivial fixes)
- If Engineer cannot execute plan → report `status: blocked`; Orchestrator escalates to Senior Engineer
- Blocked tasks and rejections escalate automatically per AGENTS.md routing rules

**ORCHESTRATOR CONSTRAINTS**:
- Orchestrator MUST NOT perform work (only route, coordinate, apply recommendations)
- Orchestrator runs in-harness; it spawns sub-agents directly and PAUSES when it has no pending DELEGATEs to issue and no outstanding sub-agent spawns awaiting a HANDBACK (no external cron/scheduler/tools — see [src/AGENTS.md > Pause Condition](../src/AGENTS.md#pause-condition))
- ALL execution work delegated to appropriate role via DELEGATE/HANDBACK

**ROLE-SPECIFIC RULES**:
- Security Engineer is invoked ONLY for security-scoped tasks
- Quality Engineer provides `model_assessment` feedback in HANDBACK (for Model Engineer)
- Lead Engineer/Senior Engineer unblock or redirect Engineer when task blocked
- Each role has specific skills (see SKILLS.md)

**Routing Decision Tree (for Orchestrator):**

When the Orchestrator receives a new task (from the user, or a re-delegation generated from a prior HANDBACK):

1. Is task security-scoped? → **Security Engineer** (see [SKILLS.md](SKILLS.md) > Security Engineer Skills)
2. Is task cross-service architecture (affects >2 repos)? → **Principal Engineer** (see [SKILLS.md](SKILLS.md) > Principal Engineer Skills)
3. Is task complex coding WITHOUT pre-written plan? → **Senior Engineer** (to plan first; see [SKILLS.md](SKILLS.md) > Senior Engineer Skills)
4. Is task code review or quality verification? → **Lead Engineer** or **Quality Engineer** (see [SKILLS.md](SKILLS.md) > Lead Engineer Skills, Quality Engineer Skills)
5. Is task well-planned, low-medium complexity? → **Engineer** (see [SKILLS.md](SKILLS.md) > Engineer Skills)
6. Otherwise → Escalate to human (unclear scope)

**For each route:** Orchestrator creates a DELEGATE block with mandatory fields:
- `role`, `model`, `effort` (from AGENTS.md columns)
- `plan` (pre-written concrete steps, required for Engineer)
- `scope`, `context`, `success_criteria` (see HANDOFF.md for format)
- Spawns the target role directly (Agent/Task tool), passing the DELEGATE block as the sub-agent's prompt
- Records the DELEGATE to the queue via `enqueue()` (audit trail) at or immediately after the spawn call
- Reads the HANDBACK back as the result of the spawn call itself — there is no `processing/` move or poll wait involved

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
task_id: 2026-04-24-fix-token-grace-period
role: Engineer
model: claude-haiku-4.5
effort: high
scope: Implement 30s token expiry grace period in {example-service}; do not change Cognito config
context:
  - File: lambda/api/main.go:92 (expiry check in extractAndValidateScopes)
  - Root cause from Lead Engineer: client-side clock skew on mobile devices
  - Design decision: Add 30s grace window to token expiry validation
plan:
  1. Add TestTokenExpiryGracePeriod test showing expected behavior
  2. Modify line 92 to accept tokens within 30s after expiry
  3. Extract grace period to constant GRACE_PERIOD_SECS
  4. Run "make verify" to confirm all tests pass
success_criteria:
  - "make verify" passes (all tests pass, coverage maintained)
  - New test TestTokenExpiryGracePeriod added and passing
  - Mobile e2e auth tests pass
  - No other repos modified
---
```

Engineer → Orchestrator (via HANDBACK block):
```yaml
---
handoff_type: HANDBACK
task_id: 2026-04-24-fix-token-timeout
status: success
deliverables:
  - Modified: lambda/api/main.go:92
  - Added: lambda/api/main_test.go (TestTokenExpiryGracePeriod)
tests:
  - "make verify": PASS (48 tests)
tokens_in: 1200
tokens_out: 820
model: claude-haiku-4.5
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

## Token Visibility & Monitoring

**New in Phase 2D:** Real-time token tracking for all agents and subagents via the token aggregator plugin.

### Token Tracking Commands

Three CLI commands provide complete visibility into token usage:

```bash
# Real-time token usage by agent
opencode-tokens --session <session-id>

# Budget status (if budget limit set)
opencode-budget --session <session-id> --limit 200000

# List all subagents in session
opencode-subagents --session <session-id>
```

### Key Insights

- **Orchestrator sees only 27%** of actual token usage (341,960 tokens)
- **Subagents account for 73%** of usage (922,062 tokens)
- **Total across 58 sessions:** 1,264,022 tokens
- **No artificial limits** on concurrent agents, depth, or token consumption
- **Proven capacity:** 36 concurrent agents from single parent (observed in production)

### Monitoring Best Practices

**During active work:**
```bash
# Watch token usage in real-time (updates every 5 seconds)
watch -n 5 'opencode-tokens --session <your-session-id>'
```

**Database queries for analysis:**
```bash
# How many agents are running?
sqlite3 ~/.local/share/opencode/opencode.db "
SELECT parent_id, COUNT(*) as children 
FROM session 
WHERE parent_id IS NOT NULL 
GROUP BY parent_id 
ORDER BY children DESC;
"

# What's the deepest nesting?
sqlite3 ~/.local/share/opencode/opencode.db "
WITH RECURSIVE depth_calc AS (
  SELECT id, parent_id, 1 as depth FROM session WHERE parent_id IS NULL
  UNION ALL
  SELECT s.id, s.parent_id, d.depth + 1 FROM session s
  INNER JOIN depth_calc d ON s.parent_id = d.id
)
SELECT MAX(depth) as max_depth FROM depth_calc;
"
```

### Token Budget Allocation

Recommended allocation for typical workflows:

| Role | Tokens | % | Notes |
|------|--------|---|-------|
| Orchestrator (Haiku, low) | 60k | 30% | Routing, coordination, metrics |
| Engineer (Haiku, high) | 80k | 40% | Implementation, well-scoped tasks |
| Quality Engineer (Sonnet, medium) | 30k | 15% | Verification, feedback |
| Senior Engineer (Sonnet, high) | 20k | 10% | Complex tasks, planning |
| Other roles | 10k | 5% | Lead, Principal, Security, Model Engineer |
| **Total** | **200k** | **100%** | Typical session budget |

**Adjust based on:**
- Task complexity (complex tasks need more tokens)
- Parallel delegation (more agents = higher total, but faster wall-clock)
- Model selection (Opus uses more tokens than Haiku)

### Parallel Delegation Token Impact

Parallel delegation **reduces wall-clock time** but increases concurrent token usage:

**Sequential (3 tasks, 1 hour each):**
- Wall-clock: 3 hours
- Peak tokens: 2,000 (one agent at a time)
- Total tokens: 6,000

**Parallel (3 tasks, 1 hour each, concurrent):**
- Wall-clock: 1 hour (66% faster)
- Peak tokens: 6,000 (three agents at once)
- Total tokens: 6,000 (same)

**Benefit:** 2 hours saved with same total token cost. Use parallel delegation when wall-clock time is critical.

### Documentation

- **Quick Start:** `docs/QUICK-START-CONCURRENT-AGENTS.md`
- **Token Plugin:** `~/.config/opencode/.opencode/plugins/TOKEN-AGGREGATOR.md`
- **Capacity Analysis:** `docs/CONCURRENT-SUBAGENT-CAPACITY.md`
- **Testing Guide:** `docs/CONCURRENT-SUBAGENT-TESTING-GUIDE.md`

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

## Standard Workflows

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

## Agentic Engineering Best Practices

### Handoff Checklist

- [ ] Gather context: uncommitted files, errors, attempted approaches
- [ ] Annotate handoff: "Escalating to [Personality] for [task type]"
- [ ] Provide state: current repo, blocker, relevant TODO items
- [ ] Set expectations: effort level, completion time, success criteria
- [ ] Monitor progress: assess milestones, cost every 5–10 min

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

---

## Real-World Example: Security Fix Cycle

**Task:** Fix security bugs in 3 repos ({service-name}, {example-service}, {example-service}).

**Optimal Plan:**
1. Advanced agent (Extra High effort, ~2 hours) → Create detailed TODO.md per repo
2. Lightweight agents (Medium effort, parallel groups):
   - **Group A:** {service-name} + {example-service} (2 agents, 1 hour each)
   - Check cost every 5 min; monitor on completion
   - **Group B:** {example-service} (1 agent, 1 hour)
3. Standard agent (High effort, ~30 min) → E2E regression test + integration check
4. All 3 repos green, ready for production deploy

**Cost:** ~40% of doing everything with Standard tier  
**Wall Clock Time:** ~4 hours (vs. 8+ hours if sequential)

---

## Notification Examples

### Completion Notifications

```
"Advanced analysis complete, reviewing TODO files"
"{service-name} security fixes merged, waiting on {example-service}"
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
"CI failure in {example-service}, human review needed"
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
- [ ] Cost monitoring enabled (assess progress every 5–10 min)

---

## Parallel Delegation (Direct Spawn Fan-Out)

Any agent whose `tools:` frontmatter grants `spawn_subagent` (see
[src/AGENTS.md > Tools-Frontmatter Permission Model](../src/AGENTS.md#tools-frontmatter-permission-model))
can decompose its assigned task into independent sub-tasks and fan them out as
concurrent direct sub-agent spawns, rather than routing everything back through the
Orchestrator serially. This reduces Orchestrator bottleneck and enables true parallel
execution.

### What is Parallel Delegation?

Parallel delegation means a spawning agent issues multiple Agent/Task tool calls in the
same turn — one DELEGATE per independent sub-task — and awaits them concurrently. Each
spawn call blocks until it returns a HANDBACK in-context; once every spawn in a batch
has returned, the spawning agent aggregates the results itself. There is no separate
polling or "wait for children" step — the spawn calls returning *is* the wait.

**Key benefits:**
- ✅ **Decentralized task creation** — no Orchestrator bottleneck; any agent with spawn authority can fan out
- ✅ **Parallel execution** — sub-tasks run concurrently, up to the fan-out limit
- ✅ **In-context aggregation** — the spawning agent combines quality, tokens, and costs once its batch of spawn calls returns
- ✅ **Audit trail preserved** — each DELEGATE and HANDBACK is still recorded via `enqueue()` (see [src/AGENTS.md > Audit-Trail Strategy](../src/AGENTS.md#audit-trail-strategy))
- ✅ **Cycle prevention** — ancestry tracking refuses a spawn that would target a role already in the spawning agent's own ancestry chain

### When to Use Parallel Delegation

Use parallel delegation when:

1. **Task is naturally decomposable** — work can be split into independent sub-tasks
2. **Sub-tasks can run concurrently** — no dependencies between children
3. **Aggregation is meaningful** — results combine into a coherent output
4. **Scope is large** — multiple agents working in parallel saves time

**Example scenarios:**
- Analyzing 3+ microservices in parallel (each gets an Engineer)
- Security audit of multiple repos (each gets a Security Engineer)
- Feature implementation across 4+ services (each gets an Engineer)
- Batch processing (e.g., migrate 10 databases in parallel)

### How Parallel Delegation Works

```
┌─────────────────────────────────────────────┐
│  Parent (e.g., Senior Engineer)              │
│  "Analyze all 3 payment services"            │
│  Issues 3 concurrent Agent/Task spawns,      │
│  one DELEGATE per service                    │
└─────────────────────────────────────────────┘
           │
           ├─► Spawn 1: Analyze Stripe   (Engineer) ─┐
           ├─► Spawn 2: Analyze PayPal   (Engineer) ─┼─ concurrent, in flight
           └─► Spawn 3: Analyze Crypto   (Engineer) ─┘
                │         │         │
                ▼         ▼         ▼
           HANDBACK   HANDBACK   HANDBACK   (each returned as its spawn call's result)
                │         │         │
                └────┬────┴────┬────┘
                     ▼          ▼
              Parent aggregates results in-context
              - Quality score (effort-weighted)
              - Tokens used (sum)
              - Cost total (sum)
```

### Fanning Out Sub-Tasks

The spawning agent issues one Agent/Task tool call per sub-task, each with a DELEGATE
block as its prompt, and records each DELEGATE to the queue via `enqueue()` for audit
purposes (see [src/AGENTS.md > Audit-Trail Strategy](../src/AGENTS.md#audit-trail-strategy)):

```yaml
---
handoff_type: DELEGATE
task_id: payment-analysis-stripe-001
agent: engineer
model: claude-haiku-4.5
effort: high
scope: "Analyze Stripe payment service for security risks..."
plan:
  - Review code for injection vulnerabilities
  - Check dependency versions
  - Document findings in security report
context:
  - Parent task: payment-analysis-001
  - Repo: stripe-integration/
  - Focus: Payment processing logic
parent_task_id: payment-analysis-001   # links this sub-task's HANDBACK back to the aggregating parent
ancestry: [senior-engineer]            # required once depth > 0 — see Recursion Limits
---
```

**Fields relevant to fan-out:**
- `parent_task_id` (optional) — the aggregating task this sub-task's result belongs to
- `ancestry` (required at depth > 0) — ordered list of roles from root to the spawning parent, used for cycle detection (see [src/AGENTS.md > Recursion Limits](../src/AGENTS.md#recursion-limits))

### Aggregating Results

When a parent's batch of spawn calls all return, it aggregates their HANDBACKs
in-context and produces its own HANDBACK:

```yaml
---
handoff_type: HANDBACK
task_id: payment-analysis-001
status: success
deliverables:
  - Analysis report: payment-analysis-report.md
children_results:
  payment-analysis-stripe-001:
    status: success
    output: {risks: 2, mitigations: 3}
    quality: 92
  payment-analysis-paypal-001:
    status: success
    output: {risks: 1, mitigations: 2}
    quality: 88
  payment-analysis-crypto-001:
    status: success
    output: {risks: 3, mitigations: 4}
    quality: 85
children_failed: []
result_aggregation_status: all_complete
tokens_in: 2400
tokens_out: 1850
model: claude-sonnet-4.6
effort: high
duration_minutes: 45
---
```

**Fields:**
- `children_results` — dict of results keyed by task_id
- `children_failed` — list of failed child task IDs
- `result_aggregation_status` — `all_complete`, `partial`, or `timed_out`

### Quality Score Aggregation

Child quality scores are **effort-weighted averages**:

| Effort | Weight |
|--------|--------|
| high   | 3×     |
| medium | 2×     |
| low    | 1×     |

**Example:** 3 children with scores `[92, 88, 85]` and efforts `[high, high, medium]`:
```
weighted_quality = (92×3 + 88×3 + 85×2) / (3+3+2) = 618/8 = 77.25
```

### Constraints & Limits

These are the same recursion limits that apply to every direct spawn, not a separate
parallel-delegation rule set — see
[src/AGENTS.md > Recursion Limits](../src/AGENTS.md#recursion-limits) for the
authoritative definitions:

| Constraint | Value |
|-----------|-------|
| Max delegation depth | 3 (root DELEGATE = depth 0) |
| Max fan-out | 5 concurrent sub-agent spawns per parent |
| Ancestry tracking | Required at depth > 0; a target role already in the spawning agent's own ancestry chain is a cycle and the spawn MUST be refused |

Additional independent work beyond 5 concurrent spawns waits for one of the first 5 to
return, or is grouped into a consolidating DELEGATE — it is never spawned as a 6th
concurrent call.

**Note on enforcement:** the limits above are a documented contract every agent's own
definition must observe — enforced today via each agent's `tools:` frontmatter grant at
the leaf tiers (see
[src/AGENTS.md > Tools-Frontmatter Permission Model](../src/AGENTS.md#tools-frontmatter-permission-model)).
No harness currently blocks an over-deep or over-wide spawn mechanically; agents
self-enforce, and a limit violation is reported via HANDBACK `status: blocked` or
`status: escalate`, not silently prevented.

### Failure Modes

**Partial (default):**
- Failed children are recorded in `children_failed`
- Successful children are aggregated normally
- Parent task continues; `result_aggregation_status = partial`

**All-or-nothing:**
- If any child fails, parent fails
- `result_aggregation_status = partial` with `children_failed` populated
- Caller decides whether to fail parent

**Timeout:**
- If a spawn call is taking unacceptably long, the spawning agent may proceed with the
  results it already has rather than wait indefinitely; `result_aggregation_status =
  timed_out`
- Available results included in `children_results`

### Spawning Agent Behavior

The spawning agent (not the Orchestrator on its behalf — this is decentralized):

1. **Issues one concurrent spawn per sub-task**, each carrying its own DELEGATE as prompt
2. **Awaits its batch of spawn calls** — a spawn call does not return control until the
   sub-agent's HANDBACK is available; "waiting" is simply the tool calls being in flight
3. **Aggregates results** as they return — quality (weighted), tokens (sum), costs (sum)
4. **Writes its own HANDBACK** with `children_results` populated
5. **Records the HANDBACK to the queue** via `enqueue()` for audit purposes once aggregation is complete

### Cost Impact

Parallel delegation **reduces wall-clock time** but may increase token cost:

**Sequential (3 tasks, 1 hour each):**
- Wall-clock: 3 hours
- Tokens: 3 × 2000 = 6000
- Cost: $0.18

**Parallel (3 tasks, 1 hour each, concurrent spawns):**
- Wall-clock: 1 hour
- Tokens: 3 × 2000 = 6000 (same)
- Cost: $0.18 (same)
- **Benefit:** 2 hours saved (66% faster)

**Parallel with different models:**
- Parent (Sonnet, high): 2500 tokens = $0.075
- 3 children (Haiku, high): 3 × 2000 = 6000 tokens = $0.09
- Total: 8500 tokens = $0.165
- **Benefit:** Cheaper than all-Sonnet, 66% faster

### Best Practices

✅ **DO:**
- Use for naturally decomposable work
- Keep concurrent spawns within the fan-out limit of 5; group the rest into a consolidating DELEGATE
- Monitor token consumption (parallel = more concurrent usage)
- Use effort levels to weight results appropriately
- Set `ancestry` on every DELEGATE issued at depth > 0

❌ **DON'T:**
- Create circular dependencies — refuse a spawn whose target role already appears in your own ancestry chain
- Exceed the depth-3 or fan-out-5 limits — these are self-enforced (see Constraints & Limits above), not blocked by any harness
- Use for sequential work (defeats the purpose)
- Ignore failed children (check `children_failed` in HANDBACK)

### Troubleshooting Parallel Delegation

**Q: A concurrent spawn is taking much longer than the others**
A: The spawning agent's context is blocked on that tool call returning — there is no separate process to check logs on. If it's unacceptably slow, treat it as a timeout: proceed with the results already in hand, mark `result_aggregation_status = timed_out`, and record the incomplete child in `children_failed`.

**Q: Aggregation quality score seems wrong**
A: Verify effort levels in child HANDBACKs. Quality is effort-weighted; high-effort children have 3× weight. Use formula: `Σ(quality × weight) / Σ(weight)`.

**Q: Can I create sub-tasks of sub-tasks?**
A: Yes, up to the depth-3 limit (root DELEGATE = depth 0; each spawn hop increments depth by 1). Ancestry tracking prevents cycles.

**Q: What if 2 of 3 children fail?**
A: `result_aggregation_status = partial`, `children_failed = [task_id_1, task_id_2]`. Parent continues with 1 successful result. Quality score reflects only successful children.

### Real-World Example: Security Audit (Parallel)

**Task:** Audit security in 4 microservices.

**Sequential approach (old):**
- Orchestrator → Security Engineer (4 hours, $0.30)
- Wall-clock: 4 hours

**Parallel approach (direct spawn fan-out):**
1. Orchestrator spawns Senior Engineer directly (30 min: plan + prepare 4 sub-task DELEGATEs)
2. Senior Engineer fans out 4 concurrent Security Engineer spawns, one per service — within the fan-out-5 limit
3. All 4 run concurrently (1 hour wall-clock)
4. Senior Engineer aggregates results in-context as each spawn call returns
5. Total: 1.5 hours wall-clock, $0.36 cost
- **Benefit:** 2.5 hours saved (62% faster)

---

**Q: Should I talk directly to Guardian/Architect/Engineer, or always go through Dispatch?**  
A: Always start with Dispatch (Haiku, low effort). Dispatch routes you to the right specialist, announces personality, and coordinates handoffs. This ensures consistent cost tracking and optimal routing.

**Q: What if I know I need Guardian (security analysis)?**  
A: Tell Dispatch: "Route to Guardian for security analysis of X." Dispatch will escalate and announce the handoff.

**Q: Can Engineer implement without a plan from Architect?**  
A: Not recommended. If there's uncertainty, Dispatch routes to Architect first for a plan, then to Engineer for implementation. This avoids wasted effort and re-work.

**Q: What if Engineer gets stuck?**  
A: Engineer escalates to Architect (via Dispatch) with context: current state, attempted approaches, specific error. Architect diagnoses and refines the plan.

**Q: Can multiple agents work in parallel?**  
A: Yes, if they're in different repos or files. Dispatch coordinates; assess milestones periodically. Avoid same file (merge conflicts, contention). See [PARALLEL-DELEGATION-GUIDE.md](PARALLEL-DELEGATION-GUIDE.md) for detailed parallel delegation patterns.

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

---

## Protocol Compliance Expectations

> **Mandatory for all roles.** Full details in [ORCHESTRATION-PROTOCOL.md](ORCHESTRATION-PROTOCOL.md).

Every agent must follow the DELEGATE/HANDBACK protocol. Violations are blocked by the
pre-commit hook or caught by the post-execution validator. Non-compliance costs tokens —
a bad DELEGATE forces re-work; a bad HANDBACK triggers retry or escalation.

### Orchestrator

**DELEGATE (emit):**
- Run Groups A/B/C pre-flight checks before emitting any DELEGATE
- Verify `task_id` is unique and correctly formatted (`YYYY-MM-DD-kebab-case`)
- Verify `scope` ≥15 words, `success_criteria` are testable, `plan` is numbered
- Route security tasks to `security_engineer`, architecture to `principal_engineer`
- Track `retry_count` per task; escalate to `principal_engineer` on >2 retries

**HANDBACK (process):**
- Accept only validator-computed quality scores (not agent self-scores) for routing decisions
- Score 90–100: move to done/ immediately
- Score 80–89: move to done/ with notes
- Score 70–79: route to Lead Engineer for manual review
- Score 60–69: issue re-work DELEGATE (max 2 retries) with `retry_context` block
- Score <60: escalate to Principal Engineer with full retry history

**Metrics:** Emit `artifacts/metrics/YYYY-MM-DD-{task_id}-metrics.yaml` per task.

### Engineer

**DELEGATE (receive):**
- If DELEGATE is incomplete or unclear, report `status: blocked` immediately — do not guess
- Confirm plan steps are concrete before starting execution
- Every plan step should map to a deliverable in the HANDBACK

**HANDBACK (emit):**
- Include all 12 required fields; do not omit `tests`, `tokens_in/out`, or `duration_minutes`
- Report actual test pass/fail counts and coverage percentage
- If scope creep occurred, document it in `scope_deviations`; stay within DELEGATE scope otherwise
- Self-report `quality_score` honestly; validator score is authoritative for routing

**Escalation:** Set `status: blocked` if stuck; Orchestrator escalates to Senior Engineer.

### Senior Engineer

**DELEGATE (receive):**
- Accept complex DELEGATEs without fully pre-written plans
- Produce a detailed numbered `plan` as first deliverable (for Engineer re-delegation if needed)
- Apply quality baseline: ≥85% test coverage, zero production hazards

**HANDBACK (emit):**
- Include `qe_feedback` block where requested by Orchestrator
- Document architectural decisions in `notes` so Lead Engineer can review them
- Flag potential production hazards explicitly in HANDBACK notes

**Mentoring:** When reviewing Engineer HANDBACKs, provide specific actionable feedback.

**SDLC Gate Maintenance:** Senior Engineer is responsible for:
- Maintaining Git hooks in `.githooks/` directory
- Updating pre-commit hooks when validation requirements change
- Updating pre-push hooks when quality gates change
- Documenting hook behavior in `.githooks/README.md`
- Monitoring hook performance (target: pre-commit < 3s, pre-push < 10s excluding tests)
- Addressing false positives or overly-strict checks that slow down development
- Escalating hook breakage to Principal Engineer if fixes are needed

**Hook Installation:** Senior Engineer ensures:
- `make setup` target automatically installs hooks for all developers
- Hooks are compatible with macOS and Linux
- Emergency override mechanism (`GIT_SKIP_HOOKS=1`) is documented and working
- Existing test suite passes with hooks enabled (no regressions)

### Lead Engineer

**Gray-Zone Review (70–79 scores):**
- Review HANDBACK notes, deliverables, and test results within 24h of routing
- Choose one of: Accept / Conditional Accept / Rework
- Document decision in `qe_feedback.lead_review` block
- Conditional Accept: create follow-up P2 task for gaps; do not block merge

**Code Review:**
- Use 8-point checklist in QUALITY.md for structured review
- Approve/reject with specific line-level reasoning (not just "looks good")

**Protocol oversight:** Interpret protocol questions from team members; escalate protocol ambiguity to Principal Engineer.

### Quality Engineer

**Standard HANDBACK (emit):**
- Always include `qe_feedback` block with `model_assessment`, `confidence`, and coverage assessment
- Record `qe_model_assessment` as: `haiku_suitable | sonnet_suitable | opus_required | over_engineered`
- Flag cost anomalies in `qe_feedback` (cost overrun >50%, unexpected escalations)

**Metrics:** Validate that 35-field canonical metrics record is complete and accurate.

**Trends:** Report systemic quality issues (recurring failures, declining coverage) to Principal Engineer.

### Principal Engineer

**Escalation handling:**
- Review all escalated tasks within 48h
- For retry-overflow escalations: decide between (a) redesign task, (b) switch agent/model, (c) mark blocked
- For critical findings: immediate review; security findings route to Security Engineer

**Protocol oversight:**
- Monthly review of protocol effectiveness with metric data
- Approve breaking protocol changes with migration plan
- Sign off on new agent roles or routing rule changes

### Security Engineer

**Scope:** Only invoked for security-scoped tasks. All other routes blocked.

**HANDBACK:** Include threat model summary, CVE references where relevant, and explicit `no_secrets_found: true/false` assertion.

### Model Engineer

**Analysis cadence:** After every Quality Engineer HANDBACK, analyze `qe_model_assessment` and `flag_for_model_engineer` signals.

**Recommendations:** Output ranked recommendations (rank_1 to rank_3) for model/effort combinations on similar future tasks.

**HANDBACK:** Include `efficiency_score` trends and cost optimization rationale in notes.

---

## Git Hook Workflow

### Pre-Commit Hook Integration

The pre-commit hook (`.githooks/pre-commit`) enforces SPEC.md compliance and quality gates at commit time. It runs as a standalone bash script (not via the DELEGATE/HANDBACK queue — hooks must be synchronous and fast).

**Flow:**
1. Developer runs `git commit`
2. Pre-commit hook validates staged files (SPEC compliance, secrets, YAML validity)
3. Hook exits 0 (allow) or 1 (block) based on validation results
4. Commit proceeds or is blocked with error message

### What the Pre-Commit Hook Checks

| Check | Severity |
|-------|----------|
| No `.py`/`.sh` in `orchestration/scripts/` | ❌ BLOCK |
| No `.cron` in `orchestration/config/` | ❌ BLOCK |
| No `subprocess`/`os.system`/`exec` in agent code | ❌ BLOCK |
| Secret detection (API keys, passwords, tokens) | ❌ BLOCK |
| YAML/JSON validity | ❌ BLOCK |
| No bypass markers in committed code | ⚠️ WARN |
| DELEGATE/HANDBACK field validation (if YAML files) | ❌ BLOCK |

### Emergency Bypass

```bash
BYPASS_HOOK_VALIDATION=true git commit -m "emergency: reason"  # bypass DELEGATE/HANDBACK validation only
SKIP_HOOKS=1 git commit -m "emergency: reason"                 # bypass all pre-commit checks
```

### Installation

```bash
make install          # installs hooks + renders agents/skills
# or manually:
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit .githooks/commit-msg .githooks/pre-push
```

### Reference

- **[docs/SDLC-HOOKS.md](SDLC-HOOKS.md)** — Complete hook reference
- **[docs/BYPASS-PROCEDURES.md](BYPASS-PROCEDURES.md)** — Emergency bypass procedures

---

## Protocol Reference

| Resource | Purpose |
|----------|---------|
| [ORCHESTRATION-PROTOCOL.md](ORCHESTRATION-PROTOCOL.md) | Master protocol document (source of truth) |
| [AGENT-ONBOARDING.md](AGENT-ONBOARDING.md) | Onboarding checklist for new agents |
| [PROTOCOL.md — Appendix G](PROTOCOL.md) | One-page quick reference cheat sheet |
| [PROTOCOL-IMPLEMENTATION-STATUS.md](PROTOCOL-IMPLEMENTATION-STATUS.md) | Implementation status and metrics |
| [DELEGATE-HANDBACK-QUALITY-GATES.md](DELEGATE-HANDBACK-QUALITY-GATES.md) | Quality gates detail |
| [delegate-schema.yaml](delegate-schema.yaml) | Machine-readable DELEGATE schema |
| [handback-schema.yaml](handback-schema.yaml) | Machine-readable HANDBACK schema |

---

## Workflow Enforcement Points

The DELEGATE/HANDBACK protocol is enforced at three critical gates via git hooks:

### Pre-Commit Hook (SPEC & Quality)

**What agents must ensure before committing:**
- ✅ SPEC.md compliance (no external scripts, cron files, process execution)
- ✅ No secrets in code (API keys, passwords, tokens)
- ✅ Valid YAML/JSON syntax
- ✅ No bypass markers in code

**What happens on violation:**
- ❌ Commit is blocked
- Error message shows what failed
- Agent must fix and re-commit

**Bypass (emergency only):**
```bash
BYPASS_HOOK_VALIDATION=true git commit -m "emergency: reason"
```

### Commit-Msg Hook (Protocol Compliance)

**What agents must ensure in commit message:**
- ✅ Message length ≥10 characters
- ✅ Conventional commit format (optional but encouraged)
- ✅ Task ID format: YYYY-MM-DD-kebab-case (optional but encouraged)
- ✅ If DELEGATE/HANDBACK present: all required fields present
- ✅ If SKIP_HOOKS mentioned: reason documented

**What happens on violation:**
- ❌ Commit is blocked
- Error message shows what failed
- Agent must fix message and re-commit

**Bypass (emergency only):**
```bash
SKIP_COMMIT_MSG_HOOK=true git commit -m "message"
```

### Pre-Push Hook (Final Quality Gate)

**What agents must ensure before pushing:**
- ✅ Agent YAML frontmatter valid (src/agents/*.md)
- ✅ Workflow files valid (.github/workflows/*.yml)
- ✅ Documentation files present (SPEC.md, AGENTS.md, README.md)
- ✅ DELEGATE/HANDBACK files valid (artifacts/)
- ✅ Test suite passing (pytest if available)
- ✅ SPEC compliance verified

**What happens on violation:**
- ❌ Push is blocked (for errors)
- ⚠️ Warning shown (for test failures, protected branch)
- Agent must fix and re-push

**Bypass (emergency only):**
```bash
SKIP_HOOKS=1 git push
```

### Integration with DELEGATE/HANDBACK Protocol

The hooks enforce protocol compliance at commit time:

```
DELEGATE Created
    ↓
[pre-commit hook]
├─ Validate YAML syntax
├─ Validate required fields: task_id, role, scope, plan, success_criteria
├─ Validate task_id format: YYYY-MM-DD-kebab-case
└─ BLOCK if invalid

[commit-msg hook]
├─ Validate DELEGATE block if present in message
├─ Validate all required fields present
└─ BLOCK if invalid

[pre-push hook]
├─ Validate all DELEGATE files in artifacts/
├─ Validate YAML syntax
├─ Validate required fields
└─ BLOCK if invalid

DELEGATE Committed & Pushed
    ↓
Agent Executes
    ↓
HANDBACK Created
    ↓
[pre-commit hook]
├─ Validate YAML syntax
├─ Validate required fields: task_id, status, deliverables, tests, quality_score
├─ Validate status value: complete|failed|partial|blocked
└─ BLOCK if invalid

[commit-msg hook]
├─ Validate HANDBACK block if present in message
├─ Validate all required fields present
└─ BLOCK if invalid

[pre-push hook]
├─ Validate all HANDBACK files in artifacts/
├─ Validate YAML syntax
├─ Validate required fields
└─ BLOCK if invalid

HANDBACK Committed & Pushed
    ↓
Quality Engineer Reviews
    ↓
Metrics Recorded
```

### Role Responsibilities for Enforcement

**Orchestrator:**
- Creates DELEGATE with all required fields
- Ensures YAML syntax is valid
- Ensures task_id format is correct
- Ensures scope, plan, success_criteria are clear

**Agent (Engineer, Senior Engineer, etc.):**
- Reads and validates DELEGATE before executing
- Creates HANDBACK with all required fields
- Ensures YAML syntax is valid
- Ensures status value is valid (complete|failed|partial|blocked)
- Ensures quality_score is honest (0-100)
- Ensures deliverables match scope

**Quality Engineer:**
- Validates HANDBACK structure
- Verifies deliverables match scope
- Checks test results
- Assesses code quality
- Scores using formula
- Provides model assessment feedback

**All Contributors:**
- Run hooks before committing
- Document bypass reason if emergency bypass needed
- Create follow-up task to fix root cause
- Re-enable hooks after emergency bypass

### Full Documentation

For comprehensive enforcement documentation, see:
- **[docs/SDLC-HOOKS.md](../SDLC-HOOKS.md)** — Complete hook reference
- **[docs/WORKFLOW.md](../WORKFLOW.md)** — Full SDLC lifecycle with 7 gates
- **[docs/TROUBLESHOOTING.md](../TROUBLESHOOTING.md)** — Troubleshooting guide
- **[docs/BYPASS-PROCEDURES.md](../BYPASS-PROCEDURES.md)** — Emergency bypass procedures

---

## Update Log

- **2026-04-19:** Initial AGENTS.md created (vendor-neutral) during {service-name}/{example-service}/{example-service} security hardening cycle.
- **2026-04-24:** Added Model Engineer role (Phase 2C) with autonomous optimization feedback loop. QE now provides model_assessment feedback. Orchestrator applies Model Engineer recommendations for continuous cost/quality improvement.
- **2026-05-09:** Added Protocol Compliance Expectations section (Week 4). Per-role DELEGATE/HANDBACK/Metrics/Escalation protocol responsibilities defined. Cross-references to ORCHESTRATION-PROTOCOL.md added.
- **2026-05-16:** Added Git Hook Workflow section documenting pre-commit hook checks, bypass procedures, and installation. Added Workflow Enforcement Points section covering all three git hooks and their integration with the DELEGATE/HANDBACK protocol. Cross-references to docs/SDLC-HOOKS.md, docs/WORKFLOW.md, docs/TROUBLESHOOTING.md, and docs/BYPASS-PROCEDURES.md.
- **2026-05-16:** Added comprehensive Parallel Delegation section (Phase 2 feature). Documents parallel sub-task creation, DELEGATE/HANDBACK fields for parent-child relationships, quality score aggregation (effort-weighted), constraints (max 5 tiers, 10 children/parent), failure modes, Orchestrator behavior, cost impact analysis, best practices, troubleshooting, and real-world example. Cross-references to PARALLEL-DELEGATION-GUIDE.md.
- **2026-08-09:** Converted the execution-model narrative from filesystem-queue polling to the Direct Sub-Agent Spawn Execution Model — the Orchestrator (and any agent with `spawn_subagent` in its `tools:` frontmatter) now spawns sub-agents directly and reads the HANDBACK back as the tool result, rather than polling `artifacts/queue/incoming/` every 30-60 seconds. The queue is retained as an audit trail only (see [src/AGENTS.md > Direct Sub-Agent Spawn Execution Model](../src/AGENTS.md#direct-sub-agent-spawn-execution-model)). Rewrote the Parallel Delegation section as concurrent direct-spawn fan-out and reconciled its constraints (depth 3, fan-out 5, ancestry tracking) with the canonical Recursion Limits in src/AGENTS.md.
- **Recommendation:** Review this guide quarterly and update tier assignments based on new model releases and Model Engineer recommendation trends. Parallel delegation enables 60-70% Orchestrator load reduction; monitor adoption and adjust constraints based on real-world usage patterns.
