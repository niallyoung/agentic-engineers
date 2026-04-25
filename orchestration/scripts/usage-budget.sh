#!/bin/bash
# Usage Budget Manager — Shell wrapper for budget checking and recommendations
#
# Usage:
#   ./usage-budget.sh --session 91 --weekly 40 --resets-in 1
#   ./usage-budget.sh --check-reset --session 91  # Exit 1 if reset recommended
#   ./usage-budget.sh --json --session 91 --weekly 40
#
# Integration:
#   Called by Orchestrator to check budget before delegating tasks
#   Called every 30 minutes during active sessions
#   Can be invoked by user anytime: "Usage Budget Manager: status"

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/usage_budget_check.py"

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: usage-budget-check.py not found at $PYTHON_SCRIPT"
    exit 1
fi

# Parse arguments
SESSION_PCT=""
WEEKLY_PCT=""
RESETS_IN=""
CHECK_RESET=false
OUTPUT_JSON=false
SHOW_REPORT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --session)
            SESSION_PCT="$2"
            shift 2
            ;;
        --weekly)
            WEEKLY_PCT="$2"
            shift 2
            ;;
        --resets-in)
            RESETS_IN="$2"
            shift 2
            ;;
        --check-reset)
            CHECK_RESET=true
            shift
            ;;
        --json)
            OUTPUT_JSON=true
            shift
            ;;
        --report)
            SHOW_REPORT=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Build Python command
PYTHON_ARGS=()

if [ -n "$SESSION_PCT" ]; then
    PYTHON_ARGS+=(--session-used "$SESSION_PCT")
fi

if [ -n "$WEEKLY_PCT" ]; then
    PYTHON_ARGS+=(--weekly-used "$WEEKLY_PCT")
fi

if [ -n "$RESETS_IN" ]; then
    PYTHON_ARGS+=(--session-resets-in "$RESETS_IN")
fi

if [ "$CHECK_RESET" = true ]; then
    PYTHON_ARGS+=(--check-reset)
fi

if [ "$OUTPUT_JSON" = true ]; then
    PYTHON_ARGS+=(--json)
fi

if [ "$SHOW_REPORT" = true ]; then
    PYTHON_ARGS+=(--report)
fi

# Run Python script
python3 "$PYTHON_SCRIPT" "${PYTHON_ARGS[@]}"
