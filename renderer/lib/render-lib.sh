#!/usr/bin/env bash
# render-lib.sh — unified rendering library for agentic-engineers
#
# Consolidates common functions used by all render scripts (agents, skills, specs).
# Provides consistent naming transformation, frontmatter extraction, and validation.
#
# Source this file from any render script:
#   source "$(dirname "$0")/../lib/render-lib.sh"
#
# Available functions:
#   Entity listing:
#     - list_source_skills [SRC_SKILLS]     — enumerate skill dirs containing SKILL.md
#     - list_source_agents [SRC_AGENTS]     — enumerate agent source files (*-agent.md)
#     - list_source_specs [SRC_SPECS]       — enumerate spec source files (SPEC.md)
#
#   Frontmatter manipulation:
#     - extract_fm <file> <key>             — extract a frontmatter field value
#     - strip_fm <file>                     — strip frontmatter, return body
#
#   Entity naming (core transformation logic):
#     - get_entity_name <file>              — extract canonical entity name from frontmatter
#     - get_entity_type <entity>            — infer entity type from naming
#     - transform_entity_filename <src> <dst_dir> <entity_type> — unified transformation
#
#   Validation:
#     - validate_frontmatter <file> <type>  — ensure required fields exist
#     - validate_entity_structure <dst_file> — verify output format consistency
#     - validate_deployment <dst_root>      — comprehensive deployment validation
#
#   Utilities:
#     - yaml_escape_inline <text>           — escape text for YAML inline values
#     - map_model <model_id>                — map full model name to short form
#     - emit_progress <mode> <type> <msg>   — consistent progress output

set -euo pipefail

# Color support (respects NO_COLOR and TTY detection)
_use_color() { [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; }
_green()  { _use_color && printf '\033[32m%s\033[0m' "$1" || printf '%s' "$1"; }
_yellow() { _use_color && printf '\033[33m%s\033[0m' "$1" || printf '%s' "$1"; }
_red()    { _use_color && printf '\033[31m%s\033[0m' "$1" || printf '%s' "$1"; }
_dim()    { _use_color && printf '\033[2m%s\033[0m'  "$1" || printf '%s' "$1"; }

# ============================================================================
# ENTITY LISTING FUNCTIONS
# ============================================================================

# Enumerate source skills (dirs containing SKILL.md).
# Usage: list_source_skills [SRC_SKILLS_PATH]
#   If SRC_SKILLS_PATH is omitted, uses $SRC_SKILLS env var (for backward compat).
list_source_skills() {
	local src_dir="${1:-${SRC_SKILLS:-}}"
	[ -n "$src_dir" ] || { echo "error: SRC_SKILLS not set" >&2; return 1; }
	
	local d
	for d in "$src_dir"/*/; do
		[ -f "$d/SKILL.md" ] || continue
		basename "$d"
	done
}

# Enumerate source agents (*-agent.md files), returning the base name without -agent.md.
# Usage: list_source_agents [SRC_AGENTS_PATH]
#   If SRC_AGENTS_PATH is omitted, uses $SRC_AGENTS env var (for backward compat).
list_source_agents() {
	local src_dir="${1:-${SRC_AGENTS:-}}"
	[ -n "$src_dir" ] || { echo "error: SRC_AGENTS not set" >&2; return 1; }
	
	local f
	for f in "$src_dir"/*-agent.md; do
		[ -f "$f" ] || continue
		basename "$f" "-agent.md"
	done
}

# Enumerate source specs (SPEC.md files), returning directory name.
# Usage: list_source_specs [SRC_SPECS_PATH]
#   If SRC_SPECS_PATH is omitted, uses $SRC_SPECS env var.
list_source_specs() {
	local src_dir="${1:-${SRC_SPECS:-}}"
	[ -n "$src_dir" ] || { echo "error: SRC_SPECS not set" >&2; return 1; }
	
	local d
	for d in "$src_dir"/*/; do
		[ -f "$d/SPEC.md" ] || continue
		basename "$d"
	done
}

# ============================================================================
# FRONTMATTER MANIPULATION FUNCTIONS
# ============================================================================

# Extract a frontmatter field value: extract_fm <file> <key>
# Returns the value of the given key from YAML frontmatter (between --- delimiters).
# Returns empty string if key not found.
extract_fm() {
	local file="$1" key="$2"
	awk -v key="$key" '
		/^---$/ { fm = !fm; next }
		fm && $0 ~ "^"key":" {
			sub("^"key":[ \t]*", "", $0)
			sub(/[ \t]+$/, "", $0)
			print
			exit
		}
	' "$file"
}

# Returns a YAML block-list value from frontmatter as a comma-joined string.
# Handles both inline arrays (key: [A, B]) and block lists:
#   key:
#     - A
#     - B
# Returns empty string if the key is absent or has no items.
# Usage: extract_fm_list <file> <key>
extract_fm_list() {
	local file="$1" key="$2"
	awk -v key="$key" '
		/^---$/ { fm = !fm; if (!fm) exit; next }
		!fm { next }
		# Inline array form: key: [A, B]
		$0 ~ "^"key":[ \t]*\\[" {
			line = $0
			sub("^"key":[ \t]*\\[", "", line)
			sub(/\].*$/, "", line)
			gsub(/[ \t]/, "", line)
			print line
			exit
		}
		# Block list header: key:
		$0 ~ "^"key":[ \t]*$" { collecting = 1; next }
		collecting {
			# A frontmatter key at column 0 ends the block list.
			if ($0 ~ /^[A-Za-z0-9_]+:/) { collecting = 0 }
			else if ($0 ~ /^[ \t]*-[ \t]*/) {
				item = $0
				sub(/^[ \t]*-[ \t]*/, "", item)
				sub(/[ \t]+$/, "", item)
				out = (out == "" ? item : out "," item)
			}
		}
		END { if (out != "") print out }
	' "$file"
}

