#!/usr/bin/env bash
# copilot-session-init.sh — sessionStart hook for Copilot CLI
# Runs at the start of every Copilot session to initialize context.
set -euo pipefail

echo "=== ERS Session Init ==="
echo ""
echo "🔒 Enforcement active:"
echo "   - preToolUse guard blocks --no-verify, destructive ops, hook tampering"
echo "   - Git hooks delegate to Makefile targets"
echo "   - All commits must pass hooks"
echo ""
echo "=== Init Complete ==="
