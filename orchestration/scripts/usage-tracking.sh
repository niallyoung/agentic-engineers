#!/bin/bash
# Token usage tracking: capture and analyze usage over time

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Commands
case "${1:-help}" in
    capture)
        # Capture current usage state
        VERBOSE=true bash "$SCRIPT_DIR/capture_token_usage.sh"
        ;;
    analyze)
        # Analyze historical trends
        python3 "$SCRIPT_DIR/analyze_usage_trends.py" "${2:-}"
        ;;
    snapshot)
        # Quick: capture + show current
        bash "$SCRIPT_DIR/capture_token_usage.sh"
        echo ""
        python3 "$SCRIPT_DIR/analyze_usage_trends.py"
        ;;
    logs)
        # Show raw usage history
        PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
        HISTORY="$PROJECT_ROOT/data/metrics/usage_history.jsonl"
        if [ -f "$HISTORY" ]; then
            echo "Usage history (latest 10 entries):"
            tail -10 "$HISTORY" | python3 -m json.tool
        else
            echo "No usage history found. Run: usage-tracking capture"
        fi
        ;;
    cron-setup)
        # Print cron job setup instructions
        cat << 'EOF'
Add to crontab (crontab -e) to capture usage every 30 minutes:

  # Capture token usage every 30 minutes
  */30 * * * * {workspace-root}/{service-name}/agentic-engineers/orchestration/scripts/capture_token_usage.sh

Or every hour:

  # Capture token usage every hour
  0 * * * * {workspace-root}/{service-name}/agentic-engineers/orchestration/scripts/capture_token_usage.sh

Install with:
  (crontab -l 2>/dev/null; echo "*/30 * * * * {workspace-root}/{service-name}/agentic-engineers/orchestration/scripts/capture_token_usage.sh") | crontab -

View installed cron jobs:
  crontab -l
EOF
        ;;
    *)
        cat << 'EOF'
Usage: usage-tracking <command> [options]

Commands:
  capture              Record current usage state to history log
  analyze [--json]     Show usage trends and analysis
  snapshot             Capture + show current state
  logs                 Show recent raw usage history entries
  cron-setup           Print cron job setup instructions

Examples:
  # Capture a snapshot now
  usage-tracking capture

  # Analyze all captured data
  usage-tracking analyze

  # JSON output for automation
  usage-tracking analyze --json

  # Setup automatic capture every 30 minutes
  usage-tracking cron-setup
EOF
        exit 1
        ;;
esac
