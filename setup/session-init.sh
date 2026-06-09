#!/bin/bash
# Session initialization wrapper — invokes agentic-engineers startup sequence
#
# Called by: Claude Code CLI, Copilot extensions, or any CLI harness
# Purpose: Initialize agentic-engineers framework at session start
# Idempotent: Safe to call multiple times during startup
#
# Usage:
#   bash agentic-engineers/setup/session-init.sh
#   source agentic-engineers/setup/session-init.sh  # In shell startup scripts
#
# Integration:
#   - Claude Code: Runs automatically if present
#   - Copilot: Invoked from copilot-instructions.md
#   - .claude/hooks: Called on session init
#   - .zshrc/.bashrc: Can be sourced for automatic startup

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTIC_ENGINEERS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Verify we're in the right location
if [ ! -f "$AGENTIC_ENGINEERS_ROOT/README.md" ]; then
    echo "ERROR: agentic-engineers framework not found at $AGENTIC_ENGINEERS_ROOT" >&2
    exit 1
fi

# ============================================================================
# Session Initialization Sequence
# ============================================================================

# 1. Load copilot instructions (static configuration)
#    This ensures all agents understand the framework rules
if [ -f "$AGENTIC_ENGINEERS_ROOT/setup/copilot-instructions.md" ]; then
    : # Instructions are for documentation; loaded implicitly by LLMs
fi

# 2. Initialize usage tracking (automatic during session)
#    This enables continuous token monitoring without explicit agent action
if [ -f "$AGENTIC_ENGINEERS_ROOT/skills/usage-tracking/SESSION-INIT.sh" ]; then
    bash "$AGENTIC_ENGINEERS_ROOT/skills/usage-tracking/SESSION-INIT.sh"
fi

# 3. Install git hooks
#    This ensures pre-commit and pre-push hooks are active
if [ -d "$AGENTIC_ENGINEERS_ROOT/.githooks" ]; then
    for hook in "$AGENTIC_ENGINEERS_ROOT"/.githooks/*; do
        if [ -f "$hook" ]; then
            git -C "$AGENTIC_ENGINEERS_ROOT" config core.hooksPath .githooks
            if [ ! -x "$hook" ]; then
                chmod +x "$hook"
            fi
        fi
    done
fi

# 4. Verify framework readiness
if [ ! -d "$AGENTIC_ENGINEERS_ROOT/src/orchestration" ] || \
   [ ! -f "$AGENTIC_ENGINEERS_ROOT/src/AGENTS.md" ]; then
    echo "WARNING: agentic-engineers framework incomplete" >&2
    exit 1
fi

# ============================================================================
# Initialization Complete
# ============================================================================

exit 0
