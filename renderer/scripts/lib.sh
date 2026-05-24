#!/usr/bin/env bash
# lib.sh — backward-compatibility shim for agentic-engineers renderer scripts
#
# This file now delegates to the unified render library:
#   renderer/lib/render-lib.sh
#
# Existing render scripts (render-claude.sh, render-opencode.sh, render-copilot.sh)
# that source this file will automatically get all functions from render-lib.sh,
# including the expanded API (list_source_specs, validate_frontmatter, etc.).
#
# New code should source renderer/lib/render-lib.sh directly:
#   source "$(dirname "$0")/../lib/render-lib.sh"
#
# Migration note: All functions previously defined here now live in render-lib.sh.
# This shim is kept for backward compatibility with any external scripts that
# source renderer/scripts/lib.sh.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source the unified render library — single source of truth for all renderer functions.
# shellcheck source=../lib/render-lib.sh
source "$SCRIPT_DIR/../lib/render-lib.sh"
