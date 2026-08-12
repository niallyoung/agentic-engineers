# src/skills/ — Skills-First Architecture

agentic-engineers is a **skills-first** framework: agent behavior is defined
declaratively in `src/agents/*.md` (frontmatter + prose instructions), and any
Python or shell logic an agent needs at runtime lives in a **skill** —
a self-contained directory under `src/skills/` with a `SKILL.md` manifest and
(optionally) a `scripts/` and `tests/` subdirectory. There is no central
Python orchestration package; skills are the only unit of packaged behavior.

Each harness renderer (`renderer/scripts/render-*.sh|py`) copies every skill
into that harness's install location verbatim, so a skill written once works
identically across Claude Code, Copilot CLI, OpenCode, and Codex.

## The 8 skills

| Skill | Kind | Purpose |
|---|---|---|
| `orchestrator` | prose-only | Direct sub-agent spawn dispatch, HANDBACK correlation, crash recovery |
| `spec-management` | prose-only | Exclusive `docs/SPEC.md` change protection (proposal → analysis → approval) |
| `skill-improvement-feedback` | prose-only | Canonical pattern for `skill_feedback` in HANDBACKs |
| `codex-agent-cleanup` | prose-only | Routine maintenance for Codex sessions |
| `protocol-validator` | script-backed | Runtime DELEGATE/HANDBACK schema validation |
| `queue-management` | script-backed | Atomic `enqueue()` — the one sanctioned queue write path |
| `queue-query` | script-backed | Read-only queue inspection (incoming/processing/done/failed) |
| `spec-validator` | script-backed | Post-hoc compliance checking of a diff against `docs/SPEC.md` |

"Prose-only" skills carry their entire behavior in `SKILL.md` instructions —
no `scripts/` directory. "Script-backed" skills pair `SKILL.md` with a
`scripts/` directory (imported via the hyphenated-directory `sys.path` /
`importlib` pattern used throughout `tests/`) and a `tests/` directory run in
isolation by `scripts/run_skill_tests.py`.

## Roles and models

Skills describe *what a capability does*; they do not own role→model
assignment. For the specialist roster (Orchestrator, Engineer,
Senior/Lead/Principal Engineer, Quality/Security/Model Engineer), their
default models, and the DELEGATE/HANDBACK protocol itself, see
`src/AGENTS.md` — the single source of truth.

## Adding a skill

Create a new directory with a `SKILL.md` (YAML frontmatter: `name`,
`description`; see any existing skill for the shape) plus an optional
`scripts/` + `tests/` pair. Then validate it:

```bash
python3 scripts/validate_skills.py     # frontmatter + registry completeness
make validate-skills                   # same check via the renderer entry point
make render-all && make validate-renders   # confirm it renders to every harness
```
