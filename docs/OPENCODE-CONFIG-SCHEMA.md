# OpenCode Configuration — Schema Reference

**Authority:** This document is the locally-maintained model of the
`opencode.jsonc` schema. It is the source of truth for the validator at
`src/opencode/config_validator.py`. The upstream JSON Schema URL
(`https://opencode.ai/config.json`) is referenced for IDE support but is not
treated as authoritative because (a) OpenCode's runtime enforces extra
constraints not in the public schema and (b) we have observed the upstream
schema lag behind the CLI's strict checks.

---

## 1. File format

- Filename: **`opencode.jsonc`** (JSONC = JSON + line/block comments + trailing commas).
- Encoding: UTF-8, LF line endings, no BOM.
- Sentinel: the file **MUST** open with a `//` or `/* */` comment line so the
  OpenCode CLI's strict path recognises it as JSONC. (Rule `OC012`.)
- Size: between **32 B** and **512 KB** (rules `OC010` / `OC011`).

---

## 2. Top-level keys

| Key | Required? | Type | Notes | Validator |
|---|---|---|---|---|
| `$schema` | recommended | string (URL) | IDE / CI self-validation. | `OC021`, `OC022` |
| `instructions` | optional | `list[str]` | Repo-relative paths to extra prompt files. No `..` or absolute paths. | `OC023`, `OC024` |
| `default_agent` | optional | string | Must match `^[a-z][a-z0-9-]{0,63}$`. | `OC025` |
| `model` | recommended | `"provider/model-id"` | Used when an agent has no explicit model. | `OC026`, `OC027` |
| `compaction` | optional | object | See §3. | `OC030`–`OC033` |
| `permission` | optional | object | Tool→mode map. See §4. | `OC040`–`OC042` |
| `agent` | optional | object | Per-agent overrides. See §5. | `OC050`–`OC054` |
| `command` | optional | object | Custom commands. See §6. | `OC060`–`OC067` |
| `provider` | optional | object | Provider/model registry. See §7. | `OC070`–`OC078` |
| `experimental` / `share` / `autoupdate` / `theme` / `mcp` / `plugin` | optional | various | Pass-through; surfaced via known-key allowlist for forward-compatibility. | `OC020` (warn on unknown) |

Unknown keys produce a **warning**, not an error, so we stay forward-compatible
when OpenCode adds new top-level fields.

---

## 3. `compaction`

```jsonc
"compaction": {
  "auto": true,              // bool;       default true
  "reserved": 30000          // int ≥ 0;    sanity-capped at 200 000
}
```

- `auto` (bool) — enable automatic context compaction.
- `reserved` (int ≥ 0) — tokens of headroom to keep before triggering compaction.
  Values above `200 000` defeat the purpose; warn.

---

## 4. `permission`

```jsonc
"permission": {
  "read": "allow", "edit": "allow", "bash": "allow",
  "task": "allow", "glob": "allow", "grep": "allow",
  "webfetch": "allow", "write": "ask", "patch": "ask"
}
```

- **Keys**: a member of `{read, edit, bash, task, glob, grep, webfetch, write,
  todowrite, todoread, patch}`. Unknown keys warn.
- **Values**: one of `{"allow", "ask", "deny"}`. Anything else errors.

---

## 5. `agent`

```jsonc
"agent": {
  "orchestrator": {
    "model": "github-copilot/claude-haiku-4.5",
    "mode": "all"            // optional: all | subagent | primary | interactive
  }
}
```

- Agent names: lowercase-kebab, ≤64 chars.
- `model` (if present) must be `provider/model-id`.
- `mode`: one of the four known values; unknown values warn (forward-compat).

---

## 6. `command` ⚠️ **most error-prone**

```jsonc
"command": {
  "sdlc-check": {
    "description": "Validate SDLC workflow compliance.",
    "agent": "orchestrator",
    "subtask": true,
    "template": "Validate SDLC workflow compliance by …"  // ⚠️ REQUIRED
  }
}
```

