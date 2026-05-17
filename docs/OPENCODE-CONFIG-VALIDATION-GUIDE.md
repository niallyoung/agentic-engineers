# OpenCode Configuration Validation Guide

This is the user-facing guide for the validation system that protects
`opencode.jsonc`. For the root-cause history see
`OPENCODE-CONFIG-INVESTIGATION.md`; for the full schema see
`OPENCODE-CONFIG-SCHEMA.md`.

---

## 1. The 4-layer model

```
            ┌─────────────────────────────┐
Developer → │ 1. Pre-commit hook          │  .githooks/pre-commit
            │    Blocks bad commit        │
            └──────────────┬──────────────┘
                           ▼
            ┌─────────────────────────────┐
Installer → │ 2. Pre-install gate         │  scripts/validate-opencode-config.sh
            │    Backup + validate + audit│
            └──────────────┬──────────────┘
                           ▼
            ┌─────────────────────────────┐
Runtime   → │ 3. opencode-safe wrapper    │  scripts/opencode-safe.sh
            │    Validate + integrity     │
            └──────────────┬──────────────┘
                           ▼
            ┌─────────────────────────────┐
CI / dev  → │ 4. Regression test suite    │  tests/test_opencode_config_validation.py
            │    79 tests, 99 % cov       │
            └─────────────────────────────┘
```

Every layer uses the same Python validator
(`src/opencode/config_validator.py`) so behaviour is consistent.

---

## 2. Quick start

### Validate now (developer workstation)

```bash
python3 -m src.opencode.config_validator opencode.jsonc
# Exit 0 → ok, 1 → errors, 2 → strict warnings, 3 → I/O error.
```

### Strict mode (treat warnings as failures)

```bash
python3 -m src.opencode.config_validator --strict opencode.jsonc
```

### Machine-readable JSON output

```bash
python3 -m src.opencode.config_validator --json opencode.jsonc | jq .
```

### Run the regression suite

```bash
python3 -m pytest tests/test_opencode_config_validation.py -v
```

---

## 3. Layer 1 — pre-commit hook

`/.githooks/pre-commit` is extended with an `opencode.jsonc` block. When that
file is staged, the hook validates the *staged content* (so `git commit
--amend` is also checked) and blocks the commit on any `ERROR` finding.

Install hooks once (already wired into `make install`):

```bash
git config core.hooksPath .githooks
```

Emergency bypass (must be documented in commit message):

```bash
BYPASS_HOOK_VALIDATION=true git commit -m "emergency: <reason>"
```

---

## 4. Layer 2 — pre-install validation

`scripts/validate-opencode-config.sh` is the install gate. It:

1. Validates `opencode.jsonc` with the full schema.
2. Creates a timestamped backup in `.opencode/backups/`.
3. Appends an entry to `.opencode/audit.log` (`timestamp sha256 rc user@host path`).
4. Exits non-zero on validation failure so `make install` aborts before
   touching the installed config.

Typical usage:

```bash
scripts/validate-opencode-config.sh                  # uses ./opencode.jsonc
scripts/validate-opencode-config.sh path/to/cfg      # explicit path
OPENCODE_STRICT=1 scripts/validate-opencode-config.sh   # warnings ⇒ failure
OPENCODE_NO_BACKUP=1 scripts/validate-opencode-config.sh # CI / dry-run only
OPENCODE_NO_AUDIT=1 scripts/validate-opencode-config.sh  # ditto
```

Recommended wiring (Makefile):

```make
install: validate-config
        cp opencode.jsonc ~/.config/opencode/opencode.jsonc
        …

validate-config:
        scripts/validate-opencode-config.sh
```

---

## 5. Layer 3 — runtime wrapper

`scripts/opencode-safe.sh` is a drop-in replacement for the `opencode`
binary. It validates the config and verifies the SHA-256 integrity baseline
before `exec`ing the real binary.

Typical aliases:

```bash
alias opencode='scripts/opencode-safe.sh'
```

Operations:

```bash
scripts/opencode-safe.sh                   # validate + launch interactive
scripts/opencode-safe.sh --agent worker    # any opencode args work
scripts/opencode-safe.sh --rollback        # restore most recent backup
OPENCODE_SAFE_RECORD=1 scripts/opencode-safe.sh status   # record new baseline after intentional change
OPENCODE_SAFE_BYPASS=1 scripts/opencode-safe.sh ...      # emergency bypass (logged)
```

Integrity baseline file: `.opencode/integrity.sha256`. If the live config's
SHA-256 differs from the baseline, the wrapper warns (does not block) and
prompts the operator to re-record with `OPENCODE_SAFE_RECORD=1`.

---

## 6. Layer 4 — regression tests

`tests/test_opencode_config_validation.py` contains 79 tests organised into:

- JSONC parser unit tests
- one positive + one negative test per `OC0xx` rule
- a `TestHistoricalIncidents` class with one test per documented incident
- CLI exit-code matrix
- file I/O and integrity helpers

Run as part of normal pytest:

```bash
python3 -m pytest tests/test_opencode_config_validation.py
```

Target: **≥95 % line coverage** of the validator. Current: **99 %**.

---

## 7. Error-code reference (`OC0xx`)

See `OPENCODE-CONFIG-SCHEMA.md §9` for the full namespace map. Every error
message printed by the validator contains its `OC0xx` code; you can search
`OPENCODE-CONFIG-COMMON-MISTAKES.md` by code to find a remedy.

---

## 8. Audit trail format

`.opencode/audit.log` (append-only) has one of:

```
2026-05-17T03:21:40Z  sha256=0b84a2c…  rc=0  user=niall@laptop  path=opencode.jsonc
2026-05-17T03:23:11Z  opencode-safe  LAUNCH cmd=--agent orchestrator
2026-05-17T03:24:02Z  opencode-safe  INTEGRITY_DRIFT was=0b84a2…  now=eef912…
```

Treat the file as immutable evidence; rotate via standard logrotate.

---

## 9. Recovery checklist (TL;DR)

| Situation | Action |
|---|---|
| Pre-commit blocked my commit | Read the `OC0xx` codes, fix the config, re-stage, re-commit. |
| `make install` aborted | Read the validator output; if the issue is in the *committed* config, revert with `git checkout opencode.jsonc`. |
| `opencode-safe` refuses to launch | `scripts/opencode-safe.sh --rollback` restores the most recent backup from `.opencode/backups/`. |
| Integrity drift warning | If change is intentional: `OPENCODE_SAFE_RECORD=1 scripts/opencode-safe.sh status`. |
| Validator itself failing | Run pytest; if the validator is broken, hold off on installs and escalate to Security Engineer. |

Full recovery procedures: `OPENCODE-CONFIG-RECOVERY.md`.
