# Usage-Tracking Skill: Quick Start

Get automatic token usage tracking running in your workflow in under 5 minutes.

---

## 30-Second Summary

This skill automatically captures and analyzes token usage throughout your session. **No agent action needed** — calls happen automatically at key decision points (session start, before delegations, checkpoints, task completion).

Result: Budget-aware task routing, automatic alerts, and historical usage data for optimization.

---

## Start a Session (One Command)

```bash
cd ~/git/ers
bash {service-name}/agentic-engineers/skills/usage-tracking/SESSION-INIT.sh
```

This:
✓ Captures baseline usage  
✓ Shows current budget status (GREEN/YELLOW/RED)  
✓ Prints quick reference commands  
✓ Optionally sets up background capture

---

## How It Works (Automatic)

### No Agent Action Needed

The Orchestrator automatically:

1. **Session Start**: Captures baseline usage
   ```bash
   bash skills/usage-tracking/scripts/capture_token_usage.sh
   ```

2. **Before Each Task**: Checks budget, decides model tier
   ```bash
   bash skills/usage-tracking/scripts/usage-tracking.sh analyze --json
   ```
   - GREEN (0-70%): Use Sonnet/Opus as needed
   - YELLOW (70-85%): Use Sonnet, estimate tokens
   - RED (>85%): Use Haiku only or defer

3. **Every 30 Minutes**: Monitors consumption rate
   ```bash
   bash skills/usage-tracking/scripts/usage-tracking.sh snapshot
   ```
   Output: velocity, hours to reset, trend direction

4. **Task Completion**: Receives metrics in HANDBACK
   - usage_before%, usage_after%, tokens_consumed
   - Model used, efficiency notes

5. **Session End**: Final metrics exported
   ```bash
   bash skills/usage-tracking/scripts/usage-tracking.sh analyze
   ```

### Voice Alerts (Passive)

When thresholds hit: "Session usage high, 70 percent" or "critical, 85 percent" (Daniel voice)  
No action needed — alerts inform decisions naturally.

---

## Manual Checks (When You Want Extra Visibility)

Engineers can manually invoke during task work:

```bash
# Quick status before starting expensive operation
bash skills/usage-tracking/scripts/usage-tracking.sh analyze

# Full trend report
bash skills/usage-tracking/scripts/usage-tracking.sh snapshot

# JSON for scripting
bash skills/usage-tracking/scripts/usage-tracking.sh analyze --json
```

---

## Data Storage

Usage history stored in: `data/metrics/usage_history.jsonl`

One entry per capture, JSON Lines format:
```json
{"timestamp":"2026-04-25T10:30:00Z","session_usage_pct":65.3,"weekly_usage_pct":42.1,"status":"YELLOW"}
```

Permanent storage — used for trend analysis and optimization.

---

## Workflow Integration

### Orchestrator Duties (with automatic calls built-in)

```
Session Start:
  → Automatic: capture baseline
  
For Each Task:
  → Automatic: check budget
  → Create DELEGATE with budget context
  → Receive HANDBACK with metrics
  
Every 30 Min:
  → Automatic: snapshot status
  → Update TODO with status
  
Session End:
  → Automatic: final metrics
  → Export for daily analysis
```

See `orchestration/ORCHESTRATOR-CHECKLIST.md` for full checklist with automatic points marked.

### Engineer Duties (optional explicit calls)

```
Before Major Work:
  → Optional: bash usage-tracking.sh analyze
  → Check if sufficient budget available
  
In HANDBACK:
  → Include: usage_before%, usage_after%, tokens_consumed
  → Include: model_used, efficiency_note
```

---

## Budget-Aware Delegation Example

DELEGATE block automatically includes budget context:

```yaml
---
handoff_type: DELEGATE
task_id: 2026-04-25-example
role: Engineer
model: claude-sonnet-4-6
budget_context:
  session_pct_at_delegation: 65
  hours_until_reset: 4.2
  status: YELLOW
  recommendation: "Sonnet suitable; estimate <3K tokens"
...
---
```

Engineer sees budget upfront and can optimize token usage.

---

## Automatic vs. Manual Points

**Automatic** (Orchestrator does automatically):
- ✅ Session start capture
- ✅ Pre-delegation budget check
- ✅ 30-minute checkpoints
- ✅ Voice alerts at thresholds
- ✅ Metrics collection from HANDBACK
- ✅ Session end analysis

**Manual/Optional** (Agents choose when to call):
- ⚠️ Engineer mid-task status check (optional)
- ⚠️ Quality Engineer anomaly review (optional)
- ⚠️ Model Engineer trend analysis (part of daily metrics)

