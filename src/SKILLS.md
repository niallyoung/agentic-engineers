# Skills Registry

> **Status:** Framework slimdown phase (SPEC-2026-005). Registry contains **6 active skills** (spec-validator and skill-improvement-feedback were removed 2026-11-10 as dead weight; this file is the single source of truth for the skills list). The filesystem queue was removed once dispatch became a direct sub-agent spawn — the harness session transcript is now the durable DELEGATE/HANDBACK audit record. Role definitions and pattern libraries were deleted; refer to [`src/AGENTS.md`](AGENTS.md) for agent descriptions.

---

## Active Skills (6)

| Skill Name | File | Purpose | Role | Effort |
|---|---|---|---|---|
| **orchestrator** | `src/skills/orchestrator/SKILL.md` | Direct sub-agent spawn dispatch, HANDBACK correlation, crash recovery, implementing the DELEGATE/HANDBACK protocol lifecycle. | orchestrator | low |
| **protocol-validator** | `src/skills/protocol-validator/SKILL.md` | Runtime protocol validation for DELEGATEs/HANDBACKs against protocol-core-v1. | orchestrator | high |
| **spec-management** | `src/skills/spec-management/SKILL.md` | Maintains SPEC.md and tracks implementation compliance across the framework. | principal-engineer | medium |
| **audit-trail-review** | `src/skills/audit-trail-review/SKILL.md` | Reviews orchestration ledger (JSONL) for unfinished delegations, orphaned work, and status inconsistencies. Prose-only meta-skill. | quality-engineer | medium |
| **self-healing-review** | `src/skills/self-healing-review/SKILL.md` | Repeatable investigate-fix-verify quality cycle: fan out read-only QE investigations, consolidate findings, dispatch disjoint fix packages by severity/file ownership, independently verify every HANDBACK, run the full battery, commit. Prose-only meta-skill. | orchestrator | low |

**Model assignments:** See [docs/MODELS.md](../docs/MODELS.md) for the specific model each role is pinned to.

---

## Skill Directory Structure

Each skill in `src/skills/<name>/` must contain a minimum:

```
src/skills/<name>/
  ├── SKILL.md          # Frontmatter + description (required)
  └── __init__.py       # Python package marker (only for script-backed skills)
```

`__init__.py` is required only where the skill ships importable Python. Three skills
have one (`audit-trail-review`, `protocol-validator`, `self-healing-review`); the
other two (`orchestrator`, `spec-management`) correctly have none.

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
  model: <any model ID in config/models.yaml, e.g. claude-haiku-5.5>   # see docs/MODELS.md
  effort: low | medium | high
---
```


**`metadata.role` / `metadata.model` / `metadata.effort` are advisory.** They name the
*suggested tier for running this skill* (the role whose perspective the skill adopts and the
model/effort that suffice for it). They are not required to equal that role's pin in
`config/models.yaml`: for example `protocol-validator` is `role: orchestrator` with a cheaper
Haiku-family model. The only requirement is that `model` is a valid registry ID (the current
eight skills all are); nothing enforces a role/model pairing, and `renderer/validate_skills.py`
checks shape only. The agent that invokes a skill still runs on its own role pin.

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

All 5 skills appear exactly once below, grouped by the `role` in their frontmatter.

### Orchestrator
- `orchestrator/SKILL.md` — direct sub-agent spawn dispatch
- `protocol-validator/SKILL.md` — DELEGATE/HANDBACK runtime validation
- `self-healing-review/SKILL.md` — investigate-fix-verify quality cycle

### Quality Engineer
- `audit-trail-review/SKILL.md` — audit JSONL review for orphaned/unfinished delegations

### Principal Engineer
- `spec-management/SKILL.md` — governed `docs/SPEC.md` maintenance
