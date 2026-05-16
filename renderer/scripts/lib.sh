#!/usr/bin/env bash
# lib.sh — shared functions for agentic-engineers renderer scripts
#
# Source this file from render-claude.sh, render-opencode.sh, render-copilot.sh:
#   source "$(dirname "$0")/lib.sh"
#
# Provides:
#   list_source_skills  SRC_SKILLS  — enumerate skill dirs containing SKILL.md
#   list_source_agents  SRC_AGENTS  — enumerate agent source files (*-agent.md)
#   extract_fm          <file> <key> — extract a frontmatter field value
#   strip_fm            <file>       — strip frontmatter, return body
#   extract_body_model  <file>       — extract Model: line from agent body
#
# Callers must set SRC_SKILLS and SRC_AGENTS before calling list_* functions.

# Enumerate source skills (dirs containing SKILL.md).
# Requires: $SRC_SKILLS to be set by caller.
list_source_skills() {
	local d
	for d in "$SRC_SKILLS"/*/; do
		[ -f "$d/SKILL.md" ] || continue
		basename "$d"
	done
}

# Enumerate source agents (*-agent.md files), returning the base name without -agent.md.
# Requires: $SRC_AGENTS to be set by caller.
list_source_agents() {
	local f
	for f in "$SRC_AGENTS"/*-agent.md; do
		[ -f "$f" ] || continue
		basename "$f" "-agent.md"
	done
}

# Extract a frontmatter field value: extract_fm <file> <key>
# Returns the value of the given key from YAML frontmatter (between --- delimiters).
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

# Strip source frontmatter (everything between first two --- lines), leaving body.
strip_fm() {
	awk '
		/^---$/ { if (++count == 2) { in_body = 1; next } else next }
		in_body { print }
	' "$1"
}

# Extract Model: line from agent body if frontmatter doesn't have it.
extract_body_model() {
	grep -m1 -E "^\*?\*?Model\*?\*?:" "$1" 2>/dev/null | sed -E 's/.*[Mm]odel[^:]*:[ *]*//; s/\*+$//; s/[ \t]+$//'
}

# YAML-escape a description for use inside double-quoted YAML value.
# Collapse newlines to spaces, replace double-quotes with single-quotes,
# normalise whitespace. Output is safe to embed as: description: "OUTPUT"
# Usage: desc_escaped=$(printf '%s' "$desc" | yaml_escape_inline)
yaml_escape_inline() {
	tr '\n' ' ' | sed -e 's/"/'\''/g' -e 's/[[:space:]]\+/ /g' -e 's/^ //' -e 's/ $//'
}

# Parse docs/AGENTS.md canonical agent definitions table.
# Returns lines of: agent_name|model|effort|description
# Usage: parse_agents_md <agents_md_file>
parse_agents_md() {
	local agents_file="$1"
	
	if [ ! -f "$agents_file" ]; then
		echo "error: $agents_file not found" >&2
		return 1
	fi
	
	awk '
		/^\| \*\*[A-Za-z]/ {
			gsub(/^\| /, "")
			gsub(/ \|$/, "")
			n = split($0, fields, "|")
			if (n < 5) next
			for (i = 1; i <= n; i++) {
				gsub(/^[ \t]+|[ \t]+$/, "", fields[i])
			}
			role = fields[1]; model = fields[2]; effort = fields[3]; description = fields[5]
			gsub(/\*\*/, "", role)
			role_lower = tolower(role)
			gsub(/ /, "-", role_lower)
			gsub(/^[ \t]+|[ \t]+$/, "", model)
			gsub(/^[ \t]+|[ \t]+$/, "", effort)
			gsub(/^[ \t]+|[ \t]+$/, "", description)
			if (role_lower && model && effort && description) {
				print role_lower "|" model "|" effort "|" description
			}
		}
	' "$agents_file"
}

# Lookup canonical agent metadata from parsed AGENTS.md map file.
# Usage: lookup_agent_metadata <agent_name> <agents_map_file>
# Returns: "model|effort|description" or empty string if not found
lookup_agent_metadata() {
	local agent_name="$1"
	local agents_map="$2"
	grep "^${agent_name}|" "$agents_map" | cut -d'|' -f2-
}
