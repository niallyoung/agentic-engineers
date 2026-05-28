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
#   3. Model IDs are fully-qualified provider/model strings (github-copilot/claude-opus-4.7 format).
#   4. Accepts both hyphen and dot formats on input, normalizes to hyphen format per Anthropic API.

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

# Source shared functions (list_source_skills, list_source_agents, extract_fm, strip_fm, extract_body_model)
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

# Map agentic-engineers canonical model id → OpenCode provider/model id.
#
# IMPORTANT: OpenCode uses Anthropic's official model IDs (hyphens, not dots).
# This mapping accepts both hyphen and dot formats for compatibility.
# Output is always hyphen-format per Anthropic API specification:
# https://docs.anthropic.com/claude/docs/models-overview
#
# Provider is hardcoded to github-copilot (the standard Copilot provider for
# Claude models in OpenCode). For users with anthropic/ provider, the mapping
# would be different (e.g., anthropic/claude-haiku-4.5).
#
# Note: claude-opus-4-6 is now declared in the custom provider config (see write_config)
# so it maps directly instead of falling back to 4.7.
map_model_opencode() {
	case "$1" in
		claude-haiku-4.5|claude-haiku-4-5)   echo "github-copilot/claude-haiku-4-5" ;;
		claude-sonnet-4.6|claude-sonnet-4-6) echo "github-copilot/claude-sonnet-4-6" ;;
		claude-sonnet-4.5|claude-sonnet-4-5) echo "github-copilot/claude-sonnet-4-5" ;;
		claude-opus-4.7|claude-opus-4-7)     echo "github-copilot/claude-opus-4-7" ;;
		claude-opus-4.6|claude-opus-4-6)     echo "github-copilot/claude-opus-4-6" ;;
		claude-opus-4.5|claude-opus-4-5)     echo "github-copilot/claude-opus-4-5" ;;
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

# yaml_escape_inline() is defined in lib.sh (sourced above)

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
# Generate per-agent permission blocks for OpenCode security enforcement
# Based on agent role and responsibility level
get_agent_permissions() {
	local agent_name="$1"
	
	# Define permission rules per agent role
	# Each role has bash and edit deny lists
	case "$agent_name" in
		orchestrator)
			# Orchestrator has NO direct execution — routing only
			cat <<'PERMS'
,
        "permission": {
          "bash": {
            "deny": ["*"]
          },
          "edit": {
            "deny": ["*"]
          }
        }
PERMS
			;;
		engineer)
			# Engineer — standard developer with protections against force-push and destructive ops
			cat <<'PERMS'
,
        "permission": {
          "bash": {
            "deny": ["git push *", "git force-push", "git push --force", "git push -f", "rm -rf *", "rm -rf /", "rm -rf ~", "sudo rm", "rm -rf .git"]
          },
          "edit": {
            "deny": ["SPEC.md", ".githooks/**", "docs/SPEC.md", "SPEC-*.md", "opencode.jsonc"]
          }
        }
PERMS
			;;
		quality-engineer)
			# Quality Engineer — QA role with protection against destructive ops
			cat <<'PERMS'
,
        "permission": {
          "bash": {
            "deny": ["rm -rf *", "rm -rf /", "rm -rf ~", "git force-push", "git push --force", "git push -f", "git reset --hard HEAD~", "sudo rm", "rm -rf .git"]
          },
          "edit": {
            "deny": ["SPEC.md", ".githooks/**", "docs/SPEC.md", "SPEC-*.md", "opencode.jsonc"]
          }
        }
PERMS
			;;
		senior-engineer)
			# Senior Engineer — architecture role; force-push requires Lead review
			cat <<'PERMS'
,
        "permission": {
          "bash": {
            "deny": ["git force-push", "git push --force", "git push -f"]
          },
          "edit": {
            "deny": ["SPEC.md", ".githooks/**", "docs/SPEC.md", "SPEC-*.md"]
          }
        }
PERMS
			;;
		lead-engineer)
			# Lead Engineer — trusted role, full access (implicit)
			echo ""
			;;
		principal-engineer)
			# Principal Engineer — ultimate authority, full access (implicit)
			echo ""
			;;
		security-engineer)
			# Security Engineer — trusted security role, full access (implicit)
			echo ""
			;;
		model-engineer)
			# Model Engineer — optimization role with protection against destructive ops
			cat <<'PERMS'
,
        "permission": {
          "bash": {
            "deny": ["rm -rf *", "rm -rf /", "rm -rf ~", "git force-push", "git push --force", "sudo rm", "rm -rf .git"]
          },
          "edit": {
            "deny": ["SPEC.md", ".githooks/**", "opencode.jsonc", "docs/SPEC.md", "SPEC-*.md"]
          }
        }
PERMS
			;;
		*)
			echo ""
			;;
	esac
}

