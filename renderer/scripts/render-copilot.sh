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
# shellcheck source=../lib/render-lib.sh
source "$(dirname "$0")/../lib/render-lib.sh"

# --- settings.json ownership helpers (mirror render-claude.sh) ----------------
# Records the settings.json "model" value THIS installer last wrote. Presence
# plus content is the ONLY safe signal that the framework owns that key.
MODEL_MARKER="$COPILOT/.agentic-engine-copilot-model"

# _settings_edit SETTINGS_FILE OPERATION [ARGS...]   (set_model | remove_model)
# Merge-edit one key. Exit 3 (file untouched, warning on stderr) when the file
# is non-empty and not a strict-JSON object.
_settings_edit() {
	local settings="$1" operation="$2"; shift 2
	python3 - "$settings" "$operation" "$@" <<'PY'
import json, os, sys

settings_file, operation, args = sys.argv[1], sys.argv[2], sys.argv[3:]
try:
	with open(settings_file) as f:
		raw = f.read()
except FileNotFoundError:
	raw = ""
if raw.strip() == "":
	data = {}
else:
	try:
		data = json.loads(raw)
		if not isinstance(data, dict):
			raise ValueError("top-level value is not a JSON object")
	except ValueError as exc:
		sys.stderr.write(
			"  WARNING: %s is not valid JSON (%s) -- left untouched; "
			"skipped '%s'. Fix the file (strict JSON: no comments or trailing "
			"commas) and re-run.\n" % (settings_file, exc, operation)
		)
		sys.exit(3)

if operation == "check":
	sys.exit(0)  # validity probe only: never writes
if operation == "set_model":
	data["model"] = args[0]
elif operation == "remove_model":
	data.pop("model", None)

tmp = settings_file + ".tmp"
with open(tmp, "w") as f:
	json.dump(data, f, indent=2)
	f.write("\n")
os.replace(tmp, settings_file)
PY
}

# _settings_get_model FILE -> current "model" string, or empty
_settings_get_model() {
	[ -f "$1" ] || return 0
	python3 - "$1" <<'PY'
import json, sys
try:
	with open(sys.argv[1]) as f:
		data = json.load(f)
except (OSError, ValueError):
	data = {}
value = data.get("model") if isinstance(data, dict) else None
print(value if isinstance(value, str) else "")
PY
}

_model_marker_value() {
	[ -f "$MODEL_MARKER" ] || return 0
	head -n1 "$MODEL_MARKER" | tr -d '[:space:]'
}

inject_settings_model() { _settings_edit "$1" set_model "$2"; }
remove_settings_model() { [ -f "$1" ] || return 0; _settings_edit "$1" remove_model; }

