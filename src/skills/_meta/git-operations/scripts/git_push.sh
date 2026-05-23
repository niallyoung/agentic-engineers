#!/usr/bin/env bash
# git_push.sh — git push helpers for the agentic-engineers release workflow.
#
# Source this file to get shell functions; do NOT execute it directly.
#
# Functions exported:
#   git_push_with_tags [--dry-run]
#       Push HEAD to the upstream remote, then push all local tags.
#       --dry-run: show what would happen without executing.
#
#   git_validate_tags <tag> [tag ...]
#       Exit 1 if any named tag does not exist locally.
#
# Design decisions:
#   - Two-step push (commits first, then tags) keeps releases explicit.
#   - Remote is inferred from the current branch's upstream; falls back to "origin".
#   - --dry-run is honoured for both push steps so callers can safely test in CI.

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# _resolve_remote — print the remote name for the current branch, or "origin".
_resolve_remote() {
    local branch
    branch=$(git symbolic-ref --short HEAD 2>/dev/null) || branch=""
    if [ -n "$branch" ]; then
        local remote
        remote=$(git config --get "branch.${branch}.remote" 2>/dev/null) || remote=""
        [ -n "$remote" ] && { echo "$remote"; return 0; }
    fi
    echo "origin"
}

# ---------------------------------------------------------------------------
# git_push_with_tags [--dry-run]
# ---------------------------------------------------------------------------
git_push_with_tags() {
    local dry_run=0
    for arg in "$@"; do
        case "$arg" in
            --dry-run) dry_run=1 ;;
            *) echo "git_push_with_tags: unknown argument: $arg" >&2; return 1 ;;
        esac
    done

    local remote
    remote=$(_resolve_remote)

    if [ "$dry_run" -eq 1 ]; then
        echo "[dry-run] git push ${remote} HEAD"
        echo "[dry-run] git push ${remote} --tags"
        return 0
    fi

    # Step 1: push commits
    echo "🚀 git push ${remote} HEAD..."
    git push "${remote}" HEAD || {
        echo "❌ git push failed (exit $?)" >&2
        return 1
    }

    # Step 2: push tags
    echo "🏷️  git push ${remote} --tags..."
    git push "${remote}" --tags || {
        echo "❌ git push --tags failed (exit $?)" >&2
        return 1
    }

    echo "✅ Push complete (commits + tags → ${remote})"
    return 0
}

# ---------------------------------------------------------------------------
# git_validate_tags <tag> [tag ...]
# ---------------------------------------------------------------------------
git_validate_tags() {
    if [ $# -eq 0 ]; then
        echo "git_validate_tags: no tags specified" >&2
        return 1
    fi

    local missing=0
    for tag in "$@"; do
        if ! git rev-parse --verify "refs/tags/${tag}" >/dev/null 2>&1; then
            echo "❌ tag not found locally: ${tag}" >&2
            missing=$((missing + 1))
        else
            echo "   ✓ tag exists: ${tag}"
        fi
    done

    if [ "$missing" -gt 0 ]; then
        echo "❌ ${missing} tag(s) missing — create them before pushing" >&2
        return 1
    fi
    return 0
}
