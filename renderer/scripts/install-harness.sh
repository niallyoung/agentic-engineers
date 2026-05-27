#!/bin/bash
# install-harness.sh - Interactive single-harness installation with optional backup
# Part of agentic-engineers fresh install workflow
#
# Usage: bash install-harness.sh {harness_name}
# Example: bash install-harness.sh copilot
#
# Flow:
# 1. Prompt: "Install {harness}? (y/n)"
# 2. If yes: prompt "Backup {harness} first? (y/n)"
# 3. If yes to backup: run backup
# 4. Render and install the harness
# 5. Show final status: "✓ {harness} installed" or "⊘ {harness} skipped"

set -euo pipefail

REPO_ROOT="${1:-.}"  # Default to current directory, but first arg might be repo root
HARNESS_NAME="${2:-}"  # Second arg is harness name

# If only one arg provided, treat it as harness name and use current repo
if [ $# -eq 1 ]; then
    HARNESS_NAME="$1"
    REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi

# Color output helpers
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_skip() {
    echo -e "${YELLOW}⊘ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
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

# Get make target name
get_make_target() {
    local harness="$1"
    echo "install-$harness"
}

# Get render make target
get_render_target() {
    local harness="$1"
    echo "render-$harness"
}

main() {
    # Validate arguments
    if [ -z "$HARNESS_NAME" ]; then
        log_error "Usage: bash install-harness.sh {harness_name}"
        echo "Valid harnesses: copilot, claude, pi, opencode"
        exit 1
    fi

    if ! validate_harness "$HARNESS_NAME"; then
        log_error "Invalid harness: $HARNESS_NAME"
        echo "Valid harnesses: copilot, claude, pi, opencode"
        exit 1
    fi

    # Step 1: Ask if user wants to install this harness
    echo ""
    echo -n "Install $HARNESS_NAME? (y/n): "
    read -r install_choice
    echo ""

    if [[ ! $install_choice =~ ^[Yy]$ ]]; then
        log_skip "$HARNESS_NAME skipped"
        echo ""
        return 0
    fi

    # Step 2: Ask if user wants to backup first
    # Get harness directory path
    case "$HARNESS_NAME" in
        copilot) harness_dir="$HOME/.copilot" ;;
        claude) harness_dir="$HOME/.claude" ;;
        pi) harness_dir="$HOME/.pi" ;;
        opencode) harness_dir="$HOME/.config/opencode" ;;
    esac
 
    echo -n "Backup $HARNESS_NAME first? (y/n): "
    read -r backup_choice
    echo ""
 
    if [[ $backup_choice =~ ^[Yy]$ ]]; then
        # Run backup for this harness
        log_info "Backing up $HARNESS_NAME..."
        if bash "$REPO_ROOT/renderer/scripts/backup-harnesses.sh" --quiet --harness "$HARNESS_NAME"; then
            log_success "$HARNESS_NAME backed up"
        else
            log_error "$HARNESS_NAME backup failed"
            exit 1
        fi
        echo ""
    elif [ -d "$harness_dir" ]; then
        # Directory exists and user skipped backup - warn about pollution risk
        echo -e "${YELLOW}⚠️  WARNING: $harness_dir exists${NC}"
        echo "   Without backup, old files may remain (potential pollution if files were renamed/deleted)"
        echo ""
        echo "   Options:"
        echo "   (a) Proceed with merge (old files will remain)"
        echo "   (b) Backup now before installing"
        echo "   (c) Clean install (delete $harness_dir and reinstall fresh)"
        echo ""
        echo -n "Choose action (a/b/c): "
        read -r action_choice
        echo ""
 
        case "$action_choice" in
            [Bb])
                log_info "Backing up $HARNESS_NAME..."
                if bash "$REPO_ROOT/renderer/scripts/backup-harnesses.sh" --quiet --harness "$HARNESS_NAME"; then
                    log_success "$HARNESS_NAME backed up"
                else
                    log_error "$HARNESS_NAME backup failed"
                    exit 1
                fi
                echo ""
                ;;
            [Cc])
                log_info "Removing $harness_dir for clean install..."
                rm -rf "$harness_dir"
                log_success "$HARNESS_NAME directory removed"
                echo ""
                ;;
            [Aa]|*)
                log_info "Proceeding with merge (old files will remain)"
                echo ""
                ;;
        esac
    fi

    # Step 3: Render the harness
    render_target=$(get_render_target "$HARNESS_NAME")
    log_info "Rendering $HARNESS_NAME configuration..."
    if ! cd "$REPO_ROOT" && make "$render_target" > /dev/null 2>&1; then
        log_error "Failed to render $HARNESS_NAME"
        exit 1
    fi
    echo ""

    # Step 4: Install the harness
    install_target=$(get_make_target "$HARNESS_NAME")
    log_info "Installing $HARNESS_NAME..."
    if ! cd "$REPO_ROOT" && make "$install_target" > /dev/null 2>&1; then
        log_error "Failed to install $HARNESS_NAME"
        exit 1
    fi

    # Step 5: Show success
    log_success "$HARNESS_NAME installed"
    echo ""
}

main "$@"
