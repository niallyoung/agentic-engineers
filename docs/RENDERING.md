---
title: Rendering & Harness Lifecycle
description: Complete lifecycle documentation for the agentic-engineers render pipeline — from source authoring through build-time rendering to runtime loading.
version: 1.0
updated: 2026-05-24
status: Authoritative
---

# Rendering & Harness Lifecycle

**Scope:** How source entities (agents, skills, specs) are rendered, deployed, and loaded  
**Audience:** Contributors, harness integrators, CI/CD engineers  

---

## Overview

The agentic-engineers framework separates **authoring** (source), **rendering** (build-time), and **loading** (runtime) into distinct lifecycle phases. This prevents harness-specific implementation details from leaking into source code and enables a single canonical source to target multiple AI harnesses.

```
src/                    dist/                   ~/.copilot/ (etc.)    AI Harness
─────────────────────   ─────────────────────   ─────────────────     ─────────────
agents/*-agent.md  ──►  copilot/agents/         ~/.copilot/agents/   loaded at session start
skills/*/SKILL.md  ──►  copilot/skills/         ~/.copilot/skills/   loaded on demand (skill tool)
config/SPEC.md etc ──►  specs/                  n/a (local ref only) QA/consistency checks
src/agents/*.md    ──►  opencode/agents/        ~/.config/opencode/  loaded at session start
src/skills/*/      ──►  opencode/skills/        ~/.config/opencode/  loaded on demand
```

The install/runtime roots are `~/.config/opencode/`, `~/.copilot/`, `~/.claude/`, and `~/.codex/` (with Codex also honoring project-scoped `.codex/` when present).

---

## Copilot CLI Harness Notes

### /fleet Command Incompatibility (GA April 2026)

GitHub Copilot CLI's native `/fleet` command enables parallel multi-agent orchestration. However, it is **not compatible** with agentic-engineers' DELEGATE/HANDBACK protocol for the following architectural reasons:

**Why /fleet doesn't fit our model:**
- `/fleet` accepts a single task description; the orchestrator decomposes it into work items and distributes them to subagents
- Our DELEGATE/HANDBACK protocol requires sending a unique, fully self-contained DELEGATE block to each subagent, with different scope, plan, and success criteria per specialist role
- /fleet has no mechanism to pass per-agent prompts; all work items derive from the single parent prompt
- Our use case (e.g., dispatching Engineer, Senior Engineer, and Lead Engineer in parallel with different instructions) requires role-specific prompts, not decomposed work items

**The fundamental mismatch:**
- `/fleet` model: 1 prompt → orchestrator decomposes → N work items
- DELEGATE model: N DELEGATE blocks → N subagents receive unique prompts

**Recommendation:** Use agentic-engineers' Orchestrator role to fan out independent tasks with role-specific DELEGATEs (the current approach). The harness session transcript already provides the audit trail and coordination layer that /fleet provides.

---

## Lifecycle Phases

### Phase 1: Authoring (Source Layer — `src/`)

**Location:** `src/agents/`, `src/skills/`, `config/`, `docs/`  
**When:** Developer creates or edits source files  
**Format:** YAML frontmatter + Markdown body  
**Lifecycle marker:** None — plain source files  

#### Entity types and their source locations:

| Entity Type | Source Location | Naming Convention | Required Fields |
|-------------|----------------|-------------------|-----------------|
| **Agents**  | `src/agents/`  | `<name>-agent.md` | `name`, `description`, `model`, `role` |
| **Skills**  | `src/skills/<name>/` | `SKILL.md` in each dir | `name`, `description` |
| **Specs**   | `docs/SPEC.md`, `config/*.yaml` | SPEC.md or *.yaml | varies |

#### Lifecycle markers in source files:
Source files do **not** carry lifecycle markers. Lifecycle context is added at render time via the `FRAMEWORK-MANIFEST.yaml` registry.

```yaml
# config/FRAMEWORK-MANIFEST.yaml — authoritative entity registry
agents:
  engineer:
    status: active        # build-time: include in render; archive: exclude
    last_deployed: "2026-05-24"  # updated by renderer
```

---

### Phase 2: Build-Time Rendering (`make render-*`)

