---
name: token-usage-tracking
description: Historical token usage capture and trend analysis across sessions
type: orchestration
---

# Token Usage Tracking

Capture and analyze Claude API token usage over time to optimize session planning and stay within global usage limits.

## Overview

**Problem**: Token usage limits reset on schedules (session, weekly, monthly), and you need visibility into consumption patterns to:
- Avoid unexpected resets mid-task
- Maximize productive work per session
- Forecast when limits will reset
- Detect anomalies or runaway token consumption

**Solution**: Automated capture of usage snapshots at regular intervals (e.g., every 30 minutes), stored as JSON Lines for analysis and trend reporting.

## Quick Start

### Manual Capture (Right Now)
```bash
usage-tracking capture
usage-tracking analyze
```

### Automatic Capture (Cron)
```bash
# Setup: capture every 30 minutes
usage-tracking cron-setup | bash

# Or manually:
(crontab -l 2>/dev/null; echo "*/30 * * * * /path/to/capture_token_usage.sh") | crontab -
```

## How It Works

### 1. Capture Phase

**`capture_token_usage.sh`** — Snapshot current usage state:
- Calls `usage_budget_check.py --json` to get current session/weekly percentages
- Records timestamp, usage percentages, status, environment
- Appends JSON object to `data/metrics/usage_history.jsonl` (JSON Lines format)
- Optional: voice alert if session usage exceeds 70% (warning) or 85% (critical)

**Storage**: `data/metrics/usage_history.jsonl`
```json
{"timestamp":"2026-04-25T14:30:00Z","session_usage_pct":45.2,"weekly_usage_pct":32.1,"status":"GREEN","environment":"development"}
{"timestamp":"2026-04-25T15:00:00Z","session_usage_pct":52.8,"weekly_usage_pct":33.5,"status":"GREEN","environment":"development"}
```

### 2. Analysis Phase

**`analyze_usage_trends.py`** — Compute metrics from historical data:
- Loads all entries from usage history file
- Calculates: current, min, max, average usage
- Computes velocity (% per hour) and trend (rising/falling)
- Estimates time to reset based on consumption rate
- Outputs human-readable report or JSON

**Sample Output**:
```
SESSION USAGE:
  Current:    52.8%
  Range:      45.2% → 62.1%
  Average:    53.4%
  Trend:      RISING
  Velocity:   +0.382% per hour
  Reset in:   ~32.5 hours

WEEKLY USAGE:
  Current:    33.5%
  Range:      32.1% → 40.2%
  Average:    34.8%
  Trend:      RISING
  Velocity:   +0.041% per hour
```

## Commands

### capture_token_usage.sh
Direct script — capture with optional verbose output:
```bash
bash scripts/capture_token_usage.sh          # Silent
VERBOSE=true bash scripts/capture_token_usage.sh  # Show what was captured
```

### analyze_usage_trends.py
Direct script — analyze with optional JSON output:
```bash
python3 scripts/analyze_usage_trends.py      # Human-readable report
python3 scripts/analyze_usage_trends.py --json  # JSON (for automation)
```

### usage-tracking.sh (Main Interface)
Unified wrapper:
```bash
usage-tracking capture              # Capture now (verbose)
usage-tracking analyze              # Show trend report
usage-tracking analyze --json       # JSON trend data
usage-tracking snapshot             # Capture + show current
usage-tracking logs                 # Show last 10 entries
usage-tracking cron-setup           # Print cron instructions
```

## Integration

### With Orchestrator HANDOFF Protocol

During Orchestrator planning, check usage before delegating work:

```markdown
## Usage Budget Check
Before delegating Engineer work, confirm we have sufficient budget:

[Usage status: session 45%, weekly 32%]
- GREEN status: proceed with full Haiku/Sonnet delegation
- YELLOW status: consider deferring non-critical work to next session
- RED status: switch to Haiku 4.5 only or defer to next session
```

### With agentic-engineers Framework

Add usage awareness to Orchestrator duties (update in USAGE-BUDGET-INTEGRATION.md):

```bash
# Start of session: capture baseline
usage-tracking capture

# Mid-session checkpoints (every 30 min)
# Cron job handles automatically

# End of session: analyze and report
usage-tracking analyze
```

### Automation Examples

**Shell script integration**:
```bash
#!/bin/bash
USAGE=$(python3 analyze_usage_trends.py --json)
SESSION_PCT=$(echo "$USAGE" | jq '.session.current')

if (( $(echo "$SESSION_PCT > 80" | bc -l) )); then
    # Switch to Haiku model only
    export MODEL_PREFERENCE="haiku"
fi
```

**Python integration**:
```python
import json
import subprocess

result = subprocess.run(
    ["python3", "scripts/analyze_usage_trends.py", "--json"],
    capture_output=True, text=True
)
data = json.loads(result.stdout)

hours_to_reset = data['session'].get('estimated_reset_in_hours', float('inf'))
if hours_to_reset < 2:
    print("⚠ Session reset in < 2 hours, wrap up")
```

