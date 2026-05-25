#!/bin/bash
# backup-harnesses.sh - Backup harness configs before fresh install
# Part of agentic-engineers multi-harness backup feature
#
# Usage: bash backup-harnesses.sh [--force] [harness1 harness2 ...]
# Example: bash backup-harnesses.sh copilot claude pi opencode
# Example (CI): bash backup-harnesses.sh --force copilot claude pi opencode
#
# Backs up existing harness directories with YYYYMMDD timestamp suffix:
#   ~/.copilot/     → ~/.copilot.20260525/
#   ~/.claude/      → ~/.claude.20260525/
#   ~/.pi/          → ~/.pi.20260525/
#   ~/.config/opencode/ → ~/.config/opencode.20260525/
#
# SCOPE: Only backs up harness config directories, never touches ~/.agentic-engineers/
#
# FLAGS:
#   --force    Skip interactive prompts (for CI/automation)

set -euo pipefail

TIMESTAMP=$(date +%Y%m%d)
BACKED_UP=()
SKIPPED=()
ERRORS=()

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
    echo -e "${GREEN}✅ $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Get harness directory path (bash 3.2 compatible)
get_harness_dir() {
    local harness_name="$1"
    case "$harness_name" in
        copilot)
            echo "$HOME/.copilot"
            ;;
        claude)
            echo "$HOME/.claude"
            ;;
        pi)
            echo "$HOME/.pi"
            ;;
        opencode)
            echo "$HOME/.config/opencode"
            ;;
        *)
            echo ""  # Invalid harness
            ;;
    esac
}

backup_harness() {
    local harness_name="$1"
    local harness_dir
    harness_dir=$(get_harness_dir "$harness_name")
    
    # Validate harness name
    if [ -z "$harness_dir" ]; then
        log_error "Unknown harness: $harness_name (valid: copilot, claude, pi, opencode)"
        ERRORS+=("$harness_name")
        return 1
    fi
    
    local backup_dir="${harness_dir}.${TIMESTAMP}"

    # Check if harness directory exists
    if [ ! -d "$harness_dir" ]; then
        log_warn "$harness_name: No existing installation at $harness_dir (skipped)"
        SKIPPED+=("$harness_name")
        return 0
    fi

    # Check if backup already exists (multiple runs same day)
    if [ -d "$backup_dir" ]; then
        log_warn "$harness_name: Backup already exists at $backup_dir (skipped)"
        SKIPPED+=("$harness_name")
        return 0
    fi

    # Calculate directory size
    local size
    size=$(du -sh "$harness_dir" 2>/dev/null | cut -f1 || echo "unknown")

    # Interactive prompt (unless --force)
    if [ "$SKIP_PROMPTS" != true ]; then
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log_info "About to backup $harness_name configuration"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  Source:      $harness_dir"
        echo "  Backup to:   $backup_dir"
        echo "  Size:        $size"
        echo ""
        echo -n "  Proceed with backup? (y/n): "
        
        read -r confirm
        echo ""
        
        if [[ ! $confirm =~ ^[Yy]$ ]]; then
            log_warn "$harness_name: Backup skipped by user"
            SKIPPED+=("$harness_name")
            return 0
        fi
    fi

    # Perform backup (simple mv)
    if [ "$SKIP_PROMPTS" = true ]; then
        log_info "Backing up $harness_name: $harness_dir → $backup_dir"
    fi
    
    if mv "$harness_dir" "$backup_dir"; then
        log_success "$harness_name: Backup complete → $backup_dir"
        BACKED_UP+=("$harness_name")
    else
        log_error "$harness_name: Backup failed"
        ERRORS+=("$harness_name")
        return 1
    fi
}

# Main execution
main() {
    # Parse arguments (check for --force flag first)
    SKIP_PROMPTS=false
    local harnesses=()
    
    for arg in "$@"; do
        if [ "$arg" = "--force" ]; then
            SKIP_PROMPTS=true
        else
            harnesses+=("$arg")
        fi
    done

    # Default to all harnesses if none specified
    if [ ${#harnesses[@]} -eq 0 ]; then
        harnesses=("copilot" "claude" "pi" "opencode")
    fi

    echo ""
    if [ "$SKIP_PROMPTS" = true ]; then
        log_info "Starting harness backup in NON-INTERACTIVE mode (timestamp: $TIMESTAMP)"
    else
        log_info "Starting INTERACTIVE harness backup (timestamp: $TIMESTAMP)"
        log_info "You will be prompted for confirmation before backing up each harness"
    fi
    echo ""

    # Backup each harness
    for harness in "${harnesses[@]}"; do
        backup_harness "$harness" || true  # Continue on error
    done

    # Summary
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Backup Summary"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ ${#BACKED_UP[@]} -gt 0 ]; then
        log_success "Backed up (${#BACKED_UP[@]}): ${BACKED_UP[*]}"
    fi
    
    if [ ${#SKIPPED[@]} -gt 0 ]; then
        log_warn "Skipped (${#SKIPPED[@]}): ${SKIPPED[*]}"
    fi
    
    if [ ${#ERRORS[@]} -gt 0 ]; then
        log_error "Failed (${#ERRORS[@]}): ${ERRORS[*]}"
        echo ""
        exit 1
    fi
    
    echo ""
    log_info "Note: ~/.agentic-engineers/ is never backed up (shared across all harnesses)"
    echo ""
}

main "$@"
