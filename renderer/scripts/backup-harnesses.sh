#!/bin/bash
# backup-harnesses.sh - Backup harness configs before fresh install
# Part of agentic-engineers multi-harness backup feature
#
# Usage: bash backup-harnesses.sh [OPTIONS] [harness1 harness2 ...]
# Example: bash backup-harnesses.sh copilot claude pi opencode
# Example (CI): bash backup-harnesses.sh --force copilot claude pi opencode
# Example (single harness): bash backup-harnesses.sh --harness copilot
# Example (quiet): bash backup-harnesses.sh --quiet copilot claude
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
#   --force        Skip interactive prompts (for CI/automation)
#   --harness NAME Back up only one harness (copilot, claude, pi, or opencode)
#   --quiet        Suppress verbose output (show only status)
#   --verbose      Show detailed output (default for interactive mode)

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
        if [ "$QUIET_MODE" != true ]; then
            log_error "Unknown harness: $harness_name (valid: copilot, claude, pi, opencode)"
        fi
        ERRORS+=("$harness_name")
        return 1
    fi
    
    local backup_dir="${harness_dir}.${TIMESTAMP}"

    # Check if harness directory exists
    if [ ! -d "$harness_dir" ]; then
        if [ "$QUIET_MODE" != true ]; then
            log_warn "$harness_name: No existing installation at $harness_dir (skipped)"
        fi
        SKIPPED+=("$harness_name")
        return 0
    fi

    # Check if backup already exists (multiple runs same day)
    if [ -d "$backup_dir" ]; then
        if [ "$QUIET_MODE" != true ]; then
            log_warn "$harness_name: Backup already exists at $backup_dir (skipped)"
        fi
        SKIPPED+=("$harness_name")
        return 0
    fi

    # Calculate directory size
    local size
    size=$(du -sh "$harness_dir" 2>/dev/null | cut -f1 || echo "unknown")

    # Interactive prompt (unless --force)
    if [ "$SKIP_PROMPTS" != true ]; then
        if [ "$QUIET_MODE" != true ]; then
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            log_info "About to backup $harness_name configuration"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "  Source:      $harness_dir"
            echo "  Backup to:   $backup_dir"
            echo "  Size:        $size"
            echo ""
        fi
        echo -n "  Backup $harness_name? (y/n): "
        
        read -r confirm
        
        if [ "$QUIET_MODE" != true ]; then
            echo ""
        fi
        
        if [[ ! $confirm =~ ^[Yy]$ ]]; then
            if [ "$QUIET_MODE" != true ]; then
                log_warn "$harness_name: Backup skipped by user"
            fi
            SKIPPED+=("$harness_name")
            return 0
        fi
    fi

    # Perform backup (simple mv)
    if [ "$SKIP_PROMPTS" = true ] && [ "$QUIET_MODE" != true ]; then
        log_info "Backing up $harness_name: $harness_dir → $backup_dir"
    fi
    
    if mv "$harness_dir" "$backup_dir"; then
        if [ "$QUIET_MODE" != true ]; then
            log_success "$harness_name: Backup complete → $backup_dir"
        fi
        BACKED_UP+=("$harness_name")
    else
        if [ "$QUIET_MODE" != true ]; then
            log_error "$harness_name: Backup failed"
        fi
        ERRORS+=("$harness_name")
        return 1
    fi
}

# Main execution
main() {
    # Parse arguments
    SKIP_PROMPTS=false
    QUIET_MODE=false
    local harnesses=()
    
    local i=1
    while [ $i -le $# ]; do
        arg="${!i}"
        case "$arg" in
            --force)
                SKIP_PROMPTS=true
                ;;
            --quiet)
                QUIET_MODE=true
                ;;
            --verbose)
                QUIET_MODE=false
                ;;
            --harness)
                # Next argument is the harness name
                i=$((i+1))
                if [ $i -le $# ]; then
                    harnesses=("${!i}")  # Single harness
                fi
                ;;
            *)
                # It's a harness name
                harnesses+=("$arg")
                ;;
        esac
        i=$((i+1))
    done

    # Default to all harnesses if none specified
    if [ ${#harnesses[@]} -eq 0 ]; then
        harnesses=("copilot" "claude" "pi" "opencode")
    fi

    # Print startup message (unless quiet mode)
    if [ "$QUIET_MODE" != true ]; then
        echo ""
        if [ "$SKIP_PROMPTS" = true ]; then
            log_info "Starting harness backup in NON-INTERACTIVE mode (timestamp: $TIMESTAMP)"
        else
            log_info "Starting INTERACTIVE harness backup (timestamp: $TIMESTAMP)"
            if [ ${#harnesses[@]} -eq 1 ]; then
                log_info "Backing up: ${harnesses[0]}"
            else
                log_info "You will be prompted for confirmation before backing up each harness"
            fi
        fi
        echo ""
    fi

    # Backup each harness
    for harness in "${harnesses[@]}"; do
        backup_harness "$harness" || true  # Continue on error
    done

    # Summary (unless quiet mode)
    if [ "$QUIET_MODE" != true ]; then
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
    else
        # In quiet mode, still exit with error code if there were failures
        if [ ${#ERRORS[@]} -gt 0 ]; then
            exit 1
        fi
    fi
}

main "$@"
