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
# Marker file (.agentic-engine-claude) tracks which targets are ours.
# Existing user files are never overwritten.

set -euo pipefail

REPO_ROOT="${1:?usage: render-claude.sh REPO_ROOT CLAUDE_DIR [--uninstall|--status]}"
CLAUDE="${2:?usage: render-claude.sh REPO_ROOT CLAUDE_DIR [--uninstall|--status]}"
MODE="${3:-install}"

# ANSI color helpers — suppressed when NO_COLOR is set or stdout is not a TTY
_use_color() { [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; }
_green()  { _use_color && printf '\033[32m%s\033[0m' "$1" || printf '%s' "$1"; }
_yellow() { _use_color && printf '\033[33m%s\033[0m' "$1" || printf '%s' "$1"; }
_red()    { _use_color && printf '\033[31m%s\033[0m' "$1" || printf '%s' "$1"; }
_dim()    { _use_color && printf '\033[2m%s\033[0m'  "$1" || printf '%s' "$1"; }

SRC_SKILLS="$REPO_ROOT/src/skills"
SRC_AGENTS="$REPO_ROOT/src/agents"
DST_SKILLS="$CLAUDE/skills"
DST_AGENTS="$CLAUDE/agents"
DOCS_AGENTS="$REPO_ROOT/docs/AGENTS.md"
SKILL_MARKER=".agentic-engine-claude"
# Agents are single files; we use a sidecar manifest to track managed names.
AGENT_MANIFEST="$DST_AGENTS/.agentic-engine-claude"
# Sentinel on line 1 of generated docs (CLAUDE.md/AGENTS.md) so we can tell ours
# apart from a user's own file and never overwrite or delete a foreign one.
# CLAUDE.md is the user's primary memory file — foreign protection is critical.
DOC_SENTINEL='<!-- managed by agentic-engineers render-claude.sh'

# Source shared functions (list_source_skills, list_source_agents, extract_fm, strip_fm, extract_body_model)
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

# Map "claude-haiku-4.5" → "haiku", "claude-sonnet-4.6" → "sonnet", "claude-opus-4.7" → "opus"
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

# parse_agents_md() and lookup_agent_metadata() are defined in lib.sh (sourced above)

# Per-role tool allow-list for Claude Code subagents.
#
# Claude Code supports a `tools:` frontmatter key on subagents: a comma-separated
# allow-list of tools the subagent may use. When omitted, the subagent inherits
# ALL tools (no restriction). Emitting a per-role list applies least-privilege,
# mirroring the OpenCode per-role permission matrix in render-opencode.sh and the
# canonical matrix in docs/CONTRIBUTING/README.md (Phase 4).
#
# Tool name reference (Claude Code built-ins):
#   Read, Glob, Grep, WebFetch, WebSearch — read/research (granted to all roles)
#   Edit, Write, Bash                      — mutation/execution (implementers only)
#   Task                                   — spawn subagents (orchestrator/senior)
#
# Returns a comma-separated tool list on stdout (empty for "inherit all").
claude_tools_for_role() {
	local role="$1"
	local base="Read, Glob, Grep, WebFetch"
	case "$role" in
		orchestrator)
			# Routing-only entry point: no edit/bash, but may spawn subagents.
			echo "$base, WebSearch, Task" ;;
		principal-engineer)
			echo "$base, WebSearch, Edit, Write, Bash" ;;
		senior-engineer)
			echo "$base, WebSearch, Edit, Write, Bash, Task" ;;
		engineer)
			echo "$base, Edit, Write, Bash" ;;
		security-engineer)
			echo "$base, WebSearch, Edit, Write, Bash" ;;
		lead-engineer)
			# Read-only review role.
			echo "$base, WebSearch" ;;
		quality-engineer)
			# Read-only review role.
			echo "$base" ;;
		model-engineer)
			# Read-only analysis role.
			echo "$base, WebSearch" ;;
		*)
			# Unknown role: omit (inherit all) rather than risk over-restriction.
			echo "" ;;
	esac
}

