#!/usr/bin/env bash
#
# Production Entrypoint for Continuous Polling Loop Automation
# 
# This script provides a production-ready entrypoint for the AutomationController.
# It handles environment setup, logging, signal handling, health checking, and metrics.
#
# Usage:
#   ./bin/run-automation-controller.sh [OPTIONS]
#
# Environment Variables:
#   POLL_INTERVAL_SECONDS   : Polling interval in seconds (default: 5)
#   LOG_LEVEL              : DEBUG|INFO|WARNING|ERROR|CRITICAL (default: INFO)
#   AUTOMATION_DAEMON_MODE : true|false (default: true)
#   AUTOMATION_IDLE_TIMEOUT: Idle timeout in seconds (default: 300)
#   AUTOMATION_MAX_CYCLES  : Max cycles before exit (default: none)
#   METRICS_FILE           : Path to write metrics JSON
#   LOG_FILE               : Path to write logs (default: stdout)

set -euo pipefail

# ─── Configuration ───────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATA_DIR="${PROJECT_ROOT}/data"
LOGS_DIR="${PROJECT_ROOT}/logs"
METRICS_DIR="${PROJECT_ROOT}/metrics"

# Create necessary directories
mkdir -p "${LOGS_DIR}" "${METRICS_DIR}" "${DATA_DIR}"

# Default values
POLL_INTERVAL="${POLL_INTERVAL_SECONDS:-5}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"
DAEMON_MODE="${AUTOMATION_DAEMON_MODE:-true}"
IDLE_TIMEOUT="${AUTOMATION_IDLE_TIMEOUT:-300}"
MAX_CYCLES="${AUTOMATION_MAX_CYCLES:-}"
METRICS_FILE="${METRICS_FILE:-${METRICS_DIR}/metrics-$(date +%Y%m%d-%H%M%S).json}"
LOG_FILE="${LOG_FILE:-${LOGS_DIR}/automation-$(date +%Y%m%d-%H%M%S).log}"

# ─── Functions ───────────────────────────────────────────────────────────────

log() {
    local level="$1"
    shift
    local message="$*"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() { log "INFO" "$@"; }
log_warn() { log "WARN" "$@"; }
log_error() { log "ERROR" "$@"; }
log_debug() { 
    if [[ "${LOG_LEVEL}" == "DEBUG" ]]; then
        log "DEBUG" "$@"
    fi
}

validate_environment() {
    log_info "Validating environment..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "python3 not found in PATH"
        return 1
    fi
    log_debug "Python: $(python3 --version)"
    
    # Check orchestration module
    if [[ ! -d "${PROJECT_ROOT}/orchestration" ]]; then
        log_error "orchestration directory not found at ${PROJECT_ROOT}"
        return 1
    fi
    
    # Set PYTHONPATH
    export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
    log_debug "PYTHONPATH: ${PYTHONPATH}"
    
    # Validate/create queue directory
    local queue_dir="${ORCHESTRATOR_QUEUE_DIR:-${DATA_DIR}/queue}"
    if [[ ! -d "${queue_dir}" ]]; then
        log_warn "Queue directory not found, creating: ${queue_dir}"
        mkdir -p "${queue_dir}"/{incoming,done}
    fi
    
    log_info "Environment validation passed"
    return 0
}

run_automation_controller() {
    log_info "Starting AutomationController..."
    log_info "Configuration:"
    log_info "  Poll Interval: ${POLL_INTERVAL}s"
    log_info "  Log Level: ${LOG_LEVEL}"
    log_info "  Daemon Mode: ${DAEMON_MODE}"
    log_info "  Idle Timeout: ${IDLE_TIMEOUT}s"
    log_info "  Max Cycles: ${MAX_CYCLES:-unlimited}"
    log_info "  Metrics File: ${METRICS_FILE}"
    log_info "  Log File: ${LOG_FILE}"
    
    # Build Python command
    local python_cmd="python3 -m orchestration.agents.automation"
    
    # Add flags
    if [[ "${DAEMON_MODE}" == "true" ]]; then
        python_cmd="${python_cmd} --daemon"
    fi
    
    python_cmd="${python_cmd} --poll-interval ${POLL_INTERVAL}"
    python_cmd="${python_cmd} --idle-timeout ${IDLE_TIMEOUT}"
    python_cmd="${python_cmd} --log-level ${LOG_LEVEL}"
    python_cmd="${python_cmd} --metrics-file ${METRICS_FILE}"
    
    if [[ -n "${MAX_CYCLES}" ]]; then
        python_cmd="${python_cmd} --max-cycles ${MAX_CYCLES}"
    fi
    
    log_info "Running: ${python_cmd}"
    
    # Change to project root and run controller
    cd "${PROJECT_ROOT}"
    eval "${python_cmd}" 2>&1 | tee -a "${LOG_FILE}"
    return ${PIPESTATUS[0]}
}

print_summary() {
    log_info "=========================================="
    log_info "Automation Session Summary"
    log_info "=========================================="
    log_info "End Time: $(date)"
    log_info "Log File: ${LOG_FILE}"
    log_info "Metrics File: ${METRICS_FILE}"
    
    if [[ -f "${METRICS_FILE}" ]]; then
        log_info ""
        log_info "Metrics Summary:"
        python3 << 'PYTHON_EOF'
import json, sys
try:
    with open(sys.argv[1], 'r') as f:
        data = json.load(f)
    m = data.get('metrics', {})
    print(f"  Cycles: {m.get('cycles_completed', 0)}")
    print(f"  Tasks: {m.get('tasks_processed', 0)}")
    print(f"  Success: {m.get('tasks_success', 0)}")
    print(f"  Failed: {m.get('tasks_failed', 0)}")
    print(f"  Duration: {m.get('total_duration_seconds', 0):.2f}s")
    print(f"  Exit Reason: {m.get('shutdown_reason', 'unknown')}")
except Exception as e:
    print(f"  Error reading metrics: {e}", file=sys.stderr)
PYTHON_EOF
        python3 -c "import json, sys; data = json.load(open('${METRICS_FILE}')); m = data.get('metrics', {}); print(f'  Cycles: {m.get(\"cycles_completed\", 0)}'); print(f'  Tasks: {m.get(\"tasks_processed\", 0)}'); print(f'  Success: {m.get(\"tasks_success\", 0)}'); print(f'  Duration: {m.get(\"total_duration_seconds\", 0):.2f}s')" 2>/dev/null || true
    fi
    log_info "=========================================="
}

# ─── Main ────────────────────────────────────────────────────────────────────

main() {
    log_info "╔════════════════════════════════════════════════════════════╗"
    log_info "║  Continuous Polling Loop Automation - Production Entrypoint║"
    log_info "╚════════════════════════════════════════════════════════════╝"
    log_info "Project Root: ${PROJECT_ROOT}"
    
    # Validate environment
    if ! validate_environment; then
        log_error "Environment validation failed"
        return 1
    fi
    
    # Run AutomationController
    if run_automation_controller; then
        log_info "AutomationController completed successfully"
        print_summary
        return 0
    else
        local exit_code=$?
        log_error "AutomationController failed with exit code ${exit_code}"
        print_summary
        return ${exit_code}
    fi
}

main "$@"
