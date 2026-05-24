# Skills Available

This document indexes all available skills in the agentic-engineers framework.

Last updated: 2026-05-24

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

## Metrics Skills

| Skill | Description | Category | Model |
|-------|-------------|----------|-------|
| metrics-etl | Data pipeline aggregating daily metrics | metrics | - |
| tokenadvisor | Daily metrics analysis for cost optimization | metrics | - |
| usage-tracking | Real-time and historical token usage | metrics | - |
| ab-testing | Experiment orchestration framework | testing | - |

## Operations Skills

| Skill | Description | Category | Model |
|-------|-------------|----------|-------|
| repo-init | Initializes new repositories with the framework | operations | - |
| file-sync | Discovers and analyzes scripts in the repository | operations | - |
| skill-creator | Creates new skills following the specification | scaffolding | - |
| voice-notify | Voice notification integration layer | notifications | - |
| version-manager | Semantic versioning workflow | versioning | - |
| todo-maintenance | Auto-sync queue DELEGATEs with TODO.md | maintenance | - |
| model-engineer | Cost-quality optimization agent | optimization | - |

## Maintenance Cadence

- **workflow-review**: Run on every PR to feature/workflow-* branches
- **consistency-checker**: Run on every heartbeat (hourly) and on protocol changes
- **spec-validator**: Run as pre-merge gate on every PR
- **protocol-validator**: Run inline during task processing (<5ms)
- **tokenadvisor**: Run daily for cost optimization
- **ab-testing**: Run on routing changes and model upgrades

## Adding a New Skill

1. Create `src/skills/<skill-name>/` directory
2. Add `SKILL.md` with frontmatter metadata
3. Add `scripts/<skill_name>.py` with implementation
4. Add tests in `tests/test_<skill_name>.py`
5. Register in `config/FRAMEWORK-MANIFEST.yaml` under `skills:`
6. Add to this document
