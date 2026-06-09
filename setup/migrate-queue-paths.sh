#!/usr/bin/env bash

################################################################################
# migrate-queue-paths.sh — Migrate queue sessions from old to canonical paths
#
# Migrates existing queue sessions from:
#   OLD: ~/.agentic-engineers/artifacts/{session-id}/{harness}/queue/
# TO:
#   NEW: ~/.agentic-engineers/{session-id}/{harness}/queue/
#
# The script:
# - Scans ~/.agentic-engineers/artifacts/ for session directories
# - Moves artifacts/{session-id}/{harness}/ → ~/.agentic-engineers/{session-id}/{harness}/
# - Preserves all queue subdirs (incoming/, processing/, done/, failed/)
# - Prints a summary of what was moved
# - Leaves artifacts/ dir empty (but with a README warning it's deprecated)
# - Is idempotent (safe to run twice)
# - Exits 0 on success, 1 on failure
################################################################################

set -eu

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AGENTIC_HOME="${HOME}/.agentic-engineers"
ARTIFACTS_DIR="${AGENTIC_HOME}/artifacts"
MIGRATION_COUNT=0
SKIPPED_COUNT=0
ERROR_COUNT=0

################################################################################
# Logging functions
################################################################################

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

################################################################################
# Main migration function
################################################################################

migrate_session_dir() {
    local session_dir="$1"
    local session_id
    session_id=$(basename "$session_dir")

    # Scan for harness subdirectories
    if [ ! -d "$session_dir" ]; then
        log_warn "Session dir does not exist: $session_dir"
        return 1
    fi

    local harness_count=0
    for harness_dir in "$session_dir"/*; do
        [ -d "$harness_dir" ] || continue

        local harness
        harness=$(basename "$harness_dir")

        # Check if this is a queue directory (contains queue subdir)
        if [ ! -d "$harness_dir/queue" ]; then
            log_warn "No queue subdir found in $harness_dir (skipping)"
            ((SKIPPED_COUNT++))
            continue
        fi

        # Build canonical paths
        local canonical_base="${AGENTIC_HOME}/${session_id}/${harness}"

        # Check if already migrated
        if [ -d "$canonical_base" ]; then
            log_warn "Already migrated: ${session_id}/${harness} (skipping)"
            ((SKIPPED_COUNT++))
            continue
        fi

        # Create parent dirs for canonical path
        mkdir -p "$(dirname "$canonical_base")"

        # Move entire harness directory to canonical location
        log_info "Migrating: artifacts/${session_id}/${harness}/ → ${session_id}/${harness}/"
        if mv "$harness_dir" "$canonical_base"; then
            ((MIGRATION_COUNT++))
            ((harness_count++))
        else
            log_error "Failed to migrate: $harness_dir"
            ((ERROR_COUNT++))
            return 1
        fi
    done

    # After moving all harnesses, remove empty session dir
    if [ -d "$session_dir" ] && [ ! "$(ls -A "$session_dir")" ]; then
        rmdir "$session_dir" 2>/dev/null || true
    fi

    return 0
}

################################################################################
# Main script
################################################################################

main() {
    log_info "Starting queue path migration..."
    echo ""

    # Check if artifacts directory exists
    if [ ! -d "$ARTIFACTS_DIR" ]; then
        log_info "No artifacts directory found at $ARTIFACTS_DIR (nothing to migrate)"
        echo ""
        log_info "Migration complete (0 sessions migrated)"
        exit 0
    fi

    # Scan all session directories in artifacts/
    local session_found=0
    for session_dir in "$ARTIFACTS_DIR"/*; do
        [ -d "$session_dir" ] || continue
        ((session_found++))
        migrate_session_dir "$session_dir"
    done

    # Check if artifacts dir is now empty
    if [ ! "$(ls -A "$ARTIFACTS_DIR")" ]; then
        log_info "Artifacts directory is now empty (leaving in place as deprecated)"

        # Create deprecation notice
        cat > "$ARTIFACTS_DIR/README.md" << 'EOF'
# DEPRECATED: artifacts/ Directory

This directory is no longer used. Queue paths have been migrated to:
```
~/.agentic-engineers/{session-id}/{harness}/queue/
```

The old path structure (`artifacts/`) is kept for historical reference but is
no longer the canonical location. You can safely delete this directory.

See setup/migrate-queue-paths.sh for migration details.
EOF

        log_info "Added deprecation notice to $ARTIFACTS_DIR/README.md"
    fi

    echo ""
    echo "================================ Migration Summary ================================"
    echo "Sessions scanned:        $session_found"
    echo "Migrations completed:    $MIGRATION_COUNT"
    echo "Skipped (already done):  $SKIPPED_COUNT"
    echo "Errors:                  $ERROR_COUNT"
    echo "================================================================================="
    echo ""

    # Exit with error if any failures occurred
    if [ "$ERROR_COUNT" -gt 0 ]; then
        log_error "Migration completed with $ERROR_COUNT error(s)"
        exit 1
    fi

    if [ "$MIGRATION_COUNT" -eq 0 ] && [ "$session_found" -eq 0 ]; then
        log_info "Nothing to migrate (artifacts directory was empty)"
    elif [ "$MIGRATION_COUNT" -eq 0 ]; then
        log_info "All sessions already migrated (no changes needed)"
    else
        log_info "Migration successful! $MIGRATION_COUNT session(s) migrated"
    fi

    exit 0
}

main "$@"
