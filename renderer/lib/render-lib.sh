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
#
#   Frontmatter manipulation:
#     - extract_fm <file> <key>             — extract a frontmatter field value
#     - extract_fm_list <file> <key>        — extract a frontmatter list as CSV
#     - strip_fm <file>                     — strip frontmatter, return body
#     - extract_body_model <file>           — extract a body "Model:" line
#
#   Validation:
#     - validate_frontmatter <file> <type>  — ensure required fields exist
#     - is_safe_entity_name <name>          — reject unsafe names before path use
#
#   Canonical roster:
#     - parse_agents_md <agents_md>         — parse the src/AGENTS.md roster table
#     - lookup_agent_metadata <name> <map>  — look up one roster row
#
#   Utilities:
#     - yaml_escape_inline <text>           — escape text for YAML inline values
#     - map_model <model_id>                — map full model name to short form
#
#   Cleanup / pruning:
#     - prune_excluded_cruft <dst_dir>      — remove tests//__pycache__/*.pyc cruft
#     - prune_orphaned_skills <dst> <src> <marker>
#     - prune_orphaned_agents <dst> <src> <prev_manifest_names>

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

# ============================================================================
# FRONTMATTER MANIPULATION FUNCTIONS
# ============================================================================

# Extract a frontmatter field value: extract_fm <file> <key>
# Returns the value of the given key from YAML frontmatter (the block between
# the opening --- on line 1 and the FIRST closing ---). Deliberately does not
# toggle on later --- lines: agent/skill bodies contain example YAML blocks
# with their own --- delimiters, which previously re-entered "frontmatter"
# state and caused false key matches (e.g. effort: inside an example DELEGATE).
# Returns empty string if key not found.
extract_fm() {
	local file="$1" key="$2"
	awk -v key="$key" '
		NR == 1 && /^---$/ { fm = 1; next }
		fm && /^---$/ { exit }
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
		*fable*)  echo "fable" ;;
		gpt-5*)   echo "gpt-5" ;;
		gpt-4*)   echo "gpt-4" ;;
		*)        echo "" ;;
	esac
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
			# Replace escaped pipes with placeholder to protect them from splitting
			gsub(/\\\|/, "__ESCAPED_PIPE__")
			n = split($0, fields, "|")
			if (n < 5) next
			for (i = 1; i <= n; i++) {
				gsub(/^[ \t]+|[ \t]+$/, "", fields[i])
				# Restore escaped pipes in each field
				gsub(/__ESCAPED_PIPE__/, "|", fields[i])
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
# EXCLUDED-CRUFT CLEANUP
# ============================================================================

# Remove cruft (tests/, __pycache__, .pytest_cache dirs; loose *.pyc files)
# from an already-installed managed skill dir, at any depth. This exists
# because those patterns are excluded from every renderer's skill rsync
# invocation (see docs/RENDERING.md nested-precedence contract) — an OLDER
# renderer version shipped them into managed skill dirs before the excludes
# were added, and plain `rsync --delete` never removes an EXCLUDED path (it
# only removes paths that would otherwise be part of the transfer), so they
# were permanently orphaned inside otherwise-still-managed dirs.
#
# NOTE on why this is a find-based walk rather than `rsync --delete-excluded`
# (task-2026-08-15-fix-renderer-bugs FIX 3): --delete-excluded plus a
# `--filter='protect AGENTS.md'` guard was the originally proposed fix, but
# empirical testing (four separate tmp-dir trials, order and pattern
# permutations) proved it unsafe on this project's actual `rsync` — macOS
# ships `openrsync` (BSD's rsync replacement, protocol-29 "2.6.9 compatible")
# as /usr/bin/rsync, not GNU rsync, and in that implementation
# --delete-excluded silently disables ALL receiver-side protect/hide filter
# rules the moment it's present on the command line — not just the ones
# matching the same pattern. Confirmed: even a bare `--filter='protect
# AGENTS.md'` with NO --exclude='AGENTS.md' at all still lost AGENTS.md the
# instant --delete-excluded was added. Shipping the suggested flag
# combination would have been a live-install data-loss regression on this
# exact machine. This helper sidesteps the whole interaction: the rsync
# invocation stays exactly as before (plain --delete + --exclude, which
# already correctly leaves excluded files/AGENTS.md untouched — verified),
# and cruft removal is a separate, portable, rsync-implementation-independent
# pass that can never touch anything named AGENTS.md because it only ever
# matches the specific cruft names/patterns below.
#
# Usage: prune_excluded_cruft DST_DIR
prune_excluded_cruft() {
	local dst="$1"
	[ -d "$dst" ] || return 0

	# Cruft directories, anywhere under dst (depth-first so nested cruft
	# inside another cruft dir is handled before its now-partially-emptied
	# parent is matched and removed too — each match is independently safe
	# via `rm -rf`, which tolerates already-removed sub-paths).
	find "$dst" -depth \( -type d \( -name 'tests' -o -name '__pycache__' -o -name '.pytest_cache' \) \) -print0 2>/dev/null \
		| while IFS= read -r -d '' d; do
			rm -rf "$d"
		done

	# Loose *.pyc files, anywhere under dst.
	find "$dst" -type f -name '*.pyc' -print0 2>/dev/null \
		| while IFS= read -r -d '' f; do
			rm -f "$f"
		done
}

# ============================================================================
# ORPHAN PRUNING
# ============================================================================

# Validate that a name is safe to use as a single path component when building
# a deletion path (e.g. "$dst_agents/$name.md" in prune_orphaned_agents below).
# Only letters, digits, hyphen, underscore — no '.', no '/', no other
# metacharacters — so a tampered manifest line (e.g. "../../x") can never walk
# outside the managed directory. Mirrors the validation style already used in
# scripts/audit_append.py's _validate_path_component() (same defense-in-depth
# rationale — untrusted content read from disk, about to be used in a path).
# Usage: is_safe_entity_name <name>  (bash return code 0 == safe)
is_safe_entity_name() {
	local name="$1"
	[[ "$name" =~ ^[A-Za-z0-9_-]+$ ]]
}

# Prune orphaned managed skill directories under DST_SKILLS: dirs that carry
# the renderer's SKILL_MARKER (i.e. WE installed them on a previous render)
# but whose source skill no longer exists under SRC_SKILLS (a later slimdown
# round deleted it upstream, and the plain "for name in $(list_source_skills)"
# install loop never revisits what's already on disk to notice).
#
# Safety invariant — mirrors the "skipping skill X — foreign" guard already
# used by every renderer's install loop, not a reinvention of it:
#   - marker ABSENT  => foreign (not ours) => NEVER touched, no matter what.
#   - marker PRESENT + name still in the current source set => current, keep.
#   - marker PRESENT + name NOT in the current source set   => orphan, prune.
#
# Usage: prune_orphaned_skills DST_SKILLS SRC_SKILLS SKILL_MARKER
# Unconditionally removes (there is no dry-run mode) and always prints a
# single report line, e.g.:
#   🧹 pruned 3 orphaned managed skill(s): foo, bar, baz
#   🧹 pruned 0 orphaned managed skill(s)
prune_orphaned_skills() {
	local dst_skills="$1" src_skills="$2" marker="$3"

	if [ ! -d "$dst_skills" ]; then
		echo "  🧹 pruned 0 orphaned managed skill(s)"
		return 0
	fi

	# Current source-skill-name set, newline-delimited with sentinel newlines
	# on both ends so a plain substring `case` match can't false-positive on
	# a name that is a substring of another name.
	local current_names
	current_names=$'\n'"$(list_source_skills "$src_skills")"$'\n'

	local pruned=() d name
	for d in "$dst_skills"/*/; do
		[ -d "$d" ] || continue
		name=$(basename "$d")
		case "$current_names" in
			*$'\n'"$name"$'\n'*) continue ;;  # still a current source skill — keep
		esac
		if [ -f "$d/$marker" ]; then
			rm -rf "$d"
			pruned+=("$name")
		fi
		# else: no marker => foreign => leave untouched, even though its name
		# is not a current source skill.
	done

	if [ "${#pruned[@]}" -gt 0 ]; then
		local joined
		joined=$(IFS=', '; echo "${pruned[*]}")
		echo "  🧹 pruned ${#pruned[@]} orphaned managed skill(s): $joined"
	else
		echo "  🧹 pruned 0 orphaned managed skill(s)"
	fi
}

# Prune orphaned managed agent files: an agent .md file we installed on a
# PREVIOUS render (its base name was listed in AGENT_MANIFEST before this
# run's install loop rebuilt it) whose source agent no longer exists under
# SRC_AGENTS (renamed/deleted upstream) — mirrors prune_orphaned_skills()
# above, adapted for agents' trust model.
#
# Agents have no per-file marker like skills' SKILL_MARKER. Instead, every
# renderer's agent-install loop already treats manifest membership itself as
# the ours-vs-foreign boundary: it refuses to overwrite a dst file that
# exists but is NOT listed in AGENT_MANIFEST (see the "skipping agent X —
# foreign" guards in render-claude.sh / render-opencode.sh). By that same
# construction, every name that WAS in the manifest is one we installed —
# so if such a name has since dropped out of the current source-agent set,
# it is safe to prune without any separate per-file marker check.
#
# Usage: prune_orphaned_agents DST_AGENTS SRC_AGENTS PREV_MANIFEST_NAMES
#   PREV_MANIFEST_NAMES: newline-separated agent names read from
#   AGENT_MANIFEST by the CALLER before this run's install loop overwrites
#   it (pass "" if the manifest didn't exist yet — nothing to prune).
# Unconditionally removes (there is no dry-run mode) and always prints a
# single report line, e.g.:
#   🧹 pruned 2 orphaned managed agent(s): foo, bar
#   🧹 pruned 0 orphaned managed agent(s)
prune_orphaned_agents() {
	local dst_agents="$1" src_agents="$2" prev_manifest_names="$3"

	if [ -z "$prev_manifest_names" ]; then
		echo "  🧹 pruned 0 orphaned managed agent(s)"
		return 0
	fi

	local current_names
	current_names=$'\n'"$(list_source_agents "$src_agents")"$'\n'

	local pruned=() name
	while IFS= read -r name; do
		[ -n "$name" ] || continue
		# Defend against a tampered/corrupted manifest line before it is ever
		# used to build a deletion path (LOW1 — path traversal hardening):
		# reject/skip and log, never silently proceed.
		if ! is_safe_entity_name "$name"; then
			echo "  ⚠️  skipping invalid manifest entry (unsafe name): $name" >&2
			continue
		fi
		case "$current_names" in
			*$'\n'"$name"$'\n'*) continue ;;  # still a current source agent — keep
		esac
		if [ -f "$dst_agents/$name.md" ]; then
			rm -f "$dst_agents/$name.md"
			pruned+=("$name")
		fi
		# else: previously-managed name has no dst file anymore anyway — nothing to prune.
	done <<< "$prev_manifest_names"

	if [ "${#pruned[@]}" -gt 0 ]; then
		local joined
		joined=$(IFS=', '; echo "${pruned[*]}")
		echo "  🧹 pruned ${#pruned[@]} orphaned managed agent(s): $joined"
	else
		echo "  🧹 pruned 0 orphaned managed agent(s)"
	fi
}

# ============================================================================
# END render-lib.sh
# ============================================================================
