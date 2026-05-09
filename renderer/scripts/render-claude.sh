#!/usr/bin/env bash
# render-claude.sh — render agentic-engineers canonical specs into ~/.claude/
#
# Inputs:  $1 = REPO_ROOT (agentic-engineers repo root)
#          $2 = CLAUDE root (e.g., $HOME/.claude)
#          $3 = optional: --uninstall | --status
#
# Renders:
#   - Skills:  src/skills/<name>/  (containing SKILL.md)  →  ~/.claude/skills/<name>/
#              (Claude Code skill format == Copilot skill format == agentic-engineers skill format)
#   - Agents:  src/agents/<name>-agent.md   →  ~/.claude/agents/<name>.md
#              (frontmatter transformed to Claude Code subagent shape)
#
# Marker file (.agentic-engine{service-name}) tracks which targets are ours.
# Existing user files are never overwritten.

set -euo pipefail

REPO_ROOT="${1:?usage: render-claude.sh REPO_ROOT CLAUDE_DIR [--uninstall|--status]}"
CLAUDE="${2:?usage: render-claude.sh REPO_ROOT CLAUDE_DIR [--uninstall|--status]}"
MODE="${3:-install}"

SRC_SKILLS="$REPO_ROOT/src/skills"
SRC_AGENTS="$REPO_ROOT/src/agents"
DST_SKILLS="$CLAUDE/skills"
DST_AGENTS="$CLAUDE/agents"
SKILL_MARKER=".agentic-engine{service-name}"
# Agents are single files; we use a sidecar manifest to track managed names.
AGENT_MANIFEST="$DST_AGENTS/.agentic-engine{service-name}"

list_source_skills() {
	local d
	for d in "$SRC_SKILLS"/*/; do
		[ -f "$d/SKILL.md" ] || continue
		basename "$d"
	done
}

list_source_agents() {
	local f
	for f in "$SRC_AGENTS"/*-agent.md; do
		[ -f "$f" ] || continue
		basename "$f" "-agent.md"
	done
}

# Map "claude-haiku-4-5" → "haiku", "claude-sonnet-4-6" → "sonnet", "claude-opus-4-7" → "opus"
map_model() {
	case "$1" in
		*haiku*) echo "haiku" ;;
		*sonnet*) echo "sonnet" ;;
		*opus*) echo "opus" ;;
		*) echo "" ;;
	esac
}

# Extract a frontmatter field value: extract_fm <file> <key>
extract_fm() {
	awk -v key="$2" '
		/^---$/ { fm = !fm; next }
		fm && $0 ~ "^"key":" {
			sub("^"key":[ \t]*", "", $0)
			sub(/[ \t]+$/, "", $0)
			print
			exit
		}
	' "$1"
}

# Strip source frontmatter (everything between first two --- lines), leaving body
strip_fm() {
	awk '
		/^---$/ { if (++count == 2) { in_body = 1; next } else next }
		in_body { print }
	' "$1"
}

# Extract Model: line from agent body if frontmatter doesn't have it
extract_body_model() {
	grep -m1 -E "^\*?\*?Model\*?\*?:" "$1" 2>/dev/null | sed -E 's/.*[Mm]odel[^:]*:[ *]*//; s/\*+$//; s/[ \t]+$//'
}

