# Dark Factory Metrics & Monitoring

Track agent performance, cost, and quality at multiple timescales to continuously optimize the multi-agent system.

---

## Minimal Viable Schema (Start Here)

To begin collecting metrics immediately, write JSON task records and session logs to disk using this schema. No code needed — any agent, script, or human can start writing records today.

### Directory Structure

```
~/.claude/metrics/
  YYYY-MM-DD/
    <task_id>.json           # Per-task record (see below)
    session-<session_id>.jsonl  # Append-only session event log
```

Example paths:
```
~/.claude/metrics/2026-04-24/2026-04-24-fix-auth-timeout.json
~/.claude/metrics/2026-04-24/session-2026-04-24-001.jsonl
```

### Per-Task Record Format

File: `~/.claude/metrics/YYYY-MM-DD/<task_id>.json`

One JSON object per file (task completion snapshot):

```json
{
  "schema_version": "1.0",
  "task_id": "2026-04-24-fix-auth-timeout",
  "session_id": "2026-04-24-001",
  "role": "Engineer",
  "model": "claude-haiku-4-5",
  "effort": "high",
  "task_type": "bug_fix",
  "repo": "{example-service}",
  "delegated_by": "Orchestrator",
  "plan_provided": true,
  "status": "complete",
  "duration_minutes": 18,
  "tokens_in": 1200,
  "tokens_out": 820,
  "tests_pass": true,
  "test_count": 48,
  "test_coverage": "89%",
  "escalations": 0,
  "deliverables": [
    "lambda/api/main.go (lines 92-95 modified)",
    "lambda/api/main_test.go (TestTokenExpiryGracePeriod added)"
  ],
  "notes": "Token expiry grace period fixed clock skew issue on mobile devices."
}
```

**Field definitions:**
- `schema_version` — always `"1.0"` for MVP; increment if format changes
- `task_id` — unique identifier (YYYY-MM-DD-slug format, from HANDOFF.md DELEGATE block)
- `session_id` — session timestamp (YYYY-MM-DD-NNN, e.g. `2026-04-24-001` for first session that day)
- `role` — exact role name from AGENTS.md (Engineer, Senior Engineer, Lead Engineer, etc.)
- `model` — exact Claude model ID used (e.g. `claude-haiku-4-5`)
- `effort` — actual effort level used (low, medium, high, max)
- `task_type` — category (bug_fix, feature, security_audit, refactor, planning, code_review, etc.)
- `repo` — single repo modified (e.g. `{example-service}`); if multiple, use comma-separated list
- `delegated_by` — role that delegated this task (usually Orchestrator)
- `plan_provided` — boolean; was a pre-written plan provided in DELEGATE block?
- `status` — complete | partial | blocked
- `duration_minutes` — wall-clock minutes from task start to completion (estimate is fine)
- `tokens_in` — approximate tokens consumed reading context (estimate: sum of DELEGATE block + code files + existing context)
- `tokens_out` — approximate tokens produced in response (estimate: length of final response / 4)
- `tests_pass` — boolean; did tests pass?
- `test_count` — total number of tests run (e.g. `make verify` result)
- `test_coverage` — test coverage % if available (e.g. `"89%"`)
- `escalations` — count of times escalated to different role/model
- `deliverables` — list of changed files (optional file:line notation)
- `notes` — optional; any notes for later review

### Session Event Log Format

File: `~/.claude/metrics/YYYY-MM-DD/session-<session_id>.jsonl`

One JSON object per line (append-only log). Track events as they occur:

```jsonl
{"event": "session_start", "session_id": "2026-04-24-001", "timestamp": "2026-04-24T09:15:00Z", "initial_context_tokens": 15000}
{"event": "delegate", "task_id": "2026-04-24-fix-auth-timeout", "from_role": "Orchestrator", "to_role": "Engineer", "timestamp": "2026-04-24T09:17:00Z"}
{"event": "handback", "task_id": "2026-04-24-fix-auth-timeout", "status": "complete", "timestamp": "2026-04-24T09:35:00Z"}
{"event": "session_end", "session_id": "2026-04-24-001", "timestamp": "2026-04-24T11:42:00Z", "total_tokens": 24500, "task_count": 3}
```

**Event types:**
- `session_start` — session begins
- `delegate` — work handed off to a specialist
- `handback` — specialist returned work
- `escalation` — task escalated to different role/model
- `voice_notify` — notification sent to user
- `session_end` — session concludes

