#!/usr/bin/env bash
# render-opencode.sh — render agentic-engineers canonical specs into an OpenCode global config dir
#
# Inputs:  $1 = REPO_ROOT (agentic-engineers repo root)
#          $2 = OPENCODE root (e.g., $HOME/.config/opencode)
#          $3 = optional: --uninstall | --status
#
# Renders:
#   - opencode.jsonc  → managed config (compaction tuning, permission lockdown, instructions ref)
#   - AGENTS.md      → global rules entry-point (framework intro + mandatory constraints)
#   - Skills:        src/skills/<name>/  (containing SKILL.md)  →  $OPENCODE/skills/<name>/
#                    (OpenCode skill format == Claude Code skill format == agentic-engineers skill format)
#   - Agents:        src/agents/<name>-agent.md   →  $OPENCODE/agents/<name>.md
#                    (frontmatter rewritten to OpenCode subagent shape: mode/model/temperature/permission)
#
# Marker file (.agentic-engine{service-name}) tracks which targets are ours.
# Existing user files are never overwritten.
#
# OpenCode docs note (verified https://opencode.ai/docs/config 2026-05-15):
#   The canonical global config dir is ~/.config/opencode/ (XDG). There is no
#   documented ~/.opencode/ fallback. Pass the path you want explicitly.
#
# Mirrors render-claude.sh in style and safety model. OpenCode-specific divergences:
#   1. Emits opencode.jsonc + AGENTS.md (Claude Code has neither — uses CLAUDE.md only).
#   2. Agent frontmatter schema is OpenCode-specific (mode/model/temperature/permission).
#   3. Model IDs are fully-qualified provider/model strings (claude-foo-X.Y dotted).

set -euo pipefail

REPO_ROOT="${1:?usage: render-opencode.sh REPO_ROOT OPENCODE_DIR [--uninstall|--status]}"
OPENCODE="${2:?usage: render-opencode.sh REPO_ROOT OPENCODE_DIR [--uninstall|--status]}"
MODE="${3:-install}"

SRC_SKILLS="$REPO_ROOT/src/skills"
SRC_AGENTS="$REPO_ROOT/src/agents"
DOCS_AGENTS="$REPO_ROOT/docs/AGENTS.md"
DST_SKILLS="$OPENCODE/skills"
DST_AGENTS="$OPENCODE/agents"
DST_CONFIG="$OPENCODE/opencode.jsonc"
DST_RULES="$OPENCODE/AGENTS.md"
SKILL_MARKER=".agentic-engine{service-name}"
# Agents are single files; we use a sidecar manifest to track managed names.
AGENT_MANIFEST="$DST_AGENTS/.agentic-engine{service-name}"
# Sentinel string embedded as a JSONC comment so we can detect ours vs foreign.
# Top-level non-schema keys are rejected by OpenCode's strict config validator
# (additionalProperties: false on Config). Using `.jsonc` + `//` comment keeps
# the marker without breaking schema validation.
CONFIG_SENTINEL='// _managed_by: agentic-engineers renderer/scripts/render-opencode.sh'
# Sentinel HTML comment line 1 of AGENTS.md.
RULES_SENTINEL='<!-- managed by agentic-engineers render-opencode.sh'

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

# Map agentic-engineers canonical model id → OpenCode provider/model id.
#
# IMPORTANT: This mapping is OpenCode-install-specific for the github-copilot
# provider (the only Claude provider currently in this user's registry per
# `opencode models`). A user with the `anthropic/` provider configured would
# want different IDs (e.g., anthropic/claude-haiku-4-5 with dashed versions).
#
# Future enhancement: detect available providers from `opencode models` output
# at install time and pick the best match. For now, hardcoded github-copilot
# matches what `opencode models | grep -E '(haiku|sonnet|opus)'` returns:
#   github-copilot/claude-haiku-4.5
#   github-copilot/claude-opus-4.5
#   github-copilot/claude-opus-4.7
#   github-copilot/claude-sonnet-4.5
#   github-copilot/claude-sonnet-4.6
#
# Note: claude-opus-4-6 maps to opus-4.7 because opus-4.6 is NOT in the registry;
# 4.7 is the closest available (newer, same tier).
map_model_opencode() {
	case "$1" in
		claude-haiku-4-5|claude-haiku-4.5)   echo "github-copilot/claude-haiku-4.5" ;;
		claude-sonnet-4-6|claude-sonnet-4.6) echo "github-copilot/claude-sonnet-4.6" ;;
		claude-sonnet-4-5|claude-sonnet-4.5) echo "github-copilot/claude-sonnet-4.5" ;;
		claude-opus-4-7|claude-opus-4.7)     echo "github-copilot/claude-opus-4.7" ;;
		claude-opus-4-6|claude-opus-4.6)     echo "github-copilot/claude-opus-4.7" ;;  # closest available
		claude-opus-4-5|claude-opus-4.5)     echo "github-copilot/claude-opus-4.5" ;;
		*) echo "" ;;  # sentinel — caller warns + skips model emission
	esac
}

