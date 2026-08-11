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

The install/runtime roots are `~/.config/opencode/`, `~/.copilot/`, `~/.claude/`, `~/.codex/`, and `~/.pi/` (with Codex also honoring project-scoped `.codex/` when present).

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

**Trigger:** `make render-opencode`, `make render-copilot`, `make render-claude`, `make render-codex`, `make render-pi`, `make render-specs`, or `make render-all`
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
   - `config/deployment.yaml` → `dist/specs/deployment.yaml`
   - `config/token_budget.yaml` → `dist/specs/token_budget.yaml`

4. **Marker files** — written to track managed files for safe uninstall:
   - Skills: `<skill_dir>/.agentic-engine-<harness>` (e.g. `.agentic-engine-claude`)
   - Agents: `agents/.agentic-engine-<harness>` (manifest file, e.g. `.agentic-engine-claude`)
   - Specs: `dist/specs/.agentic-engine-specs`

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
    ├── render-copilot.sh       # renders skills → dist/copilot/skills/
    ├── render-copilot-agents.sh # renders agents → dist/copilot/agents/ (via Python)
    ├── render-copilot-agents.py # Python agent renderer (Copilot CLI format)
    ├── render-claude.sh        # renders agents + skills → dist/claude/
    ├── render-opencode.sh      # renders agents + skills + opencode.jsonc → dist/opencode/
    ├── render-codex.py         # renders Codex custom agents + skills + config → dist/codex/
    ├── render-pi.sh            # renders pi.dev config → dist/pi/
    ├── render-pi-dev.py        # Python pi.dev config renderer
    ├── render-specs.sh         # renders SPEC.md + config YAMLs → dist/specs/
    └── validate_renders.py     # validates dist/ sync with src/
```

**All render scripts source `lib.sh` (shim), which delegates to `render-lib.sh`.**

---

### Phase 3: Install-Time Deployment (`make install-*`)

**Trigger:** `make install-opencode`, `make install-copilot`, `make install-claude`, `make install-codex`, `make install-pi`, or `make install`
**Source:** `dist/<harness>/`  
**Destination:** `~/.config/opencode/`, `~/.copilot/`, `~/.claude/`, `~/.codex/`, `~/.pi/`
**Method:** `rsync -a` with `.DS_Store` and `.git` exclusions  

**Note:** `dist/specs/` is **not** deployed to a harness home directory — specs are a local reference layer only (used by validation, QA, and consistency checks). They live in `dist/specs/` and `config/` as source-of-truth files.

#### Install produces:

| Harness | Agent format | Skill format | Config files |
|---------|-------------|-------------|--------------|
| OpenCode | `agents/<name>.md` (mode/model/temp) | `skills/<name>/SKILL.md` | `opencode.jsonc`, `AGENTS.md` |
| Copilot CLI | `*.agent.md` (YAML frontmatter) | `skills/<name>/SKILL.md` | `queue/` structure |
| Claude Code | `agents/<name>.md` | `skills/<name>/SKILL.md` | – |
| Codex | `agents/<name>.toml` | `~/.codex/skills/<name>/SKILL.md` | `config.toml`, `AGENTS.md` |
| π.dev | `agent/SYSTEM.md` | – | `agent/settings.json`, `pi.yml` |

---

### Phase 4: Runtime Loading (AI Harness)

**Trigger:** AI harness session start / user invokes skill tool  
**Source:** `~/.config/opencode/`, `~/.copilot/`, `~/.claude/`, `~/.codex/`, `~/.pi/` (installed copies)

#### Loading behavior by entity type:

**Agents** (loaded at session start):
- Copilot CLI: reads `agents/*.agent.md` on session initialization; agent becomes available via `@agent-name` or `copilot --agent=<name>`
- Claude Code: reads `agents/*.md` on session start; subagents available via `@name` references
- OpenCode: reads `agents/*.md`; subagents available via `@name` in chat
- Codex: reads custom agents from `~/.codex/agents/*.toml` or project `.codex/agents/*.toml`; subagents spawn only when explicitly requested
- π.dev: reads `~/.pi/agent/SYSTEM.md`, `AGENTS.md`, and `settings.json` at startup

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
   ├─► Load AGENTS.md (global rules)           ← installed at ~/.config/opencode/AGENTS.md, ~/.copilot/AGENTS.md, ~/.claude/AGENTS.md, ~/.codex/AGENTS.md, ~/.pi/agent/AGENTS.md
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
| `make render-pi` | π.dev harness config | `dist/pi/` |
| `make render-specs` | Spec + orchestration YAMLs | `dist/specs/` |
| `make render-all` | All of the above | all dist/ subdirs |

### Install targets (dist/ → harness home)

| Target | Description | Destination |
|--------|-------------|-------------|
| `make install-opencode` | OpenCode agents + skills | `~/.config/opencode/` |
| `make install-copilot` | Copilot agents + skills | `~/.copilot/` |
| `make install-claude` | Claude Code agents + skills | `~/.claude/` |
| `make install-codex` | Codex agents/config + skills | `~/.codex/` and `~/.codex/skills/` |
| `make install-pi` | π.dev config | `~/.pi/` |
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
