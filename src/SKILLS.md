# Skills Registry

> **Status:** Framework slimdown phase (SPEC-2026-005). Registry contains **8 active skills**: the 6 that remained after queue-removal (2026-08-13) plus the audit-trail-review (2026-08-14) and self-healing-review (2026-08-15) meta-skills. The filesystem queue was removed once dispatch became a direct sub-agent spawn — the harness session transcript is now the durable DELEGATE/HANDBACK audit record. Role definitions and pattern libraries were deleted; refer to [`src/AGENTS.md`](AGENTS.md) for agent descriptions.

---

## Active Skills (8)

| Skill Name | File | Purpose | Role | Model | Effort |
|---|---|---|---|---|---|
| **orchestrator** | `src/skills/orchestrator/SKILL.md` | Direct sub-agent spawn dispatch, HANDBACK correlation, crash recovery, implementing the DELEGATE/HANDBACK protocol lifecycle. | orchestrator | claude-sonnet-5 | low |
| **protocol-validator** | `src/skills/protocol-validator/SKILL.md` | Runtime protocol validation for DELEGATEs/HANDBACKs against protocol-core-v1. | orchestrator | claude-haiku-4.5 | high |
| **spec-validator** | `src/skills/spec-validator/SKILL.md` | Validates implementation compliance with SPEC.md requirements. | quality-engineer | claude-haiku-4.5 | medium |
| **spec-management** | `src/skills/spec-management/SKILL.md` | Maintains SPEC.md and tracks implementation compliance across the framework. | principal-engineer | claude-opus-5 | medium |
| **skill-improvement-feedback** | `src/skills/skill-improvement-feedback/SKILL.md` | Analyzes skill execution feedback and proposes targeted improvements. | orchestrator | claude-haiku-4.5 | low |
| **codex-agent-cleanup** | `src/skills/codex-agent-cleanup/SKILL.md` | Codex session hygiene: close completed sub-agents, resume active work, keep agent capacity available. | orchestrator | claude-haiku-4.5 | medium |
| **audit-trail-review** | `src/skills/audit-trail-review/SKILL.md` | Reviews orchestration ledger (JSONL) for unfinished delegations, orphaned work, and status inconsistencies. Prose-only meta-skill. | quality-engineer | claude-sonnet-5 | medium |
| **self-healing-review** | `src/skills/self-healing-review/SKILL.md` | Repeatable investigate-fix-verify quality cycle: fan out read-only QE investigations, consolidate findings, dispatch disjoint fix packages by severity/file ownership, independently verify every HANDBACK, run the full battery, commit. Prose-only meta-skill. | orchestrator | claude-sonnet-5 | low |

---

## Skill Directory Structure

Each skill in `src/skills/<name>/` must contain a minimum:

```
src/skills/<name>/
  ├── SKILL.md          # Frontmatter + description (required)
  └── __init__.py       # Python package marker (only for script-backed skills)
```

`__init__.py` is required only where the skill ships importable Python. Four skills
have one (`audit-trail-review`, `protocol-validator`, `self-healing-review`,
`spec-validator`); the four prose-only skills (`codex-agent-cleanup`, `orchestrator`,
`skill-improvement-feedback`, `spec-management`) correctly have none.

Script-backed skills also include:

```
src/skills/<name>/
  ├── scripts/          # Executable implementations
  │   └── *.py
  └── tests/            # Test suite
      └── test_*.py
```

Prose-only skills (no `scripts/` directory) contain only SKILL.md and `__init__.py`, per design; the compliance audit exempts them from the scripts/tests directory requirement.

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
  category: orchestration | validation | monitoring | management | etc
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

All 8 skills appear exactly once below, grouped by the `role` in their frontmatter.

### Orchestrator
- `orchestrator/SKILL.md` — direct sub-agent spawn dispatch
- `protocol-validator/SKILL.md` — DELEGATE/HANDBACK runtime validation
- `codex-agent-cleanup/SKILL.md` — session cleanup
- `skill-improvement-feedback/SKILL.md` — feedback analysis
- `self-healing-review/SKILL.md` — investigate-fix-verify quality cycle

### Quality Engineer
- `spec-validator/SKILL.md` — SPEC compliance validation
- `audit-trail-review/SKILL.md` — audit JSONL review for orphaned/unfinished delegations

### Principal Engineer
- `spec-management/SKILL.md` — governed `docs/SPEC.md` maintenance
