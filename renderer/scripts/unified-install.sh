#!/bin/bash
# unified-install.sh - Unified multi-harness installation with consistent backup strategy
# Part of agentic-engineers install system
#
# Usage: bash unified-install.sh [OPTIONS] [harness1 harness2 ...]
# Example: bash unified-install.sh copilot claude opencode codex        (non-interactive, auto-backup)
# Example: bash unified-install.sh --interactive copilot claude         (interactive, ask per harness)
# Example: bash unified-install.sh --no-backup copilot                  (skip backup)
# Example: bash unified-install.sh --force copilot                      (skip all prompts)
#
# Features:
# - Unified behavior: install + fresh-install use same code
# - Backup-first strategy: always backup by default (unless --no-backup)
# - Per-harness prompts: --interactive asks for each harness y/n
# - Surgical install: uses marker-based foreign file protection
# - Rollback on failure: restores backup if install fails
#
# FLAGS:
#   --interactive       Prompt for each harness (y/n to install, y/n to backup)
#   --no-backup         Skip backup (dangerous for prod, ok for testing/CI)
#   --force             Skip all prompts, assume yes (for CI/automation)
#   --backup-root PATH  Custom backup directory (default: parallel to harness dir)
#   --quiet             Suppress verbose output
#   --destdir PATH      Installation destination root (default: $HOME)
#
# Exit codes:
#   0: All installed successfully
#   1: One or more harnesses failed to install
#   2: Invalid arguments

set -euo pipefail

REPO_ROOT="${1:-.}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Parse arguments
parse_args() {
    local mode_arg=""
    INTERACTIVE=false
    NO_BACKUP=false
    FORCE=false
    QUIET=false
    BACKUP_ROOT=""
    DEST_ROOT="${DESTDIR:-$HOME}"

    # Shift past repo root if it looks like a path (first positional arg).
    # Guard the $1 access so an invocation with no args does not trip `set -u`.
    if [ $# -gt 0 ] && { [[ "$1" == /* ]] || [ "$1" = "." ]; }; then
        REPO_ROOT="$1"
        shift || true
    fi

    # Parse flags
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --interactive)
                INTERACTIVE=true
                shift
                ;;
            --no-backup)
                NO_BACKUP=true
                shift
                ;;
            --force)
                FORCE=true
                INTERACTIVE=false
                shift
                ;;
            --backup-root)
                # Require an explicit value; otherwise `set -u` would abort with a
                # cryptic "unbound variable" and we would later run mkdir/mv on an
                # empty path.
                if [ $# -lt 2 ] || [[ "$2" == -* ]]; then
                    log_error "--backup-root requires a directory argument"
                    exit 2
                fi
                BACKUP_ROOT="$2"
                shift 2
                ;;
            --quiet)
                QUIET=true
                shift
                ;;
            --destdir)
                if [ $# -lt 2 ] || [[ "$2" == -* ]]; then
                    log_error "--destdir requires a directory argument"
                    exit 2
                fi
                DEST_ROOT="$2"
                shift 2
                ;;
            --)
                shift
                break
                ;;
            -*)
                # Unknown flag — fail loudly rather than silently treating it as a
                # harness name (which would only surface as an opaque error later).
                log_error "Unknown option: $1"
                exit 2
                ;;
            *)
                break
                ;;
        esac
    done
    
    # Remaining args are harness names
    HARNESSES=("$@")
    
    # Default to all harnesses if none specified
    if [ ${#HARNESSES[@]} -eq 0 ]; then
        HARNESSES=("copilot" "claude" "opencode" "codex")
    fi
}

# Color output helpers
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    if [ "$QUIET" != true ]; then
        echo -e "${BLUE}ℹ️  $1${NC}"
    fi
}

log_success() {
    if [ "$QUIET" != true ]; then
        echo -e "${GREEN}✅ $1${NC}"
    fi
}

log_warn() {
    if [ "$QUIET" != true ]; then
        echo -e "${YELLOW}⚠️  $1${NC}"
    fi
}

log_error() {
    if [ "$QUIET" != true ]; then
        echo -e "${RED}❌ $1${NC}"
    fi
}

# Get harness directory path
get_harness_dir() {
    local harness_name="$1"
    case "$harness_name" in
        copilot)
            echo "$DEST_ROOT/.copilot"
            ;;
        claude)
            echo "$DEST_ROOT/.claude"
            ;;
        opencode)
            echo "$DEST_ROOT/.config/opencode"
            ;;
        codex)
            echo "$DEST_ROOT/.codex"
            ;;
        *)
            return 1
            ;;
    esac
}

# Validate harness name
validate_harness() {
    local harness="$1"
    case "$harness" in
        copilot|claude|opencode|codex)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Get install target
get_install_target() {
    echo "install-$1"
}

