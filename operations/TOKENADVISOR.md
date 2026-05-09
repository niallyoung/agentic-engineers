# TokenAdvisor — Usage Analytics & Optimization

Read-only feedback loop for continuous cost & token usage optimization. Analyzes metrics collected from METRICS.md to identify efficiency opportunities.

---

## What TokenAdvisor Does

TokenAdvisor is a specialized agent (Orchestrator role, claude-haiku-4-5, low effort) that:

1. **Analyzes historical metrics** — Reads `~/.claude/metrics/**/*.json` and `*.jsonl` files
2. **Produces usage summaries** — By model, by role, by task type, by repo
3. **Identifies inefficiencies** — Outliers, cost overruns, mis-routed tasks
4. **Recommends adjustments** — Model tier changes, effort level tweaks, delegation patterns
5. **Tracks trends** — Cost per task over time; quality correlation with model choice

TokenAdvisor **never writes** to service repos, never commits code, never modifies any repo. It only produces text analysis and voice notifications.

---

## TokenAdvisor Invocation

Orchestrator invokes TokenAdvisor:
- **Session start** (optional) — "TokenAdvisor: summarize yesterday's metrics"
- **Session end** (recommended) — "TokenAdvisor: summarize this session"
- **On-demand** — "TokenAdvisor, how are we doing?" (anytime during a session)

---

## TokenAdvisor Output Format

### Session Summary (invoked at session end)

Text report + optional voice notify. Example:

```
=== TokenAdvisor Session Summary ===

Session: 2026-04-24-001 (2h 22m)
Total tokens: 24,850
Cost breakdown: $0.32

By role:
  Orchestrator: 8,200 (33%) ✓ target 70% — you're routing too much directly
  Engineer:     12,100 (49%) ✓ target 15% — good use; well-planned tasks
  Senior Engineer: 3,100 (12%) ✓ target 8% — slightly high; consider simpler tasks?
  Lead Engineer: 1,450 (6%) ✓ target 10% — low; quality gate opportunity

By task type:
  Bug fix: 15,600 (63%)
  Code review: 5,300 (21%)
  Planning: 3,950 (16%)

Tasks completed: 3 commits, 1 PR merged

Outlier flag: 2026-04-24-refactor-auth-flow consumed 6,200 tokens (92nd percentile).
  Reason: Principal Engineer + no pre-written plan. Next time: pre-plan with Opus, hand to Senior.

Blockers: 1 escalation (Engineer → Senior). Cost: +2,100 tokens. Preventable with detailed plan.

Recommendation: Route more small tasks through Engineer tier (well-planned, ~2K tokens each).
Next step: Check Principal Engineer's calendar availability for pre-planning expensive tasks.
```

### Daily Summary (invoked end of work day)

Across all sessions in the calendar day:

```
=== TokenAdvisor Daily Summary (2026-04-24) ===

Sessions: 3 (2.5h, 2h, 1.5h = 6h total)
Total tokens: 87,500
Cost: $1.08

By role (actual vs. target):
  Orchestrator: 58,100 (67%) [target 70%] ✓ good
  Engineer: 18,600 (21%) [target 15%] ⚠ 6% over
  Senior Engineer: 7,200 (8%) [target 8%] ✓ on target
  Lead Engineer: 2,800 (3%) [target 10%] ⚠ 7% under (quality gate opportunity)
  Principal Engineer: 600 (1%) [target 2%] ✓ low (fewer architectural tasks today)
  Security Engineer: 0 [target 3%] ✓ good (no security audits today)

Tasks completed: 5 commits, 3 repos

Efficiency metrics:
  Avg tokens per Engineer task: 2,100 (good; well-planned)
  Avg tokens per Senior Engineer task: 3,600 (acceptable; complex tasks)
  Escalations today: 2 (1.6% of tasks) ✓ low

Trend (vs. yesterday 2026-04-23):
  Cost: +$0.08 (8% higher) — more complex tasks today
  Engineer utilization: ↑ 15% — better planning paying off
  Re-work rate: 0% ↓ — QUALITY.md checklist preventing failed tasks

Recommendation: Lead Engineer is underutilized (3% vs. 10% target).
  Action: Route more code reviews to Lead Engineer tier.
  Expected impact: ~5K tokens saved, higher quality gate.
```

---

## TokenAdvisor Analysis Categories

### 1. Cost Split by Role

**Purpose:** Verify adherence to AGENTS.md cost targets (70% Orchestrator, 15% Engineer, etc.)

**Output format:**
```
Orchestrator: 33,600 (60%) [target 70%] ⚠ 10% under
Engineer:     25,200 (45%) [target 15%] ⚠ 30% over
...
```

**Action trigger:** If any role drifts >10% from target, recommend the reason and fix.

### 2. Top 3 Most Expensive Task Types

**Purpose:** Identify which work categories burn the most tokens.

