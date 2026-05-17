#!/usr/bin/env bash
# scripts/validate-opencode-config.sh
#
# Pre-installation validation gate for opencode.jsonc.
#
# Layer 2 of the 4-layer validation system. Called by:
#   - `make install` (before copying opencode.jsonc to ~/.config/opencode)
#   - CI install jobs
#   - Manual operator: `scripts/validate-opencode-config.sh [path]`
#
# Behaviour:
#   1. Validates JSONC syntax + full schema via Python validator
#   2. Creates a timestamped backup before any destructive operation
#   3. Records SHA-256 in .opencode/audit.log (append-only audit trail)
#   4. Exits non-zero on any ERROR; exits 0 on success (warnings OK)
#
# Env vars:
#   OPENCODE_CONFIG_PATH   override default ./opencode.jsonc
#   OPENCODE_STRICT=1      treat warnings as errors
#   OPENCODE_NO_BACKUP=1   skip backup creation (CI / dry-run only)
#   OPENCODE_NO_AUDIT=1    skip audit log append
#
# Exit codes:
#   0  ok
#   1  validation errors (config invalid)
#   2  strict-mode warnings
#   3  prerequisite missing (python3, validator)
#   4  cannot create backup
set -euo pipefail

CONFIG_PATH="${OPENCODE_CONFIG_PATH:-${1:-opencode.jsonc}}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VALIDATOR_MOD="src.opencode.config_validator"
BACKUP_DIR="${REPO_ROOT}/.opencode/backups"
AUDIT_LOG="${REPO_ROOT}/.opencode/audit.log"

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
fail() { printf '\033[31m❌ %s\033[0m\n' "$*" >&2; }
warn() { printf '\033[33m⚠️  %s\033[0m\n' "$*" >&2; }
info() { printf '\033[36mℹ️  %s\033[0m\n' "$*"; }
ok()   { printf '\033[32m✅ %s\033[0m\n' "$*"; }

bold "🔒 OpenCode config pre-install validation"
info "Config: ${CONFIG_PATH}"

# ── Prereqs ───────────────────────────────────────────────────────────────────
if ! command -v python3 >/dev/null 2>&1; then
  fail "python3 not found — required by validator"
  exit 3
fi
if [ ! -f "${REPO_ROOT}/src/opencode/config_validator.py" ]; then
  fail "Validator module not found at src/opencode/config_validator.py"
  exit 3
fi
if [ ! -f "${CONFIG_PATH}" ]; then
  fail "Config not found: ${CONFIG_PATH}"
  exit 1
fi

# ── Backup (self-defense layer) ───────────────────────────────────────────────
if [ "${OPENCODE_NO_BACKUP:-0}" != "1" ]; then
  mkdir -p "${BACKUP_DIR}" || { fail "Cannot create ${BACKUP_DIR}"; exit 4; }
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  base="$(basename "${CONFIG_PATH}")"
  backup="${BACKUP_DIR}/${base}.${ts}.bak"
  cp "${CONFIG_PATH}" "${backup}"
  info "Backup → ${backup}"
fi

# ── Run validator ─────────────────────────────────────────────────────────────
strict_flag=""
[ "${OPENCODE_STRICT:-0}" = "1" ] && strict_flag="--strict"
set +e
if [ -n "${strict_flag}" ]; then
  ( cd "${REPO_ROOT}" && python3 -m "${VALIDATOR_MOD}" "${strict_flag}" "${CONFIG_PATH}" )
else
  ( cd "${REPO_ROOT}" && python3 -m "${VALIDATOR_MOD}" "${CONFIG_PATH}" )
fi
rc=$?
set -e

# ── Audit trail (append-only) ─────────────────────────────────────────────────
if [ "${OPENCODE_NO_AUDIT:-0}" != "1" ]; then
  mkdir -p "$(dirname "${AUDIT_LOG}")"
  sha="$(python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "${CONFIG_PATH}")"
  user="$(whoami)"
  host="$(hostname -s)"
  printf '%s  sha256=%s  rc=%d  user=%s@%s  path=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${sha}" "${rc}" "${user}" "${host}" "${CONFIG_PATH}" \
    >> "${AUDIT_LOG}"
fi

# ── Result ───────────────────────────────────────────────────────────────────
case "${rc}" in
  0) ok "Validation passed — safe to install." ;;
  1) fail "Validation FAILED — see errors above. Install aborted." ;;
  2) warn "Strict-mode warnings — install aborted (unset OPENCODE_STRICT to proceed)." ;;
  *) fail "Validator exited with rc=${rc}" ;;
esac

exit "${rc}"
