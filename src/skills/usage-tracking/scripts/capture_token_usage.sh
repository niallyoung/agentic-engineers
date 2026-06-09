#!/bin/bash
# Capture current token usage state to historical log for trend analysis

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Navigate from scripts/ → usage-tracking/ → skills/ → agentic-engineers/ → {workspace-name}/ → ers/
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
ERS_ROOT="$(cd "$WORKSPACE_ROOT/.." && pwd)"
METRICS_DIR="$ERS_ROOT/data/metrics"
USAGE_HISTORY="$METRICS_DIR/usage_history.jsonl"

# Ensure metrics directory exists
mkdir -p "$METRICS_DIR"

# Locate budget check script (primary: skill-relative; fallback: orchestration/)
# Per SPEC §"Queue Architecture & Paths", external scripts must not live in
# orchestration/ — this skill-relative path is canonical.
BUDGET_CHECK_SCRIPT="$SCRIPT_DIR/usage_budget_check.py"
if [ ! -f "$BUDGET_CHECK_SCRIPT" ]; then
    # Fallback for legacy deployments only
    LEGACY_PATH="$WORKSPACE_ROOT/agentic-engineers/orchestration/scripts/usage_budget_check.py"
    if [ -f "$LEGACY_PATH" ]; then
        BUDGET_CHECK_SCRIPT="$LEGACY_PATH"
        if [ "${VERBOSE:-}" = "true" ]; then
            echo "[usage-tracking] Using legacy orchestration/scripts path: $LEGACY_PATH" >&2
        fi
    else
        echo "ERROR: usage_budget_check.py not found in $SCRIPT_DIR or legacy location" >&2
        exit 1
    fi
elif [ "${VERBOSE:-}" = "true" ]; then
    echo "[usage-tracking] Using canonical skill-relative path: $BUDGET_CHECK_SCRIPT" >&2
fi

# Capture current usage data as JSON
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SESSION_INFO=$(python3 "$BUDGET_CHECK_SCRIPT" --json 2>/dev/null || echo '{}')

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

# Token usage logging complete

exit 0