write_config() {
	if [ -f "$DST_CONFIG" ] && ! grep -q "$CONFIG_SENTINEL" "$DST_CONFIG"; then
		echo "  ⚠️  skipping opencode.jsonc — foreign at $DST_CONFIG"
		return
	fi
	
	# Generate agent config from AGENTS.md Primary Assignments table
	# Format: | Role | Model | Effort | Use When |
	local agent_config=""
	local model_config=""
	local models_seen=""
	
	# Extract table rows (skip header and separator)
	local table_lines=$(sed -n '/^## Primary Assignments/,/^##/p' "$DOCS_AGENTS" | grep '^|' | tail -n +3)
	
	while IFS='|' read -r empty role model effort use_when; do
		role=$(echo "$role" | xargs)  # trim whitespace
		model=$(echo "$model" | xargs)
		
		# Skip empty lines
		[ -z "$role" ] && continue
		
		# Convert role to agent name (remove ** markers, lowercase, replace spaces with hyphens)
		local agent_name=$(echo "$role" | sed 's/\*\*//g' | tr '[:upper:]' '[:lower:]' | sed 's/ /-/g')
		
		# Convert model format: claude-haiku-4.5 → github-copilot/claude-haiku-4-5 (dots→hyphens)
		local model_normalized=$(echo "$model" | sed 's/\./-/g')  # claude-haiku-4.5 → claude-haiku-4-5
		local full_model="github-copilot/$model_normalized"
		
		# Generate per-agent permissions (empty string if no restrictions)
		local permissions=$(get_agent_permissions "$agent_name")
		
		# Add to agent config (NO trailing comma - we'll add it between entries)
		if [ -n "$agent_config" ]; then
			agent_config="${agent_config},"
		fi
		agent_config="${agent_config}
    \"$agent_name\": {
      \"model\": \"$full_model\"$permissions
    }"
		
		# Track unique models
		if ! echo "$models_seen" | grep -q "$model"; then
			models_seen="$models_seen $model"
			
			# Generate model config entry (NO trailing comma - we'll add it between entries)
			local model_name=$(echo "$model" | sed 's/claude-/Claude /' | sed 's/-/ /g' | sed 's/\([0-9]\)\.\([0-9]\)/\1.\2/')
			local model_id=$(echo "$model" | sed 's/\./-/g')  # claude-haiku-4.5 → claude-haiku-4-5
			
			if [ -n "$model_config" ]; then
				model_config="${model_config},"
			fi
			model_config="${model_config}
        \"$model_id\": {
          \"id\": \"$model_id\",
          \"name\": \"$model_name\",
          \"family\": \"claude\",
          \"release_date\": \"2025-05-01\",
          \"attachment\": true,
          \"reasoning\": true,
          \"temperature\": true,
          \"tool_call\": true,
          \"cost\": {
            \"input\": 0.000005,
            \"output\": 0.000025,
            \"cache_read\": 0.0000005,
            \"cache_write\": 0.00000625
          },
          \"limit\": {
            \"context\": 1000000,
            \"output\": 128000
          },
          \"modalities\": {
            \"input\": [\"text\", \"image\"],
            \"output\": [\"text\"]
          },
          \"status\": \"active\"
        }"
		fi
	done <<< "$table_lines"
	
	cat > "$DST_CONFIG" <<EOF
