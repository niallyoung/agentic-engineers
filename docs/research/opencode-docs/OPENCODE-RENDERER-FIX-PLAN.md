---
title: OpenCode Renderer Fix Plan — Agent/Sub-Agent Frontmatter & Permissions
description: Remediation plan for two defects in render-opencode.sh (no-op thinking block, uniform allow-all permissions) plus a false documentation claim, grounded in OpenCode's actual agent config schema.
version: 1.0
updated: 2026-05-31
status: Proposed
---

# OpenCode Renderer Fix Plan

**Scope:** Correct how `renderer/scripts/render-opencode.sh` emits OpenCode agent frontmatter so it matches OpenCode's actual recognized schema, and fix the false "granular permissions" claim emitted into `dist/opencode/AGENTS.md`.
**Audience:** Renderer maintainers, harness integrators, QA
**Status:** Proposed — no code changed by this document.

---

## Overview

OpenCode loads markdown agents and applies a **fixed frontmatter schema**. Any key
outside that schema is silently swept into an `options` bag and has **no runtime
effect**. The agentic-engineers OpenCode renderer currently emits two constructs
that OpenCode does not honor, and ships documentation that overstates what the
rendered config enforces. This plan documents the ground-truth schema, the
defects, and a concrete, testable remediation.

---

## How OpenCode configures agents / sub-agents (ground truth)

| Concern | OpenCode source | Notes |
|---------|-----------------|-------|
| Agent frontmatter schema (`AgentSchema`, `KNOWN_KEYS`, `normalize()`) | `packages/opencode/src/config/agent.ts` (~lines 21–96) | Schema + post-parse normalisation |
| Markdown agent loader (`{agent,agents}/**/*.md`) | `packages/opencode/src/config/agent.ts` | Loads from `agent/` or `agents/` dirs |
| Built-in agents + permission patterns (`build`, `plan`, `general`, `explore`) | `packages/opencode/src/agent/agent.ts` (~lines 130–282) | `explore` uses `"*": "deny"` + explicit allows |
| Reasoning / variant mapping (effort, Anthropic thinking budgets) | `packages/opencode/src/provider/transform.ts` (~lines 667–724) | Driven by model `variant`, NOT a `thinking:` block |
| Agents docs | `packages/web/src/content/docs/agents.mdx` | Primary/subagent/all semantics |

### Recognized frontmatter keys (the ONLY honored keys)

From `KNOWN_KEYS` in `packages/opencode/src/config/agent.ts`:

```
model, variant, temperature, top_p, prompt, tools (deprecated),
disable, description, mode (subagent|primary|all), hidden,
options, color, steps, maxSteps (deprecated), permission
```

`normalize()` (agent.ts ~lines 70–96) promotes **any unknown key** into
`options.<key>`. This means a misspelled or invented key (e.g. `thinking:`) does
**not** error — it is silently retained in `options` and ignored by the runtime.

### Agent types

- **primary** — user-facing, Tab-cycle selectable. A primary needs `task`
  permission to spawn subagents.
- **subagent** — invoked by a primary via the `task` tool or `@mention`; runs in
  a child session.
- **`mode: all`** — usable as both primary and subagent.
- `default_agent` must be primary-capable (not a subagent, not hidden). The
  renderer correctly uses orchestrator (`mode: all`) as `default_agent`.

### Reasoning / extended thinking

Extended thinking is controlled by the model **`variant`** field, which
`transform.ts` maps to `reasoningEffort` (OpenAI-shaped providers) or Anthropic
**thinking budgets** (`thinking.budgetTokens`, e.g. `high → 16000`). There is
**no** top-level `thinking:` agent key. To enable reasoning for a role you must
(a) emit a supported `variant:` (e.g. `high`/`max`) **and** (b) ensure the
model's provider block in `opencode.jsonc` advertises that variant tier
(`reasoning: true` and an effort/variant the provider exposes).

---

## Defects in `renderer/scripts/render-opencode.sh`

### Defect 1 — No-op `thinking:` block (render-opencode.sh ~lines 762–769)

```sh
case "$name" in
    principal-engineer|security-engineer)
        echo "thinking:"
        echo "  enabled: true"
        echo "  budget_tokens: 5000"
        ;;
esac
```

`thinking` is **not** in `KNOWN_KEYS`, so OpenCode's `normalize()` sweeps it into
`options.thinking` and ignores it. Extended thinking is silently **never
enabled** for principal-engineer / security-engineer. (Also note: even the
intended budget — 5000 — is below OpenCode's `high` Anthropic budget of 16000.)

**Fix:** Replace the `thinking:` block with a supported `variant:` emission for
reasoning-capable roles, and confirm the provider model block in the rendered
`opencode.jsonc` exposes that variant tier.

### Defect 2 — Uniform allow-all permissions (render-opencode.sh ~lines 753–760)

```sh
echo "permission:"
echo "  read: allow"
echo "  edit: allow"
echo "  bash: allow"
echo "  task: allow"
echo "  glob: allow"
echo "  grep: allow"
echo "  webfetch: allow"
```

Every rendered agent gets the identical allow-all block, yet
`dist/opencode/AGENTS.md` (emitted from render-opencode.sh ~line 484) claims
"Each agent has granular permissions enforced by OpenCode at runtime" and prints
a detailed per-agent restriction table. The claim is **false**: the rendered
frontmatter grants the same permissions to every role. Review/analysis roles
(quality-engineer, lead-engineer, model-engineer) receive `edit`/`bash` allow
they should not have.

**Fix:** Drive per-role permissions from a least-privilege matrix (below),
mirroring OpenCode's own `explore` agent pattern (`"*": "deny"` + explicit
allows, agent.ts ~lines 183–199).

