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

# Installer + test dependencies. Failures here are deliberately NON-fatal (the
# render below can still succeed with what is installed) but never silent: the
# underlying tool's own output is replayed to stderr behind a WARNING line.
if ! command -v rsync >/dev/null 2>&1; then
  if ! rsync_out=$(apt-get install -y -qq rsync 2>&1 \
      || { apt-get update -qq 2>&1 && apt-get install -y -qq rsync 2>&1; }); then
    echo "session-start: WARNING could not install rsync (continuing):" >&2
    printf '%s\n' "$rsync_out" | sed 's/^/  /' >&2
  fi
fi
# pyyaml is pinned to the major range scripts/models.py is written against.
if ! pip_out=$(python3 -m pip install -q pytest 'pyyaml>=6.0,<7' 2>&1); then
  echo "session-start: WARNING could not install python deps (continuing):" >&2
  printf '%s\n' "$pip_out" | sed 's/^/  /' >&2
fi

# Render + install agents/skills into ~/.claude (marker-aware, never clobbers foreign files)
make install-claude