**Field definitions:**
- `event` — event type (literal string)
- `timestamp` — ISO 8601 UTC timestamp
- `session_id`, `task_id`, `role`, etc. — as defined in per-task record above
- All events include a `timestamp` field

### Validation (TDD for this schema)

Write three example per-task JSON records by hand:
1. A completed Engineer task (18 min, no escalations, all tests pass)
2. A blocked task escalated to Senior Engineer (identified blocker, returned to Orchestrator)
3. A Security Engineer analysis (no code changes, 1hr analysis, test_count=0)

The schema is correct if `jq` can query them without error:

```bash
# Extract tokens_in from all tasks
jq '.tokens_in' ~/.claude/metrics/YYYY-MM-DD/*.json

# Count tasks by role
jq '.role' ~/.claude/metrics/YYYY-MM-DD/*.json | sort | uniq -c

# Find all blocked tasks
jq 'select(.status == "blocked")' ~/.claude/metrics/YYYY-MM-DD/*.json
```

---

## Measurement Timescales

### Per-Session (Current Work Window)

**Scope:** Single continuous work session (30 min — 4 hours)

**Metrics:**
- `total_tokens_spent` — Sum of all agent calls in session
- `breakdown_by_model` — Dispatch: X%, Engineer: Y%, Architect: Z%, etc.
- `handoffs_count` — Number of role handoffs (Orchestrator → Security Engineer → Engineer, etc.)
- `voice_notify_count` — Notifications sent (should be ~5–10 for 2-hour session)
- `avg_task_time_per_agent` — Time from "escalate" to "complete" per specialist
- `tasks_completed` — How many work items (commits, TODOs, fixes) completed
- `blocker_escalations` — How many times an agent got stuck and escalated

**Action:** Logged automatically by harness; summary printed at session end.  
**Goal:** Visibility into "how was today's session?" before moving to the next day.

**Example Output:**
```
=== Session Summary (2h 15m) ===
Total tokens: 24,500
Breakdown: Dispatch 60%, Engineer 25%, Architect 15%
Handoffs: 4 (Dispatch→Architect→Engineer→Dispatch)
Voice notifies: 8
Avg task time: 25 min (Engineer), 15 min (Architect)
Completed: 3 commits, 5/7 security fixes
Blockers: 1 escalation (Engineer→Architect)
```

---

### Daily (End of Work Day)

**Scope:** All work sessions in a calendar day

**Metrics:**
- `daily_tokens_spent` — Cumulative token usage (all sessions)
- `model_distribution` — % spent on Orchestrator, Engineer, Senior, Lead, Principal, Security
- `tasks_completed` — Commits, PRs merged, repos deployed
- `ci_pass_rate` — % of CI runs that passed (vs. failed, re-ran)
- `handoff_efficiency` — Avg time from "problem identified" to "fix merged"
- `personality_usage` — Which personality was most active? (indicates task type distribution)
- `escalations` — How many times did agents get stuck and escalate?
- `cost_target_tracking` — Are we hitting 70/15/10/3/2 cost split?

**Action:** End-of-day summary email / log file.  
**Goal:** "What did we accomplish today? Is cost aligned with targets?"

**Example Output:**
```
=== Daily Summary (2026-04-20) ===
Total tokens: 87,600 (4 sessions)
Model breakdown:
  - Dispatch: 61% (target: 70%) ⚠️ under-utilized
  - Engineer: 24% (target: 15%) ⚠️ over-utilized
  - Architect: 12% (target: 10%) ✓
  - Sage: 2% (target: 3%) ✓
  - Security Engineer: 2% (target: 3%)

Tasks: 8 commits, 2 repos deployed, 0 failed CI
Handoff efficiency: avg 22 min (identify→merge)
Escalations: 2 (both resolved)
Personalities: Dispatch (most), Engineer (most), Architect (most)
```

---

### Weekly (Week-in-Review)

**Scope:** All work in a calendar week (Mon–Fri, or 5 work days)

**Metrics:**
- `weekly_tokens_spent` — Total spend for the week
- `cost_per_task` — Avg tokens per completed task (commit, deployment, fix)
- `task_type_distribution` — % security work, feature work, bug fixes, chores
- `quality_metrics` — % of tasks passing first-time CI, test coverage changes, code review feedback
- `personality_effectiveness` — Which personality solved the most complex tasks? Highest quality?
- `skill_usage` — Which skills ({example-service}, {example-service}, etc.) were deployed? Effectiveness?
- `blocker_analysis` — Common escalation patterns (e.g., "Engineer stuck on type checking")
- `model_efficiency` — Cost per completed task by role (Orchestrator cheapest, Security Engineer most expensive)