**Trigger:** `make render-opencode`, `make render-copilot`, `make render-claude`, `make render-codex`, `make render-specs`, or `make render-all`
**Output:** `dist/<harness>/`  
**Scripts:** `renderer/scripts/render-*.sh`  
**Shared library:** `renderer/lib/render-lib.sh` (via `renderer/scripts/lib.sh` shim)  

#### What happens at build time:

1. **Agent rendering** — source `*-agent.md` frontmatter is transformed into harness-specific format:
   - Copilot: `dist/copilot/agents/<name>-agent.agent.md` (Copilot CLI agent YAML)
   - Claude Code: `dist/claude/agents/<name>.md` (Claude Code subagent format)
   - OpenCode: `dist/opencode/agents/<name>.md` (OpenCode subagent format)
   - Codex: `dist/codex/agents/<name>.toml` (Codex custom agent format)

2. **Skill rendering** — skill directories rsync'd to dist/:
   - Copilot: `dist/copilot/skills/<name>/` 
   - Claude Code: `dist/claude/skills/<name>/`
   - OpenCode: `dist/opencode/skills/<name>/`
   - Codex: `dist/codex/skills/<name>/`
   - Note: SKILL.md files are NOT transformed — they're compatible across all harnesses.

3. **Spec rendering** — `make render-specs` copies canonical specs to `dist/specs/`:
   - `docs/SPEC.md` → `dist/specs/SPEC.md`
   - `config/FRAMEWORK-MANIFEST.yaml` → `dist/specs/FRAMEWORK-MANIFEST.yaml`
   - `config/orchestration.yaml` → `dist/specs/orchestration.yaml`

4. **Marker files** — written to track managed files for safe uninstall:
   - Skills: `<skill_dir>/.agentic-engine-<harness>` (e.g. `.agentic-engine-claude`)
   - Agents: `agents/.agentic-engine-<harness>` (manifest file, e.g. `.agentic-engine-claude`)
   - Specs: `dist/specs/.agentic-engine-specs`

5. **Orphaned skill pruning** — after installing/updating skills, each of
   `render-claude.sh`, `render-copilot.sh`, and `render-opencode.sh` calls
   `prune_orphaned_skills()` (`renderer/lib/render-lib.sh`): it removes any previously
   installed skill directory whose source under `src/skills/` no longer exists (e.g. from
   a slimdown round), gated on that directory still carrying the harness's own marker file
   — a directory without the marker is treated as foreign/user-authored and left alone.
   The step always runs (no dry-run mode) and prints a single report line, e.g.
   `🧹 pruned 2 orphaned managed skill(s): foo, bar` or `🧹 pruned 0 orphaned managed skill(s)`.

5.5 **Orphaned agent pruning** — after installing/updating agents, each renderer
   also calls `prune_orphaned_agents()` (`renderer/lib/render-lib.sh`): it removes any
   previously installed agent file whose source under `src/agents/` no longer exists
   (e.g. from a rename or deletion), gated on that agent still being listed in the
   harness's own manifest file — an agent not in the manifest is treated as foreign/user-authored
   and left alone.

#### Renderer library architecture (post-consolidation):

```
renderer/
├── lib/
│   └── render-lib.sh          # UNIFIED library — single source of truth
│       ├── list_source_skills  # enumerate skills by SKILL.md presence
│       ├── list_source_agents  # enumerate agents by *-agent.md pattern
│       ├── list_source_specs   # enumerate spec directories by SPEC.md presence
│       ├── extract_fm          # parse YAML frontmatter field
│       ├── strip_fm            # strip frontmatter, return body
│       ├── validate_frontmatter   # check required fields for entity type
│       ├── validate_entity_structure  # verify rendered file format
│       ├── validate_deployment    # comprehensive deployment check
│       ├── yaml_escape_inline  # safe YAML string escaping
│       ├── map_model           # short model name mapping (haiku/sonnet/opus)
│       └── emit_progress       # consistent progress output (human/json modes)
└── scripts/
    ├── lib.sh                  # backward-compat SHIM — sources render-lib.sh
    ├── render-copilot.sh       # renders agents (via render-copilot-agents.py) + skills → dist/copilot/
    ├── render-copilot-agents.py # Python agent renderer (Copilot CLI format)
    ├── render-claude.sh        # renders agents + skills → dist/claude/
    ├── render-opencode.sh      # renders agents + skills + opencode.jsonc → dist/opencode/
    ├── render-codex.py         # renders Codex custom agents + skills + config → dist/codex/
    ├── render-specs.sh         # renders SPEC.md + config YAMLs → dist/specs/
    └── validate_renders.py     # validates dist/ sync with src/
```

