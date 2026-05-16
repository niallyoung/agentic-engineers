#!/usr/bin/env bash
# render-copilot.sh — render agentic-engineers' canonical skills into ~/.copilot/skills/
#
# Inputs:  $1 = REPO_ROOT (agentic-engineers repo root)
#          $2 = COPILOT root (e.g., $HOME/.copilot)
#          $3 = optional: --uninstall | --status
#
# Behavior: copies any directory under $REPO_ROOT/skills/ that contains a SKILL.md
# into $COPILOT/skills/<name>/. Top-level loose .md files in skills/ are skipped
# (those are docs, not skills). Existing user-owned skills (no source counterpart)
# are never touched.
#
# A marker file (.agentic-engine{service-name}) is written to each managed skill so
# uninstall can identify what to remove.

set -euo pipefail

REPO_ROOT="${1:?usage: render-copilot.sh REPO_ROOT COPILOT_DIR [--uninstall|--status]}"
COPILOT="${2:?usage: render-copilot.sh REPO_ROOT COPILOT_DIR [--uninstall|--status]}"
MODE="${3:-install}"

SRC_SKILLS="$REPO_ROOT/src/skills"
DST_SKILLS="$COPILOT/skills"
MARKER=".agentic-engine{service-name}"

[ -d "$SRC_SKILLS" ] || { echo "❌ no source: $SRC_SKILLS" >&2; exit 1; }

# Source shared functions (list_source_skills, list_source_agents, extract_fm, strip_fm, extract_body_model)
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

case "$MODE" in
	--uninstall)
		echo "🧹 Removing managed skills from $DST_SKILLS/..."
		count=0
		for name in $(list_source_skills); do
			target="$DST_SKILLS/$name"
			if [ -f "$target/$MARKER" ]; then
				rm -rf "$target"
				echo "  removed $name"
				count=$((count + 1))
			fi
		done
		echo "✅ Removed $count managed skill(s)"
		;;

	--status)
		ok=0; missing=0; drift=0; foreign=0
		for name in $(list_source_skills); do
			src="$SRC_SKILLS/$name"
			dst="$DST_SKILLS/$name"
			if [ ! -d "$dst" ]; then
				echo "  ❌ $name (not installed)"
				missing=$((missing + 1))
			elif [ ! -f "$dst/$MARKER" ]; then
				echo "  ⚠️  $name (exists but not managed by us)"
				foreign=$((foreign + 1))
			elif diff -rq "$src" "$dst" --exclude="$MARKER" --exclude=".DS_Store" --exclude=".git" >/dev/null 2>&1; then
				echo "  ✅ $name"
				ok=$((ok + 1))
			else
				echo "  🔄 $name (drift)"
				drift=$((drift + 1))
			fi
		done
		echo "  --- $ok in sync, $drift drift, $missing missing, $foreign foreign ---"
		;;

	install|"")
		echo "📦 Rendering skills → $DST_SKILLS/..."
		mkdir -p "$DST_SKILLS"
		count=0
		for name in $(list_source_skills); do
			src="$SRC_SKILLS/$name"
			dst="$DST_SKILLS/$name"
			# If destination exists and is NOT managed by us, refuse to overwrite
			if [ -d "$dst" ] && [ ! -f "$dst/$MARKER" ]; then
				echo "  ⚠️  skipping $name — exists at $dst and is not managed by us"
				continue
			fi
			rsync -a --delete --exclude='.DS_Store' --exclude='.git' "$src/" "$dst/"
			date -u +"%Y-%m-%dT%H:%M:%SZ" > "$dst/$MARKER"
			echo "  rendered $name"
			count=$((count + 1))
		done
		echo "✅ Rendered $count skill(s) to $DST_SKILLS/"
		;;

	*)
		echo "unknown mode: $MODE" >&2
		exit 2
		;;
esac
