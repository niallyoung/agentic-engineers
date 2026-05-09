# Usage-Tracking Skill

Agent skill for real-time and historical token usage capture, analysis, and forecasting. Automatically invoked at key workflow points to enable budget-aware decisions.

## Automatic Integration (No Agent Action Needed)

The skill is **automatically invoked** by the Orchestrator at:
- **Session start**: `bash scripts/capture_token_usage.sh`
- **Before delegation**: `bash scripts/usage-tracking.sh analyze --json`
- **Every 30 minutes**: `bash scripts/usage-tracking.sh snapshot`
- **In HANDBACK blocks**: Agents include usage metrics automatically

See `ORCHESTRATOR-CHECKLIST.md` for the complete automatic workflow.

## Manual Invocation (During Task Work)

Agents can explicitly call the skill when needed:
```bash
# Check current usage before major work
bash skills/usage-tracking/scripts/usage-tracking.sh analyze

# Capture + show trends (Orchestrator checkpoints)
bash skills/usage-tracking/scripts/usage-tracking.sh snapshot

# Get JSON for automation
bash skills/usage-tracking/scripts/usage-tracking.sh analyze --json
```

## Session Initialization

To start a session with automatic tracking enabled:

```bash
bash skills/usage-tracking/SESSION-INIT.sh
```

This:
- Captures baseline usage
- Shows initial budget status
- Optionally sets up cron for background capture (every 30 min)
- Prints quick reference commands

## Setup (One-Time)

```bash
# Make scripts executable
chmod +x scripts/*.sh scripts/*.py
chmod +x SESSION-INIT.sh

# View full documentation
cat SKILL.md
```

## Key Commands

| Command | Purpose | Use Case |
|---------|---------|----------|
| `capture` | Record current usage to history | Periodic snapshots (cron) |
| `analyze` | Show trends and forecasts | Budget-aware decision making |
| `snapshot` | Capture + analyze (combined) | Orchestrator checkpoints |
| `logs` | Show recent history entries | Debugging, verification |
| `cron-setup` | Print cron job instructions | Automated background capture |

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Complete skill documentation |
| `scripts/capture_token_usage.sh` | Snapshot current usage |
| `scripts/analyze_usage_trends.py` | Trend analysis and forecasting |
| `scripts/usage-tracking.sh` | CLI wrapper for all commands |

## When Agents Call This

1. **Orchestrator at session start**: Capture baseline
2. **Orchestrator before delegation**: Check budget, decide model tier
3. **All agents before expensive work**: Verify budget available
4. **Orchestrator every 30 min**: Analyze trends, adjust course
5. **Quality Engineer during review**: Check token consumption reasonableness
6. **Orchestrator at session end**: Capture final state for daily metrics

## Example: Orchestrator Workflow

```bash
# 1. Start of session
bash skills/usage-tracking/scripts/capture_token_usage.sh

# 2. Pre-delegation check (before assigning work to Engineer)
bash skills/usage-tracking/scripts/usage-tracking.sh analyze
# Output: Session 35%, weekly 28% → GREEN status → proceed normally

# 3. Every 30 minutes
bash skills/usage-tracking/scripts/usage-tracking.sh snapshot
# Output: Session 65%, weekly 40%, rising trend → YELLOW → monitor closely

# 4. Make decisions
# If session > 85%: switch to Haiku-only, defer non-critical work
# If weekly > 85%: same approach, wait for weekly reset

# 5. End of session
bash skills/usage-tracking/scripts/usage-tracking.sh analyze
# Output included in daily metrics for trends
```

## Data Location

History stored in: `data/metrics/usage_history.jsonl`

One JSON object per line, append-only format. No external database needed.

## Documentation

See `SKILL.md` for:
- Complete integration guide
- Output format examples
- Error handling
- Future enhancements

See `../orchestration/TOKEN-USAGE-TRACKING.md` for:
- Detailed setup and configuration
- Cron job setup
- Troubleshooting
- Analysis algorithms
