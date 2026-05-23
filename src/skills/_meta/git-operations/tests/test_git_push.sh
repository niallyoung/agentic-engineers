#!/usr/bin/env bash
# test_git_push.sh — shell tests for git_push.sh helpers.
#
# Uses a local bare-repo fixture so no network calls are made.
# Run directly: bash tests/test_git_push.sh
# Or via make test (pytest delegates shell tests via subprocess).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GIT_PUSH_SH="$SKILL_ROOT/scripts/git_push.sh"

# ---------------------------------------------------------------------------
# Minimal test harness (no external deps)
# ---------------------------------------------------------------------------
_PASS=0; _FAIL=0

pass() { echo "  ✅ $1"; _PASS=$((_PASS + 1)); }
fail() { echo "  ❌ $1"; _FAIL=$((_FAIL + 1)); }

assert_eq() {
    local desc="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        pass "$desc"
    else
        fail "$desc (expected='$expected', got='$actual')"
    fi
}

assert_exit0() {
    local desc="$1"; shift
    if "$@" >/dev/null 2>&1; then pass "$desc"; else fail "$desc (expected exit 0)"; fi
}

assert_exit1() {
    local desc="$1"; shift
    if "$@" >/dev/null 2>&1; then fail "$desc (expected non-zero exit)"; else pass "$desc"; fi
}

# ---------------------------------------------------------------------------
# Fixture: bare repo acting as "remote" + working clone
# ---------------------------------------------------------------------------
_TMPDIR=$(mktemp -d)
cleanup() { rm -rf "$_TMPDIR"; }
trap cleanup EXIT

BARE_REMOTE="$_TMPDIR/remote.git"
CLONE_DIR="$_TMPDIR/clone"

git init --bare "$BARE_REMOTE" -q
git clone "$BARE_REMOTE" "$CLONE_DIR" -q
cd "$CLONE_DIR"

# Initial commit so HEAD exists
git config user.email "test@test.com"
git config user.name "Test"
echo "init" > README.md
git add README.md
git commit -m "init" -q
git push origin HEAD -q
git tag v0.1.0

# Source helpers under test
# shellcheck source=../scripts/git_push.sh
source "$GIT_PUSH_SH"

# ---------------------------------------------------------------------------
echo ""
echo "── _resolve_remote ────────────────────────────────────────────────"

REMOTE=$(_resolve_remote)
assert_eq "resolves to 'origin' for main branch" "origin" "$REMOTE"

# ---------------------------------------------------------------------------
echo ""
echo "── git_validate_tags ──────────────────────────────────────────────"

assert_exit0 "passes for existing tag v0.1.0" git_validate_tags v0.1.0
assert_exit1 "fails for absent tag v99.0.0" git_validate_tags v99.0.0
assert_exit1 "fails with no args" git_validate_tags
assert_exit1 "fails when any tag is missing" git_validate_tags v0.1.0 v99.0.0

# ---------------------------------------------------------------------------
echo ""
echo "── git_push_with_tags --dry-run ───────────────────────────────────"

DRY_OUTPUT=$(git_push_with_tags --dry-run 2>&1)
if echo "$DRY_OUTPUT" | grep -q "\[dry-run\] git push origin HEAD"; then
    pass "dry-run emits commit push line"
else
    fail "dry-run missing commit push line"
fi
if echo "$DRY_OUTPUT" | grep -q "\[dry-run\] git push origin --tags"; then
    pass "dry-run emits tag push line"
else
    fail "dry-run missing tag push line"
fi

# ---------------------------------------------------------------------------
echo ""
echo "── git_push_with_tags (live, local remote) ────────────────────────"

# Add a second commit + tag for the live push test
echo "v2" >> README.md
git add README.md
git commit -m "feat: second commit" -q
git tag v0.2.0

assert_exit0 "git_push_with_tags succeeds with local remote" git_push_with_tags

# Verify tag landed on bare remote
REMOTE_TAGS=$(git --git-dir="$BARE_REMOTE" tag)
if echo "$REMOTE_TAGS" | grep -q "v0.2.0"; then
    pass "v0.2.0 tag pushed to remote"
else
    fail "v0.2.0 tag NOT found on remote after push"
fi

# ---------------------------------------------------------------------------
echo ""
echo "── git_push_with_tags --dry-run unknown arg ───────────────────────"

assert_exit1 "unknown arg returns exit 1" git_push_with_tags --unknown-flag

# ---------------------------------------------------------------------------
echo ""
echo "── Summary ─────────────────────────────────────────────────────────"
echo "  Passed: $_PASS   Failed: $_FAIL"
echo ""

[ "$_FAIL" -eq 0 ] && exit 0 || exit 1