| Field | Required? | Type | Validator |
|---|---|---|---|
| `template` | **✅ required — incident #2 cause** | non-empty string | `OC063`, `OC064` |
| `description` | recommended | string | `OC065` warn |
| `agent` | optional | string (existing agent) | `OC066`, cross-ref `OC081` |
| `subtask` | optional | bool | `OC067` |

> **DO NOT** define a command without `template`. OpenCode will fail with
> `ConfigInvalidError` and the whole CLI becomes unusable. See
> `OPENCODE-CONFIG-COMMON-MISTAKES.md §1`.

---

## 7. `provider`

```jsonc
"provider": {
  "github-copilot": {
    "models": {
      "claude-haiku-4.5": {
        "id":   "claude-haiku-4.5",   // SHOULD equal the parent key
        "name": "Claude Haiku 4.5",
        "family": "claude",
        "release_date": "2025-04-01",
        "attachment": false, "reasoning": false, "temperature": true, "tool_call": true,
        "cost":  { "input": 0.0000008, "output": 0.000004,
                   "cache_read": 0.0000001, "cache_write": 0.000001 },
        "limit": { "context": 200000, "output": 8192 },
        "modalities": { "input": ["text"], "output": ["text"] },
        "status": "active"
      }
    }
  }
}
```

- `provider.<name>.models.<id>.id` SHOULD equal the parent map key (`OC074` warn).
- `name` and `id` are required (`OC075`).
- `limit.context` and `limit.output` must be positive integers (`OC077`).
- `cost` and `limit` must be objects when present (`OC076`, `OC078`).

---

## 8. Cross-field rules

| Rule | Description | Validator |
|---|---|---|
| `default_agent` declared | If `agent.*` block is present, `default_agent` must be a key in it. | `OC080` (warn) |
| `command.*.agent` declared | If `agent.*` block is present, every `command.*.agent` must be a key in it. | `OC081` (error) |
| Models declared | Any `provider/model` string referenced by `model` or `agent.*.model` must be declared in some `provider.*.models`. | `OC082`, `OC083` (warn) |

---

## 9. Error-code namespace

The validator emits stable codes so each rule can be referenced by tests,
documentation, and incident reports.

| Range | Family |
|---|---|
| `OC000`, `OC001` | Parse / structural |
| `OC010`–`OC013` | Integrity / safety (size, sentinel, secrets) |
| `OC020`–`OC027` | Top-level keys |
| `OC030`–`OC033` | `compaction` |
| `OC040`–`OC042` | `permission` |
| `OC050`–`OC054` | `agent` |
| `OC060`–`OC067` | `command` |
| `OC070`–`OC078` | `provider` |
| `OC080`–`OC083` | Cross-field references |
| `OC998`, `OC999` | File I/O |

Codes are append-only; never reuse a retired number.

---

## 10. Worked example: minimum valid config

```jsonc
// agentic-engineers OpenCode configuration
{
  "$schema": "https://opencode.ai/config.json",
  "model": "github-copilot/claude-haiku-4.5",
  "default_agent": "orchestrator",
  "compaction": { "auto": true, "reserved": 30000 },
  "permission": {
    "read": "allow", "edit": "allow", "bash": "allow",
    "task": "allow", "glob": "allow", "grep": "allow", "webfetch": "allow"
  },
  "agent": {
    "orchestrator": { "model": "github-copilot/claude-haiku-4.5" }
  },
  "command": {
    "sdlc-check": {
      "description": "Validate SDLC compliance",
      "agent": "orchestrator",
      "subtask": true,
      "template": "Validate SDLC workflow compliance."
    }
  },
  "provider": {
    "github-copilot": {
      "models": {
        "claude-haiku-4.5": {
          "id": "claude-haiku-4.5",
          "name": "Claude Haiku 4.5",
          "limit": { "context": 200000, "output": 8192 }
        }
      }
    }
  }
}
```

This passes the validator with zero errors and zero warnings.
