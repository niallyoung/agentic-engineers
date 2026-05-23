# OpenCode Configuration — Recovery Procedures

This runbook covers every failure mode of `opencode.jsonc` and the steps to
recover. Each procedure is idempotent and safe to re-run.

---

## 0. Triage matrix

| Symptom | Procedure |
|---|---|
| Pre-commit hook blocks commit | **P1** |
| `make install` aborts on validation | **P2** |
| `opencode-safe` refuses to launch | **P3** |
| OpenCode CLI raises `ConfigInvalidError` after launch | **P4** |
| Integrity drift warning at runtime | **P5** |
| Validator itself crashes | **P6** |
| Total config loss (file deleted / 0 bytes) | **P7** |

If you don't know which: jump to **P4** (the "something broke" generic
procedure).

---

## P1. Pre-commit hook blocked the commit

1. Read the `OC0xx` codes printed by the hook.
2. Look each one up in `OPENCODE-CONFIG-COMMON-MISTAKES.md`.
3. Edit `opencode.jsonc`; re-stage with `git add opencode.jsonc`.
4. Re-commit. The hook re-runs automatically.
5. **Emergency bypass** (must document in commit message):

   ```bash
   BYPASS_HOOK_VALIDATION=true git commit -m "emergency: <reason>"
   ```

   Open a follow-up ticket immediately; document the actual fix plan.

---

## P2. `make install` aborted

The pre-install gate ran `scripts/validate-opencode-config.sh` and found
errors. Note: it already created a backup before failing.

1. Inspect the validator output.
2. If the issue is committed code: fix in the repo, commit, re-run `make install`.
3. If the issue is a local-only edit you don't want: revert and re-install:

   ```bash
   git checkout opencode.jsonc
   make install
   ```

4. Check the audit log: `.opencode/audit.log` records the failure.

---

## P3. `opencode-safe` refuses to launch

The runtime wrapper validates the installed config and refuses to `exec
opencode` if validation fails.

```bash
scripts/opencode-safe.sh --rollback
```

This restores the **most recent backup** from `.opencode/backups/`. If you
need a specific older backup:

```bash
ls -1t .opencode/backups/
cp .opencode/backups/opencode.jsonc.20260517T032140Z.bak opencode.jsonc
make install            # or copy directly to ~/.config/opencode/
```

Verify:

```bash
python3 -m src.opencode.config_validator opencode.jsonc
```

---

## P4. OpenCode CLI raises `ConfigInvalidError`

This means a broken config slipped past pre-commit / pre-install. Treat it
as a defence-in-depth failure and root-cause it.

1. Roll back immediately:

   ```bash
   scripts/opencode-safe.sh --rollback
   ```

2. Run the validator against the **current** (broken) config to capture the
   exact error codes:

   ```bash
   python3 -m src.opencode.config_validator <broken-copy>.jsonc --json \
     > /tmp/opencode-incident-$(date -u +%Y%m%dT%H%M%SZ).json
   ```

3. If the validator says the config is **valid** but OpenCode still rejects
   it, this is a **new failure mode**. Do the following:

   - Open an incident entry in `OPENCODE-CONFIG-INVESTIGATION.md §2`.
   - Add a regression test in `tests/test_opencode_config_validation.py`
     under `TestHistoricalIncidents` (RED-phase first).
   - Extend `src/opencode/config_validator.py` with a new `OC0xx` rule so
     the test passes.
   - Bump the audit-log entry to reference the incident ID.

4. Re-install once the validator catches the new case.

---

## P5. Integrity drift warning

`opencode-safe` reports the SHA-256 of `opencode.jsonc` no longer matches
`.opencode/integrity.sha256`. Decide:

- **Change was intentional** (you edited the config on purpose):
  ```bash
  OPENCODE_SAFE_RECORD=1 scripts/opencode-safe.sh status
  ```
- **Change was not intentional**: assume tampering, roll back:
  ```bash
  scripts/opencode-safe.sh --rollback
  ```

Audit-log review:

```bash
grep INTEGRITY .opencode/audit.log
```

If any `INTEGRITY_DRIFT` line is unexplained, escalate to Security Engineer.

---

## P6. Validator itself crashes

If `python3 -m src.opencode.config_validator …` raises an unhandled
exception:

1. **Stop all installs** — do not push config changes until the validator
   is fixed.
2. Run the test suite to localise the regression:
   ```bash
   python3 -m pytest tests/test_opencode_config_validation.py -v
   ```
3. Bisect with `git bisect` against `src/opencode/config_validator.py`.
4. Open a Security Engineer task tagged `validator-broken` (P0).

---

## P7. Total config loss

The file is missing or zero bytes (`OC010` fires).

```bash
# 1. Restore from most recent backup
ls -1t .opencode/backups/ | head -1
cp ".opencode/backups/$(ls -1t .opencode/backups/ | head -1)" opencode.jsonc

# 2. Validate
python3 -m src.opencode.config_validator opencode.jsonc

# 3. If no backup exists, restore from git
git checkout HEAD -- opencode.jsonc

# 4. If git history also lost, regenerate from renderer
make render-opencode    # or your repo's equivalent
```

---

## Backup & audit-trail invariants

- **Backups** live in `.opencode/backups/`, named
  `opencode.jsonc.YYYYMMDDThhmmssZ.bak`. Created by Layer 2 before every
  install.
- **Audit log** lives at `.opencode/audit.log`. Append-only, one event per
  line. Format: `<utc-ts>  <event>  <details>`.
- **Integrity baseline** lives at `.opencode/integrity.sha256`. Single line,
  the lowercase hex SHA-256 of the last-known-good config.

Operational rules:

1. **Never** edit `.opencode/audit.log` by hand. Treat it like a security
   evidence file; rotate (do not truncate) when it grows.
2. **Never** delete `.opencode/backups/*.bak` without recording the action
   in the audit log first.
3. **Always** re-record the integrity baseline after a deliberate config
   change (`OPENCODE_SAFE_RECORD=1`).

---

## Disaster-recovery test (quarterly)

Run this drill every quarter to confirm the procedures still work:

```bash
# 1. Simulate config corruption
cp opencode.jsonc /tmp/oc.good
echo "BROKEN" > opencode.jsonc

# 2. Confirm pre-commit blocks
git add opencode.jsonc && git commit -m "drill" || echo "✅ pre-commit blocked"

# 3. Confirm pre-install blocks
scripts/validate-opencode-config.sh || echo "✅ pre-install blocked"

# 4. Confirm runtime wrapper rolls back
scripts/opencode-safe.sh --rollback
diff opencode.jsonc /tmp/oc.good && echo "✅ rollback succeeded"

# 5. Restore working tree
git checkout opencode.jsonc
```

Record the drill date in this section's footer:

> **Last drill:** _(none yet)_ — schedule for next quarter.
