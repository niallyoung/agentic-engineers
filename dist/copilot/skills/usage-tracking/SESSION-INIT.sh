#!/bin/bash
# Initialize automatic token usage tracking for the session
# Idempotent: safe to call multiple times during session startup
# Call this at session start to enable continuous monitoring

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTIC_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TRACKING_STATE_FILE="${AGENTIC_ROOT}/.session-state/current-session-initialized"

# Check if already initialized this session (idempotent)
if [ -f "$TRACKING_STATE_FILE" ]; then
    # Session tracking already initialized, skip
    exit 0
fi

echo "🎬 Initializing token usage tracking for session..."

# 1. Capture baseline
echo "📊 Capturing baseline usage..."
bash "$SCRIPT_DIR/scripts/capture_token_usage.sh" --silent

# 2. Show initial status
echo ""
echo "📈 Initial Status:"
bash "$SCRIPT_DIR/scripts/usage-tracking.sh" analyze | head -20

# 3. Setup optional cron background capture (if on macOS/Linux with cron)
if command -v crontab &>/dev/null && [ -z "${SKIP_CRON:-}" ]; then
    echo ""
    echo "⏰ Optional: Setup background capture every 30 minutes?"
    echo "   (This will create a cron job for continuous monitoring)"
    echo ""
    echo "   Command to run:"
    echo "   bash $SCRIPT_DIR/scripts/usage-tracking.sh cron-setup | bash"
    echo ""
    echo "   Or skip: export SKIP_CRON=1"
fi

echo ""
echo "✅ Session initialization complete."
echo ""
echo "During session, automatically capture at:"
echo "  • Before major DELEGATE blocks (Orchestrator)"
echo "  • Every 30-minute checkpoint (Orchestrator)"
echo "  • In HANDBACK metrics (all agents)"
echo ""
echo "Quick commands:"
echo "  bash skills/usage-tracking/scripts/usage-tracking.sh snapshot  # Capture + analyze"
echo "  bash skills/usage-tracking/scripts/usage-tracking.sh analyze   # Show trends"
echo ""

# Mark session as initialized (idempotent)
mkdir -p "$(dirname "$TRACKING_STATE_FILE")"
touch "$TRACKING_STATE_FILE"
