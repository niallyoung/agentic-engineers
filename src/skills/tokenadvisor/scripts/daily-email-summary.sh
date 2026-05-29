#!/bin/bash
# Daily Email Summary — 24h activity report across services

set -euo pipefail

WORKSPACE_DIR="/home/user/git/ers"
REPORT_DIR="/home/user/git/ers/{workspace-name}/agentic-agents/data/reports"
TODAY=$(date +%Y-%m-%d)
REPORT_FILE="$REPORT_DIR/daily-summary-$TODAY.html"

mkdir -p "$REPORT_DIR"

# Repositories to scan
REPOS=(
    "{service-name}"
    "{service-name}"
    "{service-name}"
    "{service-name}"
    "{service-name}"
    "{service-name}"
    "{service-name}"
    "{service-name}"
    "{service-name}"
    "{service-name}"
)

echo "=== Daily Summary Report — $TODAY ===" > "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

TOTAL_COMMITS=0
TOTAL_LOC_ADDED=0
TOTAL_LOC_REMOVED=0
FEATURES_COUNT=0
FIX_COUNT=0

# Process each repo
for REPO in "${REPOS[@]}"; do
    REPO_PATH="$WORKSPACE_DIR/$REPO"
    if [ ! -d "$REPO_PATH/.git" ]; then
        continue
    fi

    echo "## $REPO" >> "$REPORT_FILE"

    # Get commits in last 24 hours
    COMMITS=$(cd "$REPO_PATH" && git log --oneline --since="24 hours ago" --decorate 2>/dev/null | wc -l)
    if [ "$COMMITS" -gt 0 ]; then
        TOTAL_COMMITS=$((TOTAL_COMMITS + COMMITS))
        echo "**Commits:** $COMMITS" >> "$REPORT_FILE"

        # Get commit messages
        cd "$REPO_PATH"
        git log --oneline --since="24 hours ago" 2>/dev/null | while read line; do
            echo "- $line" >> "$REPORT_FILE"

            # Count feature/fix commits
            if [[ "$line" =~ "feat:" ]]; then
                FEATURES_COUNT=$((FEATURES_COUNT + 1))
            elif [[ "$line" =~ "fix:" ]]; then
                FIX_COUNT=$((FIX_COUNT + 1))
            fi
        done
    fi

    # Get LOC changes in last 24 hours
    LOC_STAT=$(cd "$REPO_PATH" && git diff --stat HEAD~1..HEAD 2>/dev/null || echo "0 files changed, 0 insertions(+), 0 deletions(-)")
    if [[ "$LOC_STAT" =~ ([0-9]+)\ insertion ]]; then
        ADDED="${BASH_REMATCH[1]}"
        TOTAL_LOC_ADDED=$((TOTAL_LOC_ADDED + ADDED))
    fi
    if [[ "$LOC_STAT" =~ ([0-9]+)\ deletion ]]; then
        REMOVED="${BASH_REMATCH[1]}"
        TOTAL_LOC_REMOVED=$((TOTAL_LOC_REMOVED + REMOVED))
    fi

    echo "" >> "$REPORT_FILE"
done

# Summary section
echo "## Summary" >> "$REPORT_FILE"
echo "- **Total Commits:** $TOTAL_COMMITS" >> "$REPORT_FILE"
echo "- **Features Shipped:** $FEATURES_COUNT" >> "$REPORT_FILE"
echo "- **Bugs Fixed:** $FIX_COUNT" >> "$REPORT_FILE"
echo "- **LOC Added:** +$TOTAL_LOC_ADDED" >> "$REPORT_FILE"
echo "- **LOC Removed:** -$TOTAL_LOC_REMOVED" >> "$REPORT_FILE"
echo "- **Net Change:** +$((TOTAL_LOC_ADDED - TOTAL_LOC_REMOVED))" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "Report generated: $REPORT_FILE"

# Voice notification
if [ "$TOTAL_COMMITS" -gt 0 ]; then
    /bin/bash "$(dirname "$0")/voice-notify.sh" "Daily summary ready. $TOTAL_COMMITS commits, $FEATURES_COUNT features shipped." --volume 0.7
else
    /bin/bash "$(dirname "$0")/voice-notify.sh" "Daily summary: No commits in the last 24 hours." --volume 0.7
fi

exit 0
