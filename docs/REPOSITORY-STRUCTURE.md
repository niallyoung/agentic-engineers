# Repository Structure

## Overview

Clean, minimal directory structure with clear separation of concerns:

```
agentic-engineers/
├── src/                    # Source code (agents, skills, orchestration, config)
├── docs/                   # Documentation (guides, reference, operations, examples)
├── renderer/               # Build system (copilot/claude configuration rendering)
├── tests/                  # Test suite (pytest)
├── dist/                   # Build output (rendered configs, generated artifacts)
├── [support dirs]          # Temporary: artifacts/, logs/, metrics/, data/
└── [root files only]       # Makefile, README.md, conftest.py
```

## Directory Details

### src/ — Source Code

All Python source code and configuration lives under `src/`:

- **agents/** — Agent definition files (*.md) — role specs, routing rules
- **orchestration/** — Orchestration logic (Python modules)
  - `agents/` — Agent implementations, routing, delegation, spec validation
  - `tools/` — Orchestration utilities
- **skills/** — Skill implementations (each subdirectory = one SKILL)
  - ab-testing/, metrics-etl/, model-engineer/, tokenadvisor/, usage-tracking/, voice-notify/, etc.
- **config/** — Configuration management
  - `models.yaml` — Model registry and role assignments
  - `MODEL_ASSIGNMENTS_LOCKED.md` — Locked model assignments
  - `QUICK_REFERENCE.md` — Quick config reference
- **tools/** — Shared tooling utilities

### docs/ — Documentation

All documentation lives under `docs/`:

- **architecture/** — Architecture decisions (ADRs, model optimization)
- **decisions/** — Architecture Decision Records (ADR-*.md)
- **examples/** — Example configurations and protocol improvements
- **guides/** — Implementation and deployment guides
- **operations/** — Operational reference (metrics, memory structure, etc.)
- **reference/** — Design patterns, coding standards, architecture docs
- **specs/** — Protocol specification documents
- **archive/** — Archived session documents and historical context
- **SPEC.md** — Master implementation specification
- **PROTOCOL.md** — Queue protocol documentation
- **REPOSITORY-STRUCTURE.md** — This file

### renderer/ — Build System

Build and installation tooling:

- **scripts/** — Rendering scripts (render-copilot.sh, render-claude.sh, etc.)
- **hooks/** — GitHub/enforcement hooks
- **instructions/** — Global instructions for agents
- **workflows/** — Reusable GitHub Actions

### tests/ — Test Suite

Standard pytest test directory at repository root:

- `test_*.py` — Unit and integration tests (1047+ passing)
- `conftest.py` — Shared pytest fixtures (also at repo root)

### dist/ — Build Output (gitignored)

Generated artifacts from `make render-*` targets:

- **copilot/** — Rendered Copilot CLI configuration
- **claude/** — Rendered Claude configuration

### Support Directories

Temporary/operational directories (gitignored):

- **artifacts/** — Task queue, delegates, audit trail
- **logs/** — Runtime logs
- **metrics/** — Metrics and usage data
- **data/** — Operational data

---

## Consolidated Directories

The following directories were consolidated during restructuring (Phases 1–3):

| Old Location | New Location | Status |
|---|---|---|
| `guides/` | `docs/guides/` | ✅ Migrated |
| `reference/` | `docs/reference/` | ✅ Migrated |
| `operations/` | `docs/operations/` | ✅ Migrated |
| `examples/` | `docs/examples/` | ✅ Migrated |
| `shared/` | `docs/reference/` | ✅ Consolidated |
| `specs/` | `docs/specs/` + `src/specs/` | ✅ Migrated |
| `config/` (root) | `src/config/` | ✅ Migrated |
| `orchestration/` (root) | `src/orchestration/` | ✅ Migrated |
| `skills/` (root) | `src/skills/` | ✅ Migrated |

## Key Principles

1. **Source is `src/`** — All Python code lives under `src/`
2. **Documentation is `docs/`** — All reference material consolidated here
3. **Build is `renderer/`** — Rendering logic separate from source
4. **Output is `dist/`** — Build artifacts, never committed
5. **Tests are `tests/`** — Standard pytest location at repository root

## Import Conventions

```python
from src.orchestration.agents import ...
from src.orchestration.agents.implementations import ...
from src.config import ...
```

## Build Commands

```bash
make verify          # Verify structure + run all tests
make render-copilot  # Generate dist/copilot/
make render-claude   # Generate dist/claude/
make install         # Render + install to ~/.copilot/ and ~/.claude/
make clean           # Remove dist/ and __pycache__
```

---

*Generated during Phase 4 final validation. Updated: 2026-05-14.*
