#!/usr/bin/env bash
# install-copilot.sh — Install agentic-engineers to ~/.copilot/
#
# Smart installer that:
# - Only updates changed files (using rsync)
# - Preserves queue/ directory state
# - Does selective backups (only backs up what will change)
# - Supports install, uninstall, status modes
#
# Usage:
#   ./scripts/install-copilot.sh
#   ./scripts/install-copilot.sh --uninstall
#   ./scripts/install-copilot.sh --status

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
COPILOT_DIR="${HOME}/.copilot"
DIST_DIR="$REPO_ROOT/dist/copilot"
QUEUE_DIR="$REPO_ROOT/artifacts/queue"
MARKER=".agentic-engine{service-name}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

MODE="${1:-install}"

# Verify dist/copilot exists
if [ ! -d "$DIST_DIR" ]; then
  echo "❌ Error: $DIST_DIR not found" >&2
  echo "   Run: cd $REPO_ROOT && make render-copilot" >&2
  exit 1
fi

case "$MODE" in
  --uninstall)
    if [ ! -d "$COPILOT_DIR" ] || [ ! -f "$COPILOT_DIR/$MARKER" ]; then
      echo "⚠️  No agentic-engineers installation found at $COPILOT_DIR" >&2
      exit 0
    fi

    echo "🧹 Uninstalling agentic-engineers from $COPILOT_DIR..."
    rm -rf "$COPILOT_DIR"
    echo "✅ Uninstalled"
    ;;

  --status)
    if [ ! -d "$COPILOT_DIR" ]; then
      echo "❌ Not installed"
      exit 1
    elif [ ! -f "$COPILOT_DIR/$MARKER" ]; then
      echo "⚠️  Directory exists but not managed by agentic-engineers"
      exit 1
    fi

    echo "✅ Installed at $COPILOT_DIR"
    echo "   Installation date: $(cat "$COPILOT_DIR/$MARKER")"
    echo "   Agents: $(ls "$COPILOT_DIR/roles/" 2>/dev/null | wc -l) role(s)"
    if [ -d "$COPILOT_DIR/queue/incoming" ]; then
      INCOMING=$(ls "$COPILOT_DIR/queue/incoming/" 2>/dev/null | wc -l)
      PROCESSING=$(ls "$COPILOT_DIR/queue/processing/" 2>/dev/null | wc -l)
      DONE=$(ls "$COPILOT_DIR/queue/done/" 2>/dev/null | wc -l)
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
    if [ -d "$COPILOT_DIR" ]; then
      if [ ! -f "$COPILOT_DIR/$MARKER" ]; then
        echo "⚠️  $COPILOT_DIR exists but is not managed by agentic-engineers" >&2
        read -p "   Overwrite? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
          echo "Cancelled."
          exit 1
        fi
      else
        # Smart backup: only back up files that will be updated
        if [ "$SMART_INSTALL" = true ]; then
          echo "🔍 Checking for changed files..."
          CHANGED=$(rsync -n -r "$DIST_DIR/" "$COPILOT_DIR/" 2>&1 | grep -c "^<" || true)
          if [ "$CHANGED" -gt 0 ]; then
            BACKUP_DIR="${COPILOT_DIR}.backup.${TIMESTAMP}"
            echo "💾 Backing up $CHANGED changed file(s) → $BACKUP_DIR"
            mkdir -p "$BACKUP_DIR"

            # Backup only the files that will change
            # Get list of changed files and copy them to backup
            rsync -r --delete "$DIST_DIR/" "$BACKUP_DIR.staging/" 2>/dev/null || true
            find "$BACKUP_DIR.staging/" -type f 2>/dev/null | while read -r FILE; do
              REL_PATH="${FILE#$BACKUP_DIR.staging/}"
              if [ -f "$COPILOT_DIR/$REL_PATH" ]; then
                BACKUP_FILE="$BACKUP_DIR/$REL_PATH"
                mkdir -p "$(dirname "$BACKUP_FILE")"
                cp "$COPILOT_DIR/$REL_PATH" "$BACKUP_FILE"
              fi
            done
            rm -rf "$BACKUP_DIR.staging"
          else
            echo "✅ No changes detected; skipping backup"
          fi
        else
          # Fallback: full backup if rsync not available
          BACKUP_DIR="${COPILOT_DIR}.backup.${TIMESTAMP}"
          echo "💾 Backing up existing installation → $BACKUP_DIR"
          cp -r "$COPILOT_DIR" "$BACKUP_DIR"
        fi
      fi
    fi

    # Install from dist/copilot (smart or full)
    echo "📦 Installing agentic-engineers → $COPILOT_DIR..."
    mkdir -p "$COPILOT_DIR"

    if [ "$SMART_INSTALL" = true ]; then
      # Use rsync: only copy changed files, skip queue/
      rsync -r \
        --exclude="queue/" \
        --exclude=".agentic-engine{service-name}" \
        "$DIST_DIR/" "$COPILOT_DIR/"
    else
      # Fallback: copy all files except queue/
      cp -r "$DIST_DIR"/* "$COPILOT_DIR/" 2>/dev/null || true
      # Remove queue if it was copied (shouldn't happen with smart rsync)
      rm -rf "$COPILOT_DIR/queue"
    fi

    # Preserve or initialize queue/
    if [ ! -d "$COPILOT_DIR/queue" ]; then
      echo "📋 Initializing queue directory..."
      mkdir -p "$COPILOT_DIR/queue/"{incoming,processing,done}
    fi

    # Write installation marker
    echo "$TIMESTAMP" > "$COPILOT_DIR/$MARKER"

    echo "✅ Installation complete"
    echo "   Location: $COPILOT_DIR"
    echo "   Files: $(find "$COPILOT_DIR" -type f | wc -l) file(s)"
    echo "   Queue: $([ -d "$COPILOT_DIR/queue/incoming" ] && echo "✅ Ready" || echo "❌ Not initialized")"
    echo ""
    echo "Next steps:"
    echo "  - Edit ~/.copilot/ config if needed"
    echo "  - Run: make status (to verify)"
    echo "  - Load in Copilot: Reference ~/.copilot/ in your instructions"
    ;;

  *)
    echo "Unknown mode: $MODE" >&2
    echo "Usage: $0 [install|--uninstall|--status]" >&2
    exit 1
    ;;
esac