**Interpret** (Orchestrator makes decisions):
- 🧠 Budget status: GREEN/YELLOW/RED?
- 🧠 Next model tier: Sonnet/Haiku based on budget?
- 🧠 Velocity: Consumption accelerating/stable?
- 🧠 Anomalies: Task consumed way more/less than expected?

---

## Commands (All You Need)

```bash
# Initialize session with automatic tracking
bash skills/usage-tracking/SESSION-INIT.sh

# Orchestrator: Pre-delegation budget check
bash skills/usage-tracking/scripts/usage-tracking.sh analyze --json

# Orchestrator: 30-minute checkpoint
bash skills/usage-tracking/scripts/usage-tracking.sh snapshot

# Anyone: Quick status when needed
bash skills/usage-tracking/scripts/usage-tracking.sh analyze

# Optional: View raw history
bash skills/usage-tracking/scripts/usage-tracking.sh logs

# Optional: Setup background capture (every 30 min)
bash skills/usage-tracking/scripts/usage-tracking.sh cron-setup | bash
```

---

## Features

✅ Automatic capture at session start/checkpoints  
✅ Budget status (GREEN/YELLOW/RED)  
✅ Velocity calculation (% per hour)  
✅ Reset time forecasting (hours until 100%)  
✅ Trend detection (rising/falling/stable)  
✅ Voice alerts (70% warning, 85% critical)  
✅ Historical data (JSON Lines format)  
✅ No manual input required (metrics automatic)  
✅ Works offline (no API calls)  
✅ JSON output for automation  

---

## Common Scenarios

### Scenario 1: Session Planning
```bash
# At session start
bash skills/usage-tracking/SESSION-INIT.sh
# → Shows: Session 0%, Weekly 35%, GREEN status
# → Decision: Full capability available, plan complex work
```

### Scenario 2: Mid-Session Checkpoint
```bash
# Orchestrator checkpoint at 10:30
bash skills/usage-tracking/scripts/usage-tracking.sh snapshot
# → Shows: Session 65%, rising 7%/hr, 5 hours to reset
# → Decision: YELLOW status, next task use Sonnet (efficient)
```

### Scenario 3: Engineer Pre-Task Check
```bash
# Engineer before starting refactor
bash skills/usage-tracking/scripts/usage-tracking.sh analyze
# → Shows: Session 72%, 3.8 hours to reset
# → Decision: Estimate 3.5K tokens needed, fits within budget
```

### Scenario 4: Approaching Limits
```bash
# Orchestrator notices trend acceleration
bash skills/usage-tracking/scripts/usage-tracking.sh snapshot
# → Shows: Session 88%, rising 12%/hr, 1 hour to reset
# → Decision: RED status, suggest break until reset
```

---

## Troubleshooting

**"No usage data captured yet"**
- Run `bash skills/usage-tracking/SESSION-INIT.sh` to initialize

**Voice alerts too loud**
- Use `--silent` flag: `bash scripts/capture_token_usage.sh --silent`

**Usage percentages showing 0%**
- Normal — can't programmatically query Claude API yet
- Manual input option in `USAGE-BUDGET-MANAGER.md`

**Path errors when running from different directory**
- Run from project root: `cd ~/git/ers`
- Or use absolute path: `bash /full/path/to/scripts/usage-tracking.sh`

---

## See Also

- `SKILL.md` — Complete skill documentation
- `AGENT-INTEGRATION.md` — When agents call skill (optional)
- `ORCHESTRATOR-CHECKLIST.md` — Full Orchestrator workflow
- `orchestration/AUTOMATIC-INVOCATION.md` — How automatic integration works
- `orchestration/HANDOFF.md` — DELEGATE/HANDBACK protocol
- `orchestration/TOKEN-USAGE-TRACKING.md` — Technical setup
- `orchestration/USAGE-BUDGET-MANAGER.md` — Real-time budget checking
- `skills/roles/orchestrator.md` — Orchestrator role with automatic tracking

---

## Next Steps

1. **Start session**: `bash skills/usage-tracking/SESSION-INIT.sh`
2. **Create TODO.md** with backlog items
3. **Plan first task** using AGENTS.md routing
4. **Create DELEGATE** with budget context (automatic in workflow)
5. **Receive HANDBACK** with metrics (automatic collection)
6. **Repeat** with 30-min checkpoints (automatic)
7. **End session** with final metrics (automatic)

Everything else runs automatically. You just interpret the budget status and make model selection decisions.

---

**Ready? Run: `bash skills/usage-tracking/SESSION-INIT.sh`**
