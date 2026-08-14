#!/usr/bin/env bash
# render-copilot.sh — render agentic-engineers' canonical skills into ~/.copilot/skills/
#
# Inputs:  $1 = REPO_ROOT (agentic-engineers repo root)
#          $2 = COPILOT root (e.g., $HOME/.copilot)
#          $3 = optional: --uninstall | --status
#
# Behavior: copies any directory under $REPO_ROOT/skills/ that contains a SKILL.md
# into $COPILOT/skills/<name>/. Top-level loose .md files in skills/ are skipped
# (those are docs, not skills). Existing user-owned skills (no source counterpart)
# are never touched.
#
# A marker file (.agentic-engine-copilot) is written to each managed skill so
# uninstall can identify what to remove.

set -euo pipefail

REPO_ROOT="${1:?usage: render-copilot.sh REPO_ROOT COPILOT_DIR [--uninstall|--status]}"
COPILOT="${2:?usage: render-copilot.sh REPO_ROOT COPILOT_DIR [--uninstall|--status]}"
MODE="${3:-install}"

SRC_SKILLS="$REPO_ROOT/src/skills"
DST_SKILLS="$COPILOT/skills"
DST_RULES="$COPILOT/AGENTS.md"
SRC_AGENTS_MD="$REPO_ROOT/src/AGENTS.md"
MARKER=".agentic-engine-copilot"
# Sentinel on line 1 of AGENTS.md so we can tell ours apart from a user's file.
# User overrides should live in AGENTS.md.local (never written/removed by us).
RULES_SENTINEL='<!-- managed by agentic-engineers render-copilot.sh'

[ -d "$SRC_SKILLS" ] || { echo "❌ no source: $SRC_SKILLS" >&2; exit 1; }

# Generate the Copilot framework routing guide (AGENTS.md) from the canonical
# src/AGENTS.md. Marker-aware: refuses to overwrite a foreign AGENTS.md (one
# that does not carry our sentinel), preventing data loss of a user's own file.
# Works for both dist rendering and home install (DST_RULES is derived from
# $COPILOT, which is either the repo's dist/copilot dir or ~/.copilot).
write_agents_md() {
	if [ ! -f "$SRC_AGENTS_MD" ]; then
		echo "  ⚠️  skipping AGENTS.md — canonical source not found at $SRC_AGENTS_MD" >&2
		return 0
	fi
	if [ -f "$DST_RULES" ] && ! head -n1 "$DST_RULES" | grep -q "$RULES_SENTINEL"; then
		echo "  ⚠️  skipping AGENTS.md — foreign file at $DST_RULES (move it aside to let the framework manage it)"
		return 0
	fi
	{
		echo "$RULES_SENTINEL; user edits to AGENTS.md.local are loaded after this file. Do not edit directly — re-render overwrites it. -->"
		cat "$SRC_AGENTS_MD"
	} > "$DST_RULES"
	echo "  ✅ AGENTS.md (routing guide + framework rules)"
}

# Source shared functions (list_source_skills, list_source_agents, extract_fm, strip_fm, extract_body_model)
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"


