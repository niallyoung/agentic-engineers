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
