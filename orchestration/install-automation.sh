#!/bin/bash
# Install all agentic-agents automation into user's crontab
# Safe workflow: shows what will be installed, allows review, then installs

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$SCRIPT_DIR/config"
CRON_FILES=("$CONFIG_DIR"/*.cron)

if [ ! -d "$CONFIG_DIR" ]; then
    echo "❌ Error: config directory not found at $CONFIG_DIR"
    exit 1
fi

if [ ${#CRON_FILES[@]} -eq 0 ]; then
    echo "❌ Error: No .cron files found in $CONFIG_DIR"
    exit 1
fi

echo "╔════════════════════════════════════════════════════════════╗"
echo "║    ERS Agentic Agents — Cron Installation Workflow        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "This script will install the following automation jobs into your crontab:"
echo ""

# Display what will be installed
for CRON_FILE in "${CRON_FILES[@]}"; do
    CRON_NAME=$(basename "$CRON_FILE" .cron)
    echo "  📅 $CRON_NAME"
    # Extract description from comment
    grep "^# " "$CRON_FILE" | head -1 | sed 's/^# /     /'
    echo ""
done

echo "═════════════════════════════════════════════════════════════"
echo ""
echo "Press ENTER to review the cron expressions, or type 'skip' to proceed directly to installation:"
read -p "> " REVIEW_CHOICE

if [ "$REVIEW_CHOICE" != "skip" ]; then
    echo ""
    echo "Cron Schedule Reference:"
    echo "  0 17 * * *  = Every day at 17:00 UTC"
    echo "  0 * * * *   = Every hour on the hour"
    echo ""
    for CRON_FILE in "${CRON_FILES[@]}"; do
        CRON_NAME=$(basename "$CRON_FILE" .cron)
        echo "--- $CRON_NAME ---"
        tail -1 "$CRON_FILE"
        echo ""
    done
fi

echo "═════════════════════════════════════════════════════════════"
echo ""
read -p "Ready to install these jobs to your crontab? [y/N] " CONFIRM

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Installation cancelled."
    exit 0
fi

echo ""
echo "Installing automation jobs..."

# Build combined crontab entry
TEMP_CRONTAB=$(mktemp)
trap "rm -f $TEMP_CRONTAB" EXIT

# Get existing crontab (if any)
crontab -l > "$TEMP_CRONTAB" 2>/dev/null || true

# Add header if this is first installation
if ! grep -q "ERS Agentic Agents" "$TEMP_CRONTAB" 2>/dev/null; then
    echo "" >> "$TEMP_CRONTAB"
    echo "# ═══════════════════════════════════════════════════════════" >> "$TEMP_CRONTAB"
    echo "# ERS Agentic Agents — Automation Framework" >> "$TEMP_CRONTAB"
    echo "# Installed: $(date)" >> "$TEMP_CRONTAB"
    echo "# ═══════════════════════════════════════════════════════════" >> "$TEMP_CRONTAB"
fi

# Add each cron job
for CRON_FILE in "${CRON_FILES[@]}"; do
    CRON_NAME=$(basename "$CRON_FILE" .cron)
    CRON_EXPR=$(tail -1 "$CRON_FILE")

    # Check if already installed (by matching the job name in comment)
    if grep -q "# $CRON_NAME —" "$TEMP_CRONTAB" 2>/dev/null; then
        echo "  ⚠️  $CRON_NAME already installed (skipping)"
        continue
    fi

    # Extract comments and add to crontab
    echo "" >> "$TEMP_CRONTAB"
    grep "^# " "$CRON_FILE" >> "$TEMP_CRONTAB"
    echo "$CRON_EXPR" >> "$TEMP_CRONTAB"
    echo "  ✅ $CRON_NAME installed"
done

# Install the new crontab
crontab "$TEMP_CRONTAB"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    Installation Complete!                 ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Your crontab has been updated. Jobs will begin running at their scheduled times."
echo ""
echo "View your crontab:  crontab -l"
echo "Edit manually:      crontab -e"
echo "Remove all ERS jobs: crontab -l | grep -v 'ERS Agentic' | crontab -"
echo ""
echo "📊 Monitor via: ls -la $SCRIPT_DIR/data/logs/"
echo ""