# Write a managed framework doc with a sentinel on line 1, refusing to overwrite
# a foreign (user-authored) file of the same name. Used for CLAUDE.md/AGENTS.md.
# Usage: write_managed_doc <dst_path> <producer_fn>
#   producer_fn: name of a function that emits the doc BODY to stdout
write_managed_doc() {
	local dst="$1" producer="$2" label
	label=$(basename "$dst")
	if [ -f "$dst" ] && ! head -n1 "$dst" | grep -q "$DOC_SENTINEL"; then
		echo "  $(_yellow "⚠️  skipping $label — foreign file at $dst (move it aside to let the framework manage it)")"
		return 0
	fi
	{
		echo "$DOC_SENTINEL; do not edit directly — re-render overwrites it. -->"
		"$producer"
	} > "$dst"
	echo "  $(_green "✅") $label"
}

# Body producer: ~/.claude/AGENTS.md — canonical framework rules + roster.
emit_agents_doc() {
	cat "$DOCS_AGENTS"
}

# Body producer: ~/.claude/CLAUDE.md — concise, self-contained pointer to the
# installed agents and skills (Claude Code memory file). Kept short on purpose.
emit_claude_doc() {
	cat <<'DOC'
# Agentic Engineers Framework — Claude Code Integration

You are part of the **agentic-engineers** distributed AI orchestration system.
Eight specialised agents collaborate via a structured DELEGATE/HANDBACK protocol
on a queue-based work pipeline.

## Available agents

Invoke a specialist with `@<agent-name>`:

- `@orchestrator` — Task routing and team coordination
- `@engineer` — Implementation of well-scoped tasks
- `@senior-engineer` — Complex problem-solving and planning
- `@lead-engineer` — Code review and quality assurance
- `@quality-engineer` — Post-implementation verification
- `@principal-engineer` — Cross-service architecture decisions
- `@security-engineer` — Security analysis and threat modeling
- `@model-engineer` — Cost/quality model-routing recommendations

## Where things live

- Agent definitions: `~/.claude/agents/<name>.md`
- Skills: `~/.claude/skills/<name>/`
- Full framework rules, routing decision tree, and protocol: `~/.claude/AGENTS.md`

For the authoritative protocol and roster, read `~/.claude/AGENTS.md`.
DOC
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
				# Validate the manifest entry is a safe, simple name before using it
				# in a destructive rm. Reject anything containing path separators,
				# '..', or other characters that could escape $DST_AGENTS.
				if [[ "$name" =~ ^[A-Za-z0-9_-]+$ ]]; then
					rm -f "$DST_AGENTS/$name.md"
					count_a=$((count_a + 1))
				else
					echo "  $(_yellow "⚠️  WARNING: skipping invalid name in manifest: $name")" >&2
				fi
			done < "$AGENT_MANIFEST"
			rm -f "$AGENT_MANIFEST"
		fi
		# Framework docs: remove only files carrying our sentinel (never a user's).
		count_d=0
		for doc in "$CLAUDE/CLAUDE.md" "$CLAUDE/AGENTS.md"; do
			if [ -f "$doc" ] && head -n1 "$doc" | grep -q "$DOC_SENTINEL"; then
				rm -f "$doc"; count_d=$((count_d + 1))
			elif [ -f "$doc" ]; then
				echo "  $(_yellow "⚠️  keeping $(basename "$doc") — foreign (not managed by us)")"
			fi
		done
		echo "✅ Removed $count_s skill(s), $count_a agent(s), $count_d doc(s)"
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
		# Framework docs
		for doc in "$CLAUDE/CLAUDE.md" "$CLAUDE/AGENTS.md"; do
			label=$(basename "$doc")
			if [ ! -f "$doc" ]; then echo "  ❌ $label (not installed)"
			elif head -n1 "$doc" | grep -q "$DOC_SENTINEL"; then echo "  ✅ $label"
			else echo "  ⚠️  $label (foreign)"; fi
		done
		;;

	install|"")
		mkdir -p "$DST_SKILLS" "$DST_AGENTS"
		# 1. Skills: rsync directories with SKILL.md
		echo "📦 Rendering skills → $DST_SKILLS/..."
		count_s=0
		install_start=$(date +%s)
		for name in $(list_source_skills); do
			src="$SRC_SKILLS/$name"; dst="$DST_SKILLS/$name"
			if [ -d "$dst" ] && [ ! -f "$dst/$SKILL_MARKER" ]; then
				echo "  $(_yellow "⚠️  skipping skill $name — foreign")"
				continue
			fi
			skill_start=$(date +%s)
			_use_color && printf '\r  ⏳ %-30s' "$name"
			rsync -a --delete --exclude='.DS_Store' --exclude='.git' "$src/" "$dst/"
			date -u +"%Y-%m-%dT%H:%M:%SZ" > "$dst/$SKILL_MARKER"
			skill_end=$(date +%s)
			skill_duration=$(( skill_end - skill_start ))
			_use_color && printf '\r'
			echo "  $(_green "✅") $name $(_dim "(${skill_duration}s)")"
			count_s=$((count_s + 1))
		done

		# 2. Parse canonical agent definitions from docs/AGENTS.md
		echo "📖 Parsing canonical agent definitions from docs/AGENTS.md..."
		AGENTS_MD="$REPO_ROOT/docs/AGENTS.md"
		AGENTS_MAP=$(mktemp)
		# Clean up the temp map on normal exit AND on interrupt/terminate signals.
		# Single-quote the command so $AGENTS_MAP is expanded when the trap fires,
		# not when the trap is installed.
		trap 'rm -f "$AGENTS_MAP"' EXIT INT TERM
		
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
				echo "  $(_yellow "⚠️  skipping agent $name — foreign at $dst_file")"
				continue
			fi
			if [ -f "$dst_file" ] && [ ! -f "$AGENT_MANIFEST" ]; then
				echo "  $(_yellow "⚠️  skipping agent $name — pre-existing file (no manifest yet); move it aside and re-run")"
				continue
			fi

			# Lookup canonical metadata from docs/AGENTS.md
			canonical_metadata=$(lookup_agent_metadata "$name" "$AGENTS_MAP")
			if [ -z "$canonical_metadata" ]; then
				echo "  $(_yellow "⚠️  skipping agent $name — not found in docs/AGENTS.md")"
				continue
			fi
			
			# Parse canonical metadata: model|effort|description
			model_raw=$(echo "$canonical_metadata" | cut -d'|' -f1)
			effort=$(echo "$canonical_metadata" | cut -d'|' -f2)
			desc=$(echo "$canonical_metadata" | cut -d'|' -f3-)
			model=$(map_model "$model_raw")

		# Protocol declaration: read machine-readable capability keys from the
		# source agent frontmatter so the harness can detect protocol support.
		accepts_list=$(extract_fm_list "$src_file" "accepts")
		returns_list=$(extract_fm_list "$src_file" "returns")
		role_val=$(extract_fm "$src_file" "role")
		[ -n "$role_val" ] || role_val="$name"

		# Per-role least-privilege tool allow-list (Claude Code `tools:` key).
		tools_list=$(claude_tools_for_role "$name")

		{
			echo "---"
			echo "name: $name"
			desc_escaped=$(printf '%s' "$desc" | yaml_escape_inline)
			printf 'description: "%s"\n' "$desc_escaped"
			[ -n "$model" ] && echo "model: $model"
			[ -n "$tools_list" ] && echo "tools: $tools_list"
			[ -n "$accepts_list" ] && echo "accepts: [$accepts_list]"
			[ -n "$returns_list" ] && echo "returns: [$returns_list]"
			echo "role: $role_val"
			echo "---"
			echo
			strip_fm "$src_file"
		} > "$dst_file"

			echo "$name" >> "$AGENT_MANIFEST.tmp"
			echo "  $(_green "✅") agent $name"
			count_a=$((count_a + 1))
		done
		mv "$AGENT_MANIFEST.tmp" "$AGENT_MANIFEST"

		# 2.5 Framework documentation: generate CLAUDE.md + AGENTS.md.
		# Generated (not copied from a stale dist artifact) so the files always
		# exist, and marker-protected so a user's own CLAUDE.md/AGENTS.md is never
		# overwritten. Runs for both dist rendering and home install.
		echo "📖 Writing framework docs → $CLAUDE/..."
		if [ -f "$DOCS_AGENTS" ]; then
			write_managed_doc "$CLAUDE/AGENTS.md" emit_agents_doc
		else
			echo "  $(_yellow "⚠️  skipping AGENTS.md — canonical source not found at $DOCS_AGENTS")" >&2
		fi
		write_managed_doc "$CLAUDE/CLAUDE.md" emit_claude_doc

		install_end=$(date +%s)
		install_duration=$(( install_end - install_start ))
		echo "✅ Rendered $count_s skill(s), $count_a agent(s) $(_dim "(${install_duration}s total)")"

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
