# Skills Available

This document indexes all available (active) skills in the agentic-engineers framework.

**Last updated:** 2026-05-30  
**Status:** 14 active skills; 5 deprecated skills archived in `docs/archive/deprecated-skills/`  
**See also:** [DEPRECATED-SKILLS.md](DEPRECATED-SKILLS.md) for archived skills and alternatives

## Integration Skills

| Skill | Description | Category | Model |
|-------|-------------|----------|-------|
| harness-integration-tracker | Discover and document harness integration code/docs across all harnesses | integration | - |
| opencode-feature-sync | Drift/feature sync between OpenCode and agentic-engineers renderer | integration | - |

## Validation Skills

| Skill | Description | Category | Model |
|-------|-------------|----------|-------|
| consistency-checker | Automated cross-validation of protocol queue integrity | validation | claude-haiku-4.5 |
| protocol-validator | Runtime protocol validation for DELEGATEs/HANDBACKs | validation | - |
| spec-validator | Validates implementation compliance with SPEC.md | validation | - |
| spec-management | Exclusive SPEC.md change protection | management | - |
| workflow-review | Validates end-to-end delegation workflows | validation | claude-sonnet-4.6 |

## Agent Skills

| Skill | Description | Category | Model |
|-------|-------------|----------|-------|
| agent-creator | Scaffolds new SPEC-compliant agents | scaffolding | - |

## Queue Skills

| Skill | Description | Category | Model |
|-------|-------------|----------|-------|
| queue-management | Atomic queue operations for DELEGATE/HANDBACK lifecycle | queue | - |
| queue-query | Read-only visibility over the local queue (size, ls, orphans, done-summary) | queue | claude-haiku-4.5 |

## Metrics Skills

| Skill | Description | Category | Model |
|-------|-------------|----------|-------|
| usage-tracking | Real-time and historical token usage | metrics | - |

> **Deprecated:** metrics-etl, tokenadvisor, ab-testing. See [DEPRECATED-SKILLS.md](DEPRECATED-SKILLS.md)

## Operations Skills

| Skill | Description | Category | Model |
|-------|-------------|----------|-------|
| file-sync | Discovers and analyzes scripts in the repository | operations | - |
| skill-creator | Creates new skills following the specification | scaffolding | - |
| voice-notify | Voice notification integration layer | notifications | - |
| todo-maintenance | Auto-sync queue DELEGATEs with TODO.md | maintenance | - |
| model-engineer | Cost-quality optimization agent | optimization | - |

> **Deprecated:** repo-init. See [DEPRECATED-SKILLS.md](DEPRECATED-SKILLS.md)

## Maintenance Cadence

- **workflow-review**: Run on every PR to feature/workflow-* branches
- **consistency-checker**: Run on every heartbeat (hourly) and on protocol changes
- **spec-validator**: Run as pre-merge gate on every PR
- **protocol-validator**: Run inline during task processing (<5ms)
- **usage-tracking**: Real-time collection; analysis on demand

> **Deprecated maintenance cadence items:** tokenadvisor (daily), ab-testing (routing changes). See [DEPRECATED-SKILLS.md](DEPRECATED-SKILLS.md) for alternatives.

## Adding a New Skill

1. Create `src/skills/<skill-name>/` directory
2. Add `SKILL.md` with frontmatter metadata
3. Add `scripts/<skill_name>.py` with implementation
4. Add tests in `tests/test_<skill_name>.py`
5. Register in `config/FRAMEWORK-MANIFEST.yaml` under `skills:`
6. Add to this document
