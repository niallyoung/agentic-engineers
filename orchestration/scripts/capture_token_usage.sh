#!/bin/bash
# Capture current token usage state to historical log for trend analysis

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
METRICS_DIR="$PROJECT_ROOT/data/metrics"
USAGE_HISTORY="$METRICS_DIR/usage_history.jsonl"

# Ensure metrics directory exists
mkdir -p "$METRICS_DIR"

# Get current budget status from usage_budget_check.py
if [ ! -f "$SCRIPT_DIR/usage_budget_check.py" ]; then
    echo "ERROR: usage_budget_check.py not found at $SCRIPT_DIR" >&2
    exit 1
fi

# Capture current usage data as JSON
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SESSION_INFO=$(python3 "$SCRIPT_DIR/usage_budget_check.py" --json 2>/dev/null || echo '{}')

# Extract values from JSON (handle parsing gracefully)
SESSION_PCT=$(echo "$SESSION_INFO" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('session_usage_percent', 0))" 2>/dev/null || echo "0")
WEEKLY_PCT=$(echo "$SESSION_INFO" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('weekly_usage_percent', 0))" 2>/dev/null || echo "0")
STATUS=$(echo "$SESSION_INFO" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('status', 'UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")

# Build JSON log entry
LOG_ENTRY=$(python3 -c "
import json, sys
entry = {
    'timestamp': '$TIMESTAMP',
    'session_usage_pct': $SESSION_PCT,
    'weekly_usage_pct': $WEEKLY_PCT,
    'status': '$STATUS',
    'environment': '$(echo ${ENV_NAME:-development})',
}
print(json.dumps(entry))
")

# Append to history (JSON Lines format)
echo "$LOG_ENTRY" >> "$USAGE_HISTORY"

# Report what was captured
if [ "${VERBOSE:-false}" = "true" ]; then
    echo "✓ Captured usage snapshot:"
    echo "  Timestamp: $TIMESTAMP"
    echo "  Session:   $SESSION_PCT%"
    echo "  Weekly:    $WEEKLY_PCT%"
    echo "  Status:    $STATUS"
    echo "  Written to: $USAGE_HISTORY"
fi

# Alert if approaching limit
if (( $(echo "$SESSION_PCT > 85" | bc -l) )); then
    bash "$SCRIPT_DIR/voice_notify.sh" "Session usage critical, $SESSION_PCT percent" --voice Daniel 2>/dev/null || true
elif (( $(echo "$SESSION_PCT > 70" | bc -l) )); then
    bash "$SCRIPT_DIR/voice_notify.sh" "Session usage high, $SESSION_PCT percent" --voice Daniel 2>/dev/null || true
fi

exit 0
