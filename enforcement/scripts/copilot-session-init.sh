#!/usr/bin/env bash
# copilot-session-init.sh — sessionStart hook for Copilot CLI
# Runs at the start of every Copilot session to initialize context.
set -euo pipefail

VOICE_SCRIPT="$HOME/.copilot/scripts/voice-notify.sh"

echo "=== ERS Session Init ==="
echo ""

if [ -x "$VOICE_SCRIPT" ]; then
  echo "✅ Voice-notify available. Character roster:"
  echo "   Scout (explore) | Builder (task) | Oracle (general) | Inspector (review)"
  echo "   Architect (plan) | Cheer (success) | Gloom (error)"
  echo ""
  echo "INSTRUCTION: Use varied character voices. Match agent type to character."
else
  echo "⚠️  Voice-notify not found at $VOICE_SCRIPT"
fi

echo ""
echo "🔒 Enforcement active:"
echo "   - preToolUse guard blocks --no-verify, destructive ops, hook tampering"
echo "   - Git hooks delegate to Makefile targets"
echo "   - All commits must pass hooks"
echo ""
echo "=== Init Complete ==="
