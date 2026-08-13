#!/usr/bin/env bash
# scripts/opencode-safe.sh
#
# Runtime validation wrapper around the `opencode` CLI.
#
# Layer 3 of the 4-layer validation system. Run as:
#
#     scripts/opencode-safe.sh <subcommand> [args …]
#
# What it does (in order):
#   1.  Validates ./opencode.jsonc against the schema.
#   2.  Verifies SHA-256 integrity against last-known-good (.opencode/integrity).
#   3.  On validator failure: refuses to launch opencode. Suggests rollback.
#   4.  On integrity change: prompts (or auto-records in --record mode).
#   5.  Launches the real `opencode` binary with original args (exec).
#
# Env vars:
#   OPENCODE_BIN              real binary (default: `opencode` on PATH)
#   OPENCODE_SAFE_RECORD=1    accept any new digest as a new baseline
#   OPENCODE_SAFE_BYPASS=1    skip all checks (emergency only — logs reason)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${REPO_ROOT}/opencode.jsonc"
INTEGRITY="${REPO_ROOT}/.opencode/integrity.sha256"
AUDIT="${REPO_ROOT}/.opencode/audit.log"
BIN="${OPENCODE_BIN:-opencode}"

red()    { printf '\033[31m%s\033[0m\n' "$*" >&2; }
yellow() { printf '\033[33m%s\033[0m\n' "$*" >&2; }
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
cyan()   { printf '\033[36m%s\033[0m\n' "$*"; }

audit() {
  mkdir -p "$(dirname "${AUDIT}")"
  printf '%s  opencode-safe  %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "${AUDIT}"
}

# ── Emergency bypass ─────────────────────────────────────────────────────────
if [ "${OPENCODE_SAFE_BYPASS:-0}" = "1" ]; then
  yellow "⚠️  OPENCODE_SAFE_BYPASS=1 — runtime checks skipped"
  audit "BYPASS rc=0 cmd=$*"
  exec "${BIN}" "$@"
fi

# ── 1. Config presence ───────────────────────────────────────────────────────
if [ ! -f "${CONFIG}" ]; then
  red "❌ ${CONFIG} not found — run \`make install\` first"
  audit "MISSING_CONFIG rc=1"
  exit 1
fi

# ── 2. Validator gate ────────────────────────────────────────────────────────
cyan "🔒 Validating opencode.jsonc before launch…"
if ! ( cd "${REPO_ROOT}" && python3 scripts/validate_opencode_config.py --quiet "${CONFIG}" ); then
  red "❌ Config validation failed — refusing to launch opencode."
  red "   See errors above. Recover with: scripts/opencode-safe.sh --rollback"
  red "   Or read: docs/OPENCODE-CONFIG-RECOVERY.md"
  audit "VALIDATE_FAIL rc=1"
  exit 1
fi

# ── 3. Integrity check (last-known-good SHA-256) ─────────────────────────────
current_sha="$(python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "${CONFIG}")"

if [ -f "${INTEGRITY}" ]; then
  recorded_sha="$(cat "${INTEGRITY}")"
  if [ "${recorded_sha}" != "${current_sha}" ]; then
    if [ "${OPENCODE_SAFE_RECORD:-0}" = "1" ]; then
      printf '%s\n' "${current_sha}" > "${INTEGRITY}"
      yellow "ℹ️  New baseline recorded: ${current_sha}"
      audit "INTEGRITY_RECORD sha=${current_sha}"
    else
      yellow "⚠️  opencode.jsonc has changed since last known good."
      yellow "   recorded: ${recorded_sha}"
      yellow "   current:  ${current_sha}"
      yellow "   If intentional, re-record: OPENCODE_SAFE_RECORD=1 scripts/opencode-safe.sh ${*:-status}"
      audit "INTEGRITY_DRIFT was=${recorded_sha} now=${current_sha}"
    fi
  fi
else
  mkdir -p "$(dirname "${INTEGRITY}")"
  printf '%s\n' "${current_sha}" > "${INTEGRITY}"
  cyan "ℹ️  Initial integrity baseline recorded: ${current_sha}"
  audit "INTEGRITY_INIT sha=${current_sha}"
fi

# ── 4. Handle internal --rollback / --record sentinels ───────────────────────
if [ "${1:-}" = "--rollback" ]; then
  BACKUPS_DIR="${REPO_ROOT}/.opencode/backups"
  latest="$(ls -1t "${BACKUPS_DIR}"/*.bak 2>/dev/null | head -1 || true)"
  if [ -z "${latest}" ]; then
    red "❌ No backup found in ${BACKUPS_DIR}"
    exit 1
  fi
  cp "${latest}" "${CONFIG}"
  green "✅ Rolled back to ${latest}"
  audit "ROLLBACK from=${latest}"
  exit 0
fi

# ── 5. Hand off to real opencode ─────────────────────────────────────────────
green "✅ Config validated. Launching: ${BIN} $*"
audit "LAUNCH cmd=$*"
exec "${BIN}" "$@"
