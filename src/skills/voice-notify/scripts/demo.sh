#!/bin/bash
# Voice-Notify Demo — Showcase all agents and voice options
# Run this to hear each agent's notifications with different voices

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VOICE_NOTIFY="$SCRIPT_DIR/voice-notify.sh"

if [ ! -f "$VOICE_NOTIFY" ]; then
    echo "❌ Error: voice-notify.sh not found at $VOICE_NOTIFY"
    exit 1
fi

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║           Voice-Notify Demo — All Agents & Voices            ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "This demo shows voice notifications from each automation agent."
echo "Listen to the agent status updates with different voice options."
echo ""

# Function to run a demo notification
demo_notification() {
    local agent=$1
    local message=$2
    local voice=$3

    echo "🔊 [$agent] Voice: $voice"
    echo "   Message: \"$message\""
    bash "$VOICE_NOTIFY" "$message" --voice "$voice"
    sleep 2
    echo ""
}

echo "═════════════════════════════════════════════════════════════════"
echo ""
echo "DEMO 1: TokenAdvisor (Monitoring Agent)"
echo "─────────────────────────────────────────"
echo "Role: Orchestrator"
echo "Time: 17:00 UTC daily"
echo ""

demo_notification "TokenAdvisor" \
    "TokenAdvisor complete. Distribution healthy." \
    "Builder"

demo_notification "TokenAdvisor" \
    "Engineer over budget by 3 percent." \
    "Victoria"

demo_notification "TokenAdvisor" \
    "Escalation spike detected. Review routing." \
    "Samantha"

echo "═════════════════════════════════════════════════════════════════"
echo ""
echo "DEMO 2: Model Engineer (Optimization Agent)"
echo "──────────────────────────────────────────"
echo "Role: Senior Engineer"
echo "Time: 17:15 UTC daily"
echo ""

demo_notification "Model Engineer" \
    "Model Engineer ready. Route low complexity tasks to Engineer." \
    "Builder"

demo_notification "Model Engineer" \
    "Test variant. Reduce Senior allocation by 10 percent." \
    "Victoria"

demo_notification "Model Engineer" \
    "Upgrade to Sonnet on high complexity tasks recommended." \
    "Alex"

echo "═════════════════════════════════════════════════════════════════"
echo ""
echo "DEMO 3: A/B Testing Monitor (Experimentation Agent)"
echo "───────────────────────────────────────────────────"
echo "Role: Lead Engineer"
echo "Time: 18:00 UTC daily"
echo ""

demo_notification "A/B Testing" \
    "A/B test Engineer allocation. In progress." \
    "Builder"

demo_notification "A/B Testing" \
    "Significant result. Variant winning. P equals 0.03." \
    "Victoria"

demo_notification "A/B Testing" \
    "Early stop. Regression detected. Control is better." \
    "Samantha"

demo_notification "A/B Testing" \
    "Complete. Variant wins. Ready for deployment." \
    "Alex"

echo "═════════════════════════════════════════════════════════════════"
echo ""
echo "DEMO 4: Daily Email Summary (Reporting Agent)"
echo "──────────────────────────────────────────────"
echo "Role: Orchestrator"
echo "Time: 22:00 UTC daily"
echo ""

demo_notification "Daily Summary" \
    "Daily summary ready. 47 commits. 8 features shipped." \
    "Builder"

demo_notification "Daily Summary" \
    "Plus 1200 lines added. Test coverage up to 87 percent." \
    "Victoria"

echo "═════════════════════════════════════════════════════════════════"
echo ""
echo "DEMO 5: Voice Options Comparison"
echo "────────────────────────────────"
echo "Same message, different voices:"
echo ""

MESSAGE="Automation framework ready for deployment."

echo "Builder (default, recommended for alerts):"
demo_notification "Voice Test" "$MESSAGE" "Builder"

echo "Victoria (professional female):"
demo_notification "Voice Test" "$MESSAGE" "Victoria"

echo "Samantha (high quality female):"
demo_notification "Voice Test" "$MESSAGE" "Samantha"

echo "Alex (casual male):"
demo_notification "Voice Test" "$MESSAGE" "Alex"

echo "═════════════════════════════════════════════════════════════════"
echo ""
echo "✅ Demo Complete!"
echo ""
echo "Summary:"
echo "  • TokenAdvisor (17:00) — Cost/distribution monitoring"
echo "  • Model Engineer (17:15) — Routing recommendations"
echo "  • A/B Testing (18:00) — Experiment results"
echo "  • Daily Summary (22:00) — Activity reporting"
echo "  • Metrics ETL (hourly) — Silent background job"
echo ""
echo "Voice options:"
echo "  • Builder (deep, confident male) — Best for alerts"
echo "  • Victoria (professional female)"
echo "  • Samantha (high quality female)"
echo "  • Alex (casual male)"
echo ""
echo "To use in your cron jobs:"
echo "  bash voice-notify.sh \"Your message\" --voice Builder"
echo ""