**All render scripts source `lib.sh` (shim), which delegates to `render-lib.sh`.**

---

### Phase 3: Install-Time Deployment (`make install-*`)

**Trigger:** `make install-opencode`, `make install-copilot`, `make install-claude`, `make install-codex`, or `make install`
**Source:** `dist/<harness>/`  
**Destination:** `~/.config/opencode/`, `~/.copilot/`, `~/.claude/`, `~/.codex/`
**Method:** `rsync -a` with `.DS_Store` and `.git` exclusions  

**Note:** `dist/specs/` is **not** deployed to a harness home directory — specs are a local reference layer only (used by validation, QA, and consistency checks). They live in `dist/specs/` and `config/` as source-of-truth files.

#### Install produces:

| Harness | Agent format | Skill format | Config files |
|---------|-------------|-------------|--------------|
| OpenCode | `agents/<name>.md` (mode/model/temp) | `skills/<name>/SKILL.md` | `opencode.jsonc`, `AGENTS.md` |
| Copilot CLI | `*.agent.md` (YAML frontmatter) | `skills/<name>/SKILL.md` | – |
| Claude Code | `agents/<name>.md` | `skills/<name>/SKILL.md` | – |
| Codex | `agents/<name>.toml` | `~/.codex/skills/<name>/SKILL.md` | `config.toml`, `AGENTS.md` |

---

### Phase 4: Runtime Loading (AI Harness)

**Trigger:** AI harness session start / user invokes skill tool  
**Source:** `~/.config/opencode/`, `~/.copilot/`, `~/.claude/`, `~/.codex/` (installed copies)

#### Loading behavior by entity type:

**Agents** (loaded at session start):
- Copilot CLI: reads `agents/*.agent.md` on session initialization; agent becomes available via `@agent-name` or `copilot --agent=<name>`
- Claude Code: reads `agents/*.md` on session start; subagents available via `@name` references
- OpenCode: reads `agents/*.md`; subagents available via `@name` in chat
- Codex: reads custom agents from `~/.codex/agents/*.toml` or project `.codex/agents/*.toml`; subagents spawn only when explicitly requested

**Skills** (loaded on demand, not at session start):
- All harnesses: skill directories discovered lazily when `skill` tool is invoked
- The `SKILL.md` file describes the skill's purpose, inputs, and outputs
- Scripts within the skill directory are executed in a subprocess at runtime
- Skills are stateless — each invocation is independent

**Specs** (build-time reference only):
- `dist/specs/` is NOT loaded by any AI harness at runtime
- Specs are consumed by: `make validate-specs`, CI/CD consistency checks, QA agents
- The framework spec (`SPEC.md`) defines contracts enforced at render time, not runtime

#### Runtime lifecycle summary:

```
Session Start
   │
   ├─► Load AGENTS.md (global rules)           ← installed at ~/.config/opencode/AGENTS.md, ~/.copilot/AGENTS.md, ~/.claude/AGENTS.md, ~/.codex/AGENTS.md
   ├─► Discover agents/*.agent.md (Copilot)    ← available immediately as @agent
   ├─► Discover agents/*.md (Claude/OpenCode)  ← available immediately as @agent
   │
User invokes skill tool
   │
   ├─► Discover skills/<name>/SKILL.md        ← lazy load on first invocation
   ├─► Execute skill scripts                  ← subprocess per invocation
   └─► Return result to session               ← stateless, no side effects on harness
```

---

## Makefile Targets Reference

### Render targets (source → dist/)

| Target | Description | Output |
|--------|-------------|--------|
| `make render-opencode` | OpenCode agents + skills + config | `dist/opencode/` |
| `make render-copilot` | Copilot CLI agents + skills | `dist/copilot/` |
| `make render-claude` | Claude Code agents + skills | `dist/claude/` |
| `make render-codex` | Codex custom agents + skills + config | `dist/codex/` |
| `make render-specs` | Spec + orchestration YAMLs | `dist/specs/` |
| `make render-all` | All of the above | all dist/ subdirs |

### Install targets (dist/ → harness home)

