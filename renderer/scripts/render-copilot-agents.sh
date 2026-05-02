#!/bin/bash
# Render Copilot CLI agents from src/agents to ~/.copilot/agents
# This script converts canonical agent definitions to Copilot CLI format

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
SRC_AGENTS="$PROJECT_ROOT/src/agents"
DEST_AGENTS="${COPILOT_HOME:-$HOME/.copilot}/agents"

echo ""
echo "🎨 Rendering Copilot CLI Agents"
echo "==============================="
echo ""

# Check source exists
if [ ! -d "$SRC_AGENTS" ]; then
    echo "❌ Error: Source agents directory not found: $SRC_AGENTS"
    exit 1
fi

# Run Python renderer
python3 "$PROJECT_ROOT/renderer/scripts/render-copilot-agents.py" "$SRC_AGENTS" "$DEST_AGENTS"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ Copilot CLI agents rendered successfully!"
    echo "📁 Location: $DEST_AGENTS"
    echo ""
    echo "To use:"
    echo "  copilot --agent=engineer --prompt '...'"
    echo "  /agent  # Select in interactive mode"
    echo ""
fi

exit $EXIT_CODE
