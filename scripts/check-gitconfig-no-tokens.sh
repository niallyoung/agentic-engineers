#!/usr/bin/env bash
# check-gitconfig-no-tokens.sh — guard against the token-in-gitconfig incident class.
#
# WHY THIS EXISTS
# ---------------
# A recurring footgun is embedding a GitHub token directly into git
# configuration so that HTTPS clones authenticate "transparently", e.g.:
#
#     git config --global url."https://x-access-token:ghp_xxx@github.com/".insteadOf "https://github.com/"
#     git config --global credential.helper store          # writes ~/.git-credentials in plaintext
#
# Both of these persist a long-lived credential in plaintext on disk
# (~/.gitconfig or ~/.git-credentials), survive reboots, leak into shared
# machines/CI images, and are trivially exfiltrated. NEVER do this.
#
# SAFE ALTERNATIVES
# -----------------
#   - Interactive / dev:  `gh auth login` then `gh auth setup-git`
#                         (uses the gh credential helper; no token on disk in plaintext)
#   - One-off scoped clone: `git clone --config <key>=<value> ...`  (repo-local, NOT --global)
#   - Token auth in CI:   pass the token via env (GH_TOKEN / GITHUB_TOKEN) to `gh`,
#                         or use GIT_ASKPASS — never write it into git config.
#
# This script inspects the *resolved* global git config and the
# ~/.git-credentials file for token signatures and fails (exit 1) if any
# are found. It is wired into .githooks/pre-push and can be run standalone:
#
#     scripts/check-gitconfig-no-tokens.sh
#
# Exit codes: 0 = clean, 1 = credential material detected.

set -uo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

found=0

# Patterns that indicate a credential has been baked into config.
#   ghp_ / gho_ / ghs_ / ghu_ / ghr_  -> GitHub personal/OAuth/app/refresh tokens
#   x-access-token                    -> GitHub App installation token URL form
#   https://...:...@github            -> userinfo (token/password) embedded in a remote URL
TOKEN_PATTERNS='x-access-token|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|ghs_[A-Za-z0-9]{20,}|ghu_[A-Za-z0-9]{20,}|ghr_[A-Za-z0-9]{20,}|https://[^/@[:space:]]+:[^/@[:space:]]+@github'

scan() {
  # $1 = human label, $2 = text to scan
  local label="$1" text="$2"
  if printf '%s\n' "$text" | grep -Eiq "$TOKEN_PATTERNS"; then
    echo -e "${RED}❌ token-in-gitconfig: credential material detected in ${label}${NC}" >&2
    echo "   Offending key(s):" >&2
    printf '%s\n' "$text" | grep -Ei "$TOKEN_PATTERNS" | sed -E 's/(ghp_|gho_|ghs_|ghu_|ghr_)[A-Za-z0-9]+/\1<redacted>/g; s#(://[^:@]+:)[^@]+@#\1<redacted>@#g' | sed 's/^/     /' >&2
    found=1
  fi
}

# 1. Resolved global config (covers --global writes regardless of file location).
if command -v git >/dev/null 2>&1; then
  GLOBAL_CFG="$(git config --global --list 2>/dev/null || true)"
  scan "global git config (~/.gitconfig)" "$GLOBAL_CFG"
fi

# 2. Raw ~/.gitconfig (in case git is unavailable / include directives).
if [ -f "$HOME/.gitconfig" ]; then
  scan "~/.gitconfig (raw)" "$(cat "$HOME/.gitconfig" 2>/dev/null || true)"
fi

# 3. ~/.git-credentials — should not exist for token-based gh users; plaintext store.
if [ -f "$HOME/.git-credentials" ]; then
  scan "~/.git-credentials" "$(cat "$HOME/.git-credentials" 2>/dev/null || true)"
fi

if [ "$found" -ne 0 ]; then
  echo "" >&2
  echo "Remediation:" >&2
  echo "  1. Remove the offending config:" >&2
  echo "       git config --global --unset-all url.\"https://x-access-token:...@github.com/\".insteadOf" >&2
  echo "       git config --global --unset credential.helper   # if set to 'store'" >&2
  echo "       rm -f ~/.git-credentials" >&2
  echo "  2. Re-authenticate the safe way:  gh auth login && gh auth setup-git" >&2
  echo "  3. ROTATE the leaked token immediately at https://github.com/settings/tokens" >&2
  exit 1
fi

echo -e "${GREEN}✅ gitconfig clean — no embedded tokens or plaintext credentials${NC}"
exit 0
