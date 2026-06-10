#!/bin/bash
# Create a test session with sample DELEGATE for queue testing
#
# Usage:
#   bash setup/create-test-session.sh [--session-id SESSION_ID] [--harness HARNESS]
#   AGENTIC_SESSION_ID=test-001 AGENTIC_HARNESS=local bash setup/create-test-session.sh
#
# Environment variables (optional):
#   AGENTIC_SESSION_ID  — Session ID (UUID or test name). Defaults: auto-generated
#   AGENTIC_HARNESS     — Harness name (claude|copilot|opencode|pi|local). Defaults: local
#
# Creates:
#   ~/.agentic-engineers/{session-id}/{harness}/queue/{incoming,processing,done,failed}/
#   ~/.agentic-engineers/{session-id}/{harness}/queue/incoming/{task-id}.yaml (sample DELEGATE)

set -euo pipefail

# Parse arguments or use environment variables
SESSION_ID="${AGENTIC_SESSION_ID:-}"
HARNESS="${AGENTIC_HARNESS:-local}"

# Default to auto-generated session ID if not provided
if [ -z "$SESSION_ID" ]; then
    SESSION_ID="test-$(date +%s)"
    echo "Generated session ID: $SESSION_ID"
fi

# Validate harness name
case "$HARNESS" in
    claude|copilot|opencode|pi|local)
        : # Valid
        ;;
    *)
        echo "ERROR: Invalid harness '$HARNESS'. Must be one of: claude, copilot, opencode, pi, local" >&2
        exit 1
        ;;
esac

# Create queue directories
QUEUE_ROOT="$HOME/.agentic-engineers/$SESSION_ID/$HARNESS/queue"
mkdir -p "$QUEUE_ROOT/incoming"
mkdir -p "$QUEUE_ROOT/processing"
mkdir -p "$QUEUE_ROOT/done"
mkdir -p "$QUEUE_ROOT/failed"

echo "✓ Created queue directories:"
echo "  $QUEUE_ROOT/incoming"
echo "  $QUEUE_ROOT/processing"
echo "  $QUEUE_ROOT/done"
echo "  $QUEUE_ROOT/failed"

# Generate sample DELEGATE task ID
TASK_ID="test-session-sample-task-$(date +%s)"

# Create sample DELEGATE in canonical schema
cat > "$QUEUE_ROOT/incoming/${TASK_ID}.yaml" << 'EOF'
---
handoff_type: DELEGATE
task_id: test-session-sample-task
agent: engineer
model: claude-haiku-4.5
effort: high
scope: >
  Test implementation task.
  Verify that the agentic-engineers queue system correctly routes DELEGATE blocks
  from incoming/ queue to agents and collects HANDBACK responses.
context: |
  This is a sample DELEGATE for testing queue mechanics.
  It demonstrates the canonical DELEGATE schema.
plan:
  - Acknowledge receipt of DELEGATE
  - Verify session and harness are correct
  - Return HANDBACK with success status
success_criteria:
  - DELEGATE is valid YAML
  - DELEGATE conforms to schema
  - Session-ID and harness are detected correctly
  - HANDBACK is returned to processing/ queue
estimated_tokens: 500
---
EOF

echo "✓ Created sample DELEGATE:"
echo "  $QUEUE_ROOT/incoming/${TASK_ID}.yaml"

echo ""
echo "✅ Test session created successfully!"
echo ""
echo "Session details:"
echo "  Session ID:  $SESSION_ID"
echo "  Harness:     $HARNESS"
echo "  Queue root:  $QUEUE_ROOT"
echo "  Task ID:     $TASK_ID"
echo ""
echo "Verify with:"
echo "  ls $QUEUE_ROOT/incoming/"
echo "  cat $QUEUE_ROOT/incoming/${TASK_ID}.yaml"
echo ""
echo "Next steps:"
echo "  1. Run orchestrator polling: orchestrator-poll --session $SESSION_ID --harness $HARNESS"
echo "  2. Monitor queue: ls $QUEUE_ROOT/processing/"
echo "  3. Check completion: ls $QUEUE_ROOT/done/"