# Strip source frontmatter (everything between first two --- lines), leaving body.
# Usage: strip_fm <file>
strip_fm() {
	local file="$1"
	awk '
		/^---$/ { if (++count == 2) { in_body = 1; next } else next }
		in_body { print }
	' "$file"
}

# Extract Model: line from agent body if frontmatter doesn't have it.
# Usage: extract_body_model <file>
extract_body_model() {
	grep -m1 -E "^\*?\*?Model\*?\*?:" "$1" 2>/dev/null | sed -E 's/.*[Mm]odel[^:]*:[ *]*//; s/\*+$//; s/[ \t]+$//'
}

# ============================================================================
# ENTITY NAMING & TRANSFORMATION
# ============================================================================

# Get canonical entity name from frontmatter.
# For agents/skills/specs, extracts the 'name' field from YAML frontmatter.
# Usage: get_entity_name <file>
get_entity_name() {
	local file="$1"
	[ -f "$file" ] || { echo "error: file not found: $file" >&2; return 1; }
	
	local name
	name=$(extract_fm "$file" "name")
	[ -n "$name" ] || { echo "error: 'name' field not found in frontmatter: $file" >&2; return 1; }
	
	echo "$name"
}

# Infer entity type from its characteristics.
# Usage: get_entity_type <file>
# Returns: "agent", "skill", or "spec"
get_entity_type() {
	local file="$1"
	[ -f "$file" ] || { echo "error: file not found: $file" >&2; return 1; }
	
	# Check for presence of type-specific fields
	if extract_fm "$file" "role" >/dev/null 2>&1; then
		echo "agent"
	elif extract_fm "$file" "model" >/dev/null 2>&1; then
		# Agents also have 'model', so check for agent-specific 'role' field first
		# If no 'role', but has 'model' + 'description', it might be skill or spec
		if extract_fm "$file" "scope" >/dev/null 2>&1; then
			echo "spec"
		else
			echo "skill"
		fi
	else
		echo "unknown"
	fi
}