# Effort → temperature: deterministic-ish for low/medium, more exploratory for high/max.
effort_to_temperature() {
	case "$1" in
		low|medium) echo "0.3" ;;
		high|max)   echo "0.5" ;;
		*)          echo "0.3" ;;
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
	grep -m1 -E "^\*?\*?Model\*?\*?:" "$1" 2>/dev/null \
		| sed -E 's/.*[Mm]odel[^:]*:[ *]*//; s/\*+$//; s/[ \t]+$//'
}

# Parse docs/AGENTS.md primary roster table for a given role's (model, effort, description).
# Output: tab-separated "model<TAB>effort<TAB>description"; empty if not found.
# Role lookup is by kebab-case agent name (matches AGENT_ROLE_MAPPING from old python renderer).
docs_lookup_role() {
	local kebab="$1"
	local role
	case "$kebab" in
		orchestrator)      role="Orchestrator" ;;
		engineer)          role="Engineer" ;;
		senior-engineer)   role="Senior Engineer" ;;
		lead-engineer)     role="Lead Engineer" ;;
		quality-engineer)  role="Quality Engineer" ;;
		principal-engineer) role="Principal Engineer" ;;
		security|security-engineer) role="Security Engineer" ;;
		model-engineer)    role="Model Engineer" ;;
		*) return 0 ;;
	esac
	[ -f "$DOCS_AGENTS" ] || return 0
	awk -v role="$role" -F'|' '
		$0 ~ "\\| \\*\\*"role"\\*\\*" {
			# fields: 1=empty 2=role 3=model 4=effort 5=cost 6=use_when 7=trailing
			model=$3; effort=$4; desc=$6
			gsub(/^[ \t]+|[ \t]+$/, "", model)
			gsub(/^[ \t]+|[ \t]+$/, "", effort)
			gsub(/^[ \t]+|[ \t]+$/, "", desc)
			gsub(/\*\*/, "", model)
			print model "\t" effort "\t" desc
			exit
		}
	' "$DOCS_AGENTS"
}

# JSON-escape a string for embedding inside double quotes.
json_escape() {
	# Escape backslash, double-quote, and control chars; collapse newlines to spaces.
	python3 -c 'import json,sys; sys.stdout.write(json.dumps(sys.stdin.read())[1:-1])' 2>/dev/null \
		|| sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e ':a;N;$!ba;s/\n/ /g'
}

# YAML-escape: produce a safe single-line value. Strategy: replace double-quotes with
# single-quotes and strip newlines so the value is safe inside double-quoted YAML.
yaml_escape_inline() {
	tr '\n' ' ' | sed -e 's/"/'\''/g' -e 's/[[:space:]]\+/ /g' -e 's/^ //' -e 's/ $//'
}

# Derive a docs URL from the repo's git remote (best-effort).
derive_docs_url() {
	local url
	url=$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || true)
	if [ -z "$url" ]; then
		echo "$REPO_ROOT/docs/"
		return
	fi
	# Convert SSH form (git@github.com:org/repo.git) → https URL.
	url="${url%.git}"
	if [[ "$url" =~ ^git@([^:]+):(.+)$ ]]; then
		url="https://${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
	fi
	echo "$url"
}

# Write opencode.jsonc (lockdown config).
#
# Notes on compaction (verified against upstream packages/opencode/src/session/overflow.ts):
#   - Default `compaction.reserved` is 20000. We bump to 30000 to leave more headroom
#     for tool outputs. Skill outputs are PRUNE_PROTECTED but normal tool output is not,
#     so a larger reserve reduces mid-task compaction surprises.
#   - `compaction.auto: true` keeps automatic pruning enabled. The TUI signals when
#     compaction occurs, so user retains visibility.
write_config() {
	if [ -f "$DST_CONFIG" ] && ! grep -q "$CONFIG_SENTINEL" "$DST_CONFIG"; then
		echo "  ⚠️  skipping opencode.jsonc — foreign at $DST_CONFIG"
		return
	fi
	cat > "$DST_CONFIG" <<'EOF'
// _managed_by: agentic-engineers renderer/scripts/render-opencode.sh — do not edit; will be overwritten on re-install
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["AGENTS.md"],
  "compaction": {
    "auto": true,
    "reserved": 30000
  },
  "permission": {
    "read": "allow",
    "edit": "allow",
    "bash": "allow",
    "task": "allow",
    "glob": "allow",
    "grep": "allow",
    "webfetch": "allow"
  }
}
EOF
}

