#!/usr/bin/env bash
# render-copilot.sh — render agentic-engineers' canonical skills into ~/.copilot/skills/
#
# Inputs:  $1 = REPO_ROOT (agentic-engineers repo root)
#          $2 = COPILOT root (e.g., $HOME/.copilot)
#          $3 = optional: --uninstall | --status | --stream | --stream=json
#
# Behavior: copies any directory under $REPO_ROOT/skills/ that contains a SKILL.md
# into $COPILOT/skills/<name>/. Top-level loose .md files in skills/ are skipped
# (those are docs, not skills). Existing user-owned skills (no source counterpart)
# are never touched.
#
# A marker file (.agentic-engine{service-name}) is written to each managed skill so
# uninstall can identify what to remove.
#
# Streaming modes:
#   --stream      : Human-readable progress with per-skill timing (ANSI colors if TTY)
#   --stream=json : Structured JSON-lines output for CI/CD pipelines (delegates to Python helper)

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

# Helper function for streaming output
_stream_emit() {
	local mode="$1" type="$2" skill="$3" data="$4"
	[ -z "$mode" ] && return 0  # No-op in default mode

	local ts
	ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

	if [ "$mode" = "human" ]; then
		# ANSI progress indicator (suppressed if not a TTY)
		if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
			case "$type" in
				start)    printf "\r  ⏳ %-30s" "$skill" ;;
				complete) printf "\r  ✅ %-30s\n" "$skill" ;;
				skip)     printf "\r  ⚠️  %-30s\n" "$skill" ;;
				error)    printf "\r  ❌ %-30s\n" "$skill" ;;
				summary)  : ;;  # handled by main echo
			esac
		fi
	fi
	# json mode is handled by Python helper (exec'd above)
}


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

	install|""|--stream|--stream=json)
		# Determine output mode
		STREAM_MODE=""
		if [ "$MODE" = "--stream" ]; then
			STREAM_MODE="human"
		elif [ "$MODE" = "--stream=json" ]; then
			STREAM_MODE="json"
			# Delegate entirely to Python helper
			exec python3 "$(dirname "$0")/../../src/harnesses/copilot_cli/streaming.py" \
				"$SRC_SKILLS" "$DST_SKILLS" "$MARKER"
		fi

		echo "📦 Rendering skills → $DST_SKILLS/..."
		mkdir -p "$DST_SKILLS"
		count=0
		total_bytes=0
		install_start=$(date +%s)

		for name in $(list_source_skills); do
			src="$SRC_SKILLS/$name"
			dst="$DST_SKILLS/$name"

			# Foreign skill protection (unchanged)
			if [ -d "$dst" ] && [ ! -f "$dst/$MARKER" ]; then
				_stream_emit "$STREAM_MODE" "skip" "$name" "{}"
				echo "  ⚠️  skipping $name — exists at $dst and is not managed by us"
				continue
			fi

			# Emit start event
			skill_start=$(date +%s)
			_stream_emit "$STREAM_MODE" "start" "$name" "{\"src\":\"$src\"}"

			# Streaming rsync: use --progress for human mode (more compatible than --info=progress2)
			# For non-streaming mode, use standard rsync
			if [ "$STREAM_MODE" = "human" ]; then
				rsync -a --delete --progress \
					--exclude='.DS_Store' --exclude='.git' \
					"$src/" "$dst/" || {
					_stream_emit "$STREAM_MODE" "error" "$name" \
						"{\"message\":\"rsync failed with exit $?\"}"
					echo "  ❌ $name — rsync failed" >&2
					continue
				}
			else
				rsync -a --delete --exclude='.DS_Store' --exclude='.git' \
					"$src/" "$dst/" || {
					echo "  ❌ $name — rsync failed" >&2
					continue
				}
			fi

			# Write marker only after successful rsync
			date -u +"%Y-%m-%dT%H:%M:%SZ" > "$dst/$MARKER"

			# Collect stats
			skill_end=$(date +%s)
			skill_duration=$(( skill_end - skill_start ))
			skill_bytes=$(du -sk "$dst" 2>/dev/null | cut -f1 || echo 0)
			total_bytes=$(( total_bytes + skill_bytes ))

			_stream_emit "$STREAM_MODE" "complete" "$name" \
				"{\"duration_s\":$skill_duration,\"kb\":$skill_bytes}"
			echo "  rendered $name (${skill_duration}s)"
			count=$((count + 1))
		done

		install_end=$(date +%s)
		install_duration=$(( install_end - install_start ))
		_stream_emit "$STREAM_MODE" "summary" "" \
			"{\"count\":$count,\"total_kb\":$total_bytes,\"duration_s\":$install_duration}"
		echo "✅ Rendered $count skill(s) to $DST_SKILLS/ (${install_duration}s, ${total_bytes}KB)"

		# 2. Git hooks: configure core.hooksPath and ensure hooks are executable
		# GitHub Copilot harness: hooks are installed from REPO_ROOT/.githooks to enforce consistency.
		# Note: Copilot uses the same git repo as OpenCode/Claude, so hooks are shared.
		if [ -d "$REPO_ROOT/.githooks" ]; then
			echo "📦 Installing git hooks from $REPO_ROOT/.githooks/..."
			git -C "$REPO_ROOT" config core.hooksPath .githooks
			for hook in "$REPO_ROOT"/.githooks/*; do
				[ -f "$hook" ] && chmod +x "$hook"
			done
			echo "✅ Git hooks installed (core.hooksPath = .githooks)"
		else
			echo "⚠️  git hooks not found at $REPO_ROOT/.githooks — skipping"
		fi
		;;

	*)
		echo "unknown mode: $MODE" >&2
		exit 2
		;;
esac
