#!/usr/bin/env bash
# run-automation-controller.sh — entrypoint for AutomationController
#
# Usage:
#   ./bin/run-automation-controller.sh [options]
#
# Environment variables:
#   QUEUE_DIR       — path to queue directory (default: ~/.copilot/queue)
#   POLL_INTERVAL   — seconds between polls (default: 10)
#   IDLE_TIMEOUT    — seconds idle before exit (default: 60)
#   DAEMON_MODE     — run as daemon without idle timeout (default: false)
#   LOG_LEVEL       — logging level: DEBUG|INFO|WARNING|ERROR (default: INFO)
#   MAX_CYCLES      — maximum poll cycles before exit (default: unlimited)
#   METRICS_FILE    — path to write metrics JSON (default: none)

set -euo pipefail

# Resolve project root (directory containing this script's parent)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Defaults
QUEUE_DIR="${QUEUE_DIR:-${HOME}/.copilot/queue}"
POLL_INTERVAL="${POLL_INTERVAL:-10}"
IDLE_TIMEOUT="${IDLE_TIMEOUT:-60}"
DAEMON_MODE="${DAEMON_MODE:-false}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"
MAX_CYCLES="${MAX_CYCLES:-}"
METRICS_FILE="${METRICS_FILE:-}"

# Help
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    sed -n '2,15p' "$0" | sed 's/^# //'
    exit 0
fi

cd "${PROJECT_ROOT}"

# Build args
ARGS=(
    --queue-dir "${QUEUE_DIR}"
    --poll-interval "${POLL_INTERVAL}"
    --idle-timeout "${IDLE_TIMEOUT}"
    --log-level "${LOG_LEVEL}"
)

[[ "${DAEMON_MODE}" == "true" ]] && ARGS+=(--daemon)
[[ -n "${MAX_CYCLES}" ]] && ARGS+=(--max-cycles "${MAX_CYCLES}")
[[ -n "${METRICS_FILE}" ]] && ARGS+=(--metrics-file "${METRICS_FILE}")

exec python3 -m src.orchestration.agents.automation "${ARGS[@]}"
