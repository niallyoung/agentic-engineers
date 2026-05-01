#!/usr/bin/env bash
# install-claude.sh — Install agentic-engineers to ~/.claude/
#
# Smart installer that:
# - Only updates changed files (using rsync)
# - Preserves queue/ directory state
# - Does selective backups (only backs up what will change)
# - Supports install, uninstall, status modes
#
# Usage:
#   ./scripts/install-claude.sh
#   ./scripts/install-claude.sh --uninstall
#   ./scripts/install-claude.sh --status

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
CLAUDE_DIR="${HOME}/.claude"
DIST_DIR="$REPO_ROOT/dist/claude"
MARKER=".agentic-engine{service-name}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

MODE="${1:-install}"

# Verify dist/claude exists
if [ ! -d "$DIST_DIR" ]; then
  echo "❌ Error: $DIST_DIR not found" >&2
  echo "   Run: cd $REPO_ROOT && make render-claude" >&2
  exit 1
fi

case "$MODE" in
  --uninstall)
    if [ ! -d "$CLAUDE_DIR" ] || [ ! -f "$CLAUDE_DIR/$MARKER" ]; then
      echo "⚠️  No agentic-engineers installation found at $CLAUDE_DIR" >&2
      exit 0
    fi

    echo "🧹 Uninstalling agentic-engineers from $CLAUDE_DIR..."
    rm -rf "$CLAUDE_DIR"
    echo "✅ Uninstalled"
    ;;

  --status)
    if [ ! -d "$CLAUDE_DIR" ]; then
      echo "❌ Not installed"
      exit 1
    elif [ ! -f "$CLAUDE_DIR/$MARKER" ]; then
      echo "⚠️  Directory exists but not managed by agentic-engineers"
      exit 1
    fi

    echo "✅ Installed at $CLAUDE_DIR"
    echo "   Installation date: $(cat "$CLAUDE_DIR/$MARKER")"
    echo "   Agents: $(ls "$CLAUDE_DIR/roles/" 2>/dev/null | wc -l) role(s)"
    if [ -d "$CLAUDE_DIR/queue/incoming" ]; then
      INCOMING=$(ls "$CLAUDE_DIR/queue/incoming/" 2>/dev/null | wc -l)
      PROCESSING=$(ls "$CLAUDE_DIR/queue/processing/" 2>/dev/null | wc -l)
      DONE=$(ls "$CLAUDE_DIR/queue/done/" 2>/dev/null | wc -l)
      echo "   Queue: $INCOMING incoming, $PROCESSING processing, $DONE done"
    fi
    ;;

  install|"")
    # Check if rsync is available for smart updates
    if ! command -v rsync &> /dev/null; then
      echo "⚠️  rsync not found; using cp (will copy all files)" >&2
      SMART_INSTALL=false
    else
      SMART_INSTALL=true
    fi

    # Check if installation already exists
    if [ -d "$CLAUDE_DIR" ]; then
      if [ ! -f "$CLAUDE_DIR/$MARKER" ]; then
        echo "⚠️  $CLAUDE_DIR exists but is not managed by agentic-engineers" >&2
        read -p "   Overwrite? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
          echo "Cancelled."
          exit 1
        fi
      else
        # Smart backup: only back up files that will be updated
        if [ "$SMART_INSTALL" = true ]; then
          echo "🔍 Checking for changed files..."
          CHANGED=$(rsync -n -r "$DIST_DIR/" "$CLAUDE_DIR/" 2>&1 | grep -c "^<" || true)
          if [ "$CHANGED" -gt 0 ]; then
            BACKUP_DIR="${CLAUDE_DIR}.backup.${TIMESTAMP}"
            echo "💾 Backing up $CHANGED changed file(s) → $BACKUP_DIR"
            mkdir -p "$BACKUP_DIR"

            # Backup only the files that will change
            # Get list of changed files and copy them to backup
            rsync -r --delete "$DIST_DIR/" "$BACKUP_DIR.staging/" 2>/dev/null || true
            find "$BACKUP_DIR.staging/" -type f 2>/dev/null | while read -r FILE; do
              REL_PATH="${FILE#$BACKUP_DIR.staging/}"
              if [ -f "$CLAUDE_DIR/$REL_PATH" ]; then
                BACKUP_FILE="$BACKUP_DIR/$REL_PATH"
                mkdir -p "$(dirname "$BACKUP_FILE")"
                cp "$CLAUDE_DIR/$REL_PATH" "$BACKUP_FILE"
              fi
            done
            rm -rf "$BACKUP_DIR.staging"
          else
            echo "✅ No changes detected; skipping backup"
          fi
        else
          # Fallback: full backup if rsync not available
          BACKUP_DIR="${CLAUDE_DIR}.backup.${TIMESTAMP}"
          echo "💾 Backing up existing installation → $BACKUP_DIR"
          cp -r "$CLAUDE_DIR" "$BACKUP_DIR"
        fi
      fi
    fi

    # Install from dist/claude (smart or full)
    echo "📦 Installing agentic-engineers → $CLAUDE_DIR..."
    mkdir -p "$CLAUDE_DIR"

    if [ "$SMART_INSTALL" = true ]; then
      # Use rsync: only copy changed files, skip queue/
      rsync -r \
        --exclude="queue/" \
        --exclude=".agentic-engine{service-name}" \
        "$DIST_DIR/" "$CLAUDE_DIR/"
    else
      # Fallback: copy all files except queue/
      cp -r "$DIST_DIR"/* "$CLAUDE_DIR/" 2>/dev/null || true
      # Remove queue if it was copied (shouldn't happen with smart rsync)
      rm -rf "$CLAUDE_DIR/queue"
    fi

    # Preserve or initialize queue/
    if [ ! -d "$CLAUDE_DIR/queue" ]; then
      echo "📋 Initializing queue directory..."
      mkdir -p "$CLAUDE_DIR/queue/"{incoming,processing,done}
    fi

    # Write installation marker
    echo "$TIMESTAMP" > "$CLAUDE_DIR/$MARKER"

    echo "✅ Installation complete"
    echo "   Location: $CLAUDE_DIR"
    echo "   Files: $(find "$CLAUDE_DIR" -type f | wc -l) file(s)"
    echo "   Queue: $([ -d "$CLAUDE_DIR/queue/incoming" ] && echo "✅ Ready" || echo "❌ Not initialized")"
    echo ""
    echo "Next steps:"
    echo "  - Edit ~/.claude/config/config.yaml if needed"
    echo "  - Run: make status (to verify)"
    echo "  - Load in Claude: Reference ~/.claude/ in your instructions"
    ;;

  *)
    echo "Unknown mode: $MODE" >&2
    echo "Usage: $0 [install|--uninstall|--status]" >&2
    exit 1
    ;;
esac
