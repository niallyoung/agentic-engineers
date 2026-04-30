#!/usr/bin/env bash
# install-claude.sh — Install agentic-engineers to ~/.claude/
#
# Installs rendered Claude harness (agents, skills, config) to ~/.claude/
# Backs up existing installation, creates installation marker for tracking
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
    ;;

  install|"")
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
        # Backup existing installation
        BACKUP_DIR="${CLAUDE_DIR}.backup.${TIMESTAMP}"
        echo "💾 Backing up existing installation → $BACKUP_DIR"
        cp -r "$CLAUDE_DIR" "$BACKUP_DIR"
      fi
    fi

    # Install from dist/claude
    echo "📦 Installing agentic-engineers → $CLAUDE_DIR..."
    mkdir -p "$CLAUDE_DIR"

    # Copy all files from dist/claude
    cp -r "$DIST_DIR"/* "$CLAUDE_DIR/"

    # Write installation marker
    echo "$TIMESTAMP" > "$CLAUDE_DIR/$MARKER"

    echo "✅ Installation complete"
    echo "   Location: $CLAUDE_DIR"
    echo "   Files: $(find "$CLAUDE_DIR" -type f | wc -l) file(s)"
    echo ""
    echo "Next steps:"
    echo "  - Edit ~/.claude/config/config.yaml if needed"
    echo "  - Read ~/.claude/README.md for usage"
    echo "  - Load in Claude: 'load agentic-engineers' or reference ~/.claude/"
    ;;

  *)
    echo "Unknown mode: $MODE" >&2
    echo "Usage: $0 [install|--uninstall|--status]" >&2
    exit 1
    ;;
esac
