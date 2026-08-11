# Skills Registry

> **Status:** Framework slimdown phase (SPEC-2026-005). Registry now contains only the 8 surviving skills post-WP-2 (2026-08-11). Role definitions and pattern libraries were deleted; refer to [`src/AGENTS.md`](AGENTS.md) for agent descriptions.

---

## Active Skills (8 Survivors)

| Skill Name | File | Purpose | Role | Model | Effort |
|---|---|---|---|---|---|
| **orchestrator** | `src/skills/orchestrator/SKILL.md` | In-harness queue orchestration system implementing DELEGATE/HANDBACK protocol lifecycle. | orchestrator | claude-haiku-4.5 | high |
| **queue-management** | `src/skills/queue-management/SKILL.md` | Atomic queue operations for DELEGATE/HANDBACK lifecycle with cycle detection, rate limiting, and validation. | orchestrator | claude-haiku-4.5 | high |
| **queue-query** | `src/skills/queue-query/SKILL.md` | Local-queue visibility skill — query and inspect filesystem queue by state. | orchestrator | claude-haiku-4.5 | low |
| **protocol-validator** | `src/skills/protocol-validator/SKILL.md` | Runtime protocol validation for DELEGATEs/HANDBACKs against protocol-core-v1. | all | claude-haiku-4.5 | medium |
| **spec-validator** | `src/skills/spec-validator/SKILL.md` | Validates implementation compliance with SPEC.md requirements. | quality-engineer, lead-engineer | claude-haiku-4.5 | medium |
| **spec-management** | `src/skills/spec-management/SKILL.md` | Maintains SPEC.md and tracks implementation compliance across the framework. | senior-engineer, lead-engineer | claude-sonnet-5 | medium |
| **skill-improvement-feedback** | `src/skills/skill-improvement-feedback/SKILL.md` | Analyzes skill execution feedback and proposes targeted improvements. | orchestrator, lead-engineer | claude-sonnet-5 | medium |
| **codex-agent-cleanup** | `src/skills/codex-agent-cleanup/SKILL.md` | Codex session hygiene: close completed sub-agents, resume active work, keep queue capacity available. | orchestrator | claude-haiku-4.5 | low |

---

## Skill Directory Structure

Each skill in `src/skills/<name>/` must contain:

```
src/skills/<name>/
  ├── SKILL.md          # Frontmatter + description (required)
  ├── __init__.py       # Python package marker (required)
  ├── scripts/          # Executable implementations (required directory)
  │   └── *.py
  └── tests/            # Test suite (required directory)
      └── test_*.py
```

SKILL.md frontmatter (required keys):

```yaml
---
name: skill-name
description: One-sentence description
license: Proprietary
compatibility: agentic-engineers framework v5.10+
metadata:
  author: agentic-engineers
  version: "1.0"
  category: orchestration | queue | validation | monitoring | etc
  role: orchestrator | engineer | quality-engineer | lead-engineer | senior-engineer | principal-engineer | security-engineer
  model: claude-haiku-4.5 | claude-sonnet-5 | claude-opus-5 | claude-fable-5
  effort: low | medium | high
---
```

---

## Registration Validation

All paths listed above are automatically validated by `renderer/validate_skills.py`:

```bash
make validate-skills
```

Validates:
- All paths in this registry exist on disk
- All `SKILL.md` files have required frontmatter
- All discovered `SKILL.md` files are registered here

---

## Quick Reference by Role

### Orchestrator
- `orchestrator/SKILL.md` — main queue orchestration
- `queue-management/SKILL.md` — queue operations  
- `queue-query/SKILL.md` — queue inspection
- `codex-agent-cleanup/SKILL.md` — session cleanup
- `skill-improvement-feedback/SKILL.md` — feedback analysis

### Quality Engineer / Lead Engineer
- `spec-validator/SKILL.md` — SPEC compliance validation
- `spec-management/SKILL.md` — SPEC maintenance
- `protocol-validator/SKILL.md` — protocol validation

### All Roles
- `protocol-validator/SKILL.md` — shared validation tool
