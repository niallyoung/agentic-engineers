# OpenCode Configuration — Incident Investigation & Root-Cause Analysis

**Status:** Closed (preventive controls implemented)
**Owner:** Security Engineer
**Last updated:** 2026-05-17
**Task ID:** `2026-05-17-opencode-config-validation`

This document is the authoritative record of every known incident in which
`opencode.jsonc` broke the OpenCode CLI harness, the patterns behind those
incidents, and the controls now in place to prevent recurrence.

---

## 1. Executive summary

The Orchestrator's **primary harness** is the OpenCode CLI. Its configuration
file (`opencode.jsonc`) is loaded at every CLI invocation; if it is malformed
or schema-violating, OpenCode exits with `ConfigInvalidError` and the entire
agentic-engineers workflow halts.

We have observed **two confirmed incidents** plus several near-misses caught
during development. All of them share two root causes:

1. **No proactive validation** — errors were only detected at runtime, after
   the broken config was already on disk.
2. **Implicit schema** — OpenCode's command-block schema requires fields that
   are not obvious from documentation, and we discovered them by induction.

This investigation produced ten deliverables (5 docs + 5 code) — see
`docs/OPENCODE-CONFIG-VALIDATION-INITIATIVE.md` for the full list. The most
important is the JSON-Schema-style validator at
`src/opencode/config_validator.py`, integrated into:

- `.githooks/pre-commit` — Layer 1 (developer machine)
- `scripts/validate-opencode-config.sh` — Layer 2 (pre-install / CI)
- `scripts/opencode-safe.sh` — Layer 3 (runtime wrapper, integrity check)
- `tests/test_opencode_config_validation.py` — Layer 4 (regression suite, 99% cov)

Every codified rule in the validator carries a stable `OC0xx` code so future
incidents can be traced back to a specific check.

---

## 2. Timeline & incidents

### Incident #1 — Missing JSONC comment sentinel
**Date observed:** 2026-05-16 (commit `54b7d05`)
**Symptom:** OpenCode rejected the file with a strict-schema error.
**Root cause:** OpenCode parses `*.jsonc` files only when it can identify them
as JSONC. The strict path in the CLI uses the presence of a leading comment
(`//` or `/* */`) as a sentinel. A previous renderer emitted comment-free
JSON, which was technically valid JSON but failed the JSONC strict check.

**Fix at the time:** Manual — prepend a comment line.
**Codified prevention:** validator rule **`OC012`** rejects any opencode.jsonc
whose first non-blank line is not a comment. Regression test:
`TestHistoricalIncidents::test_incident_jsonc_sentinel_required`.

### Incident #2 — Missing `template` field in custom commands (CRITICAL)
**Date observed:** 2026-05-17 (today)
**Symptom:** `ConfigInvalidError: 4 of 5 requests failed`. The OpenCode CLI
was completely unusable for the Orchestrator.
**Root cause:** A `command.<name>` block had `description`, `agent` and
`subtask` set, but no `template` string. OpenCode's command schema requires
`template` — without it, every command invocation fails to render the user
prompt.

**Detection path:** Only caught when the user actually invoked `opencode
--agent orchestrator`. By that point, the broken config was committed and
installed.

**Fix at the time:** Copilot CLI manually added the missing `template`
strings (commit `b5ace7b`).

**Codified prevention:** validator rule **`OC063`** rejects any
`command.<name>` block missing `template`. Companion rule `OC064` rejects
empty / whitespace-only templates. Regression test:
`TestHistoricalIncidents::test_incident_2026_05_17_missing_template`.

### Near-miss A — Orchestrator default-agent drift
**Date observed:** 2026-05-16 (commits `91c34ae`, `9db58d1`, `addd562`)
**Symptom:** `--agent orchestrator` failed because the agent was the
default but had not been declared in the `agent` block.
**Codified prevention:** rule **`OC080`** (warning) when `default_agent`
points to an agent that is not declared. Regression test:
`TestHistoricalIncidents::test_incident_orchestrator_default_agent_undeclared`.