# remove_settings_if_empty FILE: after uninstall, a settings.json that is
# exactly {} is litter we created; remove it. Anything else is never touched.
remove_settings_if_empty() {
	[ -f "$1" ] || return 0
	python3 - "$1" <<'PY'
import json, os, sys
try:
	with open(sys.argv[1]) as fh:
		data = json.load(fh)
except (OSError, ValueError):
	sys.exit(0)
if data == {}:
	os.remove(sys.argv[1])
PY
}

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
		# settings.json model: remove it (and the ownership marker) ONLY if the
		# value on disk is still the one we wrote. A user-chosen value is never
		# removed. AGENTIC_KEEP_MODEL=1 (as for `make fresh-install-claude`)
		# leaves model + marker for an immediately following install.
		if [ "${AGENTIC_KEEP_MODEL:-}" = "1" ]; then
			echo "  keeping session model and ownership marker for the reinstall"
		else
			uninstall_model=$(_settings_get_model "$COPILOT/settings.json")
			uninstall_marker=$(_model_marker_value)
			if [ -n "$uninstall_model" ] && [ "$uninstall_model" = "$uninstall_marker" ]; then
				if remove_settings_model "$COPILOT/settings.json"; then
					echo "  removed model from settings.json"
				fi
			elif [ -n "$uninstall_model" ]; then
				echo "  ℹ️  keeping session model ($uninstall_model) — set by you, not by the framework"
			fi
			rm -f "$MODEL_MARKER"
			remove_settings_if_empty "$COPILOT/settings.json"
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

			# Remove any tests/__pycache__/.pytest_cache/*.pyc cruft an older
			# renderer version shipped into this managed skill dir before the
			# excludes above existed — see prune_excluded_cruft() in
			# renderer/lib/render-lib.sh for why this is a separate find-based
			# pass rather than rsync --delete-excluded.
			prune_excluded_cruft "$dst"

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

		# 1.5 Prune orphaned managed skills: dirs we installed on a prior render
		# whose source skill was since deleted from src/skills/ (a slimdown
		# round). See prune_orphaned_skills() in renderer/lib/render-lib.sh —
		# reuses the same marker-based foreign-detection as the loop above.
		prune_orphaned_skills "$DST_SKILLS" "$SRC_SKILLS" "$MARKER"

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

		# 2b. settings.json — harness session model configuration (invariant I4:
		# the installer never overwrites a model the user chose). Same ownership
		# semantics as render-claude.sh; MODEL_MARKER records the value WE last
		# wrote and is the only signal that the framework owns the key:
		#
		#   file absent                    -> fresh install, the file is ours -> SET
		#   file exists + value==marker    -> still exactly what we wrote     -> UPDATE
		#   file exists + no "model" key   -> theirs (never had one / cleared) -> SKIP
		#   file exists + value!=marker    -> user-chosen or hand-edited      -> SKIP
		#   file not strict JSON           -> left byte-for-byte untouched, warned
		#
		# Other keys are always preserved (merge, never overwrite the file).
		# Session model = the registry's pinned Copilot ID for the orchestrator
		# (scripts/models.py via map_model). Never a floating alias.
		echo "⚙️  Checking settings.json → $COPILOT/settings.json ..."
		orchestrator_model=$(map_model "orchestrator" copilot || true)
		if [ -z "$orchestrator_model" ]; then
			echo "  ⚠️  no copilot ID for orchestrator in config/models.yaml — leaving settings.json model alone" >&2
		else
			settings_existed=0
			[ -f "$COPILOT/settings.json" ] && settings_existed=1
			current_model=$(_settings_get_model "$COPILOT/settings.json")
			marker_model=$(_model_marker_value)
			if [ "$settings_existed" -eq 0 ]; then
				if inject_settings_model "$COPILOT/settings.json" "$orchestrator_model"; then
					printf '%s\n' "$orchestrator_model" > "$MODEL_MARKER"
					echo "  ✅ Set session model → $orchestrator_model (orchestrator default, from registry)"
				fi
			elif [ -n "$current_model" ] && [ "$current_model" = "$marker_model" ]; then
				if inject_settings_model "$COPILOT/settings.json" "$orchestrator_model"; then
					printf '%s\n' "$orchestrator_model" > "$MODEL_MARKER"
					echo "  ✅ Session model → $orchestrator_model (orchestrator default, from registry)"
				fi
			elif [ -z "$current_model" ]; then
				# Unparseable files also read as "no model": probe so the user is
				# told (warning on stderr, rc 3) rather than silently skipped.
				if _settings_edit "$COPILOT/settings.json" check; then
					echo "  ℹ️  Leaving your session model unset (the framework will not add one to your settings.json)"
				fi
			else
				echo "  ℹ️  Keeping your existing session model ($current_model) — set by you, not by the framework"
			fi
		fi

		# 3. Git hooks: configure core.hooksPath and ensure hooks are executable
		# GitHub Copilot harness: hooks are installed from REPO_ROOT/.githooks to enforce consistency.
		# Note: Copilot uses the same git repo as OpenCode/Claude, so hooks are shared.
		# LOW6 note: MODE has no separate "render-only" branch (see the `case
		# "$MODE" in` above — --uninstall and --status are the only
		# alternatives to this default branch), so this same code path also
		# runs for `make render-copilot`, which mutates REPO_ROOT's own
		# .git/config (core.hooksPath) as a side effect of a target presented
		# as build-only (dist/copilot/ generation). Intentional/relied-upon —
		# not changing it here, just flagging it so a future reader isn't
		# surprised that a "render" target touches the developer's git config.
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
