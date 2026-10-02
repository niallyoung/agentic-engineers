#!/bin/bash
# SessionStart hook: initialise the agentic-engineers framework (AGENTS with
# SKILLS) in Claude Code cloud sessions by running `make install-claude`, which
# renders src/agents + src/skills into the container's ~/.claude/.
# Remote-only: local clients keep their own ~/.claude install. Idempotent.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Installer + test dependencies
if ! command -v rsync >/dev/null 2>&1; then
  (apt-get install -y -qq rsync >/dev/null 2>&1 \
    || { apt-get update -qq >/dev/null 2>&1 && apt-get install -y -qq rsync >/dev/null 2>&1; }) \
    || echo "session-start: could not install rsync" >&2
fi
python3 -m pip install -q pytest "pyyaml>=6.0" >/dev/null 2>&1 \
  || echo "session-start: could not install python deps" >&2

# Render + install agents/skills into ~/.claude (marker-aware, never clobbers foreign files)
make install-claude
