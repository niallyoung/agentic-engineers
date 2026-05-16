#!/usr/bin/env bash
# copilot-guard.sh — preToolUse hook for Copilot CLI
# Reads JSON from stdin, outputs permission decision JSON to stdout.
# Enforced by the CLI runtime — the LLM cannot bypass this.
set -euo pipefail

INPUT=$(cat)
TOOL=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool',''))" 2>/dev/null || echo "")
ARGS=$(echo "$INPUT" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin).get('args',{})))" 2>/dev/null || echo "{}")

deny() {
  echo "{\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"$1\"}"
  exit 0
}

ask() {
  echo "{\"permissionDecision\":\"ask\",\"permissionDecisionReason\":\"$1\"}"
  exit 0
}

allow() {
  echo "{\"permissionDecision\":\"allow\"}"
  exit 0
}

if [ "$TOOL" = "bash" ]; then
  CMD=$(echo "$ARGS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('command',''))" 2>/dev/null || echo "")

  # Block --no-verify on any git command
  if echo "$CMD" | grep -qE '(--no-verify|--no-gpg-sign.*--no-verify)'; then
    deny "BLOCKED: --no-verify is prohibited. Commit hooks must run."
  fi

  # Block destructive rm on root paths
  if echo "$CMD" | grep -qE 'rm\s+(-rf|-fr)\s+/'; then
    deny "BLOCKED: Destructive rm -rf on root paths is prohibited."
  fi

  # Block modifications to global enforcement infrastructure
  if echo "$CMD" | grep -qE '(rm|mv|cp.*>)\s+.*\.githooks/'; then
    deny "BLOCKED: Cannot modify .githooks/ — enforcement infrastructure is protected."
  fi

  # Prompt on force push
  if echo "$CMD" | grep -qE 'git\s+push\s+.*--force'; then
    ask "Force push detected. Are you sure?"
  fi
fi

# Block edits to hook and guard files
if [ "$TOOL" = "edit" ] || [ "$TOOL" = "create" ]; then
  FILEPATH=$(echo "$ARGS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('path',''))" 2>/dev/null || echo "")
  if echo "$FILEPATH" | grep -qE '\.githooks/'; then
    deny "BLOCKED: Cannot edit .githooks/ files — enforcement infrastructure is protected."
  fi
fi

allow
