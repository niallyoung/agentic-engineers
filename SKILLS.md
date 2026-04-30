---
name: Skills Index
description: Complete catalog of agentic-engineers agent skills
---

# Skills Index

Master index of all agent role definitions. Each skill defines how a specialist agent approaches its domain.

## Core Orchestration

| Skill | Model | Role | Purpose |
|-------|-------|------|---------|
| [AGENTS.md](AGENTS.md) | Haiku | General Orchestrator | Routes tasks to specialist agents (6-point decision tree) |

## Phase 6.1: Feedback Loops

Continuous improvement agents that analyze agent performance and refine future decisions.

| Skill | Model | Role | Purpose |
|-------|-------|------|---------|
| [src/roles/model-engineer.md](src/roles/model-engineer.md) | Haiku | Model Engineer | Analyzes token efficiency, time efficiency, routing accuracy. Updates confidence tables weekly. |
| [src/roles/quality-gate-aggregator.md](src/roles/quality-gate-aggregator.md) | Haiku | Quality Gate Aggregator | Aggregates 4 sub-agent HANDBACKs, detects trends, recommends threshold adjustments. |
| [src/roles/config-enforcement-verifier.md](src/roles/config-enforcement-verifier.md) | Haiku | Config Enforcement Verifier | Validates auto-fixes resolved issues, tracks success rates by issue type. |

## Phase 7: Core SDLC Agents

Three-phase workflow: analysis → planning → execution → validation.

| Skill | Model | Role | Purpose |
|-------|-------|------|---------|
| [src/roles/engineer.md](src/roles/engineer.md) | Haiku | Engineer | Execution specialist. Implements well-scoped, planned tasks with high efficiency. |
| [src/roles/senior-engineer.md](src/roles/senior-engineer.md) | Sonnet | Senior Engineer | Analysis & planning specialist. Investigates complex unscoped work, produces detailed plans. |
| [src/roles/quality-engineer.md](src/roles/quality-engineer.md) | Sonnet | Quality Engineer | Post-implementation validation. 8-point quality checklist. APPROVE/REWORK/ESCALATE decision. |

## Phase 8: Advanced Specialists

Deep expertise agents for specific high-impact domains.

| Skill | Model | Role | Purpose |
|-------|-------|------|---------|
| [src/roles/lead-engineer.md](src/roles/lead-engineer.md) | Sonnet | Lead Engineer | Code review specialist. 8-point review checklist (style, errors, security, performance, maintainability, testing, docs, compatibility). |
| [src/roles/security-engineer.md](src/roles/security-engineer.md) | Opus | Security Engineer | Threat modeling & security validation. STRIDE framework, vulnerability assessment, compliance verification. |
| [src/roles/principal-engineer.md](src/roles/principal-engineer.md) | Opus | Principal Engineer | Cross-service architecture. Design options analysis, trade-off evaluation, implementation roadmap. |

## Phase 5.10: Quality Gates (Reference)

Local quality gates that run pre-commit/pre-push:

- Security scanning (credentials, vulnerabilities)
- Testing (unit, E2E, coverage)
- Linting (code style)
- Metrics (performance, dependencies)

*These are handled by CI/CD hooks, not agent-based.*

---

## HANDBACK Protocol

All agents return work via HANDBACK format:

```
HANDBACK
────────
Agent: [agent name]
Task: [original task summary]
Status: [COMPLETE | ESCALATE | REWORK]
Quality Score: [0-100] (if applicable)
Metrics: 
  - token_used: N
  - duration: Xs
  - quality_score: N/100
  - routing_confidence: 0.XX
  - [additional metrics per agent]
Result: [summary of work completed]
Next Steps: [if any]
```

HANDBACKs flow to:
- **Model Engineer** — token/time efficiency analysis for routing calibration
- **Quality Gate Aggregator** — quality trends and anomaly detection
- **Config Enforcement Verifier** — validation that fixes resolved underlying issues

---

## Routing Decision Tree

See [AGENTS.md](AGENTS.md) for complete decision tree and confidence scoring logic.

Quick reference:
1. Security-scoped? → Security Engineer (Opus)
2. Cross-service? → Principal Engineer (Opus)
3. Review/validation? → Lead Engineer (Sonnet) OR Quality Engineer (Sonnet)
4. Complex + no plan? → Senior Engineer (Sonnet)
5. Well-scoped + plan? → Engineer (Haiku)
6. Default → Engineer (Haiku)

---

## Skill Development Notes

### Creating a New Skill

1. **File location:** `src/roles/{agent-name}.md`
2. **Frontmatter:** name, role, model, thinking (true/false), effort level
3. **Sections:** Role description, triggers, how it works, output format, example execution
4. **HANDBACK:** Define what metrics/outputs flow back to feedback loops
5. **Provider-agnostic:** Use generic model names (claude-haiku, claude-sonnet, claude-opus) — render pipeline substitutes provider-specific names

### Testing Skills Locally

```bash
# Render to specific provider
make render-claude

# Test specific agent
claude ask "You are the Engineer agent. Execute this task: [task]"

# Review HANDBACK output
cat ~/.claude/roles/engineer.md
```

---

## Metrics Collection (Delegate Protocol)

Feedback loops use **delegate/handback protocol** for metrics:

1. **Model Engineer** collects per-HANDBACK:
   - tokens_used
   - duration
   - quality_score
   - routing_confidence
   - task_complexity (low/medium/high)

2. **Quality Gate Aggregator** collects per-HANDBACK:
   - status (COMPLETE, ESCALATE, REWORK)
   - quality_score
   - agent_name
   - task_category

3. **Config Enforcement Verifier** collects validation:
   - issue_type
   - fix_applied
   - fix_success (true/false)
   - verification_method

**Storage:** These metrics are collected via HANDBACK protocol. Later phases will add persistent storage (DynamoDB/S3) and analytics.

---

## Next Steps

- **Short term:** All 8 agent skills fully documented and provider-rendered
- **Medium term:** Local testing via Claude/Copilot CLI
- **Long term:** Integration with CI/CD, webhook invocation, metrics persistence