**Action:** Weekly retro/standup; log to shared dashboard.  
**Goal:** Spot trends (are Engineer tasks getting too complex? Is Guardian under-utilized?).

**Example Output:**
```
=== Weekly Summary (Week of 2026-04-14) ===
Total tokens: 312,000 (20 sessions)
Cost per task: 15,600 tokens avg
  - Security audit: 87,000 (5 tasks) = 17.4K/task
  - Features: 124,500 (8 tasks) = 15.6K/task
  - Bug fixes: 98,100 (7 tasks) = 14K/task
  - Chores: 2,400 (1 task) = 2.4K/task

Task breakdown: Security 25%, Features 40%, Bugs 35%, Chores 5%
Quality: 88% first-time CI pass, +2% coverage, 0 critical reviews

Personality effectiveness:
  - Guardian: 1 security audit (high quality, 90K tokens but saved 2 days of analysis)
  - Architect: 7 tasks (avg 17K tokens, 95% quality)
  - Engineer: 14 tasks (avg 12K tokens, 82% quality — some re-work)

Escalations: 3 Engineer→Architect, 1 Architect→Guardian
Blocker: Engineer struggles with TypeScript strict mode (⚠️ needs skill improvement)

Cost vs. target: Dispatch 65% (target 70%), Engineer 22% (target 15%), Architect 11% (target 10%), Sage 1%, Guardian 1%
→ Engineer over-utilized; consider more Sage planning to reduce impl burden
```

---

### Monthly (Month-in-Review)

**Scope:** All work in a calendar month (4–5 weeks)

**Metrics:**
- `monthly_tokens_spent` — Total spend for the month
- `burn_rate_trend` — Is cost increasing/decreasing/stable week-to-week?
- `personality_impact` — Has adopting voice-notify changed work quality? Cost? Morale?
- `skill_maturity` — Which skills are production-ready? Which need investment?
- `agent_specialization` — Are agents getting better at their focus areas?
- `cost_target_adherence` — Over/under on 70/15/10/3/2 split? By how much?
- `deployment_cadence` — How many repos deployed? Release frequency? Regression rate?
- `team_productivity` — Throughput (commits/week), quality (CI pass rate), velocity (features/week)
- `personality_feedback` — Which voices are most effective? Do we need new personalities?

**Action:** Monthly retrospective with team; update ORCHESTRATION.md roadmap if needed.  
**Goal:** Long-term trend analysis; feed insights into v2/v3/v4 roadmap.

**Example Output:**
```
=== Monthly Summary (April 2026) ===
Total tokens: 1,248,000 (80 sessions across 20 work days)
Burn rate: 62.4K tokens/day avg
Trend: Stable week-to-week (±5%)

Personality Impact:
  + Voice-notify increased task completion by 18% (easier to track progress)
  + Reduced context-switching (fewer "where was I?" moments)
  - Guardian personality under-utilized (only 1.5% of tasks); consider more security focus

Skills Status:
  ✓ {example-service}: Production-ready, 100% adoption
  ✓ {example-service}: Production-ready, 95% adoption
  ⚠️ {example-service}: 80% ready, needs more Opus 4.6 design work
  ⚠️ {example-service}-consumer: 70% ready, Engineer struggles with idempotency logic
  ⚠️ {example-service}: 60% ready, needs retry/circuit-breaker patterns

Agent Specialization:
  - Dispatch: Excellent routing; 98% correct first-time
  - Engineer: Strong on simple tasks; struggling with TypeScript strict mode
  - Architect: Excellent diagnosis; avg plan quality 9.2/10
  - Sage: Not enough data yet (low utilization); recommend more complex planning
  - Guardian: Excellent when used; very high-quality analysis

Cost vs. Target: Dispatch 64%, Engineer 23%, Architect 10%, Sage 1.5%, Guardian 1.5%
→ Engineer still 8pts over target; plan more Sage planning to reduce impl burden
→ Sage under-utilized; schedule 2–3 complex planning sessions next month

Deployments: 12 repos deployed, 2 production incidents (both resolved <1h)
Throughput: 32 commits/week avg, 88% CI pass rate (target: 95%), +1.2% coverage trend

Recommendations for May:
1. Invest in "{example-service}-consumer" skill (Architect + Engineer pairing)
2. Increase Sage utilization (schedule 3 multi-repo design sessions)
3. Add TypeScript strict mode handling to Engineer training
4. Experiment with new Guardian personality variant for compliance/audit work
5. Consider v2 milestone: add memory/persistence to agents (cross-session learning)
```