// _managed_by: agentic-engineers renderer/scripts/render-opencode.sh — do not edit; will be overwritten on re-install
{
  "\$schema": "https://opencode.ai/config.json",
  "instructions": ["AGENTS.md"],
  "default_agent": "orchestrator",
  "model": "github-copilot/claude-haiku-4-5",
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
  },
  "agent": {$agent_config
  },
  "provider": {
    "github-copilot": {
      "models": {$model_config
      }
    }
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
- ALL work flows through \`~/.agentic-engineers/{session-id}/opencode/queue/incoming/ → processing/ → done/\`.
- The Orchestrator polls the queue and routes per the decision tree in
  \`docs/AGENTS.md\`. No direct delegation from external sources.
- DELEGATEs are written to the queue's \`incoming/\` directory; HANDBACKs are written to
  \`processing/\` and moved to \`done/\` after Quality Engineer review.

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

## Protocol Protection (Critical)

### SPEC.md — Immutable Protocol Document

The SPEC.md file defines the agentic-engineers protocol and is protected from direct modification.

**Why**: SPEC.md is the source of truth for our multi-agent coordination protocol. Unauthorized changes could break protocol compliance.

**Who Can Modify?**
- **Principal Engineer**: Full access via \`spec-management\` skill
- **All other agents**: Denied (OpenCode will block direct edits)

**How to Modify SPEC.md?**
1. Use the \`spec-management\` skill (loads structured proposal interface)
2. Propose changes via SPEC_CHANGE_PROPOSAL.md
3. Principal Engineer reviews and approves
4. Changes applied with audit trail maintained automatically
5. All modifications tracked in SPEC_CHANGELOG.md

### Protected Files

The following files are protected from unintended modifications:
- \`SPEC.md\` — Core protocol definition (Principal Engineer only)
- \`docs/SPEC.md\` — Protocol documentation (Principal Engineer only)
- \`.githooks/**\` — Git hooks infrastructure (Security Engineer only)
- \`opencode.jsonc\` — OpenCode configuration (Principal Engineer / Security Engineer only)
- \`SPEC-*.md\` — Protocol extensions (Principal Engineer only)

### Per-Agent Permission Boundaries

Each agent has granular permissions enforced by OpenCode at runtime:

| Agent | Bash Restrictions | Edit Restrictions | Access Level |
|-------|------------------|-------------------|--------------|
| **Engineer** | Blocks: \`git push\`, \`git force-push\`, \`rm -rf *\`, \`sudo rm\` | Blocks: SPEC.md, .githooks, config files | Standard developer |
| **Orchestrator** | Blocks: ALL bash execution | Blocks: ALL file edits | Router only (no direct execution) |
| **Quality Engineer** | Blocks: Destructive ops, \`rm -rf\`, \`git force-push\` | Blocks: SPEC.md, config files | QA assurance |
| **Senior Engineer** | Blocks: \`git force-push\` (hotfix exception via Lead) | Blocks: SPEC.md, .githooks | Architecture guidance |
| **Lead Engineer** | No restrictions (logs all actions) | No restrictions (logs all actions) | Team leadership |
| **Security Engineer** | No restrictions (trusted security role) | No restrictions (trusted security role) | Security authority |
| **Model Engineer** | Blocks: Destructive ops, dangerous commands | Blocks: SPEC.md, config files | Model optimization |
| **Principal Engineer** | No restrictions (ultimate authority) | No restrictions (ultimate authority) | Org authority |

### Critical Dangerous Commands (All Agents)

The following patterns are blocked at the agent level to prevent accidental destruction:
- \`rm -rf /\` — System destruction
- \`rm -rf ~\` — Home directory destruction
- \`rm -rf .git\` — Repository destruction
- \`git push --force\` or \`git push -f\` — Force pushes (breaks history)
- \`git reset --hard HEAD~\` — Destructive resets
- \`sudo rm\` — Privileged destruction

## Layout in this install
- \`agents/\` — 8 subagents; invoke via \`opencode --agent <agent-name>\` or the task tool
  (e.g. \`opencode --agent orchestrator\`, \`opencode --agent engineer\`).
- \`skills/\` — workflow modules loaded on demand via the skill tool.
- \`opencode.jsonc\` — managed config (compaction, permissions); do not edit directly—use Principal access.
- \`AGENTS.md.local\` — *optional, user-authored*; if present, OpenCode loads
  it after this file. Use it for personal overrides that survive re-render.

## OpenCode-specific quirks
- **Compaction** is automatic with \`reserved: 30000\` tokens of headroom (vs
  upstream default 20000). The TUI signals when compaction triggers.
- **Skill tool outputs are PRUNE_PROTECTED** — invoke skills aggressively;
  their output survives compaction. Other tool output may be pruned.
- 8 subagents are installed. Mention them with \`@\` or invoke programmatically
  via the task tool.
- **Permission enforcement** is runtime-based; violations are logged and blocked at execution time.

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
		# Git hooks
		hooks_path=$(git -C "$REPO_ROOT" config core.hooksPath 2>/dev/null || true)
		if [ "$hooks_path" = ".githooks" ]; then echo "  ✅ git hooks (core.hooksPath = .githooks)"
		elif [ -n "$hooks_path" ]; then echo "  ⚠️  git hooks (core.hooksPath = $hooks_path, expected .githooks)"
		else echo "  ❌ git hooks (core.hooksPath not set — run render-opencode.sh or /hooks-install)"; fi
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

			# Mode: orchestrator is the framework's entry point, so it must be
			# selectable as a primary agent (--agent orchestrator, default_agent).
			# Use mode: all so it can also be invoked as primary agent from inside
			# any session. All other roles stay as subagents (invoked via --agent
			# or task tool only).
			if [ "$name" = "orchestrator" ]; then
				agent_mode="all"
			else
				agent_mode="subagent"
			fi

			# Emit OpenCode subagent frontmatter + transformed body.
			{
				echo "---"
				printf 'description: "%s"\n' "$desc"
				echo "mode: $agent_mode"
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

		# 3. Git hooks: configure core.hooksPath and ensure hooks are executable
		# This enforces SDLC compliance at commit/push time for the repo itself.
		# Hooks are installed from REPO_ROOT/.githooks to enforce consistency across all harnesses.
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