# Transform entity filename according to unified naming convention.
# src → dst transformation:
#   - Agents:  engineer-agent.md → engineer.agent.md (based on 'name' field)
#   - Skills:  skill-dir/ → skill-dir/ (directory-based, no single file transform)
#   - Specs:   spec-dir/SPEC.md → spec-dir/SPEC.md (directory-based)
#
# Usage: transform_entity_filename <src_file> <dst_dir> <entity_type>
# Returns the destination filename (not full path).
transform_entity_filename() {
	local src_file="$1" dst_dir="$2" entity_type="$3"
	
	case "$entity_type" in
		agent)
			# Extract canonical name from frontmatter, build dest filename
			local name
			name=$(get_entity_name "$src_file") || return 1
			echo "${name}.agent.md"
			;;
		skill)
			# Skills are directory-based; no transformation needed
			basename "$src_file"
			;;
		spec)
			# Specs are directory-based; no transformation needed
			basename "$src_file"
			;;
		*)
			echo "error: unknown entity type: $entity_type" >&2
			return 1
			;;
	esac
}

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

# Validate frontmatter completeness for an entity type.
# Usage: validate_frontmatter <file> <entity_type>
#   entity_type: "agent", "skill", or "spec"
validate_frontmatter() {
	local file="$1" entity_type="${2:-unknown}"
	
	[ -f "$file" ] || { echo "error: file not found: $file" >&2; return 1; }
	
	local required=() missing=()
	
	case "$entity_type" in
		agent)
			required=("name" "description" "model" "role")
			;;
		skill)
			required=("name" "description")
			;;
		spec)
			required=("name" "version")
			;;
		*)
			required=("name" "description")
			;;
	esac
	
	for field in "${required[@]}"; do
		if ! extract_fm "$file" "$field" >/dev/null 2>&1; then
			missing+=("$field")
		fi
	done
	
	if [ ${#missing[@]} -gt 0 ]; then
		echo "error: missing required fields in $file: ${missing[*]}" >&2
		return 1
	fi
	
	return 0
}

# Validate rendered entity file structure.
# Usage: validate_entity_structure <dst_file>
validate_entity_structure() {
	local dst_file="$1"
	
	[ -f "$dst_file" ] || { echo "error: rendered file not found: $dst_file" >&2; return 1; }
	
	# Check frontmatter exists (starts with ---)
	if ! head -1 "$dst_file" | grep -q "^---$"; then
		echo "error: rendered file missing frontmatter: $dst_file" >&2
		return 1
	fi
	
	# Check name field exists and is non-empty
	local name
	name=$(extract_fm "$dst_file" "name")
	if [ -z "$name" ]; then
		echo "error: rendered file missing 'name' field: $dst_file" >&2
		return 1
	fi
	
	return 0
}

# Comprehensive deployment validation.
# Usage: validate_deployment <dst_root>
# Checks:
#   - All source agents have rendered counterparts
#   - All filenames follow naming convention
#   - Rendered files have valid frontmatter
#   - No orphaned files in destination
validate_deployment() {
	local dst_root="$1"
	[ -d "$dst_root" ] || { echo "error: destination root not found: $dst_root" >&2; return 1; }
	
	local errors=0
	
	# Check agents directory structure
	if [ -d "$dst_root/agents" ]; then
		local agent_file
		for agent_file in "$dst_root/agents"/*.md; do
			[ -f "$agent_file" ] || continue
			
			# Agent files should be named "*.agent.md"
			if ! [[ "$(basename "$agent_file")" =~ \.agent\.md$ ]]; then
				echo "error: agent file does not follow naming convention: $agent_file" >&2
				errors=$((errors + 1))
			fi
			
			# Validate structure
			if ! validate_entity_structure "$agent_file"; then
				errors=$((errors + 1))
			fi
		done
	fi
	
	# Check skills directory structure
	if [ -d "$dst_root/skills" ]; then
		local skill_dir
		for skill_dir in "$dst_root/skills"/*/; do
			[ -d "$skill_dir" ] || continue
			
			# Skills should have SKILL.md
			if [ ! -f "$skill_dir/SKILL.md" ]; then
				echo "error: skill missing SKILL.md: $skill_dir" >&2
				errors=$((errors + 1))
			fi
		done
	fi
	
	if [ $errors -gt 0 ]; then
		echo "error: validation failed with $errors error(s)" >&2
		return 1
	fi
	
	return 0
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

# YAML-escape a description for use inside double-quoted YAML value.
# Collapse newlines to spaces, replace double-quotes with single-quotes,
# normalise whitespace. Output is safe to embed as: description: "OUTPUT"
# Usage: desc_escaped=$(printf '%s' "$desc" | yaml_escape_inline)
yaml_escape_inline() {
	# Escape backslashes FIRST (before quotes/whitespace) so a trailing or embedded
	# backslash in the source description cannot corrupt the double-quoted YAML value.
	tr '\n' ' ' | sed -e 's/\\/\\\\/g' -e 's/"/'\''/g' -e 's/[[:space:]]\+/ /g' -e 's/^ //' -e 's/ $//'
}

# Map full model name to short form (for Claude Code, etc).
# claude-haiku-4.5 → haiku, claude-sonnet-4.6 → sonnet, etc.
# Usage: map_model <model_id>
map_model() {
	case "$1" in
		*haiku*)  echo "haiku" ;;
		*sonnet*) echo "sonnet" ;;
		*opus*)   echo "opus" ;;
		gpt-5*)   echo "gpt-5" ;;
		gpt-4*)   echo "gpt-4" ;;
		*)        echo "" ;;
	esac
}