case "$MODE" in
	--uninstall)
		echo "🧹 Removing managed agents and skills from $COPILOT/..."
		# Remove agents via Python renderer (replaces deleted render-copilot-agents.sh wrapper)
		python3 "$REPO_ROOT/renderer/scripts/render-copilot-agents.py" "$REPO_ROOT/src/agents" "$COPILOT/agents" --uninstall

		# Remove skills
		count=0
		for name in $(list_source_skills); do
			target="$DST_SKILLS/$name"
			if [ -f "$target/$MARKER" ]; then
				rm -rf "$target"
				echo "  removed skill: $name"
				count=$((count + 1))
			fi
		done
		# Remove AGENTS.md only if it carries our sentinel (never a user's file)
		if [ -f "$DST_RULES" ] && head -n1 "$DST_RULES" | grep -q "$RULES_SENTINEL"; then
			rm -f "$DST_RULES"
			echo "  removed AGENTS.md"
		elif [ -f "$DST_RULES" ]; then
			echo "  ⚠️  keeping AGENTS.md — foreign (not managed by us)"
		fi
		echo "✅ Removed agents + $count managed skill(s) + docs"
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
			elif diff -rq "$src" "$dst" --exclude="$MARKER" --exclude=".DS_Store" --exclude=".git" --exclude='tests' --exclude='__pycache__' --exclude='.pytest_cache' --exclude='*.pyc' >/dev/null 2>&1; then
				echo "  ✅ $name"
				ok=$((ok + 1))
			else
				echo "  🔄 $name (drift)"
				drift=$((drift + 1))
			fi
		done
		echo "  skills: $ok ok / $drift drift / $missing missing / $foreign foreign"
		# Documentation
		if [ ! -f "$DST_RULES" ]; then echo "  ❌ AGENTS.md (not installed)"
		elif head -n1 "$DST_RULES" | grep -q "$RULES_SENTINEL"; then echo "  ✅ AGENTS.md (routing guide)"
		else echo "  ⚠️  AGENTS.md (foreign — not managed by us)"; fi
		;;

	install|"")
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
				echo "  ⚠️  skipping $name — exists at $dst and is not managed by us"
				continue
			fi

			# Render skill via rsync
			skill_start=$(date +%s)
			rsync -a --delete --exclude='.DS_Store' --exclude='.git' --exclude='tests/' --exclude='__pycache__' --exclude='.pytest_cache' --exclude='*.pyc' --exclude='AGENTS.md' \
				"$src/" "$dst/" || {
				echo "  ❌ $name — rsync failed" >&2
				continue
			}

			# Write marker only after successful rsync
			date -u +"%Y-%m-%dT%H:%M:%SZ" > "$dst/$MARKER"

			# Collect stats
			skill_end=$(date +%s)
			skill_duration=$(( skill_end - skill_start ))
			skill_bytes=$(du -sk "$dst" 2>/dev/null | cut -f1 || echo 0)
			total_bytes=$(( total_bytes + skill_bytes ))

			echo "  rendered $name (${skill_duration}s)"
			count=$((count + 1))
		done

		install_end=$(date +%s)
		install_duration=$(( install_end - install_start ))
		echo "✅ Rendered $count skill(s) to $DST_SKILLS/ (${install_duration}s, ${total_bytes}KB)"

		# 2. Copilot agents: render agents from src/agents/ via Python renderer
		# (replaces deleted render-copilot-agents.sh wrapper)
		SRC_AGENTS="$REPO_ROOT/src/agents"
		if [ -d "$SRC_AGENTS" ]; then
			echo "🎨 Rendering Copilot CLI Agents..."
			mkdir -p "$COPILOT/agents"
			python3 "$REPO_ROOT/renderer/scripts/render-copilot-agents.py" "$SRC_AGENTS" "$COPILOT/agents"
		else
			echo "⚠️  skipping agents — source directory not found at $SRC_AGENTS" >&2
		fi

		# 3. Framework documentation: generate AGENTS.md (routing guide) from the
		# canonical src/AGENTS.md. Runs for both dist rendering and home install
		# so the file always exists where downstream steps expect it, and is
		# marker-protected so a user's own AGENTS.md is never clobbered.
		echo "📖 Writing AGENTS.md → $DST_RULES ..."
		write_agents_md

		# 2b. settings.json — harness session model configuration. Written for
		# both dist rendering and home install so the installed tree matches
		# dist exactly.
		echo "⚙️  Writing settings.json → $COPILOT/settings.json ..."

		# Derive model from orchestrator row in canonical AGENTS.md
		orchestrator_meta=$(lookup_agent_metadata "orchestrator" <(parse_agents_md "$SRC_AGENTS_MD") 2>/dev/null || true)
		if [ -n "$orchestrator_meta" ]; then
			orchestrator_model_raw=$(echo "$orchestrator_meta" | cut -d'|' -f1)
			orchestrator_model=$(map_model "$orchestrator_model_raw")
			if [ -n "$orchestrator_model" ]; then
				cat > "$COPILOT/settings.json" <<EOF
{
  "model": "$orchestrator_model",
  "harness": "copilot"
}
EOF
				echo "  ✅ settings.json (session model → $orchestrator_model from orchestrator)"
			else
				# Fallback if model mapping fails
				cat > "$COPILOT/settings.json" <<'EOF'
{
  "model": "sonnet",
  "harness": "copilot"
}
EOF
				echo "  ✅ settings.json (fallback: sonnet)"
			fi
		else
			# Fallback if lookup fails
			cat > "$COPILOT/settings.json" <<'EOF'
{
  "model": "sonnet",
  "harness": "copilot"
}
EOF
			echo "  ✅ settings.json (fallback: sonnet — orchestrator not found in roster)"
		fi

		# 3. Git hooks: configure core.hooksPath and ensure hooks are executable
		# GitHub Copilot harness: hooks are installed from REPO_ROOT/.githooks to enforce consistency.
		# Note: Copilot uses the same git repo as OpenCode/Claude, so hooks are shared.
		if [ -d "$REPO_ROOT/.githooks" ]; then
			echo "📦 Installing git hooks from $REPO_ROOT/.githooks/..."
			git -C "$REPO_ROOT" config core.hooksPath .githooks
			# chmod only the actual hook entry points — NOT .githooks/* wholesale,
			# which kept re-adding exec bits to the .md docs in that directory and
			# tripping pre-commit's own file-permissions check.
			for hook in pre-commit pre-push commit-msg post-merge; do
				[ -f "$REPO_ROOT/.githooks/$hook" ] && chmod +x "$REPO_ROOT/.githooks/$hook"
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