| Target | Description | Destination |
|--------|-------------|-------------|
| `make install-opencode` | OpenCode agents + skills | `~/.config/opencode/` |
| `make install-copilot` | Copilot agents + skills | `~/.copilot/` |
| `make install-claude` | Claude Code agents + skills | `~/.claude/` |
| `make install-codex` | Codex agents/config + skills | `~/.codex/` and `~/.codex/skills/` |
| `make install` | Default harness set | default harness homes |

### Validation targets

| Target | Description |
|--------|-------------|
| `make validate-agents` | Agent frontmatter + AGENTS.md registry |
| `make validate-skills` | Skill frontmatter + SKILLS.md registry |
| `make validate-renders` | dist/ sync with src/skills/ |
| `make validate-specs` | dist/specs/ deployed + valid |

---

## Entity Type Consistency

All entity types follow the same frontmatter-first pattern:

```markdown
---
name: <canonical-name>
description: <one-line description>
model: <model-id>      # agents only
role: <role-name>      # agents only
version: <semver>      # specs only
---

# Body content here
```

**Naming rules:**
- Source agents: `<kebab-name>-agent.md` (e.g., `engineer-agent.md`)
- Rendered agents (Copilot): `<kebab-name>-agent.agent.md`
- Rendered agents (Claude/OpenCode): `<kebab-name>.md`
- Rendered agents (Codex): `<kebab-name>.toml`
- Skills: directory-based `<kebab-name>/SKILL.md`
- Specs: `SPEC.md` or `<name>.yaml`

---

## AGENTS.md v1.0 Readiness (research date: 2026-08-14)