### Secondary observations

- **`task: allow` for every subagent** enables unbounded sub-agent recursion.
  Gate `task` to orchestrator and senior-engineer only.
- **Research roles lack `websearch`.** OpenCode's `explore` allows `websearch`
  alongside `webfetch`; reasoning/research roles could add it.
- **False doc claim is generated** — the per-agent permission table lives in the
  renderer (render-opencode.sh ~line 484) and is re-emitted into
  `dist/opencode/AGENTS.md` on every render. Fix at the source (the renderer),
  not the generated artifact.

### What is already correct

Directory `agents/`; the `description`/`mode`/`model`/`temperature`/`permission`
fields; orchestrator `mode: all` as `default_agent`; subagent invocation.

---

## Remediation plan (step by step)

1. **Remove the `thinking:` case** (render-opencode.sh ~762–769).
2. **Add a per-role `variant` emission** for reasoning-capable roles, sourced
   from the variant matrix below. Only emit `variant:` when the role's model
   provider block in `opencode.jsonc` advertises that tier.
3. **Confirm/extend the provider block** in the `opencode.jsonc` emission
   (render-opencode.sh ~lines 237–300) so each model used by a reasoning role
   has `reasoning: true` and exposes the chosen variant tier.
4. **Replace the uniform permission block** (render-opencode.sh ~753–760) with a
   per-role lookup that emits a least-privilege baseline of `"*": deny` plus the
   explicit allows from the permission matrix below.
5. **Gate `task`** to orchestrator and senior-engineer only.
6. **Add `websearch: allow`** to research-capable roles.
7. **Fix the documentation source** (render-opencode.sh ~line 484): make the
   per-agent permission table reflect the actual emitted matrix, OR replace the
   "granular permissions enforced by OpenCode at runtime" prose with an accurate
   statement and a table generated from the same matrix that drives frontmatter,
   so doc and config cannot drift. Re-render to regenerate `dist/opencode/AGENTS.md`.

### Proposed per-role permission matrix

Baseline for every role: `"*": deny`, then explicit allows below. `read`, `glob`,
`grep` are granted to all roles (read-only navigation).

| Role | read | glob | grep | webfetch | websearch | edit | bash | task |
|------|:----:|:----:|:----:|:--------:|:---------:|:----:|:----:|:----:|
| orchestrator      | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| principal-engineer| ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| senior-engineer   | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| engineer          | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| lead-engineer     | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| quality-engineer  | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| security-engineer | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| model-engineer    | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

Rationale: orchestrator routes (no direct edit/bash, but needs `task`);
review/analysis roles (lead, quality, model) are read-only; implementation roles
(engineer, senior, principal, security) get edit/bash; only orchestrator and
senior-engineer may spawn subagents.

### Proposed per-role `variant` mapping (reasoning)

Mirrors the effort column in `docs/AGENTS.md`. Emit only when the role's model
provider block exposes the tier.

| Role | Model | Effort (docs/AGENTS.md) | Proposed `variant` |
|------|-------|------------------------|--------------------|
| orchestrator      | claude-haiku-4.5  | low    | low |
| engineer          | claude-haiku-4.5  | high   | high |
| quality-engineer  | claude-sonnet-4.6 | medium | (none / medium if exposed) |
| senior-engineer   | claude-sonnet-4.5 | high   | high |
| lead-engineer     | claude-sonnet-4.6 | high   | high |
| principal-engineer| claude-opus-4.6   | high   | high |
| security-engineer | claude-opus-4.8   | max    | max |
| model-engineer    | claude-sonnet-4.5 | high   | high |

---

## Acceptance criteria

- No rendered agent frontmatter contains a `thinking:` key.
- Every `variant:` emitted is a member of OpenCode's `KNOWN_KEYS` and is a tier
  advertised by the role's provider block in `opencode.jsonc`.
- Rendered permission blocks differ per role per the matrix above; no
  review/analysis role emits `edit: allow` or `bash: allow`.
- Only orchestrator and senior-engineer emit `task: allow`.
- `dist/opencode/AGENTS.md` permission text matches the emitted matrix (no false
  "granular permissions" claim).
- All rendered frontmatter keys are a subset of OpenCode `KNOWN_KEYS`.

## Validation approach

1. Render: run `renderer/scripts/render-opencode.sh`.
2. Parse `KNOWN_KEYS` from `packages/opencode/src/config/agent.ts` and assert
   every emitted frontmatter key in `dist/opencode/agents/*.md` is a member.
3. Assert per-role permission/variant emissions match the matrices above.
4. Re-run `renderer/scripts/validate_renders.py` to confirm src↔dist parity.
5. Run the new `opencode-feature-sync` skill (see
   `src/skills/opencode-feature-sync/`) to detect any residual drift between
   OpenCode's integration points and the renderer emission.

---

## References

- `packages/opencode/src/config/agent.ts` (schema, `KNOWN_KEYS`, `normalize()`)
- `packages/opencode/src/agent/agent.ts` (built-in agents, `explore` permission pattern)
- `packages/opencode/src/provider/transform.ts` (variant → reasoning/thinking mapping)
- `packages/web/src/content/docs/agents.mdx` (agent semantics)
- `renderer/scripts/render-opencode.sh` (emission sites: ~237–300, ~484, ~753–769)
- `docs/AGENTS.md` (role roster: model + effort)
- `docs/RENDERING.md` (render lifecycle)