case "$MODE" in
	--uninstall)
		echo "🧹 Removing managed files from $CLAUDE/..."
		# Skills
		count_s=0
		for name in $(list_source_skills); do
			t="$DST_SKILLS/$name"
			if [ -f "$t/$SKILL_MARKER" ]; then
				rm -rf "$t"; count_s=$((count_s + 1))
			fi
		done
		# Agents (per manifest)
		count_a=0
		if [ -f "$AGENT_MANIFEST" ]; then
			while IFS= read -r name; do
				[ -n "$name" ] || continue
				rm -f "$DST_AGENTS/$name.md"
				count_a=$((count_a + 1))
			done < "$AGENT_MANIFEST"
			rm -f "$AGENT_MANIFEST"
		fi
		echo "✅ Removed $count_s skill(s), $count_a agent(s)"
		;;

	--status)
		# Skills
		ok=0; missing=0; drift=0; foreign=0
		for name in $(list_source_skills); do
			src="$SRC_SKILLS/$name"; dst="$DST_SKILLS/$name"
			if [ ! -d "$dst" ]; then echo "  ❌ skill $name (not installed)"; missing=$((missing + 1))
			elif [ ! -f "$dst/$SKILL_MARKER" ]; then echo "  ⚠️  skill $name (foreign)"; foreign=$((foreign + 1))
			elif diff -rq "$src" "$dst" --exclude="$SKILL_MARKER" --exclude=".DS_Store" --exclude=".git" >/dev/null 2>&1; then echo "  ✅ skill $name"; ok=$((ok + 1))
			else echo "  🔄 skill $name (drift)"; drift=$((drift + 1)); fi
		done
		echo "  skills: $ok ok / $drift drift / $missing missing / $foreign foreign"
		# Agents
		ok=0; missing=0; foreign=0
		for name in $(list_source_agents); do
			t="$DST_AGENTS/$name.md"
			if [ ! -f "$t" ]; then echo "  ❌ agent $name (not installed)"; missing=$((missing + 1))
			elif [ -f "$AGENT_MANIFEST" ] && grep -qx "$name" "$AGENT_MANIFEST"; then echo "  ✅ agent $name"; ok=$((ok + 1))
			else echo "  ⚠️  agent $name (foreign)"; foreign=$((foreign + 1)); fi
		done
		echo "  agents: $ok ok / $missing missing / $foreign foreign"
		;;

	install|"")
		mkdir -p "$DST_SKILLS" "$DST_AGENTS"
		# 1. Skills: rsync directories with SKILL.md
		echo "📦 Rendering skills → $DST_SKILLS/..."
		count_s=0
		for name in $(list_source_skills); do
			src="$SRC_SKILLS/$name"; dst="$DST_SKILLS/$name"
			if [ -d "$dst" ] && [ ! -f "$dst/$SKILL_MARKER" ]; then
				echo "  ⚠️  skipping skill $name — foreign"
				continue
			fi
			rsync -a --delete --exclude='.DS_Store' --exclude='.git' "$src/" "$dst/"
			date -u +"%Y-%m-%dT%H:%M:%SZ" > "$dst/$SKILL_MARKER"
			count_s=$((count_s + 1))
		done

		# 2. Agents: transform frontmatter, write .md
		echo "📦 Rendering agents → $DST_AGENTS/..."
		: > "$AGENT_MANIFEST.tmp"
		count_a=0
		for name in $(list_source_agents); do
			src_file="$SRC_AGENTS/$name-agent.md"
			dst_file="$DST_AGENTS/$name.md"

			# Refuse to overwrite a foreign agent
			if [ -f "$dst_file" ] && [ -f "$AGENT_MANIFEST" ] && ! grep -qx "$name" "$AGENT_MANIFEST"; then
				echo "  ⚠️  skipping agent $name — foreign at $dst_file"
				continue
			fi
			if [ -f "$dst_file" ] && [ ! -f "$AGENT_MANIFEST" ]; then
				echo "  ⚠️  skipping agent $name — pre-existing file (no manifest yet); move it aside and re-run"
				continue
			fi

			# Pull description; fallback to first non-empty body line
			desc=$(extract_fm "$src_file" "description")
			if [ -z "$desc" ]; then
				desc=$(strip_fm "$src_file" | awk 'NF{print; exit}')
			fi
			# Pull model: frontmatter > body Model: line
			fm_model=$(extract_fm "$src_file" "model")
			body_model=$(extract_body_model "$src_file")
			model_raw="${fm_model:-$body_model}"
			model=$(map_model "$model_raw")

			{
				echo "---"
				echo "name: $name"
				echo "description: ${desc//\"/\'}"
				[ -n "$model" ] && echo "model: $model"
				echo "---"
				echo
				strip_fm "$src_file"
			} > "$dst_file"

			echo "$name" >> "$AGENT_MANIFEST.tmp"
			count_a=$((count_a + 1))
		done
		mv "$AGENT_MANIFEST.tmp" "$AGENT_MANIFEST"
		echo "✅ Rendered $count_s skill(s), $count_a agent(s)"
		;;

	*)
		echo "unknown mode: $MODE" >&2
		exit 2
		;;
esac
