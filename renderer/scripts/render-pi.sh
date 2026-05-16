#!/usr/bin/env bash
# render-pi.sh — Install agentic-engineers config into ~/.pi/agent/
#
# Inputs:  $1 = REPO_ROOT (agentic-engineers repo root)
#          $2 = PI root (e.g., $HOME/.pi)
#          $3 = optional: --uninstall | --status
#
# Behavior: Uses Python renderer (render-pi-dev.py) to manage config files
# in ~/.pi/agent/:
#  - SYSTEM.md
#  - AGENTS.md
#  - settings.json
#  - pi.yml
#  - SUB_AGENT_SETUP.md
#
# Preserves Pi-managed files:
#  - auth.json
#  - bin/
#  - sessions/
#
# A marker file (.agentic-engine-pi) is written to ~/.pi/agent/ so
# uninstall can identify what to remove.

set -euo pipefail

REPO_ROOT="${1:?usage: render-pi.sh REPO_ROOT PI_DIR [--uninstall|--status]}"
PI="${2:?usage: render-pi.sh REPO_ROOT PI_DIR [--uninstall|--status]}"
MODE="${3:-install}"

PI_AGENT="$PI/agent"
RENDERER_SCRIPT="$REPO_ROOT/renderer/scripts/render-pi-dev.py"
RENDERER_SRC="$REPO_ROOT/renderer/pi-dev-src"
MARKER=".agentic-engine-pi"

[ -f "$RENDERER_SCRIPT" ] || { echo "❌ Renderer not found: $RENDERER_SCRIPT" >&2; exit 1; }
[ -d "$RENDERER_SRC" ] || { echo "❌ Source not found: $RENDERER_SRC" >&2; exit 1; }

case "$MODE" in
	--uninstall)
		echo "🧹 Removing agentic-engineers config from $PI_AGENT/..."
		
		if [ ! -f "$PI_AGENT/$MARKER" ]; then
			echo "⚠️  Not installed (marker not found). Skipping."
			exit 0
		fi
		
		python3 "$RENDERER_SCRIPT" --src "$RENDERER_SRC" --dest "$PI" --uninstall
		
		# Remove marker
		if [ -f "$PI_AGENT/$MARKER" ]; then
			rm "$PI_AGENT/$MARKER"
		fi
		
		echo "✅ Uninstall complete"
		;;

	--status)
		echo "📋 Checking installation status at $PI_AGENT/..."
		python3 "$RENDERER_SCRIPT" --src "$RENDERER_SRC" --dest "$PI" --status
		;;

	install|"")
		echo "📦 Installing agentic-engineers to $PI_AGENT/..."
		mkdir -p "$PI_AGENT"
		
		python3 "$RENDERER_SCRIPT" --src "$RENDERER_SRC" --dest "$PI"
		
		# Write marker
		date -u +"%Y-%m-%dT%H:%M:%SZ" > "$PI_AGENT/$MARKER"
		
		echo "✅ Installation complete"
		;;

	*)
		echo "unknown mode: $MODE" >&2
		exit 2
		;;
esac
