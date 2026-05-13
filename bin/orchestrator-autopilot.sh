#!/bin/bash
# Orchestrator Autopilot - Continuous queue monitoring and delegation
# This script runs in a loop, checking for new tasks every 60 seconds
# and delegating them to appropriate agents

set -e

QUEUE_INCOMING="$HOME/.copilot/queue/incoming"
QUEUE_PROCESSING="$HOME/.copilot/queue/processing"
QUEUE_DONE="$HOME/.copilot/queue/done"
EMPTY_CHECKS=0
MAX_EMPTY_CHECKS=5

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     🚀 ORCHESTRATOR AUTOPILOT - Queue Monitoring Started      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Status: Ready to accept tasks"
echo "Monitoring: $QUEUE_INCOMING"
echo "Check interval: 60 seconds"
echo "Auto-exit after: $MAX_EMPTY_CHECKS consecutive empty checks"
echo ""

# Create queue directories if they don't exist
mkdir -p "$QUEUE_INCOMING" "$QUEUE_PROCESSING" "$QUEUE_DONE"

while true; do
    CURRENT_TIME=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Check for new tasks in incoming queue
    TASK_COUNT=$(find "$QUEUE_INCOMING" -maxdepth 1 -name "*.json" 2>/dev/null | wc -l)
    
    if [ "$TASK_COUNT" -gt 0 ]; then
        EMPTY_CHECKS=0
        echo "[${CURRENT_TIME}] ✅ Found $TASK_COUNT task(s) in queue - delegating now..."
        
        # List the tasks
        find "$QUEUE_INCOMING" -maxdepth 1 -name "*.json" -type f | while read TASK_FILE; do
            TASK_NAME=$(basename "$TASK_FILE" .json)
            echo "  • Processing: $TASK_NAME"
        done
        
        echo ""
        echo "⚠️  NOTE: Task delegation would happen here via Copilot CLI task routing"
        echo "         (In production, this would invoke: copilot task delegate <task>)"
        echo ""
    else
        EMPTY_CHECKS=$((EMPTY_CHECKS + 1))
        echo "[${CURRENT_TIME}] 📭 Queue empty (check $EMPTY_CHECKS/$MAX_EMPTY_CHECKS)"
        
        if [ "$EMPTY_CHECKS" -ge "$MAX_EMPTY_CHECKS" ]; then
            echo ""
            echo "╔════════════════════════════════════════════════════════════════╗"
            echo "║  📊 Queue monitoring complete - No tasks after $MAX_EMPTY_CHECKS checks  ║"
            echo "║                                                                ║"
            echo "║  Status: IDLE (ready to accept new tasks)                      ║"
            echo "║  Next: Waiting for new incoming queue items                    ║"
            echo "╚════════════════════════════════════════════════════════════════╝"
            break
        fi
    fi
    
    # Wait 60 seconds before next check
    sleep 60
done

echo ""
echo "✅ Orchestrator autopilot loop completed"
