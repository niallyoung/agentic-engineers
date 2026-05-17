#!/bin/bash
# Safety check: Prevent framework integration without explicit approval
# This script is called by the Orchestrator before creating any framework integration DELEGATEs

set -e

APPROVAL_FILE="FRAMEWORK_INTEGRATION_APPROVED.md"
PAUSE_FILE="FRAMEWORK_INTEGRATION_PAUSE.md"

echo "🔍 Checking framework integration approval status..."

# Check if pause file exists
if [ -f "$PAUSE_FILE" ]; then
    echo "⏸️  Framework integration is PAUSED"
    echo ""
    echo "To opt-in to framework integration:"
    echo "1. Review the research documents (START_HERE.md)"
    echo "2. Create $APPROVAL_FILE with your selections"
    echo "3. Notify the Orchestrator (@orchestrator)"
    echo ""
    echo "See $PAUSE_FILE for detailed instructions"
    exit 1
fi

# Check if approval file exists
if [ ! -f "$APPROVAL_FILE" ]; then
    echo "❌ ERROR: Framework integration not approved"
    echo ""
    echo "To opt-in to framework integration:"
    echo "1. Review the research documents (START_HERE.md)"
    echo "2. Create $APPROVAL_FILE with your selections"
    echo "3. Notify the Orchestrator (@orchestrator)"
    echo ""
    exit 1
fi

# Parse approval file
echo "✅ Framework integration approved"
echo ""
echo "Approved frameworks:"
grep "^-" "$APPROVAL_FILE" | head -10

exit 0