### Near-miss B — Provider model id mismatch
**Date observed:** during renderer development
**Symptom:** Agent had `model: github-copilot/claude-opus-4.6`, but the
provider block only declared `claude-haiku-4.5`. Runtime fallback caused
the wrong model to be invoked silently.
**Codified prevention:** rule **`OC082`** / **`OC083`** (warnings) when a
referenced model is not declared in any `provider.*.models`.

---

## 3. Pattern analysis

| Pattern | Manifestation | Validator code(s) |
|---|---|---|
| **Required-field omission** | OpenCode silently requires `command.*.template`, `provider.*.models.*.name`, etc. | `OC063`, `OC065`, `OC075` |
| **Format-sentinel violation** | JSONC must "look like" JSONC (leading comment). | `OC012` |
| **Dangling reference** | `default_agent` / `command.*.agent` / `agent.*.model` referring to undeclared names. | `OC080`, `OC081`, `OC082`, `OC083` |
| **Permission typo** | `"read": "allowed"` instead of `"allow"`. | `OC041`, `OC042` |
| **Numeric off-by-domain** | `compaction.reserved` negative or absurdly high. | `OC032`, `OC033` |
| **Schema URL drift** | `$schema` removed or pointing at a non-URL. | `OC021`, `OC022` |
| **Secret leakage** | Pasted API key or token in config. | `OC013` |
| **Truncation / size bombs** | Config truncated to 0 bytes by failed render. | `OC010`, `OC011` |

All eight pattern families are now covered by automated tests; see
`tests/test_opencode_config_validation.py`.

---

## 4. Why detection was late

1. **No pre-commit gate** specifically for `opencode.jsonc`. The generic
   JSON syntax check accepted the file because it *was* valid JSON — it
   just failed OpenCode's schema requirements.
2. **No pre-install gate.** `make install` copied the file verbatim.
3. **No runtime wrapper.** `opencode` was launched directly; its own error
   path was the only safety net.
4. **No regression tests** existed for the bugs we had already seen.

The four-layer system documented in §1 closes each of these gaps.

---

## 5. Mean-time-to-detect (MTTD) before / after

| Layer | Before | After |
|---|---|---|
| Developer pre-commit | n/a | **<50 ms** (validator on staged file) |
| Pre-install | n/a | **<200 ms** (validate + backup + audit) |
| Runtime | seconds-to-minutes (until user invoked a broken command) | **<200 ms** (validate before exec) |
| Regression | 0 | **79 tests, 99 % line coverage** |

Effective MTTD goes from "until a human notices" → **bounded at commit time**.

---

## 6. Threat-model recap

| Threat | Likelihood (before) | Mitigation |
|---|---|---|
| Accidental schema violation by a renderer | **High** | Layers 1–3 catch before launch |
| Malicious tampering with `opencode.jsonc` | Low | Layer 3 integrity check (SHA-256 in `.opencode/integrity.sha256`) detects drift; audit log records every change |
| Secret leakage into checked-in config | Medium | Rule `OC013` rejects common secret patterns |
| Silent corruption (disk error, partial write) | Low | Rule `OC010` rejects suspiciously small files; backup before every install |
| Untrusted commit pushing a broken config to main | Medium | Pre-commit + pre-push hook layers + branch-protection tests |

No high-severity residual risks remain. Low residual risks are accepted and
tracked here for revisit at the next quarterly review.

---

## 7. Action items closed by this initiative

- [x] Document every known incident with timestamp + root cause (this file)
- [x] Document full schema (`OPENCODE-CONFIG-SCHEMA.md`)
- [x] Codify each incident as a regression test
- [x] Implement validator with stable error codes (`OC000`–`OC083`)
- [x] Wire validator into pre-commit, pre-install, and runtime layers
- [x] Add backup, rollback, audit-trail, integrity-check self-defense
- [x] Document user-facing guide, common mistakes, recovery procedures
- [x] Achieve ≥95 % test coverage (achieved **99 %**, 79 tests)

---

## 8. Forward-looking commitments

1. Any new historical incident is added to §2 **and** to
   `TestHistoricalIncidents` in the same commit.
2. The validator's `OC0xx` code namespace is treated as a public contract;
   removing or renumbering a code requires a Principal Engineer sign-off.
3. The Security Engineer re-reads this file every quarter and during any
   OpenCode CLI major-version upgrade.
