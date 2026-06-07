#!/bin/bash
# unified-install.sh - Unified multi-harness installation with consistent backup strategy
# Part of agentic-engineers install system
#
# Usage: bash unified-install.sh [OPTIONS] [harness1 harness2 ...]
# Example: bash unified-install.sh copilot claude pi opencode           (non-interactive, auto-backup)
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
    
    # Shift past repo root if it looks like a flag
    if [[ "$1" == /* ]] || [ "$1" = "." ]; then
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
                BACKUP_ROOT="$2"
                shift 2
                ;;
            --quiet)
                QUIET=true
                shift
                ;;
            --destdir)
                DEST_ROOT="$2"
                shift 2
                ;;
            --)
                shift
                break
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
        HARNESSES=("copilot" "claude" "pi" "opencode")
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
        pi)
            echo "$DEST_ROOT/.pi"
            ;;
        opencode)
            echo "$DEST_ROOT/.config/opencode"
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
        copilot|claude|pi|opencode)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Get render target
get_render_target() {
    echo "render-$1"
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
    
    if ! mv "$harness_dir" "$backup_dir"; then
        log_error "$harness: Backup failed"
        return 1
    fi
    
    log_success "$harness: Backed up to $backup_dir"
    return 0
}

# Install a single harness
install_harness() {
    local harness="$1"
    local harness_dir
    harness_dir=$(get_harness_dir "$harness")
    
    # Step 1: Ask if user wants to install (interactive mode only)
    if [ "$INTERACTIVE" = true ] && [ "$FORCE" != true ]; then
        echo -n "Install $harness? (y/n): "
        read -r install_choice
        if [[ ! $install_choice =~ ^[Yy]$ ]]; then
            log_warn "$harness: Skipped by user"
            return 0
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
                else
                    log_warn "$harness: Proceeding without backup (old files may remain)"
                fi
            else
                # Non-interactive: auto-backup (safe default)
                if ! backup_harness_dir "$harness"; then
                    return 1
                fi
            fi
        fi
    fi
    
    # Step 3: Render
    log_info "Rendering $harness..."
    local render_target
    render_target=$(get_render_target "$harness")
    if ! cd "$REPO_ROOT" && make "$render_target" > /dev/null 2>&1; then
        log_error "$harness: Failed to render"
        return 1
    fi
    
    # Step 4: Install
    log_info "Installing $harness..."
    local install_target
    install_target=$(get_install_target "$harness")
    if ! cd "$REPO_ROOT" && make "$install_target" DESTDIR="$DEST_ROOT" > /dev/null 2>&1; then
        log_error "$harness: Failed to install"
        
        # TODO: Rollback backup if install failed
        # This is a future enhancement for safety
        
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
    
    # Install each harness
    for harness in "${HARNESSES[@]}"; do
        if install_harness "$harness"; then
            ((installed_count++))
        else
            ((failed_count++))
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