**Output format:**
```
1. Security audit (18,500 tokens, 21% of total)
   → Typically Security Engineer; cost is high but justified. No action.

2. Refactor (12,300 tokens, 14% of total)
   → Should be Principal Engineer, but using Senior (3x cost tier). 
     Action: Escalate large refactors to Principal for planning.

3. Bug triage (8,200 tokens, 9% of total)
   → Efficient; well-planned. No action.
```

### 3. Outlier Flagging

**Purpose:** Identify tasks that consumed abnormally high tokens.

**Rule:** Flag tasks in the 90th percentile by tokens_in + tokens_out.

**Output format:**
```
Outlier: 2026-04-24-refactor-api-gateway (8,100 tokens)
  Role: Senior Engineer (expected: ~3,600 tokens)
  Reason: No pre-written plan; Engineer spent 45 min exploring design space
  Action: For next refactor, route to Principal Engineer (cheaper if pre-planned)
```

### 4. Blocker Escalation Rate

**Purpose:** Track how often tasks are escalated due to complexity/blocker.

**Output format:**
```
Escalations: 2/50 tasks (4%)
  Target: <2%
  Status: ✓ on target

Details:
  1. 2026-04-24-fix-timeout (Engineer → Senior): missing root cause analysis
  2. 2026-04-24-ci-failure (Senior → Principal): design decision needed
```

**Action trigger:** If rate >2%, root cause: are tasks being delegated without adequate planning?

### 5. Quality Correlation

**Purpose:** Track relationship between model choice and quality outcomes.

**Output format:**
```
Test pass rate by role:
  Orchestrator: 100% (trivial tasks, no test failures)
  Engineer: 98% (1 task failed tests, rework required)
  Senior Engineer: 100% (complex, careful work)
  Lead Engineer: 100% (quality-focused role)

Rework rate:
  Today: 0/50 tasks (0%) ✓ excellent
  Yesterday: 2/45 tasks (4.4%) ⚠ slightly high
  Trend: Improving (QUALITY.md checklist helps)
```

---

## TokenAdvisor Data Sources

Reads from: `~/.claude/metrics/`

- Per-task JSON: `task_id`, `model`, `effort`, `tokens_in`, `tokens_out`, `role`, `test_pass`, `escalations`
- Session event log: `session_start`, `handoff`, `handback`, `session_end`, `voice_notify` events

Does not require:
- Access to service repos
- Git history or commits
- Claude API response headers (tokens_in/out are estimates in JSON)

---

## TokenAdvisor Recommendations (Examples)

### Example 1: Engineer Over-Used

```
Observation: Engineer tasks are 49% of token spend (target: 15%)
Root cause: Tasks often lack pre-written plans → Engineer spends tokens re-planning
Recommendation: Route task planning to Senior Engineer tier (cheaper to plan once)
Expected impact: -8K tokens/session, same quality outcomes
```

### Example 2: Lead Engineer Under-Utilized

```
Observation: Lead Engineer at 3% of spend (target: 10%)
Reason: Code reviews being routed to Principal Engineer (7.5x cost)
Recommendation: Delegate code reviews to Lead Engineer (3x cost)
Expected impact: -5K tokens/session
```

### Example 3: Principal Engineer Optimized

```
Observation: Principal Engineer at 2% of spend (target: 2%) ✓ on target
Note: All tasks are multi-service architecture + planning.
Status: ✓ No action; this is correct usage
```

---

## Phase 2 (Future) — Not Implemented Yet

TokenAdvisor Phase 2 will add:
- **A/B model comparison** — Run same task on two models, compare quality + cost
- **Automated tier adjustment** — Detect when a cheaper model can do what an expensive model used to do
- **Model availability detection** — Check what models are available, detect new releases
- **Cost per quality metric** — Correlate token spend with test coverage, code review comments, etc.
- **Scheduling recommendations** — Suggest optimal task ordering to batch related work

For now, TokenAdvisor Phase 1 is read-only analysis + recommendations. Phase 2 will add automation.

---

## Running TokenAdvisor

**Usage:**
```
Orchestrator → TokenAdvisor (invoke)
```

**Example voice notify:**
```
[[volm 0.7]] TokenAdvisor: session tokens 24,850. Engineer 49% of spend, 
target 15%. Re-route more tasks to Engineer tier for savings. Two escalations today 
— consider detailed plans.
```

---

## TokenAdvisor TDD Validation

Write 5 example task JSON records representing:
1. Efficient Engineer task (2K tokens, all tests pass, no escalations)
2. Inefficient refactor (8K tokens, Senior Engineer, no plan provided)
3. Security audit (15K tokens, Security Engineer, expected high cost)
4. Code review (1.5K tokens, Lead Engineer, appropriate tier)
5. Blocked task (6K tokens, escalated twice)

TokenAdvisor Phase 1 is correct if it can:
- Calculate per-role token spend from the 5 tasks
- Identify the refactor as an outlier
- Flag the blocked task as 2 escalations
- Recommend downshifting the refactor to Principal for pre-planning
- Produce the 4 standard analyses (cost split, top 3 types, outliers, escalations)

All without reading any source code or accessing service repos.