# Backup a harness directory
backup_harness_dir() {
    local harness="$1"
    local harness_dir
    harness_dir=$(get_harness_dir "$harness")
    
    if [ ! -d "$harness_dir" ]; then
        return 0  # Nothing to backup
    fi
    
    local backup_dir="${harness_dir}.${TIMESTAMP}"
    
    # If custom backup root specified, use it
    if [ -n "$BACKUP_ROOT" ]; then
        backup_dir="${BACKUP_ROOT}/${harness}.${TIMESTAMP}"
        mkdir -p "$BACKUP_ROOT"
    fi
    
    # Check if backup already exists (multiple runs same day)
    if [ -d "$backup_dir" ]; then
        log_warn "$harness: Backup already exists at $backup_dir (skipping backup)"
        return 0
    fi
    
    # Calculate size for reporting
    local size
    size=$(du -sh "$harness_dir" 2>/dev/null | cut -f1 || echo "unknown")

    log_info "Backing up $harness: $harness_dir → $backup_dir ($size)"

    # SECURITY NOTE: harness config dirs may contain credentials / session
    # tokens (e.g. auth.json, oauth_creds.json, session state). The backup
    # preserves the original permissions, but it does create a second copy of
    # those secrets at a predictable, timestamped path. Warn the user so they
    # can clean up stale backups containing sensitive material.
    log_warn "$harness: Backup may contain credentials/session tokens — remove old backups when no longer needed: $backup_dir"

    # COPY (not move): the install step merges into the EXISTING harness dir
    # (rsync without --delete) so it can preserve user files we do not manage —
    # config.json, auth tokens, session/history state. Moving the dir aside
    # would leave the merge with nothing to layer onto and silently destroy that
    # user state on every successful install. A copy keeps the live dir intact
    # AND leaves a timestamped snapshot for safety/rollback.
    if ! cp -a "$harness_dir" "$backup_dir"; then
        log_error "$harness: Backup failed"
        # Clean up any partial copy so a later run does not see a stale backup.
        rm -rf "$backup_dir" 2>/dev/null || true
        return 1
    fi

    log_success "$harness: Backed up to $backup_dir"
    # Record where this harness was backed up so a failed install can roll back.
    LAST_BACKUP_DIR="$backup_dir"
    return 0
}

# Backup an arbitrary directory using the same safety and timestamp rules.
backup_dir() {
    local label="$1"
    local source_dir="$2"
    local backup_dir="$3"

    if [ ! -d "$source_dir" ]; then
        return 0
    fi
    if [ -d "$backup_dir" ]; then
        log_warn "$label: Backup already exists at $backup_dir (skipping backup)"
        return 0
    fi

    local size
    size=$(du -sh "$source_dir" 2>/dev/null | cut -f1 || echo "unknown")
    log_info "Backing up $label: $source_dir → $backup_dir ($size)"
    log_warn "$label: Backup may contain credentials/session tokens — remove old backups when no longer needed: $backup_dir"
    if ! cp -a "$source_dir" "$backup_dir"; then
        log_error "$label: Backup failed"
        rm -rf "$backup_dir" 2>/dev/null || true
        return 1
    fi
    log_success "$label: Backed up to $backup_dir"
    return 0
}

# Install a single harness
# Restore a harness directory from its backup snapshot (used on install failure
# so a partially-applied install does not leave the user with a corrupted config).
# The backup is a COPY of the pre-install state, so on failure we discard the
# (possibly half-merged) live dir and move the snapshot into its place.
rollback_harness_dir() {
    local harness_dir="$1"
    local backup_dir="$2"
    [ -n "$backup_dir" ] || return 0
    [ -d "$backup_dir" ] || return 0
    rm -rf "$harness_dir" 2>/dev/null || true
    if mv "$backup_dir" "$harness_dir"; then
        log_warn "Rolled back: restored $harness_dir from backup snapshot"
    else
        log_error "Rollback failed — original config remains at $backup_dir"
    fi
}

rollback_dir() {
    local target_dir="$1"
    local backup_dir="$2"
    [ -n "$backup_dir" ] || return 0
    [ -d "$backup_dir" ] || return 0
    rm -rf "$target_dir" 2>/dev/null || true
    if mv "$backup_dir" "$target_dir"; then
        log_warn "Rolled back: restored $target_dir from backup snapshot"
    else
        log_error "Rollback failed — original config remains at $backup_dir"
    fi
}

