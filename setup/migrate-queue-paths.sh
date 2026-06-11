#!/usr/bin/env bash

################################################################################
# migrate-queue-paths.sh — Migrate queue sessions from old to canonical paths
#
# Migrates existing queue sessions from:
#   OLD: ~/.agentic-engineers/artifacts/{session-id}/{harness}/queue/
# TO:
#   NEW: ~/.agentic-engineers/{harness}/{session-id}/queue/
#
# Harness-first ordering: operators browse by harness name, not by opaque
# session UUID, and session IDs cannot collide across harnesses.
#
# The script:
# - Scans ~/.agentic-engineers/artifacts/ for session directories
# - Moves artifacts/{session-id}/{harness}/ → ~/.agentic-engineers/{harness}/{session-id}/
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
            SKIPPED_COUNT=$((SKIPPED_COUNT+1))
            continue
        fi

        # Build canonical paths (harness-first: humans index by harness, not UUID)
        local canonical_base="${AGENTIC_HOME}/${harness}/${session_id}"

        # Check if already migrated
        if [ -d "$canonical_base" ]; then
            log_warn "Already migrated: ${session_id}/${harness} (skipping)"
            SKIPPED_COUNT=$((SKIPPED_COUNT+1))
            continue
        fi

        # Create parent dirs for canonical path
        mkdir -p "$(dirname "$canonical_base")"

        # Move entire harness directory to canonical location
        log_info "Migrating: artifacts/${session_id}/${harness}/ → ${harness}/${session_id}/"
        if mv "$harness_dir" "$canonical_base"; then
            MIGRATION_COUNT=$((MIGRATION_COUNT+1))
            harness_count=$((harness_count+1))
        else
            log_error "Failed to migrate: $harness_dir"
            ERROR_COUNT=$((ERROR_COUNT+1))
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
# Reversal pass: flip legacy {session-id}/{harness}/ to {harness}/{session-id}/
#
# Installs that already dropped the artifacts/ prefix sit at the top level as
# ~/.agentic-engineers/{session-id}/{harness}/queue/. The canonical order is now
# harness-first, so move each such session dir to {harness}/{session-id}/.
################################################################################

KNOWN_HARNESSES="copilot claude opencode pi local gpt"

is_known_harness() {
    local name="$1"
    case " $KNOWN_HARNESSES " in
        *" $name "*) return 0 ;;
        *) return 1 ;;
    esac
}

reverse_session_first_dirs() {
    [ -d "$AGENTIC_HOME" ] || return 0

    for candidate in "$AGENTIC_HOME"/*; do
        [ -d "$candidate" ] || continue
        local name
        name=$(basename "$candidate")

        # Skip harness-first dirs (already canonical), artifacts/, and non-session bookkeeping
        is_known_harness "$name" && continue
        [ "$name" = "artifacts" ] && continue
        [ "$name" = "rate-limits" ] && continue
        case "$name" in .*) continue ;; esac

        # A session-first dir contains one or more harness subdirs holding queue/
        local has_harness_child=0
        for harness_dir in "$candidate"/*; do
            [ -d "$harness_dir" ] || continue
            local harness
            harness=$(basename "$harness_dir")
            is_known_harness "$harness" || continue
            [ -d "$harness_dir/queue" ] || continue
            has_harness_child=1

            local canonical_base="${AGENTIC_HOME}/${harness}/${name}"
            if [ -d "$canonical_base" ]; then
                log_warn "Already reversed: ${harness}/${name} (skipping)"
                SKIPPED_COUNT=$((SKIPPED_COUNT+1))
                continue
            fi
            mkdir -p "$(dirname "$canonical_base")"
            log_info "Reversing: ${name}/${harness}/ → ${harness}/${name}/"
            if mv "$harness_dir" "$canonical_base"; then
                MIGRATION_COUNT=$((MIGRATION_COUNT+1))
            else
                log_error "Failed to reverse: $harness_dir"
                ERROR_COUNT=$((ERROR_COUNT+1))
                return 1
            fi
        done

        # Remove the now-empty session-first dir
        if [ "$has_harness_child" -eq 1 ] && [ ! "$(ls -A "$candidate" 2>/dev/null)" ]; then
            rmdir "$candidate" 2>/dev/null || true
        fi
    done
    return 0
}

################################################################################
# Main script
################################################################################

main() {
    log_info "Starting queue path migration..."
    echo ""

    local session_found=0

    # Pass 1 — migrate legacy artifacts/{session}/{harness}/ → {harness}/{session}/
    if [ -d "$ARTIFACTS_DIR" ]; then
        for session_dir in "$ARTIFACTS_DIR"/*; do
            [ -d "$session_dir" ] || continue
            session_found=$((session_found+1))
            migrate_session_dir "$session_dir"
        done
    else
        log_info "No artifacts directory at $ARTIFACTS_DIR (skipping artifacts pass)"
    fi

    # Pass 2 — reverse top-level {session}/{harness}/ → {harness}/{session}/
    reverse_session_first_dirs

    # Check if artifacts dir is now empty
    if [ -d "$ARTIFACTS_DIR" ] && [ ! "$(ls -A "$ARTIFACTS_DIR")" ]; then
        log_info "Artifacts directory is now empty (leaving in place as deprecated)"

        # Create deprecation notice
        cat > "$ARTIFACTS_DIR/README.md" << 'EOF'
# DEPRECATED: artifacts/ Directory

This directory is no longer used. Queue paths have been migrated to:
```
~/.agentic-engineers/{harness}/{session-id}/queue/
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
