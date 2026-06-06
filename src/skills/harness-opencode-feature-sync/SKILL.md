---
name: harness-opencode-feature-sync
description: >
  Drift/feature sync between OpenCode's agent and sub-agent integration points
  and the agentic-engineers OpenCode renderer. Re-performs the analysis of
  OpenCode's recognized frontmatter schema (KNOWN_KEYS), permission patterns,
  and reasoning/variant mapping, flags renderer drift (no-op keys, uniform
  permissions, missing-but-supported keys), discovers new integration points,
  and self-updates its own machine-readable registry.
license: Proprietary
compatibility: agentic-engineers framework v5.10+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: hygiene
  role: senior-engineer
  trigger: on-demand | post-opencode-upgrade | pre-render
  tdd_phase: GREEN  # 19 tests passing
---

## Overview

**harness-opencode-feature-sync** keeps the agentic-engineers OpenCode renderer
(`renderer/scripts/render-opencode.sh`) aligned with how OpenCode actually loads
agents and sub-agents. OpenCode recognizes a **fixed** set of agent frontmatter
keys; any unknown key is silently swept into an `options` bag and ignored. When
OpenCode evolves (new keys, new permission semantics, new reasoning variants) or
when the renderer drifts from the schema, this skill detects it.

It is the repeatable, re-runnable form of the one-off analysis captured in
[`docs/OPENCODE-RENDERER-FIX-PLAN.md`](../../../docs/OPENCODE-RENDERER-FIX-PLAN.md).

## When to use

- After upgrading or re-syncing the local OpenCode checkout (`~/git/opencode`).
- Before shipping changes to `render-opencode.sh`.
- Periodically, as a drift guard in the rendering pipeline.

## Inputs

| Input | Default | Purpose |
|-------|---------|---------|
| `--opencode-root` | `~/git/opencode` | OpenCode repo to introspect |
| `--repo-root` | auto (repo root) | agentic-engineers repo (locates the renderer) |
| `--registry` | `references/integration-points.yaml` | machine-readable point registry |
| `--renderer` | `<repo>/renderer/scripts/render-opencode.sh` | renderer override |
| `--update-registry` | off | SELF-UPDATE the registry (see below) |
| `--report` | stdout | write markdown report to a path |

## Outputs

- A markdown drift report (stdout or `--report <path>`) covering: OpenCode
  `KNOWN_KEYS`, renderer-emitted keys, drift findings, integration-point
  verification, and discovered candidate points.
- Exit code `2` when an **error**-severity finding exists (e.g. a no-op key),
  else `0`.
- Under `--update-registry`, an in-place rewrite of the registry data file.

## What it checks

1. **Schema fidelity** — parses `KNOWN_KEYS` from
   `packages/opencode/src/config/agent.ts` and diffs it against the top-level
   frontmatter keys the renderer emits. Emitted-but-unknown keys (e.g. the no-op
   `thinking:` block) are flagged as errors; supported-but-unemitted keys (e.g.
   `variant` for reasoning) are flagged as warnings.
2. **Permission least-privilege** — detects a uniform allow-all permission block
   (no per-role differentiation, no `"*": deny` baseline like OpenCode's own
   `explore` agent).
3. **Integration-point liveness** — confirms each registered anchor still exists
   in OpenCode (schema, loader, built-in agents, reasoning/variant mapping, docs)
   and in the renderer.
4. **Discovery** — greps OpenCode's config/agent/provider dirs for
   agent/permission/reasoning symbols not yet in the registry and proposes them
   as candidates.

## Invocation

```bash
# Read-only drift report (default, safe):
python3 scripts/opencode_feature_sync.py

# Write a report file:
python3 scripts/opencode_feature_sync.py --report SYNC.md

# Point at a custom OpenCode checkout:
python3 scripts/opencode_feature_sync.py --opencode-root /path/to/opencode

# Self-update the registry (data only):
python3 scripts/opencode_feature_sync.py --update-registry
```

## Can a skill update itself? (self-updating mechanism)

**Yes.** A skill updates itself by having its script rewrite its own
**`references/` data files** — never its executable logic. Here, the registry
`references/integration-points.yaml` is pure data: the list of OpenCode
integration points to verify each run. Under the `--update-registry` flag the
script:

- refreshes each verified entry's `last_verified` timestamp,
- marks points `missing`/`drifted` when verification or drift detection says so,
- appends newly **discovered** integration points as `candidate` entries,

then re-serializes the YAML (preserving its comment header). Next run, the skill
checks the expanded, current set of points — it has literally updated itself.

**Safeguards:**

- **Dry-run by default** — no flags ⇒ read-only; mutation requires the explicit
  `--update-registry` flag.
- **Data, not logic** — only `references/*.yaml` is mutated; the Python in
  `scripts/` is never self-modified.
- **Human-in-the-loop** — registry changes land in the working tree and are
  reviewed and committed by a human (no auto-commit).
- **Audit trail** — discovered entries are appended with `status: candidate`
  and a `last_verified` date, so every self-added point is traceable in diff and
  git history.

## Files

```
harness-opencode-feature-sync/
├── SKILL.md
├── __init__.py
├── references/
│   └── integration-points.yaml   # machine-readable registry (self-updated)
├── scripts/
│   ├── __init__.py
│   └── opencode_feature_sync.py  # CLI: read-only by default, --update-registry to self-update
└── tests/
    ├── __init__.py
    └── test_opencode_feature_sync.py
```
