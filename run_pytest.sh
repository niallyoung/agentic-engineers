#!/bin/bash
# pytest wrapper that ensures PYTHONPATH includes repo root
set -e
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"
cd "$REPO_ROOT"
exec python3 -m pytest "$@"
