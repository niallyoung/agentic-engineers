# RENDERING.md — Render-to-dist, Install-to-Harness Workflow

This document describes the canonical three-stage pipeline for distributing
skills and agents from source to each AI harness (Claude Code, GitHub Copilot,
OpenCode, π.dev).

---

## Pipeline Overview

```
src/skills/          ──(make render-*)──▶  dist/<harness>/      ──(make install-*)──▶  ~/.harness/
src/agents/                                  (version-controlled)                        (user-local, NOT in repo)

Single source of truth    Rendered, committed            Live harness dirs
```

### Stage 1 — Source (`src/`)

All skill and agent definitions live under `src/`:

```
src/
├── skills/
│   ├── ab-testing/SKILL.md
│   ├── agent-creator/SKILL.md
│   ├── ...
│   └── _meta/               ← framework-internal helpers (NOT rendered to dist/)
└── agents/
    ├── engineer-agent.md
    ├── orchestrator-agent.md
    └── ...
```

**Rules:**
- Every skill must have a `SKILL.md` with valid YAML frontmatter.
- Directories under `src/skills/_meta/` are framework-internal and are not
  rendered to dist/.
- Agent files follow the `<name>-agent.md` naming convention.

---

### Stage 2 — Dist (`dist/`)

`dist/` holds the per-harness rendered output.  It is **committed to the
repository** and serves as the single source of truth for what gets installed.

```
dist/
├── claude/
│   ├── agents/    ← Claude Code agent .md files (frontmatter transformed)
│   └── skills/    ← verbatim skill directories
├── copilot/
│   ├── agents/    ← Copilot CLI agent files
│   └── skills/    ← verbatim skill directories
├── opencode/
│   ├── agents/    ← OpenCode agent files (mode/model/temperature schema)
│   ├── skills/
│   ├── AGENTS.md
│   └── opencode.jsonc
└── pi/
    ├── SYSTEM.md
    ├── AGENTS.md
    ├── settings.json
    ├── pi.yml
    └── SUB_AGENT_SETUP.md
```

**Why commit dist/?**
- Developers can `git diff` to see exactly what will be installed before
  running `make install`.
- CI/CD can verify renders are fresh (no drift from source) without re-running
  the full render pipeline.
- The harness-specific transformations (frontmatter rewriting, model ID mapping,
  etc.) are auditable in git history.

**Render commands:**

| Target              | Renders to          | Description                            |
|---------------------|---------------------|----------------------------------------|
| `make render-claude`  | `dist/claude/`     | Claude Code agents + skills            |
| `make render-copilot` | `dist/copilot/`    | Copilot CLI agents + skills            |
| `make render-opencode`| `dist/opencode/`   | OpenCode agents + skills + config      |
| `make render-pi`      | `dist/pi/`         | π.dev harness config                   |
| `make render-all`     | all four above     | All harnesses in one step              |

---

### Stage 3 — Harness Dirs (`~/.harness/`)

`make install-*` copies the pre-rendered `dist/<harness>/` to the live harness
directory on the developer's machine.  These directories are **outside the
repository** and are never committed.

| Target                | Source            | Destination              |
|-----------------------|-------------------|--------------------------|
| `make install-claude`   | `dist/claude/`  | `~/.claude/`             |
| `make install-copilot`  | `dist/copilot/` | `~/.copilot/`            |
| `make install-opencode` | `dist/opencode/`| `~/.config/opencode/`    |
| `make install-pi`       | `dist/pi/`      | `~/.pi/`                 |
| `make install`          | all four above  | all four destinations    |

Each install target:
1. Validates the `dist/<harness>/` directory is populated (fails fast if not).
2. Uses `rsync` to copy to the harness directory (preserves marker files).
3. Configures git hooks (`core.hooksPath = .githooks`) for harnesses that
   support pre-commit / pre-push hooks.

---

## End-to-End Workflow

```bash
# Full clean rebuild and install
make clean && make render-all && make install

# Single harness
make render-claude && make install-claude

# Validate renders are in sync with source (run as part of quality-gate)
make validate-renders

# Pre-push quality gate (lint + test + verify + validate-renders)
make quality-gate
```

---

## Git Push & Tags

The canonical release workflow after committing changes:

```bash
git push && git push --tags
```

- `git push` — sends commits to the upstream remote.
- `git push --tags` — sends all local annotated/lightweight tags that the remote
  does not yet have.  This triggers GitHub Actions to create a GitHub Release.

The `git_push_with_tags` helper in
`src/skills/_meta/git-operations/scripts/git_push.sh` encapsulates this
two-step pattern.

---

## .gitignore Decisions

| Path                       | Committed? | Reason                                      |
|----------------------------|------------|---------------------------------------------|
| `dist/`                    | ✅ YES      | Single source of truth for rendered output  |
| `src/`                     | ✅ YES      | All source definitions                      |
| `~/.claude/`               | N/A        | Outside repo (harness install target)       |
| `~/.copilot/`              | N/A        | Outside repo (harness install target)       |
| `~/.config/opencode/`      | N/A        | Outside repo (harness install target)       |
| `~/.pi/`                   | N/A        | Outside repo (harness install target)       |
| `.claude` (file in root)   | ❌ NO       | Harness runtime config, not repo artifact   |
| `artifacts/`               | ❌ NO       | Runtime working data                        |

---

## Render Validation

`scripts/validate_renders.py` checks that every renderable skill in `src/skills/`
has a corresponding entry in all `dist/<harness>/skills/` directories.

```bash
# Run manually
python3 scripts/validate_renders.py

# Run via make
make validate-renders

# Automatically included in
make quality-gate
```

The validator exits non-zero if any skill is missing from dist/, prompting you to
run `make render-all` before pushing.

---

## Adding a New Skill

1. Create `src/skills/<name>/SKILL.md` with required frontmatter fields.
2. Run `make render-all` to populate `dist/<harness>/skills/<name>/`.
3. Run `make validate-renders` to confirm all harnesses are in sync.
4. Commit both `src/skills/<name>/` and the updated `dist/` entries.
5. Run `make install` to deploy to your local harness directories.

---

## Renderer Scripts

| Script                                    | Purpose                                  |
|-------------------------------------------|------------------------------------------|
| `renderer/scripts/render-claude.sh`        | Renders to `dist/claude/`               |
| `renderer/scripts/render-copilot.sh`       | Renders skills to `dist/copilot/`       |
| `renderer/scripts/render-copilot-agents.sh`| Renders agents to `dist/copilot/agents/`|
| `renderer/scripts/render-opencode.sh`      | Renders to `dist/opencode/`             |
| `renderer/scripts/render-pi-dev.py`        | Renders to `dist/pi/`                   |

Each renderer accepts `(REPO_ROOT, DEST_DIR)` as positional arguments so it can
target either `dist/<harness>/` (render step) or `~/.harness/` (legacy direct
install).  The Makefile always passes `dist/<harness>/` as the destination and
uses `rsync` in the install step.
