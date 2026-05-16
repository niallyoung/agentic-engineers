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

# Source shared functions (list_source_skills, list_source_agents, extract_fm, strip_fm, extract_body_model)
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

# Map "claude-haiku-4-5" → "haiku", "claude-sonnet-4-6" → "sonnet", "claude-opus-4-7" → "opus"
# Claude Code accepts short tier names rather than fully-qualified provider/model IDs.
# Note: does not distinguish between minor versions (e.g., sonnet-4-5 vs sonnet-4-6).
map_model() {
	case "$1" in
		*haiku*) echo "haiku" ;;
		*sonnet*) echo "sonnet" ;;
		*opus*) echo "opus" ;;
		*) echo "" ;;
	esac
}

# Parse docs/AGENTS.md canonical agent definitions table.
# Returns a map of agent_name → "model|effort|description"
# Reads the markdown table starting with "| Role | Model | Effort"
# and extracts: role (normalized to lowercase with hyphens), model, effort, and use-when description.
parse_agents_md() {
	local agents_file="$1"
	local agent_name model effort description
	
	if [ ! -f "$agents_file" ]; then
		echo "error: $agents_file not found" >&2
		return 1
	fi
	
	# Extract table rows (skip header and separator lines)
	# Table format: | **RoleName** | claude-model-X-Y | effort | $cost | description |
	awk '
		/^\| \*\*[A-Za-z]/ {
			# Extract fields from markdown table row
			# Split by | and extract fields
			gsub(/^\| /, "")  # remove leading |
			gsub(/ \|$/, "")  # remove trailing |
			
			# Split by | to get fields
			n = split($0, fields, "|")
			if (n < 5) next
			
			# Trim whitespace from each field
			for (i = 1; i <= n; i++) {
				gsub(/^[ \t]+|[ \t]+$/, "", fields[i])
			}
			
			# Extract role (field 1), model (field 2), effort (field 3), skip cost (field 4), use-when (field 5)
			role = fields[1]
			model = fields[2]
			effort = fields[3]
			description = fields[5]
			
			# Normalize role: remove ** markers, convert to lowercase, replace spaces with hyphens
			gsub(/\*\*/, "", role)
			role_lower = tolower(role)
			gsub(/ /, "-", role_lower)
			
			# Normalize model: trim and keep as-is
			gsub(/^[ \t]+|[ \t]+$/, "", model)
			
			# Normalize effort: trim and keep as-is
			gsub(/^[ \t]+|[ \t]+$/, "", effort)
			
			# Normalize description: trim and keep as-is
			gsub(/^[ \t]+|[ \t]+$/, "", description)
			
			# Output: agent_name|model|effort|description
			if (role_lower && model && effort && description) {
				print role_lower "|" model "|" effort "|" description
			}
		}
	' "$agents_file"
}

# Lookup canonical agent metadata from parsed AGENTS.md
# Usage: lookup_agent_metadata <agent_name> <agents_map_file>
# Returns: "model|effort|description" or empty if not found
lookup_agent_metadata() {
	local agent_name="$1"
	local agents_map="$2"
	
	grep "^${agent_name}|" "$agents_map" | cut -d'|' -f2-
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

		# 2. Parse canonical agent definitions from docs/AGENTS.md
		echo "📖 Parsing canonical agent definitions from docs/AGENTS.md..."
		AGENTS_MD="$REPO_ROOT/docs/AGENTS.md"
		AGENTS_MAP=$(mktemp)
		trap "rm -f '$AGENTS_MAP'" EXIT
		
		if [ ! -f "$AGENTS_MD" ]; then
			echo "❌ error: $AGENTS_MD not found" >&2
			exit 1
		fi
		
		parse_agents_md "$AGENTS_MD" > "$AGENTS_MAP"
		if [ ! -s "$AGENTS_MAP" ]; then
			echo "❌ error: failed to parse agent definitions from $AGENTS_MD" >&2
			exit 1
		fi

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

			# Lookup canonical metadata from docs/AGENTS.md
			canonical_metadata=$(lookup_agent_metadata "$name" "$AGENTS_MAP")
			if [ -z "$canonical_metadata" ]; then
				echo "  ⚠️  skipping agent $name — not found in docs/AGENTS.md"
				continue
			fi
			
			# Parse canonical metadata: model|effort|description
			model_raw=$(echo "$canonical_metadata" | cut -d'|' -f1)
			effort=$(echo "$canonical_metadata" | cut -d'|' -f2)
			desc=$(echo "$canonical_metadata" | cut -d'|' -f3-)
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

		# 3. Git hooks: configure core.hooksPath and ensure hooks are executable
		# Claude Code harness: hooks are installed from REPO_ROOT/.githooks to enforce consistency.
		# Note: Claude Code uses the same git repo as OpenCode, so hooks are shared.
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
