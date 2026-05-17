# OpenCode Configuration — Common Mistakes & How to Avoid Them

This is a fast-lookup cheat-sheet keyed by the validator error codes. If your
pre-commit hook or pre-install gate emits an `OC0xx` code, search this
document by code for the explanation and the fix.

---

## ⚠️ Top of the list: the bug that broke prod

### `OC063` — `command.<name>` missing required `template`

**This is the May 17 incident.** OpenCode raises `ConfigInvalidError: 4 of 5
requests failed` and the entire CLI is unusable.

**Wrong:**
```jsonc
"command": {
  "sdlc-check": {
    "description": "Validate SDLC compliance",
    "agent": "orchestrator",
    "subtask": true
    // ❌ no "template"
  }
}
```

**Right:**
```jsonc
"command": {
  "sdlc-check": {
    "description": "Validate SDLC compliance",
    "agent": "orchestrator",
    "subtask": true,
    "template": "Validate SDLC workflow compliance by checking the queue …"
  }
}
```

**Rule of thumb:** **every** `command.*` block must contain a non-empty
`template` string. The template is the prompt OpenCode sends when the user
invokes `/<name>`.

---

## Parse / structural

### `OC000` — Invalid JSON/JSONC syntax

Usually a stray comma or unbalanced brace. Strip comments and re-parse:

```bash
python3 -c "
import re, sys
t = open('opencode.jsonc').read()
t = re.sub(r'(?m)//.*$', '', t)
t = re.sub(r'/\*.*?\*/', '', t, flags=re.DOTALL)
import json; json.loads(t)
"
```

### `OC001` — Top-level is not an object

The file must contain `{...}`, not `[...]`.

---

## Integrity / safety

### `OC010` — File suspiciously small

A truncated file (often from a failed renderer or partial `cp`). Restore
from `.opencode/backups/` — see `OPENCODE-CONFIG-RECOVERY.md`.

### `OC011` — File suspiciously large

Real configs are <10 KB. If yours is >512 KB, something has inlined data
that should live elsewhere (e.g. provider response examples).

### `OC012` — Missing JSONC comment sentinel

The strict OpenCode parser requires the file to look like JSONC. Prepend a
comment line:

```jsonc
// agentic-engineers OpenCode configuration
{ ... }
```

### `OC013` — Possible secret detected

Never put API keys, bearer tokens, passwords, or private keys in
`opencode.jsonc`. Move them to environment variables or a secret manager.
The detector matches common patterns (AWS access keys, GitHub PATs,
OpenAI `sk-…` tokens, generic `password: "…"` patterns).

---

## Top-level

### `OC020` — Unknown top-level key (warn)

Either a typo or a new OpenCode feature we have not catalogued. If it's
real, add it to `KNOWN_TOP_LEVEL` in `src/opencode/config_validator.py`
and `OPENCODE-CONFIG-SCHEMA.md`.

### `OC021` / `OC022` — `$schema` missing or bad

Set:
```jsonc
"$schema": "https://opencode.ai/config.json",
```

### `OC023` / `OC024` — `instructions` wrong shape or unsafe path

Must be a list of repo-relative paths; no leading `/`, no `..`:
```jsonc
"instructions": [".opencode/AGENTS.md"]
```

### `OC025` — `default_agent` bad name

Lowercase, kebab-case, ≤64 chars, must start with a letter.

### `OC026` — Top-level `model` not set (warn)

Without a global model, agents that don't override `model` will fail.
Set one as a safety net:
```jsonc
"model": "github-copilot/claude-haiku-4.5"
```

### `OC027` — `model` malformed

Must be `provider/model-id`, e.g. `github-copilot/claude-opus-4.6`.

---

## `compaction`

### `OC030`–`OC032` — type errors

`compaction` is an object: `{"auto": bool, "reserved": non-negative-int}`.

### `OC033` — `reserved` too high (warn)

Anything above 200 000 defeats compaction. Typical values: 20 000–30 000.

---

## `permission`

### `OC041` — Unknown permission tool (warn)

Likely a typo. Known: `read, edit, bash, task, glob, grep, webfetch,
write, todowrite, todoread, patch`.

### `OC042` — Invalid permission value

Must be exactly `"allow"`, `"ask"`, or `"deny"` (lowercase).

---

## `agent`

### `OC050`–`OC053` — type errors

```jsonc
"agent": {
  "<lowercase-kebab-name>": { "model": "<provider/model>", "mode": "all" }
}
```

### `OC054` — Unknown `mode` (warn)

Known: `all`, `subagent`, `primary`, `interactive`.

---

## `command`

### `OC060`–`OC062` — type errors

`command` is an object keyed by command name; each value is an object.

### `OC063` — missing `template` ⚠️

**See top of file.**

### `OC064` — `template` empty / whitespace

Template must contain real prompt text.

### `OC065` — missing `description` (warn)

Recommended for UX (shown in `opencode help`).

### `OC066` / `OC067` — bad `agent` / `subtask` types

`agent` is an agent-name string; `subtask` is a boolean.

---

## `provider`

### `OC070`–`OC078`

Most common mistakes:

- Forgetting `name` field on a model (`OC075`).
- Setting `id` different from the map key (`OC074`, warn).
- Using zero or negative `limit.context` / `limit.output` (`OC077`).

---

## Cross-field

### `OC080` — `default_agent` not declared (warn)

If you have an `agent` block, `default_agent` should be a key in it.

### `OC081` — `command.*.agent` refers to undeclared agent (error)

The agent name must appear in `agent`. Either add the agent or fix the
typo in `command.*.agent`.

### `OC082` / `OC083` — model not declared in provider (warn)

If you reference `github-copilot/claude-foo-9.9`, declare it under
`provider.github-copilot.models.claude-foo-9.9`.

---

## I/O

### `OC998` / `OC999`

File system problems. Check permissions, file existence, disk space.

---

## Anti-patterns (no validator code yet)

These don't trip the validator but are still mistakes:

1. **Hand-editing the installed copy** (`~/.config/opencode/opencode.jsonc`)
   instead of the repo copy. Next `make install` will overwrite your edit.
   Always edit `opencode.jsonc` in the repo root.
2. **Disabling pre-commit hooks** to "fix later." Don't. The hooks are the
   only thing that catches `OC063` before runtime.
3. **Skipping the validator on CI.** Add `python3 -m
   src.opencode.config_validator --strict opencode.jsonc` to CI; it takes
   <50 ms.
4. **Storing secrets in `provider.*.models.*` cost data.** Cost rates are
   public; API keys are not. Keep them separate.