**Bottom line: nothing to conform to yet.** AAIF (Linux Foundation Agentic AI
Foundation, formed Dec 9 2025) hosts AGENTS.md as one of its projects
alongside MCP and goose, and secondary sources describe a 2026-2027 roadmap
workstream titled "AGENTS.md v1.0 — first stable behavioral spec, with
goose-based validation tooling." That claim could not be confirmed from a
primary AAIF source: [aaif.io](https://aaif.io) lists working groups but no
roadmap page or spec-status page as of this writing, and
[github.com/agentsmd/agents.md/releases](https://github.com/agentsmd/agents.md/releases)
has never cut a release (confirmed live, 2026-08-14: "There aren't any
releases here"). Treat "AGENTS.md v1.0" as **unreleased / roadmap-only** —
this note exists so a future re-check doesn't have to re-derive that.

**Nested-file precedence** is documented only informally today:
[agents.md](https://agents.md/) states "Agents automatically read the
nearest file in the directory tree, so the closest one takes precedence,"
but an open GitHub question
([agentsmd/agents.md#53](https://github.com/agentsmd/agents.md/issues/53),
opened Sep 11 2025) asking whether conflicts are resolved by nearest-file-wins
or by merging all ancestor files remains unanswered. A community proposal
([agentsmd/agents.md#135](https://github.com/agentsmd/agents.md/issues/135),
opened Jan 8 2026, still open/unmerged, titled "v1.1" — implying no v1.0
baseline exists to number from) attempts to formalize it: Jurisdiction
(a file governs its directory and subdirectories), Accumulation (guidance
builds down the tree), Precedence (local overrides ancestor), and an explicit
resolution chain "LLM System Prompt → Agent System Prompt → User Prompt →
Local AGENTS.md → Ancestor AGENTS.md files (nearest first)." The proposal
explicitly disclaims enforcement: "the specification does not attempt to
mandate or enforce perfect compliance."

**Validation tooling** does not exist yet in any form we could find —
no CLI, no schema validator, nothing under the `goose` project exposing an
AGENTS.md check as of 2026-08-14. See `.github/workflows/ci.yml` "Gate 5
(stub)" for the forward-looking, always-non-blocking probe that will start
running automatically once such a tool appears on `PATH`.

### Nested AGENTS.md Precedence Contract (our commitment today)

We do **not** build a nesting engine — each of our renderers emits exactly
one AGENTS.md per harness install (the root doc: `~/.claude/AGENTS.md`,
`~/.copilot/AGENTS.md`, `~/.config/opencode/AGENTS.md`, `~/.codex/AGENTS.md`),
scoped explicitly to that harness install root. That root file is already
protected from clobbering a user's own file of the same name via the
sentinel/marker check in each renderer's doc-writer (`write_managed_doc()` in
render-claude.sh; equivalent inline checks in render-opencode.sh,
render-copilot.sh, render-codex.py) — unrelated to this task, pre-existing
behavior.

What this task closed: a **deeper**, user-authored `AGENTS.md` — e.g. one a
user places inside an installed skill directory such as
`~/.claude/skills/<name>/AGENTS.md` — is exactly the nested-precedence
pattern the convention describes, and it was being silently deleted on
every re-render. `render-claude.sh` and `render-opencode.sh` sync each skill
directory via `rsync -a --delete`, which treats any file not present in the
corresponding `src/skills/<name>/` as extraneous and removes it;
`render-codex.py`'s `copy_skill()` was worse — it `shutil.rmtree()`s the
entire destination skill directory before recopying, unconditionally. A live
test (plant a file, re-render, check survival) confirmed the deletion in all
three before the fix.

The fix, verified with the same live test post-fix:

- `render-claude.sh` / `render-opencode.sh`: the skill-sync `rsync -a
  --delete` line now also carries `--exclude='AGENTS.md'`. Since no
  `src/skills/*/` directory ships its own `AGENTS.md`, this is purely
  protective — it takes such a file out of both the copy and the deletion
  scope, so a user's nested file is left untouched at any depth under the
  skill directory.
- `render-codex.py`'s `copy_skill()` now stashes the bytes of any
  `AGENTS.md` found anywhere under the existing destination (`dst.rglob(
  "AGENTS.md")`) before the `rmtree()`, and restores them verbatim after
  `copytree()` completes.
- `render-copilot.sh` also carries `--exclude='AGENTS.md'` on its
  skill-sync `rsync -a --delete` line (line 130, pinned by regression test
  at `tests/test_agents_md_nesting.py:134`), so user nested files survive
  re-render identically to claude/opencode.

Regression coverage: `tests/test_agents_md_nesting.py` (plants a nested
`AGENTS.md` inside an installed skill dir, re-renders, asserts survival, for
each of claude/opencode/codex; plus a static guard on the `rsync --exclude`
flags and the `copy_skill()` preserve logic so a future edit can't silently
reintroduce the bug).

If `src/skills/*/` ever legitimately needs to ship its own `AGENTS.md`
(e.g. a skill's own subprocess scripts want harness-agnostic behavioral
guidance), the exclude/preserve logic above will need to special-case that
skill by name — `tests/test_agents_md_nesting.py::TestNoSourceSkillShipsAgentsMd`
will fail loudly the day that happens, rather than silently stopping the
legitimate file from syncing.

---

## Adding a New Entity

### New Agent

1. Create `src/agents/<name>-agent.md` with required frontmatter (`name`, `description`, `model`, `role`)
2. Add entry to `config/FRAMEWORK-MANIFEST.yaml` under `agents:`
3. Add to `src/AGENTS.md`'s Agent Roster (canonical — `docs/AGENTS.md` is only a pointer)
4. Run `make render-all` to generate dist/ artifacts
5. Run `make validate-agents` to confirm compliance
6. Run `make install` to deploy to harnesses

### New Skill

1. Create `src/skills/<name>/SKILL.md` with `name` and `description` frontmatter
2. Add skill scripts to `src/skills/<name>/`
3. Add to `config/FRAMEWORK-MANIFEST.yaml` under `skills:`
4. Run `make render-all` and `make validate-skills`
5. Run `make install` to deploy

### New Spec

1. Add source to `docs/` (for Markdown specs) or `config/` (for YAML configs)
2. Add the file path to `SPEC_FILES` array in `renderer/scripts/render-specs.sh`
3. Run `make render-specs` and `make validate-specs`

---

## CI/CD Integration

The following pipeline order is recommended:

```yaml
# Recommended CI pipeline order
steps:
  - make lint            # Syntax checks (Python, Shell, YAML)
  - make validate-agents # Agent registry consistency
  - make validate-skills # Skill registry consistency
  - make render-all      # Generate all dist/ artifacts
  - make validate-renders # Confirm dist/ sync
  - make validate-specs  # Confirm spec deployment
  - make test            # Full test suite
```

---

*See also: [docs/WORKFLOW.md](WORKFLOW.md) for SDLC gates.*
