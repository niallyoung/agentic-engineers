---
name: automatic-invocation-integration
description: How usage-tracking skill is automatically invoked throughout the workflow
---

# Automatic Invocation: Usage-Tracking Skill Integration

Usage-tracking is embedded into the Orchestrator workflow at key decision points. **No explicit agent action required** — calls happen automatically as part of standard workflow.

---

## Invocation Points (Timeline)

### 1. Session Start (T+0)

**Who**: Orchestrator
**When**: Beginning of session, before any task planning
**What happens**:
```bash
bash skills/usage-tracking/scripts/capture_token_usage.sh
```

**Purpose**: Establish baseline usage percentage, verify budget available

**Output**:
```
✓ Captured usage snapshot:
  Timestamp: 2026-04-25T09:00:00Z
  Session:   0%
  Weekly:    35%
  Status:    GREEN
  Written to: data/metrics/usage_history.jsonl
```

**Orchestrator action**: Review status
- GREEN (0-70%): Plan session with full capability
- YELLOW (70-85%): Plan session with budget consciousness
- RED (>85%): Consider deferring non-critical work or waiting for reset

---

### 2. Pre-Delegation Check (Before Each Task)

**Who**: Orchestrator
**When**: Before creating DELEGATE block and routing to Engineer/Senior/etc.
**What happens**:
```bash
bash skills/usage-tracking/scripts/usage-tracking.sh analyze --json
```

**Purpose**: Determine appropriate model tier based on current budget

**Output**:
```json
{
  "session": {
    "current": 42.5,
    "status": "GREEN"
  }
}
```

**Orchestrator decision logic**:
```
IF session < 70%:
  → Use best model for task (Sonnet for medium, Opus for complex)
ELSE IF session 70-85%:
  → Use Sonnet (balanced capability/efficiency)
ELSE (session > 85%):
  → Use Haiku only OR defer task
```

**DELEGATE block includes**:
```yaml
budget_context:
  session_pct_at_delegation: 42.5
  hours_until_reset: 9.2
  status: GREEN
  recommendation: "Sonnet suitable for this scope"
```

Engineer sees budget upfront and can optimize token usage.

---

### 3. Periodic Checkpoints (Every 30 Minutes)

**Who**: Orchestrator
**When**: Automatically during active session, every ~30 min
**What happens**:
```bash
bash skills/usage-tracking/scripts/usage-tracking.sh snapshot
```

**Purpose**: Monitor consumption rate, detect anomalies, adjust strategy

**Output**:
```
SESSION USAGE:
  Current:    58.3%
  Trend:      RISING
  Velocity:   +5.2% per hour
  Reset in:   ~7.9 hours

STATUS: 🟡 YELLOW
```

**Orchestrator decisions**:
- Consumption on track? Continue
- Accelerating? Next task should be simpler or use Haiku
- Decelerating? Can handle more complex work
- Approaching reset? Plan break or lightweight tasks

**TODO update**:
```
# Checkpoint 09:30 — Session 48.3% (rising 5.2%/hr), task 1 complete
# Checkpoint 10:00 — Session 58.3% (rising, acceleration detected), task 2 in progress
# Action: Next task → use Haiku to cool off, estimate max 2K tokens
```

---

### 4. Delegation (In DELEGATE Block)

**Who**: Orchestrator
**When**: Creating DELEGATE for Engineer/Senior/etc.
**What happens**: Automatically includes budget context

**DELEGATE includes**:
```yaml
---
handoff_type: DELEGATE
task_id: 2026-04-25-refactor-auth
role: Engineer
model: claude-sonnet-4-6
budget_context:
  session_pct_at_delegation: 62
  estimated_tokens_needed: 2800
  hours_until_reset: 6.5
  status: YELLOW
  recommendation: "Sonnet sufficient; watch token estimate"
---
```

**Engineer sees**:
- Current session usage (62%)
- How many tokens task might consume (2800)
- Hours until reset (6.5)
- What model to use (Sonnet)

Engineer can then:
- Estimate if task fits within budget
- Optimize implementation to use fewer tokens
- Ask for clarification if estimate seems wrong
- Self-escalate if task appears too complex

---

### 5. Task Execution (During Work)

**Who**: Engineer (optional, self-initiated)
**When**: During long task work, if concerned about budget
**What happens**:
```bash
# Engineer silently checks midway
bash skills/usage-tracking/scripts/capture_token_usage.sh --silent
```

**Purpose**: Engineer self-monitors to ensure pace is sustainable

**Not required** — Orchestrator's automatic checkpoints provide visibility. Engineers only need this if they want personal awareness during their work.

---

### 6. HANDBACK (Task Completion)

**Who**: Engineer (and all agents)
**When**: Returning completed work to Orchestrator
**What happens**: Automatically include metrics in HANDBACK

**HANDBACK includes metrics**:
```yaml
---
handoff_type: HANDBACK
task_id: 2026-04-25-refactor-auth
status: complete
deliverables:
  - Modified: lambda/identity/auth.go
  - Tests: Added TestAuthRefresh
metrics:
  usage_before_session_pct: 62
  usage_after_session_pct: 67
  tokens_consumed_estimate: 2150
  session_velocity_pct_per_hour: 2.1
  model_used: claude-sonnet-4-6
  efficiency_note: "Token consumption 23% below estimate; good pattern reuse"
---
```

**Orchestrator actions**:
1. Check: Did consumption match budget estimate? (Estimated 2800, actual 2150 ✓)
2. Verify: Were tokens used efficiently? (Yes, pattern reuse noted)
3. Record: Add metrics to session summary for daily analysis
4. Update TODO: Mark task DONE, record final session% (67%)
5. Next decision: With 67% usage, can continue normally or switch to Haiku if approaching checkpoint