## Storage & Lifecycle

**Location**: `data/metrics/usage_history.jsonl`

**Format**: JSON Lines (one JSON object per line, no commas between lines)

**Retention**: Keep indefinitely for trend analysis
- Can be archived to `data/metrics/usage_history.YYYY-MM-DD.jsonl` for cleanup
- Analysis tools work on any history file

**Size**: Minimal (< 1KB per entry); 48 entries/day at 30-min intervals = ~50KB/month

## Setup Instructions

### Step 1: Enable Script Execution
```bash
chmod +x agentic-engineers/orchestration/scripts/capture_token_usage.sh
chmod +x agentic-engineers/orchestration/scripts/analyze_usage_trends.py
chmod +x agentic-engineers/orchestration/scripts/usage-tracking.sh
```

### Step 2: Test Capture
```bash
cd ~/git/ers/{service-name}
VERBOSE=true ./agentic-engineers/orchestration/scripts/capture_token_usage.sh
```

Expected output: JSON entry added to `data/metrics/usage_history.jsonl`

### Step 3: Test Analysis
```bash
python3 ./agentic-engineers/orchestration/scripts/analyze_usage_trends.py
```

Expected output: Human-readable trend report (or "No usage data" if first capture)

### Step 4: Add to Shell Aliases
```bash
# Add to ~/.zshrc or ~/.bashrc
alias usage-capture="bash ~/git/ers/{service-name}/agentic-engineers/orchestration/scripts/capture_token_usage.sh"
alias usage-analyze="python3 ~/git/ers/{service-name}/agentic-engineers/orchestration/scripts/analyze_usage_trends.py"
alias usage-tracking="bash ~/git/ers/{service-name}/agentic-engineers/orchestration/scripts/usage-tracking.sh"
```

### Step 5: Setup Cron (Optional but Recommended)
```bash
# Print setup instructions
usage-tracking cron-setup

# Install: capture every 30 minutes
(crontab -l 2>/dev/null; echo "*/30 * * * * /path/to/capture_token_usage.sh") | crontab -

# Verify installed
crontab -l | grep capture_token_usage
```

## Voice Alerts

When session usage crosses thresholds, `capture_token_usage.sh` triggers voice notifications:
- **70%**: `"Session usage high, 70 percent"` (Daniel voice)
- **85%**: `"Session usage critical, 85 percent"` (Daniel voice)

To disable:
```bash
# Pass --silent flag
bash scripts/capture_token_usage.sh --silent
```

Or comment out voice lines in `capture_token_usage.sh`.

## Troubleshooting

### "No usage data captured yet"
**Cause**: First time running — `usage_history.jsonl` doesn't exist yet

**Fix**: Run `usage-tracking capture` to create and populate the file

### "ERROR: Failed to load history"
**Cause**: Corrupted JSON in `usage_history.jsonl`

**Fix**: Check file format (one JSON object per line, no trailing commas):
```bash
# View file
cat data/metrics/usage_history.jsonl

# Validate JSON (should succeed for each line)
jq . data/metrics/usage_history.jsonl
```

### Cron job not running
**Cause**: Path issues, missing PATH environment in cron context

**Fix**: Use absolute paths in crontab
```bash
# Instead of:
*/30 * * * * capture_token_usage.sh

# Use:
*/30 * * * * {workspace-root}/{service-name}/agentic-engineers/orchestration/scripts/capture_token_usage.sh
```

Or add shebang to cron entry:
```bash
*/30 * * * * bash /path/to/capture_token_usage.sh
```

## Future Enhancements

1. **GraphQL API** — Expose usage data via simple HTTP endpoint for dashboards
2. **Grafana Integration** — Send metrics to Grafana for visualization
3. **Slack Alerts** — Notify on usage anomalies or approaching resets
4. **Email Reports** — Weekly usage summary via email
5. **Cost Estimation** — Convert tokens to estimated API costs
6. **Budget Forecasting** — Predict when weekly/monthly limits will reset based on consumption rate

## Related

- `USAGE-BUDGET-MANAGER.md` — Real-time budget status checks
- `USAGE-BUDGET-INTEGRATION.md` — Integration with Orchestrator workflow
- `scripts/usage_budget_check.py` — Budget status calculation
- `scripts/usage-budget.sh` — Budget status wrapper

## Examples

### Check usage right now
```bash
usage-tracking snapshot
```

### See trends over last day
```bash
usage-tracking analyze
```

### Get data for automation
```bash
usage-tracking analyze --json | jq '.session.pct_per_hour'
```

### View raw capture history
```bash
usage-tracking logs
```

### Setup automatic capture
```bash
usage-tracking cron-setup | bash
```
