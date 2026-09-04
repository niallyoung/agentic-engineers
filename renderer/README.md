# Agent & Skill Renderers

Renders agentic-engineers' canonical `src/agents/` + `src/skills/` sources into
per-tool target formats. Each harness gets a provider-specific rendering because
frontmatter schemas, model-id formats, and directory layouts differ.

## Supported harnesses

| Harness | Render script | Install target | Output |
|---|---|---|---|
| Claude Code | `renderer/scripts/render-claude.sh` | `make install-claude` | `~/.claude/` |
| Copilot CLI | `renderer/scripts/render-copilot.sh` (agents via render-copilot-agents.py) | `make install-copilot` | `~/.copilot/` |
| OpenCode | `renderer/scripts/render-opencode.sh` | `make install-opencode` | `~/.config/opencode/` |
| Codex | `renderer/scripts/render-codex.py` | `make install-codex` | `~/.codex/` |

Specs (SPEC.md + orchestration YAML) render separately via
`renderer/scripts/render-specs.sh` → `make render-specs`.

## Quick start

From the repo root:

```bash
make render-all      # generate dist/{claude,copilot,opencode,codex,specs}/
make install         # render + install the default harness set (marker-aware)
```

Or render/install a single harness, e.g.:

```bash
make render-claude    # generate dist/claude/
make install-claude   # render fresh + install → ~/.claude/
```

All install targets are marker-aware: they never overwrite a user's own
agents, skills, or config files. `make status` reports drift between `dist/`
and each installed target.

## Structure

```
renderer/
├── scripts/
│   ├── render-claude.sh             — Claude Code renderer (agents + skills)
│   ├── render-copilot.sh            — Copilot CLI renderer (agents via render-copilot-agents.py + skills + docs)
│   ├── render-copilot-agents.py     — Copilot CLI agent renderer (Python)
│   ├── render-opencode.sh           — OpenCode renderer
│   ├── render-codex.py              — Codex renderer
│   ├── render-specs.sh              — SPEC.md + orchestration YAML renderer
│   ├── unified-install.sh           — shared backup + install flow (all harnesses)
│   ├── validate_renders.py          — dist/ vs src/skills/ sync check
│   ├── check_test_regression.py     — pytest collection-count regression gate
│   ├── claude-delegate-guard.py     — Claude PreToolUse hook enforcing DELEGATE protocol
│   └── render-lib.sh                — shared shell helpers (single source of truth)
├── lib/                             — shared Python rendering helpers
├── validate_agents.py               — src/agents/ frontmatter + registration validator
├── validate_skills.py               — src/skills/ frontmatter + registry validator
└── README.md                        — this file
```

## Maintenance

All source files (`src/agents/`, `src/skills/`) are committed; rendered
output under `dist/` and installed copies under `~/.claude/`, `~/.copilot/`,
etc. are regenerable and not committed (`dist/` is gitignored).

Update workflow:

1. Edit source files under `src/agents/` or `src/skills/`.
2. Re-render: `make render-all` (or the single-harness target).
3. Validate: `make validate-renders && make validate-agents && make validate-skills`.
4. Commit the source changes — never the rendered `dist/` output.

**Note:** There is no `make status` target. Use `make validate-renders` to check for drift between source and rendered output.

## See Also

- `src/AGENTS.md` — canonical roster, roles, and models.
- `docs/RENDERING.md` — full rendering pipeline documentation.