---

### 7. Automatic Checkpoints Continue

**Who**: Orchestrator
**When**: Every ~30 minutes throughout session
**What happens**: Continuous monitoring via `snapshot`

Cycle repeats:
1. Checkpoint every 30 min → `snapshot`
2. Pre-delegation check → `analyze --json`
3. Create DELEGATE with budget context
4. Receive HANDBACK with metrics
5. Repeat

---

### 8. Session End (T+session_length)

**Who**: Orchestrator
**When**: End of session or before passing to next agent
**What happens**:
```bash
bash skills/usage-tracking/scripts/usage-tracking.sh analyze
```

**Output**:
```
Samples: 12
Time Span: 2026-04-25T09:00:00Z → 2026-04-25T15:30:00Z
Duration: 6.5 hours

SESSION USAGE:
  Current:    78.3%
  Min:        0%
  Max:        78.3%
  Average:    42.1%
  Trend:      RISING
  Velocity:   +12.0% per hour
  Reset in:   ~1.8 hours
```

**Recorded for daily analysis**:
- Total session duration: 6.5 hours
- Peak usage: 78.3%
- Average velocity: 12%/hour
- Estimated reset: 1.8 hours
- All HANDBACK metrics from completed tasks

---

## Voice Alerts (Automatic)

When session hits thresholds, voice alert fires:

```
70% threshold: "Session usage high, 70 percent" (Daniel voice)
85% threshold: "Session usage critical, 85 percent" (Daniel voice)
```

**No action needed** — alerts provide passive awareness. Orchestrator continues normal workflow, but acknowledges budget status.

---

## Data Flow: Automatic Integration Points

```
SESSION START
    ↓ capture_token_usage.sh
    → Baseline snapshot logged
    ↓
BEFORE TASK 1
    ↓ analyze --json
    → Check budget → GREEN → delegate to Engineer with Sonnet
    ↓
[Engineer executes Task 1]
    ↓
RECEIVE HANDBACK + metrics
    → usage_before: 0%, usage_after: 15%
    → tokens_consumed: 3100
    ↓ record to session summary
    ↓
30-MIN CHECKPOINT
    ↓ snapshot
    → Session 15%, rising 2.4%/hr, 35h to reset
    → Continue normally
    ↓
BEFORE TASK 2
    ↓ analyze --json
    → Check budget → GREEN → delegate to Senior with Sonnet
    ↓
[Senior Engineer executes Task 2]
    ↓
RECEIVE HANDBACK + metrics
    → usage_before: 15%, usage_after: 31%
    → tokens_consumed: 5200
    ↓ record to session summary
    ↓
30-MIN CHECKPOINT
    ↓ snapshot
    → Session 31%, rising 3.1%/hr, 22h to reset
    → Continue normally
    ↓
...continue pattern...
    ↓
SESSION END
    ↓ analyze
    → Final metrics: 78.3% session, 6.5h duration, 12%/hr velocity
    → Exported for daily analysis by Model Engineer
```

---

## Orchestrator Responsibilities

With automatic invocation, Orchestrator's responsibilities are:

### ✅ Automatic (No explicit action)
- Capture baseline at session start
- Check budget before each delegation
- Checkpoint every 30 minutes
- Collect metrics from HAN DBAcks
- Record to session summary
- Generate voice alerts
- Export final metrics

### ⚠️ Manual (Interpret & decide)
- **Interpret budget status**: GREEN/YELLOW/RED
- **Choose model based on budget**: Sonnet if green, Haiku if red
- **Update TODO** with checkpoint results
- **Escalate** if approaching limits (suggest break or defer)
- **Review metrics** for anomalies (task consumed way more/less than expected)
- **Provide feedback** to Model Engineer (was routing optimal?)

### 🔔 Passive (Acknowledge)
- Voice alerts at thresholds (70%, 85%)
- Hear alerts but continue workflow
- Let alerts inform decisions naturally

---

## Benefits of Automatic Integration

1. **No forgotten checkpoints**: Every 30 min automatic, not skipped
2. **Consistent data**: Same metrics collected every task
3. **Budget awareness**: Model selection automatic based on budget
4. **Trend visibility**: Velocity and consumption patterns visible
5. **Less context switching**: Orchestrator doesn't need to manually run commands
6. **Historical record**: All usage data saved for optimization

---

## Disabling Automatic Features

If automatic calls become intrusive:

```bash
# Disable voice alerts (run silently)
bash skills/usage-tracking/scripts/capture_token_usage.sh --silent

# Skip cron background capture (if enabled)
export SKIP_CRON=1
```

But all other automatic integration remains (checkpoints, pre-delegation checks, HANDBACK metrics).

---

## Configuration

### Checkpoint Frequency
Default: Every ~30 minutes (Orchestrator manually calls every checkpoint)
To change: Update `TODO.md` checkpoint interval or cron job if using background capture

### Voice Alert Thresholds
Default: 70% (warning), 85% (critical)
To customize: Edit capture script voice alert section

### Data Storage
Location: `data/metrics/usage_history.jsonl`
Retention: Permanent (for historical trend analysis)

---

## See Also

- `ORCHESTRATOR-CHECKLIST.md` — Step-by-step workflow with automatic points
- `skills/usage-tracking/AGENT-INTEGRATION.md` — When agents call skill
- `skills/usage-tracking/SESSION-INIT.sh` — Initialize automatic tracking for session
- `HANDOFF.md` — DELEGATE/HANDBACK protocol (includes automatic integration section)
- `skills/roles/orchestrator.md` — Orchestrator role responsibilities