install_harness() {
    local harness="$1"
    local harness_dir
    harness_dir=$(get_harness_dir "$harness")
    # Per-harness backup tracker; reset for each harness so rollback only ever
    # touches the backup created in this iteration.
    LAST_BACKUP_DIR=""
    LAST_SKILLS_BACKUP_DIR=""

    # Step 1: Ask if user wants to install (interactive mode only)
    if [ "$INTERACTIVE" = true ] && [ "$FORCE" != true ]; then
        echo -n "Install $harness? (y/n): "
        read -r install_choice
        if [[ ! $install_choice =~ ^[Yy]$ ]]; then
            log_warn "$harness: Skipped by user"
            return 2  # distinct from 0 (installed) so the summary counts it as skipped
        fi
    fi
    
    # Step 2: Backup strategy
    if [ "$NO_BACKUP" != true ]; then
        if [ -d "$harness_dir" ]; then
            if [ "$INTERACTIVE" = true ] && [ "$FORCE" != true ]; then
                # Interactive: ask user
                echo -n "Backup $harness before install? (y/n): "
                read -r backup_choice
                if [[ $backup_choice =~ ^[Yy]$ ]]; then
                    if ! backup_harness_dir "$harness"; then
                        return 1
                    fi
                    if [ "$harness" = "codex" ]; then
                        local skills_dir="${DEST_ROOT}/.codex/skills"
                        local skills_backup="${skills_dir}.${TIMESTAMP}"
                        if ! backup_dir "codex skills" "$skills_dir" "$skills_backup"; then
                            rollback_harness_dir "$harness_dir" "$LAST_BACKUP_DIR"
                            return 1
                        fi
                        LAST_SKILLS_BACKUP_DIR="$skills_backup"
                    fi
                else
                    log_warn "$harness: Proceeding without backup (old files may remain)"
                fi
            else
                # Non-interactive: auto-backup (safe default)
                if ! backup_harness_dir "$harness"; then
                    return 1
                fi
                if [ "$harness" = "codex" ]; then
                    local skills_dir="${DEST_ROOT}/.codex/skills"
                    local skills_backup="${skills_dir}.${TIMESTAMP}"
                    if ! backup_dir "codex skills" "$skills_dir" "$skills_backup"; then
                        rollback_harness_dir "$harness_dir" "$LAST_BACKUP_DIR"
                        return 1
                    fi
                    LAST_SKILLS_BACKUP_DIR="$skills_backup"
                fi
            fi
        fi
    fi
    
    # Step 3: Install
    # NOTE (2026-08-13 infra consolidation): this used to be preceded by a
    # "Step 3: Render" that ran `make render-$harness` (rendering to dist/
    # $harness/) before installing. That render pass was pure decoy work —
    # `make install-$harness` below renders straight to $DEST_ROOT via each
    # render-*.sh script's own DEST_ROOT argument, and never reads from
    # dist/. Removed; render failures now surface as install failures below
    # (install-$harness renders internally, so a render error still aborts
    # the harness with the same rollback behavior).
    log_info "Installing $harness..."
    local install_target
    install_target=$(get_install_target "$harness")
    if ! ( cd "$REPO_ROOT" && make "$install_target" DESTDIR="$DEST_ROOT" > /dev/null 2>&1 ); then
        log_error "$harness: Failed to install"
        # Restore the original config that the backup step moved aside, so a
        # failed install does not leave the user with no harness config.
        rollback_harness_dir "$harness_dir" "$LAST_BACKUP_DIR"
        if [ "$harness" = "codex" ]; then
            rollback_dir "${DEST_ROOT}/.codex/skills" "$LAST_SKILLS_BACKUP_DIR"
        fi
        return 1
    fi
    
    log_success "$harness: Installed successfully"
    return 0
}

# Main execution
main() {
    local exit_code=0
    local installed_count=0
    local skipped_count=0
    local failed_count=0
    
    parse_args "$@"
    
    # Validation
    if [ ${#HARNESSES[@]} -eq 0 ]; then
        log_error "No harnesses specified"
        exit 2
    fi
    
    for harness in "${HARNESSES[@]}"; do
        if ! validate_harness "$harness"; then
            log_error "Invalid harness: $harness"
            exit 2
        fi
    done
    
    # Print startup header
    if [ "$QUIET" != true ]; then
        echo ""
        if [ "$FORCE" = true ]; then
            log_info "Starting installation (non-interactive, auto-backup)"
        elif [ "$INTERACTIVE" = true ]; then
            log_info "Starting interactive installation"
        else
            log_info "Starting installation (auto-backup)"
        fi
        
        if [ "$NO_BACKUP" = true ]; then
            log_warn "Backup disabled (install only)"
        fi
        
        echo "Harnesses: ${HARNESSES[*]}"
        echo ""
    fi
    
    # Install each harness.
    # NOTE: use $((x + 1)) assignment, NOT ((x++)). Under `set -e`, `((x++))`
    # returns exit status 1 when the pre-increment value is 0 (the first count),
    # which would abort the script. The assignment form always returns 0.
    for harness in "${HARNESSES[@]}"; do
        # Capture the status explicitly (0=installed, 2=skipped, other=failed).
        # `|| rc=$?` keeps `set -e` from aborting on a non-zero return.
        local rc=0
        install_harness "$harness" || rc=$?
        if [ "$rc" -eq 0 ]; then
            installed_count=$((installed_count + 1))
        elif [ "$rc" -eq 2 ]; then
            skipped_count=$((skipped_count + 1))
        else
            failed_count=$((failed_count + 1))
            exit_code=1
        fi
    done
    
    # Print summary
    if [ "$QUIET" != true ]; then
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log_info "Installation Summary"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        if [ $installed_count -gt 0 ]; then
            log_success "Installed: $installed_count"
        fi
        
        if [ $skipped_count -gt 0 ]; then
            log_warn "Skipped: $skipped_count"
        fi
        
        if [ $failed_count -gt 0 ]; then
            log_error "Failed: $failed_count"
        fi
        
        echo ""
    fi
    
    return $exit_code
}

main "$@"
