---
name: usage-tracking
description: Real-time and historical token usage capture, analysis, and forecasting skill for agents
role: All roles (Orchestrator primary)
license: Proprietary
compatibility: macOS/Linux. Requires Python 3, bash, access to data/metrics/ directory
metadata:
  author: agentic-engineers
  version: "1.0"
  category: observability
  runtime: bash/python3
---

## Overview

Agent skill for capturing and analyzing token usage patterns during sessions. Enables intelligent decision-making about task scope, model selection, and break timing based on real-time and historical usage data.

**What it does:**
1. Captures current token usage state (session%, weekly%) to historical log
2. Analyzes trends: velocity, direction, reset forecasting
3. Enables agents to query usage at key decision points
4. Supports Orchestrator budget-aware task delegation
5. Feeds data into daily metrics analysis

## When to Invoke

### Orchestrator (Primary)
- **Session start**: Capture baseline usage
- **Before delegating work**: Check budget status, decide on model tier
- **Every checkpoint** (30 min): Analyze trends, adjust model assignments if needed
- **Session end**: Record final usage for daily metrics

### Engineers (All Roles)
- **Before expensive operations**: Check if session is nearing limit
- **Decision points**: Choose implementation approach based on token budget
- **Risk assessment**: Estimate tokens needed vs. available budget

### Quality Engineer
- **During verification**: Check usage impact of completed work
- **Regression detection**: Spot if token consumption increased significantly

## Invocation

### Quick Status Check (Before Major Work)
```bash
# One-liner: get current usage without logging
bash skills/usage-tracking/scripts/capture_token_usage.sh --silent
bash skills/usage-tracking/scripts/usage-tracking.sh analyze
```

### Capture + Analyze (Orchestrator Checkpoints)
```bash
# Full checkpoint: capture snapshot and show trends
bash skills/usage-tracking/scripts/usage-tracking.sh snapshot
```

### For Automation / HANDBACK Metrics
```bash
# JSON output for parsing in scripts
bash skills/usage-tracking/scripts/usage-tracking.sh analyze --json
```

### View History
```bash
# See last few entries
bash skills/usage-tracking/scripts/usage-tracking.sh logs

# Full analysis over time
bash skills/usage-tracking/scripts/usage-tracking.sh analyze
```

## Output Examples

### Human-Readable Analysis
```
SESSION USAGE:
  Current:    65.3%
  Trend:      RISING
  Velocity:   +7.2% per hour
  Reset in:   ~4.8 hours

WEEKLY USAGE:
  Current:    42.1%
  Trend:      RISING
  Velocity:   +1.1% per hour

STATUS: 🟡 HIGH
  Approaching session limit; consider deferring non-critical tasks
```

### JSON Output (for Automation)
```json
{
  "session": {
    "current": 65.3,
    "trend": "rising",
    "pct_per_hour": 7.2,
    "estimated_reset_in_hours": 4.8
  },
  "weekly": {
    "current": 42.1,
    "trend": "rising",
    "pct_per_hour": 1.1
  }
}
```

## Integration Points

### In Orchestrator HANDOFF Protocol
Before delegating to Engineer:

```markdown
## Usage Budget Assessment

Current state: usage-tracking snapshot shows:
- Session: 65% (rising, 4.8h to reset)
- Weekly: 42% (healthy)

**Decision**: Proceed with Haiku delegation (lower token cost)
```

### In HANDBACK Metrics
Include usage impact in agent response:

```markdown
## Metrics
- Session usage before: 60%
- Session usage after: 65%
- Tokens consumed: ~2,500 (estimate)
- Model used: Haiku (cost-optimized)
```

### In Quality Engineer Verification
Check if usage consumption was reasonable for task scope:

```bash
# Quality Engineer can verify token consumption rate
# If unusually high, flag for review
```

## Data Storage

**Location**: `data/metrics/usage_history.jsonl`

**Format**: JSON Lines (one entry per capture, UTC timestamps)

```json
{"timestamp":"2026-04-25T10:30:00Z","session_usage_pct":65.3,"weekly_usage_pct":42.1,"status":"YELLOW","environment":"development"}
```

**Retention**: Permanent (for trend analysis across weeks/months)

## Configuration

Token usage logging and archival:
```bash
# Automatic logging when session > 70% or > 85%
bash skills/usage-tracking/scripts/capture_token_usage.sh
```

Silent mode (no alerts):
```bash
bash skills/usage-tracking/scripts/capture_token_usage.sh --silent
```

## Agent Integration Example

### Engineer Starting Complex Task
```bash
# 1. Check usage before committing
bash skills/usage-tracking/scripts/usage-tracking.sh analyze
# Output shows: 45% session, rising trend

# 2. Adjust approach if needed
# (proceed with full implementation, sufficient budget)

# 3. Execute task...

# 4. Report in HANDBACK with usage impact
```

### Orchestrator at Checkpoint
```bash
# 30-minute checkpoint
bash skills/usage-tracking/scripts/usage-tracking.sh snapshot

# Output shows:
# - Session: 72% (YELLOW)
# - ~3 hours to reset
# - Decision: continue with current work, monitor next checkpoint
```

## Cron Integration (Optional)

Automatic background capture for long-running sessions:

```bash
# Setup instructions
bash skills/usage-tracking/scripts/usage-tracking.sh cron-setup

# Recommended: every 30 minutes
*/30 * * * * bash /path/to/usage-tracking.sh capture
```

## Error Handling

### "No usage data captured yet"
- First invocation — no baseline exists yet
- Solution: Run `capture_token_usage.sh` to create first entry

### File permission errors
- ensure `data/metrics/` directory is writable
- Check: `ls -la data/metrics/`
- Fix: `chmod 755 data/metrics/`

### Python import errors
- Requires: Python 3.7+
- Requires: `statistics` module (built-in)
- Check: `python3 --version`

## Design Decisions

1. **Passive capture**: Agents call skill at decision points, not hooks
   - Rationale: Agents need visibility to make informed decisions
   - Cost: Minimal (few MB of history data)

2. **JSON Lines format**: Simple, append-only, machine-readable
   - Rationale: No database needed, easy to archive/rotate
   - Supports: Streaming analytics, Excel import

3. **Local archival**: Persistent local records
   - Rationale: Easy access to historical data
   - Limitation: Manual export needed for external tools

4. **No API calls**: Purely local analysis
   - Rationale: No external dependencies, works offline
   - Limitation: Can't predict reset times perfectly (uses linear extrapolation)

## Future Enhancements

1. **Real-time API integration** — Query actual Claude usage via API (when available)
2. **Grafana dashboard** — Visualize usage trends over time
3. **Slack alerts** — Post status to team channel at checkpoints
4. **Budget-aware task queueing** — Automatically defer tasks when near limits
5. **Anomaly detection** — Flag if consumption rate suddenly increases
6. **Weekly reports** — Email usage summary and recommendations

## Related Skills

- `usage-budget-manager` (orchestration/) — Real-time budget status checking
- `metrics-analyzer` (operations/) — Daily analysis and recommendations

## See Also

- `orchestration/USAGE-BUDGET-MANAGER.md` — Budget status determination
- `orchestration/USAGE-BUDGET-INTEGRATION.md` — Orchestrator workflow integration
- `orchestration/TOKEN-USAGE-TRACKING.md` — Detailed guide