# Emit progress message with consistent formatting.
# Usage: emit_progress <mode> <type> <entity_name> [extra_data]
#   mode: "human" (ANSI colors), "json", or empty (silent)
#   type: "start", "complete", "skip", "error", "summary"
emit_progress() {
	local mode="$1" type="$2" entity="$3" data="${4:-}"
	
	[ -z "$mode" ] && return 0  # No-op in silent mode
	
	local ts
	ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
	
	if [ "$mode" = "human" ]; then
		case "$type" in
			start)
				_use_color && printf '\r  ⏳ %-30s' "$entity" || printf '  ⏳ %-30s' "$entity"
				;;
			complete)
				_use_color && printf '\r  %s %-30s\n' "$(_green "✅")" "$entity" || printf '  ✅ %-30s\n' "$entity"
				;;
			skip)
				_use_color && printf '\r  %s %-30s\n' "$(_yellow "⚠️ ")" "$entity" || printf '  ⚠️  %-30s\n' "$entity"
				;;
			error)
				_use_color && printf '\r  %s %-30s\n' "$(_red "❌")" "$entity" || printf '  ❌ %-30s\n' "$entity"
				;;
			summary)
				# Summary handled by caller
				;;
		esac
	elif [ "$mode" = "json" ]; then
		# JSON output delegated to Python helper (if needed)
		:
	fi
}

# Parse src/AGENTS.md canonical agent definitions table.
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
			# Table columns: Role | Model | Effort | Multi-Model? | Use When (description)
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
	# Match the agent name as a literal string against the first '|'-delimited field.
	# Using awk with field equality (rather than grep "^name|") avoids treating
	# regex metacharacters in agent_name (e.g. '.', '+') as patterns, which could
	# otherwise match the wrong entry.
	awk -v n="$agent_name" -F'|' '$1 == n { sub(/^[^|]*\|/, ""); print; exit }' "$agents_map" || echo ""
}

# ============================================================================
# END render-lib.sh
# ============================================================================
