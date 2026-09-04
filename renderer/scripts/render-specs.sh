#!/usr/bin/env bash
# render-specs.sh — render agentic-engineers orchestration specs into dist/specs/
#
# Deploys the authoritative framework specifications and orchestration configs
# to the dist/ layer so they are available for harness consumption and QA
# consistency checks.
#
# Inputs:  $1 = REPO_ROOT (agentic-engineers repo root)
#          $2 = DEST_ROOT  (destination root, defaults to $REPO_ROOT/dist)
#          $3 = optional: --status | --validate
#
# Outputs (written to $DEST_ROOT/specs/):
#   SPEC.md                   — master framework specification
#   FRAMEWORK-MANIFEST.yaml   — entity registry (agents/skills/hooks)
#   orchestration.yaml        — orchestrator runtime config (budgets, routing)
#
# A marker file (.agentic-engine-specs) is written to $DEST_ROOT/specs/ so
# install/uninstall can identify managed files vs user additions.
#
# Usage:
#   render-specs.sh REPO_ROOT                     # render to dist/specs/
#   render-specs.sh REPO_ROOT /custom/dest        # render to custom dest/specs/
#   render-specs.sh REPO_ROOT /custom/dest --status   # show status
#   render-specs.sh REPO_ROOT /custom/dest --validate # validate rendered output
#
# Integration: called from Makefile render-specs target; chained from render-all.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${1:?usage: render-specs.sh REPO_ROOT [DEST_ROOT] [--status|--validate]}"
DEST_ROOT="${2:-$REPO_ROOT/dist}"
MODE="${3:-install}"

SRC_DOCS="$REPO_ROOT/docs"
SRC_CONFIG="$REPO_ROOT/config"
DST_SPECS="$DEST_ROOT/specs"
MARKER=".agentic-engine-specs"

# ANSI color helpers (_use_color/_green/_yellow/_red/_dim) and the shared
# renderer functions come from the unified library.
# shellcheck source=../lib/render-lib.sh
source "$SCRIPT_DIR/../lib/render-lib.sh"

# Files to deploy: <src_path> <dest_name>
SPEC_FILES=(
    "$SRC_DOCS/SPEC.md:SPEC.md"
    "$SRC_CONFIG/FRAMEWORK-MANIFEST.yaml:FRAMEWORK-MANIFEST.yaml"
    "$SRC_CONFIG/orchestration.yaml:orchestration.yaml"
)

case "$MODE" in
    --validate)
        echo "🔍 Validating deployed specs at $DST_SPECS/..."
        errors=0

        # Check marker exists
        if [ ! -f "$DST_SPECS/$MARKER" ]; then
            echo "  ❌ Marker file missing: $DST_SPECS/$MARKER (run render-specs first)" >&2
            errors=$((errors + 1))
        fi

        # Check each expected file
        for entry in "${SPEC_FILES[@]}"; do
            dst_name="${entry##*:}"
            dst="$DST_SPECS/$dst_name"
            if [ ! -f "$dst" ]; then
                echo "  ❌ Missing: $dst_name" >&2
                errors=$((errors + 1))
            else
                # Validate YAML files parse cleanly
                case "$dst_name" in
                    *.yaml)
                        if command -v python3 >/dev/null 2>&1; then
                            python3 -c "import yaml, sys; yaml.safe_load(open('$dst'))" 2>/dev/null \
                                && printf "  %s %s\n" "$(_green "✅")" "$dst_name (valid YAML)" \
                                || { echo "  ❌ Invalid YAML: $dst_name" >&2; errors=$((errors + 1)); }
                        fi
                        ;;
                    SPEC.md)
                        # SPEC.md should have frontmatter and content
                        if ! head -1 "$dst" | grep -q "^---"; then
                            echo "  ⚠️  SPEC.md missing frontmatter" >&2
                        else
                            printf "  %s %s\n" "$(_green "✅")" "SPEC.md (valid)"
                        fi
                        ;;
                esac
            fi
        done

        if [ $errors -gt 0 ]; then
            echo "❌ Validation failed with $errors error(s)" >&2
            exit 1
        fi
        echo "✅ Spec validation passed"
        ;;

    install|"")
        echo ""
        echo "📐 Rendering Orchestration Specs"
        echo "================================="
        echo ""
        echo "📁 Source: $SRC_DOCS/, $SRC_CONFIG/"
        echo "📁 Dest:   $DST_SPECS/"
        echo ""

        mkdir -p "$DST_SPECS"
        count=0
        install_start=$(date +%s)

        for entry in "${SPEC_FILES[@]}"; do
            src="${entry%%:*}"
            dst_name="${entry##*:}"
            dst="$DST_SPECS/$dst_name"

            if [ ! -f "$src" ]; then
                printf "  %s %s\n" "$(_yellow "⚠️ ")" "skipping $dst_name — source not found: $src"
                continue
            fi

            _use_color && printf '\r  ⏳ %-40s' "$dst_name"

            cp "$src" "$dst"

            _use_color && printf '\r'
            printf "  %s %s\n" "$(_green "✅")" "$dst_name $(_dim "($(wc -l < "$dst") lines)")"
            count=$((count + 1))
        done

        # Write marker
        date -u +"%Y-%m-%dT%H:%M:%SZ" > "$DST_SPECS/$MARKER"

        install_end=$(date +%s)
        install_duration=$(( install_end - install_start ))
        echo ""
        echo "✅ Deployed $count spec file(s) to $DST_SPECS/ $(_dim "(${install_duration}s)")"
        ;;

    *)
        echo "unknown mode: $MODE" >&2
        echo "usage: render-specs.sh REPO_ROOT [DEST_ROOT] [--status|--validate]" >&2
        exit 2
        ;;
esac