# Write AGENTS.md (global rules). Concise (<3KB target). User-authored overrides
# should live in AGENTS.md.local (NOT created by this renderer; survives re-render).
write_rules() {
	if [ -f "$DST_RULES" ] && ! head -n1 "$DST_RULES" | grep -q "$RULES_SENTINEL"; then
		echo "  ⚠️  skipping AGENTS.md — foreign at $DST_RULES"
		return
	fi
	local docs_url
	docs_url=$(derive_docs_url)
	cat > "$DST_RULES" <<EOF
<!-- managed by agentic-engineers render-opencode.sh; user edits to AGENTS.md.local will be loaded after this file -->
# agentic-engineers — Global Rules

This OpenCode install is managed by the [agentic-engineers framework]($docs_url).
Eight specialised subagents (in \`agents/\`) collaborate via a structured
DELEGATE/HANDBACK protocol on a queue-based work pipeline.

## Mandatory Constraints

### Queue-based routing
- ALL work flows through \`artifacts/queue/incoming/ → processing/ → done/\`.
- The Orchestrator polls the queue and routes per the decision tree in
  \`docs/AGENTS.md\`. No direct delegation from external sources.
- DELEGATEs live in \`artifacts/delegates/YYYY-MM-DD/\`; HANDBACKs in
  \`artifacts/queue/processing/\` until the Quality Engineer reviews them.

### Orchestrator constraints
- The Orchestrator MUST NOT perform work — it only routes, coordinates, and
  applies Model Engineer recommendations.
- It runs in-harness via a polling loop (no external cron / outbound tools).
- ALL execution work is delegated to a specialist via DELEGATE/HANDBACK.

### Role-specific rules
- **Security Engineer** is invoked ONLY for security-scoped tasks.
- **Engineer** MUST NOT receive a task without a pre-written \`plan\` in the
  DELEGATE (except trivial fixes); blocked tasks escalate to Senior Engineer.
- **Quality Engineer** provides \`model_assessment\` feedback in every HANDBACK
  (consumed by the Model Engineer feedback loop).
- **Lead/Senior Engineer** unblock or redirect Engineer when blocked.
- Each role has specialised skills under \`skills/\` (see \`docs/SKILLS.md\`).

## Layout in this install
- \`agents/\` — 8 subagents; invoke via \`@<agent-name>\` or the task tool
  (e.g. \`@orchestrator\`, \`@engineer\`, \`@security-engineer\`).
- \`skills/\` — workflow modules loaded on demand via the skill tool.
- \`opencode.jsonc\` — managed config (compaction, permissions); do not edit.
- \`AGENTS.md.local\` — *optional, user-authored*; if present, OpenCode loads
  it after this file. Use it for personal overrides that survive re-render.

## OpenCode-specific quirks
- **Compaction** is automatic with \`reserved: 30000\` tokens of headroom (vs
  upstream default 20000). The TUI signals when compaction triggers.
- **Skill tool outputs are PRUNE_PROTECTED** — invoke skills aggressively;
  their output survives compaction. Other tool output may be pruned.
- 8 subagents are installed. Mention them with \`@\` or invoke programmatically
  via the task tool.

## Full specification
See [\`docs/AGENTS.md\`]($docs_url), [\`docs/HANDOFF.md\`]($docs_url),
[\`docs/QUEUE-PROTOCOL.md\`]($docs_url), and [\`docs/SKILLS.md\`]($docs_url)
in the source repository for the authoritative protocol.
EOF
}

case "$MODE" in
	--uninstall)
		echo "🧹 Removing managed files from $OPENCODE/..."
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
		# opencode.jsonc (only if ours)
		removed_cfg=0
		if [ -f "$DST_CONFIG" ] && grep -q "$CONFIG_SENTINEL" "$DST_CONFIG"; then
			rm -f "$DST_CONFIG"; removed_cfg=1
		fi
		# AGENTS.md (only if ours)
		removed_rules=0
		if [ -f "$DST_RULES" ] && head -n1 "$DST_RULES" | grep -q "$RULES_SENTINEL"; then
			rm -f "$DST_RULES"; removed_rules=1
		fi
		echo "✅ Removed $count_s skill(s), $count_a agent(s), config:$removed_cfg, rules:$removed_rules"
		;;

	--status)
		# opencode.jsonc
		if [ ! -f "$DST_CONFIG" ]; then echo "  ❌ opencode.jsonc (not installed)"
		elif grep -q "$CONFIG_SENTINEL" "$DST_CONFIG"; then echo "  ✅ opencode.jsonc"
		else echo "  ⚠️  opencode.jsonc (foreign)"; fi
		# AGENTS.md
		if [ ! -f "$DST_RULES" ]; then echo "  ❌ AGENTS.md (not installed)"
		elif head -n1 "$DST_RULES" | grep -q "$RULES_SENTINEL"; then echo "  ✅ AGENTS.md"
		else echo "  ⚠️  AGENTS.md (foreign)"; fi
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
		mkdir -p "$OPENCODE" "$DST_SKILLS" "$DST_AGENTS"

		# 0. Top-level managed files
		echo "📦 Writing managed config & rules → $OPENCODE/..."
		write_config
		write_rules

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

		# 2. Agents: hybrid frontmatter merge (docs/AGENTS.md + src frontmatter), write .md
		echo "📦 Rendering agents → $DST_AGENTS/..."
		: > "$AGENT_MANIFEST.tmp"
		count_a=0
		for name in $(list_source_agents); do
			src_file="$SRC_AGENTS/$name-agent.md"
			dst_file="$DST_AGENTS/$name.md"

			# Refuse to overwrite a foreign agent (same safety as render-claude.sh)
			if [ -f "$dst_file" ] && [ -f "$AGENT_MANIFEST" ] && ! grep -qx "$name" "$AGENT_MANIFEST"; then
				echo "  ⚠️  skipping agent $name — foreign at $dst_file"
				continue
			fi
			if [ -f "$dst_file" ] && [ ! -f "$AGENT_MANIFEST" ]; then
				echo "  ⚠️  skipping agent $name — pre-existing file (no manifest yet); move it aside and re-run"
				continue
			fi

			# Hybrid metadata: docs/AGENTS.md is authoritative for model+effort+description.
			# Source frontmatter is the fallback and may carry richer per-agent description.
			docs_row=$(docs_lookup_role "$name" || true)
			docs_model=""; docs_effort=""; docs_desc=""
			if [ -n "$docs_row" ]; then
				docs_model=$(printf '%s' "$docs_row" | awk -F'\t' '{print $1}')
				docs_effort=$(printf '%s' "$docs_row" | awk -F'\t' '{print $2}')
				docs_desc=$(printf '%s' "$docs_row" | awk -F'\t' '{print $3}')
			fi
			fm_desc=$(extract_fm "$src_file" "description" || true)
			fm_model=$(extract_fm "$src_file" "model" || true)
			body_model=$(extract_body_model "$src_file" || true)

			# Pick description: prefer docs (canonical "Use When"), fall back to src frontmatter,
			# then to first non-empty body line.
			desc="$docs_desc"
			[ -z "$desc" ] && desc="$fm_desc"
			if [ -z "$desc" ]; then
				desc=$(strip_fm "$src_file" | awk 'NF{print; exit}')
			fi
			desc=$(printf '%s' "$desc" | yaml_escape_inline)

			# Pick model: prefer docs (single source of truth), fall back to frontmatter then body.
			model_raw="${docs_model:-${fm_model:-$body_model}}"
			model_full=$(map_model_opencode "$model_raw")
			if [ -z "$model_full" ]; then
				if [ -z "$model_raw" ]; then
					echo "  ⚠️  skipping agent $name — no model in docs/AGENTS.md or source frontmatter (non-canonical role?)"
				else
					echo "  ⚠️  skipping agent $name — model '$model_raw' not in OpenCode registry (see map_model_opencode)"
				fi
				continue
			fi

			# Effort → temperature
			temp=$(effort_to_temperature "${docs_effort:-medium}")

			# Emit OpenCode subagent frontmatter + transformed body.
			{
				echo "---"
				printf 'description: "%s"\n' "$desc"
				echo "mode: subagent"
				echo "model: $model_full"
				echo "temperature: $temp"
				echo "permission:"
				echo "  read: allow"
				echo "  edit: allow"
				echo "  bash: allow"
				echo "  task: allow"
				echo "  glob: allow"
				echo "  grep: allow"
				echo "  webfetch: allow"
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