---

## Implementation: Logging & Dashboards

### Logging Structure

Store metrics in a structured JSON format per session:

```json
{
  "session_id": "2026-04-20-session-001",
  "date": "2026-04-20",
  "duration_minutes": 95,
  "start_model": "haiku",
  "start_effort": "low",
  "agents_used": ["haiku", "sonnet", "opus47"],
  "handoffs": [
    {"from": "dispatch", "to": "architect", "reason": "bug diagnosis"},
    {"from": "architect", "to": "engineer", "reason": "implementation"}
  ],
  "tokens_spent": {
    "haiku_low": 3200,
    "sonnet_high": 8400,
    "opus47_max": 12100,
    "total": 23700
  },
  "tasks_completed": [
    {"type": "commit", "repo": "{service-name}", "description": "fix(security): remove XSS vector"},
    {"type": "ci_pass", "repo": "{service-name}", "status": "green"}
  ],
  "escalations": [
    {"from": "engineer", "to": "architect", "reason": "type narrowing issue", "resolved": true}
  ],
  "voice_notifies": 8,
  "notes": "Good session; Engineer needs TypeScript strict mode training"
}
```

### Dashboard (Future)

Ingest JSON logs into a BI tool (Grafana, Tableau, etc.):
- Real-time token spend (per-session)
- Daily cost breakdown by model
- Weekly trend analysis
- Monthly efficiency metrics

---

## Fortnightly Review Cycle

**Every 2 weeks (10 work days):**

1. **Analyze metrics** — Review daily/weekly dashboards; identify trends and anomalies
2. **Fine-tune cost targets** — Adjust 70/15/10/3/2 split based on workload changes
3. **Refine personalities** — Quick poll: are voices working? Any new needs?
4. **Skill investment** — Which skills saw the most friction? Prioritize next
5. **Orchestration improvements** — Update AGENTS.md, ORCHESTRATION.md with learnings
6. **Update roadmap** — Adjust v2/v3 timeline; plan next 2 weeks of focus areas
7. **Team sync** — Brief retro; share key findings; reset cost targets if needed

**Fast iteration approach:**
- Weekly dashboards feed into fortnightly reviews (not waiting for month-end)
- Quick fixes applied same sprint (skill gaps, personality tweaks, routing logic)
- Monthly retrospective (every 4 weeks) for deeper trends + quarterly (every 8 weeks) for strategic planning

---

## Real-Time Usage Monitoring via Dispatch

**Dispatch (Haiku, Low Effort) reports /usage every 5–10 minutes during active work:**

Every N minutes, Dispatch checks current session metrics and voice-notifies:

```
Dispatch: "Session checkpoint: 8K tokens spent (Dispatch 40%, Engineer 35%, Architect 25%). 
3 tasks completed. No blockers. Next: {example-service} security analysis."
```

**Frequency:** Every 5 min if user is actively watching, 10 min during background work.  
**Voice:** Dispatch (conversational, efficient), ~70% volume  
**Metrics included:**
- Tokens spent so far (session total)
- Model breakdown (%)
- Tasks completed count
- Any blockers or escalations
- Next steps / current focus

**Configuration:**
```json
{
  "dispatch_monitoring": {
    "enabled": true,
    "interval_minutes": 5,
    "voice_personality": "dispatch",
    "voice_volume": 0.7,
    "metrics_included": ["tokens", "breakdown", "tasks", "blockers", "next_steps"]
  }
}
```

This keeps the human in the loop with near-real-time cost awareness while specialists work.

---

## Example Measurement Commands

```bash
# Per-session summary (at end of session)
agents-session-summary 2026-04-20-session-001

# Daily metrics
agents-daily-metrics 2026-04-20

# Weekly report
agents-weekly-report "2026-04-14:2026-04-20"

# Real-time usage check (every 5-10 min via Dispatch voice-notify)
agents-checkpoint --voice=dispatch

# Fortnightly review (every 2 weeks)
agents-fortnightly-review "2026-04-14:2026-04-27"

# Dashboard drill-down
agents-dashboard --model=engineer --week=2026-04-14
```

---

## Update Log

- **2026-04-19:** Initial METRICS.md established. Measurement framework defined at per-session, daily, weekly, monthly timescales.
