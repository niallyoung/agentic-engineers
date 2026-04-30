#!/usr/bin/env bash
# install-copilot.sh — Install agentic-engineers to ~/.copilot/
#
# Installs rendered Copilot harness (agents, skills, config) to ~/.copilot/
# Backs up existing installation, creates installation marker for tracking
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
    ;;

  install|"")
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
        # Backup existing installation
        BACKUP_DIR="${COPILOT_DIR}.backup.${TIMESTAMP}"
        echo "💾 Backing up existing installation → $BACKUP_DIR"
        cp -r "$COPILOT_DIR" "$BACKUP_DIR"
      fi
    fi

    # Install from dist/copilot
    echo "📦 Installing agentic-engineers → $COPILOT_DIR..."
    mkdir -p "$COPILOT_DIR"

    # Copy all files from dist/copilot
    cp -r "$DIST_DIR"/* "$COPILOT_DIR/"

    # Write installation marker
    echo "$TIMESTAMP" > "$COPILOT_DIR/$MARKER"

    echo "✅ Installation complete"
    echo "   Location: $COPILOT_DIR"
    echo "   Files: $(find "$COPILOT_DIR" -type f | wc -l) file(s)"
    echo ""
    echo "Next steps:"
    echo "  - Edit ~/.copilot/config/config.yaml if needed"
    echo "  - Read ~/.copilot/README.md for usage"
    echo "  - Load in Copilot: Reference ~/.copilot/ in your instructions"
    ;;

  *)
    echo "Unknown mode: $MODE" >&2
    echo "Usage: $0 [install|--uninstall|--status]" >&2
    exit 1
    ;;
esac
